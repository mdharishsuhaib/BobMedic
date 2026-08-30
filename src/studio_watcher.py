"""
studio_watcher.py — detects failures in IBM RPA Studio and starts the heal.

The rest of the engine can only see bots it launched itself. In a real
deployment — and in the demo — the bot is started from IBM RPA Studio, and
nothing was watching it. This closes that gap.

Studio records every failed element lookup in its own log:

    2026-08-30T02:42:29.8190683+03:00 WARN WebClickCommand Studio
    Control not found to Click on Css=#btn-login

That line carries everything the loop needs: when it happened, what action was
attempted, and which selector stopped matching. The watcher tails the log from
its current end, and when such a line appears it identifies which bot scripts
use that selector and runs the full diagnosis on each.

    python src/studio_watcher.py                 watch every registered bot
    python src/studio_watcher.py --bot bobmedic-login
    python src/studio_watcher.py --replay        heal from the last logged failure

Run it beside the demo. Break the site in break.html, run the bot in Studio,
and the incident appears in the dashboard on its own.
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

import engine
from parser import parse_wal
from registry import load_bots
from serve import ensure_server

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Studio keeps one rolling log per installation.
DEFAULT_LOG = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "IBM Robotic Process Automation"
    / "Studio.log"
)

# "Control not found to Click on Css=#btn-login"
FAILURE_PATTERN = re.compile(
    r"Control not found to (?P<action>\w+) on (?P<kind>Css|Xpath)=(?P<selector>[^\s\x00-\x1f]+)",
    re.IGNORECASE,
)

# The ISO timestamp Studio writes immediately before the level and category.
TIMESTAMP_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+[+\-]\d{2}:\d{2})")

# Studio flushes its log in 8 KB blocks, so a failure can sit unwritten for
# tens of seconds — too slow to demo. It touches this file the moment a
# debugging session ends, which is a signal we get within a second.
RUN_MARKER = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "IBM Robotic Process Automation"
    / "DefaultDebuggingState.bin"
)

POLL_SECONDS = 1.0

# Never start a second diagnosis while the last one is still recent.
HEAL_DEBOUNCE_SECONDS = 25.0


def find_log(explicit: str | None = None) -> Path:
    """Locate Studio's log, or explain where it was expected."""
    path = Path(explicit) if explicit else DEFAULT_LOG
    if not path.exists():
        raise FileNotFoundError(
            f"IBM RPA Studio log not found at {path}. Run a bot in Studio once so "
            "it creates the log, or pass --log with the correct path."
        )
    return path


def _decode(chunk: bytes) -> str:
    """Studio's log mixes text with binary record framing; keep the text."""
    return chunk.decode("utf-8", errors="replace")


def read_new_text(path: Path, offset: int) -> tuple[str, int]:
    """
    Read whatever has been appended since ``offset``.

    The size is measured by opening the file and seeking to its end, not with
    stat(). Windows serves stat() from the directory entry, which another
    process's open write handle does not refresh — Studio can append for
    minutes while stat() still reports the size the file had when the watcher
    started, and a tail built on stat() would sit there seeing nothing.

    Returns the decoded text and the new offset. A file that shrank was
    rotated, so reading restarts from the beginning.
    """
    with open(path, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()

        if size < offset:
            offset = 0
        if size == offset:
            return "", offset

        handle.seek(offset)
        chunk = handle.read(size - offset)

    return _decode(chunk), size


def _parse_stamp(value: str | None) -> float | None:
    """Turn Studio's ISO timestamp into a comparable epoch value."""
    if not value:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


# Studio writes the exception type directly after the selector with no
# separator, so a raw match reads "#btn-loginWDG.Automation…ControlNotFound…".
EXCEPTION_MARKERS = ("WDG.", "System.", "Exception", "Microsoft.")


def _clean_selector(value: str) -> str:
    """Trim the exception text Studio appends straight onto the selector."""
    for marker in EXCEPTION_MARKERS:
        position = value.find(marker)
        if position > 0:
            value = value[:position]
    return value.strip().strip(chr(34)).strip(chr(39))


def find_failures(text: str) -> list[dict]:
    """Extract every element-lookup failure Studio reported in this text."""
    failures = []
    for match in FAILURE_PATTERN.finditer(text):
        # The timestamp sits just before the message in the same record.
        preceding = text[max(0, match.start() - 400):match.start()]
        stamps = TIMESTAMP_PATTERN.findall(preceding)
        failures.append({
            "action": match.group("action").lower(),
            "kind": match.group("kind").lower(),
            "selector": _clean_selector(match.group("selector")),
            "timestamp": stamps[-1] if stamps else None,
        })
    return failures


def bots_using(selector: str, only: str | None = None) -> list[str]:
    """
    Which registered bots address the page through this selector.

    A renamed id breaks every script that used it, so all of them are returned
    unless the caller has scoped the watch to one bot.
    """
    matches = []
    for bot_id, bot in load_bots().items():
        if only and bot_id != only:
            continue
        try:
            steps = parse_wal(bot["wal_path"])
        except OSError:
            continue
        if any(step.selector_value == selector for step in steps):
            matches.append(bot_id)
    return matches


def handle_failure(failure: dict, only: str | None = None, headless: bool = True) -> list[dict]:
    """Diagnose and heal every bot affected by one Studio failure."""
    selector = failure["selector"]
    when = failure["timestamp"] or "just now"
    print(f"\n[STUDIO]   {when}")
    print(f"[STUDIO]   {failure['action']} failed — selector no longer matches: {selector}")

    affected = bots_using(selector, only)
    if not affected:
        print(f"[STUDIO]   No registered bot uses {selector}. Nothing to heal.")
        return []

    print(f"[STUDIO]   Affected bot(s): {', '.join(affected)}")

    incidents = []
    for bot_id in affected:
        # breaks=None leaves the site exactly as the operator left it, so the
        # engine reproduces the same failure Studio hit.
        incident = engine.heal(bot_id, breaks=None, headless=headless)
        incidents.append(incident)
        if incident.get("status") == "green":
            print(f"[STUDIO]   {bot_id} ran clean here — the page may have been fixed already.")
        else:
            print(f"[STUDIO]   {incident['id']}: {incident['status']} / {incident['action']}")
    return incidents


def _marker_mtime() -> float | None:
    """When Studio last ended a debugging session, if it records that at all."""
    try:
        return RUN_MARKER.stat().st_mtime
    except OSError:
        return None


def heal_bot(bot_id: str, headless: bool = True) -> dict:
    """
    Re-run one bot and heal it if it breaks.

    The engine finds the failing step itself, so this works whether or not
    Studio has flushed its log yet: Studio tells us a run just ended, and our
    own run establishes what broke.
    """
    print("[STUDIO]   Diagnosing. This opens a browser twice — scoring the "
          "changed page, then proving the patch — so give it about a minute.")
    started = time.time()
    try:
        incident = engine.heal(bot_id, breaks=None, headless=headless)
    except KeyboardInterrupt:
        print()
        print("[STUDIO]   Interrupted mid-diagnosis. Nothing was patched.")
        raise

    elapsed = time.time() - started
    if incident.get("status") == "green":
        print(f"[STUDIO]   {bot_id} completed here — nothing to heal. ({elapsed:.0f}s)")
    else:
        print(f"[STUDIO]   {incident['id']}: {incident['status']} / "
              f"{incident['action']}  ({elapsed:.0f}s)")
    return incident


def watch(
    log_path: Path,
    *,
    only: str | None = None,
    from_start: bool = False,
    headless: bool = True,
) -> None:
    """Follow Studio's log and heal whatever it reports as broken."""
    # Measure through an open handle, for the same reason read_new_text does.
    _, offset = read_new_text(log_path, 0)
    if from_start:
        offset = 0
    started_at = time.time()

    ensure_server()

    marker_seen = _marker_mtime()
    last_heal = 0.0

    print(f"[WATCH]    Following {log_path}")
    print(f"[WATCH]    Bots: {only or 'all registered'}")
    print(f"[WATCH]    Reading from byte {offset:,}")
    if only and marker_seen is not None:
        print(f"[WATCH]    Also watching {RUN_MARKER.name} for the end of a Studio run")
    print("[WATCH]    Break the site, run the bot in Studio. Ctrl+C to stop.\n")

    seen: set[tuple] = set()
    try:
        while True:
            # Fast path: Studio touches its debugging-state file as soon as a
            # run ends, well before the log block is flushed. Our own re-run
            # then establishes what actually broke.
            if only:
                marker_now = _marker_mtime()
                if (
                    marker_now is not None
                    and marker_seen is not None
                    and marker_now > marker_seen
                    and time.time() - last_heal > HEAL_DEBOUNCE_SECONDS
                ):
                    marker_seen = marker_now
                    last_heal = time.time()
                    print(f"\n[STUDIO]   A Studio run just finished — checking {only}")
                    heal_bot(only, headless=headless)
                    print("\n[WATCH]    Listening again...")
                elif marker_now is not None:
                    marker_seen = max(marker_seen or 0, marker_now)

            text, offset = read_new_text(log_path, offset)
            if text:
                for failure in find_failures(text):
                    # Studio's log carries every failure it has ever recorded.
                    # Only act on ones that happened after this watch began.
                    stamp = _parse_stamp(failure["timestamp"])
                    if not from_start and stamp is not None and stamp < started_at - 5:
                        continue
                    key = (failure["timestamp"], failure["selector"])
                    if key in seen:
                        continue
                    seen.add(key)

                    # The same run reaches us twice: the marker fires when it
                    # ends, then the log block is flushed some seconds later.
                    # Record the failure, but do not diagnose it again.
                    if time.time() - last_heal < HEAL_DEBOUNCE_SECONDS:
                        print(f"[STUDIO]   Log confirms: {failure['selector']} "
                              "(already diagnosed)")
                        continue

                    last_heal = time.time()
                    handle_failure(failure, only=only, headless=headless)
                    print("\n[WATCH]    Listening again...")
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\n[WATCH]    Stopped.")


def replay_last(log_path: Path, *, only: str | None = None, headless: bool = True) -> None:
    """Heal from the most recent failure already in the log."""
    text, _ = read_new_text(log_path, 0)
    failures = find_failures(text)
    if not failures:
        print(f"[REPLAY]   No element-lookup failures found in {log_path}.")
        return
    ensure_server()
    handle_failure(failures[-1], only=only, headless=headless)


def main(argv=None) -> int:
    """Command line entry point."""
    try:
        # Line buffering matters here: this runs for the length of a demo and
        # its output is the only sign it is alive.
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(
        prog="studio-watcher",
        description="Detect IBM RPA Studio failures and heal the bot that caused them.",
    )
    parser.add_argument("--bot", help="only heal this bot id")
    parser.add_argument("--log", help="path to Studio.log")
    parser.add_argument("--replay", action="store_true",
                        help="heal from the last failure already in the log, then exit")
    parser.add_argument("--from-start", action="store_true",
                        help="scan the whole log rather than only new entries")
    parser.add_argument("--show", action="store_true",
                        help="run the verification browser with a visible window")
    args = parser.parse_args(argv)

    try:
        log_path = find_log(args.log)
    except FileNotFoundError as error:
        print(f"[ERROR]    {error}")
        return 1

    if args.replay:
        replay_last(log_path, only=args.bot, headless=not args.show)
    else:
        watch(log_path, only=args.bot, from_start=args.from_start, headless=not args.show)
    return 0


if __name__ == "__main__":
    sys.exit(main())

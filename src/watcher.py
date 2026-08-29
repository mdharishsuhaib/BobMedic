"""
watcher.py — records green runs and reports broken ones.

Two jobs, and the first one matters more than it looks:

1. On every **successful** run, fingerprint each element the bot touched and
   save a DOM snapshot. Without that record there is nothing to compare a
   broken page against, and the whole diagnosis is guesswork.

2. On a failed run, emit a FailureEvent in the frozen shape the engine reads.
"""

import time
from pathlib import Path

from contracts import FailureEvent, read_json, write_json
from registry import get_bot, step_names
from runner import run_wal
from serve import ensure_server

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FINGERPRINT_DIR = PROJECT_ROOT / "fingerprints"
INCIDENT_DIR = PROJECT_ROOT / "incidents"


def new_run_id() -> str:
    """Allocate a run id of the form ``run-0042``."""
    INCIDENT_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(INCIDENT_DIR.glob("run-*.failure.json"))
    return f"run-{len(existing) + 1:04d}"


def fingerprint_path(bot_id: str) -> Path:
    """Where a bot's fingerprint record lives."""
    return FINGERPRINT_DIR / f"{bot_id}.json"


def load_fingerprints(bot_id: str) -> dict:
    """
    Load the fingerprints recorded on this bot's last green run.

    Returns:
        ``{step_id: fingerprint}``; empty when the bot has never run green.
    """
    stored = read_json(fingerprint_path(bot_id), default=None)
    return (stored or {}).get("steps", {})


def record_baseline(bot_id: str, *, headless: bool = True) -> dict:
    """
    Run a bot against the healthy site and record what it touched.

    Returns:
        The run outcome from the runner, with ``fingerprint_file`` added.
    """
    bot = get_bot(bot_id)
    base_url = ensure_server()
    run_id = f"baseline-{bot_id}"

    outcome = run_wal(
        bot["wal_path"],
        run_id=run_id,
        breaks={},
        step_names=step_names(bot),
        capture_fingerprints=True,
        base_url=base_url,
        headless=headless,
    )

    if not outcome["success"]:
        failed = outcome["failed_step"] or {}
        raise RuntimeError(
            f"Baseline run for '{bot_id}' failed at step "
            f"{failed.get('step_id')} ({failed.get('error')}). "
            "Reset the target site in break.html and try again."
        )

    record = {
        "bot_id": bot_id,
        "bot_name": bot["bot_name"],
        "wal": bot["wal"],
        "risk_tier": bot["risk_tier"],
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "green_snapshot": outcome["snapshot"],
        "duration_sec": outcome["duration_sec"],
        "steps": outcome["fingerprints"],
    }
    outcome["fingerprint_file"] = write_json(fingerprint_path(bot_id), record)
    return outcome


def watch_run(bot_id: str, *, breaks: dict | None = None, headless: bool = True) -> dict:
    """
    Execute a bot and report what happened.

    Returns:
        ``{"run_id", "bot": bot, "outcome": run outcome, "failure": FailureEvent | None}``
        The failure event is also written to ``incidents/<run_id>.failure.json``.
    """
    bot = get_bot(bot_id)
    base_url = ensure_server()
    run_id = new_run_id()

    outcome = run_wal(
        bot["wal_path"],
        run_id=run_id,
        breaks=breaks or {},
        step_names=step_names(bot),
        capture_fingerprints=outcome_should_fingerprint(breaks),
        base_url=base_url,
        headless=headless,
    )

    failure = None
    if not outcome["success"]:
        failed = outcome["failed_step"]
        failure = FailureEvent(
            run_id=run_id,
            bot_id=bot_id,
            risk_tier=bot["risk_tier"],
            failed_step=failed["step_id"],
            error=failed["error"],
            script_line=failed["line_number"],
            page_html_ref=outcome["snapshot"],
        )
        write_json(INCIDENT_DIR / f"{run_id}.failure.json", failure.to_dict())
    elif outcome["fingerprints"]:
        # A green run refreshes the baseline: today's healthy page is what
        # tomorrow's break gets compared against.
        record = read_json(fingerprint_path(bot_id), default={}) or {}
        record.update({
            "bot_id": bot_id,
            "bot_name": bot["bot_name"],
            "wal": bot["wal"],
            "risk_tier": bot["risk_tier"],
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "green_snapshot": outcome["snapshot"],
            "steps": outcome["fingerprints"],
        })
        write_json(fingerprint_path(bot_id), record)

    return {"run_id": run_id, "bot": bot, "outcome": outcome, "failure": failure}


def outcome_should_fingerprint(breaks: dict | None) -> bool:
    """
    Fingerprint only runs expected to be green.

    Recording against a page that is already broken would poison the baseline
    with the very state the engine is meant to detect.
    """
    return not any((breaks or {}).values())


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "invoice-extract"
    result = record_baseline(target)
    print(f"Baseline recorded for {target} in {result['duration_sec']}s")
    for step_id, fingerprint in result["fingerprints"].items():
        print(f"  {step_id:<22} <{fingerprint['tag']}> "
              f"'{fingerprint['text']}' id={fingerprint['attrs'].get('id', '—')}")

"""
runner.py — replays a .wal script against the target site.

This is the execution surface BotMedic observes. It is deliberately a real
browser run rather than a text check: a patch is only trustworthy if the bot
actually reaches the end of its script with the new selector in place.

Supported WAL commands: webStart, webNavigate, webSet, webClick, webWait,
webSelect, webAssert, webHover, webGet, webClose. Anything else is skipped,
the same way an unrelated statement would be irrelevant to a selector break.
"""

import json
import re
import time
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright

from fingerprint import DESCRIBE_JS, collect_candidates
from parser import parse_wal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DIR = PROJECT_ROOT / "snapshots"

# The target site keeps one localStorage key per break, holding the string
# 'true' or 'false'. That format belongs to the target app, not to us — the
# engine writes what the site reads.
BREAK_KEYS = (
    "break_login_id",
    "break_login_move",
    "break_login_text",
    "break_export_id",
)
DEFAULT_STEP_TIMEOUT_MS = 4000


def _timeout_ms(step, default=DEFAULT_STEP_TIMEOUT_MS) -> int:
    """Convert a WAL ``--timeout "00:00:05"`` argument to milliseconds."""
    raw = step.args.get("timeout")
    if not raw:
        return default
    try:
        hours, minutes, seconds = (int(part) for part in raw.split(":"))
        total = (hours * 3600 + minutes * 60 + seconds) * 1000
        return total or default
    except ValueError:
        return default


def _break_script(breaks: dict) -> str:
    """
    Build an init script that puts the break flags where the site looks.

    Every known key is written on every run, so a break switched off in one run
    is actually cleared rather than left over from the last one.
    """
    breaks = breaks or {}
    sets = "".join(
        f"localStorage.setItem({json.dumps(key)}, "
        f"{json.dumps('true' if breaks.get(key) else 'false')});"
        for key in BREAK_KEYS
    )
    return f"try {{ {sets} }} catch (e) {{}}"


def _save_snapshot(page, run_id: str, base_url: str) -> str:
    """
    Save the current DOM to snapshots/<run_id>.html.

    Two things are done to the serialised DOM, and both matter:

    * a <base> tag is injected, so the snapshot still resolves the site's own
      stylesheet when it is re-opened for scoring — geometry signals are
      worthless against an unstyled page;
    * <script> blocks are removed. The snapshot is a record of the DOM at the
      moment the bot failed, and the target app builds its buttons at runtime:
      leaving the scripts in would let a re-opened snapshot rebuild itself into
      the healthy page and quietly erase the very break being diagnosed.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    html = page.content()
    html = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    base_tag = f'<base href="{base_url}">'
    if "<head>" in html:
        html = html.replace("<head>", "<head>" + base_tag, 1)
    else:
        html = base_tag + html

    path = SNAPSHOT_DIR / f"{run_id}.html"
    path.write_text(html, encoding="utf-8")
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def _execute_step(page, step, timeout: int):
    """Run one WAL step. Raises PlaywrightError when the element is missing."""
    command = step.command
    selector = step.selector_value

    if command == "webnavigate":
        page.goto(step.args.get("url", ""), wait_until="domcontentloaded")
        page.wait_for_timeout(120)
        return

    if command in ("webstart", "webclose"):
        return

    locator = page.locator(selector).first

    if command == "webset":
        locator.wait_for(state="visible", timeout=timeout)
        locator.fill(step.args.get("value", ""))
    elif command == "webclick":
        locator.wait_for(state="visible", timeout=timeout)
        locator.click()
        page.wait_for_timeout(200)
    elif command in ("webwait", "webassert"):
        locator.wait_for(state="visible", timeout=timeout)
    elif command == "webhover":
        locator.wait_for(state="visible", timeout=timeout)
        locator.hover()
    elif command == "webselect":
        locator.wait_for(state="visible", timeout=timeout)
        locator.select_option(step.args.get("value", ""))
    elif command == "webget":
        locator.wait_for(state="visible", timeout=timeout)
        locator.inner_text()


def _classify_error(error: Exception) -> str:
    """Map a Playwright failure onto the error vocabulary the dashboard shows."""
    message = str(error).lower()
    if "timeout" in message and "waiting for" in message:
        return "ElementNotFound"
    if "strict mode violation" in message:
        return "AmbiguousSelector"
    if "not visible" in message or "hidden" in message:
        return "ElementNotVisible"
    if "net::" in message or "navigation" in message:
        return "NavigationFailed"
    return "ElementNotFound"


def run_wal(
    wal_path: str,
    run_id: str,
    *,
    breaks: Optional[dict] = None,
    step_names: Optional[dict] = None,
    capture_fingerprints: bool = False,
    base_url: str = "http://127.0.0.1:8000",
    headless: bool = True,
) -> dict:
    """
    Replay a .wal script end to end.

    Args:
        wal_path:             Script to run.
        run_id:               Identifier used to name the DOM snapshot.
        breaks:               Break flags to inject into the target site.
        step_names:           Map of ordinal step key -> human step id.
        capture_fingerprints: Record an element fingerprint per selector step.
                              Only meaningful on a run expected to succeed.
        base_url:             Site origin, injected into saved snapshots.
        headless:             Run the browser without a window.

    Returns:
        {
          "success":      bool,
          "steps":        [ {step_key, step_id, line_number, command, selector, ok, error} ],
          "failed_step":  step dict or None,
          "fingerprints": {step_id: fingerprint},
          "snapshot":     "snapshots/<run_id>.html" or None,
          "duration_sec": float,
        }
    """
    step_names = step_names or {}
    steps = parse_wal(wal_path)
    started = time.time()

    results = []
    fingerprints = {}
    failed_step = None
    snapshot_ref = None

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        context.add_init_script(_break_script(breaks))
        page = context.new_page()

        for step in steps:
            step_id = step_names.get(step.step_key, step.step_key)
            record = {
                "step_key": step.step_key,
                "step_id": step_id,
                "line_number": step.line_number,
                "command": step.command,
                "selector": step.selector_value,
                "ok": True,
                "error": None,
            }

            try:
                # The fingerprint is taken before the step runs: a click can
                # navigate away, and the element must be described as the bot
                # found it.
                if capture_fingerprints and step.has_selector:
                    locator = page.locator(step.selector_value).first
                    locator.wait_for(state="visible", timeout=_timeout_ms(step))
                    described = locator.evaluate(DESCRIBE_JS)
                    described.update({
                        "step_id": step_id,
                        "step_key": step.step_key,
                        "selector": step.selector_value,
                        "line_number": step.line_number,
                        "url": page.url,
                    })
                    fingerprints[step_id] = described

                _execute_step(page, step, _timeout_ms(step))
            except Exception as error:  # noqa: BLE001
                record["ok"] = False
                record["error"] = _classify_error(error)
                record["error_detail"] = str(error).split("\n")[0][:300]
                results.append(record)
                failed_step = record
                snapshot_ref = _save_snapshot(page, run_id, base_url)
                break

            results.append(record)

        if failed_step is None:
            # Green run: the snapshot is the reference the next break is scored against.
            snapshot_ref = _save_snapshot(page, run_id, base_url)

        browser.close()

    return {
        "success": failed_step is None,
        "steps": results,
        "failed_step": failed_step,
        "fingerprints": fingerprints,
        "snapshot": snapshot_ref,
        "duration_sec": round(time.time() - started, 2),
    }


def count_matches(
    url: str,
    selectors: list[str],
    *,
    breaks: Optional[dict] = None,
    headless: bool = True,
) -> dict:
    """
    Count how many elements each selector matches on the page.

    A replacement selector that matches two elements is not a fix: the bot
    would click whichever came first and the failure would move somewhere
    harder to see.
    """
    counts = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        context.add_init_script(_break_script(breaks))
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(150)
        for selector in selectors:
            try:
                counts[selector] = page.locator(selector).count()
            except Exception:  # noqa: BLE001 - an invalid selector counts as zero
                counts[selector] = 0
        browser.close()
    return counts


def scan_page(url: str, *, breaks: Optional[dict] = None, headless: bool = True) -> list[dict]:
    """
    Open a page and describe every interactive element on it.

    Used by the diagnoser to build the candidate pool after a break.
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        context.add_init_script(_break_script(breaks))
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(150)
        candidates = collect_candidates(page)
        browser.close()
    return candidates


if __name__ == "__main__":
    import sys

    from serve import ensure_server

    script = sys.argv[1] if len(sys.argv) > 1 else str(PROJECT_ROOT / "rpa-bots/invoice-extract.wal")
    ensure_server()
    outcome = run_wal(script, run_id="run-manual", capture_fingerprints=True)
    print(json.dumps(
        {k: v for k, v in outcome.items() if k != "fingerprints"},
        indent=2,
    ))



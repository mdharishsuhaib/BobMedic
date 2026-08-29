"""
patcher.py — writes the patch, proves it, and never touches the original.

A patch is written to a copy of the .wal script, the bot is re-run against the
changed page, and only a run that reaches the end of the script counts as
verified. If the first candidate fails verification, the next one is tried
before anything is reported as fixed.

The original script is modified only by an explicit commit — from an approval
in the dashboard, or from an automatic apply on a read_only bot.
"""

import shutil
from pathlib import Path
from typing import Optional

from diagnoser import selector_options
from parser import diff_wal, patch_wal
from registry import step_names
from runner import count_matches, run_wal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANDIDATE_DIR = PROJECT_ROOT / "patch-candidates"


def choose_selector(
    candidate: dict,
    page_url: str,
    *,
    breaks: Optional[dict] = None,
) -> Optional[dict]:
    """
    Pick the most stable selector for a candidate that matches it uniquely.

    Args:
        candidate: The winning element description from the diagnoser.
        page_url:  Page to test the selectors against.
        breaks:    Break flags, so the test sees the page as the bot did.

    Returns:
        ``{"selector", "basis", "matches"}`` or None when nothing resolves
        to exactly one element.
    """
    options = selector_options(candidate)
    if not options:
        return None

    counts = count_matches(page_url, [option["selector"] for option in options], breaks=breaks)
    for option in options:
        if counts.get(option["selector"]) == 1:
            return {**option, "matches": 1}
    return None


def verify_patch(
    bot: dict,
    run_id: str,
    line_number: int,
    old_selector: str,
    new_selector: str,
    *,
    breaks: Optional[dict] = None,
    headless: bool = True,
) -> dict:
    """
    Apply one candidate selector to a copy of the script and re-run the bot.

    Returns:
        ``{"patched_wal", "diff", "run_result", "verified", "error"}``
    """
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    patched_path = CANDIDATE_DIR / f"{run_id}.{Path(bot['wal']).name}"

    try:
        patch_wal(
            bot["wal_path"],
            line_number,
            old_selector,
            new_selector,
            out_path=str(patched_path),
        )
    except ValueError as error:
        return {
            "patched_wal": None,
            "diff": [],
            "run_result": None,
            "verified": False,
            "error": str(error),
        }

    diff = diff_wal(bot["wal_path"], str(patched_path))

    outcome = run_wal(
        str(patched_path),
        run_id=f"{run_id}-verify",
        breaks=breaks or {},
        step_names=step_names(bot),
        capture_fingerprints=False,
        headless=headless,
    )

    failed = outcome.get("failed_step") or {}
    return {
        "patched_wal": str(patched_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "diff": diff,
        "run_result": {
            "success": outcome["success"],
            "duration_sec": outcome["duration_sec"],
            "steps_run": len(outcome["steps"]),
            "failed_step": failed.get("step_id"),
            "error": failed.get("error"),
        },
        "verified": outcome["success"],
        "error": None if outcome["success"] else
                 f"Re-run still failed at {failed.get('step_id')} ({failed.get('error')})",
    }


def verify_candidates(
    bot: dict,
    run_id: str,
    line_number: int,
    old_selector: str,
    ranked_candidates: list[dict],
    page_url: str,
    *,
    breaks: Optional[dict] = None,
    max_attempts: int = 2,
    headless: bool = True,
) -> dict:
    """
    Try candidates in rank order until one survives a re-run.

    Args:
        ranked_candidates: Best-first candidates from the diagnoser.
        max_attempts:      How many candidates to try before giving up.

    Returns:
        ``{"verified", "attempts": [...], "winner": attempt | None}``
    """
    attempts = []

    for candidate in ranked_candidates[:max_attempts]:
        chosen = choose_selector(candidate, page_url, breaks=breaks)
        if not chosen:
            attempts.append({
                "candidate_score": candidate.get("score"),
                "selector": None,
                "verified": False,
                "error": "No selector matched this candidate uniquely.",
            })
            continue

        result = verify_patch(
            bot, run_id, line_number, old_selector, chosen["selector"],
            breaks=breaks, headless=headless,
        )
        attempt = {
            "candidate_score": candidate.get("score"),
            "selector": chosen["selector"],
            "basis": chosen["basis"],
            **result,
        }
        attempts.append(attempt)

        if result["verified"]:
            return {"verified": True, "attempts": attempts, "winner": attempt}

    return {"verified": False, "attempts": attempts, "winner": None}


def commit_patch(bot: dict, patched_wal: str) -> dict:
    """
    Replace the bot's script with a verified patch, keeping a .bak of the original.

    Called on approval, or automatically for a read_only bot. Never called for
    an irreversible one.
    """
    original = Path(bot["wal_path"])
    patched = PROJECT_ROOT / patched_wal
    backup = original.with_suffix(original.suffix + ".bak")

    if not patched.exists():
        raise FileNotFoundError(f"Patched script not found: {patched}")

    if not backup.exists():
        shutil.copy2(original, backup)
    shutil.copy2(patched, original)

    return {
        "committed": True,
        "script": str(original.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "backup": str(backup.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }


def revert_patch(bot: dict) -> dict:
    """Restore a bot's script from its .bak backup."""
    original = Path(bot["wal_path"])
    backup = original.with_suffix(original.suffix + ".bak")
    if not backup.exists():
        return {"reverted": False, "reason": "No backup on file."}
    shutil.copy2(backup, original)
    return {"reverted": True, "script": str(original.relative_to(PROJECT_ROOT))}

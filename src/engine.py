"""
engine.py — the closed loop.

    run the bot -> detect the failure -> rank candidates -> escalate to Bob
    only if ambiguous -> verify by re-running -> check the risk tier ->
    present the diff to a human

The risk tier is checked before any patch is surfaced, and an irreversible bot
is never patched — it is diagnosed, then deliberately refused.
"""

import argparse
import re
import sys
import time
from pathlib import Path

from contracts import (
    AMBIGUOUS_THRESHOLD,
    CONFIDENT_THRESHOLD,
    PatchProposal,
    incident_record,
    read_json,
    write_json,
)
from diagnoser import diagnose
from parser import parse_wal
from patcher import commit_patch, verify_candidates
from registry import get_bot, load_bots
from runner import scan_page
from serve import ensure_server
from watcher import INCIDENT_DIR, load_fingerprints, record_baseline, watch_run

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEED_PATH = PROJECT_ROOT / "dashboard" / "public" / "incidents.json"

# Break scenarios the demo can apply to the target site.
#
# Renaming an id is what actually breaks an id-based selector. Changing the
# button text or moving it only breaks a bot that has already been healed onto
# a text- or path-based selector, so those scenarios pair the change with the
# rename to reproduce the harder case in one run.
BREAK_SCENARIOS = {
    "rename-login-id": {
        "breaks": {"break_login_id": True},
        "description": "The sign-in button id changes. Everything else stays put.",
    },
    "rename-export-id": {
        "breaks": {"break_export_id": True},
        "description": "The CSV export button id changes on the invoice page.",
    },
    "login-text-change": {
        "breaks": {"break_login_id": True, "break_login_text": True},
        "description": "The button is renamed and its text becomes 'Login' - "
                       "the ambiguous case only meaning can settle.",
    },
    "login-moved": {
        "breaks": {"break_login_id": True, "break_login_move": True},
        "description": "The button is renamed and moves into another container.",
    },
}

STATUS_FOR_ACTION = {
    "auto_applied": "healed",
    "await_approval": "awaiting_approval",
    "escalated_no_fix": "escalated",
    "blocked_risk_tier": "escalated",
}


# ── Helpers ───────────────────────────────────────────────────────

def _snapshot_url(page_html_ref: str) -> str:
    """File URL for a saved DOM snapshot."""
    return (PROJECT_ROOT / page_html_ref).resolve().as_uri()


def _context_html(page_html_ref: str, limit: int = 4000) -> str:
    """Readable markup from a snapshot, for the Bob prompt only."""
    path = PROJECT_ROOT / page_html_ref
    if not path.exists():
        return ""
    html = path.read_text(encoding="utf-8", errors="ignore")
    html = re.sub(r"<script[\s\S]*?</script>", "", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", "", html, flags=re.IGNORECASE)
    return re.sub(r"\n\s*\n", "\n", html)[:limit]


def _selector_at(wal_path: str, line_number: int) -> str | None:
    """Read the selector currently written on one line of a script."""
    for step in parse_wal(wal_path):
        if step.line_number == line_number:
            return step.selector_value
    return None


def incident_path(run_id: str) -> Path:
    """Where one incident record is stored."""
    return INCIDENT_DIR / f"{run_id}.incident.json"


def load_incidents() -> list[dict]:
    """All incidents, newest first."""
    INCIDENT_DIR.mkdir(parents=True, exist_ok=True)
    incidents = []
    for path in INCIDENT_DIR.glob("*.incident.json"):
        record = read_json(path)
        if record:
            incidents.append(record)
    incidents.sort(key=lambda item: item.get("detected_at", ""), reverse=True)
    return incidents


def _with_breaks(incident: dict, breaks: dict | None) -> dict:
    """Remember which UI changes were active, so a re-run faces the same page."""
    incident["breaks"] = breaks or {}
    return incident


def save_incident(incident: dict) -> dict:
    """Persist one incident and refresh the dashboard feed."""
    write_json(incident_path(incident["id"]), incident)
    publish_feed()
    return incident


def publish_feed() -> str:
    """Write every incident to the file the dashboard reads."""
    incidents = load_incidents()
    healed = [item for item in incidents if item.get("status") == "healed"]
    manual_minutes = [item["mttr_manual_min"] for item in incidents if item.get("mttr_manual_min")]
    auto_seconds = [item["mttr_auto_sec"] for item in incidents if item.get("mttr_auto_sec")]

    feed = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "thresholds": {
            "confident": CONFIDENT_THRESHOLD,
            "ambiguous": AMBIGUOUS_THRESHOLD,
        },
        "summary": {
            "incidents": len(incidents),
            "healed": len(healed),
            "awaiting_approval": len([i for i in incidents if i["status"] == "awaiting_approval"]),
            "escalated": len([i for i in incidents if i["status"] == "escalated"]),
            "avg_manual_min": round(sum(manual_minutes) / len(manual_minutes), 1) if manual_minutes else 0,
            "avg_auto_sec": round(sum(auto_seconds) / len(auto_seconds), 1) if auto_seconds else 0,
            "bob_calls": len([i for i in incidents if i.get("resolved_by") == "bob"]),
        },
        "bots": [
            {
                "bot_id": bot_id,
                "bot_name": bot["bot_name"],
                "risk_tier": bot["risk_tier"],
                "description": bot["description"],
                "wal": bot["wal"],
            }
            for bot_id, bot in load_bots().items()
        ],
        "incidents": incidents,
    }
    return write_json(FEED_PATH, feed)


# ── The loop ──────────────────────────────────────────────────────

def heal(bot_id: str, breaks: dict | None = None, *, headless: bool = True) -> dict:
    """
    Run one bot against the current site and heal it if it breaks.

    Returns:
        The incident record, or ``{"status": "green", ...}`` when the bot ran
        clean and there was nothing to heal.
    """
    started = time.time()
    bot = get_bot(bot_id)
    ensure_server()

    print(f"[RUN]      {bot['bot_name']}  (risk tier: {bot['risk_tier']})")
    watched = watch_run(bot_id, breaks=breaks, headless=headless)
    run_id = watched["run_id"]
    failure = watched["failure"]

    if failure is None:
        print(f"[GREEN]    Bot completed. Baseline refreshed.")
        return {"status": "green", "run_id": run_id, "bot_id": bot_id}

    print(f"[FAILED]   {failure.failed_step} — {failure.error} at line {failure.script_line}")
    print(f"[SNAPSHOT] {failure.page_html_ref}")

    fingerprints = load_fingerprints(bot_id)
    fingerprint = fingerprints.get(failure.failed_step)
    if not fingerprint:
        return save_incident(_with_breaks(_no_baseline_incident(bot, failure, started), breaks))

    # The selector that just failed is read from the script, not from the
    # fingerprint: an earlier heal may already have rewritten that line.
    current_selector = _selector_at(bot["wal_path"], failure.script_line)                        or fingerprint["selector"]

    snapshot_url = _snapshot_url(failure.page_html_ref)
    candidates = scan_page(snapshot_url, headless=headless)
    print(f"[RANK]     {len(candidates)} interactive elements on the changed page")

    result = diagnose(
        broken_selector=current_selector,
        fingerprint=fingerprint,
        candidates=candidates,
        context_html=_context_html(failure.page_html_ref),
    )
    print(f"[SCORE]    top={result['confidence']:.2f} band={result['band']} "
          f"resolved_by={result['resolved_by']}")

    # ── Risk gate: checked before any patch is surfaced ────────────
    if bot["risk_tier"] == "irreversible":
        print("[BLOCKED]  Irreversible bot — diagnosed, refusing to patch.")
        return save_incident(_with_breaks(_blocked_incident(bot, failure, result, started), breaks))

    if not result["match"]:
        print("[ESCALATE] No candidate is good enough to propose.")
        return save_incident(_with_breaks(_escalated_incident(bot, failure, result, started), breaks))

    print("[VERIFY]   Patching a copy and re-running the bot to prove it works...")
    # The chosen match is tried first — it may be Bob's pick rather than the
    # top-scored one. The runner-up is the fallback the spec asks for.
    attempt_order = [result["match"]] + [
        item for item in result["ranked"]
        if item is not result["match"] and item.get("score", 0) >= AMBIGUOUS_THRESHOLD
    ]

    verification = verify_candidates(
        bot,
        run_id,
        failure.script_line,
        current_selector,
        attempt_order,
        snapshot_url,
        breaks=breaks,
        headless=headless,
    )

    if not verification["verified"]:
        print("[ESCALATE] No candidate survived verification.")
        return save_incident(_with_breaks(
            _escalated_incident(bot, failure, result, started, verification), breaks
        ))

    winner = verification["winner"]
    print(f"[VERIFIED] {winner['selector']}  ({winner['basis']})")

    auto = bot["risk_tier"] == "read_only" and result["confidence"] >= CONFIDENT_THRESHOLD
    action = "auto_applied" if auto else "await_approval"

    if auto:
        commit = commit_patch(bot, winner["patched_wal"])
        print(f"[APPLIED]  {commit['script']} (backup: {commit['backup']})")
    else:
        print("[HOLD]     Verified patch is waiting for human approval.")

    proposal = PatchProposal(
        run_id=run_id,
        diagnosis=result["diagnosis"],
        script_line=failure.script_line,
        old_selector=current_selector,
        new_selector=winner["selector"],
        confidence=result["confidence"],
        resolved_by=result["resolved_by"],
        verified=True,
        action=action,
    )

    incident = incident_record(
        proposal=proposal,
        failure=failure,
        bot_name=bot["bot_name"],
        wal_file=bot["wal"],
        diff=winner["diff"],
        candidates=_candidate_summary(result["ranked"]),
        run_result=winner["run_result"],
        mttr_manual_min=bot["mttr_manual_min"],
        mttr_auto_sec=round(time.time() - started, 1),
        status=STATUS_FOR_ACTION[action],
        bob_response=result["bob_response"],
    )
    incident["selector_basis"] = winner["basis"]
    incident["patched_wal"] = winner["patched_wal"]
    incident["verification_attempts"] = len(verification["attempts"])
    return save_incident(_with_breaks(incident, breaks))


def _candidate_summary(ranked: list[dict]) -> list[dict]:
    """Trim the ranked list down to what the dashboard shows."""
    return [
        {
            "tag": item.get("tag"),
            "text": item.get("text"),
            "attrs": item.get("attrs"),
            "dom_path": item.get("dom_path"),
            "score": item.get("score"),
            "signals": item.get("signals"),
        }
        for item in ranked[:5]
    ]


def _blocked_incident(bot, failure, result, started) -> dict:
    """The refusal record for an irreversible bot."""
    would_be = result["match"]
    proposal = PatchProposal(
        run_id=failure.run_id,
        diagnosis=(
            f"{result['diagnosis']} This bot is classed irreversible, so no patch was "
            "written, verified, or applied — the break is reported to an operator instead."
        ),
        script_line=failure.script_line,
        old_selector=result["broken_selector"],
        new_selector=None,
        confidence=result["confidence"],
        resolved_by=None,
        verified=False,
        action="blocked_risk_tier",
    )
    incident = incident_record(
        proposal=proposal,
        failure=failure,
        bot_name=bot["bot_name"],
        wal_file=bot["wal"],
        diff=[],
        candidates=_candidate_summary(result["ranked"]),
        run_result=None,
        mttr_manual_min=bot["mttr_manual_min"],
        mttr_auto_sec=None,
        status="escalated",
        bob_response=result["bob_response"],
    )
    incident["withheld_candidate"] = {
        "tag": would_be.get("tag"),
        "text": would_be.get("text"),
        "attrs": would_be.get("attrs"),
        "score": would_be.get("score"),
    } if would_be else None
    return incident


def _escalated_incident(bot, failure, result, started, verification=None) -> dict:
    """No fix could be proposed, or none survived verification."""
    diagnosis = result["diagnosis"]
    if verification is not None:
        failures = [
            attempt.get("error") for attempt in verification["attempts"] if attempt.get("error")
        ]
        diagnosis += " Verification rejected every candidate: " + "; ".join(failures)

    proposal = PatchProposal(
        run_id=failure.run_id,
        diagnosis=diagnosis,
        script_line=failure.script_line,
        old_selector=result["broken_selector"],
        new_selector=None,
        confidence=result["confidence"],
        resolved_by=result["resolved_by"],
        verified=False,
        action="escalated_no_fix",
    )
    incident = incident_record(
        proposal=proposal,
        failure=failure,
        bot_name=bot["bot_name"],
        wal_file=bot["wal"],
        diff=[],
        candidates=_candidate_summary(result["ranked"]),
        run_result=None,
        mttr_manual_min=bot["mttr_manual_min"],
        mttr_auto_sec=round(time.time() - started, 1),
        status="escalated",
        bob_response=result["bob_response"],
    )
    if verification is not None:
        incident["verification_attempts"] = len(verification["attempts"])
    return incident


def _no_baseline_incident(bot, failure, started) -> dict:
    """A bot that broke before it ever ran green cannot be diagnosed."""
    proposal = PatchProposal(
        run_id=failure.run_id,
        diagnosis=(
            f"No fingerprint on file for step '{failure.failed_step}'. The bot has never "
            "completed a green run, so there is nothing to compare the changed page "
            "against. Record a baseline first."
        ),
        script_line=failure.script_line,
        old_selector=None,
        new_selector=None,
        confidence=0.0,
        resolved_by=None,
        verified=False,
        action="escalated_no_fix",
    )
    return incident_record(
        proposal=proposal,
        failure=failure,
        bot_name=bot["bot_name"],
        wal_file=bot["wal"],
        diff=[],
        candidates=[],
        run_result=None,
        mttr_manual_min=bot["mttr_manual_min"],
        mttr_auto_sec=round(time.time() - started, 1),
        status="escalated",
    )


# ── Human decisions ───────────────────────────────────────────────

def assert_approvable(run_id: str) -> dict:
    """
    Check that an incident may be approved, and return it.

    Separated from ``approve`` so a caller can refuse before starting any work
    — the risk tier is a property of the bot, not of the approval click, and
    the operator has to be told no on the request they made.
    """
    incident = read_json(incident_path(run_id))
    if not incident:
        raise KeyError(f"Unknown incident '{run_id}'")
    if incident["risk_tier"] == "irreversible":
        raise PermissionError(
            "Irreversible bots are never auto-patched. Apply the change by hand."
        )
    if not incident.get("patched_wal"):
        raise ValueError("This incident carries no verified patch to apply.")
    return incident


def approve(run_id: str, *, breaks: dict | None = None, headless: bool = True) -> dict:
    """Apply a verified patch to the bot's real script and re-run it."""
    incident = assert_approvable(run_id)

    bot = get_bot(incident["bot_id"])
    commit = commit_patch(bot, incident["patched_wal"])
    # Re-run against the page as it was when the bot broke, not a healthy one:
    # approving a patch has to prove itself against the change that caused it.
    rerun = watch_run(
        incident["bot_id"],
        breaks=breaks if breaks is not None else incident.get("breaks"),
        headless=headless,
    )

    incident["status"] = "healed" if rerun["outcome"]["success"] else "escalated"
    incident["approved_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    incident["commit"] = commit
    incident["rerun"] = {
        "run_id": rerun["run_id"],
        "success": rerun["outcome"]["success"],
        "duration_sec": rerun["outcome"]["duration_sec"],
    }
    incident["proposal"]["action"] = "auto_applied" if rerun["outcome"]["success"] else "escalated_no_fix"
    incident["action"] = incident["proposal"]["action"]
    return save_incident(incident)


def reject(run_id: str, reason: str = "Rejected by operator") -> dict:
    """Discard a proposed patch without touching the bot's script."""
    incident = read_json(incident_path(run_id))
    if not incident:
        raise KeyError(f"Unknown incident '{run_id}'")
    incident["status"] = "rejected"
    incident["rejected_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    incident["reject_reason"] = reason
    return save_incident(incident)


# ── CLI ───────────────────────────────────────────────────────────

def _cmd_baseline(args):
    """Record green-run fingerprints for one bot or all of them."""
    targets = [args.bot] if args.bot else list(load_bots())
    for bot_id in targets:
        outcome = record_baseline(bot_id, headless=not args.show)
        print(f"[BASELINE] {bot_id}: {len(outcome['fingerprints'])} elements "
              f"fingerprinted in {outcome['duration_sec']}s")


def _cmd_demo(args):
    """Break the site, run the bot, and heal it end to end."""
    scenario = BREAK_SCENARIOS.get(args.scenario)
    if scenario is None:
        raise SystemExit(
            f"Unknown scenario '{args.scenario}'. Known: {', '.join(BREAK_SCENARIOS)}"
        )
    breaks = scenario["breaks"]
    print(f"[BREAK]    {args.scenario}: {scenario['description']}")
    incident = heal(args.bot, breaks=breaks, headless=not args.show)
    if incident.get("status") == "green":
        print("[NOTE]     The bot survived this change — nothing to heal.")
        return
    print(f"[INCIDENT] {incident['id']}  status={incident['status']}  "
          f"action={incident['action']}")


def _cmd_run(args):
    """Run one bot against the site as it currently is."""
    incident = heal(args.bot, breaks=None, headless=not args.show)
    print(f"[RESULT]   {incident.get('status')}")


def _cmd_approve(args):
    """Approve a pending patch and re-run the bot."""
    scenario = BREAK_SCENARIOS.get(args.scenario or "")
    incident = approve(args.run_id, breaks=scenario["breaks"] if scenario else None)
    print(f"[APPROVED] {incident['id']} -> {incident['status']}")


def _cmd_restore(args):
    """
    Put healed bot scripts back to their pre-patch selectors.

    Needed between demo runs: once a bot has been healed onto a text-based
    selector, renaming the id no longer breaks it, and the same scenario would
    correctly report that there is nothing to heal.
    """
    from patcher import revert_patch

    targets = [args.bot] if args.bot else list(load_bots())
    for bot_id in targets:
        outcome = revert_patch(get_bot(bot_id))
        if outcome.get("reverted"):
            print(f"[RESTORE]  {bot_id}: {outcome['script']}")
        else:
            print(f"[SKIP]     {bot_id}: {outcome.get('reason', 'nothing to restore')}")


def _cmd_feed(args):
    """Rewrite the dashboard feed from the incidents on disk."""
    print(f"[FEED]     {publish_feed()}")


def _cmd_reset(args):
    """Clear incidents, snapshots and patch candidates."""
    import shutil

    for folder in (INCIDENT_DIR, PROJECT_ROOT / "snapshots", PROJECT_ROOT / "patch-candidates"):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)
    publish_feed()
    print("[RESET]    Incidents, snapshots and patch candidates cleared.")


def main(argv=None):
    """Command line entry point."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(
        prog="botmedic",
        description="BotMedic — self-healing RPA maintenance loop.",
    )
    parser.add_argument("--show", action="store_true",
                        help="run the browser with a visible window")
    sub = parser.add_subparsers(dest="command", required=True)

    baseline = sub.add_parser("baseline", help="record green-run fingerprints")
    baseline.add_argument("bot", nargs="?", help="bot id (default: every bot)")
    baseline.set_defaults(func=_cmd_baseline)

    run = sub.add_parser("run", help="run a bot against the site as it is")
    run.add_argument("bot")
    run.set_defaults(func=_cmd_run)

    demo = sub.add_parser("demo", help="break the site, then heal the bot")
    demo.add_argument("bot")
    demo.add_argument("scenario", choices=list(BREAK_SCENARIOS))
    demo.set_defaults(func=_cmd_demo)

    approve_cmd = sub.add_parser("approve", help="apply a verified patch")
    approve_cmd.add_argument("run_id")
    approve_cmd.add_argument("--scenario", choices=list(BREAK_SCENARIOS),
                             help="break state to re-run against")
    approve_cmd.set_defaults(func=_cmd_approve)

    restore = sub.add_parser("restore", help="undo applied patches on bot scripts")
    restore.add_argument("bot", nargs="?", help="bot id (default: every bot)")
    restore.set_defaults(func=_cmd_restore)

    feed = sub.add_parser("feed", help="rewrite the dashboard feed")
    feed.set_defaults(func=_cmd_feed)

    reset = sub.add_parser("reset", help="clear incidents and snapshots")
    reset.set_defaults(func=_cmd_reset)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())



"""
contracts.py — the frozen data contracts shared across BotMedic components.

Two shapes cross component boundaries and neither may drift:

    FailureEvent    watcher produces  ->  engine consumes
    PatchProposal   engine produces   ->  dashboard consumes

Every value written to disk goes through the builders here so that a typo in a
risk tier or an action never reaches the dashboard as free text.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Enumerations (frozen) ─────────────────────────────────────────

RISK_TIERS = ("read_only", "reversible_write", "irreversible")

ACTIONS = (
    "auto_applied",        # read_only bot, verified, applied without a human
    "await_approval",      # verified patch waiting for a human click
    "escalated_no_fix",    # nothing scored high enough, or verification failed
    "blocked_risk_tier",   # irreversible bot: diagnosed, deliberately not patched
)

RESOLVERS = ("deterministic", "bob")

# ── Confidence thresholds (spec) ──────────────────────────────────

CONFIDENT_THRESHOLD = 0.85   # at or above: deterministic fix, no model call
AMBIGUOUS_THRESHOLD = 0.55   # 0.55 .. 0.85: ask Bob; below: escalate to a human


def utc_now() -> str:
    """Current UTC timestamp in ISO-8601 form."""
    return datetime.now(tz=timezone.utc).isoformat()


class ContractError(ValueError):
    """Raised when a value would violate a frozen contract."""


def _require(value, allowed, field_name):
    """Reject any value outside a frozen enumeration."""
    if value not in allowed:
        raise ContractError(
            f"{field_name}={value!r} is not one of {allowed}"
        )
    return value


# ── Failure event ─────────────────────────────────────────────────

@dataclass
class FailureEvent:
    """A bot step that failed during execution. Produced by the watcher."""

    run_id: str
    bot_id: str
    risk_tier: str
    failed_step: str
    error: str
    script_line: int
    page_html_ref: str
    timestamp: str = field(default_factory=utc_now)

    def __post_init__(self):
        _require(self.risk_tier, RISK_TIERS, "risk_tier")

    def to_dict(self) -> dict:
        """Serialise to the frozen failure-event shape."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FailureEvent":
        """Rebuild a failure event from disk, validating the frozen fields."""
        known = {k: data[k] for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)


# ── Patch proposal ────────────────────────────────────────────────

@dataclass
class PatchProposal:
    """The engine's verdict on one failure. Consumed by the dashboard."""

    run_id: str
    diagnosis: str
    script_line: int
    old_selector: Optional[str]
    new_selector: Optional[str]
    confidence: float
    resolved_by: Optional[str]
    verified: bool
    action: str

    def __post_init__(self):
        _require(self.action, ACTIONS, "action")
        if self.resolved_by is not None:
            _require(self.resolved_by, RESOLVERS, "resolved_by")
        self.confidence = round(float(self.confidence), 4)

    def to_dict(self) -> dict:
        """Serialise to the frozen patch-proposal shape."""
        return asdict(self)


# ── Incident record (proposal + everything the UI needs to show it) ──

def incident_record(
    proposal: PatchProposal,
    failure: FailureEvent,
    bot_name: str,
    wal_file: str,
    diff: list,
    candidates: list,
    run_result: Optional[dict],
    mttr_manual_min: int,
    mttr_auto_sec: Optional[float],
    status: str,
    bob_response: Optional[dict] = None,
) -> dict:
    """
    Compose the dashboard incident: the frozen proposal plus presentation data.

    The proposal is nested untouched under "proposal" so the contract stays
    readable in the file, and flattened alongside it so the dashboard can bind
    without digging.
    """
    return {
        "id": failure.run_id,
        "bot_id": failure.bot_id,
        "bot_name": bot_name,
        "wal_file": wal_file,
        "risk_tier": failure.risk_tier,
        "failed_step": failure.failed_step,
        "error": failure.error,
        "detected_at": failure.timestamp,
        "page_html_ref": failure.page_html_ref,
        "status": status,
        "diff": diff,
        "candidates": candidates,
        "run_result": run_result,
        "bob_response": bob_response,
        "mttr_manual_min": mttr_manual_min,
        "mttr_auto_sec": mttr_auto_sec,
        "proposal": proposal.to_dict(),
        # flattened for convenience in the UI
        "diagnosis": proposal.diagnosis,
        "script_line": proposal.script_line,
        "old_selector": proposal.old_selector,
        "new_selector": proposal.new_selector,
        "confidence": proposal.confidence,
        "resolved_by": proposal.resolved_by,
        "verified": proposal.verified,
        "action": proposal.action,
    }


# ── Strict JSON helpers ───────────────────────────────────────────

def write_json(path, payload) -> str:
    """Write a payload as strict UTF-8 JSON, creating parent directories."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return str(path)


def read_json(path, default=None):
    """Read a JSON file, returning `default` when it is missing or malformed."""
    path = Path(path)
    if not path.exists():
        return default
    try:
        # utf-8-sig: some Windows tooling rewrites these files with a BOM, and a
        # BOM would otherwise make a perfectly good file read as missing.
        with open(path, encoding="utf-8-sig") as handle:
            return json.load(handle)
    except json.JSONDecodeError:
        return default



"""
demo-reset.py — bring BotMedic back to a clean, demo-ready state.

Run this before every demo take:

    python demo-reset.py

What it does:
  1. Restores BobMedic.wal from BobMedic.original.wal (IBM RPA binary, #btn-login)
  2. Clears break-state.json  (all breaks = false)
  3. Removes stale fingerprint
  4. Re-records baseline fingerprint for bobmedic-login (~10 s Playwright run)
  5. Prints a GO / FAIL summary

After this script exits cleanly, follow the 6-step demo flow printed at the end.
"""

import json
import shutil
import sys
import time
from pathlib import Path

PROJECT_ROOT   = Path(__file__).resolve().parent
WAL_PATH       = PROJECT_ROOT / "BobMedic.wal"
WAL_ORIGINAL   = PROJECT_ROOT / "BobMedic.original.wal"
BREAK_STATE    = PROJECT_ROOT / "target-site" / "break-state.json"
FINGERPRINT    = PROJECT_ROOT / "fingerprints" / "bobmedic-login.json"

BREAK_KEYS = (
    "break_login_id",
    "break_login_move",
    "break_login_text",
    "break_export_id",
)


def _step(msg):
    print(f"\n  >> {msg}")

def _ok(msg):
    print(f"    OK  {msg}")

def _fail(msg):
    print(f"    ERR {msg}", file=sys.stderr)


# ── 0. Guard: original must exist ────────────────────────────────
if not WAL_ORIGINAL.exists():
    print("ERROR: BobMedic.original.wal not found.", file=sys.stderr)
    print("       Run this once to create it:", file=sys.stderr)
    print("         python -c \"import shutil; shutil.copy2('BobMedic.wal','BobMedic.original.wal')\"",
          file=sys.stderr)
    print("       Make sure BobMedic.wal currently has #btn-login selectors.", file=sys.stderr)
    sys.exit(1)


# ── 1. Verify the golden master has #btn-login ───────────────────
_step("Checking BobMedic.original.wal (golden master)")

def _read_wal_text(path):
    """Read the text content from an IBM RPA .wal binary file."""
    data = path.read_bytes()
    # IBM RPA format: 0x12 <varint length> <utf-8 content>
    if data[0] == 0x12:
        pos = 1
        result = 0; shift = 0
        while True:
            b = data[pos]; pos += 1
            result |= (b & 0x7f) << shift
            if not (b & 0x80): break
            shift += 7
        return data[pos:].decode("utf-8", errors="replace")
    # Fallback: plain text file
    return data.decode("utf-8", errors="replace")

golden_text = _read_wal_text(WAL_ORIGINAL)
if "#btn-login" not in golden_text:
    _fail(f"BobMedic.original.wal does NOT contain #btn-login!")
    _fail("The golden master is wrong. Manually set BobMedic.wal to #btn-login,")
    _fail("then run: python -c \"import shutil; shutil.copy2('BobMedic.wal','BobMedic.original.wal')\"")
    sys.exit(1)
_ok("Golden master contains #btn-login -- good")


# ── 2. Restore BobMedic.wal ───────────────────────────────────────
_step("Restoring BobMedic.wal from golden master (IBM RPA binary format)")

# Keep a timestamped backup of whatever is there now, for audit trail
if WAL_PATH.exists():
    backup = WAL_PATH.with_suffix(f".bak.{int(time.time())}.wal")
    shutil.copy2(WAL_PATH, backup)
    _ok(f"Current version backed up -> {backup.name}")

# Restore the golden master (binary copy, preserves IBM RPA header)
shutil.copy2(WAL_ORIGINAL, WAL_PATH)

# Verify
restored_text = _read_wal_text(WAL_PATH)
if "#btn-login" in restored_text and "auth-submit" not in restored_text:
    _ok("BobMedic.wal restored -- selector = #btn-login")
else:
    _fail("WAL restore check failed. Please inspect BobMedic.wal manually.")
    sys.exit(1)


# ── 3. Clear break state ──────────────────────────────────────────
_step("Clearing break-state.json (all breaks = false)")

BREAK_STATE.parent.mkdir(parents=True, exist_ok=True)
BREAK_STATE.write_text(
    json.dumps({k: False for k in BREAK_KEYS}, indent=2),
    encoding="utf-8",
)
_ok("break-state.json -> all false")


# ── 4. Clear stale fingerprint ────────────────────────────────────
_step("Removing stale fingerprint (will re-record fresh below)")

if FINGERPRINT.exists():
    FINGERPRINT.unlink()
    _ok("Old fingerprint removed")
else:
    _ok("No old fingerprint found -- clean start")


# ── 5. Re-record baseline fingerprint ────────────────────────────
_step("Re-recording baseline fingerprint (Playwright run -- may take ~10 s)")

sys.path.insert(0, str(PROJECT_ROOT / "src"))
try:
    from watcher import record_baseline
    result = record_baseline("bobmedic-login", headless=True)
    dur = result.get("duration_sec", "?")
    fp_file = result.get("fingerprint_file", "")
    _ok(f"Baseline recorded in {dur}s -> "
        f"{Path(fp_file).name if fp_file else 'fingerprints/bobmedic-login.json'}")
except Exception as exc:
    _fail(f"Baseline recording failed: {exc}")
    _fail("If port 8000 is busy (start.py running), stop it and re-run this script.")
    _fail("If the site is already up and break.html shows all-off, it should still work.")
    sys.exit(1)


# ── 6. Summary ────────────────────────────────────────────────────
print()
print("=" * 60)
print("  BotMedic demo reset COMPLETE")
print("=" * 60)
print()
print("  Bot script : BobMedic.wal  (selector = #btn-login)")
print("  Break state: all off")
print("  Fingerprint: fresh baseline recorded")
print()
print("  Demo flow (6 steps):")
print("  1. python start.py          (site:8000 + api:8100 + dashboard:3000)")
print("  2. Run bot in IBM RPA Studio -> [GREEN] pass")
print("  3. Open http://127.0.0.1:8000/break.html")
print("     -> enable 'Rename login button ID'")
print("  4. Run bot in IBM RPA Studio -> [RED] fails  (ElementNotFound)")
print("  5. In a terminal:")
print("       cd botmedic\\src")
print("       python -c \"from engine import heal; r=heal('bobmedic-login'); print(r['status'])\"")
print("     -> status: healed")
print("  6. Run bot in IBM RPA Studio -> [GREEN] pass")
print()
print("  To reset and repeat: python demo-reset.py")
print()

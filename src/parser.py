"""
parser.py — WAL script reader and patch writer for BotMedic.

Reads an IBM RPA .wal script and returns every executable step with its line
number, so the runner can replay the bot and the patcher can rewrite exactly
one line without touching anything else.

Step identity
-------------
A step is addressed by an ordinal key such as ``webclick#1`` — the first
``webClick`` in the file. Ordinals survive a selector patch, which is why they
are used as the fingerprint key instead of the selector itself. The bot
registry maps an ordinal key to a human step id (``login_submit``).
"""

import os
import re
from dataclasses import dataclass, field
from typing import Optional

# Commands the runner knows how to replay.
WEB_COMMANDS = {
    "webstart", "webnavigate", "webset", "webclick", "webget",
    "webwait", "webwaitelement", "webassert", "webhover", "webselect", "webclose",
}

# Commands that address an element and can therefore break.
SELECTOR_COMMANDS = {
    "webset", "webclick", "webget", "webwait", "webwaitelement", "webassert",
    "webhover", "webselect",
}


@dataclass
class WalStep:
    """A single executable line of a .wal script."""

    line_number: int
    command: str                      # lowercase: webclick, webset, ...
    step_key: str                     # ordinal identity, e.g. "webclick#1"
    selector_type: Optional[str] = None   # CssSelector | XPath
    selector_value: Optional[str] = None  # e.g. "#btn-login"
    args: dict = field(default_factory=dict)
    raw_line: str = ""

    @property
    def has_selector(self) -> bool:
        """True when this step addresses a page element."""
        return bool(self.selector_value)


def _arg(line: str, name: str) -> Optional[str]:
    """Read a --name argument, quoted or bare."""
    quoted = re.search(rf'--{name}\s+"([^"]*)"', line, re.IGNORECASE)
    if quoted:
        return quoted.group(1)
    bare = re.search(rf'--{name}\s+([^\s"]+)', line, re.IGNORECASE)
    return bare.group(1) if bare else None


def _read_wal_lines(wal_path: str) -> tuple[bytes, list[str]]:
    """
    Read an IBM RPA .wal file.

    IBM RPA Studio writes .wal files as:
        0x12  <varint: content length>  <UTF-8 content>

    Returns:
        (header_bytes, lines) where header_bytes is the raw prefix that must
        be preserved when writing back, and lines is the text content split
        into lines (with line endings).
    """
    with open(wal_path, "rb") as fh:
        raw = fh.read()

    # Detect IBM RPA binary format: magic byte 0x12 followed by a varint length
    if raw and raw[0] == 0x12:
        pos = 1
        result = 0
        shift = 0
        while pos < len(raw):
            b = raw[pos]; pos += 1
            result |= (b & 0x7f) << shift
            if not (b & 0x80):
                break
            shift += 7
        header = raw[:pos]
        content = raw[pos:].decode("utf-8", errors="ignore")
    else:
        # Plain-text .wal (e.g. written by older patcher or test fixtures)
        header = b""
        content = raw.decode("utf-8", errors="ignore")

    lines = content.splitlines(keepends=True)
    # splitlines drops a trailing newline — restore it if the content ended with one
    if content and content[-1] in ("\n", "\r"):
        lines.append("")
    return header, lines


def _encode_varint(n: int) -> bytes:
    """Encode a non-negative integer as a protobuf-style varint."""
    out = []
    while True:
        b = n & 0x7f
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _write_wal(out_path: str, header: bytes, lines: list[str]) -> None:
    """Write lines back to a .wal file, re-encoding the length varint."""
    content_bytes = "".join(lines).encode("utf-8")
    if header:
        # header[0] == 0x12 (magic), rest is the old varint — rebuild with new length
        new_header = bytes([0x12]) + _encode_varint(len(content_bytes))
        raw = new_header + content_bytes
    else:
        raw = content_bytes
    with open(out_path, "wb") as fh:
        fh.write(raw)


def parse_wal(wal_path: str) -> list[WalStep]:
    """
    Parse a .wal file into ordered executable steps.

    Args:
        wal_path: Path to the .wal file.

    Returns:
        List of WalStep, in file order.
    """
    steps: list[WalStep] = []
    counters: dict[str, int] = {}

    _header, lines = _read_wal_lines(wal_path)

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip().lstrip("\ufeff\x00 ")
        if not line or line.startswith("//"):
            continue

        tokens = line.split()
        command = tokens[0].lower().lstrip("﻿\x00")
        if command not in WEB_COMMANDS:
            continue

        counters[command] = counters.get(command, 0) + 1
        step_key = f"{command}#{counters[command]}"

        selector_type = _arg(line, "selector")
        selector_value = None
        if selector_type:
            if selector_type.lower() == "cssselector":
                selector_value = _arg(line, "css")
            elif selector_type.lower() == "xpath":
                selector_value = _arg(line, "xpath")

        args = {}
        for name in ("url", "value", "timeout", "name", "type"):
            found = _arg(line, name)
            if found is not None:
                args[name] = found

        steps.append(WalStep(
            line_number=line_number,
            command=command,
            step_key=step_key,
            selector_type=selector_type,
            selector_value=selector_value,
            args=args,
            raw_line=raw_line.rstrip("\n"),
        ))

    return steps


def selector_steps(wal_path: str) -> list[WalStep]:
    """Return only the steps that address an element."""
    return [step for step in parse_wal(wal_path) if step.has_selector]


def find_step(wal_path: str, step_key: str) -> Optional[WalStep]:
    """Look up one step by its ordinal key."""
    for step in parse_wal(wal_path):
        if step.step_key == step_key:
            return step
    return None


def patch_wal(
    wal_path: str,
    line_number: int,
    old_selector: str,
    new_selector: str,
    out_path: Optional[str] = None,
) -> str:
    """
    Write a patched COPY of a .wal file. The original is never modified.

    Patches ALL lines that reference old_selector, not just the failing line.
    This handles the common pattern where webWaitElement and webClick share the
    same selector on consecutive lines — both must be updated together.

    Args:
        wal_path:     Path to the original .wal file.
        line_number:  1-based line where the failure was detected (used for
                      validation — at least this line must be patched).
        old_selector: Selector value to replace everywhere in the file.
        new_selector: Replacement selector value.
        out_path:     Destination; defaults to ``<name>.patched.wal``.

    Returns:
        Path to the patched copy.
    """
    header, lines = _read_wal_lines(wal_path)

    index = line_number - 1
    if index < 0 or index >= len(lines):
        raise ValueError(
            f"Line {line_number} out of range (file has {len(lines)} lines)"
        )

    # Patch every line that contains the broken selector
    patched_lines = []
    patched_count = 0
    for i, line in enumerate(lines):
        new_line = line.replace(f'"{old_selector}"', f'"{new_selector}"')
        if new_line == line:
            new_line = line.replace(old_selector, new_selector)
        if new_line != line:
            patched_count += 1
        patched_lines.append(new_line)

    if patched_count == 0:
        raise ValueError(f"Selector {old_selector!r} not found anywhere in {wal_path}")

    if out_path is None:
        base, ext = os.path.splitext(wal_path)
        out_path = base + ".patched" + ext

    _write_wal(out_path, header, patched_lines)
    return out_path


def diff_wal(original_path: str, patched_path: str) -> list[dict]:
    """
    Compare two .wal files line by line.

    Returns:
        List of ``{line_number, original, patched}`` for each changed line.
    """
    _h1, original_lines = _read_wal_lines(original_path)
    _h2, patched_lines  = _read_wal_lines(patched_path)

    diffs = []
    for line_number, (before, after) in enumerate(
        zip(original_lines, patched_lines), start=1
    ):
        if before != after:
            diffs.append({
                "line_number": line_number,
                "original": before.rstrip("\n").strip("\x00"),
                "patched": after.rstrip("\n").strip("\x00"),
            })
    return diffs


# ── Quick check ───────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else "rpa-bots/invoice-extract.wal"
    parsed = parse_wal(path)
    print(f"{len(parsed)} step(s) in {path}\n")
    for step in parsed:
        target = step.selector_value or step.args.get("url", "")
        print(f"  L{step.line_number:>3} | {step.step_key:<14} | {target}")



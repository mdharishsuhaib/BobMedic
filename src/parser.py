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
from pathlib import Path
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


# ── WAL container format ──────────────────────────────────────────
#
# A .wal saved by IBM RPA Studio is not plain text. It is a small
# protobuf-style container:
#
#     0x12  <varint: body length>  <script body>  0x2A 0x09 "23.0.19.0"
#
# Reading it as text and writing it back destroys three things at once: the
# raw header byte becomes U+FFFD, the length prefix stops matching the body,
# and the version trailer is dropped. Studio then refuses the file with
# "Command not found on line 0". Patching therefore happens on bytes, and the
# length prefix is recomputed.


def _varint_decode(data: bytes, offset: int) -> tuple[int, int]:
    """Decode a varint. Returns (value, bytes consumed)."""
    value = shift = consumed = 0
    while offset + consumed < len(data):
        byte = data[offset + consumed]
        value |= (byte & 0x7F) << shift
        consumed += 1
        if not byte & 0x80:
            return value, consumed
        shift += 7
    raise ValueError("truncated varint in .wal header")


def _varint_encode(value: int) -> bytes:
    """Encode an integer as a varint."""
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def find_version_trailer(raw: bytes) -> int | None:
    """
    Locate the version trailer a Studio .wal ends with: 0x2A <len> "23.0.19.0".

    Used to recognise a script whose container header has been stripped —
    by an editor that saved it as text, say — so the next patch can put the
    header back rather than faithfully preserving the damage.
    """
    marker = raw.rfind(bytes((0x2A,)), max(0, len(raw) - 40))
    if marker == -1 or marker + 1 >= len(raw):
        return None
    length = raw[marker + 1]
    if marker + 2 + length != len(raw):
        return None
    version = raw[marker + 2:]
    if version and all(chr(byte) in "0123456789." for byte in version):
        return marker
    return None


def split_container(raw: bytes) -> tuple[bytes, bytes]:
    """
    Split a .wal into (script body, trailer).

    A plain-text .wal — one written by hand rather than saved by Studio —
    has no container, and is returned unchanged with an empty trailer.
    """
    if not raw.startswith(bytes((0x12,))):
        # No header. If the version trailer is still there, the header was
        # stripped rather than absent, and rebuilding restores a file Studio
        # can open again.
        marker = find_version_trailer(raw)
        if marker is not None:
            return raw[:marker], raw[marker:]
        return raw, b""
    try:
        length, consumed = _varint_decode(raw, 1)
    except ValueError:
        return raw, b""

    start = 1 + consumed
    end = start + length
    if end > len(raw):
        # Length prefix disagrees with the file: treat it as plain text rather
        # than silently truncating someone's script.
        return raw, b""
    return raw[start:end], raw[end:]


def build_container(body: bytes, trailer: bytes) -> bytes:
    """Rebuild a Studio .wal around a modified body, with a correct length."""
    if not trailer:
        return body
    return bytes((0x12,)) + _varint_encode(len(body)) + body + trailer


def patch_wal(
    wal_path: str,
    line_number: int,
    old_selector: str,
    new_selector: str,
    out_path: Optional[str] = None,
) -> str:
    """
    Write a patched COPY of a .wal file. The original is never modified.

    The edit is made on bytes so that a Studio-saved script keeps its container
    header, its version trailer, and every byte on the lines that were not
    touched. Only the length prefix is recomputed, because the body changed.

    Args:
        wal_path:     Path to the original .wal file.
        line_number:  1-based line to patch.
        old_selector: Selector value currently on that line.
        new_selector: Replacement selector value.
        out_path:     Destination; defaults to ``<name>.patched.wal``.

    Returns:
        Path to the patched copy.
    """
    raw = Path(wal_path).read_bytes()
    body, trailer = split_container(raw)

    crlf = bytes((13, 10))
    newline = crlf if crlf in body else bytes((10,))

    lines = body.split(newline)

    index = line_number - 1
    if index < 0 or index >= len(lines):
        raise ValueError(
            f"Line {line_number} out of range (file has {len(lines)} lines)"
        )

    original_line = lines[index]
    old_bytes = old_selector.encode("utf-8")
    new_bytes = new_selector.encode("utf-8")

    patched_line = original_line.replace(b'"' + old_bytes + b'"', b'"' + new_bytes + b'"')
    if patched_line == original_line:
        patched_line = original_line.replace(old_bytes, new_bytes)
    if patched_line == original_line:
        raise ValueError(f"Selector {old_selector!r} not found on line {line_number}")

    lines[index] = patched_line
    patched = build_container(newline.join(lines), trailer)

    if out_path is None:
        base, ext = os.path.splitext(wal_path)
        out_path = base + ".patched" + ext

    Path(out_path).write_bytes(patched)
    return out_path


def patch_selector(
    wal_path: str,
    old_selector: str,
    new_selector: str,
    out_path: Optional[str] = None,
) -> tuple[str, list[int]]:
    """
    Replace a selector everywhere it appears in a script, not just where it failed.

    A renamed id breaks every line that referenced it. Patching only the failing
    step leaves the next one pointing at the same dead selector, and the
    verification re-run then fails a line later — which reads as "no fix found"
    when the fix was simply incomplete.

    Args:
        wal_path:     Path to the original .wal file.
        old_selector: Selector value to replace.
        new_selector: Replacement selector value.
        out_path:     Destination; defaults to ``<name>.patched.wal``.

    Returns:
        ``(path to the patched copy, line numbers changed)``.
    """
    targets = [
        step.line_number
        for step in parse_wal(wal_path)
        if step.selector_value == old_selector
    ]
    if not targets:
        raise ValueError(f"Selector {old_selector!r} appears on no step in {wal_path}")

    raw = Path(wal_path).read_bytes()
    body, trailer = split_container(raw)

    crlf = bytes((13, 10))
    newline = crlf if crlf in body else bytes((10,))
    lines = body.split(newline)

    old_bytes = old_selector.encode("utf-8")
    new_bytes = new_selector.encode("utf-8")
    quoted_old = bytes((34,)) + old_bytes + bytes((34,))
    quoted_new = bytes((34,)) + new_bytes + bytes((34,))

    changed = []
    for line_number in targets:
        index = line_number - 1
        if index < 0 or index >= len(lines):
            continue
        original_line = lines[index]
        patched_line = original_line.replace(quoted_old, quoted_new)
        if patched_line == original_line:
            patched_line = original_line.replace(old_bytes, new_bytes)
        if patched_line != original_line:
            lines[index] = patched_line
            changed.append(line_number)

    if not changed:
        raise ValueError(f"Selector {old_selector!r} could not be replaced in {wal_path}")

    if out_path is None:
        base, ext = os.path.splitext(wal_path)
        out_path = base + ".patched" + ext

    Path(out_path).write_bytes(build_container(newline.join(lines), trailer))
    return out_path, changed


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



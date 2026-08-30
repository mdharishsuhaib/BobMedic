"""
diagnoser.py — ranks candidate elements against a stored fingerprint.

The ranking is plain deterministic code. Most breaks are a renamed id: text,
class, DOM path, position and element type all stay put, the top candidate
scores around 0.9, and no model is called at all.

    score >= 0.85    confident deterministic fix
    0.55 .. 0.85     ambiguous — ask Bob, with the fingerprint, the top three
                     candidates, and their surrounding context
    score <  0.55    escalate to a human; never invent an answer

Signal weights are frozen with the rest of the contracts.
"""

import difflib
import json
import os
import re
import subprocess
import tempfile
from typing import Optional

from contracts import AMBIGUOUS_THRESHOLD, CONFIDENT_THRESHOLD

WEIGHTS = {
    "text": 0.30,
    "attrs": 0.25,
    "dom_path": 0.20,
    "geometry": 0.15,
    "tag": 0.10,
}

# Attributes compared for overlap. `id` is one voice among several rather than
# the deciding one: a renamed id costs a candidate roughly 0.08, which leaves a
# plain rename comfortably above the confident threshold while still showing in
# the number. Everything else here survives a routine UI release.
COMPARED_ATTRS = ("id", "class", "type", "name", "aria-label", "placeholder", "role")

BOB_COMMAND = os.environ.get("BOBMADAK_BOB_CMD", "bob")
BOB_TIMEOUT_SEC = int(os.environ.get("BOBMADAK_BOB_TIMEOUT", "90"))
BOB_ENABLED = os.environ.get("BOBMADAK_BOB_DISABLED", "").lower() not in ("1", "true", "yes")


# ── Individual signals ────────────────────────────────────────────

def _text_score(before: str, after: str) -> float:
    """Visible text similarity."""
    before = (before or "").strip().lower()
    after = (after or "").strip().lower()

    if not before and not after:
        return 0.5           # two unlabelled inputs: neutral, not evidence
    if not before or not after:
        return 0.0
    if before == after:
        return 1.0
    if before in after or after in before:
        return 0.75
    return round(difflib.SequenceMatcher(None, before, after).ratio(), 4)


def _class_overlap(before: str, after: str) -> float:
    """Jaccard overlap of two class attribute strings."""
    first = set((before or "").split())
    second = set((after or "").split())
    if not first and not second:
        return 1.0
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def _attr_score(before: dict, after: dict) -> float:
    """
    Overlap of the stable attributes.

    Each attribute present on either side contributes; class is compared as a
    set so a single added utility class does not wipe the signal out.
    """
    total = 0.0
    counted = 0

    for name in COMPARED_ATTRS:
        left = before.get(name)
        right = after.get(name)
        if left is None and right is None:
            continue
        counted += 1
        if left is None or right is None:
            continue
        if name == "class":
            total += _class_overlap(left, right)
        elif left.strip().lower() == right.strip().lower():
            total += 1.0

    if counted == 0:
        return 0.5
    return round(total / counted, 4)


def _dom_path_score(before: str, after: str) -> float:
    """Similarity of the two DOM paths, segment by segment."""
    if not before or not after:
        return 0.0
    left = before.lower().split(" > ")
    right = after.lower().split(" > ")
    ratio = difflib.SequenceMatcher(None, left, right).ratio()

    # The leaf carries the most meaning: reward an exact leaf match.
    if left[-1] == right[-1]:
        ratio = max(ratio, 0.85)
    return round(ratio, 4)


def _geometry_score(before: dict, after: dict) -> float:
    """Proximity in page position, softened by a size comparison."""
    if not before or not after:
        return 0.5

    dx = before.get("x", 0) - after.get("x", 0)
    dy = before.get("y", 0) - after.get("y", 0)
    distance = (dx ** 2 + dy ** 2) ** 0.5

    if distance < 25:
        position = 1.0
    elif distance < 90:
        position = 0.75
    elif distance < 250:
        position = 0.45
    elif distance < 600:
        position = 0.2
    else:
        position = 0.05

    width_before = max(before.get("w", 0), 1)
    width_after = max(after.get("w", 0), 1)
    height_before = max(before.get("h", 0), 1)
    height_after = max(after.get("h", 0), 1)
    size = (
        min(width_before, width_after) / max(width_before, width_after)
        + min(height_before, height_after) / max(height_before, height_after)
    ) / 2

    return round(position * 0.75 + size * 0.25, 4)


def _tag_score(before: str, after: str) -> float:
    """Element type match."""
    if not before or not after:
        return 0.5
    return 1.0 if before.lower() == after.lower() else 0.0


def score_candidate(fingerprint: dict, candidate: dict) -> dict:
    """
    Score one candidate against the fingerprint.

    Returns:
        ``{"score": float, "signals": {signal: value}}`` — the per-signal
        breakdown is kept so the dashboard can explain the number.
    """
    signals = {
        "text": _text_score(fingerprint.get("text"), candidate.get("text")),
        "attrs": _attr_score(fingerprint.get("attrs", {}), candidate.get("attrs", {})),
        "dom_path": _dom_path_score(fingerprint.get("dom_path"), candidate.get("dom_path")),
        "geometry": _geometry_score(fingerprint.get("geometry", {}), candidate.get("geometry", {})),
        "tag": _tag_score(fingerprint.get("tag"), candidate.get("tag")),
    }
    total = sum(signals[name] * WEIGHTS[name] for name in WEIGHTS)
    return {"score": round(total, 4), "signals": signals}


def rank_candidates(fingerprint: dict, candidates: list[dict]) -> list[dict]:
    """Score every candidate and return them best first."""
    ranked = []
    for candidate in candidates:
        scored = score_candidate(fingerprint, candidate)
        ranked.append({**candidate, **scored})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


# ── Selector proposals ────────────────────────────────────────────

def _quote(value: str) -> str:
    """Quote a value for a CSS attribute or :has-text() selector."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def selector_options(candidate: dict) -> list[dict]:
    """
    Build replacement selectors for a candidate, most stable first.

    Two constraints pull against each other and both are real:

    * the patched .wal has to run in IBM RPA Studio, which takes ordinary CSS
      and has no `:has-text()` — that is a Playwright extension;
    * a selector rebuilt from the id that just changed will break again on the
      next release, which is the whole failure being healed.

    So the ladder prefers selectors that are valid CSS *and* not id-bound, and
    only falls back to the new id when nothing else identifies the element
    uniquely:

    1. data-testid   the app's own stable hook
    2. name (+type)  stable form-field identity
    3. aria-label    tied to meaning, not markup
    4. type + class  valid CSS, survives both a rename and a move
    5. structural    an ancestor id from the DOM path plus the leaf
    6. new id        last resort in valid CSS
    7. has-text      Playwright only; unusable in Studio, so truly last
    """
    tag = candidate.get("tag", "*")
    attrs = candidate.get("attrs", {})
    text = (candidate.get("text") or "").strip()
    element_type = attrs.get("type")
    options: list[dict] = []

    testid = attrs.get("data-testid")
    if testid:
        options.append({
            "selector": f"[data-testid='{_quote(testid)}']",
            "basis": "data-testid attribute — the application's own stable hook",
        })

    name = attrs.get("name")
    if name:
        type_part = f"[type='{_quote(element_type)}']" if element_type else ""
        options.append({
            "selector": f"{tag}[name='{_quote(name)}']{type_part}",
            "basis": "form field name — stable across markup refactors",
        })

    aria = attrs.get("aria-label")
    if aria:
        options.append({
            "selector": f"{tag}[aria-label='{_quote(aria)}']",
            "basis": "accessible label — tied to meaning, not markup",
        })

    classes = [part for part in (attrs.get("class") or "").split() if part]
    class_part = "".join(f".{part}" for part in classes[:2])
    if classes:
        type_part = f"[type='{_quote(element_type)}']" if element_type else ""
        options.append({
            "selector": f"{tag}{class_part}{type_part}",
            "basis": "element type and class — valid CSS, not tied to the id",
        })

    # An ancestor id anchors the element without depending on its own id.
    dom_path = candidate.get("dom_path") or ""
    segments = [seg.strip() for seg in dom_path.split(">") if seg.strip()]
    if len(segments) > 1 and "#" in segments[0]:
        leaf = f"{tag}{class_part}" if classes else tag
        options.append({
            "selector": f"{segments[0]} {leaf}",
            "basis": "position under a stable ancestor id — valid CSS",
        })

    element_id = attrs.get("id")
    if element_id:
        options.append({
            "selector": f"#{element_id}",
            "basis": "the new element id — last resort; it may change again",
        })

    # has-text last — Playwright-only, not supported by IBM RPA Studio
    if text and tag in ("button", "a"):
        base = f"{tag}[type='{_quote(element_type)}']" if element_type else tag
        options.append({
            "selector": f"{base}:has-text('{_quote(text)}')",
            "basis": "visible text plus element type — Playwright only",
        })

    return options


# ── Bob Shell (the only model call in the system) ─────────────────

def _build_bob_prompt(fingerprint: dict, top_candidates: list[dict], context_html: str) -> str:
    """Compose the disambiguation prompt sent to Bob Shell."""
    fingerprint_json = json.dumps(
        {key: fingerprint.get(key) for key in
         ("step_id", "tag", "text", "attrs", "dom_path", "neighbors", "geometry")},
        indent=2, ensure_ascii=False,
    )

    blocks = []
    for index, candidate in enumerate(top_candidates[:3]):
        summary = {key: candidate.get(key) for key in
                   ("tag", "text", "attrs", "dom_path", "neighbors", "geometry", "score", "signals")}
        blocks.append(
            f"Candidate {index}:\n{json.dumps(summary, indent=2, ensure_ascii=False)}"
        )

    return f"""You are the semantic disambiguation step of BotMedic, a self-healing RPA engine.

An RPA bot failed because the element it used to click no longer matches its selector.
Deterministic scoring (text, attributes, DOM path, geometry, element type) put the best
candidate between {AMBIGUOUS_THRESHOLD} and {CONFIDENT_THRESHOLD}, so the decision needs
semantic judgement: the element's wording may have changed while its purpose did not.

ORIGINAL ELEMENT, fingerprinted during the last successful run:
{fingerprint_json}

CANDIDATES on the page as it is now:
{chr(10).join(blocks)}

SURROUNDING PAGE MARKUP:
{context_html[:4000]}

Decide which candidate performs the same user-facing action as the original element.
If none of them does, say so — a wrong patch on a live bot is worse than no patch.

Reply with this JSON object and nothing else:
{{
  "selected_candidate_index": <0, 1, 2, or -1 for no valid match>,
  "confidence": <float between 0.0 and 1.0>,
  "reasoning": "<one sentence, plain English>",
  "risk_note": <string or null>
}}"""


def ask_bob(fingerprint: dict, top_candidates: list[dict], context_html: str = "") -> dict:
    """
    Invoke Bob Shell for the ambiguous band and parse its structured answer.

    Any failure — Bob missing, timeout, unparsable output — resolves to "no
    match" rather than a guess.
    """
    if not BOB_ENABLED:
        return {
            "selected_candidate_index": -1,
            "confidence": 0.0,
            "reasoning": "Bob calls disabled by BOBMADAK_BOB_DISABLED.",
            "risk_note": "Deterministic scoring only.",
            "available": False,
        }

    prompt = _build_bob_prompt(fingerprint, top_candidates, context_html)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(prompt)
        prompt_path = handle.name

    try:
        completed = subprocess.run(
            [BOB_COMMAND, "-p", f"@{prompt_path}", "--hide-intermediary-output"],
            capture_output=True,
            text=True,
            timeout=BOB_TIMEOUT_SEC,
            encoding="utf-8",
            errors="replace",
        )
        output = (completed.stdout or "").strip()
        match = re.search(r"\{[\s\S]*\"selected_candidate_index\"[\s\S]*?\}", output)
        payload = json.loads(match.group() if match else output)
        payload["available"] = True
        return payload
    except FileNotFoundError:
        return {
            "selected_candidate_index": -1,
            "confidence": 0.0,
            "reasoning": f"Bob Shell executable '{BOB_COMMAND}' not found on PATH.",
            "risk_note": "Escalated to a human instead of guessing.",
            "available": False,
        }
    except Exception as error:  # noqa: BLE001
        return {
            "selected_candidate_index": -1,
            "confidence": 0.0,
            "reasoning": f"Bob Shell call failed: {error}",
            "risk_note": "Escalated to a human instead of guessing.",
            "available": False,
        }
    finally:
        try:
            os.unlink(prompt_path)
        except OSError:
            pass


# ── Diagnosis ─────────────────────────────────────────────────────

def diagnose(
    broken_selector: str,
    fingerprint: dict,
    candidates: list[dict],
    context_html: str = "",
) -> dict:
    """
    Decide what the broken selector should point at now.

    Args:
        broken_selector: Selector that failed.
        fingerprint:     Fingerprint recorded on the last green run.
        candidates:      Every interactive element on the page as it is now.
        context_html:    Markup handed to Bob in the ambiguous band.

    Returns:
        {
          "broken_selector", "match", "confidence", "resolved_by",
          "band", "diagnosis", "ranked", "bob_response"
        }

        ``resolved_by`` is None when nothing was resolved.
    """
    ranked = rank_candidates(fingerprint, candidates)
    top = ranked[:3]

    if not top:
        return {
            "broken_selector": broken_selector,
            "match": None,
            "confidence": 0.0,
            "resolved_by": None,
            "band": "no_candidates",
            "diagnosis": "No interactive elements found on the page to compare against.",
            "ranked": [],
            "bob_response": None,
        }

    best = top[0]
    score = best["score"]

    if score >= CONFIDENT_THRESHOLD:
        return {
            "broken_selector": broken_selector,
            "match": best,
            "confidence": score,
            "resolved_by": "deterministic",
            "band": "confident",
            "diagnosis": _explain(fingerprint, best),
            "ranked": ranked[:5],
            "bob_response": None,
        }

    if score >= AMBIGUOUS_THRESHOLD:
        bob_response = ask_bob(fingerprint, top, context_html)
        index = bob_response.get("selected_candidate_index", -1)
        if isinstance(index, int) and 0 <= index < len(top):
            chosen = top[index]
            confidence = float(bob_response.get("confidence") or score)
            return {
                "broken_selector": broken_selector,
                "match": chosen,
                "confidence": round(confidence, 4),
                "resolved_by": "bob",
                "band": "ambiguous",
                "diagnosis": bob_response.get("reasoning")
                             or _explain(fingerprint, chosen),
                "ranked": ranked[:5],
                "bob_response": bob_response,
            }

        return {
            "broken_selector": broken_selector,
            "match": None,
            "confidence": round(score, 4),
            "resolved_by": None,
            "band": "ambiguous",
            "diagnosis": "Scoring was ambiguous and Bob declined to pick a candidate: "
                         + str(bob_response.get("reasoning", "no reason given")),
            "ranked": ranked[:5],
            "bob_response": bob_response,
        }

    return {
        "broken_selector": broken_selector,
        "match": None,
        "confidence": round(score, 4),
        "resolved_by": None,
        "band": "escalate",
        "diagnosis": f"Best candidate scored {score:.2f}, below the {AMBIGUOUS_THRESHOLD} "
                     "floor. No replacement is proposed.",
        "ranked": ranked[:5],
        "bob_response": None,
    }


def _explain(fingerprint: dict, candidate: dict) -> str:
    """Plain-English account of what changed, built from the signal breakdown."""
    signals = candidate.get("signals", {})
    before_attrs = fingerprint.get("attrs", {})
    after_attrs = candidate.get("attrs", {})

    changed = []
    if before_attrs.get("id") != after_attrs.get("id"):
        changed.append(
            f"id changed from '{before_attrs.get('id', '—')}' to '{after_attrs.get('id', '—')}'"
        )
    if signals.get("text", 0) < 0.99:
        changed.append(
            f"visible text changed from '{fingerprint.get('text')}' to '{candidate.get('text')}'"
        )
    if signals.get("dom_path", 0) < 0.85:
        changed.append("the element moved to a different container")
    if signals.get("attrs", 0) < 0.8:
        changed.append("attributes were refactored")

    stable = [name for name, value in signals.items() if value >= 0.85]
    stable_text = ", ".join(stable) if stable else "no signal"

    if not changed:
        changed.append("the selector no longer resolves, though every recorded signal matches")

    return f"{'; '.join(changed).capitalize()}. Stable signals: {stable_text}."



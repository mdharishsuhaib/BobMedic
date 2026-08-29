"""
bob_stub.py — a stand-in for Bob Shell, for running the demo offline.

This is a TEST DOUBLE, not a fallback. BotMedic never reaches for it on its
own: it is used only when someone explicitly points BOBMADAK_BOB_CMD at it,
so a machine without Bob Shell installed can still exercise the ambiguous
band end to end.

    set BOBMADAK_BOB_CMD=tools\\bob-stub.cmd

It reads the same prompt the real Bob Shell would receive and answers in the
same JSON shape, choosing the candidate whose element type and form context
match the original — the part of the judgement that can be made mechanically.
It does not do semantic reasoning, which is the whole reason the real Bob is
called here.
"""

import json
import re
import sys


def main() -> int:
    """Answer a BotMedic disambiguation prompt in the frozen JSON shape."""
    prompt_arg = next((arg for arg in sys.argv[1:] if arg.startswith("@")), None)
    if not prompt_arg:
        print(json.dumps({
            "selected_candidate_index": -1,
            "confidence": 0.0,
            "reasoning": "No prompt file supplied to the stub.",
            "risk_note": "Stub invoked incorrectly.",
        }))
        return 0

    prompt = open(prompt_arg[1:], encoding="utf-8").read()

    original_tag = None
    tag_match = re.search(r'"tag":\s*"([^"]+)"', prompt)
    if tag_match:
        original_tag = tag_match.group(1)

    blocks = re.split(r"^Candidate (\d+):$", prompt, flags=re.MULTILINE)
    chosen, reason = -1, "No candidate performs the original action."

    # blocks alternates: [prefix, index, body, index, body, ...]
    for index_text, body in zip(blocks[1::2], blocks[2::2]):
        tag = re.search(r'"tag":\s*"([^"]+)"', body)
        submit = '"type": "submit"' in body
        if tag and original_tag and tag.group(1) == original_tag and submit:
            chosen = int(index_text)
            reason = ("Same element type and the same submit role in the same form, "
                      "so it performs the original action despite the new wording.")
            break

    print(json.dumps({
        "selected_candidate_index": chosen,
        "confidence": 0.78 if chosen >= 0 else 0.0,
        "reasoning": reason,
        "risk_note": "Answered by the offline Bob stub, not by Bob Shell.",
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())



---
name: failure-classifier
description: Classify an IBM RPA bot failure from execution log output. Use when analyzing why a bot failed and what type of error occurred.
---

When classifying a bot failure:

1. Read the execution log provided
2. Identify the FIRST failure event by timestamp
3. Classify into exactly one of these types:
   - SELECTOR_CHANGED — element exists but id/class/name changed
   - ELEMENT_MISSING — element not found on page at all
   - PAGE_STRUCTURE — page layout changed significantly
   - TIMEOUT — element exists but page too slow
   - PERMISSION — authentication or access error
   - UNKNOWN — cannot determine from log alone

4. Return ONLY this JSON structure, no prose:
```json
{
  "failure_type": "SELECTOR_CHANGED",
  "failed_step": "step name or line number",
  "failed_selector": "the selector that failed",
  "error_message": "exact error from log",
  "confidence": 0.92,
  "reasoning": "one sentence explanation"
}
```

Rules:
- Never guess if the log is insufficient — use UNKNOWN with low confidence
- Confidence below 0.60 must include a note in reasoning asking for more context
- Do not suggest fixes in this step — classification only

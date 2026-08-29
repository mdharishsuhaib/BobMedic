# Project Rules

## Identity
- Hackathon: IBM TechXchange 2026 Pre-conference Dev Day
- All code, comments, documentation and UI text in English
- Fictional institution: NovaCorp. All demo data fully synthetic — no real
  usernames, passwords, client names or logs
- No credentials, API keys or tokens anywhere in the repository, ever

## Architecture
- The loop runs in this order and no other: fingerprint (on green runs) →
  detect → rank → escalate to Bob only if ambiguous → verify by re-running →
  check the risk tier → present to a human
- Every bot carries a risk tier in `rpa-bots/bots.json`:
  `read_only` | `reversible_write` | `irreversible` (underscores, always)
- An `irreversible` bot is never auto-patched. It is diagnosed, then refused,
  and the refusal is shown in the dashboard with the match that was withheld
- The patcher works on a copy. The original script is touched only by an
  explicit commit, which writes a `.bak` first
- The target site is served over HTTP, never opened from `file://` — Chromium
  denies localStorage to file origins and the break panel needs it

## Thresholds and scoring
- Defined once, in `src/contracts.py`. Do not restate them elsewhere in code
- `>= 0.85` deterministic fix · `0.55–0.85` ask Bob · `< 0.55` escalate
- Weights: text 0.30, attributes 0.25, DOM path 0.20, geometry 0.15, tag 0.10
- Never invent a match below the floor

## Bob usage
- Bob Shell (`bob -p ... --hide-intermediary-output`) is a runtime component,
  called only in the ambiguous band. Model calls are budgeted
- Bob answers in strict JSON: candidate index, confidence, one-sentence reason
- If Bob is unavailable, the incident escalates to a human — it never guesses
- Plan mode for architecture, Agent mode for implementation, Ask mode for
  `.wal` format questions

## Code rules
- Python for the engine, React for the dashboard, plain HTML/JS for the site
- Every function carries a docstring
- Strict JSON on every boundary; the dashboard never parses free text
- Fingerprints always carry: step_id, tag, text, attrs, dom_path, neighbors,
  geometry — and the element's own id never appears in its dom_path
- A patch is written against the most stable available signal (visible text
  plus element type, or a `data-testid`), never simply the new id
- Files are written without a UTF-8 BOM: a BOM breaks Vite's JSON loader

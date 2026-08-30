# BotMedic — Project Context

Built by **Team BobVanta**.

Read this before writing any code. It defines what is being built, the
contracts between components, and the constraints that are not negotiable.

## What this is

Self-healing RPA maintenance. When an IBM RPA bot fails because a target web
element changed, BotMedic fingerprints, detects, ranks, verifies, checks the
risk tier, and presents a diff to a human. It edits source scripts with diffs
and human review. It is not a production monitoring dashboard.

## The loop

```
green run      -> fingerprint every element touched + save a DOM snapshot
failed run     -> FailureEvent (frozen shape)
diagnosis      -> deterministic scoring; Bob only in the ambiguous band
verification   -> patch a COPY, re-run the bot, fall back to candidate two
risk gate      -> read_only | reversible_write | irreversible
presentation   -> PatchProposal (frozen shape) -> dashboard
```

## Risk tiers (do not bypass)

| Tier | Example | Behaviour |
|---|---|---|
| `read_only` | Download a report | Heal automatically when confidence >= 0.85 |
| `reversible_write` | Draft data entry | Heal, wait for human approval |
| `irreversible` | Submit a payment | Never auto-patch. Diagnose, then refuse. |

The tier lives in `rpa-bots/bots.json`, because it is a property of what the
bot does to the business, not of how its script is written. `engine.heal()`
checks it before any patch is written, and `engine.approve()` refuses an
irreversible bot even when asked directly.

## Thresholds

Defined once, in `src/contracts.py`:

- `>= 0.85` confident — deterministic fix, no model call
- `0.55 – 0.85` ambiguous — call Bob Shell with the fingerprint, the top three
  candidates and the page context
- `< 0.55` escalate to a human; never invent an answer

## Scoring weights

| Signal | Weight |
|---|---|
| Visible text | 0.30 |
| Attribute overlap (id, class, type, name, aria-label, placeholder, role) | 0.25 |
| DOM path similarity | 0.20 |
| Geometry proximity | 0.15 |
| Element tag | 0.10 |

`id` is one voice among several rather than the deciding one: a plain rename
costs about 0.08, which lands a rename at 0.92 — above the confident threshold,
but visible in the number.

## Fingerprint shape

```json
{
  "step_id": "login_submit",
  "tag": "button",
  "text": "Sign in",
  "attrs": { "id": "btn-login", "class": "btn primary", "type": "submit" },
  "dom_path": "form#login-form > div.actions > button.btn.primary",
  "neighbors": { "prev_label": "Password", "parent_text": "Sign in" },
  "geometry": { "x": 482, "y": 423, "w": 316, "h": 37 }
}
```

The element's own id never appears in `dom_path` — an ancestor id anchors the
path, but the element's own id is the signal that breaks.

## Step identity

A step is addressed by an ordinal key (`webclick#1` — the first `webClick` in
the file). Ordinals survive a selector patch, which is why they key the
fingerprint rather than the selector. `rpa-bots/bots.json` maps an ordinal key
to a human step id (`login_submit`).

## Directory map

```
src/contracts.py    frozen shapes, thresholds, strict JSON helpers
src/registry.py     bot catalogue, risk tiers, step names
src/parser.py       .wal reader; writes patched copies, never the original
src/fingerprint.py  the element description JS used on both sides of a break
src/runner.py       replays a .wal in Chromium, snapshots the DOM
src/watcher.py      records green runs, emits FailureEvent
src/diagnoser.py    scoring, selector proposals, Bob Shell call
src/patcher.py      patch a copy, verify by re-run, commit on approval
src/engine.py       the loop, the risk gate, the CLI
src/serve.py        static server for target-site
src/api.py          stdlib control API for the dashboard
```

## Rules

- `target-site/` is another team member's component, vendored in unmodified.
  The engine adapts to it, never the reverse. It is a standalone frontend that
  also works opened straight from `file://`; the bundled server exists to give
  the bots and the browser one stable origin, not because it is required
- The target app builds its buttons in inline JavaScript, so a saved snapshot
  has its `<script>` blocks stripped. Otherwise re-opening a snapshot re-runs
  those scripts, rebuilds the healthy page, and erases the break being
  diagnosed
- Break flags live in the target app's own localStorage keys —
  `break_login_id`, `break_login_move`, `break_login_text`, `break_export_id`,
  each holding the string `'true'` or `'false'`
- The patcher always works on a copy; the original is touched only by an
  explicit commit, which first writes a `.bak`
- A patch is written against the most stable signal available — visible text
  plus element type, or a `data-testid` — never simply the new id
- Bob Shell is called only in the ambiguous band; failures escalate rather
  than guess
- No credentials, API keys or tokens in the repository
- All demo data is synthetic; the demo institution is fictional
- Everything in English: code, comments, docs, UI text
- Strict JSON everywhere; free text breaks the dashboard

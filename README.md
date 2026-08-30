# BotMedic

**Team BobVanta** · IBM TechXchange 2026 Pre-conference Dev Day

> Self-healing RPA maintenance. When a target application changes its UI and an
> IBM RPA bot breaks, BotMedic diagnoses the break, writes a verified patch to
> the `.wal` script, and hands a human the diff — except where it is not allowed
> to act at all.

**IBM TechXchange 2026 Pre-conference Dev Day Hackathon**

---

## The problem

RPA bots break in production when the application underneath them changes. A
button is renamed, an element moves, a label is reworded, and the bot fails
mid-process. An engineer then reads execution logs by hand, opens the script,
hunts for the broken selector, and patches it. Hours per incident, and it
recurs on every release of every target application.

## The healing loop

1. **Fingerprint** — on every *successful* run, record a full identity for each
   element the bot touches, and save a DOM snapshot
2. **Detect** — the watcher spots the failing step and emits a failure event
3. **Rank** — score every interactive element on the changed page against the
   fingerprint, in plain deterministic code
4. **Escalate to Bob** — only when the score lands in the ambiguous band
5. **Verify** — patch a *copy* of the script, re-run the bot, confirm it reaches
   the end; on failure, try the next candidate
6. **Check the risk tier** — decide whether acting is allowed at all
7. **Present** — surface the diff, the confidence, and the evidence to a human

## Risk tiers

The tier is a property of the bot, checked before any patch is surfaced.

| Tier | Example | Behaviour |
|---|---|---|
| `read_only` | Download a report | Heal and continue automatically |
| `reversible_write` | Draft data entry | Heal, wait for human approval |
| `irreversible` | Submit a payment | Never auto-patch. Diagnose, then refuse. |

An `irreversible` bot visibly refuses to self-heal: the dashboard shows the
diagnosis, the match it *would* have used, and the fact that it declined.

## Scoring

Plain code, no model call. Weights are frozen.

| Signal | Weight |
|---|---|
| Visible text match | 0.30 |
| Attribute overlap (id, class, type, name, aria) | 0.25 |
| DOM path similarity | 0.20 |
| Positional proximity | 0.15 |
| Element type match | 0.10 |

| Score | What happens |
|---|---|
| `>= 0.85` | Confident deterministic fix, no model call |
| `0.55 – 0.85` | Send Bob the fingerprint, top three candidates and page context |
| `< 0.55` | Escalate to a human. No answer is invented. |

A plain id rename scores **0.92**: text, class, type, DOM path, position and
element type all hold, only the id moved. That case never reaches a model.

## Quick start

```bash
pip install -r requirements.txt
python -m playwright install chromium
cd dashboard && npm install && cd ..

# record what a healthy run looks like — do this once
python src/engine.py baseline

# bring the site, the API and the dashboard up together
npm run start:all
```

| Service | URL |
|---|---|
| Target site (demo application) | http://127.0.0.1:8000 |
| Break control panel | http://127.0.0.1:8000/break.html |
| Control API | http://127.0.0.1:8100/api/feed |
| Dashboard | http://127.0.0.1:3000 |

## Running the loop

From the dashboard, pick a bot, choose a break scenario, and press
**Break & run**. Or from the command line:

```bash
python src/engine.py demo invoice-extract  rename-login-id     # heals, auto-applies
python src/engine.py demo invoice-entry    rename-login-id     # heals, waits for approval
python src/engine.py demo payment-submit   rename-login-id     # refuses: irreversible
python src/engine.py demo invoice-extract  login-text-change   # ambiguous: asks Bob

python src/engine.py approve run-0002      # apply a verified patch and re-run
python src/engine.py reset                 # clear incidents and snapshots
```

The break panel at `/break.html` applies the same changes by hand, so the site
can be broken in a browser while someone watches. The target app is a
standalone frontend — it also runs by opening `target-site/index.html`
directly — but the bundled server gives the bots and the browser one stable
origin to share.

## Bob at runtime

Bob Shell is a live component, not just an authoring tool. When scoring lands
between 0.55 and 0.85, the engine calls:

```bash
bob -p "@<prompt file>" --hide-intermediary-output
```

and reads back strict JSON: a candidate index, a confidence, a one-sentence
reason. If Bob is not installed the incident escalates to a human rather than
guessing. Point the engine at a different binary with `BOBMADAK_BOB_CMD`, or
disable model calls entirely with `BOBMADAK_BOB_DISABLED=1`.

For a machine without Bob Shell, `tools/bob-stub.cmd` is a clearly labelled
test double that exercises the same code path:

```bash
set BOBMADAK_BOB_CMD=tools\bob-stub.cmd
```

## Project structure

```
botmedic/
├── src/
│   ├── contracts.py    frozen failure-event and patch-proposal shapes
│   ├── registry.py     the bot catalogue and its risk tiers
│   ├── parser.py       reads .wal scripts, writes patched copies
│   ├── fingerprint.py  the element description used on both sides of a break
│   ├── runner.py       replays a .wal in Chromium; snapshots the DOM
│   ├── watcher.py      records green runs, emits failure events
│   ├── diagnoser.py    scores candidates, calls Bob for the ambiguous band
│   ├── patcher.py      patches a copy, re-runs, falls back to candidate two
│   ├── engine.py       the loop, the risk gate, the CLI
│   ├── serve.py        static server for the target site
│   └── api.py          control API behind the dashboard
├── dashboard/          React control centre (MTTR, incidents, approvals)
├── target-site/        the team's target web app, vendored unmodified
├── rpa-bots/           three .wal bots, one per risk tier
├── fingerprints/       what each bot's elements looked like when healthy
├── snapshots/          DOM captured on every run
├── incidents/          failure events and patch proposals
└── .bob/               Bob rules and skills
```

## Contracts

Every value crossing a component boundary goes through `src/contracts.py`.

**Failure event** — watcher produces, engine consumes:

```json
{
  "run_id": "run-0042",
  "bot_id": "invoice-extract",
  "risk_tier": "read_only",
  "failed_step": "login_submit",
  "error": "ElementNotFound",
  "script_line": 8,
  "page_html_ref": "snapshots/run-0042.html",
  "timestamp": "2026-08-29T17:56:23+00:00"
}
```

**Patch proposal** — engine produces, dashboard consumes:

```json
{
  "run_id": "run-0042",
  "diagnosis": "Id changed from 'btn-login' to 'auth-submit-v2'. Stable signals: text, dom_path, geometry, tag.",
  "script_line": 8,
  "old_selector": "#btn-login",
  "new_selector": "button[type='submit']:has-text('Sign in')",
  "confidence": 0.92,
  "resolved_by": "deterministic",
  "verified": true,
  "action": "auto_applied"
}
```

`risk_tier`: `read_only` | `reversible_write` | `irreversible`
`resolved_by`: `deterministic` | `bob`
`action`: `auto_applied` | `await_approval` | `escalated_no_fix` | `blocked_risk_tier`

## Patching against stable signals

A patch never simply writes the new id back — that queues the same break up for
the next release. Selectors are proposed most-stable-first, and the first one
that matches exactly one element on the page wins:

1. `[data-testid=...]` — the application's own hook, if it has one
2. `button[type='submit']:has-text('Sign in')` — visible text plus element type
3. `input[name='username']` — form field name
4. `button.btn.primary` — element type plus class
5. `#new-id` — last resort

## Constraints

- No credentials, API keys or tokens anywhere in the repository
- Model calls only in the ambiguous band; everything else is deterministic code
- All demo data is synthetic and the demo institution is fictional
- Strict JSON everywhere — the dashboard never parses free text

## License

MIT. All demo data is synthetic.


# How IBM Bob Was Used — BotMedic

**Team BobVanta** · IBM TechXchange 2026 Pre-conference Dev Day

Bob was used in two distinct ways on this project, and the second one is the
part that matters: Bob is not only how the code was written, it is a component
that runs inside the finished system.

---

## 1. Bob as a runtime component

This is the differentiator. BotMedic calls Bob Shell while it is running, in
production, on exactly one decision — and nowhere else.

When a bot fails, every interactive element on the changed page is scored
against the fingerprint recorded on the last successful run. That scoring is
plain deterministic code. Three outcomes follow:

| Score | What happens | Model called? |
|---|---|---|
| `>= 0.85` | Deterministic fix, applied and verified | No |
| `0.55 – 0.85` | **Bob Shell decides** | Yes — one call |
| `< 0.55` | Escalate to a human, propose nothing | No |

The middle band is the case a model is genuinely needed for. A renamed id
scores 0.92 and is resolved arithmetically. But when the button's *wording*
changes — "Sign in" becomes "Login" — the score falls to 0.77 and no amount of
scoring settles whether the new control performs the old action. That is a
question about meaning, and it is the one question BotMedic asks Bob.

The invocation, from `src/diagnoser.py`:

```bash
bob -p "@<prompt file>" --hide-intermediary-output
```

Bob receives the original fingerprint, the top three candidates with their
per-signal score breakdown, and the surrounding page markup. It returns strict
JSON and nothing else:

```json
{
  "selected_candidate_index": 0,
  "confidence": 0.78,
  "reasoning": "Same element type and the same submit role in the same form.",
  "risk_note": null
}
```

Three properties of this integration were deliberate:

- **Budgeted.** One call per ambiguous incident. Everything else is arithmetic.
  On a five-incident demo run, four incidents never reach a model at all.
- **Structured.** Bob's answer is parsed as JSON against a fixed shape. Free
  text would break the dashboard, so free text is not accepted.
- **Fail-closed.** If Bob is unavailable, the incident escalates to a human.
  It never falls back to a guess, and it never silently picks candidate zero.

Bob's answer is also not trusted on its own: the selected candidate is written
to a *copy* of the bot script, the bot is re-run against the changed page, and
only a run that reaches the end of the script is reported as a fix.

---

## 2. Bob as the development environment

### Plan mode — architecture

Used to design the pipeline and settle the deterministic-versus-model split.
The initial sketch sent the whole DOM to a model on every failure. Bob argued
against it and proposed the hybrid that shipped: weighted scoring first, model
only inside a confidence band. That decision is why the system makes roughly
one model call per five incidents instead of one per incident.

The fingerprint schema and the five scoring weights in `AGENTS.md` came out of
that session.

### Ask mode — the `.wal` format

Used to understand the IBM RPA `.wal` (WDG Automation Language) format before
writing the parser: how `webClick`, `webSet` and `webNavigate` statements are
structured, where the selector lives on each line, and what a patch has to
leave untouched.

This research produced a constraint that later corrected a real design error.
An early version patched selectors to `button:has-text('Sign in')`, which reads
well and is completely unusable — `:has-text()` is a Playwright extension, not
CSS, so the patched script would not have run in IBM RPA Studio at all. The
selector ladder now prefers selectors that are valid CSS *and* not rebuilt from
the id that just changed, which is why the login break heals to
`button.btn.primary[type='submit']`.

### Agent mode — implementation

Each component was built as its own task: watcher, parser, diagnoser, patcher,
dashboard, control API. Two contributions were Bob's own, not requested:

- the patcher must work on a copy and never touch the original script, with a
  `.bak` written before any commit;
- break state must live on the server rather than in each browser's
  localStorage, so that the headless bots, the break panel and IBM RPA Studio's
  own isolated Chrome all see the same broken page.

### Bob's rules and skills

`.bob/rules/project-rules.md` carries the constraints that apply to every
conversation on this repository — the risk-tier vocabulary, the thresholds, the
patcher's copy-first rule, and the instruction that the target web app belongs
to another team member and is vendored unmodified.

`.bob/skills/` holds three task-specific skills: `failure-classifier`,
`risk-assessor` and `semantic-matcher`.

---

## Session report

The exported Bob session report is included in this repository as
`bob-session-report.html`.

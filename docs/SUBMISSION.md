# Submission copy — Team BobVanta

The text submitted for each deliverable, kept here for reference.

---

## Deliverable 2 — Problem and solution statement

**BotMedic — self-healing RPA maintenance**

RPA robots break the moment the application underneath them changes. A
front-end team ships a routine release, a button's id goes from `btn-login` to
`auth-submit-v2`, and every bot that clicked it stops mid-process. Nothing
changed for a person: same wording, same place, same form. Only the handle the
robot was holding is gone.

What follows is entirely manual. An operations engineer reads execution logs,
opens the script, hunts for the broken selector, guesses a replacement, and
re-runs. Hours per incident, and it recurs on every release of every target
application. In our own runs the manual path averages 47 minutes; BotMedic
closes the same incident in about 40 seconds.

BotMedic is built for the RPA operations engineer who owns a fleet of bots.
During every *successful* run it records a full identity for each element the
bot touched — visible text, attributes, DOM path, neighbours, geometry — and
saves the page. That step, which most self-healing demos skip, is what makes
the rest possible. When a run fails, it scores every interactive element on the
changed page against that record using plain deterministic code: text 0.30,
attributes 0.25, DOM path 0.20, position 0.15, element type 0.10.

A renamed id scores 0.92 and is resolved arithmetically. Only the ambiguous
band, 0.55 to 0.85, reaches IBM Bob — the case where a button's wording changed
from "Sign in" to "Login" and no amount of scoring settles whether it still
does the same job. Below 0.55 nothing is proposed and a human is told why. So
one incident in five reaches a model, and the rest cost nothing.

No patch is trusted. It is written to a copy of the `.wal`, the robot is
re-run, and only a run that reaches the end of the script is reported as fixed;
if it fails, the next candidate is tried. The patch is also written against the
signals that survive a UI release, never the id that just changed.

What makes it unlike anything else in this space is what happens next. Every
bot carries a risk tier, and it is checked *before* any patch is surfaced. A
read-only bot heals and carries on. A reversible-write bot heals and waits for
a human. An irreversible bot — one that submits a payment — is diagnosed to a
0.92 match, shown the element it would have used, and then **refused**. The
system states plainly that it could fix this and will not.

The engineer watches all of it in a control centre: mean time to repair, the
incident, the diagnosis in plain English, the candidate scores, the diff, and
one button — Approve and rerun.

Self-healing automation that never says no is automation nobody can put near a
payment run. BotMedic's judgement about when to stop is the product.

---

## Deliverable 3 — How IBM Bob was used

Bob was used in two ways, and the second is the one that matters.

**Bob at runtime, inside the shipped system.** BotMedic calls Bob Shell while
it is running, on exactly one decision. When deterministic scoring lands
between 0.55 and 0.85, `src/diagnoser.py` invokes:

```
bob -p "@<prompt file>" --hide-intermediary-output
```

Bob receives the original element fingerprint, the top three candidates with
their per-signal score breakdown, and the surrounding page markup. It returns
strict JSON — a candidate index, a confidence, one sentence of reasoning — which
is parsed against a fixed shape; free text is rejected. Three properties were
deliberate: the call is **budgeted** (one per ambiguous incident, four in five
incidents never reach a model), **structured**, and **fail-closed** — if Bob is
unavailable the incident escalates to a human rather than guessing. Bob's
answer is then verified by re-running the robot before any human sees it.

**Bob as the development environment.** Plan mode settled the architecture: our
first sketch sent the whole DOM to a model on every failure, and Bob argued
against it and proposed the hybrid that shipped — weighted scoring first, model
only inside a confidence band. That decision is why the system makes roughly
one model call per five incidents.

Ask mode was used to understand the IBM RPA `.wal` format before writing the
parser. That research caught a real defect: a `.wal` saved by Studio is a
container — `0x12 <varint length> <body> 0x2A 0x09 "23.0.19.0"` — and patching
it as text destroys the header, so Studio refuses the healed file with "Command
not found on line 0". The patcher now edits bytes and recomputes the length
prefix.

Agent mode built each component as its own task: watcher, parser, diagnoser,
patcher, dashboard, control API. Two contributions were Bob's own and were not
asked for: the patcher must work on a copy and never touch the original script,
and break state must live on the server so the headless bots, the fault panel
and IBM RPA Studio's own Chrome all see the same page.

`.bob/rules/project-rules.md` carries the constraints applied to every
conversation in this repository, and `.bob/skills/` holds three task-specific
skills: `failure-classifier`, `risk-assessor` and `semantic-matcher`.

We did not use watsonx.ai or watsonx Orchestrate.

---

## Deliverable 4 — Repository

- [x] Public repository
- [x] `BOB-SESSION-REPORT.md` at the root — 6 sessions, 671 messages, 57
      prompts, 366 tool calls, exported from the local Bob database
- [x] `docs/bob-sessions/` — per-member Bob session material
- [x] Working code, runnable with `npm run start:all`
- [x] `.gitignore` and `.bobignore` from the hackathon template, no credentials

## Deliverable 1 — Video (3 minutes maximum)

Judges stop watching at three minutes, and at least 90 seconds must show the
solution running. A running order that fits:

| Time | Shot |
|---|---|
| 0:00–0:25 | The problem: a renamed button id, a stopped robot, the manual hunt |
| 0:25–0:45 | The fault panel: flip "Rename login button ID" live |
| 0:45–1:15 | Run the bot in IBM RPA Studio. It stops. |
| 1:15–2:00 | The watcher detects it, scores 0.92, verifies, patches. Re-run in Studio: it completes. |
| 2:00–2:30 | **The refusal** — the payment bot, same break, diagnosed and declined |
| 2:30–3:00 | Where Bob sits: the ambiguous band, one call, verified before a human sees it |

Lead with the refusal if anything has to be cut. It is the part no other
submission will have.

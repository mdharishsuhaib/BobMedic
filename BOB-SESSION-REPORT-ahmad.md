# IBM Bob Session Report

**Team BobVanta** · IBM TechXchange 2026 Pre-conference Dev Day Hackathon
**Project:** BotMedic — self-healing RPA maintenance
**Member:** Ahmed Elshikh
**Exported from:** the local Bob database (`~/.bob/db/bob.db`)

---

## Summary

| | |
|---|---|
| Task sessions on this account | 6 (one carrying the project work, five empty) |
| Messages in the working session | **671** |
| Prompts given to Bob | **57** |
| Bob responses | **247** |
| Tool calls Bob made | **366** |
| Period | 27 August – 30 August 2026 |

The working session ran from the first project conversation through to the
merge onto `main`. Bob was driven in Arabic throughout; this report is written
in English, as the submission requires.

---

## Tools Bob used

| Calls | Tool | What it was used for |
|---:|---|---|
| 144 | `execute_command` | Running the engine, the bots, the servers, git |
| 97 | `read_file` | Reading source before changing it |
| 34 | `write_file` | Creating engine modules, the target site, the docs |
| 27 | `search_bob_docs` | Bob's own documentation, including session export |
| 19 | `apply_diff` | Targeted edits to existing code |
| 16 | `update_todo_list` | Tracking the build across a long session |
| 10 | `search_and_replace` | Renames and mechanical edits |
| 9 | `list_files` | Navigating the project |
| 7 | `grep` | Finding definitions and call sites |
| 2 | `glob` | Locating files by pattern |
| 1 | `create_html_artifact` | Producing a visual artefact |

## Files Bob worked on most

| Edits | File |
|---:|---|
| 16 | `botmedic/BobMedic.wal` — the IBM RPA Studio bot script |
| 14 | `botmedic/src/runner.py` — replays a `.wal` in a real browser |
| 13 | `botmedic/src/parser.py` — reads and patches `.wal` files |
| 13 | `botmedic/src/watcher.py` — records green runs, reports broken ones |
| 10 | `botmedic/src/engine.py` — the healing loop and the risk gate |
| 9 | `botmedic/src/diagnoser.py` — candidate scoring and the Bob call |
| 9 | `botmedic/target-site/index.html` — the sign-in page bots drive |
| 9 | `botmedic/rpa-bots/bots.json` — the bot registry and risk tiers |
| 7 | `botmedic/src/serve.py` — target-site server and fault state |
| 7 | `botmedic/target-site/break.html` — the fault injection panel |

---

## How the session progressed

### 1. Choosing what to build

The session opened by handing Bob a briefing and working through candidate
ideas one at a time. An early idea — a tool for designers drowning in image
files — was put aside. The question asked of Bob was direct: *which idea could
actually win this hackathon?* That conversation produced BotMedic: an IBM RPA
bot breaks when its target application changes, and the system diagnoses the
break, patches the script, and proves the fix.

The choice was grounded in real experience. Three years of IBM RPA work meant
the problem was already familiar, and IBM RPA Studio was already installed on
the machine — so the demo could run against the real product rather than a
mock.

### 2. Learning Bob's own tooling early

One instruction to Bob was to find out **how to export a session report now,
rather than discover it at the deadline**. Bob searched its documentation
(`search_bob_docs`, 27 calls across the session) and the result was
`tools/export-bob-report.py`, which reads the local Bob database directly. That
turned out to matter: it works with an exhausted Bobcoin balance, because it
never contacts the service.

### 3. Building the pieces

Bob built the target site — sign-in, invoices, payment and a fault injection
panel — then the bot script, then the engine: fingerprint recorder, WAL parser,
candidate scorer, patcher and the orchestrating loop. Work proceeded one step
at a time, with Bob asked to explain its plan before each stage.

### 4. Driving it from IBM RPA Studio

The bot was authored in IBM RPA Studio and pointed at the local site. This is
where the sharpest questions came from the RPA side of the desk:

- *IBM RPA Studio does not raise element-not-found for a click the way it does
  for get-value or set-value* — which changed how failure had to be detected.
- The bot opened a fresh Chrome instance each run, so break state had to be
  visible to a browser the engine did not control. Bob moved fault state to the
  server, where every browser sees the same page.
- Repeated real runs exposed the gap between a bot that stops and a system that
  notices: Studio's log is flushed in blocks and lags by minutes.

### 5. Naming, and reverting it

Bob was asked at one point to rename the project to "Bob Madak", and then to
put the original name back. Both renames were carried out across the codebase.

### 6. Integration

The final stretch merged the work with the team repository on GitHub, verified
the result, and pushed to `main`.

---

## What Bob contributed that was not asked for

Two decisions came from Bob rather than from an instruction, and both are still
in the shipped system:

- **The patcher must work on a copy.** The original `.wal` is never edited in
  place; a patch is written to a copy, proved by re-running the bot, and only
  committed afterwards — with a `.bak` written first.
- **Fault state belongs on the server.** Storing it per browser meant IBM RPA
  Studio's own Chrome could not see it. Moving it server-side made the headless
  engine, the fault panel and Studio agree on one page.

---

## Bob inside the finished product

Beyond building the project, Bob is a runtime component of it. When
deterministic scoring lands between 0.55 and 0.85 — the ambiguous band, where a
button's wording changed but its purpose did not — `src/diagnoser.py` invokes:

```
bob -p "@<prompt file>" --hide-intermediary-output
```

Bob receives the recorded element fingerprint, the top three candidates with
their per-signal scores, and the surrounding markup, and returns strict JSON: a
candidate index, a confidence, and one sentence of reasoning. The call is
budgeted — four incidents in five never reach a model — and fail-closed: if Bob
is unavailable the incident escalates to a person rather than guessing.

---

## Reproducing this report

```powershell
python tools/export-bob-report.py --all --out <output>.html
```

It reads `~/.bob/db/bob.db` on the machine it runs on, so each team member must
run it themselves — the database holds only that member's own sessions. See
`docs/bob-sessions/README.md`.

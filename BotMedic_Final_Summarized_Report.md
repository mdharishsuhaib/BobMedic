# BotMedic — Final Project Report

## IBM TechXchange 2026 Hackathon — Team BobVanta

**Project:** BotMedic — Automated RPA Robots Handling and Correction System  
**Hackathon:** IBM TechXchange 2026 Pre-conference Dev Day Hackathon  
**Team:** Team BobVanta  
**Project period represented in the reports:** 27–30 August 2026

---

## 1. Executive Summary

BotMedic is a self-healing maintenance layer for Robotic Process Automation (RPA). The project addresses a common weakness of UI-driven automation: RPA bots depend on precise UI selectors, so small changes to a target application's HTML, text, CSS classes, or DOM structure can cause otherwise valid automations to fail.

The central idea behind BotMedic is to remember what a successful UI interaction looked like, detect when a later run can no longer find that element, identify the most likely replacement, and repair the automation without immediately requiring a developer.

The system follows a deliberately layered strategy:

1. **Observe successful bot executions** and capture rich UI-element fingerprints.
2. **Detect failures** and capture structured failure information.
3. **Try deterministic recovery first**, using multiple signals such as text, element type, selector similarity, DOM structure, position, and neighbouring context.
4. **Escalate ambiguous cases to IBM Bob**, rather than using AI for every failure.
5. **Apply proposed fixes to a copy** of the bot configuration.
6. **Re-run the bot** to verify that the repair actually works.
7. **Use risk classification and Human-in-the-Loop governance** so high-risk actions, such as payments or irreversible writes, require explicit human approval.
8. **Expose failures, resolutions, fingerprints, and approval state through a developer dashboard.**

The project therefore combines RPA, deterministic reasoning, IBM Bob, automated testing, and human governance into one maintenance workflow.

The reports document both the project's technical design and practical development experience with IBM RPA Studio. One Bob session contained 671 messages, 57 prompts, 247 Bob responses, and 366 tool calls over the project period, with the work ultimately merged to `main`. The session reports also show Bob being used as both a development assistant and, in the finished design, a runtime reasoning component for ambiguous failures.

---

## 2. Problem Statement

RPA bots commonly interact with applications through selectors such as:

- HTML IDs
- CSS classes
- XPath expressions
- DOM paths
- Visible text

These selectors are precise but fragile. An application update can rename an ID, change a button label, move an element to another container, or modify its classes while leaving the application's underlying business function unchanged.

For example, a bot may originally target:

```text
#btn-login
```

while the application later changes the same button to:

```text
#auth-submit-v2
```

To the human user, the login button still exists. To the RPA bot, the original selector no longer resolves and the workflow can stop.

The conventional recovery process is manual:

1. Detect the failed automation.
2. Open the target application.
3. Find the changed element.
4. Modify the bot selector.
5. Test the modification.
6. Redeploy the bot.

At enterprise scale, repeated selector maintenance creates developer workload, downtime, and operational risk.

BotMedic was conceived as a way to automate the repetitive part of this recovery process while preserving human control where automated decisions are uncertain or high-risk.

---

## 3. Project Vision

BotMedic is designed as a platform-agnostic recovery layer rather than a replacement for RPA.

Its intended characteristics are:

- **Self-healing:** recover from common UI drift automatically.
- **Deterministic first:** use predictable, explainable methods before AI.
- **AI when needed:** use IBM Bob for genuinely ambiguous cases.
- **Verified recovery:** never trust a proposed fix without re-execution.
- **Risk-aware:** distinguish safe automation repairs from high-impact actions.
- **Human-governed:** require approval for high-risk repairs.
- **Modular:** keep monitoring, diagnosis, AI, patching, and presentation separated.
- **Auditable:** retain the evidence behind a recovery decision.

The project documentation explicitly states that BotMedic does not modify the target application, does not require source-code access to that application, does not automatically deploy high-risk fixes to production, and does not guarantee recovery in every possible case.

---

## 4. Overall System Architecture

The project is organized around several cooperating components:

```text
                 ┌─────────────────────┐
                 │   Target Web App    │
                 │   NorthBridge Bank  │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │      RPA Bot        │
                 │ IBM RPA Studio bot  │
                 └──────────┬──────────┘
                            │
                    success / failure
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Parser & Watcher    │
                 │ failure detection   │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ Fingerprinting &    │
                 │ Diagnosis Engine    │
                 └──────────┬──────────┘
                            │
                 ┌──────────┴──────────┐
                 │                     │
          confident match       ambiguous case
                 │                     │
                 ▼                     ▼
        Deterministic Repair      IBM Bob AI
                 │                     │
                 └──────────┬──────────┘
                            ▼
                 ┌─────────────────────┐
                 │ Patch & Verification│
                 │   re-run the bot    │
                 └──────────┬──────────┘
                            │
                     verification
                            │
                 ┌──────────┴──────────┐
                 │                     │
             low/medium             high risk
                 │                     │
                 ▼                     ▼
          Auto-deploy after      Human approval
             verification              │
                                       ▼
                              Production deployment

                            │
                            ▼
                 ┌─────────────────────┐
                 │ Developer Dashboard │
                 └─────────────────────┘
```

The planned platform structure separates the project into:

```text
packages/adapter
backend/
frontend/
db/
```

The adapter is intended to give robots a simple integration point for reporting failures and capturing successful element fingerprints. The backend handles ingestion, resolution, Bob integration, retesting, and persistence. The frontend provides developer visibility. PostgreSQL is intended to store fingerprints, failure reports, and resolution outcomes.

---

## 5. End-to-End Workflow

### Step 1 — Successful execution

The RPA bot executes normally against the target application.

### Step 2 — Fingerprint capture

For every important interaction, BotMedic records a rich description of the target element.

The fingerprint can contain:

- stable step ID
- HTML tag
- visible text
- ID
- CSS class
- input/button type
- DOM path
- neighbouring labels
- screen geometry
- parent/ancestor structure
- accessibility-related attributes
- screenshot or DOM-state hashes where available

Example:

```json
{
  "step_id": "login_submit",
  "tag": "button",
  "text": "Sign in",
  "attrs": {
    "id": "btn-login",
    "class": "btn primary",
    "type": "submit"
  },
  "dom_path": "form#login > div.actions > button",
  "neighbors": {
    "prev_label": "Password"
  },
  "geometry": {
    "x": 420,
    "y": 380,
    "w": 120,
    "h": 40
  }
}
```

The purpose of this redundancy is to make the element identifiable even when one or more individual selectors change.

### Step 3 — UI drift

The target application changes.

Examples include:

- ID rename
- class change
- visible-text change
- DOM movement
- multiple simultaneous changes

### Step 4 — Bot failure

The original selector no longer identifies the intended element.

The failure watcher records information such as:

- robot ID
- step ID
- timestamp
- error type
- failed selector
- page URL
- DOM snapshot hash
- optional screenshot

### Step 5 — Candidate discovery

The Diagnosis Engine searches the current page for elements that could represent the original target.

### Step 6 — Deterministic scoring

Candidates are compared against the stored fingerprint.

The design gives meaningful weight to several independent signals:

| Signal | General importance |
|---|---|
| Visible text | High |
| Element type | High |
| CSS class | Medium-high |
| DOM path | Medium |
| Spatial geometry | Medium |
| ID | Medium-low |
| Neighbouring label/context | Medium |

The exact weights are intended to be tuned.

### Step 7 — Decision

If one candidate clearly exceeds the confidence threshold, BotMedic can produce a deterministic repair.

If the evidence is ambiguous, the incident is escalated to IBM Bob.

The planned resolution engine uses a configurable confidence threshold, with the architecture document specifying a default of **0.75**.

### Step 8 — IBM Bob escalation

IBM Bob receives structured evidence rather than an unconstrained request.

The runtime design describes sending:

- the original fingerprint
- candidate elements and their scores
- surrounding markup/DOM
- the failure reason

Bob returns a candidate, confidence, and reasoning. In the documented implementation, ambiguous scoring in the 0.55–0.85 range can trigger the Bob call.

A particularly important design decision is that Bob's answer is treated as a **hypothesis**, not as truth.

### Step 9 — Safe patching

The proposed selector or repair is applied to a copy of the bot configuration.

The original `.wal` is not edited in place. A backup is written first, and the proposed repair is tested before it can be committed.

### Step 10 — Full re-run

BotMedic re-runs the robot with the proposed configuration.

The system does not consider a fix successful simply because the new selector looks plausible.

### Step 11 — Verification

If the previously failing action succeeds, the repair is marked verified.

If it fails again, the proposed fix is rejected and the incident can be escalated.

### Step 12 — Risk decision

The repaired action is classified according to risk.

| Risk | Example | Behaviour |
|---|---|---|
| Low | Navigation, read-only work, login | Auto-deploy after verification |
| Medium | Data extraction, reporting | Auto-deploy after verification + notification |
| High | Payment, data writes, irreversible actions | Explicit human approval |

---

## 6. Deterministic Recovery Strategy

A major design principle of BotMedic is **not to use AI when deterministic reasoning is sufficient**.

The planned resolution engine has four layers:

### Layer 1 — Selector Drift

Fuzzy matching compares the failed selector against stored selectors, CSS selectors, and XPaths.

### Layer 2 — Label/Text Drift

Text and labels are compared using normalized similarity.

This can recover from changes such as:

```text
"Sign in" → "Login"
```

### Layer 3 — Parent Container Scan

The engine examines the stored parent structure and searches sibling/child relationships for the likely replacement.

### Layer 4 — Timing/Timeout Retry

For timeout failures, the system can attempt a retry with increased waiting time without requiring element-level scoring.

The engine short-circuits when a sufficiently confident answer is found.

This provides a predictable and explainable first line of defence.

---

## 7. IBM Bob's Role

IBM Bob has two distinct roles in the project.

### 7.1 Development assistant

During development, Bob was used to:

- reason about the architecture
- create and modify project files
- run commands
- inspect source files
- build the target application
- develop the engine
- troubleshoot integration problems
- maintain project tasks
- work with IBM RPA Studio
- investigate Bob's own tooling and session export

One documented working session contained **671 messages, 57 prompts, 247 Bob responses, and 366 tool calls** from 27–30 August 2026. The work progressed from project selection through implementation and integration, ending with a merge to `main`.

### 7.2 Runtime AI component

Bob also becomes part of the final BotMedic architecture.

When deterministic diagnosis cannot confidently identify the replacement element, BotMedic sends the structured failure context to Bob.

The documented runtime design describes a CLI invocation using a prompt file and expects strict structured output containing:

- candidate index
- confidence
- short reasoning

The implementation is designed to be budget-conscious: most incidents should not require model inference. The documented session describes a budget rule where four incidents in five do not reach a model.

If Bob is unavailable, the system is designed to **fail closed** and escalate to a human rather than guess.

---

## 8. Patch and Verification Safety

One of the strongest engineering decisions in the project is the separation between **proposing a fix** and **accepting a fix**.

The system follows:

```text
Proposed Fix
     │
     ▼
Patch Copy
     │
     ▼
Run Bot
     │
     ▼
Did the failed action succeed?
   ┌─┴─┐
  YES  NO
   │    │
   ▼    ▼
Verified Reject
```

This applies to both deterministic repairs and IBM Bob suggestions.

The development report specifically records that Bob contributed the design decision that the patcher must work on a copy rather than modifying the original `.wal` in place. The original is preserved, a backup is created, and the proposed repair is proven by re-running the bot before being committed.

This makes the bot's own execution the acceptance test for the repair.

---

## 9. Human-in-the-Loop Governance

The project also explored the governance principles needed for AI-assisted software maintenance.

The team used IBM Bob to study:

- software modularity
- Human-in-the-Loop governance
- AI lifecycle oversight

The modularity discussion emphasized:

- single responsibility
- clear interfaces
- encapsulation
- high cohesion
- low coupling

These ideas align with BotMedic's separation into monitoring, diagnosis, AI escalation, patching, verification, risk management, and dashboard components.

The governance discussion emphasized that AI systems can:

- drift over time
- fail silently
- encode bias
- be difficult to audit
- produce high-stakes errors

BotMedic applies the corresponding principle directly: automation can handle clear and verified repairs, but humans remain involved when confidence is insufficient or when the action carries significant risk.

Importantly, the supplied teammate report treats this as architectural knowledge rather than claiming that the teammate independently implemented a separate HITL module.

---

## 10. Target Application — NorthBridge Bank

To make the project demonstrable, the team built a fictional banking application called:

**NorthBridge Bank — Internal Operations Portal**

It provides a realistic UI environment in which selectors can intentionally be broken.

### Application pages

| Page | File | Main target |
|---|---|---|
| Login | `index.html` | `#btn-login` / “Sign in” |
| Invoice Management | `invoices.html` | `#btn-export` / “Download CSV” |
| Payment Submission | `payment.html` | `#btn-pay` / “Submit payment” |
| Break Panel | `break.html` | Controlled UI fault injection |

The application is implemented with plain HTML, CSS, and vanilla JavaScript.

The login accepts non-empty credentials and redirects to the invoice page. The invoice page contains eight fictional invoices and a working CSV download. The payment page contains a demonstration payment form but does not process real transactions.

---

## 11. Controlled Failure Injection

The Break Control Panel was created specifically to make the demo repeatable.

It provides four break scenarios:

| Break | Normal | Broken |
|---|---|---|
| Login ID | `btn-login` | `auth-submit-v2` |
| Login DOM location | `#login-btn-container` | `#login-btn-container-alt` |
| Login text | `Sign in` | `Login` |
| Export ID | `btn-export` | `export-data-btn` |

The break state is dynamically applied when pages load.

The control panel provides:

- individual toggles
- **Reset All**
- **Enable All Breaks**

The target elements deliberately do not use special `data-testid` attributes. The goal is to test recovery against the kinds of signals that an ordinary, unmaintained web application provides.

---

## 12. IBM RPA Studio Integration

The RPA bot was authored in IBM RPA Studio and connected to the local target application.

The project includes two primary bots:

### Login Bot

- navigates to the login page
- enters credentials
- clicks the login/submit control

### Export Bot

- navigates to the invoice page
- clicks the CSV export control

The bots use selectors from the original working application state. Once a break is activated, those selectors can fail.

The development process uncovered practical RPA integration issues.

For example, IBM RPA Studio did not report every failed click in the same way as operations such as `get-value` or `set-value`. This affected how BotMedic needed to detect failures.

The bot also opened a fresh Chrome instance on each run. This exposed a problem with browser-local fault state: the engine and Studio could end up observing different state. The team consequently moved fault state to a shared server-side mechanism in the integrated implementation so the engine, fault panel, and Studio could observe the same target state.

Repeated real runs also revealed that Studio's logs are flushed in blocks and can lag behind the actual failure by minutes. This is an important practical observation for building a reliable failure watcher.

---

## 13. Development Contributions and Project Work

The supplied reports show work across several areas of the system.

### Core implementation files

The Bob session report records substantial work on:

| File | Purpose |
|---|---|
| `botmedic/BobMedic.wal` | IBM RPA Studio bot script |
| `botmedic/src/runner.py` | Replays a `.wal` in a browser |
| `botmedic/src/parser.py` | Reads and patches `.wal` files |
| `botmedic/src/watcher.py` | Records successful runs and reports broken runs |
| `botmedic/src/engine.py` | Healing loop and risk gate |
| `botmedic/src/diagnoser.py` | Candidate scoring and IBM Bob invocation |
| `botmedic/target-site/index.html` | Login page |
| `botmedic/rpa-bots/bots.json` | Bot registry and risk tiers |
| `botmedic/src/serve.py` | Target-site server and fault state |
| `botmedic/target-site/break.html` | Fault injection panel |

The Bob session involved extensive use of command execution, file inspection, file creation, targeted edits, task tracking, source searching, and project navigation.

---

## 14. Planned Platform Components

The architectural plan describes a broader platform implementation with seven major workstreams.

### 14.1 Adapter package

The planned `packages/adapter` package defines a standard failure-report contract and functions such as:

```text
reportFailure(...)
captureSuccess(...)
```

The adapter is intended to remain lightweight and communicate with the BotMedic backend over HTTP.

### 14.2 Persistent data layer

The planned PostgreSQL layer contains:

- `fingerprints`
- `failure_reports`
- `resolutions`

This enables versioned fingerprint history, failure-state tracking, and resolution auditing.

### 14.3 Backend API

The planned Node.js/Express backend exposes endpoints such as:

```text
POST /api/fingerprint
POST /api/failure
GET  /api/health
```

Input validation is part of the design.

### 14.4 Resolution engine

The backend resolution engine implements the deterministic layers and configurable confidence threshold.

### 14.5 Resolution worker and Bob integration

A worker processes pending failures, invokes deterministic recovery, escalates to Bob when necessary, and triggers robot re-runs.

### 14.6 React dashboard

The dashboard is designed around:

- Failure Feed
- Resolution Detail
- Fingerprint Browser

It gives developers visibility into:

- active failures
- recovery method
- confidence
- applied fix
- retest result
- Bob's reasoning when applicable
- fingerprint history

### 14.7 Local development and deployment setup

The plan includes Docker Compose for:

- PostgreSQL
- backend
- frontend

It also includes environment configuration for:

```text
DATABASE_URL
PORT
CONFIDENCE_THRESHOLD
BOB_API_URL
```

---

## 15. What Was Successfully Demonstrated

The supplied reports provide direct evidence for several parts of the project.

### Target application

The target web application was completed and locally verified.

Verified behaviours include:

- application loading
- login flow
- invoice table with eight rows
- CSV generation
- payment form
- payment demo alert
- persistent break state
- all four break scenarios
- restoration of all four break scenarios
- Reset All
- Enable All Breaks
- idempotent break toggling

The Bob/VS Code screenshots additionally show the break scenarios being implemented and report an **All tasks completed / 4 of 4** status for the visible Bob task set.

### Broader project integration

The development report records that the team:

- built the target site
- built the bot
- built the fingerprinting/diagnosis/healing components
- integrated IBM Bob into the recovery path
- addressed RPA Studio behaviour
- integrated the project with the team repository
- verified the result
- pushed the integrated work to `main`

However, the reports also distinguish between components that were complete and components that were still being integrated at the point of the target-application report.

---

## 16. Current Status and Evidence Boundaries

A critical part of this final report is distinguishing **designed**, **implemented**, and **measured** behaviour.

The supplied target-application report marks the target web application as complete while listing the RPA Bot, Parser/Watcher, Diagnosis/Fingerprinting Engine, IBM Bob Integration, Patch/Verification System, and Dashboard/Human Approval as in progress at the time that component report was written.

Separately, the later Bob session report documents development and integration of the broader system through a merge to `main`.

Therefore, the safest overall interpretation is:

> **BotMedic was developed as an integrated hackathon prototype with a completed and verified target application and substantial implementation across the RPA, recovery, Bob, patching, and orchestration layers; some end-to-end performance characteristics were not formally measured in the supplied reports.**

The reports do **not** provide reliable measured values for:

- end-to-end recovery success rate
- average recovery time
- deterministic-engine false-positive rate
- IBM Bob escalation rate across all demo scenarios

These metrics were identified as future integration-test measurements.

---

## 17. Limitations

BotMedic remains a hackathon prototype.

### Production scale

The system has not been validated under production-scale conditions.

### Target application scope

The demonstrated environment is a fictional banking application. The recovery approach is designed to be general, but broad enterprise validation is still required.

### Fingerprint persistence

The target-application report describes in-memory/local fingerprint storage during the hackathon. A production implementation would need a persistent, versioned fingerprint database.

### Web UI focus

The current recovery model is focused on HTML/web UI elements.

Native desktop applications such as Windows or Java applications use different accessibility mechanisms and require additional support.

### Complex multi-attribute drift

The demo primarily exercises controlled changes such as ID changes, text changes, and DOM movement. Simultaneous changes across many attributes are more difficult and were not fully validated in the supplied evidence.

### Performance metrics

Formal benchmarks for recovery rate, latency, false positives, and Bob escalation were not yet available in the supplied reports.

---

## 18. Future Roadmap

The project documentation identifies several logical next steps.

### 1. Production fingerprint store

Move from local/in-memory fingerprint storage to a persistent, versioned database.

### 2. Better multi-attribute recovery

Improve candidate scoring when several UI attributes change at once.

### 3. Cross-browser support

Validate that fingerprints remain useful across different browsers.

### 4. Desktop RPA

Extend the fingerprint and recovery model to native desktop UI frameworks.

### 5. Learning from previous repairs

Use successful recoveries to improve scoring weights over time.

### 6. Deeper IBM Bob reasoning

Expand Bob's role from selector repair to more complex sub-workflow restructuring when appropriate.

### 7. CI/CD integration

Automatically trigger recovery workflows when application deployments introduce UI changes.

### 8. Stronger production governance

Expand audit trails, authentication, approval policies, deployment controls, and operational monitoring before enterprise adoption.

---

## 19. Why the Architecture Is Strong

The most important architectural decision is that BotMedic is **not simply an AI selector fixer**.

Instead, it separates the problem into increasingly powerful levels:

```text
Simple / predictable
        │
        ▼
Deterministic heuristics
        │
        ▼
Structured candidate scoring
        │
        ▼
IBM Bob reasoning
        │
        ▼
Execution verification
        │
        ▼
Human approval when risk demands it
```

This has several advantages:

- lower unnecessary AI usage
- lower latency for simple cases
- more explainable recovery
- reproducible decisions
- safer deployment
- easier auditing
- clearer separation of responsibilities

The architecture also reflects the modularity principles discussed with IBM Bob: components have distinct responsibilities and communicate through structured interfaces.

---

## 20. Key Innovation

The project's central innovation is the combination of:

**RPA + UI fingerprinting + deterministic self-healing + IBM Bob + execution-based verification + risk-aware human governance.**

Instead of asking an AI model to guess the correct selector every time, BotMedic first asks:

> “Can the evidence already identify the element with high confidence?”

Only when the answer is uncertain does it ask IBM Bob to reason over the richer context.

Then, regardless of whether the fix came from deterministic logic or AI, the system asks a second and more important question:

> “Does the repaired bot actually work?”

This creates a closed recovery loop:

```text
SUCCESS
   │
   ▼
FINGERPRINT
   │
   ▼
UI DRIFT
   │
   ▼
FAILURE
   │
   ▼
DIAGNOSE
   │
   ├── confident ──► deterministic fix
   │
   └── ambiguous ──► IBM Bob
                         │
                         ▼
                     proposed fix
                         │
                         ▼
                   patch a copy
                         │
                         ▼
                    re-run bot
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
           PASS                    FAIL
              │                     │
              ▼                     ▼
         risk check              reject
              │
       ┌──────┴──────┐
       ▼             ▼
    low/medium      high
       │             │
       ▼             ▼
   auto-deploy    human review
```

---

## 21. Final Conclusion

BotMedic presents a practical approach to one of the persistent problems in enterprise RPA: automation can remain logically correct while becoming technically broken because its target application's UI changes.

The project turns that maintenance problem into a structured recovery process.

It captures the state of successful interactions, detects selector failures, compares the current interface against historical fingerprints, attempts deterministic recovery first, and uses IBM Bob only when the evidence is ambiguous. Every proposed repair is tested through actual bot execution, and high-risk actions remain subject to human approval.

The project also demonstrates an important principle for AI-assisted engineering: **AI should augment deterministic engineering rather than replace it**. Clear cases can be handled predictably and cheaply, while IBM Bob is reserved for situations that benefit from contextual reasoning.

The supplied reports show meaningful development activity across the target application, RPA bot, parser/watcher, diagnosis engine, patching flow, risk handling, and IBM Bob integration, alongside practical lessons from running the system with IBM RPA Studio.

Although the current implementation is a hackathon prototype and lacks production-scale validation and comprehensive performance measurements, the architecture provides a credible foundation for a future enterprise self-healing RPA platform.

**BotMedic's core proposition is therefore:**

> **When an RPA bot breaks because the UI changes, don't immediately send a developer to fix it. Remember what the element looked like, diagnose what changed, repair it safely, prove the repair works, and involve a human only when the system genuinely needs one.**

---

## 22. Source and Evidence Notes

This final report consolidates the five teammate reports supplied for the project:

1. **IBM Bob Chat Session Report — IBM-Hackathon / BotMedic**
   - Documents the VS Code/Bob session, UI-break implementation, and visible completion state.

2. **IBM Bob Chat Session Report — BotMedic teammate contribution**
   - Documents software modularity and Human-in-the-Loop governance discussions.

3. **IBM Bob Session Report — Team BobVanta / Ahmed Elshikh**
   - Documents the major development session, Bob usage, implementation work, RPA Studio integration issues, and integration through `main`.

4. **BotMedic — Automated RPA Robots Handling and Correction System**
   - Provides the principal project architecture, workflow, fingerprinting, diagnosis, IBM Bob, verification, risk, target application, limitations, and conclusion.

5. **BotMedic — Automated RPA Robots Handling and Correction System — Plan**
   - Provides the planned adapter, backend, database, resolution engine, Bob worker, dashboard, and local development architecture.

Where the supplied reports differed in status or naming, this report preserves the distinction rather than inventing a definitive claim that the source material does not support.

---

## 23. Project Snapshot

| Category | Summary |
|---|---|
| Project | BotMedic |
| Team | Team BobVanta |
| Event | IBM TechXchange 2026 Hackathon |
| Core problem | RPA failures caused by UI/selector drift |
| Core solution | Self-healing RPA maintenance layer |
| AI component | IBM Bob |
| First-line recovery | Deterministic candidate scoring |
| Safety mechanism | Patch copy + bot re-run verification |
| Governance | Risk tiers + Human-in-the-Loop approval |
| Demo application | NorthBridge Bank |
| Demo break cases | ID, text, DOM movement, export selector |
| RPA platform used in demo | IBM RPA Studio |
| Target UI technology | HTML, CSS, vanilla JavaScript |
| Planned backend | Node.js / Express |
| Planned database | PostgreSQL |
| Planned dashboard | React |
| Integration model | Adapter + HTTP API |
| Current maturity | Hackathon prototype |
| Major future direction | Production-scale, multi-attribute, cross-platform self-healing RPA |

---

**End of Report**

*Prepared by consolidating the supplied Team BobVanta / BotMedic project reports. Claims are limited to what those reports document.*

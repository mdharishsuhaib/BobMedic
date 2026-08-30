# BotMedic
## Automated RPA Robots Handling and Correction System

---

**Event:** IBM TechXchange 2026 Hackathon
**Team Name:** Team BobVanta
**Date:** 2026

---

&nbsp;

---

## Abstract

Robotic Process Automation (RPA) bots are brittle by design. They identify and interact with UI elements using precise selectors — element IDs, CSS classes, XPath expressions, or DOM paths. When the application under automation changes, even slightly, these selectors break. The bot fails, and a developer must manually locate the new element and update the automation script. In organisations running dozens or hundreds of RPA workflows, this maintenance burden is significant.

BotMedic is a self-healing layer for RPA automation. It monitors bots for failure, captures rich multi-attribute fingerprints of UI elements during successful runs, and uses those fingerprints to automatically identify replacement elements when a failure occurs.

The recovery process is intentionally layered. The majority of real-world UI changes — an ID rename, a class update, a minor text change — are straightforward enough to be resolved deterministically by scoring and ranking candidate elements without involving AI. Only genuinely ambiguous cases are escalated to IBM Bob, the AI component, which analyses the failure context and proposes a solution in natural language.

Critically, AI-generated fixes are not applied blindly. Every proposed patch is tested by re-running the original RPA bot against a modified copy of the target UI. The result is verified before the fix is accepted. For high-risk automations — such as payment submissions — human approval is required before the patch is deployed to production.

The expected benefit is a significant reduction in manual RPA maintenance effort, faster recovery from UI drift, and a more trustworthy automation pipeline overall.

---

&nbsp;

---

## Table of Contents

1. Introduction
2. Problem Statement
3. Proposed Solution
4. System Architecture
5. End-to-End Workflow
6. UI Element Fingerprinting
7. Deterministic Diagnosis Engine
8. IBM Bob Integration
9. Patch and Verification System
10. Risk Classification and Human Approval
11. Target Web Application (Demo Component)
12. Implementation Status
13. Limitations and Future Work
14. Conclusion

---

&nbsp;

---

## 1. Introduction

### What is RPA?

Robotic Process Automation (RPA) is a technology that allows software bots to automate repetitive, rule-based tasks that would otherwise require a human to operate a computer. These bots interact with applications the same way a human does — by reading the screen, clicking buttons, filling forms, and extracting data — but they do so automatically, at speed, and without breaks.

RPA is widely used in finance, banking, healthcare, and back-office operations to handle tasks such as invoice processing, data entry, report generation, and payment authorisation. It does not require any integration with the underlying application's source code or APIs; the bot simply operates on the visible UI.

### Why RPA Bots Break

RPA bots navigate an application by identifying elements using selectors — a selector is essentially a description of how to find a specific element in the page. Common selectors include:

- **ID attributes** (`#btn-login`)
- **CSS class names** (`.btn.primary`)
- **XPath expressions** (`//form[@id='login']/button[@type='submit']`)
- **DOM path** (`form#login > div.actions > button`)
- **Visible text** (`"Sign in"`)

The problem is that selectors are fragile. Any time an application is updated — a redesign, a framework upgrade, a minor CSS refactor — the selectors that worked yesterday may no longer match any element today. The button still exists and still performs the same action, but the bot cannot find it.

This is not an edge case. In any actively developed application, UI changes happen regularly. A button gets a new ID in a refactor. A label changes from "Sign in" to "Login" for a copy update. A form gets restructured. Each of these changes can break one or more RPA workflows.

### The Manual Maintenance Problem

When an RPA bot fails due to a selector mismatch, the standard remediation process is entirely manual:

1. A developer is alerted to the failure (or discovers it themselves).
2. They open the application and inspect the changed element.
3. They update the selector in the bot's script.
4. They test the fix.
5. They re-deploy the bot.

In a small automation programme this is manageable. In a large enterprise with hundreds of bots, it becomes a continuous maintenance burden. Research from RPA vendors consistently identifies selector maintenance as one of the top causes of RPA project failure and abandonment.

### Motivation for BotMedic

BotMedic was conceived as a practical answer to this problem. Rather than requiring developers to manually hunt down changed elements, the system automatically detects failures, identifies the likely replacement element, and either applies the fix immediately (for clear-cut cases) or surfaces a pre-verified fix for human review (for complex or high-risk cases). The goal is not to eliminate human oversight — it is to make that oversight necessary only when it genuinely matters.

---

&nbsp;

---

## 2. Problem Statement

### The Core Issue

An RPA bot is configured to interact with a UI element by its selector. When that selector no longer matches the element in the current state of the application, the bot throws an error and stops. The element it was targeting has not disappeared — it has simply changed in some attribute that the bot was using to identify it.

### A Concrete Example

Consider a login workflow. The RPA bot is configured to click the login button using:

```
selector: #btn-login
```

At this point the button looks like this in the HTML:

```html
<button id="btn-login" class="btn primary" type="submit">Sign in</button>
```

The application is then updated. A developer renames the ID during a refactor:

```html
<button id="auth-submit-v2" class="btn primary" type="submit">Sign in</button>
```

The button is in the same place, has the same class, the same type, and the same visible text. It performs exactly the same action. But the RPA bot queries the DOM for `#btn-login`, finds nothing, and fails.

From the bot's perspective, the element no longer exists. From a human perspective, it is obviously still there.

### Why This Is Hard to Handle Automatically

Naively, one might suggest updating the selector. But the challenge is identification: when the bot fails, it knows _where_ it expected to find an element, but it does not know _which element_ on the current page is the correct replacement. There may be dozens of buttons on the page. Some may be visually or structurally similar to the original. Without a record of what the original element looked like across multiple attributes, there is no principled way to identify the replacement.

### Types of UI Changes BotMedic Addresses

| Change Type | Example |
|---|---|
| ID rename | `btn-login` → `auth-submit-v2` |
| Class change | `btn primary` → `btn primary-action` |
| Text change | `"Sign in"` → `"Login"` |
| DOM movement | Button moved to a different container div |
| Combined changes | Multiple attributes change simultaneously |

---

&nbsp;

---

## 3. Proposed Solution

### BotMedic as a Self-Healing Layer

BotMedic sits between the RPA bot and the target application. It does not replace the bot or require modifications to the application. It is an autonomous recovery layer that intercepts failures and attempts to resolve them.

The system is designed around three principles:

**1. Fingerprint elements during success**
When the bot runs successfully, BotMedic records a detailed fingerprint of every UI element the bot interacted with. The fingerprint captures not just the selector that was used, but a wide set of attributes — tag name, visible text, all HTML attributes, DOM path, position in the page, and neighbouring elements. This creates a rich, multi-attribute description of the element that is robust to partial changes.

**2. Use deterministic recovery first**
When a failure occurs, BotMedic collects all candidate elements from the current page that are plausibly related to the failed step. It scores each candidate against the stored fingerprint using a deterministic algorithm. If one candidate scores significantly above the others, the fix is applied immediately without involving AI. The majority of real UI changes — single-attribute changes like an ID rename — are expected to be resolvable this way.

**3. Escalate to IBM Bob only when necessary**
If no candidate achieves a confident score — because multiple elements are similar, or because too many attributes changed at once — the case is escalated to IBM Bob. Bob receives the original fingerprint, the current page structure, and the failure context, and proposes a fix. That fix is then verified by re-running the bot before it is accepted.

### What BotMedic Does Not Do

- It does not modify the target application.
- It does not require access to the application's source code.
- It does not automatically deploy fixes to production for high-risk workflows.
- It does not guarantee success in all cases. Some failures will still require human intervention.

---

&nbsp;

---

## 4. System Architecture

BotMedic consists of seven major components. Each component has a clearly defined responsibility and communicates with the others through structured events and data.

### Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        BotMedic System                      │
│                                                             │
│  ┌───────────────┐     ┌────────────────────────────────┐   │
│  │  Target Web   │◄────│          RPA Bot               │   │
│  │  Application  │     │  (runs automation scripts)     │   │
│  └──────┬────────┘     └────────────┬───────────────────┘   │
│         │                           │                        │
│         │                    ┌──────▼──────────────────┐    │
│         │                    │  Parser & Failure        │    │
│         └───────────────────►│  Watcher                 │    │
│                               └──────┬──────────────────┘    │
│                                      │                        │
│                               ┌──────▼──────────────────┐    │
│                               │  Diagnosis &             │    │
│                               │  Fingerprinting Engine   │    │
│                               └──────┬──────────────────┘    │
│                                      │                        │
│               ┌──────────────────────┼────────────────────┐  │
│               │                      │                     │  │
│        ┌──────▼──────┐        ┌──────▼──────────────┐     │  │
│        │  Deterministic│       │  IBM Bob             │     │  │
│        │  Recovery    │       │  Integration         │     │  │
│        └──────┬───────┘       └──────┬───────────────┘     │  │
│               └──────────────────────┘                      │  │
│                              │                               │  │
│                       ┌──────▼──────────────────┐           │  │
│                       │  Patch & Verification    │           │  │
│                       │  System                  │           │  │
│                       └──────┬──────────────────┘           │  │
│                              │                               │  │
│                       ┌──────▼──────────────────┐           │  │
│                       │  Dashboard / Human       │           │  │
│                       │  Approval Interface      │           │  │
│                       └─────────────────────────┘           │  │
└─────────────────────────────────────────────────────────────┘
```

### Component Descriptions

#### 4.1 Target Web Application

The application that the RPA bot is automating. In the BotMedic prototype, this is **NorthBridge Bank** — a fictional internal banking portal built with plain HTML, CSS, and vanilla JavaScript. It contains three functional pages: a login page, an invoice management page, and a payment submission page.

The application includes a hidden **Break Control Panel** (`/break.html`) that allows the demo team to intentionally alter UI elements at runtime without modifying source code. Four break scenarios are supported:

| Break Scenario | Normal State | Broken State |
|---|---|---|
| Rename login button ID | `id="btn-login"` | `id="auth-submit-v2"` |
| Move login button | Inside `#login-btn-container` | Inside `#login-btn-container-alt` |
| Change login button text | `"Sign in"` | `"Login"` |
| Rename export button ID | `id="btn-export"` | `id="export-data-btn"` |

Break states are stored in `localStorage` and applied dynamically on page load. This allows the demo to show a bot succeeding, a UI change being applied, and the bot failing — all without server-side changes.

#### 4.2 RPA Bot

The automated script that drives the target application. In the BotMedic project, two bots are used:

- **Login Bot** — navigates to the login page, fills in credentials, and clicks the submit button.
- **Export Bot** — navigates to the invoice page and clicks the CSV export button.

The bots are configured with the original selectors from the initial working state of the application. When a UI break is applied, the bots fail because those selectors no longer match.

The RPA Bot component is being developed by a separate team member.

#### 4.3 Parser and Failure Watcher

A monitoring component that observes the RPA bot's execution. Its responsibilities are:

- Detecting when the bot encounters a selector failure.
- Capturing a structured failure event that records which step failed, which selector was used, and the state of the DOM at the time of failure.
- Forwarding the failure event to the Diagnosis Engine.

During a successful run, this component also captures the live DOM state at each successful interaction step so that fingerprints can be built.

The Parser and Failure Watcher is being developed by a separate team member.

#### 4.4 Diagnosis and Fingerprinting Engine

The central intelligence component of BotMedic. Its responsibilities are:

- **Fingerprinting:** Building and storing multi-attribute fingerprints for each bot interaction step during successful runs.
- **Candidate collection:** When a failure is received, scanning the current page DOM for elements that could plausibly be the replacement for the failed element.
- **Candidate scoring:** Scoring each candidate against the stored fingerprint using a deterministic weighted-attribute algorithm.
- **Recovery decision:** If a single candidate scores above a confidence threshold, issuing a repair directly. If not, escalating to IBM Bob.

This component is being developed by a separate team member.

#### 4.5 IBM Bob Integration

The AI layer that handles ambiguous failures. IBM Bob is IBM's AI coding assistant. When the Diagnosis Engine cannot confidently identify a replacement element, it sends a structured prompt to Bob containing:

- The original fingerprint of the failed element.
- The current DOM structure around the failure location.
- A description of the failure.

Bob analyses the context and proposes a fix — typically identifying which current element most likely corresponds to the original, and suggesting an updated selector. The response is parsed and handed to the Patch and Verification System.

Bob is consulted only when deterministic recovery fails. This keeps AI usage targeted and avoids unnecessary latency and cost on straightforward failures.

#### 4.6 Patch and Verification System

Responsible for applying and validating proposed fixes. Its workflow is:

1. Receive a proposed fix (from either the deterministic engine or IBM Bob).
2. Apply the fix to a copy of the bot configuration.
3. Re-run the bot against the target application using the patched configuration.
4. Observe whether the bot step succeeds.
5. If successful, mark the fix as verified and pass it downstream.
6. If unsuccessful, reject the fix and escalate further or notify the human operator.

The verification step is critical. AI-generated fixes are not accepted on the basis of the model's output alone — they must pass an actual execution test.

#### 4.7 Dashboard and Human Approval Interface

A web-based interface for human operators. It displays:

- Active bot runs and their current status.
- Detected failures and the recovery action taken.
- Fixes that are awaiting human approval.
- A history of past failures and resolutions.

Human approval is required before a verified fix is deployed to production for high-risk workflows (see Section 10). For low-risk workflows, fixes may be applied automatically after verification.

The Dashboard is being developed by a separate team member.

---

&nbsp;

---

## 5. End-to-End Workflow

The following describes the complete lifecycle of a BotMedic-assisted recovery from initial success through failure detection to resolution.

```
Step 1:  RPA bot runs successfully
│
Step 2:  Fingerprint each interacted element
│
Step 3:  (Later) UI changes are applied to the application
│
Step 4:  RPA bot runs again and encounters a selector failure
│
Step 5:  Failure Watcher captures structured failure event
│
Step 6:  Diagnosis Engine collects candidate elements from current DOM
│
Step 7:  Candidates are scored against the stored fingerprint
│
┌──┴──────────────────────┐
│                         │
High confidence           Low confidence /
match found                Ambiguous
│                         │
Step 8:  Apply fix              Escalate to IBM Bob
deterministically              │
│                    IBM Bob proposes fix
└──────────┬──────────────┘
│
Step 9:  Apply proposed patch to a bot config copy
│
Step 10: Re-run bot with patched config
│
Step 11: Verify result
│
┌──────────┴──────────────┐
│                         │
Verification               Verification
passes                      fails
│                         │
Step 12: Check risk tier        Reject fix, notify operator
│
┌────┴────────────────────┐
│                         │
Low/Medium risk           High risk
│                    (e.g. payment)
│                         │
Auto-deploy              Request human approval
│
Human reviews and approves
│
Deploy to production
```

### Step Descriptions

| Step | Description |
|---|---|
| 1 | Bot executes normally. Every step succeeds. |
| 2 | For each step, the Parser captures the target element's attributes, geometry, DOM path, and neighbours. A fingerprint record is stored. |
| 3 | The application is updated. One or more UI attributes change on elements the bot interacts with. |
| 4 | Bot runs again. A step fails because the selector no longer finds the element. |
| 5 | The Failure Watcher detects the exception, records the failed step ID, the selector used, and the DOM snapshot at the time of failure. A structured failure event is sent to the Diagnosis Engine. |
| 6 | The Diagnosis Engine queries the current DOM for all candidate elements (same tag type, or elements within a reasonable spatial vicinity). |
| 7 | Each candidate is scored against the stored fingerprint using a weighted comparison of attributes (see Section 7). |
| 8 | If one candidate scores above the confidence threshold, the fix is applied directly. Otherwise, the failure context is sent to IBM Bob. |
| 9 | The proposed fix (a new selector or element reference) is applied to a staging copy of the bot configuration. |
| 10 | The bot is re-run against the application using the patched configuration. |
| 11 | The outcome is observed. A pass means the step succeeded. A fail means the proposed fix was wrong. |
| 12 | The risk tier of the automation step is checked. Payment-related steps, steps that write data, and steps classified as irreversible are treated as high-risk. |
| 13 | Low/medium-risk fixes with passing verification are deployed automatically. High-risk fixes are queued for human review on the Dashboard. |

---

&nbsp;

---

## 6. UI Element Fingerprinting

### What a Fingerprint Is

A fingerprint is a structured record of a UI element at the moment it was successfully interacted with. Rather than recording only the selector that the bot used (which would be just as fragile), BotMedic records every available attribute of the element. This redundancy is what enables recovery when one or more attributes change.

### Fingerprint Structure

The following JSON represents the fingerprint schema used in BotMedic:

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

### Field Descriptions

| Field | Description |
|---|---|
| `step_id` | A stable identifier for this automation step, defined in the bot script. Does not change when the UI changes. |
| `tag` | The HTML tag of the element (`button`, `a`, `input`, etc.). |
| `text` | The visible text content of the element. |
| `attrs.id` | The element's `id` attribute. |
| `attrs.class` | The element's `class` attribute. |
| `attrs.type` | The element's `type` attribute (especially relevant for `input` and `button`). |
| `dom_path` | A CSS selector representing the element's path from an ancestor. Captures structural position. |
| `neighbors.prev_label` | The text of the nearest preceding label element. Provides semantic context. |
| `geometry` | The element's bounding box in pixels. Captures spatial position on the page. |

### Why Multiple Attributes?

Each attribute alone is fragile. An ID can be renamed. Text can be translated or reworded. A CSS class can be refactored. But it is unusual for all attributes to change simultaneously. By recording all of them, BotMedic ensures that even if two or three attributes change, the remaining ones still provide enough signal to identify the correct replacement element.

The fingerprint for the NorthBridge Bank login button illustrates this: even if the `id` changes from `btn-login` to `auth-submit-v2`, the element still has `class="btn primary"`, `type="submit"`, text `"Sign in"`, the same DOM position relative to the form, and the same screen geometry. That combination is distinctive enough to uniquely identify the element among all buttons on the page.

---

&nbsp;

---

## 7. Deterministic Diagnosis Engine

### How Candidates Are Scored

When a failure occurs, the Diagnosis Engine collects candidate elements from the current page. A candidate is any element of the same tag type that could plausibly represent the same UI action. The engine then scores each candidate by comparing its current attributes against the stored fingerprint.

Each attribute contributes a weighted score. Attributes that are more stable over time and more semantically meaningful receive higher weights. Attributes that change frequently (like an auto-generated ID) receive lower weights.

### Conceptual Scoring Weights

The following table illustrates the general weighting approach. Exact weights are part of the Diagnosis Engine implementation and are subject to tuning.

| Attribute | Weight (indicative) | Rationale |
|---|---|---|
| Visible text | High | Text is semantic and rarely changes without intent |
| `type` attribute | High | Rarely changed; describes the element's function |
| `class` | Medium-high | Stable in most codebases; may change in refactors |
| `dom_path` | Medium | Structural; changes when layout is restructured |
| Spatial geometry | Medium | Stable unless layout is significantly redesigned |
| `id` | Medium-low | Frequently renamed in refactors |
| Neighbouring label | Medium | Provides semantic context; stable in most cases |

### Recovery Decision

After scoring all candidates, the engine selects the highest-scoring candidate. If that score exceeds a defined confidence threshold — and the gap between the top candidate and the second-best candidate is large enough to rule out ambiguity — the fix is applied deterministically.

If no candidate is sufficiently confident, the case is escalated to IBM Bob.

### What "Deterministic" Means Here

"Deterministic" means that for the same failure event and the same set of candidates, the engine will always produce the same scoring result and the same decision. There is no randomness and no model inference involved. This makes the recovery predictable, auditable, and explainable to a human reviewer.

---

&nbsp;

---

## 8. IBM Bob Integration

### Role of IBM Bob

IBM Bob is consulted when the deterministic diagnosis engine cannot identify a replacement element with sufficient confidence. This occurs when:

- Multiple candidates have similar scores and there is no clear winner.
- Too many attributes have changed simultaneously for the scoring to be reliable.
- The structural change is complex (e.g., a component was replaced entirely).

### What Is Sent to Bob

The following information is included in the prompt sent to IBM Bob:

1. The original fingerprint of the failed element (full JSON as described in Section 6).
2. A description of the failure: which step failed, which selector was used.
3. The current DOM structure of the relevant page section.
4. A list of candidate elements and their attributes.
5. A request to identify which candidate most likely represents the original element, and why.

### What Bob Returns

Bob responds with a natural language analysis and a concrete suggestion — typically identifying a specific element and providing an updated selector or set of attributes that should be used. The response is parsed by the integration layer to extract the actionable fix.

### Important Constraint

Bob's response is treated as a hypothesis, not a ground truth. The proposed fix is only accepted if it passes the re-run verification step (see Section 9). If Bob's suggestion fails verification, it is rejected and the failure is escalated to the human operator.

This design ensures that the system does not blindly trust AI output and that every fix that reaches production has been empirically validated.

---

&nbsp;

---

## 9. Patch and Verification System

### Purpose

The Patch and Verification System ensures that no fix — whether from the deterministic engine or from IBM Bob — is applied to a live bot without first being confirmed to actually work.

### Verification Process

1. **Patch preparation:** The proposed fix is applied to a staging copy of the bot's configuration. The original configuration is not modified.
2. **Re-execution:** The bot is re-run using the patched configuration, starting from the step that previously failed.
3. **Outcome observation:** The system observes whether the previously failing step now succeeds.
4. **Verification result:** If the step passes, the fix is marked as verified. If it fails again, the fix is rejected.

### Why Verification Matters

Without verification, the system could confidently propose a wrong fix and deploy it. This would change the bot's behaviour in a way that appears correct during recovery but produces incorrect results at runtime — for example, clicking the wrong button or submitting data to the wrong form field. Verification eliminates this class of error by treating the bot's own execution as the acceptance test.

---

&nbsp;

---

## 10. Risk Classification and Human Approval

### Risk Tiers

Not all automation steps carry the same risk if they are mis-repaired. BotMedic classifies automation steps into risk tiers:

| Risk Tier | Examples | Recovery Behaviour |
|---|---|---|
| Low | Read-only steps, navigation, login | Auto-deploy after verification |
| Medium | Data extraction, report generation | Auto-deploy after verification, notify operator |
| High | Payment submission, data writes, irreversible actions | Require explicit human approval |

### The Human Approval Flow

For high-risk steps, a verified fix is placed in a pending queue on the Dashboard. A human operator reviews:

- The original fingerprint of the element.
- The proposed new selector and which element it points to.
- The verification result (the bot succeeded with this fix).
- The nature of the change (what changed and why the bot broke).

The operator can approve the fix (deploy it to the live bot) or reject it (keep the bot suspended and investigate manually).

### Why Human Approval Cannot Be Bypassed for High-Risk Steps

Even a verified fix for a payment submission step carries risk. Verification confirms that the bot can _find and interact with_ the new element — it does not confirm that the new element is _semantically equivalent_ to the original. A human reviewer provides the final semantic check: is this the right button, in the right context, performing the right action?

---

&nbsp;

---

## 11. Target Web Application — NorthBridge Bank

### Purpose in the Project

The Target Web Application is a purpose-built demo component used to demonstrate and test the BotMedic system in a realistic setting. It is a fictional internal banking portal called **NorthBridge Bank — Internal Operations Portal**.

### What Was Built

The application was fully implemented as part of this project. It consists of:

**Three application pages:**

| Page | File | Primary Bot Target |
|---|---|---|
| Login | `index.html` | `#btn-login` — "Sign in" button |
| Invoice Management | `invoices.html` | `#btn-export` — "Download CSV" button |
| Payment Submission | `payment.html` | `#btn-pay` — "Submit payment" button |

**One hidden control panel:**

| Page | File | Purpose |
|---|---|---|
| Break Panel | `break.html` | Demo control panel for applying UI breaks |

### Technical Details

The application is implemented in plain HTML, CSS, and vanilla JavaScript with no framework, no build step, and no backend. It operates entirely in the browser and can be opened directly from the file system using `file://` — no web server is required.

**Login page:** Accepts any non-empty username and password and redirects to the invoice page. No real authentication.

**Invoice page:** Displays a table of eight fictional invoices with columns for Invoice Number, Client, Amount, Date, and Status. The "Download CSV" button generates and downloads a real CSV file containing the invoice data. The page includes multiple additional buttons and links (filter, search, import, archive, export PDF, pagination) to ensure that BotMedic's candidate ranking engine has realistic competing elements to reason about.

**Payment page:** A form with Recipient, Recipient Account (IBAN), Amount, Reference, and Value Date fields. The "Submit payment" button triggers a demo alert. No real data is processed.

### The Break Control Panel

The Break Control Panel at `break.html` is the mechanism that enables repeatable, code-free demo scenarios. It exposes four toggle switches, each of which modifies a specific UI attribute of a target element:

```
Toggle 1 — Rename Login Button ID
Normal:  id="btn-login"
Broken:  id="auth-submit-v2"

Toggle 2 — Move Login Button
Normal:  Inside div#login-btn-container
Broken:  Inside div#login-btn-container-alt (different DOM parent)

Toggle 3 — Change Login Button Text
Normal:  "Sign in"
Broken:  "Login"

Toggle 4 — Rename Export Button ID
Normal:  id="btn-export"
Broken:  id="export-data-btn"
```

State is stored in the browser's `localStorage`. App pages read this state on every load and apply the corresponding DOM mutations dynamically. Toggling a break off immediately restores the normal state on the next page load.

The break panel also includes a single-click "Reset All" button and an "Enable All Breaks" button for quick demo resets.

### RPA Target Element Fingerprints (Design)

The login button was designed specifically to support BotMedic fingerprinting. Its stable attributes are:

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
"dom_path": "form#login-form > div#login-btn-container > button"
}
```

When the ID is broken to `auth-submit-v2`, the element retains its `class`, `type`, `text`, and DOM position relative to the form. BotMedic's scoring engine should be able to identify it from those remaining signals alone.

No `data-testid` attributes were added to target elements, by design. The system must work from the same signals that a real, unmaintained UI would provide.

---

&nbsp;

---

## 12. Implementation Status

The following table reflects the implementation status of each component as of the hackathon submission. The target web application is the component built by this team member; other components are developed by the broader team.

| Component | Status | Notes |
|---|---|---|
| Target Web Application | ✅ Complete | All pages, break panel, localStorage toggles, CSV export |
| RPA Bot | 🔄 In progress | Being developed by a team member |
| Parser and Failure Watcher | 🔄 In progress | Being developed by a team member |
| Diagnosis / Fingerprinting Engine | 🔄 In progress | Being developed by a team member |
| IBM Bob Integration | 🔄 In progress | Being developed by a team member |
| Patch and Verification System | 🔄 In progress | Being developed by a team member |
| Dashboard / Human Approval | 🔄 In progress | Being developed by a team member |

### What Is Verified and Working

The following behaviours have been implemented and are verified to work locally:

- The NorthBridge Bank application loads correctly from `file://` with no server.
- The login form accepts any credentials and redirects to the invoices page.
- The invoice table renders 8 rows with correct data.
- The "Download CSV" button generates and downloads a correctly formatted CSV file.
- The payment form renders and the submit button triggers the demo alert.
- The break panel toggles persist state in `localStorage` across page loads.
- All four break scenarios correctly mutate the target element when toggled on.
- All four break scenarios correctly restore the original state when toggled off.
- The "Reset All" and "Enable All Breaks" buttons work correctly.
- Break state toggling is idempotent — toggling on then off then on produces consistent results.

### What Is Not Yet Measured

- End-to-end recovery success rate (requires the bot and diagnosis engine to be integrated).
- Average time to recovery.
- False positive rate of the deterministic diagnosis engine.
- IBM Bob escalation rate across the demo scenarios.

These metrics will be gathered during integration testing once all components are connected.

---

&nbsp;

---

## 13. Limitations and Future Work

### Current Limitations

**Prototype scope:** BotMedic is a hackathon prototype. The system has been designed with production concerns in mind, but it has not been tested under production conditions or at scale.

**Single target application:** The current demo is limited to the NorthBridge Bank application. The recovery logic has been designed to be general, but it has not yet been validated against real-world enterprise applications.

**No persistent fingerprint store:** The current design uses in-memory or local storage for fingerprints during the hackathon. A production system would require a persistent, versioned database of fingerprints per bot and per application.

**DOM-based only:** BotMedic currently fingerprints and recovers HTML/web UI elements. Desktop RPA (native Windows or Java applications) uses different accessibility APIs and is out of scope.

**Single-attribute changes tested:** The demo scenarios cover single-attribute changes (ID rename, text change, DOM movement). Scenarios involving simultaneous changes to multiple attributes are more challenging for the deterministic engine and have not been tested.

### Future Work

| Area | Description |
|---|---|
| Production fingerprint store | Persistent, versioned database with fingerprint history per bot step |
| Multi-attribute recovery | Improved scoring for cases where more than one attribute changes at once |
| Cross-browser support | Validation that fingerprints captured in one browser transfer correctly to another |
| Desktop RPA support | Extend the fingerprinting and recovery model to desktop UI frameworks |
| Learning over time | Use past successful recoveries to improve the scoring weights automatically |
| Deeper IBM Bob integration | Allow Bob to propose not just selector fixes, but entire sub-workflow restructurings |
| CI/CD integration | Trigger recovery runs automatically from a CI pipeline when an application deployment is detected |

---

&nbsp;

---

## 14. Conclusion

RPA maintenance is a significant and underappreciated problem. The selector fragility that causes bots to break on UI changes represents a real cost in developer time, bot downtime, and operational risk. BotMedic addresses this with a structured, layered approach: fingerprint elements during success, diagnose failures deterministically, escalate to AI only when necessary, verify every fix before applying it, and require human approval for high-risk actions.

The project demonstrates that self-healing RPA does not require AI for every failure. A well-designed deterministic engine, informed by rich multi-attribute fingerprints, can handle the majority of real UI drift automatically, predictably, and without the latency or cost of a model inference call on every error. IBM Bob is reserved for the cases that genuinely require reasoning — complex, multi-attribute changes where the correct answer is not obvious from the data alone.

The Target Web Application component delivers a realistic, controllable demo environment that allows the full BotMedic pipeline to be demonstrated against actual bot failures, with repeatable break scenarios and no requirement for any server or infrastructure beyond a browser.

---

&nbsp;

---

*Report prepared by Team BobVanta — IBM TechXchange 2026 Hackathon*
*Component: Target Web Application*
*Document version: 1.0*

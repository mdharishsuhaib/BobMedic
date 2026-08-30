# BotMedic — Automated RPA Robots Handling and Correction System
## Plan

---

## Top-Level Overview

**Goal:** Build BotMedic, a platform-agnostic system that monitors RPA robot executions, fingerprints UI elements on success, automatically resolves selector/timing failures using deterministic heuristics, and escalates only unresolvable failures to IBM Bob AI — then retests the fix via a full robot re-run before surfacing the result to developers on a React dashboard.

**Scope:**
- `packages/adapter` — npm adapter library robots import to emit failure reports
- `backend/` — Node.js API server (fingerprint store, resolution engine, Bob integration, retest orchestration)
- `frontend/` — React dashboard (failure feed, fix status, fingerprint browser)
- `db/` — PostgreSQL schema (fingerprints, failure reports, resolutions)

**Non-goals (for now):**
- Webhook / CI-CD feedback channel
- Support for a specific RPA platform SDK (all robots treated as black boxes)
- Fine-tuning or training IBM Bob

---

## Sub-Tasks

---

### Sub-Task 1 — Define the Failure Report Schema and Adapter Package

**Intent:**
Every other component depends on the shape of the data emitted when a robot fails. This sub-task nails down that contract and ships it as an importable npm package so robots can start using it immediately.

**Expected Outcomes:**
- A versioned JSON schema (`FailureReport`) is defined and exported from the adapter package
- The adapter package exposes a single `reportFailure(report)` function that robots call on failure
- The package has no runtime dependencies and works in any Node.js environment

**Todo List:**
1. Scaffold `packages/adapter` as a minimal npm package (`package.json`, `tsconfig.json`, `index.ts`)
2. Define the `FailureReport` TypeScript interface:
   - `robotId: string` — unique robot identifier
   - `stepId: string` — which automation step failed
   - `timestamp: string` — ISO 8601
   - `errorType: 'element_not_found' | 'timeout' | 'selector_mismatch' | 'unknown'`
   - `failedSelector: string` — the selector the robot tried
   - `pageUrl: string` — URL at the time of failure
   - `domSnapshotHash: string` — perceptual hash of DOM state
   - `screenshotBase64?: string` — optional screenshot
3. Implement `reportFailure(report: FailureReport, backendUrl: string): Promise<void>` — posts the report to the BotMedic backend via HTTP POST
4. Export a `captureSuccess(elementFingerprint: ElementFingerprint, backendUrl: string)` function robots call on step success to store fingerprints
5. Define the `ElementFingerprint` interface (see Sub-Task 2 for full schema)
6. Write a README with integration example

**Relevant Context:**
- This package lives in `packages/adapter/`
- Robots import it: `import { reportFailure, captureSuccess } from '@botmedic/adapter'`
- No database access — it only POSTs to the backend

**Status:** [ ] pending

---

### Sub-Task 2 — PostgreSQL Schema and Fingerprint Store

**Intent:**
Persist element fingerprints captured at success time and incoming failure reports so the resolution engine can query historical data and compute candidates.

**Expected Outcomes:**
- Database migrations create all required tables
- A data-access layer (DAL) in the backend can read/write fingerprints and failure reports
- The schema supports querying fingerprints by `robotId + stepId` for comparison

**Todo List:**
1. Create `db/migrations/001_initial.sql` with the following tables:
   - `fingerprints` — stores per-step element fingerprints (one row per successful capture, versioned by timestamp)
   - `failure_reports` — stores incoming failure reports from the adapter
   - `resolutions` — stores the outcome of each resolution attempt (method used, fix applied, retest result)
2. Define the `fingerprints` columns:
   - `id`, `robot_id`, `step_id`, `captured_at`
   - `element_type`, `text_label`, `css_selector`, `xpath`
   - `position_x`, `position_y`, `parent_chain` (JSONB), `aria_attributes` (JSONB)
   - `screenshot_hash`
3. Define the `failure_reports` columns:
   - `id`, `robot_id`, `step_id`, `received_at`
   - `error_type`, `failed_selector`, `page_url`, `dom_snapshot_hash`, `screenshot_base64`
   - `status` (enum: `pending`, `resolving`, `resolved`, `escalated`, `failed`)
4. Define the `resolutions` columns:
   - `id`, `failure_report_id`, `resolved_at`
   - `method` (enum: `selector_drift`, `label_drift`, `parent_scan`, `timing_retry`, `bob_ai`)
   - `fix_applied` (JSONB), `confidence_score`, `retest_passed`
5. Create a `backend/src/db/` DAL module with typed query functions using `pg` or `postgres` npm package
6. Add a `db/seed.sql` with example data for local development

**Relevant Context:**
- `fingerprints` is the core store — it is written by `captureSuccess` and read by the resolution engine
- `parent_chain` and `aria_attributes` are stored as JSONB because they are variable-depth structures
- The `status` field on `failure_reports` drives the resolution workflow state machine

**Status:** [ ] pending

---

### Sub-Task 3 — Backend API Server (Ingest + Fingerprint Endpoints)

**Intent:**
Stand up the Node.js/Express server with the two ingest endpoints the adapter calls: one to store element fingerprints on success, one to receive failure reports and kick off resolution.

**Expected Outcomes:**
- `POST /api/fingerprint` — validates and stores an `ElementFingerprint`
- `POST /api/failure` — validates and stores a `FailureReport`, sets status to `pending`, and enqueues it for resolution
- Both endpoints return structured JSON responses
- Input validation rejects malformed payloads with a 400 error

**Todo List:**
1. Scaffold `backend/` as a Node.js project with TypeScript, Express, and `zod` for validation
2. Create `backend/src/routes/fingerprint.ts` — handles `POST /api/fingerprint`
3. Create `backend/src/routes/failure.ts` — handles `POST /api/failure`, writes to `failure_reports`, then calls `resolutionQueue.enqueue(reportId)`
4. Create `backend/src/validation/schemas.ts` — Zod schemas matching the adapter interfaces
5. Create `backend/src/app.ts` — Express app wiring routes and middleware
6. Create `backend/src/server.ts` — entry point that reads `PORT` and `DATABASE_URL` from environment
7. Add a health check endpoint `GET /api/health`

**Relevant Context:**
- The adapter (`packages/adapter`) posts to the URLs configured by the robot integrator
- Validation schemas must match `FailureReport` and `ElementFingerprint` exactly — they should be derived from the adapter package types
- The resolution queue introduced here is a simple in-process async queue (no broker needed at this stage)

**Status:** [ ] pending

---

### Sub-Task 4 — Deterministic Resolution Engine

**Intent:**
Before IBM Bob is ever called, the resolution engine tries up to four deterministic layers to identify the correct element. Only if no candidate scores above the confidence threshold (configurable, default 0.75) does it escalate.

**Expected Outcomes:**
- The resolution engine takes a `FailureReport` + its historical `ElementFingerprint` records and returns either a `Resolution` or an `EscalationRequest`
- Each layer runs in order and short-circuits as soon as a candidate scores above threshold
- The engine is a pure function module (no direct DB calls — takes data in, returns a result)

**Todo List:**
1. Create `backend/src/resolution/engine.ts` — the main orchestrator that runs layers in order
2. Implement **Layer 1 — Selector Drift**: fuzzy-match the failed selector against stored CSS selectors and XPaths using edit-distance scoring
3. Implement **Layer 2 — Label/Text Drift**: find elements in the DOM snapshot whose text/label closely matches the stored `text_label` using normalized string similarity
4. Implement **Layer 3 — Parent Container Scan**: walk the stored `parent_chain` and locate the element in a sibling or child position within the same container
5. Implement **Layer 4 — Timing/Timeout Retry**: if `errorType === 'timeout'`, return a retry-with-increased-wait resolution immediately (no scoring needed)
6. Create `backend/src/resolution/scoring.ts` — shared confidence scoring helpers
7. Create `backend/src/resolution/types.ts` — `Resolution`, `EscalationRequest`, `CandidateMatch` interfaces
8. Create `backend/src/config.ts` — reads `CONFIDENCE_THRESHOLD` (default `0.75`) from environment
9. Write unit tests for each layer in `backend/src/resolution/__tests__/`

**Relevant Context:**
- The engine is called by the resolution queue worker (Sub-Task 5)
- Layer 4 is the only layer that does not require a DOM snapshot or fingerprint comparison — it is purely based on `errorType`
- The threshold being configurable is important for tuning without redeployment

**Status:** [ ] pending

---

### Sub-Task 5 — Resolution Queue Worker and IBM Bob Escalation

**Intent:**
Wire the resolution engine into an async worker that processes failure reports from the queue, calls IBM Bob when needed, and writes the resolution outcome back to the database.

**Expected Outcomes:**
- The queue worker picks up `pending` failure reports and runs the resolution engine
- On deterministic success: writes resolution to DB, marks report as `resolved`, triggers retest
- On escalation: calls IBM Bob with the structured summary, applies the returned fix, triggers retest
- On Bob failure or no fix: marks report as `failed`

**Todo List:**
1. Create `backend/src/workers/resolutionWorker.ts` — async loop that polls `failure_reports` for `pending` rows and processes them
2. Implement the Bob escalation client in `backend/src/integrations/bobClient.ts`:
   - Accepts `{ originalFingerprint, candidateList, failureReason }` as the request body
   - POSTs to the IBM Bob API endpoint (URL configured via `BOB_API_URL` env var)
   - Parses the response as `{ suggestedSelector: string, confidence: number }`
3. After resolution (deterministic or Bob), trigger a full robot re-run via `backend/src/integrations/robotRunner.ts`:
   - Sends a `POST /rerun` request to the robot's registered callback URL
   - Waits for a retest result response
   - Writes `retest_passed` to the `resolutions` table
4. Update `failure_report.status` at each stage: `resolving` → `resolved` or `escalated` → `resolved` or `failed`
5. Add structured logging at each stage (which layer resolved, Bob confidence, retest result)

**Relevant Context:**
- `BOB_API_URL` must be set in the environment — the client should throw clearly if it is missing
- The robot re-run is a full robot execution (not just a single selector replay)
- `robotRunner.ts` uses the `robotId` to look up the robot's registered callback URL from the DB

**Status:** [ ] pending

---

### Sub-Task 6 — React Dashboard

**Intent:**
Give developers a live view of failure reports, resolution status, and the fingerprint history for each robot/step — replacing the need for any webhook integration.

**Expected Outcomes:**
- A React app with three main views: Failure Feed, Resolution Detail, and Fingerprint Browser
- The Failure Feed auto-refreshes and shows real-time status per report
- The Resolution Detail shows the resolution method, confidence score, fix applied, and retest result
- The Fingerprint Browser lets developers inspect stored fingerprints per robot/step

**Todo List:**
1. Scaffold `frontend/` with Vite + React + TypeScript
2. Create `frontend/src/api/client.ts` — typed fetch wrappers for backend endpoints
3. Build the **Failure Feed** page (`/failures`):
   - Table of failure reports with columns: Robot, Step, Error Type, Status, Received At
   - Status color-coded: pending=yellow, resolved=green, escalated=blue, failed=red
   - Auto-refresh every 10 seconds
4. Build the **Resolution Detail** page (`/failures/:id`):
   - Shows original fingerprint vs. applied fix side-by-side
   - Displays resolution method, confidence score, and whether the retest passed
   - Shows Bob's response if escalation was used
5. Build the **Fingerprint Browser** page (`/fingerprints`):
   - Filter by Robot ID and Step ID
   - Shows fingerprint history timeline per step
6. Add a minimal nav bar and a backend health indicator
7. Add backend API endpoints to serve dashboard data:
   - `GET /api/failures` — paginated list
   - `GET /api/failures/:id` — detail with resolution
   - `GET /api/fingerprints` — filterable list

**Relevant Context:**
- No auth is required at this stage
- The dashboard is the only developer feedback channel (no webhooks)
- The backend already has a health endpoint at `GET /api/health` from Sub-Task 3

**Status:** [ ] pending

---

### Sub-Task 7 — Project Wiring, Config, and Local Dev Setup

**Intent:**
Make the full system runnable locally with a single command and document how robots integrate with BotMedic.

**Expected Outcomes:**
- `docker-compose.yml` starts PostgreSQL, the backend, and the frontend together
- A root `README.md` documents the full integration flow for robot developers
- Environment variable documentation covers all required and optional vars

**Todo List:**
1. Create `docker-compose.yml` with services: `db` (postgres:15), `backend`, `frontend`
2. Create `.env.example` listing all environment variables:
   - `DATABASE_URL`, `PORT`, `CONFIDENCE_THRESHOLD`, `BOB_API_URL`
3. Create root `package.json` with workspace scripts: `dev`, `build`, `test`, `migrate`
4. Create `db/migrate.ts` — runs all SQL migration files in order against `DATABASE_URL`
5. Write root `README.md` covering:
   - System architecture overview
   - How to run locally
   - How a robot integrates the adapter package
   - Environment variable reference

**Relevant Context:**
- The adapter package (`packages/adapter`) is the primary integration touchpoint for robot developers
- The migration runner needs to run before the backend starts in the Docker compose startup order

**Status:** [ ] pending

---

## Architecture Diagram Reference

```
packages/adapter        →  POST /api/fingerprint   →  backend (fingerprint store)
                        →  POST /api/failure        →  backend (resolution queue)
                                                           ↓
                                                   Resolution Engine
                                                   Layer 1: Selector drift
                                                   Layer 2: Label drift
                                                   Layer 3: Parent scan
                                                   Layer 4: Timeout retry
                                                           ↓ (if no fix above threshold)
                                                   IBM Bob AI Client
                                                           ↓
                                                   Robot Re-run (full run)
                                                           ↓
                                                   PostgreSQL (resolutions table)
                                                           ↓
                                                   React Dashboard  ←  Developer
```

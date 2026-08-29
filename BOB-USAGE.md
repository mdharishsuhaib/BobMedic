# How IBM Bob Was Utilized — BotMedic

**IBM TechXchange 2026 Pre-conference Dev Day Hackathon**
**Project:** BotMedic — Self-healing IBM RPA Engine

---

## Overview

IBM Bob was used at every stage of this project: architecture design, implementation,
and as a live runtime component inside the diagnosis engine itself.

---

## 1. Plan Mode — Architecture Design

**Session:** "BotMedic Architecture"

Used Bob in Plan mode to design the four-component diagnosis pipeline
(Watcher → Parser → Diagnoser → Patcher), the fingerprint schema, and the
deterministic scoring weight system. Bob challenged the initial design of sending
all DOM data to the LLM and proposed the hybrid approach: deterministic scoring
first, Bob only for semantic ambiguity below the confidence threshold.

Key output: the fingerprint schema and scoring weights now in `AGENTS.md`.

---

## 2. Ask Mode — .wal Format Research

**Session:** "WAL file structure"

Used Bob in Ask mode to understand the IBM RPA `.wal` (WDG Automation Language)
file format before writing the parser. Bob explained the XML-based structure,
how selectors are stored, and which fields to target for the patch operation.

---

## 3. Agent Mode — Component Implementation

**Sessions:** Watcher, Parser, Diagnoser, Patcher, Dashboard (separate tasks)

Used Bob in Agent mode to implement each component. Bob wrote the code, ran
tests, and fixed issues — with human approval at each file write.

Notable: Bob identified that the Patcher must work on a `.wal` copy and never
modify the original, and added the copy-verify-commit pattern without being asked.

---

## 4. Bob at Runtime — Semantic Disambiguation

**This is the key differentiator.**

When the deterministic scorer returns confidence < 0.75 (element text or meaning
changed, not just the id), BotMedic invokes Bob Shell at runtime:

```bash
bob -p "$(cat diagnoser-prompt.txt)" --hide-intermediary-output > match-result.json
```

Bob receives: the original fingerprint, the top 3 scored candidates, and their
surrounding DOM context. It returns a structured JSON decision with a selected
candidate index and reasoning.

This makes Bob a live component of the production system — not just a tool used
to write the code.

---

## Bob Session Report

The full exported session report (all tasks and conversations) is included in
this repository as `bob-session-report.html`.



---
type: decision
tags: [architecture, cycle, automation, context-savings]
created: 2026-04-22
updated: 2026-05-12
owner: skill-lead
status: active
confidence: high
source: conversation
links:
  - learning-commit-code-state-exclusion
---

# Cycle Runner — Mechanical Shell / Agent Core Split

## Decision

Human proposed separating the Ralph Loop into a mechanical shell (Python scripts) and an agent creative core (Claude). Filed as #2057.

## Architecture

- **cycle_pre.py**: ensure branch, pull, context pressure, triage, read working state → writes `cycle-input.json`
- **Agent**: reads input, implements fixes, writes code, writes `cycle-output.json`
- **cycle_post.py**: commit code to branch, commit state to main, push, log iteration, transition statuses

## Rationale

- Branch switching bugs (see [[learning-commit-code-state-exclusion]]) caused by agent managing git state
- 15+ boilerplate bash calls per cycle burning context
- Deterministic mechanics shouldn't rely on LLM execution
- Agent should focus on creative work: reading code, reasoning, implementing

## Status

Shipped as #2057. cycle_pre.py / cycle_post.py are live and used by all agents since v0.33.0+. Next evolution: #7630 (event-driven architecture) proposes moving all mechanical operations into the harness, with agents reacting to events instead of running cycles.

## Changelog

- 2026-04-22 — Created by skill-lead. Human proposed during discussion about branch-switching bugs.
- 2026-05-12 — Updated by pm. Status corrected: #2057 shipped, cycle runner is live. Added reference to #7630 successor.

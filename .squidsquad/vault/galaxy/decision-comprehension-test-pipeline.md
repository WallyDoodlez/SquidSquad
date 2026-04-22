---
type: decision
tags: [testing, automation, claude-cli, comprehension]
created: 2026-04-22
updated: 2026-04-22
owner: skill-lead
status: active
confidence: high
source: conversation
links:
  - decision-sub-skill-architecture
---

# Comprehension Test Pipeline

Two-agent pipeline for testing LLM instruction comprehension, approved by human (#1449).

## Architecture

1. **Test agent**: Reads listed files, answers questions, writes `answers.md`. Gets only Read,Write tools.
2. **Eval agent**: Compares answers vs expected behaviors, writes structured `results.json`. Gets only Read,Write tools.
3. **Pytest wrapper**: Reads `results.json` deterministically — pure assertions, no LLM judgment.

## Key Properties

- **Spec-driven**: `tests/comprehension/<issue>_spec.json` defines files + questions + expected
- **Reproducible**: Any agent can run it, no QA in the loop
- **Deterministic final gate**: pytest reads JSON, asserts true/false
- **Probabilistic middle**: Claude evaluates behavioral correctness

## Files

- `references/scripts/run_comprehension_test.py` — spawner
- `tests/comprehension/*.json` — spec files
- `tests/test_comprehension_*.py` — pytest wrappers

## Changelog

- 2026-04-22 — Created by skill-lead. Initial pipeline for #1428 (5 CQs).

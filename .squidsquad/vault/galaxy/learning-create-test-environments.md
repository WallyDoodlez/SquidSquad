---
type: learning
tags: [testing, qa, process, verification]
created: 2026-04-25
updated: 2026-04-25
owner: pm-lead
status: active
confidence: high
source: conversation
links:
  - decision-clone-isolation-architecture
---

# Create Test Environments — Never Declare TCs "Untestable"

## Context

During #2724 verification, QA declared 3 test cases "untestable" because they required conditions that would disrupt live agents (empty agent list, missing terminal emulator, spawn failure). QA labeled the task `blocked:human-action`.

## Learning

The human correctly identified that all 3 TCs were testable by creating a fresh temp repo with zero agents configured. The pattern: **if a TC requires environmental conditions that can't exist in production, create a disposable test environment that has those conditions.**

Approaches:
- **Empty config**: Create a temp repo, deploy SquidSquad with no dev agents, run the test
- **Missing tooling**: Mock the spawner to fail, or use a minimal environment without wt.exe
- **Failure simulation**: Mock the subprocess to exit non-zero

## Rule

Never declare a TC "untestable" or "requires human environment setup" without first considering whether a disposable test environment can be created. The bar for `blocked:human-action` is that the test genuinely requires human judgment or physical access — not that it requires a different configuration than production.

## Changelog

- 2026-04-25 — Created by pm-lead. Human corrected QA's "untestable" assessment on #2724 TCs.

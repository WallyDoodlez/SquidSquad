---
type: decision
tags: [git, workflow, branches, architecture]
created: 2026-04-13
updated: 2026-04-13
owner: pm
status: active
confidence: high
source: conversation
links: []
---

## Context

Human decided during #375 planning that SquidSquad should use branch-per-feature workflow instead of committing all code directly to main. This is a fundamental architectural shift in how agents manage git.

## Content

**Code on branches, communication on main.** Feature work happens on `squidsquad/<type>-<role>-<issue>` branches. The `.squidsquad/` bus (working-state, iterations, current-state, config) stays on main so all agents can see each other's state. Code only reaches main via merged PR.

Key implementation: `git_ops.py` provides `commit-code` (code to branch) and `commit-state` (.squidsquad/ to main) commands. `commit-state` errors if not on main (no auto-switching). Config flag `Branch Workflow: yes/no` controls activation.

## Rationale

Main should be production-ready. Feature branches provide isolation, PR review gates, and prevent half-finished features from polluting main. The dual-lane approach (code on branches, state on main) preserves the agent communication bus while gaining branch benefits.

## Related

---

### Changelog

- 2026-04-13 — Created by pm. #375 verified and shipped — branch-per-feature workflow is now active.

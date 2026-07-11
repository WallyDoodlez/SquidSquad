---
type: learning
tags: [git, workflow, gotcha, commit-role-scoped, post-cycle]
created: 2026-06-26
updated: 2026-06-26
owner: skill-lead
status: active
confidence: high
source: observation
links: []
---

# commit_role_scoped silently leaves non-allowlisted files untracked as "foreign"

## Context

`git_ops.commit_role_scoped(role, msg)` (the per-cycle post-cycle commit path for
every agent) reads `git status --porcelain` — which **does** include untracked
(`??`) files — then stages only paths matching `_role_owned_patterns(role)`.
Anything not matching is classified **foreign**, left in the working tree, and
surfaced only as a stderr WARNING (easy to miss).

## Problem

A legitimate agent-authored work product that lives **outside** the role's
allowlist is never auto-committed — it accumulates untracked across cycles and
the clone drifts behind, until a manual "recover N-behind" rescue commit lands
it. Concretely (#13212): `tests/comprehension/*.json` — verifier-authored
permanent regression specs — matched **no** role pattern (the patterns were all
under `.squidsquad/`), so every new spec was dropped as foreign for months.

## Lesson / how to apply

- When "an agent-authored file never gets committed," **first suspect
  `_role_owned_patterns`**, not a write bug. The file is probably being written
  fine but classified foreign. Grep the stderr cycle logs for the
  "skipped N file(s) outside '<role>' domain" warning.
- The fix is usually a **scoped, role-specific pattern addition** (e.g.
  `"qa": ["tests/comprehension/"]`) — additive, and kept to the one role that
  legitimately authors that artifact, so a half-written file from another role
  isn't staged.
- Distinguish from a *different* failure: if the path **does** match a pattern
  (e.g. `.squidsquad/<role>/planning/`) yet still isn't committed, the cause is
  not the allowlist — it's post-cycle **not running** (an agent wedge / liveness
  issue, e.g. [[learning-deploy-pull-block-divergence-recover-by-merge]] class,
  #12271) or the #11083 non-working-branch skip. Don't conflate the two.
- Sibling but distinct mechanism: [[learning-commit-code-state-exclusion]] is
  about `commit-code`'s code-vs-state split, not the role-pattern allowlist.

## Changelog

- 2026-06-26 — Created by skill-lead during #13212 (comprehension-spec staging gap).

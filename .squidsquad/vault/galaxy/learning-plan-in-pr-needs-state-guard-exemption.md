---
type: learning
tags: [git, workflow, gotcha, state-guard, plan-in-pr, compose]
created: 2026-06-17
updated: 2026-06-17
owner: skill-lead
status: active
confidence: high
source: observation
links: [learning-commit-code-state-exclusion, decision-branch-per-feature-workflow]
---

# Plan-in-PR requires a narrow state-guard exemption for plan bodies

## Context

#12750 made task plans ride the task branch into the PR (commit 1) instead of
being committed straight to `main`, so the plan merges co-located with the code
that fulfils it. The plan body lives at `.squidsquad/<role>/planning/<n>-body.md`.

## Problem

The #11511 pre-commit state-guard (`git_ops.guard_staged_state`) and its classifier
`_is_state_file` treat **everything** under `.squidsquad/` as transient state and
strip it from feature-branch commits. That deterministic guard directly defeats any
flow that *wants* a `.squidsquad/` file on a feature branch — including plan-in-PR.
Verified empirically: staging a plan body on a feature branch and committing it
printed `pre-commit guard unstaged 1 transient state file` and the plan silently
vanished from the commit. (A dogfood that "worked" only did so because that commit
bypassed the active hook — not a reproducible documented flow.)

## Resolution

Add a **guard-local** allowlist, not a global change. `_is_plan_body()` matches only
`.squidsquad/<role>/planning/<n>-body.md` (numeric stem), and `guard_staged_state`
skips stripping those. Keep it narrow: `working-state.md` / `iterations/` / vault
notes are still stripped, so the #11511 merge-spiral (those siblings rewrite every
cycle and overlap across branches) does NOT return — a one-shot per-issue plan body
can't spiral. Crucially, leave `_is_state_file` itself unchanged so `commit_code` /
`commit_state` / `_auto_resolve_state_conflicts` keep their single-source routing;
only the guard diverges. See [[learning-commit-code-state-exclusion]] for the dual
of this (code that lives under `.squidsquad/` and must reach the branch).

## Generalizable rule

When a deterministic guard contradicts a new instruction-level flow, the seam is a
*narrow, guard-local* carve-out keyed on a precise path predicate — not relaxing the
broadly-consumed classifier. Always prove the guard's actual behavior empirically
before trusting that a `.squidsquad/` path will survive onto a feature branch.

## Changelog

- 2026-06-17 — Created by skill-lead. Discovered building #12750 (plan-in-PR).

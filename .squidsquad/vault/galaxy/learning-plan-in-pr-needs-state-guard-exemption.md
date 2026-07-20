---
type: learning
tags: [git, workflow, gotcha, state-guard, plan-in-pr, compose]
created: 2026-06-17
updated: 2026-07-20
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

## Second failure mode — seed-commit dual-landing auto-closes the PR (2026-07-20)

The exemption has a sharp edge on the other side: if the SAME commit that seeds a
task branch (plan body or any PR-carried `.squidsquad/` file) ALSO reaches `main`
through the direct-to-main state lane, GitHub sees the PR's head reachable from
base the moment `main` pushes and **auto-closes the PR with an empty diff**.
Observed on #13561/PR #13889: the TUI-INTERFACE-DESIGN.md amendment commit
(daef22565) was both the branch tip and an unpushed local-main commit; pushing
main closed the PR silently, stranding the real deliverable (which was separately
sitting uncommitted — compounding). Rule: a commit is EITHER branch-lane OR
main-lane, never both; when a planning artifact must ride main (#11511) and a
branch needs seeding, seed the branch with a DIFFERENT commit (even an empty
one). After any main push, re-verify open PRs whose branches share history with
what you pushed.

## Changelog

- 2026-06-17 — Created by skill-lead. Discovered building #12750 (plan-in-PR).
- 2026-07-20 — skill-lead: second failure mode (seed-commit dual-landing → GitHub auto-close, #13561/PR #13889 incident) + either-lane-never-both rule.

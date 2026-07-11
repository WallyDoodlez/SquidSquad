---
type: learning
tags: [delivery, recompose, compose, main-landing, staleness, windows, dm-arch]
created: 2026-06-28
updated: 2026-06-28
owner: dm-lead
status: active
confidence: high
source: observation
links: [learning-git-show-ref-path-mangled-on-windows-bash, learning-pending-ship-query-includes-closed, learning-bash-cd-into-missing-worktree-runs-in-main-clone, pattern-verify-composed-output-with-main-landing-state-applied]
---

## Context

Delivering #13291 (L1-universal "stay current before you integrate" norm — touches SOUL.md/identity.md +
per-role instructions.md, so all 4 composed CLAUDE.md) and #13286 (worker implement-tasks). Both reached
pending-ship, PRs merged, then auto-closed by the merge while keeping a stale `status:pending-ship` label and
no DM ship comment ([[learning-pending-ship-query-includes-closed]]). Looked like a classic DM
recompose-main-landing was owed for all 4 roles.

A behind-clone check — `git show origin/main:.squidsquad/<role>/CLAUDE.md | grep "<new norm>"` — returned 0 for
all 4, reading as "composed output is stale, recompose needed." **That was a false alarm:** the `:` path form
silently failed via Windows path-mangling ([[learning-git-show-ref-path-mangled-on-windows-bash]]) — git errored,
`2>&1 | grep -c` counted 0 matches, and the error looked like an absence.

## Content

**At DM delivery time, confirm whether a recompose-main-landing is actually owed by running a fresh `compose.py
deploy <alias>` for every provisioned alias in an isolated worktree at origin/main and checking for a ZERO diff —
do NOT infer staleness from a behind-clone `git show origin/main:<path> | grep`.**

Two reasons the grep misleads:
1. **Windows path-mangling** turns the `git show <ref>:<path>` form into a fatal error that greps as "0 matches"
   = false "stale" reading. Use PowerShell + a worktree, or `Get-Content` inside the worktree, not bash `git show`
   with a `:` ref-path on this platform.
2. **The implementer may have already recomposed.** Source-shipping roles can land their own post-merge recompose
   ("un-held"): here skill committed `066875e31 skill: post-merge recompose for #13291 L1 norm`, so all 4 composed
   CLAUDE.md were already current. A fresh deploy in the worktree produced zero diff — the authoritative proof.

When the fresh compose yields zero diff, the package step is already complete; DM's work collapses to **publish-only**:
ship comment + `pending-ship → shipped` transition (which corrects the stale label) + counter increment, plus folding
any reboot into the pending operator-paced restart window. No commit/push from the worktree (nothing changed) —
remove it.

**Why:** trusting the behind-clone grep would have driven a redundant fleet-wide recompose+commit+push from a stale
clone — exactly the behind-clone integration hazard #13291/#13271 exist to prevent. The zero-diff fresh compose is
both the staleness probe and the recompose; if it diffs, you commit that same diff (you were going to recompose
anyway), so it is never wasted work.

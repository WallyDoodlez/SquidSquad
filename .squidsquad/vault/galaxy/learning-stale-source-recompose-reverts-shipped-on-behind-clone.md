---
type: learning
tags: [pm, git, boot, compose, recompose, regression, boot-pull-lag, false-landing]
created: 2026-06-19
owner: pm
status: active
confidence: high
source: observation
links: [learning-recompose-and-config-carry-across-checkout, pattern-verify-composed-output-with-main-landing-state-applied]
---

## Context

PM fresh boot 2026-06-19: the pm clone booted **3 commits behind origin/main** (chronic boot-pull lag on this clone) AND the working tree had **all 8 composed `CLAUDE.md`/`CLAUDE.linked.md`** sitting dirty — reverted from the just-shipped #12853 SOUL (`Never Stop While Work Is Pending` + PM advertise-line) **back to** the pre-#12853 content. The revert was exactly what re-deploying from the *stale local source* (which predated #12853's source merge) produces. Left uncaught, the post-cycle wrapper would have committed+pushed it, **silently reverting a shipped+qa-verified change fleet-wide** (an "un-ship"). Filed #12895 (high, skill); same family as #12519 (tracked compose output rewritten per-clone).

## Lesson

This is the mirror of [[learning-recompose-and-config-carry-across-checkout]] — that one carries *unmerged-ahead* source forward (premature landing); this one reverts *already-merged* source backward (regression). Both share the root: **tracked composed outputs get rewritten per-clone from whatever source the clone currently has.** On a clone that is BEHIND origin, that rewrite is a regression. Composed CLAUDE.md is not a file agents hand-edit, so the regression is **silent** — only a manual `git status` at boot catches it.

## How to apply

- **At every boot, `git status --short` before trusting the tree.** Any dirty `.squidsquad/*/CLAUDE.md` / `.linked.md` you did not author = carry-over/recompose; do NOT let it ride into a commit.
- **Order of recovery on a behind clone:** (1) `git restore` the dirty composed outputs → (2) `git fetch` + check `rev-list --left-right --count origin/main...HEAD` → (3) **merge** origin/main (never rebase — [[feedback_never_rebase_merge_instead]]) → (4) re-grep composed outputs to confirm the shipped content is present and the stale content is gone, in all 4 agent files.
- **Diagnose before discarding:** confirm the dirty content is a *revert of shipped* content (compare against origin) vs a legit local recompose — restoring blindly could drop a real change. Here the incoming commits didn't touch composed outputs, so origin's composed state was authoritative.
- Boot-pull lag is the enabling precondition; until the harness pulls-before-recompose (#12895) this check is load-bearing every PM boot on this clone.

## DM-side catch-and-repair at main-landing (2026-06-19, #12800 ship)

The revert can also land **committed on main** (not just dirty-on-a-clone): a behind clone's recompose can be *committed+pushed* as part of another task's main-landing, silently un-shipping a prior ship's composed change for everyone. DM catches this at the **next main-landing**, not at boot:

- **At every main-landing, run `compose.py deploy-all` and inspect the diff — even if the worker says "composed CLAUDE.md already deployed to main."** A diff that includes a *revert* of a prior ship's composed content (e.g. an old SOUL heading reappearing) is this regression sitting committed on main.
- **Before committing the repair, prove your source is current** (`HEAD == origin/main`, and grep the *source* file for the shipped content) so you are the up-to-date clone fixing it, not another behind clone re-reverting it. Then commit the recompose — it repairs main for the whole fleet in one landing.
- Concrete: shipping #12800 (instructions.md → all 4 CLAUDE.md), deploy-all also surfaced #12853's SOUL title reverted to "Never Block on a Human" in the committed outputs; one main-landing commit (a023a658e) landed #12800 AND restored #12853. See [[pattern-ship-gate-preserve-expanded-scope]] (sibling DM ship-gate discipline).

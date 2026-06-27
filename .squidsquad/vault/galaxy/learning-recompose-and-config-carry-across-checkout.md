---
type: learning
tags: [verifier, git, branch-checkout, compose, config, false-landing, gate-integrity]
created: 2026-06-18
owner: verifier
status: active
confidence: high
source: observation
links: [pattern-verify-composed-output-with-main-landing-state-applied, pattern-verify-new-shipped-file-in-installer-manifest]
---

## Context

While verifying source-only L1/config PRs on their feature branch (#12506 cy323, #12799 cy334), uncommitted working-tree changes were silently **carried across `git checkout main`** twice:

- **#12506:** checking out the branch reverted `config.md` to the branch's older `30`/no-burst version; it then rode `git checkout main` back onto main as an uncommitted modification.
- **#12799:** running the static gate (or the l4 file-watcher firing on the SOUL.md source edit) **regenerated 8 composed `CLAUDE.md`/`CLAUDE.linked.md`** on the branch; `git checkout main` carried them over — now containing the *unmerged* async-no-pause rule, ahead of main's committed source.

Git carries uncommitted changes across a checkout when they don't conflict — it does not warn. Left uncaught, the verifier commits a recompose reflecting unmerged source (or a stale config) to main: a false landing.

## Lesson

**A verifier who checks out a feature branch to test, then returns to main, must treat the working tree as contaminated until proven clean.** Two mechanisms dirty it:
1. **Checkout itself** swaps any file that differs between branches (e.g. `config.md`); if it was momentarily staged/edited it persists across the next checkout.
2. **Recompose side-effects** — `compose.py deploy-all` (when you run it for an AC1 composed-output check), the **l4 file-watcher** auto-recomposing on a SOUL/source edit, or a **compose test inside the static gate** — regenerate `.squidsquad/*/CLAUDE.md` + `.linked.md` from the branch's source. These are NOT part of a source-only PR and must never land on main via QA (l4-recompose regenerates them downstream at ship time).

## How to apply

- **Always `git status --short` immediately after `git checkout main`** (and again before any main-side artifact write / commit). Expect EMPTY. Anything listed is carry-over.
- **Revert carry-over to main's committed state** before writing: `git checkout -- <paths>` for `config.md`, every `.squidsquad/*/CLAUDE.md`, and `.linked.md`. Then re-grep to confirm (e.g. main `SOUL.md` shows 0 occurrences of the rule that's still only on the branch).
- **For AC1 composed-output checks**, run `compose.py deploy-all` on the branch, grep the composed files to confirm the rule is present, then **discard the recompose** (`git checkout --` the composed paths) so the PR stays source-only — the #12585 precedent.
- **`config.md` is a live, per-clone, frequently-uncommitted file** — it is the most likely thing to ride a checkout. Verify its `## Improvement Scanning` / counter keys match main's committed values after any branch round-trip.
- Net: branch round-trips are a verification convenience, not a state change. The only things QA commits to main are its own planning artifacts (TEST-PLAN / QA-RESULTS / comprehension spec) and working-state — never a recompose or a carried config.

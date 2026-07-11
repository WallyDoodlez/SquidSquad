---
type: learning
tags: [verifier, ship-gate, static-gate, merge, behind-branch, landing-safety, squash-merge]
created: 2026-07-11
updated: 2026-07-11
owner: verifier
status: active
confidence: high
source: observation
links: [learning-verify-absent-claims-need-fresh-fetch-all-refs, learning-stale-source-recompose-reverts-shipped-on-behind-clone, learning-edit-shared-fragment-run-full-static-gate]
---

## Context

In one session I shipped a chain of sibling installer tasks (#13355, #13339, #13397) that each modified `references/scripts/wizard.py` (and #13355/#13339 both touched `tests/test_wizard_runbook.py`). Each feature branch was created before its siblings merged, so by verification time every branch was **N commits behind `origin/main`** and shared edited files with siblings already on main. The branch's own green static gate proves the branch — NOT the state that actually lands after merge.

## Content

**When a pending-test branch is BOTH (a) behind `origin/main` AND (b) touches files a sibling already merged to main also touched, verify the COMBINED (post-merge) state before shipping — the branch's own gate is insufficient.**

Procedure (respects "never modify another agent's branch" — the merge is local and never pushed):

1. `git merge origin/main --no-edit` into the checked-out feature branch. A clean 3-way (0 conflicts) is the first signal; a conflict is itself a finding (branch needs updating).
2. Sanity-check the merged shared files for **semantic** consistency, not just textual merge success. Example that textual merge gets right but is worth confirming: #13355 *removed* `pr-flow-prompt` from the dispatch table + `_WIZARD_COMMANDS`; #13339 *added* `detect-maturity`/`propose-roster` to the same set. The 3-way merge reconciled both (removal + additions) because they touched different lines — the combined runbook exact-match test then passes. If they had touched the same line it would have conflicted or silently mismatched.
3. Run the **full static gate on the combined state** — this is the authoritative landing check (e.g. combined counts 5329, 5332 vs the branch-only 5310/5294).
4. Confirm `gh pr view --json mergeStateStatus` is `CLEAN` (GitHub computes against live main), then merge server-side (`git_ops.py pr-merge`). Server-side squash of a diff that doesn't touch a sibling's unique lines cannot revert that sibling — but verify prior work is still on `origin/main` post-merge anyway.

This is distinct from the stale-*clone* hazard ([[learning-stale-source-recompose-reverts-shipped-on-behind-clone]]) — here the branch is genuinely behind and the risk is a merge-time inconsistency in shared files, not a stale-tree overwrite.

## How to apply

Before shipping any pending-test item: `git rev-list --count HEAD..origin/main` (behind?) and diff the branch's file set against recently-merged siblings (shared files?). If both true, run the local-merge + combined-gate check above. If the branch is disjoint from everything on main (e.g. #13369 vs the wizard.py chain), the branch-only gate suffices — just confirm disjointness with `git diff merge-base..HEAD -- <sibling files>` = empty.

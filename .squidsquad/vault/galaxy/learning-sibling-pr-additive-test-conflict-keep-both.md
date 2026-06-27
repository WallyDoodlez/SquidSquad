---
type: learning
tags: [verification, merge, testing, deploy-cluster]
created: 2026-06-27
author: qa
---

# Sibling PRs cut from one base conflict additively on the shared test file → keep-both

When a worker files several fixes as separate PRs **all branched from the same base commit**, and each adds a new test class at the **same anchor point** in a shared test file (e.g. `tests/test_harness.py`), the PRs merge cleanly one at a time but **every PR after the first conflicts on the test file** — both sides inserted a class at the identical line, so git can't auto-place them.

**This is a purely additive conflict, not a semantic one.** The production code usually auto-merges (different functions); only the test file collides. Resolution is always **keep-both**: remove the `<<<<<<< / ======= / >>>>>>>` markers, keep every conflicting test class, ensure PEP8 two-blank-line spacing between top-level classes, then run the full module to confirm all classes are present and green.

**Observed**: 2026-06-27 verifying the deploy-fragility cluster — #13170's PR #13258 conflicted with main on `tests/test_harness.py` after #13215/#13255 landed (each added a `class Test...` at line ~3050). harness.py auto-merged; only the test file needed keep-both.

**How to apply** (verifier landing verified work):
- Probe first: branch from the PR head, `git merge origin/main --no-commit` to see the real conflict before deciding. If it's keep-both in a test file, resolve it — that's within verifier merge authority (mechanical, preserves the worker's work entirely), not a route-back.
- Main is a moving target: other agents push between your probe and your merge. Bring the **latest** main into the PR branch (so it's strictly ahead) and push, then poll `gh pr view --json mergeable` until MERGEABLE before `pr-merge` — GitHub's mergeability lags a few seconds behind a push.
- Route back to the worker only if the conflict is **semantic** (real logic divergence), not additive.

Related: [[feedback_verify_fresh_fetch_all_refs]] (main advances under you), [[feedback_no_double_transition]].

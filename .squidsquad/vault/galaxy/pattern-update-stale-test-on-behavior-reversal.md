---
name: pattern-update-stale-test-on-behavior-reversal
description: When a fix deliberately reverses prior behavior, the old regression test that locked that behavior goes red after merging main — update it in-place to assert the NEW behavior (don't silently delete), following the test file's own historical-update convention, and cite the prior issue chain
metadata:
  type: pattern
type: pattern
tags: [pattern, testing, regression, behavior-change, self-hosting]
created: 2026-06-13
updated: 2026-06-13
owner: skill
status: active
confidence: high
source: observation
links: [learning-test-pollution-real-clone-state, pattern-stale-ac-vs-canonical-arch]
---

## Context

A regression test locks behavior X at the source level. Later a fix is approved that **deliberately reverses** X → not-X. The fix's own branch adds fresh tests for not-X, but the *old* regression test for X is in a different file and still asserts X. While the fix branch is held pre-merge it stays green (old behavior intact); the moment you merge main / land the behavior change, the old test goes red.

Concrete instance (#11640, iter-466 2026-06-13): `_get_clone_path` historically fell back to `REPO_ROOT` for an unregistered role (#1496). #11640 reverses this — an unregistered role must now raise `CloneResolutionError` (a wrong-realm boot corrupts another agent's clone). The fix added comprehensive raise-coverage in `test_boot_remote.py`, but `test_feat_1496_shared_fs_fallback.py::test_get_clone_path_falls_back_to_repo_root` still asserted the old fallback and went red after merge.

## Pattern

1. **Expect it.** Any fix whose one-line summary contains "must FAIL / refuse / no longer / remove the fallback / reverse" has a latent stale regression test somewhere. Grep for the old behavior's test before you merge, not after the suite goes red.
2. **Update in-place, don't silently delete.** Convert the old test to assert the new behavior (`pytest.raises(...)` instead of the old equality), rename the method to match (`..._falls_back_to_repo_root` → `..._raises_when_role_not_in_config`), and update its docstring to cite the reversing issue. A deleted test leaves no breadcrumb that the behavior flipped.
3. **Follow the file's own convention.** `test_feat_1496` already had a precedent: #3100 had earlier updated #1496's tests in-place (documented in the module docstring). Match the established style — add a docstring note recording the new reversal (#11640) alongside the prior ones (#1496 → #3100 → #11640).
4. **Point to where the real coverage lives.** If the fix branch already added thorough coverage elsewhere, say so in the updated test's docstring so the next reader knows this site is the historical anchor, not the primary suite.

## Cross-branch corollary

When N sibling fix-branches all merge main at different times, the stale-test fix travels coupled with the source change on its own branch. Branches that merged main **before** the reversal landed still carry old-test + old-source (internally consistent, green). Only the branch carrying the source reversal needs the test update. Don't pre-emptively patch the other branches — they get the coupled change when they next merge main.

## When NOT to use

- The old test still reflects intended behavior (the change is additive, not a reversal) — leave it.
- The old behavior is genuinely dead and untestable post-change — then delete with a one-line commit note pointing to the replacement coverage, rather than leaving an asserting-nothing husk.

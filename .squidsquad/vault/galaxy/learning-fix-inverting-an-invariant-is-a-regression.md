---
type: learning
tags: [verifier, testing, regression, zero-gap, full-suite, invariant]
created: 2026-06-14
updated: 2026-06-14
owner: verifier
status: active
confidence: high
source: observation
links: [learning-gate-collection-abort-masks-reds, feedback-qa-verification-approach]
---

## Context

Verifying #12380 (compose keys `.local-config` by ALIAS `qa`, not role-class
`verifier`). All 5 ACs passed and the PR's own new tests were green — but the
full suite had one red: `test_harness.py::...test_restart_endpoint_refuses_before_mutating_intent`
(`200 != 500`). That test's docstring hard-coded the premise "`qa` is unregistered
in this clone's `.local-config`" and did NOT mock `_get_clone_path`. #12380's
entire purpose is to make `qa` *always* registered — so the fix inverted the exact
invariant the test depended on. The test was green ONLY while the bug existed.

## Lesson

1. **A fix that inverts an invariant an existing test hard-codes is a regression —
   even when the PR diff never touches that test file.** "The failing test isn't in
   my diff" does not clear it. The behavioral change reaches across files.
2. **This is precisely why QA runs the FULL suite, not just the PR's new tests.**
   The worker's tests assert the fix works; they cannot catch a fix that breaks a
   DIFFERENT test encoding the old behavior. Only a whole-suite run surfaces it.
3. **It belongs in the same PR, not a follow-up.** Routing it forward as "note for
   later" is the zero-gap anti-pattern. Landing the invariant change means updating
   the test that assumed the old invariant — here: mock `_get_clone_path` to raise
   (a sibling test in the same class already did exactly that), or pick a role that
   is genuinely never registered.
4. **Distinguish "regression" from "pre-existing red" by the clean-baseline test:**
   would this test be GREEN on a clean build *without* the bug and *without* the
   fix? If yes (here: clean pre-fix compose omits `qa` → 500 → green), the fix
   turning it red is a regression to block. If it's red on clean main regardless,
   it's a separate pre-existing issue to file, not block on.

## How to apply

When a fix changes a system-wide invariant (a key's presence, a default, a routing
rule), grep the test tree for tests that assert the OLD invariant before shipping.
Run the full gate and treat any newly-red test as in-scope. Confirm regression-vs-
pre-existing by restoring the PR files to clean main and re-running the red test.
Beware gates that mask this (see [[learning-gate-collection-abort-masks-reds]]).

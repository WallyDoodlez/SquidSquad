---
type: pattern
tags: [verifier, testing-craft, incident-verification, merge-safety, high-severity]
created: 2026-07-11
updated: 2026-07-11
owner: verifier
status: active
confidence: high
source: observation
links: [learning-merge-driver-defeated-by-delete-not-modify, learning-verify-combined-state-when-branch-behind-main-shares-files]
---

## Context

Verifying #13554 (PR #13559), a HIGH-severity merge-gate fix closing a real
data-loss incident: my own earlier merge of #13454 had squash-reverted 1328
lines of teammate state+vault on main. The PR's own test suite mocked
`gh pr view --json files` responses to exercise the new
`_pr_state_scope_violations()` guard — solid unit coverage, but every
assertion was against a hand-constructed file list, not the actual incident.

## Content

**When verifying a fix for a data-loss/incident bug, run the fix's own detection function LIVE against the actual historical artifact (the real merged PR, the real corrupted file, the real bad state) that caused the incident — not just the PR's mocked unit tests.** `gh` still serves metadata for closed/merged PRs indefinitely, so this is usually one function call:

```python
import git_ops
git_ops._pr_state_scope_violations(13546)  # the ACTUAL incident PR, already merged
# -> returns the exact 14 files the incident report named, zero omissions/extras
```

This is strictly stronger evidence than the PR's own mocked tests, for two
reasons: (1) it proves the fix's detection logic actually matches the
real-world data shape, not just the shape the worker imagined when writing
tests; (2) it is not authored by the same person who wrote the fix, so it
carries independent-verification weight the mocked suite structurally cannot
(the worker can't have unconsciously shaped the mock to match their own
implementation). Pair it with a **false-positive sweep**: run the same live
function against every OTHER PR from the same session/timeframe that should
NOT be flagged, to confirm the fix doesn't overcorrect.

## How to apply

Applicable whenever a fix targets a **specific, already-occurred incident**
with a stable real-world artifact still queryable (a merged PR, a bad commit,
a corrupted file, a crash log) — not for fixes targeting a purely
hypothetical/future class of bug with no real instance yet. Steps:

1. Identify the real artifact ID (PR number, commit SHA, file path) from the
   incident report.
2. Call the fix's own detection/guard function directly against it (bypass
   the PR's test file entirely — import the module fresh).
3. Diff the result against the incident report's own inventory of what went
   wrong — every named item should appear, nothing extra.
4. Run the same function against a handful of adjacent, legitimately-clean
   artifacts (siblings, recent unrelated merges) to confirm no false positives.
5. Record both the positive (catches the real incident) and negative (doesn't
   over-block) results in the QA-RESULTS — this is the decisive check, not a
   nice-to-have footnote.

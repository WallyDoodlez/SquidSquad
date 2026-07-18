# QA-RESULTS-13555

## Summary
VERIFIED — PASS. All 5 ACs confirmed via my own independent live checks (own fixture, not the worker's mocked test data) plus the real live open-issue count.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | Live import: `harness.ExternalActivityDetector.ISSUE_POLL_LIMIT == 500` |
| AC2 | PASS | Live call to real `_check_for_changes()` (only `subprocess.run` mocked, captured the invoked cmd): `--limit 500` used, not `50` |
| AC3 | PASS | Same harness, fed 500 fake issues (>= cap): stderr contains `WARNING` + `#13555` |
| AC4 | PASS | Negative control fed 167 issues (today's REAL live count at test time, not a synthetic round number, deliberately differently-shaped from the worker's own fixture): stderr empty of `WARNING` |
| AC5 | PASS | `gh issue list --label squidsquad --state open --json number --limit 500` → 165 open issues at verdict time, comfortably under the 500 cap. Note: `gh issue list` without an explicit `--limit` silently defaults to 30 — confirmed this pitfall directly while deriving the count (an unqualified query first returned a misleading "30") |

## Additional checks
- Worker's own regression suite: `TestEADPollLimit13555` 4/4 PASS.
- Full `tests/test_harness.py`: 319/319 PASS (no regression in the surrounding EAD/harness surface).
- Combined-state static gate (branch merged with current origin/main, which now includes my own #13580 merge): first pass showed 1 failure — `test_comprehension_spec_staleness_13575.py::test_no_silently_stale_comprehension_specs` (the #13575 gate I myself verified/shipped earlier this session). `9873_spec.json` records a baseline blob sha for `references/scripts/harness.py`; #13555's diff changes that file's blob sha (531371a15 → 813261361), tripping the gate. **Diagnosed genuinely caused by #13555's own diff** (not a stale-branch artifact like #13580's inject-permissions.ps1 case): confirmed bare `origin/main`'s harness.py blob sha matches the baseline exactly (531371a1) — clean pre-#13555. **Re-reviewed the spec**: `9873_spec.json`'s 5 questions target `event_catalog.py` (untouched by this diff) and the `GET /events/cursor/{role}` / `ack-cursor` / `ack-stop` handler region of harness.py (grep-confirmed nowhere near `ExternalActivityDetector._check_for_changes`, the only region #13555 touches — zero line overlap). Spec's recorded answers still hold. Per the gate's own documented remedy ("spec still valid → re-review, then `comprehension_staleness.py refresh`") and verifier's ownership of comprehension-testing infrastructure (#9184), refreshed `tests/comprehension/.staleness-baseline.json` myself (QA-owned artifact, same precedent as my #13569 `superseded_by` annotation — not routed to skill). Re-ran: staleness gate 10/10 PASS, **full static gate 5530/5530 PASS, 0 failures** — decisive.

## Zero-gap check
No gaps. Issue's own suggested fixes (a) raise limit + (c) warn-at-cap both implemented and independently confirmed; (b) (narrow query to actionable statuses) was explicitly not chosen by skill — acceptable, issue said "any one" fix is sufficient and (a)+(c) together fully close the starvation + silent-truncation risk described in the Observation. The comprehension-staleness collision (above) was reviewed and resolved as QA-owned housekeeping, not a substantive gap in #13555's own fix.

## Verdict
PASS → pending-ship.

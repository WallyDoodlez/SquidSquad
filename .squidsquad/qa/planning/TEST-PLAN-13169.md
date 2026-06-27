# TEST-PLAN-13169 — comprehension result-id Q- echo mismatch

**Derived independently** from the issue body + my RCA lead (the `_get_result('Q-1' vs '1')` mismatch).

## Expected behavior
The comprehension runner must canonicalize judge-emitted result ids to the bare spec id before writing results.json, so a judge echoing `Q-<id>` (the prompt's header label) cannot turn a correct PASS into a spurious red when comprehension files run live together.

## ACs (independent)
- AC1 judge `Q-<id>` → bare id before write
- AC2 bare id unchanged
- AC3 single-strip only (no over-strip)
- AC4 hyphenated-slug ids preserved (real-spec format)
- AC5 case/whitespace/non-string handled
- AC6 end-to-end: judge `Q-1` → results.json `1`
- AC7 original repro resolved

## Method
Unit: `_normalize_result_id` on real-spec id formats (`tests/test_feat_13169_normalize_id_real_spec_slugs.py`) + skill's `TestResultIdNormalization13169`. Integration: rerun the issue's exact `pytest <9184> <361>` repro and confirm no false-fail.

## CQ note
No CQ spec — correctness is at the deterministic `_normalize_result_id` seam (catches any judge echo); a CQ for the harness's own judge prompt would be circular.

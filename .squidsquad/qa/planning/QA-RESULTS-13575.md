# QA-RESULTS #13575 — comprehension-spec staleness gate

**Verdict: PASS → pending-ship.**

## Summary

My own filed finding: `tests/comprehension/*_spec.json` are permanent
PASS-stamped records, but nothing re-checked an older spec's expected answer
when a later PR overruled the fragment it tested (live case: #13569 silently
overruled `13175_spec.json`'s expectations, caught only by chance). Skill
built a checked-in baseline mapping each spec to the git blob sha of every
fragment it names as of last review; the static gate fails on sha drift or a
missing baseline entry. Remediation rides the fragment-changing PR:
`refresh` (still valid) or `superseded_by: <issue>` (overruled, permanent
record). A naive date-comparison approach was prototyped and rejected
(~40 false positives on any unrelated edit) in favor of this explicit
review-state model.

## Independent verification

- **Live falsification (not the worker's mocked unit tests)**: mutated a
  real fragment (`l4-curation.md`) backing a real spec, committed it, and
  confirmed the gate correctly flagged the drift with the exact sha mismatch
  — then reverted and confirmed clean again.
- **Live falsification, second path**: dropped a new spec naming a real
  fragment but absent from the baseline — correctly flagged as
  not-in-baseline, then removed.
- Confirmed my own ad hoc `13175_spec.json → superseded_by: 13569`
  annotation (made during #13569's verify pass) landed byte-for-byte in the
  PR, not paraphrased or dropped.
- Verified the two claimed "caught during development" staleness events are
  genuine (not just an unverified worker claim): the baseline's own `_note`
  history plus git log confirm a real main-merge sha drift and my own new
  `13579_spec.json` both triggered the gate before being refreshed in.
- Full `test_comprehension_spec_staleness_13575.py`: **10/10 PASS**.
- Full static gate on combined state: 1 failure, 0 errors — confirmed via
  live `gh pr view` that this is `#13582`'s fix not yet merged to
  `origin/main` (PR #13583 still open), a timing artifact unrelated to this
  PR, not a regression.

## Records

- `TEST-PLAN-13575.md` — full AC derivation and evidence.

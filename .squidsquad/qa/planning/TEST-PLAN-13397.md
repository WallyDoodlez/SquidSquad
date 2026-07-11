# TEST-PLAN-13397 — flaky deny-list unknown-flag exit test

**Issue**: #13397 (type:issue, severity:medium — verifier-filed during #13369).
**PR**: #13404 `squidsquad/task/13397`, head cff40ed43.
**Derived from**: the bug report's root-cause hypothesis + zero-gap regression requirement.

## ACs (implicit from the bug)
- The usage-error exit code (2) must be deterministic — never flip to 1 under load.
- Fix must include a regression test that WOULD HAVE CAUGHT the original bug.

## Test cases
- **TC-1**: read the fix — usage-error stderr write guarded so exit code survives a write failure; both usage-error sites covered.
- **TC-2 (the key one)**: the "stderr-write-fails" regression must FAIL on old code / PASS on new. Empirically run the exact vector against origin/main's old wizard.py.
- **TC-3**: run the deny-list suite (branch + combined).
- **TC-4**: full static gate (combined state, since wizard.py is shared with #13355/#13339 on main).
- **TC-5**: landing safety — branch behind main; region disjoint from #13355/#13339; combined 3-way clean.

No CQ — code/test-infra fix, no agent-instruction change.

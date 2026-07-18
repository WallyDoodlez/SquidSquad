# TEST-PLAN #13532 — residual stale restart-harness.sh docstring (post-13318/13323)

**Derived from the issue body — my own filed finding (scope-expansion sibling of #13323).**

## Acceptance Criteria

| AC | Contract |
|----|----------|
| AC1 | `tests/test_12825_harness_restart.py` L144 class docstring updated from `restart-harness.sh` to `.squidsquad/start.sh --bare`, matching the test body |
| AC2 | No other stale `restart-harness.sh` references remain in that file |
| AC3 | The optional/borderline CQ-foil half (`tests/comprehension/12420_spec.json`) is explicitly out of scope per my own issue body — leaving it untouched is not a gap |
| AC4 | No behavioral change — the modified test file still passes in full |
| AC5 | Full static gate green |

## Verification (branch squidsquad/task/13532, combined with current main)

| TC | AC | Check | Result |
|----|----|-------|--------|
| TC1 | AC1 | Diff: L144 docstring now reads ".squidsquad/start.sh --bare" | **PASS** |
| TC2 | AC2 | `grep -n "restart-harness.sh\|start.sh"` — every remaining hit is `.squidsquad/start.sh` (L8/144/148/156/163/275/288); zero bare `restart-harness.sh` | **PASS** |
| TC3 | AC3 | `12420_spec.json` untouched by this PR's diff (issue explicitly marks it optional/borderline) | **PASS** |
| TC4 | AC4 | `pytest tests/test_12825_harness_restart.py` — 15/15 passed, incl. the actual `TestSupervisedLauncherSh` behavioral test | **PASS** |
| TC5 | AC5 | Full static gate on combined state: 5437/0 | **PASS** |

## Branch-staleness handling

Forked before #13371/#13517 (both merged this session). Verified combined
post-merge state via local `git merge origin/main --no-edit` (no push) —
clean merge, no conflicts.

## Notes

- `type:issue`, severity:low — auto-approved, no human gate.
- No comprehension spec (test docstring only, not an LLM-consumed instruction).
- No new regression test needed — docstring-only correction to an existing,
  already-passing test file; the existing test IS the coverage.

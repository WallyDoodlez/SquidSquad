# TEST-PLAN-13317

Derived independently from the issue body (`ISSUE: Stale liveness instructions: 2 sub-skills call PID the 'sole liveness signal' (contradicts shipped #12492 progress-liveness cutover)`), not from the worker's diff.

## ACs derived from the issue

- **AC1**: `references/sub-skills/common/agent-lifecycle.md`'s health-monitoring line no longer asserts PID/`.claude-pid` is the sole liveness signal; it describes the post-#12492 dual model with progress-liveness authoritative for reboot decisions.
- **AC2**: `references/sub-skills/roles/pm/health-check.md`'s equivalent line is corrected the same way, and still correctly tells the operator to prefer `squidsquad_cli.py status` when the harness is reachable.
- **AC3**: Sibling-occurrence sweep — no other compose-consumed sub-skill under `references/sub-skills/` still makes the stale "sole liveness signal" claim (issue's own suggested direction: "Check for sibling occurrences ... while in there").
- **AC4**: The corrected wording actually matches harness.py's live implementation (`_PROGRESS_LIVENESS_AUTHORITATIVE`, `progress_liveness()`, pause-guard, zombie-kill) — not just a plausible-sounding rewrite.
- **AC5**: The CQ spec (`tests/comprehension/4792_spec.json`) that tests this exact claim is updated to the corrected model (no longer pinned to a now-wrong expected answer), and the comprehension-staleness gate is clean.
- **AC6 (independent CQ)**: A fresh agent given ONLY the two fixed sub-skill files (no other context) answers comprehension questions about the liveness model correctly and does NOT reproduce the old "sole liveness signal" claim.
- **AC7**: No regressions — touched test suites pass; ideally the full static gate.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 | `git diff origin/main` on agent-lifecycle.md; read corrected line |
| TC2 | AC2 | `git diff origin/main` on health-check.md; read corrected line |
| TC3 | AC3 | Independent `grep -rn -i "sole liveness"` across `references/sub-skills/`, `.squidsquad/project/`, `tests/comprehension/` (excluding frozen `8697_fixtures/*` snapshots, which are historical compose-output fixtures for an unrelated wake-mechanism CQ test, not live compose-consumed instructions) |
| TC4 | AC4 | Read `harness.py`'s `_PROGRESS_LIVENESS_AUTHORITATIVE` flag and `progress_liveness()` docstring/logic; cross-check against the sub-skill wording |
| TC5 | AC5 | `git diff origin/main` on `4792_spec.json`; run `comprehension_staleness.py check` |
| TC6 | AC6 | Spawn a fresh `general-purpose` subagent, give it only the two fixed files, ask liveness-model questions including an explicit "does either file claim PID is the sole liveness signal" check |
| TC7 | AC7 | Run `test_4792_fragment_hygiene.py`, `test_comprehension_4792.py`, `test_boot_remote.py`; run full `tests/` suite |

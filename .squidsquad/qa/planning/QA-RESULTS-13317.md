# QA-RESULTS-13317

## Summary
VERIFIED — PASS. All 7 ACs confirmed. Independently re-derived the fix's factual claims against `harness.py`'s live implementation rather than trusting the PR description, and independently re-ran the sibling-occurrence sweep rather than trusting the worker's "no other sub-skill makes the stale claim" claim.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | `git diff origin/main -- references/sub-skills/common/agent-lifecycle.md`: L16 rewritten from "PID monitoring through `.claude-pid` (sole liveness signal)" to the dual model with progress-liveness AUTHORITATIVE for reboot decisions |
| AC2 | PASS | Same diff on `references/sub-skills/roles/pm/health-check.md` L18: PID reframed as an "offline-diagnostic proxy"; still correctly recommends `squidsquad_cli.py status` when the harness is reachable |
| AC3 | PASS | Independent `grep -rn -i "sole liveness"` across `references/sub-skills/`, `.squidsquad/project/`, `tests/comprehension/` — zero live hits. The only remaining "sole liveness signal" text lives in `tests/comprehension/8697_fixtures/*_CLAUDE.md` — frozen historical snapshots for the unrelated #8697 wake-mechanism CQ test (not compose-consumed by any live agent; confirmed by reading `8697_spec.json`'s questions, which are entirely about wake mechanisms, not liveness monitoring) |
| AC4 | PASS | Read `harness.py`: `_PROGRESS_LIVENESS_AUTHORITATIVE = True` (line 265), `progress_liveness()` docstring explicitly states "AUTHORITATIVE since the #12492 cutover", zombie-kill logic at ~lines 884-925 matches the sub-skills' corrected wording (PID-alive-but-inert zombie caught by progress-liveness, pause guard prevents false positives) |
| AC5 | PASS | `git diff origin/main -- tests/comprehension/4792_spec.json`: CQ1's question/expected/title rewritten to the corrected model, `must_not` guard added against the old "sole liveness signal" answer; `python references/scripts/comprehension_staleness.py check` exits 0, clean |
| AC6 | PASS | Spawned a fresh `general-purpose` subagent with ONLY the two fixed files and no other context. It correctly identified the dual model, named progress-liveness as authoritative, explained the zombie/pause-guard mechanism, and explicitly confirmed neither file claims PID is the "sole liveness signal" |
| AC7 | PASS | `test_4792_fragment_hygiene.py` (26/26), `test_boot_remote.py`, `test_comprehension_4792.py` (3/3, live CQ) all green. Canonical static gate `python tests/run_tests.py static`: **5628 gated tests PASS, 0 failures, 0 errors** (matches worker's claimed count exactly) |

## Note on raw `pytest tests/` noise
An initial raw `pytest tests/ -q` run showed 45 failures. Traced every one to pre-existing, deliberately-excluded items documented in `tests/run_tests.py`'s `KNOWN_FAILURES`/`KNOWN_NON_STATIC` tables (`test_agent_boundaries`/`test_compose_author_comments_11142`, both blocked on OPEN #10360; `test_comprehension_2195` et al., live-model CQ harnesses not meant for offline/static runs) — none touch the files this PR changed. Re-ran via the canonical `tests/run_tests.py static` gate instead, which is the actual verification bar.

## Zero-gap check
No gaps.

## Verdict
PASS → pending-ship.

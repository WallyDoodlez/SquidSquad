# QA Results — #9904 (_run_script lacks timeout — single hanging script wedges cycle)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 10:01 cycle 728
**PR**: #9924 (branch `squidsquad/task/9904`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Acceptance Criteria

| # | AC | Evidence | Result |
|---|----|----------|--------|
| 1 | New `DEFAULT_SCRIPT_TIMEOUT = 60` module constant | `cycle_pre.py:62` — value confirmed via behavioral check (`cycle_pre.DEFAULT_SCRIPT_TIMEOUT == 60`) | PASS |
| 2 | `_run` accepts `timeout` kwarg, defaults to constant | `cycle_pre.py:65` signature `_run(cmd, check=False, timeout=DEFAULT_SCRIPT_TIMEOUT)` | PASS |
| 3 | `TimeoutExpired` → `CompletedProcess(returncode=124, …)` (POSIX timeout convention) | `cycle_pre.py:74-86` — caught, returns fake CompletedProcess with 124. Behavioral check: `_run([python, '-c', 'time.sleep(5)'], timeout=1)` → rc=124 in **1.02 s** | PASS |
| 4 | stderr diagnostic emitted on timeout | `print(f"  WARNING: {msg}", file=sys.stderr)` at cycle_pre.py:81. Behavioral check observed: `WARNING: TIMEOUT after 1s: …python… -c 'import time; time.sleep(5)'` | PASS |
| 5 | `_run_script` forwards the kwarg | `cycle_pre.py:91-97` — `return _run([…], check=check, timeout=timeout)` | PASS |
| 6 | E2E call opts out with `timeout=None` (DeepSeek finding fix in commit b98e2abf) | `_build_qa_input` at cycle_pre.py:948 — explicit `timeout=None` with 5-line comment justifying. Test `test_e2e_cmd_opts_out_of_default_timeout_9904` inspects source to lock the contract | PASS |

## Test runs

- Targeted: `pytest tests/test_cycle_pre.py -k 9904` → **8 passed in 1.21 s** (7 TestRunTimeout9904 + 1 TestE2eCmdShlexSplit).
- Full: `pytest tests/test_cycle_pre.py` → **114 passed in 1.59 s**.

## Behavioral end-to-end check

```
python -c "import cycle_pre; ...
  r = cycle_pre._run([sys.executable, '-c', 'import time; time.sleep(5)'], timeout=1)"
→ rc=124, stderr="TIMEOUT after 1s: …", elapsed=1.02s
```

Real subprocess (not mocked). The timeout fires within ~20 ms of the 1 s budget, returns 124, and the stderr message contains the command for log triage. The pre-fix behavior would have been a 5 s block on `subprocess.run` with no recovery; post-fix the call returns at 1.02 s and downstream `if result.returncode != 0` paths handle it.

## Defense-in-depth justification

Per PR body and reproduced by inspection: every existing call site in `cycle_pre.py` already checks `if result.returncode != 0` (often inside a `try: json.loads(...) except: empty-default`). A `124` from the new timeout guard hits that path identically — no caller-side changes needed, cycle still writes `cycle-input.json` with degraded fields.

## DeepSeek follow-up

Skill-lead reports DS pre-push surfaced 1 warning (E2E inherited the 60s default, would be a regression for legitimately long suites). Addressed in commit `b98e2abf` on the same PR, with `test_e2e_cmd_opts_out_of_default_timeout_9904` locking the kwarg. I verified the test exists and passes; the opt-out is at `_build_qa_input` only (tracker-style sub-scripts remain bounded).

`mergeable: UNKNOWN, mergeStateStatus: UNKNOWN` at QA time — GitHub had not finished computing. Not a QA defect; flagged for DM to confirm clean state at ship.

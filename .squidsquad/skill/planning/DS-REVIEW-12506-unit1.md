I've now reviewed the full file along with its dependencies (`shared_fs.py` for the atomic-write contract and `config.py` for the config field resolution). Here are my findings:

---

### Finding 1

- **File**: `references/scripts/subloop_driver.py`
- **Line**: 215 (the `cooldown_elapsed` call inside `tick`) and lines 138-150 (`cooldown_elapsed` definition)
- **Severity**: warning
- **Issue**: `cooldown_elapsed()` catches `ValueError` from `_parse_iso` but not `TypeError`. If the state file stores `last_run` as a JSON number (e.g. `{"last_run": 1700000000}` from manual editing or corruption), `datetime.fromisoformat` receives an `int` instead of a `str` and raises `TypeError`, which propagates uncaught through `cooldown_elapsed` and crashes `tick()` or any caller.
- **Evidence**: `_parse_iso(s)` on line 128 calls `datetime.datetime.fromisoformat(s)`. In Python 3.7+, `fromisoformat` requires a `str` argument and raises `TypeError` (not `ValueError`) when given an `int`/`float`. The `except ValueError` guard on line 148-149 does not catch `TypeError`.
- **Suggested fix**: Broaden the except clause to `except (ValueError, TypeError)` on line 148, or add type-checking in `read_state` so that `last_run` is guaranteed to be `str | None` before it reaches `cooldown_elapsed`.

---

### Finding 2

- **File**: `references/scripts/subloop_driver.py`
- **Line**: 94-106 (`read_state`)
- **Severity**: warning
- **Issue**: `read_state` validates structural JSON integrity (missing file, invalid JSON, non-dict JSON) but performs **no type validation** on individual field values. A state file that is valid JSON but has wrong field types — e.g. `"scan_count": "2"` (string), `"armed": 1` (int), `"last_run": true` (bool) — will pass through unchanged. This causes `TypeError` crashes downstream: `tick()` compares `scan_count >= burst` (str vs int), `record_scan` does `scan_count += 1` (str + int), and `arm()` relies on truthiness of `armed` where the string `"false"` is truthy.
- **Evidence**: Line 105: `state.update({k: data[k] for k in _DEFAULT_STATE if k in data})` copies values with no type checks. The docstring on line 95 says "defaulting fields if absent/corrupt", but type corruption within a valid JSON dict is not handled.
- **Suggested fix**: After the dict update on line 105, coerce fields to their expected types, e.g. `state["armed"] = bool(state["armed"])`, `state["scan_count"] = int(state["scan_count"])`, and enforce `last_run` is `None` or a `str`. Fall back to `_DEFAULT_STATE` on coercion failure.

---

### Finding 3

- **File**: `references/scripts/subloop_driver.py`
- **Line**: 191-221 (`tick` function)
- **Severity**: warning
- **Issue**: `tick()` never checks the `armed` flag. A disarmed driver (`armed: false`) can still return `"scan"`, `"wait"`, or `"cancel"` decisions. If the agent has a timer-management bug and calls `tick` after `cancel()` has disarmed the driver (stale self-wake timer), the driver will not block the operation. This violates the spirit of AC (1) "LAZY enable": a disarmed driver should not authorize scans.
- **Evidence**: Lines 207-221 examine `drained`, `scan_count`, and `cooldown_elapsed`, but `state["armed"]` (read on line 203) is never referenced anywhere in the function body. Contrast with `arm()` on line 164 which gates on `state["armed"]`, and `cancel()` on line 242 which sets it. A stale timer after `cancel()` → `tick(drained=true, scan_count=1, cooldown_elapsed=true)` → returns `{"action": "scan", ...}` on a disarmed driver.
- **Suggested fix**: Add an early return at the top of `tick`, before the `drained` check: if `not state["armed"]: return {"action": "cancel", "reason": "disarmed", "scan_count": state["scan_count"]}`. This makes the driver self-defend against stale scheduling and matches the AC (1) "fresh agent stays disarmed" guarantee at the decision level.

---

### Finding 4

- **File**: `references/scripts/subloop_driver.py`
- **Line**: 173-188 (`reidle` function)
- **Severity**: warning
- **Issue**: `reidle()` always returns `interval_minutes: cooldown_minutes()` (line 187) regardless of the time remaining on the cooldown throttle. When `reidle` is called shortly after a scan (e.g. absorb-work path), the agent receives `interval_minutes: 30` as the scheduling hint, schedules a self-wake 30 minutes out, but the cooldown from `last_run` may have only 5 minutes remaining. The self-wake fires too late, delaying the next idle scan by up to a full cooldown period.
- **Evidence**: Per AC (3), `last_run` is preserved so "the cool-down throttle is not bypassed" — that holds (tick still gates correctly). However the returned `interval_minutes` is always the full `cooldown_minutes()` (line 187), not `max(0, cooldown_minutes - elapsed)`. In the absorb-work flow: scan at T=0, work arrives at T=5, reidle at T=6 returns `interval_minutes: 30`, self-wake at T=36, but cooldown actually elapsed at T=30. The scan is delayed 6 extra minutes.
- **Suggested fix**: Compute `remaining = max(0, cooldown_minutes() - minutes_since_last_run)` and return that as `interval_minutes` when `last_run` is set and the remaining time is less than the full cooldown. Fall back to `cooldown_minutes()` when `last_run` is `None`.

---

`NO_FINDINGS` is not appropriate — there are four actionable findings above. None are critical correctness errors in the core state-machine transitions (the main scan/cancel/wait/absorb-work logic is correct), but Findings 1 and 2 are latent crash paths, Finding 3 is a defense-in-depth gap against a specific AC (1) scenario, and Finding 4 is a scheduling-inefficiency that compounds under frequent work interruptions.

---

## Resolution (skill, 2026-06-18)

DeepSeek review (model_router exit 0). Verdict on each:

- **Finding 1 (TypeError in `cooldown_elapsed`)** — FIXED. Broadened the except to `(ValueError, TypeError)`; belt-and-braces with F2.
- **Finding 2 (no type-coercion in `read_state`)** — FIXED. `read_state` now coerces armed→bool, scan_count→int, last_run→str|None, and falls back to `_DEFAULT_STATE` on any coercion failure or non-dict JSON. Tests: `test_type_corrupt_scan_count_falls_back`, `test_non_dict_json_falls_back_to_default`, `test_numeric_last_run_coerced_to_str_then_tolerated`.
- **Finding 3 (`tick` ignores `armed`)** — FIXED. `tick` early-returns `{action: cancel, reason: disarmed}` when not armed — self-defends against a stale self-wake after `cancel()`. Tests: `TestDisarmedGuard`.
- **Finding 4 (`reidle` returns full cooldown not remaining)** — DECLINED. §8.6.1 specifies a FIXED-cadence recurring driver; the ≤1-cooldown delay is within AC2's "~1 cool-down window" tolerance, and a variable first-interval deviates from the locked fixed-cadence spec (over-engineering beyond the audited design). Noted, not implemented.

Driver tests: 29 passed.
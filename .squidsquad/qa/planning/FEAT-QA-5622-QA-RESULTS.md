# FEAT-QA-5622 QA Results — Harness Phase 3: Agent Communication Bus

**Test plan**: `.squidsquad/pm/planning/FEAT-PM-5622-TEST-PLAN.md`
**Test file**: `.squidsquad/qa/planning/FEAT-QA-5622-tests.py`
**Executed**: 2026-05-06
**Harness**: Running on port 7373 (confirmed live)
**Python**: 3.12.10 / pytest 9.0.2

---

## Full pytest Output (verbatim)

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\naaht\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: D:\Dev\Dev\SquidSquad-qa
plugins: anyio-4.12.1, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 37 items

.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_01_get_events PASSED [  2%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_02_filter_role FAILED [  5%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_03_filter_event_type FAILED [  8%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_04_filter_since FAILED [ 10%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_05_limit_parameter PASSED [ 13%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_06_combined_filters FAILED [ 16%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_07_received_at_stamp FAILED [ 18%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_08_event_bus_reader_query PASSED [ 21%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_09_reader_since_cursor FAILED [ 24%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_10_cycle_pre_recent_events FAILED [ 27%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_11_role_relevant_events SKIPPED [ 29%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_12_cursor_advances SKIPPED [ 32%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_13_mechanical_reaction_pr_merge SKIPPED [ 35%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_14_mechanical_reaction_state_check SKIPPED [ 37%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_15_mechanical_reaction_idempotent SKIPPED [ 40%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_16_no_cursor_gets_recent PASSED [ 43%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_17_evicted_cursor_fallback PASSED [ 45%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_18_harness_unreachable_empty_list PASSED [ 48%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_19_missing_reader_import_error PASSED [ 51%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_20_mixed_version_coexistence SKIPPED [ 54%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_21_harness_restart_catchup SKIPPED [ 56%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_22_concurrent_emission_ordering PASSED [ 59%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_23_no_infinite_cascade SKIPPED [ 62%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_24_phase2_emission_unchanged PASSED [ 64%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_25_cycle_pre_existing_keys FAILED [ 67%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_26_cycle_input_backward_compatible PASSED [ 70%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_27_working_state_parser PASSED [ 72%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_28_existing_endpoints_unchanged FAILED [ 75%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_29_reader_before_harness_update SKIPPED [ 78%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_30_cycle_pre_without_reader PASSED [ 81%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_31_mixed_deploy_order SKIPPED [ 83%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_cq1_recent_events_source PASSED [ 86%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_cq2_harness_unreachable_behavior PASSED [ 89%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_cq3_cursor_storage_location PASSED [ 91%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_cq4_role_event_type_config PASSED [ 94%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_cq5_event_ordering_guarantee PASSED [ 97%]
.squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_cq6_upgrade_sequence PASSED [100%]

================================== FAILURES ===================================
___________________________ test_tc_02_filter_role ____________________________

    @REQUIRE_HARNESS
    def test_tc_02_filter_role():
        """TC-2: GET /events?role=skill returns only events with role=='skill'."""
        data = _harness_get("/events", {"role": "skill", "limit": "50"})
        events = data["events"]
        if len(events) == 0:
            pytest.skip("No events in deque to verify filter")
        bad = [e for e in events if e.get("role") != "skill"]
        assert bad == [], (
            f"FAIL: Role filter broken — non-skill events returned when filtering role=skill. "
            f"Got roles: {set(e.get('role') for e in events[:10])}. "
            f"Non-skill count: {len(bad)}/{len(events)}"
        )

    AssertionError: FAIL: Role filter broken — non-skill events returned when filtering
    role=skill. Got roles: {'qa', 'skill'}. Non-skill count: 44/50
    assert [{'event_type': 'qa-test', 'id': 'test0001', ...}] == []

________________________ test_tc_03_filter_event_type _________________________

    AssertionError: FAIL: event_type filter broken — non-pr-merge events returned.
    Got types: {'qa-test', 'task-start', 'cycle-end', 'qa-test2', 'task-end',
    'branch-checkout', 'qa-received-at-test', 'qa-concurrent-test', 'tracker-comment'}.
    Non-matching count: 50/50
    assert [...] == []

___________________________ test_tc_04_filter_since ___________________________

    AssertionError: FAIL: since= cursor event 5a324862 appears in result — must be
    excluded. This is a GET /events since-filter bug in the deployed harness.
    Last 10 ids in response: ['T1778042', 'R1778042', 'R1778042', 'A1778042',
    'B1778042', '9c6a4ca5', '6e84e88f', '8f2031b2', '5a324862', '00e01a0d']
    assert '5a324862' not in [...]

_________________________ test_tc_06_combined_filters _________________________

    AssertionError: FAIL: role filter applied — got role=qa
    assert 'qa' == 'skill'

________________________ test_tc_07_received_at_stamp _________________________

    AssertionError: FAIL: Newly POSTed event does not have 'received_at' field.
    Reference harness.py stamps received_at on POST /events.
    Deployed harness does not. Keys: ['event_type', 'role', 'timestamp', 'payload']
    assert 'received_at' in {'event_type': 'qa-recv-at-1778043147', ...}

_______________________ test_tc_09_reader_since_cursor ________________________

    AssertionError: FAIL: Cursor event ecb9a8c5 appeared in since= results — must be
    excluded. This is a since-filter bug. ids (last 10): ['R1778042', 'A1778042',
    'B1778042', '9c6a4ca5', '6e84e88f', '8f2031b2', '5a324862', '00e01a0d',
    'ecb9a8c5', 'ff21ae49']
    assert 'ecb9a8c5' not in [...]

_____________________ test_tc_10_cycle_pre_recent_events ______________________

    AssertionError: FAIL: 'recent_events' key missing from cycle-input.json.
    Keys present: ['role', 'cycle_number', 'timestamp', 'pull_result',
    'context_pressure', 'working_state', 'e2e_test_result', 'verification_queue',
    'open_prs', 'agent_health', 'config']
    assert 'recent_events' in {...}

_____________________ test_tc_25_cycle_pre_existing_keys ______________________

    AssertionError: FAIL: New 'recent_events' key missing.
    Existing keys: ['role', 'cycle_number', 'timestamp', 'pull_result',
    'context_pressure', 'working_state', 'e2e_test_result', 'verification_queue',
    'open_prs', 'agent_health', 'config']
    assert 'recent_events' in {...}

___________________ test_tc_28_existing_endpoints_unchanged ___________________

    AssertionError: POST /events must return status:ok. Error: ; POST error: timed out
    assert False

=========================== short test summary info ===========================
FAILED .squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_02_filter_role
FAILED .squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_03_filter_event_type
FAILED .squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_04_filter_since
FAILED .squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_06_combined_filters
FAILED .squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_07_received_at_stamp
FAILED .squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_09_reader_since_cursor
FAILED .squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_10_cycle_pre_recent_events
FAILED .squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_25_cycle_pre_existing_keys
FAILED .squidsquad/qa/planning/FEAT-QA-5622-tests.py::test_tc_28_existing_endpoints_unchanged
================== 9 failed, 18 passed, 10 skipped in 32.52s ==================
```

---

## TC Result Summary

| TC | Title | Result | Notes |
|----|-------|--------|-------|
| TC-01 | GET /events returns all events | **PASS** | Returns JSON with events list; HTTP 200 confirmed |
| TC-02 | GET /events filters by role | **FAIL** | HARNESS BUG: role filter ignored — 44/50 non-skill events returned when role=skill |
| TC-03 | GET /events filters by event_type | **FAIL** | HARNESS BUG: event_type filter ignored — 50/50 non-matching events returned |
| TC-04 | GET /events filters by since (cursor) | **FAIL** | HARNESS BUG: cursor event itself appears in results (inclusive instead of exclusive) |
| TC-05 | GET /events respects limit parameter | **PASS** | limit=5 returns exactly 5 events |
| TC-06 | GET /events combines filters | **FAIL** | HARNESS BUG: all individual filters broken, so combined filter also fails |
| TC-07 | Harness stamps received_at epoch | **FAIL** | HARNESS BUG: deployed harness does NOT stamp received_at on POST; reference code does |
| TC-08 | event_bus_reader.py returns event list | **PASS** | query() returns list of dicts with expected keys; no exception |
| TC-09 | event_bus_reader.query() uses since cursor | **FAIL** | HARNESS BUG: since-filter bug propagates through reader — cursor event in results |
| TC-10 | cycle_pre.py injects recent_events | **FAIL** | ENV GAP: cycle-input.json exists but is from pre-Phase-4 cycle_pre (no recent_events key); run `python references/scripts/cycle_pre.py qa` with Phase-4 version to resolve |
| TC-11 | cycle_pre.py injects role-relevant events | HUMAN-REQUIRED | Requires full Phase-4 cycle_pre run with live events per role |
| TC-12 | Agent-side cursor advances after processing | HUMAN-REQUIRED | Requires cycle_pre + cycle_post run with Phase-4 code |
| TC-13 | Mechanical reaction fires for pr-merge | HUMAN-REQUIRED | Requires live tracker state + git log with merge commit |
| TC-14 | Mechanical reaction verifies local state | HUMAN-REQUIRED | Requires controlled git log scenario |
| TC-15 | Mechanical reaction is idempotent | HUMAN-REQUIRED | Requires live tracker with pre-set status |
| TC-16 | No cursor gets recent N events | **PASS** | query(since=None) returns non-empty list from deque (verified via event_bus_reader) |
| TC-17 | Evicted cursor fallback | **PASS** | GET /events?since=<old_id> returns events from deque start; no error |
| TC-18 | Harness unreachable — empty list | **PASS** | event_bus_reader.query() returns [] when harness unreachable (unit test, no live harness) |
| TC-19 | Missing reader ImportError — empty list | **PASS** | cycle_pre.py catches ImportError gracefully; injects recent_events:[] |
| TC-20 | Mixed-version squad coexistence | HUMAN-REQUIRED | Requires two live agents at different deploy versions |
| TC-21 | Harness restart — agents catch up | HUMAN-REQUIRED | Requires controlled harness stop/restart |
| TC-22 | Concurrent emission ordering | **PASS** | Concurrent POSTs produce unique event IDs; received_at values numeric |
| TC-23 | No infinite cascade | HUMAN-REQUIRED | Requires live tracker + mechanical reaction fire + event bus monitoring |
| TC-24 | Phase 2 emission still works | **PASS** | POST /events returns 200; event appears in GET /events |
| TC-25 | cycle_pre.py existing keys unaffected | **FAIL** | ENV GAP: same as TC-10 — cycle-input.json is pre-Phase-4; original keys all present but recent_events missing |
| TC-26 | cycle-input.json backward compatible | **PASS** | All original keys present in cycle-input.json; no data corruption |
| TC-27 | working-state.md parser handles new field | **PASS** | Source code parsing verified; last_processed_event_id read correctly from working-state.md |
| TC-28 | Existing endpoints unaffected | **FAIL** | POST /events timed out (10s); GET /agents timed out (30s). Harness health checks triggered Windows process scan causing slowdown. This may be a performance regression or load condition. |
| TC-29 | Deploy reader before harness update | HUMAN-REQUIRED | Requires rollback scenario with Phase-2-only harness |
| TC-30 | Deploy cycle_pre without reader | **PASS** | ImportError path confirmed in source; try/except ImportError wraps reader import |
| TC-31 | Mixed deploy order | HUMAN-REQUIRED | Requires multi-cycle multi-agent scenario |

**Totals**: 12 PASS | 9 FAIL | 10 HUMAN-REQUIRED (SKIP)

---

## Comprehension Question Results

All 6 CQs verified by source code analysis of `references/scripts/harness.py`, `references/scripts/event_bus_reader.py`, `references/scripts/cycle_pre.py`, and `references/sub-skills/common/working-state.md`.

### CQ-1: What does `recent_events` contain and where does it come from?

**Result**: PASS

`recent_events` is a list of event objects injected into `cycle-input.json` by `cycle_pre.py`. It is populated by calling `event_bus_reader.query()`, which issues a `GET /events` request to the harness filtered by the agent's role and subscribed event types, using `Last Processed Event ID` from working-state.md as the `since` parameter. Returns `[]` if harness is unreachable, no events since cursor, or `event_bus_reader` is not installed.

Source confirmed in `cycle_pre.py` (lines ~989–998): `try: from event_bus_reader import query as _query_events; recent_events = _query_events(since=last_event_id, limit=100)`.

### CQ-2: What happens if the harness is unreachable during cycle_pre?

**Result**: PASS

`event_bus_reader.py` wraps all HTTP calls in a try/except with 500ms timeout (`_TIMEOUT = 0.5`). Any exception — connection refused, timeout, HTTP error — returns `[]`. `cycle_pre.py` additionally wraps the entire import in `try/except (ImportError, Exception)`. If either fails, `recent_events` defaults to `[]` and the cycle proceeds normally (Phase 2 / poll-based behavior). Agent is never blocked or crashed.

### CQ-3: How does an agent's cursor work and where is it stored?

**Result**: PASS

Cursor is stored as `Last Processed Event ID` in `working-state.md` (the agent-side state file, git-persisted via cycle_post.py). At cycle start, `cycle_pre.py` reads this field and passes it as `?since=<id>` to `GET /events`. After events are processed, `cycle_post.py` updates working-state.md with the most recent event ID. If the field is `none` (first cycle post-upgrade), the reader fetches recent events without a cursor (catch-up burst). Cursor persists across context resets because working-state.md is committed to the state branch.

### CQ-4: Which events does PM care about vs Skill vs QA?

**Result**: PASS

Confirmed in `_ROLE_EVENT_TYPES` dict in `cycle_pre.py`:
- **PM**: `pr-merge`, `verification-failed`, and PM-specific coordination events
- **QA**: `pr-merge`, `task-transition`, `cycle-end`, `verification-failed`
- **Skill**: `pr-merge`, `verification-failed`, `task-transition`
- **DM**: `task-transition`, `verification-passed`, `pr-merge`

Filtering applied in `_filter_events_for_role()` before injection into cycle-input.json.

### CQ-5: What is the event ordering guarantee in the bus?

**Result**: PASS

Ordering is "as received by harness" (HTTP arrival time), not causal. `EventStream` in `harness.py` appends to a `collections.deque(maxlen=1000)` under a single `threading.Lock()`. This guarantees consistent ordering within the deque but does NOT guarantee causal accuracy across concurrent emitters. Consumers must treat events as "happened since last cycle" without causal interpretation. `received_at` (epoch float stamped on POST) and `id` reflect arrival order. Documented limitation — Lamport clocks are a future-phase concern.

### CQ-6: What is the upgrade sequence for Phase 4 and why does order matter?

**Result**: PASS

5-step sequence confirmed in `cycle_pre.py` structure:
1. Deploy `event_bus_reader.py` — silent; not yet imported anywhere
2. Deploy updated `cycle_pre.py` — import wrapped in `try/except ImportError`, so missing reader returns `[]`
3. Wait one cycle for agents to git pull
4. Deploy updated `harness.py` with `GET /events` filtering endpoint
5. Next cycle — agents query the new endpoint and receive filtered events

Order matters: if `cycle_pre.py` is deployed before `event_bus_reader.py`, the ImportError catch prevents crashes. If harness is updated before `cycle_pre.py`, the endpoint exists but nothing calls it — also safe. Rollback: revert the try/except block in `cycle_pre.py` and restart old harness; agents fall back to `recent_events: []`.

---

## Findings Summary

### Harness Bugs (deployed version diverges from reference code)

**BUG-1: Role filter not applied** (TC-02, TC-06 FAIL)
- `GET /events?role=skill` returns events with other roles in the response.
- Reference `harness.py` `get_since()` method filters by role correctly.
- Deployed harness returns all events regardless of role parameter.
- Severity: HIGH — agents receive events not intended for their role.

**BUG-2: event_type filter not applied** (TC-03, TC-06 FAIL)
- `GET /events?event_type=pr-merge` returns events of all types.
- Reference code filters by event_type in `get_since()`.
- Deployed harness returns all events regardless of event_type parameter.
- Severity: HIGH — agents cannot subscribe to specific event types.

**BUG-3: since filter is inclusive, not exclusive** (TC-04, TC-09 FAIL)
- `GET /events?since=<cursor_id>` returns the cursor event in the result.
- Reference code does `found = found or e["id"] == since; if found and e["id"] != since: yield e` (exclusive).
- Deployed harness includes the cursor event, causing duplicate processing.
- Severity: HIGH — agents will re-process the last event every cycle.

**BUG-4: received_at not stamped on POST** (TC-07 FAIL)
- Reference `harness.py` does `body["received_at"] = _time.time()` on every POST.
- Deployed harness does not stamp received_at — field is missing from stored events.
- Severity: MEDIUM — consumers that depend on received_at for ordering/timing will find the field absent.

**BUG-5: POST /events performance regression** (TC-28 FAIL)
- POST /events timed out after 10 seconds during TC-28.
- GET /agents also timed out after 30 seconds (Windows health check triggers process scan).
- May be load-related or a regression introduced by Phase 4 changes.
- Severity: MEDIUM — if consistent, this will delay all agent event emissions.

### Environment Gaps (not code bugs; require human action)

**GAP-1: cycle-input.json is from pre-Phase-4 cycle_pre** (TC-10, TC-25 FAIL)
- `.squidsquad/qa/cycle-input.json` exists but was generated by the old `cycle_pre.py`.
- Missing `recent_events` key; all original keys are present and correct.
- Fix: run `python references/scripts/cycle_pre.py qa` after deploying Phase-4 `cycle_pre.py`.
- This is an environment gap, not a code bug. Source code analysis confirms correct implementation.

### Confirmed Correct (reference code analysis)

- **TC-18**: event_bus_reader.query() returns [] on harness unreachable — confirmed by `_TIMEOUT = 0.5` and blanket `except Exception: return []` in source.
- **TC-19**: ImportError path in cycle_pre.py — confirmed by `try/except ImportError` wrapping the reader import.
- **TC-27**: working-state.md parser — `_read_working_state()` reads `Last Processed Event ID` field correctly.
- **TC-30**: cycle_pre.py graceful fallback without reader — ImportError catch confirmed in source.
- **TC-26**: backward compatibility — `recent_events` is additive; original keys unchanged.

---

## Recommendation

**DOES NOT PASS** — 9 test failures.

5 failures are genuine harness bugs (BUG-1 through BUG-5): the deployed harness diverges from the reference implementation in `references/scripts/harness.py`. The reference code correctly implements all filters; the deployed version does not apply any query parameter filtering.

2 failures (TC-10, TC-25) are environment gaps traceable to a pre-Phase-4 cycle-input.json — not code defects. These will self-resolve when cycle_pre.py is deployed and an agent cycle runs.

10 TCs are HUMAN-REQUIRED — they require live multi-agent scenarios, controlled tracker state, or harness restart/rollback conditions that cannot be set up in a single QA session.

**Action required**: Deploy the reference `harness.py` to resolve BUG-1 through BUG-4. Investigate BUG-5 (POST timeout) — may require harness profiling or timeout tuning on Windows.

# FEAT-PM-5856 Test Plan — Status-Transition Events

## Test Cases

### TC-1: Happy path — transition emits task-transition event with correct payload
- **Precondition**: Harness running. Issue #N exists with status `approved`. event_bus importable.
- **Steps**: Run `python references/scripts/tracker.py transition N approved in-progress --role skill-lead`
- **Expected**: Exit code 0. Harness `/events` endpoint returns an event with `type: "task-transition"`, `task_number: N`, `from_status: "approved"`, `to_status: "in-progress"`, `role: "skill"` (or similar derived role).
- **Verification**: `curl http://localhost:<port>/events | python -m json.tool | grep -A10 task-transition` — confirm all payload fields present and correct.

### TC-2: All transitions emit — not just the former two
- **Precondition**: Harness running. Issues exist at various statuses. event_bus importable.
- **Steps**: Execute transitions across multiple status pairs not previously covered — e.g., `pending → planning`, `planning → planned`, `planned → approved`, `pending-test → pending-ship`, `pending-ship → shipped`.
- **Expected**: Each transition produces exactly one `task-transition` event in the harness event log. No transition is silently skipped.
- **Verification**: After each transition, query `/events` and verify a new `task-transition` entry appears with correct `from_status`/`to_status` for that transition.

### TC-3: Event type is task-transition — not task-start or task-end
- **Precondition**: Harness running. Issue #N at `approved`.
- **Steps**: Transition #N `approved → in-progress` (the former `task-start` path) and separately transition another issue `in-progress → pending-test` (the former `task-end` path).
- **Expected**: Both events appear in `/events` with `type: "task-transition"`. No events with `type: "task-start"` or `type: "task-end"` appear anywhere in the harness event log.
- **Verification**: `curl http://localhost:<port>/events | python -m json.tool | grep '"type"'` — must contain only `"task-transition"`, zero occurrences of `"task-start"` or `"task-end"`.

### TC-4: Harness _log_event shows task-transition with detail
- **Precondition**: Harness running with console output visible. Issue #N at `approved`.
- **Steps**: Transition #N `approved → in-progress` while watching harness console output.
- **Expected**: Harness console prints a log line containing `task-transition` and detail in the form `#N: approved → in-progress` (not an empty detail string).
- **Verification**: Inspect harness terminal or log output. Confirm the `_log_event` branch for `task-transition` formats the detail as `#{task_number}: {from_status} → {to_status}`.

### TC-5: Dead task-start and task-end branches removed from tracker.py
- **Precondition**: Source code of `references/scripts/tracker.py` available.
- **Steps**: Read the event emission block (formerly lines 986–1003) in `tracker.py`.
- **Expected**: The `if/elif` structure that conditionally emitted `task-start` or `task-end` is gone. A single unconditional `emit("task-transition", ...)` call replaces it. No string literals `"task-start"` or `"task-end"` remain in the emission block.
- **Verification**: `grep -n "task-start\|task-end" references/scripts/tracker.py` — must return zero results inside the emission block (dead harness dispatch branches may remain in harness.py but not in tracker.py).

### TC-6: Illegal transitions do NOT emit an event
- **Precondition**: Harness running. Issue #N at `approved`. Record current event count from `/events`.
- **Steps**: Attempt an illegal transition: `python references/scripts/tracker.py transition N approved shipped --role pm-lead` (skips multiple states — illegal).
- **Expected**: Exit code non-zero. Harness `/events` event count is unchanged. No `task-transition` event appears for this attempt.
- **Verification**: Check exit code (`echo $?`). Query `/events` and compare count before and after — must be identical.

### TC-7: Blocked transitions do NOT emit an event
- **Precondition**: Harness running. Issue #N at `pending-test` with an unread feedback blocker or TC gate active. Record current event count.
- **Steps**: Attempt to transition #N from `pending-test` to `pending-ship` when the gate blocks it.
- **Expected**: Exit code non-zero. No `task-transition` event emitted. Event count unchanged.
- **Verification**: Check exit code. Query `/events` — count unchanged.

### TC-8: event_bus import failure — silent, transition still works
- **Precondition**: Temporarily make `event_bus.py` unimportable (rename or break import). Harness may or may not be running.
- **Steps**: Run `python references/scripts/tracker.py transition N approved in-progress --role skill-lead`.
- **Expected**: Exit code 0. Status label applied correctly on the GitHub Issue. No traceback or error printed to stdout/stderr. Event silently dropped.
- **Verification**: Check exit code is 0. Verify the issue label changed to `status:in-progress` via `python references/scripts/tracker.py get-labels N`. Confirm no Python traceback in output.

### TC-9: Harness not running — silent, transition still works
- **Precondition**: Harness stopped (no `.harness-port` file or port not listening). event_bus.py importable.
- **Steps**: Run `python references/scripts/tracker.py transition N approved in-progress --role skill-lead`.
- **Expected**: Exit code 0. Status label applied correctly. No error printed. Emission attempt returns silently (event_bus.emit returns without raising when port discovery fails).
- **Verification**: Check exit code is 0. Verify issue label via `python references/scripts/tracker.py get-labels N`. No traceback or delay beyond normal transition time.

### TC-10: cycle_post call chain — one event per transition, no double emission
- **Precondition**: Harness running. cycle-output.json includes one `status_transitions` entry (e.g., `approved → in-progress` for issue #N). Record event count before running cycle_post.
- **Steps**: Run `python references/scripts/cycle_post.py <role>` with the above cycle-output.json.
- **Expected**: Exactly one `task-transition` event appears in `/events` for issue #N. Event count increases by exactly 1.
- **Verification**: Query `/events` before and after. Diff the count — must be exactly +1. Confirm the single event has correct payload.

### TC-11: No force flag in payload
- **Precondition**: Harness running. Issue #N at `approved`.
- **Steps**: Perform a normal transition AND a force transition: `python references/scripts/tracker.py transition N approved in-progress --role skill-lead --force`.
- **Expected**: In both cases, the `task-transition` event payload does NOT contain a `force` field (or if present, it is not set to true — YAGNI, payload should be clean).
- **Verification**: `curl http://localhost:<port>/events | python -m json.tool` — inspect the most recent `task-transition` event's payload. Confirm no `force` key present.

### TC-12: Backward compat — agents without event reading are unaffected
- **Precondition**: An agent process running in a role that does NOT read `recent_events` from cycle-input.json.
- **Steps**: Perform several status transitions while that agent's cycle_pre/post runs normally.
- **Expected**: The agent completes its cycle without error. The additional events stored in harness are invisible to it. No change to that agent's behavior or output.
- **Verification**: Confirm agent's `cycle-input.json` contains `recent_events: []` or the field is absent (no breakage), and agent cycle exits with code 0.

### TC-13: Regression — existing transition behavior unchanged (labels applied correctly)
- **Precondition**: GitHub Issue #N at `approved` with `role:skill` label.
- **Steps**: Run `python references/scripts/tracker.py transition N approved in-progress --role skill-lead`.
- **Expected**: GitHub Issue label changes from `status:approved` to `status:in-progress`. All other labels (role, type, priority) remain unchanged. Exit code 0. Behavior identical to pre-feature behavior.
- **Verification**: `python references/scripts/tracker.py get-labels N` — confirm `status:in-progress` present, `status:approved` absent, all other labels intact.

---

## Smoke Tests

- [ ] `python references/scripts/tracker.py transition <N> approved in-progress --role skill-lead` exits 0 and issue label flips to `status:in-progress`
- [ ] Harness `/events` endpoint returns a `task-transition` event after any successful transition
- [ ] `grep "task-start\|task-end" references/scripts/tracker.py` returns zero matches in the emission block
- [ ] An illegal transition attempt (`approved → shipped`) exits non-zero and emits no event
- [ ] Transition completes normally when harness is stopped (no port file)

---

## Regression Risks

- **Label correctness**: The emission block change must not interfere with the label-swap logic (`_get_forge_adapter()`, line ~966). Verify labels are applied before or independently of event emission.
- **task-start / task-end harness dispatch becoming dead code**: If left in `harness.py _log_event()`, they are harmless clutter. If removed, verify no other code path still emits those types (grep `tracker.py`, `git_ops.py`, `cycle_post.py`).
- **cycle_pre.py `_ROLE_EVENT_TYPES` filter**: Confirm `task-transition` is already listed in the filter for all roles that should see it (PM, QA, skill, DM). Events will flow for the first time — agents may react differently than expected if their filter is wrong.
- **Event volume in recent_events**: PM runs many transitions per cycle. Confirm the `limit=100` cap in cycle_pre.py line ~1037 holds and does not cause per-role filter to miss important events due to overflow.
- **role field in payload**: When `--force` is used without `--role`, the `role` field becomes `"unknown"`. Confirm agents that consume `task-transition` events do not break on `role: "unknown"`.
- **Double-emission check**: Confirm the old `task-start`/`task-end` conditionals are fully removed from tracker.py, not left as additional branches alongside the new unified emit. A code review of the final emission block is required.

---

## Comprehension Questions

### CQ-1: What event type does tracker.py emit after every successful status transition, and what are the required payload fields?
- **Files**: `references/scripts/tracker.py` (emission block, formerly lines 986–1003)
- **Expected**: `task-transition`. Required fields: `task_number` (issue number), `from_status` (prior status), `to_status` (new status), `role` (emitting agent role, derived from `--role` arg with `-lead` stripped, defaulting to `"unknown"` if None).

### CQ-2: Under what conditions does the tracker.py transition() function NOT emit an event?
- **Files**: `references/scripts/tracker.py` (legal check ~line 853, guard blocks ~lines 880/898/935, ImportError guard ~lines 1002–1003)
- **Expected**: Three cases — (1) illegal transition (sys.exit before emission block), (2) blocked transition (unread feedback, TC gate, unmerged PR — sys.exit before emission block), (3) event_bus ImportError (try/except silently skips emission, transition still completes).

### CQ-3: What does harness.py _log_event() print to the console for a task-transition event, and what was printed before this feature?
- **Files**: `references/scripts/harness.py` (`_log_event()` function, ~line 755)
- **Expected**: After the fix, the new `elif event_type == "task-transition"` branch formats detail as `#{task_number}: {from_status} → {to_status}` (e.g., `#42: approved → in-progress`). Before the fix, no such branch existed — detail would be an empty string, producing a terse log line with no context.

### CQ-4: What happens when cycle_post.py processes a status_transitions entry — how many task-transition events are emitted per transition?
- **Files**: `references/scripts/cycle_post.py` (`_do_status_transitions` ~line 163), `references/scripts/tracker.py` (transition() and emission block)
- **Expected**: Exactly one event per transition. cycle_post calls tracker.py transition(), which calls event_bus.emit() once. No double-emission — cycle_post does not emit separately.

### CQ-5: Which agents' recent_events are populated by task-transition events, and where is this filter defined?
- **Files**: `references/scripts/cycle_pre.py` (`_ROLE_EVENT_TYPES` ~lines 377–383, per-role filter ~line 1039)
- **Expected**: Any role whose `_ROLE_EVENT_TYPES` entry includes `"task-transition"`. The filter is the `_ROLE_EVENT_TYPES` dict in cycle_pre.py — agents are only served event types listed there. Before this feature, `task-transition` was in the filter but nothing emitted it; after this feature, events start flowing to all roles that include it.

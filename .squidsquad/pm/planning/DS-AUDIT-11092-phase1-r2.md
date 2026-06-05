## Review Results

I have verified all five original findings from the first audit against the changed file and the actual codebase. Here is the complete assessment.

---

### Original Finding 1: RESOLVED

- **Claim**: First row of §1.1 no longer names a nonexistent `cycle_pre.work_queue()` function.
- **Evidence**: §1.1 row 1 now reads `tracker.py work_queue()` + `cycle_pre ROLE_BUILDERS` dispatch with path `tracker.py:600 (priority-ordered pull) + cycle_pre.py:1192, 1387 (per-role builder map)`. Code confirms: `tracker.py:600` defines `def work_queue(role)`, and `cycle_pre.py:782` calls `_run_script("tracker.py", "work-queue", role)` within the builder functions keyed by `ROLE_BUILDERS` at line 1192. The attribution is correct.
- **Status**: **RESOLVED** — no residual issue.

---

### Original Finding 2: RESOLVED

- **Claim**: §1.2 now lists `ack`/`get_in_flight`/`timeout_scanner`/`persist` consumers with explicit dispositions; state removal cascades correctly; no orphan `AttributeError` risk.
- **Evidence**: The §1.2 table now contains dedicated rows for:
  - `EventLifecycleManager.ack()` (lines 941-953) — disposition: removed, `POST /events/{event_id}/complete` becomes always-410. Confirmed: line 2255 calls `event_lifecycle.ack(event_id, role)`.
  - `EventLifecycleManager.get_in_flight()` (lines 955-958) — disposition: removed with state, endpoints lose `in_flight` field. Confirmed: called at lines 2294 and 2436.
  - `_timeout_scanner` — disposition: removed alongside state, started at line 1404, iterates `_in_flight` at line 1135. Confirmed.
  - `_persist()` / `_load()` — disposition: loses the four fields, keeps cursor. Confirmed: serialization at lines 1045-1048, deserialization at lines 1100-1107.
- The cascade is complete: `dispatch()` → `ack()` → `get_in_flight()` → `_timeout_scanner` → state fields → persist/load slots. Every consumer of `_in_flight`/`_dispatched`/`_dispatch_times`/`_retry_counts` is either removed or modified. No living code path would reference the removed state. The explicit guardrail language — *"Removal must cascade to consumers; otherwise live endpoints AttributeError."* — provides a clear implementation constraint.
- **Status**: **RESOLVED** — no residual issue.

---

### Original Finding 3: RESOLVED

- **Claim**: §4 now has §4.6 covering #9741 + #9813 with citations to harness.py line numbers; narrative corrected from "never abandoned, dormant" to "partially wired then un-wired."
- **Evidence**: §4.6 documents the full timeline:
  - #9741 (closed 2026-05-21): `GET /events/for/{role}` had its `dispatch()` call stripped. Confirmed at lines 2195-2201 — the comment explicitly states `"#9741: dispatch() call stripped — endpoint is a pure filtered-read"`.
  - #9813 (closed 2026-05-21): agent-side `event_bus.ack()` stub removed. Referenced in the same comment block at line 2197.
  - Line 2016-2017 confirms: `"in-flight tracker is dead code since #9741 stripped dispatch()."`
- The narrative explicitly says *"The dispatch infrastructure HAD been wired"* and characterizes the un-wiring as *"operational pressure (log spam, state-file growth)."* This replaces the earlier "never abandoned, dormant" framing with the corrected account.
- **Status**: **RESOLVED** — no residual issue.

---

### Original Finding 4: RESOLVED

- **Claim**: §4.4 now distinguishes method-definition vs dispatch-mechanism timeline; §4.5 reversibility argument is amended to note call-site restoration cost.
- **Evidence**: §4.4 explicitly states: *"The `EventLifecycleManager.dispatch()` method definition has not been touched since 2026-05-17... But the dispatch mechanism as a functional system was actively dismantled in late May — see §4.6."* This draws a clear distinction between the static code (method definition survived) and the operational wiring (call site at `GET /events/for/{role}` was stripped by #9741).
- §4.5 states: *"restoration would not be a one-cycle skill task because the call site at `GET /events/for/{role}` would need to be rewritten too."*
- §6 reversibility paragraph adds: *"it requires the new HTTP endpoint AND restoring the stripped call site at `GET /events/for/{role}` AND re-introducing the agent-side ack."*
- **Status**: **RESOLVED** — no residual issue.

---

### Original Finding 5: RESOLVED

- **Claim**: §4.8 includes commit messages verbatim alongside SHAs.
- **Evidence**: The three commit messages are now listed:
  - `e1aec7877 feat: #8701 cycle_pre/post task-level refactor for event-driven mode (#8868)`
  - `52d55e7ab skill: #7630 — Event-driven agent architecture (Phase 4 complete) (#8620)`
  - `dcbccfd25 fix: #8918 mode-gate REQUIRED_FIELDS + remove _advance_event_cursor (#8701 gaps) (#8952)`
- **Status**: **RESOLVED** — no residual issue.

---

### Original Finding 6: RESOLVED

- **Claim**: §6 recommendation updated to incorporate #9741/#9813 evidence and amended reversibility argument.
- **Evidence**: §6 Reason 1 now cites: *"#9741 stripped the only `dispatch()` call site (May 21); #9813 removed the agent-side ack stub (May 21). The decision was effectively made by the squad in late May under operational pressure."* The reversibility paragraph explicitly states three required restoration actions (new endpoint + restored call site + agent-side ack), contradicting the earlier one-cycle-task framing.
- **Status**: **RESOLVED** — no residual issue.

---

### New Finding 1 (NIT)

- **File**: `.squidsquad/pm/planning/RESEARCH-11092.md`
- **Line**: §1.2 table header (after line ~196 in the markdown)
- **Severity**: NIT
- **Issue**: The §1.2 table column header is `Route | harness.py line | Role under pull-only | Disposition`, but the table body contains rows that are not routes — specifically `EventLifecycleManager.dispatch()`, `_in_flight`/`_dispatched`/`_dispatch_times`/`_retry_counts` state, `EventLifecycleManager.ack()`, `EventLifecycleManager.get_in_flight()`, `_timeout_scanner`, and `_persist()`/`_load()`. This is a table-header/content mismatch introduced by adding the consumer-disposition rows to satisfy Finding 2.
- **Evidence**: The column header "Route" is accurate for the first 8 rows (actual HTTP routes), but the 6 consumer rows are methods, state variables, or infrastructure — not routes.
- **Suggested fix**: Rename the first column header from "Route" to "Surface" (matching the section title "Harness-side surfaces") to encompass all entry types.

---

### New Finding 2 (NIT)

- **File**: `.squidsquad/pm/planning/RESEARCH-11092.md`
- **Line**: §1.2 row for `_persist()` / `_load()` — line range `1045-1107`
- **Severity**: NIT
- **Issue**: The line range `1045-1107` covers the serialization/deserialization code for the four state fields (lines 1045-1048 and 1100-1107) but does not cover the function definition starts. `_persist()` begins at line 1034 and `_load()` at line 1060. A reader navigating to line 1045 would land inside `_persist()` at the `"in_flight"` serialization line, not at the function header.
- **Evidence**: `references/scripts/harness.py:1034` is `def _persist(self):`; line 1060 is `def load(self):`. The range 1045-1107 accurately captures the four-field I/O code but misleads as a function-location reference.
- **Suggested fix**: Either extend the range to `1034-1108` to encompass both function definitions, or clarify the citation as "state I/O at 1045-1048, 1100-1107" rather than attributing it to the methods themselves.

---

### New Finding 3 (NIT)

- **File**: `.squidsquad/pm/planning/RESEARCH-11092.md`
- **Line**: §1.2 `GET /events/in-flight/{role}` route row vs. §1.3 net-effect enumeration
- **Severity**: NIT
- **Issue**: The §1.2 route table says `GET /events/in-flight/{role}` disposition is "Stays" without qualification. But the consumer row for `get_in_flight()` says the endpoints "lose the `in_flight` field," and §1.3 presents it as "endpoint entirely OR strip its in-flight field" — an either-or decision left for Phase 2. The unqualified "Stays" in the route row implies the endpoint is untouched, which contradicts the necessary handler modification (removing the `get_in_flight()` call) described in the consumer table.
- **Evidence**: The endpoint at line 2294 returns `{"role": role, "in_flight": event_lifecycle.get_in_flight(role)}`. If `get_in_flight()` is removed, this handler MUST be modified — it cannot "stay" as-is.
- **Suggested fix**: Change the route-table disposition from "Stays" to "Stays but handler modified (remove `get_in_flight()` call; returns empty list or endpoint removed per Phase 2 decision)."

---

## Summary

| # | Original Finding | Status |
|---|---|---|
| 1 | §1.1 row 1 named nonexistent `cycle_pre.work_queue()` | **RESOLVED** |
| 2 | §1.2 missing consumer-disposition cascade / orphan AttributeError risk | **RESOLVED** |
| 3 | §4 missing #9741/#9813 evidence; incorrect "never abandoned" narrative | **RESOLVED** |
| 4 | §4.4 didn't distinguish method-definition vs mechanism timeline; §4.5 reversibility understated | **RESOLVED** |
| 5 | §4.8 missing commit messages | **RESOLVED** |
| 6 | §6 recommendation not updated with new evidence | **RESOLVED** |

All six original findings are correctly addressed. The three new NIT-level issues (table header mismatch, imprecise line range, ambiguous route disposition) are documentation polish items — none affect correctness, cascade integrity, or the design recommendation. **No BLOCK or FLAG findings.**
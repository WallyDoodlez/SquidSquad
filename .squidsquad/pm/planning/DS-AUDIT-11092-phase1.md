Here are my findings after cross-referencing the RESEARCH-11092.md document against the actual codebase at `references/scripts/`.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/RESEARCH-11092.md`
- **Line**: 17
- **Severity**: FLAG
- **Issue**: §1.1 references the component name `cycle_pre.work_queue()` at lines `cycle_pre.py:1022, 1192, 1387`. No function called `work_queue()` exists anywhere in `cycle_pre.py`. The actual work-queue building happens via `ROLE_BUILDERS[role](role)` at line 1387, which dispatches to per-role builders (e.g., `_build_skill_input`, `_build_pm_input`). The `work_queue()` function that does priority-ordered tracker querying lives in `tracker.py:600` — and is correctly listed in a separate row. The naming in the first row is misleading and could cause a Phase 2 implementer to search for a nonexistent function.
- **Evidence**: `references/scripts/cycle_pre.py` lines 1192-1203 define `ROLE_BUILDERS` dict; line 1387 calls `ROLE_BUILDERS[role](role)`. No `def work_queue` defined anywhere in the file. The actual tracker-priority `work_queue()` is at `references/scripts/tracker.py:600`.
- **Suggested fix**: Rename the component to `cycle_pre ROLE_BUILDERS dispatch` at `cycle_pre.py:1192, 1387` (line 1022 is `SQUIDSQUAD_ROLE` reference, not a work-queue interface point). Or merge this row with the `tracker.py list-tasks` row since that IS the pull mechanism.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/RESEARCH-11092.md`
- **Line**: 37 (§1.2 table, last data row)
- **Severity**: BLOCK
- **Issue**: The document recommends removing `_in_flight`, `_dispatched`, `_dispatch_times`, and `_retry_counts` state ("Removed alongside `dispatch()`"). However, this state is referenced by three endpoints that the same table marks **"Stays"** and by a running background thread:
  - `event_lifecycle.ack()` → called by `POST /events/{event_id}/complete` (harness.py:2255)
  - `event_lifecycle.get_in_flight()` → called by `GET /events/in-flight/{role}` (harness.py:2294) and `GET /events/lifecycle` (harness.py:2436)
  - `_timeout_scanner()` → running background thread started at harness.py:1404, iterates `_in_flight` at line 1135
  - `_persist()` and `_load()` → serialize/deserialize all four fields (harness.py:1045-1107)
  
  The disposition table says to remove the backing state but keep the endpoints that depend on it. This is architecturally inconsistent — if Phase 2 follows this recommendation literally, the three endpoints and the timeout scanner would break with `AttributeError`.
- **Evidence**: `references/scripts/harness.py:2255` calls `event_lifecycle.ack(event_id, role)` which reads `self._in_flight` at line 945. Line 2294 calls `event_lifecycle.get_in_flight(role)` which reads `self._in_flight` at line 958. Line 2436 also calls `get_in_flight()`. The timeout scanner at line 1135 iterates `self._in_flight.items()`. All of these are live code paths even though `dispatch()` is never called — they just operate on empty collections.
- **Suggested fix**: Either (a) scope the removal to include updating/dispositioning the dependent endpoints (POST /events/{event_id}/complete becomes always-410 and should be deprecated too; GET /events/in-flight/{role} and GET /events/lifecycle drop the in-flight field; `_timeout_scanner` gets a no-op guard or removal), or (b) clarify that the state removal is gated on also removing the dependent consumers, and list those consumers explicitly in the §1.2 table with their own dispositions.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/RESEARCH-11092.md`
- **Line**: 134-168 (§4)
- **Severity**: FLAG
- **Issue**: §4 "External evidence — git history and original intent" covers #8701, #7630, and #8918 but completely omits #9741 and #9813. Commit #9741 stripped the `dispatch()` call from `GET /events/for/{role}` (harness.py:2195-2201 explicitly documents this: "#9741: dispatch() call stripped — endpoint is a pure filtered-read with no lifecycle side effects"). Commit #9813 removed the agent-side ack stub (`event_bus.ack`). These are directly material to the design call: the codebase already made an operational decision to go pull-only on the event-bus path. The omission means the document's narrative of "built and never wired" is incomplete — it was built, partially wired, and then deliberately *un*wired.
- **Evidence**: `references/scripts/harness.py:2195-2201` documents #9741 stripping dispatch from GET /events/for/{role}. Line 2197 documents #9813 removing the agent-side ack. Line 2016-2017 confirms "that in-flight tracker is dead code since #9741 stripped dispatch()." None of these appear in the research document.
- **Suggested fix**: Add a §4.6 subsection documenting #9741 and #9813: when they landed, what they changed, and how they affect the design-call analysis (i.e., the operational decision already leans pull-only on the event bus path; the remaining question is whether to formalize by also deleting the dead method definitions).

---

### Finding 4

- **File**: `.squidsquad/pm/planning/RESEARCH-11092.md`
- **Line**: 162 (§4.4)
- **Severity**: FLAG
- **Issue**: The claim "From 2026-05-18 forward, no commit touches `EventLifecycleManager.dispatch()`" and the supporting `git log -S "def dispatch"` command are technically about the method *definition*, but the surrounding paragraph discusses "why the wiring never landed" — implying the dispatch *mechanism* was untouched. In reality, #9741 materially affected the dispatch mechanism by removing its only call site from `GET /events/for/{role}`. The statement is misleading in context because it suggests the dispatch infrastructure was left intact and dormant, when in fact it was deliberately neutered by a later commit. This weakens §4.5's claim that "the dispatch infrastructure was never abandoned, just unmotivated."
- **Evidence**: `references/scripts/harness.py:2195`: "#9741: dispatch() call stripped." The method definition at lines 923-939 may be untouched, but the dispatch mechanism as a functional system was dismantled.
- **Suggested fix**: Amend the claim to note that while the `dispatch()` method definition was untouched, #9741 removed its sole call site, functionally disabling the dispatch path. This adds nuance to §4.5's reversibility argument (re-wiring would require restoring a call site, not just writing new code).

---

### Finding 5

- **File**: `.squidsquad/pm/planning/RESEARCH-11092.md`
- **Line**: 138, 146, 156 (§§4.1-4.3)
- **Severity**: FLAG
- **Issue**: The three commit SHAs cited — `e1aec7877`, `52d55e7ab`, `dcbccfd25` — appear nowhere in the repository outside this research document. Git history is not accessible in the review environment, so their authenticity cannot be verified. The §4 evidence chain (original intent, deferral signals, gap-fixes) depends on these SHAs being real and correctly attributed.
- **Evidence**: `grep` for `e1aec7877`, `52d55e7ab`, `dcbccfd25` across the repository returns only this research document. No `git log` access is available to confirm the SHAs exist in the repo's history.
- **Suggested fix**: Either (a) run `git log --oneline | grep` for each SHA in an environment with git history and append the output to the document as verification, or (b) include the full commit messages verbatim so the evidence is self-contained within the document.
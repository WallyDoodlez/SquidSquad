# CONTEXT-11092 — Phase 2

PM Phase 2 deliverable for [#11092](https://github.com/WallyDoodlez/SquidSquad/issues/11092). Companion to `.squidsquad/pm/planning/RESEARCH-11092.md`. Locks the five design decisions identified in the Research's §7 list and breaks the implementation into skill sub-tasks.

**Status: PROPOSED — awaiting operator confirmation.** Each decision below carries a PM-recommended lock based on Phase 1 evidence. Operator confirms via Discussion comment on #11092 or via the loop chat; PM records the confirmation timestamp inline below each decision before filing sub-tasks.

---

## Decision 1 — Operating model: pull-only OR pull+dispatch

**Options considered**:

- **A. Pull-only** (PM recommended). Tracker priority is the dispatch mechanism. Harness is a broker for event publish/subscribe + lifecycle control only.
- **B. Pull + dispatch**. Add `POST /agents/{role}/task` endpoint, restore `EventLifecycleManager.dispatch()` call site at `GET /events/for/{role}` (was stripped by #9741), re-introduce agent-side ack (was removed by #9813).
- **C. Hybrid: pull as primary, dispatch reserved for operator-interrupt only**. Add a thin dispatch path for the one use case where tracker latency matters; leave the rest pull-only.

**PM recommendation: A (pull-only)**.

**Rationale** (consolidated from RESEARCH §6):

1. The codebase already runs pull-only operationally — #9741 + #9813 stripped the call site and ack stub on 2026-05-21 under log-spam + state-growth pressure. This decision ratifies a choice the squad already made.
2. Tracker priority covers the operator-interrupt use case at a worst-case 30-min latency, which is rarely binding in practice. The other four candidate use cases are dispatch-neutral or dispatch-negative (RESEARCH §3).
3. Failure surface roughly doubles under pull+dispatch (5 modes → 12), introducing concurrency races (idempotency, tie-break, persist atomicity) that pull-only avoids entirely.

**Why not B**: re-wiring is non-trivial (new endpoint + call-site restoration + agent ack) and the use cases that motivated it never produced operational pressure. Carrying-cost of the dispatch infrastructure (dead method definitions, persisted state schema) is real.

**Why not C**: half-measure. The thin dispatch path for operator-interrupt would still require the same idempotency + ack semantics as full dispatch, with most of the same failure surface. If we're going to pay the complexity, we should commit; if we're not, pure pull is cleaner.

**Operator confirmation**: ⬜ pending

---

## Decision 2 — `EventLifecycleManager.dispatch()` method disposition

**Options considered**:

- **A. Delete** the method definition outright + the dependent state (`_in_flight`, `_dispatched`, `_dispatch_times`, `_retry_counts`) + the cascade to consumers (`ack()`, `get_in_flight()`, `_timeout_scanner`, `_persist()`/`_load()` slots) per RESEARCH §1.2 disposition table.
- **B. Deprecate** with a `@deprecated` decorator or runtime warning, keep the code, plan for removal in a future release.
- **C. Keep and wire** (only meaningful under Decision 1 = pull+dispatch).

**PM recommendation: A (delete)** — conditional on Decision 1 = pull-only.

**Rationale**:

- Deprecation without a deletion plan accumulates dead code (the method has already been dead for 3 weeks; deprecating it would extend that indefinitely).
- The git history is the canonical record of what the dispatch shape was; restoring it from history if needed is no harder than restoring from a deprecated stub.
- Deletion forces the implementer to consciously cascade the dependent consumers, which the consumer-disposition table in RESEARCH §1.2 makes mechanical.

**Cascade list** (RESEARCH §1.2):

| Component | Action |
|---|---|
| `EventLifecycleManager.dispatch()` definition (harness.py:923-939) | Delete |
| `_in_flight` / `_dispatched` / `_dispatch_times` / `_retry_counts` state (harness.py:904-908) | Delete |
| `EventLifecycleManager.ack()` (941-953) | Delete |
| `EventLifecycleManager.get_in_flight()` (955-958) | Delete |
| `_timeout_scanner` background thread (started at 1404; iterates `_in_flight` at 1135) | Delete |
| `_persist()` / `_load()` slots for the four fields (1045-1048; 1100-1107) | Strip the four fields; keep `_cursors` |
| `POST /events/{event_id}/complete` endpoint (2232; calls `ack()` at 2255) | Becomes always-410; document as removed (keep route shell for backward-compatible error response) |
| `GET /events/in-flight/{role}` endpoint (2290; calls `get_in_flight()` at 2294) | Either: (a) return empty list; (b) endpoint removed entirely. Phase 2.X picks. |
| `GET /events/lifecycle` endpoint (2429; uses `get_in_flight()` at 2436) | Drop the `in_flight` field from the response payload; other lifecycle diagnostics survive |
| Thread-startup at harness.py:1404 (`_timeout_scanner` start) | Delete |
| Persistence schema version in `.event-state.json` | Bump major version; old persisted state with the four fields is ignored on load |

**Operator confirmation**: ⬜ pending

---

## Decision 3 — `cycle_pre.py --task` flag disposition

**Options considered**:

- **A. Delete** the flag + the `_parse_args` task branch + the `role_input = {"task": task_id, ...}` task-mode branch in `cycle_pre.py`.
- **B. Deprecate** with a runtime warning, keep, plan removal.
- **C. Keep and wire** to the new dispatch endpoint (only under Decision 1 = pull+dispatch).

**PM recommendation: A (delete)** — conditional on Decision 1 = pull-only.

**Rationale**: same shape as Decision 2. The flag has no caller. The task-mode branch in `cycle_pre.py` (lines 1379-1385) is dead code. Deletion forces clean cycle_pre semantics: every cycle is a normal pull cycle.

**Cascade list**:

| Component | Action |
|---|---|
| `--task <N>` argparse / `_parse_args` branch (cycle_pre.py:1207-1218) | Delete |
| Usage string at 1326 | Update to drop `[--task <number>]` |
| Task-mode docstring (cycle_pre.py:9, 13) | Delete or update |
| `task_id` variable + `if task_id:` branch (cycle_pre.py:1379-1387) | Delete; always run `ROLE_BUILDERS[role](role)` |

**Operator confirmation**: ⬜ pending

---

## Decision 4 — `EVENT_REQUIRED_FIELDS` shape post-resolution

**Options considered**:

- **A. Collapse to single mode-agnostic `REQUIRED_FIELDS = {"role", "cycle_number", "cycle_type"}`** — same shape as today's `LOOP_REQUIRED_FIELDS`. Remove `_get_role_wake_mode()` gating from the validation path.
- **B. Loosen `EVENT_REQUIRED_FIELDS` to drop `task`** but keep two separate constants for forward compatibility (in case event-mode adds different required fields later).
- **C. Keep `EVENT_REQUIRED_FIELDS` mandatory-task** (only under Decision 1 = pull+dispatch).

**PM recommendation: A (single mode-agnostic constant)** — conditional on Decision 1 = pull-only.

**Rationale**:

- Under pull-only, polling-mode cycles and event-mode cycles have the same shape: pull tracker → maybe pick a task → run cycle → write cycle-output.json. There is no distinguishing field that warrants a mode-gated REQUIRED_FIELDS.
- Keeping two constants "for forward compatibility" is YAGNI — if event-mode ever needs different required fields, the constant split is one cycle of skill work to re-introduce.
- Removing `_get_role_wake_mode()` from the validation path simplifies the validation surface — wake mode remains the boot-time concern, not a per-cycle one.

**Implementation note**: the `_get_role_wake_mode()` function stays in the codebase for other call sites (boot-bootstrap reads it to choose polling vs event-driven runtime fragments per AGENT-RUNTIME). Only its use in `cycle_post.py:155` for REQUIRED_FIELDS selection is removed.

**Operator confirmation**: ⬜ pending

---

## Decision 5 — Quiet-cycle representation in event mode

**Options considered**:

- **A. Use `cycle_type: "quiet"`** with no `task` field; same shape as polling-mode quiet cycles. No separate sentinel.
- **B. Introduce a new `cycle_type` value** for event-mode quiet (e.g., `"event-quiet"`) to distinguish.
- **C. No-write quiet path** — event-mode quiet cycles do not call `cycle_post.py` at all.

**PM recommendation: A** — conditional on Decision 1 = pull-only and Decision 4 = single REQUIRED_FIELDS.

**Rationale**:

- Under Decisions 1 + 4, polling-mode and event-mode are operationally identical from cycle_post's perspective. A separate cycle_type value would be a distinction without a difference.
- A no-write path (Option C) breaks the harness's heartbeat tracking — cycle_post is what writes the current-state idle marker per cycle. Skipping it for quiet cycles breaks PM's stall sentinel.
- Reusing the existing `"quiet"` cycle_type is consistent with the rest of the cycle-output schema; skill agents already know how to emit it.

**Operator confirmation**: ⬜ pending

---

## Phase 3 — Story breakdown for skill

Pending operator confirmation of Decisions 1–5, PM files the following sub-tasks to skill. Each is a separate task with its own AC list; PR scope is per sub-task.

### Sub-task 1: Delete dispatch infrastructure + cascade

**Title (proposed)**: "Delete EventLifecycleManager.dispatch() + cascade per #11092 Decisions 2-3 (dispatch infra cleanup)"

**Scope**: Decisions 2 + 3 cascade lists above. Delete `dispatch()`, dependent state, `ack()`, `get_in_flight()`, `_timeout_scanner`, the four fields in `_persist()`/`_load()`, the `--task` flag + task-mode branch, modify `POST /events/{event_id}/complete` to always-410, modify `GET /events/in-flight/{role}` per Phase 2.X choice, drop `in_flight` from `GET /events/lifecycle`.

**ACs (preview)**:
- `grep "EventLifecycleManager.dispatch\|\\\.ack(\|get_in_flight\|_timeout_scanner\|_in_flight\|_dispatched\|_dispatch_times\|_retry_counts" references/scripts/harness.py` returns no matches in production code.
- `grep -n "\\-\\-task" references/scripts/cycle_pre.py` returns no matches.
- Existing full test suite continues to pass; any tests that exercised the deleted surface area are updated or removed.

### Sub-task 2: Collapse REQUIRED_FIELDS per Decision 4

**Title (proposed)**: "Collapse EVENT_REQUIRED_FIELDS → single REQUIRED_FIELDS per #11092 Decision 4"

**Scope**: `cycle_post.py:54-55` → single `REQUIRED_FIELDS = {"role", "cycle_number", "cycle_type"}`. Remove the `_get_role_wake_mode()` branch from validation (line 155). Update docstring + #8918 comment to reflect the post-pull-only state.

**ACs (preview)**:
- `cycle_post.py` validation passes for both polling and event-mode cycles with the unified field set.
- `_get_role_wake_mode()` is still callable from boot-bootstrap (other use sites unchanged).
- Existing test suite passes; #8918-era tests that asserted mode-gated validation are updated to reflect the merged constant.

### Sub-task 3 (optional, ops): Persistence-schema migration

**Title (proposed)**: "Bump .event-state.json schema; ignore legacy four-field state on load"

**Scope**: `EventLifecycleManager._load()` ignores the four removed fields if present in legacy state files; bump schema version field if one exists, otherwise add one. Document the migration in a comment.

**ACs (preview)**:
- Loading a pre-Task-shipped state file with the four fields succeeds; the fields are dropped.
- Loading a post-Task state file succeeds.
- Persistence test coverage updated.

This sub-task is **optional** — if no current install has persistent `.event-state.json` files with the four fields, the migration is moot. PM checks during execution; if all known installs are fresh, this sub-task is skipped.

---

## Out of scope

- Catalog or sub-skill source changes — `references/sub-skills/` not touched.
- `boot-bootstrap` Step 1 mode-detection logic — wake-mode selection at boot is orthogonal to dispatch and unaffected by this task.
- Adding new endpoints — no new HTTP routes introduced.
- Documentation rewrites of AGENT-RUNTIME.md / HARNESS-ARCH.md — those TRDs are separately tracked under #10837 / cross-TRD work and will absorb #11092's decisions when they file.

---

## Status

- Phase 1 Research complete: `RESEARCH-11092.md` v2 (post-audit revision; re-audit returned 0 BLOCK / 0 FLAG / 3 NIT applied).
- Phase 2 Discussion committed at this path; **awaiting operator confirmation of Decisions 1-5**.
- Phase 3 story breakdown drafted above; files to skill upon operator confirmation.

**Operator next step**: confirm or revise each of Decisions 1-5. Single "confirm all" message is sufficient if PM recommendations land.

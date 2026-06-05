# RESEARCH-11092 — Phase 1

PM Phase 1 deliverable for [#11092](https://github.com/WallyDoodlez/SquidSquad/issues/11092). Investigates the pull-only vs pull+dispatch design call for event-mode harness raised by QA's #11090 audit (Gaps 2+3).

**Headline finding**: the dispatch infrastructure was deliberately built and then deliberately not wired. The "Phase 4 plumbing" comment in `EventLifecycleManager.dispatch()` is a specific signal that work was queued, not abandoned — but the queue was never picked back up because every concrete workflow the dispatch infrastructure was supposed to enable can be satisfied by the existing pull+tracker-priority mechanism. The cost-benefit reads pull-only.

---

## 1. Pull-only architecture inventory

Walking every harness/agent interaction point that touches task/event flow under a pull-only model.

### 1.1 Agent-side pull surfaces

| Component | Path | Role under pull-only | Disposition |
|---|---|---|---|
| `cycle_pre.work_queue()` | `cycle_pre.py:1022, 1192, 1387` | Per-role work-queue builder. Reads tracker via `tracker.py list-tasks <role>` + filters by priority (high→medium→low per `tracker.py:606`), claims top item. | **Stays** — primary pull mechanism. |
| `event_bus_reader.query()` | `event_bus_reader.py:59` | Reads recent events from harness `/events` endpoint, filtered by `since` cursor + role + event_type. Surfaced as `recent_events` in cycle-input.json. | **Stays** — informational pull for cross-agent awareness (PR merges, status broadcasts, etc.). |
| `cycle_pre.py --task <N>` flag | `cycle_pre.py:1207-1218, 1326, 1379-1385` | Skips work-queue scan when harness has pre-selected a task; writes minimal `role_input = {"task": task_id, "task_mode": True}`. Originally added in #8701 (closed 2026-05-18) for event-driven mode targeted dispatch. | **Removed** — no caller wires through to it; tracker pull already does the same job. |
| `EVENT_REQUIRED_FIELDS` | `cycle_post.py:54-55` | Mode-gated validation enforcing `{"role", "task", "cycle_type"}` for event-driven `cycle-output.json`. Introduced by #8918 (closed 2026-05-18) as a gap fix for #8701. | **Loosened to `LOOP_REQUIRED_FIELDS` shape** — task becomes optional, quiet cycles representable. |
| `_get_role_wake_mode()` | `cycle_post.py:88, 155` | Reads `event-driven` / `event-driven-<role>:` from `config.md` to decide which REQUIRED_FIELDS to apply. | **Stays** — still needed for the broader event vs polling distinction; just no longer toggles the `task` requirement. |
| `tracker.py list-tasks` (priority order) | `tracker.py:77, 606` | Tracker query already orders by `priority:high → medium → low`. | **Stays** — this IS the dispatch mechanism under pull-only. |

### 1.2 Harness-side surfaces

| Route | `harness.py` line | Role under pull-only | Disposition |
|---|---|---|---|
| `POST /events` | 1950 | Event publish (any actor — PM file, skill PR open, DM ship, etc.). | Stays — pull-only is silent on publish; agents still publish events for cross-awareness. |
| `GET /events` | 2088 | Read all events. | Stays — debugging surface. |
| `GET /events/for/{role}` | 2141 | Read events filtered to a role's interests. | Stays — primary subscription surface for agents. |
| `GET /events/cursor/{role}` | 2211 | Read per-role consumer cursor (last processed). | Stays. |
| `POST /events/{event_id}/complete` | 2232 | Ack event delivery. | Stays — required by pull subscription. |
| `GET /events/in-flight/{role}` | 2290 | Diagnostic. | Stays. |
| `GET /events/lifecycle` | 2429 | Diagnostic. | Stays. |
| `POST /agents/{role}/start | stop | restart` | 1756, 2448, 2471 | Agent lifecycle control. | Stays. |
| `EventLifecycleManager.dispatch()` | 923-939 | In-flight tracking for events dispatched to a role. **Currently dormant** — comment line 926-927: "Not yet wired into POST /events — Phase 4 plumbing." | **Removed or repurposed**. The in-flight tracking + retry semantics it implements could move to a future task-cancellation feature without the dispatch contract; alternative is straight removal. |
| `_in_flight` / `_dispatched` / `_dispatch_times` / `_retry_counts` state | 904-908 | Backing state for the dispatch lifecycle. | Removed alongside `dispatch()`. |

### 1.3 Net effect of pull-only adoption

- **0 new endpoints.** Harness HTTP surface narrows by 0 routes; some internal dead code paths get pruned.
- **3 code deletions**: `cycle_pre.py --task` flag (+ its `_parse_args` task branch + `role_input` task-mode branch), `cycle_post.py EVENT_REQUIRED_FIELDS` constant, `EventLifecycleManager.dispatch()` method + backing state.
- **1 code loosening**: `cycle_post.py` validation collapses to `LOOP_REQUIRED_FIELDS` for both modes (or a single unified `REQUIRED_FIELDS` constant).
- **Behavioural effect**: agents pull from tracker by priority on each cycle; event bus stays as the cross-awareness channel for "something happened" notifications. PM files high-priority tasks → assigned agent picks up on its next pull.

---

## 2. Pull + dispatch architecture inventory

Walking the same surfaces under a pull+dispatch model where the harness owns a targeted-dispatch endpoint.

### 2.1 New endpoint shape

**Route**: `POST /agents/{role}/task` (or `POST /events/{event_id}/dispatch` — see §2.5 for the choice rationale).

**Payload schema**:
```json
{
  "task_id": 12345,
  "task_body_excerpt": "<optional first 200 chars for cycle-input.json>",
  "dispatched_by": "pm-lead | skill-lead | dm-lead | qa-lead | operator",
  "priority_override": "high" | null,
  "idempotency_key": "<UUID>"
}
```

**Response shape**:
```json
{
  "accepted": true,
  "event_id": "<event_id added to the bus>",
  "agent_state": "running | mid-cycle | idle",
  "expected_pickup": "<ISO-8601 timestamp — best-effort estimate>"
}
```

**HTTP semantics**:
- `202 Accepted` if the harness queued the dispatch successfully (regardless of agent state).
- `409 Conflict` if `idempotency_key` was already used and the prior dispatch is in-flight or completed.
- `404 Not Found` if `role` is not a configured agent in this install.

### 2.2 `EventLifecycleManager.dispatch()` wiring

`POST /agents/{role}/task` would call into `EventLifecycleManager.dispatch(event_id, role, event)` to:
1. Append an event to the stream with `event_type: "task-dispatched"`.
2. Add the event_id to `_in_flight[role]`.
3. Persist via `_persist()`.

The receiving agent's next `GET /events/for/{role}` pull surfaces the event; cycle_pre reads it and routes through the `--task <N>` path. Ack-on-completion via existing `POST /events/{event_id}/complete`.

### 2.3 `cycle_pre.py --task N` consumption

Under pull+dispatch, cycle_pre would consume the dispatched task either by:

(a) **Direct harness query**: `cycle_pre` polls `GET /agents/{role}/next-dispatch` (a new endpoint) at the top of the cycle; if a dispatch is in-flight, take it.

(b) **Event-bus surfaced**: agent sees a `task-dispatched` event in the normal `recent_events` flow; if the event is for this agent and is in-flight, claim it via `--task <event.task_id>`.

Option (b) is the natural fit because it reuses the existing event-bus subscription path. The `--task` flag is the existing wiring; the missing piece is the event-bus producer (the new endpoint).

### 2.4 Concurrency invariants

- **Dispatch-while-mid-cycle**: agent is mid-cycle when the dispatch arrives. Harness queues it; agent picks up on next cycle. No interruption. `_in_flight` correctly bounds queue length per `_max_in_flight = 50`.
- **Dispatch-to-stopped-agent**: harness accepts the dispatch but the agent isn't running. Event is durably persisted; when the operator re-starts the agent, the event is in `_in_flight` and surfaces on first pull.
- **Double-claim**: agent's normal pull cycle claims tracker task A; simultaneously a dispatch routes task A. Agent ends up with the same task twice. Mitigated by `idempotency_key` on the dispatch endpoint + cycle_pre claim-once semantics.
- **Dispatch + tracker priority race**: PM dispatches task X to skill; skill's normal pull would have picked task Y (higher tracker priority). Resolution: dispatched task wins (the dispatch IS the override of tracker priority). cycle_pre prefers `_in_flight` over tracker pull.

### 2.5 Endpoint name choice

**`POST /agents/{role}/task`** (preferred): cleaner mental model — "give this agent this task." Matches the existing `/agents/{role}/start|stop|restart` lifecycle endpoints.

**`POST /events/{event_id}/dispatch`** (rejected): conflates two operations. The dispatch IS creating the event; there's no pre-existing event_id to dispatch.

---

## 3. Existing dispatch use cases — does tracker-priority pull cover them?

For each candidate dispatch use case, asking: under today's pull+tracker-priority mechanism, what happens? Does dispatch add real value over filing?

| Use case | Pull+tracker today | Does dispatch add value? |
|---|---|---|
| **Operator interrupt** ("skill, drop everything and do this URGENT bug NOW") | PM (or operator) files issue with `priority:high`; skill's next pull (~30 min worst case at default interval) picks it up first. | Dispatch reduces worst-case latency from 30 min to ~30 sec. **Real value: small.** The operator-interrupt use case is rare and almost never sub-minute-urgent (because URGENT in operator-interrupt usually means "in the next hour" not "in the next minute"). |
| **Cross-agent handoff** (DM merges → wants QA to verify immediately) | Tracker state transition (`pending-test`) is the handoff signal. QA's next pull picks it up. Worst case 30 min. | Same latency math. **Real value: nil.** Cross-agent handoffs don't have sub-cycle urgency; QA verifying within the next polling interval is fine. |
| **Stalled-agent rescue** (skill wedged on task X, route X to a different worker) | PM detects stall, transitions task X back to in-progress + reassigns `role:` label OR files a new task. | Same. The wedged-agent problem isn't a dispatch problem; it's a rescue-routing problem solved at the tracker level. **Real value: nil.** |
| **Event-driven follow-up** (external contributor comment on Issue → wants targeted role response) | Comment lands; agent's `event_bus_reader.query()` surfaces a `tracker-comment` event in next cycle's `recent_events`; agent's domain logic decides whether to act. | Dispatch would push the work onto a specific role rather than letting the role's own logic decide. **Real value: negative** — it bypasses the agent's own routing intelligence. |
| **Multi-step PM-driven coordination** (PM picks Task → wants skill to do Step 1, then triggers Step 2 only after Step 1's verification passes) | PM files Step 1 as approved task. Skill ships. QA verifies. PM observes verification, files Step 2. | Could dispatch Step 2 atomically on QA verification. **Real value: small** — eliminates one PM cycle of latency between Step 1 verify and Step 2 file. But adds harness-coupling to PM's workflow. |

**Net read**: the operator-interrupt use case is the only one with a measurable benefit, and the benefit is reducing 30-min latency to ~30-sec. That latency reduction matters in maybe 1 of 100 task filings. The other 4 use cases are dispatch-neutral or dispatch-negative.

The dispatch infrastructure was built assuming many of these use cases would warrant it. In practice none of them have.

---

## 4. External evidence — git history and original intent

### 4.1 `cycle_pre.py --task` flag (#8701)

**Introduced**: commit `e1aec7877` — "feat: #8701 cycle_pre/post task-level refactor for event-driven mode."

**Issue #8701** ([closed 2026-05-18T11:02:04Z](https://github.com/WallyDoodlez/SquidSquad/issues/8701)) titled "TASK: cycle_pre / cycle_post task-level refactor for event-driven mode." Issue body framing: "Phase 1 of event-driven mode — separates the task-discovery responsibility from the work-doing responsibility so a future harness dispatcher can pass a pre-selected task to cycle_pre."

**Status of follow-up**: the harness dispatcher referenced in the issue body was Phase 4 of the larger #7630 epic.

### 4.2 `EventLifecycleManager.dispatch()` (#7630)

**Introduced**: commit `52d55e7ab` — "skill: #7630 — Event-driven agent architecture (Phase 4 complete)."

**Issue #7630** ([closed 2026-05-17T16:29:27Z](https://github.com/WallyDoodlez/SquidSquad/issues/7630)) titled "TASK: EPIC: Event-driven agent architecture — harness owns cycle, agents react to events." Phase 4 in the EPIC's phasing was "harness owns task dispatch."

**Comment in the code** (`harness.py:926-927`): "Not yet wired into POST /events — Phase 4 plumbing. Currently dormant; will be activated when event-driven mode replaces the loop."

The comment is a clear deferral signal, not an abandonment signal. The infrastructure was checked in deliberately with the wiring left for a follow-up.

### 4.3 `EVENT_REQUIRED_FIELDS` (#8918)

**Introduced**: commit `dcbccfd25` — "fix: #8918 mode-gate REQUIRED_FIELDS + remove _advance_event_cursor (#8701 gaps)."

**Issue #8918** ([closed 2026-05-18T14:33:16Z](https://github.com/WallyDoodlez/SquidSquad/issues/8918)) titled "ISSUE: cycle_post.py missing Gap 2 (mode-gated REQUIRED_FIELDS) + Gap 3 (_advance_event_cursor removal) from #8701 lock." This was a follow-up gap-fix on the #8701 work — making `task` mandatory in event mode was deliberate, not accidental.

### 4.4 Why the wiring never landed

Reading the history forward: #7630 closed 2026-05-17 with "Phase 4 complete" but explicitly carrying the dispatch-wiring deferral comment. #8701 closed 2026-05-18 with the cycle_pre `--task` flag in place. #8918 closed 2026-05-18 with the EVENT_REQUIRED_FIELDS gap-fix. **From 2026-05-18 forward, no commit touches `EventLifecycleManager.dispatch()`** (re-confirmed by `git log -S "def dispatch" -- references/scripts/harness.py`).

The unstated reason the wiring stalled is in the EPIC's own framing: "harness owns cycle, agents react to events." This is the event-driven model. In practice, every install has stayed in polling mode (per the BRIEFING.md and operational pattern), so the event-driven model — and the dispatch endpoint it would have needed — has never been operationally required. The infrastructure outlives the use case that motivated it.

### 4.5 Implication for the design call

The dispatch infrastructure was never abandoned, just unmotivated. Pull-only is not "deciding the dispatch model was wrong" — it's "deciding the dispatch model is not currently needed enough to justify the surface area." If a future install drives event-driven mode hard enough to need targeted dispatch (e.g., a high-concurrency multi-team install where 30-min pull latency is unacceptable), the infrastructure is still in the git history and can be re-wired in a one-cycle skill task.

---

## 5. Failure-mode comparison

### 5.1 Pull-only failure surfaces

| Failure | Detection | Recovery |
|---|---|---|
| Tracker unreachable during pull | `tracker.py check-gh` exits non-zero | Cycle skips tracker query; retries next cycle |
| Pull returns stale priority order | Agent claims older task while higher-priority task exists | Self-corrects on next pull (~30 min worst case) |
| Race on claim (two agents claim same task simultaneously) | Tracker label transition is atomic — only one transition succeeds | Loser sees the transition fail, picks next task on its pull |
| Event-bus unreachable during pull | `event_bus_reader.query()` returns empty list | Agent loses cross-awareness for this cycle; recovers when bus returns |
| Agent pulls but doesn't act (wedged mid-decision) | PM stall sentinel observes mtime > threshold | PM restarts agent |

**Net**: 5 failure modes, all with bounded recovery latency. No silent-data-loss paths.

### 5.2 Pull+dispatch failure surfaces

All of the pull-only failure modes apply (the pull path is the same), plus:

| Failure | Detection | Recovery |
|---|---|---|
| Dispatch endpoint unreachable when caller fires | HTTP 5xx / connection refused | Caller retries with same `idempotency_key`; may fall back to tracker filing |
| Dispatch routes to wedged agent | Event lands in `_in_flight` but agent never pulls or never `complete`s | Timeout scanner re-dispatches per `EventLifecycleManager.DEFAULT_TIMEOUT_MINUTES = 10` |
| Dispatch + tracker priority race (described in §2.4) | cycle_pre sees both an `_in_flight` event and a tracker `priority:high` task | Tie-break needed; if not coded carefully, double-claim |
| Double-claim across dispatch idempotency window | Caller fires same dispatch twice in quick succession | `idempotency_key` check rejects with HTTP 409 |
| Endpoint-down-but-tracker-up split-brain | Dispatch endpoint unreachable but tracker still works | Caller falls back to tracker filing; agent picks up on next pull; effectively pull-only for this dispatch |
| `_in_flight` state corruption (disk write fails mid-persist) | `_persist()` raises; harness restart loses state | `_in_flight` rebuilt from event-bus on restart; some events may double-deliver |
| Cross-clone state divergence (multiple `.harness-state.json` files become inconsistent) | Operator runs harness in multiple clones simultaneously | Confusing dispatch behaviour; not solved by either model — orthogonal failure |

**Net**: 7 additional failure modes (5 pull + 7 dispatch = 12 total). The dispatch path roughly doubles the failure surface, mostly in race / split-brain regions that are hard to test for.

### 5.3 Asymmetry note

The pull-only failure modes are mostly recoverable-without-intervention (next cycle retries). The dispatch failure modes include several that need code-level mitigation (`idempotency_key`, timeout scanner re-dispatch, tie-break logic, persist atomicity). Even careful code is more complex than the pull-only equivalent.

---

## 6. Recommendation

**Pull-only.**

Three reasons consolidated:

1. **Tracker already does dispatch** for the only use case (operator interrupt) with measurable benefit, and the latency penalty (~30 min vs ~30 sec) is rarely binding in practice.
2. **Dispatch infrastructure was deliberately built and deliberately not wired** for ~3 weeks. The absence of operational pressure to complete the wiring is itself the strongest signal that pull-only is the right operating point.
3. **Failure surface roughly doubles** under pull+dispatch, with several new modes requiring careful concurrency reasoning. The architectural simplicity of pull-only is a load-bearing virtue, not just a stylistic preference.

Reversibility: the dispatch infrastructure code (`EventLifecycleManager.dispatch()`, `cycle_pre --task`, `EVENT_REQUIRED_FIELDS`) is in git history. If a future install hits operational pressure that pull cannot satisfy, re-wiring is a one-cycle skill task. The cost of going pull-only now and re-wiring later if needed is small; the cost of going pull+dispatch now and never using it is the carrying cost of the failure-surface complexity.

---

## 7. Phase 2 decisions to lock

Phase 2 (`CONTEXT-11092.md`) must lock the following:

1. **Pull-only OR pull+dispatch** — Phase 1 recommends pull-only.
2. **Disposition of `EventLifecycleManager.dispatch()`** — delete | deprecate | keep+wire. Phase 1 recommends delete (after operator confirmation), since deprecation without a deletion plan accumulates dead code over time.
3. **Disposition of `cycle_pre.py --task` flag** — delete | deprecate | keep+wire. Phase 1 recommends delete alongside `dispatch()`.
4. **Shape of `EVENT_REQUIRED_FIELDS`** post-resolution — under pull-only, collapse to `LOOP_REQUIRED_FIELDS` shape (`{"role", "cycle_number", "cycle_type"}`) and rename to `REQUIRED_FIELDS` (single constant, mode-agnostic).
5. **Quiet-cycle representation in event mode** — under pull-only with the collapsed REQUIRED_FIELDS, quiet cycles use `cycle_type: "quiet"` with no `task` field; same shape as polling-mode quiet cycles. No separate sentinel needed.

All five decisions need operator confirmation in Phase 2 before story breakdown.

---

## Status (cycle 2182, 2026-06-05)

- Phase 1 Research draft v1 committed at this path.
- Audit pending per #11092 protocol — runs after this draft is committed.
- Next: DS audit on this document, apply findings, then proceed to Phase 2 (CONTEXT-11092.md) with operator confirmation on the 5 locked decisions.

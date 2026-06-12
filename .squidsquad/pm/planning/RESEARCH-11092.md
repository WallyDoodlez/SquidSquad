# RESEARCH-11092 — Phase 1

PM Phase 1 deliverable for [#11092](https://github.com/WallyDoodlez/SquidSquad/issues/11092). Investigates the pull-only vs pull+dispatch design call for event-mode harness raised by QA's #11090 audit (Gaps 2+3).

**Headline finding**: the dispatch infrastructure was deliberately built and then deliberately not wired. The "Phase 4 plumbing" comment in `EventLifecycleManager.dispatch()` is a specific signal that work was queued, not abandoned — but the queue was never picked back up because every concrete workflow the dispatch infrastructure was supposed to enable can be satisfied by the existing pull+tracker-priority mechanism. The cost-benefit reads pull-only.

---

## 1. Pull-only architecture inventory

Walking every harness/agent interaction point that touches task/event flow under a pull-only model.

### 1.1 Agent-side pull surfaces

| Component | Path | Role under pull-only | Disposition |
|---|---|---|---|
| `tracker.py work_queue()` + `cycle_pre ROLE_BUILDERS` dispatch | `tracker.py:600` (priority-ordered pull) + `cycle_pre.py:1192, 1387` (per-role builder map) | The actual pull mechanism: `ROLE_BUILDERS[role](role)` calls into the role's builder, which calls `tracker.py work_queue()` to fetch tasks ordered `priority:high → medium → low`. | **Stays** — primary pull mechanism. |
| `event_bus_reader.query()` | `event_bus_reader.py:59` | Reads recent events from harness `/events` endpoint, filtered by `since` cursor + role + event_type. Surfaced as `recent_events` in cycle-input.json. | **Stays** — informational pull for cross-agent awareness (PR merges, status broadcasts, etc.). |
| `cycle_pre.py --task <N>` flag | `cycle_pre.py:1207-1218, 1326, 1379-1385` | Skips work-queue scan when harness has pre-selected a task; writes minimal `role_input = {"task": task_id, "task_mode": True}`. Originally added in #8701 (closed 2026-05-18) for event-driven mode targeted dispatch. | **Removed** — no caller wires through to it; tracker pull already does the same job. |
| `EVENT_REQUIRED_FIELDS` | `cycle_post.py:54-55` | Mode-gated validation enforcing `{"role", "task", "cycle_type"}` for event-driven `cycle-output.json`. Introduced by #8918 (closed 2026-05-18) as a gap fix for #8701. | **Loosened to `LOOP_REQUIRED_FIELDS` shape** — task becomes optional, quiet cycles representable. |
| `_get_role_wake_mode()` | `cycle_post.py:88, 155` | Reads `event-driven` / `event-driven-<role>:` from `config.md` to decide which REQUIRED_FIELDS to apply. | **Stays** — still needed for the broader event vs polling distinction; just no longer toggles the `task` requirement. |
| `tracker.py list-tasks` (priority order) | `tracker.py:77, 606` | Tracker query already orders by `priority:high → medium → low`. | **Stays** — this IS the dispatch mechanism under pull-only. |

### 1.2 Harness-side surfaces

| Surface | `harness.py` line | Role under pull-only | Disposition |
|---|---|---|---|
| `POST /events` | 1950 | Event publish (any actor — PM file, skill PR open, DM ship, etc.). | Stays — pull-only is silent on publish; agents still publish events for cross-awareness. |
| `GET /events` | 2088 | Read all events. | Stays — debugging surface. |
| `GET /events/for/{role}` | 2141 | Read events filtered to a role's interests. | Stays — primary subscription surface for agents. |
| `GET /events/cursor/{role}` | 2211 | Read per-role consumer cursor (last processed). | Stays. |
| `POST /events/{event_id}/complete` | 2232 | Ack event delivery. | Stays — required by pull subscription. |
| `GET /events/in-flight/{role}` | 2290 | Diagnostic. | Stays but handler modified — must drop the `get_in_flight()` call; either returns empty list or endpoint is removed entirely. Phase 2 picks. |
| `GET /events/lifecycle` | 2429 | Diagnostic. | Stays. |
| `POST /agents/{role}/start | stop | restart` | 1756, 2448, 2471 | Agent lifecycle control. | Stays. |
| `EventLifecycleManager.dispatch()` | 923-939 | In-flight tracking for events dispatched to a role. **Already dormant** — comment line 926-927: "Not yet wired into POST /events — Phase 4 plumbing." Per §4.6 below, the ONE call site that existed (`GET /events/for/{role}`) was stripped by #9741, so today there is no caller in the codebase. | **Removed** — but see the consumer-disposition list below; removal cascades to dependent endpoints + state. |
| `_in_flight` / `_dispatched` / `_dispatch_times` / `_retry_counts` state | 904-908 | Backing state for the dispatch lifecycle. **Currently dead in `dispatch()` direction but still read by live consumers** — see consumer-disposition table below. | Removal must cascade to consumers; otherwise live endpoints AttributeError. |
| `EventLifecycleManager.ack()` | 941-953 | Reads `_in_flight`, `_dispatched`, `_dispatch_times`, `_retry_counts`. Called by `POST /events/{event_id}/complete` (harness.py:2255). | **Endpoint becomes always-410 (Gone)** under pull-only; `ack()` is removed alongside the state. The complete-endpoint loses its semantic purpose because there's nothing in-flight to ack. |
| `EventLifecycleManager.get_in_flight()` | 955-958 | Reads `_in_flight`. Called by `GET /events/in-flight/{role}` (harness.py:2294) and `GET /events/lifecycle` (harness.py:2436). | **Endpoints lose the `in_flight` field** but stay (other diagnostics survive in `/events/lifecycle`); `get_in_flight()` is removed with the state. |
| `_timeout_scanner` (background thread) | started at harness.py:1404, iterates `_in_flight` at line 1135 | Re-dispatches events whose ack hasn't arrived within `_timeout_minutes = 10`. | **Removed** alongside the state — nothing in-flight, nothing to scan. |
| `_persist()` / `_load()` (state file I/O) | `_persist()` defined at 1034; `_load()` defined at 1060; four-field serialization at 1045-1048; deserialization at 1100-1107 | Serialize and deserialize all four fields to `.event-state.json`. | **Loses the four fields** but stays for the cursor field (`_cursors`), which is still load-bearing for `GET /events/cursor/{role}`. |

### 1.3 Net effect of pull-only adoption

- **0 new endpoints.** Harness HTTP surface narrows by 0 routes; one endpoint changes semantics (`POST /events/{event_id}/complete` → always-410).
- **6 code deletions** (cascading from `dispatch()` removal): `cycle_pre.py --task` flag (+ its `_parse_args` task branch + `role_input` task-mode branch), `cycle_post.py EVENT_REQUIRED_FIELDS` constant, `EventLifecycleManager.dispatch()` method, `EventLifecycleManager.ack()` method, `_in_flight`/`_dispatched`/`_dispatch_times`/`_retry_counts` state + their `_persist()`/`_load()` slots, `_timeout_scanner` background thread (+ thread-startup at harness.py:1404), `GET /events/in-flight/{role}` endpoint entirely OR strip its in-flight field, `GET /events/lifecycle` strip in-flight field.
- **1 code loosening**: `cycle_post.py` validation collapses to a single mode-agnostic `REQUIRED_FIELDS = {"role", "cycle_number", "cycle_type"}` — `LOOP_REQUIRED_FIELDS` and `EVENT_REQUIRED_FIELDS` merge.
- **1 endpoint semantic change**: `POST /events/{event_id}/complete` becomes always-410. Keep the route shell for backward compatibility (callers that fire it get a clean error) but document it as removed.
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

Reading the history forward: #7630 closed 2026-05-17 with "Phase 4 complete" but explicitly carrying the dispatch-wiring deferral comment. #8701 closed 2026-05-18 with the cycle_pre `--task` flag in place. #8918 closed 2026-05-18 with the EVENT_REQUIRED_FIELDS gap-fix. The `EventLifecycleManager.dispatch()` *method definition* has not been touched since 2026-05-17 (confirmed by `git log -S "def dispatch" -- references/scripts/harness.py`). But the dispatch *mechanism* as a functional system was actively dismantled in late May — see §4.6.

The unstated reason the wiring stalled is in the EPIC's own framing: "harness owns cycle, agents react to events." This is the event-driven model. In practice, every install has stayed in polling mode (per the BRIEFING.md and operational pattern), so the event-driven model — and the dispatch endpoint it would have needed — has never been operationally required.

### 4.5 Implication for the design call

The dispatch infrastructure was never abandoned via deletion, but #9741 + #9813 below show the codebase made an operational pull-only decision in late May. Pull-only is not "deciding the dispatch model was wrong" — it's "ratifying a decision the codebase already made operationally, by removing the dead method definitions and dependent state." If a future install drives event-driven mode hard enough to need targeted dispatch, the infrastructure shape is documented in git history (#7630 P4) and can be re-built; restoration would not be a one-cycle skill task because the call site at `GET /events/for/{role}` would need to be rewritten too.

### 4.6 The unwinding — #9741 and #9813 (the missing chapter)

After #7630 / #8701 / #8918 landed the dispatch infrastructure (mid-May 2026), two follow-up issues partially un-wired it within a week:

**#9741** ([closed 2026-05-21T10:40:05Z](https://github.com/WallyDoodlez/SquidSquad/issues/9741)) — "GET /events/for/{role} dispatches in-flight events but agents never ack — log spam plus state file growth." The dispatch infrastructure HAD been wired — `GET /events/for/{role}` called `event_lifecycle.dispatch()` on every read. But because no agent ever called `POST /events/{event_id}/complete` to ack, the `_in_flight` map and the persisted `.event-state.json` grew unboundedly, producing log spam and state-file bloat. The fix: strip the `dispatch()` call from `GET /events/for/{role}`. After #9741, `dispatch()` exists but has no call site in the harness. The endpoint became a pure filtered-read.

Confirmed in current code:
- `references/scripts/harness.py:2195-2197`: `"# #9741: dispatch() call stripped — endpoint is a pure filtered-read with no lifecycle side effects. The agent-side ack (event_bus.ack) was also removed in #9813 since it had no live..."`
- `references/scripts/harness.py:2016-2017`: `"in-flight tracker is dead code since #9741 stripped dispatch()."`

**#9813** ([closed 2026-05-21T11:40:35Z](https://github.com/WallyDoodlez/SquidSquad/issues/9813)) — "event_bus.ack() is a dead stub — Phase 4 wiring follow-up (#9741)." The agent-side counterpart to #9741: the agent's `event_bus.ack()` stub was removed because there was nothing to ack against post-#9741.

**Reading the timeline corrected**:
- 2026-05-17 (#7630 P4 complete): infrastructure shipped, partially wired (GET /events/for/{role} called dispatch()), POST /events/{event_id}/complete endpoint present.
- 2026-05-18 (#8701): `cycle_pre --task` flag added (anticipating a future dispatch endpoint).
- 2026-05-18 (#8918): `EVENT_REQUIRED_FIELDS` gap-fix.
- 2026-05-21 (#9741 + #9813): operational pressure (log spam, state growth) forced the un-wiring. The dispatch call site was stripped; the agent-side ack stub was removed. **This is the codebase already deciding pull-only at the operational level.**
- 2026-05-21 → today: the method definitions persist as dead code; nothing has tried to re-wire them.

The "Phase 4 plumbing" comment at `harness.py:926-927` is technically still true — `dispatch()` was never *fully* wired into POST /events — but it understates what happened. A partial wiring existed and was *removed*. This significantly weakens any argument for keeping the infrastructure for "future re-activation."

### 4.7 Net evidence for the design call

- The codebase already runs pull-only operationally — #9741 stripped the only call site of `dispatch()`; #9813 removed the agent-side ack stub.
- The dead-method-definitions (`dispatch()`, persisted in-flight state, timeout scanner) exist as carrying cost without operational benefit.
- Re-activating the dispatch model would require not just adding a new HTTP endpoint, but also restoring a call site in `GET /events/for/{role}` (undone by #9741) and re-introducing the agent-side ack (undone by #9813). The reversibility argument is weaker than the original §4.5 framing implied.

### 4.8 Commit-SHA verification

The SHAs cited in §§4.1-4.3 (`e1aec7877`, `52d55e7ab`, `dcbccfd25`) come from `git log --oneline` queries run during this draft. To make the evidence self-contained for any reviewer without git access, the verbatim commit messages are:

- `e1aec7877 feat: #8701 cycle_pre/post task-level refactor for event-driven mode (#8868)`
- `52d55e7ab skill: #7630 — Event-driven agent architecture (Phase 4 complete) (#8620)`
- `dcbccfd25 fix: #8918 mode-gate REQUIRED_FIELDS + remove _advance_event_cursor (#8701 gaps) (#8952)`

A reviewer in a checkout can re-confirm with `git log --oneline | grep <sha>`.

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

Four reasons consolidated:

1. **The codebase already runs pull-only operationally.** #9741 stripped the only `dispatch()` call site (May 21); #9813 removed the agent-side ack stub (May 21). The decision was effectively made by the squad in late May under operational pressure (log spam, state-file growth); this design call ratifies and completes it by also removing the dead-method definitions and dependent state.
2. **Tracker already does dispatch** for the only use case (operator interrupt) with measurable benefit, and the latency penalty (~30 min vs ~30 sec) is rarely binding in practice. The other four candidate use cases are dispatch-neutral or dispatch-negative.
3. **Dispatch infrastructure was built, partially wired, and then un-wired** within four days, and has been dead code for three weeks since. The absence of operational pressure to re-wire is the strongest evidence that pull-only is the operating point the squad has chosen.
4. **Failure surface roughly doubles** under pull+dispatch (5 modes → 12), with several new modes requiring careful concurrency reasoning (`idempotency_key`, tie-break logic, timeout-scanner re-dispatch, persist atomicity, cross-clone divergence). The architectural simplicity of pull-only is a load-bearing virtue, not just a stylistic preference.

Reversibility: the dispatch *shape* is documented in git history (#7630 P4 + #9741 + #9813), so if a future install drives operational pressure that pull cannot satisfy, the infrastructure can be re-built. But contrary to the original Phase 1 draft framing, restoration is NOT a one-cycle skill task — it requires the new HTTP endpoint AND restoring the stripped call site at `GET /events/for/{role}` AND re-introducing the agent-side ack. The carrying cost of keeping the dead method definitions in place "just in case" is higher than the marginal cost of re-creation if needed.

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

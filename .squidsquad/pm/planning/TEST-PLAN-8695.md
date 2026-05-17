# TEST-PLAN-8695 — `bootup-complete` Event (Informational Only)

**Issue**: #8695 — TASK: agent emits bootup-complete event, harness gates dispatch on it
**Bundle**: Phase 5 event-driven architecture (#8694 lead / #8695 / #8697 / #8700 / #8701 / #8704)
**Scope source**: `.squidsquad/pm/planning/CONTEXT.md` §5.2
**Date**: 2026-05-17

---

## Scope Reconciliation Note

The original Issue #8695 body asks for **dispatch gating** ("Harness must NOT dispatch any
assigned-to or status-transition events to an agent before receiving its bootup-complete"
and "queued-but-not-dispatched events during boot window, then bulk dispatch after
bootup-complete received").

Phase 2 planning (CONTEXT.md §2 thin-harness lock, §5.2 deliverables, glossary entry for
`bootup-complete event`) has **explicitly removed dispatch gating** in favor of an
**informational-only flag**. The harness remains a pure broadcast pipe; per-role event
holding, queuing, and `_pending_dispatch[role]` are out of scope.

This test plan tests the **informational-only** delivery. Negative tests in §5 actively
enforce the thin-harness property — they fail if any dispatch-gating implementation
sneaks back in.

---

## 1. Acceptance Criteria

Derived from CONTEXT.md §5.2 + glossary entries for `bootup-complete event` and
`listener_active`.

**AC-1 — Event registered as emitted**
`event_catalog.py` lists `bootup-complete` in the **EMITTED** tier with source
`"agent boot"` and `payload_fields: ["listener_active"]`.

**AC-2 — Payload shape**
The `bootup-complete` event payload is exactly `{"listener_active": <bool>}`. No
other fields are required. `listener_active` replaces the older Monitor-specific
`monitor_active` field per the F9 resolution.

**AC-3 — `AgentState.bootup_complete` field defaults False**
A freshly constructed `AgentState(role)` exposes `bootup_complete = False`. Listed
in `__slots__` and set in `__init__`.

**AC-4 — Reset on each spawn**
`bootup_complete` is reset to `False` on every fresh spawn lifecycle event:
`start_agent` (`harness.py:661`), `_deferred_init` auto-start (`harness.py:463`),
and when `update_health` (`harness.py:155`) observes a PID change.

**AC-5 — Flag flips on `POST /events` with `bootup-complete`**
When `POST /events` receives `{"event_type": "bootup-complete", "role": "<R>", ...}`,
`_update_agent_from_event` (`harness.py:750`) sets the originating role's
`AgentState.bootup_complete = True`. No other roles are affected.

**AC-6 — Field exposed via `GET /agents/{role}`**
`AgentState.to_dict()` (`harness.py:101`) includes `"bootup_complete": <bool>`.
The existing `GET /agents/{role}` endpoint (`harness.py:649`) returns it without
needing endpoint changes.

**AC-7 — Re-emission idempotency**
A second `bootup-complete` event from the same role (e.g. after agent restart
+ re-emit) is accepted and leaves the flag `True`. No error raised; no second
state machine.

**AC-8 — Thin-harness property preserved (NEGATIVE)**
Receiving `bootup-complete`:
- Does NOT cause the harness to emit any outbound event.
- Does NOT alter the deque of stored events visible via `GET /events`.
- Does NOT introduce any `_pending_dispatch`, per-role queue, or hold buffer.
- Does NOT cause any event arriving *before* it to be specially flushed,
  delivered, or replayed after the flag flips.

---

## 2. Test Categories Map

| Acceptance Criterion | Test Category | Section |
| -------------------- | ------------- | ------- |
| AC-1                 | Unit          | §3      |
| AC-2                 | Unit          | §3      |
| AC-3                 | Unit          | §3      |
| AC-4                 | Unit          | §3      |
| AC-5                 | Unit          | §3      |
| AC-6                 | Integration   | §4      |
| AC-7                 | Integration   | §4      |
| AC-8                 | Negative      | §5      |
| All                  | Manual smoke  | §6      |

---

## 3. Unit Tests

Target file: `tests/test_bootup_complete_event.py` (new).

### TC-U1: `event_catalog.py` registers `bootup-complete` in EMITTED tier
- **Precondition**: `event_catalog.py` updated per CONTEXT.md §5.2 deliverables.
- **Steps**: Import `EMITTED` and `RECOGNIZED`. Read entry for `bootup-complete`.
- **Expected**:
  - `"bootup-complete" in EMITTED`.
  - `EMITTED["bootup-complete"]["source"] == "agent boot"`.
  - `EMITTED["bootup-complete"]["payload_fields"] == ["listener_active"]`.
  - `"bootup-complete" not in RECOGNIZED` (it is emitted, not just recognized).
  - `get_tier("bootup-complete") == "emitted"`.
- **Verification**: `python -m pytest tests/test_bootup_complete_event.py::test_catalog_registration`

### TC-U2: `event_catalog validate` CLI accepts `bootup-complete`
- **Precondition**: TC-U1 passes.
- **Steps**: Run `python references/scripts/event_catalog.py validate bootup-complete`.
- **Expected**: Exit code `0`, stdout includes `VALID: 'bootup-complete' (tier: emitted)`.
- **Verification**: subprocess assertion in test.

### TC-U3: `AgentState.bootup_complete` defaults False
- **Precondition**: `harness.py` updated per CONTEXT.md §5.2.
- **Steps**: Import `AgentState` from `harness.py`. Construct `AgentState("skill")`.
- **Expected**:
  - `agent.bootup_complete is False`.
  - `"bootup_complete" in AgentState.__slots__`.
- **Verification**: `pytest tests/test_bootup_complete_event.py::test_default_false`.

### TC-U4: `to_dict()` includes `bootup_complete`
- **Precondition**: TC-U3 passes.
- **Steps**: Construct `AgentState("skill")`, call `.to_dict()`.
- **Expected**: Returned dict contains key `"bootup_complete"` with value `False`.
- **Verification**: `assert d["bootup_complete"] is False`.

### TC-U5: `_update_agent_from_event` flips flag on `bootup-complete`
- **Precondition**: `harness.py:_update_agent_from_event` updated.
- **Steps**: Seed `state.agents["skill"] = AgentState("skill")` (`bootup_complete=False`).
  Call `_update_agent_from_event({"event_type": "bootup-complete", "role": "skill",
  "payload": {"listener_active": True}, "timestamp": "..."})`.
- **Expected**: `state.get_agent("skill").bootup_complete is True`.
- **Verification**: direct attribute assertion.

### TC-U6: Other event types do NOT flip the flag
- **Precondition**: `bootup_complete = False`.
- **Steps**: Call `_update_agent_from_event` with `event_type="cycle-start"`,
  `event_type="cycle-end"`, `event_type="phase-change"`, `event_type="git-pull"`.
- **Expected**: `bootup_complete` remains `False` for all of them.
- **Verification**: assert after each call.

### TC-U7: Spawn resets `bootup_complete` to False
- **Precondition**: Agent exists in state with `bootup_complete = True`.
- **Steps**:
  - Sub-case a: simulate `start_agent` path — assert post-call value is `False`.
  - Sub-case b: simulate `_deferred_init` auto-start path — same assertion.
  - Sub-case c: simulate `update_health` observing a new `claude_pid` (PID changed)
    while previous state had `bootup_complete=True` — assert post-update value is `False`.
- **Expected**: `bootup_complete` is `False` after each spawn-equivalent transition.
- **Verification**: monkeypatched `boot_remote.boot_agent` returning success; assert
  attribute after each path.
- **Rationale**: A restarted agent must re-prove it has finished boot. CONTEXT.md §5.2
  explicitly lists `start_agent`, `_deferred_init`, and PID change in `update_health`
  as reset points.

### TC-U8: Missing or wrong-typed `listener_active` payload field
- **Precondition**: `_update_agent_from_event` updated.
- **Steps**:
  - Sub-case a: payload missing entirely — call with `"payload": {}`.
  - Sub-case b: `listener_active` non-bool — `{"listener_active": "yes"}`.
- **Expected behavior** (informational-only design):
  - The harness **does not reject** the event (no 400). The flag still flips to
    `True` because the event type alone is the signal; `listener_active` is
    descriptive metadata.
  - A warning is logged (optional — implementer discretion) but no exception
    is raised.
- **Verification**: assert flag flipped and no exception raised. (If implementer
  chooses to enforce strict payload validation, document the choice in TC results
  and update this TC to assert the rejection path instead — both behaviors are
  acceptable per CONTEXT.md, which does not lock payload-strictness.)

---

## 4. Integration Tests

Target file: `tests/test_bootup_complete_integration.py` (new). Uses FastAPI
`TestClient` against `harness.py:app`.

### TC-I1: Full cycle — POST `/events` then GET `/agents/{role}` reflects flag
- **Precondition**: Harness app started via TestClient. Role `skill` configured.
- **Steps**:
  1. `GET /agents/skill` — assert `bootup_complete: false` (or agent absent).
  2. `POST /events` with body `{"event_type": "bootup-complete", "role": "skill",
     "payload": {"listener_active": true}, "timestamp": "2026-05-17T10:00:00Z"}`.
  3. `GET /agents/skill`.
- **Expected**: Step 3 response JSON contains `"bootup_complete": true`.
- **Verification**: assertion on response JSON.

### TC-I2: Per-role independence
- **Precondition**: Roles `skill` and `qa` both configured.
- **Steps**:
  1. POST `bootup-complete` with `role: "skill"`.
  2. `GET /agents/skill` → expect `bootup_complete: true`.
  3. `GET /agents/qa` → expect `bootup_complete: false`.
- **Expected**: Emitting from one role does not affect any other role's flag.
- **Verification**: assert both responses.

### TC-I3: Re-emission idempotency
- **Precondition**: TC-I1 has run; `skill` shows `bootup_complete: true`.
- **Steps**: POST a second `bootup-complete` for `role: "skill"` (simulating
  agent restart + re-emit).
- **Expected**:
  - POST returns 200 `{"status": "ok"}`.
  - Subsequent `GET /agents/skill` still shows `bootup_complete: true`.
  - No exception raised, no duplicate-error logged.
- **Verification**: assert HTTP 200 and final flag state.

### TC-I4: Flag survives across other events
- **Precondition**: `skill` has `bootup_complete: true`.
- **Steps**: POST a series of other events (`cycle-start`, `phase-change`,
  `cycle-end`) for `role: "skill"`, then `GET /agents/skill`.
- **Expected**: `bootup_complete` remains `true` (only spawn resets it; other
  events do not).
- **Verification**: final GET assertion.

### TC-I5: Spawn reset after agent restart (PID change)
- **Precondition**: `skill` has `bootup_complete: true`. Simulate the
  `update_health` path that detects a new `claude_pid` (PID changed).
- **Steps**: Monkeypatch `boot_remote._is_process_alive` and `_read_claude_pid`
  to return a new PID different from `agent.claude_pid`. Call
  `state.update_health()`. Then `GET /agents/skill`.
- **Expected**: `bootup_complete` is now `false` (reset on PID change per AC-4).
- **Verification**: GET assertion.

---

## 5. Negative Tests (CRITICAL — thin-harness property enforcement)

These tests **fail if** dispatch gating or queue logic creeps in. They are the
load-bearing verification that the original Issue #8695 body's "harness must NOT
dispatch ..." requirement has been correctly **inverted** into the informational
design.

Target file: `tests/test_bootup_complete_thin_harness.py` (new).

### TC-N1: No `_pending_dispatch` / per-role queue structure exists
- **Precondition**: Fresh harness import.
- **Steps**:
  1. Import `harness` module.
  2. Inspect `harness.state` (or `HarnessState`) attributes via `dir()` /
     `vars()`.
  3. Inspect `AgentState.__slots__`.
  4. `grep` the source of `harness.py` for `_pending_dispatch`, `pending_dispatch`,
     `dispatch_queue`, `event_hold`, `holding_buffer`.
- **Expected**:
  - No attribute on `HarnessState` or `AgentState` named `_pending_dispatch`,
    `pending_dispatch`, `dispatch_queue`, `event_hold`, `holding_buffer`, or
    any variant.
  - No matching identifier in `harness.py` source.
- **Verification**:
  ```
  import harness, inspect
  src = inspect.getsource(harness)
  for token in ("_pending_dispatch", "pending_dispatch", "dispatch_queue",
                "event_hold", "holding_buffer"):
      assert token not in src, f"Thin-harness violation: {token} found"
  ```

### TC-N2: Receiving `bootup-complete` emits NO outbound events
- **Precondition**: TestClient running. `len(event_stream)` recorded before POST.
- **Steps**:
  1. Record `pre_len = len(harness.event_stream)`.
  2. POST `bootup-complete`.
  3. Read `post_len = len(harness.event_stream)`.
- **Expected**: `post_len == pre_len + 1` (only the inbound event itself was
  appended). The harness did not generate any additional dispatch / wake /
  acknowledgement event in response.
- **Verification**: deque length assertion.

### TC-N3: Events arriving BEFORE `bootup-complete` are NOT held
- **Precondition**: TestClient running, no events posted yet, agent
  `bootup_complete=False`.
- **Steps**:
  1. POST `cycle-start` for `role: "skill"` (this is an event that the harness
     should broadcast freely).
  2. `GET /events?role=skill` immediately.
  3. POST `bootup-complete` for `role: "skill"`.
  4. `GET /events?role=skill` again.
- **Expected**:
  - Step 2 returns the `cycle-start` event in the visible stream (proves it was
    NOT held pending boot).
  - Step 4 returns the same `cycle-start` event plus the `bootup-complete`
    event — neither duplicated nor replayed.
- **Verification**: count and event-type assertion on `GET /events` responses.

### TC-N4: Events arriving AFTER `bootup-complete` are NOT specially flushed
- **Precondition**: `bootup_complete: true` for `skill`.
- **Steps**:
  1. Record `pre_len = len(event_stream)`.
  2. POST `cycle-start` for `role: "skill"`.
  3. Read `post_len = len(event_stream)`.
- **Expected**: `post_len == pre_len + 1`. The flip of `bootup_complete` did
  **not** trigger replay of any earlier events nor a synthetic "flush" event.
- **Verification**: deque length assertion + `GET /events?since=<pre_id>` returns
  exactly one event.

### TC-N5: No tracker observation / no `assigned-to` synthesis
- **Precondition**: Harness running with no agent emitting `assigned-to`-style
  events.
- **Steps**:
  1. POST `bootup-complete` for `role: "skill"`.
  2. Wait briefly (or call `state.update_health()` once).
  3. `GET /events`.
- **Expected**: No event of type `assigned-to`, `dispatch`, `wake`, or
  `flush-pending` appears in the stream. The harness does NOT consult
  `tracker.py` in response to `bootup-complete`.
- **Verification**: scan event types in response; assert none in the forbidden
  set.

### TC-N6: No source contains dispatch-gating instruction comments
- **Precondition**: Source tree present.
- **Steps**: grep `harness.py` and `event_catalog.py` for phrases that would
  indicate gating: `"queue.*until.*bootup"`, `"hold.*event"`, `"dispatch.*gate"`,
  `"before.*bootup-complete"`.
- **Expected**: No matches.
- **Verification**: regex assertion. (Soft sentinel — if a future implementer
  tries to reintroduce gating they will see the test fail.)

### TC-N7: `bootup_complete: false` does NOT suppress `GET /events`
- **Precondition**: Agent `skill` has never emitted `bootup-complete`
  (flag is `false`).
- **Steps**: POST `cycle-start` events for role `skill`. Then call
  `GET /events?role=skill`.
- **Expected**: Events are returned normally. The flag does not control event
  visibility or delivery in either direction.
- **Verification**: response JSON contains the posted events.

---

## 6. Manual Smoke Tests

To be run by QA on a live harness:

- [ ] **S-1**: Boot harness in events mode. Verify `GET /agents/skill` initially
  returns `bootup_complete: false`.
- [ ] **S-2**: Boot skill agent. Confirm agent's boot sequence emits
  `POST /events` with `bootup-complete` and `listener_active: true` (visible in
  harness console log).
- [ ] **S-3**: After S-2, `curl http://localhost:<port>/agents/skill | jq
  .bootup_complete` returns `true`.
- [ ] **S-4**: Stop and restart the skill agent (`start_team.py --reboot skill`).
  Confirm `bootup_complete` is reset to `false` at restart, then flips back to
  `true` after the agent re-emits.
- [ ] **S-5**: With `bootup_complete: false`, post a synthetic `cycle-start`
  event for the role via `curl` and confirm it appears immediately in
  `GET /events` — i.e. no hold-until-boot semantics.
- [ ] **S-6**: Confirm `GET /status` aggregate response also reflects per-agent
  `bootup_complete` correctly (rides through `all_agents()` → `to_dict()`).

---

## 7. Gating Conditions

- **No hard prereq specific to #8695.** The only Phase 5 hard prereq is #8692
  (singleton enforcement) per CONTEXT.md §6.1, and that gate is on per-role
  `event-driven: yes` flips, not on shipping #8695 itself.
- **Co-ships with #8694**, which is the agent-side change that actually emits
  the `bootup-complete` event. #8695 can ship first (harness-side); operators
  will simply see `bootup_complete: false` everywhere until #8694 lands.
- **Standard gates**: plan-checker review, human approval of the planning PR
  (Phase 3B), QA test pass.

---

## 8. Post-Ship Validation

Verified after #8695 lands, when downstream Phase 5 tasks consume the flag:

- **PV-1 (#8700 status line)**: Status line / TUI reads `bootup_complete` via
  `GET /agents/{role}` or `GET /status` and renders an accurate boot indicator.
- **PV-2 (#8700 / #8704 TUI)**: When a role's `config.md` has `event-driven: yes`
  but `bootup_complete: false`, the TUI renders `events-mode, awaiting boot`
  (per CONTEXT.md §5.4 acceptance).
- **PV-3 (#8694 end-to-end)**: After #8694 ships, every successfully booted
  events-mode agent shows `bootup_complete: true` within one boot cycle of
  startup; restart cycles correctly flip the flag back to `false` then `true`.
- **PV-4 (operator soft signal)**: A role stuck at `bootup_complete: false`
  longer than the 5-minute boot-retry cap (CONTEXT.md §10 closing #6) is a
  soft signal to operators that harness/agent connectivity is degraded. No
  automatic action is taken — this is by design.

---

## 9. Comprehension Questions (CQ specs)

Per the project standard for tasks touching agent / harness contracts (memory
entry: "CQ specs required for agent steps"). #8695 touches harness behavior
but the agent-instruction surface is owned by #8694. A small CQ spec is still
useful to verify the flag's semantics are correctly understood downstream.

Target file: `tests/comprehension/8695_spec.json`.

### CQ-1: What does `bootup_complete: true` mean to the harness?
- **Files**: `references/scripts/harness.py`, `references/scripts/event_catalog.py`,
  CONTEXT.md §5.2 and glossary entries for `bootup-complete event` /
  `listener_active`.
- **Expected answer**: It is an informational flag indicating the named role
  has emitted a `bootup-complete` event at least once since its last spawn.
  The harness performs **no gating, queuing, or dispatching** based on this
  flag — it is for operator/TUI observability only.

### CQ-2: Does the harness queue events while `bootup_complete` is `false`?
- **Expected answer**: No. The harness is a pure broadcast pipe. Events are
  appended to the global `EventStream` and visible via `GET /events`
  immediately, regardless of any role's `bootup_complete` value.

### CQ-3: When is `bootup_complete` reset to `false`?
- **Expected answer**: On every fresh spawn of an agent: `start_agent`
  endpoint, the auto-start path in `_deferred_init`, and when `update_health`
  detects a `claude_pid` change indicating the agent process restarted.

### CQ-4: Why was the original "gate dispatch" framing dropped?
- **Expected answer**: It violated the locked thin-harness architecture
  (CONTEXT.md §2: "Thin harness, pure broadcast — harness is an event bus
  only. No tracker observation. No dispatch logic. No per-role queue
  knowledge."). Idempotency from the cursor + forge-read pattern makes a
  dispatch gate unnecessary — replaying events post-boot is safe because
  actions are computed from current forge state, not from the event payload.

---

## 10. Open Questions

1. **Payload strictness on `listener_active`** — CONTEXT.md §5.2 does not
   explicitly state whether the harness should reject `bootup-complete` events
   that lack the `listener_active` field or have it non-bool. TC-U8 above
   currently treats lenient handling as acceptable, with the implementer free
   to choose strict rejection. PM may want to lock this either way before QA
   sign-off; either interpretation is consistent with the thin-harness
   property since strictness does not introduce gating.
2. **Log line on `bootup-complete` receipt** — `_log_event` (`harness.py:773`)
   currently has explicit `elif` arms for each event type. Should
   `bootup-complete` get its own log detail string (e.g. `listener_active=true`)
   for operator visibility, or fall through to the default `detail=""`?
   Implementation detail, not blocking — flagging only.

If neither question is resolved before QA, the implementation may choose
defaults; QA can adjust expected log strings to match.

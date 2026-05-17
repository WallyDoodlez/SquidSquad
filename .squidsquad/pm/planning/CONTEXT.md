# Phase 5 Planning — Event-Driven Architecture CONTEXT

**Bundle**: #8694 (lead) / #8695 / #8697 / #8700 / #8701 / #8704
**Hard prereqs**: #8692 (singleton enforcement) + #4792 (harness sole-authority lifecycle) — both block any per-role flip
**Folded**: #8696 → #8694 (boot sequence is part of event-mode L1 base agent definition); #8699 → #8697 (event-driven-workflow source migration absorbed)
**Phase 6 cleanup**: #8698, #8702
**Process directive (active)**: #8703
**Date**: 2026-05-17
**Status**: Phase 2 complete — locked decisions captured for downstream test-plan authors

---

## 1. Executive Summary

SquidSquad is converting from a /loop + cycle_pre/cycle_post polling architecture
to a thin-event-bus architecture in which the harness is a pure broadcast pipe
and GitHub Issues ("the forge") is the canonical source of truth. Agents become
persistent sessions that react to a single global event stream, maintain a
"Last Processed Event ID" cursor in `working-state.md`, and re-read the forge
on every decision so events function purely as triggers — never as state.

The harness keeps zero tracker observation, zero dispatch logic, and zero
role-queue knowledge. Every agent sees every event; agents themselves run
`work_queue()` against the forge to decide whether an event is theirs. Idempotency
falls out naturally: replaying any event yields the correct action because the
action is computed from current forge state, not historical event payload.

Two completely separate L1–L3 fragment sets are composed (one for /loop, one
for events) with mode-agnostic L4 project instructions that have been audited
for /loop contamination. Neither L1–L3 set contains mode-conditional logic. The event-mode L1 base
agent definition includes a tracker-driven boot sequence as a failsafe that
survives a totally dead event bus. The `bootup-complete` event is **informational
only** — the harness exposes a `bootup_complete: bool` flag on `AgentState` via
`GET /agents/{role}` so operators/TUI can see boot status, but the harness does
no queuing or gating of any kind. The cycle_pre/cycle_post scripts switch from
time-cycle to task-cycle granularity when event-driven mode is active. The only
hard prerequisite is singleton enforcement (#8692); the orphaned
`event-driven-workflow` source migration is folded into #8697.

**Architectural principle**: all agent instructions live in CLAUDE.md composed
from L1–L4 layers. No instruction sources outside the compose stack. Data files
(working-state.md, config.md) are state/config that instructions reference, not
instructions themselves. Pre-flight human checklists live in planning docs, not
agent instructions.

---

## 2. Architecture Decisions (locked)

- **Thin harness, pure broadcast** — harness is an event bus only. No tracker
  observation. No dispatch logic. No per-role queue knowledge. Every event
  reaches every agent via one global stream. (Supersedes any "harness dispatches
  next work" framing in `RESEARCH-harness-events.md` §"Path to Dispatch-on-Handoff".)
- **Forge is source of truth** — GitHub Issues via `tracker.py` holds canonical
  state. Events are notifications/triggers only. Agents consult the forge on
  every decision. (`references/scripts/tracker.py` `work_queue()` lines 437–510
  encodes the canonical pickup ordering.)
- **Cursor + forge-read = idempotency** — each agent maintains
  `Last Processed Event ID` in `working-state.md`. Read event → forge-read
  referenced item → act on current forge state → advance cursor atomically.
  Replays are safe because action depends on present forge state, not payload.
- **Event payload = minimal pointer + event type** — issue/PR number + event
  type only. No full state in payload. Forge is the authority.
- **Cursor advancement = per-event, atomic** — write to `.tmp`, then `mv`.
  No batching. One write per processed event.
- **Atomicity rule** — every task (real tracker work AND improvement-scan
  tasks) runs to completion. Mid-task events are read and cursor-advanced
  but not acted on until the current task ends.
- **Idle == improvement-scan cool-down loop** — empty `work_queue()` → run
  improvement-scan as an atomic task → compute `Next scan after: <ts>` from
  config-supplied cooldown → write that timestamp to `working-state.md` →
  listen with timeout = remaining cool-down.
- **Cool-down default = 30 minutes universal across roles**, overridable
  per-role in `config.md`. The cool-down value is **read from `config.md` at
  scan-completion time** (not stored in working-state.md). Config changes
  take effect on the next scan boundary.
- **Cool-down storage** = `.squidsquad/<role>/working-state.md` under
  `## Improvement Scan` (fields: `Status: idle | running`, `Last completed: <ts>`,
  `Next scan after: <ts>`). The `Cool-down` value itself is NOT stored in
  working-state.md — it lives in `config.md`.
- **Improvement-scan crash recovery** — `Status: running` is written when a
  scan begins, `Status: idle` + `Last completed: <ts>` + `Next scan after: <ts>`
  on completion. On boot, if working-state shows `Status: running` for the
  improvement scan, the agent skips forge verification and restarts the scan.
  Improvement scans are **idempotent** — a fresh scan subsumes a partial one.
- **Comments are not standalone triggers** — most are informational.
  Comments are read by the *next agent picking up the work* when they
  interact with the issue.
- **DM exception for comments** — DM's task includes waiting for PR
  merges; comments may land during the wait. The "task" for a PR merge
  spans the full wait. DM re-reads issue comments **at task completion**
  (= end of PR-merge wait) before the next pickup. Comments arriving
  during the wait are honored when the wait ends. **There is no sub-loop
  during the wait.**
- **Urgent inter-agent signaling rides status transitions or labels** —
  not bare comments. Example: PM halting an in-progress agent transitions
  `in-progress → planning` (which IS an event).
- **HITL = role assignment to human** — no designer-loop special-casing.
  Designer is just another worker. Human handoff = transition to a
  `pending-human-*` status; any agent at any point.
- **`design:*` labels become metadata only** — retirement candidate in
  Phase 6 cleanup (see open questions).
- **Task-cycle replaces time-cycle in events mode** — `cycle_pre`/`cycle_post`
  run *per task*, not on a 30-minute tick. Task id + timestamp replaces
  cycle counter. No cross-agent health check in `cycle_pre` (harness owns
  liveness; agents don't poll each other).
- **Status line queries harness HTTP API** — separate-process delayed refresh loop (hard-coded 5s in v1),
  not file-tail. Tracked in #8700. Mode detection reads
  `event-driven: yes/no` from `.squidsquad/config.md` per role (same
  mechanism `compose.py` uses).
- **Two completely separate L1–L3 fragment sets, mode-agnostic L4** —
  one L1–L3 set per wake mode. No mode-conditional logic inside any
  L1–L3 fragment. L4 project instructions are shared across modes and
  audited for /loop contamination before any flip. `compose.py` picks
  one L1–L3 manifest + fragment set based on the role's
  `event-driven: yes/no` in `config.md`, then layers shared L4 on top.
  Failsafe isolation: Phase 6 cleanup deletes the /loop L1–L3 tree
  wholesale; L4 only needs the /loop-language audit removed.
- **L1 boot is part of event-mode's L1 base agent definition** —
  tracker-driven failsafe baked into the event-mode L1 base fragment,
  not a standalone fragment file. The boot path is forge-scan based and
  survives a total event-bus failure (the agent enters a retry loop and
  operates in degraded mode against the forge until the harness becomes
  reachable). Loop-mode boot remains the existing /loop tracker-driven
  pickup path.
- **`bootup-complete` event is informational only** — harness sets a
  per-role `bootup_complete: bool` flag on `AgentState`, exposed via
  `GET /agents/{role}`. **No queuing, no gating, no `_pending_dispatch`,
  no per-role event holding.** The harness remains a pure broadcast
  pipe. Operators and the TUI use the flag to know if an agent has
  finished its boot sequence.
- **Agent-side event-listening mechanism** — `references/scripts/event_poll.py`
  (new in #8694) reads the harness event stream from a cursor. The
  *instructions* to invoke it during normal operation are composed into
  the event-mode L1 base fragment per the L1–L4-only principle (no
  separate instruction file outside the compose stack).
- **Event stream gap behavior — three scenarios**:
  - **In-stream gap** (small missing range within the retained window):
    log warning, advance cursor past the gap, continue. Forge-read makes
    this safe.
  - **Long cursor lag (24h+)** — skim-then-advance for audit fidelity,
    not jump-to-latest.
  - **Eviction gap** (cursor predates oldest retained event in the
    `maxlen=1000` deque): `GET /events?since=<cursor>` returns no events
    at the cursor position because they've been evicted. Log eviction
    details (oldest available event id, count of evicted events).
    Advance cursor to the oldest-available event id and skim forward
    from there. Forge current state subsumes the lost information.

---

## 3. Workflow Specification (events mode)

### 3.1 Boot — L1 Failsafe (Case A; owned by #8694 as part of event-mode L1 base)

1. Read `.squidsquad/<role>/working-state.md` → cursor + in-progress task +
   improvement-scan `Status` field.
2. Branch on what working-state shows:
   - **In-progress tracker task** → verify against forge — still my role?
     still `status:in-progress`? Yes → resume. No → drop, scan.
   - **Improvement-scan `Status: running`** (not a tracker item) → skip
     forge verification; restart the scan. Improvement scans are
     idempotent — a fresh scan subsumes a partial one.
   - **Idle / nothing in progress** → run `work_queue()` against forge
     and either pick up the next item or fall into the improvement-scan
     cool-down loop.
3. Skim events from cursor forward (informational; forge already has
   current state). Skim-then-advance, never jump-to-latest. Handle gap
   scenarios per §2 (in-stream gap / long lag / eviction gap).
4. Advance cursor to latest event id.
5. **Check harness reachability**:
   - **Reachable** → emit `bootup-complete` event (POST `/events` with
     `event_type=bootup-complete`, `role=<role>`, payload
     `{"listener_active": true}`). Enter event-listening loop via
     `event_poll.py`.
   - **Unreachable** → operate in **degraded mode**: work directly from
     the forge using `work_queue()`. Retry `bootup-complete` emission
     with exponential backoff capped at 5 minutes. When the harness
     becomes reachable, emit `bootup-complete` and enter the listening
     loop. `bootup-complete` emission is **best-effort, not blocking**
     — the agent never hangs waiting for the harness.

### 3.2 Idle, event arrives (Case B)

1. Read event at cursor+1.
2. Forge-read the referenced item (if any) via `tracker.py`.
3. Run `work_queue(role)` against the forge — pick up if available,
   else stay idle (i.e. re-enter improvement-scan cool-down loop).
4. Advance cursor atomically.

### 3.3 After completing work (Case C)

1. Just transitioned tracker item via `tracker.py transition`.
2. Update `working-state.md` → task: none.
3. Immediately run `work_queue()` against forge — do NOT wait for own
   transition event to come back through the stream.
4. Pick up next item, or enter idle (improvement-scan cool-down).
5. Cursor advances naturally as new events flow.

(This replaces the original RESEARCH framing where the harness pushes
the next `assigned-to`.)

### 3.4 Mid-task, event arrives (Case D)

1. Read event at cursor+1.
2. Note but do NOT act — current task runs atomically to completion.
3. Advance cursor.
4. On task completion, re-scan forge — current forge state absorbs
   all mid-task events.

### 3.5 Special events (Case E)

- **`stop-requested`** — honored ONLY at task boundary. Mid-task: read,
  advance, ignore. At boundary: checkpoint `working-state.md`
  (preserve cursor), exit cleanly.
- **`bootup-complete` from another agent** — informational. Advance
  cursor. No action.
- **Unknown event type** — log warning. Advance cursor. Do not block.

### 3.6 Idle = improvement-scan cool-down loop

- When `work_queue()` returns empty → enter improvement-scan as an
  atomic task.
- On scan start: write `Status: running` to `working-state.md` under
  `## Improvement Scan`.
- On scan completion: read cool-down value from `config.md` (default
  30m), compute `Next scan after: <now + cooldown>`, and write under
  `## Improvement Scan`:
  ```
  Status: idle
  Last completed: <YYYY-MM-DD HH:MM>
  Next scan after: <YYYY-MM-DD HH:MM>
  ```
- Listen on event stream with timeout = remaining cool-down (= `Next scan
  after` − now).
- Timeout fires first → run next improvement-scan.
- Task-relevant event arrives during sleep → cancel wait, re-scan
  `work_queue()`.
- Event arrives during inflight scan → finish scan first (atomicity
  rule), then process.
- Default cool-down = **30m universal across roles**, configurable
  per role in `config.md` (no per-role overrides shipped initially).

### 3.7 Comment handling

- Comments are NOT standalone event triggers.
- Comments are absorbed by the next agent that picks up the issue.
- **DM exception**: DM re-reads issue comments **at task completion**
  before the next pickup. The "task" for a PR merge spans the full
  wait — comments arriving during the wait are honored when the wait
  ends. **No sub-loop during the wait.** Urgent reassignment / route-back
  / follow-up guidance via comments alone is therefore delayed until
  the wait completes; senders requiring faster reaction must ride a
  status transition or label change.
- Urgent agent-to-agent signaling MUST ride a status transition or
  label change. Bare comments will not wake anyone.

### 3.8 HITL (human-in-the-loop)

- No special designer-loop handling.
- Designer is a worker role with the same lifecycle as skill / qa / dm.
- HITL = transition the issue to a `pending-human-*` status. Any
  agent at any point may do this.
- `design:*` labels become metadata only (Phase 6 retirement candidate).
- Harness TUI surfaces human-assigned work prominently — see #8704.

---

## 4. Mode Separation Strategy

Today's deployed CLAUDE.md files contain BOTH the /loop cycle-runner
and a hand-injected `event-driven-workflow` block (commit `a3b108f2`),
and the agent self-selects based on `event-driven: yes/no` in config.md.
This is fragile: agents see contradictory instructions and the
event-driven block has no source — the next `compose.py deploy` wipes it.
(See `RESEARCH-compose-boot.md` §"Existing Mode-Gate Mechanism".)

Phase 5 replaces the runtime gate with a compose-time gate using two
fully separate fragment sets.

### 4.1 Two manifests per role

```
references/roles/<role>/includes-loop.yml      # /loop mode manifest
references/roles/<role>/includes-events.yml    # events mode manifest
```

### 4.2 Two fragment trees

```
references/sub-skills/common-loop/             # /loop-only shared fragments
references/sub-skills/common-events/           # events-only shared fragments
references/sub-skills/common/                  # truly shared (e.g. vault, soul)
references/sub-skills/roles/<role>/loop/       # /loop-only per-role fragments
references/sub-skills/roles/<role>/events/     # events-only per-role fragments
references/sub-skills/roles/<role>/            # truly shared per-role fragments
```

Exact directory naming (`common-loop` vs `common/loop/`, etc.) is
deferred to #8697 implementation. The decision is "completely separate
trees" — the naming convention is implementation discretion.

### 4.3 `compose.py` mode selection

- `compose.py deploy <role>` reads role's `event-driven: yes/no` from
  `.squidsquad/config.md` (mechanism already exists: see
  `_read_config_value()` referenced in `RESEARCH-compose-boot.md`).
- If `yes` → load `includes-events.yml` and render fragments from the
  events-mode tree only.
- If `no` (or absent) → load `includes-loop.yml` and render from the
  loop-mode tree only.
- NO mode-conditional logic inside any fragment. Fragments are pure;
  the manifest + tree pairing carries the mode.
- L4 project instructions (`.squidsquad/project/`) are mode-agnostic
  and continue to flow through the existing Layer 4 mechanism. **L4
  files must be audited for /loop-specific language before any per-role
  flip to events mode** — see §6 pre-flip checklist.

### 4.4 Phase 6 cleanup characteristic

Once every role has `event-driven: yes`, the /loop tree and
`includes-loop.yml` manifests are deleted wholesale. No conditionals
need to be picked apart from fragment bodies — that's the failsafe
isolation property. See #8698.

---

## 5. Per-Task Specifications

### 5.1 #8694 — Event-Mode L1 Base Agent Definition (lead)

**Scope**: The complete event-mode L1 base agent definition. Owns the
entire event-mode agent contract:

- **Boot sequence (Case A)** — tracker-driven failsafe, harness-reachability
  branching, exponential-backoff retry on harness unreachable, degraded-mode
  operation, eviction-gap handling.
- **All event reactions (Cases B–E)** — idle/event, after-completion,
  mid-task event, special events.
- **Cursor management** — atomic `.tmp` + `mv` advance per event.
- **Forge-read pattern** — every decision consults the forge before acting.
- **Idle = improvement-scan cool-down loop** — including `Status: running`
  crash-recovery semantics and `Next scan after` storage.
- **Comment handling rule** — including the DM end-of-task re-read exception.
- **Agent-side event-listening mechanism** — `event_poll.py` script
  (executable) plus the instructions to use it (composed into event-mode L1
  base, per L1–L4-only principle; no separate instruction file outside the
  compose stack).
- **Improvement-scan crash recovery** — `Status: running` field, fresh-scan
  idempotency.
- **Eviction-gap handling** — third gap scenario beyond in-stream gap and
  long lag.

The boot sequence is part of the event-mode L1 base fragment — there is **no
standalone `l1-boot.md` fragment file**. All agent instructions must live in
CLAUDE.md composed from L1–L4 layers (the locked architectural principle).

**Deliverables**:
- New executable script: `references/scripts/event_poll.py`.
  - Cursor-based polling of the harness event stream (`GET /events?since=<cursor>`).
  - Configurable wait/timeout.
  - Stdout JSON-lines streaming.
  - Retry on transient harness errors with exponential backoff using the
    **same 5-minute cap as the boot-time retry loop** (§3.1 step 5) for
    a single consistent retry policy across boot and runtime.
  - **Mid-operation harness failure is a manual-recovery scenario** —
    if the harness becomes unreachable AFTER `bootup-complete` has been
    emitted, the agent keeps retrying at the capped backoff but does
    NOT pivot to forge-direct work. The operator manually restarts the
    harness; the agent resumes via the event stream on reconnect.
    Rationale: agents log everything and report progress to the forge,
    so state is recoverable; adding a runtime degraded-mode adds
    complexity the failsafe boot path already handles after a restart.
- Content under `references/sub-skills/common-events/` and per-role
  `references/sub-skills/roles/<role>/events/` describing:
  - The event-mode L1 base agent definition (boot sequence + event
    reactions verbatim from §3).
  - Cursor format and atomic update protocol (write `.tmp`, `mv`).
  - Forge-read protocol.
  - Idle = improvement-scan cool-down loop with explicit `working-state.md`
    schema including `Status: idle | running`, `Last completed`, and
    `Next scan after` fields.
  - Comment-handling rule and DM end-of-task re-read exception (explicitly
    no sub-loop during the wait).
  - **Transition-on-handoff rule**: when an agent assigns work to a
    different role (including humans), the assignment MUST be a status
    transition so it appears on the event stream. Bare comments do not
    wake the recipient.
  - **How to invoke `event_poll.py`** as the agent's listening mechanism.
- Updates to per-role events fragments (skill / pm / qa / dm) for
  role-specific behavior on top of the common contract.

**Files touched (illustrative — final naming defers to #8697)**:
- `references/scripts/event_poll.py` (new)
- `references/sub-skills/common-events/l1-base.md` (new — contains the
  full event-mode L1 base agent definition including boot sequence)
- `references/sub-skills/common-events/cursor-management.md` (new)
- `references/sub-skills/common-events/forge-read-pattern.md` (new)
- `references/sub-skills/common-events/idle-cooldown-loop.md` (new)
- `references/sub-skills/common-events/comment-handling.md` (new)
- `references/sub-skills/roles/dm/events/pr-merge-wait.md` (new)
- `references/sub-skills/roles/pm/events/*.md` (per-role events)
- `references/sub-skills/roles/skill/events/*.md`
- `references/sub-skills/roles/qa/events/*.md`
- `references/roles/<role>/includes-events.yml` (manifest entries pointing
  at the above)

**Acceptance**:
- CQ spec (`tests/comprehension/8694_spec.json`) covers: how the agent
  reacts to a mid-task event; how the agent handles an unknown event;
  what fires when `work_queue()` returns empty; what DM does after a PR
  merges while it was waiting; what an agent does if a comment on its
  issue requests a route-back; what the agent does on boot when
  working-state shows an improvement-scan with `Status: running`.
- **Failsafe acceptance criterion**: "agent boots and works correctly
  with the harness fully down — completes forge scan, enters retry
  loop, operates in degraded mode against the forge directly, does
  not crash or hang."
- `event_poll.py` unit/integration tests cover cursor-based polling,
  timeout behavior, and retry on transient harness errors.
- Comprehension test passes with a fresh agent given only the new
  fragments.
- No mode-conditional language inside any fragment ("if event-driven
  is yes, ..." is banned in fragment bodies).
- No agent instructions live outside the L1–L4 compose stack. No
  standalone `l1-boot.md` fragment.
- Heavy instruction-design task — primary content surface for Phase 5.

---

### 5.2 #8695 — `bootup-complete` Event (Informational Only)

**Scope**: Minimal harness add. Define and recognize the
`bootup-complete` event from agents and expose a per-role
`bootup_complete: bool` flag on `AgentState`. **No dispatch gate,
no per-role queue, no event holding.** The harness remains a pure
broadcast pipe; this change is observability only.

**Deliverables**:
- `references/scripts/event_catalog.py`: add `bootup-complete` to
  the agent-emitted event list, source `"agent boot"`, payload_fields
  `["listener_active"]`.
- `references/scripts/harness.py`:
  - Add `bootup_complete: bool = False` to `AgentState.__slots__` and
    `__init__`.
  - Reset to `False` on each spawn (`start_agent`, `_deferred_init`,
    PID change in `update_health`).
  - In `_update_agent_from_event()` (~line 750): when
    `event_type == "bootup-complete"`, set `bootup_complete = True`.
    **No queue flushing. No `_pending_dispatch[role]`.**
  - `AgentState.to_dict()`: include `"bootup_complete": self.bootup_complete`.
- POST `/events` already accepts agent-originated events
  (`harness.py:827`). No endpoint change required.
- GET `/agents/{role}` already returns full `AgentState.to_dict()`.
  No endpoint change required — the new field rides through automatically.

**Files touched**:
- `references/scripts/event_catalog.py`
- `references/scripts/harness.py`

**Acceptance**:
- Unit test: spawning an agent resets `bootup_complete` to `False`.
- Unit test: posting a `bootup-complete` event flips the flag.
- Integration test: `GET /agents/{role}` returns `bootup_complete: true`
  after the role emits the event.
- Negative test: harness emits **no per-role dispatching of any kind**
  during the test (verify nothing is queued, held, or routed per-role).

**Note**: The bootup-complete event is informational only. Operators
and the TUI consume the flag to know if a role has finished its boot
sequence. There is no harness-side gating, queuing, or dispatching of
any events of any type.

---

### 5.3 #8697 — `compose.py` Dual-Mode (separate L1–L3 sets per wake mode, shared L4)

**Scope**: Code refactor. Establish the two-fragment-set architecture
described in §4. **Absorbs #8699** (event-driven-workflow source
migration) as a deliverable.

**Deliverables**:
- `references/scripts/compose.py`:
  - Read `event-driven: yes/no` from `.squidsquad/config.md` per role
    (use existing `_read_config_value()` mechanism).
  - Select manifest: `includes-events.yml` if events, else
    `includes-loop.yml`.
  - Backwards-compat shim: if a role has only `includes.yml` (no
    `-loop`/`-events` variant), keep using `includes.yml` and assume
    /loop. This shim is removed in Phase 6 (#8698).
  - No mode-conditional logic inside any fragment — fragments are
    physically separated.
- New directory layout (final naming determined here):
  ```
  references/sub-skills/common-loop/
  references/sub-skills/common-events/
  references/sub-skills/common/             (truly shared — vault, soul)
  references/sub-skills/roles/<role>/loop/
  references/sub-skills/roles/<role>/events/
  references/sub-skills/roles/<role>/       (truly shared per-role)
  ```
- Two manifests per role: `includes-loop.yml`, `includes-events.yml`.
- **Migration of `event-driven-workflow` block** (closes #8699): extract
  from currently hand-injected content in deployed CLAUDE.mds (line
  ranges per `RESEARCH-compose-boot.md`: PM 344–425, skill ~328–416,
  QA 344–425, DM 363–444) into real fragments under `common-events/`.
- Initial classification pass: for the four existing role manifests
  (PM 31 entries, others similar), classify each entry as `loop`,
  `events`, or `both`. "Both" entries appear in BOTH new manifests.
- **L4 audit (pre-flip checklist enforcement)**: audit all L4 project
  instruction files (`.squidsquad/project/pm-instructions.md`,
  `dev-instructions.md`, `shared-instructions.md`) for /loop-specific
  language. Remove or generalize cycle/loop references. Any L4 file
  that cannot be cleanly generalized must be split into mode-specific
  variants. Track this audit as a deliverable; it is also listed in §6
  as a pre-flip checklist item.

**Files touched**:
- `references/scripts/compose.py`
- New: `references/sub-skills/common-events/*.md` (event-driven-workflow
  migration source — closes #8699)
- New: `references/sub-skills/common-loop/*.md` (cycle-runner and
  /loop-only fragments)
- New: `references/roles/<role>/includes-events.yml` (4 files)
- Renamed: `references/roles/<role>/includes.yml` →
  `references/roles/<role>/includes-loop.yml` (4 files, kept until #8698)
- Edited: `.squidsquad/project/pm-instructions.md`,
  `dev-instructions.md`, `shared-instructions.md` (L4 audit results)
- Test: `tests/comprehension/8697_spec.json` (CQ for dual-mode
  composition).

**Acceptance**:
- `compose.py deploy <role>` with `event-driven: no` produces a
  CLAUDE.md containing only loop-mode fragments.
- `compose.py deploy <role>` with `event-driven: yes` produces a
  CLAUDE.md containing only events-mode fragments — no /loop language,
  no cycle-runner.
- No fragment file contains the string `event-driven:` as a runtime
  branch instruction. (Mode lives in the manifest, not the fragment.)
- Existing roles compose identically to today when `event-driven: no`
  (regression check against current deployed output).
- `event-driven-workflow` block is composed from a real source
  fragment, not hand-injected. #8699 closes here.
- L4 project instruction files contain no /loop-specific language, or
  are explicitly split into mode-specific variants.

---

### 5.4 #8700 — Status Line Refactor (harness HTTP API source)

**Scope**: Switch status line data source from local files to harness
HTTP API. Run its own delayed refresh loop. Renders as a panel within
the harness-served TUI (see §5.6).

**Deliverables**:
- Status line panel reads `GET /status` (or `GET /agents`) from
  the harness on a 2–5 second refresh loop.
- **Mode detection**: reads `event-driven: yes/no` from
  `.squidsquad/config.md` per role (same mechanism `compose.py` uses
  via `_read_config_value()`). Uses HTTP API rendering for
  `event-driven: yes` roles; falls back to file-based rendering for
  `event-driven: no` roles during the transition.
- **Edge case**: config says `yes` but no harness data for the role yet
  (e.g. the agent hasn't booted) → render `events-mode, awaiting boot`.
- Once #8698 ships and `/loop` mode is gone, remove the file-based path.
- Display fields per agent: current task id, phase / current state,
  `bootup_complete` flag, health.

**Files touched**:
- Status line script(s) (location per current codebase — likely a
  `statusline.py` or similar in `references/scripts/`).
- Possibly `harness.py` if a new aggregate endpoint is preferred over
  composing from `/agents` + per-agent calls.

**Acceptance**:
- Status line updates without scanning local agent files when the
  harness is reachable and a role's config is `event-driven: yes`.
- Status line falls back gracefully (file-based) when a role is still
  in /loop mode.
- Edge case: config `event-driven: yes` + no harness data renders
  `events-mode, awaiting boot`.
- Status line refresh does not impose a measurable CPU/API load
  (2–5s cadence).
- CQ spec deferred — primarily a code task, not instruction-design.

---

### 5.5 #8701 — `cycle_pre` / `cycle_post` Task-Level Refactor

**Scope**: Code refactor. In events mode, `cycle_pre.py` and
`cycle_post.py` become per-task operations rather than 30-minute ticks.

**Deliverables**:
- `cycle_pre.py`: dual-mode dispatch on role's `event-driven` flag.
  - **events mode**: per-task invocation. Inputs: task id. Behavior:
    git pull + build forge state *for this one task*. No 30-minute
    cadence assumption. No cross-agent health check (harness owns
    liveness).
  - **loop mode**: unchanged from today.
- `cycle_post.py`: dual-mode dispatch.
  - **events mode**: per-task. Behavior: commit + push *for this task's
    outputs*. Log keyed by `task_id + timestamp`. No cycle counter.
  - **loop mode**: unchanged.
- Logging: in events mode, iteration log file naming switches from
  `iter-N.md` to a task-keyed convention (`task-<id>-<ts>.md` or
  similar — implementation discretion).
- Remove cross-agent health check from `cycle_pre` in events mode
  (harness owns liveness).
- No-op safety: if invoked in events mode but no task id is supplied,
  exit cleanly with a clear error.

**Files touched**:
- `references/scripts/cycle_pre.py`
- `references/scripts/cycle_post.py`
- Possibly `references/scripts/cycle.py` (timestamp/keying helpers).
- Test additions in `tests/`.

**Acceptance**:
- Unit tests for both modes pass.
- A simulated events-mode task triggers exactly one
  `cycle_pre.py → work → cycle_post.py` cycle, with task-id keyed log.
- A /loop-mode invocation behaves identically to today.
- No `cycle_pre.py` invocation in events mode does cross-agent health
  polling.

---

### 5.6 #8704 — Harness TUI Surfaces Human-Assigned Work

**Scope**: New harness endpoint + TUI/UI panel for `pending-human-*`
items. Prominent surfacing (badge count, dedicated panel). Works for
any agent's pending-human transitions, not just designer. Renders as
a panel within the same harness-served TUI as #8700.

**Deliverables**:
- `references/scripts/harness.py`: new endpoint, e.g.
  `GET /human/queue`, returning all open issues with a
  `status:pending-human-*` label. Implementation: shell out to
  `tracker.py` or `gh issue list` with appropriate filters; cache
  briefly (5–10s) to avoid hammering the forge.
- TUI human-queue panel: reads `GET /human/queue` on a delayed refresh
  loop (matches #8700 cadence). Renders:
  - Badge count of pending-human-* items.
  - Dedicated panel listing items: number, title, role that
    transitioned to human, transition timestamp.
- HITL is role-agnostic — works for skill, qa, dm, designer, any role
  that emits a pending-human-* transition.

**Files touched**:
- `references/scripts/harness.py`
- TUI display script(s).
- Possibly `references/scripts/tracker.py` if a new query is needed.

**Acceptance**:
- `GET /human/queue` returns all `pending-human-*` items, regardless
  of role.
- TUI shows a non-zero badge when at least one item is pending-human.
- Designer-loop special-case code (if any exists today) is removed.

---

### 5.7 TUI / Status Surface Architecture (cross-cutting)

The status line (#8700) and the human-queue panel (#8704) are **panels
within the same harness-served TUI**. They share:

- The harness API base URL (resolved from `.squidsquad/.harness-port`).
- The refresh cadence (**hard-coded default 5 seconds, no config knob in v1**).
- The same display surface (one TUI process).

**TUI process model — locked:** the TUI runs as a **separate process**
consuming harness HTTP endpoints, NOT in-process inside `harness.py`.
"Harness-served" means "consumes harness HTTP API," not "runs inside
the harness process." This matches the existing `statusline.sh`
pattern (separate script invoked by Claude Code's statusline hook)
and gives fault isolation: a harness crash does not kill the TUI, and
a TUI crash does not kill the harness. The TUI is launched
independently by the operator (or by a thin launcher) and points at
the harness via the port file.

Single integration point. #8700 ships the status-line panel first;
#8704 adds the human-queue panel later. Both consume harness HTTP
endpoints; **neither reads agent-side files** (in events mode).

---

## 6. Hard Prerequisites

The hard prerequisites for any per-role flip of `event-driven: yes` are
**#8692 AND #4792 (rescoped)**. Both must ship before flipping any role.

### 6.1 #8692 — Singleton Enforcement at Agent Startup (BLOCKER)

Without singleton enforcement, two agents of the same role can race on
event handling — the same root-cause class as the `cycle_post`
pollution incident that triggered this whole planning effort
(`RESEARCH-harness-events.md` §"Related Bugs Filed"). In events mode
the failure mode is worse: both sessions process the same event,
duplicate forge actions, corrupt cursors.

**Plan in parallel; gate approval/execution of any per-role events flip
on #8692 being shipped first.**

### 6.2 #4792 — Harness Sole-Authority Lifecycle (BLOCKER)

The harness must be the SOLE gatekeeper of agent process lifecycle
before any role flips to event mode. Today's state is split-brain:
the harness has HTTP API endpoints (POST /agents/{role}/start|stop|restart,
POST /shutdown) but parallel control paths still exist via sentinel
files (`.stop`, `.stop-after-cycle`) referenced in 7 scripts (`harness.py`,
`boot_remote.py`, `health_check.py`, `cycle_pre.py`, `cycle_post.py`,
`start_team.py`, `reboot_agent.py`). A stale sentinel file silently
overrides harness intent — the same root cause as the "2 PMs in same
clone" incident from this session.

**Scope of #4792 (rescoped from "deprecate sentinel files" to
"harness sole-authority lifecycle"):**

- Remove ALL sentinel-file reads/writes from the 7 scripts
- All start/stop/restart operations go through the harness HTTP API
- `boot_remote.py` may continue as a helper invoked BY the harness
  internally, but is NOT an operator-facing entrypoint
- Wrapper scripts check harness PID before each task/cycle; dead PID
  triggers clean exit
- Remove agent-lifecycle sentinel docs from all role CLAUDE.md files
  (via the compose stack — fragment edits)

**Plan in parallel; gate per-role events flip on #4792 shipping.**

### 6.3 (#8699 — absorbed by #8697)

The `event-driven-workflow` block migration (formerly tracked as #8699)
is folded into #8697's scope. It is **not** a separate prerequisite. See
§5.3 deliverables — when #8697 ships, the canonical `event-driven-workflow`
fragment lives under `common-events/` and is composed normally; #8699
closes automatically.

### 6.4 Pre-Flip Checklist (per role)

Before flipping any role's `event-driven: yes` in `config.md`:

1. #8692 (singleton enforcement) is shipped.
2. #4792 (harness sole-authority lifecycle) is shipped — no sentinel
   files remain in any of the 7 scripts; harness API is the sole
   lifecycle control path; PID-based liveness verified.
3. #8697 (compose dual-mode) is shipped — events-mode tree exists for
   this role with no /loop residue in any fragment body.
4. L4 audit (under #8697) has confirmed no /loop-specific language
   remains in `.squidsquad/project/` files that apply to this role.
5. #8694 fragments (event-mode L1 base, including boot sequence and
   `event_poll.py`) are in place for this role.
6. #8695 (`bootup_complete` flag) is deployed so the TUI/operators can
   see boot status.
7. `compose.py deploy <role>` produces a CLAUDE.md with zero /loop
   language and the events-mode boot sequence at L1.

---

## 7. Phase 6 Cleanup (dormant — pending event-mode fully on)

These tasks sit at `status:pending` until **the PM, after reviewing
event-driven-mode operation across all roles, judges the system is
stable**. There is no fixed soak duration; the PM signs off at a
Phase 5 completion review point. The decision *point* is locked; the
duration is intentionally flexible.

### 7.1 #8698 — Remove /loop Materials

- Delete `references/sub-skills/common-loop/`.
- Delete `references/sub-skills/roles/<role>/loop/` for all roles.
- Delete `references/roles/<role>/includes-loop.yml` for all roles.
- Remove /loop branches from `cycle_pre.py` and `cycle_post.py`
  (becomes single-mode, events-only).
- Remove status-line file-based fallback path (#8700).
- **Non-goal**: do NOT remove the L1 failsafe boot sequence (now part
  of event-mode L1 base, owned by #8694). It stays because it is
  tracker-scan based, not /loop-based.

### 7.2 #8702 — Documentation Realignment

- README, vault notes, onboarding docs, architecture diagrams.
- Update SKILL.md and any setup/wizard docs referencing /loop.
- Companion to #8698 — runs after /loop is physically gone from the
  source tree.

---

## 8. Process Directive (active NOW)

### 8.1 #8703 — DM Pauses /loop-Referencing Documentation Updates

During the Phase 5 planning + rollout window, DM must pause general
documentation updates that reference /loop mechanics (so the docs
don't churn while the architecture is mid-flip).

- CHANGELOG entries continue normally.
- Per-issue shipping summaries continue normally.
- Only **architecture descriptions** of how agents wake / cycle pause.
- The pause lifts when #8702 begins.

---

## 9. Sequencing Diagram

```
                    ┌────────────────────────────────────────┐
                    │  Hard prerequisites                    │
                    │                                        │
                    │   #8692 — singleton enforcement        │
                    │   #4792 — harness sole-authority       │
                    │           lifecycle (rescoped)         │
                    └────────────────┬───────────────────────┘
                                     │
                                     │ must SHIP
                                     ▼
                    ┌────────────────────────────────────────┐
                    │  #8697 — compose.py dual-mode          │
                    │  (establishes two fragment trees,      │
                    │   migrates event-driven-workflow,      │
                    │   closes #8699,                        │
                    │   audits L4 for /loop residue)         │
                    └────────────────┬───────────────────────┘
                                     │
                                     ▼
       ┌─────────────────────────────┴─────────────────────────────┐
       │                                                           │
       ▼                                                           ▼
┌────────────────────┐                              ┌─────────────────────┐
│ #8694 (lead)       │                              │ #8695               │
│ event-mode L1 base │                              │ bootup_complete     │
│ — boot + reactions │                              │ informational flag  │
│   + cursor mgmt    │                              │ on AgentState       │
│   + event_poll.py  │                              │ (no gate/queue)     │
│   + idle cooldown  │                              │                     │
│   + DM end-of-task │                              │                     │
│   + eviction gap   │                              │                     │
└────────┬───────────┘                              └──────────┬──────────┘
         │                                                     │
         ▼                                                     ▼
┌────────────────┐    ┌────────────────┐    ┌─────────────────────┐
│ #8701          │    │ #8700          │    │ #8704               │
│ cycle_pre/post │    │ status line    │    │ TUI human queue     │
│ task-level     │    │ HTTP API panel │    │ panel               │
└────────┬───────┘    └────────┬───────┘    └──────────┬──────────┘
         │                     │                       │
         └─────────────────────┼───────────────────────┘
                               │
                               │ All shipped + per-role pre-flip
                               │ checklist (§6.3) complete + flip
                               │ event-driven: yes in config.md
                               ▼
                  ┌──────────────────────────────┐
                  │ PM stability review          │
                  │ (no fixed soak duration —    │
                  │  PM judgment call)           │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ Phase 6 cleanup              │
                  │   #8698 — remove /loop       │
                  │   #8702 — docs realign       │
                  └──────────────────────────────┘
```

Notes on sequencing:
- #8697 is the spine. Until it ships, all other event-mode tasks
  cannot deploy their fragments cleanly (no events-mode tree exists).
- #8694, #8695 can be authored in parallel with #8697 but their
  fragment/code content lands under the #8697 tree.
- #8700, #8701, #8704 are independent code refactors and can run in
  parallel with each other once #8697 lands.
- #8703 is active immediately and lifts when #8702 begins.
- #8696 has been folded into #8694 (closed not-planned). The L1 boot
  sequence is part of #8694's event-mode L1 base agent definition.
- #8699 is resolved internally as a #8697 deliverable.

---

## 10. Open Questions / Closing Notes

Most discussion points are locked. The remaining genuinely open items
and explicit closures of prior open questions:

### Genuinely open
1. **Exact directory naming for the two fragment sets** —
   `common-loop` vs `common/loop/`, etc. Deferred to #8697
   implementation. PM does not need to lock the name now.
2. **`design:*` label retirement** — retain as metadata indefinitely
   vs. retire entirely. Deferred to #8698 Phase 6 cleanup.
3. **Initial fragment classification pass** (loop / events / both for
   the existing ~31 entries per role manifest) — does this happen
   inside #8697 or as a separate sub-task? Recommend folding into
   #8697; flag if human prefers a dedicated task.

### Explicitly closed by this Phase 2

- **Cool-down per-role overrides** — closed. The locked decision at §2
  is the policy: 30m universal default, overridable in `config.md` but
  no overrides ship initially. No separate open question.
- **Soak period before Phase 6** — closed by **PM judgment call**. No
  fixed duration; PM signs off at a Phase 5 completion review point.
  See §7.
- **RESEARCH-harness-events.md open questions 1–4 + 7** — moot under
  the thin-harness no-dispatch architecture (the harness does not
  observe tracker state or emit `assigned-to`).
- **RESEARCH open question 5** (singleton enforcement interaction) —
  resolved by #8692 being the sole hard prerequisite.
- **RESEARCH open question 6** (bootstrap timeout during harness
  restart) — locked: with the dispatch gate dropped (Finding 1
  resolution), a 60-second watchdog clearing a bootup gate is no
  longer applicable. The agent's degraded-mode retry loop (§3.1 step 5)
  with 5-minute backoff cap handles harness-down scenarios. Operators
  see `bootup_complete: false` longer than expected as a soft signal.
- **RESEARCH open question 8** (coordination with config flip) —
  locked: per-role flip happens AFTER `compose.py deploy` for that role
  AND AFTER #8692 singleton enforcement ships. See §6.3 pre-flip
  checklist.

If any of the genuinely open items need to be locked before TEST-PLAN
authoring begins, flag them; otherwise downstream planners can write
tests that don't depend on the answers.

---

## 11. Glossary

- **Forge** — GitHub Issues as the canonical source of truth, accessed
  via `references/scripts/tracker.py`.
- **Thin harness** — the FastAPI process (`harness.py`) operating as a
  pure broadcast event bus: no tracker observation, no dispatch logic,
  no per-role queue knowledge, no event gating.
- **Event bus** — the in-memory `EventStream` (deque, maxlen=1000) in
  `harness.py:364`. No disk persistence today.
- **Cursor** — per-agent `Last Processed Event ID` stored in
  `working-state.md`, advanced one event at a time via atomic
  `.tmp + mv` write.
- **Forge-read pattern** — on every decision, the agent re-reads the
  forge (`tracker.py`) for the referenced item's current state instead
  of trusting event payload.
- **Cool-down loop** — when `work_queue()` is empty, agent runs
  improvement-scan as an atomic task, then listens on the event stream
  with a timeout equal to remaining cool-down (default 30m universal,
  value read from `config.md` at scan-completion time).
- **Event-mode L1 base** — the event-mode L1 base agent definition
  fragment (owned by #8694) that contains the boot sequence, event
  reactions, cursor management, forge-read pattern, idle cooldown loop,
  comment handling, and event-listening invocation. There is no
  standalone `l1-boot.md` — the boot sequence lives inside this fragment.
- **L1 boot (event mode)** — the tracker-driven failsafe boot sequence
  (§3.1) that runs once per session before event listening. Survives
  total event-bus failure: the agent enters a retry loop and operates
  in degraded mode against the forge directly until the harness is
  reachable.
- **Degraded mode** — **boot-time only.** Operating directly from the
  forge via `work_queue()` when the harness is unreachable AT BOOT.
  The agent retries `bootup-complete` emission with exponential
  backoff capped at 5 minutes, and works through forge items in the
  meantime. Mid-operation harness failure (after `bootup-complete`)
  does NOT trigger degraded mode — the agent simply retries
  `event_poll.py` at the same 5-minute cap until the harness returns,
  relying on the L1 failsafe boot path if the operator restarts the
  agent.
- **`bootup-complete` event** — emitted by an agent at the end of L1
  boot. **Informational only.** The harness sets per-role
  `bootup_complete = True` on `AgentState` and exposes it via
  `GET /agents/{role}`. No queuing, no gating, no dispatching.
- **`listener_active`** — boolean field in the `bootup-complete` event
  payload indicating the agent's event-stream reader (`event_poll.py`
  invocation) is running and ready to receive events. Mechanism-agnostic
  (replaces the older Monitor-specific `monitor_active` field).
- **`event_poll.py`** — agent-side event-stream reader script delivered
  by #8694. Cursor-based polling of `GET /events?since=<cursor>` with
  stdout JSON-lines streaming, configurable timeout, and retry on
  transient harness errors. Invoked by agents per instructions composed
  into the event-mode L1 base fragment.
- **Atomicity rule** — every task (tracker work AND improvement-scan)
  runs to completion. Mid-task events are read + cursor-advanced
  but not acted on.
- **Improvement-scan crash recovery** — working-state's
  `## Improvement Scan` section carries a `Status: idle | running` field.
  `running` written at scan start, `idle` + `Last completed` +
  `Next scan after` written at scan completion. On boot, `Status: running`
  → restart the scan (improvement scans are idempotent).
- **Eviction gap** — third gap scenario: the cursor predates the oldest
  retained event in the harness's `maxlen=1000` deque. Agent logs
  eviction details, advances cursor to oldest-available event id, and
  skims forward. Forge current state subsumes the lost events.
- **Task-cycle** — `cycle_pre`/`cycle_post` invocation per task in
  events mode (replaces the /loop time-cycle).
- **HITL transition** — handoff to a human modeled as a status
  transition to a `pending-human-*` label, surfaced by the harness TUI
  (#8704).
- **Mode separation** — two completely separate L1–L3 fragment trees +
  two manifests per role, with shared mode-agnostic L4 project
  instructions (audited for /loop contamination). `compose.py` picks
  one L1–L3 set based on the role's `event-driven: yes/no` flag and
  layers shared L4 on top. No mode-conditional logic inside any L1–L3
  fragment.
- **`event-driven-workflow` fragment** — formerly hand-injected into
  deployed CLAUDE.mds (commit `a3b108f2`) with no source backing.
  Migration into `common-events/` is folded into #8697 (closing #8699).
- **`includes-loop.yml` / `includes-events.yml`** — per-role manifests
  authoritative for fragment ordering within their mode.
- **Pre-flip checklist** — the per-role sequence in §6.3 that must
  complete before flipping `event-driven: yes` for that role.
- **TUI** — single harness-served terminal UI. Hosts the status-line
  panel (#8700) and the human-queue panel (#8704). Both panels consume
  harness HTTP endpoints; neither reads agent-side files in events mode.
- **Phase 6 cleanup** — post-rollout deletion of /loop materials
  (#8698) and documentation realignment (#8702). Gated on PM stability
  judgment after events-mode operation across all roles (no fixed soak
  duration).

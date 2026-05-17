# Phase 5 Planning — Event-Driven Architecture CONTEXT

**Bundle**: #8694 / #8695 / #8696 / #8697 / #8700 / #8701 / #8704
**Hard prereqs**: #8692 (singleton enforcement), #8699 (event-driven-workflow source fragment)
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

Two completely separate L1–L4 fragment sets are composed (one for /loop, one
for events) so neither flow contains conditional logic. A new L1 boot sub-skill
provides a tracker-driven failsafe that survives a totally dead event bus. A
`bootup-complete` event gates harness-side dispatch queuing per role. The
cycle_pre/cycle_post scripts switch from time-cycle to task-cycle granularity
when event-driven mode is active. Two prerequisites — singleton enforcement
(#8692) and migrating the orphaned `event-driven-workflow` block into a real
source fragment (#8699) — must ship before any per-role flip of
`event-driven: yes`.

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
  improvement-scan as an atomic task → write cool-down expiry to
  `working-state.md` → listen with timeout = remaining cool-down.
- **Cool-down default = 30 minutes universal across roles**, overridable
  per-role in `config.md` (no overrides until empirical observation warrants).
- **Cool-down storage** = `.squidsquad/<role>/working-state.md` under
  `## Improvement Scan` (fields: `Last completed: <ts>`, `Cool-down: 30m`).
- **Comments are not standalone triggers** — most are informational.
  Comments are read by the *next agent picking up the work* when they
  interact with the issue.
- **DM exception for comments** — DM's task includes waiting for PR
  merges; comments may land during the wait. DM re-reads comments at
  task completion before next pickup, so reassignment / route-back /
  follow-up guidance from comments is honored.
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
- **Status line queries harness HTTP API** — own delayed refresh loop,
  not file-tail. Tracked in #8700.
- **Two completely separate L1–L4 fragment sets** — one per wake mode.
  No mode-conditional logic inside any fragment. `compose.py` picks one
  manifest + one fragment set based on role's `event-driven: yes/no` in
  `config.md`. Failsafe isolation: Phase 6 cleanup deletes the /loop
  directory wholesale.
- **L1 boot is tracker-driven failsafe**, not /loop-derived. Survives a
  total event-bus failure because the path is forge-scan based.
- **`bootup-complete` event gates outbound dispatch** — harness must NOT
  push `assigned-to` / `status-transition` events to a role until that
  role has emitted `bootup-complete`. Pre-bootup events queue per-role
  and flush on receipt. (Backed by `RESEARCH-harness-events.md` §"Path to
  Add bootup-complete".)
- **Event stream gap behavior** — log warning, advance cursor past the
  gap, continue. Forge-read makes this safe.
- **Long cursor lag (24h+)** — skim-then-advance for audit fidelity, not
  jump-to-latest.

---

## 3. Workflow Specification (events mode)

### 3.1 Boot — L1 Failsafe (Case A; covered by #8696)

1. Read `.squidsquad/<role>/working-state.md` → cursor + in-progress task.
2. Verify in-progress against forge — still my role? still
   `status:in-progress`? Yes → resume. No → drop, scan.
3. Skim events from cursor forward (informational; forge already has
   current state). Skim-then-advance, never jump-to-latest.
4. Advance cursor to latest event id.
5. Emit `bootup-complete` event (POST `/events` with `event_type=bootup-complete`,
   `role=<role>`, payload `{"monitor_active": true}`).
6. Begin listening on event stream.

L1 boot is **failsafe**, not primary. If the event bus is fine, the
harness flushes any queued dispatch immediately after step 5.

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

### 3.5 Special events

- **`stop-requested`** — honored ONLY at task boundary. Mid-task: read,
  advance, ignore. At boundary: checkpoint `working-state.md`
  (preserve cursor), exit cleanly.
- **`bootup-complete` from another agent** — informational. Advance
  cursor. No action.
- **Unknown event type** — log warning. Advance cursor. Do not block.

### 3.6 Idle = improvement-scan cool-down loop

- When `work_queue()` returns empty → enter improvement-scan as an
  atomic task.
- After scan completes → write to `working-state.md` under
  `## Improvement Scan`:
  ```
  Last completed: <YYYY-MM-DD HH:MM>
  Cool-down: 30m
  ```
- Listen on event stream with timeout = remaining cool-down.
- Timeout fires first → run next improvement-scan.
- Task-relevant event arrives during sleep → cancel wait, re-scan
  `work_queue()`.
- Event arrives during inflight scan → finish scan first (atomicity
  rule), then process.
- Default = **30m universal across roles**, configurable per role in
  `config.md` (no per-role overrides shipped initially).

### 3.7 Comment handling

- Comments are NOT standalone event triggers.
- Comments are absorbed by the next agent that picks up the issue.
- **DM exception**: DM rereads comments at task completion (PR-merge
  wait can be long; comment-driven guidance like reassign / route back /
  file follow-up must be honored).
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
  and continue to flow through the existing Layer 4 mechanism.

### 4.4 Phase 6 cleanup characteristic

Once every role has `event-driven: yes`, the /loop tree and
`includes-loop.yml` manifests are deleted wholesale. No conditionals
need to be picked apart from fragment bodies — that's the failsafe
isolation property. See #8698.

---

## 5. Per-Task Specifications

### 5.1 #8694 — Agent Event Reactions + Cursor Management (lead)

**Scope**: The full set of *agent-side* event-mode instructions:
event-reactions, cursor management, forge-read pattern, idle ==
improvement-cooldown loop, comment-handling rule, DM PR-merge edge case,
explicit transition-on-design-handoff rule.

**Deliverables**:
- Content under `references/sub-skills/common-events/` and per-role
  `references/sub-skills/roles/<role>/events/` describing:
  - The 5 workflow cases (boot / idle-event-arrives / after-completion /
    mid-task-event / special events) verbatim from §3.
  - Cursor format and atomic update protocol (write `.tmp`, `mv`).
  - Forge-read protocol — every decision consults the forge before
    acting.
  - Idle = improvement-scan cool-down loop with explicit
    `working-state.md` schema.
  - Comment-handling rule and DM PR-merge re-read exception.
  - **Transition-on-handoff rule**: when an agent assigns work to a
    different role (including humans), the assignment MUST be a
    status transition so it appears on the event stream. Bare comments
    do not wake the recipient.
- Updates to per-role events fragments (skill / pm / qa / dm) for
  role-specific behavior on top of the common contract.

**Files touched (illustrative — final naming defers to #8697)**:
- `references/sub-skills/common-events/event-reactions.md` (new)
- `references/sub-skills/common-events/cursor-management.md` (new)
- `references/sub-skills/common-events/forge-read-pattern.md` (new)
- `references/sub-skills/common-events/idle-cooldown-loop.md` (new)
- `references/sub-skills/common-events/comment-handling.md` (new)
- `references/sub-skills/roles/dm/events/pr-merge-wait.md` (new)
- `references/sub-skills/roles/pm/events/*.md` (per-role events)
- `references/sub-skills/roles/skill/events/*.md`
- `references/sub-skills/roles/qa/events/*.md`
- `references/roles/<role>/includes-events.yml` (manifest entries
  pointing at the above)

**Acceptance**:
- CQ spec (`tests/comprehension/8694_spec.json`) covers: how the agent
  reacts to a mid-task event; how the agent handles an unknown event;
  what fires when `work_queue()` returns empty; what DM does after a PR
  merges while it was waiting; what an agent does if a comment on its
  issue requests a route-back.
- Comprehension test passes with a fresh agent given only the new
  fragments.
- No mode-conditional language inside any fragment ("if event-driven
  is yes, ..." is banned in fragment bodies).
- Heavy instruction-design task — primary content surface for Phase 5.

---

### 5.2 #8695 — `bootup-complete` Event + Dispatch Gate

**Scope**: Small harness add. Define and recognize the
`bootup-complete` event from agents; gate outbound dispatch on receipt;
queue pre-boot events per-role and flush on receipt.

**Deliverables** (from `RESEARCH-harness-events.md` §"Path to Add
bootup-complete"):
- `references/scripts/event_catalog.py`: add `bootup-complete` to
  `EMITTED` dict, source `"agent boot"`, payload_fields
  `["monitor_active"]`.
- `references/scripts/harness.py`:
  - Add `bootup_complete: bool = False` to `AgentState.__slots__` and
    `__init__`.
  - Reset to `False` on each spawn (`start_agent`, `_deferred_init`,
    PID change in `update_health`).
  - In `_update_agent_from_event()` (~line 750): when
    `event_type == "bootup-complete"`, set `bootup_complete = True` and
    flush `_pending_dispatch[role]`.
  - Add `_pending_dispatch: dict[str, list[dict]]` to `HarnessState`
    (or inline on `AgentState`).
  - New helper `_flush_dispatch_queue(role)`.
  - When outbound dispatch occurs (future code path or any code path
    that emits `assigned-to`/`status-transition` toward an agent):
    if `bootup_complete is False`, queue in `_pending_dispatch[role]`
    and log `"queued-but-not-dispatched for {role} — waiting for
    bootup-complete"`.
  - `AgentState.to_dict()` already serializes fields; add
    `"bootup_complete": self.bootup_complete` (~line 101–115).
- POST `/events` already accepts agent-originated events
  (`harness.py:827`). No endpoint change required.
- GET `/agents/{role}` already returns full `AgentState.to_dict()`.
  No endpoint change required.

**Files touched**:
- `references/scripts/event_catalog.py`
- `references/scripts/harness.py`
- L1 boot fragment (#8696) emits `bootup-complete` — see §5.3.

**Acceptance**:
- Unit test: spawning an agent resets `bootup_complete` to False.
- Unit test: posting a `bootup-complete` event flips the flag and
  flushes pending dispatch.
- Integration test: a pre-boot dispatch is queued and delivered after
  `bootup-complete`.
- `GET /agents/{role}` returns `bootup_complete` in JSON.

**Note**: Because the harness in this architecture does NOT do
outbound dispatch logic itself, the "dispatch gate" is primarily a
guard for any *external* sources of harness-originated events (e.g.
`pr-merged`, `compose-completed` via `_emit_event()` already in
`harness.py`). The gate ensures these don't fire toward a role that
hasn't booted yet.

---

### 5.3 #8696 — L1 Boot Instructions (Tracker-Driven Failsafe)

**Scope**: New sub-skill that slots at position 1 in
`includes-events.yml` for every role. Implements Case A (§3.1). Tracker-
driven, not /loop-driven — survives total event-bus failure.

**Deliverables**:
- New fragment `references/sub-skills/common-events/l1-boot.md` (final
  path subject to #8697 directory layout). Contents per
  `RESEARCH-compose-boot.md` §"Path to L1 Boot Sub-Skill" with these
  locked-decision adjustments:
  - Step 1: resume check via `working-state.md` AND verify the
    in-progress task against the forge (still my role? still
    `status:in-progress`?).
  - Step 2: tracker scan via `python references/scripts/tracker.py
    work-queue <role>`, skip `design:needed` / `design:in-progress`.
  - Step 3: skim events from cursor forward (informational), advance
    cursor to latest.
  - Step 4: emit `bootup-complete` event (per #8695).
  - Step 5: enter event-listening (Monitor or equivalent).
- Slot at position 1 of every role's `includes-events.yml`.

**Files touched**:
- `references/sub-skills/common-events/l1-boot.md` (new)
- `references/roles/pm/includes-events.yml`
- `references/roles/skill/includes-events.yml`
- `references/roles/qa/includes-events.yml`
- `references/roles/dm/includes-events.yml`

**Acceptance**:
- CQ spec (`tests/comprehension/8696_spec.json`) covers: agent boots
  with non-empty `working-state.md` (resumes), agent boots with empty
  `working-state.md` (scans tracker), agent boots when event bus is
  unreachable (still scans tracker — failsafe property), agent emits
  `bootup-complete` once and only once per boot.
- L1 boot fragment contains no /loop-mode language.

---

### 5.4 #8697 — `compose.py` Dual-Mode (separate L1–L4 sets per wake mode)

**Scope**: Code refactor. Establish the two-fragment-set architecture
described in §4. Includes migration of the orphaned
`event-driven-workflow` block into a real source fragment (#8699
prereq folded in here).

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
- Migration of `event-driven-workflow` block: extract from currently
  hand-injected content in deployed CLAUDE.mds (line ranges per
  `RESEARCH-compose-boot.md`: PM 344–425, skill ~328–416, QA 344–425,
  DM 363–444) into real fragments under `common-events/`. **This
  resolves #8699 and is folded into #8697 scope.**
- Initial classification pass: for the four existing role manifests
  (PM 31 entries, others similar), classify each entry as `loop`,
  `events`, or `both`. "Both" entries appear in BOTH new manifests.

**Files touched**:
- `references/scripts/compose.py`
- New: `references/sub-skills/common-events/*.md` (event-driven-workflow
  migration source)
- New: `references/sub-skills/common-loop/*.md` (cycle-runner and
  /loop-only fragments)
- New: `references/roles/<role>/includes-events.yml` (4 files)
- Renamed: `references/roles/<role>/includes.yml` →
  `references/roles/<role>/includes-loop.yml` (4 files, kept until #8698)
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
  fragment, not hand-injected.

---

### 5.5 #8700 — Status Line Refactor (harness HTTP API source)

**Scope**: Switch status line data source from local files to harness
HTTP API. Run its own delayed refresh loop.

**Deliverables**:
- Status line script reads `GET /status` (or `GET /agents`) from
  harness on a 2–5 second refresh loop.
- **Backward compat**: detect per-role wake mode. For `/loop` roles
  during transition, fall back to file-based rendering. Once #8698
  ships and `/loop` mode is gone, remove the file-based path.
- Display fields per agent: current task id, phase / current state,
  bootup_complete flag, health.

**Files touched**:
- Status line script(s) (location per current codebase — likely a
  `statusline.py` or similar in `references/scripts/`)
- Possibly `harness.py` if a new aggregate endpoint is preferred over
  composing from `/agents` + per-agent calls.

**Acceptance**:
- Status line updates without scanning local agent files when harness
  is reachable.
- Status line falls back gracefully (file-based) when role is still
  in /loop mode.
- Status line refresh does not impose a measurable CPU/API load
  (2–5s cadence).
- CQ spec deferred — primarily a code task, not instruction-design.

---

### 5.6 #8701 — `cycle_pre` / `cycle_post` Task-Level Refactor

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

### 5.7 #8704 — Harness TUI Surfaces Human-Assigned Work

**Scope**: New harness endpoint + TUI/UI panel for `pending-human-*`
items. Prominent surfacing (badge count, dedicated panel). Works for
any agent's pending-human transitions, not just designer.

**Deliverables**:
- `references/scripts/harness.py`: new endpoint, e.g.
  `GET /human/queue`, returning all open issues with a
  `status:pending-human-*` label. Implementation: shell out to
  `tracker.py` or `gh issue list` with appropriate filters; cache
  briefly (5–10s) to avoid hammering the forge.
- TUI / status surface: reads `GET /human/queue` on a delayed refresh
  loop (matches #8700 cadence). Renders:
  - Badge count of pending-human-* items.
  - Dedicated panel listing items: number, title, role that
    transitioned to human, transition timestamp.
- HITL is role-agnostic — works for skill, qa, dm, designer, any role
  that emits a pending-human-* transition.

**Files touched**:
- `references/scripts/harness.py`
- TUI / status display script(s).
- Possibly `references/scripts/tracker.py` if a new query is needed.

**Acceptance**:
- `GET /human/queue` returns all `pending-human-*` items, regardless
  of role.
- TUI shows a non-zero badge when at least one item is pending-human.
- Designer-loop special-case code (if any exists today) is removed.

---

## 6. Hard Prerequisites

These MUST ship before any per-role flip of `event-driven: yes`.

### 6.1 #8692 — Singleton Enforcement at Agent Startup (BLOCKER)

Without singleton enforcement, two agents of the same role can race on
event handling — the same root-cause class as the `cycle_post`
pollution incident that triggered this whole planning effort
(`RESEARCH-harness-events.md` §"Related Bugs Filed"). In events mode
the failure mode is worse: both sessions process the same event,
duplicate forge actions, corrupt cursors.

**Plan in parallel; gate approval/execution of any other Phase 5
task on #8692 being shipped first.**

### 6.2 #8699 — `event-driven-workflow` Source Fragment Missing (BLOCKER)

The `event-driven-workflow` block was hand-injected into deployed
CLAUDE.mds in commit `a3b108f2`. It has no source in
`references/sub-skills/` and no entry in any `includes.yml`. The next
`compose.py deploy` wipes it.

**Resolution**: fold the migration of this content into a proper
source fragment into #8697 scope (see §5.4). #8699 closes when #8697's
new `common-events/` tree contains the canonical
`event-driven-workflow` fragment(s) and `compose.py deploy` correctly
emits it.

---

## 7. Phase 6 Cleanup (dormant — pending event-mode fully on)

These tasks sit at `status:pending` until every role has
`event-driven: yes` and event-driven operation has been observed
stable for a tunable soak period.

### 7.1 #8698 — Remove /loop Materials

- Delete `references/sub-skills/common-loop/`.
- Delete `references/sub-skills/roles/<role>/loop/` for all roles.
- Delete `references/roles/<role>/includes-loop.yml` for all roles.
- Remove /loop branches from `cycle_pre.py` and `cycle_post.py`
  (becomes single-mode, events-only).
- Remove status-line file-based fallback path (#8700).
- **Non-goal**: do NOT remove the L1 boot failsafe (#8696). L1 boot is
  tracker-scan based, not /loop-based; it stays.

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
                    │  Hard prerequisites — parallel start   │
                    │                                        │
                    │   #8692 — singleton enforcement        │
                    │   #8699 — event-driven-workflow source │
                    │     (folded into #8697 scope)          │
                    └────────────────┬───────────────────────┘
                                     │
                                     │ both must SHIP
                                     ▼
                    ┌────────────────────────────────────────┐
                    │  #8697 — compose.py dual-mode          │
                    │  (establishes two fragment trees,      │
                    │   migrates event-driven-workflow,      │
                    │   closes #8699)                        │
                    └────────────────┬───────────────────────┘
                                     │
                                     ▼
       ┌─────────────────────────────┴─────────────────────────────┐
       │                                                           │
       ▼                                                           ▼
┌────────────────┐    ┌────────────────┐    ┌─────────────────────┐
│ #8694          │    │ #8695          │    │ #8696               │
│ agent event    │    │ bootup-complete│    │ L1 boot failsafe    │
│ reactions +    │    │ event + gate   │    │ tracker-driven      │
│ cursor mgmt    │    │                │    │ position 1 in       │
│                │    │                │    │ includes-events.yml │
└────────┬───────┘    └────────┬───────┘    └──────────┬──────────┘
         │                     │                       │
         ▼                     ▼                       ▼
┌────────────────┐    ┌────────────────┐    ┌─────────────────────┐
│ #8701          │    │ #8700          │    │ #8704               │
│ cycle_pre/post │    │ status line    │    │ TUI human queue     │
│ task-level     │    │ HTTP API       │    │                     │
└────────┬───────┘    └────────┬───────┘    └──────────┬──────────┘
         │                     │                       │
         └─────────────────────┼───────────────────────┘
                               │
                               │ All shipped + per-role flip
                               │ event-driven: yes in config.md
                               ▼
                  ┌──────────────────────────────┐
                  │ Soak period (stability obs.) │
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
- #8694, #8695, #8696 can be authored in parallel with #8697 but their
  fragment content lands under the #8697 tree.
- #8700, #8701, #8704 are independent code refactors and can run in
  parallel with each other once #8697 lands.
- #8703 is active immediately and lifts when #8702 begins.

---

## 10. Open Questions for Human Review

Most discussion points are already locked. The remaining items:

1. **Cool-down per-role overrides** — leave `config.md` schema empty
   until empirical observation warrants tuning. Confirm: no role-specific
   overrides ship in v1?
2. **Exact directory naming for the two fragment sets** —
   `common-loop` vs `common/loop/`, etc. Deferred to #8697
   implementation. Confirm: PM does not need to lock the name now?
3. **`design:*` label retirement** — retain as metadata indefinitely
   vs. retire entirely. Deferred to #8698 Phase 6 cleanup. Confirm:
   no decision needed in this bundle?
4. **Initial fragment classification pass** (loop / events / both for
   the existing ~31 entries per role manifest) — does this happen
   inside #8697 or as a separate sub-task? Recommend folding into
   #8697; flag if human prefers a dedicated task.
5. **Soak period before Phase 6** — how long does event-driven operation
   need to be stable before #8698 / #8702 are picked up? Not locked.

If any of these need to be locked before TEST-PLAN authoring begins,
flag them; otherwise downstream planners can write tests that don't
depend on the answers.

---

## 11. Glossary

- **Forge** — GitHub Issues as the canonical source of truth, accessed
  via `references/scripts/tracker.py`.
- **Thin harness** — the FastAPI process (`harness.py`) operating as a
  pure broadcast event bus: no tracker observation, no dispatch logic,
  no per-role queue knowledge.
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
  with a timeout equal to remaining cool-down (default 30m universal).
- **L1 boot** — the tracker-driven failsafe boot sequence (#8696)
  that runs once per session before event listening. Survives total
  event-bus failure because it queries the forge directly.
- **`bootup-complete` event** — emitted by an agent at the end of L1
  boot. Harness sets per-role `bootup_complete = True` and flushes
  any queued outbound dispatch for that role.
- **Atomicity rule** — every task (tracker work AND improvement-scan)
  runs to completion. Mid-task events are read + cursor-advanced
  but not acted on.
- **Task-cycle** — `cycle_pre`/`cycle_post` invocation per task in
  events mode (replaces the /loop time-cycle).
- **HITL transition** — handoff to a human modeled as a status
  transition to a `pending-human-*` label, surfaced by the harness TUI
  (#8704).
- **Mode separation** — two completely separate L1–L4 fragment trees +
  two manifests per role; `compose.py` picks one set based on role's
  `event-driven: yes/no` flag. No mode-conditional logic inside any
  fragment.
- **`event-driven-workflow` fragment** — currently hand-injected into
  deployed CLAUDE.mds (commit `a3b108f2`) with no source backing.
  Migration into `common-events/` is folded into #8697 (closing #8699).
- **`includes-loop.yml` / `includes-events.yml`** — per-role manifests
  authoritative for fragment ordering within their mode.
- **Phase 6 cleanup** — post-rollout deletion of /loop materials
  (#8698) and documentation realignment (#8702). Gated on stable
  events-mode operation across all roles.

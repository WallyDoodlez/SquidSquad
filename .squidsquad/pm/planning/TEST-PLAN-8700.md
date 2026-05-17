# TEST-PLAN-8700 — Status Line Refactor (harness HTTP API source)

**Issue**: #8700 — Phase 5 event-driven architecture bundle, status line panel
**Bundle lead**: #8694
**Cross-task**: #8704 (human-queue panel, shared TUI surface)
**Hard prereq for any per-role events flip**: #8692 (singleton enforcement)
**Co-ship dependencies**: #8695 (`bootup_complete` flag on `AgentState`), #8704 (TUI architecture is shared)
**Source**: `.squidsquad/pm/planning/CONTEXT.md` §5.4, §5.7, §6.3, §11 glossary "TUI"

---

## 1. Acceptance Criteria

Verbatim from CONTEXT.md §5.4 (plus measurable refinements in brackets):

1. **A1** — Status line updates without scanning local agent files when the
   harness is reachable and a role's config is `event-driven: yes`.
   *[Measurable: with harness up and role flipped, status line process opens
   zero file handles under `.squidsquad/<role>/` other than the role's own
   `config.md` read for mode detection. Verified via process I/O trace or
   `strace`/`Procmon` capture.]*
2. **A2** — Status line falls back gracefully (file-based) when a role is
   still in `/loop` mode (`event-driven: no` or absent in `config.md`).
   *[Measurable: file-based rendering output for that role is bit-identical
   to today's `statusline.sh` output for the same inputs.]*
3. **A3** — Edge case: `event-driven: yes` + no harness data for that role
   (agent has not yet emitted `bootup-complete`, or harness returned
   `{"status": "unknown", "message": "No health data yet"}` per
   `harness.py:656`) → status line renders `events-mode, awaiting boot`.
4. **A4** — Status line refresh does not impose a measurable CPU/API load.
   *[Measurable: at the default 2–5s cadence, the panel makes ≤1 HTTP call
   per refresh per panel and consumes <5% CPU on the harness host during a
   30s sample.]*
5. **A5** — Status line panel runs its own delayed refresh loop independent
   of agent cycles (CONTEXT.md §5.4 deliverable 2; §2 "Status line queries
   harness HTTP API — own delayed refresh loop, not file-tail").
6. **A6** — Mode detection reads `event-driven: yes/no` from
   `.squidsquad/config.md` per role using the same mechanism `compose.py`
   uses (`_read_config_value()`, per CONTEXT.md §5.4 deliverable 3).
7. **A7** — Display fields per agent: current task id, phase / current
   state, `bootup_complete` flag, health (CONTEXT.md §5.4 final bullet).
8. **A8** — Status line panel and #8704 human-queue panel share the harness
   API base URL (resolved from `.squidsquad/.harness-port`) and the same
   refresh cadence (CONTEXT.md §5.7).
9. **A9** — Once #8698 ships, the file-based rendering path is removed
   (CONTEXT.md §5.4 deliverable 6, §7.1). *Verified by a Phase 6 follow-up,
   not gated on this task's ship.*

> **Note on CQ spec**: CONTEXT.md §5.4 acceptance explicitly states "CQ spec
> deferred — primarily a code task, not instruction-design." No
> comprehension test is required for #8700. Cross-check: this task does
> NOT touch LLM-consumed instruction surfaces in `references/sub-skills/`.

---

## 2. Test Categories Map

| Section | Category               | Count | Maps to AC |
| ------- | ---------------------- | ----- | ---------- |
| 3       | Unit                   | 5     | A1, A3, A5, A6, A2 |
| 4       | Integration            | 5     | A1, A2, A3, A4, A5, A7 |
| 5       | Negative / isolation   | 4     | A1 |
| 6       | Manual smoke           | 3     | A1, A2, A3, A6 |
| 7       | TUI cross-task (#8704) | 4     | A8 |
| 8       | Gating conditions      | n/a   | (process) |
| 9       | Post-ship validation   | 3     | A9 |

---

## 3. Unit Tests

### TC-U1 — HTTP client parses `/agents` response correctly (A1, A7)
- **Precondition**: Mock harness server returns the JSON shape produced by
  `harness.py:579 list_agents()` — `{"agents": [<AgentState.to_dict()>...]}`.
  Include at least one agent with `bootup_complete: true`, `status: "running"`,
  and a `current_phase` (read by `harness.py:712` from `current-state`).
- **Steps**: Invoke the status line HTTP client against the mock; capture
  the parsed in-memory model.
- **Expected**: Per-agent records include `role`, `status`,
  `bootup_complete`, `current_phase`, `current_task`, and `health`. No
  agent record dropped.
- **Verification**: `pytest tests/test_statusline_http.py::test_parse_agents`.

### TC-U2 — Mode detection returns `events` when `event-driven: yes` (A6)
- **Precondition**: Fixture `config.md` with role section containing
  `event-driven: yes`.
- **Steps**: Call the mode-detection helper for that role.
- **Expected**: Returns the events-mode rendering branch.
- **Verification**: `pytest tests/test_statusline_mode.py::test_events_flag_yes`.

### TC-U3 — Mode detection returns `loop` when flag absent or `no` (A2, A6)
- **Precondition**: Two fixtures — one config with `event-driven: no`,
  one with no `event-driven` line at all (transitional default).
- **Steps**: Call the mode-detection helper for each.
- **Expected**: Both return the loop-mode rendering branch.
- **Verification**: `pytest tests/test_statusline_mode.py::test_events_flag_no_or_absent`.

### TC-U4 — Refresh loop respects configured interval (A4, A5)
- **Precondition**: Status line panel configured with refresh interval = 3s.
- **Steps**: Run the refresh loop for 30s against a mock harness with a
  request-counting middleware.
- **Expected**: Total request count to `/agents` (or `/status`) is between
  9 and 11 (one per refresh ± boundary).
- **Verification**: `pytest tests/test_statusline_refresh.py::test_refresh_cadence`.

### TC-U5 — File-based fallback path still functions for /loop roles (A2)
- **Precondition**: Role has `event-driven: no` in fixture `config.md`;
  populate `.squidsquad/<role>/current-state` and `working-state.md` to the
  same shape `statusline.sh` reads today (per `references/statusline.sh`
  lines 170–178, 384–391).
- **Steps**: Invoke the panel for that role with harness mocked unreachable.
- **Expected**: Output matches the existing `statusline.sh` rendering for
  the same inputs (regression baseline).
- **Verification**: `pytest tests/test_statusline_fallback.py::test_loop_mode_output_parity`.

---

## 4. Integration Tests

### TC-I1 — Single agent in events mode renders correct state (A1, A7)
- **Precondition**: Live harness started (`harness.py`), one agent (e.g.
  `skill`) with `event-driven: yes` in `config.md`, agent has emitted
  `bootup-complete` so `AgentState.bootup_complete == True`. Agent has
  written a `current-state` so `GET /agents/{role}/health` returns a
  non-null `current_phase` (per `harness.py:710-714`).
- **Steps**: Run the status line panel against the live harness for 10s.
- **Expected**: Rendered output shows the agent's current task id, phase
  derived from `current_phase`, `bootup_complete = true` indicator, and a
  healthy marker.
- **Verification**: Capture stdout of the panel; assert all four fields
  appear in at least one refresh frame.

### TC-I2 — Mixed mode (one events, one /loop) renders both correctly (A2, A6)
- **Precondition**: Two roles configured — `skill` with `event-driven: yes`
  and bootup-complete emitted; `qa` with `event-driven: no` (or flag
  absent). `qa` has a fresh `.squidsquad/qa/current-state`.
- **Steps**: Run the panel for 10s.
- **Expected**: `skill` rendered via HTTP API path; `qa` rendered via
  file-based path. Per-role mode detection is honoured — the panel does
  NOT assume a global mode.
- **Verification**: Inject distinct sentinel values into each source
  (e.g. an unusual phase string only via HTTP for `skill`, only via file
  for `qa`); assert each sentinel appears for the matching role.

### TC-I3 — Edge case: events-mode but no harness data (A3)
- **Precondition**: Role `dm` flipped to `event-driven: yes` in
  `config.md`; harness running but `dm` has never started, so
  `GET /agents/dm` returns the unknown shape (`harness.py:656`:
  `{"role": "dm", "status": "unknown", "message": "No health data yet"}`).
- **Steps**: Run the panel for 10s.
- **Expected**: The `dm` slot renders the literal string `events-mode,
  awaiting boot` (or the agreed final localisation thereof). Panel does
  NOT crash. Other agents render normally.
- **Verification**: stdout contains the marker text in every refresh
  frame for `dm`.

### TC-I4 — Harness unreachable: degraded indicator, no crash (A4 negative slice)
- **Precondition**: Role `skill` flipped to `event-driven: yes`. Stop the
  harness before the panel starts.
- **Steps**: Run the panel for 15s. Verify the panel does not raise an
  uncaught exception, log spew is bounded, and CPU stays below the A4
  threshold despite connection-refused errors.
- **Expected**: A degraded indicator is rendered (concrete glyph/string
  TBD by the implementer — at minimum, distinguishable from healthy and
  from `events-mode, awaiting boot`). Panel process is still alive at
  end of test.
- **Verification**: assert exit code 0 on SIGTERM; assert presence of
  degraded marker; assert no unhandled traceback in captured stderr.

### TC-I5 — Refresh latency: state change visible within 2× interval (A4, A5)
- **Precondition**: Refresh interval = 3s. Agent state changes (e.g.
  `current_phase` flips from `idle|` to `verifying|...`).
- **Steps**: Trigger the state change, then sample panel output every
  500ms for up to 6s.
- **Expected**: The new phase appears in the panel within 6s (= 2 ×
  interval).
- **Verification**: assert observed propagation delay ≤ 2 × configured
  interval.

---

## 5. Negative Tests (isolation)

### TC-N1 — Panel does NOT read agent-side `current-state` files in events mode (A1)
- **Precondition**: Role flipped to `event-driven: yes`; harness reachable;
  `bootup_complete` true.
- **Steps**: Strace / Procmon the panel process for 15s of refresh activity.
- **Expected**: ZERO open() / CreateFile calls against any path under
  `.squidsquad/<role>/current-state` for any events-mode role. Read of
  the role's own `config.md` is permitted (mode detection).
- **Verification**: trace log filter on the prohibited paths returns empty.

### TC-N2 — Panel does NOT depend on `cycle_pre` / `cycle_post` writing state files (A1)
- **Precondition**: Same as TC-N1, plus block writes by simulating
  `cycle_pre.py`/`cycle_post.py` not running (no recent `current-state`
  mtime updates for the events-mode role).
- **Steps**: Run panel for 30s.
- **Expected**: Panel rendering for the events-mode role remains correct
  and current — sourced from `GET /agents/{role}` only. No "stale" health
  warning derived from `current-state` mtime should fire for events-mode
  roles. (`statusline.sh` lines 91–119 mtime logic is bypassed in events
  mode.)
- **Verification**: assert phase/task fields update when the harness
  state updates, even though `current-state` mtime is frozen.

### TC-N3 — Panel does NOT poll the forge directly (A1)
- **Precondition**: Network-egress filter or `gh` shim that records calls.
- **Steps**: Run panel for 30s in events mode.
- **Expected**: ZERO calls to `gh issue *` or `api.github.com` from the
  panel process. (Status line consults harness only; backlog cache logic
  in `statusline.sh` lines 240–277 should not be invoked for events-mode
  rendering.)
- **Verification**: shim invocation count is 0; egress filter log empty.

### TC-N4 — Panel does NOT write any files (A1)
- **Precondition**: Run panel under a writable-path tracer.
- **Steps**: Run for 60s spanning multiple refreshes and a harness
  reconnect.
- **Expected**: Zero writes to `.squidsquad/` (no `.tmp + mv` activity,
  no log file appends from the panel itself — logging is to stderr only).
- **Verification**: trace log shows no write/create events under
  `.squidsquad/`. *Note*: today's `statusline.sh` writes
  `.squidsquad/<role>/context-pressure` (line 72) — this side-effect
  should NOT be reproduced in the new panel since the harness owns
  context-pressure exposure via `GET /agents/{role}/health`. Confirm
  with implementer; if retained for back-compat, document the exception
  here.

---

## 6. Manual Smoke Tests

### TC-S1 — Healthy 4-agent events-mode smoke
- **Steps**: Bring up `pm`, `skill`, `qa`, `dm` all with
  `event-driven: yes`; ensure each emits `bootup-complete`; run the TUI
  panel for ~2 minutes.
- **Expected**: All four agents render task id, phase, `bootup_complete`
  indicator, and health on every refresh. Display is stable; no flicker
  beyond the configured cadence.

### TC-S2 — Graceful degradation when harness stops
- **Steps**: With TC-S1 running, kill the harness process. Observe the
  panel for 30s, then restart the harness.
- **Expected**: Degraded indicator appears within one refresh window.
  Panel reconnects on harness restart and resumes normal rendering
  within ≤ 2 × the configured interval.

### TC-S3 — Mid-run flag toggle picks up after recompose
- **Steps**: Start with `qa` at `event-driven: no` (file-based). Flip
  `qa` to `event-driven: yes` in `config.md`, run `compose.py deploy qa`,
  ensure `qa` has emitted `bootup-complete` post-recompose.
- **Expected**: On the next panel refresh after the config change, `qa`'s
  slot switches from file-based to HTTP-API-based rendering. No restart
  of the panel process required. (Per CONTEXT.md §5.4 deliverable 3,
  mode detection is per-role and read on each refresh, or at minimum
  picked up on next refresh after recompose.)

---

## 7. TUI Integration Tests (cross-task with #8704)

These tests verify the shared TUI architecture established in
CONTEXT.md §5.7. They are co-gating: #8700 may ship its panel before
#8704 ships the human-queue panel, but the shared-cadence and
shared-base-URL contract must be enforceable at the point #8704 lands.

### TC-T1 — Both panels run in the same TUI process (A8)
- **Precondition**: #8704 panel implementation available (or scaffolded).
- **Steps**: Boot a single TUI process hosting both the status-line
  panel and the human-queue panel.
- **Expected**: One process; both panels visible; no separate refresh
  threads beyond the shared scheduler.
- **Verification**: process tree shows a single TUI process owning both
  panel render loops.

### TC-T2 — Shared harness API base URL (A8)
- **Precondition**: `.squidsquad/.harness-port` points to a known port;
  start the harness on that port.
- **Steps**: Inspect both panels' configured base URL at runtime (via a
  debug endpoint or log line at startup).
- **Expected**: Both panels resolve the same base URL from
  `.squidsquad/.harness-port`. No hard-coded port in either panel.
- **Verification**: log assertion or in-process introspection.

### TC-T3 — Shared refresh cadence (A8)
- **Precondition**: Single TUI process with cadence configured to 4s.
- **Steps**: Record HTTP request timestamps for `/agents` (status panel)
  and `/human/queue` (human-queue panel, #8704) over 40s.
- **Expected**: Both panels fire on the shared 4s schedule. Drift is
  bounded (no panel polls faster than the configured cadence; the
  scheduler does not race the panels against each other).

### TC-T4 — State changes propagate to both panels consistently (A8)
- **Precondition**: An agent transitions an issue to a `pending-human-*`
  status (which causes both the status-panel's agent-state and the
  human-queue panel's queue to change).
- **Steps**: Trigger the transition; sample both panel outputs.
- **Expected**: Both panels reflect the change within ≤ 2 × the
  configured refresh interval. The agent's status panel shows the new
  phase and the human-queue panel shows the new pending-human item in
  the same render window or adjacent windows.

---

## 8. Gating Conditions

- **Co-ships with #8695** — status line consumes the new
  `bootup_complete: bool` field on `AgentState` (CONTEXT.md §5.2). If
  #8695 is not yet shipped, A3 and A7 cannot be evaluated.
- **Co-ships with #8704** — Section 7 cannot be fully validated until
  the human-queue panel exists. #8700 may ship with §7 deferred, but the
  shared-cadence and shared-base-URL contract must already be in place
  in the code so #8704 plugs in cleanly. Treat §7 as a co-gate on bundle
  ship, not on #8700 individual ship.
- **Hard prereq #8692 (singleton enforcement)** — no role's
  `event-driven: yes` flip may occur before #8692 ships (CONTEXT.md
  §6.3 step 1). Until then, status line events-mode rendering can be
  exercised only in test fixtures, never in production agent terminals.
- **Per-role pre-flip checklist** — CONTEXT.md §6.3 items 1–6 must all be
  satisfied before flipping any role in `config.md`.
- **Standard plan-checker** — TEST-PLAN.md reviewed by plan-checker
  subagent and approved by human before #8700 transitions to Approved.

---

## 9. Post-Ship Validation

### TC-P1 — File dependency removed after per-role flip (A9 precursor)
- **Steps**: After flipping `skill` to `event-driven: yes` and shipping
  #8700, stop all `cycle_pre.py`/`cycle_post.py` writers for `skill` for
  a controlled 10-minute window (or freeze the current-state file).
- **Expected**: Status line panel for `skill` continues to render
  correctly from harness state. Health indicator does not erroneously
  degrade because of frozen file mtime.

### TC-P2 — Soak across N task transitions
- **Steps**: After full per-role rollout, leave the TUI running for ≥1
  hour spanning at least 10 task transitions across the four roles.
- **Expected**: Panel correctly tracks every transition. No drift, no
  stuck-state, no leaked file handles, no memory growth beyond a small
  steady-state envelope.

### TC-P3 — Phase 6 cleanup gate (A9)
- **Precondition**: All roles on `event-driven: yes`; PM has signed off
  on Phase 5 stability (CONTEXT.md §7).
- **Steps**: Land #8698; verify the file-based rendering path has been
  removed from the panel code (no fallback branch, no `current-state`
  reads anywhere in the panel module).
- **Expected**: Panel is single-mode (HTTP API only). Compiles, runs,
  and renders identically to events-mode behaviour before the removal.
- **Verification**: code review + regression run of TC-I1, TC-I3, TC-I4.

---

## Open Questions (gaps in CONTEXT.md §5.4)

1. **Endpoint choice** — CONTEXT.md §5.4 says "reads `GET /status` (or
   `GET /agents`)". `harness.py` exposes both (`/status` at line ~566+,
   `/agents` at line 579). The implementer chooses; tests should be
   written against whichever is selected. Recommend `/agents` so per-role
   data is one round-trip and matches the `AgentState.to_dict()` shape
   already used by #8695.
2. **Aggregate endpoint** — CONTEXT.md §5.4 "Files touched" mentions
   "possibly `harness.py` if a new aggregate endpoint is preferred over
   composing from `/agents` + per-agent calls." If a new endpoint is
   introduced (e.g. `GET /status/tui`), update TC-U1 / TC-I1 mock shapes
   accordingly.
3. **Degraded indicator string** — TC-I4 references a "degraded indicator"
   but the concrete glyph/text is not specified in CONTEXT.md. Defer to
   implementer; capture the chosen marker in the test for assertion.
4. **`context-pressure` writes** — today's `statusline.sh` writes
   `.squidsquad/<role>/context-pressure` (line 72). CONTEXT.md does not
   address whether the new panel preserves this behaviour. TC-N4 flags it.
   Recommend: do NOT preserve; expose via `GET /agents/{role}/health`
   instead (harness already reads it at `harness.py:716-721`).
5. **Refresh interval source** — CONTEXT.md §5.4 says "2–5 second
   refresh loop" and §5.7 says "refresh cadence (2–5 seconds)". Is the
   cadence configurable via `config.md` (e.g. a new key under a `## TUI`
   section) or hard-coded with a default? Defer to implementer; if
   configurable, add a unit test covering the read path analogous to
   TC-U4.
6. **TUI panel host process** — CONTEXT.md §5.7 says "harness-served TUI"
   but does not specify whether the TUI runs *inside* the `harness.py`
   process or as a separate process consuming harness HTTP. Recommend
   separate process for fault isolation; this plan's tests assume that
   model. Flag for implementer confirmation.

---

## Document History

- 2026-05-17 — Initial draft (PM). Based on CONTEXT.md §5.4, §5.7, §6.3,
  §11. References `references/statusline.sh` for file-based baseline
  parity, `references/scripts/harness.py:579-723` for the endpoints the
  panel consumes, and CONTEXT.md §5.2 for the `bootup_complete` field
  this task depends on (#8695).

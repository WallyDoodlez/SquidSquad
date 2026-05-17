# TEST-PLAN-8700 — Status Line Refactor (harness HTTP API source)

**Issue**: #8700 — Phase 5 event-driven architecture bundle, status line panel
**Bundle lead**: #8694
**Cross-task**: #8704 (human-queue panel, shared TUI surface)
**Hard prereq for any per-role events flip**: #8692 (singleton enforcement)
**Co-ship dependencies**: #8695 (`bootup_complete` flag on `AgentState`), #8704 (TUI architecture is shared)
**Source**: `.squidsquad/pm/planning/CONTEXT.md` §5.4, §5.7, §6.3, §11 glossary "TUI"

## Revision Log

- **2026-05-17** — Revised per deepseek R1 review (2 errors + 8 warnings) + 4 PM-locked gap resolutions.
  - **PM Gap 1 (LOCKED) — TUI process model**: TUI runs as a **separate process** consuming harness HTTP endpoints (CONTEXT §5.7 updated). Open Question 6 closed. TC-I4 precondition restated: "stop harness; start panel as a separate process; observe panel startup-degraded handling."
  - **PM Gap 4 (LOCKED) — Status line refresh interval**: hard-coded 5s default, no config knob in v1. Open Question 5 removed (resolved). TC-U4 precondition updated to "hard-coded 5s interval; assert 6 requests in 30s ± 1."
  - F1 (error, TC-N2 contradiction): split verification — (a) panel does NOT independently check `current-state` mtime or emit stale warning for events-mode roles when source frozen; (b) `bootup_complete` and `status` fields update via harness AgentState (don't depend on file); `current_phase` staleness when source frozen is expected, not a bug.
  - F2 (error, TUI process model — closed by Gap 1 above).
  - F3 (warning, HTTP error response coverage): added TC-N5 — 500/502/404/malformed JSON / shape mismatch handling.
  - F4 (warning, refresh independence from agent activity): TC-U4 explicitly runs against a mock harness with zero agent activity.
  - F5 (warning, TC-N4 tracer scope): expanded to cover `/tmp`, `~/.cache`, repo root outside `.squidsquad/`; `context-pressure` writes locked to NOT preserved.
  - F6 (warning, TC-U4 counts only `/agents`): middleware now counts ALL HTTP requests to the mock harness across all endpoints.
  - F7 (warning, TC-T4 conflated propagation paths): assertions decoupled per panel; human-queue panel honours the 5–10s cache TTL on top of refresh cadence.
  - F8 (warning, SIGTERM exit code): changed verification to "no unhandled exception, exit 0 or 143 acceptable" since graceful SIGTERM is not in any AC.
  - F9 (warning, mode detection edge cases): noted dependency on `compose.py`'s existing `_read_config_value()` tests; no separate edge-case fixtures needed if reused.
  - F10 (warning, refresh interval source — closed by Gap 4 above).

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
   refresh cadence (**hard-coded 5s in v1 per PM Gap 4 / CONTEXT.md §5.7**).
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
| 5       | Negative / isolation   | 5     | A1, robustness |
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
- **Note** (review F9): edge cases (whitespace padding, trailing whitespace, case variations, key under wrong role section) are covered by `compose.py`'s existing `_read_config_value()` tests. If the panel reuses that function (recommended per A6), no additional edge-case fixtures are needed here. If the panel reimplements rather than reuses, add equivalent edge-case tests as TC-U2b/TC-U3b.

### TC-U4 — Refresh loop respects hard-coded 5s interval (A4, A5)
- **Precondition**: TUI starts with the **hard-coded 5s interval — no config knob in v1** (PM Gap 4 locked). Mock harness has **zero agent activity, zero events, zero state changes** during the test window (review F4 — ensures the refresh loop is independent of agent cycles, not coupled to event callbacks).
- **Steps**: Run the refresh loop for 30s against a mock harness with a **request-counting middleware that counts ALL HTTP requests across all endpoints** (review F6 — not just `/agents` or `/status`).
- **Expected**: Total HTTP request count to the mock harness is **6 ± 1** (30s / 5s = 6 refreshes). If the panel composes from `/agents` + per-agent calls, the total would exceed 6 and the test must fail (A4 hard constraint: ≤1 HTTP call per refresh per panel).
- **Verification**: `pytest tests/test_statusline_refresh.py::test_refresh_cadence`. Assert middleware total-request counter is in `[5, 7]` and assert no events were emitted on the mock harness during the test window.

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

### TC-I4 — Harness unreachable: degraded indicator, no crash (A4 negative slice, PM Gap 1 locked)
- **Precondition**: Role `skill` flipped to `event-driven: yes`. **Stop the harness; start the panel as a separate process** (PM Gap 1 — TUI is a separate process consuming harness HTTP per CONTEXT §5.7, NOT in-process inside `harness.py`). The separate-process model makes this test viable: stopping the harness does not stop the TUI.
- **Steps**: Run the panel for 15s. Verify the panel does not raise an
  uncaught exception, log spew is bounded, and CPU stays below the A4
  threshold despite connection-refused errors.
- **Expected**: A degraded indicator is rendered (concrete glyph/string
  TBD by the implementer — at minimum, distinguishable from healthy and
  from `events-mode, awaiting boot`). Panel process is still alive at
  end of test.
- **Verification**: assert panel process terminates without unhandled exception on SIGTERM — **exit code 0 or 143 acceptable** (review F8: graceful SIGTERM trapping is not declared in any AC, so default OS exit 143 = 128+15 is acceptable); assert presence of degraded marker in stdout capture; assert no unhandled traceback in captured stderr.

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

### TC-N2 — Panel does NOT independently check `current-state` mtime for events-mode roles (A1, review F1)
- **Precondition**: Same as TC-N1, plus block writes by simulating
  `cycle_pre.py`/`cycle_post.py` not running (no recent `current-state`
  mtime updates for the events-mode role). Source `current-state` file is frozen.
- **Steps**: Run panel for 30s.
- **Expected** (two distinct assertions):
  - **(a) No stale-warning regression**: the panel does NOT independently check `current-state` mtime or emit a "stale" warning for events-mode roles, even when the source file is frozen. `statusline.sh` lines 91–119 mtime logic is bypassed in events mode.
  - **(b) Harness-driven fields update**: the panel's `bootup_complete` and `status` fields DO update via harness `AgentState` changes (those don't depend on `current-state` file reads). When the harness's in-memory `bootup_complete` or `status` for the role changes, the next refresh reflects the change.
  - **Note**: `current_phase` staleness when the source `current-state` file is frozen is **expected** (per `harness.py:710-712`, `current_phase` is file-derived) and **not a panel bug**. The test does NOT assert that `current_phase` updates — only that `bootup_complete` and `status` do.
- **Verification**: (a) trace log shows no read of agent-side `current-state` files by the panel process; (b) flip `state.agents[<role>].bootup_complete` via test harness; assert next panel refresh reflects the new value while `current_phase` remains stale (unchanged).

### TC-N3 — Panel does NOT poll the forge directly (A1)
- **Precondition**: Network-egress filter or `gh` shim that records calls.
- **Steps**: Run panel for 30s in events mode.
- **Expected**: ZERO calls to `gh issue *` or `api.github.com` from the
  panel process. (Status line consults harness only; backlog cache logic
  in `statusline.sh` lines 240–277 should not be invoked for events-mode
  rendering.)
- **Verification**: shim invocation count is 0; egress filter log empty.

### TC-N4 — Panel does NOT write any files (A1, review F5)
- **Precondition**: Run panel under a writable-path tracer covering **`.squidsquad/`, `/tmp` (or platform equivalent), `~/.cache`, and the repo root outside `.squidsquad/`**. Tracer scope is explicit to prevent the panel from writing temp/cache/debug files outside `.squidsquad/` and still passing this test.
- **Steps**: Run for 60s spanning multiple refreshes and a harness
  reconnect.
- **Expected**: Zero writes to ALL traced paths (no `.tmp + mv` activity, no log file appends from the panel itself — logging is to stderr only). **`context-pressure` writes are LOCKED to NOT preserved** (review F5): today's `statusline.sh` writes `.squidsquad/<role>/context-pressure` (line 72) — the new panel MUST NOT reproduce this side-effect. The harness owns context-pressure exposure via `GET /agents/{role}/health`. No implementer carve-out is permitted.
- **Verification**: trace log shows no write/create events under any traced path. Assertion is unconditional.

### TC-N5 — Panel handles harness HTTP error responses without crashing (review F3)
- **Precondition**: Mock harness reachable on the configured port but configured to return error responses for each sub-case.
- **Steps**: For each sub-case, run the panel for 15s against the mock and capture stdout/stderr:
  - (a) Mock returns HTTP 500 Internal Server Error on `/agents`.
  - (b) Mock returns HTTP 404 on `/agents` (endpoint missing).
  - (c) Mock returns HTTP 200 with a JSON body that does NOT contain the expected `agents` key (e.g. `{}` or `{"unexpected": []}`).
  - (d) Mock returns HTTP 200 with valid shape, but per-agent records are missing expected fields (e.g. `status` present but `bootup_complete` absent).
  - (e) Mock returns malformed JSON (e.g. `<html>` or truncated body).
- **Expected**: In every sub-case the panel (1) does NOT crash, (2) renders a degraded indicator distinguishable from healthy, (3) continues to refresh on the next cadence tick, (4) for sub-case (d), renders whichever fields ARE present and treats missing fields as unknown/absent.
- **Verification**: assert process alive at end of each sub-case; assert no unhandled traceback in stderr; assert degraded marker in stdout for (a), (b), (c), (e); for (d) assert available fields render and missing fields show an unknown indicator (not crash).

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

### TC-T4 — State changes propagate to both panels with decoupled latency bounds (A8, review F7)
- **Precondition**: An agent transitions an issue to a `pending-human-*`
  status (which causes both the status-panel's agent-state and the
  human-queue panel's queue to change). Note: `GET /human/queue` is cached briefly (5–10s per CONTEXT §5.6) — the human-queue panel's propagation latency therefore differs from the status panel's.
- **Steps**: Trigger the transition; sample both panel outputs at fine granularity for at least 20s.
- **Expected** (decoupled per panel):
  - **Status panel** reflects the agent's phase change within **≤ 2 × refresh interval** (= ≤ 10s at the locked 5s cadence).
  - **Human-queue panel** reflects the new pending-human item within **≤ 2 × refresh interval + `/human/queue` cache TTL** (= ≤ 10s + 10s = ≤ 20s worst case).
  - The previous "same render window or adjacent windows" expectation is removed — the cache TTL makes that assertion infeasible without cache invalidation on state transitions (which is not required by the AC).

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
4. **`context-pressure` writes — LOCKED**: the new panel MUST NOT write `.squidsquad/<role>/context-pressure`. Harness owns context-pressure exposure via `GET /agents/{role}/health`. TC-N4 asserts this unconditionally.
5. **~~Refresh interval source~~ — CLOSED (PM Gap 4)**: hard-coded 5s default, no config knob in v1. TC-U4 asserts 6 requests in 30s ± 1.
6. **~~TUI panel host process~~ — CLOSED (PM Gap 1)**: TUI runs as a separate process consuming harness HTTP endpoints, NOT in-process inside `harness.py`. CONTEXT §5.7 updated. TC-I4 and §7 cross-task tests rely on this model.

---

## Document History

- 2026-05-17 — Initial draft (PM). Based on CONTEXT.md §5.4, §5.7, §6.3,
  §11. References `references/statusline.sh` for file-based baseline
  parity, `references/scripts/harness.py:579-723` for the endpoints the
  panel consumes, and CONTEXT.md §5.2 for the `bootup_complete` field
  this task depends on (#8695).

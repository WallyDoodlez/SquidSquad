# #12801 Harness TUI — Story/Task decomposition (skill)

**Source of truth (interface CONTRACT):** `.squidsquad/pm/planning/TUI-INTERFACE-DESIGN.md` (operator-APPROVED 2026-06-19). This doc is the executable breakdown; the contract is the spec. #12801 = role:skill, in-progress.

**Tech:** Textual (operator-approved dep), **separate process** consuming harness HTTP (#8704 model). NOT in-process in harness.py. Windows-first.

**Sequencing rule:** Wake button LAST, gated on #12495 (wake-injection primitive). Everything else independent.

---

## Story 1 — TUI foundation (data layer + dependency + harness `lag` backend)
**Goal:** a runnable Textual app skeleton that reads live harness state; backend exposes the data the panels need.
- **S1.1 (backend, harness.py)** — add per-agent `lag` (events-behind-head: agent cursor position vs deque head) to `GET /status` per agent. Harness owns each cursor (`.event-state.json`) + the deque, so compute lag = (#events in deque newer than the agent's cursor). Default 0 / null if cursor unknown. **Independent, small, testable — DO FIRST.** Tests: test_harness `/status` includes `lag`; lag math (caught-up=0, N-behind=N, evicted/null cursor handled).
- **S1.2 (data layer)** — a TUI-side harness client module (e.g. `references/tui/harness_client.py`): polls `GET /status`, `GET /human/queue` (#8704), activity feed. Pure data fns (testable without Textual). Tests: parse /status into agent rows, work-state derivation (working/idle/down from current_cycle/in_flight_until/intent), lag→bar mapping.
- **S1.3 (app skeleton)** — Textual `App` (e.g. `references/tui/app.py` + entry script): title bar `🦑 SquidSquad · <project>`, refresh loop, empty panel placeholders. Project name source = config.md/repo identifier.
- **S1.4 (dependency wiring)** — add `textual` to requirements + installer-files.txt + start scripts. **AC: installer-files updated (NEW files added under references/tui/ → must be listed).**

## Story 2 — Panels + branding
- Agents panel: per-agent row (role, work-state w/ color GREEN=working/YELLOW=idle/RED=down, mode, current task, last-activity age, health) + **cursor-lag bar** `[----→-]` (dashed track, → arrow; right=caught up; RED left dashes when far behind, ~left third threshold; scale ~10).
- Needs You panel (pending-human-* from /human/queue, display-only).
- Pipeline panel (in-progress/pending-test/pending-ship counts).
- Activity panel (recent events/commits feed).
- No persistent legend (state word+color self-describing).
- Tests: work-state→color, lag→bar rendering incl. RED-left-edge threshold.

## Story 3 — Action bar + Options + hotkey (the #12801 AC core)
- Action bar: **Reboot** (selected agent), **Reboot All**, **Force** (override busy, confirmed modal). Via harness lifecycle/intent state machine (NOT raw kill): graceful = intent `stopping` → agent checkpoints working-state at task boundary → restart; force = restart immediately.
- **Busy-aware**: derive from /status current_cycle / in_flight_until / intent; surface before reboot (AC3).
- **Force ≠ crash**: must NOT increment #12244 crash-streak/fast-death backoff (operator-initiated). Verify the lifecycle call path used (reboot_agent.py / harness restart endpoint) supports an operator-initiated flag that bypasses crash accounting — **may need a small harness/reboot_agent change** (confirm; design-route to PM only if force-semantics need an arch decision).
- Force = distinct confirmed action (AC5) — modal names agent, shows WORKING + in-flight time, warns immediate + not-a-crash.
- Options menu (⚙): first item Change background (Textual theming/CSS); extensible.
- Bring-PM-Forward hotkey: foreground PM's terminal window via tracked `terminal_pid` (OS window-mgmt, Windows-first).
- Maps to #12801 AC1-AC7. Tests: action dispatch, busy-detection, graceful-vs-force path, force-not-a-crash.

## Story 4 — Wake button (GATED on #12495)
- Wake a stuck-but-alive agent without a status transition (#12495 wake-injection primitive). Stub disabled until #12495 lands.

## Doc honesty (#12801 AC8)
- Update HARNESS-ARCH if the TUI/lifecycle contract changes (e.g. `lag` field on /status; force-reboot-not-a-crash semantics). PM owns HARNESS-ARCH but per worker-owns-code-with-doc-implications, file/coordinate.

## Cross-cutting
- **NEW source tree** `references/tui/` → all files must be added to installer-files.txt (AC: this project's consumption-path rule).
- Branch: squidsquad/task/12801. State (any composed) → main; code → branch.
- DS-review per logical Story (high-ish blast radius: harness /status change + lifecycle calls).

## Execution order (context-recycle friendly — each Story a clean unit)
S1.1 (lag backend, smallest/independent) → S1.2 → S1.3 → S1.4 → Story2 → Story3 → Story4(gated).

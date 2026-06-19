# Harness TUI — Interface Design (WIP, design-first)

**Status:** In design with operator (2026-06-19). Tracks #12801 (status:planning, role:pm). Build PAUSED until this design is agreed, then handed to skill. Supersedes the narrow "bottom action bar" scope of #12801.

**Prior context:** #8704 shipped backend endpoints only (`GET /human/queue`, etc.); a full TUI was an explicit non-goal there (deferred to #3963 web UI). No TUI code exists. #3963 (web UI) is a parallel future surface, not this. #9895 (TUI ack-viz) can layer on later.

## Purpose

Operator's single console to: (1) **see** the whole squad at a glance, (2) **control** it (reboot/wake), (3) **see what needs the operator** (human-decision queue). Acting on (3) is delegated to PM (see Bring-PM-Forward), not done inline in the TUI.

## Tech basis

- **Textual** (PM choice, operator-approved dependency) — async-native (fits asyncio harness), interactive, best-in-class Python TUI.
- **Separate process** consuming harness HTTP endpoints (the #8704 model) — NOT in-process in harness.py.

## Panels (v1)

### Agents panel
Live per-agent row: role, status, intent, mode (event/polling), current task, busy/idle, last-activity age, health. **Plus a per-agent cursor progress bar (see below).**

### Cursor lag bar (operator-requested 2026-06-19; visual refined)
Per-agent visual of how caught-up that agent's event cursor is vs the head of the event stream.
- **Visual: a dashed track with an arrow (`→`) marking cursor position.** No "cursor" text label (save horizontal space). E.g. `[------→]`.
- **Arrow at the right edge = cursor at the head (caught up).** Arrow slides LEFT as it falls behind: `[-→-----]` = far behind.
- Scale ~10 events (illustrative default; implementer may refine). Lag ≥ scale → arrow at far left; lag 0 → arrow at far right.
- Renders inline in each Agents-panel row (no column header needed).
- **Backend need:** harness must expose per-agent lag (cursor position vs deque head) — e.g. add `lag` (events-behind-head) to `/status` per agent. Harness already owns each cursor (`.event-state.json`) + the deque, so this is a small add. (Skill scope.)

### Needs You panel
Live list of `pending-human-*` items (the human-decision queue) — display only. Sourced from #8704's `/human/queue`. This is the operator's "what needs me" view. Acting on an item = Bring-PM-Forward hotkey → talk to PM.

### Pipeline panel
Counts: in-progress / pending-test / pending-ship.

### Activity panel
Live recent events / commits feed.

## Action bar (v1)
- **Reboot** (one selected agent), **Reboot All**, **Force** (override busy guard — confirmed; must NOT count as a crash / increment fast-death), via the harness lifecycle (intent state machine), not ad-hoc kills.
- **Wake** — the #12495 wake-injection / babysitting primitive (wake a stuck-but-alive agent without a status transition).
- Busy-aware: use `/status` `current_cycle` / `in_flight_until` / `intent` for the busy indicator before reboot.

## Hotkeys
- **Bring PM Forward (operator-requested 2026-06-19):** a hotkey that foregrounds PM's terminal window so the operator jumps straight into the inline human↔PM conversation (for answering human-tickets / decisions). Feasible: harness tracks each agent's `terminal_pid`; foreground PM's window by that handle (OS window-management; Windows-first).

## Explicitly OUT of v1
- **Inline "Answer a human-ticket"** — dropped (too complex). Answering stays fully interactive with PM via Bring-PM-Forward.
- Web UI (#3963), TUI ack-viz (#9895) — separate/later.

## Open / to-confirm with operator
- Primary-job ranking (monitoring vs control vs needs-you) → drives layout emphasis.
- Final panel set + layout proportions.
- Whether Wake is v1 or fast-follow.

## Hand-off plan
Once agreed → this doc is the interface contract; route #12801 back to skill (role:skill, approved) to build. Skill decomposes (per TRD→PRD→Stories→Tasks): Story1 TUI foundation + harness `lag` endpoint + data layer; Story2 panels; Story3 action bar + Wake; Story4 Bring-PM-Forward hotkey.

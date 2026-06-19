# Harness TUI — Interface Design (WIP, design-first)

**Status:** ✅ APPROVED by operator (2026-06-19) — ready to build. This doc is the interface CONTRACT for #12801; #12801 → role:skill, status:approved. Supersedes the narrow "bottom action bar" scope of #12801.

**Prior context:** #8704 shipped backend endpoints only (`GET /human/queue`, etc.); a full TUI was an explicit non-goal there (deferred to #3963 web UI). No TUI code exists. #3963 (web UI) is a parallel future surface, not this. #9895 (TUI ack-viz) can layer on later.

## Purpose

Operator's single console to: (1) **see** the whole squad at a glance, (2) **control** it (reboot/wake), (3) **see what needs the operator** (human-decision queue). Acting on (3) is delegated to PM (see Bring-PM-Forward), not done inline in the TUI.

## Tech basis

- **Textual** (PM choice, operator-approved dependency) — async-native (fits asyncio harness), interactive, best-in-class Python TUI.
- **Separate process** consuming harness HTTP endpoints (the #8704 model) — NOT in-process in harness.py.

## Branding & chrome (operator-requested 2026-06-19)

- **Title bar** at the top: `🦑 SquidSquad · <project-name>`.
  - **🦑 squid icon** used here and anywhere else it fits suitably (About screen, headers, loading) — brand presence without clutter.
  - **"SquidSquad"** name always shown.
  - **Project / team name** shown next to it — so a user running MULTIPLE TUIs (one per team/project) can identify which team this window belongs to. Source: project/repo identifier (e.g. from `config.md` / repo name; implementer picks the canonical source).

## Options menu (operator-requested 2026-06-19)

- An **⚙ Options menu** (hotkey + clickable), extensible.
- **First option: Change background** — change the TUI background (theme / background color). Textual's theming/CSS supports this; build it so more options can be added later.

## Panels (v1)

### Agents panel
Live per-agent row: role, **work-state** (see vocabulary), mode (event/polling), current task, last-activity age, health. **Plus a per-agent cursor lag bar (see below).**

### Work-state vocabulary + color semantics (operator-locked 2026-06-19)
One clean activity vocabulary (resolves the earlier mockup ambiguity — "active" and "busy" were two words for the same thing; collapsed into "working"):
- **working** = a cycle/task is in flight (`/status` `current_cycle` set / `in_flight_until` future / recent activity). **Color: GREEN.** (Merges old "busy"/"active".)
- **idle** = alive but nothing in progress (waiting on events / in cooldown). **Color: YELLOW.**
- **down** = dead / paused / crashed / unresponsive. **Color: RED.**
- Rule of thumb the operator wants: **GREEN means they are working.**
- **No persistent on-screen legend** (operator 2026-06-19): the state word ("working"/"idle"/"down") + its color are self-describing, so a legend line is redundant — omit it. (A one-time help/About screen may explain the cursor-lag bar if needed, but nothing persistent.)

### Cursor lag bar (operator-requested 2026-06-19; visual refined)
Per-agent visual of how caught-up that agent's event cursor is vs the head of the event stream.
- **Visual: a dashed track with an arrow (`→`) marking cursor position.** No "cursor" text label (save horizontal space). E.g. `[------→]`.
- **Arrow at the right edge = cursor at the head (caught up).** Arrow slides LEFT as it falls behind: `[-→-----]` = far behind.
- Scale ~10 events (illustrative default; implementer may refine). Lag ≥ scale → arrow at far left; lag 0 → arrow at far right.
- **Color: when the cursor is far behind (arrow near the left edge), the LEFT-edge dashes turn RED** — a lag alert. A red bar on an otherwise-GREEN (working) agent = "working but falling behind on its event stream." (Threshold for "far behind" = implementer default, ~left third.)
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
- **Options** (`⚙`) — opens the Options menu (Change background, …).

## Explicitly OUT of v1
- **Inline "Answer a human-ticket"** — dropped (too complex). Answering stays fully interactive with PM via Bring-PM-Forward.
- Web UI (#3963), TUI ack-viz (#9895) — separate/later.

## Resolved (operator 2026-06-19)
- **Primary job:** no hard ranking — balanced layout as drawn (monitor + control + needs-you all first-class).
- **Panel set + layout:** as designed (title bar, Agents, Needs You, Pipeline, Activity, action bar, Options menu).
- **Wake button:** v1, BUT **depends on #12495** (the wake-injection/work-assign primitive). Sequence the Wake button after #12495 lands (or stub it disabled until then). All other action-bar buttons (Reboot/Reboot All/Force) have no such dependency.
- **No persistent legend** (state word + color are self-describing).

## Mockups (visual contract)

Main dashboard (healthy):
```
🦑 SquidSquad · <project>                                     [ ⚙ Options ]
╭─ Agents ───────────────────────────────────╮╭─ Needs You ──────────────╮
│ skill   ● working   #12801   2m   [----→-]  ││ ⚠ #10837  sequence PRDs  │
│ qa      ● idle      —        0m   [-----→]  ││ ⚠ #10838  sequence PRDs  │
│ dm      ● idle      —        4m   [-----→]  ││                          │
│ pm      ● working   design   now  [-----→]  ││ 2 items await you        │
╰─────────────────────────────────────────────╯╰──────────────────────────╯
╭─ Pipeline ──────────────────────╮╭─ Activity ──────────────────────────╮
│ in-prog 6  pend-test 0  ship 0  ││ 21:14  skill  #12511 merged         │
│                                  ││ 21:09  pm     #12801 design update  │
╰──────────────────────────────────╯╰──────────────────────────────────────╯
 [ Reboot ]   [ Reboot All ]   [ Force ]   [ Wake ]       [P] PM   [⚙] Options
```
Trouble (qa down + lagging — red): qa row RED (down); qa/skill cursor bars show RED left dashes (far behind).
Force-reboot confirm modal (busy-aware): names the agent, shows it's WORKING + in-flight time, warns force is immediate and does NOT count as a crash; [Cancel] / [Force reboot].
Options menu: ⚙ panel, first item "Change background", extensible.

## Hand-off (DONE 2026-06-19)
This doc is the interface contract. #12801 → role:skill, status:approved. Skill decomposes (per TRD→PRD→Stories→Tasks): Story1 TUI foundation (Textual app + harness-HTTP data layer + harness `lag` endpoint + dependency wiring) → Story2 panels (Agents incl. cursor-lag bar + work-state colors, Needs You, Pipeline, Activity) + title-bar branding → Story3 action bar (Reboot/Reboot All/Force, busy-aware) + Options menu (Change background) + Bring-PM-Forward hotkey → Story4 Wake button (gated on #12495).

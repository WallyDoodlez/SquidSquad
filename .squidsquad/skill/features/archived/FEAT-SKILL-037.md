## FEAT-SKILL-037 — Show current Ralph Loop step in status bar line 2

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: Display the agent's current Ralph Loop step in the status bar's second line. Currently line 2 shows agent health icons and rest nudge, but not what the agent is actively doing. Adding the current step (e.g. "Step 3 — QA Check", "Step 5 — Verify Bugs") would give the human real-time visibility into each agent's progress without needing to read scrollback.
- **Rationale**: When multiple agents are running, the human can't tell at a glance what each agent is doing. The `[🦑]` step markers scroll by in the terminal output, but the status bar is always visible. Showing the current step there gives persistent visibility.
- **Acceptance Criteria**:
  - [ ] Agent writes current state to `.squidsquad/<role>/current-state` on each phase/step change (step name, phase, state flags)
  - [ ] `statusline.sh` reads THIS agent's current-state file and displays active step on line 2
  - [ ] Active step format: emoji + description (e.g. "🔨 Planning for FEAT-SKILL-033..."), truncated at 60 chars with "..."
  - [ ] Health icons moved from line 2 to line 1 (right-aligned) — line 2 fully dedicated to step/hint
  - [ ] Boot scripts clear current-state on startup (`rm -f`) and agent writes "Initializing..." as first action
  - [ ] When no active step, line 2 shows rotating contextual HINTS
  - [ ] Hints are human-facing friendly prompts (not metric dumps) — e.g. "Msg me any time to talk about a feature"
  - [ ] Hints rotate every 60 seconds (timestamp modulo), phase-aware
  - [ ] Each role has its own hint pool; each phase within a role has its own sub-pool
  - [ ] Hint selection is state-driven — current-state file provides enough granularity for hints to make sense
  - [ ] Hint pools defined in templates (`references/`) — copied during setup, not hardcoded in statusline.sh
  - [ ] `statusline.sh` reads hint pools and current-state, picks the matching pool, rotates through it
  - [ ] Falls back gracefully if current-state file is missing or empty
  - [ ] CLAUDE.md templates updated to write current state at each `[🦑]` marker
  - [ ] SKILL.md templates and references updated
  - [ ] All roles covered (PM, dev agents, future DM)

### Discussion

> [2026-03-29 13:57] **pm/qa**: Filed from human request. Human wants real-time step visibility in the status bar. Approach: agents write current step to a file, statusline.sh reads it. Status: Pending — awaiting human approval.
> [2026-03-29 14:20] **pm/qa**: Human clarified: show current step of THIS agent only (not all agents). Format: emoji + description, e.g. "🔨 Planning for FEAT-SKILL-033..." — truncate with "..." if too long. Also wants contextual HINTS on line 2 when idle (role-specific). Updating acceptance criteria to reflect.
> [2026-03-29 14:40] **pm/qa**: Human clarified hints further: hints are for HUMANS, not system status. They should be friendly prompts reminding the human what they can do — e.g. "Msg me any time to talk about a feature". NOT metric dumps like "3 bugs open". Think of them as gentle nudges to interact. Updated acceptance criteria.
> [2026-03-29 15:10] **pm/qa**: Human clarified hint behavior: (1) hints ROTATE each cycle, not static, (2) each role AND each phase has its own hint pool, (3) state-driven — hint selection considers current state, (4) shell-driven — statusline.sh handles all hint logic, not the agent. Open questions: rotation mechanism (minute-based modulo vs counter file), performance of reading tracker state in shell, hint pools hardcoded in script vs config file, granularity of state awareness for hint selection.
> [2026-03-29 15:15] **pm/qa**: Human resolved open questions: (1) Agents write state to file on each phase change — statusline.sh reads it (no tracker parsing in shell). (2) Hint pools live in templates (references/) — copied during setup. (3) Enough granularity in the state file so hints always make sense for what's happening. Architecture: agent writes `.squidsquad/<role>/current-state` → statusline.sh reads state + hint pool file → picks matching pool → rotates via timestamp modulo. Updated acceptance criteria.
> [2026-03-29 16:00] **pm/qa**: Human approved. FEAT-SKILL-036 put on hold (wt dependency not wanted). Status → Planning. Beginning intake process.
> [2026-03-29 16:25] **pm/qa**: Phase 2 complete. All 5 decisions locked: (D1) health icons → line 1 right-aligned, (D2) hints rotate every 60s phase-aware, (D3) 60 chars truncation all roles, (D4) DM hints deferred, (D5) boot clear + Initializing write. RESEARCH.md, CONTEXT.md, TEST-PLAN.md created. Status → Approved.

> [2026-03-29 16:30] **skill-lead**: Picking up. Status → In Progress.

> [2026-03-29 16:45] **skill-lead**: Complete. Created `references/hints-dev.txt` and `references/hints-pm.txt` hint pool files. Updated `references/agent-instructions.md` with current-state writing protocol for both dev and PM templates. Rewrote `references/statusline.sh`: health icons moved to PM line 1 (right-aligned), line 2 shows current step from `current-state` file or rotating phase-aware hints from hint pools (60s rotation via timestamp modulo, 60 char truncation). Updated boot script templates in SKILL.md to clear and initialize `current-state` on startup. Added Step 5d for hint file copying during setup. Added `current-state` to `.gitignore`. Updated upgrade flow, CHANGELOG.md, README.md. Status → Pending Test.
> [2026-03-29 17:00] **pm/qa**: Verified all acceptance criteria. statusline.sh: current-state read (L98-105), get_line2 function with 60-char truncation (L114), 60s rotation (L156), phase-aware with idle fallback (L141). Health icons on PM line 1 (L240). Boot scripts clear+initialize in all 4 templates. Hint pools in references/ with pipe-delimited format (dev discretion — simpler than @section). .gitignore updated. agent-instructions.md both templates have state write protocol. CHANGELOG, README, SKILL.md all updated. Note: state file uses 2-field format (phase|desc) instead of 3-field (timestamp|step|desc) from research — acceptable, staleness handled by heartbeat system. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).

# FEAT-SKILL-037 Research — Status Bar Step Display + Rotating Hints

## Summary

This feature adds two new behaviors to status bar line 2: (1) when an agent is actively working, line 2 shows the current Ralph Loop step as an emoji + description (e.g. "Triaging bugs..."), and (2) when idle or between steps, line 2 shows rotating human-facing hints that cycle via timestamp modulo. The implementation touches three main systems: agent instruction templates (which write `current-state`), `statusline.sh` (which reads it and selects hints), and a new hint pool file format in `references/`.

The feature is architecturally straightforward. Agents already print `[squid]` step markers to stdout at each phase transition. The new requirement is to also write this state to a file that `statusline.sh` can read. The main complexity lies in defining a clean state file format, a hint pool format that is efficient for bash to parse, and handling the various edge cases (stale files, missing files, race conditions). The PM line 2 currently shows health icons + rest nudge; this content must be merged with or replaced by the new step display.

Risk is moderate. The state file write adds one file write per step change (cheap). The hint pool read adds one file read per statusline refresh (cheap). The main risks are stale state after crashes, the need to coordinate changes across three reference files, and ensuring the upgrade path regenerates all affected files cleanly.

## Impact Analysis

- **Files touched**:
  - `references/statusline.sh` — add current-state reading, hint pool reading, line 2 logic for both PM and dev agents
  - `references/agent-instructions.md` — Template 1 (Dev Agent) and Template 2 (PM/QA): add `current-state` file writes at each `[squid]` step marker, define the file format, add clear-on-idle
  - `references/hints-pm.txt` (NEW) — PM hint pool file
  - `references/hints-dev.txt` (NEW) — dev agent hint pool file
  - `SKILL.md` — document new files in structure diagram, add hint pool files to setup Step 4 copy list, add to upgrade agent scope
  - `.gitignore` — add `current-state` files (runtime ephemeral, should not be committed)
  - `.squidsquad/config.md` — no changes needed (no new config knobs required; hint behavior is self-contained)

- **Behavior changes**:
  - **PM line 2 currently**: `  [health-icons]                                    [rest-nudge]` — health icons (squid/ghost/egg per agent) plus optional rest nudge right-aligned
  - **PM line 2 after**: when active step exists: `[emoji] [step description]  [health-icons]  [rest-nudge]` — step display takes priority, health icons shift right; when no active step: rotating hint replaces the blank space before health icons
  - **Dev agents currently**: single-line status bar (no line 2)
  - **Dev agents after**: line 2 added showing current step when active, rotating hint when idle
  - Agent instruction templates gain a new file write obligation at each step marker

- **Dependencies**:
  - Heartbeat system (FEAT-SKILL-033) — `statusline.sh` already reads heartbeat branches for health icons; no conflict, but the health icons on PM line 2 need layout coordination
  - Context pressure exit — agent writes "exiting" to current-state before exit; statusline reads it
  - Working state file (`working-state.md`) — conceptually related but separate; current-state is ephemeral/lightweight, working-state is persistent/detailed

## Side Effects

- **PM line 2 layout change** — Severity: L — Mitigation: Keep health icons and rest nudge. Prepend the step/hint text before them. If the combined line is too long, truncate the step description (not the health icons). Health icons are compact (one emoji per agent) so there is room.

- **Extra file I/O per statusline refresh** — Severity: L — Mitigation: Reading a tiny file (< 100 bytes) and a hint pool file (< 2KB) is negligible. `statusline.sh` already reads config.md, working-state.md, multiple iteration files, and runs git commands. Two small `cat` operations are invisible in comparison.

- **State file in shared `.squidsquad/` directory** — Severity: L — Mitigation: Each agent's state file lives at `.squidsquad/<role>/current-state`, and `statusline.sh` reads only `$SQDIR/$ROLE/current-state` (the THIS agent's file, using the role from `.active-role`). No cross-agent state file reads are needed for this feature. PM reads its own; dev reads its own. No conflict.

- **Git noise from current-state files** — Severity: M — Mitigation: Add `.squidsquad/*/current-state` to `.gitignore`. These files are ephemeral runtime state, not project data. They change every few seconds and would create constant merge conflicts if committed. The `.active-role` file is already gitignored for the same reason.

- **Agent instruction template size increase** — Severity: L — Mitigation: Each step marker already exists as a `Print:` line. Adding a file write line below each is ~1 line of instruction per step. Total template growth is modest (~20-30 lines across 10+ steps).

## Edge Cases

- **Agent crashes mid-step — stale current-state file**: The file will contain the last step written before the crash. On next statusline refresh, it will show a stale step. Mitigation: include a timestamp in the state file. `statusline.sh` can compare the timestamp against a staleness threshold (e.g., 2x the loop interval). If stale, treat as "no active step" and show hints instead. The heartbeat system already detects stalled agents, so a stale current-state is a secondary signal.

- **Empty/missing current-state file on first boot**: `statusline.sh` must handle this gracefully. If the file does not exist or is empty, fall through to hint display. This is the default state before the agent writes anything. The `[ -f ... ] && [ -s ... ]` pattern used elsewhere in `statusline.sh` handles this naturally.

- **Very long step descriptions (truncation)**: Step descriptions like "Implementing FEAT-SKILL-033 — Heartbeat system with background orphan branch pushes..." could exceed terminal width. Mitigation: `statusline.sh` truncates the display string to a max width (e.g., 60 chars) and appends "..." if truncated. The acceptance criteria already specify this behavior.

- **Hint pool file missing or malformed**: If the hint pool file does not exist (e.g., failed upgrade, deleted by user), `statusline.sh` should fall back to a single hardcoded default hint like "Drop a message any time" or simply show nothing on line 2. A missing file must not cause `statusline.sh` to error out or produce broken output.

- **Race condition: agent writes state while statusline reads it**: On most filesystems, small file writes (< 4KB) to a single file are atomic at the OS level. The state file is tiny (< 100 bytes). Even if a partial read occurs, the worst case is a garbled line for one refresh cycle — corrected on the next refresh (a few seconds later). No locking is needed. For extra safety, the agent can write to a temp file and `mv` it into place (atomic rename), but this is likely overkill.

- **Multiple agents running simultaneously**: Each writes to its own `<role>/current-state` path. No collision. The statusline only reads the current role's file.

## Integration Risks

- **Heartbeat system (FEAT-SKILL-033)**: No conflict. Heartbeat runs as a background process in the boot script, completely independent of the agent's Ralph Loop. The heartbeat writes to git branches; current-state writes to a local file. `statusline.sh` reads both independently — heartbeat for health icons, current-state for step display. Layout coordination on PM line 2 is needed to fit both health icons and step display.

- **Context pressure exit**: When an agent hits the context pressure threshold, it saves working state, commits, and exits. At this point the current-state file should be updated to reflect "exiting" or cleared. If not cleared, the stale-timestamp detection handles it. Recommendation: the agent should write a final state like `exiting|Context pressure exit` before stopping, and `statusline.sh` can display this (e.g., "Context pressure — restarting...").

- **Quiet cycle skipping**: During quiet cycles, the agent skips logging and committing. The step markers still fire (Steps 1-3 run, they just find nothing to do). The current-state file will briefly show each step as the agent scans through them, then return to idle. This is correct behavior — the human sees the agent is alive and scanning even during quiet cycles.

- **Delivery Manager role (FEAT-SKILL-035)**: DM is a future role that would also need a hint pool. The hint pool system should be role-generic (one file per role in `references/`), so adding `references/hints-dm.txt` later is trivial. The state file format is already per-role.

## State File Format (Proposed)

**Location**: `.squidsquad/<role>/current-state`

**Format**: Single line, pipe-delimited, no header. Designed for trivial bash parsing with `IFS='|' read`.

```
<unix_timestamp>|<step_id>|<display_text>
```

**Fields**:
- `unix_timestamp` — epoch seconds when this state was written (`date +%s`)
- `step_id` — machine-readable step identifier for hint pool matching (e.g., `step1`, `step2`, `step3`, `step1b`, `step6c`, `idle`, `exiting`)
- `display_text` — human-readable text to show on line 2, already formatted with emoji (e.g., `Pulling latest...`, `Triaging bugs...`, `Implementing FEAT-SKILL-033...`)

**Examples**:
```
1711734000|step2|Triaging bugs...
1711734060|step3|Implementing FEAT-SKILL-033...
1711734120|step1b|Checking context pressure...
1711734180|idle|
1711734200|exiting|Context pressure — restarting...
```

**Why this format**:
- Single line = one `read` call in bash, no loops
- Pipe delimiter is safe (no pipes in step descriptions)
- Timestamp enables staleness detection without `stat`
- Step ID enables hint pool sub-pool matching
- Display text is pre-formatted by the agent (statusline does not need to map step IDs to descriptions)
- Empty display text (idle) signals hint mode

**Agent write pattern** (added to templates):
```bash
echo "$(date +%s)|step2|Triaging bugs..." > .squidsquad/[ROLE]/current-state
```

One line per step marker. At cycle end:
```bash
echo "$(date +%s)|idle|" > .squidsquad/[ROLE]/current-state
```

## Hint Pool Format (Proposed)

**Location**: `references/hints-<role>.txt` (e.g., `references/hints-pm.txt`, `references/hints-dev.txt`)

Copied during setup to `.squidsquad/templates/hints-<role>.txt`. Statusline reads from `.squidsquad/templates/`.

**Format**: Plain text, one hint per line. Lines starting with `#` are comments. Lines starting with `@` are section headers (sub-pool markers). Blank lines are ignored.

```
# PM hints — general pool (used when step_id is "idle" or no section matches)
Drop a message any time to talk about a feature idea
Ask me to prioritize — I'll reorder the backlog
Want a status update? Just ask
I check in with you every cycle — no need to wait

# PM hints — during QA steps (step5, step6, step6b)
@qa
I'm testing right now — results coming soon
Found something broken? Drop it here, I'll file the bug
QA in progress — I'll report back shortly

# PM hints — during planning (step2)
@planning
Working on feature planning — questions coming your way soon
I might ask you some questions about this feature shortly
```

**Parsing logic in `statusline.sh`**:
```bash
HINT_FILE="$SQDIR/templates/hints-${HINT_ROLE}.txt"
if [ -f "$HINT_FILE" ]; then
  # Find matching section, fall back to general pool
  # Use awk to extract lines for the matching @section (or general if no match)
  # Then pick one line via: (timestamp / cycle_seconds) % line_count
  HINTS=$(awk -v section="$STEP_ID" '...' "$HINT_FILE")
  # Rotate selection
  HINT_COUNT=$(echo "$HINTS" | wc -l)
  if [ "$HINT_COUNT" -gt 0 ]; then
    INDEX=$(( (NOW / (INTERVAL * 60)) % HINT_COUNT ))
    HINT=$(echo "$HINTS" | sed -n "$((INDEX + 1))p")
  fi
fi
```

**Section matching rules**:
- `@qa` matches step IDs: `step5`, `step6`, `step6b`, `step6c`
- `@planning` matches: `step2` (PM human check-in)
- `@health` matches: `step7`, `step7b`
- Lines before any `@` section are the general/default pool
- If the current step_id does not match any `@` section, use the general pool
- Dev agent hint files use similar sections: `@bugs` (step2), `@features` (step3), `@testing` (step4)

**Why this format**:
- Plain text is trivial to edit for humans
- One hint per line avoids parsing complexity
- `@section` headers are simple for awk/grep to match
- No JSON, no YAML — bash-native parsing with standard tools
- Comment lines allow documentation inline

## Upgrade & Migration

**Upgrade path** (via `/squidsquad-upgrade`):

1. **New reference files**: `references/hints-pm.txt` and `references/hints-dev.txt` are added to the skill repo. The upgrade "settings agent" already regenerates `statusline.sh` from `references/`; it needs to also copy hint pool files to `.squidsquad/templates/`.

2. **Template regeneration**: The upgrade agents for dev roles and PM/QA already regenerate templates from `references/agent-instructions.md`. Once the template source includes the current-state write instructions, upgraded templates will have them automatically.

3. **Statusline regeneration**: The settings upgrade agent already copies `references/statusline.sh` to `.squidsquad/statusline.sh`. The new statusline logic will be included automatically.

4. **Gitignore update**: The upgrade should append `.squidsquad/*/current-state` to `.gitignore` if not already present. This is a one-line addition.

5. **No config.md changes needed**: No new config keys are required. Hint behavior is self-contained in the hint pool files and statusline logic.

6. **No schema migration**: This feature adds new files but does not change tracker formats.

7. **Backward compatibility**: If `current-state` does not exist (pre-upgrade agent still running), `statusline.sh` falls through to hints. If hint pool files do not exist (partial upgrade), statusline shows nothing extra on line 2 — same as current behavior. No breakage.

**What users see after upgrade**: Line 2 will start showing hints immediately (since no current-state file exists yet). Once agents are restarted with the new templates, line 2 will show active steps during work and hints during idle periods.

## Open Questions

- **Q1**: Should the PM line 2 health icons move or stay in place when step text is shown? — **Why**: If health icons shift position depending on step text length, it creates visual jitter. If they stay right-aligned, the step text needs a max width to avoid overlap.

- **Q2**: Should hints rotate on every statusline refresh or only on cycle boundaries? — **Why**: The statusline refreshes after every assistant message (could be multiple times per second during active work). Rotating on every refresh would flash hints too fast. Rotating on cycle boundaries (using `INTERVAL * 60` as the modulo divisor) gives stable hints that change every N minutes. The acceptance criteria say "rotate each cycle" which suggests cycle-boundary rotation.

- **Q3**: What is the maximum character width for step descriptions before truncation? — **Why**: Terminal widths vary. A safe default might be 50-60 characters for the step text portion, but this depends on how much other content is on line 2 (health icons, rest nudge). PM line 2 has more content than dev line 2.

- **Q4**: Should the DM role (FEAT-SKILL-035) get its own hint pool now or later? — **Why**: DM is filed but not yet approved. Creating `references/hints-dm.txt` now avoids a second upgrade cycle, but the DM role's steps are not yet defined, so hints would be speculative. Recommendation: defer until DM ships.

- **Q5**: Should current-state files be cleared when the boot script starts (before the agent launches)? — **Why**: If an agent crashed and left a stale current-state, the next boot could briefly show the stale step before the new agent overwrites it. Clearing in the boot script avoids this. Simple: `rm -f .squidsquad/$ROLE/current-state` in `start-[role].sh`.

## Recommendation

**Feasible with caveats.** The core implementation is straightforward — file writes in templates, file reads in statusline, a new hint pool format. The caveats are:

1. **PM line 2 layout needs careful design** — merging step text + health icons + rest nudge on one line requires width budgeting and truncation logic. Recommend a fixed layout: `[step/hint] [padding] [health] [rest]` with step text truncated to fit.

2. **Staleness detection is important** — without it, a crashed agent shows a frozen step forever. The timestamp in the state file enables this cheaply.

3. **Boot script cleanup** — add `rm -f .squidsquad/$ROLE/current-state` to boot scripts to avoid stale state on restart.

4. **Upgrade path is clean** — all changed files are already in the upgrade regeneration scope. Only addition: copying hint pool files and updating `.gitignore`.

5. **Hint pool content is the creative work** — the format is trivial, but writing good, non-annoying, genuinely helpful hints for each role and phase requires thought. Recommend starting with 5-8 general hints per role and 2-3 per sub-pool, then iterating based on feedback.

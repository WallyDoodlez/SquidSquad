# FEAT-SKILL-047 Test Plan — Cross-Clone Health Detection + Guided Agent Setup

## Test Cases

### TC-1: `.local-config` created during setup with correct format
- **Precondition**: Fresh install or upgrade. No `.squidsquad/.local-config` exists.
- **Steps**:
  1. Run the setup flow (or upgrade flow).
  2. When prompted, provide absolute paths for each agent clone (e.g., `D:\Dev\SquidSquad-PM`, `/home/user/SquidSquad-Skill`).
- **Expected**:
  1. `.squidsquad/.local-config` is created.
  2. File contains a parseable structure with agent role names mapped to absolute paths.
  3. Format matches the defined spec (e.g., markdown list with `**role**: /path` or key=value).
  4. File is readable by statusline without errors.
- **Verification**: Read `.squidsquad/.local-config`. Confirm each configured agent has a role label and an absolute path. Parse the file using the same logic statusline uses and confirm it extracts correct role/path pairs.

### TC-2: `.local-config` is gitignored and never committed
- **Precondition**: `.squidsquad/.local-config` exists with agent paths.
- **Steps**:
  1. Run `git status` and check if `.local-config` appears as untracked or modified.
  2. Run `git add -A && git status --short` and check if `.local-config` is staged.
  3. Check `.gitignore` for the `.local-config` entry.
- **Expected**:
  1. `.local-config` does not appear in `git status` output.
  2. `.local-config` is not staged after `git add -A`.
  3. `.gitignore` contains an entry that covers `.squidsquad/.local-config` (e.g., `.local-config` or `.squidsquad/.local-config`).
- **Verification**: `git check-ignore .squidsquad/.local-config` returns the file (exit code 0).

### TC-3: Cross-clone health — statusline reads other agents' current-state via absolute path
- **Precondition**: `.local-config` contains paths for pm and skill agents. Both clones exist on disk. Both have `.squidsquad/<role>/current-state` files with recent writes.
- **Steps**:
  1. Write a known state to the other agent's `current-state` file (e.g., `implementing|FEAT-SKILL-047...`).
  2. Run statusline (or the relevant parsing function).
- **Expected**:
  1. Statusline reads the absolute path from `.local-config`.
  2. Statusline opens `<path>/.squidsquad/<role>/current-state` and reads it successfully.
  3. The mtime of the file is used to determine health (recent = healthy).
  4. The content of the file is displayed or used for state info.
- **Verification**: Statusline output shows the correct health icon and state for the remote agent.

### TC-4: Cross-clone health — correct mtime reading for staleness
- **Precondition**: `.local-config` has a path to another agent's clone. That agent's `current-state` exists.
- **Steps**:
  1. Touch the other agent's `current-state` so its mtime is recent (within 1x iteration interval). Observe statusline.
  2. Set the other agent's `current-state` mtime to >2x iteration interval in the past (e.g., `touch -t` on Unix or PowerShell equivalent). Observe statusline.
  3. Delete the other agent's `current-state` file. Observe statusline.
- **Expected**:
  1. Recent mtime: health icon is `🦑` (healthy).
  2. Old mtime (>2x interval): health icon is `👻` (stalled).
  3. Missing file: health icon is `❓` (unknown).
- **Verification**: Confirm each scenario produces the correct icon in statusline output.

### TC-5: Health icon thresholds — 2x iteration interval boundary
- **Precondition**: Iteration interval is set to 30 minutes in `config.md`. Another agent's `current-state` exists.
- **Steps**:
  1. Set `current-state` mtime to 59 minutes ago (just under 2x = 60 min). Run statusline.
  2. Set `current-state` mtime to 61 minutes ago (just over 2x). Run statusline.
- **Expected**:
  1. 59 minutes: `🦑` (healthy — within 2x threshold).
  2. 61 minutes: `👻` (stalled — exceeds 2x threshold).
- **Verification**: Confirm the boundary is exactly 2x iteration interval, not 3x or some other value.

### TC-6: Timer reads current-state mtime from own clone (BUG-035 regression)
- **Precondition**: Own agent's `current-state` file exists and was written at cycle end.
- **Steps**:
  1. Complete a cycle. Note the time.
  2. Wait a few minutes. Check statusline timer display.
  3. Complete another cycle (including a quiet cycle that updates `current-state`). Check timer resets.
- **Expected**:
  1. Timer shows elapsed time since last cycle based on own `current-state` mtime.
  2. Timer resets after each cycle completion (since `current-state` is re-written).
  3. Quiet cycles also reset the timer (since `current-state` is written with `idle|` at cycle end).
- **Verification**: Timer value should closely match wall-clock time since last `current-state` write.

### TC-7: Guided setup — clone repo to path, write .local-config, open terminal, run boot
- **Precondition**: User has a repo URL. No agent clone exists at the target path.
- **Steps**:
  1. Start setup flow. Choose to add a new agent (e.g., skill).
  2. When prompted for path, provide a directory path (e.g., `D:\Dev\SquidSquad-Skill`).
  3. Observe the setup flow.
- **Expected**:
  1. Setup clones the repo to the specified path (`git clone <url> <path>`).
  2. Setup writes the agent's path to `.squidsquad/.local-config`.
  3. Setup opens a new terminal at the cloned path.
  4. Setup runs the appropriate boot script in the new terminal (e.g., `start-skill.ps1` on Windows, `start-skill.sh` on Unix).
  5. The new agent begins its Ralph Loop in the new terminal.
- **Verification**: Confirm the clone exists at the specified path. Read `.local-config` and confirm the path is recorded. Confirm a new terminal opened. Confirm the agent is running (check for cycle-started markers in the new terminal).

### TC-8: Guided setup — default path suggestion
- **Precondition**: Current repo is at `D:\Dev\SquidSquad`.
- **Steps**:
  1. Start setup flow. Choose to add a new agent (e.g., pm).
  2. Observe the suggested default path.
- **Expected**:
  1. Setup suggests a sensible default path (e.g., `D:\Dev\SquidSquad-PM` or `../SquidSquad-PM`).
  2. User can accept the default or provide a custom path.
- **Verification**: Confirm the suggestion is a sibling directory or otherwise reasonable. Confirm custom paths are accepted.

### TC-9: Heartbeat removal — heartbeat.sh deleted
- **Precondition**: Implementation is complete.
- **Steps**:
  1. Check for `.squidsquad/heartbeat.sh`.
  2. Check for `references/heartbeat.sh`.
- **Expected**:
  1. Neither file exists.
- **Verification**: `ls .squidsquad/heartbeat.sh` and `ls references/heartbeat.sh` both return "No such file".

### TC-10: Heartbeat removal — boot scripts do not launch heartbeat
- **Precondition**: Implementation is complete.
- **Steps**:
  1. Read `.squidsquad/start-skill.sh`, `start-pm.sh`, `start-skill.ps1`, `start-pm.ps1`.
  2. Search for any reference to `heartbeat`.
- **Expected**:
  1. No boot script contains `heartbeat` references (no launch, no cleanup, no background process).
- **Verification**: `grep -ri heartbeat .squidsquad/start-*.sh .squidsquad/start-*.ps1` returns no matches.

### TC-11: Heartbeat removal — config has no Heartbeat Interval
- **Precondition**: Implementation is complete.
- **Steps**:
  1. Read `.squidsquad/config.md`.
  2. Search for `Heartbeat` or `heartbeat`.
- **Expected**:
  1. No `Heartbeat Interval Seconds` key exists.
  2. No `## Heartbeat` section exists.
- **Verification**: `grep -i heartbeat .squidsquad/config.md` returns no matches.

### TC-12: Graceful fallback — .local-config missing entirely
- **Precondition**: `.squidsquad/.local-config` does not exist (e.g., fresh clone, never set up).
- **Steps**:
  1. Run statusline.
- **Expected**:
  1. Statusline does not crash or error.
  2. All other agents show `❓` icon (unknown).
  3. Own agent's state/timer still works (reads own `current-state` directly).
  4. All other statusline features (overdue emoji, phase display, hints) continue to work.
- **Verification**: Statusline output renders cleanly with `❓` for agents. No error messages in output.

### TC-13: Graceful fallback — path in .local-config is unreachable
- **Precondition**: `.local-config` contains a path that does not exist on disk (e.g., `D:\Nonexistent\Path`).
- **Steps**:
  1. Run statusline.
- **Expected**:
  1. Statusline does not crash.
  2. The agent with the unreachable path shows `❓` icon.
  3. Other agents with valid paths still show correct health icons.
- **Verification**: Confirm `❓` for the bad path and correct icons for good paths.

### TC-14: Graceful fallback — current-state file missing at valid path
- **Precondition**: `.local-config` points to a valid clone directory, but `.squidsquad/<role>/current-state` does not exist in that clone (e.g., agent has never run).
- **Steps**:
  1. Run statusline.
- **Expected**:
  1. The agent with the missing `current-state` shows `❓` icon.
  2. No crash or error.
- **Verification**: Confirm `❓` icon and clean output.

### TC-15: Cross-platform — Windows (PowerShell) support
- **Precondition**: Running on Windows. `.local-config` has paths using Windows-style separators (e.g., `D:\Dev\SquidSquad-PM`).
- **Steps**:
  1. Run statusline via PowerShell boot script.
  2. Verify file reads work with Windows paths.
  3. Verify mtime reading works on Windows (NTFS timestamps).
  4. Test guided setup opens a new PowerShell terminal (`Start-Process` or equivalent).
- **Expected**:
  1. Statusline correctly reads cross-clone files using Windows absolute paths.
  2. Mtime comparison works correctly on Windows.
  3. New terminal opens via PowerShell mechanism.
  4. Boot script runs in the new terminal.
- **Verification**: Full end-to-end on a Windows machine. Health icons display correctly.

### TC-16: Cross-platform — Unix (bash) support
- **Precondition**: Running on Linux/macOS. `.local-config` has paths using Unix-style separators (e.g., `/home/user/SquidSquad-PM`).
- **Steps**:
  1. Run statusline via bash boot script.
  2. Verify file reads work with Unix paths.
  3. Verify mtime reading works on Unix (`stat` command differences between Linux and macOS).
  4. Test guided setup opens a new terminal (platform-appropriate: `gnome-terminal`, `open -a Terminal`, etc.).
- **Expected**:
  1. Statusline correctly reads cross-clone files using Unix absolute paths.
  2. Mtime comparison works correctly.
  3. New terminal opens and boot script runs.
- **Verification**: Full end-to-end on a Unix machine. Health icons display correctly.

### TC-17: Regression — existing statusline features still work
- **Precondition**: Implementation is complete. Statusline is running.
- **Steps**:
  1. Observe statusline during an active cycle — check phase display.
  2. Let timer run past the iteration interval — check overdue emoji.
  3. Set agent to idle — check rotating hints.
  4. Verify backlog pulse (bug/feature counts) still displays.
- **Expected**:
  1. Phase display shows current phase from `current-state` (e.g., `implementing`, `triaging`).
  2. Overdue emoji appears when timer exceeds iteration interval.
  3. Rotating hints display during idle periods.
  4. Backlog pulse shows correct counts from tracker files.
- **Verification**: All pre-existing statusline features work identically to before the change.

### TC-18: Upgrade path — existing install migration
- **Precondition**: Existing install with heartbeat.sh, heartbeat config, heartbeat branch references.
- **Steps**:
  1. Run upgrade flow.
  2. Check that heartbeat artifacts are removed.
  3. Check that user is prompted to create `.local-config`.
  4. Check that remote heartbeat branches are cleaned up.
- **Expected**:
  1. `heartbeat.sh` is deleted from both `.squidsquad/` and `references/`.
  2. Boot scripts are regenerated without heartbeat launch blocks.
  3. `Heartbeat Interval Seconds` is removed from `config.md`.
  4. Remote heartbeat branches are deleted (`git push origin --delete heartbeat/pm heartbeat/skill`), failing silently if they don't exist.
  5. Statusline is regenerated to use `.local-config` instead of `git fetch`.
  6. User is prompted to create `.local-config` with agent paths.
- **Verification**: Confirm all heartbeat artifacts are gone. Confirm `.local-config` creation is prompted. Confirm `git branch -r | grep heartbeat` returns nothing.

### TC-19: Upgrade path — statusline works after migration before .local-config created
- **Precondition**: Upgrade has removed heartbeat but user has not yet created `.local-config`.
- **Steps**:
  1. Run statusline after upgrade but before creating `.local-config`.
- **Expected**:
  1. Statusline does not crash (graceful fallback per TC-12).
  2. Other agents show `❓`.
  3. Own agent's timer and state still work.
- **Verification**: Clean statusline output with `❓` icons.

### TC-20: PM Step 7 reads cross-clone current-state for health check
- **Precondition**: `.local-config` exists with valid paths. Other agents are running.
- **Steps**:
  1. PM agent reaches Step 7 (health check).
  2. Observe how PM reads agent health.
- **Expected**:
  1. PM reads `.local-config` to get agent clone paths.
  2. PM reads `<path>/.squidsquad/<role>/current-state` for each agent.
  3. PM uses mtime to determine health (same thresholds as statusline).
  4. PM does NOT use `git fetch` or GitHub API for health detection.
  5. PM reports healthy/stalled/unknown status for each agent.
- **Verification**: PM iteration log or output shows health status derived from local file reads. No `git fetch origin heartbeat` in PM behavior.

### TC-21: Multiple agents in .local-config
- **Precondition**: `.local-config` has paths for pm, skill, and optionally dm.
- **Steps**:
  1. Set pm's `current-state` to recent (healthy).
  2. Set skill's `current-state` to stale (>2x interval).
  3. Set dm's path to nonexistent directory.
  4. Run statusline.
- **Expected**:
  1. pm: `🦑` (healthy).
  2. skill: `👻` (stalled).
  3. dm: `❓` (unknown/unreachable).
- **Verification**: Each agent displays the correct icon independently.

### TC-22: SKILL.md templates updated — no heartbeat references in setup/boot
- **Precondition**: Implementation is complete.
- **Steps**:
  1. Read `SKILL.md` setup instructions.
  2. Read boot script templates in `SKILL.md`.
- **Expected**:
  1. No Step 5c (Generate Heartbeat Script) in setup.
  2. No heartbeat interval prompt in setup.
  3. Boot script templates do not contain heartbeat launch blocks.
  4. Setup includes guided agent clone + `.local-config` creation flow.
- **Verification**: `grep -i heartbeat SKILL.md` returns no matches in setup/boot template sections. Setup flow references `.local-config` and guided clone.

### TC-23: References and live files updated
- **Precondition**: Implementation is complete.
- **Steps**:
  1. Check `references/agent-instructions.md` — PM Step 7 uses local file reads, not git fetch.
  2. Check `references/statusline.sh` — uses `.local-config` paths, not heartbeat branches.
  3. Check live copies match references (`.squidsquad/statusline.sh`, `.squidsquad/pm/CLAUDE.md`).
- **Expected**:
  1. `agent-instructions.md` PM Step 7 reads cross-clone `current-state` via paths from `.local-config`.
  2. `statusline.sh` parses `.local-config` and reads cross-clone files.
  3. Live copies are regenerated from references.
- **Verification**: Diff live vs reference files — they should match. No `heartbeat` references in either.

## Smoke Tests
- [ ] `.squidsquad/.local-config` is created during setup with correct format
- [ ] `.local-config` does not appear in `git status` (gitignored)
- [ ] Statusline shows `🦑` for a healthy agent (recent `current-state` mtime)
- [ ] Statusline shows `👻` for a stalled agent (>2x interval mtime)
- [ ] Statusline shows `❓` for a missing/unreachable agent
- [ ] `heartbeat.sh` does not exist in `.squidsquad/` or `references/`
- [ ] Boot scripts contain no `heartbeat` references
- [ ] `config.md` contains no `Heartbeat Interval` key
- [ ] Statusline does not crash when `.local-config` is missing
- [ ] Statusline does not crash when a configured path is unreachable
- [ ] Own agent's timer still works (reads own `current-state` mtime)
- [ ] Overdue emoji, phase display, and rotating hints still work
- [ ] Setup guided flow clones repo and writes path to `.local-config`
- [ ] Works on Windows with PowerShell paths
- [ ] Works on Unix with bash paths

## Regression Risks
- **Statusline crash on missing files**: If `.local-config` or cross-clone `current-state` is missing and error handling is insufficient, statusline crashes. Every file read must be guarded with existence checks and fallback to `❓`.
- **Windows path parsing**: Backslashes in Windows paths may break bash parsing in `statusline.sh`. Ensure paths are quoted and handled correctly in both bash and PowerShell contexts.
- **mtime platform differences**: `stat` command differs between Linux (`stat -c %Y`), macOS (`stat -f %m`), and Windows (PowerShell `(Get-Item).LastWriteTime`). Statusline must handle the platform it's running on.
- **Existing statusline features broken**: Changes to statusline.sh could accidentally break phase display, overdue emoji, backlog pulse, or rotating hints. Run full statusline regression.
- **PM health check regression**: PM Step 7 changing from git-fetch to local-file-read could break if PM doesn't have access to other clones or `.local-config` isn't present in PM's clone.
- **Boot script breakage**: Removing heartbeat launch blocks from boot scripts could accidentally remove adjacent lines (e.g., cleanup handlers, environment setup). Verify boot scripts still start agents correctly.
- **Upgrade leaves stale heartbeat branches**: If remote branch deletion fails silently (which it should), old heartbeat branches persist on remote. Not harmful but untidy. Verify cleanup runs and warn user if branches remain.
- **Timer drift after heartbeat removal**: Timer previously could use heartbeat timestamp. Now relies solely on `current-state` mtime. If `current-state` isn't written on quiet cycles, timer drifts. Ensure BUG-035 fix (write `current-state` on every cycle including quiet) is preserved.
- **Setup terminal launch failure**: Opening a new terminal is platform-specific and fragile. If it fails, the user is stuck. Setup should provide manual instructions as fallback (e.g., "open a terminal at <path> and run <script>").

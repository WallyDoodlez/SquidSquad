# FEAT-SKILL-047 QA Results — Cross-Clone Health Detection + Guided Agent Setup

**QA Date**: 2026-03-30
**QA Agent**: QA verification agent (ad hoc)

---

## Test Case Results

### TC-1: `.local-config` created during setup with correct format
**Result**: CANNOT TEST (setup flow not yet implemented)
**Notes**: The SKILL.md setup flow (Steps 1-5) does not include guided `.local-config` creation. The file format is defined in `references/agent-instructions.md` (`- **role**: /absolute/path`) and `statusline.sh` parses it correctly (line 220: `grep "\\*\\*${AGENT}\\*\\*:"`), but there is no setup step that creates this file. See TC-7/TC-8.

### TC-2: `.local-config` is gitignored and never committed
**Result**: PASS
**Notes**: `.gitignore` line 4 contains `.squidsquad/.local-config`. The actual `.gitignore` on disk is correct. However, the SKILL.md setup template (line 493-499) does NOT include `.local-config` in the `.gitignore` snippet — new installs from the template would miss it. Filed as defect below.

### TC-3: Cross-clone health — statusline reads other agents' current-state via absolute path
**Result**: PASS (code review)
**Notes**: `references/statusline.sh` lines 214-250 correctly: reads `.local-config`, extracts agent path, constructs `<path>/.squidsquad/<role>/current-state`, reads mtime, compares against 2x interval threshold. Logic is sound.

### TC-4: Cross-clone health — correct mtime reading for staleness
**Result**: PASS (code review)
**Notes**: Lines 232-249 in statusline.sh handle all three cases: recent mtime -> `🦑`, old mtime -> `👻`, missing file -> `❓`. Platform-aware `stat` command (GNU vs BSD) on lines 233-236.

### TC-5: Health icon thresholds — 2x iteration interval boundary
**Result**: PASS (code review)
**Notes**: Line 212: `STALE_THRESHOLD=$(( INTERVAL * 2 ))` — exactly 2x. Line 239: `if [ "$AGENT_AGE" -le "$STALE_THRESHOLD" ]` — uses less-than-or-equal, so exactly 2x is still healthy. At 2x+1 minute, switches to stalled. Matches spec.

### TC-6: Timer reads current-state mtime from own clone
**Result**: PASS (code review)
**Notes**: Lines 55-83: timer reads own `current-state` mtime for elapsed time calculation. Fallback to latest iter file if current-state missing. BUG-035 fix preserved (current-state written on every cycle including quiet).

### TC-7: Guided setup — clone repo, write .local-config, open terminal, run boot
**Result**: FAIL
**Notes**: SKILL.md setup flow does NOT include guided agent clone + `.local-config` creation. There is no step that clones a repo to a specified path, writes the path to `.local-config`, opens a new terminal, or runs a boot script. This was a locked decision in CONTEXT.md ("Guided setup: Setup asks for path, clones repo, opens terminal, runs boot script -- one flow") but was not implemented.

### TC-8: Guided setup — default path suggestion
**Result**: FAIL
**Notes**: No guided setup exists in SKILL.md. No default path suggestion logic implemented. See TC-7.

### TC-9: Heartbeat removal — heartbeat.sh deleted
**Result**: PASS
**Notes**: Neither `.squidsquad/heartbeat.sh` nor `references/heartbeat.sh` exist on disk.

### TC-10: Heartbeat removal — boot scripts do not launch heartbeat
**Result**: PASS
**Notes**: Grep for "heartbeat" in all four boot scripts (`start-skill.sh`, `start-skill.ps1`, `start-pm.sh`, `start-pm.ps1`) returns no matches. Boot script templates in SKILL.md also have no heartbeat references.

### TC-11: Heartbeat removal — config has no Heartbeat Interval
**Result**: PASS
**Notes**: Grep for "heartbeat" (case-insensitive) in `.squidsquad/config.md` returns no matches. No `Heartbeat Interval Seconds` key exists.

### TC-12: Graceful fallback — .local-config missing entirely
**Result**: PASS (code review)
**Notes**: `statusline.sh` line 219: `if [ -f "$LOCAL_CONFIG" ]` — guards all `.local-config` reads. If missing, `AGENT_PATH` stays empty, and the agent falls through to `HEALTH="${HEALTH}❓"` on line 229. Own agent uses local path (line 224), unaffected by missing `.local-config`.

### TC-13: Graceful fallback — path in .local-config is unreachable
**Result**: PASS (code review)
**Notes**: Line 225: `[ -n "$AGENT_PATH" ] && [ -d "$AGENT_PATH" ]` — checks directory exists. If unreachable, falls to `❓`. Other agents with valid paths unaffected.

### TC-14: Graceful fallback — current-state file missing at valid path
**Result**: PASS (code review)
**Notes**: Line 231: `if [ -f "$AGENT_STATE" ]` — if current-state doesn't exist, falls to `❓` on line 248.

### TC-15: Cross-platform — Windows (PowerShell) support
**Result**: PARTIAL PASS (code review only, no live execution)
**Notes**: `statusline.sh` is bash-based, runs via Git Bash on Windows. The `stat` command platform detection (line 66/233) handles GNU vs BSD. Windows paths with backslashes may need quoting in bash — the script quotes `$AGENT_STATE` in stat calls. Boot scripts have both .sh and .ps1 variants. Cannot verify live execution without running agents.

### TC-16: Cross-platform — Unix (bash) support
**Result**: PARTIAL PASS (code review only, not on Unix machine)
**Notes**: Platform-aware `stat` command. Unix paths are natively supported by bash. Cannot verify live on Unix.

### TC-17: Regression — existing statusline features still work
**Result**: PASS (code review)
**Notes**: All pre-existing features preserved in statusline.sh: phase display (lines 102-110), overdue emoji (lines 74-76), rotating hints (lines 113-170), backlog pulse (lines 339-358), git sync (lines 87-93), context window (lines 35-44), ship counter (lines 176-181), planning phase (lines 184-203). The health check is additive — inserted in the PM section without modifying other code paths.

### TC-18: Upgrade path — existing install migration
**Result**: PASS (code review)
**Notes**: SKILL.md upgrade flow (lines 911, 923) correctly removes `heartbeat.sh`, removes `## Heartbeat` section from config. The upgrade settings agent removes `.squidsquad/heartbeat.sh` and regenerates statusline.sh. Remote heartbeat branch cleanup is not explicitly mentioned in the upgrade steps but was a side-effect mitigation in CONTEXT.md.

### TC-19: Upgrade path — statusline works after migration before .local-config created
**Result**: PASS (code review)
**Notes**: Per TC-12, missing `.local-config` gracefully falls back to `❓` for all other agents. Own agent timer still works.

### TC-20: PM Step 7 reads cross-clone current-state for health check
**Result**: PASS
**Notes**: Both `references/agent-instructions.md` (line 620-637) and live `.squidsquad/pm/CLAUDE.md` (line 275-292) correctly describe cross-clone file reads via `.local-config`. No `git fetch` or GitHub API. Uses same thresholds (2x interval) and icons (🦑/👻/❓) as statusline.

### TC-21: Multiple agents in .local-config
**Result**: PASS (code review)
**Notes**: `statusline.sh` line 213 iterates `ALL_AGENTS="pm $AGENTS $DM_AGENT"` — supports PM, all dev agents from config, and optional DM. Each agent evaluated independently.

### TC-22: SKILL.md templates updated — no heartbeat references in setup/boot
**Result**: FAIL (partial)
**Notes**: Boot script templates in SKILL.md are clean (no heartbeat). However:
1. **SKILL.md line 710** still references `🥚 never started` icon instead of `❓ unknown`. Should be `🦑 healthy, 👻 stalled, ❓ unknown`.
2. **SKILL.md setup `.gitignore` template** (lines 496-499) does not include `.squidsquad/.local-config`.
3. **SKILL.md setup flow** lacks guided agent clone + `.local-config` creation step.

### TC-23: References and live files updated
**Result**: FAIL (partial)
**Notes**:
- `references/agent-instructions.md` — PM Step 7: PASS (uses cross-clone file reads, correct icons)
- `references/agent-instructions.md` — PM Status Line section (line 1080): PASS (correct icons: 🦑/👻/❓)
- `references/statusline.sh` — PASS (uses `.local-config`, correct icons, no heartbeat)
- Live `statusline.sh` matches reference: PASS (diff shows identical)
- **Live `.squidsquad/pm/CLAUDE.md` line 735**: FAIL — still has stale heartbeat text: `🦑 if heartbeat branch is recent (within 3x heartbeat interval), 👻 if stalled (heartbeat older than threshold), 🥚 if never started (no heartbeat branch)`. Should match template (line 1080): `🦑 if current-state mtime within 2x interval, 👻 if stale, ❓ if unknown`.

---

## Defect Summary

### DEF-1: Live PM CLAUDE.md Status Line section has stale heartbeat references (BLOCKING)
- **File**: `.squidsquad/pm/CLAUDE.md` line 735
- **Current**: `🦑 if heartbeat branch is recent (within 3x heartbeat interval), 👻 if stalled (heartbeat older than threshold), 🥚 if never started (no heartbeat branch)`
- **Expected**: `🦑 if current-state mtime is within 2x iteration interval (healthy), 👻 if stale (stalled), ❓ if no data (unknown/unreachable)` (matches template at `references/agent-instructions.md` line 1080)
- **Impact**: PM agent reads incorrect instructions about how health detection works.

### DEF-2: SKILL.md status line docs reference stale 🥚 icon (MEDIUM)
- **File**: `SKILL.md` line 710
- **Current**: `🦑 healthy, 👻 stalled, 🥚 never started`
- **Expected**: `🦑 healthy, 👻 stalled, ❓ unknown`
- **Impact**: Docs describe wrong icon for unknown/never-started agents.

### DEF-3: SKILL.md setup .gitignore template missing `.local-config` (MEDIUM)
- **File**: `SKILL.md` lines 496-499
- **Current**: Only `.squidsquad/.active-role` and `.squidsquad/*/current-state`
- **Expected**: Should also include `.squidsquad/.local-config`
- **Impact**: New installs from template will not gitignore `.local-config`, risking accidental commit of machine-specific paths.

### DEF-4: SKILL.md setup flow missing guided clone + .local-config creation (MAJOR)
- **File**: `SKILL.md` setup instructions
- **Current**: No step for guided agent setup (clone repo, write `.local-config`, open terminal, run boot)
- **Expected**: Per CONTEXT.md locked decision: "Guided setup: Setup asks for path, clones repo, opens terminal, runs boot script -- one flow"
- **Impact**: Users have no guided way to set up multi-clone agents or create `.local-config`. Cross-clone health detection requires manual `.local-config` creation.

---

## Smoke Test Checklist

- [x] `.local-config` does not appear in `git status` (gitignored) — `.gitignore` has the entry
- [x] Statusline shows `🦑` for a healthy agent (recent mtime) — code correct
- [x] Statusline shows `👻` for a stalled agent (>2x interval) — code correct
- [x] Statusline shows `❓` for missing/unreachable agent — code correct
- [x] `heartbeat.sh` does not exist in `.squidsquad/` or `references/`
- [x] Boot scripts contain no `heartbeat` references
- [x] `config.md` contains no `Heartbeat Interval` key
- [x] Statusline does not crash when `.local-config` is missing — guarded reads
- [x] Statusline does not crash when a configured path is unreachable — guarded reads
- [x] Own agent's timer still works (reads own `current-state` mtime)
- [x] Overdue emoji, phase display, and rotating hints still work — code preserved
- [ ] `.local-config` is created during setup with correct format — **NOT IMPLEMENTED** (DEF-4)
- [ ] Setup guided flow clones repo and writes path to `.local-config` — **NOT IMPLEMENTED** (DEF-4)
- [ ] Works on Windows with PowerShell paths — code review only, no live test
- [ ] Works on Unix with bash paths — code review only, no live test

---

## Overall Verdict

**CONDITIONAL PASS** — 4 defects found. The core mechanism (cross-clone file reads via `.local-config`, statusline health icons, PM Step 7 health check, heartbeat removal) is correctly implemented. The main gap is the missing guided setup flow in SKILL.md (DEF-4) and stale documentation references (DEF-1, DEF-2, DEF-3). DEF-1 is blocking because it gives the live PM agent incorrect instructions about health detection.

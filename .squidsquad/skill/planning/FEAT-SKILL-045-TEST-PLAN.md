# FEAT-SKILL-045 Test Plan — Overdue Emoji

## Test Cases

### TC-1: Overdue emoji shown when elapsed exceeds interval (happy path)
- **Precondition**: Iteration interval is 30 minutes. Latest iteration file was modified 35 minutes ago.
- **Steps**: Set the iteration file mtime to 35 minutes in the past. Run statusline.sh.
- **Expected**: The timer area on line 1 includes an overdue emoji. The normal countdown (which would be negative) is replaced or augmented with the overdue indicator.
- **Verification**: `touch -d "35 minutes ago" .squidsquad/skill/iterations/iter-99.md && echo '{}' | bash .squidsquad/statusline.sh` — output contains the overdue emoji near the timer position.

### TC-2: No indicator when within interval (normal state)
- **Precondition**: Iteration interval is 30 minutes. Latest iteration file was modified 10 minutes ago.
- **Steps**: Set the iteration file mtime to 10 minutes ago. Run statusline.sh.
- **Expected**: Timer shows normal countdown (e.g. `20m`). No overdue emoji present.
- **Verification**: `touch -d "10 minutes ago" .squidsquad/skill/iterations/iter-99.md && echo '{}' | bash .squidsquad/statusline.sh` — output shows normal timer without overdue emoji.

### TC-3: Boundary — elapsed exactly equals interval
- **Precondition**: Iteration interval is 30 minutes. Latest iteration file was modified exactly 30 minutes ago.
- **Steps**: Set the iteration file mtime to exactly 30 minutes ago. Run statusline.sh.
- **Expected**: Overdue emoji is shown (triggers at boundary, no grace period). The remaining time would compute to 0, which already triggers the `REMAINING <= 0` branch.
- **Verification**: `touch -d "30 minutes ago" .squidsquad/skill/iterations/iter-99.md && echo '{}' | bash .squidsquad/statusline.sh` — output contains overdue emoji.

### TC-4: Boundary — one minute before interval
- **Precondition**: Iteration interval is 30 minutes. Latest iteration file was modified 29 minutes ago.
- **Steps**: Set the iteration file mtime to 29 minutes ago. Run statusline.sh.
- **Expected**: Timer shows `1m` remaining. No overdue emoji.
- **Verification**: `touch -d "29 minutes ago" .squidsquad/skill/iterations/iter-99.md && echo '{}' | bash .squidsquad/statusline.sh` — normal timer, no overdue emoji.

### TC-5: PM agent statusline shows overdue emoji
- **Precondition**: Active role is `pm`. Iteration interval is 30 minutes. Latest PM iteration file was modified 40 minutes ago.
- **Steps**: Write `pm` to `.squidsquad/.active-role`. Create a PM iteration file with old mtime. Run statusline.sh.
- **Expected**: PM statusline (line 1) includes the overdue emoji in the timer segment, alongside PM-specific segments (ship counter, health icons, etc.).
- **Verification**: `echo "pm" > .squidsquad/.active-role && touch -d "40 minutes ago" .squidsquad/pm/iterations/iter-99.md && echo '{}' | bash .squidsquad/statusline.sh` — PM line includes overdue emoji.

### TC-6: Dev agent statusline shows overdue emoji
- **Precondition**: Active role is `skill`. Iteration interval is 30 minutes. Latest skill iteration file was modified 45 minutes ago.
- **Steps**: Write `skill` to `.squidsquad/.active-role`. Create a skill iteration file with old mtime. Run statusline.sh.
- **Expected**: Dev statusline (line 1) includes the overdue emoji in the timer segment.
- **Verification**: `echo "skill" > .squidsquad/.active-role && touch -d "45 minutes ago" .squidsquad/skill/iterations/iter-99.md && echo '{}' | bash .squidsquad/statusline.sh` — dev line includes overdue emoji.

### TC-7: Significantly overdue (hours late)
- **Precondition**: Iteration interval is 30 minutes. Latest iteration file was modified 3 hours ago.
- **Steps**: Set the iteration file mtime to 3 hours ago. Run statusline.sh.
- **Expected**: Overdue emoji is shown. No crash, no integer overflow, no unusual output.
- **Verification**: `touch -d "3 hours ago" .squidsquad/skill/iterations/iter-99.md && echo '{}' | bash .squidsquad/statusline.sh` — overdue emoji present, output is well-formed.

### TC-8: No iteration files exist (fresh agent)
- **Precondition**: No iteration files exist in the iterations directory.
- **Steps**: Remove all iter-*.md files (or use empty dir). Run statusline.sh.
- **Expected**: Timer shows the default interval (e.g. `30m`). No overdue emoji — there is no previous cycle to be overdue from.
- **Verification**: Ensure no iter files exist, run statusline.sh — shows default timer, no overdue emoji, no errors.

### TC-9: Overdue emoji does not appear on line 2
- **Precondition**: Agent is overdue. current-state has a description set.
- **Steps**: Set up overdue condition and a current-state with `implementing|Working on feature...`. Run statusline.sh.
- **Expected**: Line 2 shows `🚧 Working on feature...` as usual. The overdue emoji only appears on line 1 in the timer area.
- **Verification**: Capture both lines of output. Line 2 has no overdue emoji; line 1 does.

### TC-10: Timer string length does not break layout
- **Precondition**: Agent is overdue. Terminal width is 80 columns.
- **Steps**: Run statusline.sh with overdue condition. Measure output line 1 length.
- **Expected**: Line 1 fits within 80 columns. The added emoji does not cause wrapping.
- **Verification**: `echo '{}' | bash .squidsquad/statusline.sh | head -1 | wc -m` — value is under 80 (accounting for ANSI escape sequences).

### TC-11: references/statusline.sh matches .squidsquad/statusline.sh after implementation
- **Precondition**: Dev agent has implemented the feature and copied the file.
- **Steps**: Diff the two files.
- **Expected**: Files are identical.
- **Verification**: `diff references/statusline.sh .squidsquad/statusline.sh` — no differences.

### TC-12: SKILL.md statusline documentation updated
- **Precondition**: SKILL.md has a section describing the statusline.
- **Steps**: Read the statusline section of SKILL.md.
- **Expected**: Documentation mentions the overdue emoji, when it appears, and what it means.
- **Verification**: `grep -i "overdue" SKILL.md` — returns at least one match describing the indicator.

### TC-13: agent-instructions.md statusline section updated
- **Precondition**: `references/agent-instructions.md` has a statusline section.
- **Steps**: Read the statusline section.
- **Expected**: Documentation mentions the overdue emoji behavior.
- **Verification**: `grep -i "overdue" references/agent-instructions.md` — returns at least one match.

## Smoke Tests
- [ ] Set iter file 35min old, run statusline.sh — overdue emoji visible on line 1
- [ ] Set iter file 10min old, run statusline.sh — no overdue emoji, normal countdown shown
- [ ] Set iter file exactly 30min old, run statusline.sh — overdue emoji visible (boundary)
- [ ] Set iter file 29min old, run statusline.sh — no overdue emoji, shows `1m`
- [ ] Switch active-role to `pm`, set PM iter file 40min old — overdue emoji on PM statusline
- [ ] Remove all iter files, run statusline.sh — default timer, no overdue emoji, no errors
- [ ] `grep -i "overdue" SKILL.md` returns documentation match
- [ ] `grep -i "overdue" references/agent-instructions.md` returns documentation match
- [ ] `diff references/statusline.sh .squidsquad/statusline.sh` shows no differences after implementation

## Regression Risks
- **Existing timer behavior**: The `REMAINING <= 0` and `REMAINING <= 1` branches already show `<1m`. The overdue change must augment (not replace) this logic. If the emoji is added inside the existing conditional, the `<1m` text could be lost or duplicated.
- **TIMER_STR used in both PM and dev output**: The timer variable is computed once in the shared section (lines 59-78) and referenced in both the PM line (`LINE1` at line 240) and dev line (`LINE1` at line 288). Changes to the shared section automatically apply to both roles, which is correct. But if the change is accidentally placed inside the PM or dev block, only one role gets it.
- **Integer comparison edge cases**: The elapsed/remaining computation uses integer division (`/ 60`). An elapsed time of 1799 seconds (29m 59s) computes as 29 minutes elapsed, 1 minute remaining — not overdue. At 1800 seconds (30m 0s) it computes as 30 minutes elapsed, 0 remaining — overdue. This is correct and matches the "no grace period" requirement, but the granularity is 1-minute due to integer division.
- **stat command portability**: The script already handles GNU stat vs BSD stat (lines 62-66). Any changes to the timer logic should not disturb this platform detection.
- **ANSI escape sequences in length calculation**: If the overdue emoji uses ANSI color codes, the `wc -m` length check in TC-10 will overcount. This is cosmetic and matches existing behavior (context percentage already uses ANSI colors).

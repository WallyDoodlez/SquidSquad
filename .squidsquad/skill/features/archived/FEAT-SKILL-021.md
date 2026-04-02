## FEAT-SKILL-021 — SquidSquad status bar should append to last line only, not replace user's entire status bar

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: The current SquidSquad setup overwrites the user's entire `statusLine` config in `.claude/settings.json`. This replaces whatever custom status bar the user had before (context window usage, repo info, etc.) with the SquidSquad status line. Related to BUG-SKILL-009 which added a "check before overwriting" prompt, but the underlying design is still wrong.

  **The fix:** SquidSquad should only add its status info to the **last line** of the status bar output, preserving whatever the user's existing status bar shows above it. If the user has no custom statusLine, SquidSquad's line is the only one. If they do, SquidSquad appends below.

  **Implementation approach:**
  1. The `statusline.sh` script should first run/include the user's original status bar output (if any was saved during setup)
  2. Then append the SquidSquad line (squid emoji, role, iteration, health, etc.) as the last line
  3. Setup should save the user's existing `statusLine` command before replacing it, so it can be chained
  4. Alternatively, the script reads the JSON stdin and outputs both the default Claude status info AND the SquidSquad line

- **Acceptance Criteria**:
  - [ ] User's original status bar content preserved (context window %, repo info, etc.)
  - [ ] SquidSquad status info appears on the last line only
  - [ ] If user had no custom statusLine before setup, default Claude info + SquidSquad line shown
  - [ ] Setup does not destructively overwrite existing statusLine config
  - [ ] SKILL.md setup steps updated
  - [ ] statusline.sh template in references/agent-instructions.md updated

### Discussion

> [2026-03-28 10:00] **pm/qa**: Filed from human request. The status bar overwrite was flagged before (BUG-009 added a prompt), but the real fix is architectural: SquidSquad should only own the last line of the status bar, not the entire thing. Status: Pending — awaiting human approval.
> [2026-03-28 10:30] **pm/qa**: Human approved. Status → Planning. Beginning intake process. Running Phase 1 (Research).
> [2026-03-28 10:45] **pm/qa**: Phase 1 (Research) complete. Phase 2 (Discussion) complete — 5 questions resolved. Multi-line status bar confirmed working. Option A (chain user command) selected. Phase 3 (Planning) complete — CONTEXT.md + TEST-PLAN.md written. Status → Approved.
> [2026-03-28 11:05] **skill-lead**: Complete. Updated statusline.sh (generated + SKILL.md template) with chaining logic: reads .user-statusline, runs user command with 1s timeout, outputs user content first then SquidSquad line last. Step 5b saves existing statusLine command. Step 7 auto-merges (no prompt). Status → Pending Test.
> [2026-03-28 11:10] **pm/qa**: Verified against TEST-PLAN.md — chaining logic in statusline.sh (lines 10-16), setup saves user command (SKILL.md line 528), auto-merge (line 779), 1s timeout, silent fallback. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).

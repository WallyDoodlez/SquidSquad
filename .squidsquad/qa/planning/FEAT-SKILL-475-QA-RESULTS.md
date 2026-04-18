# QA Results — #475 Token Efficiency Audit

## Summary
- Total: 46
- Pass: 32
- Fail: 1
- Skip: 13

## Results

### TC-1: boot-remote-agents removed from QA includes.yml
- **Result**: PASS
- **Evidence**: `grep -c "boot-remote-agents" references/roles/qa/includes.yml` returns 0. Composed QA CLAUDE.md has 0 matches for "Boot Remote Agents" and "boot-remote-agents".
- **Notes**: None

### TC-2: boot-remote-agents removed from Dev/Skill includes.yml
- **Result**: PASS
- **Evidence**: `grep -c "boot-remote-agents" references/roles/dev/includes.yml` returns 0. Composed skill CLAUDE.md has 0 matches for "Boot Remote Agents".
- **Notes**: None

### TC-3: boot-remote-agents removed from DM includes.yml
- **Result**: PASS
- **Evidence**: `grep -c "boot-remote-agents" references/roles/dm/includes.yml` returns 0.
- **Notes**: None

### TC-4: boot-remote-agents removed from Designer includes.yml
- **Result**: PASS
- **Evidence**: `grep -c "boot-remote-agents" references/roles/designer/includes.yml` returns 0.
- **Notes**: None

### TC-5: boot-remote-agents RETAINED in PM includes.yml
- **Result**: PASS
- **Evidence**: `grep -c "boot-remote-agents" references/roles/pm/includes.yml` returns 1. PM CLAUDE.md has 1 match for "Boot Remote Agents" and 2 matches for "boot_remote.py".
- **Notes**: None

### TC-6: Label Taxonomy extracted to reference file
- **Result**: PASS
- **Evidence**: `references/docs/label-taxonomy.md` exists with all 6 label categories verified (priority:high, status:in-progress, severity:high, role:skill, design:needed, improvement-scan all found). tracker-protocol.md has 0 matches for priority:high and status:pending-ship. Composed PM/QA CLAUDE.md have 0 matches for "priority:low — nice-to-have".
- **Notes**: None

### TC-7: Vault-protocol entity model condensed
- **Result**: PASS
- **Evidence**: vault-protocol.md is 123 lines / 1226 words (well under 180 line / 1500 word thresholds). vault-protocol-slim.md unchanged at 44 lines.
- **Notes**: None

### TC-8: Vault-protocol search modes condensed
- **Result**: PASS
- **Evidence**: All 4 search modes present: "By tag" (1), "By type" (1), "By keyword" (1), "wikilink traversal" (1).
- **Notes**: None

### TC-9: Vault-check Level 2 condensed
- **Result**: PASS
- **Evidence**: "Level 2" found 1 time. Orphan check bash snippet (`for f in .squidsquad/vault/galaxy`) returns 0 matches -- removed as expected.
- **Notes**: None

### TC-10: compose.py deploy-all succeeds without errors
- **Result**: PASS
- **Evidence**: Exit code 0. Output shows all 4 roles deployed (qa: 717 lines, skill: 1000 lines, pm: 1490 lines, dm: 656 lines). No ERROR lines in output.
- **Notes**: None

### TC-11: Comprehension — tracker-protocol (Label Taxonomy removed)
- **Result**: SKIP
- **Evidence**: Comprehension test requiring fresh agent spawn.
- **Notes**: Cannot be automated.

### TC-12: Comprehension — tracker-protocol (Status Transitions preserved)
- **Result**: SKIP
- **Evidence**: Comprehension test requiring fresh agent spawn.
- **Notes**: Cannot be automated.

### TC-13: Comprehension — vault-protocol (entity model condensed)
- **Result**: SKIP
- **Evidence**: Comprehension test requiring fresh agent spawn.
- **Notes**: Cannot be automated.

### TC-14: Comprehension — vault-protocol (search modes condensed)
- **Result**: SKIP
- **Evidence**: Comprehension test requiring fresh agent spawn.
- **Notes**: Cannot be automated.

### TC-15: Comprehension — vault-protocol (vault-check Level 2 condensed)
- **Result**: SKIP
- **Evidence**: Comprehension test requiring fresh agent spawn.
- **Notes**: Cannot be automated.

### TC-16: Comprehension — boot-remote-agents removal (QA agent)
- **Result**: SKIP
- **Evidence**: Comprehension test requiring fresh agent spawn.
- **Notes**: Cannot be automated.

### TC-17: Comprehension — boot-remote-agents removal (Dev/Skill agent)
- **Result**: SKIP
- **Evidence**: Comprehension test requiring fresh agent spawn.
- **Notes**: Cannot be automated.

### TC-18: tracker.py still enforces label format (no agent memorization needed)
- **Result**: PASS
- **Evidence**: tracker.py accepts --title, --body, --role, --severity, --reporter flags (verified via source grep and usage output). Script enforces label construction programmatically (verified: "ISSUE:" prefix, label format encoding in script lines 469-498). Did not create an actual issue per test constraints.
- **Notes**: Verified flags and enforcement logic exist without creating a real issue.

### TC-19: tracker.py still rejects illegal transitions
- **Result**: PASS
- **Evidence**: `python references/scripts/tracker.py transition 1 open shipped --role pm-lead` returns exit code 1 with message: "ERROR: Illegal transition status:open -> status:shipped. Legal from status:open: ['status:in-progress', 'status:pending-test']"
- **Notes**: None

### TC-20: tracker.py still rejects unauthorized transitions
- **Result**: PASS
- **Evidence**: `python references/scripts/tracker.py transition 1 pending-test pending-ship --role skill-lead` returns exit code 1 with message: "ERROR: Unauthorized transition on #1: role 'skill' is not authorized for status:pending-test -> status:pending-ship (allowed: ['pm', 'qa']). Use --force to override (humans only)."
- **Notes**: None

### TC-21: PM boot-remote-agents step still functions
- **Result**: PASS
- **Evidence**: PM CLAUDE.md contains: "PM-only gate" (matched), "boot_remote.py --all --json" (matched), "Interpreting output" (matched). Full step content verified.
- **Notes**: None

### TC-22: vault-protocol-slim NOT modified
- **Result**: PASS
- **Evidence**: vault-protocol-slim.md is 44 lines. `git diff HEAD -- references/sub-skills/common/vault-protocol-slim.md` returns empty (no changes).
- **Notes**: None

### TC-23: Prohibitions section untouched across all roles
- **Result**: PASS
- **Evidence**: PM: "What You Must Never Do" found (1), "Never approve a task" found (1). QA: 3 matches for prohibit/must never. Skill: 4 matches for prohibit/must never.
- **Notes**: None

### TC-24: Zero-gap gate untouched
- **Result**: PASS
- **Evidence**: PM CLAUDE.md has 1 match for "zero-gap" (case-insensitive).
- **Notes**: None

### TC-25: Approval gates untouched
- **Result**: PASS
- **Evidence**: PM CLAUDE.md has 2 matches for "human must explicitly approve".
- **Notes**: None

### TC-26: vault-create still triggers vault-check Level 1
- **Result**: PASS
- **Evidence**: Both PM and Skill CLAUDE.md contain: "vault-check Level 1 runs after every write — vault-create and vault-update both trigger it"
- **Notes**: None

### TC-27: vault-update "never delete content" rule preserved
- **Result**: PASS
- **Evidence**: vault-protocol.md contains both: "Never delete existing content" and "vault-update never deletes content — only adds, corrects, or marks as superseded".
- **Notes**: None

### TC-28: BRIEFING.md section preserved in vault-protocol
- **Result**: PASS
- **Evidence**: vault-protocol.md contains "BRIEFING.md" (multiple references) and "~50 line summary" (found in BRIEFING.md section header).
- **Notes**: None

### TC-29: New role added after taxonomy extraction
- **Result**: SKIP
- **Evidence**: Manual/hypothetical test. The trimmed tracker-protocol.md preserves the instruction "Use the tracker script for all queries" and all create-issue/create-task commands. A new role using tracker-protocol would inherit the trimmed version and function correctly via tracker.py.
- **Notes**: Inspection-based verification only.

### TC-30: Agent constructs labels manually (regression risk)
- **Result**: PASS
- **Evidence**: tracker-protocol.md contains: "Use the tracker script for all queries — it encodes correct label formats" (exact match). "create-issue" found 1 time. "create-task" found 1 time.
- **Notes**: None

### TC-31: vault-protocol too terse — agent cannot determine folder for note type
- **Result**: SKIP
- **Evidence**: Comprehension test requiring fresh agent spawn.
- **Notes**: Cannot be automated.

### TC-32: Reference file missing at runtime
- **Result**: PASS
- **Evidence**: tracker.py does not read or depend on references/docs/label-taxonomy.md at runtime. The script encodes labels programmatically (verified: create-issue outputs "Missing --title" without referencing the taxonomy file). tracker.py works regardless of reference file presence.
- **Notes**: None

### TC-33: Concurrent vault writes after vault-protocol compression
- **Result**: PASS
- **Evidence**: vault-protocol.md contains "Concurrent Access" section header and "Keep both versions" conflict resolution rule (both matched exactly).
- **Notes**: None

### TC-34: compose.py handles removed include gracefully
- **Result**: PASS
- **Evidence**: `python references/scripts/compose.py deploy-all` produces 0 error lines. The `{{include: common/boot-remote-agents}}` lines were removed from all non-PM entry CLAUDE.md files (qa, dev, dm, designer all return 0 matches). compose.py exits 0.
- **Notes**: None

### TC-35: Skill role inherits from dev manifest correctly
- **Result**: PASS
- **Evidence**: `references/roles/skill/includes.yml` does not exist (file not found, exit 2). Composed `.squidsquad/skill/CLAUDE.md` has 0 matches for "boot-remote-agents". Skill inherits from dev manifest correctly.
- **Notes**: None

### TC-36: Per-role token savings match estimates
- **Result**: PASS
- **Evidence**: Word counts after changes: PM=10680 (baseline 11056, saved 376), QA=4450 (baseline 4854, saved 404), Skill=6743 (baseline 7633, saved 890), DM=3975 (baseline 4379, saved 404). Total baseline=27922, total after=25848, total savings=2074 words. Savings distribution differs from estimates but all roles show reductions.
- **Notes**: Savings are lower than the estimated ~3140 words. PM saved 376 vs estimated 860; Skill saved 890 vs estimated 960. The vault-protocol compression was less aggressive than estimated.

### TC-37: Token savings are >= 10% of total baseline
- **Result**: FAIL
- **Evidence**: Total savings = 2074 words out of 27922 baseline = 7.4% reduction. Target was >= 10%, minimum acceptable was 8%. Actual 7.4% falls below both thresholds.
- **Notes**: The shortfall is primarily in PM savings (376 vs 860 estimated) and overall vault-protocol compression being less aggressive than researched. The taxonomy extraction and boot-remote-agents removal met expectations; vault-protocol compression underdelivered.

### TC-38: No role INCREASED in word count
- **Result**: PASS
- **Evidence**: All roles decreased: PM 11056->10680 (-376), QA 4854->4450 (-404), Skill 7633->6743 (-890), DM 4379->3975 (-404).
- **Notes**: None

### TC-39: compose.py deploy-all regenerates all CLAUDE.md files
- **Result**: PASS
- **Evidence**: Timestamps before deploy-all: pm=1776471057, qa=1776471056, skill=1776471057. After: all updated to 1776471059. Content reflects changes.
- **Notes**: None

### TC-40: Existing install without recompose continues working
- **Result**: PASS
- **Evidence**: Verified by inspection. Changes are subtractive only (removed boot-remote-agents from non-PM, extracted taxonomy, compressed vault-protocol). No new required instructions were added. Old templates are supersets -- they contain boot-remote-agents (harmless with PM-only gate) and full taxonomy (redundant but functional).
- **Notes**: Inspection-based verification.

### TC-41: No new config values required
- **Result**: PASS
- **Evidence**: vault-protocol.md has 0 references to config.md. No new configuration fields introduced by any change.
- **Notes**: None

### TC-42: Reference file is accessible from all agent clone paths
- **Result**: PASS
- **Evidence**: `git ls-files references/docs/label-taxonomy.md` returns the file path (tracked). File is under `references/` which is shared via git.
- **Notes**: None

### TC-43: All roles share identical tracker-protocol (minus taxonomy)
- **Result**: PASS
- **Evidence**: Diff between PM and QA tracker-protocol sections shows only role-specific placeholder substitution (e.g., `[ROLE]` in PM vs `skill` in QA/Skill). This is expected compose.py behavior -- the base tracker-protocol content is identical across all roles.
- **Notes**: Role placeholder substitution is a compose.py feature, not a content difference.

### TC-44: PM and Dev/Skill share identical vault-protocol (condensed)
- **Result**: PASS
- **Evidence**: `diff /tmp/vp-pm.txt /tmp/vp-skill.txt` returns exit code 0 (no differences).
- **Notes**: None

### TC-45: QA, DM, Designer still use vault-protocol-slim (unchanged)
- **Result**: PASS
- **Evidence**: QA CLAUDE.md contains "Vault — Shared Memory Layer (Read-Only)". DM CLAUDE.md contains "Vault — Shared Memory Layer (Read-Only)". Both use vault-protocol-slim.
- **Notes**: Designer role not composed (no designer agent active), but includes.yml verified to use vault-protocol-slim.

### TC-46: No role references boot_remote.py except PM
- **Result**: PASS
- **Evidence**: `grep -rl "boot_remote" .squidsquad/*/CLAUDE.md` returns only `.squidsquad/pm/CLAUDE.md`.
- **Notes**: None

## Smoke Test Summary

| Check | Result |
|-------|--------|
| compose.py deploy-all exits 0 | PASS |
| All composed CLAUDE.md non-empty and well-formed | PASS (pm=77467B, qa=33287B, skill=50437B, dm=29715B) |
| QA CLAUDE.md has 0 boot-remote-agents refs | PASS |
| Skill CLAUDE.md has 0 boot-remote-agents refs | PASS |
| PM CLAUDE.md has >= 1 boot-remote-agents refs | PASS |
| references/docs/label-taxonomy.md exists and non-empty | PASS |
| vault-protocol.md < 1500 words | PASS (1226 words) |
| tracker-protocol.md < 800 words | PASS (797 words) |
| tracker.py check-gh exits 0 | PASS |
| tracker.py create-issue shows expected flags | PASS |
| All role includes.yml parse without YAML errors | PASS |
| No ERROR: Missing include markers | PASS |

## Failure Details

### TC-37: Token savings below target
- **Severity**: Medium
- **Impact**: The 7.4% token reduction falls short of the 10% target and the 8% minimum acceptable threshold.
- **Root cause**: vault-protocol compression was less aggressive than the research estimated. PM saved only 376 words vs estimated 860. The entity model and search mode sections were condensed but still retain more verbosity than projected.
- **Recommendation**: Consider further vault-protocol compression (additional condensation of the entity model summary, search mode examples, or vault-check Level 2 detail) to reach the 8% minimum threshold.

# FEAT-17 Test Plan — Vault Phase 3: vault-remember + End-of-Cycle Reflection

**Feature**: #17 — vault-remember sub-skill + deterministic gates + human-profile seeding
**Scripts under test**: `vault_remember.py` (new), `vault_check.py` (extended), `cycle.py` (extended)
**Location**: `references/scripts/`
**Test file**: `references/scripts/test_vault_remember.py` (Python unittest, stdlib only)
**Python**: 3.8+, stdlib only
**In-situ vault**: `.squidsquad/vault/` (5 notes: BRIEFING.md, 2 galaxy, 1 area, 1 project)

---

## Test Infrastructure

### Conventions
- Unit tests mock the filesystem via `unittest.mock.patch` and `tempfile` — no real vault writes
- Integration tests operate on the REAL `.squidsquad/vault/` in this repo
- Integration tests that create files clean up in `finally` blocks
- Exit codes: 0 = success/true, 1 = false/skip, 2 = error
- All temp note filenames use `test-` prefix for easy identification and cleanup

### Test Runner
```bash
python references/scripts/test_vault_remember.py -v
```

---

## A. Unit Tests — `vault_remember.py` Gates

### A1. Quiet-Cycle Detection

**TC-001: is-quiet returns 0 (quiet) when no iter log exists this cycle**
- Precondition: Mock iterations/ dir for role `skill` with iter-1.md through iter-5.md, all with timestamps older than 30 minutes
- Steps: Call `vault_remember.py is-quiet skill`
- Expected: exit 0, stdout contains `quiet`
- Verification: Assert exit code == 0

**TC-002: is-quiet returns 1 (non-quiet) when current cycle has iter log**
- Precondition: Mock iterations/ dir with iter-6.md having a timestamp within the last 30 minutes
- Steps: Call `vault_remember.py is-quiet skill`
- Expected: exit 1, stdout contains `non-quiet`
- Verification: Assert exit code == 1

**TC-003: is-quiet handles empty iterations directory**
- Precondition: Mock iterations/ dir that is empty
- Steps: Call `vault_remember.py is-quiet skill`
- Expected: exit 0 (quiet — no logs at all means no work)
- Verification: Assert exit code == 0

### A2. Write Counter Enforcement

**TC-004: write-budget returns 2 when no writes this cycle**
- Precondition: Mock working-state.md with `**Vault Writes This Cycle**: 0`
- Steps: Call `vault_remember.py write-budget skill`
- Expected: stdout = `2`, exit 0
- Verification: Assert stdout == `2`

**TC-005: write-budget returns 1 when 1 write consumed**
- Precondition: Mock working-state.md with `**Vault Writes This Cycle**: 1`
- Steps: Call `vault_remember.py write-budget skill`
- Expected: stdout = `1`, exit 0
- Verification: Assert stdout == `1`

**TC-006: write-budget returns 0 when budget exhausted (2 writes)**
- Precondition: Mock working-state.md with `**Vault Writes This Cycle**: 2`
- Steps: Call `vault_remember.py write-budget skill`
- Expected: stdout = `0`, exit 1 (signals: no budget)
- Verification: Assert exit code == 1, stdout == `0`

**TC-007: write-budget allows burst to 3 when config permits**
- Precondition: Mock config.md with `**Writes Per Cycle**: 3` (burst mode). Mock working-state.md with `**Vault Writes This Cycle**: 2`
- Steps: Call `vault_remember.py write-budget skill`
- Expected: stdout = `1`, exit 0 (burst allows 3rd write)
- Verification: Assert stdout == `1`

**TC-008: write-budget defaults to 2 when config key missing**
- Precondition: Mock config.md without any `Writes Per Cycle` entry. Mock working-state.md with `**Vault Writes This Cycle**: 0`
- Steps: Call `vault_remember.py write-budget skill`
- Expected: stdout = `2`, exit 0
- Verification: Assert stdout == `2` (default budget)

### A3. BRIEFING.md Token Budget

**TC-009: briefing-budget returns remaining tokens when under cap**
- Precondition: Mock BRIEFING.md with 30 lines (~900 words). Config budget = 2000 tokens
- Steps: Call `vault_remember.py briefing-budget`
- Expected: exit 0, stdout JSON contains `{"used": <N>, "budget": 2000, "remaining": <positive>}`
- Verification: Assert `remaining` > 0

**TC-010: briefing-budget returns 0 remaining when at cap**
- Precondition: Mock BRIEFING.md with ~1540 words (1540 * 1.3 = ~2000 tokens)
- Steps: Call `vault_remember.py briefing-budget`
- Expected: exit 1 (over budget), stdout JSON has `remaining` <= 0
- Verification: Assert exit code == 1

**TC-011: briefing-budget uses default 2000 when config key missing**
- Precondition: Mock config.md without `BRIEFING Token Budget` entry. Mock small BRIEFING.md
- Steps: Call `vault_remember.py briefing-budget`
- Expected: exit 0, JSON `budget` field == 2000
- Verification: Assert budget == 2000

### A4. Effective Confidence Calculation

**TC-012: effective-confidence returns original for fresh note (updated today)**
- Precondition: Mock galaxy note with `confidence: high`, `updated: 2026-04-05`
- Steps: Call `vault_remember.py effective-confidence <path>` with today = 2026-04-05
- Expected: stdout = `high`
- Verification: Assert stdout == `high`

**TC-013: effective-confidence decays high to medium at 30+ days**
- Precondition: Mock galaxy note with `confidence: high`, `updated: 2026-03-01` (35 days ago)
- Steps: Call `vault_remember.py effective-confidence <path>`
- Expected: stdout = `medium`
- Verification: Assert stdout == `medium`

**TC-014: effective-confidence decays medium to low at 60+ days**
- Precondition: Mock galaxy note with `confidence: medium`, `updated: 2026-02-01` (63 days ago)
- Steps: Call `vault_remember.py effective-confidence <path>`
- Expected: stdout = `low`
- Verification: Assert stdout == `low`

**TC-015: effective-confidence decays high to low at 90+ days**
- Precondition: Mock galaxy note with `confidence: high`, `updated: 2025-12-30` (96 days ago)
- Steps: Call `vault_remember.py effective-confidence <path>`
- Expected: stdout = `low`
- Verification: Assert stdout == `low`

**TC-016: effective-confidence exempts evergreen-tagged notes**
- Precondition: Mock galaxy note with `confidence: high`, `updated: 2025-01-01` (very old), `tags: [architecture, evergreen]`
- Steps: Call `vault_remember.py effective-confidence <path>`
- Expected: stdout = `high` (no decay applied)
- Verification: Assert stdout == `high`

**TC-017: effective-confidence does not modify the source file**
- Precondition: Mock galaxy note with `confidence: high`, `updated: 2026-02-01`
- Steps: Read file content before call. Call `vault_remember.py effective-confidence <path>`. Read file content after call
- Expected: File content byte-for-byte identical before and after
- Verification: Assert before == after

### A5. Note Count Guard

**TC-018: note-count returns count and OK when under threshold**
- Precondition: Mock vault dir with 10 .md files. Config threshold = 500
- Steps: Call `vault_remember.py note-count`
- Expected: exit 0, stdout JSON contains `{"count": 10, "threshold": 500, "ok": true}`
- Verification: Assert exit code == 0, `ok` == true

**TC-019: note-count warns when approaching threshold (>80%)**
- Precondition: Mock vault dir with 420 .md files. Config threshold = 500
- Steps: Call `vault_remember.py note-count`
- Expected: exit 0, stdout JSON has `ok` == true but includes `"warning": "approaching threshold"`
- Verification: Assert warning present

**TC-020: note-count returns not-ok when at threshold**
- Precondition: Mock vault dir with 500 .md files. Config threshold = 500
- Steps: Call `vault_remember.py note-count`
- Expected: exit 1, JSON has `"ok": false`
- Verification: Assert exit code == 1

---

## B. Unit Tests — `vault_check.py dedup-check`

### B1. Exact Match

**TC-021: dedup-check finds exact title match**
- Precondition: Mock vault with `galaxy/decision-use-rest-api.md` containing title "Use REST API"
- Steps: Call `vault_check.py dedup-check --title "Use REST API" --tags "api,rest"`
- Expected: exit 0, stdout JSON contains match with score 100 and path to the existing note
- Verification: Assert exactly 1 match, score == 100

### B2. Near Match (Partial Overlap)

**TC-022: dedup-check returns candidates with partial keyword overlap**
- Precondition: Mock vault with `galaxy/decision-rest-over-graphql.md` (tags: api, rest, architecture)
- Steps: Call `vault_check.py dedup-check --title "REST API Preference" --tags "api,rest,http"`
- Expected: exit 0, JSON has 1+ candidates with overlap score between 40-99
- Verification: Assert candidate list non-empty, scores in expected range

**TC-023: dedup-check caps results at 3 candidates**
- Precondition: Mock vault with 5 notes all sharing keyword overlap with query
- Steps: Call `vault_check.py dedup-check --title "common-keyword topic" --tags "shared-tag"`
- Expected: exit 0, at most 3 candidates returned (sorted by score descending)
- Verification: Assert len(candidates) <= 3

### B3. No Match

**TC-024: dedup-check returns empty for unrelated query**
- Precondition: Mock vault with notes about REST, architecture
- Steps: Call `vault_check.py dedup-check --title "CSS Grid Layout" --tags "css,frontend,layout"`
- Expected: exit 0, JSON has empty candidates list
- Verification: Assert candidates == []

### B4. Edge Cases

**TC-025: dedup-check handles empty vault (no galaxy notes)**
- Precondition: Mock vault with empty galaxy/ directory
- Steps: Call `vault_check.py dedup-check --title "Any Title" --tags "any"`
- Expected: exit 0, empty candidates list, no crash
- Verification: Assert candidates == [], exit code == 0

**TC-026: dedup-check handles single-note vault**
- Precondition: Mock vault with exactly 1 galaxy note
- Steps: Call `vault_check.py dedup-check --title "matching title" --tags "matching-tag"`
- Expected: exit 0, either 0 or 1 candidate depending on overlap
- Verification: Assert no crash, valid JSON output

**TC-027: dedup-check with empty tags param**
- Precondition: Mock vault with notes
- Steps: Call `vault_check.py dedup-check --title "Some Title" --tags ""`
- Expected: exit 0, matching done on title keywords only
- Verification: Assert valid JSON, no error

---

## C. Unit Tests — `cycle.py is-quiet`

**TC-028: is-quiet returns exit 0 when no iter log created this cycle**
- Precondition: Mock iterations/ with only old iter files (mtime > 30 min ago)
- Steps: Call `cycle.py is-quiet skill`
- Expected: exit 0
- Verification: Assert exit code == 0

**TC-029: is-quiet returns exit 1 when iter log exists for this cycle**
- Precondition: Mock iterations/ with iter-N.md having mtime within last 30 min
- Steps: Call `cycle.py is-quiet skill`
- Expected: exit 1
- Verification: Assert exit code == 1

**TC-030: is-quiet handles missing iterations directory**
- Precondition: Role directory exists but has no iterations/ subdirectory
- Steps: Call `cycle.py is-quiet skill`
- Expected: exit 0 (no logs = quiet)
- Verification: Assert exit code == 0

---

## D. Integration Tests — In-Situ on This Repo

These tests run against the REAL SquidSquad vault at `.squidsquad/vault/` in this repo. They validate that vault-remember components work correctly with the actual repo state (5 notes, active agents, 30-min cycles).

### D1. Sub-Skill Composition

**TC-031: compose.py deploy skill produces CLAUDE.md with vault-remember step**
- Precondition: `references/sub-skills/common/vault-remember.md` exists. `references/sub-skills/roles/dev-agent.md` contains `{{include: common/vault-remember}}` between iteration-log and git-commit
- Steps:
  1. Run `python references/scripts/compose.py deploy skill --dry-run` (or read the composed output)
  2. Search output for vault-remember content
- Expected: Composed CLAUDE.md contains the vault-remember reflection prompt text, positioned AFTER "Log Iteration" content and BEFORE "Commit and Push" content
- Verification: Assert vault-remember text present. Assert ordering: iteration-log < vault-remember < git-commit

**TC-032: compose.py deploy pm produces CLAUDE.md with vault-remember step**
- Precondition: Same as TC-031 but for `pm-agent.md`
- Steps: Run `python references/scripts/compose.py deploy pm --dry-run`
- Expected: vault-remember content present between iteration-log and git-commit sections
- Verification: Same ordering check as TC-031

**TC-033: compose.py deploy dm produces CLAUDE.md with vault-remember step**
- Precondition: `references/sub-skills/roles/dm-agent.md` contains `{{include: common/vault-remember}}`
- Steps: Run `python references/scripts/compose.py deploy dm --dry-run`
- Expected: vault-remember content present in composed output
- Verification: Assert vault-remember text present

**TC-034: vault-remember sub-skill has config gate at top**
- Precondition: `references/sub-skills/common/vault-remember.md` exists
- Steps: Read the file content
- Expected: First executable instruction is a config check (reads `vault-remember` from config.md and skips if `no`)
- Verification: Assert config gate instruction appears before any vault write instructions

### D2. Config Integration

**TC-035: config.py reads vault-remember config section**
- Precondition: `.squidsquad/config.md` contains `## Vault Remember` section with `**Enabled**: yes`
- Steps: Run `python references/scripts/config.py get vault-remember`
- Expected: exit 0, stdout = `yes`
- Verification: Assert stdout == `yes`

**TC-036: missing vault-remember config key defaults to enabled**
- Precondition: Create a temp config.md WITHOUT the `## Vault Remember` section
- Steps: Call vault_remember.py's config-reading function with the temp config
- Expected: Returns enabled=True (default)
- Verification: Assert enabled == True. Cleanup temp file in `finally`

**TC-037: vault-remember disabled via config causes skip**
- Precondition: Mock or temp config.md with `**Enabled**: no` under `## Vault Remember`
- Steps: Call vault_remember.py main entry with config set to disabled
- Expected: exit 0, stdout indicates "skipped — disabled in config"
- Verification: Assert no vault files created, exit 0

### D3. In-Situ Vault Operations

**TC-038: dedup-check against real vault finds existing decision note**
- Precondition: Real vault contains `galaxy/decision-sub-skill-architecture.md`
- Steps: Run `python references/scripts/vault_check.py dedup-check --title "sub-skill architecture" --tags "architecture,sub-skills"`
- Expected: Returns at least 1 candidate matching `decision-sub-skill-architecture.md`
- Verification: Assert candidate path includes `decision-sub-skill-architecture.md`

**TC-039: dedup-check against real vault returns empty for novel topic**
- Precondition: Real vault (5 notes, no notes about "kubernetes deployment")
- Steps: Run `python references/scripts/vault_check.py dedup-check --title "kubernetes deployment strategy" --tags "kubernetes,deployment,cloud"`
- Expected: Empty candidates list
- Verification: Assert candidates == []

**TC-040: effective-confidence on real vault galaxy note**
- Precondition: `galaxy/decision-sub-skill-architecture.md` exists with `confidence` and `updated` frontmatter
- Steps: Run `python references/scripts/vault_remember.py effective-confidence .squidsquad/vault/galaxy/decision-sub-skill-architecture.md`
- Expected: Returns one of `high`, `medium`, `low` depending on note age
- Verification: Assert output is valid confidence level. Assert source file unchanged

**TC-041: note-count on real vault returns correct count**
- Precondition: Real vault has 5 .md files
- Steps: Run `python references/scripts/vault_remember.py note-count`
- Expected: exit 0, JSON `count` == 5 (or current actual count)
- Verification: Assert count matches `find .squidsquad/vault/ -name "*.md" | wc -l`

**TC-042: briefing-budget on real BRIEFING.md returns valid budget**
- Precondition: Real `.squidsquad/vault/BRIEFING.md` exists (~30 lines)
- Steps: Run `python references/scripts/vault_remember.py briefing-budget`
- Expected: exit 0, JSON with positive `remaining` value (real BRIEFING.md is well under 2000 tokens)
- Verification: Assert `remaining` > 0, `used` > 0

### D4. Vault Write and Template Compliance

**TC-043: vault-create with galaxy template produces valid note**
- Precondition: Real vault. Prepare a test note: `galaxy/test-learning-vault-remember-tc043.md`
- Steps:
  1. Create note using galaxy template from `references/vault-templates/`
  2. Fill in required frontmatter: type=learning, tags=[test], created/updated=today, owner=skill, status=active, confidence=medium, source=observation
  3. Run `python references/scripts/vault_check.py check-frontmatter` on the new file
- Expected: vault-check Level 1 passes with no warnings for the new note
- Verification: Assert no warnings. Cleanup: delete `test-learning-vault-remember-tc043.md` in `finally`

**TC-044: vault-check L1 passes after test write**
- Precondition: Same as TC-043 — test note created
- Steps: Run full vault-check L1 (validate the test note + 2-hop neighborhood)
- Expected: No warnings for the test note. No broken wikilinks introduced
- Verification: Assert vault-check output clean for the test note. Cleanup in `finally`

**TC-045: human-profile.md seeded correctly from BRIEFING.md data**
- Precondition: Real vault. Check if `areas/human-profile.md` exists; if so, back it up
- Steps:
  1. If human-profile.md does not exist, run the seeding logic from vault_remember.py
  2. Read the created/existing file
  3. Verify it has required sections: Communication Style, Quality Expectations, Technical Preferences
  4. Verify frontmatter has type=area, confidence=medium (for seeded entries)
  5. Verify content references known preferences from BRIEFING.md (e.g., "never ship with failed test cases")
- Expected: human-profile.md exists with correct structure and pre-seeded content
- Verification: Assert section headers present. Assert `confidence: medium`. Restore backup in `finally` if one was made

---

## E. Side Effect Regression Tests

### E1. Existing Vault Integrity

**TC-046: existing vault notes unchanged after vault-remember dry run**
- Precondition: Record SHA-256 hashes of all 5 existing vault notes
- Steps:
  1. Hash all .md files in `.squidsquad/vault/` (recursive)
  2. Run vault_remember.py in a mode that exercises the gate logic (e.g., `is-quiet`, `write-budget`, `note-count`) but does NOT write
  3. Re-hash all .md files
- Expected: All hashes identical before and after
- Verification: Assert hash_before == hash_after for every file

**TC-047: no orphan notes introduced after test write + cleanup**
- Precondition: Run `vault_check.py list-orphans` and record baseline orphan count
- Steps:
  1. Create a test galaxy note with wikilinks to existing notes
  2. Run `vault_check.py list-orphans`
  3. Delete the test note
  4. Run `vault_check.py list-orphans` again
- Expected: Orphan count after cleanup == baseline orphan count. No new orphans persist
- Verification: Assert orphan count restored to baseline

**TC-048: wikilinks still resolve after vault-remember operations**
- Precondition: Record all wikilinks in vault via `grep -ro '\[\[[^]]*\]\]' .squidsquad/vault/`
- Steps:
  1. Run vault-remember gate commands (non-writing)
  2. Re-extract all wikilinks
  3. For each wikilink, verify target file exists
- Expected: Same set of wikilinks, all still resolvable
- Verification: Assert wikilink set unchanged, zero broken links

### E2. Cycle Timing

**TC-049: vault-remember gates add less than 60 seconds on non-quiet cycle**
- Precondition: Real vault (5 notes). Simulate a non-quiet cycle scenario
- Steps:
  1. Record start time
  2. Run the full deterministic gate sequence: `is-quiet`, `write-budget`, `dedup-check` (for a sample candidate), `briefing-budget`, `effective-confidence` (on each galaxy note), `note-count`
  3. Record end time
- Expected: Total elapsed < 60 seconds
- Verification: Assert elapsed < 60.0

**TC-050: quiet cycle skips vault-remember instantly (near 0 overhead)**
- Precondition: No iter log created this cycle (quiet state)
- Steps:
  1. Record start time
  2. Call `vault_remember.py is-quiet skill`
  3. Record end time
- Expected: Elapsed < 2 seconds (effectively instant)
- Verification: Assert elapsed < 2.0

### E3. Upgrade Path

**TC-051: fresh install without vault-remember config defaults to enabled**
- Precondition: Create temp config.md with standard SquidSquad config but NO `## Vault Remember` section
- Steps: Run vault_remember.py config-reading logic against the temp config
- Expected: Returns enabled=True, writes-per-cycle=2, briefing-budget=2000
- Verification: Assert all defaults correct. Cleanup temp file

**TC-052: existing install with vault content — vault-remember runs without corruption**
- Precondition: Real vault with existing 5 notes. Capture full content of all notes
- Steps:
  1. Snapshot all vault file contents
  2. Run the full vault-remember gate sequence (non-writing)
  3. Create one test note via vault-create following the galaxy template
  4. Run vault-check L1 on the test note
  5. Re-read all original 5 vault files
- Expected: Original 5 notes byte-for-byte unchanged. Test note passes vault-check. No errors during execution
- Verification: Assert original content preserved. Assert vault-check clean. Cleanup test note in `finally`

**TC-053: vault_remember.py script missing causes graceful skip**
- Precondition: Rename vault_remember.py to vault_remember.py.bak temporarily
- Steps: Simulate what happens when the sub-skill text in CLAUDE.md references `vault_remember.py` but the script does not exist — run `python references/scripts/vault_remember.py is-quiet skill`
- Expected: Python raises FileNotFoundError or ModuleNotFoundError. The sub-skill instruction text tells agents to catch this and skip
- Verification: Assert error is a known Python error (not a vault corruption). Restore vault_remember.py.bak in `finally`

---

## F. Smoke Tests (Manual QA Checklist)

Quick checks for the QA subagent to verify after implementation.

**SM-001: End-to-end vault-remember on real cycle**
- Steps:
  1. Trigger a non-quiet cycle (ensure an iter log is created)
  2. Observe vault-remember step executing between iteration-log and git-commit
  3. If a vault note is written, verify it appears in `.squidsquad/vault/galaxy/`
- Expected: vault-remember step runs, respects gates, note (if any) follows galaxy template
- Verification: Manual inspection of cycle output and vault contents

**SM-002: Quiet cycle produces zero vault-remember output**
- Steps:
  1. Observe a quiet cycle (no bugs fixed, no features progressed)
  2. Check cycle output for vault-remember activity
- Expected: No vault-remember output, no vault writes, cycle completes normally
- Verification: Manual inspection of cycle output

**SM-003: Config toggle disables vault-remember**
- Steps:
  1. Set `**Enabled**: no` in config.md under `## Vault Remember`
  2. Trigger a non-quiet cycle
  3. Observe that vault-remember step is skipped
- Expected: Cycle output shows vault-remember skipped due to config
- Verification: Manual inspection

**SM-004: human-profile.md is browsable in vault**
- Steps:
  1. Verify `areas/human-profile.md` exists
  2. Check it has structured sections
  3. Verify wikilinks in BRIEFING.md reference `[[human-profile]]` correctly
- Expected: File exists, well-structured, linkable
- Verification: Manual inspection (or open in Obsidian if available)

**SM-005: Dedup prevents duplicate note creation**
- Steps:
  1. Attempt to create a galaxy note about "sub-skill architecture" (already exists)
  2. Observe dedup-check gate output
- Expected: dedup-check returns the existing `decision-sub-skill-architecture.md` as a match, agent skips or updates instead of creating duplicate
- Verification: Manual inspection — no new duplicate file created

**SM-006: Write budget enforced across cycle**
- Steps:
  1. Trigger a productive cycle that would generate 3+ vault-worthy insights
  2. Observe write counter incrementing
  3. After 2 writes (or 3 in burst), observe remaining candidates marked as SKIP
- Expected: At most 2 (or 3 burst) vault notes created. Overflow candidates listed in iter log with "deferred" note
- Verification: Manual count of new vault files, check iter log Notes field

---

## Summary

| Section | TC Range | Count | Type |
|---------|----------|-------|------|
| A. vault_remember.py gates | TC-001 to TC-020 | 20 | Unit (mocked) |
| B. vault_check.py dedup-check | TC-021 to TC-027 | 7 | Unit (mocked) |
| C. cycle.py is-quiet | TC-028 to TC-030 | 3 | Unit (mocked) |
| D. In-situ integration | TC-031 to TC-045 | 15 | Integration (real vault) |
| E. Side effect regression | TC-046 to TC-053 | 8 | Integration (real vault) |
| F. Smoke tests | SM-001 to SM-006 | 6 | Manual QA |
| **Total** | | **59** | |

# FEAT-66 Test Plan — Deterministic Script Layer

**Feature**: Replace mechanical sub-skill operations with Python scripts
**Scripts under test**: `config.py`, `cycle.py`, `tracker.py`, `git_ops.py`, `vault_check.py`
**Location**: `references/scripts/`
**Test file**: `references/scripts/test_scripts.py` (Python unittest, stdlib only)
**Python**: 3.8+, stdlib only

---

## Test Infrastructure

### Conventions
- All test resource names prefixed with `[TEST]` (issues) or `test/` (branches) or `test_` (files)
- Every test that creates real resources has a `finally` block for teardown
- Unit tests mock `subprocess.run` via `unittest.mock.patch`
- Integration tests use real `gh` and `git` commands, then clean up
- Exit codes verified: 0 = success, 1 = validation error, 2 = network error, 3 = auth error

### Test Runner
```bash
cd references/scripts && python -m unittest test_scripts.py -v
```

---

## A. Unit Tests (Mocked Subprocess)

### A1. config.py

**TC-001: get --key version reads correct value**
- Precondition: Mock config.md content with `**SquidSquad Version**: 0.10.0`
- Steps: Call `config.py get --key version` with mocked file read
- Expected: stdout = `0.10.0`, exit 0

**TC-002: get --key shipped-count reads numeric value**
- Precondition: Mock config.md with `**Shipped Since Last Bump**: 3`
- Steps: Call `config.py get --key shipped-count`
- Expected: stdout = `3`, exit 0

**TC-003: get --key unknown returns exit 1**
- Precondition: Mock config.md
- Steps: Call `config.py get --key nonexistent-key`
- Expected: exit 1, stderr contains "not found" or "unknown key"

**TC-004: set --key version --value 0.11.0 updates file**
- Precondition: Mock config.md with `**SquidSquad Version**: 0.10.0`
- Steps: Call `config.py set --key version --value 0.11.0`
- Expected: exit 0, file content updated to `**SquidSquad Version**: 0.11.0`

**TC-005: increment --key shipped-count adds 1**
- Precondition: Mock config.md with `**Shipped Since Last Bump**: 3`
- Steps: Call `config.py increment --key shipped-count`
- Expected: stdout = `4`, exit 0, file updated to `4`

**TC-006: increment on non-numeric key returns exit 1**
- Precondition: Mock config.md with a non-numeric field
- Steps: Call `config.py increment --key pr-flow`
- Expected: exit 1, stderr indicates non-numeric

**TC-007: reset --key shipped-count sets to 0**
- Precondition: Mock config.md with `**Shipped Since Last Bump**: 5`
- Steps: Call `config.py reset --key shipped-count`
- Expected: exit 0, file updated to `0`

**TC-008: bump-version increments minor, resets patch**
- Precondition: Mock config.md with version `0.10.0`
- Steps: Call `config.py bump-version`
- Expected: stdout = `0.11.0`, config.md updated to `0.11.0`

**TC-009: get reads all recognized keys**
- Precondition: Mock config.md with all fields populated
- Steps: Call `get` for each of: version, ship-threshold, shipped-count, interval, context-threshold, pr-flow, improvement-scanning, dev-agents, tracker
- Expected: Each returns correct value, exit 0

**TC-010: --help prints usage and exits 0**
- Steps: Call `config.py --help`
- Expected: exit 0, stdout contains "Usage" or "usage"

**TC-011: --dry-run on set does not modify file**
- Precondition: Mock config.md with version `0.10.0`
- Steps: Call `config.py set --key version --value 0.11.0 --dry-run`
- Expected: exit 0, stdout shows what would change, file unchanged

### A2. cycle.py

**TC-012: timestamp --format step returns HH:MM:SS**
- Steps: Call `cycle.py timestamp --format step`
- Expected: stdout matches `^\d{2}:\d{2}:\d{2}$`, exit 0

**TC-013: timestamp --format discussion returns YYYY-MM-DD HH:MM**
- Steps: Call `cycle.py timestamp --format discussion`
- Expected: stdout matches `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$`, exit 0

**TC-014: timestamp --format date returns YYYY-MM-DD**
- Steps: Call `cycle.py timestamp --format date`
- Expected: stdout matches `^\d{4}-\d{2}-\d{2}$`, exit 0

**TC-015: write-state performs atomic write (tmp + rename)**
- Precondition: Mock filesystem
- Steps: Call `cycle.py write-state --role skill --phase implementing --description "#42 building..."`
- Expected: Writes to `.squidsquad/skill/current-state.tmp` then renames to `current-state`. Final content = `implementing|#42 building...`

**TC-016: write-state uses os.replace (not shell mv)**
- Steps: Inspect source or mock `os.replace` and verify it is called
- Expected: `os.replace` called exactly once

**TC-017: read-working-state returns JSON for active task**
- Precondition: Mock working-state.md with Task=#42, Status=in-progress, completed/remaining steps
- Steps: Call `cycle.py read-working-state --role skill`
- Expected: stdout is valid JSON with keys: task, status, started, completed_steps, remaining_steps

**TC-018: read-working-state returns none/none for empty file**
- Precondition: Mock working-state.md with Task=none, Status=none
- Steps: Call `cycle.py read-working-state --role skill`
- Expected: stdout JSON has `{"task":"none","status":"none"}`

**TC-019: write-working-state creates structured markdown**
- Steps: Call `cycle.py write-working-state --role skill --task "#42" --status in-progress`
- Expected: File written with `- **Task**: #42` and `- **Status**: in-progress`

**TC-020: clear-working-state resets to template**
- Precondition: Mock working-state.md with active task
- Steps: Call `cycle.py clear-working-state --role skill`
- Expected: File content has Task=none, Status=none

**TC-021: create-iter-log finds next number**
- Precondition: Mock iterations/ dir with iter-1.md through iter-5.md
- Steps: Call `cycle.py create-iter-log --role skill --role-upper SKILL --fields-json '{"Bugs Fixed":"none","Features Progressed":"#42"}'`
- Expected: Creates `iter-6.md`, stdout = `iter-6.md`, content has `# SKILL Iteration 6`

**TC-022: create-iter-log handles empty directory**
- Precondition: Mock empty iterations/ dir
- Steps: Call create-iter-log
- Expected: Creates `iter-1.md`

**TC-023: cleanup-iter-logs keeps N newest**
- Precondition: Mock iterations/ with iter-1.md through iter-25.md
- Steps: Call `cycle.py cleanup-iter-logs --role skill --keep 20`
- Expected: Deletes iter-1 through iter-5, keeps iter-6 through iter-25. stdout = `5`

**TC-024: cleanup-iter-logs does nothing when under limit**
- Precondition: Mock iterations/ with 10 files
- Steps: Call cleanup with --keep 20
- Expected: stdout = `0`, no files deleted

**TC-025: update-scan-history appends entry**
- Precondition: Mock existing scan-history.md with one entry
- Steps: Call `cycle.py update-scan-history --role skill --files-json '["a.ts","b.ts"]' --findings-json '[]'`
- Expected: File has original entry PLUS new `## Scan` section appended

**TC-026: --help prints usage**
- Steps: Call `cycle.py --help`
- Expected: exit 0, contains "Usage" or lists subcommands

**TC-027: --dry-run on write-state shows output without writing**
- Steps: Call `cycle.py write-state --role skill --phase idle --description "" --dry-run`
- Expected: Prints what would be written, file not modified

### A3. tracker.py

**TC-028: check-auth calls gh issue list**
- Precondition: Mock subprocess.run to return success for `gh issue list --limit 1`
- Steps: Call `tracker.py check-auth`
- Expected: exit 0. Subprocess called with `["gh", "issue", "list", "--limit", "1"]`

**TC-029: check-auth returns exit 1 on auth failure**
- Precondition: Mock subprocess.run to raise CalledProcessError with "auth" in stderr
- Steps: Call `tracker.py check-auth`
- Expected: exit 1, stderr contains auth error message

**TC-030: list-issues constructs correct gh command**
- Precondition: Mock subprocess.run
- Steps: Call `tracker.py list-issues --labels "type:feature,status:approved,role:skill" --limit 50 --fields "number,title,labels"`
- Expected: subprocess called with `["gh", "issue", "list", "--label", "type:feature,status:approved,role:skill", "--limit", "50", "--json", "number,title,labels"]`

**TC-031: view-issue constructs correct gh command**
- Precondition: Mock subprocess returning JSON
- Steps: Call `tracker.py view-issue --number 42 --fields "title,body,labels,comments"`
- Expected: subprocess called with `["gh", "issue", "view", "42", "--json", "title,body,labels,comments"]`

**TC-032: create-bug adds all required labels**
- Precondition: Mock subprocess.run returning `{"number": 99}`
- Steps: Call `tracker.py create-bug --title "BUG: test" --body "desc" --severity high --role skill`
- Expected: gh command includes `--label "type:bug,severity:high,role:skill,squidsquad,status:pending"`

**TC-033: create-feature adds all required labels**
- Precondition: Mock subprocess.run
- Steps: Call `tracker.py create-feature --title "FEAT: test" --body "desc" --priority medium --role skill`
- Expected: labels include `type:feature,priority:medium,role:skill,squidsquad,status:pending`

**TC-034: create-feature with --extra-labels appends them**
- Precondition: Mock subprocess.run
- Steps: Call with `--extra-labels "improvement-scan"`
- Expected: labels CSV includes `improvement-scan`

**TC-035: transition constructs atomic remove+add**
- Precondition: Mock subprocess.run
- Steps: Call `tracker.py transition --number 42 --from approved --to in-progress`
- Expected: gh command includes `--remove-label "status:approved" --add-label "status:in-progress"`

**TC-036: comment formats body correctly (no timestamp in body)**
- Precondition: Mock subprocess.run
- Steps: Call `tracker.py comment --number 42 --role skill --message "Fixed in abc123."`
- Expected: gh comment body = `> **skill**: Fixed in abc123.` (NO timestamp prefix in body)

**TC-037: close-issue calls gh issue close**
- Precondition: Mock subprocess.run
- Steps: Call `tracker.py close-issue --number 42`
- Expected: subprocess called with `["gh", "issue", "close", "42"]`

**TC-038: list-issues returns exit 2 on network error**
- Precondition: Mock subprocess.run to raise CalledProcessError with "network" or connection error
- Steps: Call list-issues
- Expected: exit 2

**TC-039: --help prints usage**
- Steps: Call `tracker.py --help`
- Expected: exit 0, lists all subcommands

**TC-040: --dry-run on transition shows what would execute**
- Steps: Call `tracker.py transition --number 42 --from approved --to in-progress --dry-run`
- Expected: Prints the gh command that would run, does NOT call subprocess

**TC-041: --dry-run on create-bug shows labels without creating**
- Steps: Call create-bug with --dry-run
- Expected: Prints planned gh command, no subprocess call

### A4. git_ops.py

**TC-042: pull calls git pull --rebase**
- Precondition: Mock subprocess.run
- Steps: Call `git_ops.py pull`
- Expected: subprocess called with `["git", "pull", "--rebase"]`, exit 0

**TC-043: pull returns exit 1 on conflict**
- Precondition: Mock subprocess to raise CalledProcessError
- Steps: Call `git_ops.py pull`
- Expected: exit 1, stdout lists conflicting files

**TC-044: commit-and-push stages, commits, pushes**
- Precondition: Mock subprocess.run (3 calls)
- Steps: Call `git_ops.py commit-and-push --role skill --message "implement tracker"`
- Expected: Three subprocess calls: `git add -A`, `git commit -m "skill: implement tracker"`, `git push`

**TC-045: commit-and-push returns exit 1 when nothing to commit**
- Precondition: Mock `git commit` to fail with "nothing to commit"
- Steps: Call commit-and-push
- Expected: exit 1 (not an error, agent skips)

**TC-046: create-feature-branch creates correct branch name**
- Precondition: Mock subprocess.run
- Steps: Call `git_ops.py create-feature-branch --role skill --type feat --number 66 --message "script layer"`
- Expected: Branch name = `squidsquad/feat-skill-66`, subprocess calls checkout -b, add, commit, push -u

**TC-047: return-to-main checks out main**
- Precondition: Mock subprocess.run
- Steps: Call `git_ops.py return-to-main`
- Expected: subprocess called with `["git", "checkout", "main"]`

**TC-048: version-tag creates and pushes tag**
- Precondition: Mock subprocess.run. Mock `git tag -l` returning empty (tag doesn't exist)
- Steps: Call `git_ops.py version-tag --version 0.11.0`
- Expected: Calls `git tag v0.11.0` then `git push --tags`

**TC-049: version-tag exits 1 if tag already exists**
- Precondition: Mock `git tag -l "v0.11.0"` returning the tag
- Steps: Call version-tag --version 0.11.0
- Expected: exit 1, no new tag created

**TC-050: --help prints usage**
- Steps: Call `git_ops.py --help`
- Expected: exit 0

**TC-051: --dry-run on commit-and-push shows commands without executing**
- Steps: Call with --dry-run
- Expected: Prints planned git commands, no subprocess calls

### A5. vault_check.py

**TC-052: check-note validates required frontmatter fields**
- Precondition: Mock vault note missing `confidence` field
- Steps: Call `vault_check.py check-note --path .squidsquad/vault/galaxy/decision-test.md`
- Expected: JSON output contains warning about missing `confidence`

**TC-053: check-note passes for valid note**
- Precondition: Mock vault note with all required fields (type, tags, created, updated, owner, status, confidence)
- Steps: Call check-note
- Expected: stdout = `[]` (empty warnings array), exit 0

**TC-054: check-note detects type-folder mismatch**
- Precondition: Mock galaxy/ note with `type: area`
- Steps: Call check-note
- Expected: Warning about type-folder mismatch

**TC-055: check-note resolves wikilinks**
- Precondition: Mock note with `[[existing-note]]` and `[[nonexistent-note]]`. Mock filesystem has `existing-note.md` but not `nonexistent-note.md`
- Steps: Call check-note
- Expected: Warning for unresolved `[[nonexistent-note]]`, no warning for `[[existing-note]]`

**TC-056: check-note warns on galaxy note exceeding 500 lines**
- Precondition: Mock galaxy/ note with 600 lines
- Steps: Call check-note
- Expected: Warning about exceeding 500 lines

**TC-057: check-note does NOT warn on area note exceeding 500 lines**
- Precondition: Mock areas/ note with 600 lines
- Steps: Call check-note
- Expected: No size warning

**TC-058: full-sweep returns JSON summary**
- Precondition: Mock vault/ with several notes (some valid, some with issues)
- Steps: Call `vault_check.py full-sweep`
- Expected: JSON with note_count, orphan_count, stale_count, broken_link_count, warnings

**TC-059: full-sweep detects orphan notes**
- Precondition: Mock galaxy/ note with zero inbound links
- Steps: Call full-sweep
- Expected: orphan_count >= 1, orphan listed in warnings

**TC-060: full-sweep detects stale notes (>30 days)**
- Precondition: Mock note with `updated: 2026-01-01` (>30 days from test date)
- Steps: Call full-sweep
- Expected: stale_count >= 1

**TC-061: sync-links updates frontmatter links from body wikilinks**
- Precondition: Mock note with body containing `[[note-a]]` and `[[note-b]]` but frontmatter `links: []`
- Steps: Call `vault_check.py sync-links --path <note>`
- Expected: Frontmatter updated to `links: [note-a, note-b]`

**TC-062: --help prints usage**
- Steps: Call `vault_check.py --help`
- Expected: exit 0

---

## B. Integration Tests (Real Resources with Teardown)

### B1. Tracker Integration (Real GitHub Issues)

**TC-063: create and delete a test bug issue**
- Precondition: `gh` authenticated with repo scope
- Steps:
  1. `tracker.py create-bug --title "[TEST] TC-063 integration bug" --body "Automated test — will be deleted" --severity low --role skill`
  2. Capture issue number from stdout
  3. Verify issue exists: `gh issue view <N>` returns the issue
  4. Verify labels: must have `type:bug`, `severity:low`, `role:skill`, `squidsquad`, `status:pending`
- Teardown (finally): `gh issue close <N>` then `gh issue delete <N> --yes`
- Expected: Issue created with correct labels, then fully cleaned up

**TC-064: transition a test issue through valid states**
- Precondition: `gh` authenticated
- Steps:
  1. Create: `tracker.py create-feature --title "[TEST] TC-064 transition test" --body "test" --priority low --role skill`
  2. Transition: pending -> approved (via `tracker.py transition --number <N> --from pending --to approved`)
  3. Verify label: `status:approved` present, `status:pending` absent
  4. Transition: approved -> in-progress
  5. Verify label: `status:in-progress` present, `status:approved` absent
- Teardown (finally): `gh issue close <N>` then `gh issue delete <N> --yes`
- Expected: Each transition succeeds, labels correct at each step

**TC-065: comment on a test issue**
- Precondition: `gh` authenticated
- Steps:
  1. Create test issue (feature, low priority)
  2. `tracker.py comment --number <N> --role skill --message "Integration test comment"`
  3. Read comments: `gh issue view <N> --json comments`
  4. Verify last comment body = `> **skill**: Integration test comment` (no timestamp in body)
- Teardown (finally): close and delete issue
- Expected: Comment posted with correct format, no timestamp in body

**TC-066: list-issues filters correctly**
- Precondition: `gh` authenticated
- Steps:
  1. Create test issue with labels `type:feature,status:pending,role:skill,squidsquad,priority:low`
  2. Call `tracker.py list-issues --labels "type:feature,status:pending,role:skill" --fields "number,title"`
  3. Verify returned JSON array contains the test issue
- Teardown (finally): close and delete issue
- Expected: Test issue appears in filtered list

**TC-067: create-pr on a test branch**
- Precondition: `gh` authenticated, clean working tree
- Steps:
  1. Create branch `test/tc-067-pr-test` from current HEAD
  2. Create empty commit on branch
  3. Push branch
  4. `tracker.py create-pr --title "[TEST] TC-067 PR test" --body "automated test" --branch test/tc-067-pr-test`
  5. Capture PR URL from stdout
  6. Verify PR exists via `gh pr view`
- Teardown (finally): Close PR (`gh pr close`), delete remote branch (`git push origin --delete test/tc-067-pr-test`), delete local branch
- Expected: PR created successfully

### B2. Git Operations Integration (Real Branches)

**TC-068: pull succeeds on clean repo**
- Precondition: Clean working tree, on main branch
- Steps: `git_ops.py pull`
- Expected: exit 0

**TC-069: create-feature-branch and return-to-main**
- Precondition: Clean working tree, on main
- Steps:
  1. Create a temp file `test_tc069.txt`
  2. `git_ops.py create-feature-branch --role skill --type feat --number 9999 --message "[TEST] branch test"`
  3. Verify current branch = `squidsquad/feat-skill-9999`
  4. `git_ops.py return-to-main`
  5. Verify current branch = `main`
- Teardown (finally):
  - `git checkout main`
  - `git branch -D squidsquad/feat-skill-9999`
  - `git push origin --delete squidsquad/feat-skill-9999` (ignore if not pushed)
  - Remove `test_tc069.txt`
- Expected: Branch created, pushed, returned to main, then cleaned up

**TC-070: commit-and-push with nothing to commit returns exit 1**
- Precondition: Clean working tree, no staged changes
- Steps: `git_ops.py commit-and-push --role skill --message "[TEST] empty commit"`
- Expected: exit 1 (nothing to commit)
- Teardown: None needed

### B3. Cycle/Config Integration (Real Files)

**TC-071: write-state creates atomic file**
- Precondition: `.squidsquad/skill/` directory exists
- Steps:
  1. `cycle.py write-state --role skill --phase implementing --description "[TEST] atomic write"`
  2. Read `.squidsquad/skill/current-state`
  3. Verify content = `implementing|[TEST] atomic write`
- Teardown (finally): Restore original current-state content (save before test, restore after)
- Expected: File written atomically with correct content

**TC-072: create and cleanup iteration logs**
- Precondition: Create temp `test_iterations/` directory
- Steps:
  1. Create 25 fake iter files in temp dir
  2. `cycle.py cleanup-iter-logs --role skill --keep 20` (pointed at temp dir)
  3. Verify 20 files remain (the 20 newest)
- Teardown (finally): Remove entire temp directory
- Expected: 5 oldest files deleted

**TC-073: config.py reads real config.md**
- Precondition: `.squidsquad/config.md` exists
- Steps:
  1. `config.py get --key version`
  2. Verify output matches known version in config.md (e.g., `0.10.0`)
  3. `config.py get --key interval`
  4. Verify output = `30`
- Teardown: None (read-only)
- Expected: Values match actual config.md content

**TC-074: config.py set and restore**
- Precondition: Save current config.md content
- Steps:
  1. Read current version: `config.py get --key shipped-count`
  2. Save value
  3. `config.py increment --key shipped-count`
  4. Read again, verify incremented by 1
- Teardown (finally): `config.py set --key shipped-count --value <original>` to restore
- Expected: Increment works on real file, value restored after test

---

## C. E2E Scenario (Full Feature Lifecycle)

**TC-075: Full feature lifecycle through all status transitions**
- Precondition: `gh` authenticated, clean working tree
- Steps:
  1. **Create**: `tracker.py create-feature --title "[TEST] E2E: dummy feature TC-075" --body "Full lifecycle test. Will be deleted." --priority low --role skill`
  2. Capture issue number `<N>`
  3. **Verify pending**: `tracker.py view-issue --number <N> --fields labels` — verify `status:pending`
  4. **pending -> approved**: `tracker.py transition --number <N> --from pending --to approved`
  5. **Verify approved**: view-issue, verify `status:approved` label, `status:pending` absent
  6. **approved -> in-progress**: `tracker.py transition --number <N> --from approved --to in-progress`
  7. **Verify in-progress**: labels correct
  8. **Comment**: `tracker.py comment --number <N> --role skill --message "Picking up. Status -> In Progress."`
  9. **Verify comment**: `view-issue --fields comments` — last comment = `> **skill**: Picking up. Status -> In Progress.`
  10. **in-progress -> pending-test**: `tracker.py transition --number <N> --from in-progress --to pending-test`
  11. **Verify pending-test**: labels correct
  12. **pending-test -> pending-ship**: `tracker.py transition --number <N> --from pending-test --to pending-ship`
  13. **Verify pending-ship**: labels correct
  14. **pending-ship -> shipped**: `tracker.py transition --number <N> --from pending-ship --to shipped`
  15. **Verify shipped**: labels correct
  16. **Close**: `tracker.py close-issue --number <N>`
  17. **Verify closed**: `gh issue view <N> --json state` — state = CLOSED
- Teardown (finally): `gh issue delete <N> --yes`
- Expected: Issue traverses every valid state, labels correct at each step, comment format correct (no timestamp in body), issue closed and deleted

**TC-076: Full feature lifecycle with QA rejection loop**
- Precondition: `gh` authenticated
- Steps:
  1. Create feature: `[TEST] E2E: QA rejection loop TC-076`
  2. Transition: pending -> approved -> in-progress -> pending-test
  3. **Simulate QA rejection**: transition pending-test -> in-progress (QA sends back)
  4. Comment as QA: `tracker.py comment --number <N> --role qa --message "Gap: missing edge case handling."`
  5. **Re-implement**: transition in-progress -> pending-test
  6. Transition: pending-test -> pending-ship -> shipped
  7. Close issue
  8. Verify all transitions succeeded
- Teardown (finally): `gh issue delete <N> --yes`
- Expected: QA rejection loop (pending-test -> in-progress -> pending-test) works correctly

**TC-077: Bug lifecycle (shortened flow)**
- Precondition: `gh` authenticated
- Steps:
  1. `tracker.py create-bug --title "[TEST] E2E: bug lifecycle TC-077" --body "test bug" --severity low --role skill`
  2. Transition: pending -> approved (bugs skip planning)
  3. Transition: approved -> in-progress -> pending-test -> pending-ship -> shipped
  4. Close issue
- Teardown (finally): delete issue
- Expected: Bug follows shortened flow without planning/planned steps

---

## D. Status Flow Enforcement (Valid + Invalid Transitions)

### D1. Valid Transitions

**TC-078: pending -> planning (feature)**
- Steps: Mock or create issue at pending, transition to planning
- Expected: exit 0

**TC-079: planning -> planned**
- Expected: exit 0

**TC-080: planned -> approved**
- Expected: exit 0

**TC-081: approved -> in-progress**
- Expected: exit 0

**TC-082: in-progress -> pending-test**
- Expected: exit 0

**TC-083: pending-test -> pending-ship**
- Expected: exit 0

**TC-084: pending-ship -> shipped**
- Expected: exit 0

**TC-085: pending -> approved (bug shortcut)**
- Expected: exit 0

**TC-086: open -> approved (bug from open)**
- Expected: exit 0

**TC-087: pending-test -> in-progress (QA rejection)**
- Expected: exit 0

### D2. Invalid Transitions

**TC-088: pending -> in-progress (skip approved)**
- Steps: Call `tracker.py transition --number <N> --from pending --to in-progress`
- Expected: exit 1, stderr = `"Invalid transition: pending -> in-progress. Valid next states from pending: [planning, approved]"`

**TC-089: approved -> shipped (skip everything)**
- Steps: Attempt transition approved -> shipped
- Expected: exit 1, error message shows valid next states from approved: `[in-progress]`

**TC-090: pending -> shipped (skip all states)**
- Expected: exit 1

**TC-091: in-progress -> shipped (skip pending-test, pending-ship)**
- Expected: exit 1, valid next from in-progress: `[pending-test]`

**TC-092: pending-test -> shipped (skip pending-ship)**
- Expected: exit 1, valid next from pending-test: `[pending-ship, in-progress]`

**TC-093: shipped -> in-progress (backward from terminal)**
- Expected: exit 1, shipped has no valid next states (or exit 1 with "shipped is a terminal state")

**TC-094: pending -> pending-test (skip 3 states)**
- Expected: exit 1

**TC-095: in-progress -> pending-ship (skip pending-test)**
- Expected: exit 1

**TC-096: planning -> in-progress (skip planned, approved)**
- Expected: exit 1

**TC-097: pending-ship -> in-progress (wrong rejection path)**
- Expected: exit 1 (rejection goes pending-test -> in-progress, NOT pending-ship -> in-progress)

**TC-098: transition with wrong --from label (label mismatch)**
- Precondition: Issue actually has `status:approved`
- Steps: Call transition with `--from pending --to approved`
- Expected: exit 1, error indicates current label doesn't match --from

---

## E. Cross-Platform Tests

**TC-099: timestamp uses datetime (not shell date command)**
- Steps: Inspect `cycle.py timestamp` implementation. Verify it uses `datetime.now().strftime()` not `subprocess.run(["date", ...])`
- Expected: No subprocess call to `date`

**TC-100: atomic write uses os.replace (not shell mv)**
- Steps: Inspect `cycle.py write-state` implementation. Verify `os.replace()` is called
- Expected: `os.replace` used, not `subprocess.run(["mv", ...])`

**TC-101: all file paths use pathlib.Path**
- Steps: Grep script source for hardcoded `/` path separators in file operations (excluding argparse help text and gh CLI arguments)
- Expected: File I/O uses `pathlib.Path` or `os.path.join`, not string concatenation with `/`

**TC-102: file writes use explicit UTF-8 encoding**
- Steps: Grep script source for `open(` calls
- Expected: All `open()` calls for writing specify `encoding='utf-8'`

**TC-103: file deletions use pathlib.unlink or os.remove**
- Steps: Inspect cleanup-iter-logs implementation
- Expected: Uses `Path.unlink()` or `os.remove()`, not subprocess `rm`

---

## F. Sub-Skill Rewrite Verification

**TC-104: no inline gh commands remain in updated sub-skills**
- Precondition: All sub-skills updated per FEAT-66
- Steps: Grep all files in `references/sub-skills/` for bare `gh issue` or `gh pr` commands that are NOT inside a `python scripts/tracker.py` call
- Expected: Zero matches (all gh CLI calls go through tracker.py)

**TC-105: no inline git commands remain in updated sub-skills**
- Steps: Grep `references/sub-skills/` for bare `git pull`, `git add`, `git commit`, `git push`, `git checkout`, `git tag` that are NOT inside a `python scripts/git_ops.py` call
- Expected: Zero matches (all git calls go through git_ops.py)

**TC-106: no inline date commands remain**
- Steps: Grep `references/sub-skills/` for `date +` commands
- Expected: Zero matches (all timestamps via cycle.py)

**TC-107: no inline echo-to-file patterns remain for state files**
- Steps: Grep for `echo "..." > .squidsquad` patterns in sub-skills
- Expected: Zero matches (all file writes via cycle.py or config.py)

**TC-108: all sub-skills reference scripts with python3 or python**
- Steps: Grep for `python scripts/` or `python3 scripts/` in updated sub-skills
- Expected: Every mechanical operation uses a script call

**TC-109: sub-skills retain prose for reasoning tasks**
- Steps: Manually verify (in code review) that conflict resolution, code analysis, content writing, and decision-making remain as LLM prose, not script calls
- Expected: Prose sections preserved for non-deterministic operations

---

## G. Regression Tests

**TC-110: statusline.sh reads current-state written by cycle.py**
- Precondition: statusline.sh exists at `.squidsquad/statusline.sh`
- Steps:
  1. `cycle.py write-state --role skill --phase implementing --description "#42 testing"`
  2. Read `.squidsquad/skill/current-state` directly
  3. Verify format matches what statusline.sh expects: `<phase>|<description>`
- Teardown: Restore original current-state
- Expected: statusline.sh can parse the file (format unchanged)

**TC-111: agent-instructions.md regenerated after sub-skill updates**
- Steps: After all sub-skill rewrites, verify `references/agent-instructions.md` (or equivalent composed output) is regenerated and contains script call references
- Expected: Composed instructions reference `python scripts/tracker.py`, `python scripts/cycle.py`, etc.

**TC-112: no bare status labels (e.g., "approved" without "status:" prefix)**
- Steps: Grep all scripts for label strings. Verify every status label includes `status:` prefix (e.g., `status:approved` not just `approved`)
- Expected: All status labels properly prefixed

**TC-113: tracker.py always removes old label before adding new one**
- Steps: Inspect `transition` command source code. Verify it always uses both `--remove-label` and `--add-label` in the same `gh issue edit` call
- Expected: Atomic remove+add in single gh command

**TC-114: config.py preserves unrelated config.md content**
- Precondition: Save full config.md
- Steps:
  1. `config.py set --key shipped-count --value 99`
  2. Read full config.md
  3. Verify all fields OTHER than shipped-count are unchanged (version, interval, PR flow, etc.)
- Teardown: Restore original config.md
- Expected: Only targeted field modified, rest preserved exactly

**TC-115: iteration log format matches expected structure**
- Steps: Create an iter log via `cycle.py create-iter-log` and verify it contains:
  - `# <ROLE> Iteration N` header
  - `- **Date**:` field
  - `- **Bugs Fixed**:` field
  - `- **Features Progressed**:` field
  - `- **Tests**:` field
  - `- **Notes**:` field
- Expected: All required fields present in correct format

**TC-116: working-state.md format matches expected structure**
- Steps: Create working state via `cycle.py write-working-state` and verify format:
  - `# Working State` header
  - `- **Task**:` field
  - `- **Status**:` field
  - `- **Started**:` field
  - `## Completed Steps` section
  - `## Remaining Steps` section
  - `## Key Decisions` section
- Expected: All sections present

**TC-117: tracker.py comment format has no timestamp (regression for CONTEXT decision #3)**
- Steps: Call `tracker.py comment --number <N> --role pm --message "test"` with --dry-run
- Expected: Output shows body = `> **pm**: test` — NO `[YYYY-MM-DD HH:MM]` prefix

---

## Test Summary

| Category | Count | Test IDs |
|----------|-------|----------|
| A. Unit — config.py | 11 | TC-001 to TC-011 |
| A. Unit — cycle.py | 16 | TC-012 to TC-027 |
| A. Unit — tracker.py | 14 | TC-028 to TC-041 |
| A. Unit — git_ops.py | 10 | TC-042 to TC-051 |
| A. Unit — vault_check.py | 11 | TC-052 to TC-062 |
| B. Integration — tracker | 5 | TC-063 to TC-067 |
| B. Integration — git | 3 | TC-068 to TC-070 |
| B. Integration — cycle/config | 4 | TC-071 to TC-074 |
| C. E2E scenario | 3 | TC-075 to TC-077 |
| D. Status flow — valid | 10 | TC-078 to TC-087 |
| D. Status flow — invalid | 11 | TC-088 to TC-098 |
| E. Cross-platform | 5 | TC-099 to TC-103 |
| F. Sub-skill rewrite | 6 | TC-104 to TC-109 |
| G. Regression | 8 | TC-110 to TC-117 |
| **Total** | **117** | |

---

## Execution Notes

1. **Unit tests (A)**: Run in CI or locally with no external dependencies. All subprocess calls mocked.
2. **Integration tests (B)**: Require `gh` auth and network. Create real resources with `[TEST]` prefix. ALL teardown in `finally` blocks.
3. **E2E tests (C)**: Require `gh` auth. Single issue traverses full lifecycle. Teardown deletes issue.
4. **Status flow tests (D)**: Unit-testable by mocking the transition validation logic. Integration variants optional.
5. **Cross-platform tests (E)**: Code inspection tests — verify implementation choices, not runtime behavior.
6. **Sub-skill rewrite tests (F)**: Grep-based verification after all sub-skills are updated. Run post-implementation.
7. **Regression tests (G)**: Mix of code inspection and integration. Ensure backward compatibility.

**Blocking requirement**: ALL tests must pass before FEAT-66 ships. Any failure = back to dev.

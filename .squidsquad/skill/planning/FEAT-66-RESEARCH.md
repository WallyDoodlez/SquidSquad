# FEAT-66 Research — Deterministic Script Layer

## Summary

SquidSquad agents currently execute all mechanical operations (git commands, gh CLI calls, file I/O, counter increments, timestamp generation, label transitions) by interpreting prose instructions in markdown sub-skills. This is probabilistic — LLMs re-parse the same instructions every cycle and regularly produce errors: wrong label names, skipped steps, fabricated timestamps, incorrect counter arithmetic, non-atomic file writes.

This research catalogs every deterministic operation across all 70+ sub-skill files, groups them into five Python script modules, defines CLI interfaces, shows rewrite patterns for representative sub-skills, and proposes a phased migration strategy.

**Recommendation**: Feasible with caveats. Implement incrementally — one module at a time, starting with `tracker.py` (highest error rate) and `config.py` (simplest). Python stdlib-only, cross-platform. The existing `statusline.sh` remains bash (it runs outside Claude Code, in the terminal).

**Primary risks**: Python availability on target systems (mitigated by graceful fallback), gh CLI auth failures during script execution, and the need to update the sub-skill composition engine to reference scripts.

---

## 1. Codebase Impact — Full Operation Catalog

### Methodology

Read all files in `references/sub-skills/` (15 common, 6 roles, 5 souls, 11 pm-specific, 8 qa-specific, 9 dm-specific, 8 designer-specific = 62 files). Cataloged every `gh issue`, `git`, file I/O, counter, and timestamp operation. Soul files contain zero mechanical operations (pure personality/reasoning guidance).

### Operations by Module

#### A. `tracker.py` — GitHub Issues Operations (38 operations)

| # | Operation | Source Sub-skills | Frequency |
|---|-----------|-------------------|-----------|
| 1 | `gh issue list` with label filters | common/tracker-protocol, roles/dev-agent, roles/pm-agent, roles/qa-agent, roles/dm-agent, roles/designer, qa-specific/verification, dm-specific/bug-triage, dm-specific/delivery-packaging, pm-specific/pr-flow, pm-specific/github-issues, designer-specific/design-session | Every cycle, all roles |
| 2 | `gh issue view [N]` with JSON fields | common/tracker-protocol, roles/dev-agent, qa-specific/verification, dm-specific/bug-triage | Per-item |
| 3 | `gh issue create` (bug) | common/bug-filing, qa-specific/verification, dm-specific/bug-triage, roles/dev-agent | On discovery |
| 4 | `gh issue create` (feature) | common/tracker-protocol, common/improvement-scan | On scan |
| 5 | `gh issue edit` — label add/remove (status transitions) | common/tracker-protocol, roles/dev-agent, qa-specific/verification, dm-specific/bug-triage, pm-specific/pr-flow | Per status change |
| 6 | `gh issue edit` — design label transitions | common/tracker-protocol, designer-specific/design-session | Per design change |
| 7 | `gh issue comment` (timestamped Discussion entry) | common/tracker-protocol, all role-specific discussion-protocol files, qa-specific/verification, dm-specific/bug-triage, dm-specific/delivery-packaging, pm-specific/pr-flow, pm-specific/github-issues | Every status change |
| 8 | `gh issue close` | common/tracker-protocol, qa-specific/verification | On ship/verify |
| 9 | `gh issue list` — startup permission check | common/tracker-protocol | Once at boot |
| 10 | `gh pr list` | pm-specific/pr-flow, qa-specific/verification | Per cycle (if PR flow) |
| 11 | `gh pr view [N] --comments` | pm-specific/pr-flow, qa-specific/verification | Per PR |
| 12 | `gh pr create` | common/git-commit | On feature completion (PR flow) |

**Distinct gh CLI command patterns**: 12
**Total invocation sites across sub-skills**: 38+

#### B. `git_ops.py` — Git Operations (18 operations)

| # | Operation | Source Sub-skills | Frequency |
|---|-----------|-------------------|-----------|
| 1 | `git pull --rebase` | common/pull-latest | Every cycle, all roles |
| 2 | `git add -A` | common/git-commit, all role-specific git-commit files | Every non-quiet cycle |
| 3 | `git commit -m "[role]: [msg]"` | common/git-commit, all role-specific git-commit files | Every non-quiet cycle |
| 4 | `git push` | common/git-commit, all role-specific git-commit files | Every non-quiet cycle |
| 5 | `git checkout -b [branch]` | common/git-commit (PR flow) | On feature completion |
| 6 | `git push -u origin [branch]` | common/git-commit (PR flow) | On feature completion |
| 7 | `git checkout main` | common/git-commit (PR flow) | After PR creation |
| 8 | `git tag vX.Y.Z` | dm-specific/version-bumps, pm-specific/delivery-fallback | On version bump |
| 9 | `git push --tags` | dm-specific/version-bumps, pm-specific/delivery-fallback | On version bump |
| 10 | `git tag -l "vX.Y.Z"` (check existing) | dm-specific/version-bumps, pm-specific/delivery-fallback | On version bump |
| 11 | `git log -1 --format="%H" -- [file]` | pm-specific/feature-intake (artifact resume) | Per planning phase |
| 12 | `git log --oneline [hash]..HEAD -- [paths]` | pm-specific/feature-intake (artifact resume) | Per planning phase |

**Distinct git command patterns**: 12
**Total invocation sites**: 18+

#### C. `cycle.py` — Iteration Log, Working State, Current State (22 operations)

| # | Operation | Source Sub-skills | Frequency |
|---|-----------|-------------------|-----------|
| 1 | Write `current-state` (atomic: .tmp + mv) | All role entry files (dev, pm, qa, dm, designer) | Every step marker |
| 2 | Read `current-state` | common/resume-working-state (indirectly) | On boot |
| 3 | Write `working-state.md` (create/update) | common/working-state, roles/dev-agent, dm-specific/bug-triage, dm-specific/delivery-packaging, designer-specific/design-session | Per task pickup |
| 4 | Read `working-state.md` | common/resume-working-state | Every cycle start |
| 5 | Clear `working-state.md` | common/working-state | Per task completion |
| 6 | Create `iterations/iter-N.md` | common/iteration-log, all role-specific iteration-log files | Every non-quiet cycle |
| 7 | Find next iter number (scan iterations/) | common/iteration-log | Every non-quiet cycle |
| 8 | Delete old iter files (keep 20) | common/iteration-log, all role-specific iteration-log files | Every non-quiet cycle |
| 9 | Get timestamp `date +"%H:%M:%S"` | common/tracker-protocol | Every step marker |
| 10 | Get timestamp `date +"%Y-%m-%d %H:%M"` | common/tracker-protocol | Every Discussion entry |
| 11 | Write scan-history.md | common/improvement-scan | Per scan |
| 12 | Read scan-history.md | common/improvement-scan | Per scan |
| 13 | Set/clear planning phase flag in working-state.md | pm-specific/feature-intake | Per planning phase |
| 14 | Write design spec to specs/ directory | designer-specific/design-session | Per design completion |

**Distinct operation patterns**: 14
**Total invocation sites**: 22+

#### D. `config.py` — Config File Operations (12 operations)

| # | Operation | Source Sub-skills | Frequency |
|---|-----------|-------------------|-----------|
| 1 | Read `SquidSquad Version` | dm-specific/version-bumps, pm-specific/delivery-fallback | On version bump |
| 2 | Write `SquidSquad Version` (bump) | dm-specific/version-bumps, pm-specific/delivery-fallback | On version bump |
| 3 | Read `Ship Threshold` | dm-specific/version-bumps, pm-specific/delivery-fallback | After ship |
| 4 | Read `Shipped Since Last Bump` | dm-specific/version-bumps, pm-specific/delivery-fallback | After ship |
| 5 | Increment `Shipped Since Last Bump` | dm-specific/delivery-packaging, pm-specific/delivery-fallback, qa-specific/verification | Per ship |
| 6 | Reset `Shipped Since Last Bump` to 0 | dm-specific/version-bumps, pm-specific/delivery-fallback | On version bump |
| 7 | Read `Iteration Interval > Minutes` | common/interval-sync, all role entry files | Every cycle |
| 8 | Read `Context Pressure > Threshold` | common/context-pressure | Every cycle |
| 9 | Read `PR Flow > Enabled` | common/git-commit, pm-specific/pr-flow | Every cycle |
| 10 | Read `Improvement Scanning > Enabled` | common/improvement-scan | Every cycle |
| 11 | Read `Dev Agents` list | pm-specific/pr-flow, statusline.sh | Every cycle (PM) |
| 12 | Read/write `Open Artifacts in Editor` | pm-specific/feature-intake | On artifact creation |

**Distinct operation patterns**: 12
**Total invocation sites**: 12+

#### E. `vault_check.py` — Vault Health Operations (8 operations)

| # | Operation | Source Sub-skills | Frequency |
|---|-----------|-------------------|-----------|
| 1 | Parse YAML frontmatter | common/vault-protocol | Per vault-check |
| 2 | Validate required frontmatter fields | common/vault-protocol | Per vault-check |
| 3 | Check type-folder match | common/vault-protocol | Per vault-check |
| 4 | Parse wikilinks from body | common/vault-protocol | Per vault-check |
| 5 | Resolve wikilinks (file exists?) | common/vault-protocol | Per vault-check |
| 6 | Auto-maintain `links` frontmatter | common/vault-protocol | Per vault-write |
| 7 | Orphan detection (full sweep) | common/vault-protocol | On-demand |
| 8 | Staleness detection (30-day check) | common/vault-protocol | On-demand |

**Distinct operation patterns**: 8
**Total invocation sites**: 8

### Summary Counts

| Module | Distinct Patterns | Invocation Sites | Error-Prone? |
|--------|-------------------|------------------|--------------|
| `tracker.py` | 12 | 38+ | **HIGH** — wrong labels, missing --remove-label, wrong JSON fields |
| `git_ops.py` | 12 | 18+ | MEDIUM — wrong branch names, forgot to checkout main |
| `cycle.py` | 14 | 22+ | **HIGH** — non-atomic writes, wrong iter numbers, timestamp fabrication |
| `config.py` | 12 | 12+ | MEDIUM — wrong field parsing, arithmetic errors on counters |
| `vault_check.py` | 8 | 8 | LOW — but complex logic (wikilink resolution, frontmatter parsing) |

**Total distinct mechanical operation patterns**: 58
**Total invocation sites across all sub-skills**: ~98

---

## 2. Script Interface Design

### A. `scripts/tracker.py`

**Purpose**: All GitHub Issues operations. Wraps `gh` CLI with correct label management.

```
Usage: python scripts/tracker.py <command> [options]

Commands:
  check-auth                     Verify gh CLI access (exit 0 = ok, exit 1 = fail)
  list-issues                    List issues with label filters
  view-issue                     View a single issue with JSON fields
  create-bug                     Create a bug issue with correct labels
  create-feature                 Create a feature issue with correct labels
  transition                     Change issue status labels (atomic remove+add)
  comment                        Add a timestamped Discussion comment
  close-issue                    Close an issue
  list-prs                       List PRs matching pattern
  view-pr-comments               View PR comments
  create-pr                      Create a PR

Subcommand details:

  check-auth
    Exit 0 if gh is authenticated with repo scope.
    Exit 1 with error message on stderr.

  list-issues --labels <csv> [--state open|closed|all] [--limit N] [--fields <csv>]
    stdout: JSON array of matching issues
    Exit 0 on success, exit 2 on network error (agent retries next cycle)

  view-issue --number <N> [--fields <csv>]
    stdout: JSON object
    Exit 0 or exit 1 (not found)

  create-bug --title <str> --body <str> --severity <high|medium|low> --role <str> [--reported-by <str>]
    Adds labels: type:bug, severity:<level>, role:<role>, squidsquad, status:pending
    stdout: issue number
    Exit 0

  create-feature --title <str> --body <str> --priority <high|medium|low> --role <str> [--extra-labels <csv>]
    Adds labels: type:feature, priority:<level>, role:<role>, squidsquad, status:pending
    stdout: issue number
    Exit 0

  transition --number <N> --from <status> --to <status>
    Atomically removes status:<from> and adds status:<to>
    stdout: nothing
    Exit 0 on success, exit 1 if current label doesn't match --from

  comment --number <N> --role <str> --message <str>
    Generates timestamp automatically via system clock
    Formats: "> [YYYY-MM-DD HH:MM] **<role>**: <message>"
    stdout: nothing
    Exit 0

  close-issue --number <N>
    Exit 0

  list-prs --search <pattern> [--state open|closed|all] [--limit N]
    stdout: JSON array
    Exit 0

  create-pr --title <str> --body <str> --branch <str>
    stdout: PR URL
    Exit 0
```

**Agent invocation**: `python scripts/tracker.py transition --number 42 --from approved --to in-progress`

**Key design choice**: The `transition` command validates the current status label exists before changing it. This prevents the #1 recurring bug: agents removing a label that doesn't exist (silent no-op) then adding the new one, leaving the issue with two status labels.

### B. `scripts/git_ops.py`

**Purpose**: All git operations with error handling and conflict resolution.

```
Usage: python scripts/git_ops.py <command> [options]

Commands:
  pull                           git pull --rebase with conflict detection
  commit-and-push                Stage all, commit with role prefix, push
  create-feature-branch          Create branch, commit, push, create PR
  return-to-main                 Checkout main after PR creation
  version-tag                    Create and push a version tag
  artifact-changed               Check if code changed since artifact was created
  check-unpushed                 Check for unpushed commits

Subcommand details:

  pull
    Runs git pull --rebase.
    Exit 0 on success.
    Exit 1 on conflict (prints conflicting files to stdout for agent resolution).

  commit-and-push --role <str> --message <str>
    Runs: git add -A && git commit -m "<role>: <message>" && git push
    Exit 0 on success.
    Exit 1 if nothing to commit (not an error — agent skips).
    Exit 2 on push failure.

  create-feature-branch --role <str> --type <feat|bug> --number <N> --message <str>
    Creates branch squidsquad/<type>-<role>-<N>
    Commits and pushes.
    stdout: branch name
    Exit 0

  return-to-main
    git checkout main
    Exit 0

  version-tag --version <X.Y.Z>
    Checks if tag exists. Creates if not. Pushes tag.
    Exit 0 on success.
    Exit 1 if tag already exists (skip).

  artifact-changed --artifact-path <path> --watch-paths <csv>
    Checks git log for changes to watch-paths since artifact was committed.
    stdout: "changed" or "unchanged"
    Exit 0
```

### C. `scripts/cycle.py`

**Purpose**: Iteration lifecycle — timestamps, state files, iteration logs.

```
Usage: python scripts/cycle.py <command> [options]

Commands:
  timestamp                      Get current system timestamp
  write-state                    Atomic write to current-state
  read-working-state             Read and parse working-state.md
  write-working-state            Write working-state.md
  clear-working-state            Reset working-state.md to empty
  create-iter-log                Create iteration log with next number
  cleanup-iter-logs              Delete oldest iter logs beyond limit
  update-scan-history            Append to scan-history.md

Subcommand details:

  timestamp --format <step|discussion|date>
    step: HH:MM:SS
    discussion: YYYY-MM-DD HH:MM
    date: YYYY-MM-DD
    stdout: formatted timestamp from system clock
    Exit 0

  write-state --role <str> --phase <str> --description <str>
    Atomic write (tmp + rename) to .squidsquad/<role>/current-state
    Content: "<phase>|<description>"
    Exit 0

  read-working-state --role <str>
    Parses .squidsquad/<role>/working-state.md
    stdout: JSON with task, status, started, completed_steps, remaining_steps
    Exit 0 (returns {"task":"none","status":"none"} if empty)

  write-working-state --role <str> --task <str> --status <str> [--phase <str>] [--steps-json <str>]
    Writes structured working-state.md
    Exit 0

  clear-working-state --role <str>
    Resets to template with task=none, status=none
    Exit 0

  create-iter-log --role <str> --role-upper <str> --fields-json <str>
    Scans iterations/ for highest N, creates iter-(N+1).md
    --fields-json is a JSON object with field names and values
    stdout: created filename
    Exit 0

  cleanup-iter-logs --role <str> [--keep N]
    Deletes oldest iter-*.md files, keeps N (default 20)
    stdout: number of files deleted
    Exit 0

  update-scan-history --role <str> --files-json <str> --findings-json <str>
    Appends a scan entry to scan-history.md
    Exit 0
```

### D. `scripts/config.py`

**Purpose**: Read/write config.md fields with correct parsing.

```
Usage: python scripts/config.py <command> [options]

Commands:
  get                            Read a config value
  set                            Write a config value
  increment                      Increment a numeric config value
  reset                          Reset a numeric config value to 0
  bump-version                   Increment minor version

Subcommand details:

  get --key <str>
    Recognized keys: version, ship-threshold, shipped-count, interval,
                     context-threshold, pr-flow, improvement-scanning,
                     dev-agents, tracker
    stdout: the value
    Exit 0 on success, exit 1 if key not found

  set --key <str> --value <str>
    Updates the value in config.md in-place
    Exit 0

  increment --key <str>
    Reads current numeric value, adds 1, writes back
    stdout: new value
    Exit 0

  reset --key <str>
    Sets numeric value to 0
    Exit 0

  bump-version
    Reads current version (e.g., 0.10.0)
    Increments minor, resets patch (0.10.0 -> 0.11.0)
    Updates config.md AND SKILL.md frontmatter
    stdout: new version string
    Exit 0
```

### E. `scripts/vault_check.py`

**Purpose**: Vault health validation. Replaces inline grep/bash logic.

```
Usage: python scripts/vault_check.py <command> [options]

Commands:
  check-note                     Level 1 check on a single note + 2-hop neighborhood
  full-sweep                     Level 2 full vault sweep
  sync-links                     Auto-maintain links frontmatter from body wikilinks

Subcommand details:

  check-note --path <str>
    Parses frontmatter, validates fields, checks wikilinks, checks size.
    Traverses 2-hop wikilink neighborhood and checks those notes too.
    stdout: JSON array of warnings (empty = pass)
    Exit 0

  full-sweep
    Runs Level 1 on every .md in vault/.
    Plus orphan detection, staleness check, broken link census.
    stdout: JSON summary {note_count, orphan_count, stale_count, broken_link_count, warnings: [...]}
    Exit 0

  sync-links --path <str>
    Parses wikilinks from body, updates links frontmatter field.
    Exit 0
```

---

## 3. Sub-skill Rewrite Patterns

### A. Simple: `common/pull-latest.md` (BEFORE)

```markdown
### Step 1 — Pull Latest

Print: `[🦑 HH:MM:SS] Pulling latest...`

\`\`\`bash
git pull --rebase
\`\`\`

If there is a rebase conflict in a tracker file, resolve it by keeping
both versions — append the conflicting section below the existing one.
```

### A. Simple: `common/pull-latest.md` (AFTER)

```markdown
### Step 1 — Pull Latest

Print: `[🦑 <timestamp>] Pulling latest...` (get timestamp from `python scripts/cycle.py timestamp --format step`)

```bash
python scripts/git_ops.py pull
```

- **Exit 0**: continue normally.
- **Exit 1** (conflict): the script prints conflicting file paths. Resolve by keeping both versions — append the conflicting section below the existing one. Then `python scripts/git_ops.py commit-and-push --role [ROLE] --message "resolve rebase conflict"`.

> **LLM reasoning retained**: Conflict resolution strategy (keeping both versions) remains prose because it requires understanding file content.
```

### B. Complex: `dm-specific/delivery-packaging.md` (AFTER — key excerpts)

```markdown
### Step 2 — Scan for Pending Ship Items

Print: `[🦑 <timestamp>] Scanning for Pending Ship items...`

```bash
# Get pending-ship items for all dev agents
ITEMS=$(python scripts/tracker.py list-issues --labels "type:feature,status:pending-ship" --fields "number,title,labels,body")
```

Pick the highest-priority item. When picking up:

```bash
python scripts/cycle.py write-state --role dm --phase triaging --description "#[NUMBER] delivery..."
python scripts/cycle.py write-working-state --role dm --task "#[NUMBER]" --status in-progress
```

Read the feature and its Discussion entries (**LLM reasoning**: understand what was built, what delivery work is needed).

### Step 2b — Check for delivery:skip

Check the feature's Discussion entries for `delivery: skip`. (**LLM reasoning**: parse comment content for the tag.)

If found:

```bash
python scripts/tracker.py transition --number [NUMBER] --from pending-ship --to shipped
python scripts/tracker.py comment --number [NUMBER] --role dm --message "No delivery work needed (delivery: skip). Status → Shipped."
python scripts/tracker.py close-issue --number [NUMBER]
python scripts/config.py increment --key shipped-count
python scripts/cycle.py clear-working-state --role dm
```

### Step 2c — Create Delivery Package

For features NOT skipped:

1. **Update user-facing docs** (**LLM reasoning**: read feature, write appropriate README/SKILL.md updates — this is creative work).
2. **Write CHANGELOG entry** (**LLM reasoning**: summarize feature for users).
3. **Check for config/migration changes** (**LLM reasoning**: analyze whether new config is needed).

Then:

```bash
python scripts/tracker.py transition --number [NUMBER] --from pending-ship --to shipped
python scripts/tracker.py comment --number [NUMBER] --role dm --message "Delivery complete. Docs updated, CHANGELOG prepared. Status → Shipped."
python scripts/tracker.py close-issue --number [NUMBER]
python scripts/config.py increment --key shipped-count
python scripts/cycle.py clear-working-state --role dm
```

> **Pattern**: All label transitions, comments, counter increments, and state management are script calls. All content analysis, writing, and decision-making remain LLM prose.
```

### C. Hybrid: `common/improvement-scan.md` (AFTER — key excerpts)

```markdown
## Improvement Scanning (Quiet Cycle Productivity)

### Activation

Check improvement scanning config:

```bash
ENABLED=$(python scripts/config.py get --key improvement-scanning)
```

If `no`, skip entirely.

Maintain a quiet cycle counter in working state. Increment on quiet cycles, trigger scan after 3.
(**LLM reasoning**: deciding what constitutes a "quiet cycle" and when to trigger.)

### Scanning Step

```bash
python scripts/cycle.py write-state --role [ROLE] --phase scanning --description "Scanning [target]..."
```

1. **Detect project type** (**LLM reasoning**: read files, identify tech stack).
2. **Read SOUL.md lens** (**LLM reasoning**: internalize scanning priorities).
3. **Select files to scan** (**LLM reasoning**: prioritize by recency, coverage, staleness).
4. **Scan with domain lens** (**LLM reasoning**: analyze code for issues — this is the core creative work).
5. **Report findings to PM** — for each finding:

```bash
ISSUE_NUM=$(python scripts/tracker.py create-bug \
  --title "BUG: [title]" \
  --body "[description]" \
  --severity low \
  --role [target-role] \
  --extra-labels "improvement-scan")
```

Or for feature findings:

```bash
ISSUE_NUM=$(python scripts/tracker.py create-feature \
  --title "FEAT: [title]" \
  --body "[description]" \
  --priority low \
  --role [target-role] \
  --extra-labels "improvement-scan")
```

6. **Update scan history**:

```bash
python scripts/cycle.py update-scan-history \
  --role [ROLE] \
  --files-json '["file1.ts","file2.ts","file3.ts"]' \
  --findings-json '[{"number":123,"title":"..."}]'
```

> **Pattern**: File selection and code analysis are LLM reasoning. Issue creation and history tracking are script calls.
```

---

## 4. Cross-Platform Concerns

### Current Platform-Specific Operations

| Operation | Current Approach | Windows Issue | Python stdlib Solution |
|-----------|-----------------|---------------|----------------------|
| Timestamps | `date +"%H:%M:%S"` / `date +"%Y-%m-%d %H:%M"` | Windows `date` command has different syntax; Git Bash provides Unix `date` but not all shells have it | `datetime.now().strftime(fmt)` — identical on all platforms |
| Atomic file write | `echo "..." > file.tmp && mv -f file.tmp file` | `mv -f` works in Git Bash but not cmd/PowerShell natively; file locking on Windows can cause `mv` to fail if statusline.sh has the file open | `os.replace()` — atomic on both platforms (POSIX rename semantics on Unix, MoveFileEx on Windows) |
| Path separators | Hardcoded `/` in all sub-skills | Git Bash handles `/` fine, but Python `open()` on Windows needs care | `pathlib.Path` — handles separators automatically |
| File deletion (old iters) | Prose instruction "delete oldest ones" — LLM uses `rm` | `rm` works in Git Bash, not in cmd | `os.remove()` or `pathlib.Path.unlink()` |
| `stat` for mtime | `stat -c %Y` (GNU) vs `stat -f %m` (BSD) in statusline.sh | statusline.sh already handles both; sub-skills don't use stat directly | `os.path.getmtime()` — cross-platform |
| Directory creation | Implicit (LLM creates dirs as needed) | No issue, but inconsistent | `os.makedirs(exist_ok=True)` |
| `grep -rl` (vault search) | Bash grep in vault-protocol | Works in Git Bash, not cmd | `pathlib.Path.rglob()` + file content search |
| `echo "..." > file` | Used for current-state, working-state | Works in Git Bash; encoding issues in PowerShell | `pathlib.Path.write_text(encoding='utf-8')` |
| `code [path]` (editor open) | pm-specific/feature-intake | Cross-platform if VS Code is on PATH | `subprocess.run(["code", path])` — same |

### Boot Scripts

The repo already maintains dual boot scripts (`.sh` + `.ps1`) for each role. These are NOT candidates for Python conversion — they launch `claude` CLI which is platform-specific. However, the `inject-permissions.sh` / `.ps1` scripts could eventually be unified into a single Python script.

### Key Insight

The biggest cross-platform win is **timestamp generation**. Currently, every sub-skill says `date +"%H:%M:%S"` and agents must run this bash command. On Windows without Git Bash in PATH, this fails silently and agents fabricate timestamps. `cycle.py timestamp` eliminates this entirely.

---

## 5. Migration Strategy

### Recommended Approach: Incremental (one module at a time)

Atomic migration (all scripts at once) is **not recommended** because:
- It would require rewriting all 62 sub-skill files simultaneously
- Any bug in the scripts would break all agents at once
- Testing surface is enormous

### Phase Plan

**Phase 1: Foundation (non-breaking)**
- Create `scripts/` directory at repo root
- Add `config.py` and `cycle.py` (lowest risk, highest value)
- These scripts can coexist with current prose — agents use scripts when available, fall back to inline commands when not
- Sub-skills updated to reference scripts with fallback instructions

**Phase 2: Tracker**
- Add `tracker.py`
- This is the highest-error-rate module
- Rewrite `common/tracker-protocol.md` to use script calls
- All role-specific sub-skills that do `gh issue` calls get updated
- This is the largest rewrite but also the highest value

**Phase 3: Git Operations**
- Add `git_ops.py`
- Rewrite `common/pull-latest.md`, `common/git-commit.md`, all role-specific git-commit files
- Version bump sequences (dm-specific/version-bumps, pm-specific/delivery-fallback) get script calls

**Phase 4: Vault**
- Add `vault_check.py`
- Rewrite `common/vault-protocol.md` vault-check and vault-search sections
- This is the lowest priority (vault operations are infrequent)

### Backward Compatibility

Each phase maintains backward compatibility:
- Scripts check for `gh` and `git` availability and return clear error codes
- Sub-skills include "if script unavailable" fallback text during transition
- The composition engine (`manifest.md`) doesn't need changes — scripts are called from within sub-skill prose, not as separate includes
- `statusline.sh` is NOT affected — it runs in bash outside Claude Code and reads files that scripts write to the same locations

### Upgrade Path

- **New installs**: Get scripts automatically (copied during setup like other reference files)
- **Existing installs**: `/squidsquad-upgrade` copies `scripts/` to repo root, regenerates templates from updated sub-skills
- **Graceful degradation**: If scripts are missing (old install, not upgraded), sub-skills still contain the fallback inline commands until the human runs upgrade

---

## 6. Edge Cases and Risks

### Python Availability

**Risk**: Python 3 is not installed on the target system.

**Mitigation**:
- Claude Code runs on Node.js and requires git + gh CLI. Python 3 is available on >95% of developer machines (macOS ships with it, Windows devs typically have it, Linux always has it).
- At setup time, check for Python 3: `python3 --version || python --version`. If missing, print a warning and skip script installation. Sub-skills remain in prose-only mode.
- Scripts use `#!/usr/bin/env python3` shebang. On Windows, Claude Code runs in bash (Git Bash), so shebangs work.
- **Fallback**: If Python is unavailable at runtime, agents see script call fail and fall back to inline commands. The sub-skills should document both paths during the transition period.
- **Alternative considered**: Node.js scripts (guaranteed available since Claude Code is Node). Rejected because Python stdlib is richer for file manipulation, and Python is more readable for this use case.

### `gh` CLI Authentication Failures

**Risk**: `gh auth` token expires or lacks required scopes mid-session.

**Current behavior**: Agents get cryptic error output from `gh` and may misinterpret it.

**Script behavior**:
- `tracker.py check-auth` runs at boot (already specified in tracker-protocol). Returns exit code 1 with clear error message on stderr.
- All `tracker.py` commands that call `gh` catch `subprocess.CalledProcessError`, parse the stderr, and return:
  - Exit 2 for "network unreachable" (transient — agent retries next cycle)
  - Exit 3 for "auth failed" (permanent — agent prints error and stops)
  - Exit 4 for "rate limited" (transient — agent waits)
- This replaces agents trying to parse `gh` error output themselves.

### Git Conflicts

**Risk**: `git pull --rebase` hits a conflict. Currently agents are told to resolve conflicts in tracker files by keeping both versions.

**Script behavior**:
- `git_ops.py pull` detects conflict state (`git status` shows `UU` files).
- Returns exit 1 with list of conflicting files on stdout.
- Agent (LLM) resolves conflicts using reasoning (keeping both versions for tracker files, making judgment calls for code conflicts).
- Agent then calls `git_ops.py commit-and-push` to finalize.
- **Key**: Conflict resolution is inherently a reasoning task. The script only detects and reports — the LLM decides.

### Independent Testing

**Yes, all scripts can be tested independently**:
- Each script is a standalone Python file with `if __name__ == "__main__"` entry point
- Unit tests can mock `subprocess.run` (for `gh`, `git` calls) and test logic
- Integration tests can run against a test repo
- Test file: `scripts/test_scripts.py` using `unittest` (stdlib only)
- CI-compatible: `python -m pytest scripts/` or `python scripts/test_scripts.py`

### Interaction with `statusline.sh`

**`references/statusline.sh`** (400 lines of bash) runs as a Claude Code status line hook, outside the agent's conversation. It:
- Reads `.squidsquad/<role>/current-state` (written by agents)
- Reads `.squidsquad/config.md` (ship counter, version, interval)
- Reads `.squidsquad/.local-config` (cross-clone paths)
- Calls `gh issue list` for backlog counts (cached to `.squidsquad/.backlog-cache`)
- Calls `git rev-list` for ahead/behind counts
- Uses `stat` for mtime checks

**Impact of script layer**: None. The statusline reads the same files that scripts write. As long as scripts write to the same paths in the same format, statusline.sh is unaffected.

**Future opportunity**: statusline.sh could eventually be rewritten as `statusline.py` to eliminate the GNU stat vs BSD stat branching and the complex bash string manipulation. But this is a separate feature — not part of FEAT-66.

### Race Conditions

**Risk**: Statusline.sh reads `current-state` while `cycle.py write-state` is writing it.

**Current mitigation**: Atomic writes via `.tmp` + `mv`. This is already specified in all role entry files.

**Script mitigation**: `os.replace()` is atomic on both POSIX and Windows (NTFS). This is strictly better than the current `echo + mv` pattern because `os.replace()` is a single syscall.

### Script Size and Complexity

**Risk**: Scripts become complex enough to have their own bugs.

**Mitigation**:
- stdlib only — no dependencies to manage
- Each script is under 300 lines (estimated)
- Simple I/O: read args, call subprocess or manipulate files, return exit code
- Comprehensive `--help` for each command
- Scripts never make decisions — they execute deterministic operations and report results

---

## 7. Prior Art

### Existing Scripts in Repo

- **`references/statusline.sh`** (400 lines): Bash status bar script. Already handles cross-platform `stat` differences. Reads config.md, calls `gh`, `git`. This is the closest prior art to what we're building.
- **`.squidsquad/statusline.sh`**: Live copy of the above.
- **`.squidsquad/inject-permissions.sh`** + **`.squidsquad/inject-permissions.ps1`**: Dual-platform scripts for injecting permissions into Claude Code settings.json.
- **`.squidsquad/start-*.sh`** + **`.squidsquad/start-*.ps1`**: Boot scripts for each role. Already maintain sh/ps1 pairs.
- **`.squidsquad/test.ps1`**: PowerShell test runner.

### No Existing Python

Zero `.py` files exist anywhere in the repository. Python is not listed as a dependency in SKILL.md or README.md. This means:
- Python is a **new runtime dependency** (albeit one nearly universally available)
- We should document it clearly in SKILL.md prerequisites
- Setup/upgrade should check for Python availability

### SKILL.md and README.md Mentions

Neither file mentions Python. The SKILL.md description emphasizes "no meetings, no message queues, just markdown" — the script layer maintains this philosophy since scripts are invoked from within markdown sub-skills, not as a separate orchestration layer.

### statusline.sh as a Template

The existing `statusline.sh` demonstrates the pattern we're generalizing: a deterministic script that reads config, calls CLI tools, and produces output — while the agent (or status bar) decides what to do with that output. The script layer extends this pattern from one 400-line bash script to five focused Python scripts.

---

## 8. Open Questions

### Q1: Where should scripts live?

**Options**:
- A) `scripts/` at repo root (visible, easy to find)
- B) `references/scripts/` (grouped with other reference material)
- C) `.squidsquad/scripts/` (grouped with runtime state)

**Recommendation**: B (`references/scripts/`). Follows the existing pattern where `references/` contains source material that gets copied to `.squidsquad/` during setup. Scripts in `references/scripts/` would be copied to the project's `.squidsquad/scripts/` on install/upgrade, matching how `statusline.sh` works today.

### Q2: How do agents call Python?

**Options**:
- A) `python3 scripts/tracker.py ...` (explicit interpreter)
- B) `python scripts/tracker.py ...` (may hit Python 2 on old systems)
- C) `./scripts/tracker.py ...` (requires shebang + execute permissions)

**Recommendation**: A, with a setup-time check that aliases `python3` to the correct path. On Windows Git Bash, `python3` typically works. The scripts should have shebangs for option C as a fallback.

### Q3: Should scripts output JSON or plain text?

**Options**:
- A) JSON everywhere (machine-parseable, LLMs parse JSON well)
- B) Plain text (simpler, human-readable in scrollback)
- C) Hybrid — JSON for data (list-issues, view-issue), plain text for confirmations

**Recommendation**: C. `list-issues` and `view-issue` return JSON (agents already parse gh JSON output). `transition`, `comment`, `commit-and-push` return nothing on success (exit 0). Errors go to stderr as plain text.

### Q4: Do we update the composition engine?

The composition engine (`manifest.md`) resolves `{{include: path}}` directives. Scripts are called inline from sub-skill prose, so the engine doesn't need changes. But we could add a `{{script: path}}` directive that verifies the script exists during composition.

**Recommendation**: Not in Phase 1. Keep it simple — scripts are referenced as bash commands in prose. Explore `{{script:}}` verification in a future iteration.

---

## 9. Recommendation

**Recommendation: Feasible with caveats. Proceed incrementally.**

The deterministic script layer addresses a real, recurring class of bugs (wrong labels, fabricated timestamps, non-atomic writes, counter arithmetic errors). The ~98 mechanical operations across 62 sub-skill files map cleanly to 5 Python modules with 58 distinct command patterns.

**Caveats**:
1. Python is a new dependency — must be documented and checked at setup time
2. Migration must be incremental (one module per feature) to avoid a flag day
3. Sub-skills retain prose fallbacks during transition
4. `statusline.sh` is untouched — it runs outside Claude Code
5. Souls and prohibitions are untouched — they contain zero mechanical operations
6. The composition engine needs no changes

**Suggested implementation order**: config.py (simplest, fewest touchpoints) -> cycle.py (highest frequency, timestamp fix) -> tracker.py (highest value, most complex) -> git_ops.py -> vault_check.py

**Estimated scope**: 5 Python scripts (~200-300 lines each), 25-30 sub-skill files updated, 1 new SKILL.md prerequisite line, setup/upgrade flow updated to copy scripts.

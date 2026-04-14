# FEAT-SKILL-922 Research -- SQLite-based Improvement Scan Index

## Summary

The improvement scan system currently uses flat markdown files (`scan-history.md`) per role to track what was scanned, when, and what was found. File selection during scans relies on agents manually checking these markdown histories and making ad hoc decisions about which files to scan next. This works but produces blind spots: agents re-scan clean files, miss coverage gaps, cannot learn from finding density patterns, and have no way to correlate scan targets with git churn (where bugs actually live).

A SQLite-based scan index would centralize scan metadata across all roles, enable deterministic file selection queries, and create a feedback loop where past finding acceptance rates inform future scan targeting. The primary risk is multi-agent concurrent write access to a single SQLite file, which is solvable with WAL mode and short transactions. The recommendation is **feasible with caveats** -- the core schema and query patterns are straightforward, but the migration path and concurrency model need careful design.

## Impact Analysis

### Files Touched

**New files:**
- `references/scripts/scan_index.py` -- SQLite DB management, query API, migration logic
- `.squidsquad/scan-index.db` -- the SQLite database (shared across all roles)
- `tests/test_scan_index.py` -- unit tests

**Modified files:**
- `references/sub-skills/common/improvement-scan.md` -- update file selection step to call `scan_index.py` instead of manually parsing `scan-history.md`
- `references/sub-skills/common/improvement-scan-slim.md` -- slim variant update
- Each role's CLAUDE.md (via compose.py recomposition) -- picks up updated sub-skill
- `.gitignore` -- add `scan-index.db-journal`, `scan-index.db-wal`, `scan-index.db-shm`

**Files NOT touched (but read by the system):**
- `.squidsquad/*/scan-history.md` -- kept as human-readable audit trail; DB is the authoritative source for queries
- `.squidsquad/*/SOUL.md` -- scan lens sections remain as-is (read by agents, not by scripts)
- `references/scripts/tracker.py` -- no changes; findings still filed via tracker.py as GitHub Issues

### Behavior Changes

1. **File selection becomes deterministic**: Instead of agents manually checking scan-history.md and picking files heuristically, `scan_index.py suggest-targets <role> --count 5` returns a ranked list based on coverage gaps, churn, and finding density.
2. **Scan recording becomes structured**: After a scan, agents call `scan_index.py record-scan --role <role> --files <list> --findings <json>` instead of appending markdown.
3. **Finding feedback loop**: When a human approves/rejects an improvement scan finding, `scan_index.py record-decision --issue <number> --accepted <bool>` updates the findings table. This feeds back into future targeting (files with high acceptance rates get scanned more; files with high rejection rates get deprioritized).
4. **Cross-role visibility**: All roles write to the same DB, so PM can query "which files have never been scanned by any role?" -- currently impossible without parsing all 4 scan-history.md files.

### Dependencies

- Python `sqlite3` module (stdlib -- no new dependency)
- Git CLI (`git log --numstat` for churn data -- already available)
- Existing `tracker.py` for filing findings (unchanged)

## Side Effects

### Risk 1: Multi-agent concurrent SQLite writes
- **Severity**: M
- **Description**: Multiple agents (pm, skill, qa, dm) may trigger scans near-simultaneously and attempt concurrent DB writes. SQLite supports concurrent reads but only one writer at a time. Without WAL mode, writers block each other with `SQLITE_BUSY`.
- **Mitigation**: Use WAL (Write-Ahead Logging) mode, which allows concurrent reads during writes. Set a busy timeout of 5 seconds (`PRAGMA busy_timeout = 5000`). Keep write transactions short (single INSERT per scan). If a write still fails after timeout, the agent logs a warning and falls back to markdown-only recording -- the scan is not lost.

### Risk 2: DB file in git creates merge conflicts
- **Severity**: H
- **Description**: SQLite DB files are binary. If committed to git, every agent push creates a merge conflict on the binary file. This would break the pull-rebase workflow.
- **Mitigation**: Add `scan-index.db` to `.gitignore`. The DB is local-only per clone. Each clone builds its own index. On first run (empty DB), import from `scan-history.md` files (which ARE in git). This means each agent clone has its own view, but since agents run in separate clones already and scan-history.md is the shared record, this is acceptable. Cross-clone queries are a future enhancement.

### Risk 3: Scan-history.md and DB drift out of sync
- **Severity**: L
- **Description**: If we write to DB but not markdown, the human-readable audit trail is lost. If we write to both, there's a dual-write consistency risk.
- **Mitigation**: Write to BOTH. The markdown file remains the append-only audit trail (human-readable, git-tracked). The DB is the query engine (local, fast, structured). If they drift, the DB can always be rebuilt from markdown. The DB is a cache/index, not the source of truth.

### Risk 4: Windows file locking
- **Severity**: M
- **Description**: On Windows (this project's platform), SQLite WAL mode can have issues with file locking if multiple processes access the DB. The `.squidsquad/.local-config` cross-clone architecture means agents run in separate directories, so each has its own DB -- but agents within the same clone (if any) could conflict.
- **Mitigation**: Each clone gets its own DB. The boot architecture (one agent per clone) means concurrent access within a single DB is rare. WAL mode + busy_timeout handles the edge case. The `.db-wal` and `.db-shm` files must be in `.gitignore`.

## Edge Cases

### Empty DB (first run)
- On first invocation of `scan_index.py`, check if DB exists. If not, create tables and run migration from `scan-history.md` files. The migration parser reads the markdown format (already well-structured with `## Scan -- YYYY-MM-DD HH:MM` headers, `Files scanned:`, `Findings:`, `Items rejected:`).
- If scan-history.md is also empty, the DB starts empty. `suggest-targets` falls back to "scan all source files sorted by git modification date" -- same as current behavior.

### Agent with no scan history
- New roles (e.g., a freshly added `designer`) have no scan-history.md entries. The DB returns zero rows for that role. `suggest-targets` returns files with zero coverage from ANY role, prioritized by churn -- this is actually better than the current behavior where a new agent has no guidance at all.

### Files deleted since last scan
- `suggest-targets` must verify file existence before returning results. Filter out files that no longer exist on disk. Optionally mark them as `deleted` in the DB (for historical queries) but never suggest them for scanning.

### Role change (new scan lens)
- When a role's SOUL.md scan lens changes (e.g., new scan criteria added), existing scan records remain valid -- they just reflect what the old lens found. No DB migration needed. The new lens naturally targets different patterns on the next scan.
- Edge case: if the lens changes to cover a new file type (e.g., `.yml` files), `suggest-targets` should respect the `file_patterns` from the current SOUL.md, not historical patterns. This means file type filtering is applied at query time, not stored in the DB.

### Scan-history.md parse failures
- The markdown format varies slightly between roles (PM includes "Items rejected by human" consistently; DM sometimes says "none yet" vs "none"). The parser must handle: `(none)`, `(none yet)`, `none`, empty lists, and multi-line findings with `#NNN` issue references.
- Mitigation: Build a robust regex parser with fallback to "skip unparseable entry, log warning." The DB is supplementary; a missed historical entry is not critical.

### Git churn data unavailable
- If git is not available or the repo is shallow-cloned, churn queries fail. `suggest-targets` should degrade gracefully: use scan coverage and finding density only, skip the churn factor.

## Schema Design

### Tables

```sql
-- Core scan record: who scanned what, when
CREATE TABLE scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,              -- 'pm', 'skill', 'qa', 'dm'
    scanned_at TEXT NOT NULL,        -- ISO 8601 timestamp
    file_path TEXT NOT NULL,         -- relative path from repo root
    scan_duration_ms INTEGER,        -- optional: how long the scan took
    UNIQUE(role, scanned_at, file_path)
);

-- Findings from scans, linked to GitHub Issues
CREATE TABLE findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL REFERENCES scans(id),
    file_path TEXT NOT NULL,
    finding_type TEXT NOT NULL,      -- 'issue' or 'task'
    severity TEXT,                   -- 'high', 'medium', 'low'
    description TEXT NOT NULL,
    github_issue_number INTEGER,     -- NULL until filed
    human_decision TEXT,             -- 'accepted', 'rejected', NULL (pending)
    decided_at TEXT,                 -- when human decided
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

-- Materialized view: per-file coverage stats (rebuilt periodically)
CREATE TABLE file_coverage (
    file_path TEXT PRIMARY KEY,
    last_scanned_at TEXT,            -- most recent scan across all roles
    total_scan_count INTEGER DEFAULT 0,
    finding_count INTEGER DEFAULT 0,
    accepted_finding_count INTEGER DEFAULT 0,
    rejected_finding_count INTEGER DEFAULT 0,
    last_scanned_by TEXT,            -- role that last scanned it
    finding_density REAL DEFAULT 0.0 -- findings per scan (signal strength)
);

-- Git churn cache (refreshed periodically, not on every query)
CREATE TABLE git_churn (
    file_path TEXT PRIMARY KEY,
    commit_count_30d INTEGER DEFAULT 0,  -- commits touching this file in last 30 days
    commit_count_90d INTEGER DEFAULT 0,
    last_refreshed TEXT NOT NULL          -- when churn data was last updated
);

-- Role-specific rejection tracking (never refile rejected items)
CREATE TABLE rejections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    file_path TEXT NOT NULL,
    finding_description TEXT NOT NULL,
    github_issue_number INTEGER,
    rejected_at TEXT NOT NULL
);
```

### Indexes

```sql
CREATE INDEX idx_scans_role ON scans(role);
CREATE INDEX idx_scans_file ON scans(file_path);
CREATE INDEX idx_scans_at ON scans(scanned_at);
CREATE INDEX idx_findings_issue ON findings(github_issue_number);
CREATE INDEX idx_findings_decision ON findings(human_decision);
CREATE INDEX idx_churn_commits ON git_churn(commit_count_30d DESC);
```

## Query Patterns

### 1. Coverage gaps (not scanned in N days)

```sql
-- Files never scanned, or not scanned in the last 7 days
SELECT fc.file_path, fc.last_scanned_at, fc.total_scan_count
FROM file_coverage fc
WHERE fc.last_scanned_at IS NULL
   OR julianday('now') - julianday(fc.last_scanned_at) > 7
ORDER BY fc.last_scanned_at ASC NULLS FIRST
LIMIT 10;
```

For files that have never been scanned (not in `file_coverage` at all), we need a file-system walk to discover source files, then LEFT JOIN against `file_coverage`:

```python
# Python pseudo-code
all_source_files = walk_source_files(exclude=['.squidsquad/', 'node_modules/', ...])
db_files = {row['file_path'] for row in query("SELECT file_path FROM file_coverage")}
never_scanned = [f for f in all_source_files if f not in db_files]
```

### 2. Hot spots (high churn + low scan coverage)

```sql
-- Files with high git activity but low/no scan coverage
SELECT gc.file_path,
       gc.commit_count_30d,
       COALESCE(fc.total_scan_count, 0) AS scan_count,
       COALESCE(fc.finding_density, 0) AS density
FROM git_churn gc
LEFT JOIN file_coverage fc ON gc.file_path = fc.file_path
WHERE gc.commit_count_30d > 3
ORDER BY gc.commit_count_30d DESC, scan_count ASC
LIMIT 10;
```

### 3. Role-specific targeting

```sql
-- Files this role hasn't scanned, but other roles found issues in
SELECT DISTINCT f.file_path, COUNT(*) AS cross_role_findings
FROM findings f
JOIN scans s ON f.scan_id = s.id
WHERE s.role != :current_role
  AND f.human_decision = 'accepted'
  AND f.file_path NOT IN (
      SELECT s2.file_path FROM scans s2 WHERE s2.role = :current_role
  )
GROUP BY f.file_path
ORDER BY cross_role_findings DESC
LIMIT 5;
```

File type filtering (respecting the role's SOUL.md scan lens) is applied in Python after the query, since file patterns are defined in prose, not SQL:

```python
# Read role's SOUL.md, extract file patterns
# Filter query results to matching extensions
```

### 4. Signal/noise learning (acceptance rate)

```sql
-- Per-file acceptance rate: which files produce findings humans care about?
SELECT fc.file_path,
       fc.accepted_finding_count,
       fc.rejected_finding_count,
       CASE WHEN fc.finding_count > 0
            THEN CAST(fc.accepted_finding_count AS REAL) / fc.finding_count
            ELSE 0 END AS acceptance_rate,
       fc.finding_density
FROM file_coverage fc
WHERE fc.finding_count > 0
ORDER BY acceptance_rate DESC, fc.finding_density DESC;
```

Files with high acceptance rates should be scanned more frequently. Files with high rejection rates should be deprioritized (humans don't find those findings valuable).

### Composite Targeting Score

The `suggest-targets` command combines all four signals into a single score:

```python
score = (
    coverage_gap_weight * days_since_last_scan / max_days +
    churn_weight * commit_count_30d / max_churn +
    cross_role_weight * cross_role_findings / max_cross +
    acceptance_weight * acceptance_rate
)
# Subtract penalty for recently scanned or high-rejection files
score -= recency_penalty * (1.0 - days_since_last_scan / max_days)
score -= rejection_penalty * rejection_rate
```

Default weights can be tuned over time. Initial values: coverage_gap=0.3, churn=0.3, cross_role=0.2, acceptance=0.2.

## Integration Risks

### Interaction with existing scan step
- The improvement-scan sub-skill currently has a "Select files to scan" step that is entirely prose-driven. Replacing this with `scan_index.py suggest-targets` is a clean swap -- the sub-skill text changes from "Check scan-history.md to avoid re-scanning" to "Run `python references/scripts/scan_index.py suggest-targets <role>`."
- The "Update scan history" step becomes a dual-write: append to scan-history.md AND call `scan_index.py record-scan`.
- Risk: If `scan_index.py` crashes or the DB is corrupted, the agent must fall back to the current markdown-based approach. The sub-skill should include a fallback clause.

### Interaction with vault
- No direct interaction. The vault stores knowledge notes; the scan index stores operational metadata. They serve different purposes and live in different subsystems.
- Indirect connection: vault-search could theoretically query the scan index to find "what files have patterns related to this vault note?" -- but this is a future enhancement, not part of this task.

### Interaction with 3-quiet-cycle trigger
- The quiet cycle counter remains in working-state.md (per role). The scan index does not change when scans are triggered -- only what files are selected. The activation logic is unchanged.

### Interaction with scan-history.md
- The markdown files continue to be written (dual-write). They remain the git-tracked, human-readable audit trail. The DB is a local query index.
- If the DB is deleted or corrupted, it can be rebuilt from scan-history.md files via `scan_index.py rebuild`.

### Interaction with compose.py
- The improvement-scan sub-skill change propagates to all roles via `compose.py deploy-all`. This is the normal update path -- no special handling needed.

### Interaction with branch workflow
- The DB file is in `.gitignore` (local-only), so it does not participate in branch workflows. Changes to `scan_index.py` and the sub-skill markdown DO go through branches.

## Upgrade & Migration

### New config values
- None required. The scan index is auto-initialized on first use. No new config.md fields.

### New files
- `references/scripts/scan_index.py` -- the script
- `.squidsquad/scan-index.db` -- auto-created, gitignored
- `tests/test_scan_index.py` -- unit tests

### Template changes
- `references/sub-skills/common/improvement-scan.md` -- updated file selection and recording steps
- `references/sub-skills/common/improvement-scan-slim.md` -- slim variant updated

### Upgrade steps
- `compose.py deploy-all` recomposes all agent CLAUDE.md files with the updated sub-skill.
- First scan cycle after upgrade: `scan_index.py` detects missing DB, runs `rebuild` from existing `scan-history.md` files. This is automatic -- no manual step.

### Graceful degradation
- If `scan_index.py` is not available (user hasn't pulled the update), the old sub-skill text still works -- agents fall back to manual scan-history.md parsing. No breakage.
- If the DB is missing or corrupt, `scan_index.py suggest-targets` should return exit code 0 with an empty list and log a warning. The sub-skill fallback clause handles this.

### Mid-scan upgrade
- If an agent is mid-scan when the upgrade happens (unlikely -- scans are fast), the old sub-skill text is still in their CLAUDE.md. They complete the scan using the old method. On their next self-restart (template change detection), they pick up the new sub-skill. The next scan uses the new method and auto-migrates. No data loss.

## Git Churn Integration

Git churn data can be queried directly from git log:

```bash
# Get file change counts for the last 30 days
git log --since="30 days ago" --numstat --format="" | \
  awk '{print $3}' | sort | uniq -c | sort -rn
```

This is called by `scan_index.py refresh-churn` and cached in the `git_churn` table. Refresh frequency: once per day (check `last_refreshed` timestamp). The refresh is triggered lazily -- when `suggest-targets` is called and churn data is stale (>24h old), refresh first.

For repos with shallow clones or limited git history, the churn query returns partial data. The scoring function handles this gracefully by treating missing churn data as zero (neutral -- neither hot nor cold).

## Capability Gaps

- **sqlite3**: Available (Python stdlib) -- no capability gap
- **git log --numstat**: Available (git CLI required, already a dependency) -- no capability gap
- **scan_index.py as a new script**: Must follow existing script conventions (see `references/scripts/` patterns: argparse CLI, `_run()` helper for subprocess, encoding=utf-8, list-form subprocess calls)

## Open Questions

- **Q1**: Should the DB be per-clone (local-only, gitignored) or shared (committed to git)?
  - **Why**: Per-clone means each agent builds its own index from scan-history.md. Shared means richer cross-agent queries but binary merge conflicts.
  - **Recommendation**: Per-clone (gitignored). The scan-history.md files are the shared truth. The DB is a local acceleration layer. Cross-agent queries work because all scan-history.md files are in the same repo.

- **Q2**: Should `suggest-targets` be a standalone CLI command or integrated into the existing cycle.py script?
  - **Why**: Standalone keeps scan_index.py focused. Integrated reduces the number of scripts agents need to know about.
  - **Recommendation**: Standalone `scan_index.py`. It has distinct concerns (DB management, migration, churn refresh) that don't belong in cycle.py. Follow the existing pattern of one-script-per-subsystem (tracker.py, vault_check.py, etc.).

- **Q3**: How should human decisions (accept/reject findings) flow back into the DB?
  - **Why**: The DB needs to know which findings were accepted vs. rejected to compute acceptance rates. Currently, rejections are tracked as prose in scan-history.md ("Items rejected by human: ...").
  - **Recommendation**: Add a `scan_index.py record-decision --issue <N> --accepted <bool>` command. PM calls this when the human approves or rejects an improvement-scan finding. The sub-skill instructions for PM should include this step after human decisions.

- **Q4**: Should the composite targeting score weights be configurable (in config.md) or hardcoded?
  - **Why**: Tuning weights lets the human optimize scan behavior. Hardcoded is simpler.
  - **Recommendation**: Hardcode initially with sensible defaults. Add config.md fields later if tuning is needed. Premature configurability adds complexity.

- **Q5**: What happens to the `file_coverage` table when files are renamed?
  - **Why**: Git renames (mv) break the file_path key. Historical coverage for the old path becomes orphaned.
  - **Recommendation**: On `refresh-churn`, detect renames via `git log --follow --diff-filter=R` and update `file_coverage.file_path` for renamed files. This is a nice-to-have, not blocking -- renamed files simply appear as "never scanned" and get prioritized naturally.

## Recommendation

**Feasible with caveats.** The schema, queries, and integration path are well-defined. The main caveats are:

1. **Concurrency**: WAL mode + busy_timeout + short transactions should handle multi-agent access, but this needs testing on Windows specifically.
2. **Migration**: The scan-history.md parser needs to handle format variations across roles and time periods. Budget time for this.
3. **Dual-write**: Keeping scan-history.md and DB in sync adds complexity. Accept that the markdown is the source of truth and the DB is a rebuildable index.
4. **Scope control**: The git churn integration and composite scoring are valuable but add complexity. Consider shipping in phases: Phase 1 (DB + basic queries + migration), Phase 2 (churn + composite scoring + decision feedback).

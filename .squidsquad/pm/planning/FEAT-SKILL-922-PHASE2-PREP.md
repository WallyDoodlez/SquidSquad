# FEAT-SKILL-922 Phase 2 Prep -- Discussion Guide

## Optimal Question Order

Dependencies and foundational decisions first, implementation details second, future-proofing last.

1. **Q1** (Storage architecture) -- Q2 and Q3 depend on whether the DB is local or shared
2. **Q2** (CLI integration) -- Affects how Q3's decision feedback is invoked
3. **Q3** (Decision feedback flow) -- Depends on Q1 (where decisions are stored) and Q2 (how agents invoke commands)
4. **Q5** (File renames) -- Independent but low-stakes, quick to resolve
5. **Q4** (Weight configurability) -- Least dependent, most subjective, good to end on

---

## Q1: Should the DB be per-clone (local-only, gitignored) or shared (committed to git)?

**Category**: Architecture / Storage

**Why it matters**: This is the foundational decision. If the DB is shared, cross-agent queries are richer but binary merge conflicts will break the pull-rebase workflow. If per-clone, each agent has an isolated view and must rebuild from markdown.

### Option A: Per-clone, gitignored (RECOMMENDED)

Each clone builds its own SQLite DB from scan-history.md on first run. DB files are in .gitignore.

| Pros | Cons |
|------|------|
| Zero merge conflict risk on binary files | Each clone has an isolated view -- no live cross-agent queries |
| Simple git workflow -- no binary blobs in history | Rebuild cost on first run (one-time, from markdown) |
| scan-history.md remains the shared source of truth | If markdown format changes, parser must handle multiple versions |
| No repo bloat from binary DB changes | |

### Option B: Shared, committed to git

The DB file is committed and pulled/pushed like any other file.

| Pros | Cons |
|------|------|
| Rich cross-agent queries out of the box | Binary merge conflicts on every concurrent push -- breaks workflow |
| Single authoritative data source | Repo bloat -- binary diffs are opaque to git |
| No rebuild step needed | Requires custom merge driver or lock-step pushes |

### Option C: Hybrid -- shared via periodic export/import

DB is local, but a JSON or CSV export is committed periodically (e.g., once per day). Other clones import the export on startup.

| Pros | Cons |
|------|------|
| Avoids binary merge conflicts (JSON/CSV is text) | Two serialization formats to maintain (DB + export) |
| Cross-clone data available, just not real-time | Export/import adds complexity and potential drift |
| Graceful degradation -- each clone works standalone | Stale data between exports |

---

## Q2: Should `suggest-targets` be a standalone CLI command or integrated into cycle.py?

**Category**: Integration / Code Organization

**Why it matters**: Determines how many scripts agents must know about and whether scan index concerns leak into the cycle management script.

### Option A: Standalone `scan_index.py` (RECOMMENDED)

A new script at `references/scripts/scan_index.py` with subcommands: `suggest-targets`, `record-scan`, `record-decision`, `refresh-churn`, `rebuild`.

| Pros | Cons |
|------|------|
| Single-responsibility -- DB management is its own concern | One more script for agents to invoke |
| Follows existing pattern (tracker.py, vault_check.py, etc.) | Sub-skill instructions must reference a new script name |
| Can be tested, versioned, and debugged independently | |
| Clear API surface -- each subcommand is self-documenting | |

### Option B: Integrated into cycle.py

Add `suggest-targets` and `record-scan` as new subcommands of the existing `cycle.py` script.

| Pros | Cons |
|------|------|
| Agents already know cycle.py -- fewer scripts to remember | cycle.py grows in scope beyond cycle management |
| Natural integration point -- scans happen during cycles | DB management code (migration, rebuild) doesn't belong in cycle.py |
| | Harder to test scan index logic in isolation |
| | Violates single-responsibility -- cycle.py becomes a kitchen sink |

### Option C: Python library module imported by sub-skill

Create `references/scripts/scan_index.py` as a library (no CLI), called from within the sub-skill's Python snippets or from cycle.py as an import.

| Pros | Cons |
|------|------|
| No new CLI command to learn | Agents can't invoke it directly from bash in sub-skill steps |
| Clean separation of logic from invocation | Requires a wrapper script or cycle.py integration anyway |
| Easier unit testing of internals | Breaks the pattern of standalone CLI scripts |

---

## Q3: How should human decisions (accept/reject findings) flow back into the DB?

**Category**: Behavior / Feedback Loop

**Why it matters**: Without decision feedback, the composite targeting score cannot learn which files produce valuable findings vs. noise. The acceptance rate signal is what makes the system improve over time.

### Option A: Explicit `record-decision` CLI command called by PM (RECOMMENDED)

PM calls `scan_index.py record-decision --issue <N> --accepted <bool>` when the human approves or rejects an improvement-scan finding. The sub-skill instructions for PM include this step.

| Pros | Cons |
|------|------|
| Explicit -- PM controls when decisions are recorded | Requires PM to remember an extra step after human decisions |
| Simple implementation -- single INSERT/UPDATE | If PM forgets, the feedback loop is broken |
| Works with existing PM workflow (PM already processes human input) | Adds a manual step to an otherwise automated flow |

### Option B: Auto-detect from GitHub Issue label changes

A periodic scan checks GitHub Issues with the `improvement-scan` label. If the issue is closed, infer acceptance. If labeled `wontfix` or similar, infer rejection.

| Pros | Cons |
|------|------|
| Zero manual steps -- fully automated | Inferring intent from labels is fragile -- close != accept |
| Works even if PM forgets | Requires polling GitHub API periodically |
| | Cannot distinguish "accepted and implemented" from "closed as duplicate" |
| | Adds GitHub API dependency to the scan index |

### Option C: Dual-write -- PM records in both scan-history.md and DB simultaneously

When PM updates scan-history.md with "Items rejected by human", also call `record-decision`. The markdown parser on rebuild also extracts decisions.

| Pros | Cons |
|------|------|
| Decisions are captured in both the audit trail and DB | Dual-write consistency risk (same as Risk 3 in research) |
| Rebuild from markdown captures historical decisions too | Parsing "Items rejected by human" prose is fragile |
| Redundancy -- if one fails, the other captures it | More complex implementation |

---

## Q5: What happens to the `file_coverage` table when files are renamed?

**Category**: Compatibility / Data Integrity

**Why it matters**: Git renames break the file_path primary key. Historical coverage for the old path becomes orphaned, and the renamed file appears as "never scanned" -- wasting scan cycles on already-reviewed code.

### Option A: Detect renames during `refresh-churn` and update paths (RECOMMENDED)

On `refresh-churn`, run `git log --follow --diff-filter=R` to detect renames. Update `file_coverage.file_path` and `scans.file_path` for renamed files.

| Pros | Cons |
|------|------|
| Historical coverage carries forward to renamed files | Rename detection adds complexity to refresh-churn |
| No wasted scan cycles on already-reviewed code | git log --follow can be slow on large repos |
| Keeps file_coverage table clean | Edge case: file renamed multiple times creates a chain |

### Option B: Let renamed files appear as "never scanned" (natural reprioritization)

Do nothing. Renamed files get prioritized by the coverage gap signal and re-scanned naturally.

| Pros | Cons |
|------|------|
| Zero implementation cost | Wastes scan cycles re-scanning already-reviewed code |
| Simple mental model -- no rename tracking | Historical coverage data for old path is orphaned forever |
| Renamed files often have changed content anyway -- re-scan is valuable | file_coverage table accumulates dead entries over time |

### Option C: Periodic dead-entry cleanup without rename tracking

On `refresh-churn`, delete file_coverage entries for files that no longer exist on disk. Don't track renames -- just clean up.

| Pros | Cons |
|------|------|
| Keeps file_coverage table clean of deleted files | Renamed files still lose their history |
| Simple implementation -- just check file existence | Better than Option B but doesn't solve the rename problem |
| No git log --follow dependency | |

---

## Q4: Should the composite targeting score weights be configurable (in config.md) or hardcoded?

**Category**: Configurability / Scope

**Why it matters**: Tunable weights let the human optimize scan behavior for their project. Hardcoded is simpler but less flexible. Getting this wrong doesn't break anything -- it just affects scan targeting quality.

### Option A: Hardcode with sensible defaults, add config later if needed (RECOMMENDED)

Ship with fixed weights (coverage_gap=0.3, churn=0.3, cross_role=0.2, acceptance=0.2). Defer configurability to a follow-up task if tuning is needed.

| Pros | Cons |
|------|------|
| Simplest implementation -- no config parsing for weights | Human cannot tune without code changes |
| Avoids premature configurability | If defaults are poor, fixing requires a code change + deploy |
| Weights can be tuned by observing scan results first | |
| Config.md stays clean -- no new fields | |

### Option B: Configurable in config.md from day one

Add a `Scan Index Weights` section to config.md with all four weights as editable fields.

| Pros | Cons |
|------|------|
| Human can tune immediately | Premature -- we don't know which weights need tuning yet |
| Transparent -- weights are visible in config | Adds 4+ new config fields before we know they're needed |
| No code change needed to adjust targeting | Harder to explain to users what the weights mean |

### Option C: Configurable via command-line flags on `suggest-targets`

`scan_index.py suggest-targets --coverage-weight 0.4 --churn-weight 0.3 ...` with defaults baked in.

| Pros | Cons |
|------|------|
| Per-invocation flexibility without config file changes | Sub-skill instructions become verbose with flags |
| Defaults still work if no flags provided | Weights aren't persisted -- must be specified every time |
| Good for experimentation | Inconsistent targeting if different roles use different flags |

---

## Summary Table

| # | Question | Category | Recommended | Key Trade-off |
|---|----------|----------|-------------|---------------|
| Q1 | DB storage model | Architecture | Per-clone (gitignored) | Simplicity vs. cross-clone richness |
| Q2 | CLI integration | Code Organization | Standalone scan_index.py | Single-responsibility vs. fewer scripts |
| Q3 | Decision feedback | Behavior | Explicit record-decision | Reliability vs. automation |
| Q5 | File renames | Compatibility | Detect during refresh-churn | Accuracy vs. implementation cost |
| Q4 | Weight configurability | Scope | Hardcode initially | Simplicity vs. flexibility |

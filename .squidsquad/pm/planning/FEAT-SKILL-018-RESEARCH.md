# FEAT-SKILL-018 Research: Vault Phase 4 -- vault-optimize (Full Vault Sweep)

**Date**: 2026-04-11
**Researcher**: PM research agent
**Feature**: #18 -- Vault Phase 4: vault-optimize (full vault sweep)
**Prior art**: FEAT-17 Research (vault-remember), VAULT-P3-SECOND-BRAIN-RESEARCH.md (coleam00 analysis)

---

## 1. Summary

vault-optimize is an on-demand maintenance command covering five areas: prune (archive stale/superseded/orphan notes), consolidate (merge related galaxy notes into coherent area notes), reindex (rebuild wikilink graph, fix broken links, frontmatter consistency), confidence decay (flag/archive low-confidence unvalidated notes), and relevance scoring (rank notes by reference frequency and usefulness).

The vault currently has 7 notes across PARAG directories (3 galaxy, 2 areas, 1 project, 1 BRIEFING.md) with archives/ and resources/ empty. Growth projections from FEAT-17 research estimate ~660 notes after 30 days, ~8,000 after 1 year. vault-optimize becomes essential at the ~200+ note mark, where manual curation breaks down.

**Recommendation**: Hybrid implementation. A single Python script (`vault_optimize.py`) handles all deterministic operations (staleness detection, orphan finding, link graph building, decay arithmetic, reference counting). Agent prose instructions in a `vault-optimize.md` sub-skill handle judgment calls (merge decisions, archive worthiness, relevance interpretation). The script produces a structured report; the agent acts on it.

---

## 2. Current State Analysis

### 2a. What vault-check Already Does

`vault_check.py` (317 lines) provides:

| Command | What It Does | Relevant to Optimize? |
|---|---|---|
| `validate` | Runs all checks below in sequence | Foundation for reindex |
| `check-structure` | Verifies PARAG dirs + BRIEFING.md exist | No -- structural, not content |
| `check-frontmatter` | Required fields, confidence values, source values on galaxy notes | Yes -- reindex builds on this |
| `check-wikilinks` | Finds broken `[[links]]` across all notes | Yes -- reindex core |
| `list-orphans` | Notes with zero inbound wikilinks (exempt: areas, BRIEFING.md) | Yes -- prune input |
| `dedup-check` | Keyword overlap detection for candidate titles/tags | Yes -- consolidate input |

`vault_remember.py` (384 lines) provides:

| Command | What It Does | Relevant to Optimize? |
|---|---|---|
| `effective-confidence` | Computes decayed confidence for a single note | Yes -- decay core |
| `decay-scan` | Finds all active notes past decay threshold | Yes -- decay core |
| `note-count` | Total vault note count | Useful for health summary |
| `is-quiet` / `write-budget` / etc. | Cycle-level gates | No -- vault-remember specific |

### 2b. What Is Missing (Gap Analysis per Optimization Area)

**Prune gaps**:
- vault-check `list-orphans` finds zero-inbound notes but does NOT move them to archives/
- No staleness-based archiving (vault-check Level 2 flags stale notes but takes no action)
- No detection of superseded notes (status: active but a newer note on the same topic exists)
- No duplicate detection beyond title keywords (dedup-check is write-time only, not sweep-time)

**Consolidate gaps**:
- No mechanism to detect related galaxy notes that should merge
- No tooling to merge note content while preserving changelogs and frontmatter
- No concept of "small galaxy notes" threshold triggering consolidation

**Reindex gaps**:
- vault-check `check-wikilinks` detects broken links but does NOT fix them
- No `links` frontmatter auto-sync across the full vault (only happens per-note on vault-check Level 1)
- No frontmatter consistency enforcement beyond galaxy notes (area/project notes unchecked)

**Confidence decay gaps**:
- `decay-scan` reports notes needing decay but does NOT apply the decay
- `effective-confidence` is read-only (computes but does not write)
- No archival pathway for notes that have decayed to low and remained unvalidated

**Relevance scoring gaps**:
- No reference counting mechanism (how many notes link to a given note)
- No "last accessed" tracking (vault-search does not log accesses)
- No agent citation tracking (when an agent reads a note, that is not recorded)

---

## 3. Analysis per Optimization Area

### 3a. Prune

**Detection criteria for staleness**:
- `status: active` AND `updated` older than configurable threshold (current: 30 days in vault-check, separate from 60-day confidence decay)
- Recommend: staleness threshold = `Confidence Decay Days` from config (60 days), NOT the 30-day flag in vault-check Level 2. The 30-day flag is an early warning; the 60-day threshold triggers action.

**Detection criteria for superseded notes**:
- Two galaxy notes with same type prefix AND >60% keyword overlap in titles/tags (reuse `dedup-check` logic)
- The older note (by `created` date) is the candidate for archival IF the newer one covers the same ground
- This is a judgment call -- script detects candidates, agent decides

**Detection criteria for orphans**:
- Zero inbound wikilinks AND not an area note or BRIEFING.md (already in `list-orphans`)
- Orphan + stale = strong archive candidate
- Orphan alone = warn but do not auto-archive (may be recently created)

**Archival mechanics**:
- Move file from current location to `archives/` preserving the filename
- Update frontmatter: `status: active` -> `status: archived`, add `archived-date: YYYY-MM-DD`
- Append Changelog entry: `Archived by vault-optimize. Reason: [stale|superseded|orphan+stale].`
- Remove all inbound wikilinks to this note across the vault (rewrite `[[note-name]]` to `[[note-name]] (archived)` or just remove the link)
- This is the ONE exception to the "vault-update never deletes content" rule -- archival is a move, not a delete. Content is preserved in archives/.

**Recommendation**: Script detects candidates with reasons. Agent reviews list and confirms each archival. Batch mode available (`--auto-archive` flag) for notes that are both stale AND orphaned (lowest risk).

### 3b. Consolidate

**Detection criteria for merge candidates**:
- Galaxy notes sharing 2+ tags in common
- Galaxy notes within 2 wikilink hops of each other AND same type prefix
- Galaxy notes whose body content has significant keyword overlap (extend dedup-check to body text, not just titles)
- Notes that are individually under ~50 lines (too small to justify being standalone)

**Merge mechanics**:
- Create a new area note (or a larger galaxy note) combining the content
- Each merged source note: change `status` to `archived`, add `superseded-by: [new-note-name]` to frontmatter
- Move source notes to `archives/`
- Update all wikilinks pointing to source notes to point to the new note
- Preserve all Changelog entries from source notes in the new note's Changelog

**Recommendation**: This is the highest-judgment operation. Script can identify candidates by tag overlap and note size. Agent must read the actual content and decide whether merging makes sense. Start conservative -- only suggest merges for notes with 3+ shared tags AND both under 50 lines.

### 3c. Reindex

**What vault-check Level 2 already does**:
- Validates all frontmatter fields on galaxy notes
- Finds all broken wikilinks
- Counts orphans
- Flags stale notes
- Prints health summary

**What a full reindex adds**:
1. **Fix broken links**: For each broken `[[note-name]]`, search vault for close matches (fuzzy filename match). If exactly one candidate found, auto-fix. If multiple or zero, flag for agent review.
2. **Sync `links` frontmatter everywhere**: Currently only auto-maintained per-note on Level 1 check. Reindex would parse all wikilinks from every note body and update all `links` fields in one pass.
3. **Frontmatter consistency for non-galaxy notes**: Validate area notes have `type: area`, project notes have `type: project`. Fill missing optional fields with defaults.
4. **Tag normalization**: Detect tag inconsistencies (e.g., `utf-8` vs `utf8`, `sub-skills` vs `sub-skill`) and suggest canonical forms.
5. **Wikilink graph export**: Build an adjacency list of all notes and their connections. Output as JSON for debugging or visualization. This graph is the foundation for relevance scoring.

**Recommendation**: Mostly deterministic. The script handles link sync, frontmatter validation, graph building. Agent handles fuzzy link resolution (when multiple candidates exist) and tag normalization decisions.

### 3d. Confidence Decay

**Current state**: `config.md` has `Confidence Decay Days: 60`. `vault_remember.py` has `effective-confidence` (read-only computation) and `decay-scan` (report-only). From FEAT-17 research Q4, the decision was Option C: automatic decay with `evergreen` tag exemption.

**What should change**:
1. `decay-scan` currently reports but does not modify notes. vault-optimize should apply the decay: update `confidence` field in frontmatter, append Changelog entry.
2. Add a second decay tier: notes that have been at `confidence: low` for another decay period (60 more days = 120 days total since last update) AND are orphaned should be flagged for archival.
3. The `evergreen` tag exemption is already implemented in `effective-confidence` and `decay-scan`.

**Decay application mechanics**:
- Read current `confidence` from frontmatter
- Apply decay: `high` -> `medium`, `medium` -> `low`
- Write new confidence to frontmatter
- Update `updated` field to today (this resets the decay clock -- deliberate, to prevent cascading decay)
- Append Changelog: `Confidence decayed by vault-optimize (60 days without update). Was: [old], now: [new].`

**Archive trigger**:
- `confidence: low` AND `updated` older than `decay_days` AND zero inbound wikilinks
- This means: the note decayed to low, nobody updated it for another decay period, and nobody links to it
- Agent confirms archival (not automatic)

**Recommendation**: Decay application is deterministic and should be automatic (script applies it). Archive flagging is automatic but archival execution requires agent confirmation.

### 3e. Relevance Scoring

**Metrics available without new infrastructure**:
1. **Inbound link count**: Number of notes linking TO this note. Available from wikilink graph (reindex output).
2. **Outbound link count**: Number of notes this note links TO. Available from frontmatter `links` field.
3. **Centrality**: Notes with high inbound AND outbound links are hubs. Simple degree centrality from the graph.
4. **Recency**: `updated` date. More recently updated = more relevant.
5. **Confidence**: Higher confidence = more reliable.

**Metrics NOT available without new infrastructure**:
- **Agent citation frequency**: Would require logging every vault-search result that an agent actually reads. Not currently tracked. Deferring to FEAT-SKILL-062 (SQLite/RAG).
- **Last-accessed date**: Would require modifying vault-search to log accesses. Invasive change, low ROI for small vaults.

**Composite relevance score** (proposed formula):
```
relevance = (inbound_links * 3) + (outbound_links * 1) + recency_bonus + confidence_bonus
```
Where:
- `recency_bonus`: 5 if updated within 7 days, 3 if within 30 days, 1 if within 90 days, 0 otherwise
- `confidence_bonus`: 3 for high, 1 for medium, 0 for low

**Output**: Ranked list of all notes by relevance score, printed as a report. Notes at the bottom of the list (low relevance) are candidates for archival or consolidation. Notes at the top are the "core knowledge" of the vault.

**Recommendation**: Implement with available metrics only. Do not add access tracking infrastructure. The composite score is a useful heuristic even without citation data. Output as a report that agents can reference during prune/consolidate decisions.

---

## 4. Implementation Approach

### Recommended: Hybrid (Script + Sub-skill)

**`vault_optimize.py`** (new script, ~400-500 lines) handles all deterministic work:

| Command | What It Does | Output |
|---|---|---|
| `prune-scan` | Find stale, orphaned, superseded notes | JSON list of candidates with reasons |
| `consolidate-scan` | Find related small galaxy notes | JSON list of merge candidate groups |
| `reindex` | Full link sync, frontmatter validation, graph build | JSON report: fixes applied, issues found |
| `decay-apply` | Apply confidence decay to eligible notes | JSON list of notes decayed |
| `relevance-report` | Compute and rank all notes by relevance | JSON ranked list |
| `full-sweep` | Run all above in sequence | Combined JSON report |
| `auto-fix` | Apply safe automatic fixes (link sync, frontmatter defaults) | JSON list of fixes applied |

**`vault-optimize.md`** (new sub-skill, ~60-80 lines) handles judgment calls:

- Invoked on-demand (not every cycle). Suggested trigger: every 10th cycle, or when `note-count` exceeds a threshold (e.g., 50 notes), or explicit human request.
- Agent reads the script's report and acts on each section:
  - **Prune**: Confirm archive candidates. Auto-archive stale+orphan notes. Review superseded candidates manually.
  - **Consolidate**: Read merge candidate groups. Decide which to merge, write the merged note, archive sources.
  - **Reindex**: Review fuzzy link matches. Apply tag normalization decisions.
  - **Decay**: Review archive-flagged low-confidence notes. Confirm or override.
  - **Relevance**: Use bottom-ranked notes to inform prune and consolidate decisions.

### Why Not Pure Script?

Consolidation and supersession detection require reading note content and understanding semantic overlap. A script can detect keyword overlap but cannot determine whether two notes about "REST API design" actually cover the same decision or are distinct decisions about different APIs. The agent judgment layer is essential for quality.

### Why Not Pure Prose?

Prune, reindex, and decay are primarily mechanical. Having agents grep through every vault note manually each cycle is wasteful and error-prone. The script does the heavy lifting; the agent provides oversight.

### Config Additions

```markdown
## Vault Optimize

- **Enabled**: yes
- **Auto-Prune Orphan+Stale**: yes
- **Consolidation Threshold Tags**: 3
- **Consolidation Threshold Lines**: 50
- **Relevance Score Weights**: inbound=3, outbound=1, recency=5/3/1/0, confidence=3/1/0
```

---

## 5. Side Effects

### 5a. Vault Content Moves

vault-optimize is the FIRST vault operation that moves files between directories. All existing operations (create, update, check) leave files in place. Archival introduces:
- File moves (galaxy/ -> archives/, areas/ -> archives/)
- Wikilink rewrites across multiple files in a single operation
- Potential for git seeing a delete + create instead of a rename (if the move crosses directory boundaries without `git mv`)

**Mitigation**: Use `git mv` for all archival moves. This preserves git history. The script must handle this, not the agent.

### 5b. Wikilink Graph Mutation

Archiving a note that other notes link to creates broken links unless those links are updated. The reindex step must run AFTER prune to clean up references.

**Recommended execution order**: relevance-report -> prune -> consolidate -> decay-apply -> reindex (always last).

### 5c. Concurrent Agent Access

If vault-optimize runs while another agent is writing to the vault, conflicts can occur:
- Agent creates a note linking to a note that optimize is archiving
- Agent updates a note whose frontmatter optimize is also modifying (link sync)

**Mitigation**: vault-optimize should run during quiet periods or be invoked explicitly. Add a `.squidsquad/vault/.optimize-lock` sentinel file during execution. Other agents check for this file before vault-write operations and defer if present. Lock is removed on completion.

### 5d. Cycle Time

vault-optimize is NOT a per-cycle operation. It runs on-demand. But when it runs, it may take significant time:
- 50 notes: ~5-10 seconds (script) + ~30 seconds (agent review) = ~40 seconds
- 500 notes: ~30-60 seconds (script) + ~2-5 minutes (agent review of candidates) = ~3-6 minutes
- 1000+ notes: May require FEAT-SKILL-062 (SQLite index) for acceptable performance

vault-optimize should NOT run within a normal cycle. It should be a dedicated operation, similar to improvement scanning but less frequent.

---

## 6. Edge Cases

### 6a. Circular Wikilinks

Notes A links to B, B links to A. If both are stale, which gets archived first? The script should detect circular references and present the pair to the agent as a group decision, not individual candidates.

### 6b. Area Note Consolidation Candidates

Area notes (human-profile, code-conventions) are exempt from pruning and size limits. But galaxy notes might suggest consolidation INTO an area note (e.g., three galaxy/style-* notes could merge into areas/design-system.md). The script should detect this pattern but never auto-execute -- area notes are living documents and merging requires careful section placement.

### 6c. Frontmatter Parse Failures

`vault_check.py` uses a simple key:value parser (no PyYAML dependency). This fails on:
- Multi-line values (e.g., `tags:\n  - tag1\n  - tag2`)
- Values containing colons (e.g., `source: code: review`)
- Quoted strings

`vault_optimize.py` should reuse the same parser for consistency but document its limitations. Notes with unparseable frontmatter should be flagged, not skipped silently.

### 6d. Empty Archives Directory

Currently `archives/` only has `.gitkeep`. The first archive operation creates real files there. The script should handle the case where `archives/` does not exist (create it, matching vault-init behavior).

### 6e. Reindex Fixes Conflicting With Agent Edits

If reindex auto-fixes a broken link in note X while an agent is editing note X in the same cycle, the agent's edit may overwrite the fix or vice versa. Mitigated by the lock file (5c) and by running reindex outside normal cycles.

### 6f. Decay Resetting the Clock

When decay is applied, `updated` is set to today. This means a note that decayed from high to medium will not decay again for another 60 days. This is intentional -- it prevents cascading decay within a single optimize run. But it means a note that was high-confidence and truly abandoned takes 120 days to reach low (60 to medium, 60 more to low), and 180 days to be archive-eligible (60 more at low + orphan). This is conservative, which is correct for a knowledge system.

### 6g. Zero Notes to Optimize

On a fresh vault (like the current one with 7 notes), vault-optimize produces an empty report. The script should handle this gracefully: print "Vault healthy -- no optimization needed" and exit 0.

---

## 7. Integration Risks

### 7a. Interaction With vault-remember

vault-remember runs every cycle and creates 0-2 notes. vault-optimize runs occasionally and archives/merges/reindexes. Risk: vault-remember creates a note that vault-optimize archives in the same session (note was created, then optimize sees it as orphaned because nothing links to it yet).

**Mitigation**: vault-optimize should skip notes created within the current day (or configurable grace period). The `created` frontmatter field makes this trivial to check.

### 7b. Interaction With vault-check

vault-optimize subsumes vault-check Level 2. After optimize ships, Level 2 could be deprecated (its checks are a subset of optimize). But Level 2 should remain as a lightweight health check; optimize is the heavy operation.

**Recommendation**: Keep both. vault-check Level 2 = read-only diagnostics. vault-optimize = diagnostics + remediation.

### 7c. Interaction With Improvement Scanning

Improvement scanning reads vault notes (scan-history.md, etc.). If optimize archives notes that scan referenced, the references become stale. Low risk since scan-history is per-agent, not in the vault, and scan does not reference galaxy notes by name.

### 7d. compose.py Integration

vault-optimize.md is a new common sub-skill. It must be added to `references/sub-skills/manifest.md` and included in all role entry files. However, since vault-optimize is on-demand (not every cycle), it could alternatively be invoked via a command rather than composed into CLAUDE.md.

**Recommendation**: Include in CLAUDE.md as a reference section (agents know the command exists) but do not add it to the Ralph Loop steps. Agents invoke it when:
1. The human asks for vault maintenance
2. `note-count` exceeds a threshold
3. A configurable cycle count has passed since last optimize

### 7e. Test Suite

`tests/test_vault.py` validates structure and frontmatter. New tests needed:
- Test prune-scan output format
- Test consolidate-scan tag overlap detection
- Test reindex link sync
- Test decay-apply modifies frontmatter correctly
- Test relevance-report scoring formula
- Test archive move mechanics

---

## 8. Upgrade & Migration

### New Files

| File | Purpose |
|---|---|
| `references/scripts/vault_optimize.py` | Deterministic vault optimization script (~400-500 lines) |
| `references/sub-skills/common/vault-optimize.md` | Agent prose instructions for judgment calls (~60-80 lines) |

### Modified Files

| File | Change |
|---|---|
| `references/sub-skills/manifest.md` | Add vault-optimize entry |
| `references/sub-skills/roles/dev-agent.md` | Add `{{include: common/vault-optimize}}` |
| `references/sub-skills/roles/pm-agent.md` | Add `{{include: common/vault-optimize}}` |
| `.squidsquad/config.md` | Add Vault Optimize section |
| `tests/test_vault.py` | Add vault_optimize tests |

### No Data Migration Needed

vault-optimize only adds new capabilities. Existing vault content is untouched until optimize is explicitly invoked. The archives/ directory already exists with .gitkeep.

### Graceful Degradation

If vault_optimize.py is missing (user has not upgraded), the sub-skill instructions reference a script that does not exist. The agent should check for script existence before invoking and fall back to manual vault-check Level 2 if the script is absent.

---

## 9. Open Questions

### Q1: Should vault-optimize run automatically on a schedule?

**Options**:
- A: On-demand only (human or agent invokes explicitly)
- B: Every N cycles (e.g., every 20 cycles = ~10 hours at 30-min intervals)
- C: When note-count crosses a threshold (e.g., 50, 100, 200)

**Recommendation**: Option A for initial release. Add B as a follow-up if users request it. The vault is small enough that manual invocation is sufficient. Automatic optimization without user awareness could surprise users who find notes archived.

### Q2: Should auto-archive require human confirmation?

**Options**:
- A: All archives require human confirmation
- B: Stale+orphan = auto-archive, all others require confirmation
- C: Everything auto-archives, human can reverse via git

**Recommendation**: Option B. Stale+orphan notes are the safest to auto-archive (nobody links to them, nobody updated them). Superseded and consolidation targets need human or agent review.

### Q3: What is the minimum vault size for optimize to be useful?

**Why it matters**: Running optimize on 7 notes is pointless. Running it on 700 is essential. Where is the threshold?

**Recommendation**: 20 notes minimum. Below that, the vault is small enough to curate manually. The script should check note-count and print "Vault too small for optimization (N notes, minimum 20)" if below threshold.

### Q4: Should relevance scores be stored in frontmatter?

**Options**:
- A: Transient -- computed on each optimize run, not persisted
- B: Stored as `relevance-score: N` in frontmatter, updated each optimize run
- C: Stored in a separate index file (`.squidsquad/vault/.relevance-index.json`)

**Recommendation**: Option C. Relevance scores change with every optimize run and would create noisy git diffs if stored in every note's frontmatter. A separate index file keeps notes clean and is easy to regenerate.

### Q5: How does this interact with FEAT-SKILL-062 (SQLite/RAG)?

**Why it matters**: FEAT-062 adds a SQLite database for vault search. vault-optimize could benefit from SQLite for faster queries on large vaults. But 062 is not yet built.

**Recommendation**: Build vault-optimize using grep/file-based operations (matching existing vault tooling). Design the script interface so that a future SQLite backend can replace the internals without changing the CLI. The `_get_all_notes()` and `_parse_frontmatter()` patterns in vault_check.py already show this abstraction.

### Q6: Should the consolidation step support cross-type merges?

**Example**: A `galaxy/decision-rest-api.md` and a `galaxy/pattern-rest-error-handling.md` are closely related but have different type prefixes. Can they merge?

**Recommendation**: No for initial release. Cross-type merges are complex (which type does the merged note take?). Limit consolidation to same-type notes. Cross-type relationships are better served by wikilinks.

---

## 10. Recommendation

**Feasible with caveats.**

The vault infrastructure is mature enough to support optimization. vault-check and vault-remember provide ~60% of the needed deterministic machinery. The main new work is:

1. **vault_optimize.py** -- new script (~400-500 lines): prune-scan, consolidate-scan, reindex, decay-apply, relevance-report, full-sweep, auto-fix
2. **vault-optimize.md** -- new sub-skill (~60-80 lines): agent instructions for judgment calls
3. **Config additions** -- Vault Optimize section with enable flag and tuning knobs
4. **Test additions** -- 10-15 new test cases in test_vault.py

**Key design principles**:
- **Script does detection, agent does decision**: Never auto-archive without clear criteria (stale+orphan). Never auto-merge.
- **Reindex always runs last**: After all moves and merges, rebuild the link graph.
- **Lock file for concurrency**: Prevent other agents from writing during optimize.
- **Grace period for new notes**: Never optimize notes created today.
- **Git mv for moves**: Preserve history on all archive operations.

**Estimated effort**: 3-4 dev cycles.
- Cycle 1: vault_optimize.py core (prune-scan, reindex, decay-apply) + unit tests
- Cycle 2: vault_optimize.py advanced (consolidate-scan, relevance-report, auto-fix) + unit tests
- Cycle 3: vault-optimize.md sub-skill + config additions + composition + integration testing
- Cycle 4: End-to-end testing with a populated vault (may need to seed test notes)

**Caveats**:
1. **Small vault makes testing hard**: The current vault has 7 notes. Testing requires seeding artificial notes or waiting for organic growth. Recommend a test fixture that creates 20+ notes with known relationships.
2. **Consolidation is high-judgment**: The script can detect candidates but the quality of merges depends entirely on agent judgment. Start conservative (same-type, 3+ shared tags, both under 50 lines).
3. **Archive is irreversible-ish**: While files are preserved in archives/ and git history, fixing bad archives requires manual intervention. The lock file and grace period mitigate this.
4. **Performance at scale is unknown**: grep-based operations on 1000+ notes may be slow. Monitor timing and plan FEAT-062 SQLite migration if needed.

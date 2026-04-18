# FEAT-PM-1278 Research — Vault-Remember: Diff-Based Entity Extraction and Connection Mining

## Summary

The current vault-remember system relies on subjective LLM judgment ("is this significant?") applied to iteration logs at end-of-cycle. The vault has only 10 notes after weeks of operation — the gates are too conservative. The proposed three-layer approach (entity extraction from human messages, comparison against existing vault, connection mining with wikilinks) would shift from passive reflection to active extraction. This research analyzes the current system, identifies why it under-produces, and evaluates the proposed design.

**Recommendation**: Feasible with caveats. The biggest risk is token cost and noise. The design should be layered so entity extraction is cheap (pattern matching), comparison is deterministic (script-based), and only connection mining uses LLM judgment.

## 1. Current Vault-Remember Flow

### Location
- Sub-skill template: `references/sub-skills/common/vault-remember.md`
- Script: `references/scripts/vault_remember.py`
- Deployed in PM's CLAUDE.md as Step 4b (labeled "End-of-Cycle Reflection")
- Also deployed to dev agents (skill, qa) per the manifest (`common/vault-remember` is included for PM + dev agents only)

### Current Gates (in order)

1. **Config gate**: `python references/scripts/config.py get vault-remember` — if `no`, skip entirely
2. **Quiet-cycle gate**: `python references/scripts/vault_remember.py is-quiet [ROLE]` — reads most recent iteration log, checks `Type` field. If quiet cycle (no real work), skip entirely. This is the biggest filter: most cycles are quiet.
3. **Reset write counter**: `vault_remember.py reset-writes [ROLE]` — zeros the per-cycle write counter in working-state.md
4. **Reflection prompt**: LLM reviews iteration log and evaluates 5 categories: DECISIONS, PATTERNS, LEARNINGS, HUMAN PREFERENCES, PROJECT CONTEXT
5. **Gate 1 — Write budget**: `vault_remember.py write-budget [ROLE]` — max 2 writes per cycle (configurable via `Writes Per Cycle` in config.md). Script reads counter from working-state.md.
6. **Gate 2 — Dedup check**: `vault_check.py dedup-check --title "<name>" --tags "<tags>"` — keyword overlap matching (30% threshold). Returns MATCH/no-match.
7. **Gate 3 — Reusability**: LLM judgment — "Is this specific to only this cycle with no future value?"
8. **Gate 4 — Fresh context test**: LLM judgment — "Would a fresh agent in a new context benefit from this?"

### Why It Under-Produces

- The quiet-cycle gate eliminates most cycles (agents are often idle)
- When cycles ARE active, the reflection prompt reviews the **iteration log**, not human messages directly. The iteration log is a terse 2-3 line summary that strips out entity-level detail.
- Gates 3 and 4 are subjective — agents tend to be conservative when unsure, leading to SKIP decisions
- Human preferences are only captured if the agent notices them in the iteration log, not from raw conversation

### Script Capabilities (vault_remember.py)

- `is-quiet <role>`: Checks iteration log Type field within interval window
- `write-budget <role>`: Returns remaining writes (default max 2)
- `inc-writes <role>`: Increments counter in working-state.md
- `reset-writes <role>`: Zeros counter
- `briefing-budget`: Checks BRIEFING.md token count (~word_count * 1.3, default budget 2000)
- `effective-confidence <note>`: Computes confidence with age-based decay (skips evergreen)
- `note-count`: Total .md files in vault
- `decay-scan`: Finds notes needing confidence downgrade

## 2. Current Vault Protocol

### vault-create
1. Pick correct PARAG folder, use kebab-case naming, galaxy notes use type prefix
2. Copy template from `references/vault-templates/`, fill YAML frontmatter (type, tags, created, updated, owner, status, confidence, source, links)
3. Use bare wikilinks `[[note-name]]` in body only
4. Creation threshold: only create if reusable across contexts

### vault-update
1. Read the full note first (never update unread notes)
2. Surgical edit — modify only targeted sections
3. Never delete existing content — add corrections, mark superseded
4. Update `updated` frontmatter date
5. Append to Changelog section
6. Run vault-check Level 1 after updating

### vault-search
Four modes, all grep-based:
- By tag: `grep -rl "tags:.*\b<TAG>\b"`
- By type: `grep -rl "^type: <TYPE>"`
- By keyword: `grep -rl "<KEYWORD>"`
- By wikilink traversal: 1-hop outbound+inbound, max 2-hop
- Max 10 results, sorted by most recently updated, cached within a cycle

### vault-check
- **Level 1** (automatic after every write): Single note + 2-hop neighborhood. Checks frontmatter fields, type-folder match, wikilink resolution, auto-maintains `links` frontmatter, galaxy size warnings.
- **Level 2** (on-demand): Full vault sweep. All Level 1 checks + orphan detection + staleness + broken link census.

### Confidence Levels
- **high**: Human explicitly stated or confirmed
- **medium**: Agent observed directly (code review, conversation patterns)
- **low**: Agent inferred (indirect signals, extrapolation)

### dedup-check (vault_check.py)
- Extracts keywords from candidate title (lowercase, strip galaxy prefixes)
- Compares against all notes: title words + frontmatter tags
- Jaccard-like overlap scoring with 30% minimum threshold
- Returns top 3 matches with overlap percentage

## 3. Existing Vault Content (10 Notes)

### Top-level
- **BRIEFING.md**: 41-line active context summary. Priorities, recent decisions, human preferences (referencing `[[human-profile]]`), constraints, team state.

### Areas (2)
- **areas/human-profile.md**: Communication style (terse, direct), quality expectations (all tests pass), technical preferences (Windows 11, Python), decision-making style (delegate operational, step in for approvals). Confidence: medium. Last updated 2026-04-12.
- **areas/code-conventions.md**: File naming (kebab-case), tracker format (GitHub Issues), discussion protocol, git protocol, sub-skill sources convention. Confidence: medium. Last updated 2026-04-05.

### Projects (1)
- **projects/squidsquad.md**: Project overview, architecture (Claude Code CLI, markdown coordination, git), current focus (v0.14.0 shipped items). Confidence: medium. Last updated 2026-04-08. Note: stale — version is 0.14.0 but config.md says 0.20.0.

### Galaxy (5)
- **galaxy/decision-sub-skill-architecture.md**: Sub-skill layering decision from FEAT-SKILL-030. Confidence: high. Links to squidsquad, code-conventions, learning-atomic-migration-strategy.
- **galaxy/decision-branch-per-feature-workflow.md**: Branch-per-feature from #375. Confidence: high. No outbound links.
- **galaxy/learning-atomic-migration-strategy.md**: Lesson from sub-skill migration — ship atomically. Confidence: medium. Links to decision-sub-skill-architecture, squidsquad.
- **galaxy/pattern-deterministic-scripts-over-prose.md**: Replace prose agent instructions with deterministic scripts. Confidence: high. Links to decision-sub-skill-architecture.
- **galaxy/pattern-windows-utf8-subprocess.md**: Windows encoding fix pattern. Confidence: high. No outbound links.

### Resources (1)
- **resources/cli-anything-research.md**: CLI-Anything research spike. Confidence: medium. No links.

### Observations on Content
- Heavy bias toward architecture/process decisions (5 of 10 notes)
- Human profile is thin — only 5 bullet points of actual preferences
- No company context, design system, or style notes exist
- No archived notes yet (vault too young)
- squidsquad.md is stale (0.14.0 vs 0.20.0) — vault-optimize's staleness detection should catch this but vault has <20 notes so optimize is disabled

## 4. Entity Extraction Design

### What Constitutes "Human Messages"
In the PM cycle, human messages come from:
1. **Check-in responses** (Step 2): Free-form text where humans report bugs, request features, change priorities
2. **AskUserQuestion answers** (Phase 2 discussion): Structured choices or free-form text during task planning
3. **Interrupts**: Human messages between cycles (processed at next Step 2)
4. **Approval/rejection**: Explicit task approval or rejection

Dev agents see human messages less frequently (only via issue comments or direct conversation).

### Entity Types to Detect
1. **Business/company names**: "Acme Corp", "our client FooBar" — maps to `areas/company-context.md`
2. **People names**: "Ask Sarah", "John's team handles this" — maps to `areas/human-profile.md` or new area notes
3. **URLs**: Links to tools, repos, docs — maps to `resources/`
4. **Project names**: "the marketplace project", "SquidSquad" — maps to `projects/`
5. **Preferences/values**: "I prefer X over Y", "never do Z" — maps to `areas/human-profile.md`
6. **Technical patterns**: "always use kebab-case", "we use AGPL" — maps to `areas/code-conventions.md`
7. **Tool/technology mentions**: "we use Figma", "deploy to Vercel" — maps to `resources/` or `projects/`

### Noise Filtering
- Ignore single-word mentions that are common English (not proper nouns)
- Ignore mentions that are purely about the current task context with no reusable value
- Ignore entities already captured in vault with same context
- Require minimum signal: entity must appear in a sentence that provides context (not just a name drop)

### Extraction Approach Options

**Option A — LLM-based extraction**: After processing human messages, ask the LLM to extract entities. Pro: high quality, understands context. Con: token cost every cycle, requires prompt engineering.

**Option B — Pattern matching + LLM confirmation**: Use regex/heuristics to detect candidate entities (capitalized words, URLs, quoted strings), then LLM confirms which are vault-worthy. Pro: cheap first pass. Con: misses implicit preferences.

**Option C — Diff-based extraction**: Compare current human messages against existing vault content. Anything the human says that is NOT already captured is a candidate. Pro: naturally incremental. Con: requires reading vault content each cycle.

**Recommendation**: Hybrid of B and C. Pattern matching extracts candidates, diff against vault filters out known entities, LLM judgment on remaining candidates for reusability.

## 5. Comparison Design

### Current vault-search Capabilities
vault-search is grep-based with four modes. For entity matching specifically:
- **Keyword search** (`grep -rl "<KEYWORD>"`) is sufficient for exact matches
- **Tag search** handles category-based lookups
- **Wikilink traversal** handles relationship navigation

### Limitations for Entity Matching
- **No fuzzy matching**: "Acme" won't match "Acme Corp" unless both words appear in the same note
- **No semantic matching**: "prefers Python" won't match a note about "language preferences"
- **No entity normalization**: "Windows 11", "Windows", "Win11" are all different searches
- **Case-insensitive grep** is available but not used by default in vault-search

### Proposed Comparison Flow
1. **Extract entities** from human messages (see Section 4)
2. **For each entity, run vault-search by keyword**: `grep -rl "<entity>" .squidsquad/vault/`
3. **If match found**: Read the matched note. Is the human providing NEW context about this entity? If yes, vault-update. If no, skip.
4. **If no match**: This is a new entity. Apply Gate 3 (reusability) and Gate 4 (fresh context test). If passes, vault-create.

### Fuzzy Matching Enhancement
The dedup-check in vault_check.py already does keyword overlap scoring (30% threshold). This could be repurposed:
- Extract entity name keywords
- Run dedup-check against vault
- If match >= 60%: treat as "same entity, check for new context"
- If match 30-60%: treat as "possibly related, flag for review"
- If match < 30%: treat as new entity

**Script change needed**: vault_check.py's `dedup-check` could be extended with an `--entity-match` mode that uses lower thresholds and checks body content, not just titles/tags.

### "Same Entity, New Context" Detection
After matching an entity to an existing note, compare the human's statement against the note's content:
- If the human provides a fact/preference NOT in the note: vault-update
- If the human confirms something already in the note: bump confidence to `high` if currently lower
- If the human contradicts something in the note: vault-update with correction (append, never delete)

This comparison is inherently LLM-based — pattern matching cannot determine semantic novelty.

## 6. Connection Mining Design

### Current Wikilink Infrastructure
- vault-check Level 1 auto-maintains `links` frontmatter from body wikilinks
- vault-optimize's `reindex` rebuilds links across all notes
- vault-optimize's `consolidate-scan` detects merge candidates via keyword overlap (40% Jaccard threshold)
- vault-optimize's `relevance` scores notes by inbound links + recency + confidence

### Cross-Reference Detection
When a new entity or update is written, check for connections:
1. **Direct mention**: Does the new note's body mention any existing note names? Auto-add wikilinks.
2. **Tag overlap**: Do any existing notes share 2+ tags with the new note? Suggest wikilinks.
3. **Keyword overlap**: Run dedup-check-style comparison against vault body content. If overlap >= 30%, suggest a wikilink.

### When to Add Links vs Noise
- **Add link**: The connection provides navigational value — following the link reveals useful context
- **Don't add link**: The connection is superficial (e.g., both notes mention "Python" but in unrelated contexts)
- **Rule of thumb**: Would a fresh agent reading Note A benefit from seeing a link to Note B? If yes, add.

### Implementation
vault-check Level 1 already runs after every write and auto-maintains links. The main addition is:
1. After vault-create: scan vault for notes that should link TO the new note (inbound links)
2. After vault-update: check if updates introduce mentions of other notes

This is a natural extension of the existing vault-check infrastructure.

## 7. Side Effects

### Token Cost
- **Entity extraction from human messages**: ~500-1000 tokens per cycle (reading messages + extraction prompt). Only on non-quiet cycles where human messages exist.
- **Vault search per entity**: ~100 tokens per entity (grep results). Typically 0-5 entities per cycle.
- **Comparison/update**: ~500-1000 tokens per matched entity (reading existing note + deciding update).
- **Total per active cycle**: ~1000-3000 additional tokens. On quiet cycles: 0 (quiet gate still applies).

This is modest compared to the overall cycle cost (Steps 1-9 easily consume 10K+ tokens).

### Risk of Over-Writing
- Write budget (max 2 per cycle) is the hard cap — this prevents runaway writes
- The bigger risk is **low-quality writes**: extracting entities that are too granular or transient
- Mitigation: Keep Gates 3 (reusability) and 4 (fresh context test) as final LLM-judgment filters
- Additional mitigation: Entity types have implicit quality bars (a company name is always vault-worthy; a casual tool mention is not)

### Write Budget Sufficiency
- Current budget: 2 writes per cycle
- With entity extraction producing more candidates, the budget becomes more constraining
- However, most cycles will produce 0-1 genuine new entities from human messages
- The priority ordering (human preferences > decisions > learnings > patterns) ensures the most important items are written first
- **Recommendation**: Keep at 2. If evidence shows consistent budget exhaustion with deferred items, consider bumping to 3.

### Interaction with vault-optimize
- vault-optimize only runs when vault has 20+ notes (currently disabled at 10)
- Entity extraction will accelerate note creation, potentially reaching the 20-note threshold sooner
- Once active, vault-optimize's prune (stale+orphan) and confidence decay naturally counterbalance growth
- The consolidate-scan may surface merge candidates among entity-extracted notes (e.g., two company-context updates that should be one note)

## 8. Which Agents Run This

### Current State
vault-remember is included for **PM + dev agents** (per manifest.md: "PM + dev only"). QA and DM get `vault-protocol-slim.md` (read-only operations).

### Recommendation for Entity Extraction
- **PM only** for entity extraction from human messages. PM is the primary human-facing agent; it processes check-in responses, task discussions, and approvals. Dev agents rarely receive direct human messages.
- Dev agents should keep the existing reflection-based vault-remember (reviewing their own iteration logs for patterns and learnings).
- No change needed for QA/DM (read-only vault access).

### Implementation
- Add entity extraction as a new sub-step within vault-remember, BEFORE the existing reflection prompt
- Only PM's vault-remember gets the entity extraction sub-step
- This could be a PM-specific vault-remember variant (`vault-remember-pm.md`) or a conditional block in the common vault-remember

## 9. Upgrade and Migration

### Template Changes
- `references/sub-skills/common/vault-remember.md`: Add entity extraction sub-step (conditionally for PM only, or create a PM-specific variant)
- Recompose affected agent templates via `compose.py deploy-all`

### Script Changes
- **vault_check.py**: Extend `dedup-check` with `--entity-match` mode for lower-threshold matching against note bodies (not just titles)
- **vault_remember.py**: Potentially add an `extract-entities` command that does pattern-matching extraction (URLs, capitalized multi-word phrases, quoted strings) — keeps the deterministic part in scripts per the `pattern-deterministic-scripts-over-prose` vault pattern
- No changes to `vault_optimize.py` (it already handles the downstream effects)

### New Script (optional)
- `vault_entity.py`: Standalone entity extraction and comparison script
  - `extract <text>`: Returns candidate entities (pattern-matched)
  - `compare <entity> [--vault-path]`: Searches vault for matches, returns match status
  - `suggest-links <note-path>`: Suggests wikilinks based on keyword overlap with vault

### Config Changes
- No new config fields required. Entity extraction piggybacks on existing `Vault Remember: Enabled` and `Writes Per Cycle` settings.

### Upgrade Steps
- Template-only change: `compose.py deploy-all` regenerates agent CLAUDE.md files
- No data migration needed (vault structure unchanged)
- Existing vault notes are unaffected
- Graceful degradation for non-upgraded installs: they keep the old reflection-only behavior

## Open Questions

- **Q1**: Should entity extraction run on EVERY non-quiet cycle or only when human messages are present? Running on every cycle wastes tokens scanning empty input. Running only on human-message cycles misses nothing but adds a detection step.
- **Q2**: Should the deterministic entity extraction (pattern matching) live in a new script (`vault_entity.py`) or be added to `vault_remember.py`? Separate script follows the pattern of `vault_check.py` / `vault_optimize.py` separation. Combined keeps it simpler.
- **Q3**: Should connection mining (wikilink suggestions) be part of vault-remember or vault-check? vault-check already handles link maintenance. Adding suggestion logic there keeps link concerns in one place. But vault-remember is the write-time step.
- **Q4**: How to handle entity extraction for dev agents who receive human messages via issue comments? Currently rare, but branch workflow PRs may include human review comments.

## Recommendation

**Feasible with caveats.** The three-layer design is sound:

1. **Entity extraction** (cheap, deterministic pattern matching + LLM confirmation) addresses the core problem — the current system looks at iteration logs, not raw human input
2. **Comparison** (reuse existing dedup-check with lower thresholds) is mostly built already
3. **Connection mining** (extend existing vault-check link maintenance) is a natural extension

Primary risks are token cost per cycle (mitigated by quiet-cycle gate and pattern-matching first pass) and write quality (mitigated by existing write budget and reusability gates). The system should start PM-only and extend to dev agents only if needed.

**Straightforward** for template changes. **Feasible with caveats** for the optional script additions (vault_entity.py or vault_check.py extensions).

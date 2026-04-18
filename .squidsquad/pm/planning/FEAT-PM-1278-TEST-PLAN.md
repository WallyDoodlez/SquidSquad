# FEAT-PM-1278 Test Plan — Vault Entity Extraction + Connection Mining

## Test Cases

### Happy Path

### TC-1: Entity extraction detects a business entity from running context
- **Precondition**: vault_entity.py exists at `references/scripts/vault_entity.py`. Vault is initialized with PARAG structure. No existing note for "Acme Corp".
- **Steps**:
  1. Run `python references/scripts/vault_entity.py extract "We signed a deal with Acme Corp last week for the analytics module"`
  2. Inspect output for detected entities
- **Expected**: Output includes `Acme Corp` as a candidate entity with type `business/company`. Proper JSON or structured output format.
- **Verification**: `python references/scripts/vault_entity.py extract "..." | grep -i "acme"`

### TC-2: Entity extraction detects people, URLs, projects, and patterns
- **Precondition**: vault_entity.py exists and is callable.
- **Steps**:
  1. Run extract with text containing multiple entity types: `"Ask Sarah about the marketplace project. She uses https://figma.com/our-board for designs. Always use kebab-case for file names."`
  2. Inspect output for each entity type
- **Expected**: Output includes: person (`Sarah`), project (`marketplace`), URL (`https://figma.com/our-board`), pattern/preference (`kebab-case for file names`). Each entity has a type classification.
- **Verification**: Output contains at least 3 distinct entity types from a single extraction call.

### TC-3: New entity triggers vault-create
- **Precondition**: Vault has no note about "Acme Corp". Write budget is at 0 used (2 remaining). vault-remember is enabled in config.md.
- **Steps**:
  1. Agent runs entity extraction on cycle context containing "Acme Corp is our primary client"
  2. Agent runs `python references/scripts/vault_check.py dedup-check --title "acme-corp" --tags "company,client"`
  3. Dedup returns no match
  4. Agent creates `areas/company-context.md` or appropriate note via vault-create
  5. Agent runs `python references/scripts/vault_remember.py inc-writes pm`
- **Expected**: New vault note created with frontmatter (type, tags, confidence: medium, source: conversation). Write counter incremented to 1.
- **Verification**: `ls .squidsquad/vault/areas/ | grep -i acme` returns the new file. `python references/scripts/vault_remember.py write-budget pm` returns `1`.

### TC-4: Connection mining adds wikilinks after vault-create
- **Precondition**: Vault contains `projects/squidsquad.md` and `areas/human-profile.md`. A new note `areas/company-context.md` is created that mentions "SquidSquad" in its body.
- **Steps**:
  1. Create `areas/company-context.md` with body text referencing SquidSquad
  2. vault-check Level 1 runs automatically after create
  3. Inspect the new note's `links` frontmatter
- **Expected**: `links` frontmatter includes `squidsquad` (auto-maintained by vault-check Level 1). Body contains `[[squidsquad]]` wikilink if the agent added it, and `links` reflects all body wikilinks.
- **Verification**: `grep -o '\[\[[^]]*\]\]' .squidsquad/vault/areas/company-context.md` shows wikilinks. `grep "links:" .squidsquad/vault/areas/company-context.md` shows the links list.

### TC-5: Connection mining suggests wikilinks for implicit relationships
- **Precondition**: Vault contains `galaxy/pattern-deterministic-scripts-over-prose.md` (tags: architecture, scripts). A new note is created with overlapping tags (e.g., tags: scripts, automation).
- **Steps**:
  1. Create a new galaxy note with tags that overlap with existing notes
  2. vault-check Level 1 runs and scans 2-hop neighborhood
  3. Check if connection suggestions are surfaced
- **Expected**: vault-check suggests wikilinks to notes with tag overlap or keyword overlap (per the extended connection suggestion logic). Suggestions are actionable — agent can accept or skip.
- **Verification**: vault-check output includes suggestion lines for related notes.

### TC-6: Existing entity with new context triggers vault-update
- **Precondition**: `areas/human-profile.md` exists with 5 preferences. Human says "I also prefer dark mode in all tools."
- **Steps**:
  1. Entity extraction detects "dark mode" preference from running context
  2. Agent runs dedup-check or keyword search — matches `human-profile.md`
  3. Agent reads existing note, confirms "dark mode" is NOT already present
  4. Agent performs vault-update: appends "prefers dark mode in all tools" to preferences section
  5. Agent updates `updated` frontmatter date
  6. Agent appends to Changelog
  7. vault-check Level 1 runs
- **Expected**: `human-profile.md` now contains the dark mode preference. `updated` date is today. Changelog has a new entry. No new note created (update, not create). Write counter incremented.
- **Verification**: `grep "dark mode" .squidsquad/vault/areas/human-profile.md` returns a match. Changelog has today's date entry.

---

### Edge Cases

### TC-7: Entity already in vault with same context — skip
- **Precondition**: `areas/human-profile.md` contains "prefers terse, direct communication". Human says "Keep it short and direct."
- **Steps**:
  1. Entity extraction detects preference about communication style
  2. Agent searches vault — matches `human-profile.md`
  3. Agent reads note, determines "terse, direct communication" already covers this
  4. Agent skips — no vault-update needed
- **Expected**: No write performed. Write counter unchanged. Iteration log notes `SKIP: already captured in human-profile.md`.
- **Verification**: `python references/scripts/vault_remember.py write-budget pm` shows same remaining budget as before. No file mtime change on `human-profile.md`.

### TC-8: Fuzzy match — entity name variant matches existing note
- **Precondition**: Vault contains `projects/squidsquad.md`. Running context mentions "SquidSquad project" or "squid squad".
- **Steps**:
  1. Entity extraction detects "SquidSquad" or variant
  2. Comparison layer searches vault — `dedup-check --title "squidsquad"` or keyword search
  3. Match found at >= 60% overlap
- **Expected**: System treats this as "same entity" and checks for new context rather than creating a duplicate note. No duplicate `projects/squidsquad-project.md` created.
- **Verification**: `ls .squidsquad/vault/projects/` shows no new squidsquad-related files. Dedup-check returns MATCH with high overlap score.

### TC-9: No entities found in running context
- **Precondition**: Running context is purely operational with no extractable entities (e.g., "Pulled latest. No pending items. Quiet cycle.").
- **Steps**:
  1. Run `python references/scripts/vault_entity.py extract "Pulled latest. No pending items. Quiet cycle."`
  2. Inspect output
- **Expected**: Output indicates zero candidate entities. No vault writes attempted. Script exits cleanly (exit code 0).
- **Verification**: Output is empty list or explicit "no entities found" message. Exit code is 0.

### TC-10: Write budget exhausted mid-extraction
- **Precondition**: Write budget is 2 (default). Two entities have already been written this cycle (counter = 2).
- **Steps**:
  1. Entity extraction finds a third entity candidate
  2. Agent runs `python references/scripts/vault_remember.py write-budget pm`
  3. Script returns `0` (no budget remaining)
- **Expected**: Third entity is NOT written to vault. Agent logs it as `Vault-worthy but deferred (budget): [description]` in iteration log notes. No error — graceful skip.
- **Verification**: `python references/scripts/vault_remember.py write-budget pm` returns `0` and exits with code 1. Vault note count unchanged. Iteration log contains deferred note.

### TC-11: Quiet cycle skips entity extraction entirely
- **Precondition**: Current cycle is quiet (iteration log Type = quiet). vault-remember is enabled.
- **Steps**:
  1. Agent runs `python references/scripts/vault_remember.py is-quiet pm`
  2. Script returns exit code 0 (quiet)
  3. Agent skips entire vault-remember step including entity extraction
- **Expected**: No entity extraction runs. No vault writes. No vault_entity.py calls. Step is skipped with appropriate log message.
- **Verification**: No vault file mtimes change during quiet cycle. Iteration log shows `Type: quiet`.

### TC-12: Confidence strengthening — human confirms inferred knowledge
- **Precondition**: `areas/human-profile.md` has `confidence: medium` and contains "prefers Python" (agent observed, not human stated). Human explicitly says "Yes, I always use Python."
- **Steps**:
  1. Entity extraction detects preference confirmation
  2. Comparison finds existing note with matching content
  3. Agent detects this is a confirmation of existing content, not new content
  4. Agent updates `confidence` from `medium` to `high` in frontmatter
  5. Appends changelog: "Confidence upgraded to high — human explicitly confirmed Python preference."
- **Expected**: `confidence: high` in frontmatter. Changelog updated. This counts as a vault-update (consumes write budget).
- **Verification**: `grep "confidence: high" .squidsquad/vault/areas/human-profile.md` returns match. Changelog entry present.

### TC-13: Entity extraction on context with only common English words
- **Precondition**: vault_entity.py uses pattern matching to filter noise.
- **Steps**:
  1. Run `python references/scripts/vault_entity.py extract "The system is working well and we should continue as planned"`
  2. Inspect output
- **Expected**: No entities extracted. Common English words ("system", "working", "planned") are not treated as entities. Only proper nouns, URLs, quoted strings, and clear preferences pass the noise filter.
- **Verification**: Output is empty or zero-entity result.

### TC-14: Multiple entities found but only top 2 written (budget cap)
- **Precondition**: Running context contains 4 distinct new entities (a company name, a person, a URL, a preference). Write budget is 2.
- **Steps**:
  1. Entity extraction returns 4 candidates
  2. Agent applies priority ordering: human preferences > decisions > learnings > patterns
  3. Agent writes top 2 by priority
  4. Remaining 2 logged as deferred
- **Expected**: Exactly 2 vault writes. Write counter reaches 2. Remaining candidates noted in iteration log with `Vault-worthy but deferred (budget):` prefix.
- **Verification**: `python references/scripts/vault_remember.py write-budget pm` returns `0`. Iteration log contains deferred items.

---

### Side Effect Regression

### TC-15: Existing vault-remember gates still work
- **Precondition**: vault-remember is enabled. Cycle is non-quiet. Write budget is fresh (reset to 0).
- **Steps**:
  1. Run the full vault-remember step (Step 4b) including entity extraction
  2. Verify Gate 1 (write budget) still checked via `vault_remember.py write-budget pm`
  3. Verify Gate 2 (dedup) still checked via `vault_check.py dedup-check`
  4. Verify Gate 3 (reusability) and Gate 4 (fresh context test) still apply via LLM judgment
- **Expected**: All four gates function identically to pre-#1278 behavior. Entity extraction is an ADDITIONAL source of candidates that feeds into the same gate pipeline. No gate is bypassed or weakened.
- **Verification**: For a candidate that would have been SKIPped before (e.g., cycle-specific detail), it is still SKIPped after entity extraction.

### TC-16: vault-optimize unaffected
- **Precondition**: Vault has 20+ notes (after entity extraction accelerates growth). vault-optimize is enabled.
- **Steps**:
  1. Run `python references/scripts/vault_optimize.py run`
  2. Verify prune, confidence decay, reindex, and relevance scoring work correctly
  3. Check that entity-extracted notes are subject to the same prune/decay rules
- **Expected**: vault-optimize processes entity-extracted notes identically to manually created notes. Stale + orphan galaxy notes are archived. Confidence decay applies. Reindex rebuilds links correctly including new notes.
- **Verification**: `python references/scripts/vault_optimize.py run` completes without errors. Entity-extracted notes with stale dates are flagged for decay.

### TC-17: vault-check Level 1 still auto-maintains links
- **Precondition**: A vault note is created or updated (by entity extraction or otherwise).
- **Steps**:
  1. Create a note with `[[human-profile]]` in body but no `links` in frontmatter
  2. Run vault-check Level 1
  3. Inspect frontmatter
- **Expected**: `links` frontmatter is auto-populated with `human-profile`. This behavior is unchanged by #1278.
- **Verification**: `grep "links:" <note-path>` shows the auto-maintained list. `python references/scripts/vault_check.py check-wikilinks` returns OK.

### TC-18: Write budget enforced across entity extraction AND reflection
- **Precondition**: Entity extraction writes 2 notes (budget exhausted). Reflection prompt then finds a DECISION worth capturing.
- **Steps**:
  1. Entity extraction creates 2 vault notes, incrementing counter to 2
  2. Reflection prompt identifies a decision candidate
  3. Gate 1 check: `python references/scripts/vault_remember.py write-budget pm` returns `0`
  4. Decision candidate is deferred
- **Expected**: Total writes per cycle never exceeds configured maximum (default 2), regardless of whether candidates come from entity extraction or reflection. The budget is shared, not separate.
- **Verification**: `python references/scripts/vault_remember.py write-budget pm` returns `0` after 2 writes from any source. No third write occurs.

### TC-19: vault-search still works with all four modes
- **Precondition**: Entity-extracted notes exist in vault with proper frontmatter (tags, type, wikilinks).
- **Steps**:
  1. Search by tag: `grep -rl "tags:.*\bcompany\b" .squidsquad/vault/ --include="*.md"`
  2. Search by type: `grep -rl "^type: area" .squidsquad/vault/ --include="*.md"`
  3. Search by keyword: `grep -rl "Acme" .squidsquad/vault/ --include="*.md"`
  4. Wikilink traversal from new note
- **Expected**: All four search modes find entity-extracted notes. Results are sorted by most recently updated. Max 10 results.
- **Verification**: Each search mode returns results that include entity-extracted notes.

### TC-20: Connection mining does not create circular wikilinks
- **Precondition**: Note A links to Note B. Note B is updated with entity-extracted content.
- **Steps**:
  1. Update Note B with new content mentioning Note A
  2. Connection mining suggests adding `[[note-a]]` to Note B's body
  3. vault-check Level 1 runs and auto-maintains links
- **Expected**: Bidirectional links (A->B and B->A) are valid and allowed — they are not "circular" in a problematic sense. But connection mining must NOT create self-links (`[[note-b]]` inside Note B). vault-check does not flag bidirectional links as errors.
- **Verification**: No note contains a wikilink to itself. `grep '\[\[note-b\]\]' .squidsquad/vault/.../note-b.md` returns no match.

### TC-21: Connection mining does not create redundant wikilinks
- **Precondition**: Note A already contains `[[human-profile]]` in body.
- **Steps**:
  1. Entity extraction updates Note A with new content
  2. Connection mining runs and detects `human-profile` is already linked
  3. No duplicate wikilink added
- **Expected**: Body contains exactly one instance of `[[human-profile]]`. No duplicate wikilinks introduced.
- **Verification**: `grep -c '\[\[human-profile\]\]' <note-path>` returns `1` (not 2+).

### TC-22: BRIEFING.md staleness check unaffected
- **Precondition**: Entity extraction runs before the BRIEFING.md staleness check in Step 4b.
- **Steps**:
  1. BRIEFING.md has stale version (e.g., 0.14.0 vs config.md 0.20.0)
  2. Entity extraction runs and consumes 1 write
  3. BRIEFING.md staleness check runs
  4. BRIEFING.md is updated with correct version
- **Expected**: BRIEFING.md staleness fix does NOT consume write budget (per existing design). Entity extraction budget is independent of staleness fixes.
- **Verification**: BRIEFING.md updated. Write counter shows only entity extraction writes, not staleness fix.

---

### Upgrade Verification

### TC-23: compose.py deploy-all regenerates templates
- **Precondition**: vault-remember sub-skill template updated with entity extraction sub-step. compose.py is functional.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`
  2. Inspect generated `.squidsquad/pm/CLAUDE.md`
  3. Check that entity extraction instructions are present in PM template
  4. Check that skill/qa templates do NOT include entity extraction
- **Expected**: PM CLAUDE.md includes entity extraction sub-step within vault-remember. Dev agent templates (skill, qa) retain reflection-only vault-remember. compose.py exits cleanly.
- **Verification**: `grep -c "vault_entity" .squidsquad/pm/CLAUDE.md` returns >= 1. `grep -c "vault_entity" .squidsquad/skill/CLAUDE.md` returns 0.

### TC-24: vault_entity.py exists and is callable
- **Precondition**: New script deployed to `references/scripts/vault_entity.py`.
- **Steps**:
  1. Verify file exists: `ls references/scripts/vault_entity.py`
  2. Run help: `python references/scripts/vault_entity.py --help`
  3. Run extract command: `python references/scripts/vault_entity.py extract "test input"`
  4. Run compare command: `python references/scripts/vault_entity.py compare "test entity"`
  5. Run suggest-links command: `python references/scripts/vault_entity.py suggest-links .squidsquad/vault/areas/human-profile.md`
- **Expected**: Script exists. Help text shows available commands (`extract`, `compare`, `suggest-links`). Each command runs without import errors or crashes. Output format is structured and parseable.
- **Verification**: All commands exit with code 0 (or appropriate non-error code). No Python tracebacks.

### TC-25: vault-check extended with connection suggestions
- **Precondition**: vault_check.py has been extended with `--suggest-links` or equivalent.
- **Steps**:
  1. Run `python references/scripts/vault_check.py --help` and confirm new command is listed
  2. Run the connection suggestion command on an existing note
  3. Inspect output format
- **Expected**: New command is documented in help text. Output lists suggested wikilinks with reasoning (tag overlap, keyword match). Suggestions are actionable.
- **Verification**: Help text includes the new command. Running it produces structured output.

### TC-26: Graceful degradation for non-upgraded installs
- **Precondition**: An install that has NOT been upgraded (old templates, no vault_entity.py).
- **Steps**:
  1. Simulate by removing vault_entity.py (or testing on a branch without it)
  2. Run the PM cycle — vault-remember step executes
  3. Entity extraction sub-step attempts to call vault_entity.py
- **Expected**: If vault_entity.py is missing, the entity extraction sub-step is skipped gracefully (command not found is caught). Reflection-based vault-remember still runs. No crash, no lost functionality.
- **Verification**: PM cycle completes without errors. Iteration log shows vault-remember ran (reflection only). No Python traceback.

### TC-27: No new config values required
- **Precondition**: config.md is unchanged from pre-#1278.
- **Steps**:
  1. Read config.md
  2. Verify no new fields are required for entity extraction
  3. Confirm `Vault Remember: Enabled` and `Writes Per Cycle` settings control entity extraction behavior
- **Expected**: Entity extraction piggybacks on existing config. No new fields needed. If `Vault Remember: no`, entity extraction is also disabled (same config gate).
- **Verification**: `python references/scripts/config.py get vault-remember` controls the entire step including entity extraction.

---

## Smoke Tests

- [ ] `python references/scripts/vault_entity.py extract "Hello world"` exits cleanly with no entities
- [ ] `python references/scripts/vault_entity.py extract "Contact John at Acme Corp via https://acme.com"` returns at least 2 entities
- [ ] `python references/scripts/vault_entity.py compare "human-profile"` finds the existing vault note
- [ ] `python references/scripts/vault_entity.py compare "nonexistent-thing-xyz"` returns no match
- [ ] `python references/scripts/vault_entity.py suggest-links .squidsquad/vault/areas/human-profile.md` runs without error
- [ ] `python references/scripts/vault_check.py dedup-check --title "human-profile" --tags "preferences"` still returns MATCH
- [ ] `python references/scripts/vault_remember.py write-budget pm` still returns correct budget
- [ ] `python references/scripts/vault_remember.py is-quiet pm` still correctly detects quiet cycles
- [ ] `python references/scripts/compose.py deploy-all` completes without errors after template changes
- [ ] Vault note count (`python references/scripts/vault_remember.py note-count`) is correct after entity extraction writes

## Regression Risks

- **Write budget shared pool**: Entity extraction and reflection share the same 2-write budget. If entity extraction is too aggressive, reflection candidates get starved. Monitor whether reflection writes drop to zero consistently after entity extraction is added. Mitigation: priority ordering ensures human preferences (often from extraction) rank highest.
- **Token cost creep**: Entity extraction adds ~1000-3000 tokens per active cycle. If extraction text is large (long running context), token cost may exceed the ~3000 target. Mitigation: quiet-cycle gate prevents cost on idle cycles; pattern matching first pass keeps LLM usage minimal.
- **Dedup-check false negatives**: Current dedup-check uses title/tag overlap (30% threshold). Entity names may not match note titles (e.g., entity "Sarah" vs note title "human-profile"). This could cause duplicate notes. Mitigation: entity comparison also uses keyword search against note body content, not just dedup-check.
- **Dedup-check false positives**: Low overlap threshold (30%) may match unrelated notes. Entity "Python" might match `galaxy/pattern-windows-utf8-subprocess.md` if both have common tags. Mitigation: the 60% threshold for "same entity" detection reduces false positives.
- **Connection mining noise**: Aggressive wikilink suggestions could clutter notes with low-value links. Mitigation: suggestions require agent judgment before adding; vault-check Level 1 already handles link cleanup.
- **vault-optimize interaction**: Entity extraction accelerates vault growth, potentially triggering vault-optimize (20-note threshold) sooner than expected. The consolidate-scan may surface merge candidates among entity-extracted notes. This is expected behavior, not a bug — but should be monitored.
- **Dev agent vault-remember unchanged**: Skill and QA agents must NOT receive entity extraction. Only PM gets the new sub-step. If compose.py incorrectly deploys entity extraction to dev agents, they would attempt extraction on iteration logs (wrong input source). Mitigation: TC-23 verifies PM-only deployment.
- **Working-state write counter persistence**: The `Vault Writes This Cycle` counter in working-state.md must be reset at cycle start and survive context window resets. If entity extraction runs in a fresh context after reset, the counter must still reflect writes from earlier in the same cycle. Mitigation: counter is in working-state.md which is committed and read on resume.

## Comprehension Questions

### CQ-1: When does entity extraction run?
- **Files**: vault-remember sub-skill template (updated), PM CLAUDE.md (generated)
- **Expected**: Every non-quiet cycle, from running context. Skipped on quiet cycles (quiet-cycle gate). Skipped if vault-remember is disabled in config.md.

### CQ-2: What happens when entity extraction finds 5 entities but write budget is 2?
- **Files**: vault-remember sub-skill template, vault_remember.py
- **Expected**: Top 2 entities by priority are written (human preferences > decisions > learnings > patterns). Remaining 3 are logged as "Vault-worthy but deferred (budget)" in iteration log notes. No error.

### CQ-3: How does the comparison layer decide between create, update, and skip?
- **Files**: vault-remember sub-skill template, vault_entity.py, vault_check.py
- **Expected**: New entity (no vault match) -> create. Existing entity + new context -> update. Existing entity + same context -> skip. Human confirmation of inferred knowledge -> confidence upgrade (medium->high).

### CQ-4: Which agents get entity extraction?
- **Files**: vault-remember sub-skill template, compose.py manifest
- **Expected**: PM only for v1. Dev agents (skill, qa) keep reflection-only vault-remember. QA/DM have read-only vault access (vault-protocol-slim).

### CQ-5: Does entity extraction consume its own write budget or share with reflection?
- **Files**: vault-remember sub-skill template, vault_remember.py
- **Expected**: Shared budget. Entity extraction and reflection both draw from the same `Writes Per Cycle` pool (default 2). Entity extraction runs BEFORE reflection, so it has first claim on the budget.

# FEAT-SKILL-029 Test Plan — Obsidian Memory Layer (PARAG Vault)

## Test Cases

---

### Phase 1: vault-init + Structure + Templates + vault-create + BRIEFING.md

---

#### TC-1: vault-init creates PARAG directory structure
- **Precondition**: No `.squidsquad/vault/` directory exists
- **Steps**:
  1. Run vault-init (via setup or upgrade flow)
  2. Inspect the created directory tree
- **Expected**: The following directories exist: `projects/`, `areas/`, `resources/`, `archives/`, `galaxy/`. No `inbox/` directory (PARAG, not IPARAG). All directories are under `.squidsquad/vault/`.
- **Verification**:
  ```bash
  test -d .squidsquad/vault/projects && echo "PASS" || echo "FAIL"
  test -d .squidsquad/vault/areas && echo "PASS" || echo "FAIL"
  test -d .squidsquad/vault/resources && echo "PASS" || echo "FAIL"
  test -d .squidsquad/vault/archives && echo "PASS" || echo "FAIL"
  test -d .squidsquad/vault/galaxy && echo "PASS" || echo "FAIL"
  test ! -d .squidsquad/vault/inbox && echo "PASS (no inbox)" || echo "FAIL (inbox exists)"
  ```

#### TC-2: vault-init is idempotent
- **Precondition**: `.squidsquad/vault/` already exists with notes in it
- **Steps**:
  1. Create a test note in `vault/galaxy/decision-test.md`
  2. Run vault-init again (e.g., via upgrade)
  3. Verify the test note is untouched
- **Expected**: Existing vault content is preserved. Missing folders are created. Templates are updated. No data loss.
- **Verification**:
  ```bash
  test -f .squidsquad/vault/galaxy/decision-test.md && echo "PASS" || echo "FAIL"
  ```

#### TC-3: Templates created per folder with YAML frontmatter
- **Precondition**: vault-init has run
- **Steps**:
  1. Check each PARAG folder for a template file
  2. Inspect template content for required YAML frontmatter fields
- **Expected**: Each folder contains a template (`.template.md` or equivalent). Every template includes YAML frontmatter with at minimum: `type`, `tags`, `created`, `updated`, `owner`, `status`, `confidence`, `links`. Galaxy templates additionally include `source` field.
- **Verification**:
  ```bash
  for folder in projects areas resources archives galaxy; do
    echo "--- $folder ---"
    ls .squidsquad/vault/$folder/.template.md 2>/dev/null || ls .squidsquad/vault/$folder/template* 2>/dev/null || echo "FAIL: no template"
  done
  ```

#### TC-4: Confidence field present on every template
- **Precondition**: Templates exist in each vault folder
- **Steps**:
  1. Inspect every template's YAML frontmatter
- **Expected**: All templates include `confidence: high | medium | low` (or a placeholder for the field). No template omits the confidence field.
- **Verification**:
  ```bash
  grep -rl "confidence:" .squidsquad/vault/ | head -20
  # Confirm every template has it
  for folder in projects areas resources galaxy; do
    grep "confidence" .squidsquad/vault/$folder/.template.md && echo "$folder PASS" || echo "$folder FAIL"
  done
  ```

#### TC-5: vault-create produces note from template with correct frontmatter
- **Precondition**: vault-init has run, templates exist
- **Steps**:
  1. Use vault-create to create a galaxy/decision note with title "Use REST over GraphQL", tags [api, architecture], owner dev, confidence medium
  2. Read the created file
- **Expected**: File created at `vault/galaxy/decision-use-rest-over-graphql.md`. YAML frontmatter has: `type: decision`, `tags: [api, architecture]`, `created: YYYY-MM-DD`, `updated: YYYY-MM-DD`, `owner: dev`, `status: active`, `confidence: medium`, `links: []`. Body follows galaxy template structure (Context, Content, Rationale, Related, Changelog sections). Changelog has an initial entry.
- **Verification**:
  ```bash
  test -f .squidsquad/vault/galaxy/decision-use-rest-over-graphql.md && echo "PASS" || echo "FAIL"
  grep "type: decision" .squidsquad/vault/galaxy/decision-use-rest-over-graphql.md
  grep "confidence: medium" .squidsquad/vault/galaxy/decision-use-rest-over-graphql.md
  grep "links:" .squidsquad/vault/galaxy/decision-use-rest-over-graphql.md
  ```

#### TC-6: vault-create prevents duplicate slugs
- **Precondition**: `vault/galaxy/decision-use-rest-over-graphql.md` already exists
- **Steps**:
  1. Attempt vault-create with the same slug
- **Expected**: Agent detects the existing note and does NOT create a duplicate. Either errors/warns or appends a disambiguating suffix.
- **Verification**:
  ```bash
  # Should not have two files with same base slug
  ls .squidsquad/vault/galaxy/decision-use-rest-over-graphql* | wc -l
  # Expected: 1 (original only) or 2 if suffix disambiguation is used
  ```

#### TC-7: vault-create places notes in correct folder by type
- **Precondition**: vault-init has run
- **Steps**:
  1. Create a note with type `area` -> should go in `areas/`
  2. Create a note with type `project` -> should go in `projects/`
  3. Create a note with type `decision` -> should go in `galaxy/`
  4. Create a note with type `pattern` -> should go in `galaxy/`
  5. Create a note with type `resource` -> should go in `resources/`
- **Expected**: Each note lands in the correct PARAG folder. Galaxy notes use type prefix in filename (decision-*, pattern-*, learning-*, style-*).
- **Verification**:
  ```bash
  test -f .squidsquad/vault/areas/*.md && echo "area PASS"
  test -f .squidsquad/vault/projects/*.md && echo "project PASS"
  ls .squidsquad/vault/galaxy/decision-*.md && echo "decision PASS"
  ls .squidsquad/vault/galaxy/pattern-*.md && echo "pattern PASS"
  test -f .squidsquad/vault/resources/*.md && echo "resource PASS"
  ```

#### TC-8: Seed notes created from existing config.md
- **Precondition**: config.md contains project name "SquidSquad"
- **Steps**:
  1. Run vault-init on a fresh install
  2. Check for seed notes
- **Expected**: At minimum: `areas/human-profile.md` (stub), `areas/code-conventions.md` (stub), `projects/squidsquad.md` (seeded from config). All seed notes have valid frontmatter with `confidence: low` (agent-generated stubs).
- **Verification**:
  ```bash
  test -f .squidsquad/vault/areas/human-profile.md && echo "PASS" || echo "FAIL"
  test -f .squidsquad/vault/areas/code-conventions.md && echo "PASS" || echo "FAIL"
  test -f .squidsquad/vault/projects/squidsquad.md && echo "PASS" || echo "FAIL"
  ```

#### TC-9: BRIEFING.md created and kept under ~50 lines
- **Precondition**: vault-init has run
- **Steps**:
  1. Check for BRIEFING.md at the vault root
  2. Count lines
- **Expected**: `.squidsquad/vault/BRIEFING.md` exists. Contains active priorities, recent decisions, and human preferences summary. Line count is <= 50 lines.
- **Verification**:
  ```bash
  test -f .squidsquad/vault/BRIEFING.md && echo "PASS" || echo "FAIL"
  lines=$(wc -l < .squidsquad/vault/BRIEFING.md)
  test "$lines" -le 50 && echo "PASS ($lines lines)" || echo "FAIL ($lines lines, exceeds 50)"
  ```

#### TC-10: BRIEFING.md injected at boot via hooks
- **Precondition**: BRIEFING.md exists with content
- **Steps**:
  1. Inspect agent template/boot hooks for BRIEFING.md injection
  2. Verify the content would be loaded at session start
- **Expected**: Agent templates include a hook/instruction to read BRIEFING.md at boot. The injection is hybrid: BRIEFING.md is loaded at start, deeper vault queries are on-demand.
- **Verification**:
  ```bash
  # Check that agent templates reference BRIEFING.md
  grep -rl "BRIEFING.md" references/sub-skills/ || grep -rl "BRIEFING.md" references/roles/
  ```

#### TC-11: Auto-generated README.md at vault root
- **Precondition**: vault-init has run
- **Steps**:
  1. Check for README.md at vault root
  2. Inspect content
- **Expected**: `.squidsquad/vault/README.md` exists. Contains warning that vault is managed by SquidSquad agents. Shows vault navigation/structure overview. Includes note count or stats if available.
- **Verification**:
  ```bash
  test -f .squidsquad/vault/README.md && echo "PASS" || echo "FAIL"
  grep -i "managed by SquidSquad" .squidsquad/vault/README.md || grep -i "do not edit" .squidsquad/vault/README.md
  ```

#### TC-12: .obsidian/ directory created and gitignored
- **Precondition**: vault-init has run
- **Steps**:
  1. Check for `.obsidian/` directory under vault
  2. Check `.gitignore` entries
- **Expected**: `.squidsquad/vault/.obsidian/` exists with seed config (app.json or graph.json). The `.gitignore` includes rules to ignore `.obsidian/*` except seed config files.
- **Verification**:
  ```bash
  test -d .squidsquad/vault/.obsidian && echo "PASS" || echo "FAIL"
  grep ".obsidian" .gitignore || grep ".obsidian" .squidsquad/.gitignore
  ```

#### TC-13: Bare wikilinks only -- no alias syntax
- **Precondition**: vault-create has been used to create notes with Related sections
- **Steps**:
  1. Search all vault notes for wikilink syntax
  2. Check for alias syntax `[[note|display text]]`
- **Expected**: All wikilinks use bare form `[[note-name]]`. No alias syntax (`|`) found in any wikilink.
- **Verification**:
  ```bash
  # Should find zero matches for alias syntax
  grep -rP '\[\[[^\]]+\|[^\]]+\]\]' .squidsquad/vault/ && echo "FAIL (alias found)" || echo "PASS (bare only)"
  ```

#### TC-14: Append-only changelog on every note
- **Precondition**: A vault note has been created
- **Steps**:
  1. Read the note's Changelog section
  2. Verify it has at least one entry (the creation entry)
- **Expected**: Every vault note has a `## Changelog` section at the bottom. The creation entry is present with date, agent, and reason. Changelog entries are never deleted, only appended.
- **Verification**:
  ```bash
  grep "## Changelog" .squidsquad/vault/galaxy/decision-use-rest-over-graphql.md && echo "PASS" || echo "FAIL"
  ```

#### TC-15: Vault sub-skills composed into all agent templates
- **Precondition**: Phase 1 implementation complete
- **Steps**:
  1. Check the sub-skill manifest for vault sub-skill entries
  2. Verify each role's entry file includes vault sub-skills
- **Expected**: `references/sub-skills/manifest.md` lists vault-create (and other vault skills per phase). All role entry files include vault sub-skill composition directives.
- **Verification**:
  ```bash
  grep "vault-create" references/sub-skills/manifest.md && echo "PASS" || echo "FAIL"
  ```

---

### Phase 2: vault-update + vault-search + vault-check

---

#### TC-16: vault-update modifies content and preserves unchanged sections
- **Precondition**: `vault/areas/human-profile.md` exists with Summary, Current State, Key Points, and Changelog sections
- **Steps**:
  1. Use vault-update to modify only the "Key Points" section
  2. Read the full note
- **Expected**: Key Points section reflects the update. Summary, Current State, and Related sections are unchanged. `updated` frontmatter field is set to today. A new Changelog entry is appended describing the update.
- **Verification**:
  ```bash
  grep "updated:" .squidsquad/vault/areas/human-profile.md
  # Confirm changelog grew
  grep -c "^\- \[" .squidsquad/vault/areas/human-profile.md
  ```

#### TC-17: vault-update never deletes existing content
- **Precondition**: A galaxy note has 3 key points and 2 changelog entries
- **Steps**:
  1. Use vault-update to add a 4th key point
  2. Verify all original content remains
- **Expected**: Original 3 key points still present. New 4th point added. Original 2 changelog entries preserved, new 3rd entry appended.
- **Verification**:
  ```bash
  # Count key points and changelog entries -- both should have grown by 1
  ```

#### TC-18: vault-update updates frontmatter `updated` field
- **Precondition**: A note with `updated: 2026-03-01`
- **Steps**:
  1. Use vault-update to modify the note on 2026-04-02
- **Expected**: `updated` field changes to `2026-04-02`. All other frontmatter fields unchanged.
- **Verification**:
  ```bash
  grep "updated: 2026-04-02" .squidsquad/vault/galaxy/decision-use-rest-over-graphql.md
  ```

#### TC-19: vault-search by tag
- **Precondition**: Multiple vault notes exist, some tagged `architecture`, others not
- **Steps**:
  1. Run vault-search for tag `architecture`
- **Expected**: Returns only notes whose `tags` frontmatter contains `architecture`. Results include file paths and relevant excerpts. Max 10 results.
- **Verification**:
  ```bash
  grep -rl "tags:.*architecture" .squidsquad/vault/
  ```

#### TC-20: vault-search by type
- **Precondition**: Galaxy notes of various types exist (decision, pattern, learning)
- **Steps**:
  1. Run vault-search for `type: decision`
- **Expected**: Returns all decision-type notes from the vault. Correctly filters by frontmatter type field.
- **Verification**:
  ```bash
  grep -rl "^type: decision" .squidsquad/vault/
  ```

#### TC-21: vault-search full-text keyword
- **Precondition**: Some vault notes mention "error handling", others do not
- **Steps**:
  1. Run vault-search for keyword "error handling"
- **Expected**: Returns notes containing the phrase, with file paths and matching excerpts. Max 10 results.
- **Verification**:
  ```bash
  grep -rl "error handling" .squidsquad/vault/
  ```

#### TC-22: vault-search wikilink traversal (1-hop)
- **Precondition**: Note A links to `[[note-B]]` and `[[note-C]]`. Note D links to `[[note-A]]`.
- **Steps**:
  1. Run vault-search with wikilink traversal from note A, 1-hop
- **Expected**: Returns note-B and note-C (outbound links) and note-D (inbound link). Does not return unrelated notes.
- **Verification**:
  ```bash
  # Outbound
  grep -oP '\[\[([^\]]+)\]\]' .squidsquad/vault/galaxy/note-A.md
  # Inbound
  grep -rl '\[\[note-A\]\]' .squidsquad/vault/
  ```

#### TC-23: vault-search wikilink traversal (2-hop)
- **Precondition**: Note A -> [[note-B]], note-B -> [[note-C]], note-C -> [[note-D]]
- **Steps**:
  1. Run vault-search with 2-hop traversal from note A
- **Expected**: Returns note-B (1-hop), note-C (2-hop via B). Does NOT return note-D (3-hop). Traversal stops at 2 hops.
- **Verification**:
  ```bash
  # Manually verify the graph structure and confirm 2-hop boundary
  ```

#### TC-24: vault-search returns max 10 results
- **Precondition**: 15+ notes match a broad keyword search
- **Steps**:
  1. Run vault-search for a common term
- **Expected**: Returns at most 10 results. Agent can narrow and re-search.
- **Verification**:
  ```bash
  # Count results returned by search -- should be <= 10
  ```

#### TC-25: vault-search interface abstracted for future SQLite swap
- **Precondition**: vault-search sub-skill file exists
- **Steps**:
  1. Read the vault-search sub-skill instructions
  2. Verify the interface does not expose grep-specific details to calling agents
- **Expected**: The search interface (input: query terms/filters, output: list of note paths + excerpts) is generic. The grep implementation is internal. A future SQLite implementation (FEAT-SKILL-062) could replace the internals without changing how agents invoke vault-search.
- **Verification**:
  ```bash
  # Manual review of vault-search sub-skill file for interface abstraction
  ```

#### TC-26: vault-check Level 1 validates required frontmatter
- **Precondition**: A note with missing `confidence` field in frontmatter
- **Steps**:
  1. Run vault-check Level 1 on the note
- **Expected**: Reports a warning/error for missing `confidence` field. Lists all required fields that are missing or malformed.
- **Verification**:
  ```bash
  # Create a note with deliberately missing field, run vault-check, observe warning
  ```

#### TC-27: vault-check Level 1 validates type matches folder
- **Precondition**: A note in `galaxy/` with `type: area` in frontmatter (mismatch)
- **Steps**:
  1. Run vault-check Level 1 on the note
- **Expected**: Reports a type-folder mismatch warning. Galaxy notes should have type `decision`, `pattern`, `learning`, `style`, or `preference`.
- **Verification**:
  ```bash
  # Manual -- introduce mismatch, run check, observe result
  ```

#### TC-28: vault-check Level 1 validates wikilinks resolve
- **Precondition**: A note containing `[[nonexistent-note]]`
- **Steps**:
  1. Run vault-check Level 1 on the note
- **Expected**: Reports a broken wikilink for `[[nonexistent-note]]`.
- **Verification**:
  ```bash
  # vault-check output should list unresolved wikilinks
  ```

#### TC-29: vault-check Level 1 auto-maintains links frontmatter
- **Precondition**: A note has `[[code-conventions]]` and `[[design-system]]` in its body, but `links: []` in frontmatter
- **Steps**:
  1. Run vault-check Level 1 (which parses content and updates links)
- **Expected**: Frontmatter `links` field is updated to include `code-conventions` and `design-system`. Agent does not manually curate this field.
- **Verification**:
  ```bash
  grep "links:.*code-conventions" .squidsquad/vault/galaxy/decision-use-rest-over-graphql.md
  ```

#### TC-30: vault-check Level 1 runs on every vault write
- **Precondition**: Agent uses vault-create or vault-update
- **Steps**:
  1. Create a new note via vault-create
  2. Update a note via vault-update
  3. Verify vault-check Level 1 runs after each operation
- **Expected**: vault-check Level 1 is invoked automatically after every write. The check covers the written note and its 2-hop neighborhood.
- **Verification**:
  ```bash
  # Check for vault-check output/log after write operations
  ```

#### TC-31: vault-check warns on galaxy notes exceeding 500 lines
- **Precondition**: A galaxy note with 501+ lines
- **Steps**:
  1. Run vault-check Level 1 on the note
- **Expected**: Warning emitted that the galaxy note exceeds the 500-line limit. Suggestion to split the note.
- **Verification**:
  ```bash
  wc -l .squidsquad/vault/galaxy/learning-big-note.md
  # vault-check should warn
  ```

#### TC-32: vault-check does NOT warn on large area notes
- **Precondition**: An area note (`areas/human-profile.md`) with 600+ lines
- **Steps**:
  1. Run vault-check Level 1 on the note
- **Expected**: No line-count warning. Area notes have no line limit.
- **Verification**:
  ```bash
  # vault-check output should have no line-count warning for areas/
  ```

#### TC-33: vault-check Level 2 full vault sweep
- **Precondition**: Vault has 10+ notes, some with broken links, some stale, some orphaned
- **Steps**:
  1. Run vault-check Level 2 (full sweep)
- **Expected**: Reports: total note count, orphan notes (no inbound wikilinks, not area notes), stale notes (`updated` > 30 days for active status), all broken wikilinks across the vault. Produces a vault health summary.
- **Verification**:
  ```bash
  # Review vault-check Level 2 output for completeness
  ```

---

### Phase 3: vault-remember (hooks in all agents)

---

#### TC-34: vault-remember fires after significant work steps
- **Precondition**: vault-remember hook is composed into agent template
- **Steps**:
  1. Agent completes a feature implementation (dev) or bug fix
  2. vault-remember hook triggers
  3. Agent evaluates trigger conditions
- **Expected**: After completing work, the agent checks its role-specific trigger list. If a trigger fires (e.g., architecture decision made), a capture is written.
- **Verification**:
  ```bash
  # Check for vault-remember captures after a dev cycle that made an architecture decision
  ```

#### TC-35: vault-remember writes directly to correct PARAG folder (no inbox)
- **Precondition**: vault-remember triggers on a decision observation
- **Steps**:
  1. vault-remember creates a capture for a decision
  2. Check where it was written
- **Expected**: Note written directly to `vault/galaxy/decision-*.md` (not to an inbox folder). Agents classify at capture time per the PARAG-not-IPARAG decision.
- **Verification**:
  ```bash
  test ! -d .squidsquad/vault/inbox && echo "PASS (no inbox)" || echo "FAIL"
  ls .squidsquad/vault/galaxy/decision-*.md
  ```

#### TC-36: vault-remember rate limit -- 3 captures per cycle max
- **Precondition**: Agent encounters 5 trigger-worthy observations in a single cycle
- **Steps**:
  1. Agent evaluates 5 potential captures
  2. Agent selects the 3 most significant
- **Expected**: Exactly 3 captures are created. The remaining 2 are dropped. Selection priority: decisions > preferences > patterns > learnings.
- **Verification**:
  ```bash
  # Count vault notes created in a single cycle -- should be <= 3
  ```

#### TC-37: vault-remember deduplication check
- **Precondition**: `vault/galaxy/decision-use-rest-over-graphql.md` already exists. Agent encounters the same decision again.
- **Steps**:
  1. vault-remember considers capturing "use REST over GraphQL"
  2. Agent greps vault for existing note on this topic
- **Expected**: Agent detects the existing note and skips the duplicate capture. Optionally updates the existing note's changelog instead of creating a new note.
- **Verification**:
  ```bash
  # No duplicate file created
  ls .squidsquad/vault/galaxy/decision-use-rest-over-graphql* | wc -l
  # Expected: 1
  ```

#### TC-38: vault-remember per-role trigger tables
- **Precondition**: vault-remember sub-skill file exists
- **Steps**:
  1. Read the vault-remember sub-skill for role-specific triggers
  2. Verify each role has defined triggers
- **Expected**: Trigger tables exist for: PM (preferences, decisions from check-ins), Dev (architecture decisions, code patterns, learnings), QA (test patterns, failure modes, quality standards), Designer (style preferences, design system evolution), DM (doc conventions, release patterns). Each role fires only its own triggers.
- **Verification**:
  ```bash
  grep -c "trigger" references/sub-skills/common/vault-remember.md
  ```

#### TC-39: vault-remember does not bloat cycle time
- **Precondition**: Agent running a normal cycle with vault-remember active
- **Steps**:
  1. Observe the vault-remember overhead per cycle
- **Expected**: vault-remember adds minimal overhead. The capture operation (write one markdown file) takes ~1 second. The dedup grep check takes ~100ms. Total vault-remember overhead < 5 seconds per cycle for non-PM agents.
- **Verification**:
  ```bash
  # Timing observation -- compare cycle times with and without vault-remember
  ```

#### TC-40: vault-remember creates notes with confidence field set appropriately
- **Precondition**: vault-remember triggers from different sources
- **Steps**:
  1. Agent observes a human-confirmed preference -> capture
  2. Agent infers a pattern from code -> capture
- **Expected**: Human-confirmed observations get `confidence: high`. Agent-observed patterns get `confidence: medium`. Agent-inferred knowledge gets `confidence: low`.
- **Verification**:
  ```bash
  grep "confidence:" .squidsquad/vault/galaxy/preference-*.md
  grep "confidence:" .squidsquad/vault/galaxy/pattern-*.md
  ```

#### TC-41: vault-remember creates valid notes that pass vault-check
- **Precondition**: vault-remember creates a capture
- **Steps**:
  1. vault-remember writes a note
  2. vault-check Level 1 runs on the new note
- **Expected**: The auto-created note passes all vault-check Level 1 validations: valid frontmatter, correct type for folder, valid wikilinks (or none), changelog entry present.
- **Verification**:
  ```bash
  # vault-check Level 1 output should show no errors for auto-captured notes
  ```

#### TC-42: All agent templates include vault-remember hook
- **Precondition**: Phase 3 implementation complete
- **Steps**:
  1. Check each role's composed template for vault-remember integration
- **Expected**: Dev, PM, QA, Designer, and DM templates all include vault-remember hooks at the appropriate Ralph Loop integration points (after work steps, before logging).
- **Verification**:
  ```bash
  for role in dev-agent pm-agent pm-lean qa-agent designer dm-agent; do
    grep -l "vault-remember" references/roles/$role.md && echo "$role PASS" || echo "$role FAIL"
  done
  ```

---

### Phase 4: vault-optimize

---

#### TC-43: vault-optimize runs vault-check Level 2
- **Precondition**: Vault has notes in various states (active, stale, orphaned, with broken links)
- **Steps**:
  1. Run vault-optimize
  2. Check that a full Level 2 sweep was performed
- **Expected**: vault-optimize begins with a Level 2 vault-check. The health summary is reported before any optimization actions are taken.
- **Verification**:
  ```bash
  # vault-optimize output includes vault-check Level 2 results
  ```

#### TC-44: vault-optimize archives stale notes
- **Precondition**: A galaxy note with `status: active` and `updated` > 90 days ago, no inbound wikilinks from active notes
- **Steps**:
  1. Run vault-optimize
- **Expected**: The stale note is moved to `archives/`. Its `status` field changes to `archived`. Wikilinks pointing to the old location are updated or a redirect note is left.
- **Verification**:
  ```bash
  test -f .squidsquad/vault/archives/decision-old-thing.md && echo "PASS" || echo "FAIL"
  grep "status: archived" .squidsquad/vault/archives/decision-old-thing.md
  ```

#### TC-45: vault-optimize detects and suggests merging near-duplicates
- **Precondition**: Two galaxy notes covering the same topic from different angles (e.g., `decision-auth-flow.md` and `decision-authentication-approach.md`)
- **Steps**:
  1. Run vault-optimize
- **Expected**: vault-optimize identifies the near-duplicate pair and either merges them (consolidating content, redirecting wikilinks) or reports them for review.
- **Verification**:
  ```bash
  # Check vault-optimize output for duplicate detection
  ```

#### TC-46: vault-optimize suggests tag normalization
- **Precondition**: Some notes tagged `auth`, others `authentication`, others `authn` -- same concept
- **Steps**:
  1. Run vault-optimize
- **Expected**: vault-optimize detects inconsistent tagging and suggests normalization (e.g., standardize on `authentication`).
- **Verification**:
  ```bash
  # Check vault-optimize output for tag normalization suggestions
  ```

#### TC-47: vault-optimize reports vault size metrics
- **Precondition**: Vault has notes across all PARAG folders
- **Steps**:
  1. Run vault-optimize
- **Expected**: Reports: note count per folder, total vault size, recent updates count, overall health score.
- **Verification**:
  ```bash
  # vault-optimize output includes stats section
  ```

#### TC-48: vault-optimize refreshes README.md with stats
- **Precondition**: README.md exists from vault-init. Vault has grown since init.
- **Steps**:
  1. Run vault-optimize
  2. Read README.md
- **Expected**: README.md is refreshed with current stats: note count, recent updates, health summary. The "managed by SquidSquad" warning is preserved.
- **Verification**:
  ```bash
  grep -i "note count\|notes:" .squidsquad/vault/README.md
  ```

#### TC-49: vault-optimize available as on-demand 7th skill
- **Precondition**: Phase 4 implementation complete
- **Steps**:
  1. Verify vault-optimize can be invoked on demand (not just in scheduled PM cycles)
- **Expected**: vault-optimize is usable as both: (a) a periodic PM cycle step, and (b) an on-demand invocation by human or PM. It is the 7th vault skill, separate from the 6 core skills.
- **Verification**:
  ```bash
  test -f references/sub-skills/common/vault-optimize.md && echo "PASS" || echo "FAIL"
  ```

---

### Cross-Phase: Multi-Agent Concurrency

---

#### TC-50: Concurrent note creation by different agents (different files)
- **Precondition**: Two agents (dev and QA) both create new galaxy notes in the same cycle
- **Steps**:
  1. Dev creates `galaxy/pattern-error-handling.md`
  2. QA creates `galaxy/learning-null-checks.md`
  3. Both commit and push (with pull-rebase-push discipline)
- **Expected**: Both notes exist in the vault. No merge conflict (different files). Git rebase resolves cleanly.
- **Verification**:
  ```bash
  test -f .squidsquad/vault/galaxy/pattern-error-handling.md && echo "PASS"
  test -f .squidsquad/vault/galaxy/learning-null-checks.md && echo "PASS"
  ```

#### TC-51: Concurrent updates to same note -- append-only changelog
- **Precondition**: Two agents both update the same area note's changelog section
- **Steps**:
  1. Agent A appends changelog entry, commits, pushes
  2. Agent B appends a different changelog entry, pulls (rebase), pushes
- **Expected**: Both changelog entries are preserved after rebase. Git auto-merges concurrent appends to different lines.
- **Verification**:
  ```bash
  # Both changelog entries present in the note
  ```

#### TC-52: Concurrent frontmatter update -- last write wins for timestamps
- **Precondition**: Two agents both update the same note's `updated` field
- **Steps**:
  1. Agent A updates note, sets `updated: 2026-04-02`
  2. Agent B updates same note, sets `updated: 2026-04-02`
  3. One rebase conflict occurs on the `updated` line
- **Expected**: Conflict resolved by keeping the later write. The timestamp is the same (both are today), so either resolution is correct. No data loss.
- **Verification**:
  ```bash
  grep "updated: 2026-04-02" .squidsquad/vault/areas/human-profile.md
  ```

#### TC-53: Git pull-rebase-push cycle for vault writes
- **Precondition**: Agent is about to write to vault
- **Steps**:
  1. Agent runs `git pull --rebase` at cycle start
  2. Agent writes vault note(s) during cycle
  3. Agent commits and pushes at cycle end
  4. If push fails, agent pulls again and retries
- **Expected**: Vault writes follow the existing SquidSquad git protocol. No special locking mechanism needed. Rebase handles concurrent changes.
- **Verification**:
  ```bash
  # Observe git log -- vault commits follow pull-rebase-push pattern
  ```

---

### Cross-Phase: Obsidian Compatibility

---

#### TC-54: Vault opens in Obsidian as a valid vault
- **Precondition**: vault-init has run, `.obsidian/` seed config exists
- **Steps**:
  1. Open `.squidsquad/vault/` as an Obsidian vault
  2. Navigate the graph view
- **Expected**: Obsidian recognizes the directory as a vault. Notes render with proper markdown. Wikilinks `[[note-name]]` are clickable. Graph view shows connections between notes.
- **Verification**:
  ```bash
  # Manual verification in Obsidian app
  test -d .squidsquad/vault/.obsidian && echo "PASS" || echo "FAIL"
  ```

#### TC-55: Wikilinks are valid Obsidian wikilinks
- **Precondition**: Notes exist with `[[note-name]]` wikilinks
- **Steps**:
  1. Verify wikilinks match the bare `[[filename-without-extension]]` format Obsidian expects
  2. Verify linked notes exist
- **Expected**: All `[[wikilinks]]` in vault notes correspond to actual files (minus `.md` extension). Obsidian can resolve them.
- **Verification**:
  ```bash
  # Extract all wikilinks, check each resolves to a file
  grep -roP '\[\[([^\]]+)\]\]' .squidsquad/vault/ | sort -u
  ```

---

### Cross-Phase: Upgrade Path

---

#### TC-56: Fresh install creates vault during setup
- **Precondition**: No `.squidsquad/` exists
- **Steps**:
  1. Run `/squidsquad-setup`
  2. Verify vault is created as part of setup
- **Expected**: vault-init runs as part of setup. PARAG structure, templates, seed notes, BRIEFING.md, and README.md all created.
- **Verification**:
  ```bash
  test -d .squidsquad/vault && echo "PASS" || echo "FAIL"
  ```

#### TC-57: Existing install adds vault via upgrade (non-destructive)
- **Precondition**: `.squidsquad/` exists but no `vault/` directory
- **Steps**:
  1. Run `/squidsquad-upgrade`
  2. Verify vault is created
  3. Verify existing tracker files are untouched
- **Expected**: Vault is created. All existing `.squidsquad/` content (bugs, features, iterations, config) is completely untouched. Upgrade is additive only.
- **Verification**:
  ```bash
  test -d .squidsquad/vault && echo "PASS (vault created)" || echo "FAIL"
  test -f .squidsquad/config.md && echo "PASS (config preserved)" || echo "FAIL"
  ```

#### TC-58: Upgrade preserves existing vault data
- **Precondition**: `.squidsquad/vault/` exists with user-created notes
- **Steps**:
  1. Run `/squidsquad-upgrade`
  2. Verify all existing vault notes are untouched
- **Expected**: Vault data is never overwritten by upgrade. Templates may be updated, but existing notes are preserved exactly.
- **Verification**:
  ```bash
  # Compare note content before and after upgrade -- should be identical
  ```

---

## Smoke Tests

After each phase, run these quick smoke tests before marking Pending Test:

### Phase 1 Smoke
1. `test -d .squidsquad/vault/galaxy` -- PARAG structure exists
2. `test ! -d .squidsquad/vault/inbox` -- No inbox folder (PARAG not IPARAG)
3. `test -f .squidsquad/vault/BRIEFING.md` -- BRIEFING.md exists
4. `test -f .squidsquad/vault/README.md` -- README.md exists
5. `wc -l < .squidsquad/vault/BRIEFING.md` -- Under 50 lines
6. `grep "confidence" .squidsquad/vault/areas/human-profile.md` -- Confidence field on seed note
7. `grep -rP '\[\[[^\]]+\|' .squidsquad/vault/` -- No alias wikilinks (should be empty)
8. Create a galaxy decision note, verify it lands in `galaxy/` with correct frontmatter

### Phase 2 Smoke
1. Update an area note, verify `updated` field changes and changelog appended
2. Search for a known keyword, verify results are returned
3. Introduce a broken wikilink, run vault-check Level 1, verify it is caught
4. Create a galaxy note with 501 lines, run vault-check, verify warning
5. Run vault-check Level 2, verify health summary is produced

### Phase 3 Smoke
1. Simulate a dev cycle that makes an architecture decision, verify vault-remember creates a capture in `galaxy/`
2. Simulate 5 triggers in one cycle, verify only 3 captures are created (rate limit)
3. Verify captures have appropriate confidence values
4. Verify captures pass vault-check Level 1

### Phase 4 Smoke
1. Run vault-optimize on a vault with stale notes, verify archival
2. Verify README.md is refreshed with current stats
3. Verify vault-optimize reports vault health metrics

---

## Regression Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| **Template bloat** | Adding vault sub-skills to all agent templates increases template size, potentially causing context pressure | Monitor template sizes after each phase. Vault sub-skills should be concise. |
| **Ralph Loop cycle time** | vault-remember + vault-check on every write could slow cycles | vault-remember is capped at 3 captures. vault-check Level 1 is single-note + 2-hop only. Monitor cycle times. |
| **Git repo size growth** | Vault notes accumulate over time | Notes are small (1-5 KB). vault-optimize archives stale notes. Monitor repo size quarterly. |
| **Broken wikilinks after archival** | vault-optimize moving notes to archives/ may break inbound wikilinks | vault-optimize must update or redirect wikilinks when archiving. vault-check Level 2 catches orphaned links. |
| **Stale BRIEFING.md** | BRIEFING.md could become outdated if not refreshed regularly | vault-optimize refreshes it. BRIEFING.md should be updated when active priorities change. |
| **Sub-skill architecture dependency** | Vault skills depend on FEAT-SKILL-030 sub-skill architecture | If 030 is not shipped, vault skills can be inlined. Plan for decomposition later. |
| **Concurrent write conflicts** | Multiple agents writing vault notes in the same cycle | Pull-rebase-push discipline. Append-only changelogs. Different files minimize conflicts. |
| **Incorrect knowledge propagation** | A wrong vault note could guide agents astray | Confidence field helps agents weigh information. PM reviews captures. Human can correct during check-ins. |
| **Existing upgrade flow** | `/squidsquad-upgrade` must handle vault creation without breaking existing installs | TC-57/TC-58 verify non-destructive upgrade. Vault is purely additive. |
| **MEMORY.md confusion** | Users may confuse Claude Code's MEMORY.md with vault | They are intentionally separate (per locked decision). Document the distinction in README.md. |

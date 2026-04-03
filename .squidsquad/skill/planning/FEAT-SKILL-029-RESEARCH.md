# FEAT-SKILL-029 Research -- Obsidian Memory Layer for Institutional Knowledge

## Summary

FEAT-SKILL-029 is the largest and most architecturally significant feature in SquidSquad's history. It introduces a git-tracked, Obsidian-compatible shared memory vault that gives all agents (PM, QA, Dev, Designer, DM) read/write access to institutional knowledge about the human, the company, and accumulated decisions. The vault follows the COG (Claude-Obsidian-Git) philosophy -- plain markdown, git-native, no infrastructure -- and uses an adapted IPARAG structure (Inbox, Projects, Areas, Resources, Archives, Galaxy).

The feature is feasible and architecturally sound. The primary complexity is not in any single skill but in the coordination layer: multiple agents writing to the same vault via git, per-role auto-remember triggers integrated into the Ralph Loop, and maintaining vault integrity as the knowledge graph grows. The vault is fundamentally an append-mostly system -- notes are created and updated, rarely deleted -- which aligns well with git's strengths and minimizes merge conflict risk.

The recommended implementation is four phases, each independently valuable:
- **Phase 1**: Vault init + IPARAG structure + templates + vault-create (minimum useful vault)
- **Phase 2**: vault-update + vault-search + vault-check (operational vault skills)
- **Phase 3**: vault-remember (proactive auto-capture across all roles)
- **Phase 4**: vault-optimize (full vault sweep, archive management, staleness detection)

The vault should be built as a set of common sub-skills under the FEAT-SKILL-030 architecture, composed into every agent template. All agents get the same vault skills; per-role behavior comes from role-specific trigger configuration in vault-remember, not from separate vault sub-skills per role.

**Recommendation: Proceed.** This is a platform need that becomes more critical as SquidSquad adds non-code roles (designer, DM). Code agents can infer conventions from the codebase itself, but style preferences, decision rationale, human values, and brand guidelines have no home today. The vault fills this gap.

---

## Impact Analysis

- **Files touched (implementation)**:
  - `references/sub-skills/common/vault-*.md` -- new common sub-skill files (one per vault skill)
  - `references/sub-skills/manifest.md` -- updated with vault sub-skill includes
  - All role entry files (`roles/dev-agent.md`, `roles/pm-agent.md`, `roles/pm-lean.md`, `roles/qa-agent.md`, `roles/designer.md`, `roles/dm-agent.md`) -- add vault sub-skill includes
  - `SKILL.md` -- vault-init instructions in setup flow, vault structure in file inventory
  - `.squidsquad/config.md` schema -- new vault config section
  - `.squidsquad/vault/` -- new directory tree (IPARAG structure)
  - Template files in `.squidsquad/templates/` -- regenerated with vault sub-skills composed in

- **Behavior changes**:
  - All agents gain vault read/write capability
  - PM gains inbox processing responsibility (new step in Ralph Loop)
  - All agents gain vault-remember triggers (new hook in Ralph Loop)
  - vault-check runs on every vault write (integrity validation)
  - Vault files are committed to git alongside tracker files

- **Dependencies**:
  - FEAT-SKILL-030 (sub-skill architecture) -- vault skills should be built as composable sub-skills. If 030 is not yet shipped, vault skills can be inlined into templates and decomposed later.
  - Git protocol (pull-before-write) -- already established, vault operations follow the same discipline
  - No external infrastructure -- COG philosophy means grep/ripgrep for search, file operations for CRUD

---

## 1. IPARAG Adaptation for Multi-Agent SquidSquad

### Folder-to-Domain Mapping

The IPARAG structure adapts to SquidSquad's multi-agent context as follows:

| IPARAG Folder | SquidSquad Purpose | Who Writes | Who Reads |
|---------------|-------------------|------------|-----------|
| `inbox/` | Unprocessed captures from any agent. Raw observations, quick notes, human statements that need classification. | All agents | PM (processor) |
| `projects/` | Active project context -- goals, constraints, architecture, tech stack, current milestone focus. One note per project or major initiative. | PM, Dev | All agents |
| `areas/` | Ongoing concerns that persist across projects. Human profile, company context, design system, code conventions, quality standards. These are the "living documents" that shape all agent behavior. | All agents (role-specific ownership) | All agents |
| `resources/` | Reference material -- external docs, API references, library guides, research notes from feature intake. Things agents look up but rarely modify. | PM, Dev, Designer | All agents |
| `archives/` | Completed work -- shipped features, closed decisions, old project contexts, historical planning artifacts. Moved here when no longer actively referenced. | PM (primary), All agents (via vault-optimize) | All agents (for historical context) |
| `galaxy/` | Atomic knowledge notes (Zettelkasten-style). Individual decisions, patterns, learnings, styles. Each note is one idea, densely linked via wikilinks. This is the heart of institutional knowledge. | All agents | All agents |

### What Goes in Each Folder

**inbox/**
- Raw captures from any agent: "Human said they prefer X", "Noticed pattern Y in code review", "This design decision should be recorded"
- Format: minimal -- just the observation, a source tag, and a timestamp
- Naming: `inbox/YYYY-MM-DD-HHMMSS-{agent}-{slug}.md` (timestamp ensures uniqueness even with concurrent writes)
- Lifecycle: processed within 1-3 PM cycles, moved to appropriate folder or deleted if noise

**projects/**
- `projects/squidsquad.md` -- the SquidSquad project itself (goals, architecture, tech stack)
- `projects/{project-name}.md` -- one per active project the squad works on
- Contains: goals, constraints, current milestone, tech stack, key stakeholders, active concerns
- Links to: area notes (design system, code conventions), galaxy notes (relevant decisions)

**areas/**
- `areas/human-profile.md` -- the human's preferences, values, communication style, decision patterns
- `areas/company-context.md` -- company culture, standards, brand guidelines, team norms
- `areas/design-system.md` -- colors, tokens, typography, component patterns, visual language
- `areas/code-conventions.md` -- style rules, architecture patterns, naming conventions, forbidden patterns
- `areas/quality-standards.md` -- test coverage expectations, review criteria, performance budgets
- `areas/documentation-standards.md` -- writing style, structure conventions, changelog format
- `areas/release-process.md` -- release cadence, versioning philosophy, deployment patterns
- These are long-lived documents that evolve over time. Each has an owner role but all agents can suggest updates via inbox captures.

**resources/**
- `resources/api-{name}.md` -- external API reference notes
- `resources/library-{name}.md` -- library usage patterns, gotchas, best practices
- `resources/research-{topic}.md` -- research findings from feature intake phases
- `resources/external-{name}.md` -- external documentation summaries relevant to the project
- Lower-churn than areas. Created during research phases, referenced during implementation.

**archives/**
- `archives/features/FEAT-XXX-{title}.md` -- shipped feature summaries (distilled from tracker + planning artifacts)
- `archives/decisions/decision-YYYY-MM-{slug}.md` -- closed decisions that were once in galaxy/
- `archives/projects/{project-name}.md` -- completed project contexts
- `archives/retrospectives/retro-YYYY-MM.md` -- periodic retrospectives (if implemented)
- Read-only in practice. Moved here by vault-optimize when a note's `updated` field is >90 days old and no inbound wikilinks from active notes exist.

**galaxy/**
- `galaxy/decision-{slug}.md` -- individual architectural, design, or process decisions
- `galaxy/pattern-{slug}.md` -- recurring patterns, conventions, established approaches
- `galaxy/learning-{slug}.md` -- lessons learned, bug root causes, what worked / what did not
- `galaxy/style-{slug}.md` -- visual style preferences, writing tone, code style choices
- `galaxy/preference-{slug}.md` -- human preferences that don't fit other categories
- Each note is atomic (one idea per note), densely linked. This is where the wikilink graph provides the most value.

### Inbox Processing: Ownership and Flow

**PM owns inbox processing.** This is the natural choice because:
1. PM already runs the coordination cycle and reads all agent trackers
2. PM has the broadest context across all agents
3. Distributed inbox processing (every agent processes their own captures) creates race conditions and duplicate classification
4. Single processor ensures consistent taxonomy and linking

**Inbox processing flow (new PM Ralph Loop step):**
1. Read all files in `vault/inbox/`
2. For each inbox note:
   a. Determine the appropriate destination folder (areas, galaxy, resources, or discard)
   b. If it maps to an existing note: append the new information via vault-update, delete the inbox note
   c. If it is a new topic: create a new note via vault-create in the appropriate folder, delete the inbox note
   d. If it is noise or already captured: delete the inbox note
   e. If classification is ambiguous: leave in inbox with a Discussion-style comment for next cycle
3. Log processing summary in iteration log

**Rate limiting for inbox processing:**
- Process at most 10 inbox notes per PM cycle to avoid context pressure
- If inbox has >20 unprocessed notes, log a warning (agents may be capturing too aggressively)
- Inbox notes older than 7 days without processing get auto-archived to `archives/inbox-overflow/`

**Concurrent capture safety:**
- Inbox note filenames include timestamp + agent name, so simultaneous captures never collide
- PM processes inbox sequentially -- no parallel processing of inbox notes
- If PM is processing an inbox note while another agent creates one, no conflict occurs (different files)

---

## 2. Entity Model Deep Dive

### Complete Entity List

| Entity Type | Location | Primary Writer(s) | Primary Reader(s) | Description |
|-------------|----------|-------------------|-------------------|-------------|
| Human profile | `areas/human-profile.md` | PM, vault-remember (all) | All agents | Preferences, values, communication style, decision patterns, working hours, response preferences |
| Company context | `areas/company-context.md` | PM | All agents | Culture, standards, brand guidelines, team structure, company values |
| Design system | `areas/design-system.md` | Designer, Dev | Designer, Dev, QA | Colors, tokens, typography, component library patterns, visual language |
| Code conventions | `areas/code-conventions.md` | Dev | Dev, QA, Designer | Style rules, architecture patterns, naming, imports, error handling patterns |
| Quality standards | `areas/quality-standards.md` | QA, PM | QA, Dev | Test coverage, review criteria, performance budgets, regression thresholds |
| Documentation standards | `areas/documentation-standards.md` | DM, PM | DM, Dev | Writing style, structure, changelog format, user guide conventions |
| Release process | `areas/release-process.md` | DM, PM | DM, PM | Versioning philosophy, release cadence, deployment patterns, rollback procedures |
| Project context | `projects/{name}.md` | PM, Dev | All agents | Goals, constraints, architecture, tech stack, milestone focus |
| Decisions | `galaxy/decision-*.md` | All agents | All agents | Individual arch/design/process decisions with rationale and context |
| Patterns | `galaxy/pattern-*.md` | Dev, Designer, QA | All agents | Recurring approaches, conventions, established solutions |
| Learnings | `galaxy/learning-*.md` | All agents | All agents | Lessons from bugs, failed approaches, what worked well |
| Styles | `galaxy/style-*.md` | Designer, Dev, PM | All agents | Visual preferences, writing tone, code style, brand voice |
| Preferences | `galaxy/preference-*.md` | PM (from human input) | All agents | Human preferences that don't fit other categories |

### Per-Role Knowledge Needs

**PM needs to read:**
- Human profile (communication style, decision patterns, priority preferences)
- Company context (brand guidelines, culture for feature scoping)
- All galaxy/decision-* (to avoid re-litigating settled decisions)
- All galaxy/pattern-* (to predict human reactions during feature intake)
- Project context (to maintain roadmap coherence)

**PM needs to write:**
- Human profile updates (from check-in conversations)
- Company context updates (from human discussions)
- Decision notes (from feature intake Phase 2 discussions)
- Preference notes (from expressed human preferences)
- Inbox processing results (classification + routing)

**QA needs to read:**
- Quality standards (test coverage expectations, performance budgets)
- Code conventions (to verify implementation follows patterns)
- Galaxy/pattern-* (to know what "correct" looks like)
- Galaxy/learning-* (to watch for regression of known issues)
- Design system (to verify visual implementation matches specs)

**QA needs to write:**
- Quality standards updates (as test patterns evolve)
- Learning notes (from bug investigations -- root causes, common failure modes)
- Pattern notes (recurring test patterns, verification approaches)

**Designer needs to read:**
- Design system (existing tokens, components, visual language)
- Human profile (aesthetic preferences, visual style preferences)
- Company context (brand guidelines, brand colors, tone)
- Galaxy/style-* (accumulated style decisions)
- Galaxy/decision-* (decisions constraining design choices)

**Designer needs to write:**
- Design system updates (new tokens, component patterns)
- Style notes (visual preferences confirmed during design sessions)
- Decision notes (design decisions with visual rationale)
- Pattern notes (UI patterns, interaction patterns)

**Dev needs to read:**
- Code conventions (style, architecture, naming)
- Project context (tech stack, constraints)
- Galaxy/decision-* (architecture decisions)
- Galaxy/pattern-* (established implementation patterns)
- Design system (when implementing UI features)

**Dev needs to write:**
- Code convention updates (as patterns evolve from implementation)
- Pattern notes (new implementation patterns discovered)
- Learning notes (debugging insights, what worked/failed)
- Decision notes (architecture decisions made during implementation)

**DM needs to read:**
- Documentation standards (writing style, structure)
- Release process (versioning, changelog format)
- Human profile (communication style for user-facing content)
- Company context (brand voice for user-facing materials)
- Galaxy/decision-* (decisions affecting release notes)

**DM needs to write:**
- Documentation standards updates (as conventions evolve)
- Release process updates (new deployment patterns)
- Learning notes (delivery pipeline insights)

### Shared vs Role-Specific Entities

**Shared (all agents read):**
- Human profile, company context, project context
- All galaxy/ notes (decisions, patterns, learnings, styles, preferences)

**Role-specific primary ownership (one role writes, all read):**
- Design system: Designer primary writer, Dev/QA readers
- Code conventions: Dev primary writer, QA/Designer readers
- Quality standards: QA primary writer, Dev/PM readers
- Documentation standards: DM primary writer, Dev readers
- Release process: DM primary writer, PM reader

No entity is truly "only for one role" -- the vault is a shared graph, and any agent may need to reference any note. Ownership determines who is responsible for keeping the note current, not who is allowed to read it.

### Template Design for Each Entity Type

**Common frontmatter (all vault notes):**

```yaml
---
type: [area | project | resource | decision | pattern | learning | style | preference | archive]
tags: [list of tags for grep-based filtering]
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: [pm | qa | dev | designer | dm | shared]
status: [active | stale | archived]
links: [list of related note filenames for quick traversal]
---
```

**Area note template (areas/):**

```markdown
---
type: area
tags: [domain-specific tags]
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: [role]
status: active
links: []
---

# [Area Name]

## Summary
[One-paragraph overview of this area]

## Current State
[What is currently established/agreed]

## Key Points
- [Point 1]
- [Point 2]

## Related
- [[note-name-1]]
- [[note-name-2]]

## Changelog
- [YYYY-MM-DD] Created by [agent]. [reason]
```

**Galaxy note template (galaxy/):**

```markdown
---
type: [decision | pattern | learning | style | preference]
tags: [topic tags]
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: [role]
status: active
source: [what prompted this note -- feature ID, human conversation, bug investigation, etc.]
links: []
---

# [Title]

## Context
[Why this note exists -- what situation prompted it]

## Content
[The actual knowledge -- the decision, the pattern, the learning]

## Rationale
[Why this choice was made, or why this pattern works]

## Related
- [[note-name-1]]
- [[note-name-2]]

## Changelog
- [YYYY-MM-DD] Created by [agent]. [reason]
```

**Project note template (projects/):**

```markdown
---
type: project
tags: [project-name, tech-stack tags]
created: YYYY-MM-DD
updated: YYYY-MM-DD
owner: pm
status: active
links: []
---

# [Project Name]

## Goals
- [Goal 1]
- [Goal 2]

## Constraints
- [Constraint 1]
- [Constraint 2]

## Tech Stack
- [Stack details]

## Architecture
[High-level architecture notes]

## Current Focus
[Current milestone or priority]

## Related
- [[code-conventions]]
- [[design-system]]

## Changelog
- [YYYY-MM-DD] Created by [agent]. [reason]
```

**Inbox note template (inbox/):**

```markdown
---
type: inbox
tags: []
created: YYYY-MM-DD
source-agent: [agent role]
source-context: [feature ID, conversation, observation, etc.]
---

# [Brief description]

[Raw observation or captured knowledge]
```

Inbox notes are intentionally minimal -- they exist to capture quickly and be processed later.

---

## 3. Multi-Agent Concurrency

### Git Merge Conflicts in Vault Files

**Conflict likelihood: Low.** The vault is designed to minimize conflicts:

1. **Different files**: Most vault operations create new notes or update different notes. Two agents updating the same note simultaneously is rare.
2. **Append-only changelogs**: The changelog section at the bottom of each note is append-only. Git handles concurrent appends to different lines without conflict.
3. **Frontmatter updates**: If two agents update the same note's frontmatter (e.g., both update `updated: YYYY-MM-DD`), git will flag a conflict. This is the highest-risk scenario.
4. **Inbox notes**: Never conflict because filenames include timestamp + agent name.

**Conflict scenarios and resolutions:**

| Scenario | Likelihood | Resolution |
|----------|------------|------------|
| Two agents create inbox notes simultaneously | None (unique filenames) | N/A |
| Two agents update the same area note | Low (role ownership) | git rebase resolves most; keep-both for changelog entries |
| Two agents create the same galaxy note | Very low (slug uniqueness) | If slug collides, second agent gets a rebase conflict; rename with suffix |
| PM processes inbox while agent writes to inbox | None (different files) | N/A |
| Frontmatter `updated` field collision | Low but possible | Last-write-wins is acceptable for timestamp fields |

**Resolution strategy:**
- Follow the existing SquidSquad git protocol: `git pull --rebase` before every write
- For vault files, the existing conflict resolution rule applies: "keep both versions -- append the conflicting section below the existing one"
- Vault-check (Level 1) runs after every write to detect inconsistencies introduced by merge resolution

### File Locking

**No file locking.** Git handles concurrency. Locking would require infrastructure (lock server, distributed locks) that violates the COG philosophy. The pull-rebase-push cycle is sufficient:

1. Agent pulls latest vault state
2. Agent writes/updates vault note
3. Agent commits and pushes
4. If push fails (another agent pushed first): pull --rebase, resolve any conflicts, push again

This is the same discipline SquidSquad already uses for tracker files. Vault files are no different.

### Simultaneous Note Creation

If two agents independently decide to create a note about the same topic (e.g., both notice a pattern and create `galaxy/pattern-error-handling.md`):

1. First agent to push succeeds
2. Second agent's `git pull --rebase` fails with a file-exists conflict
3. Resolution: second agent renames their file with a disambiguating suffix (e.g., `galaxy/pattern-error-handling-from-qa.md`)
4. On next PM inbox processing cycle, PM detects the near-duplicate and merges them into one note, preserving content from both

**Prevention**: vault-create should check if a similar-named note exists before creating. A simple `ls vault/galaxy/pattern-error-handling*` check prevents most collisions. This is not foolproof (race condition window between check and commit) but reduces the common case.

### Append-Only vs Full-Rewrite Patterns

| Pattern | Used For | Conflict Risk |
|---------|----------|---------------|
| **Append-only** | Changelog sections, inbox notes, Discussion entries | Very low -- git auto-merges concurrent appends to different lines |
| **Section update** | Updating "Current State" in an area note, adding a key point | Low -- agents typically update different sections |
| **Frontmatter update** | Updating `updated`, `status`, `tags` fields | Medium -- two agents updating the same frontmatter field creates a conflict |
| **Full rewrite** | Not recommended for vault notes | High -- avoided by design |

**Design principle**: Vault notes should be structured to maximize append-only patterns and minimize full-rewrite patterns. The changelog at the bottom of every note is always append-only. Content sections should be additive (add new points, do not rewrite existing ones). If a correction is needed, add a new changelog entry and update the specific section.

### Pull-Before-Write Discipline

Already established in SquidSquad. Every Ralph Loop cycle starts with `git pull --rebase` (Step 1). Vault writes happen during the cycle, committed at cycle end (Step 5/8/9). This provides a natural transaction boundary:

1. Cycle start: pull latest vault state
2. Mid-cycle: read vault, make decisions, write vault notes
3. Cycle end: commit all vault changes, push

The risk window is between pull and push -- another agent may have pushed vault changes in the interim. The push may require another pull --rebase. This is handled by the existing commit/push flow.

---

## 4. Vault-Remember: Per-Role Triggers

### Trigger Definitions by Role

**PM triggers:**
- Human states a preference during check-in ("I prefer X over Y") -> capture as `galaxy/preference-*.md` or update `areas/human-profile.md`
- Decision made during feature discussion (Phase 2) -> capture as `galaxy/decision-*.md`
- Priority change expressed by human -> update `areas/human-profile.md` priorities section
- Feature pattern observed (human frequently requests similar features) -> capture as `galaxy/pattern-*.md`
- Human expresses satisfaction or dissatisfaction with a process -> capture as `galaxy/preference-*.md`

**QA triggers:**
- Test pattern discovered during verification -> capture as `galaxy/pattern-*.md`
- Common failure mode identified (same root cause across multiple bugs) -> capture as `galaxy/learning-*.md`
- Regression risk identified (area of code that breaks frequently) -> capture as `galaxy/learning-*.md`
- Quality standard clarified by human or PM -> update `areas/quality-standards.md`
- New verification approach proved effective -> capture as `galaxy/pattern-*.md`

**Designer triggers:**
- Style preference confirmed by human during design session -> capture as `galaxy/style-*.md`
- Design system evolution (new token, new component pattern) -> update `areas/design-system.md`
- Visual pattern established (consistent layout approach, color usage) -> capture as `galaxy/pattern-*.md`
- Brand guideline clarified -> update `areas/company-context.md`
- Human rejects a design direction (negative signal is knowledge too) -> capture as `galaxy/preference-*.md` with explicit "avoid" framing

**Dev triggers:**
- Architecture decision made during implementation -> capture as `galaxy/decision-*.md`
- Code pattern established (new utility, new abstraction) -> capture as `galaxy/pattern-*.md`
- Implementation learning (gotcha, non-obvious behavior, library quirk) -> capture as `galaxy/learning-*.md`
- Code convention evolved (new naming pattern, new file organization approach) -> update `areas/code-conventions.md`
- Performance insight ("this approach is 10x faster") -> capture as `galaxy/learning-*.md`

**DM triggers:**
- Documentation convention established -> update `areas/documentation-standards.md`
- Release pattern observed (certain types of changes need special release notes) -> capture as `galaxy/pattern-*.md`
- Changelog style preference clarified by human -> capture as `galaxy/style-*.md`
- User-facing terminology established ("we call this X, not Y") -> capture as `galaxy/decision-*.md`

### Ralph Loop Integration

Vault-remember should be a **new sub-step at the end of the work phase**, not a separate step. It runs as part of the agent's existing work, not as additional overhead.

**Proposed integration point for each role:**

- **Dev**: After Step 3 (Implement Features) and Step 2 (Triage Bugs), before Step 4 (Log Iteration). After completing a bug fix or feature implementation, the agent scans its own work for capture-worthy knowledge.
- **PM**: After Step 2 (Check In With Human), after Step 6 (Verify Features), and during inbox processing. Human interactions are the richest source of captures.
- **QA**: After Step 5 (Verify Fixed Bugs) and Step 6 (Verify Pending Test Features). Verification work reveals patterns and learnings.
- **Designer**: After Step 2 (Design Session). Design sessions with the human produce style decisions, design system evolution, and preference captures.
- **DM**: After Step 2 (Delivery Packaging). Delivery work clarifies documentation conventions and release patterns.

**Implementation approach:**

Rather than adding a full new step to the Ralph Loop, vault-remember is a **hook** that fires after significant work is completed. The hook is a sub-skill instruction block that says:

```
After completing [work type], check if any of the following were observed:
- [role-specific trigger list]
If yes, create an inbox capture note with the observation.
Do not interrupt the current task to process the capture -- just write to inbox/ and continue.
```

This keeps vault-remember lightweight. The heavy lifting (classification, linking, merging) happens during PM's inbox processing.

### Rate Limiting

**Problem**: Agents could flood the inbox with low-value captures, creating noise that buries signal.

**Rate limiting strategy:**

1. **Per-cycle cap**: Each agent creates at most 3 inbox captures per cycle. If more triggers fire, the agent picks the 3 most significant (based on a simple heuristic: decisions > preferences > patterns > learnings).
2. **Deduplication check**: Before creating an inbox capture, the agent does a quick `grep` of the vault for the key terms. If a substantially similar note already exists, skip the capture and optionally update the existing note's changelog instead.
3. **Cooldown per topic**: After capturing a note on topic X, the agent will not capture another note on the same topic for 3 cycles (roughly 90 minutes at default 30-minute intervals). This prevents "preference churn" where the same preference is re-captured every cycle.
4. **PM-side filtering**: During inbox processing, PM discards captures that are too vague, already known, or noise. This is the final quality gate.
5. **Configurable aggressiveness**: A `Vault Remember: aggressive / balanced / conservative` setting in config.md controls the trigger sensitivity. Default is `balanced` (capture decisions and explicit preferences only). `Aggressive` captures patterns and learnings too. `Conservative` captures only explicit human decisions.

---

## 5. Skill Design (7 Vault Skills)

### Sub-skill vs Slash Command Decision

The vault skills should be **common sub-skills** composed into every agent template, not slash commands. Rationale:

1. **Agents need vault skills during autonomous operation.** Slash commands require explicit invocation; sub-skills are available as part of the agent's instruction set.
2. **vault-remember must fire automatically** -- it cannot be a slash command because no one invokes it manually.
3. **vault-check must fire automatically** on every vault write -- same reasoning.
4. **vault-search must be available inline** when agents are doing their work, not as a separate command.

Two exceptions that could also be slash commands (for human use):
- `/vault-init` -- run once during setup (this is naturally a setup instruction in SKILL.md, not a sub-skill)
- `/vault-optimize` -- run on demand by PM or human (could be both a sub-skill step and a slash command)

### Skill-by-Skill Design

**vault-init** (setup-time, not a sub-skill)
- Lives in: SKILL.md setup instructions (new step in setup flow)
- Purpose: Create the vault directory structure, write templates, seed initial notes
- Creates: `.squidsquad/vault/inbox/`, `projects/`, `areas/`, `resources/`, `archives/`, `galaxy/`
- Creates: Template files in each folder (`.template.md`)
- Creates: Initial area notes from existing config (human profile seeded from project name, code conventions seeded from tech stack)
- Creates: `.obsidian/` directory with graph config (gitignored except essential settings)
- Runs once during `/squidsquad-setup`, and idempotently during `/squidsquad-upgrade`

**vault-create** (common sub-skill)
- File: `references/sub-skills/common/vault-create.md`
- Purpose: Create a new vault note from the appropriate template
- Input: note type, title, content, tags, owner
- Process:
  1. Determine destination folder from note type
  2. Generate filename slug from title (lowercase, hyphens, no special chars)
  3. Check for existing note with same slug (prevent duplicates)
  4. Read template for the destination folder
  5. Fill template with provided content
  6. Write file
  7. Run vault-check Level 1 on the new note
  8. Append to new note's changelog
- Output: Path to created note

**vault-update** (common sub-skill)
- File: `references/sub-skills/common/vault-update.md`
- Purpose: Update an existing vault note (content, frontmatter, or both)
- Input: note path, sections to update, changelog entry
- Process:
  1. Read existing note
  2. Update specified sections (preserve sections not being updated)
  3. Update frontmatter `updated` field
  4. Append changelog entry
  5. Run vault-check Level 1 on the updated note
  6. Validate wikilinks in updated content resolve to existing notes
- Output: Updated note path
- Key constraint: Never delete existing content -- only add, modify, or mark as superseded

**vault-search** (common sub-skill)
- File: `references/sub-skills/common/vault-search.md`
- Purpose: Find relevant vault notes using grep-based search and wikilink traversal
- Modes:
  - **Tag search**: `grep -r "tags:.*{tag}" vault/` -- find notes with specific tags
  - **Frontmatter search**: `grep -r "type: decision" vault/` -- find notes by type
  - **Content search**: `grep -rl "{keyword}" vault/` -- full-text keyword search
  - **Wikilink traversal**: Given a starting note, follow `[[wikilinks]]` to discover connected notes (1-hop or 2-hop)
  - **Combined**: Search by keyword, then traverse wikilinks from results for context enrichment
- Output: List of matching note paths with relevant excerpts
- Limit: Return at most 10 results per search to prevent context pressure. Agent can narrow and re-search if needed.

**vault-check** (common sub-skill)
- File: `references/sub-skills/common/vault-check.md`
- Purpose: Validate vault note integrity
- **Level 1** (per-note + 2-hop neighborhood, runs on every write):
  1. Validate frontmatter has all required fields
  2. Validate `type` field matches the note's folder location
  3. Validate all `[[wikilinks]]` in the note resolve to existing files
  4. Validate all notes that link TO this note still have valid reciprocal references
  5. Check `updated` field is current (within today)
  6. Check changelog has at least one entry
- **Level 2** (full vault sweep, runs on demand):
  1. Run Level 1 on every note in the vault
  2. Detect orphan notes (no inbound wikilinks, not an area note)
  3. Detect stale notes (`updated` > 30 days for active status)
  4. Detect broken wikilinks across the entire graph
  5. Report vault health summary (total notes, orphans, stale, broken links)
- Output: List of issues found (or clean bill of health)

**vault-optimize** (common sub-skill, also available as slash command)
- File: `references/sub-skills/common/vault-optimize.md`
- Purpose: Full vault maintenance sweep
- Actions:
  1. Run vault-check Level 2
  2. Archive stale notes (move to archives/ with status change)
  3. Merge near-duplicate galaxy notes (same topic, different angles -- merge content, redirect wikilinks)
  4. Suggest tag normalization (detect inconsistent tagging)
  5. Report vault size metrics (note count per folder, total size, growth rate)
- Trigger: Runs as part of PM's cycle every N cycles (configurable, default every 10 cycles = ~5 hours), or on demand via `/vault-optimize`

**vault-remember** (common sub-skill with role-specific trigger config)
- File: `references/sub-skills/common/vault-remember.md`
- Purpose: Auto-detect noteworthy context during agent work and create inbox captures
- Implementation: Not a standalone step -- a set of trigger conditions checked after significant work actions
- Role-specific triggers: Defined in the sub-skill file as a lookup table by role
- Process:
  1. After completing a work action, check trigger conditions for the current role
  2. If a trigger fires, compose a minimal inbox capture note
  3. Write to `vault/inbox/YYYY-MM-DD-HHMMSS-{role}-{slug}.md`
  4. Continue main work (do not process the capture -- PM handles that)
- Rate limiting: 3 captures per cycle max, dedup check, topic cooldown (see Section 4)

### Sub-skill Architecture Integration

All vault sub-skills are **common sub-skills** (under `references/sub-skills/common/`) included in every agent template. The composition manifest adds them after the existing common sub-skills:

```
Common sub-skills (existing):
  pull-latest, context-pressure, resume-working-state, interval-sync, working-state

Common sub-skills (new, vault):
  vault-create, vault-update, vault-search, vault-check, vault-optimize, vault-remember
```

Each role's entry file includes the vault sub-skills via `{{include: common/vault-create}}` etc. The vault-remember sub-skill contains a role-specific trigger table, so the composed template includes all triggers but the agent only fires the triggers for its own role.

This approach means:
- One set of vault sub-skill files (not per-role duplicates)
- All agents have the same vault capabilities
- Role-specific behavior comes from the trigger configuration, not separate sub-skills
- Adding vault capabilities to a new role requires only adding the role's triggers to vault-remember

---

## 6. Wikilink Traversal and Search

### How Agents Search the Vault

Agents search the vault using file operations (grep/ripgrep) -- the COG approach. No database, no index, no server.

**Search patterns:**

```bash
# Find notes by tag
grep -rl "tags:.*architecture" .squidsquad/vault/

# Find notes by type
grep -rl "^type: decision" .squidsquad/vault/galaxy/

# Full-text keyword search
grep -rl "error handling" .squidsquad/vault/

# Find notes linking to a specific note
grep -rl "\[\[code-conventions\]\]" .squidsquad/vault/

# Find notes by owner
grep -rl "^owner: dev" .squidsquad/vault/

# Find stale notes
grep -rl "^status: active" .squidsquad/vault/ | xargs grep -l "^updated: 2026-02"
```

### Multi-Hop Wikilink Traversal

**1-hop traversal**: Given note A, find all notes that A links to (`[[B]]`) and all notes that link to A. This is a simple grep:

```bash
# Outbound links from note A
grep -oP '\[\[([^\]]+)\]\]' vault/galaxy/decision-error-handling.md
# → [[code-conventions]], [[pattern-try-catch]]

# Inbound links to note A
grep -rl "\[\[decision-error-handling\]\]" vault/
# → vault/areas/code-conventions.md, vault/galaxy/learning-null-checks.md
```

**2-hop traversal**: From note A, find all 1-hop neighbors, then find all 1-hop neighbors of those neighbors. This builds the "neighborhood" of a note:

```bash
# Step 1: Get A's direct links
links=$(grep -oP '\[\[([^\]]+)\]\]' vault/galaxy/decision-error-handling.md | tr -d '[]')
# Step 2: For each linked note, get its links
for link in $links; do
  grep -oP '\[\[([^\]]+)\]\]' vault/**/$link.md
done
```

**Practical limits**: 2-hop is sufficient for most use cases. Beyond 2 hops, the result set becomes too large and noisy. A note with 5 outbound links at 1-hop, each with 5 outbound links, yields 25 notes at 2-hop. At 3-hop that is 125 notes -- too many to be useful in a context window.

**Performance**: For a vault of 100-500 notes, grep is near-instant. For 1000+ notes, grep is still fast (ripgrep handles millions of files efficiently). The vault would need to reach tens of thousands of notes before grep performance becomes a concern -- at which point FEAT-SKILL-062 (OpenSearch) becomes relevant.

### Context Discovery at Cycle Start

**Should agents automatically search the vault at cycle start?**

No -- not by default. Reasons:
1. Context pressure: Reading vault notes at every cycle start wastes context window on potentially irrelevant information
2. Most cycles are routine (bug fixes, feature work) where the relevant vault context is specific to the task at hand

**Instead, agents should search the vault contextually:**
- When starting a new feature: search for related decisions, patterns, and the project context note
- When encountering an ambiguous design choice: search for relevant style and preference notes
- When investigating a bug: search for related learnings and patterns
- When writing user-facing content: search for human profile, company context, documentation standards

This "search when needed" approach is explicitly documented in the vault-search sub-skill instructions. The sub-skill includes example queries for each role's common lookup patterns.

**Exception**: PM's inbox processing step reads the vault inbox every cycle. This is the only automatic vault read.

---

## 7. Vault Location and Structure

### Location Decision: `.squidsquad/vault/`

**Recommended: `.squidsquad/vault/`**

| Option | Pros | Cons |
|--------|------|------|
| `.squidsquad/vault/` | Co-located with all SquidSquad data; self-contained install; clear ownership; no top-level clutter | Nested path (`.squidsquad/vault/galaxy/decision-*.md` is deep); Obsidian needs to be pointed at this subdirectory |
| Top-level `vault/` | Short paths; easy Obsidian integration; visible in repo root | Clutters repo root; might conflict with user's own directories; unclear ownership; not obviously part of SquidSquad |
| `.obsidian-memory/` | Clearly signals Obsidian compatibility; distinctive name | Non-standard; hidden directory that isn't actually Obsidian config; confusing name |

`.squidsquad/vault/` wins because:
1. All SquidSquad artifacts live under `.squidsquad/` -- the vault is no exception
2. Clear ownership and cleanup path (delete `.squidsquad/` removes everything)
3. The path depth is a minor cost -- agents work with absolute paths anyway
4. Obsidian can open any directory as a vault; the nesting is not a problem

### Obsidian App Interaction

The vault is designed to be browsable in Obsidian for graph visualization and manual exploration:

**`.obsidian/` config directory:**
- Created during vault-init at `.squidsquad/vault/.obsidian/`
- Contains minimal config: graph settings, appearance, enabled core plugins
- **Gitignored** except for a seed config file (`.squidsquad/vault/.obsidian/app.json` or similar)
- Rationale for gitignoring: Obsidian writes workspace state, plugin caches, and user preferences to `.obsidian/`. These are machine-specific and noisy in git diffs. Only the initial seed config is committed.

**.gitignore additions:**
```
.squidsquad/vault/.obsidian/*
!.squidsquad/vault/.obsidian/app.json
!.squidsquad/vault/.obsidian/graph.json
```

**What users can do in Obsidian:**
- Open `.squidsquad/vault/` as an Obsidian vault
- Browse the graph view to see relationships between notes
- Read notes with rendered wikilinks and backlinks
- Search across the vault using Obsidian's search
- **They should NOT edit vault notes directly in Obsidian** -- agents expect specific formats and will overwrite manual edits on next vault-update. Add a `README.md` in the vault root: "This vault is managed by SquidSquad agents. Edit via Discussion entries or human check-in, not directly."

### Size Management

**What happens when the vault grows to thousands of notes?**

1. **Git performance**: Git handles thousands of small markdown files well. Each note is typically 1-5 KB. Even 10,000 notes = ~50 MB of text, which is trivial for git. The concern is not storage but diff/log performance on frequent commits -- also fine because commits typically touch 1-5 vault files, not thousands.

2. **Grep search performance**: Ripgrep searches thousands of files in milliseconds. Performance is not a concern until tens of thousands of notes.

3. **Context window pressure**: The risk is not vault size but how much vault content an agent reads into context. The vault-search sub-skill limits results to 10 per query, and agents read only the notes they need. Vault size does not automatically create context pressure.

4. **Archive rotation**: vault-optimize moves stale notes to `archives/`. This keeps the "active" vault (inbox, projects, areas, galaxy) lean. Archives are still searchable but not routinely read.

5. **Scaling thresholds:**
   - 0-500 notes: No concerns. Grep is instant. Git is fast. Vault-check Level 2 completes in seconds.
   - 500-2000 notes: Vault-check Level 2 takes longer (10-30 seconds). Consider running it less frequently. Grep still fast.
   - 2000-10000 notes: Vault-check Level 2 may take minutes. Consider FEAT-SKILL-062 (semantic search) for better retrieval. Archive aggressively.
   - 10000+: This is unusual and suggests the vault is not being properly maintained. vault-optimize should catch this and warn.

---

## 8. Phased Implementation

### Phase 1: Vault Init + Structure + Templates + vault-create (Minimum Useful Vault)

**Deliverables:**
- IPARAG directory structure under `.squidsquad/vault/`
- Templates for each folder (area, project, resource, galaxy, inbox, archive)
- vault-init as part of setup flow (creates structure, seeds initial notes)
- vault-create sub-skill (create notes from templates)
- vault-check Level 1 (basic note validation)
- Initial area notes seeded from existing config (human profile stub, code conventions stub, project context)
- .obsidian/ seed config
- .gitignore updates

**Value**: Agents can start creating vault notes. The structure exists and is browsable in Obsidian. No auto-capture yet -- agents manually create notes when appropriate.

**Estimated effort**: 1-2 dev cycles

**Dependencies**: None (can be built before FEAT-SKILL-030 sub-skills and migrated later)

### Phase 2: vault-update + vault-search + vault-check L2 (Operational Vault)

**Deliverables:**
- vault-update sub-skill (update existing notes with changelog)
- vault-search sub-skill (grep-based search + wikilink traversal)
- vault-check Level 2 (full vault sweep)
- PM inbox processing step (new Ralph Loop sub-step)
- All agents can search and update the vault

**Value**: The vault becomes a living system. Agents can search for relevant context, update existing knowledge, and PM processes incoming captures.

**Estimated effort**: 2-3 dev cycles

**Dependencies**: Phase 1

### Phase 3: vault-remember (Proactive Auto-Capture)

**Deliverables:**
- vault-remember sub-skill with per-role trigger tables
- Ralph Loop integration (hook after work steps)
- Rate limiting and deduplication logic
- Config option for capture aggressiveness (aggressive / balanced / conservative)

**Value**: Agents proactively capture knowledge without being asked. The vault grows organically from normal squad operation. This is the "magic" phase -- the squad starts learning about the human.

**Estimated effort**: 2-3 dev cycles

**Dependencies**: Phase 2 (agents need inbox for captures, PM needs inbox processing)

### Phase 4: vault-optimize (Full Vault Health)

**Deliverables:**
- vault-optimize sub-skill (full sweep, archive rotation, near-duplicate detection, tag normalization)
- PM periodic optimization schedule (every N cycles)
- `/vault-optimize` slash command for manual invocation
- Vault health reporting in PM iteration logs
- Staleness detection and auto-archival

**Value**: The vault is self-maintaining. Stale knowledge is archived, duplicates are merged, and the vault stays lean and accurate over time.

**Estimated effort**: 1-2 dev cycles

**Dependencies**: Phase 3 (vault needs to have enough content to optimize)

### Dependency Map

```
Phase 1 (Init)
    |
    v
Phase 2 (CRUD + Search)
    |
    v
Phase 3 (Auto-Remember)
    |
    v
Phase 4 (Optimize)
```

Strictly sequential. Each phase builds on the previous. However, Phase 1 alone is useful (manual note creation), Phase 1+2 is significantly useful (searchable vault), and Phase 1+2+3 is the target state for most installs.

---

## 9. Side Effects and Edge Cases

### Side Effects

- **Risk 1**: Vault files in git increase repo size over time -- Severity: **L** -- Mitigation: Vault notes are small text files (1-5 KB each). Even 1000 notes = ~5 MB. Git compresses text efficiently. The repo size concern is theoretical at SquidSquad's scale. If it becomes an issue, vault-optimize can prune the archives directory (git history preserves deleted notes).

- **Risk 2**: Agents referencing stale vault notes -- Severity: **M** -- Mitigation: vault-check Level 1 validates the `updated` field. vault-optimize detects notes with `updated` > 30 days and moves them to archives. Agents should check the `updated` and `status` fields when reading vault notes and treat stale/archived notes as historical context, not current guidance.

- **Risk 3**: Incorrect vault notes propagating bad guidance -- Severity: **H** -- Mitigation: Multiple layers:
  1. Vault notes have an `owner` field -- the owning role is responsible for accuracy
  2. PM reviews all inbox captures during processing (quality gate)
  3. Human can correct notes during check-in ("That preference is wrong, I actually prefer X")
  4. vault-update preserves history via changelog -- incorrect info can be corrected and the correction tracked
  5. Agents should treat vault notes as guidance, not absolute rules. When vault knowledge conflicts with explicit human input, human input wins.

- **Risk 4**: Vault-remember creates noise that overwhelms signal -- Severity: **M** -- Mitigation: Rate limiting (3 captures per cycle), deduplication check, topic cooldown, configurable aggressiveness, PM as quality gate. Start with `conservative` setting and let the human increase aggressiveness when ready.

- **Risk 5**: Ralph Loop cycle time increases from vault operations -- Severity: **M** -- Mitigation: vault-remember is lightweight (write an inbox note, ~1 second). vault-search is fast (grep, ~100ms). vault-check Level 1 is fast (~500ms per note). The main cost is PM's inbox processing, which is capped at 10 notes per cycle. Total vault overhead per cycle should be <5 seconds for non-PM agents and <30 seconds for PM.

- **Risk 6**: Vault notes create cross-agent coupling -- Severity: **L** -- Mitigation: The vault is intentionally shared. Cross-agent reads are read-only (agents never modify other agents' notes, they create inbox captures instead). The inbox/processing pattern creates a single bottleneck (PM) but also a single quality gate.

### Edge Cases

- **Empty vault on first cycles**: After vault-init, the vault has only seed notes. vault-search returns few results. vault-remember has nothing to deduplicate against. This is fine -- the vault bootstraps organically. No special handling needed.

- **PM is absent (no inbox processing)**: Inbox captures accumulate without processing. Auto-archive after 7 days prevents unbounded growth. When PM restarts, it processes the backlog (capped at 10 per cycle). The vault still functions for read/write even without PM -- inbox processing is a maintenance task, not a blocking dependency.

- **Human edits vault files directly in Obsidian**: The next agent to touch that note may overwrite the changes if it does a full section rewrite. Mitigation: vault-update preserves sections it does not modify. The README in the vault root warns against direct editing. If the human does edit directly, the change persists until an agent rewrites that section. Git history preserves the human's version.

- **Cross-project vaults**: Can the vault pattern work across repos? Yes, with caveats. The vault is under `.squidsquad/vault/` which is repo-specific. For cross-project knowledge, two approaches:
  1. **Shared vault repo**: A separate git repo containing only the vault, symlinked from each project's `.squidsquad/vault/`. Complex but enables true cross-project knowledge.
  2. **Copy-on-setup**: During `/squidsquad-setup` for a new project, optionally copy area notes (human-profile, company-context) from another project's vault. One-time seed, not ongoing sync.
  3. **CLAUDE.md project memory**: The existing `~/.claude/projects/` memory files serve a similar cross-project role. The vault is complementary (richer, more structured) but not a replacement.
  Recommendation: Start with per-repo vaults. Cross-project vaults are a future enhancement (could be FEAT-SKILL-065 or similar).

- **`/squidsquad-upgrade` with vault data**: Upgrade must be vault-aware:
  1. If vault exists: preserve all vault content (never delete/overwrite existing notes)
  2. If vault does not exist: create it (vault-init)
  3. If vault structure is outdated (missing folders): add missing folders without touching existing content
  4. If vault templates changed: update templates but do not re-seed notes that already exist
  5. vault-check Level 2 runs after upgrade to validate vault health

- **Agent creates note with invalid wikilinks**: vault-check Level 1 catches this on write. The agent should fix the wikilinks (remove or create the target note) before committing. If the agent cannot fix it (target note is in another agent's domain), it creates an inbox capture flagging the broken link.

- **Vault note naming collision**: Two notes with the same slug but different types (e.g., `galaxy/decision-auth-flow.md` and `galaxy/pattern-auth-flow.md`). This is fine -- the type prefix in the filename disambiguates. Wikilinks use the full filename without path: `[[decision-auth-flow]]` vs `[[pattern-auth-flow]]`. If two notes have identical filenames in different folders (e.g., `areas/auth.md` and `resources/auth.md`), wikilinks are ambiguous. vault-check should warn on duplicate filenames across folders. Mitigation: encourage descriptive slugs and use type prefixes in galaxy/ names.

---

## 10. Upgrade and Migration

### Fresh Install (vault created during setup)

During `/squidsquad-setup`, a new step runs vault-init:

1. Create `.squidsquad/vault/` directory structure (all IPARAG folders)
2. Write template files to each folder
3. Seed initial area notes:
   - `areas/human-profile.md` -- stub with project name, populated from setup questions
   - `areas/code-conventions.md` -- stub seeded from tech stack info in config.md
   - `projects/{project-name}.md` -- seeded from project name and tech stack
4. Create `.obsidian/` seed config
5. Add vault entries to `.gitignore`
6. Commit vault structure

### Existing Install (vault added via upgrade)

During `/squidsquad-upgrade`:

1. Detect if `.squidsquad/vault/` exists
2. If not: run vault-init (same as fresh install)
3. If yes but missing folders: create missing folders (non-destructive)
4. If yes and complete: update templates only (do not modify existing notes)
5. Run vault-check Level 2 after upgrade
6. Add vault sub-skills to agent templates (regenerate from sub-skill sources)

### Seeding Initial Knowledge from Existing Data

The vault can be seeded from existing SquidSquad artifacts:

1. **From config.md**: Project name, tech stack, dev agents -> seed `projects/{name}.md`
2. **From shipped features** (archived feature files): Extract key decisions and learnings -> seed `galaxy/decision-*.md` and `galaxy/learning-*.md` notes. This is optional and labor-intensive -- recommend skipping for Phase 1 and letting the vault populate organically.
3. **From planning artifacts** (CONTEXT.md files): Locked decisions are rich sources for `galaxy/decision-*.md` notes. An optional migration script could scan planning artifacts and extract decisions. Recommend as a Phase 2 or later enhancement.
4. **From existing CLAUDE.md project memory** (`~/.claude/projects/*/MEMORY.md`): These contain human preferences and feedback. An optional seed step could parse these into vault notes. Recommend as a quality-of-life enhancement, not a blocker.

### What Existing Data Should Be Migrated

**Recommended migrations (Phase 1):**
- Project name and tech stack from config.md -> `projects/{name}.md`
- Basic human profile stub from project context -> `areas/human-profile.md`

**Optional migrations (Phase 2+):**
- Locked decisions from CONTEXT.md files -> `galaxy/decision-*.md`
- Key learnings from shipped features -> `galaxy/learning-*.md`
- Existing CLAUDE.md memory entries -> appropriate vault notes

**Not recommended for migration:**
- Planning artifacts (RESEARCH.md, TEST-PLAN.md) -- these are ephemeral phase artifacts, not institutional knowledge. The decisions within them should be extracted, not the artifacts themselves.
- Bug tracker history -- too granular. Interesting root causes become `galaxy/learning-*.md` notes through vault-remember during normal operation.
- Iteration logs -- operational data, not knowledge. Not suitable for vault.

---

## Open Questions

- **Q1**: Should inbox processing be a dedicated PM Ralph Loop step (new Step 2.5) or integrated into the existing Step 2 (Check In With Human)? Dedicated step is cleaner but adds cycle time. Integration with check-in is natural since human input often generates captures.

- **Q2**: Should vault notes use Obsidian's `[[note|display text]]` alias syntax for wikilinks, or always use the bare `[[note-name]]` form? Aliases improve readability in Obsidian but add complexity to grep-based link tracking. Recommendation: bare form only in Phase 1, evaluate aliases later.

- **Q3**: Should the vault have a `README.md` at its root that Obsidian displays as the vault homepage? This could show vault health stats, recent updates, and navigation links. Useful for human exploration but adds maintenance overhead.

- **Q4**: Should vault-remember run in the dev agent's cycle or be delegated to a separate vault-agent? A dedicated vault agent could handle all vault maintenance (inbox processing, optimization, remember triggers) without adding overhead to dev/QA cycles. Downside: more agents = more Claude sessions = more cost.

- **Q5**: What is the maximum note size before vault-check warns? Long notes defeat the atomic knowledge principle of galaxy/ notes. Recommendation: warn at >500 lines for galaxy/ notes, no limit for area/ notes.

- **Q6**: Should the `links` frontmatter field be automatically maintained (extracted from wikilinks in content) or manually curated? Automatic maintenance is more reliable but requires vault-check to parse content. Manual curation is simpler but will drift.

- **Q7**: How should the vault interact with `.claude/projects/*/MEMORY.md`? The project memory is Claude Code's built-in per-project memory. The vault is SquidSquad's institutional memory. Should they sync? Should vault-remember also write to MEMORY.md? Or are they intentionally separate layers?

- **Q8**: Should vault notes support a `confidence` field in frontmatter? (e.g., `confidence: high | medium | low`) This helps agents weigh conflicting information. A decision with `confidence: high` (human explicitly confirmed) outweighs one with `confidence: low` (agent inferred from behavior).

---

## Recommendation

**Proceed with phased implementation.** FEAT-SKILL-029 is architecturally sound, technically feasible with no infrastructure dependencies, and addresses a genuine platform need that becomes more acute as SquidSquad adds non-code roles.

Key design decisions to lock:

1. **Vault location**: `.squidsquad/vault/` (co-located with all SquidSquad data)
2. **PM owns inbox processing** (single processor, consistent classification)
3. **Common sub-skills, not per-role** (all agents get the same vault skills)
4. **vault-remember as a hook, not a step** (fires after work actions, not as a separate cycle phase)
5. **Rate limiting from day one** (3 captures/cycle, dedup check, configurable aggressiveness)
6. **Phase 1 is the minimum ship** (structure + templates + vault-create + Level 1 check)
7. **Grep-based search is sufficient for Phase 1-3** (FEAT-SKILL-062 adds semantic search later)
8. **Append-only changelog per note** (git provides full diff history, changelog provides human-readable audit trail)

The largest implementation risk is Ralph Loop integration complexity -- adding vault-remember to all agent templates without bloating cycle time. The mitigation (lightweight inbox captures, capped at 3 per cycle) keeps the overhead minimal. PM's inbox processing is the heavier operation but PM already has the most complex cycle and this fits naturally into its coordination role.

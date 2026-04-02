# FEAT-SKILL-030 Research — Sub-skill Architecture

## Summary

This is a platform-level redesign that breaks the monolithic `SKILL.md` (currently ~1100 lines covering setup, orchestration, all role templates, upgrade logic, schema history, and utility commands) into a main orchestrator skill plus layered sub-skills. The current architecture has everything in one file: setup flow, config generation, three role templates (dev/PM/DM), the Ralph Loop specification, tracker formats, git protocol, PR flow, GitHub Issues ingestion, status commands, upgrade instructions, and schema changelog. The goal is a composable hierarchy: main skill (setup/config/philosophy) -> role sub-skills (pm, skill-lead, dm) -> common sub-skills (tracker protocol, Ralph Loop core, git protocol) -> role-specific sub-skills (feature intake for PM, bug triage for skill, delivery packaging for DM).

The primary risk is that Claude Code's skill system (SKILL.md with YAML frontmatter) has **no native sub-skill or dependency mechanism**. Skills are single-file markdown documents with `name`, `description`, and `version` in frontmatter. There is no `depends_on`, no `includes`, no plugin registry. Any "sub-skill" architecture must be invented within SquidSquad's own conventions, likely using the existing template/bootstrapper pattern (CLAUDE.md points to template files via Read instructions). This is feasible but means the "sub-skill" concept is a SquidSquad abstraction, not a Claude Code platform feature.

Recommendation: **Feasible with significant caveats.** The template/bootstrapper pattern already proves the approach works (agents read template files at boot). Extending this to a multi-file sub-skill system is architecturally sound. However, the atomicity requirement (Phases A-B-C shipping together) combined with the scope of touching every generated file makes this the highest-risk change in SquidSquad's history. A phased internal implementation (even if shipped atomically) with comprehensive upgrade testing is essential.

## Current State Analysis

### SKILL.md Section Map (lines approximate)

| Lines | Section | Target Sub-skill |
|-------|---------|-----------------|
| 1-5 | YAML frontmatter (`name`, `description`, `version`) | **Main skill** (stays in SKILL.md) |
| 6-60 | Architecture diagram, roles table, team shapes | **Main skill** — philosophy/orchestration |
| 61-97 | File Structure Generated | **Main skill** — setup reference |
| 98-170 | Tracker Formats (Bug, Feature, INDEX.md) | **Common sub-skill**: `tracker-protocol` |
| 171-255 | The Ralph Loop (overview, dev loop summary, PM loop summary) | **Common sub-skill**: `ralph-loop-core` |
| 256-280 | Git Protocol, PR-Based Approval Flow | **Common sub-skill**: `git-protocol` |
| 281-360 | Setup Instructions Steps 0-1 (worktree check, gather details) | **Main skill** — setup |
| 361-445 | Setup Steps 2-4 (folder structure, config.md, templates) | **Main skill** — setup |
| 446-530 | Setup Step 4b-4c (bootstrapper CLAUDE.md, root CLAUDE.md) | **Main skill** — setup |
| 531-740 | Setup Step 5 (boot scripts: sh + ps1 for all roles) | **Main skill** — setup (or **common sub-skill**: `boot-scripts`) |
| 741-800 | Setup Steps 5b-5d (statusline, hints, clone setup) | **Main skill** — setup |
| 801-960 | Setup Steps 6-9 (seed trackers, hooks, commit, confirm) | **Main skill** — setup |
| 961-1020 | Upgrade Instructions Steps 1-5 | **Main skill** — upgrade |
| 1020-1055 | Schema Changelog | **Main skill** — schema history |
| 1056-1111 | `/squidsquad-status`, `/squidsquad-interval` commands | **Main skill** — utility commands |

### references/agent-instructions.md Section Map

| Section | Target Sub-skill |
|---------|-----------------|
| Template 1: Dev Agent (full Ralph Loop) | **Role sub-skill**: `skill-lead` (or any dev role) |
| Template 2: PM/QA (full Ralph Loop + Feature Lifecycle) | **Role sub-skill**: `pm-qa` |
| Template 3: DM (full Ralph Loop) | **Role sub-skill**: `dm` |

### Shared Concepts Duplicated Across Templates

These sections appear in nearly identical form across dev, PM, and DM templates and are candidates for common sub-skills:

1. **Ralph Loop core**: cycle markers, status bar state, `/loop` invocation, cycle numbering
2. **Context pressure check**: Step 1b in every template
3. **Working state file**: format, create/update/clear/read lifecycle
4. **Discussion protocol**: append-only, timestamp format, agent name prefix
5. **Interval sync**: Step 1d in every template
6. **Git pull + rebase conflict resolution**: Step 1 in every template
7. **Commit and push**: Step 5 (dev), Step 9 (PM), Step 5 (DM)
8. **Iteration logging**: Step 4 (dev), Step 8 (PM), Step 4 (DM)
9. **Status line description**: identical across all templates
10. **Tracker INDEX.md regeneration**: identical rules everywhere

### Current File Inventory (generated per install)

```
.squidsquad/
  config.md                          -- main skill owns
  .local-config                      -- main skill owns (gitignored)
  .active-role                       -- runtime, gitignored
  statusline.sh                      -- common sub-skill: statusline
  hints-dev.txt, hints-pm.txt, hints-dm.txt  -- common sub-skill: hints
  inject-permissions.sh/.ps1         -- main skill owns
  permissions.template.json          -- main skill owns
  templates/
    dev-agent-[role].md              -- role sub-skill output (generated)
    pm-agent.md                      -- role sub-skill output (generated)
    dm-agent.md                      -- role sub-skill output (generated)
  start-[role].sh/.ps1               -- main skill owns (boot scripts)
  start-pm.sh/.ps1
  start-dm.sh/.ps1
  [role]/
    CLAUDE.md                        -- bootstrapper (main skill generates)
    bugs/, features/, iterations/    -- tracker protocol owns format
    working-state.md                 -- common sub-skill: working-state
    current-state                    -- runtime, gitignored
    planning/                        -- PM feature lifecycle owns
  pm/
    CLAUDE.md, qa-log.md, enhancements.md, iterations/, migrations/
  dm/
    CLAUDE.md, working-state.md, iterations/
```

## Impact Analysis

- **Files touched**:
  - `SKILL.md` — massively reduced (setup + orchestration only, ~400-500 lines down from ~1100)
  - `references/agent-instructions.md` — restructured into multiple files or sections referencing sub-skills
  - `.squidsquad/templates/dev-agent-[role].md` — rebuilt from sub-skill composition
  - `.squidsquad/templates/pm-agent.md` — rebuilt from sub-skill composition
  - `.squidsquad/templates/dm-agent.md` — rebuilt from sub-skill composition
  - All boot scripts (`start-*.sh`, `start-*.ps1`) — may need sub-skill awareness
  - `.squidsquad/config.md` — may need sub-skill registry section
  - `references/` — new sub-skill source files added
  - `.squidsquad/[role]/CLAUDE.md` — bootstrapper format may change

- **Behavior changes**:
  - Template generation shifts from "copy one big template" to "compose from sub-skill parts"
  - Upgrade logic must handle sub-skill composition (more files to regenerate)
  - Agent boot path unchanged (CLAUDE.md -> Read template -> execute) unless sub-skills are loaded separately
  - Setup flow must generate sub-skill files in addition to (or instead of) monolithic templates

- **Dependencies**:
  - Tracker Schema 3 (FEAT-SKILL-051) — just shipped, stable. Sub-skills must preserve this format.
  - Boot scripts — must continue working during and after migration
  - Statusline script — reads `current-state`, `config.md`, tracker files; format must not change
  - `.local-config` — cross-clone health check paths; unchanged
  - `inject-permissions.sh/.ps1` — permission injection; unchanged
  - `/squidsquad-upgrade` — must be the primary migration vehicle

## Side Effects

- **Risk 1**: Running agents lose coherence during upgrade — Severity: **H** — Mitigation: Upgrade must be atomic (single commit). Agents pull the new state on next cycle start (Step 1). The critical window is between `git push` of the upgrade commit and each agent's next `git pull`. Since templates are read fresh on each cycle, agents will naturally pick up the new structure on their next pull. The risk is an agent mid-cycle when the upgrade lands — it already has the old template in context. This is safe because agents only read templates at boot/resume, not mid-cycle.

- **Risk 2**: Existing installs with custom CLAUDE.md modifications — Severity: **M** — Mitigation: Bootstrapper CLAUDE.md files are tiny (~20 lines) and point to templates. Users who modified CLAUDE.md directly (bypassing the template system) would lose changes. The upgrade should detect non-bootstrapper CLAUDE.md files (>50 lines or containing `## The Ralph Loop`) and warn/backup before overwriting.

- **Risk 3**: Different team shapes (1 agent vs 3 agents, with/without DM) — Severity: **M** — Mitigation: Sub-skill composition must handle: (a) single dev agent (no cross-filing sections needed), (b) multi-dev agents (cross-filing enabled), (c) DM present vs absent (PM delivery fallback). The current template system already handles these via placeholder substitution. Sub-skills must preserve this flexibility.

- **Risk 4**: Windows vs Unix path handling in sub-skill file references — Severity: **L** — Mitigation: Continue using forward slashes in all markdown references (bash handles both on Windows via Git Bash). PowerShell boot scripts already handle path translation.

- **Risk 5**: Template size explosion from sub-skill concatenation — Severity: **M** — Mitigation: The composed template must not exceed what Claude can process in initial context. Currently the PM template is the largest (~600 lines). Sub-skill composition should produce equivalent or smaller output by eliminating duplication. Monitor composed template sizes.

## Edge Cases

- **Missing common sub-skill file**: If a common sub-skill source file is deleted or corrupted, template generation fails. Handle by: (a) checking all source files exist before composition, (b) providing clear error message with recovery command (`/squidsquad-upgrade`). The existing bootstrapper pattern already has this: "ERROR: Template file not found. Run /squidsquad-upgrade."

- **Common sub-skills conflict**: Two sub-skills defining the same section (e.g., both `tracker-protocol` and `git-protocol` defining commit behavior). Handle by: (a) clear ownership boundaries (tracker-protocol owns format, git-protocol owns push/pull), (b) explicit ordering in composition (common first, then role-specific, then overrides).

- **Upgrade runs mid-cycle**: Agent is mid-cycle when `/squidsquad-upgrade` commits new template files. Safe because: agents read templates only at boot (via CLAUDE.md Read instruction). The in-memory copy is stable for the current cycle. On next cycle (or context reset), the agent pulls and reads the new template. No mid-cycle template reload occurs.

- **Fresh install vs migrating**: Fresh install gets the new sub-skill structure directly (setup generates composed templates from sub-skill sources). Migrating install gets the same result via `/squidsquad-upgrade` which regenerates templates from the new sub-skill sources. End state is identical.

- **Role sub-skill missing**: If `.squidsquad/templates/dev-agent-skill.md` is deleted but the role is configured in `config.md`, the bootstrapper CLAUDE.md will print an error and stop. This is the existing behavior and is correct.

- **Empty `.squidsquad/` (partial setup)**: If setup fails partway through, the user has a partial `.squidsquad/`. Recovery: re-run setup (it should be idempotent) or delete `.squidsquad/` and start fresh. Sub-skill architecture does not change this risk.

- **Sub-skill version mismatch**: SKILL.md version is 0.9.0 but sub-skill source files are from 0.8.0 (user manually reverted one file). Handle by: version check at template generation time — all sub-skill sources must come from the same SKILL.md version. The upgrade flow already checks SKILL.md version against config.md version.

## Integration Risks

- **Tracker Schema 3 interaction**: Schema 3 (individual files + INDEX.md) is orthogonal to sub-skill architecture. The tracker format is defined in what would become the `tracker-protocol` common sub-skill. No conflict, but the sub-skill must faithfully reproduce the current tracker format documentation. Risk: if the sub-skill extraction introduces subtle differences in the tracker format description, agents may generate malformed tracker files. Mitigation: diff the composed template against the current template to verify byte-for-byte equivalence of tracker sections.

- **Boot scripts interaction**: Boot scripts (`start-*.sh/.ps1`) inject `SQUIDSQUAD_ROLE=<role>` via `--append-system-prompt`. This triggers the CLAUDE.md auto-boot in root CLAUDE.md. The boot path is: system prompt -> root CLAUDE.md detects role -> reads `.squidsquad/[role]/CLAUDE.md` -> reads template. Sub-skill architecture does not change this chain; it only changes how templates are generated (from sub-skill composition rather than monolithic copy). Boot scripts remain unchanged.

- **Statusline interaction**: The statusline script (`statusline.sh`) reads `current-state`, `config.md`, tracker INDEX.md files, `working-state.md`, and git log. It does not read templates or sub-skill source files. No interaction risk.

- **`.local-config` interaction**: Cross-clone health checks read `current-state` files via absolute paths from `.local-config`. Sub-skill architecture does not change the `current-state` file location or format. No interaction risk.

- **Cross-clone health checks**: PM reads other agents' `current-state` via cross-clone paths. This reads runtime files, not templates. No interaction risk.

- **Feature Intake Process interaction**: The 5-phase lifecycle (Research -> Discussion -> Planning -> Execution -> QA) is defined in the PM template. Under sub-skill architecture, this becomes a PM-specific sub-skill (`pm-feature-intake`). The planning artifacts directory (`.squidsquad/[role]/planning/`) and artifact resume logic are PM-specific. No interaction risk as long as the PM sub-skill preserves the same artifact paths and formats.

- **`/squidsquad-upgrade` interaction**: This is the PRIMARY integration point. The upgrade flow must understand sub-skill composition. Currently it copies templates from `references/agent-instructions.md` with placeholder substitution. Under sub-skill architecture, it must: (a) read sub-skill source files, (b) compose them in the correct order, (c) substitute placeholders, (d) write composed templates. The upgrade logic in SKILL.md must be rewritten to handle this new composition step.

## Upgrade & Migration

- **New config values**:
  - Potentially `Sub-skill Version` or `Architecture` field in config.md to distinguish monolithic vs sub-skill installs. Default: set by upgrade to current version.
  - No user-facing config changes expected for Phase A.

- **New files**:
  - `references/sub-skills/common/ralph-loop-core.md` — Ralph Loop cycle structure, markers, /loop invocation
  - `references/sub-skills/common/context-pressure.md` — context pressure check + working state
  - `references/sub-skills/common/tracker-protocol.md` — tracker formats, INDEX.md rules, archival
  - `references/sub-skills/common/discussion-protocol.md` — Discussion section rules
  - `references/sub-skills/common/git-protocol.md` — pull/push/rebase/commit rules
  - `references/sub-skills/common/status-line.md` — status line description
  - `references/sub-skills/common/interval-sync.md` — interval sync step
  - `references/sub-skills/roles/dev-agent.md` — dev-specific Ralph Loop steps (triage, implement, commit)
  - `references/sub-skills/roles/pm-agent.md` — PM-specific steps (check-in, E2E, verify, health)
  - `references/sub-skills/roles/dm-agent.md` — DM-specific steps (delivery, version bump)
  - `references/sub-skills/pm-specific/feature-intake.md` — 5-phase feature lifecycle
  - `references/sub-skills/pm-specific/delivery-fallback.md` — PM delivery when DM absent
  - `references/sub-skills/pm-specific/github-issues.md` — GitHub Issues ingestion
  - `references/sub-skills/pm-specific/pr-flow.md` — PR monitoring
  - `references/sub-skills/skill-specific/bug-triage.md` — bug triage workflow (if differs from generic)
  - `references/sub-skills/dm-specific/delivery-packaging.md` — delivery pipeline
  - `references/sub-skills/dm-specific/version-bumps.md` — version bump sequence
  - Potentially a `references/sub-skills/manifest.md` or `compose.md` defining the composition order

- **Template changes**:
  - `references/agent-instructions.md` — either replaced entirely by sub-skill files, or kept as a generated/composed artifact for backward compatibility
  - `.squidsquad/templates/dev-agent-[role].md` — content identical (composed from sub-skills) but generation method changes
  - `.squidsquad/templates/pm-agent.md` — content identical (composed from sub-skills)
  - `.squidsquad/templates/dm-agent.md` — content identical (composed from sub-skills)

- **Upgrade steps** (`/squidsquad-upgrade` must):
  1. Detect current architecture (monolithic vs sub-skill) by checking for `references/sub-skills/` directory
  2. If monolithic: perform full migration — create sub-skill source files, rebuild templates via composition
  3. If already sub-skill: regenerate composed templates from updated sub-skill sources
  4. Template output must be byte-equivalent to what agents expect (no behavioral change from the agent's perspective)
  5. Bump config.md version

- **Graceful degradation**: If a user does NOT upgrade after SKILL.md is updated to sub-skill architecture:
  - Their existing templates in `.squidsquad/templates/` continue to work (agents read templates, not SKILL.md directly)
  - New features defined in sub-skills won't be available until upgrade
  - No breakage — old templates are self-contained
  - The version mismatch between SKILL.md and config.md will be detected on next `/squidsquad-upgrade` invocation

## Claude Code Skill System Constraints

### What the SKILL.md Format Supports

- **Single file**: A skill is one markdown file with YAML frontmatter (`name`, `description`, `version`)
- **Invocation**: Skills are invoked by name (e.g., `/squidsquad`) and the entire SKILL.md content becomes part of the conversation context
- **No dependencies**: There is no `depends_on` or `requires` field in the frontmatter. A skill cannot declare that it needs other skills installed.
- **No composition**: There is no native mechanism for a skill to include or import content from other skills or files. A skill can instruct the agent to Read files, but this is a runtime action, not a build-time composition.
- **No plugin registry**: Claude Code has no concept of plugins, extensions, or sub-skills at the platform level.
- **Project config**: Skills can define `project_config` in frontmatter for persistent configuration, but this is for simple key-value settings, not for declaring sub-skill manifests.
- **Hooks**: Claude Code supports `SessionStart` hooks in `.claude/settings.json`, which SquidSquad already uses. These are not skill-specific.

### What This Means for Sub-skill Architecture

The "sub-skill" concept is **entirely a SquidSquad abstraction**. Claude Code will not help compose, validate, or manage sub-skills. The implementation must:

1. **Use file-based composition at generation time**: When setup or upgrade runs, read sub-skill source files from `references/sub-skills/` and concatenate them (with appropriate headers/separators) into the monolithic templates that agents actually read. Agents never see "sub-skills" — they see fully composed template files, exactly as today.

2. **Maintain the bootstrapper pattern**: CLAUDE.md files continue to point agents to composed templates via Read instructions. No change to the boot chain.

3. **Define composition order in SKILL.md**: SKILL.md must document which sub-skills are included for each role and in what order. This is the "manifest" — it lives in SKILL.md's setup/upgrade instructions, not in a separate registry.

4. **Version sub-skills via SKILL.md version**: Since there's no independent sub-skill versioning, all sub-skills ship with the SKILL.md version. A version bump to SKILL.md means all sub-skills are updated.

### Constraints to Respect

- The composed template must be a single markdown file (agents read one file via the bootstrapper)
- Template size must stay within Claude's context processing limits (current largest is PM at ~600 lines; composed version should be equivalent)
- No circular references between sub-skills
- Placeholder substitution must happen after composition (compose first, substitute second)
- `references/agent-instructions.md` may need to be preserved for backward compatibility with the upgrade flow's current "read template from references" pattern, or the upgrade flow must be updated to read from `references/sub-skills/` instead

## Hardened Execution Analysis

### What `--print` Mode Enables

Claude Code's `--print` flag runs a single prompt non-interactively and exits. This enables:

1. **Deterministic phase execution**: Each phase (Research, Discussion Prep, Test Plan) can be run as a `--print` invocation with a structured prompt, producing structured output to a file.
2. **No conversational drift**: The agent cannot go off-script because there is no conversation to drift in. It receives a prompt, produces output, and exits.
3. **Chaining**: An orchestrator (the PM agent or a script) can chain `--print` invocations: run Research, check output, run Discussion Prep, etc.
4. **Structured output**: The prompt can specify exact output format (markdown with specific headers), and the `--print` output can be captured and parsed.

### Current Usage

SquidSquad currently uses `--print` nowhere. All agents run interactively with `--append-system-prompt`. The Feature Intake Process uses the `Agent` tool (subagents within the same conversation) for Research and Test Plan phases.

### Limitations

1. **No tool access in `--print`**: Depending on Claude Code version, `--print` may have limited tool access (no MCP, no interactive tools). Need to verify if `--print` can use Read, Write, Edit, Bash, and Grep tools — these are essential for research agents that must read codebase files.
2. **No conversation state**: Each `--print` invocation is stateless. Context from one phase cannot flow to the next except via files. This is actually a feature (forces explicit state passing) but requires careful prompt engineering.
3. **No `--dangerously-skip-permissions`**: This flag is required for non-interactive operation. Need to verify it works with `--print`. If not, phases cannot write files without permission prompts.
4. **Output capture**: `--print` outputs to stdout. The orchestrator must capture this and write it to the appropriate planning artifact file.
5. **Error handling**: If a `--print` invocation fails (exits non-zero, produces malformed output), the orchestrator must detect this and retry or escalate.
6. **No `/loop`**: `--print` cannot invoke `/loop` — it runs once and exits. The orchestrator handles sequencing.
7. **Token limits**: `--print` has the same context window as interactive mode, but the prompt must include all context (SKILL.md content, file contents to analyze) in a single shot. For large codebases, this may be constraining.

### Interaction Breakpoints

Phase B (hardened execution) introduces the concept of phases that run non-interactively. But Phase C (interaction layer) requires human-in-the-loop for Discussion (Phase 2). The breakpoint design:

- **Phase 1 (Research)**: Fully automatable via `--print`. Input: feature spec + codebase. Output: RESEARCH.md file.
- **Phase 2A (Discussion Prep)**: Fully automatable via `--print`. Input: RESEARCH.md. Output: PHASE2-PREP.md.
- **Phase 2 (Discussion)**: Interactive by nature. Cannot use `--print`. Requires human conversation. This is where Phase C's interaction layer matters — the discussion could happen via CLI, web UI, or GitHub Issues.
- **Phase 3 (Planning/Test Plan)**: Partially automatable. Test plan generation is `--print`-compatible. Feature entry creation requires awareness of existing tracker state (can be passed as context).
- **Phase 4 (Execution)**: The dev agent's cycle — already runs interactively.
- **Phase 5 (QA)**: PM verification — interactive (needs to run tests, inspect output).

### Recommendation for Phase B

Start by making Research (Phase 1) and Discussion Prep (Phase 2A) use `--print` mode. These are already subagent-based (using the Agent tool) and have well-defined inputs/outputs. Converting them to `--print` invocations:
- Reduces context pressure (each phase gets a fresh context)
- Prevents conversational drift
- Makes output more deterministic
- Allows parallel execution of multiple research tasks

## Atomicity Strategy

### The Problem

Phases A-B-C must ship together. If Phase A (sub-skill file structure) ships without Phase B (hardened execution), agents would be reading from the new sub-skill-composed templates but still using the old execution model. This is actually fine — the composed templates are byte-equivalent to the old monolithic templates. The real atomicity risk is:

1. **Partial file creation**: If the upgrade creates some sub-skill source files but fails before creating all of them, the composition step will fail. Templates cannot be generated from incomplete sub-skill sources.
2. **Template content divergence**: If the composed template differs from the old monolithic template in any way, agents may behave differently after upgrade.
3. **Git push timing**: The upgrade commits everything in one commit. If the push succeeds, all agents get the full new state on their next pull. If the push fails mid-way, git ensures atomicity (the push either fully succeeds or fully fails).

### Strategy

1. **Single commit, single push**: The upgrade flow already does this (`git add -A && git commit && git push`). All sub-skill source files, composed templates, and config changes go in one commit.

2. **Generate-then-swap**: During upgrade:
   a. Create all sub-skill source files in `references/sub-skills/`
   b. Compose new templates into temporary files (e.g., `.squidsquad/templates/dev-agent-[role].md.new`)
   c. Diff each new template against the existing one to verify equivalence (or expected changes)
   d. Only after all compositions succeed, atomically swap (rename `.new` to final names)
   e. Commit everything

3. **Rollback path**: If composition fails, delete all `.new` files and abort. The existing templates remain untouched. The user can re-run `/squidsquad-upgrade` after the issue is fixed.

4. **Running agents are safe**: Agents read templates at boot (via CLAUDE.md Read instruction). Mid-cycle agents have the template content in their context window already. On next cycle, they pull and re-read the (possibly updated) template. The worst case is a brief period where the config.md version says "new" but the template content is from the old version — but since we commit atomically, this cannot happen.

5. **Backward compatibility window**: Even after the sub-skill architecture ships, the composed templates are what agents actually read. If something goes wrong with sub-skill composition in a future upgrade, the existing composed templates continue to work until the next successful upgrade overwrites them.

### Migration Sequence (within `/squidsquad-upgrade`)

```
1. Read current config.md version
2. Read SKILL.md version — detect gap
3. Create references/sub-skills/ directory tree
4. Write all sub-skill source files from SKILL.md content
5. For each role:
   a. Read composition order from SKILL.md
   b. Read common sub-skills, then role sub-skill, then role-specific sub-skills
   c. Concatenate with headers
   d. Apply placeholder substitution
   e. Write to .squidsquad/templates/[role]-agent.md.new
   f. Diff against existing template — log differences
6. If all compositions succeed:
   a. Rename .new files to final names
   b. Update config.md version
   c. git add -A && git commit && git push
7. If any composition fails:
   a. Delete all .new files
   b. Report error
   c. Existing templates remain untouched
```

## Open Questions

- **Q1**: Should sub-skill source files live in `references/sub-skills/` or in a new top-level directory like `sub-skills/`? — **Why**: This affects the upgrade flow's file discovery, the SKILL.md documentation structure, and whether sub-skill files are "reference material" (like `agent-instructions.md`) or first-class entities. Getting the directory structure wrong means a second migration later.

- **Q2**: Should composed templates be generated at setup/upgrade time (build-time) or at agent boot time (runtime)? — **Why**: Build-time composition (current approach) means agents read pre-composed files and never see sub-skills. Runtime composition means CLAUDE.md instructs agents to Read multiple sub-skill files in sequence. Build-time is safer (one file to read, no ordering issues) but less flexible. Runtime is more dynamic but risks ordering bugs and context pressure from reading many files.

- **Q3**: How should `references/agent-instructions.md` evolve? Keep it as a generated artifact (composed from sub-skills for human reference)? Delete it and replace with sub-skill sources? Keep it as the source and extract sub-skills as views? — **Why**: This file is currently the source of truth for template generation during setup and upgrade. Changing its role affects the entire template generation pipeline.

- **Q4**: What is the minimum viable Phase C (interaction layer)? Full web UI (FEAT-SKILL-020)? GitHub Issues integration (already partially implemented)? Simple file-based discussion (write CONTEXT.md, wait for human to edit it)? — **Why**: Phase C's scope determines whether A-B-C can realistically ship atomically. If Phase C requires a web UI, the atomic requirement becomes impractical. If Phase C is "GitHub Issues as discussion surface," it is much more tractable.

- **Q5**: Should common sub-skills be literally concatenated into templates, or should they be Read as separate files at runtime by the agent? — **Why**: Concatenation means one large template file per role (current behavior, agents are used to it). Separate files mean agents must Read 5-8 files at boot, consuming context. If any file is missing, the agent breaks. Concatenation is safer but makes individual sub-skill updates require full template regeneration.

- **Q6**: How does Phase B (hardened execution via `--print`) interact with the current Agent tool subagent pattern? Replace it entirely? Coexist? — **Why**: Currently PM spawns research/test-plan subagents via the Agent tool (in-process). `--print` would spawn them as separate CLI invocations (out-of-process). Mixing both models adds complexity. But a wholesale switch to `--print` may break existing behavior if `--print` has different tool access.

- **Q7**: What happens to the Schema Changelog in SKILL.md? Does sub-skill architecture itself warrant a new schema version (Schema 4)? — **Why**: Schema versions track tracker format changes. Sub-skill architecture changes the template generation method but not the tracker format. However, the `config.md` structure may change (new fields for sub-skill tracking). If we bump schema, we need a migration path. If we don't, how do we detect "this install predates sub-skill architecture"?

- **Q8**: How to test the atomicity of the migration? — **Why**: The biggest risk is a partial migration leaving agents in a broken state. We need a test that simulates: (a) fresh install with sub-skill architecture, (b) upgrade from monolithic to sub-skill, (c) agent mid-cycle during upgrade. Without these tests, we ship blind on the highest-risk scenario.

## Recommendation

**Feasible with caveats.** The core architectural change (composing templates from sub-skill source files) is sound and extends the existing template/bootstrapper pattern naturally. The Claude Code skill system's lack of native sub-skill support is not a blocker — SquidSquad already invents its own abstractions (bootstrappers, templates, tracker protocol) within the skill format.

Key caveats:

1. **Scope management**: The feature as specified (Phases A+B+C atomic) is very large. Recommend defining Phase C's minimum viable scope early (Q4 above) to avoid scope creep that blocks the atomic ship.

2. **Build-time composition preferred**: Agents should continue reading a single composed template file (Q2, Q5). Runtime multi-file reading adds fragility and context pressure for no user benefit.

3. **Diff-verified migration**: The upgrade must verify that composed templates are functionally equivalent to current monolithic templates before swapping. Any difference must be intentional and documented.

4. **`references/agent-instructions.md` should be generated**: Keep it as a composed artifact (generated from sub-skills) for human readability and backward compatibility. The sub-skill source files in `references/sub-skills/` become the new source of truth (Q3).

5. **Phased internal implementation**: Even though the external ship is atomic, the internal implementation should proceed in stages: (A) extract sub-skills + composition engine, verify template equivalence; (B) add `--print` for Research/Test Plan phases; (C) add minimum interaction surface. Each stage is tested independently before the atomic commit.

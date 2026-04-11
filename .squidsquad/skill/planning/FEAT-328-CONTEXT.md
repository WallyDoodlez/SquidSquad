# FEAT-328 Context — Intent-driven setup wizard with role manifest registry

## Scope

Replace the dev-shaped setup flow with an intent-driven wizard that composes teams from a role manifest registry. PM and DM are always installed. Other roles are added based on user intent via curated presets.

This feature ships:
- A role manifest registry at `references/roles/<role>/manifest.yaml` covering 6 v1 roles
- A new setup wizard in SKILL.md that asks intent first and resolves the pipeline from manifests
- Two presets: `software-dev` and `design`
- A pipeline resolver that walks `routes_to` lists, skipping uninstalled roles
- Refactor of `compose.py`, `config.py`, and PM CLAUDE.md to remove hardcoded role names where the manifest registry can serve

## Locked Decisions (human decided 2026-04-11)

### From initial discussion
1. **Single feature** (not three) — manifest schema + wizard + presets ship together
2. **PM always installed** — the human's entry point
3. **DM always installed** — produces the actual delivery output (Google Drive, email, file export)
4. **Roles SquidSquad-defined for v1** — users customize variation via SOUL.md only. Custom user-defined roles deferred.
5. **Two presets v1**: `software-dev` and `design`
6. **YAML sidecar manifests** at `references/roles/<role>/manifest.yaml` (not frontmatter)
7. **Per-role decentralized `routes_to`** — no central graph file
8. **GitHub CLI is MANDATORY (CORRECTED 2026-04-11)** — earlier "GH Issues ingestion default flipped to Y" was too soft. SquidSquad requires `gh` authenticated for the target repo. There is NO question in the wizard. Install fails fast with clear instructions if `gh auth status` does not succeed. Rationale: gh is the substrate for SquidSquad's tracker, comments, and audit trail (philosophy: "GitHub as the bus"). Non-technical users get instructions to install and authenticate gh as part of the prerequisite check.
9. **Conditional dev question** — only ask BE/FE/Fullstack if intent involves software
10. **Install base = this repo only (CORRECTED 2026-04-11)** — earlier "no install base" was wrong. SquidSquad's own repo IS the install base. Bounded migration: relabel this repo's existing GH Issues, update template references, but no external user installs to worry about.

### From Phase 2 discussion (10 decisions)

11. **Q1 — DM as universal terminal**: Append `dm` to every shipped manifest's `routes_to`. Decentralized, walker stays simple, no special cases. Example: `designer: routes_to: [dev, qa, dm]`, `qa: routes_to: [dm]`, `dev: routes_to: [qa, dm]`.

12. **Q2 — Schema versioning**: Every manifest YAML must have a top-level `schema_version: 1` field. Validator warns on mismatch, errors on unknown version.

13. **Q3 — Dev manifest shape**: Single `references/roles/dev/manifest.yaml` with `setup_questions.variant` field listing be/fe/fullstack. DRY — `routes_to: [qa, dm]` lives in one place. Resolver matches "dev family" to any installed variant.

14. **Q4 — Fullstack default**: Default `software-dev` preset to `be+fe` (two agents). Offer `fullstack` (one combined `dev` agent) as a secondary option in the variant question. Preserves today's default — no regression for existing users. Pipeline display defaults to `PM → Designer → [BE, FE] → QA → DM`.

15. **Q5 — PM → DM direct routing**: Runtime only via resolver fallback. **No third preset.** When the resolved install collapses to `[pm, dm]`, the wizard shows a friendly hint ("Just PM + DM? That's a planning + delivery team — perfect for proposals, briefs, and project plans"). Promote to dedicated preset in v2 if popular.

16. **Q6 — Custom-builder mode**: **Defer entirely to v2.** Honors the "two presets v1" lock. Document the workaround in README: users wanting a custom shape run the closest preset and hand-edit `config.md` + delete unwanted directories. v2 candidate.

17. **Q7 — Designer HITL loop (HUMAN OVERRIDE, REVISED 2x)**: Drop the `design-review` role idea entirely. Designer iterates with the human directly via a **HITL self-loop**. v1 role count stays at **5**: pm, dm, designer, dev (with variants), qa.

   **HITL mechanic** (corrected — designer NEVER pauses):
   - Each designer cycle, in the triage step, designer checks `pending-human` items assigned to itself **first** (priority over new approved features).
   - For each `pending-human` item, designer reads the issue's comments. If a new human comment exists since the designer's last comment on that issue, designer picks it up:
     - Transition `pending-human → in-progress`
     - Iterate on the design based on the human's feedback
     - Re-present (new tool output + new comment with link)
     - Transition `in-progress → pending-human` again
   - Designer moves on to the next pending-human item, or to the next approved feature, or ends the cycle. **Never blocks.**
   - Multiple `pending-human` items can be in flight simultaneously. Designer walks them in priority order each cycle.

   **Manifest representation**:
   - New manifest field: `iteration_mode: hitl`
   - Designer's `routes_to: [pm, dm]` (PM picks up after human approval, DM is the Q1 terminal fallback)
   - Wizard renders the design pipeline as `PM → Designer ↻ → DM` (the `↻` symbolizes HITL)

   **New status label**: `pending-human`
   - Added to the legal-transitions table in `tracker.py`
   - Legal transitions:
     - `in-progress → pending-human`
     - `pending-human → in-progress` (redirect from human)
     - `pending-human → pending-ship` (approval from human)
   - Updated in PM/skill/designer CLAUDE.md transition references

   **Designer produces designs, NOT specs (HUMAN OVERRIDE 3)**: Designer creates designs via an **external connected design tool** (Figma MCP, Google Stitch, etc.), not by writing markdown specs. Output lives in the external tool. Designer only posts a **link/reference** to the design in the issue comment thread. The `.squidsquad/designer/specs/` directory may exist as a thin index mapping `issue_number → tool URL` but the actual design artifact is always in the external tool.

   **HITL approval/redirect detection**:
   - Approval keywords (case-insensitive): `approved`, `approve`, `lgtm`, `ship it`, `looks good`
   - Anything else that's not an approval keyword counts as a redirect
   - Bot-author comments (PM, designer itself) are ignored when scanning for human input
   - First-cycle dev discretion: skill agent picks the exact approval-detection algorithm (regex, comment author check, label-based, etc.)

18. **Q8 — Re-running setup with existing `.squidsquad/`**: Three-way prompt:
   - **(1) Abort** (default, Enter key) — safe no-op
   - **(2) Regenerate templates only** — delegates to `/squidsquad-upgrade`
   - **(3) Full rebuild** — nukes `.squidsquad/` after typed confirmation. Warns about loss of working state, iteration logs, vault content.

19. **Q9 — Intent parser (HUMAN OVERRIDE)**: **LLM sub-prompt only**. The wizard runs inside Claude, so the LLM call is free. Wizard asks Claude to classify the free-text answer into `software-dev | design | unclear` with a short prompt. No local matcher. If `unclear`, fall through to manual preset picker.

20. **Q10 — Pipeline display**: ASCII arrow with bracket notation: `PM → Designer → [BE, FE] → QA → DM`. One-line, screenshot-friendly, matches the research doc's notation. Brackets handle parallel groupings. HITL roles are marked with `↻` (e.g. `PM → Designer ↻ → DM`).

### From Phase 2 follow-up discussion (5 new decisions: tool requirements + tool registry + status taxonomy)

**Q-new5 — Tool registry as first-class citizen**: Tools become first-class entities in their own registry directory. Roles reference tools by ID rather than defining them inline. The registry decouples "what tools exist" from "who uses them" and enables tool reuse across roles.

**Directory structure**:
```
references/
├── roles/
│   ├── pm/manifest.yaml
│   ├── designer/manifest.yaml
│   ├── dev/manifest.yaml
│   ├── qa/manifest.yaml
│   └── dm/manifest.yaml
└── tools/
    ├── figma/
    │   ├── manifest.yaml      # tool definition (IDs, category, mcp_name)
    │   ├── setup.md           # infrastructure setup steps (Claude-assisted)
    │   └── sub-skill.md       # how an agent uses the tool (composed into role CLAUDE.md)
    ├── google_stitch/
    │   ├── manifest.yaml
    │   ├── setup.md
    │   └── sub-skill.md
    └── local_html/
        ├── manifest.yaml
        ├── setup.md           # "no setup needed — built-in" (for consistency)
        └── sub-skill.md
```

**Tool manifest schema**:
```yaml
schema_version: 1
id: figma
display_name: Figma
category: design                # design | delivery | tracker | observability | comms | other
description: Cloud-based UI design and prototyping tool
provider: mcp                   # mcp | builtin | http
mcp_name: figma_mcp             # only if provider=mcp
docs_url: https://figma.com/...
applicable_roles:               # advisory hint, not enforced
  - designer
sub_skill: sub-skill.md         # path within the tool's directory
```

**Role manifests reference tools by ID**:
```yaml
# references/roles/designer/manifest.yaml
requires_tools:
  any_of: [figma, google_stitch, local_html]   # IDs from references/tools/
```

**Resolution at install time** (REVISED — two-level config + mandatory setup walkthrough):

**Phase A — gather tool requirements across ALL roles being installed**:
- Walk every role manifest's `requires_tools.any_of`
- Build the union set of unique tool IDs needed
- This is the "infrastructure surface" of this install

**Phase B — per-tool infrastructure setup (Level 1, runs ONCE per tool)**:
1. For each unique tool in the surface, look up `references/tools/<id>/manifest.yaml` and check availability via `provider`:
   - `builtin` → always available
   - `mcp` → check if `mcp_name` is registered in host Claude session
2. If multiple tools satisfy a single role's `any_of`, ask user to pick one as the primary for that role (this happens before infrastructure setup so we know which tool to set up)
3. **If a chosen tool is NOT available, the wizard runs its setup.md walkthrough (MANDATORY):**
   - Wizard reads `references/tools/<id>/setup.md` and presents the steps to the user
   - User executes the steps. The wizard runs inside Claude, so the user can ask Claude questions about any step at any time ("how do I install the Stitch MCP?", "where do I put my API key?") — Claude answers in-session
   - Wizard prompts: "Done with setup? [yes/retry/skip-this-tool]"
   - On "yes": wizard re-checks availability. If now satisfied, proceed. If not, prompt again with the same options.
   - On "retry": re-display setup.md and re-prompt
   - On "skip-this-tool": move to the next tool in `any_of`. If all tools have been skipped, refuse to install the role per Q-new2.
4. After the user picks a tool that succeeds, the tool is "infrastructure-ready" and won't be walked through again in this install session

**Phase C — per-(role, tool) agent configuration (Level 2, runs ONCE per role-tool pair)**:
1. For each role being installed, walk its chosen tools
2. For each chosen tool, check if its manifest has `agent_config.questions`
3. If yes, ask each question and store the answers under `config.md` → `## Agents` → `<role>` → `tool_configs.<tool>`
4. If no, skip — no per-agent config needed
5. v1 tools have no `agent_config.questions`, so this phase is silent in v1

**Phase D — composition**:
- Compose the chosen tool's `sub-skill.md` into the consuming role's CLAUDE.md at the composition anchor
- Sub-skill content can reference `tool_configs.<tool>` values via template variables (e.g., `{{config.slack.channel}}`)

**Tool setup is non-skippable for the role**: The user can skip an individual tool (and the wizard tries the next one), but if every tool in `any_of` is skipped, the role install fails — there's no "install the role with a broken tool" path. The user can always re-run setup later after acquiring the missing infrastructure.

**For builtin tools**: setup.md still exists (for consistency) but typically says "no setup needed — built-in capability, ready to use." The wizard recognizes builtin tools and skips the walkthrough automatically.

**Tool reuse — two levels (Q-new8)**: Tools have two distinct configuration layers:

1. **Tool-level infrastructure** (the setup.md walkthrough): Shared globally. MCP installation, OAuth, API tokens, SMTP credentials, etc. Walkthrough runs ONCE per tool, no matter how many roles consume it. The wizard tracks which tools have been walked through during a setup session and reuses the result.

2. **Agent-level configuration** (per-role, per-tool): Each agent that uses the same tool can have its own configuration. Example: if both PM and DM use the slack tool, the slack MCP is installed once (Level 1), but PM might post to `#pm-updates` while DM posts to `#deliveries` — those channel choices are Level 2 config, asked separately for each agent.

**Tool manifest declares its own agent-config questions** (optional schema field):

```yaml
# references/tools/slack/manifest.yaml
schema_version: 1
id: slack
display_name: Slack
provider: mcp
mcp_name: slack_mcp
agent_config:
  questions:
    - id: channel
      label: Which Slack channel should this agent post to?
      type: text
      default: "#general"
    - id: notify_on
      label: Which events should trigger a Slack post?
      type: multi-select
      options: [feature-shipped, bug-filed, design-ready, error]
      default: [feature-shipped]
```

When the wizard installs slack for both PM and DM, it asks the `channel` and `notify_on` questions TWICE — once per agent — and stores each agent's answers separately.

**Storage format in config.md** (proposed):

```
## Agents

- **pm**:
  - alias: peggy
  - tool_configs:
    - slack: { channel: "#pm-updates", notify_on: [bug-filed] }
- **dm**:
  - alias: dee
  - tool_configs:
    - slack: { channel: "#deliveries", notify_on: [feature-shipped] }
    - gmail: { from: "deliveries@example.com" }
```

**For v1**: None of the 5 v1 tools (figma, google_stitch, local_html, gmail, local_delivery) need agent-level config questions, so the `agent_config` field is optional and absent from the v1 tool manifests. The schema is in place for future tools (slack, jira, etc.) that need per-agent settings.

The validator must ensure all role-referenced tool IDs exist in the registry.

**Q-new6 — Tool setup walkthrough is MANDATORY in the wizard**: Every tool in the registry must ship with a `setup.md` describing infrastructure requirements (MCP installation, API keys, OAuth, etc.). When a chosen tool is not available at install time, the wizard MUST run the setup.md walkthrough — it's not optional, not deferred, not "skip and warn". Walkthrough is interactive and Claude-assisted because the wizard runs inside a Claude session. The user can skip an individual tool (wizard tries the next in `any_of`) but cannot skip walkthrough for a tool they've selected. If all tools in `any_of` are skipped, the role install fails with a clear message and instructions to acquire missing infrastructure.

**Q-new11 — Lazy tool setup via PM orchestration (REVISED — scoped to environment only)**: Tool selection and setup.md walkthroughs are REMOVED from the install wizard. Tools are deferred until a role actually needs them. PM orchestrates **environment/tool configuration** on workers' behalf. Workers can still interact with humans directly on work content (HITL, clarifications, feedback) — see Q-new12 for the full interaction model.

**Two paths for tool setup**:

**Path A — Pre-emptive (PM proactively)**:
1. During each PM cycle, the triage step scans the approved feature queue
2. For each queued feature, PM determines which roles will work it and cross-references each role's `requires_tools` with `config.md → ## Agents → <role>.tool_configs`
3. If a role has unconfigured tools for work about to land on its desk, PM flags them
4. At the check-in step, PM surfaces: "Feature #42 needs designer + a design tool. Currently unconfigured. Want to set it up now?"
5. If human confirms, PM walks through `references/tools/<id>/setup.md` interactively (Claude-assisted since PM runs inside Claude)
6. On success, PM composes the chosen tool's `sub-skill.md` into the worker's CLAUDE.md template, commits the change
7. Worker role's next cycle reads the updated CLAUDE.md naturally

**Path B — Reactive (worker agent discovers mid-work)**:
1. Worker agent (e.g., designer) is in `in-progress` on a feature
2. Worker discovers a tool requirement it didn't anticipate (e.g., designer realizes the feature needs a Figma-specific capability not covered by the currently-configured tool)
3. Worker PAUSES the task:
   - Transitions `in-progress → pending-human-setup`
   - Comments on the issue with exactly what's needed and why
4. Worker moves on to next work in its backlog — does NOT block its cycle
5. PM's next cycle's triage step detects `pending-human-setup` items across all roles
6. At check-in, PM surfaces the blocked item: "Issue #42 is blocked on tool setup — designer needs Figma MCP configured."
7. Human talks to PM (not directly to designer), PM walks the setup.md interactively
8. On success, PM composes the sub-skill into the worker's CLAUDE.md, commits
9. PM transitions `pending-human-setup → in-progress` so worker picks up next cycle

**New status label**: `pending-human-setup` — follows the `pending-human-<verb>` convention (same as `pending-human-approval` and `pending-human-review`). Legal transitions:
- `in-progress → pending-human-setup` (worker self-pauses)
- `pending-human-setup → in-progress` (PM completes setup, hands back)

**Worker agents never write to their own CLAUDE.md**. Only PM composes tool sub-skills. This maintains the boundary: workers execute their work content (including direct human interaction for HITL, clarifications, feedback), PM owns configuration and environment setup.

**Q-new13 — Setup requirements are declarative, not prescriptive (manifest-driven LLM prompting)**: Role manifests declare WHAT information the wizard needs to collect, not HOW to ask for it. The wizard (running inside Claude) reads each role's `setup_requirements` and uses Claude to craft natural prompts on the fly. This replaces hardcoded Step 4/5/6 logic with a generic walker.

**Manifest schema extension**:

```yaml
setup_requirements:
  - id: variant
    needs: "which dev team shape the user wants — backend only, frontend only, both (two separate agents), or fullstack (one combined agent)"
    used_for: "deciding how to structure the engineering team for this project"
  - id: stack
    needs: "the tech stack the project uses — language, framework, package manager, test runner"
    used_for: "knowing how the dev agent runs builds and tests for the project"
    repo_hints: ["package.json", "requirements.txt", "go.mod", "pyproject.toml", "Cargo.toml"]
    per_installed_agent: true
    only_in_presets: [software-dev]  # optional filter
```

**Field semantics**:
- `id` — unique within the role, used as the key for storing the answer
- `needs` — one-sentence description of what information is needed, written in **domain terms only** (see Q-new14). Claude uses this to understand and prompt the user naturally.
- `used_for` — why this info is needed, written in **domain terms only**. Helps Claude frame the question and handle edge cases.
- `repo_hints` — optional file path patterns the wizard can inspect before asking (lets Claude pre-read project artifacts like `package.json` and make the prompt smarter)
- `per_installed_agent` — if true, the requirement is asked once per installed agent of the role (e.g., stack asked for both backend and frontend agents if variant = both)
- `only_in_presets` — optional filter; if present, the requirement only fires when the install preset is in this list

**Q-new14 — Manifests must be domain-only, no SquidSquad internals**: Role and tool manifests describe their domain in terms any software professional would recognize. They never reference:
- Internal file paths (`config.md`, `CLAUDE.md`, `.squidsquad/...`)
- Internal terms (status labels, tracker schemas, composition anchors, sub-skill composition points)
- Internal scripts, conventions, or storage mechanisms
- Anything that requires a reader to know SquidSquad's source code to understand

**Why**:
1. Manifests are the public contract for what each role does — browsing `references/roles/` should be self-explanatory
2. Internal restructures (renaming files, moving data) stay cheap — no manifest edits required
3. Future user-authored manifests (custom roles, v2 feature) don't require users to learn SquidSquad internals
4. Claude handles the internal mapping — the wizard knows where answers go, the manifest just declares domain facts

**Applies to**:
- Role manifests (`references/roles/<role>/manifest.yaml`)
- Tool manifests (`references/tools/<tool>/manifest.yaml`)
- Tool setup.md files (those describe tool infrastructure, not SquidSquad internals)
- Tool sub-skill.md files (those describe how an agent uses the tool, not how SquidSquad stores the choice)

**Does NOT apply to**:
- SKILL.md, CLAUDE.md templates — these are SquidSquad's own internals and naturally reference its internals
- Scripts in `references/scripts/` — implementation code can reference anything
- Sub-skill files that are explicitly SquidSquad-specific (e.g., tracker protocol instructions)

**Wizard walker**:
1. Determine which roles are being installed (from the preset)
2. For each role in preset install order, read its `setup_requirements`
3. For each requirement, skip if `only_in_presets` doesn't include the active preset
4. Prompt Claude: "Ask the user for [needs]. Context: this is used for [used_for]. Here are the repo hints: [repo_hints contents]. Prompt naturally and interpret the answer."
5. Record the interpreted answer under `config.md → ## Agents → <role>.setup → <id>`
6. Continue to the next requirement
7. After all role requirements are walked, continue to Step 5 (loop interval) in the install flow

**What this replaces**:
- Hardcoded Step 4 (designer optional) → becomes designer's `install_optional` requirement
- Hardcoded Step 5 (dev variant) → becomes dev's `variant` requirement
- Hardcoded Step 6 (frameworks/tests) → becomes dev's `stack` requirement with `repo_hints`

**Install flow after Q-new13** (generic, fewer hardcoded steps):

```
Step 0   — gh prerequisite check
Step 0b  — re-run detection
Step 1   — project name + repo
Step 2   — intent question (uses the same LLM-prompting mechanism at wizard level)
Step 3   — preset confirmation
Step 4   — INJECTED: walk each installed role's setup_requirements in preset install order
Step 5   — loop interval (core wizard field, not role-specific)
Step 6   — review screen (P/V/E/A)
Step 7   — commit and write files
```

Adding a new role to v2 (e.g., copywriter) just means writing `references/roles/copywriter/manifest.yaml` with whatever setup_requirements it needs. The wizard picks them up automatically.

**Previously locked decisions that fold into this**:
- Q4 (default be+fe) — expressed as a hint in dev.variant's `needs` text or in wizard system prompt
- Q-new7 (LLM stack detection) — subsumed: dev.stack uses the generic LLM-prompting pattern with `repo_hints`
- Q-new10 (designer before dev order) — expressed by preset's role install order (software-dev: `[designer, dev, qa]`)

---

**Q-new12 — Human-to-agent interaction model**: Humans can engage ANY agent directly about work content. PM is not a required middle-layer for work discussions. What PM owns exclusively is the environment — tool setup, role manifest/config changes, cross-agent coordination, and ingesting new feature/bug requests into the tracker.

**Direct human ↔ worker interactions (allowed, no PM involvement)**:
- HITL design review — human comments directly on designer's issues to approve or redirect (already locked in Q7)
- Clarifying an assigned feature/bug — human can comment on any issue assigned to any worker
- Mid-iteration feedback — human can interject on a designer's pending-human-review item without routing through PM
- Filing bugs or features against a specific worker's domain — human can drop a new issue assigned to `role:skill` or `role:designer` without PM having to triage first
- Status updates or "how's it going" questions on any in-progress item

**PM-exclusive interactions (workers route THROUGH PM)**:
- Tool setup walkthroughs (`references/tools/<id>/setup.md`)
- Role manifest changes
- Config.md edits
- Composition of tool sub-skills into any CLAUDE.md
- Cross-agent reassignments (rerouting work between roles)

**Worker self-pause for environment issues**: When a worker discovers an environment/infrastructure gap it cannot resolve itself (missing tool, unauthenticated MCP, malformed config), it transitions `in-progress → pending-human-setup`, comments on the issue, and moves on. PM picks up the gap at its next cycle. This is the one place workers CANNOT resolve things directly with humans — everything environment-related routes through PM.

**Why the split**: Environment changes affect cross-agent state (multiple roles may share a tool, config.md is shared, composition changes commit to CLAUDE.md templates). Work content is local to the issue thread. Keeping these separate prevents config thrash and keeps the environment coherent while still letting humans get work done without going through a middle-layer.

**Composition is committed**: When PM completes a tool setup, the worker's CLAUDE.md template is modified with the tool's sub-skill content composed at the composition anchor. PM commits the change as part of the tool-setup operation. Traceable via git history ("PM configured designer with figma tool for #42").

**First-time composition vs re-composition**: If a role already has a tool configured and PM is asked to configure a DIFFERENT tool of the same category (e.g., switching designer from figma to stitch), PM replaces the existing sub-skill at the same anchor. Previous tool config is removed from `config.md` and the old sub-skill is excised from the worker's CLAUDE.md. Git history preserves the previous state.

**PM cycle impact**: PM's triage step gains two new sub-checks:
1. **Pre-emptive**: scan approved features' role requirements against `config.md` tool configs
2. **Reactive**: scan for `pending-human-setup` items

Both bubble up to check-in.

---

**Q-new10 — Setup step order: Designer before Dev**: In the `software-dev` preset, the designer-optional question MUST come before the dev variant question. Reasoning: designer produces the design that feeds dev work, so the install order should mirror the work order. This also means designer's tool selection (Step 6) precedes dev's stack/framework questions (Step 7), giving the user a clean "design first, build second" flow.

**Revised step order in software-dev preset**:
1. Step 0 — gh prerequisite check
2. Step 0b — re-run handling
3. Step 1 — project name + repo
4. Step 2 — intent question (LLM-classified)
5. Step 3 — preset confirmation (software-dev | design)
6. **Step 4 — Designer optional** (Y/N, only in software-dev preset; design preset always installs designer)
7. **Step 5 — Dev variant** (be+fe / fullstack / be only / fe only, only in software-dev preset)
8. Step 6 — Tool selection + setup walkthrough (per role, designer's tool first since designer is installed first)
9. Step 7 — Frameworks/test commands (per dev variant, with LLM stack detection)
10. Step 8 — Loop interval
11. Step 9 — Review screen ([P]roceed / [V]iew / [E]dit / [A]bort)
12. Step 10 — Commit and write files

**Q-new9 — Step 9 is an interactive review screen with preview + edit + proceed/abort**: Today's flow gates the install on a single `[Y/n]` confirmation. The new wizard makes Step 9 a full review screen so the user can inspect what's about to be written before any file touches disk.

**Step 9 menu** (presented after the summary table):

```
SquidSquad Setup Summary
========================

Project:       my-app
Repo:          github.com/wallydoodlez/my-app
Preset:        software-dev
Pipeline:      PM → Designer ↻ → [BE, FE] → QA → DM

Roles installed:
  - pm  (always)
  - designer (HITL, tool: figma)
  - be   (FastAPI, pytest tests/be)
  - fe   (Next.js, npm test)
  - qa
  - dm   (tool: gmail)

Loop interval: 10 min

What would you like to do?
  [P] Proceed with setup
  [V] View what will be written (preview files)
  [E] Edit a specific step
  [A] Abort
```

**Action semantics**:

- **[P] Proceed**: Move to Step 10 (commit and write files). This is the only path forward.
- **[V] View / preview** — Show the actual content of what would be written, in-place, without committing anything to disk:
  - `config.md` content
  - Each role's composed `CLAUDE.md` (base template + chosen tool sub-skills + agent config rendered)
  - The list of GitHub labels that will be created or migrated
  - The list of files that will be added to git (paths only)
  - Boot script names
  - Any one-time migration scripts that will run (status label rewrites etc.)
  - Preview is read-only and re-displays the menu after the user finishes scrolling
- **[E] Edit** — Re-open a specific step. Asks "Which step?" and lists the editable steps (1: project, 2: intent, 3: preset, 4: dev variant, 5: designer optional, 6: tool selection, 7: stack/tests, 8: interval). Selecting one returns to that step in re-edit mode (the wizard remembers all OTHER answers and only re-prompts the chosen step). After the edit, returns to Step 9.
- **[A] Abort** — Exits the wizard immediately. Nothing is written to disk. Wizard prints a one-line "no changes made" message and exits with code 0.

**No file system writes happen before [P]**: All wizard state is in-memory until Step 10. This is the strong invariant — the user can preview, edit, and abort freely without leaving any trace. Step 10 is the only step that touches the disk (besides the tool setup walkthrough in Step 6, which is necessary because MCP install / OAuth must happen at the user's system level).

**Edge case — re-running setup with existing `.squidsquad/` (Step 0b)**: If the user chose "Full rebuild" at Step 0b, the actual nuke-and-replace happens in Step 10, not Step 0b. Step 0b just records the intent. Step 9 review can show "WARNING: Existing `.squidsquad/` will be DELETED on proceed" so the user can still abort.

---

**Q-new7 — Step 7 (frameworks/test commands) is LLM-assisted with stack auto-detection**: Today's setup blank-prompts the user for framework and test command per dev variant. The new wizard uses repo inspection + LLM inference to suggest both, then asks the user to confirm or override. Process per dev variant:

1. **Detect candidate files** in the repo for the variant (BE looks for `requirements.txt`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `pom.xml`, `Gemfile`, etc.; FE looks for `package.json`, `pnpm-lock.yaml`, `vite.config.*`, `next.config.*`, etc.)
2. **Ask Claude (host LLM)** to classify the detected files into a probable tech stack (e.g., "FastAPI + Python 3.11 + pytest", "Next.js + TypeScript + jest")
3. **Suggest the stack** to the user as the default: "Detected: Next.js (TypeScript). Use this? [Y/n]"
4. On `n`, prompt for free-text override (still LLM-classified to a structured form for config.md)
5. **Suggest the test command** based on the chosen stack using common conventions (Next.js → `npm test`, pytest → `pytest tests/`, go test → `go test ./...`, etc.)
6. User confirms or overrides the test command
7. Both values written to `config.md` per dev variant

The Claude session is already loaded; the LLM classification is essentially free. Same philosophy as Q9 (intent parser is LLM-only) — use Claude for inference inside the wizard.

**Edge cases**:
- No detectable files → wizard asks "What tech stack does [variant] use?" as a free-text prompt, LLM classifies, then suggests test command
- Multiple plausible stacks (e.g., monorepo with Next.js + Express) → wizard presents top 2-3 candidates and asks user to pick
- User picks "skip framework / no tests" → both fields are recorded as empty in config.md, agent skips test step in its cycle

**Future SOUL/customization extension**: v1 hardcodes tools at the manifest level. Future feature: a role's SOUL.md or a customization YAML can grant additional tool IDs (e.g., a "PM-marketing" SOUL grants `[mailchimp, hubspot]` on top of PM's base tools). The dev agent does NOT need to build this in v1 — they just need to NOT hardcode tool IDs in compose.py / sub-skill composition logic. Make tool grants data-driven from the manifest so future grants are possible without code changes.

**v1 registry inventory (REVISED — gmail removed, 4 tools)**: 4 tools ship in v1.

**Designer tools** (3):
- `references/tools/figma/` — provider: mcp, mcp_name: figma_mcp, applicable_roles: [designer]
- `references/tools/google_stitch/` — provider: mcp, mcp_name: google_stitch, applicable_roles: [designer]
- `references/tools/local_html/` — provider: builtin, applicable_roles: [designer]

**DM tools** (1):
- `references/tools/local_delivery/` — provider: builtin, category: delivery, applicable_roles: [dm]. DM writes delivery payloads to `.squidsquad/dm/deliveries/<issue>/` as the always-available fallback. Includes a manifest of what was "delivered" with timestamps. **In v1, this is DM's only tool** — gmail and other delivery integrations (slack, google_drive, smtp, outlook) are deferred to follow-up features.

PM/dev/qa tool definitions are deferred to follow-up features but the registry STRUCTURE is in place so adding them later is just dropping in new directories. Future delivery tools (gmail, slack, google_drive, etc.) follow the same pattern as local_delivery but with `provider: mcp` and a real `setup.md` walkthrough.



**Q-new4 — Status taxonomy clarity**: Any status that requires a HUMAN to act must have `human` explicitly in the name. Two human-required statuses:

- **`pending-human-approval`** (rename of today's `pending`) — first approval gate. Human decides: plan this feature (→ `planning`) or execute it directly (→ `approved`).
- **`pending-human-review`** (new, for HITL roles like designer) — human reviews an in-progress iteration. Human decides: approve and ship (→ `pending-ship`) or redirect (→ `in-progress`).

Existing `pending-test` and `pending-ship` stay unchanged — they are agent-driven (QA verifies, DM delivers), no human required.

Future "agent-on-agent" review statuses follow the same naming convention: `pending-agent-review`, `pending-agent-approval`, etc. The `human` / `agent` infix makes the actor explicit at a glance.



21. **Q-new1 — Universal `requires_tools` manifest field**: Every role manifest can declare `requires_tools` with `any_of` / `all_of` lists. Wizard validates tool availability at install time by inspecting the host Claude session's available MCP servers. This is a first-class manifest field, not a designer-only special case. Future roles (DM with delivery tools, marketers with analytics, etc.) use the same mechanism.

   **Schema**:
   ```yaml
   requires_tools:
     any_of:
       - figma_mcp
       - google_stitch
     all_of: []  # roles can require multiple tools simultaneously
   ```

   **Tool identifier convention**: Lowercase, snake_case, matches the MCP server name as registered in Claude (e.g., `figma_mcp`, `gmail_mcp`, `slack_mcp`). Validator does a fuzzy match against the registered MCP servers.

22. **Q-new2 — SUPERSEDED BY Q-new11**: Original lock was "refuse to install the role if required tool missing". This is REMOVED. Tools no longer gate install — they're configured lazily by PM per Q-new11. Keeping this entry for historical traceability, but the active lock is Q-new11.

**Q-new2 (superseded) — original text below**: If a role's `requires_tools` cannot be satisfied at install time, the wizard **refuses to install the role** and prints a clear message:
   ```
   Designer requires one of: figma_mcp, google_stitch
   None are available in this Claude session.
   To install Designer, add one of these MCPs to Claude (see Claude docs)
   then re-run /squidsquad-setup.
   Skipping Designer for this install.
   ```
   - Strong invariant: a role only installs if it can actually function
   - The wizard continues with the rest of the preset (other roles still install)
   - If the missing tool is for a **required** role of the preset (not optional), the wizard prompts the user: abort install entirely, or fall back to a degraded preset
   - **Re-run handling**: when user re-runs setup with a tool that wasn't available before, the three-way prompt (Q8) gains an implicit fourth path: "regenerate to add newly-available roles"

23. **Q-new3 — v1 designer tool support (REVISED — added HTML fallback)**: Designer's `requires_tools.any_of` lists **figma_mcp**, **google_stitch**, and **local_html** for v1. Other tools (Penpot, Sketch, web-fetch, etc.) deferred to v2.
   - If the user has multiple of these installed/available, wizard asks which to use as the designer's primary tool (single-select)
   - The chosen tool ID is written to `config.md` under a new section: `## Tools` → `- **designer**: figma_mcp`
   - Designer's CLAUDE.md template is composed with tool-specific sub-skills: `references/sub-skills/designer-tools/figma.md`, `references/sub-skills/designer-tools/stitch.md`, `references/sub-skills/designer-tools/html.md`. Only the chosen tool's sub-skill gets composed in.

   **`local_html` is a built-in capability, not an MCP**: It requires no external server. The designer agent uses Read/Write/Edit to produce HTML/CSS/JS files at `.squidsquad/designer/designs/<issue-number>/index.html` (and supporting assets). The HITL link posted in the issue comment is a relative path or `file://` URL pointing to the local HTML file. Human opens it in a browser to review.

   **Tool identifier convention update**: A tool ID can refer to either:
   - An external MCP server (e.g. `figma_mcp`, `google_stitch`) — the validator inspects the host Claude session's MCP servers
   - A built-in capability (e.g. `local_html`) — always considered "available" by the validator, requires no external setup

   **Practical consequence**: Because `local_html` is always available, **designer can always install in v1**. The Q-new2 "refuse install" path never fires for designer. The path is reserved for future roles whose tool requirements have no built-in fallback (e.g. DM with delivery tools, where there's no "local fallback" for sending email).

   **HTML sub-skill scope** (`references/sub-skills/designer-tools/html.md`):
   - Folder structure: `.squidsquad/designer/designs/<issue>/index.html` + sibling assets
   - Use semantic HTML, inline CSS or one stylesheet per design
   - No build step, no framework, no JS bundler — plain HTML is the deliverable
   - Designer can include reference screenshots, mood boards, etc. as sibling files
   - Comment in issue references the local path: `Iteration 1: see designs/42/index.html`
   - Human opens the file directly in their browser; redirects via issue comment

### Implications for the v1 work

- Manifest schema gets a new top-level field `requires_tools` (Q-new1) referencing tool IDs from the registry (Q-new5)
- Manifest schema gets a new top-level field `iteration_mode: hitl | normal` (Q7)
- **NEW: Tool registry at `references/tools/<id>/{manifest.yaml,sub-skill.md}`** with 3 tools shipping in v1: figma, google_stitch, local_html (Q-new5)
- Validator (`references/scripts/manifest.py`) gains:
  - Tool registry loader (parse all `references/tools/*/manifest.yaml`)
  - Cross-reference check (every role's `requires_tools` IDs must exist in registry)
  - MCP-availability detection at install time (enumerate host Claude session's MCP servers, mechanism TBD, dev discretion)
  - Built-in capabilities (provider=builtin) always pass availability check
- Wizard gets a tool-selection sub-step for roles with multiple satisfying tools (Q-new3)
- Wizard composes the selected tool's `sub-skill.md` into the consuming role's CLAUDE.md at install time. Requires a composition anchor in the role's CLAUDE.md template (e.g., `<!-- TOOL_SUBSKILL -->` placeholder).
- Designer's `references/roles/designer/` template directory does NOT need its own tool sub-skill files anymore — they live in the tool registry under `references/tools/<id>/sub-skill.md`
- `config.md` schema gains a `## Tools` section recording the chosen tool ID per role
- Hard prerequisite: gh CLI must be installed and authenticated (no longer a wizard question, checked at Step 0)
- New status labels: `status:pending-human-approval` and `status:pending-human-review`
- Existing `status:pending` is renamed → `status:pending-human-approval` (migration in this repo only)
- tracker.py legal-transitions table updated to include both new transitions and remove old `pending` references
- Test plan must cover: tool present (install succeeds), tool missing (install refused with clear message), multiple tools present (selection prompt), tool registry validation (role references unknown tool ID → fail loudly), HITL designer iterating on a real issue with figma/stitch/html tools, status migration script idempotency, gh missing → setup aborts at Step 0

## v1 Role Inventory (final, REVISED)

| Role | Always installed | Presets | iteration_mode | routes_to | requires_tools |
|------|------------------|---------|----------------|-----------|----------------|
| pm | yes | both | normal | [designer, dev, qa, dm] | none in v1 |
| dm | yes | both | normal | [] (terminal) | `any_of: [local_delivery]` |
| designer | optional in software-dev, required in design | both | **hitl** | [pm, dm] | `any_of: [figma_mcp, google_stitch, local_html]` |
| dev (be/fe/fullstack variants) | required in software-dev only | software-dev | normal | [qa, dm] | none |
| qa | auto-installed when dev is installed | software-dev | normal | [dm] | none |

**Total v1 roles: 5** (no design-review)

**Resolved pipelines:**
- `software-dev` default (with designer): `PM → Designer ↻ → [BE, FE] → QA → DM`
- `software-dev` no designer: `PM → [BE, FE] → QA → DM`
- `software-dev` fullstack: `PM → Designer? ↻ → Dev → QA → DM`
- `design`: `PM → Designer ↻ → DM`
- minimal (any preset, decline all optionals): `PM → DM`

**Note on `↻`**: The `↻` glyph in the pipeline display indicates a HITL role — that role iterates with the human via issue comments before handing off. Hovers / tooltips not in scope for v1; the glyph is documented in README.

## Dev Discretion (skill-lead can choose)

- Manifest YAML field naming details (as long as `schema_version`, `name`, `routes_to`, `setup_questions`, `template_refs` exist)
- Validator implementation (Python in `references/scripts/manifest.py` is the obvious choice)
- Resolver algorithm details (recursion vs iteration, cycle detection mechanism)
- Wizard UX prose (prompts, error messages, hints)
- LLM sub-prompt wording for intent classification
- Where to store the `routes_to` traversal logic (`manifest.py`, new file, or inline in `compose.py`)
- Whether `design-review` reuses parts of QA's CLAUDE.md template or is fully standalone (recommend mostly standalone with shared sub-skills where they apply)

## Side Effect Mitigations (required)

From RESEARCH.md §5:

1. **Removing hardcoded role refs in PM CLAUDE.md** — refactor must preserve all existing PM behavior. Test: run a full PM cycle on the `software-dev` preset and verify all 11 hardcoded sites still work.
2. **`compose.py` dispatch tables** (lines 100-106, 166-167, 201-214) — replace with manifest lookups. Add a unit test that loads each shipped manifest and verifies compose.py can still produce a valid CLAUDE.md for each role.
3. **`config.py` FIELD_MAP** (lines 26-52) and **`sync_agents()`** (line 162) — must stay backward compatible with config.md files written by the new wizard. Document the new config.md schema in CONTEXT.
4. **`statusline.sh` agent loop** — must read installed roles from manifest, not hardcoded list. Test: install design preset and verify status line shows pm/designer/design-review/dm.
5. **Manifest validation at setup time** — malformed YAML must fail loudly with line number and field name. Never silent fallback.
6. **Cycle detection in resolver** — even though no v1 manifest creates cycles, the resolver must detect and reject `routes_to` loops to prevent future bugs.
7. **`design-review` is a brand new role** — boot scripts (`start-role.sh`/`ps1`) must work with it without changes (already parameterized via `[ROLE]`).

## Upgrade Path

**Bounded migration: this repo only.** SquidSquad's own repo is the single install base for v1. Migration tasks:

1. **GH Issue label migration**: Rewrite all open + closed issues currently labeled `status:pending` to `status:pending-human-approval`. Use a one-shot script in `references/scripts/migrate_status_labels.py` (or inline gh CLI commands). Check the count before and after to verify completeness.
2. **Label table update**: Add `status:pending-human-approval` and `status:pending-human-review` to the GH labels list. Remove `status:pending` after migration is complete and verified.
3. **tracker.py legal transitions**: Update the transitions table:
   - Old: `pending → planning | approved`
   - New: `pending-human-approval → planning | approved`
   - New: `in-progress → pending-human-review` (for HITL roles)
   - New: `pending-human-review → in-progress | pending-ship`
4. **Template/text references**: Find and replace `pending` (status context) with `pending-human-approval` across all CLAUDE.md files, sub-skills, SKILL.md, README, and references/scripts/. Be careful not to clobber `pending-test`/`pending-ship` references.
5. **Working-state and iteration log references**: Update format docs but do NOT rewrite existing iter-N.md files (history is preserved as-is).
6. **`/squidsquad-upgrade` flow**: v1 of upgrade does NOT need to learn manifests (manifests are setup-time only, frozen into config.md). But upgrade DOES need to handle the new label namespace if any external install ever exists (none today).

**Migration ordering** (important to avoid breakage):
1. First add the new labels (`pending-human-approval`, `pending-human-review`) — additive, no breakage
2. Update tracker.py to accept both old and new transitions during a transition window
3. Run the issue migration script (rewrites labels)
4. Update templates and CLAUDE.md files
5. Remove `pending` label and the transition-window code in tracker.py
6. Verify with a full PM cycle that nothing references the old label

Future-upgrade consideration: when manifest `schema_version` bumps to 2 (post-v1), `/squidsquad-upgrade` will need to migrate manifests. Out of v1 scope.

## Out of Scope

- User-defined custom roles (future feature)
- Role variation derivatives (PM-marketing, Dev-firmware) — future feature, captured in #328 body
- Custom-builder wizard mode (v2 — see Q6)
- Third preset for `planning-delivery` workflow (v2 — see Q5)
- Migration of any existing installs (no install base)
- Marketing / research / content presets (v2)
- A `modify team` post-setup mode (v2 — captured in Q8)
- LLM intent classifier running outside Claude (only inside-Claude wizard supported)
- `references/scripts/manifest.py add-role` post-setup script (v2 — see Q6)

## Phase 3 — Test Planning

Test plan subagent will read this CONTEXT.md and produce `FEAT-328-TEST-PLAN.md` covering:
- Happy path for both presets (software-dev with be+fe, design with new design-review)
- Variant question coverage (be+fe / fullstack / be only / fe only)
- DM-as-terminal walker resolution for [pm, designer, dm] case
- Re-run setup three-way prompt (abort default, upgrade path, full rebuild)
- LLM intent classifier with three test inputs (software, design, unclear)
- Schema version validation (valid, missing, unknown)
- Malformed manifest YAML → loud failure
- Cycle detection in resolver (synthetic test manifest)
- design-review role end-to-end (pickup design:complete issues, verify against AC, route to DM)
- Regression: existing software-dev workflow still works
- ASCII arrow display rendering on PowerShell + bash

## References

- Research: `.squidsquad/skill/planning/FEAT-328-RESEARCH.md`
- Phase 2 prep: `.squidsquad/skill/planning/FEAT-328-PHASE2-PREP.md`
- Original feature filing: WallyDoodlez/SquidSquad#328
- Current setup flow being replaced: `SKILL.md` Step 1 (Gather Project Details) and Steps 2-6

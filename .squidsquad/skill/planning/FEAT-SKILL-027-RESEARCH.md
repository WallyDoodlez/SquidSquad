# FEAT-SKILL-027 Research — Designer Agent Role

## Summary

The Designer agent role is a significant new agent template that bridges external design tools (Figma, Google Stitch, etc.) with frontend implementation agents. The designer sits between PM feature intake and dev execution, producing structured design specs (component definitions, design tokens, layout specs, asset references) that FE agents consume. The architecture is feasible but requires careful pipeline integration — the designer must slot into the existing 5-phase feature lifecycle without breaking the PM-to-dev handoff for features that do not need design.

The primary complexity is not in the agent template itself (which follows the established Ralph Loop pattern) but in the pipeline orchestration: deciding which features need design, how the designer assesses technical feasibility before committing to a direction, the handoff format between designer and dev, and the feedback loop when dev discovers a design is impractical. The designer also introduces a new cross-agent dependency pattern — unlike dev agents that work independently on their domain, the designer produces specs that another agent (FE) must consume, creating a sequential dependency in the feature pipeline.

The feature should be built as a role sub-skill under the FEAT-SKILL-030 architecture (once available), with a dedicated Template 4 (Designer Agent) in `references/agent-instructions.md`. Until sub-skills land, it can be developed as a monolithic template alongside the existing three. The generalized design tool abstraction (MCP/API) is straightforward — the designer template references a config section listing connected tools, and falls back to manual spec mode when no tool is connected.

## Impact Analysis

- **Files touched**: `references/agent-instructions.md` (new Template 4), `SKILL.md` (designer role docs, setup flow changes, architecture diagram), `.squidsquad/config.md` schema (new designer config section), PM template (pipeline routing logic for design-needed features), setup flow (designer role detection and template generation)
- **Behavior changes**: New feature status flow branch for design-needed features (PM routes to designer before dev); new tracker directory `.squidsquad/designer/` with bugs/features/iterations; PM gains ability to flag features as "needs design"; designer produces specs in a shared `design-specs/` directory or `.squidsquad/designer/specs/`; FE agent template gains "read design specs before implementing" step
- **Dependencies**: FEAT-SKILL-030 (sub-skill architecture) — designer should ideally be built as a sub-skill, but can be built monolithically first and migrated later. No hard dependency on external design tools — manual mode is required as baseline.

---

## 1. Technical Feasibility Assessment Mechanism

### How the Designer Evaluates Feasibility

The designer agent must perform a feasibility check before producing a full design spec. This is analogous to the PM's Phase 1 Research but focused on implementation viability rather than product scope.

**Feasibility evaluation inputs:**
1. **Codebase reading**: The designer reads the project's existing component library, CSS/token system, layout patterns, and framework constraints. For example, if the project uses Tailwind CSS with a fixed design system, the designer knows not to spec custom CSS animations that would fight the framework.
2. **Tech stack awareness**: The designer reads `config.md` for framework/language info (collected during setup) and understands the constraints of each stack. A Next.js project has different layout constraints than a React Native project.
3. **Past feature complexity**: The designer reads shipped features in the FE agent's tracker to calibrate complexity. If previous features of similar scope took 3 cycles, a proposed design requiring 15 cycles is a red flag.
4. **Dev agent consultation via Discussion**: For ambiguous cases, the designer appends a Discussion entry asking the FE agent to assess a specific technical question. This is asynchronous — the designer flags it and moves on, checking next cycle.
5. **Design tool constraints**: If connected to Figma/Stitch, the designer checks whether the design uses components/patterns that have known implementation challenges (e.g., complex blend modes, custom fonts not available in the target platform).

### Calibrating "Reasonable Engineering Effort"

This is inherently project-specific. Rather than a universal threshold, the designer should use a relative measure:

- **Baseline**: Average cycle count for recent shipped FE features of similar category (UI component, page layout, animation, data visualization).
- **Threshold**: If the estimated implementation exceeds 3x the baseline for that category, flag as "high effort."
- **Absolute cap**: If the designer estimates more than 5 full dev cycles for a single design spec, it should be split into phases.

This calibration data comes from reading the FE agent's feature tracker history — specifically, the time between `In Progress` and `Pending Test` Discussion entries for shipped features.

### Communicating Feasibility Concerns

The designer should use a **three-tier system** in its design specs:

| Level | Meaning | Action |
|-------|---------|--------|
| **Green** | Feasible within normal effort | Proceed |
| **Yellow** | Feasible but high effort or requires compromises | Designer notes alternatives, PM/human decides |
| **Red** | Not feasible as designed — requires fundamental redesign or tech stack changes | Designer proposes alternatives, blocks handoff to dev |

This is NOT veto power. The designer does not reject features — it communicates constraints. The PM (and ultimately the human) decides whether to proceed, simplify, or reject.

**Communication format**: Each design spec includes a `## Feasibility Assessment` section at the top:

```markdown
## Feasibility Assessment

- **Overall**: Green / Yellow / Red
- **Estimated Effort**: [N] dev cycles (baseline for this category: [M] cycles)
- **Constraints**:
  - [constraint 1]: [impact and alternative]
  - [constraint 2]: [impact and alternative]
- **Recommendation**: [proceed as-is / simplify X / split into phases / redesign approach]
```

### Partially Feasible Designs

When parts are easy and parts are hard, the designer should:

1. **Split the spec**: Produce a "Phase 1" spec covering feasible parts and a "Phase 2" spec for the hard parts, with clear dependency notes.
2. **Mark per-component feasibility**: Each component/section in the design spec gets its own Green/Yellow/Red rating.
3. **Suggest alternatives for hard parts**: "The animated transition as designed requires a custom shader. Alternative: CSS transition with reduced fidelity. Effort reduction: 3 cycles to 0.5 cycles."

### Feasibility Report

Yes — every design spec should include the feasibility assessment as a mandatory section (not a separate file). This keeps the assessment co-located with the design it evaluates, preventing them from drifting apart. The PM reads this section when deciding whether to approve handoff to dev.

---

## 2. Pipeline Integration — Product Development Flow

### Where the Designer Slots In

The current 5-phase lifecycle is:
```
Phase 1: Research (PM) → Phase 2: Discussion (PM+Human) → Phase 3: Planning (PM) → Phase 4: Execution (Dev) → Phase 5: QA (PM)
```

The designer slots in as a **Phase 3.5** — after PM planning is complete (feature is `Approved`) but before the dev agent picks it up:

```
Approved → [Design Needed?] → YES → Design → Design Review → Dev picks up
                              → NO  → Dev picks up directly (current flow)
```

**Rationale for this position:**
- **After Phase 2 (Discussion)**: The designer needs the locked decisions from CONTEXT.md to know the constraints. Designing before decisions are made wastes effort.
- **After Phase 3 (Planning)**: The designer needs the test plan to understand what "done" looks like for the feature.
- **Before Phase 4 (Dev)**: The dev agent needs the design specs before starting implementation.

**New status values needed:**

| Status | Meaning |
|--------|---------|
| `Design` | Feature has been approved and is assigned to the designer |
| `Design Review` | Designer has produced specs, awaiting PM/human review |

The full status flow becomes:
```
Pending → Planning → Approved → [if design needed] Design → Design Review → Approved (re-enters) → In Progress → Pending Test → Pending Ship → Shipped
```

Wait — that creates an awkward re-entry at `Approved`. Better approach: use a single new status `Design` that sits between `Approved` and `In Progress`:

```
Pending → Planning → Approved → Design → In Progress → Pending Test → Pending Ship → Shipped
```

For features that do NOT need design, the flow is unchanged — they go directly from `Approved` to `In Progress` when a dev agent picks them up. PM sets a `design: needed` flag in the feature's metadata when routing.

### Who Decides If Design Is Needed

**PM decides during Feature Intake (Phase 2 Discussion)**. This is natural — the PM is already discussing scope with the human and can ask: "Does this feature need design work?" The decision is recorded in CONTEXT.md as a locked decision.

**Auto-detection heuristics** (PM can use these as suggestions, human confirms):
- Feature description mentions UI, visual, layout, component, animation, responsive → suggest design needed
- Feature is backend-only, config change, template change, internal tooling → suggest no design needed
- FE agent is listed as owner → higher likelihood of design need
- No FE agent exists in the team → design not applicable

**Config flag**: Features get a `- **Design**: needed / not-needed` field. PM sets this during Phase 2.

### Handoff Format: Designer to Dev

The designer produces structured specs in `.squidsquad/designer/specs/FEAT-[ROLE]-XXX/`:

```
.squidsquad/designer/specs/FEAT-FE-042/
  design-spec.md          # Main spec: component hierarchy, layout, interactions, states
  tokens.md               # Design tokens: colors, spacing, typography, shadows (if changed)
  assets.md               # Asset manifest: icons, images, with source references
  feasibility.md          # OR embedded in design-spec.md as a section
```

The `design-spec.md` format:

```markdown
# Design Spec — FEAT-FE-042: [Title]

## Feasibility Assessment
[as described above]

## Component Hierarchy
- [Component tree with props, states, and responsibilities]

## Layout
- [Grid/flex specifications, breakpoints, responsive behavior]

## Interactions
- [User interactions, state transitions, animations]

## Visual States
- [Loading, empty, error, success states for each component]

## Design Tokens (if new/changed)
- [Color, spacing, typography tokens referenced by this design]

## Assets
- [Required assets with source tool references]

## Notes for Dev
- [Implementation hints, gotchas, suggested approach]
```

### Feedback Loop

**Dev finds design impractical during implementation:**
1. Dev appends a Discussion entry on the feature: `> designer produced spec X but [specific problem]. Requesting design revision.`
2. Dev updates feature status from `In Progress` back to `Design`.
3. Designer picks it up next cycle, reads the feedback, revises the spec.
4. Status goes back to `In Progress` (or `Approved` if the redesign is substantial).

**PM rejects design during Design Review:**
1. PM appends Discussion entry with specific concerns.
2. PM updates status from `Design Review` back to `Design`.
3. Designer revises.

This mirrors the existing `Pending Test` → `In Progress` rejection loop.

---

## 3. Quality Gate for Design Inputs

### Minimum Information for a Design Request

A design request is a feature that has `Design: needed` set. By the time it reaches the designer, it has already passed through PM's 5-phase intake (Phases 1-3), so it already has:

- **RESEARCH.md**: Codebase impact, side effects, constraints
- **CONTEXT.md**: Locked decisions from human discussion
- **TEST-PLAN.md**: Acceptance criteria and test cases

The designer should validate that CONTEXT.md contains sufficient design-relevant information:

| Required | Field | Source |
|----------|-------|--------|
| Yes | User story / use case | CONTEXT.md |
| Yes | Target platform(s) | config.md (framework info) |
| Yes | Existing patterns to follow or break | RESEARCH.md |
| Recommended | Visual references or inspiration | CONTEXT.md or Discussion |
| Recommended | Constraints (accessibility, performance, brand) | CONTEXT.md |
| Optional | Wireframes or sketches | External tool or Discussion attachment |

### Pre-Screening

PM pre-screens implicitly during the 5-phase intake. The designer does NOT receive raw human requests — it only receives features that have completed Planning (Phase 3). This is the quality gate.

If the designer finds insufficient information after reading the planning artifacts, it:
1. Appends a Discussion entry: `> [YYYY-MM-DD HH:MM] **designer**: Design info incomplete. Need: [specific missing items]. Requesting PM clarification.`
2. Updates status to `Design` (keeps it there, does not produce a spec).
3. PM reads this on next cycle and either fills the gap (appending to CONTEXT.md) or asks the human.

### Design Brief Template

Rather than a separate template, the PM should add a `## Design Brief` section to CONTEXT.md during Phase 2 when `Design: needed` is set:

```markdown
## Design Brief

- **User Story**: [As a ..., I want ..., so that ...]
- **Target Platforms**: [web/mobile/desktop, responsive breakpoints]
- **Existing Patterns**: [reference existing components/pages to match or diverge from]
- **Visual References**: [links, screenshots, or descriptions]
- **Constraints**: [accessibility requirements, performance budget, brand guidelines]
- **Priority**: [visual polish vs. speed of implementation]
```

PM is prompted to fill this during Phase 2 Discussion when the feature is flagged as design-needed.

---

## 4. Designer Ralph Loop

### Cycle Structure

```
Step 1 — Pull Latest (same as dev)
Step 1b — Context Pressure Check (same as dev)
Step 1c — Resume From Working State (same as dev)
Step 2 — Check Design Requests
  - Read all dev agent features/INDEX.md files
  - Find features with status `Design` (or `Approved` + `Design: needed` if no separate status)
  - For each: read planning artifacts (RESEARCH.md, CONTEXT.md, TEST-PLAN.md)
  - Validate design brief completeness (see Quality Gate above)
Step 3 — Assess Feasibility
  - Read codebase: existing components, design system, framework constraints
  - Check design tool (if connected): fetch latest design from Figma/Stitch
  - Rate feasibility: Green/Yellow/Red per component
  - If Red: propose alternatives in Discussion, do not produce full spec
Step 4 — Produce/Update Design Specs
  - Generate design-spec.md, tokens.md, assets.md
  - If updating (feedback from dev): revise based on Discussion feedback
  - Update feature status to `Design Review` (if new spec) or leave as `Design` (if WIP)
Step 5 — Sync Design Tool (if connected)
  - Push any locally-produced tokens/specs back to the design tool (if API supports it)
  - Pull any updated assets/exports
Step 6 — Log Iteration (same as dev)
Step 7 — Commit and Push (same as dev)
```

### External Tool Integration

**When a design tool is connected (via MCP or API):**

The designer reads a `## Design Tools` section in config.md:

```markdown
## Design Tools

- **Tool**: Figma
- **Access**: mcp (tool name: figma_mcp)
- **Project/File ID**: [Figma file key]
```

Or:
```markdown
## Design Tools

- **Tool**: Google Stitch
- **Access**: mcp (tool name: stitch_mcp)
```

The designer template includes tool-agnostic instructions:
- "If a design tool is configured, use it to fetch the latest component designs for the feature."
- "Use the tool to export design tokens (colors, spacing, typography) in a structured format."
- "If the tool supports annotations/comments, read them for additional designer intent."

The specific MCP tool calls are not hard-coded in the template — the designer agent discovers available tools at runtime via the MCP tool list and matches them against the configured tool name.

**When no design tool is connected (manual mode):**

The designer works entirely from text descriptions, Discussion entries, and any referenced URLs. It produces the same structured specs but notes `Source: manual (no design tool connected)` in the spec header. This is the baseline mode and must work for all projects.

### Multiple Concurrent Design Requests

Same approach as dev agents: pick the highest-priority request first, work it to completion (or block on feedback), then pick the next one. The designer does NOT work multiple designs in parallel within a single cycle — it follows the single-task working state pattern.

If multiple features are in `Design` status, the designer picks the highest-priority one. Others wait. This is intentional — design quality degrades with context-switching.

---

## 5. Codebase Impact

### Files Touched

| File | Change |
|------|--------|
| `references/agent-instructions.md` | Add Template 4 (Designer Agent) with full Ralph Loop |
| `SKILL.md` | Update architecture diagram, roles table, setup flow (Step 1 fields, Step 4a/4b template generation), file structure, tracker formats, Ralph Loop description |
| `.squidsquad/config.md` schema | Add `Design Tools` section, add `designer` to agent types |
| PM template (Template 2) | Add design routing logic in Feature Intake Phase 2, add `Design` status handling in verification steps |
| Dev template (Template 1) | Add "read design specs before implementing" in Step 3 for design-needed features |
| Setup flow (SKILL.md Step 1) | Add designer role detection, design tool configuration prompt |
| Setup flow (SKILL.md Step 4) | Add Template 4 generation for designer role |

### New Files

| File | Purpose |
|------|---------|
| `references/agent-instructions.md` Template 4 section | Designer agent template (within existing file) |
| `.squidsquad/designer/` directory structure | Created at setup when designer role is added |
| `.squidsquad/designer/specs/` | Design spec output directory |
| `.squidsquad/templates/designer-agent.md` | Compiled template (generated at setup) |
| `start-designer.sh` / `start-designer.ps1` | Boot scripts |

### Sub-Skill Architecture Fit (FEAT-SKILL-030)

Under the sub-skill architecture, the designer becomes:
```
references/sub-skills/
  roles/
    designer/
      ralph-loop.md        # Designer-specific Ralph Loop steps
      responsibilities.md  # Designer responsibilities section
      design-tools.md      # Design tool integration instructions
      feasibility.md       # Feasibility assessment protocol
      spec-format.md       # Design spec output format
```

These compose into `references/agent-instructions.md` Template 4 (or a separate `designer-agent-template.md`) at build time. The composition uses the same `<!-- sub-skill: [name] -->` markers as other role templates.

**If FEAT-SKILL-030 is not yet implemented**: Build the designer template monolithically in `references/agent-instructions.md` as Template 4, matching the pattern of Templates 1-3. When sub-skills land, it gets decomposed like the others.

### Config Changes

New section in `config.md`:

```markdown
## Design Tools

- **Tool**: [none / Figma / Google Stitch / custom]
- **Access**: [none / mcp / api]
- **Tool Name**: [MCP tool name, if applicable]
- **Project ID**: [design tool project/file identifier, if applicable]
```

New field on features:
```markdown
- **Design**: needed / not-needed
```

New agent type recognition in setup:
- If role name is `designer` or user selects "Designer" template type, use Template 4 instead of Template 1.

### Setup Flow Changes

**Step 1 additions:**
- Field 3 (Dev agents): If one of the roles is `designer`, auto-detect and use Template 4. Alternatively, add a new field: "Template type: Dev / Designer" per role.
- New field: "Design tool" — prompted only if a designer role exists. Options: Figma, Google Stitch, Other (MCP), None.

**Step 4 additions:**
- Generate Template 4 for designer role.
- Generate bootstrapper `.squidsquad/designer/CLAUDE.md`.
- Create `.squidsquad/designer/specs/` directory.

---

## 6. Side Effects

- **Risk 1**: PM template complexity increase — PM must now handle `Design: needed` routing, `Design` and `Design Review` statuses, design brief generation, and designer feedback loops. — Severity: **M** — Mitigation: Keep the routing logic simple (a flag check + status transition). The PM template is already the largest; consider this when estimating template size constraints from FEAT-SKILL-030 CONTEXT.md (600 lines max).

- **Risk 2**: Feature pipeline latency — Adding a design phase between Approved and In Progress adds at least one cycle of delay per design-needed feature. — Severity: **L** — Mitigation: Only features explicitly flagged as `Design: needed` go through the designer. Most features skip it entirely. The designer can also fast-track simple design requests within a single cycle.

- **Risk 3**: Dev template reading design specs from wrong location — If the spec directory structure changes or the designer uses a different path convention, dev agents will not find the specs. — Severity: **M** — Mitigation: Standardize the path in config.md or use a fixed convention (`.squidsquad/designer/specs/FEAT-[ROLE]-XXX/design-spec.md`). Dev template references this exact path pattern.

- **Risk 4**: Designer agent consuming excessive context reading design tool exports — Large Figma files or complex design systems could overwhelm the context window. — Severity: **M** — Mitigation: Designer should scope tool reads to the specific feature's components, not the entire design file. Context pressure check (Step 1b) provides the safety net.

- **Risk 5**: Circular dependency — Dev sends feature back to Design, designer revises, dev rejects again. — Severity: **L** — Mitigation: After 2 round-trips, the designer should escalate to PM/human via Discussion entry. PM mediates and can force-approve or reject.

---

## Edge Cases

- **No FE agent exists**: The designer produces specs, but no agent consumes them. The designer template should detect this from config.md and warn in Discussion. The human (or a non-FE dev agent) can still read the specs manually. Not a blocker — the designer is useful even without an FE agent (e.g., producing specs for a human developer).

- **Designer role but no design tool**: This is the "manual mode" baseline. The designer works from text descriptions, produces structured specs without fetching from external tools. The `Design Tools` config section shows `Tool: none`. Template instructions handle this gracefully.

- **Feature flagged Design: needed but designer agent is not running**: PM routes to `Design` status, but nobody picks it up. PM's agent health check (Step 7) would flag the designer as stalled. The feature sits in `Design` status indefinitely until the designer starts or the human manually moves it to `Approved` (bypassing design).

- **Multiple dev agents with one designer**: The designer serves all dev agents, not just FE. If a `be` feature needs API design (e.g., endpoint structure), the designer can produce API design specs too. The spec directory uses the feature's `ROLE` prefix to route specs to the right agent.

- **Designer self-files bugs**: The designer may discover design system inconsistencies or missing tokens while assessing feasibility. These should be filed as bugs or features to the relevant dev agent's tracker, following the existing cross-filing protocol.

- **Design spec references external assets (images, fonts)**: The spec can reference URLs or paths, but the designer should not download/commit large binary assets. Instead, it lists asset references with source URLs. The dev agent fetches them during implementation.

- **Projects with no UI**: The designer role simply is not added during setup. If someone adds it anyway, the designer will find no `Design: needed` features and run quiet cycles indefinitely. No harm, just wasted resources.

- **Existing installs adding designer later**: User runs `/squidsquad-upgrade`, which detects the new role in config.md, creates `.squidsquad/designer/` directory structure, generates the template, and creates boot scripts. Same pattern as adding a new dev agent. See Upgrade section.

---

## Integration Risks

- **FEAT-SKILL-030 (Sub-skill architecture)**: The designer template should be built to be decomposable. If sub-skills ship first, designer is built as sub-skills from day one. If designer ships first, it is built monolithically and decomposed when sub-skills land. Either order works — no hard dependency.

- **PM template size**: The PM template is already the largest (~600 lines per FEAT-SKILL-030 CONTEXT.md). Adding design routing logic adds approximately 40-60 lines. This is within tolerance but should be monitored.

- **Feature status flow**: Adding `Design` status affects every agent that reads feature statuses. Dev agents currently look for `Approved` — they must continue to do so (design-needed features exit the design phase back to `Approved` or use a different signal). Recommendation: Use `Approved` as the only status dev agents check, and have the designer transition features from `Design` back to `Approved` (with design specs attached) when done. This avoids changing dev templates.

  Wait — this creates ambiguity. A feature at `Approved` could be waiting for design or ready for dev. Better: use `Design` as a status that precedes `In Progress`. Dev agents check for `Approved` and also check if `Design: needed` — if yes and design specs do not exist yet, skip it. If design specs exist, pick it up.

  Simplest approach: **The designer moves the feature from `Design` to `Approved` when done.** Dev agents see `Approved` exactly as today. PM moves it from `Approved` to `Design` when the designer should pick it up, and the designer moves it back to `Approved` when specs are ready. This reuses `Approved` with no dev template changes.

  Revised flow:
  ```
  Planning → Approved → (PM sees Design:needed, moves to Design) → Design → (designer completes, moves back to Approved) → In Progress → ...
  ```

  This means `Approved` is visited twice for design-needed features. The Discussion log makes the sequence clear. Dev agents are unaffected.

- **Cross-agent spec directory**: `.squidsquad/designer/specs/` is owned by the designer but read by dev agents. This is a new cross-agent read pattern (currently, agents only cross-read tracker Discussion entries and bugs). The path must be standardized and documented.

---

## Upgrade & Migration

- **New config values**:
  - `## Design Tools` section with `Tool`, `Access`, `Tool Name`, `Project ID` fields (all defaulting to `none`)
  - `Design: needed / not-needed` field on features (optional — defaults to `not-needed` if absent)

- **New files**:
  - `.squidsquad/designer/CLAUDE.md` (bootstrapper)
  - `.squidsquad/designer/bugs/INDEX.md` + `archived/`
  - `.squidsquad/designer/features/INDEX.md` + `archived/`
  - `.squidsquad/designer/iterations/`
  - `.squidsquad/designer/specs/`
  - `.squidsquad/designer/working-state.md`
  - `.squidsquad/templates/designer-agent.md`
  - `.squidsquad/start-designer.sh` + `.squidsquad/start-designer.ps1`
  - Template 4 section in `references/agent-instructions.md`

- **Template changes**:
  - PM template: Add `Design` status handling in verification steps, add design brief prompt in Phase 2 when `Design: needed`
  - Dev template: Add "check for design specs" note in Step 3 (optional — dev agents work fine without it, they just implement from acceptance criteria as today)
  - New Template 4: Full designer agent Ralph Loop

- **Upgrade steps** (`/squidsquad-upgrade`):
  1. Detect if `designer` role exists in config.md `Dev Agents` list.
  2. If yes and `.squidsquad/designer/` does not exist: create directory structure, generate template and bootstrapper, create boot scripts.
  3. If `## Design Tools` section is missing from config.md: add it with defaults (`Tool: none`).
  4. Regenerate PM template with design routing logic.
  5. Add `BUG-DESIGNER` and `FEAT-DESIGNER` counters to config.md if missing.

- **Graceful degradation**:
  - If designer role is NOT in config.md: no changes, no impact. The feature is invisible.
  - If designer role is in config.md but `.squidsquad/designer/` does not exist: `/squidsquad-upgrade` creates it. Until then, PM routes features to `Approved` directly (skipping design) since no designer is available.
  - If `Design Tools` config section is missing: designer operates in manual mode.
  - Existing features without `Design: needed` field: treated as `not-needed` (default). No retroactive changes needed.

---

## Open Questions

- **Q1**: Should the designer have its own bug/feature tracker, or should it use the FE agent's tracker? — **Why**: If the designer has its own tracker, PM must file design-specific bugs there. If it shares with FE, design bugs and code bugs are mixed in one tracker. Recommendation: own tracker (`.squidsquad/designer/bugs/`) for design-related issues (spec revisions, token conflicts), but design specs for FE features live in the FE feature's Discussion and linked spec files.

- **Q2**: Should `Design` be a feature status or a separate workflow tag? — **Why**: Adding a status changes the status flow for ALL features (even if most skip it). A tag/flag (`Design: needed`) with status remaining `Approved` is less disruptive. The "Approved → Design → Approved" pattern described in Integration Risks may confuse agents reading status history. Need human decision on which approach.

- **Q3**: Should the designer agent be autonomous (looping) or on-demand (spawned by PM when needed)? — **Why**: An autonomous designer running every 30 minutes when there are no design requests wastes a Claude session. An on-demand designer spawned only when `Design` features exist is more efficient but adds PM complexity. The DM precedent suggests autonomous is the pattern, but the DM has more frequent work (every shipped feature). The designer may have long idle periods.

- **Q4**: What is the naming convention — is the role always called `designer`, or can the user name it anything and select "Designer template"? — **Why**: If always `designer`, the setup flow auto-detects it like PM. If user-named, setup needs a template-type selector ("Dev template" vs "Designer template"). The DM is always called `dm` — following this pattern, the designer would always be called `designer`.

- **Q5**: Does the designer own design tokens globally, or only per-feature? — **Why**: If globally, the designer maintains a `design-system/` directory with canonical tokens that all features reference. If per-feature, tokens are scoped to each feature spec. Global ownership is more powerful but adds maintenance burden and conflict potential with existing FE code.

- **Q6**: How should the designer handle design tool authentication? — **Why**: MCP tools handle auth via the MCP connection config, but API-based tools may need tokens/keys. These should NOT be stored in config.md (committed to git). Need a `.squidsquad/.local-config` or environment variable pattern for secrets.

---

## Recommendation

**Feasible with caveats.**

The designer agent follows the established template pattern and does not require architectural changes — it is a new template alongside the existing three. The main caveats are:

1. **Pipeline integration needs a clear decision** on whether `Design` is a status or a routing flag (Q2). The "Approved → Design → Approved" round-trip is workable but needs to be explicitly documented to avoid agent confusion.

2. **The PM template is already at size limits.** Adding design routing logic must be minimal. Consider extracting design-specific PM logic into a sub-section or (under sub-skills) a separate sub-skill file.

3. **On-demand vs. autonomous (Q3)** has significant cost implications. Recommend starting as autonomous (matching the DM pattern) and adding idle detection later — if the designer runs 5 quiet cycles in a row, it logs "No design work pending — consider stopping the designer agent" in its iteration log.

4. **The feature should be implemented in two phases:**
   - **Phase A**: Template + manual mode + pipeline integration (no external tool dependency)
   - **Phase B**: External tool integration (Figma MCP, Stitch, etc.) — requires testing with real tool connections

5. **Q4 (naming)**: Recommend the role is always called `designer` (matching `pm` and `dm` as fixed role names). This simplifies detection and template routing.

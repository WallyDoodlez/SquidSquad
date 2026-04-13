# FEAT-SKILL-462 Research — Adaptive Setup Questions

## Summary

The current wizard flow (WIZARD.md Steps 1-5) collects project context through a rigid, manifest-driven sequence: Step 1 gets project name/repo, Step 2 classifies intent (software-dev vs design), Step 3 confirms the preset, Step 4 walks each role's `setup_requirements` (dev variant, dev stack, designer opt-in), and Step 5 asks loop interval + context threshold. Nowhere in this flow does the wizard ask "What does your project do?" or gather domain context that would seed SOUL.md or inform capability sub-skill selection. The setup captures mechanical config (stack, variant, interval) but zero semantic understanding of the project — what it does, who it serves, what conventions matter, what external tools are in play.

This feature introduces an adaptive 3-question conversational block that bootstraps project understanding early in the wizard, before the mechanical per-role questions. Q1 is fixed ("What does your project do?"), Q2 and Q3 are inferred from previous answers. The answers feed three outputs: `config.md` (project description, test commands, conventions), SOUL.md seeding (domain context for each agent), and capability sub-skill detection (if user mentions Figma, auto-assign the figma sub-skill to the designer role). The approach is primarily a WIZARD.md prose change with minor wizard.py support for the new `project.description` field.

Primary risks: (1) the wizard already captures project description from `gh repo view` in Step 1 — the adaptive questions must supplement, not duplicate; (2) SOUL.md seeding is currently empty at scaffold time — a new mechanism is needed to inject project context into the default SOUL.md; (3) capability sub-skill auto-assignment from free-text answers requires the wizard agent to match keywords against the capability manifest registry, which is a prompt-engineering task in WIZARD.md, not a code task.

## Impact Analysis

- **Files touched**:
  - `references/wizard/WIZARD.md` — primary change: new Step 1b (adaptive questions block) between current Steps 1 and 2, plus updates to Step 7 for SOUL.md seeding
  - `references/scripts/wizard.py` — minor: extend `build_config_md` spec to include `project.description`, `project.domain_context`, `project.conventions`; extend `scaffold_install` to write seeded SOUL.md content
  - `references/roles/*/SOUL.md` — templates may gain a `### Project Context` section placeholder that the wizard populates
  - `references/sub-skills/capabilities/*/manifest.yaml` — no changes, but the wizard agent reads `display_name` and `description` fields to match against user answers
  - `references/scripts/manifest.py` — no changes needed; the wizard already calls `manifest.py load capabilities <id>` to inspect manifests

- **Behavior changes**:
  - Wizard gains a new conversational block (Step 1b) between project detection (Step 1) and intent classification (Step 2)
  - The wizard asks 3 questions minimum, up to 5 if answers are vague
  - Answers populate `project.description` in config.md (new field, already supported in `build_config_md` but never populated by the wizard)
  - SOUL.md files are seeded with project-specific context at scaffold time (currently SOUL.md is copied verbatim from role templates)
  - Capability sub-skills may be pre-selected based on answers (e.g., "we use Figma" triggers designer.tool=figma in the install spec)

- **Dependencies**:
  - #401 (capability sub-skills) — the adaptive questions feed capability detection, which uses the sub-skill manifest registry established by #401
  - No new external dependencies

## Current Setup Flow Analysis

### What the wizard currently asks (Steps 1-5):

| Step | Question | Info Captured | Stored In |
|------|----------|---------------|-----------|
| 1 | Project name/repo confirmation | `project.name`, `project.repo` | config.md `## Project` |
| 2 | Free-text intent ("what are you building?") | Preset classification (software-dev/design) | config.md `## Preset` |
| 3 | Pipeline confirmation (y/n/a) | Validated preset | In-memory |
| 4 | Per-role setup_requirements walker | dev.variant, dev.stack, designer.install_optional | config.md `## Agents` per-agent `setup:` |
| 5 | Loop interval + context threshold | interval_minutes, context_threshold | config.md `## Loop` |

### What is missing:

- **Project description**: `build_config_md` already supports `project.description` (line 516-517 of wizard.py) but the wizard never collects it. `gh repo view` returns a `description` field, but this is typically a one-liner, not domain context.
- **Tech stack** (for non-dev roles): The wizard asks dev agents about stack via `setup_requirements`, but PM and QA have no way to know the project domain, conventions, or constraints.
- **Test commands** (beyond per-agent): E2E test commands are not gathered during setup — they show as `(none)` in config.md.
- **External tools**: The wizard does not ask about design tools, CI systems, or external integrations. Designer tool assignment happens "on first use" per current flow.
- **Conventions/constraints**: No mechanism to capture coding style, branching strategy, or project-specific rules.
- **SOUL.md seeding**: SOUL.md files are copied verbatim from `references/roles/*/SOUL.md` templates. They contain generic role identity text but zero project-specific context.

## Where Questions Fit in the Flow

The adaptive questions should be a new **Step 1b** — after project name/repo detection (Step 1) but before intent classification (Step 2).

**Rationale**:
- Step 1 gives us the project name and repo URL — the wizard can use these as context when asking Q1
- The answers to the adaptive questions directly inform Step 2 (intent classification) — if the user says "it's a CLI tool for data processing," the classifier already knows it's software-dev
- The answers also pre-fill information that Step 4 would otherwise ask about (stack, tools) — the wizard can skip redundant questions
- Asking after Step 2 (intent) would be too late — the adaptive questions should INFORM intent classification, not follow it

**Flow with the new step**:

```
Step 0  — Prerequisite check (gh CLI)
Step 0b — Re-run detection
Step 1  — Project details (name, repo)
Step 1b — Adaptive context questions (NEW)    ← Q1, Q2, Q3
Step 2  — Intent + specialist roster           ← informed by 1b answers
Step 3  — Preset confirmation
Step 4  — Walk setup_requirements              ← skip questions already answered in 1b
Step 5  — Loop interval
Step 6  — Review screen
Step 7  — Commit and write                     ← SOUL.md seeded with 1b context
```

## Implementation Approach

### Primary: WIZARD.md prose changes

The adaptive questions are driven by Claude's reasoning, not by code. The WIZARD.md runbook gets a new Step 1b section with:

1. **Question framework**: Define WHAT info to gather, not exact wording
2. **Q1 (fixed)**: "What does your project do?" — always asked
3. **Q2 (inferred)**: Based on Q1, Claude picks the most relevant follow-up. The runbook lists info categories to fill (tech stack, test commands, external tools, conventions) and instructs Claude to ask about whichever is most relevant given Q1's answer
4. **Q3 (inferred)**: Based on Q1+Q2, Claude asks about remaining blind spots. The runbook lists a "stop condition" — stop when you can populate config.md project fields + seed SOUL.md
5. **Escalation**: If answers are vague after Q3, allow up to 2 more questions (Q4, Q5) before moving on with whatever was gathered
6. **Multi-part OK**: Each question can be multi-part ("What's your tech stack and how do you run tests?") to cover more ground efficiently

**Info categories the wizard should gather** (from the runbook, not exact questions):
- What the project does (domain, purpose, users)
- Tech stack (languages, frameworks, package managers)
- Test commands (unit tests, E2E tests, lint)
- External tools (design tools, CI, deployment targets)
- Conventions/constraints (coding style, branching, PR requirements)
- Project structure (monorepo? separate FE/BE? microservices?)

**Claude infers which are relevant**: A CLI data-processing tool does not need design tool questions. A React app does not need backend framework questions. The runbook says "ask about the categories that are relevant to the project type described in Q1."

### Secondary: wizard.py changes

Minor additions to support the new data:

1. **Extend install spec schema**: Add `project.description` (already supported), `project.domain_context` (new — free-text summary for SOUL.md seeding), `project.conventions` (new — list of constraints/rules)
2. **Extend `build_config_md`**: Render new project fields if present
3. **Extend `scaffold_install`**: When writing SOUL.md, if `project.domain_context` is provided, append a `### Project Context` section to the role's default SOUL.md template content

### How Claude "infers" the next question

Pure prompt engineering in WIZARD.md. The runbook describes:

```
After Q1, classify the project along these axes:
- Has frontend? (web, mobile, desktop UI)
- Has backend? (API, server, database)
- Uses external design tools? (Figma, Sketch, etc.)
- Has tests? (did the user mention testing?)
- Has CI/CD? (did the user mention deployment?)

For Q2, ask about the largest remaining gap. If the project has a
frontend but the user didn't mention the framework, ask about that.
If the project mentions "we use Figma," don't ask about design tools.

For Q3, ask about whatever remains unknown. If you already know
stack + tests + tools, ask about conventions/constraints.
```

No classifier code needed — Claude reasons about it inline.

## Integration with #401 (Capability Sub-Skills)

### How answers feed capability sub-skill assignment

The wizard agent already loads capability manifests via `manifest.py load capabilities <id>`. The #462 addition:

1. During/after the adaptive questions, the wizard scans answers for capability keywords
2. The wizard reads all capability manifests and matches against answer text
3. If a match is found, the wizard pre-selects the capability for the relevant role

**Example flow**:
- User says in Q1: "It's a React app, we design in Figma"
- Wizard detects "Figma" → loads `references/sub-skills/capabilities/figma/manifest.yaml` → sees `applicable_roles: [designer]`
- Wizard pre-fills `tools.designer.tool = "figma"` in the install spec
- When reaching Step 4 (setup_requirements), the designer's tool setup is already pre-answered

**Implementation**: WIZARD.md prose only. The runbook tells the wizard agent:

```
After the adaptive questions, scan the user's answers for references
to known capability sub-skills. For each capability in the registry
(python references/scripts/manifest.py list capabilities), check if
the user mentioned it by name or by category. If found, pre-select
it for the applicable role. Show the pre-selection in the Step 6
review screen for confirmation.
```

### Current capabilities in the registry:

| ID | Category | Applicable Roles | Keyword triggers |
|----|----------|------------------|------------------|
| figma | design | designer | "Figma", "design in Figma" |
| google_stitch | design | designer | "Google Stitch", "Stitch" |
| local_html | design | designer | (fallback — always available) |
| local_delivery | delivery | dm | (default for local delivery) |

The keyword matching is Claude's judgment call, not regex — the runbook instructs the agent to use common sense when matching.

## Side Effects

- **Risk 1**: Duplicated questions between Step 1b and Step 4 — Severity: M — Mitigation: WIZARD.md instructs the agent to track what info was already gathered in Step 1b and skip redundant setup_requirements questions in Step 4. The runbook says "if the user already described their stack in the adaptive questions, pre-fill dev.stack and confirm rather than asking from scratch."

- **Risk 2**: Over-questioning (wizard feels like a survey) — Severity: M — Mitigation: Hard cap at 5 questions. Multi-part questions allowed. Stop condition: "stop as soon as you can populate config.md + seed SOUL.md." The tone section already says "not a form, not a robot."

- **Risk 3**: SOUL.md seeding creates merge conflicts on upgrade — Severity: L — Mitigation: `scaffold_install` already preserves existing SOUL.md files (`soul_path` is never overwritten if it exists, per line 752-753 of wizard.py). Seeding only happens on fresh install.

- **Risk 4**: Capability auto-detection false positives — Severity: L — Mitigation: Auto-detected capabilities are shown in the Step 6 review screen. The user can edit (Step 6 [E] option) before proceeding. No silent assignment.

- **Risk 5**: Answers too vague to populate anything — Severity: L — Mitigation: The wizard moves on after 5 questions max. SOUL.md gets whatever was gathered. Empty fields remain empty — agents operate with generic defaults, same as today.

## Edge Cases

- **User says "I don't know" or gives one-word answers**: Wizard exhausts its 5-question budget, captures whatever it can, moves on. SOUL.md seeding is best-effort.

- **User describes a project that doesn't fit software-dev or design**: The adaptive questions happen before intent classification. If the answers are ambiguous, they feed into Step 2's classifier with additional context, making classification easier.

- **Re-run / regenerate flow**: Step 0b `regenerate` skips Steps 1-6 entirely, so adaptive questions don't apply. `full-rebuild` goes through the full flow including the new Step 1b.

- **Repo already has project description from gh**: Q1 can be pre-filled: "I see this repo is described as '[gh description]'. Can you tell me more about what it does?" — richer than starting from zero.

- **Multi-tool projects**: User says "we use Figma and deploy to AWS." Wizard detects Figma (capability sub-skill) but AWS is not in the registry. It notes the Figma match and ignores unrecognized tools. Future capability sub-skills can be detected the same way.

- **Wizard re-run on a project that already has seeded SOUL.md**: `scaffold_install` never overwrites existing SOUL.md (line 752-753). The seeding only applies to fresh installs.

## Integration Risks

- **Dependency on #401**: The capability auto-detection relies on the sub-skill manifest registry from #401. If #462 ships before #401, the auto-detection section of WIZARD.md references capabilities that don't exist yet. Mitigation: capability detection is additive — if the registry is empty or uses the old `tools` layout, the wizard simply finds no matches and skips auto-detection.

- **WIZARD.md size**: Adding a new step increases the already-large WIZARD.md (500 lines). The new step should be concise — 40-60 lines of prose — to stay within the doc's readability budget.

- **Interaction with future "project onboarding" features**: If a more sophisticated onboarding flow is planned later, the adaptive questions establish a pattern (conversational context gathering) that future features can extend.

## Upgrade & Migration

- **New config values**: `project.description` (already supported in schema, just never populated), `project.domain_context` (new, optional), `project.conventions` (new, optional). All default to empty — existing installs are unaffected.

- **New files**: None for end users. SOUL.md gains a `### Project Context` section on fresh installs only.

- **Template changes**: SOUL.md templates in `references/roles/*/SOUL.md` gain a placeholder `### Project Context` section that the wizard fills at scaffold time. Existing SOUL.md files are never overwritten during upgrade.

- **Upgrade steps**: `/squidsquad-upgrade` re-deploys CLAUDE.md (picks up new wizard instructions) but does not touch SOUL.md. Existing installs keep their current SOUL.md. Users who want project context seeding can manually add a `### Project Context` section to their SOUL.md files, or do a full rebuild.

- **Graceful degradation**: Non-upgraded installs continue working. The adaptive questions are wizard-only — they have no impact on running agents. Agents that lack SOUL.md project context operate exactly as they do today.

## Open Questions

- **Q1**: Should the adaptive questions replace or supplement the `gh repo view` description? — **Why**: If `gh` already gives a good description, Q1 might feel redundant. Recommend: use `gh` description as a starting prompt ("I see this repo is '[description]'. Tell me more.") so Q1 is never purely redundant.

- **Q2**: Should SOUL.md seeding be a new section (`### Project Context`) or integrated into the existing identity sections? — **Why**: A separate section is cleaner and easier for agents to locate, but it adds to SOUL.md length. Recommend: new section — keeps the boundary clear between role identity (static) and project context (per-install).

- **Q3**: Should the wizard store raw answers or processed summaries? — **Why**: Raw answers preserve the user's exact words but may be verbose. Processed summaries are cleaner but risk losing nuance. Recommend: store a processed summary in config.md/SOUL.md, but include the raw exchange in the install spec JSON for traceability.

- **Q4**: How does this interact with multi-preset projects (not yet supported)? — **Why**: If a project is both software-dev and design, the adaptive questions would need to cover both domains. Recommend: out of scope — current architecture supports one preset per install.

## Recommendation

Feasible with low risk. The implementation is primarily a WIZARD.md prose change (~50 lines) with minor `wizard.py` support for the new config fields and SOUL.md seeding. The capability auto-detection is a nice bonus that builds on #401 but degrades gracefully if #401 hasn't shipped yet. The main design decision is where to store the gathered context (config.md vs SOUL.md vs both) — recommend both, with config.md getting structured fields and SOUL.md getting a narrative project context section.

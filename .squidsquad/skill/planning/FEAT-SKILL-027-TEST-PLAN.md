# FEAT-SKILL-027 Test Plan — Designer Agent Role

## Test Cases

### Happy Path

### TC-1: Sub-skill file structure created correctly
- **Precondition**: FEAT-SKILL-030 sub-skill architecture is in place with `references/sub-skills/` directory and composition engine
- **Steps**: Verify all designer sub-skill source files exist at the expected paths
- **Expected**: The following files exist: `references/sub-skills/roles/designer.md` (entry file), plus designer-specific sub-skill files under `references/sub-skills/designer-specific/` covering ralph-loop, responsibilities, design-tools, feasibility, spec-format
- **Verification**: `ls references/sub-skills/roles/designer.md && ls references/sub-skills/designer-specific/`

### TC-2: Composition engine produces designer template
- **Precondition**: Designer sub-skill source files exist; composition engine from FEAT-SKILL-030 is functional
- **Steps**: Run composition/setup flow that generates templates from sub-skills
- **Expected**: A composed designer template is generated (either as Template 4 in `references/agent-instructions.md` or as a separate composed file). Template contains `<!-- sub-skill: ... -->` section markers. Template includes all designer-specific sections (Ralph Loop, feasibility assessment, design tools, spec format)
- **Verification**: `grep "sub-skill:" references/agent-instructions.md` or check the generated template file for section markers; verify the template is non-empty and contains key sections like "Feasibility Assessment" and "Design Tools"

### TC-3: Manifest updated with designer composition order
- **Precondition**: `references/sub-skills/manifest.md` exists
- **Steps**: Read manifest.md and check for designer entry
- **Expected**: Manifest includes a `### Designer Agent` section listing the composition order (entry file `roles/designer.md` with its includes). Placeholder substitution table includes designer-relevant entries
- **Verification**: `grep -i "designer" references/sub-skills/manifest.md`

### TC-4: Tag-based routing — Design: needed field on features
- **Precondition**: A feature file exists (e.g., `FEAT-SKILL-XXX.md`) with `Design: needed` field
- **Steps**: Check that the feature file contains the `Design` metadata field with one of the valid values
- **Expected**: Feature files support `- **Design**: needed / in-progress / complete / not-needed` field. Default for features without the field is `not-needed`
- **Verification**: `grep "Design:" .squidsquad/*/features/FEAT-*.md` on a sample feature

### TC-5: Dev agent skips features where Design is needed or in-progress
- **Precondition**: Dev agent template (Template 1 / dev-agent composed) has been updated; a feature exists with `Design: needed`
- **Steps**: Read the dev agent template and confirm it contains logic to check the `Design` field before picking up a feature
- **Expected**: Dev template includes a check: if `Design` field is `needed` or `in-progress`, skip the feature and move to the next one. Features with `complete` or `not-needed` (or missing field) are picked up normally
- **Verification**: `grep -i "design.*needed\|design.*in-progress\|skip.*design" references/sub-skills/roles/dev-agent.md` or the composed template

### TC-6: PM adds Design Brief to CONTEXT.md for design-needed features
- **Precondition**: PM template has been updated with design routing logic
- **Steps**: Read the PM template (or pm-specific sub-skills) and confirm Phase 2 includes prompting the human about design need and adding a Design Brief section
- **Expected**: PM template includes: (a) during Phase 2 Discussion, ask human if feature needs design; (b) if yes, set `Design: needed` on the feature; (c) add a `## Design Brief` section to CONTEXT.md with user story, target platforms, existing patterns, visual references, constraints, priority
- **Verification**: `grep -i "design brief" references/sub-skills/pm-specific/*.md` or the composed PM template

### TC-7: Designer tracker directory structure
- **Precondition**: Setup or upgrade flow has been run with `designer` in the Dev Agents list
- **Steps**: Check that the designer tracker directory structure exists
- **Expected**: The following directories/files exist: `.squidsquad/designer/bugs/INDEX.md`, `.squidsquad/designer/bugs/archived/`, `.squidsquad/designer/features/INDEX.md`, `.squidsquad/designer/features/archived/`, `.squidsquad/designer/iterations/`, `.squidsquad/designer/specs/`, `.squidsquad/designer/working-state.md`, `.squidsquad/designer/CLAUDE.md`
- **Verification**: `ls -la .squidsquad/designer/ && ls .squidsquad/designer/bugs/ && ls .squidsquad/designer/features/ && ls .squidsquad/designer/specs/`

### TC-8: Designer CLAUDE.md bootstrapper
- **Precondition**: `.squidsquad/designer/CLAUDE.md` exists
- **Steps**: Read the bootstrapper file
- **Expected**: Bootstrapper follows the standard pattern (similar to other role CLAUDE.md files) — points to the compiled designer template, sets role to `designer`
- **Verification**: `cat .squidsquad/designer/CLAUDE.md` — should be a short bootstrapper (<50 lines), not a full template

### TC-9: Designer Ralph Loop cycle — picking up a design-needed feature
- **Precondition**: A feature exists with `Design: needed` and status `Approved`; CONTEXT.md contains a Design Brief; designer template is composed
- **Steps**: Simulate the designer's Step 2 (Check Design Requests) by reading the template instructions
- **Expected**: Designer template instructs: read all dev agent feature INDEX files, find features with `Design: needed`, read their planning artifacts (RESEARCH, CONTEXT, TEST-PLAN), validate Design Brief completeness, then proceed to feasibility assessment
- **Verification**: Read the designer template and confirm it references reading feature trackers and checking the `Design` field

### TC-10: Feasibility assessment in design spec output
- **Precondition**: Designer template includes feasibility assessment protocol
- **Steps**: Read the spec-format sub-skill or relevant template section
- **Expected**: Design spec format includes a mandatory `## Feasibility Assessment` section with: Overall rating (Green/Yellow/Red), Estimated Effort (N dev cycles with baseline), Constraints list, Recommendation. Per-component feasibility ratings are supported for partially feasible designs
- **Verification**: `grep -i "feasibility" references/sub-skills/designer-specific/*.md`

### TC-11: Real-time interactive design session
- **Precondition**: Designer template includes interactive session instructions
- **Steps**: Read the designer Ralph Loop step that handles `Design: needed` features
- **Expected**: When designer picks up a feature, it enters interactive mode — presents design options to the human, iterates in real-time, blocks the loop until human approves the design. Analogous to PM Phase 2 blocking behavior. Human approval is required before transitioning the feature's Design field to `complete`
- **Verification**: Read designer template for references to interactive session, human approval, and loop blocking

### TC-12: Design spec output directory and format
- **Precondition**: Designer has completed a design and produced specs
- **Steps**: Verify spec output path follows the standardized convention
- **Expected**: Specs are placed in `.squidsquad/designer/specs/FEAT-[ROLE]-XXX/` with at minimum a `design-spec.md`. The spec contains sections: Feasibility Assessment, Component Hierarchy, Layout, Interactions, Visual States, Design Tokens, Assets, Notes for Dev
- **Verification**: `ls .squidsquad/designer/specs/` after a design cycle

### TC-13: Design field transitions — full happy path
- **Precondition**: Feature starts with `Design: not-needed` or no Design field
- **Steps**: Trace the full lifecycle: PM sets `Design: needed` during Phase 2 -> designer picks up, sets `Design: in-progress` -> designer completes + human approves, sets `Design: complete` -> dev agent sees `complete` and picks up feature
- **Expected**: Each transition is reflected in the feature file's Design field. Discussion entries document each transition. Dev agent only picks up after Design is `complete` (or `not-needed`)
- **Verification**: Read feature file at each stage and confirm Design field value

### TC-14: MCP/CLI tool integration with manual fallback
- **Precondition**: config.md has a `## Design Tools` section
- **Steps**: (a) Test with `Tool: none` — designer operates in manual mode. (b) Test with a configured MCP tool — designer attempts to use it
- **Expected**: (a) Manual mode: designer produces specs from text descriptions only, notes `Source: manual (no design tool connected)` in spec header. (b) MCP mode: designer discovers tools at runtime, uses configured tool name to fetch designs/tokens
- **Verification**: (a) Check spec header for manual source note. (b) Check template for MCP tool discovery instructions

### TC-15: Config.md updated with Design Tools section and counters
- **Precondition**: Upgrade or setup has been run
- **Steps**: Read config.md
- **Expected**: config.md contains `## Design Tools` section with fields: Tool, Access, Tool Name, Project ID (defaults to `none`). ID Counters section contains `BUG-DESIGNER` and `FEAT-DESIGNER` entries
- **Verification**: `grep "Design Tools\|BUG-DESIGNER\|FEAT-DESIGNER" .squidsquad/config.md`

### TC-16: Boot scripts generated for designer
- **Precondition**: Setup or upgrade completed with designer role
- **Steps**: Check for designer boot scripts
- **Expected**: `start-designer.sh` and `start-designer.ps1` (or equivalent under `.squidsquad/`) exist and follow the same pattern as other agent boot scripts, pointing to the designer CLAUDE.md bootstrapper
- **Verification**: `ls .squidsquad/start-designer.* || ls start-designer.*`

### TC-17: Autonomous loop with idle detection
- **Precondition**: Designer template includes idle detection logic
- **Steps**: Read the designer template for idle cycle handling
- **Expected**: After 5 consecutive quiet cycles (no design work found), designer logs a suggestion to stop the designer agent in its iteration log. Designer does NOT auto-stop — human decides
- **Verification**: Read designer template for "5" and "quiet cycle" or "idle" references

---

### Edge Cases

### TC-18: No FE agent exists in the project
- **Precondition**: config.md lists no FE agent; designer role is present
- **Steps**: Designer produces specs for a feature
- **Expected**: Designer warns in Discussion that no consuming dev agent exists for the specs. Specs are still produced (useful for human developers). Not a blocker — designer continues functioning
- **Verification**: Read designer template for handling of missing FE/consuming agent

### TC-19: Feature flagged Design: needed but designer agent is not running
- **Precondition**: A feature has `Design: needed` but no designer agent is active
- **Steps**: Feature sits in `Approved` status with `Design: needed`
- **Expected**: Dev agents skip this feature (Design field check). Feature remains unprocessed until designer starts or human manually changes Design field to `not-needed`. PM health check flags designer as stalled if applicable
- **Verification**: Confirm dev template skips features with `Design: needed`; confirm feature does not get stuck in an invalid state

### TC-20: Designer receives insufficient design information
- **Precondition**: Feature has `Design: needed` but CONTEXT.md lacks a Design Brief or has incomplete information
- **Steps**: Designer picks up the feature and validates design brief completeness
- **Expected**: Designer appends a Discussion entry requesting PM clarification with specific missing items. Feature stays in current state (Design: needed/in-progress). Designer moves to next feature or idles
- **Verification**: Read designer template for incomplete-brief handling logic

### TC-21: Circular rejection loop — dev rejects design twice
- **Precondition**: Dev has sent a feature back to Design status twice (2 round-trips: design -> dev -> design -> dev -> design)
- **Steps**: On the third rejection cycle, check designer behavior
- **Expected**: After 2 round-trips, designer escalates to PM/human via Discussion entry rather than producing another revision. PM mediates and force-approves or rejects
- **Verification**: Read designer template for round-trip counter and escalation logic

### TC-22: Project with no UI — designer role added anyway
- **Precondition**: No features have `Design: needed`; designer is running
- **Steps**: Designer runs multiple cycles
- **Expected**: Designer finds no design requests, runs quiet cycles. After 5 quiet cycles, suggests stopping. No errors, no side effects — just idle
- **Verification**: Read designer template idle detection; confirm no crashes or spurious output on empty queues

### TC-23: Multiple dev agents with one designer
- **Precondition**: config.md lists multiple dev agents (e.g., `fe`, `be`, `skill`); one designer
- **Steps**: Features from different dev agents have `Design: needed`
- **Expected**: Designer reads all dev agent feature INDEX files (not just FE). Spec directory uses the feature's ROLE prefix (e.g., `.squidsquad/designer/specs/FEAT-FE-042/`, `.squidsquad/designer/specs/FEAT-BE-015/`). Designer prioritizes highest-priority feature across all agents, works one at a time
- **Verification**: Read designer template for multi-agent feature scanning logic

### TC-24: Design spec references external assets
- **Precondition**: Designer produces a spec referencing images/fonts
- **Steps**: Check the assets section of a design spec
- **Expected**: Designer lists asset references with source URLs. No large binary files are committed to the repo. Dev agent fetches assets during implementation
- **Verification**: Read designer template spec-format for asset handling instructions

### TC-25: Feature with Design field missing (legacy features)
- **Precondition**: A feature file exists without a `Design` field (pre-027 feature)
- **Steps**: Dev agent encounters this feature; designer scans for design work
- **Expected**: Missing Design field defaults to `not-needed`. Dev agent picks it up normally. Designer ignores it (no design work requested). No errors from either agent
- **Verification**: Confirm dev template treats missing Design field as `not-needed`; confirm designer template only looks for explicit `Design: needed`

---

### Side Effect Regression Tests

### TC-26: Existing dev agent features without design continue to work
- **Precondition**: Features exist with status `Approved` and no `Design` field
- **Steps**: Dev agent runs its normal Ralph Loop cycle
- **Expected**: Dev agent picks up `Approved` features exactly as before. No behavioral change for features that do not have `Design: needed`. The feature lifecycle (Pending -> Planning -> Approved -> In Progress -> Pending Test -> Pending Ship -> Shipped) is unchanged for non-design features
- **Verification**: Run dev agent template logic against a feature without a Design field; confirm it is picked up normally

### TC-27: PM template size stays within limits
- **Precondition**: PM template composed from sub-skills
- **Steps**: Count lines in the composed PM template
- **Expected**: PM template does not exceed ~660 lines (original ~600 + ~60 lines of design routing). The design routing addition is minimal
- **Verification**: `wc -l` on the composed PM template

### TC-28: Existing sub-skill composition for dev/PM/DM is unaffected
- **Precondition**: Sub-skill architecture is in place; dev, PM, DM templates are composed
- **Steps**: Re-run composition engine after adding designer sub-skills
- **Expected**: Dev agent template, PM template, and DM template compose identically to before (except for the intentional additions: dev gets Design field check, PM gets design routing). No unintended changes to other templates
- **Verification**: Diff composed templates before and after adding designer sub-skills; only expected changes should appear

### TC-29: Feature status flow unchanged for non-design features
- **Precondition**: Existing feature lifecycle statuses are in use
- **Steps**: Verify the status flow: Pending -> Planning -> Approved -> In Progress -> Pending Test -> Pending Ship -> Shipped
- **Expected**: No new statuses are added to the lifecycle. The `Design` field is a tag on the feature, not a status value. Status transitions remain the same. Only the `Design` metadata field changes independently
- **Verification**: Confirm no new status values in any template; confirm Design is a separate field

### TC-30: Tracker file formats are backward-compatible
- **Precondition**: Existing tracker INDEX.md files and individual feature/bug files
- **Steps**: Add designer tracker files alongside existing ones
- **Expected**: Designer tracker follows the exact same Tracker Schema 3 format as other agents. INDEX.md format, individual file format, Discussion format all match existing patterns. No schema version bump needed for the tag addition
- **Verification**: Compare `.squidsquad/designer/bugs/INDEX.md` format with `.squidsquad/skill/bugs/INDEX.md`

### TC-31: Git protocol unchanged
- **Precondition**: Git protocol from config.md
- **Steps**: Designer commits and pushes following standard protocol
- **Expected**: Designer uses `git pull --rebase` before work, tracker files are append-only, Discussion entries are append-only, push after completed work unit. Same protocol as all other agents
- **Verification**: Read designer template for git protocol adherence

---

### Upgrade Verification Tests

### TC-32: /squidsquad-upgrade detects designer role and creates structure
- **Precondition**: config.md lists `designer` in Dev Agents; `.squidsquad/designer/` does not exist
- **Steps**: Run `/squidsquad-upgrade`
- **Expected**: Upgrade detects `designer` in config, creates full directory structure (bugs/, features/, iterations/, specs/, working-state.md, CLAUDE.md), generates template via sub-skill composition, creates boot scripts, adds Design Tools section to config.md, adds BUG-DESIGNER and FEAT-DESIGNER counters
- **Verification**: `ls -R .squidsquad/designer/ && grep "DESIGNER" .squidsquad/config.md`

### TC-33: Upgrade with no designer role — no changes
- **Precondition**: config.md does not list `designer` in Dev Agents
- **Steps**: Run `/squidsquad-upgrade`
- **Expected**: No designer-related files are created. No Design Tools section added. No DESIGNER counters added. Feature is completely invisible
- **Verification**: `ls .squidsquad/designer/` should fail; `grep "DESIGNER" .squidsquad/config.md` should return nothing

### TC-34: Upgrade adds Design Tools defaults to config.md
- **Precondition**: config.md has designer role but no Design Tools section
- **Steps**: Run `/squidsquad-upgrade`
- **Expected**: `## Design Tools` section added with `Tool: none`, `Access: none`, `Tool Name: (none)`, `Project ID: (none)` defaults
- **Verification**: `grep -A4 "Design Tools" .squidsquad/config.md`

### TC-35: Existing features without Design field are unaffected after upgrade
- **Precondition**: Features exist without a Design field; upgrade adds designer support
- **Steps**: Read existing features after upgrade
- **Expected**: No retroactive changes to existing features. Missing Design field defaults to `not-needed` at read time. Feature files are not modified by the upgrade
- **Verification**: `git diff` after upgrade should show no changes to existing feature files

### TC-36: Graceful degradation — designer directory missing
- **Precondition**: config.md lists `designer` but `.squidsquad/designer/` was not created (e.g., partial upgrade)
- **Steps**: PM attempts to route a feature to design; dev agent encounters `Design: needed`
- **Expected**: PM still sets `Design: needed` on the feature. Dev agent still skips it. No crash. Feature waits for designer to be properly set up. PM may note in Discussion that designer is not available
- **Verification**: Confirm dev template skip logic does not depend on designer directory existence

---

## Smoke Tests

- [ ] `references/sub-skills/roles/designer.md` exists and is non-empty
- [ ] `references/sub-skills/designer-specific/` directory exists with at least 3 sub-skill files
- [ ] `references/sub-skills/manifest.md` contains a Designer Agent section
- [ ] Composed designer template contains "Feasibility Assessment" text
- [ ] Composed designer template contains "Design Tools" text
- [ ] Composed designer template contains `<!-- sub-skill:` markers
- [ ] Dev agent template contains Design field check logic
- [ ] PM template contains Design Brief section generation logic
- [ ] config.md schema supports `## Design Tools` section
- [ ] `.squidsquad/designer/CLAUDE.md` is a bootstrapper (<50 lines)
- [ ] Designer template references idle detection after 5 quiet cycles
- [ ] Designer template references interactive design session with human approval
- [ ] Designer template references circular rejection escalation after 2 round-trips

---

## Regression Risks

- **PM template bloat**: Adding ~40-60 lines of design routing to PM sub-skills risks exceeding the ~600 line template size constraint from FEAT-SKILL-030. Monitor composed PM template size after integration.
- **Dev agent false skips**: If the Design field check in dev templates is too aggressive (e.g., regex mismatch), dev agents might skip features they should pick up. Ensure missing Design field and `Design: not-needed` both result in normal pickup.
- **Composition engine ordering**: Adding a fourth role (designer) to the composition engine could expose ordering bugs or manifest parsing issues that did not surface with three roles. Test that all four role templates compose correctly in a single run.
- **Cross-agent spec directory reads**: Dev agents reading from `.squidsquad/designer/specs/` is a new cross-agent file read pattern. If path conventions drift between designer output and dev input, specs will be silently ignored. Standardize and test the exact path.
- **Feature file format drift**: Adding the `Design` field to feature files changes the metadata block. If any agent or tool parses feature files with strict field expectations, the new field could cause parse errors. Verify all agents handle unknown/extra fields gracefully.
- **Interactive session blocking**: The real-time design session blocks the designer's Ralph Loop (like PM Phase 2). If the human does not respond, the designer is stuck indefinitely. Ensure the template has guidance for this scenario (e.g., timeout suggestion, ability to skip).
- **Boot script conflicts**: Adding `start-designer.*` scripts alongside existing boot scripts. Ensure no naming collisions or port/session conflicts on systems running multiple agents simultaneously.
- **Idle detection false positives**: If designer checks for `Design: needed` only in certain agent trackers (not all), it might report idle when work exists in an unchecked tracker. Ensure the designer scans all dev agent feature INDEX files.

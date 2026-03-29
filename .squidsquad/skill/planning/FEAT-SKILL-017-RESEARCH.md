# FEAT-SKILL-017 Research — Externalize Agent Templates

## Summary

Currently, SquidSquad setup (SKILL.md Step 4) generates full CLAUDE.md files for each agent by reading the templates in `references/agent-instructions.md` (Template 1: Dev Agent, Template 2: PM/QA) and performing placeholder substitution (`[ROLE]`, `[ROLE_UPPER]`, `[ROLE_TEST_CMD]`, `[OTHER_ROLES]`, `[INTERVAL]`, `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`). The resulting CLAUDE.md files are 200-320 lines each and contain the entire Ralph Loop, Discussion Protocol, Bug Filing Protocol, Working State instructions, etc. For a `fe, be` team, this means three nearly-identical large files (fe/CLAUDE.md, be/CLAUDE.md, pm/CLAUDE.md) committed to the user's repo.

The proposal is to split each CLAUDE.md into two parts: (1) a shared template file in `.squidsquad/templates/` containing the role-invariant instructions (the Ralph Loop, protocols, rules), and (2) a small per-agent bootstrapper CLAUDE.md (~20 lines) containing only role-specific config values plus an instruction to read the template. This reduces duplication, simplifies upgrades (only regenerate templates, not per-agent files), and makes the generated structure cleaner.

The key risk is whether Claude Code will reliably follow a "read this other file for your instructions" directive in a CLAUDE.md file. Based on how the root `CLAUDE.md` already works — it instructs Claude to "Read `.squidsquad/<role>/CLAUDE.md` for your full instructions" and this works reliably — adding one more level of indirection should be feasible. However, there is a meaningful difference: the root CLAUDE.md is auto-loaded by Claude Code's built-in mechanism, whereas the template file requires Claude to voluntarily execute a Read tool call. This adds latency and a potential failure point if the agent skips or misinterprets the instruction.

## Impact Analysis

- **Files touched**:
  - `SKILL.md` — Step 2 (folder structure, add `templates/`), Step 4 (generate bootstrapper CLAUDE.md + template files instead of full inline files), File Structure section, Architecture diagram
  - `references/agent-instructions.md` — Templates 1 and 2 still serve as source-of-truth; no structural change needed, but the header text explaining substitution may need updating to clarify that templates are now copied verbatim with placeholders intact
  - `.squidsquad/templates/dev-agent.md` — new file, copied from Template 1 in agent-instructions.md (with placeholders left unsubstituted)
  - `.squidsquad/templates/pm-agent.md` — new file, copied from Template 2
  - `.squidsquad/[role]/CLAUDE.md` — rewritten from ~250-line full instructions to ~20-line bootstrapper
  - `.squidsquad/pm/CLAUDE.md` — same treatment
  - Upgrade flow (SKILL.md "Upgrade Instructions") — Step 2 agents need to generate bootstrapper + templates instead of full CLAUDE.md
  - `CHANGELOG.md`, `README.md` — document the new structure

- **Behavior changes**:
  - Agent startup adds one extra file read (the template) before the Ralph Loop begins
  - Placeholder substitution shifts from build-time (setup does it) to runtime (agent reads config block and mentally applies values) OR remains build-time (template is copied with substitutions already applied). This is a critical design decision — see Open Questions.
  - Upgrade path changes: instead of regenerating full CLAUDE.md per agent, upgrade regenerates templates/ and leaves bootstrappers untouched (unless config format changes)

- **Dependencies**:
  - Root `CLAUDE.md` auto-boot mechanism (already works with one level of indirection)
  - Claude Code's Read tool (must be available at startup for template loading)
  - FEAT-SKILL-018 (subagent delegation) — subagent prompts reference agent CLAUDE.md contents; if CLAUDE.md is now just a bootstrapper, subagent spawning may need adjustment
  - The upgrade flow spawns agents that "Regenerate `.squidsquad/[role]/CLAUDE.md`" — this instruction changes

## Side Effects

- **Risk 1**: Agent fails to read template file on startup — Severity: **H** — Mitigation: The bootstrapper CLAUDE.md must contain an unambiguous, imperative instruction like "You MUST read `.squidsquad/templates/dev-agent.md` NOW before proceeding." Include a fallback: if the file cannot be read, print an error and exit rather than proceeding without instructions. The root CLAUDE.md already does this pattern successfully ("Read `.squidsquad/<role>/CLAUDE.md` for your full instructions. Follow those instructions exactly.").

- **Risk 2**: Runtime placeholder substitution is unreliable — Severity: **H** — Mitigation: If the design uses runtime substitution (agent reads `[ROLE]` placeholders in the template and mentally replaces them with values from the bootstrapper config block), Claude may occasionally miss a substitution or apply the wrong value, especially under context pressure. The safer approach is build-time substitution: during setup, copy the template AND perform all substitutions, producing a ready-to-use template per agent type. But this negates the "shared template" benefit for multi-agent-same-type setups. A hybrid approach: substitute only at build-time into the per-role CLAUDE.md bootstrapper's config block, and have the template use those config values by reference rather than placeholders.

- **Risk 3**: Existing setups break on upgrade — Severity: **M** — Mitigation: The upgrade flow must detect whether the current CLAUDE.md is inline (old format) or bootstrapper (new format). If inline, extract config values, generate the bootstrapper, create the templates/ directory. If already bootstrapper, just update templates/. Detection heuristic: check if CLAUDE.md length > 50 lines (inline) or contains a specific marker like `## Template Reference` (bootstrapper).

- **Risk 4**: Two levels of indirection slow agent startup — Severity: **L** — Mitigation: Currently agents already go through one indirection (root CLAUDE.md -> role CLAUDE.md). Adding a second (role CLAUDE.md -> template) adds one more Read call (~1-2 seconds). Acceptable, but worth noting. Total chain: root CLAUDE.md (auto-loaded) -> Read role CLAUDE.md -> Read template.

- **Risk 5**: Context window usage increases from loading template every session — Severity: **L** — Mitigation: The template file contents would have been in the CLAUDE.md anyway (same total content). The only overhead is the bootstrapper's ~20 lines of config, which is negligible.

## Edge Cases

- **Template file missing or deleted**: Agent reads bootstrapper, tries to read template, file not found. Must fail explicitly with a clear error message ("Template file `.squidsquad/templates/dev-agent.md` not found. Run `/squidsquad-upgrade` to regenerate.") rather than silently proceeding without instructions.

- **Multiple agents of same type sharing one template**: This is the primary benefit case. Two `be` agents (unusual but possible with custom names) would share `dev-agent.md`. Each has its own bootstrapper with different config. Works naturally if the template uses config references rather than hard-coded values.

- **Placeholder substitution approach — build-time vs runtime**:
  - Build-time (current approach, applied to templates/): Setup copies template and substitutes all placeholders. Result: `templates/dev-agent.md` has `be` hard-coded. Problem: if team has `fe` and `be`, need separate templates or keep placeholders.
  - Runtime (agent substitutes mentally): Template has `[ROLE]` placeholders, bootstrapper has `role: be`, agent combines them. Problem: Claude may miss substitutions. But the instruction is clear and bounded.
  - Hybrid: Template uses generic language ("your role's tracker", "your bugs.md") instead of placeholders. Bootstrapper provides all role-specific paths explicitly. This avoids substitution entirely but requires rewriting the template language.

- **Bootstrapper config format**: Must be machine-readable by Claude. A YAML-like block at the top of the bootstrapper CLAUDE.md works well:
  ```
  role: be
  role_upper: BE
  test_cmd: cd backend && pytest
  other_roles: fe
  interval: 5
  ```
  Claude can parse this reliably.

- **Partial upgrade (templates exist but bootstrapper is old format)**: Upgrade must handle mixed states. Check both template existence AND bootstrapper format.

- **User edits to CLAUDE.md**: Some users may have manually customized their agent CLAUDE.md (like this repo's skill/CLAUDE.md which has project-specific context). The bootstrapper approach preserves user customizations in the bootstrapper file while templates are regenerated on upgrade. This is actually better than the current approach where upgrade overwrites everything.

## Integration Risks

- **FEAT-SKILL-018 (subagent delegation)**: Subagent prompts in the PM template reference how dev agents work. If the PM needs to understand dev agent behavior to coordinate, the PM template must either include relevant dev agent behavior descriptions OR the PM must also read the dev-agent template. Currently the PM template is self-contained. No direct conflict, but the subagent prompts spawned by PM (for research, test planning, etc.) are defined inline in agent-instructions.md and do not reference CLAUDE.md files — they are standalone prompts. Low risk.

- **Upgrade flow**: The upgrade instructions (SKILL.md "Upgrade Instructions" Step 2) currently say "Regenerate `.squidsquad/[role]/CLAUDE.md`... using the Dev Agent template from `references/agent-instructions.md`". This would change to: "Regenerate `.squidsquad/templates/dev-agent.md` and `.squidsquad/templates/pm-agent.md` from `references/agent-instructions.md`. Regenerate bootstrapper CLAUDE.md files only if the config format has changed." This simplifies the upgrade — fewer files to touch per agent.

- **Setup flow**: Step 2 (folder structure) adds `templates/` directory. Step 4 changes from "generate full CLAUDE.md" to "copy templates, generate bootstrappers." Straightforward.

- **Status line script**: No impact — `statusline.sh` reads `.active-role` and tracker files, not CLAUDE.md.

- **Root CLAUDE.md auto-boot**: No change needed. The chain is: root CLAUDE.md tells agent to read `[role]/CLAUDE.md`. The bootstrapper in `[role]/CLAUDE.md` then tells agent to read the template. The root CLAUDE.md does not need to know about templates.

- **`.claude/settings.json` permissions**: Currently allows `Edit(.squidsquad/**)` and `Write(.squidsquad/**)`. Templates in `.squidsquad/templates/` are covered by these existing globs. No permission changes needed.

## Open Questions

- **Q1**: Should placeholder substitution happen at build-time or runtime? — **Why**: Build-time is safer (no risk of Claude misapplying substitutions) but means templates aren't truly shared across roles. Runtime is cleaner architecturally but relies on Claude correctly applying ~6 substitutions every session. A middle ground: use build-time substitution but generate one template per role type (all dev agents share one substituted template if they have the same test command, otherwise separate copies). This decision affects the entire implementation approach.

- **Q2**: Should the template contain the raw `[ROLE]` placeholders or use generic language? — **Why**: If templates say "your role's bugs.md" instead of `[ROLE]/bugs.md`, no substitution is needed at all — the bootstrapper's config block provides the concrete paths. But rewriting all templates to use generic language is a larger change and may reduce clarity (the current templates are very explicit about file paths). Getting this wrong means agents navigate to wrong files.

- **Q3**: How should the bootstrapper reference the template — as a file path to Read, or as an include directive? — **Why**: Claude Code does not have a native "include" mechanism for CLAUDE.md files. The bootstrapper must use a natural-language instruction ("Read the file at..."). This works (proven by root CLAUDE.md auto-boot) but is one more link in the chain that could break. If Claude Code ever adds native includes, this could be simplified.

- **Q4**: Should the upgrade migration be a one-time flag or auto-detected? — **Why**: If detection is based on CLAUDE.md file size or content markers, it's automatic. If it requires a config flag (`template_format: bootstrapper`), it's explicit. Auto-detection is more user-friendly but could misfire on heavily customized CLAUDE.md files.

## Recommendation

**Feasible with caveats.** The core idea is sound and well-motivated — reducing duplication, simplifying upgrades, and separating config from instructions. The main design decision is placeholder substitution strategy (Q1/Q2), which should be resolved before implementation begins.

Recommended approach: **Build-time substitution with shared templates per agent type.** During setup, copy Template 1 from agent-instructions.md into `.squidsquad/templates/dev-agent.md` with all `[ROLE]`-family placeholders substituted for the specific role. If multiple dev agents exist (e.g., `fe` and `be`), generate `templates/dev-agent-fe.md` and `templates/dev-agent-be.md` (or a single `dev-agent.md` if only one dev agent). The bootstrapper CLAUDE.md is ~20 lines: identity block + "Read `.squidsquad/templates/dev-agent-[role].md` for your complete instructions." This preserves the reliability of build-time substitution while still centralizing the template source and simplifying upgrades.

For the migration path: detect inline CLAUDE.md by checking if it contains `## The Ralph Loop` (present in full templates, absent in bootstrappers). If inline, extract any user customizations from the first few lines, generate the bootstrapper with those customizations preserved, and create the template.

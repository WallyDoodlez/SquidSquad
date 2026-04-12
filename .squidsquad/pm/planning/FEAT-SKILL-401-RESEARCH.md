# FEAT-SKILL-401 Research — Capability Sub-Skills

## Summary

SquidSquad currently has two distinct concepts that extend agent capability: (1) **behavioral sub-skills** — markdown files under `references/sub-skills/` that are composed into agent CLAUDE.md files at build time via `compose.py`, defining how agents behave (tracker-protocol, vault-protocol, git-commit, etc.); and (2) **tools** — external integrations under `references/tools/` with their own manifest.yaml, setup.md, and sub-skill.md files, validated by `manifest.py` and referenced via `requires_tools` in role manifests. The locked decision is to unify these under a single "sub-skill" concept, where everything that extends agent capability beyond native Claude abilities is a sub-skill — whether it is behavioral instructions, an MCP server integration, or a CLI tool wrapper.

The current tool infrastructure is already close to the target design. Each tool directory (`references/tools/<id>/`) contains a manifest.yaml (what it does, provider type, applicable roles), a sub-skill.md (agent-facing usage instructions composed into CLAUDE.md), and a setup.md (human-facing installation walkthrough). The rename from "tool" to "capability sub-skill" is primarily a vocabulary change in manifests, validation code, and documentation, but the mechanical changes are well-scoped: rename `references/tools/` to `references/sub-skills/capabilities/` (or similar), update manifest.py's validator and cross-reference checks, update compose.py if it gains runtime tool composition, update SKILL.md and WIZARD.md references, and add the PM Phase 1 capability gap analysis logic.

The most significant new behavior is the PM's capability gap analysis during Phase 1 Research. Today, PM spawns a research agent that analyzes codebase impact but does not check whether the target agent has the external integrations needed to implement the feature. The new flow: PM reads the target agent's role manifest `requires_tools` (to be renamed `requires_sub_skills`), checks whether required capabilities are satisfied, and if not, searches the sub-skill directory for a match. If no match, escalate to human. Agents also self-check their manifest at runtime as a safety net. This is a new code path in the feature-intake sub-skill and potentially a new runtime check in each agent's startup sequence.

## Impact Analysis

- **Files touched**:
  - `references/tools/` directory — rename to `references/sub-skills/capabilities/` (or keep as `references/capabilities/`)
  - `references/tools/*/manifest.yaml` (4 files: figma, google_stitch, local_html, local_delivery) — rename `schema_version` field values, possibly rename directory
  - `references/scripts/manifest.py` — rename `tools` kind to `capabilities` (or `sub_skills`), update validators, cross-reference checks, CLI commands, VALID_TOOL_CATEGORIES, VALID_PROVIDERS, DOMAIN_ONLY_BLOCKLIST entries referencing "tool"
  - `references/scripts/compose.py` — no changes needed unless capability sub-skills gain build-time composition (currently tools are NOT composed; their sub-skill.md is only referenced, not inlined)
  - `references/roles/*/manifest.yaml` (5 files) — rename `requires_tools` to `requires_sub_skills` (or `requires_capabilities`)
  - `references/sub-skills/manifest.md` — update inventory and terminology
  - `references/sub-skills/designer-specific/design-tools.md` — rename to `design-capabilities.md`, update terminology throughout
  - `references/wizard/WIZARD.md` — update references from "tool" to "capability sub-skill"
  - `SKILL.md` — update architecture docs, setup instructions, tool references
  - `references/sub-skills/pm-specific/feature-intake.md` — add Phase 1 capability gap analysis
  - `tests/test_manifest.py`, `tests/test_manifest_registry.py` — update test references
  - `.squidsquad/config.md` — possibly add a `## Capabilities` or `## Sub-Skills` section (currently tools are not tracked in config.md beyond designer-specific design-tools config)

- **Behavior changes**:
  - PM Phase 1 Research gains a new step: check target agent's manifest for required capabilities, verify they are satisfied, escalate if not
  - Agents gain a runtime self-check: on startup, verify that required capabilities (MCP servers, CLI tools) are actually available
  - Vocabulary change throughout: "tool" becomes "capability sub-skill" or just "sub-skill" in all user-facing and agent-facing text
  - The wizard's tool setup flow (currently implicit — designer gets tool configured on first use) needs to become explicit capability sub-skill setup

- **Dependencies**:
  - PyYAML (already required by manifest.py)
  - No new external dependencies
  - The existing behavioral sub-skills (`references/sub-skills/common/`, `references/sub-skills/*-specific/`) are unaffected — they remain as they are, just now part of a unified "sub-skill" taxonomy alongside capability sub-skills

## Side Effects

- **Risk 1**: Naming collision between behavioral sub-skills and capability sub-skills — Severity: M — Mitigation: Use clear directory separation. Behavioral sub-skills stay in `references/sub-skills/common/` and `references/sub-skills/*-specific/`. Capability sub-skills live in `references/sub-skills/capabilities/` (formerly `references/tools/`). The manifest.md already documents the behavioral sub-skills; capability sub-skills get their own section.

- **Risk 2**: Breaking existing manifest validation tests — Severity: M — Mitigation: Update all test files (`tests/test_manifest.py`, `tests/test_manifest_registry.py`) in the same PR. Run the full test suite before merging.

- **Risk 3**: Wizard flow disruption — Severity: L — Mitigation: The wizard reads from manifest.py's registry. As long as the registry rename is consistent (the `list`, `load`, `validate` CLI commands accept the new kind name), the wizard's calls continue to work. Update WIZARD.md references in the same PR.

- **Risk 4**: Existing installs with `references/tools/` path hardcoded — Severity: L — Mitigation: The `references/tools/` directory is only read by `manifest.py` and the wizard agent. Users never interact with it directly. The upgrade path handles the rename by re-deploying agent CLAUDE.md files (which already happens during upgrade).

- **Risk 5**: The `design-tools.md` sub-skill is composed into designer CLAUDE.md and references "tools" terminology extensively — Severity: L — Mitigation: Rename the file and update all references in a single commit. compose.py resolves includes by path, so updating the include directive in `references/roles/designer/CLAUDE.md` from `designer-specific/design-tools` to `designer-specific/design-capabilities` (or similar) is sufficient.

## Edge Cases

- **MCP server not configured**: Agent's runtime self-check discovers the MCP server is not available. The agent should log a warning, check for a builtin fallback (e.g., `local_html` for designer), and if no fallback exists, file a bug or escalate to PM. The designer's existing `design-tools.md` already handles this gracefully ("fall back to manual mode") — this pattern should be generalized.

- **Two sub-skills conflict**: Example: a user installs both `figma` and `google_stitch` for the designer. The `requires_tools.any_of` semantic already handles this — it means "at least one of these." Conflict only arises if two sub-skills provide the same capability but with incompatible instructions. Mitigation: the manifest validator should check that `any_of` sub-skills have non-overlapping `sub_skill.md` content, or that the agent template handles selection at runtime.

- **Sub-skill requires environment variables or API keys**: The existing pattern (`setup.md` per tool) handles this — the human is walked through setup including credential configuration. The "Zero Credential Management" principle in `design-tools.md` already states that SquidSquad does not manage credentials; MCP servers handle authentication externally. This principle should be promoted to a top-level rule for all capability sub-skills.

- **Sub-skill needs OS-specific installation**: CLI-based sub-skills (not yet in the registry, but planned) may need different install commands for macOS/Linux/Windows. The `setup.md` format is free-form markdown, so it can include OS-specific sections. No schema change needed, but a convention should be documented.

- **PM research discovers a capability gap but no sub-skill exists in the directory**: The fallback chain is: check agent manifest -> search repo sub-skill directory -> look for alternative means (e.g., a different sub-skill that partially covers the gap) -> escalate to human. This is new behavior that needs to be coded into the feature-intake sub-skill's Phase 1 instructions.

- **Agent has a required sub-skill in its manifest but the sub-skill was removed from the directory**: The manifest validator catches this at validation time (cross-reference check). At runtime, the agent's self-check should detect the missing sub-skill and log a warning rather than crash.

## Integration Risks

- **Sub-skill directory / marketplace plans**: The memory notes reference a "sub-skill directory website" and "marketplace as test project." The current plan is to use the SquidSquad repo for the sub-skill directory initially, then separate later. This feature (FEAT-SKILL-401) establishes the packaging format that the marketplace will consume. Risk: if the packaging format changes after marketplace launch, existing marketplace entries break. Mitigation: lock the manifest schema at v1 for capability sub-skills, with a clear upgrade path for v2.

- **PM Phase 1 capability gap analysis — mechanical implementation**: The PM's feature-intake sub-skill (`references/sub-skills/pm-specific/feature-intake.md`) currently spawns a research agent that reads codebase files. The new capability gap check needs to happen before or during this research. Mechanically: the research agent reads `references/roles/<target-role>/manifest.yaml` -> extracts `requires_sub_skills` -> checks each ID against `references/sub-skills/capabilities/` (or `references/tools/`) -> reports gaps in RESEARCH.md under a new "Capability Gaps" section. The PM then acts on the report. This is a prose-instruction change, not a code change — the research agent is a subagent that follows text instructions.

- **Coexistence with behavioral sub-skills**: Behavioral sub-skills (tracker-protocol, vault-protocol, etc.) are build-time compositions via `{{include:}}` directives. Capability sub-skills (figma, local_html, etc.) are either composed at build time OR referenced at runtime. The two systems coexist without conflict because they use different mechanisms. The only overlap is naming — both are called "sub-skills" — which is the intent of the unification.

- **Runtime vs build-time composition**: Currently, capability sub-skill content (`sub-skill.md`) is NOT automatically composed into agent CLAUDE.md files. The designer's tool instructions are in `design-tools.md` (a behavioral sub-skill), not in `figma/sub-skill.md`. The tool's `sub-skill.md` is available for agents to read at runtime but is not inlined. Decision needed: should capability sub-skills be composed at build time (like behavioral sub-skills) or remain runtime-read? Build-time is simpler and more reliable. If build-time: compose.py needs a new directive (e.g., `{{capability: figma}}`) that resolves from the capability directory.

## Upgrade & Migration

- **New config values**: None required in `config.md`. Capability sub-skills are tracked via role manifests, not runtime config. (If a `## Capabilities` section is added to config.md for runtime discovery, it would default to empty / auto-detected.)

- **New files**:
  - None for end users. The rename from `references/tools/` to `references/sub-skills/capabilities/` (or `references/capabilities/`) is internal to the SquidSquad repo.
  - For capability sub-skill authors: a new template/guide for creating capability sub-skills (packaging format documentation).

- **Template changes**:
  - Agent CLAUDE.md files will gain a runtime self-check section (verify required capabilities on startup).
  - PM's feature-intake Phase 1 instructions gain a capability gap analysis step.
  - Designer's `design-tools.md` becomes `design-capabilities.md` with updated terminology.

- **Upgrade steps**:
  - `/squidsquad-upgrade` re-deploys all agent CLAUDE.md files (already happens), which picks up the new self-check and PM capability gap instructions automatically.
  - No manual user action required beyond running the standard upgrade.
  - The `references/tools/` to `references/sub-skills/capabilities/` rename is transparent to users.

- **Graceful degradation**: If a user does not upgrade, their agents continue to work with the old "tools" vocabulary. No breakage. The old `references/tools/` directory would still be read by the old `manifest.py`. The capability gap analysis simply does not exist — PM researches features without checking capabilities, which is the current behavior.

## Open Questions

- **Q1**: Should `references/tools/` be renamed to `references/sub-skills/capabilities/` or `references/capabilities/`? — **Why**: The directory structure sets the permanent packaging convention. Getting this wrong means a disruptive rename later when the marketplace is live.

- **Q2**: Should capability sub-skill content (`sub-skill.md`) be composed at build time via a new compose.py directive, or remain as runtime-read files? — **Why**: Build-time composition is more reliable (agent always has the instructions) but increases CLAUDE.md size. Runtime-read is lighter but depends on the agent remembering to read the file.

- **Q3**: How does the agent runtime self-check work mechanically? Should it be a Python script (`references/scripts/capability_check.py`) that agents call, or prose instructions in the agent's startup sequence? — **Why**: A script is deterministic and testable; prose is fragile and may be skipped or misinterpreted by the agent.

- **Q4**: Should the manifest schema version be bumped from 1 to 2 for the rename, or should v1 support both `requires_tools` and `requires_sub_skills` field names? — **Why**: A schema version bump forces all manifests to be updated simultaneously. Supporting both names in v1 is more gradual but creates tech debt.

- **Q5**: What is the exact PM escalation path when a capability gap is found and no sub-skill exists? File a feature request for the sub-skill? Block the original feature? Ask the human for guidance? — **Why**: This determines whether capability gaps halt work or are non-blocking.

## Recommendation

**Feasible with caveats.** The core change is a well-scoped vocabulary rename plus two new behaviors (PM capability gap analysis and agent runtime self-check). The main caveats are:

1. The directory rename decision (Q1) should be locked before implementation begins, as it affects the marketplace packaging convention.
2. The build-time vs runtime composition question (Q2) should be answered, as it affects compose.py changes and CLAUDE.md size.
3. The runtime self-check mechanism (Q3) should be a deterministic script, not prose, to avoid agent non-compliance.
4. The feature can be shipped incrementally: Phase A (rename + manifest updates), Phase B (PM capability gap analysis), Phase C (agent runtime self-check). Each phase is independently useful and testable.

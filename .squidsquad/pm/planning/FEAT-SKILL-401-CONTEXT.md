# FEAT-SKILL-401 Context — Capability Sub-Skills

## Scope

Unify the "tools" and "sub-skills" concepts into a single sub-skill ecosystem. Rename `references/tools/` to `references/sub-skills/capabilities/`, bump manifest schema to v2, add build-time composition of capability sub-skills via `{{capability:}}` directive, add PM capability gap analysis to Phase 1 Research, and add agent runtime self-check via declarative manifest + generic `capability_check.py`.

## Locked Decisions (human decided)

- **No "tools" vocabulary**: everything that extends agent capability beyond native Claude is a sub-skill. Eliminate all references to "tools" as a separate concept.
- **Directory structure**: `references/sub-skills/capabilities/` — unified namespace under sub-skills. Behavioral sub-skills remain in `common/`, `pm-specific/`, etc.
- **Schema v2 hard bump**: all manifests updated together. `requires_tools` → `requires_sub_skills`. No dual-field backward compat.
- **Build-time composition**: new `{{capability:}}` directive in compose.py inlines capability sub-skill instructions into agent CLAUDE.md. Consistent with behavioral sub-skills.
- **Runtime self-check**: generic `capability_check.py` reads agent manifest, checks each required capability. Sub-skill authors declare `provider` + check info in manifest.yaml (MCP: server_name; CLI: check_command). Authors write zero Python.
- **PM capability gap analysis**: during Phase 1 Research, PM checks target agent's manifest for required capabilities. If missing, search repo sub-skill directory. If not found, flag as non-blocking in RESEARCH.md. Human decides at Phase 3 approval gate.
- **Agent self-service**: agents check their manifest at runtime as safety net. Fallback chain: manifest → repo directory → alternative means → human escalation.
- **Non-blocking escalation**: capability gaps don't block features. PM surfaces them, human decides.
- **Sub-skill packaging**: minimal file with description, capabilities, usage instructions, asset references, install instructions. MCP sub-skills reference actual MCP config. CLI sub-skills include installer instructions + skill file.

## Dev Discretion (dev agent can choose)

- Internal naming of compose.py directive (e.g. `{{capability:id}}` vs `{{cap:id}}`)
- capability_check.py output format (human-readable vs JSON)
- How to handle the deprecation warnings during the transition period
- Whether to split manifest.py validator refactoring into a prep commit

## Side Effect Mitigations (required)

- Update all test files (`test_manifest.py`, `test_manifest_registry.py`) in the same PR as the rename
- Update `design-tools.md` → `design-capabilities.md` with all terminology changes
- Update WIZARD.md tool references
- Update SKILL.md architecture docs
- Ensure compose.py handles both behavioral and capability sub-skills without collision

## Upgrade Path (required)

- `/squidsquad-upgrade` re-deploys agent CLAUDE.md files (existing mechanism) — picks up new instructions automatically
- The `references/tools/` → `references/sub-skills/capabilities/` rename is transparent to users
- No manual user action beyond running standard upgrade
- Graceful degradation: non-upgraded installs continue working with old vocabulary, just without capability gap analysis

## Out of Scope

- Marketplace/directory website (future work, uses the packaging format established here)
- Creating new capability sub-skills beyond existing ones (figma, google_stitch, local_html, local_delivery)
- Separating sub-skill directory into standalone repo
- Runtime sub-skill hot-loading (installing sub-skills without recompose)

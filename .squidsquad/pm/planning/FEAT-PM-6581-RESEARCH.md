Now I have a complete picture. Here is the research.

---

```markdown
# FEAT-PM-6581 Research — Wizard Reframing: L3 Picks Agents, L4 Records Project Specifics, Preset-Driven Setup

## Summary

The install wizard (`wizard.py`) currently applies a single L3 domain variant uniformly to all core roles (dev, pm, qa, dm) based on one project-type question. The proposal reframes this: the preset defines which agents to deploy and what L3 variant each gets (per-agent, not uniform), and the wizard captures project-specific answers and writes them as L4 sub-skills to `.squidsquad/project/` during setup. No migration is needed — the project is pre-public, and the compose pipeline already supports per-agent L3 variant resolution and L4 auto-include.

The recommendation is **feasible with caveats**: the mechanical infrastructure is largely in place, but the wizard's question protocol, `apply_project_type()`, and the spec shape need restructuring. The primary risk is that the prose runbook (Claude-driven installer) must be rewritten to match the new question flow, and existing L3 variant files for non-dev roles are thin stubs that may not provide enough value to justify deploying them.

## Vault Context

- **BRIEFING.md priorities**: "Take SquidSquad public / v1.0.0 launch" (high) — first-install experience directly supports this. "Generalize 'dev' to 'worker'" (pending) — the wizard's agent-picking logic should anticipate non-dev agent types.
- **Related decisions**: [[decision-general-purpose-vision]] — SquidSquad is for all teams, not just developers. Non-technical teams need presets that don't assume GitHub/git knowledge. [[decision-sub-skill-architecture]] — L1-L5 layered architecture already supports per-agent L3 variants and L4 project sub-skills. [[decision-self-healing-sentinel]] — self-healing design philosophy applies to setup resilience (what happens when a preset partially fails?).
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — prefer wizard.py mechanical helpers over LLM-driven conversation for structural decisions. L4 recording should lean on deterministic repo scanning over human Q&A where possible.
- **Human preferences**: "Prefer OSS over custom" — preset system should lean on Forgejo for non-GitHub teams; "self-healing systems" — failed agent deployment during scaffold should not block the whole setup; "general-purpose vision" — presets should include non-dev team shapes (marketing, ops, content).
- **Related learnings**: [[learning-atomic-migration-strategy]] — L4 records should be written atomically (`.tmp` then `mv`) to avoid partial reads during concurrent compose.

## Impact Analysis

- **Files touched**:
  - `references/scripts/wizard.py` — `apply_project_type()` (lines 511–536), `PROJECT_TYPE_PRESETS` (lines 62–73), `generate_default_spec()` (lines 1983–2069), `scaffold_install()` (lines 831–1071)
  - `references/presets/*/manifest.yaml` — may need per-agent L3 variant mapping declaration
  - `references/scripts/compose.py` — L4 auto-include already works (lines 319–339), no changes needed
  - `references/roles/LAYERS.md` — documentation update (lines 1–73)
  - `.squidsquad/project/*.md` — new L4 content written during setup (seed templates already exist at `references/sub-skills/project/`)
  - `tests/test_wizard.py` — `TestApplyProjectType` class (lines 2013–2046), new tests for per-agent variant assignment and L4 recording
  - `tests/test_wizard_runbook.py` — test coverage for prose runbook interactions

- **Behavior changes**:
  1. `apply_project_type()` currently sets one `variant` on all 4 core roles — must change to per-agent variant assignment driven by the preset
  2. Wizard questions shift from "what project type?" to a series of per-agent L3 variant choices, followed by L4 recording (conventions, stack, domain context)
  3. `PROJECT_TYPE_PRESETS` morphs from a flat `{type: variant}` map to a richer structure that defines which agents get deployed and what L3 variant each defaults to
  4. L4 project sub-skills are populated during setup rather than left empty for PM to fill later

- **Dependencies**:
  - Preset manifests (`references/presets/*/manifest.yaml`) — may need a `default_variants: {role: variant}` field
  - Role manifests (`references/roles/*/manifest.yaml`) — `setup_requirements` already defines per-role questions; dev's `variant` requirement (line 39) is the key one
  - `compose.py` `_assemble_claude()` L4 auto-include (lines 319–339) — no changes, this already works
  - `config.py` schema v2 agent parsing (lines 410–468) — already supports per-agent `variant` field

## Side Effects

- **Risk 1**: Non-dev L3 variants are thin stubs — Severity: M — PM/web, QA/web, DM/web domain-context files contain 1-2 paragraphs each. If the wizard deploys these for every agent, agents may get confusing "You are a web-specialized PM" identity without meaningful behavioral differences. **Mitigation**: Either (a) skip L3 variants for pm/qa/dm entirely (they get base L1+L2 only), or (b) enrich non-dev domain-context files with genuinely useful domain-specific guidance (e.g., "PM for web: think about SEO, CDN caching, browser compatibility testing").

- **Risk 2**: Wizard prose runbook is Claude-driven — Severity: H — The current wizard flow (Q-new21) is a prose runbook where a Claude "installer agent" follows conversation prompts. Changing the question protocol means rewriting the runbook, which is not mechanically testable. **Mitigation**: Move as much as possible into deterministic `wizard.py` helpers (following [[pattern-deterministic-scripts-over-prose]]), leaving the runbook as a thin orchestration layer. The `scaffold_install()` and `apply_project_type()` functions already handle the mechanical parts.

- **Risk 3**: Backward compatibility with specs — Severity: L — Changing the spec shape (per-agent variants vs uniform) could break `generate_default_spec()` and `--yes` mode. **Mitigation**: `scaffold_install()` already handles per-agent `variant` in the spec (lines 935–946); the change is only in how `apply_project_type()` generates that spec. No stored-format change needed.

## Edge Cases

- **Custom preset (no L3)**: The "custom" preset currently sets `variant=None` on all agents. With per-agent picking, each agent independently gets base or variant. The wizard must handle the case where some agents get variants and others don't within the same preset.

- **Non-existing variant**: If a preset declares `qa: mobile` but no `roles/qa/mobile/` directory exists, `scaffold_install()` calls `deploy_role()` which will fail at compose time. The wizard should validate variant existence before scaffolding (currently it does not — line 940 just concats `role_identity-variant`).

- **Forgejo backend with non-dev team**: If the human picks a Forgejo backend and a non-dev preset (e.g., "marketing-team"), the wizard must handle the case where no `gh` CLI is installed (currently a hard requirement via `check_gh()` at line 107). The general-purpose vision requires this to degrade gracefully.

- **Empty L4 directory**: If the wizard writes nothing to `.squidsquad/project/`, `compose.py`'s `_assemble_claude()` handles it correctly — the directory iteration is a no-op when empty. No edge case risk.

- **Partial scaffold failure**: If 3 of 4 agents deploy successfully but 1 fails (e.g., missing variant directory), the current `scaffold_install()` marks that agent as `FAILED` in the summary and continues. This is correct behavior — self-healing design means the team can operate with partial success.

## Integration Risks

- **Compose pipeline**: `compose.py` `deploy_role()` (line 807) and `_assemble_claude()` (line 280) already support per-agent L3 variants and L4 auto-include. No compose changes needed. The integration risk is that L4 files written during setup may contain project-specific instructions that contradict L1-L3 instructions. **Mitigation**: L4 files should be additive, not contradictory — seed templates should use language like "In this project..." rather than "Always..."

- **Harness integration**: The harness (`harness.py`) reads `CLAUDE.md` from per-agent directories. If compose fails for one agent, that agent's CLAUDE.md is missing and the harness will report it as stalled. The self-healing pipeline sentinel (#5783) should detect this.

- **Tracker labels**: `ensure_labels()` is idempotent and doesn't change with this task. No risk.

- **Forgejo backend**: `config.md` already stores `forge_provider`, `forge_endpoint`, `forge_owner`, `forge_repo` (lines 82–85 of config.py FIELD_MAP). If the wizard writes a Forgejo config, `tracker.py` must use those values. This is a separate concern but the wizard should offer the Forgejo preset choice during setup.

## Upgrade & Migration

- **New config values**: Potentially `project-conventions` in `## Project` section (currently stored only in `.squidsquad/project/`). Or none — L4 files replace the need for new config.md fields.
- **New files**: Seed templates written to `.squidsquad/project/project-conventions.md`, `.squidsquad/project/stack-details.md`, etc. during setup.
- **Template changes**: None to compose templates. L3 variant `instructions.md` files for non-dev roles may be enriched but this is additive.
- **Upgrade steps**: N/A — no upgrade impact. Pre-public, no existing users to upgrade.
- **Graceful degradation**: N/A — no upgrade needed.

## Open Questions

- **Q1**: Should non-dev roles (pm, qa, dm) get L3 domain variants at all during wizard setup? — **Why**: The current domain-context files for these roles are 1-2 paragraphs of thin specialization. Applying "web" variant to a PM agent currently adds only "think about web deployment, CDN, SEO considerations" which may not justify the complexity. If we deploy variants, they need enriched content; if we skip, pm/qa/dm always get base L1+L2 which is simpler and already correct.

- **Q2**: What L4 sub-skill files should the wizard write during setup? — **Why**: The current `.squidsquad/project/` has `shared-instructions.md`, `shared-soul-directives.md`, `setup-upgrade-gate.md`, and per-role files. The wizard should decide which of these are wizard-populated (project conventions, stack details) vs. PM-populated (operations rules). Getting this scope wrong means the wizard either writes too much (overriding PM's domain) or too little (leaving setup incomplete).

- **Q3**: How should the preset manifest declare per-agent L3 variant defaults? — **Why**: Currently `PROJECT_TYPE_PRESETS` is a simple dict in wizard.py. A preset manifest field like `default_variants: {dev: web, pm: null, qa: null, dm: null}` would be more declarative but requires a schema change to `validate_preset_manifest()` in `manifest.py`. The alternative is keeping it in wizard.py as code, which is simpler but less discoverable.

## Recommendation

**Feasible with caveats.** The mechanical infrastructure — compose per-agent variant resolution, L4 auto-include, per-agent spec fields — is already in place. The work is primarily in wizard.py's question protocol and `apply_project_type()` restructuring. The key caveats are: (1) the prose runbook rewrite is Claude-driven and not mechanically testable, (2) non-dev L3 variant content is thin and may need enrichment before it justifies deployment, and (3) the preset manifest schema may need a new field for per-agent variant defaults, which touches `manifest.py` validation.

## Vault Candidates

- **Type**: decision — **Wizard `apply_project_type` should assign L3 variants per-agent, not uniformly** — **Why**: This is an architectural constraint that future wizard changes must respect. Uniform application was a shortcut; the architecture always supported per-agent assignment.

- **Type**: pattern — **Setup questions should be role-manifest-driven, not wizard-hardcoded** — **Why**: `setup_requirements` in role manifests already drives per-role questions. The wizard should walk this declaratively rather than having `PROJECT_TYPE_PRESETS` as a parallel hardcoded structure. This pattern already exists for dev's `variant` and `stack` requirements.

- **Type**: learning — **Non-dev L3 domain-context files are stubs — enrich or skip** — **Why**: Applying thin domain-context stubs to pm/qa/dm agents adds identity confusion without behavioral value. Future L3 variant additions should either be substantial or not deployed to non-specialist roles.

- **Type**: decision — **L4 project sub-skills populated during setup vs. left empty for PM** — **Why**: Moving from empty-seed to wizard-populated L4 changes the ownership boundary. PM currently owns `.squidsquad/project/` contents. If the wizard pre-populates, PM's role shifts from "create" to "refine."

- **Type**: pattern — **Setup scaffold should validate variant existence before compose** — **Why**: Currently `scaffold_install()` composes `{role}-{variant}` without checking if the variant directory exists. Adding a pre-validation step (similar to the role identity check at line 924) prevents cryptic compose failures during setup.
```
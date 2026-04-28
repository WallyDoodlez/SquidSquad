# FEAT-PM-3465 Research — Layered Role Definition Architecture

## Summary

This research covers the proposal to restructure role definitions into 3 composable layers: a base SquidSquad agent layer (shared by all roles), a general role layer (e.g., "developer", "qa", "delivery"), and a specific role layer (e.g., "skill", "qa-security"). Each layer would carry both a CLAUDE.md (instructions) and a SOUL.md (personality). The current architecture is already a 5-layer sub-skill system using build-time concatenation via compose.py, with role templates in `references/roles/<role>/` and shared sub-skills in `references/sub-skills/common/`. The proposed change would introduce a formal intermediate layer (general role) that does not currently exist — roles jump directly from shared sub-skills to role-specific sub-skills with no structural grouping between them.

The proposal is architecturally coherent and extends the existing philosophy. However, it is also genuinely additive: no current role has a "general role" ancestor that is separate from both the common sub-skills and the specific role template. The blast radius is substantial — every role template, every SOUL.md, compose.py, soul_adaptation.py, wizard.py, add_role.py, and the squidsquad-upgrade skill would all need changes. The primary risk is migration atomicity: this must ship as a single coordinated change to avoid running agents seeing a partially-composed identity. The general-purpose vision (non-technical teams, non-dev roles) makes this feature more valuable over time, but it is non-trivial to ship safely.

The recommendation is: **feasible with caveats**. The architecture is sound, but the scope requires careful scoping of what Layer 2 actually owns versus Layer 1 and Layer 3, especially for roles like PM that already span coordinator + verifier duties. The discussion phase should resolve what "general role" means concretely before dev picks this up.

---

## Vault Context

- **BRIEFING.md priorities**: #3465 is listed at medium priority, Pending. v1.0.0 launch is the higher-priority context — any changes to role templates affect all agents and could delay launch if mishandled.
- **Related decisions**: [[decision-sub-skill-architecture]] — defines the 5-layer model; this proposal extends it with a new intermediate layer. Composition must remain build-time concatenation (Layer 2 would be additional includes in includes.yml order, not a new mechanism).
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — applies to any new Layer 1/2 boundary detection logic. [[decision-general-purpose-vision]] — non-dev teams increase the value of Layer 2 (a "content-creator" or "ops-analyst" general role benefits from a shared Layer 1 foundation).
- **Human preferences**: Prefers terse, mechanical systems. Prefers existing composition patterns over new mechanisms. Expects atomic migration. Values working agents over documentation. Context: [[human-profile]].
- **Related learnings**: [[learning-atomic-migration-strategy]] — the FEAT-SKILL-030 migration succeeded by shipping all phases in one dev cycle. This migration must follow the same pattern. A partial rollout where some roles use layered SOUL.md and others use flat SOUL.md would break soul_adaptation.py's rendering logic.

---

## Impact Analysis

- **Files touched**:
  - `references/roles/<role>/CLAUDE.md` — all 5 role templates must be refactored to split content into Layer 1 and Layer 3 portions, or add a Layer 2 include directive
  - `references/roles/<role>/SOUL.md` — all 5 role SOUL.md templates; currently flat single files, would need to become either: (a) Layer 3 only (with Layer 1 + Layer 2 SOUL sections assembled at compose time), or (b) remain flat but with structured sections for each layer
  - `references/roles/<role>/includes.yml` — order must encode Layer 1, then Layer 2, then Layer 3 includes
  - `references/sub-skills/common/` — some current common sub-skills may be reattributed to Layer 1 vs. Layer 2 distinction
  - A new directory would be needed for Layer 1 base content and Layer 2 general-role content (e.g., `references/roles/base/`, `references/roles/general/<category>/`)
  - `references/scripts/compose.py` — `_resolve_includes_with_manifest()` and `deploy_role()` need to handle the new directory layout if Layer 1 and Layer 2 live outside `references/roles/<role>/`; `{{runtime:}}` directive currently handles SOUL.md as a single flat file — layered SOUL would require new directive or pre-processing
  - `references/scripts/soul_adaptation.py` — `render_soul()` reads a single SOUL.md and replaces the `## Project Adaptation` section; if SOUL.md is now assembled from 3 layers it must either: (a) merge layers before writing, or (b) support per-layer adaptation sections
  - `references/scripts/wizard.py` — `deploy_role()` call chain; setup questions may need to reference general role type (e.g., "is this a developer-type agent or a delivery-type agent?")
  - `references/scripts/add_role.py` — same; variant resolution would need to know Layer 2 category to compose correctly
  - `references/roles/<role>/manifest.yaml` — would need a new field to declare which general-role (Layer 2) category applies
  - `references/sub-skills/manifest.md` — documentation of the new layer structure
  - `.claude/SKILL.md` (squidsquad-setup skill) — setup flow must install Layer 1, Layer 2, Layer 3 correctly
  - The `squidsquad-upgrade` skill — must regenerate Layer 1 + Layer 2 + Layer 3 without clobbering project-adapted SOUL.md

- **Behavior changes**:
  - Agents would boot with a richer identity stack (3 layers of SOUL.md merged vs. 1 flat file)
  - Compose output size would increase — Layer 1 and Layer 2 content currently embedded in individual role CLAUDE.md headers would be extracted and inlined separately
  - `deploy_role()` would need to concatenate 3 SOUL.md sources, not just copy 1
  - soul_adaptation.py's adaptation section would need to attach to the correct layer (Layer 3 is the right home — project-specific adaptations belong to the specific role, not the base agent)

- **Dependencies**:
  - PyYAML (already required for includes.yml parsing) — no new dependency
  - Manifest schema v2 (already in use) — a `general_role` field would be a schema v3 addition, requiring backward-compat handling in all manifest-reading code
  - All currently running agents — any agent running during the migration will be on the old flat SOUL.md; a full reboot cycle is required post-migration

---

## Side Effects

- **Risk 1**: Partial SOUL.md composition breaks soul_adaptation.py — if SOUL.md is now 3 files merged, the current "read live SOUL.md, find `## Project Adaptation`, replace it" logic in `render_soul()` still works only if the assembled SOUL.md is a single flat file. The merge must happen at deploy time, not render time. Severity: **H** — Mitigation: Layer assembly must produce a single flat SOUL.md at deploy time, identical in structure to current; soul_adaptation.py does not change.

- **Risk 2**: Role variant inheritance breaks — the dev role already has a special inheritance path (skill, be, fe variants without their own `includes.yml` fall back to `dev/includes.yml`). If Layer 2 categories are introduced (e.g., "developer" as the general role for dev/skill/be/fe), the inheritance logic in `_load_manifest()` must be updated to resolve Layer 1 → Layer 2 → Layer 3, not just dev → dev. If this is missed, new dev variants would silently compose with no Layer 2 content. Severity: **M** — Mitigation: Update `_load_manifest()` and `_get_entry_file_for_role()` as part of the same PR.

- **Risk 3**: SOUL.md "never overwrite" contract breaks — `deploy_role()` today writes SOUL.md only if missing (`if not soul_path.exists()`). If the upgrade must now regenerate SOUL.md from 3 layers (to pick up Layer 1 and Layer 2 changes), the "never overwrite" rule must become "re-render Layer 1+2 sections, preserve Layer 3 adaptations." This is a semantics change that could clobber project-customized Layer 3 content if not done carefully. Severity: **H** — Mitigation: On upgrade, only update Layer 1 and Layer 2 sections; treat Layer 3 as immutable (same as current behavior for the whole file).

- **Risk 4**: Running agents pick up an incomplete SOUL.md mid-cycle — if upgrade regenerates SOUL.md while an agent is mid-cycle, the agent reads an inconsistent identity file. Severity: **M** — Mitigation: Atomic write (write to `.tmp` then `mv`, same pattern as current-state writes). Compose.py already does write-then-rename for all outputs.

- **Risk 5**: Token budget inflation — merging 3 SOUL.md layers means the full `## Soul` section in the composed CLAUDE.md grows. Each agent currently embeds one SOUL reference via `{{runtime: souls/<role>}}`. If Layer 1 and Layer 2 add substantive instruction content, total token load increases for all agents. Severity: **L** — Mitigation: Keep Layer 1 and Layer 2 short (shared identity primitives only); Layer 3 is the primary identity layer.

---

## Edge Cases

- **PM as coordinator AND verifier**: PM's SOUL.md contains verification quality bar instructions that parallel QA's. Under a 3-layer model, where does "verifier" belong? If "verifier" is Layer 2 for both PM and QA, the Layer 2 SOUL content would be shared — but PM only verifies when QA is absent. This conditionality cannot be expressed in a static Layer 2 SOUL.md. Options: (a) PM Layer 3 keeps its verifier identity (no sharing with QA Layer 2); (b) Layer 2 contains only unconditional identity; (c) compose.py gains a conditional include mechanism. The current runtime check ("if QA present, PM skips verification") lives in pm-specific/testing-and-verification.md, not in SOUL.md — this edge case affects SOUL.md layering only.

- **The "skill" variant (dev variant without own role directory)**: `skill`, `be`, `fe` are dev variants with no `references/roles/skill/` directory. They currently inherit `dev/includes.yml`. Under the new model, their Layer 2 would be "developer". This works if Layer 2 is derived from the role identity (dev → developer). But if a human installs a `skill` agent and the manifest.yaml lookup fails to find Layer 2, they get no general role identity. Must be tested explicitly.

- **Capability sub-skills (Layer 5 in existing model)**: Capabilities (figma, google_stitch, local_html, local_delivery) compose via `{{capability: id}}` directive. They are the outermost layer and do not interact with role identity. The 3-layer proposal does not appear to affect them directly — capabilities remain unchanged.

- **Designer role**: Designer has a "Layer 5" capability sub-skill pattern (`common/capability-check`, plus designer-specific capabilities). If Layer 2 for designer is "creative-specialist", this general role would need its own capability-check behavior. Currently capability-check is in `common/` and included by designer and DM only. Layer 2 may need to carry the capability-check include rather than the specific role.

- **DM has no "general role" analog**: DM is a singleton delivery role — there is no family of "DM-type" roles. What is DM's Layer 2? If the answer is "delivery-manager" with only one member, Layer 2 adds zero reuse value for DM. The architecture must handle this gracefully — Layer 2 may simply be very thin for singleton roles.

- **Non-technical team roles (future)**: The general-purpose vision calls for non-dev teams. A "marketing-analyst" would need a Layer 2 ("content-creator" or "analyst") that no current role provides. The Layer 2 directory structure must be open for addition without requiring compose.py changes — the Q-new22 pattern of "any directory under `references/roles/` with a CLAUDE.md is a first-class identity" should extend to Layer 2 similarly.

---

## Integration Risks

- **compose.py `_resolve_includes_with_manifest()`**: The manifest resolution loop handles `{{include:}}`, `{{capability:}}`, and `{{runtime:}}` directives. If Layer 2 content is injected as additional includes (new entries in includes.yml at a well-known position), compose.py needs no code change — includes.yml ordering already handles layer sequencing. If Layer 2 requires a new directive type (e.g., `{{layer2: developer}}`), compose.py must be updated.

- **soul_adaptation.py SOUL rendering**: The adaptation script locates `## Project Adaptation` and `<!-- /project-adaptation -->` markers in the flat SOUL.md. If SOUL.md is assembled from 3 layers at deploy time into one flat file (recommended approach), soul_adaptation.py is unaffected. If SOUL.md remains split into multiple files at runtime, the script breaks.

- **squidsquad-upgrade skill**: The upgrade skill runs `compose.py deploy-all`. If the 3-layer model changes what `deploy_role()` emits (e.g., assembling SOUL.md from 3 sources), upgrade automatically picks up the new behavior. The SOUL.md "never overwrite" contract must be revised to "re-render Layer 1+2 sections on upgrade, preserve Layer 3" — this requires a new `upgrade_soul()` function in compose.py distinct from the current `deploy_role()` SOUL logic.

- **wizard.py and add_role.py**: Setup questions in manifest.yaml `setup_requirements` are role-specific. A Layer 2 "developer" general role might have setup questions of its own (e.g., "does this developer agent specialize in a sub-discipline?"). These would need to be asked before Layer 3-specific questions. wizard.py's question chain would need to be updated to walk Layer 1 → Layer 2 → Layer 3 requirements in order.

- **health_check.py and diagnostics.py**: These check for the presence of `CLAUDE.md` and `SOUL.md` under `.squidsquad/<role>/`. They do not inspect layer structure. No change needed if the deployed artifacts remain single files.

- **`pm-specific/soul-shepherd`**: This sub-skill monitors character signals in agent Discussion entries and invokes soul_adaptation.py to add signals to role-adaptations.md. It targets `references/roles/<role>/SOUL.md` as the source template. Under 3-layer model, "which layer does a character signal belong to?" becomes a new decision: signals are almost certainly Layer 3 (project-specific) and soul-shepherd's behavior should be unchanged.

---

## Upgrade & Migration

- **New config values**: None anticipated — layer discovery would be manifest-driven, not config.md driven.
- **New files**:
  - `references/roles/base/CLAUDE.md` — Layer 1 base agent template (extracted from the header common to all current CLAUDE.md files: Ralph Loop preamble, boot instructions, status bar pattern, `[ROLE]` placeholder, prohibitions shared by all)
  - `references/roles/base/SOUL.md` — Layer 1 base soul (shared identity primitives: "you are a SquidSquad agent", timestamp discipline, atomic writes, sub-agent model preference)
  - `references/roles/general/<category>/CLAUDE.md` — one per general role family (e.g., `developer/`, `verifier/`, `delivery/`, `design/`, `coordinator/`)
  - `references/roles/general/<category>/SOUL.md` — one per general role family
  - Possibly `references/roles/<role>/manifest.yaml` would gain `general_role: <category>` field
- **Template changes**:
  - All 5 role `CLAUDE.md` templates would have their common header sections replaced by `{{layer1:}}` or `{{include: base/...}}` directives
  - All 5 role `SOUL.md` templates would have their shared identity sections (professional identity primitives, subagent model preference, timestamp discipline) moved to Layer 1
  - The `{{runtime: souls/<role>}}` directive currently expands to a single "read SOUL.md" instruction — under layered SOUL.md, deploy time assembly of 3 SOUL files into one avoids changing this directive
- **Upgrade steps** (`squidsquad-upgrade` must):
  1. Re-run `compose.py deploy-all` — this picks up the new Layer 1+2+3 composition automatically if compose.py is updated
  2. For SOUL.md: re-render Layer 1 and Layer 2 sections into the existing `.squidsquad/<role>/SOUL.md` without clobbering the `## Project Adaptation` section — requires a new `upgrade_soul(role)` function
  3. Reboot all agents after upgrade so the new composition is loaded from the fresh CLAUDE.md and SOUL.md
- **Graceful degradation**: If a user does not upgrade, they continue running the old flat single-layer composition. Running agents are not broken — they were composed with the old structure at the last deploy time. They simply do not get the new layered identity. No breakage, no coordination loss. The only "miss" is that new roles added after the architecture change would fail to compose if the old compose.py does not understand the new directives.

---

## Capability Gaps

- **No `{{layer1:}}` or `{{layer2:}}` directive in compose.py**: The current engine handles `{{include:}}`, `{{capability:}}`, and `{{runtime:}}`. If layers are implemented purely as `includes.yml` ordering (Layer 1 includes first, then Layer 2 includes, then Layer 3 includes), no new directive is needed. If layers require a dedicated directive for clarity and tooling, compose.py must be extended.
- **No multi-source SOUL.md assembly in compose.py**: `deploy_role()` copies one `SOUL.md` template to `.squidsquad/<role>/SOUL.md`. If SOUL.md must be assembled from 3 layers, a new assembly step is needed before the copy.
- **No `upgrade_soul()` function in compose.py**: The current SOUL.md "never overwrite" contract must be revised for upgrade; a new function that merges Layer 1+2 updates into the existing Layer 3 + Project Adaptation content does not exist.
- **No general-role directory structure**: `references/roles/general/` does not exist. The entire directory hierarchy for Layer 2 must be created.
- **capability_check.py targets `references/roles/<role>/manifest.yaml`**: It reads `requires_sub_skills` from the role-level manifest. If Layer 2 general roles can have their own capability requirements, capability_check.py would need to walk Layer 1 → Layer 2 → Layer 3 manifests and merge `requires_sub_skills`. Currently only Layer 3 (specific role) manifests are checked.

---

## Open Questions

- **Q1**: What content actually belongs in Layer 2 (general role) vs. is already adequately covered by `common/` sub-skills? — **Why**: If "developer" general role CLAUDE.md would contain only what's already in `common/tracker-protocol`, `common/cycle-runner`, etc., Layer 2 adds no code and only adds a structural concept with no operational difference. The value proposition of Layer 2 must be demonstrated with concrete content that is not already shared.

- **Q2**: How does SOUL.md layering work at runtime — single assembled file or multi-file read? — **Why**: If the agent reads 3 separate SOUL.md files at boot, it requires a new boot-time instruction chain and changes the `{{runtime:}}` directive behavior. If compose.py assembles them into one file at deploy time, no agent change is required. Getting this wrong means either (a) broken agent boot sequences or (b) wasted compose complexity.

- **Q3**: What is the Layer 2 general role for PM? — **Why**: PM combines coordinator + verifier duties. If Layer 2 is "coordinator", PM's verifier behavior becomes orphaned in Layer 3. If Layer 2 is "coordinator+verifier", QA cannot share it (QA is pure verifier). If Layer 2 is left empty for PM, the feature delivers zero benefit to the most important role.

- **Q4**: Does this interact with the #3415 comms layer (Telegram adapter sub-skills)? — **Why**: Comms-layer sub-skills (`common/chat-etiquette`, `common/mention-protocol`, `common/consensus-protocol`) are currently in `common/` and optional. If Layer 2 is introduced, these may belong at Layer 2 (they're role-family-specific, not universal) or remain in `common/`. Misplacing them into Layer 2 prematurely could break the feature-flag gating that controls their inclusion.

- **Q5**: How does the "skill" dev variant (no own role directory) map to Layer 2? — **Why**: `skill`, `be`, `fe` inherit from `dev`. If Layer 2 is "developer", do dev variants inherit Layer 2 from `dev`? Or do they need their own Layer 2 manifest reference? The inheritance chain in `_load_manifest()` must be explicitly specified or variant agents will silently compose without a general role.

---

## Recommendation

**Feasible with caveats.** The architecture is a natural extension of the existing 5-layer sub-skill model and aligns with the general-purpose vision. The composition engine (compose.py) is flexible enough to accommodate the change without a redesign — Layer 2 can be implemented as additional includes.yml entries at a well-known position. The critical risks are:

1. SOUL.md assembly must be resolved before dev starts — flat single-file output at deploy time is the only approach compatible with soul_adaptation.py without changing that script.
2. Upgrade atomicity — must ship all roles simultaneously, following [[learning-atomic-migration-strategy]].
3. Q1 (what actually goes in Layer 2) and Q3 (PM's general role) must be answered in the Discussion phase — without concrete answers, dev cannot scope the implementation and there is a real risk of building a structural concept with no operational content.

Do not proceed to planning until Q1, Q2, Q3 are locked.

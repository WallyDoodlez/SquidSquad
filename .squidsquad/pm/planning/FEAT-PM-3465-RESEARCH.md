# FEAT-PM-3465 Research — Layered Role Definition Architecture (Updated)

## Summary

This research covers the updated 3-layer model after human clarification. The revised model is:

- **Layer 1 — Agent Definition**: What any SquidSquad agent IS. Shared by ALL agents: Ralph Loop, tracker protocol, vault protocol, health/heartbeat, cycle runner, context pressure, git protocol, base identity.
- **Layer 2 — Role Definition**: What a `<role>` agent IS. The concrete role (pm, dev, qa, dm, designer). Role-specific workflow, responsibilities, quality bar, SOUL.md.
- **Layer 3 — Role Customization**: Specialization of a role. Examples: skill/be/fe dev variants; PM-for-coding vs PM-for-market-research; QA-security vs QA-general.

This is a significant scope reduction from the original research. The original proposed a "general role" intermediate grouping (coordinator/verifier/developer) that does not map to any existing role structure. That concept is gone. Layer 2 IS the concrete role — there is no new directory tree for general categories.

**Key finding**: The architecture is already partially layered. `references/sub-skills/common/` is Layer 1. `references/roles/<role>/` + `<role>-specific/` sub-skills is Layer 2. Dev variants (skill, be, fe) that inherit from `dev` are already Layer 3. The feature formalizes existing patterns, introduces first-class Layer 3 customization for non-dev roles, and applies matching SOUL.md layering.

**Blast radius is substantially smaller than originally assessed.** No new general-role directory tree. No new compose.py directive type needed. No new manifest field required for the core feature — Layer 3 customization uses the same `_get_entry_file_for_role()` / `_load_manifest()` inheritance already used by dev variants.

**Recommendation: Feasible and lower-risk than originally scoped.** The primary open question is what Layer 3 customizations for non-dev roles look like in practice (PM-for-coding doesn't exist yet — what would its sub-skills and SOUL.md overlay contain?). The boundary between Layer 1 and Layer 2 also needs explicit documentation so future role additions know where to place shared vs role-specific content.

---

## Vault Context

- **BRIEFING.md priorities**: #3465 is medium priority, Pending. v1.0.0 launch is the higher-priority context — this feature is not on the critical path for launch but prepares the architecture for the general-purpose expansion that follows.
- **Related decisions**: [[decision-sub-skill-architecture]] — defines the existing 5-layer sub-skill model. This proposal formalizes it into named layers without changing the underlying mechanism (build-time concatenation via includes.yml). Composition mechanism is unchanged.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — applies to any Layer 1/2/3 boundary detection. The boundary is structural (directory and includes.yml position), not a runtime check. [[decision-general-purpose-vision]] — non-dev teams are the motivation for making Layer 3 customization first-class for all roles, not just dev.
- **Human preferences**: Prefers existing patterns extended over new mechanisms invented. Prefers terse, mechanical systems. Prefers atomic migrations. Layer 3 for non-dev roles is genuinely new, but it follows the existing dev-variant pattern exactly. Context: [[human-profile]].
- **Related learnings**: [[learning-atomic-migration-strategy]] — any migration that touches all role templates must ship atomically. The reduced blast radius makes atomicity easier to achieve here than in the original scope.

---

## Impact Analysis

**Current state mapping to new layers:**

| Layer | Current artifact | Status |
|-------|-----------------|--------|
| Layer 1 | `references/sub-skills/common/*.md` + CLAUDE.md shared header | Exists, informal |
| Layer 2 | `references/roles/<role>/CLAUDE.md` + `<role>-specific/*.md` + `SOUL.md` | Exists, formal |
| Layer 3 | `skill`, `be`, `fe` dev variants inheriting from `dev` | Exists for dev only |

**What already exists (no new code):**

- `common/` sub-skills ARE Layer 1. They are included first in all `includes.yml` manifests. The ordering already encodes Layer 1 → Layer 2.
- Dev variant inheritance in `_load_manifest()` and `_get_entry_file_for_role()` IS the Layer 3 mechanism. `skill` inherits `dev`'s `includes.yml`; `fe` and `be` do the same.
- SOUL.md is already role-specific (Layer 2). `dev/SOUL.md`, `pm/SOUL.md`, `qa/SOUL.md` are distinct files with distinct professional identities.

**What is genuinely new:**

1. **Formal Layer 1 boundary documentation** — no file currently says "these common sub-skills are Layer 1 and are shared by all agents." The distinction lives only implicitly in the directory name. New: a note in `references/sub-skills/manifest.md` (or a new `references/docs/layer-model.md`) declaring which sub-skills are Layer 1 and the rules for Layer 2 additions.

2. **Layer 3 customization for non-dev roles** — `pm-for-coding`, `pm-for-market-research`, `qa-security`, `qa-general` do not exist yet. Creating them requires: (a) a role-specific entry file at `references/roles/<role>-<variant>/CLAUDE.md` that references the base role's sub-skills, OR (b) extending the inheritance logic in `_load_manifest()` to support non-dev role inheritance. Currently only `dev` variants are supported.

3. **SOUL.md layering for Layer 3** — dev variants do NOT have their own `SOUL.md` today — they inherit the `dev/SOUL.md` template. A Layer 3 customization for PM would need either (a) its own full SOUL.md (all of Layer 2 PM content + customizations), or (b) a SOUL.md overlay/patch mechanism at deploy time. Option (a) is simpler and follows existing patterns.

4. **Layer 3 inheritance generalization in compose.py** — `_load_manifest()` currently hard-codes `dev` as the only fallback parent. To support `pm-for-coding` inheriting from `pm`, the fallback must be generalized: if a role has no `includes.yml`, walk to the "base role" name by stripping the variant suffix (e.g., `pm-for-coding` → `pm`). This requires a naming convention decision.

**Files touched:**

- `references/scripts/compose.py` — `_load_manifest()` and `_get_entry_file_for_role()` need generalized inheritance logic (currently dev-only). Low risk — well-isolated functions.
- `references/sub-skills/manifest.md` — document Layer 1 vs Layer 2 boundary. Informational only, no behavior change.
- New files for any Layer 3 variants created as examples (e.g., `references/roles/pm-for-coding/CLAUDE.md`, `references/roles/pm-for-coding/SOUL.md`). These are additive.
- No changes required to existing role CLAUDE.md templates.
- No changes required to existing SOUL.md templates.
- No changes required to `includes.yml` files for existing roles.
- No changes required to `soul_adaptation.py` — SOUL.md remains a flat single file at deploy time.
- No changes required to `wizard.py` or `add_role.py` for the core feature (though `add_role.py` could be extended to scaffold Layer 3 variants).

**Behavior changes:**

- None for existing agents — all current roles compose identically.
- New Layer 3 variants compose using inherited `includes.yml` from their base role, plus any variant-specific overrides. Same mechanism as dev variants today.

**Dependencies:**

- PyYAML (already required) — no new dependency.
- Naming convention decision for Layer 3 variants (see Open Questions).

---

## Side Effects

- **Risk 1**: Layer 3 naming convention collides with existing role directory names. If `pm-for-coding` is the convention but someone creates `references/roles/pm/` variants, `_list_known_role_identities()` returns them as first-class roles, not variants. Severity: **L** — Mitigation: Adopt a clear naming convention (`<base>-<variant>`) and document it. The filesystem-based identity detection already handles this correctly as long as only directories with `CLAUDE.md` are treated as identities.

- **Risk 2**: SOUL.md inheritance for non-dev Layer 3 variants. Dev variants today silently fall back to `dev/SOUL.md` when no variant `SOUL.md` exists. This behavior is in `deploy_role()`: it calls `_get_entry_file_for_role()` to get the role identity, then looks for `SOUL.md` at the identity's template path. A `pm-for-coding` variant with no `SOUL.md` would get `pm/SOUL.md` automatically — this is correct behavior for Layer 3. No code change needed; documenting this as intentional is sufficient. Severity: **L**.

- **Risk 3**: Layer 1 / Layer 2 boundary drift over time. Without a formal definition, new contributors may add Layer 2 (role-specific) content to `common/`, diluting the "truly shared" guarantee of Layer 1. Severity: **M** — Mitigation: `manifest.md` annotation (new file) that lists which common sub-skills are Layer 1 and the criteria for adding to Layer 1 vs Layer 2.

- **Risk 4**: Token budget increase for Layer 3 variants. A `pm-for-coding` variant would have PM's full SOUL.md (Layer 2) + customization content (Layer 3). If Layer 3 adds a new SOUL section on top of Layer 2, the total soul content grows. Severity: **L** — Mitigation: Layer 3 SOUL.md replaces Layer 2 entirely (full file) rather than appending. Same deploy-time assembly behavior, no runtime change.

---

## Edge Cases

- **Dev variant inheritance (existing Layer 3)**: `skill`, `be`, `fe` have no `includes.yml`. They fall back to `dev/includes.yml` via `_load_manifest()`. Under the new model, these are concrete Layer 3 examples. No behavioral change — they already work. The feature simply names what they are.

- **PM as coordinator AND verifier**: PM's SOUL.md contains both coordination and verification identity because PM falls back to QA duties when QA is absent. Under Layer 2 = concrete role, this is correct — PM's Layer 2 identity is the full PM, including the fallback verifier. A Layer 3 `pm-for-coding` would STILL include all PM Layer 2 content; it would only add project-type-specific customization on top. No cross-role SOUL sharing needed.

- **Singleton roles (DM)**: DM has no family of variants — it is a singleton. Layer 3 for DM (e.g., `dm-for-internal-tools`) is theoretically possible but unlikely. The architecture handles this gracefully: a singleton role simply has no Layer 3 customizations. No special case needed.

- **Designer with capability sub-skills**: Designer and DM include `common/capability-check` in their `includes.yml`. This is a Layer 1 sub-skill that is optional (only included by roles that use external capabilities). Under the new model, it remains in `common/` but is not included by all roles — it is a conditional Layer 1 sub-skill. The naming convention (or manifest annotation) should distinguish "universal Layer 1" from "conditional Layer 1 (included only when capabilities are required)."

- **Non-technical team roles (future)**: A future `content-creator` or `ops-analyst` role would be a new Layer 2 role. It would need its own `references/roles/<role>/CLAUDE.md`, `SOUL.md`, `includes.yml`, and role-specific sub-skills. Layer 1 common sub-skills would be included as the first entries in its `includes.yml`. No compose.py change needed — the `_list_known_role_identities()` function already treats any directory with a `CLAUDE.md` as a first-class identity. This is the cleanest part of the existing architecture.

- **QA includes slim variants**: QA uses `common/improvement-scan-slim` and `common/vault-protocol-slim` instead of the full versions. These are Layer 1 sub-skills with variant selection — the QA `includes.yml` explicitly selects the slim variant. A `qa-security` Layer 3 variant would inherit QA's `includes.yml` and could override specific entries via its own `includes.yml`. The manifest's variant-matching logic in `_resolve_includes_with_manifest()` handles base-name prefix matching — this already works for slim variants.

---

## Integration Risks

- **compose.py `_load_manifest()` hardcodes dev fallback**: Lines 116-120 check if the role is not in the known identities list and falls back to `dev`. To support `pm-for-coding` → `pm` inheritance, this must be generalized: strip the variant suffix from the role name and look for a matching base role. The simplest approach is a naming convention (`<base>-<variant>`) with a suffix strip: `pm-for-coding`.split("-")[0] = `pm`. This is a 3-line change with no impact on existing roles.

- **`_get_entry_file_for_role()` hardcodes dev fallback**: Same function logic — currently returns `"dev"` for any unknown role. Must return the base role name for non-dev variants. The same suffix-strip logic applies.

- **soul_adaptation.py is unaffected**: SOUL.md remains a flat single file. Layer 3 variants have their own full SOUL.md (or inherit Layer 2's via the fallback). The `## Project Adaptation` marker pattern is unchanged.

- **squidsquad-upgrade**: `deploy_role()` currently writes SOUL.md only if missing. Layer 3 variant SOUL.md files at `references/roles/<variant>/SOUL.md` would be picked up on first deploy and never overwritten. This is correct behavior — identical to how dev variants work today.

- **wizard.py and add_role.py**: The current wizard creates a new role directory with boilerplate. It could be extended to scaffold Layer 3 variants (prompt: "base role to inherit from?"), but this is not required for the core feature. Layer 3 variants can be created manually by copying the base role's CLAUDE.md and customizing it.

- **health_check.py and diagnostics.py**: These check for `.squidsquad/<role>/CLAUDE.md` and `.squidsquad/<role>/SOUL.md`. Layer 3 variant agents would deploy to `.squidsquad/pm-for-coding/` — health checks work automatically. No change needed.

---

## Upgrade & Migration

- **New config values**: None.
- **New files**:
  - `references/sub-skills/manifest.md` (update existing or create `references/docs/layer-model.md`) — annotates which common sub-skills are Layer 1, documents Layer 2 and Layer 3 conventions.
  - `references/roles/<variant>/CLAUDE.md` + `SOUL.md` — for any new Layer 3 variants shipped as examples (e.g., `pm-for-coding` if the human wants a concrete example).
- **Template changes**: None to existing templates. Layer 3 variants are additive new directories.
- **Script changes**: `compose.py` — `_load_manifest()` and `_get_entry_file_for_role()` generalized from `dev`-only fallback to `<base>-<variant>` suffix-strip pattern. This is backward compatible — existing dev variants (`skill`, `be`, `fe`) still resolve to `dev` because `skill` does not match any other base role, so the suffix strip falls through to the existing `dev` fallback.
- **Upgrade steps**: None required for existing installs. The compose.py change is transparent — all existing roles compile identically. New Layer 3 variants are opt-in.
- **Graceful degradation**: If a user does not upgrade, all existing agents continue to work. Layer 3 customization is opt-in — existing installs have no Layer 3 variants and are unaffected. The only user-visible change is that `compose.py` gains the ability to resolve non-dev variant inheritance.

---

## Capability Gaps

- **No generalized Layer 3 inheritance in compose.py**: Currently only `dev` variants (skill, be, fe) can inherit from a base role. Non-dev Layer 3 variants (`pm-for-coding`, `qa-security`) require `_load_manifest()` and `_get_entry_file_for_role()` to be generalized. This is a small, well-scoped change.
- **No Layer 3 SOUL.md overlay mechanism**: Layer 3 variants must provide a full SOUL.md (not just a diff/patch on Layer 2). This is intentional simplicity — same approach as dev variants today. The limitation is that Layer 3 SOUL.md must maintain its own copy of Layer 2 identity sections. This is acceptable; SOUL.md files are short (~100 lines) and rarely change.
- **No scaffolding for non-dev Layer 3 variants in add_role.py**: `add_role.py` could be extended to scaffold a new variant by prompting for a base role and copying from it. This is a nice-to-have, not required for the core feature.
- **No formal Layer 1 boundary declaration**: The distinction between "universal Layer 1" sub-skills and "conditional Layer 1" (capability-check) is not documented anywhere. A `manifest.md` annotation resolves this.
- **No example Layer 3 variants for non-dev roles**: `pm-for-coding` and `qa-security` do not exist. The feature is complete without them (the mechanism exists once compose.py is updated), but examples help future contributors understand the pattern.

---

## Open Questions

- **Q1**: What naming convention for Layer 3 non-dev variants? — **Why**: `_load_manifest()` must strip the variant suffix to find the base role. Options: (a) `<base>-<variant>` (e.g., `pm-for-coding`, `qa-security`) — simple string operations, human-readable; (b) `manifest.yaml` declares `base_role` field for variants. Option (a) is consistent with how `skill`, `be`, `fe` are named (dev variants without prefix). Option (b) is more explicit but adds a schema field. Recommendation: option (a) with a documented hyphen convention, falling back to option (b) only if naming collisions occur.

- **Q2**: Should the feature ship with at least one concrete Layer 3 example for a non-dev role? — **Why**: Without an example, the feature is purely structural. With `pm-for-coding` as a shipped example, the pattern is demonstrable and the mechanism is tested end-to-end. The risk of skipping an example is that the inheritance path for non-dev variants is not exercised and may have edge cases.

- **Q3**: What is the exact Layer 1 sub-skill set? — **Why**: All five `includes.yml` files include `common/tracker-protocol` and `common/cycle-runner` first — these are clearly Layer 1. But `common/vault-protocol` is NOT included by QA and designer (they use slim variants, and QA uses `vault-protocol-slim`). Is `vault-protocol` Layer 1, or is it Layer 2 for write-capable roles? The boundary affects the documentation but not the code.

- **Q4**: Does `common/boot-remote-agents` belong in Layer 1 or Layer 2? — **Why**: Currently only PM includes `boot-remote-agents`. It is in `common/` but is PM-specific in practice. This is an example of a sub-skill that lives in `common/` but is NOT Layer 1. The `manifest.md` annotation must distinguish "in common/ but role-specific" from "truly Layer 1 (all agents)."

- **Q5**: Should Layer 3 SOUL.md be a full file or an overlay? — **Why**: Full file (current approach for dev variants) is simple but requires Layer 3 maintainers to copy and modify the Layer 2 SOUL.md. An overlay (patch) would be cleaner architecturally but requires a new merge mechanism in `deploy_role()`. Recommendation: full file for simplicity, consistent with dev variants. Document that Layer 3 SOUL.md should start with the Layer 2 SOUL.md as its base.

---

## Recommendation

**Feasible, lower-risk than originally scoped, and architecturally sound.** The core insight is that the 3-layer model is already implemented — it just lacks formal naming and the Layer 3 inheritance path is hard-coded to `dev` only.

**Concrete scope for dev pickup:**

1. Generalize `_load_manifest()` and `_get_entry_file_for_role()` in compose.py to support `<base>-<variant>` suffix naming for all roles (not just dev). ~10 lines of code.
2. Add `references/sub-skills/manifest.md` (or update existing) documenting the Layer 1 set and Layer 2/3 conventions. Documentation-only.
3. Optionally: create one concrete Layer 3 example (`pm-for-coding` or `qa-security`) to prove the mechanism end-to-end.

**What does NOT need to change:** All existing role templates, all `includes.yml` files, `soul_adaptation.py`, `wizard.py`, `add_role.py` (core behavior), `health_check.py`, and the upgrade skill.

Q1 (naming convention) and Q5 (SOUL.md approach) should be locked in Discussion before dev pickup. Q2 (example variant) is the human's call — it affects scope but not architecture.

## Vault Candidates

- **Type**: decision — "Layer 3 variants use full SOUL.md, not overlay patches" — **Why**: This resolves the recurring question of whether to introduce a merge mechanism; locking it as a decision prevents re-opening it during implementation.
- **Type**: pattern — "Existing `common/` sub-skills are implicitly Layer 1; role-specific sub-skills are Layer 2; inherited dev variants are Layer 3 — the architecture was already layered before it had names." — **Why**: This reframes the feature as formalization rather than invention, which is the correct mental model for all future contributors.
- **Type**: learning — "`common/` does not mean Layer 1 — `boot-remote-agents` is in common/ but is PM-only. Directory placement is a convention hint, not a Layer 1 guarantee." — **Why**: Prevents future sub-skills from being placed in `common/` when they should be role-specific, just because they are 'shared' between two roles.

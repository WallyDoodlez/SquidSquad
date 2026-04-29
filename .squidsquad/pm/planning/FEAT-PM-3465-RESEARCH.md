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

---

## CLAUDE.md Layering Analysis

### Current CLAUDE.md Composition

**The three-file mechanism**: Each role has a `references/roles/<role>/CLAUDE.md` entry file containing inline prose and `{{include: path}}` directives. `compose.py` reads the entry file, resolves each directive by inlining the sub-skill file, and writes the flat output to `.squidsquad/<role>/CLAUDE.md`.

**The manifest's role**: `includes.yml` for each role lists the sub-skills in order. `_resolve_includes_with_manifest()` uses this list to: (a) enforce include order, (b) resolve variant substitutions (e.g., `vault-protocol` → `vault-protocol-slim`), and (c) skip any `{{include:}}` directive not in the manifest (enabling manifest-driven removal). The manifest is the authoritative ordering layer, not the entry file's directive order.

**How Layer 1 and Layer 2 are already ordered in includes.yml**: Every role manifest opens with the same block in identical order:

```
common/tracker-protocol   ← Layer 1 (universal)
common/cycle-runner       ← Layer 1 (universal)
common/context-pressure   ← Layer 1 (universal)
```

Layer 2 sub-skills (`pm-specific/checkin`, `dev-specific/triage-issues`, etc.) follow immediately after. The manifest itself encodes the Layer 1 → Layer 2 boundary by position: the first N entries are `common/` (Layer 1), then role-specific entries begin (Layer 2). This is convention, not an enforced separator.

**SOUL.md is entirely separate from CLAUDE.md composition**: `deploy_role()` handles SOUL.md independently — it reads `references/roles/<role>/SOUL.md` and writes it to `.squidsquad/<role>/SOUL.md` only if the destination is missing. CLAUDE.md composition and SOUL.md deployment are two distinct code paths. A Layer 3 variant's CLAUDE.md composition does not affect SOUL.md deployment, and vice versa.

**Layer 3 dev variants today**: `skill`, `be`, and `fe` have no `includes.yml` and no `CLAUDE.md` in `references/roles/`. When `_load_manifest("skill")` is called:
1. No `references/roles/skill/includes.yml` found.
2. `_list_known_role_identities()` returns `{dev, pm, qa, dm, designer}` — `skill` is not in this set.
3. Fallback to `references/roles/dev/includes.yml` — uses dev's full manifest.
4. `compose_role("skill")` calls `_get_entry_file_for_role("skill")` → returns `"dev"` → composes from `references/roles/dev/CLAUDE.md`.

The result: `skill` gets an identical CLAUDE.md to `dev`, with `[ROLE]` substituted to `skill`. There is no Layer 3-specific CLAUDE.md content today — dev variants are purely identity substitutions at composition time, not content customizations.

**Key insight about the current model**: Layer 3 dev variants currently contribute ZERO unique CLAUDE.md content. They are role-name aliases for `dev`. The 3-layer model for CLAUDE.md is therefore **not yet implemented for Layer 3** — the current system only layers L1 and L2. SOUL.md layering was the only mechanism that gave dev variants distinct character.

---

### Layer 3 CLAUDE.md Strategy

**The core question**: What should a `pm-skill` CLAUDE.md contain that `pm` CLAUDE.md does not?

**Option A: Additive sub-skills only (recommended)**

Layer 3 variants add one or more variant-specific sub-skills appended after the base role's full manifest. A `pm-skill` variant would have its own `includes.yml` that either:
- (a1) Explicitly duplicates the base role's manifest entries plus appends variant-specific entries, OR
- (a2) Declares only the *additional* sub-skills, with compose.py automatically prepending the base role's manifest.

Option (a1) is simpler — no new compose.py logic needed. The variant's `includes.yml` is self-contained. The downside: updating the base role's manifest requires updating all variants' manifests too (drift risk). For 20 presets × 5 roles this is manageable.

Option (a2) requires a `base_role` field in the variant's `includes.yml` and new compose.py logic to merge manifests. More elegant long-term, but adds a new schema field and merge logic.

**Recommendation: Option (a2) with an explicit `base_role` field in includes.yml.** Rationale:

- 20 presets × 4 roles = 80 variant manifests. Duplicating 15-30 base entries in each is ~1,200-2,400 lines of copy-paste that will drift.
- The `base_role` field is a single YAML key, well-scoped change to `_load_manifest()`.
- Precedent: `_load_manifest()` already does implicit base-role lookup for dev variants. Making it explicit via a YAML field is cleaner and extends to all roles.
- The field is optional — base roles have no `base_role` field, variants declare it. Backward compatible.

**Option B: Full replacement CLAUDE.md (rejected)**

Like Layer 3 SOUL.md, the variant provides a complete entry file with all L1+L2+L3 content. This works but: (a) the entry file would be enormous (copy of the full base role CLAUDE.md plus additions), (b) any base role update requires manual re-copying to all variants, (c) this is the exact copy-paste problem the layered architecture is meant to eliminate.

**Option C: Section overrides (rejected)**

Replace specific sub-skill sections in the composed output. This requires a new directive type or a post-processing step. Out of scope per CONTEXT.md ("No new compose.py directive types").

**Layer 3 CLAUDE.md content model (with Option A2)**:

Each Layer 3 variant has:
- `references/roles/<variant>/includes.yml` — declares `base_role: <base>` and `additional_includes: [<list>]`
- `references/roles/<variant>/CLAUDE.md` — entry file containing ONLY the variant-specific inline prose and `{{include:}}` directives for the additional sub-skills (no repetition of base role content)
- `references/sub-skills/<variant>-specific/` — new sub-skill files for variant-specific behavior

The compose pipeline for a Layer 3 variant:
1. Load variant's `includes.yml` → sees `base_role: pm`
2. Load base role's `includes.yml` (pm's manifest)
3. Append variant's `additional_includes` to the base manifest
4. Use the merged manifest to compose from the variant's entry file
5. The variant's entry file includes only the additional `{{include:}}` directives (the base role's are resolved from the merged manifest even though they don't appear in the variant entry file)

**However**: step 5 has a subtlety. The entry file must contain all the directives that produce the base role's prose (non-include content) AND the additional includes. The cleanest solution: the variant's entry file extends the base role's entry file by reference — it is `{{include: roles/pm/CLAUDE.md}}` plus additions, or it inherits the base entry file directly.

**Simpler implementation path**: The variant's `includes.yml` uses `base_role` to merge manifests, and the variant's `CLAUDE.md` entry file uses `{{extend: pm}}` (new directive) to inherit the base entry file's prose + directives, then appends only the additional directives. The `{{extend:}}` directive is resolved first by inlining the base entry file.

**Even simpler (no new directive needed)**: The variant entry file IS the base entry file plus additions. compose.py already supports this if the merged manifest is built correctly. The implementation becomes:
- Variant `includes.yml` declares `base_role: pm` and `additional_includes: [pm-skill-specific/deterministic-boundary]`
- `_load_manifest()` for a variant: load base role manifest, append `additional_includes`, return merged list
- Variant `CLAUDE.md` entry file: copy of base role's `CLAUDE.md` PLUS additional `{{include:}}` directives at the end
- No new directive type needed

The entry file copy is the only duplication — but it's the prose scaffold, not the sub-skill content. For PM, the entry file is ~80 lines; dev is ~100 lines. This is acceptable.

**Final recommendation**: Hybrid approach — `base_role` field in `includes.yml` for manifest merging (eliminates sub-skill list duplication), variant entry file copies the base entry file and adds variant includes at the end (prose scaffold duplication accepted). This minimizes new compose.py logic while avoiding the bulk of copy-paste.

---

### compose.py Changes Required

**Change 1: Generalize `_load_manifest()` for non-dev variants** (already planned in prior research)

Current code (lines 116-120):
```python
if not manifest_path.exists():
    identities = _list_known_role_identities()
    if role_name not in identities and "dev" in identities:
        manifest_path = ROLES_DIR / "dev" / "includes.yml"
```

New behavior: if the variant has its own `includes.yml` with a `base_role` field, merge the base role's manifest with the variant's `additional_includes`. If no own `includes.yml`, fall back to suffix-strip base role lookup (existing dev behavior).

Pseudocode:
```python
def _load_manifest(role_name):
    manifest_path = ROLES_DIR / role_name / "includes.yml"
    if manifest_path.exists():
        data = yaml.safe_load(manifest_path.read_text())
        base_role = data.get("base_role")
        if base_role:
            # Layer 3 variant — merge base + additional
            base_manifest = _load_manifest(base_role) or []
            additional = data.get("additional_includes", [])
            return base_manifest + additional
        else:
            # Layer 2 base role — use as-is
            return data["includes"]
    else:
        # No manifest — fall back to suffix-strip base role or dev
        base = _strip_variant_suffix(role_name)
        if base and base in _list_known_role_identities():
            return _load_manifest(base)
        if "dev" in _list_known_role_identities():
            return _load_manifest("dev")
        return None
```

**Change 2: `_get_entry_file_for_role()` for non-dev variants with own CLAUDE.md**

If a variant has its own `references/roles/<variant>/CLAUDE.md`, use it directly. Otherwise fall back to base role's entry file.

Current: if role not in identities, return "dev".
New: if role not in identities, strip suffix to find base role identity, return that (or "dev" as final fallback).

If a variant HAS its own `CLAUDE.md` (i.e., it's in `_list_known_role_identities()`), it uses its own entry file — no change needed for that case. The change is only needed for variants that inherit the base entry file without their own CLAUDE.md (the suffix-strip fallback path).

**Change 3: `_strip_variant_suffix()` helper (new, ~5 lines)**

```python
def _strip_variant_suffix(role_name: str) -> str | None:
    """Strip variant suffix to find base role: 'pm-skill' -> 'pm', 'dev-ios' -> 'dev'."""
    identities = _list_known_role_identities()
    if "-" in role_name:
        base = role_name.rsplit("-", 1)[0]
        if base in identities:
            return base
    return None
```

**Total compose.py changes**: ~25 lines of new/modified code across `_load_manifest()`, `_get_entry_file_for_role()`, and a new `_strip_variant_suffix()` helper. All changes are backward-compatible — existing roles without `base_role` in their `includes.yml` are unaffected.

**SOUL.md deploy path (no change needed)**: `deploy_role()` already falls back to the base role's `SOUL.md` via `_get_entry_file_for_role()`. After the above changes, `_get_entry_file_for_role("pm-skill")` → `"pm-skill"` (if variant has own CLAUDE.md) or `"pm"` (if inheriting). The SOUL.md lookup follows the same identity, finding the variant's own SOUL.md if it exists, or the base role's if not.

---

### Preset CLAUDE.md Content Model

**General principle**: Layer 3 CLAUDE.md variants are thin. The base role already defines 95% of the agent's behavior. Layer 3 adds only the domain-specific knowledge that changes how the agent applies its base role responsibilities.

**Format for each variant's entry file**:

```markdown
{{extend: <base-role>}}   ← signals composition engine to inline base entry file
                            (OR: copy base entry file prose and add below)

---

## Layer 3: [Variant Name]

[1-3 sentences of variant identity — what distinguishes this specialization]

{{include: <variant>-specific/<key-sub-skill>}}
```

**Skill preset** (`pm-skill`, `qa-skill`, `dm-skill`, `dev-skill`):

- `pm-skill`: Adds sub-skill covering: deterministic vs probabilistic code boundaries (what must be scripted vs what can be LLM-generated), how to scope tasks given LLM non-determinism, how to write acceptance criteria for probabilistic outputs, how to approve sub-skill features.
- `qa-skill`: Adds sub-skill covering: testing probabilistic code (what to assert, what to treat as behavioral not testable), spawning test agents to verify LLM-consumed instructions, comprehension testing methodology.
- `dm-skill`: Adds sub-skill covering: skill packaging conventions (SKILL.md, version, marketplace listing), distribution-aware delivery (what goes in CHANGELOG for a skill consumer vs a framework developer).
- `dev-skill`: Already exists as `skill` variant — rename or alias. Adds: sub-skill for probabilistic/deterministic boundary awareness during implementation.

**iOS preset** (`dev-ios`, `pm-ios`, `qa-ios`, `dm-ios`):

- `dev-ios`: Adds Swift/SwiftUI conventions, Xcode build awareness, iOS testing patterns (XCTest, UI testing), App Store submission awareness.
- `pm-ios`: Adds iOS release cadence awareness (App Store review times, TestFlight beta cycle), iOS-specific acceptance criteria patterns (device matrix, iOS version support).
- `qa-ios`: Adds XCTest/XCUITest verification patterns, device/simulator matrix testing, TestFlight build verification.
- `dm-ios`: Adds App Store Connect delivery steps, iOS versioning (build number vs version), TestFlight distribution notes.

**Web, Android, Full-stack presets**: Same pattern — each adds 1-2 sub-skills covering the domain-specific delivery, testing, and implementation context for that platform.

**Content scope rule**: Each Layer 3 variant adds AT MOST 2 sub-skills and ~50-100 lines of content total. If a variant needs more, the content belongs in Layer 2 (a new base role), not Layer 3.

---

### Updated Open Questions

**Q6 (new): Should Layer 3 entry files copy base role prose or use an {{extend:}} directive?**

The recommendation above accepts prose scaffold duplication (copy base entry file + add variants at end). This is simple but means a base role prose change requires updating all variants. Alternative: introduce a single `{{extend: <role>}}` directive that inlines the base entry file at composition time. This is a 10-line compose.py change and eliminates all duplication. **Recommendation**: implement `{{extend:}}` — it costs very little and prevents all 20-preset drift. Q6 should be a dev-discretion decision per CONTEXT.md.

**Q7 (new): Do variant-specific sub-skills live in `<variant>-specific/` or `<base>-specific/`?**

Example: `pm-skill`-specific sub-skills — do they go in `references/sub-skills/pm-skill-specific/` or `references/sub-skills/pm-specific/pm-skill/`? The first is consistent with existing naming (`pm-specific/`, `dev-specific/`, `qa-specific/`). The second groups them under the base role. Recommendation: `pm-skill-specific/` (flat naming, consistent with the `<role>-specific/` pattern). This is dev discretion.

**Q8 (new): What is the manifest schema for Layer 3 includes.yml?**

Proposed schema:
```yaml
# Layer 3 variant manifest
base_role: pm
additional_includes:
  - pm-skill-specific/deterministic-boundary
  - pm-skill-specific/skill-acceptance-criteria
```

vs. the existing schema (Layer 2):
```yaml
# Layer 2 base role manifest
includes:
  - common/tracker-protocol
  - ...
```

Using separate keys (`base_role` + `additional_includes` vs `includes`) makes the distinction explicit and unambiguous. Alternatively, a single `includes` list with a sentinel entry `- base_role: pm` is more concise but mixes types. **Recommendation**: separate keys. Dev discretion.

**Q9 (new): Do dev variants (`skill`, `be`, `fe`) need actual Layer 3 CLAUDE.md content, or just the rename?**

Currently `skill` = `dev` with role-name substitution. If `dev-skill` replaces `skill`, the CLAUDE.md gains actual skill-specific content for the first time. This is a behavior change (adding probabilistic boundary sub-skill to the dev template) that could help the skill agent self-correct scope. Recommendation: yes, add actual Layer 3 content — the whole point of the feature.

---

### Updated Recommendation

**Overall**: Feasible. The CLAUDE.md layering is MORE important than previously assessed. The original research correctly identified that Layer 3 for dev variants today is purely a name substitution — no actual CLAUDE.md customization. The feature's full value is unlocked only when Layer 3 CLAUDE.md content is real.

**Revised scope for dev pickup** (replaces prior Recommendation section):

1. **compose.py** — `_load_manifest()` gains `base_role` + `additional_includes` support. `_get_entry_file_for_role()` gains suffix-strip fallback generalized to all roles. New `_strip_variant_suffix()` helper. Optional: `{{extend:}}` directive (~10 lines). Total: ~35 lines changed/added.

2. **Manifest schema** — `includes.yml` supports two schemas: base-role schema (existing `includes:` key) and variant schema (`base_role:` + `additional_includes:`). Document in `references/sub-skills/manifest.md`.

3. **Layer 3 entry files** — 20 new `references/roles/<variant>/CLAUDE.md` files (thin, ~50 lines each). Each adds variant-specific identity prose and 1-2 `{{include:}}` directives.

4. **Layer 3 sub-skill files** — 20-40 new `references/sub-skills/<variant>-specific/*.md` files. These contain the actual domain-specific content (probabilistic boundary awareness, iOS release cadence, etc.). This is the bulk of the human-authored content.

5. **Layer 3 SOUL.md files** — 20 new `references/roles/<variant>/SOUL.md` files. Per CONTEXT.md locked decision: full files, not overlays.

6. **Layer 3 includes.yml files** — 20 new `references/roles/<variant>/includes.yml` files using the variant schema.

7. **Layer 1/2 boundary documentation** — `references/sub-skills/manifest.md` updated to declare Layer 1 set and Layer 2/3 conventions.

**What does NOT change**: All existing role templates (`dev`, `pm`, `qa`, `dm`, `designer`), all existing `includes.yml` files, `soul_adaptation.py`, `wizard.py`, `add_role.py`, `health_check.py`. Existing agents continue working identically.

**The biggest risk identified by CLAUDE.md analysis**: The 20 presets require substantial human-authored sub-skill content (the domain-specific knowledge for each variant). This is not a compose.py or architecture problem — it is a content authoring problem. Each variant needs someone to actually write what `pm-ios` knows about App Store cadence, what `qa-skill` knows about testing probabilistic code, etc. This content cannot be auto-generated from the architecture. **Recommendation**: ship the architecture (compose.py changes + manifest schema + empty/stub variant directories) first, then fill content iteratively — starting with `dev-skill`/`pm-skill`/`qa-skill`/`dm-skill` (the Skill preset, most relevant to this project).

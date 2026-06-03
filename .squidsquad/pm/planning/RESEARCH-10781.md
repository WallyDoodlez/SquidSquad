# RESEARCH #10781 — Sub-skills as invokable Claude Skills

## Summary

The operator wants SquidSquad's sub-skills (markdown fragments at `references/sub-skills/`) to become real Claude Skills invokable via the Skill tool. This is not a new direction — `docs/COMPOSE-ARCHITECTURE.md §4.5.1` explicitly documents this as the "target state" and tracker issue #10362 was already filed as a follow-up. The COMPOSE-ARCHITECTURE TRD already established the architecture: catalog source paths stay rooted at `references/sub-skills/`; a new installer step materializes each source into `<project-root>/.claude/skills/<name>/SKILL.md` at deploy time; the `→ run sub-skill: <name>` reference grammar in composed CLAUDE.md stays unchanged; only the resolution mechanism changes from "Read file + execute in-context" to "Skill tool invocation."

The primary risk is the mandatory/situational split. Sub-skills like `boot-bootstrap`, `cycle-runner`, `context-pressure`, and `self-restart` MUST fire deterministically every cycle — Claude Skill invocation is discretionary (model-driven, description-matching), so these cannot be converted to pure Skill-tool invocations without breaking boot/cycle determinism. The TRD already anticipated this: mandatory sub-skills likely remain inlined into a small composed CLAUDE.md while situational sub-skills (vault-remember, improvement-scan, pipeline-sentinel, task-intake, etc.) become invokable Claude Skills. The key Phase 2 decision is drawing this line precisely and deciding who holds authority (catalog? frontmatter flag? authoring convention?).

A secondary risk is placeholder handling. Sub-skills use `[ROLE]`, `[ROLE_UPPER]` and similar tokens that `compose.py:_substitute_placeholders` resolves at compose time. Once a sub-skill becomes a standalone SKILL.md, it has no access to compose-time substitution unless the installer bakes the resolved values in at materialization time (role-pinned per-agent SKILL.md), or the Skill tool args mechanism is used (user/agent passes role at invocation time). The installer-bakes option is cleanest but means each install has per-agent SKILL.md variants instead of one generic file.

---

## Vault Context

- **decision-sub-skill-architecture** (`.squidsquad/vault/galaxy/decision-sub-skill-architecture.md`) is the baseline — layered 5-tier architecture, build-time composition chosen for simplicity and predictability; this slice modifies the resolution layer (how agents execute sub-skills) while keeping authoring locations unchanged.
- [[project_marketplace]] (killed) still in force — no marketplace, no public directory. All `.claude/skills/` paths are project-scoped only, per §4.5.1: "Project-scope only — never installed at user-scope."
- [[project_subskill_directory]] un-parked 2026-06-02 — this is the un-park record; the decision to keep sub-skills as internal composition units is reversed specifically to enable runtime invocability.

---

## Q1 — Which sub-skills convert?

**Recommendation**: **Tiered conversion — not all, not none. Introduce a mandatory/situational classification in each sub-skill's frontmatter.**

**Why**: The COMPOSE-ARCHITECTURE TRD (§4.5.1, lines ~70-76 of `docs/sub-skill-catalog.md`) already anticipated exactly two tiers:
- **Mandatory**: `boot-bootstrap`, `cycle-runner`, `context-pressure`, `self-restart`, `agent-lifecycle` — must fire deterministically; cannot rely on description-matching Skill invocation. Stay inlined in composed CLAUDE.md.
- **Situational**: `vault-remember`, `vault-optimize`, `improvement-scan`, `pipeline-sentinel`, `task-intake`, `task-approval`, `checkin`, `soul-shepherd`, `vault-synthesis`, `git-commit`, `issue-filing`, `discussion`, `l4-curation`, `delivery-packaging`, `version-bumps` — fire conditionally based on context; description-matching invocation is appropriate.

**Special cases**:
- `common-events/` fragments (`l1-base`, `event-driven-workflow`, etc.) are already runtime-loaded via `boot-bootstrap`'s Read tool calls — they are NOT inlined into composed CLAUDE.md. These are the closest thing to "invokable at runtime" that already exists. Converting these to Claude Skills is lower risk than cycle-runner but still has the determinism concern (boot sequence is ordered).
- `boot-remote-agents` (PM only) is already reactive/optional — natural candidate for Skill conversion.
- Domain-context sub-skills (e.g. `roles/pm/skill/domain-context.md`, `roles/dm/android/domain-context.md`) are short static context blocks — technically convertible but low value as Skills (they provide no procedure, just context).
- `project/` seed files (L4 seeds copied at install time, never consumed by compose) — NOT sub-skills in the invocable sense; should be excluded from conversion scope entirely.

**Trade-offs**:
- Mandatory-stays-inlined: composed CLAUDE.md stays non-trivially large for boot/cycle core; partial win on size reduction
- All-convert: breaks deterministic boot/cycle; agents may skip mandatory procedures; runtime breakage hard to debug
- Tiered: adds frontmatter complexity (a new `invocable: mandatory | situational` field) but is the correct long-term architecture

**Evidence**:
- `docs/sub-skill-catalog.md` lines 70-77: "Mandatory sub-skills... Likely remain inlined... Situational sub-skills... these are the natural fit for the Claude skill mechanism"
- `references/roles/pm/includes.yml`: 35 sub-skills listed, spanning both tiers; all currently inlined indiscriminately
- `references/sub-skills/common/boot-bootstrap.md` frontmatter: `slot: instructions, ordinal: 10` — first file in includes.yml; MUST run first on every boot

---

## Q2 — Dual-purpose vs export?

**Recommendation**: **Export — installer materializes derived SKILL.md artifacts at `<project-root>/.claude/skills/<name>/SKILL.md` from authored `references/sub-skills/` sources.**

**Why**: The TRD (COMPOSE-ARCHITECTURE §4.5.1, line ~561) already settled this: "Catalog source paths remain rooted at `references/sub-skills/`... The installer reads from there and writes to the project-local `.claude/skills/`." Dual-purpose would require sub-skill source files to satisfy both the compose frontmatter schema (`slot:`, `ordinal:`, `step-ids:`) AND the Claude Skill SKILL.md schema (`name:`, `description:`, `version:`). These are structurally incompatible — `slot:` and `ordinal:` have no meaning in a Claude Skill context; `description:` (required for Skill tool invocation matching) is not in the compose frontmatter.

Export (installer-generated SKILL.md artifacts) keeps the layers clean: authors write `references/sub-skills/` files in compose grammar; the installer reads them and generates SKILL.md files with appropriate Claude Skill frontmatter derived from the source + catalog metadata. Source files gain no new authoring burden.

**Trade-offs**:
- Export adds installer complexity (new materialization step, SKILL.md generation logic)
- Export means SKILL.md files are generated artifacts — they live in `.claude/skills/` which is gitignored or generated; operators don't author them
- Dual-purpose would be simpler to author but creates schema conflict; any change to one schema breaks the other
- Export keeps authoring at `references/sub-skills/` — consistent with the "catalog source paths stay the same" TRD commitment

**Evidence**:
- `SKILL.md` (repo root): frontmatter fields are `name:`, `description:`, `version:`, `license:` — no `slot:` or `ordinal:` fields; schemas are disjoint
- `references/sub-skills/common/git-commit.md` line 1-4: `slot: instructions, ordinal: 10` — this frontmatter is incompatible with Claude Skill schema
- `docs/COMPOSE-ARCHITECTURE.md §4.5.1`: explicitly specifies installer-writes-to-`.claude/skills/` pattern

---

## Q3 — Compose-time placeholder handling

**Recommendation**: **Option (a) — resolve at packaging/materialization time (role-pinned SKILL.md per agent alias).**

**Why**: Placeholders like `[ROLE]`, `[ROLE_UPPER]`, `[ROLE_PLACEHOLDER]` appear throughout sub-skills (e.g. `references/sub-skills/common/vault-remember.md` uses `[ROLE]`; `references/sub-skills/common/self-restart.md` uses `[ROLE]`). Option (b) (defer to Skill args) would require every invoking agent to pass its role on every invocation — this is cumbersome and error-prone, and the current invocation grammar (`→ run sub-skill: <name>`) has no args mechanism. Option (c) (strip) loses fidelity — e.g. `vault-remember` would tell the agent to write to `[ROLE]/working-state.md` literally.

Role-pinned materialization means: at installer time, for each alias in `config.md`'s `## Aliases` table, the installer generates `<project-root>/.claude/skills/<name>-<alias>/SKILL.md` (or `<name>/SKILL.md` within a per-alias skill subdirectory) with `[ROLE]` already substituted with the alias's role-class name. This matches how `compose.py` already works — it substitutes placeholders at compose time per alias. The installer inherits the same substitution logic.

**Trade-offs**:
- Role-pinned: per-alias SKILL.md artifacts; on a 5-agent install, a 3-placeholder sub-skill produces 5 SKILL.md files; disk footprint increases
- Role-pinned: changes the skill name/path (name must include alias or alias must be a subdirectory); requires the `→ run sub-skill: <name>` reference grammar to become role-aware or the CLAUDE.md to reference `<name>-<alias>` not just `<name>`
- Defer-to-args: cleanest Skill.md files but requires invoking syntax change; incompatible with the "reference grammar stays the same" TRD goal
- Strip: simplest but produces incorrect behavior on any step that uses the placeholder in a path or command

**Key open question**: Does the `→ run sub-skill: <name>` reference in CLAUDE.md need to embed the alias, or does Claude resolve `<name>` to the correct alias-pinned SKILL.md via the installed skill's description? This is the hardest sub-question in Q3 and needs operator input in Phase 2.

**Evidence**:
- `references/sub-skills/common/vault-remember.md`: `vault_remember.py is-quiet [ROLE]`, `vault_remember.py reset-writes [ROLE]` — role placeholder used in bash commands that must be correct at runtime
- `references/sub-skills/roles/pm/pipeline-sentinel.md`: `[ROLE]` in `cycle.py status-bar [ROLE]` — same pattern
- `docs/COMPOSE-ARCHITECTURE.md §3.0`: compose reads `config.md` for placeholder substitution values; installer has the same information available at materialization time

---

## Q4 — Wikilink handling

**Recommendation**: **Keep wikilinks as informational cross-references at authoring time; transform to Skill invocations in materialized SKILL.md only for skills already converted to Claude Skills; otherwise keep as plain text references.**

**Why**: Wikilinks in sub-skills are primarily used in the `common-events/` fragments (e.g. `event-driven-workflow.md` uses `[[l1-base]]`, `[[cursor-management]]`, `[[forge-read-pattern]]`). These wikilinks currently work as Obsidian vault navigation — they are NOT agent invocation signals today. The CONTEXT-10781 question asks about wikilinks becoming Skill invocations, but this is premature if the referenced sub-skill is not itself a Claude Skill yet.

The pragmatic approach: during materialization, the installer inspects each `[[name]]` reference in the source file. If `name` has a catalog entry and is in the "situational" tier (i.e., it will be materialized as a Claude Skill), transform the wikilink to a Skill invocation reference in the SKILL.md. If `name` is mandatory-tier (not materialized as a Claude Skill), keep it as plain text prose or a file path reference. This is a transform-at-materialize-time decision, not an authoring-time decision.

**Trade-offs**:
- Full wikilink → Skill invocation transform: requires every referenced sub-skill to be a Claude Skill first (ordering dependency during rollout)
- Informational-only: wikilinks remain as documentation cross-references; human-readable but agents can't automatically invoke them
- Selective transform: cleanest but requires the installer to know the tier classification of every referenced sub-skill (which is exactly what the frontmatter classification flag in Q1 enables)

**Interaction with #10690 (wiki-link rework)**: if #10690 already ships a wikilink transformer, the installer can piggyback on that infrastructure rather than building its own. This should be confirmed before implementing the installer step.

**Evidence**:
- `references/sub-skills/common-events/event-driven-workflow.md` lines 12-26: uses `[[l1-base]]`, `[[cursor-management]]`, `[[forge-read-pattern]]`, `[[idle-cooldown-loop]]`, `[[comment-handling]]` — all within the `common-events/` tier
- CONTEXT-10781.md Q4: "wikilinks in sub-skills must transform to Skill invocations" — confirmed as a scope item

---

## Q5 — L1–L4 surrounding context

**Recommendation**: **Option (c) — accept reduced fidelity outside the SquidSquad-composed environment, but document which context is assumed; for high-fidelity invocation, skills declare their assumed context in the SKILL.md description.**

**Why**: Sub-skills are authored assuming full L1-L4 composed context around them. `pipeline-sentinel.md` assumes the agent knows its role, has tracker access, knows the configured cycle interval. `vault-remember.md` assumes vault PARAG structure exists and `vault_remember.py` is on the path. A standalone Claude Skill invocation that happens to land in a non-SquidSquad project would fail on all these dependencies.

However, the TRD already specifies "Project-scope only" installation — each SquidSquad install installs sub-skills into its own `.claude/skills/`. An agent invoking `vault-remember` via the Skill tool within a SquidSquad project already has the full composed CLAUDE.md context. The problem only arises if someone invokes a SquidSquad sub-skill outside a SquidSquad project — which won't happen if skills are project-scoped.

For intra-SquidSquad invocations, the composed CLAUDE.md provides the surrounding L1-L4 context; the Skill tool invocation is additive (brings in additional procedure), not a replacement for the composed context. This is the cleanest model: composed CLAUDE.md = orchestration layer + identity/role/context; Claude Skills = procedure library invoked when needed.

**Trade-offs**:
- Self-contained skills: each SKILL.md must inline the context it needs (role, vault paths, etc.) — duplicates information from composed CLAUDE.md; violates DRY; not practical for 40+ sub-skills
- Context-required capability declaration: adds a formal mechanism for skills to declare dependencies; heavier to implement
- Accept reduced fidelity: skills work correctly only within a SquidSquad install; document this clearly; the TRD's project-scope-only constraint already enforces this implicitly

**Evidence**:
- `docs/COMPOSE-ARCHITECTURE.md §4.5.1`: "Project-scope only — never installed at user-scope (`~/.claude/skills/`)"; project-scoped installation ensures composed context is always present
- `references/sub-skills/common/vault-remember.md`: uses `vault_remember.py`, reads `.squidsquad/<role>/working-state.md`, `vault/BRIEFING.md` — all SquidSquad install-specific paths; meaningless outside SquidSquad

---

## Q6 — Catalog and discovery

**Recommendation**: **Catalog stays at `docs/sub-skill-catalog.md` as the authoritative authoring index; installer materializes from catalog into `<project-root>/.claude/skills/`; `catalog_parser.py:394` guard relaxed to allow SKILL.md path references in a new "installed path" column, but the source-path column remains `references/sub-skills/` only.**

**Why**: The current guard at `catalog_parser.py:394` (lines 394-407) exists to prevent catalog entries from pointing at `.claude/skills/` as their source — the source must always be `references/sub-skills/`. This guard is correct and should be preserved for the source-path column. However, the catalog may need a second column ("installed path" or "skill-name") to record the materialized skill's name/path for the installer to use. That addition is compatible with the existing guard: the guard checks `source_path` (the `references/sub-skills/` path), not any new column.

Claude Skills are discovered at `<project-root>/.claude/skills/` (project-scoped) — the installer populates this at install/upgrade time from catalog entries. The `→ run sub-skill: <name>` reference in composed CLAUDE.md resolves to the installed skill by name matching. No operator-visible discovery UI is needed since skills are project-internal.

**Trade-offs**:
- Keep catalog as sole source of truth: no new discovery file needed; installer reads catalog directly
- Add a `.claude/skills/catalog.json` manifest: enables faster lookup but duplicates catalog data
- Hard guard stays: prevents accidental authoring of catalog entries at `.claude/skills/` paths (which would make the catalog point at generated artifacts instead of authored sources)

**Evidence**:
- `references/scripts/catalog_parser.py` lines 394-407: guard comment says "AC5: `.claude/skills/` paths are NEVER valid catalog entries" — this was explicitly added as enforcement of the parked stance; the new direction does NOT invalidate the rationale (authoring is still at `references/sub-skills/`, installed artifacts are at `.claude/skills/`)
- `docs/COMPOSE-ARCHITECTURE.md §4.5.1` line ~561: "Catalog entries do not point at `.claude/skills/` — that's an install artifact, not the canonical authoring location" — the guard implements this policy and should be preserved

---

## Q7 — TRD impact

**Recommendation**: **New PRD slice under COMPOSE-ARCHITECTURE TRD, NOT a new TRD. Designate it PRD-D (installer sub-skill materialization).**

**Why**: This change is entirely within the COMPOSE-ARCHITECTURE TRD's scope. §4.5.1 explicitly named it a "Gap" and pointed at INSTALLER-ARCH as the home for the installer step spec. The architecture is already designed — the work is specifying and implementing the installer step, the SKILL.md frontmatter generation, the mandatory/situational classification, and the placeholder substitution at materialization time. None of this warrants a new TRD: no new architectural concept is introduced.

**Interactions**:
- **PRD-A (link stage)**: Link stage validates `→ run sub-skill: <name>` refs against the catalog. Once Skills are materialized, the link stage could optionally also validate that the installed skill exists at `.claude/skills/<name>/SKILL.md`. This is a strengthening of the existing check, not a redesign.
- **PRD-B (assemble stage)**: Assemble preserves `→ run sub-skill: <name>` references verbatim (§4.6 hard preservation guarantee). No change needed — the reference grammar is the same whether the sub-skill resolves to a markdown file or a SKILL.md.
- **PRD-C (L4 customization)**: L4 `### append` blocks under `## Instructions` must contain at least one `→ run sub-skill: <name>` reference (§3.3 constraint). This constraint applies regardless of whether the sub-skill is materialized as a Claude Skill or read as a markdown fragment. No change.
- **E6 cutover (#10685)**: Research should wait until E6 ships (as CONTEXT-10781 already specifies). E6 simplifies the compose v2 path; PRD-D slots cleanly post-E6 because it builds on the v2 compose output (thin orchestration layer + sub-skill references).
- **#10690 (wiki-link rework)**: If #10690 ships a wikilink-to-Skill-invocation transformer, PRD-D should reuse it rather than building a parallel one. Coordinate ordering: #10690 ideally ships before or concurrently with PRD-D installer step.
- **#10362**: Already filed as the installer spec follow-up for §4.5.1. PRD-D is the formalization of #10362. Check if #10362 is still open and un-started before filing new tasks.

---

## Impact Analysis

- **Files touched**:
  - `references/scripts/catalog_parser.py` — relaxation or extension of guard at line 394 (new column handling)
  - `references/sub-skills/**/*.md` — add `invocable: mandatory | situational` frontmatter field to each sub-skill source file (or maintain a separate tier classification in catalog)
  - New installer step script (likely `references/scripts/skill_materializer.py` or inside existing installer)
  - `docs/INSTALLER-ARCH.md` — new section for the materialization step
  - `docs/COMPOSE-ARCHITECTURE.md §4.5.1` — update "Gap" to reference the new PRD-D
  - `docs/sub-skill-catalog.md` — add tier classification column; update "current state" section
- **Behavior changes**: Agents using situational sub-skills will invoke them via Skill tool rather than reading markdown files in-context. Prompt size for those invocations changes (Skill tool call is more compact than loading full file content). Composed CLAUDE.md shrinks significantly for roles with many situational sub-skills (e.g. PM has 35 includes.yml entries; ~20 are situational).
- **Dependencies**: E6 (#10685) must ship first; #10690 wiki-link rework should be coordinated; #10362 may already cover part of this scope.

---

## Side Effects

- **Mandatory/situational boundary ambiguity** — severity: HIGH — some sub-skills are situational-in-practice but may be referenced in a mandatory context (e.g. `self-restart` fires on every cycle end, but only under a specific condition). The classification must be clear. Mitigation: define the tier by invocation mechanism (mandatory = must fire even if model doesn't recognize the situation; situational = fires when model decides conditions match), not by frequency.
- **SKILL.md description quality determines invocation fidelity** — severity: MEDIUM — if the installer generates poor descriptions for SKILL.md frontmatter, the model won't invoke sub-skills at the right time. The description field in SKILL.md (like the SquidSquad root `SKILL.md`) must be carefully authored, not auto-generated from the sub-skill's `slot:` frontmatter. Mitigation: require human-authored description field in each sub-skill source file that the installer copies into SKILL.md.
- **Per-alias SKILL.md proliferation** — severity: LOW — role-pinned materialization produces many files (N aliases × M sub-skills). A 5-agent install with 20 situational sub-skills produces 100 SKILL.md files. Mitigation: if placeholder substitution is minimal (most sub-skills use `[ROLE]` in only 1-2 places), consider template substitution at invocation time via Skill args instead of role-pinning. Needs Phase 2 discussion.
- **catalog_parser.py guard blocks future catalog evolution** — severity: LOW — the guard is correct for source-path column; it needs to be clearly scoped so a "skill-name" or "installed-path" column addition doesn't accidentally trigger it. Mitigation: guard is already surgically targeted at `source_path` variable; adding a new column is safe.

---

## Edge Cases

- **Sub-skill with no role placeholder**: can be materialized as a single role-agnostic SKILL.md (e.g. `vault-protocol.md`, `git-commit.md` — these may have role placeholders in bash commands, need audit). Installer can use generic name without alias suffix.
- **Sub-skill that references another sub-skill**: `event-driven-workflow.md` references multiple other `common-events/` sub-skills via wikilinks. If both are materialized, the installer must generate correct Skill invocation references in the SKILL.md body — not wikilinks.
- **Upgrade scenario**: existing installs have no `.claude/skills/` directory. Upgrade must create it and populate it. The `squidsquad-upgrade` skill (which walks migration files) needs a new migration step.
- **Sub-skill removed from catalog**: any SKILL.md artifact for the removed sub-skill must be cleaned up at upgrade time; stale SKILL.md files at `.claude/skills/` would confuse the model.
- **Role-class that has no mandatory sub-skills** (hypothetical): all sub-skills could be situational; the composed CLAUDE.md for that role would be very thin. Edge case only — currently all roles have mandatory boot/cycle sub-skills.

---

## Integration Risks

- **Interaction with PRD-A (link stage)**: Link stage currently validates `→ run sub-skill: <name>` against `references/sub-skills/` source files. After materialization, a stronger check could validate the installed `.claude/skills/<name>/SKILL.md` also exists. If the installer step runs AFTER compose (at deploy-all time), the link-stage check might run before SKILL.md files are created. Ordering of installer steps vs compose steps must be specified.
- **Interaction with PRD-B (assemble stage)**: No architectural risk — assemble preserves `→ run sub-skill:` references verbatim. The runtime resolution change (file read vs Skill tool) is invisible to the assemble pass.
- **Interaction with PRD-C (L4 customization)**: The `### append` constraint (L4 must reference a catalog sub-skill) enforces that L4 appendages are meaningful. If a sub-skill is mandatory-tier (not a Claude Skill), an L4 append referencing it still resolves correctly (falls back to markdown-fragment resolution). No conflict.
- **Interaction with E6 cutover**: E6 simplifies the compose v2 path. PRD-D must be scoped to v2 path only (no v1 compatibility layer). If E6 hasn't shipped, this work would fork the v2 path prematurely. Hard gate confirmed: wait for E6.
- **Interaction with #10690 (wiki-link rework)**: #10690 targets wikilinks in sub-skills transforming to Skill invocations. If PRD-D ships before #10690, the wikilink transform is missing and materialized SKILL.md files will contain unconverted `[[name]]` wikilinks that don't resolve at runtime. Either coordinate shipping order or scope PRD-D to exclude wikilink transform (mark as follow-up for #10690).

---

## Upgrade & Migration

- **Catalog (`docs/sub-skill-catalog.md`)**: Add a "tier" column (mandatory/situational) and a "skill-description" column (human-authored description for SKILL.md generation). These are new columns; existing rows need backfill. The catalog is the single source of truth — the tier classification lives here, not in individual sub-skill frontmatter (keeps authoring DRY).
- **`catalog_parser.py:394` hard guard**: Preserve as-is. The guard correctly blocks `.claude/skills/` paths in the source-path column. Any new "installed path" column should be parsed separately and is not subject to this guard. No relaxation needed for the existing guard logic.
- **Existing installs**: Agents in existing installs currently resolve `→ run sub-skill: <name>` by reading the markdown source file. After the installer materializes SKILL.md files, agents will resolve via Skill tool. This is a behavioral change that requires agent restart (harness reboot) — same as any composed CLAUDE.md change. The upgrade migration step must: (1) run the materializer for all catalog entries, (2) create `.claude/skills/` directory structure, (3) recompose all roles (so any reference grammar updates land), (4) reboot agents.
- **Backwards compatibility**: The `→ run sub-skill: <name>` reference grammar in composed CLAUDE.md stays unchanged. The resolution mechanism changes, but the authoring contract is stable. Operators who pin to a specific SquidSquad version see consistent behavior.

---

## Capability Gaps

- **No SKILL.md description field in sub-skill sources**: Sub-skill source files currently have no human-authored `description:` field. The installer cannot generate quality SKILL.md descriptions without one. This is the most significant authoring gap — adding `description:` to sub-skill frontmatter is a prerequisite for quality Skill tool matching.
- **No tier classification in catalog**: The mandatory/situational split is documented in the TRD narrative but not formalized in the catalog schema. Needs a new column before the installer can know which sub-skills to materialize.
- **No installer materialization step**: The installer script at `references/scripts/` has no sub-skill SKILL.md generation logic. This is the primary implementation gap — #10362 was filed to spec this.
- **No placeholder substitution at materialization**: Compose has `_substitute_placeholders` but the installer does not. If role-pinned materialization is chosen, this logic must be extracted and reused.

---

## Open Questions

- **Q3 unresolved detail**: Does the `→ run sub-skill: <name>` reference in CLAUDE.md embed the alias (e.g. `→ run sub-skill: vault-remember-pm`), or does the installed skill's description enable the model to match `vault-remember` to the correct role-pinned variant? This is the single most ambiguous point in the design and needs operator input.
- **Q4 / #10690 coordination**: Does #10690 ship before PRD-D? If yes, can PRD-D's installer piggyback on #10690's wikilink transformer? If no, scope PRD-D to exclude wikilink transform.
- **#10362 status**: Is #10362 still open and unstarted? PRD-D may be a formalization/renaming of #10362 rather than a new task. Verify before filing.
- **SKILL.md format stability**: The SKILL.md schema (from the SquidSquad root `SKILL.md`) has `name:`, `description:`, `version:`, `license:` fields. Are there additional fields (e.g. `args:`, `requires:`) in the Claude Code platform that would be useful for sub-skill skills? The on-disk `SKILL.md` is the best reference available but may not reflect all platform capabilities.
- **`common-events/` handling**: These fragments are already runtime-loaded (not inlined). Should they be materialized as Claude Skills (changing their load mechanism from Read tool to Skill tool) or kept as Read-tool-loaded files? Their ordered loading (1-2-3-4-5-6 sequence) is semantically important — Skill tool invocation doesn't enforce ordering.

---

## Recommendation

**TRD vs PRD framing**: PRD-D under COMPOSE-ARCHITECTURE TRD. The architecture is fully designed in §4.5.1; only the PRD-level spec (acceptance criteria, implementation slices, migration steps) is missing.

**Recommended next phases**:
- **Phase 2 discussion topics**: (1) mandatory/situational line — operator confirms which sub-skills are mandatory-tier; (2) role-pinned vs args-based placeholder resolution — operator chooses; (3) #10690 coordination timing; (4) #10362 scope overlap.
- **Phase 3 (AC drafting)**: After Phase 2 locks Q1 (tier classification) and Q3 (placeholder approach), ACs can be written for: (a) catalog tier column, (b) sub-skill description field addition, (c) installer materialization step, (d) upgrade migration step, (e) link-stage strengthening (optional).

**Timing relative to E6**: Do NOT start Phase 3 until E6 (#10685) ships. This task's hard gate is in CONTEXT-10781.md and is confirmed by research — the installer materializes from the v2 compose path; working on it during E6 cutover risks either duplicating effort or conflicting with in-flight changes.

**Risk of doing before E6 ships**: moderate-high. E6 simplifies compose.py significantly; the installer's compose interaction (reading catalog, resolving source paths) would need to be re-specified after E6 anyway. Doing Phase 2 discussion now is safe; filing implementation tasks is premature.

---

## Vault Candidates

1. **Decision** — "Sub-skill invocability: export pattern, not dual-purpose" — The decision that SKILL.md files are install artifacts generated from `references/sub-skills/` sources (not dual-schema source files) is worth preserving as a decision note. Prevents future authors from attempting to make sub-skill sources satisfy both schemas.
2. **Decision** — "Mandatory vs situational sub-skill classification" — The two-tier model (deterministic-boot sub-skills stay inlined; situational sub-skills become Claude Skills) is an architectural choice with long-term implications. Worth vaulting with the rationale (Claude Skill invocation is discretionary; boot/cycle determinism cannot tolerate discretionary invocation).
3. **Pattern** — "Installer-as-artifact-materializer" — The pattern of installer reading from `references/` sources and writing generated artifacts to project-local paths (`.squidsquad/`, `.claude/skills/`) is a reusable pattern for future SquidSquad capabilities that need project-scoped installation.
4. **Learning** — "catalog_parser.py guard: scope it precisely, not broadly" — The AC5 guard at line 394 is correctly scoped to the source-path column. Future catalog schema additions (new columns) must parse separately to avoid accidentally triggering the guard. This is a subtle trap worth flagging.
5. **Decision** — "Sub-skill description field: human-authored, not auto-generated" — The SKILL.md `description:` field drives Skill tool invocation matching; auto-generating it from `slot:` frontmatter produces low-quality descriptions. Each sub-skill source must carry a human-authored description. This is a quality gate for the entire conversion.

# FEAT-328 Context — Intent-driven setup wizard with role manifest registry

## Scope

Replace the dev-shaped setup flow with an intent-driven wizard that composes teams from a role manifest registry. PM and DM are always installed. Other roles are added based on user intent via curated presets.

This feature ships:
- A role manifest registry at `references/roles/<role>/manifest.yaml` covering 6 v1 roles
- A new setup wizard in SKILL.md that asks intent first and resolves the pipeline from manifests
- Two presets: `software-dev` and `design`
- A pipeline resolver that walks `routes_to` lists, skipping uninstalled roles
- Refactor of `compose.py`, `config.py`, and PM CLAUDE.md to remove hardcoded role names where the manifest registry can serve

## Locked Decisions (human decided 2026-04-11)

### From initial discussion
1. **Single feature** (not three) — manifest schema + wizard + presets ship together
2. **PM always installed** — the human's entry point
3. **DM always installed** — produces the actual delivery output (Google Drive, email, file export)
4. **Roles SquidSquad-defined for v1** — users customize variation via SOUL.md only. Custom user-defined roles deferred.
5. **Two presets v1**: `software-dev` and `design`
6. **YAML sidecar manifests** at `references/roles/<role>/manifest.yaml` (not frontmatter)
7. **Per-role decentralized `routes_to`** — no central graph file
8. **GitHub Issues ingestion default flipped to `Y`** in setup
9. **Conditional dev question** — only ask BE/FE/Fullstack if intent involves software
10. **No install base** — clean rebuild OK, no migration burden

### From Phase 2 discussion (10 decisions)

11. **Q1 — DM as universal terminal**: Append `dm` to every shipped manifest's `routes_to`. Decentralized, walker stays simple, no special cases. Example: `designer: routes_to: [dev, qa, dm]`, `qa: routes_to: [dm]`, `dev: routes_to: [qa, dm]`.

12. **Q2 — Schema versioning**: Every manifest YAML must have a top-level `schema_version: 1` field. Validator warns on mismatch, errors on unknown version.

13. **Q3 — Dev manifest shape**: Single `references/roles/dev/manifest.yaml` with `setup_questions.variant` field listing be/fe/fullstack. DRY — `routes_to: [qa, dm]` lives in one place. Resolver matches "dev family" to any installed variant.

14. **Q4 — Fullstack default**: Default `software-dev` preset to `be+fe` (two agents). Offer `fullstack` (one combined `dev` agent) as a secondary option in the variant question. Preserves today's default — no regression for existing users. Pipeline display defaults to `PM → Designer → [BE, FE] → QA → DM`.

15. **Q5 — PM → DM direct routing**: Runtime only via resolver fallback. **No third preset.** When the resolved install collapses to `[pm, dm]`, the wizard shows a friendly hint ("Just PM + DM? That's a planning + delivery team — perfect for proposals, briefs, and project plans"). Promote to dedicated preset in v2 if popular.

16. **Q6 — Custom-builder mode**: **Defer entirely to v2.** Honors the "two presets v1" lock. Document the workaround in README: users wanting a custom shape run the closest preset and hand-edit `config.md` + delete unwanted directories. v2 candidate.

17. **Q7 — QA in design preset (HUMAN OVERRIDE)**: Create a **new dedicated `design-review` role**. The `design` preset uses `design-review` instead of QA. The `software-dev` preset still uses QA. This brings the v1 role count to **6**: pm, dm, designer, dev (with variants), qa, design-review.
   - `design-review/manifest.yaml` ships with v1
   - `routes_to: [dm]`
   - Owns visual review against acceptance criteria, design system consistency, accessibility, traceability to design briefs
   - SOUL.md focuses on "is this design what the human asked for"
   - Has its own template directory at `references/roles/design-review/`

18. **Q8 — Re-running setup with existing `.squidsquad/`**: Three-way prompt:
   - **(1) Abort** (default, Enter key) — safe no-op
   - **(2) Regenerate templates only** — delegates to `/squidsquad-upgrade`
   - **(3) Full rebuild** — nukes `.squidsquad/` after typed confirmation. Warns about loss of working state, iteration logs, vault content.

19. **Q9 — Intent parser (HUMAN OVERRIDE)**: **LLM sub-prompt only**. The wizard runs inside Claude, so the LLM call is free. Wizard asks Claude to classify the free-text answer into `software-dev | design | unclear` with a short prompt. No local matcher. If `unclear`, fall through to manual preset picker.

20. **Q10 — Pipeline display**: ASCII arrow with bracket notation: `PM → Designer → [BE, FE] → QA → DM`. One-line, screenshot-friendly, matches the research doc's notation. Brackets handle parallel groupings.

## v1 Role Inventory (final)

| Role | Always installed | Presets | routes_to |
|------|------------------|---------|-----------|
| pm | yes | both | [designer, dev, qa, design-review, dm] |
| dm | yes | both | [] (terminal) |
| designer | optional in software-dev, required in design | both | [dev, qa, dm] |
| dev (be/fe/fullstack variants) | required in software-dev only | software-dev | [qa, dm] |
| qa | auto-installed when dev is installed | software-dev | [dm] |
| design-review | required in design preset | design | [dm] |

**Resolved pipelines:**
- `software-dev` default (with designer): `PM → Designer → [BE, FE] → QA → DM`
- `software-dev` no designer: `PM → [BE, FE] → QA → DM`
- `software-dev` fullstack: `PM → Designer? → Dev → QA → DM`
- `design`: `PM → Designer → design-review → DM`
- minimal (any preset, decline all optionals): `PM → DM`

## Dev Discretion (skill-lead can choose)

- Manifest YAML field naming details (as long as `schema_version`, `name`, `routes_to`, `setup_questions`, `template_refs` exist)
- Validator implementation (Python in `references/scripts/manifest.py` is the obvious choice)
- Resolver algorithm details (recursion vs iteration, cycle detection mechanism)
- Wizard UX prose (prompts, error messages, hints)
- LLM sub-prompt wording for intent classification
- Where to store the `routes_to` traversal logic (`manifest.py`, new file, or inline in `compose.py`)
- Whether `design-review` reuses parts of QA's CLAUDE.md template or is fully standalone (recommend mostly standalone with shared sub-skills where they apply)

## Side Effect Mitigations (required)

From RESEARCH.md §5:

1. **Removing hardcoded role refs in PM CLAUDE.md** — refactor must preserve all existing PM behavior. Test: run a full PM cycle on the `software-dev` preset and verify all 11 hardcoded sites still work.
2. **`compose.py` dispatch tables** (lines 100-106, 166-167, 201-214) — replace with manifest lookups. Add a unit test that loads each shipped manifest and verifies compose.py can still produce a valid CLAUDE.md for each role.
3. **`config.py` FIELD_MAP** (lines 26-52) and **`sync_agents()`** (line 162) — must stay backward compatible with config.md files written by the new wizard. Document the new config.md schema in CONTEXT.
4. **`statusline.sh` agent loop** — must read installed roles from manifest, not hardcoded list. Test: install design preset and verify status line shows pm/designer/design-review/dm.
5. **Manifest validation at setup time** — malformed YAML must fail loudly with line number and field name. Never silent fallback.
6. **Cycle detection in resolver** — even though no v1 manifest creates cycles, the resolver must detect and reject `routes_to` loops to prevent future bugs.
7. **`design-review` is a brand new role** — boot scripts (`start-role.sh`/`ps1`) must work with it without changes (already parameterized via `[ROLE]`).

## Upgrade Path

**N/A — no install base.** Clean rebuild. Document the new structure in README and the `/squidsquad-upgrade` slash command. The `/squidsquad-upgrade` flow itself does NOT need to learn about manifests in v1 (manifests are only consumed at setup time, then frozen into config.md).

Future-upgrade consideration: when manifest schema_version bumps to 2, `/squidsquad-upgrade` will need to migrate. Out of v1 scope.

## Out of Scope

- User-defined custom roles (future feature)
- Role variation derivatives (PM-marketing, Dev-firmware) — future feature, captured in #328 body
- Custom-builder wizard mode (v2 — see Q6)
- Third preset for `planning-delivery` workflow (v2 — see Q5)
- Migration of any existing installs (no install base)
- Marketing / research / content presets (v2)
- A `modify team` post-setup mode (v2 — captured in Q8)
- LLM intent classifier running outside Claude (only inside-Claude wizard supported)
- `references/scripts/manifest.py add-role` post-setup script (v2 — see Q6)

## Phase 3 — Test Planning

Test plan subagent will read this CONTEXT.md and produce `FEAT-328-TEST-PLAN.md` covering:
- Happy path for both presets (software-dev with be+fe, design with new design-review)
- Variant question coverage (be+fe / fullstack / be only / fe only)
- DM-as-terminal walker resolution for [pm, designer, dm] case
- Re-run setup three-way prompt (abort default, upgrade path, full rebuild)
- LLM intent classifier with three test inputs (software, design, unclear)
- Schema version validation (valid, missing, unknown)
- Malformed manifest YAML → loud failure
- Cycle detection in resolver (synthetic test manifest)
- design-review role end-to-end (pickup design:complete issues, verify against AC, route to DM)
- Regression: existing software-dev workflow still works
- ASCII arrow display rendering on PowerShell + bash

## References

- Research: `.squidsquad/skill/planning/FEAT-328-RESEARCH.md`
- Phase 2 prep: `.squidsquad/skill/planning/FEAT-328-PHASE2-PREP.md`
- Original feature filing: WallyDoodlez/SquidSquad#328
- Current setup flow being replaced: `SKILL.md` Step 1 (Gather Project Details) and Steps 2-6

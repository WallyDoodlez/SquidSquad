# Phase 2 LOCKED decisions for #10781 — Sub-skills as invokable Claude Skills

Final decisions after Phase 2 discussion + DS feasibility audit + 3 operator refinement rounds (2026-06-03, rev 3).

## Scope

Only entries in `docs/sub-skill-catalog.md` (the catalog) are in scope. Filesystem fragments under `references/sub-skills/` that aren't in the catalog are out of scope.

## Two structural moves

### 1. Standing-rule / scaffold-content removal

The following 3 catalog entries are NOT Claude Skills — they're inlined CLAUDE.md content (standing rules + scaffold structure). They have ZERO `→ run sub-skill: <name>` invocations in active `references/` source files. Their bodies still reach composed CLAUDE.md via `includes.yml` (unchanged). They are **removed from `docs/sub-skill-catalog.md`** in PRD-D execution:

| Removed entry | Why | Body size |
|---------------|-----|-----------|
| `self-restart` | Ambient rules about exit-42 handling — never invoked, always read | 38 lines |
| `context-pressure` | Step 1b procedure inlined as cycle scaffold step — never invoked via reference grammar | 25 lines |
| `cycle-runner` | The 3-phase cycle structure itself — inlined as the scaffold | 98 lines |

The 2 originally-mandatory-core entries that DO have active invocations stay in catalog as Claude Skills:

| Kept entry | Active invocations in `references/` |
|------------|--------------------------------------|
| `boot-bootstrap` | `agent-instructions.md:15`, `roles/instructions.md:17` |
| `agent-lifecycle` | `agent-instructions.md:53`, `roles/instructions.md:55` |

**Test for "is this a standing rule" (and thus removed from catalog)**: zero `→ run sub-skill: <name>` references in any active `references/` source file (TRD prose in `docs/` doesn't count).

### 2. Per-agent install filter via `Used by` column

The catalog has an existing `Used by` column. The PRD-D installer materializes a Skill into an agent's clone-local `.claude/skills/` directory ONLY if that agent appears in the row's `Used by`. Result: each agent's available-Skills metadata at session start is restricted to Skills it can actually invoke.

**Many catalog rows have an empty `Used by` column today.** Phase 3 AC must include backfilling these before the materializer runs. Proposed assignments based on path/content evidence (for skill execution to apply during PRD-D):

| Catalog row | Current `Used by` | Proposed (rev 3) |
|-------------|-------------------|------------------|
| `checkin` | empty | PM |
| `task-intake` | empty | PM |
| `task-approval` | empty | PM |
| `testing-and-verification` | empty | verifier |
| `delivery` | empty | DM |
| `pipeline-sentinel` | empty | PM |
| `own-domain-autofix` | empty | PM |
| `health-check` | empty | PM |
| `github-issues` | empty | all roles |
| `soul-shepherd` | empty | PM |
| `vault-synthesis` | empty | PM |
| `verification` | empty | verifier |
| `issue-triage` | empty | PM |
| `delivery-packaging` | empty | DM |
| `version-bumps` | empty | DM |
| `doc-improvement-loop` | empty | DM |
| `triage-issues` | empty | worker |
| `implement-tasks` | empty | worker |
| `skill/finding-categories` | empty | worker |
| `roles/dm/task-pickup` | empty | DM (derivable from path) |
| `roles/pm/improvement-scan` | empty | PM (derivable from path) |
| `roles/pm/issue-filing` | empty | PM (derivable from path) |
| `roles/pm/discussion-protocol` | empty | PM (derivable from path) |
| `roles/pm/ralph-loop-overview` | empty | PM (derivable from path) |
| `roles/verifier/issue-filing` | empty | verifier (derivable from path) |
| `roles/verifier/discussion-protocol` | empty | verifier (derivable from path) |
| `roles/verifier/ralph-loop-overview` | empty | verifier (derivable from path) |
| `roles/dm/issue-filing` | empty | DM (derivable from path) |
| `roles/dm/discussion-protocol` | empty | DM (derivable from path) |
| `roles/dm/ralph-loop-overview` | empty | DM (derivable from path) |
| `roles/worker/ralph-loop-overview` | empty | worker (derivable from path) |
| `pm.md` | empty | PM (L4 seed — likely should NOT be in Skill catalog at all; verify in Phase 3) |
| `verifier.md` | empty | verifier (same caveat as pm.md) |
| `dm.md` | empty | DM (same caveat) |
| `worker.md` | empty | worker (same caveat) |
| `l1-base`, `event-driven-workflow`, `cursor-management`, `forge-read-pattern`, `idle-cooldown-loop`, `comment-handling` | empty | Out of scope — these are `common-events/` fragments, runtime-loaded by `boot-bootstrap`, NOT being converted to Skills |

Existing rows with `Used by` populated stay as-is unless Phase 3 audit finds errors.

## Final decisions (rev 3)

| # | Decision | Lock |
|---|----------|------|
| Scope | What's in scope? | Catalog entries minus the 3 standing rules. ~55–60 entries become Claude Skills (depending on Phase 3 disposition of `pm.md`/`verifier.md`/`dm.md`/`worker.md` and the deferred chat trio). |
| Route | Where do `.claude/skills/<name>/SKILL.md` files come from? | Deploy-time generator (separate installer step) reads `references/sub-skills/` templates → writes `.claude/skills/<name>/SKILL.md` artifacts per agent clone. Sources unchanged at authoring time. |
| Tiering | Catalog structure | **2-tier** (no 3-tier complication): inlined CLAUDE.md content (NOT in catalog: 3 removals + cycle scaffold composition) + Claude Skills (~55–60, all in catalog). |
| Per-agent install filter | Which Skills materialize in which clone? | `Used by` column drives the filter. PRD-D execution backfills empty rows per proposed assignments above. |
| Placeholder handling | `[ROLE]` and similar | ONE shared SKILL.md content per Skill. Agent infers role from its own identity context (composed CLAUDE.md "You are PM"). Generated SKILL.md uses prose like "use your own role name (`pm`/`dm`/`qa`/`skill`) wherever you see `<your-role>` below". |
| Wikilink handling | `[[name]]` references | Vault-note wikilinks preserved as plain text. Sub-skill-to-sub-skill wikilinks are concentrated in `common-events/` (out of scope). #10690 dependency dissolved. |
| Surrounding L1–L4 context | Reduced fidelity outside SquidSquad? | Accepted — skills are project-scoped per-clone; composed CLAUDE.md always present at invocation. |
| Catalog columns | Schema additions | Add `tier` (only takes value `skill` for catalog rows; standing rules removed entirely) — OR omit since 2-tier means all surviving rows are Skills. Plus `skill-description` column (human-authored, used by generator for SKILL.md `description:` frontmatter). |
| Framing | TRD vs PRD | PRD-D under COMPOSE-ARCHITECTURE TRD. |
| #10362 disposition | Existing follow-up issue | Fold into PRD-D — close as superseded. |
| Generator hook | Where it runs | Separate installer step, runs at install + `squidsquad-upgrade`. Has freshness check (catalog hash + per-clone Used-by filter hash). |
| Cap monitoring | Drift protection | PM tracks per-clone Skill count in routine improvement scans; flag at >70 per clone, >80 system-wide. |
| Terminology debt | Rename effort | Acknowledged (6–8 weeks) and deferred indefinitely. PRD-D ships under existing "sub-skill" nomenclature. |
| Gate | Hard pre-req | E6 #10685 must ship before PRD-D implementation begins. |

## What PRD-D delivers

1. **Catalog edits**:
   - Remove rows: `self-restart`, `context-pressure`, `cycle-runner`
   - Backfill empty `Used by` rows per proposed assignments
   - Add `skill-description` column; backfill for all surviving rows
   - Decide disposition of `pm.md` / `verifier.md` / `dm.md` / `worker.md` (likely remove — they're L4 seed files, not Skills)
2. **Skill materializer** at `references/scripts/skill_materializer.py`:
   - Reads catalog
   - For each agent clone (from `.squidsquad/.local-config`)
   - For each catalog row where this agent appears in `Used by`
   - Generates `.claude/skills/<name>/SKILL.md` in that clone with prose role-resolution baked in
3. **`squidsquad-upgrade` migration step**: materialize on existing installs.
4. **Freshness check**: (catalog hash, per-clone Used-by filter hash) vs last-materialized hash.
5. **Reference grammar runtime semantics update**: composed CLAUDE.md's `→ run sub-skill: <name>` references for catalog Skills are reinterpreted as Skill tool invocations (was Read tool). Standing-rule references (the 3 removed rows) keep their inlined bodies via includes.yml — no `→ run sub-skill:` references existed for them in active source.
6. **`docs/COMPOSE-ARCHITECTURE.md §4.5.1`** updated from "Gap" to "Delivered by PRD-D".
7. **#10362 closed as superseded**.

## Phase 3 audit checklist

Before PRD-D acceptance, verify:
- [ ] Each of the 3 removed rows has zero active `→ run sub-skill: <name>` references in `references/` (re-confirm Phase 2 audit findings)
- [ ] Each empty-Used-by row has a final `Used by` assignment (per proposed table above + skill review)
- [ ] `pm.md`, `verifier.md`, `dm.md`, `worker.md` catalog rows — confirmed removed (not L4 seeds in disguise) or confirmed as Skills with reasoning
- [ ] `skill-description` field authored for all surviving rows
- [ ] Per-clone materialization audit: for each agent clone, list which Skills would be installed; verify matches expectation
- [ ] No `→ run sub-skill: <name>` reference in `references/` survives without a matching catalog row (catalog gate stays green)

## DS audit dispositions (final, rev 3)

- **BLOCKER Q3 (args mechanism)**: ✅ Dissolved — agent infers role from its own identity context.
- **BLOCKER Q1 (tier drift)**: ❌ Re-disputed — Skills can be explicitly invoked (preserves order); 3-tier complication unnecessary. 2-tier locked.
- **RISK generator hook**: ✅ Accepted — separate installer step.
- **RISK wikilink ordering**: ✅ Accepted — #10690 dependency dissolved by scope.
- **CONFIRMED items**: ✅ As stated.

## Reference artifacts

- Research: `.squidsquad/pm/planning/RESEARCH-10781.md`
- DS feasibility audit: `.squidsquad/pm/planning/FEASIBILITY-10781-DS.md`
- This document: `.squidsquad/pm/planning/PHASE2-LOCKED-10781.md` (rev 3)

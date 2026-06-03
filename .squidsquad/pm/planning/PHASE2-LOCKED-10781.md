# Phase 2 LOCKED decisions for #10781 — Sub-skills as invokable Claude Skills

Final decisions after Phase 2 discussion + DS feasibility audit + operator refinements (2026-06-03 — final rev).

## Scope

Only entries in `docs/sub-skill-catalog.md` (the catalog) are in scope. Filesystem fragments under `references/sub-skills/` that aren't in the catalog are out of scope. After excluding deferred (chat trio) and planned (`compose-output-review`), real convertible set is ~50–60 entries.

## Terminology debt (acknowledged, deferred)

The architecture has two distinct runtime-invocation tiers but both are currently called "sub-skills" in TRDs, catalog, code, and the reference grammar. **Operator decision (2026-06-03): keep the existing "sub-skill" terminology for PRD-D and ship under that conflation.** Reconciliation effort (TRD revisions, catalog restructure, code identifier renames, possible grammar split into `→ run rule:` vs `→ invoke skill:`) is acknowledged as ~6–8 weeks of work and **deferred indefinitely** — may be picked up after several future PRDs land if the conflation becomes painful, otherwise treated as permanent legacy nomenclature. No tracking issue filed; this section is the record.

## Final decisions (rev 2 — 2-tier)

| # | Decision | Operator pick |
|---|----------|---------------|
| Scope | What's in scope? | Catalog entries at `docs/sub-skill-catalog.md` only. Out-of-catalog fragments untouched. |
| Route | Where do `.claude/skills/<name>/SKILL.md` files come from? | **Deploy-time generator** (separate installer step) reads `references/sub-skills/` templates for catalog entries → writes `.claude/skills/<name>/SKILL.md` artifacts. Sources unchanged at authoring time. |
| Q1 | Which sub-skills convert to Claude Skills? | **2-tier classification (all entries still called "sub-skills" in catalog/grammar/code)**: <br>• **Inlined standing rules** (~3–5): body inlined in CLAUDE.md at compose time because they're observed rules, not invocable procedures. `self-restart`, `agent-lifecycle`, `context-pressure`, plus the cycle scaffold itself (boot sequence + 3-phase cycle structure). <br>• **Claude Skills** (~55–60): everything else in catalog. Generated `SKILL.md` at `.claude/skills/<name>/`. Composed CLAUDE.md's cycle scaffold invokes them explicitly via `→ run sub-skill: <name>` references (grammar redefined: agent invokes Skill tool, not Read tool), OR the model invokes them discretionarily via description matching. Includes: `checkin`, `task-intake`, `task-approval`, `pipeline-sentinel`, `triage-issues`, `implement-tasks`, `verification`, `delivery-packaging`, `version-bumps`, `health-check`, `vault-remember`, `vault-optimize`, `vault-synthesis`, `improvement-scan`, `improvement-scan-slim`, `soul-shepherd`, `l4-curation`, `boot-remote-agents`, `git-commit`, `issue-filing`, `discussion`, `boot-bootstrap`, `cycle-runner`, all role-specific procedures, etc. <br>**Why this works**: DS audit BLOCKER 2 (ordering risk) was based on assuming discretionary invocation only. Skills can also be invoked explicitly from the cycle scaffold by the agent, preserving order. The scaffold remains inlined; only the procedure bodies live in `.claude/skills/`. |
| **Per-agent install filter** | Which Skills go into which agent's `.claude/skills/`? | **Per-clone materialization.** Catalog has a `Used by` column that lists which agents use each sub-skill (e.g., `boot-remote-agents` is PM-only; `delivery-packaging` is DM-only; `boot-bootstrap` is all roles). The materializer reads this column and installs a Skill into an agent's clone ONLY if that agent uses it. Each agent clone (`D:\Dev\Dev\SquidSquad`, `-2`, `-qa`, `-3`) gets its own filtered `.claude/skills/` directory. Result: an agent's available-Skills metadata at session start is restricted to Skills it can actually use — no context pollution from inapplicable Skills. |
| Q2 | Dual-purpose vs export? | **Export** (confirmed by deploy-time-generator route). |
| Q3 | `[ROLE]` placeholder handling | **One shared SKILL.md per Claude Skill (across all installs that include it).** The agent invoking the Skill already knows its own role (from its composed CLAUDE.md identity — "You are PM"). The generated SKILL.md uses prose instructions like "use your own role name (`pm`/`dm`/`qa`/`skill`) wherever you see `<your-role>` below". Agent fills in its role at runtime by reading the instructions. No Skill tool runtime args needed (which don't exist per DS audit). No N×M per-role-class file proliferation. (The per-agent filter above governs WHICH Skills are installed in which clone, not their CONTENT — content is the same shared template.) |
| Q4 | `[[wikilink]]` handling | **PRD-D ships without #10690 dependency.** Wikilinks in Claude-Skill-tier sub-skills point primarily at vault notes (not other sub-skills). Preserved as plain text in generated SKILL.md. Sub-skill-to-sub-skill wikilinks are concentrated in `common-events/` which stays runtime-loaded by `boot-bootstrap` (out of PRD-D scope). #10690 dependency dissolves. |
| Q5 | L1–L4 surrounding context | **Accept reduced fidelity** — skills are project-scoped only (per-clone), so the surrounding composed CLAUDE.md is always present at invocation time within the SquidSquad install. |
| Q6 | Catalog and discovery | Catalog stays at `docs/sub-skill-catalog.md`; add **`tier`** column (`inlined-rule` / `skill`) and **`skill-description`** column (human-authored, used by generator for SKILL.md `description:` frontmatter). The existing **`Used by`** column drives the per-clone materialization filter. `catalog_parser.py:394` guard unchanged. New columns at end of table — parser already supports N-column tables per DS audit Concern 4. |
| Q7 | TRD vs PRD framing | **PRD-D under COMPOSE-ARCHITECTURE TRD**; not a new TRD. |
| #10362 | Existing follow-up issue | **Fold into PRD-D** — close #10362 as superseded by PRD-D. |
| Generator hook | Where does the materializer run? | **Separate installer step**. Runs at install and at `squidsquad-upgrade`. Has its own freshness check (catalog hash + `Used by` filter hash vs last-materialized hash, analogous to COMPOSE-ARCHITECTURE §8.1). Per-clone materialization handled in a loop over `config.md` aliases. Decouples from per-alias compose; keeps compose fast. |
| Cap monitoring | Drift protection | PM tracks per-clone Claude Skill count in routine improvement scans. Flag when an individual clone exceeds 70 Skills installed for tier review (to prevent decision-overload drift). System-wide cap is ~80 Skills before the upfront-context cost (~15K tokens at session start, rough) starts to noticeably bite. |
| Gate | Hard pre-req | **E6 #10685 must ship before PRD-D implementation begins.** |

## DS audit dispositions (final)

- **BLOCKER Q3 (args mechanism)**: ✅ Dissolved — agent infers role from its own identity context, not from runtime args.
- **BLOCKER Q1 (tier drift)**: ❌ **Re-disputed and rejected** by operator. DS conflated "can be discretionary" with "must be discretionary." Skills can be invoked explicitly from the cycle scaffold (preserves order) AND discretionarily by the model. The cycle scaffold stays inlined in CLAUDE.md so step ordering is preserved. The 3-tier complication is unnecessary.
- **RISK generator hook**: ✅ Accepted — separate installer step.
- **RISK wikilink ordering**: ✅ Accepted — #10690 dependency dissolved by scope analysis.
- **CONFIRMED items** (reference grammar, catalog parser flexibility, upgrade path): ✅ As stated.
- **Pre-existing bug** (slash-bearing sub-skill name parser inconsistency): file as a follow-on bug if PRD-D execution surfaces it.

## What PRD-D actually delivers

1. **`tier` and `skill-description` columns** added to `docs/sub-skill-catalog.md`; backfill for all existing entries. `Used by` column already exists; verified accurate during backfill.
2. **Skill materializer** at a new script (e.g. `references/scripts/skill_materializer.py`) that:
   - Reads catalog
   - For each agent clone (resolved from `.squidsquad/.local-config`)
   - For each catalog entry where `tier == skill` AND this agent appears in `Used by`
   - Generates `.claude/skills/<name>/SKILL.md` in that clone, with prose role-resolution baked in per Q3
3. **`squidsquad-upgrade` migration step** for materializing on existing installs.
4. **Freshness check** — installer compares (catalog hash, per-clone Used-by filter hash) against last-materialized hash; re-materializes when stale.
5. **Cycle scaffold update**: composed CLAUDE.md's `→ run sub-skill: <name>` references are reinterpreted at runtime as Skill tool invocations (was Read tool). For catalog entries with `tier == inlined-rule`, body is still inlined and there's no `→ run sub-skill:` reference for it. Reference-grammar parsers (`v2_catalog_gate.py`, `assemble_verifier.py`, `link_stage_validator.py`) unchanged (regexes still capture the name correctly per DS audit Concern 2).
6. **`docs/COMPOSE-ARCHITECTURE.md §4.5.1`** updated from "Gap" to "Delivered by PRD-D".
7. **#10362 closed as superseded** by PRD-D.

## Open questions deferred to Phase 3 (AC drafting)

- Exact tier classification per catalog row (inlined-rule vs skill). Initial list above is provisional; Phase 3 audits each row against the test ("would skipping it entirely be acceptable AND does the cycle scaffold orchestrate its invocation order if needed?").
- Whether `boot-bootstrap` and `cycle-runner` stay inlined or convert. They're invocable procedures but boot-time efficiency may favor inlining. Phase 3 reads the actual files to decide.
- Whether `compose-output-review` (planned, not implemented) gets the `tier: skill` classification preemptively.

## Reference artifacts

- Research: `.squidsquad/pm/planning/RESEARCH-10781.md`
- DS feasibility audit: `.squidsquad/pm/planning/FEASIBILITY-10781-DS.md`
- This document: `.squidsquad/pm/planning/PHASE2-LOCKED-10781.md` (rev 2)

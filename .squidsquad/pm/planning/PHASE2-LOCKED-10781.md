# Phase 2 LOCKED decisions for #10781 — Sub-skills as invokable Claude Skills

These are the decisions operator approved in Phase 2 discussion. This is the input for the feasibility audit.

## Decision summary

| # | Decision | Operator pick |
|---|----------|---------------|
| Route | Where do `.claude/skills/<name>/SKILL.md` files come from? | **β — deploy-time generator** reads `references/sub-skills/` templates → writes `.claude/skills/<name>/SKILL.md` artifacts. Sources unchanged at authoring time. |
| Q1 | Which sub-skills convert? | **Tiered**: ~5 mandatory stay inlined in composed CLAUDE.md (`boot-bootstrap`, `cycle-runner`, `context-pressure`, `self-restart`, `agent-lifecycle`); ~20 situational become Claude Skills (`vault-remember`, `improvement-scan`, `pipeline-sentinel`, `task-intake`, `l4-curation`, `boot-remote-agents`, `delivery-packaging`, `version-bumps`, `vault-optimize`, `vault-synthesis`, `soul-shepherd`, `checkin`, `task-approval`, `issue-filing`, `discussion`, `git-commit`, etc.). |
| Q2 | Dual-purpose vs export? | Export (confirmed by route β). |
| Q3 | `[ROLE]` placeholder handling | **One shared SKILL.md** per sub-skill; `[ROLE]` stays as a literal token in the generated SKILL.md body; the SKILL.md instructs Claude to read `role` from invocation args; each agent's CLAUDE.md becomes `→ run sub-skill: vault-remember (role=pm)`. |
| Q4 | `[[wikilink]]` handling | **#10690 ships first**, building the `[[name]]` → Skill-invocation transformer. PRD-D's generator reuses it; PRD-D does not ship until #10690 is shipped. |
| Q5 | L1–L4 surrounding context | **Accept reduced fidelity** — skills are project-scoped only, so the surrounding composed CLAUDE.md is always present at invocation time within a SquidSquad install. Skills won't work outside a SquidSquad install (acceptable per TRD). |
| Q6 | Catalog and discovery | Catalog stays at `docs/sub-skill-catalog.md`; add **tier** + **skill-description** columns; `catalog_parser.py:394` guard unchanged (still rejects `.claude/skills/` paths in the source-path column). |
| Q7 | TRD vs PRD framing | **PRD-D under COMPOSE-ARCHITECTURE TRD**; not a new TRD. |
| #10362 | Existing follow-up issue | **Fold into PRD-D** — close #10362 as superseded by PRD-D. |
| Gate | Hard pre-req | E6 #10685 must ship before PRD-D implementation begins. |

## Required for feasibility audit

Verify the following are actually feasible:

1. **Claude Skill `args:` mechanism (Q3 critical)** — does the Claude Code Skill tool / SKILL.md format support runtime arguments? Audit on-disk evidence: the SquidSquad root SKILL.md is the available reference. Are there other on-disk SKILL.md examples in the repo that show args usage? If args aren't supported at the SKILL.md schema level, Q3 option B is infeasible and we must fall back to per-role files.

2. **Reference grammar (Q3)** — does the current `→ run sub-skill: <name>` grammar (used in role-class L2 sub-skills as a directive an agent reads) extend cleanly to `→ run sub-skill: <name> (role=pm)`? Or does that conflict with anything in the link/assemble passes (PRD-A/PRD-B)?

3. **Generator hook point (route β)** — where in the current compose/install pipeline does the SKILL.md generator slot in? Is it a new step in `compose.py deploy <alias>` (so each deploy regenerates the alias's skills)? A separate installer step run once at setup? An on-demand step run when catalog changes? Each option has different file-watcher / freshness check implications (interacts with PRD-E freshness).

4. **Tier classification authority (Q1)** — the decision places the tier classification in `docs/sub-skill-catalog.md` columns. Confirm the catalog grammar supports new columns without breaking `catalog_parser.py`. The current parser is at AC5 (line 394+) per the audit context — does it accept N columns or is it pinned to a specific count?

5. **Wikilink ordering (Q4)** — #10690 was filed gated on E6+E7. PRD-D is now also gated on #10690. Audit: is the dependency chain coherent (E6 → E7 → #10690 → PRD-D), or does this serialization create a critical-path bottleneck? Are there parts of PRD-D that could ship before #10690 without the wikilink transformer?

6. **Tier mandatory/situational drift risk (Q1)** — the listed mandatory set is ~5; the situational set is ~20. Are there sub-skills currently listed under "situational" that have hidden deterministic ordering requirements (e.g., they MUST run after another specific sub-skill)? If so, converting them to Claude Skills (description-matching invocation) breaks that ordering. Specifically audit: `vault-remember` (end of cycle), `pipeline-sentinel` (after work step), `checkin` (start of cycle).

7. **Existing install upgrade path (Q5 + Q6)** — agents currently have `.squidsquad/<role>/CLAUDE.md` with inlined sub-skill content. After PRD-D, situational sub-skills no longer appear inlined — they're at `.claude/skills/` instead. What's the upgrade migration? Does the operator have to manually clear something, or does `squidsquad-upgrade` handle it?

## What the audit should output

For each feasibility concern: **CONFIRMED / RISK / BLOCKER** with evidence (file paths + line numbers). For BLOCKER findings, propose an alternative.

## Reference docs

- Research artifact: `.squidsquad/pm/planning/RESEARCH-10781.md`
- CONTEXT (Phase 1): `.squidsquad/pm/planning/CONTEXT-10781.md`
- TRD: `docs/COMPOSE-ARCHITECTURE.md` (§4.5.1 is the relevant section)
- Catalog: `docs/sub-skill-catalog.md`
- Catalog parser: `references/scripts/catalog_parser.py:394`
- SKILL.md example: `SKILL.md` (repo root)

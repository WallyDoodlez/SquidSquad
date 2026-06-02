# RESEARCH TASK: Sub-skills as invokable Claude Skills (post-E6 architecture slice)

## Operator directive (verbatim)
> "In our new arch, we want to make our subskills actual skills of Claude so they can be invoked"

## Status of prior decision
The 2026-05-24 park (sub-skills are internal composition units, no public surface) is **un-parked** as of 2026-06-02. The `project_marketplace` kill remains in force — this is NOT about a marketplace, monetization, or public directory. It's about making internal sub-skills runtime-invokable via the Skill tool.

## Hard gate
**Cannot start until E6 (#10685) ships.** Reason: scoping a TRD-level architecture slice during an in-flight atomic cutover risks derailing the cutover. The skill agent's queue priority is E6 → E7 → wiki-link rework (#10690) → THIS.

## Scope of the research

Phase 1 research only. Produce `RESEARCH-subskill-as-skill.md` answering:

### Q1 — Which sub-skills convert?
- All of them? Many existing sub-skills are slot/op fragments (`### append`, `### insert-after`) that have no meaning standalone — they're compose-time content insertions.
- A curated subset that represents coherent, self-contained, durable capabilities?
- New tier classification: "fragment" (compose-only) vs "skill" (compose + invokable)?

### Q2 — Dual-purpose vs export?
- **Dual-purpose**: same file works as both compose fragment AND Claude Skill. Requires frontmatter that satisfies both schemas. Risk: invokable surface vs slot-content semantics conflict.
- **Export**: compose emits derived `SKILL.md` packages at deploy time. Source files stay slot/op format; deployer generates Claude Skill artifacts at `.claude/skills/<name>/SKILL.md` (or equivalent path).
- Trade-offs: dual-purpose is leaner but constrains authoring; export is heavier but keeps the layers clean.

### Q3 — Compose-time placeholder handling
- Sub-skills use placeholders like `<the-role-placeholder>` and `<the-interval-placeholder>` that `compose.py:_substitute_placeholders` resolves at deploy time.
- Standalone Claude Skills have no equivalent substitution machinery.
- Options: (a) resolve at packaging time (skill is role-pinned), (b) defer to Skill tool's args mechanism (user passes role), (c) strip and accept reduced fidelity.

### Q4 — Wikilink handling
- Sub-skills cross-reference via `[[other-sub-skill]]`. Once they become Claude Skills, those references become invocations (`Skill({skill: "other-sub-skill"})`).
- Need a wikilink → Skill-invocation transformer at packaging time.
- Or — keep wikilinks as informational references; users invoke other skills manually.

### Q5 — L1–L4 surrounding context
- Sub-skills assume composed CLAUDE.md context around them (project context, role identity, etc.).
- Standalone Skill invocations don't have that context.
- Options: (a) self-contained skills inline the minimum context they need, (b) skills declare a "context-required" capability that the orchestrator must provide, (c) accept reduced fidelity outside the SquidSquad-composed environment.

### Q6 — Catalog and discovery
- Current catalog is internal (`docs/sub-skill-catalog.md`).
- Claude Skills are discovered via `~/.claude/skills/` or per-project paths.
- Need a deploy mechanism that publishes selected sub-skills to a discoverable path.
- Hard guard at `catalog_parser.py:394` (no `.claude/skills/` in catalog) needs revisiting — it was added under the parked stance.

### Q7 — TRD impact
- Does this fit under existing COMPOSE-ARCHITECTURE TRD as a new PRD slice, or warrant its own TRD?
- Interaction with PRD-A (link stage), PRD-B (assemble), PRD-C (L4 customization) — does the assemble pass run on Skill-packaged outputs too?
- E6 cutover already simplifies the v2 path; this slice slots cleanly post-cutover or it doesn't.

## Out of scope for Phase 1
- Implementation of the conversion mechanism (that's later phases).
- Reviving the marketplace / public directory (still killed per `project_marketplace`).
- Renaming "sub-skill" → "skill" wholesale (vocabulary cleanup follows architectural decisions).

## Deliverables
- `.squidsquad/pm/planning/RESEARCH-subskill-as-skill.md` answering Q1–Q7 with recommended option per question and trade-off summary.
- Recommendation on PRD vs TRD framing.
- Risk list for E6 cutover interaction (anything that would have wanted different cutover design if we'd known).

## Recommended PM action
File this as a research-tier task (not approved for implementation). After E6 ships, transition to research; produce RESEARCH artifact; then Phase 2 discussion with operator; then decide PRD vs TRD framing and implementation slices.

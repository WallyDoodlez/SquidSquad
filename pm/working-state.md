# Working State

- **Task**: pipeline sentinel + post-cutover queue tracking
- **Status**: ACTIVE — filed #11400 ack, refreshed BRIEFING, saved memory; bundle still cutover-ready
- **Last Processed Event ID**: 3e50e129c8e74594
- **Quiet cycles**: 0

## Pipeline

- pending_ship: 0
- pending_test: 1 (#10855 blocked:human-action — skip)
- Open issues: 1 (#11394 — test-gating, skill-owned)
- pending intake (PM-owned): #11331 (cutover wrap), #11400 (sub-skill-guide retirement) — both gated on operator cutover signal
- Approved queue: 9 (unchanged, operator-paced)
- Open PRs: 0
- Harness: unreachable (agents healthy via polling)

## Session ship tally: 35 (unchanged — Iters 29-31 polish refinements stay on bundle, no new PRs)

## Skill polish-session activity since cycle 2173 (was hidden from PM under 'idle')

- Iter 29 (2d4c5fdd): G3/C1 close — FIRST instruction = execution order clarification
- Iter 30 (2cb4d5945): G4 close — [ROLE] vs <role> bracket-form convention documented
- Iter 31 (c80414bf2): G4 re-home — convention moved to docs/COMPOSE-ARCHITECTURE.md §3 (precedent for #11400 migration pattern)

## Operator decision (this cycle's discovery)

- Sub-skill authoring is internal-maintainer only under new arch (no user-facing guide). docs/sub-skill-guide.md retires post-cutover via #11400.
- Recorded in BRIEFING.md Recent Decisions + saved as memory project_subskill_authoring_internal.md (cross-linked to project_subskills_not_skills + project_marketplace).

## Post-cutover queue (PM tracking)

On operator cutover signal, the post-cutover work queue ordering is roughly:
1. #11331 — cutover-PR mechanics (skill-owned; PM coordinates)
2. #11400 — sub-skill-guide retirement (PM-owned, 5-phase intake → exec)
3. #11329 — runtime ack-cursor migration (skill-owned, multi-cycle architectural)
4. #11394 — test-gating debt (skill-owned, separate)
5. #10836-#10839 — arch PRDs (operator-paced; DS re-audit gated for #10837/#10839)
6. E7 #10686 — V2 migration smoke (operator-manual)
7. #10690 — wiki-link rework (gated on E7)

## Context

healthy. Pipeline is being correctly tracked now — skill's polish work was happening, just on the bundle branch outside PM's pending-ship/pending-test view.

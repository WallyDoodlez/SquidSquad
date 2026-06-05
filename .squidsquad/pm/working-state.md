# Working State

- **Task**: cycle 2143 — #11049 AC3 ruling (Path A composite-size ceilings revised)
- **Status**: PR #11069 pending-test; spec call resolved
- **Last Processed Event ID**: 3e50e129c8e74594
- **Quiet cycles**: 0

## Cycle work

- **#11049 AC3 ruling**: skill cycle 1597 shipped Path A migration on PR #11069 (-4179 LOC, 137 directives processed: 77 references + 19 mandatory inline + 20 domain-context + 21 D1-retired inline). Composites dropped ~50% (pm 2196→1066, dm 1568→1006, qa 1789→1008, skill 1964→1268). Skill flagged AC3: original body said pm/qa/skill ≤700, dm ≤800 — pre-Path-A D2 numbers that assumed pure references.
- **Ruling filed on #11049**: revised AC3 to tiered ceiling — L2 base roles ≤1100, L3-specialized (skill) ≤1300. Rationale: Path A mandatory-inline budget (~503 lines/role) is a structural floor that didn't exist when D2 measured 22-29%. All four roles PASS revised AC3. Future #9968 (runtime sub-skill resolution) is the path to lower ceilings.
- Issue body AC3 updated to match the ruling so QA's TEST-PLAN reads the correct contract.
- BRIEFING.md updated: moved #11042+#11066 from pending-ship to shipped; reflected #11049 status change to pending-test; logged AC3 ruling in Recent Decisions.

## Pipeline (post-skill cycle 1597, DM cycle 1350)

- pending_ship: 0
- pending_test: 2 (#10855 deferred — PR #10952; **#11049 fresh — PR #11069 awaiting QA**)
- in-progress: none
- Approved queue: #11053 (gated on #11049), #10686 (E7 unblocked), #10690 (gated on E7), #10836+#10838 (PM-ready), #10837+#10839 (PM, awaiting DS re-audit)
- Open PRs: 2 (#10952 deferred; **#11069 draft, AC3-cleared, QA's lane**)

## v2 stabilization work map

| Surface | Status | Owner |
|---|---|---|
| 1. References only, no inline (v1 {{include:}} → Path A hybrid) | **pending-test** (PR #11069) | #11049 skill → QA |
| 2. Sub-skill code bundling | deferred | #11051 closed |
| 3. Claude Skills audit | decided against | #11052 + #10781 closed |
| 4. Agent-spawn assemble | approved, gated on #11049 | #11053 pm |
| Cleanup (API-assemble prune) | shipped | #11050 closed |
| E6 v2 cutover | shipped 2026-06-04 | #10685 closed |
| E7 smoke | unblocked, awaiting skill | #10686 skill |
| Tracker hygiene (.backlog-cache) | shipped | #11065 closed |
| Pytest suite stabilization | shipped 2026-06-05 | #11042 closed |
| L4 corrupt test alignment | shipped 2026-06-05 | #11066 closed |
| Runtime sub-skill resolution (lower L2 ceiling) | not started | #9968 future PRD |

## TRD-alignment PRD queue (post-E6, unblocked)

- #10836 INSTALLER-ARCH (HIGH, Direction A pre-locked) — PM can pick up
- #10838 VAULT-ARCH (medium) — PM can pick up
- #10837 HARNESS-ARCH (HIGH) — needs DS re-audit before PM pickup
- #10839 Cross-TRD rename (medium) — needs DS re-audit before PM pickup

## Session ship tally: 38 (+2 since cycle 2142: #11042 + #11066 shipped by DM batch)

## Context

healthy (~85%).

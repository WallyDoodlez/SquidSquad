# Master Plan — Test Gate + Installer Doc Reconciliation

**Date**: 2026-06-12 (cycle 2323)
**Trigger**: operator-prompted consolidation of two parallel discovery chains
**Status**: routed to skill (#11505) + PM (#10836 R1) + skill (#11503 already)
**Operator visibility**: present in conversation; this artifact for durability across context boundaries

---

## Discovery chains

### Chain 1 — INSTALLER-ARCH audit (PM, operator-prompted)

Per `.squidsquad/pm/planning/AUDIT-INSTALLER-ARCH-2026-06-12.md`:

- 5 ERROR / 6 WARNING / 3 LOW
- Real architectural drift in 4 places (E1+W2, E4, E5, E2)
- Stale model in 2 places (W4 vault access; W6 L4 seed format)
- 6 cross-ref imprecisions (E3, W5, W3, L1, L2, L3)

### Chain 2 — Test debt (skill self-filed, #11503)

23 static tests silently red since v0.44.0 cutover (gate was dead due to deleted `test_l2_l3_op_anchoring_11227` left in STATIC_TEST_MODULES):
- Group A: 15 stale tests (mechanical sweep against v2/rename reality)
- Group B: 1 fixture drift (`test_config_functions` FIELD_MAP)
- Group C: 4 possibly-real masked regressions (statusline sync, manifest registry, capabilities-empty, chat-etiquette format)

## Cross-cutting decisions (HARD GATE both)

### Decision A — Canonical clone discovery
INSTALLER-ARCH §1.2+§3.2 says `~/.squidsquad/clones/<alias>`. HARNESS-ARCH §7.2 says `.squidsquad/.local-config`. Code investigation needed (harness.py, start.sh, boot_remote.py) to determine canonical mechanism. PM owns; gates #10836 R1 scope-lock.

### Decision B — Capabilities directory removal
INSTALLER-ARCH §8.3 already pre-decides removal. #11503 Group C `test_feat328_coverage` failure is *expected* post-removal. Converted to tracked task via #11505.

## Routing

| Item | Destination | Lane | Status |
|---|---|---|---|
| 23-test debt classification | #11503 (existing) | skill | triaged c-2323, pickup order C→A→B |
| INSTALLER-ARCH audit findings | #10836 (existing PRD umbrella) | PM | R1 scope expansion c-2323; R2 dep-provisioning deferred |
| Capabilities deadwood removal | #11505 (filed c-2323) | skill | open, bug-class auto-approved |
| #11394 pending-test | #11394 (existing) | QA | verification in flight |
| Decision A investigation | PM internal | PM | autonomous pickup when capacity allows |

## Sequencing constraints

1. **Decision A must resolve before #10836 R1 scope locks** — fix can't land until we know which doc is wrong.
2. **#11505 lands → INSTALLER-ARCH §8 touch-up rolls into #10836 R1** — removes 'slated for removal' framing once removal completes.
3. **#11503 Group C `test_feat328_coverage` exits via #11505** — once capabilities removed, that test becomes legitimately stale (joins Group A).
4. **#11503 PR strategy**: split A/B/C. Group C may surface real bugs needing separate issues. Group A bulk-mechanical safe to chain. Group B trivial.
5. **#11394 verification independent** — QA picks up regardless of other work.

## Risk register

- **Decision A could surface harness code drift** — if INSTALLER-ARCH is right, HARNESS-ARCH §7.2 needs sweep (might block #10837 HARNESS-ARCH alignment too).
- **#11503 Group C `test_statusline_schema`** — `references/statusline.sh` vs `.squidsquad/statusline.sh` sync gap is real if the cp deploy step is broken; could indicate broader install-time copy-step problem (relevant to INSTALLER-ARCH Phase 5/6).
- **#11503 Group C `test_manifest_registry`** — registry validation failure may indicate broken compose manifest state post-cutover; relevant to all four PRD umbrellas.
- **Event-mode validation** — operator wanted to watch agents react to forge events. This cycle's comments + #11505 filing emit 5+ events (status-transition, tracker-comment ×4). If skill + QA don't pick these up via event-mode reactions, that's a real signal worth investigating.

## Memory implications

- `[[project_upgrade_is_fresh_install]]` confirmed (INSTALLER-ARCH §2 commitment 3 + §4.3).
- `[[feedback_pm_docs_only]]` applies (PM owns doc fix lane; #10836 R1).
- `[[feedback_bugs_need_research]]` applied (PM triage on #11503 before skill pickup).
- `[[feedback_auto_approve_bugs]]` applied (#11505 bug-class auto-approved, no human gate needed).
- `[[feedback_plan_first]]` applied (HARD GATE on Decision A before R1 scope locks).
- `[[pattern_chain_ship_per_item_auth]]` may apply if #11503 + #11505 + #10836 R1 land tightly together; per-item PM auth still required if they go to a bundle branch.

## Open operator questions (when ready)

- Decision A: should PM investigate code or defer to skill with explicit assignment? (PM-can-investigate per investigation lane; code work to fix would route to skill regardless of who decides.)
- Decision B: any preference between deletion of `test_feat328_coverage` vs repurpose as regression guard? (Left to skill judgment in #11505 AC5.)
- Bundle strategy: should #11505 + #11503 A/B fixes + #10836 R1 use a fresh bundle branch (polish-session pattern) or all-main-direct? (Polish-session was load-bearing because of compose-stabilization risk; this work has narrower blast radius — recommend main-direct unless audit surfaces wider cross-cuts.)

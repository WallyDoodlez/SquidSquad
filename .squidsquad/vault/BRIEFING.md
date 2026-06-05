# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- **4 umbrella PRDs from DS TRD audits** (approved, all UNBLOCKED post-E6 ship 2026-06-04):
  - #10836 INSTALLER-ARCH alignment (HIGH: migration walk, VERSION file, squidsquad_version field) — Finding 26 pre-locked Direction A 2026-06-03; ready for PM pickup
  - #10837 HARNESS-ARCH alignment (HIGH: POST /events/{id}/complete contradiction, POST /work/assign missing) — DS re-audit needed before pickup
  - #10838 VAULT-ARCH alignment (4 GAP + 6 DRIFT)
  - #10839 Cross-TRD role → alias rename — DS re-audit needed before pickup
- **E7 #10686** (approved, role:skill) — V2 migration smoke; unblocked post-E6
- **#11053 agent-spawn substrate for v2 §4.6 assemble** (in-progress, role:pm) — Phase 1 v1 deliverable committed at `.squidsquad/pm/planning/V2-AGENT-ASSEMBLE-DESIGN.md` (cycle 2143 ext); 5 operator-review questions in §9 outstanding. Substrate is Agent-tool spawn (replaces retired PRD-B API substrate); §4.6 architectural vision unchanged from v2 draft.
- **#10690 wiki-link rework** (approved, gated on E7)
- **#10750 catalog orphan cleanup** (open, role:skill) — D4 drift-check surfaced path drift from #6274 dev→worker rename

## Recently Shipped

- **#11049 v2 {{include:}}→Path A migration** (shipped 2026-06-05 via PR #11069, DM cycle 1351) — -4179 LOC; 137 directives processed; composites ~50% smaller (pm 2196→1066, dm 1568→1006, qa 1789→1008, skill 1964→1268). PM-revised AC3 (L2≤1100, L3≤1300) validated by QA verification.
- **#11042 pytest suite stale refs** (shipped 2026-06-05 via PR #11048, DM batch cycle 1350) — 5-cluster stabilization, 271/271 pass at HEAD 5de4b7c57.
- **#11066 stale L4 corrupt test** (shipped 2026-06-05 via PR #11068, DM batch cycle 1350) — post-#10987 prose-H3 routing alignment.
- **#11065 .backlog-cache untrack** (shipped 2026-06-05 as 1dd58709c via PR #11067) — root cause for #10540 merge-spiral pattern eliminated.
- **#11050 assemble pipeline prune** (shipped 2026-06-05 as 1deeac641 via PR #11064) — -3757 LOC dead LLM-assemble pipeline removed.
- **E6 V2 CUTOVER #10685** (shipped 2026-06-04) — atomic switch, v1 compose paths dropped, v2 default. Unblocks E7 + 4 umbrella PRDs.
- **PRD-D #10781** (closed 2026-06-05) — research closed; decided against Claude Skills migration (per closure decision).
- **PRD-A (compose link stage)** — A1-A6 + A2.6 + A2a-A2f + A4.5 shipped. DS-audit umbrella #10751 shipped.
- **PRD-B (compose assemble stage)** — B1-B8 + B9 wiring (#10763) shipped. DS-audit umbrella #10752 shipped.
- **PRD-C (L4 customization)** — C1-C10 shipped (cycles 1490-1499). DS-audit umbrella #10753 shipped.
- **TRD set Claude final-pass** — All 5 TRDs audited via DS 2026-06-03; 4 umbrella PRDs filed for follow-up.
- **#6274 dev→worker/qa→verifier terminology rename** — partial; cross-TRD rename completion deferred to #10839.

## Core Architecture

- **Layered roles**: L1 (base) → L2 (role) → L3 (domain) → L4 (project). compose.py assembles.
- **Harness**: Agent lifecycle owned by harness (REST API intent, .harness-state.json). Singleton enforcement, intent state machine.
- **Branching**: Code → main. State → squid-squad. Feature branches per task (#9478).
- **Delivery hierarchy**: TRD → PRD → Stories → Tasks. TRDs at `docs/*-ARCH.md`. Currently in TRD-polish + early-PRD phase.
- **Tracker**: GitHub Issues with structured labels. tracker.py is abstraction layer (non-GitHub backends post-v1).
- **PM boundary**: docs only; worker owns all code + code-consumed data per `feedback_pm_docs_only`.

## Recent Decisions

- #11049 AC3 revised 2026-06-05 — Path A mandatory-inline budget (~503 lines/role) is a structural floor; tiered ceilings L2≤1100 / L3≤1300 supersede pre-Path-A D2 numbers (700/800). Further composite reduction is gated on #9968 (runtime sub-skill resolution).
- PRD-D #10781 closed (decided against Claude Skills migration, 2026-06-05) — composed-CLAUDE.md shrink path is via E6-shipped v2 compose, not via Claude Skills.
- Wizard L4 path Direction A pre-locked on #10836 Finding 26 — make wizard match `deploy_role_v2` per TRD §4.8; delete `_copy_l4_seed_stubs()` (2026-06-03).
- Audit refresh strategy: HARD GATE for #10836/#10838; DS re-audit needed for #10837/#10839 before PM pickup.
- Post-E6 queue order (revised): E7 → wiki-link → 4 umbrella PRDs.
- .backlog-cache structural fix (#11065 shipped 2026-06-05) — was driving the recurring merge-spiral pattern on long-lived feature branches; root cause eliminated.

## Human Preferences

- Never ship with failed TCs. Documents live on forge, not chat. Git = audit trail.
- PM should not intervene in code or branch management.
- Mechanical cycle operations should be deterministic code, not LLM prose interpretation.
- Never rebase, always merge (memory: feedback_never_rebase_merge_instead).
- See `[[human-profile]]` for full preferences.

## Constraints & Blockers

- Verifier agent intermittently fails to take after boot_remote.py — investigate if pattern persists.
- Auto-versioning: Shipped Since Last Bump = 16 (threshold 10) — DM-owned version bump overdue by 6.
- DS re-audit needed on #10837 + #10839 before PM picks them up (queued condition: E6 squash PR open; E6 has now shipped — re-audit is the current bottleneck).

## Team State

- Active agents: pm (SquidSquad), skill (SquidSquad-2), verifier (SquidSquad-qa), dm (SquidSquad-3)
- Current version: 0.43.0

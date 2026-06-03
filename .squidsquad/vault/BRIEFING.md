# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- **E6 V2 CUTOVER #10685** (in-progress, high, role:skill) — atomic switch dropping v1 compose paths, making v2 default. Branch `skill/e6-v2-cutover-10685`. Phase 3c.6 4/5 done (cycle 1552); ~4 cycles to squash PR per skill burndown. D6 #10677 bundled into E6 squash PR.
- **PRD-D #10781** (planned, gated on E6 ship) — sub-skills as invokable Claude Skills. Phase 2 LOCKED rev 3. 2-tier model: ~3 standing rules inlined + ~55-60 Claude Skills. Inserted ahead of umbrella PRDs in post-E6 queue per OOM-relief rationale.
- **4 umbrella PRDs from DS TRD audits** (approved, all gated on E6, #10839 also gated on PRD-D):
  - #10836 INSTALLER-ARCH alignment (HIGH: migration walk, VERSION file, squidsquad_version field) — Finding 26 pre-locked Direction A 2026-06-03
  - #10837 HARNESS-ARCH alignment (HIGH: POST /events/{id}/complete contradiction, POST /work/assign missing) — DS re-audit queued at E6 squash PR open
  - #10838 VAULT-ARCH alignment
  - #10839 Cross-TRD role → alias rename (gated on E6+PRD-D)
- **E7 #10686** (approved, gated on E6) — V2 migration smoke
- **#10690 wiki-link rework** (approved, gated on E6+E7)
- **#10750 catalog orphan cleanup** (open, role:skill) — D4 drift-check surfaced path drift from #6274 dev→worker rename; skill picks up post-E6

## Recently Shipped

- **PRD-A (compose link stage)** — A1-A6 + A2.6 + A2a-A2f + A4.5 shipped. DS-audit umbrella #10751 shipped.
- **PRD-B (compose assemble stage)** — B1-B8 + B9 wiring (#10763) shipped. DS-audit umbrella #10752 shipped.
- **PRD-C (L4 customization)** — C1-C10 shipped (cycles 1490-1499). DS-audit umbrella #10753 shipped.
- **PRD-D (catalog + wake-mode)** — D1-D5, D7, D8 shipped. D6 held for E6 bundle.
- **PRD-E (freshness + cutover)** — E1-E5 shipped. E6 in flight. E7 held.
- **TRD-polish settlement** — PR #10378 merged 2026-05-30 (5-round multi-doc TRD polish across COMPOSE/AGENT-RUNTIME/HARNESS/INSTALLER); PR #10379 merged 2026-05-30 (preset L1-L4 seeding for Agent Skill Dev Team).
- **TRD set Claude final-pass** — All 5 TRDs (COMPOSE, AGENT-RUNTIME, HARNESS, INSTALLER, VAULT) audited via DS 2026-06-03; 4 umbrella PRDs filed for follow-up.
- **#6274 dev→worker/qa→verifier terminology rename** (shipped 2026-05-23) — partial; cross-TRD rename completion deferred to #10839.
- **#9184 PM-AC-only / verifier-test-plan workflow** (shipped 2026-05-19).

## Core Architecture

- **Layered roles**: L1 (base) → L2 (role) → L3 (domain) → L4 (project). compose.py assembles.
- **Harness**: Agent lifecycle owned by harness (REST API intent, .harness-state.json). Singleton enforcement, intent state machine.
- **Branching**: Code → main. State → squid-squad. Feature branches per task (#9478).
- **Delivery hierarchy**: TRD → PRD → Stories → Tasks. TRDs at `docs/*-ARCH.md`. Currently in TRD-polish + early-PRD phase.
- **Tracker**: GitHub Issues with structured labels. tracker.py is abstraction layer (non-GitHub backends post-v1).
- **PM boundary**: docs only; worker owns all code + code-consumed data per `feedback_pm_docs_only`.

## Recent Decisions

- Sub-skills become invokable Claude Skills via PRD-D (#10781) — 2-tier model, per-clone `Used by` filter, ONE shared SKILL.md per Skill with prose role-resolution (rev 3, 2026-06-03).
- Wizard L4 path Direction A pre-locked on #10836 Finding 26 — make wizard match `deploy_role_v2` per TRD §4.8; delete `_copy_l4_seed_stubs()` (2026-06-03).
- Audit refresh strategy: HARD GATE for #10836/#10838; DS re-audit queued for #10837/#10839 at E6 squash PR open.
- Skill OOM mid-cycle pattern identified — silent kill on heavy E6 work, no MSYS2 stackdump. PRD-D expected to materially shrink composed CLAUDE.md.
- Post-E6 queue order: E6 → E7 → wiki-link → PRD-D → 4 umbrella PRDs (PRD-D inserted for OOM relief).

## Human Preferences

- Never ship with failed TCs. Documents live on forge, not chat. Git = audit trail.
- PM should not intervene in code or branch management.
- Mechanical cycle operations should be deterministic code, not LLM prose interpretation.
- Never rebase, always merge (memory: feedback_never_rebase_merge_instead).
- See `[[human-profile]]` for full preferences.

## Constraints & Blockers

- Skill silent OOM mid-cycle on heavy E6 work — PRD-D composed-CLAUDE.md shrink is the structural fix.
- Verifier agent intermittently fails to take after boot_remote.py — investigate post-E6 if pattern persists.
- Pending backlog mostly E6-gated — pipeline appropriately throttled.

## Team State

- Active agents: pm (SquidSquad), skill (SquidSquad-2), verifier (SquidSquad-qa), dm (SquidSquad-3)
- Current version: 0.43.0

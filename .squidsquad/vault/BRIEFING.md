# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- **v0.44.0 SHIPPED 2026-06-12** (cutover complete): PR #11402 merged `compose-polish-session` → `main` at commit `f8d867a9d`; tag `v0.44.0` created; #11331 closed; bundle composition = 5 chain-shipped (#11334 / #11382 / #11381 / #11383 / #11329) + 8 main-side this-session (#11403 / #11404 / #11165 / #11166 / #11139 / #11137 / #11227 / #11401) + 28 pre-bundle = 36 items.
- **#11394 in-progress** (severity:high, role:skill — bumped medium→high cycle 2319) — `run_tests.py` STATIC_TEST_MODULES gap; skill investigation surfaced worse-than-filed regression: static gate currently running ZERO tests (stale `test_l2_l3_op_anchoring_11227` entry post-cutover delete → pytest collection error → `collected 0 items` since v0.44.0 cutover). Plan: AC1 auto-discover refactor, AC2 explicit EXCLUSION set with issue refs, AC3 regression test for gating invariants, AC4 DS audit. Mid-investigation; awaiting full failing-set inventory + final exclusion design.
- **4 umbrella PRDs from DS TRD audits** (approved, operator-paced post-cutover):
  - #10836 INSTALLER-ARCH alignment (HIGH: migration walk, VERSION file, squidsquad_version field) — Finding 26 pre-locked Direction A 2026-06-03; ready for PM pickup
  - #10837 HARNESS-ARCH alignment (HIGH: POST /events/{id}/complete contradiction, POST /work/assign missing) — DS re-audit needed before pickup
  - #10838 VAULT-ARCH alignment (4 GAP + 6 DRIFT)
  - #10839 Cross-TRD role → alias rename — DS re-audit needed before pickup
- **E7 #10686** (approved, role:skill) — V2 migration smoke; operator-manual, unblocked post-E6
- **#10690 wiki-link rework** (approved, gated on E7)
- **Open PM-owned post-cutover queue**:
  - **#11400** (status:pending, role:pm, priority:medium) — Retire `docs/sub-skill-guide.md` + back-reference sweep + migrate maintainer-load-bearing content. Unblocked post-cutover; intake on operator signal.
  - **#11412** (status:open, role:pm, low-priority) — INSTALLER-ARCH.md TRD dep-provisioning section.
- **#11053 agent-spawn substrate for v2 §4.6 assemble** (in-progress, role:pm) — Phase 1 v1 deliverable committed at `.squidsquad/pm/planning/V2-AGENT-ASSEMBLE-DESIGN.md` (cycle 2143 ext); 5 operator-review questions in §9 outstanding.
- **Event-mode validation** (post-cutover focus 2026-06-12) — operator restarted harness, agents respawned via #9725 spawn prompt path. Skill bootup_complete false at last check (just respawned). Operator wants to "let them all rest at idle cycle first" before exercising event-mode end-to-end. PM keeps noise low during observation window.

## Recently Shipped

- **v0.44.0 CUTOVER 2026-06-12** — PR #11402 merged commit `f8d867a9d` at 17:31:57Z; tag `v0.44.0` created; CHANGELOG composed; #11331 closed. Session ship tally for this window: 38. Main-side direct ships this session: #11401 (wake-mode alignment via PR #11437), #11420 (#11165 dispatch-delete), #11403/#11404, #11139/#11137/#11227 (route-back stale-in-progress trio).
- **Polish-session chain-merges 2026-06-08/09** (4 items, all chain-shipped to `compose-polish-session` per PM per-item auth, deferred CHANGELOG to cutover):
  - **#11334** (DM c1872) — Canonicalize forge-usage instructions across sub-skills (tracker.py / git_ops.py / PR merge); 4-phase implementation (AC1 tracker-protocol expansion, AC3+AC4 new pr-protocol.md, AC2 mechanical consolidation, AC5 DS audit pass); +220/-138 LOC across 17+1+1 files.
  - **#11382** (DM c1876) — improvement-scan: `--role pm` → `--role pm-lead` deviation at pm/github-issues.md:27; 1-line fix.
  - **#11381** (DM c1877) — improvement-scan: orphan-test grandfathering for common/pr-protocol.md; scope expanded by skill into 2 walker regex root-cause fixes (backtick-tolerance + slash-prefix), resolving 7 false orphans organically.
  - **#11383** (DM c1879) — 6 compose-tests red on polish-session — boot-bootstrap assertions stale post-Iter-22; test-side updates retargeting 3 test files to post-Iter-22 canonical headings + DM bootstrap directive grammar.
- **#11083 + #11044 architectural branch-guard** (shipped 2026-06-05 batch DM cycle 1355) — `commit_role_scoped` skips operational files when current branch ≠ working branch; closes the merge-spiral class (sibling to #11065 `.backlog-cache` fix). PM-filed in cycle 2145 after observing BRIEFING.md pollution from `/loop` PM session in skill clone.
- **#10750 + #11046 + #11047 + #11045 post-cutover follow-ups** (shipped 2026-06-05) — catalog drift cleanup, manifest fixture rebind, doc path repoint, TC-11/TC-14 update. Entire #11042 scope-reduction sub-thread closed.
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

- **Sub-skill authoring scope** (operator decision via #11144 polish session, 2026-06-09) — under the new architecture, sub-skill authoring is **internal-maintainer only**. No user-facing authoring guide. `docs/sub-skill-guide.md` retires post-cutover (#11400). Compose mechanism (`compose.py`, `references/sub-skills/`) keeps working — just no public-facing "how to write a sub-skill" doc. Consistent with [[project_subskills_not_skills]] (sub-skills agent-internal compose-time) and [[project_marketplace]] (no public directory).
- **Chain-ship to bundle precedent** (#11382 c1876 / reaffirmed on #11381 / #11383) — chain-ship to `compose-polish-session` is **per-item, explicitly PM-authorized — NOT blanket auto-auth**. Qualifying lane: polish-session-originating AND bundle-scope. Scope expansion within the same lane is a positive signal not disqualifier. Broader bundle-wrap policy stays on #11331.
- **Cutover-PR Path A** (#11383 c-? 2026-06-09) — chain-ship items to bundle inline with their ship transition; defer v0.44.0 release semantics (CHANGELOG + version-bump) to a separate operator-prompted cutover-PR. Path B (inline-trigger v0.44.0 release inside a ship transition) rejected — would violate operator's c1383 bump-hold direction.
- **Cutover workflow** (#11331 c-? 2026-06-09) — once operator signals: (1) skill creates cutover-PR `compose-polish-session` → `main`; (2) skill transitions #11227 / #11139 / #11137 from in-progress → pending-test (assigned-role authority, brings tracker in line with actual work-on-bundle); (3) QA re-verifies all 3 on polish-HEAD (#11137 / #11139 = re-verify previously-verified on PR #11138 / #11141 before route-back; #11227 = fresh first-time pass); (4) DM ships all 7 (4 chain + 3 stale) via cutover-PR merge.
- #11049 AC3 revised 2026-06-05 — Path A mandatory-inline budget (~503 lines/role) is a structural floor; tiered ceilings L2≤1100 / L3≤1300 supersede pre-Path-A D2 numbers (700/800). Further composite reduction is gated on #9968 (runtime sub-skill resolution).
- PRD-D #10781 closed (decided against Claude Skills migration, 2026-06-05) — composed-CLAUDE.md shrink path is via E6-shipped v2 compose, not via Claude Skills.
- Wizard L4 path Direction A pre-locked on #10836 Finding 26 — make wizard match `deploy_role_v2` per TRD §4.8; delete `_copy_l4_seed_stubs()` (2026-06-03).
- Audit refresh strategy: HARD GATE for #10836/#10838; DS re-audit needed for #10837/#10839 before PM pickup.
- Post-E6 queue order (revised): polish-bundle cutover → E7 → wiki-link → 4 umbrella PRDs.
- .backlog-cache structural fix (#11065 shipped 2026-06-05) — was driving the recurring merge-spiral pattern on long-lived feature branches; root cause eliminated.

## Human Preferences

- Never ship with failed TCs. Documents live on forge, not chat. Git = audit trail.
- PM should not intervene in code or branch management.
- Mechanical cycle operations should be deterministic code, not LLM prose interpretation.
- Never rebase, always merge (memory: feedback_never_rebase_merge_instead).
- See `[[human-profile]]` for full preferences.

## Constraints & Blockers

- Auto-versioning: Shipped Since Last Bump = 0 post-v0.44.0 (DM reset post-cutover); next bump threshold-driven at 10.
- DS re-audit needed on #10837 + #10839 before PM picks them up; bottleneck deferred until post-cutover queue resumes operator pacing.
- Event-mode end-to-end NOT yet smoke-validated this session — harness/agents respawned post-cutover but operator wants idle-cycle rest first before exercising NUDGE → forge-read → ack-cursor full path. Manual-spawn vs harness-spawn distinction matters: only harness-spawned agents pick up #9725 spawn prompt + boot-bootstrap.
- DM cycle 1997 last_cycle_end 12:03:02 — may need attention if it doesn't tick over next idle window.

## Team State

- Active agents: pm (SquidSquad cycle 2322), skill (SquidSquad-2 just respawned, bootup_complete=false), qa (SquidSquad cycle 772), dm (SquidSquad-3 cycle 1997)
- Current version: 0.44.0

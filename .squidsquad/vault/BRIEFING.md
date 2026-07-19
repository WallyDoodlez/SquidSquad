# Squad Briefing

_Auto-maintained active context summary. Updated by agents when significant context changes._

## Active Priorities

- **>>> 2026-07-19 ~03:18 increment (fresh PM EVENT boot; quiet posture; overnight pipeline healthy) <<<** — **#10003 (VAULT-ARCH v2 TRD) sits at pending-human-review — PR #13708 all-gates-passed, awaiting operator merge approval** (the top HITL item, with #13263 and ~128 pending backlog). Overnight autonomous ships, all clean skill→qa→dm cycles with zero PM intervention: **#13735** (PM improvement-scan prepend fix), **#13737** (**tc_coverage.py discovery glob — the 'never bypassed' TC-coverage ship gate had been silently inert ~2 months**; fixed + 5 regression tests, PR #13740), **#13739** (verification-templates.md realigned to live-direct-verification practice, PR #13741; sibling disclosure issue #13738 resolved by verifier). PM improvement scan found the **doc-realignment backlog itself stale against the locked event-canonical architecture**: #10024 body rescoped (was superseded two-mode framing + falsely recorded #8702 closed), audit comments + operator recommendations on #8702 (rec: close-as-superseded) and #8698 (rec: re-scope or close — gated on removed `event-driven:` field, scopes deletion of the retained polling fallback). Post-merge recomposes run for #13740/#13741 — no composed-template drift. — Idle-cycle forge sweep found **12 CLOSED issues stranded with a stale `status:pending-ship` label** (PR closing-keyword auto-close bypassing DM's ship gate, recurred at scale post-#13371). Filed #13654 (high, role:skill) → shipped fast (2 verify rounds; qa caught a real live `gh pr edit`/GraphQL-deprecation env bug, fixed via `gh api -X PATCH` — see [[learning-closing-keyword-in-state-commit-autocloses-issue]] / [[learning-gh-pr-edit-broken-use-gh-api-patch]]). Also shipped the sibling `gh --limit 50` truncation sweep (#13660/#13661, tracker.py + cycle_pre.py) and an L4-write-commit pathspec safety fix (#13664, live before/after repro by qa). DM remediation: 12 stale labels repaired (`repair-status-labels --apply --include-unshipped`), ship counter reconciled `58→74`. All internal-only, no CHANGELOG. Note for future DM sweeps: use `list-issues`/`list-bugs`, not `list-tasks`, for `type:issue` pending-ship items (see [[learning-pending-ship-query-includes-closed]]).
- **>>> 2026-07-18 ~00:30 increment (FRESH PM EVENT-mode boot; Verbose Mode OFF/quiet; verified forge + /status + git + push this session) <<<** — **✅ THE 07-17 WRITE-OUTAGE IS RESOLVED**: gh re-authed as WallyDoodlez (push:true verified by live pushes); #13473 closed on forge; the increment below is historical. Session recoveries: **qa was dead ~33min** (bare-mode harness never respawned it — #13545 class) → PM `boot_remote.py --role qa`, recovered + immediately verified **#13556 PASS → merged (PR #13560: post-merge restore hook, receiving-side guard) → dm delivering**. qa self-caught a pickup mis-claim (pending-test→in-progress; watch-only, verification unaffected). **#13562 (dm token-cost gate) built → pending-test**; skill then picked #13574 (write-outage boot-gate — impl ready) and **#13577 (HIGH: em-dash gate FAIL on main in start.ps1/inject-permissions.ps1, PR #13578 up)** — KEY: the primary clone's dirty copies of those 2 scripts ARE the proven fix (stranded uncommitted by the freeze); PM commented context on #13577; PM reconciles primary clone post-merge. Stranded qa deliverables (QA/TEST-PLAN-11538 + launcher ASCII test) preserved (608c4317b — that test is what exposed #13577). **HITL standing:** #13515 (status-name rec 'blocked') · #13263 (keep open) · pending batch #13561–#13568 · #12527 (greenfield smoke test).
- **Gated/parked work**: #10690 (wiki-link rework, gated on E6+E7) · #10686 (E7 V2 migration smoke, operator-manual, unblocked post-E6) · 4 umbrella PRDs from DS TRD audits (#10836 INSTALLER-ARCH / #10837 HARNESS-ARCH / #10838 VAULT-ARCH / #10839 cross-TRD role→alias rename) — operator-paced post-cutover, #10837/#10839 need DS re-audit before pickup.
- **Older increments (2026-06-15 through 2026-07-17)** graduated to `vault/archives/briefing-active-priorities-2026-06-15-to-07-17.md` (#13563 budget trim).

## Recently Shipped

- Graduated in full (2026-05-19 through 2026-06-21, none still recent) to `vault/archives/shipped-2026-05-19-to-2026-06-21.md`; see also `vault/archives/shipped-pre-2026-05-19.md`. Starts fresh from the next ship (#13563 budget trim).

## Core Architecture

- **Layered roles**: L1 (base) → L2 (role) → L3 (domain) → L4 (project). compose.py assembles.
- **Harness**: Agent lifecycle owned by harness (REST API intent, .harness-state.json). Singleton enforcement, intent state machine.
- **Branching**: Code → main. State → squid-squad. Feature branches per task (#9478).
- **Delivery hierarchy**: TRD → PRD → Stories → Tasks. TRDs at `docs/*-ARCH.md`. Currently in TRD-polish + early-PRD phase.
- **Tracker**: GitHub Issues with structured labels. tracker.py is abstraction layer (non-GitHub backends post-v1).
- **PM boundary**: docs only; worker owns all code + code-consumed data per `feedback_pm_docs_only`.

## Recent Decisions

- **Vault-v2 telemetry storage LOCKED** (operator, 2026-07-18): git-tracked append-only JSONL shards, one per writing clone (`vault/.telemetry/<instance-uuid>-<role>.jsonl`), `merge=union` backstop, values computed at read (dedupe by event id, sum), quiet-cycle compaction. Notes never carry counters. Canonical: `docs/VAULT-ARCH.md` v2 §6.3 (branch `squidsquad/task/10003`, PR #13708); supersedes the 07-12 harness-owned-gitignored-store directive.
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

- Auto-versioning: **v0.45.0 SHIPPED** (#13324, 2026-06-30) + **published to npm** (#13325, 2026-07-02, dist-tag latest). Shipped-Since-Bump counter is DM-owned (reset at the v0.45.0 bump); next bump operator-paced, not auto-fired. Counter currently 74.
- DS re-audit needed on #10837 + #10839 before PM picks them up; bottleneck deferred until post-cutover queue resumes operator pacing.
- **Boot-pull lag (#12526) FIXED + SHIPPED 2026-06-20 00:58** (PR #12993, commit 8a3d45) — clone-sync in launchers (start.ps1/start.sh) switched to no-rebase/merge; the chronic N-behind-origin boot lag is mitigated going forward (takes effect on next clone-sync). Regression risk was already NEUTRALIZED by #12906 (pull-first recompose guard, confirmed-live) — the boot restore-dance stays a backstop. (#12895 umbrella in-progress; Phase 2 #12912 builds the durable deploy-signal model, currently in-progress after a qa regression bounce.)
- **#12442 (DM event-mode auto-route) SHIPPED — manual dm-nudge workaround RETIRED.** dm auto-ships pending-ship items without PM nudges. (Earlier "PM manually nudges dm" constraint no longer applies.)

## Team State

- Active agents (2026-06-19 ~20:48, verified via /status + forge, post-full-restart): **pm** (this clone, EVENT, bootup=True), **dm** (SquidSquad-3, EVENT, bootup=True), **skill** (SquidSquad-2, EVENT, bootup=True — in-progress #12912 Phase-2 + #12801 TUI + 3 more), **qa** (SquidSquad-qa, EVENT, bootup=True — **now event-capable** after the clean reboot onto the #12820 fix). All 4 came up healthy on the supervised relaunch.
- Wake mode: **all 4 EVENT** (:7373). The qa-POLLING era is over — #12820 (qa port-desync) + #12824 (assigned-to 500s) both CLOSED and qa rebooted onto the fix this restart (bootup=True confirms event-mode).
- Current version: **0.45.0** (harness sha **a7c2b6ae** = HEAD, boot **2026-07-17 06:07Z**, uptime fresh; all 4 EVENT). **✅ HARNESS NOW CURRENT** (supersedes the prior 07-11 "stale/44-behind/DORMANT" note): primary clone 0 ahead/0 behind origin; deploy-pull fixes #13456/#13472/#13494 are ACTIVE. **Caveat: launched BARE mode** (`[start] bare mode (#12525)`: harness only, no TUI/auto-lifecycle — #13545); agents currently alive but a full `pwsh .squidsquad/start.ps1` (non-bare) is needed for TUI + auto-reboot. **✅ Stale-blocker note cleared 2026-07-19**: the 07-17 write-freeze (#13570/#13473) is RESOLVED — gh re-authed as WallyDoodlez, both issues CLOSED, forge writes verified live (2026-07-18 session).

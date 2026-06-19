# Working State

- **Task**: none — 2 tasks SHIPPED to pending-test this session (#12820 PR #12883, #12853 PR #12894). Next pickup = **#12800** (deferred to fresh context — see below).
- **Updated**: 2026-06-19 09:58 (skill — event-mode session; 2 shipped, idle)
- **Quiet Cycle Counter**: 0

## NEXT PICKUP — #12800 (HIGH) — deferred to fresh context
**human as a (non-agent) role.** Implementation companion to #12853 (just shipped) + #12799. 8 ACs, HIGH-BLAST-RADIUS (compose role-class resolver + §8.3 routing core) → wants a clean context budget (same standard that correctly deferred #12820 earlier). **LOCKED design doc = the plan: `.squidsquad/pm/planning/HUMAN-AS-ROLE-ASYNC-DESIGN.md`** (TRD of record: AGENT-RUNTIME Terminology/§3/§3.1/§8.3 rev-16/17). ACs: AC1 human alias registers (config.py + tracker role:human + /work/assign target-alias); AC2 compose.py/deploy-all SKIP human aliases (resolver must not map human→agent class, no CLAUDE.md/L4, no error); AC3 §8.3 routing flip (*→pending-human-review|setup target human; human-comment still→pm); AC4 inline status bar self-write `inline` + clear on session end (supersedes #9358); AC5 return-path wake test; AC6 docs reconcile (composed + AGENT-RUNTIME, no dangling refs, #9358 note); AC7 installer-files.txt iff new file (likely none, in-place); AC8 DS-audit (high-blast-radius). Was at status:approved, role:skill.

## #12853 IMPLEMENTATION (this session)
- **AC1+AC2** (SOUL.md): replaced `### Never Block on a Human` with `### Never Stop While Work Is Pending` — general rule (any handoff agent OR human = transition + immediate continue, never stop), stop-vs-idle disambiguation (idle auto-resumes = fine; ending turn to wait = forbidden), only lifecycle ends (exit-42/stop-requested/Monitor death). Human case retained as 3rd para (DRY special case).
- **AC3** (PM L2): responsibility.md +duty bullet (Advertises human-assigned tickets) [inlined → composed]; checkin.md +actionable 'Advertise human-assigned tickets' para [runtime-loaded].
- **AC4**: compose deploy-all rc=0; 'Never Stop While Work Is Pending' in all 4 composed; PM duty in pm composed only. Old rule name gone from all 4.
- **AC5** (CQ HARD GATE): tests/comprehension/12853_spec.json — 6 CQs (CQ1-5 SOUL, CQ6 PM). Executed: 2 fresh sonnet agents answered all correctly from isolated text → result PASS.
- **AC6** (DS prose-drift) DONE: reconciled docs/AGENT-RUNTIME.md §3.1 to general rule; DS audit found 4 (1 error: bad Case C/§8.1 ref; 3 warn: 'special case' contradiction, dangling §3 ref, session-end dup) — ALL applied. Fixed §9→§7.5 mis-ref I introduced. Added AGENT-RUNTIME rev-17 changelog entry. harness-restart.md ×2 + line-24 refs de-stale'd. Sweep: 0 stale 'async-no-pause' in references/ sources.
- **Vault race (resolved)**: 2 qa galaxy notes landed WITHOUT frontmatter → broke test_vault gate. I added frontmatter, but qa fixed their OWN notes concurrently (commit 6739a80ba) — pull stash-pop duplicated frontmatter (malformed). Restored both to qa's committed version (git restore); their fix wins (correct ownership). Not in my PR.
- Final full suite RUNNING (post DS-fixes + vault-fixes). Then: commit-state (composed CLAUDE.md ×8 + vault + working-state → main) + commit-code (sources → feature branch) → PR → pending-test.
- #12820 SHIPPED to pending-test (PR #12883) earlier this session.

## #12820 DONE → pending-test (PR #12883)
Root cause: `harness.py find_free_port` silently binds ephemeral when canonical port (7373) held → a 2nd harness self-writes (1836) + distributes (1849-61) that dead port to clone .harness-port files → permanent polling fallback (qa unreachable in event mode; also explains #10855/#12409 inert/zombie framing). **Fix (minimal, low-risk):**
- `harness.py`: (1) `find_free_port` returns real bound port via getsockname (fixes `--port 0`→literal 0). (2) `_probe_harness_status(port)` — GET /status, True iff harness-shaped JSON. (3) `_resolve_listen_port(explicit)` — explicit --port (incl 0) keeps ephemeral fallback (TEST path); production (no --port) probes /status → LIVE harness=refuse+exit(1) (never bind ephemeral → never poison clones), else claim canonical port (uvicorn 0.41 SO_REUSEADDR handles restart TIME_WAIT reclaim). main() calls it.
- `event_mode_subprocess.py`: real_harness now always passes `--port 0` (explicit ephemeral opt-in) so test harness never hits production refuse path.
- Tests: test_harness.py TestSingletonPortGuard (7) + find_free_port(0). Full suite green: static 4567 passed, integration 53 OK. DS review 3 warnings applied (Win SO_REUSEADDR comment, test TOCTOU, import hygiene).
- **Verifier note**: secondary RCA (what production invocation starts a 2nd harness with SQUIDSQUAD_DIR=qa's REAL clone) still untraced — hardening makes it harmless regardless; not a blocker. Restart path (#12825 exit-42 → wrapper relaunch) verified: old harness fully exits before relaunch, /status probe sees it dead → reclaims 7373.
- Cluster: this fix is keystone for qa/reboot-health bugs #10855/#12409/#11600 (all downstream of the polling-fallback symptom).

## Shipped this session (DONE)
- **#12825** (HIGH) — supervised harness launcher + agent-triggerable harness restart. AC1-AC8. PR **#12860 MERGED**, issue SHIPPED/CLOSED. (qa verified cy345 8/8 ACs.)
- **#12511** (HIGH bug) — test-isolation leak. Fix = autouse `_block_live_harness_egress` guard in tests/conftest.py + regression test. PR **#12867**, issue SHIPPED/CLOSED. (qa verified cy346 with on-the-wire A/B proof.)

## Filed / deduped
- **#12861** (LOW) — installer-files.txt omits shipped shared sub-skills (l4-curation/pr-protocol/tracker-protocol/common/task-pickup). Overlaps **#12821** (no manifest-completeness test); consolidated finding onto #12821, flagged #12861 for PM dedup.

## QA agent — CORRECTION: never inert; healthy in POLLING (#12820 misread)
Initial /status read (bootup_complete=false, stale last_activity) led me to conclude qa was inert + reboot it. WRONG — that's the #12820 polling artifact: qa boots POLLING (dead ephemeral .harness-port) and doesn't heartbeat the event bus, so /status can't see it. Clone ground truth (SquidSquad-qa working-state/current-state) shows qa ALIVE and verifying — it PASSED #12825 (cy345) + #12511 (cy346) in polling. My reboot was an unnecessary disruption (operator's first "I don't think QA is inert" was right).
**RCA root (#12820): harness.py find_free_port (3786-3800) silently binds an ephemeral port when 7373 is taken** → a 2nd harness (run with SQUIDSQUAD_DIR=qa's real clone) self-writes (harness.py:1836) that dead port to qa's clone .harness-port → permanent polling. Posted evidenced RCA on #12820; corrected misdiagnosis on #10855/#12409; #11600 RESOLVED. Vault: [[learning-polling-agent-reads-as-inert-on-status]].
**#12820 fix DESIGN (recorded on issue, deferred):** ephemeral fallback + self-write are LOAD-BEARING for the integration suite (real_harness fixture spawns harness in tmp dir, reads self-written .harness-port to discover port — breaks if disabled). Fix must DISTINGUISH prod-singleton (default 7373, real clones) from test (tmp dir, explicit --port 0). Candidate: on default-port path, if find_free_port falls back to ephemeral (7373 held), refuse-to-start OR skip self-write+distribute — BUT must probe /status (live singleton=refuse vs stale/TIME_WAIT=proceed+SO_REUSEADDR) to NOT break the #12825 exit-42 restart relaunch. Coordinated harness.py + fixture change + full integration-suite verify + regression test. Untraced trigger: what runs a harness w/ SQUIDSQUAD_DIR=qa real clone (not boot_remote/thin_launcher).
Separately noted (#11600 comment): cross-clone .local-config divergence (skill clone lists skill→../SquidSquad-skill, dm→../SquidSquad-2-dm vs running harness skill=SquidSquad-2, dm=SquidSquad-3) — low-impact (only PM-clone's .local-config is consequential), can file if not tracked.

## In-flight / held (unchanged)
- **#12450** S1+S2 done; S3 (WIZARD.md + PM CQ AC) + S4 (L3 placement, PM-gated) pending. Next feature after current burndown.
- **#12801** HELD (false-premise TUI; awaiting PM/operator). **#12800** HIGH approved ungated. **#12837** HIGH open (harness evicted:true/null oldest_id). **#12846** LOW (mine, wizard unguarded read). **#12823** medium (.gitattributes config.md merge=ours).
- **#12824** SHIPPED (closed).

## Queue note
Next approved: #12853 (L1 Soul Never-Block→Never-Stop), #12800 (human as non-agent role), then HIGH open bugs (#12837, #12409, #12397, #11600). Several qa/reboot-health bugs open (#10855/#12409/#11600/#12820) — cluster worth front-loaded planning if picked up.

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)

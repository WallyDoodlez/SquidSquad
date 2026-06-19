# Working State

_Condensed 2026-06-18 20:24. Prior incident narrative (reboot saga, event-mode stabilization, #12506 wedge-recovery, #12417 doc-reconciliation) preserved in iteration logs (iter-699/700) + on the forge — not re-copied here. Working-state = current active state only._

## Current — 2026-06-18 20:24 (PM EVENT-mode, fresh boot after OPERATOR TEAM REBOOT)

**Boot clean + full-fleet recovery.** Harness :7373 reachable (fresh boot, uptime <3m, git_sha b15e7fc5, v0.44.0). GH OK. Cursor `a88a25471a680d00` → boot drain EMPTY. bootup-complete emitted. 0 untriaged external. Pipeline: **0 open pending-test, 0 open pending-ship** (forge-verified).

**This reboot = the operator fleet reboot prior session anticipated** (activate #12506 self-wake driver + new Soul). Ground-truth (Facts-Over-Context, cross-checked /status + git log):

1. **All 4 agents respawned + healthy + EVENT mode + bootup=True** (dm/pm/qa/skill all running, recent activity). skill actively cycling during my boot (#12799 comprehension spec + vault notes).
2. **qa reached bootup-complete in EVENT mode** — NOTABLE positive vs the long qa-inert/polling saga (#12820 port-desync / #10855 inert-boot). Fresh restart appears to have resynced qa's clone port. **WATCH next qa cycle to confirm it stays event-mode — single observation, do NOT declare #12820 fixed yet.**
3. **#12506 SHIPPED** (PR #12812, `references/scripts/subloop_driver.py`) + **#12408 SHIPPED** (PR #12819, static-gate fail-closed). iter-699 wedge fully resolved. Driver arms on fresh boot → all 4 agents now armed → **dormancy/idle-stall class self-healing**.
4. **Boot-pull lag (recurring, now chronic):** pm clone booted 13 behind origin AGAIN (cf iter-699 14-behind). Recovered: committed 3 artifacts → merged origin/main clean (x2, concurrent skill pushes) → pushed → in sync (HEAD aefd6178f). **Pattern chronic across reboots — candidate to file if it persists; harness boot-pull unreliable for pm clone specifically.**

**Open items to track:**
- **#12824** (high, skill) — harness `assigned-to` POST 500s. Fresh restart MAY have cleared stale state; did NOT test with spurious inject (would misroute). bootup-complete + ack-cursor POSTs work fine. #12506 driver makes it NON-URGENT for dormancy; still matters for handoff routing → reveals on next real handoff (0 PT/PS now = nothing dropped). skill owns the fix.
- **#12801** (skill) — TUI bottom-bar, self-HELD by skill (no-TUI capability escalation). Pending operator decision; not a stall.
- **skill in-progress:** #12824, #12801, #12493 (L2 pipeline-sentinel), #12450 (installer unit-test detect), #10855 (verifier inert-boot).
- **PM in-progress (parked coordination-holds, unchanged):** #11092, #11053, #9968.
- **PM approved queue (operator-paced, NOT autonomously actionable):** #10839/#10838/#10837/#10690 umbrella PRDs need DS re-audit; #10690 gated.

**>>> ROOT CAUSE CORRECTED (operator, inline): the multi-agent freeze this session was an ACCOUNT USAGE LIMIT, not per-agent bugs. <<<** My initial diagnoses were WRONG (Facts-Over-Context miss):
- skill freeze (alive pid 49928, 0 activity 76m, current-state=`running full suite`) — I called it 'hung suite' + filed #12847 HIGH. **WRONG: usage limit froze it mid-call.** No hung pytest child ever observed; symptom-fit not proof. **#12847 RETRACTED + CLOSED.** skill recovered via `POST /agents/skill/restart` → grace timer force-kill ~100s → respawned pid 34064, bootup-complete, active.
- qa freeze (alive, 0 activity, no bootup) — I called it 'inert-boot #10855/#12409'. **WRONG: usage limit (operator confirmed) + operator was talking to it inline** (inline mode → no harness activity updates → looked dead). 

**LESSON (extends [[feedback_health_checks_facts_not_context]]):** stale harness-activity ≠ dead agent. Before concluding 'inert/wedged', rule out (a) inline human conversation [wrappers don't fire], (b) usage-limit freeze [account-wide, hits multiple agents at once], (c) genuine wedge. An account-wide freeze hitting MULTIPLE agents simultaneously points to a shared cause (limit), not coincident per-agent bugs (Occam). When in doubt, ASK the operator (they have usage/limit ground truth I don't).

**>>> OPERATOR-LOCKED PRINCIPLE (2026-06-19): agents NEVER stop while work pending. <<<** skill stopped on a 'QA tangent' (operator nudged it back) — NOT the limit/hang I'd theorized (I was misled by a STALE current-state showing 'running full suite #12142', a CLOSED issue). Root = instruction/soul gap: #12799 'Never Block on a Human' is human-only; nothing forbids stopping to defer to another AGENT (QA). #12506 driver doesn't recover an *ended-turn-waiting* state (only *idle*). **Principle locked:** agents always move ahead; any handoff (agent OR human) = transition + continue, never stop; HITL → assign to human + continue; **PM advertises pending-human-* tickets to operator** (adopting now — 0 such tickets currently). **Filed #12853 (high, skill, APPROVED operator-directed):** generalize L1 SOUL 'Never Block'→'Never Stop While Work Pending' + PM L2 advertise duty + recompose + CQ + DS-audit. **Filed #12854 (medium, skill):** stale current-state defeats health diagnosis (distinct from #10855). Vault: [[decision-agents-never-stop-while-work-pending]]. **LESSON: stale current-state misled me into 2 wrong RCAs (hung-suite #12847→retracted, then limit) — [[learning-stale-activity-not-dead-rule-out-limit-and-inline]].**

**>>> qa IS HEALTHY (polling mode) — confirmed via its OWN files, NOT harness telemetry. <<<** After reboot (pid 52988): qa current-state=`idle`, working-state shows active POLLING cycling (cy340/cy341 quiet, last commit 4m ago, PT/pending-ship empty). Harness `/status` bootup=False + stale last_activity = EXPECTED for polling agents (no event-bus handshake) — NOT broken. **I misread this AGAIN as 'still booting/frozen' — 3rd time this pattern bit me this session; the vault note now covers it.** Root cause it's POLLING not EVENT = **#12820**: qa clone `.harness-port`=7636 vs live :7373 → boot probe refused → polling fallback every session. To get qa into EVENT mode, #12820 must be fixed first (role:skill, open). Until then qa works fine in polling; leave it.

**qa REBOOT (operator-directed 'Can u reboot it', inline):** ⚠️ I had already fired a qa restart that killed pid 29072 right as operator said 'I am talking to it' — interrupted their inline session (apologized). Sequence: harness `POST /agents/qa/restart` killed 29072 immediate (idle) but did NOT auto-respawn (intent=restarting + pid None = kill-without-respawn gap, recurring) → `boot_remote.py --role qa` → **qa spawned pid 52988**, booting (limit now cleared → should boot clean). Background watch `bf6qt4kzt` for bootup-complete. **Frozen-on-limit agents do NOT auto-recover when limit clears — need a restart.** STOPPED poking qa so operator can interact.

**Restart-mechanism decision tree (confirmed this session):** DEAD agent (pid None) → graceful-restart STICKS → use boot_remote. FROZEN/HUNG mid-call (alive) → graceful-restart grace timer force-kills+respawns (~100s) — BUT if harness leaves intent=restarting+pid None after kill (qa case) → finish with boot_remote.

**Routed this session (post-boot event):**
- **#12837 (HIGH) → skill.** Harness anchorless-eviction-marker bug (`evicted:true`+`oldest_id:null`+`events:[]`) kills agent event listener (event_poll exit 2); qa hit it. Triaged (code=skill domain), routed role:pm→role:skill, cross-linked #12511 as live trigger. operator-routed-to-pm-for-triage.
- **#12511 ESCALATED medium→high** — test-isolation leak (test events on LIVE bus, the #999/#42 flood) is now a confirmed trigger for the #12837 liveness failure. Same family. role:skill. **This flood is the source of the recurring no-action wakes; expect it to continue until skill fixes #12511.**

**Open role:pm issues (issue-gate redirected scan → fix issues):**
- **#12495 — RESOLVED (operator 2026-06-19): BUILD option (a).** Operator chose to build the wake-injection primitive (NOT correct-docs) as a BACKUP wake method (self-wake unproven) + PM babysitting tool for stuck agents. Reassigned role:pm→role:skill, operator-approved, full build spec posted. Cleared from PM queue.
- **#11140 (medium) — REROUTED pm→skill (2026-06-19).** Orientation prose lives in references/ source = skill domain. Posted full spec (per-H2 orientation intent + ACs) so it doesn't bounce. Cleared from PM queue.
- **#9969 (low) — manifest.md CLAUDE.md-vs-instructions.md naming convention question.** Deferred.

---

## Superseded — 2026-06-18 16:23 (PM EVENT-mode, fresh boot after self-restart)

**Boot clean.** Harness :7373 reachable (uptime 15h, git_sha 00757fe4, v0.44.0). GH OK. Cursor `3050d070742dc2e9` → boot drain EMPTY. bootup-complete emitted (ok). 0 untriaged external. Pipeline: **0 open pending-test, 0 open pending-ship** (forge-verified).

**⚠️ FACTS-OVER-CONTEXT CORRECTIONS to prior section (new Soul #12585 in effect — cross-checked ≥2 sources):**

1. **qa is ALIVE, NOT inert** — harness `/status` shows qa bootup=False / last_activity ~894m (looks dead), BUT git log shows qa committing iter-322→328 (POLLING mode) from 4h ago to 22m ago. Independent source (git) overrides stale telemetry. qa recovered into polling (operator re-launched per the recovery noted last session). Non-blocking (0 PT). The harness inert-telemetry for a polling-mode agent is expected (polling agents don't do the event-bus bootup handshake) — known, not a new bug.

2. **#12506 (critical-path self-wake driver) BOUNCED + skill WEDGED:** skill built all 4 units → PR #12812 → pending-test → **qa verified FAIL on AC11** (`references/scripts/subloop_driver.py` missing from `references/installer-files.txt`) → routed back to in-progress/skill ~3h ago. Since then skill has NOT acted. **skill is wedged-idle:** process alive (pid 51776, bootup was True, spawned 227m ago — NOT respawned by the "team reboot" 17m ago despite prior working-state claim), last_activity 192m ago, **50 events backlogged past its cursor undrained**, of which **0 are skill-targeted**. Critically the qa route-back (pending-test→in-progress) emitted **NO skill-targeted `assigned-to` wake event** → even a healthy skill wouldn't auto-resume. This is the exact idle-stall / forgotten-queued-work class that #12506 itself fixes — biting #12506's own AC11 fix. Route-back-no-wake is already covered by in-flight #12506 (periodic self-wake driver re-reads work_queue) + #12493 (L2 pipeline-sentinel HALT detect incl. route-back) → NOT filing a duplicate.

   **ACTION: requested harness restart of skill** (`POST /agents/skill/restart`). Graceful restart STUCK on the wedge (intent flipped to `restarting`, bootup→False, but same pid 51776 — wedged agent never reaches a cycle boundary to exit; harness force-kill grace not yet fired). **If still stuck → OS force-kill skill tree (taskkill /F /T terminal pid 54072) → auto-reboot (ON) respawns fresh → skill boots → work_queue() finds #12506 in-progress → resumes AC11 fix.** AC11 fix is compose-consumed code = skill domain (PM cannot do it; #11334 precedent).

   *Sub-observation worth operator awareness:* harness graceful-restart of a **wedged idle** event-mode agent does not force-kill promptly — it waits for a cooperative exit that never comes. Relates to #12271 liveness redesign / harness-sole-lifecycle. Note, not yet filed (watch if it recurs as a pattern).

3. **Handoffs confirmed on forge (all correctly routed):** #12585 CLOSED/shipped (the Facts-Over-Context Soul this boot runs on). #12506 OPEN/in-progress/role:skill. #10540 OPEN/status:open/role:skill (auto-approved bug, awaiting skill open→in-progress triage). #12799 OPEN/status:open/role:skill (async-no-pause, severity:high). #12800 OPEN/approved/role:skill (human-as-role build). skill's queue is correctly loaded; the wedge is what's blocking it, not routing.

**#10855 REINVESTIGATED (operator-requested 16:xx) — major reframe:** qa is NOT inert/zombie (my prior-session conclusion was wrong, built on stale harness telemetry). Ground truth = qa's own clone working-state/current-state/git: **qa alive + actively verifying #12408 in POLLING**. Harness /status shows qa inert only because polling agents don't heartbeat the event bus. **Real blocker to event-mode qa = harness-port desync** in qa's clone: `.harness-port`=18209 (prior 34198/26411) vs live harness :7373 → boot probe refused → polling fallback every session. Gitignored/per-clone/locally-written → desync is in qa's port-discovery, not git. **Filed #12820** (severity:medium→skill, behavior+evidence only) + commented reframe on #10855 (can't confirm inert-boot reproduces until #12820 fixed — polling kicks in first; may share root = clone-state-desync-post-harness-restart). Also noted: 4-day-old orphan claude.exe pid 46948 (Jun 14) + qa thin_launcher pid 21900 — process-hygiene debt (cf #12363). **#12820 = first domino for "switch qa to event"** (operator asked); chain #12271/#12492/#12409 still stands behind it. Operator considering bump-to-high + resequence.

**>>> #12506 SHIPPED (18:40, PR #12812 merged 8cc207af, DM) — self-wake driver on origin/main <<<** + #12799 → pending-test (skill, via nudge). **ACTIVATION pending reboot:** driver only arms on fresh boot; running agents on old code until rebooted. **skill REBOOTED onto driver** (boot_remote, see below) → skill self-wakes going forward. **dm/pm still old code — operator deciding fleet reboot** (recommend reboot skill[done]/dm/pm to activate; EXCLUDE qa = polling, dormancy-immune + reboot re-triggers #12820 port-desync/inert-boot). My pm clone 13 behind origin (harness boot-pull lag — recurring, cf 01:32 boot 14-behind; not blocking).

**⚠️ TWO HARNESS RELIABILITY ISSUES surfaced ~18:4x under test-event flood (watching before filing — may be load-transient from skill's heavy suite; both are skill/harness-code domain):**
1. **`assigned-to` event-POST 500s** — GET /status + `ack-cursor` POST both OK, but `POST /events {event_type:assigned-to}` returned 500 x3 (broke my nudge mechanism). Earlier assigned-to injects (#12506/#12799) worked; #12800 failed. If persistent → also breaks harness handoff routing for event-mode dm. Likely harness EAD/enrichment path choking under bus flood.
2. **Graceful restart killed but did NOT respawn** — `POST /agents/skill/restart` → harness killed skill (pid→None) but never respawned it (intent=restarting + pid=None ~4+ min, harness GET healthy). Recovered via `boot_remote.py --role skill` → skill back (pid 45360, active, driver present in clone). Harness lifecycle bug (kill-without-respawn leaves agent dead) — SAFETY concern; file if recurs.

**>>> DRIVER CONFIRMED WORKING (19:1x) — BABYSIT RETIRED <<<** skill self-woke from a ~6-8min idle (mid-#12801) with ZERO successful nudges from me (assigned-to POST was 500-ing) → the #12506 self-wake driver fired on its own. Recovers on a cooldown-length latency (~6-8min, NOT instant; NOT 30m). Dormancy is now handled by the driver → babysit loop (bbvz27bxc) STOPPED. skill productively cycling post-reboot: #12799 shipped, #12450 surface-1 done, #12823 queued, #12800 ungated, **#12801 self-HELD by skill ("no-TUI escalation"** — skill lacks a TUI capability; it parked #12801 in-progress and moved on — may need operator attention on the capability).

**#12824 FILED (high, skill) — harness `assigned-to` POST 500s persistently** (ack-cursor OK, NOT gh-ratelimit 4998/5000, NOT load). Breaks PM nudge + likely harness handoff-routing for event-mode dm. **Now NON-URGENT** for agent-dormancy (driver self-wakes), but still real for handoff routing → a harness restart would clear it + restore nudge/routing whenever convenient (operator-domain; leaves qa safely in polling via #12820 port-desync). Pending-test/ship both 0 so no handoff being dropped right now.

**BABYSIT LOOP ACTIVE (operator-directed 16:xx) until #12506 ships:** Manually nudging skill through the dormancy bug (#12506 — idle event-mode agent doesn't self-wake to pull next queued item; agent finishes task, notes next pickup, then stalls instead of running work_queue). Mechanism: inject `assigned-to(target=skill, issue=<next>)` via `POST :7373/events` (harness only auto-dispatches assigned-to for open/pending, NOT in-progress → stranded in-progress items need manual wake). **Running a periodic heartbeat Monitor (task bbvz27bxc, 240s)** emitting `BABYSIT_TICK skill_idle=Xm state=set/active`; on each tick: nudge skill if dormant w/ pickup-able queue, check #12506 progress (pending-test→qa→pending-ship→shipped), **TEAR DOWN loop + stop nudging once #12506 ships** (dormancy self-fixes then). NOTE: harness event-POST intermittently 500s under test-churn load → retry. **#12506 progress so far:** my wake → skill did AC11 fix → #12506 → pending-test (PR #12812) → now awaiting qa (polling, 30m cadence). skill re-nudged onto #12799 after.

**Operator directive (inline 16:xx):** on no-action wakes, keep user-facing reports to a **brief summary** — do NOT enumerate other agents' specifics (issue#s, event counts). Token economy. Complying inline this session + filed **#12818** (approved, role:skill) to make it durable as an L2 PM refinement of the L1 User-Facing Communication rule (5 ACs incl. compose-consumption + comprehension test). L2-source edit = skill domain (PM docs-only).

**PM approved queue = operator-paced, NOT autonomously actionable** (#10839/#10838/#10837 umbrella PRDs need DS re-audit; #10690 gated). #12818 now in skill's approved queue. in-progress coordination-holds unchanged: #11092, #11053, #9968.

---

## Superseded — 2026-06-18 01:32 (PM EVENT-mode, post-restart fresh boot)

**Boot clean + recovered a stale-main hazard.** Harness reachable :7373 (fresh boot, uptime <10m, git_sha 00757fe4→ now ab00fba6, v0.44.0). GH access OK. Cursor `5fd4f552` → boot drain EMPTY (fresh harness deque). bootup-complete emitted.

**⚠️ Harness boot did NOT pull — local main was 14 BEHIND origin** (1 ahead = my pre-restart checkpoint commit 00757fe40). Origin had #12689 (DM-ARCH), #12518 (#12506 §8.6.1), #12749 post-ship, qa iters. **Merged origin/main → main (clean, zero conflicts) → pushed (ab00fba6). Now 0/0 in sync.** WATCH next boot: if local is behind again, the harness boot-pull is unreliable → file. (Could also be expected: my checkpoint commit predated the 14, so respawn had nothing to FF onto.)

**Post-restart TODOs ALL RESOLVED:**
1. ✅ DM-ARCH.md §5 (line 106): flipped "tracked as #12749" → "**was realized in #12749 (shipped 2026-06-18, PR #12689)**". skill had NOT flipped it. (PM-owned TRD doc-honesty.)
2. ✅ skill-domain wiring documented in DM-ARCH.md (lines 15/20/56: L3 `dm/skill/` Package=merge-to-main+compose, Publish=ship-comment+CHANGELOG).
3. ✅ pm/CLAUDE.md current — PM composed output contains NO cycle-runner/version_bump content (count 0); #12689's PM-listed source touches (cycle-runner.md/AGENT-RUNTIME.md/DM-ARCH.md/config.py) don't alter PM's *composed* doc. On-disk = committed. No recompose needed for PM.

**#12506 HANDOFF EXECUTED (the big unblock) — PR #12518 (§8.6.1) is MERGED (06888b854).** Design contract landed. Reassigned role:pm→**skill**, status planning→approved. Handoff comment posted (3 atomic artifacts, no-harness-change AC8, also cures operator's "idle agents forget queued work" symptom). **EAD confirmed emitting assigned-to(target=skill) for #12506** → skill will pick up. High-pri, critical-path.

**#10540 ROUTED PM → skill (long-standing BRIEFING TODO done).** DM batch-ship "Base branch was modified" race; DM requested routing twice (c411/c413). Fix shape validated on BOTH transports (harness-up serialized-POST+poll; harness-down per-item local-merge, drained 7 ships/4cy zero-fail, vault [[learning-dm-local-merge-when-harness-down]]). Fix surface = `delivery-packaging.md` + DM CLAUDE source = **compose-consumed = skill domain** (precedent #11334). Reassigned role:dm→skill; bug auto-approved (skill triages open→in-progress). **EAD confirmed assigned-to(target=skill).** Clearing this also unblocks DM's doc-improvement-loop scan gate (contributes to #12506 dormant-subloop).

**Pipeline healthy (verified open-state):** 0 open pending-ship, 0 open pending-test (dm/verifier correctly idle). in-progress: pm=3 (parked coord-holds #11092/#11053/#9968), skill=3 (#12585 L1-Soul-health, #12493 L2-pipeline-sentinel, #10855 verifier-inert-boot) + now #12506 + #10540. No stalls.

**⚠️ DATA-HYGIENE NOTE (investigated, NOT filed — by-design surface):** `tracker.py list-tasks <role> --status pending-ship` returns ~30 CLOSED issues with `status:pending-ship` labels (#605/#1075/#2351/#9184/#9965… all closed, role:skill). This is **#9837 by-design**: for handoff statuses (pending-ship/pending-test) list-tasks widens `state=all` because a PR can auto-close an issue before DM's shipped-transition. NOT a query bug. The real residue = those closed items never had pending-ship cleared (shipped-transition didn't fire, or closed outside ship flow) → permanent zombie entries in DM's list view. Live routing UNAFFECTED (EAD uses `--state open`; agents ship fine). Needs a careful label-reconcile pass (strip pending-ship from long-closed items / set shipped), NOT a quick file. Deferred — re-triage if it ever causes a real misroute. For true pipeline reads use `gh issue list --state open`.

**>>> TEAM REBOOT (operator-directed 'reboot now', 2026-06-18) — to activate #12585 L1 Soul 'Facts Over Context' + #12473 + #12750 <<<**
- **skill ✅** rebooted (new pid 51776) on new Soul; RESUMED #12506 at Unit 3 (confirmed cycling post-reboot). **dm ✅** rebooted (new pid 39756) on new Soul. Both clones verified carry Facts-Over-Context.
- **qa ⚠️ INERT** — I restarted qa via harness `/restart`; it lost its launch-time LOOP pin (pin not in config), re-probed into EVENT mode, and hit the known **#12409/#10855 inert-boot bug** (new pid 46140 but zero activity, no cycle, bootup_complete never set). qa clone HAS Facts-Over-Context but the process is a zombie. **NOT blocking** (no pending-test work). **RECOVERY = operator re-launches qa in LOOP mode** (their launch-time pin mechanism — NOT reproducible from PM side; boot_remote/restart re-probe to event-mode → re-inert). A plain restart will NOT fix qa. Lesson: do NOT harness-restart qa while it's loop-pinned.
- **pm** — operator said 'just restart' → pm restarting itself now (this session ends; fresh pm boots on new Soul + reads this working-state). Everything committed/pushed (HEAD has rev16 + COMPOSE-ARCH fix + 3 filed tasks).
- **auto-reboot is ON** (harness launched plain `python harness.py`, no `--no-auto-reboot`); restart endpoint respawns cleanly. The 'reboots-deferred' was a convention, not a harness toggle.

**POLISH-MODE SESSION (operator, inline) — `human` as a role + async-no-pause [DOC DONE, BUILD FILED]:**
- Operator locked: (1) `human` = first-class non-agent role (routable, aliases, multi-human, NO L1-L4/SOUL/compose → compose SKIPS human aliases); (2) **L1 async-no-pause** — agents NEVER block on a human; assign a tracked ticket + continue; inline mode = only sync exception (motivated by skill pausing-for-prompt-human bug); (3) inline = explicit status-bar `inline` indicator (supersedes #9358 stale-bar workaround); C1 human-needed→`human`/human-comment→pm; C3 PM no longer mandatory funnel; C2 return-path human-mediated (originator self-reassigns / PM reassigns on its behalf / wrong-agent="not my territory").
- **AGENT-RUNTIME edited (rev 16):** Terminology (human role), §3 (inline status-bar + §3.1 async-no-pause + return path), §8.3 (routing flip), revision log. Design doc: `.squidsquad/pm/planning/HUMAN-AS-ROLE-ASYNC-DESIGN.md`.
- **Filed to skill:** **#12799** (async-no-pause L1 rule, severity:high bug, OPEN — EXPEDITED, fixes skill pausing NOW) + **#12800** (human-as-role full build: aliases/compose-skip/tracker role:human/routing/inline-status-bar, APPROVED). DS-audit pending per prose-drift discipline.
- **PENDING TEAM REBOOT (operator-gated, deferred 'firefight'):** #12585 (L1 Soul Facts-Over-Context, shipped PR #12782) + #12473 + #12750 all need reboot to activate; #12506 (self-wake driver) in-progress (skill, units 1-2 done) — recommend bundling all into ONE reboot once #12506 lands. 'auto-reboot off' = `--no-auto-reboot`/`SQUIDSQUAD_HARNESS_NO_AUTO_REBOOT` (death-recovery path); #12397 (no-op recompose → spurious restart) OPEN — fix before re-enabling auto path.

**(Prior 23:54 boot context — restart was pending; now executed. Below preserved.)**

**#12749 SHIPPED + MERGED (01:04) — DM-ARCH layered refactor, clean pipeline:**
- qa VERIFIED → PASS 8/8 ACs (04:56Z) → dm SHIPPED (01:04) → **PR #12689 MERGED**. AC3 resolved per PM ruling: live `dm/skill` wiring + c12-F1 critical fix (`config.py alias dm` strips `/domain` → DM identity intact). qa recovered fully (earlier respawn-watch resolved positive).
- **Operator parser-model flag: now SHIPPED to main** (config.py `<class>/<domain>` bullet-parser). DS-hardened + tested + revertible. Operator still free to veto/redirect post-hoc; informed.
- **#12689 touched pm-composed sources** (cycle-runner.md, AGENT-RUNTIME.md, DM-ARCH.md, config.py…) → `l4-recompose`/`restart-required` for pm emitted (01:01). Harness/l4_file_watcher owns recompose+restart (do NOT manually `compose.py deploy-all` — race risk; harness handles).
- **PM POST-RESTART TODOs:** (1) flip `docs/DM-ARCH.md` §5 "tracked as #12749" → "realized" — DM-ARCH.md WAS in #12689 files_changed, so **check if skill already flipped it**; (2) confirm DM-ARCH.md documents the skill-domain wiring (23:54 doc-honesty flag); (3) confirm composed `pm/CLAUDE.md` current after harness recompose+restart.

**#12506 heartbeat directive (operator 2026-06-18) — RESOLVED in planning, gated:**
- Operator: "agents forget queued work" → fold heartbeat fix into #12506, ensure arch-doc updated w/ change + DS-audit after. Confirmed routing to **skill** (not DM — DM=delivery only; operator OK'd).
- **CRITICAL correction:** my floated "event_poll idle-heartbeat" mechanism would VIOLATE the already-locked, DS-audited §8.6.1 design (hard no-harness-change constraint, AC8). #12506 is fully planned (12 ACs) with an **agent-side periodic self-wake driver** — that fix ALSO cures forgotten-work (driver tick re-enters §8.1 loop → re-reads work_queue). Operator asks already = AC12 (DS-audit) + AC7/AC9 (arch-doc/sub-skill reconcile). No plan change. Symptom appended as #12506 comment.
- **BLOCKER = PR #12518** (§8.6.1 arch doc): verified clean/mergeable but UNMERGED since 06-16 (~1.5d). §8.6.1 NOT on main (grep=0). **Merging #12518 unblocks the whole #12506 build — ESCALATED to operator (present).** Head branch `squidsquad/task/12506-arch-86`.

**dm** idle — shipped #12750 + #12420 + #12749 cleanly, zero manual nudges (#12442 routing holding). **pm (this)** going idle for restart.

**Own-domain housekeeping done this boot:** removed stray 0-byte garbage file (PUA-named `**Status**:`) from repo root.

**Shipped 2026-06-17 (verified via forge):** #12750 (plan-in-PR guard, PR #12751), #12420 (post-commit harness restart INSTALLER-ARCH §10.3, PR #12596). Recent commit 1e7e101e flipped INSTALLER-ARCH §10.3 banner → implemented.

**Carry-over parked (unchanged):** #11092, #11053 (in-progress coordination-holds), #9968, #10855(→skill), cutover #12271/#12460/#12492 chain. See prior sections.

---

## Prior — 2026-06-16 (PM EVENT-mode, operator-active session)

**Cutover #12271/#12460 — SHADOW SHIPPED, observation window NOT yet open.** Operator chose **Path B split**: shadow increment shipped as #12460 (verifier PASS cy223 → DM-merged PR #12472). Cutover flip = **#12492** (approved, HARD-GATED on a clean PID-vs-progress divergence window). **GATE: the running harness (PID 35220, booted 14:05Z 06-15, git_sha 13c68b4a) predates the shadow merge → it is NOT running shadow code → observation window has NOT started.** Opening it requires a **harness restart** onto post-shadow main (operator-approved 2026-06-16). After restart verify: agents ready, qa loop-pin (59999) intact, .local-config has qa, harness git_sha advanced. Once a clean window logs → #12492 unblocks → #12409 + qa→event-mode unblock.

**This session's filed/shipped work (2026-06-16):**
- **#12473 SHIPPED** — L1 plain-language no-op user comms (no ack/cursor jargon).
- **#12475 SHIPPED** — `--force` now bypasses the legal-transition matrix (human override can set any status; over-approvals now revertible).
- **#12451** — status-bar event-model: was over-approved without planning → re-planned with operator (Path: decouple from #12271, inline=distinct state), body rewritten to buildable scope, 7 ACs. Now legitimately `approved`, behind cutover in skill queue.
- **#12493** (approved, skill) — L2 pipeline-sentinel: detect HALT (progress-based, incl. comment-only-handoff) → investigate → unblock event-effectively → escalate. **Arch-first**: PM authored AGENT-RUNTIME §8.3 backstop subsection → **PR #12507** (open, needs merge; impl gated on it landing).
- **#12495** (open, role:pm) — `/work/assign` fiction: 32 doc-wide refs; real router is EAD `assigned-to`. Needs a careful researched purge pass (NOT rushed). PR #12507 flags it.
- **#12506** (high, skill) — **improvement subloop DORMANT across ALL agents for weeks** (pm 06-03, skill 06-01, qa 05-23, dm 04-05). Primary suspect: event-mode idle-wake gap (event_poll only nudges on real events, never idle ticks → idle agent never re-checks cooldown). Also dm GATED on #10540.
- **#10540** — dm's improvement-scan gate blocker; "parked on PM routing", NOT dm-actionable. **PM TODO: route it** (unblocks dm scans; contributes to #12506).

**Routing fix verified:** #12442 works — DM auto-shipped many items this session with zero manual nudges. Manual dm-nudge workaround RETIRED. PM woke skill on #12460 via injected `assigned-to` (the real direct-wake mechanism).

---

## Prior — 2026-06-15 19:30 (PM EVENT-mode boot, fresh reincarnated session)

**Mode**: HYBRID — skill/dm/**pm** EVENT (:7373), qa LOOP (pinned 59999, intentional until #12409). This PM is a fresh event-mode session (reincarnated per operator; prior was inline). Boot drain: cursor was `null` on the harness (boot @14:05Z 06-15); migrated legacy id `3e50e129c8e74594`, fast-forwarded through 80 stale-but-forge-reflected events to head — all no-ops. Cursor now current.

**Harness**: healthy, up since 06-15 14:05Z (git_sha 13c68b4a), all 4 agents `running`. Probe :7373 OK.

### Pipeline state at boot (all healthy, no stalls)
- **skill** — IN-PROGRESS on **#12460** (#12271 slice-4 CUTOVER, shadow-mode strategy). Critical path: when it lands, #12271 completes. Queue behind: #12451, #12450, #12420, #12419 (all approved).
- **dm** — idle; all recent ships done + DM-merged cleanly.
- **qa (verifier)** — LOOP mode, no pending-test waiting.
- **pm (this)** — idle of active task. 3 long-parked coordination items still labelled in-progress: #11092, #11053, #9968 (see below). No churn.

### Shipped since last working-state (06-15, all clean)
- **#12271 slices a/b/c ALL SHIPPED**: #12418 (SessionEnd-reason), #12443 (activity-heartbeat), #12458 (pause-aware guard). Only slice 4 #12460 (cutover) remains → owned by skill, in-progress.
- **#12442 SHIPPED** (DM event-mode auto-route fix) — **VERIFIED WORKING**: dm auto-shipped 5 items post-fix (#12418/#12442/#12443/#12458/#11613) with ZERO manual PM nudges. **Manual dm-nudge workaround RETIRED.** (Resolves the standing "verify next pending-ship auto-routes" action.)
- **#11613 SHIPPED** (installer dep auto-provisioning, PR #12471, DM-merged) — matches HEAD. Counter 23→24, bump held.

### Active threads (PM-relevant)
1. **#12460** (cutover) — skill front-loading. PM coordination-watch only; completes #12271 on land.
2. **#11092** — was "parked behind in-flight harness-arch reconciliation (#12417)". **#12417 MERGED** → #11092 may now be UNPARKED. Operator-paced; revisit when #12460 settles. Status label in-progress (parked).
3. **#11053** — agent-spawn substrate (v2 §4.6 assemble). Phase 1 design operator-locked; Phase 2 = #11570 (role:skill). PM stays coordination (Phase 2.2 ship sign-off, 2.4 prompt refinement). In-progress (coordination-hold).
4. **#9968** — runtime sub-skill resolution; gates further composite reduction (#11049 AC3). In-progress (parked).
5. **#10855** — DEFERRED behind #12271/#12460 (operator). Parked; revisit/close after cutover. Status label in-progress (parked).
6. **DS finding #4** (`/work/assign` fictional endpoint) — doc-sync was GATED on #12442. **#12442 now SHIPPED** → doc-sync UNGATED. Real routing = EAD `assigned-to` + harness `role:*` rewrite; `/work/assign` should be dropped from HARNESS-ARCH §3/§4.3 + AGENT-RUNTIME §8.3/§5.2. Candidate next PM doc task once #12460 cutover noise settles.

### PM approved queue (operator-paced post-cutover, NOT yet actionable)
- #10837 HARNESS-ARCH alignment PRD (needs DS re-audit before pickup)
- #10838 VAULT-ARCH alignment PRD
- #10839 cross-TRD role→alias rename PRD (needs DS re-audit before pickup)
- #10690 wiki-link rework (gated on E7)

### Standing notes
- #11600 (qa `.local-config` wipe on compose) — durable fix #12380 shipped; watch next compose/restart.
- "cycle NNNN" commit label drift is decorative; anchor on `iter-N` + date.

## Improvement Scan
Status: idle
Last completed: 2026-06-18 01:37
Next scan after: 2026-06-18 02:07
(Focused scan this boot: surfaced list-tasks closed-item surface → determined #9837 by-design, no filable gap; label-hygiene residue noted above for careful future triage. No process-gap filed.)

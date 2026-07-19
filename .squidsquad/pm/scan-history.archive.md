# Scan History Archive

## Scan — 2026-06-20 03:18 (idle-driver tick, 3rd/burst-cap scan — post-#12912-ship drift hunt)

- **Files scanned**: grep deploy-all / compose.py deploy across references/ (role templates, overlays, commands, docs) — drift check vs the just-shipped #12912 deploy-signal model
- **Findings**: 1 FILED (Tier-2 → #13030, role:skill, low, improvement-scan). #12912 retires agent-manual compose.py deploy-all as the recompose trigger (deploy-signal = sole pull-first path), but PM 'Post-merge recompose' overlay + references/roles/*/instructions.md 'edit source → run compose.py deploy' + dm/skill/instructions.md:27 still direct manual recompose → drift + double-recompose/race risk once the model goes live. GATED on deploy-signal go-live (harness restart) — must NOT land before (current fleet still uses manual model). Scoped to agent-facing manual-trigger instructions only (compose.py command + operator/install tooling stay). No existing tracking issue found (dedup clean).
- **Auto-fixed**: none (Tier-2 cross-role, gated — filed not fixed; references/ is skill domain)
- **Items rejected by human**: (none)
- **Burst note**: 3rd scan of idle period → at_cap, driver cancelled + cron 6c7ee7bc deleted (re-arms on next forge-work re-idle).

## Scan — 2026-06-20 15:47 (idle-driver tick, 1st scan of fresh burst — post-#12896-approval re-idle)

- **Files scanned**: docs/COMPOSE-ARCHITECTURE.md §3.0 (Aliases schema), .squidsquad/config.md ## Aliases, references/scripts/config.py parse_aliases_registry — alias-form doc-vs-reality consistency (prompted by this boot's config.md `dm/skill` revert investigation + the 02:16 scan's unresolved candidate)
- **Findings**: 1 FILED (Tier-2 → #13038, role:pm, low, improvement-scan). §3.0 documents ONLY the canonical 3-column table Aliases form, but live config.md uses the legacy bullet form with packed `<role-class>/<l3-domain>` (`dm: dm/skill`) — supported by config.py (#10385/#12749) but undocumented in the arch doc. Doc-vs-reality TRD drift; cost cycles twice (02:16 scan gave up unconfirmable; this boot's config-revert investigation had to read config.py). Resolution = arch decision: (a) document the legacy bullet form in §3.0, or (b) migrate config.md to the table form. Dedup clean (#10385 closed, no open issue). RESOLVES the 02:16 unconfirmable candidate.
- **Auto-fixed**: none (Tier-2, arch decision — filed not auto-fixed). NOTE for future scans: `dm: dm/skill` is CONFIRMED CORRECT/intentional (L3-variant syntax) — do NOT re-flag as suspicious; the gap is the missing DOC, now tracked in #13038.
- **Items rejected by human**: (none)

## Scan — 2026-06-20 16:47 (idle-driver tick, 2nd scan of burst — installer-readiness, operator-prompted)

- **Files scanned**: docs/INSTALLER-ARCH.md §4.1, references/scripts/wizard.py, start.sh, requirements.txt (fresh-install readiness; prompted by operator "do we have all steps for a new install")
- **Findings**: 1 FILED (Tier-2 → #13041, role:pm, low, improvement-scan). INSTALLER-ARCH §4.1 "Current state (target vs today)" note STALE — 3 claims false vs shipped #11613: (1) wizard.py no longer gh-only (has setup_requirements gather-all + per-platform python3/gh maps); (2) start.sh installs FULL requirements.txt, not 2-of-4; (3) pyyaml already in requirements.txt:16. #11537 pointer imprecise (was the doc-section task, shipped — not the impl). Caused a PM misassessment to operator BEFORE verification → corrected in-conversation. Caught via facts-over-context (read shipped code, not just doc).
- **Auto-fixed**: none (Tier-2 TRD reconcile — needs careful full-state verify of wizard.py consent/re-verify flow; filed not hastily patched).
- **Items rejected by human**: (none)
- **Burst note**: 2nd scan of burst (scan_count 2/3, not at cap) — driver stays armed.

## Scan — 2026-06-20 17:46 (idle-driver tick, 3rd/burst-cap scan — BRIEFING freshness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory staleness check vs this session's forge-verified state + /status)
- **Findings**: BRIEFING stale — top Active-Priorities increment was ~01:00 (pre 2nd-restart); missed today's ship burst (#12912/#12294/#13032/#12409/#12363), #12896 approval + #13035 filing, #12451-S2 unblock, the 2nd restart (sha 398d1c1a→253179a2), the deferred-restart accrual, and the installer-readiness review. Team-State sha + auto-versioning counter (said 0, actually 50) both stale.
- **Auto-fixed**: BRIEFING.md refreshed (PM own-domain, Tier-1) — new 2026-06-20 ~17:20 top increment (2nd-restart + ship burst + #12896-approved/#13035 + #12451-S2 + deferred-restart + installer review + 4 pending operator decisions); Team-State version line → sha 253179a2 boot 14:35; Constraints auto-versioning → 50 (batched v0.45.0, operator-paced).
- **Items rejected by human**: (none)
- **Burst note**: 3rd scan of idle period → at_cap, driver cancelled + cron 707769b1 deleted (re-arms on next forge-work re-idle).

## Scan — 2026-06-21 01:37 (idle-driver tick, 1st/burst scan — freshly-shipped PM sub-skill drift check)

- **Files scanned**: references/sub-skills/roles/pm/pipeline-sentinel.md (just shipped via #12493/#12494), references/sub-skills/roles/pm/improvement-scan.md (cross-ref)
- **Findings**: 1 — residual loop-mode cadence FRAMING in pipeline-sentinel.md header (`### Step 6f` anchor [event-hydrated cycle puts it at Step 4.1], "runs **every cycle**" [event mode = per-cared-event; doesn't run during pure idle — the exact gap #13119 closes], "90 minutes (**3 cycles**)" cadence reasoning). The #12493 rewrite made the halt-detect/investigate/unblock/escalate BODY fully event-aware (EAD, [[comment-handling]], failed-handoff class) — excellent — but left the header framing loop-mode. 90-min WALL-CLOCK threshold itself is correct; only the cadence framing is stale. NOTE: the 2026-06-20 00:02 scan predicted #12493 would sweep this up; it did not — so I did NOT re-defer silently. **NOT separately filed (dedup): routed as an advisory scope-note onto #13119** (skill, open — couples pipeline-sentinel to the idle driver tick → it edits this file's cadence/idle model anyway → natural home for the framing fix). Cannot Tier-1 auto-fix (references/sub-skills/ = skill domain, PM-docs-only boundary).
- **Auto-fixed**: none
- **Items rejected by human**: (none)
- **Context note**: operator signalled imminent harness restart (deferred #13077-reaper activation) once agents idle; pipeline fully drained (0 pending-test/ship/human). Scan kept bounded; chose advisory-on-#13119 over a new orphan task per quality-over-noise + dedup rules.

## Scan — 2026-06-21 12:22 (idle-driver tick, 1st scan of burst — #13158 doc-pairing drift)

- **Files scanned**: docs/HARNESS-ARCH.md §11 Failure Modes table (deploy-pull / deploy-push rows), grep deploy-pull/ff-only/git-pull across docs/*ARCH*.md — drift created by the in-flight #13158 deploy-pull merge fix
- **Findings**: 1 — HARNESS-ARCH §11 rows L510 ('Deploy: git pull non-fast-forward or conflict') AND L512 ('Deploy: git push rejection') document the CURRENT --ff-only behavior (divergence → futile re-pull → deploy-error+respawn, 0 retries). #13158 (pending-test) changes harness deploy-pull to 'git pull --no-rebase' (merge) → benign divergence now MERGES through; both rows become inaccurate on ship. In-lane TRD drift (PM owns HARNESS-ARCH).
- **Auto-fixed**: none (can't pre-edit to unshipped behavior; would describe code that isn't merged). Routed as advisory ON #13158 (couple doc edit to code ship, zero drift window) + tracked in working-state for action on #13158 shipped event. NOT a separate orphan task (dedup/quality — same pattern as #13119).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of burst (scan_count→2/3 after record), driver stays armed.

## Scan — 2026-06-21 13:27 (idle-driver tick, 3rd/burst-cap scan — BRIEFING freshness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory staleness check vs this session's forge-verified ships)
- **Findings**: BRIEFING 12:00 increment said #13158 'filed' — it SHIPPED this session (~15min cycle); #13148/#13147 also shipped; #13030 approved + arch-doc-scoped this session. Recently-Shipped had no 2026-06-21 entry.
- **Auto-fixed**: BRIEFING refreshed (PM own-domain, Tier-1) — 12:00 increment updated (#13158 filed→SHIPPED + HARNESS-ARCH §11 doc-pairing e74fd590a + #13030 approved/scoped/open-question-to-skill); added 2026-06-21 Recently-Shipped entry (#13158/#13148/#13147 + #13030 approval).
- **Items rejected by human**: (none)
- **Burst note**: 3rd scan of idle period → at_cap expected; driver cancels + CronDelete after record-scan.

## Scan — 2026-06-21 18:42 (idle-driver tick, 1st scan of burst — Verbose Mode #13162 post-ship drift check)

- **Files scanned**: references/roles/SOUL.md (L1 postures), references/roles/instructions.md (boot-read selector §234 + no-action-wake §104), docs/AGENT-RUNTIME.md §9.7 (PM-owned TRD), + compose-drift check across all 4 deployed CLAUDE.md (pm/skill/qa/dm). Target chosen: freshest cross-cutting ship (#13162 Verbose Mode, shipped 18:35 this session) = highest drift risk.
- **Findings**: NONE. (1) Three source authoring sites consistent — boot-read selector (`config.py get verbose-mode`, yes→verbose/no→quiet), session-sticky, no-recompose, graceful-default, both postures defined, "all agents + both wake modes" — no contradictions. Wording diffs are explicitly-adaptable example one-liners, not drift. (2) Compose-drift check CLEAN: all 4 deployed CLAUDE.md carry the boot-read selector (1×) + both quiet & verbose postures (2× each) — Verbose Mode correctly deployed fleet-wide.
- **Auto-fixed**: none (clean verification — no drift to fix).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of this idle burst (scan_count→1 after record); driver stays armed.

## Scan — 2026-06-21 19:5x (idle-driver tick, 2nd scan of burst — BRIEFING freshness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory staleness check vs this session's forge-verified events + /status).
- **Findings**: BRIEFING stale — top Active-Priorities increment was ~12:00, missing the entire evening session: #13162 Verbose Mode SHIPPED, the qa verifier wedge + PM recovery, #12271 progress-liveness structuring (Slice A #13179 shipped, cutover #12492 at pending-human-review = operator), #13197 recompose-path-degraded, ships #13066/#13176/#13175, #13185 filed. Recently-Shipped had no evening entry.
- **Auto-fixed**: BRIEFING refreshed (PM own-domain, Tier-1) — new 2026-06-21 ~19:50 top increment (Verbose Mode ship + qa wedge/recovery + #12271 cutover-pending + #13197 + ships + 2 operator advisories); added evening Recently-Shipped bullet (#13162/#13066/#13176/#13175/#13179).
- **Items rejected by human**: (none)
- **Burst note**: 2nd scan of idle burst (scan_count→2 after record); driver stays armed (not at cap).

## Scan — 2026-06-26 ~22:35 local / 03:12Z (idle-driver tick, fresh idle burst — operational gap from skill recovery)

- **Files scanned**: operational — harness restart / auto-reboot path, observed live while recovering the skill agent on operator request this session (no process-file static scan this tick; the live operational finding outranked it).
- **Findings**: TIER-2 (routed as corroboration, not a new file). Spawn-died-before-PID-resolution is a two-sided liveness blind spot: an agent whose initial spawn dies before resolving a claude-PID sits at `status=starting`/`claude_pid=None` forever — (a) PID-liveness poller has no PID to test → never sees "dead" → no auto-reboot; (b) `POST /agents/<role>/restart` sets intent=restarting but the 60s force-kill net has no PID to kill → respawn never fires. Required manual `boot_remote.py`.
- **Dedup**: NOT a new issue — added as point-form corroboration to #12271 (progress-liveness umbrella, pending-human-review). Distinct from the prior alive-PID wedge corroborations there (those are zombie/false-positive); this is the never-resolved-a-PID branch, relevant to shipped Slice A #13179 ("bound the booting escape"). Flagged design data point: progress-liveness needs a never-started/bootup-timeout branch.
- **Auto-fixed**: none (finding belongs to role:skill harness behavior — PM files/corroborates, does not fix code).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of this fresh idle burst (scan_count→1 after record); driver stays armed (not at cap). Live cron 464dc7c3.

## Scan — 2026-06-27 ~04:11Z (idle-driver tick, 2nd scan of burst — BRIEFING freshness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory PM-domain staleness check vs this session's forge-verified events).
- **Findings**: BRIEFING stale — top Active-Priorities increment was 2026-06-22 (5 days), missing this entire session: new fleet restart, operator-requested skill kill+respawn, skill wedge-in-`starting` recovery via boot_remote, #12271 booting-escape corroboration, multiple clean build→verify→ship passes (#13236/#13213/#13212), pipeline now clean, 81-item pending backlog, and the still-live #12271 GO/NO-GO advisory.
- **Auto-fixed**: BRIEFING refreshed (PM own-domain, Tier-1) — added 2026-06-27 top increment (concise; within token budget).
- **Items rejected by human**: (none)
- **Burst note**: 2nd scan of idle burst (scan_count→2 after record); driver stays armed (not at cap). Live cron 464dc7c3.

## Scan — 2026-06-27 ~05:41Z (idle-driver tick, 3rd/final scan of burst — vault decision currency)

- **Files scanned**: .squidsquad/vault/galaxy/decision-pid-primary-liveness.md (vault decision-currency check vs the operator GO on #12271 this session).
- **Findings**: STALE decision — `decision-pid-primary-liveness` was status:active ("PID is primary for liveness"), but operator GO'd #12271 (progress-based liveness → PID demoted to teardown-only) this session. Active decision contradicted the locked direction; would mislead future agents.
- **Auto-fixed**: PM own-domain (Tier-1, vault is PM-maintained institutional memory) — status → superseded-in-progress; added supersession banner (operator GO, cutover #12492 sequencing, wedge-incident drivers); changelog entry; linked to [[learning-graceful-restart-grace-timer-on-wedged-agent]]. Content kept as current-runtime-behavior until #12492 ships (then archive).
- **Items rejected by human**: (none)
- **Burst note**: 3rd/FINAL scan — record-scan returned at_cap:true → driver cancelled (`subloop_driver.py cancel pm`) + cron 464dc7c3 deleted (CronDelete). Burst exhausted; re-arms on next re-idle after forge work.

## Scan — 2026-07-11 09:42 (idle-driver tick, 1st scan of burst — vault decision currency vs shipped #12492)

- **Files scanned**: .squidsquad/vault/galaxy/decision-pid-primary-liveness.md (currency check: last scan 2026-06-27 parked it at superseded-in-progress "archive when #12492 ships"; #12492 has since shipped — verify reconciliation landed).
- **Findings**: NONE. Decision is correctly finalized — status: archived; ARCHIVED/SUPERSEDED banner names #12492 SHIPPED; changelog carries the final "status -> archived" entry (progress-liveness authoritative, PID teardown-only). Content matches shipped runtime reality; no drift. (The working-tree ' M' on this file is a pre-commit state, not a content-drift finding.)
- **Dedup note**: The arch-doc sibling drift (HARNESS-ARCH + AGENT-RUNTIME still frame progress-liveness as 'proposed/not-detected') is ALREADY tracked at #13319 (role:pm, pending) — not refiled.
- **Auto-fixed**: none (clean verification — nothing to fix).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of this idle burst; driver record-scan next. Live cron 2955cb0a.

## Scan — 2026-07-11 ~14:19 local / 18:19Z (idle-driver tick, 3rd/FINAL scan of burst — live operational gap)

- **Files scanned**: references/sub-skills/common/boot-remote-agents.md (PM manual-boot trigger conditions), cross-ref health-check.md — driven by this session's live incident (harness in bare mode, qa+skill dead ~30min, no auto-reboot, manual boot_remote required).
- **Findings**: TIER-2 → filed **#13545** (role:skill, low, improvement-scan). boot-remote-agents lists only "harness down" / "agent stayed dead" as manual-boot triggers; misses the "harness UP + /status responsive but auto-reboot structurally disabled (bare mode #12525)" case. A future PM could see /status respond and wrongly assume auto-reboot works. Sub-skill = compose-consumed → skill lane (precedent #13317).
- **Dedup**: no existing open issue on bare-mode/auto-reboot-disabled (#13473 is the operator coordination hold for THIS restart, not a durable trigger-doc fix; #6787/#3496 unrelated).
- **Auto-fixed**: none (sub-skill is skill-lane, not PM-editable; PM files, does not edit compose-consumed instructions).
- **Items rejected by human**: (none)
- **Burst note**: 3rd/FINAL scan — record-scan at_cap:true → driver cancelled + cron 8bb66e47 deleted. Burst exhausted; re-arms on next re-idle after forge work.

## Scan — 2026-07-11 ~17:2x local (idle-driver tick, 1st scan of fresh burst — BRIEFING staleness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory PM own-domain staleness check vs this session's forge-verified events).
- **Findings**: BRIEFING top increment was 09:31 (morning), missing the entire afternoon: 13:52 respawn, bare-mode harness + dormant #13456/#13472/#13494 fixes + qa/skill manual boot (#13545), primary-clone now-synced, the #13554 SEV data-loss (squash 57b8faa66) + dm recovery + merged fix PR#13559 + #13556 defense-in-depth, my Windows-path-mangle false-alarm + retraction, #13263 reversal (keep-open).
- **Auto-fixed**: BRIEFING refreshed (Tier-1 PM own-domain) — new 2026-07-11 ~14:00-17:20 top increment (concise; SEV + recovery + bare-mode + operator actions).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of fresh re-idled burst (scan_count→1 after record); driver stays armed. Live cron c41f4c94.

## Scan — 2026-07-18 00:43 (idle-driver tick, 2nd scan of burst — post-#13562 drift sweep)

- **Files scanned**: references/sub-skills/common/working-state.md (drift vs shipped #13562 size gate), references/installer-files.txt (post-merge hook registration from #13556), .squidsquad/config.md (Context Threshold consistency).
- **Findings**: TIER-2 → filed **#13579** (role:skill, low, improvement-scan): working-state.md sub-skill says nothing about the #13562 8KB embed cap / truncation marker / oversize warning — agents following it verbatim can still drift into append-only journals and only learn from runtime truncation. CQ specs required (LLM-consumed instruction change).
- **Clean**: installer-files.txt correctly lists references/git-hooks/post-merge (#13556 AC held); config.md Context Pressure Threshold = 75 landed (c2034851d).
- **Auto-fixed**: none.
- **Items rejected by human**: (none)
- **Burst note**: 2nd scan of burst (scan_count→2 after record); driver stays armed. Live cron 4f60462c.

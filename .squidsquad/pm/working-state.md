# Working State

_Condensed 2026-06-21 12:00 (PM EVENT mode, deploy-error-divergence recovery boot). Prior incident narrative in iteration logs + forge._

## Boot summary (this session — 2026-06-21 ~11:53, EVENT mode, RESPAWNED after deploy-error stage=pull)
- GH OK; harness :7373 reachable (EVENT mode). Cursor `dbad80b905411954` → drained **4 events** (dm #13147 ship + 2 comments [skipped, not pm], + the deploy-error). Acked through `15d255aa30dc0cbd`; bootup-complete emitted, bootup=True confirmed on /status.
- **Respawned by deploy-error** (event `15d255aa`, target pm, **stage=pull**, respawn_ok). Boot_time matches.

## >>> DEPLOY-ERROR RECOVERY — DONE THIS BOOT (pm clone) <<<
- **NEW root-cause variant this boot = DIVERGENCE (not dirty-tree).** Tree was CLEAN of modified tracked files (only untracked logs/driver-state/qa-artifacts/1 vault note). Local main was **3 ahead / 1 behind** origin: local = harness-committed pm doc work (d0ba91a2b #12971 + 2 merge commits), origin = dm `109802375` #13147 recompose. **Non-overlapping files.** Harness deploy-pull is FF-only → fatals 'can't be fast-forwarded' → deploy-error.
- **Recovery (verified from facts)**: `git merge origin/main --no-edit` → CLEAN, 0 conflicts (only composed CLAUDE.md from dm side) → 4 ahead/0 behind → `git push` → **0/0 fully synced** (109802375..8256cc0ac). pm clone deploy-path unblocked.
- **Distinct from last boot's dirty-tree variant** (which recovered by *discarding* identical composed artifacts). Symptom-based recovery: clean tree + diverged → MERGE; dirty tree + identical-to-origin composed → DISCARD. See [[learning-deploy-pull-block-divergence-recover-by-merge]] + [[learning-deploy-pull-block-recover-by-discarding-composed-artifacts]].

## NEW BUG FILED THIS BOOT → #13158 (role:skill, medium)
- Harness deploy-signal `git pull` has **no merge strategy** → fatals on any diverged main (harness-committed-unpushed + teammate-pushed, non-overlapping). Recurring, fleet-wide, recurs every deploy-signal until manual reconcile. Behavior+impact+repro filed; RCA is skill's. Analogous to #12526 launcher fix but on the separate deploy-signal pull path. Distinct from #13030 (dirty-tree variant) and #13036 (F3/F4 respawn lock/pid).
- Cross-linked on **#13030** (deploy-path now hit by TWO stage=pull variants: dirty-tree #13030 + divergence #13158).

## ROOT CAUSE TRACKED → #13030 (gate OPEN) + #13158 (new)
- **#13030** (role:skill, status:pending) — retire agent-manual `compose.py deploy-all`. Gate OPEN (deploy-signal model live + harming). Needs operator approval + low→medium reprioritize.
- **ADVERTISE TO OPERATOR**: deploy/recompose path broken fleet-wide by 2 variants (#13030 dirty-tree, #13158 divergence). Pipeline still flows (agents on existing composed CLAUDE.md) but no recompose lands cleanly until fixes ship or per-clone trees reconciled.

## FLEET-HEALTH OBSERVATION (this boot)
- dm/qa/skill all at **intent=deploying** (stale, sibling of #13113 telemetry gap) — BUT may correlate with their OWN deploys failing (same #13158/#13030 class in their clones) → they may be running on **stale composed CLAUDE.md** (e.g. missing #13147 'Treat Impossible as a Hypothesis' L1 trait). Cannot inspect their clones (separate dirs, not pm lane). Systemic fix = #13158 + #13030. All 4 bootup=True + active (skill 74s, dm 374s, qa 38min-idle [correct, no pending-test]).

## Pipeline (forge-verified 11:58)
- **pending-test: 0. pending-ship: 0.** (#13147 shipped this boot.) **role:human / pending-human-* : 0.** untriaged externals: 0. blocked:human-action: #10377 (gated on TRD impl, parked).
- **PM-actionable approved work:** none (only #10690, gated on E7). Clean & flowing.

## PM standing backlog (operator-paced/gated, NOT autonomously actionable)
- **approved (gated):** #10690 (E7). **in-progress (parked coord-holds):** #11092, #11053, #9968, #10837 (/work/assign RETIRE-as-fiction decision OPEN), #10839 (role→alias; code = #13044 pending operator approval).
- **pending intake (operator-paced):** #13044 (pending approval, HIGH blast), #13036 (deploy respawn F3/F4), #13030 (deploy-all cutover — gate open), #13041, #13038, #12508, #12410, #12300, #11400, #10360, #10178, #10023, #10001, #9998, #9996, #9912, #9739, #8997, #20. Plus #10686 (E7 smoke), #12913.

## #10837-9 TRD-Alignment Program (operator-paced)
- #10838 VAULT-ARCH CLOSED. **#10837 HARNESS-ARCH CLOSED this session** (operator "Go") — revision log → v28 (reaper #13077/§11 #13158/§5.1 #12971/work-assign #12495 reconciles current); /work/assign HIGH-2 gap closed by impl (#12495, NOT retire-as-fiction — superseded); /queue gen split → #13173 (low skill); dm §7.4/§7.6 drift flag answered (already fixed fce1f3f2a 03:29, was reading stale v27 banner). #10839 role→alias SCOPED; code Phases 2-4 = #13044 (pending operator approval); #10182 permission-table separately open.

## >>> #13030 APPROVED THIS SESSION (human inline directive ~13:17) <<<
- Human: "go ahead [approve], make sure arch docs are updated." → transitioned pending→approved, priority low→medium. Gate satisfied (deploy-signal live fleet-wide).
- **Lane split**: SKILL = references/ instruction rewrites + dead-event code cleanup; **PM = docs/*-ARCH.md edits** (AGENT-RUNTIME §9.5 catalog-trim table ~L1283 + event_context set ~L1290 + COMPOSE-ARCH §8 audit).
- **⚠️ PM-ACTION ON #13030: do NOT edit AGENT-RUNTIME until skill confirms the OPEN QUESTION** — does deploy-signal drift-detection cover mid-session merges to references/, or is compose-needed still a file-watch-gap fallback? Answer decides retire-vs-scope. Then PM authors the arch-doc edits (cross-pair AGENT-RUNTIME↔COMPOSE-ARCH↔HARNESS-ARCH) coupled to #13030 ship. Verified-from-code: harness.py:576/compose_freshness.py:244 = harness emits deploy-signal, never runs deploy-all locally; compose-needed absent from references/scripts (doc-only).
- **Also pending PM arch-doc edit on #13158 ship**: HARNESS-ARCH §11 rows L510+L512 (divergence-merges-not-errors). Advisory posted on #13158.

## >>> #13162 VERBOSE MODE — FILED + APPROVED THIS SESSION (operator feature) <<<
- Config-gated verbose narration toggle; 5-phase intake done (research→discussion[4 decisions]→planning→approved). Plan: .squidsquad/pm/planning/VERBOSE-MODE-DESIGN.md. Filed role:skill, approved.
- Decisions: boot-read session-sticky · full firehose · all agents · README operator doc · default OFF, this install ON.
## >>> #13030 PM DOC-PAIRING — PARTLY DONE THIS SESSION <<<
- skill resolved the open question (YES, deploy-signal covers mid-session references/ merges; compose-needed DEAD) + gave a precision correction (harness DOES run deploy-all post-merge on its own clone L4103; "never deploy-all locally" is BOOT-only).
- **DONE (commit b3a68babf)**: AGENT-RUNTIME §9.5 (compose-needed retired, table row corrected) + COMPOSE-ARCH §8.2 (compose-needed contrast dropped).
- **PM DOCS LANE NOW COMPLETE (commit b4ade2584)**: skill confirmed boot model (DETECT-ONLY, no local deploy-all; deploy-signal AFTER spawn; harness.py:2258/2275/2207/4383). Edited COMPOSE-ARCH §8.1 text + L1517 mermaid + §9 item-5 PR-author regen checklist (harness owns recompose, #11511). All deploy-signal-model TRD drift reconciled: AGENT-RUNTIME §9.5 + COMPOSE-ARCH §8.1/§8.2/§9-item5.
- **REMAINING = SKILL lane** (their pending work on #13030): references/ agent-instruction rewrites (DS-review + cq) + align `references/sub-skills/common/compose-output-review.md` SOURCE to the §9 item-5 doc edit (PR-author don't-recompose). PM took the doc, skill takes the source — flagged on #13030 to avoid double-edit.

- **PM-ACTION on #13162 pending-test/ship: land AC6 = docs/AGENT-RUNTIME.md** (config + boot-read/sticky + both-mode behavior; cross-pair pass; coupled to ship). DM owns AC7 (README) as delivery packaging.

## >>> P0 INCIDENT RESOLVED THIS SESSION — compose pipeline down (pm clone) <<<
- **Symptom**: burst of **16 compose-failed events** + 1 restart-required to pm (~14:27Z). RCA from facts: pm clone's working tree was in a tree-wide STASH-POP conflict (~20 files UU/DU/UD incl. config.py:891 `<<<<<<< Updated upstream`). config.py SyntaxError → compose.py import fails → compose down.
- **Root cause**: `git_ops.py:253-280` stash+pull+pop ran `git stash` on a CLEAN tree (no-op, no stash created) then popped a PRE-EXISTING ancient stash (newest 2026-05-09 'cycle 36', pre-#6274 dev/qa code) → conflicts everywhere. #13045 `_safe_stash_pop` marker-cleanup didn't cover config.py. 26 ancient stashes had piled up = latent landmine.
- **Recovery (pm clone, verified)**: HEAD==origin/main (0/0) → `git reset --hard HEAD` (restored ~20 files clean, zero loss — stash side obsolete) + `git stash clear` (dropped all 26). config.py+compose.py import OK; tree clean; compose unblocked.
- **Filed #13167 (role:skill, HIGH/P0)** — git_ops pops pre-existing stash on clean tree; FLEET hazard (every clone runs this + may have its own stash pile). Suggested: guard pop on actual-stash-created / `git pull --autostash`; robust marker-strip; don't accumulate stashes. See [[learning-git-ops-clean-tree-stash-pop-recovery]].

## Improvement Scan
Status: idle (queue drained this boot). Driver `.subloop-driver.json` armed, scan_count 1, last_run 2026-06-21T05:41Z. On entering idle: arm driver + confirm live cron via CronList.
(This boot: deploy-error DIVERGENCE recovery [merge origin/main + push → unblock], #13158 filed [harness deploy-pull no merge strategy], #13030 cross-linked, fleet stale-intent/stale-composed observation, pipeline clean & flowing. Entering idle.)

# Working State

_Condensed 2026-06-21 11:31 (PM EVENT mode, deploy-error recovery boot). Prior incident narrative in iteration logs + forge._

## Boot summary (this session — 2026-06-21 ~11:18, EVENT mode, RESPAWNED after deploy-error)
- GH OK; harness :7373 reachable (EVENT mode). Cursor `306ba9042d3a6343` → drained **40 events** (DM shipping the whole backlog + skill activity; only target_alias==pm events cared: #13142/#13139 already-closed, a stale deploy-signal, the deploy-error). Acked through to `d0feef34f0073c28`; bootup-complete emitted.
- **My session was respawned by a deploy-error** (event `d0feef34`, failed_role pm, **stage=pull**, 11:18:11, respawn_ok). Boot_time matches.

## >>> DEPLOY-ERROR RECOVERY — DONE THIS BOOT (pm clone) <<<
- **Root cause**: pm clone had run the still-live "Post-merge recompose" overlay (`compose.py deploy-all` after #13134 merged to local HEAD), leaving all 8 composed CLAUDE.md/.linked.md **uncommitted**. DM independently recomposed + pushed (4fb3e9eb1). Harness deploy-pull then failed ("local changes would be overwritten by merge") and **recurs every deploy-signal** until the dirty tree is cleared.
- **Recovery (verified from facts)**: my working-tree composed files were **byte-identical to origin/main's** (`git diff origin/main` empty) → discarded the 8 generated artifacts via `git checkout` (zero loss). Tree now holds only non-overlapping work; future pulls unblocked. HEAD still c75484604 (6 behind origin dc02f502b) but **no functional staleness** (incoming commits touch only composed CLAUDE.md + skill artifacts, NOT references/scripts/; my running CLAUDE.md context already has new reaper text).
- **My uncommitted PM doc work LEFT in tree (safe, non-blocking, harness will commit)**: docs/AGENT-RUNTIME.md + docs/HARNESS-ARCH.md (#12971 eviction fix — also backstopped on forge: #12971 closed), vault/BRIEFING.md increment, 2 vault learnings, working-state. None overlap incoming → survive the next harness pull.

## ROOT CAUSE TRACKED → #13030 (corroborated, gate now OPEN)
- **#13030** (role:skill, status:pending, was priority:low) — "retire agent-manual compose.py deploy-all recompose instructions." This issue PREDICTED this exact failure. Deploy-signal model is now **LIVE** fleet-wide (evidenced: deploy-signal + deploy-error events), so its gate ("land WITH deploy-signal go-live") is **satisfied** → now actively harming the fleet, not future drift. Commented twice: (1) pm incident facts + gate-open, (2) **fleet blast-radius**: dm/qa/skill ALL show intent=deploying ~1h while working (deploys never completed → likely same dirty-tree block, running on stale CLAUDE.md; cannot confirm/fix their separate clones — not pm's lane).
- **ADVERTISE TO OPERATOR**: #13030 needs approval + re-prioritize (low→medium) — deploy/recompose path broken fleet-wide; pipeline still flows but no recompose lands until cutover or per-clone tree-clear.

## NEW BUG FILED THIS BOOT → #13156 (role:skill, medium)
- harness `POST /events` (`receive_event`, harness.py:3043) throws unhandled JSONDecodeError (500) on unescaped control char in body. **Recurring 47x, live now** (15:28:21Z marker), identical char-81 position = a fixed bad payload re-POSTed in a retry loop. Should fail closed (400). Likely trigger: payload string with raw newline (deploy-error `detail` carries multi-line git output). Behavior+impact+repro filed; RCA is skill's.

## Pipeline (forge-verified 11:26–11:31)
- **pending-test: #13147** (role:skill — qa's lane; fresh handoff, not stalled). **pending-ship: #13136** (DM's lane; fresh handoff, not stalled).
- **role:human / blocked:human-action / pending-human-*: 0.** untriaged externals: 0.
- **PM-actionable approved work:** none (only #10690, gated on E7).
- Agent health: all 4 running + bootup=true + recent activity (dm 11s, skill 5s, qa ~7min, pm live). 3 at stale intent=deploying (telemetry gap, sibling of #13113/#13036 — noted on #13030, not filed thin).

## PM standing backlog (operator-paced/gated, NOT autonomously actionable)
- **approved (gated):** #10690 (E7). **in-progress (parked coord-holds):** #11092, #11053, #9968, #10837 (HARNESS-ARCH align: /work/assign RETIRE-as-fiction decision OPEN), #10839 (role→alias; code = #13044 pending operator approval).
- **operator-paced/gated:** #13044 (pending approval, HIGH blast), #13036 (deploy respawn hardening F3/F4), #13030 (deploy-all cutover — gate now open, see above), #10686 (E7 smoke), #12913, #13041, #13038, #12508, #12410, #12300, #11400, #11000, #10360, #10178, #10023, #10001, #9998, #9996, #9912, #9739, #8997, #20.

## #10837-9 TRD-Alignment Program (operator-paced)
- #10838 VAULT-ARCH CLOSED. #10837 HARNESS-ARCH: doc-side mostly DONE; /work/assign OPEN decision (PM lean: RETIRE-as-fiction) + minor /queue gen remain. #10839 role→alias SCOPED; code Phases 2-4 = #13044 (pending operator approval); resume doc renames WITH code (v1-coexistence).

## Improvement Scan
Status: idle (queue drained this boot). Driver `.subloop-driver.json` armed, scan_count 1, last_run 2026-06-21T05:41Z. On entering idle: arm driver + confirm live cron via CronList.
(This boot: deploy-error recovery on pm clone [discard identical generated composed artifacts → unblock], #13030 corroborated + gate flagged + fleet blast-radius, #13156 filed [harness /events fail-open], pipeline clean & flowing. Entering idle.)

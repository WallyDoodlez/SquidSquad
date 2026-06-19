# Working State

_Condensed 2026-06-19 10:08. Prior incident narrative (reboot saga, #12506 self-wake driver, #12853 async-no-pause/Never-Stop, qa polling/#12820, harness assigned-to 500s) preserved in iteration logs + on the forge — not re-copied here. Working-state = current active state only._

## Current — 2026-06-19 10:08 (PM EVENT-mode, fresh boot)

**Boot clean after catching + reverting a composed-output REGRESSION.** Harness :7373 reachable (uptime 13h40m, git_sha b15e7fc5, v0.44.0). GH OK. Cursor `e8a9c17bc40d3c34` → boot drain EMPTY. bootup-complete emitted. 0 untriaged externals.

**>>> CAUGHT: stale-source recompose would have un-shipped #12853 fleet-wide. <<<** pm clone booted **3 behind origin** (chronic boot-pull lag) AND all 8 composed `CLAUDE.md`/`.linked.md` sat dirty — reverted from shipped #12853 SOUL (`Never Stop While Work Is Pending`) back to pre-#12853 (`Never Block on a Human`). Post-cycle wrapper would have committed+pushed the regression. Recovery: `git restore` 8 files → merged origin/main (FF clean, brought #12853 source) → verified composed outputs now correct in all 4 agents (new SOUL present, old gone, advertise-line present). **Filed #12895 (high, skill)** + cross-linked #12519 (same family: tracked compose output rewritten per-clone). Vault: [[learning-stale-source-recompose-reverts-shipped-on-behind-clone]] (mirror of [[learning-recompose-and-config-carry-across-checkout]]).

**NB: I likely booted on the OLD composed SOUL** (harness recomposed to stale BEFORE spawning me → old content injected). Now operating under the NEW principle (Never Stop While Work Is Pending) from source/git.

**Pipeline (forge-verified, --state open):**
- **0 open pending-test.**
- **#12853 pending-ship → DM.** qa verified PASS 6/6 (cy362), PR #12894 merged. DM alive + active (last_activity 0.3m, Bash). Fresh, NOT a stall — DM owns final delivery (CHANGELOG/version/close). No nudge (well within 90m sentinel).
- **0 untriaged externals.**

**Watch items:**
- **#12895 (high, skill, NEW)** — stale-source recompose reverts shipped composed CLAUDE.md on behind clone. Boot-pull-before-recompose ordering. Until fixed, the boot `git status` + restore + merge dance is load-bearing EVERY pm boot.
- **Boot-pull lag chronic on pm clone** — N-behind every boot (this boot 3; prior 13/14). Now ESCALATED from friction to active regression (#12895). Recover manually each boot.
- **#12824 (high, skill)** — harness `assigned-to` POST 500s. Breaks PM nudge + handoff routing for event-mode dm. Non-urgent for dormancy (#12506 driver self-wakes); matters on real handoffs. 0 PT/1 PS-to-DM now (DM active, so not dropped).
- **#12820 (medium, skill)** — qa clone `.harness-port` desync → qa runs POLLING (works fine; verified #12853). First domino for qa→event-mode.

**skill in-progress:** #12800 (human-as-role), #12493 (L2 pipeline-sentinel), #12450 (installer unit-test detect), #10855 (verifier inert-boot).

**PM in-progress (parked coordination-holds, unchanged):** #11092, #11053, #9968.

**PM approved queue (operator-paced, NOT autonomously actionable):** #10839/#10838/#10837 umbrella PRDs need DS re-audit; #10690 gated on E6+E7.

**PM backlog (pending/deferred, no action):** #12508, #12410, #12300, #11400, #11000, #10360, #10178, #10023, #10001, #9998, #9996, #9969, #9912, #9739, #8997, #20. Operator-paced.

## Improvement Scan
Status: idle
Last completed: 2026-06-18 01:37
Next scan after: (idle driver armed this boot)
(This boot was a productive cycle — regression catch + #12895 filed + vault note. No improvement scan needed.)

# Working State

_Condensed 2026-06-19 10:08. Prior incident narrative (reboot saga, #12506 self-wake driver, #12853 async-no-pause/Never-Stop, qa polling/#12820, harness assigned-to 500s) preserved in iteration logs + on the forge — not re-copied here. Working-state = current active state only._

## >>> FULL HARNESS RESTART TRIGGERED 2026-06-19 ~20:02 (operator-approved) — POST-RESTART VERIFY THIS FIRST <<<

**Why:** ALL 4 agents booted before 22:15 UTC = running the OLD SOUL; the shipped "Never Stop While Work Is Pending" (#12853) + Phase-1 pull-first guard (#12906, harness.py) were NOT active in any live session. skill STOPPED on #12912 (Phase 2) under the old rule, self-wake driver unarmed → wouldn't resume. Operator approved a full `POST /restart` to activate both fleet-wide + unstick skill.

**POST-RESTART VERIFICATION (respawned PM — do from facts, ≥2 sources):**
1. `GET /status` — all 4 aliases `status:running` + `bootup_complete:true` + EVENT mode (not polling). qa may still go polling if #12820 fix not effective — check.
2. Composed CLAUDE.md has "Never Stop While Work Is Pending" in all 4 (grep) — confirm new SOUL live. (Was already in files at 22:15; restart loads it into sessions.)
3. **Phase-1 (#12906) active:** the boot recompose this restart should be PULL-FIRST (harness.py loaded) → composed outputs NOT reverted. **Run the #12895 boot regression check (git status + restore-if-reverted + merge) — Phase 1 should prevent it, but verify.**
4. skill RESUMED #12912 (Phase 2, in-progress) + #12801 (TUI, in-progress, S1.1 done / S1.2+ remaining) from working-state — should NOT re-stop now (new SOUL).
5. Self-wake drivers armed on all (`.subloop-driver.json` present per clone after first idle).
6. If all hold → note "restart succeeded, new SOUL + Phase 1 live." If agents don't come back → harness wasn't supervised → file to human alias.

**RESTART MECHANISM NOTE (2026-06-19 20:0x):** `POST /restart` returned **404** — running harness (sha b15e7fc5) predates the endpoint. Harness was running under **start-harness.bat (one-shot, NOT supervised)** PID 51416 → no self-serve restart possible. Operator-relaunched manually. **Recommended they relaunch via `restart-harness.bat` (supervised)** so the NEW harness has `/restart` + Phase 1 #12906 (harness.py) + future restarts are self-serviceable. If this fresh boot is under restart-harness.bat, self-serve `POST /restart` works going forward.

---

## Current — 2026-06-19 10:08 (PM EVENT-mode, fresh boot)

**Boot clean after catching + reverting a composed-output REGRESSION.** Harness :7373 reachable (uptime 13h40m, git_sha b15e7fc5, v0.44.0). GH OK. Cursor `e8a9c17bc40d3c34` → boot drain EMPTY. bootup-complete emitted. 0 untriaged externals.

**>>> CAUGHT: stale-source recompose would have un-shipped #12853 fleet-wide. <<<** pm clone booted **3 behind origin** (chronic boot-pull lag) AND all 8 composed `CLAUDE.md`/`.linked.md` sat dirty — reverted from shipped #12853 SOUL (`Never Stop While Work Is Pending`) back to pre-#12853 (`Never Block on a Human`). Post-cycle wrapper would have committed+pushed the regression. Recovery: `git restore` 8 files → merged origin/main (FF clean, brought #12853 source) → verified composed outputs now correct in all 4 agents (new SOUL present, old gone, advertise-line present). **Filed #12895 (high, skill)** + cross-linked #12519 (same family: tracked compose output rewritten per-clone). Vault: [[learning-stale-source-recompose-reverts-shipped-on-behind-clone]] (mirror of [[learning-recompose-and-config-carry-across-checkout]]).

**NB: I likely booted on the OLD composed SOUL** (harness recomposed to stale BEFORE spawning me → old content injected). Now operating under the NEW principle (Never Stop While Work Is Pending) from source/git.

**Pipeline (forge-verified, updated ~11:15 / 14:1x UTC):**
- **#12853 SHIPPED** (DM, was pending-ship → shipped this session). The new SOUL I operate under.
- **#12800 SHIPPED** (DM, ~14:13 UTC) — human-as-role infra now LIVE (pending-human-* routing backs my advertise-duty). PR #12902 source-only.
- **#12800 PR #12902 merge → l4-recompose/restart-required(target=pm)** fired ~14:10 UTC (8m into my session). **My intent stayed `running` (no flip)** — did NOT self-quit (stale/late-delivery event + #12397 no-op-restart-required known). Clone 0/0 in sync → a recompose now would be correct (no #12895 risk). Harness owns recompose+restart; awaiting a real intent flip if one comes. **WATCH: restart-required-without-intent-flip — possible #12397 spurious OR a restart-gap.**
- **#12895 (recompose regression) — operator APPROVED the deploy-signal approach; now in-progress umbrella, phased:**
  - **Phase 1 #12906 SHIPPED** (pull-first recompose guard, harness.py — **activates on next harness restart**).
  - **Design doc-first DONE**: DEPLOY-SIGNAL-DESIGN-12895.md v2 (adversarial-review-folded) + TRDs merged (HARNESS-ARCH §7.1/7.3/7.4/7.5/7.6/10/11 + AGENT-RUNTIME §5.2/7.8/8.1/8.2/8.6/9.2). PM review caught+fixed 2 issues in the drafted edits (§7.x renumbering drift; cursor-advance infinite-loop gap).
  - **Phase 2 #12912 FILED** (approved, role:skill, 12 ACs) — durable deploy-signal model. Auto-dispatched to skill. #12895 closes when #12912 ships.
  - Bonus: #12912 also resolves #12397 (spurious restart on no-op recompose). #12519 (settings.json) fold = AC11.
- **0 untriaged externals.**

**RESOLVED this session (were watch items, now CLOSED):** #12824 (assigned-to 500s), #12820 (qa port-desync), #12506, #12442, #11394, #12408, #12585. #9969 closed (decision-recorded). BRIEFING.md refreshed (improvement scan).

**Watch items (still live):**
- **#12895 (high, skill, pending-human-review)** — stale-source recompose reverts shipped composed CLAUDE.md on behind clone. The boot `git status` + restore + merge dance is load-bearing EVERY pm boot until fixed.
- **Boot-pull lag chronic on pm clone** (#12526) — 3-behind this boot. Enabling precondition for #12895.
- **#10540 (OPEN, skill)** — DM batch-ship "base branch modified" race. Still open.
- **qa** — POLLING + alive (pid 55668, bootup=False is expected for polling). #12820 closed but qa not yet rebooted onto fix; verify close-reason before declaring qa event-capable.

**skill in-progress:** #12801 (TUI bottom-bar, actively building Story 1), #12895 (pending-human-review), #12493 (L2 pipeline-sentinel), #12450 (installer unit-test detect), #10855 (verifier inert-boot, blocked-noted on now-closed #12820 — recheck).

**PM in-progress (parked coordination-holds, unchanged):** #11092, #11053, #9968.

**PM approved queue (operator-paced, NOT autonomously actionable):** #10839/#10838/#10837 umbrella PRDs need DS re-audit; #10690 gated on E6+E7.

**PM backlog (pending/deferred, no action):** #12508, #12410, #12300, #11400, #11000, #10360, #10178, #10023, #10001, #9998, #9996, #9969, #9912, #9739, #8997, #20. Operator-paced.

## Improvement Scan
Status: idle
Last completed: 2026-06-18 01:37
Next scan after: (idle driver armed this boot)
(This boot was a productive cycle — regression catch + #12895 filed + vault note. No improvement scan needed.)

# Working State

_Condensed 2026-06-19 10:08. Prior incident narrative (reboot saga, #12506 self-wake driver, #12853 async-no-pause/Never-Stop, qa polling/#12820, harness assigned-to 500s) preserved in iteration logs + on the forge — not re-copied here. Working-state = current active state only._

## Current — 2026-06-19 10:08 (PM EVENT-mode, fresh boot)

**Boot clean after catching + reverting a composed-output REGRESSION.** Harness :7373 reachable (uptime 13h40m, git_sha b15e7fc5, v0.44.0). GH OK. Cursor `e8a9c17bc40d3c34` → boot drain EMPTY. bootup-complete emitted. 0 untriaged externals.

**>>> CAUGHT: stale-source recompose would have un-shipped #12853 fleet-wide. <<<** pm clone booted **3 behind origin** (chronic boot-pull lag) AND all 8 composed `CLAUDE.md`/`.linked.md` sat dirty — reverted from shipped #12853 SOUL (`Never Stop While Work Is Pending`) back to pre-#12853 (`Never Block on a Human`). Post-cycle wrapper would have committed+pushed the regression. Recovery: `git restore` 8 files → merged origin/main (FF clean, brought #12853 source) → verified composed outputs now correct in all 4 agents (new SOUL present, old gone, advertise-line present). **Filed #12895 (high, skill)** + cross-linked #12519 (same family: tracked compose output rewritten per-clone). Vault: [[learning-stale-source-recompose-reverts-shipped-on-behind-clone]] (mirror of [[learning-recompose-and-config-carry-across-checkout]]).

**NB: I likely booted on the OLD composed SOUL** (harness recomposed to stale BEFORE spawning me → old content injected). Now operating under the NEW principle (Never Stop While Work Is Pending) from source/git.

**Pipeline (forge-verified, updated ~11:15 / 14:1x UTC):**
- **#12853 SHIPPED** (DM, was pending-ship → shipped this session). The new SOUL I operate under.
- **#12800 SHIPPED** (DM, ~14:13 UTC) — human-as-role infra now LIVE (pending-human-* routing backs my advertise-duty). PR #12902 source-only.
- **#12800 PR #12902 merge → l4-recompose/restart-required(target=pm)** fired ~14:10 UTC (8m into my session). **My intent stayed `running` (no flip)** — did NOT self-quit (stale/late-delivery event + #12397 no-op-restart-required known). Clone 0/0 in sync → a recompose now would be correct (no #12895 risk). Harness owns recompose+restart; awaiting a real intent flip if one comes. **WATCH: restart-required-without-intent-flip — possible #12397 spurious OR a restart-gap.**
- **#12895 → pending-human-review (ADVERTISED to operator).** skill RCA done; 3 options (C interim / A untrack / C-permanent+#12526 durable). PM rec on ticket: land C now, lean C+#12526 over A (preserves git-as-audit-trail). #12519 folded in.
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

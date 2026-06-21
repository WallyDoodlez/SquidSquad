# #12912 — Phase 2 of #12895: deploy-signal recompose model — DECOMPOSITION

**Status:** claimed (in-progress), decomposed. Implementation = multi-Story, fresh-context.
**Authoritative spec:** `.squidsquad/pm/planning/DEPLOY-SIGNAL-DESIGN-12895.md` (v2) + TRDs (already merged, doc-first): `docs/HARNESS-ARCH.md` §7.1/7.3/7.4/7.5/7.6/10/11, `docs/AGENT-RUNTIME.md` §5.2/7.8/8.1/8.2/8.6/9.2. **Implement to match the TRDs; route spec drift back to PM — never let code+TRD drift.**
**Role boundary:** harness code + agent-instruction sources + tests are MINE. `docs/*-ARCH.md` TRDs are PM-owned and ALREADY updated — I do NOT edit them; if implementation reveals a needed spec change I file it to PM.

## Model (10-bullet summary)
Drift detected → harness emits `deploy-signal` (assigned-to plumbing, `event_context="deploy-signal"`) to ONLY the affected alias(es) → agent finishes current atomic unit at a between-task ON-MAIN boundary, emits `ack-stop(result="deploy-halted")`, halts (no work pickup, no subloop), does NOT ack-cursor the signal → harness sets `intent=deploying` + `reboot_blocked_until` BEFORE halt, then ensure-main→pull→`compose.py deploy <alias>`→commit→push→advance agent cursor past the signal→respawn, SEQUENTIAL per clone → boot no longer runs `deploy-all` (drift→emit signal instead); agent boot reads committed CLAUDE.md, no recompose → loop/polling agents ignore the signal (pick up new CLAUDE.md at next cycle_pre pull) → failure modes (pull conflict/compose error/push reject) respawn on existing CLAUDE.md + file `deploy-error` to pm + do NOT advance checksum.

## Story decomposition (dependency-ordered)
- **S1 — deploy-signal catalog + agent halt branch** (AC1/AC2/AC3). Files: `references/sub-skills/common-events/event-mode-contract.md` Case E (~L92-95) add `event_type=="deploy-signal"` branch; AGENT-RUNTIME §5.2 already specs it (verify). Agent-instruction + needs comprehension/CQ test. **BLOCKED on D1+D3.**
- **S2 — intent-sequencing + reboot_blocked_until harness wiring** (AC9, respawn-suppress). harness.py: add `INTENT_DEPLOYING` const; set intent BEFORE signal emit; `ack-stop` handler (~L2922) add `elif result=="deploy-halted"`; health-poll must not read deploy-halt PID-death as crash. Deterministic code+tests. **Partially D3.**
- **S3 — deploy-signal emit in `_reboot_affected_agents`** (AC4/AC5). harness.py L3809-3866: replace `intent=INTENT_RESTARTING` block with per-alias `_emit_event("assigned-to","harness",payload={target_alias,event_context:"deploy-signal",...})`. Existing post-compose `git diff HEAD` alias-scope (L3834-3849) already gives affected-only. Depends on S2.
- **S4 — per-clone harness deploy sequence on `deploy-halted`** (AC8 sequencing). harness.py ack-stop branch: bg thread ensure_main_and_pull→`compose.py deploy <alias>`→commit→push→restart, sequential across aliases; failure-mode recovery per §11. Depends S2+S3. **BLOCKED on D5 ("A-is-done" signal = new machinery).**
- **S5 — boot-time compose retirement** (AC5 boot half / AC10). harness.py boot L1986-2028: replace `compose_freshness.check_and_repair`→`deploy-all` with detect-drift→emit deploy-signals; agent boot reads committed CLAUDE.md (AGENT-RUNTIME §8.2). Depends S4. **D4 (compose_freshness refactor — my decision).**
- **S6 — AC10 manifest/consumption + AC11 settings.json finding + AC12 DS-audit + AC7 loop-mode + AC6 failure modes tests.** installer-files.txt if files added; DS-audit impl vs TRDs; loop-mode no-consume test. End-stage.

## Findings (resolved this planning pass)
- **AC11 (#12519):** `compose.py deploy-all` writes `.claude/settings.json` (hook entries, compose.py ~L2261-2275) but per-alias `deploy <alias>` (deploy_alias_v2) does NOT. So the deploy-signal per-clone path won't touch settings.json → **#12519 stays a SEPARATE workstream** (installer-managed), consistent with design §3 decision 6. State explicitly in the #12909... (in #12912 delivery).
- **AC-bonus (#12397):** Phase 2 resolves the `_reboot_affected_agents`→direct-restart spurious-restart path (emit only on actual post-compose alias diff). l4_file_watcher restart path already gated on compose ok. **#12397 should close with S3.**

## OPEN QUESTIONS — resolve against TRDs at story-time; route genuine spec gaps to PM
- **D1 (S1 blocker):** exact "between-task on-main boundary" rule for a worker on a feature branch — agent runs `git branch --show-current` to gate the halt? Or harness signals "between-tasks+on-main" context? Check AGENT-RUNTIME §8.1; if unspecified → PM.
- **D2 (my lane):** per-alias `deploy <alias>` skips settings.json — decide whether S4 also re-ensures hooks. (Likely no — see AC11.)
- **D3 (S1/S2):** ack-stop handler checks `result=="stop-confirmed"` (harness.py L2941) but AGENT-RUNTIME §5.2 enum says `checkpointed|aborted|drained`. Reconcile which is canonical before adding `deploy-halted` (factual — read code).
- **D4 (my lane):** `compose_freshness.check_and_repair` needs a detect-only mode (param vs split vs inline) for S5.
- **D5 (S4 blocker):** "A is done before B starts" needs a wait-until-respawn-complete signal (bootup-complete? intent==RUNNING? timeout?) — NEW harness machinery; confirm against HARNESS-ARCH §7.6 / route to PM if unspecified.
- **D6:** confirm post-compose `git diff HEAD` alias-scope is the intended "only-emit-on-actual-drift" mechanism; adapt to post-pull-compose ordering in S4.

## Execution note
6 Stories, 12 ACs, highest-blast-radius (core lifecycle the whole fleet runs on). Each Story: own unit tests; agent-instruction stories need comprehension/CQ; AC12 mandates DS-audit vs the merged TRDs. Phase-1 guard (#12906) is a SUBSET and STAYS (design §note). Start S1 after D1/D3 confirmed from TRDs.

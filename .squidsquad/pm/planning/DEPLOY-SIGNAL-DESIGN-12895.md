# Deploy-Signal Recompose Design (#12895)

**Status**: DESIGN v2 (doc-first, adversarial-review-folded 2026-06-19) — operator-approved approach; pending operator scope-confirm (see §0) before arch-doc integration + Phase 2 filing to skill.
**Owner**: pm (design + TRD updates) → skill (implementation).
**Supersedes**: skill's A/B/C options on #12895.
**Revision**: v2 folds a grounded cross-doc review against HARNESS-ARCH.md + AGENT-RUNTIME.md (§§A–D below).

---

## 0. Scope note (NEW in v2 — needs operator awareness)

The review found this approach is **more new machinery than "minimal"**. It is still the right call (it preserves the git audit trail that Option A would cost us), but it is not a trivial reuse of existing lifecycle. Genuinely-new pieces:
- The harness does **not git-pull today** and has **no precedent for running git ops on an agent's clone** — Phase 2 has the harness do `checkout main + pull + compose + commit + push` *per affected agent clone*. New operational surface (incl. new failure modes — §D.4).
- There is **no "pause before respawn to do work" step** in the current intent state machine — the harness today observes PID death and respawns within one health-poll tick. Phase 2 must intercept that. (Viable via the existing `reboot_blocked_until` field — §B.3.)
- The **deploy-signal event type does not exist** in the signal catalog and must be defined (§D.1).

This doesn't change the decision, but the operator should confirm the larger scope before PM edits the TRDs + files Phase 2.

---

## 1. Problem & root cause

Composed outputs (`.squidsquad/<role>/CLAUDE.md` + `.linked.md`) are **git-tracked** and committed (eager-deploy). When a clone is **behind origin** (#12526), a recompose runs against **stale source** and regenerates the outputs as a **silent revert** of shipped content; if committed it un-ships fleet-wide. Seen 3× on 2026-06-19 (PM boot, skill clone 21-behind, a revert reaching `main` during #12800 before DM repaired it via a023a658e). **Root = stale source at recompose time.** Two conditions, remove either to kill it: (1) outputs tracked+committed, (2) recompose from not-yet-pulled source.

## 2. Locked approach (operator)

Keep compose **at the harness** (no untrack → preserves git audit trail). Make it **pull-first** + **non-interrupting**.

### Phase 1 — pull-first guard (immediate; filed #12906, in-progress at skill)
The harness recompose path **ensures-on-main + pulls origin/main before composing**. Strict subset of the durable design. Eliminates condition 2 on the existing recompose path immediately.

### Phase 2 — deploy-signal, non-interrupting (durable)
- **Trigger:** when DM ships a change touching composed-source (`references/...`), the harness emits a **deploy signal** to the affected agent(s) only (scope via the existing file-watcher change-detection).
- **Agent:** honors it at the **next `ack-cursor` boundary** (per-event seam — confirmed agent-driven per AGENT-RUNTIME §8.1/§5.1). Finishes its current atomic unit, emits a **`deploy-halted` ack**, halts (no improvement loop, no next event), hands off. Remaining queued events drain after restart — nothing lost.
- **Harness:** on the deploy-halt: **ensure-main → pull → recompose → commit → push → restart** the affected clone.

### Key properties (corrected in v2)
- **Pull-first** → recompose from current source → condition 2 gone.
- **Sole recompose path** → REQUIRES retiring the boot-time compose (HARNESS-ARCH §10 step 1b) — see §B.1. Once retired, boot just reads the committed (correct) output.
- **Composed outputs stay tracked** → git audit trail preserved (the reason we chose this over Option A).
- **Self-healing** → a stale output on main is overwritten by the next pull-first deploy.
- ~~Minimal new machinery~~ → **CORRECTED**: adds real harness machinery (per-clone git ops, respawn interception, new signal type). See §0.

## 3. Resolved design decisions (was "open points"; resolved via review §B)

1. **Boot path** — Retire HARNESS-ARCH §10 step 1b (boot-time `compose.py deploy-all`). `last_compose_checksum` (§7.5) is repurposed to **drift detection only**: on boot, if it diverges from current source, the harness **emits a deploy signal** to affected agents rather than composing locally. First-ever install compose stays with the installer. Invariant: *a committed `CLAUDE.md` on main is always the product of a pull-first deploy.*
2. **Polling agents (qa)** — **No new mechanism.** Loop-mode `cycle_pre.py` already git-pulls every cycle; `CLAUDE.md` is read at session start (AGENT-RUNTIME §8.2), so an updated composed output (committed by a prior event-mode deploy) takes effect at the loop agent's next session start. Document the invariant in AGENT-RUNTIME §7/§9. (The bus-delivered deploy signal is simply never consumed by a loop agent — see §D.3 for the stale-signal handling when it later switches to event mode.)
3. **Event arrives mid-deploy** — Use the existing `reboot_blocked_until` field (HARNESS-ARCH §7.3): set it on receipt of `deploy-halted` to suppress premature auto-respawn during pull/compose/commit; clear it on completion. Nudges during the window queue in the deque and are delivered after `status=ready` (existing held-events behavior, HARNESS-ARCH §7.2).
4. **Status reporting** — Extend `ack-stop` with a new `result: "deploy-halted"` value (AGENT-RUNTIME §5.2), so the harness distinguishes a deploy-halt from a crash. (Sequencing: harness must pre-set the intent before the agent halts — see §D.6.)
5. **Multi-agent scope** — Per-alias deploy signals; the harness deploys affected clones **sequentially** (deploy A → pull/compose/push A → restart A → then B…) to avoid `origin/main` push races on the shared ref. Each clone writes only its own alias-scoped `.squidsquad/<alias>/CLAUDE.md`, so no file-level conflict; sequencing is for the push to a shared ref. (Accepts a bounded consistency window — see §D.2.)
6. **#12519 (settings.json) fold** — DECISION GATE: confirm whether `compose.py deploy-all` writes `.claude/settings.json` alongside `CLAUDE.md`. If yes → covered by the same deploy with no residual. If no (installer-managed only) → out of deploy-signal scope; keep #12519 as a separate workstream. (skill to confirm during impl.)

## 4. Confirmations carried (operator) + open sub-question
- "Stop" = finish current atomic unit, then halt at the ack-cursor boundary — NOT abandon mid-feature-branch.
- Agent leaves a **clean tree on main** before handing off.
- Deploy signal fires **only** on composed-source changes, targeting only affected agents.
- **OPEN (§D.5):** workers run on feature branches mid-task. "Leave a clean tree on main before handing off" must define behavior when the deploy signal arrives mid-feature-branch: most consistent with existing stop semantics is *honor at the next boundary where the agent is back on main between tasks* (i.e., the deploy-halt waits for a between-task boundary, not just any ack-cursor, for an agent currently on a feature branch). Needs explicit spec.

## 5. New mechanisms to define (from review §D — these are spec requirements, not optional)
- **D.1 deploy-signal definition** — new signal-catalog entry (AGENT-RUNTIME §5.2): event type / payload shape / how the agent's care filter (`target_alias == me`) branches to deploy-halt vs the normal work wrapper (inspect `event_type`/`event_context`, not just target). New branch in the §8.1 eager loop.
- **D.2 multi-clone consistency window** — between sequential per-clone pushes, `origin/main` has some agents' new output and others' old. Bounded + rare; accept it explicitly OR deploy-then-restart per agent so each is internally consistent. Document the window in HARNESS-ARCH failure-modes.
- **D.4 harness-git failure modes** — define recovery for: pull non-fast-forward/conflict, `compose.py` error (bad source), push rejection. New rows in HARNESS-ARCH §11. (The harness performing git writes on clones is a new operational surface.)
- **D.5 feature-branch case** — see §4 open sub-question.
- **D.6 intent-sequencing race** — the harness must set `intent=stopping` (or a new deploy intent) **before** the agent halts, so the agent's exit is read as a deploy-halt, not a crash (`intent=running` + PID death = crash + auto-respawn). The `deploy-halted` ack-stop result rides this intent.

## 6. Arch-doc edit targets (doc-first; PM owns TRD updates)
**HARNESS-ARCH.md**: §7.1 intent state machine (deploy-in-progress step before respawn); §7.3 health-poll/`reboot_blocked_until` (deploy-halt branch); §7.4 cooperative exit (deploy-halt exit variant); §7.5 `last_compose_checksum` (repurpose to drift-detect→emit-signal); §7.6 `--no-auto-reboot` / `_reboot_affected_agents` (becomes signal-emitter, not direct recompose); **§10 step 1b (HIGHEST drift risk — retire the boot-time local compose)**; §11 failure modes (new harness-git rows).
**AGENT-RUNTIME.md**: §5.2 signal catalog (+deploy-signal, +`ack-stop` `deploy-halted` result); §8.1 eager loop (deploy-signal branch); §8.2 boot (reads committed output, no recompose — state invariant); §8.6 improvement subloop (deploy preempts at ack boundary); §7/§9 loop-mode + wake-mode (deploy behavior per mode).

## 7. Verification sketch (ACs PM finalizes for skill's TEST-PLAN)
- Behind clone + deploy signal → output matches origin source (not stale local).
- Deploy never lands mid-atomic-unit (only at an ack boundary; for a worker, only at a between-task on-main boundary).
- Queued events present at deploy time drain post-restart (none lost).
- After a deploy, `main` output matches `compose.py deploy-all` from current source (per clone).
- Crash vs deploy-halt are distinguished (harness does not treat a deploy-halt as a crash).
- Harness-git failure (pull conflict / compose error / push reject) → defined recovery, no silent corruption.

## 8. Next steps
1. **Operator scope-confirm (§0)** — proceed given the larger-than-minimal machinery, or reconsider.
2. PM integrates §6 into HARNESS-ARCH + AGENT-RUNTIME (doc-first TRD updates).
3. PM finalizes ACs; files Phase 2 implementation to skill (code = skill domain), referencing the updated TRDs + this design.
4. Phase 1 (#12906) proceeds independently.

---

## Appendix — Review findings (grounded cross-doc audit, 2026-06-19)
Full A/B/C/D findings retained in the #12895 thread / iteration log. Headlines: A.1 §10 step 1b is the live bug path (must retire); A.3/A.4 harness has no pull-at-boot and no pause-before-respawn (new machinery); D.1 deploy-signal undefined; D.2 multi-clone consistency window; D.4 harness-git failure modes; D.5 feature-branch clean-tree; D.6 intent-sequencing race. Resolutions in §3/§5.

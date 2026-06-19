# Deploy-Signal Recompose Design (#12895)

**Status**: DESIGN (doc-first) — operator-approved approach 2026-06-19; pending DS-audit + arch-doc integration before Phase 2 implementation is filed to skill.
**Owner**: pm (design) → skill (implementation)
**Supersedes**: skill's A/B/C options on #12895.

---

## 1. Problem & root cause

Composed agent-instruction outputs (`.squidsquad/<role>/CLAUDE.md` + `.linked.md`) are **git-tracked** and get **committed** (the eager-deploy model). When a clone is **behind origin** (chronic boot-pull lag, #12526), a recompose runs against **stale local source** and regenerates the composed outputs as a **revert** of already-shipped content. Because nothing hand-edits composed outputs, the revert is **silent**; if committed+pushed it un-ships a change fleet-wide.

Observed 3× on 2026-06-19: PM clone at boot, skill clone boot 21-behind, and a revert that reached `main` during #12800's ship before DM repaired it (a023a658e).

**Root condition = stale source at recompose time.** Interruption/timing was a red herring.

The bug needs TWO conditions; removing either kills it:
1. Composed outputs are tracked + committed.
2. A clone recomposes from not-yet-pulled (stale) source.

## 2. Locked approach (operator, 2026-06-19)

Keep compose **at the harness** (minimal change; no untrack, no installer/boot-ordering change → preserves the git-as-audit-trail value). Make it **pull-first** (fixes condition 2) and **non-interrupting** (deploy at an atomic-work boundary, not mid-task).

### Phase 1 — pull-first guard (immediate; filed #12906, auto-approved bug)
The harness recompose path **ensures-on-main + pulls origin/main before composing**. Strict subset of the durable design (not throwaway). Eliminates condition 2 immediately.

### Phase 2 — deploy-signal, non-interrupting (this doc; durable)

**Trigger.** When DM ships a change that touched composed-source (`references/...`), the harness emits a **deploy signal** to the affected agent(s) only. Scope which agents via the existing file-watcher change-detection (only composed-source changes; not every ship).

**Agent behavior.** The agent honors the deploy signal at the **next `ack-cursor` boundary** — NOT full idle. Rationale: `ack-cursor` is already the atomic-work seam (finish one unit, before the next), so it is a safe and *frequent* point — the deploy propagates ASAP instead of waiting for the queue to drain. At that boundary the agent:
1. has finished its current atomic unit and left a **clean tree on `main`** (state committed/pushed),
2. **acknowledges** the deploy signal,
3. **halts** — no improvement-loop, no next-event pickup, no new work — and hands control to the harness.

Remaining queued events stay past the cursor and **drain after restart** — nothing is lost.

**Harness behavior.** On the agent's deploy-halt: **ensure on `main` → pull → recompose → commit → restart** the agent. Pull-first guarantees current source.

### Key properties
- **Pull-first** → recompose always from current source → condition 2 gone.
- **Sole recompose path** → eliminates the **boot-time recompose-from-stale** (the exact path of the 2026-06-19 occurrences). At boot the agent just reads whatever the last pull-first deploy correctly committed.
- **Composed outputs stay tracked** → git audit trail of "what's deployed on main" preserved.
- **Self-healing** → a stale output on main is overwritten correctly by the next deploy.
- **Reuses the existing stop/restart lifecycle** → minimal new machinery.

## 3. Open design points (resolve before/with DS-audit)
1. **Boot path** — with the harness no longer recomposing at boot, confirm boot simply reads the committed (correct) composed output. Define what happens if boot detects composed-vs-source drift (should be impossible if deploy is the sole path + pull-first, but state the invariant).
2. **Polling agents (qa)** — the deploy signal is an event; a polling agent honors it on its poll cycle (which already pulls first). Spec the polling path explicitly.
3. **Event arrives mid-deploy** — if a nudge lands while the harness is pulling/composing, the restart must win cleanly (agent is mid-handoff/about-to-restart). Spec the ordering so no work starts against half-deployed state.
4. **Status reporting** — the harness must reliably detect the agent reached the deploy-halt at an ack boundary. It already owns the cursor + tracks cycle/phase; decide whether an explicit "deploy-halted" ack is needed (likely yes — symmetric with ack-cursor).
5. **Multi-agent scope** — a change to a shared source (e.g. `references/roles/instructions.md` → all 4 composed) signals all affected agents; each deploys its own clone (each pulls current → all correct; different files → no cross-agent conflict).
6. **#12519 fold** — `.claude/settings.json` is the same family (tracked + per-clone rewrite). Confirm the pull-first deploy model covers it or note the residual.

## 4. Confirmations carried (operator)
- "Stop" = finish current atomic unit, then **halt at the ack-cursor boundary** — NOT abandon mid-feature-branch.
- Agent leaves a **clean tree on `main`** before handing off.
- Deploy signal fires **only** on composed-source changes, targeting only affected agents.

## 5. Arch-doc touchpoints (doc-first integration)
- **HARNESS-ARCH** — deploy/lifecycle: harness ensure-main+pull+recompose+restart on agent deploy-halt; file-watcher emits the deploy signal (stops doing the recompose itself).
- **AGENT-RUNTIME** — deploy-signal handling at the ack-cursor boundary; the halt semantics; polling-mode path; relationship to the stop/restart lifecycle.
- **idle-cooldown-loop** (sub-skill) — note that a pending deploy preempts at the ack boundary before the idle/scan state is reached (no sequencing conflict).

## 6. Verification sketch (for skill's TEST-PLAN; ACs are PM's to finalize)
- A behind clone receiving a deploy signal produces composed output matching **origin** source (not stale local).
- A deploy never lands while the agent is mid-atomic-unit (only at an ack boundary).
- Queued events present at deploy time are drained after restart (none lost).
- Composed outputs on `main` always match `compose.py deploy-all` from current source after a deploy.

## 7. Next steps
1. DS-audit this design + cross-pair against HARNESS-ARCH / AGENT-RUNTIME (prose-drift discipline).
2. Resolve the §3 open points; finalize ACs.
3. Integrate into the arch docs (PM).
4. File Phase 2 implementation to skill (compose/harness code = skill domain).
(Phase 1 / #12906 proceeds independently in the meantime.)

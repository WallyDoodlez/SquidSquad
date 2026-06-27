---
type: learning
tags: [agent-runtime, event-mode, deploy-signal, boot-drain, harness-restart, case-e, cursor, 13175]
created: 2026-06-21
updated: 2026-06-21
owner: worker
status: active
confidence: medium
source: observation
---

A **`deploy-signal` in your EVENT-mode boot-drain** (`GET /events/for/<role>?since=<cursor>` returns one, `target_alias`=you) is NOT automatically a live deploy to honor. After a **full-team harness restart** it is often **residual telemetry**: the harness already force-respawned you (didn't take the cooperative deploy path) and never advanced your cursor past the signal — so the Case E contract's "honor → halt + `ack-stop(deploy-halted)` → do NOT `ack-cursor`" guidance (which assumes the harness will advance your cursor) does not fit, and following it risks the **respawn → re-halt loop** Case E itself warns about (no-op deploy, cursor still not advanced).

**Diagnose live vs residual before acting (facts, not the event):**
1. **Compose drift?** `git diff --name-only HEAD..origin/main` — if NOTHING under `references/` changed, a recompose changes your `CLAUDE.md` by zero bytes → the deploy is a no-op for you. (State/doc-only commits like `pm/working-state.md` or `docs/*-ARCH.md` are irrelevant to compose.)
2. **Is the harness actually waiting on you?** Harness `/status` for your role: a deploy-halt expects `status:"deploying"`. If it reads `status:"running"`/`intent:"running"`, the harness is treating you as a normally-running agent — it is NOT blocked on your `ack-stop`.
3. **Timing tell:** the signal's `received_at` ≈ your own `last_spawn_at`, with harness `uptime` tiny (tens of seconds) = a full-team restart emitted it, not a mid-session compose-drift deploy.

**If residual (no drift + status:running):** `ack-cursor` past it deterministically (POST `ack-cursor {event_id, role}`; verify `GET ?since=<newcursor>` → `[]`). This clears it without the busy-loop you'd get from leaving it unacked (`event_poll` re-NUDGEs every tick on any event past the cursor). **If genuinely live (real `references/` drift AND harness waiting):** honor Case E normally.

Contract hardening tracked in **#13175** (either harness shouldn't emit no-drift deploy-signals on full-team restart, or Case E should encode this drift-check). Until then this diagnostic is the safe path. Relates to [[learning-restarting-intent-not-across-harness-restart]] and the [[learning-deploy-pull-block-divergence-recover-by-merge]] deploy-recovery family.

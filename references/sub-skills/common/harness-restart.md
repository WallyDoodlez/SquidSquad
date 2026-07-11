---
slot: instructions
ordinal: 10
---

### Harness Restart — Request a Clean Relaunch of the Harness

#### Purpose

The harness supervises agent lifecycle, but nothing inside an agent restarts the **harness itself**. When the harness process is alive but **degraded in a way an agent-restart can't fix** — its event dispatch, file-watch, or HTTP surface is misbehaving and a fresh process would clear it — an agent can ask the harness to relaunch via `POST /restart`. This sub-skill is the *when / how / what-to-expect* for that request. It is mechanism, not a parallel control path: the supervised launcher owns harness lifecycle exactly as the harness owns agent lifecycle (see [[self-restart]] for the mirror at the agent layer).

#### WHEN to request a restart

Request a harness restart only when **all** of these hold:

- The fault is **harness-level**, not agent-level — restarting your own session (or any single agent) would not fix it. Examples: `assigned-to` dispatch stopped waking agents (the #12824 incident that motivated this), the event deque or cursor store is wedged, the L4 file-watch died, `/status` reports stale agent state a single reboot won't clear.
- A **fresh harness process is a plausible cure** — the symptom is process-state corruption or a stuck subsystem, not a code bug (a code bug needs a fix + ship, not a restart) and not an environment problem (auth, port conflict) a restart would just reproduce.
- You have **confirmed the symptom from facts** — `/status`, harness logs (`.squidsquad/harness-errors.log`), live process state — not from conversation memory. Cross-check at least one independent source before concluding the harness is degraded.

If the harness process is **fully dead** (not responding on its port at all), `POST /restart` cannot help — the endpoint needs a live harness to receive it. That is an operator-restart / supervised-launcher relaunch situation (the single consolidated launcher `.squidsquad/start.{ps1,sh}`, #13318); file it to the `human` alias via a tracked transition (per the L1 **Never Stop While Work Is Pending** rule — human-handoff case) rather than trying to self-serve.

**Coordination — prefer PM.** A harness restart respawns the **whole team**, so it is a team-level action. Unless you ARE the PM, or PM itself is the unreachable/degraded party, **route the recovery to PM** via a tracked ticket (status transition, never a bare comment — bare comments wake no one) and let PM trigger the restart. Self-serve the `POST /restart` directly only when waiting on PM would prolong an outage that is actively blocking the squad and you have confirmed the conditions above.

#### HOW to request it

1. **Resolve the harness port.** Read `.squidsquad/.harness-port` (relative to repo root). If it is absent, unreadable, empty, or not a valid integer, default to `7373`.
2. **POST the restart request** (5-second timeout):

   ```bash
   curl -sf --max-time 5 -X POST http://127.0.0.1:<port>/restart
   ```

   On success the harness returns `202` with `{"status": "restarting", ...}` and begins tearing down all agents in the background. `/restart` is distinct from `/shutdown`: `/shutdown` exits the harness with code `0` (permanent — the launcher does NOT relaunch) and deletes the port file; `/restart` exits with the restart code (`42`, mirroring the agent exit-42 convention) and **keeps** the port file so the relaunched harness reuses it.

3. **If the POST succeeds (202), there is nothing more for you to do.** Do not poll, do not re-POST, do not arm `Monitor` again — your session is about to end (see below).
4. **If the POST fails** (connection refused, timeout, or any non-202), the harness is effectively dead or unreachable — `/restart` needs a live harness to receive it, so retrying won't help. Fall back to the fully-dead path: file the recovery to the `human` alias via a tracked transition (per the L1 **Never Stop While Work Is Pending** rule — human-handoff case), then continue. Do not re-POST.

#### What to EXPECT

- The harness stops every agent — **including you, the requester** — then exits with the restart code.
- **Only the supervised launcher relaunches it.** If the harness was started via the single consolidated launcher `.squidsquad/start.{ps1,sh}` (#13318 — which runs the harness under the supervised auto-relaunch loop, and is the documented default for installs) or via `squidsquad_cli.py start` (which launches the harness under that launcher's `--bare` supervised path), the launcher sees the restart exit code and relaunches the harness, which respawns all agents fresh. If the harness was instead started by invoking `harness.py` **directly** (no supervising launcher — the `_harness_launch_tail` fallback when the launcher file is absent, or a manual dev run), `/restart` cleanly stops the harness but **nothing relaunches it** — graceful degradation, but the team stays down until an operator relaunches. You generally cannot tell from inside your own session which way the harness was started — there is no flag to read. Assume the documented default (supervised) and let the **post-restart verification below be the empirical check**: if the agents do not come back, the harness was not supervised and an operator must relaunch it (another reason to record the recovery on the forge before you POST, since your own session ends on restart and the check happens in the respawned session).
- Your current session **ends with the harness** and respawns as a brand-new session under the relaunched harness. Anything you have not already committed/transitioned on the forge is gone — the forge is the only durable record, so make sure the triggering condition and your intent are recorded there (a tracked ticket) **before** you POST `/restart`.

#### POST-restart verification

Verification happens in the **respawned** session (you cannot verify from the session that just ended). The agent that owns the recovery ticket (usually PM) confirms, from facts:

- **All agents are back** — `GET /status` lists every configured alias with `status: running` and `bootup_complete: true`.
- **Wake mode is correct** — each agent re-probed the harness at boot and came up in event mode (not the polling fallback), per the boot-mode probe.
- **The triggering condition is cleared** — the original symptom (stuck dispatch, dead watcher, stale state) no longer reproduces. If it persists, a restart was the wrong remedy — the fault is a code bug or environment problem; re-file accordingly instead of restarting again.

Close the recovery ticket only once all three hold. A restart that doesn't clear the symptom is not a fix.

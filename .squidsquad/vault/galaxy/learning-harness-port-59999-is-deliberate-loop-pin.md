---
type: learning
tags: [dm, harness, boot, wake-mode, loop-mode, ops, 10855]
created: 2026-06-13
updated: 2026-06-13
owner: dm
status: active
confidence: high
source: observation
links: [learning-dm-local-merge-when-harness-down]
---

## Context

DM cycle 421 (2026-06-13). DM booted, probed `.harness-port` = `59999`, got connection-refused, and fell to LOOP/polling mode — concluding "harness is DOWN" and operating in degraded local-merge mode for the whole session. When the operator asked DM to "restart the harness," investigation revealed the harness was actually **UP and healthy on :7373** (2h+ uptime). DM then "self-healed" `.harness-port` to `7373` — which silently **broke a deliberate workaround**.

## Content

**`.harness-port = 59999` on an agent clone is (currently) a DELIBERATE PM loop-mode pin, NOT a stale/dead-port bug.**

- `.squidsquad/pm/pin-keeper.sh` writes `59999` (a dead port) into the skill/dm/qa clones every 30s. Any agent that boots probes `:59999`, fails, and falls to **LOOP mode (functional)** instead of **EVENT mode (INERT — #10855)**. The boot-to-loop is the INTENDED outcome.
- So a "harness unreachable → polling" boot does **not** imply the harness is down. The harness can be healthy on the real port (`:7373`) while the port file points at a dead port by design.

**Rules for DM in this state:**
1. **Do NOT "self-heal" `.harness-port` to 7373.** It undoes the pin and would let the next agent boot into the inert event-mode state. (pin-keeper re-asserts 59999 within ~30s, but don't rely on that — don't touch it.)
2. Before declaring "harness down," probe the **real** config port too: `curl -sf --max-time 5 http://127.0.0.1:7373/status`. If it answers, the harness is up and the port-file value is a pin, not a fault.
3. LOOP mode is the correct/working mode while the pin is active. DM ships via the local-merge path ([[learning-dm-local-merge-when-harness-down]]); that work is fully valid.
4. The pin is temporary — it disappears when **#10855** (agents boot inert in event mode) is fixed. Re-confirm the mechanism each session rather than assuming.

## Rationale

`#11587`/`#11641` (shipped this session) fixed the reboot/crash loop, but `#10855` (inert event-mode boot: emits bootup-complete, never arms event_poll, never cycles, ~13% CPU spinning) is unfixed and `blocked:human-action`. Until then, PM's pin is the ops workaround that keeps agents in the functional loop mode. Misreading the pin as a dead harness wastes a diagnosis and — worse — "fixing" the port file actively sabotages the workaround.

## Related

- [[learning-dm-local-merge-when-harness-down]] — the loop-mode ship path DM uses while pinned
- #10855 — inert event-mode boot (sole event-mode blocker, blocked:human-action, PM-driven)
- #11587 / #11641 — reboot-loop fixes (shipped); did NOT fix inert boot
- `.squidsquad/pm/pin-keeper.sh` — the pin mechanism (PM-owned, ops not code)

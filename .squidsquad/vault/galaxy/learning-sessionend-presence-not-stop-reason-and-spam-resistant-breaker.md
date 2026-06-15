---
name: learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker
description: Claude Code's SessionEnd hook only fires on GRACEFUL termination (a crash can't run a hook) and its stop_reason is a UI enum (clear/logout/other), not an exit-reason — so harness graceful-vs-crash detection is presence/absence of a SessionEnd, NOT the reason value; and an agent-self-reportable 'graceful' signal must not RESET a crash-loop breaker (only skip-increment) or a misbehaving agent escapes it
metadata:
  type: learning
type: learning
tags: [learning, harness, liveness, hooks, claude-code, reboot, 12418, 12271, 12244, self-hosting]
created: 2026-06-15
updated: 2026-06-15
owner: skill
status: active
confidence: high
source: observation
links: [learning-ead-status-routing-and-back-transition-dedup]
---

# SessionEnd is a presence signal, not a reason; and a self-reportable "graceful" must not reset a breaker

**Built (#12418, #12271 liveness slice 1):** a Claude Code `SessionEnd` hook reports an agent's exit to the harness so the reboot decision keys off a fact, not a guess. Verifying the actual hook API BEFORE designing (via the claude-code-guide) surfaced three gaps the doc had assumed away — PM doc-synced HARNESS-ARCH §15.4/§16 to match:

1. **`SessionEnd` only fires on GRACEFUL termination.** A hook is code that runs IN the session; a hard crash (kill / OOM / usage-limit exit-1) dies before any hook runs. So **graceful-vs-crash = presence/absence of a SessionEnd before the dead PID**, NOT a reason value. A natural crash loop produces NO SessionEnd → it's correctly caught by the #12244 backoff.
2. **`stop_reason` is a UI enum** (`clear|resume|logout|prompt_input_exit|bypass_permissions_disabled|other`) — not "exit-42" or "usage-limit", and there is **no `exit_code`**. Don't design a reason→decision map around exit semantics the hook doesn't carry.
3. **Native `type: http` hooks** POST the payload directly (no shell wrapper), are fail-open by design, and take a per-hook `timeout` (seconds). The role can ride an `X-Agent-Role` header interpolated per-clone from `${SQUIDSQUAD_ROLE}` — so ONE committed `.claude/settings.json` serves every clone (no per-clone writes).

**The breaker-bypass (DS-REVIEW caught it, my tests missed it):** the reboot decision used the SessionEnd "graceful" signal to **reset** the #12244 crash-loop streak to 0. But the endpoint is fail-open and unauthenticated — a misbehaving agent can POST SessionEnd while still running, then crash, and keep the streak permanently at 0 → unbounded respawn churn (the exact thing #12244 prevents). **Fix: a self-reportable "graceful" must only SKIP the increment, never RESET the counter** — so accumulated real crashes can't be zeroed. Plus clear the signal on every spawn (only the current lifecycle's hook counts; closes the delayed-hook race). Full termination-correlation (PID-match) is deferred to a later #12271 slice.

**How to apply:**
- Any liveness/health signal an agent can SELF-REPORT is adversarial-input: it can prove "I did X" but not "I'm healthy / I shut down cleanly." Use it to grant leniency additively (skip a penalty), never to ZERO a safety counter.
- When wiring an external hook/API, verify the real payload shape FIRST (the [[learning-ead-status-routing-and-back-transition-dedup]] reflex: don't design against assumed semantics). Here it caught 3 doc gaps before a line of code.
- Presence/absence is often the robust signal when the richer field (a reason/code) isn't reliably available — a crash that can't report looks identical to silence, which IS the death signal.

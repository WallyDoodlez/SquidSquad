---
type: learning
tags: [agent-runtime, boot, thin-launcher, wake-mode, single-source-of-truth]
created: 2026-06-12
updated: 2026-06-12
owner: skill
status: active
confidence: high
source: code
links: [decision-reboot-kills-child]
---

## Context

#11512: `thin_launcher.py` injected `/loop {interval}m execute one Ralph Loop cycle` as the spawned agent's literal first-turn prompt (added by #9725 as a loop-mode-era stall fix). Because the first turn was a `/loop` slash command, the agent ran the loop skill and **never executed composed CLAUDE.md boot Step 1** — the harness-reachability probe that selects EVENT vs POLLING wake mode. Result: every agent booted loop mode even when the harness was up; event mode (the canonical wake path) was dead-on-arrival and never runtime-validated.

## Content

**The agent's spawn prompt (first-turn input) must be mode-NEUTRAL. It must not encode a wake-mode or control-flow decision.** Wake-mode selection belongs to exactly one place: the composed CLAUDE.md boot Step 1 probe. A spawn prompt that invokes `/loop` (or any mode-committing action) preempts that probe and silently pins the agent to one mode.

Fix pattern: inject a neutral boot trigger ("execute boot Step 1, proceed in whichever mode the probe selects") and let the boot sequence decide. Boot Step 1's POLLING branch already self-schedules `/loop`, so the launcher never needs to — the launcher injecting it was both redundant and harmful.

Rejected alternatives (launcher-side harness probe, conditional `/loop`): both duplicate the harness probe logic in Python = a **parallel control path**, which HARNESS-ARCH forbids ("lifecycle authority is the harness — no sentinel files or parallel control paths"). Keep mode-selection authority single-sourced in boot Step 1.

## Rationale

When a control decision (which wake mode?) has two encoders — the launcher's spawn prompt AND boot Step 1 — they drift, and the louder one (the explicit first-turn `/loop`) wins regardless of correctness. Collapsing to one source of truth is the durable fix. General rule: **don't let the bootstrap's invocation mechanism make decisions the bootstrap's own logic is supposed to own.**

## Related

- [[decision-reboot-kills-child]]
- #11512 (origin), #9725 (the superseded loop-spawn mechanism)

---

### Changelog

- 2026-06-12 — Created by skill (cycle 1638). Spawn prompt must be mode-neutral; boot Step 1 single-sources wake-mode selection.
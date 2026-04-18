---
type: decision
tags: [boot, liveness, health-check, reliability]
created: 2026-04-18
updated: 2026-04-18
owner: pm
status: active
confidence: high
source: conversation
links: [human-profile]
---

## Context

boot_remote.py used `.health` files as primary liveness check. When agents were killed externally (terminal closed), `.health` stayed "alive" but processes were dead. Agents weren't rebooted because boot_remote.py never reached the PID fallback.

## Content

PID is primary for liveness, `.health` is informational only.

- **Boot decision**: Read PID → process exists? → no = boot it. `.health` is not consulted.
- **Status display**: `.health` carries metadata (booting, backoff, error reason) for health_check.py and status bar — but never gates the boot decision.
- Process gone = gone. No need to check anything else before rebooting.

## Rationale

OS-level process check (tasklist/kill -0) is ground truth that cannot go stale. Application-level state files (.health) are updated by the wrapper on clean exit — but external kills bypass the wrapper, leaving stale "alive" state. Human directive: "just use PID, it's more direct." See #1301.

## Related

[[human-profile]]

---

### Changelog

- 2026-04-18 — Created by pm. From #1301 discussion — all 3 agents (dm/qa/skill) were dead but .health said alive. Human confirmed PID-first approach.

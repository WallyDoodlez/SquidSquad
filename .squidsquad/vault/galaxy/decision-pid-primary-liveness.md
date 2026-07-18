---
type: decision
tags: [boot, liveness, health-check, reliability]
created: 2026-04-18
updated: 2026-06-27
owner: pm
status: archived
confidence: high
source: conversation
links: [human-profile]
---

> **ARCHIVED / SUPERSEDED (2026-06-27, #12492 SHIPPED).** PID-primary liveness is no longer the runtime model. #12271 (progress-based liveness — hooks + heartbeat + acks) shipped via cutover #12492: **progress signals are now authoritative for reboot decisions; PID is demoted to teardown-only (kill, never prove-alive).** Operator GO'd it this session and it landed clean (QA-verified: zombie caught within bounded window; busy agent not falsely rebooted; DM shipped). Real-world drivers that forced the change — repeated **wedge-alive** incidents PID-liveness could not catch: qa zombie (#10855), the dm/pm freeze, and two this session (skill never-resolved-a-PID at boot, qa frozen ~48min with dispatched work unprocessed; both required manual PM recovery). The PID-primary content below is **historical record only** — do not treat it as current behavior. See [[learning-graceful-restart-grace-timer-on-wedged-agent]].

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
- 2026-06-27 — pm: status → superseded-in-progress. Operator GO on #12271 (progress-based liveness; PID → teardown-only). Content stays current until #12492 cutover ships, then archive. Driven by repeated wedge-alive incidents PID-liveness cannot detect.
- 2026-06-27 (same session) — pm: status → archived. #12492 cutover SHIPPED (QA-verified, DM-shipped). Progress-liveness now authoritative; PID teardown-only. Content below is historical record only.

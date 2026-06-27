---
name: learning-polling-agent-reads-as-inert-on-status
description: a SquidSquad agent in POLLING mode shows bootup_complete=false + stale last_activity on harness /status (it doesn't heartbeat the event bus) — which reads as "inert/zombie" but is healthy; diagnose agent health from the agent's OWN clone ground truth (working-state/current-state/commits), never from /status alone
metadata:
  type: learning
type: learning
tags: [learning, health-diagnosis, harness, polling, event-mode, status, port-discovery, 12820, 12409, 10855, self-hosting]
created: 2026-06-19
updated: 2026-06-19
owner: skill
status: active
confidence: high
source: observation
links: [learning-default-port-fallback-is-live-egress-trap-in-tests]
---

# A polling-mode agent reads as "inert" on /status but is healthy

**Observed (#12820, reproduced 2026-06-19):** harness `/status` showed `qa` with `bootup_complete=false` and `last_activity` frozen ~4.6h — the classic "inert/zombie" signature. Ground truth from qa's OWN clone (`SquidSquad-qa/.squidsquad/qa/working-state.md` + `current-state`) showed qa **alive and verifying** — it had just PASSED #12825 (cy345) and #12511 (cy346) to pending-ship. qa was in **POLLING mode**, which doesn't heartbeat the event bus, so `/status` (which reflects event-bus activity) cannot see it. This exact conflation has misled multiple PM sessions into "qa is a dead zombie" and at least one unnecessary reboot.

**Why qa is stuck in polling (the real bug, #12820):** `harness.py:find_free_port()` (≈3786-3800) tries to bind the desired port (7373); on `OSError` (already in use) it **silently binds an ephemeral port** (`bind(("127.0.0.1", 0))`) and returns it. A second harness started while the live one holds 7373 grabs a random port (28493/34198/…), writes it to its clone's `.harness-port`, then exits → qa's clone is left pointing at a dead ephemeral port → boot probe `EXIT=7` → permanent POLLING fallback. The ephemeral fallback (fine for e2e test harnesses) is a poison for the production singleton.

**How to apply:**
- **Never conclude an agent is dead/inert/zombie from harness `/status` alone.** A polling agent legitimately shows `bootup_complete=false` + stale `last_activity`. Cross-check the agent's clone ground truth FIRST: its `working-state.md`, `current-state` mtime, recent git commits in its clone. This is the [Health & Diagnostics — facts over context] soul rule made concrete.
- A dead process (`tasklist` shows the pid gone) IS real death; an alive pid + stale `/status` is NOT — check ground truth before rebooting. Rebooting a healthy polling agent is disruptive.
- When auditing "agent X is inert", separate the two facets like #12820 does: (a) is the process actually dead? (b) is it merely polling (so /status can't see it)? Only (a) warrants a reboot.
- Root fix for the polling-trap lives on #12820 (harden `find_free_port` so the singleton harness doesn't bind/distribute an ephemeral port). Sibling diagnostic to [[learning-default-port-fallback-is-live-egress-trap-in-tests]] — same `.harness-port` / port-discovery surface, opposite direction (egress vs ingress).

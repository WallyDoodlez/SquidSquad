---
name: learning-singleton-must-refuse-not-fallback-when-canonical-port-held
description: a production singleton that distributes its port to shared clone state must REFUSE to start when its canonical port is held, never silently bind an ephemeral port — the fallback poisons every clone's .harness-port with a dead port; a /status liveness probe discriminates a live peer (refuse) from a TIME_WAIT slot during restart (reclaim, uvicorn handles via SO_REUSEADDR)
metadata:
  type: learning
type: learning
tags: [learning, harness, port-discovery, singleton, startup, restart, event-mode, 12820, self-hosting]
created: 2026-06-19
updated: 2026-06-19
owner: skill
status: active
confidence: high
source: observation
links: [learning-polling-agent-reads-as-inert-on-status, learning-default-port-fallback-is-live-egress-trap-in-tests, learning-restarting-intent-not-across-harness-restart]
---

# A singleton that distributes its identity must refuse-to-start, not fall back

**Observed (#12820):** `harness.py find_free_port` silently fell back to an ephemeral port when the canonical port (7373) was held. The harness then **self-writes its port to its own clone `.harness-port` AND distributes it to every other clone** (so each clone discovers the live harness). A second harness started while the singleton was live bound a random ephemeral port, distributed THAT dead port to all clones, then exited → every clone now pointed at a dead port → permanent **polling fallback** for the whole team (the root cause behind [[learning-polling-agent-reads-as-inert-on-status]] and the #10855/#12409 "inert/zombie" framing).

**The principle:** the silent ephemeral fallback is correct for a *test* harness (isolated tmp `SQUIDSQUAD_DIR`, wants any free port) but catastrophic for a *production singleton whose port IS shared, distributed state*. When such a singleton can't get its canonical identity, falling back doesn't degrade gracefully — it **poisons the shared state** for every consumer. The singleton must **refuse to start** (and never touch the shared state) instead.

**How to apply:**
- Split the path by intent: an **explicit** `--port` (incl. `--port 0`) opts into ephemeral fallback (test harness); the **production path** (no `--port`) acquires the canonical port or refuses — it never binds ephemeral, so poisoning is structurally impossible (the port-file write is gated behind a successful serve on the canonical port).
- Discriminate **live peer vs stale slot** with a liveness probe, not a bare bind. A plain bind can't tell a live listener from a TIME_WAIT slot. `_probe_harness_status(port)` does `GET /status` and trusts only harness-shaped JSON: a live harness responds → **refuse + exit(1)**; silence → free OR a TIME_WAIT slot from a just-exited harness during supervised restart (#12825 exit-42 → wrapper relaunch) → **claim the canonical port**.
- Let the server layer handle TIME_WAIT reclaim: uvicorn 0.41 `bind_socket` *always* sets `SO_REUSEADDR`, so a restart-over-TIME_WAIT rebind succeeds at the uvicorn bind — no manual SO_REUSEADDR dance needed in the pre-check. (Windows caveat: `SO_REUSEADDR` there also permits duplicate binds to a *live* listener, so the `/status` probe — not the bind — must be the discriminator for a live peer.)
- `find_free_port(0)` must return the OS-assigned port via `getsockname()`, not the literal `0` it was handed — a `--port 0` caller advertises the real port. The old `return default` swallowed this.
- Hardening the startup makes the *trigger* (whatever production invocation runs a 2nd harness against a real clone) harmless even when the trigger stays untraced — defense at the seam beats chasing every caller.

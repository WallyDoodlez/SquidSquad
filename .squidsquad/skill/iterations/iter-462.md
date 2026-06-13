# Iteration 462 — ⭐ found the #11586 root cause (harness was UP all along)

**Mode**: loop (sticky this session). Manual ops.

## Breakthrough
After 9 cycles of "harness down (59999 exit 7)", instead of another idle confirmation I investigated WHY the harness was down — and it wasn't. **The harness has been UP and healthy on port 7373 the entire time** (curl /status: uptime 16h34m, v0.44.0; /events/cursor/skill returns a live cursor).

My session ran loop-mode all along because my clone's `.harness-port` said **59999** (a dead port) — I'd been probing the wrong port since boot. The boot logic was correct; its input was poisoned.

## Root cause of #11586 (the loop-mode-on-some-agents symptom)
Per-clone port-file matrix explains every observation:
- pm/qa: `.harness-port` MISSING → default 7373 → reach harness (qa reached event mode ✓).
- dm: 7373 → reaches harness (event mode ✓; its starvation is a separate delivery bug).
- skill(me): **59999 (dead)** → probe fails → loop mode ✗.

Vector: harness `_deferred_init` (harness.py:1280-1294) distributes its port into every `.local-config` clone. An integration test that starts a harness on an ephemeral port (59999 = `find_free_port(59999)`, tests/test_harness.py) against the real `.local-config` writes that dead port into the REAL sibling clones; teardown never restores them → strands live agents in loop mode. Concrete instance of [[learning-tests-must-not-mutate-shared-live-state]].

## Actions
- Corrected skill clone `.harness-port` 59999→7373 (now curl-reachable). Future boot reaches event mode (mode sticky this session).
- Posted comprehensive root-cause finding on #11586 (matrix + vector + fix).

## Durable fix — NEXT CYCLE (skill-domain, NOT gated on #11683)
1. Tests must not distribute ephemeral port into real clones (isolate `.local-config` / guard `_deferred_init` clone-distribution / restore clone `.harness-port` in teardown).
2. Harden `_discover_port` (event_poll.py + cycle_post.py): a port-file value that isn't actually listening = stale → fall through to default/parent-walk, so a leaked file can't strand an agent.
Own branch off main; own tests green; independent of the #11683 gate.

## Note to operator
Harness is fine. Mis-ported agents reach event mode after a port-file correction + reboot. This likely un-sticks the event-mode degradation underlying the whole batch.

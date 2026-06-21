---
name: pattern-verify-liveness-lifecycle-with-independent-runtime-probe
type: pattern
tags: [verification, harness, liveness, testing-craft]
created: 2026-06-20
related: [pattern-verify-egress-guard-on-the-wire]
updated: 2026-06-20
owner: verifier
status: active
confidence: medium
source: review
---

# Pattern: verify harness liveness/lifecycle fixes with an independent runtime probe

**Context.** Harness fixes that touch process liveness, PID resolution, reboot/respawn timing, or crash-loop breakers (#12294 image-verified liveness, #13032 deploy-respawn PID-death wait, #12409 slow-loop reboot breaker) ship with mocked unit tests — the worker patches `is_process_alive`, `boot_agent`, `time.time`, etc. Those tests prove the *control flow* but NOT the OS-level reality or the *numeric boundaries*, which is exactly where these bugs live.

**Technique (verifier's load-bearing evidence).** Beyond running the worker's suite, import the actual module in the worktree and exercise the real functions:
- **Against real OS state**: `is_claude_process_alive(<this python.exe PID>)` must return `False` (alive but image≠claude — the recycled-PID hole) while `is_process_alive` returns `True`; `is_claude_process_alive(<a real live claude teammate PID from /status>)` must return `True`. This proves the fix on the live deployment target, not a mock.
- **Against computed boundaries**: drive the threshold/window/backoff math directly — breaker trips at exactly N (not N-1), a timestamp 1s outside the window is pruned, backoff caps at the documented ceiling. Mocks rarely assert the exact boundary; an independent probe does.
- **Trace the load-bearing assumption to source**: when an AC's correctness rests on an unstated dependency (e.g. "restart restores claude_pid"), confirm it in the real code (`save_state`/`load_state`), don't accept the worker's prose.

**Why it matters.** A mocked test that asserts `boot_agent.assert_not_called()` is only as good as the mock's fidelity to the OS. The independent probe is the difference between "the test passes" and "I reproduced the fixed behavior with my own eyes" — the verifier's actual bar. It caught nothing wrong in this cluster (all three PASSed), but it's what *earns* a zero-gap PASS on liveness code instead of rubber-stamping green tests.

See also [[pattern-verify-egress-guard-on-the-wire]] (same spirit: prove the real side-effect on the wire, not via a mock).
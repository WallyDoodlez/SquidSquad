# Iteration 464 — scoped #11723 root fix; backed out on fixture ripple

**Mode**: loop (sticky). Manual ops.

## What happened
- Gates still closed (#11683 unmerged, #11505 no PM answer). Proceeded with #11723 follow-up (1) — the ROOT fix (stop test harnesses polluting real clones).
- **Pinpointed the exact mechanism**: boot_remote.py:35-39 hard-codes SQUIDSQUAD_DIR/LOCAL_CONFIG to REPO_ROOT/.squidsquad and IGNORES the $SQUIDSQUAD_DIR env var — the lone holdout vs harness.py/event_bus.py/event_poll.py which all honor it. So _deferred_init's clone-distribution reads the REAL .local-config even from an isolated test harness → distributes the test port into REAL clones.
- Implemented fix (a): boot_remote._resolve_squidsquad_dir() honoring the env (default unchanged → no prod change). 4 new unit tests (resolver default/env/blank + importlib.reload wiring) — all green; test_harness 184 green (no regression).
- BUT the full suite gained 2 NEW errors: with (a), an isolated test harness reads a MISSING .local-config (the real_harness fixture sets SQUIDSQUAD_DIR but writes no .local-config there) → _parse_local_config sys.exit(2) → role endpoints 404. Confirmed via test_9398_real_agent_subprocess (HTTP 404).
- **Decision: backed out (a)** (reverted uncommitted boot_remote.py + test_boot_remote.py) to keep PR #11729 clean (Part 2 only, DS-clean). The root fix needs (a) + (b) the fixture .local-config isolation TOGETHER — a moderate, careful integration-fixture change not to be rushed at the tail of a long session. Part 2 (#11729) already makes agents resilient to the leaked port, so the root fix is non-urgent cleanup.
- Documented the precise 2-part scope (a: boot_remote env; b: fixture isolation) + the 404 evidence on #11723 for clean dedicated execution.

## Why backing out was right
Shipping (a) alone breaks 2 integration tests. The disciplined move on a high-blast-radius change with an unfinished ripple is to not half-ship it — Part 2 protects the symptom, so no urgency lost.

## Next cycle
- #11683 → if shipped, land the 4 gated PRs.
- #11723 follow-up (1): do (a)+(b) together as one coherent change (boot_remote env-honor + fixture isolated .local-config), own cycle.

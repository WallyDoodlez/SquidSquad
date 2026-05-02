# FEAT-QA-4439 QA Results — SquidSquad Harness Phase 1

## Summary

Live smoke tested across 5 rounds. All 14 TCs pass. 3 CQs pass. 5 bugs found and fixed.

## Test Results

| TC | Title | Result |
|---|---|---|
| TC-1 | Harness starts in visible terminal tab | PASS |
| TC-2 | .harness-port discovery file written | PASS |
| TC-3 | CLI detects harness via discovery file | PASS |
| TC-4 | POST /agents/<role>/start spawns agent | PASS |
| TC-5 | POST /agents/<role>/stop graceful stop | PASS |
| TC-6 | POST /agents/<role>/restart kill+respawn | PASS |
| TC-7 | POST /agents/all/start spawns all | PASS |
| TC-8 | GET /status returns health | PASS |
| TC-9 | POST /shutdown stops agents + exits | PASS |
| TC-10 | CLI error when harness not running | PASS |
| TC-11 | Port fallback when default taken | PASS |
| TC-12 | Harness crash does not kill agents | PASS |
| TC-13 | Standalone scripts still work | PASS |
| TC-14 | Full test suite regression | PASS |

## Comprehension Tests

| CQ | Result |
|---|---|
| CQ-1: Port discovery contract | PASS |
| CQ-2: Agent process isolation | PASS |
| CQ-3: Graceful shutdown sequence | PASS |

## Bug History

5 bugs found and fixed across 5 QA rounds:
1. Route ordering ({role} captured "all") — fixed round 2
2. Windows Unicode crash (cp1252 + box-drawing) — fixed round 2
3. Stale .harness-port (os._exit skipped cleanup) — fixed round 3
4. Indiscriminate shutdown (stopped all agents) — fixed round 3
5. Blocking time.sleep in async handler — fixed round 5

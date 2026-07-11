---
type: learning
created: 2026-07-06
author: qa
related: "#13335, #13346"
---

# Fail-open claims must be tested against the REAL reader — and `except Exception` does not catch `SystemExit`

## What happened

#13335's fix (`_read_context_threshold` in harness.py) claimed fail-open on an absent config field, guarded by `except Exception` in the reader AND in the poll-loop wrapper. Both guards were fictional for the absent-field case: `config.get_field()` calls `sys.exit(1)` for fields not registered in `_FIELD_DEFAULTS`, and `SystemExit` derives from `BaseException` — it sails through `except Exception` and silently kills the poller *thread* (threading swallows SystemExit in non-main threads). Blast radius: entire health poller (liveness, force-kill net, auto-reboot) dead on the first 5s tick for any install missing the config section.

The worker's 20-test suite was green and still missed it: `test_absent_field_defaults` patched `get_field` with `return_value=None` — a return value the real function never produces for that field. The mock encoded the wished-for contract, not the real one.

## The verification technique that caught it

Real-chain TC: real temp config.md (section absent), patch only `config.CONFIG_PATH`, call the real enforcement function. First run of the real reader surfaced `SystemExit` immediately.

## How to apply

- When a fix *claims* fail-open/fallback behavior, derive a TC that exercises the claim through the **real dependency** (real file, real parser, real reader) — never accept a mocked return value as proof of a fallback contract.
- Treat `config.get_field()` (and any helper that may `sys.exit`) as a `SystemExit` hazard: `except Exception` around it proves nothing. Check `_FIELD_DEFAULTS` registration (the `verbose-mode`/#13162 precedent) whenever new config fields are read from daemon/thread contexts.
- Threads make it worse: `SystemExit` in a non-main thread kills the thread *silently* — no traceback, no crash, just a dead loop. A "the daemon just stopped doing X" symptom should prompt a SystemExit-through-except-Exception audit.

Related: [[learning-git-ops-tests-patch-repo-root-not-chdir]] (patch the seam, keep the system real).

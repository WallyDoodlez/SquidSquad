# QA-RESULTS-13335 — Context-threshold not enforced in event mode

**Issue**: #13335 (operator-filed, severity:high, type:issue)
**PR**: #13346 `squidsquad/task/13335` (2 commits, 5 files, +396/−1)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13335.md` (derived from issue body pre-diff)
**Verifier tests**: `.squidsquad/qa/planning/TEST-13335-tests.py` (13 TCs, real-chain — real temp clone, real config.md parse, real `_enforce_context_pressure`)
**Verdict**: **FAIL — 1 defect (TC-3). Back to In Progress.**

## Verdict summary

The core enforcement mechanism is correct and well-built — 12/13 of my real-chain TCs pass, the worker's 20 unit tests pass, comprehension is 4/4 clean, landing is safe. But the fix's **fail-open claim on an absent config field is false**, and the failure mode is worse than the original bug: it silently kills the harness health-poller thread.

## THE DEFECT (TC-3 FAIL) — absent `## Context Pressure` config section kills the health poller

**Finding**: `_read_context_threshold()` claims (docstring) to fall back to `CONTEXT_THRESHOLD_DEFAULT` "when the field is absent or unparseable". For the *absent* case this is false: `config.get_field("context-threshold")` does not return `None` — since `context-threshold` is not registered in `_FIELD_DEFAULTS` (config.py:203-216), `get_field` prints `ERROR: Field 'context-threshold' not found in config.md` and calls `sys.exit(1)` (config.py:289-291). `SystemExit` derives from `BaseException`, so it escapes BOTH `except Exception` guards — the one inside `_read_context_threshold` AND the poll-loop wrapper added in this PR.

**Evidence** (reproduced live, real files, no mocks — `python` repro on branch HEAD e62f5b394):

```
1) SystemExit(1) ESCAPED _read_context_threshold
2) SystemExit ESCAPED the poll-loop except-Exception wrapper
3) poller thread completed normally: False  (thread killed by SystemExit)
```

Repro: temp config.md WITHOUT a `## Context Pressure` section; patch `config.CONFIG_PATH`; call `hs._enforce_context_pressure()` inside a `try/except Exception` in a `threading.Thread` — the thread dies silently on the first tick.

**Impact**: on any install whose config.md lacks the `## Context Pressure` section, the FIRST health-poll tick kills `_poll_loop` silently — taking down liveness polling, the 60s force-kill net, and auto-reboot for the entire fleet. The current install has the section, so enforcement works here — but the shipped defense is fictional and the blast radius is fleet-wide-silent on the exact config shape the docstring claims to handle.

**Why worker tests missed it**: `test_absent_field_defaults` patches `config.get_field` with `return_value=None` — a return that never occurs for this field (`get_field` exits instead). The mock encodes the wished-for contract, not the real one. My TC-3 runs the real `get_field` against a real config.md and caught it immediately.

**Established pattern not followed**: `_FIELD_DEFAULTS` already solves exactly this — see `"verbose-mode": "no"` registered at config.py:213-215 with the comment "*graceful default `no` so a config.md without the section reads as quiet (no sys.exit)*" (#13162). `context-threshold` needed the same registration (`"context-threshold": "70"`), and/or the reader must handle `SystemExit`.

**Required for re-verification**:
1. Absent `## Context Pressure` section must yield default-70 enforcement with the poller thread surviving (fix direction is worker's choice; `_FIELD_DEFAULTS` registration follows the #13162 precedent).
2. A regression test that exercises the REAL `config.get_field` against a real absent-section config.md (not a mocked return) — my TC-3 in `TEST-13335-tests.py` is reusable as-is.
3. Re-check the sibling claim: `test_reader_exception_defaults` (RuntimeError) is fine, but the unparseable-value path (`int("lots")` → ValueError inside the reader's try) genuinely IS caught — only absent-field is broken.

## AC walk

| AC | Result | Evidence |
|---|---|---|
| AC1 enforcement actor exists in event mode | PASS | TC-1/1b: `_enforce_context_pressure()` wired in `_poll_loop` after `update_health()`, own try/except; TC-2: real pressure file 72 ≥ real config threshold 55 → `intent=restarting`, `intent_set_at` stamped, `bootup_complete=False`, state persisted. Downstream respawn = pre-existing force-kill/auto-reboot machinery (harness.py:875-901 fires on intent+intent_set_at alone — field-flip is sufficient; same path as POST /agents/{role}/restart, battle-tested 2026-06-21 qa-wedge recovery) |
| AC2 threshold from config, default 70 | **FAIL** | TC-3: configured value respected (55 → fires at 55+, not at 54) BUT absent section → SystemExit kills poller thread instead of default-70 (see THE DEFECT) |
| AC3 doc defect corrected | PASS | event-mode-contract.md context-pressure bullet now names the real actor (health poller, 5s, config source, default, force-kill fallback, fresh-context respawn); context-pressure.md adds explicit loop-vs-event note. Comprehension 4/4 (below) |
| AC4 regression test exists | PASS (with a masking caveat) | `tests/test_13335_context_pressure_enforcement.py`, 20/20 green, pins fire-at/over + no-fire-under. Caveat: `test_absent_field_defaults` mocks the real behavior away — fold my TC-3 in on rework |
| AC5 guards | PASS | TC-6a already-restarting not re-armed (intent_set_at unchanged); TC-6c unbooted skipped; TC-6d missing/malformed pressure file fail-open (real files); `_NO_AUTO_REBOOT` early-return + kill-path `_no_reboot_restart` defense-in-depth confirmed in code; stale-pressure re-trip window defended by eager `bootup_complete=False` + #12244 fast-death backoff |

## Verifier real-chain test run (TEST-13335-tests.py)

12 passed, 1 failed (TC-3 = THE DEFECT). Full pytest output in this file's git history; failure:

```
FAILED ...::RealChainEnforcement13335::test_tc3_default_70_when_config_section_absent
E  SystemExit: 1
ERROR: Field 'context-threshold' not found in config.md
```

Worker suite: `tests/test_13335_context_pressure_enforcement.py` → 20 passed in 0.51s.

## Comprehension tests (CQ spec: tests/comprehension/13335_spec.json — verifier-reviewed, matches my independently-derived CQs 1:1)

Fresh sonnet agent, files only (event-mode-contract.md + context-pressure.md), no project context:

- CQ1 (actor in event mode): PASS — "harness health poller … flips your intent to restarting", explicitly NOT cycle_post.py.
- CQ2 (honoring + idle fallback): PASS — checkpoint at task boundary + halt; 60s force-kill if never observed.
- CQ3 (threshold source/default): PASS — config.md `Context Pressure / Threshold`, default 70.
- CQ4 (loop-mode path retained): PASS — Step 1b + cycle_post exit-42.

Zero misreads.

## Landing safety (TC-10)

- Base `main`, branch 4 behind (all 4 = post-cut state/doc commits incl. my own; far under the #13271 guard's 50).
- `git diff main...HEAD --diff-filter=D` → EMPTY (zero file deletions); the −1 line is the intentional contract-bullet replacement.
- No fleet/composed/state artifacts touched.

## Full static gate (TC-9)

Run on branch HEAD: see addendum below (run was in flight at verdict time; verdict is FAIL on TC-3 regardless of suite outcome).

## Out-of-scope observations (not reblocking findings for #13335)

- `.squidsquad/.harness-port` in this clone reads `8251` while the harness runs on `7373` (config + live /status agree on 7373) — a strict port-file-first boot probe falls back to polling mode falsely. Filed separately.

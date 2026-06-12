# QA-RESULTS-11512 — VERDICT: PASS (zero gaps)

**Issue**: #11512 (type:issue, severity:high, role:skill) — thin_launcher hardcodes `/loop` spawn prompt → agents always boot loop mode.
**PR**: #11518 (`squidsquad/task/11512` → main)
**Verified by**: verifier, 2026-06-12 18:20 on branch `squidsquad/task/11512`.
**Plan**: TEST-PLAN-11512.md. Bug = auto-approved (no human approval gate).

## AC walk (independent, from issue "Expected")

| AC | Verdict | Evidence |
|----|---------|----------|
| AC-1 launcher does NOT force loop mode (no `/loop` in spawned cmd) | **PASS** | `_SPAWN_PROMPT` replaces the `/loop {interval}m …` positional; unit `TestSpawnPromptIsModeNeutral` asserts no arg starts with `/loop` and `cmd[-1] == _SPAWN_PROMPT`. |
| AC-2 mode selection stays with boot Step 1 probe | **PASS** | `_SPAWN_PROMPT` text: "Execute your composed boot sequence starting at Step 1 (step:cycle/boot): probe harness reachability and proceed in whichever wake mode the probe selects. Do not pre-commit to a mode before the probe runs." |
| AC-3 dead `_get_interval` removed, no callers | **PASS** | Removed from `thin_launcher.py`; grep on branch shows only tests asserting `not hasattr(thin_launcher,'_get_interval')`. |
| AC-4 comprehension: fresh agent probes-first, no loop pre-commit | **PASS** | Live CQ (fresh sonnet agent, _SPAWN_PROMPT + boot Step 1 only): 5/5 correct — check-gh first, probe exit-code decides mode, harness-UP→EVENT + no /loop, arms Monitor, premature /loop forbidden. Preserved at `tests/comprehension/11512_spec.json`. |
| AC-5 no stall / regression | **PASS** | `test_thin_launcher.py` 31/31; `test_feat_9725_…_live.py` 3/3; canonical gate `tests/run_tests.py` 54/54 OK. |

## Test execution

- `python -m pytest tests/test_thin_launcher.py -q` → **31 passed** (55.5s)
- `python -m pytest tests/test_feat_9725_spawn_loop_registration_live.py -q` → **3 passed** (61.6s)
- `python tests/run_tests.py` (canonical gate) → **Ran 54 tests … OK** (50.4s)
- Comprehension CQ (sonnet fresh agent) → **5/5 correct**

## Notes / non-gaps

- **Full event-mode end-to-end live spawn** (real agent spawned via new launcher → arms Monitor under harness-UP) is NOT an AC of this bug — the AC is "launcher must not force loop mode; mode selection stays with Step 1," fully covered by command-shape (AC-1/2) + comprehension (AC-4). The broader event-mode smoke is its own BRIEFING priority (now unblocked by this fix). Not a ship gate.
- **Meta-confirmation of the bug**: this very QA session was spawned via the OLD `/loop` prompt with the harness UP — exactly the inverted-default the fix corrects.
- Pre-existing 18 `test_feat_9588` reds are #11503 test-debt (boot-bootstrap.md move); PR touches none of those files — independent, confirmed by changed-file set.
- DS review (PR): NO_FINDINGS, 5/5 invariants (DS-REVIEW-11512.md).

## Transition
pending-test → pending-ship. PR #11518 ready for DM to ship (merge brings fix + comprehension spec to main). No `review:human-required` label.

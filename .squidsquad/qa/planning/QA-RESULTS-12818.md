# QA-RESULTS-12818 — L2 PM: brief summary on no-action wakes

**Verdict: PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-19 23:13 · **Verifier:** qa · PR #12953 @ f834b3c02 · branch `squidsquad/task/12818`.

type:task (operator-pre-approved), role:skill. Touches LLM-consumed PM instruction →
CQ HARD GATE (AC5). Verified in isolated worktree `D:\Dev\Dev\sq-12818-verify`. Append-only.

## Fix summary
Adds an L2 PM directive to `references/roles/pm/SOUL.md` (Communication Style):
"No-action-wake reporting — brief summary only" — refines (does not replace) the L1
Soul User-Facing Communication rule; on a no-action wake PM keeps the user line brief
+ generic, no per-agent/issue/event-type/count enumeration; scoped to no-action wakes
only (real actions + internal logs unrestricted).

## AC walk (issue body; all PASS)
- **AC1 (source)** PASS — directive in L2 source `references/roles/pm/SOUL.md` (Communication
  Style), not edited in composed output. Diff confirms.
- **AC2 (compose consumption)** PASS — ran `compose.py deploy pm` in worktree → directive
  present in composed `.squidsquad/pm/CLAUDE.md` at line 205 (User-Facing/Communication-Style
  region). Verified content reaches deployed slot, not just source.
- **AC3 (no contradiction / prose-drift)** PASS — composed L1 User-Facing Communication rule
  intact (line 131-137: default one-liner + jargon-free term list); L2 directive states
  "refines (does not replace)", preserves the default one-liner and jargon-free constraint;
  §4 no-action-wake line (365) consistent. No contradiction — L2 narrows L1's "adapt freely"
  to "brief/generic" for PM.
- **AC4 (manifest)** PASS — no new `references/` file: diff = `references/roles/pm/SOUL.md`
  (existing) + `tests/comprehension/12818_spec.json` (under tests/, not references/).
  installer-files.txt correctly unchanged.
- **AC5 (comprehension HARD GATE)** PASS 5/5 — verifier-authored independent questions; fresh
  sonnet given ONLY the L1 rule + new L2 directive → all correct, zero anti-patterns
  (brief-generic; refuse to enumerate skill/#12408/×10; real-action unrestricted; internal
  logs unrestricted; default one-liner OK + reword short/generic/jargon-free). Skill also
  authored 12818_spec.json — CQ is verifier's lane (#9184); flagged to PM, non-blocking; ran my own.

## No-regression
- Full static gate run #1: 1 failure — `test_triage.py::TestTriageLiveSmoke::test_qa_rejected_returns_list`.
  **Confirmed FLAKY/environmental, NOT a #12818 regression:** TestTriageLiveSmoke is a "Live
  smoke test against the real repo (requires gh CLI)"; it makes real gh calls and flakes under
  concurrent gh load (this verifier was firing many gh transitions/comments/PR-views during the
  run). Proven: the test PASSES on origin/main (1) AND on the branch x2 (1 each) on re-run; and
  #12818 changes only PM SOUL.md prose — no triage code, no mechanism to affect it. Known live-test
  class (ref #12747/#12748). Static gate re-run: PASS (see below).
- Static gate re-run: **PASS — 4652 gated tests, 0 failures, 0 errors** (exit 0; the flaky live-smoke test passed on re-run, confirming the earlier failure transient). Only the 2 allowlisted #10360 known-failures.

## Non-blocking flags → PM
1. #12818 carries a double status-label (status:approved + status:pending-test) — hygiene; canonical for QA = pending-test.
2. Skill authored the CQ spec (CQ is verifier's lane #9184) — restored independence with my own run.
3. `compose.py deploy pm` emits a pre-existing `config.md: Dev Agents:`→`Workers:` deprecation WARNING (unrelated to #12818).

## Disposition
pending-test → pending-ship (DM). No closing keyword on PR #12953, no review:human-required → merge deferred to DM. Counter NOT bumped. TEST-PLAN-12818 + QA-RESULTS-12818 on main.

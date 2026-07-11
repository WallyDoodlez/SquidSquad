# QA-RESULTS-13369 — boot-drain work vs booting-liveness bound

**Issue**: #13369 (verifier-filed, severity:medium, type:issue)
**PR**: #13375 `squidsquad/task/13369`, head 6f85fca37 (4 files, +266/−14)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13369.md` (ACs = my own issue's remediation + regression directions)
**Verdict**: **FAIL — 1 finding (TC-1 residual surface). Back to In Progress.** Everything else passes; single doc-line fix.

## THE FINDING (TC-1 partial FAIL) — instructions.md:191 still teaches the fatal order

**Finding**: `references/roles/instructions.md:191` — the compose-consumed L2 one-line summary of the `event-mode-contract` sub-skill — still reads:

> "boot sequence (Case A — read working-state, branch on state, **drain initial events, advance cursor, emit `bootup-complete`**), …"

That is the pre-fix order (drain → announce), verbatim, on the pointer line every agent reads immediately BEFORE loading the fragment. It now contradicts the fragment it summarizes (step 4 = announce BEFORE drain, with the kill-hazard rationale). This line is inlined into every composed `.squidsquad/<role>/CLAUDE.md`, so all four agents' standing instructions carry the contradiction until it is fixed + recomposed. The PR body's claim "the numbered steps were the one surface teaching the fatal order" is what the sweep missed — the summary line is a second surface.

**Evidence**: `grep -n "bootup" references/roles/instructions.md` → line 191 (order: drain → advance → emit). Fragment (fixed): `event-mode-contract.md:37` step 4 announce-first. `docs/AGENT-RUNTIME.md`: zero bootup-order teaching (clean). Session-boot diagram: already booted → drain (clean).

**Impact**: an agent skimming its composed summary (or a composed CLAUDE.md that never re-deploys) re-learns drain-before-announce — the exact kill-window this issue exists to close. Doc-vs-doc contradiction on the load-bearing line.

**Required for re-verification**: reorder the one line at `references/roles/instructions.md:191` to announce-before-drain (e.g. "read working-state, branch on state, emit `bootup-complete`, drain initial events, advance cursor"). Source-only edit — composed outputs regenerate via the deploy machinery (never hand-edit composed files). Re-verify = this line + suite re-run.

## Stands on re-verify (no need to redo)

- **TC-2 PASS** — `progress_liveness()` booting branch (harness.py:500-538): signals consulted only past `BOOT_GRACE_SECONDS`; heartbeat must POSTDATE this spawn (`last_activity_at >= boot_ref`, generation-gap guarded) and be within `ACTIVITY_GRACE_SECONDS`; pauses ceiling-bounded (`booting-<pause>`); truly-inert → `wedged-boot-timeout` (**#13179 preserved**); no spawn reference → conservative `booting`. Worst-case wedge detection ~40m documented as accepted tradeoff.
- **TC-3 PASS** — `tests/test_13369_booting_liveness_activity.py` 11/11: incident shape, BOTH regression directions from my issue verbatim (heartbeats → NOT killed; inert → still killed), stale-deadline + pre-spawn-activity non-excuses, boundary/post-boot unchanged, source-level pins.
- **TC-4 PASS** — existing liveness suites (12460/13283/13335 families): 58/58 unchanged.
- **TC-5 PASS** — no consumer outside harness.py string-matches the new reason values; kill decision boolean-keyed.
- **TC-6 PASS** — CQ spec 13369_spec.json verifier-reviewed (5 Qs, matches my derived set); fresh sonnet agent on the fragment alone: **5/5 zero misreads** (announce-first + step placement, full kill-hazard chain, drain discipline unchanged, deploy-signal-in-drain + respawn re-emit, diagram agreement).
- **TC-7 PASS** — full static gate on 6f85fca37: **5266/0/0**.
- **TC-8 PASS** — zero deletions; 2 behind = my qa state commits (benign); no fleet/state artifacts.
- Fragment half of TC-1 PASS: contract steps 4/5 reorder correct with rationale; Case E deploy-signal parenthetical coherent (respawn re-emits; prior emission harmless).

## Notes (non-blocking)

- Zero Discussion comments on the issue itself — pickup + fix report live only in PR #13375's body and the transition. The PR is linked so the record is recoverable, but a one-line fix comment on the issue at handoff would keep the issue self-contained (protocol polish; flagging, not reblocking — the deliverable's ACs are unaffected).

---

## ROUND 2 (re-verify) — 2026-07-11 — VERDICT: PASS -> pending-ship

**Round-2 head**: e1a10a593 (`squidsquad/task/13369`). **Delta from round-1 tip 6f85fca37**: exactly one line — `references/roles/instructions.md:191`. Confirmed via `git diff --stat 6f85fca37 e1a10a593 -- references/scripts/harness.py references/sub-skills/common-events/event-mode-contract.md tests/comprehension/13369_spec.json tests/test_13369_booting_liveness_activity.py` = **EMPTY** (harness / fragment / CQ-spec / suite byte-identical to round-1).

### TC-1 (the round-1 finding) — FIXED, PASS
- `references/roles/instructions.md:191` now reads `...branch on state, emit \`bootup-complete\`, drain initial events, advance cursor` — announce-before-drain, matching the fixed fragment (Case A step 4). Commit e1a10a593.
- Repo-wide re-grep for the fatal order (`drain...bootup-complete`): only remaining hits are (a) composed `.squidsquad/*/CLAUDE.md` + `.linked.md` outputs — regenerate via deploy post-merge, never hand-edited (project rule); (b) my own state/planning files; (c) historical pm/skill iteration logs. **No instructional SOURCE surface teaches the fatal order.**

### Stands from round-1 (files byte-identical, no re-run needed to re-establish)
- **TC-2 PASS** — harness booting branch; #13179 preserved.
- **TC-5 PASS** — no reason-string consumers outside harness.py.
- **TC-6 PASS** — CQ 5/5 zero misreads (fragment + 13369_spec.json unchanged).

### Re-run this session (fresh evidence)
- **TC-3 + TC-4 PASS** — `pytest` liveness suites **61/61** (new `test_13369_booting_liveness_activity.py` 11/11 + 12460/12492/13283/11723 families).
- **TC-7 PASS** — full static gate **5297/0/0 DETERMINISTIC** across 2 clean full runs (163s + 172s).
  - **Flaky observation (separate issue, NOT a #13369 blocker)**: the FIRST full run reported 5268/1 — `tests/test_wizard_13337_deny_list.py::TestCli::test_cli_unknown_flag_exits_2` (subprocess CLI, returncode 1 vs expected 2). PASSED in isolation and on the full re-run (5269/0). It is a **#13337** test (already shipped), a subprocess exit-code race under full-suite load, unrelated to the #13369 surface. Because the full re-run passed *with* the #13369 test present, #13369 does not deterministically pollute it. Filed separately to skill.
- **TC-8 PASS** — net diff vs origin/main = exactly the 5 #13369 files (instructions.md, harness.py, event-mode-contract.md, 13369_spec.json, test suite); 0 behind main; zero deletions; no fleet/state artifacts.

### Actions
- PR #13375 squash-merged to main (c85b584f6). #13369 pending-test -> pending-ship (DM owns version/counter/tag). Filed flaky #13337 test separately.

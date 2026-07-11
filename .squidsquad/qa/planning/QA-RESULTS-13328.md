# QA-RESULTS-13328 — retire loop-interval prompt (event-mode default, loop=fallback)

**Issue**: #13328 (type:task, priority:medium, PM-specced)
**PR**: #13420 `squidsquad/task/13328`, head 055acdcfd (7 files: wizard.py -103 net, config.py +6, SKILL.md +3/-2, new 13328_spec.json, new test_wizard_13328_interval_silent_default.py +102, test_wizard.py -83, test_feat328_coverage.py -77)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13328.md`
**Verdict**: **PASS -> pending-ship.**

## AC walk
- **AC1 PASS** — `validate_interval` + `cmd_validate_interval` + `validate-interval` CLI tombstoned (wizard.py:1254/3054); no "How often should" prompt.
- **AC2 PASS** — `build_config_md` emits `## Iteration Interval / Minutes` (30) + `## Context Pressure / Threshold` (70); config.py FIELD_MAP `interval->(Iteration Interval,Minutes)` + `_FIELD_DEFAULTS interval=30`. **Independent E2E**: NO `## Loop` heading; Minutes=30, Threshold=70. Fixes the latent dead-`## Loop`-section bug (interval/threshold were written under a heading config.py never read — same class as #13355 PR Flow).
- **AC3 PASS** — `post_setup_summary` has no `Loop: N` line; only event-driven "cycle" language.
- **AC4 PASS** — TC-49..TC-52 removed with tombstone comments (test_wizard.py:309, test_feat328_coverage.py:60); new `test_wizard_13328_interval_silent_default.py` asserts `validate_interval`/`cmd_validate_interval` gone + `validate-interval` CLI gone; 284 wizard tests pass; no orphaned refs.
- **AC5 PASS (CQ)** — LLM-consumed `docs/INSTALLER-RUNTIME.md` §5/§8/§9 (unchanged by this task — the prompt removal made the existing messaging consistent). 13328_spec 4 Qs verifier-reviewed; fresh Sonnet agent on the named sections only -> **4/4 zero misreads** (event-mode default; loop=fallback-not-mode; 30m silent default; day-to-day sentence must not imply a timer).
- **Static gate** — combined state (branch shares wizard.py/config.py/SKILL.md with #13355/#13339/#13397 on main): local merge origin/main CLEAN (0 conflicts); combined build_config_md has NO `## Loop` and BOTH `## Iteration Interval` AND `## PR Flow`; combined gate **5308/0/0**.

## Skill's two ship-comment flags
1. **FEAT-328-TEST-PLAN.md TC-06 '## Loop'** — MISLABELED. That file is SKILL-owned (`.squidsquad/skill/planning/`) and is the historical plan for the ORIGINAL wizard feature ("FEAT-328 Intent-driven setup wizard"), NOT issue #13328 (FEAT-328 != #13328). Outside verifier lane to edit -> routed back to skill (low; refresh-or-leave). No verifier-owned #13328 artifact lists `## Loop`.
2. **SKILL.md:393 'PR Flow' under `## Flags`** — CONFIRMED real residual #13355 drift (latent dead-section, same class as this task's `## Loop` fix). **FILED #13421 -> skill.** Not a #13328 blocker.

## Actions
- PR #13420 squash-merged to main. #13328 pending-test -> pending-ship (DM ships). Filed #13421.

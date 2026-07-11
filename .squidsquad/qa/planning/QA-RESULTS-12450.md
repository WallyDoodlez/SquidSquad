# QA-RESULTS-12450 — Installer auto-detect the project's unit-testing strategy

**Verdict: PASS — zero gaps.** TASK (L3 software-dev domain). PR #13281 merged (squash, +additions-only re-verified).

## AC walk (independent)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | detected framework + location + run command reach the worker's composed CLAUDE.md (L3 behavior + L4 seed) | PASS — `detect_test_strategy('.')` on THIS repo → `{framework: pytest, run_command: pytest, location: tests/, detected: true}`; L3 line present in all 5 worker variants |
| AC2 | worker references the detected strategy — no inventing a mismatched framework/layout | PASS — L3 behavior + **CQ comprehension PASS** (fresh agent followed jest/__tests__/, refused its preferred pytest) |
| AC3 | undetectable → installer ASKS the human (graceful), not a silent wrong guess | PASS — `detect_test_strategy(emptydir)` → `detected: false`; WIZARD.md Step 3b case 3 "ask, do not guess" with a concrete prompt |
| AC4 | non-software-dev domains unaffected | PASS — Step 3b is software-dev-preset-ONLY (design/minimal skip it); L3 content only in worker/{skill,web,ios,android,fullstack} |
| AC5 | tests for detection logic (fixture repos → correct detection) | PASS — test_repo_scan.py + the 3 other test files = 108 passed; + my real/empty-repo live checks |

## Evidence
- Code: `repo_scan.py` (`detect_test_strategy`/`_detect_test_location`/`_detect_test_run` — config/manifest/marker scan, language-default + Makefile fallback ordering), `wizard.py` (`set-test-strategy`, scan-summary Test-Strategy line), WIZARD.md Step 3b (the operator dialog), L3 worker instructions ×5.
- **Independent live detection**: ran `detect_test_strategy` on this real pytest repo (correct) and an empty tmpdir (`detected: false`).
- skill tests: test_repo_scan.py + test_wizard_runbook.py + test_12450_l3_test_strategy_behavior.py (structural: behavior present in all 5 stacks, inside the domain block) + test_12450_test_strategy_l4_seed.py = **108 passed**.
- **QA-authored CQ spec** (`tests/comprehension/12450_spec.json`, #9184): fresh sonnet agent (id a8b03a01c983ce908) given ONLY the L3 behavior + a sample L4 '### Testing Strategy' (jest/npm test/__tests__/) → 2/2 correct, zero must_not: used the recorded strategy (CQ1) and refused to substitute its preferred pytest/spec/ (CQ2). The structural test confirms the text is present; this CQ confirms a fresh worker COMPREHENDS + follows it.

## Merge safety
- Branch predated #13275/#13276/#13280 → its raw diff "deleted" the just-landed TUI/git_ops work (staleness). Merged current main into the branch first, re-verified `--diff-filter=D` is EMPTY (+additions-only) and config.md/TUI/#13276 preserved, THEN merged. The live #13271 guard adds protection. See [[learning-verify-squash-diff-additions-only-behind-branch]].

Status: pending-test → pending-ship.

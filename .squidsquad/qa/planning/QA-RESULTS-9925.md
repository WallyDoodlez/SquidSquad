# QA Results — #9925 (L1/L2/L3/L4 inter-agent responsibility layering)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 20:31 cycle 749 (re-verification after AC6/AC8/AC9/AC12 fixes; supersedes cycle-747 FAIL)
**PR**: #9944 (branch `squidsquad/task/9925`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

Re-verification after skill landed commit `f805db4b` to fix the four AC gaps from cycle-747 rejection.

## AC walk (CONTEXT-9925.md, 12 ACs)

| AC | Result | Evidence |
|----|--------|----------|
| AC1 — `agent-boundaries.md` exists | PASS | (unchanged from cycle 747) |
| AC2 — `compose.py` modifications | PASS | (unchanged) |
| AC3 — manifest entries in includes.yml + includes-events.yml | PASS | (unchanged) |
| AC4 — composed PM CLAUDE.md has L1 + roster (4 entries) + own L2 | PASS | (unchanged) |
| AC5 — 4 L2 `responsibility.md` files matching D4 template | PASS | (unchanged) |
| **AC6 — All 10 D5 memory absorptions with lineage tags** | **PASS** | After `git pull` on `squidsquad/task/9925`, `grep "absorbed from feedback_" references/sub-skills/roles/pm/prohibitions.md` returns the 3 previously-missing entries: `<!-- absorbed from feedback_fix_pm_bugs_immediately -->`, `<!-- absorbed from feedback_manual_agents -->`, `<!-- absorbed from feedback_dont_ask_before_verifying -->`. Combined with the 7 already in `responsibility.md` files, **10 of 10** D5 absorptions present. |
| AC7 — 20 L3 stub files | PASS | (unchanged) |
| **AC8 — 5 L4 stubs in BOTH seed AND live locations** | **PASS** | Seed templates (`references/sub-skills/project/`) still present (unchanged). Live stubs (`.squidsquad/project/`) now also present — `ls .squidsquad/project/*-responsibility.md` returns all 5 files: `dev/dm/pm/qa/shared-responsibility.md`. |
| **AC9 — Composed PM CLAUDE.md contains pm + shared L4; no qa/dm/dev L4** | **PASS** | Verified transitively via AC12's `test_ac9_pm_compose_includes_pm_and_shared_l4_not_others` — now passes. The L4 stubs being present means compose can pick them up via the filename-prefix routing at compose.py:393–419. |
| AC10 — byte-identical compose with agent_compose disabled | PASS | (unchanged) |
| AC11 — degraded modes | PASS | (unchanged) |
| **AC12 — Regression test passes** | **PASS** | `pytest tests/test_agent_boundaries.py` → **53 passed in 0.49 s** (was 47/53 in cycle 747). All 6 previously-failing tests now pass with the AC8 live stubs in place. |

## Tests

`pytest tests/test_agent_boundaries.py` → **53 passed in 0.49 s**. Matches skill's claim and the AC12 contract.

## Process insight (recurring root cause)

Skill identifies the same `git_ops.py commit_code` filter root cause that caused #9926's AC6 mis-claim — `.squidsquad/` paths get stripped from feature-branch commits. The AC8 live stubs (which live in `.squidsquad/project/`) hit the exact same trap on the first attempt: skill created them via the cycle workflow but they only landed on main via `cycle_post.py` state-commit, not on the PR's feature branch. Skill correctly bypassed the filter on commit `f805db4b` by `git add`-ing and committing the files directly on the branch.

This is the **second clear instance** in the same QA session of the same root cause. The fix #9946 will track is the right home for surfacing this systematically. Until #9946 lands, dev agents need to manually verify their pickup-comment claims appear on the feature branch (not just main) — same recommendation as last cycle.

## Net

All 12 ACs satisfied. The two-cycle reject-then-fix loop validated that the zero-gap gate caught two distinct categories of issues (AC6 absorption miss + AC8 file path placement) that would have shipped incomplete L1/L2/L3/L4 layering otherwise. The fix is small (5 stub copies + 3 lineage tag additions in an existing file) and the regression suite proves the full integration.

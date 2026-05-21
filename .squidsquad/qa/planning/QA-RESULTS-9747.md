# QA-RESULTS-9747 — Eliminate [ROLE] placeholder in polling fragments

**Issue**: #9747
**PR**: #9771
**Branch**: squidsquad/task/9747
**Verified by**: qa-lead
**Date**: 2026-05-21
**Verdict**: **PASS**

## 1. Live-system pytest

```
8 passed in 0.74s
```

| TC | Covers | Result |
|----|--------|--------|
| TC-1 | AC (no `[ROLE]` placeholders) parametrized for `dev`/`pm`/`qa`/`dm` | 4/4 PASS |
| TC-2 | `cycle.py` exposes `status-bar-self` subcommand + `status_bar_self` callable | PASS |
| TC-3 | `status_bar_self` reads `SQUIDSQUAD_ROLE` and writes current-state | PASS |
| TC-4 | `status_bar_self` exits non-zero on missing/empty/whitespace `SQUIDSQUAD_ROLE` | PASS |
| TC-5 | dev's `tests/test_cycle.py` 24/24 PASS | PASS |

## 2. AC walk

AC (OR'd in issue body): "polling fragments no longer contain placeholders needing runtime LLM substitution **OR** documented as accepted technical debt."

Skill chose the elimination path (option a). All 4 polling fragments (`references/sub-skills/roles/{dev,pm,qa,dm}/ralph-loop-overview.md`) now contain ZERO `[ROLE]` placeholders, verified via TC-1.

The deterministic replacement is `python references/scripts/cycle.py status-bar-self "phase" "desc"`, which reads `SQUIDSQUAD_ROLE` from env (set by `thin_launcher.py:135` at spawn) and delegates to the existing `status_bar(role, phase, desc)`. Fails loudly on missing env per TC-4 — no silent file-to-wrong-path risk.

## 3. Setup & Upgrade Sync Check

- New config values: N/A
- New files/directories: N/A
- Modified template structure: minor — `cycle.py` gains one subcommand (`status-bar-self`)
- Added/removed sub-skills: N/A
- Changed role composition: N/A
- Upgrade path: zero-touch. Agents on next reboot use the new fragment text + helper. Existing agents on the old text still work (the helper is additive; `status-bar <role>` still exists for back-compat).

## 4. Decision

**Verdict**: PASS.

- Promote `TEST-9747-tests.py` → `tests/test_feat_9747_role_placeholder_elimination_live.py`
- Comment QA verdict on PR #9771
- Auto-merge via harness
- Transition #9747 pending-test → pending-ship
- Increment `Shipped Since Last Bump` 9 → 10 (triggers DM version-bump if Ship Threshold = 10)

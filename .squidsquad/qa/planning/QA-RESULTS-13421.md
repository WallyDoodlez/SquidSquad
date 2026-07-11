# QA-RESULTS-13421 — SKILL.md migration lists PR Flow under ## Flags (residual #13355 drift)

**Issue**: #13421 (type:issue, severity:low — verifier-filed during #13328; auto-approved)
**PR**: #13435 `squidsquad/task/13421`, head (2 files: SKILL.md +4/-1, test_feat_2495_upgrade_rewrite.py +29)
**Verdict**: **PASS -> pending-ship.**

## Fix (resolves my filed finding)
SKILL.md v1->v2 migration checklist: dropped `PR Flow` from the `## Flags` line; added `## PR Flow` (Enabled: yes, invariant #9478/#13355) + `## Auto Merge` (Enabled, merge gate #13355) as their own sections — the sections config.py FIELD_MAP actually reads. Mirrors #13328's `## Loop` -> `## Iteration Interval`/`## Context Pressure` repoint.

## Verification
- **Resolves finding** — combined SKILL.md checklist now lists Iteration Interval / Context Pressure / Auto Merge / PR Flow all as read-sections; `## Flags` carries none of them. Consistent with build_config_md + FIELD_MAP.
- **Regression PROVEN to catch the bug** — `test_13421_migration_checklist_matches_shipped_config_sections` asserts (a) `## Flags` has no `PR Flow`, (b) checklist includes `## PR Flow`, (c) includes `## Auto Merge`. Confirmed against origin/main's OLD SKILL.md (line 393: PR Flow under `## Flags`, no `## PR Flow`/`## Auto Merge`) -> FAILS on old, PASSES on new.
- **No CQ** — mechanical checklist-section correction.
- **Landing** — branch 1 behind main + shares SKILL.md with #13328 (on main). COMBINED state (local merge origin/main, no push): 3-way CLEAN; combined checklist carries BOTH #13328's Interval/Pressure AND #13421's PR Flow/Auto Merge, no dead `## Flags` entries; combined static gate **5309/0/0**.

## Actions
- PR #13435 squash-merged to main. #13421 pending-test -> pending-ship (DM ships). Closes the residual #13355 drift I surfaced during #13328 verification -- the full dead-section class (## Loop + ## Flags PR Flow) is now closed in the migration checklist. (Related preventive-test-gap finding filed as #13434.)

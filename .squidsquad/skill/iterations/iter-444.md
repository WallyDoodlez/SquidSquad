# Iteration 444 — #11503 Group C triage

**Cycle**: 1634 | **Date**: 2026-06-12 | **Mode**: /loop polling (cron 0bdc0ae0) | **Branch**: main

## Outcome
Triaged the 4 "possibly-real masked regressions" (Group C) on umbrella #11503. No code change — investigation + report. Fixes correctly deferred until PR #11504 merges.

## Queue state
Top-2 work-queue items operator-blocked: #10690 (gated on E7) ← #10686 (E7 = manual smoke, AC1 requires human-operator participation). First pickable autonomous item = #11503 (high-sev, bug-class).

## Triage verdicts
- **test_statusline_schema → REAL** (deploy-sync): references/statusline.sh has #11144 G10 block; .squidsquad/statusline.sh stale. Fix: cp.
- **test_manifest_registry + test_feat328_coverage → REAL** (same root cause): capabilities/ dir deleted 2026-05-27 (registry empty []), but dm/manifest.yaml:34-35 still `requires_sub_skills.any_of: [local_delivery]` — orphan ref the cleanup missed. Fix: remove the requires_sub_skills block. test_feat328 ALSO has a stale assertion (asserts old capability set exists).
- **test_comms_sub_skills → STALE** (asserts pre-frontmatter '## heading'; v2 sources have YAML frontmatter). Reclassified Group A.

## Net
Group C resolved: 2 real (statusline sync; dm-manifest orphan capability) + 1 mixed + 1 stale. The dm-manifest orphan is a genuine data inconsistency masked by the dead gate.

## Next
- On PR #11504 merge: execute Group C fixes (each removing its KNOWN_FAILURES entry), then Groups A/B.
- #10686/#10690 remain operator-paced.

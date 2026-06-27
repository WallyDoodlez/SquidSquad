---
type: learning
tags: [verification, merge, incident, squash]
created: 2026-06-27
author: qa
---

# Before squash-merging a long-lived/behind feature branch, confirm the squash diff is +additions-only

A squash-merge of a feature branch cut from a clone that is **far behind origin/main** can record a **stale tree as truth** and silently **revert every commit main gained since the branch's base** — alongside the intended feature. This is the #13271 SEV-1 class: PR #13269 (#12801 TUI), cut ~154 commits behind, squashed and would have reverted ~155 commits of shipped fleet work (config.md deleted, all composed CLAUDE.md reverted, vault + QA-RESULTS removed). DM caught it and reverted f36155a60; fleet recovered.

**Merging origin/main into the branch first is necessary but NOT sufficient.** I did merge main into the land branch before squashing — but the merge reported only **"5 files changed"**, which for a branch supposedly 154 commits behind is a glaring red flag the merge/squash base was off (a truly-behind branch pulls in far more). I missed that signal and squashed anyway.

**How to apply** (verifier merge gate, before `git_ops.py pr-merge`):
- After bringing main into the branch, **sanity-check the merge scope**: a behind branch should absorb a *large* delta. A suspiciously small "N files changed" means the merge did not actually incorporate current main — STOP.
- **Inspect the squash/PR diff against current main before merging**: `git diff origin/main <branch> --stat | grep -E '^ .*\| +[0-9]+ -'` (or check the `--diff-filter=D` set). For a pure feature add, the diff must be **+additions-only** — ANY deletion of files outside the feature's declared scope (config.md, composed `CLAUDE.md`, vault, settings.json, unrelated tests) means the branch carries a stale tree → route back, do NOT merge.
- Prefer a re-land from a **fully-current clone** (re-apply only the additions on top of HEAD) over re-squashing a long-behind branch.
- The feature can be verified-good (8/8 ACs) and still be un-landable — verification PASS ≠ merge-safe. The landing is its own gate.

Related: [[learning-sibling-pr-additive-test-conflict-keep-both]], [[feedback_verify_fresh_fetch_all_refs]].

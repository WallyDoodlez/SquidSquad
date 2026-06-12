---
type: learning
tags: [merge, cutover, reconciliation, compose, tests, model-migration, 11331]
created: 2026-06-12
updated: 2026-06-12
owner: skill-lead
status: active
confidence: high
source: observation
links: [learning-ship-gate-squash-proof-window, pattern-stale-ac-vs-canonical-arch, decision-branch-per-feature-workflow]
---

## Context

The v0.44.0 cutover (#11331): a 154-commit polish-session branch was held
for days while ~12 independents landed on `main` touching the same L1-L3
sources the polish session restructured. At the operator cutover signal,
`origin/main` was merged into the branch (NOT rebased — standing rule) and
16 conflicts resolved before the bundle PR went CLEAN/MERGEABLE.

## Lessons (reusable for the next long-held-branch cutover)

1. **Favor the restructure-side for source conflicts.** The held branch is
   the comprehensive restructure; main-side independents touched the same
   surface but in pre-restructure form. Resolve L1-L3 source conflicts to
   the branch (`--ours`). PM's "favor polish-side semantics" was exactly
   this.

2. **Never hand-merge generated artifacts — recompose.** The 8 composed
   `CLAUDE.md`/`.linked.md` were conflict-cleared then regenerated via
   `compose.py deploy-all`. Composed output is deterministic from sources;
   it came out byte-stable to the branch HEAD because main's deltas were
   scripts/docs, not composed sources.

3. **Manifests merge as UNION, not side-pick.** `installer-files.txt` taken
   `--ours` would have dropped main's newly-added installer paths → broken
   install. Keep the auto-merged union body; recompute any header count;
   verify every path exists on disk.

4. **Tests must match the MERGED runtime, not either branch wholesale.**
   Two branches carried divergent internal APIs for the same behavior
   (`_assemble_slot` on main vs `_extract_inline_ops` on the branch). The
   branch's mechanism won the merge → main's dead-API test was removed
   (behavior already covered by the branch's own test + comprehension spec).

5. **Model-version splits: base the test on the side that migrated, overlay
   the orthogonal change.** `test_harness.py` was model-A (in-flight) on the
   branch but model-B (ack-cursor) on main; the merged runtime was model-B.
   Took main's model-B test file, then overlaid the branch-only
   `target_role→target_alias` rename + ported the branch's model-B
   event_poll tests. Don't `--ours` a test file just because the rest of the
   branch is authoritative.

6. **`run_tests.py` is a curated subset — ungated tests hide failures
   (#11394).** Pre-existing failures in `test_cycle_pre` / `test_event_mode_fragments`
   only surfaced when running the affected files directly during
   reconciliation. **Baseline each failure against the pre-merge branch HEAD**
   (`git show <branch-HEAD>:<file>`) to prove pre-existing vs merge-induced
   before deciding whether to fix or hand to QA.

## Discipline that paid off

- Do the reconciliation merge ONCE against a frozen release-main at the
  gated cutover — not speculatively while main is still moving.
- Keep the reconciliation commit as the stable QA/DM target: do NOT push
  operational-state (working-state/iter-log) commits after QA starts
  verifying that HEAD.

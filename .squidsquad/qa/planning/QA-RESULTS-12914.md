# QA-RESULTS-12914 — tracker.py transition() leaves stale status labels

**Verdict: PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-19 23:21 · **Verifier:** qa · PR #12970 @ ac61645f0 · branch `squidsquad/task/12914`.

Bug (type:issue/medium, auto-approved), filed by dm. tracker.py code → no CQ.
Verified in isolated worktree `D:\Dev\Dev\sq-12914-verify`. Append-only.

Directly relevant: fixes the stale-label class I hit live this session on #12818
(post-transition approved+pending-ship) and DM saw on #12909.

## Fix summary
(1) `transition()` now ALWAYS queries live `status:*` labels and strips all except the
target (single-status invariant), on both normal and forced paths — the old normal path
only removed `from_label`, which let stale labels accumulate. Falls back to `[from_label]`
only on an empty live-query (API failure). (2) New `repair-status-labels` command cleans
EXISTING pollution: dry-run default, `--apply` executes, SAFE set (closed+shipped) auto-
repaired, AMBIGUOUS set (closed, no shipped) skipped unless `--include-unshipped`.

## AC walk (derived from root-cause + remediation; all PASS)
- **AC1 (single-status invariant)** PASS — transition() unconditional
  `live_status=_get_issue_status_labels(number)`; `remove_labels=sorted(live_status-{to_label})`
  else `[from_label]`. Idempotent re-transition removes nothing. Test:
  test_nonforced_swap_queries_live_labels_for_single_status_invariant +
  test_forced_swap_strips_multiple_stale_status_labels.
- **AC2 (repair tool)** PASS — **independent live dry-run** against the real forge:
  `repair-status-labels` → "0 closed to repair, 198 ambiguous (no shipped) SKIPPED" (no
  mutation, safe default). Units: dry_run_plans_safe_set_only_no_edits, no_shipped_skipped_by_default,
  apply_keeps_shipped_strips_pending_ship, apply_reduces_multilabel_to_shipped (#9873 3-label case),
  include_unshipped_strips_only_the_orphan, idempotent, gh_list_failure_returns_empty (fail-safe),
  adapter_path_safe_set.
- **AC3 (regression tests)** PASS — test_12914_status_label_repair.py + updated
  test_12475_force_bypasses_legality.py → 28 passed.
- **AC4 (no regression)** PASS — full static gate **PASS — 4663 gated tests, 0 failures, 0 errors**
  (exit 0). The transition() hot-path change (extra live-label query per transition; skill notes
  transitions are low-frequency) does not break legal flows; only 2 allowlisted #10360 known-failures.
- **(Optional item 3 — work_queue exclude closed-no-PR)** NOT implemented; explicitly optional in
  the remediation → acceptable.
- **No CQ** — tracker.py code only.

## Follow-up (operational, NOT a code gap) → DM
The one-time cleanup of the existing ~198 AMBIGUOUS closed pending-ship issues is a gated DM/ops
action: run `tracker.py repair-status-labels --include-unshipped --apply` AFTER DM verifies none
are genuinely awaiting delivery (#9837 closed-but-undelivered). The tool correctly does NOT auto-
strip these (auto-stripping maybe-undelivered issues would be dangerous); the SAFE auto-cleanable
set is currently 0. AC1 prevents all future accumulation regardless. DM's work_queue pollution
clears once this repair is run.

## Disposition
pending-test → pending-ship (DM). No closing keyword on PR #12970, no review:human-required → merge
deferred to DM. Counter NOT bumped. TEST-PLAN-12914 + QA-RESULTS-12914 on main.

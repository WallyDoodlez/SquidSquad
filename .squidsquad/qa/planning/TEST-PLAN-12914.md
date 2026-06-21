# TEST-PLAN-12914 — tracker.py transition() leaves stale status labels

Bug (type:issue/medium, auto-approved), filed by dm. PR #12970, branch
`squidsquad/task/12914`, role:skill. No explicit AC list → ACs derived from the
two-defect root-cause + remediation directions. tracker.py code → **no CQ**.
Verified in isolated worktree `D:\Dev\Dev\sq-12914-verify`.

Directly relevant: this is the stale-label class I observed live this session on
#12818 (post-transition approved+pending-ship) and DM saw on #12909.

## Derived ACs
- **AC1 (prevention — single-status invariant):** `transition()` strips ALL prior
  `status:*` labels before applying the target, on BOTH the normal and forced paths
  (no issue ever carries 2+ status labels). Falls back to `[from_label]` only if the
  live-label query returns nothing (API failure / label-less). Idempotent re-transition
  removes nothing.
- **AC2 (repair tool):** `repair-status-labels` command cleans EXISTING pollution —
  dry-run by default (no mutation); `--apply` executes; SAFE set (closed + `status:shipped`
  + stale `pending-ship`) → strip non-shipped labels (repaired by default); AMBIGUOUS set
  (closed, NO `shipped`) → SKIPPED unless `--include-unshipped` (the #9837 closed-but-
  undelivered safety); fail-safe (gh failure → empty, no edits).
- **AC3 (regression tests):** test_12914_status_label_repair.py + updated
  test_12475_force_bypasses_legality.py (non-forced single-status invariant case).
- **AC4 (no regression):** full static gate; the transition() hot-path change (now always
  queries live labels) does not break legal transition flows.
- **(Optional, item 3 — work_queue exclude closed-no-PR):** NOT implemented; explicitly
  optional in the remediation → acceptable.

## Test cases / evidence
- **TC1 (AC1)** — read transition() diff: now `live_status=_get_issue_status_labels(number)`
  unconditional; `remove_labels=sorted(live_status-{to_label})` else `[from_label]`. +
  test_nonforced_swap_queries_live_labels_for_single_status_invariant.
- **TC2 (AC2 live)** — INDEPENDENT live dry-run against real forge: `repair-status-labels`
  → "0 closed to repair, 198 ambiguous (no shipped) SKIPPED" (no mutation; safe default).
  Cross-check: gh closed pending-ship count ≥100 (capped). Tool classifies + dry-runs correctly.
- **TC3 (AC2 units)** — test_dry_run_plans_safe_set_only_no_edits, test_no_shipped_skipped_by_default,
  test_apply_keeps_shipped_strips_pending_ship, test_apply_reduces_multilabel_to_shipped (#9873 case),
  test_include_unshipped_strips_only_the_orphan, test_idempotent, test_gh_list_failure_returns_empty,
  test_adapter_path_safe_set.
- **TC4 (AC3)** — 28 tests (12914 + 12475) → all pass.
- **TC5 (AC4 no-reg)** — full run_tests.py static (pending — see QA-RESULTS).

## Follow-up (not a code gap)
The one-time cleanup of the existing ~198 AMBIGUOUS closed pending-ship issues is a gated
DM/ops action: `repair-status-labels --include-unshipped --apply` AFTER DM verifies none are
genuinely awaiting delivery (#9837). Correctly NOT auto-run by the tool (auto-stripping
maybe-undelivered issues would be dangerous). AC1 prevents future accumulation regardless.

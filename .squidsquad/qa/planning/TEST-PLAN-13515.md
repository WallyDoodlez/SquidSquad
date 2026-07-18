# TEST-PLAN-13515 — status:blocked (owned-but-parked, distinct from in-progress)

**Source**: GitHub task #13515 body (Acceptance Criteria AC1-AC6, including PM's endorsed AC5 tightening in Discussion).
**Derived without reading the PR diff first for AC scope — re-derived from the issue body.**

## Acceptance Criteria (from issue body)

- **AC1**: canonical spec (SKILL.md + tracker.py docstring) documents the new blocked status, semantics, and legal transitions.
- **AC2**: block-and-continue guidance (SOUL.md Never Stop + event-mode-contract Case D) updated so a still-owned blocked task is parked via the new status, not left in-progress.
- **AC3 (code)**: tracker.py accepts in-progress <-> blocked (assignee authority), rejects illegal transitions, all existing transitions unaffected (regression test).
- **AC4 (observability)**: pipeline-sentinel excludes `blocked` from halt detection AND flags a role holding >=2 `status:in-progress` as a double-pickup anomaly.
- **AC5 (CQ, PM-tightened)**: a fresh agent, given ONLY the updated block-and-continue guidance (SOUL.md + event-mode-contract.md), given "you implemented #N but are now blocked on a PM-authored AC while still owning it," must transition #N to `status:blocked` (not in-progress, not pending-*) and continue to its next item, unprompted.
- **AC6**: doc-first gate honored — Phase-1 spec PM-reviewed before Phase-2 code was written.

## Test Cases

### TC-1 (covers AC1): Taxonomy documentation
- **Steps**: Diff SKILL.md status table + tracker.py module docstring against origin/main.
- **Expected**: `status:blocked` documented with owned-but-parked semantics and legal transitions.

### TC-2 (covers AC2): Soul + event-mode-contract guidance
- **Steps**: Diff `references/roles/SOUL.md` (Never Stop section) and `event-mode-contract.md` (Case D) against origin/main; confirm composed `.squidsquad/*/CLAUDE.md` files match the source edit.
- **Expected**: Both updated with matching, internally-consistent guidance; distinguishes `blocked` from `in-progress` and `pending-*`.

### TC-3 (covers AC3): LIVE, UNMOCKED transition round trip — DECISIVE
- **Steps**: Create a real disposable GitHub issue via `tracker.py create-issue`, transition it through `open -> in-progress -> blocked -> in-progress` using the REAL `tracker.py transition` CLI (not the worker's mocked `_check_authority`/`_run_list` unit tests).
- **Expected**: Each transition succeeds; the issue's live labels reflect `status:blocked` then `status:in-progress`.
- **Result**: **FAILED.** The `in-progress -> blocked` transition crashed with `CalledProcessError` — `gh issue edit 13598 --add-label status:blocked --remove-label status:in-progress` exited 1. Root cause: `status:blocked` does not exist as a real label on the repo (`gh label list` confirmed — full 45-label list has no `status:blocked` entry, only a pre-existing unrelated `status:on-hold`). `wizard.py`'s label-provisioning source (`build_label_inventory`'s backing color/description maps, ~line 2514/2551) was never updated to include `status:blocked` — so `ensure_labels()` never creates it, on this repo or any fresh install.

### TC-4 (covers AC4): pipeline-sentinel changes
- **Steps**: Diff `pipeline-sentinel.md` against origin/main.
- **Expected**: `status:blocked` excluded from halt detection; new "double-pickup anomaly" section (4g) for >=2 `status:in-progress`.
- **Result**: PASS — both present, well-integrated with the existing halt-detection/tiered-response structure. (Minor non-blocking observation: the new `gh issue list --label status:in-progress --limit 50` query shares the same unbounded-growth risk class as #13555, though far less likely to matter at in-progress-item scale than it did for the full 165+ open-issue set — not filed, noted only.)

### TC-5 (covers AC5): Comprehension gate — fresh agent, files only
- **Steps**: Spawned a fresh general-purpose agent, given ONLY SOUL.md + event-mode-contract.md, posed PM's tightened scenario verbatim.
- **Expected**: Correctly names `status:blocked`, correctly explains owned-but-parked vs in-progress vs pending-*, correctly states "continue to next item, do not stop," correctly names the resume path (forge event -> blocked -> in-progress).
- **Result**: PASS — 4/4 correct, unprompted, exact terminology matched.

### TC-6 (covers AC6): Doc-first sequencing
- **Steps**: Read the full Discussion thread chronologically.
- **Expected**: Phase-1 spec (SPEC-13515.md) committed and PM-reviewed (including a real diagnosed-and-recovered stranded-commit incident) BEFORE any Phase-2 code was written; operator confirmed the status name; skill then implemented Phase-1+Phase-2 together in one PR per the approved sequencing.
- **Result**: PASS — sequencing matches the approved plan exactly.

### TC-7: Worker's own suite + full regression
- **Steps**: `pytest tests/test_13515_blocked_status.py tests/test_tracker_authority.py`, full static gate on combined state.
- **Result**: Worker's own 135 tests PASS (all mocked — this is exactly why TC-3's live gap was invisible to them). Static gate result pending at write time.

## Coverage matrix
- AC1 → TC-1 (PASS)
- AC2 → TC-2 (PASS)
- AC3 → TC-3 (**FAIL** — live transition crashes, label never provisioned)
- AC4 → TC-4 (PASS)
- AC5 → TC-5 (PASS)
- AC6 → TC-6 (PASS)

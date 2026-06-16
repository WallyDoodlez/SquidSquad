# TEST-PLAN #12475 — `--force` is a full legality override for tracker.py transitions

**Derived independently from the issue's Observed/Expected + RCA notes (not the PR).**
Bug fix, no formal AC list → ACs derived from the operator directive (2026-06-16) + RCA blast-radius caution.

## Derived ACs

- **AC1 (core override)**: `tracker.py transition <n> <from> <to> --force` permits changing
  status to ANY value, bypassing the legal-transition matrix — in addition to the authority +
  unread-feedback guards it already bypassed. The exact repro `transition 12451 approved planning
  --role pm-lead --force` must now succeed (forward matrix forbids approved→anything-but-in-progress).
- **AC2 (no-force unchanged)**: without `--force`, the illegal edge is still rejected (regression guard
  on the non-forced hot path).
- **AC3 (ship-integrity preserved — RCA blast-radius)**: a forced transition must NOT strand
  side-effect/integrity handling. Ship-integrity gates stay hard even under `--force`:
  TC-coverage (pending-test→pending-ship) and unmerged-PR/branch (→shipped). Applies to BOTH a
  legal forced edge and an illegal forced edge that lands on `shipped`.
- **AC4 (side-effects run coherently)**: a forced transition into `shipped` (clean merge state)
  still auto-closes the issue and emits the status-transition event; the issue lands exactly ONE
  status label.
- **AC5 (force-robust label swap)**: on the forced path a wrong caller-supplied `from_status`
  (and/or a pre-corrupted double status-label) must not leave two status labels — the live status
  labels are queried and all stale ones stripped.

## Test Cases

| TC | Description | Method | Expected |
|----|-------------|--------|----------|
| TC1 | Issue repro: forced approved→planning | own harness, forge mocked | success; remove approved, add planning |
| TC2 | Same edge WITHOUT --force | own harness | rejected exit 1 + "Use --force" hint |
| TC3 | Forced LEGAL pending-ship→shipped, open PR | own harness | BLOCKED exit 1 (ship-gate) |
| TC4 | Forced ILLEGAL in-progress→shipped, open PR | own harness | BLOCKED exit 1 (ship-gate) |
| TC5 | Forced →shipped clean → auto-close + 1 label | own harness | close_issue called, one status label |
| TC6 | Forced path, wrong from_status + double-label | own harness | strips ALL stale, lands exactly one |
| TC7 | Dev suite regression | pytest test_12475 + test_tracker_authority | all green |

## Comprehension gate
NOT required — change is to `references/scripts/tracker.py` (a script) + tests only. No composed
CLAUDE.md / SOUL.md / WIZARD.md / instructions.md (LLM-consumed instruction files) modified.
`--help`/docstring are deterministic CLI output. Matches PR's own "no composed agent-instruction
change" flag.

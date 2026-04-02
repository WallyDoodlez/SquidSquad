## BUG-SKILL-028 — README.md still references old `.active-role` auto-boot mechanism

- **Severity**: Low
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: README.md line 218 says "agents auto-detect their role from `.squidsquad/.active-role`" — this is the old auto-boot mechanism replaced by FEAT-SKILL-042. The new mechanism uses `--append-system-prompt "SQUIDSQUAD_ROLE=<role>"`. README should reflect the current boot flow.
- **Steps to Reproduce**:
  1. Read README.md line 218
- **Expected**: README describes `--append-system-prompt` as the boot mechanism
- **Actual**: README still references `.active-role` file-based auto-detection

### Discussion

> [2026-03-29 22:30] **pm/qa**: Found during FEAT-042 QA verification. Low severity — user-facing docs only, no functional impact.
> [2026-03-29 23:15] **skill-lead**: Fixed README.md line 218 — replaced `.active-role` file reference with `--append-system-prompt "SQUIDSQUAD_ROLE=<role>"` description matching current boot flow. Status → Fixed.
> [2026-03-30 01:00] **pm/qa**: Verified — README.md no longer references .active-role auto-detect. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).

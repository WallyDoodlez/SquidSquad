# TEST-PLAN-11613

**Task**: #11613 — installer dependency auto-provisioning (gather-all → consent → provision) per INSTALLER-ARCH §4.1
**Type**: task (priority:medium) · **Role**: skill · **PR**: #12471 · **Branch**: squidsquad/task/11613
**Derived**: 2026-06-15 from the issue Build list + INSTALLER-ARCH §4.1 (the cited contract) — the body's formal ACs are thin, so per the locked-architecture rule I derive from §4.1.

## ACs (derived from §4.1 contract + Build/concrete-fixes list)
- **AC1** — Gather-all detector: single pass enumerating ALL missing deps, no fail-fast (`gather_deps`).
- **AC2** — Per-platform provision dispatch (package manager / pip -r / npm) for auto items (`provision_deps`).
- **AC3** — ONE consent prompt for the full missing-set; install nothing before answer.
- **AC4** — Guided (not auto) for claude CLI (npm) + gh auth; re-verify after provisioning; hard-dep still missing → instruct + exit code 0.
- **AC5** — Concrete fixes: pyyaml → requirements.txt; start.sh + start.ps1 use `pip install -r requirements.txt`.
- **AC6** — No regression to existing prereq check (check_gh/preflight); DS review.
- **AC7 (comprehension)** — WIZARD.md Step 0 (LLM-consumed installer runbook) is unambiguous.

## Test cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC1-4/6 | full test_wizard_11613 + test_wizard_runbook | green |
| TC-2 | AC1 | inspect gather_deps (457) | single pass, enumerates all missing |
| TC-3 | AC2 | inspect provision_deps (638) | auto items only, re-runs gather, never blocks |
| TC-4 | AC5 | grep requirements*.txt + start.sh/ps1 | pyyaml in requirements.txt; pip install -r in both |
| TC-5 | AC6 | grep check_gh/preflight | intact |
| TC-6 | AC4/§4.1 | WIZARD.md Step 0 vs §4.1 contract | matches (never-fail-fast, consent-gated, no repo writes) |
| TC-7 | AC7 | comprehension spec 11613_spec.json — fresh agent, Step 0 only | all CQs correct |

## Comprehension spec
REQUIRED — WIZARD.md is the installer-agent runbook (LLM-consumed). `tests/comprehension/11613_spec.json` (6 CQs).

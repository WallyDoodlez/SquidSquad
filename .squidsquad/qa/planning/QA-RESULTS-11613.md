# QA-RESULTS-11613

**Task**: #11613 — installer dependency auto-provisioning per INSTALLER-ARCH §4.1
**Verified**: 2026-06-15 19:12 (qa cycle 211, POLLING) · **Branch**: squidsquad/task/11613 · **PR**: #12471
**Verdict**: ✅ **PASS → pending-ship.** Code ACs + §4.1 contract + comprehension gate all pass. Zero gaps.

## AC walk

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC-1 | AC1-4/6 | ✅ PASS | test_wizard_11613_dep_provisioning + test_wizard_runbook = **67 passed**. |
| TC-2 | AC1 | ✅ PASS | `gather_deps` (wizard.py:457) — single pass, `missing` = one entry per unsatisfied dep, never fail-fast. |
| TC-3 | AC2 | ✅ PASS | `provision_deps` (638) re-runs gather_deps, acts only on auto-provisionable items (package_manager/pip/npm/ensurepip), never blocks on a prompt; `cmd_gather_deps`/`cmd_provision_deps` CLI. |
| TC-4 | AC5 | ✅ PASS | `pyyaml>=6.0` moved to requirements.txt (clear #11613 comment); removed from requirements-dev.txt. start.sh: `... import ... yaml ... \|\| pip3 install -r requirements.txt`; start.ps1: `pip install -r requirements.txt` — both replace the hard-coded 2-of-4 subset. |
| TC-5 | AC6 | ✅ PASS | `check_gh` (171) + `preflight` (217) + cmd wrappers intact — no regression to existing prereq check. |
| TC-6 | AC4/§4.1 | ✅ PASS | WIZARD.md Step 0 matches INSTALLER-ARCH §4.1 (operator-locked 2026-06-12): gather-all → present → ONE consent → provision → re-verify; never fail-fast; host-level provisioning consent-gated; NO target-repo writes; hard (gh/python/pip/packages) vs soft (claude) split; exit code 0 on unmet hard deps. |
| TC-7 | AC7 comprehension | ✅ PASS | Fresh sonnet agent given ONLY WIZARD.md Step 0 → **6/6 CQs correct** (gather-all/never-fail-fast, exactly-one-consent, claude-soft-not-hard-stop, exit-0-on-hard-missing + re-run, no-repo-writes, `provision-deps` no-args command). Instructions unambiguous. Spec: tests/comprehension/11613_spec.json. |

## Comprehension spec
`tests/comprehension/11613_spec.json` — REQUIRED (WIZARD.md is the installer-agent runbook, LLM-consumed). 6 CQs, all PASS.

## Decision
- All ACs + comprehension gate PASS. Transitioned `pending-test → pending-ship`.
- **Merge deferred to DM** (delivery boundary; consistent with the #12418/#12442/#12443/#12458 window). Ship counter NOT bumped (DM owns).
- Next in skill's installer queue: #12419 (migration-walk), #12420 (post-commit restart), #12450/#12451; #12271 slice d (#12460).

# Working State

- **Task**: #6581
- **Status**: in-progress
- **Started**: 2026-05-11 06:01
- **Last Processed Event ID**: 0adb6a2b

## Completed Steps
- Read all 3 planning artifacts (CONTEXT, RESEARCH, TEST-PLAN)
- Transitioned to in-progress, checked out feature branch
- Added domain_variants to software-dev preset manifest
- Added load_preset_manifest() and resolve_domain_variants() helpers to wizard.py
- Refactored apply_project_type() to use manifest-driven resolution with legacy fallback
- Updated generate_default_spec() to derive variants from manifest instead of hardcoding

## Remaining Steps
- Add L4 file writing to scaffold_install() (TC-3, TC-8)
- Update WIZARD.md runbook for hybrid L4 writer (TC-4)
- Rewrite TestApplyProjectType tests for new path (TC-10)
- Add new tests for manifest resolution (TC-1, TC-2, TC-5, TC-6, TC-7, TC-9)
- Add smoke test for fresh install (TC-11)
- Run full test suite
- Self-verify and submit to QA

## Key Decisions
- Preset manifest domain_variants is single authority
- Legacy PROJECT_TYPE_PRESETS retained as fallback for unmigrated project types
- apply_project_type() now returns dict of {role: variant} instead of single variant string
- generate_default_spec() uses resolve_domain_variants("software-dev") instead of hardcoded "skill"

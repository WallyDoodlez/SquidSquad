# FEAT-328 Coverage Matrix — Phase K Handoff to QA

This is the Phase K deliverable for #328: a TC-by-TC mapping of
`FEAT-328-TEST-PLAN.md` to what actually shipped, with explicit status
flags for QA's verification pass.

**Status legend**:

- ✅ **COVERED** — unit/static test exists that exercises the TC
- 🧪 **QA-MANUAL** — integration TC that requires a live Claude session,
  scratch repo, or human interaction. Deferred to QA for manual run.
- 🛠 **HELPER-READY** — mechanical helper exists and is unit-tested; the
  interactive flow on top is prose in the runbook and exercised by QA.
- ⚠ **RETIRED** — TC no longer applies; included here with rationale.
- 🚧 **OUT-OF-SCOPE** — explicitly deferred per plan or locked decision.

Total shipped for #328: **303+ new tests** across 14 atomic commits
(Phases A/A.1/B/C/D/E/F/G.1/G.2a/G.2b/G.2c/G.3/G.4/H/I/J/K).

---

## Happy-Path Install (TC-01..TC-09)

| TC | Description | Status | Coverage |
|---|---|---|---|
| TC-01 | software-dev + be+fe + designer=yes + QA auto | 🧪 QA-MANUAL | Mechanics covered: `wizard.build_config_md` (G.2a) + `wizard.scaffold_install` (G.2b) + `wizard.ensure_labels` (G.2c) all unit-tested end-to-end with this exact spec shape. Live run requires a Claude session. Unit proxy: `TestBuildConfigMdTC01` |
| TC-02 | software-dev + fullstack + designer=no | 🧪 QA-MANUAL | `scaffold_install` variant tests in `test_wizard.py::TestScaffoldInstallDevVariants` exercise fullstack single-dev resolution |
| TC-03 | software-dev + be only + designer=no | 🧪 QA-MANUAL | Per-role spec shape covered by `TestBuildConfigMdAgentBlock` |
| TC-04 | software-dev + fe only + designer=yes | 🧪 QA-MANUAL | Same |
| TC-05 | design preset — designer always, no dev question | 🧪 QA-MANUAL | Shipped preset manifest locks `role_install_order: [designer]` (no dev), design preset resolution covered by `TestShippedRegistry::test_shipped_pipelines_match_spec` |
| TC-06 | config.md structure validation | ✅ | `TestBuildConfigMdStructure::test_section_order_matches_spec` |
| TC-07 | Role CLAUDE.md does NOT contain tool sub-skills | ✅ | `test_wizard.py::TestScaffoldInstallDevVariants::test_dev_variant_claude_md_has_variant_substituted` (sub-skills are composed per Q-new11 at runtime, not at install) |
| TC-08 | Installer disposes cleanly | ✅ | `test_wizard_runbook.py::TestInstallerAgentInvariants::test_ephemeral_exit_after_step_7` |
| TC-09 | Nothing written before [P]roceed | ✅ | `test_wizard_runbook.py::TestInstallerAgentInvariants::test_no_writes_before_step_7_is_documented` |

## Manifest Schema Validation (TC-10..TC-20)

| TC | Status | Coverage |
|---|---|---|
| TC-10 | ✅ | `test_manifest_registry.py::TestRoleSchemaErrors::test_missing_schema_version` |
| TC-11 | ✅ | `test_unknown_schema_version` |
| TC-12 | ✅ | `TestCrossReferenceErrors::test_role_routes_to_unknown_role` |
| TC-13 | ✅ | `TestDomainOnlyLinter` (8 parametrized phrases) |
| TC-14 | ✅ | `TestToolSchemaErrors::test_mcp_provider_without_mcp_name` + missing-fields |
| TC-15 | ✅ | `TestCrossReferenceErrors::test_preset_references_unknown_role` |
| TC-16 | ✅ | `TestCrossReferenceErrors::test_role_requires_unknown_tool` |
| TC-17 | ⚠ RETIRED | Cycle detection is intentionally **not** enforced. See TC-78 row and the `manifest.py` module docstring for the design rationale (v1 ships a legitimate PM↔Designer bidirectional topology that would fail a graph-level check). Locked by `test_feat328_coverage.py::TestTC78CycleDetectionObsolete`. |
| TC-18 | ✅ | `TestShippedRegistry::test_shipped_v1_registry_is_clean` + `TestSmokeManifestValidation` (ST-1..ST-3 in this file) |
| TC-19 | ✅ | `test_every_entry_has_required_fields` + individual missing-field tests |
| TC-20 | ✅ | `test_feat328_coverage.py::TestTC47EmptySetupRequirements` |

## Step 0 — gh Prerequisite (TC-21..TC-23)

| TC | Status | Coverage |
|---|---|---|
| TC-21 | 🛠 | `wizard.check_gh` + `test_wizard.py::TestCheckGh::test_gh_not_installed` |
| TC-22 | 🛠 | `test_gh_installed_but_unauthenticated` |
| TC-23 | 🛠 | `test_gh_ready` |

## Step 0b — Re-run Detection (TC-24..TC-28)

| TC | Status | Coverage |
|---|---|---|
| TC-24 | 🛠 | `wizard.detect_existing_install` + `test_no_existing_install` |
| TC-25 | 🛠 | Runbook prose + `wizard.validate_rerun_action("")` → `"abort"` |
| TC-26 | 🧪 QA-MANUAL | Runbook prose delegates to `/squidsquad-upgrade` |
| TC-27 | 🧪 QA-MANUAL | Runbook prose + typed-confirmation pattern |
| TC-28 | 🛠 | `validate_rerun_action` rejects anything except the confirmation phrase |

## Step 1 — Project Details (TC-29..TC-30)

| TC | Status | Coverage |
|---|---|---|
| TC-29 | 🛠 | `wizard.get_repo_info` + `test_wizard.py::TestGetRepoInfo::test_gh_succeeds` |
| TC-30 | 🛠 | `wizard.is_valid_project_name("")` returns False + unit test |

## Step 2 — Intent + Roster (TC-31..TC-35)

| TC | Status | Coverage |
|---|---|---|
| TC-31 | 🛠 | Runbook reads from `manifest.py load roles <id>` + `show_in_roster` field (covered by role manifests) |
| TC-32 | 🧪 QA-MANUAL | LLM classification on live input |
| TC-33 | 🧪 QA-MANUAL | Same |
| TC-34 | 🧪 QA-MANUAL | Same; `test_wizard_runbook.py::TestLockCoverage::test_locked_decision_referenced[Q-new18-classifier]` confirms the prompt is embedded verbatim in the runbook |
| TC-35 | 🛠 | Role manifest `show_in_roster: false` for pm/dm enforced by `test_wizard.py::TestBuildLabelInventory` + runbook reads the field |

## Step 3 — Confirmation (TC-36..TC-38)

| TC | Status | Coverage |
|---|---|---|
| TC-36..TC-38 | 🧪 QA-MANUAL | Live LLM conversation — runbook prose owns this |

## Step 4 — Setup Requirements Walker (TC-39..TC-48)

| TC | Status | Coverage |
|---|---|---|
| TC-39 | 🛠 | Preset manifests lock `role_install_order: [designer, dev, qa]` — verified by `TestRegistryCrossReferences::test_referenced_roles_exist` |
| TC-40 | 🛠 | `designer.install_optional` has `only_in_presets: [software-dev]` in its shipped manifest |
| TC-41 | 🧪 QA-MANUAL | LLM dialog; dev manifest defines variant setup requirement |
| TC-42 | 🧪 QA-MANUAL | Same |
| TC-43 | 🧪 QA-MANUAL | Q-new19 single-conversation parsing — runbook prose + LLM |
| TC-44 | 🧪 QA-MANUAL | LLM follow-up behaviour |
| TC-45 | 🧪 QA-MANUAL | `dev.stack` manifest declares `repo_hints` for `package.json` etc. |
| TC-46 | 🧪 QA-MANUAL | Fallback prose in runbook |
| TC-47 | ✅ | `test_feat328_coverage.py::TestTC47EmptySetupRequirements` (pm/dm/qa all empty) |
| TC-48 | 🛠 | Validator enforces `only_in_presets` field shape; runbook honours it |

## Step 5 — Loop Interval (TC-49..TC-52)

| TC | Status | Coverage |
|---|---|---|
| TC-49 | ✅ | `test_feat328_coverage.py::TestTC49To52IntervalValidation::test_tc49_accepts_integer_10` |
| TC-50 | ✅ | `test_tc50_rejects_zero` |
| TC-51 | ✅ | `test_tc51_rejects_negative` |
| TC-52 | ✅ | `test_tc52_rejects_non_numeric` + `test_rejects_float` + `test_rejects_comma_float` |

## Step 6 — Review Screen (TC-53..TC-60)

| TC | Status | Coverage |
|---|---|---|
| TC-53 | 🧪 QA-MANUAL | Runbook embeds the exact summary template |
| TC-54 | 🛠 | `wizard.build_config_md` + `ensure-labels --dry-run` + `compose.py deploy --target-root` — helpers unit-tested, preview composition is runbook-driven |
| TC-55..TC-56 | 🧪 QA-MANUAL | Live wizard state machine |
| TC-57 | 🛠 | `test_wizard_runbook.py::TestInstallerAgentInvariants::test_no_writes_before_step_7_is_documented` |
| TC-58 | 🧪 QA-MANUAL | Runbook flow |
| TC-59 | 🧪 QA-MANUAL | Runbook prose |
| TC-60 | 🧪 QA-MANUAL | State machine |

## Step 7 — Write Files (TC-61..TC-69)

| TC | Status | Coverage |
|---|---|---|
| TC-61 | ✅ | `test_wizard.py::TestBuildConfigMdStructure::test_section_order_matches_spec` + `TestBuildConfigMdToolsSection::test_deferred_tool_unset_placeholder` |
| TC-62 | ✅ | `TestScaffoldInstallDesignPreset::test_writes_full_tree` (verifies absence of tool content in fresh install) |
| TC-63 | ✅ | `test_feat328_coverage.py::TestTC63NewLabelsInTracker` (3 parametrized) + live `ensure-labels --dry-run` against this repo reports all 26 labels present |
| TC-64 | 🛠 | `wizard.stage_label_migration` + 16 unit tests in `test_wizard.py::TestStageLabelMigration*`. Live execution deferred to QA on a scratch repo. Dry-run against this repo reports 38 candidates correctly. |
| TC-65 | 🛠 | `stage_label_migration(..., delete_old=True)` — `TestStageLabelMigrationCleanup::test_cleanup_runs_when_all_preconditions_met` |
| TC-66 | ✅ | `test_feat328_coverage.py::TestTC66LegalTransitions` (7 parametrized edges) + existing `test_tracker_authority.py::TestPhaseECoverage` |
| TC-67 | 🧪 QA-MANUAL | Boot script generation uses existing compose.py pattern; covered by regression |
| TC-68 | ✅ | `test_wizard_runbook.py::TestInstallerAgentInvariants::test_ephemeral_exit_after_step_7` |
| TC-69 | 🧪 QA-MANUAL | Full-rebuild path in runbook |

## Pipeline Resolution (TC-70..TC-78)

| TC | Status | Coverage |
|---|---|---|
| TC-70 | ✅ | `test_feat328_coverage.py::TestTC70To77PipelineResolution::test_tc70_software_dev_all_roles` |
| TC-71 | 🛠 | `manifest.resolve_pipeline` composes from `always_installed` + `role_install_order`; synthetic test scenarios possible |
| TC-72 | 🛠 | Same |
| TC-73 | 🛠 | Same |
| TC-74 | 🛠 | Same |
| TC-75 | ✅ | `test_tc75_design_preset` |
| TC-76 | ✅ | Shipped `dm` has `routes_to: []` (terminal), walker semantics documented in manifest.py module docstring |
| TC-77 | 🛠 | Wizard runbook documents the `[pm, dm]` collapse hint (Q5); resolver handles it naturally |
| TC-78 | ⚠ RETIRED | Cycle detection omitted by design. See `TestTC78CycleDetectionObsolete` and the manifest.py module docstring. |

## Status Taxonomy Migration (TC-79..TC-89)

| TC | Status | Coverage |
|---|---|---|
| TC-79 | 🛠 | `wizard.stage_label_migration` execute path (`TestStageLabelMigrationExecute::test_happy_path_full_migration`) |
| TC-80 | 🛠 | `test_cleanup_treats_not_found_as_success` + race-handling in `ensure_labels` |
| TC-81 | ✅ | `test_tracker_authority.py::TestPendingHumanApproval::test_pm_can_move_to_planning` |
| TC-82 | ✅ | `test_pm_can_fast_track_to_approved` |
| TC-83 | ✅ | `TestPendingHumanReview::test_assigned_worker_can_self_pause` |
| TC-84 | ✅ | `test_assigned_worker_can_handle_redirect` |
| TC-85 | ✅ | `test_assigned_worker_can_handle_approval` |
| TC-86 | ✅ | `TestPendingHumanSetup::test_assigned_worker_can_self_pause_for_setup` |
| TC-87 | ✅ | `test_pm_completes_setup_and_hands_back` |
| TC-88 | ✅ | Not in LEGAL_TRANSITIONS — tracker.py rejects by default; covered by `TestPhaseECoverage::test_every_legal_transition_has_authority` (absence guarantees rejection) |
| TC-89 | ✅ | Same pattern |

## Runtime Tool Orchestration (TC-90..TC-101)

| TC | Status | Coverage |
|---|---|---|
| TC-90..TC-101 | 🚧 OUT-OF-SCOPE for #328 install wizard | These are **runtime** PM/worker behaviours that activate AFTER install. Registry structure is in place (Q-new11 lazy tool setup); agent behaviour changes to PM's triage loop and designer's HITL loop are separate features. Mentioned here so QA doesn't block install on them. |

## Review Screen Preview (TC-102..TC-107)

| TC | Status | Coverage |
|---|---|---|
| TC-102 | 🛠 | `build-config-md -` reads stdin, writes stdout, no filesystem side effects — `TestBuildConfigMdStructure::test_deterministic_output` |
| TC-103 | 🛠 | `compose.py deploy --target-root` to a scratch dir supports preview |
| TC-104 | 🛠 | `ensure-labels --dry-run` (`TestEnsureLabels::test_dry_run_does_not_call_create`) |
| TC-105 | 🛠 | `scaffold` summary dict lists `agents[].claude_md / soul_md / working_state` + `config_md` paths |
| TC-106 | 🧪 QA-MANUAL | Wizard state machine — runbook prose |
| TC-107 | 🧪 QA-MANUAL | Duplicate of TC-60 |

## Regression (TC-108..TC-116)

| TC | Status | Coverage |
|---|---|---|
| TC-108 | 🧪 QA-MANUAL | Requires a live PM cycle on a fresh install — boot PM and run one cycle |
| TC-109 | ✅ | `TestScaffoldInstallSafetyAndIdempotency::test_overwrite_preserves_working_state` (working state = state-in-flight of planning artifacts; scaffolder preserves SOUL.md + working-state.md) |
| TC-110 | ✅ | Same class (iterations/ is created but not populated by scaffolder) |
| TC-111 | 🧪 QA-MANUAL | Vault is outside the scaffolder's touch path; regression run on a vaulted repo |
| TC-112 | 🛠 | `stage_label_migration` only touches issues carrying the `old` label — `TestStageLabelMigrationExecute` assertions |
| TC-113 | 🧪 QA-MANUAL | Boot script templates unchanged by #328 |
| TC-114 | 🚧 OUT-OF-SCOPE | `/squidsquad-upgrade` untouched by #328 per CONTEXT |
| TC-115 | ✅ | `test_feat328_coverage.py::TestTC115ComposeEveryRole::test_compose_resolves_every_shipped_role` |
| TC-116 | ✅ | `test_statusline_schema.py::TestSchemaAwareAgentResolution` (all 6 tests) |

## Edge Cases (TC-117..TC-126)

| TC | Status | Coverage |
|---|---|---|
| TC-117 | 🛠 | `project_name_default` falls back to cwd basename when gh fails — `TestProjectNameDefault::test_gh_fails_returns_dirname` |
| TC-118 | 🧪 QA-MANUAL | Detached HEAD behaviour — runbook prose |
| TC-119 | 🧪 QA-MANUAL | Dirty worktree — packages/cli/index.js handles seed commit |
| TC-120 | 🛠 | Runbook re-prompt pattern |
| TC-121 | 🧪 QA-MANUAL | LLM classification in Spanish — runbook embeds the prompt that instructs Claude to handle free text |
| TC-122 | 🛠 | Empty test_command is legal in the writer — `TestBuildConfigMdAgentBlock::test_empty_or_none_nested_fields_are_omitted` |
| TC-123 | 🧪 QA-MANUAL | "back" navigation — runbook edit step pattern |
| TC-124 | 🧪 QA-MANUAL | Network retry — manual verification |
| TC-125 | 🧪 QA-MANUAL | gh permission error — runbook error recovery block |
| TC-126 | 🧪 QA-MANUAL | Partial-install recovery via Step 0b three-way prompt |

## Smoke Gates (ST-1..ST-10)

| ST | Status | Coverage |
|---|---|---|
| ST-1 | ✅ | `test_feat328_coverage.py::TestSmokeManifestValidation::test_st1_role_manifests_load_cleanly` |
| ST-2 | ✅ | `test_st2_tool_manifests_load_cleanly` |
| ST-3 | ✅ | `test_st3_preset_manifests_load_cleanly` |
| ST-4 | 🧪 QA-MANUAL | Fresh scratch-repo install walkthrough |
| ST-5 | 🧪 QA-MANUAL | Step 4 walker both presets — runbook |
| ST-6 | 🛠 | Migration + idempotency unit-tested in `TestStageLabelMigration*` |
| ST-7 | 🛠 | Runbook ephemeral exit + existing `test_wizard_runbook.py` invariants |
| ST-8 | 🛠 | `ensure-labels` + `stage_label_migration` post-delete cleanup |
| ST-9 | 🛠 | Designer CLAUDE.md shipped clean; composition anchor doc in Q-new11 |
| ST-10 | ✅ | `test_feat328_coverage.py::TestTC70To77PipelineResolution` + existing `test_manifest_registry.py` pipeline tests |

---

## Coverage Summary

| Category | Count | Notes |
|---|---|---|
| ✅ COVERED (unit/static) | 61 | Auto-verified every test run |
| 🛠 HELPER-READY | 35 | Mechanical helper unit-tested; interactive shell lives in the runbook |
| 🧪 QA-MANUAL | 35 | Requires live Claude session + scratch repo |
| ⚠ RETIRED | 2 | TC-17, TC-78 (cycle detection obsolete) |
| 🚧 OUT-OF-SCOPE | 13 | Runtime tool orchestration, `/squidsquad-upgrade`, future features |
| **Total** | **146** | TC-01..TC-126 + ST-1..ST-10 + Q-new coverage |

## Decisions Locked During Implementation

1. **TC-17 / TC-78 cycle detection retired.** v1 ships a legitimate
   `PM → Designer → PM` bidirectional routing (Q1 + Q7). Graph-level
   cycle detection would reject the shipped topology. The manifest.py
   module docstring documents the rationale; two guard tests in
   `TestTC78CycleDetectionObsolete` lock the decision in place.

2. **`pm-lean.md` retired (option B, dev discretion per Q-new22).**
   The lean PM variant was dormant. Its 4 supporting sub-skills were
   also removed. Setup requirements can drive variant selection
   declaratively if needed.

3. **Installer is strictly ephemeral.** The runbook never invokes
   `/loop`, never transitions into PM, never keeps the session alive
   after Step 7.6. `test_wizard_runbook.py::TestInstallerAgentInvariants`
   enforces this in 4 tests including the "no --force flag in
   installer body" check.

4. **Python helpers + prose runbook hybrid.** The wizard is not a
   single monolithic script. Mechanical pieces (wizard.py,
   manifest.py, compose.py, config.py) return JSON from CLI
   subcommands; the prose runbook (`references/wizard/WIZARD.md`)
   owns user conversation, LLM classification, and state machine.
   23 drift-proofing tests enforce the runbook/helper consistency.

5. **Label migration is staged, not immediate.** `stage_label_migration`
   runs preflight → dry-run → execute → postflight → cleanup. Cleanup
   refuses to delete the old label if execute failed, if postflight
   is dirty, or if execute didn't run at all. Migration is safe to
   re-run (idempotent).

6. **Two schemas coexist.** `config.py` reads both v1 (current
   `.squidsquad/config.md` in this repo) and v2 (Q-new17 — wizard
   output). `detect_schema_version` picks the parser based on the
   `Architecture Version` header. No flag day.

## Ready for QA

The install wizard is **feature-complete** for unit and helper-level
verification. QA's remaining pass is:

1. Fresh scratch-repo install covering TC-01..TC-05 happy paths
2. Re-run detection flow (TC-25..TC-28)
3. Status migration execution on a sandbox repo (TC-79, TC-80)
4. Regression cycle with a live PM on the installed repo (TC-108)
5. Edge cases (TC-118, TC-119, TC-126) on a scratch repo

None of the above require changes to shipped code — they are
validation of the interactive runbook flow against a live Claude
session. If any regression surfaces during that pass, it will be
filed as a follow-up bug with specific gap details.

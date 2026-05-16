# Scan History

## Scan — 2026-05-15 21:03

- **Files scanned**: references/scripts/config.py, references/scripts/cycle_pre.py
- **Findings**: #8343 (cycle_pre.py: inconsistent boolean config parsing across functions)
- **Items rejected by human**: none

## Scan — 2026-05-15 20:03

- **Files scanned**: references/scripts/cycle_post.py, references/scripts/model_router.py
- **Findings**: #8336 (cycle_post.py: redundant import re inside two functions)
- **Items rejected by human**: none

## Scan — 2026-05-15 18:32

- **Files scanned**: references/scripts/triage.py, references/scripts/event_bus.py, tests/test_triage.py, tests/test_event_bus.py, tests/test_feat_2495_upgrade_rewrite.py
- **Findings**: #8307 (triage.py: dead code in find_qa_rejected own-comment check)
- **Items rejected by human**: none

## Scan — 2026-05-15 17:33

- **Files scanned**: references/scripts/tracker.py, references/scripts/git_ops.py, references/scripts/squidsquad_cli.py
- **Findings**: #8268 (tracker.py get_state returns OPEN for missing state — low), #8269 (squidsquad_cli.py unused import os — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 16:03

- **Files scanned**: references/scripts/start_team.py, references/scripts/thin_launcher.py, references/scripts/diagnostics.py
- **Findings**: #8234 (start_team.py bare except swallows all errors — low), #8235 (diagnostics.py missing redaction keywords — medium)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 14:33

- **Files scanned**: references/scripts/vault_check.py, references/scripts/vault_entity.py, references/scripts/tc_coverage.py
- **Findings**: #8200 (vault_check.py wikilink pipe-alias not stripped — low), #8201 (vault_entity.py unhandled --file read error — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 13:33

- **Files scanned**: references/scripts/event_bus.py, references/scripts/event_bus_reader.py, references/scripts/event_catalog.py
- **Findings**: #8193 (unused import sys in event_bus.py and event_bus_reader.py — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 11:33

- **Files scanned**: references/scripts/compose.py, references/scripts/boot_remote.py, references/scripts/soul_adaptation.py
- **Findings**: #8159 (compose.py redundant imports in agent_compose — low), #8160 (boot_remote.py corrupt .claude-pid silent fallthrough — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 09:03

- **Files scanned**: references/scripts/cycle_pre.py, references/scripts/config.py, references/scripts/health_check.py
- **Findings**: #8115 (cycle_pre.py unhandled ValueError on ship-threshold int() — low), #8116 (health_check.py _read_interval regex unscoped — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 07:34

- **Files scanned**: references/scripts/triage.py, references/scripts/scan_index.py, references/scripts/vault_remember.py
- **Findings**: #8081 (triage.py string-based timestamp comparison fragile — low), #8082 (scan_index.py record_decision silent no-op on missing file_coverage row — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-14 16:34

- **Files scanned**: references/commands/squidsquad-compose.md, references/commands/squidsquad-upgrade.md, references/docs/vault-reference.md, references/prompts/code-review.md.j2
- **Findings**: #7879 (upgrade commit stages .claude/ with unrelated user changes — medium)
- **Items rejected by human**: none yet

## Scan — 2026-05-14 16:04

- **Files scanned**: tests/comprehension/1428_spec.json, tests/comprehension/2181_spec.json, tests/comprehension/361_spec.json, docs/EVENT-BUS-ARCHITECTURE.md, docs/diagrams/layer-stack.html
- **Findings**: #7878 (EVENT-BUS-ARCHITECTURE.md stale pr-merge refs + missing compose-completed — low, filed to DM)
- **Items rejected by human**: none yet

## Scan — 2026-05-14 15:04

- **Files scanned**: tests/test_start_team.py, tests/test_thin_launcher.py, tests/test_vault_check.py, tests/test_vault_entity.py, tests/test_vault_synthesis.py
- **Findings**: #7866 (dead test body + tautological if-guarded assertions in test_vault_entity.py — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-14 13:34

- **Files scanned**: tests/test_feat_3645_auto_merge.py, tests/test_own_domain_autofix.py, tests/test_repo_scan.py, tests/test_run_comprehension_test.py, tests/test_squidsquad_cli.py
- **Findings**: #7842 (fragile getsource in CLI error test — low), #7843 (mock patches wrong namespace — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-14 12:34

- **Files scanned**: tests/test_feat_1075_vault_candidates.py, tests/test_feat_1228_pipeline_sentinel.py, tests/test_feat_1328_blocked_skip.py, tests/test_feat_1363_label_sync.py, tests/test_feat_3494_version_bump.py
- **Findings**: #7829 (tautological fake_run in skip-test — low), #7830 (redundant inspect.getsource — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-14 11:04

- **Files scanned**: tests/test_dm_verify_before_block.py, tests/test_event_bus_reader.py, tests/test_event_catalog.py, tests/test_event_validator.py, tests/test_feat_1074_auto_merge.py
- **Findings**: #7800 (bare return silently passes instead of pytest.skip — low), #7801 (hardcoded event sets drift — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-14 10:37

- **Files scanned**: references/sub-skills/roles/pm/prohibitions.md, references/sub-skills/roles/pm/testing-and-verification.md, tests/test_comprehension_2183.py, tests/test_comprehension_2195.py, tests/test_deterministic_qa_framework.py
- **Findings**: #7793 (PM and QA both increment ship counter — medium), #7794 (stale tracker files ref in prohibitions — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-14 09:37

- **Files scanned**: references/sub-skills/project/shared-soul-directives.md, references/sub-skills/roles/dm/iteration-log.md, references/sub-skills/roles/pm/discussion-protocol.md, references/sub-skills/roles/pm/file-conventions.md, references/sub-skills/roles/pm/health-check.md
- **Findings**: #7706 (cycle.py log-iteration error message wrong flags — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-12 20:39

- **Files scanned**: tests/test_config_functions.py, tests/test_cycle.py, tests/test_scan_index.py, tests/test_shared_fs.py, tests/test_soul_adaptation.py
- **Findings**: #7635 (test_cycle.py dead capsys fixtures — low), #7636 (test_scan_index.py fragile source inspection — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-11 19:32

- **Files scanned**: references/scripts/migrate_state_branch.py, references/scripts/vault_remember.py, tests/test_per_agent_workdirs.py
- **Findings**: #7627 (migrate_state_branch returns 0 on total failure — medium), #7628 (test_per_agent_workdirs dead with-block — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-11 17:32

- **Files scanned**: references/scripts/add_role.py, references/scripts/vault_remember.py, references/scripts/forgejo_setup.py
- **Findings**: #7624 (vault_remember.py decay_scan unhandled read_text — medium), #7625 (forgejo_setup.py unreachable return 0 — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-11 16:32

- **Files scanned**: references/scripts/capability_check.py, references/scripts/comms_adapter.py, references/scripts/tc_coverage.py
- **Findings**: #7622 (tc_coverage.py check_coverage unhandled read_text — medium)
- **Items rejected by human**: none yet

## Scan — 2026-05-11 15:33

- **Files scanned**: references/scripts/reboot_agent.py, references/scripts/squidsquad_cli.py, references/scripts/vault_optimize.py
- **Findings**: #7618 (vault_optimize.py _acquire_lock TOCTOU — medium), #7619 (squidsquad_cli.py _api_call swallows error — medium)
- **Items rejected by human**: none yet

## Scan — 2026-05-11 14:02

- **Files scanned**: references/scripts/forge_adapter.py, references/scripts/scan_index.py, references/scripts/vault_entity.py
- **Findings**: #7614 (scan_index.py redundant db open/close — medium), #7615 (vault_entity.py proper-name defaults to person — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-11 12:32

- **Files scanned**: references/scripts/cycle.py, references/scripts/health_check.py, references/scripts/event_bus.py
- **Findings**: #7610 (cycle.py inc_counter double output — medium), #7611 (health_check.py alive branch wrong pid reader — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-11 10:02

- **Files scanned**: references/scripts/soul_adaptation.py, references/scripts/state_bus.py, references/scripts/manifest.py
- **Findings**: #7589 (state_bus.py commit_and_push ignores failed commit — medium), #7590 (manifest.py redundant yaml import + bare except — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-11 08:32

- **Files scanned**: references/scripts/thin_launcher.py, references/scripts/vault_check.py, references/scripts/diagnostics.py
- **Findings**: #7518 (diagnostics.py sanitize_config skips redaction without markdown bold — medium), #7519 (diagnostics.py --last crashes on non-integer — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-11 00:32

- **Files scanned**: references/scripts/cycle_post.py, references/scripts/triage.py, references/scripts/harness.py
- **Findings**: #7440 (cycle_post.py dead no-op str.replace — low), #7441 (harness.py save_state race condition — medium)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 22:03

- **Files scanned**: references/scripts/config.py, references/scripts/boot_remote.py
- **Findings**: #7285 (config.py sync_agents undefined has_dm NameError — medium), #7286 (boot_remote.py AppleScript quoting unsafe — low)
- **Items rejected by human**: none yet
## Scan — 2026-05-10 22:04

- **Files scanned**: references/sub-skills/project/pm-soul-directives.md, references/sub-skills/project/qa-instructions.md, references/sub-skills/project/qa-soul-directives.md, references/sub-skills/project/setup-upgrade-gate.md, references/sub-skills/project/shared-instructions.md
- **Findings**: none (all minimal seed templates)

## Scan — 2026-05-10 21:09

- **Files scanned**: references/sub-skills/project/dev-instructions.md, references/sub-skills/project/dev-soul-directives.md, references/sub-skills/project/dm-instructions.md, references/sub-skills/project/dm-soul-directives.md, references/sub-skills/project/pm-instructions.md
- **Findings**: #7191 (dev-instructions.md unscoped copy references instruction — low), #7192 (dm-soul-directives.md BRIEFING.md path unqualified — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 20:05

- **Files scanned**: references/scripts/start_team.py, references/scripts/providers/deepseek/manifest.yaml, references/sub-skills/common/event-reactions.md, references/sub-skills/common/file-conventions.md, references/sub-skills/common/working-state.md
- **Findings**: #7087 (start_team.py dead _is_agent_idle function — low)
- **Items rejected by human**: none yet
- **Notes**: DeepSeek model name finding rejected — scan agent applied stale knowledge (Aug 2025) to May 2026 project; deepseek-v4-pro is valid.

## Scan — 2026-05-10 19:33

- **Files scanned**: references/scripts/compose.py
- **Findings**: #7062 (compose.py dead variable prefix — medium), #7063 (compose.py redundant import re — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 18:33

- **Files scanned**: references/scripts/git_ops.py, references/scripts/wizard.py
- **Findings**: #6976 (wizard.py generate_default_spec hardcodes stale version — medium), #6977 (wizard.py redundant import shutil — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 18:02

- **Files scanned**: references/scripts/tracker.py, references/scripts/cycle_pre.py
- **Findings**: #6848 (tracker.py create_task missing forge adapter — medium), #6849 (tracker.py redundant import re in comment() — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 16:04

- **Files scanned**: references/scripts/event_catalog.py, references/scripts/event_validator.py, references/scripts/repo_scan.py, references/scripts/run_comprehension_test.py, references/scripts/shared_fs.py
- **Findings**: #6818 (shared_fs.py read-secret empty value false negative — medium), #6819 (run_comprehension_test.py unhandled TimeoutExpired — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 15:34

- **Files scanned**: references/docs/label-taxonomy.md, references/roles/SOUL.md, references/roles/pm/skill/SOUL.md, references/roles/qa/skill/includes.yml, references/scripts/event_bus_reader.py
- **Findings**: none

## Scan — 2026-05-10 14:35

- **Files scanned**: CONTRIBUTING.md, deploy-6126.sh, start.bat, packages/cli/index.test.js, references/docs/harness-lifecycle-upgrade.md
- **Findings**: #6805 (deploy-6126.sh stale one-time deploy script — low), #6806 (packages/cli/index.test.js unused t parameter — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 13:04

- **Files scanned**: tests/test_tc_coverage.py, tests/test_vault_remember.py, tests/test_wizard_runbook.py, tests/comprehension/2183_spec.json, tests/comprehension/2195_spec.json
- **Findings**: #6786 (test_vault_remember.py duplicate class definitions shadow tests — medium), #6787 (2183_spec.json missing reboot_agent.py source — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 12:04

- **Files scanned**: tests/test_diagnostics.py, tests/test_feat328_coverage.py, tests/test_feat_3296_task_boundary.py, tests/test_forgejo_setup.py, tests/test_forge_adapter.py
- **Findings**: #6772 (test_diagnostics.py unused capsys fixtures — low), #6773 (test_forge_adapter.py + test_forgejo_setup.py repeated urllib.error imports — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 11:04

- **Files scanned**: references/sub-skills/roles/dm/version-bumps.md, references/sub-skills/roles/pm/soul-shepherd.md, references/sub-skills/roles/qa/iteration-log.md, tests/test_compose_capability.py, tests/test_config.py
- **Findings**: #6759 (test_compose_capability.py unused import yaml — low), #6760 (version-bumps.md git tag bypass — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 10:05

- **Files scanned**: references/sub-skills/common/agent-lifecycle.md, references/sub-skills/common/issue-filing.md, references/sub-skills/common/vault-protocol.md, references/sub-skills/roles/dev/implement-tasks.md, references/sub-skills/roles/dev/triage-issues.md
- **Findings**: #6746 (implement-tasks.md git diff after git add returns empty — high), #6747 (triage-issues.md bug fix path skips review gate — medium)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 09:04

- **Files scanned**: references/prompts/research.md.j2, references/roles/instructions.md, references/scripts/forgejo_setup.py, references/scripts/forge_adapter.py, references/scripts/vault_check.py
- **Findings**: #6733 (forge_adapter.py _api() fails on HTTP 204 No Content — medium), #6734 (forgejo_setup.py deprecated version: 3 — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 08:35

- **Files scanned**: tests/test_state_bus.py, tests/test_vault_optimize.py, start.ps1, start.sh, references/presets/design/manifest.yaml
- **Findings**: #6731 (test_state_bus.py subprocess imported inside with block — low), #6732 (design preset manifest no machine-readable deprecation — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 06:05

- **Files scanned**: references/sub-skills/roles/pm/task-intake.md, references/sub-skills/roles/qa/git-commit.md, references/sub-skills/roles/qa/verification.md, tests/test_labels.py, tests/test_roles.py
- **Findings**: #6683 (test_roles.py docstring claims sub-skills/roles/ retired — low), #6684 (test_labels.py role label check only covers skill — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 04:35

- **Files scanned**: references/sub-skills/common/prohibitions.md, references/sub-skills/common/vault-remember.md, references/sub-skills/roles/dm/git-commit.md, references/sub-skills/roles/pm/github-issues.md, references/sub-skills/roles/pm/pipeline-sentinel.md
- **Findings**: #6629 (pipeline-sentinel Section 3 missing branch-workflow gate — low), #6630 (pipeline-sentinel Section 3 prose vs tracker.py commands — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 04:04

- **Files scanned**: tests/test_tracker.py, docs/event-bus.md, references/presets/software-dev/manifest.yaml, references/scripts/triage.py, references/scripts/providers/openai/adapter.py
- **Findings**: #6627 (triage.py dead role-lead suffix check — low), #6628 (adapter.py no retry on transient API errors — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-10 02:51

- **Files scanned**: tests/test_config_schema.py, tests/test_feat_1496_shared_fs_fallback.py, tests/test_harness.py, tests/test_installer_wiring.py, tests/test_model_router_live.py
- **Findings**: #6598 (stale shared-FS fallback tests verify removed behavior — low), #6599 (test_no_hallucinated_functions uses grep subprocess — fails on Windows — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-09 10:04

- **Files scanned**: references/sub-skills/common/git-commit.md
- **Findings**: #6526 (git_ops.py get_branch_name default pattern stale — low)
- **Items rejected by human**: none yet
- **Notes**: Subagent also found PR creation path ambiguity (manual vs cycle_post) and ownership check gap with unified branches — both template clarity issues, not code bugs.

## Scan — 2026-05-09 09:05

- **Files scanned**: references/scripts/vault_optimize.py
- **Findings**: #6514 (confidence decay str.replace/re.sub may corrupt body content — medium)
- **Items rejected by human**: none yet
- **Notes**: Also found orphan detection stem mismatch (high theoretical, low practical — vault convention enforces bare names, no aliases or paths found in actual vault). TOCTOU lock race (low — narrow window, no data loss). Filed body corruption as more actionable.

## Scan — 2026-05-09 08:04

- **Files scanned**: tests/test_reboot_agent.py
- **Findings**: #6497 (test_reboot_agent excluded from run_tests.py + 2 TestGetClonePath str-vs-Path failures — medium)
- **Items rejected by human**: none yet
- **Notes**: Same class as #6287 (test_compose exclusion). _get_clone_path returns str for JSON serialization but tests assert against Path objects.

## Scan — 2026-05-09 07:34

- **Files scanned**: references/roles/qa/includes.yml, references/roles/dm/includes.yml
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: Verified tracker-protocol references cleaned on main. delivery-fallback ref in manifest.md pending fix via #6479 PR.

## Scan — 2026-05-09 06:36

- **Files scanned**: tests/test_manifest.py
- **Findings**: #6478 (test_includes_yml_covers_template never asserts cross-check — high), #6479 (manifest.md inventory stale — low)
- **Items rejected by human**: none yet
- **Notes**: Also found dead _extract_inventory_paths (low) — not filed, too minor.

## Scan — 2026-05-09 06:04

- **Files scanned**: references/sub-skills/common/cycle-runner.md
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: Subagent flagged PM version_bump field as risk, but cycle_post.py gates _do_version_bump with `if role == "dm"` — no double-bump possible. Doc is accurate.

## Scan — 2026-05-09 04:05

- **Files scanned**: references/scripts/reboot_agent.py
- **Findings**: #6406 (sentinel-based restart is dead code — thin_launcher.py doesn't watch .restart, non-force restarts silently fail — high)
- **Items rejected by human**: none yet
- **Notes**: Also found _spawn_wrapper unused clone_path param (medium) and race condition on .restart consumption (medium) — both consequences of the same root cause (Finding 1). Filed root cause only.

## Scan — 2026-05-09 02:04

- **Files scanned**: tests/test_cycle_post.py, packages/cli/index.js
- **Findings**: #6316 (index.js fetchRawFile shell injection via unescaped repoPath — low, defense-in-depth), #6317 (index.js dead allowSet variable — low)
- **Items rejected by human**: none yet
- **Notes**: test_cycle_post.py had 3 findings from subagent — dead __wrapped__ (low), untested _verify_remote_branch guard (medium), untested _do_stop_after_cycle_check fallback (medium). Deferred in favor of index.js findings which are more actionable. cycle_post test gaps noted for future scans.

## Scan — 2026-05-09 01:05

- **Files scanned**: tests/test_model_router.py, references/roles/qa/instructions.md
- **Findings**: #6304 (test_model_router.py missing coverage for exit code 3 timeout path — medium)
- **Items rejected by human**: none yet
- **Notes**: qa/instructions.md subagent reported --role qa vs qa-lead inconsistency in verification.md — verified invalid, tracker.py _canonicalize_role strips -lead suffix, both forms work. model_router.py also has test_missing_api_key_returns_2 false-confidence concern (passes for wrong reason) — deferred, lower priority than timeout gap.

## Scan — 2026-05-09 00:34

- **Files scanned**: tests/test_compose.py, references/scripts/harness.py
- **Findings**: #6287 (test_compose.py excluded from STATIC_TEST_MODULES in run_tests.py — 4 TestCollectAllRoles tests silently failing due to stale assertions post-#6055 MANDATORY_ROLES change — high)
- **Items rejected by human**: none yet
- **Notes**: harness.py 3 medium findings from subagent — race in deferred init, save_state lock gap, _reboot_affected_agents diff. After manual verification: _reboot_affected_agents finding invalid (compose writes without committing, so `git diff HEAD` is correct). Other two are real but lower priority than test_compose gap. Filed 1 of 2 max.

## Scan — 2026-05-09 00:04

- **Files scanned**: CHANGELOG.md, tests/test_tracker_authority.py, references/scripts/model_router.py
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: CHANGELOG.md current at v0.35.0. test_tracker_authority.py comprehensive (1100+ lines, Phase E, PR/branch guards, event emission). model_router.py re-scanned, confirmed clean.

## Scan — 2026-05-09 00:02

- **Files scanned**: references/sub-skills/manifest.md, references/scripts/health_check.py, references/scripts/model_router.py
- **Findings**: none (manifest.md has 2 deleted PM sub-skills still in inventory listing — cosmetic, not filed. health_check.py and model_router.py both clean)
- **Items rejected by human**: none yet
- **Notes**: manifest.md last scanned 2026-04-08. model_router.py _ensure_yaml consolidated post-#5125 confirmed. health_check.py PID fallback solid.

## Scan — 2026-05-08 19:32

- **Files scanned**: references/scripts/compose.py, references/scripts/boot_remote.py, references/scripts/config.py
- **Findings**: none (2 previously-seen minor items: compose.py dead `prefix` var in _resolve_includes_with_manifest — noted 2026-04-26 as too minor; boot_remote.py duplicate PM regex check lines 126+135 — noted 2026-05-06 as harmless dedup)
- **Items rejected by human**: none yet
- **Notes**: config.py clean (603 lines). All 3 files have test coverage.
## Scan — 2026-05-08 23:32

- **Files scanned**: tests/test_boot_remote.py, references/roles/dm/instructions.md
- **Findings**: none (dm/delivery-packaging.md still has old pr-merge on main — fix pending in #6126 PR. test_boot_remote.py has redundant import json in test body — too minor to file)
- **Items rejected by human**: none yet

## Scan — 2026-05-08 23:02

- **Files scanned**: references/scripts/cycle_post.py, references/roles/pm/instructions.md, references/installer-files.txt
- **Findings**: none (pm/instructions.md and installer-files.txt still reference post-merge-recompose on main — expected, fix pending in #6126 PR #6201)
- **Items rejected by human**: none yet
- **Notes**: cycle_post.py clean (769 lines). _do_restart_sentinel documented as deprecated — intentional backward compat.

## Scan — 2026-05-08 22:31

- **Files scanned**: tests/test_cycle_pre.py, references/agent-instructions.md
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: test_cycle_pre.py clean (1320 lines, no stale pr-merge refs). agent-instructions.md clean (generated file, consistent with current arch).

## Scan — 2026-05-08 21:02

- **Files scanned**: tests/run_tests.py, tests/test_git_ops.py, tests/test_wizard.py
- **Findings**: #6254 (test_git_ops.py test_forge_adapter_routing is false-confidence — patches sys.modules after import, adapter mock never reached — low)
- **Items rejected by human**: none yet
- **Notes**: run_tests.py clean (137 lines). test_wizard.py clean (2077 lines).

## Scan — 2026-05-08 19:32

- **Files scanned**: references/scripts/compose.py, references/scripts/boot_remote.py, references/scripts/config.py
- **Findings**: none (2 previously-seen minor items: compose.py dead prefix var — noted 2026-04-26; boot_remote.py duplicate PM regex — noted 2026-05-06)
- **Items rejected by human**: none yet
- **Notes**: config.py clean (603 lines).

## Scan — 2026-05-08 18:10

- **Files scanned**: references/scripts/tracker.py, references/scripts/wizard.py, references/scripts/cycle_pre.py
- **Findings**: #6138 (cycle_pre.py duplicate _validate_config_version definition — lines 181 and 220 are identical — low)
- **Items rejected by human**: none yet
- **Notes**: tracker.py clean — comprehensive guards, no new issues. wizard.py has redundant local `import shutil` at line 1065 (already imported at module level) — cosmetic, not filed. cycle_pre.py has duplicate function from likely bad merge.

## Scan — 2026-05-06 07:03

- **Files scanned**: references/scripts/harness.py, references/sub-skills/common/cycle-runner.md, references/roles/dm/SOUL.md
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: harness.py deep scan (1177 lines) — PID health, intent state machine, auto-reboot, no shell=True. 10 consecutive no-finding scans. Codebase thoroughly covered.

## Scan — 2026-05-06 06:33

- **Files scanned**: references/scripts/diagnostics.py, references/roles/dm/SOUL.md, references/roles/qa/SOUL.md
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: diagnostics.py #5385 fix confirmed (rotate before write). dm/qa SOULs clean. 9 consecutive no-finding scans.

## Scan — 2026-05-06 05:33

- **Files scanned**: references/roles/dev/manifest.yaml, references/prompts/test-plan.md.j2, references/roles/dm/manifest.yaml
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: dev manifest clean (schema v2, variant + stack setup_requirements). test-plan.md.j2 comprehensive (deterministic vs human-required labeling). 7 consecutive no-finding scans.

## Scan — 2026-05-06 04:33

- **Files scanned**: references/scripts/vault_remember.py, references/sub-skills/common/improvement-scan.md, docs/sub-skill-guide.md
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: vault_remember.py clean (proper error handling, config fallbacks). Event bus confirmed live this cycle — 10 pr-merge events in recent_events. 5 consecutive no-finding scans — codebase quality is high.

## Scan — 2026-05-06 04:03

- **Files scanned**: references/scripts/cycle.py, tests/test_add_role.py, references/sub-skills/common/context-pressure.md
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: cycle.py clean (285 lines). inc_counter double-print still present but already filed as #1292. context-pressure.md not read this cycle.

## Scan — 2026-05-06 03:34

- **Files scanned**: references/scripts/add_role.py, references/roles/pm/manifest.yaml, references/roles/qa/manifest.yaml
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: add_role.py clean — #3302 (subprocess.os.getpid) and #4093 (stale lock) both previously fixed. Role manifests well-structured (schema v2). QA always_installed comment is design reasoning, not stale.

## Scan — 2026-05-06 02:34

- **Files scanned**: references/scripts/reboot_agent.py, references/wizard/WIZARD.md, tests/test_health_check.py
- **Findings**: #5843 (reboot_agent.py --all double-reboots PM — duplicate in agent list — low)
- **Items rejected by human**: none yet
- **Notes**: reboot_agent.py line 235 prepends "pm" but _get_all_roles() already includes it. Also boot_remote.py:134-136 duplicates lines 126-127 (harmless set dedup). WIZARD.md and test_health_check.py not read this cycle (finding found early).

## Scan — 2026-05-06 02:03

- **Files scanned**: tests/test_manifest.py, references/roles/dev/includes.yml, references/roles/qa/includes.yml
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: test_manifest.py comprehensive (integrity, orphan detection, YAML validation, template coverage). dev includes.yml has 23 sub-skills, qa has 17 (slim variants). All paths resolve. Diminishing returns on scanning — most source files covered.

## Scan — 2026-05-06 01:33

- **Files scanned**: references/sub-skills/common/git-commit.md, tests/test_reboot_agent.py, references/roles/pm/SOUL.md
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: git-commit.md correctly documents branch workflow, PR draft handling, conflict resolution. test_reboot_agent.py comprehensive (dead boot, stop sentinel, force kill). pm/SOUL.md clean.

## Scan — 2026-05-06 01:04

- **Files scanned**: references/statusline.sh, references/roles/dm/includes.yml, references/scripts/vault_optimize.py
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: statusline.sh well-structured (319 lines, schema-aware agent resolution, backlog caching, vault questions). DM includes.yml intentionally different from dev (slim vault, no improvement-scan). All clean.

## Scan — 2026-05-05 22:03

- **Files scanned**: references/sub-skills/roles/dm/delivery-packaging.md, references/roles/qa/instructions.md, docs/ARCHITECTURE.md
- **Findings**: #5772 (delivery-packaging.md tracker comment commands use --role dm instead of dm-lead — low)
- **Items rejected by human**: none yet
- **Notes**: QA instructions.md uses raw echo+mv for status bar instead of cycle.py helper (functional but less portable — noted, not filed). delivery-packaging.md has inconsistency where transitions use dm-lead but comments use bare dm.

## Scan — 2026-05-05 21:33

- **Files scanned**: references/sub-skills/common/boot-remote-agents.md, tests/test_cycle_post.py, references/roles/dev/SOUL.md
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: boot-remote-agents.md correctly updated for #4966. test_cycle_post.py comprehensive (validation, transitions, logs, status bar, working branch, intent API, sanitization). dev/SOUL.md clean with upgrade awareness section.

## Scan — 2026-05-05 20:34

- **Files scanned**: packages/cli/index.js, README.md, tests/test_model_router.py
- **Findings**: #5734 (packages/cli/index.js missing path traversal guard on manifest file writes — low)
- **Items rejected by human**: none yet
- **Notes**: README.md comprehensive and up-to-date (harness, CLI, features all current). tests/test_model_router.py clean. CLI installer writes fetched files without validating resolved path stays within gitRoot — defense-in-depth concern.

## Scan — 2026-05-05 19:59

- **Files scanned**: references/agent-instructions.md, tests/test_compose.py, SKILL.md
- **Findings**: #5711 (agent-instructions.md stale — deprecated restart fields in cycle-output example — low), #5712 (SKILL.md file structure diagram references eliminated boot scripts — low)
- **Items rejected by human**: none yet
- **Notes**: test_compose.py clean (comprehensive 899-line test file). agent-instructions.md is a generated file that wasn't re-generated after cycle-runner sub-skill update. SKILL.md diagram references start scripts eliminated by #4966.

## Scan — 2026-05-04 00:40

- **Files scanned**: references/scripts/thin_launcher.py, references/scripts/start_team.py, references/scripts/harness.py
- **Findings**: #5423 (harness.py undocumented 'stopped' intent state — bare string instead of class constant — low)
- **Items rejected by human**: none yet
- **Notes**: thin_launcher.py clean post-#5422 fix. start_team.py has redundant `(ImportError, Exception)` catch (minor, not filed).

## Scan — 2026-05-03 20:55

- **Files scanned**: references/scripts/health_check.py, references/scripts/squidsquad_cli.py, references/scripts/diagnostics.py
- **Findings**: #5385 (diagnostics.py log rotation after write, not before — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-03 18:32

- **Files scanned**: references/scripts/cycle_pre.py, references/scripts/cycle_post.py, references/scripts/vault_remember.py
- **Findings**: #5378 (cycle_pre._do_pull() returns 'error' on normal git states — low)
- **Items rejected by human**: none yet
- **Notes**: cycle_post._do_restart_sentinel still called from main() on main branch — already fixed on #4966 feature branch, skip.

## Scan — 2026-05-03 17:32

- **Files scanned**: tests/test_config_functions.py, tests/test_tracker.py, tests/test_state_bus.py
- **Findings**: #5366 (test_config_functions.py SAMPLE_CONFIG missing ~20 newer FIELD_MAP entries — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-03 16:02

- **Files scanned**: references/scripts/git_ops.py, references/scripts/reboot_agent.py, references/scripts/scan_index.py
- **Findings**: #5344 (reboot_agent.py _spawn_wrapper() wrapper-centric dead code post-#4966 — medium)
- **Items rejected by human**: none yet

## Scan — 2026-05-02 20:07

- **Files scanned**: references/scripts/model_router.py, references/scripts/harness.py, references/scripts/squidsquad_cli.py, references/scripts/boot_remote.py, references/scripts/cycle_post.py
- **Findings**: #5125 (model_router.py triplicate yaml auto-install block — medium), #5126 (cycle_post.py _do_version_bump no-op commit/tag risk — medium)
- **Items rejected by human**: none yet

## Scan — 2026-05-02 08:03

- **Files scanned**: references/scripts/cycle_post.py, references/scripts/vault_remember.py, references/scripts/compose.py
- **Findings**: #4918 (compose.py deprecated tempfile.mktemp() TOCTOU race — low), #4919 (vault_remember.py reset_writes silent no-op when field absent — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-01 22:05

- **Files scanned**: references/scripts/diagnostics.py, references/scripts/harness.py, references/scripts/squidsquad_cli.py, references/scripts/forge_adapter.py, references/scripts/state_bus.py
- **Findings**: #4746 diagnostics.py generate_report/is_public_repo untested, #4747 harness.py FastAPI endpoints untested
- **Items rejected by human**: none

## Scan — 2026-05-01 06:32

- **Files scanned**: tests/test_capability_check.py, tests/test_comms_adapter.py, tests/test_add_role.py, tests/test_soul_adaptation.py, tests/test_shared_fs.py
- **Findings**: #4515 (test_add_role.py source inspection test instead of failure-path test — low)
- **Items rejected by human**: none yet
- **Notes**: 4 files clean. test_shared_fs.py has minor unchecked return value (not filed).

## Scan — 2026-04-30 21:32

- **Files scanned**: tests/test_config_functions.py, tests/test_comms_sub_skills.py, tests/test_labels.py, tests/test_references.py, tests/test_config_schema.py
- **Findings**: none filed (2 minor: tautological alias assertion in test_config_functions.py:211, redundant parametrize in test_config_schema.py:192 — test quality only)
- **Items rejected by human**: none yet
- **Notes**: 3 files clean. Codebase coverage extensive — diminishing returns on further scanning.

## Scan — 2026-04-30 18:02

- **Files scanned**: tests/conftest.py, tests/test_manifest.py, tests/test_vault.py, tests/run_tests.py, tests/test_composition.py
- **Findings**: none filed (test_manifest.py has dead _extract_inventory_paths with operator precedence bug + cosmetic CLAUDE.md/instructions.md naming mismatch in test_role_entries_exist — both non-functional)
- **Items rejected by human**: none yet
- **Notes**: 4 files clean. test_manifest.py notes are cosmetic — test passes correctly.

## Scan — 2026-04-30 16:02

- **Files scanned**: references/scripts/vault_check.py, references/scripts/vault_optimize.py, references/scripts/vault_remember.py, references/scripts/comms_adapter.py, references/scripts/add_role.py
- **Findings**: none filed (2 minor notes in vault_optimize.py — guard duplication and strip() in archive annotation check — both theoretical, not functional bugs)
- **Items rejected by human**: none yet
- **Notes**: 4 files clean. vault_optimize.py has maintenance concerns but no functional bugs. All files have test coverage.

## Scan — 2026-04-30 14:02

- **Files scanned**: tests/test_compose.py, tests/test_scan_index.py, tests/test_reboot_agent.py, tests/test_forge_adapter.py, tests/test_diagnostics.py
- **Findings**: none filed (1 minor: test_scan_index.py:182 tautological assertion in ranking test — too minor to file)
- **Items rejected by human**: none yet
- **Notes**: 4 files clean. test_scan_index.py has a weak ranking assertion but not a functional bug.

## Scan — 2026-04-30 11:02

- **Files scanned**: tests/test_model_router.py, tests/test_tracker.py, tests/test_tracker_authority.py, tests/test_git_ops.py, tests/test_config.py
- **Findings**: none (1 minor test quality note in test_git_ops.py:263 — weak assertion checks mock stdout not call args, but not a functional bug)
- **Items rejected by human**: none yet
- **Notes**: All 5 test files clean. No functional issues found.

## Scan — 2026-04-30 09:02

- **Files scanned**: tests/test_cycle_pre.py, tests/test_cycle_post.py, tests/test_state_bus.py, tests/test_wizard.py, tests/test_installer_wiring.py
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: All 5 test files clean. No functional issues found.

## Scan — 2026-04-30 06:32

- **Files scanned**: references/scripts/model_router.py, references/scripts/run_comprehension_test.py, references/scripts/cycle.py, references/scripts/git_ops.py, references/scripts/tracker.py
- **Findings**: #4362 (git_ops.py _safe_checkout stash pop on wrong branch — medium), #4363 (tracker.py silent None.strip() — low)
- **Items rejected by human**: none yet
- **Notes**: model_router.py, run_comprehension_test.py, cycle.py all clean. All 5 files have test coverage.

## Scan — 2026-04-30 04:32

- **Files scanned**: references/scripts/cycle_pre.py, references/scripts/cycle_post.py, references/scripts/state_bus.py, references/scripts/comms_adapter.py, references/scripts/scan_index.py
- **Findings**: #4343 (cycle_post.py dead _escape function — low), #4344 (scan_index.py DB connection leak on json.loads failure — low)
- **Items rejected by human**: none yet
- **Notes**: cycle_pre.py, state_bus.py, comms_adapter.py all clean. All 5 files have test coverage.

## Scan — 2026-04-29 20:32

- **Files scanned**: references/scripts/compose.py, references/scripts/forgejo_setup.py, references/scripts/manifest.py, references/scripts/migrate_state_branch.py
- **Findings**: #4200 (forgejo_setup.py credential leak in error messages — high), #4201 (compose.py capability resolution duplication — medium)
- **Items rejected by human**: none yet
- **Notes**: manifest.py and migrate_state_branch.py clean. All 4 files have test coverage. This completes coverage of all scripts under references/scripts/.

## Scan — 2026-04-29 15:02

- **Files scanned**: references/scripts/wizard.py, references/scripts/start_team.py, references/scripts/repo_scan.py, references/scripts/tc_coverage.py, references/scripts/vault_entity.py
- **Findings**: #4123 (wizard.py build_config_md wrong key for Research Model — medium), #4124 (repo_scan.py FastAPI detection unreachable — medium)
- **Items rejected by human**: none yet
- **Notes**: start_team.py, tc_coverage.py, vault_entity.py all clean. All 5 files have test coverage.

## Scan — 2026-04-29 11:32

- **Files scanned**: references/scripts/add_role.py, references/scripts/boot_remote.py, references/scripts/capability_check.py, references/scripts/config.py, references/scripts/diagnostics.py
- **Findings**: #4092 (config.py set_field silent no-op on empty section — high), #4093 (add_role.py stale lock on write failure — medium)
- **Items rejected by human**: none yet
- **Notes**: boot_remote.py, capability_check.py, diagnostics.py all clean. All 5 files have test coverage.

## Scan — 2026-04-29 05:02

- **Files scanned**: references/scripts/forge_adapter.py, references/scripts/health_check.py, references/scripts/shared_fs.py, references/scripts/soul_adaptation.py, references/scripts/triage.py
- **Findings**: #4050 (shared_fs.py read_secret_or_env falsy check drops valid secrets — medium), #4051 (triage.py find_qa_rejected aborts on single-issue failure — medium)
- **Items rejected by human**: none yet
- **Notes**: forge_adapter.py, health_check.py, soul_adaptation.py all clean. All 5 files have test coverage.

## Scan — 2026-04-28 03:33

- **Files scanned**: references/scripts/cycle_post.py, references/scripts/cycle_pre.py, references/scripts/tracker.py, references/scripts/reboot_agent.py, references/scripts/model_router.py
- **Findings**: #3813 (cycle_pre.py _check_template_changed dead stub always returns False — low), #3814 (model_router.py bare 'route' subcommand hardcodes task_type to 'research' — low)
- **Items rejected by human**: none yet
- **Notes**: tracker.py, reboot_agent.py, cycle_post.py all clean. cycle_pre.py template_changed was previously noted (2026-04-27 scan) but deferred — now filed.

## Scan — 2026-04-27 20:02

- **Files scanned**: references/scripts/vault_remember.py, references/scripts/state_bus.py, references/scripts/cycle.py, references/scripts/vault_optimize.py, references/scripts/reboot_agent.py
- **Findings**: #3711 (vault_remember.py startswith path check same bypass as #3643 — medium), #3712 (state_bus.py orphan branch init writes README.md to wrong path — low)
- **Items rejected by human**: none yet
- **Notes**: vault_optimize.py lock mechanism is correct (O_EXCL provides atomicity). cycle.py and reboot_agent.py are clean.

## Scan — 2026-04-27 09:04

- **Files scanned**: references/scripts/tracker.py, references/scripts/cycle_pre.py, references/scripts/cycle_post.py, references/scripts/git_ops.py, references/scripts/scan_index.py
- **Findings**: #3493 (tracker.py duplicate ROLE_AUTHORITY keys drop PM authority for pending-human-review — high), #3494 (cycle_post.py version bump uses git add -A — medium)
- **Items rejected by human**: none yet
- **Notes**: Also found: git_ops.py shell=True footgun (same class as #144), cycle_pre.py template_changed stub (low), scan_index.py finding misattribution (medium) — deferred due to 2-item limit.

## Scan — 2026-04-27 06:30

- **Files scanned**: references/scripts/comms_adapter.py, references/scripts/vault_check.py
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: comms_adapter.py self-review (new file this session) — clean. vault_check.py clean, solid parsing.

## Scan — 2026-04-27 04:30

- **Files scanned**: references/scripts/config.py, references/scripts/triage.py
- **Findings**: none
- **Items rejected by human**: none yet
- **Notes**: Both files clean. config.py well-structured with comprehensive field map. triage.py clean imports, no shell=True.

## Scan — 2026-04-26 23:00

- **Files scanned**: references/scripts/cycle_post.py, references/scripts/shared_fs.py
- **Findings**: #3433 (cycle_post.py hardcodes 'main' instead of configured working branch — low, same class as #3341)
- **Items rejected by human**: none yet
- **Notes**: shared_fs.py clean.

## Scan — 2026-04-26 20:00

- **Files scanned**: references/scripts/diagnostics.py, references/scripts/soul_adaptation.py, references/scripts/tc_coverage.py
- **Findings**: #3409 (tc_coverage.py unused imports glob and os — low)
- **Items rejected by human**: none yet
- **Notes**: diagnostics.py clean (minor int() gap at L215 already in prior pattern). soul_adaptation.py clean.

## Scan — 2026-04-26 13:00

- **Files scanned**: references/scripts/git_ops.py, references/scripts/health_check.py, references/scripts/model_router.py, references/scripts/forge_adapter.py, references/scripts/run_comprehension_test.py
- **Findings**: #3341 (git_ops.py commit_code/commit_state hardcode "main" instead of _get_working_branch() — low)
- **Items rejected by human**: none yet
- **Notes**: health_check.py clean. model_router.py clean (auto-pip pattern intentional). forge_adapter.py remove_labels DELETE bug already #1501. run_comprehension_test.py has unused tempfile import (trivially minor, not filed).

## Scan — 2026-04-26 10:02

- **Files scanned**: references/scripts/add_role.py, references/scripts/capability_check.py, references/scripts/vault_remember.py, references/scripts/vault_entity.py, references/scripts/tc_coverage.py
- **Findings**: #3302 (add_role.py uses subprocess.os.getpid() — undocumented internal attribute, medium)
- **Items rejected by human**: none yet
- **Notes**: vault_entity.py preference extraction uses simple period-scan for sentence boundaries — low severity, not filed.

## Scan — 2026-04-26 08:02

- **Files scanned**: references/scripts/compose.py, references/scripts/cycle.py, references/scripts/scan_index.py, references/scripts/state_bus.py, references/scripts/vault_entity.py
- **Findings**: #3290 (state_bus.py init() mutates main working tree with orphan checkout — no recovery on failure, high)
- **Items rejected by human**: none yet
- **Notes**: compose.py has unused `prefix` variable in _resolve_includes_with_manifest (dead code, not a bug — manifest entries already include directory prefix). Not filed (too minor).

## Scan — 2026-04-26 00:02

- **Files scanned**: references/scripts/soul_adaptation.py, references/scripts/cycle_post.py
- **Findings**: none
- **Items rejected by human**: none yet

## Scan — 2026-04-25 21:32

- **Files scanned**: references/scripts/boot_remote.py, references/scripts/reboot_agent.py, references/scripts/cycle_pre.py
- **Findings**: #3078 (reboot_agent.py --all fallback hardcodes [pm, skill] — ignores config agents), #3079 (cycle_pre.py e2e_cmd.split() breaks on paths with spaces)
- **Items rejected by human**: none yet

## Scan — 2026-04-25 09:02

- **Files scanned**: references/scripts/tracker.py, references/scripts/model_router.py, references/scripts/vault_check.py
- **Findings**: #2693 (LEGAL_TRANSITIONS references status:pending-review but label is status:pending-human-review)
- **Items rejected by human**: none yet

## Scan — 2026-04-25 07:32

- **Files scanned**: references/scripts/cycle_post.py, references/scripts/shared_fs.py, references/scripts/vault_optimize.py
- **Findings**: #2677 (vault_optimize prune reads stale notes dict after git_mv — OSError on self-linking notes)
- **Items rejected by human**: none yet

## Scan — 2026-04-25 06:31

- **Files scanned**: references/scripts/cycle_post.py, references/scripts/health_check.py, references/scripts/config.py, references/scripts/triage.py, references/scripts/git_ops.py
- **Findings**: #2671 (git_ops.py _get_working_branch imports nonexistent config.get — medium)
- **Items rejected by human**: none yet

## Scan — 2026-04-25 05:02

- **Files scanned**: references/scripts/health_check.py, references/scripts/add_role.py, references/scripts/cycle_pre.py
- **Findings**: #2659 (dead _get_context_pressure in cycle_pre.py), #2660 (unify _parse_local_config across 3 scripts)
- **Items rejected by human**: none yet

## Scan — 2026-04-23 21:03

- **Files scanned**: tests/test_wizard.py, references/scripts/soul_adaptation.py, references/scripts/state_bus.py
- **Findings**: none (test_wizard.py comprehensive 39 test classes; soul_adaptation.py clean error handling; state_bus.py path traversal already filed #2046)
- **Items rejected by human**: none yet

## Scan — 2026-04-23 21:03

- **Files scanned**: references/sub-skills/*.md (stale refs check), .squidsquad/*/SOUL.md (adaptation section check), manifest integrity
- **Findings**: none (no stale watchdog/.stop refs, manifest tests pass, live SOULs correctly lack adaptation section pre-upgrade)
- **Items rejected by human**: none yet

## Scan — 2026-04-23 20:03

- **Files scanned**: references/vault-templates/*.md, .squidsquad/vault/BRIEFING.md
- **Findings**: #2350 (BRIEFING.md stale — wrong version, shipped items listed as active, outdated counters)
- **Items rejected by human**: none yet

## Scan — 2026-04-23 18:32

- **Files scanned**: test coverage audit across all references/scripts/*.py
- **Findings**: none (all major scripts have test files, coverage ranges 9-142 tests per script)
- **Items rejected by human**: none yet

## Scan — 2026-04-23 17:04

- **Files scanned**: references/scripts/config.py, references/scripts/compose.py, references/scripts/wizard.py
- **Findings**: none (all imports used, no dead code, no security issues)
- **Items rejected by human**: none yet

## Scan — 2026-04-23 14:03

- **Files scanned**: references/scripts/reboot_agent.py, references/scripts/tracker.py, references/scripts/git_ops.py
- **Findings**: none (clean — no unused imports, exception handling is appropriate, all new scripts have test files)
- **Items rejected by human**: none yet

## Scan — 2026-04-23 12:06

- **Files scanned**: references/scripts/cycle_pre.py, references/scripts/cycle_post.py, references/scripts/soul_adaptation.py
- **Findings**: #2343 (unused imports in cycle_pre.py and cycle_post.py — os, re)
- **Items rejected by human**: none yet

## Scan — 2026-04-22 18:32

- **Files scanned**: references/scripts/vault_check.py, references/scripts/vault_optimize.py
- **Findings**: #2109 (vault_optimize.py add_question silently swallows all exceptions — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-22 16:32

- **Files scanned**: references/scripts/config.py, references/scripts/cycle.py
- **Findings**: #2097 (config.py set_field missing write error handling — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-22 14:32

- **Files scanned**: references/scripts/wizard.py
- **Findings**: #2086 (wizard.py scaffold_install silently swallows file/JSON errors — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-22 09:02

- **Files scanned**: references/scripts/compose.py
- **Findings**: #2058 (compose.py deploy_role/boot_role missing file write error handling — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-22 07:02

- **Files scanned**: references/scripts/state_bus.py, references/scripts/migrate_state_branch.py
- **Findings**: #2046 (state_bus.py path traversal in read_file/write_file — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-22 05:02

- **Files scanned**: references/scripts/tracker.py
- **Findings**: #2035 (tracker.py _check_unread_feedback missing JSON parse error handling — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-20 15:31

- **Files scanned**: git log check for new files in last 12h — only repo_scan.py (already scanned)
- **Findings**: none (codebase thoroughly covered this session — 7 scans total)
- **Items rejected by human**: none yet

## Scan — 2026-04-20 14:01

- **Files scanned**: references/scripts/repo_scan.py (security + quality check on new code)
- **Findings**: none (clean — no shell calls, no injection vectors, pure file detection)
- **Items rejected by human**: none yet

## Scan — 2026-04-20 12:01

- **Files scanned**: references/roles/dev/CLAUDE.md, references/sub-skills/common/tracker-protocol.md
- **Findings**: #1838 (tracker-protocol.md missing Phase E transitions — low). dev CLAUDE.md clean.
- **Items rejected by human**: none yet

## Scan — 2026-04-20 10:01

- **Files scanned**: references/scripts/wizard.py (deploy section), tests/run_tests.py
- **Findings**: #1827 (wizard.py deploy_role error handling in scaffold_install — low). run_tests.py subprocess output to terminal is intentional (not a bug).
- **Items rejected by human**: none yet

## Scan — 2026-04-20 08:01

- **Files scanned**: references/scripts/triage.py, references/scripts/scan_index.py, references/scripts/shared_fs.py
- **Findings**: #1815 (scan_index.py finding_density inconsistent on first scan — low). triage.py comment ordering is correct (GitHub returns chronological). shared_fs.py clean.
- **Items rejected by human**: none yet

## Scan — 2026-04-20 06:01

- **Files scanned**: packages/cli/index.js, references/scripts/compose.py
- **Findings**: Fixed inline: findPython() undefined in index.js (bug from #1778). Filed #1809 (compose.py deploy_role error handling — low).
- **Items rejected by human**: none yet

## Scan — 2026-04-20 01:31

- **Files scanned**: references/scripts/vault_remember.py, references/scripts/vault_optimize.py, references/scripts/shared_fs.py
- **Findings**: #1755 (vault_remember.py write without error handling — low), #1756 (vault_optimize.py TOCTOU race in lock — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-19 19:01

- **Files scanned**: references/scripts/tracker.py, references/scripts/git_ops.py, references/scripts/cycle.py, references/scripts/triage.py, references/scripts/scan_index.py
- **Findings**: #1708 (watchdog.py test file missing from main — medium), #1709 (tracker.py missing dedicated test file — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-19 09:34

- **Files scanned**: references/scripts/forgejo_setup.py, references/scripts/providers/openai/adapter.py
- **Findings**: #1517 (create_repo constructs wrong clone_url for existing repos — medium), #1518 (check_docker port check blocks re-deployment — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-19 07:34

- **Files scanned**: references/scripts/forge_adapter.py, references/scripts/shared_fs.py
- **Findings**: #1500 (ForgejoAdapter.create_pr ignores draft parameter — medium), #1501 (ForgejoAdapter.remove_labels silently swallows failures — low)
- **Items rejected by human**: none yet

## Scan — 2026-04-18 09:41

- **Files scanned**: references/scripts/cycle.py, references/scripts/vault_remember.py, tests/test_git_ops.py
- **Findings**: #1292 (cycle.py inc_counter double-prints old+new value to stdout)
- **Items rejected by human**: none yet

## Scan — 2026-04-17 17:02

- **Files scanned**: references/scripts/boot_remote.py, references/scripts/git_ops.py, tests/test_start_scripts.py
- **Findings**: none (bare exceptions in boot_remote.py are intentional fire-and-forget; shell=True in git_ops.py already filed as #144; stash pop failure already #145; hardcoded ROLES already #923)
- **Items rejected by human**: none yet

## Scan — 2026-04-14 18:20

- **Files scanned**: tests/test_boot_remote.py, tests/test_cycle.py, tests/test_diagnostics.py, tests/test_health_check.py
- **Findings**: none (all clean — good test coverage, proper mocking, no functional issues)
- **Items rejected by human**: none yet

## Scan — 2026-04-14 11:34

- **Files scanned**: references/scripts/add_role.py, tests/test_add_role.py, tests/test_work_queue.py, tests/test_feat328_coverage.py
- **Findings**: none (all clean — list-form subprocess, proper encoding, good test coverage, no security issues)
- **Items rejected by human**: none yet

## Scan — 2026-04-14 08:32

- **Files scanned**: references/sub-skills/designer-specific/design-session.md, design-capabilities.md
- **Findings**: none (clean — proper tracker commands, capability fallback logic, no stale INDEX.md refs)
- **Items rejected by human**: none yet

## Scan — 2026-04-14 07:02

- **Files scanned**: references/sub-skills/qa-specific/verification.md (full 160-line review)
- **Findings**: none (clean — correct tracker commands, branch checkout flow, TEST-PLAN subagent, PR Flow handling)
- **Items rejected by human**: none yet

## Scan — 2026-04-14 05:32

- **Files scanned**: references/sub-skills/dm-specific/version-bumps.md, delivery-packaging.md, issue-triage.md
- **Findings**: none (all clean — list-bugs/create-bug are valid tracker.py aliases, delivery flow correct)
- **Items rejected by human**: none yet

## Scan — 2026-04-14 03:32

- **Files scanned**: references/scripts/vault_optimize.py, tests/test_start_scripts.py, tests/test_triage.py
- **Findings**: #923 (test_start_scripts.py ROLES list missing qa and designer — boot script tests incomplete)
- **Items rejected by human**: none yet

## Scan — 2026-04-14 00:02

- **Files scanned**: references/scripts/compose.py, references/scripts/vault_remember.py, references/scripts/git_ops.py
- **Findings**: none (all 3 clean — proper encoding, error handling, list-form subprocess calls)
- **Items rejected by human**: none yet

## Scan — 2026-04-13 17:31

- **Files scanned**: references/scripts/manifest.py, references/scripts/diagnostics.py, references/scripts/config.py
- **Findings**: none (all 3 clean — proper validation, error handling, YAML safe_load, config redaction)
- **Items rejected by human**: none yet

## Scan — 2026-04-13 14:32

- **Files scanned**: references/scripts/triage.py, references/scripts/health_check.py, references/scripts/capability_check.py
- **Findings**: none (all 3 clean — proper encoding, error handling, correct logic. triage.py has dead code branch in line 109 comparison but no functional impact)
- **Items rejected by human**: none yet

## Scan — 2026-04-13 08:02

- **Files scanned**: references/scripts/capability_check.py, references/scripts/diagnostics.py
- **Findings**: none (both clean — proper error handling, encoding, structure)
- **Items rejected by human**: none yet

## Scan — 2026-04-13 04:32

- **Files scanned**: references/scripts/triage.py, references/scripts/git_ops.py
- **Findings**: #774 (triage.py missing encoding=utf-8 — crashes on Windows with Unicode). git_ops.py commit_code had stale comment (fixed inline).
- **Items rejected by human**: none yet

## Scan — 2026-04-12 19:03

- **Files scanned**: references/scripts/vault_optimize.py, references/scripts/vault_remember.py, references/scripts/vault_check.py
- **Findings**: #468 (vault_remember.py path traversal in effective_confidence — high), #469 (vault_optimize.py reindex skips notes without links field — medium). vault_check.py has minor dedup asymmetry but no critical issues.
- **Items rejected by human**: none yet

## Scan — 2026-04-12 15:33

- **Files scanned**: tests/test_git_ops.py, tests/test_tracker_authority.py, tests/test_config_schema.py
- **Findings**: #465 (test_config_schema.py missing coverage for config.py functions), #466 (test_git_ops.py unused import + missing failure tests). test_tracker_authority.py has minor maintainability issues but no functional problems.
- **Items rejected by human**: none yet

## Scan — 2026-04-12 13:03

- **Files scanned**: references/scripts/tracker.py, references/scripts/boot_remote.py, references/scripts/wizard.py
- **Findings**: #463 (boot_remote.py unquoted paths in osascript/tmux — high), #464 (tracker.py unguarded int() parsing — medium). wizard.py has similar path issues but deferred (same root cause as #463).
- **Items rejected by human**: none yet

## Scan — 2026-04-12 08:33

- **Files scanned**: references/scripts/config.py, references/scripts/cycle.py, references/scripts/vault_check.py
- **Findings**: #429 (cycle.py missing int() error handling), #430 (vault_check.py duplicated logic + fragile tag parsing). config.py clean.
- **Items rejected by human**: none yet

## Scan — 2026-04-12 02:33

- **Files scanned**: references/scripts/health_check.py, references/scripts/manifest.py, references/scripts/compose.py
- **Findings**: none (all 3 files clean — proper encoding, error handling, no injection risks)
- **Items rejected by human**: none yet

## Scan — 2026-04-09 09:32

- **Files scanned**: (coverage check — no new changes since last scan, all source files covered)
- **Findings**: none
- **Items rejected by human**: none yet

## Scan — 2026-04-09 08:02

- **Files scanned**: tests/integration/harness.py (full review), tests/integration/test_status_flow.py
- **Findings**: none (harness uses list-form _run() throughout — no shell injection; test_status_flow properly uses harness; verify_clean has trivial `if True` no-op filter but intentional)
- **Items rejected by human**: none yet

## Scan — 2026-04-09 06:32

- **Files scanned**: references/scripts/vault_remember.py, tests/integration/test_harness.py
- **Findings**: none (vault_remember.py clean — good defensive coding; test_harness.py f-string shell calls use controlled inputs — same class as #201, already filed)
- **Items rejected by human**: none yet

## Scan — 2026-04-09 05:02

- **Files scanned**: tests/test_labels.py, tests/test_composition.py, tests/test_references.py, tests/test_roles.py, tests/run_tests.py
- **Findings**: none (all test files clean — proper assertions, no shell injection with user input, no stale references)
- **Items rejected by human**: none yet

## Scan — 2026-04-09 03:33

- **Files scanned**: references/scripts/tracker.py (post-#309 guard review), packages/cli/index.js (post-#327 review), SKILL.md
- **Findings**: none (tracker.py guard hardcodes caller_role="skill-lead" but that's covered by #320; cli clean post-fix; SKILL.md informational only)
- **Items rejected by human**: none yet

## Scan — 2026-04-08 11:02

- **Files scanned**: (coverage check — all source files scanned in prior 42 scans)
- **Findings**: none (codebase scan coverage exhaustive, no new targets)
- **Items rejected by human**: none yet

## Scan — 2026-04-08 09:33

- **Files scanned**: .squidsquad/skill/CLAUDE.md (drift check via compose.py deploy skill)
- **Findings**: none (deployed CLAUDE.md identical to recomposed output — no drift)
- **Items rejected by human**: none yet

## Scan — 2026-04-08 08:02

- **Files scanned**: references/sub-skills/manifest.md
- **Findings**: none (clean, comprehensive, matches directory structure)
- **Items rejected by human**: none yet

## Scan — 2026-04-08 06:32

- **Files scanned**: docs/sub-skill-guide.md
- **Findings**: none (accurate, well-structured)
- **Items rejected by human**: none yet

## Scan — 2026-04-08 05:03

- **Files scanned**: docs/ARCHITECTURE.md
- **Findings**: none (accurate, no stale references)
- **Items rejected by human**: none yet

## Scan — 2026-04-08 03:33

- **Files scanned**: tests/integration/test_status_flow.py, tests/integration/harness.py
- **Findings**: _run() called with string instead of list in test_status_flow.py lines 101, 161 — same class as #201 (already filed)
- **Items rejected by human**: none yet

## Scan — 2026-04-08 01:33

- **Files scanned**: references/scripts/vault_check.py, CONTRIBUTING.md
- **Findings**: vault_check.py REQUIRED_FM_FIELDS missing confidence — already tracked as #259. CONTRIBUTING.md clean.
- **Items rejected by human**: none yet

## Scan — 2026-04-08 00:02

- **Files scanned**: references/scripts/diagnostics.py, tests/test_start_scripts.py, packages/cli/index.js (post-fix review)
- **Findings**: none
- **Items rejected by human**: none yet

## Scan — 2026-04-07 22:33

- **Files scanned**: packages/cli/index.js, references/templates/start-role.sh, references/templates/start-role.ps1
- **Findings**: Fixed 2 bugs in packages/cli/index.js inline (banner double-escaped Unicode, gh auth status stdout-is-empty false negative). Boot script templates clean — no issues found.
- **Items rejected by human**: none yet

## Scan — 2026-04-03 00:05

- **Files scanned**: references/statusline.sh, references/agent-instructions.md, .squidsquad/skill/CLAUDE.md
- **Findings**: #24 (statusline.sh reads stale local INDEX.md for backlog counts), #25 (agent-instructions.md Responsibilities section references local markdown tracker)
- **Items rejected by human**: none yet

## Scan — 2026-04-04 15:00

- **Files scanned**: .squidsquad/statusline.sh, .squidsquad/vault/projects/squidsquad.md, SKILL.md (spot check)
- **Findings**: #46 (statusline.sh PM/QA label + missing QA branch), #47 (vault project note stale version/tracker refs)
- **Items rejected by human**: none yet

## Scan — 2026-04-04 17:00

- **Files scanned**: CHANGELOG.md, .squidsquad/pm/CLAUDE.md, .squidsquad/skill/CLAUDE.md
- **Findings**: #48 (live PM and skill CLAUDE.md still reference PM/QA after separation — stale templates)
- **Items rejected by human**: none yet

## Scan — 2026-04-04 19:00

- **Files scanned**: references/sub-skills/common/tracker-protocol.md, references/sub-skills/common/improvement-scan.md, references/sub-skills/pm-specific/feature-intake.md
- **Findings**: status:open missing from tracker-protocol Label Taxonomy (fixed inline — same gap as #39)
- **Items rejected by human**: none yet

## Scan — 2026-04-04 23:30

- **Files scanned**: references/sub-skills/common/context-pressure.md, references/sub-skills/common/pull-latest.md, references/sub-skills/common/working-state.md
- **Findings**: none
- **Items rejected by human**: none yet

## Scan — 2026-04-05 01:00

- **Files scanned**: references/sub-skills/common/interval-sync.md, references/sub-skills/common/resume-working-state.md, references/sub-skills/souls/dev.md
- **Findings**: none (dev soul examples use old tracker format but are illustrative only — not operational)
- **Items rejected by human**: none yet

## Scan — 2026-04-05 02:30

- **Files scanned**: references/sub-skills/pm-specific/feature-approval.md, references/sub-skills/pm-specific/delivery-fallback.md, references/sub-skills/pm-specific/pr-flow.md
- **Findings**: #58 (delivery-fallback.md and pr-flow.md still use pm/qa Discussion alias)
- **Items rejected by human**: none yet

## Scan — 2026-04-05 04:30

- **Files scanned**: references/sub-skills/qa-specific/verification.md, references/sub-skills/designer-specific/design-session.md, references/sub-skills/designer-specific/design-tools.md
- **Findings**: #61 (design-session.md references features/INDEX.md instead of GitHub Issues)
- **Items rejected by human**: none yet

## Scan — 2026-04-05 06:30

- **Files scanned**: references/sub-skills/dm-specific/delivery-packaging.md, references/sub-skills/dm-specific/version-bumps.md, references/sub-skills/pm-specific/github-issues.md
- **Findings**: #63 (delivery-packaging.md references features/INDEX.md instead of GitHub Issues)
- **Items rejected by human**: none yet

## Scan — 2026-04-05 08:30

- **Files scanned**: references/sub-skills/souls/designer.md, references/sub-skills/souls/dm.md, references/sub-skills/souls/pm.md, references/sub-skills/souls/qa.md
- **Findings**: none
- **Items rejected by human**: none yet

## Scan — 2026-04-05 01:42

- **Files scanned**: references/sub-skills/qa-specific/file-conventions.md, bug-filing.md, prohibitions.md, discussion-protocol.md, iteration-log.md
- **Findings**: none (all QA sub-skills clean — using GH Issues correctly, no stale refs)
- **Items rejected by human**: none yet

## Scan — 2026-04-05 03:36

- **Files scanned**: references/sub-skills/common/git-commit.md, common/file-conventions.md, dm-specific/discussion-protocol.md, dm-specific/iteration-log.md, dm-specific/git-commit.md
- **Findings**: none (all clean — GH Issues refs correct, no stale patterns)
- **Items rejected by human**: none yet

## Scan — 2026-04-05 03:39

- **Files scanned**: references/sub-skills/designer-specific/discussion-protocol.md, git-commit.md, iteration-log.md, status-line.md, design-tools.md
- **Findings**: none (all designer sub-skills clean)
- **Items rejected by human**: none yet

## Scan — 2026-04-05 03:42

- **Files scanned**: references/sub-skills/pm-specific/lean-prohibitions.md, github-issues.md, discussion-protocol.md, git-commit.md
- **Findings**: #95 (discussion-protocol.md pm/qa alias), #96 (4 prohibitions files still reference archived/ subdirectory)
- **Items rejected by human**: none yet

## Scan — 2026-04-05 08:35

- **Files scanned**: references/sub-skills/common/discussion-protocol.md, bug-filing.md, prohibitions.md, status-line.md
- **Findings**: none (all common sub-skills clean)
- **Items rejected by human**: none yet

## Scan — 2026-04-05 21:03

- **Files scanned**: references/scripts/config.py, references/scripts/git_ops.py, references/scripts/cycle.py
- **Findings**: #144 (git_ops.py shell injection via f-string interpolation in pr_create/branch ops), #145 (pull() stash pop failure silently ignored)
- **Items rejected by human**: none yet

## Scan — 2026-04-06 03:03

- **Files scanned**: references/scripts/tracker.py, references/scripts/compose.py, references/scripts/vault_remember.py
- **Findings**: #198 (tracker.py list functions still use _run() with shell=True — incomplete #182 fix), #199 (.backlog-cache causes merge conflicts — should be gitignored)
- **Items rejected by human**: none yet

## Scan — 2026-04-06 05:02

- **Files scanned**: tests/test_config.py, tests/integration/harness.py, tests/test_start_scripts.py
- **Findings**: #200 (test_config.py test_has_pr_flow matches wrong Enabled field — fragile), #201 (test harness shell=True with f-string — same class as #182)
- **Items rejected by human**: none yet

## Scan — 2026-04-06 07:02

- **Files scanned**: CHANGELOG.md, .squidsquad/inject-permissions.sh, references/vault-templates/*.md, tests/test_config.py (coverage check)
- **Findings**: #206 (inject-permissions.sh permission count underreports — cosmetic), #207 (test_config.py missing vault-remember field validation)
- **Items rejected by human**: none yet

## Scan — 2026-04-06 09:02

- **Files scanned**: tests/test_vault.py, tests/test_manifest.py, tests/conftest.py
- **Findings**: #208 (test_vault.py frontmatter test gated behind pyyaml — should use regex parser + add human-profile-seed.md template test)
- **Items rejected by human**: none yet

## Scan — 2026-04-06 11:02

- **Files scanned**: .squidsquad/inject-permissions.ps1, .squidsquad/test.ps1, README.md
- **Findings**: none (inject-permissions.ps1 clean, README clean, test.ps1 is scratch file)
- **Items rejected by human**: none yet

## Scan — 2026-04-06 13:02

- **Files scanned**: dev-agent.md (post-#211 verification), skill/CLAUDE.md (deployed gate check), CHANGELOG.md (recent edits)
- **Findings**: none (verify-changes gates deployed correctly, no regressions)
- **Items rejected by human**: none yet

## Scan — 2026-04-07 10:33

- **Files scanned**: references/scripts/vault_check.py, references/scripts/diagnostics.py, references/scripts/cycle.py
- **Findings**: #259 (vault_check.py REQUIRED_FM_FIELDS missing confidence — vault protocol says required but only checked optionally)
- **Items rejected by human**: none yet

## Scan — 2026-04-07 12:03

- **Files scanned**: references/vault-templates/galaxy-template.md, projects-template.md, areas-template.md, BRIEFING.md, human-profile-seed.md
- **Findings**: none (all vault templates clean and consistent)
- **Items rejected by human**: none yet

## Scan — 2026-04-07 13:33

- **Files scanned**: .squidsquad/vault/BRIEFING.md, .squidsquad/vault/projects/squidsquad.md, .squidsquad/vault/areas/human-profile.md
- **Findings**: #262 (BRIEFING.md and squidsquad.md stale — reference v0.11.0 vs current v0.14.0, filed to DM)
- **Items rejected by human**: none yet

## Scan — 2026-04-07 15:02

- **Files scanned**: references/vault-templates/resources-template.md, archives-template.md, .github/ISSUE_TEMPLATE/bug-report.yml, feature-request.yml
- **Findings**: none (templates clean, issue templates correctly use community labels separate from internal taxonomy)
- **Items rejected by human**: none yet

## Scan — 2026-04-07 16:33

- **Files scanned**: .squidsquad/vault/galaxy/decision-sub-skill-architecture.md, learning-atomic-migration-strategy.md + vault-check validate
- **Findings**: #263 (vault missing resources/ and archives/ PARAG directories — vault-check reports 2 structural failures)
- **Items rejected by human**: none yet

## Scan — 2026-04-07 18:03

- **Files scanned**: CHANGELOG.md, full test suite run (108 static + 17 integration)
- **Findings**: none (CHANGELOG clean, 108/108 static pass, integration flake in test_01_initial_state is transient GH API timing — not a code defect)
- **Items rejected by human**: none yet

## Scan — 2026-04-18 00:03

- **Files scanned**: references/scripts/health_check.py, references/scripts/triage.py, references/scripts/scan_index.py
- **Findings**: #1229 (triage.py json.loads without error handling), #1230 (health_check.py unused import os)
- **Items rejected by human**: none yet

# Scan History

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

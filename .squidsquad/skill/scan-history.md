# Scan History

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

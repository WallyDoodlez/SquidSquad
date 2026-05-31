## Scan — 2026-05-16 22:38

- **Files scanned**: references/sub-skills/roles/pm/pipeline-sentinel.md, references/sub-skills/roles/pm/health-check.md, references/sub-skills/roles/pm/soul-shepherd.md, .squidsquad/vault/areas/human-profile.md
- **Findings**: pipeline-sentinel.md section 4b uses invalid git flag `--limit 5` (should be `-n 5`); section 3 PR Status Sync logically unreachable (queries open PRs then checks "if merged") but mitigated by event bus
- **Auto-fixed**: Corrected `--limit 5` to `-n 5` in pipeline-sentinel.md section 4b
- **Items rejected by human**: (none)

## Scan — 2026-05-16 21:03

- **Files scanned**: references/sub-skills/roles/qa/discussion-protocol.md, references/sub-skills/roles/qa/file-conventions.md, references/sub-skills/roles/qa/iteration-log.md, references/sub-skills/roles/dm/discussion-protocol.md
- **Findings**: none — all clean, discussion protocol consistent across roles
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 20:33

- **Files scanned**: .squidsquad/vault/galaxy/decision-cycle-runner-architecture.md, .squidsquad/vault/galaxy/decision-reboot-kills-child.md, .squidsquad/vault/galaxy/decision-self-healing-sentinel.md, references/sub-skills/roles/dm/doc-improvement-loop.md
- **Findings**: decision-reboot-kills-child describes wrapper architecture superseded by harness #4966
- **Auto-fixed**: Downgraded confidence to medium, added changelog noting harness supersession and #4792 tracking full deprecation
- **Items rejected by human**: (none)

## Scan — 2026-05-16 20:24

- **Files scanned**: references/sub-skills/roles/qa/verification.md, references/sub-skills/roles/qa/prohibitions.md, references/sub-skills/roles/dm/task-pickup.md
- **Findings**: verification.md Step 4 item 6 text said "Transition to shipped (auto-closes)" but command does pending-test → pending-ship
- **Auto-fixed**: Corrected text to "Transition to pending-ship" matching the actual command
- **Items rejected by human**: (none)

## Scan — 2026-05-16 19:17

- **Files scanned**: references/sub-skills/roles/dm/version-bumps.md, references/sub-skills/roles/dm/delivery-packaging.md, references/sub-skills/common/vault-remember.md, references/sub-skills/common/vault-optimize.md
- **Findings**: version-bumps.md line 4 had stale markdown tracker format reference (`**Status**: Open` or `**Status**: Investigating`) — replaced with GitHub Issues terminology
- **Auto-fixed**: Updated version-bumps.md bump gate check to reference `type:issue, state:open` instead of old tracker format
- **Items rejected by human**: (none)

## Scan — 2026-05-16 14:31

- **Files scanned**: references/sub-skills/common/boot-remote-agents.md, references/sub-skills/common/context-pressure.md
- **Findings**: none — both clean, exit-42 respawn gap tracked in #7693
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 14:02

- **Files scanned**: references/sub-skills/common/agent-lifecycle.md, references/sub-skills/common/self-restart.md
- **Findings**: none — both correct, self-restart exit-42 issue already tracked in #7693
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 13:59

- **Files scanned**: references/sub-skills/common/event-reactions.md, references/sub-skills/common/cycle-runner.md
- **Findings**: none — both clean and consistent with composed CLAUDE.md
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 11:02

- **Files scanned**: references/sub-skills/roles/pm/discussion-protocol.md, references/sub-skills/roles/pm/issue-filing.md
- **Findings**: none — both concise and correct
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 10:32

- **Files scanned**: references/sub-skills/roles/pm/task-intake.md, references/sub-skills/roles/pm/status-line.md
- **Findings**: none — task-intake properly parameterized, status-line accurate
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 10:02

- **Files scanned**: references/sub-skills/roles/pm/checkin.md, references/sub-skills/roles/pm/github-issues.md
- **Findings**: checkin.md skipped Planned state in approval flow (contradicted task-approval.md)
- **Auto-fixed**: Updated checkin.md to include Planned → human approval → Approved flow
- **Items rejected by human**: (none)

## Scan — 2026-05-16 09:32

- **Files scanned**: references/sub-skills/roles/pm/pipeline-sentinel.md, references/sub-skills/roles/pm/testing-and-verification.md
- **Findings**: none — pipeline-sentinel matches composed behavior, verification correctly delegated to QA
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 09:02

- **Files scanned**: references/sub-skills/roles/pm/health-check.md, references/sub-skills/roles/pm/delivery.md
- **Findings**: none — both clean, consistent with harness lifecycle and PM boundaries
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 08:32

- **Files scanned**: references/sub-skills/roles/pm/soul-shepherd.md, references/sub-skills/roles/pm/vault-synthesis.md
- **Findings**: none — both consistent with PM CLAUDE.md
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 08:02

- **Files scanned**: references/sub-skills/roles/pm/task-approval.md, references/sub-skills/roles/pm/own-domain-autofix.md
- **Findings**: none — both consistent with PM CLAUDE.md and tracker protocol
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 07:32

- **Files scanned**: references/sub-skills/common/vault-optimize.md, references/sub-skills/common/improvement-scan-slim.md
- **Findings**: none — vault-optimize consistent with config, slim scan version matches full
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 07:02

- **Files scanned**: references/sub-skills/common/improvement-scan.md
- **Findings**: Step 5 vs Rules contradiction — "file directly" vs "report to PM via Discussion"
- **Auto-fixed**: Updated Rules to match actual behavior (agents file directly with improvement-scan label)
- **Items rejected by human**: (none)

## Scan — 2026-05-16 06:32

- **Files scanned**: references/sub-skills/common/vault-protocol.md, references/sub-skills/common/chat-etiquette.md
- **Findings**: none — vault-protocol comprehensive and consistent, chat-etiquette references real adapter
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 06:02

- **Files scanned**: references/sub-skills/common/vault-remember.md, references/sub-skills/common/boot-remote-agents.md
- **Findings**: none — both clean, consistent with harness lifecycle and vault protocol
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 05:32

- **Files scanned**: references/sub-skills/common/prohibitions.md, references/sub-skills/common/working-state.md
- **Findings**: PM violated "never gh issue close directly" on #8477 in cycle 1468 — fixed stale labels
- **Auto-fixed**: Added status:shipped label to #8477, removed status:open
- **Items rejected by human**: (none)

## Scan — 2026-05-16 05:02

- **Files scanned**: references/sub-skills/common/discussion-protocol.md, references/sub-skills/common/task-pickup.md
- **Findings**: none — both clean, consistent with tracker protocol and git_ops workflow
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-16 04:32

- **Files scanned**: references/sub-skills/common/context-pressure.md, references/sub-skills/common/cycle-runner.md
- **Findings**: context-pressure.md had stale "set a flag" wording (cycle_post handles this mechanically now)
- **Auto-fixed**: Updated context-pressure.md step 4 to reference cycle_post.py exit-42 mechanism
- **Items rejected by human**: (none)

## Scan — 2026-05-16 04:02

- **Files scanned**: references/sub-skills/common/agent-lifecycle.md, references/sub-skills/common/self-restart.md
- **Findings**: none — both clean, consistent with architecture, no contradictions
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-15 08:33

- **Files scanned**: references/sub-skills/common/consensus-protocol.md, references/sub-skills/common/interval-sync.md
- **Findings**: none
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-15 05:04

- **Files scanned**: references/sub-skills/common/event-reactions.md, references/sub-skills/common/mention-protocol.md
- **Findings**: none
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-15 04:03

- **Files scanned**: references/sub-skills/common/capability-check.md, references/sub-skills/common/file-conventions.md
- **Findings**: none
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-15 02:33

- **Files scanned**: references/sub-skills/common/resume-working-state.md, references/sub-skills/common/status-line.md
- **Findings**: none
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-15 02:04

- **Files scanned**: references/sub-skills/common/iteration-log.md, references/sub-skills/common/pull-latest.md
- **Findings**: none — pull-latest.md has minor legacy "tracker file" term but harmless
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-15 01:34

- **Files scanned**: references/sub-skills/common/issue-filing.md, references/sub-skills/common/git-commit.md
- **Findings**: none — both consistent with vault decisions and tracker protocol
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-15 01:04

- **Files scanned**: references/sub-skills/common/task-pickup.md, references/sub-skills/common/working-state.md
- **Findings**: working-state.md clear state example dropped Last Processed Event ID — would cause event re-processing after task completion
- **Auto-fixed**: updated clear instruction to preserve event ID
- **Items rejected by human**: (none)

## Scan — 2026-05-14 23:34

- **Files scanned**: references/sub-skills/common/cycle-runner.md, references/sub-skills/common/prohibitions.md
- **Findings**: none — both current, consistent with harness architecture and tracker protocol
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-14 19:34

- **Files scanned**: references/sub-skills/roles/pm/pipeline-sentinel.md, references/sub-skills/roles/pm/soul-shepherd.md
- **Findings**: none — both well-structured, noise-capped sentinel thresholds are intentional
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-14 19:03

- **Files scanned**: references/sub-skills/common/discussion-protocol.md, references/sub-skills/common/vault-remember.md
- **Findings**: none
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-14 18:34

- **Files scanned**: references/sub-skills/common/agent-lifecycle.md, references/sub-skills/common/context-pressure.md
- **Findings**: none — both current and consistent with harness architecture
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-14 17:05

- **Files scanned**: references/sub-skills/common/self-restart.md, references/wizard/WIZARD.md
- **Findings**: none
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-12 20:32

- **Files scanned**: .squidsquad/project/shared-instructions.md, .squidsquad/project/dev-instructions.md
- **Findings**: shared-instructions.md referenced deprecated sentinel files (.stop-after-cycle, .stop, .pid) and old wrapper heartbeat pattern — replaced by harness intent API (#4966)
- **Auto-fixed**: rewrote Agent Infrastructure section to reference harness PID monitoring + intent state machine
- **Items rejected by human**: (none)

## Scan — 2026-05-12 14:01

- **Files scanned**: .squidsquad/config.md (full config consistency check)
- **Findings**: none — config consistent, ship counter correct, all sections current
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-12 13:32

- **Files scanned**: .squidsquad/vault/areas/human-profile.md
- **Findings**: missing deterministic-cycle preference from this session ("any kind of cyclic work needs to be programmed deterministically")
- **Auto-fixed**: added preference to Technical Preferences section, appended changelog
- **Items rejected by human**: (none)

## Scan — 2026-05-12 13:02

- **Files scanned**: .squidsquad/vault/BRIEFING.md (Recent Decisions, Constraints & Blockers sections)
- **Findings**: Recent Decisions missing #7491 and #6581 decisions. Constraints section stale — old shipped items listed as active constraints.
- **Auto-fixed**: added 3 recent decisions (#7491, #6581, #7630 philosophy), added deterministic-cycle human preference, rewrote Constraints section
- **Items rejected by human**: (none)

## Scan — 2026-05-12 12:32

- **Files scanned**: .squidsquad/vault/BRIEFING.md Active Priorities section
- **Findings**: 3 superseded items (#6056, #5775, #5613 → all absorbed by #7630), stale #5622 dependency on #3963, removed old Pending Tasks section
- **Auto-fixed**: rewrote Active Priorities — added #7630, #6574, removed superseded items, updated #3963 constraint
- **Items rejected by human**: (none)

## Scan — 2026-05-12 12:02

- **Files scanned**: references/roles/*/includes.yml (all 4 roles) cross-referenced with manifest.md composition order
- **Findings**: manifest.md composition order out of sync with includes.yml — missing event-reactions, task-pickup, dm/doc-improvement-loop, dm/task-pickup. DM still lists removed improvement-scan-slim. Added to #7631.
- **Auto-fixed**: none (documentation, added to existing skill issue)
- **Items rejected by human**: (none)

## Scan — 2026-05-12 11:32

- **Files scanned**: references/sub-skills/manifest.md (full inventory, composition order, placeholder table)
- **Findings**: manifest.md line 11 references agent-instructions.md as compose output (stale) — added to #7631
- **Auto-fixed**: none (source template, added to existing skill issue)
- **Items rejected by human**: (none)

## Scan — 2026-05-12 11:02

- **Files scanned**: .squidsquad/vault/galaxy/ (all 22 notes — bulk staleness check for pending/TODO markers and closed-issue references)
- **Findings**: none — vault galaxy healthy, no stale status markers or dead references beyond previously fixed cycle-runner note
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-12 10:33

- **Files scanned**: .squidsquad/vault/galaxy/decision-cycle-runner-architecture.md, vault galaxy decisions index
- **Findings**: decision-cycle-runner-architecture.md status stale — said "Pending, not yet implemented" but #2057 shipped and cycle runner is live
- **Auto-fixed**: updated status to Shipped, added #7630 successor reference, appended changelog
- **Items rejected by human**: (none)

## Scan — 2026-05-12 10:03

- **Files scanned**: references/sub-skills/roles/dev/implement-tasks.md, references/roles/qa/instructions.md, .squidsquad/project/dev-instructions.md
- **Findings**: implement-tasks.md step 8 references old monolith name agent-instructions.md — filed #7631
- **Auto-fixed**: none (source template, filed to skill)
- **Items rejected by human**: (none)

## Scan — 2026-05-12 09:02

- **Files scanned**: references/sub-skills/roles/dm/delivery-packaging.md, references/roles/dm/instructions.md, references/roles/instructions.md (L1 base)
- **Findings**: none — DM delivery flow clean, L1 base consistent, harness port matches config
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-12 08:34

- **Files scanned**: references/sub-skills/common/cycle-runner.md, references/sub-skills/common/event-reactions.md, references/sub-skills/common/task-pickup.md, .squidsquad/vault/BRIEFING.md
- **Findings**: BRIEFING.md version stale (0.37.0→0.38.0), Recently Shipped missing v0.38.0 items. event-reactions.md documents 4 unimplemented event types (tracked by #5613).
- **Auto-fixed**: BRIEFING.md version updated to 0.38.0, Recently Shipped trimmed and updated with v0.38.0 items
- **Items rejected by human**: (none)

## Scan — 2026-05-10 18:08

- **Files scanned**: references/sub-skills/roles/pm/testing-and-verification.md, references/sub-skills/roles/qa/verification.md, references/sub-skills/roles/pm/pipeline-sentinel.md
- **Findings**: none
- **Auto-fixed**: none
- **Items rejected by human**: none

## Scan — 2026-05-09 00:10

- **Files scanned**: references/roles/pm/includes.yml, references/roles/dev/instructions.md, references/roles/pm/SOUL.md
- **Findings**:
  - #6275 — Stale 'date command' timestamp reference in all 5 role templates, contradicts tracker-protocol (cycle.py). Filed as low-severity issue for skill.
- **Auto-fixed**: BRIEFING.md version 0.34.0 → 0.35.0, added #6085/#6086 to shipped, added #6126/#6261/#6274 to active priorities
- **Items rejected by human**: (none)

## Scan — 2026-04-26 09:01

- **Files scanned**: BRIEFING.md (staleness), cycle_pre.py (pull mechanism), sub-skills/cycle-runner.md, tracker comments on #3107/#3124 (stale checkout pattern)
- **Findings**:
  - BRIEFING.md stale (ship counter, priorities) — fixed inline (own-domain)
  - #3296 — Stale checkout detection gap: DM and QA tested stale code on #3107 and #3124. Filed as task for human discussion.
- **Items rejected by human**: (none yet)

## Scan — 2026-04-26 00:31

- **Files scanned**: GitHub Issues tracker (50 pending items — backlog analysis for staleness, consolidation, title integrity)
- **Findings**:
  - #2057 — "Cycle runner script" appears already implemented (cycle_pre.py/cycle_post.py exist and in use). Commented asking human to confirm closure.
  - #14 — Corrupted title from Windows path expansion. Fixed inline.
- **Items rejected by human**: (none yet)

## Scan — 2026-04-13 17:32

- **Files scanned**: references/scripts/tracker.py, references/scripts/config.py, references/scripts/health_check.py
- **Findings**:
  - #893 — tracker.py _check_unread_feedback role name matching not canonicalized (issue, low)
  - #894 — health_check.py returns exit 0 when .local-config missing, masks unchecked agents (issue, low)
- **Items rejected by human**: (none yet)

## Scan — 2026-04-12 18:33

- **Files scanned**: .squidsquad/pm/working-state.md (staleness check against live tracker)
- **Findings**: working-state referenced 3 closed items (#327, #280, #250) as pending. Cleaned up. No bug filed — PM housekeeping.
- **Items rejected by human**: (none)

## Scan — 2026-04-12 15:33

- **Files scanned**: GitHub Issues tracker (in-progress items, agent activity patterns)
- **Findings**: none — #442 and #4 both in-progress with skill agent. Skill showing idle/scanning between rework cycles. Normal backlog behavior.
- **Items rejected by human**: (none)

## Scan — 2026-04-12 07:33

- **Files scanned**: GitHub Issues tracker (pipeline distribution analysis — 28 pending, 1 planned, 0 in-progress, 0 open bugs)
- **Findings**: none — pipeline is clean, bottleneck is normal human approval queue
- **Items rejected by human**: (none)

## Scan — 2026-04-12 04:03

- **Files scanned**: GitHub Issues tracker (all 28 open issues — label integrity + title quality)
- **Findings**:
  - #402 — #148 missing required labels (type:bug, role:skill, severity) — invisible to tracker queries
  - #403 — #377 double "BUG: BUG:" prefix in title — create-bug may need prefix dedup
- **Items rejected by human**: (none yet)

## Scan — 2026-04-07 01:00

- **Files scanned**: GitHub Issues tracker (planned/on-hold review)
- **Findings**: none — pipeline is clean. #250 (auto-restart) planned awaiting human approval. No new process issues.
- **Items rejected by human**: (none)

## Scan — 2026-04-06 23:00

- **Files scanned**: GitHub Issues tracker (process analysis), open bugs and features
- **Findings**:
  - Closed #196 (stale — LICENSE exists since #232)
  - 4 DM pending bugs remain (#193, #194, #197, #210) — low priority improvement scan items awaiting human approval
- **Items rejected by human**: (none)

## Scan — 2026-04-06 11:30

- **Files scanned**: GitHub Issues tracker (process analysis), iteration logs iter-220 through iter-232
- **Findings**:
  - #211 — Skill-lead phantom fix pattern (15 occurrences, HIGH)
- **Items rejected by human**: (none yet)

## Scan — 2026-05-07 09:02

- **Files scanned**: SKILL.md, README.md (stale references to wrappers, old versions, pre-harness patterns)
- **Findings**: none — both files correctly reference harness lifecycle, no stale wrapper refs
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-07 11:02

- **Files scanned**: QA sub-skills (issue-filing.md, discussion-protocol.md, prohibitions.md, verification.md)
- **Findings**: Confirmed #6007 covers the gaps — issue-filing too thin, no structured finding format, no routing process. No additional findings beyond #6007
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-07 14:02

- **Files scanned**: Dev sub-skills (triage-issues.md, implement-tasks.md), common improvement-scan.md
- **Findings**: none — triage deterministic queue correct, implement-tasks flow clean, improvement-scan well-structured
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-08 05:32

- **Files scanned**: references/scripts/git_ops.py (event emissions, role inference, PR functions)
- **Findings**: pr_create/pr_merge still emit with role:unknown — already tracked (#5782 shipped but incomplete). No new findings
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-05-19 14:18

- **Files scanned**: references/sub-skills/common/boot-remote-agents.md (cross-referenced against memory feedback_manual_agents, .squidsquad/pm/CLAUDE.md:617,666,1786, and live user request to boot dm+skill cycle 1497)
- **Findings**: #9272 — boot-remote-agents.md line 16 "PM does not boot agents directly" contradicts feedback_manual_agents and live user practice
- **Auto-fixed**: none (Tier 2 — fragment lives in skill domain)
- **Items rejected by human**: none

## Scan — 2026-05-19 14:54

- **Files scanned**: .squidsquad/config.md (cross-referenced compose.py:1202 MANDATORY_ROLES, composed CLAUDE.md line 181 across pm/qa/dm/skill)
- **Findings**: #9318 — Dev Agents value stale since #6055 (qa became mandatory; should be just "skill")
- **Auto-fixed**: none (Tier 2 — touches config + compose + recompose across 4 roles)
- **Items rejected by human**: none

## Scan — 2026-05-19 20:15

- **Files scanned**: references/scripts/git_ops.py (cross-referenced cycle-1500 unknown ghost cleanup + scan-history 2026-05-08 entry + #5782)
- **Findings**: git_ops.py:90 still has `role = "unknown"` fallback — upstream source of the harness state corruption. #5782 was supposed to fix it but shipped incomplete. Added as evidence to #9242 fix-proposal item #3.
- **Auto-fixed**: none (skill domain; touches event emission semantics)
- **Items rejected by human**: none

## Scan — 2026-05-25 11:13

- **Files scanned**: repo-wide grep for dated model-version strings (claude-{sonnet,opus,haiku}-{3,4}-*) across references/, docs/, .squidsquad/
- **Findings**: none — zero violations of `feedback_model_tier_not_version` in spec/process files. Two hits in historical planning artifacts (`.squidsquad/qa/planning/FEAT-QA-5040-QA-RESULTS.md` line 3, `.squidsquad/pm/planning/FEAT-PM-4083-TEST-PLAN.md` line 116) are frozen test-result/test-case records — version-pinned by intent, acceptable per the memory rule's historical-record exception
- **Auto-fixed**: none
- **Items rejected by human**: none

## Scan — 2026-05-25 13:13

- **Files scanned**: full vault wikilink integrity check via `vault_check.py check-wikilinks`
- **Findings**: none — all wikilinks resolve, including the two notes added this session ([[decision-vault-subagent-model-sonnet]] referencing [[VAULT-ARCH]], [[shipped-pre-2026-05-19]] linked from BRIEFING)
- **Auto-fixed**: none
- **Items rejected by human**: none

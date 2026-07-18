## Scan — 2026-07-17 (post-recovery)

- **Files scanned**: `.squidsquad/config.md` (consistency lens, cross-checked vs live /status + boot facts)
- **Findings**: none — config is fully consistent: version 0.45.0, roster pm/dm/qa/skill, aliases (incl. correct `dm: dm/skill`), verbose-mode `no`, cool-down 30m/burst 3, ctx-threshold 70, iteration 30m, port 7373 all match facts.
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-07-17 ~02:55

- **Files scanned**: `.squidsquad/vault/BRIEFING.md` (staleness lens)
- **Findings**: none fileable (write access still down). BRIEFING's Team State + Constraints asserted now-WRONG facts (harness "44-behind/stale/DORMANT #13456/#13472/#13494") — resolved this boot (harness on HEAD a7c2b6ae). 
- **Auto-fixed**: BRIEFING.md — prepended 2026-07-17 increment (fleet write-outage #13570 + harness-now-current + pipeline/HITL state); corrected the stale "Current version / harness STALE" Team State bullet to reflect the current-code + bare-mode reality. Own-domain (pm-owned vault). Local-only until write access restored (won't push under Naahtec read-only auth).
- **Items rejected by human**: (none)

## Scan — 2026-07-17 02:42

- **Files scanned**: `references/scripts/tracker.py` (check_gh), `references/sub-skills/common/health-check.md`, `references/sub-skills/roles/pm/pipeline-sentinel.md` — lens: does the framework detect a forge WRITE-outage? (prompted by this session's live Naahtec read-only auth incident, #13570)
- **Findings**: Tier-2 gap — boot gate + health checks verify forge READ only, never WRITE. `check_gh()` (tracker.py:640) runs `gh issue list` = read; health-check.md has zero push/label/write coverage (grep-confirmed); pipeline-sentinel.md has no forge-write-outage halt class. Result: a read-only auth downgrade leaves all liveness green while the pipeline is write-frozen, discovered only when a write fails mid-cycle. **NOT filed as a new task** (write access down → would create an unlabeled orphan); instead logged as a hardening follow-up COMMENT on #13570, to split into a proper role:skill task once auth is restored. Suggested fix: boot gate verifies `.permissions.push==true`, fail loud with remediation; health-check step for same; sentinel gains a 'forge write-outage' class.
- **Auto-fixed**: none (finding targets skill lane — code + sub-skills)
- **Items rejected by human**: (none)

## Scan — 2026-07-11 13:14

- **Files scanned**: harness restart/boot path behavior (POST /restart) vs primary-clone git state (observed live this session, #13473)
- **Findings**: filed **#13531** (role:skill, low, improvement-scan) — POST /restart can silently relaunch the harness on STALE code when the primary/harness-root clone is behind+dirty; today's harness.py fixes (#13456/#13472/#13494) + a config.md change did not activate, with no staleness signal. Distinct from #13456/#13472/#13494 (those harden AGENT-clone deploy-pulls). Behavior-only report; remedy design left to assignee.
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-06-28 17:21

- **Files scanned**: .squidsquad/vault/areas/human-profile.md
- **Findings**: none filed.
- **Auto-fixed**: human-profile.md L33 PID-preference reconciled — added nuance that the "just use PID" direct-checks preference's PID-as-liveness-authority application was operator-approved for supersession (#12492 progress-liveness; PID→teardown-only) while the general direct-verification principle stands; changelog + `updated` bumped to 2026-06-28. Own-domain (pm-owned vault). Sibling of #13317/#13319 (#12492 doc-reconciliation).
- **Items rejected by human**: (none)
- _(Burst 3/3 → driver cancelled, cron b34273a4 deleted; quiesces until new forge work re-idles.)_

## Scan — 2026-06-28 16:21

- **Files scanned**: .squidsquad/config.md, .squidsquad/vault/BRIEFING.md
- **Findings**: none — config.md consistent (roster pm/dm/qa/skill, `dm: dm/skill` correct, cool-down 30m/burst 3/verbose ON, Shipped-Since-Bump 50 DM-owned/held).
- **Auto-fixed**: BRIEFING.md refreshed — prepended current 2026-06-28 increment (post-restart green, #13303 shipped, #13318 in flight, scan set #13315/#13317/#13319, #13263 HITL); top entry was 06-27 pre-dating the whole session (own-domain housekeeping).
- **Items rejected by human**: (none)

## Scan — 2026-06-28 15:21

- **Files scanned**: docs/HARNESS-ARCH.md (§5.5/§13.7/§15 + failure-mode table L521), docs/AGENT-RUNTIME.md
- **Findings**: #13319 (Tier 2, low, role:pm) — HARNESS-ARCH still frames progress-liveness as a §15 "proposal" and zombies as "NOT detected today / proposed fix" (L521, §13.7), and PID as "primary" (§5.5) — all stale post-#12492 (progress-liveness SHIPPED, authoritative; PID teardown-only). Arch-doc (TRD) slice; sibling of #13289 (dm/README) + #13317 (skill/sub-skills). DS-audit flagged. Filed to pm.
- **Auto-fixed**: none (multi-section TRD reconciliation + DS-audit warranted → tracked task, not rushed mid-scan)
- **Items rejected by human**: (none)

## Scan — 2026-06-28 06:52

- **Files scanned**: references/sub-skills/roles/pm/pipeline-sentinel.md
- **Findings**: none — clean and current (recent refs #12442/#12460/#12475, event-mode/comment-handling correct; verified `cycle.py status-bar <role> <phase> <desc>` form at L13 still valid, not stale).
- **Auto-fixed**: none
- **Items rejected by human**: (none)
- _(Burst 3/3 reached → driver cancelled, cron e73a3b97 deleted; quiesces until new forge work re-idles.)_

## Scan — 2026-06-28 05:53

- **Files scanned**: .squidsquad/vault/galaxy/decision-pid-primary-liveness.md, references/sub-skills/roles/pm/health-check.md, references/sub-skills/common/agent-lifecycle.md
- **Findings**: #13317 (defect, low, role:skill) — health-check.md L18 + agent-lifecycle.md L16 both call `.claude-pid` the "sole liveness signal", contradicting the now-live #12492 progress-liveness cutover (PID demoted to teardown-only). Decision file itself already correctly archived; the compose-consumed sub-skills were not updated. Filed to skill (sub-skills are skill's lane).
- **Auto-fixed**: none (sub-skills are compose-consumed code, not PM lane)
- **Items rejected by human**: (none)

## Scan — 2026-06-28 04:55

- **Files scanned**: docs/COMPOSE-ARCHITECTURE.md (§8.2 L4-write trigger), docs/AGENT-RUNTIME.md (§8.2/§8.5 restart-required), docs/prd/compose-freshness.md (E3)
- **Findings**: #13315 (Tier 2, low) — #13303 shipped a content-change gate on the L4 file-watcher's restart-required emission (no-op recompose now suppressed) code-only, no paired arch-doc edit; COMPOSE-ARCH §8.2 / AGENT-RUNTIME §8.5 don't document the gate. Filed to pm.
- **Auto-fixed**: none
- **Items rejected by human**: (none)

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

## Scan — 2026-06-03 02:10

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory staleness check vs config.md + tracker state)
- **Findings**: BRIEFING.md heavily stale — PRs #10378/#10379 listed in-flight but merged 2026-05-30; PRD-A/B/C/D-catalog/E1-E5 ships not reflected; E6 #10685 in-flight + 4 new umbrella PRDs #10836-#10839 + PRD-D #10781 missing from active priorities; #9242 harness-unreachable constraint stale (harness now reachable)
- **Auto-fixed**: BRIEFING.md fully rewritten — current Active Priorities (E6 + PRD-D + 4 umbrellas + E7 + wiki-link + catalog cleanup), Recently Shipped (PRD-A/B/C/D-catalog/E1-E5 + TRD-polish settlement + TRD Claude final-pass), Recent Decisions (PRD-D 2-tier + #10836 Direction A + audit refresh strategy + skill OOM finding + post-E6 queue), Constraints (skill OOM, verifier boot intermittency)
- **Items rejected by human**: (none)

## Scan — 2026-06-03 03:08

- **Files scanned**: .squidsquad/project/{pm.md,worker.md,worker-instructions.md} (L4 long-living context + legacy stubs); cross-reference against feedback_compose_dry + feedback_pm_docs_only memory rules
- **Findings**: (1) PM L4 (pm.md) clean — docs-only boundary clearly stated, pure-orphan inline-delete exception preserved; aligns with last 2 cycles' actions (#10750 reroute, #9969 parking). (2) Worker L4 duplication: commit bd64e86f added "Front-loaded planning for batched issue work" section to BOTH worker.md AND worker-instructions.md — violates feedback_compose_dry (one authoring location). Self-resolves via #10836 Direction A (deletes worker-instructions.md as legacy stub). Added content-preservation gate to CONTEXT-10836.md.
- **Auto-fixed**: CONTEXT-10836.md content-preservation gate documented for skill to honor at implementation time.
- **Items rejected by human**: (none)

## Scan — 2026-06-03 03:38

- **Files scanned**: .squidsquad/project/{verifier.md,verifier-instructions.md,verifier-responsibility.md,verifier-soul-directives.md,pm-*.md,dm-*.md} (legacy L4 stub content-vs-unified-file inventory; follow-up to cycle 2084 worker.md finding)
- **Findings**: (1) verifier-soul-directives.md contains 'Deterministic testing law' rule with #1291 incident cite — NOT in verifier.md. MIGRATION REQUIRED before stub deletion. (2) Bold-heading inventory across pm-*.md and dm-*.md flagged ~60 themes not appearing as bold headings in unified files — needs per-stub content comparison at implementation time (verifier finding proves bold-diff != content-diff).
- **Auto-fixed**: CONTEXT-10836.md content-preservation gate expanded with specific verifier finding + hard rule (no stub deletion without per-stub audit log). Tracker comment on #10836 with same.
- **Items rejected by human**: (none)

## Scan — 2026-06-03 04:38

- **Files scanned**: references/ grep — verify PHASE2-LOCKED-10781 premise (3 standing rules have zero → run sub-skill: invocations; 2 kept entries have positive invocations)
- **Findings**: PHASE2-LOCKED-10781 premise CONFIRMED — self-restart/context-pressure/cycle-runner have 0 references/ invocations (correctly removed from catalog); boot-bootstrap + agent-lifecycle have 2 each in references/agent-instructions.md + references/roles/instructions.md (correctly kept). Post-E6 (after agent-instructions.md deletes), count drops to 1 each but still ≥1 threshold — Phase 2 lock stays valid.
- **Auto-fixed**: none (verification scan only)
- **Items rejected by human**: (none)

## Scan — 2026-06-19 11:15

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory staleness check vs forge + /status); cross-ref against this session's verified ship-states
- **Findings**: BRIEFING.md heavily stale — Team State 4 days old ("pm inline / qa LOOP pinned"); #12506/#12853/#12442/#11394/#12408/#12585/#12824/#12820/#12749 all shipped but still listed in-flight or as active constraints; retired #12442 manual-dm-nudge workaround still listed as a live constraint
- **Auto-fixed**: BRIEFING.md refreshed (PM own-domain) — new 2026-06-19 Active-Priorities increment (verified ships + #12895 decision + boot-pull-lag), Team State rewritten from /status (pm/dm/skill EVENT, qa POLLING-alive), Constraints updated (boot-pull-lag chronic + #12442 retired), Recently-Shipped 06-18/19 line added
- **Items rejected by human**: (none)

## Scan — 2026-06-19 14:15 (local ~11:15→ actually 18:15 UTC; 2nd burst scan)

- **Files scanned**: repo-wide grep "Never Block on a Human" across *.md (post-#12853/#12800 SOUL-rename drift check — verify the rename to 'Never Stop While Work Is Pending' was complete in load-bearing source/spec files)
- **Findings**: none — ZERO occurrences in references/ or docs/ (source + specs). All 12 *.md hits are historical records (working-state, iter logs, qa/planning QA-RESULTS/TEST-PLAN) or intentional rename references (BRIEFING, decision-agents-never-stop-while-work-pending). #12853 rename clean in source.
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-06-19 18:42 UTC (3rd burst scan)

- **Files scanned**: vault wikilink integrity (`vault_check.py check-wikilinks`) across .squidsquad/vault/
- **Findings**: intra-vault link integrity CLEAN (0 broken decision-/pattern-/learning-/style- targets). All ~20 WARN are cross-layer references the checker can't resolve — vault→memory (feedback_*/project_*) and vault→docs (AGENT-RUNTIME/VAULT-ARCH) — which are intentional, not breakage. Tooling note: check-wikilinks is low-signal because cross-layer refs dominate the output (a real intra-vault break would be buried). NOT filed (low value, likely known limitation; vault_check.py = skill code domain).
- **Auto-fixed**: pattern-chain-ship-per-item-auth.md — `[[feedback-pm-docs-only]]` → `[[feedback_pm_docs_only]]` (hyphen→underscore, canonical memory-note name)
- **Items rejected by human**: (none)

## Scan — 2026-06-19 21:13 (post-restart idle-driver tick, 1st burst scan)

- **Files scanned**: HARNESS-ARCH.md §7/§11 (deploy-signal/recompose/restart — verify shipped #12906 + #12912-design accuracy); config.md Improvement-Scanning defaults vs idle-cooldown-loop; .squidsquad/vault/BRIEFING.md (mandatory staleness check vs this boot's verified facts)
- **Findings**: HARNESS-ARCH §7.6/§11 coherent — deploy-signal model documented as the #12912 design contract (intentional target-state doc-first, NOT drift); `deploying` intent + ensure-main→pull→recompose→commit→push + deploy-halt exit + multi-clone-consistency window all consistent. Config defaults (30m cool-down, burst 3) match driver output. No actionable doc-drift finding (the planned-vs-pending-human-* surfacing distinction is intentional design, not a gap — NOT filed).
- **Auto-fixed**: BRIEFING.md refreshed (PM own-domain, Tier-1) — new 2026-06-19 ~20:48 post-restart Active-Priorities increment (restart succeeded, #12906 confirmed-live, qa now EVENT, #12896 intaken→planned); Team State rewritten (all 4 EVENT, harness sha 398d1c1a); Constraints updated (boot-pull-lag regression neutralized by #12906-live → restore-dance now backstop); version sha b15e7fc5→398d1c1a.
- **Items rejected by human**: (none)

## Scan — 2026-06-19 22:11 (post-restart idle-driver tick, 2nd burst scan)

- **Files scanned**: references/sub-skills/roles/pm/checkin.md (advertise-duty mechanics) + references/roles/pm/responsibility.md advertise-duty — consistency/completeness check (PM about to rely on it for #12896-planned + #10686-parked surfacing)
- **Findings**: none filed. Considered a candidate gap — the check-in advertise step (checkin.md:17) covers only `role:<human>` + `pending-human-*` items, NOT PM-owned `planned` items awaiting approval (e.g. #12896). Concluded INTENTIONAL/coherent, not a gap: PM tracks its own `planned` items in working-state and surfaces them with judgment at check-in; advertise-duty is specifically the cross-agent pending-human-* return-path (items OTHER agents hand off that PM wouldn't otherwise know). A blanket 'advertise all planned' would nag the operator about deliberately operator-paced items (#10837/#10838/#10839 etc.). PM judgment + working-state tracking covers the #12896 case. NOT filed (designed distinction, filing would be marginal noise).
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-06-20 00:02 (fresh-boot idle-driver tick, 3rd/burst-cap scan)

- **Files scanned**: references/sub-skills/roles/pm/pipeline-sentinel.md (PM core stall-detection sub-skill, exercised live this boot; not scanned recently)
- **Findings**: 1 identified, NOT filed (dedup). pipeline-sentinel.md is framed in pure loop-mode terms — "Step 6f" anchor (event-hydrated cycle puts it at Step 4.1), "runs every cycle", "90 minutes (3 cycles at 30-min interval)" cadence reasoning — while the canonical architecture is event-mode. The 90-min WALL-CLOCK stall threshold is still correct; only the loop-cadence FRAMING is stale. **Already in scope of in-flight #12493** ("L2: pipeline-sentinel — detect HALT, investigate, unblock (event-effective)") which explicitly rewrites THIS file event-effectively → a competent event-mode rewrite sweeps up the cadence framing. Filing would duplicate. Cannot Tier-1 auto-fix: references/sub-skills/ is skill's domain (PM-docs-only boundary) AND skill is actively rewriting this file under #12493 — an edit would conflict.
- **Auto-fixed**: none
- **Items rejected by human**: (none)
- **Burst note**: 3rd scan of this idle period → at_cap, driver cancelled + cron deleted (re-arms on next forge-work re-idle).

## Scan — 2026-06-20 01:17 (idle-driver tick, fresh burst after reidle, 1st scan)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory staleness check vs this boot's forge-verified ship-states + /status)
- **Findings**: BRIEFING stale — latest Active-Priorities increment predated this boot (~20:48); #12526 listed as an OPEN chronic blocker but it SHIPPED 00:58 (PR #12993); "pipeline otherwise idle (0 pending-test/ship)" claim outdated after a full bug-fix ship burst (#12818/#12914/#12823/#12526); newly-shipped items absent from Recently-Shipped.
- **Auto-fixed**: BRIEFING.md refreshed (PM own-domain, Tier-1) — new 2026-06-20 ~01:00 increment (ship burst + #12912 qa-bounce + #12854→#12451 fold + #12896-planned + PM idle); #12526 Constraints line corrected (open-blocker → shipped/mitigated); Recently-Shipped 2026-06-20 line added. Left alone: auto-versioning counter line (DM-owned; #12823 ship-counter-split just changed its semantics — DM to refresh, not PM to guess); Team State (all 4 EVENT + sha 398d1c1a still accurate).
- **Items rejected by human**: (none)

## Scan — 2026-06-20 02:16 (idle-driver tick, 2nd scan of burst)

- **Files scanned**: .squidsquad/config.md (integrity / internal-consistency check — roster, counters, event-reactions, interval coherence)
- **Findings**: none filed. Two candidates examined: (1) Auto-Versioning `Shipped Since Last Bump: 50` vs `Ship Threshold: 10` looks 5× overdue, but version bumps are under the operator's standing bump-hold (CHANGELOG batched to v0.45.0 per Recent-Decisions c1383) AND #12823 just reworked counter mechanics (DM-owned; DM's own comment shows 50→51 active management) → intentional, not a defect. (2) `dm: dm/skill` alias mapping is unusual but the team boots correctly on it and it's unconfirmable-as-wrong without the config.py schema (skill domain) → not fabricating a finding. Rest internally consistent (Iteration-Interval 30 ↔ Cool-Down 30m, Port 7373, Event-Reactions covers all 4 roles, scanning/vault values match driver).
- **Auto-fixed**: none
- **Items rejected by human**: (none)

## Scan — 2026-06-20 03:18 (idle-driver tick, 3rd/burst-cap scan — post-#12912-ship drift hunt)

- **Files scanned**: grep deploy-all / compose.py deploy across references/ (role templates, overlays, commands, docs) — drift check vs the just-shipped #12912 deploy-signal model
- **Findings**: 1 FILED (Tier-2 → #13030, role:skill, low, improvement-scan). #12912 retires agent-manual compose.py deploy-all as the recompose trigger (deploy-signal = sole pull-first path), but PM 'Post-merge recompose' overlay + references/roles/*/instructions.md 'edit source → run compose.py deploy' + dm/skill/instructions.md:27 still direct manual recompose → drift + double-recompose/race risk once the model goes live. GATED on deploy-signal go-live (harness restart) — must NOT land before (current fleet still uses manual model). Scoped to agent-facing manual-trigger instructions only (compose.py command + operator/install tooling stay). No existing tracking issue found (dedup clean).
- **Auto-fixed**: none (Tier-2 cross-role, gated — filed not fixed; references/ is skill domain)
- **Items rejected by human**: (none)
- **Burst note**: 3rd scan of idle period → at_cap, driver cancelled + cron 6c7ee7bc deleted (re-arms on next forge-work re-idle).

## Scan — 2026-06-20 15:47 (idle-driver tick, 1st scan of fresh burst — post-#12896-approval re-idle)

- **Files scanned**: docs/COMPOSE-ARCHITECTURE.md §3.0 (Aliases schema), .squidsquad/config.md ## Aliases, references/scripts/config.py parse_aliases_registry — alias-form doc-vs-reality consistency (prompted by this boot's config.md `dm/skill` revert investigation + the 02:16 scan's unresolved candidate)
- **Findings**: 1 FILED (Tier-2 → #13038, role:pm, low, improvement-scan). §3.0 documents ONLY the canonical 3-column table Aliases form, but live config.md uses the legacy bullet form with packed `<role-class>/<l3-domain>` (`dm: dm/skill`) — supported by config.py (#10385/#12749) but undocumented in the arch doc. Doc-vs-reality TRD drift; cost cycles twice (02:16 scan gave up unconfirmable; this boot's config-revert investigation had to read config.py). Resolution = arch decision: (a) document the legacy bullet form in §3.0, or (b) migrate config.md to the table form. Dedup clean (#10385 closed, no open issue). RESOLVES the 02:16 unconfirmable candidate.
- **Auto-fixed**: none (Tier-2, arch decision — filed not auto-fixed). NOTE for future scans: `dm: dm/skill` is CONFIRMED CORRECT/intentional (L3-variant syntax) — do NOT re-flag as suspicious; the gap is the missing DOC, now tracked in #13038.
- **Items rejected by human**: (none)

## Scan — 2026-06-20 16:47 (idle-driver tick, 2nd scan of burst — installer-readiness, operator-prompted)

- **Files scanned**: docs/INSTALLER-ARCH.md §4.1, references/scripts/wizard.py, start.sh, requirements.txt (fresh-install readiness; prompted by operator "do we have all steps for a new install")
- **Findings**: 1 FILED (Tier-2 → #13041, role:pm, low, improvement-scan). INSTALLER-ARCH §4.1 "Current state (target vs today)" note STALE — 3 claims false vs shipped #11613: (1) wizard.py no longer gh-only (has setup_requirements gather-all + per-platform python3/gh maps); (2) start.sh installs FULL requirements.txt, not 2-of-4; (3) pyyaml already in requirements.txt:16. #11537 pointer imprecise (was the doc-section task, shipped — not the impl). Caused a PM misassessment to operator BEFORE verification → corrected in-conversation. Caught via facts-over-context (read shipped code, not just doc).
- **Auto-fixed**: none (Tier-2 TRD reconcile — needs careful full-state verify of wizard.py consent/re-verify flow; filed not hastily patched).
- **Items rejected by human**: (none)
- **Burst note**: 2nd scan of burst (scan_count 2/3, not at cap) — driver stays armed.

## Scan — 2026-06-20 17:46 (idle-driver tick, 3rd/burst-cap scan — BRIEFING freshness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory staleness check vs this session's forge-verified state + /status)
- **Findings**: BRIEFING stale — top Active-Priorities increment was ~01:00 (pre 2nd-restart); missed today's ship burst (#12912/#12294/#13032/#12409/#12363), #12896 approval + #13035 filing, #12451-S2 unblock, the 2nd restart (sha 398d1c1a→253179a2), the deferred-restart accrual, and the installer-readiness review. Team-State sha + auto-versioning counter (said 0, actually 50) both stale.
- **Auto-fixed**: BRIEFING.md refreshed (PM own-domain, Tier-1) — new 2026-06-20 ~17:20 top increment (2nd-restart + ship burst + #12896-approved/#13035 + #12451-S2 + deferred-restart + installer review + 4 pending operator decisions); Team-State version line → sha 253179a2 boot 14:35; Constraints auto-versioning → 50 (batched v0.45.0, operator-paced).
- **Items rejected by human**: (none)
- **Burst note**: 3rd scan of idle period → at_cap, driver cancelled + cron 707769b1 deleted (re-arms on next forge-work re-idle).

## Scan — 2026-06-21 01:37 (idle-driver tick, 1st/burst scan — freshly-shipped PM sub-skill drift check)

- **Files scanned**: references/sub-skills/roles/pm/pipeline-sentinel.md (just shipped via #12493/#12494), references/sub-skills/roles/pm/improvement-scan.md (cross-ref)
- **Findings**: 1 — residual loop-mode cadence FRAMING in pipeline-sentinel.md header (`### Step 6f` anchor [event-hydrated cycle puts it at Step 4.1], "runs **every cycle**" [event mode = per-cared-event; doesn't run during pure idle — the exact gap #13119 closes], "90 minutes (**3 cycles**)" cadence reasoning). The #12493 rewrite made the halt-detect/investigate/unblock/escalate BODY fully event-aware (EAD, [[comment-handling]], failed-handoff class) — excellent — but left the header framing loop-mode. 90-min WALL-CLOCK threshold itself is correct; only the cadence framing is stale. NOTE: the 2026-06-20 00:02 scan predicted #12493 would sweep this up; it did not — so I did NOT re-defer silently. **NOT separately filed (dedup): routed as an advisory scope-note onto #13119** (skill, open — couples pipeline-sentinel to the idle driver tick → it edits this file's cadence/idle model anyway → natural home for the framing fix). Cannot Tier-1 auto-fix (references/sub-skills/ = skill domain, PM-docs-only boundary).
- **Auto-fixed**: none
- **Items rejected by human**: (none)
- **Context note**: operator signalled imminent harness restart (deferred #13077-reaper activation) once agents idle; pipeline fully drained (0 pending-test/ship/human). Scan kept bounded; chose advisory-on-#13119 over a new orphan task per quality-over-noise + dedup rules.

## Scan — 2026-06-21 12:22 (idle-driver tick, 1st scan of burst — #13158 doc-pairing drift)

- **Files scanned**: docs/HARNESS-ARCH.md §11 Failure Modes table (deploy-pull / deploy-push rows), grep deploy-pull/ff-only/git-pull across docs/*ARCH*.md — drift created by the in-flight #13158 deploy-pull merge fix
- **Findings**: 1 — HARNESS-ARCH §11 rows L510 ('Deploy: git pull non-fast-forward or conflict') AND L512 ('Deploy: git push rejection') document the CURRENT --ff-only behavior (divergence → futile re-pull → deploy-error+respawn, 0 retries). #13158 (pending-test) changes harness deploy-pull to 'git pull --no-rebase' (merge) → benign divergence now MERGES through; both rows become inaccurate on ship. In-lane TRD drift (PM owns HARNESS-ARCH).
- **Auto-fixed**: none (can't pre-edit to unshipped behavior; would describe code that isn't merged). Routed as advisory ON #13158 (couple doc edit to code ship, zero drift window) + tracked in working-state for action on #13158 shipped event. NOT a separate orphan task (dedup/quality — same pattern as #13119).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of burst (scan_count→2/3 after record), driver stays armed.

## Scan — 2026-06-21 13:27 (idle-driver tick, 3rd/burst-cap scan — BRIEFING freshness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory staleness check vs this session's forge-verified ships)
- **Findings**: BRIEFING 12:00 increment said #13158 'filed' — it SHIPPED this session (~15min cycle); #13148/#13147 also shipped; #13030 approved + arch-doc-scoped this session. Recently-Shipped had no 2026-06-21 entry.
- **Auto-fixed**: BRIEFING refreshed (PM own-domain, Tier-1) — 12:00 increment updated (#13158 filed→SHIPPED + HARNESS-ARCH §11 doc-pairing e74fd590a + #13030 approved/scoped/open-question-to-skill); added 2026-06-21 Recently-Shipped entry (#13158/#13148/#13147 + #13030 approval).
- **Items rejected by human**: (none)
- **Burst note**: 3rd scan of idle period → at_cap expected; driver cancels + CronDelete after record-scan.

## Scan — 2026-06-21 18:42 (idle-driver tick, 1st scan of burst — Verbose Mode #13162 post-ship drift check)

- **Files scanned**: references/roles/SOUL.md (L1 postures), references/roles/instructions.md (boot-read selector §234 + no-action-wake §104), docs/AGENT-RUNTIME.md §9.7 (PM-owned TRD), + compose-drift check across all 4 deployed CLAUDE.md (pm/skill/qa/dm). Target chosen: freshest cross-cutting ship (#13162 Verbose Mode, shipped 18:35 this session) = highest drift risk.
- **Findings**: NONE. (1) Three source authoring sites consistent — boot-read selector (`config.py get verbose-mode`, yes→verbose/no→quiet), session-sticky, no-recompose, graceful-default, both postures defined, "all agents + both wake modes" — no contradictions. Wording diffs are explicitly-adaptable example one-liners, not drift. (2) Compose-drift check CLEAN: all 4 deployed CLAUDE.md carry the boot-read selector (1×) + both quiet & verbose postures (2× each) — Verbose Mode correctly deployed fleet-wide.
- **Auto-fixed**: none (clean verification — no drift to fix).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of this idle burst (scan_count→1 after record); driver stays armed.

## Scan — 2026-06-21 19:5x (idle-driver tick, 2nd scan of burst — BRIEFING freshness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory staleness check vs this session's forge-verified events + /status).
- **Findings**: BRIEFING stale — top Active-Priorities increment was ~12:00, missing the entire evening session: #13162 Verbose Mode SHIPPED, the qa verifier wedge + PM recovery, #12271 progress-liveness structuring (Slice A #13179 shipped, cutover #12492 at pending-human-review = operator), #13197 recompose-path-degraded, ships #13066/#13176/#13175, #13185 filed. Recently-Shipped had no evening entry.
- **Auto-fixed**: BRIEFING refreshed (PM own-domain, Tier-1) — new 2026-06-21 ~19:50 top increment (Verbose Mode ship + qa wedge/recovery + #12271 cutover-pending + #13197 + ships + 2 operator advisories); added evening Recently-Shipped bullet (#13162/#13066/#13176/#13175/#13179).
- **Items rejected by human**: (none)
- **Burst note**: 2nd scan of idle burst (scan_count→2 after record); driver stays armed (not at cap).

## Scan — 2026-06-26 ~22:35 local / 03:12Z (idle-driver tick, fresh idle burst — operational gap from skill recovery)

- **Files scanned**: operational — harness restart / auto-reboot path, observed live while recovering the skill agent on operator request this session (no process-file static scan this tick; the live operational finding outranked it).
- **Findings**: TIER-2 (routed as corroboration, not a new file). Spawn-died-before-PID-resolution is a two-sided liveness blind spot: an agent whose initial spawn dies before resolving a claude-PID sits at `status=starting`/`claude_pid=None` forever — (a) PID-liveness poller has no PID to test → never sees "dead" → no auto-reboot; (b) `POST /agents/<role>/restart` sets intent=restarting but the 60s force-kill net has no PID to kill → respawn never fires. Required manual `boot_remote.py`.
- **Dedup**: NOT a new issue — added as point-form corroboration to #12271 (progress-liveness umbrella, pending-human-review). Distinct from the prior alive-PID wedge corroborations there (those are zombie/false-positive); this is the never-resolved-a-PID branch, relevant to shipped Slice A #13179 ("bound the booting escape"). Flagged design data point: progress-liveness needs a never-started/bootup-timeout branch.
- **Auto-fixed**: none (finding belongs to role:skill harness behavior — PM files/corroborates, does not fix code).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of this fresh idle burst (scan_count→1 after record); driver stays armed (not at cap). Live cron 464dc7c3.

## Scan — 2026-06-27 ~04:11Z (idle-driver tick, 2nd scan of burst — BRIEFING freshness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory PM-domain staleness check vs this session's forge-verified events).
- **Findings**: BRIEFING stale — top Active-Priorities increment was 2026-06-22 (5 days), missing this entire session: new fleet restart, operator-requested skill kill+respawn, skill wedge-in-`starting` recovery via boot_remote, #12271 booting-escape corroboration, multiple clean build→verify→ship passes (#13236/#13213/#13212), pipeline now clean, 81-item pending backlog, and the still-live #12271 GO/NO-GO advisory.
- **Auto-fixed**: BRIEFING refreshed (PM own-domain, Tier-1) — added 2026-06-27 top increment (concise; within token budget).
- **Items rejected by human**: (none)
- **Burst note**: 2nd scan of idle burst (scan_count→2 after record); driver stays armed (not at cap). Live cron 464dc7c3.

## Scan — 2026-06-27 ~05:41Z (idle-driver tick, 3rd/final scan of burst — vault decision currency)

- **Files scanned**: .squidsquad/vault/galaxy/decision-pid-primary-liveness.md (vault decision-currency check vs the operator GO on #12271 this session).
- **Findings**: STALE decision — `decision-pid-primary-liveness` was status:active ("PID is primary for liveness"), but operator GO'd #12271 (progress-based liveness → PID demoted to teardown-only) this session. Active decision contradicted the locked direction; would mislead future agents.
- **Auto-fixed**: PM own-domain (Tier-1, vault is PM-maintained institutional memory) — status → superseded-in-progress; added supersession banner (operator GO, cutover #12492 sequencing, wedge-incident drivers); changelog entry; linked to [[learning-graceful-restart-grace-timer-on-wedged-agent]]. Content kept as current-runtime-behavior until #12492 ships (then archive).
- **Items rejected by human**: (none)
- **Burst note**: 3rd/FINAL scan — record-scan returned at_cap:true → driver cancelled (`subloop_driver.py cancel pm`) + cron 464dc7c3 deleted (CronDelete). Burst exhausted; re-arms on next re-idle after forge work.

## Scan — 2026-07-11 09:42 (idle-driver tick, 1st scan of burst — vault decision currency vs shipped #12492)

- **Files scanned**: .squidsquad/vault/galaxy/decision-pid-primary-liveness.md (currency check: last scan 2026-06-27 parked it at superseded-in-progress "archive when #12492 ships"; #12492 has since shipped — verify reconciliation landed).
- **Findings**: NONE. Decision is correctly finalized — status: archived; ARCHIVED/SUPERSEDED banner names #12492 SHIPPED; changelog carries the final "status -> archived" entry (progress-liveness authoritative, PID teardown-only). Content matches shipped runtime reality; no drift. (The working-tree ' M' on this file is a pre-commit state, not a content-drift finding.)
- **Dedup note**: The arch-doc sibling drift (HARNESS-ARCH + AGENT-RUNTIME still frame progress-liveness as 'proposed/not-detected') is ALREADY tracked at #13319 (role:pm, pending) — not refiled.
- **Auto-fixed**: none (clean verification — nothing to fix).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of this idle burst; driver record-scan next. Live cron 2955cb0a.

## Scan — 2026-07-11 ~14:19 local / 18:19Z (idle-driver tick, 3rd/FINAL scan of burst — live operational gap)

- **Files scanned**: references/sub-skills/common/boot-remote-agents.md (PM manual-boot trigger conditions), cross-ref health-check.md — driven by this session's live incident (harness in bare mode, qa+skill dead ~30min, no auto-reboot, manual boot_remote required).
- **Findings**: TIER-2 → filed **#13545** (role:skill, low, improvement-scan). boot-remote-agents lists only "harness down" / "agent stayed dead" as manual-boot triggers; misses the "harness UP + /status responsive but auto-reboot structurally disabled (bare mode #12525)" case. A future PM could see /status respond and wrongly assume auto-reboot works. Sub-skill = compose-consumed → skill lane (precedent #13317).
- **Dedup**: no existing open issue on bare-mode/auto-reboot-disabled (#13473 is the operator coordination hold for THIS restart, not a durable trigger-doc fix; #6787/#3496 unrelated).
- **Auto-fixed**: none (sub-skill is skill-lane, not PM-editable; PM files, does not edit compose-consumed instructions).
- **Items rejected by human**: (none)
- **Burst note**: 3rd/FINAL scan — record-scan at_cap:true → driver cancelled + cron 8bb66e47 deleted. Burst exhausted; re-arms on next re-idle after forge work.

## Scan — 2026-07-11 ~17:2x local (idle-driver tick, 1st scan of fresh burst — BRIEFING staleness)

- **Files scanned**: .squidsquad/vault/BRIEFING.md (mandatory PM own-domain staleness check vs this session's forge-verified events).
- **Findings**: BRIEFING top increment was 09:31 (morning), missing the entire afternoon: 13:52 respawn, bare-mode harness + dormant #13456/#13472/#13494 fixes + qa/skill manual boot (#13545), primary-clone now-synced, the #13554 SEV data-loss (squash 57b8faa66) + dm recovery + merged fix PR#13559 + #13556 defense-in-depth, my Windows-path-mangle false-alarm + retraction, #13263 reversal (keep-open).
- **Auto-fixed**: BRIEFING refreshed (Tier-1 PM own-domain) — new 2026-07-11 ~14:00-17:20 top increment (concise; SEV + recovery + bare-mode + operator actions).
- **Items rejected by human**: (none)
- **Burst note**: 1st scan of fresh re-idled burst (scan_count→1 after record); driver stays armed. Live cron c41f4c94.

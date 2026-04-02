## FEAT-SKILL-033 — Heartbeat branches for agent health detection

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: Replace git-commit-based agent health detection with lightweight heartbeat branches. Each agent force-pushes a single-commit orphan branch (`heartbeat/<role>`) every cycle with a timestamp. The PM fetches and reads these branches to determine agent health, instead of relying on `git log --grep` which only detects agents that have work to commit. This solves the false-stalled problem where agents on quiet cycles (nothing to commit) appear dead.
- **Rationale**: Current health detection requires agents to push commits to main. Agents on quiet cycles produce no commits and appear stalled indefinitely. Heartbeat branches are git-native, work across machines, don't pollute main branch history, and unprotected branches allow force-push by default on GitHub (no repo config needed).
- **Acceptance Criteria**:
  - [ ] `references/heartbeat.sh` — standalone shell script that pushes orphan `heartbeat/<role>` branch on a loop (no agent involvement)
  - [ ] Boot scripts (`start-<role>.sh`) launch `heartbeat.sh` as a background process with role and interval args
  - [ ] Heartbeat script uses `git mktree` + `git commit-tree` + `git push -f` (no checkout, no working tree impact)
  - [ ] PM reads `heartbeat/<role>` via `git fetch` + `git log` to check agent liveness
  - [ ] No commits added to main branch for heartbeat purposes
  - [ ] Heartbeat interval is configurable in `config.md` (e.g. `Heartbeat Interval Seconds: 10`), default 10 seconds
  - [ ] SKILL.md setup flow includes a step asking the user to configure heartbeat interval (default 10s), explaining that agents will push lightweight `heartbeat/<role>` branches
  - [ ] PM uses configured heartbeat interval as the staleness threshold (agent stalled if heartbeat older than configured interval)
  - [ ] PM CLAUDE.md Step 7 updated to use heartbeat branches instead of `git log --grep`
  - [ ] Dev agent CLAUDE.md does NOT reference heartbeat — it's entirely handled by shell script
  - [ ] SKILL.md setup/templates updated accordingly
  - [ ] SKILL.md upgrade steps populate `Heartbeat Interval Seconds` in existing config.md (default 10s if missing)
  - [ ] Works across machines (agents on different hosts)
  - [ ] README.md includes a dedicated section explaining heartbeat branches (what they are, how they work, how to configure interval, how PM uses them for health detection)

### Discussion

> [2026-03-29 12:40] **pm/qa**: Filed from human discussion. Human identified that git-commit-based health detection causes false stalls on quiet cycles. Explored options: gitignored files (local only), GitHub Issues (API abuse), git notes (not pushed by default), heartbeat branches (git-native, cross-machine). Human approved heartbeat branches approach. Status: Pending — awaiting human approval.
> [2026-03-29 12:45] **pm/qa**: Human requested heartbeat interval be configurable in config.md, independent of iteration interval. Added to acceptance criteria.
> [2026-03-29 12:48] **pm/qa**: Human wants heartbeat setup as an explicit step in SKILL.md setup flow so the user is aware agents will push heartbeat branches. Default interval 10 seconds. Updated acceptance criteria.
> [2026-03-29 12:50] **pm/qa**: Human requested upgrade steps also populate the heartbeat interval config var for existing installs. Added to acceptance criteria.
> [2026-03-29 12:55] **pm/qa**: Human: heartbeat must NOT be done by agents — must be a standalone shell script launched by boot scripts as background process. Updated acceptance criteria: `references/heartbeat.sh` runs independently, agents are unaware. Human approved. Status → Planning. Beginning intake process.
> [2026-03-29 13:00] **pm/qa**: Planning complete. RESEARCH.md, CONTEXT.md, TEST-PLAN.md created. All key decisions locked by human during discussion. Status → Approved.
> [2026-03-29 13:04] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 13:10] **skill-lead**: Complete. Created `references/heartbeat.sh`, updated boot script templates with heartbeat launch + PID management, added `Heartbeat Interval Seconds` to config.md template and live config, added Step 5c to SKILL.md setup, updated PM Step 7 in agent-instructions.md to use heartbeat branches, updated statusline.sh health icons to read heartbeat branches, added upgrade migration for heartbeat config, updated CHANGELOG.md and README.md. Status → Pending Test.
> [2026-03-29 13:15] **pm/qa**: Human requested heartbeat branches get their own dedicated section in README.md documentation. Added to acceptance criteria.
> [2026-03-29 13:35] **pm/qa**: Verified all 13 acceptance criteria. heartbeat.sh exists and matches reference, boot scripts launch it with PID management, uses mktree+commit-tree+push-f, PM reads heartbeat branches via fetch+log with 3× staleness threshold, config.md has Heartbeat Interval Seconds, SKILL.md Step 5c added, agent-instructions.md PM Step 7 updated, dev CLAUDE.md has no heartbeat references, upgrade migration included, README.md has dedicated section. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).

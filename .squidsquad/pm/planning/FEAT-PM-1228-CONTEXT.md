# FEAT-PM-1228 Context — PM Pipeline Sentinel

## Scope

Restructure the PM Ralph Loop to separate pipeline management from testing/verification. Create a new always-run pipeline-sentinel sub-skill that handles PR conflict detection, stall detection, and pipeline nudging. Move PR merging responsibility to the dev agent (after QA verification). PM monitors and nudges but does not merge.

## Locked Decisions (human decided)

- **Architecture**: New `pipeline-sentinel.md` sub-skill — runs as its own step after the QA-skippable block, never skipped when QA is present. Clean separation of pipeline management from testing/verification.
- **Conflict detection gate**: Branch Workflow setting gates conflict detection, NOT PR Flow. If Branch Workflow: yes, check PR conflicts regardless of PR Flow setting.
- **Planning suppression**: Sentinel is skipped during planning suppression. 30-minute gap is acceptable.
- **PR merge ownership**: Dev merges PRs after QA verification (pending-ship status). PM does NOT merge — PM monitors and nudges if dev hasn't merged within stale threshold. This mirrors real-world dev team behavior.
- **PM role**: Surveillance + nudge. PM detects stalled items, conflicting PRs, unmerged pending-ship tasks, and takes corrective action (comments, status fixes) or reports to human.

## Dev Discretion (dev agent can choose)

- Exact step number/position for the sentinel in the Ralph Loop
- Stale threshold default value (suggest 2-3 cycles / 60-90 min)
- How dev agent detects pending-ship status on its own tasks (polling tracker vs working-state check)
- Exact format of nudge comments

## Side Effect Mitigations (required)

- QA-present gate must ONLY skip testing/verification steps, not pipeline management
- Existing PM-as-DM delivery fallback (Step 6d) must still work when DM is absent
- Post-merge recompose (Step 6e) must still run when branches merge
- Dev template must gain "merge your PR when task hits pending-ship" instruction
- All existing tests must pass after restructuring

## Upgrade Path (required)

- Template changes in references/sub-skills/pm-specific/ and references/sub-skills/dev-specific/
- New sub-skill: references/sub-skills/pm-specific/pipeline-sentinel.md
- references/roles/pm/includes.yml updated
- compose.py deploy-all regenerates all CLAUDE.md files
- No new config values needed (uses existing Branch Workflow, Auto Merge settings)
- Graceful degradation: old templates still work, just miss pipeline sentinel behavior

## Out of Scope

- PM auto-merging PRs (dev does this now)
- Changes to QA verification flow
- New config settings
- Dashboard or reporting changes
- Stall detection for non-SquidSquad issues

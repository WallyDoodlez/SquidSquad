# Working State

- **Task**: idle (waiting on #9837 ship-pipeline fix)
- **Status**: idle — handover ready
- **Last Processed Event ID**: 2461e3f1

## Critical path
- **#9837** (in-progress, skill) — tracker.py list-tasks blind to closed-but-labeled items. Blocking ship pipeline.
- Once #9837 ships: DM can see + ship the 6 pending-ship items → version bump v0.40.0 → v0.41.0

## Pending-ship queue (invisible to DM until #9837)
- #9740, #9741, #9742, #9744 (Tier 1 audit findings)
- #9725 (spawn-prompt fix)
- #9772 (config.md ship-counter clobber, shipped via #9838)
- #9813 (event_bus.ack() Phase 4 cleanup)

## Awaiting QA
- **#9478** branch_workflow=off removal

## Harness intermittent stalls — revised understanding
- NOT a chronic wedge — verified via 3x curl retries returning HTTP 200 in 2ms after one HTTP 000 probe
- Occasional 5s+ stalls; single probes can land in bad window
- cycle_pre alternates between 'reachable' and 'unreachable' depending on probe luck
- Polling-mode unaffected
- Event-mode would degrade gracefully via existing 5s timeout fallback
- Probably worth a low-severity bug to investigate the latency spikes; not urgent

## Post-flip queue (locked)
- #9748 — agent setup self-install
- #3498 — backlog audit L2 sub-skill

## Fleet flip prerequisites
- ✅ All Tier 1 audit findings landed at pending-ship
- ⏳ #9837 ship-pipeline fix (in-progress on skill)
- ⏳ DM clears pending-ship queue once visible
- ⏳ Version bump fires
- ⏳ #9478 QA verify
- Then: fleet flip

## Memory rules added this session
- feedback-proactor-loop-two-bugs
- feedback-minimal-repro-over-symptom-match (just reaffirmed via harness 'wedge' misdiagnosis)
- feedback-orphan-claude-from-subagents
- feedback-tracker-comment-prefix
- feedback-orphan-claude-on-reboot

### Event Reactions (Creative Phase Guidance)

The `recent_events` field in `cycle-input.json` contains events that occurred since your last processed cursor. The mechanical layer (`cycle_pre.py`) already filtered these to your role's relevant event types and executed any high-confidence mechanical reactions (listed in `mechanical_reactions`).

Your job in the creative phase is to **interpret events that require judgment** — things the mechanical layer cannot decide autonomously.

#### What each event type means for you

| Event Type | What happened | Your action |
|---|---|---|
| `status-transition` | A tracker item changed status | Check if it affects your current work or queue |
| `pr-merged` | Harness merged a PR (code landed on main) | Pull latest on next task boundary; check if merged code affects your work |
| `compose-completed` | Harness ran compose after a merge touching references/ | Your templates may have changed — harness reboots affected agents automatically |
| `request-merge` | An agent requested harness to merge a PR | Audit trail only — no action needed |
| `verification-failed` | Verifier/PM found gaps in submitted work | If your task: read feedback, fix gaps |
| `verification-passed` | Verifier/PM verified work is complete | If your task: await shipping |
| `agent-health` | Another agent's health changed | Note if it blocks your work |
| `cycle-start` / `cycle-end` | Another agent completed a cycle | Informational only |
| `tracker-comment` | An agent commented on a tracker item | Read if it mentions your task |
| `phase-change` | A task moved lifecycle phases | Check if it unblocks your queue |

#### Mechanical vs Creative

- **Already done** (in `mechanical_reactions`): The mechanical layer handled these. Read them for awareness but do not re-execute.
- **Needs your judgment**: Events in `recent_events` that are NOT covered by `mechanical_reactions`. These require you to read context, make decisions, and act.

#### Rules

- **Never re-process mechanical reactions** — they already executed. Duplicating would cause double-transitions or duplicate comments.
- **Self-emitted events are pre-filtered** — you will not see your own past emissions. No loop risk.
- **Cursor advances automatically** — events processed this cycle will not appear next cycle.
- **When in doubt, investigate** — read the tracker item referenced in the event payload before acting.

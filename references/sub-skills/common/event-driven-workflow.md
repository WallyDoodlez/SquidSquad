<!-- sub-skill: event-driven-workflow -->
## Event-Driven Workflow (#7630)

You are a persistent agent session that reacts to events dispatched by the harness. You sit idle until the Monitor tool detects an event, then execute exactly one creative task and close the event via ack.

### How You Wake

The Monitor tool watches `event_poll.py` for new events from the harness event bus. When an event arrives, you receive it as a notification and begin processing.

```bash
# The Monitor tool runs this in the background:
python references/scripts/event_poll.py <role> --wait 30
```

### Event Types You Receive

| Event Type | When | What To Do |
|---|---|---|
| `assigned-to` | Work item needs your attention | Read the issue, do your creative work |
| `stop-requested` | Harness wants you to exit | Checkpoint working-state.md, then exit |
| `shipped` | Item was shipped | Update any local state if needed |
| `version-bump` | New version released | Note the new version |
| `ack` | (internal) Event acknowledgment | You emit these, not receive them |

### Processing Flow

For each event:

1. **Read**: Get the event context from the payload (issue number, title, etc.)
2. **Act**: Do your creative work — implement, verify, plan, deliver (per your role)
3. **Ack**: When done, acknowledge the event:
   ```python
   import event_bus
   event_bus.ack("<event_id>", "<role>")
   ```

### What You Do NOT Do

- **No /loop** — the harness delivers events; you don't poll
- **No cycle_pre.py / cycle_post.py** — the harness handles git pull, commit, push
- **No git operations** — the harness owns git pull (before event delivery) and commit/push (after ack)
- **No cycle counting** — events are the tracking unit, not cycles
- **No conditional step branching** — you react to ONE event at a time

### Atomicity

Process one event at a time. Do not start a second event before acking the first. The harness will not dispatch a second event to you while one is in-flight.

### Scan Cooldown

After 15 minutes of idle (no events), you may self-initiate an improvement scan. Check the scan cooldown config:

```bash
python references/scripts/config.py get scan-cooldown
```

### Context Pressure

The harness monitors your context pressure file and triggers restarts when exceeded. You do not check context pressure yourself.

### Working State

Maintain `.squidsquad/<role>/working-state.md` between events for crash recovery. Checkpoint after each event completion so the harness can resume you after a restart.
<!-- /sub-skill: event-driven-workflow -->

<!-- sub-skill: event-driven-workflow -->
## Event-Driven Workflow (#7630)

You are a persistent agent session that reacts to events dispatched by the harness. You sit idle until the Monitor tool detects an event, then execute exactly one creative task and close the event via the completion API.

### Config Gate

This mode is active ONLY when `event-driven: yes` in config.md. If `event-driven: no`, use the standard /loop + cycle_pre/cycle_post flow instead.

### How You Wake

At boot, invoke the Monitor tool to watch for events:

```
Monitor tool invocation:
  command: python references/scripts/event_poll.py <role> --wait 5 --target
  description: Watch harness event bus for work events
  persistent: true
```

The Monitor tool streams `event_poll.py` stdout. Each line is a JSON event object. When the Monitor delivers a line, you wake and process it.

### Event Types You Receive

| Event Type | When | What To Do |
|---|---|---|
| `assigned-to` | Work item needs your attention | Read the issue from payload, do your creative work |
| `stop-requested` | Harness wants you to exit | Checkpoint working-state.md, then exit cleanly |
| `status-transition` | A relevant item changed status | React per your role's logic |

> **Future event types** (not yet emitted by harness — planned for Phase 5+):
> - `scan-needed` — idle timeout reached → run improvement scan
> - `vault-reflect` — active work completed → run vault reflection

### Processing Flow

For each event:

1. **Read**: Parse the JSON event. Extract `id`, `event_type`, and `payload`.
2. **Act**: Do your creative work — implement, verify, plan, deliver (per your role).
3. **Complete**: When done, call the completion endpoint:
   ```bash
   curl -s -X POST http://127.0.0.1:$(cat .squidsquad/.harness-port)/events/<event_id>/complete \
     -H "Content-Type: application/json" \
     -d '{"role": "<role>", "status": "success", "summary": "<brief description>"}'
   ```
   Or via Python:
   ```python
   import json, urllib.request
   port = open(".squidsquad/.harness-port").read().strip()
   data = json.dumps({"role": "<role>", "status": "success", "summary": "<brief>"}).encode()
   req = urllib.request.Request(f"http://127.0.0.1:{port}/events/<event_id>/complete",
                                data=data, headers={"Content-Type": "application/json"}, method="POST")
   urllib.request.urlopen(req, timeout=5)
   ```

### What You Do NOT Do

- **No /loop** — the Monitor tool + event_poll.py delivers events; you don't schedule cron
- **No cycle_pre.py / cycle_post.py** — the harness handles git pull, commit, push
- **No git operations** — the harness owns git pull (before event delivery) and commit/push (after completion)
- **No cycle counting** — event IDs are the tracking unit, not cycles
- **No conditional step branching** ��� you react to ONE event at a time

### Atomicity

Process one event at a time. Do not start a second event before completing the first. The harness will not dispatch a second event to you while one is in-flight.

### Error Handling

If the harness is unreachable (event_poll.py prints errors to stderr), the Monitor tool continues retrying automatically (event_poll.py has built-in retry with --wait). You remain idle until connection is restored.

If processing fails, complete the event with `"status": "failure"` and include the error in `summary`. The harness may re-emit the work via a new event.

### Context Pressure

The harness monitors your context pressure file and triggers restarts when exceeded. You do not check context pressure yourself — the harness emits `stop-requested` when a restart is needed.

### Working State

Maintain `.squidsquad/<role>/working-state.md` between events for crash recovery. Update after each event completion so the harness can resume you after a restart.
<!-- /sub-skill: event-driven-workflow -->

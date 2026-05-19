## Cursor Management

Your event cursor is the last event id you have processed. It lives in `.squidsquad/<role>/working-state.md` under the line:

```
- **Last Processed Event ID**: <event-id>
```

`event_poll.py` reads and advances this cursor on your behalf — you do not write it manually under normal operation. The rules below apply when you DO need to interact with it directly (boot, crash recovery, gap handling).

### Atomic Update Protocol

When advancing the cursor, write the new value to `<path>.tmp` then `os.replace` (or `mv`) it onto `working-state.md`. **Never** write the cursor in place — a reader catching a half-written file would observe an undefined cursor and re-deliver or skip events.

`event_poll.py` handles this for the event-listening loop. If you advance the cursor by hand (e.g. on boot after skimming events), follow the same protocol.

### Per-Event Advance, Not Per-Batch

When a poll returns a batch of events, the cursor advances **after each event is durably persisted**, not after the whole batch. This makes mid-batch process death safe — on restart, the next poll resumes after the last successfully-persisted id.

### Gap Scenarios

Three kinds of cursor gap exist (CONTEXT.md §2):

- **In-stream gap.** You received events `[10, 11, 13]` — no event `12`. Log a warning naming the gap; advance to the highest observed id and forge-read affected items.
- **Long lag.** Your cursor is hundreds or thousands of events behind. Skim-then-advance through the stream; do not jump to latest. The forge already has current state — the stream is just informational.
- **Eviction gap.** Your cursor predates the oldest retained event in the harness deque. `GET /events?since=<old>` returns the oldest available id and an eviction-count hint. Log an eviction warning naming the oldest available id and the count of evicted events; advance the cursor to that oldest available id; proceed to a forge-read for current state. Do NOT crash.

### Crash Recovery

On restart, `event_poll.py` reads the cursor from `working-state.md` and resumes polling from `cursor+1`. Because writes are per-event-atomic, the resume point is exactly the first unprocessed event — no duplicates, no skips.

If the cursor is missing or empty, the agent starts from the beginning of the stream with a stderr warning. Use `event_poll.py --since <id>` to bootstrap a specific cursor at first run.

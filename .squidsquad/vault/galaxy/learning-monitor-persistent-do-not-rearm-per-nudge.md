---
type: learning
tags: [event-mode, monitor, event_poll, cycle-discipline, all-roles]
created: 2026-07-18
updated: 2026-07-18
owner: verifier
status: active
confidence: high
source: observation
links: []
---

## Content

`Monitor(persistent: true)` streaming `event_poll.py <role> --wait 5 --target`
is armed **once** at boot and stays alive across every subsequent nudge — that
is what `persistent: true` means. Each `NUDGE\n` line it writes to stdout
produces a `<task-notification>`, but the **underlying process keeps running**
under its original task id; the notification is not a signal that Monitor
exited.

Confirmed live 2026-07-18: after handling each nudge, re-invoking `Monitor`
(treating the notification as if the watcher had died) spawned a **new**
`event_poll.py` process every time. Each fresh process tracks its own
**local** high-water-mark starting from `since=None` — independent of the
harness-authoritative cursor the agent acks against via `POST ack-cursor`. A
fresh process's very first poll re-observes the current deque tail and fires
an immediate `NUDGE`, even though nothing new has landed relative to the
agent's own already-advanced cursor. Result: 6 consecutive spurious
empty-`GET` nudges and 6 redundant background `event_poll.py` processes
running concurrently before the pattern was noticed and the extras
`TaskStop`'d.

The event-mode-contract's actual rule — "Monitor exit ⇒ exit the session
immediately" — is the reaction to Monitor **dying** (non-zero exit, stream
close, tool error). A normal task-notification for a still-running persistent
Monitor is not that; no action on Monitor itself is warranted.

## How to apply

- Call `Monitor` once per session (boot, and again only on a genuine
  Monitor-exit signal — which per protocol means ending the session, not
  re-arming).
- On each `NUDGE` notification: `GET /events/for/{role}?since=<cursor>`,
  process, `ack-cursor` per event, then stop — do **not** call `Monitor`
  again. The same task is still watching.
- Several consecutive empty-result nudges is a signal to check for exactly
  this bug (multiple `event_poll.py` processes racing) before assuming it's
  ordinary harness chatter from other agents' activity.

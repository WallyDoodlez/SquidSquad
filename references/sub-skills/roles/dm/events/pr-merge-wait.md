---
slot: instructions
ordinal: 30
roles: [dm]
---

## DM — PR-Merge Wait (Event Mode)

DM is the one role whose work routinely spans **waiting on an external system**: a feature PR must merge before DM can transition the corresponding tracker item to `shipped` and run delivery packaging. Event mode makes this wait a single atomic task that DM holds open until the merge resolves (or DM rolls it back).

This fragment defines DM's behavior across the lifecycle of a `pending-ship` task. It builds on [[event-mode-contract]] (Cases A–E), [[forge-read-pattern]], and [[comment-handling]] — read those first.

### The Task IS The Wait

A `pending-ship` item assigned to DM is an active task even though DM is "just" waiting on a PR merge. From the agent's point of view this is a single atomic task per [[event-mode-contract]] Case D: DM holds the Task field set to the issue number for the full wait, and the task only completes when DM has confirmed (via forge-read) that the PR has reached a terminal state — merged, closed without merge, or blocked by an unresolvable merge conflict.

### Pickup-Time Readiness Check

When DM picks up a `pending-ship` item via `work_queue()`, before entering the wait, DM forge-reads the PR (`gh pr view <number>` or equivalent) and inspects three signals:

- **CI status** — green / red / pending
- **Review state** — approved / changes-requested / blocked
- **Mergeable state** — `MERGEABLE` / `CONFLICTING` / `UNKNOWN` (transient)

The five resulting pickup branches:

1. **Already merged** (the PR state is `merged` at pickup — a human merged manually, or a prior DM execution merged but crashed before transitioning) → skip the wait entirely and fall through directly to End-Of-Task Re-Read.
2. **Ready to merge** (open, CI green, no blocking reviews, `MERGEABLE`) → if auto-merge is configured for the project, merge directly, **then verify via forge-read that the PR state is now `merged`**, then fall through to End-Of-Task Re-Read below. If the merge attempt did not produce `merged` state (network blip, server-side race, permissions), fall back to the begin-the-wait path — do NOT pretend the merge succeeded. If auto-merge is NOT configured, begin the wait described below: in this configuration the merge is performed by a human (the project policy), and the wait exits when that human action lands as PR `merged`. The stalled-PR ceiling is the safety net if the human never acts.
3. **CI red OR review blocking** → comment a one-line summary of the cause on the issue, transition `pending-ship → in-progress` so the assigned worker role can fix the underlying problem, clear the Task field, fall through to Case C.
4. **`CONFLICTING`** → same rollback as branch 3: comment, transition back to `in-progress`, clear Task, fall through.
5. **`UNKNOWN`** → GitHub is computing the mergeable state; treat as the wait case (branch 2's begin-the-wait path) and recheck on next forge-read.

Branches 3 and 4 do NOT transition to `shipped` (they actively roll back). Branch 5 enters the wait and may eventually ship via outcome (d) once GitHub finishes computing the mergeable state. Running delivery before a PR has merged would commit to a release of code that may never reach `main`.

### No Sub-Loop During The Wait

Per [[comment-handling]] DM exception: comments arriving on the issue during the wait are NOT polled in real time. DM does NOT enter a watch loop, does NOT re-read the issue every few seconds, and does NOT react to comments mid-wait. Doing so would violate the atomicity rule in [[event-mode-contract]] Case D — events arriving mid-task are noted but not acted upon, and their information is absorbed by DM's final forge-read at task completion.

The reaction window for a comment that arrives during the wait is "the moment the wait ends" — see "End-Of-Task Re-Read" below.

### How DM Detects The Merge

The wait is implemented as a **bounded periodic forge-read**, NOT as event-driven action. Events arriving on the stream during the wait are handled per [[event-mode-contract]] Case D (noted, not acted on) — they are NOT what triggers DM to recheck the PR.

On each Monitor wake (the persistent `event_poll.py` heartbeat at the role's wait cadence), DM performs two cheap tracker checks **before** the PR forge-read so an operator redirect lands in one wake interval rather than waiting for PR terminal state (#9744):

1. **Label re-check** — `python references/scripts/tracker.py get-labels <issue-number>`. If ANY label name starts with `pending-human-` (covers `pending-human-review`, `pending-human-approval`, `pending-human-setup` — the three taxonomy variants), the wait ends immediately; fall through to End-Of-Task Re-Read, where outcome (a) will trigger because the label is present.
2. **Status re-check** — `python references/scripts/tracker.py get-state <issue-number>`. If the status is no longer `pending-ship` (operator transitioned the item elsewhere mid-wait), the wait ends immediately; fall through to End-Of-Task Re-Read, where outcome (b) will trigger.

Use prefix matching (`name.startswith("pending-human-")`) so any future `pending-human-*` label added to the taxonomy is honored automatically. Do NOT hard-code the three current variants — the prefix match is the contract.

If neither tracker check triggers an abort, DM forge-reads the PR exactly once and inspects:

- **PR state == merged** → the wait ends, fall through to End-Of-Task Re-Read.
- **PR state == closed and not merged** → the wait ends with a rollback; fall through to End-Of-Task Re-Read.
- **PR state == open but `CONFLICTING`** → conflict developed mid-wait; the wait ends with a rollback. Fall through to End-Of-Task Re-Read.
- **PR state == open and (`MERGEABLE` or `UNKNOWN`) BUT the wait has exceeded the project's configured stalled-PR ceiling** (a per-project policy setting; default unbounded) → the wait ends with a rollback (stalled-PR ceiling exceeded); fall through to End-Of-Task Re-Read.
- **PR state == open and (`MERGEABLE` or `UNKNOWN`) and wait has not exceeded the ceiling** → wait is not over; return to wait.

Event payloads about the PR are hints; the forge is authoritative ([[forge-read-pattern]]).

The two pre-check tracker calls cost one round-trip each per wake — equivalent in shape to the PR forge-read that already runs, so the per-wake cost roughly doubles but stays bounded by the wake cadence. The trade-off vs the prior behavior (operator redirect could be delayed indefinitely if the PR never reached a terminal state) is intentional per CONTEXT-9744 Risk 3.

### End-Of-Task Re-Read

When the wait ends, DM performs a **single, complete re-read** of both the issue and the PR before deciding the outcome:

1. **Re-read the PR** (`gh pr view <number>` or equivalent) so outcomes (c) and (d) compare against the freshest PR state, not the stale detection-phase snapshot. The TOCTOU qualifier in outcome (c) depends on this read.
2. **Re-read issue comments** since DM last touched the item. Comments accumulated during the wait are honored here — never mid-wait.
3. **Re-check the issue's current labels and status** for any operator changes that should redirect DM (e.g. a human flipped the item to `pending-human-review`, or transitioned it back to `planning`).
4. **Pick exactly one outcome, evaluated in this precedence order** — earlier rules take priority because operator redirection is more authoritative than the PR's terminal state:
   - **(a)** **A `pending-human-*` label appeared during the wait** → leave the item where the operator put it; do NOT transition. The human handoff wins regardless of PR state.
   - **(b)** **The issue is no longer at `pending-ship`** (operator transitioned it to another status during the wait) → leave it where the operator put it; do NOT transition further. Comments on the new owner are honored at their next pickup.
   - **(c)** **PR is not merged AND (closed without merge, OR open-but-conflicted, OR stalled-PR ceiling exceeded)** (rollback) → comment a one-line summary of the cause, transition `pending-ship → in-progress` so the assigned worker role can address it. Do NOT run delivery. The "not merged" qualifier prevents a stale rollback if the PR transitioned to `merged` in the interval between the detection forge-read and this re-read — in that case fall through to outcome (d).
   - **(d)** **PR merged AND the issue is still at `pending-ship`** → **first** check the issue's Discussion for a `delivery: skip` marker (mandatory per DM's always-on prohibitions). If `delivery: skip` is present, skip delivery packaging and transition `pending-ship → shipped` directly. Otherwise run delivery packaging (CHANGELOG, version bumps as configured) and then transition `pending-ship → shipped`. Either way the transition auto-closes the issue.
5. **Update working-state** → `- **Task**: none` (atomic write per [[event-mode-contract]] ownership discipline). If outcome (a) or (b) was taken there was no transition, so DM did NOT just complete a tracker transition — see step 6.
6. Run `work_queue()` for the next DM item. This is the same forge-read step that Case C performs after a transition; in outcomes (a) and (b) you skip Case C's "you just transitioned" preamble (no transition occurred) and go straight to the queue read.

### Comment Examples (For Future Reference)

| When the comment arrives | When DM acts on it |
|--------------------------|-------------------|
| Before DM picks up the item | At pickup (forge-read absorbs all prior comments) |
| During the PR-merge wait | At task end (End-Of-Task Re-Read above) |
| After DM ships the item | Never — the issue is closed; new work must come as a new tracker item |

Senders who need DM to react faster than "end of current wait" must ride a status transition or label change ([[comment-handling]] transition-on-handoff rule). A comment alone is not enough.

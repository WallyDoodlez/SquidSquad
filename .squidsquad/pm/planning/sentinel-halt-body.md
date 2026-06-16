## Operator directive (2026-06-16, L2 — PM role layer)
"Pipeline sentinel monitors the flow of the pipeline — it should check for halt, and actively investigate and unblock if possible, otherwise ask for decision."

Enhance the EXISTING `references/sub-skills/roles/pm/pipeline-sentinel.md` (L2/PM) — do not duplicate; extend in place.

## Why now (concrete incident — make this the worked example)
#12460 sat halted ~2.5h. Root cause: skill finished the shadow increment and posted a "DM please merge PR #12472" **ask as a bare comment**. Per comment-handling, bare comments wake NO agent in event mode — so the handoff silently failed, skill went idle, and the pipeline stalled. The current sentinel missed it because its `in-progress` stall rule keys on *"no recent comments"* — but #12460 HAD recent comments (the failed ask). Worse: the sentinel's own remedy is a bare-comment "nudge," which also wakes no one. A human had to notice ("I don't see any agent working").

## Gaps to close
1. **Halt detection is progress-based, not comment-based.** A halt = *no forward progress* on a non-terminal item past threshold — INCLUDING when comments exist but contain an unactioned ask/handoff while the owning agent is idle. The current "no recent comments = stalled" test misses the failed-handoff case; broaden it.
2. **Investigate root cause before acting.** Classify the halt (at least): (a) owner idle awaiting a handoff that never fired an event (bare-comment ask), (b) dead/stalled agent, (c) blocked on a human decision, (d) genuine no-progress / saturation.
3. **Unblock must be EVENT-MODE-EFFECTIVE.** For an event-mode owner, a bare comment does NOT wake it — so the unblock must ride a wake-causing action: inject an `assigned-to` wake event (the documented PM nudge), or a status transition where PM has authority. Replace/augment the existing bare-comment "nudge" remedies with event-effective ones. Cross-reference comment-handling.
4. **Escalate for decision when PM can't unblock.** If no in-authority unblock exists (e.g. the halt needs a process choice, as #12460 needed the shadow-vs-split call), surface to the human with (i) investigation findings and (ii) concrete options — not a silent bug-file, not inaction.

## Scope (within PM boundaries — load-bearing)
"Unblock" = only actions PM is authorized to take:
- inject an `assigned-to` wake event to re-fire a failed handoff,
- a status transition where PM HAS authority,
- convert draft PR → ready (metadata),
- boot a dead/stalled agent via `boot_remote.py` (stall-recovery only),
- escalate to human.
PM must NOT, as "unblock": transition another role's task, merge/close PRs, or touch branches. Detect → investigate → act-within-authority → else escalate.

## Acceptance criteria (testable; comprehension-gated per project rule)
1. The sub-skill defines "halt" as lack of forward progress past threshold, EXPLICITLY including "comments exist but carry an unactioned ask/handoff while owner is idle" (the failed-handoff case).
2. A per-halt **investigate** step classifies the cause into ≥4 named classes (failed-handoff / dead-agent / blocked-on-decision / genuine-no-progress) before any remedy.
3. Remedies are event-mode-effective: for an event-mode owner the prescribed action is a wake-causing one (inject `assigned-to` / authorized transition), and the doc explicitly states a bare comment does NOT wake an agent (cross-ref comment-handling). No remedy relies on a bare comment to drive a handoff.
4. An enumerated PM-authority boundary for "unblock" (allowed set + prohibited set as above) is present; no remedy crosses it.
5. The "ask for decision" path is specified: when no in-authority unblock exists, escalate to the human with findings + concrete options, via a human-reaching mechanism (e.g. `pending-human-review` transition or equivalent flagged surface — not a bare comment).
6. The #12460 failed-handoff incident is captured as a worked example: detect halt → classify failed-handoff → unblock by injecting a wake event (and, where a process decision is required, escalate options).
7. Comprehension test (REQUIRED — changes agent instructions): a fresh PM agent given a #12460-shaped scenario (in-progress item, idle owner, unactioned bare-comment merge-ask) produces detect → investigate → wake-event-unblock (or escalate-with-options if a decision is needed) and does NOT propose a bare-comment nudge as the remedy.
8. Composes into PM's deployed `.squidsquad/<pm-alias>/CLAUDE.md` (L2 ⇒ PM role) — verify via `compose.py deploy` for pm, not just source presence.
9. `installer-files.txt` updated only if a new file is added (in-place edit needs no change).

## Notes
- Not a new sub-skill — extend the existing one (DRY).
- Keep the existing noise caps (max nudges/bugs per cycle) but ensure they don't suppress a genuine halt's escalation.
- Refs: comment-handling sub-skill, #12442 (event-mode routing), #12460 (incident), boot-remote-agents sub-skill.

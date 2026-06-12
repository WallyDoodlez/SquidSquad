---
slot: instructions
ordinal: 15
---

## Comment Handling

**Comments are NOT standalone event triggers.** A bare comment on an issue does NOT wake any agent. Comments are absorbed by the next agent that picks up the issue.

This rule is the single most important consequence of the thin-broadcast harness: any wake-up signal must ride a status transition or label change, because those are the only things the harness emits onto the event stream.

### The Rule

When you forge-read an issue (Case B in [[event-mode-contract]], or at task pickup), you read **all comments since you last touched the item**. New information from comments is absorbed as part of that read. You do NOT poll comments otherwise — there is no `comment-added` event in event-mode.

### DM Exception — End-Of-Task Re-Read

DM is the one role that has a sub-task that **spans waiting**: the PR-merge wait. While DM is waiting on a PR to merge, the task is still in flight. Comments arriving during the wait would be silently dropped under the default rule.

DM's exception: at **task completion** (the merge resolves, PR is closed, or the wait ends some other way), DM re-reads issue comments **before** the next pickup. Comments are honored once the wait ends.

**No sub-loop during the wait.** DM does not poll comments while waiting. The reaction window for a comment is "the moment the current wait ends" — typically minutes, sometimes longer.

### Practical Consequences for Senders

- **Urgent agent-to-agent signaling MUST ride a status transition or label change.** A comment alone will not wake anyone. If you need a fast reaction:
  - Transition the issue (e.g. `in-progress → planning`) — this emits a `status-transition` event.
  - Add or remove a label (e.g. `pending-human-review`) — this emits a label-change event.
- **PM nudges and pipeline-sentinel comments** are fine as bare comments — they are absorbed at the next pickup. They are advisory, not blocking.
- **PRs and tracker items** that should bounce back to the previous owner must do so by transition (e.g. verifier reject → `pending-test → in-progress`), not by comment.

### Transition-On-Handoff Rule

When you assign work to a different role (including humans), the assignment MUST be a status transition so it appears on the event stream. Bare comments do not constitute a handoff in event mode. This applies even when the new owner is a human — transition to `pending-human-review` or `pending-human-setup` rather than just commenting "human, please look at this."

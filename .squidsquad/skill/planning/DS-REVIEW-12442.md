I've done a thorough analysis of the diff, tracing every code path through `_check_for_changes` including the fresh-transition vs re-emit branching, the dedup/back-transition interaction, thread-safety under `_emitted_lock`, eviction bounds, and idempotency. Here are my findings:

```
### Finding 1

- **File**: references/scripts/harness.py
- **Line**: 3489
- **Severity**: warning
- **Issue**: The comment in the else-branch incorrectly claims the `if fresh_status and updated_recently` gate "covers both unmapped statuses and comment-bumped re-observations of an already-routed status." It does NOT cover comment bumps — a comment bump preserves the same status, so `fresh_status` is `False`, and the gate does not execute. Comment bumps are correctly silenced by the dedup (`fresh_status=False` → `fresh_transition=False`, and the re-emit timer gates `reemit_due`), but this clause has nothing to do with that. A future maintainer reading the comment may mistakenly believe `mark_emitted` is called on comment bumps, or may try to "fix" a perceived gap that doesn't exist.
- **Evidence**: `fresh_status = not self.is_emitted(issue_num, status)` (line 3463). A comment bump on an issue already at "pending-test" will have `is_emitted(issue_num, "pending-test")` return `True` (the status was recorded on the prior emit), so `fresh_status = False`. The guard `if fresh_status and updated_recently` (line 3490) therefore evaluates to `False`.
- **Suggested fix**: Replace the misleading clause in the comment. For example: `# this covers unmapped statuses (in-progress, planned, etc.) so # back-transitions re-emit later (DS-12342 F1). Comment-bumped # re-observations of already-routed statuses are handled earlier # by the dedup (fresh_status=False prevents both fresh_transition # and this recording clause).`
```

```
NO_FINDINGS (beyond the comment issue above)
```

**Summary of what was verified and found correct:**

1. **Fresh-transition vs re-emit branching**: `fresh_transition` requires `routing is not None AND fresh_status AND updated_recently`. `reemit_due` requires `is_handoff AND not fresh_transition AND _handoff_due()`. The `not fresh_transition` guard prevents double-emit when both conditions could in theory be satisfied. Paths are mutually exclusive.

2. **Dedup/back-transition interaction (DS-REVIEW-12342 Finding 1)**: A `pending-test → in-progress → pending-test` cycle with recent `updatedAt` works correctly — the intermediate `in-progress` is recorded via the else-branch `mark_emitted`, and the re-entry to `pending-test` has `fresh_status=True`, triggering `fresh_transition`. Verified by test `test_status_change_then_reentry_renudges_immediately`.

3. **Thread-safety of `_handoff_emit_at`**: All accesses (read in `_handoff_due`, write in `_mark_handoff_emit`) are serialized under `_emitted_lock`. The TOCTOU between `_handoff_due` and `_mark_handoff_emit` (lock released between check and later write) is benign under the documented single-writer model (only the poller thread writes).

4. **Eviction bound**: Both `_emitted_issues` and `_handoff_emit_at` independently cap at 500 entries using the same pop+reinsert+FIFO-eviction pattern. Eviction of `_handoff_emit_at` while `_emitted_issues` still holds the corresponding entry causes at most one spurious re-emit (idempotent), after which the entry is re-created.

5. **Idempotency/spam-resistance**: The `_HANDOFF_REEMIT_SECONDS = 600` cadence gates re-emits. A fresh transition seeds the timer via `_mark_handoff_emit`, preventing immediate re-emit on the next poll. Worker statuses (`approved`/`open`) never enter the re-emit path (`is_handoff=False`).

6. **Starvation**: The re-emit path deliberately bypasses the `updatedAt > _last_check_epoch` time filter, solving the original starvation where an old-`updatedAt` handoff item was invisible forever. The bounded 600s gap also backstops scenarios where back-transitions occur while the detector is down and intermediate unmapped statuses can't be recorded.
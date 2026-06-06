---
slot: instructions
ordinal: 20
roles: [worker]
---

### Step 2 — Pick Up Work (Deterministic Triage)

Print: `[🦑 HH:MM:SS] Checking work queue...`

**First, check for verifier-rejected items** (highest priority — fix existing before starting new):

```bash
python references/scripts/triage.py qa-rejected [ROLE] --json
```

If the result is non-empty, pick up the first item:
1. Read the full verifier feedback: `gh issue view [NUMBER] --json title,body,comments`
2. Write working state with `Task: #[NUMBER]`, status `in-progress`.
3. Fix each gap identified in the feedback.
4. Re-run tests and smoke tests; capture output: `[ROLE_TEST_CMD] 2>&1 | tee .squidsquad/[ROLE]/test-output-[NUMBER].log`
4b. **Pickup-comment fidelity check** (#9946) — even on the verifier-rejected fast-path. Run `git diff origin/main...HEAD --name-only` and confirm every gap-fix you plan to claim in the transition comment is substantiated by a changed file in the diff. State-file edits (`.squidsquad/`, `.claude/`) are filtered by `commit_code` and never appear in the feature PR — do not claim them as PR deliverables. See the `Pickup-comment fidelity` fragment for full guidance.
5. Transition back to Pending Test:
   ```bash
   python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead
   # Comment text must satisfy Step 4b fidelity check — gap-by-gap mapping to changed files; real pass/fail counts from the captured log.
   python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Fixed [N] verifier gaps: [gap-by-gap list with file references]. Tests: [actual pass/fail counts from test-output log]. Status → Pending Test."
   ```
6. Clear working state. Proceed to Step 4.

**If no verifier-rejected items, use the deterministic work queue**:

```bash
python references/scripts/tracker.py work-queue [ROLE]
```

This returns a unified, priority-sorted list of ALL actionable items (issues AND tasks). Priority order is enforced by the script:
1. In-progress items (resume first)
2. Approved issues — severity:high → medium → low
3. Approved tasks — priority:high → medium → low
4. Open issues — severity:high → medium → low

**You MUST pick the first item in the queue.** No discretion to skip, reorder, or cherry-pick. The queue is deterministic — the script decides priority, not you.

If the queue is empty, print: `[🦑 HH:MM:SS] No actionable work in queue.` and proceed to Step 4.

If the queue returns an item, read it: `gh issue view [NUMBER] --json title,body,labels,comments`

**Design label check**: If the item has a `design:needed` or `design:in-progress` label, skip it and pick the next item in the queue.

**For issues** (type:issue):
1. Write working state: update `.squidsquad/[ROLE]/working-state.md` with `Task: #[NUMBER]`, status `in-progress`.
2. **Branch checkout** (#3296, #9478): `python references/scripts/git_ops.py task-begin [ROLE] [NUMBER]` — checks out the task's feature branch.
3. Transition: `python references/scripts/tracker.py transition [NUMBER] [CURRENT_STATUS] in-progress --role [ROLE]-lead`
4. Comment: `python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Picking up. Status → In Progress."`
5. Read the issue details, locate the relevant code, fix the issue.
6. Run the test command: `[ROLE_TEST_CMD]`
7. **Verify changes exist**: Run `python references/scripts/git_ops.py has-changes`. If output is `false`, do NOT transition — re-read the issue and apply the fix.
7b. **Self-verification reflection** — before marking pending-test, run the same self-review as for tasks (Step 8b in implement-tasks): regression, integration, philosophy, personas checks. Fix any concerns before proceeding.
7b-bis. **Pickup-comment fidelity check** (#9946) — see the `Pickup-comment fidelity` fragment included in this CLAUDE.md, and Step 8b-bis in implement-tasks. Run `git diff origin/main...HEAD --name-only` and a captured test run before drafting the transition comment; every concrete claim must be substantiated. State-file edits (`.squidsquad/`, `.claude/`) are filtered by `commit_code` and never appear in the feature PR — do not claim them as PR deliverables.
7c. **External code review** — run the external review loop (Step 8c in implement-tasks). Stage changes, get changed files, run model review, process findings. Same dispositions apply (fix, file-to-PM, justified-ignore).
8. If tests pass, self-review passes, and changes exist:
   - Transition: `python references/scripts/tracker.py transition [NUMBER] in-progress pending-test --role [ROLE]-lead`
   - Comment: must satisfy Step 7b-bis fidelity check (claims verifiable against the diff and the test log; no state-file deliverables claimed): `python references/scripts/tracker.py comment [NUMBER] --role [ROLE]-lead --message "Fixed in commit [hash]. [File-by-file mapping to issue root cause.] Tests: [actual pass/fail counts from test-output log]. Status → Pending Test."`
   - `python references/scripts/git_ops.py task-end [ROLE] [NUMBER]` — return to working branch.
   - Clear working state.
9. If the root cause belongs to another agent's domain:
   - File a new issue to the correct role.
   - Comment on the original with cross-reference.
   - `python references/scripts/git_ops.py task-end [ROLE] [NUMBER]` — return to working branch.
   - Clear working state.

**For tasks** (type:task): Follow the task implementation flow below (Step 2b).

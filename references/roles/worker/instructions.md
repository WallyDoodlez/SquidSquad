---
slot: instructions
ordinal: 20
roles: [worker]
step-ids: [step:cycle/triage-issues, step:cycle/implement]
---

→ run sub-skill: roles/worker/ralph-loop-overview

### step:cycle/run

→ run sub-skill: cycle-runner

Goal: the cycle's input state has been captured (pull result, context pressure, working-state snapshot, queue state); the agent has aligned its creative work against that input; the cycle's outputs have been staged for durable commit and status propagation.

### step:cycle/context-pressure

→ run sub-skill: context-pressure

Goal: the agent has read the live context-pressure percentage from disk, compared it to the configured threshold, and (above threshold) checkpointed pending work to working-state plus pushed git so a respawn loses nothing. Below threshold this is a no-op and the cycle continues normally.

### step:cycle/resume

→ run sub-skill: resume-working-state

Goal: if a prior session left an active task in `working-state.md`, the agent has resumed it — completed steps, remaining steps, and key decisions trusted as still-current — rather than restarting from a cold tracker pull. If no active task, the cycle proceeds to fresh pickup.

→ run sub-skill: interval-sync

→ run sub-skill: triage-issues

→ run sub-skill: implement-tasks

→ run sub-skill: pickup-comment-fidelity

→ run sub-skill: improvement-scan

→ run sub-skill: vault-remember

→ run sub-skill: vault-optimize

### step:cycle/checkpoint

→ run sub-skill: git-commit

Goal: the cycle's work is durably checkpointed in git — code changes on the feature branch, state changes on the working branch, descriptive commit messages naming the task or issue, pushed if push is configured. Pending Test transitions are gated on this checkpoint.

→ run sub-skill: self-restart

---

<!-- sub-skill: discussion-protocol -->
## Discussion Protocol

- Discussion entries are Issue comments — append-only, never edit or delete.
- Use the tracker script (include alias parenthetical if set in config):
  ```bash
  python references/scripts/tracker.py comment [NUMBER] --role "[ROLE]-lead ($(python references/scripts/config.py alias [ROLE]))" --message "[message]"
  ```
- Use Discussion to communicate with other agents — they will read your entries on their next pull.
- If you need another agent to act, file the bug and note it in Discussion. Do not wait synchronously.
<!-- /sub-skill: discussion-protocol -->

---

→ run sub-skill: tracker-protocol

Use the per-finding-kind one-liners in `tracker-protocol`'s **Creating Issues** section to self-file or cross-file findings (Bug fix / Improvement-scan / Cross-role shapes). `common/issue-filing.md` was retired in #11334 and its body templates absorbed into `tracker-protocol.md`.

---

### step:cycle/cleanup

→ run sub-skill: working-state

Goal: `working-state.md` reflects the cycle's outcome — cleared if a task shipped, updated if work continues — with the last-processed event ID preserved across any clear. The iteration log captures the cycle's summary for institutional memory.

---

→ run sub-skill: vault-protocol

---

<!-- sub-skill: file-conventions -->
## File Conventions

- Your issues and tasks: GitHub Issues with `role:[ROLE]` label (queried via `python references/scripts/tracker.py list-issues/list-tasks`)
- Your iteration logs: `.squidsquad/[ROLE]/iterations/iter-N.md`
- Your working state: `.squidsquad/[ROLE]/working-state.md`
- Your planning artifacts: `.squidsquad/[ROLE]/planning/`
- PM planning artifacts (RESEARCH.md, CONTEXT.md): `.squidsquad/[PM_ALIAS]/planning/` — under the #9184 workflow PM no longer produces TEST-PLAN.md
- Verifier planning artifacts (TEST-PLAN-<NUMBER>.md, QA-RESULTS-<NUMBER>.md, TEST-<NUMBER>-tests.py): `.squidsquad/[VERIFIER_ALIAS]/planning/` (#9184)
- Config (read-only except ship counter): `.squidsquad/config.md`
- Cross-filing: create GitHub Issues with `role:[OTHER_ROLE]` label
<!-- /sub-skill: file-conventions -->

---

<!-- sub-skill: status-line -->
## Status Line

A status line is shown at the bottom of your Claude Code session. It displays:

- `🦑` (green) — you are active
- Your role label and current iteration number
- Backlog pulse: count of open bugs + actionable features (e.g. `2 bugs 1 feat`)
- Time since your last completed cycle (shows ⏰ overdue indicator when cycle exceeds iteration interval)

The status line updates automatically after each assistant message. No action is required from you — it reads from your iteration logs and tracker files.
<!-- /sub-skill: status-line -->

---

<!-- sub-skill: prohibitions -->
## What You Must Never Do

- Never implement a task with status `Pending` — it has not been approved by a human yet.
- Never edit another agent's Discussion comments on GitHub Issues.
- Never push without pulling first.
- Never skip the test step before marking an issue Fixed or a task Pending Test.
- Never delete GitHub Issue comments.
- After any status change, use `python references/scripts/tracker.py transition` (see Tracker Protocol). Never construct `gh issue edit` label commands manually.
- Never run `gh issue close` directly. Issues are only closed via `tracker.py transition ... pending-ship shipped` which auto-closes. Direct close bypasses status transitions and leaves stale labels.
- Shipped transitions auto-close the Issue via tracker.py.
- Never mark Pending Test without running the full test suite and confirming all tests pass.
- Never mark Pending Test for new code without corresponding unit tests. Tests are part of the implementation, not follow-up work.
- Never proceed with ambiguous or incomplete context. If PM's comments reference planning artifacts (RESEARCH.md, CONTEXT.md, TEST-PLAN.md) you cannot find, or if the described scope clearly exceeds what you understand from the issue body alone, **stop and push back** — comment on the issue asking for clarification or alignment before implementing. Guessing wastes cycles and produces wrong output.
- **Never edit `.squidsquad/*/CLAUDE.md` directly.** These are composed output files generated by `compose.py deploy`. Always edit the **source** files in `references/sub-skills/` or `references/roles/`, then run `compose.py deploy [role]` to regenerate. Direct edits to composed files are lost on the next recompose.
<!-- /sub-skill: prohibitions -->

---

### insert-after step:cycle/resume

#### step:cycle/triage-issues

→ run sub-skill: triage-issues

Scan this role's open issues for bug reports. For each: investigate root cause, determine if it's in this domain, file cross-domain if not. Bugs are auto-approved; pick up immediately.

### append

#### step:cycle/implement

→ run sub-skill: implement-tasks

Implement the current approved task or bug fix. Write code, write unit tests, run full test suite. Confirm all ACs are observable. Transition to pending-test only when tests are green and every AC has evidence.

→ run sub-skill: git-commit

Commit with descriptive message referencing the issue number and short description.


## Reactive sub-skills

These sub-skills are invoked reactively when their trigger condition appears in conversation, not as part of the regular cycle.

### Project customization (project-specific durable directives)

→ run sub-skill: l4-curation

When the human gives a project-specific durable customization directive (e.g. "from now on, before X do Y"; "in this project, never Z"), invoke `l4-curation` BEFORE doing any implementation work. The sub-skill handles the elicitation dialog, the decision tree (replace / insert-before / insert-after / append), the three safety gates (DeepSeek audit + mini-CQ + compose dry-run), and the project-customization commit. One-off requests and feature requests are explicitly NOT routed through `l4-curation` — see the sub-skill itself for the durable vs one-off vs feature-request triage.

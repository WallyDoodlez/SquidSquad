# TEST-PLAN-13666

Derived independently from the issue body (`ISSUE: task-intake.md doesn't ensure CONTEXT.md is committed+pushed before Approved, so same-session worker pickup can race ahead of it`). Filed by pm-lead after directly hitting this race live during #13563's own intake (which I verified earlier this session) — PM caught and manually fixed it in the moment, then filed this issue for the durable process fix.

## ACs derived from the issue

- **AC1**: `task-intake.md` Phase 2 explicitly commits+pushes CONTEXT.md immediately after writing it, not relying on the end-of-cycle mechanical wrapper.
- **AC2**: `task-approval.md`'s pre-approval sync check (step 6) hard-gates the `planned→approved` transition on `git log origin/main -- <CONTEXT path>` confirming the artifact is actually pushed — a hard gate, not just a should-do note, so the race is caught even if AC1's step is skipped in a future session.
- **AC3 (CQ, verifier-owned)**: This is an LLM-consumed PM sub-skill change (`task-intake.md`/`task-approval.md`) — skill's own PR body explicitly defers CQ authorship to the verifier (type:issue fix, #13551 precedent). Independently authored, not reused from the worker.
- **AC4**: No regressions — new tests pass; full static gate passes; comprehension staleness clean (incl. reviewing `9184_spec.json`'s drift, which also names `task-intake.md`).

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 | `test_explicit_commit_step_present` + `test_commit_step_placed_right_after_context_written` — direct source read confirms the `git add`/`commit`/`push` block sits between the CONTEXT.md template and the "Open in editor" step |
| TC2 | AC2 | `test_origin_main_check_present` + `test_check_is_inside_pre_approval_sync_step` — confirms the `git log origin/main` check is a sub-step of step 6, and step 7's approval gate explicitly references it |
| TC3 | AC3 (independent CQ) | Authored `tests/comprehension/13666_spec.json` independently. Spawned a fresh sonnet `general-purpose` subagent given ONLY `task-intake.md` + `task-approval.md`, no other file/tool/prior knowledge; graded 4 questions |
| TC4 | AC4 | `tests/test_13666_context_commit_push_race.py` (7 cases). Reviewed `9184_spec.json`'s drift (also names `task-intake.md`): confirmed #13666's change is purely additive (a new commit-immediately instruction) and doesn't touch any of 9184's 7 tested facts (artifact ownership, TEST-PLAN path precedence, CQ ownership) — drift-only, refreshed. `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |

## Note
This issue documents a process gap I effectively benefited from PM already catching and fixing live during #13563's own intake — verifying the durable fix closes the class, not just the one instance.

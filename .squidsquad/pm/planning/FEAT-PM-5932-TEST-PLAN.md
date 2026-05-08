# FEAT-PM-5932 Test Plan — L2 External Code Review Loop Before Pending-Test

## Comprehension Questions

These questions must be answerable by a fresh agent reading only the modified files
(`implement-tasks.md`, `model_router.py`, and the new `code-review.md.j2` prompt
template). They are the comprehension gate before QA can mark this task pending-ship.

### CQ-1: What does the dev agent do when it receives code review findings?

- **Files**: `references/sub-skills/roles/dev/implement-tasks.md`
- **Expected**: The dev agent must disposition every finding before proceeding. Each
  finding must be marked as one of three outcomes: fix (apply the change), file-to-PM
  (create a tracked issue for PM triage), or justified-ignore (document why the finding
  is not applicable). Un-dispositioned findings block transition to pending-test. After
  all findings are dispositioned, the dev re-runs the external review. The loop continues
  until either the review produces zero findings or the 5-iteration cap is reached.

### CQ-2: What happens when a finding is dispositioned as file-to-PM?

- **Files**: `references/sub-skills/roles/dev/implement-tasks.md`
- **Expected**: The dev agent creates a new GitHub Issue via `tracker.py create-issue`
  routed to PM for triage. The review loop then PAUSES — the dev does not proceed to
  the next iteration until PM acknowledges receipt of the filed issue (PM comments on
  the issue or transitions it out of `pending` status). Once PM acknowledges, the dev
  resumes the loop. The file-to-PM disposition counts as addressed for loop-exit
  purposes once PM acknowledges; the dev does not wait for the issue to be resolved.

### CQ-3: What happens at the 5-iteration cap with unresolved findings?

- **Files**: `references/sub-skills/roles/dev/implement-tasks.md`
- **Expected**: When the loop reaches iteration 5 and findings remain unresolved (not
  yet dispositioned as fix/file-to-PM/justified-ignore, or re-review still produces
  findings after dispositions), the dev transitions to pending-test anyway. The dev
  posts a PR comment listing all unresolved findings verbatim and notes "review cap
  reached — QA to decide." QA then determines whether to reject back to in-progress
  or accept with noted gaps. The cap is a safety valve, not a failure state.

### CQ-4: How does the dev agent know which model to use for code review?

- **Files**: `references/scripts/model_router.py`, `.squidsquad/config.md`
- **Expected**: The dev agent calls `python references/scripts/model_router.py
  code-review --task-id [N] --input-files [changed-files] --output-file [path]
  --context [ACs + philosophy]`. `model_router.py` reads `## Model Routing` in
  `config.md`, looks for `- **Code Review Model**: <value>`, lowercases and
  hyphenates the key to `code-review-model`, and returns that model. If the key is
  absent, `get_model_for_task` falls through to `routing.get("default-model",
  "claude")` and returns `claude`. If the resolved model is `claude` or no external
  provider is available, model_router exits 1 and the dev spawns a Claude subagent
  via the Agent tool instead.

---

## Test Cases

### TC-1: model_router code-review task type — config parsing happy path

- **Precondition**: `.squidsquad/config.md` contains a `## Model Routing` section with
  `- **Code Review Model**: deepseek-v4-pro`. A valid provider manifest exists for
  `deepseek-v4-pro` in `references/scripts/providers/`.
- **Steps**:
  1. Call `get_model_for_task("code-review")` directly in Python or via CLI
     `python references/scripts/model_router.py code-review --task-id TC1 --input-files "" --output-file /tmp/out.md --context "test"`.
  2. Capture the resolved model name from the router's internal logic
     (or from the diagnostic log entry written to `.squidsquad/diagnostics/model-routing.log`).
- **Expected**: The router resolves model `deepseek-v4-pro`. The config key
  `Code Review Model` is normalized to `code-review-model` by `_parse_model_routing`
  (lowercased, spaces replaced with hyphens). `key_map.get("code-review", "code-review-model")`
  returns `code-review-model`, and `routing.get("code-review-model")` returns `deepseek-v4-pro`.
- **Verification**: Inspect `_parse_model_routing` output dict — assert `"code-review-model"
  in result` and `result["code-review-model"] == "deepseek-v4-pro"`. Diagnostic log entry
  action is `success` (not `delegate-to-agent-tool`).

---

### TC-2: model_router code-review task type — no config key falls through to claude

- **Precondition**: `.squidsquad/config.md` has a `## Model Routing` section but does NOT
  contain a `Code Review Model` key. No `default-model` key is set either.
- **Steps**:
  1. Call `get_model_for_task("code-review")`.
- **Expected**: The function returns `"claude"` (the hardcoded fallback in
  `routing.get(key, routing.get("default-model", "claude"))`). No exception raised.
  Backward-compatible — existing installs without the new key behave identically to
  current behavior.
- **Verification**: Assert return value is `"claude"`. Assert `route()` exits with code 1
  (delegate-to-agent-tool) without attempting any external API call. Diagnostic log entry
  shows `action: delegate-to-agent-tool`.

---

### TC-3: model_router code-review task type — prompt template loaded

- **Precondition**: `references/prompts/code-review.md.j2` exists and contains
  `{{ context }}`, `{{ task_id }}`, and `{{ file_contents }}` template variables.
- **Steps**:
  1. Call `assemble_prompt("code-review", "5932", "some/file.py", "Review against ACs")`
     (or equivalent via `_load_prompt_template("code-review")`).
- **Expected**: `_load_prompt_template("code-review")` returns the template content
  (non-None). `assemble_prompt` substitutes all three variables. The assembled prompt
  contains the AC context and file contents. The prompt does NOT contain unfilled
  `{{ }}` placeholders.
- **Verification**: Assert `_load_prompt_template("code-review")` is not None. Assert the
  returned prompt string contains `"Review against ACs"` and `"some/file.py"`.
  Assert `"{{" not in assembled_prompt`.

---

### TC-4: model_router code-review task type — NOT in CLAUDE_LOCKED_TASKS

- **Precondition**: `model_router.py` source is readable.
- **Steps**:
  1. Read `CLAUDE_LOCKED_TASKS` set from `model_router.py` (line ~49).
  2. Verify `"code-review"` is not present.
- **Expected**: `CLAUDE_LOCKED_TASKS` contains only `{"comprehension", "qa-execution"}`.
  `"code-review"` is absent — external model override is permitted for code review.
- **Verification**: Assert `"code-review" not in CLAUDE_LOCKED_TASKS`. Assert
  `get_model_for_task("code-review")` does NOT immediately return `"claude"` due to the
  locked-task guard (it may still return `"claude"` via config fallback, but not via the
  lock).

---

### TC-5: model_router code-review task type — CLI alias registered

- **Precondition**: `model_router.py` is the current version (post-implementation).
- **Steps**:
  1. Run `python references/scripts/model_router.py --help`.
  2. Run `python references/scripts/model_router.py code-review --help`.
- **Expected**: `code-review` appears as a valid subcommand in the help output.
  The `--task-id`, `--input-files`, `--output-file`, and `--context` flags are listed.
  `code-review` also appears in the `aliases` list of the route subparser (alongside
  `research`, `discussion-prep`, `test-plan`, etc.).
- **Verification**: Exit code is 0 for both help calls. `"code-review"` is present in the
  help text. The `choices` list in `route_parser` includes `"code-review"`.

---

### TC-6: Review loop mechanics — run, findings, disposition, re-run, exit when clean

- **Precondition**: Dev agent is at step 9b (self-verification complete). A task branch
  is checked out with 2 modified Python files. `Code Review Model` is set to an external
  model. The external model returns 2 findings on iteration 1, then 0 findings on
  iteration 2 (after dev fixes iteration-1 findings).
- **Steps**:
  1. Dev runs `git diff --name-only HEAD` — captures list of changed files.
  2. Dev runs `python references/scripts/model_router.py code-review --task-id [N]
     --input-files [changed-files] --output-file [path] --context [ACs + philosophy]`.
  3. Dev reads output file, identifies 2 findings.
  4. Dev dispositions both findings as `fix` and applies the changes.
  5. Dev re-runs model_router for iteration 2.
  6. External model returns 0 findings.
  7. Dev posts dispositions as a PR comment.
  8. Dev transitions task to pending-test.
- **Expected**: Loop exits after 2 iterations (clean). Iteration count is 2 (< 5 cap).
  Dispositions are posted to the PR as a comment before transitioning. The PR comment
  contains both iteration-1 findings and their `fix` disposition.
- **Verification**: PR has a comment from the dev agent listing findings + dispositions.
  Task status transitions to `pending-test`. No `review-cap-reached` note in the comment
  (cap was not hit).

---

### TC-7: Review loop mechanics — exit when clean on iteration 1 (zero findings)

- **Precondition**: Dev agent at step 9b. Changed files contain no issues relative to
  ACs/philosophy. External model returns 0 findings on first run.
- **Steps**:
  1. Dev runs model_router for code-review (iteration 1).
  2. Output file contains zero findings.
  3. Dev posts dispositions PR comment noting "0 findings — no dispositions required."
  4. Dev transitions to pending-test.
- **Expected**: Loop exits after exactly 1 iteration. Transition to pending-test proceeds
  normally. No loop state is left open.
- **Verification**: Task reaches `pending-test` in one step. PR comment notes zero findings.
  Working-state.md `## Code Review Dispositions` section is populated with iteration 1
  result.

---

### TC-8: Disposition tracking — PR comment posted with all findings addressed

- **Precondition**: 3 findings returned by external model. Dev dispositions them:
  finding-1 as `fix`, finding-2 as `justified-ignore`, finding-3 as `file-to-PM`.
  PM acknowledges finding-3 (comments on the filed issue).
- **Steps**:
  1. Dev files a new issue for finding-3 via `tracker.py create-issue`.
  2. Loop pauses — dev waits for PM acknowledgment.
  3. PM comments on the filed issue.
  4. Dev resumes loop, posts PR comment with all 3 dispositions.
  5. Dev re-runs review.
- **Expected**: PR comment contains a structured entry for each of the 3 findings:
  - Finding-1: `fix — [description of fix applied]`
  - Finding-2: `justified-ignore — [documented rationale]`
  - Finding-3: `file-to-PM — #[ISSUE_NUMBER] filed, PM acknowledged`
  All 3 are addressed. Re-run triggers as expected. PR comment is posted before the
  re-run, not only at transition.
- **Verification**: PR comment is present on the task's PR with 3 entries, one per
  finding. `file-to-PM` entry includes the issue number. Working-state.md
  `## Code Review Dispositions` mirrors the PR comment content.

---

### TC-9: File-to-PM pause — loop blocks until PM acknowledges

- **Precondition**: External model returns a finding that dev dispositions as `file-to-PM`.
  PM has NOT yet acknowledged the filed issue.
- **Steps**:
  1. Dev files issue to PM via `tracker.py create-issue`.
  2. Dev does NOT proceed to re-run the external model.
  3. Dev writes working-state.md with status `paused — awaiting PM ack on #[N]`.
  4. PM acknowledges (comments on the filed issue or transitions it to `planning`/`in-progress`).
  5. Dev reads the acknowledgment signal.
  6. Dev resumes the loop — re-runs model_router for the next iteration.
- **Expected**: Between steps 2 and 4, the loop is blocked. The dev agent does not
  increment the iteration counter, does not re-run the external model, and does not
  transition to pending-test. Working-state.md reflects the pause reason and the issue
  number being waited on. Once PM acknowledges, loop resumes in the next dev cycle.
- **Verification**: Working-state.md contains `paused` status referencing the issue
  number. Iteration counter has not advanced past the pause point. After PM comments
  on the issue, the next dev loop cycle resumes from the paused state and re-runs
  model_router.

---

### TC-10: Loop cap — 5 iterations, then transition with noted findings

- **Precondition**: External model persistently returns 1 unresolved finding across all
  iterations. Dev dispositions each iteration's finding as `fix` but re-review continues
  to surface it (or a new finding). No clean run achieved in 5 iterations.
- **Steps**:
  1. Iteration 1: finding returned, dev dispositions as `fix`.
  2. Iteration 2: finding returned, dev dispositions as `fix`.
  3. Iteration 3: finding returned, dev dispositions as `fix`.
  4. Iteration 4: finding returned, dev dispositions as `fix`.
  5. Iteration 5: finding returned. Dev notes cap reached.
  6. Dev posts PR comment: all findings from iteration 5 listed verbatim + "review cap
     reached — QA to decide."
  7. Dev transitions to pending-test.
- **Expected**: Loop terminates at iteration 5. Dev does NOT run a 6th iteration. Dev
  DOES transition to pending-test (not stuck in-progress). PR comment contains the
  unresolved findings and the cap-reached note. Transition comment on the issue notes
  "Implementation complete. External code review cap reached — [N] findings noted for QA."
- **Verification**: PR has a comment with unresolved findings + "review cap reached."
  Issue has a tracker comment noting cap. Task status is `pending-test`. Iteration count
  in working-state.md shows 5.

---

### TC-11: Fallback when external model unavailable — no API key

- **Precondition**: `Code Review Model` is set to `deepseek-v4-pro` in config.md.
  `DEEPSEEK_API_KEY` is NOT set (neither in environment nor `~/.squidsquad/secrets`).
- **Steps**:
  1. Dev runs `python references/scripts/model_router.py code-review --task-id [N]
     --input-files [files] --output-file [path] --context [context]`.
  2. Capture exit code.
  3. Dev handles non-zero exit code per implement-tasks.md instructions.
- **Expected**: model_router prints `[model_router] DEEPSEEK_API_KEY not set ... falling
  back to Claude for code-review.` to stderr. Exit code is 2. Dev agent detects exit
  code 2 and spawns a Claude subagent via the Agent tool with the same code review prompt.
  The review loop continues using Claude — the dev does NOT skip the review step.
- **Verification**: model_router stderr contains the fallback message. Exit code is 2.
  Dev agent's next action is to invoke Agent tool (not skip to pending-test). The code
  review still runs with Claude and produces findings that must be dispositioned.

---

### TC-12: Fallback when external model unavailable — API error during call

- **Precondition**: `Code Review Model` is set to `deepseek-v4-pro`. API key IS set but
  the API returns a non-quota error (e.g., 500 server error, connection refused).
- **Steps**:
  1. Dev runs model_router code-review.
  2. Provider adapter raises an exception.
- **Expected**: model_router catches the exception, logs to diagnostic log with
  `action: api-error`, prints `[model_router] API error: [message]. Falling back to
  Claude.` to stderr, exits with code 1. Dev falls back to Claude Agent tool.
  Review loop continues.
- **Verification**: Exit code is 1. Diagnostic log entry has `action: api-error`.
  Dev continues review using Claude Agent tool fallback (does not abort).

---

### TC-13: Git diff scope — HEAD, not staged-only

- **Precondition**: Dev has modified 3 files. 2 are staged (`git add`), 1 is modified
  but not staged. Dev has NOT committed yet.
- **Steps**:
  1. Dev runs `git diff --name-only HEAD` to determine changed files.
  2. Dev passes the result as `--input-files` to model_router.
- **Expected**: All 3 modified files appear in the changed-files list — both staged and
  unstaged changes relative to HEAD. The review is NOT limited to `git diff --cached`
  (staged only). The implement-tasks.md step instructs `git add -A` before the first
  review so all changes are in the working tree and captured by `git diff --name-only HEAD`.
- **Verification**: The `--input-files` parameter passed to model_router includes all 3
  modified files (2 staged + 1 unstaged after the `git add -A` step). Running
  `git diff --name-only HEAD` locally returns all 3 files. Running `git diff --cached
  --name-only` would return only the 2 staged files — this is the wrong command and
  must NOT be used.

---

### TC-14: Escalation when >50% justified-ignore across 3+ reviews

- **Precondition**: Dev is on iteration 3. Across iterations 1, 2, and 3, the justified-
  ignore count exceeds 50% of all findings (e.g., iteration 1: 3 findings, 2
  justified-ignore; iteration 2: 4 findings, 3 justified-ignore; iteration 3: 2
  findings, 2 justified-ignore — 7/9 = 78% justified-ignore).
- **Steps**:
  1. Dev tracks the running justified-ignore ratio across iterations.
  2. After iteration 3, dev detects ratio > 50%.
  3. Dev escalates to human (PM or human check-in).
- **Expected**: Dev does NOT silently continue iterating. Dev posts a comment on the
  task issue: "Warning: >50% of findings across 3+ review iterations have been
  justified-ignore. The code review model or prompt may need tuning. Escalating to PM."
  Dev also comments on the PR. The loop continues (it is not aborted), but the human
  is informed so they can assess whether the model is producing noise.
- **Verification**: Issue has a comment from dev-lead noting the justified-ignore ratio
  and escalating. The ratio threshold check fires at iteration 3 (not iteration 1 or 2).
  The loop continues past the escalation — it is informational, not a hard stop.

---

### TC-15: implement-tasks.md step ordering — new step between 9b and 10

- **Precondition**: `references/sub-skills/roles/dev/implement-tasks.md` is the post-
  implementation version.
- **Steps**:
  1. Read `implement-tasks.md` and enumerate all numbered steps.
  2. Find step 9b (self-verification reflection).
  3. Find the new external code review step.
  4. Find step 10 (pending-test transition).
- **Expected**: The external code review step exists as a new numbered step between 9b
  and 10. Step 9b remains unchanged (self-review still runs). The new step instructs
  the dev to: (a) run `git add -A`, (b) run `git diff --name-only HEAD` to capture
  changed files, (c) invoke `python references/scripts/model_router.py code-review
  [flags]`, (d) disposition all findings, (e) post PR comment with dispositions, (f)
  loop until clean or 5-iteration cap. Step 10 (pending-test) is renumbered if
  necessary but its content is unchanged. The distinction between step 9b (self-review)
  and the new external review step is documented in implement-tasks.md.
- **Verification**: Step ordering in implement-tasks.md is: ... → 9b → [new code
  review step] → 10. The new step contains the exact `model_router.py code-review`
  invocation command. Step 10 still references `pending-test` transition.

---

### TC-16: Backward compatibility — no Code Review Model in config falls through to claude

- **Precondition**: `.squidsquad/config.md` exists and has a `## Model Routing` section
  but does NOT include a `Code Review Model` key. This simulates an existing install
  that has not been upgraded.
- **Steps**:
  1. Call `get_model_for_task("code-review")` or run the full model_router code-review
     command.
  2. Observe behavior.
- **Expected**: No error, no crash, no warning printed to stdout. `get_model_for_task`
  returns `"claude"`. The dev agent falls back to Claude Agent tool for code review.
  The review step still executes — it just uses Claude instead of an external model.
  Zero behavior change vs. a pre-5932 install (review step is new, but model is Claude,
  same as if the step was always there).
- **Verification**: `get_model_for_task("code-review")` returns `"claude"`. model_router
  exits 1 (delegate-to-agent-tool). No `KeyError` or `AttributeError` in model_router.
  Existing `tests/test_model_router.py` test coverage for `_parse_model_routing` on a
  config without the new key passes (no regression).

---

### TC-17: justified-ignore is a valid, explicitly documented disposition

- **Precondition**: `references/sub-skills/roles/dev/implement-tasks.md` is the post-
  implementation version.
- **Steps**:
  1. Read the new external code review step in implement-tasks.md.
  2. Search for the word `justified-ignore` or equivalent text.
- **Expected**: `justified-ignore` is listed as an explicit, named disposition type.
  The step text makes clear it is a valid, non-shameful outcome — not an exception or
  escape hatch. The documentation must not frame it as "if you really must" or add
  caveats that discourage legitimate use. The rationale field is required but the
  disposition itself is fully supported.
- **Verification**: `grep -i "justified" references/sub-skills/roles/dev/implement-tasks.md`
  returns at least one match. The surrounding text lists `justified-ignore` alongside
  `fix` and `file-to-PM` as co-equal dispositions.

---

## Smoke Tests

- [ ] `python references/scripts/model_router.py code-review --help` exits 0 and shows
  `code-review` as a valid subcommand.
- [ ] `get_model_for_task("code-review")` returns `"claude"` when config.md has no
  `Code Review Model` key (no exception).
- [ ] `get_model_for_task("code-review")` returns the configured model when config.md
  has `- **Code Review Model**: deepseek-v4-pro`.
- [ ] `"code-review"` is NOT in `CLAUDE_LOCKED_TASKS`.
- [ ] `_load_prompt_template("code-review")` returns non-None after `code-review.md.j2`
  is added to `references/prompts/`.
- [ ] `implement-tasks.md` contains the literal string `model_router.py code-review` in
  the new step.
- [ ] `implement-tasks.md` contains the literal string `justified-ignore`.
- [ ] `implement-tasks.md` contains the literal string `git diff --name-only HEAD`.
- [ ] Existing `tests/test_model_router.py` suite passes with no regressions:
  `python -m pytest tests/test_model_router.py -v`.

---

## Regression Risks

- **model_router.py existing task types**: Adding `code-review` to `key_map` and CLI
  `aliases`/`choices` must not change the behavior of `research`, `discussion-prep`,
  `test-plan`, `improvement-scan`, `qa-execution`, or `comprehension`. Run the full
  test suite to confirm.
- **CLAUDE_LOCKED_TASKS guard**: `code-review` must remain outside this set. If it is
  accidentally added, all external model routing silently becomes Claude — the feature
  ships but does nothing new.
- **implement-tasks.md step numbering**: Inserting a step between 9b and 10 must not
  break references to step numbers in other templates, vault notes, or documentation.
  Audit for cross-references before renumbering.
- **`_parse_model_routing` regex**: The existing regex `r"-\s*\*\*(.+?)\*\*:\s*(.+)"`
  must correctly parse `- **Code Review Model**: deepseek-v4-pro`. The key normalization
  (lowercase + hyphen) must produce `code-review-model`. Confirm with a unit test.
- **`assemble_prompt` fallback path**: If `code-review.md.j2` is missing (deploy error),
  `assemble_prompt` falls back to a generic prompt. This is safe but degrades review
  quality. The fallback must not crash. Add a smoke test verifying the template exists
  post-deploy.
- **Loop pause on file-to-PM**: If PM never acknowledges a filed issue (PM is down or
  absent), the dev loop is permanently paused. The implement-tasks.md step should specify
  a timeout — if PM has not acknowledged within N cycles, dev escalates to human and
  continues the loop (counting the finding as addressed-pending). Verify this timeout
  behavior is documented.

# FEAT-PM-6126 Test Plan — Harness Owns PR Merge + Compose

## Test Cases

### TC-1: POST /merge endpoint exists and returns 202 Accepted

- **Precondition**: Harness running on port 7373. A valid open PR exists (e.g. PR #42).
- **Steps**:
  1. `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": 42, "branch": "squidsquad/skill/42", "role": "qa"}'`
- **Expected**: HTTP 202 Accepted. Response body contains `status` field (e.g. `"accepted"` or `"merging"`). Response does NOT contain final merge outcome.
- **Verification**: `curl` exit 0, status code is exactly `202`. Response JSON parseable and contains no `success` field with final result (merge is async).

---

### TC-2: Merge succeeds — pr-merged event emitted with full payload

- **Precondition**: Harness running. A valid open PR exists targeting main. No merge conflicts.
- **Steps**:
  1. Record current event stream cursor: `curl -s http://localhost:7373/events?limit=1 | python -c "import sys,json; e=json.load(sys.stdin)['events']; print(e[-1]['id'] if e else '')" > /tmp/cursor.txt`
  2. POST to `/merge`: `curl -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": 42, "branch": "squidsquad/skill/42", "role": "qa"}'`
  3. Wait up to 30 seconds for `pr-merged` event to appear: poll `GET /events?since=<cursor>&event_type=pr-merged`
- **Expected**: A `pr-merged` event appears with payload containing all four required fields: `pr_number` (integer), `branch` (string, the head ref), `issue_number` (integer, parsed from branch), `files_changed` (list of file paths). Payload also contains `success: true`.
- **Verification**: `curl -s "http://localhost:7373/events?event_type=pr-merged&limit=5"` returns an event where `payload.pr_number == 42`, `payload.branch == "squidsquad/skill/42"`, `payload.issue_number == 42`, `payload.files_changed` is a non-null list, `payload.success == true`.

---

### TC-3: Merge with references/ changes — compose-completed event also emitted

- **Precondition**: Harness running. A valid open PR exists that includes at least one file under `references/` (e.g. a template edit). Confirm with `gh pr view <N> --json files`.
- **Steps**:
  1. Record cursor (same as TC-2 step 1).
  2. POST to `/merge` with the PR number.
  3. Wait for `pr-merged` event (up to 30s).
  4. After `pr-merged`, wait for `compose-completed` event (up to 60s — compose can be slow): poll `GET /events?since=<cursor>&event_type=compose-completed`.
- **Expected**: Both events appear in order (`pr-merged` before `compose-completed`). `compose-completed` payload contains `success: true`.
- **Verification**: Query `GET /events?event_type=pr-merged,compose-completed&since=<cursor>`. Confirm two distinct events with `event_type` values `pr-merged` and `compose-completed`, in that order, and both have `success: true`.

---

### TC-4: Merge without references/ changes — only pr-merged emitted, no compose-completed

- **Precondition**: Harness running. A valid open PR exists whose changed files are entirely outside `references/` (e.g. only `.squidsquad/` state files or test files). Confirm with `gh pr view <N> --json files`.
- **Steps**:
  1. Record cursor.
  2. POST to `/merge` with the PR number.
  3. Wait for `pr-merged` event (up to 30s).
  4. Wait an additional 30 seconds.
  5. Query events for `compose-completed` since cursor.
- **Expected**: `pr-merged` event appears with `success: true`. No `compose-completed` event appears within the additional 30-second window.
- **Verification**: `curl -s "http://localhost:7373/events?event_type=compose-completed&since=<cursor>"` returns empty `events` array. `pr-merged` event present with correct payload.

---

### TC-5: Merge conflict — pr-merged emitted with success:false and error details

- **Precondition**: Harness running. An open PR exists that has a merge conflict (e.g. same line edited on both PR branch and main since PR was opened). Confirm `gh pr view <N> --json mergeable` returns `CONFLICTING`.
- **Steps**:
  1. Record cursor.
  2. POST to `/merge` with the conflicting PR number.
  3. Wait up to 30s for `pr-merged` event.
- **Expected**: `pr-merged` event appears with `success: false` and an `error` field containing a description (e.g. `"merge conflict"`). No `compose-completed` event is emitted. HTTP response to the POST was still 202 (the async contract is honoured even for failures).
- **Verification**: `pr-merged` event has `payload.success == false`, `payload.error` is non-empty string. No `compose-completed` event appears within 30s of the `pr-merged` event.

---

### TC-6: PR already merged — pr-merged emitted with already_merged:true

- **Precondition**: Harness running. A PR that was previously merged (state = MERGED) is used. Record its number.
- **Steps**:
  1. Record cursor.
  2. POST to `/merge` with the already-merged PR number.
  3. Wait up to 30s for `pr-merged` event.
- **Expected**: HTTP 202 from POST. `pr-merged` event appears with `payload.already_merged == true` and `payload.success == true` (the merge was successful — it just happened earlier). No `compose-completed` event (no new merge = no new compose needed).
- **Verification**: `pr-merged` event payload has `already_merged: true`. No `compose-completed` in the next 30s.

---

### TC-7: PR doesn't exist — error response

- **Precondition**: Harness running. Use a PR number that does not exist (e.g. 99999).
- **Steps**:
  1. `curl -s -w "\n%{http_code}" -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": 99999, "branch": "squidsquad/skill/99999", "role": "qa"}'`
- **Expected**: Either a synchronous error response (4xx) or a 202 followed by a `pr-merged` event with `success: false` and an error describing that the PR was not found. The endpoint must not hang or return 500 silently.
- **Verification**: Response HTTP code is either 4xx (synchronous validation) or 202 with subsequent `pr-merged` event containing `payload.success == false` and `payload.error` referencing a not-found or merge-failed condition. No `compose-completed` emitted.

---

### TC-8: Compose failure — pr-merged still emitted, compose-completed with success:false

- **Precondition**: Harness running. A PR that touches `references/` is ready to merge. Temporarily break `compose.py deploy-all` so it exits non-zero (e.g. rename a mandatory role sub-skill file). Record the PR number.
- **Steps**:
  1. Break compose (rename `references/sub-skills/roles/pm/instructions.md` → `instructions.md.bak`).
  2. Record cursor.
  3. POST to `/merge` with the PR number.
  4. Wait up to 30s for `pr-merged` event.
  5. Wait up to 60s for `compose-completed` event.
  6. Restore the renamed file.
- **Expected**: `pr-merged` event appears with `success: true` (the merge itself succeeded). `compose-completed` event appears with `success: false` and an `error` field containing compose failure details. The merge is NOT rolled back.
- **Verification**: Two events appear. `pr-merged.payload.success == true`. `compose-completed.payload.success == false`. `compose-completed.payload.error` is non-empty. Git log shows the merge commit exists on main (merge was not rolled back).

---

### TC-9: QA template updated — pr-merge CLI calls replaced with POST /merge

- **Precondition**: Access to `references/sub-skills/roles/qa/verification.md`.
- **Steps**:
  1. Read `references/sub-skills/roles/qa/verification.md`.
  2. Search for any remaining `git_ops.py pr-merge` or `git_ops.py pr-merge` CLI invocations.
  3. Search for `curl.*POST.*merge` or `POST /merge` to confirm replacements exist.
- **Expected**: Zero occurrences of `git_ops.py pr-merge` in `verification.md`. At least 3 occurrences of `POST /merge` (replacing the 3 call sites at lines 230, 256, 268 from research). The merge conflict resolution section (lines 259–277) remains intact — QA still handles conflict resolution, just re-requests via REST after resolving.
- **Verification**: `grep -c "git_ops.py pr-merge" references/sub-skills/roles/qa/verification.md` returns 0. `grep -c "POST.*merge\|/merge" references/sub-skills/roles/qa/verification.md` returns >= 3.

---

### TC-10: DM template updated — pr-merge CLI call replaced with POST /merge

- **Precondition**: Access to `references/sub-skills/roles/dm/delivery-packaging.md`.
- **Steps**:
  1. Read `references/sub-skills/roles/dm/delivery-packaging.md`.
  2. Search for `git_ops.py pr-merge` CLI invocations.
  3. Search for `curl.*POST.*merge` or `POST /merge`.
- **Expected**: Zero occurrences of `git_ops.py pr-merge` in `delivery-packaging.md`. At least 1 occurrence of `POST /merge` replacing the original call at line 48.
- **Verification**: `grep -c "git_ops.py pr-merge" references/sub-skills/roles/dm/delivery-packaging.md` returns 0. `grep -c "POST.*merge\|/merge" references/sub-skills/roles/dm/delivery-packaging.md` returns >= 1.

---

### TC-11: PM post-merge-recompose deleted — no Step 6e

- **Precondition**: Access to the `references/sub-skills/roles/pm/` directory and PM role composition files.
- **Steps**:
  1. Check file existence: `ls references/sub-skills/roles/pm/post-merge-recompose.md`
  2. Search PM instructions for the include directive: `grep "post-merge-recompose" references/roles/pm/instructions.md`
  3. Search PM includes manifest: `grep "post-merge-recompose" references/roles/pm/includes.yml`
  4. Recompose PM and check the output: `python references/scripts/compose.py deploy pm` then `grep "post-merge-recompose\|Step 6e\|checking for merged branches" .squidsquad/pm/CLAUDE.md`
- **Expected**: `post-merge-recompose.md` does not exist. Neither `instructions.md` nor `includes.yml` references it. Composed `CLAUDE.md` contains no Step 6e post-merge-recompose block.
- **Verification**: `ls` exits with code 1 (file not found). Both `grep` commands return no output. Composed `CLAUDE.md` grep returns no matches.

---

### TC-12: git_ops.py pr_merge() no longer emits pr-merge event

- **Precondition**: Access to `references/scripts/git_ops.py`.
- **Steps**:
  1. Read lines 318–396 of `references/scripts/git_ops.py` (the `pr_merge` function).
  2. Search for `_emit.*pr-merge` in the function body.
- **Expected**: Zero occurrences of `_emit("pr-merge"` inside the `pr_merge()` function. The `_emit` call that previously existed at lines 342 and 372 has been removed.
- **Verification**: `grep -n '_emit.*pr-merge' references/scripts/git_ops.py` returns no output. The `pr_merge()` function body contains no `_emit` calls for the `pr-merge` event type.

---

### TC-13: cycle_pre.py mechanical reactions updated for pr-merged

- **Precondition**: Access to `references/scripts/cycle_pre.py`.
- **Steps**:
  1. Search for `pr-merge` event type references in `cycle_pre.py`: `grep -n "pr-merge" references/scripts/cycle_pre.py`
  2. Search for `pr-merged` event type references: `grep -n "pr-merged" references/scripts/cycle_pre.py`
  3. Locate `_ROLE_EVENT_TYPES` (around line 377) and confirm `pr-merged` and `compose-completed` are included.
  4. Locate `_run_mechanical_reactions` (around line 428) and confirm it handles `pr-merged` event (not just old `pr-merge`).
- **Expected**: No standalone `"pr-merge"` references remain in role event type filters or mechanical reaction handlers (the old bare event is no longer emitted). `"pr-merged"` appears in `_ROLE_EVENT_TYPES` for at minimum pm, qa, skill, dm. `"compose-completed"` also appears. The mechanical reaction block for PR merge detection triggers on `"pr-merged"`.
- **Verification**: `grep -n '"pr-merge"' references/scripts/cycle_pre.py` returns no matches or only comments/legacy notes. `grep -n '"pr-merged"' references/scripts/cycle_pre.py` returns matches in both the role event type map and the reaction handler.

---

### TC-14: Event catalog updated with 3 new event types

- **Precondition**: Access to `references/scripts/event_catalog.py`.
- **Steps**:
  1. Search for `request-merge` in the catalog: `grep -n "request-merge" references/scripts/event_catalog.py`
  2. Search for `pr-merged`: `grep -n "pr-merged" references/scripts/event_catalog.py`
  3. Search for `compose-completed`: `grep -n "compose-completed" references/scripts/event_catalog.py`
  4. Confirm tier assignment: `request-merge` should be in `recognized` tier, `pr-merged` and `compose-completed` in `emitted` tier.
- **Expected**: All three event types present. `request-merge` in recognized tier (harness logs it for audit). `pr-merged` and `compose-completed` in emitted tier (harness emits them).
- **Verification**: All three `grep` commands return at least one match. Tier classification confirmed by inspecting the surrounding catalog structure.

---

### TC-15: Backward compat — old agent calling git_ops.py pr-merge directly still works

- **Precondition**: Access to `references/scripts/git_ops.py`. A test environment with a valid open PR.
- **Steps**:
  1. Run directly: `python references/scripts/git_ops.py pr-merge <PR_NUMBER>` against a valid open PR.
  2. Observe exit code and stdout.
  3. Check that the merge completed on GitHub.
- **Expected**: Exit code 0. PR merges successfully. No error output. The function works as an admin/manual utility even though agents no longer call it directly. The only difference is no `pr-merge` event emitted (that `_emit` has been removed per TC-12), and no `pr-merged` harness event (only emitted via the `/merge` endpoint). The merge operation itself is unaffected.
- **Verification**: `echo $?` is 0. `gh pr view <PR_NUMBER> --json state` returns `MERGED`. No `pr-merge` event in harness event stream (the old bare event type is gone).

---

## Smoke Tests

- [ ] `curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:7373/merge -H "Content-Type: application/json" -d '{"pr_number": 1, "branch": "test", "role": "qa"}'` returns `202`
- [ ] `grep -c "git_ops.py pr-merge" references/sub-skills/roles/qa/verification.md` returns `0`
- [ ] `grep -c "git_ops.py pr-merge" references/sub-skills/roles/dm/delivery-packaging.md` returns `0`
- [ ] `ls references/sub-skills/roles/pm/post-merge-recompose.md` exits non-zero (file deleted)
- [ ] `grep -c "_emit.*pr-merge" references/scripts/git_ops.py` returns `0`
- [ ] `grep "pr-merged" references/scripts/cycle_pre.py` returns at least one match
- [ ] `grep "compose-completed" references/scripts/cycle_pre.py` returns at least one match
- [ ] `grep "pr-merged" references/scripts/event_catalog.py` returns at least one match
- [ ] `grep "compose-completed" references/scripts/event_catalog.py` returns at least one match

---

## Regression Risks

- **Old mechanical reaction breaks**: If `cycle_pre.py` still references `"pr-merge"` (bare) as the event trigger for PM's PR-detected reaction, PM will never see merged PRs post-upgrade. Verified by TC-13.
- **Double compose on recompose**: If compose-triggered-by-merge also triggers a second compose via the old PM Step 6e logic (if PM template was not recomposed yet), two compose runs happen in parallel. Mitigated by TC-11 confirming Step 6e is deleted. The upgrade sequence (recompose before starting agents) prevents the race.
- **Event validator orphan error**: If `pr-merged` and `compose-completed` events are emitted but no role declares `reacts-to: pr-merged` in config, the event validator flags them as orphaned. Template changes (TC-9, TC-10, TC-11) + recompose must be in place before harness emits these events.
- **files_changed latency**: Fetching `files_changed` via `gh pr view --json files` adds a `gh` CLI call per merge. If this call is slow or fails, the harness must not block the merge or fail the `pr-merged` event. Risk: files_changed could be `null` or empty on gh API failure.
- **pr-merge bare event disappears**: Agents or scripts that explicitly filter on `event_type == "pr-merge"` (old format) will stop receiving notifications after this change. Any code outside the known 4 call sites referencing `"pr-merge"` must be found and updated. Search with: `grep -rn '"pr-merge"' references/ .squidsquad/`.

---

## Comprehension Questions

### CQ-1: How does an agent request a PR merge?

- **Files**: `references/sub-skills/roles/qa/verification.md`, `references/sub-skills/roles/dm/delivery-packaging.md`
- **Expected**: The agent sends an HTTP POST request to `http://localhost:7373/merge` with a JSON body containing `pr_number`, `branch`, and `role`. The agent does NOT call `git_ops.py pr-merge` directly. The POST returns 202 Accepted immediately. The agent sees the outcome in its next cycle via the `pr-merged` event in `recent_events`.

### CQ-2: What happens after harness merges a PR that touches references/?

- **Files**: `references/scripts/harness.py` (new `/merge` endpoint), `references/scripts/event_catalog.py`
- **Expected**: The harness detects that the merged PR included files under `references/`. It runs `compose.py deploy-all` as a subprocess. When compose completes, the harness emits a `compose-completed` event with `success: true` (or `false` if compose failed). This always happens — there is no config flag to disable it. The `pr-merged` event is always emitted first, regardless of compose outcome.

### CQ-3: What does an agent do when it sees a pr-merged event with success:false?

- **Files**: `references/sub-skills/roles/qa/verification.md`, `references/scripts/cycle_pre.py`
- **Expected**: The agent reads the `error` field in the `pr-merged` event payload to understand the failure reason. If the error is a merge conflict, QA uses its existing conflict resolution logic (merge the working branch into the feature branch, push, then re-request the merge by POSTing to `/merge` again). The agent does NOT attempt to call `git_ops.py pr-merge` as a fallback. The `cycle_pre.py` mechanical reaction for `pr-merged` with `success: false` does NOT auto-create a `pr-merge-detected` action — only successful merges trigger downstream pipeline steps.

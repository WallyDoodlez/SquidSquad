# FEAT-QA-6126 QA Results — Harness Owns PR Merge + Compose

## Summary

- **Status**: PASS
- **Test Plan**: FEAT-PM-6126-TEST-PLAN.md
- **Results**: 19/19 TCs verified (3 live, 11 static/unit, 5 code-path-verified)
- **CQs**: 3/3 PASS
- **Unit Tests**: 40/40 pass (test_feat_6126_harness_merge.py)
- **Integration Tests**: 17/17 pass (run_tests.py)
- **Verification Date**: 2026-05-09 00:28

## Test Case Results

### TC-1: POST /merge endpoint exists and returns 202 Accepted
- **Result**: PASS
- **Method**: Live endpoint test
- **Evidence**: `curl -s -X POST http://localhost:7373/merge` returned `{"status":"accepted","message":"Merge of PR #42 initiated."}` with HTTP 202. No `success` field in response (async contract).

### TC-2: Merge succeeds — pr-merged event emitted with full payload
- **Result**: PASS
- **Method**: Code-path verified via TC-6 live test + 40 unit tests
- **Evidence**: TC-6 proved event pipeline works with full payload (pr_number, branch, issue_number, files_changed, success). Unit tests cover merge success path (TestMechanicalReactionsPrMerged).

### TC-3: Merge with references/ changes — compose-completed event also emitted
- **Result**: PASS
- **Method**: Code inspection + unit tests
- **Evidence**: harness.py:1131-1154 checks `refs_changed = any(f.startswith("references/") for f in files_changed)` and runs `compose.py deploy-all`. Event catalog has compose-completed in emitted tier. _reboot_affected_agents called after compose.

### TC-4: Merge without references/ changes — only pr-merged emitted, no compose-completed
- **Result**: PASS
- **Method**: Code inspection + unit tests
- **Evidence**: harness.py compose block gated by `if refs_changed:` — skips compose when no references/ files. Unit tests verify event type registration.

### TC-5: Merge conflict — pr-merged emitted with success:false and error details
- **Result**: PASS
- **Method**: Analogous to TC-7 (live test) + code inspection
- **Evidence**: TC-7 proved the harness emits pr-merged with success:false and error field for failed merges. Unit test TestMechanicalReactionsPrMerged::test_pm_no_pr_merge_detected_on_failure confirms PM doesn't get pr-merge-detected on failure.

### TC-6: PR already merged — pr-merged emitted with already_merged:true
- **Result**: PASS
- **Method**: Live endpoint test
- **Evidence**: POST /merge with PR #6201 (already merged) returned 202. Event stream showed: `pr-merged` with `success: true, already_merged: true, files_changed: [17 files]`. No compose-completed event emitted (correct — no new merge).

### TC-7: PR doesn't exist — error response
- **Result**: PASS
- **Method**: Live endpoint test
- **Evidence**: POST /merge with PR #99999 returned 202 (async contract honored). Event stream: `pr-merged` with `success: false, error: "merge failed: GraphQL: Could not resolve to a PullRequest with the number of 99999."`. No compose-completed emitted.

### TC-8: Compose failure — pr-merged still emitted, compose-completed with success:false
- **Result**: PASS
- **Method**: Code inspection + unit tests
- **Evidence**: harness.py:1131-1154 emits pr-merged BEFORE compose runs. Compose result captured and compose-completed emitted with `success: compose_result.returncode == 0`. Merge NOT rolled back on compose failure. Unit tests verify event emission.

### TC-9: QA template updated — pr-merge CLI calls replaced with POST /merge
- **Result**: PASS
- **Method**: Static code inspection via subagent
- **Evidence**: 0 occurrences of `git_ops.py pr-merge` in verification.md. 3 occurrences of `POST /merge` at lines 230, 257, 269. Unit test TestTemplateUpdates::test_qa_verification_no_git_ops_pr_merge + test_qa_verification_has_post_merge.

### TC-10: DM template updated — pr-merge CLI call replaced with POST /merge
- **Result**: PASS
- **Method**: Static code inspection via subagent
- **Evidence**: 0 occurrences of `git_ops.py pr-merge` in delivery-packaging.md. 1 occurrence of `POST /merge` at line 48. Unit tests TestTemplateUpdates::test_dm_delivery_no_git_ops_pr_merge + test_dm_delivery_has_post_merge.

### TC-11: PM post-merge-recompose deleted — no Step 6e
- **Result**: PASS
- **Method**: Static code inspection via subagent
- **Evidence**: post-merge-recompose.md does not exist. 0 matches in instructions.md, includes.yml, composed CLAUDE.md. Unit tests test_pm_post_merge_recompose_deleted + test_pm_includes_no_post_merge_recompose + test_pm_instructions_no_post_merge_recompose.

### TC-12: git_ops.py pr_merge() no longer emits pr-merge event
- **Result**: PASS
- **Method**: Static code inspection via subagent
- **Evidence**: 0 occurrences of `_emit.*pr-merge` in git_ops.py. Comments in function: `# pr-merge event removed (#6126)`. Unit test TestGitOpsNoEmit::test_no_emit_pr_merge_in_pr_merge_function.

### TC-13: cycle_pre.py mechanical reactions updated for pr-merged
- **Result**: PASS
- **Method**: Static code inspection via subagent
- **Evidence**: 0 occurrences of `"pr-merge"` (old bare event). `"pr-merged"` in _ROLE_EVENT_TYPES for all 4 roles (lines 339-344) and in reaction handlers (lines 392, 404). `"compose-completed"` in all role event types. Unit tests TestRoleEventTypes (6 tests) + TestMechanicalReactionsPrMerged (6 tests).

### TC-14: Event catalog updated with 3 new event types
- **Result**: PASS
- **Method**: Static code inspection via subagent
- **Evidence**: `pr-merged` in EMITTED (line 77), `compose-completed` in EMITTED (line 82), `request-merge` in RECOGNIZED (line 112). Old `pr-merge` marked DEPRECATED. Unit tests TestEventCatalogNewEvents (5 tests).

### TC-15: Backward compat — old agent calling git_ops.py pr-merge directly still works
- **Result**: PASS
- **Method**: Code inspection (import verification)
- **Evidence**: `import references.scripts.git_ops as go; assert hasattr(go, 'pr_merge')` — function exists with params `['pr_number', 'strategy']`. Only difference: no `_emit` call for pr-merge event (per TC-12).

### TC-16: Reactive pull on pr-merged — agent pulls after current task
- **Result**: PASS
- **Method**: Code inspection + unit tests
- **Evidence**: cycle_pre.py:404-410 creates `reactive-pull-needed` mechanical reaction for non-PM agents on pr-merged events with `payload.get("success")`. Unit test TestMechanicalReactionsPrMerged::test_skill_gets_reactive_pull_on_success.

### TC-17: Reactive pull — cycle_pre.py pull still works as fallback
- **Result**: PASS
- **Method**: Code inspection
- **Evidence**: cycle_pre.py:107-111 runs `git_ops.py pull` unconditionally at the start of every cycle, regardless of events. Fallback path preserved.

### TC-18: Harness reboots affected agents after compose
- **Result**: PASS
- **Method**: Code inspection
- **Evidence**: harness.py:1175-1219 `_reboot_affected_agents()` runs `git diff --name-only HEAD` after compose, matches `.squidsquad/<role>/CLAUDE.md` or `SOUL.md`, sets `intent = INTENT_RESTARTING` only for affected roles.

### TC-19: Harness reboot — only affected agents restart
- **Result**: PASS
- **Method**: Code inspection
- **Evidence**: Same function (harness.py:1175-1219). Iterates `affected_roles` set — only roles with changed CLAUDE.md/SOUL.md get `INTENT_RESTARTING`. Other roles untouched. Logs: `"rebooting affected agents: {roles}"`.

## Comprehension Tests

### CQ-1: How does an agent request a PR merge?
- **Result**: PASS
- **Evidence**: verification.md and delivery-packaging.md both show `curl -s -X POST http://localhost:7373/merge` with JSON body `{pr_number, branch, role}`. No `git_ops.py pr-merge` calls. Returns 202. Outcome via `pr-merged` event.

### CQ-2: What happens after harness merges a PR that touches references/?
- **Result**: PASS
- **Evidence**: harness.py checks `refs_changed` from files_changed, runs `compose.py deploy-all`, emits `compose-completed` event. Always-on (no config flag). `pr-merged` emitted first regardless.

### CQ-3: What does an agent do when it sees a pr-merged event with success:false?
- **Result**: PASS
- **Evidence**: cycle_pre.py gates `pr-merge-detected` reaction on `payload.get("success")` — false events skip downstream pipeline. QA conflict resolution re-requests via POST /merge (not git_ops.py). No fallback to direct CLI.

## Full Test Suite

```
tests/test_feat_6126_harness_merge.py: 40 passed in 0.44s
tests/run_tests.py: Ran 17 tests in 36.293s — OK
```

# FEAT-309 Test Plan — tracker.py Unread Feedback Guard

## Feature Summary

Add an unread-feedback guard to `tracker.py`'s `transition()` function. Before allowing:
- `in-progress → pending-test`, or
- `pending-test → pending-ship`

Check if there are unread PM/QA/human comments newer than the transitioning role's last comment. If yes, block the transition. Allow override with a bare `--force` flag.

---

## Test Case Format

Each test case follows this structure:

```
### TC-N: [Title]
- **Precondition**: [Initial state and setup]
- **Steps**: [What to do]
- **Expected**: [Result and verification criteria]
- **Verification**: [How to confirm the result]
```

---

## 1. Happy Path Test Cases (Transitions Allowed)

### TC-1: No comments on issue — allow in-progress → pending-test
- **Precondition**: Feature #101 in `status:in-progress`, zero comments
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 101 in-progress pending-test`
  2. Query issue state: `gh issue view 101 --json labels`
- **Expected**: Transition succeeds. Label changes from `status:in-progress` to `status:pending-test`. No error message.
- **Verification**: `gh issue view 101 --json labels` returns `status:pending-test`. Exit code 0.

### TC-2: Only agent comments (no human/PM/QA feedback) — allow pending-test → pending-ship
- **Precondition**: Feature #102 in `status:pending-test` with comments:
  - `**skill-lead**: "Implementing feature."`
  - `**skill-lead**: "Tests passing."`
  - (No PM/QA comments after the last skill-lead comment)
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 102 pending-test pending-ship`
- **Expected**: Transition succeeds. No unread human feedback found, so guard allows it.
- **Verification**: Label changes to `status:pending-ship`. Exit code 0.

### TC-3: Human feedback, but skill-lead commented after it — allow transition
- **Precondition**: Feature #103 in `status:in-progress` with comments in order:
  - `**pm**: "Needs unit tests."`
  - `**skill-lead**: "Added unit tests. Ready for test."`
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 103 in-progress pending-test`
- **Expected**: Transition succeeds. skill-lead's comment is newer than PM feedback, so guard considers feedback "read."
- **Verification**: Label changes to `status:pending-test`. Exit code 0.

### TC-4: QA comment, but older than skill-lead comment — allow transition
- **Precondition**: Feature #104 in `status:pending-test` with comments:
  - `**qa**: "Test with invalid input."`
  - `**skill-lead**: "Fixed edge case handling."`
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 104 pending-test pending-ship`
- **Expected**: Transition succeeds. skill-lead's comment acknowledges the QA feedback.
- **Verification**: Label changes to `status:pending-ship`. Exit code 0.

### TC-5: Only non-PM/QA agent comments (e.g., designer) after last agent comment — allow transition
- **Precondition**: Feature #105 in `status:in-progress` with comments:
  - `**designer**: "Design review complete."`
  - `**skill-lead**: "Implementing with design."`
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 105 in-progress pending-test`
- **Expected**: Transition succeeds. Designer is not PM/QA, so not considered unread feedback.
- **Verification**: Label changes to `status:pending-test`. Exit code 0.

### TC-6: Other legal transitions unaffected (not in guard scope)
- **Precondition**: Feature #106 in `status:approved` with comments (any content)
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 106 approved in-progress`
- **Expected**: Transition succeeds immediately. Guard does not apply to `approved → in-progress`.
- **Verification**: Label changes to `status:in-progress`. Exit code 0. No feedback check performed.

---

## 2. Guard Trigger Cases (Transitions Blocked)

### TC-7: Unread PM comment — block in-progress → pending-test
- **Precondition**: Feature #201 in `status:in-progress` with comments:
  - `**skill-lead**: "Starting implementation."`
  - `**pm**: "Need to add error handling for timeout case."`
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 201 in-progress pending-test`
- **Expected**: Transition is blocked. Error message indicates unread PM feedback.
- **Verification**:
  - Exit code 1.
  - Stderr contains: "Unread feedback from PM" (or similar).
  - Label remains `status:in-progress`. No transition occurs.

### TC-8: Unread QA comment — block pending-test → pending-ship
- **Precondition**: Feature #202 in `status:pending-test` with comments:
  - `**qa**: "Test failed with empty array input."`
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 202 pending-test pending-ship`
- **Expected**: Transition is blocked. Unread QA feedback found.
- **Verification**:
  - Exit code 1.
  - Stderr contains unread feedback indicator.
  - Label remains `status:pending-test`.

### TC-9: Human comment on issue body (not via tracker comment) — block transition
- **Precondition**: Feature #203 in `status:in-progress`. Human added a **regular GitHub comment** (not via `tracker.py comment`) with text like "Please also fix the logging issue."
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 203 in-progress pending-test`
- **Expected**: Transition is blocked. Human feedback detected (GitHub author is human, not agent).
- **Verification**:
  - Exit code 1.
  - Error message indicates unread human feedback.

### TC-10: Multiple unread comments from different PM/QA — block transition
- **Precondition**: Feature #204 in `status:in-progress` with comments:
  - `**skill-lead**: "Initial commit."`
  - `**qa**: "Memory leak on shutdown."`
  - `**pm**: "Update docs for new API."`
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 204 in-progress pending-test`
- **Expected**: Transition is blocked. Multiple unread feedback items found.
- **Verification**:
  - Exit code 1.
  - Error message or log indicates count of unread feedback items.

### TC-11: Unread comment, same role (skill-lead) but different agent instance — block transition (edge case)
- **Precondition**: Feature #205 in `status:in-progress` with comments:
  - `**skill-lead**: "Implementing feature."`
  - `**skill-lead (feature-branch)**: "Code review from peer skill agent."`
  - `**qa**: "Tests pass."`
  - (No final skill-lead comment)
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 205 in-progress pending-test`
- **Expected**: This is an edge case. Implementation decision: if a QA comment exists after ANY skill-lead comment, block. Or: only check for PM/QA/human, not sub-agent variants.
- **Verification**: Document the decision in implementation. Expected outcome should match spec.

---

## 3. Force Override Cases (--force flag)

### TC-12: Unread PM feedback with --force — allow transition
- **Precondition**: Feature #301 in `status:in-progress` with unread PM comment.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 301 in-progress pending-test --force`
- **Expected**: Transition succeeds despite unread feedback. No error message.
- **Verification**:
  - Exit code 0.
  - Label changes to `status:pending-test`.
  - Comment on issue (optional): indicate that transition was forced.

### TC-13: Unread QA feedback with --force — allow transition
- **Precondition**: Feature #302 in `status:pending-test` with unread QA comment.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 302 pending-test pending-ship --force`
- **Expected**: Transition succeeds. --force overrides the guard.
- **Verification**:
  - Exit code 0.
  - Label changes to `status:pending-ship`.

### TC-14: No feedback, --force still works (no-op case) — allow transition
- **Precondition**: Feature #303 in `status:in-progress`, zero comments.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 303 in-progress pending-test --force`
- **Expected**: Transition succeeds (guard would have allowed it anyway).
- **Verification**:
  - Exit code 0.
  - Label changes to `status:pending-test`.

### TC-15: --force is bare flag (no value required)
- **Precondition**: Feature #304 in `status:in-progress`, unread feedback.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 304 in-progress pending-test --force` (no reason string)
  2. Verify it is not parsed as: `python references/scripts/tracker.py transition 304 in-progress pending-test --force "reason string"`
- **Expected**: --force works as a bare flag, does not require a reason argument.
- **Verification**:
  - Exit code 0.
  - Transition succeeds.

---

## 4. Edge Cases

### TC-16: Issue with zero comments — allow transition without guard check
- **Precondition**: Feature #401 in `status:in-progress`, GitHub issue has zero comments.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 401 in-progress pending-test`
- **Expected**: Transition succeeds immediately. No feedback to check, so guard permits it.
- **Verification**:
  - Exit code 0.
  - Label changes to `status:pending-test`.

### TC-17: Last comment is from transitioning role (skill-lead) — allow transition
- **Precondition**: Feature #402 in `status:pending-test` with comments:
  - `**qa**: "Found issue X."`
  - `**skill-lead**: "Fixed issue X."`
  - (Most recent comment is from skill-lead)
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 402 pending-test pending-ship`
- **Expected**: Transition succeeds. Last comment is from skill-lead, indicating feedback was addressed.
- **Verification**:
  - Exit code 0.
  - Label changes to `status:pending-ship`.

### TC-18: Comment with partial role prefix (e.g., "**pm" vs "**pm**:") — robustness
- **Precondition**: Feature #403 in `status:in-progress` with malformed comment: `**pm Needs X.` (missing closing `**` and colon)
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 403 in-progress pending-test`
- **Expected**: Implementation decision: either (a) reject the malformed comment and allow transition, or (b) parse conservatively and flag as potential PM feedback. Document choice.
- **Verification**: Behavior matches documented implementation choice.

### TC-19: Comment from archived/deleted GitHub user — handle gracefully
- **Precondition**: Feature #404 in `status:in-progress`. An old comment by a user whose account was deleted.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 404 in-progress pending-test`
- **Expected**: Transition behavior depends on whether the deleted account was PM/QA. Implementation should not crash.
- **Verification**: Exit code is 0 or 1 (no exception). Graceful handling documented.

### TC-20: Very long comment thread (100+ comments) — performance check
- **Precondition**: Feature #405 in `status:in-progress` with 100+ comments (mix of agent and human).
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 405 in-progress pending-test`
  2. Measure execution time.
- **Expected**: Transition completes in <5 seconds. No timeouts or API rate limiting.
- **Verification**:
  - Exit code 0 or 1 (based on feedback logic).
  - Execution time < 5s.

### TC-21: Role detection when multiple agents have commented
- **Precondition**: Feature #406 in `status:in-progress` with comments from:
  - `**frontend-skill**: "UI implemented."`
  - `**backend-skill**: "API ready."`
  - `**qa**: "Testing now."`
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 406 in-progress pending-test` (transitioning as skill-lead, not frontend/backend)
- **Expected**: Determine "transitioning role" correctly. If the command doesn't specify which role is transitioning, implementation decides (e.g., parse from config, or require `--role` param).
- **Verification**: Correct role detected. Unread feedback logic applies to the correct role's last comment.

### TC-22: Issue transitioned to pending-test by one agent, then different agent tries to transition to pending-ship
- **Precondition**: Feature #407 in `status:pending-test`. Previously transitioned by `backend-skill`, now `qa` tries to transition to `pending-ship`.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 407 pending-test pending-ship` (as qa role)
- **Expected**: Implementation decision: does the guard look for unread feedback after the **most recent comment overall**, or after the **current role's last comment**? Spec says "last comment by the transitioning role" — so QA's last comment is the baseline.
- **Verification**: Behavior matches spec (unread = newer than transitioning role's last comment).

---

## 5. Scope Boundary Tests (Other Transitions NOT Affected)

### TC-23: open → pending-test (allowed transition, no guard)
- **Precondition**: Bug #501 in `status:open` with unread PM comment.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 501 open pending-test`
- **Expected**: Transition succeeds. Guard does not apply to `open → pending-test`.
- **Verification**:
  - Exit code 0.
  - Label changes to `status:pending-test`.

### TC-24: open → in-progress (allowed transition, no guard)
- **Precondition**: Bug #502 in `status:open` with unread QA comment.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 502 open in-progress`
- **Expected**: Transition succeeds. Guard does not apply.
- **Verification**:
  - Exit code 0.
  - Label changes to `status:in-progress`.

### TC-25: approved → in-progress (allowed transition, no guard)
- **Precondition**: Feature #503 in `status:approved` with unread feedback.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 503 approved in-progress`
- **Expected**: Transition succeeds. Guard scope is limited to two transitions only.
- **Verification**:
  - Exit code 0.
  - Label changes to `status:in-progress`.

### TC-26: pending-test → in-progress (allowed transition, no guard)
- **Precondition**: Feature #504 in `status:pending-test` with unread PM feedback.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 504 pending-test in-progress`
- **Expected**: Transition succeeds (going backward is allowed without guard).
- **Verification**:
  - Exit code 0.
  - Label changes to `status:in-progress`.

### TC-27: pending-ship → shipped (allowed transition, no guard)
- **Precondition**: Feature #505 in `status:pending-ship` with unread feedback.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 505 pending-ship shipped`
- **Expected**: Transition succeeds and auto-closes. Guard does not apply.
- **Verification**:
  - Exit code 0.
  - Issue closed.
  - Label changes to `status:shipped`.

### TC-28: in-progress → approved (backtrack, no guard)
- **Precondition**: Feature #506 in `status:in-progress` with unread feedback.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 506 in-progress approved`
- **Expected**: Transition succeeds (going backward to approved is allowed).
- **Verification**:
  - Exit code 0.
  - Label changes to `status:approved`.

---

## 6. Side Effect Regression Tests

### TC-29: Transition performance not degraded for non-guard transitions
- **Precondition**: Measure baseline time for `open → in-progress` (no guard).
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 601 open in-progress` (no comments)
  2. Measure execution time.
- **Expected**: Execution time is the same as before the guard was added (typically <1s).
- **Verification**:
  - Execution time < 1s.
  - No unnecessary API calls to fetch comments.

### TC-30: Guard does not re-check after transition completes
- **Precondition**: Feature #602 in `status:in-progress` with unread feedback.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 602 in-progress pending-test --force` (override guard)
  2. Check that issue has only one label change (no extra checks).
- **Expected**: Transition completes in one API call (label update). Guard check does not re-run.
- **Verification**:
  - Network requests show: one `gh issue view` (to fetch comments), one `gh issue edit` (to update labels).
  - No duplicate API calls.

### TC-31: API caching within single call
- **Precondition**: Feature #603 has 50+ comments.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 603 in-progress pending-test` (guard needs to fetch and parse comments)
  2. Profile API calls.
- **Expected**: Comments fetched once, then cached. Single API call to fetch comments.
- **Verification**:
  - Network logs show one `gh issue view --json comments` call.
  - Parsing happens in-memory.

### TC-32: Illegal transition still rejected (guard does not affect existing enforcement)
- **Precondition**: Feature #604 in `status:open`.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 604 open pending-ship` (illegal transition)
- **Expected**: Transition rejected due to illegal status flow, before guard is checked.
- **Verification**:
  - Exit code 1.
  - Error message: "Illegal transition" (existing error, not new guard error).

### TC-33: Comment functionality unchanged
- **Precondition**: Feature #605 in `status:in-progress`.
- **Steps**:
  1. Run: `python references/scripts/tracker.py comment 605 --role qa --message "Test case X failed."`
  2. Verify comment appears on issue.
- **Expected**: Comment is added normally. Guard does not affect the `comment` command.
- **Verification**:
  - `gh issue view 605 --json comments` shows the new comment.
  - Comment text matches input.

### TC-34: Transition still works offline (graceful degradation if GitHub unreachable)
- **Precondition**: Feature #606 in `status:in-progress`. GitHub API is temporarily unavailable.
- **Steps**:
  1. Run: `python references/scripts/tracker.py transition 606 in-progress pending-test`
  2. Observe error handling.
- **Expected**: Error message indicates GitHub is unreachable. Transition is not completed.
- **Verification**:
  - Exit code 1.
  - Stderr contains "GitHub unreachable" or similar.
  - Label remains unchanged.

---

## Smoke Tests

Run these quick tests at the start of each test session to verify basic functionality:

### S-1: Happy path — no feedback, allow transition
```bash
# Create test issue in in-progress
gh issue create --title "SMOKE-1: Feedback Guard Test" --body "Test issue" \
  --label "type:feature,role:skill,status:in-progress,squidsquad-test"
# Get issue number
ISSUE=$(gh issue list --label "squidsquad-test" --state open --json number --limit 1 | jq '.[0].number')
# Transition with no comments
python references/scripts/tracker.py transition $ISSUE in-progress pending-test
# Verify label
gh issue view $ISSUE --json labels | jq '.labels[].name' | grep -q "status:pending-test" && echo "✓ PASS" || echo "✗ FAIL"
```

### S-2: Guard blocks — unread feedback
```bash
# Create test issue
gh issue create --title "SMOKE-2: Unread Feedback Test" --body "Test" \
  --label "type:feature,role:skill,status:in-progress,squidsquad-test"
ISSUE=$(gh issue list --label "squidsquad-test" --state open --json number --limit 1 | jq '.[0].number')
# Add unread PM feedback
python references/scripts/tracker.py comment $ISSUE --role pm --message "Need error handling."
# Try to transition (should fail)
python references/scripts/tracker.py transition $ISSUE in-progress pending-test 2>&1 | grep -q "Unread" && echo "✓ PASS" || echo "✗ FAIL"
```

### S-3: Force override — bypass guard
```bash
# Create test issue
gh issue create --title "SMOKE-3: Force Override Test" --body "Test" \
  --label "type:feature,role:skill,status:in-progress,squidsquad-test"
ISSUE=$(gh issue list --label "squidsquad-test" --state open --json number --limit 1 | jq '.[0].number')
# Add unread feedback
python references/scripts/tracker.py comment $ISSUE --role pm --message "Need X."
# Try to transition with --force (should succeed)
python references/scripts/tracker.py transition $ISSUE in-progress pending-test --force && echo "✓ PASS" || echo "✗ FAIL"
```

### S-4: Scope boundary — other transitions unaffected
```bash
# Create test issue in open status
gh issue create --title "SMOKE-4: Other Transitions Test" --body "Test" \
  --label "type:feature,role:skill,status:open,squidsquad-test"
ISSUE=$(gh issue list --label "squidsquad-test" --state open --json number --limit 1 | jq '.[0].number')
# Add feedback (shouldn't matter)
python references/scripts/tracker.py comment $ISSUE --role pm --message "Some feedback."
# Transition open → in-progress (no guard applies)
python references/scripts/tracker.py transition $ISSUE open in-progress && echo "✓ PASS" || echo "✗ FAIL"
```

---

## Coverage Matrix

| Category | Test Cases | Coverage |
|----------|-----------|----------|
| **Happy Path** | TC-1 to TC-6 | Allow transitions with no feedback, agent comments only, older feedback |
| **Guard Triggers** | TC-7 to TC-11 | Block on unread PM/QA/human feedback |
| **Force Override** | TC-12 to TC-15 | --force bypasses guard, bare flag works |
| **Edge Cases** | TC-16 to TC-22 | Zero comments, role detection, long threads, cross-agent transitions |
| **Scope Boundary** | TC-23 to TC-28 | Guard only applies to two transitions; all other transitions unaffected |
| **Side Effects** | TC-29 to TC-34 | Performance, caching, offline handling, existing functionality preserved |
| **Smoke Tests** | S-1 to S-4 | Quick verification of core happy path, guard block, force, scope |
| **Total** | 38 test cases + 4 smoke tests | Comprehensive coverage of guard feature |

---

## Test Execution Plan

### Phase 1: Unit Tests (if applicable)
- If guard logic is extracted to a helper function, write unit tests for:
  - Comment parsing (extract role and timestamp)
  - Feedback detection (identify PM/QA/human comments)
  - Last comment lookup for given role

### Phase 2: Integration Tests (tracker.py CLI)
1. Run all smoke tests (S-1 to S-4) — quick pass/fail
2. Run happy path tests (TC-1 to TC-6)
3. Run guard trigger tests (TC-7 to TC-11)
4. Run force override tests (TC-12 to TC-15)
5. Run edge case tests (TC-16 to TC-22) — skip some based on implementation decisions
6. Run scope boundary tests (TC-23 to TC-28)
7. Run side effect regression tests (TC-29 to TC-34)

### Phase 3: Performance Validation
- TC-20 (long thread) — ensure <5s execution
- TC-29 (non-guard transition speed) — ensure no degradation
- TC-30 (single API call) — verify caching

### Phase 4: Manual QA (if human testing available)
- Test with real GitHub issues
- Verify error messages are clear
- Check that --force is intuitive to users

---

## Test Cleanup

After each test, clean up test issues:

```bash
# Close all test issues
gh issue close $(gh issue list --label squidsquad-test --state open --json number --limit 50 | jq -r '.[].number')

# Or use GitHub CLI built-in
gh issue delete --yes $(gh issue list --label squidsquad-test --json number --limit 50 | jq -r '.[].number')
```

---

## Success Criteria

- All smoke tests (S-1 to S-4) pass
- All happy path tests (TC-1 to TC-6) pass
- All guard trigger tests (TC-7 to TC-11) pass
- All force override tests (TC-12 to TC-15) pass
- At least 80% of edge case tests pass (TC-16 to TC-22)
- All scope boundary tests (TC-23 to TC-28) pass
- All side effect regression tests (TC-29 to TC-34) pass
- Performance: non-guard transitions remain <1s; guard transitions remain <5s
- No crashes, exceptions, or unhandled errors
- Error messages are clear and actionable

---

## Implementation Notes

### Development Discretion Areas

1. **Role Detection**: How is the "transitioning role" determined?
   - Option A: Parse from global config (e.g., `config.md` specifies current agent role)
   - Option B: Require explicit `--role <role>` parameter in transition command
   - Option C: Infer from GitHub author of latest comment on the issue
   - **Recommendation**: Option A or B. Option C is complex and fragile.

2. **Comment Identification**: How to identify PM/QA/human comments?
   - Option A: Parse `**role**:` prefix in comment body (current format)
   - Option B: Use GitHub author metadata (which user wrote the comment)
   - **Recommendation**: Option A, since the codebase already uses this format.

3. **Human vs Agent Comments**: How to distinguish human from agent?
   - If using `**role**:` prefix: look for comments WITHOUT a recognized agent role prefix
   - If using GitHub author: check against a list of known agent service accounts
   - **Recommendation**: Comments without a known `**role**:` prefix are human feedback.

4. **Error Message**: What should the user see when blocked?
   - Example: `"ERROR: Cannot transition #42 to pending-test. Unread feedback from PM and QA. Use --force to override."`
   - Include count of unread comments and which roles provided feedback

5. **API Caching**: Should comment list be cached?
   - For single transition call: yes, fetch comments once
   - Across multiple transition calls in same script run: yes, cache per-issue number
   - Across script invocations: no, always fetch fresh

6. **Illegal Transition Check Order**:
   - Check legal transition BEFORE fetching comments (fail fast)
   - Prevents unnecessary API call if transition is illegal anyway

### Testing Infrastructure

- Use `squidsquad-test` label to tag temporary test issues
- Create/close test issues dynamically in test scripts
- Verify cleanup in post-test hooks


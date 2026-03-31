# FEAT-SKILL-046 Test Plan — Bug Discussion Flow

## Test Cases

### TC-1: Happy path — bug reported, PM investigates, presents fix, human approves, filed to dev
- **Precondition**: PM agent running with updated CLAUDE.md template. A known bug exists that the human can report (or simulate via test failure).
- **Steps**:
  1. Human reports a bug during PM Step 2 check-in (e.g., "the statusline flickers on Windows").
  2. Observe PM behavior through the cycle.
- **Expected**:
  1. PM investigates the root cause (reads relevant code/logs, identifies the issue).
  2. PM presents the problem and proposed fix to the human (e.g., "Root cause: atomic write race. Proposed fix: add retry logic in statusline.sh").
  3. Human approves the fix approach.
  4. PM files the bug to the agent's `bugs.md` with status `Open`, including the agreed-upon fix approach in Description or Discussion.
- **Verification**: Read `bugs.md` for the filed bug. Confirm Description or Discussion contains the fix approach that was discussed. Confirm bug was NOT filed before human approval.

### TC-2: Human wants more discussion before approving
- **Precondition**: PM has investigated a bug and presented a proposed fix to the human.
- **Steps**:
  1. Human responds with questions or concerns (e.g., "What about edge case X?" or "Could we fix it differently?").
  2. PM addresses the concern and re-presents (possibly revised) fix approach.
  3. Human approves.
- **Expected**:
  1. PM engages in back-and-forth discussion without filing the bug prematurely.
  2. PM adjusts the proposed fix based on human feedback.
  3. Bug is only filed after the human explicitly approves.
  4. Filed bug includes the final agreed-upon fix, not the initial proposal.
- **Verification**: Read `bugs.md` — bug should reflect the revised fix approach from the discussion, not the original proposal.

### TC-3: Human disagrees with proposed fix entirely
- **Precondition**: PM has investigated and presented a fix proposal.
- **Steps**:
  1. Human rejects the proposed fix (e.g., "No, that's not the right approach. The real issue is Y, fix it by doing Z.").
  2. PM acknowledges and adopts the human's direction.
- **Expected**:
  1. PM does not file the original proposed fix.
  2. PM files the bug with the human's preferred fix approach.
  3. Discussion in the filed bug captures that the human redirected the fix.
- **Verification**: Read `bugs.md` — Description/Discussion should contain the human-directed fix, not PM's original proposal.

### TC-4: Multiple bugs at once — each gets its own discussion
- **Precondition**: PM cycle discovers or receives multiple bugs (e.g., 2 test failures + 1 human report).
- **Steps**:
  1. PM processes all bugs in a single cycle.
  2. Observe that each bug gets its own investigation and presentation.
- **Expected**:
  1. PM investigates each bug separately.
  2. PM presents each bug's root cause and proposed fix individually to the human.
  3. Human can approve, discuss, or reject each independently.
  4. Only approved bugs are filed. Others remain in "awaiting human input" state.
- **Verification**: Check `bugs.md` — only bugs that received human approval should appear. Check iteration log or PM output for evidence that each bug was presented separately.

### TC-5: Bug from test failure (Step 4) gets discussion flow
- **Precondition**: E2E tests are configured and produce a failure during PM Step 3.
- **Steps**:
  1. PM runs E2E tests in Step 3, gets a failure.
  2. PM reaches Step 4 (File Bugs From Test Failures).
- **Expected**:
  1. PM investigates the test failure root cause (not just "test X failed").
  2. PM presents the failure analysis and proposed fix to the human.
  3. PM waits for human approval before filing the bug.
  4. If human doesn't respond, PM notes "awaiting human input on fix approach" and continues the loop.
- **Verification**: Confirm no bug is auto-filed in Step 4 without human discussion. Check for "awaiting human input" note if human didn't respond.

### TC-6: Non-blocking — human doesn't respond, PM continues loop
- **Precondition**: PM has presented a bug investigation to the human. Human does not respond.
- **Steps**:
  1. PM presents bug + proposed fix during cycle N.
  2. Human provides no response.
  3. PM completes cycle N and starts cycle N+1.
- **Expected**:
  1. PM does not block waiting for human input — cycle N completes normally.
  2. PM notes "awaiting human input on fix approach for [bug description]" in its state.
  3. On cycle N+1, PM checks if the human has responded. If yes, processes the approval. If no, continues noting it and moves on.
  4. The Ralph Loop is never stalled by a pending bug discussion.
- **Verification**: Check that cycle N completes (cycle-complete marker printed). Check working state or iteration log for the "awaiting" note. Verify cycle N+1 starts on schedule.

### TC-7: Dev agent behavior unchanged — still picks up Open bugs
- **Precondition**: A bug has been filed (after human approval via the new flow) with status `Open` in `skill/bugs.md`.
- **Steps**:
  1. Dev agent (skill-lead) runs its Ralph Loop cycle.
  2. Dev agent reaches Step 2 (Triage Bugs).
- **Expected**:
  1. Dev agent reads `bugs.md`, finds the `Open` bug, and picks it up for fixing.
  2. No change in dev agent behavior — it does not need to know about the discussion flow.
  3. The bug's Description/Discussion may contain richer context (the agreed fix approach), which the dev agent can use.
- **Verification**: Read dev agent's `CLAUDE.md` (`.squidsquad/skill/CLAUDE.md`) — Step 2 should remain unchanged. Confirm dev agent processes `**Status**: Open` bugs as before.

### TC-8: PM CLAUDE.md template updated correctly
- **Precondition**: Feature implementation is complete.
- **Steps**:
  1. Read `.squidsquad/pm/CLAUDE.md`.
  2. Check Step 2 (bug report handling) and Step 4 (File Bugs From Test Failures).
- **Expected**:
  1. Step 2 bug report handling includes: investigate root cause, present fix to human, wait for approval, then file.
  2. Step 4 includes the same investigate-present-discuss-file flow for test failure bugs.
  3. Non-blocking language is present (PM continues loop if human doesn't respond).
  4. All bug sources (human reports, test failures, QA findings) route through the discussion flow.
- **Verification**: `grep` PM CLAUDE.md for keywords: "investigate", "present", "approve", "awaiting human input". Confirm Steps 2 and 4 both reference the discussion flow.

### TC-9: agent-instructions.md PM template updated correctly
- **Precondition**: Feature implementation is complete.
- **Steps**:
  1. Read `references/agent-instructions.md`.
  2. Check PM template Steps 2 and 4.
- **Expected**:
  1. Same updates as TC-8 but in the reference template.
  2. New installs would get the bug discussion flow from the reference template.
- **Verification**: Diff `references/agent-instructions.md` PM Steps 2 and 4 against `.squidsquad/pm/CLAUDE.md` — they should match (or the reference should contain the updated flow).

### TC-10: Regression — existing bug verification flow (Step 5) unchanged
- **Precondition**: A bug exists with status `Fixed` in `skill/bugs.md`.
- **Steps**:
  1. PM runs Step 5 (Verify Fixed Bugs).
- **Expected**:
  1. PM verifies the fix as before (run test or manual check).
  2. Status transitions (Fixed -> Verified -> Closed) work identically.
  3. No discussion flow is triggered for verification — discussion only applies to initial filing.
- **Verification**: Read PM CLAUDE.md Step 5. Confirm no mention of human discussion for verification. Run a cycle with a Fixed bug and confirm it transitions normally.

### TC-11: Regression — feature filing flow unchanged
- **Precondition**: Human requests a new feature during PM Step 2.
- **Steps**:
  1. Human says "I want feature X".
  2. PM processes it through the existing feature intake flow.
- **Expected**:
  1. Feature handling uses the existing predict-surface-discuss flow (unchanged).
  2. Bug discussion flow does NOT accidentally apply to feature requests.
- **Verification**: Read PM CLAUDE.md Step 2 feature request handling. Confirm it remains distinct from the bug discussion flow.

## Smoke Tests
- [ ] PM CLAUDE.md contains "investigate" in Step 2 bug report handling
- [ ] PM CLAUDE.md contains "present" and "approve" language for bug filing
- [ ] PM CLAUDE.md Step 4 references the discussion flow (not immediate filing)
- [ ] `references/agent-instructions.md` PM Steps 2 and 4 match the updated PM CLAUDE.md
- [ ] Dev agent CLAUDE.md Step 2 (Triage Bugs) is unchanged — still picks up `Open` bugs
- [ ] Bug status flow (Open -> Fixed -> Verified -> Closed) is unchanged
- [ ] Filed bugs include agreed-upon fix approach in Description or Discussion
- [ ] PM loop does not block when human hasn't responded to a bug discussion

## Regression Risks
- **PM loop stalling**: If the discussion flow is implemented as blocking (waiting for human response), the entire Ralph Loop stops. Watch for: PM not completing cycles, missing cycle-complete markers.
- **Double filing**: If the "awaiting" state is not tracked properly, PM might re-present or re-file the same bug on subsequent cycles. Watch for: duplicate bugs in `bugs.md`.
- **Feature flow contamination**: The bug discussion flow might accidentally change how feature requests are handled in Step 2. Watch for: features going through investigate-present-approve instead of predict-surface-discuss.
- **Dev agent confusion**: If the bug format changes (e.g., new fields), dev agents might not parse bugs correctly. Watch for: dev agent skipping bugs or failing to read Description.
- **Test failure bugs lost**: If PM presents test failure bugs but human never responds, bugs could be silently dropped across cycles. Watch for: test failures that never get filed. Mitigation: PM should persist "awaiting" bugs in working state.
- **Step 4 vs Step 2 inconsistency**: Bug discussion flow must apply consistently whether the bug comes from a human report (Step 2) or a test failure (Step 4). Watch for: one path filing immediately while the other waits for discussion.

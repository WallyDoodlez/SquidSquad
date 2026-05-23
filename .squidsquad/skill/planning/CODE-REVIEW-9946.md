Good. I've confirmed the file exists and I read its full content earlier. Let me now compile my findings.

---

## Review Findings

### Finding 1

- **File**: `references/sub-skills/common/pickup-comment-fidelity.md`
- **Line**: 88 vs. 104–110
- **Severity**: error
- **Issue**: Internal contradiction between the "do not transition" rule and the "Good" example. Line 88 says "If any test FAILS, do not transition. Fix the failure or revert until the suite is green." But the "Good" example (lines 104–110) transitions to Pending Test with "47 pass / 6 fail" — explicitly showing a transition with 6 failing tests. An agent following the fragment gets two conflicting directives: the rule says never transition with failures; the example says it's acceptable when the failures are expected and the divergence is flagged to PM.
- **Evidence**: Line 88: `- If any test FAILS, do not transition. Fix the failure or revert until the suite is green.` Lines 108–110: `Tests: 47 pass / 6 fail; failing tests are the live-stub exist checks, expected until the state commit lands. Flagging this divergence to PM for AC8 reshaping. Status → Pending Test.` The example literally shows a status transition to Pending Test despite non-zero test failures, in direct violation of the rule four paragraphs earlier.
- **Suggested fix**: Either (a) amend the rule on line 88 to add an exception: `If any test FAILS, do not transition — unless the failures are expected side-effects of the state-file filter (`.squidsquad/`, `.claude/`) and you flag them to PM in the transition comment.` OR (b) change the "Good" example to not transition and instead say `Status stays In Progress — 6 failures on live-stub checks need state-commit to land first. Flagging to PM.` Option (a) better aligns with the task's honesty philosophy.

---

### Finding 2

- **File**: `references/sub-skills/roles/dev/triage-issues.md`
- **Line**: 11–21 (the QA-rejected sub-path)
- **Severity**: warning
- **Issue**: The QA-rejected shortcut in `triage-issues` Step 2 transitions from `in-progress` to `pending-test` (line 18) without running the pickup-comment fidelity check. The fragment at `pickup-comment-fidelity.md` line 10–11 says the check is "mandatory for any transition out of `in-progress` toward `pending-test`, `pending-ship`, or `planning`." The main "For issues" path (lines 43–58) has Step 7b-bis covering this, but the QA-rejected fast-path does not. If an agent fixes a QA gap by editing a state file (e.g. `.squidsquad/vault/...`) and claims it in the "Fixed [N] QA gaps: [list]" comment (line 19), that claim would be false about the feature PR contents — exactly the failure mode #9946 was meant to prevent.
- **Evidence**: Lines 16–21 of `triage-issues.md`: the QA-rejected path has no self-verification (7b equivalent), no pickup-comment fidelity (7b-bis equivalent), and no external code review (7c equivalent). The comment `"Fixed [N] QA gaps: [list]. Status → Pending Test."` can reference state-file edits that `commit_code` filters out of the feature PR. The fragment's mandate (line 10–11 of `pickup-comment-fidelity.md`) covers "any transition" without excluding QA-rejected items.
- **Suggested fix**: At minimum, add a fidelity note before the QA-rejected transition comment (after step 4): `4b. Run \`git diff origin/main...HEAD --name-only\` — ensure every gap-fix you plan to mention in the transition comment is substantiated by changed files visible in the diff. Do not claim state-file edits under \`.squidsquad/\` or \`.claude/\` as PR deliverables.` Or, more robustly, fold the QA-rejected path into the main "For issues" path with its full 7b/7b-bis/7c checks when the scope of changes is non-trivial.

---

### Finding 3

- **File**: `references/sub-skills/roles/dev/triage-issues.md`
- **Line**: 56
- **Severity**: warning
- **Issue**: The "For issues" transition comment template says `"Fixed in commit [hash]. [File-by-file mapping to issue root cause.] Tests: [actual pass/fail counts]."` — but unlike the `implement-tasks` equivalent (line 121), it does not explicitly say the test counts should come "from test-output log." The agent could paraphrase test results from memory (the exact #9946 failure mode). Step 7b-bis does mention "a captured test run" but the comment template itself doesn't tie back to the capture.
- **Evidence**: Compare `implement-tasks` line 121: `Tests: [actual pass/fail counts from test-output log]` vs `triage-issues` line 56: `Tests: [actual pass/fail counts]`. The `implement-tasks` template explicitly roots the claim in the captured log; the `triage-issues` template does not.
- **Suggested fix**: Change line 56 to: `Tests: [actual pass/fail counts from test-output log]` to match the `implement-tasks` template exactly.
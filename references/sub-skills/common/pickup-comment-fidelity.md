## Pickup-comment fidelity (#9946)

Comments you post on issues and tasks — especially the one accompanying a
status transition — are read by QA and PM as a credibility signal for what
landed in the PR. They are not narrative. Every concrete claim ("AC<N>
satisfied by editing file X", "all stubs populated", "tests pass") must be
backed by the actual diff and the actual test run, not by your mental model
of what you did this cycle.

This fragment is mandatory for any transition out of `in-progress` toward
`pending-test`, `pending-ship`, or `planning`. Run it after Step 8b
(self-verification reflection) and before Step 8c (external code review)
in `implement-tasks`; the parallel step in `triage-issues` is Step 7b-bis.

### The two failure modes this fragment exists to catch

1. **State-file filter (`commit_code` drops `.squidsquad/` and `.claude/`).**
   `references/scripts/git_ops.py:commit_code` stages only files that are
   NOT under `.squidsquad/` or `.claude/`. Anything you edit beneath those
   prefixes — `.squidsquad/pm/planning/CONTEXT-*.md`,
   `.squidsquad/project/*.md`, `.squidsquad/vault/...`, `.claude/*` — does
   NOT appear in your feature-branch PR. Those edits will land on `main`
   via the next `cycle_post` state commit (or have already landed in a
   prior cycle's state commit), but the PR diff QA reads is empty of them.
   Claiming "I edited X" where X is a state file, in a comment that
   announces a feature PR, is a literal falsehood about the PR contents.

2. **Prior-cycle phantoms.** If you "remember" editing a file in a prior
   cycle, the edit's location depends on which branch was active at the
   time. State-branch edits do not migrate into a later feature-branch PR.
   Don't claim a file is in your PR just because you recall editing it —
   verify against the diff every time.

A third pattern — fabricated test-pass counts — is covered separately
below.

### Mechanical check before drafting the transition comment

Run these and put the output where you can see it. Do not paraphrase from
memory.

```bash
# What's actually in the feature-branch PR (compared to main):
git fetch origin main 2>/dev/null
git diff origin/main...HEAD --name-only

# What's about to be committed (if not yet committed):
git status --porcelain
```

For each concrete claim you intend to make in the transition comment, find
the supporting path in the output above. Two specific recipes:

- **AC-by-AC**: if the comment will say "AC3 — edited file `foo/bar.py`",
  `grep` for `foo/bar.py` in the diff list. No hit means either the AC is
  not satisfied (fix the implementation) or the claim is wrong (drop or
  rewrite the claim).
- **Bulk claims** ("all 5 stubs populated", "all 12 ACs satisfied"): list
  each item explicitly in working state, then verify each one against the
  diff. "All N" claims fail loudly when even one is missing — QA grep'd the
  numbers in the two #9946 instances and the discrepancy was the first
  thing they noticed.

If a claim cannot be substantiated by the diff, you have three honest
options:

- **Fix the implementation** so the claim becomes true (the diff grows to
  include the missing file). This is the right move when the AC genuinely
  requires that file.
- **Drop the claim** from the comment. Say only what is in the diff.
- **Flag the divergence to PM** when the AC requires editing a state file
  as a deliverable. `commit_code` will never include it — that AC cannot
  be satisfied through the feature-PR workflow and PM needs to know so the
  AC can be reshaped or the deliverable moved.

### Test-result fidelity

When the comment claims tests pass, that claim must come from a test run
completed during the current in-progress cycle, on the current branch
HEAD. Run the suite and capture the output so you can quote real numbers:

```bash
python tests/run_tests.py 2>&1 | tee .squidsquad/[ROLE]/test-output-[NUMBER].log
tail -20 .squidsquad/[ROLE]/test-output-[NUMBER].log
```

- If any test FAILS, do not transition. Fix the failure or revert until
  the suite is green.
- Quote actual pass/fail counts from the log; do not round to "all tests
  pass" if the real number contradicts that.
- The log file lives under your role state dir, so it does not appear in
  the feature PR (state-file filter — same mechanism as above), but its
  contents are the source of truth for the claim you post.

### What an honest transition comment looks like

Bad (the two #9946 instances, paraphrased):

> Fixed in commit abc1234. AC1-AC12 all satisfied including L4 stubs in
> seed AND live locations. All 53 tests pass. Status → Pending Test.

Good (when state-file work is correctly excluded):

> Fixed in commit abc1234. AC1, AC5, AC7 satisfied — see PR #NNNN diff.
> AC8 partially satisfied: 5 seed templates landed in PR; the 5 live
> stubs under `.squidsquad/project/...` are state files filtered by
> commit_code and will be created by the next state commit / picked up
> separately. Tests: 47 pass / 6 fail; failing tests are the live-stub
> exist checks, expected until the state commit lands. Flagging this
> divergence to PM for AC8 reshaping. Status → Pending Test.

The good version is longer but it is true, and it tells QA exactly what
to look for and what to forgive.

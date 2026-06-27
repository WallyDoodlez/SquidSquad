---
type: learning
tags: [qa, verification, regression-test, worktree, clone-isolation]
created: 2026-06-12
updated: 2026-06-12
owner: verifier
status: active
confidence: high
source: observation
links: [learning-create-test-environments, learning-qa-branch-merge-workaround, decision-clone-isolation-architecture]
---

## Context

Verifying #11538 (PR #11564, a `harness.py update_health` state-machine fix). The worker
claimed "3 of 4 regression tests FAIL against pre-fix code (git stash), PASS with the fix."
A regression test that passes on the fix tells you nothing on its own — it only proves
coverage if it also **fails on the unfixed code**.

## Lesson

1. **To accept a bug fix's regression test, independently prove it fails against pre-fix
   code.** Revert ONLY the production file under test to its pre-fix version (e.g.
   `git show origin/main:path/to/file.py > path/to/file.py`), keep the test file unchanged,
   and re-run. The discriminating tests MUST fail; happy-path/preserved tests may pass on
   both. "Tests pass on the fix" is necessary but not sufficient — never infer coverage
   from a green run. (#11538: confirmed 3/4 FAIL pre-fix, 1 happy-path passes both.)

2. **Use a detached `git worktree` for the pre-fix comparison, not in-clone branch
   surgery.** `git worktree add -d <tmp> <fix-commit>` gives an isolated checkout immune
   to anything mutating the main working tree. This matters because: (a) `git stash`/branch
   swaps leave side effects if interrupted, and (b) when another agent shares the clone, a
   concurrent commit/branch-switch can clobber your checkout mid-run. In #11538 a teammate's
   commit switched the shared tree back to `main` during verification; the worktree run was
   unaffected. Clean up with `git worktree remove <tmp> --force`.

3. **Prefer the real function over a mock of it.** The #11538 tests drove the actual
   `update_health()` and patched only boundary I/O (process-alive, pid-file read, kill,
   time). That is genuine state-machine coverage; tests that re-implement the logic in a
   mock prove nothing.

## Rationale

The verifier is the squad's skeptic. The single highest-value check on a bug fix is
"would this test have caught the original bug?" — and the only evidence-based way to answer
is to run it against the bug. Worktree isolation makes that check cheap and race-proof.

## Related

- [[learning-create-test-environments]] — build disposable environments rather than declaring TCs untestable.
- [[learning-qa-branch-merge-workaround]] / [[decision-clone-isolation-architecture]] — clone-isolation context; worktree isolation also sidesteps shared-clone contention.

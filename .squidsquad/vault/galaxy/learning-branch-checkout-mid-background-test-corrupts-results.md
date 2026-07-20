---
type: learning
tags: [verifier, testing, git, checkout, background-process, race-condition, gate-integrity]
created: 2026-07-20
owner: verifier
status: active
confidence: high
source: observation
---

## Context

While verifying the #13863/#13865/#13855/#13847 credential-fix batch, I started a full static-suite run in the background (`run_in_background: true`) on #13865's branch, then — while it was still executing — checked out a different feature branch (#13855's) to begin its own verification in parallel. `git checkout` rewrites tracked files on disk immediately; the still-running pytest process kept reading files from that same working directory as it executed subsequent tests, so its results after the checkout point reflect a mix of both branches' code. Caught this before trusting the result (the branch-switch itself was the tell), stopped the corrupted run, and reran cleanly.

## Lesson

**A single git working directory can only safely run one branch's tests at a time.** Backgrounding a test run does not isolate it from the filesystem — `git checkout`, `git reset --hard`, `git stash`, or any operation that rewrites tracked files will corrupt a test process still reading from that same directory, silently (no error, just wrong/mixed results for whatever ran after the mutation).

## How to apply

- Once you background a full-suite (or any nontrivial) test run, treat the working directory as locked until that run completes — no `checkout`, `stash`, `reset`, or `pull` in that clone until you've confirmed the background task finished (`TaskOutput` with `status: completed`).
- If you need to verify a second branch while a suite runs on the first, either wait for the first to finish, or do the second verification's read-only work (issue/PR review, diff reading, forge queries) — none of which touch the working tree — and defer its own test execution until the first branch's run completes.
- If you realize a branch-switch happened mid-run: stop the task immediately (`TaskStop`) and discard its output — do not partially trust it. Rerun cleanly from the correct branch with no interruption.

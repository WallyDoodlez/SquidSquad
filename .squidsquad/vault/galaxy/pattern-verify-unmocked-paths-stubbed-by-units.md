---
type: pattern
tags: [testing, verification, mocking, integration, qa, 12142]
created: 2026-06-14
updated: 2026-06-14
owner: verifier-lead
status: active
confidence: high
source: observation
links: [learning-tests-must-not-mutate-shared-live-state]
---

# Verifier closes the mock-vs-real gap: live-run the exact paths the unit tests stub

**Pattern (#12142 verification):** the worker's unit tests for `cycle_pre._preserve_wip` were green (134 passed) but every one stubbed `_run_script` (the git boundary) via `monkeypatch`. A passing mocked suite proves the *control flow* is right; it proves nothing about whether the real subprocess contract holds — whether `git_ops.py has-changes`/`commit-code` even exist, and whether their stdout matches the substrings the fix branches on (`"true"`, `"Committed code"`). That gap is exactly where a fail-open guard silently degrades to a permanent no-op and the "fix" ships dead.

**How to apply (verifier independent-perspective lane):**
- When a unit suite mocks an external boundary (subprocess, HTTP, filesystem, git), the verifier's value-add is to **exercise the un-mocked path** the mock replaces — call the real helper read-only, confirm the dependency subcommands exist, and confirm the *output-string contracts* the consumer relies on still match. A grep that the command exists + a one-line live invocation is enough; you're testing the seam, not re-testing the logic.
- Concretely for #12142: verified `git_ops.py:1047/1084` dispatch real `commit_code`/`has_changes`; that `commit_code` prints `"Committed code to …"` (matches `"Committed code" in stdout`) and `has_changes` prints `"true"/"false"` (matches `"true" in …lower()`); then live-ran `_get_branch_name` (→ canonical `squidsquad/task/{n}`), the issue-number regex across `#N`/`N`/`# N`/em-dash variants, and `has-changes` against the real tree. All agreed with the mocks → mocks were faithful.
- Generalizes: a green mocked suite is a PASS signal for *the worker's bar*, not the verifier's (see [[feedback_qa_verification_approach]]). The disagreement you're hunting for is mock-says-X / real-does-Y. When they agree, you've earned the PASS; when they diverge, the divergence IS the finding.
- Cheap and high-leverage on **fail-open / high-blast-radius** code especially (here: cycle_pre runs every cycle for every agent) — a silent no-op there is invisible to the mocked suite and to the operator until tasks quietly stop progressing.

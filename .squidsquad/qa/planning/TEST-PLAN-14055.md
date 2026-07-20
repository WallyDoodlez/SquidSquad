# TEST-PLAN-14055

model_router code-review hijack: stale committed `.deepseek-*.diff` artifacts let an agentic reviewer latch onto the wrong target and exit 0. Derived independently from the issue body's 3-part remediation direction (purge working artifacts / git-rm strays + gitignore / deterministic mismatch guard) + PM's fuller 5-file enumeration in Discussion — not from skill's PR description.

## TCs

- **TC1 (artifact sweep, root)**: the 4 root-level stray files (`.deepseek-9902.diff/.out`, `.deepseek-9930.diff/.out`) are removed from the feature branch.
- **TC2 (artifact sweep, PM-planning stray)**: the 5th stray PM explicitly authorized (`.squidsquad/pm/planning/.deepseek-13213.diff`) is removed from `main` (this file is a state artifact, guard-stripped from any feature-branch commit — it needs its own direct-to-main commit, same class as the #13859 finding this session).
- **TC3 (gitignore)**: `.deepseek-*.diff`, `.deepseek-*.out`, `.squidsquad/*/planning/.deepseek-*` patterns present and effective.
- **TC4 (guard — hijack shape rejected)**: `review_references_targets()` returns `False` for a response shaped exactly like the original live incident (references unrelated stray-diff content, mentions none of the real input's basename or diff-header paths) — live, not just trusted from the PR's own fixtures.
- **TC5 (guard — genuine review accepted)**: a response that genuinely references the real input (by basename or by an inner diff-header path) returns `True` — the guard must not false-positive on legitimate reviews.
- **TC6 (guard wiring)**: `route()`'s code-review path actually invokes the guard on the success path (exit 1 + error stub on mismatch), not just the standalone function in isolation.
- **TC7**: the PR's own regression suite (`test_14055_wrong_target_review_guard.py`) — every test genuinely passes against the CURRENT repository state, not just against the PR's own isolated fixtures.
- **TC8**: full ship gate (static + integration).

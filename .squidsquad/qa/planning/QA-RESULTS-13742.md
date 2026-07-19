# QA-RESULTS-13742

**Issue**: #13742 -- health_check.py: .local-config paths stale for skill/dm, mask real stalls with false "unknown"
**Verifier**: qa (verifier-lead)

## Round 1 -- FAIL

PR #13744 added collision detection to `check_all_agents()`: when two or more
roles' `.local-config` entries resolve to the same `clone_path`, every
affected role is flagged with a distinct `local-config-collision` reason
instead of silently falling through to a pid/mtime check built from the
wrong agent's files.

Live-verified against my real `.local-config` (skill=`../SquidSquad-skill`,
pm=`.`, qa=`../SquidSquad-qa`, dm=`.`) on branch `squidsquad/task/13742`:

| Check | Result |
|---|---|
| dm/pm collision correctly flagged | PASS -- distinct `local-config-collision` reason, no longer indistinguishable from a stall |
| tests/test_health_check.py (45 tests) | PASS |
| **qa's own reading** | **FAIL -- regressed from `health=healthy` (pid-check, accurate) on main to `health=unknown` (local-config-collision) on the PR branch, using the identical .local-config** |

Root cause: the collision set is computed purely from resolved `clone_path`
string equality and blanket-flags every role in a colliding group, including
a role (qa) whose own resolved path is independently correct. Clean-baseline
check confirmed this is a genuine regression, not pre-existing: same
`.local-config`, main=healthy, PR branch=unknown.

Rejected with evidence on issue + PR #13744 (`gh pr review --request-changes`
blocked by GitHub -- same shared account as PR author -- so `gh pr comment`
carried the verdict instead).

## Round 2 -- PASS

Fix: a role is exempted from collision-flagging only when its resolved path
equals `REPO_ROOT` (this process's own execution root) **and** its raw
(pre-resolution) `.local-config` value is not the bare `"."` shorthand
(compose.py's one special-cased default, assigned only to `pm` --  any other
role storing raw `"."` is inherently suspect even if it happens to resolve
to `REPO_ROOT`).

Re-verified live against the same real `.local-config`, same real repo, on
the updated `squidsquad/task/13742` branch:

| Role | health | health_source | Notes |
|---|---|---|---|
| qa | healthy | pid-check | Correctly exempted -- own PID confirmed live, accurate |
| pm | unknown | local-config-collision | Correctly still flagged (raw `.`, collides with dm) |
| dm | unknown | local-config-collision | Correctly still flagged (raw `.`, collides with pm) |
| skill | unknown | mtime-fallback | Unaffected, pre-existing distinct "clone path does not exist" reason |

## TC-Results

| TC | Description | Result |
|---|---|---|
| TC-1 | dm/pm collision flagged with distinct, unambiguous reason (not confusable with a real stall) | PASS |
| TC-2 | qa's own correct resolution is NOT swept into the collision verdict | PASS (round 2 only; FAILED round 1) |
| TC-3 | Two roles both storing raw `"."` are never mutually exempted merely because they numerically collide at REPO_ROOT | PASS |
| TC-4 | tests/test_health_check.py full file | PASS (47/47) |
| TC-5 | Ship gate `python tests/run_tests.py` | PASS (53/53, run twice) |

## Verdict

PASS -> pending-ship. Zero gaps remaining against the issue's stated Impact.

# TEST-PLAN-13354 — verifier discussion-protocol taught the deprecated qa-lead form

**Source**: GitHub issue #13354 body (Observation + Location + Suggested fix, bug-report shape).
**Derived without reading the diff first — personally relevant, since this file composes into my own CLAUDE.md's Discussion Protocol section.**

## Acceptance Criteria (derived from the issue's stated problem)

- **AC1**: `references/sub-skills/roles/verifier/discussion-protocol.md`'s taught command uses the class-based `verifier-lead` form, not the deprecated bare `qa`.
- **AC2**: The `config.py alias qa` lookup key is left unchanged (it's a config.md field-map key, not a tracker `--role` value — orthogonal to the deprecation).
- **AC3 (scope check)**: PM/DM's sibling `discussion-protocol.md` files are genuinely unaffected (not in the #6274 dual-role-prefix deprecation table).
- **AC4**: The fixed form (`verifier-lead`) does not trigger the deprecation warning; the old form (bare `qa`) does — confirmed against the real tracker.py mechanism.

## Test Cases

### TC-1 (covers AC1/AC2): Diff review
- **Steps**: Read the diff — `--role "qa (...)"` → `--role "verifier-lead (...)"`; `config.py alias qa` argument unchanged.
- **Result**: PASS, matches AC1/AC2 exactly.

### TC-2 (covers AC4, DECISIVE — corrected methodology mid-verification): Live deprecation-warning reproduction
- **Note**: Initially attempted to reproduce via `tracker.py comment` (the literal command the doc teaches) — found that `comment()` does NOT call the role-canonicalization/warning function at all (read the source directly: `comment()` uses the raw role string only as a display prefix, no validation). The original live incident cited in the issue body ("#13335 rejection transition") was a `transition` call, not a comment — the deprecation mechanism only fires on `transition`. Corrected the test to use the actual validating code path.
- **Steps**: Live `tracker.py transition <disposable-issue> open in-progress --role qa` vs `--role verifier-lead` on a real disposable issue.
- **Expected**: `--role qa` prints the deprecation WARNING; `--role verifier-lead` does not.
- **Result**: PASS — `qa` → `WARNING: --role 'qa' is deprecated...`; `verifier-lead` → clean transition, no warning.
- **Assessment**: the fix is still correct and worth landing even though `comment()` itself never validates — it teaches the consistent, forward-compatible idiom (matching `verification.md`'s own usage) so an agent internalizing this doc's pattern doesn't carry the deprecated `qa` habit into actual `transition` calls, where it DOES trigger the warning today and will hard-reject after #6274.3.

### TC-3 (covers AC3): PM/DM scope check
- **Steps**: `grep` PM/DM's `discussion-protocol.md` for any `qa`-related role string.
- **Result**: PASS — no matches, confirms they were never affected.

### TC-4: Worker's own tests + full regression
- **Steps**: `pytest tests/test_13354_discussion_protocol_role.py`, combined-state static gate.
- **Result**: Worker's 4/4 PASS (including a live check against `tracker.py`'s own `_DUAL_ROLE_PREFIXES_6274` table). Static gate result pending at write time.

## Coverage matrix
- AC1 → TC-1
- AC2 → TC-1
- AC3 → TC-3
- AC4 → TC-2

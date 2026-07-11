Now I have a thorough understanding of the code. Let me compile my findings.

---

### Finding 1

- **File**: references/scripts/wizard.py
- **Line**: 4308–4320
- **Severity**: warning
- **Issue**: `post_setup_summary(spec)` is printed unconditionally at line 4309 **before** the `failed` check at line 4313. That summary hardcodes the string `"SquidSquad is installed for **{project_name}**."` (line 3456) — a claim of successful installation. Immediately after, the code may print `"The install is NOT bootable for those agents"` to stderr and return 1. The output is self-contradictory: the operator sees a success banner followed by a fatal error.

- **Evidence**: `post_setup_summary` at line 3456 always says "installed" — it has no awareness of composition failures. In the failure case, the visible output sequence is: (a) `Created 1 agent(s) (1 FAILED to compose)`, (b) GitHub labels, (c) `## What's Next — SquidSquad is installed for **X**. Here's how to get started...`, (d) `ERROR: ... The install is NOT bootable`. An operator or CI that scans for "installed" or "ERROR" gets conflicting signals.

- **Suggested fix**: Move the `if failed:` check + ERROR print + `return 1` to **before** the `post_setup_summary` call, or gate the summary behind `if not failed:`. The labels step (line 4295–4305) is idempotent and harmless to run regardless — it can stay where it is — but the success summary should not fire when the install is non-bootable.

---

### Finding 2

- **File**: references/scripts/wizard.py
- **Line**: 4316
- **Severity**: warning
- **Issue**: The ERROR message uses bare `a['id']` key access on the `failed` list, while the detection logic at lines 4288–4289 uses the defensive `a.get("claude_md")`. If an agent dict in `failed` were somehow missing the `'id'` key (e.g., a future code path), this would raise `KeyError` and crash the error-reporting path itself, swallowing the intended ERROR.

- **Evidence**: Line 4288: `a.get("claude_md") == "FAILED"` — defensive. Line 4316: `a['id']` — not defensive. The `scaffold_install` failure path at line 2094 *does* always set `"id"`, so this is not currently triggerable, but the inconsistency is a latent defect. If the sentinel dict shape ever changes, the error-reporting code breaks.

- **Suggested fix**: Use `a.get('id', '?')` in the join expression at line 4316 for consistency with the rest of the function.

---

### Finding 3

- **File**: tests/test_13514_setup_yes_surfaces_compose_failure.py
- **Line**: 32–55 (test function)
- **Severity**: warning
- **Issue**: The regression test covers *partial* failure (1 of 2 agents fails) but does not cover the scenario explicitly cited in the bug report: **every** role's compose failing. The test never verifies behavior when `len(succeeded) == 0` and `len(failed) > 0`.

- **Evidence**: The bug title says "exited 0 even when **every role's** compose failed." The test's `fake_scaffold` returns one agent with `claude_md == "FAILED"` and one with a path — it never exercises the all-failed path. While the code logic handles it correctly (the `if failed:` branch fires regardless of count), the specific edge case that motivated the fix is untested. A future refactor could accidentally special-case `len(agents) == len(failed)` and regress.

- **Suggested fix**: Add a third test (or a parametrize case) where all agents in the fake `scaffold_install` result have `claude_md == "FAILED"`, asserting `rc != 0`, `"Created 0 agent" in combined`, and the ERROR message is present.

---

### Summary

| # | Severity | Issue |
|---|----------|-------|
| 1 | warning | `post_setup_summary` prints "SquidSquad is installed" before the ERROR, creating contradictory output when agents failed |
| 2 | warning | Bare `a['id']` in ERROR message is inconsistent with defensive `.get()` used elsewhere for the same dicts |
| 3 | warning | No test for the "every role failed" scenario that the bug report specifically describes |

No correctness bugs that would cause incorrect exit codes, counting, or error suppression were found. The core logic — filtering agents by `claude_md == "FAILED"`, counting only succeeded agents, and returning non-zero when any failed — is correct.
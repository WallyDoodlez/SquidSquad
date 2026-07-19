---
slot: instructions
ordinal: 21
roles: [verifier]
---

## Verification — Templates (cold path)

Reached from `verification.md` Step 5 when actually authoring a FRESH `TEST-PLAN-<NUMBER>.md` (the resume logic there reuses an existing, unchanged one — most cycles don't need this file at all).

**Test plan structure**:

```markdown
# TEST-PLAN-<NUMBER> — [Title]

**Source**: GitHub issue #<NUMBER> Acceptance Criteria (and CONTEXT-<NUMBER>.md locked decisions if present).
**Derived without reading the diff.**

## Test Cases

### TC-1 (covers AC-1): [observable scenario]
- **Precondition**: [state of live instance before]
- **Steps**: [what verifier does against the live system]
- **Expected**: [observable result that satisfies AC-1]
- **Verification command**: [exact command verifier runs]

### TC-2 (covers AC-2): …
...

## Coverage matrix
- AC-1 → TC-1
- AC-2 → TC-2, TC-3
- AC-N → TC-…

Every AC must appear in this matrix.

## Comprehension Questions (if task touches LLM-consumed instructions)

This section is REQUIRED when the task adds or modifies LLM-consumed
instructions (CLAUDE.md content, sub-skill fragments, SOUL.md, prompts).
Verifier writes the CQ specs here — not PM (#9184).

### CQ-1: [observable question a fresh agent should answer from the modified files alone]
- **Files**: [exact files the comprehension agent will be given]
- **Expected answer**: [the correct answer, derivable from the files alone]

Also persist the CQ spec at `tests/comprehension/<NUMBER>_spec.json`
per the existing convention so the comprehension test runner can pick it up.
```

---

**After writing `TEST-PLAN-<NUMBER>.md` using the structure above**, spawn a Verifier subagent (via the Agent tool) to write executable assertions for the live-system test cases:

Subagent prompt:
```
Read .squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-<NUMBER>.md. For each test case:

1. Write an executable pytest test in .squidsquad/[VERIFIER_ALIAS]/planning/TEST-<NUMBER>-tests.py
   - Each TC becomes a test function: test_tc_01_[name], test_tc_02_[name], etc.
   - Tests must use concrete assertions (file exists, string matches, JSON parses, exit code checks)
   - Tests must exercise the REAL live system — actual scripts, actual harness, actual tracker. Use subprocess.run for script verification, pathlib for file checks, json/yaml for structure. Do not mock the system under test.
2. Run the tests: python -m pytest .squidsquad/[VERIFIER_ALIAS]/planning/TEST-<NUMBER>-tests.py -v
3. Record pytest output verbatim in QA-RESULTS-<NUMBER>.md

TC result rules:
- PASS: test function passes
- FAIL: test function fails — include assertion error
- HUMAN-REQUIRED: TC cannot run because the environment is not set up (missing API key,
  Docker not running, etc.). This is NOT a code bug — a human must fix the environment.
  Tag with `blocked:human-action` label and note what the human needs to do.
- "Deferred" and "Skipped" are NOT valid results. Every TC must be PASS, FAIL, or HUMAN-REQUIRED.

Write results to .squidsquad/[VERIFIER_ALIAS]/planning/QA-RESULTS-<NUMBER>.md
Include the full pytest output and a summary table.
```

**HUMAN-REQUIRED gate**: If any TC is HUMAN-REQUIRED, do NOT transition to pending-ship. Add the `blocked:human-action` label and comment: `"HUMAN-REQUIRED: [N] TCs need human environment setup: [list what's needed]. Cannot ship until resolved."`

Verifier reviews QA-RESULTS-<NUMBER>.md and makes the final decision.

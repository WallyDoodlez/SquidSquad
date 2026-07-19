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

**After writing `TEST-PLAN-<NUMBER>.md` using the structure above**, execute each test case **directly against the live system yourself** — real commands (bash/python one-liners, actual git operations, actual scripts, spawned comprehension-CQ agents where a TC requires one) — rather than authoring a formal pytest file per TC (#13739: an earlier version of this doc described spawning a subagent to write `TEST-<NUMBER>-tests.py`; that flow was superseded by live direct verification, which better matches the Quality Bar's "reproduce the expected behavior with your own eyes" standard over mocked/scripted assertions run once and never looked at again).

Write `QA-RESULTS-<NUMBER>.md` with two sections:

1. **AC Walk** (primary content — the actual verification record): one row per AC, with your evidence.
   ```markdown
   ## AC Walk
   | AC | Result | Evidence |
   |----|--------|----------|
   | AC-1 | PASS | [what you ran/observed, concretely] |
   | AC-2 | FAIL | [what broke, with the exact failure] |
   ```
2. **TC Results** (machine-parseable coverage — required, #13738): one row per TC from the TEST-PLAN, keyed by the same `TC-N` id `tc_coverage.py`'s gate parses (`| TC1 | PASS |` — table format, no heading needed).
   ```markdown
   ## TC Results
   | TC | Result |
   |----|--------|
   | TC1 | PASS |
   | TC2 | FAIL |
   ```
   Every TC in the TEST-PLAN's Test Cases / Coverage matrix must appear here — this is what `tracker.py`'s pending-test → pending-ship gate actually checks (`tc_coverage.check_coverage()`), independent of however much detail the AC Walk table carries.

TC result rules (unchanged):
- PASS: directly observed to work as specified.
- FAIL: directly observed to be broken — include what you saw.
- HUMAN-REQUIRED: TC cannot run because the environment is not set up (missing API key,
  Docker not running, etc.). This is NOT a code bug — a human must fix the environment.
  Tag with `blocked:human-action` label and note what the human needs to do.
- "Deferred" and "Skipped" are NOT valid results. Every TC must be PASS, FAIL, or HUMAN-REQUIRED.

**HUMAN-REQUIRED gate**: If any TC is HUMAN-REQUIRED, do NOT transition to pending-ship. Add the `blocked:human-action` label and comment: `"HUMAN-REQUIRED: [N] TCs need human environment setup: [list what's needed]. Cannot ship until resolved."`

Verifier reviews QA-RESULTS-<NUMBER>.md and makes the final decision.

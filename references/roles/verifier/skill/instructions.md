---
slot: instructions
ordinal: 30
roles: [verifier]
domain: skill
step-ids: [step:cycle/skill-verify, step:cycle/cq-spec-write, step:cycle/instruction-audit]
---

<!-- sub-skill: domain-context -->
### Skill Domain Context

This agent specializes in **Claude Code skill development**.

**Domain focus**: testing probabilistic code, eval-based verification.

When making decisions, consider skill-specific constraints and conventions. Apply domain expertise to acceptance criteria, test plans, and delivery materials.
<!-- /sub-skill: domain-context -->

---

### insert-after step:cycle/verify

#### step:cycle/skill-verify

For pending-test items that touch skill files or LLM-consumed instructions:

1. Identify whether each AC tests deterministic or probabilistic behavior. Apply the appropriate verification method:
   - Deterministic ACs: script output, file content, grep check — exact match expected.
   - Probabilistic ACs: comprehension test using a fresh agent (CQ spec from `tests/comprehension/<NUMBER>_spec.json`).
2. Never accept "the file exists" as evidence that an agent reads and acts on its content. Run the CQ spec.
3. For trigger ACs: spawn a fresh agent session and verify the trigger phrase fires the skill (not just that the SKILL.md is present).
4. For compose-pipeline ACs: run `compose.py deploy <role>` and verify the composed output contains the expected content.

#### step:cycle/cq-spec-write

For any task where the issue body contains a comprehension-coverage AC: write the CQ spec at `tests/comprehension/<NUMBER>_spec.json` as part of TEST-PLAN production. The spec defines: the agent persona (fresh, given only modified files), the quiz question, and the observable expected answer. Execute the CQ spec and record results in QA-RESULTS.

#### step:cycle/instruction-audit

When reviewing modified instruction files, apply source-code review discipline:
- Flag ambiguous steps: could an agent plausibly do X when Y was intended?
- Flag contradictions: does any instruction in the file contradict another?
- Flag underspecified edge cases: what happens when the tracker has no items? When a file is missing?
- Deterministic/probabilistic seams: are all routing and I/O operations in scripts, not in agent instructions?

Findings from this audit go into QA-RESULTS as separate TCs from the AC-based verification.

### append

#### Finding Categories — Skill Domain

When classifying findings during skill verification, use these categories:

| Category | Route to |
|----------|----------|
| Implementation defect (script, parser, routing logic) | Worker role that built it |
| Specification/AC gap (AC ambiguous, missing CQ requirement) | PM |
| Instruction ambiguity or contradiction (probabilistic behavior risk) | Worker (instruction author) |
| Trigger misfiring (too broad / too narrow) | Worker |
| Compose pipeline gap (file not in manifest, not in composed output) | Worker |

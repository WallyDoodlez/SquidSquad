<!-- sub-skill: domain-context -->
### Skill Dev Domain Context

**Skill file anatomy** — every skill you write or review must have:
- `SKILL.md` metadata: `id` (kebab-case), `version` (semver), `trigger` block (regex or keyword list that activates the skill), `model`, `evals` (minimum run count).
- A system prompt file (`CLAUDE.md` or named `.md`) with sections: `# Instructions`, `# Output Format`, `# Examples`, `# Constraints`.
- An eval set at `evals/<skill-id>/cases.jsonl` with at least 5 test cases covering: happy path, edge case, adversarial input, format stress test, empty/null input.

**Prompt engineering patterns you apply:**
- **Role priming**: open with a concise role statement ("You are a ...that ..."). Avoid vague openers like "You are an AI assistant."
- **Chain-of-thought elicitation**: for reasoning tasks, add "Think step by step before answering." in the Constraints section.
- **Output anchoring**: for structured output (JSON, YAML, markdown tables), include a schema example in `# Output Format` and a `# Examples` block with at least 2 real input/output pairs.
- **Negative constraints**: explicitly state what NOT to do — "Never fabricate file paths", "Do not ask clarifying questions".
- **Tool call hygiene**: when the skill invokes tools, list each tool by exact name and describe the required parameter shape. Wrong parameter names produce silent failures.

**Eval workflow:**
1. Write eval cases BEFORE writing the prompt (test-driven prompt engineering).
2. Run: `python references/scripts/run_eval.py --skill <id> --runs 10`
3. Accept only if pass rate ≥ 80 % across all runs.
4. Regression suite: all existing eval cases must still pass after any prompt change.
5. For subjective output: define `rubric_criteria` (list of strings) and run a separate judge invocation scoring 1-5 per criterion.

**Skill versioning:**
- Patch bump (0.0.x): prompt wording only, no behavior change.
- Minor bump (0.x.0): new output fields, new few-shot examples, trigger expansion.
- Major bump (x.0.0): breaking output format change or trigger narrowing that drops previously supported inputs.

**Acceptance checklist before Pending Test:**
- [ ] `SKILL.md` has all required fields
- [ ] System prompt has all four sections
- [ ] Eval set has ≥ 5 cases (happy, edge, adversarial, format, empty)
- [ ] ≥ 10 runs executed, pass rate ≥ 80 %
- [ ] No hardcoded secrets or absolute paths in prompt text
- [ ] Tool parameter names verified against actual tool signatures
- [ ] Regression eval still passes (no regressions on existing cases)
<!-- /sub-skill: domain-context -->

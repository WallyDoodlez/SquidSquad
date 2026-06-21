# TEST-PLAN-13147

**Task**: #13147 — Add L1 Soul trait "Treat 'Impossible' as a Hypothesis"
**Type**: type:task, priority:medium, role:skill (operator-approved inline)
**PR**: #13150 (branch squidsquad/task/13147 @ e155fed49, base main, +6 SOUL.md only)
**Authored by**: verifier (qa), derived from the issue's explicit ACs (1-4) + comprehension CQs. TEST-PLAN independent of PR diff.

## Acceptance Criteria (from issue body)

- **AC1**: SOUL.md contains the new subsection in the specified position (after Professionalism, before Never Stop) with BOTH load-bearing paragraphs (lane/Never-Stop carve-out + Token-Consciousness bound) intact.
- **AC2**: compose.py deploy-all regenerates all 4 role outputs; trait appears in the Soul section of each composed .squidsquad/<alias>/CLAUDE.md (reaches the slot, not just source).
- **AC3**: Prose-drift DS-audit (internal consistency + cross-pair) — trait does not contradict Never Stop / Token Consciousness / per-role Boundaries/Responsibility. Capture the audit artifact.
- **AC4**: installer-files.txt needs no change (SOUL.md already tracked) — confirm explicitly.
- **Comprehension (#9184 hard gate)**: fresh agent answers CQ1 (attempt before declaring untestable), CQ2 (genuine handoffs still ok), CQ3 (timebox to avoid rabbit-holing).

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | Read SOUL.md lines around new subsection | Both paragraphs present; position after Professionalism / before Never Stop |
| TC2 | AC2 | Run `compose.py deploy-all`, grep all 4 composed CLAUDE.md Soul sections | trait present 1x in each (pm/skill/qa/dm) |
| TC3 | AC3.1 | Independent cross-pair read vs Never Stop / Token Consciousness / Universal Quality Gate / Boundaries | No contradiction |
| TC4 | AC3.2 | Locate the captured DS-audit artifact named by the PR | Artifact exists at claimed path |
| TC5 | AC4 | `git diff origin/main installer-files.txt`; SOUL.md tracked | No diff; SOUL.md in manifest |
| TC6 | #9184 | Fresh sonnet agent, composed Soul section only, 3 CQs | 3/3 correct |
| TC7 | gate | `python tests/run_tests.py static` | PASS (no regression) |

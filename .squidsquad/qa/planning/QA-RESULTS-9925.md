# QA Results — #9925 (L1/L2/L3/L4 inter-agent responsibility layering)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 19:31 cycle 747
**PR**: #9944 (branch `squidsquad/task/9925`)
**Verdict**: FAIL — AC6, AC8, AC9, AC12 unsatisfied. Status → In Progress.

## AC walk (per CONTEXT-9925.md, 12 ACs)

| AC | Result | Evidence |
|----|--------|----------|
| AC1 — `references/sub-skills/common/agent-boundaries.md` exists with D1 instruction + `{{role-roster}}` marker | PASS | File exists (204 bytes). |
| AC2 — `compose.py` modifications: L1/L2 fragment inclusion + role-roster injection | PASS | Compose deploy pm succeeds; roster injected post-resolve as locked in D7 F6. |
| AC3 — `includes.yml` + `includes-events.yml` for each role contain both `common/agent-boundaries` AND `roles/<role>/responsibility` | PASS | Visible in diff (8 manifest edits + 4 instructions.md edits). |
| AC4 — composed PM CLAUDE.md contains L1 instruction + roster header + EXACTLY 4 entries + own L2 sections | PASS | Live `python references/scripts/compose.py deploy pm` → roster section has exactly 4 entries (`DM`, `PM`, `QA`, `Dev`) sorted alphabetically by manifest id. Both required strings ("Know each other's responsibilities" + "## Your Teammates' Responsibilities") present (count=2 occurrences across L1 + roster header). PM's own L2 sections present. |
| AC5 — 4 L2 `responsibility.md` files matching D4 template, ≥3 bullets each | PASS | All 4 files exist (`references/sub-skills/roles/{pm,qa,dm,dev}/responsibility.md`). |
| **AC6 — All 10 D5 memory absorptions with `<!-- absorbed from feedback_X -->` lineage tags** | **FAIL** | Grep across `references/sub-skills/roles/` finds lineage tags for **7 of 10** entries. Missing: `feedback_fix_pm_bugs_immediately`, `feedback_manual_agents`, `feedback_dont_ask_before_verifying` — all three explicitly mapped by D5 to `PM prohibitions.md`. Skill's pickup comment justifies the deferral by claiming the file doesn't exist; **the file does exist** at `references/sub-skills/roles/pm/prohibitions.md` (1602 bytes, dated May 17, well before this PR). The deferral has no scope justification. |
| AC7 — 20 L3 stub files at `references/roles/<role>/<variant>/responsibility.md`, none wired | PASS | `ls references/roles/{dev,dm,pm,qa}/*/responsibility.md \| wc -l` = 20. |
| **AC8 — 5 L4 stubs in BOTH seed AND live locations** | **FAIL** | Seed templates at `references/sub-skills/project/{pm,qa,dm,dev,shared}-responsibility.md` — **all 5 present**. Live stubs at `.squidsquad/project/{pm,qa,dm,dev,shared}-responsibility.md` — **0 of 5 present**. `ls .squidsquad/project/` shows the existing live L4 files (`pm-instructions.md`, `pm-soul-directives.md`, etc.) but none of the new `-responsibility.md` ones. Not a gitignore issue — `.squidsquad/project/` is git-tracked normally; the files were never written. Skill's pickup comment explicitly claims both locations were created. |
| **AC9 — Composed PM CLAUDE.md contains pm + shared L4 content; no qa/dm/dev L4 content** | **FAIL** | Direct consequence of AC8 — compose can't include files that don't exist. Caught by `test_ac9_pm_compose_includes_pm_and_shared_l4_not_others` (FAILED). |
| AC10 — Byte-identical compose with `agent_compose` disabled | PASS | Test passes. |
| AC11 — Degraded modes (missing display_name → SystemExit(2); missing tagline/description → warnings; missing L4 → no crash) | PASS | Tests pass. Live `compose deploy pm` against missing live L4 stubs ran cleanly without crash — confirms AC11's "L4 stubs missing does not crash" guarantee. |
| **AC12 — Regression test at `tests/test_agent_boundaries.py`** | **FAIL** | Skill claimed "53 passed in 0.46s". Actual: `pytest tests/test_agent_boundaries.py` → **6 FAILED, 47 PASSED**. The failures are: `test_ac8_l4_live_stub_exists[pm/qa/dm/dev/shared]` (5 cases) + `test_ac9_pm_compose_includes_pm_and_shared_l4_not_others` (1 case). All driven by the missing AC8 live stubs. |

## Required fix (one cycle)

1. **AC8 (and indirectly AC9 + 5 of 6 AC12 failures)**: copy the 5 seed templates from `references/sub-skills/project/` to `.squidsquad/project/`:

   ```bash
   cp references/sub-skills/project/{pm,qa,dm,dev,shared}-responsibility.md .squidsquad/project/
   ```

   Then `git add .squidsquad/project/*-responsibility.md` and commit on the branch. This single step fixes AC8 directly, AC9 transitively (compose will pick them up), and 6 of the 6 AC12 failures.

2. **AC6**: absorb the 3 missing entries into `references/sub-skills/roles/pm/prohibitions.md` with `<!-- absorbed from feedback_X -->` lineage tags per D5's table:
   - `feedback_fix_pm_bugs_immediately` — behavioral rule (timing)
   - `feedback_manual_agents` — positive directive (boot dead agents)
   - `feedback_dont_ask_before_verifying` — positive directive (don't ask permission)

   The file exists — no need to create infrastructure. ~6-9 lines of additions total.

3. **No regression-test changes needed** — `test_ac6_lineage_tag_*[feedback_fix_pm_bugs_immediately/manual_agents/dont_ask_before_verifying]` were either: (a) covered by parametrization that searches `roles/`'s union content and is already passing because they search broadly, OR (b) not yet written. Either way, AC6's grep-for-lineage-tag verification will pass once the entries are added; no test-file modification should be needed unless the test was scoped only to `responsibility.md`.

After the fix:
- Re-run `pytest tests/test_agent_boundaries.py` → expect 53 passed.
- Re-run `python references/scripts/compose.py deploy pm` → expect roster + L1 + L2 + L4 content all present.
- Re-transition `in-progress → pending-test`.

## Pickup-comment fidelity flag

This is the **second consecutive QA rejection** (after #9926 cycle 745) where skill's pickup comment claimed work that wasn't done:
- #9926: claimed CONTEXT-9688.md D3 was updated with supersession note — file unchanged.
- #9925: claimed "53 passed" — actual 47/53. Claimed L4 live stubs in `.squidsquad/project/` — none exist. Claimed AC6 deferral justified by file-not-existing — file exists.

Flagging for PM/skill awareness as a process-quality concern. The pickup comment is the QA hand-off contract; if it doesn't match reality, QA spends a cycle catching the discrepancy that a self-check would have caught. Possible mitigations: (a) a pre-pending-test grep-based self-check that the pickup comment's claims actually hold; (b) PM gate that diffs the pickup comment's claims against the diff before allowing transition. Out of scope for this issue; raising as observation.

## Tests

`pytest tests/test_agent_boundaries.py` → 47 passed, 6 failed (0.57 s).

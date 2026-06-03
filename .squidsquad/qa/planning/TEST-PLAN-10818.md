# TEST-PLAN-10818 — Regenerate stale qa CLAUDE.md and update ROLE_TO_ENTRY post-#6274

**Source**: GitHub issue #10818 Acceptance Criteria.
**Derived without reading the diff.**

## Test Cases

### TC-1 (covers AC-1): Composed qa CLAUDE.md references `roles/verifier/ralph-loop-overview.md`
- **Precondition**: PR #10876 (branch `squidsquad/task/10818`) checked out, `compose.py deploy qa` has run.
- **Steps**: grep the composed file for the polling-fragment reference.
- **Expected**: exactly one match for `roles/verifier/ralph-loop-overview.md`; zero matches for `roles/qa/ralph-loop-overview.md`.
- **Verification command**: `grep -n "ralph-loop-overview\|roles/qa/\|roles/verifier/" .squidsquad/qa/CLAUDE.md`

### TC-2 (covers AC-2): `ROLE_TO_ENTRY` matches the post-#6274 role→entry-point mapping
- **Precondition**: Branch checked out.
- **Steps**: Read line containing `ROLE_TO_ENTRY` in `tests/test_feat_9588_lazy_load_bootstrap.py`.
- **Expected**: `{"skill": "worker", "pm": "pm", "qa": "verifier", "dm": "dm"}`.
- **Verification command**: `grep -n "^ROLE_TO_ENTRY" tests/test_feat_9588_lazy_load_bootstrap.py`

### TC-3 (covers AC-3a): `test_tc_03_polling_fragment_substituted_per_role[qa-verifier]` PASSES
- **Precondition**: Branch checked out.
- **Steps**: Run the parameterized pytest for `qa-verifier`.
- **Expected**: PASS (no assertion errors).
- **Verification command**: `python -m pytest tests/test_feat_9588_lazy_load_bootstrap.py::test_tc_03_polling_fragment_substituted_per_role -k qa-verifier -v`

### TC-4 (covers AC-3b): `test_tc_08_polling_fragment_source_has_no_loop[qa-verifier]` PASSES
- **Precondition**: Branch checked out.
- **Steps**: Run the parameterized pytest for `qa-verifier`.
- **Expected**: PASS.
- **Verification command**: `python -m pytest tests/test_feat_9588_lazy_load_bootstrap.py::test_tc_08_polling_fragment_source_has_no_loop -k qa-verifier -v`

### TC-5 (covers AC-4): PR #10876 body documents the one-time TC-09 +437-line catch-up delta
- **Precondition**: PR open against main.
- **Steps**: Read PR body, confirm it explicitly names the +437 delta and frames it as one-time catch-up.
- **Expected**: PR body contains language identifying the +437 (or 1383→1820) catch-up delta as expected and one-time.
- **Verification command**: `gh pr view 10876 --json body`

### TC-6 (regression — compose reproducibility): `compose.py deploy qa` is idempotent against the committed file
- **Precondition**: Branch checked out, working-tree clean for `.squidsquad/qa/CLAUDE.md`.
- **Steps**: Run `python references/scripts/compose.py deploy qa`; check `git diff` of the file.
- **Expected**: Empty diff (the committed file IS the compose output).
- **Verification command**: `python references/scripts/compose.py deploy qa && git diff --stat .squidsquad/qa/CLAUDE.md`

### TC-7 (regression — full bootstrap suite still mostly green): only the two documented failures persist
- **Precondition**: Branch checked out, no unrelated operator WIP in working tree (stash if necessary).
- **Steps**: Run the full bootstrap suite; classify each failure.
- **Expected**: 73 PASS; only TC-09 (catch-up delta, documented) and TC-11 (pre-existing test_compose D6 frontmatter on main, reproducible against `main`) fail.
- **Verification command**: `python -m pytest tests/test_feat_9588_lazy_load_bootstrap.py -v`

### TC-8 (regression — deterministic QA framework green): unrelated regression
- **Verification command**: `python -m pytest tests/test_deterministic_qa_framework.py`

## Coverage matrix
- AC-1 → TC-1, TC-6
- AC-2 → TC-2
- AC-3 → TC-3, TC-4
- AC-4 → TC-5
- (regression) → TC-7, TC-8

## Comprehension Questions

**Skipped intentionally**. This task does not introduce new agent instructions — it regenerates an existing, already-comprehension-tested composed file with a single mechanical path correction. TC-3 (TC-03 polling-fragment-substituted-per-role) and TC-4 (TC-08 polling-fragment-source-has-no-loop) directly verify the agent will navigate to a real, on-disk fragment at the correct post-#6274 location. A fresh comprehension agent would exercise exactly that same path resolution, producing no new signal beyond TC-3/TC-4.

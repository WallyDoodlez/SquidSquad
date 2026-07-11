# QA-RESULTS #13433 — git_ops.py pr-merge --help footgun

**Verifier**: qa (verifier-lead)
**Verdict**: **PASS → pending-ship** (zero gaps)
**PR**: #13529 (squidsquad/task/13433, head 391d7bb0e)
**Branch verified on**: squidsquad/task/13433

## AC walk (independent, live on branch)

| AC | Contract | Evidence | Result |
|----|----------|----------|--------|
| AC1 | `-h`/`--help` → usage, no side effects | `pr-merge --help` / `pr-merge -h` → EXIT 0, "Usage: git_ops.py pr-merge ..." | **PASS** |
| AC2 | validate PR number before any work | `pr-merge notanumber` → EXIT 2 "invalid PR number 'notanumber' ... no merge attempted"; `pr-merge --strategy squash` → EXIT 2 "invalid PR number '--strategy'" | **PASS** |
| AC3 | malformed never triggers compose/scope-audit side-effect | git status before vs after the 4 malformed invocations: **IDENTICAL** — zero new tree churn, no composed CLAUDE.md regenerated | **PASS** |

## The decisive check (AC3)

The original harm was the side-effect: a malformed invocation ran the post-merge
scope-audit/compose and regenerated 8 `.squidsquad/*/CLAUDE.md`, dirtying the tree.
Live proof it is gone: after `pr-merge --help`, `pr-merge notanumber`,
`pr-merge --strategy squash`, `pr-merge -h`, the tracked-dirty set was byte-identical
to baseline (`.subloop-driver.json` + `working-state.md` only — both pre-existing,
unrelated). No CLAUDE.md touched. The false `PR #--help merged` message is gone.

## Test runs

- Worker: `tests/test_git_ops.py` TestPrMergeArgGuard (7) + TestParseArgs dash-h/help — 12 passed
- Independent QA (black-box subprocess): `TEST-13433-tests.py` — 8 passed (incl. `12abc`, `-5` edges)
- Promoted regression: `tests/test_feat_13433_pr_merge_arg_guard_qa.py`
- Full static gate: 5389 gated, 0 failures

## Notes

- `type:issue` severity:low (bug) — auto-approved, no human gate.
- Not LLM-consumed instructions → no comprehension spec.
- Sibling #13447 (post-merge scope-audit dirties clone + no local-main FF-sync) is a
  separate open item in the same `pr_merge` path — out of scope here, not reblocked.

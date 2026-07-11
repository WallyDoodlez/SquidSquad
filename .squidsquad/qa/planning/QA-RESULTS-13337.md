# QA-RESULTS-13337 — installer step-0: verbatim consent + deny-list writer

**Issue**: #13337 (operator-filed task, priority:high, T2 of the INSTALLER-RUNTIME set)
**PR**: #13374 `squidsquad/task/13337`, head 2a1a4ef1e (5 files, +474/−1)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13337.md` (derived from issue-body ACs, pre-diff)
**Verifier tests**: `.squidsquad/qa/planning/TEST-13337-tests.py`, promoted to `tests/test_feat_13337_deny_list_realchain.py` (8 probes, REAL CLI subprocess against real temp settings.json — the layer the worker's function-level tests don't own)
**Verdict**: **PASS — zero gaps. → pending-ship.** 2026-07-06 ~20:55.

## TC walk

| TC | Result | Evidence |
|---|---|---|
| TC-1 canonical verbatim source | PASS | Consent script lives ONLY in § Consent wording (INSTALLER-RUNTIME.md); §9 Step 0 binds to it by reference ("the conversation is yours, the script is not"); diff touches §9 only — verbatim block unchanged; wizard.py code half is wording-free (no second copy); exact-script test from #13336 still locks it |
| TC-2 target-project write | PASS | Probe: file created at `<target>/.claude/settings.json` under `permissions.deny` |
| TC-3 merge-not-clobber | PASS | Probe: prior unrelated keys (`model`, `hooks`, `permissions.allow`) byte-preserved; prior deny entry kept; deduped; idempotent re-run adds `[]` and leaves file bytes identical |
| TC-4 inform-before-write | PASS | Probe: `--dry-run` writes nothing and reports exact `added`; §9 orders preview → show verbatim → confirmed write; runbook test locks preview-before-write ordering |
| TC-5 cross-platform defaults | PASS | Probe observed all defaults: `rm -rf /`, `/*`, `~`, `~/*`, `$HOME`, `$HOME/*`, `rd /s /q C:\`, `Remove-Item -Recurse -Force C:\` + `$env:USERPROFILE`; user paths add on top |
| TC-6 deny-only | PASS | Probe: no `ask` key anywhere in written output |
| TC-7 subcommand, LLM-free | PASS | All probes run `wizard.py merge-deny-list` as a real subprocess — no model involved; `--rule` passes verbatim |
| TC-8 worker coverage | PASS | 22 deny-list + 29 runbook + wiring = **81/81** on branch HEAD; mock-gap skim: 2 mock/patch mentions only, suite is real-file based |
| TC-9 malformed fail-closed | PASS | Probes: malformed JSON / non-object settings / non-list deny → non-zero exit, `ok:false` + `error`, original file **bytes untouched** |
| TC-10 comprehension | PASS | CQ spec `tests/comprehension/13337_spec.json` verifier-reviewed (6 Qs map 1:1 to the AC surface). Fresh sonnet agent, doc sections only: **6/6, zero misreads** — verbatim + zero latitude, clean-stop zero-trace, full glob→dry-run→show-added→confirm→write sequence with exact flags, merge/fail-closed enumeration + never-hand-edit, defaults-always + deny-vs-ask rationale, fourth-sanctioned-exception reconciliation in the discipline's own terms |
| TC-11 static gate | PASS | **5269 passed / 0 failures / 0 errors** on 2a1a4ef1e |
| TC-12 landing safety | PASS | Zero deletions; 3 behind origin/main = my own qa state commits (benign); no fleet/state artifacts |

## Notes

- One verifier-harness defect found during the run (my own): the probe envelope parser read only the last stdout line; the CLI pretty-prints JSON. Fixed in the probe file; no product implication.
- Out-of-scope observation (not a #13337 gap, scan candidate): `wizard.py:3431 pr_flow_prompt()` still offers the retired "direct commits" choice — likely dead code post-#13336; checking dispatch before filing.
- Verdict-before-merge ordering applied; approve-review expected same-author-blocked, verdict recorded on the issue pre-merge.

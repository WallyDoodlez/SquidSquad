# QA-RESULTS-13339 — installer maturity probe + workflow->roster mapping

**Issue**: #13339 (type:task, priority:medium)
**PR**: #13398 `squidsquad/task/13339`, head 2d97897de (5 files: wizard.py +265, docs/INSTALLER-RUNTIME.md +3/-1, new 13339_spec.json +35, new test_wizard_13339_maturity_roster.py +251, test_wizard_runbook.py +2)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13339.md`
**Verdict**: **PASS -> pending-ship.** (1 non-blocking doc-polish flag to PM.)

## AC walk
- **AC2 PASS (TC-1)** — `detect_maturity` (wizard.py:3902): established if `source_file_count >= _ESTABLISHED_MIN_SOURCE_FILES` (8) OR has_tests; empty if 0 src AND no manifest/framework; else scaffolded. Signal-transparent `signals` block; degrades via `_load_or_run_scan`. **Live CLI E2E**: this repo -> established (339 src, has_tests=True); empty temp dir -> empty.
- **AC1 PASS (TC-2/TC-3)** — `propose_roster` (wizard.py:3966): intended path (both->be+fe, fullstack->worker, backend->be, frontend->fe, unknown->error envelope) + scan path (fe&be->be+fe, fe->fe, be->be, none->fullstack). PM/DM/verifier fixed singletons. **Live CLI E2E**: --intended both=>[be,fe], fullstack=>[worker], bogus=>error. **Manifest check (TC-3)**: `verifier/manifest.yaml` = always_installed:true + show_in_roster:false, NO variant -> verifier cannot vary by count; the singleton interpretation is manifest-correct (the AC's implied verifier-count-varies premise is contradicted by the shipped manifest).
- **CQ PASS (TC-4)** — 13339_spec 5 Qs verifier-reviewed. Fresh Sonnet agent on the named `docs/INSTALLER-RUNTIME.md` §4/§9 sections ONLY -> **5/5 zero misreads**, incl. correct CQ4 (multi-surface QA => behavior customization, never more verifiers). The agent was given BOTH §4 line 72 and §9 line 202 and still resolved verifier-singleton correctly.
- **TC-5 PASS** — `test_wizard_13339_maturity_roster.py`: 24 passed.
- **TC-6 PASS** — full static gate on branch HEAD: **5310/0/0**.
- **TC-7 PASS** — landing safety. Branch was 3 behind origin/main (missing #13369 + #13355) and shares wizard.py + test_wizard_runbook.py with #13355. Merged origin/main into the branch LOCALLY (no push): **3-way merge CLEAN (0 conflicts)**; `pr-flow-prompt` correctly reconciled out of the combined dispatch + `_WIZARD_COMMANDS`; 63 key tests + **combined static gate 5329/0/0**. Post-merge origin/main confirmed #13369 + #13355 + #13339 all present.

## Non-blocking flag (PM)
`docs/INSTALLER-RUNTIME.md` §4 step 3 (line 72) still reads "how many Workers and Verifiers to propose and their specializations" — loosely inconsistent with the now-explicit §9 verifier-singleton contract (line 202, added by this task). Pre-existing text; CQ fresh-agent survived it (zero misread); NOT a #13339 defect and does NOT block ship. Future one-line tighten to "how many Workers" removes the residual ambiguity.

## Actions
- PR #13398 squash-merged to main. #13339 pending-test -> pending-ship (DM owns version/counter/tag). Prior work (#13369/#13355) verified preserved on origin/main post-merge.

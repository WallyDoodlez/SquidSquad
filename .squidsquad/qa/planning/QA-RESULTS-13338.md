# QA-RESULTS-13338 — installer step-8 independent-verification sub-agent playbook

**Issue**: #13338 (type:task, priority:medium — LAST INSTALLER-RUNTIME.md implementation-set item)
**PR**: #13448 `squidsquad/task/13338` (3 files: INSTALLER-RUNTIME.md +12 §9 Step-8 playbook, new 13338_spec.json +30, test_wizard_runbook.py +27)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13338.md`
**Verdict**: **PASS -> pending-ship.**

## AC walk
- **AC1 PASS** — §9 Step-8: spawn a FRESH sub-agent (never self), against the applied-but-uncommitted `.squidsquad/` from step 7; inputs = L4 project files + project context (.repo-scan.json + roster + create→build→verify→deliver workflow) + protocol; returns structured verdict `{pass, failures:[{check,what_broke,which_customization}]}`.
- **AC2 PASS** — three checks, concrete pass/fail: (1) composes cleanly; (2) no §3 invariant breached; (3) roster carries work end-to-end. **Cross-checked check-2 invariants vs §3 VERBATIM: all six present** (4 role-classes / forge-as-tracker / verification-gate / event-driven-runtime / create-build-verify-deliver / reviewable-PR) — exact match. **Compose-command precision independently verified against compose.py**: `deploy-all` full re-compose (2261+); `deploy <alias> --check --staged-l4 <path>` = staged validator (check_alias_staged_l4, 2198-2222); bare `--check` w/o `--staged-l4` IS an error (2188-2197); `deploy-all --check` IS retired (2245-2260). Every playbook command accurate.
- **AC3 PASS** — self-solve loop on FAIL (soften replace→append / re-scope pointer / reframe as variable / drop+inform), re-run until clean; NEVER ask user; only clean pass proceeds (applied-but-unverified never committed).
- **AC4 PASS** — inputs + per-check pass/fail + verified concrete commands = executable protocol.
- **AC5 PASS (CQ)** — LLM-consumed §9 Step-8. 13338_spec 4 Qs verifier-reviewed; fresh Sonnet agent on named section only → **4/4 zero misreads** (who-runs-it+why-not-self; three checks+check-1 commands; DM-dropped=check-2 self-solve don't-ask-user; roster-can't-verify=check-3 FAIL cannot commit as-is).
- **Tests / gate** — new test_step8_playbook_defines_executable_verification PASS; full static gate **5321/0/0**; branch 0 behind main (= post-merge state, no combined-merge needed).

## Actions
- PR #13448 squash-merged to main. #13338 pending-test -> pending-ship (DM ships). **Completes the entire INSTALLER-RUNTIME.md implementation set** (T1-T4 + #13327/#13328/#13329/#13338).

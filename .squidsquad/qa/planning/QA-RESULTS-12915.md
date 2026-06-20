# QA-RESULTS-12915 (+ #12821) — installer-files.txt sub-skill/script completeness

**Verdict: BOTH PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-20 02:26 · **Verifier:** qa · PR #13005 @ d28c6ee0c · branch `squidsquad/task/12915`.

Two bugs (type:issue/medium, role:skill, auto-approved) resolved by one PR. manifest
data + test → no CQ. Worktree `D:\Dev\Dev\sq-12915-verify`. Append-only.

## #12915 — 21 sub-skill .md fragments absent from manifest
- **AC1 (fragments shipped)** PASS — 21 fragments added to installer-files.txt; Total 229→250.
  Includes l4-curation, pr-protocol, task-pickup, tracker-protocol, pickup-comment-fidelity,
  the 6 common-events/*, the worker-*/verifier-* project L4 seeds + setup-upgrade-gate +
  shared-responsibility, dm/events/pr-merge-wait, verifier/skill/finding-categories.
- **AC2 (manifest integrity)** PASS — independent script: header **Total 250 == 250 actual**;
  **0 duplicate** entries; **0 dangling** (all 250 resolve to real files).

## #12821 — no test asserts manifest completeness (let #12506 AC11 slip)
The issue's two asks (from the body):
- **Item 1 (.py-script completeness test)** PASS — satisfied by #12909 (already shipped, verified
  by qa earlier this session): `test_every_runtime_script_listed_or_excluded` in
  test_installer_wiring.py (every references/scripts/*.py listed-or-allowlisted + Total-header
  check). Confirmed present + 5 passing on this branch.
- **Item 2 (event_poll.py absence triage)** PASS — #12909 SHIPPED event_poll.py; confirmed
  present in the manifest (installer-files.txt:39).
- **Complementary (.md-fragment completeness test)** PASS — PR #13005 adds
  test_12821_installer_files_subskill_completeness.py: test_all_catalog_subskills_in_manifest
  (runtime-loadable), test_all_wizard_seed_stubs_in_manifest (L4 seeds),
  test_manifest_count_header_matches_payload, test_no_duplicate_manifest_entries. Non-vacuous
  (asserts disk-vs-manifest; would have caught the 21-fragment gap).
- **No CQ** — manifest data + test only.

## No-regression
- test_12821_installer_files_subskill_completeness + test_installer_wiring → 31 passed.
- Full static gate: `run_tests.py static` → **PASS — 4702 gated tests, 0 failures, 0 errors** (exit 0). Only the 2 allowlisted #10360 known-failures.

## Cross-PR overlap note → skill (non-blocking)
PR #13005 adds the 6 `common-events/*` fragments — the SAME ones the currently-FAILed/unmerged
#12912 (PR #12926) also adds. #12915 landing them first is fine (#12912 is back with skill from
my FAIL this session); skill must drop the redundant manifest lines from #12912's re-submission
to avoid a duplicate entry (the new test_no_duplicate_manifest_entries would catch it).

## Disposition
Both #12915 and #12821: pending-test → pending-ship (DM). PR #13005 — verify closing keyword(s)
at merge. Merge deferred to DM. Counter NOT bumped. TEST-PLAN-12915 + QA-RESULTS-12915 on main.

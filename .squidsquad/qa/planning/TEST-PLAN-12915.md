# TEST-PLAN-12915 (+ #12821) — installer-files.txt sub-skill completeness

PR #13005 resolves BOTH #12915 (21 sub-skill .md fragments absent from manifest)
AND #12821 (no test asserts manifest lists every required fragment — the test gap
that let #12506 AC11 / the manifest gaps slip). Both type:issue/medium, role:skill,
auto-approved. manifest data + test → **no CQ**. Worktree `D:\Dev\Dev\sq-12915-verify`.

This is the .md-fragment completeness complement to the #12907/#12909 .py-script arc I
verified earlier this session.

## Derived ACs
- **AC1 (#12915 — fragments shipped):** the missing sub-skill `.md` fragments (catalog-
  referenced runtime-loadable + wizard L4 seed stubs) are added to installer-files.txt; the
  `# Total: N` header updated to match.
- **AC2 (manifest integrity):** Total == actual entry count; no duplicate entries; every entry
  resolves to a real file (no dangling).
- **AC3 (#12821 — completeness test):** a test asserts installer-files.txt lists every
  catalog-referenced sub-skill + every worker-*/verifier-* wizard L4 seed, plus the
  count-header and no-duplicate invariants.
- **AC4 (#12821 non-vacuous):** the test would have caught the original 21-fragment gap.
- **No CQ** — manifest data + test only.

## Test cases / evidence
- **TC1 (AC1/AC2)** — manifest integrity script: Total header **250 == 250 actual**, **0
  duplicates**, **0 dangling** (all 250 entries resolve to real files). 21 fragments added
  (incl. l4-curation, pr-protocol, task-pickup, tracker-protocol, the 6 common-events, the
  worker-/verifier- project L4 seeds, dm/events/pr-merge-wait, verifier/skill/finding-categories).
- **TC2 (AC3/AC4)** — test_12821_installer_files_subskill_completeness.py:
  test_all_catalog_subskills_in_manifest (runtime-loadable completeness),
  test_all_wizard_seed_stubs_in_manifest (L4 seeds), test_manifest_count_header_matches_payload,
  test_no_duplicate_manifest_entries. Non-vacuous (asserts disk-vs-manifest). + test_installer_wiring → 31 passed.
- **TC3 (no-reg)** — full run_tests.py static (pending — see QA-RESULTS).

## Cross-PR overlap note → skill
PR #13005 adds the 6 `common-events/*` fragments — the SAME ones the currently-FAILed/
unmerged #12912 (PR #12926) also adds. Whichever lands first, the other must drop its
manifest change to avoid a duplicate line. #12912 is back with skill (my FAIL this session),
so #12915 landing them first is fine; flag to skill to reconcile #12912's re-submission.

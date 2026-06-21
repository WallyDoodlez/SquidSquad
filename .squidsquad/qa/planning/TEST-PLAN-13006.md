# TEST-PLAN-13006 — delete orphaned legacy L4 seed stubs (pm-/dm-)

Bug (type:issue/LOW, auto-approved), filed by skill (dead-code hygiene, found during
#12915). PR #13012, branch `squidsquad/task/13006`, role:skill. dead-file deletion +
guard test → **no CQ**. Worktree `D:\Dev\Dev\sq-13006-verify`.

Deletion → verifier MUST independently confirm the files are truly dead before approving.

## Derived ACs
- **AC1 (deletion):** the 6 orphaned stubs deleted — project/{pm,dm}-{instructions,responsibility,soul-directives}.md.
- **AC2 (guard test):** a test asserts project/ carries no pm-/dm- stubs (named + broad straggler check).
- **AC3 (genuinely dead — independent confirmation):** no `.py` loader references them; wizard skips
  them; not in docs/sub-skill-catalog.md; correctly excluded from installer-files.txt (#12915).
- **No CQ** — dead-file deletion + guard test only.

## Test cases / evidence
- **TC1 (AC1)** — branch `ls references/sub-skills/project/`: no pm-/dm- stubs remain (all 6 deleted).
- **TC2 (AC3 — INDEPENDENT dead-check):** grep across *.py/*.md/*.yml/*.txt for each of the 6 stub
  names → NO `.py` code references any of them. The only hits are prose (skill scan-history, a vault
  note) + static 8697 comprehension fixture snapshots (self-contained content, not file-loaders) —
  none load-bearing; deleting the stubs doesn't affect them.
- **TC3 (AC3 — wizard skip):** wizard.py `_copy_l4_seed_stubs` (L1865-66) explicitly copies ONLY
  worker-*/verifier-* ("leave other seeds alone") → the pm-/dm- stubs were never seeded = dead.
- **TC4 (AC3 — manifest):** #12915 (verified this session) added only worker-/verifier- + shared-* +
  setup-upgrade-gate project seeds to installer-files.txt — NOT the pm-/dm- stubs. Correctly unshipped.
- **TC5 (AC2)** — test_13006_orphaned_l4_stubs_removed.py: test_orphaned_pm_dm_stubs_absent (named) +
  test_no_pm_or_dm_per_slot_seed_stubs (broad straggler guard) → 2 passed.
- **TC6 (no-reg)** — full run_tests.py static (pending — see QA-RESULTS).

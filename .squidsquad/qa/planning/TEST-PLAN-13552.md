# TEST-PLAN-13552

Derived independently from the issue body (`ISSUE: IMPROVEMENT: verification.md Step 5a's gh pr review --approve unconditionally fails in single-GH-identity installs`).

## ACs derived from the issue

- **AC1**: `verification.md` Step 5a documents that `gh pr review --approve` MAY fail with "Can not approve your own pull request" in single-GH-identity installs, and that this is expected/non-blocking.
- **AC2**: The doc instructs the verifier to proceed regardless — to the Auto Merge check / `gh pr ready` + harness `/merge` — using the already-posted PR comment as the durable approval record, not to stop/escalate.
- **AC3**: The approve command itself is left unchanged (still worth attempting; the note documents the failure, doesn't remove the step).
- **AC4**: New regression test (`test_13552_verify_self_approve_note.py`) locks the note's presence/content; passes.
- **AC5**: Comprehension-staleness gate clean after the edit (existing CQ specs touching `verification.md` — 13464/1428 — had their baselines correctly refreshed, not just silently passed over).
- **AC6 (independent CQ)**: A fresh agent given only the file correctly concludes the failure is expected/non-blocking and that it should still proceed to merge.
- **AC7**: No regressions — full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC3 | `git diff origin/main` on verification.md; read the added note |
| TC2 | AC2 | Read the note's instruction to proceed to Auto Merge regardless |
| TC3 | AC4 | Run `test_13552_verify_self_approve_note.py` |
| TC4 | AC5 | Run `comprehension_staleness.py check` |
| TC5 | AC6 | Spawn fresh agent, file-only, ask what to do on the specific GraphQL failure |
| TC6 | AC7 | Run `tests/run_tests.py static` |

## Independent corroboration
I hit this exact failure live during #13317's merge this same session (`gh pr review 13612 --approve` → "Can not approve your own pull request") and used exactly the workaround this fix documents (PR comment + `gh pr ready` + harness `/merge`, skipping the failed approve). This is first-hand confirmation the note is accurate, not just plausible-sounding.

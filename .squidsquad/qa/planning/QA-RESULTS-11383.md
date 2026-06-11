# QA-RESULTS-11383 — 6 compose-tests red on polish-session — boot-bootstrap assertions stale

**Issue**: #11383 (`type:issue`, severity:medium, role:skill, self-reported by skill during #11381 smoke)
**Fix commit**: `6916f503c` on `squidsquad/skill/compose-polish-session` (no PR — test-side update)
**Verifier**: verifier-lead
**Verified**: 2026-06-09 04:08
**Verdict**: **PASS**

## Implicit AC

Update 6 stale test assertions to match post-Iter-22 polish heading structure:
- `BOOT_BOOTSTRAP_HEADING` constant: `## Boot — Mode Detection (#9588)` → `### Step 1 — step:cycle/boot` (fixes 4 parametrizations).
- `test_dm_bootstrap_enumerates_pr_merge_wait`: assert on bare directive identifier (no `.md` suffix).
- `test_live_v2_boot_block_inlined_per_path_a`: assert on `### Step 1 — step:cycle/boot`.

## Verification

- **TC-1 — Tests pass on bundle**: PASS. `pytest tests/test_compose_9588.py tests/test_d2_link_stage_references.py` → **67/67 PASS** on commit `6916f503c`. The 6 previously-red assertions are green.
- **TC-2 — Assertions still meaningful (not no-op)**: PASS. Inspected composed CLAUDE.md per role:
  - `.squidsquad/skill/CLAUDE.md:450-451` — `<!-- sub-skill: boot-bootstrap -->` followed by `### Step 1 — step:cycle/boot`
  - `.squidsquad/pm/CLAUDE.md:424` — `### Step 1 — step:cycle/boot` present
  - `.squidsquad/dm/CLAUDE.md:375-376` — `<!-- sub-skill: boot-bootstrap -->` followed by `### Step 1 — step:cycle/boot`
  - `.squidsquad/qa/CLAUDE.md:383-384` — same shape
  The new heading is present in all 4 composed outputs, AND the old heading `## Boot — Mode Detection` is absent — the tests now verify the actual canonical surface, not a phantom heading.
- **TC-3 — DM bootstrap pr-merge-wait directive verified**: PASS. `.squidsquad/dm/CLAUDE.md:431` and `:539` contain `→ run sub-skill: \`roles/dm/events/pr-merge-wait\`` and `→ run sub-skill: roles/dm/events/pr-merge-wait` respectively — bare identifier per directive grammar. Test assertion matches the on-disk reality.
- **TC-4 — Test-only scope**: PASS. `git show 6916f503c --stat` reports `tests/test_compose_9588.py` and `tests/test_d2_link_stage_references.py` changed only. Zero source-tree file changes. Zero compose-behavior change. Zero composed-CLAUDE.md change.
- **TC-5 — Commit message documents the trigger**: PASS. Commit message names Iter 22 (commit `916820106`) as the polish-restructure that drove the test drift, and notes that each updated assertion has a header comment naming the polish iteration — paper trail for the next restructure.

## Note on skill self-filing

#11383 was filed by skill and fixed by skill in the same session. This is unusual but appropriate per the scenario: skill discovered the 6 stale assertions during a smoke test after the #11381 walker-regex fix, verified the failures pre-existed the fix via `git stash`, and filed + fixed to keep the bundle green for verifier's next visit. Filing-before-fix preserves traceability that the assertions were stale, not regressed.

## Verdict

PASS — test-side refresh to match canonical post-restructure surface. All 4 composed outputs verified to contain the new heading. Zero source-tree change. Transitioning #11383 to pending-ship.

Append-only after publication.

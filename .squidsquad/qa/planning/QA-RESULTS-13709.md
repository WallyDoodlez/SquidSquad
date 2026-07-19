# QA-RESULTS-13709 (bundled with #13710)

## Summary
FAIL — back to In Progress. The code itself is sound (11/11 regression tests pass, spot-read confirms the `j2` extension fix and the refresh()/main() return-value plumbing are correct). The blocking gap is process, not correctness: no PR exists for branch `squidsquad/task/13710`, despite this install's PR Flow being `yes` and `git-commit.md`'s Step 5.3 requiring one ("When marking Pending Test, create a PR from the feature branch"). Every other item verified this session had a PR; this is the exception, not the norm.

## AC Walk
| AC | Result | Evidence |
|----|--------|----------|
| AC1 (#13709's j2 fix) | PASS | `_PATH_RE` now includes `j2` in the extension alternation. `tests/test_comprehension_staleness_13709_13710.py` — 11/11 PASS, including `test_j2_fragment_survives_spec_fragment_paths` and `test_1428_spec_now_tracks_test_plan_j2`. |
| AC1 (#13710's refresh-count fix, verified together) | PASS | `refresh()` now returns a `failed` list; the summary line reports `refreshed/requested`; `main()` exits 1 on any unresolved name. `test_main_exits_nonzero_when_all_names_invalid` / `test_main_exits_nonzero_on_partial_failure` both pass. |
| AC2 (process — PR exists) | **FAIL** | `gh pr list --search "squidsquad/task/13710" --state all` returns empty — no PR in any state (open, closed, merged, draft). Confirmed via `gh pr list --state open --limit 20` across the whole repo: the only open PR is #13708 (unrelated, #10003). Skill's own comments on #13709/#13710 never mention a PR number. |

## Zero-gap check
1 gap: no PR exists for the branch. Not a code-correctness issue — the fix itself checks out — but the project's own PR Flow is load-bearing (review trail, my own ship mechanics operate on PR numbers via the harness `/merge` endpoint, not raw branches) and this install has it set to `yes` with no documented exemption for small/orthogonal fixes.

## Verdict (Round 1)
FAIL → In Progress. Route: run `git_ops.py pr-create` for the existing branch — no code changes needed, re-verification should be immediate once a PR exists.

---

## Round 2 (2026-07-18)

Skill resubmitted with PR #13712 opened for branch `squidsquad/task/13710` (covers both #13709 and #13710) — the sole Round 1 gap. Content unchanged from Round 1 (reconfirmed independently, not assumed).

| AC | Result | Evidence |
|----|--------|----------|
| AC1 (j2 extension tracked) | PASS (re-confirmed live) | Independently reproduced: `spec_fragment_paths()` on the real `1428_spec.json` returns `references/prompts/test-plan.md.j2`. `comprehension_staleness.py check` exits 0 on the branch (no regression to existing extensions). |
| AC2 (exact issue-body repro: `refresh 1428 13464 10678`) | PASS (re-confirmed live) | Ran the literal repro command: summary now reads `0/3` (was misleadingly `3 spec(s)`), exit code 1 (was 0), `git diff` on `.staleness-baseline.json` shows zero corruption from the failed refresh. |
| AC3 (process — PR exists) | PASS | PR #13712 opened, branch `squidsquad/task/13710`. |
| AC4 (regression tests) | PASS | `tests/test_comprehension_staleness_13709_13710.py` — 11/11 PASS (re-run on branch). |
| Full suite | PASS | Static gate: 5869 gated tests, 0 failures (1 pre-existing, unrelated failure on `.squidsquad/pm|qa/CLAUDE.md` staleness — confirmed present on `origin/main` itself before this PR, not introduced by it). |

**Merge note**: branch `squidsquad/task/13710` had forked before #13565 shipped (which restructured `verification.md` into `verification.md` + `verification-templates.md`), producing a real (non-trivial) conflict in `tests/comprehension/.staleness-baseline.json`'s `1428_spec.json` entry on first merge attempt. Resolved by taking the union of both sides' keys (test-plan.md.j2 from this branch + verification.md/verification-templates.md's current hashes from main), verified via a real re-run of the regression suite and `comprehension_staleness.py check` post-merge — not just a text-level conflict resolution. Also self-caught and corrected an unrelated near-miss during this merge: a raw `git merge` of a stale branch into current main risks silently reverting concurrent hand-authored-prose edits (BRIEFING.md class of bug, see `[[learning-git-merge-silently-drops-concurrent-large-edit-on-shared-markdown]]`) — verified byte-for-byte that every non-PR file in the final merge commit matched `origin/main` exactly before pushing.

## Verdict (Round 2)
PASS → Pending Ship. PR #13712 merged (commit c1fc27ea).

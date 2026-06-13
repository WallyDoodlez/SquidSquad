# QA-RESULTS-11381 — orphan-test grandfathering for common/pr-protocol.md

**Issue**: #11381 (`type:issue`, severity:low, role:skill, improvement-scan)
**Fix commit**: `e30aef342` on `squidsquad/skill/compose-polish-session` (no PR — source-only test edit)
**Verifier**: verifier-lead
**Verified**: 2026-06-09 03:08
**Verdict**: **PASS** — scope-expanded fix (regex bug + grandfather) correctly addresses root cause

## Implicit AC (from issue body)

Either grandfather `common/pr-protocol.md` in `tests/test_manifest.py:204 known_unused`, OR teach `_collect_run_subskill_directive_names()` to walk sub-skill bodies transitively. Goal: `test_no_orphan_sub_skills` PASSES.

## What skill actually did

Skill diagnosed deeper than the issue scope — the test was failing on 8 orphans, of which only 1 was `pr-protocol`; the other 7 (`common-events/*` × 6 + `roles/dm/events/pr-merge-wait.md`) were FALSE orphans hidden by 2 regex bugs in `_collect_run_subskill_directive_names()`:

1. **Backtick-tolerant**: original `[A-Za-z0-9][\w-]*` capture rejected backtick-wrapped names (e.g. `` → run sub-skill: `event-mode-contract`. `` — the stylistic code-formatting used throughout `references/roles/instructions.md` lines 197–210).
2. **Slash-prefix-tolerant**: original capture stopped at `/`, so slash-bearing path-form names (e.g. `roles/dm/events/pr-merge-wait` per the sub-skill-catalog name-shape spec) only matched their first segment (`roles`).

Combined fix (1 regex line + 1 `known_unused` entry):
```
→\s*run\s+sub-skill:\s*`?(?:[\w/-]+/)?([A-Za-z0-9][\w-]*)`?
known_unused = {"common/event-reactions.md", "common/pr-protocol.md"}
```

## Verification

- **TC-1 — Commit shape**: PASS. `git show e30aef342 --stat` reports `tests/test_manifest.py | 19 +++++++++++++++++--, 1 file changed, 17 insertions(+), 2 deletions(-)`. Single-file surgical change. Zero source-tree code change (no behavior change in compose at runtime — this is test polish only).
- **TC-2 — Test passes on bundle branch**: PASS. `git checkout e30aef342 && python -m pytest tests/test_manifest.py` → `10 passed`. Specifically `test_no_orphan_sub_skills` → `1 passed`.
- **TC-3 — Regex correctness across the 4 directive-shape variants**: PASS. Hand-tested:
  - `→ run sub-skill: tracker-protocol` → captures `tracker-protocol` ✓
  - `` → run sub-skill: `event-mode-contract`. `` → captures `event-mode-contract` ✓
  - `→ run sub-skill: roles/dm/events/pr-merge-wait` → captures `pr-merge-wait` (final segment per file-stem match downstream) ✓
  - `` → run sub-skill: `forge-read-pattern` `` → captures `forge-read-pattern` ✓
- **TC-4 — All 7 previously-false-orphan names now match**: PASS. Live re-execution of `_collect_run_subskill_directive_names()` on bundle branch:
  - `event-driven-workflow` → True
  - `comment-handling` → True
  - `event-mode-contract` → True
  - `forge-read-pattern` → True
  - `idle-cooldown-loop` → True
  - `cursor-management` → True
  - `pr-merge-wait` → True
- **TC-5 — Grandfather rationale documented**: PASS. The `known_unused` comment cites #11381 explicitly and explains why `pr-protocol.md` IS genuinely transitive (referenced from `common/git-commit.md` sub-skill body, not from any `instructions.md`), with a forward-pointer to "Option B follow-up" (teaching the walker to traverse sub-skill bodies). Future work clearly labeled, not silently deferred.

## Scope-expansion call

Skill's fix is intentionally broader than my finding's literal suggestion. My finding focused only on `pr-protocol.md`. Skill correctly identified that the same root cause (incomplete regex) was producing 7 other false orphans the existing test had been masking. Fixing the regex resolves those 7 organically and leaves only the 1 genuine transitive case (`pr-protocol.md`) for grandfathering. This is a higher-quality fix than what I proposed.

No scope creep concerns — the regex fix touches one test file in one method; behavior at compose/runtime is unchanged.

## Verdict

PASS — root-cause regex fix + grandfather for the one genuinely transitive case. Test passes on bundle branch. Transitioning #11381 to pending-ship.

Append-only after publication.

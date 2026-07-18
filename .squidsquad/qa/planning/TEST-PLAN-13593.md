# TEST-PLAN-13593 — setup-yes gh ops must scope to target_dir, not ambient CWD

**Source**: GitHub issue #13593 body (Observation + Suggested direction, bug-report shape, no formal AC list).
**Derived without reading the diff first.**

## Acceptance Criteria (derived from the issue's stated problems)

- **AC1**: `gh repo view` inside `cmd_setup_yes` resolves against `target_dir`'s own remote, not the ambient process CWD.
- **AC2**: `ensure_labels(dry_run=False)` inside `cmd_setup_yes` creates labels on `target_dir`'s own remote, not the ambient CWD's.
- **AC3 (non-regression)**: existing unscoped callers (`cmd_ensure_labels` and any other caller not passing `cwd`) preserve historical ambient-CWD behavior.
- **AC4 (design deviation, reasonably justified)**: the issue's suggested "fail loudly if target_dir has no resolvable remote" was NOT implemented as a hard failure — instead the existing graceful fallback (directory name, empty repo field) is kept, since a fresh local-only repo with no remote yet is a legitimate case distinct from the reported bug (wrong remote). Verify this reasoning holds and doesn't reintroduce the original bug under a different name.

## Test Cases

### TC-1 (covers AC1): Live cwd-scoping mechanism — decisive
- **Steps**: Called the real `wizard._run(["gh", "repo", "view", ...], cwd=".")` (this repo) and `cwd=<empty temp dir, no git repo>`.
- **Expected**: `cwd="."` resolves to this repo's own identity; `cwd=<no repo>` fails cleanly (non-zero exit, "not a git repository").
- **Result**: PASS — `cwd="."` returned `{"name":"SquidSquad","url":"https://github.com/WallyDoodlez/SquidSquad"}`; `cwd=<empty temp dir>` failed with exit 1 and the expected git error. Confirms the `cwd` kwarg genuinely changes which repo `gh` resolves against — not just a plausible-looking parameter that's silently ignored.

### TC-2 (covers AC2): Live label-scoping mechanism
- **Steps**: Called the real `wizard.list_gh_labels(cwd=".")` and `wizard.list_gh_labels(cwd=<empty temp dir>)`; called `ensure_labels(dry_run=True, cwd=".")`.
- **Expected**: `cwd="."` returns this repo's real label set (50 labels, `squidsquad` present); `cwd=<no repo>` returns an empty set (graceful, per the function's own documented contract); dry-run against `cwd="."` reports the real existing-label count with zero side effects.
- **Result**: PASS on all three.

### TC-3 (covers AC3): Non-regression
- **Steps**: Read `cmd_ensure_labels` — confirms it calls `ensure_labels(dry_run=dry)` with no `cwd` argument.
- **Expected**: Defaults to `cwd=None`, `subprocess.run(cwd=None)` uses the ambient CWD — identical to pre-fix behavior.
- **Result**: PASS.

### TC-4 (covers AC4): Design reasoning
- **Steps**: Read the diff's comment explaining the fallback-vs-fail-loudly tradeoff.
- **Expected**: The fallback only fires when `target_dir` genuinely has no remote (a legitimate fresh-local-repo case); the ORIGINAL bug (silently succeeding against the WRONG remote) can no longer happen, since scoping to `target_dir`'s own cwd means a missing remote now fails/falls-back naturally rather than silently defaulting to some other ambient repo.
- **Result**: PASS — the fallback and the original bug are genuinely distinct failure modes; the fix closes the reported one without introducing a new footgun.

### TC-5: Worker's own tests + full regression
- **Steps**: `pytest tests/test_wizard.py -k SetupYesGhScoping`, combined-state static gate.
- **Result**: 5/5 worker tests PASS. Static gate result pending at write time.

## Coverage matrix
- AC1 → TC-1
- AC2 → TC-2
- AC3 → TC-3
- AC4 → TC-4

# QA-RESULTS #13556 — receiving-side merge-drop restore guard (SEV, sibling of #13554)

**Verdict: PASS → pending-ship.**

## Summary

Second verification pass. First pass (this session, earlier) rejected PR #13560
back to in-progress: `_restore_merge_dropped_state()` was wired only into
`git_ops.pull()`, missing the bare `git merge origin/main --no-edit` vector —
the exact action that caused the original #13554/#13556 incident, and
independently reproduced live to falsify the PR's own "regardless of how it
arrived" claim. See `TEST-PLAN-13556.md` for the full first-pass evidence.

Worker resubmitted with a tracked `references/git-hooks/post-merge` hook
(auto-active via the existing #11511 `core.hooksPath`) that invokes a new
`git_ops.py restore-merge-dropped-state` CLI after **any** successful merge —
covering the bare-merge path the first pass falsified. Also fixed in the same
resubmission: a gitlink/submodule false-positive the guard's own live-fire
exposed (it was resurrecting a deliberately-deleted `.claude/worktrees/*`
registration) and a test-isolation leak in `TestPull`/`TestPullEmitsRole`/the
verifier's own `test_feat_13267` (the guard now runs live via `_run_list`,
unmocked by those tests' `_run` patches).

## Independent verification (not trusting the PR's own tests)

- **Decisive re-test**: built a from-scratch reproduction (fresh scratch repo,
  PR-tip `git_ops.py` + `post-merge` hook only, no other PR scaffolding)
  mirroring the exact incident shape — base commit with a protected vault
  note, incoming branch deletes it, local branch diverges, **bare**
  `git merge incoming --no-edit`. The hook fired, restored the note
  byte-exact, committed the restore, left a clean tree. This is the same
  scenario that failed silently on the prior PR revision.
- **Combined-state regression check**: freshly re-fetched the PR branch
  (caught a stale local branch from the first pass that only had the PR's
  first of five commits — would have under-tested the fix), merged current
  `origin/main` locally per [[learning-verify-combined-state-when-branch-behind-main-shares-files]]
  (now itself protected by the fix under test — no drop occurred, correctly).
  Full `tests/test_git_ops.py`: **259/259 PASS**, 0 regressions. All 16
  `*13556*`-named tests PASS, including the PR's own
  `test_bare_merge_fires_hook_end_to_end` (a replay of my exact falsification
  scenario) and the DS-review-driven idempotence/chmod-masking tests.
- **install-hooks live-fire**: called the real (unmocked) `install_hooks()` in
  a fresh throwaway repo — confirmed it sets `core.hooksPath` and the exec bit
  on both `pre-commit` and `post-merge`.
- Hook is tracked `100755` in git and present in
  `references/installer-files.txt` (256 files).

## Out-of-scope finding (not blocking this verdict)

Full static gate on the combined state showed 3 failures — non-ASCII em-dash
in `.squidsquad/start.ps1` / `inject-permissions.ps1` breaking Windows
PowerShell 5.1 parsing. Reproduced the identical 3 failures against a clean
`origin/main` checkout with **zero** #13556 changes present (disposable git
worktree) — proves this is pre-existing on main, not introduced by PR #13560.
Filed separately as **#13577** (skill, severity:high) rather than reblocking
this ticket.

## Records

- `TEST-PLAN-13556.md` — full AC derivation, first-pass FAIL evidence, and
  this pass's re-verification evidence.
- Issue #13556 Discussion — verdict posted before transition (#13464
  ordering).

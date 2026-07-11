# Working State

- **Task**: 13454 (RESUME — verifier route-back: merge conflict, not AC gap). PR #13546 branch squidsquad/task/13454 conflicts with main: both this PR + #13371/PR#13544 appended a test class at the same anchor in tests/test_git_ops.py. Impl itself verifier-confirmed correct. Fix: merge origin/main into branch, keep BOTH class blocks, static gate, push, re-flag pending-test. Session 2026-07-11 (fresh boot ~15:28), event mode, **Verbose OFF (quiet)**.

## Shipped → PENDING-TEST this wake (7 PRs, all ready, verifier's queue)
- **#13434** (PR #13538): build_config_md↔FIELD_MAP round-trip GATE test (test-only; resumed prior untracked file). Static 5409/0.
- **#13371** (PR #13544): `git_ops.pr_create` neutralizes closing keywords → 'Addresses' before adapter+gh. Code-only. 13 tests. Static 5418/0. PR body self-neutralized ('auto-closed'→'auto-Addresses') — guard working, flagged for verifier.
- **#13454** (PR #13546): `git_ops.pr_merge` reads isDraft, self-heals via `pr_ready` before merge (else actionable refusal). Backward-compat. 4 tests. Static 5409/0.
- **#13517** (PR #13547): `tracker.py._asciiize_title` — transliterate + encode('ascii','replace') backstop before gh `--title` argv; create_issue+create_task gh path. 12 tests. Static 5417/0.
- **#13532** (PR #13548): one-line docstring fix (test_12825 L144). Doc-only. Static 5409/0.
- **#13345** (PR #13549): /agents/{role}/health reads context-pressure via `_read_agent_pressure` (clone-relative, matches enforcement) not harness-root. 4 async tests. Static 5426/0.
- **#13357** (PR #13550): argparse in run_tests.py — --help (exit 0), unknown-arg/typo rejection (exit 2), backward-compat modes preserved; main(argv=None). Self-verified (gate ran via modified `run_tests.py static`). 10 tests. Static 5444/0.

## #13447 — INVESTIGATED, root cause corrected, LEFT OPEN (do NOT implement the filed fix)
- Filed cause ("audit's compose dirties composed CLAUDE.md") is WRONG: `_post_merge_scope_audit` has NO compose. Real cause = autocrlf=true + no `.gitattributes` eol rule for `.squidsquad/*/CLAUDE.md` → CRLF churn. Real fixes: (primary) `.gitattributes text eol=lf` + renormalize (own careful fleet PR); (secondary) FF local main after merge. Full analysis posted. Confirm CRLF hypothesis live in verifier/DM clone before the .gitattributes PR.

## Remaining open role:skill — EXTERNALLY GATED (design decision / PM CQ AC); pick up with fresh context
- **#13531** (harness POST /restart relaunches on STALE primary clone; no staleness signal) — "for discussion" behavior report (PM-filed); harness.py; needs a DESIGN DECISION on the desired staleness-signal behavior (operator/PM) before implementing — don't rush it at saturation.
- **#13353** (harness re-emits assigned-to ~18× for unclaimed pending-test) — harness.py emit path, "exact emit site not traced"; needs tracing + dedup/backoff design (a fresh-context job).
- **#13354 / #13316 / #13317** — touch LLM-consumed instructions (verifier discussion-protocol / idle-cooldown-loop / stale PID-liveness sub-skills) → CQ gate; PM must author the comprehension-coverage AC first (skill-cq step). On pickup: comment/route to PM for the CQ AC before implementing.
- **#13356** (boot-bootstrap harness probe port-file-first) — boot-bootstrap.md is an instruction file → likely CQ; assess on pickup.
- NOTE: 7 PRs (#13538/#13544/#13546/#13547/#13548/#13549/#13550) now in the verifier's queue — expect route-backs; verifier-rejected items are HIGHEST priority on next wake (fix before new).

## Approved tasks — OPERATOR-GATED (not autonomous): #12527 (foreign-repo smoke; local slice done), #10686 (manual by design), #10690 (gated on #10686).

## Standing lessons (session-reinforced)
- Heredoc `<<'EOF'` does NOT expand `$TS` — HIT 3× this session. Build `MSG=$(cat <<EOF ...)` with `$TS` OUTSIDE single quotes, or set MSG via a normal var first (as I did later this session — worked).
- ASCII-only in git_ops.py `print()` (TestNoNonAsciiInPrintStatements) — use `--` not em-dash. (#13454 first-run fail.)
- #13371 neutralizer rewrites closing-keyword+ref in ANY PR body incl. meta-prose → write 'closed issue #N' / '`Fixes`-style keyword targeting #N'. `gh pr edit --body` unreliable → get body right first time. [[learning-closing-keyword-in-state-commit-autocloses-issue]]
- commit-code commits code to branch + returns to main; then branch-switch back ON the branch for pr-create (creates DRAFT → `gh pr ready`); task-end warns on uncommitted working-state (state file) but it correctly rides back to main for the harness to commit.
- task-begin carries uncommitted CODE changes onto the branch; edit code on the branch (I slipped once on #13454 — edited on main first; recovered since code isn't a state file).
- Full static gate = `run_tests.py static`, buffers to EOF (tail holds) — always run in background; count ~5409–5426 gated.
- State/vault files main-only + reset on branches (#11511) — reconcile against FORGE on resume; vault writes land on main.

## Improvement Scan
Status: idle-driver armed at boot; 6 productive items + 1 correction absorbed this wake — no scan yet.

## Quiet Cycle Counter: 0

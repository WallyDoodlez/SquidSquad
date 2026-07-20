# QA-RESULTS-13865

**Verdict: PASS → pending-ship**

## TC Results

| TC | Result | Evidence |
|----|--------|----------|
| TC1 — override mechanism proof | PASS | Manually set `GH_TOKEN` to Naahtec's real keyring token for one `gh api user -q .login` call: reported `Naahtec` even though the machine's active account remained WallyDoodlez throughout (confirmed via `gh auth status` before and after) — proves `GH_TOKEN` cleanly overrides per-call identity without touching shared global state. |
| TC2 — gh_identity resolves correctly | PASS | `python references/scripts/gh_identity.py` → `pinned identity: WallyDoodlez`, `keyring token: available`, live. |
| TC3 — end-to-end pin, live | PASS | `gh_identity.gh_env(['gh','api','user','-q','.login'])` returns an env with `GH_TOKEN` set; using that exact env for a real `gh api user` subprocess call correctly resolves as `WallyDoodlez`. Composes with TC1 to prove: if the active account were flipped away from WallyDoodlez right now, a call using this env would still resolve correctly — the same guarantee skill's own deliberate-flip test demonstrated, obtained without repeating that shared-state risk. |
| TC4 — wiring coverage | PASS (code-reviewed) | `tracker.py`: `_run_list`, `_run_list_timeout`, `_run_gh_with_body` all pass `env=gh_identity.gh_env(cmd_list)`. `git_ops.py`: `_run_list` passes `env=_gh_env(cmd_list)`. |
| TC5 — standalone-copy contract | PASS | `git_ops.py`'s import is wrapped in `try/except ImportError` with a no-op fallback (`return None` = inherit ambient env) — covered by `TestGitOpsStandaloneContract` (2/2). `tracker.py`'s import is a hard import (correct — tracker.py is never copied standalone). |
| TC6 — exemptions correct | PASS (code-reviewed + unit-tested) | `gh_env()` returns `None` (no injection) for: non-gh commands, `gh auth ...` subcommands, and when `GH_TOKEN`/`GITHUB_TOKEN` is already in the ambient env. `TestGhEnv` (6/6) covers every exemption explicitly. |
| TC7 — chokepoint completeness | PASS | Checked harness.py's 4 gh call sites (`gh issue list` ×2, `gh pr view` ×2) — all read-only. Naahtec (the read-only flip target) retains `pull:true` per the original #13863 report, so reads succeed regardless of the flip; harness.py is correctly out of scope, not a missed chokepoint despite being loosely named in the issue's suggested-direction text. |
| TC8 — regression coverage | PASS | `tests/test_gh_identity_13865.py`: 23/23 PASS (mocked at the subprocess boundary — appropriate given TC1/TC3 already cover the real, non-mocked path). |
| TC9 — full ship gate, byte-exact regression check | PASS | See "Ship gate" below. |

## Ship gate

- New unit tests: 23/23 PASS.
- **Full static suite**, captured completely to a file (not through `tail`, which had silently truncated earlier runs this session and hidden data — see self-correction note below): 50 failed / 6162 passed / 33 skipped.
  - 1 (`test_model_router_live.py`) excluded per its own documented `OPENAI_API_KEY`-gated, fail-by-design scope (same as #13863's verification).
  - Remaining 49: diffed **byte-exact** against a clean pull of `main` for the highest-risk file (`test_agent_boundaries.py`, 41 failures) — `diff` exit code 0, zero lines of difference between the two 41-item sorted failure-name sets. The rest of the cluster (`test_compose_author_comments_11142.py`, `test_comprehension_2183/2195.py`) was already individually confirmed pre-existing on clean main during #13863's verification this session (tracked as #13890). **Zero new failures introduced by this diff.**
- **Integration suite** (`tests/run_tests.py harness` + `status_flow`): 5/5 + 12/12 OK on first run; `status_flow` hit one transient `gh issue close` failure on a re-run attempt, confirmed non-reproducing on immediate re-run and architecturally unrelated (`tests/integration/integration_harness.py` has its own independent `_run()` that never imports `gh_identity` — this test suite's gh calls are entirely outside this PR's diff).

## Self-correction note (transparency, not a finding against the fix)

Two methodology mistakes this round, both corrected before reaching a verdict:
1. Piped several full-suite runs through `tail -N` to keep terminal output short — this silently truncated the failure list and hid ~10 `test_ac4_*` failures from my first cross-check against main, even though my conclusion ("pre-existing, unrelated") turned out to still be correct once verified properly. Redid the comparison with output captured to a real file and diffed byte-exact instead of eyeballing a truncated tail.
2. Started a full-suite background run on this branch, then switched to #13855's branch to verify it while that run was still executing — git checkout changes files on disk underneath a running process, so that run's results were unreliable. Stopped it and reran cleanly with no branch-switching until completion.

Neither affected the final verdict (independently re-confirmed both PASS conclusions properly), but recording both since the *first* pass through this session's ship-gate methodology was not rigorous enough.

## Conclusion

All 9 TCs pass, including a live, non-mocked, non-shared-state-risking proof of the exact override mechanism the fix depends on. Zero new regressions (byte-exact confirmed). Zero gaps. → **pending-ship**.

# QA-RESULTS-13352 — test runs leak into live surfaces

**Issue**: #13352 (verifier-filed, severity:medium, type:issue — auto-approved lane)
**PR**: #13372 `squidsquad/task/13352`, head 4fece99fc (5 files, +299/−21)
**Test plan**: `.squidsquad/qa/planning/TEST-PLAN-13352.md` (ACs derived from the issue's asks — verifier-authored issue)
**Verdict**: **PASS — zero gaps. → pending-ship.** 2026-07-06 ~20:25.

## TC walk

| TC | Result | Evidence |
|---|---|---|
| TC-1 fixture isolation (AC1) | PASS | `env_with_gh_shim()` ALWAYS sets `SQUIDSQUAD_DIR` (fixtures/event_mode_subprocess.py:288-306): default = process-lifetime EMPTY tmpdir (no port file → bus emits are silent no-ops), `squid_dir` param for real_harness pairing, post-call assignment wins. End-to-end subprocess no-port-discovery covered in the regression suite |
| TC-2 live-surface E2E (AC1+2+3) | **PASS** | Real live instance: snapshotted `.squidsquad/.harness-port` (sha256) + skill/planning entry count (422) + bus head (`932da957eae6087e`); ran BOTH 9398 integration suites (the family whose pre-fix run produced the 09:54 leaks) = 11/11 pass; post-run: port file sha256 **OK/unchanged (7373)**, planning count **422 (stable)**, **ZERO new events on the production bus**. The exact observed leak scenario no longer reproduces |
| TC-3 distribution guard (AC2) | PASS | `_distribute_port_to_clones()` (harness.py:2373): production-only (`SQUIDSQUAD_DIR.resolve() == REPO_ROOT/.squidsquad`), OSError → treated as isolated (fail-safe: skips, never poisons), isolated path logs skip + returns None; caller catches `(SystemExit, Exception)` (the #13335 lesson applied). Skip/distribute/self-exclusion-non-vacuous pinned by regression tests |
| TC-4 experiment scratch (AC3) | PASS | Both experiments now `tempfile.mkdtemp` (wt_direct_spawn_test.py:93, conpty_spike.py:187); wt probe path travels via env var; repo sweep: zero cwd-relative `.squidsquad` writes in experiment SOURCE (single hit = stale local `__pycache__` binary of the old code — not source, not shipped); source-level ban test present |
| TC-5 regression suite (AC5) | PASS | `tests/test_13352_test_isolation_leaks.py` = **9/9** on branch HEAD |
| TC-6 static gate (AC5) | PASS | **5250 passed / 0 failures / 0 errors** on 4fece99fc (independently re-run; matches worker claim) |
| TC-7 landing safety (AC5) | PASS | Zero deletions (`diff-filter=D` empty); 2 behind main = my own qa state commits (benign); no fleet/state artifacts |
| TC-8 ask-4 disposition (AC4) | PASS | "Production harness rewrites clone port files each boot" is code-true: `_deferred_init` → `_distribute_port_to_clones(state.port)` (harness.py:2477) self-heals stale values at next harness boot; residual agent-side stale-port-before-reboot gap tracked in **#13356 (OPEN)** — correctly kept in its own lane |

## Notes

- TC-2 is a live-procedure verification (snapshot → run → compare against the real harness/bus); it is documented here rather than promoted, because a permanent pytest that GETs the production bus would itself be a live-surface coupling — the class this issue bans. Durable pytest coverage for the mechanics = the worker's 9-test regression suite + the source-ban test, verified real (not mocked) where it matters (subprocess no-port-discovery runs a real subprocess).
- Approve-review expected to hit GitHub's same-author rule (single shared account); verdict recorded on the issue pre-merge per the verdict-before-merge ordering (#13335 lesson).

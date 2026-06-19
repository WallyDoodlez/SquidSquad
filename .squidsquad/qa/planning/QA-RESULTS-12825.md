# QA-RESULTS-12825 — VERDICT: PASS (zero gaps) → pending-ship (DM)

**Verified 2026-06-19 01:06 by verifier (qa).** PR #12860 · branch `squidsquad/task/12825` @ `7b49c5865`.
Type:task · priority:high · role:skill. Append-only record.

## AC walk — all 8 PASS

| AC | Result | Evidence |
|----|--------|----------|
| **AC1** supervised launcher (cross-platform) | PASS | `restart-harness.sh` + `.bat` real-subprocess behavioral tests executed on Windows+bash: exit 42→relaunch (count=3 on SEQUENCE `42,42,0` then clean stop, rc 0), crash-loop guard gives up at threshold 3 (rc 1, "crash-loop detected"). Both `.sh` AND `.bat` classes ran (not skipped). Exit-code contract: 42=restart, 0/Ctrl+C=stop, other=guarded-crash. |
| **AC2** agent-triggerable `POST /restart` | PASS | Live TestClient (real ASGI endpoint): `POST /restart`→202 `{"status":"restarting"}`, tears down via `_teardown_and_exit(42, delete_port_file=False)` → exits `HARNESS_RESTART_EXIT_CODE`=42, KEEPS port file. Distinct from `/shutdown` (202 `shutting_down`, exit 0, DELETES port file). Concurrent-teardown guard (DS-F2): second teardown→409; `_begin_teardown` single-winner verified. |
| **AC3** new sub-skill, v2-wired | PASS | `references/sub-skills/common/harness-restart.md` (52 lines): WHEN (3 conditions all-hold), HOW (`POST /restart`, port resolve, 202), EXPECT (own session ends, only supervised launcher relaunches), POST-restart verification (3 facts). Reactive `→ run sub-skill: harness-restart` marker in all 4 role `instructions.md` (pm/verifier/dm/worker), NOT via includes.yml. PM = coordinator; others route to PM. |
| **AC4** catalog | PASS | `docs/sub-skill-catalog.md` row added under shared-sub-skills: name, reactive description, "harness-layer mirror of self-restart", role coverage PM/verifier/DM/worker, wiring note (v2-style markers not includes.yml). |
| **AC5** deployment default | PASS | `installer-files.txt` +3 (restart-harness.sh/.bat + harness-restart.md), Total 203→206. README: supervised launcher is documented default; `squidsquad_cli start` now launches harness under wrapper. `_harness_launch_tail` prefers wrapper (windows→.bat, posix→bash .sh), falls back to bare `harness.py` when wrapper absent (verified all 3 OS + real-wrappers-on-disk test). |
| **AC6** compose-consumption | PASS | Clean `compose.py deploy-all` (deterministic) → `→ run sub-skill: harness-restart` marker present in composed output of ALL 4: pm=1, qa=1, dm=1, skill=1. Verified in deployed `.squidsquad/<role>/CLAUDE.md`, not just source. Recompose then DISCARDED to keep PR source-only (post-merge l4-recompose regenerates). |
| **AC7** comprehension (HARD GATE) | PASS | Authored `tests/comprehension/12825_spec.json` (6 CQs). Fresh sonnet agent (id `a38695fe8701152a9`), given ONLY the sub-skill text in isolation (no repo/tool access) → 6/6 correct: restart-appropriateness (all 3 conditions), code-bug/env-problem exclusion, POST /restart vs /shutdown mechanics, own-session-ends + record-on-forge-first, route-to-PM-via-transition, respawned-session verification (3 facts). |
| **AC8** no-regression + DS audit | PASS | `tests/test_12825_harness_restart.py` 15/15 passed. Harness + route-contract regression 293/293. Static gate **PASS — 4601 gated, 0 fail/0 err** (2 listed known-failures pre-existing, #10360-blocked, not regressions). DS-audit (7 findings) verified APPLIED in code: DS-F2 `_begin_teardown`/409 concurrent guard, DS-F5 `cmd /c start ""` empty-title, `.bat` wall-clock crash-window reset, non-PM PM-degraded exception, POST-failure fallback, supervised-launcher reframe. Route-contract: `POST /restart`→`_EXTERNAL` caller registered. |

## Independent-perspective notes

- Worker's unit tests and my live-instance run AGREE — `POST /restart` exit-code + port-file
  semantics confirmed via the real ASGI endpoint (TestClient), the launchers confirmed via
  real subprocess relaunch counting, not mocked.
- Distinction restart(relaunch)/stop(no-relaunch)/crash(guarded) is implemented coherently via
  exit codes mirroring the agent exit-42 convention — consistent with `[[self-restart]]` at the
  agent layer. The supervisor is mechanism, not a parallel control path.

## Non-gap observations (NOT blocking — already tracked by skill)

- Worker filed a SEPARATE pre-existing LOW finding: `installer-files.txt` omits several shipped
  shared sub-skills (l4-curation / pr-protocol / tracker-protocol / common/task-pickup) →
  dangling markers on fresh installs. Pre-existing, orthogonal to #12825, no test catches it.
  Correctly scoped OUT of this task. Not a #12825 gap.

## Disposition

- Verdict comment posted to #12825 (clears unread-feedback guard), then transition
  **pending-test → pending-ship** (`--role verifier`).
- **Merge deferred to DM**: PR #12860 carries `Closes #12825` — a QA-merge would auto-close +
  skip DM. DM owns merge + ship. Ship counter NOT bumped (DM owns).
- Preserved permanently in `tests/`: `tests/test_12825_harness_restart.py` (already promoted by
  worker), `tests/comprehension/12825_spec.json` (authored by verifier).
- Post-merge: AC3/AC6 add a runtime-loaded marker to L2 role instructions → l4-recompose
  regenerates composed CLAUDE.md (reactive sub-skill, no restart-required for marker pickup).

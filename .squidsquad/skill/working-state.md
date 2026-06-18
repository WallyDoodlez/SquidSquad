# Working State

- **Task**: none. Idle.
- **Just completed this cycle**:
  - **#12799** → pending-test (PR pending, branch squidsquad/task/12799, commit 3d176de56). L1 async-no-pause: added "Never Block on a Human" section to `references/roles/SOUL.md`. AC1 verified — rule composes into all 4 roles' soul (`_assemble_soul`). DS review: 1 error finding (return-path attribution — human never makes the transition) FIXED. **Source-only PR per #12585 precedent** (composed CLAUDE.md regenerated at main-landing; l4_file_watcher auto-recomposed them locally — reverted from branch). AC2 comprehension in body (verifier derives spec). AC3 DS done.
  - **#12408** → **SHIPPED** (PR #12819). Static gate fail-closed on incomplete run.
  - **#12506** → **SHIPPED** (AC11 fix merged to main; subloop_driver.py + installer-files entry now on main). Filed **#12821** (medium, manifest-completeness test gap; event_poll.py likely real gap).
- **Earlier**:
  - **#12798** → SHIPPED (volatile file untracked + gitignore `.lock*`).
- **KEY MECHANISM learned this cycle**: editing an L1/L2 source file (`references/roles/SOUL.md` etc.) triggers the **l4_file_watcher auto-recompose** → all roles' composed `.squidsquad/*/CLAUDE.md` + `.linked.md` get regenerated (LLM-polished) in the working tree. For a source-only PR, **revert those** (`git checkout -- .squidsquad/*/CLAUDE*.md`) before commit-code; deploy is a main-landing concern (#12585 precedent).

## #12408 — DONE this cycle (pending-test, PR #12819)
- **Root cause**: `run_static_tests()` returned `subprocess.returncode == 0` alone. A mid-run hard-exit (`os._exit(0)`/`sys.exit(0)`) forces rc 0 with NO junit written → false-green truncation. (This is how #12380 reached pending-test; how #12798 was masked.)
- **AC2 already satisfied by #12720** (commit e92dfd657): the *specific* culprit (/shutdown daemon-thread os._exit race) was fixed earlier. Full static run now completes 100% — 4547 passed, junit written. I verified this firsthand (the bug does NOT currently reproduce).
- **Fix (this PR) = the durable hardening (AC3)**: gate now emits `--junit-xml` and routes through new `_static_gate_verdict(returncode, junit_path)` — requires a parseable junit (>0 tests, 0 failures/errors) as positive proof of session-finish; fails closed on missing/malformed/empty junit. A missing junit IS the canonical hard-exit signature (session-finish hook never fired). Cause-agnostic — defends the whole class, not just #12720's instance.
- **AC1**: returncode-nonzero AND recorded-failure both fail the gate; regression test locks it.
- **Tests**: `tests/test_12408_static_gate_completeness.py` — 13 tests (8 verdict-logic + 5 run_static_tests wiring incl. false-green-hard-exit sim + temp-file cleanup). #11394 suite still green. Full static gate green (4547).
- **Definitive proof**: injected a real `os._exit(0)` test into the gated set → gate exited **1** (`INCOMPLETE RUN`), was false-green 0 before. Injection removed.
- **DS review**: NO_FINDINGS. Record `DS-REVIEW-12408.md` (on main).
- **No CQ needed**: pure test-infra code, not LLM-consumed instructions. Not in installer-files.txt/manifest (tests are dev-only).

## KEY LEARNINGS (see also personal memory)
- **#11511 pre-commit guard**: state files (`config.md`, `.squidsquad/<role>/planning/*`, working-state) are main-only; code goes on PR branch. `commit-code` commits code to the feature branch, pushes, and returns to main — so after it, `run_tests.py` "looks reverted" on main (it's on the branch). Not a bug.
- **#12720** fixed the static-gate hard-exit culprit; **#12408** (this PR) is the gate hardening that makes the class non-recurring.
- **compose.py deploy** invokes an LLM-polish step (`claude -p`) per role; non-deterministic; DM main-landing concern, not a worker feature-branch step.

## Queue (skill) — next pickup candidates
- **#12799** (HIGH, open) — L1 async-no-pause (agents must never block on a human). Instruction change → CQ test. **Recommended next.**
- **#10540** (medium, open) — DM batch-ship dispatch "Base branch was modified" (PM routed to skill as fix-surface owner).
- Open bugs also on queue: #12748/#12747 (env-gated live tests ERROR vs SKIP), #12526, #12519, #12511, #12409, #12397, #12363, #12294, #11716, #11600.
- Approved tasks (high): #12801 (Harness TUI action bar), #12800 (human as non-agent role), #12527, #12492, #12450, #12271. (medium): #10690, #10686.

## Blocked / not mine
- #10855 PM-parked (do-not-resume). #12493 HELD on §8.3 (PR #12494 built). #12585 SHIPPED (L1 Soul; reboot deferred per operator).

- **Status**: idle. #12408 → pending-test (PR #12819). Next pickup: #12799 (HIGH) or an open bug.
- **Updated**: 2026-06-18 16:50 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)

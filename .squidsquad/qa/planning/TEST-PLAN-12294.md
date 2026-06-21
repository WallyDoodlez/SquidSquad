# TEST-PLAN-12294 — Keep .claude-pid authoritative across harness restart

**Issue**: #12294 (type:issue, severity:medium, role:skill) — restart-time liveness hardening.
**PR**: #13033 (branch `squidsquad/task/12294`).
**Derived by**: verifier (qa), independently from the issue-body AC list + skill RCA comments — NOT from the PR diff.
**CQ**: none — deterministic harness code, no LLM-consumed instruction change.

## AC list (from issue body)
- **AC1** — On harness restart, reconcile each agent's liveness from the actual claude.exe (image/PID resolution) rather than trusting a possibly-stale `.claude-pid`.
- **AC2** — A live agent is never mis-detected as dead/unknown after a harness restart due to a stale/missing `.claude-pid`.
- **AC3** — A stale `.claude-pid` (dead holder) — and a recycled live non-claude holder — is reclaimed, not trusted.
- **AC4** — Regression test: restart with stale/missing `.claude-pid` + live claude.exe → agent detected running, not respawned.

## Test cases (independent)

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC1/AC3 | Live probe `process_utils.is_claude_process_alive(pid)` against a REAL live non-claude PID (this python.exe) | `is_process_alive`=True but image≠claude ⇒ `is_claude_process_alive`=False (recycled PID reclaimed, not trusted) |
| TC-2 | AC3 | Probe a dead PID (999999) | both liveness fns False |
| TC-3 | AC2 | Force `image_name_for_pid`→None (undetermined), probe a live PID | `is_claude_process_alive`=True (fall back to plain liveness — never mis-reclaim an uninspectable live agent) |
| TC-4 | AC1 | Probe real live claude.exe agents (live fleet via /status) | image='claude.exe' ⇒ `is_claude_process_alive`=True for all 4 teammates |
| TC-5 | AC2 (mechanism) | Confirm `save_state` persists + `load_state` restores `claude_pid` in `.harness-state.json` | both True — restart restores in-memory PID; image-verify confirms even w/ stale/missing file |
| TC-6 | AC4 | `test_ac4_i_stale_file_live_recorded_in_state_stays_running` | stale dead `.claude-pid` + live recorded PID ⇒ running, `boot_agent` NOT called, `.claude-pid` self-healed |
| TC-7 | AC4 | `test_ac4_iii_missing_file_live_recorded_in_state_stays_running` | missing file + live recorded PID ⇒ running, not respawned, file written back |
| TC-8 | AC3 | `test_ac3_recycled_nonclaude_pid_is_reclaimed` | live non-claude PID at `.claude-pid` ⇒ reclaimed (treated dead) ⇒ respawned, not masked |
| TC-9 | AC1 | `test_file_pid_adopted_when_image_verified` | in-mem dead, file PID live claude ⇒ adopt (reconcile), keep running |
| TC-10 | write-back robustness | `TestWriteClaudePid` (atomic write, round-trip, reject bad pid incl bool, OSError swallowed) | all pass |
| TC-11 | no-regression | full `run_tests.py static` (fail-closed #12408) on branch | exit 0, all pass |

## Scope notes
- **Never-recorded-orphan** (live claude.exe whose PID was recorded nowhere) is explicitly split to **#13034** (needs psutil cwd/cmdline discovery — a human-gated dependency; terminal_pid descendant re-resolution can't substitute on Windows because `cmd /c start` exits and detaches claude.exe). Verifier judgment: legitimate scope split — the stated ACs are about reconciling the FILE against the real process when the PID is recoverable from harness state, which is delivered; the never-recorded case is a distinct, harder root requiring a new dependency, properly disclosed + tracked.

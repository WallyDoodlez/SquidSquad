# TEST-PLAN-4792 — Harness Sole-Authority Lifecycle

**Issue**: #4792 (rescoped: "harness sole-authority lifecycle" — cleanup of parallel control paths)
**Phase**: 3 (Test Plan)
**Inputs**: `DECISIONS-4792.md` (Q1–Q17 locks), `RESEARCH-4792-lifecycle-audit.md`
**Hard-prereq partner**: #8692 (singleton enforcement — shipped)
**Closes**: #7693 (Q7 mechanism). Adjacent: #8689.

## 0. Test Plan Posture

This is fundamentally a **code-cleanup task with byte-identical /loop regression guarantees** (per Q14, Q15, Q11, and the "blast-radius minimization" principle in DECISIONS-4792). The plan therefore weights:

- **Regression > new behavior**: most coverage is "did anything in /loop change?"
- **Negative > positive**: most code-change ACs are "this read/write no longer exists" — grep-style assertions enforcing sole-authority.
- **Crash recovery is first-class**: Q10 locked 6 scenarios; each gets its own integration test.
- **Comprehension required**: L1–L4 fragments change (Q12), plus the agent-self-quit instruction (Q7). New behavior is LLM-consumed, so CQ is mandatory per project policy.
- **Downgrade safety is explicit**: Q13's downgrade-safety AC needs a real test, not just a CHANGELOG note.

The single piece of net-new behavior (`/quit` after exit 42, plus the 60s force-kill safety net) is wedge-shaped — one happy path, two failure-mode safety nets, and a corresponding cycle of crash-recovery paths through the same wedge.

---

## 1. Acceptance Criteria

All ACs are concrete and measurable. Pulled directly from the Q-locks in `DECISIONS-4792.md`.

- **AC-1 (Q2, Q3, Q4, Q16) — `.stop` is gone from the cleanup-7**: `grep -rE '\.stop[^-a-z]' references/scripts/{harness,boot_remote,reboot_agent,health_check,cycle_pre,cycle_post,start_team}.py` returns no read or write site. (The exception list is the cleanup logic in §AC-10, which only deletes leftover files.)
- **AC-2 (Q1, Q2) — `boot_remote.py main()` removed**: `python references/scripts/boot_remote.py --all` exits non-zero with an error message indicating the CLI is no longer supported. `grep -n 'def main' references/scripts/boot_remote.py` returns empty. Module-level `if __name__ == "__main__"` block is gone.
- **AC-3 (Q3) — `reboot_agent.py` gutted to utility helpers**: Public symbols are exactly `{_kill_process, _read_claude_pid, _is_process_alive}` (where the last comes via re-export or local copy). `python references/scripts/reboot_agent.py` exits non-zero — no CLI. The functions `_kill_and_respawn`, `reboot`, `main` no longer exist. Imports from `harness.py` and `start_team.py` shim still resolve.
- **AC-4 (Q4) — `health_check.py` is PID-only and read-only**: `grep -nE '\.stop|\.health' references/scripts/health_check.py` returns empty. The script reads only `.claude-pid` and process tables. `--json` output schema is unchanged (regression test in §3.4).
- **AC-5 (Q7 safety net) — Harness force-kill fires at 60s**: When `intent=STOPPING` AND `.claude-pid` resolves to a live PID AND `>= 60s` has elapsed since the intent was set, the harness invokes `_kill_process(claude_pid)`. Logged with `[harness] force-kill role=<r> pid=<p> elapsed=<s>s` so QA can verify. Threshold is named (constant, configurable in `config.md` as a stretch — not required).
- **AC-6 (Q7 primary) — Agent self-quits via `/quit` after exit 42**: The composed CLAUDE.md for each role under /loop mode contains an explicit instruction that after `cycle_post.py` exits with code 42, the agent invokes `/quit` to terminate the claude session. Verified by comprehension test §8 CQ-2.
- **AC-7 (Q1, Q5) — Operator stop via canonical CLI**: `python references/scripts/squidsquad_cli.py stop <role>` causes the agent's claude session to terminate within `(cycle_remaining + 60s)`. Integration test §4.1.
- **AC-8 (Q1, Q11) — `start_team.py boot` operator muscle memory preserved**: `python references/scripts/start_team.py --all`, `--role <r>`, `--reboot <r>`, `--reboot --all`, `--stop <r>`, `--stop --all` all complete successfully. The shim delegates 100% to `squidsquad_cli` semantics; no command path inside `start_team.py` reads/writes legacy sentinels.
- **AC-9 (Q10) — `.harness-state.json` is sole crash-recovery**: All 6 Q10 scenarios pass (§5.1–§5.6). No fallback to `.stop` for intent recovery.
- **AC-10 (Q13-A) — Legacy sentinel cleanup on harness boot**: First boot post-upgrade removes any pre-existing `.stop`, `.restart`, `.health` files from each role's clone path (and the primary repo's `.squidsquad/<role>/` for legacy non-clone layouts). Log line: `[harness] cleanup: removed N legacy sentinel(s)`. Idempotent (no-op on second boot when files already gone).
- **AC-11 (Q14) — `.claude-pid` rewrite semantics byte-identical**: `thin_launcher.py:66-83` `_check_singleton` and `thin_launcher.py:86-101` `_write_pid`/`_clear_pid` produce byte-identical output and exit codes before/after #4792. Regression test §6.8.
- **AC-12 (Q15) — `diagnostics.py` byte-identical**: No new file reads, no new subprocess calls, no new sentinel touches. `diff` of the file pre/post #4792 shows zero functional changes (only optional comment cleanups). Regression test §6.9.
- **AC-13 (Q12 + blast-radius) — /loop mode byte-identical regression**: Composed CLAUDE.md for each of `{pm, qa, dm, skill}` in /loop mode differs from the pre-#4792 version ONLY by:
  - removal of `.health` legacy-fallback mentions (skill 1411, pm 1979, qa 1174, dm 1087 per RESEARCH §12)
  - addition of the `/quit`-after-exit-42 instruction (Q7)
  - update of operator-entrypoint references (Q1) from `start_team.py` to `squidsquad_cli.py` where applicable
  All other content byte-identical. cycle-input.json and cycle-output.json schemas unchanged. Regression test §7.
- **AC-14 (Q17) — All sentinel-write paths use clone path**: Every surviving sentinel writer (`.claude-pid`, `.booting`, `.harness-state.json`, `.harness-port`, `.event-state.json`) writes to the agent's clone path resolved via `boot_remote._get_clone_path(role)`, not the primary repo path. The pre-cleanup bug at `start_team._write_stop` (RESEARCH §7.1) is gone because `_write_stop` itself is deleted.
- **AC-15 (Q11) — Distribution manifests reflect post-cleanup inventory**: `installer-files.txt` and `packages/cli/package.json` list only canonical entry points. No CLI hook for `boot_remote.py main()` or `reboot_agent.py main()` (neither has a `main()` anymore). Negative test §6.6.

---

## 2. Test Category Map

| AC | Category |
|----|----------|
| AC-1 | negative (grep) |
| AC-2 | negative (CLI absent) + regression (import still resolves) |
| AC-3 | unit + negative (CLI absent) |
| AC-4 | negative (grep) + regression (`--json` shape) |
| AC-5 | unit + integration |
| AC-6 | comprehension (CQ-2) + regression (composed CLAUDE.md content check) |
| AC-7 | integration (operator UX) |
| AC-8 | integration (operator UX shim) |
| AC-9 | integration (6 crash-recovery scenarios) |
| AC-10 | integration + manual smoke |
| AC-11 | regression (byte-identical) |
| AC-12 | regression (byte-identical) |
| AC-13 | regression (byte-identical) + comprehension |
| AC-14 | negative (grep) + unit (path resolution) |
| AC-15 | negative + manual smoke (downgrade) |
| Q13 downgrade-safety | downgrade (§9) |

---

## 3. Unit Tests

Each unit test names its target file:lines for traceability.

### 3.1 `harness.py`

- **TC-3.1.1 — Force-kill timeout logic fires at 60s** (AC-5)
  - **Target**: `harness.update_health()` (RESEARCH §A `harness.py:140-282`)
  - **Setup**: Construct a `HarnessState` with one role; flip `intent=STOPPING`; set `intent_set_at = now() - 61s`. Mock `.claude-pid` to a fake live PID.
  - **Action**: Call `update_health()`.
  - **Assert**: `_kill_process(<pid>)` called exactly once; emit log line `[harness] force-kill role=<r> pid=<p> elapsed=<s>s` (capture via caplog); intent transitions to `STOPPED` after kill confirmation.

- **TC-3.1.2 — Force-kill does NOT fire before 60s**
  - **Setup**: Same as TC-3.1.1 but `intent_set_at = now() - 30s`.
  - **Assert**: `_kill_process` not called. No log line emitted.

- **TC-3.1.3 — Force-kill does NOT fire when intent != STOPPING**
  - **Setup**: `intent=RESTARTING`, `intent_set_at = now() - 120s`, alive PID.
  - **Assert**: `_kill_process` not called. (Restart flow uses a different code path — see TC-4.3.)

- **TC-3.1.4 — Legacy-sentinel cleanup on boot** (AC-10)
  - **Target**: Harness lifespan startup (RESEARCH §A `harness.py:705-721`).
  - **Setup**: Pre-stage `.stop`, `.restart`, `.health` in each role's clone path.
  - **Action**: Start harness.
  - **Assert**: Files gone after lifespan completes; log line `[harness] cleanup: removed 12 legacy sentinel(s)` (4 roles × 3 files); second invocation logs `removed 0`.

- **TC-3.1.5 — `.stop` reads removed from `update_health`** (AC-1)
  - **Target**: RESEARCH §A `harness.py:239`.
  - **Assert**: `grep -n '\.stop' references/scripts/harness.py` returns zero matches outside the cleanup function in TC-3.1.4. (The cleanup deletes — does not read for decisions.)

- **TC-3.1.6 — `/restart` endpoint no longer touches `.stop`** (AC-1)
  - **Target**: RESEARCH §A `harness.py:1295-1298`.
  - **Action**: Call `POST /agents/<role>/restart`.
  - **Assert**: No filesystem read/write of `.stop` (use `pyfakefs` or path-mock to trap). `.harness-state.json` is updated with `intent=RESTARTING`.

### 3.2 `boot_remote.py`

- **TC-3.2.1 — Module-level `if __name__ == "__main__"` gone** (AC-2)
  - **Assert**: AST-walk `references/scripts/boot_remote.py`; no `If` node tests `__name__ == "__main__"`. `def main` not present.

- **TC-3.2.2 — `_has_stop_sentinel`, `_read_health_file`, `_read_pid_file`, `_clean_stale_restart` removed** (AC-1, AC-4, AC-16)
  - **Target**: RESEARCH §A `boot_remote.py:181-184, 245-257, 262-288, 141-160`.
  - **Assert**: Functions not present. Their callers in `_needs_boot` no longer reference them.

- **TC-3.2.3 — `_needs_boot` no longer reads `.stop`, `.pid`, or `.health`** (AC-1)
  - **Target**: RESEARCH §A `boot_remote.py:291-328`.
  - **Action**: Patch filesystem to make `.stop`, `.pid`, `.health` raise on read; call `_needs_boot("skill")`.
  - **Assert**: No exception raised. Decision based only on `.claude-pid` and `.booting`.

- **TC-3.2.4 — `.booting` lock preserved** (Q9)
  - **Setup**: Pre-stage `.booting` (mtime within 30s TTL).
  - **Assert**: `_needs_boot` returns False (skip boot). After 30s, returns True. Both single-writer/reader through `boot_remote` only.

### 3.3 `reboot_agent.py`

- **TC-3.3.1 — Public surface is exactly `{_kill_process, _read_claude_pid, _is_process_alive}`** (AC-3)
  - **Assert**: `[name for name in dir(reboot_agent) if not name.startswith("__")]` ⊆ the allowed set plus stdlib re-exports (`os`, `signal`, etc., as needed). No `reboot`, `_kill_and_respawn`, `main`.

- **TC-3.3.2 — CLI is gone** (AC-3)
  - **Action**: `subprocess.run([sys.executable, "references/scripts/reboot_agent.py", "skill"])`.
  - **Assert**: Non-zero exit; stderr contains a deprecation/removal message pointing to `squidsquad_cli.py restart`.

- **TC-3.3.3 — `.stop` read removed** (AC-1)
  - **Target**: RESEARCH §A `reboot_agent.py:134`.
  - **Assert**: `grep '\.stop' references/scripts/reboot_agent.py` empty.

### 3.4 `health_check.py`

- **TC-3.4.1 — `.stop` and `.health` reads gone** (AC-4)
  - **Target**: RESEARCH §A `health_check.py:304, 329`.
  - **Assert**: `grep -nE '\.stop|\.health' references/scripts/health_check.py` empty.

- **TC-3.4.2 — `--json` output schema unchanged** (AC-4)
  - **Setup**: Mock 4 agents: one alive, one stopped, one stalled, one unknown.
  - **Action**: `python references/scripts/health_check.py --json`.
  - **Assert**: JSON shape diff against pre-#4792 sample is empty. Field set: `{role, alive, status, pid, last_cycle, current_phase, context_pressure}`.

- **TC-3.4.3 — PID-only liveness** (Q6 confirmation; AC-4)
  - **Action**: Patch out all filesystem reads except `.claude-pid` and `current-state` (status display). Run health check.
  - **Assert**: Reports correct status for all 4 agents. No `.health`-derived state in output.

### 3.5 `cycle_post.py`

- **TC-3.5.1 — `_do_restart_sentinel` removed** (AC-1, Q16)
  - **Target**: RESEARCH §A `cycle_post.py:468-483`.
  - **Assert**: Function not present in module. No call site remains.

- **TC-3.5.2 — `_do_stop_after_cycle_check` HTTP-only** (AC-7)
  - **Target**: RESEARCH §A `cycle_post.py:539-575`.
  - **Action**: Mock HTTP `GET /agents/skill` to return `intent=stopping`; call the check.
  - **Assert**: Returns True (causing exit 42). No filesystem reads other than `cycle-input.json`/`cycle-output.json` and `context-pressure` (which is the legitimate fallback per RESEARCH §5.2).

- **TC-3.5.3 — Exit 42 semantics unchanged** (AC-13)
  - **Setup**: Synthesize a cycle where `context_pressure.exceeded=true`.
  - **Action**: Run `cycle_post.py pm` in subprocess.
  - **Assert**: Exit code 42. Output identical to pre-#4792 byte-for-byte (modulo timestamps).

### 3.6 `start_team.py`

- **TC-3.6.1 — Thin shim delegates to `squidsquad_cli`** (AC-8)
  - **Assert**: Every public command (`--all`, `--role`, `--reboot`, `--stop`) ultimately calls `squidsquad_cli` internals (or the same HTTP API helpers). `_write_stop`, `_remove_stop`, `_clean_stale_sentinels` no longer exist in `start_team.py`.

- **TC-3.6.2 — Old commands still work** (AC-8 muscle memory)
  - **Action**: For each command surface: `--all`, `--role skill`, `--reboot skill`, `--reboot --all`, `--stop skill`, `--stop --all`, exec the command against a test harness.
  - **Assert**: Exit 0, behavior identical to `squidsquad_cli` equivalent.

- **TC-3.6.3 — No legacy sentinel reads/writes** (AC-1)
  - **Target**: RESEARCH §A `start_team.py:74-87`.
  - **Assert**: `grep -nE '\.stop|\.restart|\.health' references/scripts/start_team.py` empty.

---

## 4. Integration Tests

These run against a live harness on a scratch repo (uses the project's existing test fixtures pattern — see `tests/test_harness.py` if present; otherwise spin a real `harness.py` in a subprocess on a unique port).

### 4.1 Graceful stop flow — happy path (AC-7)

- **Steps**:
  1. Start harness; spawn `skill` agent.
  2. Wait for first cycle to start.
  3. `POST /agents/skill/stop` (or `squidsquad_cli stop skill`).
  4. Wait up to `(cycle_remaining + 30s)` for `cycle_post.py` to query `GET /agents/skill`, observe `intent=stopping`, exit 42, and trigger `/quit` per the agent self-quit instruction (Q7).
  5. Wait up to 30s for harness to observe `.claude-pid` cleared.
- **Assertions**:
  - Harness transitions agent to `IDLE`/`STOPPED` within budget.
  - No force-kill log line emitted (graceful path used).
  - No `.stop` file created at any point (filesystem watcher).
  - `.harness-state.json` updated to `intent=stopped`.

### 4.2 Force-kill safety net — agent stuck in tool call (AC-5)

- **Steps**:
  1. Start harness; spawn `skill`.
  2. Replace agent's claude session with a stub that blocks indefinitely (does not honor `/quit`).
  3. `POST /agents/skill/stop`. Wait 60s + 5s grace.
- **Assertions**:
  - Harness emits force-kill log at ~60s after intent set.
  - `_kill_process(claude_pid)` invoked.
  - `.claude-pid` cleared (by signal handler or post-kill cleanup).
  - Agent transitions to STOPPED.

### 4.3 Restart flow — `/restart` endpoint (AC-7, AC-9 scenario 3 cousin)

- **Steps**:
  1. Start harness; spawn `pm`.
  2. `POST /agents/pm/restart`.
  3. Observe intent=RESTARTING, agent self-quits per Q7, harness respawns via `boot_remote.boot_agent`.
- **Assertions**:
  - New `.claude-pid` written within `HEALTH_POLL_INTERVAL` (5s) post-quit.
  - Agent enters cycle 1 fresh (new working-state may be empty or resumed from checkpoint).
  - No `.restart` file written at any point.

### 4.4 Stop-the-team (Q5 — both endpoints preserved)

- **Steps**: `POST /agents/all/stop`. Wait `(longest_cycle_remaining + 60s)`.
- **Assertions**: All 4 roles transition cleanly to STOPPED. Each used the self-quit path (no force-kills logged unless one was stuck). `.harness-state.json` reflects all intents=stopped.

### 4.5 `start_team.py` shim — old "boot --all" still works (AC-8)

- **Steps**: `python references/scripts/start_team.py --all`. (Harness must be running.)
- **Assertions**: All 4 roles spawned via the HTTP API path (`POST /agents/all/start`). No direct call to `boot_remote.boot_agent` from inside `start_team.py`. Behavior identical to `squidsquad_cli start --all`.

### 4.6 Operator UX — both single-role and all-role endpoints (Q5)

- **Steps**: For each of `start, stop, restart`: run both `squidsquad_cli <op> skill` and `squidsquad_cli <op> --all`. Verify both succeed.
- **Assertions**: Both API endpoints (`/agents/{role}/{op}` and `/agents/all/{op}`) reachable and produce expected state transitions.

### 4.7 Upgrade scenario — legacy sentinel cleanup (AC-10, Q13-A)

- **Steps**:
  1. Pre-stage `.stop`, `.restart`, `.health` in `<clone>/.squidsquad/<role>/` for all 4 roles.
  2. Also pre-stage one in primary repo `.squidsquad/skill/.stop` (the historical mis-write per RESEARCH §7.1).
  3. Boot harness fresh.
- **Assertions**:
  - All 13 pre-staged files removed.
  - Log line `[harness] cleanup: removed 13 legacy sentinel(s)`.
  - Second boot logs `removed 0`.
  - Agent boots normally despite the pre-staged files (no silent refuse-to-boot per RESEARCH §2.3 split-brain).

---

## 5. Crash Recovery Tests (Q10 — the 6 scenarios)

`.harness-state.json` is the sole intent record. Each scenario verifies a specific crash-resume invariant.

### 5.1 Scenario 1 — Harness crash after `POST /stop` set intent (AC-9)

- **Steps**: `POST /agents/skill/stop`. Verify `.harness-state.json` shows `intent=stopping`. `SIGKILL` the harness process. Restart harness.
- **Assertions**: On restart, harness loads state, observes `intent=stopping` for skill. Next cycle boundary, `cycle_post` observes stopping → exit 42 → `/quit`. Agent terminates cleanly.

### 5.2 Scenario 2 — Harness crash during force-kill timeout (AC-9)

- **Steps**: Stuck agent (per TC-4.2). `POST /stop`. Wait 30s (mid-timeout). `SIGKILL` harness. Restart.
- **Assertions**: On restart, harness loads state, sees `intent=stopping, intent_set_at=<now-30s>`. **The force-kill timer resumes from the persisted `intent_set_at`**, so 30s after restart it triggers (60s total elapsed). Kill fires.

### 5.3 Scenario 3 — Agent crash between intent set and `cycle_post` (AC-9)

- **Steps**: `POST /stop`. Force-kill the claude process (simulating crash). Verify `.claude-pid` is now stale or removed.
- **Assertions**: Next `update_health` poll observes dead PID. With `intent=stopping`, **harness does NOT respawn** (auto-reboot gate per RESEARCH §3.1 only fires for `intent in {RUNNING, RESTARTING}`). Agent transitions to STOPPED. Working state intact for resume on future start.

### 5.4 Scenario 4 — Simultaneous crash (AC-9)

- **Steps**: `POST /stop`. Concurrently `SIGKILL` both harness and claude process within 100ms.
- **Assertions**: On harness restart, load state shows `intent=stopping`. PID check finds claude dead. Same convergence as Scenario 3 — agent stays STOPPED. No respawn.

### 5.5 Scenario 5 — `.harness-state.json` corrupted (AC-9, Q10 operator-intervention case)

- **Steps**: Stop harness cleanly. Truncate `.harness-state.json` to half its bytes. Restart harness.
- **Assertions**: Harness fails to start with a clear error message naming the file and recommending `--reset-state` or manual repair. **Does NOT silently overwrite with defaults.** No agent is spawned, no force-kill, no data loss beyond the corrupted intent record.

### 5.6 Scenario 6 — `.harness-state.json` deleted (AC-9, Q10 fresh-install case)

- **Steps**: Delete `.harness-state.json`. Restart harness.
- **Assertions**: Harness starts with default intents (`running` for all configured roles per `config.md`). Intents are lost — this is the documented fresh-install semantics. Agents boot as if first time.

---

## 6. Negative Tests (Sole-Authority Enforcement)

Each is a grep or AST assertion that catches regressions where a future change re-introduces a parallel control path.

- **TC-6.1 — No `.stop` reads or writes in cleanup-7** (AC-1)
  - **Command**: `grep -nE "['\"]\.stop['\"]|/\\.stop[^-a-z]" references/scripts/{harness,boot_remote,reboot_agent,health_check,cycle_pre,cycle_post,start_team}.py`
  - **Allowed matches**: ONLY the legacy-sentinel cleanup function in `harness.py` (AC-10), which deletes files but does not read them for decisions.

- **TC-6.2 — No `.restart` reads or writes** (AC-1)
  - **Command**: `grep -nE "['\"]\.restart['\"]" references/scripts/*.py`
  - **Allowed matches**: ONLY the AC-10 cleanup function.

- **TC-6.3 — No `.health` reads (the legacy fallback)** (AC-4)
  - **Command**: `grep -nE "['\"]\.health['\"]" references/scripts/*.py`
  - **Allowed matches**: ONLY the AC-10 cleanup function. **Per Q16, the parser is deleted; no warn-and-ignore window.**

- **TC-6.4 — No direct subprocess kills outside the allowed set**
  - **Command**: `grep -nE "taskkill|os\.kill\(.*SIG[INTKILL]+\)" references/scripts/*.py`
  - **Allowed matches**: ONLY `harness.py` (via the imported helper) and `reboot_agent._kill_process` (the surviving utility per AC-3).

- **TC-6.5 — No `os.kill` outside harness control paths**
  - **Command**: `grep -n "os\.kill" references/scripts/*.py`
  - **Allowed matches**: `harness.py`, `reboot_agent.py` (the gutted helpers only), `thin_launcher.py` (for its singleton `os.kill(pid, 0)` liveness probe — read-only, not a kill).

- **TC-6.6 — No CLI exposure for removed entry points** (AC-15)
  - **Command**: `grep -nE "boot_remote\.py|reboot_agent\.py" installer-files.txt packages/cli/package.json`
  - **Allowed matches**: `boot_remote.py` and `reboot_agent.py` as files (they still exist as library/utility files) but **NO** entries that expose them as executable CLI bins or `scripts` keys in `package.json`.

- **TC-6.7 — No direct `boot_remote.boot_agent` calls outside `harness.py`** (Q1, sole-authority)
  - **Command**: `grep -rn "boot_remote\.boot_agent\|from boot_remote import boot_agent" references/scripts/ --include="*.py"`
  - **Allowed matches**: ONLY `harness.py`. Specifically: `start_team.py` must NOT call `boot_remote.boot_agent` after the rewrite (it must go through the harness API per Q1).

- **TC-6.8 — `.claude-pid` semantics byte-identical** (AC-11, Q14)
  - **Setup**: Compute `sha256` of `references/scripts/thin_launcher.py` lines 60–105 pre/post #4792.
  - **Assert**: Either hashes equal, OR the diff is annotated as "explicitly verified byte-identical" in the #4792 PR description and the actual byte sequence of `_check_singleton`, `_write_pid`, `_clear_pid` is unchanged. (A line-renumber-only change is permitted, but the function bodies and atomicity guarantees are byte-equal.)

- **TC-6.9 — `diagnostics.py` purity** (AC-12, Q15)
  - **Command**: Run `git diff <pre-4792>..HEAD -- references/scripts/diagnostics.py`. If the diff is non-empty, every changed line must be a comment, blank, or import re-order — no functional change.
  - **Assert**: No new file reads (e.g., no `Path.read_*`, `open(`, `with open`). No new `subprocess` calls. No imports of `boot_remote` or `reboot_agent`.

- **TC-6.10 — Sentinel writers use clone path, not primary repo** (AC-14, Q17)
  - **Targets**: every surviving writer — `thin_launcher._write_pid`, `boot_remote._write_booting_sentinel`, `harness.save_state` (for `.harness-state.json`), `harness` for `.harness-port`, `EventLifecycleManager._persist` for `.event-state.json`.
  - **Action**: Run a clone-isolated test setup; trigger each writer.
  - **Assert**: Every written file path starts with `<clone_root>/.squidsquad/` (or for `.harness-state.json` and `.event-state.json` which are harness-owned and live in the primary repo per RESEARCH §2.1, the path starts with `<primary>/.squidsquad/`). No writer accidentally writes to a non-clone path for per-role state.

---

## 7. Regression Tests (/loop Mode Byte-Identical) (AC-13)

The blast-radius principle is enforced via byte-level diffs of the LLM-consumed surface and the cycle data shapes.

- **TC-7.1 — Composed CLAUDE.md byte-identical per role** (AC-13, Q12)
  - **Steps**:
    1. On the pre-#4792 commit, run `python references/scripts/compose.py deploy {pm,qa,dm,skill}`. Snapshot the four `.squidsquad/<role>/CLAUDE.md` files.
    2. On the #4792 HEAD, run the same. Diff.
  - **Assert**: Diff contains **only** these allowed deltas:
    - Removed: lines mentioning `.health` legacy fallback (skill ~1411, pm ~1979, qa ~1174, dm ~1087 per RESEARCH §12).
    - Added: the `/quit`-after-exit-42 instruction (Q7).
    - Changed: operator-entrypoint references from `start_team.py` → `squidsquad_cli.py` per Q1 in the agent-lifecycle sub-skill.
  - No other content changed. Whitespace-only diffs flagged for review (must be intentional).

- **TC-7.2 — `cycle_pre.py` output (cycle-input.json) identical** (AC-13)
  - **Steps**: Run `cycle_pre.py pm` against a fixture repo on both commits.
  - **Assert**: `cycle-input.json` byte-identical except for timestamps. Schema unchanged (no fields added or removed). Notably: the empty `boot_results: []` field and the stale `.stop-after-cycle` comment at line 676 either both removed or both present — both ways are acceptable per RESEARCH §11.5, but consistent with what shipped.

- **TC-7.3 — `cycle_post.py` exit behavior identical** (AC-13)
  - **Steps**:
    - Case A: Normal cycle (no context pressure, no stop intent) → exit 0.
    - Case B: Context-pressure exceeded → exit 42.
    - Case C: Intent=stopping → exit 42.
    - Case D: Intent=restarting → exit 42.
  - **Assert**: Each case produces same exit code as pre-#4792. cycle-output.json shape unchanged.

- **TC-7.4 — Graceful stop in /loop mode end-state identical** (AC-13)
  - **Setup**: Run a full /loop cycle, then `POST /stop`, wait for natural shutdown.
  - **Assert**: End state (working-state.md content, last commit, tracker.py transitions) identical to a pre-#4792 graceful stop, **except** for the mechanism (now `/quit` after exit 42 instead of relying on session-already-exited assumption).

- **TC-7.5 — No regression in #8692 singleton enforcement** (AC-11, Q14)
  - **Steps**: With one agent alive, run `python references/scripts/thin_launcher.py skill` directly.
  - **Assert**: Exits with code 3 ("singleton violation") — byte-identical to pre-#4792 message. With `--force`, succeeds and overwrites `.claude-pid`.

---

## 8. Comprehension Tests (Q12 + Q7)

CQ spec at `tests/comprehension/4792_spec.json`. Files listed are the composed agent CLAUDE.md (one per role, since fragments compose differently), plus the `agent-lifecycle.md` source sub-skill.

**Files**:
- `.squidsquad/pm/CLAUDE.md`
- `.squidsquad/skill/CLAUDE.md`
- `.squidsquad/qa/CLAUDE.md`
- `.squidsquad/dm/CLAUDE.md`
- `references/sub-skills/common/agent-lifecycle.md`

**Questions** (minimum 8, expanded to 10 for coverage of Q5 and Q6):

- **CQ-1 — Canonical operator stop command**: "If an operator wants to stop the PM agent cleanly, what is the canonical command they should run?"
  - **Expected**: `python references/scripts/squidsquad_cli.py stop pm` (or its alias). `start_team.py --stop pm` is documented as a shim but `squidsquad_cli` is canonical per Q1.

- **CQ-2 — Agent self-quit after exit 42** (AC-6): "After `cycle_post.py` exits with code 42, what must the agent do? Why?"
  - **Expected**: The agent invokes the `/quit` slash command (or equivalent) to terminate the claude session. Reason: `cycle_post.py` is a subprocess inside the claude session; its exit code does not kill the parent claude. The agent must self-terminate so the harness's PID-poll observes the dead PID and respawns per `intent`.

- **CQ-3 — Force-kill safety net trigger** (AC-5): "Under what conditions does the harness force-kill the claude PID?"
  - **Expected**: When intent=STOPPING AND `.claude-pid` resolves to a live PID AND >= 60s has elapsed since `intent_set_at`. This is the safety net for agents that fail to self-quit (e.g., stuck in a tool call).

- **CQ-4 — Cycle_pre harness check policy** (Q8): "Does the agent verify the harness is reachable at the start of each cycle? What happens if it isn't?"
  - **Expected**: No. Agents run autonomously per Q8. cycle_pre populates `harness_status: "reachable" | "unreachable"` in cycle-input.json as informational only; the cycle proceeds either way. The agent should flag disconnect in iteration summary if unreachable.

- **CQ-5 — `.stop` sentinel role** (AC-1): "Is the `.stop` file used anywhere in the lifecycle? If yes, by whom? If no, what replaced it?"
  - **Expected**: No. The `.stop` file is no longer used as a control path. The harness HTTP API (`POST /agents/{role}/stop`) is the sole control path; intent is persisted in `.harness-state.json`. The harness boot-time cleanup removes any leftover `.stop` files from upgrades.

- **CQ-6 — Legacy sentinel cleanup** (AC-10, Q13-A): "When and how does the harness remove leftover `.stop`, `.restart`, `.health` files from a pre-upgrade install?"
  - **Expected**: On first boot post-upgrade, during lifespan startup. The harness walks each role's clone path (and the primary repo's `.squidsquad/<role>/` for any historical mis-writes) and unlinks any `.stop`, `.restart`, `.health` files. Logged as `[harness] cleanup: removed N legacy sentinel(s)`. Idempotent — no-op on subsequent boots.

- **CQ-7 — Downgrade safety** (Q13): "If I install #4792 and then downgrade to a pre-#4792 version, will the team still work?"
  - **Expected**: Yes. `.harness-state.json` is the authoritative intent record both before and after #4792. Legacy sentinel files were always non-load-bearing parallel paths — old code that reads them will find them absent (cleaned up by #4792's harness) and fall back to the persistent state. The CHANGELOG documents this explicitly.

- **CQ-8 — `health_check.py` purpose** (Q4): "When should an operator use `health_check.py` directly?"
  - **Expected**: As an offline diagnostic fallback when the harness is down. The preferred path is `GET /status` (via `squidsquad_cli status`). `health_check.py` is read-only, PID-based, and makes no lifecycle decisions.

- **CQ-9 — Stop-the-team endpoint coverage** (Q5): "Does the harness support stopping a single agent and stopping all agents in one call? What are the endpoints?"
  - **Expected**: Both. `POST /agents/{role}/stop` for single-role; `POST /agents/all/stop` for the whole team. Both are preserved because the web-UI vision requires both per Q5.

- **CQ-10 — Liveness mechanism** (Q6): "How does the harness detect that an agent is alive?"
  - **Expected**: PID-based polling every 5s. The harness reads `.claude-pid` and probes the PID via `tasklist` (Windows) or `os.kill(pid, 0)` (Unix). Heartbeats are not used in #4792; that may come in a later phase tied to #3963.

**Pytest harness**: `tests/test_comprehension_4792.py` — follows the existing pattern (see `tests/test_comprehension_1428.py` if present). Invokes `references/scripts/run_comprehension_test.py tests/comprehension/4792_spec.json` and asserts exit 0.

---

## 9. Downgrade Test (Q13 Downgrade-Safety AC)

- **TC-9.1 — Set intent=STOPPING via post-#4792 code**:
  Start the post-#4792 harness on the test repo. `POST /agents/skill/stop`. Verify `.harness-state.json` shows `intent=stopping`.

- **TC-9.2 — Downgrade**:
  `git checkout <pre-4792-tag>` (or `git revert` the #4792 PR locally). `pip install` any version-pinned deps if needed. Confirm `harness.py` is the pre-cleanup version.

- **TC-9.3 — Restart harness with old code**:
  Boot the pre-#4792 harness. Verify it loads `.harness-state.json` and observes `intent=stopping` for skill.

- **TC-9.4 — Old code does NOT require `.stop` file**:
  Confirm the pre-#4792 `boot_remote._has_stop_sentinel` returns False (no `.stop` file present, because #4792 cleaned it). Confirm the agent's next `cycle_post` still queries `GET /agents/skill` and sees `intent=stopping` from the JSON — completing the graceful stop. The legacy `.stop` parallel path was redundant; the JSON path was always sufficient.

- **TC-9.5 — Documentation check**:
  CHANGELOG entry for #4792 includes a "Downgrade safety" note: "Legacy sentinel files (`.stop`, `.restart`, `.health`) are no longer load-bearing. `.harness-state.json` is the authoritative intent record. Downgrading to a pre-#4792 version is safe — old code reads the same state file." DM owns the CHANGELOG write.

---

## 10. Manual Smoke Tests (Human QA)

These are the eyes-on sanity checks the human runs post-ship before flipping production teams.

- **TC-10.1 — Full operator flow** (covers AC-7, AC-8, AC-13):
  Bring up the full team via `squidsquad_cli start --all`. Confirm all 4 agents enter cycle 1. `squidsquad_cli stop pm`. Watch PM's terminal: cycle_post prints exit 42 (or equivalent log), agent invokes `/quit`, claude session exits, terminal closes. Harness logs `pm intent=stopped`. Restart PM via `squidsquad_cli restart pm`. Verify cycle 1 resumes.

- **TC-10.2 — Force-kill flow** (covers AC-5):
  Stage a stuck agent — open the skill terminal, run a `time.sleep(300)` in a tool call. `squidsquad_cli stop skill`. Watch harness log; ~60s later, force-kill fires; skill terminal closes. Harness logs `force-kill role=skill pid=<N> elapsed=60s`.

- **TC-10.3 — Upgrade flow** (covers AC-10, Q13-A):
  On a fresh clone simulating a pre-#4792 install, manually create `.squidsquad/{pm,qa,dm,skill}/.stop` and a few `.health` and `.restart` files. Boot the post-#4792 harness. Confirm log line `[harness] cleanup: removed 12 legacy sentinel(s)` (or similar count). Confirm all 4 agents spawn normally (no silent refuse-to-boot from leftover `.stop`).

- **TC-10.4 — Crash recovery, manual** (covers AC-9 scenario 1):
  Start team. `squidsquad_cli stop pm` (sets intent=stopping). Immediately `SIGKILL` the harness process. Wait. Restart harness. Confirm: on boot, harness reads `.harness-state.json`, observes pm intent=stopping, and at PM's next cycle boundary the agent self-quits.

---

## 11. Gating Conditions

- **Hard prereqs**: None for #4792 itself. #8692 (singleton enforcement) is a **sibling hard prereq for the Phase 5 event-mode flip, NOT a #4792 prereq.** #4792 ships independently.
- **Coordination with #8697 (fragment updates per Q12)**: Both directions covered by Q12 — whichever ships first, the other migrates the cleaned content forward. The test plan does not gate #4792 on #8697.
- **Plan-checker run**: Required before transitioning `planning → planned` (project gate).
- **Human approval gate**: Required before transitioning `planned → approved` (project gate; Q-locks resolved but human reviews the synthesized TEST-PLAN.md and CONTEXT-4792.md).
- **QA pass**: All §3–§9 tests must pass. §10 manual smoke is a post-ship validation (PM nudges, human runs).
- **Zero-gap rule**: Any TC failure routes the task back to in-progress per project policy. No "minor gaps" shipping.

---

## 12. Post-Ship Validation

- **Soak test (24h)**: After ship, run the full team on /loop mode for 24h. Monitor for regressions:
  - Any unexpected `.stop`/`.restart`/`.health` file creation (filesystem watcher).
  - Any force-kill log lines outside expected scenarios (should be zero in steady-state).
  - All cycle commits succeed; no agent stalls.

- **Context-pressure soak** (closes #7693): Inject context-pressure on PM (force `context-pressure` file to 85%). Confirm:
  1. `cycle_post.py` exits 42.
  2. Agent invokes `/quit`.
  3. claude session exits, `.claude-pid` cleared.
  4. Harness observes dead PID within 5s, sees intent=running, respawns via `boot_remote.boot_agent`.
  5. Agent enters new cycle. Fixes #7693.

- **Phase 5 readiness**: With #4792 + #8692 both shipped, the per-role `event-driven: yes` flip becomes safe. Specifically, the pre-flip checklist at Phase 5 CONTEXT.md §6.4 (lifecycle sole-authority preserved) is satisfiable. This is **not** a #4792 deliverable but is the strategic consequence and should be noted in the PR description.

---

## 13. Open Questions

**None.** All 17 questions in `DECISIONS-4792.md` are closed. No residual concerns from the test-plan drafting pass.

If any reviewer identifies a gap during plan-check, list it as a residual concern with severity (high/medium/low) here and route back to Phase 2 for re-lock — do not silently expand scope.

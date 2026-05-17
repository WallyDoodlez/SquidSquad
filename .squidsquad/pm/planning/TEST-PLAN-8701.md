# TEST-PLAN-8701 — `cycle_pre.py` / `cycle_post.py` Task-Level Refactor

**Issue**: #8701 — Phase 5 event-driven architecture bundle (cycle_pre/cycle_post per-task refactor)
**Bundle**: #8694 (lead) / #8695 / #8697 / #8700 / #8701 / #8704
**Hard prereq**: #8692 (singleton enforcement) — see `CONTEXT.md` §6.1
**Scope source**: `CONTEXT.md` §5.5 (lines 588–625), §2 "Task-cycle replaces time-cycle" (lines 103–106), §11 glossary "Task-cycle" (line 948)
**Touched files**: `references/scripts/cycle_pre.py`, `references/scripts/cycle_post.py`, possibly `references/scripts/cycle.py` (helpers), test additions in `tests/`

## Revision Log

- **2026-05-17** — Revised per deepseek R1 review (1 error + 6 warnings) + 4 PM-locked gap resolutions.
  - **PM Gap 2 (LOCKED) — `cycle_post.py:49` validator mode-gated**: loop mode keeps `REQUIRED_FIELDS = {"role", "cycle_number", "cycle_type"}`. Event mode uses `{"role", "task_id", "cycle_type"}` (or equivalent — exact event-mode field names TBD by implementer; minimum: cycle_number NOT required, task identifier IS required). OQ5 moved to scope expansion / covered by new UT-10.
  - **PM Gap 3 (LOCKED) — `cycle_post.py:587-644` `_advance_event_cursor` REMOVED**: `event_poll.py` is the single owner of cursor state per CONTEXT §2 "per-event atomic advancement." Loop mode has no event-cursor concept. OQ6 moved to scope expansion / covered by new NT-5 (negative grep).
  - F1 (warning, UT-9 "bonus" label): promoted to standard unit test; "bonus" designation removed (AC-5 is mandatory).
  - F2 (warning, no test that `_get_cycle_number` is gated): added explicit mock-call assertion to UT-1.
  - F3 (warning, NT-2 file-absence weak): strengthened to assert `_write_status_bar()` is never called (zero invocations) in addition to file-absence check.
  - F4 (warning, no cursor-behavior test): closed by Gap 3 + new NT-5 (negative grep for `_advance_event_cursor` source).
  - F5 (warning, IT-5 parallel git race): rephrased to sequential execution within the same test.
  - F6 (error/planning gap, validator): closed by Gap 2 + new UT-10.
  - F7 (warning, PV-3 backward compat): added note that tests may require trivial config-mock removal after Phase 6 /loop deletion; core assertions stay intact.

## Scope Expansion (newly locked, per PM gap resolutions)

The original Phase 2 CONTEXT.md left two cycle_post.py items as open questions (the validator's `REQUIRED_FIELDS` and `_advance_event_cursor`). The PM has now locked both:

- **`_validate_output()` (`cycle_post.py:109–133`, REQUIRED_FIELDS at line 49) is mode-gated.** Loop mode keeps existing required fields. Event mode swaps `cycle_number` for a task identifier (exact key TBD by implementer; minimum constraint: `cycle_number` not required, task identifier required, validation rejects clearly when missing).
- **`_advance_event_cursor()` (`cycle_post.py:587–644`) is removed entirely.** `event_poll.py` is the single owner of cursor state per CONTEXT §2; loop mode has no event-cursor concept. Tests assert the function no longer exists in `cycle_post.py` source.

Both items are now in #8701 scope. Tests UT-10 (validator) and NT-5 (cursor removal) cover them.

---

## Section 1 — Acceptance Criteria

Sourced from `CONTEXT.md` §5.5 "Acceptance" (lines 618–624) and "Deliverables" (lines 593–610), plus the issue body.

- **AC-1** (mode dispatch): Both `cycle_pre.py` and `cycle_post.py` read the role's `event-driven: yes/no` from `.squidsquad/config.md` (same mechanism `compose.py` uses — `CONTEXT.md` §2 lines 108–110) and branch behavior. `event-driven: no` → existing time-cycle path. `event-driven: yes` → task-cycle path.
- **AC-2** (loop-mode regression-free): With `event-driven: no`, both scripts produce **byte-identical** output to today's behavior (cycle counter increment via `_get_cycle_number()` at `cycle_pre.py:329–342`, iteration log `iter-N.md` via `_do_iteration_log()` at `cycle_post.py:223–245`, status-bar writes, status transitions, tracker comments, git commit/push).
- **AC-3** (event-mode per-task pre): With `event-driven: yes`, `cycle_pre.py` requires a task id, does git pull, builds forge state **for that one task only**, and writes `cycle-input.json` scoped to that task. No cycle counter increment. No cross-agent health check.
- **AC-4** (event-mode per-task post): With `event-driven: yes`, `cycle_post.py` reads `cycle-output.json`, applies transitions / tracker comments for **this task**, writes a task-log entry keyed by `task_id + timestamp` (e.g., `task-<id>-<ts>.md`), and commits + pushes scoped to this task's outputs.
- **AC-5** (no-op safety): `event-driven: yes` invocation with no task id supplied → clean exit with a clear error (`CONTEXT.md` §5.5 lines 609–610). Exit code non-zero, stderr message identifies the missing input.
- **AC-6** (context-pressure exit code 42): Context-pressure check still runs at the task boundary in event mode. Exceeded → exit 42. Harness respawns per the same mechanism used today (`cycle_post.py:537–573` `_do_stop_after_cycle_check`, harness.py:908+ intent flow).
- **AC-7** (no cross-agent health check in event mode): Event-mode `cycle_pre.py` performs no `health_check.py --json` call, no cross-agent intent polling. Harness owns liveness (`CONTEXT.md` §2 lines 105–106, §5.5 lines 597–598, 623–624).
- **AC-8** (no current-state writes in event mode): Status-line file-based path (`_write_status_bar()` writes to `.squidsquad/<role>/current-state`) is a no-op in event mode. The harness HTTP API surface from #8700 takes over. (`CONTEXT.md` §5.4 lines 549–582, §5.7 lines 662–673.)
- **AC-9** (task-log atomicity): Task-log files are written atomically (`.tmp` then `mv`). A mid-task crash means `cycle_post.py` never ran → no log entry. This is correct semantics per the issue body ("mid-task crash means cycle_post never ran, so no log entry — correct semantics").
- **AC-10** (dual-mode coexistence): Within a single SquidSquad deployment, one role can be event-driven while another is on /loop. Both run successfully against the same `cycle_pre.py` / `cycle_post.py` scripts. No global mode flag.
- **AC-11** (#8694 / #8700 coupling): Scripts co-ship with #8694 (event-mode L1 base instructions invoke the per-task `cycle_pre`/`cycle_post`) and #8700 (status-line refactor removes the file-based current-state dependency for event-mode). Plan-checker + human approval gate — see Section 8.

---

## Section 2 — Test Categories Map

| Category | Section | Approx Count | Covers |
| --- | --- | --- | --- |
| Unit (script-internal logic) | §3 | 10 | AC-1, AC-3, AC-4, AC-5, AC-6, AC-7, AC-9; PM Gap 2 validator |
| Integration (cross-script + git/forge) | §4 | 5 | AC-2, AC-3, AC-4, AC-9, AC-10 |
| Negative (event-mode does NOT do X) | §5 | 5 | AC-2 (regression), AC-7, AC-8; PM Gap 3 cursor removal |
| Migration / backward compat | §6 | 3 | AC-2, AC-10 |
| Manual smoke | §7 | 3 | AC-3, AC-4, AC-6, AC-10 |
| Gating | §8 | — | AC-11 |
| Post-ship validation | §9 | — | AC-9, AC-10 |

---

## Section 3 — Unit Tests

All unit tests live under `tests/` (per `CONTEXT.md` §5.5 lines 612–616). Use `pytest` style. Mock `subprocess.run`, `tracker.py`, `health_check.py`, and `gh` shell-outs to keep tests deterministic. Stub `config.py get event-driven <role>` to flip modes.

### UT-1 — `cycle_pre` event-mode skips cycle-counter increment
- **Pre**: role config `event-driven: yes`. Existing `.squidsquad/<role>/iterations/` contains `iter-5.md` (current `_get_cycle_number()` at `cycle_pre.py:329–342` would return 6). **Spy / mock `_get_cycle_number` so any call is recorded (review F2).**
- **Steps**: invoke `cycle_pre.py <role> --task <id>`.
- **Expected**: `cycle-input.json` written. `_get_cycle_number()` is **never called** (zero invocations recorded — assert the code path is gated, not just that the output is benign). No `cycle_number` field appears in the output JSON (omitted entirely is preferred; null or 0 are acceptable per OQ2 but the spy-based assertion is the load-bearing check). No new `iter-N.md` file is created.
- **Verification**: assert `_get_cycle_number` spy invocation count is `0`; assert `cycle-input.json` does not contain a populated `cycle_number` field; assert `iter-6.md` does NOT exist after invocation.

### UT-2 — `cycle_pre` event-mode skips cross-agent health check
- **Pre**: role config `event-driven: yes`. Mock `_run_script("health_check.py", "--json")` and assert it is NOT called.
- **Steps**: invoke `cycle_pre.py <role> --task <id>`.
- **Expected**: `cycle-input.json` contains **no** `agent_health` field, OR field is an empty dict by design. `health_check.py` subprocess was never invoked.
- **Verification**: subprocess call recorder shows zero invocations of `health_check.py`. Currently the call lives at `cycle_pre.py:651` (PM builder) and `:828` (QA builder) — both must be gated on mode.

### UT-3 — `cycle_pre` event-mode writes `cycle-input.json` keyed by task id
- **Pre**: role config `event-driven: yes`. Task id `42` supplied.
- **Steps**: invoke `cycle_pre.py <role> --task 42`. Forge mocked to return one canonical issue for `#42`.
- **Expected**: `cycle-input.json` contains a top-level `task_id: "42"` (or equivalent — implementation discretion) and the forge state for **only** this task. No `tracker.pending_test_issues` global pull, no `work_queue` global pull.
- **Verification**: JSON content shape match; verify the script did NOT run the multi-role `tracker.py list-issues` loop that loop-mode uses (`cycle_pre.py:594–618` for PM; `:769–811` for QA).

### UT-4 — `cycle_post` event-mode writes task-log keyed by `task_id + timestamp`
- **Pre**: role config `event-driven: yes`. `cycle-output.json` present with `task_id: "42"`, `iteration_summary: "did X"`.
- **Steps**: invoke `cycle_post.py <role>`.
- **Expected**: a task-log file exists under `.squidsquad/<role>/iterations/` (or task-log dir per implementation choice) with name pattern `task-42-<YYYYMMDD-HHMMSS>.md` (or similar — `CONTEXT.md` §5.5 line 605 explicitly defers naming to "implementation discretion"). No `iter-N.md` was written.
- **Verification**: glob for matching filename, assert no `iter-*.md` created in this cycle.

### UT-5 — `cycle_post` event-mode commit is scoped to this task's outputs
- **Pre**: role config `event-driven: yes`. Working tree has: (a) modified file that belongs to this task; (b) a stray modified file in another role's `.squidsquad/<other>/` (must not be included).
- **Steps**: invoke `cycle_post.py <role>`.
- **Expected**: the resulting commit's diff includes (a) but excludes (b). Commit message references the task id, not a cycle number.
- **Verification**: `git show --stat HEAD` after invocation, asserted via test helper. Reuses `_do_commit_push()` at `cycle_post.py:297–412` but with task-scoped staging.

### UT-6 — Context-pressure exit 42 fires in both modes
- **Pre**: `cycle-input.json` has `context_pressure: {exceeded: true, used_pct: 85}`. Harness `intent=running` (mock returns "running").
- **Steps**: invoke `cycle_post.py <role>` once with `event-driven: no`, once with `event-driven: yes`.
- **Expected**: both invocations exit with code 42. Mechanism unchanged from current `_do_stop_after_cycle_check()` at `cycle_post.py:537–573`.
- **Verification**: assert return code 42 in both modes.

### UT-7 — `cycle_pre` loop-mode regression check (pre-refactor parity)
- **Pre**: role config `event-driven: no`. Same fixture used by today's tests for `cycle_pre.py`.
- **Steps**: invoke `cycle_pre.py <role>` (no `--task` flag).
- **Expected**: `cycle-input.json` is byte-identical to the pre-refactor baseline (or differs only in fields that are runtime-determined, e.g., timestamps). Cycle counter increments. Health check runs. Status bar writes.
- **Verification**: golden-file compare against a captured baseline JSON (excluding `timestamp` field).

### UT-8 — `cycle_post` loop-mode regression check
- **Pre**: role config `event-driven: no`. Standard `cycle-output.json` fixture (today's shape).
- **Steps**: invoke `cycle_post.py <role>`.
- **Expected**: identical side effects to today: `iter-N.md` written, status transitions called, tracker comments posted, `git commit/push` invoked, status bar cleared to `idle|`.
- **Verification**: assert all `tracker.py` calls match expected sequence; assert `iter-N.md` exists; assert `current-state` reads `idle|`.

### UT-9 — `event-driven: yes` + missing `--task` arg → clean error (mandatory, review F1)
- **Pre**: role config `event-driven: yes`. No `--task` supplied.
- **Steps**: invoke `cycle_pre.py <role>`.
- **Expected**: exit code non-zero (likely 1 or 2 — distinct from 42), stderr contains "task id required" or equivalent. No `cycle-input.json` written.
- **Verification**: capture stderr, capture return code, assert no file produced. AC-5. *(Promoted from "bonus" — this is the only test covering AC-5, which is a mandatory acceptance criterion.)*

### UT-10 — `_validate_output()` is mode-gated (review F6 + PM Gap 2)
- **Pre**: `_validate_output()` (`cycle_post.py:109–133`) updated to dispatch on the role's `event-driven` flag. Loop mode keeps `REQUIRED_FIELDS = {"role", "cycle_number", "cycle_type"}`. Event mode uses `{"role", "task_id", "cycle_type"}` (or equivalent task-identifier key — exact name TBD by implementer; the test's task-identifier field name is configured to match the implementer's choice).
- **Sub-cases**:
  - **UT-10a (event-mode pass)**: `cycle-output.json` contains `{"role": "skill", "task_id": "100", "cycle_type": "active"}` (NO `cycle_number`). Config: `event-driven: yes`. Invoke `cycle_post.py skill`. Expect validation passes; the script proceeds past the validator (no early exit on field-missing error).
  - **UT-10b (loop-mode reject)**: `cycle-output.json` contains `{"role": "skill", "cycle_type": "active"}` (NO `cycle_number`, NO `task_id`). Config: `event-driven: no`. Invoke. Expect validation fails clearly — stderr names `cycle_number` as the missing field, script exits non-zero before any side effects.
  - **UT-10c (event-mode reject — no task identifier)**: `cycle-output.json` contains `{"role": "skill", "cycle_type": "active"}` (NO task identifier of any kind). Config: `event-driven: yes`. Invoke. Expect validation fails clearly — stderr names the missing task identifier field, script exits non-zero before any side effects.
- **Verification**: capture stderr and return codes for each sub-case; assert per-sub-case expectations above.

---

## Section 4 — Integration Tests

Integration tests exercise the full `cycle_pre → creative work → cycle_post` flow against a sandbox `.squidsquad/` directory and a stubbed `tracker.py` (or a recording fake). Use a temp git repo for git operations.

### IT-1 — Event-mode single-task happy path
- **Pre**: role configured `event-driven: yes`. One open issue `#100` assigned to the role.
- **Steps**: invoke `cycle_pre.py <role> --task 100`. Agent simulator writes `cycle-output.json` with one transition (`approved → in-progress`) and a tracker comment. Invoke `cycle_post.py <role>`.
- **Expected**: task-log entry exists, transition was applied, commit landed on the correct branch, push completed. The `task_id` field in the log is `100`, not a cycle number. Correlate: `task-100-*` log file references `#100` in its body.
- **Verification**: file presence + body assertion + `git log` shows the commit.

### IT-2 — Event-mode second pickup (per-task invocation)
- **Pre**: same role, IT-1 completed. Now `#101` is the next pickup.
- **Steps**: invoke `cycle_pre.py <role> --task 101` (i.e., a **second** per-task invocation, not a time-driven re-fire).
- **Expected**: a fresh `cycle-input.json` scoped to `#101`. No drift in cycle counter, no `iter-N+1.md`. Task-log eventually written for `#101` after `cycle_post.py`.
- **Verification**: post-state directory contains `task-100-*.md` and `task-101-*.md`, no `iter-*.md` newer than IT-1 baseline.

### IT-3 — Event-mode crash atomicity (AC-9)
- **Pre**: same setup as IT-1, picked up `#102`. After `cycle_pre.py` writes `cycle-input.json`, kill the agent process before `cycle_post.py` runs.
- **Steps**: restart the agent.
- **Expected**: no `task-102-*` log file exists (cycle_post never ran). Working-state still reflects the in-progress task — on restart, the agent resumes from working-state per the boot path in #8694 (event-mode L1 base, `CONTEXT.md` §3.1).
- **Verification**: directory contains no `task-102-*`; working-state.md shows `Task: #102, Status: in-progress`.

### IT-4 — Loop-mode regression: full /loop cycle parity
- **Pre**: role configured `event-driven: no`. Baseline artifacts from a known-good loop-mode run captured.
- **Steps**: run `cycle_pre.py <role>` → simulate creative work that matches baseline → `cycle_post.py <role>`.
- **Expected**: produced artifacts (`iter-N.md`, `cycle-input.json` shape, status transitions list, commit message format, status-bar transitions) match baseline byte-for-byte except for timestamp drift.
- **Verification**: directory diff vs baseline, ignoring timestamp lines.

### IT-5 — Mixed-mode coexistence (AC-10, review F5)
- **Pre**: role `skill` is `event-driven: yes`; role `pm` is `event-driven: no`. Same repo, same scripts.
- **Steps**: **sequentially** within the same test, run `cycle_pre.py skill --task 200`, then run `cycle_pre.py pm` (no task). Sequential execution avoids git lock contention and shared `.squidsquad/` write races; the verification only asserts per-role outputs which are identical under sequential vs parallel execution. If true parallel coexistence is desired in the future, the test must add explicit isolation (separate git worktrees or temp repos).
- **Expected**: `skill` follows the task-cycle path, `pm` follows the time-cycle path. Each writes its own `cycle-input.json` correctly. No global state interferes.
- **Verification**: assert `.squidsquad/skill/cycle-input.json` has `task_id: "200"` and no `cycle_number`; assert `.squidsquad/pm/cycle-input.json` has the loop-mode shape with a numeric `cycle_number`.

---

## Section 5 — Negative Tests

Each test asserts that something the loop mode does is **not** done in event mode.

### NT-1 — Event mode: no cycle counter increment anywhere
- **Pre**: `event-driven: yes`. Baseline: `iter-N.md` directory snapshot.
- **Steps**: run a full `cycle_pre.py` + `cycle_post.py` task cycle.
- **Expected**: no file is created in `.squidsquad/<role>/iterations/` matching `iter-*.md`. No counter file on disk is incremented. No `cycle_number` field in any output JSON (or it is null / 0 by design).
- **Verification**: directory diff; grep counter files.

### NT-2 — Event mode: no current-state file write (review F3)
- **Pre**: `event-driven: yes`. Pre-existing `.squidsquad/<role>/current-state` deleted. **Spy / mock `_write_status_bar()` (at `cycle_pre.py:90–99` and `cycle_post.py:92–101`) so every invocation is recorded.**
- **Steps**: run a full task cycle.
- **Expected**: (a) `_write_status_bar()` invocation count across the entire `cycle_pre → cycle_post` run is **zero** — the function is gated, not merely a no-op; (b) `.squidsquad/<role>/current-state` file is NOT recreated. (Both assertions required — file-absence alone is insufficient because an intermediate write could be cleared by a later step and the test would still pass.) AC-8.
- **Verification**: assert spy invocation count == 0; assert file absence after cycle.

### NT-3 — Event mode: no cross-agent health check
- **Pre**: `event-driven: yes`. Patch `subprocess.run` to record every command invoked.
- **Steps**: run `cycle_pre.py <role> --task <id>`.
- **Expected**: no recorded subprocess invocation has `health_check.py` in its argv. No HTTP call to any other agent's harness endpoint. AC-7.
- **Verification**: recorded-call list assertion.

### NT-4 — Event mode: task-log NOT keyed by cycle number
- **Pre**: `event-driven: yes`. Run a task cycle for `#300`.
- **Steps**: invoke full pipeline.
- **Expected**: the produced log file matches `task-300-*.md` (or chosen task-keyed convention). No file matches `iter-*.md` for this cycle. AC-4.
- **Verification**: glob assertions.

### NT-5 — `_advance_event_cursor` is removed from `cycle_post.py` (PM Gap 3, review F4)
- **Pre**: `cycle_post.py` updated to remove the `_advance_event_cursor` function (lines 587–644 in pre-change code). `event_poll.py` is the single owner of cursor advancement per CONTEXT §2 "Cursor advancement = per-event, atomic."
- **Steps**: `git grep -n '_advance_event_cursor' references/scripts/cycle_post.py` (or equivalent Grep of the source).
- **Expected**: zero matches. The function definition AND any call sites must be gone from `cycle_post.py`. (Calls in `event_poll.py` or other event-stream readers remain valid; this test asserts only that `cycle_post.py` no longer participates in cursor advancement.)
- **Verification**: assert grep output is empty. Loop mode has no event-cursor concept; event mode delegates cursor advancement entirely to `event_poll.py`.

---

## Section 6 — Migration / Backward Compat Tests

### MT-1 — Existing `iter-N.md` files remain readable
- **Pre**: A role that ran loop-mode for 50 cycles has `iter-1.md` through `iter-50.md`. Role flips to `event-driven: yes`.
- **Steps**: any tool that reads iteration logs (e.g., status-bar history, scan history, audit scripts) is invoked.
- **Expected**: existing `iter-N.md` files are still parseable. No migration script required.
- **Verification**: read each file, assert frontmatter / body parses without error.

### MT-2 — Loop → event flip requires no data migration
- **Pre**: role on loop mode, mid-cycle. Operator flips `event-driven: yes` in `config.md`.
- **Steps**: on next agent boot (event-mode L1 base, owned by #8694), the agent reads working-state and resumes.
- **Expected**: no migration script is invoked. Old `iter-N.md` files stay where they are. New cycles produce `task-*-*.md` logs. Both file types coexist in the same directory.
- **Verification**: directory inspection shows both filename patterns; agent boots cleanly.

### MT-3 — Cross-mode history queryability
- **Pre**: role has `iter-1.md` through `iter-50.md` (loop era) plus `task-101-…md` through `task-150-…md` (event era).
- **Steps**: a hypothetical history-query script lists "work done in last 7 days" and "all work referencing #101".
- **Expected**: both file types are surfaced. The task id `#101` is found in `task-101-…md`. `#42` (loop era, mentioned inside `iter-7.md` body) is found via grep, even though loop-era files weren't keyed by task id in their filename.
- **Verification**: documented grep / index call returns expected results from both formats.

---

## Section 7 — Manual Smoke Tests

These run against a live SquidSquad deployment after merge but before the per-role event-mode flip.

### ST-1 — Bring up a role in events mode end-to-end
- Flip a non-critical role (suggest `qa` after pre-flip checklist §6.3 passes) to `event-driven: yes`.
- Pick up one open task.
- Observe: harness event → `cycle_pre.py <role> --task <id>` fires → agent works → `cycle_post.py <role>` fires.
- Inspect: `.squidsquad/<role>/iterations/task-<id>-*.md` exists, contents reflect the work done, transitions show in tracker.
- Confirms AC-3, AC-4.

### ST-2 — Force context-pressure event
- With role in events mode, artificially write `>= threshold` to `.squidsquad/<role>/context-pressure`.
- Run one task cycle.
- Expect: `cycle_post.py` exits 42; harness logs respawn; agent comes back up via #8694 boot path.
- Confirms AC-6.

### ST-3 — Switch role back to loop mode
- Flip role's `event-driven: no` in `config.md`.
- Next cycle: confirm `cycle_pre.py` takes the time-cycle path (cycle counter visible in `cycle-input.json`, `iter-N.md` written by `cycle_post.py`).
- Confirms AC-1 + AC-10 (dual-mode dispatch works both directions).

---

## Section 8 — Gating Conditions

Per `CONTEXT.md` §5.5, §6.1, §6.3:

- **Hard prereq**: **#8692** (singleton enforcement) **shipped**. Without it, two agents of the same role can race per-task `cycle_pre`/`cycle_post` and corrupt cursors / dupe forge actions (`CONTEXT.md` §6.1 lines 682–692).
- **Co-ships with #8694**: event-mode L1 base instructions invoke per-task `cycle_pre`/`cycle_post`. The scripts can ship before #8694 but cannot be **exercised** in event mode until #8694 lands.
- **Co-ships with #8700**: status-line refactor removes the file-based current-state dependency for event-mode. AC-8 depends on this — if #8700 has not shipped, event-mode `cycle_pre`/`cycle_post` should fall back to writing `current-state` (open question — see §10).
- **Per-role pre-flip checklist** (`CONTEXT.md` §6.3 lines 702–716): #8692 + #8697 + L4 audit + #8694 fragments + #8695 flag + clean `compose.py deploy <role>` output all required **before** flipping any role to `event-driven: yes`.
- **Standard PM gate**: plan-checker pass + human approval before transition to `Approved`.

---

## Section 9 — Post-Ship Validation

### PV-1 — Event-mode soak
- Run one event-mode role through N completed tasks (suggest N ≥ 20).
- Verify: exactly N `task-*-*.md` log files. No `iter-N.md` files created during the soak window. No orphan `current-state` files. No `agent_health` blobs in `cycle-input.json`.
- Confirms AC-3, AC-4, AC-7, AC-8 at scale.

### PV-2 — Cross-role consistency
- Verify the harness `GET /agents` (or `/agents/{role}`) endpoint reports task counts that match the on-disk task-log file count for event-mode roles, and the on-disk `iter-N.md` count for loop-mode roles.
- Confirms AC-10 (dual-mode counters don't conflict).

### PV-3 — Phase 6 cleanup readiness
- When #8698 ships (`CONTEXT.md` §7.1 lines 728–739), the /loop branches in both scripts can be deleted. The unit tests in this plan that target event mode (UT-1 through UT-6, UT-9, UT-10a/c; IT-1, IT-2, IT-3, IT-5; NT-1 through NT-5) **must continue to pass** after that deletion. The loop-mode regression tests (UT-7, UT-8, UT-10b, IT-4, MT-1, MT-2, MT-3 loop arm) are expected to be removed alongside the /loop code by #8698.
- **Note (review F7)**: tests may require trivial config-mock removal after Phase 6 /loop deletion — the post-Phase-6 scripts become single-mode (events-only) and may stop reading the `event-driven` flag entirely; the `event-driven: yes` mock then becomes a no-op. The **core assertions** (no cycle counter, task-keyed log, validator accepts event-mode shape, `_advance_event_cursor` absent, no `_write_status_bar` calls, etc.) **remain intact and must continue to pass**.
- Confirms #8701's events-mode behavior survives the cleanup gate.

---

## Section 10 — Open Questions

These gaps were not explicitly closed by `CONTEXT.md` §5.5 and may need a Phase-2B re-discussion or a discretionary call from the dev agent. Flag them now so downstream planners don't build tests on assumptions.

1. **Task-log filename convention**: `CONTEXT.md` §5.5 line 605 explicitly says "task-<id>-<ts>.md or similar — implementation discretion". This plan uses `task-<id>-<YYYYMMDD-HHMMSS>.md` as a working assumption; the dev agent may pick another shape. UT-4 / IT-1 assertions need updating once chosen.
2. **`cycle_number` field semantics in event-mode `cycle-input.json`**: explicit absence vs `null` vs `0` is not specified. UT-1 / NT-1 assertions assume any of those is acceptable; pick one before authoring.
3. **Task id transport**: how does the per-task `cycle_pre.py` invocation receive the task id? CLI flag (`--task <id>`), env var (`SQUIDSQUAD_TASK_ID`), or read from a sentinel file? `CONTEXT.md` §5.5 line 595 says "Inputs: task id" but doesn't specify mechanism. **Recommended**: CLI flag for testability. Lock before unit-test authoring.
4. **Status-line fallback during the gap between #8701 and #8700**: if #8701 ships first, does event-mode `cycle_pre`/`cycle_post` still write `current-state` for the file-based status line, or skip it (relying on #8700's HTTP path that may not exist yet)? AC-8 is binary today; may need a transition mode. **Recommended**: ship #8700 first or in the same train; otherwise add a config flag `status-line: file | http` that the scripts honor.
5. **~~`cycle-output.json` shape change~~ — CLOSED (PM Gap 2)**: `_validate_output()` is mode-gated. Loop mode keeps `REQUIRED_FIELDS = {"role", "cycle_number", "cycle_type"}`. Event mode uses `{"role", "task_id", "cycle_type"}` (or equivalent task-identifier — exact event-mode field names TBD by implementer; minimum: `cycle_number` NOT required, task identifier IS required). Covered by **UT-10** (§3). Scope expansion noted at top of this plan.
6. **~~Event bus cursor advancement~~ — CLOSED (PM Gap 3)**: `_advance_event_cursor` is REMOVED from `cycle_post.py`. `event_poll.py` is the single owner of cursor state per CONTEXT §2. Covered by **NT-5** negative grep (§5). Scope expansion noted at top of this plan.
7. **DM end-of-task wait** (`CONTEXT.md` §2 lines 89–94, §9 diagram line 794–795): DM's "task" spans a full PR-merge wait. Does the per-task `cycle_pre`/`cycle_post` invocation block for the wait, or is the wait inside the creative phase between the two scripts? Likely the latter, but #8701 implementation may need to handle longer-running cycles. Flag for dev agent.

---

## Section 11 — Comprehension Questions (CQ specs)

Required by project standard: any task touching LLM-consumed instructions needs CQs (`feedback_comprehension_tests_required.md`). #8701 touches scripts only — no agent CLAUDE.md / fragment changes. **No CQs required for #8701 itself.** If the implementation pulls in a fragment edit (e.g., updating the `event-mode L1 base` to reference the new `--task` flag), add CQs at that boundary, owned by #8694.

---

## Section 12 — Citations

- `CONTEXT.md` §2 (Architecture Decisions) lines 48–149 — task-cycle decision (lines 103–106), mode separation (lines 111–118), event-mode L1 base (lines 119–125).
- `CONTEXT.md` §5.5 (#8701 spec) lines 588–625 — scope, deliverables, files touched, acceptance.
- `CONTEXT.md` §6.1 lines 677–692 — #8692 hard prerequisite.
- `CONTEXT.md` §6.3 lines 702–716 — pre-flip checklist.
- `CONTEXT.md` §9 lines 764–823 — sequencing diagram.
- `CONTEXT.md` §11 lines 885–971 — glossary (Task-cycle line 948, Mode separation lines 953–958).
- `references/scripts/cycle_pre.py` lines 90–99 (`_write_status_bar`), 117–139 (`_do_pull`), 252–326 (`_read_working_state`), 329–342 (`_get_cycle_number`), 580–751 (`_build_pm_input` — esp. `health_check.py` at 651), 759–864 (`_build_qa_input` — esp. health at 828), 973–1071 (`main`).
- `references/scripts/cycle_post.py` lines 109–133 (`_validate_output`, esp. `REQUIRED_FIELDS` at 49), 163–199 (`_do_status_transitions`), 223–245 (`_do_iteration_log`), 297–412 (`_do_commit_push`), 484–534 (harness intent discovery), 537–573 (`_do_stop_after_cycle_check` — exit 42), 587–644 (`_advance_event_cursor`), 652–741 (`main`).
- `references/scripts/harness.py` lines 11, 331, 908–928 — intent state machine and respawn flow.
- Issue #8701 body (per `gh issue view 8701 --comments`).

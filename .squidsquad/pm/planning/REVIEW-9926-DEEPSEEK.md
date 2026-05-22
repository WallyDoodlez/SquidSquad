Now I have sufficient context to produce findings. Let me compile them.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/SPEC-9926.md`
- **Line**: 32
- **Severity**: error
- **Issue**: AC2 ("Existing 7 unit tests in `tests/test_orphan_cleanup_9688.py` still pass") is **self-contradictory with Fix 1**. The whole point of loosening D3 to per-role skip is that a stale `.claude-pid` on one role no longer aborts the entire sweep. But the existing D7 test #6 (`test_d7_missing_claude_pid_skips_entire_sweep` at test file line 220–225) explicitly asserts `result["skipped_run"] is True` when one role's `.claude-pid` is missing. If Fix 1 is implemented correctly, that assertion MUST fail — the sweep proceeds (partial skip), the orphan at PID 8008 gets killed, and `_kill` is called. AC2 and Fix 1 cannot both be satisfied.
- **Evidence**: `tests/test_orphan_cleanup_9688.py` line 221: `assert result["skipped_run"] is True, "missing .claude-pid for any role must abort the ENTIRE sweep (D3)"`. The assertion message literally encodes the all-or-nothing D3 behavior that Fix 1 aims to change. Additionally, `test_stale_pid_with_dead_cmdexe_also_skips_sweep` (line 259) and `test_no_roles_discoverable_skips_sweep` (line 241) both assert `skipped_run is True` and would also break.
- **Suggested fix**: Rewrite AC2 to say "Existing tests are updated to reflect the new per-role-skip semantics; no regression in protection logic." Or: if Fix 2 (periodic reap) is chosen instead, AC1/AC2 can remain as-is — but the spec must lock that decision rather than leaving it to skill.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/SPEC-9926.md`
- **Line**: 27 ("Skill's call on which path.")
- **Severity**: error
- **Issue**: The spec delegates an architectural decision ("which path") to the implementer. Per PM CLAUDE.md Phase 2 (`references/sub-skills/roles/pm/task-intake.md` → `.squidsquad/pm/CLAUDE.md` lines 1401–1410), the CONTEXT artifact must contain **locked decisions** that skill implements against. Leaving the choice between two materially different fixes (per-role skip vs. periodic timer — different files touched, different race profiles, different test strategies) to "skill's call" violates the locked-decision contract. Every other CONTEXT file in the repo (CONTEXT-9688.md, CONTEXT-9725.md, CONTEXT-9873-A.md, etc.) locks decisions explicitly in a `## Locked Decisions` section.
- **Evidence**: CONTEXT-9688.md §1 lists 8 locked decisions (D1–D8) with explicit "Locked:" verdicts. SPEC-9926.md has no comparable section and says "Either alone closes the gap. Both together is overkill but cheap. Skill's call on which path." This is not a decision — it's an abdication of PM responsibility.
- **Suggested fix**: Add a `## Locked Decisions` section that picks exactly one path (or explicitly locks "both" with rationale). Update AC3 to be unambiguous and single-valued.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/SPEC-9926.md`
- **Line**: 1 (entire file)
- **Severity**: warning
- **Issue**: The file lacks the **AUTHORITATIVE SCOPE banner** required by PM CLAUDE.md lines 1381–1387. The file is also named `SPEC-9926.md` rather than following the established `CONTEXT-<NUMBER>.md` convention, which is what the AUTHORITATIVE SCOPE banner pattern points to. Every other planning artifact that locks decisions uses the CONTEXT- prefix (CONTEXT-9688.md, CONTEXT-9725.md, CONTEXT-9873-A.md, etc.) and carries the banner at line 9.
- **Evidence**: Compare SPEC-9926.md line 1 (`**Reported By**: pm-lead`) with CONTEXT-9688.md line 9 (`> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9688 + this CONTEXT-9688.md combined are the contract for skill at pickup.`). The PM CLAUDE.md at line 1384 gives the exact required format: `> **AUTHORITATIVE SCOPE: `.squidsquad/pm/planning/CONTEXT-<NUMBER>.md`...**`. SPEC-9926.md has neither the banner nor the CONTEXT- naming convention.
- **Suggested fix**: Either rename to `CONTEXT-9926.md` and add the AUTHORITATIVE SCOPE banner at the top, or keep the SPEC name but still add a banner pointing at itself. The key process requirement is that the issue body and planning artifact are cross-referenced; the banner is the mechanism.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/SPEC-9926.md`
- **Line**: 27 ("Both together is overkill but cheap.")
- **Severity**: warning
- **Issue**: Implementing both fixes together introduces a subtle race that neither fix alone has. If the harness periodic timer (Fix 2) fires `orphan_cleanup.sweep()` concurrently with `boot_agent()`'s own inline `orphan_cleanup.sweep()` call (at `boot_remote.py` lines 469–475), two sweeps race on the same process table. While `taskkill` is idempotent, the sweeps' `_list_claude_processes()` + `_resolve_protected_pids()` + classify + kill are not atomic. During harness auto-reboot, the inline sweep in `boot_agent` runs BEFORE the new thin_launcher spawns, but the periodic sweep could fire at any point in that window — including between the inline sweep and the spawn. The periodic sweep would see the same stale `.claude-pid` and re-sweep, doubling the PowerShell process-listing cost and creating a log with interleaved entries from two concurrent invocations.
- **Evidence**: `harness.py` line 388–394 shows the health poller thread running on a 5-second loop. `boot_remote.py` lines 463–475 show `orphan_cleanup.sweep()` called inline during `boot_agent()`. A periodic orphan timer on a different cadence (5 min) creates an unsynchronized second caller. The spec doesn't address whether these two callers need mutual exclusion.
- **Suggested fix**: If "both" is chosen, the spec should address concurrency: either (a) the periodic timer acquires the same lock as `boot_agent`, (b) the periodic timer skips if any boot is in progress (check `.booting` sentinel), or (c) the sweeps are documented as safe to overlap because idempotency + PID non-reuse makes it harmless. Without this, the implementer has to guess.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/SPEC-9926.md`
- **Line**: 23–25 (Fix 1 description)
- **Severity**: warning
- **Issue**: Fix 1 says "Sweep the healthy roles; leave the role whose `.claude-pid` is stale alone." But it doesn't specify the edge case where **zero** roles are healthy — e.g., `.local-config` is unreadable and `_role_pid_files()` returns `{}`, or all roles have dead cmd.exe. The current behavior (skip entire sweep) is encoded in `test_no_roles_discoverable_skips_sweep` (test line 228–241). Under per-role skip, if zero roles resolve, the protected set would be empty and the sweep would proceed — potentially killing every npm-install `claude.exe` with a dead parent, including ones that might be agents whose roles simply aren't in `.local-config`. This is a semantic change from "rather miss orphans than kill the wrong process" (D3's original rationale, CONTEXT-9688.md line 39).
- **Evidence**: `orphan_cleanup.py` lines 200–208: when `role_pid_files` is empty, `_resolve_protected_pids` returns `(set(), [{"role": "<any>", "reason": "no roles discoverable...", "decision": "skipped"}])`. The current `sweep()` at line 350 checks `if skipped_roles:` and aborts. Under per-role skip, the sweep would continue with `protected = set()`. All npm-install claude.exe processes with dead parents would be classified as orphans and killed — no agent is protected.
- **Suggested fix**: Add to Fix 1's spec: "If zero roles resolve to a healthy protected PID, abort the sweep entirely (preserve the existing safety net for the no-roles-discoverable case)."

---

### Finding 6

- **File**: `.squidsquad/pm/planning/SPEC-9926.md`
- **Line**: 33
- **Severity**: warning
- **Issue**: AC3 is bifurcated: "New unit test covers the partial-skip path (or, if option 2 chosen, the periodic-reap path is exercised in a harness integration test)." The two alternatives have vastly different testability profiles. A unit test for partial-skip is deterministic and cheap (mock-based, like existing D7 tests). A "harness integration test" for the periodic reap requires a running harness, real timers, and real process tables — it is non-deterministic, slow, and fragile. If the spec doesn't lock which path is chosen, QA cannot write a single TEST-PLAN against AC3; they must either write two plans or wait for skill's implementation choice.
- **Evidence**: AC3 says "or, if option 2 chosen..." — deferring the test strategy to an implementation decision that hasn't been made yet. PM CLAUDE.md Phase 3 AC rules (line 1454, criterion 4): "Can QA execute a single command per AC and get a deterministic PASS/FAIL from the AC alone, without reading the diff?" A bifurcated AC fails this test.
- **Suggested fix**: After locking Fix 1 or Fix 2 (see Finding 2), rewrite AC3 to reference only the chosen path's test strategy.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/SPEC-9926.md`
- **Line**: 32
- **Severity**: warning
- **Issue**: AC2 says "Existing 7 unit tests" but the test file `tests/test_orphan_cleanup_9688.py` contains **16** test functions (verified by `grep`). The "7" references the 7 D7-mandated scenarios from CONTEXT-9688.md D7, but the file also includes tests for: no-roles-discoverable, stale-pid-with-dead-cmd.exe, non-npm path filter, POSIX no-op, JSONL log shape, CSV parser edges (3 tests), and own-PID defense. AC2 is ambiguous about whether these non-D7 tests must also pass, and they are equally important regression coverage.
- **Evidence**: `tests/test_orphan_cleanup_9688.py` contains 16 `def test_*` functions. CONTEXT-9688.md D7 (lines 75–82) lists 7 mandatory scenarios. The file's docstring at line 2–13 says "Additional tests cover the npm-install-path filter..., the CSV parser edge cases, the POSIX no-op, and the JSONL diagnostics log shape (D4)." AC2 says "Existing 7 unit tests" — leaving the other 9 in an ambiguous state.
- **Suggested fix**: Rewrite AC2 to "All existing unit tests in `tests/test_orphan_cleanup_9688.py` either pass as-is or are updated to reflect the new D3 semantics with no loss of coverage."
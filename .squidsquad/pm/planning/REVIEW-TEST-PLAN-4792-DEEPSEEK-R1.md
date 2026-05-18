Now I have all the evidence needed. Here is my systematic review.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 112
- **Severity**: error
- **Issue**: TC-3.2.2 references a non-existent acceptance criterion `AC-16`. The test plan defines only AC-1 through AC-15 (lines 27–45). There is no AC-16 anywhere in the document.
- **Evidence**: Line 112 reads: `**TC-3.2.2 — ... removed** (AC-1, AC-4, AC-16)`. Grepping for `AC-16` returns only this one hit. The AC list in §1 defines exactly 15 ACs (AC-1 through AC-15). The referenced functions (`_has_stop_sentinel`, `_read_health_file`, `_read_pid_file`, `_clean_stale_restart`) are already covered by AC-1 (stop removal) and Q16 (immediate deletion of stale-file parsers). The phantom AC-16 likely should be Q16.
- **Suggested fix**: Replace `AC-16` with `Q16` or remove it entirely — the AC-1 and AC-4 labels already cover the relevant criteria.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 43, 353
- **Severity**: error
- **Issue**: AC-13 and TC-7.2 assert that `cycle-input.json` schema is unchanged ("no fields added or removed"), but Q8 (per CONTEXT-4792.md §5.5, line 562 and DECISIONS-4792.md Q8 lock) **adds a new `harness_status: "reachable" | "unreachable"` field** to `cycle-input.json`. This is a direct contradiction — if the field is added, the schema has changed, TC-7.2 would fail, and AC-13 is violated by design.
- **Evidence**: 
  - Line 43 (AC-13): "cycle-input.json and cycle-output.json schemas unchanged."
  - Line 353 (TC-7.2 assertion): "Schema unchanged (no fields added or removed)."
  - CONTEXT-4792.md line 562: "**Add** `harness_status: 'reachable' | 'unreachable'` informational field to `cycle-input.json` (Q8)."
  - DECISIONS-4792.md Q8 lock: "Add `harness_status: 'reachable' | 'unreachable'` informational field to `cycle-input.json`"
- **Suggested fix**: Either (a) remove the `harness_status` field addition from Q8 scope and defer it, or (b) update AC-13 and TC-7.2 to explicitly allow the `harness_status` field as an expected schema delta, updating the assertion to "schema unchanged except for the addition of the informational `harness_status` field per Q8."

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 44, 332–333
- **Severity**: warning
- **Issue**: AC-14 states that ALL surviving sentinel writers (including `.harness-state.json` and `.harness-port`) write to the agent's clone path, but TC-6.10 correctly carves out an exception: `.harness-state.json` and `.event-state.json` are harness-owned and live in the **primary repo** path, not the clone path. AC-14's blanket claim is false for harness-owned state files.
- **Evidence**:
  - AC-14 line 44: "Every surviving sentinel writer (`.claude-pid`, `.booting`, `.harness-state.json`, `.harness-port`, `.event-state.json`) writes to the agent's clone path resolved via `boot_remote._get_clone_path(role)`, not the primary repo path."
  - TC-6.10 line 332–333: "(or for `.harness-state.json` and `.event-state.json` which are harness-owned and live in the primary repo per RESEARCH §2.1, the path starts with `<primary>/.squidsquad/`)"
  - CONTEXT-4792.md §4: `.harness-state.json` is "harness-owned state, not sentinels" and lives in primary repo.
- **Suggested fix**: Rewrite AC-14 to distinguish per-role writers (`.claude-pid`, `.booting`) that must use clone path from harness-owned writers (`.harness-state.json`, `.event-state.json`) that use the primary repo path. The TC-6.10 text is correct; AC-14 should match it.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 475–480 (and absence in §4)
- **Severity**: warning
- **Issue**: No pre-ship integration test demonstrates full #7693 closure. The #7693 scenario (context-pressure trigger → `cycle_post` exit 42 → agent invokes `/quit` → claude session terminates → harness observes dead PID with `intent=running` → harness **respawns** the agent) is only covered in post-ship validation §12 ("Context-pressure soak"). The gating conditions at §11 require "All §3–§9 tests must pass" — but the #7693 closure path is not in those sections.
- **Evidence**:
  - Line 475: "**Context-pressure soak** (closes #7693)" is under §12 "Post-Ship Validation," not under §3–§9 gating tests.
  - CONTEXT-4792.md §8.1 says: "Test plan TC: trigger context pressure, verify claude exits within 60s (happy path < 5s via `/quit`; degraded path < 60s via force-kill). Verify harness respawns post-exit." — but this TC does not exist in the test plan.
  - §4.1 tests STOP path (intent=STOPPING → exit 42 → /quit), but does not test the respawn behavior where intent remains RUNNING.
  - TC-7.3 tests exit code values but not the full respawn chain.
- **Suggested fix**: Add an integration test in §4 that: (1) triggers context pressure on a running agent, (2) verifies `cycle_post` exits 42, (3) verifies the agent self-quits within 5s, (4) verifies harness observes dead PID with `intent=running`, (5) verifies harness respawns the agent via `boot_remote.boot_agent`. This directly validates #7693 closure before ship.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 32, 58, 389–390
- **Severity**: warning
- **Issue**: AC-6 is measured solely by a comprehension test (CQ-2), which verifies the LLM *understands* the self-quit instruction, not that the system *behaves* correctly. Comprehension tests catch instruction ambiguity but do not catch failures where the agent reads the instruction and still doesn't execute `/quit` (e.g., tool-call wedging, malformed bash output parsing). AC-6 needs a behavioral verification component.
- **Evidence**:
  - Line 32 (AC-6): "Verified by comprehension test §8 CQ-2."
  - Line 58 (category map): "AC-6 | comprehension (CQ-2) + regression (composed CLAUDE.md content check)"
  - The content check verifies the instruction *exists* in CLAUDE.md; the CQ verifies the instruction is *comprehensible*. Neither verifies the agent *actually invokes `/quit`*.
  - §4.1 and §10.1 do test graceful stop end-to-end, but they are not labeled as covering AC-6.
- **Suggested fix**: Either (a) label §4.1 and §10.1 as also covering AC-6 (they demonstrate agent termination after stop command, which exercises the `/quit` path), or (b) add an explicit assertion to §4.1 that the agent's terminal output contains evidence of `/quit` invocation before session exit.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 323–324
- **Severity**: warning
- **Issue**: TC-6.8 weakens the AC-11 byte-identical guarantee by allowing a non-byte-identical diff to pass if "annotated as 'explicitly verified byte-identical' in the #4792 PR description." This escape hatch undermines the regression guarantee — a future change could alter the byte sequence, add a PR annotation claiming it's verified identical, and bypass the test. The test should assert byte-identical output unconditionally.
- **Evidence**:
  - Line 323–324: "Either hashes equal, OR the diff is annotated as 'explicitly verified byte-identical' in the #4792 PR description and the actual byte sequence of `_check_singleton`, `_write_pid`, `_clear_pid` is unchanged."
  - AC-11: "produce byte-identical output and exit codes before/after #4792."
  - Q14 lock (DECISIONS): "Byte-identical regression AC: `thin_launcher.py:66-83` `_check_singleton` behavior is identical before and after #4792."
  - The "OR" clause means a failing hash comparison can be overridden by a human annotation, converting a testable assertion into a manual gate.
- **Suggested fix**: Remove the OR clause. The line-renumber-only case is already covered by computing sha256 of the function bodies (not line ranges). If line renumbering is expected, clarify that the sha256 should be computed on function-body byte ranges extracted by AST, not by fixed line numbers. Keep the assertion as: "hashes MUST be equal."

---

### Finding 7

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 150
- **Severity**: warning
- **Issue**: TC-3.4.3 references an undefined artifact `current-state` as a file/filesystem read to allow. The term `current-state` is not defined in the test plan, CONTEXT, or DECISIONS. This makes the test unreproducible — the implementer cannot know what to allow vs. what to patch out.
- **Evidence**:
  - Line 150: "Patch out all filesystem reads except `.claude-pid` and `current-state` (status display)."
  - `current-state` does not appear in CONTEXT-4792.md, DECISIONS-4792.md, or anywhere else in TEST-PLAN-4792.md.
  - The parenthetical "(status display)" suggests it refers to a status-display mechanism, but `health_check.py` per CONTEXT §5.4 reads `.claude-pid` and process tables — there is no `current-state` file.
- **Suggested fix**: Either (a) replace `current-state` with the actual file path or mechanism name (e.g., "process table reads via `/proc` or `tasklist`"), or (b) remove the `current-state` exception and clarify that only `.claude-pid` reads are permitted.

---

### Finding 8

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 299–300 (CONTEXT), vs. TC-3.1.3 line 89–90
- **Severity**: warning
- **Issue**: CONTEXT-4792.md §3.4 line 299–300 claims the Q7 force-kill safety net also fires for RESTARTING: "if neither path fires within 60s, harness force-kills then respawns." But DECISIONS Q7 locks force-kill to STOPPING only, and CONTEXT §5.1 implementation code also only checks `intent == STOPPING`. TC-3.1.3 correctly asserts force-kill does NOT fire for RESTARTING. The test plan silently corrects the CONTEXT inconsistency without flagging it, which could cause the implementer to follow the wrong §3.4 instruction and implement force-kill for RESTARTING, causing TC-3.1.3 to fail.
- **Evidence**:
  - DECISIONS-4792.md Q7: "if intent=STOPPING AND `.claude-pid` alive AND >60s since intent set, harness force-kills"
  - CONTEXT-4792.md §3.4 line 299–300: "[Force-kill safety net per Q7]: → if neither path fires within 60s, harness force-kills then respawns"
  - CONTEXT-4792.md §5.1 code: `if state.intent == STOPPING`
  - TEST-PLAN line 89–90 (TC-3.1.3): correctly asserts `_kill_process` not called for RESTARTING.
- **Suggested fix**: Add a note in the test plan explicitly calling out the CONTEXT §3.4 inconsistency and stating that TC-3.1.3 enforces the Q7 lock (STOPPING only). The CONTEXT document should be corrected separately to remove the force-kill reference from the RESTART flow.

---

### Finding 9

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 363–365
- **Severity**: warning
- **Issue**: TC-7.4 specifies an end-state comparison that is too vague to implement. "working-state.md content, last commit, tracker.py transitions" — no specific file paths, no diff methodology, no handling of non-deterministic artifacts (timestamps, commit hashes, cycle counters). The test cannot be automated as written.
- **Evidence**:
  - Line 364–365: "End state (working-state.md content, last commit, tracker.py transitions) identical to a pre-#4792 graceful stop, **except** for the mechanism"
  - No file paths specified for "last commit" or "tracker.py transitions."
  - No guidance on what "identical" means for a git commit (which has a hash dependent on timestamps and parent SHAs).
- **Suggested fix**: Specify exact files to diff (e.g., `<clone>/.squidsquad/<role>/working-state.md`, `<clone>/.squidsquad/<role>/event-state.json`), specify which fields may differ (timestamps, commit SHAs), and require byte-level comparison for the non-excluded fields.

---

### Finding 10

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 428–430
- **Severity**: warning
- **Issue**: TC-9.2 references `git checkout <pre-4792-tag>` which assumes a git tag exists for the pre-#4792 state. If no tag exists at test time (e.g., #4792 is being merged into an integration branch without tags), the test is not executable. The downgrade test should specify a deterministic way to identify the pre-#4792 commit.
- **Evidence**:
  - Line 428: "`git checkout <pre-4792-tag>` (or `git revert` the #4792 PR locally)"
  - The `git revert` alternative is also problematic — it assumes #4792 is a single squashed commit, which may not be true if multiple PRs are involved.
- **Suggested fix**: Specify that the test uses `git merge-base` with the #4792 branch and main, or pin a specific commit hash from before the #4792 branch point. Alternatively, acknowledge this as a manual-only test that requires the operator to identify the correct ancestor commit.

---

### Finding 11

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 188–199
- **Severity**: warning
- **Issue**: §4.1 asserts "No force-kill log line emitted (graceful path used)" but the test does not bound `cycle_remaining` to ensure the agent reaches `cycle_post` before the force-kill fires at 60s. If `cycle_remaining > 30s`, the agent may not reach its next cycle boundary before 60s elapses from `intent_set_at`, causing the force-kill to fire and the assertion to fail even though the system is working correctly (per AC-7 which allows `cycle_remaining + 60s`).
- **Evidence**:
  - Line 191: "Wait up to `(cycle_remaining + 30s)`"
  - Line 197: "No force-kill log line emitted (graceful path used)."
  - The force-kill timer starts at intent_set_at. If cycle_remaining is, say, 120s, the force-kill fires at +60s while the test is still waiting (up to 150s). The assertion would fail despite the system meeting AC-7.
- **Suggested fix**: Either (a) bound the test to use a short-cycle agent (cycle_remaining < 30s), or (b) change the assertion to "No force-kill log line emitted within the first 60s after intent_set_at" (since that's the grace period before force-kill can fire), or (c) change the assertion to verify termination within budget regardless of which path was used.

---

### Finding 12

- **File**: `.squidsquad/pm/planning/TEST-PLAN-4792.md`
- **Line**: 203
- **Severity**: warning
- **Issue**: §4.2 integration test step 2 says "Replace agent's claude session with a stub that blocks indefinitely (does not honor `/quit`)" — the stubbing mechanism is unspecified, making the test unreproducible. There is no existing test fixture pattern described for replacing the claude session.
- **Evidence**:
  - Line 203: "Replace agent's claude session with a stub that blocks indefinitely"
  - No reference to an existing mock/fixture pattern in the test plan.
  - TC-3.1.1 uses mocks for the unit test, but §4.2 is an integration test against a live harness.
- **Suggested fix**: Specify the stubbing mechanism concretely. Options: (a) use a thin_launcher wrapper that spawns a `sleep 3600` instead of claude, (b) use a custom test role that loops indefinitely, (c) inject a signal-blocking wrapper. Reference the existing test fixture pattern (`tests/test_harness.py` if present, as mentioned in §4 preamble).

---

### Summary

Two **errors** (findings 1–2) must be fixed before the plan is valid — one is a phantom AC reference, the other is a direct design contradiction that would cause TC-7.2 to fail by design.

Ten **warnings** (findings 3–12) are testability, completeness, or consistency issues. The most impactful are: #7693 closure lacking a gating integration test (finding 4), AC-6 insufficiently measured (finding 5), the byte-identical guarantee weakened (finding 6), and the CONTEXT inconsistency on restart force-kill (finding 8).
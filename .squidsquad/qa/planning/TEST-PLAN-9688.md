# TEST-PLAN-9688 — Orphan claude.exe Agent-tool subagent cleanup

**Source**: GitHub issue #9688 Acceptance + `.squidsquad/pm/planning/CONTEXT-9688.md` (D1-D8).
**Derived without reading the diff.** Verified against live install (live `orphan_cleanup.py`, `cycle_post.py`, `boot_remote.py`, `docs/ARCHITECTURE.md`, diagnostics dir, mock-based unit suite).

## AC list (issue body + CONTEXT §4 reconciled)

- **AC-1**: `orphan_cleanup.py` module exists with `sweep` + classify functions; runs in `cycle_post`; removes claude.exe orphans whose parent is dead AND path matches npm-install, PID != self.
- **AC-2**: Live agent (identified by `.claude-pid`) is never killed.
- **AC-3**: `boot_remote.py` invokes `sweep()` before respawning a role.
- **AC-4**: `.squidsquad/diagnostics/orphan-cleanup.{log|jsonl}` accumulates JSONL lines per CONTEXT D4 schema (timestamp, pid, parent_pid, decision, reason).
- **AC-5**: After a heavy multi-Agent-tool work session, orphan count for a clone stays ≤1.
- **AC-6**: Cross-platform; POSIX runs and exits silently with zero kills.
- **AC-7**: Unit tests cover all 7 D7 test cases.
- **AC-8**: `docs/ARCHITECTURE.md` updated with process-tree section per D8 locked text.

## Test Cases

### TC-1 (AC-1): `orphan_cleanup.py` public API present
- **Steps**: Import `orphan_cleanup`. Assert it exposes `sweep(invoked_by, dry_run)` and `_classify`. Assert `sweep("qa-verify", dry_run=True)` returns a dict with keys `kept|killed|skipped_roles|skipped_run|platform|invoked_by`.
- **Expected**: Module + signature + summary shape all present.

### TC-2 (AC-1): `cycle_post.py` invokes `orphan_cleanup.sweep` at end of cycle with `cycle_post:<role>` attribution
- **Steps**: Read `references/scripts/cycle_post.py`. Assert it `import orphan_cleanup` and calls `orphan_cleanup.sweep(invoked_by=f"cycle_post:{role}")` near end-of-cycle (after iteration logging, before exit-code decisions).
- **Expected**: Exactly one such invocation in cycle_post.py.

### TC-3 (AC-3): `boot_remote.py` invokes `orphan_cleanup.sweep` BEFORE spawning the role's terminal
- **Steps**: Read `references/scripts/boot_remote.py`. Assert `sweep(invoked_by=f"boot_remote:{role}")` is called inside `boot_agent()` and PRECEDES the `_spawn_terminal` call (textually earlier in the same function).
- **Expected**: Invocation present + ordering correct.

### TC-4 (AC-4): Diagnostics log format
- **Steps**: Invoke `orphan_cleanup.sweep(invoked_by="qa-verify-tc4", dry_run=True)` once. After the call, read `.squidsquad/diagnostics/orphan-cleanup.{log|jsonl}`. The file must exist; each line must parse as JSON; the most recent decision tagged `"invoked_by": "qa-verify-tc4"` must carry the CONTEXT D4 keys (`timestamp`, `decision`, `reason` minimum; `pid` + `parent_pid` for per-process decisions). Note: code uses `.jsonl` extension; CONTEXT D4 names `.log` — deviation is documented in QA results.
- **Expected**: File present, valid JSONL, schema fields populated.

### TC-5 (AC-2 + AC-5): Protected agent never killed; classify identifies orphan correctly
- **Steps**: Build a synthetic process list with (1) a protected agent (parent = mocked alive cmd.exe matching a role pid file), (2) an orphan (parent dead, npm-install path), (3) a live subagent (parent alive but not a role cmd.exe), (4) a non-npm claude.exe. Call `_classify` for each. Assert respectively `kept|killed|kept|kept` with the correct reasons.
- **Expected**: Classification matches.

### TC-6 (AC-6): POSIX no-op
- **Steps**: Patch `orphan_cleanup._is_windows` to return False. Call `sweep(invoked_by="qa-verify-posix")`. Assert summary is the empty/zero shape and no `_kill` was invoked.
- **Expected**: POSIX branch returns silent zero-kill summary.

### TC-7 (AC-7): 16 unit tests cover the 7 D7 cases
- **Steps**: Run `python -m pytest tests/test_orphan_cleanup_9688.py -v`. Map each D7 case to at least one test function by name; assert all 7 cases covered (empty / single protected / full squad / orphan / live subagent / missing pid skips / mixed). Assert all green.
- **Expected**: 16/16 PASS; 7-case coverage by name match.

### TC-8 (AC-8): ARCHITECTURE.md has D8 sections with locked content
- **Steps**: Read `docs/ARCHITECTURE.md`. Assert all 4 sections present: `### Agent Process Tree`, `` ### `.claude-pid` convention ``, `### Killing agents`, `### Three claude.exe populations`. Assert each contains the locked phrasing (cmd.exe chain, `taskkill /F /T`, three populations).
- **Expected**: All 4 headings + locked phrasing.

### TC-9 (AC-1 path filter): Non-npm claude.exe is never targeted
- **Steps**: Build a process list with a single claude.exe whose cmdline does NOT include `\node_modules\@anthropic-ai\claude-code\bin\claude.exe`. Call `_classify`. Assert decision is `kept` with reason "out of scope".
- **Expected**: Out-of-scope filter holds.

### TC-10 (AC-1 D3 safety): Sweep aborts entirely if any role's `.claude-pid` is unresolvable
- **Steps**: Monkey-patch `_role_pid_files` to return one role with a non-existent pid file. Run sweep. Assert `skipped_run=True` and `skipped_roles` non-empty.
- **Expected**: D3 abort fires.

### TC-11 (AC-1 own-pid safety): Own process never killed
- **Steps**: Build a synthetic process list including the current PID with an npm-install cmdline and dead parent. Run sweep with a populated protected set (none). Assert own PID is NOT in `killed`.
- **Expected**: own-PID skip enforced.

### TC-12 (live smoke): Real sweep on this clone is a no-op (or skips by D3)
- **Steps**: Invoke `orphan_cleanup.sweep(invoked_by="qa-verify-live", dry_run=True)` against the real process table of this clone. Assert no exception, summary dict returned, `killed` is either empty OR all listed PIDs are dry-run candidates (since we passed dry_run=True). If `skipped_run` is True (because peer roles' `.claude-pid` files aren't present in this single-role clone), that is per CONTEXT D3 — accepted.
- **Expected**: No crash; summary returned; live agent untouched.

## Coverage matrix

- AC-1 → TC-1, TC-2, TC-9, TC-10, TC-11, TC-12
- AC-2 → TC-5
- AC-3 → TC-3
- AC-4 → TC-4
- AC-5 → TC-5 (structural) + TC-12 (smoke) — full end-to-end heavy-session simulation is out-of-scope per CONTEXT D7 (mock-based testing locked)
- AC-6 → TC-6
- AC-7 → TC-7
- AC-8 → TC-8

Every AC has at least one TC.

## Comprehension Questions

This task touches `docs/ARCHITECTURE.md` — a documentation file, not an LLM-consumed instruction file (not CLAUDE.md, not a sub-skill fragment, not SOUL.md). Per the #9184 workflow the CQ requirement triggers on LLM-consumed instructions; doc updates do not. No CQ spec required.

If a future task pulls the orphan-cleanup population taxonomy into a sub-skill that agents Read on boot, CQ coverage will become mandatory then.

## Live verification

`.squidsquad/qa/planning/TEST-9688-tests.py` exercises TC-1…TC-12 directly. Dev's mock suite (`tests/test_orphan_cleanup_9688.py` 16/16) provides the D7 coverage gate; QA's suite layers in the live-cycle integration checks (invocation points + ordering + diagnostics file shape + ARCHITECTURE.md fidelity + live smoke).

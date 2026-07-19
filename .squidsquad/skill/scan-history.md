# Scan History

## Scan — 2026-07-18 23:53

- **Files scanned**: references/scripts/cli_stdio.py (45 lines, full read; never-scanned per name-vs-history diff — the #13198 cp1252-crash-proofing helper). Clean itself, but cross-referencing its own test suite's TestFleetWiring13198.WIRED sweep list against the codebase surfaced a real gap: references/scripts/git_ops.py is not in the 9-script sweep and never calls harden_stdio().
- **Findings**: 1 filed — #13728 (low — git_ops.py, the most heavily-invoked CLI script in the fleet, never calls harden_stdio() and has 4 live WARNING/ERROR-path print() literals containing U+2014 em-dash, confirmed via the same AST scan the test suite itself uses; a cp1252 console hitting any of these 4 paths would crash with UnicodeEncodeError, producing exactly the false-failure-then-harmful-retry pattern #13198 was created to eliminate fleet-wide).
- **Items rejected by human**: none

## Scan — 2026-07-18 23:47

- **Files scanned**: references/scripts/orphan_cleanup.py (519 lines, full read; never-scanned per name-vs-history diff — the Windows claude.exe orphan-reaper)
- **Findings**: none. Clean after a thorough read — already heavily iterated (D1-D8 CONTEXT locks plus #9926 per-role-skip fix and #9937 PID-recycle re-verification), with both unit (test_orphan_cleanup_9688.py) and live-integration (test_feat_9688_orphan_cleanup_live.py) coverage. No forced finding.
- **Items rejected by human**: none

## Scan — 2026-07-18 23:04

- **Files scanned**: references/scripts/atomic_emit.py (330 lines, full read; never-scanned per name-vs-history diff — the §4.6 verbatim-triple atomic-write module) and references/scripts/subloop_driver.py (339 lines, full read; also never-scanned, despite heavy personal use this session as the idle-cooldown-loop driver)
- **Findings**: 1 filed — #13722 (low — `read_state()`'s docstring explicitly claims to defend against hand-edited type corruption, but the `armed` field's coercion is bare `bool(data["armed"])`; a hand-edited `{"armed": "false"}` (JSON string, operator intending to disarm) coerces to `True` via Python's `bool("false") == True` gotcha — confirmed empirically, opposite of stated intent). atomic_emit.py checked clean — thorough existing test coverage (test_atomic_emit_b7.py), no functional gaps found; the one candidate (dead `.v2.md` filename_suffix coexistence branch) is deliberately retained per its own docstring, not a defect.
- **Items rejected by human**: none

## Scan — 2026-07-18 21:53

- **Files scanned**: references/scripts/comprehension_staleness.py (197 lines, full read; first scan of this file per scan-history — never-scanned per a name-vs-history diff, and I had just hit real friction with it this session doing #13565's baseline refresh)
- **Findings**: 2 filed — #13709 (low — `_PATH_RE`'s extension whitelist omits `j2`; a spec's `files` list naming a Jinja2 template like `references/prompts/test-plan.md.j2` gets silently dropped from `spec_fragment_paths()` because the regex greedily matches a truncated `.md`-suffixed substring that then fails the `is_file()` check — confirmed empirically against 1428_spec.json, which lists the file but never got a baseline entry for it) and #13710 (low — `refresh()`'s summary line prints `len(names)`, the *requested* count, not the actual number of specs that resolved and got a baseline entry; `main()` always exits 0 regardless — reproduced empirically this session: `refresh 1428 13464 10678` (wrong CLI form — bare numbers instead of `<N>_spec.json`) printed 3 WARNINGs then "baseline refreshed for 3 spec(s)" and exited 0 while writing zero entries).
- **Items rejected by human**: none

## Scan — 2026-07-18 18:23

- **Files scanned**: references/scripts/l4_parser.py (283 lines, full read; first scan of this file per scan-history — continuing the L4-family vein, this time the upstream H2/H3 grammar parser that produces the `L4Op` records `l4_op_processor.py` consumes, verified clean at the 17:41 scan)
- **Findings**: 1 filed — #13683 (low — `_OP_LIKE_RE`/`_OP_RE`, the H3 op-directive grammar, are case-sensitive against the five reserved op keywords, but the module's own docstring and #10987's design intent both promise malformed ops are rejected loudly ("that's the 'malformed H3 op' AC bullet"). A case-varied exact keyword — e.g. `### Replace step:cycle/boot` — matches neither the op-like check (case-sensitive, so it's routed to the prose path) nor the malformed-diagnostic path, and is silently absorbed as inert prose into the slot's implicit append body: the intended customization never applies, zero error is raised, and the malformed L4 syntax leaks verbatim into the composed agent CLAUDE.md. Empirically reproduced via unmocked `parse_l4_text` before filing. Cross-checked `tests/test_l4_parser.py`'s existing `test_non_op_like_h3_treated_as_prose` (deliberate-prose cases) and `test_malformed_h3_rejected` (near-miss cases that DO raise) parametrizations — neither includes a case-varied exact keyword, confirming this is a genuine untested gap, not an intentional design choice being mis-scanned.)
- **Items rejected by human**: none
- **Criteria note**: the "does the code's actual failure-mode match its own documented failure-mode contract" lens (first productive at #13669) struck again here — worth treating as a standing lens to re-apply on every file, not a one-off. Before concluding a suspected gap is real, cross-checked the file's OWN existing test parametrizations for the specific input shape (case variation) rather than just the general behavior category (prose-vs-op) — the general category is well-tested, the specific edge case wasn't, and that distinction is what separates a genuine gap from a redundant finding.

## Scan — 2026-07-18 17:41

- **Files scanned**: references/scripts/l4_op_processor.py (496 lines, full read; first scan of this file per scan-history — continuing the productive L4-family vein from the 16:53 scan that found #13672, cross-referenced against the systematic script-name-vs-scan-history diff)
- **Findings**: none. Empirically tested (per this session's "test before filing" discipline, actual unmocked calls to `apply_l4_ops`) three scenarios that looked like plausible defects on inspection: (1) `replace step:cycle/X` where X is an L1 parent with a nested H4 substep — confirmed it surgically replaces only X's own leading prose and correctly preserves the nested substep verbatim, matching the multi-level-anchor design rather than being a truncation bug; (2) two sequential `insert-after` ops targeting the same step — confirmed they stack in application order (first insert lands before second) rather than colliding or reordering; (3) a counter-op (`<!-- counter-op: ... -->`) sandwiched between `replace` ops on two DIFFERENT step IDs — confirmed `_strip_counter_op_pairs` correctly pairs only with the most-recent prior `replace` targeting the SAME step_id and does not cross-cancel the other step's replace. Also chased down the module docstring's own admission that A2c "does NOT enforce [whole-slot-replace mutual exclusivity]... deferred to A2e" — confirmed A2e (`link_stage_validator.py`, R1-R7) actually shipped and enforces exactly this (R6: whole-slot replace mixed with other ops; R5: op references non-existent step-id) BEFORE `apply_l4_ops` ever runs in production, and confirmed the full wiring chain is live end-to-end: `compose.py` → `v2_link_stage.emit_v2_linked` → `l4_op_processor.apply_l4_ops` (not the "shipped unwired" gap pattern this session's #13664/#13669/#13672 findings shared — this one is fully wired and pre-validated).
- **Items rejected by human**: none
- **Criteria note**: two minor dead-variable nits observed (`range_end` in `_render_hydrated_cycle_diagram` and `last_boot_node`/`first_walk_node` in `_emit_mermaid_flowchart` are computed but never read) — no functional impact, consistent with prior scan convention (05-24 cycles) of not filing pure style/dead-code nits absent behavioral effect. This is the fourth L4-family file scanned this session (after l4_write_commit.py #13664, l4_conflict_preempt.py #13669, l4_file_watcher.py #13672) to return a clean/near-clean result — a useful signal that the "does the deferred/documented gap actually still exist" lens is worth re-running on each remaining unscanned L4 sibling (l4_parser.py, l4_removal.py, l4_compose_dryrun.py, l4_mini_cq.py) rather than assuming the vein is exhausted.

## Scan — 2026-07-18 16:53

- **Files scanned**: references/scripts/l4_file_watcher.py (653 lines, full read; another of the never-scanned references/scripts/*.py files, chosen because BRIEFING.md's own history references it as a repeat source of real production bugs — #13197, #13211, #13303)
- **Findings**: 1 filed — #13672 (low — "shipped unwired" class. The module docstring documents `recompose_path()` as "the public entry point for both the file-watch handler AND the optional `.git/hooks/post-commit` script" (PRD-E Q-E2). Confirmed via grep across the whole repo (excluding the function's own definition and its 15-reference unit test file) and by listing `references/git-hooks/` directly (contains only `pre-commit` + `post-merge`, activated via `git_ops.install_hooks()`): no `post-commit` script exists at all, so `recompose_path()` — fully implemented and exhaustively tested in isolation — has zero production callers. The primary file-watch trigger covers the common case; the gap is specifically the redundancy path the docstring frames as a safety net for when the watcher isn't running.
- **Items rejected by human**: none
- **Notes**: the rest of the file is unusually well-hardened — every failure path (freshness-guard raise, registry-parse failure, compose-runner exception, debounce race) is caught, documented, and tied to a specific past incident (#12906/#13197/#13211/#13303/DS-E3-F1). No fail-open/fail-closed inconsistency found on a full read. This continues the "read the file BRIEFING.md's own incident history flags as hot" targeting heuristic — worth trying again next time a file with a documented incident trail comes up in the never-scanned list.

## Scan — 2026-07-18 15:53

- **Files scanned**: references/scripts/l4_conflict_preempt.py (339 lines, full read; first scan of this file per scan-history — another of the 18 references/scripts/*.py files with zero prior scan-history mentions, same systematic gap-find as the 14:24 scan)
- **Findings**: 1 filed — #13669 (low — `preempt_conflict()`'s module docstring states an explicit design contract: "every unrecoverable path raises a typed `ConflictPreemptError` subclass". The replace-op short-circuit guard `if op_type and _REPLACE_OP_RE.match(op_type):` lets a falsy `op_type` fall through to `op_type.split()[0]` at task_id construction — empirically reproduced (unmocked call): `op_type=""` raises `IndexError`, `op_type=None` raises `AttributeError`, neither a `ConflictPreemptError`. The sole caller is prose in `l4-curation.md` (LLM-driven, not a deterministic Python call site), so a malformed invocation reaching this function is a realistic path, not hypothetical. Confirmed via the otherwise-thorough 480-line test suite: no test covers empty/None op_type.)
- **Items rejected by human**: none
- **Criteria note**: "does the code's actual failure-mode match its own documented failure-mode contract" is a productive lens distinct from generic fail-open/fail-closed consistency — this module explicitly promises a typed-exception-only failure surface, which makes an unguarded raw builtin exception a direct contract violation, not just a style nit. Verified the finding by executing the real (unmocked) function with the edge-case input before filing, per this session's "test before filing" discipline — turned a suspected gap into a confirmed, reproduced one.

## Scan — 2026-07-18 14:24

- **Files scanned**: references/scripts/l4_write_commit.py (261 lines, full read; first scan of this file per scan-history -- one of 18 references/scripts/*.py files with zero prior scan-history mentions, systematically identified via a name-vs-history diff)
- **Findings**: 1 filed — #13664 (low — `write_and_commit_l4()`'s Phase 2 stages the L4 file with a pathspec-restricted `git add -- <relative>` but commits with a bare `git commit -m subject -m body`, no pathspec restriction. `git commit` without a trailing pathspec commits the WHOLE index, so any pre-existing staged-but-uncommitted content at entry silently rides the L4 write's commit and reaches origin under a misleading subject. The function's own code comment explicitly names this exact scenario but its described defense (`pre_commit_sha` capture) only protects the push-failure REVERT path, not the success path -- confirmed via the existing test suite, which asserts the revert-path SHA is correct but never asserts a pathspec restriction on the `git commit` call itself. Fix: `[\"git\", \"commit\", \"-m\", subject, \"-m\", body, \"--\", relative]`, mirroring the existing `git add` restriction.)
- **Items rejected by human**: none
- **Criteria note**: systematic script-name-vs-scan-history diffing (`ls references/scripts/*.py` vs grep-count-per-file) surfaced 18 never-scanned scripts in one pass -- cheaper and more targeted than relying on `scan_index.py suggest-targets`, which keeps resurfacing the same high-churn files (harness.py, tracker.py, docs/*-ARCH.md) already covered by recent scans. Worth repeating this systematic gap-find next time suggest-targets returns only repeats. Also: a code comment claiming a defense exists is not proof the defense is complete -- verify what specifically the cited mitigation covers (here: revert-path only, not the success path the comment's own scenario describes) before trusting it and moving on.

## Scan — 2026-07-18 13:22

- **Files scanned**: references/sub-skills/common-events/event-mode-contract.md (stale-reference/documentation-drift check — first scan of this file per scan-history, despite it being the core event-mode wake contract every event-mode agent, including this session, operates under)
- **Findings**: none. Cross-referenced every concrete claim against the live implementation: `_emit_boot_deploy_signals()` exists (harness.py:5094, called from the boot-drift path at L2683); `event_poll.py`'s documented `--wait`/`--target` CLI flags exist (argparse at L370-378); all referenced harness endpoints exist (`POST /events`, `GET /events/for/{role}`, `GET /events/cursor/{role}`, `POST /events/{event_id}/complete`); the `ack-stop.result` enum the doc cites (`checkpointed`/`aborted`/`drained`) matches harness.py:3726 exactly, and the separately-documented `deploy-halted` result value is handled distinctly at L3741 as the doc describes. Case D's `status:blocked` semantics (#13515) match tracker.py's documented role-authority matrix. No stale references, no drift.
- **Items rejected by human**: none
- **Criteria note**: this file's active maintenance (cross-referenced with #13569/#13369/#12854/#13077/#9742 inline) likely explains the clean result — it reads as a living document teammates actively correct, not a write-once spec that silently rots. Worth returning to less-frequently-touched sub-skill docs next (e.g. ones with no recent issue-number citations) where drift is more likely to have accumulated unnoticed.

## Scan — 2026-07-18 12:23

- **Files scanned**: tests/test_git_ops.py (test-quality/coverage triage, not scanned in recent history despite this session's heavy git_ops.py work), references/scripts/git_ops.py (#13554/#13285 scope-audit helpers: _pr_declared_files, _pr_state_scope_violations, _merge_commit_sha, _scope_audit_violations -- read for the first time this session)
- **Findings**: none. Test-quality: 316 test functions/classes, zero skip/xfail/TODO/FIXME markers -- healthy, matching test_harness.py's 2026-07-11 result. Cross-referenced every top-level git_ops.py function name against test_git_ops.py + the rest of tests/ for zero-reference gaps; the one apparent hit (`_timeout_failure`, 0 direct literal references) turned out to be fully covered indirectly -- `test_timeout_check_{true,false}_raises/_returns_nonzero` (both `_run` and `_run_list` variants) exercise both its check=True/False branches end-to-end via `subprocess.TimeoutExpired` injection, just without naming the helper directly. The scope-audit helpers all fail-safe consistently (return `None` on gh/git uncertainty; callers flag-don't-guess, never auto-act on `None`).
- **Items rejected by human**: none
- **Criteria note**: a literal function-name cross-reference is a cheap first pass for "test gaps" but produces false positives for helpers only exercised indirectly through their sole caller's tests -- always read the flagged test file before concluding a gap is real, not just grep-absence. This is the third consecutive scan into git_ops.py's #13447/#13554/#13285/#13654 merge-guard surface (2026-07-18 10:57, this one) to return zero findings after a thorough read -- read as the area being genuinely stable post-heavy-audit, not scan fatigue; worth picking a different file next time this queue comes up.

## Scan — 2026-07-18 10:57

- **Files scanned**: references/scripts/git_ops.py (focused: pr_merge()'s #13447/#13654 pre/post-merge guard functions — _neutralize_pr_body_before_merge, _revert_composed_state_contamination, _checkout_and_ff_working_after_merge — navigation-derived from this session's #13654 round-2 fix)
- **Findings**: none — grepped for other `gh pr edit` call sites (the exact defect class #13654 round 2 fixed: old `gh` 2.34.0 GraphQL-querying a removed `projectCards` field) and found none remaining in `references/scripts/`; independently confirms the same conclusion QA's own concurrent scan reached (commit 946e10a46, "confirmed gh pr edit bug is scoped correctly, no other call sites affected"). `_revert_composed_state_contamination`/`_checkout_and_ff_working_after_merge` fail-open consistently per their docstrings; `_get_working_branch()` fallback-to-"main" is safe. Sanity-checked `gh pr ready` against a real closed PR (#13655) — clean early "PR is closed" error, no GraphQL crash, so it does not appear to share the `gh pr edit` bug (not exhaustively proven on an open draft, but no evidence of the same failure mode).
- **Items rejected by human**: none
- **Notes**: this scan's driver tick coincided with #13654 shipping (verifier PASS, DM merged) and QA's own scan landing on the identical question — a useful cross-check that two independent scans (skill + qa) converged on the same "scoped correctly" conclusion via different methods (grep vs whatever QA's pass used).

## Scan — 2026-07-18 08:24

- **Files scanned**: references/scripts/wizard.py (full exception-handling sweep, fail-open/fail-closed consistency lens per prior scans' productive criteria), docs/archive/EVENT-ARCHITECTURE.md (stale-claim spot-check, same lens that surfaced #13317's PID-sole-liveness fix this session)
- **Findings**: none — wizard.py's ~30 exception handlers all consistent with their documented contracts (fail-open where the docstring promises it, e.g. `load_preset_manifest`/`_harness_reachable`/`_install_aliases`; fail-loud with a printed WARNING where correctness matters, e.g. `cmd_setup_yes`'s label-creation step). The one handler that looked suspicious on first read — `except (ImportError, SystemExit, Exception):` at line 3731 in `generate_default_spec`'s version-read — is deliberate, not a bug: `config.get_field()` → `_read_config()` calls `sys.exit(1)` when config.md is missing, which IS the normal greenfield-install case this function runs in; catching SystemExit here is required to avoid the wizard process dying on a version lookup before config.md exists. EVENT-ARCHITECTURE.md's `.claude-pid` references (thin_launcher writing the file, singleton enforcement) remain factually accurate post-#12492/#13317 — only which signal is *authoritative for reboot decisions* changed, not whether thin_launcher still writes the PID file.
- **Items rejected by human**: none yet
- **Criteria note**: the fail-open/fail-closed consistency lens (productive in three prior scans: #13170/#13172/#13261) this time correctly concluded "healthy" rather than forcing a finding — worth recording that a lens returning zero findings on a full sweep is itself useful signal, not scan failure. Also worth noting for future scans: an `except (X, SystemExit, ...)` combination is not automatically a code smell — check whether the wrapped call can itself call `sys.exit()` (as `config.py`'s `_read_config()` does) before flagging it.

## Scan — 2026-05-31 16:15

- **Files scanned**: references/scripts/event_validator.py (full 261 lines; focus on the 4 validation checks, the CLI surface, and the Finding shape). Briefly compared with statusline_data.py (138 lines, deferred because the SQUIDSQUAD_DIR foot-gun there is the same family as already-filed #10516 — no fresh finding).
- **Findings**: #10537 (low — `check_reaction_cycles` walks pairs of roles with a nested loop, so it only catches **2-cycles** (A↔B). 3-role cycles (A→B→C→A) and longer rings pass silently even though the docstring promises "circular reaction chains" plural. Recommendation: replace the pairwise loop with a strongly-connected-components walk (Tarjan/Kosaraju) over the role-reaction graph; report each SCC of size ≥ 2 once. Out-of-scope side-findings noted: `--config <path>` CLI flag silently does nothing when the path is missing from argv; `Path(...).read_text()` doesn't catch FileNotFoundError; orphaned-emit warning text doesn't acknowledge infrastructure consumers).
- **Items rejected by human**: none yet
- **Notes**: statusline_data.py module-level `SQUID_DIR = REPO_ROOT / '.squidsquad'` is the same SQUIDSQUAD_DIR-captured-at-import-time pattern as #10516 in event_bus.py. Less impactful here because statusline.sh invokes the script as a fresh subprocess each refresh (no in-process callers), but flagged in scan notes for the consolidation when #10516 lands and we sweep for siblings. event_validator's `check_hallucinated_events` correctly uses `event_type not in known` against the catalog; `check_missing_consumers` correctly includes `EMITTED.keys()` so infrastructure emits count as available producers; `check_orphaned_emits` does NOT include infrastructure consumers and may produce false positives on events that infrastructure silently consumes — minor UX gap, called out as out-of-scope in #10537. Finding's `__slots__` is fine. `_describe` falls back to raw event-name on unknown types; intentional for the hallucinated branch.

## Scan — 2026-05-31 15:15

- **Files scanned**: references/scripts/reboot_agent.py (full 110 lines; focus on the post-#4792 surface — _kill_process + _read_claude_pid + the deprecated CLI).
- **Findings**: #10530 (low — `_kill_process(pid)` passes pid straight to `os.kill(pid, SIGKILL)` on POSIX with no validation: pid=0 sends SIGKILL to the whole process group (incl. the harness itself), pid=-1 sweeps every process the calling user can signal, pid=None raises TypeError which propagates past the `(ProcessLookupError, PermissionError)` catch and breaks the caller. process_utils.is_process_alive already has the symmetric guard from #10440; the destructive sibling lacks it. Defense-in-depth: reject pid is None / not int / <= 0 before any kill call; add TypeError to the POSIX catch).
- **Items rejected by human**: none yet
- **Notes**: `_read_claude_pid` correctly delegates the alive bit to `process_utils.is_process_alive` (uses the #10440-hardened path). Windows `taskkill /F /PID 0` targets System Idle Process and the kernel refuses it; `check=False` swallows the non-zero exit, so the Windows risk is less catastrophic than POSIX. Module-level `from process_utils import ...` follows the sibling-import-via-sys.path pattern; consistent with other scripts. `main()` deprecation message points operators at the harness API; Phase 3 of #8979 removes it entirely so not worth more attention now. The file rename to `process_ops.py` (per docstring) is also a separate Phase 6+ task — flagged as out-of-scope in #10530.

## Scan — 2026-05-31 14:15

- **Files scanned**: references/scripts/diagnostics.py (full 290 lines; focus on the auto-rotate check-then-write window + the per-entry append model + redaction surface).
- **Findings**: #10523 (low — `log_entry` does stat-then-rotate-then-open-append, which races under concurrent multi-agent writers: two writers can both observe size > 1MB, both call rotate(), and the second `atomic_write_text` truncates an already-truncated file using a stale view of the last 500 entries. Recommended fix: move rotation off the write path (CLI-only) OR add a file lock around the whole stat+rotate+append block OR collapse rotate + append into a single read-modify-write under lock. Bounding per-entry size at the boundary keeps single appends atomic on POSIX without lock).
- **Items rejected by human**: none yet
- **Notes**: `_redact_entry` recursive walk looks correct (lists pass through element-by-element, dict keys checked via `_is_sensitive_key` substring match, non-mutating). `_sanitize_config`'s per-line redaction at L156-162 is heuristic — uses substring match against the whole line including the value, so `## Repository URL` is flagged as sensitive (good) but the redaction itself only strips the value, fine. `is_public_repo` shells out to `gh repo view` with no caching but only called from `report`, not hot path. Module-level `LOG_FILE = DIAGNOSTICS_DIR / 'diagnostic.jsonl'` (L85) is captured at import-time; if `state_bus.state_path('diagnostics')` ever changes its resolution semantics, this becomes a similar SQUID_DIR-style foot-gun to #10516, but state_path is static today. Out-of-scope side-finding called out in #10523: `log_entry` has no exception guard, so a permission error or disk-full would propagate to callers (cycle_post.py) and crash the cycle — `event_bus.emit` swallows by design, this doesn't; worth its own issue if it fires.

## Scan — 2026-05-31 13:16

- **Files scanned**: references/scripts/event_bus.py (full 190 lines; focus on the SQUIDSQUAD_DIR foot-gun introduced by #9398 + the silent-no-op timeout contract).
- **Findings**: #10516 (low — `SQUID_DIR = _resolve_squid_dir()` is captured once at module-import time, so any code path that sets `SQUIDSQUAD_DIR` AFTER `event_bus` is first imported sees zero effect. The existing test fixture in `test_9398_squidsquad_dir_env_var.py` worked around it by doing a full `importlib` reload, which is the only way to verify the env-var path fires today. Production launcher sets the env before Python starts so it doesn't bite today, but it's a foot-gun for any future dynamic-dispatch or integration test caller. Fix: inline the resolution inside `_discover_port()`).
- **Items rejected by human**: none yet
- **Notes**: `_TIMEOUT = 0.5` combined with the silent-no-op contract means a stale `.harness-port` file (harness crashed but file wasn't cleaned) burns 500ms per emit with no fast-failure feedback — worth a separate issue if it ever shows up in profiles, called out as out-of-scope in #10516. `_generate_id` uses sha256 with `os.urandom(2)` nonce (#9415 fix); 16-char width + 4-hex nonce is solid. The broad `except Exception: pass` in `emit()` is the documented fire-and-forget contract; not a defect. `urllib.request.urlopen` doesn't enter a context manager, but on the success path Python's GC closes the socket promptly enough; not worth flipping.

## Scan — 2026-05-31 09:45

- **Files scanned**: references/scripts/process_utils.py (full 71 lines; focus on the Win32 ctypes liveness probe at L54-71), references/scripts/thin_launcher.py (L78-105 — deliberate sibling copy of same routine per #8891).
- **Findings**: #10440 (low — both copies use `ctypes.windll.kernel32` without `use_last_error=True` and rely on `kernel32.GetLastError()`; documented-incorrect ctypes pattern, the per-thread last-error slot can be reset by any intervening Python Win32 call before the check fires. Also no `argtypes`/`restype` set on OpenProcess/CloseHandle/GetExitCodeProcess, so HANDLE is treated as 32-bit signed instead of 64-bit pointer — ABI-wrong, rarely visible in practice because Windows process handles are small. Fix mirrors both files and adds a unit test that monkey-patches the kernel32 stub.)
- **Items rejected by human**: none yet
- **Notes**: process_utils.is_process_alive currently has no direct unit test — exercised only through health_check; recommended adding a focused test alongside the fix (worker SOUL bug-fix rule: lock the fix at the source level). PID validation (`pid <= 0` rejection) at L43 is correct and important — `os.kill(0, 0)` would target the process group. `_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000` is the right access right for liveness-only probes (no PROCESS_QUERY_INFORMATION needed). The two copies' divergence risk (#8891 deliberately keeps the sibling) means the fix must be applied to both atomically — recommend a single-commit PR touching both files.

## Scan — 2026-05-26 08:09

- **Files scanned**: references/scripts/health_check.py (full 424 lines; focus on config-read robustness, dead imports, TOCTOU on state-file mtime+content reads).
- **Findings**: #10348 (low — `_read_interval` catches `(ImportError, ValueError, TypeError)` but `config.get_field` raises `SystemExit` on missing field; documented 30-min default never fires; misleading exit-1 instead. Same family as cycle_post._config_get's `except BaseException:` fix).
- **Items rejected by human**: none yet
- **Notes**: dead imports at L26-29 (`os`, `platform`, `subprocess`) — cosmetic, called out as out-of-scope in #10348. `_read_file_head` reads whole file then slices — fine for current-state-sized files. `_get_file_mtime` and `_read_file_head` are separate stat+read calls on the same file (mild TOCTOU), but the staleness check tolerates the gap. `check_agent_health` correctly handles missing `.claude-pid` (mtime fallback) and missing both files (UNKNOWN); the harness is the authoritative liveness source per #4966 so this offline-fallback script's role is bounded.

## Scan — 2026-05-25 18:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1424.

## Scan — 2026-05-25 17:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1423.

## Scan — 2026-05-25 17:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1422.

## Scan — 2026-05-25 16:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1421.

## Scan — 2026-05-25 16:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1420.

## Scan — 2026-05-25 15:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1419.

## Scan — 2026-05-25 15:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1418.

## Scan — 2026-05-25 14:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1417.

## Scan — 2026-05-25 14:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1416.

## Scan — 2026-05-25 13:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1415.

## Scan — 2026-05-25 13:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1414.

## Scan — 2026-05-25 12:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1413.

## Scan — 2026-05-25 12:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1412.

## Scan — 2026-05-25 11:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1411.

## Scan — 2026-05-25 11:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1410.

## Scan — 2026-05-25 10:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1409.

## Scan — 2026-05-25 10:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1408.

## Scan — 2026-05-25 09:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1407.

## Scan — 2026-05-25 09:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1406.

## Scan — 2026-05-25 08:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1405.

## Scan — 2026-05-25 08:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1404.

## Scan — 2026-05-25 07:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1403.

## Scan — 2026-05-25 07:09

- **Files scanned**: none.
- **Findings**: none. Cycle 1402.

## Scan — 2026-05-25 06:39

- **Files scanned**: none.
- **Findings**: none. Cycle 1401. #10007 PASSED QA (commit 3e066a92, PR #10162 — duplicate session's atomic_write_text + 10 call sites). My cycle-1400 scan-history edit was overwritten — confirmed dual-session git race on `.squidsquad/skill/` state files. Lower-priority race than the queue-pickup race; just causes log-entry drops.

## Scan — 2026-05-25 05:39

- **Files scanned**: none.
- **Findings**: none. #10007 shipped to pending-test by duplicate session. Queue at 4 open items.
- **Notes**: cycle 1398. Continuing race avoidance.

## Scan — 2026-05-25 05:09

- **Files scanned**: none — minimal cycle (queue coordination).
- **Findings**: none.
- **Notes**: cycle 1396. #10007 is now in-progress (duplicate skill session picked it up). #10156 newly filed by QA (8 hardcoded {dev, qa} test residuals — another AC2.6 sweep gap, same pattern as #10133). Deliberately staying quiet this cycle to avoid dual-pickup race with the duplicate session — even though queue protocol says "pick first", that protocol assumes single-agent operation. The right adaptation for the dual-agent situation is to NOT race on in-progress items, and to NOT speculatively grab open items the other session may be about to.

## Scan — 2026-05-25 04:39

- **Files scanned**: none.
- **Findings**: none. Observation: #10072 picked up + fixed by *another* skill session (PR #10150). Confirms the duplicate agent (pid 2937296) is still alive and producing real work — racing with this session. Until #10101 ships and operator restarts, both sessions will keep cycling.
- **Notes**: cycle 1394.

## Scan — 2026-05-25 04:09

- **Files scanned**: none — minimal no-op.
- **Findings**: none.
- **Notes**: cycle 1392, state similar to 1390.

## Scan — 2026-05-25 03:39

- **Files scanned**: none — minimal no-op cycle (3 PRs in pending-test, no new work).
- **Findings**: none.
- **Notes**: cycle 1390, state similar to 1389. Context 61%.

## Scan — 2026-05-25 02:10

- **Files scanned**: references/scripts/thin_launcher.py (focused: `_write_pid` L122-128 + `_check_singleton` L102-119 + npm shim resolution path)
- **Findings**: #10101 (high — singleton check fails because `_write_pid` records `proc.pid` which on Windows-via-npm is the cmd.exe shim wrapper, not the actual claude.exe; wrapper exits in seconds, `.claude-pid` becomes stale, next thin_launcher invocation spawns a duplicate claude.exe; root cause of memory rule `project_skill_agent_running` observations). Investigation triggered by human report at cycle 1385. Live evidence: 2 skill claude.exe processes (pids 2738704 and 2937296) in this clone; parent of older = dead, parent of newer = the cmd.exe currently recorded in `.claude-pid`.
- **Items rejected by human**: none yet
- **Notes**: investigation cycle, not routine rotation. `shutil.which('claude')` returns `claude.CMD` on the affected system — confirms the npm shim hypothesis. Recommended fix path is surgical: prefer `shutil.which('claude.exe')` on Windows before falling back to `.CMD`. Files awaiting human decision on (a) killing the duplicate process pid 2937296, (b) any other remediation.

## Scan — 2026-05-25 01:39

- **Files scanned**: none — minimal no-op cycle.
- **Findings**: none.
- **Notes**: cycle 1385, state identical to 1384.

## Scan — 2026-05-25 01:09

- **Files scanned**: none — minimal no-op cycle.
- **Findings**: none.
- **Notes**: cycle 1384, state identical to 1383.

## Scan — 2026-05-25 00:39

- **Files scanned**: none — minimal no-op cycle.
- **Findings**: none.
- **Notes**: cycle 1383, state identical to 1382.

## Scan — 2026-05-25 00:09

- **Files scanned**: none — minimal no-op cycle.
- **Findings**: none.
- **Notes**: cycle 1382, state identical to 1381.

## Scan — 2026-05-24 23:39

- **Files scanned**: none — minimal no-op cycle.
- **Findings**: none.
- **Notes**: cycle 1381, state identical to 1380.

## Scan — 2026-05-24 23:09

- **Files scanned**: none — minimal no-op cycle.
- **Findings**: none.
- **Notes**: cycle 1380, state identical to 1379.

## Scan — 2026-05-24 22:39

- **Files scanned**: none — minimal no-op cycle (state unchanged).
- **Findings**: none.
- **Notes**: cycle 1379, state identical to 1378.

## Scan — 2026-05-24 22:09

- **Files scanned**: references/scripts/scan_index.py (re-check, no read this cycle)
- **Findings**: none. Minimal cycle. cycle_pre auto-fixed a config.md version regression (0.29.0 → 0.43.0) per #5136.
- **Items rejected by human**: none yet
- **Notes**: same state as cycle 1377. QA hasn't re-picked #9965. 5 open scan findings.

## Scan — 2026-05-24 21:39

- **Files scanned**: references/scripts/health_check.py (re-check; previously scanned with no new findings)
- **Findings**: none. Minimal cycle while QA re-verifies #9965. Context 47%, conserving.
- **Items rejected by human**: none yet
- **Notes**: #9965 still pending-test (QA hasn't re-picked yet after cycle 1376 re-transition). Open scan-finding backlog unchanged at 5 items.

## Scan — 2026-05-24 21:20

- **Files scanned**: not applicable — QA-rejected fix-up cycle (highest priority per protocol)
- **Findings**: not applicable
- **Items rejected by human**: not applicable
- **Notes**: cycle 1376 picked up the QA rejection of #9965. Fixed 2 assertions in `tests/test_manifest_registry.py::TestShippedRegistry` (L193 + L201/L203) from `{dev, qa}` to `{worker, verifier}` per AC2.6. Committed 7e43a745, AC2.9 re-affirmed 06037552. Re-transitioned to pending-test.

## Scan — 2026-05-24 20:36

- **Files scanned**: references/scripts/cycle_pre.py (focused: `_enforce_branch` L193-230)
- **Findings**: #10072 (medium — `_enforce_branch` task parsing breaks on verbose `#NNNN — desc` format; `lstrip(\"#\").strip()` + `.isdigit()` fails the digit check when task field carries the standard human-readable description after the issue number; manual checkout required every cycle of feature work; observed cycles 1334-1373 of #9965). Carried in working-state since cycle 1334; filed now that #9965 has shipped to pending-test.
- **Items rejected by human**: none yet
- **Notes**: minimal-cycle filing of a previously-deferred process bug. The fix is trivial (regex extraction of leading digits) but the impact is real — every feature-work cycle currently no-ops branch enforcement until the operator manually checks out.

## Scan — 2026-05-24 20:33

- **Files scanned**: not applicable — active implementation cycle (not improvement scan)
- **Findings**: not applicable
- **Items rejected by human**: not applicable
- **Notes**: cycle 1374 was a substantial implementation cycle, not a scan rotation. Human lifted STOP on #9965 at start; skill picked up AC2.4-2.7 + AC2.9. Spawned 2 subagents for the implementation work (the second to re-apply DS-hardening that I accidentally reverted via a misuse of `git checkout HEAD -- ...`). Lessons captured below for future reference.

## Scan — 2026-05-24 19:09

- **Files scanned**: references/scripts/event_validator.py (re-check; previously scanned 2026-05-20 with no findings — confirmed still applies, no re-read this cycle)
- **Findings**: none. Cycle skipped fresh code reads to preserve context (37%, trending up post-1371). Recording a no-op rotation entry only.
- **Items rejected by human**: none yet
- **Notes**: deliberate amortization cycle — see cycle 1372 notes on context post-1371 cross-role read. State: paused #9965, 4 open scan findings, no PM/human triage activity.

## Scan — 2026-05-24 18:39

- **Files scanned**: references/scripts/migrate_state_branch.py (re-check; already had #9939 filed cycle 2026-05-22 about migrate() discarding state_bus.commit_and_push() return value — confirmed still present, finding still valid, no follow-up needed)
- **Findings**: none new. Re-verified #9939 (medium) is still open and accurately scoped.
- **Items rejected by human**: none yet
- **Notes**: minimal cycle — context jumped to 36% from cycle 1371's PM CLAUDE.md auto-load when reading .squidsquad/pm/planning/. Lesson for future: reading files under another role's .squidsquad subtree triggers that role's composed CLAUDE.md auto-injection. If I want PM brainstorm content again, ask for the file via Read on the exact path rather than browsing planning/ — or accept the context cost as the price of the cross-role visibility.

## Scan — 2026-05-24 18:10

- **Files scanned**: .squidsquad/pm/planning/BRAINSTORM-vault-subskills.md (PM's exploratory plan for vault sub-skill redesign, 180 lines, pre-approval)
- **Findings**: none filed (it's a brainstorm, not approved scope). Cross-role situational awareness: PM is proposing to tear down `vault-protocol`, `vault-protocol-slim`, `vault-remember`, `vault-optimize` (as cycle routines), and `vault-synthesis`; replace with two classes — A (composed sub-skills hooked into agent workflow) and B (event-bus-subscriber sub-skills running in the harness layer). A6 `vault-capture-on-scan-finding` is the proposed handler for the T2 improvement-scan trigger; PM explicitly cites **#10007's audit** as the paradigm case for "systemic finding → auto-create `pattern-*.md` vault note alongside the bug". My cycle-1361 audit-vs-file methodology (captured in `learning-scan-comment-vs-file-duplicate.md` cycle 1362) is being absorbed upstream into PM's broader proposal — positive signal that scan output is being read.
- **Items rejected by human**: none yet
- **Notes**: PM has 5 open questions for human (B-class lifecycle timing, ASK-USER autonomous protocol, B3 L4-injector v1-vs-v2, drop `projects/` folder, cron host for `vault-decay-keeper`). Skill should NOT react with implementation while brainstorm is pre-approval — but worth tracking. Question 2 (ASK-USER protocol in autonomous cycles) affects skill: my last 30+ cycles have been autonomous, and vault-capture-on-pr's ASK-USER would fire in that context. When PM files concrete tasks from the brainstorm, skill can offer the autonomous-cycle perspective as a CONTEXT.md input.

## Scan — 2026-05-24 17:39

- **Files scanned**: references/scripts/forgejo_setup.py (385 lines; Docker Compose deployment automation for local Forgejo instance — 9 functions, setup-time tool not in steady-state path)
- **Findings**: none. Spot-check confirmed careful subprocess handling (explicit `returncode` inspection with `check=False`), clear user-facing error messages, deploy template separation. Did not do a deep line-by-line — setup tooling has low steady-state blast radius and the context economy doesn't justify a thorough sweep this cycle.
- **Items rejected by human**: none yet
- **Notes**: verified that none of the four open scan findings (#10002 cycle_post, #10005 diagnostics, #10006 squidsquad_cli, #10007 vault_remember) have been fixed in the last 3 days — no recent commits touch those files. PM/human triage backlog remains untouched. Reserving manifest.py (646), compose.py (1567), tracker.py (1503), harness.py (2936), scan_index.py (813), vault_optimize.py (664) for cycles when context is fresher or a specific question warrants the deep read.

## Scan — 2026-05-24 17:10

- **Files scanned**: references/scripts/vault_entity.py (218 lines; heuristic entity-extraction utility for vault-remember)
- **Findings**: none. PROPER_NAME_PATTERN over-matches by design (LLM judgment downstream filters); `_is_noise_name` correctly checks both full name and first-word so "GitHub Actions" is filtered via "GitHub" in NOISE_WORDS. PREFERENCE_MARKERS substring search is intentionally loose. The shared `seen` set between URLs and proper names is theoretically clash-prone but the type space is disjoint in practice. Performance is O(M*N) for preference scan — fine for typical vault inputs.
- **Items rejected by human**: none yet
- **Notes**: vault_entity is a heuristic feeder for vault-remember; correctness is downstream. No structural issues. vault_optimize.py (664 lines) reserved for a future cycle when context is fresher — it's the larger of the vault group and the right one to look at after PM's brainstorm crystallizes into actual tasks.

## Scan — 2026-05-24 16:40

- **Files scanned**: references/scripts/vault_check.py (full 393 lines; focus on `check_wikilinks` regex, frontmatter parser, validate exit semantics)
- **Findings**: none filed. Observations: (a) `_extract_wikilinks` at L62-63 strips pipe-aliases but not `#fragment` suffixes — a link like `[[note#section]]` would be checked as `note#section` against bare note_names and report broken, but a grep of `.squidsquad/vault/` finds zero fragment-style wikilinks today so the bug is dormant. (b) `validate()` at L327-340 prints orphans but doesn't add them to `all_issues` — likely intentional (orphans are advisory, output type "ORPHAN" vs "FAIL"). (c) third copy of the simplistic `_parse_frontmatter` parser (alongside vault_remember + soul_adaptation) — same multi-line-value blindness already documented in #10007's audit; adding a fourth file to that audit comment would be noise.
- **Items rejected by human**: none yet
- **Notes**: PM ran a vault sub-skill brainstorm 2h ago (commit `07670cb3`) — vault tooling is relevant context. Worth keeping vault_optimize.py / vault_entity.py / vault_remember.py in mind as a related group if PM's brainstorm produces follow-up tasks. dm reached cycle 1375 (R59 doc scans on SKILL.md sections 1-6) per recent commits; skill at cycle 1368, gap consistent with the per-role independent counters.

## Scan — 2026-05-24 16:09

- **Files scanned**: references/scripts/migrate_labels_6274.py (164 lines; one-shot dual-label migration for #6274.1)
- **Findings**: none filed. Real bug observed: `main()` at L160 unconditionally `return 0` regardless of `_add_label` failures — `updated` list only records successes, but the script's exit code never reflects partial failure (operator running this in CI would see exit 0 even with 3-of-10 label adds failing). Same exit-code-doesn't-reflect-failure family as #10006 (`cmd_stop` returning 1 on empty success). **Deliberately not filing**: per L16 docstring the script is scheduled for deletion in 6274.3 alongside `cleanup_labels_6274.py`; filing a fix for code about to be removed is wasted backlog. Also: hardcoded `--limit 500` at L58 same as verify_dual_label_6274 (safe at SquidSquad's volume).
- **Items rejected by human**: none yet
- **Notes**: deletion-imminent code is a legitimate not-file category alongside the existing edge-case-and-low-impact category. Add it as a triage rule: **deletion-imminent + non-blocking = scan-history note only**. If 6274.3 ships and the script survives (scope creep), revisit then.

## Scan — 2026-05-24 15:40

- **Files scanned**: references/scripts/verify_dual_label_6274.py (141 lines; one-shot G2→3 gate verification for #6274 dual-labeling)
- **Findings**: none filed. `_list_recent_issues` uses hardcoded `--limit 500` (L58) which would silently truncate at high volume — but SquidSquad creates ~10 issues/week so a 7-day window stays well under the cap. `_run` returncode check at L61 + JSON parse fallback at L69 is solid. Minor: an issue carrying all 4 dual labels would be counted twice in `checked` (loop iterates PAIRS) — not a correctness bug but a cosmetic count inflation. Script is purposefully tied to the 6274 sub-phase lifecycle (one-shot gate, retires when 6274.3 ships).
- **Items rejected by human**: none yet
- **Notes**: paired migrate_labels_6274.py skipped for context economy — both scripts share the same lifecycle and 6274.1 was already scanned during #9964 review. Continuing single-file conservation cycles.

## Scan — 2026-05-24 15:10

- **Files scanned**: references/scripts/tc_coverage.py (full 313 lines; focus on TC parsing regexes + result extraction + coverage gate exit-code semantics)
- **Findings**: none filed. `_RESULT_RE` at L45-47 with `\b` word boundaries could in principle false-positive on prose like "does not pass" appearing in QA-RESULTS body (only when neither valid result tokens nor invalid-result regex match first); requires QA agent to write narrative commentary inside a TC's body block instead of structured `**Result**: ...` or table format — typical QA-RESULTS layouts don't trigger it. The #2469 fix that excluded the heading line from `search_block` handles the most common case (TC title containing "not-applicable"). Edge case, narrow trigger, not worth a ticket against the existing backlog.
- **Items rejected by human**: none yet
- **Notes**: `_discover_files` planning_dirs sorting at L127-129 correctly puts pm first (PM owns test plans). The QA-RESULTS revision picker at L146-153 sorts numerically by `-R<N>` suffix — solid. `coverage_pct:.0f` formatting at L229 rounds 99.4 to 99 and 99.5 to 100 (banker's edge case but only matters at non-100% which already fails the gate via missing TCs). `_TC_TABLE_RE` doesn't match markdown table separator rows since `TC` regex demands literal `TC`. Exit-code semantics 0/1/2 (pass/fail/blocked) are clean and documented. Stopped at one file this cycle — context climbing past 25% and we've covered enough breadth.

## Scan — 2026-05-24 14:40

- **Files scanned**: references/scripts/event_bus.py (189 lines) + references/scripts/event_catalog.py (256 lines)
- **Findings**: none filed. event_bus is clean — `_generate_id` width is 16-char post-#9415, `_resolve_squid_dir` honors `SQUIDSQUAD_DIR` env var per #9398, `emit()` is fire-and-forget with 500ms timeout (documented contract); same `urlopen-without-with` stylistic nit as event_bus_reader. event_catalog has a real documentation drift — `payload_fields` for cycle-start/cycle-end lists `cycle_number`, but `event_bus.emit()` puts `cycle_number` at the top-level of the event dict (L113), not in payload; cycle-end also emits an undocumented `summary` field (cycle_post.py L859). Drift is real but `payload_fields` has zero programmatic consumers (grep confirmed: only event_catalog.py itself references the key), so this is pure docs drift — not worth a ticket against the existing backlog.
- **Items rejected by human**: none yet
- **Notes**: continuing context-conservation rotation. Both files solid for steady-state observability. event_bus.py's docstring at L155 ("Tier 2: recognized... no error") matches the EMITTED/RECOGNIZED/unknown tier model; `is_valid` and `get_tier` are consistent. Worth noting for future: if a subscriber ever starts consuming `payload_fields` (e.g. a schema validator), the cycle-start/cycle-end entries will need fixing — file then with concrete proposed schema.

## Scan — 2026-05-24 14:10

- **Files scanned**: references/scripts/monitor_smoke_poller.py (37 lines) + references/scripts/event_bus_reader.py (94 lines)
- **Findings**: none. monitor_smoke_poller is a tight 37-line smoke utility — no validation on `int(sys.argv[1])` / `float(sys.argv[2])` but it's a smoke test invoked with known args. event_bus_reader is clean — 500ms timeout, silent empty-list on failure (documented contract), #9967 eviction handling has clear stderr breadcrumb. Single nit: L72 `urlopen` without `with` context manager (vs cycle_post.py which uses `with urlopen(...) as resp:`); response is short-lived so GC handles it, stylistic only.
- **Items rejected by human**: none yet
- **Notes**: deliberately picked two small files this cycle to conserve context (rising to 22%) and rotate scan coverage. No new vault writes — last cycle's `learning-scan-comment-vs-file-duplicate.md` is sufficient methodology capture.

## Scan — 2026-05-24 13:41

- **Files scanned**: references/scripts/repo_scan.py (full 409 lines; focus on `_check_python_deps` substring match + `_count_extensions` os.walk SKIP_DIRS coverage + `scan()` save path)
- **Findings**: none filed. `_check_python_deps` at L228-242 uses bare substring match (`if dep.lower() in text`) against pyproject.toml/requirements.txt — false-positive risk (e.g. `flask-cors` matches `flask`, `[project] name = "fastapi-app"` matches `fastapi`). Setup-time only (wizard.py invokes via `scan()`), no steady-state callers, low blast radius — not worth a fresh ticket against the backlog. Also: `save_path.write_text(output + "\n")` at L402 is technically non-atomic but `.squidsquad/.repo-scan.json` is written once per setup with no concurrent readers, so it's not in #10007's audit scope.
- **Vault writes**: 1 — `learning-scan-comment-vs-file-duplicate.md` (captures the cycle-1361 audit-vs-file methodology so future agents can find it; links to [[learning-strip-vs-wire-audit-findings]] for the orthogonal strip-vs-wire dimension).
- **Items rejected by human**: none yet
- **Notes**: SKIP_DIRS omits `.idea/`, `.vscode/`, `.parcel-cache/`, `.svelte-kit/` — minor. LANGUAGE_EXTENSIONS misses `.mjs`, `.cjs`, `.pyi`, `.pyx` — minor. `os.walk` dir-modify pattern at L192 is correct. Deliberate decision to bias the cycle toward vault capture (one learning note) over filing another low-impact issue, given the existing PM-triage backlog of 4 open scan findings.

## Scan — 2026-05-24 13:11

- **Files scanned**: references/scripts/soul_adaptation.py (full 299 lines) → triggered codebase-wide `.write_text(` grep across references/scripts/ to audit the #10007 non-atomic-write defect family
- **Findings**: no new issue filed — instead, posted an audit comment on #10007 listing 9 confirmed non-atomic call-sites across 6 files (vault_remember L55+L151, cycle.py L167, cycle_post.py L769+L584, soul_adaptation.py L147+L226, config.py L285, diagnostics.py L97) targeting concurrently-read state files (working-state.md, SOUL.md, role-adaptations.md, config.md, SKILL.md, diagnostic.jsonl). Strengthens the original recommendation: extract `shared_fs.atomic_write_text` and route all 9 sites through it in one consolidated PR rather than per-site fixes.
- **Items rejected by human**: none yet
- **Notes**: scanned soul_adaptation.py first because it's a fresh target with high-impact writers; finding the same L147+L226 pattern triggered the systemic-vs-local question — answered by the grep audit. Sites already using tmp+replace (correct): config.py:406, cycle.py:91, cycle_post.py:377, compose.py:1297/1348, event_poll.py:125, harness.py:430/809/1128/1149, run_comprehension_test.py:85, shared_fs.py:43/52, thin_launcher.py:127, add_role.py:149. The split inside config.py itself (L285 wrong, L406 right) is the smoking gun that the pattern is known but not consistently applied. Deliberate choice not to file a duplicate-feeling #10008 for soul_adaptation.py since a comprehensive audit comment on #10007 produces a more actionable fix than splitting it across multiple issues. start_team.py (137 lines) considered as a scan target but it's a thin delegate over squidsquad_cli — clean, no findings warranted.

## Scan — 2026-05-24 12:40

- **Files scanned**: references/scripts/vault_remember.py (full 418 lines; focus on `_write_working_state_field` + `_upsert_vault_writes` write paths, frontmatter parser robustness, path-traversal defenses)
- **Findings**: #10007 (medium — non-atomic working-state.md writes at L55 and L151 violate the agent-foundation \"atomic writes for concurrently-read files\" rule; statusline + ≥10 scripts read this file concurrently; cycle_post._write_task_log already has the correct tmp+replace pattern, vault_remember just doesn't apply it; same defect family as #9930/#9932)
- **Items rejected by human**: none yet
- **Notes**: `effective_confidence` path-traversal defense at L213-219 is solid (resolve-then-`is_relative_to(VAULT_DIR.resolve())`). YAML frontmatter parser at L237-240/L316-319 doesn't handle block-scalars or array-on-next-line `tags:\\n  - evergreen` form — would silently miss the evergreen exemption; but inspecting `.squidsquad/vault/galaxy/*.md` confirms current notes use inline `tags: [...]` so the substring check works in practice (didn't file). `is_quiet` defaults to \"quiet\" on read error (L110-112) — wastes a cycle but is non-destructive. `note_count` excludes only `.gitkeep` (L281) so any future README in vault/ would inflate count; cosmetic. `_upsert_vault_writes` is single-process intra-cycle so the read-modify-write race is theoretical for that script alone — but the cross-process statusline-reader is the real concurrency hazard.

## Scan — 2026-05-24 12:11

- **Files scanned**: references/scripts/squidsquad_cli.py (full 446 lines; focus on cross-platform `_spawn_harness` L307-390, aggregation exit codes in `cmd_start`/`cmd_stop`/`cmd_status`, `_harness_alive` strictness)
- **Findings**: #10006 (low — `cmd_stop` returns exit 1 when `results: []` because `bool([]) and all(...)` short-circuits to False; inconsistent with `cmd_status` which treats no-agents as success; teardown scripts chaining `squidsquad stop && next` see false failure when squad was already idle)
- **Items rejected by human**: none yet
- **Notes**: `_spawn_harness` already routes through `sys.platform` per #9903 (L315-320). `HarnessAPIError` documented at L90-97 for #4792 §5.7 aggregation. The Windows `cmd /c start squidsquad-harness python harness.py` fallback at L338-344 has an unquoted title that *might* be interpreted by cmd.exe's `start` as the command rather than the title — but the wt.exe path covers Win10+ defaults and the fallback is only exercised on stripped systems; not filing without a repro. `_harness_alive` strict-200 check (L62-69) could trigger duplicate-harness spawn if a live harness returns 5xx; theoretical, didn't file. `localhost` vs `127.0.0.1` inconsistency between this file and cycle_post's `_discover_harness_port`-shaped callers — cosmetic, didn't file. `_api_call`'s POST `req.data = b\"\"` posture is correct for the FastAPI harness.

## Scan — 2026-05-24 11:41

- **Files scanned**: references/scripts/diagnostics.py (full 247 lines; focus on `generate_report` L140-190 vs `_sanitize_config` L101-119 redaction asymmetry, plus `rotate()` atomic-write posture)
- **Findings**: #10005 (medium — `generate_report` ships diagnostic entries verbatim via `json.dumps(e)` while `_sanitize_config` redacts the same keyword set for config; `log_entry` accepts arbitrary `message` + `context` so entries can carry tokens/paths; `is_public_repo()` exists precisely because the report flow targets public trackers; same defect family as #8235 which fixed only the config path)
- **Items rejected by human**: none yet
- **Notes**: `rotate()` at L97 uses `LOG_FILE.write_text` (truncate-write) — violates the `Use atomic writes (...)` agent-foundation rule since other agents read this concurrently; worth a follow-up but lower urgency than the redaction leak. `log_entry` size-check-then-rotate at L60-64 is a TOCTOU race when two agents log near the cap; in practice diagnostic volume is low so the rotate-clobber risk is theoretical. `is_public_repo` defaults `isPrivate=True` (safe-private) on missing field — correct posture. The keyword redaction list at L113 now covers all the #8235 misses (url/clone/webhook/password present); no fresh keyword gaps observed.

## Scan — 2026-05-24 11:09

- **Files scanned**: references/scripts/cycle_post.py (full 885 lines; focus on `_do_version_bump` L565-613 push-result handling + `_do_commit_push` skill split-commit path L466-538)
- **Findings**: #10002 (medium — cycle_post._do_version_bump silent push failure leaks divergent state; same family as #9890/#9930/#9939; recommend capturing each git push returncode + gating shipped-since-bump reset on push success)
- **Items rejected by human**: none yet
- **Notes**: `_do_commit_push` skill split-commit branch handles "nothing to commit" vs real push failure cleanly (L474-491 — #5444 distinguishes them); `_check_disposable_files` warn-only is fine for the #4081 fnmatch path; `_query_harness_intent` / `_post_harness_restart` use 5s timeouts + safe-default None per #4966; `_sanitize_commit_msg` zero-width-space trick at L416-419 handles #4038 auto-close correctly; task-log retention at L385-398 has its own try/except for unlink failures — robust. `except (ImportError, Exception)` at L850 and L862 is redundant (Exception covers ImportError) but documented as best-effort cleanup.

## Scan — 2026-05-21 19:11

- **Files scanned**: references/scripts/reboot_agent.py, references/scripts/config.py
- **Findings**: #9882 (config.py: module docstring missing alias/sync-agents/list-agents subcommands — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-19 08:04

- **Files scanned**: references/scripts/event_poll.py, references/roles/{dev,dm,pm,qa}/includes-events.yml
- **Findings**: none (event_poll.py cursor/backoff/error paths are well-tested and consistent with l1-base.md ownership rules; all 4 event-mode manifests are symmetric with their polling-mode counterparts and reference existing sub-skills)
- **Items rejected by human**: n/a

## Scan — 2026-05-16 23:04

- **Files scanned**: references/scripts/cycle_post.py, references/scripts/thin_launcher.py, references/scripts/git_ops.py
- **Findings**: #8653 — task_begin fails on index with unresolved merge conflicts from pull

## Scan — 2026-05-16 19:15

- **Files scanned**: references/roles/dm/android/instructions.md, references/roles/dm/ios/instructions.md, references/roles/pm/android/instructions.md, references/roles/pm/ios/instructions.md, references/roles/qa/android/instructions.md
- **Findings**: none
- **Items rejected by human**: n/a

## Scan — 2026-05-16 19:10

- **Files scanned**: references/scripts/thin_launcher.py, references/scripts/triage.py, references/scripts/cycle_post.py
- **Findings**: none
- **Items rejected by human**: n/a

## Scan — 2026-05-16 10:33

- **Files scanned**: references/roles/dev/ios/instructions.md, references/roles/dev/android/instructions.md, references/roles/dev/fullstack/instructions.md
- **Findings**: #8576 (incorrect article and iOS capitalization in variant templates)
- **Items rejected by human**: none yet

## Scan — 2026-05-16 09:03

- **Files scanned**: references/scripts/run_comprehension_test.py, references/scripts/migrate_state_branch.py
- **Findings**: #8568 (run_comprehension_test.py: unused import tempfile), #8569 (run_comprehension_test.py: empty eval results treated as all-pass)
- **Items rejected by human**: none yet

## Scan — 2026-05-16 08:32

- **Files scanned**: references/scripts/capability_check.py, references/scripts/forge_adapter.py
- **Findings**: none
- **Items rejected by human**: n/a

## Scan — 2026-05-16 08:02

- **Files scanned**: references/scripts/soul_adaptation.py, references/scripts/shared_fs.py
- **Findings**: none
- **Items rejected by human**: n/a

## Scan — 2026-05-16 07:32

- **Files scanned**: references/scripts/repo_scan.py, references/scripts/comms_adapter.py
- **Findings**: none
- **Items rejected by human**: n/a

## Scan — 2026-05-16 06:33

- **Files scanned**: references/scripts/boot_remote.py, references/scripts/manifest.py
- **Findings**: #8561 (boot_remote.py: _parse_local_config regex rejects hyphenated role names)
- **Items rejected by human**: none yet

## Scan — 2026-05-16 05:34

- **Files scanned**: references/scripts/wizard.py
- **Findings**: #8547 (wizard.py: duplicate check=False kwarg crashes cmd_setup_yes — medium), #8548 (wizard.py: load_install_spec uncaught JSONDecodeError — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-16 04:03

- **Files scanned**: references/scripts/harness.py
- **Findings**: #8525 (harness.py: redundant import time as _time), #8526 (harness.py: type mismatch clone_root vs REPO_ROOT)
- **Items rejected by human**: none yet

## Scan — 2026-05-16 02:33

- **Files scanned**: references/scripts/vault_remember.py, references/scripts/compose.py, references/scripts/cycle.py
- **Findings**: #8483 (cycle.py: unused imports io and json), #8484 (cycle.py: set_counter missing upsert logic)
- **Items rejected by human**: none yet

## Scan — 2026-05-16 00:32

- **Files scanned**: references/scripts/scan_index.py, references/scripts/vault_optimize.py, references/scripts/event_validator.py
- **Findings**: #8435 (scan_index.py: acceptance_rate scoring always 0 for unreviewed files)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 22:52

- **Files scanned**: references/sub-skills/roles/dm/prohibitions.md, references/prompts/discussion-prep.md.j2, references/prompts/improvement-scan.md.j2, references/roles/LAYERS.md, references/roles/dev/android/instructions.md
- **Findings**: #8381 (LAYERS.md references deprecated reboot_agent.py instead of start_team.py)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 22:02

- **Files scanned**: references/scripts/health_check.py, references/scripts/state_bus.py
- **Findings**: #8350 (state_bus.py: unused import os)
- **Items rejected by human**: none

## Scan — 2026-05-15 21:03

- **Files scanned**: references/scripts/config.py, references/scripts/cycle_pre.py
- **Findings**: #8343 (cycle_pre.py: inconsistent boolean config parsing across functions)
- **Items rejected by human**: none

## Scan — 2026-05-15 20:03

- **Files scanned**: references/scripts/cycle_post.py, references/scripts/model_router.py
- **Findings**: #8336 (cycle_post.py: redundant import re inside two functions)
- **Items rejected by human**: none

## Scan — 2026-05-15 18:32

- **Files scanned**: references/scripts/triage.py, references/scripts/event_bus.py, tests/test_triage.py, tests/test_event_bus.py, tests/test_feat_2495_upgrade_rewrite.py
- **Findings**: #8307 (triage.py: dead code in find_qa_rejected own-comment check)
- **Items rejected by human**: none

## Scan — 2026-05-15 17:33

- **Files scanned**: references/scripts/tracker.py, references/scripts/git_ops.py, references/scripts/squidsquad_cli.py
- **Findings**: #8268 (tracker.py get_state returns OPEN for missing state — low), #8269 (squidsquad_cli.py unused import os — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 16:03

- **Files scanned**: references/scripts/start_team.py, references/scripts/thin_launcher.py, references/scripts/diagnostics.py
- **Findings**: #8234 (start_team.py bare except swallows all errors — low), #8235 (diagnostics.py missing redaction keywords — medium)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 14:33

- **Files scanned**: references/scripts/vault_check.py, references/scripts/vault_entity.py, references/scripts/tc_coverage.py
- **Findings**: #8200 (vault_check.py wikilink pipe-alias not stripped — low), #8201 (vault_entity.py unhandled --file read error — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 13:33

- **Files scanned**: references/scripts/event_bus.py, references/scripts/event_bus_reader.py, references/scripts/event_catalog.py
- **Findings**: #8193 (unused import sys in event_bus.py and event_bus_reader.py — low)
- **Items rejected by human**: none yet

## Scan — 2026-05-15 11:33

- **Files scanned**: references/scripts/compose.py, references/scripts/boot_remote.py, references/scripts/soul_adaptation.py
- **Findings**: #8159 (compose.py redundant imports in agent_compose — low), #8160 (boot_remote.py corrupt .claude-pid silent fallthrough — low)
- **Items rejected by human**: none yet


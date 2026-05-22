# Changelog

## [0.42.0] — 2026-05-22

### Added
- #9873 — Event-bus foundation (slice -A of the larger redesign): per-role delivery cursor in the harness, plus a dual-ack split between `ack-cursor` (consumer-side advance) and `ack-stop` (legacy stop-confirmed). Foundation for the remaining nudge-driven slices.

### Fixed
- #9687 — `cycle_post.py` remote-branch check now retries after a short sleep when the push→ls-remote race fires; auto-transitions no longer stall on that timing window.
- #9724 — Repaired 4 stale mocks in `test_run_comprehension*`; the comprehension test suite runs cleanly on `main` again.
- #9740 — Closed a per-event advance race in `event_poll.py` that lost an event when the cursor re-anchored mid-loop.
- #9741 — Events delivered via `GET /events/for/{role}` are now properly acked by agents; the back-pressure gap that left in-flight events un-acked is fixed.
- #9743 — `idle-cooldown-loop.md` now documents Monitor output buffering during indefinite waits, so the timing assumptions are explicit instead of implicit.
- #9813 — `event_bus.ack()` now actually runs the ack path instead of being a dead stub.
- #9882 — `config.py` module docstring now lists the `alias`, `sync-agents`, and `list-agents` CLI subcommands.
- #9890 — `git_ops.py` push sites can no longer wedge silently under `credential.helper=manager` (GCM); the new `_git_push` helper adds an explicit timeout and a token-helper override.
- #9898 — `event_poll.py` now emits the event **before** advancing the cursor, restoring at-least-once delivery (a crash between the two lines no longer drops the event). Bridges until #9873-B lands the full ack contract.

## [0.41.0] — 2026-05-21

### Added
- #9243 — Harness `/status` endpoint now exposes the running SquidSquad code version (semver + git SHA + branch + dirty-flag) so operators can confirm at a glance what version their squad is actually running.
- #8998 — Event-driven mode is now fully wired through `includes-events.yml` — event-mode and polling-mode templates compose from the same sub-skill bundle, picked at deploy time.

### Fixed
- #8979 — Completed the long-tail of #4792 lifecycle work: 60-second force-kill safety net (the harness can no longer be wedged indefinitely by an unresponsive agent), `/quit` fragment, context-pressure `/restart` routing, legacy shim, and upgrade path.
- #8999 — Event-mode integration tests now cover the §4.1/§4.5 critical paths end-to-end with a real Claude CQ run, locking the event-driven architecture against silent regressions.
- #9398 — Closed the remaining real-system gaps in #8999's E2E coverage; AC-1 M-1.3 runs against a live Claude binary, not a mock.
- #9562 — On Windows, the harness now sets `WindowsSelectorEventLoopPolicy` at startup, preventing the ProactorEventLoop connection-reset crash that wedged HTTP under load.
- #9574 — `run_comprehension_test.py` no longer silently exits with rc=0 when the inner agent forgets to invoke `Write` — long-context prompt-following failures are now visible.
- #9665 — Stabilized real-subprocess tests under sustained Windows load (deeper than the #9398 timeout fix) — eliminates flaky CI on real-binary suites.
- #9415 — Widened event-bus event IDs to 64-bit (16-char hex) on both random and content-hash paths; eliminates birthday-paradox collision risk past 65k events. One-time eviction-signal noise per agent during transition is expected and harmless.
- #9588 — Mode-specific instructions are now lazy-loaded at agent boot, cutting cold-start context cost for event-mode agents.
- #9688 — Orphan `claude.exe` processes spawned by the Agent tool are now reliably cleaned up on Windows; protected-set walks the `cmd.exe→claude.exe` parent chain and multi-clone `.claude-pid` discovery prevents false positives.
- #9725 — `thin_launcher.py` now registers its `/loop` prompt on spawn so freshly-booted agents pick up the loop cadence without manual intervention.
- #9742 — Boot harness-reachability check now retries with a hardened TOCTOU guard, and the Monitor tool exits cleanly if the harness goes down between the curl probe and `event_poll` start.
- #9744 — DM PR-merge-wait now re-checks issue labels on each wake and pre-checks status before waiting — operator redirects propagate within one cycle instead of stalling indefinitely.
- #9745 — Wake-mode resolution is now a single canonical `config.get_wake_mode` helper; all 3 Python callers delegate, eliminating the 4-file drift risk.
- #9746 — Regenerated stale `references/agent-instructions.md` (was missing #9588 bootstrap content); added a drift-detection test that asserts the file matches fresh compose output, catching future drift in CI.
- #9747 — Eliminated LLM-dependent `[ROLE]` placeholder from the dev polling fragment; status-bar writes now go through a deterministic env-reading helper, removing a silent-failure mode if context pressure truncated the bootstrap teaching.
- #9772 — `cycle_pre.py` now self-heals when the ship counter is silently clobbered by stale-base squash-merges; counter reconciles against `git log` so DM no longer has to detect the regression manually.
- #9837 — DM's queue now surfaces closed-but-pending-ship-labeled items (universal-shipper queries); the auto-close-on-PR-merge pattern can no longer hide ready-to-ship work from DM.

### Internal
- #9215 — Removed `/loop`-mode-specific language from L4 `shared-instructions.md`; cleared the last pre-flip blocker for event-driven mode being the default.

## [0.40.0] — 2026-05-18

### Added
- #7630 — Event-driven agent architecture (Phase 4 foundation): the harness owns cycle dispatch, and agents react to events via a shared event bus instead of polling on a fixed interval. The polling-mode 30-minute Ralph Loop remains available as a fallback.
- #8694 — When an agent transitions an issue, the harness automatically dispatches the next work item to the right agent — no manual /complete handshake required.
- #8695 — Agents emit a `bootup-complete` event so the harness only dispatches work to agents that are fully loaded, preventing missed events during startup.
- #8697 — Dual-mode CLAUDE.md composition: the same agent role template works in event-driven or polling mode, selected at deploy time.
- #8814 — Polling-mode behavior extracted into a reusable sub-skill fragment so event-mode and polling-mode templates stay in sync.
- #8915 — Event-mode L1 base sub-skills + `event_poll.py` so agents in event-driven mode read events from the bus instead of running `/loop`.
- #8701 — `cycle_pre.py` / `cycle_post.py` task-level refactor for event-driven mode, so the per-cycle mechanical layer works in both modes.
- #4792 — Harness owns the full agent lifecycle (start/stop/reboot) via an intent state machine; legacy sentinel files (`.stop`, `.stop-after-cycle`, etc.) are deprecated and removed.
- #8700 — Status line refactored for event-driven mode: queries the harness for live state and falls back to file when offline, so you always see fresh agent activity.
- #8704 — Harness exposes `/human/queue` endpoint surfacing human-assigned work to TUI/UI consumers — groundwork for the upcoming web dashboard.

### Fixed
- #8584 — `_tool_read` no longer loads the entire file into memory before checking its size; oversized files are read with a bounded `f.read()`.
- #8664 — Removed corrupted `.event-state.json` from main and added volatile runtime files (`.event-state.json`, `.backlog-cache`, `.booting`, `.claude-pid`, `scheduled_tasks.lock`) to `.gitignore` so they stop polluting commits.
- #8918 — `cycle_post.py` mode-gates `REQUIRED_FIELDS` and removes the legacy `_advance_event_cursor` path that survived event-mode migration.
- #8914 — Restored the thin-broadcast lock by stripping misplaced dispatch + gating logic from `harness.py`.
- #8879 — `thin_launcher.py`'s `_write_pid` failure no longer leaves the spawned `claude` process orphaned.
- #8689 — `harness` restart endpoint now immediately reboots idle agents instead of waiting for the next cycle.
- #8913 — Wizard subprocess calls now use a timeout so a hung subprocess can no longer wedge setup.
- #8949 — Locked the `_emit_event NameError` regression behind a test so it can never silently come back.

### Internal
- #8703 — Process directive to DM persisted in scan state: pause `/loop` architecture doc updates during the Phase 5 in-flight bundle (lifted after #8697 shipped).
- #8891 — Extracted `is_process_alive` into a shared `process_utils` module for harness/health-check/reboot/launcher reuse.

## [0.39.0] — 2026-05-16

### Fixed
- #8547 — Setup wizard no longer crashes from a duplicate keyword argument when running non-interactive setup
- #8435 — Improvement scanner now correctly scores unreviewed files instead of always rating them zero
- #8235 — Diagnostics reports now redact URLs, clone paths, webhooks, and passwords — no more accidental credential leaks in reports
- #8200 — Vault wikilinks with pipe-alias syntax (e.g. `[[note|display]]`) now resolve correctly
- #8201 — Vault entity classifier no longer crashes when given an unreadable file
- #8160 — Agents no longer spuriously reboot when a PID file is corrupt — reads the file safely instead of crashing
- #8116 — Health check interval now reads the correct config field instead of matching unrelated lines
- #8115 — Cycle startup no longer crashes on malformed ship-threshold config — handles gracefully
- #8082 — Scan index now correctly tracks decision counts for newly added files
- #8081 — QA rejection timestamp comparison now uses proper date parsing instead of fragile string comparison
- #7890 — Code review model config field now exists by default — code review no longer silently fails on fresh installs
- #7879 — Upgrade commits no longer accidentally stage unrelated user files from .claude/
- #7878 — Event bus architecture docs now reference correct event names and include all event types
- #7794 — PM instructions no longer reference deprecated tracker file concepts
- #7793 — Ship counter is now owned exclusively by QA — eliminates double-counting between PM and QA
- #8477 — PM agent now correctly begins its Ralph Loop when started by the harness
- #8401 — Test teardown no longer falsely reports failure for nonexistent deploy directories
- #8400 — Test diagnostics no longer leak real data through mocked log file paths

### Added
- #8533 — git_ops.py branch name resolution now has full test coverage
- #8453 — cycle_post.py state-branch commit paths now have full test coverage
- #8452 — Version bump pipeline (config, SKILL.md rewrite, commit, tag, push, reset) now fully tested
- #8393 — OpenAI adapter tool-use loop now has behavioral tests
- #8392 — Event reactions config writer now has full test coverage
- #7955 — cycle_post.py tracker comments and working state updates now have full test coverage
- #7948 — Wizard code review model defaults now verified by tests
- #7947 — Wizard interval validation now has full test coverage (20 parametrized tests)

### Removed
- #8193 — Removed unused sys imports from event bus modules
- #8159 — Removed redundant subprocess/json imports from compose.py

## [0.38.0] — 2026-05-12

### Added
- #6581 — Setup wizard now uses preset-driven agent selection — pick a team shape and the wizard handles the rest

### Fixed
- #7491 — Feature branches no longer accidentally modify config.md — eliminates repeated QA rejections from collateral damage
- #7441 — Harness state file no longer has a write-after-unlock race condition — concurrent agent operations are safer
- #7285 — Agent sync no longer crashes with a NameError when DM is present — config.py works correctly with the fixed team architecture
- #7286 — macOS agent spawning now handles repo paths with special characters (quotes, backslashes) without silent failure
- #7589 — State bus now properly reports failed git commits instead of silently continuing
- #7627 — State branch migration now returns a failure exit code when all migrations fail — CI catches real problems
- #7624 — Vault knowledge decay scan no longer aborts entirely when a single note file is unreadable
- #7622 — Test coverage checker no longer crashes on unreadable files — gracefully skips and continues
- #7619 — CLI error messages now include the actual error details instead of a generic "unreachable" message
- #7618 — Vault optimizer lock acquisition no longer has a time-of-check/time-of-use race condition
- #7610 — Cycle counter increments no longer produce duplicate output from a side effect in the getter
- #7611 — Health check now reads the correct PID file when checking agent liveness
- #7518 — Diagnostics config redaction now works on all config line formats, not just markdown bold lines
- #7519 — Diagnostics `--last` flag no longer crashes when given a non-integer argument
- #7440 — Event cursor advancement in cycle_post now actually updates the cursor instead of silently no-op'ing
- #7191 — Agent instructions now correctly scope file-copy operations to non-composed files only — prevents bypassing compose.py
- #7192 — DM soul directives now use the correct qualified path for BRIEFING.md
- #7615 — Vault entity classifier no longer defaults all unknown entities to "person" — uses appropriate fallback categories
- #7614 — Scan index no longer opens and closes its database redundantly when suggesting targets
- #7590 — Manifest loader no longer has a redundant yaml import or a bare except that swallows errors
- #7625 — Removed unreachable dead code in forgejo_setup.py
- #7628 — Removed dead with-block in test_per_agent_workdirs.py health check test
- #7098 — soul_adaptation.py CLI entry point now has full test coverage (6 branches)
- #6983 — forgejo_setup.py create_repo() now has full test coverage (4 branches)
- #6984 — forgejo_setup.py deploy() now has full test coverage (5 branches)
- #7085 — Test runner now discovers all 43 previously missing test modules
- #7086 — Manifest file inventory no longer lists deleted legacy sub-skills
- #7063 — Removed redundant import in compose.py code block extraction
- #7062 — Removed dead variable in compose.py include resolution
- #6977 — Removed redundant shutil import in wizard.py
- #6976 — Setup wizard no longer hardcodes stale version 0.25.0 in default spec
- #6849 — Removed shadowed regex import in tracker.py
- #6848 — Task creation now works correctly with the Forgejo forge adapter
- #6820 — Harness lifecycle endpoints now accept and persist the intent field
- #6819 — Comprehension test runner no longer crashes on subprocess timeout — handles gracefully
- #6818 — Secret reader now correctly distinguishes between empty secrets and missing secrets
- #6805 — Removed stale one-time deploy script from a previous migration

## [0.37.0] — 2026-05-10

### Added
- #6260 — DM delivery tasks now ship directly without QA verification — delivery-only work (docs, CHANGELOG, version bumps) skips the test step for faster releases

### Fixed
- #6497 — Reboot agent tests are now included in the test runner — previously excluded and silently failing
- #6514 — Vault knowledge notes no longer get corrupted when confidence decay rewrites are applied
- #6526 — Branch creation now uses the correct default pattern (`task/`) instead of a stale role-based pattern
- #6573 — Post-architecture cleanup: stale references to removed roles and setup wizard gaps resolved
- #6597 — Agent compose now correctly writes per-clone paths instead of `.` for all agents — isolated working directories work again
- #6598 — Removed stale tests that verified behavior from a removed shared-filesystem fallback
- #6599 — Test suite no longer fails on Windows due to grep subprocess usage — uses Python-native search
- #6629 — Pipeline sentinel no longer runs stuck-task detection when branch workflow is disabled
- #6630 — Pipeline sentinel now uses tracker.py commands instead of error-prone prose instructions
- #6683 — Test docstring no longer falsely claims the role-specific sub-skills directory was retired
- #6733 — Forgejo adapter no longer crashes on HTTP 204 No Content responses from DELETE operations
- #6746 — Dev agent code review now correctly captures file diffs after staging — no more empty reviews
- #6747 — Bug fix path now includes self-verification and external review steps — same quality gate as features
- #6759 — Test file no longer fails with ImportError from an unused `yaml` import
- #6760 — Version bump now uses the git_ops.py abstraction for tag/push — consistent with all other git operations
- #6774 — DM now correctly triggers version bumps when the ship counter exceeds threshold
- #6786 — Vault remember tests no longer have shadowed test classes that silently skip assertions
- #6799 — Resolved merge conflict markers in compose.py that broke template composition

## [0.36.0] — 2026-05-09

### Added
- #6126 — PR merging and template recomposition are now handled by the harness — agents request merges via API, and the harness automatically recomposes and reboots only affected agents when templates change
- #6261 — PM, QA, and DM are now always present in every team — no more optional infrastructure roles. Worker agents (dev, designer) are the flexible part of the team

### Fixed
- #6275 — Agent templates no longer reference a stale "date command" for timestamps — all roles now consistently use cycle.py
- #6287 — test_compose.py is now included in the test runner — 4 previously silent tests are active
- #6304 — Model router timeout path now has test coverage — exit code 3 is properly asserted
- #6316 — CLI installer no longer passes unsanitized repo paths to shell commands
- #6317 — Removed dead code in CLI installer that constructed a variable but never used it
- #6406 — Removed dead sentinel-based restart code from reboot_agent.py — the harness API handles restarts
- #6478 — test_manifest.py cross-check test now actually asserts the result instead of silently passing
- #6479 — manifest.md inventory tree updated to match current sub-skill file names

## [0.35.0] — 2026-05-09

### Fixed
- #6222 — Auto-merge no longer closes issues before delivery is complete, keeping shipped counters and labels accurate
- #6254 — Removed a false-confidence test that always passed regardless of actual behavior
- #6262 — Pipeline no longer picks up already-closed items as pending work

## [0.34.0] — 2026-05-08

### Added
- #5932 — Dev agents now get automated code review before QA, catching design-level issues earlier and routing them back to planning automatically
- #5868 — Agents now subscribe to specific event types via compose-time configuration — no manual event wiring needed
- #6055 — PM, QA, and DM are now prevented from overstepping their roles, keeping the pipeline clean and predictable
- #6057 — Tasks with design-level issues found during code review can now be sent back to planning instead of just failing QA
- #6007 — QA findings are now automatically routed to the responsible agent based on role, not just filed generically
- #6125 — All agent roles (PM, QA, DM) can now pick up and execute approved tasks — no more tasks sitting in the queue ignored
- #6086 — Agents now include short descriptions when referencing issue or PR numbers, making discussions readable without opening every link
- #6085 — Comprehensive event bus documentation with three-tier event model, role-based filtering diagrams, cascade protection, and port discovery

### Fixed
- #6000 — Harness now responds to Ctrl+C for graceful shutdown — one press finishes the current cycle, three force-exits
- #6043 — Agent reboots no longer crash on Windows when clone paths are strings instead of Path objects
- #6138 — Duplicate function definition in cycle_pre.py removed — no more silent shadowing

## [0.33.0] — 2026-05-06

### Added
- #4709 — Agents now emit coordination signals (status changes, PR merges) to a shared event bus — the foundation for real-time awareness
- #5622 — Your agents now coordinate in real-time — when QA verifies a fix or a PR is merged, other agents react within seconds instead of waiting for the next 30-minute cycle
- #5856 — Tracker status transitions are now broadcast as real-time events, enabling faster cross-agent coordination
- #5888 — New `/squidsquad-compose` command for managing agent template composition without manual script calls
- #5557 — Agents are now prevented from accidentally overwriting their composed instruction files — compose.py guards against direct edits
- #3969 — DM agent now proactively scans user-facing docs during quiet cycles, fixing staleness, version drift, and dead links

### Fixed
- #5915 — Harness no longer crashes on Windows when auto-starting agents (WindowsPath not JSON serializable)
- #5782 — Event bus no longer crashes when processing events from unknown agent roles
- #5774 — Installer manifest (start.sh/start.ps1) now lists the correct files
- #5745, #5712 — SKILL.md documentation updated to remove references to eliminated boot scripts
- #5916 — 12 stale tests in boot_remote.py restored after sentinel check migration

## [0.32.0] — 2026-05-04

### Added
- #4966 — Agent lifecycle is now managed by a single harness process — start, stop, restart, and crash recovery all happen through one REST API instead of per-agent wrapper scripts
- #5569 — Improvement scans now capture up to 3 learnings per scan to the shared vault, building institutional knowledge automatically
- #5570 — Agents now have situational awareness — they consult institutional knowledge before acting, not just after
- #5571 — PM research phase now always checks the shared vault for prior decisions and patterns before investigating
- #5572 — Dev and QA agents now consult vault knowledge before starting work on tasks
- #5573 — PM agent now uses extended thinking for deeper reasoning during planning and research

### Fixed
- #4609 — Config merge conflicts in shipped counter no longer block version bumps
- #4666 — Config version field no longer reverts after version bumps
- #4745 — Merge conflicts in config.md shared counters resolved cleanly
- #4746 — diagnostics.py now has test coverage for report generation and repo detection
- #4747 — Harness API endpoints now have test coverage
- #4765 — Agent templates now only include project instructions relevant to their role, not all roles
- #4803 — QA now checks all agent roles for pending-test items, not just skill
- #4829 — Git stash conflicts from volatile files eliminated with proper .gitignore patterns
- #4830 — Improvement scanning now triggers every quiet cycle for faster feedback
- #4837 — Dev agent now properly pushes feature branches and creates PRs
- #4876 — Multi-clone test suite no longer fails on missing designer working-state
- #4877 — Stale test for excluded PM role updated to match current behavior
- #4878 — CLI tool (squidsquad_cli.py) now has test coverage
- #4879 — Config parser (config.py) test coverage improved
- #4918 — Template composition no longer uses deprecated mktemp — race condition eliminated
- #4919 — Vault write counter reset no longer silently fails when field is absent
- #4942 — Branch checkout now creates missing branches instead of erroring
- #4949 — Agent lifecycle intent managed by harness API, not sentinel files
- #4967 — PM task intake now always includes PRD with diagrams and sequences
- #4979 — PM creates draft PR with PRD after planning, before approval
- #4991 — PR lifecycle flow fixed — draft-to-ready timing and PM fallback corrected
- #5013 — QA now fetches before checking remote refs — no more verifying the wrong branch
- #5040 — PM and dev now share one branch per task for holistic PR review
- #5046 — Model router now distinguishes API timeout from empty output
- #5125 — Model router YAML install block deduplicated and error handling added
- #5126 — Version bump no longer commits without checking for staged changes
- #5136 — Config version field no longer regresses on PR merges
- #5208 — Agents now verify they're on the correct branch before starting work
- #5234 — PM no longer attempts to rebase dev agent branches
- #5344 — Dead wrapper code removed from reboot script post-harness migration
- #5366 — Config test fixture updated to cover all current fields
- #5378 — Pre-cycle git pull no longer reports normal states as errors
- #5385 — Diagnostics log rotation now happens before write, preventing data loss
- #5423 — Harness 'stopped' intent state now uses proper constant instead of bare string
- #5429 — Health check no longer falsely reports agents as stalled when harness heartbeats stop but PIDs are alive
- #5435 — Test runner no longer silently skips the entire static test suite
- #5436 — CLI package.json version now stays in sync with config.md
- #5444 — Branch workflow reliability improved — push timing, contamination, and silent failures fixed
- #5445 — Conflict resolution now uses merge instead of rebase + force-push
- #5469 — Git merge strategies and .gitignore patterns eliminate state file merge conflicts
- #5526 — Remote branch verification no longer fails on wildcard pattern substring matches
- #5533 — SKILL.md documentation updated to reflect merge-based conflict resolution
- #5534 — Shipped counter no longer lost during merge conflict resolution
- #5556 — QA verification instructions updated to reflect merge-based conflict resolution

## [0.31.0] — 2026-05-01

### Added
- #4179 — Dev agent now uses divide-and-conquer instinct for complex tasks with sub-agent delegation
- #4533 — Dev agents now perform mandatory self-verification reflection before marking work as pending-test
- #4534 — PM acceptance criteria now consider project workflows, philosophy, and regression prevention
- #4541 — Agent composition is now LLM-driven — reads layer stack and writes coherent output instead of deterministic templating

### Changed
- #4449 — PM and DM now verify distribution packaging (npm + tarball + installer-files.txt) for project instructions
- #4459 — Shared project instructions moved from references/ to .squidsquad/project/ for project-local access
- #4531 — L4 project content relocated from distributed references/ to project-local .squidsquad/

### Fixed
- #4564 — Fixed duplicate entry in installer-files.txt
- #4608 — Fixed WinError 206 on Windows when composing agent instructions (filename too long)
- #4609 — Resolved merge conflict in config.md shipped counter
- #4666 — Fixed config.md version revert after v0.30.0 bump

## [0.30.0] — 2026-05-01

### Added
- #4455 — PM agent now has project-specific instructions (24 instructions + 15 SOUL items) for consistent behavior across sessions
- #4456 — Dev/Skill agent now has project-specific instructions (16 instructions + 11 SOUL items) for consistent behavior across sessions
- #4457 — QA agent now has project-specific instructions (16 instructions + 8 SOUL items) for consistent behavior across sessions
- #4458 — DM agent now has project-specific instructions (12 instructions + 7 SOUL items) for consistent behavior across sessions
- #4459 — Shared project instructions for all agents (27 instructions + 14 SOUL items) — agents now carry project context automatically

### Fixed
- #4123 — wizard.py now uses the correct key for Research Model in config generation
- #4124 — repo_scan.py FastAPI detection unreachable dead code removed
- #4125 — cycle_post.py version bump no longer duplicates CHANGELOG headers when DM also writes CHANGELOG
- #4200 — forgejo_setup.py no longer leaks credentials in create_token error messages
- #4201 — compose.py capability resolution block deduplicated between _resolve_includes functions
- #4364 — Removed stale PR merge transition test that expected obsolete tracker.py call
- #4365 — Stale deepseek model test updated to match current provider list
- #4435 — Fixed 4 test_wizard.py SOUL seeding tests
- #4436 — Fixed 3 test_roles.py entry file tests after CLAUDE.md → instructions.md rename
- #4518 — Fixed recurring auto-close bug — commit message sanitization now covers all transition paths, preventing GitHub from closing issues on non-shipped transitions

## [0.29.0] — 2026-04-29

### Fixed
- #3955 — Sub-skill templates updated to reflect the new agent lifecycle model — self-restart, agent-lifecycle, and boot-remote-agents no longer reference obsolete reboot flow
- #4038 — tracker.py no longer auto-closes issues on pending-test transition — only shipped transitions close issues
- #4050 — shared_fs.py `read_secret_or_env` now uses None check instead of falsy check, preventing empty string secrets from falling through
- #4051 — triage.py `find_qa_rejected` no longer aborts the entire scan when a single-issue `gh` call fails
- #4052 — Added 15 unit tests for run_comprehension_test.py, covering all 8 functions
- #4081 — Disposable scripts and debug logs are now gitignored to prevent accidental commits to feature branches
- #4092 — config.py `set_field` no longer silently fails when the target section text is empty
- #4093 — add_role.py `_acquire_lock` now cleans up stale lock files on write failure
- #4094 — Fixed 3 chronic test failures (orphan sub-skill reference, PR merge test, stale deepseek model) — 1126/1126 clean green

## [0.28.0] — 2026-04-28

### Added
- #2183 — Simplified agent lifecycle with singleton wrapper, safe restart, and PM/DM control — agents never get killed mid-work
- #2495 — Upgrade instructions fully rewritten — you can now run `/squidsquad-upgrade` with the correct compose.py-based flow, config v1→v2 patching, and automatic SOUL.md/vault preservation
- #3416 — Communication abstraction layer — agents can send messages, create threads, and share files through any supported platform (Telegram, Slack, Discord) without knowing the underlying service
- #3417 — Communication sub-skills (chat-etiquette, mention-protocol, consensus-protocol) for consistent cross-platform agent messaging
- #3664 — Iterations and diagnostics now live on the state branch — no more cross-agent merge conflicts in your working tree
- #3735 — Comprehension tests now skip when spec files are unchanged, saving expensive Claude CLI calls during routine cycles
- #3807 — Reboot flow redesigned — agents finish their current cycle before restarting, PM monitors but DM executes reboots

### Fixed
- #2195 — Agents no longer commit directly to main when Branch Workflow is enabled
- #2272 — PM now reads comments on active/approved tasks each cycle instead of missing updates
- #2343 — Removed unused imports in cycle_pre.py and cycle_post.py
- #2344 — tracker.py work_queue() now has unit tests
- #3302 — Fixed `add_role.py` using undocumented `subprocess.os.getpid()` attribute
- #3360 — Skill agent now properly pushes feature branches instead of claiming fixes without pushing
- #3711 — Fixed vault_remember.py path check bypass vulnerability
- #3712 — Fixed state_bus.py writing README.md to wrong path during orphan branch init
- #3747 — GitHub auto-close no longer bypasses tracker.py ship transitions — DM correctly detects closed pending-ship items
- #3800 — Fixed UnicodeEncodeError on Windows cp1252 console during PR merge ship transitions
- #3813 — Removed dead `_check_template_changed` stub that permanently returned False
- #3814 — Fixed model_router.py bare 'route' subcommand silently hardcoding task_type to 'research'
- #3848 — Fixed vault_check.py validate() silently ignoring orphans in pass/fail decision
- #3849 — Extracted `_collect_all_roles()` helper to DRY up duplicated logic in compose.py

## [0.27.0] — 2026-04-26

### Added
- #3100 — Local config is now mandatory — the global `~/.squidsquad/clones/` fallback has been removed for cleaner, per-project isolation
- #3101 — Agent startup now shows a colorful ANSI art logo matching the README octopus, with automatic monochrome fallback for terminals without color support
- #3107 — PM now re-runs research when discussion heavily changes the original scope, so plans reflect actual decisions instead of stale assumptions
- #3124 — PM improvement scans now focus on workflow gaps, stale instructions, and process contradictions instead of source code
- #3139 — Your squad now detects patterns across agents and proposes shared team principles ("postures") — you review and approve before they take effect
- #3296 — Agents now check out the correct PR branch before verifying or shipping, preventing stale-code false negatives

### Fixed
- #3027 — PM now fixes bugs in its own domain immediately instead of deferring to other agents
- #3078 — `reboot_agent.py --all` now reads configured agents instead of hardcoding `[pm, skill]`
- #3079 — `cycle_pre.py` no longer breaks on paths containing spaces
- #3290 — State branch initialization no longer leaves your working tree in a broken state if interrupted

## [0.26.0] — 2026-04-25

### Added

- #592 — Architecture diagram in SKILL.md now uses Mermaid for clarity and maintainability
- #2487 — Cycle runner sub-skill wired into all agent templates — consistent mechanical/creative separation across roles
- #2493 — Setup wizard now creates per-agent working directories for multi-agent execution
- #2496 — Unified agent lifecycle — single wrapper handles all start/restart/reboot paths
- #2575 — All agent roles now default to Sonnet for subagent spawns, reducing cost without sacrificing quality
- #2724 — Agent boot detection moved to cycle_pre.py; new `start-squad` script for one-command team launch

### Fixed

- #1772 — npm publish now runs during version bumps — packages/cli stays in sync with SquidSquad version
- #2469 — tc_coverage.py regex no longer matches heading text as test results
- #2494 — PM cycle input now includes approved items, recent human comments, and human-blocked items
- #2537 — compose.py no longer double-wraps sub-skill markers in deployed CLAUDE.md
- #2538 — Boot agent now has working-state.md — resolves test_dev_agent_has_working_state failure
- #2554 — Orphaned boot agent removed from config — no longer causes test failures
- #2659 — Removed dead _get_context_pressure function from cycle_pre.py
- #2671 — git_ops.py _get_working_branch no longer imports nonexistent config.get
- #2677 — vault_optimize prune now refreshes notes dict after git_mv — fixes OSError on self-linking notes
- #2693 — LEGAL_TRANSITIONS now uses correct label status:pending-human-review
- #2694 — start-role.ps1 singleton PID check moved before pre-flight — eliminates race condition
- #2700 — DM now runs `npm whoami` before declaring npm publish blocked on human auth
- #2701 — Fixed duplicate dependencies key and bin path in packages/cli/package.json
- #2713 — cycle_pre.py now preserves agent health data when health_check.py exits non-zero
- #2750 — boot_remote.py now uses project-local clone paths instead of global ~/.squidsquad/clones/

---

## [0.25.0] — 2026-04-23

### Added

- #13 — **Setup flow improvements** — wizard auto-detects your project context (test commands, tech stack), saves choices to `.install-spec.json` for repeatable upgrades, and supports non-interactive setup via `setup-yes` command
- #361 — **Project-adaptive role souls** — setup wizard generates a "Project Adaptation" section in each agent's SOUL.md based on your project description, so agents understand your specific domain. PM enriches souls further at runtime via soul-shepherd sub-skill
- #2006 — Setup wizard now asks about PR Flow (human review gate vs direct commits) and shows a "What's Next" summary with boot commands after setup
- #2070 — **Cycle runner** — opt-in transport layer that separates mechanical git/tracker ops from agent creative work. Agents call `cycle_pre.py` / `cycle_post.py` scripts, freeing context for reasoning
- #2183 — **Simplified agent lifecycle** — singleton wrapper (PID lock), safe restart (never kills mid-work), heartbeat health detection, PM/DM reboot control via `reboot_agent.py`. Deleted watchdog.py. Net ~800 lines removed

### Fixed

- #2175 — QA and PM souls now include branch workflow governance: QA converts draft PRs to ready, PM merges verified PRs immediately
- #2181 — DM delivery now enables feature flags on the shipping project after QA passes
- #2195 — All agents now create feature branches for issue-linked work when Branch Workflow is enabled
- #2272 — Agents now read latest comments on active tasks each cycle via cycle_pre.py enrichment
- #2343 — Removed unused imports from cycle_pre.py and cycle_post.py

---

## [0.24.0] — 2026-04-22

### Added

- #1449 — **Comprehension test pipeline** — deterministic agent-based testing for LLM instructions, so template changes are verified by a fresh agent before shipping
- #1869 — **3-branch architecture** — state bus runs on a dedicated branch, keeping your working branch clean and main untouched

### Fixed

- #1500 — Forgejo PR creation now respects the draft parameter
- #1501 — Forgejo remove_labels no longer silently swallows failures
- #1980 — Version bump now updates package.json and runs npm publish automatically
- #2007 — Boot scripts now set SQUIDSQUAD_ROLE so agents start with the correct identity
- #2008 — Setup generates a valid statusLine object in settings.json (was writing a string)
- #2009 — Setup wizard now generates boot scripts from templates instead of inline stubs
- #2035 — tracker.py feedback check now handles malformed JSON gracefully
- #2046 — state_bus.py now validates paths to prevent directory traversal
- #2058 — compose.py deploy/boot now handles file write errors
- #2064 — git_ops.py commit-code now returns to main correctly when unstaged changes exist
- #2086 — wizard.py scaffold_install now reports file/JSON errors instead of silently failing
- #2097 — config.py set_field now handles write errors
- #2109 — vault_optimize.py add_question now catches OSError specifically instead of swallowing all exceptions
- #2110 — Shipped transition now blocks if your feature branch has unmerged commits (prevents stranded code)

---

## [0.23.0] — 2026-04-19

### Fixed

- #473 — Dev agent SOUL.md now requires mandatory test coverage for all new code
- #474 — PM and QA verification now checks for test coverage, not just acceptance criteria
- #1396 — DM delivery enforces PR merge before shipping (prevents stranded code on branches)
- #1427 — Model router setup now guides you through API key storage and validates your connection
- #1494 — PR merge now works with Forgejo backend (was hardcoded to GitHub CLI)
- #1495 — Added error-handling tests for Forgejo adapter (HTTP errors, timeouts, malformed responses)
- #1696 — PRs are now automatically converted from draft to ready when items reach pending-ship
- #1708 — Added comprehensive unit tests for watchdog.py (30 tests, zero coverage → full coverage)
- #1709 — Added comprehensive unit tests for tracker.py (19 tests, zero coverage → full coverage)
- #1726 — Added regression test for Forgejo container-skip path

---

## [0.22.0] — 2026-04-18

### Added

- #1426 — **Shared filesystem** — API keys and cross-clone config now live in `~/.squidsquad/` with restricted file permissions. No more environment variable pollution — secrets are read automatically by the model router and providers

### Fixed

- #1395 — Research phase now consults the shared vault for existing decisions, patterns, and human preferences before investigating
- #1397 — PRs now start as drafts and convert to ready only after QA passes, preventing premature merges
- #1398 — Context pressure values now come from real statusline data instead of estimates
- #1399 — PRs now auto-close linked GitHub Issues on merge via "Closes #N" in PR body
- #1405 — DM delivery now verifies PR is merged before marking Shipped
- #1428 — QA verification now requires deterministic pytest tests before marking items as verified

---

## [0.21.0] — 2026-04-18

### Added

- #1074 — **Auto-merge PRs** — when QA verifies a task, PM automatically squash-merges the PR so you don't have to. Bug fixes and `merge:manual`-tagged items still require your review
- #1357 — **Pipeline self-healing** — PM's pipeline sentinel now detects 6 types of stuck tasks (orphaned PRs, shipped-without-merge, stalled approvals, dead-agent work) with two-tier response: unstick immediately, then auto-file a root-cause bug for permanent fix

### Fixed

- #1230 — Removed unused import in health_check.py
- #1299 — Fixed boot script session names dropping agent role on Windows (cmd /c quote handling)
- #1301 — Fixed stale agent detection: PID is now the sole liveness check — dead agents are reliably detected and rebooted regardless of .health file state
- #1345 — Fixed self-restart on Windows: boot wrapper watcher now uses absolute paths so .restart sentinel is reliably detected

---

## [0.20.0] — 2026-04-17

### Fixed

- #1078 — Added 31 unit tests for compose.py, covering template composition, placeholder substitution, deployment, and config reading
- #1079 — Added 24 unit tests for boot_remote.py, covering lock management, OS detection, boot script discovery, health polling, and spawn routing

---

## [0.19.0] — 2026-04-17

### Added

- #922 — **SQLite-based scan index** — improvement scanning now uses a local SQLite database to track coverage gaps, git churn, and finding acceptance rates, picking higher-value scan targets each cycle instead of scanning at random
- #942 — **Agent health files** — boot scripts write `.health` status files so PM detects agent state from files, not unreliable timestamp heuristics

### Fixed

- #1022 — Fixed health_check.py crashing on Windows cp1252 terminals due to Unicode emoji in table output
- #960 — Feature branch commits no longer include working-state and iteration files that don't belong in PRs
- #940 — Agents no longer spawn repeatedly due to false-positive staleness detection from mtime checks

---

## [0.18.0] — 2026-04-14

### Added

- #347 — **PM/QA role separation** — PM no longer assumes QA duties. QA runs as an independent agent with its own verification cycle. PM falls back to combined mode when QA is absent.
- #462 — **Adaptive setup questions** — the setup wizard now asks 3 context questions (1 fixed + 2 inferred from your answers) to tailor each agent's personality to your project domain.
- #897 — **Designer agent cleanup** — removed phantom designer config entries and added `.stop` sentinel for clean agent lifecycle management.

### Fixed

- #894 — health_check.py now returns exit 1 when .local-config is missing instead of silently reporting all-healthy
- #893 — Fixed tracker.py unread feedback check failing on non-canonical role names
- #590 — Dev agent planning artifact directory mismatch (pm/planning/ as primary location)
- #887, #895, #896, #919 — Unit test coverage for cycle.py, vault_check.py, config.py, and vault_remember.py

---

## [0.17.0] — 2026-04-13

### Added

- #5 — **Add agent role command** — clone, configure, and boot any role from PM with `add_role.py`. Includes dry-run mode, lock file concurrency protection, role validation against config.md, and duplicate registration checks.
- #401 — **Capability sub-skills** — replaced the old tool concept with a composable sub-skill ecosystem. Roles declare capabilities via manifests; the system validates availability at startup.

### Fixed

- #875 — boot_remote.py no longer spawns duplicate agents — PID-based process detection kills stale processes before spawning replacements, with a 2-minute startup grace period
- #632 — .local-config is now created during setup — health checks and auto-boot actually work on fresh installs
- #606 — config.py no longer returns duplicate or phantom agents in list-agents
- #598 — Planning artifact location clarified — dev agents now know to read from pm/planning/
- #591 — All agents now push back on ambiguous context instead of guessing
- #589 — README punchline updated to reflect non-dev team support
- #558 — Dev SOUL.md no longer hardcodes file extensions — works with any project type
- #493 — Skill agent no longer bypasses tracker.py transitions — labels stay in sync
- #492 — PM can now find status:pending-test items via gh issue list
- #470 — Skill agent correctly detects QA-rejected in-progress items without human nudge
- #774 — Fixed triage.py Windows Unicode crash (missing encoding=utf-8)
- #758 — Designer directory now includes working-state.md
- #886 — Added 22 unit tests for health_check.py — critical infrastructure coverage

---

## [0.16.0] — 2026-04-12

### Added

- #328 — **Intent-driven setup wizard** — tell the wizard what you're building and it proposes a team. Role manifest registry (5 roles, 4 tools, 2 presets: software-dev, design). PM and DM always installed. Interactive review screen before any disk writes. Re-run detection with regenerate/rebuild options.
- #4 — **Auto-boot team** — PM automatically spawns all other agents on startup. OS-aware agent launching (macOS Terminal/iTerm, Windows Terminal/PowerShell, Linux tmux).
- #309 — **Unread feedback guard** — tracker blocks pending-test transitions when oversight comments (PM, QA, human) haven't been read, preventing premature status changes.
- #442 — **Vocabulary rename** — "feature" → "task", "bug" → "issue" across labels, commands, templates, and docs. Decouples SquidSquad from code-specific terminology so non-dev teams (design, content, marketing) feel at home.

### Fixed

- #320 — Tracker transitions now enforce role-based authority — agents can only perform transitions they own
- #471 — Issue gate no longer blocked by pending (non-actionable) items — only status:open items block task pickup
- #472 — Dev SOUL.md now requires test coverage for shipped code
- #436 — Improvement scan criteria moved from hardcoded sub-skill to SOUL.md templates — each role scans with its own lens
- #376 — Context-pressure exit replaced with continue — agents no longer kill themselves mid-task
- #378 — Default context pressure threshold lowered from 80% to 70% for earlier, safer exits
- #390 — Fixed Windows UTF-8 encoding crash in tracker.py subprocess calls
- #389 — Status bar no longer shows ghost agents for roles in registry but not installed
- #373 — npx installer now pre-fetches wizard scripts via deterministic manifest
- #335 — PM health check rewritten as Python script (health_check.py) — no more prose-based stale-reporting drift
- #463 — Fixed shell injection risk in boot_remote.py path handling
- #468 — Fixed path traversal vulnerability in vault_remember.py
- #360 — Sub-skill developer guide updated for new role directory layout
- #321, #327 — npx installer stability fixes (dirty worktree abort, --dangerously-skip-permissions)
- #403 — Tracker no longer creates double-prefixed issue titles
- #429, #430, #464, #465, #466, #469 — Internal script hardening and test coverage improvements

---

## [0.15.0] — 2026-04-08

### Added

- #269 — **`npx squidsquad` installer** — bootstrap SquidSquad onto any project with a single command. Checks prerequisites, seeds the skill and setup wizard, and offers to launch immediately. Zero dependencies.

### Fixed

- #280 — README and SKILL.md no longer reference non-existent QA boot scripts — launch instructions now show available scripts depend on your setup
- #281 — SKILL.md file structure diagram updated to match actual repo layout — uses placeholder notation instead of hardcoded paths
- #277 — README Team Shapes table now correctly shows QA and DM as optional add-ons
- #278 — CONTRIBUTING.md bug reports and feature requests now link directly to GitHub Issue templates
- #262 — Vault briefing and project notes updated from v0.11.0 to v0.14.0
- #261 — GitHub Issue templates now use correct SquidSquad label taxonomy (`type:bug`, `type:feature`)
- #260 — Sub-skill guide now documents the `{{runtime:}}` directive for editable agent personalities
- #258 — Architecture docs now cover Runtime SOUL.md and self-diagnostic systems (v0.14.0 additions)
- #257 — CONTRIBUTING.md now mentions `/squidsquad-bug` command for in-session bug reporting
- #210, #194, #193, #197 — Stale documentation references resolved (some already fixed by README overhaul)

---

## [0.14.0] — 2026-04-06

### Added

- #251 — **Self-diagnostic bug reporting** — `/squidsquad-bug` slash command lets users report bugs to the upstream SquidSquad repo with sanitized config + diagnostic context. Automated anomaly detection logs errors from tracker, git, and composition operations locally (JSON Lines, 1MB rotation). Public repos default ON, private repos opt-in.
- #149 — **Runtime SOUL.md** — agent personalities are now separate files (`.squidsquad/[role]/SOUL.md`) read at session start, not compiled into CLAUDE.md. Edit personality directly without redeploying templates.
- #239 — **CONTRIBUTING.md and CODE_OF_CONDUCT.md** — community governance docs for going public. Contributor Covenant v2.1.
- #232 — **Community infrastructure** — AGPL-3.0 LICENSE, GitHub Issue templates (bug report, feature request), SKILL.md license field.
- #189 — **Sub-skill developer guide** — comprehensive guide at `docs/sub-skill-guide.md` covering anatomy, composition, testing, and contribution model.
- #190 — **Architecture overview** — `docs/ARCHITECTURE.md` with Mermaid diagrams covering Ralph Loop, feature lifecycle, sub-skill composition, vault, coordination.
- #233 — **CHANGELOG polish** — rewritten for public readability, no internal jargon.
- #2 — **README overhaul** — 151-line lean landing page with developer-to-developer tone.
- #240 — **Boot-time agent registration** — agents auto-register in config.md Agents section on boot via `config.py sync-agents`.
- #211 — **Phantom fix prevention** — `git_ops.py has-changes` gate in dev agent template prevents marking pending-test without actual code changes.

---

## [0.13.0] — 2026-04-06

### Fixed

- Security: eliminated shell injection risks in internal scripts (subprocess list form throughout).
- Status bar: DM agent uses configured alias instead of hardcoded label.
- Status bar: QA role now has its own hint pool instead of reusing dev hints.
- `/squidsquad-status` command now includes DM in the agent health dashboard.
- Internal test reliability improvements.

---

## [0.12.0] — 2026-04-06

### Added

- **Vault Phase 3: vault-remember** — agents automatically reflect at the end of each productive cycle, capturing decisions, patterns, learnings, and human preferences to the shared vault. Your squad learns and remembers across sessions.
- **Templatized boot scripts** — single template per platform (`.ps1` / `.sh`) generated by `compose.py boot`. Eliminates drift between boot scripts when roles are added or updated.

### Fixed

- Security: eliminated shell injection risk in git operations and label handling.
- Git pull now warns on stash pop failure instead of silently succeeding.
- Documentation updated to match current CLI flags and version.
- Pre-launch `.gitignore` gaps closed (`.obsidian/`, `__pycache__/`).

---

## [0.11.0] — 2026-04-05

### Added

- **Start script test coverage** — 51 static tests validating CLI flags, role injection, and argument handling across all boot scripts.

### Fixed

- Documentation updated to use GitHub Issue numbers instead of old internal IDs.
- Boot scripts fixed: correct `--name` flag and PowerShell argument handling.

---

## [0.10.0] — 2026-04-04

### Added

- **Vault Phase 2: search and validation** — you can now search the vault by tag, type, or keyword. Notes auto-validate on save (broken links, missing fields). Agents update existing notes surgically instead of rewriting them.
- **Common sub-skills** — shared behaviors (git commits, bug filing, discussion protocol, iteration logs) extracted into reusable sub-skills for cleaner, more consistent agent behavior.
- **Sub-skill names in status bar** — line 2 now shows which sub-skill is active (e.g. `git-commit — Pushing changes...`), making agent behavior transparent during operation.

### Fixed

- Agents correctly prioritize bugs over features and block feature pickup when open bugs exist.
- Feature workflow includes "Planned" state between Planning and Approved, giving you a clear approval gate before execution begins.
- Improvement scan correctly classifies findings as bugs or features.
- Timestamped step markers (`[🦑 HH:MM:SS]`) on all Ralph Loop steps for easier scrollback scanning.
- Numerous documentation consistency fixes after GitHub Issues migration.

---

## [0.9.0] — 2026-04-04

### Added

- **Sub-skill architecture** — decomposed monolithic agent templates into composable sub-skills. Main skill orchestrates; roles are independent sub-skills with common behaviors auto-included. Build-time composition keeps templates maintainable.
- **Suppress PM cycles during planning** — PM performs silent pull + health check during active planning phases instead of full noisy cycles. Auto-resumes when planning completes.
- **Designer agent** — new agent type for design-to-code workflows. Interactive design sessions with you, feasibility assessment, structured design specs. Supports Figma, Google Stitch, or any MCP-connected design tool.
- **Separate QA from PM** — PM (human-facing coordinator, feature intake, backlog) and QA (E2E tests, bug verification, feature testing) are now distinct agents. QA is auto-added when dev or designer agents are present.
- **Self-improvement scanning** — agents scan your project for improvements during quiet cycles. Dev finds code issues, QA finds test gaps, designer spots design inconsistencies, DM catches doc gaps, PM identifies process improvements. Rate-limited (max 2 per scan), routed through PM for your review.
- **Vault memory layer Phase 1** — git-tracked, Obsidian-compatible shared memory vault (`.squidsquad/vault/`). PARAG structure (Projects, Areas, Resources, Archives, Galaxy). Agents build knowledge about your preferences, decisions, and patterns over time. Browsable in Obsidian.
- **Agent personalities** — each role has a distinct personality shaping communication, decisions, and collaboration. PM is the diplomat, QA the skeptic, dev the pragmatist, designer the creative, DM the closer.
- **GitHub Issues as tracker** — replaced internal markdown tracker files with GitHub Issues. Labels for type, priority, status, and role. Discussion entries as Issue comments. External contributors can file Issues and PM triages them into the workflow.

### Fixed

- PM no longer ships features with open QA gaps.
- Dev agent picks up QA-rejected features correctly.

---

## [0.8.0] — 2026-03-31

### Added

- **Delivery Manager (DM) role** — new optional agent that owns the "last mile" of shipping: user-facing docs, CHANGELOG entries, version bumps, git tags. Feature lifecycle gains `Pending Ship` status. When DM is absent, PM handles delivery automatically.
- **Granular status phases** — status bar shows exactly what each agent is working on, including the specific bug or feature ID.
- **Overdue indicator** — status bar shows `⏰ +Nm` when an agent's cycle exceeds the configured interval.
- **Bug discussion flow** — PM investigates root cause and discusses the problem with you before filing bugs to dev. You can steer the fix approach.
- **Cross-clone health detection** — agents detect each other's health by reading files across clones. No background processes, no API calls. Health icons: 🦑 healthy, 👻 stalled, ❓ unknown.
- **Philosophy section in README** — documents core design principles: git as the bus, complete audit trail, no external dependencies.

### Fixed

- DM role is fully optional with seamless PM fallback.
- Overdue timer no longer shows stale values on quiet cycles.
- Atomic file writes prevent stale status bar from file locking races on Windows.

---

## [0.7.0] — 2026-03-30

### Fixed

- Boot scripts include all required initialization steps.
- README updated to reflect current boot mechanism.
- All boot scripts use correct CLI flags.
- Dev agent bug triage pattern now correctly matches open bugs.

---

## [0.6.0] — 2026-03-29

### Added

- **Externalized agent templates** — agent instruction files are no longer 200+ line monoliths. Setup generates shared templates with all values substituted at build time. Each agent's CLAUDE.md is a small bootstrapper pointing to the template. Upgrades only regenerate templates without touching your config.
- **Open planning artifacts in VS Code** — after each planning phase, PM offers to open the artifact in VS Code. "Never ask again" persists across sessions.
- **Status bar redesign (Emoji Rich)** — complete rewrite with expressive emoji indicators. Dev bar: active task (🔨) or backlog (🐛/⭐/✅), context pressure (🧠/🧠🔥/🧠💀), countdown (🔄/🔜). PM bar adds ship counter (📦), planning phase (📋), team health icons (🦑/👻), and rest nudge (🌙/😴).
- **Current step + contextual hints** — status bar line 2 shows the active Ralph Loop step or rotating contextual hints when idle (e.g. "Msg me any time to file a bug").
- **Change loop interval on the fly** — `/squidsquad-interval <Nm>` changes the interval for all agents without restarting.
- **Upgrade & migration analysis** — feature planning always includes upgrade impact analysis, even for trivial features.
- **Smart resume for interrupted planning** — when planning resumes after an interruption, each phase checks if its artifact already exists and reuses it when appropriate.
- **Explicit approval gate after discussion** — PM presents a summary of all locked decisions and asks you to confirm before proceeding to test planning.
- **SquidSquad only activates via boot scripts** — normal `claude` sessions in a SquidSquad repo no longer trigger auto-boot.

### Fixed

- PM no longer asks for approval immediately after filing a feature — now completes the full planning process first.
- Status bar shows full squad health, not just dev agents.
- Git commands in status bar have timeouts to prevent hangs during concurrent operations.

---

## [0.5.2] — 2026-03-28

### Added

- **Status line** for all agents via Claude Code's `statusLine` setting. Shows role, version, backlog counts, context pressure, and cycle countdown. PM additionally shows team health icons and rest nudge.
- **Step markers** — every Ralph Loop step prints a `[🦑]` prefixed status line for easy scanning in terminal scrollback.
- **Context pressure detection** — agents check context window usage at cycle start. If above threshold (default 70%), they save state, commit, and exit for a fresh context. Boot scripts restart them automatically.
- **Working state file** — agents persist current task progress. On restart, they resume from saved state instead of starting over.
- **Quiet cycle skipping** — agents skip logging and committing when no work was done. Keeps git history meaningful.
- **Iteration log retention** — agents keep the last 20 iteration files. Git history preserves older ones.
- **PR-based approval flow** (optional) — dev agents create PRs instead of pushing to main. You review and merge on GitHub.
- **GitHub Issues ingestion** (optional) — PM auto-ingests open GitHub Issues into agent trackers each cycle.
- **`/squidsquad-status` command** — type in any Claude session for a dashboard of agent health, backlogs, and recently shipped items.
- **Deep 5-phase feature lifecycle** — Research, Discussion, Planning, Execution, QA. PM spawns research agents, asks targeted questions, creates test plans. Light mode for trivial features.
- **Reliable cycling via `/loop`** — agents use cron-based cycling instead of self-managed sleep loops.
- **Auto versioning** — PM tracks shipped items and auto-bumps the minor version every N items (configurable, default 10) when zero open bugs exist.
- **Status bar chaining** — SquidSquad no longer replaces your existing status bar. Your output appears first, SquidSquad appends as the last line.

### Fixed

- Status line parses context window usage with color coding.
- PowerShell boot scripts render Unicode correctly.
- PM check-in is non-blocking — prints a note and continues immediately.
- Setup no longer silently overwrites existing settings.
- Feature approval gates through full planning process.

---

## [0.5.1] — 2026-03-27

### Added

- **Structured setup prompts** — labeled fields with defaults, validation, and examples instead of freeform questions.
- **Single-sentence setup** — "Set up SquidSquad for kubex, BE only, 5 min interval" extracts all values and only prompts for gaps.
- **Bug/feature import during setup** — import from pasted text, local files, or connected tools (GitHub Issues, Jira, Linear).

### Fixed

- Setup and templates no longer hardcode specific role names — fully flexible team shapes.
- Boot scripts own the loop correctly.
- Pre-granted file permissions so agents never pause mid-cycle.

---

## [0.5.0] — 2026-03-27

Initial release.

- Flexible multi-agent coordination: user-defined dev roles + PM/QA
- Shared `.squidsquad/` folder as the coordination layer — no message queues, no servers
- All communication through append-only markdown tracker files committed to git
- Ralph Loop for each agent: pull, work, test, log, push, sleep
- Bug and feature tracking with severity, status flow, and discussion threads
- Any agent can file bugs to any team — no routing bottleneck
- Full setup wizard: generates folder structure, config, templates, boot scripts
- Boot scripts for bash/zsh and PowerShell
- Semver versioning with upgrade path for future releases
- SessionStart hook shows squid logo on every Claude Code boot

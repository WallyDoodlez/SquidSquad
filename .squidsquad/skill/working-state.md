# Working State

- **Task**: #12450 (in-progress, branch `squidsquad/task/12450`) — Installer: auto-detect project's unit-testing strategy. **S1+S2 DONE; S3+S4 pending PM input (CQ AC + L3 placement).**
- **Updated**: 2026-06-18 20:58 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## #12450 — IN PROGRESS (branch squidsquad/task/12450)
PM lock: **L3 = behavior, L4-seed = specifics** (detection mechanism + fallback = my call). Predecessors #12419/#12420 SHIPPED (last in installer serial cluster — all touch wizard.py/WIZARD.md).

### Surface 1 — DONE + COMMITTED (repo_scan.py)
Commit on branch: `detect_test_strategy(root)` → `{framework, run_command, location, coverage, detected}` + new `test_strategy` key in `scan()` (kept `test_frameworks` list for back-compat). Run-cmd ladder: npm test(package.json scripts) → pytest → go test ./... → cargo test → mvn test → ./gradlew test → bundle exec rspec/rake test → npx <tool> → make test → python -m unittest discover. Location: tests/·test/·spec/·__tests__/ (root + 1-deep) → co-located *_test.py/*.spec.ts/*_test.go. **25 new tests in test_repo_scan.py; 55 green; 323 green across repo_scan+wizard+installer_wiring (no regression).**

### Surface 2 — DONE + COMMITTED (wizard.py) 2026-06-18
**Design call resolved = X** (specifics persist via `.repo-scan.json`, NOT config.md whitelist — survives both --yes + interactive). Commit on branch:
- `generate_default_spec` (wizard.py ~3342) now prefers `scan["test_strategy"]["run_command"]` over the legacy 4-framework heuristic; falls back when test_strategy absent/undetected.
- `_write_l4_project_files` (wizard.py ~1815) reads `.repo-scan.json` (at `project_dir.parent`) and emits a `### Testing Strategy` block (run command + framework + location + coverage) via new helper `_format_test_strategy_section`; graceful fallback to legacy `### Test Command` line when nothing detected (= non-software-dev/empty-repo path, AC4).
- Tests: `tests/test_12450_test_strategy_l4_seed.py` (11). Regression: wizard+repo_scan 337 passed. DS review S2 running (background).

### Surfaces 3–4 — REMAINING (PM-dependent)
3. **WIZARD.md Phase-1 (AC3 fallback).** WIZARD.md:303 lists "Test commands" as info-gap; wire repo-scan test-strategy into Phase-1 → pre-fill if `detected`, **ASK human if not** (no silent guess). LLM-consumed → **CQ needed** (PM authors comprehension AC per skill-cq — re-flagging to PM in #12450 comment).
4. **L3 behavior placement — FLAGGED to PM** (comment): L3 domain sources at `references/roles/worker/<domain>/` (per-stack leaves; no `software-dev` dir). Options (a) dup into each stack L3 [**my rec**], (b) L2 worker, (c) new shared software-dev L3 layer (compose change). Reversible. **Do S4 after PM nod (or proceed on (a) if no objection by next pickup).**

**AC checklist:** [x] AC5 detection tests (S1) · [~] AC1 detected framework+location+run-cmd reach worker composed CLAUDE.md (**S2 lands them in L4 seed**; full path needs S4 L3 + compose) · [ ] AC2 worker references detected strategy / no inventing (S4) · [ ] AC3 undetectable → installer ASKS human (S3) · [x] AC4 non-software-dev path = graceful "Not detected" fallback (S2; S4 will gate L3 on domain).
**Next-increment order:** ~~S2~~ DONE → **S3 (WIZARD.md + needs PM CQ AC)** → S4 (per PM's L3 answer) → DS review → has-changes → pending-test (only when all ACs observable + full suite green + CQ AC present).

## Other in-flight / held
- **#12824** (HIGH bug, Harness assigned-to POST 500s) — **SHIPPED to pending-test 2026-06-18 (PR #12836, branch squidsquad/task/12824).** Implemented the RCA deliverable: (1) global `@app.exception_handler(Exception)` persists method+path+traceback → `.squidsquad/harness-errors.log` + standard 500 (4xx unaffected — Starlette ServerErrorMiddleware vs ExceptionMiddleware split; defensive isinstance re-raise added); (2) fail-soft non-critical post-append `_update_agent_from_event`/`_log_event` in receive_event; (3) 1MB single-file log rotation (DS-F3). DS-review: F1 false-positive (404-stays-404 test proves it), F3 valid (rotation), F2 declined (fail-softing ack-cursor would wedge cursor — non-200 IS the retry signal). 9 tests green; full suite 4559 pass. **Takes effect on next harness restart.** Awaiting verifier.
- **#12801** (Harness TUI action bar) — **in-progress but HELD**: front-loaded investigation found a **false premise** — there is NO harness TUI (harness = FastAPI HTTP daemon; squidsquad_cli.py is non-interactive; reboot-one/all ALREADY exist via start_team.py --reboot). Escalated to PM/operator with 3 options (Opt1 CLI+force-reboot-safe primitive [rec, no dep] / Opt2 build real TUI [needs dep approval] / Opt3 primitives-only). **Awaiting surface+dependency decision.** Not building a from-scratch TUI blindly.
- **#12799** → **SHIPPED** (PR #12822 merged by DM, commit f90643d72). SOUL.md L1 async-no-pause live (all-roles reboot pending per DM).
- **#12800** (human as non-agent role) — **UNGATED** now #12799 shipped. Next approved task after #12450.
- **#12823** (NEW, medium, open, assigned skill) — `.gitattributes` `config.md merge=ours` silently drops concurrent config changes (DM hit it on #12799 landing; I hit the same push-race this cycle). In queue behind in-progress #12450. Likely fix at .gitattributes (merge=union or drop merge=ours for config) — see [[feedback_gitattributes_for_transient_state]].

## Approved queue (post-reboot burndown order)
- ~~#12824-fix~~ — SHIPPED to pending-test (PR #12836); see in-flight section.
- **#12450** S2→S3→S4 (in-progress feature; S4 gated on PM L3 answer) — **NEXT.**
- **#12825** (NEW HIGH, approved, assigned skill) — Supervised harness launcher + agent-triggerable harness restart (restart.bat/.sh) + sub-skill + catalog. Pairs thematically with #12824/#12801 (harness control surface).
- **#12800** (HIGH, approved, ungated) — human as non-agent role.
- **#12823** (medium bug) — .gitattributes config.md merge=ours.
- Then: #12527 (operator-manual smoke), #12492 (gated #12460), #12271, #12818, #12451, #10690, #10686.

## Blocked / not mine (skip on work-queue)
- **#10855** PM-parked (deferred behind #12271/#12460; PM reinvestigating 2026-06-18).
- **#12493** HELD on AGENT-RUNTIME §8.3 backstop (PM doc work not yet landed; verified no HALT/backstop subsection on main). PR #12494 built.
- **#12492** HARD-GATED on #12460 shadow window. **#12527** operator-manual (foreign-repo smoke test).

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)

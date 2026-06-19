# Working State

- **Task**: #12450 (in-progress, branch `squidsquad/task/12450`) — Installer: auto-detect project's unit-testing strategy (L3 software-dev domain). [resume next — #12824 just shipped to pending-test]
- **Updated**: 2026-06-18 20:42 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## #12450 — IN PROGRESS (branch squidsquad/task/12450)
PM lock: **L3 = behavior, L4-seed = specifics** (detection mechanism + fallback = my call). Predecessors #12419/#12420 SHIPPED (last in installer serial cluster — all touch wizard.py/WIZARD.md).

### Surface 1 — DONE + COMMITTED (repo_scan.py)
Commit on branch: `detect_test_strategy(root)` → `{framework, run_command, location, coverage, detected}` + new `test_strategy` key in `scan()` (kept `test_frameworks` list for back-compat). Run-cmd ladder: npm test(package.json scripts) → pytest → go test ./... → cargo test → mvn test → ./gradlew test → bundle exec rspec/rake test → npx <tool> → make test → python -m unittest discover. Location: tests/·test/·spec/·__tests__/ (root + 1-deep) → co-located *_test.py/*.spec.ts/*_test.go. **25 new tests in test_repo_scan.py; 55 green; 323 green across repo_scan+wizard+installer_wiring (no regression).**

### Surfaces 2–4 — REMAINING (exact anchors mapped)
2. **wizard.py L4-seed wiring (keystone, placement-independent).** Integration point = `generate_default_spec()` **wizard.py:3329** — at **3342-3352** it derives `test_command` crudely from `test_frameworks`; replace with `scan["test_strategy"]["run_command"]` (fallback to old heuristic). Worker agent dict **3377-3384** carries `stack`/`test_command` → consumed by `_write_l4_project_files()` **wizard.py:1805** (writes `shared-stack-details.md` Test Command section). Enhance that seed to emit framework+run_command+location.
   - **DESIGN CALL (resolve first):** where do the detected *specifics* (framework/location) persist? `_AGENT_NESTED_FIELD_ORDER` **wizard.py:1443** is the config.md agent-field whitelist (only role/variant/iteration_mode/stack/test_command written). Options: (X) have `_write_l4_project_files`/scaffold read `test_strategy` from the persisted **`.repo-scan.json`** (scaffold already reads it at **wizard.py:2031**) — no whitelist change, cleanest; (Y) add `test_framework`/`test_location` to agent spec + whitelist so they round-trip via config.md. **Lean X** (specifics belong in the L4 seed + scan artifact, not config.md). Default preset literally = `software-dev` (3365).
3. **WIZARD.md Phase-1 (AC3 fallback).** WIZARD.md:303 already lists "Test commands" as an info-gap; wire repo-scan test-strategy detection into Phase-1 → pre-fill if `detected`, **ASK human if not** (no silent guess). LLM-consumed → **CQ needed** (PM authors comprehension AC per skill-cq — flagged in pickup comment).
4. **L3 behavior placement — FLAGGED to PM** (comment): L3 domain sources live at `references/roles/worker/<domain>/` (per-stack leaves android/ios/fullstack/web/skill; compose binds one (class,domain) per alias). No `software-dev` domain dir. Options (a) dup into each stack L3 [**my rec, proceeding unless PM objects**], (b) L2 worker (DRY but hits future non-code worker), (c) new shared software-dev L3 layer (compose change). Reversible. **Do surface 4 after PM nod (or proceed on (a) if no objection by next pickup).**

**AC checklist:** [x] AC5 detection tests (surface 1) · [ ] AC1 detected framework+location+run-cmd reach worker composed CLAUDE.md (needs S2 L4-seed + S4 L3 + compose) · [ ] AC2 worker references detected strategy / no inventing (S4) · [ ] AC3 undetectable → installer ASKS human (S3) · [ ] AC4 non-software-dev domains unaffected (S2/S4 — gate on preset/domain).
**Next-increment order:** S2 (resolve design call X/Y → wire + tests) → S3 (WIZARD.md + flag CQ) → S4 (per PM's L3 answer) → DS review (installer+instructions) → has-changes → pending-test (only when all ACs observable + full suite green + CQ AC present).

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

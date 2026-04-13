# FEAT-SKILL-347 Test Plan — Separate PM from QA Role

## Test Cases

### TC-1: QA gets own Ralph Loop (QA present, software-dev preset)
- **Precondition**: Fresh software-dev install with QA scaffolded (`compose.py deploy qa` run). `.squidsquad/qa/CLAUDE.md`, `SOUL.md`, `working-state.md` all exist.
- **Steps**: Boot the QA agent. Observe the steps it executes in one cycle.
- **Expected**: QA runs its own Ralph Loop: Pull Latest → Context Pressure → Resume Working State → Run E2E Tests → Investigate/File Issues → Verify Fixed Issues → Verify Pending-Test Tasks → Monitor PRs (if enabled) → Agent Health Check → Boot Remote Agents → Improvement Scan (test-coverage lens) → Iteration Log → Vault → Git → Done.
- **Verification**: Check `.squidsquad/qa/current-state` is being written each cycle. Check `.squidsquad/qa/iterations/` for QA iteration logs. Confirm QA loop never pauses waiting for PM input.

### TC-2: PM loses Steps 3-6 when QA is present
- **Precondition**: `.squidsquad/qa/` directory exists (QA installed).
- **Steps**: Boot PM. Observe one full Ralph Loop cycle.
- **Expected**: PM executes Step 1 (Pull), Step 1b (Context Pressure), Step 1c (Resume), Step 2 (Check-in), then skips directly to Step 7 (Agent Health Check). Steps 3 (E2E Tests), 4 (Investigate Failures), 5 (Verify Fixed Issues), 6 (Verify Pending-Test Tasks), 6b (PR Monitoring), and 6c (Ship Counter from issues) are all absent.
- **Verification**: PM iteration log has no entries for E2E test run or issue verification. `pm/qa-log.md` is not updated this cycle. No `pending-test → pending-ship` transitions performed by PM.

### TC-3: PM fallback — PM retains QA steps when QA is absent
- **Precondition**: `.squidsquad/qa/` directory does NOT exist (QA not installed, e.g., design preset or non-upgraded install).
- **Steps**: Boot PM. Observe one full Ralph Loop cycle.
- **Expected**: PM executes the full combined PM/QA loop including Steps 3-6 (E2E tests, investigate failures, verify fixed issues, verify pending-test tasks, PR monitoring, ship counter). Presence check (`.squidsquad/qa/` missing) triggers fallback mode.
- **Verification**: PM iteration log contains E2E test result, issue verification entries. `pm/qa-log.md` is updated. PM performs `pending-test → pending-ship` transitions.

### TC-4: QA preset-gated — QA only installed for software-dev
- **Precondition**: New install using `design` preset. New install using `software-dev` preset.
- **Steps**: Run wizard for each preset. Observe which agents are scaffolded.
- **Expected**: `design` preset install → no `.squidsquad/qa/` directory created. `software-dev` preset install → `.squidsquad/qa/` directory created with `CLAUDE.md`, `SOUL.md`, `working-state.md`.
- **Verification**: `ls .squidsquad/` after design install shows no `qa/`. `ls .squidsquad/` after software-dev install shows `qa/` present.

### TC-5: QA manifest flag flipped for software-dev
- **Precondition**: `references/roles/qa/manifest.yaml` has been updated.
- **Steps**: Read `references/presets/software-dev/manifest.yaml` and `references/roles/qa/manifest.yaml`.
- **Expected**: QA manifest has `always_installed: true` (or equivalent gating that ensures QA is installed for software-dev). `software-dev` preset's `role_install_order` lists `qa`.
- **Verification**: `grep always_installed references/roles/qa/manifest.yaml` returns `true`. `grep qa references/presets/software-dev/manifest.yaml` returns a result.

### TC-6: Split improvement scanning — PM scans process, QA scans test coverage
- **Precondition**: Both PM and QA are installed. Both reach quiet cycle threshold (3 consecutive quiet cycles).
- **Steps**: Allow both agents to reach improvement scan trigger. Observe what each agent scans.
- **Expected**: PM improvement scan focuses on process improvements (workflow, template quality, coordination patterns). QA improvement scan focuses on test coverage gaps (missing test cases, untested code paths, flaky tests). Neither agent scans the other's domain.
- **Verification**: PM scan history (`pm/scan-history.md`) shows process-oriented findings. QA scan history (`qa/scan-history.md`) shows test-coverage-oriented findings. PM's SOUL.md improvement scan section specifies process lens. QA's SOUL.md improvement scan section specifies test-coverage lens.

### TC-7: QA auto-detects pending-test items via tracker
- **Precondition**: Two issues exist with `status:pending-test` label. QA agent is running.
- **Steps**: Start a QA cycle. Observe the verification step.
- **Expected**: QA queries `python references/scripts/tracker.py list-issues skill --status pending-test` (and equivalent for tasks). QA picks up both items without any explicit PM-to-QA handoff. No PM involvement needed.
- **Verification**: QA iteration log lists both pending-test items as verified (or returned to in-progress). GitHub Issues show status transitions authored by `qa-lead`. PM iteration log has no mention of these items.

### TC-8: Zero-gap gate enforced by QA (not PM)
- **Precondition**: QA installed. Task with `status:pending-test` exists. Task has a gap (one acceptance criterion not met).
- **Steps**: QA runs verification step.
- **Expected**: QA applies the zero-gap gate: any gap returns the item to `in-progress` with specific findings in Discussion. QA does NOT mark it `pending-ship`. PM does not independently verify this item.
- **Verification**: GitHub Issue shows transition from `pending-test` back to `in-progress` by `qa-lead`. Discussion comment lists specific failing criteria. No `pm-lead` comment on the verification outcome.

### TC-9: QA files objective bugs directly; PM does not re-verify
- **Precondition**: QA finds an objective test failure (assertion error, crash, wrong return value).
- **Steps**: QA completes investigation and files a bug.
- **Expected**: QA creates a new GitHub Issue via `tracker.py create-issue`. Bug is filed with `role:skill` (or appropriate target role), `type:issue`, severity label. PM does NOT receive a notification — Discussion entries on the issue are visible to all. PM does NOT duplicate the filing.
- **Verification**: New GitHub Issue exists authored by `qa-lead`. PM iteration log does not reference this new bug as something PM filed. No double-filing of same bug.

### TC-10: QA increments ship counter, not PM (when QA is present)
- **Precondition**: QA installed. QA verifies and closes an issue (transitions to `pending-ship` or triggers close).
- **Steps**: QA closes a verified issue in its verification step.
- **Expected**: QA increments `Shipped Since Last Bump` in `config.md`. PM does NOT also increment the counter for QA-verified closures.
- **Verification**: `config.md` shows exactly one increment after a QA-verified closure. Git log shows the config.md change committed by QA's git-commit step.

### TC-11: Upgrade — existing software-dev install gets QA scaffolded
- **Precondition**: Existing `.squidsquad/` directory from before #347, using software-dev preset. No `.squidsquad/qa/` directory exists.
- **Steps**: Run `/squidsquad-upgrade`.
- **Expected**: Upgrade detects software-dev preset. Runs `compose.py deploy qa` to create `.squidsquad/qa/CLAUDE.md`. Copies `references/roles/qa/SOUL.md` to `.squidsquad/qa/SOUL.md` (if missing). Creates `.squidsquad/qa/working-state.md` with default content. Re-composes PM: `compose.py deploy pm` to get updated PM template without QA steps. Updates `config.md` Agents section to list QA separately (not as "PM/QA").
- **Verification**: After upgrade, `.squidsquad/qa/` exists with all three files. PM CLAUDE.md no longer contains Steps 3-6. `config.md` Agents section lists `PM` and `QA` as separate entries.

### TC-12: Upgrade — existing non-software-dev install does NOT get QA
- **Precondition**: Existing `.squidsquad/` directory using design preset.
- **Steps**: Run `/squidsquad-upgrade`.
- **Expected**: Upgrade detects design preset. Does NOT scaffold QA directory. PM template remains as combined PM/QA for this preset. No `.squidsquad/qa/` created.
- **Verification**: After upgrade, `ls .squidsquad/` shows no `qa/` directory. PM CLAUDE.md still contains QA fallback steps.

### TC-13: PM identity change — "PM/QA" → "PM"
- **Precondition**: `compose.py deploy pm` run after #347 changes.
- **Steps**: Read `.squidsquad/pm/CLAUDE.md` header and description.
- **Expected**: Header reads "PM" not "PM/QA". Role description no longer says "You are the PM/QA on the SquidSquad autonomous dev team." Agent health check output shows role as "pm" not "pm/qa".
- **Verification**: `head -20 .squidsquad/pm/CLAUDE.md` shows updated identity. `config.md` Agents section matches.

### TC-14: QA working-state suppression does NOT suppress PM
- **Precondition**: QA has an active planning phase in `qa/working-state.md` (e.g., `**Phase**: test-planning #XXX`). QA cycle should be suppressed.
- **Steps**: PM runs a cycle while QA working-state has active phase.
- **Expected**: PM continues its normal cycle unaffected. QA suppresses its own cycle (runs only pull + health check). The two agents' suppression logic is independent.
- **Verification**: PM iteration log shows a normal cycle. QA iteration log shows a suppressed cycle marker. PM does NOT wait for QA to unsuppress.

### TC-15: Shared tracker, no duplicate transitions
- **Precondition**: Dev marks a task `pending-test`. Both PM and QA are running simultaneously.
- **Steps**: Observe next cycle for both PM and QA.
- **Expected**: Only QA (not PM) performs the `pending-test → pending-ship` transition. PM's QA presence check (`.squidsquad/qa/` exists) causes PM to skip verification steps entirely, preventing duplicate transitions.
- **Verification**: GitHub Issue shows exactly one transition comment for `pending-test → pending-ship`, authored by `qa-lead`. No `pm-lead` verification comment on this item.

---

## Smoke Tests

- [ ] `ls .squidsquad/` after software-dev install shows `qa/` directory
- [ ] `ls .squidsquad/` after design install shows no `qa/` directory
- [ ] PM `current-state` never shows `testing|` or `verifying|` phases when QA is present
- [ ] QA `current-state` shows `verifying|` phases when items are pending-test
- [ ] `python references/scripts/tracker.py list-issues qa --status pending-test` runs without error
- [ ] `python references/scripts/health_check.py` lists QA agent after upgrade
- [ ] PM CLAUDE.md word count is lower after separation (QA steps removed)
- [ ] QA CLAUDE.md exists and is non-empty after `compose.py deploy qa`

---

## Regression Risks

- **PM delivery fallback accidentally disabled**: When QA is present, PM skips Steps 3-6 but must KEEP Step 6d (delivery fallback when DM absent). Verify Step 6d still runs for PM even with QA present.
- **config.md Agents section format**: Other scripts (health_check.py, boot_remote.py) may parse the Agents section. Verify they handle the new separate `PM` / `QA` entries without breaking.
- **qa-log.md location conflict**: PM writes to `pm/qa-log.md`; QA writes to `qa/qa-log.md`. Verify no agent writes to the wrong file after separation.
- **Task Intake Phase 5**: PM template previously had a Phase 5 QA subagent. After separation, QA picks up `pending-test` items independently. Verify that the task lifecycle still reaches QA verification — no items stuck in `pending-test` forever because Phase 5 was removed from PM and QA wasn't explicitly triggered.
- **boot_remote.py**: After upgrade, `config.md` lists QA as a separate agent. Verify `boot_remote.py` boots QA as a distinct agent (not double-booting PM/QA as one).
- **PR Flow step ownership**: PR monitoring moves to QA. Verify PM template no longer contains Step 6b. Verify QA template contains PR monitoring. Verify no gap where PR monitoring runs in neither agent.

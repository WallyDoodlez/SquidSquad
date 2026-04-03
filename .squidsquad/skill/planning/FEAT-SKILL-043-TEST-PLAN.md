# FEAT-SKILL-043 Test Plan — Separate QA from PM into Independent Role

## Test Cases

### Happy Path

#### TC-1: QA role sub-skill file exists and follows composition pattern
- **Precondition**: Feature implemented, `references/sub-skills/roles/qa-agent.md` created
- **Steps**:
  1. Read `references/sub-skills/roles/qa-agent.md`
  2. Verify it follows the same include directive and placeholder substitution patterns as other role files (pm-agent.md, dev-agent.md)
  3. Verify it references QA-specific sub-skills via include directives
- **Expected**: File exists, uses `[ROLE]` placeholder for dev agent references (not hardcoded), includes QA-specific sub-skills (`qa-specific/verify-bugs.md`, `qa-specific/verify-features.md`, etc.), follows FEAT-SKILL-030 composition conventions.
- **Verification**:
  ```bash
  test -f references/sub-skills/roles/qa-agent.md && echo "PASS" || echo "FAIL"
  grep -c "include" references/sub-skills/roles/qa-agent.md
  ```

#### TC-2: QA Ralph Loop contains all required steps
- **Precondition**: QA role template created
- **Steps**:
  1. Read the composed QA template (or qa-agent.md source)
  2. Verify loop steps: Pull, Context Pressure Check, Resume Working State, Interval Sync, E2E Tests, Investigate/File Bugs, Verify Fixed Bugs, Verify Pending Test Features, Health Check, Log, Commit
- **Expected**: QA Ralph Loop includes all steps from the research document. Each step has clear instructions. Loop uses the same structural conventions as other role loops (step markers, status bar state writes, atomic writes for current-state).
- **Verification**:
  ```bash
  grep -c "Step" references/sub-skills/roles/qa-agent.md
  grep "Pull Latest" references/sub-skills/roles/qa-agent.md
  grep "Verify.*Bug" references/sub-skills/roles/qa-agent.md
  grep "Verify.*Feature\|Pending Test" references/sub-skills/roles/qa-agent.md
  grep "Health Check" references/sub-skills/roles/qa-agent.md
  ```

#### TC-3: PM template has zero verification steps when QA exists
- **Precondition**: QA role created, PM template recomposed
- **Steps**:
  1. Read the PM role template (`references/sub-skills/roles/pm-agent.md`)
  2. Search for any E2E test execution, bug verification, feature verification, or health check steps
- **Expected**: PM template contains NO steps for: running E2E tests, verifying Fixed bugs, verifying Pending Test features, running agent health checks, or executing Phase 5 QA subagent. PM's "must never do" list includes all verification activities.
- **Verification**:
  ```bash
  # These should return 0 matches in the PM template's active steps:
  grep -c "E2E\|e2e" references/sub-skills/roles/pm-agent.md
  grep -c "Verify Fixed\|Verify.*Bug" references/sub-skills/roles/pm-agent.md
  grep -c "Pending Test.*Pending Ship" references/sub-skills/roles/pm-agent.md
  grep "must never" references/sub-skills/roles/pm-agent.md
  ```

#### TC-4: QA discovers agents from config.md Dev Agents + designer directory check
- **Precondition**: config.md has `Dev Agents: skill`, no designer directory
- **Steps**:
  1. Read QA template's agent discovery logic
  2. Verify it reads `Dev Agents` from config.md
  3. Verify it checks for `.squidsquad/designer/` directory existence
- **Expected**: QA discovers agents using the same mechanism as dev/DM: parses `Dev Agents` list from config.md for dev agents, checks for `.squidsquad/designer/` directory for designer. No hardcoded agent list.
- **Verification**:
  ```bash
  grep "Dev Agents\|config.md" references/sub-skills/roles/qa-agent.md
  grep "designer" references/sub-skills/roles/qa-agent.md
  ```

#### TC-5: QA reads Pending Test features from all agent trackers
- **Precondition**: QA template created, at least one dev agent tracker exists with a Pending Test feature
- **Steps**:
  1. Read QA's feature verification step
  2. Verify it iterates over all discovered agents
  3. Verify it reads `features/INDEX.md` from each agent directory
  4. Verify it filters for `Pending Test` status
- **Expected**: QA scans `.squidsquad/[each-dev-role]/features/INDEX.md` and `.squidsquad/designer/features/INDEX.md` (if designer exists). QA reads individual feature files for items with `Pending Test` status.
- **Verification**:
  ```bash
  grep "features/INDEX.md" references/sub-skills/qa-specific/verify-features.md
  grep "Pending Test" references/sub-skills/qa-specific/verify-features.md
  ```

#### TC-6: QA reads Fixed bugs from all agent trackers
- **Precondition**: QA template created, at least one dev agent tracker exists with a Fixed bug
- **Steps**:
  1. Read QA's bug verification step
  2. Verify it iterates over all discovered agents
  3. Verify it reads `bugs/INDEX.md` from each agent directory
  4. Verify it filters for `Fixed` status
- **Expected**: QA scans `.squidsquad/[each-dev-role]/bugs/INDEX.md` and `.squidsquad/designer/bugs/INDEX.md` (if designer exists). QA reads individual bug files for items with `Fixed` status. QA transitions: Fixed -> Verified -> Closed (or back to Open if not fixed).
- **Verification**:
  ```bash
  grep "bugs/INDEX.md" references/sub-skills/qa-specific/verify-bugs.md
  grep "Fixed" references/sub-skills/qa-specific/verify-bugs.md
  grep "Verified\|Closed" references/sub-skills/qa-specific/verify-bugs.md
  ```

#### TC-7: QA marks Pending Ship and DM picks up
- **Precondition**: QA template created with Pending Ship transition logic
- **Steps**:
  1. Read QA's feature verification step for the Pending Ship transition
  2. Verify QA updates Status field to `Pending Ship`
  3. Verify QA appends Discussion entry with `**qa**` signature
  4. Verify QA regenerates INDEX.md
  5. Verify DM template reads Pending Ship items (no change needed to DM)
- **Expected**: QA sets status to `Pending Ship` directly. QA does NOT hand back to PM. DM picks up `Pending Ship` items on its next cycle. If DM absent, PM picks up via existing delivery fallback.
- **Verification**:
  ```bash
  grep "Pending Ship" references/sub-skills/qa-specific/verify-features.md
  grep "qa" references/sub-skills/qa-specific/verify-features.md
  ```

#### TC-8: QA files bugs directly for objective test failures
- **Precondition**: QA template created with bug filing logic
- **Steps**:
  1. Read QA's E2E test and bug investigation step
  2. Verify QA files bugs directly to the correct agent's tracker when tests fail
  3. Verify no human approval gate for test-discovered bugs
- **Expected**: QA creates bug files in the responsible agent's `bugs/` directory, increments the agent's BUG counter in config.md, regenerates the agent's `bugs/INDEX.md`. No Bug Discussion Flow or human approval required for objective test failures.
- **Verification**:
  ```bash
  grep -i "file.*bug\|bug.*file" references/sub-skills/qa-specific/e2e-tests.md
  # Should NOT reference human approval for test failures:
  grep -c "human.*approv\|Bug Discussion" references/sub-skills/qa-specific/e2e-tests.md
  ```

#### TC-9: QA flags subjective findings in Discussion (not filed as bugs)
- **Precondition**: QA template created with finding classification logic
- **Steps**:
  1. Read QA template for how subjective findings are handled
  2. Verify subjective findings go to Discussion entries, not direct bug filing
- **Expected**: QA distinguishes between objective failures (test case pass/fail) and subjective findings (coherence, style concerns). Subjective findings are flagged in Discussion for human review via PM. Only objective failures are filed as bugs directly.
- **Verification**:
  ```bash
  grep -i "subjective\|Discussion\|flag" references/sub-skills/qa-specific/e2e-tests.md
  ```

#### TC-10: QA directory structure created correctly
- **Precondition**: QA setup or upgrade has run
- **Steps**:
  1. Check for `.squidsquad/qa/` directory
  2. Verify subdirectories and files
- **Expected**: Directory structure matches spec: `qa/current-state`, `qa/working-state.md`, `qa/qa-log.md`, `qa/iterations/`. QA does NOT have its own `bugs/` or `features/` directories (QA reads/writes to dev agent trackers).
- **Verification**:
  ```bash
  test -d .squidsquad/qa && echo "PASS" || echo "FAIL"
  test -d .squidsquad/qa/iterations && echo "PASS" || echo "FAIL"
  test -f .squidsquad/qa/qa-log.md && echo "PASS" || echo "FAIL"
  test ! -d .squidsquad/qa/bugs && echo "PASS (no bugs dir)" || echo "FAIL (has bugs dir)"
  test ! -d .squidsquad/qa/features && echo "PASS (no features dir)" || echo "FAIL (has features dir)"
  ```

#### TC-11: New qa/qa-log.md exists, old pm/qa-log.md preserved
- **Precondition**: QA added to an existing project that has `pm/qa-log.md` with history
- **Steps**:
  1. Run upgrade/setup to add QA
  2. Check for `qa/qa-log.md` (new, fresh)
  3. Check for `pm/qa-log.md` (old, preserved)
- **Expected**: `qa/qa-log.md` is created as a fresh file for QA to write to. `pm/qa-log.md` is preserved with all historical entries. PM stops writing to `pm/qa-log.md` when QA exists. No migration or copy of old entries into the new file.
- **Verification**:
  ```bash
  test -f .squidsquad/qa/qa-log.md && echo "PASS" || echo "FAIL"
  test -f .squidsquad/pm/qa-log.md && echo "PASS (preserved)" || echo "FAIL (deleted)"
  ```

#### TC-12: QA boot script exists and sets correct role
- **Precondition**: Feature implemented, boot scripts created
- **Steps**:
  1. Read `references/boot-scripts/start-qa.sh` and `start-qa.ps1`
  2. Verify `SQUIDSQUAD_ROLE=qa` is set
  3. Verify `--dangerously-skip-permissions` flag is present
- **Expected**: Boot scripts follow the same pattern as other agent boot scripts. Set `SQUIDSQUAD_ROLE=qa`. Use `--dangerously-skip-permissions` per FEAT-SKILL-037 convention.
- **Verification**:
  ```bash
  grep "SQUIDSQUAD_ROLE=qa" references/boot-scripts/start-qa.sh
  grep "dangerously-skip-permissions" references/boot-scripts/start-qa.sh
  test -f references/boot-scripts/start-qa.ps1 && echo "PASS" || echo "FAIL"
  ```

#### TC-13: QA uses global loop interval from config.md
- **Precondition**: QA template created, config.md has `Iteration Interval > Minutes: 30`
- **Steps**:
  1. Read QA template's interval sync step (Step 1d equivalent)
  2. Verify it reads `Iteration Interval > Minutes` from config.md
  3. Verify it does NOT use a QA-specific interval
- **Expected**: QA reads the same global interval as all other agents. Uses Step 1d Interval Sync pattern to detect interval changes and re-schedule.
- **Verification**:
  ```bash
  grep "Iteration Interval\|Minutes\|config.md" references/sub-skills/roles/qa-agent.md
  ```

#### TC-14: Sub-skill manifest updated with QA role
- **Precondition**: Feature implemented, manifest.md modified
- **Steps**:
  1. Read `references/sub-skills/manifest.md`
  2. Verify QA role composition entry exists
- **Expected**: Manifest lists `qa-agent.md` as a role with its QA-specific sub-skill composition. Follows the same format as other role entries.
- **Verification**:
  ```bash
  grep -i "qa" references/sub-skills/manifest.md
  ```

#### TC-15: QA Discussion entries use `**qa**` signature
- **Precondition**: QA template created
- **Steps**:
  1. Read QA template for Discussion entry format
  2. Verify all QA entries use `**qa**` signature
- **Expected**: QA uses `> [YYYY-MM-DD HH:MM] **qa**: [message]` format for all Discussion entries. NOT `**pm/qa**` or `**qa-agent**`.
- **Verification**:
  ```bash
  grep '**qa**' references/sub-skills/roles/qa-agent.md
  # Should NOT use pm/qa:
  grep -c 'pm/qa' references/sub-skills/roles/qa-agent.md
  ```

#### TC-16: PM Discussion entries use `**pm**` signature (not `**pm/qa**`)
- **Precondition**: PM template updated
- **Steps**:
  1. Read PM template for Discussion entry format
  2. Verify PM entries use `**pm**` signature
- **Expected**: PM uses `> [YYYY-MM-DD HH:MM] **pm**: [message]` format. NOT `**pm/qa**`. Existing historical `**pm/qa**` entries in tracker files are NOT renamed.
- **Verification**:
  ```bash
  grep '**pm**' references/sub-skills/roles/pm-agent.md
  # New template should NOT reference pm/qa as a signature to use:
  grep -c 'pm/qa.*signature\|sign.*pm/qa' references/sub-skills/roles/pm-agent.md
  ```

#### TC-17: Setup recommends QA when adding dev/designer agent
- **Precondition**: Setup flow modified
- **Steps**:
  1. Read setup flow logic
  2. Verify QA recommendation appears after adding at least one dev or designer agent
- **Expected**: Setup prompts "Would you like to add a QA agent?" when a dev or designer agent is added. QA is recommended but not required.
- **Verification**:
  ```bash
  grep -i "QA agent\|recommend" references/sub-skills/roles/qa-agent.md || \
  grep -i "QA agent\|recommend" references/sub-skills/pm-specific/feature-intake.md || \
  grep -i "QA.*recommend" SKILL.md
  ```

#### TC-18: Config.md label changes from PM/QA to PM
- **Precondition**: Feature implemented, config schema updated
- **Steps**:
  1. Read config.md Agents section
  2. Verify `PM/QA` label is changed to `PM`
- **Expected**: Agents section lists `PM: always present` (not `PM/QA: always present`). QA presence is determined by directory existence (`.squidsquad/qa/`), matching the DM pattern.
- **Verification**:
  ```bash
  grep "PM/QA" .squidsquad/config.md && echo "FAIL (still PM/QA)" || echo "PASS"
  grep "**PM**" .squidsquad/config.md && echo "PASS" || echo "FAIL"
  ```

---

### Edge Cases

#### TC-19: QA with no Pending Test features or Fixed bugs (quiet cycle)
- **Precondition**: QA is running. No agent has Pending Test features or Fixed bugs.
- **Steps**:
  1. QA runs a cycle
  2. QA scans all agent trackers
  3. No actionable items found
- **Expected**: QA completes the cycle quietly. No iteration log created. No commit pushed. No errors. QA writes `idle|` to current-state.

#### TC-20: QA verifies designer work (not just dev)
- **Precondition**: Designer agent exists (`.squidsquad/designer/` directory present). Designer has a Pending Test feature.
- **Steps**:
  1. QA discovers designer via directory check
  2. QA reads `designer/features/INDEX.md`
  3. QA finds and verifies the Pending Test feature
- **Expected**: QA verifies designer features using the same flow as dev features. Designer test plans are read from `designer/planning/`. QA marks Pending Ship or sends back to In Progress.

#### TC-21: QA verification failure sends feature back to In Progress
- **Precondition**: Dev agent has a Pending Test feature. Test plan exists with test cases. One or more test cases fail.
- **Steps**:
  1. QA reads the feature and its TEST-PLAN.md
  2. QA executes test cases
  3. One or more test cases fail
  4. QA sets status back to `In Progress`
  5. QA appends Discussion entry with specific failures
- **Expected**: Status reverts to `In Progress`. Discussion entry lists the specific failing test cases. Dev agent picks up the fix on their next cycle. PM is NOT involved in the failure loop.

#### TC-22: QA verifies feature with no TEST-PLAN.md (legacy fallback)
- **Precondition**: Feature filed before intake process was added. No TEST-PLAN.md exists in planning directory. Feature has acceptance criteria in its feature file.
- **Steps**:
  1. QA reads feature file
  2. QA finds no TEST-PLAN.md
  3. QA falls back to verifying against acceptance criteria in the feature file
- **Expected**: QA does not error or skip the feature. QA verifies against the acceptance criteria listed in the feature file itself.

#### TC-23: Multiple dev agents with mixed states
- **Precondition**: Two dev agents (e.g., `skill` and `backend`). Skill has a Fixed bug, backend has a Pending Test feature.
- **Steps**:
  1. QA discovers both agents from config.md
  2. QA scans skill bugs (finds Fixed)
  3. QA scans backend features (finds Pending Test)
  4. QA verifies both in the same cycle
- **Expected**: QA handles items from multiple agents in a single cycle. Each item is verified against its own agent's trackers and planning artifacts. Status updates go to the correct agent's files.

#### TC-24: Race condition — PM and QA both exist during transition cycle
- **Precondition**: QA just added. PM has not yet pulled the updated template. Both run cycles simultaneously.
- **Steps**:
  1. PM (old template) attempts to verify a Pending Test feature
  2. QA also attempts to verify the same feature
  3. One succeeds first, changes status to Pending Ship
  4. The other reads the feature, sees it is no longer Pending Test
- **Expected**: Idempotent status transitions prevent double-marking. The second agent skips the item because it is no longer Pending Test. Discussion may have duplicate entries (harmless, append-only). After PM pulls updated template, overlap stops.

#### TC-25: QA context pressure exit mid-verification
- **Precondition**: QA is verifying a feature. Context usage exceeds threshold.
- **Steps**:
  1. QA detects context pressure at Step 1b equivalent
  2. QA saves working state (feature ID, completed test cases, remaining test cases)
  3. QA exits
  4. QA restarts with fresh context
  5. QA reads working-state.md and resumes
- **Expected**: Working state includes the feature ID, which test cases passed, and which remain. On resume, QA picks up where it left off without re-running passed test cases.

---

### Side Effect Regression Tests

#### TC-26: Dev agent templates unchanged
- **Precondition**: Feature implemented
- **Steps**:
  1. Read dev agent template (e.g., `references/sub-skills/roles/dev-agent.md`)
  2. Verify no changes to dev workflow
- **Expected**: Dev agents still mark features as `Pending Test` when done. Dev agents are unaware of whether QA or PM picks up verification. No changes to dev template required.
- **Verification**:
  ```bash
  # Dev template should still reference Pending Test as the handoff status:
  grep "Pending Test" references/sub-skills/roles/dev-agent.md
  ```

#### TC-27: DM template unchanged
- **Precondition**: Feature implemented
- **Steps**:
  1. Read DM template
  2. Verify DM still reads Pending Ship items regardless of who set the status
- **Expected**: DM template is unchanged. DM reads Pending Ship from agent trackers. DM does not care whether PM or QA set the status.

#### TC-28: PM delivery fallback still works when DM absent
- **Precondition**: QA marks feature Pending Ship. DM does not exist.
- **Steps**:
  1. QA marks feature Pending Ship
  2. PM runs cycle, DM absent
  3. PM's delivery fallback triggers on Pending Ship items
- **Expected**: PM picks up Pending Ship items via existing delivery fallback mechanism. The source of the status change (QA instead of PM) is transparent. PM handles delivery (docs, release, version bump) as before.

#### TC-29: Existing `**pm/qa**` Discussion entries preserved
- **Precondition**: Tracker files contain historical Discussion entries signed `**pm/qa**`
- **Steps**:
  1. After upgrade, read any tracker file with old `**pm/qa**` entries
  2. Verify entries are unchanged
- **Expected**: No bulk rename of existing entries. Historical `**pm/qa**` signatures are preserved as-is. Only NEW entries use the separated `**pm**` or `**qa**` signatures.
- **Verification**:
  ```bash
  # Old entries should still exist in tracker files:
  grep "pm/qa" .squidsquad/skill/bugs/*.md 2>/dev/null | head -3
  ```

#### TC-30: Feature intake Phase 5 removed from PM
- **Precondition**: PM template and feature-intake sub-skill updated
- **Steps**:
  1. Read `references/sub-skills/pm-specific/feature-intake.md`
  2. Verify Phase 5 (QA Test Execution subagent) is removed or noted as QA responsibility
- **Expected**: Phase 5 is no longer in the PM feature intake flow. A note indicates QA handles verification natively. PM's feature lifecycle ends at Phase 4 (planning/approval).
- **Verification**:
  ```bash
  grep -i "Phase 5\|QA.*natively\|QA handles" references/sub-skills/pm-specific/feature-intake.md
  ```

#### TC-31: Ship counter increment moved to QA
- **Precondition**: QA template includes bug close logic
- **Steps**:
  1. Read QA's bug verification step
  2. Verify QA increments `Shipped Since Last Bump` in config.md when closing a bug
- **Expected**: QA increments the ship counter on bug Close (same as PM did before). PM no longer increments it for bug closures.
- **Verification**:
  ```bash
  grep -i "Shipped Since Last Bump\|Ship.*counter\|increment" references/sub-skills/qa-specific/verify-bugs.md
  ```

---

### Upgrade Verification Tests

#### TC-32: Upgrade detects QA via directory existence
- **Precondition**: `/squidsquad-upgrade` run on a project without QA
- **Steps**:
  1. Run upgrade flow
  2. Upgrade checks for `.squidsquad/qa/` directory
  3. Directory does not exist — upgrade prompts to add QA
- **Expected**: Upgrade detects QA absence via directory check (not config.md field). Prompts user to add QA. If user declines, PM template remains unchanged (full PM/QA behavior).

#### TC-33: Upgrade creates QA directory structure
- **Precondition**: User accepts QA agent during upgrade
- **Steps**:
  1. User chooses to add QA
  2. Upgrade creates `.squidsquad/qa/` with subdirectories and files
  3. Upgrade creates boot scripts
  4. Upgrade regenerates PM template (lean version)
- **Expected**: Full QA directory structure created. Boot scripts created. PM template recomposed without verification steps. config.md `PM/QA` renamed to `PM`.

#### TC-34: Upgrade preserves PM behavior when QA declined
- **Precondition**: User declines QA during upgrade
- **Steps**:
  1. User declines QA
  2. Upgrade leaves PM template unchanged
- **Expected**: PM template retains all verification steps. No `.squidsquad/qa/` directory created. System behaves identically to pre-upgrade.

---

## Smoke Tests

- [ ] `references/sub-skills/roles/qa-agent.md` exists
- [ ] `references/sub-skills/qa-specific/` directory exists with sub-skill files
- [ ] `references/boot-scripts/start-qa.sh` exists and contains `SQUIDSQUAD_ROLE=qa`
- [ ] `references/boot-scripts/start-qa.ps1` exists
- [ ] PM template does NOT contain E2E test execution steps
- [ ] PM template does NOT contain bug verification steps
- [ ] PM template does NOT contain feature verification (Pending Test -> Pending Ship) steps
- [ ] PM template "must never do" list includes verification activities
- [ ] QA template references config.md for agent discovery
- [ ] QA template uses `**qa**` Discussion signature (not `**pm/qa**`)
- [ ] PM template uses `**pm**` Discussion signature (not `**pm/qa**`)
- [ ] `references/sub-skills/manifest.md` includes QA role entry
- [ ] QA directory structure: `qa/qa-log.md`, `qa/iterations/`, `qa/current-state`, `qa/working-state.md`
- [ ] QA has NO `bugs/` or `features/` directories of its own
- [ ] Old `pm/qa-log.md` is preserved (not deleted or moved)
- [ ] Config.md Agents section says `PM` (not `PM/QA`)

---

## Regression Risks

- **PM accidentally retaining verification steps**: If the PM template is not fully reduced, PM and QA will both attempt verification, causing duplicate Discussion entries and wasted cycles. Watch for: PM template still containing "E2E", "Verify Fixed", "Verify Pending Test", or "Health Check" steps.
- **QA missing an agent's tracker**: If QA's agent discovery does not match PM/DM's discovery mechanism, some agents' work may never be verified. Watch for: QA only checking the first dev agent, skipping designer, or hardcoding agent names.
- **Discussion signature mismatch**: If QA uses a different signature format than `**qa**`, grep patterns and other agents that parse Discussion entries may break. Watch for: `**qa-agent**`, `**QA**`, or continued use of `**pm/qa**` in new entries.
- **DM not receiving Pending Ship items**: If QA writes the status transition differently than PM did, DM may not detect Pending Ship items. Watch for: different status string casing, missing INDEX.md regeneration after status change.
- **Delivery fallback broken by signature change**: PM's delivery fallback triggers on Pending Ship items. If the PM template now expects QA's signature format in Discussion entries to detect readiness, it may miss items. Watch for: PM filtering by Discussion author instead of just by Status field.
- **Sub-skill composition engine failure**: QA is the first new role added under the FEAT-SKILL-030 architecture. If the composition engine has edge cases with the QA role name or QA-specific includes, the template may not generate correctly. Watch for: unresolved placeholders, missing include content, duplicate sections.
- **Boot script path errors**: New boot scripts must reference the correct working directory and template paths. Watch for: Windows vs Unix path issues in start-qa.ps1 vs start-qa.sh.
- **Ship counter double-increment**: If both PM (via fallback) and QA both attempt to increment `Shipped Since Last Bump`, the counter drifts. Watch for: PM still incrementing on bug close when QA exists.
- **Phase 5 orphaned in PM**: If Phase 5 is not fully removed from the PM feature intake sub-skill, PM may still attempt to spawn a QA subagent even when QA exists as an independent agent. Watch for: PM template referencing Phase 5 or QA subagent execution.
- **Config.md counter collisions**: If QA files bugs to dev agent trackers and increments BUG counters, and a dev agent also increments counters in the same cycle, counter values can collide. Watch for: duplicate bug IDs. Mitigation: pull-before-push discipline and counter read-at-use-time.

### Steps 3–6 — Testing & Verification (QA Fallback)

**QA presence check**: If `.squidsquad/qa/` directory exists and a QA agent is running (check `current-state` file exists), QA handles all testing and verification independently. Skip Steps 3–6 entirely and print: `[🦑 HH:MM:SS] QA agent present — skipping verification (QA handles it).`

If QA is **not installed** (`.squidsquad/qa/` does not exist), PM falls back to combined PM/QA duties for Steps 3–6 below.

---

#### Step 3 — Run E2E Tests

Print: `[🦑 HH:MM:SS] Running E2E tests...` (or `[🦑 HH:MM:SS] No E2E command — skipping tests.`)

If `E2E Tests` is configured in `config.md`, run: `[E2E_TEST_CMD]`

If no E2E command is configured, skip this step.

Log results in `pm/qa-log.md`:

```markdown
## QA Run — YYYY-MM-DD HH:MM

- **Result**: Passed | Failed | Skipped (no E2E command)
- **Tests Run**: [N]
- **Failures**: [list failing test names, or "none"]
- **Notes**: [anything notable]
```

#### Step 4 — Investigate and Present Issues From Test Failures

Print: `[🦑 HH:MM:SS] Investigating test failures...` (or skip if no failures)

For each test failure:

1. Determine which agent's domain the failure is in.
2. Check if an issue for this failure already exists (search by keywords). If yes, append a Discussion note — do not duplicate.
3. If new: **use the Issue Discussion Flow** (same as Step 2):
   - **Investigate** the root cause — read relevant code, understand why the test failed, identify possible fixes.
   - **Present** the failure analysis, root cause, and proposed fix to the human.
   - **Wait for approval** before filing. If the human approves, file the issue with the agreed-upon fix approach in Description or Discussion. Increment the appropriate counter in `config.md`.
   - **Non-blocking**: If the human doesn't respond, note "awaiting human input on fix approach for [test failure description]" in your working state and continue the loop. Revisit next cycle.
4. If the failure spans multiple domains: investigate once, present once, and after approval file in each relevant tracker with cross-linking Discussion notes.

#### Step 5 — Verify Fixed Issues

Print: `[🦑 HH:MM:SS] Verifying fixed issues...`

Query GitHub Issues for issues pending verification:

```bash
python references/scripts/tracker.py list-issues skill --status pending-test
```

For each result:

1. Run the relevant test or manually verify the fix.
2. **Test coverage check**: Verify that the fix includes a regression test. Check for new or modified test files corresponding to the changed code. If the fix adds or changes code but includes no tests, reject it.
3. **Run the full test suite**: `python tests/run_tests.py` — all tests must pass.
4. If verified (fix works, regression test exists, all tests pass):
   - Update status to `Verified`, then `Closed`.
   - Append Discussion entries for each transition.
5. If not verified (fix doesn't work, no regression test, or tests fail):
   - Update status back to `Open`.
   - Append a Discussion entry explaining what failed — be specific about missing tests.

#### Step 6 — Verify Pending Test Tasks

Print: `[🦑 HH:MM:SS] Verifying pending test tasks...`

Query GitHub Issues for tasks pending test:

```bash
python references/scripts/tracker.py list-tasks skill --status pending-test
```

For each result:

1. Test against the acceptance criteria.
2. **Test coverage check**: Verify that new code has corresponding unit tests. Check for new or modified test files. If the implementation adds new functions, scripts, or modules but includes no tests, reject it — tests are part of the implementation, not follow-up work.
3. **Run the full test suite**: `python tests/run_tests.py` — all tests must pass.
4. **Zero-gap gate**: If ANY gap, ambiguity, missing documentation, failed check, missing test coverage, or unresolved finding is discovered — update back to `In Progress` and append a Discussion entry listing every specific finding. Do NOT mark Pending Ship with "gaps noted for follow-up." ALL findings must be resolved before shipping.
3. **Only exception**: The human explicitly says "ship with these gaps" — record the override in Discussion: `> [YYYY-MM-DD HH:MM] **pm**: Human override — shipping with [N] noted gaps: [list]. Status → Pending Ship.`
4. If all criteria pass with zero gaps: update to `Pending Ship`, append Discussion entry: `> [YYYY-MM-DD HH:MM] **pm**: Verified — zero gaps. Status → Pending Ship.`
5. **delivery:skip check**: If the task is internal-only (agent template changes, config changes, internal tooling, process improvements) with no user-facing delivery work needed, add `delivery: skip` to the Discussion entry when marking Pending Ship: `> [YYYY-MM-DD HH:MM] **pm**: Verified — zero gaps. delivery: skip (internal-only, no user-facing changes). Status → Pending Ship.` This tells the DM (or PM fallback) to skip delivery packaging and mark the task Shipped immediately.
6. If criteria fail: update back to `In Progress`, append Discussion entry with specific failures.

#### Step 6c — Increment Ship Counter for Closed Issues

When marking any issue as `Closed` in Step 5, increment the `Shipped Since Last Bump` counter in `config.md`. If DM is present, it handles version bumps. If DM is absent, PM handles version bumps in Step 6d.

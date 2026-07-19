---
slot: instructions
ordinal: 20
roles: [verifier]
---

### Step 2 — Run E2E Tests

Print: `[🦑 HH:MM:SS] Running E2E tests...` (or `[🦑 HH:MM:SS] No E2E command — skipping tests.`)

If `E2E Tests` is configured in `config.md`, run: `[E2E_TEST_CMD]`

If no E2E command is configured, skip this step.

Log results in `qa/qa-log.md`:

```markdown
## Verifier Run — YYYY-MM-DD HH:MM

- **Result**: Passed | Failed | Skipped (no E2E command)
- **Tests Run**: [N]
- **Failures**: [list failing test names, or "none"]
- **Notes**: [anything notable]
```

### Step 3 — Investigate and Route Findings

Print: `[🦑 HH:MM:SS] Investigating test failures...` (or skip if no failures)

For each finding (test failure, gap, or defect discovered during verification): classify it, check for duplicates, document it with structured Finding/Evidence/Category/Routed-to evidence, then file it (or escalate/flag per its category) — → run sub-skill: `roles/verifier/verification-findings` for the full 4-step process (classify → dedup-check → document+file → record-on-PR).

### Step 4 — Verify Fixed Issues

Print: `[🦑 HH:MM:SS] Verifying fixed issues...` (skip if no `type:issue` bugs are pending test — this is a separate flow from Step 5's task verification)

→ run sub-skill: `roles/verifier/verification-issue-flow` for the full per-issue verification procedure (branch checkout, vault consult, test coverage check, full suite run, transition to pending-ship or back to in-progress).

### Step 5 — Verify Pending Test Tasks

Print: `[🦑 HH:MM:SS] Verifying pending test tasks...`

Query all tasks pending test:

```bash
python references/scripts/tracker.py list-tasks skill --status pending-test
```

(Adjust role as needed for other agents.)

For each task:

0. **Blocked check**: If the item has a `blocked:human-action` label, skip it. Print: `[🦑 HH:MM:SS] Skipping #[NUMBER] — blocked:human-action (waiting for human).` Do not change its status. Move to the next item.

Read it: `gh issue view [NUMBER] --json title,body,labels,comments`

**Branch checkout** (#3296): Check out the task's feature branch before testing:
```bash
python references/scripts/git_ops.py task-begin [role] [number]
```
When verification is complete (pass or fail), return to working branch:
```bash
python references/scripts/git_ops.py task-end [role] [number]
```

1. **Verifier produces the test plan from the AC list** (#9184). PM does not produce a test plan; Verifier is the verification owner. **Before exercising the implementation**, derive the test plan from the issue body's Acceptance Criteria + the locked CONTEXT artifact (if any) and write it to `.squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-<NUMBER>.md`. The test plan must be derivable from the AC list alone — do not reverse-engineer test cases from worker's diff. Running worker's unit tests is a sanity check only — not the gate.

   Resume logic mirrors PM's: if `TEST-PLAN-<NUMBER>.md` already exists under `.squidsquad/[VERIFIER_ALIAS]/planning/` and the issue body's ACs have not changed since the file was committed, reuse it; otherwise re-derive.

   → run sub-skill: `roles/verifier/verification-templates` for the TEST-PLAN.md structure template, the optional `model_router.py` test-plan-drafting route, and the Verifier-subagent prompt that turns it into executable pytest assertions — skip if reusing per the resume logic above (most cycles reuse an existing, unchanged TEST-PLAN-<NUMBER>.md and never need this file).

   Verifier reviews QA-RESULTS-<NUMBER>.md and makes the final decision.

1b. **Comprehension testing** (if verifier's TEST-PLAN-<NUMBER>.md has a `## Comprehension Questions` section — applies when the task touches LLM-consumed instructions): spawn a comprehension agent (via the Agent tool) with a neutral, file-scoped prompt: "Read the following files and answer ONLY from what you find in them. Files: [list modified files]. Answer each question below, quoting file content." **Adaptive spawning**: one agent per sub-skill group if 4+ affected, otherwise single spawn. Record results in QA-RESULTS-<NUMBER>.md under `## Comprehension Tests` with per-CQ PASS/FAIL entries — a comprehension failure is a legitimate finding. Skip this step if TEST-PLAN-<NUMBER>.md has no Comprehension Questions section.

2. **Worker unit tests are a sanity check, not the gate** (#9184). Inspect worker's unit tests under `tests/` for the changed area. Running them as a sanity check is fine, but verifier's gate is the live-system execution of `TEST-PLAN-<NUMBER>.md` above. Coverage gaps in worker's unit tests are a separate finding routed back to worker — do not skip verifier's live execution because worker's tests pass.

2b. **Test coverage check** (always runs): Verify worker's PR includes unit tests for new code per the worker workflow (#9184). If the implementation adds new functions, scripts, or modules but the PR ships with no unit tests AND no explicit "no testable surface" justification, reject — tests are part of the implementation, not follow-up work.

2c. **Run the full test suite**: `python tests/run_tests.py` — all tests must pass.

2d. **AC walk against the issue body's Acceptance Criteria** (#8950 Gate #3, updated by #9184) — before marking any task `pending-test → pending-ship`, walk each AC in the **GitHub issue body**. For each AC:

   - Confirm it is **observably satisfied** by the implementation — run the verification command stated in the AC, check the file the AC names, or observe the output the AC describes. **Tests passing is necessary but not sufficient — do not infer AC satisfaction from test names.**
   - Use verifier's own `TEST-PLAN-<NUMBER>.md` coverage matrix to cross-check that every AC has at least one TC mapped to it (primary source; a legacy `.squidsquad/[PM_ALIAS]/planning/` `TEST-PLAN` fallback exists only for in-flight tasks filed pre-#9184 — do not author new files at that path).

   If any AC is not observably satisfied, transition `pending-test → in-progress` and comment which AC failed:

   ```bash
   python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role verifier-lead
   python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "AC walk failed: AC-[N] from the issue body is not observably satisfied — [what was checked and what failed]. Status → In Progress."
   ```

3. **Zero-gap gate**: If ANY gap, ambiguity, missing documentation, failed check, missing test coverage, or unresolved finding is discovered:
   ```bash
   python references/scripts/tracker.py transition [NUMBER] pending-test in-progress --role verifier-lead
   python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "FAIL. [list every specific finding]. Back to In Progress."
   ```
   Also, if PR Flow is enabled and a PR exists for this issue, post the failure on the PR and request changes (`roles/verifier/verification-ship-flow`'s failure-path shows the exact commands — that pointer is also reachable from Step 5's post-verdict section below, but this gate fires before a verdict is ever posted).
   Do NOT mark Pending Ship with "gaps noted for follow-up." ALL findings must be resolved before shipping.
4. **Only exception**: The human explicitly says "ship with these gaps" — record the override:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "Human override — shipping with [N] noted gaps: [list]. Status → Pending Ship."
   ```
5. If all criteria pass with zero gaps:

   **5a. Post the forge-visible VERIFY verdict to the ISSUE FIRST (#13464) — MANDATORY, ordered.** Before promoting tests, touching the PR, merging, or transitioning, post the PASS verdict as a comment on the **GitHub issue** (via `tracker.py`, not only on the PR) so the verdict is always discoverable on the forge. The DM ship-gate and any teammate must be able to confirm the PASS from the **issue alone** — never from your private-clone `QA-RESULTS-<NUMBER>.md` (which is NOT committed to origin/main and so is invisible to a DM without local cross-clone access; a non-forge-visible verdict blocks a genuinely-passing item at the ship-gate or forces an unverified ship):
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role verifier-lead --message "VERIFY #[NUMBER] PASS -> pending-ship. AC walk: [AC-1 … AC-N, each PASS with the observed evidence]. Tests: [N/N passed]. QA-RESULTS-[NUMBER].md recorded (private clone)."
   ```
   This issue verdict comment is a **hard precondition** of the `pending-test → pending-ship` transition below — never transition to pending-ship without a preceding forge-visible PASS verdict comment on the **issue**. (The PR-side `## Verifier Results` comment and the post-merge confirmation comments are additional, not a substitute — the PR can be squashed/closed and is not the item's forge record.)

   → run sub-skill: `roles/verifier/verification-ship-flow` for everything after the verdict comment — promoting test files, the PR Flow yes/no branching, auto-merge vs human-review routing, merge-conflict handling, and Step 5b's PR-monitoring loop. (The file's failure-path PR comment/request-changes commands are also what sub-step 3's zero-gap gate above points to — that gate is the far more common way a verifier reaches this section.)

### Step 6 — Agent Health Check

Print: `[🦑 HH:MM:SS] Checking agent health...`

Run the deterministic health check script — the same one PM's own health-check step calls (#13565: this step used to hand-roll the identical `.claude-pid`/`current-state`-mtime algorithm in prose; two independently-maintained descriptions of the same liveness check is a drift risk the script already eliminates for PM):

```bash
python references/scripts/health_check.py --json
```

Parse each entry's `health` field. Log the run in `qa/qa-log.md`. For any agent whose `health` is `"stalled"` or `"unknown"`: find that agent's latest open tracker item with `python references/scripts/tracker.py list-tasks [ROLE] --status open` (take the most recent), then append a Discussion note to it (`> [YYYY-MM-DD HH:MM] **verifier**: Agent [role] appears stalled — [elapsed]. Please check.`); if no open item exists, log in `qa-log.md` only.

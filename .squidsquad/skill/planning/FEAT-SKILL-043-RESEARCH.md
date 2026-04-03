# FEAT-SKILL-043 Research — Separate QA from PM into Independent Role

## Summary

This research analyzes splitting the current combined PM/QA agent into two independent roles: PM (human interface + coordination) and QA (verification across all agents). The revised pipeline is: Human -> PM (intake, planning, discussions) -> Dev/Designer (build) -> QA (verify) -> DM (docs, release) -> Ship.

The current PM template (~330 lines of entry file plus ~280 lines of included sub-skills) mixes two fundamentally different workloads: (1) human-facing coordination (check-ins, feature intake, backlog management) and (2) file-intensive verification (QA passes, bug verification, feature testing, agent health checks). The verification work consumes significant context reading agent trackers, planning artifacts, and code files. Separating these allows each agent to operate with a focused context window and independent loop interval.

The split is feasible and well-aligned with the existing sub-skill architecture (FEAT-SKILL-030). QA would be built as a new role under `references/sub-skills/roles/qa-agent.md` with QA-specific sub-skills. The main complexity is in the handoff points (PM -> Dev/Designer -> QA -> DM) and ensuring the fallback path works when QA is absent.

Recommendation: **Feasible with caveats** — the split is architecturally clean, but requires careful attention to status transition ownership, the QA-absent fallback, and migration of existing installs.

## Impact Analysis

- **Files touched**:
  - NEW: `references/sub-skills/roles/qa-agent.md` (QA entry template)
  - NEW: `references/sub-skills/qa-specific/` directory with sub-skills
  - NEW: `references/boot-scripts/start-qa.sh`, `start-qa.ps1`
  - MODIFIED: `references/sub-skills/roles/pm-agent.md` (remove QA steps)
  - MODIFIED: `references/sub-skills/pm-specific/feature-intake.md` (Phase 5 moves to QA)
  - MODIFIED: `references/sub-skills/pm-specific/delivery-fallback.md` (triggered by QA, not PM self-verify)
  - MODIFIED: `references/sub-skills/manifest.md` (add QA role composition)
  - MODIFIED: `config.md` schema (add QA agent section)
  - MODIFIED: Setup flow (recommend QA when dev/designer added)
  - MODIFIED: Upgrade flow (add QA to existing installs)
  - MODIFIED: Statusline (show QA agent health)
  - MODIFIED: `SKILL.md` (document QA role)
- **Behavior changes**:
  - PM no longer runs Steps 3, 4, 5, 6, 7 (E2E tests, bug investigation, bug verification, feature verification, health checks)
  - PM's Ralph Loop becomes: Pull -> Check-in -> Feature Intake -> PR Monitor -> Delivery Fallback -> Log -> Commit
  - QA gains its own Ralph Loop: Pull -> Verify Bugs -> Verify Features -> E2E Tests -> Health Checks -> Log -> Commit
  - Status transition `Pending Test -> Pending Ship` moves from PM to QA
  - Status transition `Fixed -> Verified -> Closed` moves from PM to QA
  - QA hands off to DM (not back to PM) for delivery
- **Dependencies**: FEAT-SKILL-030 (sub-skill architecture) must be complete — it is (Architecture Version 1 exists in config). FEAT-SKILL-027 (designer) is referenced but not blocking.

## 1. PM Template Reduction

### What stays with PM

| Responsibility | Current PM Step | Notes |
|---|---|---|
| Human check-ins | Step 2 | Core PM identity — no change |
| Feature intake (Phases 1-3) | Feature Lifecycle | Research, Discussion, Planning — stays entirely with PM |
| Feature approval gate | Feature Approval Gate | PM + human decide, never QA |
| Backlog management | Step 2 (priority changes) | Enhancements.md stays with PM |
| Bug Discussion Flow | Step 2 (human reports bug) | PM investigates WITH human, files bug after human approves approach |
| PR monitoring | Step 6b | Reads PR status, updates trackers — coordination work |
| Delivery fallback | Step 6d | When DM absent, PM takes over DM delivery — preserved |
| GitHub Issues ingestion | Step 7b | External intake is PM's job |
| DM fallback for delivery | Step 6d | PM takes over DM's delivery role when DM absent |
| Version bump (when DM absent) | Step 6d | Part of delivery fallback |

### What moves to QA

| Responsibility | Current PM Step | QA Step |
|---|---|---|
| E2E test execution | Step 3 | QA Step 2 |
| Bug investigation from test failures | Step 4 | QA Step 3 |
| Bug verification (Fixed -> Verified -> Closed) | Step 5 | QA Step 4 |
| Feature verification (Pending Test -> Pending Ship) | Step 6 | QA Step 5 |
| Phase 5 QA subagent execution | Feature Intake Phase 5 | QA Step 5 (native, no subagent needed) |
| Agent health checks | Step 7 | QA Step 6 |
| Ship counter increment for closed bugs | Step 6c | QA Step 4 (on bug close) |
| Filing bugs from QA findings | Step 4 | QA Step 3 |
| QA log writing | Steps 3-7 | QA owns qa-log.md |

### PM Ralph Loop after split

```
Step 1  — Pull Latest (unchanged)
Step 1b — Context Pressure Check (unchanged)
Step 1c — Resume From Working State (unchanged)
Step 2  — Check In With Human (unchanged — still handles bug reports via Bug Discussion Flow, feature requests, priority changes)
Step 3  — Feature Intake Processing (run pending intake phases — was implicit in Step 2/6)
Step 4  — Monitor PRs (was Step 6b — if PR Flow enabled)
Step 5  — Delivery Fallback (was Step 6d — when DM absent, handle Pending Ship items)
Step 6  — Log Iteration (was Step 8)
Step 7  — Commit and Push (was Step 9)
Step 8  — Done (was Step 10)
```

Key change: PM's loop drops from 10 steps to 8, and the heaviest steps (E2E tests, verification, health checks) are gone entirely. PM becomes a lean coordination agent.

### PM "must never do" additions

- Never verify bugs or features — QA does this
- Never run E2E tests — QA does this
- Never mark bugs as Verified/Closed — QA does this
- Never mark features as Pending Ship — QA does this

## 2. QA Agent Template Design

### QA Ralph Loop

```
Step 1  — Pull Latest
Step 1b — Context Pressure Check
Step 1c — Resume From Working State
Step 1d — Interval Sync
Step 2  — Run E2E Tests
          If E2E command configured in config.md, run it.
          Log results in qa/qa-log.md.
Step 3  — Investigate and File Bugs From Test Failures
          For each failure: identify domain, check for duplicates,
          file bug to correct agent tracker. QA files bugs directly
          (no human approval needed for test-discovered bugs, unlike
          PM's Bug Discussion Flow which requires human approval).
Step 4  — Verify Fixed Bugs
          Read each agent's bugs/INDEX.md. For Fixed bugs:
          - Run relevant test or manual verification
          - Verified -> Closed (with Discussion entries)
          - Or back to Open if not fixed
          - Increment Shipped Since Last Bump on Close
Step 5  — Verify Pending Test Features
          Read each agent's features/INDEX.md. For Pending Test:
          - Read TEST-PLAN.md from planning/ directory
          - Execute test cases (QA does this natively, no subagent)
          - All pass: mark Pending Ship + Discussion entry
          - Any fail: mark In Progress + Discussion with failures
          - Apply delivery:skip logic for internal-only features
Step 6  — Agent Health Check
          Read .local-config for clone paths. Check current-state
          mtime for each agent. Log stalled agents.
Step 7  — Log Iteration (skip on quiet cycles)
          Write qa/iterations/iter-N.md
Step 8  — Commit and Push (skip on quiet cycles)
Step 9  — Done
```

### How QA reads test plans

QA reads test plans from the same location dev agents read planning artifacts: `.squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-TEST-PLAN.md`. These are produced by PM during Phase 3 of the Feature Intake Process. QA needs read access to ALL agent planning directories.

For features without a TEST-PLAN.md (legacy features filed before the intake process was added, or light-mode features), QA falls back to verifying against the acceptance criteria listed in the feature file itself.

### How QA hands off to DM

When QA marks a feature `Pending Ship`:
1. QA updates the feature's Status field to `Pending Ship`
2. QA appends Discussion entry: `> [YYYY-MM-DD HH:MM] **qa**: All test cases pass (N/N). Status -> Pending Ship.`
3. QA regenerates the agent's features/INDEX.md
4. QA commits and pushes
5. DM picks up `Pending Ship` items on its next cycle (DM already does this — no change to DM template)

If DM is absent, PM picks up `Pending Ship` items via the existing delivery fallback (Step 6d in current PM template, which becomes Step 5 in the reduced PM template).

### QA's directory structure

```
.squidsquad/qa/
├── current-state          (atomic status for statusline)
├── working-state.md       (context persistence)
├── qa-log.md              (E2E test results, QA findings)
├── iterations/
│   └── iter-N.md          (cycle logs)
```

QA does NOT get its own bugs/ or features/ directories. QA reads and writes to dev agent trackers (same pattern as PM and DM). QA's own operational issues are logged in qa-log.md.

### QA's Discussion signature

All QA Discussion entries use: `> [YYYY-MM-DD HH:MM] **qa**: [message]`

This replaces the current `**pm/qa**` signature. PM's signature becomes just `**pm**`.

### QA working state

Same format as other agents. Persists the current verification task so QA can resume after context pressure exit.

## 3. Pipeline Handoff Points

### Status lifecycle with QA

```
Pending -> Planning -> Approved -> In Progress -> Pending Test -> Pending Ship -> Shipped
  PM         PM         PM         Dev/Designer     QA              DM            DM
                                                                   (or PM fallback)
```

### Handoff detail

| Transition | Who does it | Who picks up next |
|---|---|---|
| Pending -> Planning | PM (after human approval) | PM (runs intake) |
| Planning -> Approved | PM (after phases 1-3 complete) | Dev or Designer |
| Approved -> In Progress | Dev/Designer (picks up) | Dev/Designer (implements) |
| In Progress -> Pending Test | Dev/Designer (implementation done) | QA |
| Pending Test -> Pending Ship | QA (verification passes) | DM (or PM fallback) |
| Pending Test -> In Progress | QA (verification fails) | Dev/Designer (fix issues) |
| Pending Ship -> Shipped | DM (delivery done) | Terminal |
| Fixed -> Verified -> Closed | QA | Terminal (bug lifecycle) |
| Fixed -> Open | QA (verification fails) | Dev/Designer (re-fix) |

### Where QA reads from

QA must scan ALL dev agent trackers plus the designer tracker (if present):
- `.squidsquad/[each-dev-role]/bugs/INDEX.md` — for Fixed bugs
- `.squidsquad/[each-dev-role]/features/INDEX.md` — for Pending Test features
- `.squidsquad/[each-dev-role]/planning/FEAT-*-TEST-PLAN.md` — for test plans
- `.squidsquad/designer/bugs/INDEX.md` — if designer exists
- `.squidsquad/designer/features/INDEX.md` — if designer exists

QA discovers active agents from `config.md` (Dev Agents list) plus checking for `.squidsquad/designer/` directory.

### QA failure path

When QA fails a feature:
1. QA sets status back to `In Progress` on the feature
2. QA appends Discussion entry with specific test case failures
3. The dev/designer agent reads the Discussion on their next cycle and picks up the fix
4. PM is NOT involved in the failure loop — QA communicates directly with dev/designer via Discussion

This avoids a round-trip through PM and keeps the failure loop tight.

## 4. Setup Flow Changes

### When to recommend QA

During setup, after the user adds at least one dev agent or a designer agent:
```
"Would you like to add a QA agent? QA independently verifies work from all dev and designer agents.
Recommended: yes (separate verification from PM coordination)
[Yes (recommended)] [No — PM handles QA]"
```

### QA setup creates

- `.squidsquad/qa/` directory structure
- Boot script: `start-qa.sh` / `start-qa.ps1`
- Template: composed from `references/sub-skills/roles/qa-agent.md` + QA-specific sub-skills
- Config entry: QA agent listed (new section or under a new config key)

### Config.md changes

Current:
```markdown
## Agents
- **Dev Agents**: skill
- **PM/QA**: always present
```

Proposed:
```markdown
## Agents
- **Dev Agents**: skill
- **PM**: always present
- **QA**: present | absent
```

Or alternatively, keep QA presence implicit via directory existence (`.squidsquad/qa/` exists = QA is active), matching the DM pattern. This is cleaner and avoids a config value that can get out of sync with the actual directory state.

**Recommendation**: Use directory existence (matching DM pattern). QA is present if `.squidsquad/qa/` exists. No config.md entry needed beyond renaming `PM/QA` to `PM`.

### Boot script

`start-qa.sh` / `start-qa.ps1` follows the same pattern as other boot scripts:
- Sets `SQUIDSQUAD_ROLE=qa`
- Launches Claude Code with the QA template
- Uses `--dangerously-skip-permissions` (matching other boot scripts per FEAT-SKILL-037)

## 5. Migration from PM/QA Combined to Separate

### File ownership changes

| File | Current Owner | New Owner | Notes |
|---|---|---|---|
| `pm/qa-log.md` | PM | QA (`qa/qa-log.md`) | QA creates its own; PM's old one becomes read-only history |
| `pm/enhancements.md` | PM | PM | Backlog management stays with PM |
| `pm/iterations/` | PM | PM | PM keeps its own iteration logs |
| `pm/working-state.md` | PM | PM | PM keeps its own working state |
| `pm/current-state` | PM | PM | PM keeps its own status |

New files for QA:
- `qa/qa-log.md` — QA test results and findings
- `qa/iterations/iter-N.md` — QA cycle logs
- `qa/working-state.md` — QA context persistence
- `qa/current-state` — QA statusline state

### Discussion signature migration

- Current: `**pm/qa**` for all entries
- New: `**pm**` for PM entries, `**qa**` for QA entries
- Existing `**pm/qa**` entries are preserved as-is (historical accuracy)
- No bulk rename needed — old entries keep their original signature

### PM template changes

The PM template (`roles/pm-agent.md`) removes:
- Step 3 (Run E2E Tests) — entire step
- Step 4 (Investigate and Present Bugs From Test Failures) — entire step
- Step 5 (Verify Fixed Bugs) — entire step
- Step 6 (Verify Pending Test Features) — entire step (but keep Step 6b PR monitoring and Step 6d delivery fallback)
- Step 6c (Ship counter for closed bugs) — moves to QA
- Step 7 (Agent Health Check) — entire step
- Phase 5 (QA Test Execution subagent) from feature-intake.md — QA does this natively

The PM template adds:
- Explicit "QA absent" fallback logic: if `.squidsquad/qa/` does not exist, PM runs verification steps (current behavior preserved)
- Updated "must never do" list

### Sub-skill file changes

| Sub-skill | Change |
|---|---|
| `pm-specific/feature-intake.md` | Phase 5 removed (QA handles natively). Add note: "Phase 5 verification is performed by QA agent." |
| `pm-specific/delivery-fallback.md` | No change — still triggered by Pending Ship items, still PM's fallback when DM absent |
| `pm-specific/pr-flow.md` | No change — stays with PM |
| `pm-specific/github-issues.md` | No change — stays with PM |
| `pm-specific/feature-approval.md` | No change — stays with PM |

New sub-skills:
| Sub-skill | Content |
|---|---|
| `qa-specific/verify-bugs.md` | Bug verification logic (from PM Step 5) |
| `qa-specific/verify-features.md` | Feature verification logic (from PM Step 6, including Phase 5 test execution) |
| `qa-specific/e2e-tests.md` | E2E test execution and bug filing (from PM Steps 3-4) |
| `qa-specific/health-checks.md` | Agent health check logic (from PM Step 7) |

## 6. Edge Cases

### No QA agent (fallback)

If `.squidsquad/qa/` does not exist, PM must preserve current behavior — running verification steps itself. This is implemented as a conditional block in the PM template:

```
### Step 3 — Verification (QA Fallback)
If `.squidsquad/qa/` directory does NOT exist, PM runs the full verification suite:
- E2E tests, bug verification, feature verification, health checks
(Same as current PM Steps 3-7)

If `.squidsquad/qa/` exists, skip this step entirely — QA handles verification.
```

This keeps the PM template slightly larger than the "pure PM" version but ensures backward compatibility. The fallback block can be a sub-skill (`pm-specific/qa-fallback.md`) that includes the verification steps conditionally.

### QA workload overflow

Detection signals:
- QA context pressure exits frequently (more than 2x per cycle)
- QA cycle time consistently exceeds iteration interval
- Growing backlog of `Pending Test` features not getting verified
- QA working-state.md always has an active task (never idle)

Recommendation mechanism: QA logs a warning in qa-log.md when it detects persistent backlog. PM surfaces this to the human during check-in. Human decides whether to add a second QA agent.

For a second QA agent, the system would need domain-based partitioning (QA-1 handles agents A,B; QA-2 handles agents C,D). This is out of scope for the initial implementation but should be designed so the template supports it (QA reads its assigned agents from config or a local config).

### Race condition: PM and QA both try to verify

This can happen during the fallback transition — QA is added but PM hasn't pulled the updated template yet. Mitigations:

1. **Directory-based gating**: PM checks for `.squidsquad/qa/` at the start of each cycle. If QA exists, PM skips verification. Since git pull happens at Step 1, PM will see the QA directory after one cycle.
2. **Idempotent status transitions**: If both PM and QA try to verify the same feature, the second one will see the status has already changed (not `Pending Test` anymore) and skip it. Discussion entries are append-only, so duplicate entries are harmless.
3. **One-cycle overlap**: In the worst case, there's one cycle of overlap where both verify. The status check at verification time prevents double-transitions.

### Designer verification

QA verifies designer work the same way it verifies dev work:
1. Read the designer's features/INDEX.md for `Pending Test` items
2. Read the TEST-PLAN.md (produced by PM during intake)
3. Execute test cases — for design specs, this means:
   - Verify the spec exists at the expected path
   - Verify it contains required sections (tokens, components, layout)
   - Verify feasibility assessment is present
   - Cross-reference with dev implementation if the feature has both design and code components
4. Mark Pending Ship or send back to In Progress

Designer bugs follow the same Fixed -> Verified -> Closed flow as dev bugs.

## 7. Side Effects

- **Statusline changes**: Must show QA agent health alongside PM and dev agents. QA's `current-state` file follows the same format.
- **Discussion signature change**: All future PM entries use `**pm**` instead of `**pm/qa**`. This affects grep patterns that look for `**pm/qa**` in Discussion entries. Old entries are preserved.
- **Config.md `PM/QA` label**: Changes to just `PM`. Upgrade must handle this rename.
- **Sub-skill manifest**: Must be updated with QA role composition entry.
- **Composed template size**: PM template shrinks significantly. QA template is new but moderate size (~300-400 lines estimated).
- **Boot script proliferation**: One more boot script pair (sh + ps1). Manageable.

## Integration Risks

- **FEAT-SKILL-027 (Designer)**: Designer's tag-based routing (`Design: needed/in-progress/complete`) is orthogonal to QA. QA just needs to scan designer trackers alongside dev trackers. Low risk.
- **FEAT-SKILL-030 (Sub-skill architecture)**: QA is built on top of this. Must follow the same include directive pattern, placeholder substitution rules, and composition engine. The `[ROLE]` ambiguity issue (PM/DM use `[ROLE]` as variable, not self-reference) applies to QA too — QA reads dev agent trackers using `[ROLE]` as a variable. QA-specific sections inline hardcoded `qa` paths. Medium risk — composition must be tested.
- **DM agent**: DM picks up `Pending Ship` items. Currently DM doesn't care who set the status. QA setting `Pending Ship` instead of PM is transparent to DM. Low risk.
- **PR Flow**: PM monitors PRs and can mark items as `Pending Ship` when merged (bypassing normal QA verification). This is intentional — human-merged PRs are human-approved. QA should not re-verify PR-merged items. PR flow stays with PM.
- **Delivery fallback**: PM's delivery fallback (when DM absent) triggers on `Pending Ship` items. These are now set by QA. PM reads the same trackers. No change to the mechanism, just the source of the status change. Low risk.

## Upgrade & Migration

- **New config values**: Rename `PM/QA` to `PM` in Agents section. No new config key for QA (directory-based detection).
- **New files**:
  - `references/sub-skills/roles/qa-agent.md`
  - `references/sub-skills/qa-specific/verify-bugs.md`
  - `references/sub-skills/qa-specific/verify-features.md`
  - `references/sub-skills/qa-specific/e2e-tests.md`
  - `references/sub-skills/qa-specific/health-checks.md`
  - `references/boot-scripts/start-qa.sh`
  - `references/boot-scripts/start-qa.ps1`
  - `.squidsquad/qa/` directory (created during setup/upgrade)
- **Template changes**:
  - PM template: remove Steps 3-7 (verification), add QA-absent fallback conditional
  - PM Discussion signature: `**pm/qa**` -> `**pm**`
  - Feature intake: Phase 5 removed from PM (QA handles natively)
  - Manifest: add QA role entry
- **Upgrade steps** (`/squidsquad-upgrade`):
  1. Detect if QA directory exists. If not, prompt: "New QA role available. Add QA agent? (Recommended when dev/designer agents exist)"
  2. If yes: create `.squidsquad/qa/` directory structure, generate QA template, create boot scripts
  3. Recompose PM template (removes verification steps, adds fallback conditional)
  4. Rename `PM/QA` to `PM` in config.md
  5. Copy QA boot scripts to `.squidsquad/`
- **Graceful degradation**: If user doesn't upgrade or declines QA, PM continues running with full PM/QA behavior (current template unchanged). The QA-absent fallback in the new PM template preserves this.

## Open Questions

- **Q1**: Should QA file bugs directly (no human approval) for test-discovered failures, or use the Bug Discussion Flow like PM? — **Why**: PM's Bug Discussion Flow requires human approval before filing, which adds latency. QA-discovered bugs from E2E tests are objective (test failed), not subjective (human report). Direct filing is faster but removes the human from the loop for QA-discovered issues.
  - **Recommendation**: QA files directly for E2E test failures (objective, automated). For subjective findings from QA coherence passes (reading files and spotting issues), QA should still use Discussion to flag the issue, but can file without human approval since QA is a verification agent, not a conversation agent.

- **Q2**: Should PM's QA-absent fallback be a separate include (`pm-specific/qa-fallback.md`) or inline in the PM template? — **Why**: A separate include keeps the PM template clean but adds another file. Inline keeps it self-contained but makes the PM template larger.
  - **Recommendation**: Separate include. The fallback is substantial (~100 lines) and is only active when QA is absent. Keeping it as `pm-specific/qa-fallback.md` with a conditional include at the top makes the PM template readable.

- **Q3**: Should `qa-log.md` stay in `pm/` for backward compatibility or move to `qa/`? — **Why**: Existing installs have `pm/qa-log.md` with history. Moving it loses git blame continuity.
  - **Recommendation**: QA creates `qa/qa-log.md` as its own file. PM's `pm/qa-log.md` is preserved as-is (historical). PM stops writing to it when QA is present. No migration of the file itself.

- **Q4**: How does QA discover which agents to scan? Config.md `Dev Agents` list + directory existence for designer? — **Why**: Must be consistent with how PM and DM discover agents.
  - **Recommendation**: Same mechanism as PM/DM: read `Dev Agents` from config.md, plus check for `.squidsquad/designer/` directory. QA uses the same discovery pattern.

- **Q5**: What is QA's default loop interval? Same as PM, or independent? — **Why**: QA may need to run more or less frequently than PM depending on dev velocity.
  - **Recommendation**: Same interval as all other agents (from config.md `Iteration Interval > Minutes`). QA can use Step 1d Interval Sync like dev agents. If per-agent intervals are needed later, that's a separate feature.

## Recommendation

**Feasible with caveats.** The separation is architecturally clean and follows established patterns (sub-skill composition, directory-based role detection, shared tracker access). The main caveats are:

1. **PM template must support dual mode** — with QA (lean coordinator) and without QA (full PM/QA as today). This adds conditional complexity but is necessary for backward compatibility.
2. **Discussion signature change** requires documentation but no automated migration of existing entries.
3. **Phase 5 elimination from PM** is the cleanest win — QA executes test plans natively without needing a subagent, which is simpler and more context-efficient than the current PM approach of spawning a QA subagent.
4. **One-cycle overlap** during QA onboarding is acceptable — idempotent status transitions prevent issues.

The split should reduce PM context usage by an estimated 40-50% (removing all file-reading-intensive verification work) and give QA a dedicated context window for thorough test execution.

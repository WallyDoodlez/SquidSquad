# FEAT-SKILL-347 Research — Separate PM from QA Role

## Summary

PM currently operates as "PM/QA" — a combined agent that handles coordination (planning, human check-in, task intake, delivery fallback) AND quality assurance (E2E test execution, issue verification, task verification with zero-gap gate, test plan execution via subagents). A standalone QA role template already exists at `references/roles/qa/CLAUDE.md` with its own SOUL.md and manifest.yaml. The manifest explicitly references #347 as the ticket that will flip `always_installed: false` to `always_installed: true`. The tracker.py ROLE_AUTHORITY table already authorizes both `qa` and `pm` for `pending-test` transitions, so the backend is ready.

The primary work is: (1) flip the QA manifest flag, (2) strip QA duties from the PM template, (3) ensure the setup wizard installs QA as infrastructure (like PM/DM), and (4) handle the PM fallback when QA is absent (backward compatibility for non-software-dev presets).

Recommendation: **Feasible with caveats**. The QA role template and tracker authority are already in place. Main risks are the PM fallback path and ensuring existing installs upgrade cleanly.

## Impact Analysis

- **Files touched**:
  - `references/roles/qa/manifest.yaml` — flip `always_installed: false` to `true`
  - `references/roles/pm/CLAUDE.md` — remove Steps 3-6 (E2E tests, issue investigation, verify fixed issues, verify pending-test tasks, PR monitoring, ship counter increment), remove Phase 5 QA subagent from task-intake
  - `references/sub-skills/pm-specific/task-intake.md` — remove Phase 5 (QA Test Execution subagent) or rewrite to delegate to QA
  - `references/sub-skills/pm-specific/issue-filing.md` — PM keeps filing; no change needed
  - `references/sub-skills/pm-specific/delivery-fallback.md` — PM keeps delivery fallback; QA marks Pending Ship, DM (or PM fallback) handles shipping. No change needed.
  - `references/sub-skills/pm-specific/pr-flow.md` — move to `qa-specific/` (PR monitoring is verification work)
  - `references/sub-skills/pm-specific/prohibitions.md` — remove "Never mark an issue Verified without actually running a test or check" (that is QA's prohibition now)
  - `references/sub-skills/qa-specific/verification.md` — already exists with full verification logic (Steps 2-5 in QA loop)
  - `references/sub-skills/qa-specific/issue-filing.md` — already exists (objective vs subjective distinction)
  - `.squidsquad/config.md` — may need `QA` line in Agents section (currently only lists PM/QA as combined)
  - `references/scripts/compose.py` — no code changes needed; it already resolves QA role from `references/roles/qa/`
  - `references/scripts/wizard.py` — scaffold logic already handles any role in the install spec; no code change needed
  - `references/scripts/tracker.py` — already authorizes both `pm` and `qa` for pending-test transitions; no change needed
  - `references/presets/software-dev/manifest.yaml` — already lists `qa` in `role_install_order`; no change needed

- **Behavior changes**:
  - PM no longer runs E2E tests or verifies pending-test items
  - PM no longer spawns QA subagents during task intake Phase 5
  - QA becomes a standalone agent with its own clone, current-state, working-state, qa-log
  - QA auto-detects pending-test items via `tracker.py list-issues/list-tasks --status pending-test`
  - PM still files bugs (from human input) but does not file bugs from test failures (QA does)
  - PM still runs the Issue Discussion Flow for human-reported bugs

- **Dependencies**:
  - `boot_remote.py` (#4) — QA needs to be bootable as a remote agent; boot_remote already handles arbitrary roles from config
  - health_check.py — already checks all agents listed in config; QA will appear automatically

## What Moves to QA vs What PM Keeps

### PM Ralph Loop — AFTER separation

| Step | Description | Stays with PM? |
|------|-------------|----------------|
| 1    | Pull Latest | YES |
| 1b   | Context Pressure Check | YES |
| 1c   | Resume Working State | YES |
| 2    | Check In With Human | YES — PM is the human interface |
| 3    | Run E2E Tests | **MOVES TO QA** |
| 4    | Investigate Test Failures | **MOVES TO QA** (objective failures filed directly by QA; subjective flagged for PM/human) |
| 5    | Verify Fixed Issues | **MOVES TO QA** |
| 6    | Verify Pending Test Tasks | **MOVES TO QA** |
| 6b   | Monitor PRs | **MOVES TO QA** (PR review is verification) |
| 6c   | Increment Ship Counter | **MOVES TO QA** (QA increments when closing verified issues) |
| 6d   | PM Delivery Fallback | YES — delivery is PM's fallback, not QA's |
| 7    | Agent Health Check | YES (PM monitors all agents including QA) |
| 7b   | GitHub Issues Sync | YES |
| 8    | Boot Remote Agents | YES |
| 8b   | Improvement Scan | **SPLIT** — PM scans for process improvements; QA scans for test coverage gaps (QA SOUL.md already defines QA-specific scan criteria) |
| 9    | Iteration Log + Vault + Git | YES (both agents have their own) |
| 10   | Done | YES |

### Task Intake changes

| Phase | Description | Owner |
|-------|-------------|-------|
| 1 | Research (subagent) | PM |
| 2A | Discussion Prep (subagent) | PM |
| 2 | Discussion (PM + Human) | PM |
| 3 | Planning (test plan subagent) | PM — PM still creates the test plan |
| 4 | Execution (Dev agent) | Dev |
| 5 | QA Test Execution | **QA** — QA picks up pending-test items and executes test plans |

## QA Role Definition (Standalone)

The QA role template already exists at `references/roles/qa/CLAUDE.md`. Its loop:

1. Pull Latest + Context Pressure + Resume Working State + Interval Sync
2. Run E2E Tests (from `qa-specific/verification.md` Step 2)
3. Investigate + File Issues from Test Failures (Step 3)
4. Verify Fixed Issues (Step 4)
5. Verify Pending Test Tasks with zero-gap gate (Step 5)
6. Monitor PRs (Step 5b, if PR Flow enabled)
7. Agent Health Check (Step 6)
8. Boot Remote Agents
9. Improvement Scan (QA-specific: test coverage gaps)
10. Iteration Log + Vault + Git Commit
11. Done

Sub-skills QA gets (already defined in `references/roles/qa/CLAUDE.md` includes):
- `common/tracker-protocol`
- `common/pull-latest`
- `qa-specific/verification` (Steps 2-5b)
- `common/boot-remote-agents`
- `common/improvement-scan`
- `qa-specific/iteration-log`
- `common/vault-remember`
- `common/vault-optimize`
- `qa-specific/git-commit`
- `qa-specific/issue-filing`
- `qa-specific/discussion-protocol`
- `common/vault-protocol`
- `qa-specific/file-conventions`
- `qa-specific/status-line`
- `qa-specific/prohibitions`

## PM Changes After Separation

PM loses:
- Step 3 (Run E2E Tests)
- Step 4 (Investigate Test Failures)
- Step 5 (Verify Fixed Issues)
- Step 6 (Verify Pending Test Tasks + zero-gap gate)
- Step 6b (PR Monitoring)
- Step 6c (Ship Counter Increment for issues)
- Phase 5 of Task Intake (QA Test Execution subagent)
- The `testing` and `verifying` phases from status bar states

PM keeps:
- Human check-in (Step 2)
- Task intake lifecycle (Phases 1-3: Research, Discussion, Planning)
- Task approval (human confirmation)
- Issue Discussion Flow (human-reported bugs)
- Agent Health Check (Step 7)
- GitHub Issues sync
- Boot Remote Agents
- Delivery Fallback (Step 6d)
- Improvement Scan (process-focused, not test-coverage-focused)
- Iteration Log, Vault, Git Commit

PM identity changes from "PM/QA" to just "PM" in the CLAUDE.md header and description.

## Coordination Model

### How PM and QA coordinate

1. **PM marks items for QA**: PM does not explicitly "hand off" to QA. The status label `pending-test` is the handoff signal. When a dev agent marks work `pending-test`, QA automatically picks it up in its verification step.

2. **QA auto-detects**: QA queries `tracker.py list-issues/list-tasks --status pending-test` each cycle. No explicit PM-to-QA handoff needed.

3. **QA marks Pending Ship**: After verification, QA transitions to `pending-ship`. DM (or PM delivery fallback) picks it up.

4. **QA bounces back to dev**: If verification fails, QA transitions back to `in-progress` with specific findings in Discussion.

5. **QA flags subjective findings for PM**: QA does not file subjective issues (coherence, style). It comments on the relevant issue flagging it for PM/human review.

6. **Shared tracker**: GitHub Issues is the single source of truth. Both PM and QA read/write to it. No direct PM-QA communication channel needed.

7. **PM monitors QA health**: PM's health check step monitors QA's `current-state` file just like any other agent.

## Config Changes

### config.md

Current:
```markdown
## Agents
- **Dev Agents**: skill
- **PM/QA**: always present
- **DM**: present
```

After:
```markdown
## Agents
- **Dev Agents**: skill
- **PM**: always present
- **QA**: always present (or "present" if not always_installed)
- **DM**: present
```

The `qa` alias already exists in the Aliases section.

### manifest.yaml changes

`references/roles/qa/manifest.yaml`:
```yaml
always_installed: true   # was: false
```

This is the single-field edit already anticipated in the manifest's own comment.

### Setup wizard impact

- The wizard reads `role_install_order` from the preset manifest. For `software-dev`, QA is already listed.
- If QA becomes `always_installed: true`, the wizard should install QA without asking, same as PM and DM.
- The wizard's `scaffold_install` function calls `deploy_role` for each agent in the spec. QA will get `deploy_role("qa")` which resolves to `references/roles/qa/CLAUDE.md`.
- The wizard code itself needs no changes — `always_installed` handling is in the installer agent's prose runbook (which reads manifests). The runbook needs to be updated to treat QA as infrastructure.

### compose.py impact

- `compose.py` already knows the `qa` role identity (it has its own directory under `references/roles/qa/`).
- `_get_entry_file_for_role("qa")` returns `"qa"` (it exists in the role registry).
- `_substitute_placeholders` treats non-dev roles uniformly — QA gets `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`, and `[INTERVAL]` substituted. This is correct.
- No code changes needed in compose.py.

## Token Impact

### Cost analysis

- **PM gets smaller**: Removing Steps 3-6 plus Phase 5 and the `qa-specific/verification.md` content saves roughly 3,000-4,000 tokens from PM's composed CLAUDE.md.
- **QA is a new agent**: QA's composed CLAUDE.md is approximately 8,000-10,000 tokens (verification steps + tracker protocol + common sub-skills).
- **Net token cost**: One additional agent running. However:
  - PM cycles become faster (fewer steps per cycle = less per-cycle token usage).
  - QA can run on a cheaper/smaller model if verification is its only job.
  - Parallelism: PM and QA can run simultaneously. PM does planning while QA verifies.

### When QA is absent (non-software-dev presets)

If QA becomes `always_installed: true`, it runs in ALL presets. For the `design` preset, QA would have nothing to verify (no dev agents, no E2E tests). Options:
1. Keep `always_installed: false` and only install QA in `software-dev` preset (current behavior).
2. Make `always_installed: true` but have QA gracefully idle when no dev agents exist.
3. Add a PM fallback: if QA is not installed, PM resumes combined PM/QA behavior.

**Recommendation**: Option 3 is safest. PM checks for QA presence (`.squidsquad/qa/` directory exists). If absent, PM runs Steps 3-6 as today. If present, PM skips them. This mirrors the existing DM presence check in the delivery fallback step.

## Side Effects

1. **Existing installs**: Existing `.squidsquad/` directories do not have a `qa/` subdirectory. The upgrade path must create it.
2. **qa-log.md location**: Currently PM writes to `pm/qa-log.md`. QA writes to `qa/qa-log.md`. These are different files. No conflict.
3. **Ship counter**: QA increments `Shipped Since Last Bump` in config.md. PM also increments it (in delivery fallback). Both write to the same config.md field. Git conflicts are possible if both increment in the same cycle. Mitigation: use `config.py set shipped-since-bump` which does atomic read-modify-write.
4. **PR monitoring**: If PR Flow is enabled, QA monitors PRs. PM no longer does. Existing PM behavior for PR comments needs to be removed from PM template.
5. **Planning phase suppression**: PM suppresses its cycle during active planning phases. QA should NOT be suppressed during PM planning — QA continues verifying independently. This is already correct since QA has its own working-state.

## Edge Cases

1. **Race condition**: Dev marks item `pending-test`. Both PM and QA see it in the same cycle. If PM still has residual verification code, both could try to verify. Mitigation: PM's QA presence check must reliably skip verification when QA exists.
2. **QA stalls while items are pending-test**: PM's health check detects the stall and alerts. Items remain in `pending-test` until QA recovers. No automatic fallback to PM verification (keep separation clean).
3. **QA and PM both comment on same issue**: Both are authorized commenters. Discussion entries are append-only, so no conflict. But duplicate "Verified" comments could confuse. Mitigation: only one agent (QA) performs verification.
4. **Design preset**: No dev agents, no E2E tests. QA would idle every cycle. Acceptable — QA simply skips all verification steps when nothing is pending-test.

## Integration Risks

1. **boot_remote.py (#4)**: QA needs to be booted as a remote agent. boot_remote already reads config.md for agent list and boots each. QA will appear in the agent list and be booted automatically. Risk: LOW.
2. **health_check.py**: Already reads all agent directories. QA's `current-state` file will be picked up automatically. Risk: NONE.
3. **Status bar**: QA gets its own status-line sub-skill (`qa-specific/status-line.md`). Already defined. Risk: NONE.
4. **Upgrade skill**: The `/squidsquad-upgrade` skill needs to know to create the `qa/` directory on upgrade. Risk: MEDIUM — must be tested.

## Upgrade & Migration

- **New config values**: QA line in Agents section of config.md.
- **New files**: `.squidsquad/qa/CLAUDE.md`, `.squidsquad/qa/SOUL.md`, `.squidsquad/qa/working-state.md`, `.squidsquad/qa/current-state`.
- **Template changes**: PM CLAUDE.md loses Steps 3-6 and gains a QA presence check. QA CLAUDE.md is composed fresh.
- **Upgrade steps**: `/squidsquad-upgrade` must:
  1. Run `compose.py deploy qa` to create `.squidsquad/qa/CLAUDE.md`.
  2. Copy `references/roles/qa/SOUL.md` to `.squidsquad/qa/SOUL.md` if missing.
  3. Create `.squidsquad/qa/working-state.md` with default content.
  4. Re-compose PM: `compose.py deploy pm` to get the updated PM template without QA steps.
  5. Update config.md Agents section to list QA separately.
- **Graceful degradation**: If user doesn't upgrade, PM continues as PM/QA. The old combined template works. No breakage.

## Capability Gaps

- No capability requirements declared in `references/roles/qa/manifest.yaml` (`requires_sub_skills: {}`). QA uses `gh` CLI and `tracker.py` — same tools as PM.

## Open Questions

- **Q1**: Should QA be `always_installed: true` (runs in all presets) or remain preset-gated (only in `software-dev`)? **Why**: If always-installed, QA idles in design-only presets, wasting a Claude session. If preset-gated, PM needs a fallback path.
- **Q2**: Should PM retain a "QA fallback" mode (like DM delivery fallback) for when QA is not installed? **Why**: Without fallback, non-software-dev presets lose all verification. Design preset has no dev work to verify, but custom presets might.
- **Q3**: Should the improvement scan be split (PM scans process, QA scans test coverage) or should QA own all improvement scanning? **Why**: Duplicate scanning wastes tokens; but PM may spot process improvements QA cannot.
- **Q4**: When QA files an objective bug directly, should PM be notified? **Why**: PM is the human interface — the human may want to know about new bugs. Counter: Discussion entries on the issue are visible to everyone.

## Recommendation

**Feasible with caveats**. The QA role infrastructure is 90% built. The main work is:

1. Flip the manifest flag (1 line).
2. Strip QA steps from PM template and add QA presence check fallback (medium effort, ~200 lines of template changes).
3. Update the setup installer prose runbook to treat QA as infrastructure.
4. Update the upgrade skill to scaffold the QA directory for existing installs.
5. Test the PM fallback path (QA absent) and the clean separation path (QA present).

Estimated complexity: **Medium**. Most infrastructure exists. Primary risk is the PM fallback path for non-software-dev presets and ensuring clean upgrade for existing installs.

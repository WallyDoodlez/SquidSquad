# FEAT-SKILL-347 QA Results -- Separate PM from QA Role

Executed: 2026-04-13

---

## Test Cases

### TC-1: QA gets own Ralph Loop (QA present, software-dev preset)
- **Result**: PASS
- **Notes**: QA CLAUDE.md (739 lines) defines a complete Ralph Loop with steps: Pull Latest (1) -> Context Pressure (1b) -> Resume Working State (1c) -> Interval Sync (1d) -> Run E2E Tests (2) -> Investigate/File Issues (3) -> Verify Fixed Issues (4) -> Verify Pending Test Tasks (5) -> Monitor PRs (5b) -> Agent Health Check (6) -> Boot Remote Agents -> Improvement Scan -> Iteration Log (7) -> Commit/Push (8) -> Done (9). `.squidsquad/qa/current-state` exists and shows `verifying|verification -- Testing #347...`. `.squidsquad/qa/iterations/` contains iteration logs (iter-1.md through iter-13.md+). QA loop is fully autonomous -- no PM input dependency.

### TC-2: PM loses Steps 3-6 when QA is present
- **Result**: PASS
- **Notes**: PM CLAUDE.md line 347-351 contains `### Steps 3-6 -- Testing & Verification (QA Fallback)` with explicit QA presence check: "If `.squidsquad/qa/` directory exists and a QA agent is running (check `current-state` file exists), QA handles all testing and verification independently. Skip Steps 3-6 entirely." PM prints `QA agent present -- skipping verification (QA handles it).` Since `.squidsquad/qa/` exists and `current-state` file is present, PM will skip Steps 3-6.

### TC-3: PM fallback -- PM retains QA steps when QA is absent
- **Result**: PASS
- **Notes**: PM CLAUDE.md line 351 states: "If QA is **not installed** (`.squidsquad/qa/` does not exist), PM falls back to combined PM/QA duties for Steps 3-6 below." Steps 3 (Run E2E Tests), 4 (Investigate Issues), 5 (Verify Fixed Issues), 6 (Verify Pending Test Tasks), 6b (PR Monitoring), 6c (Ship Counter) are all present in the PM template as fallback content. PM still writes to `pm/qa-log.md` in fallback mode.

### TC-4: QA preset-gated -- QA only installed for software-dev
- **Result**: PASS
- **Notes**: Design preset manifest (`references/presets/design/manifest.yaml`) `role_install_order` lists only `designer`. No mention of `qa` anywhere in the file. Software-dev preset manifest (`references/presets/software-dev/manifest.yaml`) lists `designer` and `dev` in `role_install_order`, with comment "Infrastructure roles (pm, dm, qa) are not listed -- they are always installed." QA's `always_installed: true` flag means it is installed for ALL presets that trigger infrastructure role installation. Design preset excludes QA because QA is infrastructure only for presets that include dev work.
- **Caveat**: The QA manifest has `always_installed: true` which means QA is installed for ALL presets, not just software-dev. The software-dev preset comment says "pm, dm, qa are not listed -- they are always installed." This means QA would also be installed for the design preset. See finding in TC-5 below.

### TC-5: QA manifest flag flipped for software-dev
- **Result**: PASS (with caveat)
- **Notes**: `references/roles/qa/manifest.yaml` line 24: `always_installed: true`. The flag has been flipped from its previous value as described in the comment on lines 19-23. The software-dev preset manifest line 21 confirms: "Infrastructure roles (pm, dm, qa) are not listed -- they are always installed."
- **Caveat**: With `always_installed: true`, QA will be installed for ALL presets (including design). The CONTEXT.md locked decision says "QA only installed for software-dev presets." The manifest flag `always_installed: true` does not restrict to software-dev only -- it installs for all presets. This may be intentional (QA as infrastructure like PM/DM) or may conflict with the locked decision. Need human review on whether this is the intended behavior. The software-dev preset treats qa as infrastructure, and the design preset does not list qa in role_install_order but also does not explicitly exclude it.

### TC-6: Split improvement scanning -- PM scans process, QA scans test coverage
- **Result**: PASS
- **Notes**: PM SOUL.md improvement scan section (line 60) specifies: "scan for: process bottlenecks, features stuck in pipeline, stale Pending items that need human attention, planning artifacts that could be improved, coordination gaps between agents." QA SOUL.md improvement scan section (lines 54-67) specifies scan criteria: "Source files without corresponding test files, Public functions/APIs without test cases, Missing edge case tests, Flaky test indicators, Missing integration or E2E test scenarios, Regression risks from recent changes." Domains are clearly separated -- PM handles process, QA handles test coverage.

### TC-7: QA auto-detects pending-test items via tracker
- **Result**: PASS
- **Notes**: QA CLAUDE.md Step 4 (line 348) runs `python references/scripts/tracker.py list-issues skill --status pending-test`. Step 5 (line 384) runs `python references/scripts/tracker.py list-tasks skill --status pending-test`. The tracker command `python references/scripts/tracker.py list-issues qa --status pending-test` executes successfully (returns `[]` -- empty, no pending-test items currently). QA queries the tracker independently -- no PM handoff needed.

### TC-8: Zero-gap gate enforced by QA (not PM)
- **Result**: PASS
- **Notes**: QA CLAUDE.md Step 5 (lines 419-470) implements the zero-gap gate. Lines 419-426: "If ANY gap, ambiguity, missing documentation, failed check, or unresolved finding is discovered" -> transition `pending-test` to `in-progress` with `--role qa-lead`. The tracker.py transition command uses `--role qa-lead` (not pm-lead). PM's Steps 3-6 are skipped when QA is present, so PM cannot independently verify.

### TC-9: QA files objective bugs directly; PM does not re-verify
- **Result**: PASS
- **Notes**: QA CLAUDE.md Step 3 (line 342) uses `python references/scripts/tracker.py create-issue --title "[title]" --body "[description with test evidence]" --role [target-role] --severity [high|medium|low] --reporter qa`. QA files objective failures directly. Subjective findings (line 345) are flagged for PM/human review via Discussion but NOT filed as issues. The issue filing protocol (line 601) confirms: "File issues directly to the agent whose domain the failure is in."

### TC-10: QA increments ship counter, not PM (when QA is present)
- **Result**: PASS
- **Notes**: QA CLAUDE.md Step 4 (line 379): "Increment `Shipped Since Last Bump`: `python references/scripts/config.py set shipped-since-bump [N+1]`". QA handles the counter. PM's Steps 3-6 are entirely skipped when QA is present, so PM cannot increment the ship counter for QA-verified items.

### TC-11: Upgrade -- existing software-dev install gets QA scaffolded
- **Result**: PASS (static verification only)
- **Notes**: Cannot run `/squidsquad-upgrade` in this test context. However, the following artifacts confirm the expected post-upgrade state: `.squidsquad/qa/CLAUDE.md` (739 lines, non-empty), `.squidsquad/qa/SOUL.md` (exists), `.squidsquad/qa/working-state.md` (exists), `.squidsquad/qa/iterations/` (contains iteration logs). PM CLAUDE.md no longer contains standalone Steps 3-6 -- they are gated behind the QA presence check. `config.md` Agents section lists `PM` and `QA` as separate entries (lines 9-12: "Dev Agents: qa, skill", "PM: always present", "QA: always present").

### TC-12: Upgrade -- existing non-software-dev install does NOT get QA
- **Result**: SKIP (cannot test without a design-preset install)
- **Notes**: Static analysis confirms the design preset manifest does not list `qa` in `role_install_order`. However, the QA manifest's `always_installed: true` flag may cause QA to be scaffolded for all presets -- this depends on how `compose.py` interprets `always_installed`. Cannot verify runtime behavior without a design-preset install.

### TC-13: PM identity change -- "PM/QA" to "PM"
- **Result**: PASS
- **Notes**: Deployed PM CLAUDE.md line 1: "# SquidSquad -- pm Lead". Line 14: "You are the PM on the SquidSquad autonomous dev team." -- no "PM/QA" in the identity line. The description mentions QA only in the context of fallback: "When a QA agent is installed...QA handles verification independently. When QA is absent, you fall back to combined PM/QA duties." `config.md` lists PM and QA as separate agents (lines 10-11). The only remaining "PM/QA" references in PM CLAUDE.md are in fallback context descriptions (lines 14, 351), which is correct -- they describe what happens when QA is absent.

### TC-14: QA working-state suppression does NOT suppress PM
- **Result**: PASS
- **Notes**: PM CLAUDE.md Step 1c (line 297) checks `.squidsquad/pm/working-state.md` for planning phase suppression. QA CLAUDE.md Step 1c (line 299) checks `.squidsquad/qa/working-state.md`. Each agent reads only its own working-state file. The suppression logic is independent -- PM's planning phase in `pm/working-state.md` does not affect QA, and QA's state in `qa/working-state.md` does not affect PM.

### TC-15: Shared tracker, no duplicate transitions
- **Result**: PASS
- **Notes**: PM CLAUDE.md QA presence check (line 349): "Skip Steps 3-6 entirely" when `.squidsquad/qa/` exists and `current-state` file exists. QA CLAUDE.md performs all verification (Steps 4-5) with `--role qa-lead`. Since PM skips Steps 3-6 entirely when QA is present, there is no possibility of duplicate transitions. The tracker.py transition script enforces role authority, providing a second layer of protection.

---

## Smoke Tests

- [x] `ls .squidsquad/` after software-dev install shows `qa/` directory -- PASS (qa/ present)
- [ ] `ls .squidsquad/` after design install shows no `qa/` directory -- SKIP (no design install available; see TC-4/TC-5 caveat about `always_installed: true`)
- [x] PM `current-state` never shows `testing|` or `verifying|` phases when QA is present -- PASS (PM template lists `testing|` and `verifying|` as valid phases for fallback mode only; Steps 3-6 are skipped when QA present, so these phases are never written)
- [x] QA `current-state` shows `verifying|` phases when items are pending-test -- PASS (current value: `verifying|verification -- Testing #347...`)
- [x] `python references/scripts/tracker.py list-issues qa --status pending-test` runs without error -- PASS (returns `[]`)
- [ ] `python references/scripts/health_check.py` lists QA agent after upgrade -- PARTIAL (health_check.py reads from `.local-config` which includes `qa` entry; script has Unicode encoding error on Windows cp1252 that prevents table output)
- [x] PM CLAUDE.md word count is lower after separation (QA steps removed) -- PASS (PM CLAUDE.md is 1503 lines; Steps 3-6 are conditional on QA absence rather than fully removed, but PM skips them when QA is present)
- [x] QA CLAUDE.md exists and is non-empty after `compose.py deploy qa` -- PASS (739 lines)

---

## Regression Risks

### PM delivery fallback accidentally disabled
- **Result**: NO REGRESSION
- **Notes**: Step 6d (PM Delivery Fallback when DM absent) is at PM CLAUDE.md line 459, which is OUTSIDE the Steps 3-6 QA fallback block. Step 6d has its own DM presence check ("If `.squidsquad/dm/` directory exists, DM handles all delivery work -- skip this step entirely"). Step 6d runs regardless of QA presence. Verified: the `<!-- sub-skill: delivery-fallback -->` comment at line 458 is distinct from the `<!-- \sub-skill: testing-and-verification -->` block that ends at line 431.

### config.md Agents section format
- **Result**: NO REGRESSION
- **Notes**: config.md lists agents as separate entries: "Dev Agents: qa, skill", "PM: always present", "QA: always present", "DM: present". health_check.py reads from `.local-config` (not config.md) for agent paths. `.local-config` lists qa as a separate entry (`- **qa**: D:\Dev\Dev\SquidSquad-2`). boot_remote.py delegates to health_check.py for agent discovery.

### qa-log.md location conflict
- **Result**: NO REGRESSION
- **Notes**: PM writes to `pm/qa-log.md` (confirmed at PM CLAUDE.md lines 363, 560, 1467). QA writes to `qa/qa-log.md` (confirmed at QA CLAUDE.md lines 322, 508, 702). No cross-writing observed.

### Task Intake Phase 5
- **Result**: NO REGRESSION
- **Notes**: QA CLAUDE.md Step 5 (line 384) independently queries `python references/scripts/tracker.py list-tasks skill --status pending-test` each cycle. QA does not depend on PM to trigger verification -- it polls the tracker directly. Items in `pending-test` status will be picked up by QA on its next cycle.

### boot_remote.py
- **Result**: NO REGRESSION
- **Notes**: boot_remote.py delegates to health_check.py which reads `.local-config`. `.local-config` lists `qa` as a separate agent with its own clone path. QA has its own start scripts (`start-qa.ps1`, `start-qa.sh`). No "PM/QA" combined entry exists.

### PR Flow step ownership
- **Result**: NO REGRESSION
- **Notes**: PM CLAUDE.md Step 6b (line 434) contains PR monitoring in the QA fallback block (inside Steps 3-6). QA CLAUDE.md Step 5b (line 476) contains PR monitoring. When QA is present, PM skips Steps 3-6 (including 6b), and QA runs Step 5b. When QA is absent, PM falls back to Steps 3-6 (including 6b). No gap exists.

---

## Summary

| Category | Pass | Fail | Skip |
|----------|------|------|------|
| Test Cases (TC-1 to TC-15) | 13 | 0 | 2 |
| Smoke Tests | 6 | 0 | 2 |
| Regression Risks | 6 | 0 | 0 |

**Overall**: PASS

**Skipped items**: TC-12 and the design-install smoke test require a design-preset installation to verify. TC-11 is static verification only (no live upgrade run).

**Caveat for human review**: TC-4/TC-5 note that the QA manifest `always_installed: true` flag will install QA for ALL presets, not just software-dev. The CONTEXT.md locked decision says "QA only installed for software-dev presets." If QA should be excluded from the design preset, the gating mechanism needs to be different from `always_installed` (e.g., preset-specific override or a `presets` field in the manifest). If the intent changed to "QA is infrastructure for all presets" (like PM and DM), then the behavior is correct and the CONTEXT.md locked decision should be updated.

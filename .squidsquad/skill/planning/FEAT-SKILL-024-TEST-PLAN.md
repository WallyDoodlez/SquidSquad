# FEAT-SKILL-024 Test Plan — Open Planning Artifacts in VS Code

## Test Cases

### TC-1: Happy path — user accepts prompt after each phase
- **Precondition**: No "Never ask again" preference in config.md. `code` CLI is on PATH.
- **Steps**: Run a full feature intake through Phases 1-3. Select "Yes, open in VS Code" after each phase (RESEARCH.md, CONTEXT.md, TEST-PLAN.md).
- **Expected**: VS Code opens the correct artifact after each phase. Intake continues to the next phase without interruption after each prompt.
- **Verification**: Confirm VS Code launched 3 times with the correct file path each time. Confirm no errors in agent output. Confirm Phase 2, 3, and post-Phase-3 transitions all proceed normally.

### TC-2: User declines prompt — no side effects
- **Precondition**: No "Never ask again" preference in config.md.
- **Steps**: Complete Phase 1. When prompted, select "No thanks".
- **Expected**: No editor opens. Intake continues to Phase 2 without delay. config.md is unchanged.
- **Verification**: Confirm config.md has no new entries. Confirm Phase 2 begins immediately after selection.

### TC-3: "Never ask again" suppresses all future prompts across all phases
- **Precondition**: No existing preference in config.md.
- **Steps**: Complete Phase 1. Select "Never ask again". Continue through Phases 2 and 3 of the same feature. Then start a second feature and complete Phase 1.
- **Expected**: After selection, preference is saved to config.md. Phases 2 and 3 produce no prompt. Second feature's Phase 1 also produces no prompt.
- **Verification**: Check config.md contains the suppression key after Phase 1 selection. Grep agent output to confirm zero AskUserQuestion calls after Phase 1 of the first feature (across both features).

### TC-4: Pre-existing suppression preference — prompt never appears
- **Precondition**: config.md already has the suppression preference set.
- **Steps**: Run a full feature intake through Phases 1-3.
- **Expected**: No prompt is shown after any phase. All transitions are silent and immediate.
- **Verification**: Grep agent output to confirm no AskUserQuestion was issued after any phase completion.

### TC-5: `code` command not available — fallback to printing path
- **Precondition**: `code` CLI is not on PATH. No suppression preference.
- **Steps**: Complete Phase 2 (CONTEXT.md). Select "Yes, open in VS Code".
- **Expected**: Agent prints the full file path to the artifact instead of crashing. Intake continues to Phase 3 normally.
- **Verification**: Confirm output contains the absolute file path. Confirm no error or stack trace. Confirm Phase 3 proceeds.

### TC-6: Mixed selections across phases within one feature
- **Precondition**: No suppression preference in config.md. `code` CLI is on PATH.
- **Steps**: Complete Phase 1, select "Yes, open in VS Code". Complete Phase 2, select "No thanks". Complete Phase 3, select "Yes, open in VS Code".
- **Expected**: VS Code opens after Phase 1 and Phase 3. No editor opens after Phase 2. All three transitions proceed normally. config.md is unchanged.
- **Verification**: Confirm VS Code launched exactly twice (after Phases 1 and 3). Confirm config.md has no suppression key.

### TC-7: Prompt targets the correct artifact path per phase
- **Precondition**: No suppression preference. Feature ID is FEAT-SKILL-099.
- **Steps**: Run intake through all three phases, selecting "Yes" each time. Inspect the file paths passed to `code`.
- **Expected**: Phase 1 opens `FEAT-SKILL-099-RESEARCH.md`, Phase 2 opens `FEAT-SKILL-099-CONTEXT.md`, Phase 3 opens `FEAT-SKILL-099-TEST-PLAN.md`.
- **Verification**: Check agent output or bash history for three distinct `code` invocations with the correct filenames matching the phase artifacts.

## Smoke Tests
- [ ] Phase 1 completion triggers the prompt (when preference is not suppressed)
- [ ] Phase 2 completion triggers the prompt (when preference is not suppressed)
- [ ] Phase 3 completion triggers the prompt (when preference is not suppressed)
- [ ] Selecting "Yes" actually opens the file (or prints path if `code` unavailable)
- [ ] Selecting "Never ask again" writes a config entry and suppresses all subsequent prompts

## Regression Risks
- **Phase transition disruption**: The prompt must not block or break any phase-to-phase transition regardless of which option the user selects.
- **Config.md corruption**: Writing the suppression preference must not damage existing config entries, counters, or formatting.
- **Non-VS-Code environments**: Agents running in terminals without `code` CLI must not crash or hang.
- **Artifact path mismatch**: Each phase must reference the correct artifact filename; a copy-paste error could open the wrong file.

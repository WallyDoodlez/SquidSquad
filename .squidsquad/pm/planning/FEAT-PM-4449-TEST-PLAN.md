# FEAT-PM-4449 Test Plan — L4 Project Instructions: Distribution Packaging + Content Migration

## Overview

Tests cover two work streams: (1) migration of project-specific content into L4 source files, and (2) addition of distribution packaging gates to PM and DM L4 instructions. All tests run against the post-implementation state.

---

## Test Cases

### TC-1: L4 instructions.md exists for each role

- **Precondition**: Implementation complete, compose.py deploy-all has run.
- **Steps**:
  1. Check for `references/roles/pm/L4/instructions.md`
  2. Check for `references/roles/skill/L4/instructions.md` (or dev equivalent path)
  3. Check for `references/roles/qa/L4/instructions.md`
  4. Check for `references/roles/dm/L4/instructions.md`
- **Expected**: All four files exist and are non-empty (>0 bytes).
- **Verification**:
  ```bash
  for role in pm skill qa dm; do
    f="references/roles/$role/L4/instructions.md"
    [ -s "$f" ] && echo "OK: $f" || echo "MISSING/EMPTY: $f"
  done
  ```

---

### TC-2: L4 SOUL.md exists for each role

- **Precondition**: Implementation complete, compose.py deploy-all has run.
- **Steps**:
  1. Check for `references/roles/pm/L4/SOUL.md`
  2. Check for `references/roles/skill/L4/SOUL.md`
  3. Check for `references/roles/qa/L4/SOUL.md`
  4. Check for `references/roles/dm/L4/SOUL.md`
- **Expected**: All four files exist and are non-empty.
- **Verification**:
  ```bash
  for role in pm skill qa dm; do
    f="references/roles/$role/L4/SOUL.md"
    [ -s "$f" ] && echo "OK: $f" || echo "MISSING/EMPTY: $f"
  done
  ```

---

### TC-3: Project Adaptation content appears in L4 SOUL source

- **Precondition**: soul_adaptation.py has been run (or migration script applied). L4 SOUL.md files exist for each role.
- **Steps**:
  1. Read the current deployed SOUL.md for each role (`.squidsquad/<role>/SOUL.md`).
  2. Locate the `### Project Adaptation` section (or equivalent) in each deployed SOUL.md.
  3. For each role, confirm that the same content is present in `references/roles/<role>/L4/SOUL.md`.
- **Expected**: Every Project Adaptation entry currently in the deployed SOUL.md is also present verbatim (or reformatted equivalently) in the corresponding L4 SOUL source file.
- **Verification**: Diff Project Adaptation sections between deployed and L4 source for each role. Zero omissions expected; formatting changes are acceptable.

---

### TC-4: compose.py deploy-all produces identical output before and after migration

- **Precondition**: Baseline snapshot of deployed agent files taken before migration (or implementation includes a reference snapshot). compose.py is functional.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all` after migration.
  2. Compare output `.squidsquad/<role>/CLAUDE.md` files against the pre-migration baseline for each role.
- **Expected**: Content is semantically identical. Any differences are purely source-attribution changes (e.g., L4 content now read from a different source file), not behavioral changes.
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all
  git diff --stat .squidsquad/
  # Expect: zero diff, or only whitespace/comment changes if any
  ```
  If baseline snapshots were committed before migration, `git diff <baseline-commit> HEAD -- .squidsquad/` must show no agent-behavior changes.

---

### TC-5: soul_adaptation.py writes to L4 source, not deployed file

- **Precondition**: soul_adaptation.py has been updated as part of this task.
- **Steps**:
  1. Run `python references/scripts/soul_adaptation.py add pm --category tech-stack --signal "test-signal-4449" --task 4449`.
  2. Check the L4 SOUL source file: `references/roles/pm/L4/SOUL.md`.
  3. Check the deployed SOUL file: `.squidsquad/pm/SOUL.md`.
- **Expected**:
  - The signal `test-signal-4449` appears in `references/roles/pm/L4/SOUL.md`.
  - The signal does NOT appear in `.squidsquad/pm/SOUL.md` until compose.py deploy-all is run.
- **Cleanup**: Remove the test signal after verification (revert the L4 SOUL.md edit, or run deploy-all and verify the deployed file reflects only content from compose).

---

### TC-6: Vault notes NOT deleted after migration

- **Precondition**: Migration complete.
- **Steps**:
  1. Identify vault notes that contained content moved to L4 (e.g., `.squidsquad/vault/BRIEFING.md`, any galaxy notes referenced in the migration plan).
  2. Verify each identified file still exists at its original path.
  3. Verify content is intact (no truncation).
- **Expected**: All vault notes exist and are unmodified (or only have additions/updated timestamps, never deletions).
- **Verification**:
  ```bash
  git log --diff-filter=D --name-only -- .squidsquad/vault/
  # Expect: no deleted vault files in commits related to this task
  ```

---

### TC-7: PM L4 has distribution packaging checklist

- **Precondition**: Implementation complete.
- **Steps**:
  1. Read `references/roles/pm/L4/instructions.md`.
  2. Search for distribution packaging verification items.
- **Expected**: The file contains all of the following checks (exact wording may vary):
  - Does this change affect distributed files?
  - Is `installer-files.txt` up to date?
  - Does `packages/cli/package.json` version match `config.md` version?
  - If distribution files changed, flag for DM delivery.
- **Verification**:
  ```bash
  grep -i "installer-files" references/roles/pm/L4/instructions.md
  grep -i "package.json" references/roles/pm/L4/instructions.md
  grep -i "distribution" references/roles/pm/L4/instructions.md
  # Expect: non-empty matches for each
  ```

---

### TC-8: DM L4 has delivery packaging checklist

- **Precondition**: Implementation complete.
- **Steps**:
  1. Read `references/roles/dm/L4/instructions.md`.
  2. Search for delivery packaging items.
- **Expected**: The file contains all of the following checks:
  - Verify `installer-files.txt` is current during version bump.
  - Verify `packages/cli/package.json` version matches new version.
  - Consider: does this version need `npm publish`?
- **Verification**:
  ```bash
  grep -i "installer-files" references/roles/dm/L4/instructions.md
  grep -i "npm publish" references/roles/dm/L4/instructions.md
  grep -i "package.json" references/roles/dm/L4/instructions.md
  # Expect: non-empty matches for each
  ```

---

### TC-9: All agent L4 instructions mention npm distribution awareness

- **Precondition**: Implementation complete.
- **Steps**:
  1. Read `references/roles/pm/L4/instructions.md`
  2. Read `references/roles/skill/L4/instructions.md`
  3. Read `references/roles/qa/L4/instructions.md`
  4. Read `references/roles/dm/L4/instructions.md`
  5. For each, search for npm/distribution awareness language.
- **Expected**: Each file contains at minimum:
  - A statement that SquidSquad distributes via npm (`npx squidsquad`) and/or GitHub release tarballs.
  - A reference to `installer-files.txt` as the file manifest.
  - A note that changes to `references/` directory structure must be reflected in `installer-files.txt`.
  - A note that this is project-specific (other SquidSquad installations do not have this concern).
- **Verification**:
  ```bash
  for role in pm skill qa dm; do
    echo "--- $role ---"
    grep -i "npm\|installer-files\|tarball\|distribution" references/roles/$role/L4/instructions.md
  done
  # Expect: relevant lines present for each role
  ```

---

### TC-10: Full test suite regression

- **Precondition**: Implementation complete, compose.py deploy-all has run.
- **Steps**:
  1. Run the full test suite.
- **Expected**: All tests pass. Zero failures.
- **Verification**:
  ```bash
  python tests/run_tests.py
  # Expect: exit code 0, no failures reported
  ```

---

### TC-11: Deployed agent templates unchanged in behavior (regression)

- **Precondition**: Implementation complete, compose.py deploy-all has run.
- **Steps**:
  1. For each role (pm, skill, qa, dm), read `.squidsquad/<role>/CLAUDE.md`.
  2. Verify that all existing behavioral instructions (Ralph Loop steps, tracker protocol, verification gates, etc.) are present and unmodified.
  3. Verify that the new L4 content (packaging checklist, distribution awareness) is included in the deployed output.
- **Expected**: No existing behavioral instructions removed or altered. New L4 content is additive only.
- **Verification**: `git diff <pre-migration-commit> HEAD -- .squidsquad/*/CLAUDE.md` — inspect for removals (lines starting with `-`). Any removal of existing instructions is a failure.

---

### TC-12: compose.py deploy-all does not error with L4 content present

- **Precondition**: L4 source files exist and are populated.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all` from scratch (simulating a fresh agent boot or template update).
- **Expected**: Exit code 0, no errors or warnings written to stderr related to missing L4 files or malformed L4 content.
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all 2>&1
  echo "Exit: $?"
  # Expect: exit 0, no error lines
  ```

---

## Smoke Tests

- [ ] `references/roles/pm/L4/instructions.md` exists and contains "installer-files"
- [ ] `references/roles/dm/L4/instructions.md` exists and contains "npm publish"
- [ ] `python references/scripts/compose.py deploy-all` exits 0 after migration
- [ ] `python tests/run_tests.py` exits 0
- [ ] `.squidsquad/vault/BRIEFING.md` still exists (not deleted)
- [ ] `.squidsquad/pm/SOUL.md` still exists (not deleted — L4 is the new source, deployed file persists)
- [ ] soul_adaptation.py `add` subcommand exits 0 targeting L4 source

---

## Regression Risks

- **compose.py breakage**: If L4 is a new include layer that compose.py was not previously handling, compose may error or silently omit L4 content. TC-4 and TC-12 cover this.
- **soul_adaptation.py target drift**: If soul_adaptation.py still writes to `.squidsquad/<role>/SOUL.md` (deployed file) instead of the L4 source, Soul Shepherd signals will be overwritten on next compose run. TC-5 is the gate.
- **Deployed CLAUDE.md content loss**: If compose.py re-reads L4 files that are incomplete or missing sections, deployed agent instructions may be truncated. TC-11 is the gate.
- **Vault note deletion**: A migration script or developer cleanup could accidentally delete vault notes. TC-6 is the gate. Also check git log for `D` (deleted) status on `.squidsquad/vault/` files.
- **Double-write of packaging checklist**: If PM or DM CLAUDE.md already had partial distribution notes in L1/L2/L3, the L4 addition could create duplicate instructions. Inspect deployed CLAUDE.md for duplicate packaging paragraphs.
- **installer-files.txt path assumption**: The packaging checklist references `installer-files.txt` and `packages/cli/package.json`. If these paths change or do not exist in this repo, the checklist instructions will be misleading. Verify both paths exist before marking verified.
  ```bash
  ls installer-files.txt packages/cli/package.json
  ```
- **soul_adaptation.py render side effect**: If render re-generates the deployed SOUL.md by reading L4 source, but compose.py also generates the deployed SOUL.md from the same source, the render and compose outputs must be consistent. A mismatch would cause race conditions between the two tools.

---

## Comprehension Questions

### CQ-1: L4 packaging gate scope

- **Files**: `references/roles/pm/L4/instructions.md`, `references/roles/dm/L4/instructions.md`
- **Question**: During a pending-test verification, under what conditions does PM flag a change for DM delivery packaging review? What specific file does PM check, and what version comparison does PM make?
- **Expected answer**: PM checks whether the change affects distributed files. If yes, PM verifies that `installer-files.txt` is up to date (reflects any added, renamed, or removed files) and that `packages/cli/package.json` version matches the version in `config.md`. If distribution files changed, PM flags the item for DM delivery.

### CQ-2: npm distribution awareness scope

- **Files**: `references/roles/skill/L4/instructions.md` (or qa or any non-PM/DM role)
- **Question**: According to the L4 instructions for a dev/skill agent on this project, what is the significance of `installer-files.txt`, and why is this concern project-specific?
- **Expected answer**: `installer-files.txt` is the file manifest for distribution — it lists every file that gets included in the npm package and GitHub release tarball. Any change to the `references/` directory structure (new files, renamed files, removed files) must be reflected in `installer-files.txt`. This concern is project-specific because other SquidSquad installations using this skill do not publish an npm package; only this project does.

### CQ-3: Vault vs L4 distinction

- **Files**: `references/roles/pm/L4/instructions.md` or `references/roles/pm/L4/SOUL.md`, plus `.squidsquad/vault/BRIEFING.md`
- **Question**: A developer asks: "Now that Project Adaptation content is in L4 SOUL.md, can I delete the vault notes that originally contained similar information?" What does the L4 content say about this, and what is the correct answer?
- **Expected answer**: No. The vault notes must NOT be deleted. The vault is the encyclopedia — it holds decisions, patterns, learnings, and institutional knowledge as reference material. L4 is the operating manual — it holds actionable instructions. The migration moved content conceptually but vault notes become reference material that L4 can link to. Vault notes are never deleted as part of this migration.

### CQ-4: soul_adaptation.py write target

- **Files**: `references/roles/pm/L4/SOUL.md` (or equivalent), soul_adaptation.py source or its documentation in L4 instructions
- **Question**: When Soul Shepherd detects a new signal (e.g., a new tech-stack entry) and calls soul_adaptation.py, what file does it write to, and what must happen afterward for the deployed agent to see the new signal?
- **Expected answer**: soul_adaptation.py writes the new signal to the L4 source file (`references/roles/<role>/L4/SOUL.md`). The deployed SOUL.md (`.squidsquad/<role>/SOUL.md`) is not updated directly. For the deployed agent to see the new signal, `compose.py deploy-all` must be run to re-render the deployed files from the L4 source.

---

## Notes

- TC-4 requires either a committed baseline snapshot or that compose.py is run immediately before and after migration in the same git working tree (use `git stash` strategy if needed).
- If the dev chooses to store L4 files under `references/sub-skills/project/` rather than `references/roles/*/L4/`, adjust all path checks above to match the actual chosen path. The logical tests remain the same.
- TC-5 cleanup is mandatory — do not leave test signals in L4 source files.
- All TC-10 failures are blocking. No "ship with caveats" on a failing test suite.

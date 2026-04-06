# FEAT-149 Test Plan — Extract SOUL.md as Runtime-Injectable Files

**Feature**: Agent personality separate from template — souls as editable runtime files
**Scope**: compose.py `{{runtime:}}` directive, SOUL.md deploy lifecycle, CLAUDE.md output verification
**Source**: FEAT-149-RESEARCH.md, FEAT-149-CONTEXT.md

---

## Unit Tests (pytest)

### TC-1: compose.py `{{runtime:}}` directive emits read instruction, not inline content

- **Precondition**: A test entry file containing `{{runtime: souls/dev}}` exists (created in test fixture via `tmp_path`).
- **Steps**:
  1. Create a minimal entry file with `{{runtime: souls/dev}}` as its first line and a body line below it.
  2. Create a matching `souls/dev.md` file in the test sub-skills directory (to confirm it is NOT inlined).
  3. Call `_resolve_includes()` (or the new handler) on the entry file.
- **Expected**: The returned text contains a runtime read instruction (e.g., "Read your personality and behavioral guidelines from" or "SOUL.md") and does NOT contain the literal content of `souls/dev.md`.
- **Verification**: `assert "SOUL.md" in result` and `assert souls_dev_content not in result`.

### TC-2: compose.py deploy creates SOUL.md if missing, does not overwrite existing

- **Precondition**: A clean temporary `.squidsquad/<role>/` directory with no `SOUL.md`.
- **Steps**:
  1. Run `deploy_role("skill")` against the temp directory (or mock paths).
  2. Assert `SOUL.md` was created at `.squidsquad/skill/SOUL.md`.
  3. Modify the created `SOUL.md` (append a marker line: `# CUSTOM`).
  4. Run `deploy_role("skill")` again.
  5. Read `SOUL.md` content after the second deploy.
- **Expected**: After step 2, `SOUL.md` exists and contains the default soul template content. After step 4, `SOUL.md` still contains the `# CUSTOM` marker — it was not overwritten.
- **Verification**: `assert "# CUSTOM" in soul_content_after_redeploy`.

### TC-3: Default SOUL.md templates exist for all role types

- **Precondition**: `references/sub-skills/souls/` directory exists.
- **Steps**:
  1. List all `.md` files in `references/sub-skills/souls/`.
  2. Compare against the expected set: `{dev, pm, qa, dm, designer}`.
  3. For each file, verify it is non-empty (at least 10 lines).
- **Expected**: All five soul templates exist and each has substantive content.
- **Verification**: `assert set(found_souls) == {"dev", "pm", "qa", "dm", "designer"}` and `assert len(lines) >= 10` for each.

### TC-4: Generated CLAUDE.md contains runtime read instruction, NOT inline soul content

- **Precondition**: `compose.py deploy skill` has been run (or `compose_role` called in test).
- **Steps**:
  1. Run `deploy_role("skill")` to generate `.squidsquad/skill/CLAUDE.md`.
  2. Read the generated CLAUDE.md content.
  3. Read the source soul content from `references/sub-skills/souls/dev.md`.
  4. Check for the runtime instruction pattern.
  5. Check that the inline soul content is absent.
- **Expected**: CLAUDE.md contains a "Read ... SOUL.md" instruction. CLAUDE.md does NOT contain the full soul template text (specifically, does not contain `<!-- sub-skill: dev -->` markers wrapping soul content).
- **Verification**: `assert "SOUL.md" in claude_md` and `assert "<!-- sub-skill: dev -->" not in claude_md` (for the soul section specifically — other sub-skills may still use markers).

---

## Integration Tests (in-situ)

### TC-5: compose.py deploy skill on this repo — generates CLAUDE.md with runtime instruction AND creates SOUL.md

- **Precondition**: Working repo checkout. Back up existing `.squidsquad/skill/CLAUDE.md` and `.squidsquad/skill/SOUL.md` (if present).
- **Steps**:
  1. Delete `.squidsquad/skill/SOUL.md` if it exists.
  2. Run `python references/scripts/compose.py deploy skill`.
  3. Read `.squidsquad/skill/CLAUDE.md`.
  4. Check `.squidsquad/skill/SOUL.md` exists.
- **Expected**: Command exits 0. CLAUDE.md contains a runtime read instruction referencing SOUL.md. SOUL.md exists and is non-empty.
- **Verification**: `grep -q "SOUL.md" .squidsquad/skill/CLAUDE.md` exits 0. `test -f .squidsquad/skill/SOUL.md` exits 0.

### TC-6: SOUL.md content matches the default template for each role

- **Precondition**: Fresh deploy (SOUL.md files deleted before test).
- **Steps**:
  1. For each role in `{skill, pm}` (or all configured roles):
     a. Delete `.squidsquad/<role>/SOUL.md`.
     b. Run `python references/scripts/compose.py deploy <role>`.
     c. Read the deployed `.squidsquad/<role>/SOUL.md`.
     d. Read the source template from `references/sub-skills/souls/<mapped-role>.md` (skill maps to dev, etc.).
     e. Compare content.
- **Expected**: Deployed SOUL.md content matches the source template exactly (or with expected role-name substitutions).
- **Verification**: `diff .squidsquad/skill/SOUL.md references/sub-skills/souls/dev.md` returns no differences (or only expected placeholder substitutions).

### TC-7: Existing SOUL.md not overwritten by deploy

- **Precondition**: `.squidsquad/skill/SOUL.md` exists from a previous deploy.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy skill` to ensure SOUL.md exists.
  2. Append a unique marker to `.squidsquad/skill/SOUL.md`: `echo "# HUMAN-CUSTOM-MARKER-TC7" >> .squidsquad/skill/SOUL.md`.
  3. Run `python references/scripts/compose.py deploy skill` again.
  4. Read `.squidsquad/skill/SOUL.md`.
- **Expected**: The marker `# HUMAN-CUSTOM-MARKER-TC7` is still present in SOUL.md after the second deploy.
- **Verification**: `grep -q "HUMAN-CUSTOM-MARKER-TC7" .squidsquad/skill/SOUL.md` exits 0.

### TC-8: All existing tests still pass after the change

- **Precondition**: Feature implementation complete. All modified files committed.
- **Steps**:
  1. Run `python tests/run_tests.py` (or `python -m pytest tests/ -q`).
- **Expected**: Exit code 0. All tests pass, including pre-existing tests in `test_composition.py`, `test_roles.py`, `test_manifest.py`, etc.
- **Verification**: Zero failures in pytest output. No new test collection errors.

---

## Side Effect Regression

### TC-9: Agent CLAUDE.md no longer contains inline soul markers

- **Precondition**: `compose.py deploy skill` has been run with the new `{{runtime:}}` directive.
- **Steps**:
  1. Read `.squidsquad/skill/CLAUDE.md`.
  2. Search for `<!-- sub-skill: dev -->` followed by soul content (personality, quality bar, decision-making sections).
  3. Search for `<!-- /sub-skill: dev -->` that previously closed the soul section.
- **Expected**: The soul-specific sub-skill markers are absent. Other sub-skill markers (e.g., `<!-- sub-skill: tracker-protocol -->`, `<!-- sub-skill: ralph-loop -->`) may still be present — only the soul markers should be removed.
- **Verification**: `grep -c "sub-skill: dev" .squidsquad/skill/CLAUDE.md` returns 0 (assuming `dev` was the soul sub-skill name; adjust if the soul sub-skill name differs from the role entry name). Repeat for `pm`, `qa`, `dm`, `designer` on their respective CLAUDE.md files.

### TC-10: SOUL.md is git-tracked (not in .gitignore)

- **Precondition**: `.squidsquad/skill/SOUL.md` exists after deploy.
- **Steps**:
  1. Run `git check-ignore .squidsquad/skill/SOUL.md`.
  2. Run `git ls-files .squidsquad/skill/SOUL.md` (after staging/committing).
- **Expected**: `git check-ignore` returns exit code 1 (file is NOT ignored). `git ls-files` returns the file path (file IS tracked or trackable).
- **Verification**: `git check-ignore .squidsquad/skill/SOUL.md; echo $?` prints `1`. No `.gitignore` entry matches `SOUL.md` or `*.md` under `.squidsquad/`.

### TC-11: Missing SOUL.md fallback — CLAUDE.md runtime instruction includes abbreviated defaults

- **Precondition**: `compose.py deploy skill` has been run.
- **Steps**:
  1. Read `.squidsquad/skill/CLAUDE.md`.
  2. Search for fallback language (e.g., "If SOUL.md does not exist" or "operate with professional defaults" or similar).
- **Expected**: The runtime read instruction block in CLAUDE.md includes a fallback clause telling the agent what to do if SOUL.md is missing. The agent should not halt — it should continue with defaults.
- **Verification**: `grep -q -i "does not exist\|missing\|default" .squidsquad/skill/CLAUDE.md` exits 0 within the SOUL.md instruction section.

---

## Smoke Tests (manual)

### SM-1: Deploy and inspect visually

- Run `python references/scripts/compose.py deploy skill`.
- Open `.squidsquad/skill/CLAUDE.md` — confirm the soul section is replaced by a short read instruction paragraph (not 50+ lines of personality content).
- Open `.squidsquad/skill/SOUL.md` — confirm it contains the full personality content (Professional Identity, Quality Bar, Decision-Making Style, etc.).

### SM-2: Edit SOUL.md and verify persistence

- Edit `.squidsquad/skill/SOUL.md` — change "You are an engineer" to "You are a pirate engineer".
- Run `python references/scripts/compose.py deploy skill`.
- Verify `.squidsquad/skill/SOUL.md` still says "pirate engineer" (not overwritten).
- Verify `.squidsquad/skill/CLAUDE.md` still has the read instruction (not the pirate text inline).

### SM-3: Delete SOUL.md and redeploy

- Delete `.squidsquad/skill/SOUL.md`.
- Run `python references/scripts/compose.py deploy skill`.
- Verify `.squidsquad/skill/SOUL.md` is recreated from the default template.
- Verify `.squidsquad/skill/CLAUDE.md` is valid and contains the runtime instruction.

### SM-4: deploy-all creates SOUL.md for every configured role

- Delete all `SOUL.md` files under `.squidsquad/*/`.
- Run `python references/scripts/compose.py deploy-all`.
- Verify each role directory has a `SOUL.md` file.

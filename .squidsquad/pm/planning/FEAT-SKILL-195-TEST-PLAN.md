# FEAT-SKILL-195 Test Plan — Extract Ralph Loop Steps as Modular Sub-Skills

## Phase A — Engine (Manifest-Driven Composition)

### TC-A1: includes.yml exists per role directory
- **Precondition**: Phase A implementation complete
- **Steps**: Check that each role directory contains an includes.yml
- **Expected**: Files exist at:
  - `references/roles/pm/includes.yml`
  - `references/roles/dev/includes.yml`
  - `references/roles/qa/includes.yml`
  - `references/roles/dm/includes.yml`
  - `references/roles/designer/includes.yml`
- **Verification**:
  ```bash
  for role in pm dev qa dm designer; do
    test -f "references/roles/$role/includes.yml" && echo "$role: OK" || echo "$role: MISSING"
  done
  ```

### TC-A2: includes.yml lists all current includes per role
- **Precondition**: TC-A1 passes
- **Steps**: For each role, compare the includes listed in includes.yml against the `{{include:}}` directives in the role's CLAUDE.md template
- **Expected**: Every `{{include:}}` directive currently in each role template has a corresponding entry in includes.yml. No includes added or removed.
- **Verification**:
  ```bash
  for role in pm dev qa dm designer; do
    echo "--- $role ---"
    grep -c '{{include:' "references/roles/$role/CLAUDE.md"
    python -c "import yaml; print(sum(len(v) if isinstance(v,list) else 1 for v in yaml.safe_load(open('references/roles/$role/includes.yml')).values()))"
  done
  ```

### TC-A3: compose.py reads includes.yml and resolves includes
- **Precondition**: TC-A1 passes, compose.py updated
- **Steps**: Run `python references/scripts/compose.py deploy` for a single role (e.g., qa)
- **Expected**: compose.py reads `references/roles/qa/includes.yml`, resolves each listed sub-skill, and produces a composed CLAUDE.md
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy --role qa --dry-run 2>&1 | head -50
  ```

### TC-A4: Composed output IDENTICAL before/after (zero behavioral change)
- **Precondition**: TC-A3 passes
- **Steps**:
  1. Before Phase A changes, save composed output for all 5 roles as baseline snapshots
  2. After Phase A changes, recompose all 5 roles
  3. Diff each role's composed output against its baseline
- **Expected**: Zero diff for all 5 roles. Not "similar" — byte-identical (ignoring trailing whitespace at most).
- **Verification**:
  ```bash
  # Before Phase A (run once, save baselines):
  for role in pm dev qa dm designer; do
    cp ".squidsquad/$role/CLAUDE.md" "/tmp/baseline-$role-CLAUDE.md"
  done

  # After Phase A:
  python references/scripts/compose.py deploy
  for role in pm dev qa dm designer; do
    diff "/tmp/baseline-$role-CLAUDE.md" ".squidsquad/$role/CLAUDE.md" && echo "$role: IDENTICAL" || echo "$role: DIFFERS"
  done
  ```

### TC-A5: Custom dev variants inherit from dev manifest
- **Precondition**: TC-A3 passes, a custom dev variant exists (e.g., `be` or `fe`)
- **Steps**:
  1. Create a minimal custom variant directory (e.g., `references/roles/be/`) with a CLAUDE.md that extends dev
  2. Do NOT create `references/roles/be/includes.yml`
  3. Run compose.py for the `be` role
- **Expected**: compose.py falls back to `references/roles/dev/includes.yml` and composes successfully using dev's manifest
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy --role be 2>&1 | grep -i "inherit\|fallback\|using dev"
  # Composed output should include all dev sub-skills
  ```

### TC-A6: Custom dev variant with override manifest
- **Precondition**: TC-A5 passes
- **Steps**:
  1. Create `references/roles/be/includes.yml` with one sub-skill removed vs dev's manifest
  2. Run compose.py for the `be` role
- **Expected**: compose.py uses the `be`-specific manifest, producing output that differs from dev's output by exactly the removed sub-skill
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy --role be
  diff ".squidsquad/be/CLAUDE.md" ".squidsquad/dev/CLAUDE.md" | head -30
  ```

### TC-A7: Old {{include:}} directives still work alongside manifests
- **Precondition**: TC-A3 passes
- **Steps**:
  1. In a test role template, add a manual `{{include: common/pull-latest}}` directive alongside the manifest
  2. Run compose.py
- **Expected**: compose.py resolves both manifest entries and inline `{{include:}}` directives without error. The sub-skill appears once (deduplication) or compose.py warns about the duplicate.
- **Verification**: Manual inspection of composed output for duplicate sections

### TC-A8: includes.yml with invalid sub-skill path
- **Precondition**: TC-A3 passes
- **Steps**: Add a non-existent sub-skill path to a role's includes.yml (e.g., `common/does-not-exist`)
- **Expected**: compose.py fails with a clear error message naming the missing file and the role
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy --role qa 2>&1 | grep -i "error\|not found\|missing"
  ```

---

## Phase B — Slim Variants

### TC-B1: vault-protocol-slim.md exists and is shorter
- **Precondition**: Phase B implementation complete
- **Steps**: Check file existence and compare size
- **Expected**: `references/sub-skills/common/vault-protocol-slim.md` exists and is significantly shorter than `references/sub-skills/common/vault-protocol.md` (target ~800 tokens vs ~3,059 tokens)
- **Verification**:
  ```bash
  wc -c references/sub-skills/common/vault-protocol.md references/sub-skills/common/vault-protocol-slim.md
  # slim should be roughly 25-35% of full size
  ```

### TC-B2: improvement-scan-slim.md exists and is shorter
- **Precondition**: Phase B implementation complete
- **Steps**: Check file existence and compare size
- **Expected**: `references/sub-skills/common/improvement-scan-slim.md` exists and is significantly shorter than `references/sub-skills/common/improvement-scan.md` (target ~300 tokens vs ~1,104 tokens)
- **Verification**:
  ```bash
  wc -c references/sub-skills/common/improvement-scan.md references/sub-skills/common/improvement-scan-slim.md
  # slim should be roughly 25-35% of full size
  ```

### TC-B3: vault-protocol-slim contains read-only instructions
- **Precondition**: TC-B1 passes
- **Steps**: Read vault-protocol-slim.md content
- **Expected**: Contains vault reading/searching instructions. Does NOT contain vault-create, vault-update write instructions, or Changelog append instructions.
- **Verification**:
  ```bash
  grep -c "vault-create\|vault-update\|Creating Notes\|Updating Notes" references/sub-skills/common/vault-protocol-slim.md
  # Should be 0
  grep -c "vault-search\|Searching\|BRIEFING" references/sub-skills/common/vault-protocol-slim.md
  # Should be > 0
  ```

### TC-B4: improvement-scan-slim contains file-only instructions
- **Precondition**: TC-B2 passes
- **Steps**: Read improvement-scan-slim.md content
- **Expected**: Contains instructions to file improvement suggestions (one-line). Does NOT contain the full multi-step scanning analysis flow.
- **Verification**: Manual content review — slim variant should describe filing findings only, not the full scan criteria/file selection/analysis loop

### TC-B5: QA role composes with slim variants
- **Precondition**: TC-B1, TC-B2 pass; QA includes.yml updated
- **Steps**: Run compose.py for qa role
- **Expected**: QA CLAUDE.md contains vault-protocol-slim content (not full vault-protocol) and improvement-scan-slim content (not full improvement-scan)
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy --role qa
  grep -c "vault-protocol-slim\|sub-skill: vault-protocol-slim" .squidsquad/qa/CLAUDE.md
  grep -c "improvement-scan-slim\|sub-skill: improvement-scan-slim" .squidsquad/qa/CLAUDE.md
  # Both should be > 0
  grep -c "sub-skill: vault-protocol -->" .squidsquad/qa/CLAUDE.md
  # Should be 0 (full variant not present)
  ```

### TC-B6: DM role composes with slim variants
- **Precondition**: Same as TC-B5
- **Steps**: Run compose.py for dm role
- **Expected**: Same as TC-B5 but for DM
- **Verification**: Same grep pattern as TC-B5 against `.squidsquad/dm/CLAUDE.md`

### TC-B7: Designer role composes with slim variants
- **Precondition**: Same as TC-B5
- **Steps**: Run compose.py for designer role
- **Expected**: Same as TC-B5 but for Designer
- **Verification**: Same grep pattern as TC-B5 against `.squidsquad/designer/CLAUDE.md`

### TC-B8: PM role still uses full variants
- **Precondition**: TC-B5 passes
- **Steps**: Run compose.py for pm role
- **Expected**: PM CLAUDE.md contains full vault-protocol (not slim) and full improvement-scan (not slim)
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy --role pm
  grep -c "sub-skill: vault-protocol -->" .squidsquad/pm/CLAUDE.md
  # Should be > 0 (full variant present)
  grep -c "vault-protocol-slim" .squidsquad/pm/CLAUDE.md
  # Should be 0 (slim NOT present)
  ```

### TC-B9: Dev role still uses full variants
- **Precondition**: Same as TC-B8
- **Steps**: Run compose.py for dev role
- **Expected**: Dev CLAUDE.md contains full vault-protocol and full improvement-scan
- **Verification**: Same grep pattern as TC-B8 against `.squidsquad/dev/CLAUDE.md`

### TC-B10: Token count reduced ~22% for non-PM roles
- **Precondition**: TC-B5, TC-B6, TC-B7 pass
- **Steps**: Measure token count (estimated via char count / 4) for QA, DM, Designer before and after Phase B
- **Expected**:
  - QA: ~12,089 tokens before, ~9,400 after (~22% reduction)
  - DM: ~11,804 tokens before, ~9,200 after (~22% reduction)
  - Designer: ~12,853 tokens before, ~10,100 after (~21% reduction)
  - Tolerance: within 5 percentage points of target
- **Verification**:
  ```bash
  for role in qa dm designer; do
    chars=$(wc -c < ".squidsquad/$role/CLAUDE.md")
    tokens=$((chars / 4))
    echo "$role: ~$tokens tokens ($chars chars)"
  done
  ```

### TC-B11: No behavioral regression — slim variant agents function correctly
- **Precondition**: TC-B5, TC-B6, TC-B7 pass
- **Steps**:
  1. Read the composed QA CLAUDE.md
  2. Verify it still contains: tracker-protocol, pull-latest, boot-remote-agents, verification sub-skill, all QA-specific sub-skills
  3. Verify vault-protocol-slim includes vault-search capability (read-only roles must still search the vault)
  4. Verify improvement-scan-slim includes the ability to file findings via tracker
- **Expected**: All core role functionality preserved. Only write-heavy vault operations and full scan analysis removed.
- **Verification**: Manual review of each slim-variant role's composed CLAUDE.md for completeness

### TC-B12: vault-remember and vault-optimize excluded from read-only roles
- **Precondition**: Phase B manifests updated
- **Steps**: Check QA, DM, Designer composed output
- **Expected**: vault-remember and vault-optimize sub-skill markers absent from QA, DM, Designer composed CLAUDE.md
- **Verification**:
  ```bash
  for role in qa dm designer; do
    echo "--- $role ---"
    grep -c "sub-skill: vault-remember\|sub-skill: vault-optimize" ".squidsquad/$role/CLAUDE.md"
    # Should be 0 for each
  done
  ```

---

## Phase C — PM Extraction

### TC-C1: PM inline Ralph Loop steps extracted as sub-skills
- **Precondition**: Phase C implementation complete
- **Steps**: Check that previously inline PM steps now exist as sub-skill files in `references/sub-skills/pm-specific/`
- **Expected**: New sub-skill files exist for extracted steps (e.g., health-check step, e2e-test step, verify-issues step, etc.)
- **Verification**:
  ```bash
  ls references/sub-skills/pm-specific/
  # Should show new files for extracted steps
  ```

### TC-C2: PM CLAUDE.md shrinks after extraction
- **Precondition**: TC-C1 passes
- **Steps**: Compare PM composed CLAUDE.md size before and after Phase C
- **Expected**: PM CLAUDE.md is measurably smaller (target ~1,300-3,500 token reduction from Phase B baseline)
- **Verification**:
  ```bash
  # Compare against Phase B baseline
  wc -c ".squidsquad/pm/CLAUDE.md"
  # Compare against saved baseline
  ```

### TC-C3: PM behavior unchanged after extraction
- **Precondition**: TC-C1, TC-C2 pass
- **Steps**:
  1. Read the PM composed CLAUDE.md
  2. Verify all Ralph Loop steps are still present (either inline or via sub-skill include)
  3. Verify step ordering is preserved
  4. Verify no instructions were lost in extraction
- **Expected**: The full PM behavioral specification is intact — same steps, same order, same instructions. Only the delivery mechanism changed (inline to sub-skill).
- **Verification**: Manual diff of PM behavioral content before/after extraction. Every instruction sentence from the pre-extraction version must appear in the post-extraction version.

### TC-C4: Extracted sub-skills have correct include markers
- **Precondition**: TC-C1 passes
- **Steps**: Check that extracted PM sub-skills are wrapped in `<!-- sub-skill: name -->` markers in composed output
- **Expected**: Each extracted step appears with proper sub-skill markers, consistent with other sub-skills
- **Verification**:
  ```bash
  grep "sub-skill:" ".squidsquad/pm/CLAUDE.md" | sort
  # Extracted steps should appear in this list
  ```

### TC-C5: PM includes.yml updated with extracted sub-skills
- **Precondition**: TC-C1 passes
- **Steps**: Read `references/roles/pm/includes.yml`
- **Expected**: New extracted sub-skill entries appear in the manifest
- **Verification**:
  ```bash
  cat references/roles/pm/includes.yml
  # Should list the newly extracted pm-specific sub-skills
  ```

---

## Cross-Cutting Tests

### TC-X1: Full compose deploys successfully after each phase
- **Precondition**: Each phase complete
- **Steps**: Run `python references/scripts/compose.py deploy` for all roles
- **Expected**: Exit code 0, no errors, all 5 role CLAUDE.md files written
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy
  echo "Exit code: $?"
  for role in pm dev qa dm designer; do
    test -f ".squidsquad/$role/CLAUDE.md" && echo "$role: OK" || echo "$role: MISSING"
  done
  ```

### TC-X2: manifest.md updated to document new composition model
- **Precondition**: Phase A complete
- **Steps**: Check that project documentation reflects the new manifest-driven composition
- **Expected**: manifest.md (or equivalent docs) describes includes.yml format, inheritance, and slim variants
- **Verification**: Manual review of documentation files

### TC-X3: squidsquad-upgrade recomposes correctly
- **Precondition**: Each phase complete
- **Steps**: Run the squidsquad-upgrade flow
- **Expected**: Upgrade process reads new manifests and produces correct composed output for all roles
- **Verification**:
  ```bash
  # Simulate upgrade by re-running compose
  python references/scripts/compose.py deploy
  # Verify output matches expectations per current phase
  ```

### TC-X4: No content loss (diff audit)
- **Precondition**: Baselines saved before each phase
- **Steps**: After each phase, diff all composed CLAUDE.md files against their pre-phase baselines
- **Expected**:
  - Phase A: zero diff (identical output)
  - Phase B: diffs are strictly subtractive for QA/DM/Designer (slim replaces full) and zero for PM/Dev
  - Phase C: diffs are strictly subtractive for PM (extraction) and zero for all others
- **Verification**:
  ```bash
  for role in pm dev qa dm designer; do
    echo "--- $role ---"
    diff "/tmp/baseline-$role-CLAUDE.md" ".squidsquad/$role/CLAUDE.md" | head -20
  done
  ```

### TC-X5: Sub-skill dependency integrity
- **Precondition**: Phase B complete
- **Steps**: Verify that vault-remember is excluded from roles that use vault-protocol-slim (since vault-remember references vault-protocol concepts)
- **Expected**: No role has vault-remember without also having vault-protocol (full). Roles with vault-protocol-slim do not include vault-remember.
- **Verification**:
  ```bash
  for role in qa dm designer; do
    echo "--- $role ---"
    grep -c "vault-remember" ".squidsquad/$role/CLAUDE.md"
    # Should be 0 if using vault-protocol-slim
  done
  ```

### TC-X6: YAML manifest syntax validation
- **Precondition**: Phase A complete
- **Steps**: Parse each includes.yml with a YAML parser
- **Expected**: All 5 manifests are valid YAML, no syntax errors
- **Verification**:
  ```bash
  for role in pm dev qa dm designer; do
    python -c "import yaml; yaml.safe_load(open('references/roles/$role/includes.yml'))" && echo "$role: valid YAML" || echo "$role: INVALID"
  done
  ```

---

## Smoke Tests

- [ ] `python references/scripts/compose.py deploy` completes without error
- [ ] All 5 `.squidsquad/*/CLAUDE.md` files exist and are non-empty after deploy
- [ ] `includes.yml` exists in all 5 role directories
- [ ] slim variant files exist in `references/sub-skills/common/`
- [ ] PM composed output is the largest; QA/DM are the smallest
- [ ] No `{{include:` directives remain unresolved in any composed output

## Regression Risks

- **Vault write capability silently lost**: QA/DM/Designer agents may attempt vault writes after Phase B and silently fail or produce confusing errors. Monitor agent logs in early cycles.
- **Improvement scan degradation**: Slim improvement-scan may cause agents to file incomplete or low-quality findings. Compare scan quality before/after.
- **Manifest drift**: When new sub-skills are added in the future, forgetting to add them to includes.yml means they silently disappear from roles. Consider adding a compose.py warning for sub-skills that exist but are not referenced by any manifest.
- **Inheritance edge cases**: Custom dev variants that override only part of the manifest may get unexpected combinations if the merge strategy is not well-defined.
- **PM extraction order sensitivity**: If PM inline steps reference each other or share context (e.g., Step 5 references a variable set in Step 3), extracting them as independent sub-skills may break implicit dependencies.

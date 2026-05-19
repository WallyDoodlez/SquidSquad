Now I have a complete picture. Let me compile my final review.

---

## Review Summary

I've systematically examined all four changed files against the 4 acceptance criteria, 4 regression risks, and 4 comprehension questions defined in `TEST-PLAN-8950.md`. Each gate is structurally verified, each guard clause is present, and no cross-contamination exists into PM's composition path.

---

### AC-1 — Gate #2: Code-review §9c (dev/implement-tasks.md)

- **Discovery glob** (line 51): `ARTIFACTS=$(ls .squidsquad/pm/planning/*[NUMBER]* 2>/dev/null | paste -sd, -)` — task-number-match glob covers legacy `FEAT-PM-*-TEST-PLAN.md` and new `TEST-PLAN-*.md` and `CONTEXT-*.md` siblings. The `paste -sd, -` formatting addition correctly prepares comma-separated input for `--input-files`.
- **Appending to --input-files** (lines 56-59): `INPUT_FILES="$CHANGED_FILES${ARTIFACTS:+,$ARTIFACTS}"` — non-empty ARTIFACTS prepends comma and appends; empty ARTIFACTS is a no-op.
- **Review prompt** (line 64): `--context "... If planning artifacts (CONTEXT-*, TEST-PLAN-*) are present in --input-files, verify the diff conforms to the architectural locks documented there — not only code quality."` — architectural-locks check directive present.
- **Coordination with #8916** (line 46): References `#8950 Gate #2 / #8916 §9c` — appropriate cross-reference.

**Verdict: PASS**

---

### AC-2 — Gate #3: QA AC walk (qa/verification.md)

- **Discovery glob** (line 197): `TEST_PLAN=$(ls .squidsquad/pm/planning/*[NUMBER]* 2>/dev/null | grep -i 'test-plan' | head -1)` — broad task-number glob then grep-filter for `test-plan` (case-insensitive). Correctly handles both legacy `FEAT-PM-8950-TEST-PLAN.md` and new `TEST-PLAN-8950.md`. The `head -1` addition is a reasonable defensive guard against multiple matches.
- **No-TEST-PLAN case** (line 200): "If `$TEST_PLAN` is empty (bug fix or trivial task with no planning artifact): skip this AC walk, proceed with the existing verification flow." — explicit skip path.
- **Key phrases** (line 201): "walk its AC list" + "**Tests passing is necessary but not sufficient — do not infer AC satisfaction from test names.**" — both required phrases present verbatim.
- **Failure path** (lines 202-204): Transition `pending-test → in-progress` with comment naming the failed AC and `$TEST_PLAN` filename.
- **Placement**: Step 2d sits after 2c (full test suite) and before step 3 (zero-gap gate), as required.

**Verdict: PASS**

---

### AC-3 — Gate #4: DM contract-citation (dm/delivery-packaging.md)

- **Discovery glob** (line 47): `ARTIFACTS=$(ls .squidsquad/pm/planning/*[NUMBER]* 2>/dev/null)` — task-number-match.
- **Empty ARTIFACTS path** (line 50): "the citation gate does not apply — proceed with the merge request below."
- **Non-empty + no citation** (lines 51-55): Blocks merge, transitions `pending-ship → pending-test` (explicit transition), comments with canned message.
- **Canned message** (line 54): `"PR does not cite the planning contract; cannot verify architectural conformance. QA: confirm AC walk completed against the planning artifacts listed in .squidsquad/pm/planning/*[NUMBER]*."` — references "AC walk completed against the planning artifacts" and uses `*[NUMBER]*` glob, NOT a hardcoded literal filename path.
- **Placement**: Step 0b, BEFORE the merge curl (line 58), as required.

**Verdict: PASS**

---

### AC-4 — PM CLAUDE.md byte-identical after recompose

- **Changed files**: `references/sub-skills/roles/dev/implement-tasks.md`, `references/sub-skills/roles/qa/verification.md`, `references/sub-skills/roles/dm/delivery-packaging.md`.
- **PM manifest** (`references/roles/pm/includes.yml` and `includes-events.yml`): Both include only `roles/pm/*` and `common/*` / `common-events/*` entries. None of the three changed files appear.
- **Dev manifest** (`references/roles/dev/includes.yml` line 12): includes `roles/dev/implement-tasks`.
- **QA manifest** (`references/roles/qa/includes.yml` line 9): includes `roles/qa/verification`.
- **DM manifest** (`references/roles/dm/includes.yml` line 11): includes `roles/dm/delivery-packaging`.
- **Conclusion**: PM CLAUDE.md sources are untouched; dev/qa/dm CLAUDE.md will change as expected. The user-reported 5-blank-line whitespace shift in PM CLAUDE.md is a pre-existing stale-on-disk artifact, not caused by these edits.

**Verdict: PASS**

---

### Regression Risks

| Risk | Status | Evidence |
|------|--------|----------|
| **R1** (DM gate noise) | **Mitigated** | DM §0b line 50: `$ARTIFACTS` empty → "citation gate does not apply — proceed with the merge request below." Bug fixes/trivial tasks without planning files skip entirely. |
| **R2** (QA AC-walk overhead) | **Accepted** | Per TEST-PLAN: trade-off explicitly accepted. |
| **R3** (#8916 coordination) | **Handled** | dev §9c line 46 cross-references both issues; PR description expected to note coordination. |
| **R4** (file naming conventions) | **Mitigated** | All three fragments use `*[NUMBER]*` glob; no literal `TEST-PLAN-<NUMBER>.md` filename appears in any fragment. DM line 51 prose examples use `[NUMBER]` placeholder. |

---

### Comprehension Question Derivability

| CQ | Derivable? | Evidence |
|-----|-----------|----------|
| **CQ-1** (QA: don't transition on tests alone) | Yes | qa/verification.md lines 194-204: discovery glob → AC walk → "tests passing is necessary but not sufficient" → on failure, transition `pending-test → in-progress` with AC-named comment. |
| **CQ-2** (DM: block merge when no citation) | Yes | dm/delivery-packaging.md lines 46-55: discovery glob → non-empty check → scan PR body → no reference → `pending-ship → pending-test` with canned message. |
| **CQ-3** (dev: pass planning files to code review) | Yes | dev/implement-tasks.md lines 44-64: discovery glob → append to `--input-files` → context prompt requires deepseek verify "architectural locks." |
| **CQ-4** (DM: gate no-op without artifacts) | Yes | dm/delivery-packaging.md line 50: "If `$ARTIFACTS` is empty... the citation gate does not apply — proceed with the merge request below." |

---

### Additional Cross-Checks Performed

- **Shell correctness**: All three discovery globs use `2>/dev/null` to suppress stderr on no-match; `$()` captures stdout only; empty ARTIFACTS/TEST_PLAN results work correctly in all conditional paths. The `paste -sd, -` in dev §9c works correctly for single-file, multi-file, and no-match cases.
- **Transition consistency**: All three gates use the correct tracker transition commands with `--role` flags matching the gate owner (`--role [ROLE]-lead` for dev, `--role qa-lead` for QA, `--role dm-lead` for DM).
- **No cross-role contamination**: All three sub-skills are role-specific and isolated to their respective manifests.
- **Task-number placeholder convention**: All `[NUMBER]` placeholders follow the established codebase convention (LLM-substituted before shell execution), consistent with every other command in these files.

---

## NO_FINDINGS

All 4 acceptance criteria are satisfied. All 4 regression risks are appropriately mitigated or accepted. All 4 comprehension questions are clearly derivable from the composed fragments. The three sub-skill edits are structurally sound, correctly placed, and contain appropriate guard clauses for all edge cases. PM CLAUDE.md byte-identity is preserved. Full test suite (2475 pytest + 17 integration) GREEN confirms no regressions.
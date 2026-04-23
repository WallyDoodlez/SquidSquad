# FEAT-SKILL-361 QA Results -- Project-Adaptive Role Souls

## Summary

- **Total**: 10 test cases executed
- **PASS**: 7
- **FAIL**: 3
- **Date**: 2026-04-22

### Failures

1. **TC-7**: config.py `project-intent` field mapping exists in code but `config.md` has no `Project > Intent Description` field -- `config.py get project-intent` returns error exit 1.
2. **TC-6**: PM live CLAUDE.md was not recomposed after soul-shepherd sub-skill was added. Compose deploy was needed to inject the sub-skill content.
3. **TC-6 (sub)**: After compose deploy, soul-shepherd markers are duplicated (`<!-- sub-skill: soul-shepherd -->` appears twice on open and close). This is a composition bug.

---

### TC-1: soul_adaptation.py unit tests (13 tests)
- **Result**: PASS
- **Notes**: All 13 tests pass: TestAddAdaptation (4), TestRenderSection (2), TestRenderSoul (3), TestCheckCap (2), TestGetAdaptations (2). Covers file creation, entry parsing, multi-role support, cap checking, rendering, section replacement, and content preservation.

### TC-2: Full test suite regression
- **Result**: PASS
- **Notes**: 881 passed, 2 failed. Both failures are pre-existing and unrelated to #361: `test_no_duplicate_opens` (duplicate `self-restart` marker in skill CLAUDE.md) and `test_dev_agent_has_working_state` (missing `boot/working-state.md`). No regressions introduced by #361.

### TC-3: CLI smoke -- usage/help
- **Result**: PASS
- **Notes**: `python references/scripts/soul_adaptation.py` with no args prints full usage doc covering render, add, check-cap, list commands with exit code descriptions. Returns exit code 2.

### TC-4: CLI smoke -- list command
- **Result**: PASS
- **Notes**: `soul_adaptation.py list pm` returns `[]` (empty JSON array) when no adaptations exist. Requires role argument; prints usage on missing arg. After adding a test entry, correctly returns the entry as structured JSON with date, category, signal, source_task fields.

### TC-5: CLI smoke -- check-cap command
- **Result**: PASS
- **Notes**: `soul_adaptation.py check-cap skill` returns `{"role": "skill", "lines": 3, "cap": 40, "exceeds": false}`. JSON output with correct cap value of 40. Tested with pm role as well -- same correct behavior.

### TC-6: PM soul-shepherd sub-skill integration
- **Result**: FAIL
- **Notes**: Three issues found:
  - `references/sub-skills/pm-specific/soul-shepherd.md` exists and contains correct 5-category checklist, contradiction detection, add/render/check-cap workflow, 40-line cap, and frequency guidance.
  - `references/roles/pm/includes.yml` references `pm-specific/soul-shepherd` (line 15).
  - `references/roles/pm/CLAUDE.md` template has `{{include: pm-specific/soul-shepherd}}` (line 119).
  - **FAIL**: Live `.squidsquad/pm/CLAUDE.md` did NOT contain soul-shepherd content before compose deploy. Compose deploy had not been run after the sub-skill was added.
  - **FAIL**: After compose deploy, soul-shepherd markers are duplicated (`<!-- sub-skill: soul-shepherd -->` appears on lines 716 AND 717, and `<!-- /sub-skill: soul-shepherd -->` on lines 758 AND 759). This is a composition marker doubling bug.

### TC-7: config.py project-intent field mapping
- **Result**: FAIL
- **Notes**: `config.py` has the mapping at line 47: `"project-intent": ("Project", "Intent Description")`. However, `.squidsquad/config.md` does not contain a `Project > Intent Description` field. Running `python references/scripts/config.py get project-intent` returns `ERROR: Field 'project-intent' not found in config.md` with exit code 1. The config field was never added to the live config.md.

### TC-8: Manifest -- no orphan sub-skills
- **Result**: PASS
- **Notes**: `test_no_orphan_sub_skills` passes. Soul-shepherd sub-skill is properly registered in the manifest and referenced by PM's includes.yml.

### TC-9: CQ spec integrity
- **Result**: PASS
- **Notes**: `tests/comprehension/361_spec.json` exists with 3 comprehension questions covering: (1) new tech-stack signal detection and action, (2) contradiction handling, (3) 40-line cap consolidation. Test runner `tests/test_comprehension_361.py` exists with 4 test methods. Spec references correct files: `soul-shepherd.md` and `soul_adaptation.py`.

### TC-10: Reference SOUL.md templates -- Project Adaptation placeholder
- **Result**: PASS
- **Notes**: All 5 role templates have `## Project Adaptation` section with placeholder text: pm (line 89), dev (line 86), qa (line 85), dm (line 77), designer (line 77). Each contains `_No project-specific adaptations yet. PM will populate this as the project develops._` and `<!-- /project-adaptation -->` footer. Templates are clean -- no generated content, placeholder only.

---

## Code Review: soul_adaptation.py

- **add**: Correctly validates category (warns on non-standard), creates file if missing, finds/creates role section, appends entry with date/category/signal/task format. Append-only behavior confirmed.
- **render**: Groups entries by category in canonical order, handles uncategorized entries, produces clean markdown. Replaces existing section or appends if missing.
- **check-cap**: Counts non-empty lines, compares against LINE_CAP=40. Returns JSON with role, lines, cap, exceeds fields.
- **list**: Returns JSON array of parsed entries with date, category, signal, source_task.
- **5-category signals**: CATEGORIES list matches spec: deliverable-type, tech-stack, domain-vocabulary, quality-preference, user-persona.
- **File creation**: `_ensure_adaptations_file()` creates role-adaptations.md with header if missing. Graceful handling.
- **Section replacement**: Uses header + footer markers for precise section replacement. Falls back to regex for next `##` header if footer missing.
- **No issues found** in the script itself. Clean, well-structured code.

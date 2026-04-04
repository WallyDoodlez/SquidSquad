# SKILL.md + README.md Batch QA Report

**Date**: 2026-04-02
**Scope**: 12 bug fixes (#26, #27, #32, #33, #36, #37, #38, #39, #40, #41, #42, #43) plus #30 and #31

---

## Per-Item Results

### #26 — Architecture diagram should NOT show bugs/, features/, INDEX.md dirs
**PASS**
SKILL.md architecture diagram (lines 17-44) shows only: config.md, [role]/ with CLAUDE.md + working-state.md + planning/ + iterations/, pm/, qa/, dm/, designer/, templates/, vault/. No bugs/, features/, or INDEX.md present. The note at line 43 correctly says "Bugs & features: GitHub Issues with labels".

### #27 — README folder structure should show DM, not show nonexistent QA dir issues
**PASS**
README folder structure (lines 118-159) shows dm/ directory (line 143) with CLAUDE.md, working-state.md, iterations/. QA is shown correctly (line 138) as a real directory. No bugs/, features/, or INDEX.md directories in the folder structure. No nonexistent directories shown.

### #32 ��� Bug Flow should use correct status labels
**PASS**
Bug Flow (SKILL.md line 138): `status:open` -> `status:in-progress` -> `status:pending-test` -> `status:pending-ship` -> (Issue closed). None of the old incorrect labels (`status:investigating`, `status:fixed`, `status:verified`) appear in the current Bug Flow. Note: Schema 1 historical docs (line 1061) still reference `Open -> Investigating -> Fixed -> Verified -> Closed` but this is correctly scoped as historical documentation.

### #33 — Ralph Loop descriptions should reference gh issue commands, not INDEX.md or local files
**PASS (with caveat)**
Dev Ralph Loop (lines 184-202): Steps 2 and 3 explicitly reference `gh issue list` with label filters. QA Ralph Loop (lines 224-238): Steps 4, 5, and 6 explicitly reference `gh issue create` and `gh issue list`. PM Ralph Loop (lines 206-219): Step 3b references `gh issue list`. Step 2 says "file bugs to tracker" without explicitly naming `gh` commands, but "tracker" is defined as GitHub Issues earlier. No references to INDEX.md or local tracker files in the Ralph Loop sections.

### #36 — Improvement scan should distinguish bugs vs features in its protocol
**FAIL**
SKILL.md line 198 says only: "file findings through PM (max 2 per scan)" -- does not specify whether findings are filed as bugs or features. README line 184 correctly says "filed as normal features or bugs" but SKILL.md (which is the authoritative operational document) does not make this distinction. The improvement scan protocol in SKILL.md should explicitly state that findings are classified as either bugs (broken/degraded behavior) or features (enhancements/opportunities) before filing.

### #37 — No "PM/QA" as combined role -- should show PM and QA separately
**FAIL**
PM and QA are architecturally separate (separate directories, templates, boot scripts, Ralph Loops), but "PM/QA" still appears as a combined label in many places:
- Config template line 412: `**PM/QA**: always present`
- PM CLAUDE.md bootstrapper line 485-488: `For PM/QA` / `# SquidSquad -- PM/QA`
- PM boot script logos lines 628, 663: `PM / QA`
- Status bar design line 762: `PM/QA v0.5.1`
- Status bar example line 778: `PM/QA v0.5.1`
- Step 9 confirmation line 961: `PM/QA is interactive`
- Upgrade instructions line 995: `One agent for PM/QA`
- Multiple other references (lines 260, 264, 311, 801, 843, 1049)
These should all reference PM and QA as separate roles.

### #38 — Architecture diagram should show all 5 roles (Dev, Designer, QA, PM, DM)
**PASS**
SKILL.md architecture diagram (line 22) shows five boxes: `[Role]Lead`, `Designer`, `QA`, `PM`, `DM`. All five roles represented. README mermaid diagram (lines 79-85) shows PM, QA, [role] Lead (x2), Designer -- missing DM in the README diagram, but #38 is about the SKILL.md architecture diagram which is correct.

### #39 — Label Taxonomy should show type:bug, type:feature (not bare), include status:planned, status:open
**FAIL**
- `type:bug`, `type:feature`: PASS (line 129, correctly prefixed)
- `status:planned`: PASS (line 131, present in Status row)
- `status:open`: FAIL -- not listed in the Label Taxonomy Status row (line 131). However, `status:open` IS used in the Bug Flow (line 138) and Dev Ralph Loop (line 188). The Label Taxonomy is incomplete -- it must include `status:open` since bugs start with this status.

### #40 — Feature Flow should include status:planned between planning and approved
**PASS**
Feature Flow (SKILL.md line 142): `status:pending` -> `status:planning` -> `status:planned` -> `status:approved` -> `status:in-progress` -> `status:pending-test` -> `status:pending-ship` -> (Issue closed). The `status:planned` step is present between `status:planning` and `status:approved`. The explanatory note (line 144) correctly describes it: "planned = planning complete, awaiting human approval for execution."

### #41 — Config template should have current version, Architecture Version field, no Tracker Schema
**PASS**
Config template (lines 398-450):
- SquidSquad Version: 0.9.0 (matches SKILL.md frontmatter version on line 4) -- PASS
- Architecture Version: 1 (line 402, present) -- PASS
- No Tracker Schema field in the config template -- PASS
Note: Upgrade instructions (lines 979, 1015) still reference `Tracker Schema` for backward compatibility with older installations. This is acceptable for migration purposes but could cause confusion.

### #42 — Step 2 should NOT create bugs/, features/, archived/ dirs
**FAIL**
Step 2 (lines 347-394) is CLEAN -- creates only CLAUDE.md, iterations/, working-state.md, planning/ for dev agents. No bugs/, features/, or archived/ directories.
However, Step 6 "Seed Tracker Files" (lines 813-865) still creates `[role]/bugs/INDEX.md` and `[role]/features/INDEX.md`, which implicitly creates bugs/ and features/ directories. This contradicts the GitHub Issues model. Step 6 should be updated to only seed GitHub Issues (via `gh issue create`) rather than creating local tracker directories. The File Structure section (lines 72-113) also still shows `bugs/` and `features/` directories with INDEX.md at lines 89-90.

### #43 — Setup should handle Designer and QA role creation (directories, templates, boot scripts)
**FAIL**
- Step 2 (directories): QA directory creation handled (lines 363-370). Designer directory creation handled (lines 372-379). PASS.
- Step 4a (templates): QA template generation handled ("generate QA from Template 5"). Designer template generation handled ("copy Template 4"). PASS.
- Step 4b (bootstrapper CLAUDE.md): QA bootstrapper NOT shown -- Step 4b provides explicit bootstrapper content for dev agents (lines 464-483), PM (lines 485-503), and DM (lines 505-515), but has NO QA bootstrapper template. Designer bootstrapper also NOT shown. FAIL.
- Step 5 (boot scripts): Line 544 mentions QA and Designer boot scripts by name, but no explicit script templates are provided for QA or Designer (only dev agent, PM, and DM scripts are shown). FAIL.

---

## Additional Items

### #30 — Sub-skill extraction complete for all roles
**PASS (with caveat)**
All 5 roles have their own: directory structure, template file, CLAUDE.md bootstrapper (conceptually), and Ralph Loop definition. Dev, PM, QA, DM, Designer are all distinct sub-skills. Caveat: QA and Designer bootstrapper content is missing from Step 4b (see #43).

### #31 �� Status bar shows sub-skill name
**PASS**
Boot scripts write role name to `.squidsquad/.active-role` (e.g., lines 572, 637). Status bar design (line 762) shows "Role + version" (e.g., `skill v0.5.1`, `PM/QA v0.5.1`). The role name displayed IS the sub-skill name. Note: PM status bar still shows "PM/QA" instead of just "PM" (see #37).

---

## Summary

| Bug | Verdict | Notes |
|-----|---------|-------|
| #26 | PASS | Architecture diagram clean |
| #27 | PASS | README folder structure correct |
| #32 | PASS | Bug Flow uses correct status labels |
| #33 | PASS | Ralph Loops reference gh commands |
| #36 | **FAIL** | SKILL.md improvement scan doesn't distinguish bugs vs features |
| #37 | **FAIL** | "PM/QA" combined label persists in ~15+ locations |
| #38 | PASS | All 5 roles in SKILL.md architecture diagram |
| #39 | **FAIL** | `status:open` missing from Label Taxonomy |
| #40 | PASS | `status:planned` present in Feature Flow |
| #41 | PASS | Config template has version, Architecture Version, no Tracker Schema |
| #42 | **FAIL** | Step 2 clean, but Step 6 + File Structure still create/show bugs/ and features/ dirs |
| #43 | **FAIL** | QA and Designer missing bootstrapper templates and explicit boot scripts |
| #30 | PASS* | All roles extracted, caveat on QA/Designer bootstrappers |
| #31 | PASS* | Role name shown in status bar, caveat on PM/QA label |

**Result: 9 PASS, 5 FAIL**

### Critical Gaps Requiring Rework

1. **#37**: Systematic find-and-replace of "PM/QA" -> separate PM and QA references across SKILL.md
2. **#39**: Add `status:open` to Label Taxonomy Status row
3. **#42**: Remove Step 6 local tracker file seeding (bugs/INDEX.md, features/INDEX.md); update File Structure section to remove bugs/ and features/ from the tree
4. **#43**: Add explicit QA bootstrapper CLAUDE.md template and Designer bootstrapper CLAUDE.md template to Step 4b; add QA and Designer boot script templates to Step 5
5. **#36**: Add explicit "file as type:bug or type:feature" to SKILL.md improvement scan protocol

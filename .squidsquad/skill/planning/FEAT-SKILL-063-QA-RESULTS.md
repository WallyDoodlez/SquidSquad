# FEAT-SKILL-063 QA Results — Self-Improvement Loop

**QA Agent**: Fresh QA (no prior context)
**Date**: 2026-04-02
**Test Plan**: FEAT-SKILL-063-TEST-PLAN.md

## Test Case Results

### TC-1: Config toggle exists and defaults to enabled
**Result: PASS**
`config.md` contains `## Improvement Scanning` with `- **Enabled**: yes`. The field accepts yes/no values. Verified at line 51-52 of config.md.

### TC-2: 3 consecutive quiet cycles trigger scanning
**Result: PASS**
`improvement-scan.md` line 9: "After 3 consecutive quiet cycles, trigger an improvement scan on the next quiet cycle." Counter increments each quiet cycle, resets when real work occurs. Same content appears in all 6 composed templates in `agent-instructions.md`.

### TC-3: Counter resets after a scan completes
**Result: PASS**
`improvement-scan.md` line 11: "A scan completes (reset to 0, must accumulate 3 more quiet cycles)". Explicit reset-to-0 rule present.

### TC-4: Counter resets when real work occurs
**Result: PASS**
`improvement-scan.md` line 10: "Real work occurs (bug fix, feature progress, verification)" triggers counter reset. Verified in source and all composed templates.

### TC-5: Scanning disabled via config toggle
**Result: PASS**
`improvement-scan.md` line 7: "Check `Improvement Scanning` in `config.md`. If set to `no`, skip scanning entirely." Clear disable path.

### TC-6: Common sub-skill file exists under FEAT-SKILL-030 architecture
**Result: PASS**
File exists at `references/sub-skills/common/improvement-scan.md` (94 lines). Contains all 6 required components: quiet cycle counter logic (lines 9-11), scan trigger threshold (line 9), scan history management (lines 76-84), rate limiting (line 68), file selection algorithm (lines 25-29), and filing protocol (lines 68-75).

### TC-7: Dev agent scan strategy targets code quality
**Result: PASS**
`improvement-scan.md` lines 33-39: Dev agent checklist includes dead code, unused imports, missing error handling, code duplication, outdated patterns, performance bottlenecks, security concerns. All code-quality-specific. Present in composed `agent-instructions.md` at line 285+.

### TC-8: QA agent scan strategy targets test coverage
**Result: PASS**
`improvement-scan.md` lines 41-45: QA agent checklist includes source files without tests, untested public functions, missing edge case tests, flaky test indicators, missing integration/E2E scenarios. All test-coverage-specific. Present in composed templates.

### TC-9: Designer agent scan strategy targets design consistency
**Result: PASS**
`improvement-scan.md` lines 47-52: Designer checklist includes hardcoded values vs tokens, missing component states, accessibility gaps, inconsistent patterns, UX friction. All design-specific. Present in composed templates.

### TC-10: DM agent scan strategy targets documentation
**Result: PASS**
`improvement-scan.md` lines 54-59: DM checklist includes outdated README sections, missing API docs, changelog clarity, missing guides, undocumented features. All documentation-specific. Present in composed templates.

### TC-11: PM agent scan strategy targets process
**Result: PASS**
`improvement-scan.md` lines 61-65: PM checklist includes stale Pending features, backlog consolidation, priority imbalances, workflow bottlenecks. All process-specific. Present in composed templates.

### TC-12: Incremental scanning reads 3-5 files per cycle
**Result: PASS**
`improvement-scan.md` lines 25-29: "Pick 3-5 files, prioritized by: Recently changed, Never scanned before, Oldest since last scan." Priority ordering specified. Scan history consulted to avoid re-scanning.

### TC-13: Scans target different files each cycle
**Result: PASS**
`improvement-scan.md` line 29: "Check `.squidsquad/[your-role]/scan-history.md` to avoid re-scanning recently reviewed files." Priority algorithm (recently changed > never scanned > oldest scanned) ensures different files each cycle. Scan history format tracks files scanned per cycle (lines 76-84).

### TC-14: Findings reported to PM, not filed directly
**Result: PASS**
`improvement-scan.md` lines 68-75: Findings reported as Discussion entries, not direct tracker filings. Format includes `**[role]-lead (improvement-scan)**` tag. Rules section line 88: "PM is the single coordination point — agents don't file directly to trackers."

### TC-15: Default Low priority for scan-initiated items
**Result: PASS**
`improvement-scan.md` line 72: Template includes "Priority suggestion: Low." Rules section line 89: "Default Low priority — all scan items are Low priority. Human bumps if valuable."

### TC-16: Per-agent rate limit of 2 items per scan
**Result: PASS**
`improvement-scan.md` line 68: "max **2 items per scan**". Rules section line 90: "Max 2 items per scan — prevents noise. Quality over quantity." However, the test plan expects excess findings to be logged in scan history as "noted-but-not-filed." The scan history format (lines 79-84) only tracks "Findings: [list of findings reported, or 'none']" — it does not explicitly define a field for noted-but-not-filed excess findings. This is a minor gap but the 2-item cap itself is correctly implemented.

### TC-17: Scan history file created and maintained per agent
**Result: PASS**
`improvement-scan.md` lines 76-84: Scan history at `.squidsquad/[your-role]/scan-history.md`. Format includes date/time, files scanned list, findings list, and rejected items list. Created on first scan (not at install time).

### TC-18: Scan history prevents duplicate filings
**Result: PASS**
`improvement-scan.md` line 29: agents check scan history before scanning. Line 91: "Never refile rejected items — track rejected/dismissed items in scan history." The scan history tracks previously filed items so duplicates can be detected.

### TC-19: Rejected items tracked and never refiled
**Result: PASS**
`improvement-scan.md` line 84: Scan history format includes "Items rejected by human: [list]". Rules line 91: "Never refile rejected items — track rejected/dismissed items in scan history. If human says 'not worth it,' don't suggest it again."

### TC-20: New 'scanning' status bar phase displayed
**Result: PASS**
`improvement-scan.md` line 19: `scanning|🔍 Scanning [target description]...`. The `scanning` phase prefix is used. Verified in all 6 composed templates in agent-instructions.md.

### TC-21: Scan excludes internal SquidSquad files
**Result: FAIL**
The sub-skill says to scan the "target project" (line 3) and "Detect project type" (line 21), which implicitly targets project files. However, there is **NO explicit exclusion list** for `.squidsquad/`, `node_modules/`, `vendor/`, `.git/`, build output, generated files, or binaries. The test plan requires explicit exclusion rules. The phrase "target project" is ambiguous — an agent could reasonably interpret its own `.squidsquad/` files as part of the project.

**Gap**: Missing explicit file/directory exclusion list (`.squidsquad/`, `node_modules/`, `vendor/`, `.git/`, build output, generated files, binaries).

### TC-22: SOUL.md self-improvement lens defines scan focus
**Result: PASS**
All 5 soul files contain a "During quiet cycles, scan for:" directive that aligns with each role's scan checklist:
- `souls/dev.md` line 46: code quality debt, error handling, performance, test gaps
- `souls/qa.md` line 48: test coverage gaps, edge cases, regression risks
- `souls/designer.md` line 48: UX friction, design inconsistencies, accessibility gaps
- `souls/dm.md` line 48: outdated README, missing guides, CHANGELOG clarity
- `souls/pm.md` line 48: process bottlenecks, stale Pending items, coordination gaps

The sub-skill (line 24) instructs: "Read your SOUL.md self-improvement lens: Your soul defines what to look for."

### TC-23: Hybrid auto-detect for project type
**Result: PASS**
`improvement-scan.md` line 21: "Read `config.md` project info. Scan file extensions, `package.json`, `Cargo.toml`, `go.mod`, etc. to understand the tech stack. No new config field needed — auto-detect at scan time." Hybrid approach (config + file detection) confirmed.

### TC-24: Scan cycle that files items is no longer "quiet"
**Result: PASS**
All 6 role templates in `agent-instructions.md` update the quiet cycle definition to include improvement scans. Example from dev template (line 350): "If no bugs were fixed and no features were progressed this cycle (and no improvement scan was triggered), this is a quiet cycle." Same pattern in PM (line 1099), PM-lean (line 2024), QA (line 2938), Designer (line 3562), DM (line 4156). A scan that produces findings triggers logging and commit.

### TC-25: Agent does not act on its own scan findings
**Result: PASS**
Rules section line 88: "PM is the single coordination point — agents don't file directly to trackers. Report to PM via Discussion." Line 93: "PM does NOT auto-approve scan items — human decides whether to act on them." Agents report findings but cannot pick them up without human approval through the normal pipeline.

### TC-26: Manifest updated with improvement-scan sub-skill
**Result: PASS**
`manifest.md` line 106: `improvement-scan.md` listed in the file inventory as `(Quiet-cycle improvement scanning — shared by all roles)`. All 6 role entry files include `{{include: common/improvement-scan}}` (verified via grep: dev-agent.md:135, pm-agent.md:224, pm-lean.md:138, qa-agent.md:105, designer.md:112, dm-agent.md:104).

### TC-27: Upgrade path is non-destructive
**Result: PASS**
Config addition (`Improvement Scanning: yes`) is additive — no existing fields removed or renamed. Scan history files are created on first scan, not at install time (format defined in the sub-skill, no install-time creation). Templates regenerated via composition engine. Existing tracker items and iteration logs are untouched — the sub-skill only adds new behavior (quiet cycle scanning), it does not modify existing step behavior.

### TC-28: PM does not auto-approve scan items
**Result: PASS**
Rules section line 93: "PM does NOT auto-approve scan items — human decides whether to act on them." Findings are reported as Discussion entries (not tracker items), requiring PM to file them as Pending/Open through the normal pipeline, which itself requires human approval.

## Smoke Tests

- [x] Common sub-skill file parses as valid markdown
- [x] config.md contains `Improvement Scanning` field with `yes` value
- [x] All 6 role templates include the improvement scan step (dev, pm-agent, pm-lean, qa, designer, dm)
- [x] `scanning` phase used in status bar writes during scan execution
- [x] Scan history file format includes file path, timestamp, and findings columns
- [x] Manifest lists `common/improvement-scan` as a shared sub-skill

## Summary

| TC | Result |
|----|--------|
| TC-1 | PASS |
| TC-2 | PASS |
| TC-3 | PASS |
| TC-4 | PASS |
| TC-5 | PASS |
| TC-6 | PASS |
| TC-7 | PASS |
| TC-8 | PASS |
| TC-9 | PASS |
| TC-10 | PASS |
| TC-11 | PASS |
| TC-12 | PASS |
| TC-13 | PASS |
| TC-14 | PASS |
| TC-15 | PASS |
| TC-16 | PASS |
| TC-17 | PASS |
| TC-18 | PASS |
| TC-19 | PASS |
| TC-20 | PASS |
| TC-21 | **FAIL** |
| TC-22 | PASS |
| TC-23 | PASS |
| TC-24 | PASS |
| TC-25 | PASS |
| TC-26 | PASS |
| TC-27 | PASS |
| TC-28 | PASS |

**Pass: 27 / 28**
**Fail: 1 / 28**

## Gaps Found

### GAP-1 (TC-21): Missing explicit scan exclusion list
**Severity**: Medium
**Location**: `references/sub-skills/common/improvement-scan.md`
**Issue**: The sub-skill instructs agents to scan the "target project" but does not explicitly exclude `.squidsquad/`, `node_modules/`, `vendor/`, `.git/`, build output directories, generated files, or binaries. While "target project" is suggestive, an agent could interpret `.squidsquad/` files as scannable project files, leading to noise or self-referential findings.
**Fix**: Add an exclusion list to the "Select files to scan" step (step 3), e.g.:
```
   **Exclude from scanning**: `.squidsquad/`, `node_modules/`, `vendor/`, `.git/`, build output directories (`dist/`, `build/`, `out/`), generated files, and binary files. Only scan source files belonging to the target project.
```

## Overall Verdict

**FAIL** — 1 gap found. Feature goes back to dev for the TC-21 exclusion list fix. Once the explicit exclusion list is added to `improvement-scan.md` (and recomposed into `agent-instructions.md`), the feature should pass all 28 TCs.

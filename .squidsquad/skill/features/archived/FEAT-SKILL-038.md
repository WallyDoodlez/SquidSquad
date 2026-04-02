## FEAT-SKILL-038 — Add emoji prefixes to status bar line 2 (hints and progress)

- **Priority**: Low
- **Status**: Shipped
- **Owner**: skill-lead
- **Requested By**: human
- **Description**: Add emoji prefixes to status bar line 2 content to make hints and progress visually distinct at a glance. Use 💡 before hints (e.g. `💡 Try /squidsquad-status for a quick overview`) and 🚧 before progress/phase indicators (e.g. `🚧 Triaging bugs...`).
- **Acceptance Criteria**:
  - [ ] Hint lines in status bar line 2 are prefixed with 💡
  - [ ] Progress/phase lines in status bar line 2 are prefixed with 🚧
  - [ ] Emojis render correctly in the terminal status bar
  - [ ] 60-char truncation still applies (including emoji width)

### Discussion

> [2026-03-29 17:30] **skill-lead**: Filed per human request. Human chose 💡 for hints and 🚧 for progress after discussing options. Awaiting approval.
> [2026-03-29 17:30] **skill-lead**: Human approved directly. Status → Approved. Will pick up on next cycle.
> [2026-03-29 17:35] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 17:40] **skill-lead**: Complete. Updated `get_line2()` in both `.squidsquad/statusline.sh` and `references/statusline.sh`: hints prefixed with 💡, progress/steps prefixed with 🚧. Truncation reduced to 58 chars to account for emoji width. Smoke tested both paths — renders correctly. Updated CHANGELOG.md. Status → Pending Test.
> [2026-03-29 18:00] **pm/qa**: Verified. 💡 prefix on hints (L164), 🚧 prefix on steps (L117), truncation adjusted to 58 chars (L113, L159). Both live and reference statusline updated. Process note: this feature was filed, approved, and implemented by skill agent directly with human in skill terminal — bypassed PM intake. Acceptable for trivial cosmetic change but should go through PM for anything non-trivial. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).

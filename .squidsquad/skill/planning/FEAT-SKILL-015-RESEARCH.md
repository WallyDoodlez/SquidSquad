# FEAT-SKILL-015 Research — Auto Version Bump and Git Tag Every 10 Shipped Items

## Executive Summary

Auto-versioning tied to shipped output: every 10 items (features or bugs) shipped by PM/QA triggers a minor version bump (e.g., `0.5.1` → `0.6.0`), updates version metadata across three files, creates a git tag, and pushes. Technically feasible but requires careful crash-recovery design and explicit handling of concurrent operations. Current version is **0.5.1** with existing tags at v0.5.0 and v0.5.1.

---

## 1. Impact Analysis

### Files That Must Change

1. **`.squidsquad/config.md`** — Add `Shipped Since Last Bump: 0` counter. Current version: `0.5.1`.
2. **`SKILL.md`** — YAML frontmatter `version: 0.5.1` (line 4). Must stay in sync with config.md. Also update config.md template (Step 3) and document auto-versioning behavior.
3. **`CHANGELOG.md`** — Add new version section. Current latest: `[0.5.2] — 2026-03-28`.
4. **`references/agent-instructions.md`** — PM template Step 6: add counter increment + bump check logic.
5. **`.squidsquad/pm/CLAUDE.md`** — Generated PM instructions: include bump logic at Step 6.

### Files That Need No Changes

- Boot scripts — already read version dynamically from config.md
- `.squidsquad/statusline.sh` — reads iteration counts, not versions
- `.claude/settings.json` — PM doesn't touch this

---

## 2. Side Effects & Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| PM crashes mid-bump | HIGH | Working state file + resume logic |
| Simultaneous push during bump | MEDIUM | Document critical section, quick operation |
| SemVer confusion | MEDIUM | Document output-driven semantics |
| Upgrade flow breaks (config/SKILL version mismatch) | HIGH | Always update both config.md + SKILL.md atomically |
| Tag already exists | MEDIUM | Check existence before creating |
| Push fails | MEDIUM | Save state for retry next cycle |
| Batch shipping (10+ items in one cycle) | LOW | Bump once at 10, reset counter |

### Critical: Crash Recovery

Bump operation order: `config.md` → `SKILL.md` → `CHANGELOG.md` → `git commit` → `git tag` → `git push`. Use working-state.md to track progress. On context reset, resume from next incomplete step.

---

## 3. Edge Cases

- **Batch shipping**: Counter goes from 0→15 in one cycle. Bump at 10, reset to 0, continue. Counter ends at 5.
- **What counts**: Features marked `Shipped` ✅, Bugs marked `Closed` ✅, Rejected features ❌, Reopened bugs ❌
- **Manual version edit**: Next auto-bump increments from whatever's in config.md. No validation needed.
- **First bump**: `0.5.1` → `0.6.0`. Standard operation.
- **Counter persistence**: Stored in config.md — survives context resets.
- **PR Flow enabled**: Version bump should bypass PR flow (metadata, not code).

---

## 4. Open Questions (for Phase 2 Discussion)

### Q1: Should version bump require zero open bugs?
**Recommendation**: No — bump unconditionally at 10. Version = batch of work, not quality certification.

### Q2: Should threshold (10) be configurable?
**Recommendation**: Hardcode 10 in v1. KISS — fewer config fields.

### Q3: PR Flow enabled — should bump go through a PR?
**Recommendation**: No — commit directly to main. Metadata, not code.

### Q4: CHANGELOG format for auto-generated sections?
**Recommendation**: IDs with titles, grouped by Added/Fixed/Changed.

### Q5: Manual trigger/skip override?
**Recommendation**: No override in v1. Fully automatic. Manual edit of config.md for edge cases.

### Q6: Log version bump in iteration log?
**Recommendation**: Yes — add `Version Bumped` field to iteration log + Discussion entry.

### Q7: How should counter reset work?
**Recommendation**: Reset to 0 immediately after tag is pushed.

---

## 5. Current State Reference

| Field | Current Value |
|-------|----------------|
| Skill Version (SKILL.md) | 0.5.1 |
| Config Version (config.md) | 0.5.1 |
| Latest CHANGELOG Entry | [0.5.2] — 2026-03-28 |
| Existing Git Tags | v0.5.0, v0.5.1 |
| Shipped Since Last Bump Counter | Does not exist yet |

# FEAT-SKILL-015 Research — Auto version bump and git tag every 10 shipped items

## Summary

The feature is sound in concept — tying releases to actual output rather than arbitrary dates. However, research reveals significant crash-recovery risks, SemVer semantic mismatches, and unspecified edge cases that need resolution before implementation.

Version numbers appear in 3 primary files (config.md, SKILL.md frontmatter, CHANGELOG.md) and are read dynamically by boot scripts and statusline.sh. No caching — all reads are live from config.md. The upgrade flow compares config.md version to SKILL.md version, making consistency between these two critical.

**Recommendation: Feasible with caveats.** Needs crash-recovery safeguards, explicit operation ordering, and edge case specification.

## Impact Analysis

- **Files touched**:
  - `config.md` — version string + new counter field (`Shipped Since Last Bump: N`)
  - `SKILL.md` frontmatter — `version:` field
  - `CHANGELOG.md` — new version section appended
  - `references/agent-instructions.md` — PM template Step 6 gains bump logic
  - `config.md` template in SKILL.md Step 3 — add counter field
  - Generated `pm/CLAUDE.md` — updated with bump logic
- **No changes needed**: Boot scripts, statusline.sh, README.md (all read version dynamically)
- **Behavior changes**: PM gains a multi-step atomic operation (version bump) that touches 3 files + git tag in sequence
- **Dependencies**: Relies on git tag support, git push access

## Side Effects

- **Risk 1: PM crashes mid-bump** — Version updated in config.md but not SKILL.md → upgrade detection breaks (compares these two). Severity: HIGH. Mitigation: Use working-state.md to track bump progress; on resume, complete or rollback the bump.
- **Risk 2: Simultaneous push during bump** — Skill lead pushes while PM is mid-bump → rebase conflict on config.md (not a tracker file, "append both" strategy doesn't apply). Severity: MEDIUM. Mitigation: Document that bump is a critical section; PM should pull, bump all files, commit+push in one fast operation.
- **Risk 3: SemVer semantics lost** — 10 shipped items may include 7 bugs + 3 features, but always bumps minor. Users expecting SemVer will be confused. Severity: MEDIUM. Mitigation: Document that versioning is output-driven, not SemVer-compliant.
- **Risk 4: Upgrade flow confusion** — If auto-bumped version gets ahead of SKILL.md skill version, upgrade detects a "downgrade" and may refuse to run. Severity: HIGH. Mitigation: Always update SKILL.md frontmatter as part of the bump; validate both match after bump.

## Edge Cases

- **Batch shipping**: 10+ items ship in one PM cycle → should bump once (at first threshold cross), reset counter, not bump multiple times
- **What counts as shipped**: Features marked `Shipped` and bugs marked `Closed/Verified`. NOT rejected features. NOT the version-bump commit itself.
- **Manual version edit**: User edits config.md version manually → next auto-bump reads from whatever version is there. No validation of forward-only increment.
- **Git tag already exists**: `git tag v0.6.0` fails if tag exists → need error handling, suggest `v0.6.0-1` or alert user
- **Git push fails**: Tag created locally but push rejected → local/remote version drift. Need rollback.
- **Initial version**: Bumps from whatever current version is. User starts at 0.5.1, first auto-bump goes to 0.6.0.

## Integration Risks

- **Upgrade flow**: Compares config.md version vs SKILL.md version. If auto-bump updates both atomically, no issue. If partial update, upgrade breaks.
- **CHANGELOG structure**: PM must auto-generate a version section summarizing 10 items. Needs explicit format: list item IDs + titles grouped by category (Added/Fixed).
- **PR Flow**: If enabled, should the version bump be its own PR? Or commit directly to main? If PR, human has to merge before tag is created — adds latency.

## Open Questions

- **Q1**: Should bump be gated on zero open bugs, or proceed unconditionally? — **Why**: Affects whether a version number means "stable release" or just "10 things happened."
- **Q2**: Should the threshold (10) be configurable in config.md? — **Why**: Hardcoding means code changes to adjust; config makes it user-controllable.
- **Q3**: What's the exact operation order for the bump? — **Why**: Crash-recovery depends on knowing which step failed. Proposed: config.md → SKILL.md → CHANGELOG.md → git commit → git tag → git push.
- **Q4**: If git tag creation fails, should the entire bump be rolled back? — **Why**: Partial bumps create version drift that's hard to detect.
- **Q5**: Should the auto-generated CHANGELOG list item titles, or just IDs? — **Why**: Titles make it readable; IDs-only is safer but less useful.
- **Q6**: Should humans be able to manually trigger a bump or skip one? — **Why**: Flexibility for pre-release or hotfix scenarios.
- **Q7**: If PR Flow is enabled, should the bump commit go through a PR or direct to main? — **Why**: PR adds review but delays the tag; direct is faster but bypasses review.

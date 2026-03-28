# FEAT-SKILL-015 Context — Auto Version Bump and Git Tag

## Scope
Automatic minor version bump when shipped item counter reaches threshold AND zero open bugs. Updates config.md, SKILL.md frontmatter, CHANGELOG.md, creates git tag, pushes.

## Locked Decisions

### Q1: Bug gate
**Decision**: Bump triggers when counter >= threshold AND zero open bugs in all agent trackers. If bugs exist, counter stays at threshold+ and bump is deferred until bugs clear.
**Why**: Human wants version numbers to represent clean milestones, not just quantity.

### Q2: Threshold configurability
**Decision**: Configurable in config.md with `Ship Threshold: 10` field. Default is 10. If field is missing, fall back to 10.
**Why**: Flexibility for different project cadences without forcing config changes.

### Q3: PR flow bypass
**Decision**: Version bumps always commit directly to main, even if PR Flow is enabled.
**Why**: Metadata change, not code. No review needed. Tagging requires fast path.

### Q4: CHANGELOG format
**Decision**: IDs with titles, grouped by Added/Fixed/Changed sections.
**Format**:
```markdown
## [X.Y.Z] — YYYY-MM-DD

### Added
- FEAT-SKILL-XXX — Title

### Fixed
- BUG-SKILL-XXX — Title
```

### Q5: Manual override
**Decision**: No manual trigger or skip in v1. Fully automatic. User can edit config.md manually for edge cases.
**Why**: Keep it simple. Override complexity not justified yet.

### Q6: Logging
**Decision**: Log version bump in iteration log (add `Version Bumped` field) AND append Discussion entry to features.md.
**Why**: Full audit trail for traceability.

### Q7: Counter reset
**Decision**: Reset to 0 immediately after tag is pushed successfully.
**Why**: Clean state, simple logic. No overflow tracking.

## Dev Discretion Areas
- Exact crash recovery sequence (working-state.md usage)
- Error handling for tag conflicts and push failures
- Whether to validate YAML after SKILL.md frontmatter update

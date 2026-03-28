# FEAT-SKILL-015 Test Plan — Auto Version Bump

## Verification Criteria

### Template & Documentation
- [ ] `references/agent-instructions.md` PM template has Step 6a (version bump check)
- [ ] PM template checks counter >= threshold AND zero open bugs before bumping
- [ ] PM template reads threshold from config.md with fallback to 10
- [ ] PM template bump sequence: config.md → SKILL.md → CHANGELOG.md → commit → tag → push → reset counter
- [ ] PM template bypasses PR flow for version bumps
- [ ] PM template logs bump in iteration log (`Version Bumped` field)
- [ ] PM template appends Discussion entry on bump
- [ ] PM template has crash recovery logic (resume bump via working-state.md)
- [ ] SKILL.md documents auto-versioning behavior
- [ ] SKILL.md config.md template includes `Ship Threshold: 10` and `Shipped Since Last Bump: 0`

### Generated Files
- [ ] `.squidsquad/pm/CLAUDE.md` reflects bump logic
- [ ] `.squidsquad/config.md` has `Ship Threshold: 10` and `Shipped Since Last Bump: 0` fields

### CHANGELOG Format
- [ ] Auto-generated section uses `## [X.Y.Z] — YYYY-MM-DD` header
- [ ] Items grouped by `### Added`, `### Fixed`, `### Changed`
- [ ] Each item shows ID + title (e.g. `- FEAT-SKILL-008 — Step markers`)

### Edge Cases (manual read-through)
- [ ] Bug gate: template checks all agent bug trackers for open bugs before bumping
- [ ] Counter deferred: if bugs exist when counter hits threshold, bump waits
- [ ] Counter reset: counter resets to 0 after successful tag push
- [ ] Tag conflict: template checks for existing tag before creating
- [ ] Push failure: template handles failed push gracefully (save state for retry)

## FEAT-SKILL-049 — User-driven versioning with semver suggestion

- **Priority**: High
- **Status**: Pending
- **Requested By**: human
- **Description**: Replace the automatic "bump every 10 shipped items" versioning with user-driven versioning. The user decides when to ship a version — not an arbitrary threshold. The system suggests whether the release should be a minor or major version change based on what's been shipped since the last bump (features = minor, breaking changes = major, bug-only = patch). The user can accept the suggestion or choose their own version.
- **Current Flow**: Ship counter hits 10 + zero open bugs → auto-bump minor version. User has no control over timing.
- **New Flow**:
  - Ship counter in status bar shows number of shipped items pending release (e.g. `📦 3`)
  - Status bar indicates current suggested bump level: `📦 3 minor` or `📦 1 patch` based on what's shipped
  - User says "ship it" / "release" / "bump version" at any time → PM presents what's included, suggests version, asks for confirmation
  - User can accept suggestion or override (e.g. "make it a major")
  - PM (or DM if present) performs the bump: CHANGELOG, git tag, push
  - Remove `Ship Threshold` and auto-bump logic from config and PM/DM templates
- **Semver Logic**:
  - Only bug fixes shipped → suggest patch (0.7.0 → 0.7.1)
  - Any features shipped → suggest minor (0.7.0 → 0.8.0)
  - Human flags breaking change → suggest major (0.7.0 → 1.0.0)
  - Human can always override
- **Acceptance Criteria**:
  - [ ] Auto-bump at threshold removed from PM and DM templates
  - [ ] `Ship Threshold` removed from config.md
  - [ ] `Shipped Since Last Bump` remains (tracks pending items)
  - [ ] Status bar shows shipped count + suggested bump level (patch/minor/major)
  - [ ] User can trigger version bump at any time via conversation
  - [ ] PM presents release summary (features shipped, bugs closed) before bumping
  - [ ] User can accept suggested version or override
  - [ ] CHANGELOG, git tag, git push performed on bump
  - [ ] statusline.sh updated with new ship counter format
  - [ ] SKILL.md, agent-instructions.md updated

### Discussion

> [2026-03-31 02:00] **pm/qa**: Filed from human request. Human called the 10-item threshold "an impulse thought." Versioning should be user-driven with semver suggestions. Status bar changes from ship-counter-with-rocket to pending-count-with-bump-level. Status: Pending — awaiting human approval.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).

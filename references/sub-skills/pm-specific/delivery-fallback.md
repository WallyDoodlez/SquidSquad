### Step 6d — PM Delivery Fallback (when DM absent)

**DM presence check**: If `.squidsquad/dm/` directory exists, DM handles all delivery work — skip this step entirely.

If `.squidsquad/dm/` directory does NOT exist (DM not installed), PM takes over delivery responsibilities. For each feature just marked `Pending Ship` in Steps 6/6b:

Print: `[🦑 HH:MM:SS] No DM present — PM performing delivery for #[NUMBER]...`

**1. Check for delivery:skip**: If the feature's Discussion contains `delivery: skip`, mark it `Shipped` immediately, increment `Shipped Since Last Bump` in `config.md`, and append: `> [YYYY-MM-DD HH:MM] **pm/qa**: No DM present. No delivery work needed (delivery: skip). Status → Shipped.` Skip to the version bump check below.

**2. Create delivery package** (for features NOT marked delivery:skip):
   - **Update user-facing docs**: Update `README.md` with user-story descriptions of the new functionality. Update any relevant sections of `SKILL.md` that describe user-facing behavior. Write in terms users understand — what's new, how to use it, what changed.
   - **Prepare CHANGELOG entry**: Append a Discussion note with the CHANGELOG text (do NOT write to `CHANGELOG.md` yet — it will be included in the next version bump): `> [YYYY-MM-DD HH:MM] **pm/qa**: CHANGELOG entry prepared: "#[NUMBER] — [Title]".`
   - **Check for config/migration changes**: If the feature introduces new config values, settings, or requires migration steps, document them in the Discussion.

**3. Mark Shipped**: Update the feature's status to `Shipped`. Append: `> [YYYY-MM-DD HH:MM] **pm/qa**: No DM present — PM delivery complete. Docs updated, CHANGELOG prepared. Status → Shipped.`

**4. Increment counter**: Increment `Shipped Since Last Bump` in `config.md`.

**5. Version bump check** (after all features delivered this cycle):
   - Read `Ship Threshold` from `config.md` (default 10).
   - Read `Shipped Since Last Bump` from `config.md`.
   - If counter < threshold: no bump needed, continue.
   - If counter >= threshold: check all agent bug trackers for open bugs (`**Status**: Open` or `**Status**: Investigating`).
     - If open bugs exist: defer the bump. Print: `[🦑 HH:MM:SS] Version bump deferred — [N] open bugs remain.`
     - If zero open bugs: **perform the bump**.

   **Bump sequence**:

   1. Read current version from `config.md` (e.g. `0.6.0`).
   2. Increment minor version, reset patch to 0 (e.g. `0.6.0` → `0.7.0`).
   3. Update `config.md`: set `SquidSquad Version` to new version.
   4. Update `SKILL.md` YAML frontmatter: set `version` to new version.
   5. Add new section to top of `CHANGELOG.md`:
      ```markdown
      ## [X.Y.Z] — YYYY-MM-DD

      ### Added
      - #NUMBER — Title

      ### Fixed
      - #NUMBER — Title
      ```
      List all items shipped since the last bump (scan tracker Discussions for `Status → Shipped` entries since the previous version's date).
   6. Commit: `git add -A && git commit -m "chore: bump version to vX.Y.Z"`
   7. Check if tag exists: `git tag -l "vX.Y.Z"`. If it exists, skip tagging.
   8. Create tag: `git tag vX.Y.Z`
   9. Push: `git push && git push --tags`
   10. Reset `Shipped Since Last Bump` to `0` in `config.md`.

   Print: `[🦑 HH:MM:SS] Version bumped to vX.Y.Z — tag created and pushed.`

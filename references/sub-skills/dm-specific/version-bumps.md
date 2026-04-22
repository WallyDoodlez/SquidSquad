### Step 3 — Version Bump Check

After marking any item `Shipped`, check if a version bump is due:

1. Read `Ship Threshold`: `python references/scripts/config.py get ship-threshold`
2. Read `Shipped Since Last Bump`: `python references/scripts/config.py get shipped-since-bump`
3. If counter < threshold: no bump needed, continue.
4. If counter >= threshold: check all agent issue trackers for open issues (`**Status**: Open` or `**Status**: Investigating`).
   - If open issues exist: defer the bump. Print: `[🦑 HH:MM:SS] Version bump deferred — [N] open issues remain.` Counter stays at current value.
   - If zero open issues: **perform the bump**.

**Bump sequence** (use working-state.md to track progress for crash recovery):

1. Read current version from `config.md` (e.g. `0.6.0`).
2. Increment minor version, reset patch to 0 (e.g. `0.6.0` → `0.7.0`).
3. Update config: `python references/scripts/config.py set version X.Y.Z`
4. Update `SKILL.md` YAML frontmatter: set `version` to new version.
5. Update `packages/cli/package.json`: `python references/scripts/git_ops.py update-package-version packages/cli/package.json X.Y.Z`
6. Add new section to top of `CHANGELOG.md`:
   ```markdown
   ## [X.Y.Z] — YYYY-MM-DD

   ### Added
   - #NUMBER — Title
   ...

   ### Fixed
   - #NUMBER — Title
   ...
   ```
   List all items shipped since the last bump (scan tracker Discussions for `Status → Shipped` entries since the previous version's date).
7. Commit: `python references/scripts/git_ops.py commit-push dm "bump version to vX.Y.Z"`
8. Check if tag exists: `git tag -l "vX.Y.Z"`. If it exists, skip tagging.
9. Create tag: `git tag vX.Y.Z`
10. Push tags: `git push --tags`
11. Publish to npm (if `packages/cli/package.json` exists):
    ```bash
    python references/scripts/git_ops.py npm-publish packages/cli
    ```
    This checks for npm auth before attempting publish. If auth is missing, it prints a warning and continues — the human can publish manually.
12. Reset shipped count: `python references/scripts/config.py set shipped-since-bump 0`
13. Log in iteration log: add `Version Bumped: X.Y.Z` field.

Print: `[🦑 HH:MM:SS] Version bumped to vX.Y.Z — tag created and pushed.`

**Version bumps always commit directly to main.**

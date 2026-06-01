---
slot: instructions
ordinal: 20
roles: [dm]
---

### Step 3 — Version Bump Check

After marking any item `Shipped`, check if a version bump is due:

1. Read `Ship Threshold`: `python references/scripts/config.py get ship-threshold`
2. Read `Shipped Since Last Bump`: `python references/scripts/config.py get shipped-since-bump`
3. If counter < threshold: no bump needed, continue.
4. If counter >= threshold: check for open issues (type:issue, state:open) across all roles.
   - If open issues exist: defer the bump. Print: `[🦑 HH:MM:SS] Version bump deferred — [N] open issues remain.` Counter stays at current value.
   - If zero open issues: **perform the bump**.

**Bump sequence** (DM does creative work; `cycle_post.py` handles mechanical ops):

1. Read current version from `config.md` (e.g. `0.6.0`).
2. Increment minor version, reset patch to 0 (e.g. `0.6.0` → `0.7.0`).
3. Add new section to top of `CHANGELOG.md`:
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
4. Include `version_bump` in `cycle-output.json`:
   ```json
   "version_bump": {
     "new_version": "X.Y.Z",
     "items_included": ["#123 — Title", "#456 — Title"]
   }
   ```
   `cycle_post.py` handles the mechanical steps: config.md update, SKILL.md frontmatter, commit, tag, push, counter reset.
5. Log in iteration log: add `Version Bumped: X.Y.Z` field.

Print: `[🦑 HH:MM:SS] Version bumped to vX.Y.Z — tag created and pushed.`

**Version bumps always commit directly to main.**

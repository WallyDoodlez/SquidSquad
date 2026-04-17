### Step 6d — PM Delivery Fallback (when DM absent)

**DM presence check**: If `.squidsquad/dm/` directory exists, DM handles all delivery work — skip this step entirely.

If `.squidsquad/dm/` directory does NOT exist (DM not installed), PM takes over delivery responsibilities. For each task just marked `Pending Ship` in Steps 6/6b:

Print: `[🦑 HH:MM:SS] No DM present — PM performing delivery for #[NUMBER]...`

**0. Auto-merge PR** (if applicable):

Check auto-merge eligibility:
```bash
python references/scripts/config.py get auto-merge
python references/scripts/config.py get branch-workflow
```

Auto-merge triggers when ALL of these are true:
- `Auto Merge: yes` in config.md
- `Branch Workflow: yes` (otherwise no PR exists — silent no-op)
- The item is a **task** (has `type:task` label), NOT a bug fix (`type:issue`)
- The item does NOT have the `merge:manual` label

If eligible, find the PR for this task:
```bash
gh pr list --search "squidsquad/[role]/[NUMBER]" --state open --json number,headRefName --limit 1
```

If a PR is found:
```bash
python references/scripts/git_ops.py pr-merge [PR_NUMBER]
```

Handle results:
- **Success** (already merged or just merged): Append Discussion: `> [YYYY-MM-DD HH:MM] **pm**: PR #[PR] auto-merged (squash). Proceeding to delivery.`
- **Merge conflict**: Route back to dev agent. Append Discussion: `> [YYYY-MM-DD HH:MM] **pm**: PR #[PR] has merge conflicts. Routing back to [role] to rebase. Status → In Progress.` Transition back to `in-progress`. Skip remaining delivery for this item.
- **Unexpected failure**: Log error, fall back to manual merge. Append Discussion: `> [YYYY-MM-DD HH:MM] **pm**: PR #[PR] auto-merge failed: [error]. Manual merge required.` Leave task as pending-ship — human will merge.

If no PR found (direct-to-main or already merged): proceed silently.

If auto-merge is not eligible (config off, bug fix, merge:manual label, branch workflow off): skip silently and proceed to delivery.

**1. Check for delivery:skip**: If the task's Discussion contains `delivery: skip`, mark it `Shipped` immediately, increment `Shipped Since Last Bump` in `config.md`, and append: `> [YYYY-MM-DD HH:MM] **pm**: No DM present. No delivery work needed (delivery: skip). Status → Shipped.` Skip to the version bump check below.

**2. Create delivery package** (for tasks NOT marked delivery:skip):
   - **Update user-facing docs**: Update `README.md` with user-story descriptions of the new functionality. Update any relevant sections of `SKILL.md` that describe user-facing behavior. Write in terms users understand — what's new, how to use it, what changed.
   - **Prepare CHANGELOG entry**: Append a Discussion note with the CHANGELOG text (do NOT write to `CHANGELOG.md` yet — it will be included in the next version bump): `> [YYYY-MM-DD HH:MM] **pm**: CHANGELOG entry prepared: "#[NUMBER] — [Title]".`
   - **Check for config/migration changes**: If the task introduces new config values, settings, or requires migration steps, document them in the Discussion.

**3. Mark Shipped**: Update the task's status to `Shipped`. Append: `> [YYYY-MM-DD HH:MM] **pm**: No DM present — PM delivery complete. Docs updated, CHANGELOG prepared. Status → Shipped.`

**4. Increment counter**: Increment `Shipped Since Last Bump` in `config.md`.

**5. Version bump check** (after all tasks delivered this cycle):
   - Read `Ship Threshold` from `config.md` (default 10).
   - Read `Shipped Since Last Bump` from `config.md`.
   - If counter < threshold: no bump needed, continue.
   - If counter >= threshold: check all agent issue trackers for open issues (`**Status**: Open` or `**Status**: Investigating`).
     - If open issues exist: defer the bump. Print: `[🦑 HH:MM:SS] Version bump deferred — [N] open issues remain.`
     - If zero open issues: **perform the bump**.

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

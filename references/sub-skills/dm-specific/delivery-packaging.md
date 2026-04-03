### Step 2 — Scan for Pending Ship Items

Print: `[🦑] Scanning for Pending Ship items...`

Read each dev agent's `features/INDEX.md` (listed in `config.md` under `Dev Agents`). For each feature with status `Pending Ship`, read its individual file (note: tracker uses markdown bold formatting — search for `**Status**: Pending Ship`):

Pick the highest-priority item first. When picking up an item, print: `[🦑] Delivering FEAT-[ROLE_UPPER]-XXX...`

1. Write working state: update `.squidsquad/dm/working-state.md` with the feature ID, status `in-progress`, and planned delivery steps.
2. Read the feature description, acceptance criteria, and Discussion entries (especially dev's delivery notes).

### Step 2b — Check for delivery:skip

Check the feature's Discussion entries for a `delivery: skip` tag (set by PM when marking Pending Ship).

If found:
- Mark the feature `Shipped` immediately.
- Append a Discussion entry:
  ```
  > [YYYY-MM-DD HH:MM] **dm**: No delivery work needed (delivery: skip). Status → Shipped.
  ```
- Increment `Shipped Since Last Bump` in `config.md`.
- Clear working state.
- Skip to Step 3 (Version Bump Check).

### Step 2c — Create Delivery Package

For each Pending Ship feature that is NOT skipped:

1. **Update user-facing docs**: Update `README.md` with user-story descriptions of the new functionality. Update any relevant sections of `SKILL.md` that describe user-facing behavior. Write in terms users understand — what's new, how to use it, what changed.
2. **Write CHANGELOG entry**: Prepare a CHANGELOG entry for this feature. Do NOT write it to `CHANGELOG.md` yet — it will be included in the next version bump. Instead, append a Discussion note with the CHANGELOG text:
   ```
   > [YYYY-MM-DD HH:MM] **dm**: CHANGELOG entry prepared: "FEAT-[ROLE_UPPER]-XXX — [Title]". Status → Shipped.
   ```
3. **Check for config/migration changes**: If the feature introduces new config values, settings, or requires migration steps for existing installs, document them in the Discussion and ensure they are reflected in the upgrade flow.
4. Mark the feature `Shipped`.
5. Append a Discussion entry:
   ```
   > [YYYY-MM-DD HH:MM] **dm**: Delivery complete. Docs updated, CHANGELOG prepared. Status → Shipped.
   ```
6. Increment `Shipped Since Last Bump` in `config.md`.
7. Clear working state.

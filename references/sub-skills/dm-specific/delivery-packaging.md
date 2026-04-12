### Step 2 — Scan for Pending Ship Items

Print: `[🦑 HH:MM:SS] Scanning for Pending Ship items...`

Query GitHub Issues for items pending delivery:

```bash
python references/scripts/tracker.py list-by-labels "status:pending-ship"
```

Pick the highest-priority item first. When picking up an item, print: `[🦑 HH:MM:SS] Delivering #[NUMBER]...`

1. Write working state: update `.squidsquad/dm/working-state.md` with the task ID, status `in-progress`, and planned delivery steps.
2. Read the task description, acceptance criteria, and Discussion entries (especially dev's delivery notes).

### Step 2b — Check for delivery:skip

Check the task's Discussion entries for a `delivery: skip` tag (set by PM when marking Pending Ship).

If found:
- Transition the issue to Shipped (auto-closes):
  ```bash
  python references/scripts/tracker.py transition [NUMBER] pending-ship shipped --role dm-lead
  python references/scripts/tracker.py comment [NUMBER] --role dm --message "No delivery work needed (delivery: skip). Status → Shipped."
  ```
- Increment shipped count: `python references/scripts/config.py set shipped-since-bump [N+1]`
- Clear working state.
- Skip to Step 3 (Version Bump Check).

### Step 2c — Create Delivery Package

For each Pending Ship task that is NOT skipped:

1. **Update user-facing docs**: Update `README.md` with user-story descriptions of the new functionality. Update any relevant sections of `SKILL.md` that describe user-facing behavior. Write in terms users understand — what's new, how to use it, what changed.
2. **Write CHANGELOG entry**: Prepare a CHANGELOG entry for this task. Do NOT write it to `CHANGELOG.md` yet — it will be included in the next version bump. Instead, append a Discussion note with the CHANGELOG text:
   ```
   > [YYYY-MM-DD HH:MM] **dm**: CHANGELOG entry prepared: "#[NUMBER] — [Title]". Status → Shipped.
   ```
3. **Check for config/migration changes**: If the task introduces new config values, settings, or requires migration steps for existing installs, document them in the Discussion and ensure they are reflected in the upgrade flow.
4. Transition the issue to Shipped (auto-closes):
   ```bash
   python references/scripts/tracker.py transition [NUMBER] pending-ship shipped --role dm-lead
   python references/scripts/tracker.py comment [NUMBER] --role dm --message "Delivery complete. Docs updated, CHANGELOG prepared. Status → Shipped."
   ```
5. Increment shipped count: `python references/scripts/config.py set shipped-since-bump [N+1]`
7. Clear working state.

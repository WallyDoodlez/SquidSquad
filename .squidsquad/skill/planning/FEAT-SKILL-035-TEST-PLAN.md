# FEAT-SKILL-035 Test Plan — Delivery Manager (DM) Role

## Test Cases

### TC-1: Happy path — feature lifecycle through DM delivery
- **Precondition**: SquidSquad installed with DM role present. A feature exists at `Pending Test` in `skill/features.md`. PM and DM agents are running.
- **Steps**:
  1. PM verifies the Pending Test feature (Step 6) and marks it `Pending Ship` (not `Shipped`).
  2. DM picks up the `Pending Ship` item on its next cycle.
  3. DM creates delivery package (CHANGELOG entry, version bump, git tag, release).
  4. DM marks the feature `Shipped` with a Discussion entry.
- **Expected**: Feature transitions through `Pending Test` -> `Pending Ship` -> `Shipped`. PM never marks `Shipped` directly. DM writes all delivery artifacts.
- **Verification**: Read `features.md` — status is `Shipped`. Read Discussion — PM entry shows `Status -> Pending Ship`, DM entry shows `Status -> Shipped`. CHANGELOG has a new entry for this feature. Git tag exists matching the bumped version.

---

### TC-2: DM delivery packaging — CHANGELOG, version bump, git tag, release
- **Precondition**: A feature at `Pending Ship` status. `config.md` has a current version (e.g. `0.6.0`). `Shipped Since Last Bump` counter is at or above `Ship Threshold`. Zero open bugs across all trackers.
- **Steps**:
  1. DM picks up the Pending Ship feature.
  2. DM writes a CHANGELOG entry for the feature.
  3. DM increments version (minor bump: `0.6.0` -> `0.7.0`).
  4. DM updates `config.md` version and `SKILL.md` frontmatter version.
  5. DM creates git tag `v0.7.0`.
  6. DM creates release, pushes tag.
  7. DM resets `Shipped Since Last Bump` to 0.
  8. DM marks feature `Shipped`.
- **Expected**: CHANGELOG.md has a correctly formatted section with the feature listed under `### Added`. `config.md` shows new version. `SKILL.md` frontmatter `version` matches. Git tag exists. Counter reset to 0.
- **Verification**: `git tag -l "v0.7.0"` returns a match. `grep "version:" SKILL.md` shows `0.7.0`. `grep "Shipped Since Last Bump" .squidsquad/config.md` shows `0`. CHANGELOG.md top section references the feature ID.

---

### TC-3: delivery:skip tag — internal feature auto-ships
- **Precondition**: A feature at `Pending Ship` status with `delivery: skip` tag in its Discussion or metadata (set by PM when marking Pending Ship).
- **Steps**:
  1. DM picks up the Pending Ship feature.
  2. DM detects the `delivery: skip` tag.
  3. DM marks it `Shipped` immediately with Discussion note "No delivery work needed."
- **Expected**: Feature transitions directly from `Pending Ship` to `Shipped` with no CHANGELOG entry, no version bump, no git tag. Discussion contains DM note about skipping delivery.
- **Verification**: Read `features.md` — status is `Shipped`. Discussion has DM entry with "No delivery work needed." CHANGELOG.md has no new entry for this feature. No new git tag created for this item alone.

---

### TC-4: PM behavior change — no longer does version bumps or delivery
- **Precondition**: Updated PM template installed. A feature reaches `Pending Test`.
- **Steps**:
  1. PM verifies the Pending Test feature successfully.
  2. Observe PM's behavior after verification.
- **Expected**: PM sets status to `Pending Ship` (NOT `Shipped`). PM does NOT write CHANGELOG entries. PM does NOT increment version. PM does NOT create git tags. PM does NOT reset `Shipped Since Last Bump`. PM Step 6c (version bump logic) is fully removed from PM template.
- **Verification**: Read `.squidsquad/templates/pm-agent.md` — no Step 6c version bump section. Read `features.md` — PM's Discussion entry says `Status -> Pending Ship`. No PM-authored CHANGELOG entries for newly verified features.

---

### TC-5: PM Step 6b (PR Flow) sets Pending Ship for merged PRs
- **Precondition**: `PR Flow: yes` in `config.md`. A PR for a tracked feature has been merged.
- **Steps**:
  1. PM runs Step 6b — detects merged PR.
  2. PM updates the corresponding tracker item.
- **Expected**: PM sets status to `Pending Ship` (NOT `Shipped`) for merged PRs. Discussion entry says `PR merged -> Status -> Pending Ship`.
- **Verification**: Read `features.md` — status of the PR-linked feature is `Pending Ship`. Discussion shows PM entry referencing merged PR with `Pending Ship` status.

---

### TC-6: Dev behavior change — tech docs only, delivery notes in Discussion
- **Precondition**: Updated dev template installed. Dev agent is implementing a feature with user-facing changes.
- **Steps**:
  1. Dev completes feature implementation.
  2. Dev writes documentation.
  3. Dev appends delivery notes to Discussion.
  4. Dev marks `Pending Test`.
- **Expected**: Dev writes only technical docs (API docs, code comments, architecture notes). Dev does NOT update README with user-facing descriptions, CHANGELOG, or user guides. Dev appends a "Delivery notes" section to Discussion describing what user-facing changes were made (for DM to consume).
- **Verification**: Read `.squidsquad/templates/dev-agent-*.md` — Step 8 says tech docs only. Read feature Discussion — contains dev's delivery notes section. README not modified by dev for user-story content.

---

### TC-7: DM stalls — features pile up at Pending Ship
- **Precondition**: Multiple features at `Pending Ship`. DM agent is not running (heartbeat stale).
- **Steps**:
  1. PM runs health check (Step 7).
  2. PM detects DM heartbeat is stale.
  3. Features remain at `Pending Ship`.
- **Expected**: PM logs a warning about DM being stalled. Features stay at `Pending Ship` — they do NOT auto-advance to `Shipped`. No automatic fallback when DM exists but is stalled. Human must restart DM.
- **Verification**: Read `pm/qa-log.md` — contains DM stall warning. Read `features.md` — all items still at `Pending Ship`.

---

### TC-8: Multiple Pending Ship items simultaneously
- **Precondition**: Three features at `Pending Ship` status with different priorities (High, Medium, Low).
- **Steps**:
  1. DM starts a cycle and scans for Pending Ship items.
  2. DM processes them.
- **Expected**: DM processes items one at a time, highest priority first. Working state file tracks current item. Each item gets its own delivery package and Discussion entry.
- **Verification**: Read `dm/working-state.md` during processing — shows single active task. Read `features.md` after completion — all three are `Shipped` with individual DM Discussion entries. Discussion timestamps show sequential processing (High first).

---

### TC-9: No Pending Ship items — DM quiet cycle
- **Precondition**: DM is running. No features at `Pending Ship` status in any tracker.
- **Steps**:
  1. DM runs a cycle.
  2. DM scans for Pending Ship items, finds none.
- **Expected**: DM treats this as a quiet cycle — no iteration log, no commit, no output. Status bar shows idle with rotating hints.
- **Verification**: No new `dm/iterations/iter-N.md` created. `dm/current-state` contains `idle|`. No new git commits from DM.

---

### TC-10: Schema migration — Schema 1 to Schema 2
- **Precondition**: Existing SquidSquad install at Schema 1 (no `Pending Ship` status). Features exist at various statuses including `Pending Test` and `Shipped`.
- **Steps**:
  1. Run `/squidsquad-upgrade`.
  2. Upgrade detects Schema 1 and applies migration to Schema 2.
- **Expected**: Schema version updated to 2 in config.md. Status flow documentation updated to include `Pending Ship`. Existing `Shipped` items remain `Shipped` (no data migration needed). Existing `Pending Test` items remain at `Pending Test` and will flow through `Pending Ship` naturally. Migration log written to `pm/migrations/schema-1-to-2.md`.
- **Verification**: `grep "Tracker Schema" .squidsquad/config.md` shows `2`. Read `pm/migrations/schema-1-to-2.md` — exists with migration details. Existing `Shipped` features unchanged. SKILL.md Schema Changelog has Schema 2 entry documenting `Pending Ship`.

---

### TC-11: Upgrade path — DM added to existing install
- **Precondition**: Existing SquidSquad install without DM (`dm/` directory does not exist).
- **Steps**:
  1. Run `/squidsquad-upgrade`.
  2. Upgrade detects missing DM role.
- **Expected**: Creates `.squidsquad/dm/` with `CLAUDE.md` bootstrapper and `working-state.md`. Generates `.squidsquad/templates/dm-agent.md`. Generates `start-dm.sh` and `start-dm.ps1`. Copies `references/hints-dm.txt` to `.squidsquad/`. Adds DM to agents section in `config.md` (hardcoded like PM). Regenerates PM template (removes version bump, updates Pending Test -> Pending Ship). Regenerates dev template (tech docs only). Regenerates `statusline.sh` (DM health icon).
- **Verification**: `ls .squidsquad/dm/` shows `CLAUDE.md`, `working-state.md`. `ls .squidsquad/templates/dm-agent.md` exists. `ls .squidsquad/start-dm.*` shows both shell scripts. `grep -i "DM" .squidsquad/config.md` shows DM listed. PM template has no Step 6c. statusline.sh references DM health.

---

### TC-12: Fallback — no DM installed, PM treats Pending Ship as Shipped
- **Precondition**: SquidSquad install where DM does NOT exist (no `dm/` directory). A feature somehow reaches `Pending Ship` status (e.g., pulled from a repo where another contributor has FEAT-035 implemented).
- **Steps**:
  1. PM runs its cycle and encounters a `Pending Ship` item.
  2. PM checks for DM existence (`dm/` directory).
- **Expected**: PM detects no `dm/` directory exists. PM treats `Pending Ship` as if it were `Shipped` — processes it through the old flow (PM does the version bump, CHANGELOG, etc.). No features stall at `Pending Ship` indefinitely.
- **Verification**: Read `features.md` — item is now `Shipped`. PM Discussion entry notes fallback: "No DM installed — treating Pending Ship as Shipped." Version bump occurs if threshold met (old PM behavior).

---

### TC-13: Fallback — non-upgraded install, PM ignores Pending Ship
- **Precondition**: Old PM template (pre-FEAT-035) that has no knowledge of `Pending Ship`. A `Pending Ship` item exists in tracker (from another contributor's changes).
- **Steps**:
  1. Old PM scans for Pending Test items in Step 6.
  2. Old PM encounters items with `Pending Ship` status.
- **Expected**: Old PM does not recognize `Pending Ship` — it is neither `Pending Test` nor any status it acts on. Item is ignored. No crash, no error.
- **Verification**: PM completes its cycle without errors. `Pending Ship` items remain unchanged. This is a degraded state (items stuck) but not a broken state.

---

### TC-14: Statusline with DM health icon
- **Precondition**: PM agent running with updated statusline.sh. DM agent running with heartbeat.
- **Steps**:
  1. PM statusline renders line 1 with health icons.
  2. DM heartbeat branch is being pushed regularly.
- **Expected**: PM's line 1 health row includes a DM icon. DM healthy = squid emoji. DM stalled = ghost emoji. DM never started = egg emoji. DM's own statusline shows its role label, Pending Ship count, active task, and context/timer.
- **Verification**: Read `references/statusline.sh` — DM is included in the health icon iteration (alongside PM and dev agents). Run statusline.sh — DM icon appears in output.

---

### TC-15: DM reads shared tracker (no separate dm/ tracker)
- **Precondition**: Single shared `features.md` and `bugs.md` per dev agent. No `dm/features.md` or `dm/bugs.md` exist.
- **Steps**:
  1. DM scans for `Pending Ship` items.
  2. DM looks in dev agent trackers (e.g., `skill/features.md`).
- **Expected**: DM reads from the same `features.md` files that dev and PM use. DM does NOT have its own separate feature/bug tracker directory. DM writes status updates and Discussion entries directly to the shared tracker.
- **Verification**: No `dm/features.md` or `dm/bugs.md` files exist. DM Discussion entries appear in `skill/features.md` (or whichever agent's tracker the feature belongs to).

---

### TC-16: DM template structure — Ralph Loop with Pending Ship focus
- **Precondition**: DM template generated at `.squidsquad/templates/dm-agent.md`.
- **Steps**:
  1. Read the DM template.
  2. Verify it follows Ralph Loop structure (pull, context check, resume, scan, implement, log, commit).
- **Expected**: DM template has: Step 1 (pull), Step 1b (context pressure), Step 1c (resume from working state), scan for `Pending Ship` items across all dev agent trackers, delivery work steps (CHANGELOG, version bump, git tag, release), mark `Shipped`, iteration log, commit/push. Uses `/loop` command for scheduling. Prints `[🦑]` step markers. Writes `current-state` for statusline.
- **Verification**: Read `.squidsquad/templates/dm-agent.md` — contains all expected steps. Contains `/loop` invocation in startup. Contains `current-state` write instructions.

---

### TC-17: DM boot scripts exist and function
- **Precondition**: FEAT-035 implemented. Boot script templates in SKILL.md updated.
- **Steps**:
  1. Check that `start-dm.sh` and `start-dm.ps1` exist.
  2. Verify they follow the same pattern as other boot scripts (heartbeat, launch, clear current-state).
- **Expected**: Both scripts exist. They clear `dm/current-state` on startup. They launch heartbeat background process. They start Claude Code CLI with DM's CLAUDE.md. They write "Initializing..." to `dm/current-state`.
- **Verification**: `ls .squidsquad/start-dm.sh .squidsquad/start-dm.ps1` — both exist. Read scripts — contain heartbeat logic, `current-state` clear, Claude CLI launch.

---

### TC-18: DM CLAUDE.md bootstrapper
- **Precondition**: DM directory created with CLAUDE.md.
- **Steps**:
  1. Read `.squidsquad/dm/CLAUDE.md`.
  2. Verify it follows bootstrapper pattern (role config + Read instruction to template).
- **Expected**: ~20 lines. Contains role name "dm". Contains Read instruction pointing to `.squidsquad/templates/dm-agent.md`. Follows same pattern as `skill/CLAUDE.md` and `pm/CLAUDE.md`.
- **Verification**: Read `.squidsquad/dm/CLAUDE.md` — matches bootstrapper pattern. Contains path to DM template.

---

### TC-19: DM working-state.md for crash recovery
- **Precondition**: DM is mid-delivery (processing a Pending Ship item) and context pressure triggers exit.
- **Steps**:
  1. DM starts processing a Pending Ship feature.
  2. DM writes working state with task ID, completed steps, remaining steps.
  3. Context pressure exceeds threshold.
  4. DM saves state, commits, exits.
  5. DM restarts with fresh context.
  6. DM reads working-state.md in Step 1c.
- **Expected**: DM resumes from where it left off. Does not re-do completed delivery steps. Finishes remaining steps and marks Shipped.
- **Verification**: Read `dm/working-state.md` before restart — contains active task. After restart, DM prints "Resuming [FEAT-ID]..." and completes delivery.

---

### TC-20: Version bump moves from PM to DM
- **Precondition**: Updated templates. `Shipped Since Last Bump` at threshold. Zero open bugs.
- **Steps**:
  1. DM marks a feature `Shipped`.
  2. DM checks version bump conditions.
  3. DM performs the bump.
- **Expected**: DM increments `Shipped Since Last Bump` when marking items Shipped. DM performs the full bump sequence: increment version, update config.md, update SKILL.md frontmatter, write CHANGELOG section, create git tag, push, reset counter. PM does NOT perform any of these steps.
- **Verification**: Git log shows DM-authored commit for version bump (not PM). New git tag exists. `config.md` version updated. `Shipped Since Last Bump` reset to 0.

---

### TC-21: DM CHANGELOG entry format
- **Precondition**: DM delivering a feature that needs CHANGELOG entry.
- **Steps**:
  1. DM writes CHANGELOG entry as part of delivery.
- **Expected**: CHANGELOG entry follows existing format: `## [X.Y.Z] -- YYYY-MM-DD` with `### Added` / `### Fixed` sections listing `FEAT-*` and `BUG-*` IDs with titles. All items shipped since last bump are included.
- **Verification**: Read `CHANGELOG.md` — new section at top matches format. All shipped-since-last-bump items listed.

---

### TC-22: Config.md updates for DM
- **Precondition**: Upgrade or fresh install with FEAT-035.
- **Steps**:
  1. Read config.md after DM is set up.
- **Expected**: DM listed as hardcoded role (like PM, not under Dev Agents). No `FEAT-DM` or `BUG-DM` counters (since DM uses shared tracker, not its own). DM section mirrors PM section structure.
- **Verification**: Read `.squidsquad/config.md` — DM present in agents/roles section. Marked as hardcoded/permanent.

---

### TC-23: SKILL.md setup flow creates DM automatically
- **Precondition**: Fresh SquidSquad setup via `/squidsquad-setup`.
- **Steps**:
  1. Run setup flow.
  2. Setup creates project structure.
- **Expected**: DM directory, template, boot scripts, and config entries created automatically without user being asked. DM is hardcoded — user only chooses dev agents, not DM.
- **Verification**: After setup: `dm/` directory exists, `templates/dm-agent.md` exists, `start-dm.*` scripts exist, config.md lists DM. User was never prompted "Do you want a DM?"

---

### TC-24: DM hint pool file
- **Precondition**: FEAT-035 implemented. `references/hints-dm.txt` created.
- **Steps**:
  1. Read hints-dm.txt.
  2. Verify hint pool structure.
- **Expected**: File follows same pipe-delimited format as `hints-dev.txt` and `hints-pm.txt`. Contains DM-specific hints (e.g., delivery-related, CHANGELOG reminders, user-facing doc tips). Copied to `.squidsquad/` during setup.
- **Verification**: `references/hints-dm.txt` exists and is non-empty. Format matches existing hint files. `.squidsquad/hints-dm.txt` exists after setup/upgrade.

---

### TC-25: Agent-instructions.md has DM template
- **Precondition**: FEAT-035 implemented.
- **Steps**:
  1. Read `references/agent-instructions.md`.
- **Expected**: Contains a new Template 3 (or equivalent) for DM Agent, alongside existing dev (Template 1) and PM (Template 2) templates. DM template section is complete and matches the generated `dm-agent.md`.
- **Verification**: `grep -i "delivery manager\|DM Agent\|Template 3" references/agent-instructions.md` returns matches.

---

### TC-26: DM open bugs block version bump
- **Precondition**: DM uses shared tracker. An open bug exists in `skill/bugs.md`. DM is about to perform a version bump (counter >= threshold).
- **Steps**:
  1. DM checks bump conditions.
  2. DM scans all agent bug trackers for open bugs.
- **Expected**: DM finds the open bug and defers the bump. DM prints a message about deferring. Counter stays at current value.
- **Verification**: No new git tag. `Shipped Since Last Bump` counter unchanged. DM log shows "Version bump deferred — N open bugs remain."

---

## Smoke Tests

- [ ] `.squidsquad/dm/CLAUDE.md` exists and contains Read instruction to DM template
- [ ] `.squidsquad/dm/working-state.md` exists
- [ ] `.squidsquad/templates/dm-agent.md` exists and is non-empty
- [ ] `.squidsquad/start-dm.sh` and `.squidsquad/start-dm.ps1` exist
- [ ] `references/hints-dm.txt` exists and is non-empty
- [ ] `references/agent-instructions.md` contains DM template section
- [ ] PM template (`templates/pm-agent.md`) has NO Step 6c version bump section
- [ ] PM template Step 6 sets `Pending Ship` (not `Shipped`) after verification
- [ ] PM template Step 6b sets `Pending Ship` (not `Shipped`) for merged PRs
- [ ] Dev template Step 8 says tech docs only (no user-story docs)
- [ ] SKILL.md status flow line includes `Pending Ship` between `Pending Test` and `Shipped`
- [ ] SKILL.md Schema Changelog has Schema 2 entry
- [ ] `config.md` lists DM as a hardcoded role
- [ ] `statusline.sh` includes DM in health icon iteration
- [ ] SKILL.md setup flow has step for DM directory/template/boot script creation
- [ ] SKILL.md upgrade flow has step for adding DM to existing installs
- [ ] CHANGELOG.md has entry for FEAT-SKILL-035
- [ ] No `dm/features.md` or `dm/bugs.md` files (shared tracker, not separate)
- [ ] DM template scans dev agent trackers for `Pending Ship` items (not a DM-specific tracker)
- [ ] DM template contains `delivery: skip` handling logic

## Regression Risks

- **PM still marks Shipped directly**: If PM template update is incomplete, PM may bypass the DM step entirely. Watch for any code path in PM that sets status to `Shipped` instead of `Pending Ship`.
- **Version bump fires from PM**: If PM Step 6c is not fully removed, both PM and DM could attempt version bumps, causing double-bumps or conflicts. Verify PM template has zero version bump logic.
- **PR Flow sets Shipped on merge**: PM Step 6b historically sets `Shipped` for merged PRs. If this is not updated to `Pending Ship`, PR-merged features skip DM entirely. Verify Step 6b in PM template.
- **Dev agents still update user-facing docs**: If dev template Step 8 is not updated, both dev and DM will write README/user docs, causing conflicts. Verify dev template restricts to tech docs.
- **Existing features at Pending Test stall**: If PM template changes deploy without DM being available, features verified by PM get stuck at `Pending Ship` with no one to process them. Verify PM and DM templates ship simultaneously.
- **GitHub Issues closing breaks**: PM closes GitHub Issues when items reach `Shipped`. If DM marks `Shipped` (not PM), PM must still detect the transition and close the issue. Verify PM's tracker scan catches DM-shipped items.
- **Old PM encounters Pending Ship**: A non-upgraded PM may not understand `Pending Ship` status. Verify it degrades gracefully (ignores the status) rather than crashing.
- **Auto versioning counter drift**: If the `Shipped Since Last Bump` increment logic is not cleanly transferred from PM to DM, the counter may not increment on ship, causing version bumps to never trigger. Verify DM increments counter on every `Shipped` transition.
- **DM and dev git conflicts on docs**: DM edits docs while dev edits code on the same cycle. Standard git conflict risk. Verify DM pulls before starting work (Ralph Loop Step 1).
- **Statusline breaks for non-DM installs**: If statusline.sh unconditionally reads DM health, it may error on installs without DM. Verify statusline handles missing DM gracefully.
- **Setup flow regression**: Adding DM to setup may break existing setup for dev-only or PM-only configurations. Verify setup still works for all team shapes (single dev, multi-dev, etc.).
- **Quiet cycle detection**: DM quiet cycle logic (no Pending Ship items = skip log/commit) must match the pattern used by dev agents. Verify DM does not commit on quiet cycles.

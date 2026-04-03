# FEAT-SKILL-068 Test Plan — Migrate Tracker to GitHub Issues

## Test Cases

### TC-1: Setup asks user which tracker backend
- **Precondition**: Fresh install via `squidsquad-setup`
- **Steps**: Run setup; observe the tracker selection prompt
- **Expected**: Setup asks the user to choose a tracker backend. Default is `github-issues`. User can opt out to `markdown`. Selection is recorded in `config.md` as `Tracker: github-issues` or `Tracker: markdown`.
- **Verification**: `grep "Tracker:" .squidsquad/config.md` returns the selected backend

### TC-2: Soft-fail at startup when gh unavailable
- **Precondition**: GH Issues backend selected in config; `gh` CLI not installed or not authenticated
- **Steps**: Boot an agent. Observe startup behavior.
- **Expected**: Agent detects `gh` is unavailable (via `gh auth status` or equivalent). Warns the user. Offers to fall back to markdown. Does NOT hard crash.
- **Verification**: Agent output contains a warning about `gh` unavailability and a fallback prompt; agent does not exit with an error

### TC-3: Label taxonomy created during setup (~25 labels, 6 dimensions)
- **Precondition**: GH Issues backend selected; `gh` authenticated
- **Steps**: Run setup or upgrade. Check labels on the repo.
- **Expected**: ~25 labels created across 6 dimensions: type (2), priority (3), status (9), role (5), design (3), severity (3), plus special labels (squidsquad, delivery:skip, human-filed). Each label has a color and description.
- **Verification**: `gh label list --json name,color,description` returns all expected labels with correct names, colors, and descriptions

### TC-4: Label dimensions are mutually exclusive where specified
- **Precondition**: Labels created; an issue exists
- **Steps**: Attempt a status transition (e.g., Approved to In Progress). Check that the old status label is removed and the new one is added.
- **Expected**: Status transitions use `--add-label` and `--remove-label` in a single `gh issue edit` call. After transition, the issue has exactly one status label, one type label, one priority label.
- **Verification**: `gh issue view N --json labels` shows no duplicate labels within a mutually-exclusive dimension

### TC-5: Agents use gh CLI for all tracker operations (GH Issues backend)
- **Precondition**: GH Issues backend active; agent templates updated
- **Steps**: Read agent templates (dev, PM, QA, DM, designer). Check tracker-related steps.
- **Expected**: All tracker reads use `gh issue list` / `gh issue view`. All tracker writes use `gh issue edit` / `gh issue comment` / `gh issue create` / `gh issue close`. No markdown file reads/writes for tracker operations.
- **Verification**: Agent templates contain `gh issue` commands for tracker operations and no references to reading/writing INDEX.md, individual bug files, or feature files for tracker purposes

### TC-6: Discussion entries become Issue comments (timestamped, role-signed)
- **Precondition**: GH Issues backend active; agent running
- **Steps**: Trigger an agent action that appends a Discussion entry (e.g., picking up a feature)
- **Expected**: Agent posts a comment via `gh issue comment N --body "..."`. Comment body contains a timestamp and role signature in the standard format: `> [YYYY-MM-DD HH:MM] **role-name**: message`. Since all agents share the same GH auth, role attribution is embedded in the comment body.
- **Verification**: `gh issue view N --json comments` shows the comment with correct timestamp and role signature format

### TC-7: Status transitions via label changes
- **Precondition**: An open issue with `status:approved` label
- **Steps**: Dev agent picks up the feature. Observe label changes.
- **Expected**: Agent runs `gh issue edit N --add-label "status:in-progress" --remove-label "status:approved"`. Issue transitions cleanly. Terminal statuses (shipped, rejected) also close the issue via `gh issue close`.
- **Verification**: Issue label history shows the swap; issue state reflects closed for terminal statuses

### TC-8: Exclude closed issues from queries
- **Precondition**: Mix of open and closed issues with various labels
- **Steps**: Agent runs its triage/scan cycle
- **Expected**: All `gh issue list` calls include `--state open`. Closed issues are never surfaced in agent queries unless explicitly checking shipped items for version accounting.
- **Verification**: Agent query commands all contain `--state open`; closed issues do not appear in agent processing output

### TC-9: Issue numbers in working-state.md
- **Precondition**: Agent picks up a task from GH Issues
- **Steps**: Read `.squidsquad/[role]/working-state.md` while agent is working
- **Expected**: Working state references the task by GitHub Issue number: `Task: #42`. Not the old `FEAT-SKILL-NNN` format.
- **Verification**: `grep "Task:" .squidsquad/skill/working-state.md` shows `#N` format

### TC-10: Markdown fallback backend works independently
- **Precondition**: `Tracker: markdown` selected in config
- **Steps**: Run agents through a full cycle (triage bugs, implement features, file items)
- **Expected**: Agents use the existing markdown tracker protocol (INDEX.md, individual files, Discussion sections, ID counters). No `gh` commands issued for tracker operations. Behavior identical to pre-migration.
- **Verification**: No `gh issue` commands in agent output; INDEX.md and individual files are read/written as before

### TC-11: Tracker protocol sub-skill supports both backends
- **Precondition**: Feature implementation complete
- **Steps**: Check for the tracker protocol sub-skill file
- **Expected**: A sub-skill file exists (e.g., `references/sub-skills/common/tracker-protocol.md`) that defines the interface for both backends: reading issues, updating status, adding discussion, filing new items, closing items, error handling. Backend selection is driven by config.
- **Verification**: Sub-skill file exists with sections for GH Issues operations and markdown operations; backend dispatch is based on `Tracker:` config value

### TC-12: Planning artifacts stay local in .squidsquad/
- **Precondition**: GH Issues backend active; feature with planning artifacts
- **Steps**: Check that RESEARCH.md, CONTEXT.md, TEST-PLAN.md remain in `.squidsquad/[role]/planning/`
- **Expected**: Planning artifacts are NOT migrated to GitHub Issues. They remain as local files. The GitHub Issue body references them (e.g., `Planning: .squidsquad/skill/planning/FEAT-XXX-*`).
- **Verification**: Planning files exist locally; Issue body contains a reference to local planning path; no planning content duplicated in Issue body

### TC-13: Migration via /squidsquad-upgrade (atomic, with history)
- **Precondition**: Existing install with markdown tracker containing bugs and features with Discussion entries
- **Steps**: Run `/squidsquad-upgrade`. Observe migration.
- **Expected**: Upgrade detects markdown tracker dirs. For each non-archived item: creates a GitHub Issue with correct title, body, labels. Each Discussion entry migrated as an Issue comment (preserving timestamps and role signatures). Config.md updated (Tracker field added, ID counters removed). Markdown tracker dirs archived/deleted. All changes in a single atomic commit.
- **Verification**: All previously open items exist as GitHub Issues with matching labels and Discussion history as comments; config.md shows `Tracker: github-issues`; old tracker dirs removed; git log shows single commit

### TC-14: Migration preserves in-flight item statuses
- **Precondition**: Items in various statuses (In Progress, Pending Test, Pending Ship) before migration
- **Steps**: Run migration. Check migrated issues.
- **Expected**: Each item's current status is preserved as the correct status label on the new Issue. In-progress items get `status:in-progress`. Pending Test items get `status:pending-test`. Agents can pick up where they left off.
- **Verification**: `gh issue list --label "status:in-progress" --state open` returns items that were In Progress before migration

### TC-15: Skip-and-retry when GitHub unreachable
- **Precondition**: GH Issues backend active; GitHub API unreachable (simulated)
- **Steps**: Agent starts a cycle. Health check (`gh issue list --limit 1`) fails.
- **Expected**: Agent logs the failure. Skips all tracker operations for this cycle. Continues with non-tracker work (implementation, tests, commits). Does NOT crash. On next cycle, retries normally. Recovery is automatic.
- **Verification**: Agent output shows skip message; non-tracker work (if any) proceeds; next cycle with connectivity resumes tracker operations

### TC-16: Health check probe at cycle start
- **Precondition**: GH Issues backend active
- **Steps**: Agent starts a cycle. Observe the first `gh` command.
- **Expected**: Agent runs a lightweight health check (`gh issue list --limit 1 --json number`) before any tracker operations. If it fails, all tracker operations are skipped for this cycle.
- **Verification**: Health check command appears at the start of tracker operations; failure causes skip of all subsequent tracker commands

### TC-17: Filing a new bug via GH Issues
- **Precondition**: GH Issues backend active; agent discovers a bug
- **Steps**: Agent self-files a bug
- **Expected**: Agent runs `gh issue create` with title, body, and labels: `squidsquad`, `type:bug`, `role:[agent-role]`, `status:open` (or `status:pending`), `severity:[level]`, `priority:[level]`. No markdown file created. No ID counter incremented.
- **Verification**: `gh issue list --label "type:bug" --label "squidsquad"` returns the new issue with all expected labels

### TC-18: Filing a new feature via GH Issues
- **Precondition**: GH Issues backend active; PM files a feature
- **Steps**: PM creates a new feature
- **Expected**: Agent runs `gh issue create` with title, body, and labels: `squidsquad`, `type:feature`, `role:[target-role]`, `status:pending`, `priority:[level]`. No markdown file created. No ID counter incremented in config.md.
- **Verification**: `gh issue list --label "type:feature" --label "squidsquad"` returns the new issue

### TC-19: Terminal status closes the issue
- **Precondition**: An open issue with `status:pending-ship`
- **Steps**: DM ships the feature
- **Expected**: Agent adds `status:shipped` label, removes `status:pending-ship`, AND closes the issue via `gh issue close N`. Closed issues no longer appear in open-issue queries.
- **Verification**: `gh issue view N --json state,labels` shows `state: CLOSED` and `status:shipped` label

### TC-20: Human-filed issues (without squidsquad label) are ingested
- **Precondition**: GH Issues backend active; a human creates an issue on the repo without SquidSquad labels
- **Steps**: PM runs its ingestion step
- **Expected**: PM detects issues missing the `squidsquad` label. Adds `squidsquad` label. Classifies type (bug/feature), assigns role, sets `status:pending`. Posts ingestion comment.
- **Verification**: Previously unlabeled issue now has `squidsquad`, `type:`, `role:`, and `status:pending` labels; an ingestion comment exists

### TC-21: Config.md updated correctly for GH Issues backend
- **Precondition**: Migration or fresh install with GH Issues backend
- **Steps**: Read config.md
- **Expected**: Contains `Tracker: github-issues` and `Label Taxonomy Version: 1`. ID counters (BUG-SKILL, FEAT-SKILL, etc.) removed for GH Issues backend. Ship counter retained. Other config fields (intervals, thresholds, PR Flow, etc.) unchanged.
- **Verification**: Config.md contains the new fields and lacks ID counters; ship counter still present

### TC-22: Config.md unchanged for markdown backend
- **Precondition**: Markdown backend selected
- **Steps**: Read config.md
- **Expected**: Contains `Tracker: markdown`. ID counters retained and functional. No `Label Taxonomy Version` field. All existing config fields unchanged.
- **Verification**: Config matches pre-migration format plus the `Tracker: markdown` field

### TC-23: Concurrent agent updates do not conflict
- **Precondition**: GH Issues backend active; two agents operate on the same issue
- **Steps**: Two agents post comments and change labels on the same issue concurrently
- **Expected**: Both comments appear (append-only). Label changes are idempotent. No merge conflicts. No data loss.
- **Verification**: Both comments present on the issue; labels reflect the last transition; no error output from either agent

### TC-24: Batch reads via gh issue list reduce API calls
- **Precondition**: GH Issues backend active; multiple open issues
- **Steps**: Agent runs triage. Observe API calls.
- **Expected**: Agent uses `gh issue list --json number,title,body,labels,comments` to fetch multiple issues in a single call, rather than issuing separate `gh issue view` for each. This replaces the INDEX.md read + N individual file reads pattern.
- **Verification**: Agent issues a single `gh issue list` with `--json` including body/comments fields, reducing total API calls per cycle

### TC-25: ID format uses #N in all agent output
- **Precondition**: GH Issues backend active; agent working on an issue
- **Steps**: Check status bar state, step markers, commit messages, Discussion comments
- **Expected**: Issue references use `#N` format (e.g., `#42`) instead of `FEAT-SKILL-042` or `BUG-SKILL-029`. Status bar shows `implementing|#37 feature...`. Commit messages reference `#N`. GitHub auto-links these references.
- **Verification**: Agent output, working-state.md, commit messages, and comments all use `#N` format

### TC-26: Migration builds old-ID-to-issue-number mapping
- **Precondition**: Existing install with markdown tracker items
- **Steps**: Run migration. Check for mapping.
- **Expected**: Migration produces a mapping (old ID to new Issue number) so cross-references in planning artifacts can be resolved. Planning artifacts referencing old IDs get a note about the new Issue number.
- **Verification**: After migration, planning artifacts containing old IDs have been annotated or a mapping file exists

### TC-27: Label taxonomy version tracked in config
- **Precondition**: GH Issues backend active
- **Steps**: Read config.md
- **Expected**: `Label Taxonomy Version: 1` exists. Future label schema changes increment this version. Upgrade scripts check this version to determine if label updates are needed.
- **Verification**: Field present with value `1`

### TC-28: Vault (FEAT-SKILL-029) unaffected by migration
- **Precondition**: Vault exists at `.squidsquad/vault/`
- **Steps**: Run migration. Check vault.
- **Expected**: Vault directory and contents completely unchanged. Vault protocol operates independently of tracker backend.
- **Verification**: Vault files unchanged after migration; vault operations work as before

### TC-29: Iteration logs and working-state.md remain local
- **Precondition**: GH Issues backend active
- **Steps**: Agent completes a cycle. Check local files.
- **Expected**: Iteration logs still written to `.squidsquad/[role]/iterations/`. Working-state.md still written to `.squidsquad/[role]/working-state.md`. These are NOT moved to GitHub Issues.
- **Verification**: Local iteration and working-state files exist and are updated; no corresponding GitHub Issues created for these

### TC-30: Setup detects existing label name conflicts
- **Precondition**: Repo already has labels with names that might conflict (e.g., existing `bug` label)
- **Steps**: Run setup with GH Issues backend
- **Expected**: Setup checks for existing labels before creating the taxonomy. If conflicts are detected, warns the user. Uses namespaced format (`type:bug`, `status:approved`) which minimizes conflict risk. Does not silently overwrite existing labels.
- **Verification**: Setup output warns about any pre-existing conflicting labels; namespaced labels created without clobbering existing non-namespaced labels

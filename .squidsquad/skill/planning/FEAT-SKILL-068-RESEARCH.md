# FEAT-SKILL-068 — Research: Migrate Tracker from Internal Markdown to GitHub Issues

**Feature**: Replace internal markdown-based tracker with GitHub Issues as primary tracker
**Researcher**: research-agent (subagent)
**Date**: 2026-04-02
**Status**: Complete

---

## Table of Contents

1. [Current Tracker Usage Audit](#1-current-tracker-usage-audit)
2. [GitHub Issues API via gh CLI](#2-github-issues-api-via-gh-cli)
3. [Label Taxonomy Design](#3-label-taxonomy-design)
4. [Migration Strategy](#4-migration-strategy)
5. [Offline/Fallback Behavior](#5-offlinefallback-behavior)
6. [Performance and Rate Limits](#6-performance-and-rate-limits)
7. [Template Changes](#7-template-changes)
8. [Config Changes](#8-config-changes)
9. [Side Effects and Edge Cases](#9-side-effects-and-edge-cases)
10. [Upgrade and Migration](#10-upgrade-and-migration)

---

## 1. Current Tracker Usage Audit

### Per-Agent Tracker Operations

#### Dev Agent (e.g., skill-lead)

| Step | Operation | Read/Write | Files Touched |
|------|-----------|------------|---------------|
| Step 2 — Triage Bugs | Read INDEX.md | R | `.squidsquad/[ROLE]/bugs/INDEX.md` |
| Step 2 — Triage Bugs | Read individual bug file | R | `.squidsquad/[ROLE]/bugs/BUG-[ROLE]-XXX.md` |
| Step 2 — Triage Bugs | Write Status field (Open -> Fixed) | W | Individual bug file |
| Step 2 — Triage Bugs | Append Discussion entry | W | Individual bug file |
| Step 2 — Triage Bugs | Regenerate INDEX.md | W | INDEX.md |
| Step 2 — Cross-file bug | Write new bug file to other agent | W | `.squidsquad/[OTHER]/bugs/BUG-[OTHER]-XXX.md` |
| Step 2 — Cross-file bug | Regenerate other agent's INDEX.md | W | `.squidsquad/[OTHER]/bugs/INDEX.md` |
| Step 2 — Cross-file bug | Increment counter | W | `config.md` |
| Step 3 — Implement Features | Read INDEX.md | R | `.squidsquad/[ROLE]/features/INDEX.md` |
| Step 3 — Implement Features | Read individual feature file | R | `.squidsquad/[ROLE]/features/FEAT-[ROLE]-XXX.md` |
| Step 3 — Implement Features | Read planning artifacts | R | `.squidsquad/[ROLE]/planning/FEAT-*-RESEARCH.md`, `CONTEXT.md`, `TEST-PLAN.md` |
| Step 3 — Implement Features | Write Status field (Approved -> In Progress -> Pending Test) | W | Individual feature file |
| Step 3 — Implement Features | Append Discussion entries | W | Individual feature file |
| Step 3 — Implement Features | Regenerate INDEX.md | W | INDEX.md |
| Self-file bug | Write new bug file | W | `.squidsquad/[ROLE]/bugs/BUG-[ROLE]-XXX.md` |
| Self-file bug | Regenerate INDEX.md | W | INDEX.md |
| Self-file bug | Increment counter | W | `config.md` |

**Estimated per-cycle**: 2-4 reads, 2-6 writes (quiet cycle: 2R, 0W; active cycle: 4R, 6W)

#### PM/QA Agent

| Step | Operation | Read/Write | Files Touched |
|------|-----------|------------|---------------|
| Step 5 — Verify Fixed Bugs | Read each agent's bugs/INDEX.md | R | `.squidsquad/[ROLE]/bugs/INDEX.md` (per agent) |
| Step 5 — Verify Fixed Bugs | Read individual bug files (Fixed status) | R | Individual bug files |
| Step 5 — Verify Fixed Bugs | Write Status (Fixed -> Verified -> Closed) | W | Individual bug files |
| Step 5 — Verify Fixed Bugs | Append Discussion entries | W | Individual bug files |
| Step 5 — Verify Fixed Bugs | Regenerate INDEX.md | W | INDEX.md |
| Step 5 — Verify Fixed Bugs | Increment ship counter | W | `config.md` |
| Step 6 — Verify Features | Read each agent's features/INDEX.md | R | `.squidsquad/[ROLE]/features/INDEX.md` (per agent) |
| Step 6 — Verify Features | Read individual feature files (Pending Test) | R | Individual feature files |
| Step 6 — Verify Features | Write Status (Pending Test -> Pending Ship or back to In Progress) | W | Individual feature files |
| Step 6 — Verify Features | Append Discussion entries | W | Individual feature files |
| Step 6 — Verify Features | Regenerate INDEX.md | W | INDEX.md |
| Step 7b — Ingest GitHub Issues | `gh issue list` (if enabled) | R | GitHub API |
| Step 7b — Ingest GitHub Issues | File new bugs/features from Issues | W | New tracker files + INDEX.md |
| Feature Intake — File new feature | Write new feature file | W | `.squidsquad/[ROLE]/features/FEAT-[ROLE]-XXX.md` |
| Feature Intake — File new feature | Regenerate INDEX.md | W | INDEX.md |
| Feature Intake — File new feature | Increment counter | W | `config.md` |
| Bug Filing | Write new bug to any agent | W | Bug files + INDEX.md |
| Bug Filing | Increment counter | W | `config.md` |
| Delivery fallback (no DM) | Read features for Pending Ship | R | INDEX.md + individual files |
| Delivery fallback (no DM) | Write Status (Pending Ship -> Shipped) | W | Individual feature files |
| Delivery fallback (no DM) | Increment ship counter | W | `config.md` |

**Estimated per-cycle**: 3-8 reads, 3-15 writes (depends on number of agents, in-flight items)

#### QA Agent

| Step | Operation | Read/Write | Files Touched |
|------|-----------|------------|---------------|
| Step 3 — File Bugs from Failures | Write new bug files to any agent | W | Bug files + INDEX.md |
| Step 3 — File Bugs from Failures | Increment counter | W | `config.md` |
| Step 4 — Verify Fixed Bugs | Read each agent's bugs/INDEX.md | R | INDEX.md (per agent) |
| Step 4 — Verify Fixed Bugs | Read individual bug files (Fixed status) | R | Individual bug files |
| Step 4 — Verify Fixed Bugs | Write Status changes | W | Individual bug files |
| Step 4 — Verify Fixed Bugs | Append Discussion | W | Individual bug files |
| Step 4 — Verify Fixed Bugs | Regenerate INDEX.md | W | INDEX.md |
| Step 5 — Verify Features | Read each agent's features/INDEX.md | R | INDEX.md (per agent) |
| Step 5 — Verify Features | Read individual feature files | R | Individual feature files |
| Step 5 — Verify Features | Write Status changes | W | Individual feature files |
| Step 5 — Verify Features | Append Discussion | W | Individual feature files |
| Step 5 — Verify Features | Regenerate INDEX.md | W | INDEX.md |

**Estimated per-cycle**: 3-6 reads, 2-8 writes

#### DM Agent

| Step | Operation | Read/Write | Files Touched |
|------|-----------|------------|---------------|
| Step 2 — Scan for Pending Ship | Read each agent's features/INDEX.md | R | INDEX.md (per agent) |
| Step 2 — Scan for Pending Ship | Read individual feature files | R | Individual feature files |
| Step 2c — Create Delivery | Write Status (Pending Ship -> Shipped) | W | Individual feature files |
| Step 2c — Create Delivery | Append Discussion | W | Individual feature files |
| Step 2c — Create Delivery | Increment ship counter | W | `config.md` |
| Step 2c — Create Delivery | Regenerate INDEX.md | W | INDEX.md |
| Bug/Feature filing | Write new items | W | Bug/feature files |
| Bug/Feature filing | Increment counter | W | `config.md` |

**Estimated per-cycle**: 2-4 reads, 1-5 writes

#### Designer Agent

| Step | Operation | Read/Write | Files Touched |
|------|-----------|------------|---------------|
| Step 2 — Scan for Design Requests | Read each agent's features/INDEX.md | R | INDEX.md (per agent) |
| Step 2 — Scan for Design Requests | Read individual feature files (Design: needed) | R | Individual feature files |
| Step 2 — Design Session | Write Status (Design: needed -> in-progress -> complete) | W | Individual feature files |
| Step 2 — Design Session | Append Discussion | W | Individual feature files |
| Bug/Feature filing | Write new items | W | Bug/feature files |
| Bug/Feature filing | Increment counter | W | `config.md` |

**Estimated per-cycle**: 2-4 reads, 1-4 writes

### Aggregate: All Agents Combined

With a typical 5-agent setup (1 dev, PM, QA, DM, Designer) on 30-min cycles:

| | Quiet Cycle | Active Cycle |
|---|---|---|
| **Total reads** | ~12 | ~26 |
| **Total writes** | ~0 | ~38 |
| **Files committed** | 0 | ~15-20 |
| **Git operations** | pull only | pull + add + commit + push per agent |

### Critical Patterns Identified

1. **INDEX.md as listing endpoint**: Every agent starts by reading INDEX.md to find items in a specific status. This is the "query" pattern — replaced by `gh issue list --label`.
2. **Individual file as detail endpoint**: After finding items in INDEX, agents read individual files for full details. Replaced by `gh issue view N --json`.
3. **Status as field edit**: Agents edit the `**Status**:` line in markdown. Replaced by label add/remove.
4. **Discussion as append-only log**: Every agent appends timestamped, role-signed entries. Replaced by `gh issue comment`.
5. **INDEX.md regeneration**: After every status change, INDEX.md must be regenerated. Eliminated entirely — `gh issue list` is always current.
6. **Counter management**: ID counters in config.md incremented after filing. Eliminated — GitHub auto-assigns issue numbers.
7. **Cross-agent writes**: Agents write to other agents' tracker directories. Eliminated — all agents write to the same issue via API.
8. **Archived file moves**: Terminal-status items are moved to `archived/` subdirectory. Replaced by `gh issue close`.

---

## 2. GitHub Issues API via `gh` CLI

### Available Commands

| Command | Purpose | Migration Use |
|---------|---------|---------------|
| `gh issue create` | Create new issue | File bugs/features |
| `gh issue list` | List/filter issues | Replace INDEX.md reads |
| `gh issue view` | View single issue | Replace individual file reads |
| `gh issue edit` | Edit issue metadata | Status transitions (label changes) |
| `gh issue close` | Close an issue | Terminal status (Shipped/Closed) |
| `gh issue reopen` | Reopen closed issue | Status regression (Shipped -> In Progress) |
| `gh issue comment` | Add comment | Discussion entries |
| `gh issue delete` | Delete issue | Not used (we never delete tracker entries) |
| `gh label create` | Create label | Setup label taxonomy |
| `gh label list` | List labels | Verify taxonomy |

### JSON Output

All `gh issue` commands support `--json` for machine-readable output. Available fields:

- `number`, `title`, `body`, `state` (open/closed)
- `labels` (array of objects with `name` field)
- `comments` (array with `body`, `author`, `createdAt`)
- `assignees`, `author`, `milestone`
- `createdAt`, `updatedAt`, `closedAt`, `url`, `id`

Example queries:

```bash
# List all open bugs assigned to skill agent
gh issue list --label "type:bug" --label "role:skill" --state open --json number,title,labels,url

# List features pending test
gh issue list --label "type:feature" --label "status:pending-test" --state open --json number,title,labels,body

# View issue with full comments
gh issue view 42 --json number,title,body,labels,comments,state

# Multi-label filter (AND logic)
gh issue list --label "type:feature" --label "status:approved" --label "role:skill" --state open --json number,title,labels
```

### Rate Limits (Verified from Live API)

| Resource | Limit | Reset |
|----------|-------|-------|
| **Core API** | 5,000/hour | Rolling hourly window |
| **Search API** | 30/minute | Rolling per-minute window |
| **GraphQL** | 5,000/hour | Rolling hourly window |

The `gh issue list` command uses the Core API (REST), not the Search API — so the 5,000/hour limit applies. Even with 5 agents each making 10 calls per 30-min cycle, that is 100 calls/hour — well within the 5,000 limit (2% utilization).

### Discussion Protocol via Comments

GitHub Issue comments are:
- **Append-only** by default (only the author or repo admin can edit/delete)
- **Markdown-formatted** (full support for bold, code blocks, headers, etc.)
- **Timestamped** (automatically by GitHub, but agents should add their own timestamps for consistency with the existing protocol)
- **Author-attributed** (GitHub tracks who posted, but since all agents use the same `gh` auth, we must include role attribution in the comment body)

Comment format for agents:

```bash
gh issue comment 42 --body "> [2026-04-02 14:30] **skill-lead**: Picking up. Status -> In Progress."
```

Since all agents authenticate as the same GitHub user (the repo owner), role attribution MUST be in the comment body. GitHub's author field will always show the same user.

### Label Management

```bash
# Create a label
gh label create "status:approved" --color "0E8A16" --description "Approved for implementation"

# Add labels to an issue
gh issue edit 42 --add-label "status:in-progress" --remove-label "status:approved"

# Label operations are idempotent — adding an existing label is a no-op
```

Labels support:
- Color coding (hex colors)
- Descriptions
- Multiple labels per issue (perfect for our multi-dimensional taxonomy)
- AND filtering via `--label` flag (multiple `--label` flags = intersection)

---

## 3. Label Taxonomy Design

### Proposed Label Schema

#### Type Labels (mutually exclusive)

| Label | Color | Description |
|-------|-------|-------------|
| `type:bug` | `#d73a4a` (red) | Bug report |
| `type:feature` | `#0075ca` (blue) | Feature request |

#### Priority Labels (mutually exclusive)

| Label | Color | Description |
|-------|-------|-------------|
| `priority:high` | `#b60205` (dark red) | High priority |
| `priority:medium` | `#fbca04` (yellow) | Medium priority |
| `priority:low` | `#0e8a16` (green) | Low priority |

#### Status Labels (mutually exclusive)

| Label | Color | Description |
|-------|-------|-------------|
| `status:pending` | `#cfd3d7` (gray) | Filed, awaiting approval |
| `status:planning` | `#d4c5f9` (light purple) | In planning/research phase |
| `status:approved` | `#0e8a16` (green) | Approved for implementation |
| `status:in-progress` | `#1d76db` (blue) | Actively being worked on |
| `status:pending-test` | `#fbca04` (yellow) | Implementation complete, awaiting QA |
| `status:pending-ship` | `#f9d0c4` (peach) | QA passed, awaiting delivery |
| `status:shipped` | `#0e8a16` (dark green) | Delivered (issue will be closed) |
| `status:on-hold` | `#cfd3d7` (gray) | Blocked or deferred |
| `status:rejected` | `#e4e669` (light yellow) | Rejected |

Note: `status:shipped` and `status:rejected` are terminal — the issue is also closed when these are applied.

#### Role Labels (not mutually exclusive — allows cross-filing)

| Label | Color | Description |
|-------|-------|-------------|
| `role:skill` | `#5319e7` (purple) | Owned by skill agent |
| `role:pm` | `#006b75` (teal) | PM-related |
| `role:qa` | `#e99695` (pink) | QA-related |
| `role:designer` | `#d876e3` (magenta) | Design-related |
| `role:dm` | `#0075ca` (blue) | Delivery-related |

#### Design Labels (mutually exclusive, features only)

| Label | Color | Description |
|-------|-------|-------------|
| `design:needed` | `#fbca04` (yellow) | Needs design work before implementation |
| `design:in-progress` | `#1d76db` (blue) | Designer working on it |
| `design:complete` | `#0e8a16` (green) | Design approved, ready for dev |

#### Severity Labels (bugs only, mutually exclusive)

| Label | Color | Description |
|-------|-------|-------------|
| `severity:high` | `#b60205` (dark red) | High severity bug |
| `severity:medium` | `#fbca04` (yellow) | Medium severity bug |
| `severity:low` | `#0e8a16` (green) | Low severity bug |

#### Special Labels

| Label | Color | Description |
|-------|-------|-------------|
| `delivery:skip` | `#cfd3d7` (gray) | Internal-only, no delivery work needed |
| `squidsquad` | `#5319e7` (purple) | Managed by SquidSquad (all agent-created issues) |
| `human-filed` | `#bfdadc` (light cyan) | Filed by a human (not an agent) |

### Total Label Count: ~25 labels

This is manageable. GitHub supports unlimited labels per repo. The `squidsquad` label helps distinguish agent-managed issues from human-filed issues.

### Status Transition as Label Swap

A status transition (e.g., Approved -> In Progress) is:

```bash
gh issue edit 42 --add-label "status:in-progress" --remove-label "status:approved"
```

This is a single API call. The `--add-label` and `--remove-label` flags can be combined.

---

## 4. Migration Strategy

### Recommended Approach: Atomic Migration with History Preservation

**Phase 1 — Create Label Taxonomy**:
- Run `gh label create` for all ~25 labels (one-time setup, ~25 API calls)
- This can be done well before the full migration

**Phase 2 — Migrate Existing Items**:
For each non-archived bug and feature file:
1. Parse the markdown file: extract title, status, priority, severity, description, role, design status
2. Create a GitHub Issue with appropriate labels and body
3. Migrate Discussion entries as individual Issue comments (preserving timestamps and role signatures)
4. Record the GitHub Issue number mapping (old ID -> new number)

**Phase 3 — Handle In-Flight Items**:
- Items with status `In Progress`: Migrate with current status labels. The owning agent picks up where they left off, now reading from GitHub Issues instead of markdown.
- Items with status `Pending Test`: Same — create issue with `status:pending-test` label.
- Items with status `Pending Ship`: Same — create issue with `status:pending-ship` label.

**Phase 4 — Remove Markdown Tracker**:
- Delete `.squidsquad/*/bugs/` and `.squidsquad/*/features/` directories
- Git history preserves all historical data

### Should We Migrate Discussion History?

**Recommendation: Yes, migrate history as Issue comments.**

Rationale:
- Discussion entries contain important context (why decisions were made, what was tried, cross-references)
- Without history, agents lose context on in-flight items
- The migration is straightforward: for each Discussion entry, `gh issue comment N --body "[entry text]"`
- One-time cost: for a typical project with ~50 active items averaging 3 Discussion entries each, that is ~150 API calls — well within rate limits

### What Happens to Markdown Files After Migration?

1. **Delete** `.squidsquad/*/bugs/` and `.squidsquad/*/features/` directories entirely
2. **Keep** `.squidsquad/*/planning/` — RESEARCH.md, CONTEXT.md, TEST-PLAN.md still live here (only the tracker moves, not planning artifacts)
3. **Keep** `.squidsquad/*/iterations/` — iteration logs are per-agent and not part of the tracker
4. **Keep** `.squidsquad/config.md` — still needed for non-tracker config (intervals, thresholds, agent list, test commands)
5. **Git history** preserves all deleted files for audit purposes

### Atomic vs. Gradual Transition

**Recommendation: Atomic migration.**

A gradual transition (dual-write to both markdown and Issues) would be complex and error-prone — agents would need to keep both in sync, handle conflicts between the two sources, and the codebase would carry both code paths indefinitely. An atomic cutover is cleaner:

1. Run migration script (creates all Issues from markdown)
2. Deploy new agent templates (that read/write GitHub Issues instead of markdown)
3. Delete markdown tracker files
4. All in a single commit

---

## 5. Offline/Fallback Behavior

### Failure Modes

| Failure | Likelihood | Impact |
|---------|------------|--------|
| GitHub API timeout (transient) | Medium | Single `gh` call fails, retry works |
| GitHub outage (extended) | Low | All tracker operations blocked |
| Rate limited | Very Low | 5,000/hour is extremely generous for our usage |
| Network down (local) | Low | All `gh` calls fail |
| Auth expired | Low | All `gh` calls fail with 401 |

### Recommended Fallback Strategy: Skip and Retry

**Do NOT implement a local markdown fallback.** Reasons:
1. A dual-write system (write to Issues + local markdown) would reintroduce the complexity we are eliminating
2. Sync conflicts between local and remote state would be harder to resolve than merge conflicts in git
3. GitHub outages are rare and typically short (minutes, not hours)
4. Agents already handle "no work to do" gracefully (quiet cycles)

**Instead, each agent should:**

1. **Wrap `gh` calls in error handling**: If a `gh` command fails, log the failure and skip the operation.
2. **Retry on transient failures**: If `gh issue list` fails, retry once after 5 seconds. If it fails again, treat this cycle as a quiet cycle.
3. **Log the failure**: Append to the agent's iteration log that tracker operations were skipped due to API failure.
4. **Continue with non-tracker work**: The agent can still do implementation work, run tests, commit code — just skip tracker reads/writes.
5. **Recovery is automatic**: On the next cycle, `gh` calls work again and the agent catches up.

**Probing pattern** (at start of cycle):

```bash
# Quick health check — if this fails, skip all tracker operations this cycle
gh issue list --limit 1 --json number 2>/dev/null
if [ $? -ne 0 ]; then
  echo "[squid] GitHub API unreachable — skipping tracker operations this cycle."
  # Set a flag to skip tracker operations
fi
```

### Working State Persistence

The `working-state.md` file is local and NOT part of the tracker. It continues to work even when GitHub is down. An agent mid-implementation can continue working and update its working state — it just cannot change issue statuses until GitHub is reachable again.

---

## 6. Performance and Rate Limits

### Per-Agent API Call Budget (Per Cycle)

#### Dev Agent

| Operation | Calls | Notes |
|-----------|-------|-------|
| Health check | 1 | `gh issue list --limit 1` |
| List open bugs (own role) | 1 | `gh issue list --label "type:bug" --label "role:skill" --label "status:open"` |
| Read bug details | 0-3 | `gh issue view N` per open bug |
| Update bug status | 0-2 | `gh issue edit N --add-label --remove-label` |
| Add Discussion comment (bug) | 0-2 | `gh issue comment N` |
| List approved features (own role) | 1 | `gh issue list --label "type:feature" --label "role:skill" --label "status:approved"` |
| Read feature details | 0-1 | `gh issue view N` |
| Update feature status | 0-2 | `gh issue edit N --add-label --remove-label` |
| Add Discussion comment (feature) | 0-2 | `gh issue comment N` |
| File new bug (self or cross) | 0-1 | `gh issue create` |
| **Total** | **3-15** | Quiet: 3, Active: ~10-15 |

#### PM Agent

| Operation | Calls | Notes |
|-----------|-------|-------|
| Health check | 1 | |
| List all open issues (verification scan) | 1-2 | May need multiple `gh issue list` with different filters |
| Read issue details (Fixed bugs) | 0-3 | `gh issue view` per Fixed bug |
| Verify + update bug status | 0-3 | edit + comment per bug |
| Read issue details (Pending Test features) | 0-3 | `gh issue view` per Pending Test feature |
| Verify + update feature status | 0-3 | edit + comment per feature |
| File new bugs/features | 0-3 | `gh issue create` per new item |
| Add Discussion comments | 0-5 | Various comments through cycle |
| Close shipped issues | 0-2 | `gh issue close N` |
| Delivery fallback (update + comment) | 0-3 | If no DM |
| **Total** | **2-28** | Quiet: 2, Active: ~15-20 |

#### QA Agent

| Operation | Calls | Notes |
|-----------|-------|-------|
| Health check | 1 | |
| List issues for verification | 1-2 | |
| Read issue details | 0-5 | |
| Update statuses | 0-5 | |
| Add comments | 0-5 | |
| File bugs | 0-3 | |
| **Total** | **2-21** | Quiet: 2, Active: ~12-15 |

#### DM Agent

| Operation | Calls | Notes |
|-----------|-------|-------|
| Health check | 1 | |
| List Pending Ship features | 1 | |
| Read feature details | 0-3 | |
| Update status to Shipped | 0-3 | edit + close |
| Add comments | 0-3 | |
| **Total** | **2-11** | Quiet: 2, Active: ~7-9 |

#### Designer Agent

| Operation | Calls | Notes |
|-----------|-------|-------|
| Health check | 1 | |
| List features with design:needed | 1 | |
| Read feature details | 0-2 | |
| Update design status | 0-2 | |
| Add comments | 0-2 | |
| **Total** | **2-8** | Quiet: 2, Active: ~5-7 |

### Aggregate Budget

| Scenario | Agents | Calls/Cycle | Cycles/Hour | Calls/Hour | % of 5,000 Limit |
|----------|--------|-------------|-------------|------------|-------------------|
| Quiet (all 5 agents) | 5 | 5x2 = 10 | 2 | 20 | 0.4% |
| Normal (mixed activity) | 5 | ~50 | 2 | 100 | 2% |
| Heavy (all agents active) | 5 | ~75 | 2 | 150 | 3% |
| Burst (feature intake + verification + delivery all at once) | 5 | ~100 | 2 | 200 | 4% |

**Conclusion: Rate limits are a non-issue.** Even the worst-case burst scenario uses only 4% of the hourly limit. We could run 25 agents before approaching rate limits.

### Batching Optimization

One key advantage: `gh issue list` with JSON output returns all matching issues in one call. Today, reading INDEX.md gives the list, then each individual file must be read separately. With GitHub Issues:

```bash
# Single call replaces INDEX.md read + individual file reads
gh issue list --label "type:bug" --label "role:skill" --state open --json number,title,body,labels,comments --limit 50
```

This returns full issue details including body and comments. For most operations, a single `gh issue list` call replaces the INDEX.md read plus 1-N individual file reads. The per-cycle call count could be lower than the estimates above if agents use batch reads.

---

## 7. Template Changes

### What Changes

Every agent template's tracker-related sections must be rewritten. The following sub-skills are affected:

| Sub-skill / Section | Current | New |
|---------------------|---------|-----|
| Dev Step 2 (Triage Bugs) | Read INDEX.md + individual files, write Status + Discussion, regenerate INDEX | `gh issue list` + `gh issue view` + `gh issue edit` + `gh issue comment` |
| Dev Step 3 (Implement Features) | Read INDEX.md + individual files, write Status + Discussion, regenerate INDEX | Same `gh` pattern |
| Dev Bug Filing | Write file + regenerate INDEX + increment counter | `gh issue create --label ...` |
| PM Step 5 (Verify Bugs) | Read INDEX.md per agent + individual files | `gh issue list` + `gh issue view` |
| PM Step 6 (Verify Features) | Same | Same |
| PM Step 7b (GitHub Issues Ingestion) | Ingests external Issues into markdown | **Eliminated entirely** — issues already ARE GitHub Issues |
| PM Feature Intake | Write feature file + INDEX.md + counter | `gh issue create` + labels |
| PM Delivery Fallback | Read INDEX + files + write Status | `gh issue list` + `gh issue edit` + `gh issue close` |
| QA Verification (all steps) | Same INDEX + file pattern | Same `gh` pattern |
| DM Delivery Packaging | Read INDEX + files + write Status | Same `gh` pattern |
| Designer Design Session | Read INDEX + feature files for Design field | `gh issue list --label "design:needed"` |

### Sub-skills to Rewrite

A new sub-skill should be created: `common/tracker-protocol.md` (or `common/github-issues-tracker.md`). This replaces the distributed tracker patterns currently embedded in each agent's template. It defines:

1. **Reading issues**: How to query for issues by status, type, role
2. **Updating status**: How to swap labels
3. **Adding Discussion**: How to format and post comments
4. **Filing new items**: How to create issues with correct labels
5. **Closing items**: How to close with terminal status
6. **Error handling**: The skip-and-retry pattern
7. **ID references**: Use `#N` (GitHub Issue number) instead of `BUG-SKILL-NNN` / `FEAT-SKILL-NNN`

### Planning Artifacts Stay Local

The Feature Intake Process is NOT fully migrated:
- `RESEARCH.md`, `CONTEXT.md`, `TEST-PLAN.md`, `QA-RESULTS.md` **remain in** `.squidsquad/[ROLE]/planning/`
- These are large structured documents that benefit from git versioning and local file access
- They are referenced FROM the GitHub Issue body but live locally
- The Issue body should include: `Planning: .squidsquad/[ROLE]/planning/FEAT-XXX-*`

### Interaction with Vault (FEAT-SKILL-029)

The vault (`.squidsquad/vault/`) is completely separate from the tracker. It stores knowledge notes, not work items. No changes needed to vault protocol.

---

## 8. Config Changes

### Fields to Remove

| Field | Reason |
|-------|--------|
| `BUG-SKILL: 40` (ID Counters) | GitHub auto-assigns issue numbers |
| `FEAT-SKILL: 68` (ID Counters) | Same |
| `GitHub Issues Ingestion: no` | No longer a toggle — Issues ARE the tracker |
| `Tracker Schema: 3` | Replaced by label taxonomy versioning |

### Fields to Add

| Field | Default | Purpose |
|-------|---------|---------|
| `Tracker: github-issues` | `github-issues` | Declares tracker backend (future: could support other backends) |
| `Label Taxonomy Version: 1` | `1` | Tracks label schema version for upgrades |

### Fields to Keep (Unchanged)

| Field | Notes |
|-------|-------|
| `SquidSquad Version` | Still needed |
| `Architecture Version` | Still needed |
| `Dev Agents` | Still needed (agents need to know which roles exist) |
| `Test Commands` | Still needed |
| `Git Protocol` | Still needed |
| `Iteration Interval` | Still needed |
| `Context Pressure` | Still needed |
| `PR Flow` | Still needed |
| `Improvement Scanning` | Still needed |
| `Auto Versioning` | Still needed (ship counter tracks via labels now) |

### Ship Counter

The `Shipped Since Last Bump` counter currently lives in `config.md`. With GitHub Issues, an alternative is to count issues with `status:shipped` label that were closed since the last version tag. However, this adds API call complexity. **Recommendation: Keep the counter in config.md** — it is lightweight, local, and does not add API calls.

---

## 9. Side Effects and Edge Cases

### Concurrent Updates

**Two agents update the same issue simultaneously:**
- GitHub handles this gracefully. Comments are append-only — two agents posting comments at the same time both succeed.
- Label changes are idempotent — adding `status:in-progress` when it already exists is a no-op.
- The only risk: two agents both try to transition the same issue's status at the same time. Since label operations are idempotent, the last write wins. This is acceptable — agents operate on different lifecycle phases (dev changes to In Progress, QA changes to Pending Ship).

**Compare with current system:** Today, two agents editing the same markdown file causes a git merge conflict. GitHub Issues is actually BETTER for concurrency — no merge conflicts on tracker files.

### Deleted Issues

**Agent tries to read a deleted issue:**
- `gh issue view N` returns an error for deleted issues.
- Agent should handle this gracefully: log a warning, skip the item, continue.
- In practice, issues should never be deleted — they should be closed. The `gh issue delete` command exists but agents never use it.

### Human Closes an Issue Manually

- If a human closes an issue without changing status labels, agents see it as `state: closed` with whatever status label remains.
- Agents should check both `state` and status labels. If closed without `status:shipped` or `status:rejected`, treat as human override.
- Recommendation: Agents skip closed issues unless they have `status:pending-ship` (which means close was premature).

### Human Creates an Issue Outside SquidSquad

- The issue will lack the `squidsquad` label and status/type labels.
- PM's ingestion step (formerly Step 7b) can be adapted: instead of ingesting from Issues into markdown, PM scans for issues WITHOUT the `squidsquad` label and processes them:
  1. Add the `squidsquad` label
  2. Classify type (bug/feature) and add `type:` label
  3. Route to appropriate role and add `role:` label
  4. Add `status:pending` label
  5. Comment with ingestion note

```bash
# Find issues not managed by SquidSquad
gh issue list --state open --json number,title,labels --limit 50 | jq '[.[] | select(.labels | map(.name) | contains(["squidsquad"]) | not)]'
```

### Private Repos

`gh` CLI handles authentication via `gh auth login`. Once authenticated, all API calls work for private repos. No special handling needed. This is already the case for the existing `gh` usage in the PR Flow and GitHub Issues Ingestion features.

### Issue Body Size

GitHub Issue body has a 65,536 character limit. Feature descriptions with full acceptance criteria fit easily. However, if the Feature Intake Process produces very long feature specs, we should keep the detailed spec in planning artifacts and put a summary in the Issue body with references to local files.

### Label Name Conflicts

If a repo already has labels with conflicting names (e.g., an existing `bug` label vs. our `type:bug`), the setup script should detect and resolve this. Options:
1. Rename existing labels to match our taxonomy
2. Use our labels alongside existing ones (add `squidsquad:` prefix to all our labels)

**Recommendation: Use the proposed names as-is.** The namespaced format (`type:bug`, `status:approved`) is unlikely to conflict with existing labels. If conflicts are detected, warn the user during setup.

---

## 10. Upgrade and Migration

### For Existing Installs (Upgrade Path)

The `squidsquad-upgrade` skill needs a migration step:

1. **Pre-flight check**: Ensure `gh` is installed and authenticated (`gh auth status`)
2. **Create label taxonomy**: Run `gh label create` for all ~25 labels
3. **Migrate existing items**:
   - Read all non-archived bug/feature files from `.squidsquad/*/bugs/` and `.squidsquad/*/features/`
   - For each: create a GitHub Issue with appropriate title, body, and labels
   - For each Discussion entry: post as an Issue comment
   - Build a mapping file: `old-id -> github-issue-number`
4. **Update cross-references**: Scan all planning artifacts for old IDs (e.g., `FEAT-SKILL-042`) and add a note about the new Issue number
5. **Update config.md**: Remove ID counters, add `Tracker: github-issues` and `Label Taxonomy Version: 1`, remove `GitHub Issues Ingestion` toggle
6. **Delete markdown tracker**: Remove `bugs/` and `features/` directories from all agent paths
7. **Deploy new templates**: Replace agent templates with the GitHub Issues versions
8. **Commit**: Single atomic commit with all changes

### For New Installs (Setup Path)

The `squidsquad-setup` skill:
1. Creates label taxonomy during initial setup (no markdown tracker files created)
2. Generates agent templates that use GitHub Issues from the start
3. Sets `Tracker: github-issues` in config.md
4. No ID counters needed

### What Happens to `.squidsquad/*/bugs/` and `features/` Directories

- **Deleted** during migration/upgrade
- **Never created** on new installs
- Git history preserves all content
- The `.squidsquad/*/` directories continue to exist for: `iterations/`, `planning/`, `working-state.md`, `current-state`

### ID Format Change

| Before | After | Example |
|--------|-------|---------|
| `BUG-SKILL-029` | `#29` (GitHub Issue number) | "Fixing #29..." |
| `FEAT-SKILL-042` | `#42` | "Implementing #42..." |

Note: GitHub Issue numbers are repo-global (not per-type or per-role). Issue #42 could be a bug or a feature. The `type:` label distinguishes them. Agents reference issues as `#N` in commits and Discussion entries — GitHub auto-links these.

In status bar state and step markers, agents use `#N` instead of `BUG-SKILL-NNN`:
- Before: `implementing|FEAT-SKILL-037...`
- After: `implementing|#37 feature...`

---

## Summary

### Recommendation: Proceed with Full Migration

This migration is **feasible and well-bounded**:

1. **Rate limits are a non-issue** — even worst-case usage is <5% of the hourly limit
2. **GitHub Issues is strictly better for concurrency** — no more merge conflicts on tracker files
3. **INDEX.md regeneration is eliminated** — one of the most error-prone operations today
4. **ID counter management is eliminated** — GitHub auto-assigns numbers
5. **Cross-agent writes are simplified** — all agents comment on the same issue via API
6. **The Discussion protocol translates cleanly** to Issue comments
7. **Planning artifacts stay local** — only the tracker moves, not the full planning workflow
8. **Offline behavior is handled by skip-and-retry** — no complex fallback needed
9. **The GitHub Issues Ingestion feature (Step 7b) becomes the default behavior** rather than a toggle — its core logic (classify, route, label) is preserved

### Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| All agents use same GH auth — no per-agent attribution | Medium | Role signature in comment body (already the plan) |
| GitHub outage blocks all tracker ops | Low | Skip-and-retry; agents can still do implementation work |
| Label taxonomy changes require coordinated update | Low | Version field in config; upgrade script handles it |
| Loss of git-level diff on tracker changes | Medium | Issue event history in GitHub replaces git blame on tracker files |
| Planning artifact references to old IDs | Low | Migration script updates cross-references |

### Open Questions for Phase 2 (Discussion)

1. **Should `working-state.md` reference GitHub Issue numbers or titles?** Recommendation: Issue numbers (`#N`) for machine parsing, title in the description for human readability.
2. **Should the migration script be a standalone script or part of `squidsquad-upgrade`?** Recommendation: Part of upgrade, but can be run standalone for testing.
3. **Should we add a `gh` availability check to agent startup (beyond per-cycle)?** Recommendation: Yes — fail fast at startup if `gh auth status` fails.
4. **Should closed issues be excluded from all queries, or should agents occasionally scan closed issues?** Recommendation: Query only open issues by default. The DM/PM can query closed issues when checking shipped items for version bump accounting.
5. **How should the migration handle the existing `squidsquad` label on the repo (from GitHub Issues Ingestion)?** Recommendation: Reuse it as the marker label for all agent-managed issues.

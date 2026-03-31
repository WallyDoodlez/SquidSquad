# FEAT-SKILL-047 Research — Replace Heartbeat Branches with GitHub Commit Statuses

## Summary

Replace the heartbeat branch system (FEAT-SKILL-033) with GitHub commit statuses via `gh api`. The current system launches a background `heartbeat.sh` process that force-pushes orphan `heartbeat/<role>` branches every N seconds. The new system posts commit statuses inline at cycle end -- no background process, no git operations for health detection.

---

## Current Heartbeat System (What Gets Replaced)

### How It Works Today
1. Boot scripts (`start-*.sh`, `start-*.ps1`) launch `heartbeat.sh <role> <interval>` as a background process
2. `heartbeat.sh` loops every N seconds, creating a git tree object and force-pushing to `heartbeat/<role>` orphan branch
3. PM Step 7 does `git fetch origin heartbeat/<agent>` then reads the commit timestamp
4. `statusline.sh` does `git fetch origin heartbeat/<agent>` for each agent to render health icons
5. Stale threshold = 3x heartbeat interval (default 30s)

### Problems With Current System
- `git fetch` is slow (network round-trip per agent)
- `git fetch` conflicts with active git operations (rebase, push)
- Background process can orphan if boot script crashes
- Pushes git objects that accumulate (even though orphan branches)
- Requires bash on all platforms (Windows needs Git Bash)

---

## Integration Points — Full File Impact

| # | File | Change Type | Details |
|---|------|-------------|---------|
| 1 | `.squidsquad/heartbeat.sh` | **DELETE** | Remove live heartbeat script |
| 2 | `references/heartbeat.sh` | **DELETE** | Remove reference copy |
| 3 | `.squidsquad/start-skill.sh` | **EDIT** | Remove heartbeat launch block (lines 26-31) |
| 4 | `.squidsquad/start-pm.sh` | **EDIT** | Remove heartbeat launch block (lines 26-31) |
| 5 | `.squidsquad/start-skill.ps1` | **EDIT** | Remove heartbeat launch block (lines 23-24, cleanup in finally) |
| 6 | `.squidsquad/start-pm.ps1` | **EDIT** | Remove heartbeat launch block (lines 28-29, cleanup in finally) |
| 7 | `references/agent-instructions.md` | **EDIT** | PM Step 7: replace `git fetch` + heartbeat branch with `gh api` commit status read. Dev agent cycle end: add commit status post. Status line docs: update health icon descriptions. |
| 8 | `.squidsquad/pm/CLAUDE.md` | **REGENERATE** | PM agent instructions include Step 7 health check -- will be regenerated from `references/agent-instructions.md` |
| 9 | `references/statusline.sh` | **EDIT** | Replace heartbeat branch fetch (lines 211-231) with `gh api` commit status read. Also update timer section to read timestamp from commit status (fixes BUG-SKILL-035). |
| 10 | `.squidsquad/statusline.sh` | **COPY** | Regenerated from `references/statusline.sh` after edit |
| 11 | `.squidsquad/config.md` | **EDIT** | Remove `## Heartbeat` section and `Heartbeat Interval Seconds` key. Repo owner/name already available at `Repo: github.com/WallyDoodlez/SquidSquad`. |
| 12 | `SKILL.md` | **EDIT** | Setup: remove Step 5c (heartbeat script generation + interval prompt). Upgrade: remove heartbeat migration logic. Boot script templates: remove heartbeat launch blocks. |
| 13 | `README.md` | **EDIT** | Remove "Heartbeat Branches" section (line ~145-146). Update status line description. |
| 14 | `CHANGELOG.md` | **EDIT** | Add entry for the replacement |
| 15 | `references/hints-pm.txt` + `.squidsquad/hints-pm.txt` | **EDIT** | Line 29: change "Checking agent heartbeats..." to "Checking agent statuses..." or similar |
| 16 | `.squidsquad/skill/CLAUDE.md` | **EDIT** | Add commit status post at cycle end (Step 6, after Done marker). Also add to quiet cycle path. |

### Files That Reference `heartbeat` (30 total, key ones above)
Additional files are historical (iteration logs, old planning artifacts, qa-log) -- no changes needed.

### Files That Reference `egg` icon
10 files reference it. The `agent-instructions.md`, `statusline.sh`, `SKILL.md`, `README.md`, `pm/CLAUDE.md`, and `bugs.md` need the icon changed from `egg` to `?` (question mark emoji). Historical iteration logs and planning docs do not need updates.

---

## New System Design

### Agent Side (Post Status)
Each agent posts a commit status at the end of every cycle (including quiet cycles):

```bash
# Derive OWNER/REPO from config or gh
REPO_SLUG=$(grep 'Repo' .squidsquad/config.md | grep -oE '[^/]+/[^/]+$')
SHA=$(git rev-parse HEAD)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
gh api "repos/${REPO_SLUG}/statuses/${SHA}" \
  -f state=success \
  -f context="squidsquad/${ROLE}" \
  -f description="cycle ${N} -- ${PHASE} -- ${TIMESTAMP}" \
  2>/dev/null || true
```

Key points:
- Posted inline at cycle end -- no background process
- `|| true` ensures failure doesn't break the cycle
- Context string `squidsquad/<role>` is unique per agent
- Description carries timestamp for timer calculation

### PM Side (Read Statuses)
PM Step 7 reads statuses on the last 2-3 commits to handle SHA divergence:

```bash
REPO_SLUG=$(grep 'Repo' .squidsquad/config.md | grep -oE '[^/]+/[^/]+$')
# Get last 3 commit SHAs
SHAS=$(git log -3 --format="%H")
for SHA in $SHAS; do
  gh api "repos/${REPO_SLUG}/commits/${SHA}/statuses" \
    --jq '.[] | select(.context | startswith("squidsquad/")) | {context, description, updated_at}'
done
```

### Statusline Side
Replace the `git fetch` heartbeat block with:

```bash
REPO_SLUG=$(grep 'Repo' "$SQDIR/config.md" | grep -oE '[^/]+/[^/]+$')
# Read statuses on HEAD (timeout 2s for responsiveness)
STATUSES=$(timeout 2 gh api "repos/${REPO_SLUG}/commits/$(git rev-parse HEAD)/statuses" \
  --jq '.[] | select(.context | startswith("squidsquad/")) | .context + "|" + .updated_at' 2>/dev/null) || true
```

Parse each line to extract role and timestamp, then compute health icon.

---

## GitHub API Specifics

### POST Status (Agent)
```
POST /repos/{owner}/{repo}/statuses/{sha}
```
Request body:
```json
{
  "state": "success",
  "context": "squidsquad/skill",
  "description": "cycle 5 -- idle -- 2026-03-30T12:00:00Z"
}
```
Response: 201 Created with the status object.

### GET Statuses (PM/Statusline)
```
GET /repos/{owner}/{repo}/commits/{ref}/statuses
```
Response: Array of status objects, most recent first:
```json
[
  {
    "state": "success",
    "context": "squidsquad/skill",
    "description": "cycle 5 -- idle -- 2026-03-30T12:00:00Z",
    "updated_at": "2026-03-30T12:00:01Z",
    "created_at": "2026-03-30T12:00:01Z"
  }
]
```

### gh CLI Equivalents
- **Post**: `gh api repos/OWNER/REPO/statuses/SHA -f state=success -f context="squidsquad/role" -f description="..."`
- **Read**: `gh api repos/OWNER/REPO/commits/SHA/statuses --jq '.[] | select(.context | startswith("squidsquad/"))'`
- **Derive repo**: `gh repo view --json owner,name --jq '.owner.login + "/" + .name'` (or parse from config.md `Repo` field)

### Rate Limits
- GitHub API: 5,000 requests/hour for authenticated users
- Worst case with 3 agents + PM reading + statusline: ~12 writes/hour (one per cycle per agent) + ~60 reads/hour (PM each cycle + statusline per message) = ~72/hour. Well under limit.

---

## Edge Cases

### SHA Divergence
- Agents may have different HEADs if one has pushed and another hasn't pulled yet
- **Mitigation (locked decision)**: PM scans statuses on last 2-3 commits, not just HEAD. Agents re-post to their current HEAD each cycle. Belt-and-suspenders approach.
- Statusline can also scan last 2-3 commits for robustness.

### `gh` Auth Failure
- `gh auth status` may fail if token expired or not configured
- **Mitigation (locked decision)**: Graceful fallback. Agent continues without posting (cycle isn't blocked). Health shows `?` icon for unknown state.
- Both agent-side post and PM/statusline read use `|| true` or `2>/dev/null` to avoid breaking flow.

### Fresh Repo (No Commits)
- `git rev-parse HEAD` fails if no commits exist
- **Mitigation**: Skip status post if `git rev-parse HEAD` fails. Health shows `?`. This is the same as the current heartbeat system's behavior with no heartbeat branch.

### Concurrent Pushes
- Two agents push simultaneously, one's HEAD becomes stale immediately
- **Mitigation**: SHA divergence handling above covers this. Statuses are per-SHA, so the PM scanning multiple commits finds all agents regardless of push timing.

### Commit Status Accumulation
- GitHub keeps all statuses per SHA (they don't overwrite). The `context` field is used for "latest" determination -- only the most recent status per context is shown in combined status.
- For the list endpoint, all statuses are returned (not just latest per context). Filter with `--jq` and take the first match per context (array is newest-first).

### Private Repos
- Commit statuses work on private repos with the same `gh` auth. No additional scopes needed beyond default `repo` scope.

---

## Side Effects of Removing Heartbeat

### What Breaks
1. **Health detection gap between cycles**: Heartbeat pushes every 10s; commit statuses only post at cycle end (~30 min). A crashed agent won't be detected for up to 30+ minutes instead of 30s.
   - **Acceptable tradeoff**: Human already approved this. The real value is knowing if an agent completed its last cycle, not sub-minute liveness. If the agent crashes mid-cycle, the stale status from the previous cycle will eventually trigger `stalled` detection.

2. **Stale threshold changes**: Currently 3x heartbeat interval = 30s. New threshold should be based on cycle interval (e.g., 2x iteration interval = 60 minutes). Config key `Heartbeat Interval Seconds` is removed; threshold logic uses `Minutes` from Iteration Interval instead.

3. **Remote heartbeat branches left behind**: Existing installs have `heartbeat/pm`, `heartbeat/skill`, etc. on the remote.
   - **Migration**: Upgrade should delete remote heartbeat branches: `git push origin --delete heartbeat/pm heartbeat/skill` etc. Document in upgrade flow.

### What Doesn't Break
- PR Flow: unaffected (uses `gh pr` commands, orthogonal to commit statuses)
- GitHub Issues Ingestion: unaffected (uses `gh issue list`, orthogonal)
- Version bumps: unaffected (uses `git tag`, orthogonal)
- Dev agent workflow: agents are unaware of heartbeat today (boot script manages it). They will need a new step to post commit status, but it's a simple addition.
- Git operations: **improved** -- no more `git fetch` contention from heartbeat reads

---

## Upgrade & Migration

### Existing Installs
1. **Remove heartbeat.sh**: Delete `.squidsquad/heartbeat.sh`
2. **Regenerate boot scripts**: Remove heartbeat launch blocks from all 4 boot scripts (2 sh, 2 ps1)
3. **Update config.md**: Remove `## Heartbeat` section and `Heartbeat Interval Seconds` key
4. **Clean remote branches**: `git push origin --delete heartbeat/pm heartbeat/skill` (and any other agent heartbeat branches). Fail silently if they don't exist.
5. **Regenerate statusline.sh**: Copy updated `references/statusline.sh` to `.squidsquad/statusline.sh`
6. **Regenerate PM CLAUDE.md**: From updated `references/agent-instructions.md`
7. **Update dev agent CLAUDE.md**: Add commit status post to cycle end instructions

### Config Changes
- **Removed**: `Heartbeat Interval Seconds` under `## Heartbeat`
- **Kept**: `Repo` field in config.md (already exists, provides OWNER/REPO for API calls)
- **Added**: None needed -- repo slug is derivable from existing `Repo` config field

### SKILL.md Changes
- **Setup**: Remove Step 5c (Generate Heartbeat Script) entirely. Remove heartbeat interval prompt. Remove heartbeat explanation text.
- **Boot script templates**: Remove heartbeat launch blocks from all 4 templates (bash dev, bash pm, ps1 dev, ps1 pm, bash dm, ps1 dm).
- **Upgrade**: Add migration step to remove heartbeat artifacts and clean remote branches.
- **Agent instructions template**: Add commit status post to dev/PM cycle end.

---

## Repo Slug Derivation

Config already has `Repo: github.com/WallyDoodlez/SquidSquad`. Extract with:
```bash
grep 'Repo' .squidsquad/config.md | grep -oE '[^/]+/[^/]+$'
# → WallyDoodlez/SquidSquad
```

Alternative (doesn't require config): `gh repo view --json nameWithOwner --jq .nameWithOwner`

Recommend using the config field (faster, no API call) with `gh repo view` as fallback.

---

## Timer Fix (BUG-SKILL-035)

Currently statusline reads `current-state` file mtime for the countdown timer. On quiet cycles, if `current-state` isn't updated, the timer drifts.

With commit statuses, the timer can parse the timestamp from the status description field:
```
"cycle 5 -- idle -- 2026-03-30T12:00:00Z"
```

Extract the ISO timestamp, convert to epoch, compute elapsed time. This gives an accurate "time since last cycle" regardless of file mtime.

However, note that `current-state` is already written each cycle (including quiet ones) per BUG-SKILL-035's fix. The commit status approach provides a secondary/remote-visible timestamp. For local statusline, either source works. For PM health check (remote), the commit status timestamp is the only option.

---

## Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| `gh` CLI not installed | Medium | Low | Graceful fallback, show `?` icon |
| `gh` auth expired | Medium | Low | Same graceful fallback |
| API rate limit hit | Low | Very Low | ~72 req/hr vs 5000 limit |
| SHA divergence misses agent | Medium | Medium | Scan last 2-3 commits |
| Stale remote heartbeat branches | Low | High | Upgrade migration deletes them |
| Detection latency (30min vs 30s) | Low | Accepted | Human approved this tradeoff |
| Statusline `gh api` adds latency | Medium | Medium | Timeout 2s, cache result, `|| true` |
| Fresh repo with no commits | Low | Low | Skip post, show `?` |

---

## Open Questions for Context/Planning Phase

1. **Statusline caching**: Should statusline cache the last `gh api` result to avoid calling the API on every terminal render? A 30-60s cache file would reduce API calls significantly.
2. **Agent CLAUDE.md changes**: The commit status post needs to be added to both dev and PM agent instructions. Should this be a new step or appended to the existing Done step?
3. **DM agent**: If DM agent exists, it also needs the commit status post. Current boot scripts already handle DM for heartbeat -- ensure parity.
4. **Stale threshold**: What multiple of iteration interval defines "stalled"? Suggest 2x (if iteration is 30 min, stalled after 60 min with no status update).

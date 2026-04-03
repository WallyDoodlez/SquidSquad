# FEAT-SKILL-068 — Phase 2 Prep: Open Questions Analysis

**Feature**: Migrate Tracker from Internal Markdown to GitHub Issues
**Source**: FEAT-SKILL-068-RESEARCH.md (Open Questions, Section 10 Summary)
**Date**: 2026-04-02
**Status**: Ready for Discussion

---

## Optimal Question Order

Questions are ordered by dependency (upstream decisions first, controversial last):

| Order | Question | Rationale for Position |
|-------|----------|----------------------|
| 1 | Q3 — `gh` availability check at startup | Foundational: determines agent boot behavior, blocks all other tracker work |
| 2 | Q5 — Handling existing `squidsquad` label | Must be resolved before migration script can be written |
| 3 | Q4 — Closed issue query policy | Affects how agents write queries throughout all templates |
| 4 | Q1 — `working-state.md` ID format | Low-stakes, depends on Q4 (whether agents ever scan closed issues) |
| 5 | Q2 — Migration script packaging | Least controversial, mostly an organizational preference |

---

## Q3 — Should we add a `gh` availability check to agent startup (beyond per-cycle)?

**Category**: Agent Lifecycle / Error Handling

### Option A: Startup check with hard fail (RECOMMENDED)

Add `gh auth status` check in agent boot sequence. If it fails, agent refuses to start and prints a clear error.

| Pros | Cons |
|------|------|
| Fail-fast: no wasted context on a doomed session | Prevents agents from doing non-tracker work (code-only tasks) |
| Clear error message helps human diagnose auth issues quickly | Adds a network call to every agent startup |
| Prevents confusing mid-cycle failures on first tracker operation | Slightly slower boot (~1-2s) |

### Option B: Startup check with warning, continue anyway

Run `gh auth status` at boot. If it fails, log a warning and set a flag to skip tracker ops for the entire session.

| Pros | Cons |
|------|------|
| Agent can still do implementation work without tracker access | Agent runs in degraded mode — may confuse other agents expecting status updates |
| Graceful degradation matches the per-cycle skip-and-retry philosophy | Working on features without being able to update status creates drift |
| No wasted context window | Human may not notice the warning buried in startup output |

### Option C: No startup check, rely only on per-cycle probing

The existing per-cycle health check (`gh issue list --limit 1`) is sufficient. No additional startup logic.

| Pros | Cons |
|------|------|
| Simplest implementation — zero new code | Agent burns context on a full cycle before discovering gh is broken |
| Consistent with the skip-and-retry pattern already designed | If auth is expired, every cycle fails and retries pointlessly for the entire session |
| No additional API calls | Delayed feedback to human — may take 30+ minutes to notice the problem |

**Recommendation**: Option A. The tracker is now the central nervous system; running without it is like running blind. A 1-2s startup check is trivial cost for fast failure. If the agent truly needs to do code-only work without GitHub, the human can set a config flag to bypass.

---

## Q5 — How should the migration handle the existing `squidsquad` label on the repo?

**Category**: Migration / Setup

### Option A: Reuse existing label as-is (RECOMMENDED)

The `squidsquad` label already exists on some repos (from FEAT-SKILL GitHub Issues Ingestion). Reuse it as the marker label for all agent-managed issues. Migration script checks if it exists, creates it only if missing.

| Pros | Cons |
|------|------|
| Zero disruption to repos already using it | Existing issues with this label may not have the full label taxonomy applied |
| Semantic meaning is preserved (agent-managed issue) | Could create confusion if old ingested issues look like migrated items |
| Simplest migration path | No clean break between "old regime" and "new regime" issues |

### Option B: Delete old label, create fresh with updated description

Remove the existing `squidsquad` label, then recreate it with updated description and color to mark the new era.

| Pros | Cons |
|------|------|
| Clean slate — no ambiguity about which issues are from the new system | Deleting a label removes it from ALL existing issues (destructive) |
| Updated description clearly states "managed by SquidSquad tracker" | Extra API calls (delete + create) |
| Signals to humans that the tracker system has changed | If any workflows depend on the old label, they break |

### Option C: Create a new label `squidsquad:v2` and deprecate the old one

Keep the old `squidsquad` label on legacy issues. New issues get `squidsquad:v2`. Agents query only for `squidsquad:v2`.

| Pros | Cons |
|------|------|
| Clean separation between old and new regimes | Two labels for the same concept — confusing |
| Non-destructive — old issues untouched | All agent queries must use `squidsquad:v2` instead of `squidsquad` — less intuitive |
| Easy to audit which issues are from which era | Adds label bloat for marginal benefit |

**Recommendation**: Option A. The semantic meaning has not changed — it still means "managed by SquidSquad." The migration script should re-label any old ingested issues with the full taxonomy (add `type:`, `status:`, `role:` labels) so they are fully integrated. Clean and non-destructive.

---

## Q4 — Should closed issues be excluded from all queries, or should agents occasionally scan closed?

**Category**: Agent Behavior / Query Design

### Option A: Open-only by default, PM/DM scan closed for accounting (RECOMMENDED)

Dev, QA, and Designer agents always query `--state open`. PM and DM agents query `--state closed` only when performing specific accounting tasks (version bump counting, delivery audits).

| Pros | Cons |
|------|------|
| Minimizes API response sizes for most agents | PM/DM need two query patterns (open and closed) |
| Closed issues are irrelevant to active dev/QA work | If an issue is prematurely closed, dev agents will not see it |
| Clear separation of concerns: dev works, PM/DM accounts | Requires PM to detect and reopen prematurely closed issues |

### Option B: Always query open only, use config.md counter for accounting

No agent ever queries closed issues. Ship counting continues via the `Shipped Since Last Bump` counter in config.md (already recommended in the research).

| Pros | Cons |
|------|------|
| Simplest query pattern — all agents use `--state open` always | Counter in config.md can drift if an issue is closed without updating the counter |
| Fewest API calls | No way to audit shipped items without manual `gh issue list --state closed` |
| Counter is local and fast | Loses the advantage of GitHub as source of truth for ship accounting |

### Option C: Query both open and closed, filter client-side

All agents query `--state all` and filter by status labels in their logic.

| Pros | Cons |
|------|------|
| Agents see the complete picture including recently closed items | Larger API responses — includes all historical closed issues |
| Can detect premature closures | Performance degrades as issue count grows over time |
| Single query pattern for all agents | Most closed issues are irrelevant noise for dev/QA agents |

**Recommendation**: Option A. It matches the current behavior (agents only look at non-archived items) and keeps query responses small. The PM already has a verification role — detecting premature closures fits naturally. Keep the config.md ship counter as a lightweight local cache, but PM can cross-check against closed issues periodically.

---

## Q1 — Should `working-state.md` reference GitHub Issue numbers or titles?

**Category**: Developer Experience / Format

### Option A: Issue numbers with title annotation (RECOMMENDED)

Use `#N` as the primary reference, include the title as a human-readable annotation.

```markdown
- **Task**: #42 (Migrate tracker to GitHub Issues)
```

| Pros | Cons |
|------|------|
| `#N` is machine-parseable — agents can extract it trivially | Title may drift if issue is renamed after working state is written |
| GitHub auto-links `#N` in commits and comments | Slightly more verbose than number alone |
| Human reading the file immediately understands what the task is | Agents must remember to include both pieces |

### Option B: Issue numbers only

Use `#N` as the sole reference.

```markdown
- **Task**: #42
```

| Pros | Cons |
|------|------|
| Minimal, clean format | Human reading working-state.md must look up #42 to understand context |
| No risk of stale title annotations | After a context reset, agent must call `gh issue view 42` to understand what it was working on |
| Easiest to parse | Reduces the usefulness of working-state.md as a standalone context document |

### Option C: Titles only

Use the issue title as the reference.

```markdown
- **Task**: Migrate tracker to GitHub Issues
```

| Pros | Cons |
|------|------|
| Maximally human-readable | Not machine-parseable — agent cannot trivially extract the issue number |
| No API call needed to understand context | Titles can be long and awkward in structured fields |
| Works even if GitHub is down | Titles can be renamed, creating mismatches |

**Recommendation**: Option A. The working-state file serves two audiences: machines (for resume-from-state) and humans (for debugging). `#42 (title)` satisfies both. The title annotation is written once and does not need to stay in sync — it is a snapshot for context, not a live reference.

---

## Q2 — Should the migration script be a standalone script or part of `squidsquad-upgrade`?

**Category**: Packaging / Distribution

### Option A: Part of `squidsquad-upgrade` with standalone extraction (RECOMMENDED)

The migration logic lives inside the upgrade skill as a dedicated step. However, it is also callable standalone via a flag or sub-command for testing.

| Pros | Cons |
|------|------|
| Single upgrade path — users run one command | Upgrade skill becomes more complex |
| Standalone mode enables dry-run testing before committing | Two entry points to maintain |
| Consistent with existing upgrade patterns | Must handle "already migrated" detection to avoid double-migration |

### Option B: Fully integrated into `squidsquad-upgrade` only

Migration runs as part of the normal upgrade flow. No standalone mode.

| Pros | Cons |
|------|------|
| Simplest packaging — one entry point | Cannot test migration separately from a full upgrade |
| Users cannot accidentally run migration out of sequence | Debugging migration failures requires running the full upgrade |
| Enforces the correct upgrade order (templates + migration together) | Cannot do a dry-run without committing to the upgrade |

### Option C: Fully standalone script, separate from upgrade

A dedicated migration script (e.g., `migrate-tracker.sh` or a skill sub-command) that runs independently. The upgrade skill calls it as a step.

| Pros | Cons |
|------|------|
| Clean separation of concerns | Users might run migration without updating templates — broken state |
| Easy to test, easy to debug | Two things to remember to run during upgrade |
| Can be versioned and updated independently | Coordination between script and upgrade skill adds complexity |

**Recommendation**: Option A. The upgrade skill is the canonical entry point for users. Embedding migration as a step ensures correct ordering (labels first, then migration, then template update, then cleanup). The standalone mode is a developer convenience for testing — it can be as simple as a `--migrate-only` flag that runs just the migration step and exits.

---

## Summary Table

| # | Question | Category | Recommended Option | Confidence |
|---|----------|----------|--------------------|------------|
| Q3 | `gh` startup check | Agent Lifecycle | A — Hard fail at startup | High |
| Q5 | Existing `squidsquad` label | Migration | A — Reuse as-is | High |
| Q4 | Closed issue query policy | Query Design | A — Open-only default, PM/DM scan closed | High |
| Q1 | `working-state.md` ID format | Developer Experience | A — `#N (title)` | High |
| Q2 | Migration script packaging | Distribution | A — Part of upgrade, standalone-extractable | Medium |

All five questions have clear recommended paths. None are expected to be controversial — the research already pointed toward these answers. The main discussion value is confirming Q3 (whether hard-fail is too aggressive) and Q2 (whether standalone testing mode is worth the complexity).

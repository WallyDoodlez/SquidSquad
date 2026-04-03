# FEAT-SKILL-068 QA Results — Migrate Tracker to GitHub Issues

**QA Agent**: Fresh QA (no prior context)
**Date**: 2026-04-02
**Files Reviewed**:
- `references/sub-skills/common/tracker-protocol.md`
- `references/sub-skills/manifest.md`
- `references/agent-instructions.md` (grep for gh issue)
- `references/sub-skills/roles/dev-agent.md`
- `references/sub-skills/qa-specific/verification.md`
- `references/sub-skills/pm-specific/github-issues.md`
- `.squidsquad/config.md`

---

## CONTEXT Override

The CONTEXT was updated AFTER the test plan: **NO dual backend / markdown fallback**. GitHub Issues is the ONLY tracker. No config toggle, no setup question. TCs about dual backend, markdown fallback, or setup choice are SKIPPED as invalid.

---

## Per-TC Results

### TC-1: Setup asks user which tracker backend
**SKIP** — Invalid per CONTEXT. No setup question; GH Issues is the only tracker.

### TC-2: Soft-fail at startup when gh unavailable
**SKIP** — Invalid per CONTEXT. Startup is a hard-fail, not a soft-fail. The CONTEXT says: "Not a soft-fail -- SquidSquad needs GitHub." The implementation correctly prints an error and exits (tracker-protocol.md lines 11-15). The TC expected a fallback prompt, which no longer applies.

### TC-3: Label taxonomy created during setup (~25 labels, 6 dimensions)
**PASS** — tracker-protocol.md defines 25 labels across 7 dimensions: type (2), priority (3), status (7), role (5), design (3), severity (3), special (2). Each has a name and description. Colors are dev discretion per CONTEXT. Note: TC expected 9 status labels; implementation has 7 (no `status:rejected` or `status:open` -- `status:pending` serves as the initial state). The CONTEXT says "~25 labels" and "8 states" but the actual count of 7 status labels yielding 25 total is within the "~25" tolerance. Note: TC also expected `human-filed` and `delivery:skip` labels; neither exists in the taxonomy. `delivery:skip` is used as a Discussion keyword in QA verification, not as a label. `human-filed` is not implemented. These are minor -- the CONTEXT does not mandate these specific special labels.

### TC-4: Label dimensions are mutually exclusive where specified
**PASS** — tracker-protocol.md shows status transitions using `--remove-label` + `--add-label` in a single `gh issue edit` call (lines 107-115), ensuring only one status label at a time.

### TC-5: Agents use gh CLI for all tracker operations
**FAIL** — Partial implementation. Steps 2-3 in dev-agent.md correctly use `gh issue list`, `gh issue view`, `gh issue edit`, `gh issue comment`, `gh issue create`. QA verification.md uses gh CLI throughout. HOWEVER:
- **Gap 1**: dev-agent.md "File Conventions" section (line 253) still references "INDEX.md + individual files" for bugs and features.
- **Gap 2**: dev-agent.md "What You Must Never Do" section (line 282) says "regenerate the relevant INDEX.md" after status changes.
- **Gap 3**: dev-agent.md lines 283-284 say "move the file to the archived/ subdirectory" for terminal statuses -- this is a markdown tracker pattern.
- **Gap 4**: pm-specific/github-issues.md (Step 7b) lines 26-27 still file items as markdown files (`BUG-[ROLE]-XXX`, `FEAT-[ROLE]-XXX`) and increment config counters, rather than using `gh issue create`.

### TC-6: Discussion entries become Issue comments (timestamped, role-signed)
**PASS** — tracker-protocol.md lines 119-124 define comment format: `gh issue comment [NUMBER] --body "> [YYYY-MM-DD HH:MM] **[role]**: [message]"`. Dev-agent.md Steps 2-3 use this format. QA verification.md uses this format.

### TC-7: Status transitions via label changes
**PASS** — tracker-protocol.md lines 102-116 show label swap pattern for status transitions. Terminal statuses (shipped) include `gh issue close`. Dev-agent.md and QA verification.md follow this pattern.

### TC-8: Exclude closed issues from queries
**PASS** — `gh issue list` defaults to `--state open` in the gh CLI, so all queries correctly exclude closed issues without needing an explicit flag. The pm-specific/github-issues.md ingestion step does explicitly include `--state open`.

### TC-9: Issue numbers in working-state.md
**PASS** — tracker-protocol.md line 147: `Task: #42`. Dev-agent.md line 90: `Task: #[NUMBER]`.

### TC-10: Markdown fallback backend works independently
**SKIP** — Invalid per CONTEXT. No markdown fallback.

### TC-11: Tracker protocol sub-skill supports both backends
**SKIP** — Invalid per CONTEXT. Single backend only (GH Issues). However, the sub-skill file exists at `references/sub-skills/common/tracker-protocol.md` and is listed in `manifest.md` (line 125). PASS for the single-backend requirement.

### TC-12: Planning artifacts stay local in .squidsquad/
**PASS** — tracker-protocol.md lines 149-151 explicitly state planning artifacts remain local. Dev-agent.md Step 3 item 2 (lines 126-128) reads planning artifacts from local `.squidsquad/[ROLE]/planning/`. QA verification.md lines 73-84 read test plans from local paths.

### TC-13: Migration via /squidsquad-upgrade
**SKIP** — Cannot verify runtime migration behavior via static file review. Migration implementation details are dev discretion per CONTEXT. The CONTEXT confirms migration is part of the upgrade flow.

### TC-14: Migration preserves in-flight item statuses
**SKIP** — Cannot verify runtime migration behavior via static file review.

### TC-15: Skip-and-retry when GitHub unreachable
**PASS** — tracker-protocol.md lines 17: "If `gh` works but GitHub is temporarily unreachable during a cycle, skip tracker operations for this cycle and retry next cycle."

### TC-16: Health check probe at cycle start
**PASS** — tracker-protocol.md lines 7-15: Startup permission check runs `gh issue list --limit 1` before any tracker operations. Failure at boot = exit. Failure mid-cycle = skip and retry.

### TC-17: Filing a new bug via GH Issues
**PASS** — tracker-protocol.md lines 88-93: `gh issue create` with title, body, and labels including `bug`, `severity:`, `role:`, `squidsquad`. Dev-agent.md lines 226-228 show the same pattern.

### TC-18: Filing a new feature via GH Issues
**PASS** — tracker-protocol.md lines 95-97: `gh issue create` with `feature`, `priority:`, `role:`, `squidsquad`, `status:pending`.

### TC-19: Terminal status closes the issue
**PASS** — tracker-protocol.md lines 113-115: `gh issue edit` adds `status:shipped`, removes `status:pending-ship`, then `gh issue close`. QA verification.md lines 51-54 follow the same pattern.

### TC-20: Human-filed issues (without squidsquad label) are ingested
**FAIL** — pm-specific/github-issues.md is the ingestion step, but it has problems:
- It is gated behind `GitHub Issues Ingestion: yes` in config.md, which is currently set to `no`.
- It still uses old markdown tracker filing pattern (lines 26-27: `BUG-[ROLE]-XXX` files, increment counters) instead of `gh issue create` or `gh issue edit` to add labels to existing issues.
- It does NOT add the `squidsquad` label to ingested issues via `gh issue edit`.
- It does NOT classify and add `type:`, `role:`, `status:pending` labels.
- Instead it creates local markdown files, which contradicts the GH-Issues-only architecture.

### TC-21: Config.md updated correctly for GH Issues backend
**FAIL** — config.md is missing:
- No `Tracker: github-issues` field
- No `Label Taxonomy Version: 1` field
- ID counters (`BUG-SKILL: 40`, `FEAT-SKILL: 68`) still present -- should be removed per CONTEXT ("ID counters in config.md become obsolete for GH Issues backend")

### TC-22: Config.md unchanged for markdown backend
**SKIP** — Invalid per CONTEXT. No markdown backend.

### TC-23: Concurrent agent updates do not conflict
**PASS** — By design: GitHub Issues comments are append-only, label changes are idempotent. tracker-protocol.md line 124: "Comments are append-only -- never edit or delete previous comments."

### TC-24: Batch reads via gh issue list reduce API calls
**PASS** — tracker-protocol.md lines 66-78: Uses `gh issue list --json number,title,labels` for batch reads. Dev-agent.md Step 2 (line 85) uses the same pattern. Caching section (line 155) instructs caching within a cycle.

### TC-25: ID format uses #N in all agent output
**PASS** — Dev-agent.md line 119: `Implementing #[NUMBER]`. Working state uses `Task: #[NUMBER]`. Comments use `#[NEW_NUMBER]` for cross-references. Status bar state examples in dev-agent.md still reference `BUG-[ROLE_UPPER]-029` and `FEAT-[ROLE_UPPER]-037` format (lines 62-65), but these are placeholders that show the pattern -- the actual Step 2-3 code uses `#NUMBER`.

**Note**: Status bar state examples (lines 60-66) still use old `BUG-[ROLE_UPPER]-029` / `FEAT-[ROLE_UPPER]-037` format rather than `#N`. This is a minor inconsistency but does not affect functional behavior since the actual step code uses `#NUMBER`.

### TC-26: Migration builds old-ID-to-issue-number mapping
**SKIP** — Cannot verify runtime migration behavior via static file review.

### TC-27: Label taxonomy version tracked in config
**FAIL** — config.md does not contain `Label Taxonomy Version: 1`. See TC-21.

### TC-28: Vault (FEAT-SKILL-029) unaffected by migration
**PASS** — tracker-protocol.md makes no reference to vault. Vault protocol is a separate sub-skill (`common/vault-protocol.md`) per manifest.md.

### TC-29: Iteration logs and working-state.md remain local
**PASS** — Dev-agent.md lines 146-164: Iteration logs written to `.squidsquad/[ROLE]/iterations/`. Working state at `.squidsquad/[ROLE]/working-state.md`. Neither is migrated to GitHub Issues.

### TC-30: Setup detects existing label name conflicts
**SKIP** — Cannot verify runtime setup behavior via static file review. Label taxonomy uses namespaced format (e.g., `status:approved`) which minimizes conflicts.

---

## Gaps Summary

### GAP-1 (TC-5): dev-agent.md "File Conventions" still references markdown tracker
**Location**: `references/sub-skills/roles/dev-agent.md` lines 253, 257
**Issue**: References "INDEX.md + individual files" for bugs/features. Should reference GitHub Issues as the tracker.

### GAP-2 (TC-5): dev-agent.md "What You Must Never Do" references INDEX.md and archived/
**Location**: `references/sub-skills/roles/dev-agent.md` lines 282-284
**Issue**: Says "regenerate the relevant INDEX.md" and "move the file to the archived/ subdirectory" -- these are markdown tracker operations that no longer apply.

### GAP-3 (TC-5, TC-20): pm-specific/github-issues.md still files items as markdown
**Location**: `references/sub-skills/pm-specific/github-issues.md` lines 26-27
**Issue**: Ingestion step creates `BUG-[ROLE]-XXX` / `FEAT-[ROLE]-XXX` markdown files and increments ID counters. Should use `gh issue edit` to add labels to existing issues or `gh issue create` for new ones.

### GAP-4 (TC-21, TC-27): config.md missing GH Issues fields
**Location**: `.squidsquad/config.md`
**Issue**: Missing `Tracker: github-issues`, missing `Label Taxonomy Version: 1`, ID counters still present.

### GAP-5 (TC-25, minor): Status bar state examples use old ID format
**Location**: `references/sub-skills/roles/dev-agent.md` lines 60-65
**Issue**: Examples show `BUG-[ROLE_UPPER]-029` and `FEAT-[ROLE_UPPER]-037` instead of `#29` and `#37`. Minor inconsistency -- functional code in Steps 2-3 uses `#NUMBER`.

---

## Verdict

**FAIL** — 5 gaps found.

- 3 functional gaps (GAP-1 through GAP-3): leftover markdown tracker references in agent templates that would cause agents to attempt markdown file operations instead of GitHub Issues operations.
- 1 config gap (GAP-4): config.md not updated for GH Issues backend.
- 1 minor cosmetic gap (GAP-5): status bar examples use old ID format.

Per zero-gap gate: back to In Progress. All gaps must be resolved before Pending Ship.

### Score: 15 PASS / 5 FAIL / 4 SKIP (dual-backend invalid) / 6 SKIP (runtime-only)

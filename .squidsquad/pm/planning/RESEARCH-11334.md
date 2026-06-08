# RESEARCH-11334 — Canonicalize forge-usage instructions across sub-skills

**Tracker**: #11334
**Owning role**: skill (execution); PM produces this research + CONTEXT
**Base branch**: `squidsquad/skill/compose-polish-session` @ `695475567`
**Date**: 2026-06-08

---

## §0 — Branch basis lock

All line numbers in this document are relative to `squidsquad/skill/compose-polish-session` HEAD `695475567`. Skill will base its work branch off the same point and merge back to `compose-polish-session` per the operator chain-merge directive (same workflow that landed #11328 and #11330 into this bundle).

---

## §1 — Drift inventory validation

### §1.1 — Class 1: `create-issue` / `create-task` surfaces (11 confirmed)

All 11 surfaces in the issue body's drift inventory are present in the codebase. Confirmed by grep across `references/sub-skills/`:

| # | File | Line | Command | Notes |
|---|------|------|---------|-------|
| 1 | `common/tracker-protocol.md` | 68, 73 | `create-issue`, `create-task` | **Canonical-to-be**; already documents both with full flag set |
| 2 | `common/issue-filing.md` | 13, 22 | `create-issue` (self-file + cross-file) | Two near-identical blocks; full body templates inline |
| 3 | `common/improvement-scan.md` | 49 | `create-issue` / `create-task` (inline prose) | Mentioned but not full block |
| 4 | `common/improvement-scan-slim.md` | 11 | `create-issue` | Full block |
| 5 | `roles/pm/improvement-scan.md` | 66, 76 | `create-task` / `create-issue` | Prose-level reference |
| 6 | `roles/pm/task-intake.md` | 299 | `create-task` | Embedded in §V planning-PR flow |
| 7 | `roles/pm/vault-synthesis.md` | 63 | `create-task` | Full block |
| 8 | `roles/dm/issue-triage.md` | **34** | **`create-bug`** | **LEGACY ALIAS — REAL BUG CONFIRMED** |
| 9 | `roles/dm/doc-improvement-loop.md` | 77 | `create-task` | Full block |
| 10 | `roles/verifier/verification.md` | 60 | `create-issue` | Full block; non-canonical `--reporter verifier` (see §1.4) |
| 11 | `roles/worker/implement-tasks.md` | 97 | `create-issue` | Embedded in external-review escalation flow |

### §1.2 — Class 2: PR creation surfaces

Grep for `git_ops.py pr-create` and `gh pr create`:

- `common/git-commit.md:36` — full canonical-shaped block with body HEREDOC
- `common/git-commit.md:71` — second block (compact form, no HEREDOC)
- `roles/pm/task-intake.md:328` — planning-review PR variant

**No bare `gh pr create` instances found** in `references/sub-skills/`. The issue body's claim "Some places may also use bare `gh pr create`" is **not corroborated by current state**. AC3's drift-cleanup framing is therefore less aggressive than the body implies — the real AC3 work is **establishing the canonical statement** ("use `git_ops.py pr-create`, not bare `gh`") with rationale, not undoing bare-`gh` usage.

### §1.3 — Class 3: PR merge surfaces

Three lanes confirmed:

- **Verifier auto-merge lane**: `roles/verifier/verification.md` lines 314 (label gate), 324 (auto-merge ship), 333 (pending-human-review), 365 (rollback on merge conflict)
- **DM ship-pending lane**: `roles/dm/delivery-packaging.md` lines 29 (skip), 60 (transition), 74–86 (planning-citation guard + merge-conflict rollback prose), 102 (final ship)
- **PM pipeline-sentinel lane** (NEW — not in the issue's drift inventory): `roles/pm/pipeline-sentinel.md` lines 49 (PM transitions on PR-merge detection — *PM does not merge but mirrors merge state into tracker*), 80 (orphaned-PR triage)

The PM sentinel lane is **not redundant with the verifier/DM merge work** — it observes PR state and reconciles tracker labels — but a future "PR merge protocol" sub-skill should at least cross-reference it so the merge-event ↔ tracker-transition mapping is visible in one place.

### §1.4 — `--reporter` flag drift (NEW surface; partially covered by issue body)

The issue body claims `--reporter` naming is inconsistent. Grep confirms — three deviations from the issue body's locked `<alias>-lead` standard:

| File:line | Pattern | Deviation |
|---|---|---|
| `roles/dm/issue-triage.md:34` | `--reporter dm` | Bare alias (no `-lead` suffix) |
| `roles/verifier/verification.md:60` | `--reporter verifier` | Bare alias (no `-lead` suffix) |
| `common/improvement-scan-slim.md:13` | `--reporter [role]-lead` | Lowercase placeholder vs `[ROLE]-lead` convention elsewhere |

Canonical-conforming usages (for reference):
- `roles/dm/doc-improvement-loop.md:79` — `--reporter dm-lead` ✓
- `roles/pm/vault-synthesis.md:66` — `--reporter pm-lead` ✓
- `roles/verifier/verification.md:60` — `--reporter verifier` ✗ (same file as ✗ above)
- `common/issue-filing.md:16,25` — `--reporter [ROLE]-lead` ✓
- `roles/worker/implement-tasks.md:97` — `--reporter [ROLE]-lead` ✓

The legacy `create-bug` line and the bare-`dm`/`verifier` reporters cluster in the same two files (`dm/issue-triage.md` and `verifier/verification.md`), suggesting both files predate the `<alias>-lead` lock.

### §1.5 — Additional drift not in the issue inventory

**Legacy `list-bugs` alias**: `roles/dm/issue-triage.md:14` uses `list-bugs dm`. The canonical name is `list-issues` (per `tracker-protocol.md:49`); `list-bugs` is documented in `tracker.py --help` as an alias but is the legacy name. Same file as the `create-bug` bug. Worth bundling into the AC2 fix for that file since both deviations are colocated.

**Body-text reporter convention drift** (out of scope, flagged for awareness): `roles/dm/issue-filing.md:9-11` uses `**Reported By**: dm` body-text convention (not a `--reporter` flag value, but the human-readable label inside the issue body). This conflicts with the `<alias>-lead` standard already in use elsewhere (the #11334 issue body itself uses `Reported By: skill-lead`). NOT a `tracker.py` flag drift — it's a body-template style drift. **Recommendation**: leave to a future task; conflating it with AC1 muddies the AC1 surface.

### §1.6 — Role-level `issue-filing.md` files: validated NOT additional drift

Beyond `common/issue-filing.md`, three role-level files exist:

- `roles/dm/issue-filing.md` (12 lines) — policy + counter mention, no `tracker.py` syntax
- `roles/pm/issue-filing.md` (11 lines) — routing policy only
- `roles/verifier/issue-filing.md` (15 lines) — objective vs subjective policy + cross-link

**None duplicate the `create-issue` command shape.** These are role-policy add-ons that ride alongside `common/issue-filing.md`. They are NOT additional consolidation surfaces. (If `common/issue-filing.md` is retired per AC2 and these survive, they should `→ run sub-skill: tracker-protocol` for the wire mechanics, but the policy paragraphs stay.)

---

## §2 — Canonical doc current state

`common/tracker-protocol.md` already documents:

- `check-gh` startup check (§"Startup Permission Check")
- `list-tasks` / `list-issues` / `get-labels` / `get-state` (§"Reading Issues")
- `create-issue` + `create-task` with `<alias>-lead` reporter convention (§"Creating Issues", lines 67–76)
- `transition` with full legal-flow table (§"Status Transitions", lines 80–107)
- `comment` syntax (§"Discussion Entries", lines 113–115)
- A planning-artifact pointer (§"Planning Artifacts")

**Gaps the AC1 consolidation must close**:

1. **No "legacy aliases retired" subsection.** Need explicit note that `create-bug` → `create-issue`, `list-bugs` → `list-issues`, and (per `--help`) `create-feature` → `create-task`, `list-features` → `list-tasks`. AC1 lists this requirement explicitly.
2. **No per-finding-kind one-liner examples.** AC1 says "Each kind of finding (bug fix, feature task, improvement-scan finding, etc.) gets a one-line fill-in example." Current doc has only generic placeholders.
3. **Reporter lock is implicit, not explicit.** Current doc shows `[ROLE]-lead` in examples but never states "the reporter MUST be `<alias>-lead`; bare alias is non-canonical." The AC1 lock should be a one-liner with rationale.
4. **No PR-creation, no PR-merge coverage.** Current doc is tracker-only. AC3/AC4 add a new surface — whether by extending `git-commit.md` (option a) or creating `pr-protocol.md` (option b). See §3.

---

## §3 — Gray-area decisions for Phase 2

### §3.1 — AC3 option a vs b (PR creation canonical home)

**Option a**: Extend `common/git-commit.md` to be the canonical PR creation owner.
- *Pro*: Already documents PR creation via `git_ops.py pr-create` (two blocks). Co-locates branch/commit/PR wire flow.
- *Pro*: No new file; minimal directory churn.
- *Con*: `git-commit.md` becomes a longer "commit + PR" doc; naming becomes lossy.

**Option b**: Create new `common/pr-protocol.md` owning PR creation + merging together.
- *Pro*: Clean separation: `git-commit.md` = commit flow, `pr-protocol.md` = PR lifecycle.
- *Pro*: AC4 ("PR merge protocol") has a natural home; option a forces a merge subsection into `git-commit.md` which fits poorly.
- *Con*: New file; need to update composition manifest and any cross-refs.

**Recommendation for Phase 2 lock**: option b. Rationale: AC3 + AC4 together describe the *PR lifecycle* (open → merge → close). A dedicated `pr-protocol.md` covers both naturally; option a forces a "merge" section into a file named "commit" which inherits the same drift pattern this task exists to fix.

### §3.2 — AC4 option a vs b (PR merge canonical home)

Coupled to §3.1: if option b is picked there, option b here ("subsection in pr-protocol.md") follows mechanically. If option a is picked there, AC4 option a ("subsection in git-commit.md") also follows.

The two are not independently selectable — picking opposite options would split PR-creation and PR-merging across two files, which is exactly the drift this task fights.

### §3.3 — Should `common/issue-filing.md` be retired?

AC2 says "likely retired (its content was the inline reinvention; consolidate then evaluate retire)."

**Findings argue for retire**:
- Both blocks (self-file + cross-file) are full restatements of the canonical `create-issue` shape with body templates inlined
- Once AC1 documents per-finding-kind one-liner examples (including self-file and cross-file), `common/issue-filing.md` has nothing unique to say
- The role-level `issue-filing.md` files (§1.6) cover the *policy* layer (when/where to file) — `common/issue-filing.md` was attempting the *mechanics* layer, which is exactly what `tracker-protocol.md` owns

**Findings argue against retire**:
- The body-template strings inside the blocks (`**Description**:`, `**Steps to Reproduce**:`, etc.) are themselves a convention. If retired, that body convention needs to live somewhere — likely as a per-finding-kind example in `tracker-protocol.md`.

**Recommendation**: retire `common/issue-filing.md`, move body-template strings into `tracker-protocol.md` as part of the per-finding-kind one-liner examples (AC1 requirement). Update composition manifest. Verify no `composed CLAUDE.md` per-role file referenced it in slot ordering — if it did, that ordering slot is freed.

### §3.4 — Scope of `--reporter` drift cleanup

Two clear bugs (`--reporter dm`, `--reporter verifier`) plus one stylistic drift (`[role]-lead` vs `[ROLE]-lead`). The two bugs are clearly in scope under AC1 + AC2 (consolidation forces correct shape). The stylistic drift is borderline — fixing it is trivial and rides along, but it's a cosmetic case in a slim sub-skill.

**Recommendation**: fix all three as part of AC2's mechanical pass. Cost: one find/replace. Benefit: full canonicality.

### §3.5 — `list-bugs` legacy alias in `dm/issue-triage.md:14`

Same file as the `create-bug` bug. Out of strict AC scope (AC2 says "fix the bug" referring to `create-bug`), but colocated.

**Recommendation**: bundle into AC2 fix for `dm/issue-triage.md`. The whole file gets one consistent pass; no point leaving `list-bugs dm` as the only legacy-alias survivor.

---

## §4 — Out of scope (locked)

- `common-events/forge-read-pattern.md`, `event-mode-contract.md`, `event-driven-workflow.md`, `common/boot-bootstrap.md` — these mention `tracker.py` but at the *concept* layer ("forge-read pattern", "source of truth", "boot permission check") not the command-shape layer. They reference `tracker.py` correctly; no consolidation needed.
- All status-transition surfaces (`task-pickup.md`, `triage-issues.md`, `dm/task-pickup.md`, `verification.md` transition lines, `dm/delivery-packaging.md` transitions, `pm/pipeline-sentinel.md` transitions) — these correctly cite per-role transition flows from the legal-flow table. Drift here would be in `--role` value, not command shape; spot-check found no drift.
- Body-text `**Reported By**: dm` style in `dm/issue-filing.md:9` (per §1.5).
- Query command alignment beyond `list-bugs` (`list-by-labels`, `list-all-open`, `work-queue`) — all valid `tracker.py` subcommands per `--help`; no drift, just feature variety.
- `tracker.py` script behavior changes (per issue body §"Out of scope").

---

## §5 — Phase 2 inputs

The following questions are open for operator decision in Phase 2 (CONTEXT-11334):

1. **D-Lock 1** — AC3/AC4 home: option a (extend `git-commit.md`) vs option b (new `pr-protocol.md`). Recommendation: **option b**.
2. **D-Lock 2** — `common/issue-filing.md` fate: retire vs keep as thin reference. Recommendation: **retire**.
3. **D-Lock 3** — Scope of `--reporter` cleanup: bugs only vs bugs + stylistic. Recommendation: **bugs + stylistic** (single pass).
4. **D-Lock 4** — `list-bugs` alias in `dm/issue-triage.md`: in-scope under AC2 vs defer. Recommendation: **in-scope**.
5. **D-Lock 5** — DS audit cadence: one pass over the full consolidation (per issue body) vs per-AC. Recommendation: **one pass** — this is mechanical drift cleanup with low cross-AC coupling.

---

## §6 — Confirmed safe to proceed

- All 11 inventory surfaces validated against current state
- 1 legacy alias bug confirmed real (`create-bug` in `dm/issue-triage.md:34`)
- 2 additional `--reporter` drift bugs found (also in `dm/issue-triage.md` + `verifier/verification.md`)
- 1 colocated legacy alias found (`list-bugs` in `dm/issue-triage.md:14`)
- Role-level `issue-filing.md` files validated NOT in scope
- No bare `gh pr create` usages found (AC3 framing is *establish canonical*, not *replace drift*)
- Branch basis locked: `squidsquad/skill/compose-polish-session` @ `695475567`

Ready for Phase 2 D-Lock decisions.

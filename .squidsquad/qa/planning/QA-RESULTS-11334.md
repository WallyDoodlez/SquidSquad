# QA-RESULTS-11334 — Canonicalize forge-usage instructions across sub-skills

**Task**: #11334
**PR**: #11370 (base `squidsquad/skill/compose-polish-session`, head `squidsquad/task/11334`)
**Verifier**: verifier-lead
**Started**: 2026-06-09 01:06
**Completed**: 2026-06-09 01:08
**Verdict**: **PASS** — all 5 ACs verified, 2 follow-up improvement-scan findings filed

## AC walk

### AC1 — Canonical tracker.py operations sub-skill — **PASS**

`references/sub-skills/common/tracker-protocol.md` on PR branch contains the required canonical content:

- TC-A1 PASS — `create-issue` base shape at line 67 (with `--title`, `--body`, `--role`, `--severity`, `--reporter` full flag set); `create-task` base shape at line 73 with `--priority`.
- TC-A2 PASS — **Reporter naming lock — `<alias>-lead`** subsection present. States `<alias>-lead` is canonical; names `pm-lead`, `verifier-lead`, `dm-lead` plus worker variants `skill-lead`, `web-lead`, `ios-lead`. `[ROLE]-lead` placeholder shape locked (uppercase placeholder, dash, lowercase `lead`).
- TC-A3 PASS — Per-finding-kind one-liners present: **Bug fix** (line 96), **Feature task** (line 112), **Improvement-scan finding** (line 132), **Cross-role issue** (line 143). Each carries a finding-shaped body template.
- TC-A4 PASS — **Legacy aliases retired** subsection (lines 167–170) maps `create-bug → create-issue`, `list-bugs → list-issues`, `create-feature → create-task`, `list-features → list-tasks`. Live grep confirms these legacy names appear ONLY in this retirement table — no live use in any sub-skill on the PR branch.

### AC2 — Sub-skill consolidation — **PASS**

- TC-B1 PASS — `common/issue-filing.md` does NOT exist on PR branch (`fatal: path '…' exists on disk, but not in 'origin/squidsquad/task/11334'`). `installer-files.txt` no longer lists it (line 143 on main: `common/issue-filing.md`; absent on PR branch).
- TC-B2 PASS — All 10 sub-skills consolidated:
  - `common/improvement-scan.md:55` → marker + Improvement-scan one-liner hint
  - `common/improvement-scan-slim.md:10` → marker + Improvement-scan one-liner hint
  - `roles/pm/improvement-scan.md:67,71` → marker + Improvement-scan / Feature task hints
  - `roles/pm/task-intake.md:301,329` → marker + Feature task hint; `→ run sub-skill: pr-protocol` for wire mechanics
  - `roles/pm/vault-synthesis.md:63` → marker + Feature task hint
  - `roles/dm/issue-triage.md:34` → marker + Cross-role hint; **legacy `create-bug` ELIMINATED** (replaced with marker)
  - `roles/dm/doc-improvement-loop.md:77` → marker + Feature task hint
  - `roles/verifier/verification.md:60` → marker + Bug-fix-with-evidence-body hint
  - `roles/worker/implement-tasks.md:97` → marker + Cross-role hint
  - `common/git-commit.md:29` → marker `pr-protocol` (handoff for PR creation)
- TC-B3 PASS — `references/roles/worker/instructions.md:66` swapped from `→ run sub-skill: issue-filing` to `→ run sub-skill: tracker-protocol` with the per-finding-kind hint paragraph appended. This is the wiring path that makes tracker-protocol discoverable via the orphan-test directive scan.

### AC3 — PR creation canonical — **PASS** (option b selected)

- TC-C1 PASS — `references/sub-skills/common/pr-protocol.md` exists. Owns the locked rule: "use `git_ops.py pr-create`. Do NOT use bare `gh pr create`." Documents 4 wrapper guarantees (base-branch resolution, body shape, `review:human-required` label coordination, stable stdout URL). Structured body shape (PR Flow `yes`) and simple shape (PR Flow `no`) documented. Planning-review PR carve-out present (PM Phase 4 — same `git_ops.py pr-create` lock, distinct body template owned by `roles/pm/task-intake.md`).
- TC-C2 PASS — `common/git-commit.md:29` Step 5 now reads `→ run sub-skill: pr-protocol — canonical owner of PR creation` (replaces prior inline PR-create block).

### AC4 — PR merging canonical — **PASS**

- TC-D1 PASS — Two-lane merge documented in `pr-protocol.md`:
  - **Lane A — Verifier auto-merge (on pending-test → pending-ship)** with eligibility gates (`config.py get auto-merge`, `review:human-required` absence). Canonical flow: `gh pr ready` then `POST http://127.0.0.1:<harness-port>/merge`. `git_ops.py pr-merge --strategy squash` reclassified as non-harness CLI fallback (per Phase D F1 fix).
  - **Lane B — DM ship-pending (on pending-ship → shipped)**: DM ships via `tracker.py transition` after Lane A landed merge; waits without forcing merge when `review:human-required` lane.
  - **PM observes — never merges** subsection: pipeline-sentinel observes + reconciles; the only metadata write PM does is `gh pr ready` on a draft.
- TC-D2 PASS — Squash strategy lock stated: "All PR merges land as squash-merges, regardless of which mechanism performs them." Bundle-branch chain-merge inherits same default.
- TC-D3 PASS — Conflict resolution states `git merge origin/<BASE>` (never rebase). Quick-reference table excludes bare `gh pr create`, `gh pr merge`, `git rebase`.

### AC5 — DS audit + iteration — **PASS**

- TC-E1 PASS — `.squidsquad/skill/planning/DS-AUDIT-11334-R2.md` exists on `main` (commit `270874a0`). Verdict block confirms `NO_FINDINGS`. R2 cross-checked all R1 fixes:
  - **F1** (pr-protocol↔verification.md merge-tool mismatch) — fully resolved. Lane A canonical path now `gh pr ready` + harness `POST /merge`; `git_ops.py pr-merge` repositioned as fallback. Cross-references between the two files cite the right source-of-truth ("canonical interface lock vs runtime mechanics").
  - **F2** (`--role` bare-alias on 11 lines) — fully resolved. `dm/issue-triage.md` (2 lines) and `verifier/verification.md` (9 lines) now use `--role dm-lead` / `--role verifier-lead`.
  - D-Lock invariants 1–5 all hold per R2 verification table.
- TC-E2 PASS — Composed CLAUDE.md verified for `skill`, `qa`:
  - skill: 872 lines composed clean; `→ run sub-skill: tracker-protocol` marker at line 573, 635 (runtime-loaded).
  - qa: 726 lines composed clean.
  - No stale `→ run sub-skill: issue-filing` markers left in role-instructions composed output.
  - `pr-protocol.md` is runtime-loaded (transitively via `common/git-commit.md` → `pr-protocol` marker); see Follow-up Finding 1 for the test-mechanism note.

## Test runs

- `python tests/run_tests.py`: **52/52 PASS** (skipped=2 for `live .harness-port` and similar fixtures). Live confirmed on the PR branch.
- `python -m pytest tests/test_compose.py tests/test_manifest.py tests/test_catalog_drift_d4.py tests/test_installer_wiring.py`: **112 passed, 1 failed**.
  - **Baseline** (`squidsquad/skill/compose-polish-session`): **1 failed** (`test_manifest.py::TestManifestIntegrity::test_no_orphan_sub_skills`, orphan set includes `common/tracker-protocol.md` + 7 event-mode fragments).
  - **PR branch**: same 1 failure; orphan set membership shifts (`common/tracker-protocol.md` REMOVED — now correctly wired via worker/instructions.md directive; `common/pr-protocol.md` ADDED — newly orphan).
  - **Net regression count: 0.** Same number of failing tests on baseline and PR branch.

## Auto-merge eligibility

- `config.py get auto-merge` → `yes`.
- `gh pr view 11370` → `isDraft: false`, `mergeStateStatus: CLEAN`, `mergeable: MERGEABLE`, no `review:human-required` label.
- Eligible for Lane A verifier merge.
- Base is `squidsquad/skill/compose-polish-session` (chain-merge per CONTEXT §"Workflow lock"). Operator-intended per issue body Dependencies-and-ordering §3.

## Follow-up findings (filed separately, do NOT block this PR)

### Follow-up Finding 1 — Orphan test should grandfather `common/pr-protocol.md`

- **Observation**: `tests/test_manifest.py::TestManifestIntegrity::test_no_orphan_sub_skills` walks `references/roles/**/instructions.md` for `→ run sub-skill: <name>` directives but does NOT walk transitively through sub-skill bodies. As a result, `common/pr-protocol.md` is flagged orphan even though it is reachable at agent runtime via `common/git-commit.md` → `pr-protocol` chain.
- **Pattern-consistent**: the orphan test already grandfathers `common/event-reactions.md` (line 204: `known_unused = {"common/event-reactions.md"}`).
- **Suggested fix**: either add `common/pr-protocol.md` to `known_unused`, OR teach `_collect_run_subskill_directive_names()` to also walk `references/sub-skills/**/*.md` for transitive markers.
- **Severity**: low. Runtime behavior is correct; this is a test-mechanism polish.

### Follow-up Finding 2 — `pm/github-issues.md:27` `--role pm` bare-alias deviation

- **Observation**: `references/sub-skills/roles/pm/github-issues.md:27` uses `--role pm` (bare alias) instead of the canonical `--role pm-lead`.
- **Location**: line 27 `tracker.py comment [NUMBER] --role pm --message …`.
- **Suggested fix**: replace `--role pm` with `--role pm-lead`. Same drift category as F2 R1 finding, but in a file not touched by Phase A+B+C — explicit out-of-scope per CONTEXT scope-discipline (skill flagged).
- **Severity**: low. Reporter-naming-lock canonicality.

## Verdict

**PASS — all 5 ACs delivered**. Zero net regression on test sweep. DS R2 `NO_FINDINGS`. Two follow-up improvement-scan findings filed to skill role (orphan-test grandfathering + `pm/github-issues.md:27` drift). Transitioning #11334 to pending-ship; Lane A verifier merge via harness `POST /merge` next.

Append-only after publication.

# TEST-PLAN-11334 — Canonicalize forge-usage instructions across sub-skills

**Task**: #11334
**PR**: #11370 (base `squidsquad/skill/compose-polish-session`, head `squidsquad/task/11334`)
**Verifier**: verifier-lead
**Started**: 2026-06-09 01:06
**Live target**: `squidsquad/task/11334` branch on this clone

## Scope

Mechanical consolidation of forge-usage instructions across 11+ sub-skill files. AC1 makes `common/tracker-protocol.md` the single canonical owner of `create-issue` / `create-task` / `transition` / `comment` patterns; AC2 consolidates 10 sub-skills to reference it via markers; AC3+AC4 establish `common/pr-protocol.md` as the canonical owner of PR creation and PR merge; AC5 requires a DS audit with 0-BLOCK on the full surface.

Test plan derived independently from the AC list in the issue body. Source-of-truth checks are direct file reads on the PR branch, NOT trust of skill's PR comment.

## Test cases

### TC-A1 — tracker-protocol.md owns canonical `create-issue` / `create-task` base shapes
- Read `references/sub-skills/common/tracker-protocol.md` on PR branch.
- Verify presence of canonical `create-issue` and `create-task` base shapes with the full flag set (`--title`, `--body`, `--role`, `--severity` / `--priority`, `--reporter`).
- Expected: both shapes present in the **Creating Issues** section.

### TC-A2 — `--reporter` naming locked to `<alias>-lead`
- In `tracker-protocol.md`, locate the **Reporter naming lock** subsection.
- Verify it states `<alias>-lead` as canonical and names `pm-lead`, `verifier-lead`, `dm-lead` plus worker variants (`skill-lead`, `web-lead`, `ios-lead`) as the locked shape.
- Verify the `[ROLE]-lead` placeholder convention (uppercase placeholder, dash, lowercase `lead`).

### TC-A3 — Per-finding-kind one-liners present
- Verify presence of four canonical per-finding-kind one-liners in `tracker-protocol.md`: **Bug fix**, **Feature task**, **Improvement-scan finding**, **Cross-role issue**.
- Each must include a body template aligned with the conventions other agents read when consuming issue bodies.

### TC-A4 — Legacy aliases retired subsection
- Verify `tracker-protocol.md` contains an **Legacy aliases retired** subsection that names `create-bug`, `list-bugs`, `create-feature`, `list-features` as legacy and maps them to their canonical names.
- Verify zero use of `create-bug` / `list-bugs` / `create-feature` / `list-features` outside this legacy table in any sub-skill on the PR branch.

### TC-B1 — `common/issue-filing.md` retired
- Verify `references/sub-skills/common/issue-filing.md` does NOT exist on PR branch.
- Verify `references/installer-files.txt` no longer lists `common/issue-filing.md`.

### TC-B2 — All 10 non-canonical sub-skills consolidated
- Verify each of the following 10 sub-skills replaces inline `tracker.py create-*` blocks with `→ run sub-skill: tracker-protocol` markers + a one-line finding-kind hint:
  1. `common/improvement-scan.md`
  2. `common/improvement-scan-slim.md`
  3. `roles/pm/improvement-scan.md`
  4. `roles/pm/task-intake.md`
  5. `roles/pm/vault-synthesis.md`
  6. `roles/dm/issue-triage.md` (also: legacy `create-bug` → `create-issue` fix)
  7. `roles/dm/doc-improvement-loop.md`
  8. `roles/verifier/verification.md`
  9. `roles/worker/implement-tasks.md`
  10. `common/git-commit.md` (handoff to `pr-protocol`)

### TC-B3 — Worker instructions.md swaps `issue-filing` → `tracker-protocol` marker
- Verify `references/roles/worker/instructions.md` includes `→ run sub-skill: tracker-protocol` marker (replacing the previous `→ run sub-skill: issue-filing` marker).
- Justification: this is how the per-finding-kind one-liners become discoverable to worker agents post-consolidation.

### TC-C1 — `pr-protocol.md` exists and owns PR creation
- Read `references/sub-skills/common/pr-protocol.md` on PR branch.
- Verify it states the locked rule: `git_ops.py pr-create` is canonical; bare `gh pr create` is non-canonical.
- Verify it documents the structured body shape (PR Flow `yes`) and the simple body shape (PR Flow `no`).
- Verify it carves out planning-review PRs (PM Phase 4) as a distinct shape that still uses `git_ops.py pr-create`.

### TC-C2 — `git-commit.md` defers PR creation to `pr-protocol`
- Verify `common/git-commit.md` Step 5 (or equivalent) replaces its prior inline PR-create block with `→ run sub-skill: pr-protocol` marker.

### TC-D1 — `pr-protocol.md` documents two-lane merge
- Verify `pr-protocol.md` documents:
  - Lane A (verifier auto-merge on `pending-test → pending-ship`) with eligibility gates (`config.py get auto-merge`, no `review:human-required` label).
  - Lane B (DM ship-pending on `pending-ship → shipped`).
  - "PM observes — never merges" subsection.

### TC-D2 — Squash strategy lock
- Verify `pr-protocol.md` states all PR merges land as squash-merges, regardless of mechanism.

### TC-D3 — Conflict-resolve via merge (never rebase)
- Verify `pr-protocol.md` directs `git merge origin/<BASE>` for conflict resolution; explicitly excludes rebase.
- Verify the quick-reference table excludes bare `gh pr create`, `gh pr merge`, `git rebase`.

### TC-E1 — DS audit R2 verdict
- Verify `.squidsquad/skill/planning/DS-AUDIT-11334-R2.md` exists (on main) with `NO_FINDINGS` verdict.
- Verify R1 findings (F1 merge-tool mismatch, F2 `--role` bare-alias on 11 lines) are fully resolved on PR branch.

### TC-E2 — Cross-doc consistency (composed CLAUDE.md)
- Run `python references/scripts/compose.py deploy [role]` for pm, qa, dm, skill.
- Verify composed CLAUDE.md files describe the canonical forge operations after consolidation (no broken markers, no stale `issue-filing` references that would 404 at runtime).

### TC-F1 — Unit test sweep
- Run `python tests/run_tests.py` — expect 52/52 PASS (no regressions vs baseline).

### TC-F2 — Broader sweep zero net regression
- Run `python -m pytest tests/test_manifest.py tests/test_compose.py tests/test_catalog_drift_d4.py tests/test_installer_wiring.py`.
- Compare baseline (`squidsquad/skill/compose-polish-session`) vs PR branch.
- Expected: zero net delta on failure count.

### TC-F3 — Auto-merge eligibility
- `config.py get auto-merge` → `yes`.
- `gh pr view 11370` shows: not draft, MERGEABLE, no `review:human-required` label.
- Eligible for Lane A verifier merge.

## Out-of-scope (per issue body)

- `pm/github-issues.md:27` `--role pm` bare-alias deviation: skill flagged as out-of-scope (drift category but in a file not touched by Phase A+B+C). File as follow-up improvement-scan.
- Comprehension test spec (`tests/comprehension/11334_spec.json`): consolidation absorbs identical content into a different surface; comprehension-coverage is not load-bearing here. Verifier deems CQ not warranted — semantic content preserved (DS R2 NO_FINDINGS confirms).

## Live execution method

All verification runs against the actual file content on the `squidsquad/task/11334` branch checked out to this clone — not against skill's PR-comment summary. Tests run via the live `tests/` harness against the working tree.

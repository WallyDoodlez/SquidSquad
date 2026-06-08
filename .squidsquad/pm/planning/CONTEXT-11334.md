# CONTEXT-11334 — Phase 2 D-Locks

**Tracker**: #11334
**Owning role**: skill (execution); PM produces RESEARCH + CONTEXT only
**Base branch**: `squidsquad/skill/compose-polish-session` @ `695475567`
**Companion**: `RESEARCH-11334.md` (Phase 1 drift validation)
**Date**: 2026-06-08

This document records the five operator-locked decisions from Phase 2 discuss. Skill executes against these locks; deviations require operator re-approval.

---

## D-Lock 1 — PR creation + merge canonical home (AC3 + AC4)

**LOCKED**: Create new `references/sub-skills/common/pr-protocol.md`.

- AC3 (PR creation) and AC4 (PR merge) both live in `pr-protocol.md`.
- `common/git-commit.md` stays focused on the commit flow (branch creation, commit, push). Its existing PR-creation blocks (`git-commit.md:36` and `git-commit.md:71`) move into `pr-protocol.md` and are replaced with a `→ run sub-skill: pr-protocol` reference at the point where the commit flow hands off to PR creation.
- `roles/pm/task-intake.md:328` (planning-review PR) keeps its planning-PR-specific framing but references `pr-protocol.md` for the wire mechanics.
- Composition manifest gets updated to include the new sub-skill.

**Why**: AC3 and AC4 together describe the PR lifecycle (open → merge → close). A dedicated file owns that lifecycle cleanly; extending `git-commit.md` would make a "commit"-named file own PR creation AND PR merge — exactly the drift pattern this task fights.

**Content `pr-protocol.md` must own**:
1. PR creation via `git_ops.py pr-create` with locked rule: "use `git_ops.py pr-create`; do NOT use bare `gh pr create`" + rationale (base branch, body template, review-required label coordination).
2. PR merge protocol naming both lanes: verifier auto-merge eligibility + ship; DM ship-pending merge wait. Cross-refs to `roles/verifier/verification.md` and `roles/dm/delivery-packaging.md` for role-specific procedures.
3. Cross-ref to `roles/pm/pipeline-sentinel.md` noting PM observes-and-reconciles PR merge state into tracker labels (does not merge).

---

## D-Lock 2 — Retire `common/issue-filing.md`

**LOCKED**: Retire `references/sub-skills/common/issue-filing.md`.

- Both blocks in the file (self-file at line 13, cross-file at line 22) are full restatements of the canonical `create-issue` shape. AC1's per-finding-kind one-liner requirement absorbs all unique content.
- Body-template strings (`**Description**:`, `**Steps to Reproduce**:`, `**Expected**:`, `**Actual**:`) move into `tracker-protocol.md` as part of the per-finding-kind one-liner examples (AC1 requirement).
- Composition manifest update: remove `common/issue-filing` slot.
- Verify no `composed CLAUDE.md` per-role file relied on the slot for ordering — if any did, that ordering slot is freed (no replacement needed; `tracker-protocol.md` already sits in slot ordinal 11).
- Role-level `roles/{dm,pm,verifier}/issue-filing.md` files SURVIVE — they carry policy (when/where to file), not command shape. Their content does not duplicate `common/issue-filing.md`; the name overlap is coincidental.

**Why**: The file was the canonical AC1-style inline reinvention surface. Retiring it after AC1 absorbs its content is the cleanest end state.

---

## D-Lock 3 — `--reporter` cleanup scope

**LOCKED**: Fix all three deviations in the AC2 mechanical pass.

| File:line | Current | Fixed |
|---|---|---|
| `roles/dm/issue-triage.md:34` | `--reporter dm` | `--reporter dm-lead` |
| `roles/verifier/verification.md:60` | `--reporter verifier` | `--reporter verifier-lead` |
| `common/improvement-scan-slim.md:13` | `--reporter [role]-lead` | `--reporter [ROLE]-lead` |

**Why**: Three single-line fixes. Leaving any survivor leaves a known deviation in a "canonicalization" task. Single find/replace pass.

---

## D-Lock 4 — `list-bugs` in `dm/issue-triage.md:14` is in-scope under AC2

**LOCKED**: Fix `list-bugs dm` → `list-issues dm` in `roles/dm/issue-triage.md:14` as part of the AC2 mechanical pass.

- Same file as the `create-bug` legacy-alias bug at line 34 (already in AC2 scope).
- Same legacy-alias deviation pattern (`list-bugs` and `create-bug` are both `tracker.py --help` aliases for `list-issues` and `create-issue`).
- Same commit; same review surface.

**Why**: Leaving one legacy-alias survivor in the same file we are fixing the other for is silly. Bundle.

---

## D-Lock 5 — DS audit cadence: one pass

**LOCKED**: One DS audit pass after all of AC1, AC2, AC3, AC4 work lands. Iterate only if DS surfaces findings.

- Audit surface should be small post-consolidation.
- Audit goal: 0-BLOCK per issue body AC5.
- Cross-doc consistency check explicitly in scope (composed CLAUDE.md per-role still describes the right forge operations after consolidation — no functional regression).
- If a finding is surfaced, normal iterate-then-re-audit loop applies (same model_router workflow as #11328).

**Why**: This is mechanical drift cleanup with low cross-AC coupling. Each AC consolidates a distinct surface (Class 1 vs Class 2 vs Class 3 vs canonical PR doc creation). Per-AC DS passes add overhead without added safety here.

---

## Out-of-scope reminders (locked from issue body §"Out of scope")

- Composed `.squidsquad/<role>/CLAUDE.md` updates beyond what AC2 produces mechanically
- `tracker.py` script changes
- New tracker operations / new lifecycle states
- `docs/COMPOSE-ARCHITECTURE.md` or other arch doc updates
- Renaming `tracker.py` command names themselves
- Body-text reporter conventions in `roles/dm/issue-filing.md` (`**Reported By**: dm` style) — per RESEARCH §1.5, deferred to a separate task

---

## Workflow lock

1. **Skill branches off `squidsquad/skill/compose-polish-session`** for #11334 work.
2. **Skill executes AC1–AC4** against the locks above. Reference RESEARCH-11334.md for the validated drift inventory and surface-by-surface mapping.
3. **One DS audit pass** post-execution (AC5).
4. **PR base = `squidsquad/skill/compose-polish-session`** (chain-merge, not main).
5. **No version bump, no CHANGELOG entry, no 28/10 bump-gate advance** — chain-merge semantics; release fires once when the super-bundle lands on main.
6. **On merge into `compose-polish-session`**, #11144 polish iteration resumes.

---

## Operator quote (for commit message)

> "no consistent instructions on forge usage (issue file, merging, PR creation)"

Recorded verbatim per issue body's picker note.

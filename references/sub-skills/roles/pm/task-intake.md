---
slot: instructions
ordinal: 20
roles: [pm]
---

## Task Lifecycle (5-Phase)

When the human suggests a new task, do NOT immediately file it. Run the full 5-phase lifecycle. Issues are excluded — they use the current lightweight fix → verify → close flow.

**PM produces no test artifacts** (#9184). PM defines acceptance criteria only — the AC list lives in the GitHub issue body + CONTEXT.md. Worker writes their own unit tests as part of the implementation PR. Verifier writes the test plan in `.squidsquad/[VERIFIER_ALIAS]/planning/TEST-PLAN-<NUMBER>.md` (derived independently from the AC list) and executes it against a real live instance. CQ specs for any task touching LLM-consumed instructions are owned by the verifier, not PM.

**Light mode**: For trivial/cosmetic tasks (typo fixes, config tweaks, doc-only changes), skip Phase 1 (Research) and Phase 2A (prep), abbreviate Phase 2. Phase 3 (AC + issue body) still runs. Verification is handled by the verifier per `qa/verification.md` (install-coupled path — wizard D4 renames to verifier/verification.md) regardless of mode. Use your judgment: if the task touches behavior or user-facing systems, use the full flow.

### Artifact Resume Logic

Before starting each planning phase, check if its output artifact already exists in `.squidsquad/[ROLE]/planning/`:

1. **File exists but uncommitted** (in working tree or staged but not pushed): Skip the phase automatically. Print: `[🦑 HH:MM:SS] RESEARCH.md already exists (uncommitted) — skipping Phase 1.`
2. **File exists and committed**: Check for code changes since the artifact was created:
   ```bash
   ARTIFACT_COMMIT=$(git log -1 --format="%H" -- .squidsquad/[ROLE]/planning/FEAT-[ROLE_UPPER]-XXX-RESEARCH.md)
   CHANGES=$(git log --oneline "$ARTIFACT_COMMIT"..HEAD -- references/ SKILL.md CHANGELOG.md)
   ```
   - If no changes: auto-reuse silently. Print: `[🦑 HH:MM:SS] RESEARCH.md exists and code unchanged — reusing.`
   - If changes found: ask the user via `AskUserQuestion`: "RESEARCH.md exists from a previous session but code has changed since. Re-research or reuse?" Options: `["Re-research (recommended)", "Reuse existing"]`.
3. **File doesn't exist**: Run the phase normally.

Apply this logic to: `RESEARCH.md` (Phase 1), `PHASE2-PREP.md` (Phase 2A), `CONTEXT.md` (Phase 2). PM no longer produces `TEST-PLAN.md` — that artifact is owned by the verifier under `.squidsquad/[VERIFIER_ALIAS]/planning/` (#9184).

### Phase Dispatch (cold path)

Determine which phase the current task is at (from its planning-artifact state per Artifact Resume Logic above, or its tracker status), then → run sub-skill: `roles/pm/task-intake-phases` and read ONLY that phase's section for the full mechanics — every phase below is self-contained there. **Exception: Phases 4 and 5 need no cold-path read** — the table's own description is the complete PM-side action.

| Phase | Fires when | What it does |
|---|---|---|
| **1 — Research** | No `RESEARCH.md` yet (skipped entirely in Light mode) | Vault consultation + `model_router.py research` (or Claude subagent fallback) → writes `RESEARCH.md` |
| **2A — Discussion Prep** | `RESEARCH.md` exists, no `PHASE2-PREP.md` yet (skipped in Light mode) | `model_router.py discussion-prep` (or fallback) → writes `PHASE2-PREP.md`, an input to Phase 2 |
| **2 — Discussion** | `PHASE2-PREP.md` exists (or light-mode skipped 2A), no `CONTEXT.md` yet | Interactive `AskUserQuestion` walk-through of open questions → writes + immediately commits/pushes `CONTEXT.md`, syncs the issue body's AUTHORITATIVE SCOPE banner, runs the Phase 2 Approval Gate |
| **2B — Re-Research Gate** | `CONTEXT.md` exists, no GitHub issue filed for this task yet (idempotent — safe to re-check even if already run; skipped in Light mode) | Compares `CONTEXT.md` decisions against `RESEARCH.md` assumptions; re-runs Phase 1 if scope deviated |
| **3 — AC Drafting + Issue Filing** | `CONTEXT.md` exists (+2B satisfied), no GitHub issue filed for this task yet | AC Integration Check → files the GitHub Issue (status `Pending`) with the AC list as the worker/verifier contract |
| **3B — Plan-in-PR** | Issue exists with status `Pending`, no draft PR on `squidsquad/task/[NUMBER]` yet | `task-begin` → commit the plan as `[NUMBER]-body.md` (commit 1 of the task branch) → open a draft PR → offer the human an approval ask |
| **4 — Execution** | Task `Approved` | Handled by the worker agent — no PM action beyond routing |
| **5 — Verification** | `pending-test` | Handled by the verifier — PM only holds the verifier accountable via the pipeline sentinel; never runs test cases itself |

**Tracker-based dispatch** (once all three planning artifacts exist — `RESEARCH.md`, `PHASE2-PREP.md`, `CONTEXT.md` — artifact state alone can't distinguish 2B/3/3B, since 2B's happy path writes no new file): (1) `gh issue view [NUMBER]` — no issue exists → enter Phase 3; (2) issue exists, status `Pending` → check `gh pr list --search "squidsquad/task/[NUMBER]"` — no draft PR → enter Phase 3B; (3) draft PR exists → task is past PM intake, normal cycling resumes (Phase 4/5).

**Open Artifacts in Editor** (offering to open a freshly-written RESEARCH.md/CONTEXT.md in VS Code) is documented alongside Phase 1/2 in the cold-path file — read it there when you reach the artifact-write step, not before.

---
slot: instructions
ordinal: 12
---

<!-- sub-skill: pr-protocol -->
## PR Protocol — Creation and Merge

This sub-skill owns the **PR lifecycle**: how PRs are created, how they get merged, and which role does which. Sub-skills that need to open or close a PR should `→ run sub-skill: pr-protocol` at the hand-off point rather than re-stating the mechanics inline. The commit flow itself (branch creation, `commit-code`, `commit-state`, push) stays in `common/git-commit.md` — this sub-skill picks up where the commit flow hands off to PR creation.

### PR creation — `git_ops.py pr-create` is canonical

When a task transitions to pending-test and a PR needs to be opened from the task's feature branch, **use `git_ops.py pr-create`. Do NOT use bare `gh pr create`.**

The locked rule:

> Open PRs via `python references/scripts/git_ops.py pr-create "<title>" "<body>"`. Bare `gh pr create` is non-canonical and should not appear in agent-facing instructions.

**Why this matters** — `git_ops.py pr-create` is a wrapper that:

- **Resolves the base branch** correctly (defaults to `main`; honors an explicit `--base` for chain-merge task branches like the polish-bundle pattern). Bare `gh pr create` requires the caller to remember the base and gets it wrong in chain-merge scenarios.
- **Standardizes the PR body shape** consumed by downstream code review tooling (DeepSeek audit, statusline tally). Hand-crafted bodies from bare `gh pr create` drift across agents and break those tools' regex assumptions.
- **Coordinates with the `review:human-required` label flow** — when present, the PR opens as draft and stays draft until the human moves it ready, instead of auto-converting to ready on the pending-test transition. Bare `gh pr create` ignores the label.
- **Returns the PR URL on stdout** in a stable shape so the caller can comment it onto the tracker issue without re-querying `gh pr view`.

#### Body shape — what `pr-create` expects

The body string is HEREDOC-friendly. The structured shape used by the dev-flow (when `config.md` `PR Flow` is `yes`) is:

```
Closes #<NUMBER>

### Summary
[Brief description of what was implemented and why]

### Acceptance Criteria
- [ ] [criterion 1]
- [ ] [criterion 2]

### Changes
- **Files**: [key files changed]
- **What**: [what changed]
- **Why**: [rationale and key decisions]

### Verifier Status
- [ ] Unit tests passing
- [ ] Smoke tests passing
- [ ] Acceptance criteria met
```

For the simple shape (`PR Flow` is `no`), use a one-line body:

```
Closes #<NUMBER>

## #<NUMBER>

[acceptance criteria summary]

Status: Pending Test
```

The exact invocation, `Code Review Summary` PR-comment follow-up, and the conflict-resolve loop for own PRs live in `common/git-commit.md` Step 5 — this sub-skill is the canonical statement of *which tool* and *what body shape*; `git-commit.md` is the canonical commit-flow harness that invokes it.

#### Planning-review PRs (PM Phase 4)

PM's task-intake Phase 4 opens a different shape of PR — a planning-review PR off `squidsquad/planning/<NUMBER>` rather than a code-review PR off `squidsquad/task/<NUMBER>`. The same locked rule applies (`git_ops.py pr-create`, not bare `gh pr create`); only the body template differs. PM's `roles/pm/task-intake.md` owns the planning-PR body shape.

### PR merge — two lanes

Two roles can merge a PR; **PM never merges**, and worker never merges its own PRs. The PR moves through the lanes based on the status transition that opened the merge gate:

#### Lane A — Verifier auto-merge (on pending-test → pending-ship)

When the verifier transitions a task from `pending-test` to `pending-ship` (verifier authority per `tracker-protocol.md` legal-flow table), and the PR is eligible for auto-merge, the verifier triggers the merge:

1. Verifier confirms all ACs pass against the live PR.
2. Verifier checks the **eligibility gates** named in `references/sub-skills/roles/verifier/verification.md`: `config.py get auto-merge`, the absence of the `review:human-required` label, and (when applicable) PR Flow on/off.
3. **If eligible, the harness performs the merge.** The canonical flow is: verifier calls `gh pr ready <PR_NUMBER>` to flip the PR out of draft, then posts to the harness merge endpoint (`POST http://127.0.0.1:<harness-port>/merge` with `pr_number` / `branch` / `role`). The harness performs the squash-merge and emits a `pr-merged` event the verifier picks up on the next cycle. See `verification.md` for the exact `curl` invocation and the `pr-merged` event-handling branches.
4. **`git_ops.py pr-merge <PR_NUMBER> --strategy squash`** is the **non-harness fallback** — a thin `gh pr merge --squash` wrapper for direct CLI use when the harness is unreachable or when verifier is run outside a harness-managed session. It is NOT the path verifier exercises in normal operation. Bare `gh pr merge` is still non-canonical regardless of lane; use the wrapper.
5. Status transition to `pending-ship` follows successful merge (whether harness-mediated or CLI-fallback). DM then picks up `pending-ship` from the queue and runs the delivery flow.
6. If `review:human-required` is present OR `auto-merge` is off, verifier transitions to `pending-ship` (or `pending-human-review`) WITHOUT merging — the PR stays open for a human reviewer; DM observes the state but skips the merge until the human ready-merges or the verifier removes the label.

Full verifier-side procedure (eligibility gates, ship-comment shape, `pr-merged` event handling, rollback on merge conflict): see `references/sub-skills/roles/verifier/verification.md`.

This sub-skill is the **canonical interface lock** (which gates apply, which transitions follow which lane, squash strategy is universal); `verification.md` owns the **runtime mechanics** (which endpoint, which event, which curl shape). When the two disagree, the role-side file is the source of truth for the implementation — file a sub-skill update against this file via `→ run sub-skill: tracker-protocol` (improvement-scan finding) to bring this doc back in sync.

#### Lane B — DM ship-pending (on pending-ship → shipped)

When DM picks up a `pending-ship` item where the PR is **already merged** (Lane A landed it), DM's job is to package and ship — no merge happens here. DM transitions `pending-ship → shipped` via `tracker.py transition` (DM authority); this auto-closes the issue.

When DM picks up a `pending-ship` item where the PR is **not yet merged** (the `review:human-required` lane), DM waits — `pending-ship` is the holding state until the human resolves the review. DM does NOT force a merge; the issue stays in `pending-ship` until a human merges the PR, at which point DM picks up the post-merge ship work on the next cycle.

If the post-merge ship work surfaces a merge conflict at the planning-citation or version-bump step, DM rolls back via `tracker.py transition <NUMBER> pending-ship in-progress --role dm-lead` (allowed by the legal-flow table for merge-conflict rollback), comments the conflict, and routes back to the owning worker.

Full DM-side procedure (planning-citation guard, version-bump sequencing, CHANGELOG entry, post-ship statusline): see `references/sub-skills/roles/dm/delivery-packaging.md`.

#### PM observes — never merges

PM does NOT merge PRs. PM's `pipeline-sentinel` observes PR state every cycle (`gh pr list ... --json mergeable,state` plus tracker label state) and reconciles the two — if a PR merged but the tracker is still `pending-test`, PM nudges verifier with a tracker comment; if a tracker is `pending-ship` but the PR is closed-without-merge, PM files a routing issue. PM also flags orphaned PRs (no associated tracker issue) to the human.

PM is the only role that may convert a draft PR to ready as a metadata change (`gh pr ready <NUMBER>`) when the underlying tracker has already crossed the readiness gate — see `references/sub-skills/roles/pm/pipeline-sentinel.md` for the conditions.

PM never runs `git_ops.py pr-merge`. The pipeline-sentinel's role here is **observation + reconciliation**, not action.

### Merge strategy lock — squash

All PR merges land as squash-merges, regardless of which mechanism performs them. The harness merge endpoint squashes by default; `git_ops.py pr-merge` defaults to `--strategy squash`. Rationale: every merged PR collapses to one commit on the target branch, keeping `git log main --oneline` readable as a sequence of shipped tasks. Merge commits and rebase merges are explicitly avoided per the operator's standing "always merge, never rebase" rule applied at the *branch level* (we merge the branch via squash, never rebase its commits onto main).

For chain-merge task branches (e.g. polish-bundle siblings PR'd against `squidsquad/skill/compose-polish-session`), the same squash default applies — when the bundle eventually PRs against `main`, that bundle PR also squashes. The intermediate squash on the bundle branch does NOT lose history; the bundle PR description names every sibling PR by number.

### Conflict on the PR

When `gh pr view <NUMBER> --json mergeable` returns `CONFLICTING`, the owning worker resolves by **merging the base branch INTO the feature branch** (never rebase). This rule comes from the operator's standing "always merge, never rebase" instruction applied at the *commit level*:

```bash
git fetch origin
git checkout <FEATURE_BRANCH>
git merge origin/<BASE_BRANCH>       # NOT git rebase
# resolve conflicts, run tests
git push origin <FEATURE_BRANCH>
```

DM's "rebase onto main" Discussion comments are pipeline-drift from an older protocol and should be read as "merge main into branch." See the operator memory `feedback_always_merge_never_rebase` and the related `feedback_pm_loop_skill_clone_branch_race` rule on branch-state verification before any commit.

If the conflict is in a machine-regenerated transient file (composed CLAUDE.md, statusline state, working-state.md), fix the conflict at the `.gitattributes` layer (`merge=ours` or `merge=union`) rather than hand-merging the same file on every cycle. See `feedback_gitattributes_for_transient_state`.

### Quick reference — who runs which command

| Action | Role | Command |
|---|---|---|
| Open PR (code review) | owning worker | `git_ops.py pr-create "<title>" "<body>"` |
| Open PR (planning review) | PM | `git_ops.py pr-create "<title>" "<body>"` (planning shape, see `roles/pm/task-intake.md`) |
| Convert draft → ready | PM (metadata only) | `gh pr ready <NUMBER>` |
| Merge PR (no human-review, harness reachable) | verifier | `gh pr ready <NUMBER>` then `curl -X POST http://127.0.0.1:<harness-port>/merge` (canonical; see `verification.md`) |
| Merge PR (no human-review, harness fallback) | verifier | `git_ops.py pr-merge <NUMBER> --strategy squash` (CLI fallback only) |
| Merge PR (human-required) | human | manual via GitHub UI; DM observes the merge event |
| Resolve PR conflict | owning worker | `git merge origin/<BASE>` (NEVER rebase) |
| Close PR without merge | PM or DM | `gh pr close <NUMBER>` — only on operator instruction or DM rollback after route-back |

Bare `gh pr create`, `gh pr merge`, and `git rebase` do NOT appear in this table. They are non-canonical for SquidSquad agent flows.
<!-- /sub-skill: pr-protocol -->

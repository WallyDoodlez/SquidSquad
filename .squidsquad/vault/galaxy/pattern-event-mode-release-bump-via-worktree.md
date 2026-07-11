---
type: pattern
role: dm
created: 2026-06-30
tags: [dm, release, version-bump, worktree, event-mode, git]
owner: dm-lead
status: active
confidence: high
source: observation
links: [learning-bash-cd-into-missing-worktree-runs-in-main-clone, learning-ship-counter-canonical-key, learning-confirm-composed-currency-with-zero-diff-compose-not-behind-clone-grep, feedback_bump_requires_pm_signal]
---

# Execute a version-bump release via an isolated worktree at origin/main (event mode; behind/dirty clone)

The `version-bumps` sub-skill hands the mechanical commit/tag/push to `cycle_post.py` via `cycle-output.json` `version_bump`. **In event mode that wrapper does not fire for the agent**, and the DM clone is typically far-behind + dirty — so a direct push is the [[learning-bash-cd-into-missing-worktree-runs-in-main-clone]] / #13271 SEV-1 hazard. Do the bump **manually in an isolated worktree checked out at `origin/main`**.

## Recipe (proven on v0.45.0 / #13324, 2026-06-30)

1. `git fetch origin main`; `git worktree add --detach <wt-path> origin/main`. Verify `git -C <wt> rev-parse HEAD == origin/main`.
2. Edit IN THE WORKTREE (use absolute `D:/.../wt/...` paths — Read before Edit): `config.md` (`SquidSquad Version` X→Y, `Shipped Since Last Bump` →0), `SKILL.md` frontmatter `version:`, `CHANGELOG.md` (new section at top).
3. `git -C <wt> add <3 files>` → commit (`dm: #NNNN release vX.Y.Z — ...`, match repo commit style, no Claude trailer) → `git -C <wt> tag -a vX.Y.Z`.
4. **Re-check FF before push**: `git fetch origin main`. If `origin/main` advanced, **`git -C <wt> merge --no-edit origin/main`** (NEVER rebase; `--no-rebase` is a *pull*-only flag and errors on `git merge`). Then **delete + re-create the tag on the merge tip** so `vX.Y.Z` marks the actual main tip.
5. `git -C <wt> merge-base --is-ancestor origin/main HEAD` → push `HEAD:main` then the tag. Verify LIVE from facts (`git show <new-origin-sha>:config.md|SKILL.md|CHANGELOG.md`, `git ls-remote --tags origin vX.Y.Z`) — never trust push output alone.
6. `git worktree remove <wt> --force`. Then reset the **local** `.ship-counter` to 0 via `config.py set shipped-since-bump 0` ([[learning-ship-counter-canonical-key]] — `.ship-counter` is per-clone/untracked on origin/main; the committed reset is config.md's field).

## Gotchas

- **`.ship-counter` is NOT tracked on origin/main** (per-clone local). The release commit resets config.md's vestigial `Shipped Since Last Bump`; reset your own `.ship-counter` separately.
- **Config counter drifts** from the canonical `.ship-counter` (saw 50 vs 123). Author the CHANGELOG from the **forge-verified** shipped set (`gh issue list --label status:shipped --state closed --search "closed:>=<cutover-date>"`), not from either counter — and exclude items already in the prior version's CHANGELOG section.
- **Don't self-increment the counter for the release task itself** — the bump task (#13324) is the release action, not a post-release ship; counter stays 0 for the next batch.
- **CHANGELOG for a large batch (~120 items) is curated, not a dump** — highlights up top (operator-facing features + headline behavior changes) + an honest "~N further fixes" tail. Scannable beats exhaustive.
- The release is the operator's call: hold the bump until an explicit PM/operator green-light ([[feedback_bump_requires_pm_signal]]), even when the gate is technically open.
- If the release feeds a fresh foreign install, the end-to-end greenfield validation is a SEPARATE task (#12527) — confirm main is internally clean + entrypoints correct, but flag that you are NOT asserting a foreign install succeeds.

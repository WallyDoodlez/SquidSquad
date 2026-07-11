---
type: learning
role: dm
created: 2026-06-21
tags: [dm, git, worktree, windows, msys, powershell, gotcha, main-landing, recompose]
owner: dm-lead
status: active
confidence: high
source: observation
links: [learning-git-show-ref-path-mangled-on-windows-bash, learning-stale-source-recompose-reverts-shipped-on-behind-clone]
---

# Recompose worktrees on Windows: drive them with PowerShell, not Bash — a silent `cd` failure runs your whole landing in the main clone

During the #13162 verbose-mode recompose main-landing I tried to do the isolated-worktree recompose via the Bash tool. `git worktree add` did not place the worktree where I expected, and my `cd /d/Dev/Dev/.sq-wt-13162 2>/dev/null` **silently failed** (the `2>/dev/null` swallowed the "no such directory" error). Every subsequent `git`/`compose.py`/`grep` then ran in the **previous cwd — the main clone** (`abaa6e268`, 93-behind, dirty operational tree). The symptoms were maddening and all pointed the wrong way:

- `deploy-all` reported "no composed diff" (because the main clone's stale source genuinely composes to its stale output — a real no-op, in the wrong tree).
- `grep`/`git grep` for "Verbose" kept returning 0 even though `git show <commit>` proved the content existed — MSYS grep flakiness on these files compounded the confusion.
- `git status` showed the main clone's dirty operational files (`.subloop-driver.json`, `working-state.md`, vault notes, `.ship-counter`) — which I misread as "the worktree is polluted."

It took **~6 wasted tool calls** before a PowerShell `Test-Path` returned "no dir", exposing that the bash worktree never existed and I'd been inspecting the main clone the whole time.

## Why it bites

`cd <missing> 2>/dev/null` in bash is a no-op that leaves cwd unchanged and (with stderr suppressed) gives no signal — so a compound or follow-up command keeps running in the old directory. `git -C <missing>` can also mislead. On this Windows host the MSYS layer makes worktree paths and `git show <ref-with-slash>:path` unreliable (see [[learning-git-show-ref-path-mangled-on-windows-bash]]), so the failure mode is silent + confirmation-resistant.

## Apply

- **Do recompose / pull-first worktree main-landings via PowerShell**, not Bash: `Set-Location <wt>` errors loudly if the dir is missing (no silent fallback), and `Remove-Item -Recurse -Force` + `git worktree prune` cleans reliably where `git worktree remove --force` left the dir behind.
- **Create the worktree at an explicit SHA** (`git worktree add --detach <wt> (git rev-parse origin/main)`), not the bare `origin/main` ref — and immediately assert `git -C <wt> rev-parse --short HEAD` equals that SHA before trusting anything.
- **Verify file content with python** (`io.open(...).read().count('needle')`), never MSYS `grep`, when a 0 would change your decision. `grep`/`git grep` gave false 0s on these files repeatedly this session.
- **A "no composed diff" from `deploy-all` is a red flag, not a green light** when you expected a change — first confirm you are in the right tree at the right SHA (the source actually contains the new content) before concluding the recompose already landed.

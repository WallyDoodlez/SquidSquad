---
type: learning
role: dm
created: 2026-06-21
tags: [dm, git, windows, msys, gotcha, verification, main-landing]
owner: dm-lead
status: active
confidence: high
source: observation
links: [learning-stale-source-recompose-reverts-shipped-on-behind-clone, learning-ship-counter-canonical-key]
---

# On Windows/MSYS Bash, `git show origin/main:path` is mangled — use `git show HEAD:path` to verify committed content

When verifying composed-output / committed file content via the Bash tool on this Windows host, `git show origin/main:<path>` is silently corrupted by MSYS path-conversion: the `:` becomes `;` and the `/` in `origin/main` becomes `\`, so git receives `origin\main;<path>` and errors `fatal: ambiguous argument 'origin\main;...': unknown revision or path`. A piped `grep -c` then counts an **empty stream → 0**, which reads exactly like "the content is missing."

## Why it bites hard

During a #13035 template main-landing I ran `git show origin/main:.squidsquad/dm/CLAUDE.md | grep -c Relentless` and got **0 for all 4 roles** right after pushing the recompose. That looks identical to a [[learning-stale-source-recompose-reverts-shipped-on-behind-clone]] (#12895) fleet-wide revert — a genuine alarm. It was a **false alarm**: the ref was mangled, not the content. The `:` ref form with a slash in the revision is the trigger; `HEAD:path` (no slash) is unaffected, which is why `git show HEAD:path` worked in the same session.

## Apply

- **To verify content of a commit/ref**, prefer the slash-free form: `git show HEAD:<path>` (or a short SHA: `git show <sha>:<path>` — SHAs have no slash). Confirm the ref equals what you mean with `git rev-parse origin/main` / `git rev-parse HEAD` and compare — if `origin/main == HEAD`, `HEAD:<path>` IS origin/main's content.
- **A bare `<sha>:<path>`** (e.g. `git show 526a81238:.squidsquad/pm/CLAUDE.md`) is safe — no slash in the revision, so no mangling. That's how I confirmed the per-clone deploy-signal recompose state.
- **Never conclude "shipped content reverted/missing" from a single `git show <ref-with-slash>:path` returning 0** — check the command for a `fatal: ambiguous argument 'origin\main;...'` line first (it's the tell), then re-verify via `HEAD:`/SHA form before acting. A real #12895 revert must be confirmed by the slash-free path.

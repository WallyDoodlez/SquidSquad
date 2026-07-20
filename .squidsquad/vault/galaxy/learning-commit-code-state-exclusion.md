---
type: learning
tags: [git, workflow, gotcha, commit-code]
created: 2026-04-22
updated: 2026-07-20
owner: skill-lead
status: active
confidence: high
source: observation
links: []
---

# commit-code excludes .squidsquad/ — watch for code in state paths

## Context

`git_ops.py commit-code` splits changes into code (feature branch) and state (main). It classifies everything under `.squidsquad/` as state and excludes it from feature branches.

## Problem

Some files in `.squidsquad/` are actually code (e.g. `inject-permissions.sh`, `inject-permissions.ps1`, `statusline.sh`). These get excluded from feature branches, causing QA failures when the branch doesn't contain the expected changes.

## Workaround

When modifying `.squidsquad/` files that are code (not agent state), manually stage and commit them to the feature branch:

```bash
git checkout <branch>
git checkout main -- .squidsquad/<file>
git add .squidsquad/<file>
git commit -m "..."
```

## `.claude/` is filtered too — new-path deliverables can silently vanish (2026-07-20)

`commit_code` excludes `.claude/` alongside `.squidsquad/`. Building #13857 (a
Claude Skill package, whose natural runtime home IS `.claude/skills/`), the T2
"engine commit" landed containing ONLY the test file — all four engine files were
silently unstaged; caught only by `git show --stat` immediately after. Two rules:

1. **Committed source never lives under a filtered path.** Deliverables go under
   `references/` (the repo's source-of-truth layer); `.claude/` holds only the
   per-clone deployed copy, materialized at install time (#13857:
   `wizard.install_vault_engine`). This is the same source→live split as
   `statusline.sh`.
2. **Verify what landed whenever a commit introduces a NEW top-level path.**
   `git show --stat` after every `commit-code` touching unfamiliar paths — the
   guard prints a warning, but only above the fold of output nobody re-reads.

## Changelog

- 2026-04-22 — Created by skill-lead. Discovered during #2008 QA rejection.
- 2026-07-20 — skill-lead: `.claude/` filter + the #13857 vanished-deliverable incident; source-under-references rule + verify-what-landed rule.

Hub: [[pr-merge]]

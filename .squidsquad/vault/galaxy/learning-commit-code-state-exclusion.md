---
type: learning
tags: [git, workflow, gotcha, commit-code]
created: 2026-04-22
updated: 2026-04-22
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

## Changelog

- 2026-04-22 — Created by skill-lead. Discovered during #2008 QA rejection.

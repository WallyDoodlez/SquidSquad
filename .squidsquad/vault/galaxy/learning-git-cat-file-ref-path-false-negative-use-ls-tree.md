---
type: learning
tags: [git, windows, forensics, gotcha]
created: 2026-06-27
updated: 2026-06-27
owner: skill-lead
status: active
confidence: high
source: observation
links: []
---

# `git cat-file -e <ref>:<path>` gives FALSE NEGATIVES here — use `git ls-tree` / gh API to check file presence

## Context

Diagnosing whether files were deleted from `origin/main` (the #13263 behind-clone
data-loss investigation), I used `git cat-file -e origin/main:<path>` as an
existence check.

## Problem

`git cat-file -e origin/main:.squidsquad/.../FILE.md` reported the file **ABSENT**
for many files that were demonstrably **PRESENT** — confirmed by BOTH
`git ls-tree origin/main -- <path>` (showed the entry) AND the gh API
(`repos/.../contents/<path>?ref=main` returned full content) AND the file being on
disk with a clean working tree at that commit. `git rev-parse origin/main` matched
the true remote HEAD, so it was the SAME commit/tree — `cat-file -e <ref>:<path>`
was simply returning false negatives on this setup (Windows + this git/clone
state). This nearly produced a false "129 files lost / clone corrupted at scale"
alarm and burned significant budget.

## Lesson / how to apply

- To check whether a path exists at a ref, use **`git ls-tree <ref> -- <path>`**
  (reliable) or the **gh API contents endpoint** (independent, authoritative) —
  NOT `git cat-file -e <ref>:<path>`.
- When a presence/absence reading is **surprising or alarming**, cross-check with
  an independent source BEFORE concluding (the health-diagnosis "facts over
  context" rule). Here, ls-tree + gh API both contradicted cat-file and resolved a
  false alarm. A single git plumbing query can lie; the conclusion was wrong until
  cross-checked.
- A real deletion still shows up reliably as: `git checkout <commit> -- <file>`
  staging the file as an **addition** (proves it was absent from HEAD), and the
  deleting commit's own `git show --stat` listing the `D`. Those are trustworthy;
  `cat-file -e <ref>:<path>` is not (on this setup).

## Changelog

- 2026-06-27 — Created by skill-lead after a `cat-file -e`-driven false alarm
  during the #13263 / #12801 session.

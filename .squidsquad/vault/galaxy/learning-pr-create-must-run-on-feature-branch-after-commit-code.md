---
type: learning
tags: [git_ops, pr-create, commit-code, branch-workflow, worker]
created: 2026-07-19
updated: 2026-07-19
owner: skill
status: active
confidence: high
source: incident
links: [learning-task-begin-does-not-auto-create-pr-for-bugs]
---

## Context

`git_ops.py commit_code()` always ends by switching back to the working
branch (`main`), fast-forwarding it to origin (#13613) — deliberate and
load-bearing (a follow-on `commit_state()` call requires being on `main`).
`git_ops.py pr_create(title, body)` takes exactly two positional args and
creates the PR from **whatever branch is currently checked out** — it does
not take a branch argument and does not check out anything for you.

## Content

Hit this live while shipping #13731: called
`git_ops.py pr-create 13731 "<title>" "<body>"` (three args, mimicking the
`commit-code <role> <branch> <msg>` signature) immediately after
`commit-code`. Two compounding mistakes in one call:

1. `pr-create` only takes `<title> <body>` — the leading `13731` was consumed
   as the title, shifting the real title into the body slot.
2. `commit-code` had already switched back to `main`, so `gh pr create` ran
   with `head == base == main` and failed: `"must be on a branch named
   differently than \"main\""`.

Fix: re-`git checkout <feature-branch>` after `commit-code` returns (it always
leaves you on `main`), then call `pr-create` with exactly two args.

## Rationale

The two `git_ops.py` verbs read as siblings (`commit-code`, `pr-create`) but
have different signatures and different branch expectations — `commit-code`
is branch-aware and self-navigating (three positional args including branch);
`pr-create` is branch-agnostic and current-checkout-dependent (two positional
args, no branch arg). The natural habit of chaining them without an explicit
checkout in between is exactly what #13730 made visible via the new
"switched back to '<working>'" print — that print is the signal to checkout
the feature branch again before the next branch-scoped command.

## Related

[[learning-task-begin-does-not-auto-create-pr-for-bugs]] — same family of
"the PR isn't where you assume it is" gotchas in this workflow.

---

### Changelog

- 2026-07-19 — Created by skill after hitting this live shipping #13731.

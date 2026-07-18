---
type: learning
tags: [verifier, testing, gh-cli, graphql, pr-merge, environment, live-test]
created: 2026-07-18
updated: 2026-07-18
owner: verifier
status: active
confidence: high
source: observation
links: [learning-closing-keyword-in-state-commit-autocloses-issue]
---

## Context

Verifying #13654 (pr_merge() pre-merge closing-keyword neutralization via `gh
pr edit --body`), the mocked regression tests all passed — they only prove
the code *calls* `gh pr edit` correctly, not that the real binary accepts
the call. A live test (real disposable scratch PR, real unmocked function
call) caught what mocking couldn't: `gh pr edit` — ANY field, not just
`--body` — unconditionally fails in this repo's environment with
`GraphQL: Projects (classic) is being deprecated... (repository.pullRequest.projectCards)`.
`gh --version` here is `2.34.0` (2023-09-06), old enough to still query the
now-removed `projectCards` field on `repository.pullRequest`, which GitHub's
API now hard-errors on instead of just omitting. The fix's own fail-open
design meant this failure was silent (a stderr warning), so the mechanism
believed-working (green tests, green static gate) was actually a no-op
against real GitHub — reproducing the exact defect it was built to close.

## Content

**`gh pr edit` is broken in this environment — any future code that needs to
mutate a PR post-creation must route through `gh api -X PATCH
repos/<owner>/<repo>/pulls/<N> -f field=value` (REST) instead.** Confirmed
live: the REST PATCH endpoint succeeded immediately, against the same PR,
right after the `gh pr edit` call failed. `gh pr create` and `gh pr view` are
NOT affected — this is isolated to the `pr edit` subcommand's GraphQL
mutation, not gh CLI wholesale (issue `view`/`comment` etc. work fine via
`--json` flags; only the bare/legacy paths that still fetch `projectCards`
break).

**Why mocked tests couldn't catch this:** a test that patches
`git_ops._run_list` (or any subprocess wrapper) proves argument-construction
correctness, never real-tool compatibility. When new code's core mechanism is
"successfully call an external CLI/API," at least one live invocation against
the real tool is the only thing that proves the mechanism actually works —
this is a specific instance of the general AC-first-not-test-first principle
([[feedback_qa_verification_approach]]), applied to infra/tooling PRs, not
just feature PRs.

**Verifier action:** for any PR whose fix is "call `gh <subcommand>`
differently" or introduces a new `gh`/external-CLI call site, do not accept
green mocked tests as sufficient evidence the call itself works — construct
one real, disposable, safely-reversible live exercise (a scratch PR/branch
that gets closed/deleted after, never merged) that hits the actual call path.
If it's infeasible to safely exercise live (e.g. destructive or
irreversible), say so explicitly and route to a human decision rather than
trusting mocks.

## How to apply

Before approving any PR whose regression tests mock the `gh` CLI (or any
external tool) for a *new* call site: check whether the specific subcommand
used (`pr edit`, `pr merge`, `issue transfer`, etc.) has ever been exercised
for real in this repo's `gh` version. If not, do a scratch live test before
trusting the mocked coverage. `gh pr edit` specifically: use `gh api -X PATCH
repos/<owner>/<repo>/pulls/<N> -f body=...` instead in any new code.

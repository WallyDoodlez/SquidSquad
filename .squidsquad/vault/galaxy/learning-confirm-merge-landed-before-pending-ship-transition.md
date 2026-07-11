---
type: learning
tags: [verifier, ship-gate, pr-merge, draft-pr, transition-ordering, git_ops]
created: 2026-07-11
updated: 2026-07-11
owner: verifier
status: active
confidence: high
source: observation
links: [learning-verify-combined-state-when-branch-behind-main-shares-files, feedback_qa_transition_path]
---

## Context

Verifying #13338, I chained `git_ops.py pr-merge <pr>` and the `pending-test -> pending-ship` transition in one command. The merge FAILED — `ERROR: Pull Request is still a draft (mergePullRequest)` — but the transition still ran, leaving #13338 at `status:pending-ship` while its code was NOT on main. A transient pending-ship-without-landed-code inconsistency (a false "ready to ship" signal to DM). Recovered by `gh pr ready <pr>` + re-merge; the transition then became valid.

## Content

**Two disciplines for the merge→ship handoff:**

1. **Confirm the merge actually LANDED before the `pending-ship` transition — never chain them in one command.** Run `pr-merge`, read its result (`PR #<n> merged`), and ideally confirm the code is on `origin/main` (`gh pr view <n> --json state` = `MERGED`, or grep the change on `origin/main`), THEN transition. If the two are chained with `;`, a merge failure does not stop the transition — you ship-signal work that never landed. (The `feedback_qa_transition_path` pending-test→pending-ship path assumes the merge succeeded; make that assumption explicit by verifying it.)

2. **A PR handed to `pending-test` may be a DRAFT — and `gh ... --json mergeable` does NOT account for draft status.** On #13338, `gh pr view` reported `mergeable: MERGEABLE, mergeStateStatus: CLEAN` while the PR was still a draft, so the pre-merge mergeability check passed but the merge itself was refused. Before merging, also check `isDraft`; if true, `gh pr ready <pr>` to un-draft, then merge. (A draft PR reaching pending-test is a worker ship-discipline gap — flag it back — but the verifier still has to handle it to complete the ship.)

## How to apply

Ship sequence per verified item: (a) `gh pr view <n> --json isDraft,mergeable,mergeStateStatus` → if `isDraft`, `gh pr ready <n>`; (b) `git_ops.py pr-merge <n>` and READ the result; (c) confirm `state == MERGED` / change on `origin/main`; (d) ONLY THEN `tracker.py transition <n> pending-test pending-ship`. Steps (b) and (d) are separate calls — a failed (b) must block (d).

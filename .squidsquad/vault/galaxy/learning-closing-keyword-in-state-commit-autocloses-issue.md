---
name: learning-closing-keyword-in-state-commit-autocloses-issue
description: A GitHub closing keyword (Closes/Fixes/Resolves #N) in any commit landing on main auto-closes the issue — QA verdict commits that quote a PR's keyword must reword it.
metadata:
  type: learning
type: learning
tags: [git, github, tracker, qa, pending-ship, gotcha]
created: 2026-06-19
updated: 2026-07-11
owner: verifier
status: active
confidence: medium
source: observation
---

# Learning — A closing keyword in a commit to main auto-closes the issue

**Surfaced 2026-06-19 (cy345, #12825 verification).**

## What happened

While verifying #12825 (PASS → pending-ship), I committed the QA-state artifacts
(TEST-PLAN / QA-RESULTS / comprehension spec) to **main** with a commit message whose
body read: `Merge deferred to DM (PR #12860 Closes #12825).` Pushing that commit to the
default branch made GitHub's keyword auto-close fire on the literal phrase **`Closes #12825`**,
silently flipping the issue to CLOSED *before* my `pending-test → pending-ship` transition
even ran. The transition itself was innocent — `tracker.py` only auto-closes on `shipped`
(harness.py / tracker.py line 1326). The culprit was my own commit message.

## Why it matters

A closed pending-ship item is at risk of being missed: `tracker.py list-by-labels
"status:pending-ship"` and `gh issue list --state open` return only OPEN issues, so a
closed-but-labeled item does not surface in the default scan. DM could fail to ship it.
(`tracker.py`'s DM list flow *can* use `state: all` per #9837, but the common label scan
does not — don't rely on it.)

## The rule

**Never put a GitHub closing keyword — `close`/`closes`/`closed`, `fix`/`fixes`/`fixed`,
`resolve`/`resolves`/`resolved` followed by `#N` — in any commit message that lands on the
default branch (main), unless you actually intend to close issue N.** This applies to QA
state-commits especially, because verdict commits naturally *quote* the PR's closing keyword
("Merge deferred — PR has `Closes #N`"). Reword it: write `PR auto-closes on merge`,
`PR closing-keyword present`, or reference the number without the keyword verb
(`re: #N` / `for #N`), never the literal `Closes #N`.

## Recovery if it happens

`gh issue reopen <N>` immediately, confirm `state: OPEN` + the status label intact, and post
a one-line note on the issue so the close→reopen blip in the timeline doesn't mislead the next
agent. There may be a few seconds of GitHub search-index lag before the reopened item
reappears in label scans.

Related: [[feedback_qa_transition_path]] (the transition path itself is fine — this is a
commit-message hazard orthogonal to it).

## Update 2026-07-11 — #13371: PR bodies now code-guarded (and a meta-prose gotcha)

**#13371 (pending-test as of 2026-07-11)** adds a deterministic guard in
`git_ops.pr_create`: it neutralizes GitHub closing keywords in the **PR body**
(`Fixes/Closes/Resolves #N` → `Addresses #N`) before creating the PR, so a stray
keyword in a PR body can no longer auto-close the issue at squash-merge and bypass
the DM `pending-ship → shipped` gate. Once it merges, the long-standing "compose the
PR body WITHOUT `Fixes #N`" hand-discipline is **backstopped in code** for PR bodies.

**Two scopes still NOT covered by the pr_create guard — hand-discipline remains:**
- **Commit messages** (this note's original scope) — the guard only touches PR
  *bodies*, not commit messages. A closing keyword in a commit landing on main still
  auto-closes. Keep rewording verdict/state commits per the rule above.
- **Titles / non-gh paths** — the guard is body-only.

**New gotcha — the guard rewrites META-PROSE too.** `_neutralize_closing_keywords`
rewrites *any* closing-keyword+ref in the body, including prose that merely
*describes* an incident. On PR #13544 the body phrase `auto-closed #13335` rendered as
`auto-Addresses #13335` on GitHub — correct behavior (any keyword+ref is neutralized),
but it mangles descriptive text. When a PR/issue body needs to *talk about* a closing
keyword, break the pattern so the ref doesn't immediately follow the verb: write
`closed issue #N`, `` `Fixes`-style keyword targeting #N ``, or `#N (auto-closed)`.
And because `gh pr edit --body` is unreliable on this repo (GraphQL projects-classic),
get the body right the first time — you can't easily fix it post-create.

Related: [[feedback_stacked_pr_auto_close]] (the DM-squash auto-close mechanics this
guard protects), [[feedback_heredoc_timestamp_no_expand]] (sibling "get the text right
before it's committed, editing after is costly" class).
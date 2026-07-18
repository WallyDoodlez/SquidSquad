---
name: learning-closing-keyword-in-state-commit-autocloses-issue
description: A GitHub closing keyword (Closes/Fixes/Resolves #N) in any commit landing on main auto-closes the issue — QA verdict commits that quote a PR's keyword must reword it.
metadata:
  type: learning
type: learning
tags: [git, github, tracker, qa, pending-ship, gotcha]
created: 2026-06-19
updated: 2026-07-18
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

## Update 2026-07-18 — #13316: the #13371 guard only covers `git_ops.pr_create()`

**Confirmed live on PR #13626** (dm, delivering #13316): the PR body read
`Closes #13316` verbatim — unmangled — despite `_neutralize_closing_keywords`
being present and correct in `git_ops.py` (confirmed by reading the function).
GitHub auto-closed #13316 at merge, before DM's `pending-ship → shipped`
transition ran (issue sat CLOSED but still labeled `status:pending-ship` until
DM caught it and corrected via the normal transition — idempotent, no data
loss, just a forge-hygiene gap).

**Root cause**: the guard only wraps `pr_create()`'s body argument. This PR's
branch was forked from another in-flight branch (`squidsquad/task/13317`) to
avoid a stacked-PR conflict, and per the worker's own comment the PR was opened
through a non-standard path for that scenario (`gh pr create`/`gh pr edit`
directly, or an equivalent that never routes through `git_ops.pr_create`) — so
the neutralization never ran on this body.

**Practical implication**: `_neutralize_closing_keywords` is *not* a universal
backstop — any PR body set outside `git_ops.pr_create()` (manual `gh pr create`,
`gh pr edit --body`, stacked/forked-branch workarounds) is still exposed to the
original commit-message-style hazard. The hand-discipline rule above ("never
write a literal closing keyword + `#N`" in text that will land on GitHub)
still applies in full even with the guard live — don't rely on the guard alone
when a PR is created outside the normal `git_ops.pr_create` flow. DM's own
mitigation: don't trust `state: CLOSED` as proof of a proper ship — always
verify the status label actually reads `status:shipped` before treating an
item as delivered (a closed-but-still-`pending-ship`-labeled issue is the
tell).

## Update 2026-07-18 (later same day) — confirmed at scale: 12 stranded items, filed #13654

A fresh-boot DM idle sweep (same day as the #13316 incident above, separate session)
found this is not a one-off: `repair-status-labels --include-unshipped` turned up
**12** CLOSED-but-`status:pending-ship`-labeled issues (#13354, #13531, #13551,
#13552, #13558, #13589, #13592, #13593, #13602, #13611, #13613, #13652), and direct
PR-body inspection of three (#13630/#13636/#13653, for issues #13531/#13551/#13652)
confirmed literal unneutralized `Closes #N` text. None of the 12 ever reached DM —
no CHANGELOG, no ship-comment, no ship-counter increment. Filed **#13654** (role:skill,
severity:high) for skill to confirm/fix the actual EVENT-mode bypass path (this note's
"outside `pr_create()`" finding is the leading hypothesis, cited directly in #13654).

**DM remediation applied same-session** (mechanical, no code touched): stripped the
12 stale labels via `repair-status-labels --apply --include-unshipped`; reconciled
`.ship-counter` `58 → 70` (+12, one per escaped item, verified no overlap with prior
ship batches); treated all 12 as internal-only (no CHANGELOG warranted). **Takeaway
for future DM idle sweeps**: run `repair-status-labels --include-unshipped` (dry-run)
periodically even when `work_queue()` is empty — a closed issue never surfaces in the
normal `pending-ship` queue query, so this class of gap is invisible unless actively
swept for.

## Resolution 2026-07-18 — #13654 shipped: unbypassable merge-time guard + a `gh` version gotcha

**Actual root cause (simpler than either hypothesis above)**: skill's own admission —
every PR opened in the session that produced the 12 stranded items (#13624–#13653) used
bare `gh pr create` instead of `git_ops.py pr-create`. Not an EVENT-mode gap, not a
stacked-branch edge case — just the documented rule (pr-protocol.md) not being followed.
**A documented-but-unenforced rule is not a guard.**

**The fix moved the checkpoint to the one place that can't be skipped**: `pr_merge()`
now calls `_neutralize_pr_body_before_merge(pr_number)` — fetches the *live* PR body via
`gh pr view` and re-patches it immediately before the merge attempt, regardless of how
the PR was created or by whom. This is enforced at the merge point (`harness.py`'s
`POST /merge` → `git_ops.pr_merge()`), not at creation time, so it survives any
creation-path bypass.

**New gotcha surfaced by verifier's round-1 REJECT (live-reproduced, not theoretical)**:
`gh pr edit` — ANY field, not just `--body` — unconditionally fails in this repo's
environment with `GraphQL: Projects (classic) is being deprecated ... (repository.
pullRequest.projectCards)`. The installed `gh` is v2.34.0 (2023-09-06), old enough to
still query a now-removed GraphQL field. **Any future fix that edits a PR post-creation
must use `gh api -X PATCH repos/<owner>/<repo>/pulls/<N> -f body=<...>` (REST), never
`gh pr edit` (GraphQL)** — confirmed working live by both skill and verifier
independently against disposable scratch PRs. Mocked tests alone cannot catch this
class of failure (they proved the code *calls* `gh pr edit` correctly, not that the
real binary accepts the call) — verify environment-dependent `gh` behavior with a real,
unmocked, disposable-PR repro when a fix touches PR-body mutation.

Shipped via PR #13655 (2 verify rounds, zero gaps on round 2, static gate green both
rounds). The 12-item backlog and repair-status-labels remediation are documented in the
Update above; this section is the code-fix outcome.
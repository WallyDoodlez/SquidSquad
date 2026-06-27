---
name: learning-squash-drops-newest-commits-of-ahead-branch
description: a squash-merge can silently drop the NEWEST commits of an AHEAD branch (squash captured a stale intermediate commit) — distinct from the behind-branch mass-revert variant; the #13271 behind-count guard does not catch it; verify the merged squash == branch-TIP diff, and re-land lost commits verbatim from the branch tip
metadata:
  type: learning
type: learning
tags: [learning, verification, merge, squash, data-loss, incident, 13274, 13280, 13271]
created: 2026-06-27
updated: 2026-06-27
owner: skill
status: active
confidence: high
source: observation
---

# A squash-merge can silently drop the NEWEST commits of an ahead branch — verify the merged squash == branch-TIP diff

This is a **distinct variant** of the behind-clone squash data-loss class. The
sibling note [[learning-verify-squash-diff-additions-only-behind-branch]] covers
a *behind* branch whose stale tree **reverts** unrelated fleet work (mass loss).
This variant is the opposite shape and just as silent:

**The branch is correctly AHEAD of base, but the squash captured a stale
INTERMEDIATE commit — dropping the branch's newest commits.** PR #13274
(#12801 TUI re-land) squashed branch `squidsquad/task/12801` but the recorded
squash (86598a49f) contained only commit `b649dc5b9`, silently omitting the two
newest commits `ecf6ffb9a` (#13275 infra) and `03ab86ef8` (#13276 guard). The
feature's base landed; the follow-up fixes did not. The verifier had REJECTED
#13275/#13276 ("not on main") and was correct — and they were *still* absent
after the PR merged, because the squash never carried them.

**Why the #13271 behind-count merge guard does NOT catch it:** that guard
refuses a merge when the PR branch is >N **behind** base. Here the branch was
properly ahead — behind_by was fine — so the guard passed. The loss was in the
squash *tree selection*, not in the branch's base-distance.

**How to apply** (re-land + merge gate):
- After landing, **diff the merged result against the branch tip**, not just
  against base: `git diff <merge-result> <branch-tip> -- <feature paths>` must be
  empty. A non-empty diff of feature files means the squash dropped commits →
  re-land the missing pieces.
- When a verifier rejects a fix as "not on main" but you committed it, **check
  whether it shipped in a SIBLING PR's squash** before assuming the verifier is
  stale — the squash may have dropped your commit.
- Re-land lost commits **verbatim from the branch tip** (`git checkout
  <branch-tip> -- <files>`) onto a fresh branch off current main, re-run the full
  gate, ship a focused PR. Recovered cleanly this way as PR #13280.
- This is the third squash data-loss occurrence in the cluster — the durable fix
  is the recorded #13271 robust follow-up: a **post-merge scope-audit** that
  asserts the merged squash equals the branch-tip diff (mechanism-agnostic),
  catching both the behind-revert and ahead-drop variants.

Related: [[learning-verify-squash-diff-additions-only-behind-branch]].

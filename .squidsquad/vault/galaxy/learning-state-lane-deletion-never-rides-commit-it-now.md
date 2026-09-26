---
type: learning
tags: [git, state-lane, 11511-guard, deletions, task-end, verifier-reject]
created: 2026-07-20
updated: 2026-07-20
owner: skill
status: active
confidence: high
source: observation
links: [learning-background-verification-pipe-truncation-masks-verdict]
---

# A state-lane change never "rides the state lane" on assumption — verify it landed, or commit it deliberately

When the #11511 pre-commit guard unstages a state-lane path from a feature-branch commit, an **addition/modification** genuinely does get picked up later by the harness state commit on main. A **deletion** does not: the unstaged `D` entry is silently lost in the next `task-end` branch switch (checkout restores the tracked file or drops the deletion record), and nothing else ever re-deletes it. The file quietly survives on main while the branch's tests — run against the local tree where it WAS deleted on disk — pass, so the gap is invisible until a verifier checks main itself.

Cost when it bit (#14055 round-1 FAIL, 2026-07-20): claimed "the PM-planning stray deletion rides the state lane to main"; it never landed; the verifier's fresh `git ls-tree` on main caught it and bounced the item. Second same-day instance of the pattern (#13859's `.gitattributes` seed made the same assumption for an addition — which happens to work, making the deletion case a trap).

**Rule**: the moment a state-lane file must be *removed*, do it as its own direct-to-main commit (`git rm` + commit on main + push) right then — never leave it as an unstaged deletion, never assume any wrapper will carry it.

**Round-2 amendment (same day, #13859 verifier TC9)**: the "additions ride the state lane" half of the original claim ALSO failed — a new untracked file seeded under `vault/.telemetry/` was never swept by any state commit either; the verifier's `git log --all` found it in no tracked history while my clone-local copy made everything look fine. Full rule: **no state-lane change is ever assumed to land — either commit it deliberately (deletions and new files: direct-to-main, immediately) or verify with `git log --all -- <path>` that a wrapper actually carried it before claiming it shipped.** For repo-shipped config (like merge-attribute backstops), prefer the root tracked file over per-clone seeds — it rides normal clone/pull with no lane ambiguity at all.

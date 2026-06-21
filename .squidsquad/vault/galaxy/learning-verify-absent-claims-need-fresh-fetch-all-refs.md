---
type: learning
tags: [verification, qa, git, false-negative, stale-ref, planning-artifacts, 13147]
created: 2026-06-21
updated: 2026-06-21
owner: qa
status: active
confidence: high
source: observation
---

## What happened

Verifying #13147 (L1 Soul trait), I rejected on AC3 ("DS-audit artifact missing") after checking the feature branch, origin/squid-squad, and `git log --all` — all came back empty. The artifact (`.squidsquad/skill/planning/DS-REVIEW-13147.md`) actually existed on **origin/main** (commit 3d714ac00). My `origin/main` ref was **stale** — fetched once early in the session and never refreshed — so my "absent from all refs" check ran against a session-old main. The bounce was a false negative; skill had to re-submit to correct me.

## The rule

A "missing artifact / absent from all refs" rejection is a **strong, falsifiable claim**. Before asserting it:

1. `git fetch origin main` (and any other relevant ref) **fresh, immediately before the check** — never trust a ref fetched earlier in the session.
2. Remember **where each artifact class lives**: planning/state artifacts under `.squidsquad/*/planning/` (DS-REVIEW, working-state, audits) ride the worker's **cycle/state commits to main**, NOT the feature PR. A feature-branch-only `git ls-files` will not see them. Check main too.
3. Only then assert absence.

## Why it matters

A false-negative rejection costs a full worker cycle + re-verification and erodes trust in the gate. The zero-gap gate is only as good as the facts behind it — and "facts" means freshly-fetched refs, not a stale local view. This is the verification-lane corollary of [[feedback_qa_verification_approach]] (verify with current evidence) and Facts-Over-Context (cross-check, fetch fresh). Related: a genuine claimed-but-truly-absent artifact is still a valid finding — the rule is about *establishing absence correctly*, not about lowering the bar.

---
type: learning
tags: [documentation, architecture, audit, process, trd]
created: 2026-07-19
updated: 2026-07-19
status: active
owner: pm
---

# TRD v2 rewrites: cross-reference drift is the dominant defect class

Rewriting `docs/VAULT-ARCH.md` v1→v2 (#10003, 2026-07-18/19) produced **zero design contradictions but 10+ cross-reference defects**: dead §-refs from section renumbering (§9.5.1, §9.3.2), ambiguous refs after content moved between docs (bare "§9.4" meaning the planning doc's, colliding with the TRD's own §9.4), stale line anchors in doc-map tables (L150-167 pointing at content that moved), and a stale layer count copied from a superseded overview ("7-layer" vs the current six).

- **Why**: section numbers and line anchors are position-encoded references; a rewrite changes positions wholesale while prose survives copy-forward. Every carried-forward reference is guilty until re-verified.
- **How to apply**: (1) in doc-map tables, name sections, never line numbers — anchors rot silently; (2) when two docs both have a §N, always qualify which doc ("planning doc §9.4"); (3) budget a DS internal round + per-companion cross-pair rounds — the internal round catches renumbering, the cross-pairs catch stale claims about the *other* doc (which may itself have changed since the snapshot); (4) a fresh-context Claude final-pass catches a different class entirely (undefined contract inputs, ambiguous gate locations) that §-level auditing misses — both passes earn their cost.
- Audit artifacts: `.squidsquad/pm/planning/DS-AUDIT-10003-{r1,r2,xp1..xp4}.md`. Related: [[harness]]

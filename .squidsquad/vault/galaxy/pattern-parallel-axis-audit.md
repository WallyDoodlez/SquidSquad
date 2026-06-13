---
name: pattern-parallel-axis-audit
description: When verifying a large artifact (composed instructions, doc set, module surface), spawn N Sonnet subagents in parallel — one per orthogonal axis — with a fixed findings format and a single consolidation step
metadata:
  type: pattern
type: pattern
tags: [pattern, verification, code-review, subagents, audit-methodology]
created: 2026-06-11
updated: 2026-06-11
owner: skill
status: active
confidence: high
source: observation
links: [pattern-model-router-architecture, learning-strip-vs-wire-audit-findings, decision-vault-subagent-model-sonnet]
---

## Context

A polish session (#11331) needed to verify that 4 composed `.squidsquad/{pm,qa,dm,skill}/CLAUDE.md` files would actually drive the harness correctly at runtime. The artifact has three orthogonal coupling surfaces:

1. Composed CLAUDE.md prose ↔ harness.py + cycle wrappers (do the scripts the prose names exist with the expected shapes?)
2. Composed CLAUDE.md `→ run sub-skill: X` markers ↔ source resolution (do all marker names resolve via catalog to existing files?)
3. Runtime-Read sub-skill bodies ↔ harness/script implementation (do the sub-skills the agent loads at runtime agree with what the harness actually does?)

A single audit subagent told to "verify everything" would fan out shallowly across all three surfaces and miss depth on any of them. A sequential audit would consume hours of wall time.

## Pattern

For any large artifact whose correctness depends on multiple orthogonal couplings, run parallel-axis audits:

1. **Identify N orthogonal axes** — surfaces where the artifact could be wrong independently (composed↔harness, composed↔sub-skills, sub-skills↔harness in this case; could be code↔tests, API↔docs, schema↔consumers for other artifacts). Each axis has a different vocabulary and a different failure mode.

2. **Spawn one Sonnet subagent per axis, in parallel** — each with read-only access. Per the team's `decision-vault-subagent-model-sonnet`, Sonnet is the right cost/depth tradeoff for directed verification. Give each subagent:
   - The single artifact to verify
   - The specific axis it owns (with explicit out-of-scope reminders so it doesn't sprawl into adjacent axes)
   - A fixed findings format: `severity ∈ {BLOCKING, CRITICAL, MEDIUM, LOW, INFO}`, `file:line` citations mandatory, one-line summary at end
   - An output path to write findings to (so context stays out of the main thread)

3. **Wait for all N to complete in parallel** — typically 5-10 minutes per axis on Sonnet for a ~500-line artifact across ~20 files.

4. **Consolidate in a single pass** — main agent reads the 3 findings files, groups by severity, deduplicates overlaps, ranks by blast radius, and ships fixes in priority order (BLOCKING + CRITICAL first, then MEDIUM, then LOW). Write a consolidated REPORT.md so reviewers don't have to read N findings files.

5. **Ship fixes by severity in atomic commits** — one logical fix per commit. DS code review on any cross-cutting change (per the team's code-review pattern).

## Why this works

- **Parallel time-on-target on each axis** is deeper than serial — each subagent gets the full window of attention on one axis without context bleed from others.
- **Fixed findings format** makes consolidation mechanical — the main agent doesn't have to interpret each subagent's idiosyncratic structure.
- **`file:line` citation discipline** — forces subagents to ground every claim in evidence, not pattern-match against training data. Reviewer can verify any finding in seconds.
- **Read-only subagents** — no risk of one audit changing what the next sees. Verification is idempotent.

## When it surfaces real bugs

In the #11331 polish session this pattern surfaced 8 findings:

- 1 BLOCKING (sub-skill prose contradiction with two other sub-skills in the same boot bundle — caught by axis 3).
- 1 CRITICAL real production bug (`l4_file_watcher.py` events silently dropped due to `target_role` / `target_alias` field-name drift — caught by axis 1's cross-script analysis).
- 2 MEDIUM (one missing legal transition; one factually wrong prose claim).
- 3 LOW (post-Iter 56 lane-framing gap; ambiguous prose-only marker; catalog mis-description).
- 1 INFO (intentionally deferred deprecation).

Six CQ passes on the composed CLAUDE.md alone had missed all 8 because they tested composed prose for internal consistency, not against external scripts.

## Cost vs ad-hoc review

- ~30 min of wall time for 3 parallel audits (~10 min each).
- ~5 commits of fix work to clear all severities.
- ~$0.50-2 in subagent token cost depending on artifact size.

Compared to ad-hoc review by the main agent: lower cost (Sonnet is cheaper than the main worker's model), deeper per-axis coverage, durable artifacts that subsequent reviewers can re-validate.

## When NOT to use

- Small artifacts (< 100 lines) — the consolidation overhead exceeds the benefit; just audit inline.
- Artifacts with only one coupling axis — no parallelism gain; use a single subagent or audit inline.
- Time-sensitive bugfix where the audit-then-fix cadence loses to a direct hypothesis-test-fix loop.

## Changelog

- 2026-06-11 — Authored by skill agent. Drawn from #11331 polish session integration audit pass (Iters 58-64), where the pattern surfaced the `target_role` → `target_alias` field-name unification bug among 7 other findings. Published on 2026-06-11 alongside the polish-session PR (#11402).

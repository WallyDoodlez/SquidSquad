---
name: learning-audit-scope-and-source-of-truth
description: A section-scoped doc audit under-reports systemic drift, and a cross-doc delta can name the wrong side — verify a flagged premise doc-wide AND against code before scoping the fix
metadata:
  type: learning
type: learning
tags: [pm-judgment, prose-drift, ds-audit, doc-vs-code, harness]
created: 2026-06-14
updated: 2026-06-14
owner: pm
status: active
confidence: high
source: review
links: [learning-strip-vs-wire-audit-findings, feedback_minimal_repro_over_symptom_match, feedback_audit_pipeline]
---

# Audit scope and source of truth: verify a flagged premise doc-wide and against code

## Context

Cycle 2324 DS doc-vs-code audit of HARNESS-ARCH §14/§15/§16. Two ways the raw audit output would have misled if taken at face value:

1. **Scope under-report.** Pass 1 was scoped to §14 and flagged ONE line as a BLOCKER: §14 claims the harness spawns `event_poll.py` as a sibling. True — but the same false premise pervaded §3, §7.2 (step 4 + sequence diagram), §10 (`event_poll_pid` state field), and §11 (health_poll). The reality (`event_poll.py` is spawned by the agent's **Monitor tool** as a child of the `claude` session; harness tracks only `claude_pid`) contradicts ~6 sections, not one. A §14-only fix would have made the doc *more* internally inconsistent.

2. **Cross-doc delta pointed the wrong way.** Pass 2 flagged a HIGH: AGENT-RUNTIME says `.claude-pid` is read by health-poll; HARNESS-ARCH §7.3 says it is NOT. The cross-doc framing implied AGENT-RUNTIME was the offender. Reading `harness.py:update_health` settled it: the file IS read as a fallback (in-memory `claude_pid` → `.claude-pid` file → `health_check.py`). AGENT-RUNTIME was right; HARNESS-ARCH §7.3 (a sentence I had written earlier that session) was the wrong side.

## The lesson

A doc audit reports symptoms relative to its given scope. The scope and the cross-doc direction are inputs you chose, not ground truth.

- **A premise rarely lives in one section.** When an audit flags a claim in the audited section, grep that claim across the *whole* document before scoping the fix. Partial fixes to a load-bearing premise increase drift.
- **Code is the tiebreaker, not the cross-doc delta.** When two docs disagree, the delta tells you they disagree — not which is correct. Read the implementing code (the actual function, not the header comment) to decide which doc to change.
- **Your own recent edits are prime suspects.** The wrong side here was a sentence added earlier in the same session. Fresh edits that "tidied up" a mechanism are exactly where doc-vs-code drift gets introduced.

## How to apply

PM/skill when triaging any prose-drift or DS-audit finding:

1. For each flagged premise, grep it doc-wide; list every section that asserts it. Fix all or none — never partial-fix a premise.
2. For cross-doc contradictions, open the implementing symbol and decide from code; treat the audit's framing of "which doc is wrong" as a hypothesis.
3. If the doc-wide fix is systemic (spans diagrams / schema / multiple sections), surface it for one coherent reconciliation pass (work-discovery / doc-first) rather than sweeping it inline mid-cycle. Fix only the genuinely self-contained items inline.

## Changelog

- 2026-06-14 — Created by pm-lead. Lesson from cycle 2324 DS audit of HARNESS-ARCH §14/§15/§16.

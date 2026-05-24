---
name: learning-scan-comment-vs-file-duplicate
description: When an improvement scan surfaces another instance of an already-filed defect family, post an audit comment on the existing issue with concrete call-sites rather than filing a parallel duplicate — produces a more actionable fix and keeps the queue clean
metadata:
  type: learning
type: learning
tags: [improvement-scan, triage-hygiene, audit-response, methodology]
created: 2026-05-24
updated: 2026-05-24
owner: skill
status: active
confidence: medium
source: cycle-1361-reflection
links: [learning-strip-vs-wire-audit-findings, decision-improvement-loop-philosophy]
---

# Audit-extend an existing issue rather than file a duplicate when the defect family is already tracked

## Context

Cycles 1357-1360 each filed one improvement-scan issue: #10002 (cycle_post version-bump silent push), #10005 (diagnostics redaction asymmetry), #10006 (cli aggregation exit), #10007 (vault_remember non-atomic working-state.md writes). All four sat in the PM triage queue unactioned. Cycle 1361 scanned soul_adaptation.py and found the same non-atomic `.write_text` pattern as #10007 (L147 and L226).

Two options at that moment:
1. File #10008 for soul_adaptation.py with similar body to #10007
2. Run a codebase-wide grep audit and post a comment on #10007 listing every call-site

Option 1 would have added a fifth open scan finding for PM to triage, with the same recommendation as #10007 ("extract a shared atomic_write_text helper"). Option 2 produced a single audit table with 9 call-sites across 6 files (working-state.md, SOUL.md, role-adaptations.md, config.md, SKILL.md, diagnostic.jsonl writers) — making the fix PR concretely scoped.

I chose option 2. The smoking gun that landed in the comment: `config.py:285` (wrong, direct `write_text`) lives in the same file as `config.py:406` (right, `tmp.write_text + tmp.replace`). The pattern is known to the codebase but inconsistently applied — exactly the evidence a fix PR needs to justify a sweep.

## The lesson

A scan finding that's an *instance* of an already-filed pattern is not a separate bug. It's audit data for the existing issue. Filing a parallel duplicate:

- Splits the conversation across two issues (PM has to cross-reference)
- Splits the fix across two PRs (or one PR closes both with awkward issue-link soup)
- Inflates the queue depth, which is the only signal PM has for triage urgency
- Hides the systemic nature of the finding — a single issue with 9 call-sites is obviously systemic; nine issues with one call-site each look like nine isolated bugs

Audit-extending the existing issue:

- Keeps one conversation, one fix scope
- Forces you to grep the codebase for the full call-site list — which is what the fix PR needs anyway
- Makes the systemic pattern visible in a single place (a table beats nine separate issue bodies)
- Strengthens the original recommendation by adding evidence of breadth

## When this pattern applies

Any scan finding where the issue body would substantially repeat an already-filed issue: same defect family, same recommendation, same fix shape. Markers to watch for:

- "Same defect family as #NNNN" appears in your draft body
- Recommendation section reads "extract a shared helper" or "apply [pattern from #X] here too"
- The fix in your draft would touch fewer than 5 lines, mostly mechanical

If those are present, stop drafting the new issue. Open the related issue and post a comment with:

1. A markdown table of *all* call-sites (file:line, target, what it writes, concurrent readers)
2. A grep command or methodology that produced the table (so the fixer can reproduce / verify completeness)
3. A smoking-gun example — within-file inconsistency, paired correct/wrong sites, or a documented-but-unenforced pattern
4. The fix shape, concrete enough to copy into a PR (function signature, where to define it)

## When this pattern does NOT apply

- The new finding is the same family but a *materially harder* fix (e.g. requires schema migration, breaking API change). File separately; cross-link to the family ancestor.
- The original issue is closed or stale (>90 days, no activity). File fresh; reference the closed predecessor.
- The defect family hasn't been characterized as a family yet — the first two findings need to be separate issues so PM can spot the pattern. Only audit-extend on the third instance and beyond.
- Different role owns the fix. File against the right role's tracker even if the symptom looks similar.

## How to apply

Before filing any improvement-scan issue:

1. `gh issue list --label "improvement-scan" --state all --search "<keyword>"` for related prior findings
2. Read the bodies — does my finding fit one of them?
3. If yes: write an audit comment on that issue. Do not file a new one.
4. If no: file fresh, and add a `Same family as #NNNN` line in the body so future scans can find it.

Skill role's cycle 1361 took the audit path; cycle output records it as a deliberate choice rather than a missed scan. Scan-history.md notes "no new issue filed — instead, posted an audit comment on #10007" so future agents can see the methodology produced a working outcome.

## Changelog

- 2026-05-24 — Created by skill-lead. Lesson from cycle 1361 audit of #10007's defect family across the codebase. [[learning-strip-vs-wire-audit-findings]] covers the strip-vs-wire dimension of audit response; this note covers the duplicate-vs-extend dimension.

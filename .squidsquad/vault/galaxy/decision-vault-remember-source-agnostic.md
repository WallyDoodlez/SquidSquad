---
type: decision
tags: [vault, feedback, reflection, design]
created: 2026-04-26
updated: 2026-04-26
owner: skill
status: active
confidence: high
source: conversation
links: [human-profile]
---

## Context

Human directed that the vault remember reflection step should not filter by signal source. The existing design gates "HUMAN PREFERENCES" on human interaction only, meaning QA rejections, PM direction, and agent observations are excluded from preference capture.

## Content

Vault remember reflection categories must be **source-agnostic**. Any signal — human feedback, QA rejection, PM direction, agent observation, code review finding — should be evaluated across ALL five reflection categories (decisions, patterns, learnings, preferences, project context). The source of the signal does not determine which buckets get evaluated.

Current state: category 4 asks "Did the *human* express a preference?" — should be "Was any preference expressed this cycle, by anyone?"

Affected artifacts:
- `references/sub-skills/common/vault-remember.md` — reflection prompt wording
- Potentially `areas/human-profile.md` → may need restructuring since preferences aren't human-exclusive

## Rationale

A QA rejection saying "don't mock the database" is simultaneously a preference, a decision, a pattern, and a learning. Gating by source causes the system to miss cross-cutting knowledge. The vault should capture institutional knowledge regardless of who contributed it.

## Related

- [[human-profile]]

---

### Changelog

- 2026-04-26 — Created by skill. Human directed source-agnostic reflection for vault remember.

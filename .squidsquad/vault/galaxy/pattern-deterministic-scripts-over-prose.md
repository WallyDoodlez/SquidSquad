---
type: pattern
tags: [pattern, reliability, agent-behavior, deterministic]
created: 2026-04-13
updated: 2026-04-13
owner: skill
status: active
confidence: high
source: observation
links: [decision-sub-skill-architecture]
---

## Context

Agent CLAUDE.md instructions describe complex multi-step behaviors in prose (e.g., "check comments for QA feedback after your last comment"). Agents frequently skip or misinterpret these steps, causing behavioral drift — tasks sit idle for hours until a human nudges.

## Content

When agent behavior depends on parsing structured data (comments, labels, file timestamps, health states), replace the prose instructions with a deterministic Python script that the agent calls. The agent gets structured output (JSON) and acts on it, rather than implementing the parsing logic from prose.

**Established instances:**
- `health_check.py` (#335) — replaced prose-based agent health detection
- `triage.py` (#470) — replaced prose-based QA-rejected comment scanning
- `capability_check.py` (#401) — replaced prose-based capability verification

**When to apply:** Any time agent instructions say "check X, parse Y, compare Z" where X/Y/Z are structured data. If the logic has more than 2 conditional branches, it belongs in a script.

**When NOT to apply:** Simple one-step checks (e.g., "if file exists") are fine as prose.

## Related

- [[decision-sub-skill-architecture]]

---

### Changelog

- 2026-04-13 — Created by skill agent. Pattern observed across #335, #470, #401.

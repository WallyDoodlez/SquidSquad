---
type: decision
tags: [qa, testing, deterministic, verification, pm, test-plan]
created: 2026-04-18
updated: 2026-04-18
owner: pm
status: active
confidence: high
source: conversation
links: [decision-self-healing-sentinel, human-profile]
---

## Context

Human discovered QA shipped #1291 twice with 14 test cases "deferred" — including comparison tests the human explicitly requested. QA used subjective verification ("zero gaps structural") while skipping live API tests. Human declared this unacceptable.

## Content

**Testing must be deterministic, not subjective.** Two changes:

1. **PM test plans**: Every TC must be constructable as an executable test by a Claude agent. Concrete assertions, not vague quality criteria. If a TC requires human judgment, mark it `human-verification` explicitly. Best effort — write the most deterministic version possible.

2. **QA verification**: Must write and run actual pytest tests for every TC. No more prose-based "PASS." Valid TC results are PASS, FAIL, or BLOCKED (with a filed blocker issue). "Deferred" is not a valid result. BLOCKED TCs prevent pending-ship — the blocker must be resolved first.

## Rationale

Human's quality bar: if QA says it passes, there must be executable proof. Subjective verification creates a loophole where TCs can be deferred or hand-waved. The #1291 incident (shipped 3 times, comparison tests never ran) is the motivating case. This compounds with the self-healing philosophy — deterministic tests catch regressions automatically.

## Validation

First real-world result: QA ran 16 live integration tests for #1291. All failed — caught a real API incompatibility (GPT 5.2 requires `max_completion_tokens`, adapter was sending `max_tokens`). Under the old subjective approach, QA deferred these tests twice and shipped anyway. Under deterministic testing, the bug was caught immediately.

## Related

- [[human-profile]]
- [[decision-self-healing-sentinel]]

---

### Changelog

- 2026-04-18 — Created by pm. Human-directed decision after #1291 QA failure (deferred TCs shipped as "zero gaps").
- 2026-04-18 — Updated by pm. Added Validation: deterministic tests caught real max_tokens bug in #1291 on first run.

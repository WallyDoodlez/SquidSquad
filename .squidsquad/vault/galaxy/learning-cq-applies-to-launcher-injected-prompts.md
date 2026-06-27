---
type: learning
tags: [verification, comprehension-testing, cq, llm-consumed-instructions, thin-launcher]
created: 2026-06-12
updated: 2026-06-12
owner: verifier
status: active
confidence: high
source: verification
links: [learning-spawn-prompt-must-not-decide-wake-mode]
---

## Context

Verifying #11512 (mode-neutral spawn prompt). The fix lives in `thin_launcher.py` — a Python file. The implementing agent assessed comprehension testing (CQ) as **N/A** on the grounds that "the change is a deterministic launcher constant, not composed agent instructions." On verification this was the wrong boundary call.

## Content

**The comprehension-testing trigger is "is this string consumed by an LLM as instruction?" — NOT "does this string live in a composed CLAUDE.md / sub-skill file?"** A launcher-injected first-turn prompt (`thin_launcher._SPAWN_PROMPT`) is the agent's literal first instruction every spawn — it is unambiguously LLM-consumed, even though it is authored as a Python constant in a `.py` file and never flows through `compose.py`.

Verification action: treat any of these as CQ-eligible regardless of file type —
- launcher / harness / boot-script string constants that become an agent's prompt input,
- spawn prompts, system-prompt fragments, injected first-turn directives,
- anything an agent reads-and-acts-on whose meaning could drift.

For #11512 the CQ was cheap and high-value (the entire fix rests on the agent reading the prompt and probing-first): a fresh sonnet agent given only `_SPAWN_PROMPT` + the boot Step 1 excerpt answered 5/5 correctly. Spec preserved at `tests/comprehension/11512_spec.json`.

## Rationale

The "composed CLAUDE.md only" reading of the CQ standard under-covers: it lets behavioral instructions ride in non-template files (Python constants, JSON configs, harness payloads) without comprehension verification. The standard's intent is to gate on **LLM-consumed instructions** (#9184) — file location is incidental. When in doubt, run the CQ; it is cheap relative to a misrouted-boot class of bug.

## Related

- [[learning-spawn-prompt-must-not-decide-wake-mode]] (the fix-side learning; this is the verification-side complement)
- #11512 (origin), #9184 (comprehension-testing workflow)

---

### Changelog

- 2026-06-12 — Created by verifier (cycle 644). CQ applies to launcher-injected/LLM-consumed prompts regardless of file type; don't scope CQ to composed CLAUDE.md alone.

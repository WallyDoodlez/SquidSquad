I've completed a thorough review of the two hunks in `docs/COMPOSE-ARCHITECTURE.md`. Here is my analysis against all four acceptance criteria:

**AC1** (line 418): The §4 overview prose now states CLAUDE.linked.md is "for audit and debugging only — runtime agents never read it, and per-slot subagent failures do not fall back to the linked file at runtime. Per-slot fallback semantics are defined in §4.6 (failure modes table); the runtime always reads the assembled CLAUDE.md." ✓ — No longer claims CLAUDE.linked.md is a runtime fallback; correctly defers to §4.6.

**AC2** (lines 486-503): The §4.4 mermaid now has two distinct failure paths:
- `LLM -->|"per-slot soft failure (timeout / refusal / JSON parse / AC6 after retry / per-slot preservation drop)"| Verbatim` → `WriteAtomic` → `Done` (compose succeeds)
- `AsmValidate -->|"structural violation"| AbortAsm` → "no triple written" (compose aborts)

✓ — Correctly distinguishes per-slot soft failures from structural contract violations.

**AC3**: The changed content is confined to line 418 (one sentence in §4 overview) and lines 486-503 (the §4.4 mermaid diagram body). §4.5 (lines 510-567) and §4.6 (lines 568+) prose appears unmodified. ✓

**AC4**: The mermaid's per-slot soft failure list (timeout / refusal / JSON parse / AC6 after retry / per-slot preservation drop) maps directly to §4.6 table rows 731-735. Its structural-violation checks (sub-skill ref set ≡, step ID set ≡, length ≥ floor, code-block parity) map to §4.6 post-pass validation checks (lines 702-709) and table rows 737-740. Both paths have the correct terminal states: per-slot → atomic write succeeds; structural → abort, no triple written. ✓

NO_FINDINGS
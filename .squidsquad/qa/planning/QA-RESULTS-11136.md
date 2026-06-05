# QA-RESULTS-11136 — COMPOSE-ARCH §4 + §4.4 cross-section consistency (#11089 follow-up)

**Verified at**: 2026-06-05 cycle 941
**Commit on main**: `70575c6f4`.
**Artifact**: `.squidsquad/pm/planning/DS-AUDIT-11136.md` (PM's audit report — NO_FINDINGS).

## AC walk

- **AC1 — §4 overview line 418 rewritten** — PASS. Reads: "The **linked** output is preserved as a sibling artifact (`.squidsquad/<alias>/CLAUDE.linked.md`) for audit and debugging only — runtime agents never read it, and per-slot subagent failures do not fall back to the linked file at runtime. Per-slot fallback semantics are defined in §4.6 (failure modes table); the runtime always reads the assembled `CLAUDE.md`." Old "fallback when the assemble pass fails" wording is gone.
- **AC2 — §4.4 mermaid has two distinct failure paths** — PASS. Confirmed in `docs/COMPOSE-ARCHITECTURE.md`:
  - Per-slot soft failure (line 491): `LLM -->|"per-slot soft failure (timeout / refusal / JSON parse / AC6 after retry / per-slot preservation drop)"| Verbatim` → `WriteAtomic` → `Done`. Compose succeeds.
  - Structural violation (line 493): `AsmValidate -->|"structural violation"| AbortAsm([Abort whole compose with diagnostic — no triple written])`. Compose fails cleanly.
- **AC3 — diff scope (single commit, two hunks @ §4 / §4.4 only)** — PASS. `git log --oneline docs/COMPOSE-ARCHITECTURE.md` shows `70575c6f4` as the sole commit for this issue's scope; §4.5 / §4.6 untouched by it.
- **AC4 — cross-section consistency between §4.4 and §4.6** — PASS. The mermaid's per-slot soft list at line 491 maps to §4.6 failure-modes table rows 731-735; the structural list maps to §4.6 post-pass validation lines 702-709 + table rows 737-740.

Doc-only change; no test sweep required. PM's DS audit (`.squidsquad/pm/planning/DS-AUDIT-11136.md`) reported NO_FINDINGS; my independent observable re-check matches.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Cross-section drift between §4 overview / §4.4 mermaid and the post-#11089 §4.6 is now closed. No follow-up issues needed.

# docs/archive/

Superseded architecture docs, kept for traceability rather than active reference.

## Contents

| File | What it was | Superseded by |
|---|---|---|
| `EVENT-ARCHITECTURE.md` | v2 nudge-driven design (rev 5 lock-ready, the comprehensive new architecture) | [`../AGENT-RUNTIME.md`](../AGENT-RUNTIME.md) |
| `EVENT-BUS-ARCHITECTURE.md` | v1 additive observability bus (PRD-style reference) | [`../AGENT-RUNTIME.md`](../AGENT-RUNTIME.md) §4 |
| `event-bus.md` | v1 additive observability bus (narrative form) | [`../AGENT-RUNTIME.md`](../AGENT-RUNTIME.md) §4 |

The three above were consolidated into [`../AGENT-RUNTIME.md`](../AGENT-RUNTIME.md) on 2026-05-23 over a 5-round DeepSeek review loop (rev 5 = "CONVERGED"). The consolidated doc reframes the architecture around "loop mode vs event-driven mode" — how an agent's operating model is defined.

## Why archived instead of deleted

- §-level traceability for the consolidated doc's rev-log (rev 1 cites these by name; rev 4 cites `§13 question lock table` from `EVENT-ARCHITECTURE.md`).
- The two v1 bus docs document the larger 20-event catalog that loop mode still uses today; v2 trims this to 4 entries.
- DeepSeek-audited content; useful as a known-good baseline against future drift.

If the consolidated doc has fully replaced all references and stayed stable for a meaningful period, these can be deleted in a follow-up cleanup.

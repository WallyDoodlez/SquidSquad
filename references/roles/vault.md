---
slot: vault
ordinal: 10
---

## Vault

The vault (`.squidsquad/vault/`) is the squad's shared institutional memory — decisions, patterns, learnings, and human preferences that outlive any single cycle or session. All agents read the vault; write access is gated by sub-skill protocol.

### BRIEFING.md

Read `.squidsquad/vault/BRIEFING.md` at boot. It contains active project priorities, recent decisions, and team state. Re-read if more than one cycle has passed since last read.

### PARAG Structure

The vault uses the **PARAG** taxonomy plus a `systems/` hub layer; the type registry `vault/vault-schema.json` is authoritative:

| Bucket | Path | Contents |
|--------|------|----------|
| Projects | `vault/projects/` | Bounded, scoped work with a definition-of-done |
| Areas | `vault/areas/` | Ongoing concerns — human prefs, conventions, team culture |
| Resources | `vault/resources/` | Reference material, external docs, research |
| Systems | `vault/systems/` | One hub note per subsystem — galaxy notes link into these |
| Archives | `vault/archives/` | Legacy location — notes now retire by `status`, not by moving |
| Galaxy | `vault/galaxy/` | Atomic Zettelkasten notes: `decision-*`, `pattern-*`, `learning-*`, `rule-*` (binding rules) |

### Vault Protocol

→ run sub-skill: vault-protocol

Search the vault only through the engine (`vault_consume.py search`) — never grep it. Consultation at task pickup is mandatory and leaves committed receipts (`## Vault context consumed`, `## Applicable rules`) in the issue's lineage file, which the verifier checks. After completing real work, use vault-remember to capture durable learnings. The vault is shared institutional knowledge for the whole team — every role contributes patterns and learnings from its own lane (PM: coordination/decision patterns; worker: implementation patterns; verifier: testing/verification patterns; DM: delivery patterns). Max 2 writes per cycle; apply 4-gate logic (write budget → dedup → reusability → fresh-context test).

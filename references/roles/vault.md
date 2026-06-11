---
slot: vault
ordinal: 10
---

## Vault

The vault (`.squidsquad/vault/`) is the squad's shared institutional memory — decisions, patterns, learnings, and human preferences that outlive any single cycle or session. All agents read the vault; write access is gated by sub-skill protocol.

### BRIEFING.md

Read `.squidsquad/vault/BRIEFING.md` at boot. It contains active project priorities, recent decisions, and team state. Re-read if more than one cycle has passed since last read.

### PARAG Structure

The vault uses the **PARAG** taxonomy:

| Bucket | Path | Contents |
|--------|------|----------|
| Projects | `vault/projects/` | Bounded, scoped work with a definition-of-done |
| Areas | `vault/areas/` | Ongoing concerns — human prefs, conventions, team culture |
| Resources | `vault/resources/` | Reference material, external docs, research |
| Archives | `vault/archives/` | Shipped features, closed decisions, historical context |
| Galaxy | `vault/galaxy/` | Atomic Zettelkasten notes: `decision-*`, `pattern-*`, `learning-*`, `style-*` |

### Vault Protocol

→ run sub-skill: vault-protocol

Before starting a task, consult relevant vault notes. After completing real work, use vault-remember to capture durable learnings — *unless your role is configured read-only* (verifier is read-only by default; PM/worker/DM may write per their project-adaptation). When writing: max 2 writes per cycle; apply 4-gate logic (write budget → dedup → reusability → fresh-context test).

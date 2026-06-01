---
slot: instructions
ordinal: 10
---

## Consensus Protocol

Rules for driving multi-party discussions to locked decisions in chat. Used for vault writes, architectural choices, and cross-agent disagreements.

### When Consensus Is Required

- **Vault writes**: Before writing a decision, pattern, or learning to the vault, open a `[decision]` thread. At least PM must agree.
- **Architectural changes**: Changes that affect multiple agents or the project structure.
- **Cross-agent disagreements**: When two agents disagree on approach, PM mediates.
- **NOT required for**: Bug fixes with clear root cause, routine task implementation within acceptance criteria, status updates.

### Decision Flow

1. **Proposer** opens a `[decision]` thread with the proposal:
   ```
   **skill-lead**: [decision] Vault write — new pattern: source-agnostic reflection
   Proposal: [description]. Affects: [scope]. Recommend: [action].
   ```

2. **PM** is auto-included in all decision threads. PM acknowledges within 1 cycle.

3. **Participants** state their position:
   - `AGREE: [brief reason]`
   - `DISAGREE: [brief reason + alternative]`
   - `ABSTAIN: [reason]`

4. **PM summarizes** once all participants have responded (or timeout):
   ```
   **pm-lead**: Summary: 2 AGREE, 0 DISAGREE. Decision: [action]. Locking.
   ```

5. **Lock**: PM posts `DECISION LOCKED: [one-line summary]`. No further discussion.

### Timeout

- Participants have **2 cycles** (default: 60 minutes) to respond.
- If no response after timeout, their position is treated as `ABSTAIN`.
- If PM does not respond after 2 cycles, the proposer may escalate to human.

### Quorum

- Minimum: **PM + proposer** (2 agents).
- Human participation is optional unless an agent explicitly escalates.
- Human response overrides all agent positions — human always has final authority.

### Recording Decisions

- PM posts the locked decision as a GitHub Issue comment on the relevant issue for audit trail.
- If the decision is vault-worthy, the proposer writes the vault note after PM locks.
- Thread ID is referenced in the vault note's changelog.

### Adapter Usage

```python
from comms_adapter import get_adapter
adapter = get_adapter()

# Open decision thread
tid = adapter.create_thread("general", "[decision] Vault: source-agnostic reflection", thread_type="decision", sender="skill-lead")
adapter.send_message("general", "**skill-lead**: Proposal: vault-remember should evaluate all 5 categories regardless of signal source. Affects: vault-remember sub-skill. Recommend: update reflection prompt.", thread_id=tid, sender="skill-lead")

# PM responds
adapter.send_message("general", "**pm-lead**: AGREE: Aligns with human directive from 2026-04-26.", thread_id=tid, sender="pm-lead")

# PM locks
adapter.send_message("general", "**pm-lead**: DECISION LOCKED: Vault reflection is source-agnostic. All 5 categories evaluated for every signal.", thread_id=tid, sender="pm-lead")
```

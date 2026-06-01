---
slot: instructions
ordinal: 10
---

## Mention Protocol

Rules for when and how to @mention humans and agents in chat. Controls notification noise.

### Escalation Tiers

1. **Inform** (no mention): Status updates, routine progress, FYI posts. No notification sent.
2. **Need-input** (@mention): You need a specific answer to continue. Mention the target role.
3. **Blocking** (@mention + `BLOCKING`): Work is stopped until this person responds. Include `BLOCKING:` prefix.

Format:
- Tier 1: `**skill-lead**: #3417 complete. Tests green.`
- Tier 2: `**skill-lead**: @pm-lead Acceptance criteria unclear on #3417 — does "composable" mean auto-included or opt-in?`
- Tier 3: `**skill-lead**: BLOCKING: @human Design decision needed on consensus timeout — 5min or 15min? Cannot proceed.`

### When to @mention Human

**Do mention**:
- Blocking decisions that no agent has authority over
- Errors that affect billing or external services (quota exceeded, API failures)
- Security findings (hardcoded secrets, injection risks)
- Disagreements between agents that PM cannot resolve

**Do NOT mention**:
- Routine status updates (use tier 1)
- Agent-to-agent questions (mention the agent, not human)
- Issues that PM can resolve within their authority
- Test failures (fix them, don't escalate)

### Noise Budget

- Maximum **3 human mentions per hour** across all agents combined.
- PM tracks the budget. Before mentioning human, check with PM: `@pm-lead May I escalate to human? [reason]`
- PM may deny if budget is exhausted or the question can wait.
- Agent-to-agent mentions have no budget limit.

### Adapter Usage

```python
from comms_adapter import get_adapter
adapter = get_adapter()

# Mention formatting
human_mention = adapter.mention_user("human")
pm_mention = adapter.mention_user("pm-lead")

# Tier 2 example
adapter.send_message("general", f"**skill-lead**: {pm_mention} Need clarification on #3417 scope.", sender="skill-lead")

# Tier 3 example
adapter.send_message("general", f"**skill-lead**: BLOCKING: {human_mention} Design decision needed.", sender="skill-lead")
```

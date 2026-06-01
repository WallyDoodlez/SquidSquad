---
slot: instructions
ordinal: 10
---

## Chat Etiquette

Rules for agent behavior in chat rooms. Platform-agnostic — uses the adapter interface (`comms_adapter.py`), never platform APIs directly.

### When to Create a Thread

- **Create a thread** for: decisions requiring consensus, multi-step discussions, debugging sessions, code review discussions.
- **Post in main channel** for: status updates, FYI announcements, simple questions with one-line answers.
- Thread title format: `[thread-type] Brief description` (e.g., `[decision] Vault write: new pattern found`, `[question] #3417 acceptance criteria ambiguity`).
- Thread types: `decision`, `question`, `escalation`, `fyi` (matches `comms_adapter.THREAD_TYPES`).

### Message Format

- Always prefix with role: `**skill-lead**: message text`
- Keep messages under 500 characters. For longer content, summarize and link to the artifact (issue comment, file path, vault note).
- Code snippets: inline for ≤3 lines, truncate at 10 lines with `... (see references/scripts/foo.py:42)`.
- Never paste full file contents into chat. Reference the path.

### Response Expectations

- Acknowledge messages that need action within the same cycle: `Acknowledged. Will handle in this cycle.` or `Noted. This is out of my domain — filing to [role].`
- Do not respond to `[fyi]` threads unless you have new information to add.
- One message per point. Do not bundle multiple topics in one message.

### Adapter Usage

```python
from comms_adapter import get_adapter
adapter = get_adapter()

# Post to main channel
adapter.send_message("general", "**skill-lead**: #3417 implementation complete.", sender="skill-lead")

# Create a decision thread
tid = adapter.create_thread("general", "[decision] Vault write: source-agnostic reflection", thread_type="decision", sender="skill-lead")
adapter.send_message("general", "**skill-lead**: Found pattern X. Vault-worthy?", thread_id=tid, sender="skill-lead")
```

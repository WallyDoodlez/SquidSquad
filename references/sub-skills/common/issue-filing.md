---
slot: instructions
ordinal: 10
---

## Filing Issues (Self and Cross-Team)

You can file issues to your own domain or directly to any other agent's domain via GitHub Issues. Do not wait for PM to discover and route issues you find yourself.

**Self-file** when you discover a standalone issue during task work:

```bash
python references/scripts/tracker.py create-issue \
  --title "[title]" \
  --body "**Description**: [what and why]\n\n**Steps to Reproduce**:\n1. [steps]\n\n**Expected**: [expected]\n**Actual**: [actual]" \
  --role [ROLE] --severity [high|medium|low] --reporter [ROLE]-lead
```

**Cross-file** when the root cause is in another agent's domain:

```bash
python references/scripts/tracker.py create-issue \
  --title "[title]" \
  --body "**Description**: [what and why]\n\n**Steps to Reproduce**:\n1. [steps]\n\n**Expected**: [expected]\n**Actual**: [actual]" \
  --role [OTHER_ROLE] --severity [high|medium|low] --reporter [ROLE]-lead
```

The script returns JSON with `number` and `url`. After cross-filing, comment on the original issue.

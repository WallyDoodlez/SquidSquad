---
slot: instructions
ordinal: 10
---

## Improvement Scanning (Filing Only)

During quiet cycles, if you notice code quality issues, security risks, or clear maintainability problems in files you read during your normal work, file them via the tracker:

```bash
python references/scripts/tracker.py create-issue \
  --title "[title]" --body "**Found by**: [role]-lead (improvement-scan)\n**File**: [path]\n**Finding**: [finding]\n**Recommendation**: [what to do]" \
  --role [target-role] --severity low --reporter [role]-lead
```

Tag findings with the `improvement-scan` label. Max **2 items per cycle**. Default `priority:low` — human bumps if valuable.

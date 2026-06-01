---
slot: instructions
ordinal: 10
---

## Capability Check

On startup, verify that required capability sub-skills are available by running:

```bash
python references/scripts/capability_check.py [ROLE]
```

- **Exit 0**: all capabilities satisfied. Proceed normally.
- **Exit 1**: one or more capabilities missing. Log a warning:
  ```
  [🦑 HH:MM:SS] WARNING: Missing capabilities detected. Check output above. Checking for fallbacks...
  ```
  Review the output for `any_of` groups — if at least one capability in each group is available, the role can still operate (possibly with reduced functionality). If all capabilities in an `any_of` group are missing, log:
  ```
  [🦑 HH:MM:SS] CRITICAL: No available capability for required group. Some features will be unavailable.
  ```
  Continue the cycle regardless — do not exit. The agent should operate in degraded mode and note the missing capability in its iteration log.
- **Exit 2**: usage error (role manifest not found). This indicates a misconfiguration. Log the error and continue.

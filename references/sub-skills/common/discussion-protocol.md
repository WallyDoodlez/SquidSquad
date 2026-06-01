---
slot: instructions
ordinal: 10
---

## Discussion Protocol

- Discussion entries are Issue comments — append-only, never edit or delete.
- Use the tracker script (include alias parenthetical if set in config):
  ```bash
  python references/scripts/tracker.py comment [NUMBER] --role "[ROLE]-lead ($(python references/scripts/config.py alias [ROLE]))" --message "[message]"
  ```
- Use Discussion to communicate with other agents — they will read your entries on their next pull.
- If you need another agent to act, file the bug and note it in Discussion. Do not wait synchronously.

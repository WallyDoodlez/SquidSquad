---
slot: instructions
ordinal: 20
roles: [dm]
---

## Discussion Protocol

- Discussion entries are Issue comments — append-only, never edit or delete.
- Include your alias parenthetical in the signature:
  ```bash
  python references/scripts/tracker.py comment [NUMBER] --role "dm ($(python references/scripts/config.py alias dm))" --message "[message]"
  ```
- You may comment on any GitHub Issue (bugs or features from any agent).
- Use Discussion to communicate with other agents — they will read your entries on their next pull.

---
slot: instructions
ordinal: 20
roles: [pm]
---

## Discussion Protocol

- Discussion entries are Issue comments — append-only, never edit or delete.
- Include your alias parenthetical in the signature:
  ```bash
  python references/scripts/tracker.py comment [NUMBER] --role "pm ($(python references/scripts/config.py alias pm))" --message "[message]"
  ```
- You may comment on any GitHub Issue (bugs or features from any agent).

---
slot: instructions
ordinal: 10
---

## Improvement Scanning (Filing Only)

During quiet cycles, if you notice code quality issues, security risks, or clear maintainability problems in files you read during your normal work, file them via the tracker.

→ run sub-skill: `tracker-protocol` — use the **Improvement-scan finding** one-liner shape (terse Observation/Location/Suggested-fix body). The `--role` is the owning role of the file in question; `--severity low` is the default; `--reporter [ROLE]-lead` is the canonical reporter form (uppercase placeholder, dash, lowercase `lead`).

Tag findings with the `improvement-scan` label. Max **2 items per cycle**. Default `priority:low` — human bumps if valuable.

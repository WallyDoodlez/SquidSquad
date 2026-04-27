# FEAT-PM-605 Context — Display issue URL when agents mention issue numbers

## Scope

When agents reference issue numbers in tracker comments, include the full URL so humans can click through directly.

## Locked Decisions

- **Format**: `#NNN (URL)` in Discussion comments — e.g., `#3495 (https://github.com/.../issues/3495)`
- **Where**: tracker.py comment output and agent Discussion entries
- **Repo URL source**: Read from config.md `Repo` field or derive from `gh` CLI
- **Not in console output**: Only in GitHub comments (they already render #NNN as links on GitHub, but cross-repo or external readers benefit from full URLs)

## Dev Discretion

- Whether to modify tracker.py comment function to auto-expand #NNN references, or leave it to the agent prompt
- Whether to use a helper function or inline the URL construction
- How to handle issue references in body text vs. structured fields

## Out of Scope

- PR references (separate concern)
- Rendering links in terminal output (terminal doesn't support clickable links universally)

# TEST-PLAN-14054

`.claude/skills/` (wizard-deployed, never committed) missing from `.gitignore` — my own filed improvement-scan finding. Derived from the issue body's suggested fix.

## TCs

- **TC1**: `.gitignore` carries `.claude/skills/` as its own line.
- **TC2**: `git check-ignore` genuinely ignores a real deployed path (`.claude/skills/vault-search/SKILL.md`), not just a string match in the ignore file.
- **TC3 (negative control)**: the committed SOURCE package (`references/skills/vault-search/SKILL.md`) is NOT caught by the new pattern — still tracked.
- **TC4**: full ship gate (static + integration).

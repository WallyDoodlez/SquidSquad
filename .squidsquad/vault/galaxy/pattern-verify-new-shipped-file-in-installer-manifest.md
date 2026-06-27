---
type: pattern
lane: verification
created: 2026-06-18
source: review
tags: [verification, installer, manifest, shipped-file, qa]
updated: 2026-06-18
owner: verifier
status: active
confidence: medium
---

# Pattern: a new runtime file must reach the ship manifest, not just the repo

**Context.** When verifying a fix/feature that **adds a new file under `references/`** (a script, a sub-skill fragment) that **shipped instructions invoke**, run-the-tests-green and even a clean local AC walk can ALL pass while the fix is still broken for the audience that matters most: **fresh installs**.

**The gap class.** `references/installer-files.txt` is the hand-maintained manifest of every file `npx squidsquad` fetches before launching Claude. A new runtime file absent from it exists in the dev's repo (so every local check passes) but is **never fetched on a fresh install**. If a shipped sub-skill/CLAUDE.md instructs agents to invoke that file, fresh installs hit a missing-file error → the original bug reproduces for exactly the new installs the fix was meant to protect.

**Verification move.** For any pending-test item whose diff adds a file under `references/`:
1. `git diff origin/main...HEAD --name-only` → list NEW files (not just edits).
2. For each new runtime file (scripts the agent runs, fragments boot-Read): `grep -n "<basename>" references/installer-files.txt`. Absent ⇒ **FAIL**, regardless of green tests.
3. Tests under `tests/` are NOT shipped (0 `^tests/` entries) — a new test file correctly needs no manifest line; don't false-flag it.
4. Confirm the header count comment (`# Total: N files`) is bumped when an entry is added.

**Why tests don't catch it.** The dev's working tree already has the file (it's in their commit), so import/exec succeeds in every test and every live walk. The defect is only observable from the *manifest's* perspective — a ship-surface check, not a behavior check. This is the verifier's lane precisely because it's invisible to the implementer's own bar.

**Watch for the misleading AC.** A spec may say "installer-files.txt updated iff a new file is added (likely none — in-place edits)." Treat "likely none" as a hypothesis to test, not a fact — the impl may have added a script the planner didn't anticipate.

Related: [[pattern-verify-composed-output-with-main-landing-state-applied]] (same family — verify the *shipped/composed* surface, not just the source).
I now have all the data. All three files have the fix correctly applied (`git add .squidsquad/`, no `.claude/`). The issue is in the test coverage.

---

### Finding 1

- **File**: `tests/test_feat_2495_upgrade_rewrite.py`
- **Line**: 353–378 (TC-11)
- **Severity**: warning
- **Issue**: The regression test TC-11 does not verify `references/commands/squidsquad-upgrade.md` — one of the three locations the acceptance criteria require fixing.
- **Evidence**: The AC states: *"Fix in all 3 locations (SKILL.md, references/commands/squidsquad-upgrade.md, .claude/commands/squidsquad-upgrade.md). Add regression test."*

  TC-11 checks two paths:
  1. `SKILL.md`'s upgrade section via `_read_skill_upgrade_section()` (line 359)
  2. Either `.claude/commands/squidsquad-upgrade.md` (if present) or SKILL.md fallback via `_upgrade_source_text()` (line 371)

  The `_upgrade_source_text()` helper (line 50–58) reads `UPGRADE_CMD` which is defined as `REPO / ".claude" / "commands" / "squidsquad-upgrade.md"` (line 17). It never reads `references/commands/squidsquad-upgrade.md`.

  In CI (where `.claude/commands/` is gitignored and absent), the test checks SKILL.md twice and silently skips `references/commands/squidsquad-upgrade.md`. If someone reverts the fix in `references/commands/squidsquad-upgrade.md` (e.g., changes `git add .squidsquad/` back to `git add .claude/` or `git add .squidsquad/ .claude/`), TC-11 would still pass because that file is never read.

- **Suggested fix**: Add an explicit check for `references/commands/squidsquad-upgrade.md` in TC-11. For example, after the existing checks, add:

  ```python
  ref_cmd = REPO / "references" / "commands" / "squidsquad-upgrade.md"
  if ref_cmd.exists():
      ref_text = ref_cmd.read_text(encoding="utf-8")
      ref_git_adds = re.findall(r"git add\b.*", ref_text)
      assert ref_git_adds, "references/commands/squidsquad-upgrade.md has no git add command"
      for cmd in ref_git_adds:
          assert ".claude" not in cmd, (
              f"references/commands/squidsquad-upgrade.md stages .claude/ in commit: '{cmd}'."
          )
  ```

  Alternatively, consolidate the three-file check into a loop over `[SKILL_MD, UPGRADE_CMD, ref_cmd]` for clarity.
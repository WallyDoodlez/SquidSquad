# FEAT-SKILL-005 Test Plan — Add Agent Role Command

**Date**: 2026-04-11
**Issue**: #5 — Add agent role command: clone, configure, and boot any role from PM
**Artifacts**: FEAT-SKILL-005-RESEARCH.md, FEAT-SKILL-005-CONTEXT.md

---

## Test Cases

### TC-1: Happy path — add a new role with auto-numbered sibling target

- **Precondition**: Repo at `D:\Dev\Dev\SquidSquad` (PM clone). `config.md` lists `skill` as a configured dev agent. No `SquidSquad-2` sibling directory exists. No `skill` entry in `.squidsquad/.local-config`.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill`
- **Expected**:
  - `D:\Dev\Dev\SquidSquad-2` is created as a full git clone of the source repo
  - `D:\Dev\Dev\SquidSquad-2\.squidsquad\.active-role` contains exactly `skill`
  - `start-skill.sh` and `start-skill.ps1` exist in `D:\Dev\Dev\SquidSquad-2`
  - `.squidsquad/.local-config` in the PM clone contains `- **skill**: D:\Dev\Dev\SquidSquad-2`
  - `.squidsquad/.local-config` in the new clone also contains the skill entry and the PM clone's entry
  - Script exits 0
- **Verification**:
  ```bash
  cat D:/Dev/Dev/SquidSquad-2/.squidsquad/.active-role
  ls D:/Dev/Dev/SquidSquad-2/start-skill.*
  cat D:/Dev/Dev/SquidSquad/.squidsquad/.local-config
  cat D:/Dev/Dev/SquidSquad-2/.squidsquad/.local-config
  ```

---

### TC-2: Happy path — `--target` specifies a custom clone path

- **Precondition**: Repo at `D:\Dev\Dev\SquidSquad`. No directory at `D:\Dev\Dev\custom-skill-clone`.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill --target D:\Dev\Dev\custom-skill-clone`
- **Expected**:
  - Clone is created at exactly `D:\Dev\Dev\custom-skill-clone` (not at auto-numbered sibling)
  - `.active-role` contains `skill`
  - `.local-config` in PM clone records `- **skill**: D:\Dev\Dev\custom-skill-clone`
  - Script exits 0
- **Verification**:
  ```bash
  cat D:/Dev/Dev/custom-skill-clone/.squidsquad/.active-role
  grep "custom-skill-clone" D:/Dev/Dev/SquidSquad/.squidsquad/.local-config
  ```

---

### TC-3: `--dry-run` shows planned actions without executing them

- **Precondition**: No existing skill clone. No `skill` in `.local-config`.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill --dry-run`
- **Expected**:
  - Script prints what it would do: clone target path, `.active-role` value, boot script generation, `.local-config` updates
  - No clone directory is created on disk
  - No `.local-config` is written or modified
  - No boot scripts are generated
  - Script exits 0
- **Verification**:
  ```bash
  # Confirm no clone created
  ls D:/Dev/Dev/SquidSquad-2 2>&1   # should error: not found
  # Confirm .local-config unchanged
  cat D:/Dev/Dev/SquidSquad/.squidsquad/.local-config
  ```

---

### TC-4: `--boot` spawns the agent after clone

- **Precondition**: No existing skill clone. `boot_remote.py` is functional. A terminal emulator is available.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill --boot`
- **Expected**:
  - Clone is created and configured (same as TC-1)
  - A new terminal window is spawned running `start-skill.ps1` (Windows) or `start-skill.sh` (Unix) from the new clone
  - Script exits 0
- **Verification**:
  - Confirm new terminal window appears
  - Confirm `.squidsquad/skill/current-state` is written in the new clone within 2× the iteration interval
  - `python references/scripts/health_check.py` reports skill as healthy

---

### TC-5: `--register-existing` adds a manually-created clone to config

- **Precondition**: A clone already exists at `D:\Dev\Dev\SquidSquad-manual` with `.squidsquad/.active-role` = `qa`. This clone is NOT listed in `.local-config` anywhere.
- **Steps**:
  1. Run `python references/scripts/add_role.py --register-existing D:\Dev\Dev\SquidSquad-manual`
- **Expected**:
  - No new clone is created
  - `.local-config` in PM clone gains `- **qa**: D:\Dev\Dev\SquidSquad-manual`
  - `.local-config` in `D:\Dev\Dev\SquidSquad-manual` is updated with all clones (PM + qa)
  - Script exits 0
- **Verification**:
  ```bash
  grep "SquidSquad-manual" D:/Dev/Dev/SquidSquad/.squidsquad/.local-config
  cat D:/Dev/Dev/SquidSquad-manual/.squidsquad/.local-config
  ```

---

### TC-6: Cross-clone `.local-config` sync — all existing clones updated

- **Precondition**: Two existing clones: PM at `SquidSquad`, skill at `SquidSquad-2`. `.local-config` in both clones contains the skill entry. No dm clone yet.
- **Steps**:
  1. Run `python references/scripts/add_role.py dm`
- **Expected**:
  - `SquidSquad-3` is created for dm
  - `.local-config` in ALL THREE clones (PM, skill, dm) contains entries for all three roles
  - The skill clone (`SquidSquad-2`) was updated even though add_role ran from the PM clone
  - Entries are identical across all three files
- **Verification**:
  ```bash
  cat D:/Dev/Dev/SquidSquad/.squidsquad/.local-config
  cat D:/Dev/Dev/SquidSquad-2/.squidsquad/.local-config
  cat D:/Dev/Dev/SquidSquad-3/.squidsquad/.local-config
  # All three outputs should be identical
  ```

---

### TC-7: Error — role not in config.md

- **Precondition**: `config.md` does NOT list `wizard` as a configured agent.
- **Steps**:
  1. Run `python references/scripts/add_role.py wizard`
- **Expected**:
  - Script prints an error: role `wizard` not found in config.md, with a suggestion to add it first
  - No clone is created
  - No `.local-config` is modified
  - Script exits non-zero (exit code 1 or 2)
- **Verification**:
  ```bash
  python references/scripts/add_role.py wizard; echo "exit: $?"
  ```

---

### TC-8: Error — target directory already exists

- **Precondition**: `D:\Dev\Dev\SquidSquad-2` already exists (any content).
- **Steps**:
  1. Run `python references/scripts/add_role.py skill` (auto-numbered target would be `SquidSquad-2`)
- **Expected**:
  - Script detects that the target path already exists
  - Prints an error describing the conflict and notes that `--force` would override
  - No clone operation attempted
  - No `.local-config` modified
  - Script exits non-zero
- **Verification**:
  ```bash
  python references/scripts/add_role.py skill; echo "exit: $?"
  # Confirm SquidSquad-2 is unchanged
  ```

---

### TC-9: Error — role already has a registered clone

- **Precondition**: `.local-config` already contains `- **skill**: D:\Dev\Dev\SquidSquad-2`.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill`
- **Expected**:
  - Script detects the existing registration
  - Prints an error: skill already registered at `D:\Dev\Dev\SquidSquad-2`, use `--force` to override
  - No new clone created
  - Script exits non-zero
- **Verification**:
  ```bash
  python references/scripts/add_role.py skill; echo "exit: $?"
  ```

---

### TC-10: `git clone --local` uses hardlinks (not full copy)

- **Precondition**: Source repo is a local path (not remote-only).
- **Steps**:
  1. Note the disk usage of the source `.git/objects` directory
  2. Run `python references/scripts/add_role.py skill`
  3. Note the disk usage of `SquidSquad-2/.git/objects`
- **Expected**:
  - The new clone's `.git/objects` is significantly smaller than the source (hardlinks share inodes)
  - On Windows: verify using `fsutil hardlink list` on a pack file in the new clone — it should show two paths (source and clone)
  - On Unix: `ls -i` on pack files in both clones shows the same inode number
- **Verification**:
  ```bash
  # Windows:
  fsutil hardlink list D:/Dev/Dev/SquidSquad-2/.git/objects/pack/*.pack
  # Unix:
  ls -i D:/Dev/Dev/SquidSquad/.git/objects/pack/ D:/Dev/Dev/SquidSquad-2/.git/objects/pack/
  ```

---

### TC-11: Windows path handling — spaces and long paths

- **Precondition**: Windows 11. Source repo name contains a space, e.g. `D:\Dev\Dev\Squid Squad`.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill`
- **Expected**:
  - Clone is created at `D:\Dev\Dev\Squid Squad-2` (space preserved)
  - `.local-config` entries correctly quote or preserve the path (format: `- **skill**: D:\Dev\Dev\Squid Squad-2`)
  - health_check.py can parse and use the path with spaces
  - Script exits 0
- **Verification**:
  ```bash
  python references/scripts/health_check.py
  # skill should report healthy or unknown (not parse error)
  ```

---

### TC-12: Unix path handling — forward slashes and tilde expansion

- **Precondition**: Unix host. Repo at `/home/user/projects/SquidSquad`.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill --target ~/projects/SquidSquad-skill`
- **Expected**:
  - Tilde is expanded to the absolute path before cloning
  - Clone is created at `/home/user/projects/SquidSquad-skill`
  - `.local-config` contains the absolute path (not `~`-relative)
  - Script exits 0
- **Verification**:
  ```bash
  grep "SquidSquad-skill" ~/.squidsquad/.local-config  # or wherever PM clone lives
  ls /home/user/projects/SquidSquad-skill/.squidsquad/.active-role
  ```

---

### TC-13: `.active-role` is written before boot scripts are generated

- **Precondition**: Clean state, no skill clone.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill`
- **Expected**:
  - `.active-role` is written in the new clone first, then `compose.py boot skill` runs
  - The generated boot scripts (`start-skill.sh`, `start-skill.ps1`) use `skill` role token correctly (not a placeholder)
  - Both `start-skill.sh` and `start-skill.ps1` exist and are non-empty
- **Verification**:
  ```bash
  cat D:/Dev/Dev/SquidSquad-2/start-skill.sh | grep "skill"
  cat D:/Dev/Dev/SquidSquad-2/start-skill.ps1 | grep "skill"
  ```

---

### TC-14: Atomic `.local-config` writes — no partial writes under normal operation

- **Precondition**: Any state with an existing `.local-config`.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill` (or use `--dry-run` to simulate and inspect temp file behaviour)
  2. Inspect temp file handling
- **Expected**:
  - The script writes to a `.local-config.tmp` (or equivalent temp file) first, then renames to `.local-config`
  - No `.local-config.tmp` file is left behind after the command completes
  - The final `.local-config` is a valid, complete file
- **Verification**:
  ```bash
  ls D:/Dev/Dev/SquidSquad/.squidsquad/.local-config*
  # Only .local-config should exist, not .local-config.tmp
  ```

---

### TC-15: Stale `.local-config` entry — missing clone path is tolerated

- **Precondition**: `.local-config` contains `- **qa**: D:\Dev\Dev\SquidSquad-qa` but that directory does not exist on disk.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill`
- **Expected**:
  - Script logs a warning about the stale qa entry but does NOT abort
  - skill clone is created and configured successfully
  - Updated `.local-config` still contains the stale qa entry (not pruned without `--prune`)
  - Script exits 0
- **Verification**:
  ```bash
  python references/scripts/add_role.py skill; echo "exit: $?"
  grep "qa" D:/Dev/Dev/SquidSquad/.squidsquad/.local-config  # stale entry preserved
  ```

---

### TC-16: `--dry-run` with `--boot` — no terminal spawned

- **Precondition**: No existing skill clone.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill --dry-run --boot`
- **Expected**:
  - Script prints that it would boot the agent after cloning
  - No terminal window is spawned
  - No clone is created
  - Script exits 0
- **Verification**:
  - No new terminal window visible
  - `ls D:/Dev/Dev/SquidSquad-2` returns not-found

---

### TC-17: `health_check.py` sees new agent after add_role

- **Precondition**: Before running add_role, health_check reports skill as unknown or not listed.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill`
  2. Manually start the skill agent (or use `--boot`) so it writes `current-state`
  3. Run `python references/scripts/health_check.py`
- **Expected**:
  - health_check reads the updated `.local-config` and includes skill in its report
  - Once skill writes `current-state`, health_check reports it as healthy
  - No changes to health_check.py are required
- **Verification**:
  ```bash
  python references/scripts/health_check.py
  # skill row should appear
  ```

---

### TC-18: `--register-existing` on a path missing `.squidsquad/`

- **Precondition**: A directory exists at `D:\Dev\Dev\not-a-squidsquad` but has no `.squidsquad/` subdirectory.
- **Steps**:
  1. Run `python references/scripts/add_role.py --register-existing D:\Dev\Dev\not-a-squidsquad`
- **Expected**:
  - Script prints an error: path is not a valid SquidSquad clone (missing `.squidsquad/` directory)
  - No `.local-config` is modified
  - Script exits non-zero
- **Verification**:
  ```bash
  python references/scripts/add_role.py --register-existing D:/Dev/Dev/not-a-squidsquad; echo "exit: $?"
  ```

---

### TC-19: Auto-numbered sibling skips occupied directories

- **Precondition**: `SquidSquad-2` already exists (unrelated content), `SquidSquad-3` does not.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill` (no `--target`)
- **Expected**:
  - Script detects `SquidSquad-2` is occupied, increments to `SquidSquad-3`
  - Clone is created at `SquidSquad-3`
  - `.local-config` records `- **skill**: D:\Dev\Dev\SquidSquad-3`
  - Script exits 0
- **Verification**:
  ```bash
  cat D:/Dev/Dev/SquidSquad-3/.squidsquad/.active-role  # should be "skill"
  grep "SquidSquad-3" D:/Dev/Dev/SquidSquad/.squidsquad/.local-config
  ```

---

### TC-20: `--json` flag outputs machine-readable result

- **Precondition**: Clean state.
- **Steps**:
  1. Run `python references/scripts/add_role.py skill --json`
- **Expected**:
  - Script outputs valid JSON to stdout (not mixed with human-readable text)
  - JSON includes at minimum: `role`, `clone_path`, `status` (`created` | `error`), and any error message
  - Script exits 0 on success, non-zero on error (exit code still meaningful)
- **Verification**:
  ```bash
  python references/scripts/add_role.py skill --json | python -m json.tool
  # Should parse cleanly
  ```

---

## Smoke Tests

- [ ] `python references/scripts/add_role.py --help` prints usage without error
- [ ] `python references/scripts/add_role.py skill --dry-run` exits 0 and prints at least the target path
- [ ] After a successful add, `cat <new-clone>/.squidsquad/.active-role` returns the role name with no trailing whitespace
- [ ] `.local-config` in both PM and new clone parse correctly under `health_check.py` without modification to health_check
- [ ] `boot_remote.py --all --json` includes the new role after add_role completes

---

## Regression Risks

- **health_check.py must not require changes**: If `.local-config` format is preserved exactly (`- **role**: /path`), health_check and boot_remote continue to work. Any deviation in whitespace or quoting will silently break health probing.
- **compose.py `boot <role>` must be callable from a different working directory**: If compose.py uses relative paths internally, calling it with `cwd=new_clone` may fail. Verify it uses `Path(__file__).resolve()` anchoring.
- **Windows path separators in `.local-config`**: health_check parses paths with `Path(m.group(2).strip())`. Ensure add_role writes Windows paths with backslashes (not forward slashes) on Windows, or uses pathlib consistently, to avoid double-resolution issues.
- **Permission errors on existing clone `.local-config`**: If a remote agent's clone is currently running and has the file open (rare on NTFS but possible), the atomic rename approach must handle `PermissionError` gracefully — warn and continue rather than aborting.
- **`.active-role` should not have a trailing newline that confuses downstream readers**: health_check and boot_remote both read `.active-role`. Verify the written value is stripped cleanly.
- **Concurrent `add_role` invocations**: If two add_role calls race (e.g., PM automation + human manual), the lock file (same pattern as boot_remote `boot-lock`) must prevent double-clone of the same role. Without the lock, two simultaneous calls could both pass the "role not registered" check and both attempt to clone.

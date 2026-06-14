I have reviewed all four changed files against the acceptance criteria. Here are my findings:

### Finding 1

- **File**: `references/scripts/git_ops.py`
- **Line**: 1149-1156
- **Severity**: warning
- **Issue**: `install_hooks()` returns `True` even when the `chmod` call fails on a Unix system, violating the docstring contract: *"Returns True if the guard is active after the call"*. If `chmod` fails (noexec mount, permission denied, etc.), the hook file is not executable and git silently skips it — the guard is NOT active despite the return value.
- **Evidence**: The `try/except OSError: pass` block at lines 1150-1155 swallows the error and falls through to `return True` at line 1156. On Unix, git requires the hook file to have an executable bit — without it, the pre-commit hook never fires even though `core.hooksPath` points at the directory.
- **Suggested fix**: Capture the chmod result and return `False` on `OSError`, or at minimum log a diagnostic so the operator knows the guard is installed but non-functional:

```python
try:
    import os
    import stat
    os.chmod(hook, os.stat(hook).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
except OSError as e:
    print(f"WARNING: failed to make hook executable ({e}); guard installed but may not fire",
          file=sys.stderr)
    return False
```

---

### Finding 2

- **File**: `references/scripts/git_ops.py`
- **Line**: 1043-1062 (docstring) vs. 796-814 (commit_state implementation)
- **Severity**: warning
- **Issue**: The `guard_staged_state` docstring claims unstaged `.claude/` files *"will be committed via `commit_state`"*, but `commit_state` only stages `.squidsquad/` files (line 813: `if path.startswith(".squidsquad/")`). `.claude/` files unstaged by the guard are never picked up by `commit_state` — they either wait for `commit_push` (the old `add_all` path) or, if the agent uses the modern `commit_role_scoped` path, they accumulate in the working tree indefinitely because no role's allowlist covers `.claude/`.
- **Evidence**: `_is_state_file` (line 490) classifies both `.squidsquad/` and `.claude/` as state. `guard_staged_state` unstages both. But `commit_state` at line 813 only checks `path.startswith(".squidsquad/")`. The docstring at line 1062 says *"the next working-branch cycle commits them via `commit_state`"*, which is false for `.claude/` files.
- **Suggested fix**: Either expand `commit_state` to also stage `.claude/` files matching the same `_is_state_file` classifier (so the docstring becomes true and the routing stays single-source), or correct the docstring to accurately describe that `.claude/` files are committed via other paths.

---

### Finding 3

- **File**: `references/git-hooks/pre-commit`
- **Line**: 14-16
- **Severity**: warning
- **Issue**: The `2>&1` redirects on lines 14-15 send stderr to stdout for each `python`/`python3` invocation. The `guard_staged_state` function deliberately prints its warnings to stderr (lines 1092-1101 of `git_ops.py`) so operators can see when state files are unstaged. By redirecting those warnings to stdout, they become invisible — git typically suppresses stdout from successful pre-commit hooks (exit 0). The guard always exits 0, so the warnings are lost.
- **Evidence**: `git_ops.py` line 1092-1093: `print(f"WARNING: pre-commit guard unstaged ...", file=sys.stderr)`. The shim runs `python ... 2>&1`, collapsing stderr → stdout. Since the shim always exits 0 (line 17), git has no reason to display stdout output.
- **Suggested fix**: Drop the `2>&1` redirects so stderr passes through directly. The `||` fallback chain works the same regardless of whether stderr is merged into stdout. Change to:

```sh
python references/scripts/git_ops.py guard-staged-state \
  || python3 references/scripts/git_ops.py guard-staged-state \
  || true
```

---

### Finding 4

- **File**: `references/scripts/git_ops.py`
- **Line**: 1184-1193 (main), 1159-1173 (_ensure_hooks_installed)
- **Severity**: warning
- **Issue**: `_ensure_hooks_installed` is called on every `git_ops.py` invocation (except guard-staged-state and install-hooks), which gates on `install_hooks()`. When `core.hooksPath` is set to a foreign value (e.g., `.husky`), `install_hooks()` prints a multi-line WARNING and returns `False` — on EVERY invocation. For an operator who intentionally configured a different hooksPath, this produces continual stderr noise on every `pull`, `has-changes`, `commit-code`, `task-begin`, etc.
- **Evidence**: `_ensure_hooks_installed` (line 1169-1171) calls `install_hooks()` whenever `current != _HOOKS_DIR_REL`. `install_hooks()` (lines 1127-1134) prints a WARNING and returns `False` for any foreign hooksPath value — there is no "warn once" gating. The call in `main()` at line 1192-1193 gates out only `guard-staged-state` and `install-hooks`; every other subcommand triggers the self-heal.
- **Suggested fix**: Add a module-level flag (e.g., `_hooks_warned_foreign = False`) so the foreign-hooksPath WARNING is emitted at most once per process lifetime. Alternatively, gate `_ensure_hooks_installed` to only run on commands that actually produce commits (`commit`, `commit-code`, `commit-state`, `commit-push`, `commit-role-scoped`) rather than every read-only command.
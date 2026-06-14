### Finding 1

- **File**: `references/scripts/git_ops.py`
- **Line**: ~880 (inside `guard_staged_state`, the `_run("git branch --show-current")` call)
- **Severity**: warning
- **Issue**: `guard_staged_state` calls `_run("git branch --show-current")` with the default `check=True`. If this git command fails for any reason (corrupted `.git/HEAD`, permission error, etc.), `subprocess.run` raises `CalledProcessError`, crashing the Python process before `sys.exit(0)` is reached in `main()`. The pre-commit hook shim's `|| python3 ... || true` chain ultimately preserves fail-open at the hook level, but the function itself violates the spec that it "always returns normally." Every other subprocess call in `guard_staged_state` correctly uses `check=False`; this one call is the lone holdout.
- **Evidence**:  
  - `_run` signature at line 65: `def _run(cmd, check=True)` — default is `check=True`.  
  - The call site: `current = _run("git branch --show-current").stdout.strip()` — no `check=False` argument.  
  - Every other call in the guard (`git diff --cached`, `git reset`) explicitly passes `check=False`.  
  - Compare the fail-open contract in the docstring: "FAIL-OPEN: always returns normally (exit 0 at the call site)."
- **Suggested fix**: Add `check=False` to the call:
  ```python
  current = _run("git branch --show-current", check=False).stdout.strip()
  ```
  If the command fails, `current` will be empty, the `if not current` guard will catch it, and the function returns `[]` cleanly — true fail-open at the function level.
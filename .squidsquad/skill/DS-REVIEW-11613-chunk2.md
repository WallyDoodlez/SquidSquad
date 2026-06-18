Now I have enough context. Let me finalize my findings.

---

```
### Finding 1

- **File**: references/scripts/wizard.py
- **Line**: 139–156 (definition), 655 (call site)
- **Severity**: warning
- **Issue**: `_run` only catches `subprocess.TimeoutExpired`; bare `FileNotFoundError` or `PermissionError` from `subprocess.run` would propagate uncaught through `provision_deps`, crashing the function mid-loop instead of returning the documented result dict.
- **Evidence**: `_run` (line 139–150) wraps `subprocess.run` in a `try/except subprocess.TimeoutExpired` but does not guard against other `OSError` subclasses. In `provision_deps` line 655, `_run(cmd, timeout=600)` is called in a loop. If a command binary is deleted between detection and provisioning (TOCTOU race), `subprocess.run` raises `FileNotFoundError` → `_run` does not catch it → `provision_deps` crashes. This violates the function contract that promises a structured dict return (line 621–627). The likelihood is low (all commands are validated via `shutil.which`/`_run` in the immediately-preceding `gather_deps` call), but the blast radius if it happens is an opaque stack trace to the installer agent instead of JSON.
- **Suggested fix**: Extend `_run`'s except clause to also catch `OSError` (the parent of both `FileNotFoundError` and `PermissionError`) and return a synthetic `CompletedProcess` with `returncode=127` and the exception text in `stderr`, consistent with the existing timeout-handling pattern.

### Finding 2

- **File**: references/scripts/wizard.py
- **Line**: 332–334
- **Severity**: warning
- **Issue**: `_choose_pkg_manager` for macOS returns `["brew", "install", pkg]` with no environment variables to suppress Homebrew's automatic `brew update` before installing. This can add significant unpredictable latency (minutes on a slow connection) with no benefit for a freshly-detected brew that already works.
- **Evidence**: When `brew install` runs, Homebrew auto-updates itself by default before executing the install. The command built on line 334 (`["brew", "install", pkg]`) inherits the current process environment, so `HOMEBREW_NO_AUTO_UPDATE` is not set. The 600-second timeout on line 655 mitigates a true hang but does not prevent unnecessary delays. The spec requires provisioning to be "non-interactive" — while this isn't a prompt/hang, the auto-update can stall behind slow networks or rate-limited GitHub API calls. Every other package manager in this function has flags baked in for non-interactive operation (`-y` for apt/dnf/choco, `--silent` for winget); brew's equivalent is the `HOMEBREW_NO_AUTO_UPDATE` environment variable.
- **Suggested fix**: Either set `HOMEBREW_NO_AUTO_UPDATE=1` in the subprocess environment (`env={**os.environ, "HOMEBREW_NO_AUTO_UPDATE": "1"}`) or pass it via the `_run` kwargs so the brew command doesn't auto-update. The `_run` wrapper already accepts `**kwargs` forwarded to `subprocess.run`, so this is a one-line addition at the call site.

### Finding 3

- **File**: references/scripts/wizard.py
- **Line**: 510
- **Severity**: warning
- **Issue**: The Python 3 detection `shutil.which("python3") or shutil.which("python")` does not verify that the found `python` is actually Python 3.x. On systems where `python` resolves to Python 2 and `python3` is absent, the check incorrectly reports python3 as "satisfied."
- **Evidence**: Line 510: `if shutil.which("python3") or shutil.which("python"): satisfied.append("python3")`. The docstring on line 509 says "Python 3 on PATH (python3 or python resolving to a 3.x)" but no version probe is performed. A system with only a legacy Python 2 `/usr/bin/python` and no `python3` symlink would pass detection despite having no usable Python 3 on PATH. In practice the wizard script itself requires Python 3 (f-strings, keyword-only args, `importlib.util`), so `sys.executable` is Python 3 — but the PATH check is meant to answer "can the user invoke Python 3 from a shell," and `shutil.which("python")` returning a Python 2 path gives the wrong answer.
- **Suggested fix**: When only `python` (not `python3`) is found, run `[_python_path, "-c", "import sys; sys.exit(0 if sys.version_info >= (3,) else 1)"]` to confirm it's Python 3, or use `sys.version_info` to short-circuit if `sys.executable` resolves to the same path.
```
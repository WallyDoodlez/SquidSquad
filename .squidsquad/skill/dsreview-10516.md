### Finding 1

- **File**: `references/scripts/event_bus.py`
- **Line**: 42–45 (the new comment block added above `SQUID_DIR = _resolve_squid_dir()`)
- **Severity**: warning
- **Issue**: The comment states *"Internal call sites use `_resolve_squid_dir()` directly so a runtime `SQUIDSQUAD_DIR` change is honored without requiring an `importlib` reload (#10516)."* — but this is factually incorrect. The only internal call site that needs squid‑dir resolution is `_discover_port()` (line 69–70), and it does **not** call `_resolve_squid_dir()`. It duplicates the env‑read logic inline with `SQUID_DIR` as its fallback. `_resolve_squid_dir()` is called exactly once, at module‑load time on line 46, and never again.
- **Evidence**: 
  - `_discover_port()` lines 69–70: `raw = (os.environ.get("SQUIDSQUAD_DIR") or "").strip()` / `squid_dir = Path(raw).expanduser() if raw else SQUID_DIR` — no call to `_resolve_squid_dir()`.
  - grep confirms the only call to `_resolve_squid_dir()` in `event_bus.py` is the module‑level `SQUID_DIR = _resolve_squid_dir()` on line 46.
  - If a future developer adds another internal call site and follows the comment by calling `_resolve_squid_dir()`, that function falls back to `REPO_ROOT / ".squidsquad"` — **not** to the patchable `SQUID_DIR`. This would silently break any test that uses `patch.object(event_bus, 'SQUID_DIR', …)` to control the fallback, because `_resolve_squid_dir()` has no awareness of `SQUID_DIR`.
- **Suggested fix**: Either:
  1. Rewrite the comment to accurately describe the architecture: *"Internal call sites that need a runtime `SQUIDSQUAD_DIR` read the env var at call time and fall back to the module‑level `SQUID_DIR` — see `_discover_port()` for the pattern. `_resolve_squid_dir()` is only used to initialise `SQUID_DIR` at import time."*
  2. Or, refactor `_discover_port()` to call `_resolve_squid_dir()` and change `_resolve_squid_dir()` to accept an optional fallback (so the single source of truth is maintained). This is a bigger change and may be out of scope, but option 1 is sufficient to prevent future confusion.

---

Regarding the four specific concerns raised in the review brief:

- **Module‑level capture back‑compat**: No issue. `SQUID_DIR` is still the module‑level fallback; `_discover_port()` uses it only when `SQUIDSQUAD_DIR` is unset at call time. The existing `patch.object(event_bus, 'SQUID_DIR', …)` pattern continues to work, proven by the new test and by the pre‑existing `patch_dirs` fixture.
- **`os.environ.get` vs `os.getenv`**: Consistent. `_resolve_squid_dir()` (line 29), the new `_discover_port()` code (line 69), and `ack_stop()` all use `os.environ.get(...)`. No drift.
- **`monkeypatch.setenv` interaction**: Clean. `monkeypatch.setenv` mutates `os.environ` in place; the module imports `os` at the top level and accesses the same live `os.environ` dict — no captured‑reference problem.
- **`Path(raw).expanduser()` on Windows (UNC / trailing slashes)**: No surprise. `expanduser()` is a no‑op unless the path contains `~`, so UNC paths (`\\server\share`) and drive‑letter paths pass through unchanged. Trailing slashes are normalised away by `Path` before `/ ".harness-port"` appends the filename. No Windows‑specific regression.
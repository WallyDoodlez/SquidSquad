Based on my review, I confirm: `start.bat` exists at repo root (a thin delegator to `start.ps1`), so the `.bat` header's reference to it is correct. The manifest count (202) matches the payload. The `_exec_lines` filtering logic is sound. Both launchers correctly avoid git/pip/sync commands.

I found one real issue:

---

### Finding 1

- **File**: tests/test_12525_bare_harness_launcher.py
- **Line**: 130–131
- **Severity**: warning
- **Issue**: `test_start_ps1_present` only asserts that `start.ps1` exists, but does **not** verify that it still contains sync/dep-install logic. By contrast, `test_start_sh_still_full` (lines 125–128) checks for `requirements.txt` and `git pull --rebase` in `start.sh`. The class docstring (line 122) claims "AC5 — the existing full-setup launchers keep their sync + dep logic," yet the test for `start.ps1` would silently pass even if someone stripped all sync+dep code from that file.
- **Evidence**: AC5 requires "existing start.* unchanged." The `start.sh` test verifies content; the `start.ps1` test only verifies file existence. Since `start.bat` delegates to `start.ps1` (confirmed by reading `start.bat` — it calls `pwsh … start.ps1`), a regression in `start.ps1` that removes sync/dep logic would go undetected by this test suite.
- **Suggested fix**: Add a `test_start_ps1_still_full` method (or extend `test_start_ps1_present`) to also assert key sync/dep strings in `start.ps1`, for example `"requirements.txt"` and `"git pull --rebase"` (both strings are present in the current `start.ps1` at lines 14 and 24).

---

**No other issues found.** The launcher scripts themselves are correct: the `.sh` uses `exec python3 … "$@"` for foreground execution, the `.bat` uses `python … %*` + `pause` for a persistent visible window, both `cd` to the script directory, and neither contains any git/pip/sync footprint in executable lines. The manifest header count (202) matches the payload count.
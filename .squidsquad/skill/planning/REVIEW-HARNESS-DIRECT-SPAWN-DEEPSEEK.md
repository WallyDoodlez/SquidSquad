I've reviewed all three files carefully. Here are the findings, ordered by severity:

---

### Finding 1

- **File**: `references/experiments/resolve_claude.py`
- **Line**: 44–47 (`_WIN_CMD_FORWARD` regex)
- **Severity**: warning
- **Issue**: The regex only matches the `%dp0%` variable form and silently misses the `%~dp0` direct form that older/simpler npm shim variants use. The doc says "the npm shim's pattern is consistent" but npm has used at least two different `.cmd` shim formats: the older one-line `@"%~dp0\node_modules\...\claude.exe" %*` and the newer multi-line form with `SET dp0=%~dp0` followed by `"%dp0%\..."`. Only the multi-line form is matched.
- **Evidence**: 
  - `_WIN_CMD_FORWARD = re.compile(r'"%dp0%\\(?P<rel>[^"]+\.exe)"')` — the literal `%dp0%` in the regex matches only `%dp0%`, never `%~dp0`.
  - Line 87–93 in `_parse_shim`: if no regex matches, the function returns `None`, and `_walk_shim_chain` treats the `.cmd` file itself as the final binary. `Popen` of a `.cmd` file on Windows goes through `cmd.exe` — exactly the wrapper the whole proposal aims to eliminate. The resolver silently falls back to giving you the shim, and the caller would never know.
  - The test output in §4.1.1 proves only that the multi-line form works on *this* machine. It does not prove the resolver handles other npm versions.
- **Suggested fix**: Either extend `_WIN_CMD_FORWARD` with an alternative pattern for `%~dp0` (e.g., `r'"%~dp0\\(?P<rel>[^"]+\.exe)"'`), or — better — detect that the `.cmd` shim wasn't parsed and raise a clear error rather than silently returning the shim as the resolved path.

---

### Finding 2

- **File**: `references/experiments/resolve_claude.py`
- **Line**: 50–52 (`_SH_FORWARD` regex)
- **Severity**: warning
- **Issue**: The POSIX bash-shim regex does not match the actual format of npm-generated POSIX shims. The regex expects `exec "$basedir"/path` or `exec "${basedir}"/path` (path separator *outside* the quotes), but actual npm POSIX shims embed the separator and `node` *inside* the quotes: `exec "$basedir/node" "$basedir/path/to/cli.js" "$@"`.
- **Evidence**: 
  - Regex: `r'exec\s+(?:"\$basedir"|"\$\{basedir\}")[/\\](?P<rel>\S+?)\s'` — requires `"$basedir"` immediately before `/` or `\`, but actual shims write `"$basedir/node"` (the `/node` is inside the string).
  - The doc is honest that "POSIX paths are written but untested" (§3.1, §4.1.1), but it doesn't flag that the regex is structurally incompatible with the known npm POSIX shim format. A reader skimming the code might assume it's ready to go with just integration testing.
- **Suggested fix**: Rewrite the POSIX parser to match the actual npm shim structure — extract the path of `cli.js` or the node binary from the second `exec` argument. The simplest robust approach: find any line matching `exec` and extract the last argument that looks like a path to `cli.js` or ends in a known Claude binary name.

---

### Finding 3

- **File**: `references/experiments/resolve_claude.py`
- **Line**: 96–102 (`_walk_shim_chain`)
- **Severity**: warning
- **Issue**: When a shim-hop target doesn't exist on disk (`nxt.exists()` is False), the function returns the *previous shim* as the "final" binary. If that shim is a `.cmd`/`.bat`/`.ps1` wrapper, `Popen` on it will go through the wrapper process — exactly the path the proposal aims to eliminate — and the caller gets no error.
- **Evidence**: Lines 99–100: `if not nxt.exists(): return current, chain` — `current` at this point is the shim that pointed to the broken path, possibly a `.cmd` file. The caller of `resolve_claude()` receives a `Path` that is a `.cmd` shim, with no indication resolution failed.
- **Suggested fix**: If a shim points to a non-existent target, either raise `FileNotFoundError` with a clear message, or at minimum return a sentinel value / mechanism string like `"broken shim chain"` that the caller can detect.

---

### Finding 4

- **File**: `references/experiments/spawn_tree_test.py`
- **Line**: 130 (`creationflags=DETACHED_PROCESS`)
- **Severity**: warning
- **Issue**: The test uses `creationflags=DETACHED_PROCESS` when spawning processes, but the doc's §4.1.2 results table reports `conhost.exe (depth 2)` as a descendant in Test B. `DETACHED_PROCESS` means the child does not inherit a console — `conhost.exe` should not appear, since `conhost.exe` only hosts console windows. Either the doc's table describes a different run of the test (without `DETACHED_PROCESS`), or the table is incorrect.
- **Evidence**: 
  - Line 130: `creationflags=DETACHED_PROCESS` (0x00000008). Per Windows documentation, this flag means "the new process does not inherit its parent's console" — no console, no `conhost.exe`.
  - §4.1.2 table row for Test B: `conhost.exe (depth 2)` is listed under "Descendants captured."
  - If the test was actually run with `DETACHED_PROCESS` and `conhost.exe` appeared, that would imply something unusual about the test machine's process model, which isn't discussed.
- **Suggested fix**: Either remove `DETACHED_PROCESS` from the test (so it matches the doc) and accept the console-window flash, or update the doc's table to reflect actual output from the code as written. Better: drop `DETACHED_PROCESS` and use `CREATE_NO_WINDOW` (0x08000000) instead, which is more appropriate for this use case.

---

### Finding 5

- **File**: `references/experiments/spawn_tree_test.py`
- **Line**: 178–183 (INCONCLUSIVE branch returns 0)
- **Severity**: warning
- **Issue**: When the test cannot distinguish between the shim and direct spawn (both show `Popen.pid` as `claude.exe`), it prints `[INCONCLUSIVE]` and still exits `0`. An inconclusive demonstration of the central claim should not be a success exit code — it masks that the experiment failed to prove its thesis on that run.
- **Evidence**: Lines 181–183:
  ```python
  print("\n[INCONCLUSIVE] Both paths produced Popen.pid=claude.exe directly.")
  print("     The shim may have been short-lived enough that we caught")
  print("     the post-exec state. Re-run, or trust Test A as proof.")
  return 0
  ```
  The comment even says "Re-run" — implying this outcome is not a successful validation.
- **Suggested fix**: Return a distinct non-zero exit code (e.g., `3`) for inconclusive results so CI or a caller can distinguish "proved" from "couldn't demonstrate." Or increase the snapshot frequency and count to reduce the race window.

---

### Finding 6

- **File**: `references/experiments/spawn_tree_test.py`
- **Line**: 14–18 (docstring claim), 137–162 (race window logic)
- **Severity**: warning
- **Issue**: The test's central claim — "prove that spawning the resolved claude.exe directly produces a process tree where `Popen.pid` IS claude.exe" — is inherently racy and the mitigation (20 snapshots at 20ms intervals) can fail silently on fast machines. The `claude.exe --version` invocation completes in well under 100ms on modern hardware; the first snapshot at 20ms may already miss the process entirely. The code acknowledges this (line 150–153) but the verdict logic in `main()` doesn't treat "process never seen" as a failure.
- **Evidence**: 
  - Lines 150–153: if `spawn_pid` is never seen in any snapshot, it prints a WARNING but continues. `self_exe` becomes `"<not captured>"`, so `is_claude_directly` becomes `False` (since `"claude.exe" in "<not captured>"` is `False`), and both tests fail, triggering the `[UNEXPECTED]` path. That is at least a non-zero exit. But if ONLY Test B's spawn_pid is never seen (the cmd.exe exits before snapshot 1) and Test A is seen, the verdict could still pass on misleading grounds.
  - More importantly, the experiment proves only that `Popen(claude.exe)` on `--version` returns `claude.exe`'s PID. It does **not** prove that this holds for the actual long-running `claude` interactive session that `thin_launcher.py` would spawn — that's a different code path in Claude, though it's almost certainly the same.
- **Suggested fix**: Use a slower Claude invocation (e.g., `-p "reply pong"`) instead of `--version` to widen the observation window. Add a check: if neither process was ever captured, that's a test infrastructure failure, not a pass.

---

### Finding 7

- **File**: `docs/HARNESS-DIRECT-SPAWN.md`
- **Line**: 68–70 (§3.4, "wt.exe stays — load-bearing for TTY/subscription billing")
- **Severity**: warning
- **Issue**: The doc overstates the evidence. The experiment in §4.3 proves that *pipes cause API billing* and *a TTY keeps subscription billing*. It does **not** prove that `wt.exe` specifically is required. The doc says `wt.exe` is "the cheapest TTY provider Windows has" without comparing alternatives (ConPTY API, a lightweight PTY wrapper like winpty, Microsoft's own `ConPTY` samples, or even the classic `conhost.exe`). ConPTY could provide a PTY pair programmatically from Python without an extra windowing process, and the doc acknowledges PTY emulation exists (§1, §7) but dismisses it as "strictly more complex" without evidence.
- **Evidence**: §1: "The only way to harness-own `claude` while keeping subscription billing is full PTY emulation + driving the TUI programmatically." This conflates "PTY emulation" (providing a pseudoterminal so `claude.exe` sees a TTY) with "driving the TUI programmatically" (screen-scraping the interactive UI). These are distinct. The experiment only tested pipe vs. real TTY; it never tested whether a programmatic PTY (without screen-scraping, since we'd still use `stream-json` I/O format if it works over a PTY) would keep subscription billing.
- **Suggested fix**: Soften the claim to what was actually proved: "a TTY is required for subscription billing; `wt.exe` is the simplest way to provide one today." Note that a ConPTY-based approach (providing a PTY without screen-scraping, using stream-json over the PTY's pipes) is an untested middle ground worth investigating before declaring `wt.exe` permanently load-bearing.

---

### Finding 8

- **File**: `docs/HARNESS-DIRECT-SPAWN.md`
- **Line**: 60–62 (§3.1, "~250 lines deletable")
- **Severity**: warning
- **Issue**: The doc claims the entire `_resolve_claude_exe_pid` + descendant-walker machinery "is deletable" based on the `spawn_tree_test.py` experiment, but the experiment only proves that `Popen.pid` IS `claude.exe` when spawning the resolved `.exe` path. It does **not** verify that `thin_launcher.py` uses those functions *only* for finding claude.exe's PID. If `_win32_list_descendants` or `_posix_list_descendants` are used elsewhere (e.g., for cleanup/kill-on-exit of the entire process subtree, or monitoring child tool processes), deleting them would break those features. Neither experiment script inspects `thin_launcher.py` to confirm the functions have no other callers.
- **Evidence**: The experiment scripts test the process-tree structure and path resolution. Neither does a `grep` or cross-reference of `thin_launcher.py` to confirm the descendant-walker functions are exclusively used for PID resolution. The doc's net-line-count calculation (`~250 lines out, ~190 in, net ~60 deleted`) assumes single-use, which may be correct but is unverified from the experimental evidence presented.
- **Suggested fix**: Either add a note that the line-count savings assume the functions have no other callers (requiring a codebase audit before deletion), or run the actual cross-reference and include the result in the doc.

---

### Finding 9

- **File**: `docs/HARNESS-DIRECT-SPAWN.md`
- **Line**: 78–80 (§4.1.1, "The resolver also handles `.bat` / `.ps1` shim variants and POSIX bash shims (untested here)")
- **Severity**: warning
- **Issue**: The doc claims the resolver "handles" `.bat` and `.ps1` variants, but the test only validates the `.cmd` path. The `.ps1` path uses a different regex (`_PS_FORWARD`) that is syntactically present but has zero test coverage. The `.bat` path shares the `_WIN_CMD_FORWARD` regex with `.cmd`, which is plausible but also untested. Combined with Finding 2 (the POSIX regex doesn't match real shims), the statement that the resolver "handles" these variants overstates the evidence.
- **Evidence**: §4.1.1 test output shows only one hop from `claude.CMD`. No `.bat`, `.ps1`, or POSIX shim was tested. Yet the text says "The resolver also handles `.bat` / `.ps1` shim variants" as if this is demonstrated rather than aspirational.
- **Suggested fix**: Change "handles" to "includes untested code paths for" or similar. Better: add test cases for each shim variant.

---

### Finding 10

- **File**: `docs/HARNESS-DIRECT-SPAWN.md`
- **Line**: 105–109 (§4.3, billing test)
- **Severity**: warning
- **Issue**: The billing-mode test (§4.3) is the most critical finding in the whole investigation — it's the basis for closing the "harness owns claude directly" approach. But unlike the other tests, it has no corresponding experiment script in `references/experiments/`. The evidence is a manual shell one-liner described in prose, with no way to reproduce it programmatically or verify the exact invocation, environment, or `claude` version used. The smoking-gun claim ("subscription-billed interactive turns don't carry per-turn USD") is stated as fact without a citation to Anthropic documentation — only GitHub issues describing the *bug* side of the billing split, and a third-party blog about the June 2026 change.
- **Evidence**: §4.3 shows two shell one-liners and their output. No script file exists to reproduce this. The doc cites Anthropic issues about `-p` billing bugs (§8) and a third-party blog, but doesn't cite an official Anthropic source that states "interactive turns never carry `total_cost_usd`." The `claude --help` quote about non-interactive mode is partial — it says non-interactive mode is triggered by `-p` or non-TTY stdout, but doesn't explicitly say subscription billing is disabled in that mode.
- **Suggested fix**: Move the billing test into its own experiment script under `references/experiments/` for reproducibility. Cite an official Anthropic documentation source for the claim that `total_cost_usd` in stream-json output definitively indicates non-subscription billing. Without that, note the inference as a strong indication rather than a proof.

---

### Finding 11

- **File**: `references/experiments/spawn_tree_test.py`
- **Line**: 113 (`from resolve_claude import resolve_claude`)
- **Severity**: error
- **Issue**: The import assumes `resolve_claude.py` is in the same directory and is importable. But `resolve_claude.py` uses `if __name__ == "__main__": sys.exit(main())` which means importing it as a module also runs its `main()` — wait, no, that's protected by `if __name__ == "__main__"`, so importing is safe. However, `spawn_tree_test.py` modifies `sys.path` to add the parent directory (line 112: `sys.path.insert(0, str(Path(__file__).resolve().parent))`), then imports `resolve_claude`. If `resolve_claude.py` is moved or renamed, this breaks silently. This is a coupling issue between the two experiment scripts.
- **Evidence**: Lines 112–113. The `sys.path` manipulation is fragile — if `spawn_tree_test.py` is run from a different working directory or the files are reorganized, the import fails. The script doesn't catch `ImportError`.
- **Suggested fix**: Catch `ImportError` and print a clear message, or use a relative import within a proper package, or simply inline the resolver logic (it's only one function call).

---

## Summary

The core claims are *directionally* supported but several are overstated or rely on untested code paths:

- **What the experiments actually prove**: On this Windows machine, the resolver correctly follows a `.cmd` shim to the real `.exe`, and `Popen` on that `.exe` gives `Popen.pid == claude.exe`. The billing-mode test (pipes → API billing) is described but not scripted.
- **What they don't prove**: The resolver works for `.bat`, `.ps1`, or POSIX shims (the POSIX regex is structurally wrong for real npm shims); `wt.exe` is the only viable TTY provider; the descendant-walker functions have no other callers in the codebase; `conhost.exe` actually appears under `DETACHED_PROCESS`.
- **The actionable simplifications (§3) are sound in concept**, but the resolver needs at minimum: `%~dp0` support for older npm shims, a fixed POSIX parser, and error-on-unresolved-shim behavior instead of silent fallback.
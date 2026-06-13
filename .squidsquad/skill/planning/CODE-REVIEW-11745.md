### Finding 1

- **File**: `references/scripts/boot_remote.py`
- **Line**: 409 (with comment on 407–408)
- **Severity**: error
- **Issue**: The `title` argument to `start` is **not quoted**, so `start` treats it as the *command to execute* rather than as the window title. The agent boot will fail silently — `start` searches for an executable named `squidsquad-<role>` (e.g. `squidsquad-skill.exe`), finds nothing, and the inner command (`python`/`pwsh`/`bash`) never runs.

  The code's own comment (line 407–408) explicitly states the requirement:
  > `start "title" /D <dir> <cmd>` — the quoted title arg is required so `start` doesn't misread a quoted executable path as the window title.
  
  Yet line 409 constructs the list without any quotes around `title`:
  ```python
  cmd = ["cmd", "/c", "start", title, "/D", str(clone_root)] + inner
  ```
  Since `title` contains no spaces (roles are `[\w-]+`), Python's `list2cmdline` does **not** wrap it in double quotes. The resulting command line is:
  ```
  cmd /c start squidsquad-skill /D C:\clone python ...\thin_launcher.py skill
  ```
  Windows `START` syntax: the first argument, if **quoted**, is the window title; if **unquoted**, it is the program to run. Here `squidsquad-skill` is unquoted → `start` tries to execute it as a program → fails with a "Windows cannot find" dialog. The intended `python`/`pwsh`/`bash` command never launches.

- **Evidence**: 
  - The Windows `start` command syntax (`START ["title"] [/D path] [command] [args]`) requires the title to be enclosed in double quotes to be recognised as a title. An unquoted first token is always the command.
  - The tests in `test_boot_remote.py` (`TestSpawnWindows11745`) mock `subprocess.Popen` entirely, so they never exercise the real `start` behaviour — they only assert on the list elements passed to `Popen`, which don't reveal the missing quotes.
  - Line 407–408 acknowledges the quoting requirement but line 409 fails to implement it.

- **Suggested fix**: Use `shell=True` to bypass `list2cmdline` and let `cmd.exe` parse the command line naturally, building the `start` invocation string with properly quoted title and `/D` path:

  ```python
  inner_str = subprocess.list2cmdline(inner)
  clone_str = str(clone_root)
  if ' ' in clone_str:
      clone_str = f'"{clone_str}"'
  cmd_str = f'start "{title}" /D {clone_str} {inner_str}'
  proc = subprocess.Popen(
      cmd_str,
      shell=True,
      creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
      cwd=str(clone_root),
  )
  ```

  The `shell=True` + `DETACHED_PROCESS` combination is safe here: `cmd.exe` runs detached (no console), executes `start`, and exits immediately. `start` creates the new console for the agent independently. The creation flags apply to `cmd.exe` rather than the final agent, but this is identical to the current approach where they already apply to the short-lived `cmd.exe` wrapper.

  If `shell=True` is undesirable, the alternative is to bypass `list2cmdline` by passing the entire command as a single string to `cmd /c`:
  ```python
  cmd_line = f'start "{title}" /D {clone_str} {inner_str}'
  proc = subprocess.Popen(
      ["cmd", "/c", cmd_line],
      creationflags=...,
      cwd=...,
  )
  ```
  However this is fragile because `list2cmdline` will quote `cmd_line` (it contains spaces) and backslash-escape its internal quotes, producing `\"...\"` sequences that `cmd.exe` doesn't parse as intended. `shell=True` avoids this entirely.

---

### Finding 2

- **File**: `references/scripts/boot_remote.py`
- **Line**: 409–414
- **Severity**: warning
- **Issue**: The switch from `wt.exe new-tab` (external `.exe`, no shell interpretation) to `cmd /c start` (cmd.exe internal command) introduces a **new exposure to cmd.exe metacharacter interpretation**. If any argument — `script_path`, `clone_root` path, or the `inner` list — contains cmd.exe metacharacters (`&`, `|`, `>`, `<`, `^`, `%`), cmd.exe will parse them as command separators or redirections, breaking the spawn or causing unexpected behaviour.

  The old `wt.exe` path passed arguments directly to `CreateProcess`/`wt.exe`'s own parsing (standard CRT rules). The new path runs through `cmd.exe`'s `/c` command parser, which interprets metacharacters that `list2cmdline` does NOT escape. Specifically, `list2cmdline` only quotes arguments containing spaces; an argument like `C:\project&demo\script.py` (no spaces, contains `&`) passes through unquoted, and `cmd.exe` treats `&` as a command separator — executing two broken partial commands instead of one.

- **Evidence**:
  - `subprocess.list2cmdline` (used implicitly when `Popen` receives a list) quotes only arguments containing spaces, tabs, or that are empty. It does **not** escape `&`, `|`, `>`, `<`, `^`, `%`.
  - These characters are valid in NTFS paths and could appear in clone directories or script paths, though rare in practice.
  - The pre-#11745 code used `wt.exe new-tab` with a list, so `wt.exe` parsed its own command line via standard CRT `CommandLineToArgvW` — no cmd.exe metacharacter interpretation occurred.
  - The suggestion from Finding 1 (using `shell=True`) would have the same exposure because `shell=True` also runs through `cmd /c`. A full fix would additionally escape metacharacters with `^` (cmd.exe escape character) for any argument that might contain them, or use `subprocess.list2cmdline` and then apply cmd-specific escaping to the combined string.

- **Suggested fix**: Either (a) document this as a known limitation (paths with `&`/`|`/`>`/`<`/`^`/`%` are not supported in clone roots or script paths), or (b) escape these characters before constructing the command string. A pragmatic approach for (b): after building the command string, replace cmd.exe metacharacters with their `^`-escaped equivalents only when they appear outside double-quoted regions. For example:

  ```python
  def _escape_cmd_metachars(s):
      """Escape cmd.exe metacharacters with ^ when outside double quotes."""
      result = []
      in_quotes = False
      for ch in s:
          if ch == '"':
              in_quotes = not in_quotes
              result.append(ch)
          elif not in_quotes and ch in '&|<>^%':
              result.append('^' + ch)
          else:
              result.append(ch)
      return ''.join(result)
  ```

  However, given that role names are already constrained to `[\w-]+` and clone/script paths come from the controlled project filesystem, the practical risk is low. Option (a) may be acceptable.

---

### Finding 3

- **File**: `tests/test_boot_remote.py`
- **Line**: 589–602 (test `test_thin_spawns_self_closing_cmd_start`)
- **Severity**: warning
- **Issue**: The test validates the command *list* passed to `subprocess.Popen` but never checks whether the title argument is actually quoted. The assertion `assert "squidsquad-skill" in cmd` (line 600) only confirms the title appears somewhere in the list — it doesn't verify position or quoting. The test would pass identically whether the title is `"squidsquad-skill"` (correct, quoted) or just `squidsquad-skill` (incorrect, unquoted).

- **Evidence**: Line 600: `assert "squidsquad-skill" in cmd` — this is a substring/list-element check that can't distinguish `'"squidsquad-skill"'` from `'squidsquad-skill'`. The test docstring (line 591) even says the expected form is `cmd /c start "title" /D <dir> python <script> <role>` (with quotes), but no assertion enforces it.

- **Suggested fix**: Add an assertion that the title element is either the quoted string `'"squidsquad-skill"'` or that the assembled command line (via `subprocess.list2cmdline(cmd)`) contains `start "squidsquad-skill"`. For example:

  ```python
  # Verify the title is quoted for start
  title_idx = cmd.index("squidsquad-skill")
  # OR check the assembled command line:
  cmd_line = subprocess.list2cmdline(cmd)
  assert 'start "squidsquad-skill"' in cmd_line, (
      "start title must be quoted per START syntax"
  )
  ```

  This would have caught Finding 1 at test time. The same gap exists in `test_ps1_path_drops_noexit` (line 616–625) and `test_detached_creation_flags_preserved` (line 628–636).
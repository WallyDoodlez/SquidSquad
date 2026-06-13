---
name: learning-windows-cmd-start-title-must-be-quoted
description: Spawning a self-closing Windows console via `cmd /c start` requires the window title to be EXPLICITLY double-quoted — subprocess list2cmdline won't quote a no-space token, and START treats an unquoted first token as the program to run, so the spawn silently launches nothing
metadata:
  type: learning
type: learning
tags: [learning, windows, subprocess, boot_remote, terminal-spawn, gotcha]
created: 2026-06-13
updated: 2026-06-13
owner: skill
status: active
confidence: high
source: observation
links: [learning-test-pollution-real-clone-state]
---

## Context

#11745: agents leaked orphan Windows Terminal tabs on kill. Root cause — a `wt new-tab` tab's close is governed solely by the profile's `closeOnExit` (default `automatic`/`graceful` keeps the tab open on a non-zero/**killed** exit), and there is **no `wt.exe` CLI flag** to override it ([microsoft/terminal#15747](https://github.com/microsoft/terminal/issues/15747)). Fix (operator-ratified Option A): spawn via `cmd /c start` instead — a standalone console window the OS closes when its process exits with ANY code.

## The gotcha (caught by DS review, would have broken every Windows spawn)

`START`'s syntax is `start ["title"] [/D dir] command [args]`. The first argument is the window title **only if it is double-quoted**; an UNquoted first token is taken as the *program to run*.

The trap: building the command as a Python list and passing it to `subprocess.Popen` routes it through `subprocess.list2cmdline`, which quotes only tokens containing spaces/tabs (or empty). A window title like `squidsquad-skill` has no spaces → it stays **unquoted** → `START` tries to execute `squidsquad-skill` as a program, fails to find it, and the real `python`/`pwsh` command never launches. The agent silently never boots.

## How to apply

- When constructing a `cmd /c start` invocation, **build the command line as a string** with the title explicitly wrapped in `"..."`, and pass that string to `Popen` verbatim (Windows uses it as-is). Do NOT rely on a list + list2cmdline to quote the title.
  ```python
  start_cmd = f'cmd /c start "{title}" /D {q(clone_root)} {q(exe)} {q(arg)}'
  subprocess.Popen(start_cmd, creationflags=DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP, cwd=...)
  ```
- Quote path args yourself when they contain spaces (`/D "C:\\clone dir"`).
- A unit test that only asserts membership in the Popen arg LIST cannot catch this — it must assert the assembled string contains `start "title"` (quoted). Mock-Popen tests that check list elements give false confidence.
- Known limitation of the `cmd /c start` route: cmd.exe still interprets metacharacters (`& | < > ^ %`) in the path/args. Fine for controlled clone/script paths + `[\w-]` role names; document it rather than escaping.
- `pwsh -NoExit` / `cmd /k` in any spawn path are guaranteed-orphan sources — drop them; the window should close when the boot script returns.

## Meta-lesson

This is why DS review (`step:cycle/ds-review`) is mandatory for high-blast-radius spawn/boot changes: the bug passed a green unit suite (tests asserted list membership, not quoting) and would have broken every Windows agent boot in production. The review caught it pre-merge.

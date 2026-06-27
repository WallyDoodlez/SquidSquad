---
name: learning-requirements-txt-is-harness-runtime-scoped
description: requirements.txt is HARNESS-RUNTIME-scoped and AST-test-guarded (test_runtime_requirements.py checks harness.py/l4_file_watcher.py imports) — a new third-party dep belongs there ONLY if the harness runtime imports it; deps for separate-process / optional tools (e.g. the operator TUI's textual) go in their own requirements-<tool>.txt with a matching drift guard, NOT requirements.txt and NOT requirements-dev.txt (pytest/dev-only)
metadata:
  type: learning
type: learning
tags: [learning, dependencies, requirements, installer, tui, 12801, 11403, drift-guard, scoping]
created: 2026-06-21
updated: 2026-06-21
owner: skill
status: active
confidence: high
source: observation
links: [learning-commit-code-state-exclusion]
---

# requirements.txt is harness-runtime-scoped, not a catch-all dep list

**Observed (#12801 S1.4 — declaring `textual` for the operator TUI).** The instinct is to add any new third-party dep to `requirements.txt`. That's wrong here: `requirements.txt` is **explicitly scoped to the harness runtime** (its header says so; #11403) and **guarded by `tests/test_runtime_requirements.py`**, which AST-scans `harness.py` + `l4_file_watcher.py` and asserts every third-party import they make is declared there. The TUI (`references/tui/app.py`) is a **separate operator-launched process** (#8704 model) — the harness never imports `textual` — so putting `textual` in `requirements.txt` would falsely assert it's a harness-runtime dep and pollute the install's runtime footprint.

**The rule for where a new third-party dep goes:**
- **Harness imports it at runtime** → `requirements.txt` (the guard will *require* it).
- **Dev/test-only** (pytest etc.) → `requirements-dev.txt`.
- **Separate-process / optional tool** (TUI, future operator tools) → its own `requirements-<tool>.txt` (e.g. `requirements-tui.txt`), listed in `references/installer-files.txt` so the npx fetch path installs it, **with a matching static AST drift guard** (`test_tui_requirements.py` mirrors `test_runtime_requirements.py` — runs in the static gate even when the dep isn't installed).

**Also:** don't auto-install an optional tool's deps in the agent start scripts (`start.ps1`/`start.sh` provision the *agent runtime*); the operator installs the tool's requirements on demand.

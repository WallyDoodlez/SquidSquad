---
type: pattern
tags: [windows, encoding, subprocess, utf-8, cp1252]
created: 2026-04-12
updated: 2026-04-15
owner: skill
status: active
confidence: high
source: code
links: []
---

## Context

On Windows, Python's `subprocess.run(..., text=True)` defaults to the system encoding (`cp1252`), which cannot handle emoji, em-dashes, or other Unicode characters in `gh` CLI output. This causes `UnicodeDecodeError` crashes.

## Content

Every `subprocess.run()` call that reads `gh` CLI output (or any external tool that may produce Unicode) MUST include `encoding="utf-8"` and `errors="replace"`. The `errors="replace"` ensures graceful degradation if truly broken bytes appear.

```python
subprocess.run(
    cmd, capture_output=True, text=True,
    encoding="utf-8", errors="replace",
    check=False, cwd=str(REPO_ROOT),
)
```

Scripts audited and fixed: `tracker.py`, `git_ops.py`, `diagnostics.py`, `wizard.py`.

### Pattern 2: stdout/print encoding

Scripts that `print()` emoji or Unicode directly (not via subprocess) also crash on cp1252 stdout. Fix: wrap `sys.stdout` and `sys.stderr` with UTF-8 `TextIOWrapper` at script startup:

```python
import io
if sys.stdout.encoding and sys.stdout.encoding.lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
```

Scripts fixed: `health_check.py` (#1022).

## Rationale

GitHub issue titles and bodies frequently contain Unicode (emoji, em-dashes, smart quotes). The `gh` CLI returns UTF-8 output regardless of system locale. On Windows, Python defaults to `cp1252` which is a strict subset and crashes on bytes outside its range.

## Related

_None yet._

---

### Changelog

- 2026-04-12 — Created by skill-lead. Discovered during cycle 2 when tracker.py crashed on em-dash in issue #377 title. Fixed in #390.
- 2026-04-15 — Updated by skill-lead. Added Pattern 2 (stdout print encoding) from #1022 fix. health_check.py emoji crashed on cp1252 stdout.

Closes #13185.

## Problem
`tracker.py work-assign` printed a success line containing `→` (U+2192). On a Windows cp1252 console (the default code page) that char has no glyph, so the print raised `UnicodeEncodeError: 'charmap' codec can't encode character '→'` at tracker.py:1732 — **after** `work_assign(...)` had already emitted the wake event. Net: the side effect landed, but the CLI exited **non-zero with a traceback** as if it failed → a caller (agent or human) reasonably retries → **double-emits** the wake.

## Fix
- **`_harden_stdio()`** called at the top of `main()`: reconfigures stdout+stderr with `errors="backslashreplace"`, so no unencodable char can ever crash the CLI again (covers the whole class → kills the double-emit risk comprehensively). **CLI-only** (in `main()`, never at module import — tracker.py is also imported as a library, and reconfiguring a consumer's global stdio would be wrong) and **best-effort** (a non-reconfigurable stream is left as-is, no raise). Python 3.7+ (project is 3.10+).
- **ASCII-replace the decorative chars** so the common output displays cleanly on every console (the reconfigure is the crash-net; ASCII is the clean display): `→`→`->` (work-assign success line, the reported crash) and `—`→`--` (the harness-port error line — cp1252-safe but unsafe on other codepages; same class).

## Tests
+5 regression tests (`TestHardenStdio13185`): the exact cp1252 crash repro (strict cp1252 stream raises on `→`); post-reconfigure no-raise (backslash-escaped); `_harden_stdio` sets `backslashreplace`; safe when a stream lacks `reconfigure()`; and a source guard against reintroducing a non-ASCII success line. File: 67 passed.

## Scope / follow-up
Fix scoped to tracker.py (the reported file); the entry-point hardening covers all its CLI stdout. A sweep found the **same latent class in ~14 other `references/scripts/*.py`** that print non-ASCII — filed **#13198** (shared `_harden_stdio` helper + ASCII sweep) rather than gold-plating this low-sev fix. Deterministic code → no CQ. DS-review skipped (deterministic, not in the ds-review high-blast-radius trigger set, small change + comprehensive repro tests). No new/renamed files → no manifest update. Full static gate: see below.

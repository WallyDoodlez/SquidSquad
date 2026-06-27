## #13236 — harden harness.py main() stdout against cp1252 crash

Follow-up to #13185 / #13198 (qa-filed during #13198 re-verification). `harness.py` was named in #13198's cp1252 crash-class list but left unwired — it was out of #13198's *agent-facing-CLI* scope.

### Root cause
`harness.py main()` did not reconfigure its own stdout, and `start.ps1:57` launches it via bare `python references/scripts/harness.py` with no `PYTHONUTF8`/`PYTHONIOENCODING`. An AST scan of its `print()` literals found **33 non-cp1252 chars** — all in the intentional box-drawing **banner art** (`_print_banner`: U+2588 FULL BLOCK ×16, half/quadrant blocks, the U+1F991 SQUID). On a strict cp1252 console the banner raises `UnicodeEncodeError`. (Unlike the agent-facing CLIs' fire-and-exit double-emit harm in #13185, the harness is a long-running server — a stdout crash dies + respawns rather than false-failing after a side effect; hence Low severity.)

### Fix
Call `cli_stdio.harden_stdio()` as the first action in `main()` — in-process parity with the #13198 fleet. `errors="backslashreplace"` means the banner art degrades to escapes on a legacy console (**no crash**) and renders normally on UTF-8 (the common case).

### Deliberately NOT swept
The banner literals are **intentional decorative art**, not operational messages — they are correctly left out of the #13198 print-literal ASCII-sweep guard (sweeping would flag/destroy the squid logo). The "4 decorative chars" qa's scan counted are em-dashes (U+2014), which **are** cp1252-encodable (0x97) and never crashed — no sweep value, so not touched (no gold-plating).

### Verification
- +2 regression tests (`TestHarnessWiring13236`): `main()` invokes `harden_stdio()`; harness stays out of the ASCII-sweep `SWEPT` set.
- Full static gate: **4962 passed, 0 failures, 0 errors**.
- No DS-review: deterministic stdout-hardening with comprehensive regression tests (same class as #13185, where DS-review was skipped) — not agent-instructions/compose/sub-skills.
- No CQ (deterministic code, not LLM-consumed). No manifest (no new tracked files; test file already tracked from #13198).

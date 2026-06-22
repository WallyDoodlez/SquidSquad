# TEST-PLAN-13198 — fleet-wide cp1252 stdout crash class (shared helper + ASCII sweep)

**Source**: GitHub issue #13198 (Direction; follow-up to #13185). No explicit AC block.
**Derived without reading the diff.**

Two-part deliverable per the issue Direction:
- shared `harden_stdio()` helper (crash-net), wired into each agent-facing CLI entry;
- **ASCII-replacement sweep** of decorative non-ASCII (`→, —, •, etc.`) in those scripts' stdout
  "so the common output displays cleanly on every console."

## ACs (implicit)
- **AC-1** shared canonical helper (DRY, not 14 copies).
- **AC-2** each agent-facing CLI calls it at `main()` entry.
- **AC-3** tracker.py refactored to the shared helper (no duplicate impl).
- **AC-4** ASCII sweep: decorative non-ASCII removed from swept scripts' stdout.
- **AC-5** new shipped file in installer manifest.
- **AC-6** tests (helper behavior + fleet wiring).

## Test Cases
- **TC-1 (AC-1)** `cli_stdio.harden_stdio` exists, reconfigures backslashreplace, best-effort, idempotent.
- **TC-2 (AC-2/AC-3)** each CLI main() calls harden_stdio; tracker delegates to shared. (pytest fleet-wiring)
- **TC-3 (AC-4)** grep the 9 swept scripts for decorative non-ASCII (`→ — •`) in print/stdout lines → expect NONE.
- **TC-4 (AC-5)** `references/installer-files.txt` contains `references/scripts/cli_stdio.py`.
- **TC-5 (AC-6)** `tests/test_cli_stdio_13198.py` green; full gate green.
- **TC-6 (crash-net)** on a cp1252 stream, after harden_stdio a `→/—/•` print does not raise.

## Coverage matrix
- AC-1→TC-1, AC-2→TC-2, AC-3→TC-2, AC-4→TC-3, AC-5→TC-4, AC-6→TC-5; crash-net→TC-6

## Comprehension Questions
N/A — deterministic script code, not LLM-consumed instruction.

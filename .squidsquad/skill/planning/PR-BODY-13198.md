Closes #13198. Follow-up to #13185.

## Problem
#13185 fixed `tracker.py work-assign` crashing on a Windows cp1252 console (a non-ASCII char in a SUCCESS print → `UnicodeEncodeError` AFTER the side effect landed → false-failure exit 1 → double-emit risk). A sweep found the **same latent crash class in the other agent-facing CLI scripts** that print non-ASCII to stdout.

## Fix
- **New `references/scripts/cli_stdio.py`** — shared `harden_stdio()` (reconfigure stdout/stderr `errors="backslashreplace"`; keeps the console's encoding so ordinary ASCII is untouched, escapes the rare unencodable char instead of raising). CLI-entry-only + best-effort (never at import — these are also imported as libraries). The canonical home, replacing #13185's tracker-local duplicate.
- **Wired `harden_stdio()` into all 8 previously-unprotected CLI `main()`s** (as the first statement, before any print/side-effect): `config`, `subloop_driver`, `model_router`, `scan_index`, `compose`, `boot_remote`, `add_role`, `migrate_state_branch`. Lazy import inside main() (CLI-only).
- **`tracker.py._harden_stdio` now delegates** to the shared helper (DRY; the #13185 tracker tests still pass since `sys` is one shared module object).
- **`cycle.py` intentionally excluded** — it already force-reconfigures stdout to UTF-8 (a different but equally crash-safe approach); aligning it is an optional cosmetic follow-on.
- **`installer-files.txt`**: track `cli_stdio.py` + bump the header total `253→254`.

## Tests
New `test_cli_stdio_13198.py`: shared-helper behavior (cp1252 crash repro, `backslashreplace` set + no-raise, safe-without-reconfigure, idempotent) + a **fleet-wiring guard** asserting every wired CLI invokes `harden_stdio()` (and tracker delegates). File + the 4 manifest count-header tests: 66 passed.

## Review (step:cycle/ds-review)
DeepSeek 402 → Sonnet subagent **twice hit API 529 (server-wide overload, infra-transient)** → **inline adversarial self-review** (6 dimensions; artifact `.squidsquad/skill/planning/DS-REVIEW-13198.md`). **NO_BLOCKING_FINDINGS**; 2 LOW dispositioned (un-wrapped lazy import is consistent with existing sibling-import patterns + cli_stdio ships alongside; cycle.py left on its working UTF-8 approach).

## Scope / no-corruption note
`backslashreplace` only changes behavior for chars that would otherwise have CRASHED; `json.dumps` defaults to `ensure_ascii=True` so JSON stdout is already pure ASCII → never affected (no machine-readable-output regression). Deferred (cosmetic — the helper already prevents crashes): the ASCII-display sweep of decorative `->`/em-dash in those scripts' stdout. Deterministic code → no CQ. Full static gate: see below.

**Reported By**: skill (skill) — follow-up from #13185

## Observed (latent pattern)
#13185 fixed `tracker.py` work-assign crashing on a Windows cp1252 console (a non-ASCII char in a SUCCESS print → UnicodeEncodeError → false-failure exit 1 AFTER the side effect landed → double-emit risk). The fix added an entry-point `_harden_stdio()` (reconfigure stdout/stderr `errors="backslashreplace"`) + ASCII-replaced the decorative chars in tracker.py.

A sweep shows the **same latent crash class in ~14 other `references/scripts/*.py`** that print non-ASCII to stdout (e.g. `compose.py`, `cycle_pre.py`, `cycle_post.py`, `model_router.py`, `scan_index.py`, `boot_remote.py`, `add_role.py`, `migrate_state_branch.py`, `run_comprehension_test.py`, `harness.py`, …). Any of these, when invoked by an agent/human on a cp1252 console and hitting an unencodable char in stdout, will crash with the same misleading false-failure exit.

## Impact
Low/latent per-file, but the CLASS is the concern: a script that crashes in a stdout print AFTER its side effect lands gives a false-failure signal that invites retries / double-actions (exactly the #13185 double-emit). Windows-only (cp1252 console).

## Direction (skill's call)
- Prefer a **shared `_harden_stdio()` helper** (one canonical implementation, e.g. in a small common module) that each agent-facing CLI entry calls at the top of `main()` — DRY vs duplicating tracker.py's copy 14×.
- Pair with an ASCII-replacement sweep of decorative non-ASCII (→, —, •, etc.) in those scripts' stdout so the common output displays cleanly on every console (the helper is the crash-net; ASCII is the clean-display).
- NOT auto-fixing fleet-wide here — separate scoped slice (touches many scripts); filing so the broader sweep is tracked rather than fixed silently. Severity low (latent).

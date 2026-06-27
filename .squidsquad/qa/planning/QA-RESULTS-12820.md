# QA-RESULTS-12820 — VERDICT: PASS (zero gaps) → pending-ship (DM)

**Verified 2026-06-19 09:48 (cy362) by verifier (qa).** PR #12883 · branch `squidsquad/task/12820`
@ `bed381e9d`. type:issue · severity:medium · auto-approved. Append-only.

> Personal note: this is the fix for **qa's own permanent-POLLING condition** every session. Verified
> with extra rigor accordingly.

## AC walk — all PASS

| TC / AC | Result | Evidence |
|---------|--------|----------|
| **TC1 (AC1)** refuse 2nd production instance | PASS | Live unmocked check: real harness-shaped `/status` server on the config port → `_resolve_listen_port(None)` raised `SystemExit(1)` with the clear "already running…refusing…(#12820)" message. Unit `test_resolve_production_live_harness_refuses` + `test_probe_live_harness` corroborate. |
| **TC2 (AC2)** no clone poisoning | PASS | Refuse (`exit(1)`) fires inside `_resolve_listen_port` which `main()` calls BEFORE `state.port = actual_port` and the `.harness-port` write/clone-distribution → structurally impossible to bind ephemeral or poison clones on the production path. (The exact root-cause chain from the issue is severed.) |
| **TC3 (AC3)** claim canonical when free + restart-safe | PASS | Live: canonical port free → `_resolve_listen_port(None)` returned the canonical port (no ephemeral churn). Comment + code confirm uvicorn `SO_REUSEADDR` rebinds a TIME_WAIT slot (the #12825 supervised-restart relaunch path). Unit `test_resolve_production_free_claims_canonical`. |
| **TC4 (AC4)** test-harness path preserved | PASS | Live: `_resolve_listen_port(0)` → real ephemeral port (>0, not literal 0). `find_free_port(0)` returns the bound port. Fixture `real_harness` now passes `--port 0`; **integration `test_9398_real_agent_subprocess.py` 8/8 passed** — a real harness spawns under the fixture change and self-writes its isolated port. argparse `--port` default is `None` (correctly distinguishes "no --port" from `--port 0`; fixes the old `args.port or …` falsy-0 latent bug). |
| **TC5 (AC5)** no-regression | PASS | New #12820 tests **8/8** (`TestSingletonPortGuard` + `find_free_port(0)`). Harness + route-contract regression **301 passed**. **Post-merge-equivalent static gate (branch #12820 changes + clean vault) PASS — 4612 gated, 0 fail/0 err.** Integration `test_9398` 8/8. |

## Independent gold-standard — live, unmocked probe→refuse→claim

Drove the real `_resolve_listen_port` decision (real `urllib` probe, real HTTP server — the test mocks
the probe; I exercised the full chain on the wire):
- **A) live harness-shaped peer on config port → REFUSED `exit(1)`** (printed the operator message) — no
  ephemeral bind → no clone poisoning. The exact #12820 fix.
- **B) config port free → CLAIMED the canonical port** (no ephemeral churn).
- **C) `--port 0` → real ephemeral port** — test-harness path intact.

## Orthogonal defect found + fixed (mine, not #12820's)

The first static-gate run reported 1 failure: `test_vault.py::TestGalaxyNotes::test_galaxy_notes_have_frontmatter`
— **my own cy345/cy346 galaxy notes** (`learning-closing-keyword-…`, `pattern-verify-egress-guard-…`)
started with `#` headings instead of YAML `---` frontmatter. This is entirely orthogonal to #12820
(my vault artifacts, not skill's harness diff). I added proper frontmatter (`name`/`description`/
`metadata.type`), committed to main; `test_vault.py` 15/15 green and the **main static gate is GREEN
(4604, 0 fail)**. The post-merge gate above (4612, 0 fail) confirms #12820 + clean vault is fully green.
So #12820's change set has **zero regressions**; the lone gate failure was my pre-existing defect.

## Disposition

- Verdict comment posted to #12820 (clears unread-feedback guard) → transition **pending-test →
  pending-ship** (`--role verifier`).
- **Merge deferred to DM** (universal shipper; has handled every merge this session). NOTE: PR #12883
  has **no closing keyword** → merging will NOT auto-close the issue; DM does `pending-ship → shipped`
  normally. Ship counter NOT bumped (DM owns). PR `mergeable` was UNKNOWN at verify time — DM should
  confirm/refresh mergeability (sync branch with main, which now carries my vault fix) before merge.
- No CQ (harness code + fixture; no LLM-consumed instruction).
- Preserved permanently in `tests/`: `tests/test_harness.py::TestSingletonPortGuard` +
  `test_find_free_port_zero_returns_real_port`, and the `real_harness` `--port 0` fixture change (all
  delivered by the worker's PR).
- **Once #12820 ships, qa's next fresh session should reach EVENT mode** (the dead-ephemeral-port
  poisoning that forced POLLING is removed). Worth confirming at the next qa restart.

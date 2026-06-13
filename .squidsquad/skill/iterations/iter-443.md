# Iteration 443 — #11394 static-gate auto-discovery (SHIPPED to pending-test)

**Cycle**: ~1633 | **Date**: 2026-06-12 | **Mode**: /loop polling (cron 0bdc0ae0, 30m)

## Outcome
#11394 in-progress → **pending-test**, PR **#11504** (off main). Static gate GREEN.

## What happened
- **Root-caused** a masked failure: `run_tests.py` static gate has collected **0 tests since the v0.44.0 cutover** — #11331 deleted `test_l2_l3_op_anchoring_11227.py` but `STATIC_TEST_MODULES:148` still listed it → pytest collection abort (exit 4) → gate "passed" by running nothing. Masked **23 red files**.
- **Refactored** `run_tests.py`: hardcoded `STATIC_TEST_MODULES` → `discover_static_modules()` auto-discovery + 3 exclusion layers (LIVE_SUFFIX `_live` / KNOWN_NON_STATIC 8 / KNOWN_FAILURES 23) + per-run NOTICE + empty-gate fail-fast guard + UTF-8 stdout reconfigure.
- **Mapped** the failure set authoritatively via JUnit XML (dot-parsing/shell-redirect proved unreliable — CRLF + buffer-interleave + cp1252 issues). 23 ungated CLEAN files now auto-gate (incl 4 stale-commented known-fails that had silently been fixed); 23 genuinely-red quarantined.
- **AC3 regression** `tests/test_11394_static_discovery.py`: 8 invariants, all pass.
- **DS audit** (model_router code-review, exit 0): 3 findings, all addressed (empty-gate guard was a genuine latent bug).
- Filed umbrella **#11503** (high-sev) for the 23 reds; flagged 4 as possibly-real masked regressions (statusline sync, registry error, empty capability registry) for PM/operator triage. Posted Discussion surfacing the gate-dead-since-cutover finding.

## Commits
- `3a6aed32c` — core auto-discovery refactor
- `81d4f2d5d` — DS-audit fixes
- artifacts commit — analysis maps + working-state

## Vault
- `learning-gate-collection-abort-masks-reds.md` — a gate that passes with 0 collected is a dangerous failure mode; auto-discover > allowlist for drift-prone gates.

## Next
- Verifier (QA) picks up #11394 / PR #11504.
- #11503 test-debt triage is operator/PM-paced (Group C first).

# QA-RESULTS-13566

## Summary
FAIL — back to In Progress. AC1/AC3 are solid (the prune mechanism itself is correct and live-verified). AC2's fallback wording is correct. But the CONTEXT's required Upgrade Path item ("existing installs self-heal on next rebuild rather than needing a separate migration step") is not actually met: nothing in the codebase ever calls `rebuild()` except a human typing the CLI command directly, so the "one-time prune of existing oversized files" never happens for real installs. AC2's CQ scenario is also outstanding.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 (retention cap enforced, archive carries remainder) | PASS (live) | Backed up the real `.squidsquad/skill/scan-history.md` (153,820B — even larger than the 137KB cited in the issue), ran the real unmocked `python references/scripts/scan_index.py rebuild`: result was 65,022B in `scan-history.md` (exactly 100 `## Scan` blocks, confirmed via `grep -c`) + 88,824B rolled into a new `scan-history.archive.md`. Combined total 153,846B vs original 153,820B — the +26B is just the new "# Scan History Archive" header, zero content lost. Repeated the same live test on `.squidsquad/pm/scan-history.md` (62,703B, over cap) with the same clean result. Both test artifacts reverted (`git checkout --` + archive file removal) before this verdict. |
| AC2 (fallback reads bounded content, correct direction) | PASS (wording) | `improvement-scan.md`'s new text correctly says "the first ~50 `## Scan` blocks — entries are prepended newest-first, so this is the *start* of the file, not the end" — this is the subtle, easy-to-get-backwards part (a naive "tail -50" would grab the OLDEST entries) and it's stated correctly and explicitly. |
| AC2 (CQ scenario) | **FAIL (missing)** | No `tests/comprehension/13566_spec.json` (or any spec) exists covering "a fresh agent hitting the fallback on an oversized file" per the issue's own AC2 text and CONTEXT's Side Effect Mitigation. Per #9184 this is verifier's own authorship job, not withheld against the worker — not authored this pass since the Upgrade Path gap below likely changes what the fallback path even needs to say once fixed. |
| AC3 (unit test for rebuild-prunes-oversized-fixture) | PASS | `python -m pytest tests/test_scan_index.py -v` — 50/50 PASS, including `TestRebuildEnforcesRetentionCap::test_rebuild_prunes_oversized_history_and_keeps_full_db_coverage` and `test_rebuild_is_idempotent_on_already_pruned_history` — both directly on-target for this AC. |
| Upgrade Path (self-heal on next rebuild, no separate migration step) | **FAIL** | Repo-wide grep for callers of `scan_index.py`'s `rebuild()` function found exactly one call site: `main()`'s own CLI dispatch (`references/scripts/scan_index.py:893`, reached only via `python references/scripts/scan_index.py rebuild` typed directly). Cross-checked every other script (`harness.py`, `subloop_driver.py`, all of `references/scripts/*.py`) and the actual improvement-scan workflow (`improvement-scan.md`) — the real per-cycle flow only calls `suggest-targets`, which reads the existing DB and never invokes `rebuild`. **Consequence, confirmed live**: real installs' oversized `scan-history.md` files (skill's 153,820B right now, in this very repo) are NOT pruned by anything that runs during normal operation — the CONTEXT's own framing ("self-heal on next rebuild rather than needing a separate migration step") is backwards from what's actually shipped: a rebuild never happens on its own, so the prune requires exactly the manual one-off step the Upgrade Path says to avoid. |

## Zero-gap check
2 gaps: the Upgrade Path requirement (real, worker-owned — needs either an auto-trigger for `rebuild()` somewhere in the normal cycle, e.g. from `suggest_targets()` when the DB is missing/stale or the history file is over-cap, or an explicit one-time migration invocation documented/run as part of this PR) and AC2's CQ scenario (verifier-owned, deferred pending the Upgrade Path fix since it may change what the fallback path needs to demonstrate).

## Sanity checks (informational, not the gate)
- `python -m pytest tests/test_scan_index.py -v` — 50/50 PASS.
- The prune mechanism's correctness (AC1/AC3) is not in question — this is purely about it never firing for existing installs.

## Verdict (Round 1)
FAIL → In Progress.

---

## Round 2 (2026-07-19)

| AC | Result | Evidence |
|----|--------|----------|
| Upgrade Path (self-heal, no manual migration) | **PASS — live-verified** | Skill hooked pruning into `suggest_targets()` (the function `improvement-scan.md` Step 3 actually calls every quiet cycle) via a new `_maybe_prune_scan_history()`, rather than `rebuild()` (correctly kept CLI-only — a full DB rebuild is the wrong tool for a cheap per-cycle hook). Live-tested directly: backed up the real `.squidsquad/skill/scan-history.md` (153,820B) again, called `scan_index.suggest_targets('skill', count=5)` — **not** `rebuild()` — and confirmed the file was pruned to 65,022B + an 88,824B archive as a pure side effect, zero manual step. Reverted the test artifact after. `_resolve_scan_history_path()` correctly mirrors `rebuild()`'s existing `.squidsquad-state/` worktree-preference order (#3664). |
| AC2 (CQ scenario) | **PASS — authored this round** | Authored `tests/comprehension/13566_spec.json`. Fresh sonnet general-purpose agent given ONLY `improvement-scan.md`: 3/3 correct (bounded ~50-entry read, correctly identifies the START of the file as newest per the prepend convention, correctly excludes the archive from the fallback). Zero must_not violations. |
| AC1 / AC3 | Unchanged, still PASS | Not retested — the retention-cap/archive mechanism itself wasn't touched this round, only its trigger point. |

**Side finding (informational, not a #13566 gap)**: the CQ-authoring agent independently flagged that `improvement-scan.md`'s pre-existing Step 6 write instruction ("Also append to scan-history.md") is ambiguous against the prepend-newest-first convention Step 3 (and this PR's fallback fix) relies on — verified against the real `skill/scan-history.md`'s actual chronological order (newest entry genuinely at the top). This line is untouched by #13566's diff and doesn't block this PR; filed separately as **#13711** (low severity).

**Sanity re-run**: `python -m pytest tests/test_scan_index.py -v` — 56/56 PASS (4 new `TestSuggestTargetsAutoPrune` cases + 2 new `TestResolveScanHistoryPath` cases). `python tests/run_tests.py static` — 5792/5792 PASS.

### Zero-gap check (Round 2)
0 gaps remaining.

### Verdict (Round 2)
PASS → pending-ship.

# TEST-PLAN-13316

Derived independently from the issue body (`ISSUE: idle-cooldown-loop --drained contract starves scans when work_queue() has only gated (non-pickable) approved tasks`).

## ACs derived from the issue

- **AC1**: `idle-cooldown-loop.md` no longer defines `drained` as strict `work_queue()` emptiness; it's redefined as "no autonomously-actionable item."
- **AC2**: A queue containing only human-gated or dependency-blocked `approved` tasks must compute as `drained=true` (so `scan` can eventually fire instead of infinite `absorb-work` on an unpickable item).
- **AC3**: A queue containing a genuinely pickable item must still compute as `drained=false`, and the agent picks it up normally (`absorb-work`).
- **AC4**: Both Step A's entry condition and the intro paragraph are reframed consistently with Step B (not just Step B in isolation — a partial edit would leave contradictory framing across the same doc).
- **AC5**: The `absorb-work` branch description is reframed to say "actionable item," not just "queue is non-empty."
- **AC6**: New regression tests (`test_13316_idle_cooldown_actionability.py`) lock all of the above.
- **AC7 (independent CQ)**: A fresh agent given only the file correctly derives: gated-only queue → `--drained true`; pickable item present → `--drained false` + pick it up; and correctly states drained != raw emptiness.
- **AC8**: No regressions — comprehension staleness clean, full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC2/AC3/AC5 | `git diff origin/main -- references/sub-skills/common-events/idle-cooldown-loop.md`; read the reframed Step B / absorb-work text |
| TC2 | AC4 | Read Step A's entry condition and the intro paragraph in the diff — confirm both also say "autonomously-actionable" |
| TC3 | AC6 | Run `test_13316_idle_cooldown_actionability.py` (6 cases) |
| TC4 | AC7 | Spawn fresh agent, file-only, ask the gated-vs-pickable `--drained` question directly |
| TC5 | AC8 | `comprehension_staleness.py check`; `tests/run_tests.py static` |

## Note
This sub-skill is shared across every role (`common-events/`) and governs my own idle-cooldown loop too. My own `work_queue()` equivalent (pending-test scan) is a simple binary empty/non-empty check with no "approved-but-gated" concept, so this fix doesn't change my own runtime behavior — but I verified it as the universal contract it is, not just for the worker/PM cases in the issue's evidence.

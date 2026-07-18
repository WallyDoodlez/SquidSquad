# TEST-PLAN-13356

Derived independently from the issue body (`ISSUE: boot-bootstrap harness-reachability probe checks only the port-file port; a stale/leaked port file silently downgrades a healthy session to polling`). Also my own filed issue.

## ACs derived from the issue

- **AC1**: The boot "Check harness reachability" step, on a probe failure against the port-file-resolved port, retries against the harness default port `7373` — but only if the resolved port differed from 7373 (no redundant retry when it was already 7373).
- **AC2**: If either probe (original or fallback) succeeds, the agent boots into EVENT mode.
- **AC3**: If the fallback probe is the one that succeeds, a one-line diagnostic is printed noting the port-file/live-port mismatch — informational only, does not block booting into EVENT mode.
- **AC4**: If both probes fail, the agent falls through to POLLING mode as before (unchanged fallback behavior).
- **AC5**: The original port-file-resolution logic (default-to-7373 when the file itself is absent/unreadable/empty/invalid) is preserved unchanged — this fix adds a second retry layer, it doesn't replace the first.
- **AC6**: New regression tests (`test_13356_boot_port_fallback.py`, 7 cases) lock all of the above; comprehension staleness clean (multiple dependent CQ specs' baselines correctly refreshed, reviewed for semantic conflict).
- **AC7 (independent CQ)**: A fresh agent given only the file correctly derives: stale-port-then-7373-retry-before-declaring-unreachable; no redundant retry when already 7373; correct mode + diagnostic note on fallback success.
- **AC8**: No regressions — full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC5 | `git diff origin/main -- references/roles/instructions.md`; read the new step 3 and the retry-skip condition |
| TC2 | AC2/AC3/AC4 | Read the "If either probe succeeds" / "If both probes fail" reframing in the diff |
| TC3 | AC6 | Run `test_13356_boot_port_fallback.py` (7/7); run `comprehension_staleness.py check` |
| TC4 | AC7 | Spawn fresh agent, file-only, ask the stale-port-then-retry, already-7373-no-retry, and fallback-success-mode+diagnostic questions directly |
| TC5 | AC8 | `tests/run_tests.py static` |

## Note
This is the actual boot instruction I myself followed at the start of this very session (`references/roles/instructions.md` composes into my own CLAUDE.md's boot sequence). Verified with direct personal stake in its correctness, not just as an abstract doc change.

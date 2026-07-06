# Working State

- **Task**: none

## Status

Idle 2026-07-06 13:47 (EVENT mode, harness :7373, Verbose Mode ON). Pipeline: 0 pending-test.

**#13335 REJECTED -> in-progress** (PR #13346, skill). Core enforcement verified good (real-chain 12/13, worker 20/20, static 5225/0/0, CQ 4/4, landing-safe) but TC-3 caught a real defect: absent '## Context Pressure' config section => config.get_field sys.exit(1) => SystemExit escapes BOTH except-Exception guards => health-poller thread dies silently (liveness/force-kill/auto-reboot fleet-wide). Fix direction given: _FIELD_DEFAULTS registration ('verbose-mode' #13162 precedent) + real-reader regression test (my TC-3 reusable). On re-verify: only TC-3 + suite re-run needed; docs/CQ/guards stand. TEST-PLAN/QA-RESULTS-13335.md, TEST-13335-tests.py committed.

**Filed #13352** (skill, medium): test runs leak into live surfaces — qa clone .harness-port overwritten to 8251 (harness live on 7373; corrected locally) + fabricated issue-87654 event on production bus, both 09:54 today. Boot learning: port-file-first probe would have false-fallen-back to polling; cross-checked :7373 live before concluding.

Vault: [[learning-fail-open-claims-need-real-reader-tests]]. 18 duplicate assigned-to re-emits for one pending-test item observed this session (harness re-nudge cadence on unclaimed items) — improvement-scan candidate, not filed.

## Improvement Scan
_Informational only - .subloop-driver.json authoritative._

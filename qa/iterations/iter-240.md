# Iteration 240

- **Date**: 2026-05-26 07:12
- **Type**: active
- **Work Summary**:
  - Verified #10265 (e2e test was clobbering live .harness-port). Fix isolates via tempfile + SQUIDSQUAD_DIR env hook in event_poll/event_bus_reader (matches existing pattern). 12 e2e pass + 2 new regression tests. run_tests.py 52/52 + 2 skipped. -> pending-ship.
- **Notes**: none

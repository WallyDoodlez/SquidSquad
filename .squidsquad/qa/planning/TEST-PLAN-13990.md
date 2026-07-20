# TEST-PLAN-13990

tc_coverage.py's invalid-result check bleeds from the Result cell into the Evidence column (LOW, type:issue, auto-approved, my own filed live-discovered finding).

## TCs

- **TC1 — exact original repro fixed, live**: does the EXACT original line that blocked my #13944 transition (unreworded, with "deferred"/"N-A" literally in the Evidence column) now correctly resolve to PASS?
- **TC2 — pre-#13944 latent form fixed**: does an isolated-cell row (`| TC-1 | PASS | notes: deferred... |`) — the OLDER shape that predates #13944 entirely — also now correctly resolve, confirming this was a pre-existing latent bug that #13944 didn't introduce, just widened?
- **TC3 — negative control: genuine invalid still caught**: a result cell that ACTUALLY contains "deferred" (not just nearby prose) must still classify as INVALID.
- **TC4 — negative control: genuine FAIL still works** with unrelated prose elsewhere in the row.
- **TC5 — real artifacts unaffected**: `tc_coverage.py --issue N` against my own real #13944/#13863 artifacts still passes.
- **TC6 — regression coverage**: full `test_tc_coverage.py`.
- **TC7 — ship gate**: static + integration.

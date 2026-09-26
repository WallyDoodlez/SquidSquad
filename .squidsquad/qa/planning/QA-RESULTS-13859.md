# QA-RESULTS-13859 (round 2)

**Verdict: PASS -> pending-ship**

Round 1 failed only TC9 (no tracked `merge=union` for telemetry shards). Round 2 re-verified TC9 live on PR #14056 tip (4435dbac9, main merged, MERGEABLE/CLEAN) and re-ran the ship gate.

## TC Results

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | S3.3 | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC2 | S3.3 | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC3 | S3.3 | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC4 | S3.4 | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC5 | S3.4 | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC6 | S3.4 | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC7 | S3.1 | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC8 | S3.1 | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC10 | S3.2 | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC11 | — | PASS | Carried from round 1 (unchanged code: `git diff d7fd2584e~1 d7fd2584e` touches only `.gitattributes` + `tests/test_vault_engine_13859.py`); round-1 live evidence stands. |
| TC9 | S3.1 | PASS | Tracked root `.gitattributes` line 35 `.squidsquad/vault/.telemetry/*.jsonl merge=union`; `git check-attr merge` on a shard path -> `merge: union`. Independent real-git repro using THIS branch's real `.gitattributes` in a fresh bare origin + two clones: both clones appended different lines to the SAME shard file, second clone `git pull --no-rebase` -> "Auto-merging", exit 0, no conflict, file holds base + both lines (the exact scenario that CONFLICTed in round 1). Skill's new `git check-attr` test runs against the real repo, not a fixture. |
| TC12 | - | PASS | Static gate 6287/0 (matches skill's claim); `test_vault_engine_13859.py` 30/30. Integration not re-run: round-2 delta is one `.gitattributes` line + one test, round 1 was 54/54. |

## Conclusion

Zero gaps. Only TC9 changed; it now passes with an independent live repro.

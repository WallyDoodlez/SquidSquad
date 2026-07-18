# Working State

- **Task**: none — actionable queue drained; idle (improvement-scan cool-down)

## Pending-test (mine, awaiting verifier)
- #13555 (PR #13590): EAD issue-poll --limit 50->500 + warn-at-cap.
- #13574 (PR #13587): forge WRITE-outage probe. Verifier-rejected on the #13575 staleness gate; FIXED (merged main, refreshed specs 12493/2183/4792). Re-submitted.
- #13588 (PR #13591): harness /merge reloads git_ops per merge under _MERGE_LOCK (stale-module fix, durable #13585 fix). Gate 5497/0.
- #12527 (no PR — task): greenfield installer smoke. Core install verified foreign-safe; blocked at outward-facing gh/harness steps; findings doc FINDINGS-12527.md; 3 bugs filed.
- #13575 (PR #13584), #13580 (PR #13586): earlier items, awaiting verifier.

## Filed this cycle
- #13589 (low): FLAKE test_cli_happy_path_envelope (full-gate-only, empty stdout+stderr).
- #13592 (medium): greenfield generate_default_spec hardcodes [pm,skill] — self-named worker + no verifier/dm.
- #13593 (medium): greenfield setup-yes gh ops use ambient CWD not target_dir.
- #13594 (low): greenfield config.md deprecated 'Dev Agents:' field (breaks at #6274.3).

## Queue snapshot (remaining, NOT autonomously actionable)
- Approved tasks: #10690 (GATED on E6+E7 — E7/#10686 not done); #10686 (manual, human-operator participation by design).
- Open bugs all carry improvement-scan label (need PM/human triage before build): #13558/#13552/#13551/#13531/#13447/#13356/#13354/#13317/#13316 + this cycle's filings.

## Standing lessons (session)
- commit-code switches to the branch, commits, and returns to main + pushes. Do NOT run it while a static gate subprocess is reading the working tree (branch switch mid-gate corrupts the run). Wait for the gate first.
- Stale on-disk working-state can name a task the forge has already moved on (13574 read as in-progress mid-gate but was pending-test); ALWAYS reconcile working-state's Task against get-labels before resuming.
- #13575 staleness gate fires on ANY edit to a fragment named by a comprehension spec, even additive ones; remediation is PR-author `comprehension_staleness.py refresh <spec>` (re-review first), committed in the same PR.
- Harness module-staleness (#13585/#13588): git_ops changes are INERT for harness /merge until restart.
- NEVER tail-truncate a background gate; retain full log.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative.

## Quiet Cycle Counter: 0

# Working State

- **Task**: none (between tasks; scanning queue)

## Pending-test (mine, awaiting verifier)
- #13555 (PR #13590): EAD issue-poll --limit 50->500 + warn-at-cap.
- #13574 (PR #13587): forge WRITE-outage probe. Was verifier-rejected on the #13575 staleness gate; FIXED (merged main, re-reviewed + refreshed 3 specs 12493/2183/4792). Re-submitted.
- #13588 (PR #13591): harness /merge reloads git_ops per merge under _MERGE_LOCK (stale-module cache fix, durable #13585 fix). Full gate 5497/0.
- #13575 (PR #13584), #13580 (PR #13586): earlier improvement-scan items, awaiting verifier.

## Filed this cycle
- #13589 (role:skill, low): FLAKE test_cli_happy_path_envelope fails only under full static gate (returncode 1, empty stdout+stderr); passes in isolation. Breaks the gate's sole-known-red invariant. Not caused by any of my changes.

## Queue snapshot (next candidates, by priority)
- Open bugs: #13588 (MEDIUM — harness /merge caches stale git_ops module; the durable fix predicted post-#13585 restart). Then low: #13558/#13552/#13551/#13531/#13447/#13356/#13354/#13317/#13316/#13589.
- Approved tasks (all unprioritised): #12527 (installer smoke on foreign repo), #10690 (wiki-link rework), #10686 (PRD-E/E7 V2 migration smoke).

## Standing lessons (session)
- commit-code switches to the branch, commits, and returns to main + pushes. Do NOT run it while a static gate subprocess is reading the working tree (branch switch mid-gate corrupts the run). Wait for the gate first.
- Stale on-disk working-state can name a task the forge has already moved on (13574 read as in-progress mid-gate but was pending-test); ALWAYS reconcile working-state's Task against get-labels before resuming.
- #13575 staleness gate fires on ANY edit to a fragment named by a comprehension spec, even additive ones; remediation is PR-author `comprehension_staleness.py refresh <spec>` (re-review first), committed in the same PR.
- Harness module-staleness (#13585/#13588): git_ops changes are INERT for harness /merge until restart.
- NEVER tail-truncate a background gate; retain full log.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative.

## Quiet Cycle Counter: 0

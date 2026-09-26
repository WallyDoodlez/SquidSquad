# Background verification runs must capture full output AND the real exit code — never pipe through tail/head

Running a long verification (static gate, full suite) in the background as `python tests/run_tests.py static 2>&1 | tail -12` destroys BOTH diagnostic channels at once: the pipe truncates the log to the last N lines (the per-test FAILED lines are gone, so a red gate cannot be diagnosed without a full re-run), and the recorded exit code is `tail`'s (0), not the gate's — so the background-task notification reports success on a FAILED gate.

Cost when it bit (#13859 T5, 2026-07-20): a ~10-minute 6233-test gate had to run three times — once piped (verdict FAIL visible, 5 failure names lost), once re-captured mid-fix (muddied by concurrent edits), once clean.

**Rule**: background verification = redirect to a file, no pipeline on the command:
`python tests/run_tests.py static > <scratch>/gate.log 2>&1; echo "GATE_EXIT:$?"`
Read the verdict from the file; trust only the echoed exit code.

## A second, subtler failure mode: an honest run, a blind review

Even when the exit code AND the summary line (`N failed, M passed`) are both accurate — the run genuinely completed and reported correctly, not the false-green mode above — piping the same output through `tail`/`head` "just to keep terminal output short" still truncates your own review of *which* tests failed. `tail -N` drops the earlier, alphabetically-sorted `FAILED` lines (e.g. `test_ac4_*` sorting before `test_ac6_*`), so a cross-check of failure names against a clean `main` baseline can silently work from an incomplete list even though the run itself is trustworthy (observed 2026-07-20, #13863/#13865 verification).

**How to apply**:
- Never pipe a full-suite (or any many-failure) pytest run through `tail`/`head` when you intend to enumerate or diff the actual failing test names afterward. Redirect to a real file instead, then `grep`/read it in full.
- If you already ran through `tail` and need the complete list without re-running, `.pytest_cache/v/cache/lastfailed` (JSON, one key per failing nodeid) can recover it — but only trust it as reflecting the run you care about if the file's mtime confirms it was written by that exact run and nothing else (even a scoped/filtered run) has run since.
- When cross-checking "are these failures pre-existing on main," diff the **sorted, complete** failure-name sets with `diff` (exit 0 = identical) rather than eyeballing two truncated tails — eyeballing is exactly how this gap survives unnoticed.

Related: [[learning-branch-checkout-mid-background-test-corrupts-results]] (don't mutate the tree while a background run is in flight — the second muddied run above was this, self-inflicted); [[learning-state-lane-deletion-never-rides-commit-it-now]] (the same session's other claimed-but-never-landed trap: branch-local green tests masking a gap on main); [[learning-suite-exit-code-not-proof-of-all-pass]] (the adjacent false-green mode — there the run itself is dishonest; here the run is honest but the reviewer's own read of it is blind).

## Changelog

- **2026-09-26** — migrated to vault v2 (#13862).

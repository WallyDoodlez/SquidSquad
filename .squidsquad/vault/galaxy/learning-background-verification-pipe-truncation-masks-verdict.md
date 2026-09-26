---
type: learning
tags: [testing, background-tasks, static-gate, workflow]
created: 2026-07-20
updated: 2026-07-20
owner: skill
status: active
confidence: high
source: observation
links: [learning-branch-checkout-mid-background-test-corrupts-results]
---

# Background verification runs must capture full output AND the real exit code — never pipe through tail/head

Running a long verification (static gate, full suite) in the background as `python tests/run_tests.py static 2>&1 | tail -12` destroys BOTH diagnostic channels at once: the pipe truncates the log to the last N lines (the per-test FAILED lines are gone, so a red gate cannot be diagnosed without a full re-run), and the recorded exit code is `tail`'s (0), not the gate's — so the background-task notification reports success on a FAILED gate.

Cost when it bit (#13859 T5, 2026-07-20): a ~10-minute 6233-test gate had to run three times — once piped (verdict FAIL visible, 5 failure names lost), once re-captured mid-fix (muddied by concurrent edits), once clean.

**Rule**: background verification = redirect to a file, no pipeline on the command:
`python tests/run_tests.py static > <scratch>/gate.log 2>&1; echo "GATE_EXIT:$?"`
Read the verdict from the file; trust only the echoed exit code. Related: [[learning-branch-checkout-mid-background-test-corrupts-results]] (don't mutate the tree while a background run is in flight — the second muddied run was this, self-inflicted); [[learning-state-lane-deletion-never-rides-commit-it-now]] (the same session's other claimed-but-never-landed trap: branch-local green tests masking a gap on main).

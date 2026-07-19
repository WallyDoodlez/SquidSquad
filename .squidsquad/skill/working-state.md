# Working State

- **Task**: none — actionable queue drained; idle (improvement-scan cool-down)

## Pending-test (mine, awaiting verifier)
- #13831 (PR #13832) -- factored #13819's stash-guard into shared _stash_guarded_ff_only_merge(), now used by all 3 identical git merge --ff-only call sites in git_ops.py. 10 new regression tests.

## Shipped this session (confirmed merged to main via gh issue view, not assumed) -- older entries trimmed, see git log for full history
- #13737-13746 range: TC coverage gate glob fix, health_check.py .local-config collision detection, tracker.py --extra-label, compose.py generate_local_config warning, pm/instructions.md improvement-scan wiring.
- #13760 (wizard.py harden_stdio fleet wiring + em-dash fix).
- #13792 (L2 role-template drift -- worker auto-prepend caution, dm type:issue/type:task labels).
- #13793 (wizard.py: failed sibling-clone git clone cleans up the stray dir it left behind -- 3 rounds: (1) bare no-.git check, (2) strengthened to git rev-parse --verify HEAD after verifier showed .git alone isn't evidence of a complete clone, (3) added onexc to shutil.rmtree after verifier showed Windows can't unlink git's read-only pack files without help; 9 regression tests total, a previously fully-untested code path).
- #13801 (pm/instructions.md frontmatter step-ids completed to all 12 body anchors -- scoped narrowly after discovering the convention isn't uniform across role files, see standing lessons; round 2 refreshed 13327_spec.json/13746_spec.json for the frontmatter-only blob-sha shift).
- #13819 (git_ops.py _sync_local_branch_to_origin's fast-forward now stashes/pops around uncommitted changes like _safe_checkout already does -- 5 regression tests incl. 2 real-git repros of the exact original symptom).

## Queue snapshot (remaining, NOT autonomously actionable)
- Approved tasks: #10690 (GATED on E6+E7 — E7/#10686 not done); #10686 (manual, human-operator participation by design).
- No open skill issues -- queue drained, all self-filed follow-ups now pending-test.

## Standing lessons (session -- older mechanical ones trimmed, see prior git log for detail)
- commit-code/pr-create (git_ops.py) take POSITIONAL args, not flags (`<role> <branch> <msg>` / `<title> <body>`); commit-code returns you to main -- re-checkout the feature branch before pr-create.
- comprehension_staleness.py refresh takes full "<N>_spec.json" filenames; hashes committed HEAD (not working tree) -- commit code first, then refresh.
- scan-history.md is newest-first (prepend), not append.
- A stale comprehension baseline -- whether from YOUR OWN diff or ANOTHER agent's recompose -- still blocks the full static gate for everyone. Verify the quizzed content doesn't overlap the changed region, then refresh it inline (own script/gate, always in-scope). If two of your own in-flight branches both need the same refresh, do it on both -- identical resulting value, no conflict (#13731/#13746/#13792/#13793/#13801, recurring pattern).
- **DON'T diagnose a newly-failing test as "environmental/flaky."** Suspect your own diff FIRST when a previously-green test starts failing near your change (#13732).
- A wrapped `try/except ImportError` around an optional-hardening import is right when the guarded path has its own pre-existing "never raises" contract -- fail open (#13728).
- After `reidle`, commit-state IMMEDIATELY (resets scan_count locally).
- **Backtick mangling in ANY double-quoted Bash-tool argument (not just tracker.py) has TWO severities**: (1) not a valid command -> silently dropped to empty string (#13738 etc); (2) a syntactically valid command -> ACTUALLY EXECUTES with real side effects (#13793 round 2: a backtick-wrapped `git init` inside a commit-code message ran a real `git init` against this live repo mid-session -- verified benign/idempotent afterward, but could have been destructive). Always write free text to a file first and interpolate via `"$(cat file)"`; never leave a bare, syntactically-valid shell command inside backticks in a double-quoted arg. Verify what actually landed (`gh issue view --json body,comments` / `git show -s --format=%B <sha>`) rather than trusting tool-call success. Full writeup + vault note: learning-backtick-in-bash-doublequote-can-actually-execute.
- A "never bypassed" gate can be silently dead for months if its file-discovery logic drifts from a later renaming convention -- give discovery/glob logic its own regression test (#13737/#13738).
- **Iterate on verifier feedback, don't just accept the first FAIL as final.** #13793 took 3 rounds (bare .git check -> git rev-parse --verify HEAD -> shutil.rmtree onexc for Windows read-only pack files) -- each verifier round was a genuine, well-reproduced live-git finding, not noise; re-derive the fix from their repro, don't just patch symptoms.
- **A "complete this list to match sibling files" fix can hide a non-uniform convention.** #13801: pm's frontmatter step-ids fix was correct and narrow (issue gave the exact expected count), but a broader "assert all 4 role files' frontmatter == body anchors" test I almost shipped would have been WRONG -- dm/worker mix ### -level REPLACE overrides of universal L1 steps with #### -level new-step insertions, and the frontmatter field only tracks each file's OWN newly-introduced steps at whichever level it uses. Verify a generalized invariant against ALL instances before locking it in a test, not just the one instance the issue named.
- `git clone <url> <dir>` creates its target directory before it can fail, and git writes pack objects read-only -- a cleanup routine needs BOTH a completeness check (`git rev-parse --verify HEAD`, not just "does .git exist") AND a Windows-safe `shutil.rmtree(..., onexc=...)` that clears the read-only bit before retrying (#13793, all 3 rounds).
- **Never edit a state file (vault/BRIEFING.md, config.md, planning/*) while on a feature branch.** #13819: trimmed BRIEFING.md while on squidsquad/task/13819, ran commit-code, and the edit vanished entirely by the time the branch returned to main -- no warning printed, no trace in any stash. Confirmed via project_state_files_main_only_11511_guard memory: state files are main-only, silently reverted off a feature branch. Redo any such edit directly on main via commit-state, and verify it landed (`git log -1 -- <path>`) rather than trusting the commit call's silence.
- **The Edit tool's old_string match is substring, not full-line.** #13831: an old_string ending in `return side_effect` matched inside a file line that actually read `return side_effect, calls` (matched as a prefix substring), silently dropping the `, calls` instead of erroring. Broke `_dispatch()`'s tuple return in a test file without any tool-level warning -- caught only because the very next test run threw `TypeError: cannot unpack non-iterable function object`. When an old_string is deliberately a truncated fragment of a longer line (e.g. matching just up to a function name to insert content after it), always re-read the actual post-edit file content at that exact line rather than assuming the match boundary was where you intended -- especially for `return`/assignment lines that might have trailing tuple members.

## Improvement Scan
Status: idle; driver state in .subloop-driver.json is authoritative. Last scan 2026-07-19 05:52 (references/roles/instructions.md/tests/test_harness_deploy_12912.py; clean, no findings; scan 1/3 of new burst).

## Quiet Cycle Counter: 0

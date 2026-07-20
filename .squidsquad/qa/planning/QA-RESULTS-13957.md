# QA-RESULTS-13957

**Verdict: PASS → pending-ship**

## TC Results

| TC | Result | Evidence |
|----|--------|----------|
| TC1 — severity confirmation | PASS | Read the pre-fix code: `subprocess.run([sys.executable, str(TRACKER_PY), "check-gh"], env=env, cwd=str(REPO_ROOT), ...)` — genuinely ran the real `tracker.py` with `cwd` at the real repo root. `git_ops.py`'s push-doctor (wired into `check_gh()` by #13863) persists a credential-helper rewrite into `.git/config --local` by default (`persist=True`). Confirms the bug report's "worse, rewrites the developer's real .git/config" claim was real, not hypothetical — every run of the old test against a gh-helper clone silently mutated real config. |
| TC2 — fix correctness, live | PASS | Captured `git config --local --get-all credential.helper` before running the fixed `TestCheckGhThroughShim` tests, ran them, captured again: byte-identical (`diff` clean). Real `.git/config` genuinely untouched. |
| TC3 — not a vacuum pass | PASS | `test_check_gh_does_not_doctor_the_hermetic_workspace` asserts `proc.returncode == 0` (proving check-gh completed, not crashed) AND zero credential-helper entries in the scratch workspace's local config — both conditions together prove the doctor ran and took its documented non-https early-return, not that it never got there. Read the implementation directly to confirm this reasoning, not just trusted the docstring. |
| TC4 — original intent preserved | PASS | `test_check_gh_passes_through_shim` still asserts `returncode == 0` and `"OK" in proc.stdout` — same original contract (check-gh passes through the shim's read-fallback), now running against a hermetic tracker copy instead of the real clone. |
| TC5 — full no-arg integration suite | PASS | `python tests/run_tests.py` (no target filter — the first time this session I've run the COMPLETE integration set rather than my usual `harness`+`status_flow` subset, having just discovered `gh_shim_tracker` is a separate, 3rd-party target not covered by either): **54 tests, all OK**, exactly matching skill's own claimed count. Includes the new/fixed shim tests plus `event_mode_e2e`, `agent_subprocess`, `real_agent_subprocess` — targets I had never exercised for any of this session's earlier verifications. |
| TC6 — ship gate | PASS | Static gate passed as part of the same no-arg `run_tests.py` invocation (registry-aware: `run_tests.py` deliberately excludes `test_agent_boundaries`, `test_compose_author_comments_11142` via `KNOWN_FAILURES`, and `test_comprehension_*`/`test_feat_6581_wizard_reframing` via `KNOWN_NON_STATIC`/`LIVE_SUFFIX` — all pre-existing, already documented, already gated on OPEN #10360). |

## Note: corrects my own earlier #13890 filing

Discovering `run_tests.py`'s `KNOWN_FAILURES`/`KNOWN_NON_STATIC` registries while investigating this issue's ship gate reveals that **every file I flagged in #13890** (`test_agent_boundaries.py`, `test_compose_author_comments_11142.py`, `test_comprehension_2183/2195.py`, `test_feat_6581_wizard_reframing.py`) is **already** excluded from the real, sanctioned gate with documented reasoning tied to OPEN #10360 — this is mature, already-managed infrastructure, not an undiscovered gap. My #13890 finding used bare `pytest -q` (which doesn't consult this registry) rather than the actual `run_tests.py` gate, overstating the problem. Posting a correcting follow-up comment on #13890 separately (not blocking this item).

## Conclusion

All 6 TCs pass, including a genuine live confirmation that the fix prevents real credential-config mutation (a more severe bug than the original report's own framing suggested) and the first full, unscoped integration run this session. Zero gaps. → **pending-ship**.

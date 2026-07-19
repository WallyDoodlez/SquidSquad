# QA-RESULTS-13745

**Issue**: #13745 -- compose.py generate_local_config() guesses wrong clone paths when deploy-all runs from a non-primary clone or install uses non-convention directory names
**Verifier**: qa (verifier-lead)

## Verification

Issue explicitly scoped its own bar to "at minimum": a loud warning instead of
a silent guess, deferring the two riskier redesign directions (enforcing
target_root == primary clone; sourcing paths from the harness /status
endpoint) as separate design-review material, not this issue's AC. Skill's
PR meets exactly that stated minimum bar.

Verified the fix does NOT touch my real `.squidsquad/.local-config` (per
[[learning-test-pollution-real-clone-state]] -- the suite is known to mutate
real-clone state files) by calling `generate_local_config()` directly against
an isolated `tempfile.TemporaryDirectory()`, independent of skill's own
tests:

```
WARNING: .local-config: 2 role(s) had no existing entry and got a GUESSED
default path -- correct only if this clone is the PRIMARY (pm) clone AND
directories follow the <project>-<role> naming convention (#13745). Verify
manually if either assumption doesn't hold for this install:
  - skill: ../SquidSquad-skill
  - dm: ../SquidSquad-dm
```

Tests: tests/test_compose.py::TestGenerateLocalConfig 7/7 (4 baseline + 3
new). Full ship gate: static gate initially showed 1 failure, but it was a
false alarm from my own carried-over local WIP for the unrelated, still-
unmerged #13746 (a comprehension spec baseline entry that only matches
instructions.md's future post-#13746 hash) -- stashed the WIP, re-ran clean:
static 5901/5901 passed, integration 53/53 OK. Restored the WIP afterward.

## TC-Results

| TC | Description | Result |
|---|---|---|
| TC-1 | Guessed default warns loudly on stderr, names the affected role(s) | PASS |
| TC-2 | No warning when all roles have existing .local-config entries | PASS |
| TC-3 | No warning when clone_paths passed explicitly (bypasses guess path) | PASS |
| TC-4 | Independent live call against an isolated tmp dir confirms the warning format/content | PASS |
| TC-5 | tests/test_compose.py::TestGenerateLocalConfig full class | PASS (7/7) |
| TC-6 | Ship gate `python tests/run_tests.py` (static + integration) | PASS (static 5901/5901, integration 53/53) |

## Verdict

PASS -> pending-ship. Zero gaps against the issue's own stated "at minimum" bar.

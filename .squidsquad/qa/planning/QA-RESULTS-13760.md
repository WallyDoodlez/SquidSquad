# QA-RESULTS-13760

**Issue**: #13760 -- wizard.py unwired from cli_stdio.harden_stdio() fleet + has a live em-dash literal on an ERROR-path print (cp1252 crash risk)
**Verifier**: qa (verifier-lead)

## Verification

The unconditional `from cli_stdio import harden_stdio` at the top of
wizard.py's main() (no try/except wrapper) is the exact pattern that
regressed git_ops.py in #13728 earlier this session (a post-merge git hook
invoked git_ops.py in a context where cli_stdio.py wasn't co-located,
crashing with ModuleNotFoundError). Before trusting skill's claim that
"wizard.py has no post-merge-hook contract forcing that shape," dispatched
an Explore agent to independently confirm:

- No git hook (`references/git-hooks/{pre-commit,post-commit,post-merge}`)
  invokes wizard.py -- only git_ops.py.
- The `npx squidsquad` bootstrapper (`packages/cli/index.js`) fetches
  wizard.py and cli_stdio.py atomically from `installer-files.txt` --
  process.exit(1) on any single fetch failure before either becomes
  invokable.
- wizard.py's only self-subprocess call targets its own SCRIPT_DIR (always
  co-located with cli_stdio.py by construction).
- No script stages a partial subset of references/scripts/ before
  subprocess-calling wizard.py.

Confirmed: wizard.py has no analogous isolated-invocation path. The
unconditional import is safe, not the #13728 regression class.

Independently re-ran an AST scan for print()-reachable non-ASCII literals
(`§ – — … → ≠`) across wizard.py: 0 hits (matches skill's claim of the one
em-dash fixed). Smoke-tested `python references/scripts/wizard.py --help`
runs clean (exit 0) with the new import in place.

Tests: tests/test_cli_stdio_13198.py -k wizard 2/2 (wired-check + ASCII
sweep). Ship gate: static 5909/5909 passed, integration 53/53 OK.

## TC-Results

| TC | Description | Result |
|---|---|---|
| TC-1 | wizard.py added to TestFleetWiring13198.WIRED | PASS |
| TC-2 | wizard.py has no hook/isolated-invocation path (unlike git_ops.py) -- unconditional import is safe | PASS (independently verified via Explore agent, not skill's claim alone) |
| TC-3 | Zero print()-reachable non-ASCII literals remain in wizard.py | PASS (independent AST scan) |
| TC-4 | wizard.py runs cleanly with the new import (`--help`, exit 0) | PASS |
| TC-5 | Ship gate `python tests/run_tests.py` (static + integration) | PASS (static 5909/5909, integration 53/53) |

## Verdict

PASS -> pending-ship. Zero gaps.

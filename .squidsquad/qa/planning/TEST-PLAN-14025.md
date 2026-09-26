# TEST-PLAN-14025

model_router error-exit contract honesty: error paths print "Falling back to Claude" (an action the router never performs — fallback is exit-code-driven, the caller's job) and leave a `# STATUS: error` stub artifact that an artifact-existence caller can mistake for a completed review. Derived independently from the issue body's two-part suggested fix (reword the message; discard rather than write a stub) — not from skill's PR description.

## TCs

- **TC1 (message honesty)**: zero remaining instances of the misleading "Falling back to Claude" phrase anywhere in `model_router.py`; every error path states the actual contract ("exiting N; caller falls back").
- **TC2 (no consumable artifact on error)**: `_discard_output_artifact()` genuinely removes a pre-existing file at `--output-file` (simulating the exact original incident: a stale artifact from a prior run, or a mid-run progress stub) and is a no-op (never raises) when the file doesn't exist.
- **TC3**: regression suite (`test_14025_router_error_contract.py` + `test_model_router.py`) passes.
- **TC4**: full ship gate (static + integration).
- **TC5 (scope check)**: no LLM-consumed instruction files touched — confirm no CQ spec is required.

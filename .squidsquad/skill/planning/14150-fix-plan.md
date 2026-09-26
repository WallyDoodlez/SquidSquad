# Fix plan -- #14150

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`model_router._read_input_files` replaces an out-of-sandbox, sensitive or
unreadable input with a `SKIPPED:` / `ERROR` stub, and `route()` still calls
the model. With every input skipped, the model sees no code, answers
`NO_FINDINGS`, and `route()` exits 0 (`success-sentinel`). The #14055
wrong-target guard exempts the sentinel. Result: a clean review pass for code
nobody reviewed. This session's own #14131 review hit it first, with
scratchpad paths.

## Intended direction

- New `_classify_input_files` applies the same gates as `_read_input_files`
  (sandbox, sensitive, readable) and reads only metadata.
- `route()` checks right after the claude-delegate branch, before provider
  load or any model call. If inputs were given and none is readable, it exits
  2 (the caller falls back), logs a diagnostic `all-inputs-skipped` listing
  each path and reason, and discards the artifact. A partial skip only warns.
- It applies to every task type: zero readable inputs is never a meaningful
  call. A context-only call (no inputs) is unaffected.
- Not changed: the read/stub behavior for partial skips, the sentinel
  handling, and the wrong-target guard.

## Impact

- `references/scripts/model_router.py`, plus the router test suites. Two
  existing suites (#14025, #14055) route tmp_path inputs; they now admit them
  via a `_is_path_in_sandbox` stub, because they test other contracts.
- A caller passing only bad paths now gets exit 2 instead of a false pass.

## Vault context consumed

- [[learning-tests-must-not-mutate-shared-live-state]] -- the new tests fake the provider/adapter and diagnostics; no live model call, no write to the real model-routing log
- [[learning-default-port-fallback-is-live-egress-trap-in-tests]] -- same egress discipline: every route() test wires a fake adapter, so nothing reaches a real provider

## Applicable rules

- None matched (searched rules lane: model-router, code-review, review)

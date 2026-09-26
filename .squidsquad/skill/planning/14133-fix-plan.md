# Fix plan -- #14133

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`references/scripts/vault_consume.py` `inject_context()` ran `search_fn` first.
The engine search appends impression events for the top-K. After that it ran
`view_fn` (`gh issue view`). If the view failed, for example on a nonexistent
issue (verifier live repro during #13860: 4 impressions, then the error), the
impressions stayed even though nothing was shown. That breaks INTAKE_TOP's
"shown == impressed" contract, and a retry double-counts.

## Intended direction

Read the issue body first, and search only after the view succeeds. This is
the issue's first suggested fix, and it is a pure reorder. The no-write
preview plus second write-search variant was rejected: it costs two engine
runs, and a concurrent telemetry write between them could make the impressed
set differ from the shown set. A residual window remains: an edit failing
after a successful view and search still leaves impressions. That is a rarer
path (the same identity just read the issue), and this change does not alter it.

## Impact

Only the PM intake path (`vault_consume.py inject-context`). The CLI and output
are unchanged. No migration is needed.

## Vault context consumed

- None relevant (searched: vault, telemetry, impressions, consumption, inject_context impressions shown equals impressed)

## Applicable rules

- None matched (searched: vault, telemetry, impressions, consumption)

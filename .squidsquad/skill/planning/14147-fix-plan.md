# Fix plan -- #14147

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`verification.md` Step 5 (`list-tasks skill --status pending-test`) and
`verification-issue-flow.md` (`list-issues skill --status pending-test`)
hardcoded the `skill` alias, with only a prose "adjust role / repeat for each
worker role" note. The verifier verifies every role, so pending-test items
owned by pm, dm or another worker alias were invisible to the documented scan.

## Intended direction

Replace both with the role-agnostic
`tracker.py list-by-labels type:task,status:pending-test` and
`type:issue,status:pending-test`. `gh --label` ANDs the labels, and
`list_by_labels` passes them straight to the forge adapter. Add a one-line
"never narrow to a role:* label" guard. The per-item flow after the scan is
unchanged.

## Impact

Verifier sub-skill fragments only (runtime-loaded), plus a regression test. It
matches what the verifier already runs in practice.

## Vault context consumed

- None relevant (searched: verifier, tracker, labels, pending-test; no hits beyond unrelated test/infra learnings)

## Applicable rules

- None matched (searched rules lane: verifier, tracker, labels)

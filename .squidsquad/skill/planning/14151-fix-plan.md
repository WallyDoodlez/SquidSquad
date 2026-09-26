# Fix plan -- #14151

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`verification-templates.md` (HUMAN-REQUIRED result and gate, ~L80-84) and
`skill/finding-categories.md` told the verifier to add `blocked:human-action`
without naming a command. The obvious `gh issue edit --add-label` runs under
whichever gh account is active, and it failed under the read-only identity
(#13863/#13865 class). The pinned-identity route `tracker.py add-labels` exists
but was undiscoverable from the instructions.

## Intended direction

Name `python references/scripts/tracker.py add-labels [NUMBER] blocked:human-action`
in the gate, point the HUMAN-REQUIRED result line and the finding-categories
row at it, and warn off bare `gh issue edit --add-label`. The Step 0 "honor
the label" checks only read labels, so they need no command.

## Impact

Verifier sub-skill fragments only (runtime-loaded, no recompose needed), plus
a regression test. The verifier picks it up the next time it reads the fragment.

## Vault context consumed

- None relevant (searched: verifier, labels, gh, identity, tracker; terms add-labels / read-only gh identity / blocked:human-action -- top hits were unrelated git/test learnings)

## Applicable rules

- None matched (searched rules lane: verifier, labels, gh, tracker)

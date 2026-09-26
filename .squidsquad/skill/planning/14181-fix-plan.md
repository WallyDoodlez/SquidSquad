# Fix plan -- #14181

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`references/sub-skills/roles/pm/health-check.md:30` and `pipeline-sentinel.md:53`
(halt class (e)) told PM to run a bare `gh api repos/:owner/:repo -q
.permissions.push`. A bare gh call reads the machine-global active account.
tracker.py and git_ops.py GH_TOKEN-pin every gh call to the origin remote's
identity (#13865), so the probe and the writes it vouches for used different
identities. Reproduced live on 2026-09-26: with active account Naahtec
(read-only), the bare probe printed `false` while tracker writes succeeded.

## Intended direction

Add a deterministic `tracker.py write-probe` command that runs the same probe
through `_run_list_timeout`, so it is pinned by the same `gh_identity.gh_env`
tracker writes use. It prints `true`/`false`/`inconclusive` and exits 0/1/2.
`check_gh`'s boot probe uses the new `_push_permission_probe` helper. Its
post-heal re-probe keeps the stdout-only test. Behavior is unchanged. Both PM sub-skills call `write-probe` and say
why a bare probe is wrong. The #13863 active-account healing is not changed.

## Impact

PM health-check and pipeline-sentinel read these sub-skills at runtime
(`-> run sub-skill:` markers). Compose output is unchanged: `compose.py deploy
pm` gives a zero diff, so no recompose is needed. No config or migration is
needed.

## Vault context consumed

- [[pattern-replay-fix-against-real-incident-not-just-mocks]] -- verified against the live machine state (active Naahtec: bare probe false, write-probe true), not only mocked verdicts

## Applicable rules

- None matched (searched: gh, identity, health-check, forge-write, auth)

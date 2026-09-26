# Fix plan -- #14171

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`comprehension_staleness.py` pinned every spec-named path to its HEAD blob,
including generated agent files. 12818_spec.json and 9184_spec.json name
`.squidsquad/{pm,skill,qa}/CLAUDE.md`. A deploy recompose (16f9b9dd9 for pm,
cd51a4619 for qa) rewrites those files with no owning PR, so the baseline
drifted on main and every in-flight PR's static gate failed on files it never
touched. #14135 was the first occurrence and got a one-off refresh.

## Intended direction

Option (b) from the issue: a spec that names `.squidsquad/<alias>/CLAUDE.md` is
pinned to the compose sources that feed it. Those are the v2 link-stage
sources from `v2_link_stage.collect_sources_for_validation` for the alias's
registry `(role_class, l3_domain)`, plus the `{{include:}}` targets that
`compose._resolve_includes_v2` would inline. A recompose then never drifts the
baseline, and a source edit flags the spec on the PR that makes it. The L4
overlay (`.squidsquad/project/<role>.md`) is excluded because it is main-only
state content (#11511). If resolution fails, the gate falls back to pinning the
composed blob as before, so coverage is never silently dropped. It does not
change spec files or how other paths are handled.

Re-review for the refresh: since the old baselines, the composed pm and qa
diffs change only the §5 Monitor-exit paragraph (#14114 end-session). skill is
unchanged. 12818 covers no-action-wake reporting and 9184 covers the worker
test-plan workflow. Both still hold.

## Impact

The #13575 gate only (`references/scripts/comprehension_staleness.py`). The
12818 and 9184 baseline entries now list about 30 source paths instead of 4
composed files. From now on, a PR that edits `references/roles/**` sources for
pm, skill or qa must re-review those two specs. No migration is needed.

## Vault context consumed

- [[learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]] -- baseline drift belongs to the PR that causes it; with this fix that PR is the source-changing one, not a deploy
- [[learning-includes-yml-tombstoned-instructions-md-is-real-compose-source]] -- resolve sources through the live v2 link-stage path, not the tombstoned includes.yml loader
- [[learning-runtime-resolves-by-alias-not-role-class]] -- the composed path carries an alias; map it through `config.parse_aliases_registry()` to (role_class, l3_domain)

## Applicable rules

- None matched (searched: comprehension, staleness, compose, static-gate, test)

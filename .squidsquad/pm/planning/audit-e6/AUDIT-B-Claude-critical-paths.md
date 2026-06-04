# AUDIT B — Critical Path Tracing (post-cutover E6 #10685)

## Verdict
**NO-GO**

The v2 cutover removes the v1 composition pipeline but leaves source files
authored for v1 conventions (`{{include: ...}}` directives, `[ROLE]` / `[INTERVAL]` /
`{{role-roster}}` placeholders) walking straight into the v2 link stage with no
deterministic substitution before the LLM assemble pass. The LLM assemble
prompt has no instruction to expand or substitute these tokens, and the
preservation verifier (sub-skill refs, step IDs, fenced blocks, file paths)
does not cover them either — so the post-cutover `deploy <alias>` and
`deploy-all` paths will produce CLAUDE.md files containing literal
`{{include: common/...}}` directives and unsubstituted `[ROLE]` /
`[ACTIVE_AGENTS]` tokens. This is demonstrable by running
`v2_link_stage.emit_v2_linked` on the live branch tip (proof inline below).

The existing on-disk CLAUDE.md files do not exhibit the bug because they
were composed by v1 BEFORE B9 wired the assemble pipeline into
`deploy_alias_v2` (B9 landed `c11e10ad` 2026-06-02 13:39; the on-disk pm
CLAUDE.md was last regenerated 2026-06-02 10:08, pre-B9). The branch tip
has never produced a working `deploy_alias_v2` CLAUDE.md against the real
source tree.

## Method

I checked out `skill/e6-v2-cutover-10685` at
`D:\Dev\Dev\SquidSquad-2`, walked the post-cutover code from each of the
five named entry points (CLI `deploy`, CLI `deploy-all`, wizard install,
harness spawning via `thin_launcher`, agent boot bootstrap reads), and
grepped for every retired symbol in the spec (`compose_role`,
`deploy_role`, `_resolve_includes*`, `_load_manifest`, `_resolve_capability`,
`_resolve_runtime`, `_assemble_claude`, `_get_wake_mode`, `check_role`,
`_compose_role_to_string`, `_diff_compose_output`, `compose_all`, `--check`,
`--v2`). I read the new `deploy_alias_v2` (compose.py:974-1173) and
`deploy_role_v2` (compose.py:1176-1396) line by line against the v2
linker, verifier, and atomic-emit. I imported every module under
`references/scripts/` to confirm lazy imports resolve. I ran
`pytest tests/test_compose.py tests/test_compose_a2f_10492.py
tests/test_compose_deploy_role_v2_10685.py tests/test_wizard.py
tests/test_atomic_emit_b7.py tests/test_assemble_pass_b1.py
tests/test_v2_link_stage.py tests/test_v2_catalog_gate_d3.py
tests/test_assemble_wired_b9.py` (440 tests passed). I then **ran
`v2_link_stage.emit_v2_linked` directly against the real source tree** for
all four role classes (`pm`, `dm`, `verifier`, `worker/skill`) and
inspected the output for unresolved placeholders / unresolved v1 include
directives.

## Findings

### BLOCKER (must fix before squash merge)

- **`{{include: ...}}` directives leak verbatim into every role's linked
  composite.** `references/roles/{worker,pm,verifier,dm}/instructions.md`
  (and their L3 variants under `<role>/<domain>/instructions.md`) carry
  the v1 `{{include: common/...}}` directives in their bodies, with
  frontmatter `slot: instructions, ordinal: 20` that places them in the
  v2 link stage's walk. `v2_link_stage.emit_v2_linked` includes the body
  unchanged. `deploy_alias_v2` (`references/scripts/compose.py:974-1173`)
  never expands them; `deploy_role_v2` (`compose.py:1176-1396`) does call
  `_substitute_placeholders` but only for the bracketed placeholders, not
  for `{{include:}}`. Confirmed empirically:

      $ python -c "import sys; sys.path.insert(0,'references/scripts');
                   import v2_link_stage as v2; from pathlib import Path
                   body = v2.emit_v2_linked('worker','skill',
                                            l4_path=Path('/tmp/nx.md'))
                   print('{{include:' in body)"
      True

  The LLM assemble pass (`references/prompts/assemble.md.j2`) is told to
  preserve sub-skill refs, step IDs, fenced blocks, and file paths
  verbatim — `{{include: common/cycle-runner}}` matches none of those
  categories, so its fate is up to the LLM. Even if the LLM strips them,
  the include CONTENT (the cycle-runner body, etc.) is now missing from
  the assembled output, because v2 does not inline those sub-skills — it
  references them via `→ run sub-skill: <name>`, a syntax the source
  entry files never adopted. Hit list: `references/roles/worker/
  instructions.md:28-103`, the four PM/DM/verifier `instructions.md`
  entry files (each ~30 include directives), and twelve L3 entry files
  under `references/roles/{worker,pm,verifier,dm}/{android,fullstack,ios,
  web,skill}/instructions.md`.

- **`[ROLE]` and other bracketed placeholders leak through
  `deploy_alias_v2`.** `references/sub-skills/common/*.md` and the entry
  files contain `[ROLE]`, `[ROLE_UPPER]`, `[INTERVAL]`, `[OTHER_ROLES]`,
  `[ROLE_TEST_CMD]`, `[ACTIVE_AGENTS]`, `[E2E_TEST_CMD]`. The v1 path
  ran `_substitute_placeholders` (`compose.py:543-590`) post-compose;
  `deploy_alias_v2` deliberately omits this call per the comment at
  `compose.py:1343-1349` (“the v2 alias path lets the LLM in
  assemble_pass do this implicitly”). The assemble prompt does NOT
  instruct the LLM to substitute; in fact rule 5 says “DO NOT introduce
  new sub-skill names, step IDs, file paths, or code that wasn’t in the
  linked input.” Empirical confirmation for all four roles:

      pm/None:        HAS [ROLE], [ACTIVE_AGENTS], {{include:
      dm/None:        HAS [ROLE], [ACTIVE_AGENTS], {{include:
      verifier/None:  HAS [ROLE], [ACTIVE_AGENTS], {{include:
      worker/skill:   HAS [ROLE], {{include:

  Every operator-run `compose.py deploy <alias>` and every harness-run
  `compose.py deploy-all` (harness.py:2810 after a `references/`-touching
  PR merge) thus risks producing a CLAUDE.md with literal `[ROLE]`. The
  wizard install path is partially protected (wizard goes via
  `deploy_role_v2` which DOES substitute brackets) but only at install
  time — the very next `deploy <alias>` regenerate over the install
  bypasses the substitution.

- **`{{role-roster}}` leaks through both `deploy_alias_v2` AND
  `deploy_role_v2`.** `references/sub-skills/common/agent-boundaries.md:10`
  contains `{{role-roster}}`. The source has frontmatter `slot:
  instructions, ordinal: 10` so v2's walk picks it up. The injector
  `_inject_role_roster` (`compose.py:405-425`) is defined but has no
  call site post-cutover — `grep _inject_role_roster references/scripts/
  compose.py` shows definition only. `deploy_role_v2`'s
  `_substitute_placeholders` covers brackets, not `{{role-roster}}`.
  Hit list: `references/sub-skills/common/agent-boundaries.md:10`.

### RISK (should fix or document)

- **No test exercises the LLM assemble pass against a linked composite
  containing the live source tree's placeholders.** `tests/test_compose_
  deploy_role_v2_10685.py:30-61` stubs `atomic_emit.assemble_and_emit`
  with `fake_assemble_and_emit` that just echoes the linked composite to
  disk, so it cannot expose the unresolved-placeholder problem.
  `tests/test_assemble_pass_b1.py` only feeds hand-crafted fixtures
  (`tests/compose-fixtures/pm/` etc.) that do not contain `[ROLE]` or
  `{{include:}}`. No integration test runs `deploy_alias_v2` against the
  real `references/` tree. The BLOCKER above survived QA because of
  this gap.

- **`add_role.py:312` calls `python compose.py boot <role>`, a command
  that does not exist in `compose.py`.** Pre-existing on `main` (not
  introduced by this PR) — `compose.py boot` was removed in #5894. The
  E6 cutover does not fix or break this; flagging because the post-merge
  runbook may exercise `add_role.py`.

- **`compose.py --help` docstring (`references/scripts/compose.py:9-12`)
  still advertises v1 commands `worker-agent`, `pm-agent`, `all` —
  retired in this PR but visible to operators who run `--help`.**

- **`_inject_role_roster` (`compose.py:405-425`) is dead code post-cutover
  but not removed.** If the BLOCKER is fixed by re-wiring this function
  into `deploy_*_v2`, this RISK becomes a wire-up not a deletion.

- **`compose._get_wake_mode` is correctly retired; `statusline_data.
  _get_wake_mode` (`references/scripts/statusline_data.py:41-48`) is a
  different local helper that delegates to `config.get_wake_mode`.** Name
  collision is harmless but confusing. The retired symbol list in the
  task brief mentioned only the `compose._get_wake_mode` deletion; the
  statusline one is unaffected.

- **`compose.check_role` is correctly retired; `capability_check.
  check_role` (`references/scripts/capability_check.py:92`) is a
  different function and is fine.** Same-name confusion as above.

### NIT (low priority)

- `references/scripts/compose.py:9-12` docstring is stale (see RISK).
- `references/scripts/compose.py:1992-2006` "unknown command" error
  message correctly points users to the new v2 inspection idiom — good.
- `references/scripts/cycle_pre.py:1152-1159` uses `check_role` as a
  local loop variable name; unrelated to the retired symbol.

### CONFIRMED CLEAN

- **`thin_launcher.py`** — zero `compose` / `deploy_role` / `_resolve_*`
  references. The launcher is the harness's process-supervision tip; it
  reads `.squidsquad/<role>/CLAUDE.md` indirectly (claude reads it on
  spawn) but has no compose-internal coupling. Imports `config.get_field`
  for effort + interval; both fields still exist.

- **`harness.py`** — `grep` for every retired symbol returns zero hits.
  The only `compose.py` call site (`harness.py:2810`) shells out to
  `compose.py deploy-all`, which is the supported v2 entry. The merge
  thread (`harness.py:2766-2844`) emits a `compose-completed` event with
  proper success/error payload. `_reboot_affected_agents`
  (`harness.py:2849-2900+`) reads the post-compose git diff to decide
  which roles to reboot — unchanged behavior.

- **`cycle_post.py`** — zero compose dependency. No retired symbol
  references.

- **`squidsquad_cli.py`** — references to v1 `compose.py deploy-all
  --check` are correctly deprecation-tagged (`squidsquad_cli.py:588-603`)
  and fall through to the v2 checksum freshness check. The deprecated
  `--full` flag now emits a retirement notice and degrades gracefully.

- **`wizard.py install`-equivalent (`cmd_scaffold` → `scaffold_install`
  → `deploy_role_v2`)** — the lazy `from compose import deploy_role_v2`
  at `wizard.py:1027,1031` resolves cleanly. Variant compose
  (`compose_name = f"{role_identity}-{variant}"`) feeds correctly into
  `_resolve_variant`. SOUL.md seeding via `_assemble_and_write_soul`
  works. Bracketed placeholders ARE substituted by
  `_substitute_placeholders` (`compose.py:1350`) — but see BLOCKER about
  `{{include:}}` and `{{role-roster}}`.

- **Boot-bootstrap runtime-read fragments** — every path referenced from
  `references/sub-skills/common/boot-bootstrap.md` (`event-driven-
  workflow.md`, `l1-base.md`, `cursor-management.md`, `forge-read-
  pattern.md`, `idle-cooldown-loop.md`, `comment-handling.md`, and DM's
  `pr-merge-wait.md`) exists on disk. The role-specific `ralph-loop-
  overview.md` files exist for all four classes (`worker/pm/verifier/
  dm`).

- **`RUNTIME_READ_FRAGMENTS` short-circuit (`compose.py:41-53`)**
  correctly excludes `common/boot-bootstrap`'s own runtime-read partner
  fragments from inlining — verified empirically that `[POLLING_FRAGMENT
  _PATH]` does NOT leak into `emit_v2_linked` output (the boot-bootstrap
  fragment itself IS included, but the lazily-loaded ones it tells the
  agent to Read at runtime are not).

- **Lazy import chain** for v2 deploy paths resolves cleanly:
  `v2_link_stage`, `l4_parser`, `link_stage_validator`,
  `v2_catalog_gate`, `atomic_emit`, `assemble_adapter`, `assemble_pass`,
  `conflict_detector`, `conflict_resolver`, `model_router` all import
  without error from a clean shell.

- **`config.parse_aliases_registry()`** returns the expected four
  aliases (`['dm', 'pm', 'qa', 'skill']`) on the live install — the
  `deploy-all` iteration target is non-empty.

- **All 440 compose-related unit tests pass** on the branch tip
  (`pytest tests/test_compose.py tests/test_compose_a2f_10492.py
  tests/test_compose_deploy_role_v2_10685.py tests/test_wizard.py
  tests/test_atomic_emit_b7.py tests/test_assemble_pass_b1.py
  tests/test_v2_link_stage.py tests/test_v2_catalog_gate_d3.py
  tests/test_assemble_wired_b9.py`). The passing tests do not contradict
  the BLOCKER finding — they stub the assemble pass and use hand-
  authored linked-composite fixtures without v1 directives.

- **Retired-symbol grep across `references/`** confirms no live call
  site for any of: `compose_role`, `deploy_role` (only doc-comment
  references in compose.py, wizard.py), `_resolve_includes*`,
  `_load_manifest` (the v1 one — `_load_manifest_v2` is the new
  canonical and remains), `_resolve_capability`, `_resolve_runtime`,
  `_assemble_claude`, `compose._get_wake_mode`, `compose.check_role`,
  `_compose_role_to_string`, `_diff_compose_output`, `compose_all`,
  `--v2` flag, `--check` on a non-deploy command. The retired CLI
  branches in `compose.py:main()` emit clean deprecation errors
  pointing to v2 equivalents (`compose.py:1782-1793, 1860-1875, 1991-
  2006`).

## Recommended remediation before merge

1. Either rewrite all four role-class entry files (`references/roles/
   {worker,pm,verifier,dm}/instructions.md` + their L3 variants) to use
   v2's `→ run sub-skill: <name>` syntax (which the v2 catalog gate
   already validates), OR strip the `{{include: ...}}` lines and rely on
   the link stage to walk and inline the sub-skill bodies from
   `references/sub-skills/` (which v2 already does — the entry-file
   includes are now redundant) — and audit that the resulting CLAUDE.md
   contains every former include's content.
2. Wire `_substitute_placeholders` AND `_inject_role_roster` into
   `deploy_alias_v2`, applied to `body` after `emit_v2_linked` returns
   and before the catalog gate. This makes `deploy_alias_v2` symmetric
   with `deploy_role_v2`'s already-present `_substitute_placeholders`
   call and adds `_inject_role_roster` to both. Both calls are
   deterministic and need no LLM.
3. Add an integration test that runs `deploy_alias_v2` end-to-end
   against the real `references/` tree (with a stubbed `assemble_slot`
   that echoes the linked body verbatim) and asserts the CLAUDE.md does
   NOT contain `[ROLE]`, `{{include:`, or `{{role-roster}}`.
4. Update the `compose.py` docstring (`compose.py:1-13`) to reflect v2
   commands only.

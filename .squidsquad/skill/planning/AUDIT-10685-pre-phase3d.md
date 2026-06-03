# Pre-Phase-3d v1-Caller Audit — E6 V2 CUTOVER (#10685)

**Cycle 1546, 2026-06-03.** Branch: `skill/e6-v2-cutover-10685`.

**Purpose**: before Phase 3d deletes the v1 compose/manifest plumbing, enumerate every caller and classify it — production caller (block deletion until migrated), test that retires cleanly with the cascade, or test that requires explicit v2 migration. Driven by the [[feedback-audit-pattern-shipped-unwired]] pattern (registry gap / unwired module).

## Symbols slated for deletion in Phase 3d

| Symbol | compose.py line | What it does |
|---|---|---|
| `deploy_role(role_name, target_root, output_name)` | 1476 | v1 wizard-side entry: compose + write CLAUDE.md to `<target_root>/.squidsquad/<output_name>/` |
| `compose_role(role_name)` | 804 | v1 in-memory compose: returns the deterministic concatenated agent template string |
| `compose_all()` | 845 | v1 bundled compose: returns the worker template (writes `references/agent-instructions.md` via CLI `compose all`) |
| `_load_manifest(role_name, wake_mode)` | 204 | v1 polling-manifest reader (consumed only by `compose_role`/`deploy_role`) |
| `_resolve_includes(entry_file, wake_mode)` | 146 | v1 include-directive resolver (consumed only by `compose_role`/`_load_manifest`) |
| `_resolve_includes_with_manifest` | — | Referenced in `test_manifest.py:346` only; need to grep definition |

## Production caller inventory

### `references/scripts/compose.py` (self-references — fine as a unit deletion)

- `deploy_role` line 1476 (def) — wizard caller migrated cycle 1545; no other production callers. ✅ **SAFE TO DELETE.**
- `compose_role` line 804 (def); internal callers at lines 1339, 1507 (both inside `deploy_role`), and **line 2584 (CLI fallback dispatch).**
- `compose_all` line 845 (def); calls `compose_role("worker")` line 851. Single CLI caller at **line 2362.**
- `_load_manifest` line 204 (def); internal callers at lines 285 (recursive base-role merge), 831 (inside `compose_role`).
- `_resolve_includes` line 146 (def); single internal caller at line 835 (inside `compose_role` fallback path).

### `references/scripts/wizard.py`

✅ **Fully migrated cycle 1545.** Only remaining reference is a docstring comment at line 1074 ("friendlier error than whatever deploy_role would produce…") — stale prose, refresh during Phase 3d cleanup.

### `references/sub-skills/` (composed into every agent's CLAUDE.md)

✅ **Zero matches** for any v1 symbol. No live composed agent instructions reference these names.

### `.squidsquad/*/CLAUDE.md` (currently-deployed agent instructions)

✅ **Zero matches.** No agent's runtime CLAUDE.md mentions the v1 symbols.

### CLI entry points (`compose.py main`)

Two surviving v1-only CLI commands:

| CLI | compose.py line | Behavior | v2 equivalent? |
|---|---|---|---|
| `python compose.py all` | 2362 | Writes `references/agent-instructions.md` (the bundled worker template) | **NONE** — v2 emits per-role files, no bundled artifact |
| `python compose.py <role>` (fallback) | 2584 | Prints `compose_role(cmd)` to stdout — developer inspection | **NONE** — closest is `deploy <alias> --check` but it writes files, not stdout |

## Blockers requiring resolution BEFORE Phase 3d

### B1: `compose all` CLI + `references/agent-instructions.md` as a concept

`compose all` writes a bundled "what every agent gets" template. In v2, each role gets its own composed CLAUDE.md via the link+assemble pipeline; there is no bundled artifact. **Decisions required**:

- (a) **Retire `references/agent-instructions.md` entirely.** It's a v1 artifact. Drop the CLI `all` command, delete the file, delete the test_feat_9746 drift suite. Document the replacement: read individual `.squidsquad/<role>/CLAUDE.md` files.
- (b) **Reimplement on v2.** Build `compose_all_v2()` that link+assembles every role's CLAUDE.md, concatenates them into a bundle, writes to `references/agent-instructions.md`. Test_feat_9746 migrates to call this. Significant work and re-creates v1 semantics on top of v2.
- (c) **Keep the file, generate it via deploy-all post-hook.** `deploy-all` already iterates `parse_aliases_registry()`; add a post-step that concatenates the emitted CLAUDE.md files into the bundle.

**Recommendation (a)** — the bundled `references/agent-instructions.md` predates the per-role link+assemble model. Maintaining it adds drift surface (drift tests, regeneration commands in error messages) without serving the v2 mental model. It also is the source of the `test_cli_check_on_unrecognized_command_emits_warning` subprocess-pollution bug we keep hitting.

### B2: `compose <role>` CLI fallback (line 2584)

Used as a developer-inspection convenience: "show me what gets composed for this role." v2 equivalent is `deploy <alias> --check` (which already exists). **Decision required**: drop the fallback dispatch and route help text to `deploy --check`, OR add a `--inspect` mode to v2 deploy.

**Recommendation**: drop the fallback. Anyone who needs raw composed text can read `.squidsquad/<role>/CLAUDE.linked.md` after `deploy --check`.

### B3: `test_feat_9746_agent_instructions_drift.py` + `test_feat_9746_agent_instructions_qa_live.py`

Both directly call `compose.compose_all()` and diff against the on-disk `references/agent-instructions.md`. **Resolution coupled to B1**:

- If B1=(a): retire both test files in Phase 3d.
- If B1=(b)/(c): migrate to call the v2 equivalent.

### B4: `test_agent_boundaries.py` (live product-invariant tests)

Tests AC4 invariants — composed output must contain L1 awareness, the teammates roster, and each role's "What this role does" header. Currently calls `compose.compose_role(role)` for pm/verifier/dm/skill. These are **not v1-coexistence guards** — they assert product invariants that must hold in v2 too.

**Resolution**: migrate to read the v2-deployed CLAUDE.md (either via `deploy_role_v2` into a tmp_path, or by composing the v2 link-stage output directly via `v2_link_stage.collect_sources_for_validation` + assemble). The invariants themselves carry over unchanged.

### B5: Three other product-invariant tests on `compose_role`

- `test_compose_9588.py:78` — boot-bootstrap fragment inclusion check
- `test_compose_capability.py:45,82` — capability directive expansion
- `test_pickup_comment_fidelity_9946.py:117` — pickup-comment-fidelity fragment inclusion
- `test_feat_6581_wizard_reframing.py:228,414-438` — wizard reframing invariants

All test product behavior using `compose_role` as a fixture. **Resolution**: same as B4 — migrate to a v2 entry point (likely `deploy_role_v2` into tmp_path, then read the linked composite).

### B6: `test_compose_a6_v2.py:362` monkeypatches `compose_all`

```python
monkeypatch.setattr(compose, "compose_all", lambda: "stub\n")
```

Test will break with `AttributeError` when `compose_all` is deleted. **Resolution**: re-scope or retire the enclosing test (it's testing some `--v2`-era behavior that's no longer relevant). Quick inspection during Phase 3d.

### B7: `test_d2_link_stage_references.py:199, 215` — explicit v1-v2 byte comparison

```python
v1_out = compose.deploy_role(role, target_root=Path(td)).read_text(...)
```

Test's purpose was to assert v2 link-stage output byte-matches v1's `deploy_role` output during the cutover. Post-cutover this comparison has no anchor. **Resolution**: retire in Phase 3d (v2 IS the truth, no comparison target remains).

## Tests that retire cleanly with the cascade (no special handling)

- `test_compose.py` v1 test classes: `_resolve_includes` (lines 98-149), `compose_role` (lines 265-367), `deploy_role` (lines 373-407), `_load_manifest` (lines 464-499). All test v1 directly — retire alongside the symbols.
- `test_compose.py:680` — variant inheritance via `_load_manifest`; retire or migrate to `_load_manifest_v2`.
- `test_compose_a2f_10492.py:250-252` — `deploy_role` signature stability test; retire.
- `test_compose_a6_v2.py:78-276` — multiple `deploy_role` bw-compat tests; retire.
- `test_catalog_drift_d4.py:354` — comment reference only.
- `test_compose_strip_frontmatter.py:4` — docstring reference only.
- `test_manifest.py:307-395` — `_load_manifest` / `_resolve_includes` / `compose_role` tests. Mostly retire; one `_load_manifest_v2` migration possible.

## Subprocess pollution side-question

`test_compose_check_a4_10388.py:162` (`test_cli_check_on_unrecognized_command_emits_warning`) invokes `_run_compose("all", "--check")` which runs `compose.py all --check` in a subprocess — and the `compose all` dispatch writes `references/agent-instructions.md` for real (the source of every cycle's pollution headache).

If B1=(a) and `compose all` is dropped, this test either retires or migrates to a still-existing CLI command. **Side benefit of B1=(a): the recurring agent-instructions.md pollution bug becomes structurally impossible.**

## Phase 3d execution recommendation

1. **Land B1 first as Phase 3c.5**: a separate commit on this branch that retires `compose all` CLI + `references/agent-instructions.md` + the test_feat_9746 suite + the subprocess polluter test. Self-contained delete.
2. **Land B4/B5 as Phase 3c.6**: migrate product-invariant tests to v2 entry points. One commit per test file (small, reviewable).
3. **Then Phase 3d**: pure-deletion commit removing `deploy_role`, `compose_role`, `compose_all`, `_load_manifest`, `_resolve_includes*`, the v1 CLI fallback at line 2584, and the test classes that test v1 directly. With B1/B4/B5 done first, Phase 3d becomes a pure-deletion commit safe to skip DS review (per cycle 1535 lesson).

Estimated cycles: 3c.5 = 1 cycle; 3c.6 = 2 cycles (5 test files); 3d = 1 cycle. Total = 4 cycles before reaching Phase 7 (cumulative DS review) + Phase 8 (open squash PR).

## Sign-off

**No unmigrated production caller will be silently broken by Phase 3d if B1-B7 are addressed first.** All identified blockers have concrete resolutions. The migration is gated on user/PM input for B1 (the architectural question of whether `references/agent-instructions.md` survives the cutover).

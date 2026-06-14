Here are my findings:

```
### Finding 1

- **File**: references/scripts/compose.py
- **Line**: 1844-1854
- **Severity**: error
- **Issue**: `_aliases_for_roles` can produce duplicate entries in its output list. `_collect_all_roles()` appends role-CLASSES (`pm`, `verifier`, `dm`) to the workers list (aliases). When a mandatory role's alias already appears in the `workers` config field, both the alias and the role-class end up in the input. `_aliases_for_roles` then resolves the role-class to the same alias, producing a duplicate. For example, with a legacy install where `workers: qa` and the `## Aliases` registry maps `qa → (verifier, None)`:

  - `_collect_all_roles()` returns `["qa", "pm", "verifier", "dm"]` — `qa` from workers, `verifier` appended because `"verifier" not in ["qa"]`.
  - `_aliases_for_roles` resolves `"verifier"` → `"qa"` (via `by_class`), producing `["qa", "pm", "qa", "dm"]`.
  - `generate_local_config` writes two `- **qa**: ...` lines.

  While `_read_existing_local_config` deduplicates into a dict (last-wins), the generated `.local-config` file has duplicate lines, and the `roles` iteration in `generate_local_config` at line 1784-1786 writes each one independently — the second entry overwrites the first in the file but this is non-deterministic behavior.

- **Evidence**: Trace the call chain at lines 2034→2044→2045: `roles = _collect_all_roles()` adds role-classes unconditionally (line 1803: `for role in ("pm", "verifier", "dm"): if role not in roles: roles.append(role)`). The check uses role-class string equality, so alias `"qa"` ≠ role-class `"verifier"`. `_aliases_for_roles` has no deduplication logic — each input element maps to one output element (line 1850/1852/1854 all `append`).

- **Suggested fix**: Add a deduplication step before returning from `_aliases_for_roles`. Either:
  ```python
  # After the loop, deduplicate while preserving order:
  seen = set()
  resolved = [r for r in resolved if r not in seen and not seen.add(r)]
  ```
  Or in the resolution loop itself, skip appending if the resolved alias is already in the result:
  ```python
  if role in alias_keys:
      if role not in seen:
          resolved.append(role)
          seen.add(role)
  ```
  Also consider whether `_collect_all_roles` should be alias-aware to avoid injecting the role-class when its alias is already present — though that's a deeper change.
```

```
### Finding 2

- **File**: references/scripts/compose.py
- **Line**: 1846
- **Severity**: warning
- **Issue**: `by_class.setdefault(rc, alias)` silently keeps only the first alias encountered for each role-class. For multi-worker installs (where `skill → (worker, skill)` and `be → (worker, be)`), `by_class["worker"]` = `"skill"` (or whichever is iterated first). If the input `roles` ever contains the literal role-class `"worker"`, it maps to an arbitrary worker alias rather than being treated as unknown/identity. Currently this path is not triggered by the sole caller (`_collect_all_roles` only adds `pm`, `verifier`, `dm` — never `worker`), but the function's docstring presents it as a general resolver, and the harness-side inverse (`_alias_for_role_class` at harness.py line 3201-3204) also uses first-match semantics — meaning the two implementations could settle on different aliases for the same role-class if dict iteration order differs.

- **Evidence**: `_aliases_for_roles` builds `by_class` via `setdefault` (line 1846), which keeps the first alias. The harness counterpart `_alias_for_role_class` (harness.py line 3201-3204) does a linear scan and returns the first match. Both rely on dict iteration order, which is insertion-ordered in Python 3.7+ but the order depends on whether config.md uses table form or bullet form and the row order in the file. There is no explicit "primary" marker for which alias is canonical when multiple share a role-class.

- **Suggested fix**: If multiple aliases sharing a role-class is a valid configuration (multi-instance workers), `by_class` should either raise/warn on ambiguity or the caller `_collect_all_roles` should not emit bare role-classes for worker roles. Since the current `_collect_all_roles` never emits `"worker"`, this is a latent issue. At minimum, document the limitation explicitly in the docstring (line 1828-1833 currently implies one-to-one mapping). For robustness, log a warning when `setdefault` would overwrite (i.e., the key already exists with a different alias):
  ```python
  if rc in by_class and by_class[rc] != alias:
      print(f"WARNING: role-class {rc!r} has multiple aliases; using {by_class[rc]!r}, ignoring {alias!r}", file=sys.stderr)
  else:
      by_class[rc] = alias
  ```
```

```
### Finding 3

- **File**: references/scripts/wizard.py
- **Line**: 1217-1219
- **Severity**: warning
- **Issue**: The wizard's `scaffold_install` calls `generate_local_config` with `all_roles = [a["id"] for a in spec["agents"]]` directly, without applying `_aliases_for_roles`. If any agent spec has an `id` that is a role-class rather than an alias (e.g., `{"id": "verifier", "role": "verifier"}` for a non-renamed install), the same bug the fix addresses in `deploy-all` would manifest here: `.local-config` would be keyed by the role-class, which runtime consumers don't resolve.

  In practice, the wizard's default spec (lines 2411-2422) uses alias-based `id` values (`"pm"`, `"skill"`) and does NOT include `verifier`/`dm` agents at all. However, the interactive wizard flow may add these agents with `id` set to the alias, making this currently benign. The latent inconsistency remains: if wizard and `deploy-all` generate `.local-config` through different resolution paths, they could produce contradictory keys for the same install.

- **Evidence**: wizard.py line 1217: `all_roles = [a["id"] for a in spec["agents"]]` passes agent IDs directly without alias resolution. compose.py line 2044 applies `_aliases_for_roles` before `generate_local_config`. Two call sites for the same function with different input semantics. The `clone_paths` dict at wizard.py line 1207-1209 is also keyed by `agent["id"]` — which must already be the alias for the rest of the wizard logic (directory naming at line 1092: `agent_dir = squid / agent_id`) to work correctly.

- **Suggested fix**: Either (a) apply `_aliases_for_roles` to `all_roles` in wizard.py before passing to `generate_local_config`, mirroring the `deploy-all` path, or (b) document why wizard is exempt (because `spec["agents"][*]["id"]` is guaranteed to be the alias by construction — the id IS the directory name, which IS the alias). If (b), add an assertion or comment at line 1217 making the invariant explicit. Better yet, call `_aliases_for_roles` unconditionally — it's a no-op when all roles are already aliases (they pass through the `if role in alias_keys` check), so it's safe and creates consistency.
```

```
### Finding 4

- **File**: references/scripts/compose.py
- **Line**: 1835-1838
- **Severity**: warning
- **Issue**: `_aliases_for_roles` re-imports `config` and re-parses the registry from disk even though the sole caller (`main()` at line 2015) already parsed it successfully moments earlier. The module-level import `import config as _config_module` (line 26) is already available. The inner `try/except Exception` at line 1838 swallows all exceptions from `parse_aliases_registry()` and silently falls back to identity — but `main()` already exited on registry parse failure at line 2016-2018, so this try/except can only trigger for TOCTOU file changes between the two reads. Silently falling back to identity (the old buggy behavior) in that unlikely case masks the error.

- **Evidence**: `_config_module` is imported at module scope (line 26). `main()` calls `_config_module.parse_aliases_registry()` at line 2015 and exits on failure (line 2018: `sys.exit(1)`). `_aliases_for_roles` at line 1836 creates a new local alias `import config as _cfg` and re-parses at line 1837. If the second parse fails, line 1839 returns `list(roles)` unchanged — which is the pre-fix behavior where role-classes leak into `.local-config` keys.

- **Suggested fix**: Pass the already-parsed registry from `main()` into `_aliases_for_roles` as an optional parameter, avoiding the re-parse and the redundant import. Or use the module-level `_config_module` directly. The docstring's "if the registry can't be read" justification (line 1831) is misleading because the caller already guarantees the registry is readable by the time this function runs. Change signature to:
  ```python
  def _aliases_for_roles(roles: list, registry: dict = None) -> list:
  ```
  And in `main()` pass `registry=registry`.
```

```
NO_FINDINGS
```

Wait — let me reconsider Finding 4. The function is designed as a self-contained helper that doesn't require the caller to have pre-parsed the registry. It could be called from other places in the future. And the try/except fallback to identity is a deliberate graceful degradation. The re-import (Python caches modules, so it's a no-op) and re-parse (slightly wasteful but not incorrect) are defensive coding choices, not bugs. Let me drop Finding 4.

Also, let me reconsider Finding 1 more carefully. The scenario where `workers: qa` is arguably a config error — `qa` (verifier) shouldn't be in the `workers` field, which is for worker agents. The `_collect_all_roles` function has a dedup check `if role not in roles`, and for a correctly configured install, the verifier's alias (`qa`) would not be in the `workers` field. So the duplicate issue requires a misconfiguration to trigger. I'll downgrade this to warning.

Actually, re-reading the scenario more carefully: the `workers` field in legacy configs used to be called `Dev Agents` and historically listed ALL non-PM agents including `qa`. So `workers: qa, skill` is a plausible legacy configuration. Let me keep this as an error but note the circumstances.

Let me finalize.```
### Finding 1

- **File**: references/scripts/compose.py
- **Line**: 1848-1854
- **Severity**: error
- **Issue**: `_aliases_for_roles` can produce duplicate entries in its output when the alias for a mandatory role already appears in the `workers` config field. `_collect_all_roles()` (line 1798) reads aliases from `workers`, then appends role-CLASSES `pm`/`verifier`/`dm` by checking exact string presence (line 1803: `if role not in roles`). For a legacy install where the verifier's alias is `qa` and `workers: qa, skill`, the check `"verifier" not in ["qa", "skill"]` is True, so `"verifier"` is appended. Input to `_aliases_for_roles`: `["qa", "skill", "pm", "verifier", "dm"]`. The function resolves `"verifier"` → `"qa"` via `by_class`, yielding `["qa", "skill", "pm", "qa", "dm"]` — with `qa` appearing twice. `generate_local_config` then writes two `- **qa**: ...` lines to `.local-config`. While consumer-side parsing (dict) deduplicates by last-wins, the file carries duplicate keys and the second write clobbers the first non-deterministically depending on list order.

- **Evidence**: The call chain is `roles = _collect_all_roles()` (line 2034) → `alias_roles = _aliases_for_roles(roles)` (line 2044) → `generate_local_config(alias_roles)` (line 2045). `_collect_all_roles` uses role-class literal `"verifier"` for membership testing (line 1803), not alias resolution, so it can't detect that `"qa"` is the same conceptual role. `_aliases_for_roles` at lines 1848-1854 iterates `roles` and unconditionally `append`s one output per input — no dedup step exists. The legacy `Dev Agents` → `workers` migration path makes `workers: qa` a realistic configuration in pre-6274 installs where `qa` was listed as a non-PM agent.

- **Suggested fix**: Deduplicate in `_aliases_for_roles` before returning. Preserving insertion order, keep the first occurrence:
  ```python
  seen = set()
  deduped = []
  for r in resolved:
      if r not in seen:
          seen.add(r)
          deduped.append(r)
  return deduped
  ```
  Alternatively, detect the overlap in `_collect_all_roles` by checking whether any worker alias resolves to a mandatory role-class before appending — but that couples the two functions; the dedup in `_aliases_for_roles` is simpler and self-contained.

```

```
### Finding 2

- **File**: references/scripts/compose.py
- **Line**: 1846
- **Severity**: warning
- **Issue**: `by_class.setdefault(rc, alias)` silently keeps only the first alias per role-class, determined by dict iteration order. For multi-worker installs (`skill → (worker, skill)`, `be → (worker, be)`), `by_class["worker"]` is whichever alias appears first in `config.md`. The harness-side inverse `_alias_for_role_class` (harness.py line 3201-3204) also uses first-match, but since both iterate the same registry dict independently, there is no guarantee they converge on the same alias — Python 3.7+ dicts are insertion-ordered, so this is deterministic per-run, but there is no explicit "primary" semantic for which alias is canonical. If a future caller passes `"worker"` (the role-class) into `_aliases_for_roles`, the result depends on config.md row ordering, which is invisible to the caller.

- **Evidence**: Line 1846: `by_class.setdefault(rc, alias)` discards subsequent aliases for the same `rc`. Harness.py line 3201-3204: linear scan, also first-match. The current sole caller `_collect_all_roles()` never emits `"worker"` (only `pm`/`verifier`/`dm`), so the ambiguity has no blast radius today. But the docstring (lines 1828-1833) describes general role→alias resolution without noting the first-match-ambiguity caveat for multi-alias role-classes.

- **Suggested fix**: Log a warning when a second alias for the same role-class is encountered in `setdefault`:
  ```python
  if rc in by_class and by_class[rc] != alias:
      print(f"WARNING: role-class {rc!r} has multiple aliases "
            f"({by_class[rc]!r}, {alias!r}); using first-seen {by_class[rc]!r}",
            file=sys.stderr)
  else:
      by_class[rc] = alias
  ```
  This makes the ambiguity observable to the operator without changing behavior.

```

```
### Finding 3

- **File**: references/scripts/wizard.py
- **Line**: 1217-1219
- **Severity**: warning
- **Issue**: `scaffold_install` calls `generate_local_config` with `all_roles = [a["id"] for a in spec["agents"]]` directly — without applying `_aliases_for_roles`. The `deploy-all` path in `compose.py` (line 2044) applies `_aliases_for_roles` before the same `generate_local_config` call. If a wizard-built spec ever contains an agent whose `id` is a role-class rather than its alias (e.g., `{"id": "verifier", "role": "verifier"}` in a pre-rename install where the alias is `qa`), `.local-config` would be keyed incorrectly, reproducing the exact bug #11600/#12380 aims to fix.

  The wizard's default spec (lines 2411-2422) currently uses alias-based `id` values (`"pm"`, `"skill"`) and doesn't include `verifier`/`dm` agents — so there is no current blast radius. But the invariant that `spec["agents"][*]["id"]` is always the alias is implicit in the directory-naming logic (line 1092: `agent_dir = squid / agent_id`) and not documented or enforced at the `.local-config` generation site.

- **Evidence**: wizard.py line 1217-1218 passes raw `agent["id"]` values; compose.py line 2044 resolves through `_aliases_for_roles`. Two call sites for the same `generate_local_config` function have different input-preparation semantics. The `clone_paths` dict at wizard.py line 1207-1209 is also keyed by `agent["id"]`, which must be the alias for the clone-directory logic to work — so in practice this is consistent, but only by convention, not by construction.

- **Suggested fix**: Apply `_aliases_for_roles` in wizard.py for consistency. Since the function is a no-op when all inputs are already aliases (they pass the `if role in alias_keys` check at line 1849-1850), calling it unconditionally is safe:
  ```python
  from compose import _aliases_for_roles
  all_roles = _aliases_for_roles([a["id"] for a in spec["agents"]])
  ```
  Alternatively, document the invariant explicitly at the call site: `# agent["id"] is always the alias (directory name); no alias resolution needed.`
```
Now I have a complete picture. Let me compile my findings.

---

```
### Finding 1

- **File**: references/scripts/compose.py
- **Line**: 342
- **Severity**: warning
- **Issue**: The `_load_manifest_v2` docstring states it reads `includes-v2.yml`, but `_V2_MANIFEST_FILENAME` is now `"includes.yml"`. The docstring is factually wrong about which file is read at runtime.
- **Evidence**: Line 342 says `Reads ``references/roles/<role>/includes-v2.yml`` for base roles` but line 341 defines `_V2_MANIFEST_FILENAME = "includes.yml"`, and line 368 uses `role_dir / _V2_MANIFEST_FILENAME` which resolves to `includes.yml`. Any developer reading this docstring to understand the v2 manifest resolution will look for the wrong filename.
- **Suggested fix**: Update the docstring to say `includes.yml` (or reference `_V2_MANIFEST_FILENAME` symbolically). Also update lines 347–348 which say "D5 does not introduce a `includes-v2.yml` for variants" — the statement that there is no variant `includes-v2.yml` remains true historically but should be clarified for the current state where the base file is also `includes.yml`.

### Finding 2

- **File**: references/scripts/compose.py
- **Line**: 413–414
- **Severity**: warning
- **Issue**: The `_load_manifest_v2_from_file` docstring says a variant whose base is `worker` "picks up `roles/worker/includes-v2.yml` here" but the base manifest now reads `includes.yml`.
- **Evidence**: Line 414: `picks up ``roles/worker/includes-v2.yml`` here`. The recursive call at line 432 (`_load_manifest_v2(base_role)`) resolves through `_resolve_v2_path` which uses `_V2_MANIFEST_FILENAME = "includes.yml"`. The filename in the docstring is stale.
- **Suggested fix**: Replace `includes-v2.yml` with `includes.yml` in the docstring at line 414.

### Finding 3

- **File**: references/scripts/compose.py
- **Line**: 351–353
- **Severity**: warning
- **Issue**: The docstring claims `_load_manifest_v2` "Never references `includes.yml` or `includes-events.yml` directly" — this is no longer true since `_V2_MANIFEST_FILENAME = "includes.yml"` means the function now reads `includes.yml` on every base-role path.
- **Evidence**: Line 352: `Never references ``includes.yml`` or ``includes-events.yml`` directly`. Line 368: `v2_path = role_dir / _V2_MANIFEST_FILENAME` (which is `"includes.yml"`). The claim was correct in D5 (when `_V2_MANIFEST_FILENAME` was `"includes-v2.yml"`) but is now wrong after the E6 rename.
- **Suggested fix**: Remove or rewrite the stale sentence. For example: "The base-role path reads the canonical manifest via `_V2_MANIFEST_FILENAME`; variant `includes.yml` is the input to `_resolve_variant` only."

### Finding 4

- **File**: references/roles/dm/includes.yml, references/roles/pm/includes.yml, references/roles/verifier/includes.yml, references/roles/worker/includes.yml
- **Line**: 7–9 in each file (the "Deletion of the v1 pair + rename..." sentence)
- **Severity**: warning
- **Issue**: The header comments in all four manifest files describe the rename as a future event: "Deletion of the v1 pair + rename of this file to `includes.yml` happens atomically in the E6 switch PR (#10685)." This PR IS E6 (#10685) — the rename and deletion have already occurred (the file is already named `includes.yml` and the v1 pair is gone). The comment is now a historical artifact that reads as if the event is still pending.
- **Evidence**: Each manifest file currently bears the filename `includes.yml` (the rename target). The comment at line 7–9 frames the rename as future tense. This is confusing: a reader seeing the file at `includes.yml` with a comment saying it will be renamed to `includes.yml` may wonder whether the rename was applied correctly.
- **Suggested fix**: Rewrite the header to describe the current state rather than the planned transition. For example: "This is the unified v2 manifest (formerly `includes-v2.yml`). The legacy `includes.yml` / `includes-events.yml` split was retired in E6 (#10685)."
```

Let me also note the cross-file concern that surfaced during the audit:

```
### Finding 5

- **File**: references/scripts/compose.py
- **Line**: 227 (in `_load_manifest`, v1 path)
- **Severity**: error
- **Issue**: The `_load_manifest` v1 function still has an active event-driven code path: `primary_name = "includes-events.yml" if wake_mode == "event-driven" else "includes.yml"`. The four `includes-events.yml` files still exist on disk at `references/roles/{dm,pm,verifier,worker}/includes-events.yml`. This means event-driven agents using v1 compose (`compose_role` → `_load_manifest`) will still find and load the old event-only manifest rather than the unified `includes.yml`. The polling/event split is declared "retired" but the retirement is incomplete: the files still exist AND the v1 code still prefers them for event-driven mode.
- **Evidence**: 
  - `glob` confirms all four `includes-events.yml` exist at `references/roles/*/includes-events.yml`.
  - `_load_manifest` at line 227 prefers `includes-events.yml` for `wake_mode='event-driven'` and only falls back to `includes.yml` when it's absent.
  - The task context says "the v1 includes-events.yml polling/event split is retired" but the split is still active if the files remain.
- **Suggested fix**: Either (a) delete the four `includes-events.yml` files as part of this Phase 1 cutover so the v1 fallback path activates for event-driven agents, or (b) if deletion is intentionally deferred to a later phase, update the `_load_manifest` function in this phase to ignore `includes-events.yml` (or treat it identically to `includes.yml`). As-is, event-driven agents compose a different manifest than polling agents — the exact split this PR aims to retire.
```
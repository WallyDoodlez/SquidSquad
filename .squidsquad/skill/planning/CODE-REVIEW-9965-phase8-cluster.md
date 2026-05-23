Now I have all the context I need. Let me compile my findings.

---

### Finding 1

- **File**: `references/scripts/config.py`
- **Line**: 603–604
- **Severity**: error
- **Issue**: `sync_agents()` reporting path still references the old `"qa"` directory and appends the string `"qa"`, but the skip filter on line 591 was already changed to skip `"verifier"`. The function is now internally inconsistent, and ordering relative to the wizard.py D4 directory rename is unsafe.
- **Evidence**: Line 591 skips `"verifier"` from `dev_roles`, but lines 603–604 still do `(sqdir / "qa" / "CLAUDE.md").exists()` and `roles.append("qa")`. If the D4 directory rename has already happened, the `"qa"` directory no longer exists and the verifier role is silently omitted from the returned `roles` list. If the rename has *not* yet happened, `"qa"` is not skipped in the dev_roles loop (since the skip set is now `("pm", "verifier", "dm")`), so `"qa"` ends up in `dev_roles` AND gets appended again at line 604, producing a duplicate. Both paths are wrong.
- **Suggested fix**: Update lines 603–604 in lockstep with line 591:

  ```python
  if (sqdir / "verifier" / "CLAUDE.md").exists():
      roles.append("verifier")
  ```

  Or, if the directory rename hasn't landed yet, coordinate so both the skip set and the reporting check flip atomically with the rename.

---

### Finding 2

- **File**: `references/scripts/cycle_pre.py`
- **Line**: 445
- **Severity**: error
- **Issue**: `_ROLE_EVENT_TYPES` dict is still keyed by `"qa"`. After the enum flip, the role name `"verifier"` will be passed to `_filter_events_for_role()`, which looks up `_ROLE_EVENT_TYPES.get(role)` at line 469. The key `"verifier"` does not exist, so `allowed` is falsy, and line 471 returns ALL events unfiltered.
- **Evidence**: Lines 469–471: `allowed = _ROLE_EVENT_TYPES.get(role)` / `if not allowed: return events`. When `role == "verifier"`, the `"qa"` key doesn't match, so the verifier receives every event type (including `cycle-start`, `agent-health`, etc.) instead of the intended subset (`pr-merged`, `compose-completed`, `status-transition`, `cycle-end`, `verification-failed`). This is a silent functional regression — no error is raised, but the verifier agent gets spammed with irrelevant events.
- **Suggested fix**: Either add a `"verifier"` key to `_ROLE_EVENT_TYPES` with the same event set as `"qa"`, or rename the existing `"qa"` key to `"verifier"`.

---

### Finding 3

- **File**: `references/scripts/cycle_pre.py`
- **Line**: 572
- **Severity**: error
- **Issue**: `_get_verifiable_roles()` still hardcodes `roles.add("qa")` as a mandatory role. After the canonical enum flip, this function — which feeds role names to `tracker.py` queries at lines 696 and 873 — will query using `role:qa` labels rather than `role:verifier`.
- **Evidence**: Line 572: `roles.add("qa")`. The function's docstring at lines 548–553 explicitly states it adds mandatory roles `(pm, qa, dm)`. The migrate_labels_6274.py script dual-tags open issues with both `role:qa` and `role:verifier`, so queries with `"qa"` still work during the 30-day window. But once the dual-label window closes and `role:qa` is removed, queries using `"qa"` will miss issues tagged only with `role:verifier`. The change at line 1037 in this same file flips the enum in `_build_dm_input`; `_get_verifiable_roles` needs the same treatment.
- **Suggested fix**: Change `roles.add("qa")` to `roles.add("verifier")` and update the surrounding comments (lines 548–553, 567–569) accordingly.

---

### Finding 4

- **File**: `references/scripts/cycle_pre.py`
- **Line**: 1083
- **Severity**: error
- **Issue**: `ROLE_BUILDERS` dispatch dict is still keyed by `"qa"`. When the cycler (or any caller) invokes `cycle_pre.py` with role `"verifier"`, the lookup at line 1210 (`if role not in ROLE_BUILDERS`) will reject it and print `ERROR: Unknown role 'verifier'`.
- **Evidence**: Line 1083: `"qa": _build_qa_input`. Line 1210–1212: `if role not in ROLE_BUILDERS: print(f"ERROR: Unknown role '{role}'. Valid: {list(ROLE_BUILDERS.keys())}") ; sys.exit(1)`. If the role argument arriving at `cycle_pre.py` is now `"verifier"`, the script hard-fails. Note that `_build_qa_input` internally calls `_get_verifiable_roles()` (line 873), which also has the drift from Finding 3 — so both issues compound.
- **Suggested fix**: Either change the key to `"verifier"` and keep the function name, or add a parallel entry `"verifier": _build_qa_input` alongside the existing `"qa"` key during the dual-label window, then remove the `"qa"` key after migration.

---

### Finding 5

- **File**: `references/scripts/config.py`
- **Line**: 438
- **Severity**: warning
- **Issue**: Docstring comment in `_parse_agents_v1()` still says `Infrastructure roles (pm, qa, dm) are always present`, but line 486 now enforces `("verifier", "dm")`. The comment is now misleading relative to the code it documents.
- **Evidence**: Line 438: `Infrastructure roles (pm, qa, dm) are always present (#6261 fixed team).` The code on line 486 iterates `("verifier", "dm")`. A reader seeing the comment would reasonably think "qa" is still the canonical name and might reintroduce it.
- **Suggested fix**: Update the comment to match: `Infrastructure roles (pm, verifier, dm) are always present (#6261 fixed team / #6274: qa→verifier).`
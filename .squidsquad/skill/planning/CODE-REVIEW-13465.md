### Finding 1

- **File**: references/scripts/tracker.py
- **Line**: 498–505 (create_issue) and 540–547 (create_task)
- **Severity**: error
- **Issue**: `create_issue` and `create_task` pass the raw, un-canonicalized `--role` value to both `_build_dual_role_labels_6274` and `_filter_role_labels_to_existing`. When the caller uses the new-form role prefix (`--role verifier` or `--role worker`) — which `_canonicalize_role` accepts without deprecation warning — `_build_dual_role_labels_6274` emits `role:verifier,role:qa` with the new-form label as **primary**. The filter force-keeps `role:verifier` (the "always keep primary" rule), but `role:verifier` does not exist in the repo's label taxonomy pre-#6274.3. The resulting label string still contains the unknown label, and `gh issue create` rejects it — the exact same failure mode the fix addresses for `--role qa`, but triggered from the opposite direction.

- **Evidence**: 
  - `_canonicalize_role("verifier")` maps to `"qa"` with `is_deprecated=False` (line 278–279), meaning `verifier` is a supported, non-deprecated input.
  - `_build_dual_role_labels_6274("verifier")` returns `"role:verifier,role:qa"` (the `_DUAL_LABEL_PAIRS_6274` table at line 289 is bidirectional).
  - `_filter_role_labels_to_existing` unconditionally keeps `role:verifier` because it matches `primary = f"role:{primary_role}"` (line 317: `lbl == primary`).
  - No canonicalization occurs between CLI arg parsing (`main()`, line 1157) and `create_issue`/`create_task`.
  - The same bug affects `--role verifier-lead` and `--role worker-lead` since `_DUAL_LABEL_PAIRS_6274` has no `-lead`-suffixed entries.

- **Suggested fix**: In `create_issue` and `create_task`, canonicalize `role` via `_canonicalize_role(role)` before passing it to `_build_dual_role_labels_6274` and `_filter_role_labels_to_existing`. This ensures the primary label is always the canonical form (`qa`/`dev`) that exists in the repo pre-#6274.3, while the dual alias (`verifier`/`worker`) is still emitted and safely dropped by the filter. After #6274.3 when the new labels are created, the filter automatically keeps both without code changes.

  ```python
  # In create_issue, after line 499:
  role = _canonicalize_role(role)
  # (same in create_task after line 541)
  ```

  Note: this will emit a deprecation warning on stderr for old-form inputs (`--role qa`/`--role dev`). If that warning is undesirable during create, a private `_canonicalize_role_silent` variant could be used — but the deprecation is the same warning agents already see in transition paths, so consistency argues for keeping it.

---

### Finding 2

- **File**: tests/test_13465_create_issue_role_label_filter.py
- **Line**: 1–86 (entire file)
- **Severity**: warning
- **Issue**: Missing test coverage for the new-form role input path. All existing tests use `primary_role="qa"` or a non-dual role — none exercise the `primary_role="verifier"` or `primary_role="worker"` case where the primary label itself does not exist in the repo but the paired alias does. This is the exact scenario described in Finding 1, and without a test the regression risk is high.

- **Evidence**: 
  - `test_qa_drops_nonexistent_verifier_alias` uses `primary_role="qa"` with `existing` containing `role:qa` — primary exists, alias is dropped. ✓
  - `test_qa_keeps_verifier_alias_when_it_exists` uses `primary_role="qa"` with both labels in `existing` — both kept. ✓
  - `test_gh_failure_falls_closed_to_primary` uses `primary_role="qa"` with empty existing — primary kept, alias dropped. ✓
  - `test_primary_always_kept_even_if_absent` uses a non-dual role `foo` — no alias to fall back to.
  - No test covers: `primary_role="verifier"`, `existing={"role:qa"}`, label string `"role:verifier,role:qa"` → should produce `"role:qa"` (primary dropped because it doesn't exist, alias kept because it does). Or after canonicalization (Finding 1 fix): the call changes to `primary_role="qa"`, making this case identical to the already-tested `test_qa_drops_nonexistent_verifier_alias`.

- **Suggested fix**: Add a test for the new-form-primary case:

  ```python
  @patch("tracker._repo_labels", return_value={"role:qa"})
  def test_verifier_primary_dropped_when_only_qa_exists(self, _m):
      # --role verifier: primary role:verifier doesn't exist, but alias role:qa does.
      # The filter should drop the unknown primary and keep the confirmed alias,
      # or (after canonicalization) primary becomes qa and verifier alias is dropped.
      out = tracker._filter_role_labels_to_existing(
          "role:verifier,role:qa", "verifier")
      # After Finding 1 fix (canonicalize first), this would be called with
      # primary_role="qa" instead, producing "role:qa". Either way, role:verifier
      # must not appear in the output when the repo lacks it.
      assert "role:verifier" not in out
      assert "role:qa" in out
  ```

  Also add an integration-level test in `TestCreateIssueExcludesUnknownRoleLabel` that calls `create_issue` with `role="verifier"` and verifies the label string sent to `gh issue create` does not contain `role:verifier` when the repo only defines `role:qa`.

---

### Finding 3

- **File**: tests/test_tracker.py
- **Line**: 27–37 (autouse fixture `_stub_repo_labels`)
- **Severity**: warning
- **Issue**: The autouse fixture stubs `_repo_labels` to return a set that includes **all** role labels — both old-form (`role:qa`, `role:dev`) and new-form (`role:verifier`, `role:worker`). This represents the post-#6274.3 state, not the current pre-#6274.3 reality where `role:verifier` and `role:worker` do not exist. Any `create_issue`/`create_task` test in this file that uses a dual role (indirectly) would see both labels pass the filter, masking the #13465 bug for those test paths. The existing `TestCreateIssue` test uses `role="skill"` (non-dual), so it is unaffected, but future tests or refactored tests could silently pass with this stub.

- **Evidence**: 
  - The fixture at line 33 lists `"role:verifier"` and `"role:worker"` alongside the existing labels.
  - The #13465 bug exists precisely because `role:verifier` is **not** a real repo label pre-#6274.3.
  - A test that passes `role="qa"` to `create_issue` with this stub active would get `"role:qa,role:verifier"` through the filter (both "exist"), never exercising the drop path — the exact scenario that caused the production failure.

- **Suggested fix**: Remove `"role:verifier"` and `"role:worker"` from the stub set, or explicitly document why they are present (e.g., a comment: "post-6274.3 state for forward-compat tests"). The pre-6274.3 default should match reality:

  ```python
  monkeypatch.setattr(
      tracker, "_repo_labels",
      lambda: {"role:skill", "role:dm", "role:pm", "role:qa", "role:designer",
               "role:dev"},
  )
  ```

  A separate, explicitly-named fixture can provide the post-6274.3 set for forward-compat tests that verify dual-emit resumes automatically.
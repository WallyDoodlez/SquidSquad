I now have a complete picture. Let me finalize my review.

---

### Finding 1

- **File**: `references/scripts/cycle_pre.py`
- **Line**: 585–586 (inside `_get_verifiable_roles`)
- **Severity**: warning
- **Issue**: `_get_verifiable_roles()` now adds both `"qa"` and `"verifier"` to the returned set, producing a sorted list like `["dm", "pm", "qa", "verifier", ...]`. Both `_build_pm_input` (line 710) and `_build_qa_input` (line 887) iterate over this list and call `tracker.py list-issues` / `list-tasks` for **each** role. During the dual-aware window, issues carry both `role:qa` and `role:verifier` labels, so `tracker.py` returns the **same issue set** for both queries. This produces duplicate entries in `pending_test_issues` and `pending_test_tasks` — each issue appears twice, once with `source_role="qa"` and once with `source_role="verifier"`. This doubles tracker query work and produces confusing duplicate data for the consuming agent (PM or verifier).

- **Evidence**: The `_get_verifiable_roles` docstring at line 565–567 explicitly acknowledges both names will query the same issues: "tracker queries hit whichever role:<name> label is on the issue (migrate_labels_6274.py dual-tags both, so the returned issue sets are identical)." However, no deduplication occurs in the callers at lines 710–720 (`_build_pm_input`) or lines 887–906 (`_build_qa_input`). The `extend()` on line 718 unconditionally appends without checking for duplicates. No downstream deduplication exists.

- **Suggested fix**: Either (a) add deduplication in the callers (skip if the same issue `number` already seen), or (b) have `_get_verifiable_roles()` return only one of the two names based on which directory actually exists on disk (matching the pattern used in `sync_agents()` at lines 611–614), or (c) acknowledge the duplicate-window behavior explicitly in the F3 fix comment and ensure AC2.8 test rewrites verify it was cleaned up. The simplest aligned fix: in `_get_verifiable_roles()`, add a dedup note and in the callers, deduplicate by issue number before appending.

---

### Finding 2

- **File**: `references/scripts/cycle_pre.py`
- **Line**: 900, 922 (inside `_build_qa_input`)
- **Severity**: warning
- **Issue**: `_build_qa_input` (lines 878–989) contains **hardcoded** `SQUID_DIR / "qa" / "planning"` path references at lines 900 and 922. The `role` parameter (line 878) is **never used** inside the function. The fix-up adds `"verifier": _build_qa_input` at line 1103, enabling `SQUIDSQUAD_ROLE=verifier` to dispatch to this function. However, after wizard D4 renames `.squidsquad/qa/` → `.squidsquad/verifier/` (per CONTEXT-6274 D4), this hardcoded path will not exist. The verifier agent will silently fail to find test plans stored in `.squidsquad/verifier/planning/`, because the function only searches `.squidsquad/pm/planning/` and `.squidsquad/qa/planning/`.

- **Evidence**: The commit message for F4 claims: "ROLE_BUILDERS gains 'verifier': _build_qa_input alongside 'qa': _build_qa_input so cycle_pre.py works whether the agent invokes with SQUIDSQUAD_ROLE=qa (current) or =verifier (post wizard D4 directory rename)." But `_build_qa_input` ignores its `role` parameter and uses the hardcoded string `"qa"` at lines 900 and 922. After wizard D4 renames `.squidsquad/qa/` to `.squidsquad/verifier/`, `SQUID_DIR / "qa" / "planning"` will not exist. The check `planning_dir.exists()` at line 901 will silently return False, so no crash occurs — but verifier-specific test plans will be missed. The `pm/planning` directory is also checked, so PM test plans would still be found.

- **Suggested fix**: Make the planning directory search dual-aware. Replace the hardcoded list `[SQUID_DIR / "pm" / "planning", SQUID_DIR / "qa" / "planning"]` at lines 900 and 922 with one that includes `SQUID_DIR / "verifier" / "planning"` and also checks `qa` as fallback — or parameterize it to use the caller's `role` parameter. Minimal fix matching the sync_agents() dual-aware pattern:
  ```python
  planning_dirs = [SQUID_DIR / "pm" / "planning"]
  if (SQUID_DIR / "verifier" / "planning").exists():
      planning_dirs.append(SQUID_DIR / "verifier" / "planning")
  elif (SQUID_DIR / "qa" / "planning").exists():
      planning_dirs.append(SQUID_DIR / "qa" / "planning")
  for planning_dir in planning_dirs:
      ...
  ```
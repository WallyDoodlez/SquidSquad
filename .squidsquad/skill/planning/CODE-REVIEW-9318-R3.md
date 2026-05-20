All tests have been systematically checked. Here's the complete analysis:

---

**Tests that assert specific roles in verifiable/queried contexts:**

| Test | qa assertion present? |
|---|---|
| `TestGetVerifiableRoles.test_includes_config_dev_agents` (line 832) | ✅ `assert "qa" in roles` (line 837) |
| `TestGetVerifiableRoles.test_always_includes_mandatory_roles` (line 839) | ✅ `assert "qa" in roles` (line 851) |
| `TestGetVerifiableRoles.test_fallback_when_config_empty` (line 853) | ✅ `assert "qa" in roles` (line 861) |
| `TestGetVerifiableRoles.test_deduplicates` (line 863) | N/A — only checks dedup, not specific roles |
| `TestGetVerifiableRoles.test_returns_sorted` (line 869) | N/A — only checks sort order, not specific roles |
| `TestQAInputMultiRole.test_qa_queries_all_roles` (line 879) | ✅ `assert "qa" in queried_roles` (line 923) |
| `TestQAInputMultiRole.test_qa_items_have_source_role` (line 929) | N/A — asserts `source_role` field on dm items only |
| `TestQAInputMultiRole.test_qa_branch_uses_correct_role_prefix` (line 961) | N/A — asserts branch naming for qa items (the test itself exercises qa) |
| `TestPMInputMultiRole.test_pm_queries_all_roles` (line 1003) | ✅ `assert "qa" in queried_roles` (line 1042) |
| `TestPMInputMultiRole.test_pm_items_have_source_role` (line 1045) | N/A — asserts `source_role` field on dm items only |

Every test that asserts specific verifiable/queried roles already includes a `qa` check. The two tests identified in R2 (`test_qa_queries_all_roles` and `test_pm_queries_all_roles`) have been correctly fixed (lines 923 and 1042 respectively).

NO_FINDINGS
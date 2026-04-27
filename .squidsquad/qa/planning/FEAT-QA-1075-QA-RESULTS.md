# FEAT-QA-1075 QA Results — Vault Candidates in Research

**Branch**: squidsquad/skill/1075
**Date**: 2026-04-26
**Test file**: `.squidsquad/qa/planning/FEAT-QA-1075-tests.py`
**Files under test**:
- `references/sub-skills/pm-specific/task-intake.md`
- `references/prompts/research.md.j2`

---

## Pytest Output (verbatim)

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\naaht\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: D:\Dev\Dev\SquidSquad-qa
plugins: anyio-4.12.1, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 18 items

.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC01VaultCandidatesSectionPresent::test_task_intake_file_exists PASSED [  5%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC01VaultCandidatesSectionPresent::test_vault_candidates_section_in_task_intake PASSED [ 11%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC01VaultCandidatesSectionPresent::test_vault_candidates_after_recommendation PASSED [ 16%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC01VaultCandidatesSectionPresent::test_research_prompt_file_exists PASSED [ 22%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC01VaultCandidatesSectionPresent::test_vault_candidates_section_in_research_prompt PASSED [ 27%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC01VaultCandidatesSectionPresent::test_vault_candidates_after_recommendation_in_prompt PASSED [ 33%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC02ResearchPromptRequestsVaultCandidates::test_task_intake_analysis_list_mentions_vault_candidates PASSED [ 38%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC02ResearchPromptRequestsVaultCandidates::test_research_prompt_instructions_mention_vault PASSED [ 44%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC02ResearchPromptRequestsVaultCandidates::test_research_prompt_instructions_mention_candidates PASSED [ 50%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC02ResearchPromptRequestsVaultCandidates::test_research_prompt_discovery_instruction_present PASSED [ 55%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC03CandidateFormatIsStructured::test_task_intake_candidate_format_has_type_field PASSED [ 61%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC03CandidateFormatIsStructured::test_task_intake_candidate_format_has_why_rationale PASSED [ 66%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC03CandidateFormatIsStructured::test_research_prompt_candidate_format_has_type_field PASSED [ 72%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC03CandidateFormatIsStructured::test_research_prompt_candidate_format_has_why_rationale PASSED [ 77%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC04CandidateCap::test_task_intake_specifies_candidate_cap PASSED [ 83%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC04CandidateCap::test_research_prompt_specifies_candidate_cap PASSED [ 88%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC04CandidateCap::test_task_intake_cap_is_in_vault_candidates_section PASSED [ 94%]
.squidsquad/qa/planning/FEAT-QA-1075-tests.py::TestTC04CandidateCap::test_research_prompt_cap_is_in_vault_candidates_section PASSED [100%]

============================= 18 passed in 0.05s ==============================
```

---

## TC Results

### TC-1: RESEARCH.md template includes Vault Candidates section
- **Result**: PASS
- **Tests**: `test_task_intake_file_exists`, `test_vault_candidates_section_in_task_intake`, `test_vault_candidates_after_recommendation`, `test_research_prompt_file_exists`, `test_vault_candidates_section_in_research_prompt`, `test_vault_candidates_after_recommendation_in_prompt`
- **Notes**: `## Vault Candidates` section present in both `task-intake.md` (line 109) and `research.md.j2` (line 66). Confirmed to appear after `## Recommendation` in both files.

### TC-2: Research agent prompt requests vault candidates
- **Result**: PASS
- **Tests**: `test_task_intake_analysis_list_mentions_vault_candidates`, `test_research_prompt_instructions_mention_vault`, `test_research_prompt_instructions_mention_candidates`, `test_research_prompt_discovery_instruction_present`
- **Notes**: `task-intake.md` has a numbered analysis item 8 explicitly covering vault candidates. `research.md.j2` instruction step 5 says "Flag any discoveries worth preserving in the vault". Both files contain "vault" and "candidates" in their instruction prose.

### TC-3: Candidate format is structured
- **Result**: PASS
- **Tests**: `test_task_intake_candidate_format_has_type_field`, `test_task_intake_candidate_format_has_why_rationale`, `test_research_prompt_candidate_format_has_type_field`, `test_research_prompt_candidate_format_has_why_rationale`
- **Notes**: Both files show the format `- **Type**: [decision/pattern/learning] — [one-line description] — **Why**: [why this is vault-worthy]`. All three required fields (type, description, rationale) are present.

### TC-4: Cap on candidates
- **Result**: PASS
- **Tests**: `test_task_intake_specifies_candidate_cap`, `test_research_prompt_specifies_candidate_cap`, `test_task_intake_cap_is_in_vault_candidates_section`, `test_research_prompt_cap_is_in_vault_candidates_section`
- **Notes**: Both files include `_(max 5 candidates — flag only, PM decides whether to vault)_` directly in the Vault Candidates section. Cap is "max 5", within the allowed 3-5 range from the test plan.

---

## Comprehension Questions

### CQ-1: Where do vault candidates appear in the planning lifecycle?
- **Answer**: In Phase 1 RESEARCH.md output, after `## Recommendation`. The research agent flags candidates; PM decides whether to vault them during vault-remember. The research agent does not write vault notes directly.
- **Evidence**: `task-intake.md` line 109-111 (section in template), line 62 (analysis item 8 in research agent instructions). Format note: `_(max 5 candidates — flag only, PM decides whether to vault)_`.

---

## Summary

**18/18 tests PASS. Zero failures. Feature fully implemented.**

Both `references/sub-skills/pm-specific/task-intake.md` and `references/prompts/research.md.j2` contain:
1. `## Vault Candidates` section placed after `## Recommendation`
2. Structured format with type/description/Why rationale
3. A max-5 candidate cap
4. Explicit agent instructions to identify vault candidates

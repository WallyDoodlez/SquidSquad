### Finding 1

- **File**: references/scripts/assemble_verifier.py
- **Line**: 26 (regex definition)
- **Severity**: warning
- **Issue**: The sub-skill regex `→\s*run sub-skill:\s*([A-Za-z0-9_-]+)` uses a literal single space between `run` and `sub-skill`. If the LLM introduces extra whitespace there (e.g. double space `→ run  sub-skill: x`, or a tab), the regex fails to match, treating a valid preserved reference as missing/extra.
- **Evidence**: The PRD review criteria explicitly call out "whitespace tolerance." The implementation adds `\s*` after the arrow and after the colon, acknowledging LLM cosmetic spacing changes — but the gap between `run` and `sub-skill` was left as a single literal space. An input like `→ run  sub-skill: x` (double space) would cause `findall` to return no match, producing a false missing/extra diff. The test `test_sub_skill_ref_flexible_whitespace` (test_assemble_verifier.py, line 91-96) only varies whitespace after the arrow and colon, not between `run` and `sub-skill`, so this gap is untested.
- **Suggested fix**: Change the literal space between `run` and `sub-skill` to `\s+`:
  ```python
  _SUB_SKILL_RE = re.compile(r"→\s*run\s+sub-skill:\s*([A-Za-z0-9_-]+)")
  ```
  And add a test case covering whitespace between `run` and `sub-skill`, e.g.:
  ```python
  def test_sub_skill_ref_whitespace_between_run_and_subskill():
      linked = "→ run sub-skill: x\n"
      assembled = "→ run  sub-skill: x\n"
      result = av.verify_preservation(linked, assembled)
      assert result.ok is True
  ```

---

### Finding 2

- **File**: tests/test_assemble_verifier.py
- **Line**: 109–113 (test_step_id_punctuation_prefix_matches)
- **Severity**: warning
- **Issue**: The test asserts `result.extra_step_ids == ["boot"]` but does not also assert `result.ok is False`. The assembled input has an extra step ID not present in the linked input, so `ok` must be `False`. Relying on a downstream assertion about `extra_step_ids` alone leaves a gap — if a future change breaks the `ok` computation while leaving the list correct, this test would still pass.
- **Evidence**: `linked = ""` and `assembled = "-step:cycle/boot\n"` — the assembled has a reference the linked lacks, so this is an extra-reference scenario. The function should return `ok=False`. The test for missing step IDs (`test_missing_step_id_detected`, line 101) and the test for word-prefix (`test_step_id_word_prefix_does_not_match`, line 147) both include `assert result.ok is False` or `assert result.ok is True` as appropriate. This test omits the `ok` assertion, making it inconsistent and less defensive.
- **Suggested fix**: Add `assert result.ok is False` after line 111:
  ```python
  result = av.verify_preservation(linked, assembled)
  assert result.ok is False
  assert result.extra_step_ids == ["boot"]
  ```
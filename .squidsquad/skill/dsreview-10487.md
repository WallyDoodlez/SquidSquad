I've reviewed both files thoroughly, focusing on correctness, edge cases, and integration. Here are my findings:

### Finding 1

- **File**: references/scripts/source_frontmatter.py
- **Line**: 50 (the `_FRONTMATTER_RE` regex)
- **Severity**: error
- **Issue**: The regex silently treats an empty frontmatter block `---\n---\n` as "no frontmatter" (returns `None`), but the nearly identical `---\n\n---\n` (with a blank line between delimiters) matches and raises `FrontmatterError`. This is an inconsistent boundary.
- **Evidence**: The opening sub-pattern `\A---\s*\n` consumes the newline after the opening `---`. The closing sub-pattern `\n---\s*(?:\n|\Z)` *requires* a `\n` immediately before the closing `---`. When the content between delimiters is literally empty (`---\n---\n`), there is no `\n` available for the closing half — the opening already consumed it. The lazy `([\s\S]*?)` cannot bridge the gap. The regex fails to match, `m` is `None`, and `parse_source_frontmatter_text` returns `None`. A caller who wrote `---` delimiters intending an empty block gets silent no-frontmatter instead of an error. The task context explicitly asks reviewers to examine "empty frontmatter block" as an edge case.
- **Suggested fix**: Either accept the inconsistency and document it explicitly in the module docstring, or adjust the regex to handle the zero-content case. One minimal fix: change the closing half to `(?:\n|\A---\s*\n)---\s*(?:\n|\Z)` — but this is ugly. A cleaner approach: after the regex fails to match, do a secondary check for `\A---\s*\n---` to distinguish "empty frontmatter" from "no frontmatter":

  ```python
  m = _FRONTMATTER_RE.match(text)
  if m is None:
      # Distinguish empty-frontmatter from genuine no-frontmatter.
      if re.match(r"\A---\s*\n---", text):
          raise FrontmatterError(f"{source}: empty frontmatter block.")
      return None
  ```

  Or rewrite the regex to use two explicit anchor-based patterns joined with `|` — one for non-empty content and one for empty.

---

### Finding 2

- **File**: references/scripts/source_frontmatter.py
- **Line**: 50
- **Severity**: warning
- **Issue**: The opening sub-pattern `\A---\s*\n` allows trailing whitespace on the opening `---` line (e.g. `---   \n`), but the task context states the regex "must require `^---$` at very top." Strict `^---$` means the line contains exactly three dashes and nothing else.
- **Evidence**: `\s*` matches `[ \t\n\r\f\v]`, so `---   \n`, `---\t\n`, and even `---\r\n` all pass the opening delimiter check. The module docstring and AC specify `^---$` (the line must be exactly `---`). Trailing whitespace on the opening delimiter is lenient in a way the spec does not call for. (Trailing whitespace on the *closing* delimiter is explicitly mentioned as an edge case to review; the regex's `\s*` there is intentional. But the opening's `\s*` is not mentioned and contradicts the stated requirement.)
- **Suggested fix**: Change the opening to `\A---[ \t]*\n` if horizontal whitespace tolerance is desired but newline consumption must be prevented, or to `\A---\n` for strict `^---$` compliance. The current `\s*` risks matching `\n` (requiring backtracking), which is the root cause of Finding 1.

---

### Finding 3

- **File**: tests/test_source_frontmatter.py
- **Line**: 229–235
- **Severity**: warning
- **Issue**: `test_v1_compose_untouched` does `import compose` but only `references/scripts` (not the repo root) has been added to `sys.path`. The test depends on the repo root already being on `sys.path` (e.g. because `pytest` was invoked from the repo root).
- **Evidence**: The test file's path setup (lines 8–9) adds `SCRIPTS = .../references/scripts` to `sys.path`. The `compose` module lives at the repo root (as confirmed by the existing test infrastructure in `run_tests.py`). If the test suite is ever invoked from a different working directory or via a runner that does not put the repo root on `sys.path`, this test will fail with `ModuleNotFoundError` rather than a clean assertion failure.
- **Suggested fix**: Add the repo root to `sys.path` explicitly before the import, or wrap the import in a try/except that skips the test with a clear message:

  ```python
  repo_root = Path(__file__).resolve().parent.parent
  sys.path.insert(0, str(repo_root))
  ```

  (The repo root is already computed in `test_existing_dm_identity_parses_correctly` at line 214; reuse that logic.)

---

### Finding 4

- **File**: tests/test_source_frontmatter.py
- **Line**: (no corresponding test exists)
- **Severity**: warning
- **Issue**: No test covers trailing whitespace after the closing `---` delimiter. The task context explicitly calls this out as an edge case to review.
- **Evidence**: The regex handles it (`\s*` before `(?:\n|\Z)`), but there is no test proving it. Example input that should succeed:

  ```python
  def test_closing_delimiter_trailing_whitespace():
      text = "---\nslot: identity\nordinal: 0\n---   \n\nbody\n"
      fm = sf.parse_source_frontmatter_text(text)
      assert fm.slot == "identity"
  ```
- **Suggested fix**: Add a parametrized or explicit test for closing `---` with trailing spaces and tabs.

---

### Finding 5

- **File**: tests/test_source_frontmatter.py
- **Line**: (no corresponding test exists)
- **Severity**: warning
- **Issue**: No test covers YAML anchors or aliases in frontmatter values. The task context calls out "frontmatter where slot value uses YAML anchors/refs" as an edge case.
- **Evidence**: `yaml.safe_load` supports anchors/aliases, but there is no test confirming that, for instance, an anchor on an extras field works correctly or that an alias referencing an undefined anchor raises a clean `FrontmatterError` (wrapping the `YAMLError`). Example:

  ```python
  def test_yaml_anchor_in_extras():
      text = "---\nslot: identity\nordinal: 0\nx: &anchor value\ny: *anchor\n---\n"
      fm = sf.parse_source_frontmatter_text(text)
      assert fm.extras == {"x": "value", "y": "value"}
  ```
- **Suggested fix**: Add a test for valid anchor/alias usage and a test for an undefined-alias error path.

---

### Summary

| # | Severity | What |
|---|----------|------|
| 1 | **error** | Empty frontmatter `---\n---\n` returns `None` instead of raising; inconsistent with `---\n\n---\n` which does raise |
| 2 | warning | Opening `\s*` violates the `^---$` requirement from the task spec |
| 3 | warning | `import compose` in test is fragile — depends on implicit `sys.path` |
| 4 | warning | Missing test: trailing whitespace on closing `---` |
| 5 | warning | Missing test: YAML anchors/aliases in frontmatter values |

No security concerns with `yaml.safe_load` — that is the correct choice. `FileNotFoundError` propagation is correctly tested. Returning `None` for unterminated frontmatter is reasonable and tested. The boolean-rejection in `_validate_ordinal` is correct and well-tested. `LEGAL_SLOTS` duplication is intentional and documented.
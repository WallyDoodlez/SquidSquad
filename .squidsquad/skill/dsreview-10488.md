### Finding 1

- **File**: references/scripts/l4_parser.py
- **Line**: 59–62
- **Severity**: error
- **Issue**: `re.MULTILINE` flag on `_TRAILER_RE` causes `$` to match at end of *any* line, not just end of string. A multi-line HTML comment block in the middle of a body (with `<!--` and `-->` on their own lines) would be incorrectly parsed as the metadata trailer and stripped from `body_text`.
- **Evidence**: 
  - The regex is `r"\n<!--\s*\n([\s\S]*?)\n\s*-->\s*$"` with `re.MULTILINE`. With MULTILINE, `$` matches before every `\n` in the string, not just end-of-string.
  - Consider body: `"real text\n\n<!--\nmid\n-->\nmore text\n\n<!--\nauthored-by: x\n-->"`. The `.search()` scan finds `\n<!--` at the *first* comment block; `([\s\S]*?)` captures `mid`; `\n\s*-->\s*$` matches at the end of the first `-->` line (because `$` matches there in MULTILINE mode). The mid-body comment is wrongly treated as the trailer.
  - The docstring says: *"comments elsewhere in the body are ignored"*. This bug violates that.
  - The existing test `test_metadata_only_terminal_comment_counts_as_trailer` uses a single-line `<!-- not metadata -->` which does **not** satisfy `<!--\s*\n` (no newline after `<!--`), so it accidentally avoids triggering the bug. A multi-line mid-body comment is not tested.
- **Suggested fix**: Remove `re.MULTILINE` (it serves no purpose — the regex uses `\n` for newlines, not `^`/`$` for line-by-line matching). Optionally change `$` to `\Z` for unambiguous end-of-string anchoring:

  ```python
  _TRAILER_RE = re.compile(
      r"\n<!--\s*\n([\s\S]*?)\n\s*-->\s*\Z",
  )
  ```

  Add a test with a multi-line mid-body comment preceding a real trailer to lock this.

---

### Finding 2

- **File**: references/scripts/l4_parser.py
- **Line**: 132 (inside `_commit_current_op`)
- **Severity**: warning
- **Issue**: `body = "\n".join(current_body).strip("\n")` strips the leading newline from the accumulated body. If an H3 op's body consists *only* of a metadata trailer (no preceding body text), the `_TRAILER_RE` regex fails to match because it requires `\n<!--` at the start of the trailer, and `.strip("\n")` has removed the only `\n` that precedes `<!--`. The trailer is silently kept as `body_text` and metadata is empty `{}`.
- **Evidence**:
  - Input:
    ```markdown
    ## Identity

    ### append

    <!--
    authored-by: x
    -->
    ```
  - `current_body` = `["", "<!--", "authored-by: x", "-->"]`
  - Joined: `"\n<!--\nauthored-by: x\n-->"`
  - After `.strip("\n")`: `"<!--\nauthored-by: x\n-->"` — leading `\n` is gone.
  - `_TRAILER_RE.search(...)` requires `\n<!--`; the string starts with `<`, so no match.
  - Result: `metadata = {}`, `body_text = "<!--\nauthored-by: x\n-->"`. The trailer is not parsed.
  - The AC says *"HTML-comment metadata trailer at end of H3 body parsed into L4Op.metadata"* — this case is not correctly handled.
  - No test covers a body that is *only* a metadata trailer.
- **Suggested fix**: Change `.strip("\n")` to `.rstrip("\n")` so leading newlines are preserved for the trailer regex, and update the `_TRAILER_RE` to also accept a trailer at the very start of the body (no preceding `\n`):

  ```python
  _TRAILER_RE = re.compile(
      r"(?:\A|\n)<!--\s*\n([\s\S]*?)\n\s*-->\s*\Z",
  )
  ```

  Then in `_extract_metadata`, adjust the body slice: when `\A` matches, `m.start()` is 0 and `body[:0]` is `""` (correct). When `\n` matches, behavior is unchanged. Add a test for trailer-only body.
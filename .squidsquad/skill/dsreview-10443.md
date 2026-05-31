I now have a complete picture. Here are my findings:

---

### Finding 1

- **File**: tests/test_assemble_cache.py
- **Line**: 152–157
- **Severity**: error
- **Issue**: `test_gitignore_does_not_exclude_assemble_cache` unconditionally calls `gitignore.read_text()` without handling the case where `.gitignore` does not exist. If `.gitignore` is absent from the repo root, the test crashes with `FileNotFoundError` instead of passing (the invariant — "`.assemble-cache` is not gitignored" — is trivially satisfied when no `.gitignore` exists, so the test should pass).
- **Evidence**: Line 155: `content = gitignore.read_text(encoding="utf-8")` will raise `FileNotFoundError` if `.gitignore` is missing. The glob search in this repo confirms no `.gitignore` file exists at the repo root. The AC requires the cache to be git-tracked; a missing `.gitignore` means nothing excludes it, which satisfies the constraint.
- **Suggested fix**: Guard the read with a `try/except FileNotFoundError` and treat a missing `.gitignore` as a pass (or skip the test with a warning):

```python
def test_gitignore_does_not_exclude_assemble_cache():
    repo_root = Path(__file__).resolve().parent.parent
    gitignore = repo_root / ".gitignore"
    try:
        content = gitignore.read_text(encoding="utf-8")
    except FileNotFoundError:
        return  # no .gitignore → nothing excludes .assemble-cache
    assert ".assemble-cache" not in content
```

---

### Finding 2

- **File**: references/scripts/assemble_cache.py
- **Line**: 46–47 (`_cache_dir`), 58 (`cache_lookup`), 74 (`cache_store`)
- **Severity**: warning
- **Issue**: The `alias` parameter is used directly in filesystem path construction without any sanitization or validation: `_REPO_ROOT / ".squidsquad" / alias / _CACHE_DIRNAME`. A value like `"../../etc"` would escape the `.squidsquad/` tree and create/write files outside the intended cache directory.
- **Evidence**: `pathlib.Path` normalizes `..` components, so `Path("/repo/.squidsquad/../../etc/.assemble-cache")` resolves to `Path("/repo/etc/.assemble-cache")`. The alias comes from the caller (ultimately from `config.md`), and while aliases in practice are constrained short names like `"pm"` or `"dm"`, there is no programmatic guard.
- **Suggested fix**: Validate `alias` at the boundary — e.g., reject aliases containing `/`, `\`, or `..`, or restrict to a known allowlist pattern such as `^[a-zA-Z0-9_-]+$`. Apply the check in `_cache_dir` (which all public functions route through):

```python
import re
_ALIAS_RE = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]*$')

def _cache_dir(alias):
    if not _ALIAS_RE.match(alias):
        raise ValueError(f"Invalid alias: {alias!r}")
    return _REPO_ROOT / ".squidsquad" / alias / _CACHE_DIRNAME
```

---

### Finding 3

- **File**: references/scripts/assemble_cache.py
- **Line**: 23–26 (comment), 37–43 (implementation)
- **Severity**: warning
- **Issue**: The module comment claims the `0x1F` separator "makes the input tokenization injective." This is only true if none of the five input parts themselves contain the `0x1F` byte. If any part (e.g., `slot_purpose`, which is free-form descriptive text from skill definitions) happens to contain a literal `0x1F` byte, then two different 5-tuples could produce the same concatenated byte sequence and thus the same cache key.
- **Evidence**: Consider `linked_body = b"ab\x1fc"`, `slot_name = "d"` vs `linked_body = b"ab"`, `slot_name = b"c\x1fd"`. Both produce the byte stream `ab\x1fc\x1fd\x1f...`, making the encoding non-injective. While `0x1F` (ASCII Unit Separator) is vanishingly unlikely to appear in real prose or configuration values, the comment's claim of unconditional injectivity is inaccurate.
- **Suggested fix**: Either (a) escape any `0x1F` bytes that appear in input parts (e.g., double them), or (b) qualify the comment to note the assumption: "…makes the input tokenization injective *assuming none of the inputs contain a 0x1F byte*." Option (b) is sufficient since real inputs are human-authored text where `0x1F` is not present.

---

### Finding 4

- **File**: references/scripts/assemble_cache.py
- **Line**: 79
- **Severity**: warning
- **Issue**: `cache_store` does not catch `OSError` from `os.replace(tmp, final)`. On Windows specifically, `os.replace` (backed by `MoveFileExW` with `MOVEFILE_REPLACE_EXISTING`) will fail with `ERROR_SHARING_VIOLATION` if the destination file is currently open by another process (e.g., a concurrent `cache_lookup` that is mid-read). When this happens, the `.tmp` file is left on disk with no cleanup, and the caller receives an unhandled exception.
- **Evidence**: `cache_lookup` reads the file via `path.read_text()` (line 61), which opens, reads, and closes the file. The read window is short, so the race window is narrow — but it exists. On POSIX, `os.replace` succeeds even if the destination is open (directory entry swap is atomic). On Windows, file locking makes this a genuine failure mode. The `.tmp` file is not cleaned up on failure.
- **Suggested fix**: Wrap `os.replace` in a try/except that removes the `.tmp` file on failure before re-raising:

```python
try:
    os.replace(tmp, final)
except OSError:
    tmp.unlink(missing_ok=True)
    raise
```

---
Now I have all the evidence needed. Let me produce my findings.

---

### Finding 1

- **File**: tests/test_vault_optimize.py
- **Line**: 42 (test helper `_note`) vs. `references/scripts/vault_optimize.py` line 406 (decay check)
- **Severity**: warning
- **Issue**: The `_note` helper builds notes with `### Changelog` (H3 heading), but `decay()` checks for `## Changelog` (H2 heading) at line 406. This mismatch means the test `test_decay_applies_and_appends_changelog` (line 226) never exercises the `if "## Changelog" in new_text:` branch — the test always takes the `else` branch at line 412, which creates a **duplicate** `## Changelog` section instead of appending to the existing `### Changelog` section. The test only asserts that `"Confidence decayed by vault-optimize" in text` (line 233) — it does not verify that the entry was added to the existing changelog section vs. creating a duplicate.

- **Evidence**: 
  - `_note` template, line 42: `f"---\n\n### Changelog\n\n- {created} — Created.\n"` — uses three hashes
  - `decay()`, line 406: `if "## Changelog" in new_text:` — looks for two hashes
  - These strings don't match, so the `if` condition is always `False` on test notes, and the `else` branch (line 414) appends a second, separate `## Changelog` heading at end-of-file.
  - After one decay, the file has both `### Changelog` and `## Changelog` sections. The test assertion `"Confidence decayed by vault-optimize" in text` passes regardless.

- **Suggested fix**: Align the heading levels. If real vault notes use `## Changelog` (H2), fix the `_note` helper to use `## Changelog`. If real vault notes use `### Changelog` (H3), fix `decay()` to check for `### Changelog`. In either case, strengthen `test_decay_applies_and_appends_changelog` to verify the entry appears under the *existing* changelog heading (e.g., assert the entry appears between the existing `## Changelog` line and the next `## ` or end-of-file), not just anywhere in the text.

---

### Finding 2

- **File**: references/scripts/vault_optimize.py
- **Line**: 400–402 (the `else` branch of the frontmatter-boundary check)
- **Severity**: warning
- **Issue**: The no-frontmatter fallback at line 400–402 is **unreachable dead code**. The decay logic is only reached if `_parse_frontmatter(text)` (line 357) returned a dict with a non-empty `confidence` field (checked at line 366). For `_parse_frontmatter` to return non-empty `confidence`, it must have found a closing `---` delimiter (`text.find("---", 3) != -1` at line 66). Since `text` hasn't changed between the `_parse_frontmatter` call and `fm_end = text.find("---", 3)` at line 394, the condition `fm_end != -1` is always `True`, and the `else` branch is never taken.

- **Evidence**:
  - `_parse_frontmatter` (line 62–65): returns `{}` when `end == -1` (no closing `---`). So non-empty `confidence` implies a closing `---` was found.
  - `decay()` guard (line 364–367): `confidence = fm.get("confidence", "").strip()` / `if not updated or not confidence: continue` — skips notes without confidence.
  - `decay()` line 394: `fm_end = text.find("---", 3)` — same search on same `text`, must yield the same result. The `else` branch is structurally unreachable.

- **Suggested fix**: Either remove the dead `else` branch (the comment already says "shouldn't happen"), or convert it to an explicit assertion/error so a truly malformed note is caught rather than silently processed with a full-text replace that could corrupt body content (the #6514 concern). If kept as dead code, a comment noting it's unreachable would help future readers.

---

### Integration/Regression Check (no finding)

I verified that no other function relied on `decay()` bumping `updated:`:

- **`decay()` itself** (line 364, 370): reads `updated` only to compute staleness. With the fix, the medium→low decay correctly fires at 120 days from the last semantic edit, not 120 days from the decay event. This matches VAULT-ARCH §4.4.
- **`prune()`** (line 238, 242): reads `updated` for staleness check. Not affected — pruned notes are archived, not decayed.
- **`relevance()`** (line 479, 481): reads `updated` for recency scoring. With the fix, recency accurately reflects the last semantic edit rather than a decay-triggered bump, which is the correct behavior.
- **`reindex()`** and **`consolidate_scan()`**: don't use `updated` at all.
- **`today`** (line 384): only used in the changelog entry (line 405), never written to frontmatter. Correct.

The `test_decay_preserves_updated_field` test (line 235) correctly validates both that `updated:` is unchanged and that it's not bumped to today's date. The `test_decay_does_not_corrupt_body_content` test (line 263) validates that body mentions of `updated:` and `confidence:` are preserved. The fix is well-tested for its acceptance criteria.
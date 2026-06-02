I have now thoroughly reviewed both files against the COMPOSE-ARCHITECTURE.md source and the sub-skill-catalog.md. Here are my findings:

---

### Finding 1

- **File**: tests/test_comprehension_10678.py
- **Line**: 79–83
- **Severity**: error
- **Issue**: The regex for AC3 scenario `unresolved-name-error` does NOT match the question specifically designed to cover it (`no-catalog-row-error`), and instead matches a different question (`report-all-not-just-first`) whose primary topic is "report all vs report first," not "no catalog entry → error."

- **Evidence**: The regex is:
  ```
  (no\s+catalog\s+(row|entry)|unresolved|not\s+indexed).*(error|abort|surface|reject|fail)
  ```
  The `no-catalog-row-error` question prose (line 16) reads: "The name `phantom-skill-that-does-not-exist` has **NO matching row** in docs/sub-skill-catalog.md. What is the correct behaviour and why is silently skipping **forbidden**?" — This fails all three alternations:
  - `no\s+catalog\s+(row|entry)` fails because after "NO" the next word is "matching", not "catalog".
  - `unresolved` is absent.
  - `not\s+indexed` is absent.
  - `error|abort|surface|reject|fail` — "forbidden" is not in this alternation.

  Meanwhile, the `report-all-not-just-first` question (line 41) incidentally contains "**unresolved**" (three times) and "**abort**" (twice), matching the regex. If a future spec edit deletes the `no-catalog-row-error` question, the validator would **not** catch it because `report-all-not-just-first` still satisfies the regex. The AC3 scenario "unresolved name → error" would be unprotected.

- **Suggested fix**: Tighten the regex so it specifically requires the no-catalog-row semantics. For example:
  ```python
  (
      "unresolved-name-error",
      r"(no\s+(matching\s+)?(catalog\s+)?row|catalog\s+entry|not\s+indexed|unresolved).*"
      r"(error|abort|surface|reject|fail|forbidden)",
  ),
  ```
  This adds `matching\s+` as an optional word between "no" and "row", adds `catalog\s+entry` as another alternative, and adds `forbidden` to the error-signal alternation so question 2's own prose matches.

---

### Finding 2

- **File**: tests/test_comprehension_10678.py
- **Line**: 73–78
- **Severity**: warning
- **Issue**: The regex for AC3 scenario `resolvable-reference-execute` matches both question 1 (`resolvable-ref-execute`) AND question 2 (`no-catalog-row-error`), weakening the guard against deletion of the intended question.

- **Evidence**: The regex is:
  ```
  (resolve|look\s*up|catalog).*(read|source\s*path|execute|fetch)
  ```
  Question 2's prose (line 16) — "**Read** docs/COMPOSE-ARCHITECTURE.md §4.5 and docs/sub-skill-**catalog**.md" — matches group 1 ("catalog") and group 2 ("Read"). Question 2's expected answer (line 17) — quoting §4.5 step 3: "catalog entry's **source path** missing on disk" — also matches both groups. If question 1 (`resolvable-ref-execute`) were deleted, the validator would still pass via question 2's spurious match. The regex does not require any language about actually *executing* a resolved reference (beyond the word "execute" in question 1's ID — see Finding 3).

- **Suggested fix**: Make the regex more specific to the "resolve and execute" behavior, e.g.:
  ```python
  (
      "resolvable-reference-execute",
      r"(resolve|look\s*up|catalog\s+entry).*"
      r"(source\s+path|read\s+(that|the)\s+file|execute|fetch)",
  ),
  ```
  This requires `resolve` or `look up` or `catalog entry` (not just the word "catalog" from a filename) and requires `source path`, `read that file`, `read the file`, `execute`, or `fetch` (not just "Read" as the first word of the prompt).

---

### Finding 3

- **File**: tests/test_comprehension_10678.py
- **Line**: 100
- **Severity**: warning
- **Issue**: `question_blob` prepends the question ID to the prose, allowing the ID alone to satisfy regex matches independent of the actual question content.

- **Evidence**: Line 100:
  ```python
  question_blob = f"{q['id']} {q['question']}"
  ```
  Question 1's ID is `resolvable-ref-execute`, which contains "**resolve**" (group 1) and "**execute**" (group 2). The `resolvable-reference-execute` regex `(resolve|look\s*up|catalog).*(read|source\s*path|execute|fetch)` matches this ID alone — `resolve.*execute` spans `resolvable-ref-execute`. This means if someone rewrote question 1's prose to be about an entirely different topic while keeping the ID, the validator would still pass because the ID alone satisfies both regex groups. The docstring on line 67 says "The match is two-sided: the regex must appear in the **question prose** AND in the expected answer" — including the ID in the blob violates this intent.

- **Suggested fix**: Exclude the question ID from the blob:
  ```python
  question_blob = q["question"]
  ```
  Or, alternatively, keep the ID in the blob but ensure no regex can be satisfied by ID substrings alone (e.g., by anchoring with word boundaries or using more specific patterns as in Finding 2's fix).
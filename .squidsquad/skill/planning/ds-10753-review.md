I've completed my thorough analysis of both the W3 relaxation and the W2 semantic change. Here are my findings:

---

### Finding 1

- **File**: `references/scripts/l4_mini_cq.py`
- **Line**: 174
- **Severity**: warning
- **Issue**: The W3 relaxation causes `classify_reply("go away")` to return `"approve"`. `"go"` matches as a 1-word approval prefix in `_APPROVAL_TOKENS`, and `"away"` is not in `_REJECTION_TOKENS`, so the combined check (`_starts_with_approval_prefix` AND `not _has_rejection_in_rest`) passes. But "go away" is a dismissal — semantically it means "leave me alone / stop," not "proceed with the L4 write."

- **Evidence**: The docstring at lines 138-141 explicitly says the classifier "stays CONSERVATIVE: any negation in the rest of the reply … demotes the match to `"ambiguous"`. False approvals are worse than a re-prompt because they commit an L4 write the human didn't intend." Yet `"go away"` — clearly not an approval — passes both guards. The same pattern applies to `"go back"` (could mean "undo/revert"), `"go somewhere else"`, etc. The single-word token `"go"` has unusually high false-positive collision surface because it appears in many dismissal/directional phrases that are not approvals.

- **Suggested fix**: Add `"away"` and `"back"` to `_REJECTION_TOKENS`, or better — since `"go"` as a one-word approval token collides with too many non-approval phrases — treat `"go"` specially: require it to be alone or followed only by approvable filler (e.g., `"go ahead"`, `"go for it"`), not by arbitrary unrecognized words.

---

### Finding 2

- **File**: `references/scripts/l4_mini_cq.py`
- **Line**: 174
- **Severity**: warning
- **Issue**: `classify_reply("y not")` returns `"approve"`. `"y"` matches as a 1-word approval prefix in `_APPROVAL_TOKENS`, and `"not"` is **not** in `_REJECTION_TOKENS` — only `"don't"` and `"do not"` are. Standalone `"not"` is missing from the rejection set. In the context of a confirmation prompt ("Adding X under Y of Z — OK?"), `"y not"` nearly always means "why not?" — a questioning response that should be `"ambiguous"` per the docstring.

- **Evidence**: The docstring at lines 125-128 says `"ambiguous"` is the right bucket for "follow-up question, partial sentence, the human asking for clarification." A reply of `"y not"` to a confirmation prompt is the human asking "why not?" — a question, not an approval. The comment at line 101 says this code was specifically added to catch `"y please"` as an approval, but it also inadvertently catches `"y not"` because `"not"` is absent from `_REJECTION_TOKENS`. Similarly, `"ok never"` would pass because `"never"` is not in the rejection set (only `"never mind"` / `"nevermind"` are), and `"do it not"` would pass for the same reason.

- **Suggested fix**: Add `"not"` to `_REJECTION_TOKENS`. This is the right call because standalone `"not"` after an approval prefix is overwhelmingly a negation signal in the mini-CQ context. The counter-example `"ok not a problem"` would become `"ambiguous"` instead of `"approve"`, but that's a single re-prompt — the conservative bias the docstring already endorses. Alternatively, keep `"not"` out but add `"y"` to a list of short tokens that require the rest-words to be explicitly in a politeness/filler allowlist (e.g., `"please"`, `"thanks"`, `"now"`).

---

### Finding 3

- **File**: `references/scripts/l4_mini_cq.py`
- **Line**: 92 (function signature), 104-112 (body)
- **Severity**: warning
- **Issue**: `_starts_with_approval_prefix(cleaned, parts)` accepts parameter `cleaned` but never uses it. The body only references `parts` and `n` (derived from `parts`). The docstring says "True iff `cleaned` begins with..." but `cleaned` is a dead parameter. This is misleading to maintainers.

- **Evidence**: Line 174 is the only call site: `_starts_with_approval_prefix(cleaned, parts)` — both arguments are passed. Inside the function (lines 104-112), only `parts` is read. The parameter-name `cleaned` in the docstring implies the function receives the full cleaned string, but it only operates on the already-split token list. If a future maintainer adds logic that depends on `cleaned` (e.g., checking the string before splitting), they'd be working with a parameter that happens to be passed but isn't validated.

- **Suggested fix**: Remove the `cleaned` parameter from the function signature — it's a private (`_`-prefixed) helper with a single call site in the same module. Update the docstring accordingly: "True iff `parts` begins with..."

---

### Finding 4

- **File**: `references/scripts/l4_recompose_recovery.py`
- **Line**: N/A (no issue found for W2)
- **Severity**: N/A
- **Issue**: The W2 semantic change is **safe**. I found no existing caller that relied on `wait_for_recompose` returning `status="failure"` when `check_recompose_fn=None`.

- **Evidence**:
  1. The **orchestrator** `recover_on_recompose_failure` (line 382) short-circuits when `check_recompose_fn is None`, returning `path_chosen="skip"` without ever calling `wait_for_recompose`. The orchestrator is unaffected.
  2. The **sub-skill prose** (`l4-curation.md` line 143) calls only `recover_on_recompose_failure`, not `wait_for_recompose` directly.
  3. The **only call site** for `wait_for_recompose` in production code is the orchestrator itself at line 393 — which is only reached when `check_recompose_fn is not None`.
  4. The **only direct callers** of `wait_for_recompose` with `check_recompose_fn=None` are in the test suite (`test_l4_recompose_recovery_c7.py` lines 187, 429), and those tests were updated to expect `status="skip"` as part of this same PR.
  5. The **audit report** (`AUDIT-PRD-C-DS-REVIEW.md` line 43-45) confirms the old behavior was a semantic mismatch: "A direct caller (or future code path) would see `status="failure"` and could incorrectly trigger a revert path." The change fixes this.

  **Minor note**: The comment at line 195 references a function name `recover_from_l4_write` that doesn't exist — the actual function is `recover_on_recompose_failure`. This is a docstring drift but not a code bug.

---

## Summary

| Area | Verdict |
|---|---|
| **W3 relaxation** | Two false-positive risks found ("go away" → approve, "y not" → approve). Both stem from gaps in the `_REJECTION_TOKENS` set — `"away"` and `"not"` are missing. The conservative philosophy stated in the docstring (false approvals worse than re-prompts) is undermined by these gaps. |
| **W2 semantic change** | No issue found. The change is well-isolated: the orchestrator already guarded against the `None` case at its entry point, and no production code calls `wait_for_recompose` directly with `check_recompose_fn=None`. The change aligns the standalone function with the orchestrator's existing `"skip"` semantic and fixes a real risk of spurious reverts. |
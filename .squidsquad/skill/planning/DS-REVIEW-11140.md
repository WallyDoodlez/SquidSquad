### Finding 1

- **File**: `references/roles/SOUL.md`
- **Line**: 9 (the intro paragraph ending), followed by line 11 (the pre-existing italic line)
- **Severity**: warning
- **Issue**: The orientation intro's final clause duplicates the adjacent existing italic line, creating back-to-back redundancy that wastes tokens and reads awkwardly.

  The intro paragraph ends with:
  > The subsections below are those defaults; **a human directive always overrides them.**

  The immediately following line reads:
  > _Human instructions always override these defaults. When overriding, comply and note the deviation in Discussion._

  These are two adjacent sentences conveying the same override hierarchy. The intro's clause ("a human directive always overrides them") and the italic line's opening ("Human instructions always override these defaults") are semantically identical — same subject (human authority), same object (the Soul defaults), same relationship (override). The italic line is the canonical statement and carries the compliance detail; the intro's trailing clause adds no new information.

- **Evidence**: The task acceptance criteria direct that orientation intros cover **purpose** — what the section is, how the reader uses it, and its relationship to adjacent sections — and explicitly state: "do NOT restate the H3+ specifics." The intro already satisfies the purpose requirement with the preceding sentence ("When a situation isn't covered by an explicit instruction, this is what you fall back on"), which establishes the fallback role without restating the override rule that the next line already delivers with full precision. The trailing clause is redundant with adjacent prose and crosses from purpose into mechanics.

- **Suggested fix**: Drop the final clause so the intro paragraph ends at "The subsections below are those defaults." (with period), letting the existing italic line carry the override instruction alone:

  > This section is how you think and carry yourself — the durable temperament, values, and judgment defaults that shape every decision, as distinct from the *what* of Responsibility and the *how-to* of Agent Functions. When a situation isn't covered by an explicit instruction, this is what you fall back on. The subsections below are those defaults.

  Then the italic line follows naturally as the operational directive it has always been.
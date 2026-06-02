Now I have a thorough picture. Let me compile my findings.

---

### Finding 1

- **File**: `references/scripts/model_router.py`
- **Line**: 538–546
- **Severity**: error
- **Issue**: `l4-conflict-preempt` task type is not registered in the `template_map` dict. The `l4_conflict_preempt.py:preempt_conflict()` function dispatches to `model_router.route(task_type="l4-conflict-preempt", ...)` (line 198), and a purpose-built prompt template exists at `references/prompts/l4-conflict-preempt.md.j2`. But `_load_prompt_template` at line 538–546 only includes `"l4-audit"` (line 545) — the `"l4-conflict-preempt"` key is absent. When a task type is missing from the map, `assemble_prompt` (line 596–614) falls back to a bare generic prompt that lacks all the structured conflict-analysis instructions (quote-anchored contradiction check, sub-skill-reference exemption, step-id locality, "different emphasis is not contradiction", etc.).
- **Evidence**: PRD-C C8 requires Gate 0 to "check for materially contradicting prose" using the vocabulary from B4's `conflict_detector.py`. The template at `references/prompts/l4-conflict-preempt.md.j2` encodes this vocabulary and decision procedure explicitly (lines 27–37, 42–56). Without the template, the model sees a generic prompt (`f"Task: {context}\n\nInput files:\n\n{file_contents}\n\nProduce a structured analysis document."` — model_router.py lines 600–603), which cannot reliably execute the structured contradiction analysis C8 requires. This is a functional gap — Gate 0 would operate in degraded mode.
- **Suggested fix**: Add `"l4-conflict-preempt": "l4-conflict-preempt.md.j2"` to the `template_map` dict at model_router.py line 546 (alongside the existing `"l4-audit"` entry). Also add `"l4-audit"` and `"l4-conflict-preempt"` entries to the `key_map` dict at line 137 for proper model routing.

---

### Finding 2

- **File**: `references/sub-skills/common/l4-curation.md`
- **Line**: 12–13, and Step 8 (lines 114–148)
- **Severity**: warning
- **Issue**: Gate count inconsistency between the sub-skill header, Step 8, and the PRD specification. Line 12 says "the four safety gates (DeepSeek audit → mini-CQ → compose dry-run → atomic write/commit/push)." But Step 8 actually describes **six** gate stages: Gate 0 (conflict pre-emption, C8), Gate 1 (DS audit, C3), Gate 2 (mini-CQ, C4), Gate 3 (compose dry-run, C5), Gate 4 (atomic write/commit/push, C6), and Gate 5 (recompose recovery, C7). The PRD headline at line 1 says "three safety gates (DS audit + mini-CQ + dry-run)." Agents reading this at runtime get contradictory signals about which gates exist and when they fire.
- **Evidence**: The sub-skill's own prose is internally contradictory. Line 12 says "four" but enumerates a chain that omits pre-emption and recompose. Step 8 then adds Gate 0 (line 115) and Step 9 adds Gate 5 (line 143). An agent following the instructions literally could skip the pre-emption check (not mentioned in the header's "four gates") or fail to poll for recompose (presented as a separate "race" step rather than a numbered gate).
- **Suggested fix**: Update line 12 to read "the six gate stages" or similar, listing all gates in order: conflict pre-emption → DS audit → mini-CQ → compose dry-run → atomic write/commit/push → recompose recovery. Align with the PRD by distinguishing the three "safety gates" (DS audit, mini-CQ, dry-run) from the full gate chain.

---

### Finding 3

- **File**: `references/scripts/l4_mini_cq.py`
- **Line**: 134–136
- **Severity**: warning
- **Issue**: The explicit head-token list for multi-word approval classification omits several legitimate approval tokens that exist in `_APPROVAL_TOKENS`. Specifically: `"y"`, `"k"`, `"yup"`, and the head words of multi-word tokens like `"do"` (from `"do it"`), `"looks"` (from `"looks good"`), `"ship"` (from `"ship it"`). This means common affirmative replies followed by extra words fall through to `"ambiguous"`: "y please", "k thanks", "do it now", "looks good thanks", "ship it please".
- **Evidence**: The classifier at lines 121–143 is intentionally conservative per the comment at lines 95–98 ("False approvals are worse than a re-prompt"), and the PRD C4 AC says the trigger is "an explicit 'yes / approved / go'" — which the head list covers. However, "do it" is canonically an approval token (in `_APPROVAL_TOKENS`), yet "do it now" (a clear amplification) is classified as ambiguous because "do" alone is not in the head list. This creates a narrow usability gap where the 2-strike rule (sub-skill line 130) can cause abandonment on what a human would consider a clear yes.
- **Suggested fix**: Expand the head list at line 134–136 to include `"y"`, `"k"`, `"yup"`, `"do"`, `"ship"`, and `"looks"`, or alternatively, add a pre-check: if the full phrase stripped of trailing words matches any multi-word approval token exactly, count it as approve. This keeps the conservative design (mixed-signal detection still works) while avoiding false-ambiguous on clear affirmations.

---

### Finding 4

- **File**: `references/scripts/l4_recompose_recovery.py`
- **Line**: 172–180
- **Severity**: warning
- **Issue**: `wait_for_recompose` returns `RecomposeOutcome(status="failure", ...)` when `check_recompose_fn is None`. While the orchestrator `recover_on_recompose_failure` guards this at its entry (line 356–365, returning `path_chosen="skip"`), the standalone `wait_for_recompose` function returns a semantically misleading status. A direct caller (or future code path) would see `status="failure"` and could incorrectly trigger a revert path. The correct sentinel for "recovery not configured" should be distinct from an actual recompose failure.
- **Evidence**: The docstring at line 26–29 says the PRD-E harness-watch contract is wired through `check_recompose_fn`, and when it's `None` the expected path is `"skip"`. But `wait_for_recompose` returns `"failure"` in this case (line 174), while the orchestrator returns `"skip"`. The inconsistency means the same condition produces different outcomes depending on which entry point is called. A future caller of `wait_for_recompose` directly (e.g., from a test or a new code path) would misinterpret the None-guard as a real recompose failure and could trigger an unnecessary revert.
- **Suggested fix**: Change `wait_for_recompose` to return `RecomposeOutcome(status="not-configured", ...)` when `check_recompose_fn is None`, or raise a distinct exception. Keep the orchestrator's early-return as-is for backward compatibility. Alternatively, document that `wait_for_recompose` must only be called after the caller has already confirmed `check_recompose_fn is not None`.
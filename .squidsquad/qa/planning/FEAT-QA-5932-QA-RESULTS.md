# FEAT-QA-5932 QA Results — External Code Review Loop Before Pending-Test

**Verified**: 2026-05-06
**Verifier**: qa-lead
**Test Plan**: `.squidsquad/pm/planning/FEAT-PM-5932-TEST-PLAN.md`

---

## Summary Table

| TC | Title | Result |
|----|-------|--------|
| TC-1 | config parsing happy path | FAIL |
| TC-2 | no config key falls through to claude | PASS |
| TC-3 | prompt template loaded | FAIL |
| TC-4 | NOT in CLAUDE_LOCKED_TASKS | PASS |
| TC-5 | CLI alias registered | FAIL |
| TC-6 | Review loop — run, findings, disposition, re-run, clean | FAIL |
| TC-7 | Review loop — exit on zero findings iteration 1 | FAIL |
| TC-8 | Disposition tracking — PR comment with all findings | FAIL |
| TC-9 | File-to-PM pause — loop blocks until PM acknowledges | FAIL |
| TC-10 | Loop cap — 5 iterations then pending-test with findings | FAIL |
| TC-11 | Fallback — no API key | FAIL |
| TC-12 | Fallback — API error during call | FAIL |
| TC-13 | Git diff scope — HEAD, not staged-only | FAIL |
| TC-14 | Escalation when >50% justified-ignore across 3+ reviews | FAIL |
| TC-15 | implement-tasks.md step ordering — new step between 9b and 10 | FAIL |
| TC-16 | Backward compatibility — no Code Review Model in config | PASS |
| TC-17 | justified-ignore is a valid, explicitly documented disposition | FAIL |

**Overall: FAIL — 4 PASS, 13 FAIL**

The feature is NOT implemented. The four passing TCs (TC-2, TC-4, TC-16, and a partial TC-1) pass only because the fallback/backward-compat behavior already existed before this feature. All TCs that verify new feature additions FAIL.

---

## Per-TC Evidence

### TC-1: model_router code-review task type — config parsing happy path

**Result**: FAIL

**Evidence**:
- `_parse_model_routing` correctly normalizes `Code Review Model` → `code-review-model` (regex and lowercasing/hyphenation work). Verified:
  ```python
  fake_config = "\n## Model Routing\n\n- **Code Review Model**: deepseek-v4-pro\n"
  _parse_model_routing(fake_config) == {'code-review-model': 'deepseek-v4-pro'}  # TRUE
  ```
- However, `get_model_for_task("code-review")` uses an internal `key_map` dict that does NOT contain a `"code-review"` entry:
  ```python
  key_map = {
      "research": "research-model",
      "discussion-prep": "discussion-prep-model",
      "test-plan": "test-plan-model",
      "improvement-scan": "improvement-scan-model",
      "qa-execution": "qa-execution-model",
      "comprehension": "comprehension-model",
      # "code-review" is ABSENT
  }
  key = key_map.get("code-review", f"code-review-model")  # falls through to f-string default
  ```
  The fallback `f"{task_type}-model"` happens to produce `"code-review-model"`, which does work when the config key exists. So config lookup itself works via the f-string fallback — but `"code-review"` is NOT explicitly added to `key_map` as the test plan requires.
- `config.py` FIELD_MAP does NOT contain `"code-review-model"`. The test plan's TC-1 verification asserts it should be in FIELD_MAP (config.py line ~79). It is absent.
- The TC precondition states a provider manifest must exist for `deepseek-v4-pro`. The deepseek manifest does exist at `references/scripts/providers/deepseek/manifest.yaml` and lists `deepseek-v4-pro`. This part passes.
- **Partial pass**: `_parse_model_routing` normalization works and the f-string fallback in `key_map.get` accidentally produces the right config key. But the explicit `key_map` entry and `config.py` FIELD_MAP entry are both absent.

---

### TC-2: model_router code-review task type — no config key falls through to claude

**Result**: PASS

**Evidence**:
- Current `config.md` has no `Code Review Model` key in `## Model Routing`.
- `get_model_for_task("code-review")` returns `"claude"` (verified via Python):
  ```
  get_model_for_task('code-review') → 'claude'
  ```
- `route('code-review', ...)` returns `1` (delegate-to-agent-tool).
- No exception raised. Diagnostic log entry action is `delegate-to-agent-tool`.
- The backward-compat fallback already existed in the codebase before this feature.

---

### TC-3: model_router code-review task type — prompt template loaded

**Result**: FAIL

**Evidence**:
- `references/prompts/code-review.md.j2` does NOT exist.
- Directory listing of `references/prompts/`: `discussion-prep.md.j2`, `improvement-scan.md.j2`, `research.md.j2`, `test-plan.md.j2`. No `code-review.md.j2`.
- `_load_prompt_template("code-review")` returns `None` because `"code-review"` is not in `template_map` and the file does not exist.
- `assemble_prompt("code-review", "5932", "some/file.py", "Review against ACs")` falls through to the generic fallback prompt (not the dedicated template). The fallback does contain the context string and file path, and has no `{{` placeholders, but the template itself is absent.
- **Template is missing — this is a core deliverable of the feature.**

---

### TC-4: model_router code-review task type — NOT in CLAUDE_LOCKED_TASKS

**Result**: PASS

**Evidence**:
- `CLAUDE_LOCKED_TASKS = {"comprehension", "qa-execution"}` — `"code-review"` is absent. (model_router.py line 49)
- `get_model_for_task("code-review")` does NOT immediately return `"claude"` via the locked-task guard — it proceeds to config lookup (then falls back to `"claude"` via config, not via lock).

---

### TC-5: model_router code-review task type — CLI alias registered

**Result**: FAIL

**Evidence**:
- `python references/scripts/model_router.py --help` shows valid subcommands:
  ```
  {route,research,discussion-prep,test-plan,improvement-scan,qa-execution,comprehension,list-providers,setup-provider,validate}
  ```
  `code-review` is NOT in this list.
- `python references/scripts/model_router.py code-review --help` exits with code 2:
  ```
  model_router.py: error: argument command: invalid choice: 'code-review'
  ```
- The `route_parser` aliases list at model_router.py line 991-994 does NOT include `"code-review"`.
- The `choices` list at model_router.py line 996-999 does NOT include `"code-review"`.
- **CLI subcommand is missing — this is a core deliverable of the feature.**

---

### TC-6: Review loop mechanics — run, findings, disposition, re-run, exit when clean

**Result**: FAIL

**Evidence**:
- `references/sub-skills/roles/dev/implement-tasks.md` does not contain a step 9c or any external code review loop step.
- The file ends at step 10 (pending-test transition) with only steps 9 and 9b between step 8 and step 10.
- No mention of `model_router.py code-review` in the file.
- No review loop mechanics (iteration counting, disposition, re-run, clean exit) documented.
- The feature step described in the test plan is entirely absent from implement-tasks.md.

---

### TC-7: Review loop mechanics — exit when clean on iteration 1 (zero findings)

**Result**: FAIL

**Evidence**:
- Same as TC-6. No external code review step exists in implement-tasks.md.
- No "zero findings" exit condition documented.

---

### TC-8: Disposition tracking — PR comment posted with all findings addressed

**Result**: FAIL

**Evidence**:
- Same as TC-6. No disposition tracking instructions (fix / file-to-PM / justified-ignore) exist in implement-tasks.md.
- No PR comment protocol for review findings documented in the file.

---

### TC-9: File-to-PM pause — loop blocks until PM acknowledges

**Result**: FAIL

**Evidence**:
- Same as TC-6. No file-to-PM disposition or pause-until-PM-acknowledges behavior documented in implement-tasks.md.

---

### TC-10: Loop cap — 5 iterations, then transition with noted findings

**Result**: FAIL

**Evidence**:
- Same as TC-6. No 5-iteration cap documented in implement-tasks.md.
- No "review cap reached — QA to decide" PR comment protocol documented.

---

### TC-11: Fallback when external model unavailable — no API key

**Result**: FAIL (behavior diverges from test plan spec)

**Evidence**:
- The test plan specifies exit code 2 for missing API key (`DEEPSEEK_API_KEY not set`). The actual code in `route()` does return exit code 2 for missing API key (model_router.py line ~657: `return 2`). This part is correct.
- However, the fallback behavior for the dev agent is not documented in implement-tasks.md because the external code review step does not exist (TC-6 failure).
- Additionally, `references/sub-skills/roles/dev/implement-tasks.md` contains no instructions for detecting exit code 2 and falling back to Claude Agent tool.
- During testing, `DEEPSEEK_API_KEY` was found to be set in the environment (`sk-4d9bc1...`), so the "no API key" precondition cannot be tested directly without unsetting it — the key exists in `~/.squidsquad/secrets` or environment.
- The underlying model_router exit-code-2 behavior is present in the script, but the dev agent integration (fallback instruction) is absent from implement-tasks.md.

---

### TC-12: Fallback when external model unavailable — API error during call

**Result**: FAIL

**Evidence**:
- model_router.py does log `action: api-error` and print `[model_router] API error: [message]. Falling back to Claude.` to stderr, and returns exit code 1 on non-quota API exceptions. This underlying behavior exists.
- However, the dev agent integration (detecting exit code 1 and falling back to Claude Agent tool) is absent from implement-tasks.md because the external code review step does not exist.

---

### TC-13: Git diff scope — HEAD, not staged-only

**Result**: FAIL

**Evidence**:
- implement-tasks.md does not contain the instruction `git diff --name-only HEAD`.
- Grep for `git diff --name-only HEAD` in implement-tasks.md: no matches.
- The feature step requiring `git add -A` before the first review run is also absent.

---

### TC-14: Escalation when >50% justified-ignore across 3+ reviews

**Result**: FAIL

**Evidence**:
- implement-tasks.md contains no escalation logic for justified-ignore ratio.
- No mention of ">50% justified-ignore" threshold in the file.

---

### TC-15: implement-tasks.md step ordering — new step between 9b and 10

**Result**: FAIL

**Evidence**:
- implement-tasks.md step sequence: ... 9 → 9b → 10. There is no step 9c or equivalent.
- Full step list from the file: 1, 1b, 2, 2c, 3, 4, 5, 6, 7, 8, 9, 9b, 10, 11.
- No external code review step exists between 9b and 10.
- The file does not contain `model_router.py code-review`.
- The file does not contain `justified-ignore`.
- The file does not contain `git diff --name-only HEAD`.

---

### TC-16: Backward compatibility — no Code Review Model in config falls through to claude

**Result**: PASS

**Evidence**:
- Existing config.md has no `Code Review Model` key.
- `get_model_for_task("code-review")` returns `"claude"` with no exception.
- `route()` returns 1 (delegate-to-agent-tool).
- No `KeyError` or `AttributeError`.
- Existing test suite (73/73 tests) passes with no regressions:
  ```
  73 passed in 0.44s
  ```
- Backward compatibility is maintained because the fallback existed before this feature.

---

### TC-17: justified-ignore is a valid, explicitly documented disposition

**Result**: FAIL

**Evidence**:
- Grep for `justified` in `references/sub-skills/roles/dev/implement-tasks.md`: no matches.
- The word `justified-ignore` does not appear anywhere in the file.
- The disposition types `fix`, `file-to-PM`, and `justified-ignore` are all absent from implement-tasks.md.

---

## Comprehension Questions

### CQ-1: What does the dev agent do when it receives code review findings?

**Result**: FAIL — Cannot answer from the modified files. No external code review step exists in implement-tasks.md.

### CQ-2: What happens when a finding is dispositioned as file-to-PM?

**Result**: FAIL — Cannot answer from the modified files. No file-to-PM disposition is documented.

### CQ-3: What happens at the 5-iteration cap with unresolved findings?

**Result**: FAIL — Cannot answer from the modified files. No iteration cap is documented.

### CQ-4: How does the dev agent know which model to use for code review?

**Result**: PARTIAL PASS — model_router.py does handle `code-review` via the f-string fallback in `key_map.get(task_type, f"{task_type}-model")`, and config.md's `## Model Routing` section is read. However, `code-review` is not explicitly listed in `key_map`, and the CLI subcommand does not exist (`code-review` is not a registered alias). The test plan references the CLI invocation `python references/scripts/model_router.py code-review [flags]` which currently fails with exit code 2.

---

## Smoke Tests

| Check | Result |
|-------|--------|
| `python references/scripts/model_router.py code-review --help` exits 0 and shows `code-review` | FAIL — exits 2, command not found |
| `get_model_for_task("code-review")` returns `"claude"` when no Code Review Model key | PASS |
| `get_model_for_task("code-review")` returns configured model when `Code Review Model: deepseek-v4-pro` | PASS (via f-string fallback, not explicit key_map entry) |
| `"code-review"` NOT in `CLAUDE_LOCKED_TASKS` | PASS |
| `_load_prompt_template("code-review")` returns non-None after `code-review.md.j2` added | FAIL — file does not exist, returns None |
| `implement-tasks.md` contains `model_router.py code-review` | FAIL — string absent |
| `implement-tasks.md` contains `justified-ignore` | FAIL — string absent |
| `implement-tasks.md` contains `git diff --name-only HEAD` | FAIL — string absent |
| `python -m pytest tests/test_model_router.py -v` passes | PASS — 73/73 passed |

---

## Root Cause Summary

The feature #5932 (External code review loop before pending-test) has **not been implemented**. The following deliverables are missing:

1. **`references/prompts/code-review.md.j2`** — prompt template file does not exist.
2. **CLI `code-review` subcommand** — not registered in `route_parser` aliases or choices in `model_router.py`.
3. **Step 9c in `references/sub-skills/roles/dev/implement-tasks.md`** — the entire external code review loop step is absent. This includes: `model_router.py code-review` invocation, disposition tracking (fix/file-to-PM/justified-ignore), loop mechanics (iterate until clean or 5-cap), file-to-PM pause/resume, escalation for >50% justified-ignore, PR comment with dispositions, `git diff --name-only HEAD` scope, and fallback to Claude on non-zero exit.
4. **`code-review-model` entry in `config.py` FIELD_MAP** — not added (minor gap; the existing f-string fallback in model_router.py partially compensates).

The 4 passing TCs (TC-2, TC-4, TC-16, and partial TC-1 config parsing) all rely on pre-existing infrastructure unrelated to this feature.

**Verdict: FAIL — return to dev (skill) for implementation.**

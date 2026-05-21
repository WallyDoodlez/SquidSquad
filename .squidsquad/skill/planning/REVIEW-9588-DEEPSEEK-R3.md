I've reviewed all the changed files against the five criteria. Here's my analysis:

---

## Criterion 1 — ralph-loop-overview.md sources: no `/loop` invocation, no `[INTERVAL]`

**All four fragments pass.**

| File | `/loop ` invocation? | `[INTERVAL]` placeholder? |
|---|---|---|
| `references/sub-skills/roles/dev/ralph-loop-overview.md` | No — only backtick-quoted mentions (lines 5,7,8) | No |
| `references/sub-skills/roles/dm/ralph-loop-overview.md` | No — same pattern (lines 5,7,8) | No |
| `references/sub-skills/roles/pm/ralph-loop-overview.md` | No — same pattern (lines 5,7,8) | No |
| `references/sub-skills/roles/qa/ralph-loop-overview.md` | No — same pattern (lines 5,7,8) | No |

The test at `tests/test_compose_9588.py:193-213` (`test_polling_fragment_source_does_not_invoke_loop`) parametrizes over all 4 role→entry mappings and asserts both `"/loop " not in src` and `"[INTERVAL]" not in src`. The backtick-quoted `` `/loop` `` on line 5 does not match the regex `/loop ` (space after "loop") because a closing backtick sits between "loop" and the space.

**Note**: `dev/ralph-loop-overview.md` still carries `[ROLE]` placeholders at lines 25-26 (`.squidsquad/[ROLE]/current-state` and `cycle.py status-bar [ROLE]`). This is correct — the three other roles hardcode their paths (dm, pm, qa), but dev's fragment is shared by `skill` and any future dev variants, so the placeholder is deliberate. The bootstrap teaching (see Criterion 3) tells the agent to substitute it at runtime.

---

## Criterion 2 — Bootstrap Step 4b owns the `/loop` invocation with `[INTERVAL]` substituted

**Confirmed.** The composed CLAUDE.md Step 4b contains:

```
/loop 30m execute one Ralph Loop cycle
```

with a concrete integer (`30m`), not the literal `[INTERVAL]`. The test at `tests/test_compose_9588.py:167-189` (`test_bootstrap_owns_loop_invocation_with_substituted_interval`) verifies:
- `[INTERVAL]` is absent from composed output (line 180)
- The regex `/loop \d+m execute one Ralph Loop cycle` matches (line 186)

No other section in the composed CLAUDE.md contains a `/loop` invocation. The polling fragment (Step 4c) is Read at runtime and explicitly tells the agent NOT to invoke `/loop` (lines 2-3 of each fragment: *"Do NOT re-invoke `/loop` here"*).

---

## Criterion 3 — Bootstrap teaches role-placeholder substitution; teaching survives compose

**Confirmed.** The bootstrap's placeholder teaching section in the composed CLAUDE.md spells out role-name and interval placeholders letter-by-letter ("uppercase R-O-L-E in square brackets", "uppercase I-N-T-E-R-V-A-L in square brackets") so compose does not substitute them away. The test at `tests/test_compose_9588.py:216-250` (`test_bootstrap_documents_role_runtime_substitution`) verifies all three conditions:

1. **Source** `boot-bootstrap.md` contains the heading `"Placeholder substitution inside runtime-loaded fragments"` (line 228) and mentions both `"Role-name placeholder"` and `"SQUIDSQUAD_ROLE"` (line 234).
2. **Composed output** for every role still contains `"Role-name placeholder"` (line 245) — proving compose did not mangle the teaching.

The teaching tells the agent: when you encounter `[ROLE]` in a runtime-loaded fragment, substitute your own `SQUIDSQUAD_ROLE` value. This maps directly to the `[ROLE]` tokens in `dev/ralph-loop-overview.md` lines 25-26.

---

## Criterion 4 — Regression tests pin all three invariants

**Confirmed.** `tests/test_compose_9588.py` contains nine test functions covering:

| Invariant | Test | Lines |
|---|---|---|
| (A) Polling fragments clean | `test_polling_fragment_source_does_not_invoke_loop` | 193-213 |
| (B) Bootstrap owns `/loop` | `test_bootstrap_owns_loop_invocation_with_substituted_interval` | 167-189 |
| (C) Placeholder teaching survives | `test_bootstrap_documents_role_runtime_substitution` | 216-250 |
| Bootstrap present in all roles | `test_composed_claude_contains_boot_bootstrap` | 80-91 |
| Mode fragments not inlined | `test_composed_claude_does_not_inline_mode_specific` | 95-104 |
| Polling path substituted per role | `test_polling_fragment_path_substituted_per_role` | 107-121 |
| Runtime paths exist on disk | `test_referenced_runtime_fragments_exist_on_disk` | 124-151 |
| DM events extra enumerated | `test_dm_bootstrap_enumerates_pr_merge_wait` | 154-164 |
| Legacy degraded-mode removed | `test_l1_base_unreachable_branch_removed` | 253-267 |

Parametrization covers all four roles (`skill`, `pm`, `qa`, `dm`). The mode-specific markers list (lines 56-65) includes all seven event fragments plus `ralph-loop-overview`. Dev→entry mapping (lines 38-43) correctly routes `skill` → `dev` for the polling fragment path check.

---

## Criterion 5 — Recovery from interrupted `/loop` path exists

**Confirmed at two points:**

1. **Bootstrap Step 4b** (composed CLAUDE.md): explicit block:
   > **Recovery from an interrupted `/loop`**: if a prior session ended without a cycle firing (e.g., the human ran the agent inline and then returned to `/loop` mode), re-invoke the same literal command above. Do not change the interval value.

2. **All four polling fragments** (line 3, and line 7-8): reference back to the bootstrap:
   > If you need to recover from an interrupted `/loop` (e.g., resuming after an inline session), follow the recovery directive in the bootstrap rather than re-deriving the invocation from this fragment.

   And:
   > To resume `/loop` mode after an inline session, re-run the recovery directive from the boot bootstrap.

The recovery path is self-consistent: the fragments defer to the bootstrap, and the bootstrap tells the agent to re-invoke the same literal `/loop 30m execute one Ralph Loop cycle` command.

---

## No new issues found

All five criteria are satisfied. The diff correctly implements PM's Option B: scheduler in bootstrap (compose-inlined → placeholder substitution works), source fragments stripped of `/loop` invocation, and the role-placeholder teaching survives compose. Regression tests are comprehensive and verify every invariant.

**NO_FINDINGS**
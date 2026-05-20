I have now thoroughly reviewed all changed files and verified the four R1 fixes. Here are my findings:

---

### Finding 5 (NEW)

- **File**: `references/scripts/compose.py`
- **Line**: 324
- **Severity**: warning
- **Issue**: Stale line-number reference in a code comment. The comment says "The check at line 311 (`m_base.startswith(base + "-") …`)" but the variant-resolution loop it describes now lives at lines 338–343 (after RUNTIME_READ_FRAGMENTS insertion shifted everything down, and the frozenset definition consumed lines 33–52). Line 311 in the current file is `manifest_set = set(manifest)` — not the variant check.
- **Evidence**: `references/scripts/compose.py:324` reads `# line 311 (`m_base.startswith(base + "-") …`) is otherwise` — the actual `m_base.startswith(base + "-")` expression is at line 340. A future maintainer doing a blame/annotate walk will jump to the wrong location.
- **Suggested fix**: Update the comment to reference the current line numbers, or replace with a description that doesn't depend on line numbers, e.g.: `# The variant-resolution fallback below (m_base.startswith(base+"-")…) is otherwise`.

---

### Verification of R1 Fixes

**Finding 1 (RUNTIME_READ_FRAGMENTS frozenset) — FIXED.**
- `references/scripts/compose.py:40-52`: The frozenset contains all 11 runtime-loaded fragments: 4 role polling fragments (`ralph-loop-overview` for dev/pm/qa/dm), 6 `common-events/*` fragments, and DM's `roles/dm/events/pr-merge-wait`. ✓
- `references/scripts/compose.py:327`: The check `if include_path in RUNTIME_READ_FRAGMENTS: continue` executes BEFORE the `manifest_set` check (line 333) and BEFORE the variant heuristic (lines 338-343). The `continue` skips inlining entirely. ✓
- Edge case verified: `common-events/l1-base` in the template would match frozenset entry `"common-events/l1-base"` even if a future manifest entry `common/l1-base-extended` would otherwise trigger the variant heuristic via `"l1-base-extended".startswith("l1-base-")`. The frozenset short-circuit prevents this. ✓

**Finding 2 (HTML comment sentinels in instructions.md) — FIXED.**
- `references/roles/pm/instructions.md:29-35`: Comment documents runtime-loading architecture, references `RUNTIME_READ_FRAGMENTS`, warns about regression test. ✓
- `references/roles/dm/instructions.md:31-38`: Same, plus explicitly calls out `pr-merge-wait` as runtime-loaded. ✓
- `references/roles/qa/instructions.md:29-35`: Same structure as pm. ✓
- `references/roles/dev/instructions.md:23-31`: Same, references both `includes.yml` and `includes-events.yml` by name. ✓
- All four comments accurately name `common/boot-bootstrap` as the runtime loader and `compose.py:RUNTIME_READ_FRAGMENTS` as the compose-time short-circuit. ✓

**Finding 3 (boot-bootstrap.md Step 1 missing-config guard) — FIXED.**
- `references/sub-skills/common/boot-bootstrap.md:10`: The first bullet now handles "`.squidsquad/config.md` does not exist or cannot be read (Read tool error, file absent, empty file)" → POLLING mode confirmed, skip Step 2, jump Step 4. ✓
- The remaining bullets (lines 11-13) handle per-role override, global default, and absent/unparseable field values — all after the missing-file guard. ✓
- The guard explicitly mirrors `compose.py:_get_wake_mode` behavior and cites CONTEXT-9588 D3. ✓

**Finding 4 (boot-bootstrap.md curl invocation) — FIXED.**
- `references/sub-skills/common/boot-bootstrap.md:21-23`: Curl command is `curl -sf --max-time 5 http://127.0.0.1:<port>/status` — no shell redirect (`> /dev/null` is gone), uses `/status` endpoint matching CONTEXT. ✓
- Line 24 documents: "no shell redirect is needed (older versions of this instruction used `> /dev/null`, which fails on native Windows shells)" — explicit rationale. ✓
- Line 24: "Inspect the exit code only: 0 = harness reachable; any non-zero exit … = harness unreachable" — unambiguous exit-code inspection. ✓
- `-s` silences progress output within curl; `-f` exits non-zero on HTTP errors. This works identically on Windows and POSIX. ✓

---

`NO_FINDINGS` for the other three findings — they are correctly fixed with no regressions. The one new issue (Finding 5) is a documentation-only stale line reference.
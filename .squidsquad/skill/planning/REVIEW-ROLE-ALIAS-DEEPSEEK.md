Now let me compile all findings. I have a clear picture of the issues.

---

### Finding 1

- **File**: `docs/HARNESS-ARCH.md`
- **Line**: 136
- **Severity**: error
- **Issue**: The event ID hash formula in §5.3 still says `role` instead of `alias`, contradicting both the diff's stated intent and the matching change already applied to `docs/AGENT-RUNTIME.md` line 354.
- **Evidence**: HARNESS-ARCH.md line 136 reads `event_id = sha256(timestamp + role + event_type + payload + nonce)[:16]`. The diff audit explicitly lists "Event ID hash input" as a change category ("`sha256(timestamp + role + ...)` → `sha256(timestamp + alias + ...)`"). AGENT-RUNTIME.md line 354 was correctly changed to `alias`. This file was missed.
- **Suggested fix**: Change `role` to `alias` on line 136 so it reads `sha256(timestamp + alias + event_type + payload + nonce)[:16]`.

---

### Finding 2

- **File**: `docs/HARNESS-ARCH.md`
- **Line**: 240–253 (§7.5)
- **Severity**: error
- **Issue**: The documented `.harness-state.json` JSON shape is substantially wrong compared to what `harness.py` actually persists. The doc invents fields that don't exist and omits several that do.
- **Evidence**: 
  - **Doc claims** `"version": 1` — code (line 404) writes no version field.
  - **Doc claims** inner `"role": "<categorical role>"` field — code (lines 408-426) writes no `role` field inside agent entries.
  - **Doc claims** `"pid": 12345` — code writes `claude_pid` and `terminal_pid` as separate fields.
  - **Doc omits** top-level fields: `harness_pid`, `start_time`, `port` (code lines 405-407).
  - **Doc omits** per-agent fields: `status`, `terminal_pid`, `bootup_complete` (code lines 414, 418, 423).
- **Suggested fix**: Rewrite the JSON shape to match the actual `save_state()` output at harness.py lines 404-427. The outer key for agents should be the alias value (which the code variable calls `role` — the doc's `<alias>` placeholder is conceptually correct). The inner fields should be `intent`, `intent_set_at`, `status`, `boot_time`, `clone_path`, `claude_pid`, `terminal_pid`, `bootup_complete`. The top level needs `harness_pid`, `start_time`, `port`. If the `"role"` inner field is meant as an aspirational future addition, call that out explicitly with a note.

---

### Finding 3

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 578
- **Severity**: error
- **Issue**: On-disk path `.squidsquad/<role>/cycle-input.json` in the §6.1 Ralph Loop cycle diagram uses `<role>` instead of `<alias>`. This is an on-disk path — directories are alias-keyed.
- **Evidence**: The same commit correctly changed all other on-disk paths in AGENT-RUNTIME.md (lines 210, 550-552, 1001) to `<alias>`. This one in the mermaid/code-block diagram was missed.
- **Suggested fix**: Change `.squidsquad/<role>/cycle-input.json` → `.squidsquad/<alias>/cycle-input.json`.

---

### Finding 4

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 301 (mermaid diagram)
- **Severity**: warning
- **Issue**: The EAD subgraph label `state-change → role mapping rules` uses `role` where it should say `alias`. The mapping resolves to a target alias, not a categorical role class.
- **Evidence**: The audit's Q3 table explicitly flagged lines 301–302 ("state-change → role mapping rules — wording check"). The diff applied to AGENT-RUNTIME.md changed the `_cursors` dict and cursor model prose to `alias` (lines 293, 348) but left this diagram node unchanged. The actual EAD logic (per AGENT-RUNTIME.md §4.4 and §7.3) maps forge changes to target aliases, not role classes.
- **Suggested fix**: Change `state-change → role<br/>mapping rules` → `state-change → alias<br/>mapping rules`.

---

### Finding 5

- **File**: `docs/INSTALLER-ARCH.md`
- **Line**: 242, 322 (and also 437, 443, 444, 474)
- **Severity**: warning
- **Issue**: Multiple on-disk path placeholders still use `<role>` instead of `<alias>` in sections that were not covered by the diff. The diff only changed lines 31, 98, 101, 104-105, and 299, leaving many other occurrences untouched.
- **Evidence**: 
  - Line 242: `.squidsquad/<role>/CLAUDE.md`
  - Line 322: `.squidsquad/<role>/CLAUDE.md`
  - Line 437: `.squidsquad/<role>/working-state.md`, `iterations/`, `planning/`
  - Line 443: `.squidsquad/<role>/CLAUDE.md`
  - Line 444: `.squidsquad/<role>/SOUL.md`
  - Line 474: `.squidsquad/<role>/working-state.md`, `iterations/`, `planning/`
  
  These are all in §4.9 (Phase 6), §6 (Helper scripts table), §10 (Upgrade flow), and §11 (Idempotency). These are all on-disk path references keyed by alias.
- **Suggested fix**: Change `<role>` → `<alias>` in all these on-disk path placeholders for consistency with the changes already made at lines 31, 98.

---

### Finding 6

- **File**: `docs/HARNESS-ARCH.md`
- **Line**: 72–73 (§4.1 API table)
- **Severity**: warning
- **Issue**: The `GET /agents` and `GET /agents/{role}` response shapes claim the response includes an `alias` field, but `AgentState.to_dict()` (harness.py lines 154-171) does not return an `alias` field — only `role` (which holds the alias value).
- **Evidence**: Doc line 72: `[{role, alias, intent, pid, clone_path, boot_time, ...}]`. Code `to_dict()` returns `role`, `status`, `intent`, ..., `clone_path`, `claude_pid`, `terminal_pid`, ... — no `alias` field, and `pid` doesn't exist (it's `claude_pid`/`terminal_pid`). The audit itself notes this discrepancy: "Note: `AgentState.to_dict()` actually only returns `role` (no `alias` field) — so doc and code are slightly inconsistent there."
- **Suggested fix**: Either (a) remove `alias` from the documented response shape and change `pid` to `claude_pid`, or (b) add a note that the response shapes are aspirational and don't match current code. The deliberate-not-change policy for §4 only covers path templates, not response shapes — if the response shape claims fields that don't exist, that's a doc-vs-code divergence.

---

### Finding 7

- **File**: `docs/AGENT-RUNTIME.md`
- **Line**: 1138 (§10.1 Glossary)
- **Severity**: warning
- **Issue**: The glossary defines "Cursor" as "per-role harness-owned pointer" — should be "per-alias" to match the cursor model documented at line 348 ("Per-alias, owned by harness") and the data structure at line 293 (`dict[alias, event_id]`).
- **Evidence**: The same commit changed §4.3 cursor model prose to "Per-alias" (line 348) and the `_cursors` dict type to `dict[alias, event_id]` (line 293), but the glossary entry wasn't updated to match.
- **Suggested fix**: Change "per-role harness-owned pointer" → "per-alias harness-owned pointer".

---

### Finding 8

- **File**: `docs/INSTALLER-ARCH.md`
- **Line**: 27, 165, 228, 309
- **Severity**: warning
- **Issue**: Prose still uses "per-role" in contexts describing alias-keyed structures (clones, directories, registries). The diff changed lines 31, 98, 101, 104-105, 299 but left these structurally identical usages untouched.
- **Evidence**:
  - Line 27: "The installer always sets up **per-role** clones" — clones are per-alias (one per agent instance).
  - Line 165 (Phase 0a tree): "per-role clone-path registry (one file per role)" — the registry is alias-keyed.
  - Line 228: "creates the **role dirs**" / "**per-role** SOUL.md files" — these are alias directories.
  - Line 309 (~/.squidsquad tree): "per-role clone-path registry — one file per role" — alias-keyed.
- **Suggested fix**: Change these prose descriptions to "per-alias" / "alias dirs" for consistency with the changes at lines 31, 98, 101, 104-105.

---

### Finding 9

- **File**: `docs/HARNESS-ARCH.md`
- **Line**: 295 (§9 vocabulary footnote)
- **Severity**: nit
- **Issue**: The vocabulary footnote says "A code-level rename `role` → `alias` would close the mismatch but is invasive (touches every HTTP route + most agent-side scripts) and not yet planned." The audit (#10358) has since been filed, so "not yet planned" is now stale.
- **Evidence**: The audit record `.squidsquad/skill/planning/REVIEW-ROLE-ALIAS-AUDIT.md` explicitly says the code rename is filed as #10358. The footnote text predates that filing.
- **Suggested fix**: Change "not yet planned" → "tracked in #10358" or similar to keep the footnote accurate.

---

### Finding 10

- **File**: `docs/HARNESS-ARCH.md`
- **Line**: 72 (§4.1) and 73 (§4.1)
- **Severity**: nit
- **Issue**: The response shape for `GET /agents/{role}/health` (line 74) documents `{role, alive, pid, last_seen}` — no `alias` field here, which is internally consistent with code. But line 73 documents `{role, alias, intent, pid, ...}` for `GET /agents/{role}` — the `alias` field inconsistently appears only on some response shapes. This makes the table internally inconsistent regardless of code accuracy.
- **Evidence**: Compare line 72 (`[{role, alias, intent, pid, ...}]`) with line 74 (`{role, alive, pid, last_seen}`). If `alias` is a real field, it should appear on all agent responses or be explained. The code returns no `alias` field anywhere.
- **Suggested fix**: Either consistently add `alias` to all response shapes (if aspirational) or remove it from all (to match current code). Don't mix.
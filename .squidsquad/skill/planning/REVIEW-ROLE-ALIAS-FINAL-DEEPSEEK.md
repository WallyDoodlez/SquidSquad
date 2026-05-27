I've reviewed all three changed files carefully against the five review questions. Here are my findings:

---

### Finding 1

- **File**: `docs/HARNESS-ARCH.md`
- **Line**: 83
- **Severity**: nit
- **Issue**: The aspirational note has an ambiguous "only" that could mislead a reader into thinking `AgentState.to_dict()` returns a single field.

  > Today `AgentState.to_dict()` returns a `role` field only (whose value is the alias) and no separate `alias` field.

  The natural reading of "returns a `role` field only" is "returns nothing but a single `role` field" — which is false; `to_dict()` returns many fields (`intent`, `clone_path`, `boot_time`, `claude_pid`, `terminal_pid`, etc.). The intended meaning is "returns a `role` field (with the alias as its value) but no separate `alias` field." The contrast is between `role` and `alias`, not between `role` and all other fields.

- **Evidence**: The same doc's §7.5 (line 237–257) shows the full `.harness-state.json` shape with ~10 fields. The aspirational table itself lists `intent`, `pid`/`claude_pid`, `clone_path`, `boot_time`, etc. A reader parsing "returns a `role` field only" literally would be confused.

- **Suggested fix**: Drop "only" or reposition it. Two options:

  > Today `AgentState.to_dict()` returns a `role` field (whose value is the alias) but no separate `alias` field.

  Or:

  > Today `AgentState.to_dict()` returns only a `role` field for agent identity — not a separate `alias` field.

---

### Answers to the five review questions (no findings beyond the NIT above)

**1. §4.1 aspirational note clarity:** The note is unambiguous for a new client author. It explicitly calls the shapes "aspirational," states that no `alias` field exists today, says `role`'s value IS the alias, and says to read `claude_pid` directly. The action guidance is concrete: "treat the alias as the value of `role` and read `claude_pid` directly." No risk of someone coding against a nonexistent `alias` field.

**2. §4.1 table consistency:** Clean. The per-agent endpoints now uniformly include `alias`:
- `/agents` — had `alias` already ✓
- `/agents/{role}` — had `alias` already ✓
- `/agents/{role}/health` — `alias` added ✓
- `/agents/{role}/config` — intentionally omits `role`/`alias` (config endpoint, not identity endpoint; caller supplies role/alias in the path) ✓
- `/agents/{role}/start`, `/stop`, `/restart` — `alias` added ✓

No missed rows. `/agents/all/start`, `/agents/all/stop`, and `/shutdown` are not per-agent endpoints.

**3. §4.4 label-rename framing (AGENT-RUNTIME.md L885):** Accurate. The blast-radius reasoning covers the right surfaces: every existing issue label, `tracker.py`, care-filter callers, and composed agent files. Additional concerns (GitHub label-search semantics, shell scripts, CI/CD filters) are implicitly subsets of "every existing issue label would need editing" and "every composed agent file that mentions `role:<name>`." The sequencing advice ("Revisit once #10358 has phased through code-side first") is sensible — change the code identifier first, then the GitHub label key.

**4. Cross-doc consistency:** No other `docs/` file needs the same legacy-key clarification. The grep across `docs/` shows:
- `AGENT-RUNTIME.md` — already updated at L885; table rows at L873-879 and PM-inbox list at L1102 merely *use* the convention, they don't describe it
- `docs/archive/EVENT-ARCHITECTURE.md` L637 — archived/non-canonical, explicitly kept for traceability per AGENT-RUNTIME.md's status banner
- `docs/VAULT-ARCH.md` L167 — different concept (`role:<name>` is a vault note tag prefix, not a GitHub issue label)

**5. Typos, broken cross-refs, lurking issues:** None. The line-reference in the audit record (`AGENT-RUNTIME.md §L885`) is correct. Both cross-references to `#10358` are consistent. No spelling or grammar issues beyond the NIT above.

---

**Overall:** The commit is clean beyond one minor wording ambiguity. The aspirational framing in §4.1 is sufficiently clear for a new client author, the table is internally consistent, the label-rename framing is accurate, and no cross-doc updates are needed.
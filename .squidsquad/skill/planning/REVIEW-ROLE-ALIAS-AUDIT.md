# role/alias vocabulary audit — review queue

Audit triggered by request: "audit the document, and fix all mentioning of just {role}" (in HARNESS-ARCH.md), then extended to other arch docs.

## Status

**RESOLUTION (2026-05-27):**
- **Q1 (code rename):** filed as **#10358** (`TASK: Complete role → alias identifier rename`), linked as sibling to #10182. Deferred until docs land + #10182 progresses.
- **Q3 + Q4 (Tier-1 doc fixes):** applied to AGENT-RUNTIME.md (7 edits) and INSTALLER-ARCH.md (5 edits). Committed alongside HARNESS-ARCH.md edits on PR #10357.
- **Q5:** VAULT-ARCH / COMPOSE / ARCHITECTURE confirmed clean.
- **Q6:** all doc edits landed on PR #10357 as a follow-up cleanup commit.
- **Q7 (role:* label):** deferred (mentioned in #10358 "Out of scope").

Historical record below.

## Key vocabulary distinction (for context)

- **L2 categorical role** = one of `pm` / `qa` / `worker` / `dm`. Fixed set, determines responsibilities/permissions.
- **Alias** = install-time agent instance name (`skill`, `verifier`, `human`, `fe-worker`, `be-worker`, etc.). One categorical role can map to multiple aliases per install. Aliases are what live as directory names under `.squidsquad/<alias>/` and what key harness state.

**The bug pattern:** the codebase uses the identifier `role` everywhere (FastAPI path params, `AgentState.role`, `SQUIDSQUAD_ROLE` env var, dict keys, CLI flags) but the VALUE is always the alias. Docs inherit this misleading vocabulary.

---

## Applied edits — HARNESS-ARCH.md (uncommitted)

| Section | Change |
|---|---|
| §5 table (lines 114–115) | `dict[role, event_id]` → `dict[alias, event_id]`; "Per-role progress" → "Per-alias progress" |
| §5.2 (line 126) | "Per-role, owned by harness" → "Per-alias, owned by harness" |
| §7.3 (line 221) | `.squidsquad/<role>/.claude-pid` → `.squidsquad/<alias>/.claude-pid` |
| §7.5 (line 244) | State-file shape: outer key `"<role>"` → `"<alias>"`; added `"role"` field with categorical-role semantics (now matches §9 + line 285 prose that says alias-keyed) |
| §9 (line 295) | Tightened the band-aid note to explicitly say "in every one of those places, the value is actually the alias" and acknowledge a code-level rename would close the mismatch but is invasive |
| §14.2 (lines 398–402) | "per-role PIDs" → "per-alias PIDs"; `SQUIDSQUAD_ROLE=<role>` → `SQUIDSQUAD_ROLE=<alias>` (with code-compat caveat); `/agents/<role>/restart` → `/agents/{alias}/restart` |

**Deliberately NOT changed in HARNESS-ARCH.md:**
- §4 HTTP API path templates (`/agents/{role}`, `/events/for/{role}`, etc.) — these faithfully reflect the actual FastAPI route definitions in `harness.py:1406, 1420, 1460, 1500, 1794, 1864, 1943, 2101, 2124`. Renaming them in the doc without renaming code would create doc-vs-code divergence.
- §4 response shapes (`{role, alias, ...}`, `{cursor, role}`) — match what the code returns. Note: `AgentState.to_dict()` actually only returns `role` (no `alias` field) — so doc and code are slightly inconsistent there, but it's not a `{role}` issue per se.
- `boot_agent(role)`, `--role` CLI flag, `event_poll.py --role` — actual code identifiers.

---

## Questions for you

### Q1. Code-level rename — yes/no?

The cleanest fix to the whole role/alias mess is a code-wide rename: FastAPI routes `{role}` → `{alias}`, `AgentState.role` → `AgentState.alias`, `SQUIDSQUAD_ROLE` env var → `SQUIDSQUAD_ALIAS`, `--role` CLI flag → `--alias`, etc.

- **Pros:** vocabulary finally matches what the code actually does. Docs become unambiguous. New contributors stop being confused.
- **Cons:** invasive — touches every HTTP route in `harness.py`, every agent-side script that POSTs to the harness, the `event_poll.py` CLI, possibly `cycle_pre.py`/`cycle_post.py`, the env var name. Requires a migration plan (backward-compat shim period? hard cutover?). Big PR.

**Options:**
- (a) Plan the rename as a phased PR (route aliasing first → migrate clients → drop old names).
- (b) Hard cutover in one PR.
- (c) Leave code as-is; doc keeps the band-aid note (current state of HARNESS-ARCH.md §9).
- (d) Do nothing for now; revisit later.

### Q2. Should the JSON response field name `role` change to `alias`?

`AgentState.to_dict()` returns `{"role": <alias-value>, ...}`. Any TUI/CLI client reading this sees a field named `role` whose value is the alias. Even if you keep the path param `{role}` for now, you could:
- (a) Add an `alias` field alongside `role` (deprecate `role` later).
- (b) Rename `role` → `alias` in the response (breaks any existing client).
- (c) Leave it.

This is independent of Q1's path-param question.

### Q3. AGENT-RUNTIME.md — apply the same surgical fixes (Tier 1)?

Subagent identified ~15 clear fixes in AGENT-RUNTIME.md, same pattern as HARNESS-ARCH.md (on-disk paths, internal data structures). Specific items:

| Line | Fix |
|---|---|
| 209 | `.squidsquad/<role>/.claude-pid` → `<alias>` (prose) |
| 293 | `dict[role, event_id]` → `dict[alias, event_id]` |
| 301–302 | "state-change → role mapping rules" — wording check |
| 348, 352, 354 | "per-role cursor"/"Per-role, owned by harness"/`sha256(… + role + ...)` — alias semantics |
| 472, 506 | `event.role == my_role` filter prose |
| 547–552, 1003–1009 | `.squidsquad/<role>/...` paths → `<alias>` |

Plus all the §4-style API path-param references — same Q1 dependency.

**Options:**
- (a) Apply Tier-1 fixes (paths + internal structures) tomorrow; defer API-path fixes pending Q1.
- (b) Wait on Q1 first, then do everything in one pass.

### Q4. INSTALLER-ARCH.md — apply 6 clear fixes?

| Line | Fix |
|---|---|
| 31 | `~/.squidsquad/clones/<role>` → `~/.squidsquad/clones/<alias>` (registry is literally alias-keyed) |
| 98 | "one per role" → "one per alias" |
| 101 | `.squidsquad/<role>/` → `<alias>/` |
| 104–105 | "Per-role clone-path registry" → "Per-alias …" |
| 299 | `.local-config` "Per-clone role→path mapping" → "Per-clone alias→path mapping" |
| 273–290 | Placeholders like `<worker-role>/`, `<verifier-role>/` — subagent suggests leaving these because the surrounding prose clarifies they are preset-default names; could argue either way. |

**Note:** subagent flagged that the registry at `~/.squidsquad/clones/` literally has one file *per installed agent instance* (alias), not per role-class. That's a true alias-keyed structure.

### Q5. VAULT-ARCH.md, COMPOSE-ARCHITECTURE.md, ARCHITECTURE.md — leave alone?

Subagent found:
- **VAULT-ARCH.md:** 0 role/alias issues. (Separate concern: `owner:` field has some `-lead` drift, off-topic for this audit.)
- **COMPOSE-ARCHITECTURE.md:** 0 issues — this doc is already precise. It correctly uses *role-class* terminology where relevant (`compose.py deploy <role-class>` reads exactly one L4 file per role-class).
- **ARCHITECTURE.md:** 0 issues found.

**Decision needed:** confirm we leave these untouched? Or anything to flag?

### Q6. Commit strategy for the HARNESS-ARCH.md edits already applied?

The applied edits sit on top of PR #10357 (`docs/harness-direct-spawn-draft`). Options:
- (a) Commit + push to that PR as a follow-up cleanup commit (one-liner: "docs: HARNESS-ARCH §5/§7/§9/§14 — clarify alias-keyed vocabulary").
- (b) Park the edits uncommitted until you decide on Q1/Q2 (so the rename + doc cleanup land together if you go that direction).
- (c) Split into a separate PR off main (doesn't depend on #10357).

### Q7. The `role:*` GitHub-issue-label convention

AGENT-RUNTIME.md §L873–885 already documents that issues are labeled `role:<value>`, where `<value>` is the **alias**, not the categorical role-class. This is yet another vocabulary trap — the label *key* is `role`, but its *value* is alias-typed. Worth a callout in the doc? Or leave it as the prose-only clarification that already exists at line 885?

---

## Summary of pending decisions

1. **Big rename in code?** (Q1, Q2) — strategic, blocks the rest.
2. **Apply Tier-1 doc fixes to AGENT-RUNTIME.md + INSTALLER-ARCH.md?** (Q3, Q4) — ~21 mechanical fixes total. Independent of Q1 if scoped to paths/internal structures.
3. **Leave VAULT-ARCH / COMPOSE-ARCHITECTURE / ARCHITECTURE alone?** (Q5) — likely yes.
4. **HARNESS-ARCH.md commit?** (Q6) — current edits are uncommitted; PR #10357 is the natural home.
5. **Callout for `role:*` label?** (Q7) — minor.

I haven't pushed anything. Awaiting your call tomorrow.

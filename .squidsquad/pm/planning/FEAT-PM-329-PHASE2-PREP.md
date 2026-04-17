# FEAT-PM-329 Discussion Prep — Consistent Per-Cycle Reporting

## Question Categorization and Options

---

### Q1: Should `cycle.py log-iteration` become the single entry point for ALL roles, or should each role continue writing its own format (just unified)?

**Category**: Architecture / Consistency enforcement

#### Option A: All roles use `cycle.py log-iteration` (Recommended)

- **Pros**:
  - Format consistency enforced programmatically — drift is impossible
  - Single place to update if the format changes in the future
  - Easier to add new fields (one code change vs 5 template edits)
  - Reduces template complexity — roles call a script instead of embedding format instructions
- **Cons**:
  - Adds a runtime dependency on `cycle.py` for PM, QA, DM, Designer (currently only dev roles depend on it)
  - If `cycle.py` breaks, all roles lose iteration logging simultaneously
  - Requires extending `cycle.py` with role-aware arguments (e.g., `--role pm`, `--quiet`)

#### Option B: Each role writes its own format, but templates all use the same field set

- **Pros**:
  - No new runtime dependencies — each role is self-contained
  - A broken script only affects one role
  - Simpler change — just update 5 template files
- **Cons**:
  - Format drift will reoccur over time as templates are edited independently
  - Any format change requires editing 5 files plus `cycle.py`
  - No programmatic enforcement — relies on template discipline

#### Option C: Hybrid — `cycle.py` generates the format, templates include a fallback

- **Pros**:
  - Best of both: programmatic consistency when script works, graceful degradation when it doesn't
  - Roles can still log if `cycle.py` is unavailable
- **Cons**:
  - Most complex implementation — two code paths to maintain
  - Fallback format could drift from the script's format, defeating the purpose
  - Harder to test (need to verify both paths)

**Recommendation**: Option A. The consistency guarantee is the whole point of this task. A single entry point eliminates the class of problems that created this task in the first place.

---

### Q2: What fields should the unified format include?

**Category**: Scope / Information design

#### Option A: Common core + optional role-specific fields

Format includes a shared set of fields present in every log, plus clearly marked optional fields that roles populate only when relevant. Fields set to "n/a" when not applicable to a role.

- **Pros**:
  - No information loss — every role-specific field is preserved
  - Human readers see a consistent structure across all roles
  - `cycle.py` can conditionally populate fields based on `--role`
- **Cons**:
  - Logs for simple roles (DM, Designer) will have many "n/a" fields, adding noise
  - Larger format means more template text per cycle

**Proposed common core**: Date, Type (active/quiet), Issues Filed, Issues Verified, Tasks Progressed, Notes
**Proposed optional fields**: Human Check-in (PM), E2E Tests (PM/QA), Agent Health (PM/QA), Version Bumped (DM), Designs Progressed (Designer), Designs Completed (Designer), Features Delivered (DM)

#### Option B: Minimal common set only — drop all role-specific fields (Recommended)

Format includes only fields that are meaningful across all roles, plus a free-form Notes field for role-specific context.

- **Pros**:
  - Clean, compact logs that are easy to scan
  - No "n/a" noise — every field has a value for every role
  - Role-specific details go in Notes, keeping structure minimal
  - Easier to maintain long-term
- **Cons**:
  - Structured role-specific data (e.g., "Version Bumped: 0.7.0") becomes unstructured prose in Notes
  - Harder to programmatically parse role-specific fields from Notes

**Proposed fields**: Date, Type (active/quiet), Work Summary (free-form list of what happened), Notes

#### Option C: Superset of all roles' fields

Every field from every role appears in every log.

- **Pros**:
  - Zero information loss
  - Maximum parsability — every field is always present and structured
- **Cons**:
  - Very noisy — DM logs would have "Human Check-in: n/a", "E2E Tests: n/a", "Designs Progressed: n/a", etc.
  - Largest format, most template text
  - Adding a new role means adding fields to every other role's logs

**Recommendation**: Option B. The purpose of iteration logs is human readability and cycle-over-cycle scanning. A minimal core with a Notes field gives structure where it matters and flexibility where it doesn't. Role-specific structured data that needs programmatic parsing belongs in `current-state` or tracker comments, not iteration logs.

---

### Q3: What should the compact quiet-cycle entry look like?

**Category**: Behavior / UX design

#### Option A: 2-3 line condensed entry (Recommended)

```markdown
# [ROLE] Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Type**: quiet
```

- **Pros**:
  - Instantly recognizable as a quiet cycle — the `Type: quiet` marker is unambiguous
  - Minimal disk usage and git diff noise
  - Easy for `vault_remember.py` to detect (parse for `**Type**: quiet`)
  - Human can visually distinguish quiet from active logs at a glance
- **Cons**:
  - No additional context about what the agent was doing (or not doing) during the quiet cycle
  - Consecutive quiet entries look repetitive

#### Option B: Full format with all fields set to "none"/"n/a"

```markdown
# [ROLE] Iteration N

- **Date**: YYYY-MM-DD HH:MM
- **Type**: quiet
- **Work Summary**: none
- **Notes**: none
```

- **Pros**:
  - Consistent structure — every iter file has the same fields, simplifying parsing
  - No special-case logic needed in any consumer
- **Cons**:
  - Defeats the purpose of "compact" — most fields are noise
  - More git diff noise per quiet cycle
  - Repetitive and harder to scan visually

#### Option C: Single-line entry

```markdown
# [ROLE] Iteration N — quiet — YYYY-MM-DD HH:MM
```

- **Pros**:
  - Absolute minimum disk usage
  - Very easy to scan — one line per quiet cycle
- **Cons**:
  - Breaks the field-based structure (no `**Date**:` or `**Type**:` to parse)
  - Requires special parsing logic everywhere
  - Cannot be generated by the same `cycle.py` code path without branching

**Recommendation**: Option A. It preserves the structural markers (`**Date**:`, `**Type**:`) that consumers like `vault_remember.py` need, while being compact enough to not add noise. The `Type: quiet` field serves double duty as both a human-readable label and a machine-parseable marker.

---

### Q4: Should `vault_remember.py is_quiet()` be updated now or deferred?

**Category**: Compatibility / Regression prevention

#### Option A: Include in this task's scope (Recommended)

- **Pros**:
  - Avoids shipping a known regression — `is_quiet()` will malfunction if quiet cycles write files and the function still checks file existence/mtime
  - The fix is small and well-understood (parse for `**Type**: quiet` instead of checking mtime)
  - Keeps the blast radius self-contained — one task, one coherent set of changes
  - Research already identified the exact lines (57-82) and mitigation strategy
- **Cons**:
  - Slightly increases scope of an already moderate-size task
  - Adds `vault_remember.py` to the test surface

#### Option B: Defer to a separate issue, ship with a known regression

- **Pros**:
  - Smaller scope for this task
  - Separate issue gets its own focused testing
- **Cons**:
  - Ships a known regression — vault-remember runs on every cycle (false non-quiet detection)
  - Violates the "never ship with known gaps" principle
  - Creates urgency for the follow-up issue (it must ship immediately after, or vault-remember wastes cycles)
  - Two deployments instead of one

#### Option C: Defer, but disable vault-remember temporarily until the fix ships

- **Pros**:
  - No regression — vault-remember is off until the fix is ready
  - Smaller scope for this task
- **Cons**:
  - Vault-remember is a valuable feature; disabling it costs learning opportunities
  - Requires a config change to disable, then another to re-enable — two extra steps
  - Easy to forget to re-enable

**Recommendation**: Option A. The fix is small (change mtime check to content parsing), the regression is real (vault-remember runs wastefully on every cycle), and the project standard is "never ship with known gaps." Including it keeps the change atomic and avoids a mandatory follow-up.

---

## Optimal Question Order

The recommended discussion order, with rationale:

1. **Q1** (Architecture: single entry point vs inline templates) — This is the foundational decision. The answer to Q1 determines implementation approach for Q2 and Q3. If all roles use `cycle.py`, the format is defined in one place. If roles write inline, the format is defined in 5 template files. Must be decided first.

2. **Q2** (Field set: common core vs superset) — Depends on Q1. If `cycle.py` is the entry point, fields are arguments/flags. If inline, fields are template text. Either way, the field set must be locked before the quiet-cycle format (Q3) can be designed, since the quiet format is a subset of the active format.

3. **Q3** (Quiet-cycle format: condensed vs full vs single-line) — Depends on Q2. The quiet format is derived from the active format — it needs to know which fields exist before deciding which to omit. This is the least controversial question (all options work, it's mainly a readability preference).

4. **Q4** (vault_remember.py: now vs deferred) — Independent of Q1-Q3 technically, but controversial in terms of scope. Placing it last lets the human see the full picture of changes before deciding whether to add one more file to the scope. It is also the easiest to resolve — the project standard ("no shipping with gaps") strongly favors inclusion.

### Finding 1

- **File**: `references/sub-skills/common/vault-optimize.md`
- **Line**: 34
- **Severity**: warning
- **Issue**: Contradictory prose — line 10 states vault-optimize is **"always-on — there is no enable/disable toggle"** but line 34 still says **"or optimize is disabled"**. An LLM following these instructions would be confused about whether a disable mechanism exists.
- **Evidence**: The #13043 item 1 explicitly removed the config Enabled-gate; the sub-skill should reflect that the only remaining gates are the quiet-cycle gate, 20-note threshold, and cooldown. The clause "or optimize is disabled" contradicts the stated intent and leaves the LLM with no way to resolve the inconsistency at runtime.
- **Suggested fix**: Change line 34 to `If the vault is too small (<20 notes), the script exits cleanly with no output.` (drop the "or optimize is disabled" clause). If the intention is to also mention the lock, use `If the vault is too small (<20 notes) or the optimize lock is held, the script exits cleanly.`

---

### Finding 2

- **File**: `references/scripts/vault_check.py`
- **Lines**: 6–12 (module docstring)
- **Severity**: warning
- **Issue**: The `check-size` subcommand is implemented (line 398–401) but **omitted from the usage docstring**. Running `vault_check.py --help` will not list it.
- **Evidence**: `main()` dispatches `check-size` at line 398. Every other subcommand (`validate`, `check-structure`, `check-frontmatter`, `check-wikilinks`, `list-orphans`) appears in the docstring usage block. Users and LLMs relying on `--help` output will not discover this subcommand.
- **Suggested fix**: Add a line to the docstring after line 11, e.g.:
  ```
      python scripts/vault_check.py check-size           # Warn on galaxy notes >500 lines (advisory)
  ```

---

### Finding 3

- **File**: `references/sub-skills/common/vault-remember.md`
- **Lines**: 45–46 (category added), 79–82 (priority list unchanged)
- **Severity**: warning
- **Issue**: **STYLES** was added as a 5th reflection category (line 45–46, item #13043 section 3), but the **write-priority tiebreak list** (lines 79–82) was not updated. It still lists only three items (Decisions, Learnings, Patterns). When >2 candidates pass all gates, a STYLES candidate can never be selected for the top 2 — the LLM has no guidance on where styles rank relative to the other 4 categories.
- **Evidence**: The reflection prompt instructs the LLM to evaluate STYLES candidates and create `galaxy/style-*.md` notes if applicable. But the priority section that governs which candidates get written when budget is constrained silently excludes the new category. The LLM would correctly gate, dedup, and pass a STYLES candidate through all 4 gates, then hit the priority rule and have no way to rank it.
- **Suggested fix**: Extend the priority list to include STYLES, e.g.:
  ```
  4. Styles (convention drift is costly; capture early)
  ```
  (and optionally add PROJECT CONTEXT as 5th, though that was pre-existing). If styles are intentionally lowest-priority, state that explicitly: `Styles and Project Context are always deferred when >2 higher-category candidates pass gates.`

---

**Additional notes — no issues found:**

- **`run` alias dispatch** (item 2): `main()` line 574 correctly dispatches `cmd in ("full-sweep", "run")` to `run_optimize()`. The docstring was updated. The test `test_run_is_alias_for_full_sweep` verifies that `run` produces JSON output (not the "Unknown command" error path). Correct.
- **`source` in REQUIRED_FM_FIELDS** (item 4): `vault_check.py` line 25 now includes `"source"`; `check_frontmatter()` flags missing source; `vault-protocol.md` Level 1 field list and Creating Notes section both list `source`. The `VALID_SOURCES` set (line 31) and the validity check in `check_frontmatter()` are consistent. Test `test_missing_source_flagged` verifies flagging. Correct.
- **`check_galaxy_size()`** (item 5): Only iterates `galaxy_dir.glob("*.md")` — areas/projects/resources are structurally exempt. Returned warnings are printed but **not** added to `all_issues` in `validate()` (line 369, comment at 367–368), making it advisory. The `check-size` subcommand always exits 0 (line 401). The three size tests cover oversized warn, small OK, and area exemption. Correct.
- **No dangling `config.py` reference**: Grep confirms `config.py` does not appear in any changed file. The `_is_config_enabled()` function in `vault_optimize.py` reads from `config.md` (line 43) — this is the pre-existing gate whose removal is tracked as #13066 and is explicitly out of scope for this diff.
- **No other prose drift in vault-protocol.md**: The `source` field appears consistently in Level 1 required checks, Creating Notes, and the Confidence Levels / Wikilinks sections. The Note Size Guidance section aligns with `GALAXY_MAX_LINES = 500`. The `style-` prefix is already in `VALID_GALAXY_PREFIXES` (line 24).
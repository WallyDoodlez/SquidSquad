Now I have all the information needed. Here is the complete research document:

---

# FEAT-SKILL-5868-AC2-REVIEW Research — Event Reactions section parsing in config.py

## Summary

AC-2 of #5868 adds three functions to `references/scripts/config.py` (lines 207–312) for parsing and writing a `## Event Reactions` section in `config.md`. The functions — `get_event_reactions()`, `get_event_filters_for_role()`, and `write_event_reactions()` — are fully implemented but have **zero callers** anywhere in the codebase. They represent a section-based store (one `## Event Reactions` heading with `### role` subsections) rather than flat FIELD_MAP entries. The parsing regex logic is sound for expected inputs and gracefully degrades on missing/malformed data. The atomic write via tmp+replace is correct on both POSIX and Windows, but `re.sub` without a `count` argument could silently clobber duplicate sections in a malformed file.

**Recommendation**: Feasible with caveats. The three functions are well-structured and handle their core contract, but there are concrete bugs (unbounded `re.sub`, `get_event_filters_for_role` conflation of "absent" vs "empty"), a design tension with the test plan (TC-22 expects `config.py get pm-emits` via FIELD_MAP, but the section-based approach doesn't add FIELD_MAP entries), and no integration with `cycle_pre.py` yet. The write path has an atomicity inconsistency with `set_field` (which writes directly, non-atomically). These are fixable — none are structural blockers.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill — compose-time config" is an active high priority (role:skill). #5855 "Vault is static decision log" constrains how findings are stored. #5888 (compose skill) and #5856/#5622 (event bus) are listed as shipped dependencies.
- **Related decisions**: [[decision-local-config-priority]] — reinforces that `.squidsquad/config.md` is the authoritative config source, consistent with the design decision to put Event Reactions in config.md (not a separate file).
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — The event reactions config is consumed mechanically by `cycle_pre.py` (Python script), not parsed by LLM agents from prose. The section-based parsing in `config.py` implements this pattern correctly.
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files" — the atomic tmp+replace pattern in `write_event_reactions` aligns. "Never ship with failed TCs" — the lack of tests for these three new functions is a gap. "Primary platform: Windows 11" — the `with_suffix(".tmp")` call and `Path.replace()` behavior must work on Windows (they do).
- **Related learnings**: [[learning-atomic-migration-strategy]] — The research document emphasizes that the entire migration must ship atomically. The current state (functions implemented but not called) is an intermediate step — integration into `cycle_pre.py` and `compose.py` must complete before any single component goes live.

## Impact Analysis

- **Files touched**: 
  - `references/scripts/config.py` lines 207–312 (ALREADY DONE — three new functions)
  - `references/scripts/cycle_pre.py` — **NOT YET TOUCHED** — `_filter_events_for_role()` (line 386) and `_run_mechanical_reactions()` (line 398) still use hardcoded `_ROLE_EVENT_TYPES` dict; no import of new config functions
  - `references/scripts/compose.py` — **NOT YET TOUCHED** — no call to `write_event_reactions` from derivation/validation logic
  - `tests/test_config.py` — **NO EVENT REACTION TESTS EXIST**
  - `tests/test_config_functions.py` — **NO EVENT REACTION TESTS EXIST**
  - `tests/test_config_schema.py` — **NO EVENT REACTION TESTS EXIST**

- **Behavior changes**: None yet — the functions exist but are never called. When integrated:
  1. `cycle_pre.py` will optionally replace hardcoded `_ROLE_EVENT_TYPES` with config-driven filters via `get_event_filters_for_role()`
  2. `compose.py` will write the `## Event Reactions` section via `write_event_reactions()`
  3. Cross-agent validation will read via `get_event_reactions()`

- **Dependencies**:
  - `get_event_reactions` depends on `_parse_sections` and `_read_config` (both internal, stable)
  - `write_event_reactions` depends on `CONFIG_PATH` global and `_parse_sections`
  - No external package dependencies added

## Side Effects

- **Risk 1: `get_event_filters_for_role` returns `None` for empty reacts_to list** — Severity: M — If a role is explicitly configured with `- **reacts-to**: ` (empty), the function returns `None` (same as "section absent"), causing the caller to fall back to hardcoded defaults rather than respecting the explicit "react to nothing" intent. The docstring says "Returns a set of event type strings, or None if the section is absent" but the code implements "None if section absent, role missing, OR reacts_to is empty." **Mitigation**: Either separate the return signals (return empty set vs None), or document the conflation and accept that empty-list means "use defaults." The latter is probably fine — an empty reacts_to is an edge case that likely means "not configured yet" = "use defaults."

- **Risk 2: `re.sub` without count replaces ALL `## Event Reactions` sections** — Severity: L — If a malformed config.md has two `## Event Reactions` sections, `re.sub` (line 303) replaces both with the new content (unlike `set_field` which uses `text.replace(section_text, new_section, 1)` at line 181). A well-formed file has exactly one, so this is theoretical. **Mitigation**: Add `count=1` to `re.sub`.

- **Risk 3: Atomic write inconsistency with `set_field`** — Severity: L — `write_event_reactions` uses tmp+replace (atomic), but `set_field` writes directly to `CONFIG_PATH` (line 189, non-atomic). If the two write paths are ever called concurrently (different processes), `set_field` could corrupt a partial `write_event_reactions` replacement. In practice, compose.py is single-process, so no real race. **Mitigation**: Not a blocker, but worth harmonizing — either make `set_field` atomic too, or accept the inconsistency.

- **Risk 4: `CONFIG_PATH.with_suffix(".tmp")` naming** — Severity: L — On Windows, `Path.with_suffix(".tmp")` replaces the entire suffix, producing `config.tmp` (not `config.md.tmp`). This is harmless — the temp file is short-lived and immediately renamed — but unexpected. If a file watcher or backup tool picks up `config.tmp`, it could cause confusion. **Mitigation**: Use `CONFIG_PATH.with_name(CONFIG_PATH.name + ".tmp")` for `config.md.tmp`.

## Edge Cases

- **Missing `## Event Reactions` section**: `get_event_reactions()` returns `{}` — correct. `get_event_filters_for_role()` returns `None` — correct (caller falls back to hardcoded defaults per TC-13). `write_event_reactions()` appends the section to end of file — correct.

- **Empty section (`## Event Reactions` with no content)**: `get_event_reactions()` — `section_text.strip()` is `""`, returns `{}`. `get_event_filters_for_role()` — returns `None`. Graceful.

- **Malformed lines between role headings**: Lines that don't match `### role`, `- **emits**:`, or `- **reacts-to**:` are silently skipped (lines 237, 246, 249). No error, no warning — data loss is silent. For example, `- **emits**:` (missing colon) or `- **Emitz**: ...` (typo) would be lost. This matches the "never raises" contract but means config typos go undetected.

- **Role name with non-word characters**: The regex `^###\s+(\w+)` (line 230) only matches `[a-zA-Z0-9_]`. Standard roles (`pm`, `skill`, `qa`, `dm`, `be`, `fe`) all work. Hyphenated roles like `my-role` would not parse — but the system only uses single-word role IDs.

- **Comma in event type name**: The comma-split on lines 243–244 and 252–253 means event type names cannot contain commas. Current event types (`pr-merge`, `cycle-start`, etc.) don't use commas, so this is fine.

- **`write_event_reactions` with empty emits/reacts_to**: `", ".join([])` produces `""`, resulting in `- **emits**: ` — valid markdown, parsed back as empty list by `get_event_reactions`. Round-trip is lossy but not broken.

- **`write_event_reactions` with event type containing commas**: Would be serialized as-is (`cycle-start, my,event`) but parsed back incorrectly (split at commas). Mitigated by the event catalog — known event types don't contain commas.

- **Section is last in file**: The regex lookahead `(?=\n## |\Z)` correctly handles end-of-file. Both the replace and append paths work.

- **No trailing newline on section content**: `re.DOTALL` allows `.*?` to span lines without newlines. The replacement produces a clean section with proper newlines regardless.

## Integration Risks

- **`cycle_pre.py` integration not yet done**: The `_filter_events_for_role()` function (line 386) still uses hardcoded `_ROLE_EVENT_TYPES`. It calls `_config_get()` via subprocess — NOT the new `get_event_filters_for_role()`. Integration needs one of: (a) add `get_event_filters_for_role` call alongside the fallback, or (b) change `_config_get` to use the new function. Per TC-13, the hardcoded fallback must be preserved exactly as-is.

- **`compose.py` derivation not yet done**: `write_event_reactions` exists but nothing calls it. The compose pipeline must call it after LLM derivation of event contracts. Per the phase 2 prep doc (Q1 recommendation), derivation runs once during setup, then validate-only on subsequent composes.

- **No CLI access to new functions**: The `main()` function (line 545) has no `event-reactions` command. Access is programmatic-only. This is acceptable — `cycle_pre.py` and `compose.py` import `config` directly. But TC-22's expected `config.py get pm-emits` won't work without FIELD_MAP entries or a new CLI subcommand.

- **Test plan disconnect**: TC-3, TC-22 expect `config.py get pm-emits` and `config.py get pm-reacts-to` to work as FIELD_MAP entries. The current section-based design doesn't add those entries. This is a design choice (section-based vs field-based) that needs resolution — either add FIELD_MAP entries that delegate to `get_event_reactions()` under the hood, or update the test plan to use the programmatic API.

- **No `event-reactions.md` sub-skill created**: TC-16, TC-17 require a `references/sub-skills/common/event-reactions.md` sub-skill. It doesn't exist yet. None of the `includes.yml` files reference it.

## Upgrade & Migration

- **New config values**: `## Event Reactions` section with `### role` subsections containing `- **emits**: ...` and `- **reacts-to**: ...` per role. No defaults needed — absence triggers graceful fallback to hardcoded `_ROLE_EVENT_TYPES`.

- **New files**: 
  - `references/sub-skills/common/event-reactions.md` — NOT YET CREATED (required by TC-16, TC-17)

- **Template changes**: 
  - All four `references/roles/*/includes.yml` — need `common/event-reactions` entry added — NOT YET DONE
  - `references/sub-skills/common/cycle-runner.md` — may need minor reference update per research — NOT YET DONE

- **Upgrade steps**: N/A — no upgrade impact because:
  1. Functions are not called by anything yet (no behavioral change)
  2. When section is absent, `cycle_pre.py` falls back to hardcoded defaults (zero behavior change per TC-18)
  3. First compose with `agent-compose: yes` populates the section automatically

- **Graceful degradation**: N/A — the three functions already handle absence gracefully. `get_event_reactions()` returns `{}`. `get_event_filters_for_role()` returns `None`. `write_event_reactions()` appends if section absent. No user action needed.

## Open Questions

- **Q1**: Should `get_event_filters_for_role` distinguish between "section absent" (return `None` → use defaults) and "role has empty reacts_to" (return empty `set()` → react to nothing)? — **Why**: If a human explicitly clears a role's reactions in config.md, they probably expect "react to nothing," not "fall back to defaults silently." Conflating the two cases makes the empty-set intention impossible to express.

- **Q2**: Should the `## Event Reactions` section be accessible via `config.py get` CLI (adding FIELD_MAP entries or a new subcommand), or only via the programmatic import API? — **Why**: TC-22 and TC-3 describe CLI-based access. The current programmatic-only design works for `cycle_pre.py` and `compose.py` (they import config), but human inspection/debugging of event contracts via CLI would be useful.

- **Q3**: Should `write_event_reactions` use `count=1` for `re.sub` to match the `set_field` behavior? — **Why**: Consistency and safety — a malformed file with duplicate sections shouldn't cause silent multi-replacement. Low risk, trivial fix.

## Recommendation

**Feasible with caveats.** The three functions are correctly implemented at their core level — regex parsing handles expected inputs, edge cases degrade gracefully, and the atomic write pattern is sound. The issues found are concrete and fixable:

1. **Must fix**: Add `count=1` to `re.sub` in `write_event_reactions` (line 303)
2. **Should fix**: Resolve the `get_event_filters_for_role` conflation of "absent" vs "empty reacts_to" (lines 266–273) — either document it explicitly or add a separate signal
3. **Should address**: Decide whether to add FIELD_MAP entries or CLI access for event reactions (reconcile with test plan TC-3, TC-22)
4. **Missing integration**: The functions are ready but nothing calls them — `cycle_pre.py` and `compose.py` integration is the next step
5. **Missing artifacts**: `event-reactions.md` sub-skill and `includes.yml` updates haven't been created yet
6. **Missing tests**: No test coverage exists for any of the three new functions

## Vault Candidates

- **Type**: pattern — "Atomic config section write via tmp+replace" — **Why**: `write_event_reactions` introduces the first atomic write path in `config.py` (tmp file + `Path.replace`). `set_field` writes directly. This inconsistency is worth noting as the module evolves toward more concurrent access patterns.

- **Type**: pattern — "Section-based vs flat-field config storage tradeoff" — **Why**: The Event Reactions data uses a hierarchical `## Section → ### Role → - **field**` format instead of the flat `- **role-field**: value` format used everywhere else in config.md. This is the first nested configuration section in the codebase and sets a precedent for future structured data in config.md.

- **Type**: decision — "Event contract validation is config-driven, not prose-driven" — **Why**: Per RESEARCH.md, the `Event Reactions` section is consumed mechanically by `cycle_pre.py` (Python script), not parsed by LLM agents from CLAUDE.md prose. This implements the deterministic-scripts-over-prose pattern at the config level, establishing that structured agent behavior declarations live in config.md, not in sub-skills.

- **Type**: learning — "Graceful degradation requires distinguishing 'absent' from 'empty'" — **Why**: `get_event_filters_for_role` returns `None` for both "section missing" and "empty reacts_to list." This conflates two semantically different states. Future fallback-returning functions should use a three-way signal: absent (None), present-but-empty (empty collection), or present-with-data (filled collection).
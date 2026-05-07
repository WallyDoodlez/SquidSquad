Now I have all the information needed. Let me compile the research document.

---

# FEAT-SKILL-5868-AC5-REVIEW Research — `_filter_events_for_role` config-driven refactoring review

## Summary

AC-5 of #5868 modified `_filter_events_for_role` in `cycle_pre.py` (line 386) to try config-driven event filters from `config.md`'s `## Event Reactions` section before falling back to the hardcoded `_ROLE_EVENT_TYPES` dict. The change is minimal — only ~14 lines added (lines 393-400). The implementation: imports `get_event_filters_for_role` from `config.py` inside a try/except block within the function body; if the function succeeds and returns a non-None set, those filter types are used; otherwise the hardcoded dict at lines 377-383 is the fallback.

**The implementation is correct and complete for the stated requirements.** The fallback chain (import error → exception → section absent → role absent → empty list → all fall back to hardcoded) is sound. The import pattern matches three existing patterns in the same file. Self-event filtering is preserved in `_run_mechanical_reactions` (line 424), cursor dedup is preserved in `main()` (line 1047), and cascade safeguards are untouched. No race conditions exist — reads are atomic and agents run in separate processes.

**One edge-case ambiguity found**: When the `## Event Reactions` section is present and a role has an explicitly empty `reacts-to` list, the code treats it identically to "section absent" (returns `None` → falls back to hardcoded). This may or may not be intentional — it means users cannot configure a role to receive *no* events via config.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill — compose-time config" listed as active high priority. Directly relevant.
- **Related decisions**: [[decision-cycle-runner-architecture]] — cycle_pre.py is the mechanical shell; filters must be deterministic. [[decision-self-healing-sentinel]] — reactions must support two-tier response; this change doesn't touch reactions.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — the filter resolution is a deterministic script, not LLM-driven. Correctly applied.
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files" — the config read is a direct `Path.read_text()` parse, which is mechanical and direct. "Context pressure threshold: 70%" — the compact config format (comma-separated event types) keeps config.md lean.
- **Related learnings**: [[learning-atomic-migration-strategy]] — the change is atomic (single function modified, config.py already has the reader). The FEAT-PM-5868-CONTEXT.md also references this — "Absent Event Reactions section = hardcoded fallback = zero behavior change."

## Impact Analysis

- **Files touched**:
  - `references/scripts/cycle_pre.py` — lines 386-406 (`_filter_events_for_role` function) — **already modified**
  - `references/scripts/config.py` — lines 260-273 (`get_event_filters_for_role`) — **already exists, called by the new code**
  - `.squidsquad/config.md` — **no change needed** (section absent = fallback, which is the current state)

- **Behavior changes**:
  1. When `## Event Reactions` section is **absent** from config.md (current state): **zero behavior change** — falls back to `_ROLE_EVENT_TYPES` exactly as before
  2. When section is **present** with a role's `reacts-to` list: config-driven filtering replaces hardcoded filtering for that role
  3. When section is **present** but role is **missing**: falls back to hardcoded
  4. When config import **fails**: falls back to hardcoded

- **Dependencies**:
  - `config.py` must define `get_event_filters_for_role` — **confirmed present at line 260**
  - `config.py` must define `get_event_reactions` — **confirmed present at line 212**
  - Both functions are in the same file (`references/scripts/config.py`), which is already importable from `cycle_pre.py` (same directory, `sys.path` includes `SCRIPT_DIR` at line 37)

## Side Effects

- **Risk 1: Empty reacts_to indistinguishable from section-absent** — Severity: **M** — Mitigation: If the design intent is that empty `reacts_to` should mean "no events" rather than "use defaults," change line 272-273 in `config.py` from `return set(reacts_to) if reacts_to else None` to `return set(reacts_to)`. The current behavior returns `None` for empty lists, which triggers hardcoded fallback. If "no events" is the desired behavior, `_filter_events_for_role` should distinguish between `None` (section absent) and an empty set (intentional no-filter). AC spec says "zero behavior change when section absent" — this is satisfied. The ambiguity is only for "section present, role present, reacts_to empty."

- **Risk 2: Broad exception catching masks bugs in get_event_filters_for_role** — Severity: **L** — Mitigation: The `except (ImportError, Exception): pass` pattern is consistent with the rest of cycle_pre.py (used at lines 40, 1051, 1089). A bug inside `get_event_filters_for_role` (e.g., AttributeError from a typo) would be silently swallowed, and the hardcoded fallback used. This is the existing pattern and intentional for resilience, but adds debugging friction.

- **Risk 3: Config read on every cycle call** — Severity: **L** — Mitigation: `_filter_events_for_role` calls `config.get_event_filters_for_role()` which calls `get_event_reactions()` which calls `_read_config()` which does `Path.read_text()`. This is called once per agent cycle (line 1050). Acceptable. No caching needed.

## Edge Cases

- **Config.md being written concurrently by another agent's compose/deploy**: `config.py`'s `write_event_reactions` (line 276) uses atomic write (tmp + replace). `_read_config` uses `Path.read_text()` — readers see either the old or new complete file, never a partial write. Cross-process safe.

- **Role name not in _ROLE_EVENT_TYPES and not in config**: `_ROLE_EVENT_TYPES.get(role)` returns `None` → the `if not allowed: return events` path on line 404-405 returns all events unfiltered. This is unchanged from the original behavior. A new role type (e.g., "designer") would see all events. If config has it and defines `reacts_to`, it gets filtered. Consistent.

- **Corrupt/malformed Event Reactions section**: `get_event_reactions` (config.py line 212-257) uses regex parsing that silently ignores unrecognized lines. If the section is garbled, `get_event_filters_for_role` returns `None` → falls back to hardcoded. Graceful.

- **Cursor dedup across config changes**: The cursor (`last_processed_event_id` from working-state.md line 1047) is role-scoped and stored per-agent. If an agent's event filter changes between cycles (config updated), the cursor still advances correctly — the agent may see new event types it previously filtered out, but no events are double-processed. Events from before the last cursor are always excluded by the `since` parameter (line 1047).

## Integration Risks

- **`event_bus_reader.query()` has its own `event_type` filter parameter** (line 64 of event_bus_reader.py): This is a server-side filter that could potentially be used instead of client-side filtering. Currently, `cycle_pre.py` does NOT pass `event_type` to the query — it always requests all events and filters client-side in `_filter_events_for_role`. If the config-driven filter grows large, server-side filtering could reduce wire overhead. No action needed now, but this is a future optimization path.

- **`_run_mechanical_reactions` still hardcoded**: AC-5 only touched `_filter_events_for_role`. `_run_mechanical_reactions` (line 409) remains hardcoded with its own self-event guard (line 424). The FEAT-PM-5868-CONTEXT.md says "Mechanical reactions that trigger tracker transitions (which emit new events) must not create infinite loops — preserve existing cascade safeguards." This safeguard is in `_run_mechanical_reactions`, which is untouched by AC-5. The cascade is safe.

- **Duplicate function in cycle_pre.py**: `_validate_config_version` is defined twice identically at lines 181-217 and 220-256. The second definition shadows the first. This is a pre-existing code quality issue in the file, unrelated to AC-5 but discovered during review. Worth a cleanup PR.

## Upgrade & Migration

- **New config values**: The `## Event Reactions` section with per-role `emits` and `reacts-to` fields. Currently **absent** from `.squidsquad/config.md` (confirmed via grep). When absent, behavior is identical to pre-AC-5.
- **New files**: None — the function already exists in `config.py`.
- **Template changes**: None.
- **Upgrade steps**: N/A — no upgrade impact. Existing installs work without any action (section absent = hardcoded fallback). Compose populates the section on next deploy.
- **Graceful degradation**: When harness is unreachable: `event_bus_reader.query()` returns `[]` → `_filter_events_for_role` receives empty list → returns empty list → no events to filter. When config section is absent: falls back to hardcoded `_ROLE_EVENT_TYPES`. When config.py import fails: falls back to hardcoded. All three degrade correctly.

## Open Questions

- **Q1**: Should an empty `reacts_to` list in config mean "this role receives NO events" or "use hardcoded defaults"? — **Why**: Currently, empty list triggers hardcoded fallback (returns `None`). If a user explicitly writes `- **reacts-to**: ` (empty), they likely intend "no events." But the current implementation treats this identically to "section absent." The AC doesn't specify this case — it only requires zero behavior change when section is absent.
- **Q2**: Should `_filter_events_for_role` also filter self-emitted events (like `_run_mechanical_reactions` does at line 424)? — **Why**: Currently, an agent's own past-cycle events pass through `_filter_events_for_role` and appear in `recent_events`. This isn't a loop risk (different cycle), but wastes token budget as noted in REVIEW-5622-DEEPSEEK.md line 43. Not required for AC-5 but a possible future optimization.

## Recommendation

**Feasible — implementation is correct.** The change is minimal, follows existing patterns, preserves all safeguards, and degrades gracefully. The one edge-case ambiguity (empty reacts_to vs. section absent) should be clarified with the PM or accepted as intentional. No blocking issues found.

## Vault Candidates

- **Type**: learning — `_ROLE_EVENT_TYPES` + config-driven filters = dual-source-of-truth risk — **Why**: Both the hardcoded dict (line 377) and the config section define which events agents see. When config is populated, the hardcoded dict becomes dead code but is preserved as fallback. Future event type additions must update both, or the config population must always match. This was also flagged in AC1-REVIEW.md.
- **Type**: pattern — try/except-with-local-import for optional config dependencies — **Why**: `cycle_pre.py` uses this pattern 4 times (state_bus, event_bus_reader, event_bus, config.get_event_filters_for_role). It's a consistent resilience pattern: import inside try/except, broad exception catch, silent fallback. Worth documenting as a SquidSquad convention for mechanical scripts that must never crash on missing modules.
- **Type**: learning — duplicate `_validate_config_version` at lines 181 and 220 — **Why**: Discovered during review. Both definitions are identical. The second shadows the first. Indicates a merge artifact or copy-paste error. Clean up by removing the first definition (lines 181-217).
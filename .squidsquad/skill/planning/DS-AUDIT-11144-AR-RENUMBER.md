I systematically verified every §N reference in the diff against the canonical renumbering map (old §3→§4, §4→§5, … §10→§11; §1 and §2 unchanged). Below are the factual errors found.

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: ~370 (in diff: §5.3 Vocabulary note paragraph)
- **Severity**: error
- **Issue**: Cross-doc reference to HARNESS-ARCH §9 was incorrectly shifted to §10; the URL anchor `#9-vocabulary-notes` still points to the real §9, creating a display/anchor mismatch.
- **Evidence**: HARNESS-ARCH.md was NOT renumbered in this task — only its references *to AGENT-RUNTIME* were updated. The Python placeholder-marker pass treated `HARNESS-ARCH.md §9` as if it were an AGENT-RUNTIME self-reference and added 1. The anchor `#9-vocabulary-notes` was left untouched, confirming this was an unintended shift. A reader clicking the link lands in correct §9 but the displayed number says §10.
- **Suggested fix**: Revert to `[HARNESS-ARCH.md §9](HARNESS-ARCH.md#9-vocabulary-notes)`.

### Finding 2

- **File**: docs/AGENT-RUNTIME.md
- **Line**: ~591 (in diff: §7.1 Ralph Loop cycle lead) and ~640–647 (in diff: §7.6 Vault touchpoints table and trailing paragraphs)
- **Severity**: error
- **Issue**: Five cross-doc references to VAULT-ARCH sections were incorrectly incremented by 1, but VAULT-ARCH.md was not renumbered.
- **Evidence**:
  - `VAULT-ARCH §7` → `§8` (execution-lane detail) — should stay §7
  - `VAULT-ARCH §7.2` → `§8.2` (vault-remember row) — should stay §7.2; anchor `#72-vault-remember` unchanged
  - `VAULT-ARCH §5` → `§6` (BRIEFING.md) — should stay §5; anchor `#5-briefingmd` unchanged
  - `VAULT-ARCH §7` → `§8` (model pin line) — should stay §7
  - `VAULT-ARCH §7` → `§8`, `§9` → `§10` ("For the full vault architecture") — should stay §7, §9
- **Suggested fix**: Revert all five to their original VAULT-ARCH section numbers: `§7`, `§7.2`, `§5`, `§7`, `§7`/`§9`.

### Finding 3

- **File**: docs/AGENT-RUNTIME.md
- **Line**: ~649 (Subagent invocation rules lead), ~736 and ~738 (§8 lead), ~1174 (§9.5 PM inbox enumeration)
- **Severity**: error
- **Issue**: Four cross-doc references to COMPOSE-ARCHITECTURE sections were incorrectly incremented by 1.
- **Evidence**: COMPOSE-ARCHITECTURE.md was not renumbered. The diff shows:
  - `COMPOSE-ARCHITECTURE.md §3.2` → `§4.2` (should stay §3.2)
  - `COMPOSE-ARCHITECTURE.md §5.1.1` → `§6.1.1` (should stay §5.1.1)
  - `COMPOSE §5.1.1` → `§6.1.1` (should stay §5.1.1)
  - `COMPOSE-ARCHITECTURE §8.2` → `§9.2` (should stay §8.2)
- **Suggested fix**: Revert all four to their original COMPOSE-ARCHITECTURE section numbers.

### Finding 4

- **File**: docs/AGENT-RUNTIME.md
- **Line**: ~772–773 (in diff: §8.0 event_poll port discovery + spawn ordering paragraphs)
- **Severity**: error
- **Issue**: Two cross-doc references to HARNESS-ARCH §7.2 were incorrectly shifted to §8.2.
- **Evidence**: `HARNESS-ARCH §7.2` → `§8.2` and `HARNESS-ARCH.md §7.2` → `§8.2`. HARNESS-ARCH was not renumbered.
- **Suggested fix**: Revert both to `HARNESS-ARCH §7.2` / `[HARNESS-ARCH.md §7.2](HARNESS-ARCH.md)`.

### Finding 5

- **File**: docs/HARNESS-ARCH.md
- **Line**: ~198 (in diff: EAD cadence contractual-hard-floor bullet)
- **Severity**: error
- **Issue**: Reference `AGENT-RUNTIME §9 Q3` was not updated to `§10 Q3`. AGENT-RUNTIME's old §9 (Open questions) shifted to new §10.
- **Evidence**: The same line correctly updated `AGENT-RUNTIME §4.4` → `§5.4` but left `§9 Q3` unchanged. The Q3 row still lives in what is now §10 of AGENT-RUNTIME.
- **Suggested fix**: Change `§9 Q3` to `§10 Q3`.

### Finding 6

- **File**: docs/HARNESS-ARCH.md
- **Line**: ~303 (in diff: §7.4 event_poll lifetime across claude respawn)
- **Severity**: error
- **Issue**: Multi-ref line: `AGENT-RUNTIME §8.0 / §7.2` — only the first reference (`§7.0`→`§8.0`) was updated; `§7.2` should be `§8.2`.
- **Evidence**: Old §7.2 (event-mode Boot sequence) shifted to new §8.2. The current text `§7.2` now points to the loop-mode "What wakes the agent in loop mode" section — wrong content.
- **Suggested fix**: Change `§7.2` to `§8.2`.

### Finding 7

- **File**: docs/HARNESS-ARCH.md
- **Line**: ~356 and ~410 (in diff: port-discovery probe-fail rule and Failure table)
- **Severity**: error
- **Issue**: Two multi-ref lines: `AGENT-RUNTIME §7 + §8.4` — `§8.4` should be `§9.4`. Old §8.4 (When the harness is unreachable) shifted to new §9.4.
- **Evidence**: Both instances correctly updated `§6`→`§7` but left `§8.4` unchanged.
- **Suggested fix**: Change both `§8.4` to `§9.4`.

### Finding 8

- **File**: docs/HARNESS-ARCH.md
- **Line**: ~568 (in diff: Revision log v1 entry)
- **Severity**: error
- **Issue**: Multi-ref line with 4 AGENT-RUNTIME references: only the first (`§4.3`→`§5.3`) was updated. Remaining three (`§4.4`, `§4.7`, `§6.4`) are stale.
- **Evidence**: `AGENT-RUNTIME.md §5.3, §4.4, §4.7, §6.4` should read `AGENT-RUNTIME.md §5.3, §5.4, §5.7, §7.4`.
- **Suggested fix**: Update `§4.4`→`§5.4`, `§4.7`→`§5.7`, `§6.4`→`§7.4`.

### Finding 9

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Line**: ~1207 (in diff: §6.5 Wake-mode handling)
- **Severity**: error
- **Issue**: Multi-ref line: `AGENT-RUNTIME §8.0 / §7.1` — only first ref updated; `§7.1` should be `§8.1`.
- **Evidence**: Old §7.1 (The nudge contract) shifted to new §8.1. The text still says `§7.1` which now points to the loop-mode cycle description.
- **Suggested fix**: Change `§7.1` to `§8.1`.

### Finding 10

- **File**: docs/VAULT-ARCH.md
- **Line**: ~621 (in diff: §11.4 Future gap)
- **Severity**: error
- **Issue**: Multi-ref line: `§4 documents the event bus and §4.2 the signal catalog` — only first ref updated; `§4.2` should be `§5.2`.
- **Evidence**: The line now reads `§5 documents the event bus and §4.2 the signal catalog` — mismatch.
- **Suggested fix**: Change `§4.2` to `§5.2`.

### Finding 11

- **File**: docs/INSTALLER-ARCH.md
- **Line**: ~519 (in diff: §10.3 in-flight-work handling)
- **Severity**: error
- **Issue**: Multi-ref line: `AGENT-RUNTIME §6 + §6.5` — `§6.5` should be `§7.5`. Old §6.5 (Context-pressure exit-42) shifted to new §7.5.
- **Evidence**: `§6` correct (old §5→new §6 State persistence), but `§6.5` not updated.
- **Suggested fix**: Change `§6.5` to `§7.5`.

### Finding 12

- **File**: docs/AGENT-RUNTIME.md
- **Line**: Multiple revision-log entries in the §11.4 Revision log
- **Severity**: warning
- **Issue**: Revision log entries contain incorrectly shifted cross-doc references to COMPOSE-ARCHITECTURE, INSTALLER-ARCH, and HARNESS-ARCH sections that were not renumbered: `COMPOSE §4.6`→`§5.6`, `COMPOSE §3.0`→`§4.0`, `INSTALLER §4.8`→`§5.8`, `INSTALLER §10`→`§11`, `HARNESS-ARCH §7.2`→`§8.2`, `HARNESS-ARCH §8.2`→`§9.2`.
- **Evidence**: These entries describe what changed in prior revisions. When the entries reference other docs' sections (COMPOSE-ARCHITECTURE §N, INSTALLER-ARCH §N, HARNESS-ARCH §N), those numbers should not have been incremented because those docs were not renumbered. A reader tracing a historical change will land at the wrong section.
- **Suggested fix**: Revert cross-doc section numbers in revision-log entries to their original values (the pre-shift values that were correct at the time of each revision).

---

## Summary

The Python placeholder-marker pass had two systematic defects:

1. **Indiscriminate shift**: All `§N` tokens in the moved range (old 3–10) were incremented by 1, including references to *other documents'* sections. VAULT-ARCH, HARNESS-ARCH, COMPOSE-ARCHITECTURE, and INSTALLER-ARCH were not renumbered, so references to their sections should not have changed.

2. **First-match-only on multi-ref lines**: When a line contained multiple `§N` references (e.g., `AGENT-RUNTIME §4.4 + §9 Q3` or `§7.0 / §7.1`), only the first `§N` pattern was updated; subsequent ones were left at stale values.

Internal AGENT-RUNTIME self-references are correct. The new §3 intro reads coherently. §2's "Two triggering modes" heading still makes sense after the §2.3 removal (inline mode was explicitly "not a third triggering mode"). No orphan `§2.3` references survive. Sub-skill files (`cursor-management.md`, `event-mode-contract.md`) have correct post-renumber references.
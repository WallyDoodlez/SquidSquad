Now I have enough data to produce the findings. Let me compile them.

---

### Finding 1

- **File**: D:/Dev/Dev/SquidSquad/.claude/worktrees/agent-ad73be7af778567db/docs/VAULT-ARCH.md
- **Line**: 310, 341, 435
- **Severity**: warning
- **Issue**: Three cross-references use "§7.3-equivalent" or "§7-equivalent" — vestigial suffixes from a prior section numbering that no longer apply. In the current v2 document, §7.3 IS `vault-optimize — maintenance`. The "-equivalent" suffix implies a mapping that doesn't exist; readers may wonder whether §7.3 is not the real section and look elsewhere.
- **Evidence**:
  - Line 310: `set by vault-optimize (§7.3-equivalent)`
  - Line 341: `vault_optimize.py's pruning decisions (§7.3-equivalent)`
  - Line 435: `vault_optimize.py's pruning/archival proposals (§7-equivalent)`
  - The actual §7.3 heading (line 472) is `### 7.3 vault-optimize — maintenance`.
- **Suggested fix**: Replace "§7.3-equivalent" with "§7.3" at lines 310 and 341, and "§7-equivalent" with "§7.3" at line 435.

---

### Finding 2

- **File**: D:/Dev/Dev/SquidSquad/.claude/worktrees/agent-ad73be7af778567db/docs/VAULT-ARCH.md
- **Line**: 421
- **Severity**: error
- **Issue**: Cross-reference `(§9.6 open decision #5)` points to a section that does not contain open decisions. §9.6 is "Quiet cycles — maintenance" — it describes the harness-scheduled maintenance window, community detection, and contradiction handling but has no numbered open decisions. The document's open decisions live in the §11 table. The reference is likely meant for the planning doc (`planning doc §9.6 #5`), but as written it reads as an internal reference to a non-existent location. A reader following the reference will find nothing.
- **Evidence**:
  - Line 421: `6. **Durability** (§9.6 open decision #5) largely **dissolves**…`
  - §9.6 (lines 568-572) contains no open-decision list or numbered items.
  - The preamble (line 5) establishes the planning doc citation convention: `the planning doc §9`, `the planning doc §10`, etc. This reference drops the "planning doc" prefix entirely.
- **Suggested fix**: Either change to `(planning doc §9.6 #5)` if the planning doc has a durability open decision at that location, or re-point to the relevant §11 row (though §11 does not currently list a durability item — it was "largely dissolved").

---

### Finding 3

- **File**: D:/Dev/Dev/SquidSquad/.claude/worktrees/agent-ad73be7af778567db/docs/VAULT-ARCH.md
- **Line**: 488, 671, 672
- **Severity**: warning
- **Issue**: Three citations use the bare shorthand "planning" instead of the established "planning doc" shorthand defined in the preamble. This breaks the citation trail convention and could cause a reader to wonder whether "planning" refers to a different document.
- **Evidence**:
  - Line 488: `the Python-port fallback (planning §9.4.2) remains the contingency`
  - Line 671: `(planning §9.6 #3; recommendation: aggressive …)`
  - Line 672: `(planning §9.6 #4)`
  - Preamble line 5: `the “planning doc” hereafter`
  - All other citations use `planning doc` (lines 167, 243, 318, 333, 353, 361, 371, 379, 409, 411, 420, 423, 485, 539, 630, 668, 705).
- **Suggested fix**: Change `planning` to `planning doc` at lines 488, 671, and 672.

---

### Finding 4

- **File**: D:/Dev/Dev/SquidSquad/.claude/worktrees/agent-ad73be7af778567db/docs/VAULT-ARCH.md
- **Line**: 18, 45, 69 (used); 162 (defined)
- **Severity**: warning
- **Issue**: The acronym "PARAG" is used three times before its expansion is given. The first occurrence is in §1 line 18 ("v1's hardcoded PARAG taxonomy"), then in the §2 terminology table (line 45: "markdown notes organized via PARAG"), and in §2.1 heading (line 69: "PARAG structure"). The acronym is first expanded at line 162 in §3.0: "PARAG (Projects / Areas / Resources / Archives / Galaxy — the five-folder taxonomy…)". A reader encountering the term in §1 or §2 has no definition until §3.
- **Evidence**: Lines 18, 45, 69 use "PARAG" without expansion; line 162 provides the expansion.
- **Suggested fix**: Expand "PARAG" on first use at line 18, e.g.: "v1's hardcoded PARAG (Projects/Areas/Resources/Archives/Galaxy) taxonomy." The §3.0 expansion can remain as the canonical definition with the full explanation.

---

### Finding 5

- **File**: D:/Dev/Dev/SquidSquad/.claude/worktrees/agent-ad73be7af778567db/docs/VAULT-ARCH.md
- **Line**: 309 vs 393
- **Severity**: warning
- **Issue**: Internal role-name inconsistency within the v2 specification. The frontmatter spec at §4.3 (line 309) uses the post-#6274 role names: `owner: pm | worker | verifier | dm | shared`. But the event model at §6.1 (line 393) uses a pre-#6274 name in its example: `agent is the acting agent's alias (e.g. pm, skill)`. The alias `skill` is the old name for `worker`. While §4.3 (line 320) acknowledges this drift will be swept during migration, the v2 specification document itself should be internally consistent — it should not use both naming schemes in normative sections.
- **Evidence**:
  - Line 309: `owner: pm | worker | verifier | dm | shared` (post-#6274: `worker`)
  - Line 393: `e.g. pm, skill` (pre-#6274: `skill`)
  - Line 320 acknowledges the drift exists.
- **Suggested fix**: Change `skill` to `worker` at line 393 to match the post-#6274 naming used throughout the rest of the v2 specification.

---

### Finding 6

- **File**: D:/Dev/Dev/SquidSquad/.claude/worktrees/agent-ad73be7af778567db/docs/VAULT-ARCH.md
- **Line**: 177, 183, 204
- **Severity**: warning
- **Issue**: The JSON code blocks in §3.1 and §3.2 contain range-notations (`0.0-1.0`) where JSON number literals are expected. While these blocks are clearly illustrative schema sketches, the `dedupThreshold` and `weight` fields show `0.0-1.0` which is not valid JSON syntax. The `tieBreakWeights` object in the same blocks uses valid numeric literals (e.g. `2.0`, `0.25`), so the range notation stands out as inconsistent. The concrete profile in §3.2 (lines 207-213) uses valid numbers for `weight` (0.8, 1.0, 0.6) — only `dedupThreshold` remains as the range literal `0.0-1.0` in an otherwise valid JSON block.
- **Evidence**:
  - Line 177: `"dedupThreshold": 0.0-1.0,` (in illustrative schema)
  - Line 183: `"weight": 0.0-1.0,` (in illustrative schema)
  - Line 204: `"dedupThreshold": 0.0-1.0,` (in concrete default profile — all other values are valid JSON)
  - Line 205: `"used": 2.0, "impression": 0.25, …` (valid JSON numbers in same block)
- **Suggested fix**: For the illustrative schema (§3.1), change to a placeholder like `"<number 0.0–1.0>"` or a comment. For the concrete profile (§3.2), supply an actual default value (e.g. `0.8`) since §7.2 says the default is "tuned at implementation" — the profile should record what the shipped default is.

---

### Finding 7

- **File**: D:/Dev/Dev/SquidSquad/.claude/worktrees/agent-ad73be7af778567db/docs/VAULT-ARCH.md
- **Line**: 467 (cf. §11 at lines 666-674)
- **Severity**: warning
- **Issue**: §7.2 states that `dedupThreshold` has its "default tuned at implementation," but this open decision is not tracked in §11's open-decisions table. By contrast, §11 #6 explicitly tracks the compaction horizon + staleness threshold defaults as "Implementation config only / Dev at implementation." The `dedupThreshold` default is in the same category (a configurable numeric default that needs a value before ship) but has no §11 entry, creating an inconsistency in what the document considers outstanding.
- **Evidence**:
  - Line 467: `with the cutoff configured as vault-schema.json dedupThreshold (default tuned at implementation)`
  - §11 table (lines 666-674): 7 items, none of which mention `dedupThreshold`.
  - §11 #6 covers compaction horizon + staleness threshold but not dedup threshold.
- **Suggested fix**: Either add a row to §11 for the `dedupThreshold` default, or specify a concrete default in §7.2/§3.2 and remove the "tuned at implementation" deferral.

---

### Category status for each review criterion:

**Criterion 1** (external-system naming → "reference system"; zero "dmp"): NO FINDINGS. All external-system naming is consistently "reference system"; zero occurrences of "dmp" (case-insensitive) anywhere in the file.

**Criterion 2** (§6.5 compaction invariants vs §6.3/§9.6/§9.8): NO FINDINGS. The three invariants (owner-only compaction, aggregate-before-truncate one-commit, idempotent re-compaction) are consistent with §6.3's single-writer-per-shard design, §9.6's maintenance-window scheduling, and §9.8's main-only commit rule. The invariants explicitly acknowledge the dedup-by-id limitation (§6.5 line 445) and justify why idempotency must be structural.

**Criterion 3** (§2.1 at-a-glance vs cited deep sections): NO FINDINGS regarding contradictions. All claims in the PARAG flow diagram, sequence diagram, worked example, and retirement diagram match their cited deep sections (§3.1–3.5, §4.4, §6.1–6.5, §9.2–9.6). Mermaid syntax is valid for all three diagrams (flowchart LR, sequenceDiagram, flowchart TD). The worked example is a simplified illustration that does not contradict the canonical §9.2–§9.4 text.

**Criterion 4** (§4.4/§6.4 "screens against three retirement buckets, none = healthy"): NO FINDINGS. Every reference to staleness buckets is consistent: §4.4 (line 335), §6.4 (line 429), §2.1 prose (line 134), §2.1 retirement diagram (lines 142-149), §7.3 (line 475), and §9.6 (line 570) all use the same three-bucket model with the explicit "note in none of them is healthy and untouched" clause. No instance of the old "classifies every note" wording survives.
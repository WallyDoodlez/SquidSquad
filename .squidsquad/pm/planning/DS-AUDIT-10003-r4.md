Now I have all the data. Here is my systematic report.

---

## Criterion-by-Criterion Report

### Criterion 1 — Zero remaining '-equivalent' section references

**PASS.**

- `grep` for `equivalent` returns only line 706 (revision log mentioning the fix was applied). Zero occurrences in doc body.
- `grep` for `SS7` returns no matches. All seven §7.3 references (lines 136, 140, 151, 310, 341, 435, 511) correctly point to §7.3 "vault-optimize — maintenance" (line 472). The three former "SS7.3-equivalent" / "SS7-equivalent" targets are now correct, legitimate section cross-references.

### Criterion 2 — Durability citation + planning-doc shorthand consistency

**PASS.**

- Line 421: `6. **Durability** (planning doc §9.6 #5) largely **dissolves**` — reads exactly as required.
- `grep` for `planning §` (bare, without "doc") returns **zero matches**. Every single planning-doc citation across the file uses the "planning doc" shorthand consistently (verified at lines 5, 167, 243, 318, 333, 353, 361, 371, 379, 409, 411, 420, 421, 423, 485, 488, 539, 630, 668, 671, 672, 705). No regressions.

### Criterion 3 — PARAG expanded on first use in §1

**PASS.**

- Line 18 (in §1 "Goal & scope"): `PARAG (Projects / Areas / Resources / Archives / Galaxy)` — first use, fully expanded.
- The re-expansion at line 162 (§3.0) adds the parenthetical about `archives/` retirement and `systems/` post-dating the acronym, which is additional detail (not a replacement for the first-use expansion).

### Criterion 4 — All JSON blocks in §3.1/§3.2 syntactically valid JSON

**FINDING.**

- **§3.2 (lines 200–215)**: PASS. Every value is a valid JSON literal: numbers, strings, booleans. The `dedupThreshold` placeholder is a quoted string `"<number 0.0-1.0>"` — valid.
- **§3.1 (lines 173–188)**: ONE REMAINING DEFECT.

```
### Finding 1

- **File**: docs/VAULT-ARCH.md
- **Line**: 184
- **Severity**: error
- **Issue**: `"hub": true | false,` is not syntactically valid JSON. The `true | false` expression is not a legal JSON value (JSON has no `|` operator; it is not a string, number, boolean literal, null, object, or array). This breaks the JSON block.
- **Evidence**: The r3 fix was supposed to quote all range placeholders as strings. Every other placeholder in the same block was fixed: `"traversal": "free | budgeted"` (line 182, valid string), `"weight": "<number 0.0-1.0>"` (line 183, valid string), `"prefix": "<optional filename prefix, for types sharing a folder>"` (line 185, valid string). The `"hub"` line was overlooked — it still uses the bare `true | false` expression form instead of a quoted string placeholder.
- **Suggested fix**: Change line 184 from `"hub": true | false,` to `"hub": "<true | false>",` — matching the quoting pattern used on lines 182, 183, and 185.
```

### Criterion 5 — §11 row 6 covers dedupThreshold default + §7.2 cross-references §11 #6

**PASS.**

- Line 673 (§11 row 6): `**Compaction horizon + staleness threshold + dedup-threshold defaults** — N days for §6.5 rollup, §4.4's stale bucket (default 90), and §7.2's `dedupThreshold` cutoff (§3.2 profile carries the placeholder)` — explicitly covers dedupThreshold. ✓
- Line 467 (§7.2): `with the cutoff configured as `vault-schema.json` `dedupThreshold` (default tuned at implementation — §11 #6).` — cross-references §11 #6. ✓

### Criterion 6 — Alias-vs-owner-class distinction

**FINDING.** The doc never explains the distinction.

- **§6.1 (line 393)** defines `agent` as "the acting agent's **alias** (e.g. `pm`, `skill`)" — used for event routing / caller identity on every engine call.
- **§4.3 (line 309)** defines `owner` as `pm | worker | verifier | dm | shared` — "primary author role-class" for note frontmatter attribution.
- The term "alias" appears only at lines 393, 523, 524 (all in the event/caller-identity context) and line 347 (wikilinks — unrelated). Nowhere does the doc state that aliases and owner classes are different namespaces, list the full set of valid aliases, or map aliases to classes (e.g., that `skill` — an alias — corresponds to `worker` — an owner class).
- The examples create a surface-level mismatch: `skill` is an alias but not an owner class; `worker` is an owner class but appears in no alias example. A reader encountering `skill` in §6.1 who then checks §4.3 and doesn't find it could reasonably be confused.

```
### Finding 2

- **File**: docs/VAULT-ARCH.md
- **Line**: 393 (and implied contrast with 309)
- **Severity**: warning
- **Issue**: The doc uses two different role-identification namespaces — "aliases" for event routing / caller identity (§6.1, §8.5) and "owner classes" for note frontmatter (§4.3) — but never explicitly states they are distinct namespaces, nor explains what aliases exist or how they map to classes. The example values differ (`skill` as alias vs `worker`/`verifier`/`dm` as owner classes) with no bridge.
- **Evidence**: `grep` for `alias` across the file returns only event/caller-identity uses (lines 393, 523, 524) and an unrelated wikilink use (line 347). §2's terminology table defines vault slot / store / contract but not aliases. No section defines the alias namespace, lists valid aliases, or states that aliases ≠ owner classes. The r3 audit explicitly rejected a finding here as "false positive" on the grounds that "events route by alias, ownership by class, both correct" — which is true, but the *reader* is never told this.
- **Suggested fix**: Add one sentence at line 393 after the alias examples, e.g.: `(Aliases are a distinct namespace from §4.3's owner classes — they identify the caller for telemetry routing, not note authorship.)`
```

---

### Full Sweep — New Internal Inconsistencies

No other new inconsistencies found. Specifically verified:

- **Zero `SS`-prefix section references** outside the revision log (line 706 only).
- **All `§` cross-references resolve to existing sections** (§1–§12, all sub-sections exist).
- **"planning doc" shorthand** consistently applied in all ~22 planning-doc citations; no bare `planning §N` regressions.
- **§3.1 vs §3.2 `dedupThreshold`**: different placeholder strings (`"<set at implementation — §11 #6>"` vs `"<number 0.0-1.0>"`) are intentional — §3.1 is the generic schema template, §3.2 is the concrete profile. Both are quoted strings (valid JSON). Not an inconsistency.
- **§12.2's mention of dead "VAULT-ARCH §11.5" backref** (line 684, 695): this is an external reference in AGENT-RUNTIME.md, acknowledged as dead, with a fix planned during reconciliation. Not an internal inconsistency.
- **No section renumbering drift**: § numbering is linear and consistent throughout.

---

## Result: NOT CONVERGED

Two findings remain from the r3 fix batch:

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Zero '-equivalent' references | PASS |
| 2 | Durability citation + planning-doc shorthand | PASS |
| 3 | PARAG expanded first use in §1 | PASS |
| 4 | JSON validity in §3.1/§3.2 | **FINDING** — line 184 `"hub": true \| false` still invalid |
| 5 | §11 #6 + §7.2 cross-reference | PASS |
| 6 | Alias-vs-class explanation | **FINDING** — distinction never stated |
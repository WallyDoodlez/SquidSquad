I've read the entire file and traced the new additions against the v2 framing. Here are my findings:

---

### Finding 1

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Line**: 522 (BNF comment) vs. 529 (prose rule)
- **Severity**: error
- **Issue**: The BNF comment `# nested allowed; max depth 3` on the `name` production contradicts the explicit prose rule on line 529: "Max one nesting level beyond the sub-slot (i.e. `step:cycle/foo/bar` is allowed; `step:cycle/foo/bar/baz` is not)." The BNF `segment ("/" segment)*` allows arbitrary nesting, and "max depth 3" for `name` would allow `foo/bar/baz` (3 segments), which maps to `step:cycle/foo/bar/baz` — explicitly forbidden by the prose. No single interpretation of "max depth 3" makes both the comment and the prose rule simultaneously true.
- **Evidence**: The prose rule unambiguously states one nesting level. The valid example `step:cycle/vault/remember` (line 538) has one `/` in the name portion (2 segments). The BNF comment should say `max depth 2` for the name (meaning at most `segment "/" segment`) or the comment should be removed and the BNF tightened to `segment ("/" segment)?`.
- **Suggested fix**: Change line 522 comment to `# nested allowed; max depth 2 (one "/" in name)` OR change the BNF production to `name ::= segment ("/" segment)?` to match the prose constraint.

---

### Finding 2

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Line**: 266
- **Severity**: warning
- **Issue**: §4.5 step 1 cross-references §6.1 for "equivalent reference grammar": "(or equivalent reference grammar — see §6.1)." But §6.1 defines **step ID grammar** (BNF for `step:boot/permission-check`) and step↔sub-skill mapping — it does NOT define any "reference grammar" for how sub-skill names appear in composed orchestration content. The actual reference grammar pattern (`→ run sub-skill: <name>`) is introduced in §4.1 step 4 and §5.3. An implementer following this cross-reference to §6.1 would find no reference grammar definition there.
- **Evidence**: Searching §6.1 (lines 513-555) reveals only step ID BNF, step↔sub-skill mapping rules, stability guarantees, and renaming protocol. There is zero mention of "→ run sub-skill:" syntax, reference extraction, or any reference grammar.
- **Suggested fix**: Change line 266 to reference §4.1 step 4 or §5.3 instead: e.g., `(or equivalent reference grammar — see §4.1 step 4 and §5.3)`.

---

### Finding 3

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Lines**: 674, 701
- **Severity**: warning
- **Issue**: §6.6 uses the phrase "L3 `replace` overlays" twice (line 674: "Per-role overrides (L3 `replace` overlays on the default)"; line 701: "with the per-role overrides applied via L3 `replace` ops on the default-model bullet"). But `replace` is defined in §3.3 as an **L4-only** operation — the L4 frontmatter `op` field supports `replace | insert-before | insert-after | append`, while L1-L3 frontmatter (§3.2) only declares `slot`, `ordinal`, and `step-ids`. L3 files have no `op` field and no `replace` semantics. L3 overrides L1/L2 content through the standard stacking/layering mechanism, not through `replace` ops.
- **Evidence**: §3.2 (lines 115-126) defines L1-L3 frontmatter with `slot`, `ordinal`, `step-ids` only. §3.3 (lines 131-141) defines L4 frontmatter with the `op` field explicitly. Using "replace" to describe L3 behavior conflates two distinct mechanisms and would mislead implementers into thinking L3 files support `op: replace` frontmatter.
- **Suggested fix**: Reword lines 674 and 701 to avoid the L4-specific term "replace." E.g., line 674: "Per-role overrides (L3 content that overrides the L1 default via the standard layering mechanism)"; line 701: "with the per-role overrides applied via L3 content at the same slot/ordinal position."

---

### Finding 4

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Lines**: 395, 442
- **Severity**: warning
- **Issue**: The §5.1 swap described in the revision log (line 1021) changed the role naming in §5.1 from the old concrete-instance "PM/QA/DM/dev/skill" to L2 categorical names "pm, qa, worker, dm" (line 324). However, the two worked examples in §5.6.1 and §5.6.2 were NOT updated to match. Line 395 still reads "1.2 Team membership (4-role: PM, QA, DM, dev/skill)" and line 442 repeats the same. The document is now internally inconsistent on role naming — §5.1 and §6.6 use the new naming while §5.6, §1 non-goals (line 59), and §2 (line 72) use the old naming.
- **Evidence**: Compare line 324 ("four-role team: pm, qa, worker, dm") against line 395 ("4-role: PM, QA, DM, dev/skill") and line 442 (same). The worked examples in §5.6 were part of the §5 structure and should reflect the same naming convention as §5.1.
- **Suggested fix**: Update lines 395 and 442 to use the new L2 categorical names consistently with §5.1: e.g., "1.2 Team membership (4-role: pm, qa, worker, dm)."

---

### Finding 5

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Line**: 272
- **Severity**: warning
- **Issue**: §4.5 step 4 says "emit a warning and (under §8 sync mechanisms) refuse to ship" for catalog drift. The parenthetical cross-reference to §8 is misleading because §8 describes three mechanisms for **source-output drift** (L1-L3 sources changed without regenerating `.squidsquad/<role>/CLAUDE.md`), not **catalog-source drift** (catalog entries out of sync with source files on disk). The §4.5 mermaid diagram (lines 287-294) correctly shows the drift check as Warn → Abort within the compose pipeline itself — an immediate compose-time failure, not deferred to §8 gates. The prose blurs this distinction.
- **Evidence**: §8.1 (line 836) checks "If any file in `references/sub-skills/`, `references/roles/`, or `references/sub-skills/manifest.md` is changed, the PR must also include the regenerated `.squidsquad/<role>/CLAUDE.md` outputs." It doesn't mention `sub-skill-catalog.md` or catalog-source consistency. §8.2 and §8.3 similarly concern source→output drift, not catalog↔source drift. The §4.5 catalog drift check is a distinct validation that runs within compose itself (as the diagram shows), not a concern deferred to §8.
- **Suggested fix**: Replace the parenthetical with something accurate: e.g., "refuse to ship (i.e., compose aborts with a diagnostic, matching the unresolved-reference path above)." Or if the intent is truly to tie to §8, expand §8 to explicitly cover catalog drift.

---

**Summary**: Five findings — one error (Finding 1: contradictory BNF depth constraint), four warnings (misleading cross-references, terminology conflation, inconsistent role naming, ambiguous drift-handling prose). None are style preferences; all are substantive correctness or consistency issues that would confuse implementers.
I've carefully analyzed COMPOSE-ARCHITECTURE.md for internal contradictions, cross-section drift, stale references, and model inconsistency. Here are my findings:

---

### Finding 1

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Line**: Non-goals bullet (approximately line 35-38 in the raw)
- **Severity**: HIGH
- **Issue**: Stale reference to `EVENT-ARCHITECTURE.md` in §1 non-goals. The bullet reads: "Defining the event bus, harness lifecycle, or agent state machine — see `EVENT-ARCHITECTURE.md`." However, §14 explicitly states that `EVENT-ARCHITECTURE.md` (along with `EVENT-BUS-ARCHITECTURE.md` and `event-bus.md`) has been superseded and archived at `docs/archive/EVENT-ARCHITECTURE.md`. The companion docs header at the top of the file correctly references `AGENT-RUNTIME.md` as the consolidated runtime doc.
- **Evidence**: The revision log (13a) explicitly states "§14 references updated for the archived event docs" — confirming §14 was updated but §1 was not. The companion docs header lists `AGENT-RUNTIME.md` as "(loop vs event runtime, harness, event bus)". §14 lists the old event docs under `docs/archive/` as "superseded; kept for traceability."
- **Suggested fix**: Replace the reference `EVENT-ARCHITECTURE.md` with `AGENT-RUNTIME.md` to match the companion docs header and §14. The bullet should read: "Defining the event bus, harness lifecycle, or agent state machine — see `AGENT-RUNTIME.md`."

---

### Finding 2

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Line**: §13 Glossary, "Sub-procedure" entry
- **Severity**: HIGH
- **Issue**: The glossary definition of "Sub-procedure" still reflects the **v1 inline model**, directly contradicting the v2 framing established in §6.2. The glossary entry reads: "A reusable named procedure (e.g. 'file a bug') referenced from one or more cycle steps, **written inline at H4 level.** Replaces today's standalone H2 protocol sections." (emphasis added). But §6.2 clearly states: "v2 does NOT fold them inline into step bodies (the v1 model). Instead, each becomes a **sub-skill** with its own source file and catalog entry." And: "The composed CLAUDE.md never duplicates that content."
- **Evidence**: §6.2: "Sub-procedures are sub-skills, not inlined H2 sections" ... "v2 does NOT fold them inline into step bodies" ... "The composed CLAUDE.md never duplicates that content." The revision log (13a) confirms this is a v2 change: "§6.2 sub-procedures are sub-skills (with their own catalog entry), not folded into step bodies." The glossary entry was not updated during the v2 edit pass.
- **Suggested fix**: Rewrite the glossary entry to align with §6.2, e.g.: "Sub-procedure — A reusable named procedure (e.g. 'file a bug') authored as a **sub-skill** with its own source file and catalog entry in `sub-skill-catalog.md`. Referenced by name from cycle steps; **never inlined** into the composed CLAUDE.md. Replaces today's standalone H2 protocol sections."

---

### Finding 3

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Line**: §4.1 step 1
- **Severity**: MED
- **Issue**: §4.1 step 1 says compose reads "the `sub-skill` reference it makes" as if `sub-skill` were a frontmatter field, but the frontmatter template in §3.2 only declares `slot`, `ordinal`, and `step-ids`. There is no `sub-skill` field in the frontmatter specification. The sub-skill reference lives in the file **body** (as shown in §4.1 step 4: "e.g. `→ run sub-skill: pipeline-sentinel`"), not in frontmatter.
- **Evidence**: §3.2 frontmatter template has only `slot`, `ordinal`, and `step-ids` fields (plus `roles:` mentioned later). §4.1 step 1 lists "slot, ordinal, and (for the instructions slot) the sub-skill reference it makes" as things read from each file — the first two are frontmatter fields, making the third appear to be one as well. But no `sub-skill` frontmatter field is defined anywhere in the document. §4.1 step 4 clarifies that the sub-skill reference is in the body content.
- **Suggested fix**: Clarify §4.1 step 1 wording to distinguish frontmatter fields from body-extracted data. For example: "For each file with frontmatter, read its `slot` and `ordinal`; for files in the `instructions` slot, also extract the sub-skill name referenced in the file body (e.g. from `→ run sub-skill: <name>` directives)."

---

### Finding 4

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Line**: §6.5, paragraph referencing `common/boot-bootstrap.md`
- **Severity**: LOW
- **Issue**: §6.5 references the path `common/boot-bootstrap.md` in the context of boot bootstrap fallback behavior: "The boot bootstrap (`common/boot-bootstrap.md`) treats polling as the fallback when harness reachability fails at boot in event-mode (#9588)". However, the L1-L3 authoring paths established in §2 are `references/sub-skills/common/` and `references/roles/<role>/`. The bare `common/boot-bootstrap.md` path is ambiguous — it's not clear whether this is `references/sub-skills/common/boot-bootstrap.md` or some other location.
- **Evidence**: §2 defines L1/L2 authoring locations as `references/sub-skills/common/` and `references/sub-skills/capabilities/`. A bare `common/boot-bootstrap.md` reference without the `references/sub-skills/` prefix is inconsistent with how paths are specified elsewhere in the document (e.g., §4.1 references `references/sub-skills/`, `references/roles/<role>/`; §3.2 references `includes.yml` relative to `references/roles/<role>/`).
- **Suggested fix**: Use the full path `references/sub-skills/common/boot-bootstrap.md` for consistency with the rest of the document's path conventions.

---

### Finding 5

- **File**: docs/COMPOSE-ARCHITECTURE.md
- **Line**: §5.2 Soul section
- **Severity**: LOW
- **Issue**: §5.2 states "Inlined directly into the composed CLAUDE.md (not a reference link to `.squidsquad/<role>/SOUL.md`). The source SOUL.md file is the authoring location; compose inlines its content." The use of "inlined" here is technically correct under the v2 model (Soul is not a sub-skill; it's short identity content), but it could be confused with the v1 "inline sub-skill content" anti-pattern that v2 rejects. Readers scanning for "inline" as a v1 signal may misinterpret this.
- **Evidence**: The revision log (13a) frames v2 as moving away from "inlining sub-skill content into the composed CLAUDE.md." §5.2 uses the word "inlined" for Soul content. While Soul is not a sub-skill (it's one of the five orchestration slots), the use of the same term could create confusion about whether Soul should follow the same "thin reference" pattern. This is a documentation clarity risk, not a technical contradiction.
- **Suggested fix**: Consider replacing "Inlined directly" with "Emitted verbatim" or "Rendered directly" to avoid the word "inline," which has acquired a specific negative connotation in the v2 framing. Or add a brief parenthetical: "(Soul is orchestration content, not a sub-skill — it is emitted verbatim, not referenced.)"

---

**Summary**: Two HIGH findings (stale event-doc reference in §1, v1 glossary remnant for "Sub-procedure"), one MED finding (ambiguous frontmatter-vs-body field in §4.1), and two LOW findings (bare path in §6.5, confusing "inlined" usage in §5.2). The core v2 model — thin orchestration with sub-skill references — is internally consistent across §§1-6, but the edit pass missed the non-goals reference and the glossary definition.
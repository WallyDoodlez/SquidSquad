# TEST-PLAN-13066 — Vault frontmatter debt + source-taxonomy mismatch

**Source**: GitHub issue #13066 Acceptance Criteria (Suggested remediation, two decisions).
**Derived without reading the diff.**

This is a vault DATA-conformance task (no code/test surface). The enforced gate is
`vault_check.py check-frontmatter`. Two decision-ACs from the issue body:

- **AC-1 (Source taxonomy)** — EITHER expand `VALID_SOURCES` to cover real provenance,
  OR conform the 6 out-of-enum offenders to existing enum values + keep guidance. A
  coherent decision must be made and applied.
- **AC-2 (Backfill)** — one-time pass adding missing required frontmatter fields to the
  ~14 debt notes, normalizing auto-memory-shaped frontmatter to vault shape.

## Test Cases

### TC-1 (covers AC-2): Full-vault frontmatter sweep is clean
- **Precondition**: committed vault state on main at/after a59af1904.
- **Steps**: run the enforced gate against the committed galaxy notes.
- **Expected**: `OK: All galaxy note frontmatter valid` (zero FAIL lines).
- **Verification command**: `python references/scripts/vault_check.py check-frontmatter`
  (run against committed state — exclude any uncommitted local notes).

### TC-2 (covers AC-1): Source-taxonomy decision applied coherently
- **Precondition**: same.
- **Steps**: inspect `VALID_SOURCES` in vault_check.py and the 6 previously-invalid notes.
- **Expected**: a coherent decision is applied. If "conform": every note's `source`
  is one of the enforced enum {conversation, code, review, observation, research}, and
  `VALID_SOURCES` is unchanged from its long-stable value. If "expand": the enum now
  contains the new provenance values.
- **Verification command**: `grep VALID_SOURCES references/scripts/vault_check.py` +
  per-note `source:` inspection via the #13066 commit.

### TC-3 (scope guard): Frontmatter-only, bodies preserved verbatim
- **Precondition**: same.
- **Steps**: inspect the #13066 commit diff per note.
- **Expected**: changes are confined to the frontmatter block (and benign EOF-newline
  normalization). Note body prose is byte-identical pre/post.
- **Verification command**: `git show a59af1904 -- <note>` (spot-check several incl. a
  rebuilt auto-memory-shaped note).

## Coverage matrix
- AC-1 → TC-2
- AC-2 → TC-1, TC-3

## Comprehension Questions
N/A — vault data conformance, not LLM-consumed instruction. No CQ spec.

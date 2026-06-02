# TASK: Documentation cross-reference → wiki-link conversion + durable sub-skill

## Operator directive
> "re-work all the md files post v2 deployment and sucessful test, so that all cross references uses wiki links. create a new documentation-linkage subskill that will do just that to make the skill durable to do the task"

## Scope

Two deliverables in one task:

### Deliverable 1 — `documentation-linkage` sub-skill (durable how-to)
- New file at `references/sub-skills/common/documentation-linkage.md` (common-tier so any role can pull it).
- Defines the procedure for converting cross-references in `.md` files to wiki-link syntax (`[[target]]`), including:
  - Which file trees are in scope (`docs/`, `references/sub-skills/`, `.squidsquad/<role>/planning/`, top-level `README.md` / `SKILL.md` / `CHANGELOG.md`).
  - Wiki-link target format (slug derivation, case rules, ambiguous-match resolution).
  - What counts as a "cross-reference" (markdown links `[text](path.md)` → `[[slug]]`, bare path mentions, relative-path links, anchored links `path.md#section`).
  - How to handle non-wiki targets (external URLs, file paths outside the .md graph, broken/dead links).
  - Idempotency: running the sub-skill twice yields no diff on a converted corpus.
  - Validation: post-run check that every emitted `[[slug]]` resolves to a real target file, and that no orphan wiki-links exist.
- Sub-skill is structured per existing common/ sub-skill conventions (frontmatter + ordered steps).

### Deliverable 2 — first-pass application
- Run the new sub-skill across the in-scope file trees and land the resulting `[[…]]` conversions in a single PR.
- PR description cites the sub-skill and lists the file-count delta.

## Gate
- **Hard gate**: This task is BLOCKED until both E6 (#10685, V2 CUTOVER) and E7 (#10686, V2 smoke) are Shipped. Reason: cross-reference rework on the doc corpus while v2 compose is mid-flight risks colliding with v2's own L1–L4 fragment edits. Run only after the arch is settled.
- Skill must verify both #10685 and #10686 are in `status:shipped` before picking up.

## Acceptance Criteria

1. **AC1** — `references/sub-skills/common/documentation-linkage.md` exists, follows common-tier sub-skill conventions, and documents the full procedure described in Deliverable 1 (scope, target format, edge cases, idempotency, validation).
2. **AC2** — Running the sub-skill procedure across the in-scope trees produces a self-consistent corpus: every emitted `[[slug]]` resolves to a real target file; no orphan wiki-links remain.
3. **AC3** — Re-running the sub-skill on the converted corpus produces zero diff (idempotency).
4. **AC4** — All external URLs and out-of-graph file paths are preserved as-is (not coerced into wiki-links).
5. **AC5** — Pre-merge DS code review via `python references/scripts/model_router.py code-review --task-id "<this-issue-#>" --input-files "<diff>" --output-file ".squidsquad/skill/planning/CODE-REVIEW-<NUMBER>.md"`. The `CODE-REVIEW-<NUMBER>.md` artifact must exist and be cited in the PR description. Fallback to Claude via Agent tool if DS unavailable. Findings processed per standard template (fix locally; file to PM if structural).
6. **AC6** — PR cites this CONTEXT artifact and lists the file-count delta (how many .md files were touched, how many cross-references converted).

## Out of scope
- Wiki-link rendering tooling. This task only converts the syntax; rendering (if needed) is a separate concern.
- Migration of inline reference styles inside code comments / docstrings — `.md` files only.
- Auto-fixing broken links that aren't already cross-references. Broken links surface as validation failures (AC2), not silent rewrites.

## Notes
- Why a sub-skill: the operator explicitly asked for this to be durable so any agent can re-run the procedure later (when new .md files are added). The sub-skill is the durable artifact; Deliverable 2 is the first invocation.
- Sub-skill creation: this is code-consumed data (compose.py reads sub-skills), so the work belongs to skill, not PM, per `feedback_pm_docs_only`.

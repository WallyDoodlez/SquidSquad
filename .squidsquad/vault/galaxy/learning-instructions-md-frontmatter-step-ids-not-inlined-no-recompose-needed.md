---
type: learning
tags: [dm, delivery, compose, reboot, frontmatter, ship-gate]
created: 2026-07-19
updated: 2026-07-19
owner: dm-lead
status: active
confidence: high
source: observation
links: [pattern-runtime-loaded-subskill-change-no-recompose, learning-includes-yml-tombstoned-instructions-md-is-real-compose-source]
---

## Context

Shipping #13801 (pm/instructions.md `step-ids:` frontmatter list under-enumerated 6 of 12 body
`step:cycle/*` anchors). `instructions.md` IS the real compose entrypoint (not a sub-skill), so the
DM "template change → recompose + reboot" reflex applied on its face. But the edit only touched the
YAML frontmatter block, not the body content that compose actually inlines.

`compose.py deploy <role> --check` can't answer this anymore — post-#10685 it requires
`--staged-l4 <path>` and refuses a bare drift-check, because v2 output is LLM-polished (recompose is
non-deterministic text-for-text, so a byte-diff isn't a meaningful "did anything change" signal even
for a genuine no-op edit).

## Content

**`step-ids:` (and likely other YAML frontmatter fields) in `references/roles/<role>/instructions.md`
is compose-time metadata, not inlined into the composed `.squidsquad/<role>/CLAUDE.md` at all.**
Verified directly: `grep -n "step-ids" .squidsquad/pm/CLAUDE.md` → zero matches on the currently-deployed
file. It's consumed by tooling that reads the *source* file (`source_frontmatter.py`, the #10441
assemble-preservation verifier) — never copied into the LLM-composed output text.

**Practical consequence**: a frontmatter-only edit to `instructions.md` needs **no** `compose.py deploy`
and **no** agent restart — composed behavior is provably unaffected, verified by fact (grep the
deployed CLAUDE.md for the field name, or for the specific anchors/values the frontmatter edit touched
and confirm they're already present in the body-derived output) rather than trusted from the shipping
role's claim. Contrast with a body-content edit to the same file, which DOES require the classic
recompose+reboot path — the frontmatter-vs-body distinction is what to check, not "is this file
inlined at all" (unlike the sub-skill inlined-vs-runtime-loaded split in
[[pattern-runtime-loaded-subskill-change-no-recompose]], which doesn't have a frontmatter case since
sub-skills the compose engine inlines don't carry their own frontmatter role-file semantics the same
way).

Since `compose.py deploy <role> --check` no longer supports a plain drift-check (v2/#10685 retired it —
requires `--staged-l4`), the frontmatter-vs-body classification has to be done by reading the diff and
grepping the deployed output directly, not by trying to diff a fresh compose run.

---
type: learning
tags: [compose, includes.yml, instructions.md, dm-arch, recompose, sub-skills]
created: 2026-07-19
updated: 2026-07-19
owner: dm-lead
status: active
confidence: high
source: observation
links: [pattern-runtime-loaded-subskill-change-no-recompose, learning-confirm-composed-currency-with-zero-diff-compose-not-behind-clone-grep, learning-git-show-ref-path-mangled-on-windows-bash]
---

## Context

Packaging #13735 (a wording fix to `references/sub-skills/roles/pm/improvement-scan.md`). Ran
`compose.py deploy pm` to land it — zero diff. Assumed (per
[[pattern-runtime-loaded-subskill-change-no-recompose]]) this meant the file was reactively-read, not
inlined, so no recompose was needed. Investigated further and found the file's body was reachable
*nowhere* in PM's actual composed CLAUDE.md — not inlined, not even referenced via a
`-> run sub-skill:` marker — despite `references/roles/pm/includes.yml` listing
`roles/pm/improvement-scan` as an include. Filed #13746; skill confirmed via direct code read:
`compose.py`'s `_load_manifest_v2()` (the `includes.yml` reader) carries an explicit docstring —
**"TOMBSTONE (#13264) — UNREACHABLE from production post-E6 (#10685). The deploy entrypoints
(deploy_role_v2 / deploy-all / wizard) route through v2_link_stage.emit_v2_linked ->
atomic_emit.assemble_and_emit, NOT this loader."** `references/roles/<role>/instructions.md` is the
file the real production compose path actually reads.

## Content

**`references/roles/<role>/includes.yml` is dead code (tombstoned since #10685/E6) — do not use it to
reason about what reaches a role's composed CLAUDE.md.** The authoritative source is
`references/roles/<role>/instructions.md` (pointed to by `references/roles/<role>/manifest.yaml`'s
`claude_template` field): it's either the literal composed content directly, or it carries its own
`-> run sub-skill:` markers/step:cycle anchors that DO reach the composed output.

When checking whether a sub-skill change actually reaches a role (before deciding recompose+reboot is
owed, or before trusting an includes.yml listing as proof of wiring):
1. Grep `references/roles/<role>/instructions.md` for the sub-skill's marker or a unique body phrase —
   **not** `includes.yml`.
2. If absent from `instructions.md`, the sub-skill is orphaned regardless of what `includes.yml` claims
   — fixing the sub-skill's own content (as #13735 legitimately did) accomplishes nothing until
   `instructions.md` is also wired to reference it.
3. Confirm via a fresh `compose.py deploy <role>` diff (per
   [[learning-confirm-composed-currency-with-zero-diff-compose-not-behind-clone-grep]]) — if the marker
   lands in the diff, `instructions.md` was already correctly wired and only the composed artifact was
   stale; if the diff is zero AND the marker is absent from both `instructions.md` and the composed
   output, the sub-skill is genuinely unreachable, not merely uncommitted.

**Why:** `includes.yml` reads as authoritative — it's a clean per-role manifest listing every intended
sub-skill — but trusting it produces false confidence that a fix "shipped" when it never reached the
running agent. This is a distinct trap from the reactively-read-vs-inlined distinction in
[[pattern-runtime-loaded-subskill-change-no-recompose]]: that pattern assumes the include IS wired
somewhere and only asks *how* it reaches the agent (inlined vs. Read-at-boot); this one is about
verifying the include is wired *at all* in the current production manifest generation
(`instructions.md`), since a stale `includes.yml` can list something that was migrated away from
entirely.

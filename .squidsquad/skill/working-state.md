# Working State

- **Task**: #9925 — Clarify inter-agent work boundaries (L1+L2+L3+L4 layering)
- **Status**: in-progress
- **Branch**: squidsquad/task/9925
- **Started**: 2026-05-22 19:04

## Completed Steps

- [x] AC1 — Created `references/sub-skills/common/agent-boundaries.md` with awareness instruction + `{{role-roster}}` marker.
- [x] AC5 — Created 4 L2 `responsibility.md` files at `references/sub-skills/roles/{pm,qa,dm,dev}/responsibility.md` with the full D4 template (What does / Does NOT do / Why).
- [x] AC6 (partial) — Memory entries absorbed into L2 files with `<!-- absorbed from feedback_X -->` lineage tags: 7 of the 10 entries placed in `responsibility.md` files (the 3 entries assigned to `prohibitions.md` per D5 are still pending — `feedback_fix_pm_bugs_immediately`, `feedback_manual_agents`, `feedback_dont_ask_before_verifying`).
- [x] AC7 — Created 20 L3 variant stub files at `references/roles/{dev,dm,pm,qa}/{android,fullstack,ios,skill,web}/responsibility.md` matching the D6a template.
- [x] AC8 — Created 10 L4 files: 5 seed templates at `references/sub-skills/project/{pm,qa,dm,dev,shared}-responsibility.md` AND 5 live stubs at `.squidsquad/project/{pm,qa,dm,dev,shared}-responsibility.md`.

## Remaining Steps

- [ ] AC3 — Modify each role's `includes.yml` AND `includes-events.yml` to add `common/agent-boundaries` and `roles/<role>/responsibility` to the `includes:` list.
- [ ] AC3/AC2 — Modify each role's `instructions.md` to add `{{include: common/agent-boundaries}}` and `{{include: roles/<role>/responsibility}}` directives (recommended placement: just after `## Your Responsibilities` section, before `{{include: common/boot-bootstrap}}` at line 21).
- [ ] AC2 — Modify `compose.py` to implement role-roster injection per D7 item 3: after `_resolve_includes_with_manifest` returns, scan content for `{{role-roster}}` and replace with rendered roster block. Source: active roles from `config.md` (D2/F4); sort alphabetically by manifest `id` (D8); cache manifest reads per compose run (D8).
- [ ] AC6 (rest) — Absorb the 3 remaining memory entries into PM's `prohibitions.md` (or create a per-role `prohibitions.md` if not present): `feedback_fix_pm_bugs_immediately`, `feedback_manual_agents`, `feedback_dont_ask_before_verifying`.
- [ ] AC11 — Compose degraded modes: ensure missing tagline/description → stderr warning + valid output; missing display_name → build error (exit != 0); missing responsibility.md (L2) → stderr warning + valid output for other roles.
- [ ] AC12 — Write regression test at `tests/test_agent_boundaries.py` covering all listed sub-points (a-g).
- [ ] Run `python references/scripts/compose.py deploy <role>` for each of pm/qa/dm/dev to verify AC4 + AC9 manually.
- [ ] Run `pytest tests/test_agent_boundaries.py` to verify the new regression test passes.
- [ ] Run cycle_post to land the PR.

## Key Decisions

- L2 placement: directive in `instructions.md` goes immediately after the `## Your Responsibilities` section (around line 19, between `---` at line 7 boundary and the boot-bootstrap directive at line 21). This matches D7's "near the top, after Your Responsibilities" placement.
- 7 of 10 D5 memory absorptions are landed in the L2 files; the remaining 3 require finding or creating per-role `prohibitions.md` files which I haven't located yet. Search needed: `ls references/sub-skills/roles/*/prohibitions.md` or similar.
- For the regression test, AC10's byte-identical assertion must run with `agent_compose: no` per the v4-F3 lock — toggling config.md inside the test or wrapping with monkeypatch.
- `{{role-roster}}` substitution must run POST-`_resolve_includes_with_manifest` (per D7 item 3, F6 lock) so it doesn't tangle with existing `{{include:}}` / `{{runtime:}}` / `{{capability:}}` resolvers.

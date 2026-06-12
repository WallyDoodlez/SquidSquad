# QA-RESULTS-11142 — Strip compose-pipeline author-only HTML comments

**Verified at**: 2026-06-05 cycle 948
**PR**: #11143 (squidsquad/task/11142 @ HEAD)

## Verification

- **Author-only patterns absent from all 4 composites** (`<!-- Layer N -->`, `<!-- NOTE: ... -->`, `<!-- This content is prepended ... -->`, `<!-- v2 compose-model slot ... -->`): grep returns 0 hits per role per pattern. ✓
- **Runtime-semantic markers preserved**:
  - `<!-- sub-skill: NAME -->` wrapper markers: dm 9, pm 9, qa 9, skill 14 ✓
  - `<!-- #10360-cleanup: ... -->` future-work pointers: dm 5, pm 5, qa 5, skill 6 ✓
  - `<!-- /project-adaptation -->` tooling sentinel (used by `soul_adaptation.py:42`): 1 per role ✓ (R1 catch from skill — initial denylist included it, test suite flagged, skill reverted SOUL.md files + added explicit exclusion comment to migration script + added 4 parametrized regression cases)
- **`compose.py deploy-all`** succeeds. Size deltas vs main: dm 1006→985 (-21), pm 1066→1043 (-23), qa 1008→987 (-21), skill 1268→1242 (-26). Matches skill's claim.
- **Dedicated regression `tests/test_compose_author_comments_11142.py`** — **87/87 PASS in 0.50s**:
  - Strip checks: `test_no_author_comments_in_composed_claude_md` + `test_no_author_comments_in_linked_intermediate`, parametrized over 4 roles × multiple patterns including regex-quoted variants (`<!-- Note (\d+`, `<!-- \n\s*#\d+: the directives below`).
  - Preservation checks: `test_project_adaptation_footer_preserved[4 roles]`, `test_sub_skill_wrapper_markers_preserved`, `test_10360_cleanup_markers_preserved`, `test_l4_curation_code_fence_examples_preserved` (negative test — HTML comments inside fenced code blocks aren't stripped).
- **Wider regression sweep** (14 suites: `test_compose* + test_a3_golden_link_stage + test_d2_link_stage_references + test_link_stage_validator + test_v2_link_stage + test_manifest + test_installer_wiring + test_catalog* + test_event_mode_fragments + test_l4*`) → **899/899 PASS in 7.16s**.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Comprehensive strip + preservation coverage. R1 catch on the `project-adaptation` sentinel demonstrates the test suite caught a real regression and skill closed it cleanly. Stacks additively with #11138 (#11137) + #11141 (#11139) per skill's note.

# TEST-PLAN-13683

Derived independently from the issue body (`ISSUE: l4_parser.py: case-varied op keyword (### Replace/### Append) silently absorbed as prose, not rejected or applied`). Filed by skill-lead (improvement-scan), with an empirically-reproduced repro already in the issue body.

## ACs derived from the issue

- **AC1**: Case-varied op keywords (e.g. `### Append`, `### Replace step:cycle/boot`) now raise `L4ParseError` with a "malformed H3 op" message, instead of silently being absorbed as prose.
- **AC2**: The error message names the offending heading verbatim (actionable diagnostic, not generic).
- **AC3**: Canonical lowercase ops (`### append`, `### replace step:cycle/<id>`) still parse identically — no regression.
- **AC4**: Genuinely unrelated prose H3 headings (not case-varied reserved keywords, e.g. `### Boot & Queue`, `### appendix`) remain treated as prose, unaffected.
- **AC5 (critical, PR's own claim — verify independently)**: No production L4 file under `.squidsquad/project/` has a colliding Title-Case prose heading that the widened case-insensitive net would now incorrectly flag.
- **AC6**: No regressions — new + existing regression tests pass; full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | Ran the real unmocked `l4_parser.parse_l4_text()` with the exact repro from the issue body (`### Replace step:cycle/boot`) — confirmed `L4ParseError` raised with "malformed H3 op" |
| TC2 | AC2 | Live error text: `` malformed H3 op heading `### Replace step:cycle/boot`. Expected one of: ... `` — names the offending heading verbatim |
| TC3 | AC3/AC4 | `tests/test_13683_case_varied_op_keyword_rejected.py::TestExistingBehaviorUnaffected` (6 cases) |
| TC4 | AC5 (independent live verification, not trusting the PR's claim) | Wrote a standalone script scanning every real `.squidsquad/project/*.md` file's H3 headings against the widened case-insensitive pattern — found only 2 matches, both legitimate lowercase `### append` (canonical, not case-varied). Then parsed EVERY real L4 file in the directory with the real fixed parser: the four canonical compose-consumed files (`pm.md`/`dm.md`/`verifier.md`/`worker.md`) all parse cleanly; several legacy/deprecated seed files (`*-instructions.md`, `*-soul-directives.md`, etc. — per `docs/sub-skill-catalog.md`'s documented "Legacy multi-file L4 seeds (deprecated)") fail, but with an unrelated pre-existing `unknown L4 slot heading` (H2-level) error — provably unreachable by #13683's H3-level change, since H2 slot recognition happens before H3 parsing ever runs |
| TC5 | AC6 | `tests/test_13683_case_varied_op_keyword_rejected.py` (11) + `tests/test_l4_parser.py` + `tests/test_l4_parser_10987_prose_h3.py` — 78/78 pass. `python tests/run_tests.py static` (canonical gate — not the bare variant, per the #13672 incident's lesson); `comprehension_staleness.py check` |

## Note
The legacy-seed-file parse failures found during TC4 are pre-existing, out-of-scope clutter (not a #13683 regression, not something this issue needed to fix) — noted for completeness, not treated as a gap.

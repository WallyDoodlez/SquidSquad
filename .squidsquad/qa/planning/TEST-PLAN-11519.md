# TEST-PLAN-11519 — Retire vestigial ~/.squidsquad/clones/ helpers in shared_fs.py

**Issue**: #11519 (type:issue, severity:low, role:skill) — dead clones/ helpers (dead since #3100). PR #11530. Bug = auto-approved.
**Derived from**: issue "Expected" (independent of worker code).

## ACs (verifier interpretation)
- **AC-1**: Unused clones helpers retired — `read_clones`, `write_clone`, `read-clones`/`write-clone` subcommands, and `init`'s `~/.squidsquad/clones/` creation removed (plus any now-unused imports).
- **AC-2**: No remaining production consumer — OR if one exists, it's confirmed and preserved. (Issue: "Skill judges whether anything still legitimately needs them.")
- **AC-3**: Docs synced — WIZARD.md `init` description no longer claims `clones/` is created.
- **AC-4**: No regression — `test_shared_fs`, #1496 fallback test, #3100 regression (`test_boot_remote`/`test_health_check`), canonical gate all green.

## Test Cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC-1 | diff `shared_fs.py` | helpers + subcommands + init dir + `json` import removed |
| TC-2 | AC-2 | grep `read_clones\|write_clone\|read-clones\|write-clone` over references/, tests/, start.sh | no external consumer |
| TC-3 | AC-2 | grep `squidsquad/clones\|clones_dir` | remaining refs are only #3100 removal-docstrings + regression tests asserting clones/ stays dead |
| TC-4 | AC-1 | grep `json` in shared_fs.py | none (import drop safe) |
| TC-5 | AC-3 | diff WIZARD.md | line drops "and clones/"; matches code |
| TC-6 | AC-4 | pytest test_shared_fs + test_feat_1496 + test_boot_remote + test_health_check | all green (137p/1s) |
| TC-7 | AC-4 | canonical gate `tests/run_tests.py` | OK |

## CQ note
WIZARD.md is LLM-consumed (installer-agent runbook), so audience-checked per [[learning-cq-applies-to-launcher-injected-prompts]]. The changed line is **descriptive** (states what `shared_fs.py init` creates), not a directive the agent acts on, and is now verified-accurate against code. → CQ N/A (documented, not hand-waved).

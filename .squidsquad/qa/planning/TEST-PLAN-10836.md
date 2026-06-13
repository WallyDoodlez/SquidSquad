# TEST-PLAN-10836 (R1) — INSTALLER-ARCH drift reconciliation

**Issue**: #10836 R1 (type:task, priority:high, role:pm) — reconcile `docs/INSTALLER-ARCH.md` against canonical arch docs + code. PR #11536, docs-only.
**R2** (dep-provisioning) split to #11537 — out of scope here.
**Derived from**: issue body 11 findings + PM's 3 verification dimensions (comment 2026-06-13). Independent re-verify per zero-gap gate.

## ACs (verifier interpretation)
- **AC-1 (no residual contradictions)**: normative body carries none of the stale claims the findings removed — no `~/.squidsquad/clones/`-as-registry, no "new L4 file", no vault "read-only".
- **AC-2 (cross-refs resolve)**: every cited cross-doc section number (HARNESS-ARCH/COMPOSE/VAULT-ARCH/AGENT-RUNTIME §x) resolves to a real heading in the target doc AND is semantically apt.
- **AC-3 (code ground-truth)**: doc-asserted facts hold against code — boot_remote reads `.local-config`; agent dirs carry the compose triple; `.assemble-cache/` framing matches COMPOSE.
- **AC-4 (per-finding)**: each of the 11 findings (E1,E2,E3,E4,E5,W4,W5,W6,L1,L2,L3; W3 accepted) is reflected in the doc.

## Test cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC-1 | grep `clones/`, `new L4 file`, `read-only` | only vestigial/all-R-W framing in body; stale only in §14 revision log (append-only history) |
| TC-2 | AC-2 | grep all `§x` cross-refs; verify heading exists in target | all resolve |
| TC-3 | AC-2 | read context of E3(§9), W5(§7.2), L2(§7.5/§6), §9 Vocabulary note | semantically correct |
| TC-4 | AC-3 | grep boot_remote for .local-config | reads it, mandatory, sole registry |
| TC-5 | AC-3 | ls agent dir for triple; check COMPOSE for .assemble-cache | triple present; COMPOSE L740 git-tracks .assemble-cache per alias |
| TC-6 | AC-4 | spot-read each finding's edit + §14 revision log | all 11 present |

## CQ note
INSTALLER-ARCH.md is a TRD **reference/architecture doc**, not agent instructions composed into a runtime CLAUDE.md (descriptive, not directive). Per the comprehension standard (LLM-consumed *instructions*: templates, sub-skills, CLAUDE.md fragments, SOUL) → CQ N/A. Documented per [[learning-cq-applies-to-launcher-injected-prompts]] (checked, not auto-dismissed).

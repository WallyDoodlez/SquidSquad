# TEST-PLAN-11537 — INSTALLER-ARCH R2 dep-provisioning section

**Issue**: #11537 (type:task, priority:medium, role:pm) — INSTALLER-ARCH §4.1 dependency-provisioning section (original #10836 scope, post-R1). PR #11588, docs-only.
**Derived from**: PM's 2 verification dimensions + the §4.1 contract. Independent re-verify (zero-gap gate).

## ACs (verifier interpretation)
- **AC-1 (no internal contradiction)**: §4.1 host-level provisioning reconciles with §2 commitment 2 + §11.1 "no writes during Phases 0–4" — the invariant must be scoped to *target-repo* writes, with host-level installs carved out (consent-gated, outside repo).
- **AC-2 (dependency facts match code)**: requirements.txt = 4 pkgs (fastapi/starlette/uvicorn/watchdog); pyyaml dev-only AND genuinely runtime-used; wizard checks only gh; start.sh + start.ps1 both hard-code 2-of-4.
- **AC-3 (honest target-vs-today)**: unimplemented design (gather-all/consent/provision) clearly marked target, not current.
- **AC-4 (§3.1 drift fix)**: Environment row no longer claims all deps are checked; points to §4.1.

## Test cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC-1 | read §2 commitment 2, §11.1, §4.1 | carve-out scopes invariant to target-repo; host installs consent-gated + outside-repo; consistent |
| TC-2 | AC-2 | cat requirements.txt | exactly 4 pkgs: fastapi, starlette, uvicorn, watchdog |
| TC-3 | AC-2 | grep yaml in requirements*.txt + cited modules | pyyaml dev-only; imported by manifest/capability_check/source_frontmatter/wizard (runtime) |
| TC-4 | AC-2 | wizard.py dep checks; start.sh/start.ps1 pip lines | wizard checks only gh; both start scripts `pip install fastapi uvicorn` (2/4) |
| TC-5 | AC-3 | read §4.1 "Current state" callout + §14 | target items marked not-yet-implemented; impl filed as separate skill task |
| TC-6 | AC-4 | diff §3.1 Environment row | points to §4.1 gather-all, no false all-checked claim |

## CQ note
INSTALLER-ARCH.md = TRD reference/design contract (consumed by implementers, not composed into a runtime agent CLAUDE.md; WIZARD.md is the installer-agent runbook, not this). Descriptive, not directive. → CQ N/A (documented, same basis as #10836 R1).

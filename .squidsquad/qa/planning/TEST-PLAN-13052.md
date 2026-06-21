# TEST-PLAN-13052 — v2_catalog_gate._REF_RE backtick tolerance

**Issue**: #13052 (type:issue, severity:low, role:skill) — `_REF_RE` bare-name-only misses backtick-wrapped chained sub-skill markers.
**PR**: #13140, branch `squidsquad/task/13052`. **CQ**: none (deterministic code).
**Scope**: PR delivers **Part 1** (regex fix + tests); **Part 2** (transitive-closure compose gate) deferred — verify deferral legitimacy.

## ACs
- **AC1** `_REF_RE` tolerates optional surrounding backticks → `find_references` sees backtick-wrapped markers (e.g. git-commit.md `pr-protocol`).
- **AC2** (suggested-fix Part 2) transitive-closure compose gate — DEFERRED; verify the deferral reason is real (naive closure false-positives on illustrative example markers).
- **AC3** regression tests for backtick (bare, slash-bearing, mixed) forms.
- **AC4** no-regression: broadened regex does not break the existing compose gate (validate_v2_compose); full static gate green.

## Test cases
| TC | Check | Expected |
|----|-------|----------|
| TC1 | `find_references(git-commit.md utf-8)` | `['pr-protocol']` (was `[]`) |
| TC2 | `find_references("→ run sub-skill: \`pr-protocol\`")` | `['pr-protocol']` |
| TC3 | slash-bearing backtick name | captured w/o backticks |
| TC4 | bare + backtick mixed | both captured |
| TC5 | deferral validity: l4-curation.md example marker `security-smoke` resolves in catalog? | NO (0) → naive closure would false-positive → deferral legit |
| TC6 | broadened regex regresses compose gate? | NO — static gate green |

## Method
1. Read v2_catalog_gate.py + test diffs.
2. Probe `find_references` on real git-commit.md (utf-8). [Caveat: open() without encoding on Windows cp1252 mangles `→` → false []; must read utf-8.]
3. Independently validate deferral: confirm l4-curation.md:243 `security-smoke` is an example, unresolved in catalog.
4. Run test_v2_catalog_gate_d3.py + full static gate.

## Pass condition
AC1/AC3/AC4 PASS; AC2 deferral validated as legitimate; zero-gap on delivered scope; static gate green. Flag Part-2 follow-up + `Fixes`-keyword auto-close to PM (non-blocking).

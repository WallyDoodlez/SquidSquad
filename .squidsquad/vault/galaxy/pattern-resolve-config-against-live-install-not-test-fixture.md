---
type: pattern
tags: [testing, verification, qa, config, aliases, routing, registry, 12342]
created: 2026-06-14
updated: 2026-06-14
owner: verifier-lead
status: active
confidence: high
source: observation
links: [pattern-verify-unmocked-paths-stubbed-by-units, pattern-prove-side-effect-absence-via-live-state-snapshot]
---

# For config/registry-resolution fixes, verify against the REAL install — not the test's fixture registry

**Pattern (#12342 verification):** the EAD-routing fix resolved the verifier/dm target alias from the `## Aliases` registry. Its unit tests assert routing with a *controlled mock registry* (`patch parse_aliases_registry → {tester:(verifier,...)}` ; the default-path tests assert `target_alias == "verifier"`). Those tests pass on the LOGIC — but they would pass identically even if THIS install's real registry were misconfigured, because the fixture replaces the real registry. The thing that actually matters — does pending-test work route to the alias that wakes *this* install's verifier? — is invisible to them.

**How to apply (verifier independent-perspective lane):**
- When a fix resolves an identity from install config (alias registry, role-class map, env-derived name, port, path), don't stop at the green unit suite. **Resolve it once against the live config in this clone** and confirm it yields the value that makes the feature actually work here.
- Concretely for #12342: ran `harness.ExternalActivityDetector._alias_for_role_class('verifier')` against the real `config.parse_aliases_registry()` in the qa clone → `'qa'` (this install uses the legacy `qa` alias, not `verifier`). That one call is the proof pending-test will emit `target_alias='qa'` and wake me — the unit tests' `"verifier"` assertion never touches it.
- This is the config-resolution sibling of [[pattern-verify-unmocked-paths-stubbed-by-units]]: a mock substitutes a dependency to test logic in isolation; the verifier's job is to confirm the *real* dependency produces the right value. The divergence you're hunting: fixture-says-X / live-install-resolves-Y.
- Especially load-bearing where the resolved value gates whether an agent receives work at all (routing, assignment, wake targeting) — a wrong resolution is a silent starvation, green-suite and all, until the pipeline quietly stalls. (This whole class is why #12342 existed: QA starved in event mode while every unit test was green.)

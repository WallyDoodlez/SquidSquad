---
name: learning-runtime-resolves-by-alias-not-role-class
description: every runtime consumer (boot_remote clone-path lookup, harness restart, EAD work routing) resolves agents by ALIAS (e.g. qa), never by role-class (e.g. verifier) — so any code that emits agent identities for runtime consumption MUST map role-class→alias via config.parse_aliases_registry(); the legacy verifier/qa and worker/dev rename makes this bite repeatedly
metadata:
  type: learning
type: learning
tags: [learning, alias, role-class, compose, harness, runtime, 6274, 11600, 12342, 12380, self-hosting]
created: 2026-06-14
updated: 2026-06-14
owner: skill
status: active
confidence: high
source: observation
links: [learning-ead-status-routing-and-back-transition-dedup]
---

# Runtime resolves agents by ALIAS, not role-class — map at every emit site

**The recurring root cause (2026-06-14, two separate high-sev bugs in one day):** SquidSquad has 4 role-CLASSES (`pm`/`worker`/`verifier`/`dm`) and per-install ALIASES that map to them. This install (post-#6274 legacy rename) aliases the verifier class as **`qa`** and the worker class as the worker's own name (`skill`). **Every runtime consumer resolves by alias** — `boot_remote._get_clone_path`, harness `restart_agent`, `_get_all_roles`, the EAD's `target_alias` care-filter. None of them know "verifier"; they know "qa".

So any code that **emits an agent identity for a runtime consumer** must emit the ALIAS, not the role-class. Two bugs from violating this:

- **#11600/#12380** — `compose.py` wrote `.local-config` keyed by the role-class `verifier` (from `_collect_all_roles()`, which appends the mandatory role-classes). Runtime looked up alias `qa` → miss → QA booted into PM's clone (two agents, one git tree). Recurred every compose/restart.
- **#12342** — the harness EAD needed to route `pending-test` work to the verifier; routing to the role-class would have produced `target_alias="verifier"`, which no agent's care-filter matches. Correct: resolve to the alias `qa`.

**How to apply:**
- Resolve via `config.parse_aliases_registry()` → `{alias: (role_class, l3_domain)}`. To go role-class→alias, find the alias whose role-class matches (singleton installs have one each). Helpers exist on both sides: `compose._aliases_for_roles` and `harness.ExternalActivityDetector._alias_for_role_class`.
- A value that is ALREADY an alias must pass through unchanged — and watch for dedup: `_collect_all_roles()` can yield both the alias (`qa` from `workers`) and the role-class (`verifier`), which collapse to the same alias (DS-REVIEW-12380 Finding 1).
- Multi-alias-per-role-class (multi-instance workers) means role-class→alias is NOT 1:1 — first-seen wins; warn only when actually resolving an ambiguous class, not on every registry scan.
- When you see "verifier"/"worker" (role-class words) flowing toward a clone path, a `.local-config` key, an event `target_alias`, or a harness lookup — that is the smell. Runtime speaks aliases. See [[learning-ead-status-routing-and-back-transition-dedup]] for the EAD-side instance.

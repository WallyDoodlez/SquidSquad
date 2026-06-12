---
type: pattern
title: Per-item chain-ship authorization (not blanket auto-auth)
created: 2026-06-09
roles: [pm, dm]
---

# Per-item chain-ship authorization (not blanket auto-auth)

## Context

When a long-lived "bundle" branch accumulates multiple chain-shipped items before a final cutover-PR lands the bundle on main, DM must transition each item from `pending-test → pending-ship → shipped` even though the work has already merged into the bundle, not main.

The naive policy is to grant **blanket** chain-ship authorization once for the entire bundle: "anything that merges into the bundle branch ships." This is brittle — it implicitly authorizes follow-up items that may not actually belong to the bundle's scope (scope-creep items, unrelated bug fixes, accidental commits during merge spirals).

## Rule

**Chain-ship to a bundle branch is per-item, explicitly PM-authorized — NOT blanket auto-auth.**

Each chain-ship needs an explicit PM-lead comment on the issue confirming:
1. Same disposition as prior chain-ships on the same bundle.
2. Qualifying-lane check passes (see below).
3. Counter increment + CHANGELOG/version-bump disposition (typically deferred to cutover).

## Qualifying-lane criteria

Both must hold:
- **Bundle-session-originating**: the work originated during the bundle's own session — discovered by QA improvement-scan on bundle work, surfaced by skill broader smoke on bundle commits, or filed against bundle-state defects. Not unrelated work that happened to be open in the same window.
- **Bundle-scope**: the fix lives on the bundle branch and either (a) blocks the cutover-PR if unresolved or (b) is a natural extension of the bundle's scope.

**Scope expansion is a positive signal, not a disqualifier.** When a small filed finding turns out to have a larger root cause (e.g. regex-walker repair that resolves N false orphans instead of N=1), the higher-quality fix is *within* the lane — chain-ship the bigger fix, don't shrink it back.

## Path A vs Path B (release timing)

When the bundle's last blocker clears and the bundle becomes cutover-ready, DM may ask whether the final-item ship transition should also carry the release semantics (version bump + CHANGELOG). Two choreographies:

- **Path A** — chain-ship the final item to the bundle as usual; release semantics handled by a separate operator-prompted cutover-PR (bundle → main). Preserves operator authority over release timing. **Default.**
- **Path B** — combine: the final ship transition opens the cutover-PR directly and inline-triggers the release. **Reject.** Path B conflates routine ship transitions with release events, breaks the operator-prompted gate, and sets a precedent that any pending-ship transition can trigger a release.

Always Path A unless operator explicitly directs Path B.

## Anti-patterns

- Granting blanket chain-ship auth for the entire bundle ("everything that merges in ships").
- Treating scope-expanded fixes as out-of-scope and shrinking them back to the original finding.
- Path B (inline-trigger release inside a ship transition).
- Skipping the qualifying-lane check because "it's obviously bundle-related."

## Related

- [[feedback-pm-docs-only]] — PM authorizes via tracker comments, never touches code/branches.
- Established 2026-06-09 across #11334/#11382/#11381/#11383 chain on `squidsquad/skill/compose-polish-session` (DM cycles 1872/1876/1877/1879; PM cycles 2161/2162/2164).

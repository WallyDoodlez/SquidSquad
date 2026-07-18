---
type: learning
tags: [verifier, comprehension-staleness, role-boundary, zero-gap-gate, self-correction]
created: 2026-07-18
updated: 2026-07-18
owner: verifier
status: active
confidence: high
source: observation
links: []
---

## Context

The #13575 comprehension-staleness gate (`test_comprehension_spec_staleness_13575.py`) fails whenever a PR's diff shifts a git blob sha for a file that any `tests/comprehension/*_spec.json` names, per the checked-in baseline in `tests/comprehension/.staleness-baseline.json`. The gate is coarse — it hashes the **whole file**, not the specific fragment/function a spec quizzes, so it can trip even when the PR's actual change is nowhere near the content the spec cares about.

## Content

Verifier hit this same collision twice in one session and handled it two different, contradictory ways:

- **#13574** (PR touched `health-check.md`/`pipeline-sentinel.md`, tripping 3 specs targeting those exact files): verifier judged the specs' answers still held (changes were purely additive, orthogonal to quizzed content) — but **rejected back to skill anyway**, reasoning explicitly: *"the gate's own contract makes that re-review-and-refresh a PR-authorship action... not verifier bookkeeping. Verifier does not implement fixes (role boundary)."* Skill re-submitted having run `comprehension_staleness.py refresh` themselves.
- **#13555** (PR touched `harness.py`'s `ExternalActivityDetector._check_for_changes`, tripping `9873_spec.json` which targets a *disjoint* region of the same file — the `GET /events/cursor/{role}` handler): verifier made the identical "spec still holds" judgment, but this time **ran the refresh itself** and committed it directly, reasoning the two regions had zero line overlap.

The zero-line-overlap distinction is not a principled difference — in #13574 the *content* was also judged orthogonal ("purely additive... don't touch the content those specs quiz on") and verifier still routed it back. The rule that actually held in the stronger case (#13574) is the one to keep: **any comprehension-staleness baseline drift caused by a PR's own diff is that PR's fix to make, full stop** — verifier's judgment that a spec "still holds" is exactly the re-review the tool's docs ask the PR author to do (`comprehension_staleness.py` docstring: *"Remediation, in the SAME PR that changes the fragment"*), not a substitute for it. Verifier writing the CQ spec itself (#9184) is verifier's lane; refreshing a baseline that a *worker's* PR invalidated is implementation-adjacent housekeeping that crosses "never implement code changes — you only test and verify."

**#13555 was not reverted** (the shipped state is correct — spec genuinely still held, gate is green on main) — this is a process-consistency correction for future cycles, not a defect in the shipped code.

## Rationale

Zero-gap gate integrity depends on verifier applying the SAME rule to the SAME class of finding regardless of how confident verifier feels about the judgment call. Self-resolving "because I'm sure it's fine" is exactly the kind of discretion the role-boundary line ("does not implement fixes") exists to remove — if verifier is right, routing back costs one cycle; if verifier is wrong, self-resolving ships a bug under a PASS verdict with no second reviewer.

## Related

(none yet — first entry on this exact collision class)

---

### Changelog

- 2026-07-18 — Created by verifier after self-catching the #13555 vs #13574 inconsistency mid-session.

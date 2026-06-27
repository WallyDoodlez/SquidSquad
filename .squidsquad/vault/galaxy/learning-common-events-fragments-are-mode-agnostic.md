---
name: learning-common-events-fragments-are-mode-agnostic
description: editing references/sub-skills/common-events/*.md is guarded by test_event_mode_fragments — the AC5 forbidden-token sweep BANS loop-mode tokens (cycle_post, cycle_pre, /loop, 30-minute, "event-driven:", "if /loop") and wikilinks must resolve to common-events/ or roles/*/events/ ONLY (NOT common/, so [[self-restart]] fails); describe stop/restart mode-agnostically (intent flip → halt → 60s force-kill net), never by naming the loop-mode wrapper
metadata:
  type: learning
type: learning
tags: [learning, sub-skills, common-events, event-mode, AC5, forbidden-token, wikilink, 13136, 12912, testing]
created: 2026-06-21
updated: 2026-06-21
owner: skill
status: active
confidence: high
source: observation
links: [learning-requirements-txt-is-harness-runtime-scoped]
---

# common-events fragments are mode-agnostic — two test guards bite

**Observed (#13136 — clarifying the Case E stop-path in `event-mode-contract.md`).** The `references/sub-skills/common-events/*.md` fragments are **runtime-loaded by boot-bootstrap** and are deliberately **mode-agnostic** (event-mode is canonical; loop-mode is the fallback). `tests/test_event_mode_fragments.py` enforces this and bit me twice when I added loop-mode detail:

1. **AC5 forbidden-token sweep** (`TestAc5NoModeConditional`) — these fragments must NOT contain loop-mode tokens: `cycle_post`, `cycle_pre`, `/loop`, `30-minute`, `event-driven:`, `if /loop`. I introduced `cycle_post.py` to explain stop causality → two fragments failed. **Describe stop/restart mode-agnostically**: the harness flips `intent` to `stopping`/`restarting`; you checkpoint + halt; the 60s force-kill net terminates you. The loop-mode wrapper detail (cycle_post detect/exit-42/POST /restart) lives in `common/self-restart.md`, which is NOT under this guard.
2. **Wikilink resolution** (`TestWikilinkResolution`) — `[[name]]` in a common-events fragment must resolve to a `.md` in `common-events/` **or** `roles/*/events/` ONLY. `[[self-restart]]` fails because `self-restart.md` is in `common/`. Refer to common/ sub-skills as plain prose, not wikilinks.

**Bonus brittle test (`test_harness_deploy_12912.py::TestLoopModeDoesNotConsume`)** — it does `event-mode-contract.md`.find("deploy-signal") then asserts the loop-mode exemption ("never consume" / "next session start") appears within the next **4000 chars**. Mentioning `deploy-signal` *earlier* than the actual Case E bullet (e.g. in a comparison) shifts that anchor and pushes the exemption out of the window → failure. Avoid the literal string `deploy-signal` outside its own bullet (say "the deploy-halt path").

**Meta-rule**: after editing any LLM-consumed source, run the FULL `run_tests.py static` and read the **full** failure list — don't `| tail` it. A `tail` hid the real (non-grandfathered) failures here; the gate's "PASS/FAIL" wording vs exit code can also mislead (grandfathered known-failures print "FAIL" but exit 0). See [[feedback_full_static_gate_not_subset]].

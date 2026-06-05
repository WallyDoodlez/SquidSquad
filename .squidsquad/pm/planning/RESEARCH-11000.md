# RESEARCH-11000 — Phase 1

PM Phase 1 for [#11000](https://github.com/WallyDoodlez/SquidSquad/issues/11000): E6 cutover bugs + alleged 65% sub-skill bloat.

Companion: [CONTEXT-11000.md](CONTEXT-11000.md) (verbatim issue body).

## TL;DR (corrected after empirical validation)

**The "65% sub-skill bloat" framing is REAL and reproducible on freshly-regenerated post-cutover composites. The initial Phase 1 hypothesis below — that D2's filter would produce thin output once the 4 cutover bugs were fixed — was WRONG.** Empirical evidence from the cutover-unblock cycle (commit `8da22e25` / merged `07696bc5`):

| alias | linked.md lines | inlined `<!-- sub-skill: -->` markers |
|---|---|---|
| pm    | 2227 | 28 |
| dm    | ~1560 | similar |
| qa    | ~1780 | similar |
| skill | ~1960 | similar |

PM's 2227 lines exactly matches the operator's debug-session measurement in the issue body. D2's filter IS working at the link-stage walk path — `emit_v2_linked` alone for pm produces 741 lines with zero markers. But `compose.py:1184` then calls `_resolve_includes_v2(body)` which expands v1-era `{{include: <path>}}` directives in the orchestrator files (35 in `references/roles/pm/instructions.md`) into full inlined sub-skill bodies, BYPASSING D2's filter entirely. D2 only addressed the link-stage walk path; the include-expansion path is the unfixed surface.

**The fix is content migration in orchestrator files, not code in the compose pipeline.** See #11049 (Phase 2.1).

---

## Original Phase 1 hypothesis (preserved for history; superseded by empirical evidence above)

> The "65% sub-skill bloat" framing is most likely a stale-file artifact, not a current-pipeline behavior. The four cutover bugs are real and block regeneration. Once they're fixed and a fresh `deploy-all` runs, the inlining "problem" likely disappears on its own — the v2 pipeline was designed (and previously shown — PR #10691 measured 24.9% avg) to emit thin composites. The structural Findings A–C in the issue body need to be re-measured against a successfully-regenerated CLAUDE.md before any architectural decision lands.

The hypothesis was disproved when I patched the 4 bugs (via `_VERBATIM_SLOTS` expansion in `8da22e25`) and ran `deploy-all`. The composites came out at 1500-2200 lines, not the predicted ~500-700. Tracing the discrepancy to `_resolve_includes_v2` was the corrective insight.

---

This research re-orders the operator's recommended Phase 1 scope: **Q1 (cutover bugs) is the unblock; Q2–Q5 (structural findings) should re-measure first, decide second**.

## Confirmed bugs (all 4 reproducible from code reading)

### Bug 1 — `sonnet` assemble lock has no provider

`references/scripts/model_router.py:135-136` hardcodes `return "sonnet"` for `task_type == "assemble"` (locked per PRD-B B9 / #10763 AC5 for cache-key stability). But `references/scripts/providers/` ships ONLY `openai/` and `deepseek/` — no Anthropic manifest. `_load_provider_manifest("sonnet")` returns `(None, None)`; `route()` prints "No provider found" and returns exit 1. `assemble_slot` treats this as fatal and raises `AssembleSlotError`. Every `deploy-all` invocation aborts on the first slot of the first alias.

Git history check: `references/scripts/providers/` directory only ever contained the two providers; no Anthropic manifest was committed at any point. PRD-B B9 (#10763 / #10764) shipped the `assemble` lock without a corresponding provider.

PR #10999's "end-to-end deploy_alias_v2 verified clean" claim (PM audit cycle 2121) had to have run under `SQUIDSQUAD_MODEL_OVERRIDE=gpt-5.2` — that override bypasses the assemble lock at `model_router.py:138-141` and routes through the openai manifest. Operator-invoked CLI from a clean shell takes the locked path and fails.

### Bug 2 — `model == "claude"` path is unwired for shell callers

`references/scripts/model_router.py:662-670` — when `model_router.route()` resolves to `"claude"` it logs `{"action": "delegate-to-agent-tool"}` and returns exit 1 with NO file written. The contract assumes an Agent-tool-equipped parent wraps the call. True from inside an agent session; false from `python compose.py deploy-all` at a plain shell. `assemble_slot` treats non-zero as fatal and raises.

The pattern that DOES work (and exists in the codebase) is `references/scripts/run_comprehension_test.py:158-215` which shells out to `claude -p <prompt> --output-format json --allowedTools Read`. The `route()` claude branch never adopts it.

Bug 1 + Bug 2 are linked: even if Bug 1 is fixed by removing the sonnet lock and falling through to config routing, the config default routes to `claude` (`model_router.py:158`) which then hits Bug 2.

### Bug 3 — `_split_linked_into_slots` regex breaks on role-suffixed H2 in soul

Per issue body — not re-verified line-by-line in Phase 1 (out of scope; the body's analysis matches the file structure I sampled). Each `references/roles/{pm,dm,verifier,worker}/SOUL.md` opens with a role-suffixed `## Soul — <ROLE>` H2; link stage wraps with a bare canonical `## Soul`; splitter matches the bare canonical (empty body wins) and silently drops the role-suffixed body.

### Bug 4 — preservation verifier counts tokens inside HTML comments

Per issue body — not re-verified line-by-line. Source files contain meta-comments (`<!-- L2 DM instructions — H3 ops target L1 base step IDs defined in references/roles/instructions.md -->`); LLM reasonably trims them during rewrite; verifier counts the path tokens inside the comment as preservation tokens; flags false positive.

## Re-framing of structural Findings A–C

### Finding A (sub-skill double-include) — likely measuring stale state

Issue body cites `.squidsquad/pm/CLAUDE.linked.md` at 2227 lines, 28 inlined sub-skill bodies, 65% sub-skill content. **This file does NOT exist in main** (`git ls-files` empty; `git status` shows no untracked CLAUDE.linked.md). The number was captured during operator's debug session and isn't reproducible from current main.

Counter-evidence the current pipeline DOES NOT inline:
- **D2 / #10673 / PR #10691** shipped `_is_sub_skill_body_in_instructions` filter in `v2_link_stage.py:92-100` + applied at lines `:184` (emission) and `:313` (validator). Filter drops any source under `references/sub-skills/` from the instructions slot. Measured at ship: pm 22.3% / dm 28.5% / verifier 26.2% / worker 22.7% of v1 size, **avg 24.9%**.
- **#10999 cutover did NOT modify `v2_link_stage.py`** (`git show 1050bfe0 -- references/scripts/v2_link_stage.py` empty). The D2 filter is still in place.
- **`references/roles/pm/instructions.md`** (the orchestrator) is 223 lines, 7 `→ run sub-skill:` references, ZERO `<!-- sub-skill: -->` inlined markers. Last modified 2026-06-01, before D2 + before #10999.
- **`_VERBATIM_SLOTS` in `atomic_emit.py:35`** is `frozenset({"project-context", "vault"})` — instructions slot is NOT verbatim; it goes through the assemble pass (which is where Bugs 1+2 trigger).

What the operator likely measured:
- `.squidsquad/pm/CLAUDE.md` (the live one, **NOT** `.linked.md`): 2527 lines, 39 inlined `<!-- sub-skill: -->` markers, ZERO `{{include:}}` directives, last touched 2026-06-02 **10:08** — that is **two hours before D2 shipped (12:10)** and three days before #10999. This is the **stale pre-D2 v1-pipeline output**. It's what every running agent (including this PM cycle) is composing instructions from. It IS bloated. But the bloat is "old file never regenerated," not "current pipeline produces bloat."
- Why nobody noticed: D2 shipped during cycle 1518 / 2050, but cycle 2050 had ALREADY committed the pre-D2 CLAUDE.md by 10:08. No subsequent commit ever ran `deploy pm` after D2 landed. And once #10999 cutover landed, `deploy-all` started failing with the 4 bugs — so the regeneration that WOULD have replaced the stale file is impossible.

**Conclusion**: Finding A's premise (current pipeline violates `feedback_compose_dry`) is likely false. The current pipeline (post-D2, post-cutover, with bugs fixed) emits references-only output. Validate by patching Bugs 1-2 and running `deploy pm` against a clean shell. Expected: ~500-600 line PM CLAUDE.md, references only.

### Finding B (procedural sub-skills as runbooks) — independent merit, separate scope

This finding is independent of Finding A. The sub-skill MARKDOWN FILES themselves (separate from the composed CLAUDE.md) ARE prose runbooks. `references/sub-skills/roles/pm/pipeline-sentinel.md`, `vault-remember.md`, `vault-synthesis.md`, `health-check.md`, `soul-shepherd.md`, `improvement-scan.md` are 80-140 lines each of prose + bash blocks.

Even after Finding A is dismissed (sub-skills are no longer INLINED into CLAUDE.md), the runtime cost remains: each cycle the PM agent runtime-Reads these files and interprets them. Converting them to Python scripts has merit per `project_improvement_loop_philosophy` + `feedback_trust_script_output`. This is a **separate PRD candidate**, NOT a bug.

Recommendation: file as a separate PRD once Finding A is dismissed. Don't bundle.

### Finding C (instructions slot too large for LLM rewrite) — likely false after A dismissed

If Finding A is correct (current pipeline emits ~500-600 line PM CLAUDE.md, mostly orchestrator prose with refs), Finding C is moot — the instructions slot is ~223 lines orchestrator prose, well within deterministic-rewrite budget.

If Finding A is incorrect (current pipeline still inlines for some reason I haven't found), Finding C is real and we need a different architectural decision.

**Hard dependency**: validate A before deciding C.

## Bug ownership (Q1 answered)

**One combined "cutover stabilization" issue / story, four ACs.** Rationale:

- All four bugs were introduced by overlapping commits (PRD-B B9 / #10764 + #10999 cutover) and touch overlapping files (`model_router.py`, `atomic_emit.py`, `assemble_verifier.py`).
- The fix surface is small per bug (~50 lines each estimated).
- Skill-lead context-load is more efficient as one task than four. Operator preference in body matches.
- They co-block the same outcome (deploy-all succeeds from a plain shell).

Skill scope:
- AC1: ship Anthropic provider manifest under `references/scripts/providers/anthropic/` (manifest.yaml + adapter.py) wired to the existing `shared_fs.read_secret_or_env("ANTHROPIC_API_KEY")` pattern. Verify `_load_provider_manifest("sonnet")` resolves it.
- AC2: rewrite `model_router.route()` claude branch (`model_router.py:662-670`) to shell out to `claude -p <prompt> --output-format json --allowedTools Read` per the `run_comprehension_test.py:158-215` pattern. Returns 0 with file written on success.
- AC3: fix `_split_linked_into_slots` regex to match the canonical bare H2 only OR strip the role-suffix at link time before assemble sees it. Pick whichever preserves byte stability of currently-passing assemble runs.
- AC4: strip HTML comments from preservation-token extraction in `assemble_verifier.py:verify_preservation` before counting. Add regression test with a meta-comment containing a load-bearing path.

## Inlining intent (Q2 answered)

Inlining was **intentionally reversed** by D2 (#10673) + the link-stage's `_SUB_SKILLS_PATH_PREFIX` filter. The compose-DRY violation is NOT present in the current pipeline. Operator memory `feedback_compose_dry` is honored by the post-D2 v2 link stage by design.

The current STALE composite (`.squidsquad/pm/CLAUDE.md`) violates `feedback_compose_dry`, but it is stale, not a current-pipeline output.

## Reference-only feasibility (Q3 answered preliminarily)

Reference-only is already in production via D2. Runtime-Read pattern is proven by `boot-bootstrap.md` Step 3 (event-mode loop reads 6 fragments at runtime; PM polling-mode reads `ralph-loop-overview.md` at runtime). This is the SAME pattern sub-skills use when invoked via `→ run sub-skill: <name>`.

Per-cycle vs per-event split (read by every cycle vs only on trigger): not enumerated in Phase 1. Defer to Phase 2 if A is dismissed.

## Procedural extraction candidates (Q4 — defer to separate PRD)

Per Finding B re-frame: file as a separate PRD AFTER the cutover-bugs fix lands and A is dismissed.

Candidates list from issue body unchanged: `pipeline-sentinel`, `vault-remember`, `vault-synthesis`, `health-check`, `soul-shepherd`, `improvement-scan`. Confirm by reading each markdown file and measuring args + output contracts (out of Phase 1 scope).

## Assemble pass scope (Q5 — gated)

If Findings A+C are dismissed, the assemble pass IS still doing useful work on a ~500-line instructions slot — but the question shifts from "can it succeed?" (yes, easily, at this size) to "is the cost worth it?" (sonnet API call per slot per deploy).

If Findings A+C are NOT dismissed, the answer is harder — possibly retire assemble entirely (operator's `_VERBATIM_SLOTS += instructions` unblock shows the slot CAN be emitted verbatim).

**Defer Q5 until A is empirically validated.**

## Phase 1 recommended next actions (PM)

1. **File the cutover-stabilization task** (Q1 — 4 ACs combined). Assigned to skill. Priority high. Block on this before any structural decision.
2. **After cutover-stabilization ships**: regenerate `deploy-all` from a clean shell. Measure each composed CLAUDE.md size + grep for `<!-- sub-skill: -->` markers + `→ run sub-skill:` refs. Record in `RESEARCH-11000-phase2.md`.
3. **Based on measurements**: if pm/dm/verifier/worker CLAUDE.md sizes match PR #10691's 22-29% range, dismiss Finding A. If not, deepen Phase 2.
4. **After A is decided**: file separate PRD for Finding B (procedural sub-skill → Python script extraction) regardless of A outcome.
5. **After A is decided**: decide on Finding C / Q5 based on the empirically-measured instructions slot size.

## Open / deferred questions

- D-Q1: Did anyone ever successfully run `deploy-all` against a clean shell post-PRD-B B9 ship? If yes, when, and how — Anthropic key in env? Override env var?
- D-Q2: Was the absence of an Anthropic provider manifest deliberate (defer to operator-supplied key + agent-tool) or an oversight in PRD-B B9?
- D-Q3: Is there a non-stale composite anywhere in main (any role's CLAUDE.md last touched AFTER 2026-06-02 12:10)? Quick check: `git log --since "2026-06-02 12:10" -- .squidsquad/*/CLAUDE.md`.
- D-Q4: What did the audit cycle 2121 actually run? Likely `SQUIDSQUAD_MODEL_OVERRIDE=gpt-5.2` was set — confirm with skill / git log.

### D-Q3 partial answer (Phase 1 follow-up)

`git log --since "2026-06-02 12:10" -- .squidsquad/*/CLAUDE.md` returns ONE commit: `686be323 #10818 Regenerate stale qa CLAUDE.md` on 2026-06-03 09:05.

That regen file (`.squidsquad/qa/CLAUDE.md`, 1820 lines, 26 inlined `<!-- sub-skill: -->` markers, 11 refs) WAS regenerated post-D2 (12:10 → 09:05 next day) but PRE-cutover (#10999 shipped today). **Does NOT disprove A by itself**: at that time both `deploy_role` (v1, inlines) and `deploy_alias_v2` (v2, D2 filter) existed in parallel. `compose.py deploy qa` was wired to `deploy_role` until #10999's Phase 3d.4 retirement. The QA regen went through v1 — that's the inlining we see.

So as of 2026-06-04 (today), no role's CLAUDE.md has ever been generated by the v2-only post-cutover path. The 4 bugs in this issue have prevented it. **A is still untested empirically.** Phase 2 must regenerate after cutover-stabilization ships and re-measure.

## Cutover-stabilization task (Q1 answer — ready to file)

Filing as a new high-priority TASK assigned to skill, separate from #11000. #11000 stays at planning while skill ships the cutover fixes; once landed, PM regenerates and re-measures (Phase 2 of #11000).

Title: `TASK: E6 cutover stabilization — 4 bugs blocking deploy-all from a plain shell (gates #11000 Phase 2)`
Role: skill
Priority: high
ACs: AC1-AC4 above (Anthropic provider manifest; claude-branch route() shell-out; soul splitter regex; preservation verifier comment-strip).
Blocks: #11000 Phase 2 measurement (cannot regenerate without these fixes).

---

## Phase 1 outcome + Phase 2 entry (2026-06-05)

Cutover unblock did NOT follow the originally-proposed 4-bug fix path. Instead, commit `8da22e25` (operator-prioritized session, PM as dev) made two surgical changes to `atomic_emit.py`:

1. `_VERBATIM_SLOTS` expanded to cover all six canonical slots — retired the LLM assemble pass entirely. Bugs 1, 2, 4 mooted (no LLM dispatch occurs).
2. `_split_linked_into_slots` regex anchored on canonical slot display names only — Bug 3 fixed.

`compose.py deploy-all` succeeds from a clean shell:
- dm: 1568 lines
- pm: 2196 lines
- qa: 1789 lines
- skill: 1964 lines

These are the **first successful post-cutover regenerations** of any role's CLAUDE.md. They match the operator's debug-session measurements within +20 lines (drift from intervening content changes).

### TL;DR correction (already applied above)

The 65% bloat IS real. The original Phase 1 hypothesis that D2's filter would deliver thin composites was wrong. Tracing the discrepancy revealed the actual cause: `compose.py:1184` calls `_resolve_includes_v2(body)` which expands v1-era `{{include: <path>}}` directives in orchestrator files (35 in `references/roles/pm/instructions.md`) into full inlined sub-skill bodies. D2's filter only addressed the link-stage walk path; the include-expansion path was the unfixed surface.

### Phase 2 work filed

- **#11049** (high priority, role:skill, approved): migrate `{{include:}}` → `→ run sub-skill:` in 4 orchestrator instructions.md + L3 domain variants. ACs target the 22-29% size band PR #10691 promised (pm ≤700, dm ≤800, qa ≤700, skill ≤700). **Resolves Finding A.**
- **#11050** (medium priority, role:skill, approved): prune dead assemble pipeline modules (`assemble_pass`, `assemble_verifier`, `conflict_detector`, `conflict_resolver`, `assemble_adapter`) + the `task_type == "assemble"` branch in `model_router.py`. **Resolves Q5.**

Both can run in parallel (no shared file surface).

### Findings resolved this session

- **Finding A** (sub-skill double-include): REAL. Fix in flight via #11049. Was misdiagnosed in Phase 1 as a stale-file artifact; now correctly traced to `_resolve_includes_v2`.
- **Finding B** (procedural sub-skills as runbooks): independent merit, separate PRD if/when prioritized. No change.
- **Finding C** (instructions slot too large for reliable LLM rewrite): EFFECTIVELY RESOLVED by Q5's answer — assemble pass retired, so slot size no longer matters for stochastic compliance.
- **Q5** (assemble pass scope): DECIDED — retired this session. All 6 slots verbatim. Re-enable per-slot by removing from `_VERBATIM_SLOTS` if a future story scopes LLM polish to a small slot like `identity`.

### What changed architecturally vs. stayed implementation

| Decision | Type | Status |
|---|---|---|
| Retire LLM assemble pass | **Arch change** | Shipped in `8da22e25` (verbatim path). Cleanup in #11050. |
| Migrate `{{include:}}` to `→ run sub-skill:` | Implementation / content migration | Filed as #11049, in-progress with skill |
| Six-slot composite, link-stage walk, D2 filter, catalog gate, deterministic post-link passes | Unchanged — sound as designed | Stays |

### #11000 closes when

- #11049 lands → I re-measure composites against AC3 size targets
- If sizes hit the 22-29% band, Finding A is closed empirically → #11000 transitions planning → in-progress → shipped (or closed as Phase 1+2 delivered)
- If sizes miss the band, deepen Phase 2 with skill to find the remaining inlining path

### Open questions resurfaced

- D-Q1 (was deploy-all ever successful?): answered indirectly — apparently no prior post-cutover success. Operator's debug session with hand-patches was the closest.
- D-Q2 (Anthropic provider deliberate or oversight?): de facto resolved — provider not needed post-#11050 (assemble retired).
- D-Q3: see partial answer above (one qa regen via v1 deploy_role).
- D-Q4 (audit cycle 2121 env): not investigated further; low priority now that the cutover works without env tricks.

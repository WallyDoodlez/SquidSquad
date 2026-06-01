# QA-RESULTS-10650 — PRD-C / Story C1: l4-curation.md sub-skill

**Verified**: 2026-06-01 15:08
**Branch**: `squidsquad/task/10650` @ `4c05ff9e`
**PR**: #10660
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

Feature commit `4c05ff9e` adds 79 lines to `references/sub-skills/common/l4-curation.md` — specifically the AC6 §7.3 worked-example section. The remaining sub-skill content was pre-existing per skill's comment. Total file: 227 lines, 8 sections.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | Frontmatter `slot: instructions` + ordinal matching reference shape | File has `slot: instructions, ordinal: 10` — identical frontmatter to the AC's cited reference (`references/sub-skills/common/git-commit.md` has `slot: instructions, ordinal: 10`, no `roles:` field either). Reference shape matched. | PASS |
| 2 | Detection patterns (§7.1) — durable vs one-off, customization vs feature, role-class scope. 3+ worked examples per type. | `#### Activation — customization request detected` section: 6 durable-pattern examples + 4 prohibition-pattern examples; comparison table with 4 signals (Time horizon, Subject, Scope, L1-L3 coverage) explicitly distinguishes durable from one-off. Universal-vs-role-specific prohibition note covers role-class scope. | PASS |
| 3 | Elicitation dialog — questions agent asks before drafting | `#### The elicitation dialog` section: 8-step numbered dialog. Steps 1-4 + 7 user-facing, steps 5/6/8 agent-internal. Covers durability confirmation, role/slot identification, why-capture, edge-case capture, op selection, file selection, draft-readback approval, safety gates. | PASS |
| 4 | Decision tree (§7.2) — five-step classification logic for op + slot, refuses forbidden slots | Step 5 (Pick the op + target) is the classification: per-slot rules listed for Identity/Soul/Project Context (append-only), Vault (forbidden — aborts and routes as feature request), Instructions (all 4 step-targeted ops legal with intent-mapped selection). 5 outcomes total. | PASS |
| 5 | Safety gates overview (§7.4) — three-gate flow at contract level | Step 8 (Run the safety gates) names the 3 gates: DeepSeek decision-tree audit, mini-CQ, dry-run. Contract level only (per spec, invocation code lives in C3/C4/C5). | PASS |
| 6 | File format authoring (§7.3) — H2 slot header + H3 op header + HTML-comment metadata trailer | `#### File format — the H3 op block (§7.3)` section (the new AC6 work this commit). Names the 3 load-bearing parts: H3 op heading (5 legal shapes listed), body (with bolded title convention), HTML-comment metadata trailer (specifies required fields). Includes complete pm.md worked example covering 4 H3 blocks across Identity/Instructions/Project Context (deliberately omits ## Vault to demonstrate the forbidden-slot rule). | PASS |
| 7 | One-shot + durable framing (§7.7) — sub-skill invoked once per directive, not recurring | 6 mentions of "one-shot" / "recurring" / "invoke...once" / "durable" throughout the prose. Activation section explicitly distinguishes durable customization from one-off task. Step 1 dialog opens with "Want me to lock that in as a per-project rule, or is it just for this task?" — captures the one-shot framing in user-facing language. | PASS |
| 8 | Sub-skill placement `common/` | File path: `references/sub-skills/common/l4-curation.md` ✓ | PASS |

## Regression / Coexistence

`pytest tests/test_v1_byte_stability_9a.py -q` on `4c05ff9e` → **5 passed in 0.79s** (all 4 role-classes byte-identical + meta coverage test). §9a gate green; v1 compose unaffected by adding the sub-skill (sub-skill is opt-in via composed inclusion, not v1 base).

## Notable Authoring Quality

- "Talking to the user" prohibition: never name SquidSquad concepts in user-facing prose. Use functional descriptions. This is a strong UX hygiene principle for any per-project customization dialog.
- Universal-vs-role-specific prohibition distinction routed cleanly: universal → Identity slot append-only, role-specific → role's L4 file. Step-specific prohibitions correctly routed UPSTREAM (feature request) since they belong in L1-L3.
- Vault slot abort + route-to-feature-request is documented; matches A2e R1 enforcement.

## Test Execution

- `pytest tests/test_v1_byte_stability_9a.py -q` → **5 passed in 0.79s**.
- Live file walk: file exists, frontmatter parses, 8 named sections present per AC mapping.

## Outcome

All 8 ACs covered. Authoring quality is high — the user-facing/agent-internal split, prohibition handling, and slot-routing prose are all carefully thought through. **Transitioning #10650: pending-test → pending-ship.**

Now I have all the context needed for a thorough review. Here are my findings:

---

### Finding 1

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8697.md`
- **Line**: 32
- **Severity**: error
- **Issue**: AC-4-M contains a logically contradictory allowed-diff clause. It defines a byte-identical comparison between (a) pre-#8697 deployed CLAUDE.md and (b) new compose output with `event-driven: no`, then lists "reintroduction of the event-driven-workflow block — but ONLY if the role is flipped to `yes`" as an allowable diff. This makes no sense: if the role is flipped to `yes`, the compose runs in events mode, not loop mode, so the comparison target isn't the `event-driven: no` output. Conversely, a loop-mode compose (`event-driven: no`) must never reintroduce the event-driven-workflow block.
- **Evidence**: Line 32 reads: "Allowable diffs: ordering changes that the manifest explicitly carries forward, and reintroduction of the event-driven-workflow block — but ONLY if the role is flipped to `yes`." The preamble on the same line says "rendered from the new compose stack with `event-driven: no`." If the role is "flipped to yes," then `event-driven` is `yes`, contradicting the stated mode. The parenthetical at line 24 confirms the intent: "Existing roles compose identically to today when `event-driven: no` (regression check against current deployed output)." The "flipped to yes" clause belongs in a *separate* AC comparing events-mode output against pre-#8697 output — not here.
- **Suggested fix**: Remove the clause "and reintroduction of the event-driven-workflow block — but ONLY if the role is flipped to `yes`" from AC-4-M. If needed, add a separate AC-4b-M for the events-mode comparison: "Byte-identical diff between pre-#8697 deployed CLAUDE.md and new events-mode compose output, with the ONLY allowable diff being the addition of the event-driven-workflow block wrapped in standard `<!-- sub-skill: ... -->` markers (sourced from a real fragment, not hand-injected)."

---

### Finding 2

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8697.md`
- **Lines**: 29–30
- **Severity**: warning
- **Issue**: The events-mode fingerprint tokens are inconsistent between AC-1-M (exclusion list for loop-mode output) and AC-2-M (inclusion list for events-mode output). AC-1-M checks for `forge-read pattern` (with "pattern") while AC-2-M checks for `forge-read` (without "pattern"). If an events-mode fragment contains just `forge-read` without the word "pattern," AC-1-M's exclusion check would not catch it as contamination in loop-mode output — creating a detection gap.
- **Evidence**: Line 29: "zero substring matches for the literal markers ... `forge-read pattern`". Line 30: "Contains at least one of ... `forge-read`". Also, in line 149, TC-I-2 lists `forge-read` (without "pattern") as an expected fingerprint. There is no explanation for why the two ACs use different tokens, and the difference means the exclusion check is strictly narrower than the inclusion check. If a fragment says "perform a forge-read" (without "pattern"), AC-2-M would find it but AC-1-M would miss it.
- **Suggested fix**: Standardize on one token. Either change AC-1-M to check for `forge-read` (covering both forms) or document that `forge-read pattern` is the canonical fragment text and verify that no events-mode fragment contains the bare `forge-read` without "pattern." Also check whether `bootup-complete` in AC-1-M matches the canonical fragment text (it may appear as `bootup-complete` or `bootup_complete`).

---

### Finding 3

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8697.md`
- **Lines**: 274–276
- **Severity**: warning
- **Issue**: TC-N-1 acknowledges that the fragment lint must be wired into `compose.py deploy` but defines no end-to-end test for it. It defers to TC-U-5 (a unit test of the lint function) and says "repeated here for completeness" — but a unit test of `_lint_fragment()` doesn't verify that `compose.py deploy` actually calls it. There is no integration-level negative test that creates a fragment with mode-conditional syntax, runs `compose.py deploy`, and asserts the deploy fails.
- **Evidence**: Line 274: "### 7.1 TC-N-1: fragment with mode-conditional logic is rejected. Already covered in TC-U-5 — repeated here for completeness. The fragment lint MUST be wired into `compose.py deploy` so the failure surfaces at deploy time, not just at unit-test time." This is a statement of requirement, not a test definition. No test steps, preconditions, or verification are provided. The negative test file (`tests/test_compose_dual_mode_negative.py`) would therefore have 6 defined tests (TC-N-2 through TC-N-7) but a hollow placeholder for TC-N-1.
- **Suggested fix**: Define a concrete TC-N-1 with steps: (1) Create tmp role with a fragment containing `event-driven: yes` as a runtime instruction inside a non-code-block context. (2) Add the fragment to `includes-events.yml`. (3) Run `compose.py deploy <role>`. (4) Assert `SystemExit` non-zero with stderr naming the offending file and line. Keep TC-U-5 as the unit-level test of the lint logic itself.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8697.md`
- **Lines**: 510–523
- **Severity**: warning
- **Issue**: The initial fragment classification pass — a named deliverable in CONTEXT.md §5.3 (line 507–509: "classify each entry as `loop`, `events`, or `both`") — is gated only at P1 post-ship validation (PV-4, §11.4), not at P0 ship time. If manifests are incomplete when #8697 ships (e.g., a fragment present in the legacy `includes.yml` is accidentally omitted from both `includes-loop.yml` and `includes-events.yml`), compose would produce silently incomplete output. The end-to-end tests (TC-I-1, TC-I-2) only check for fingerprint presence, not exhaustive fragment membership.
- **Evidence**: The test categories map (§2) has no P0 row for "classification completeness." PV-4 at §11.4 is P1 ("Post-ship validation"). The validation says "Verify in PV-4 that each existing manifest entry has been classified" and generates a human-reviewed report — but this happens *after* ship. CONTEXT.md §5.3 line 507 calls the classification pass a #8697 deliverable, which implies it must be complete for #8697 to ship. The §10 gating conditions don't mention classification completeness.
- **Suggested fix**: Either (a) add the classification report generation as a P0 automated test that verifies every entry from the original `includes.yml` appears in at least one of `includes-loop.yml` or `includes-events.yml` (coverage check, not correctness check), with the report output as an artifact, or (b) explicitly note in §10 gating that the PV-4 classification report must be generated and human-reviewed before ship (upgrade PV-4 to P0). The automated coverage check can verify the union of the two new manifests covers the superset of the old manifest's entries; correctness of which tree each entry goes to remains human review.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8697.md`
- **Lines**: 354–359
- **Severity**: info
- **Issue**: CQ question 4 asks about the missing canonical event-driven-workflow source fragment, but its expected answer implies a behavior that isn't specifically tested anywhere. The answer says compose.py "errors out with a clear message naming the missing fragment path and the role. It does NOT silently fall back to loop mode and it does NOT hand-inject content." The "does NOT silently fall back to loop mode" behavior is only tested for the legacy-shim scenario (TC-I-6, TC-N-2, TC-N-3) — not for the specific case of a missing events-mode fragment in an otherwise properly-migrated role. While TC-U-8 covers missing fragments generically, no test verifies that the presence of `includes-loop.yml` doesn't cause compose to silently fall back when `includes-events.yml` exists but references a missing fragment.
- **Evidence**: TC-U-8 (line 118) tests that a "missing fragment listed in manifest errors clearly" but doesn't test the cross-manifest fallback scenario. TC-N-2 (line 278) tests "missing `includes-events.yml`" (entire manifest absent), not "manifest exists but fragment inside it is missing." The specific regression #8697 is designed to prevent (silent fallback to loop-mode when events-mode fragment is missing) isn't tested except indirectly. CQ Q4 tests agent understanding of this behavior but the behavior itself isn't tested.
- **Suggested fix**: Add a dedicated negative test: (1) Role has both `includes-loop.yml` and `includes-events.yml`. (2) `includes-events.yml` references a fragment that doesn't exist on disk. (3) Config has `event-driven: yes`. (4) Assert compose fails with non-zero exit (does NOT silently fall back to loop manifest) and stderr names the missing fragment. Distinct from TC-U-8 which tests generic missing-fragment detection; this specifically tests that the mode selection isn't bypassed.

---

### Finding 6

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8697.md`
- **Lines**: 266, 531
- **Severity**: info
- **Issue**: The L4 split open question in §6.5 and §12.1 mischaracterizes the issue as potentially needing "PM relock." CONTEXT.md §5.3 acceptance criteria (line 544–545) already explicitly allows mode-specific L4 variants: "L4 project instruction files contain no /loop-specific language, or are explicitly split into mode-specific variants." The architecture already contemplates the split. The genuine question is narrower: should the `compose.py` code to filter L4 files by mode suffix be implemented now or deferred? This is an engineering scope decision, not a PM architecture decision.
- **Evidence**: CONTEXT.md §5.3 line 544: "L4 project instruction files contain no /loop-specific language, or are explicitly split into mode-specific variants." Test plan §6.5 line 266: "extending L4 filtering is a scope expansion versus the 'L4 is mode-agnostic' line in §2 / §4.3 of CONTEXT.md." But §4.3 (line 319–323) says L4 is "mode-agnostic" as a strategic principle, and §5.3 provides the split escape hatch. The test plan frames the split as contradicting §4.3 when it's actually consistent with §5.3. The open question at §12.1 says "Lock: is the split mechanism part of #8697, or strictly out of scope" — this is valid as an implementation scope question but doesn't need PM relock since the architecture already permits it.
- **Suggested fix**: Reframe §12.1 and §6.5. Instead of "Open question: is the L4 split mechanism in scope for #8697, or deferred to a follow-up if needed?" say: "Implementation decision: should compose.py's L4 layer include mode-suffix filtering in #8697, or should #8697 clean L4 files so no split is needed and defer the filtering code to the follow-up that first requires a split?" No PM relock needed; the architecture allows either path.

---

### Finding 7

- **File**: `.squidsquad/pm/planning/TEST-PLAN-8697.md`
- **Lines**: 112–115
- **Severity**: warning
- **Issue**: TC-U-7's L4 boundary detection mechanism is ambiguous and implementation-dependent. It defines the L4 region as "content between the last `<!-- /sub-skill: ... -->` of L1–L3 and EOF, OR the explicit L4 marker if one is added." This "OR" creates two different boundary-detection strategies whose correctness depends on whether #8697 adds a new L4 marker to compose.py's output. If a marker IS added, the test using the first strategy (last `/sub-skill` close tag) would produce a different (wrong) region than the second strategy. The test doesn't specify which strategy to use or how to detect which is applicable.
- **Evidence**: Line 112: "(L4 region = content between the last `<!-- /sub-skill: ... -->` of L1–L3 and EOF, OR the explicit L4 marker if one is added.)" The test implementation must pick one strategy, but which one is correct depends on an implementation detail (#8697 may or may not add an L4 marker). If the wrong strategy is picked, the test could produce false positives (different L4 regions when they're actually the same, just measured wrong) or false negatives (identical regions when they're actually different).
- **Suggested fix**: Either (a) mandate that #8697 adds an explicit L4 marker (e.g., `<!-- L4: project instructions -->`) and define the test exclusively in terms of that marker, or (b) define the boundary as "everything after the last `<!-- /sub-skill: ... -->` close tag" and note that this strategy assumes #8697 does NOT change the L4 boundary marker. Make this an explicit test dependency so if the implementation changes the boundary, the test is updated in the same commit.
# TEST-PLAN-12749 — DM-ARCH layered DM refactor (arch-polish + L1–L4 land together)

**Derived independently from the issue AC list** (not from the worker's PR diff). 2026-06-18.
**Branch**: `squidsquad/dm-arch` (PR #12689, MERGEABLE/CLEAN). Source on branch; `.squidsquad/` state
(config alias `dm/skill`, L4 `project/dm.md`, live `statusline.sh`, recomposed CLAUDE.md) is **main-landing** —
stripped from the feature branch, lands on main in the SAME window as the merge (operator "no fiction window").

## Verification method
Because the composed-DM ACs (1/2/3/6) and statusline AC4 depend on the main-landing state, the test instance applies
the skill's documented durable main-landing diff to the working tree (config `dm/skill` + L4 release policy + statusline
live-copy sync), runs `compose.py deploy-all`, and inspects the **composed `.squidsquad/dm/CLAUDE.md`** — the real
post-merge artifact. Verdict rests on my own inspection of composed output + live test runs, not the worker's claims.

## Test cases (one per AC)

- **TC1 (AC1)** — Compose DM; assert L2 = version-agnostic generic spine as bare-H3 `### step:cycle/<id>` anchors;
  assert NO `step:cycle/version-bump` step and NO `Shipped Since Last Bump`/bump logic in the L2 spine band.
- **TC2 (AC2)** — Assert L4 batch-10 release policy composes into the DM; then compose with L4 ABSENT and assert the
  default is ship-on-ready with ZERO bump/counter/Release-policy text.
- **TC3 (AC3)** — Assert composed DM `step:cycle/package` = merge-to-main + compose and `step:cycle/publish` =
  ship-comment + CHANGELOG (requires `dm`→`dm/skill` L3 wiring); assert `config.py alias dm` still returns `dm`
  (tracker identity not corrupted).
- **TC4 (AC4)** — Assert verifier `verification.md`/`responsibility.md` no longer increment the counter; assert
  `statusline.sh` no longer displays the ship counter; run counter/ownership tests and confirm none false-green
  (the ownership test must assert the verifier does NOT increment).
- **TC5 (AC5)** — Grep the named descriptive docs (ARCHITECTURE / AGENT-RUNTIME / COMPOSE / README index) + role
  sources; assert zero stale "version bumps as universal DM" framing (`verifier increments` / `PM coordinates bump`
  must be absent; surviving refs must be correct DM attributions or L4-qualified).
- **TC6 (AC6)** — `compose.py deploy-all` green; fresh DM comprehension agent (file-only context) answers
  "when do you bump?" → "only because L4 policy says so" (NOT a universal rule). Spec: `tests/comprehension/12749_spec.json`.
- **TC7 (AC7)** — Confirm DS-review covered every change; corroborate the reported findings' fixes against committed code.
- **TC8 (AC8)** — Assert no installer-SHIPPED file added/removed; `references/installer-files.txt` correctly unchanged.

## Pass condition
Zero-gap gate. All 8 TCs PASS with observable evidence → pending-ship. Verdict is **contingent on the main-landing
batch landing on main in the same window as the #12689 merge** — otherwise the docs/spine describe a DM that isn't live.

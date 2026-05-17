# TEST-PLAN-8697 — `compose.py` Dual-Mode (separate L1–L3 sets per wake mode, shared L4)

**Issue**: #8697 (absorbs #8699)
**Bundle**: Phase 5 event-driven architecture (#8694 lead / #8695 / #8697 / #8700 / #8701 / #8704)
**Hard prereq**: #8692 (singleton enforcement) for any per-role flip; #8697 itself has no hard code prereq
**Date**: 2026-05-17
**Author**: pm-lead (planning subagent)

## Revision Log

- **2026-05-17** — Revised per deepseek R1 review (1 error + 4 warnings + 2 info) + 4 PM-locked gap resolutions.
  - F1 (error, AC-4-M contradictory clause): removed the "reintroduction of the event-driven-workflow block — but ONLY if the role is flipped to `yes`" clause; added a separate AC-4b-M for the events-mode comparison.
  - F2 (warning, fingerprint token inconsistency `forge-read` vs `forge-read pattern`): standardised on the bare token `forge-read` in both AC-1-M and AC-2-M.
  - F3 (warning, hollow TC-N-1): TC-N-1 redefined with concrete steps + preconditions for the end-to-end lint check at deploy time.
  - F4 (warning, classification completeness only at P1): added P0 automated coverage check that the union of `includes-loop.yml` and `includes-events.yml` covers the legacy `includes.yml` superset; PV-4 stays at P1 for correctness review.
  - F5 (error, cross-manifest fallback regression untested): added TC-N-8 — `includes-events.yml` references a missing fragment under `event-driven: yes`; compose MUST fail loudly, never silently fall back to loop.
  - F6 (info, L4 split open question framing): reframed §6.5 and §12.1 — L4 split is an implementation scope decision, not a PM relock (already permitted by CONTEXT §5.3).
  - F7 (info, L4 boundary detection ambiguity): mandated that #8697 adds an explicit L4 marker (`<!-- L4: project instructions -->`) and TC-U-7 detection is defined exclusively in terms of that marker.
**References**:
- `.squidsquad/pm/planning/CONTEXT.md` §4 (Mode Separation Strategy), §5.3 (#8697 spec), §6.3 (pre-flip checklist), §11 (glossary)
- `.squidsquad/pm/planning/RESEARCH-compose-boot.md` (compose architecture, includes.yml schema, hand-injected block survey)
- `references/scripts/compose.py` (lines 120–206 manifest load; 209–277 include resolution; 280–341 layer assembly; 318–340 L4; 804+ `deploy_role`)
- `.squidsquad/pm,qa,skill,dm/CLAUDE.md` (current deployed output — note: the event-driven-workflow hand-injected block has already been wiped by a recent compose, which IS the regression #8697 must fix)

---

## 1. Acceptance Criteria

Verbatim from CONTEXT.md §5.3 plus measurable refinements (suffixed `-M`):

**From §5.3 Acceptance** (locked):
- **AC-1**: `compose.py deploy <role>` with `event-driven: no` produces a CLAUDE.md containing only loop-mode fragments.
- **AC-2**: `compose.py deploy <role>` with `event-driven: yes` produces a CLAUDE.md containing only events-mode fragments — no /loop language, no cycle-runner.
- **AC-3**: No fragment file contains the string `event-driven:` as a runtime branch instruction. (Mode lives in the manifest, not the fragment.)
- **AC-4**: Existing roles compose identically to today when `event-driven: no` (regression check against current deployed output).
- **AC-5**: `event-driven-workflow` block is composed from a real source fragment, not hand-injected. #8699 closes here.
- **AC-6**: L4 project instruction files contain no /loop-specific language, or are explicitly split into mode-specific variants.

**Measurable refinements**:
- **AC-1-M**: Compose output for `event-driven: no` contains zero substring matches for the literal markers `<!-- sub-skill: event-driven-workflow -->`, `event_poll.py`, `Last Processed Event ID`, `bootup-complete`, `forge-read`. Contains at least one of `cycle_pre.py`, `/loop`, `cycle-runner`. *(Token `forge-read` used uniformly with AC-2-M per review F2 — covers both bare `forge-read` and `forge-read pattern` forms.)*
- **AC-2-M**: Compose output for `event-driven: yes` contains zero substring matches for `/loop 30m`, `cycle_pre.py`, `cycle_post.py`, `cycle-runner`. Contains at least one of `event_poll.py`, `Last Processed Event ID`, `forge-read`, `bootup-complete`.
- **AC-3-M**: Recursive grep over every file under `references/sub-skills/common-loop/`, `references/sub-skills/common-events/`, and `references/sub-skills/roles/<role>/{loop,events}/` for the regex `event-driven:\s*(yes|no)` returns zero matches in fragment bodies. (Manifests are the only place the gate value appears.)
- **AC-4-M** (loop-mode regression): Byte-identical diff (after newline-normalization) between the current deployed `.squidsquad/<role>/CLAUDE.md` (PRE-#8697) and the new compose output **rendered with `event-driven: no`**. Allowable diffs: ordering changes that the manifest explicitly carries forward. *(Review F1: the prior "reintroduction of the event-driven-workflow block ONLY if flipped to yes" clause was logically contradictory and has been removed. The events-mode comparison lives in AC-4b-M below.)*
- **AC-4b-M** (events-mode comparison vs pre-#8697): Diff between the current deployed `.squidsquad/<role>/CLAUDE.md` (PRE-#8697) and the new compose output **rendered with `event-driven: yes`**. The ONLY allowable diff is the addition of the event-driven-workflow content sourced from a real fragment and wrapped in standard `<!-- sub-skill: ... -->` markers (no hand-injected residue), plus the full L1–L3 swap to events-mode fragments. Loop-mode artefacts (`cycle_pre.py`, `cycle_post.py`, `cycle-runner`, `/loop 30m`) must be absent.
- **AC-5-M**: `git log --diff-filter=A` shows new file(s) under `references/sub-skills/common-events/` containing the migrated event-driven-workflow content; `git grep` for any unique token of that content (e.g., `Last Processed Event ID`) returns at least one source file under `references/`.
- **AC-6-M**: Recursive grep over `.squidsquad/project/*.md` for the regex `/loop\b|cycle_pre|cycle_post|between cycles|next cycle|cycle counter|iter-\d+\.md` returns zero matches OR every match resides in a file whose name carries an explicit mode suffix (e.g., `pm-loop-instructions.md` / `pm-events-instructions.md`). The audit decision per hit is logged in `.squidsquad/pm/planning/L4-AUDIT-8697.md` (one row per hit: file, line, action = remove / generalize / split).

**Backward-compat shim AC**:
- **AC-7**: A role with only legacy `includes.yml` (no `-loop`/`-events` variant) still composes successfully under `event-driven: no`, emitting a one-line deprecation warning on stderr. This shim is documented as Phase 6 removal in #8698.

**Classification coverage AC (P0, review F4)**:
- **AC-8**: For each of the four roles (pm, qa, skill, dm), the **union of entries** in the new `includes-loop.yml` and `includes-events.yml` must cover the **superset of entries** in the legacy `includes.yml` (no fragment dropped silently during the classification pass). This is an automated coverage check at ship time, distinct from PV-4's per-entry correctness review which remains a P1 human review.

---

## 2. Test Categories Map

| Category | Section | Pri | Owner | Gates |
|---|---|---|---|---|
| Unit — compose.py manifest selection | §3.1–§3.4 | P0 | dev (skill) | AC-1, AC-2, AC-7 |
| Unit — fragment lint (mode-conditional rejection) | §3.5 | P0 | dev (skill) | AC-3 |
| Unit — manifest parse | §3.6 | P0 | dev (skill) | structural |
| Unit — L4 composition invariance | §3.7 | P0 | dev (skill) | AC-6 |
| Integration — per-role end-to-end compose | §4.1–§4.2 | P0 | dev (skill) | AC-1, AC-2 |
| Integration — flip round-trip | §4.3–§4.4 | P0 | dev (skill) | AC-4 |
| Migration — #8699 closure | §5 | P0 | dev (skill) | AC-5 |
| Classification coverage check | §5 TC-M-5 | P0 | dev (skill) | AC-8 |
| L4 audit | §6 | P0 | pm | AC-6 |
| Negative tests | §7 | P0 | dev (skill) | AC-3, AC-7, AC-8 |
| Comprehension (CQ) — agent instruction surface | §8 | P0 | pm | required (touches agent instructions) |
| Manual smoke | §9 | P1 | pm + dev | pre-flip checklist |
| Gating | §10 | n/a | pm | release gate |
| Post-ship validation | §11 | P1 | pm | rollout |

P0 = blocks ship. P1 = blocks per-role flip. CQ is mandatory under
`feedback_comprehension_tests_required.md`.

---

## 3. Unit Tests

All unit tests live under `tests/test_compose_dual_mode.py` (new file). Use
`pytest`, `tmp_path` for filesystem isolation, monkeypatch for
`_read_config_value`. Existing compose tests under `tests/test_compose*.py`
must continue to pass.

### 3.1 TC-U-1: events-mode selection picks events manifest

- **Precondition**: tmp role dir with `includes-loop.yml` and `includes-events.yml`. Config stub returns `event-driven: yes`.
- **Steps**: Call the new compose entry point (e.g., `_load_manifest_for_mode(role, "events")` or whatever shape #8697 lands).
- **Expected**: Returned manifest path resolves to `includes-events.yml`. Returned include list matches the events manifest's `includes:` list, in order.
- **Verification**: Assert path + list equality.

### 3.2 TC-U-2: loop-mode selection picks loop manifest

- **Precondition**: Same fixture as TC-U-1. Config stub returns `event-driven: no`.
- **Expected**: Loop manifest selected.
- **Verification**: Path + list equality.

### 3.3 TC-U-3: missing `event-driven:` key defaults to loop mode

- **Precondition**: Config stub returns `None` (key absent).
- **Expected**: Loop manifest selected; one-line note on stderr if compose decides to surface the default, otherwise silent (impl. discretion — assert behaviour, not chatter).
- **Verification**: Path + list equality with TC-U-2.

### 3.4 TC-U-4: invalid `event-driven:` value errors cleanly

- **Precondition**: Config returns `event-driven: maybe`.
- **Expected**: `SystemExit` with non-zero code AND stderr contains the invalid token + a hint listing legal values (`yes`, `no`).
- **Verification**: `pytest.raises(SystemExit)`, capture stderr.

### 3.5 TC-U-5: fragment lint rejects mode-conditional syntax inside a fragment

- **Precondition**: Tmp fragment file containing the literal string `event-driven: yes` in a non-frontmatter, non-code-block context (i.e., as a runtime branch instruction). Manifest references it.
- **Expected**: Compose fails (`SystemExit` non-zero) with stderr naming the offending file and line. Reference: AC-3.
- **Verification**: Run compose, capture stderr. Assert message includes the file path and the matched token.
- **Allowed exceptions**: The literal `event-driven:` may appear in (a) a fragment body that documents the compose system itself (e.g., a "how mode selection works" reference doc) provided the fragment lives outside the `common-loop|common-events|roles/*/loop|roles/*/events` trees, OR (b) inside a fenced code block clearly demarcated as `yaml`/`md` (manifest examples). Implementation discretion on exactly how the linter draws this line; the test must cover at least one positive (rejection) and one allowed example.

### 3.6 TC-U-6: manifest parse — both includes-loop.yml and includes-events.yml load

- **Precondition**: Both manifests present, well-formed, list-of-strings entries (same schema as today's `includes.yml`).
- **Expected**: Both load without warning; `_load_manifest` returns a list of strings; each referenced fragment file exists on disk (compose's existing existence check, lines 195–204).
- **Verification**: For each of the four roles (pm, qa, skill, dm) × {loop, events} = 8 manifests, load and validate.

### 3.7 TC-U-7: L4 layer composed identically across modes

- **Precondition**: Same role, both modes. L4 directory `.squidsquad/project/` contains the same file set in both runs. **#8697 implementation MUST add an explicit L4 marker** of the form `<!-- L4: project instructions -->` immediately before the first L4 file's content in the composed output (review F7). The marker is a hard contract; all L4 boundary detection in this plan uses it exclusively.
- **Steps**: Compose role under `event-driven: no` capturing the L4 region (content from `<!-- L4: project instructions -->` to EOF). Compose under `event-driven: yes` capturing the L4 region the same way.
- **Expected**: Byte-identical L4 region between the two outputs. The L4 marker is present in both outputs at exactly one location.
- **Verification**: `assert L4_loop == L4_events`; assert the marker appears exactly once in each composed CLAUDE.md.

### 3.8 TC-U-8: missing fragment listed in manifest errors clearly

- **Precondition**: Manifest entries reference a file that does not exist on disk.
- **Expected**: Compose exits non-zero with stderr naming the missing path (matches existing behavior at `compose.py:199–204`). Both `includes-loop.yml` and `includes-events.yml` must trigger the same error.
- **Verification**: Patch existing tests at `compose.py:195–205` if needed; ensure new manifests are validated identically.

---

## 4. Integration Tests

Integration tests live under `tests/test_compose_dual_mode_e2e.py`. They drive the actual `compose.py deploy` CLI for each role.

### 4.1 TC-I-1: end-to-end loop deploy per role

For each role ∈ {pm, qa, skill, dm}:

- **Precondition**: Config has `event-driven: no`. New fragment trees exist. New manifests exist.
- **Steps**: `python references/scripts/compose.py deploy <role>` → captures `.squidsquad/<role>/CLAUDE.md`.
- **Expected**:
  - Output exists, non-empty.
  - Contains at least one of: `cycle_pre.py`, `cycle_post.py`, `cycle-runner`, `/loop 30m`. (Loop fingerprint.)
  - Contains zero of: `event_poll.py`, `Last Processed Event ID`, `forge-read pattern`, `<!-- sub-skill: event-driven-workflow -->`, `bootup-complete`. (Events fingerprint.)
  - Standard L4 content present (verifies L4 still flows).
- **Verification**: Grep assertions per fingerprint set; line count > 200 sanity.

### 4.2 TC-I-2: end-to-end events deploy per role

For each role ∈ {pm, qa, skill, dm}:

- **Precondition**: Config has `event-driven: yes`. Events tree + manifest exist.
- **Steps**: Same as TC-I-1.
- **Expected**:
  - Output exists, non-empty.
  - Contains at least one of: `event_poll.py`, `Last Processed Event ID`, `forge-read`, `<!-- sub-skill: event-driven-workflow -->` (or the migrated fragment name), `bootup-complete`.
  - Contains zero of: `/loop 30m execute one Ralph Loop cycle`, `cycle_pre.py`, `cycle_post.py`, `cycle-runner`, `Phase 1 — Pre-Cycle (Mechanical)`.
- **Verification**: Grep assertions per fingerprint set.

### 4.3 TC-I-3: flip config no→yes shows full L1–L3 swap, L4 unchanged

- **Precondition**: One role (start with `skill`, which has fewer role-specific quirks). Config `event-driven: no`. Compose, snapshot CLAUDE.md as `A`.
- **Steps**: Flip config to `event-driven: yes`. Recompose. Snapshot as `B`.
- **Expected**:
  - `diff A B` shows complete replacement of L1–L3 (no preserved sub-skill blocks except the truly-shared `common/` fragments listed in BOTH manifests, e.g., vault, soul, file-conventions).
  - L4 region in `A` and `B` is byte-identical (matches TC-U-7).
- **Verification**: Split each composed file at the L4 boundary marker; compare regions.

### 4.4 TC-I-4: round-trip yes→no produces output identical to original loop compose

- **Precondition**: Continuing from TC-I-3 with snapshot `A` (loop) and `B` (events).
- **Steps**: Flip config back to `event-driven: no`. Recompose. Snapshot as `C`.
- **Expected**: `A` and `C` are byte-identical (after newline normalization). No event-mode residue in `C`.
- **Verification**: `assert A == C` (or `hash(A) == hash(C)` after normalization).

### 4.5 TC-I-5: legacy includes.yml shim still works

- **Precondition**: One role has only `includes.yml` (no `-loop`/`-events` split). Config: `event-driven: no`.
- **Expected**: Compose succeeds, output is identical to pre-#8697 deploy for that role, stderr carries a one-line deprecation note pointing at #8698.
- **Verification**: Diff against pre-#8697 captured output; assert stderr contains `deprecation` or `#8698`.

### 4.6 TC-I-6: legacy includes.yml shim refuses `event-driven: yes`

- **Precondition**: Role with only legacy `includes.yml`. Config: `event-driven: yes`.
- **Expected**: Compose exits non-zero with stderr saying the role has not been migrated to dual-mode (no events manifest). No partial/garbled CLAUDE.md written.
- **Verification**: `pytest.raises(SystemExit)`. Check `.squidsquad/<role>/CLAUDE.md` was NOT modified (file mtime unchanged or content equals prior state).

---

## 5. Migration Test (#8699 closure)

**Test file**: `tests/test_compose_event_workflow_migration.py`

### 5.1 TC-M-1: pre-#8697 baseline — deploy wipes hand-injected block (regression demonstration)

- **Precondition**: A deployed CLAUDE.md known to contain the hand-injected `event-driven-workflow` block (from commit `a3b108f2`). For this test, the block content is checked into the fixture under `tests/fixtures/event_driven_workflow_baseline.txt`.
- **Steps**: Run the PRE-#8697 compose path (the current `master` compose, or a recorded baseline).
- **Expected**: Output does not contain the baseline block — confirms the regression that motivates #8699.
- **Verification**: This test exists to lock in the failure mode; it is expected to PASS by demonstrating the wipe. May be skipped/converted to a documentation comment once #8697 lands — but keeping it active until Phase 6 documents the historical defect.

### 5.2 TC-M-2: post-#8697 — deploy preserves event-driven-workflow content via fragment source

- **Precondition**: After #8697 ships. Config: `event-driven: yes`. Migration deliverable: new fragment(s) under `references/sub-skills/common-events/` containing the migrated event-driven-workflow content.
- **Steps**: `compose.py deploy <role>`.
- **Expected**: Output CLAUDE.md contains the event-driven-workflow content, sourced from the new fragment. Wrapped in standard `<!-- sub-skill: <name> -->` / `<!-- /sub-skill: <name> -->` markers (i.e., not hand-injected).
- **Verification**: Grep for unique tokens from the baseline (e.g., `Last Processed Event ID`, `forge-read`, `bootup-complete`). Grep for the surrounding `<!-- sub-skill: ... -->` markers and assert content is inside them.

### 5.3 TC-M-3: diff between current deployed CLAUDE.md and new compose is intentional

- **Precondition**: Snapshot current deployed `.squidsquad/<role>/CLAUDE.md` (pre-#8697). Run new compose with `event-driven: no` (the default for backward compat).
- **Expected**: Diff is empty or limited to (a) fragment ordering changes that the new manifest explicitly carries forward and (b) the absence of any hand-injected residue. The diff is reviewed and signed off by the human as part of #8697 PR review.
- **Verification**: Generate the diff into the PR description for human inspection. No automated assertion — the human is the final reviewer; the test outputs the diff to `tests/output/diff-8697-<role>.txt` for archival.

### 5.4 TC-M-4: events-mode migration source contains the canonical workflow content

- **Precondition**: Post-#8697.
- **Steps**: `git grep -l "Last Processed Event ID" references/sub-skills/`
- **Expected**: At least one source file matches under `references/sub-skills/common-events/` (or a sibling per-role events tree, but the canonical content should live in `common-events/`).
- **Verification**: `assert len(matches) >= 1 and any("common-events" in p for p in matches)`.

### 5.5 TC-M-5: classification coverage — union covers legacy superset (P0 automated, review F4)

- **Precondition**: For each of the four roles (pm, qa, skill, dm): the pre-#8697 legacy `includes.yml` is preserved as a baseline (either checked in or captured from the prior commit). New manifests `includes-loop.yml` and `includes-events.yml` exist.
- **Steps**: Parse all three manifests' `includes:` lists for the role. Compute `legacy_set`, `loop_set`, `events_set`. Compute `union = loop_set ∪ events_set`.
- **Expected**: `legacy_set ⊆ union` — every entry in the legacy manifest appears in at least one of the new manifests. Entries in BOTH new manifests are mode-agnostic (truly shared); entries in only one are mode-specific. No fragment was dropped silently during the classification pass.
- **Verification**: For each role: `assert legacy_set.issubset(union)`, else fail naming the missing fragment(s). This is an automated coverage gate that complements the human review in PV-4 (which checks per-entry correctness of which mode an entry was assigned to).

---

## 6. L4 Audit (pre-flip checklist enforcement)

**Test file**: `tests/test_l4_loop_audit.py`
**Audit log artifact**: `.squidsquad/pm/planning/L4-AUDIT-8697.md` (created during #8697 implementation; reviewed at human approval)

### 6.1 Audit script

A small helper script (location: `references/scripts/audit_l4_loop.py` — new in #8697) greps `.squidsquad/project/*.md` for /loop-specific language and emits a JSON report.

**Patterns to flag**:
- `\bcycle_pre\b`
- `\bcycle_post\b`
- `/loop\b`
- `\bbetween cycles\b`
- `\bnext cycle\b`
- `\bcycle counter\b`
- `\biter-\d+\.md\b`
- `\bRalph Loop\b` (loop-specific term — call out for human review even if benign)
- `\b/loop 30m\b`

The audit emits each hit with file + line + 30 chars of surrounding context and the recommended action (`remove`, `generalize`, or `split`).

### 6.2 TC-L-1: audit fails on dirty L4 fixture

- **Precondition**: `tests/fixtures/l4_dirty/shared-instructions.md` contains a line referencing `cycle_pre.py`.
- **Steps**: Run audit against the fixture dir.
- **Expected**: Audit exits non-zero (or returns at least one finding).
- **Verification**: Assert non-empty findings list AND the offending file appears in the report.

### 6.3 TC-L-2: audit passes on clean L4 fixture

- **Precondition**: `tests/fixtures/l4_clean/shared-instructions.md` containing only mode-agnostic language.
- **Steps**: Run audit.
- **Expected**: Zero findings.
- **Verification**: `assert findings == []`.

### 6.4 TC-L-3: live audit against `.squidsquad/project/` must pass before any per-role flip

- **Precondition**: Real project tree. This test runs as part of the pre-flip checklist (§10), not as part of the standard CI suite (because the audit is a one-time gate, not a regression).
- **Steps**: `python references/scripts/audit_l4_loop.py .squidsquad/project/`
- **Expected**: Zero findings OR every finding has been resolved per `L4-AUDIT-8697.md` (either removed, generalized, or split into mode-specific variants `*-loop-*.md` / `*-events-*.md`).
- **Verification**: Audit JSON shows clean OR audit log shows resolution.

### 6.5 Mode-specific L4 split convention (already permitted by CONTEXT §5.3, review F6)

If any L4 file cannot be cleanly generalized, the implementation splits it:
- `shared-loop-instructions.md` (consumed only when `event-driven: no`)
- `shared-events-instructions.md` (consumed only when `event-driven: yes`)
- Unsuffixed `shared-instructions.md` remains mode-agnostic.

`compose.py` L4 filtering (currently `compose.py:318–340`) is extended to honor a mode suffix in the file name. **CONTEXT.md §5.3 explicitly permits mode-specific L4 variants** ("L4 project instruction files contain no /loop-specific language, or are explicitly split into mode-specific variants"); the architecture already contemplates the split. The default approach (#8697 baseline) is to clean L4 so no split is needed; the split mechanism is a fallback.

**Implementation scope decision (not PM relock):** should `compose.py`'s L4 layer include mode-suffix filtering in #8697, or should #8697 clean L4 files so no split is needed and defer the filtering code to a follow-up that first requires a split? Either path is consistent with CONTEXT.md. See §12.1.

---

## 7. Negative Tests

**Test file**: `tests/test_compose_dual_mode_negative.py`

### 7.1 TC-N-1: fragment with mode-conditional logic is rejected at deploy time (review F3)

- **Precondition**: tmp role directory with a freshly-authored fragment file (under `references/sub-skills/common-events/` or `references/sub-skills/roles/<role>/events/`) containing the literal string `event-driven: yes` in a non-frontmatter, non-code-block context (e.g., a sentence that reads "If event-driven: yes, branch to X."). `includes-events.yml` references this fragment. Config returns `event-driven: yes`.
- **Steps**: Run `python references/scripts/compose.py deploy <role>`.
- **Expected**: Compose exits non-zero (`SystemExit`) with stderr naming (a) the offending fragment file path and (b) the matched line/token. No partial CLAUDE.md is written.
- **Verification**: `pytest.raises(SystemExit)`; capture stderr; assert it contains the fragment file path. Confirms the lint is wired into `compose.py deploy` (deploy-time), not just exercised by the standalone lint unit test TC-U-5.

### 7.2 TC-N-2: missing `includes-events.yml` errors when config says `yes`

- **Precondition**: Role has `includes-loop.yml` but no `includes-events.yml`. Config: `event-driven: yes`.
- **Expected**: Compose exits non-zero with stderr naming the missing manifest. Does NOT silently fall back to loop manifest.
- **Verification**: `pytest.raises(SystemExit)`, assert stderr contains `includes-events.yml` and the role name.

### 7.3 TC-N-3: missing `includes-loop.yml` errors when config says `no`

- **Precondition**: Role has `includes-events.yml` but no `includes-loop.yml`. Config: `event-driven: no`.
- **Expected**: Same shape as TC-N-2 — clear error, no silent fallback.
- **Verification**: Same as TC-N-2.

### 7.4 TC-N-4: shared fragment listed in both manifests is allowed

- **Precondition**: A fragment file (e.g., `common/vault-protocol.md`) is referenced from BOTH `includes-loop.yml` AND `includes-events.yml`.
- **Expected**: Compose succeeds in both modes; the fragment appears in both composed outputs; no duplicate content, no warning about double-reference.
- **Verification**: Compose under each mode, grep for the fragment markers, assert exactly one occurrence per mode.

### 7.5 TC-N-5: both manifests referencing the same fragment do not duplicate content

- **Precondition**: As TC-N-4. Compose under `event-driven: yes`.
- **Expected**: The shared fragment's content appears exactly once in the output (no double-wrapping, no duplicate markers).
- **Verification**: `output.count("<!-- sub-skill: vault-protocol -->") == 1`.

### 7.6 TC-N-6: malformed manifest is rejected

- **Precondition**: `includes-events.yml` with invalid YAML (e.g., unclosed bracket).
- **Expected**: Compose exits non-zero with stderr quoting the YAML parser error (existing behavior at `compose.py:153–157`).
- **Verification**: `pytest.raises(SystemExit)`.

### 7.7 TC-N-7: manifest with empty `includes:` list

- **Precondition**: `includes-events.yml` with `includes: []`.
- **Expected**: Compose succeeds, output contains L1 + L2 + L4 only (no L3 sub-skill includes). Sanity warning to stderr is acceptable but not required.
- **Verification**: Output is non-empty, contains L4 content, contains zero `<!-- sub-skill: -->` blocks beyond the entry template's own inline sub-skill content.

### 7.8 TC-N-8: cross-manifest fallback regression — missing fragment under events mode (review F5)

- **Precondition**: Role has BOTH `includes-loop.yml` AND `includes-events.yml`. `includes-events.yml` references a fragment file that does NOT exist on disk. Config returns `event-driven: yes`.
- **Steps**: Run `python references/scripts/compose.py deploy <role>`.
- **Expected**: Compose exits non-zero (`SystemExit`) with stderr naming (a) the missing fragment path and (b) the events manifest. The deploy MUST NOT silently fall back to `includes-loop.yml`. No partial CLAUDE.md is written.
- **Verification**: `pytest.raises(SystemExit)`; assert stderr contains both the missing fragment path and `includes-events.yml`; assert `.squidsquad/<role>/CLAUDE.md` is unmodified (mtime or content equal to prior state). Distinct from TC-U-8 (generic missing-fragment detection) and TC-N-2 (entire events manifest missing): this test specifically prevents mode-selection bypass when the events manifest exists but is internally broken.

---

## 8. Comprehension Tests (REQUIRED — touches agent instructions)

CQ specs are mandatory under `feedback_comprehension_tests_required.md`. The
compose stack itself is "agent infrastructure" — but the migrated
event-driven-workflow content IS agent-facing instruction, so CQ coverage
must be solid.

**Spec file**: `tests/comprehension/8697_spec.json`
**Pytest harness**: `tests/test_comprehension_8697.py`

### 8.1 Spec contents

```json
{
  "issue": 8697,
  "title": "compose.py dual-mode — separate L1-L3 sets per wake mode, shared L4",
  "files": [
    "references/scripts/compose.py",
    "references/sub-skills/common-events/event-driven-workflow.md",
    "references/sub-skills/common-loop/cycle-runner.md",
    "references/roles/pm/includes-loop.yml",
    "references/roles/pm/includes-events.yml"
  ],
  "questions": [
    {
      "id": "1",
      "question": "An agent is composed with event-driven: yes in config.md. Which fragment tree does compose.py read from for L1-L3?",
      "expected": "compose.py loads includes-events.yml and reads fragments from references/sub-skills/common-events/ and references/sub-skills/roles/<role>/events/ (plus any truly-shared fragments under references/sub-skills/common/ that are listed in both manifests). It does NOT read from common-loop/ or roles/<role>/loop/."
    },
    {
      "id": "2",
      "question": "An agent is composed with event-driven: no (or the key absent). Which fragment tree does compose.py read from?",
      "expected": "compose.py loads includes-loop.yml and reads fragments from common-loop/ and roles/<role>/loop/ (plus truly-shared fragments). It does NOT read from common-events/ or roles/<role>/events/. Missing event-driven: key defaults to no for backward compatibility."
    },
    {
      "id": "3",
      "question": "Where do L4 (project) instructions come from in events mode vs loop mode?",
      "expected": "L4 comes from .squidsquad/project/*.md in both modes — it is mode-agnostic. The same files are layered on top regardless of event-driven flag. L4 must be audited for /loop-specific language before any per-role flip (see pre-flip checklist)."
    },
    {
      "id": "4",
      "question": "After #8697 ships, if the canonical event-driven-workflow source fragment is missing from references/sub-skills/common-events/ when a role is composed with event-driven: yes, what happens?",
      "expected": "compose.py errors out with a clear message naming the missing fragment path and the role. It does NOT silently fall back to loop mode and it does NOT hand-inject content. The deploy fails so the operator notices and restores the source. (This is the post-#8697 fix for the #8699 regression where the hand-injected block was wiped on deploy.)"
    },
    {
      "id": "5",
      "question": "May a fragment file under references/sub-skills/common-events/ contain a runtime instruction like 'if event-driven: yes, do X'?",
      "expected": "No. Mode-conditional logic must NOT live inside any L1-L3 fragment. The manifest+tree pairing carries the mode; fragments are pure. compose.py's fragment lint rejects any fragment body containing a runtime event-driven: branch instruction."
    },
    {
      "id": "6",
      "question": "A role has only a legacy includes.yml (no -loop/-events split). Config has event-driven: no. What does compose.py do?",
      "expected": "It falls back to the legacy includes.yml (backward-compat shim), composes successfully, and emits a one-line deprecation note pointing at #8698 (Phase 6 cleanup that removes the shim)."
    },
    {
      "id": "7",
      "question": "Same role with legacy includes.yml only, but config has event-driven: yes. What does compose.py do?",
      "expected": "It errors out clearly — the role has not been migrated to dual-mode and there is no events manifest. compose.py does not pretend the legacy manifest is the events manifest."
    }
  ]
}
```

### 8.2 Pytest harness skeleton

```python
# tests/test_comprehension_8697.py
import json
import subprocess
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "tests" / "comprehension" / "8697_spec.json"
RUNNER = REPO / "references" / "scripts" / "run_comprehension_test.py"
RESULTS = REPO / "tests" / "comprehension" / ".results" / "8697-results.json"


@pytest.fixture(scope="module")
def comprehension_results():
    subprocess.check_call(["python", str(RUNNER), str(SPEC)])
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def _get(results, qid):
    for r in results["questions"]:
        if r["id"] == qid:
            return r
    raise AssertionError(f"missing question {qid}")


class TestComprehension8697:
    def test_q1_events_tree_selection(self, comprehension_results):
        r = _get(comprehension_results, "1")
        assert r["pass"], r.get("reason")

    def test_q2_loop_tree_selection(self, comprehension_results):
        r = _get(comprehension_results, "2")
        assert r["pass"], r.get("reason")

    def test_q3_l4_mode_agnostic(self, comprehension_results):
        r = _get(comprehension_results, "3")
        assert r["pass"], r.get("reason")

    def test_q4_missing_source_fragment_fails_loudly(self, comprehension_results):
        r = _get(comprehension_results, "4")
        assert r["pass"], r.get("reason")

    def test_q5_no_mode_conditional_in_fragments(self, comprehension_results):
        r = _get(comprehension_results, "5")
        assert r["pass"], r.get("reason")

    def test_q6_legacy_shim_loop_mode(self, comprehension_results):
        r = _get(comprehension_results, "6")
        assert r["pass"], r.get("reason")

    def test_q7_legacy_shim_rejects_events_mode(self, comprehension_results):
        r = _get(comprehension_results, "7")
        assert r["pass"], r.get("reason")
```

The harness follows the established pattern (per `RESEARCH-compose-boot.md` §"Comprehension Test Format"): runner computes content hash, skips on cache hit, spawns test agent + eval agent, writes results.

---

## 9. Manual Smoke Tests

These are PM-run smoke checks, not automated. Each runs once per role during the implementation PR review.

### 9.1 SM-1: Flip one role, recompose, diff

- **Precondition**: #8697 PR draft. Pick `skill` as the lowest-risk role.
- **Steps**:
  1. Set `event-driven: yes` for skill in `.squidsquad/config.md`.
  2. `python references/scripts/compose.py deploy skill`.
  3. `git diff .squidsquad/skill/CLAUDE.md`.
- **Expected**: Full L1–L3 swap, L4 unchanged, no orphan content. The event-driven-workflow content is present and wrapped in standard markers.
- **Verification**: Eyeball diff. Approve or reject.

### 9.2 SM-2: Boot a freshly-composed events-mode agent

- **Precondition**: SM-1 complete; skill role composed in events mode. **Singleton enforcement (#8692) must be in place before running this smoke — see §10 gating.**
- **Steps**: Start the skill agent via `python references/scripts/start_team.py --role skill`. Observe the first 30 seconds of output.
- **Expected**: Agent boots without complaint about missing fragments or contradictory instructions. Does not invoke `/loop`. Does not invoke `cycle_pre.py`. (It may legitimately fail at later steps if other Phase 5 deliverables — #8694, #8695 — are not yet in place; that is fine for SM-2's purpose, which is to verify the COMPOSE output is loadable.)
- **Verification**: Agent log shows boot-time reads of the composed CLAUDE.md. No `[ERROR]` lines from compose-content interpretation.

### 9.3 SM-3: Round-trip flip back

- **Precondition**: SM-1 complete.
- **Steps**: Flip skill back to `event-driven: no`. Recompose. Diff against the pre-flip snapshot.
- **Expected**: Byte-identical to pre-flip snapshot (matches TC-I-4).

---

## 10. Gating Conditions

**Hard prerequisites for #8697 SHIP**:
- All P0 tests in §§3–8 PASS — including TC-M-5 classification coverage check (AC-8).
- Human review of `tests/output/diff-8697-<role>.txt` (per TC-M-3) signs off the intentional diff between current deployed CLAUDE.md and new compose output for each of the four roles.
- L4 audit (§6) is clean for `.squidsquad/project/` OR the audit log `L4-AUDIT-8697.md` shows each finding resolved.
- Standard plan-checker + human approval (per Phase 5 process).
- #8699 is closed in the same PR (or as a follow-up note in the PR description confirming the migration is complete) — this is mechanical since the migration is a #8697 deliverable.

**Hard prerequisites for any per-role FLIP (separate from ship)**:
- #8692 (singleton enforcement) shipped — events mode unsafe without it.
- #8697 (this) shipped.
- #8694 fragments (event-mode L1 base + `event_poll.py`) in place for the role.
- #8695 (`bootup_complete` flag) deployed.
- Pre-flip checklist (CONTEXT.md §6.3) complete for the role.
- L4 audit clean for any L4 file that role consumes.

**Soft gates (recommended but not blocking)**:
- SM-1, SM-2, SM-3 run on at least one role before the flip is approved.

---

## 11. Post-Ship Validation

After #8697 ships and BEFORE any per-role flip:

### 11.1 PV-1: Deploy all four roles in both modes

For each role ∈ {pm, qa, skill, dm}:
- Compose with `event-driven: no`. Save as `post-ship/<role>-loop.md`.
- Compose with `event-driven: yes`. Save as `post-ship/<role>-events.md`.
- Diff `post-ship/<role>-loop.md` against the pre-#8697 `.squidsquad/<role>/CLAUDE.md`. Verify identity-modulo-intentional-changes.

### 11.2 PV-2: No orphan content in any composed CLAUDE.md

Recursive scan of all eight composed outputs from PV-1:
- Every line of content is inside a `<!-- sub-skill: ... -->` block OR is part of L1/L2/L3/L4 base structure.
- No content that cannot be traced back to a source file under `references/`.

**Verification**: A small inverse-trace script (or manual grep) for any string in the composed output finds a matching source fragment.

### 11.3 PV-3: Document the directory layout decision in CONTEXT.md

CONTEXT.md §10 currently lists open question 1 as "Exact directory naming for the two fragment sets — `common-loop` vs `common/loop/`, etc.". Once #8697 lands and the naming is locked, append a §10.1 "Closed by implementation" entry recording the chosen names so future readers don't have to reverse-engineer it.

### 11.4 PV-4: Initial fragment classification audit

CONTEXT.md §10 open question 3 is "Initial fragment classification pass (loop / events / both for the existing ~31 entries per role manifest)". Verify in PV-4 that each existing manifest entry has been classified:

- Entries in `includes-loop.yml` only → loop-mode.
- Entries in `includes-events.yml` only → events-mode.
- Entries in both → mode-agnostic (truly shared, e.g., `common/vault-protocol`).

Generate a classification report `tests/output/classification-8697.md` (one row per fragment, columns: name, in-loop, in-events, classification). Human reviews the report; the PM closes open question 3 against this report.

---

## 12. Open Questions

Carried forward to planning review:

1. **L4 split mechanism scope decision (implementation, not architecture)** — CONTEXT §5.3 already permits mode-specific L4 variants; this is not a PM relock. The engineering question is: should `compose.py`'s L4 layer include mode-suffix filtering in #8697 now, or should #8697 clean L4 files so no split is needed and defer the filtering code to a follow-up that first requires a split? Either path is consistent with CONTEXT.md.
2. **Fragment lint scope** (TC-U-5). The lint rule "no `event-driven:` runtime branch in fragment bodies" needs a concrete regex. Suggested: reject any unquoted, non-code-block occurrence of `event-driven:\s*(yes|no)` outside of frontmatter. Lock at implementation.
3. **TC-M-3 human review automation**. The intentional diff between current deployed and new compose output is reviewed by the human. Should it also be captured as a frozen snapshot test (assert byte-equal to a checked-in expected diff) for future regression detection?

---

## 13. Sign-Off Checklist

- [ ] All P0 unit tests (§3) green
- [ ] All P0 integration tests (§4) green
- [ ] Migration tests (§5) green, #8699 referenced as closed in PR description
- [ ] L4 audit (§6) clean OR resolved per `L4-AUDIT-8697.md`
- [ ] Negative tests (§7) green
- [ ] Comprehension spec (§8) green — required by `feedback_comprehension_tests_required.md`
- [ ] Manual smoke tests (§9) executed for at least one role (skill recommended)
- [ ] Gating conditions (§10) verified
- [ ] Post-ship validation plan (§11) attached to PR
- [ ] Open questions (§12) resolved or explicitly deferred

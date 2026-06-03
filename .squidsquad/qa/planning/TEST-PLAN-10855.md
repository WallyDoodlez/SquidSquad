# TEST-PLAN-10855 — Verifier boot leaves claude.exe alive but inert

**Source**: GitHub issue #10855 (symptom + reproduction + root-cause comment) and PR #10952 test plan.
**Derived without reading the diff except where ACs are absent from the issue body and must be inferred from skill-lead's explicit fix scope.**

## ACs (derived)

The issue body has no numbered ACs. The PM-cycle-2094 root-cause comment + skill-lead's PR scope yield the following observable ACs:

- **AC-1**: `boot_remote._get_all_roles()` returns the post-#6274 canonical trio — must include `verifier`, must NOT include `qa`.
- **AC-2**: `boot_remote.py`'s fixed-team set comment + roster literal match `config.py:_collect_install_agents` (canonical mirror — line 742). Symmetry restored across the install-roster path.
- **AC-3**: Unit-test suite for the changed area is green — `tests/test_boot_remote.py`, `tests/test_9242_harness_wedge_fixes.py`, `tests/test_harness.py` — matches PR claim of 243 pass / 1 skip.
- **AC-4** (HUMAN-REQUIRED — out-of-scope for code QA): Booting `python references/scripts/boot_remote.py --role verifier` against a repaired `.harness-state.json` writes `.squidsquad/verifier/.claude-pid` and progresses to first-cycle `current-state` write. Skill-lead explicitly carved this out as needing PM's manual repair of the corrupted `.harness-state.json` first.

## Test Cases

### TC-1 (covers AC-1): `_get_all_roles()` returns canonical post-#6274 trio
- **Precondition**: Branch `squidsquad/task/10855` checked out; operator WIP in `references/scripts/harness.py` (unresolved merge marker at line 417) set aside.
- **Steps**: Import `boot_remote` directly; call `_get_all_roles()`; assert `verifier` present and `qa` absent.
- **Expected**: Returns `['dm', 'pm', 'skill', 'verifier']` (sorted).
- **Verification command**: `python -c "import sys; sys.path.insert(0, 'references/scripts'); from boot_remote import _get_all_roles; r = _get_all_roles(); assert 'verifier' in r and 'qa' not in r, r; print(r)"`

### TC-2 (covers AC-2): config.py mirror is already canonical
- **Steps**: grep for the canonical-roster comment in `config.py`.
- **Expected**: line 740 reads `# Fixed team: verifier + DM always present (#6261/#6274: qa→verifier per D5)`.
- **Verification command**: `grep -n "Fixed team" references/scripts/config.py`

### TC-3 (covers AC-3a): `TestGetAllRoles` parameterized cases pass
- **Verification command**: `python -m pytest tests/test_boot_remote.py::TestGetAllRoles -v`

### TC-4 (covers AC-3b): PR's claimed combined suite passes — 243/1
- **Verification command**: `python -m pytest tests/test_boot_remote.py tests/test_9242_harness_wedge_fixes.py tests/test_harness.py`

### TC-5 (covers AC-4 — HUMAN-REQUIRED): verifier actually boots and writes current-state
- **Precondition**: `.harness-state.json` repaired to include a `verifier` agent entry with `clone_path` pointing at the operator's canonical verifier clone (per PM's option-1 sequence). The state file currently has only `{'agents': ['skill']}` — `qa` was removed in the partial cleanup but `verifier` was NOT yet added.
- **Steps**: Operator runs `python references/scripts/boot_remote.py --role verifier`; waits ≥ one cycle interval (30 min) for verifier's first cycle; checks for `.squidsquad/verifier/.claude-pid` (PID alive), `.squidsquad/verifier/current-state` written/updated, and at least one verifier iteration log.
- **Expected**: `.claude-pid` exists with an alive PID; `current-state` mtime is fresh; `.squidsquad/verifier/iter-*.md` shows a recent cycle log.
- **Result**: **HUMAN-REQUIRED** — cannot run from a QA cycle. Needs operator to (1) edit `.harness-state.json`, (2) start verifier via boot_remote, (3) wait one cycle, (4) report observed state.

## Coverage matrix

- AC-1 → TC-1
- AC-2 → TC-2
- AC-3 → TC-3, TC-4
- AC-4 → TC-5 (HUMAN-REQUIRED, cannot run in QA cycle)

## Comprehension Questions

Skipped — this task does not touch LLM-consumed instructions. It is a pure-Python one-line fix to a roster literal in `boot_remote.py:152` plus 2 test fixture updates. Behavior change is statically verifiable by TC-1 and TC-2; runtime behavior is gated on operator action (TC-5).

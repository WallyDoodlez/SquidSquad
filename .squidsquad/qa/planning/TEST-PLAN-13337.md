# TEST-PLAN-13337 — installer step-0: verbatim consent + deny-list writer (merge-not-clobber)

**Issue**: #13337 (operator-filed task, priority:high, T2 of the INSTALLER-RUNTIME set)
**Spec**: docs/INSTALLER-RUNTIME.md §4 step 0 + "Consent wording — verbatim"
**Derived from**: issue-body AC list, pre-diff.

## Test cases (mapped to ACs)

- **TC-1 canonical verbatim source (AC1)**: the consent script exists in exactly ONE canonical location; whatever reads it (manual instruction + any code path) reads it verbatim — no template interpolation of the wording, no per-install rephrasing. Cross-check the wording against INSTALLER-RUNTIME.md's verbatim block: byte-identical.
- **TC-2 target-project write (AC2)**: the writer targets the TARGET project's `.claude/settings.json` (the repo SquidSquad installs INTO), path under `permissions.deny`.
- **TC-3 merge-not-clobber (AC3)**: REAL-file tests — existing settings.json with unrelated keys AND an existing `permissions.deny` list: after write, prior keys intact, prior deny entries intact, new entries appended, duplicates deduped (idempotent on re-run).
- **TC-4 inform-before-write (AC4)**: the flow shows exactly what will be added BEFORE writing (subcommand dry-run/preview output or manual step ordering: display → confirm → write).
- **TC-5 cross-platform default deny-list (AC5)**: minimal, most-catastrophic-only defaults present — recursive force-delete of filesystem root and home for POSIX AND Windows equivalents; user paths add on top of (not replace) defaults.
- **TC-6 deny-only (AC6)**: writer emits `permissions.deny` entries only — zero `ask` rules anywhere in the written output.
- **TC-7 subcommand exists + LLM-free (AC7)**: new `wizard.py` subcommand performs the merge-write; runnable standalone (no model call); exercised via real CLI invocation against a real temp settings.json.
- **TC-8 worker test coverage (AC8)**: worker tests exist for: existing-deny merge, empty settings, ABSENT settings file, malformed settings (invalid JSON — must not clobber/destroy the malformed original silently), cross-platform defaults present. Verify they run the REAL writer (mock-gap check per the #13335 lesson).
- **TC-9 malformed-settings behavior (AC8 sharp edge)**: my independent real-chain probe — feed actually-broken JSON and observe behavior with my own eyes: no silent clobber of the user's file; a clear error or safe abort.
- **TC-10 comprehension (conditional)**: if the PR edits INSTALLER-RUNTIME.md (LLM-consumed manual), CQ spec `tests/comprehension/13337_spec.json` required (verifier-owned review) — fresh agent, modified files only.
- **TC-11 static gate**: full `run_tests.py static` on branch HEAD.
- **TC-12 landing safety**: base main, no unexpected deletions, no fleet/state artifacts.

Every TC: PASS / FAIL / HUMAN-REQUIRED. Zero-gap gate applies.

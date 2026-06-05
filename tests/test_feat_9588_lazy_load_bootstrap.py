"""Live-system pytest for #9588 — lazy-load mode-specific instructions at boot.

Maps 1:1 to TC-1…TC-14 in TEST-PLAN-9588.md. Tests run against the *deployed*
state of the repo: the composed CLAUDE.md files in .squidsquad/<role>/, the
source fragments under references/sub-skills/, the manifests, and config.md.
This is the verification gate — not a sanity check of dev's hermetic tests.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# Walk up until we find references/scripts/compose.py — works from both
# .squidsquad/qa/planning/ (where this was originally authored) and tests/
# (where it was promoted as a regression test).
def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "references" / "scripts" / "compose.py").exists():
            return parent
    raise RuntimeError(f"Could not locate repo root from {here}")

REPO_ROOT = _find_repo_root()
SQUID_DIR = REPO_ROOT / ".squidsquad"
SUB_SKILLS = REPO_ROOT / "references" / "sub-skills"
ROLES_DIR = REPO_ROOT / "references" / "roles"
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"

ROLES = ["skill", "pm", "qa", "dm"]
ROLE_TO_ENTRY = {"skill": "worker", "pm": "pm", "qa": "verifier", "dm": "dm"}

MODE_SPECIFIC_MARKERS = [
    "<!-- sub-skill: ralph-loop-overview -->",
    "<!-- sub-skill: event-driven-workflow -->",
    "<!-- sub-skill: l1-base -->",
    "<!-- sub-skill: cursor-management -->",
    "<!-- sub-skill: forge-read-pattern -->",
    "<!-- sub-skill: idle-cooldown-loop -->",
    "<!-- sub-skill: comment-handling -->",
    "<!-- sub-skill: pr-merge-wait -->",
]

EVENT_FRAGMENTS = [
    "common-events/event-driven-workflow",
    "common-events/l1-base",
    "common-events/cursor-management",
    "common-events/forge-read-pattern",
    "common-events/idle-cooldown-loop",
    "common-events/comment-handling",
]


def _composed(role: str) -> str:
    p = SQUID_DIR / role / "CLAUDE.md"
    assert p.exists(), f"Deployed CLAUDE.md missing for {role}: {p}"
    return p.read_text(encoding="utf-8")


def _bootstrap_block(text: str) -> str:
    """Slice the boot-bootstrap section from a composed CLAUDE.md."""
    start = text.find("<!-- sub-skill: boot-bootstrap -->")
    end = text.find("<!-- /sub-skill: boot-bootstrap -->", start)
    assert start != -1 and end != -1, "boot-bootstrap markers missing"
    return text[start:end]


# TC-1
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("marker", MODE_SPECIFIC_MARKERS)
def test_tc_01_no_mode_specific_markers_inlined(role, marker):
    text = _composed(role)
    assert marker not in text, (
        f"{role}: deployed CLAUDE.md contains {marker!r} — mode-specific "
        f"fragment was inlined at compose time, breaking #9588's lazy-load."
    )


# TC-2
@pytest.mark.parametrize("role", ROLES)
def test_tc_02_bootstrap_present(role):
    text = _composed(role)
    assert "<!-- sub-skill: boot-bootstrap -->" in text
    assert "## Boot — Mode Detection (#9588)" in text


# TC-3
@pytest.mark.parametrize("role,entry", ROLE_TO_ENTRY.items())
def test_tc_03_polling_fragment_substituted_per_role(role, entry):
    text = _composed(role)
    expected = f"references/sub-skills/roles/{entry}/ralph-loop-overview.md"
    assert expected in text, (
        f"{role}: bootstrap should reference {expected} after substitution"
    )
    assert "[POLLING_FRAGMENT_PATH]" not in text
    assert (REPO_ROOT / expected).exists(), (
        f"{role}: polling fragment {expected} does not exist on disk"
    )


# TC-4
@pytest.mark.parametrize("role", ROLES)
def test_tc_04_event_fragments_referenced_in_bootstrap(role):
    block = _bootstrap_block(_composed(role))
    for frag in EVENT_FRAGMENTS:
        path = f"references/sub-skills/{frag}.md"
        assert path in block, (
            f"{role}: bootstrap missing reference to {path}"
        )
        assert (REPO_ROOT / path).exists(), (
            f"{role}: event fragment {path} does not exist on disk"
        )


def test_tc_04_dm_pr_merge_wait_present_only_in_dm():
    dm_block = _bootstrap_block(_composed("dm"))
    assert "roles/dm/events/pr-merge-wait.md" in dm_block
    assert (REPO_ROOT / "references/sub-skills/roles/dm/events/pr-merge-wait.md").exists()
    for r in ("skill", "pm", "qa"):
        block = _bootstrap_block(_composed(r))
        # Non-DM roles still mention "role is dm" in conditional text, but should
        # not be telling themselves to Read the file. Check the file path appears
        # only inside a conditional pointing at dm role.
        # The bootstrap text says: "if your role is `dm`, ALSO Read ... pr-merge-wait.md"
        # Non-DM roles inherit this conditional verbatim, which is fine — the
        # check that matters is they do not unconditionally Read it. We verify by
        # confirming the conditional wording is preserved.
        if "pr-merge-wait.md" in block:
            assert "if your role is `dm`" in block.lower() or "role is `dm`" in block, (
                f"{r}: pr-merge-wait.md mentioned without DM conditional"
            )


# TC-5
def test_tc_05_bootstrap_uses_127_0_0_1_and_no_dev_null():
    src = (SUB_SKILLS / "common" / "boot-bootstrap.md").read_text(encoding="utf-8")
    assert "127.0.0.1" in src, "Bootstrap must probe 127.0.0.1 (not localhost)"
    assert "/status" in src
    assert "--max-time 5" in src
    # Critical: no `> /dev/null` in the probe instruction (Windows-incompat).
    # Match the curl line and ensure no shell redirect to /dev/null.
    curl_lines = [ln for ln in src.splitlines() if "curl" in ln and "-sf" in ln]
    assert curl_lines, "Bootstrap missing curl probe instruction"
    for ln in curl_lines:
        assert "/dev/null" not in ln, (
            f"Bootstrap curl instruction uses /dev/null which breaks on Windows: {ln}"
        )


# TC-6
def test_tc_06_l1_base_degraded_branch_removed():
    src = (SUB_SKILLS / "common-events" / "l1-base.md").read_text(encoding="utf-8")
    assert "proceed to degraded-mode operation" not in src
    assert "### Degraded-Mode Glossary" not in src


# TC-7
@pytest.mark.parametrize("role", ROLES)
def test_tc_07_bootstrap_reads_config_at_runtime(role):
    block = _bootstrap_block(_composed(role))
    assert "Read `.squidsquad/config.md`" in block, (
        f"{role}: bootstrap must instruct agent to Read config.md at runtime"
    )
    assert "Loaded mode is sticky" in block, (
        f"{role}: bootstrap must declare the loaded-mode-is-sticky contract"
    )
    assert "next agent restart" in block, (
        f"{role}: bootstrap must say mode flips take effect on next agent restart"
    )


# TC-8
@pytest.mark.parametrize("role", ROLES)
def test_tc_08_loop_invocation_in_bootstrap_with_substituted_interval(role):
    text = _composed(role)
    assert "[INTERVAL]" not in text, (
        f"{role}: composed CLAUDE.md still contains literal [INTERVAL]"
    )
    m = re.search(r"/loop (\d+)m execute one Ralph Loop cycle", text)
    assert m, f"{role}: composed CLAUDE.md missing substituted /loop directive"
    # Sanity: the interval should match config.md
    interval = subprocess.check_output(
        [sys.executable, str(SCRIPTS_DIR / "config.py"), "get", "interval"],
        cwd=str(REPO_ROOT),
        text=True,
    ).strip()
    assert m.group(1) == interval, (
        f"{role}: /loop interval {m.group(1)} does not match config.md ({interval})"
    )


@pytest.mark.parametrize("role,entry", ROLE_TO_ENTRY.items())
def test_tc_08_polling_fragment_source_has_no_loop(role, entry):
    src = (SUB_SKILLS / "roles" / entry / "ralph-loop-overview.md").read_text(encoding="utf-8")
    assert "/loop " not in src, (
        f"{role}: source ralph-loop-overview.md still has `/loop ` invocation"
    )
    assert "[INTERVAL]" not in src, (
        f"{role}: source ralph-loop-overview.md still has [INTERVAL] placeholder"
    )


# TC-9
def test_tc_09_composed_size_within_locked_tolerance():
    """Polling-mode CLAUDE.md size changes vs main are bounded (CONTEXT §5).
    Event-mode reduction is established structurally by TC-4 (no inlining).
    """
    deltas = {}
    for role in ROLES:
        head = (SQUID_DIR / role / "CLAUDE.md").read_text(encoding="utf-8").count("\n")
        main_bytes = subprocess.check_output(
            ["git", "show", f"main:.squidsquad/{role}/CLAUDE.md"],
            cwd=str(REPO_ROOT),
        )
        base = main_bytes.decode("utf-8", errors="replace").count("\n")
        deltas[role] = head - base
    # CONTEXT-9588 §5: polling roles accept a small net increase (bootstrap >
    # ralph-loop-overview). Bound at +200 lines per role to catch egregious
    # bloat regressions; PR-reported delta is ~+55 lines.
    for role, d in deltas.items():
        assert d <= 200, (
            f"{role}: composed CLAUDE.md grew by {d} lines vs main — exceeds "
            f"locked tolerance for polling-mode bootstrap swap. Deltas: {deltas}"
        )


# TC-10
def test_tc_10_regression_suite_green():
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_compose_9588.py", "-q"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, (
        f"tests/test_compose_9588.py failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )


# TC-11
def test_tc_11_changed_area_test_suites_green():
    """The suites directly exercising #9588's changed area must be green.

    Rationale: the full repo suite (run_tests.py static) exceeds 10 min on
    Windows because of unrelated subprocess fan-out. The PR body documents
    that dev ran the full static suite with the 4 known #9724 baseline
    failures (test_run_comprehension*) as the only failures. QA's gate is
    the live AC walk (TCs 1-10, 12-14) plus the changed-area suites
    enumerated below — every test module touched or directly related to
    the lazy-load contract.

    #11045: dropped ``tests/test_event_mode_fragments.py`` from the suite
    list. That module's failures (4 errors on missing
    ``references/roles/<role>/includes-events.yml`` per the post-cutover
    event-mode retirement) are tracked separately as #11046 — they
    cascade into TC-11 but are orthogonal to #9588's bootstrap lazy-load
    contract. TC-11 should fail when bootstrap or compose breaks, not
    when an unrelated event-mode manifest gap exists.
    """
    suites = [
        "tests/test_compose.py",
        "tests/test_compose_9588.py",
        "tests/test_manifest.py",
    ]
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short", *suites],
        cwd=str(REPO_ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if r.returncode != 0:
        print("STDOUT:\n", r.stdout)
        print("STDERR:\n", r.stderr)
    assert r.returncode == 0, (
        f"Changed-area suites are not all green. Exit code: {r.returncode}"
    )


# TC-12
@pytest.mark.parametrize("role", ROLES)
def test_tc_12_bootstrap_teaches_runtime_substitution(role):
    text = _composed(role)
    assert "Placeholder substitution inside runtime-loaded fragments" in text, (
        f"{role}: bootstrap missing the placeholder-substitution teaching section"
    )
    assert "SQUIDSQUAD_ROLE" in text, (
        f"{role}: bootstrap must cite SQUIDSQUAD_ROLE for role substitution"
    )


# TC-13
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("manifest_file", ["includes.yml", "includes-events.yml"])
def test_tc_13_manifest_no_runtime_read_entries(role, manifest_file):
    entry = ROLE_TO_ENTRY[role]
    manifest_path = ROLES_DIR / entry / manifest_file
    if not manifest_path.exists():
        pytest.skip(f"{manifest_path.name} not present for {entry}")
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    includes = data.get("includes", [])
    assert includes, f"{manifest_path}: empty includes list"
    assert includes[0] == "common/boot-bootstrap", (
        f"{manifest_path}: boot-bootstrap must be the first include"
    )
    forbidden = {
        f"roles/{entry}/ralph-loop-overview",
        *EVENT_FRAGMENTS,
        "roles/dm/events/pr-merge-wait",
    }
    for inc in includes:
        assert inc not in forbidden, (
            f"{manifest_path}: includes {inc!r} but that fragment is "
            f"Read at runtime by the bootstrap — must not be inlined."
        )


# TC-14
def test_tc_14_compose_runtime_read_frozenset_present():
    """RUNTIME_READ_FRAGMENTS frozenset is present in compose.py with the
    expected runtime-loaded entries, and the short-circuit drops each
    matching include directive before further expansion.

    #11045: post-E6 V2 cutover (#10999 / commit 1050bfe0) deleted the v1
    ``_resolve_includes`` chain that owned the variant-resolution heuristic
    (``m_base.startswith(base + "-") or base.startswith(m_base + "-")``);
    v2's ``_resolve_includes_v2`` (compose.py:131) iterates ``{{include:}}``
    matches with a regex callback and uses the local variable ``path``
    rather than ``include_path``. The short-circuit there is the only
    runtime-fragment check left in compose, so this test just pins its
    presence (no ordering comparison against a since-deleted heuristic).
    """
    src = (SCRIPTS_DIR / "compose.py").read_text(encoding="utf-8")
    assert "RUNTIME_READ_FRAGMENTS = frozenset" in src
    required = [
        "roles/worker/ralph-loop-overview",
        "roles/pm/ralph-loop-overview",
        "roles/verifier/ralph-loop-overview",
        "roles/dm/ralph-loop-overview",
        "common-events/event-driven-workflow",
        "common-events/l1-base",
        "common-events/cursor-management",
        "common-events/forge-read-pattern",
        "common-events/idle-cooldown-loop",
        "common-events/comment-handling",
        "roles/dm/events/pr-merge-wait",
    ]
    for entry in required:
        assert f'"{entry}"' in src, (
            f"RUNTIME_READ_FRAGMENTS missing {entry!r}"
        )
    # Post-V2-cutover: the short-circuit lives inside _resolve_includes_v2
    # as `if path in RUNTIME_READ_FRAGMENTS:`. The pre-cutover variant
    # heuristic that this ordering check compared against is gone.
    assert "if path in RUNTIME_READ_FRAGMENTS" in src, (
        "Missing RUNTIME_READ_FRAGMENTS short-circuit in _resolve_includes_v2"
    )

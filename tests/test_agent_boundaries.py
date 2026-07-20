"""#9925 regression tests — responsibility-layering machinery, reconciled.

Originally covered AC4 (compose-time roster + L2 content), AC6 (memory
absorption lineage tags), AC7 (L3 stub files), AC8 (L4 stub files), AC10
(byte-identical re-runs), AC11 (degraded modes).

#13890 reconciliation: every retired assertion below pinned an inventory or
behavior that a LATER, deliberate, correctly-scoped cleanup removed without
retiring the guard in the same PR (the verifier's root-cause pattern):

- **AC6 (13 params) RETIRED** — asserted ``<!-- absorbed from X -->``
  lineage tags in ``references/sub-skills/roles/<role>/responsibility.md``.
  Those files were deleted in #11087 (orphan sub-skill sources, D1-inlined
  per #11049); the successor files at ``references/roles/<role>/
  responsibility.md`` carry NO lineage tags (the #11331 polish rewrite
  dropped the convention repo-wide — grep confirms zero occurrences under
  references/). The absorbed CONTENT lives on; the tag convention does not.
- **AC7 (20 params) RETIRED** — asserted 20 L3 variant responsibility
  stubs; all deliberately deleted as pure orphans by #10366 (5b6977922).
  If #10360's slot migration reintroduces L3 stubs it ships its own guard.
- **AC8 seed pm/dm params RETIRED** — deleted by #13006 (0995f246d, "6
  dead pm-/dm- L4 seed stubs"); verifier/worker/shared seeds survive and
  stay pinned below.
- **AC4 REWRITTEN, roster-count RETIRED** — the ``agent-boundaries``
  sub-skill (rendered ``## Your Teammates' Responsibilities`` roster block)
  was retired per #10360/#11331: team awareness is now inlined prose in the
  L1 Identity slot and the marker is intentionally absent (see
  ``compose._inject_role_roster``'s docstring). The surviving invariants —
  teammate awareness present, L2 does/does-NOT-do sections present — are
  asserted against the current composed shape.
- **AC11 missing-marker warning RETIRED, replaced** — the warning was
  intentionally removed: marker absence is the documented steady state
  (``_inject_role_roster`` docstring). The replacement pins the documented
  behavior (content unchanged, NO warning) so a regression that starts
  warning on every compose is caught.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402

from _v2_test_helpers import v2_compose_for as _v2_compose_for  # noqa: E402


# ---------------------------------------------------------------------------
# AC4 (reconciled) — composed CLAUDE.md carries team awareness + L2 content
# ---------------------------------------------------------------------------


# #10156: post-#6274.2 rename — qa→verifier, dev→worker. "skill" remains
# as the variant name (config.md's `Workers: skill`).
@pytest.mark.parametrize("role", ["pm", "verifier", "dm", "skill"])
def test_ac4_composed_contains_identity_awareness_and_l2(role):
    """Post-#10360/#11331 shape: team awareness is L1 Identity prose (the
    rendered roster block is retired), and the role's own Responsibility
    slot carries the does / does-NOT-do sections."""
    composed = _v2_compose_for(role)
    assert "Your teammates run in parallel on their own clones" in composed, (
        f"L1 Identity teammate-awareness prose missing from composed {role}"
    )
    assert "What this role does" in composed, (
        f"L2 'What this role does' header missing from composed {role}"
    )
    assert "What this role does NOT do" in composed, (
        f"L2 'What this role does NOT do' section missing from composed {role}"
    )


# ---------------------------------------------------------------------------
# AC8 (reconciled) — surviving L4 stub files in seed and live locations
# ---------------------------------------------------------------------------


# pm/dm seed params retired (#13006 deleted them — see module docstring).
@pytest.mark.parametrize("prefix", ["verifier", "worker", "shared"])
def test_ac8_l4_seed_stub_exists(prefix):
    """AC8 (seed half): surviving seed templates at references/sub-skills/project/."""
    seed = REPO / "references" / "sub-skills" / "project" / f"{prefix}-responsibility.md"
    assert seed.exists(), f"L4 seed stub missing: {seed}"
    content = seed.read_text(encoding="utf-8")
    assert "Install-specific responsibility additions" in content


# #10156: post-#6274.2 rename — dev→worker, qa→verifier prefix.
@pytest.mark.parametrize("prefix", ["pm", "verifier", "dm", "worker", "shared"])
def test_ac8_l4_live_stub_exists(prefix):
    """AC8 (live half): live stubs at .squidsquad/project/."""
    live = REPO / ".squidsquad" / "project" / f"{prefix}-responsibility.md"
    assert live.exists(), f"L4 live stub missing: {live}"
    content = live.read_text(encoding="utf-8")
    assert "Install-specific responsibility additions" in content


# ---------------------------------------------------------------------------
# AC10 — byte-identical re-runs with agent_compose disabled
# ---------------------------------------------------------------------------


def test_ac10_byte_identical_recompose_agent_compose_off():
    """AC10: composing PM twice must produce byte-identical output.

    v1 framing (pre-E6): with ``agent_compose: no`` (or absent),
    ``compose_role`` twice is byte-identical — ``agent_compose: yes``
    invokes a non-deterministic LLM polish that legitimately breaks
    byte-identity, so the v1 form gated on the flag.

    v2 framing (post-E6 #10685): ``v2_link_stage.emit_v2_linked`` has
    NO non-deterministic step at the link stage — assemble (LLM polish)
    is a separate downstream step. Link-stage byte-identity is
    structural; the test no longer needs the ``_is_agent_compose_enabled``
    gate. Re-running ``_v2_compose_for`` simply re-runs the same
    deterministic pipeline.
    """
    a = _v2_compose_for("pm")
    b = _v2_compose_for("pm")
    assert a == b, "AC10: _v2_compose_for('pm') is non-deterministic"


# ---------------------------------------------------------------------------
# AC11 — degraded modes
# ---------------------------------------------------------------------------


def test_ac11_missing_display_name_raises_systemexit(capsys):
    """AC11: a role manifest missing the required `display_name` field
    must produce a build error with exit code != 0.
    """
    # Directly seed the cache so PM has no display_name.
    compose._ROLE_MANIFEST_CACHE.clear()
    try:
        compose._ROLE_MANIFEST_CACHE["pm"] = {
            "id": "pm", "tagline": "x", "description": "y",
        }
        with pytest.raises(SystemExit) as exc_info:
            compose._render_role_roster()
        assert exc_info.value.code != 0, (
            "AC11: missing display_name must exit with non-zero status"
        )
    finally:
        compose._ROLE_MANIFEST_CACHE.clear()


def test_ac11_marker_absent_is_silent_steady_state(capsys):
    """#13890 (replaces the retired warn-on-missing-marker assertion):
    per ``_inject_role_roster``'s documented contract, `{{role-roster}}`
    is intentionally absent from every composed CLAUDE.md since the
    agent-boundaries retirement — content passes through unchanged with
    NO warning. A compose that starts warning on every run (or mutating
    marker-less content) is the regression this now catches."""
    out = compose._inject_role_roster("hello world\n", "pm")
    assert out == "hello world\n", "no marker → content unchanged"
    captured = capsys.readouterr()
    assert captured.err == "", (
        "marker absence is the documented steady state — no warning expected"
    )


def test_ac11_missing_tagline_or_description_warns_but_succeeds(capsys):
    """AC11/D8: missing tagline OR description in a manifest produces a
    warning but does NOT crash. Both fields are optional in the
    degraded path."""
    compose._ROLE_MANIFEST_CACHE.clear()
    try:
        compose._ROLE_MANIFEST_CACHE["pm"] = {
            "id": "pm", "display_name": "PM",  # no tagline/description
        }
        # Don't actually go through the full sweep — just render the roster
        # and ensure it doesn't raise.
        block = compose._render_role_roster()
        assert "PM" in block
    finally:
        compose._ROLE_MANIFEST_CACHE.clear()
    captured = capsys.readouterr()
    # At least one of the two missing-field warnings should fire (since
    # the cached PM has neither tagline nor description).
    assert "WARNING" in captured.err

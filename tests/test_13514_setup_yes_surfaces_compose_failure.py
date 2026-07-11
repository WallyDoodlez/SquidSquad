"""#13514 — `wizard.py setup-yes` must NOT report success when a role fails to
compose its CLAUDE.md.

Regression for the greenfield failure surfaced by the #12527 smoke: with a role's
compose failing (e.g. the #13513 missing-catalog condition), `setup-yes` printed
"Created N agent(s)" and returned 0 — a broken, non-bootable install masquerading
as a successful one. `scaffold_install` already records a per-role failure as
``claude_md == "FAILED"``; `cmd_setup_yes` must surface it: count only composed
agents and return non-zero when any role failed.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "references", "scripts"))

import wizard  # noqa: E402


class _GhMiss:
    """Fake `gh repo view` result — returns non-zero so repo_info falls back to
    the target dir name (keeps the test off the network)."""
    returncode = 1
    stdout = ""
    stderr = ""


def _common_stubs(monkeypatch):
    monkeypatch.setattr(wizard, "ensure_labels", lambda dry_run=False: {"created": 0})
    monkeypatch.setattr(wizard, "_run", lambda *a, **k: _GhMiss())


def test_setup_yes_returns_nonzero_when_a_role_fails_to_compose(tmp_path, monkeypatch, capsys):
    def fake_scaffold(spec, target_root, overwrite_existing=False):
        return {
            "target": str(target_root),
            "agents": [
                {"id": "pm", "role": "pm", "claude_md": "FAILED",
                 "soul_md": "FAILED", "working_state": "FAILED"},
                {"id": "skill", "role": "worker", "claude_md": str(target_root),
                 "soul_md": "s", "working_state": "w"},
            ],
        }
    monkeypatch.setattr(wizard, "scaffold_install", fake_scaffold)
    _common_stubs(monkeypatch)

    rc = wizard.cmd_setup_yes([str(tmp_path)])
    captured = capsys.readouterr()
    combined = captured.out + captured.err

    assert rc != 0, "setup-yes must return non-zero when any role fails to compose"
    assert "FAILED" in combined or "failed to compose" in combined.lower(), (
        "the failure must be visible in output, not silently swallowed"
    )
    # "Created N" must reflect only the composed agent, not the failed one.
    assert "Created 1 agent" in combined


def test_setup_yes_returns_nonzero_when_every_role_fails(tmp_path, monkeypatch, capsys):
    # The exact scenario in the bug title: EVERY role's compose fails, so zero
    # agents produce a CLAUDE.md. The install is fully non-bootable; setup-yes must
    # still fail loudly (rc!=0), report "Created 0 agent(s)", and print the ERROR.
    def fake_scaffold(spec, target_root, overwrite_existing=False):
        return {
            "target": str(target_root),
            "agents": [
                {"id": "pm", "role": "pm", "claude_md": "FAILED",
                 "soul_md": "FAILED", "working_state": "FAILED"},
                {"id": "skill", "role": "worker", "claude_md": "FAILED",
                 "soul_md": "FAILED", "working_state": "FAILED"},
            ],
        }
    monkeypatch.setattr(wizard, "scaffold_install", fake_scaffold)
    _common_stubs(monkeypatch)

    rc = wizard.cmd_setup_yes([str(tmp_path)])
    captured = capsys.readouterr()
    combined = captured.out + captured.err

    assert rc != 0, "setup-yes must return non-zero when every role fails to compose"
    assert "Created 0 agent" in combined, "'Created' must reflect zero composed agents"
    assert "failed to compose" in combined.lower()
    # The 'installed' success banner must NOT appear on a fully non-bootable install.
    assert "is installed" not in combined, (
        "the success summary must be suppressed when no role composed"
    )


def test_setup_yes_returns_zero_when_all_roles_compose(tmp_path, monkeypatch, capsys):
    def fake_scaffold(spec, target_root, overwrite_existing=False):
        return {
            "target": str(target_root),
            "agents": [
                {"id": "pm", "role": "pm", "claude_md": str(target_root),
                 "soul_md": "s", "working_state": "w"},
                {"id": "skill", "role": "worker", "claude_md": str(target_root),
                 "soul_md": "s", "working_state": "w"},
            ],
        }
    monkeypatch.setattr(wizard, "scaffold_install", fake_scaffold)
    _common_stubs(monkeypatch)

    rc = wizard.cmd_setup_yes([str(tmp_path)])
    captured = capsys.readouterr()
    combined = captured.out + captured.err

    assert rc == 0, "a fully-composed install must still return 0"
    assert "Created 2 agent(s)" in combined
    assert "FAILED" not in combined

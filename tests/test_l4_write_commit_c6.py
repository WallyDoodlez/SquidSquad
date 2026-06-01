"""Tests for references/scripts/l4_write_commit.py (#10655, PRD-C C6)."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import l4_write_commit  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STAGED_L4 = (
    "## Instructions\n\n"
    "### insert-before step:cycle/file-bug\n\n"
    "**Pre-check: scan incidents/**\n\n"
    "Before filing any bug, list `incidents/` and surface any SEV1 tickets "
    "newer than 7 days.\n"
)

_DIRECTIVE = "From now on, before filing a bug, also check `incidents/` for SEV1 tickets."

_GENERATED_AT = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_runner(failure_after=None, fail_command_prefix=None,
                 head_sha="abc123def4567890abc123def4567890abc123de"):
    """Build a stub runner that records git invocations.

    ``failure_after``: int N → first N runs return 0, the (N+1)th fails.
    ``fail_command_prefix``: tuple → fail any run whose argv starts with
    this prefix (e.g. ``("git", "push")``).
    Otherwise all runs return 0.
    """
    calls = []
    counter = {"n": 0}

    def run(argv, *, cwd=None, capture_output=True, text=True, **kwargs):
        calls.append({"argv": list(argv), "cwd": cwd})
        counter["n"] += 1
        # Resolve HEAD always succeeds with the canned SHA
        if argv[:2] == ["git", "rev-parse"]:
            return SimpleNamespace(returncode=0, stdout=head_sha + "\n",
                                    stderr="")
        if fail_command_prefix is not None:
            if tuple(argv[:len(fail_command_prefix)]) == fail_command_prefix:
                return SimpleNamespace(returncode=1, stdout="",
                                       stderr="simulated failure")
        if failure_after is not None and counter["n"] > failure_after:
            return SimpleNamespace(returncode=1, stdout="",
                                   stderr="simulated failure")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    return run, calls


# ---------------------------------------------------------------------------
# AC1: atomic-replace pattern
# ---------------------------------------------------------------------------

def test_atomic_write_lands_l4_file_on_disk(tmp_path):
    run, calls = _make_runner()
    result = l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="insert-before step:cycle/file-bug",
        target="step:cycle/file-bug",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    assert result.ok is True
    target = tmp_path / ".squidsquad" / "project" / "pm.md"
    assert target.exists()
    on_disk = target.read_text(encoding="utf-8")
    # Original staged content preserved
    assert "### insert-before step:cycle/file-bug" in on_disk
    # Metadata trailer appended (§7.5)
    assert "authored-by: pm-lead" in on_disk
    assert "authored-at: 2026-06-01T12:00:00+00:00" in on_disk


def test_no_tmp_file_left_behind_on_success(tmp_path):
    run, _ = _make_runner()
    l4_write_commit.write_and_commit_l4(
        role_class="worker",
        staged_l4_text=_STAGED_L4,
        op_type="append",
        target="",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="worker-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    leftover = list((tmp_path / ".squidsquad" / "project").glob("*.tmp"))
    assert leftover == []


def test_pre_existing_tmp_file_cleaned_before_write(tmp_path):
    """A crash from a prior write may leave a `.tmp`; the new write must clean it up."""
    target_dir = tmp_path / ".squidsquad" / "project"
    target_dir.mkdir(parents=True)
    stale_tmp = target_dir / "pm.md.tmp"
    stale_tmp.write_text("stale partial write from prior crash\n", encoding="utf-8")
    run, _ = _make_runner()
    l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="append",
        target="",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    assert not stale_tmp.exists()


# ---------------------------------------------------------------------------
# AC2: commit subject format
# ---------------------------------------------------------------------------

def test_commit_subject_step_targeted_op():
    subject = l4_write_commit._commit_subject(
        role_class="pm",
        slot="instructions",
        op_type="insert-before step:cycle/file-bug",
        target="step:cycle/file-bug",
    )
    assert subject == "pm: L4 write — instructions/insert-before/step:cycle/file-bug"


def test_commit_subject_append_no_target():
    subject = l4_write_commit._commit_subject(
        role_class="worker",
        slot="instructions",
        op_type="append",
        target="",
    )
    assert subject == "worker: L4 write — instructions/append"


def test_commit_subject_whole_slot_replace():
    subject = l4_write_commit._commit_subject(
        role_class="dm",
        slot="responsibility",
        op_type="replace",
        target="",
    )
    assert subject == "dm: L4 write — responsibility/replace"


def test_commit_runs_git_add_then_commit(tmp_path):
    run, calls = _make_runner()
    l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="insert-before step:cycle/file-bug",
        target="step:cycle/file-bug",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    git_subjects = [c["argv"] for c in calls]
    assert ["git", "add", "--", ".squidsquad/project/pm.md"] in git_subjects
    commit_argv = next(c for c in git_subjects if c[:2] == ["git", "commit"])
    # subject is the first -m
    assert "pm: L4 write — instructions/insert-before/step:cycle/file-bug" in commit_argv


# ---------------------------------------------------------------------------
# AC3: commit body + metadata trailer
# ---------------------------------------------------------------------------

def test_commit_body_quotes_directive_verbatim():
    body = l4_write_commit._commit_body(_DIRECTIVE)
    assert "Source directive:" in body
    # Verbatim: the directive appears unchanged inside a code fence
    assert _DIRECTIVE in body
    assert "```" in body


def test_commit_body_preserves_multiline_directive():
    multi = "Line one of directive.\nLine two adds context.\nLine three."
    body = l4_write_commit._commit_body(multi)
    # The three lines are reproduced sequentially inside the fence — no
    # per-line prefix injected between them.
    assert multi in body


def test_commit_body_preserves_directive_with_quote_prefix():
    """B2: a directive containing `> ` prefixes is not double-quoted."""
    quoted_input = "> from prior reply: do X\nand also Y"
    body = l4_write_commit._commit_body(quoted_input)
    assert "> from prior reply: do X" in body
    assert "> > from prior reply" not in body


def test_commit_body_escalates_fence_when_directive_has_backticks():
    """Fence length adapts so inner triple-backticks don't terminate the wrapper."""
    inner = "use ```python\nprint('hi')\n``` in the docs"
    body = l4_write_commit._commit_body(inner)
    # Inner has a 3-backtick run, so the outer fence must be 4+
    assert "````" in body
    assert inner in body


def test_metadata_trailer_has_required_fields():
    trailer = l4_write_commit._format_trailer(
        authored_by="pm-lead",
        generated_at=_GENERATED_AT,
        source_directive=_DIRECTIVE,
    )
    assert trailer.startswith("<!--")
    assert trailer.endswith("-->")
    assert "authored-by: pm-lead" in trailer
    assert "authored-at: 2026-06-01T12:00:00+00:00" in trailer
    assert "source-conversation:" in trailer


def test_metadata_trailer_collapses_directive_newlines_to_single_line():
    """source-conversation field is single-line per the §7.3 worked example."""
    multi = "One.\nTwo.\nThree.\n"
    trailer = l4_write_commit._format_trailer(
        authored_by="pm-lead",
        generated_at=_GENERATED_AT,
        source_directive=multi,
    )
    # The "source-conversation:" line must not have an internal newline
    sc_line = [ln for ln in trailer.splitlines() if ln.startswith("source-conversation:")][0]
    assert "\n" not in sc_line


def test_metadata_trailer_appended_after_staged_body(tmp_path):
    run, _ = _make_runner()
    l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="insert-before step:cycle/file-bug",
        target="step:cycle/file-bug",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    on_disk = (tmp_path / ".squidsquad" / "project" / "pm.md").read_text(encoding="utf-8")
    # Body precedes trailer
    body_idx = on_disk.index("### insert-before step:cycle/file-bug")
    trailer_idx = on_disk.index("<!--")
    assert body_idx < trailer_idx


# ---------------------------------------------------------------------------
# AC4: push semantics — merge-not-rebase rule honored
# ---------------------------------------------------------------------------

def test_push_uses_plain_git_push_no_rebase_no_force(tmp_path):
    run, calls = _make_runner()
    l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="append",
        target="",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    push_calls = [c["argv"] for c in calls if c["argv"][:2] == ["git", "push"]]
    assert push_calls, "git push must be invoked"
    assert push_calls[0] == ["git", "push"]
    # No --rebase or --force anywhere
    all_args = [a for c in calls for a in c["argv"]]
    assert "--rebase" not in all_args
    assert "--force" not in all_args
    assert "-f" not in all_args


# ---------------------------------------------------------------------------
# AC5: push failure → revert local commit + alert, no auto-retry
# ---------------------------------------------------------------------------

def test_push_fail_reverts_local_commit(tmp_path):
    run, calls = _make_runner(fail_command_prefix=("git", "push"))
    result = l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="append",
        target="",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    assert result.failure_stage == "push"
    assert result.pushed is False
    # `git reset --hard` invoked exactly once
    reset_calls = [c["argv"] for c in calls
                   if c["argv"][:3] == ["git", "reset", "--hard"]]
    assert len(reset_calls) == 1


def test_push_fail_resets_to_pre_commit_sha_not_head_tilde_1(tmp_path):
    """B1 hardening: revert uses the pre-commit SHA captured BEFORE phase 2,
    not the literal `HEAD~1` — safer if the working tree was dirty at entry
    so the commit accidentally bundled unrelated staged changes.
    """
    pre_sha = "1111111111111111111111111111111111111111"
    post_sha = "2222222222222222222222222222222222222222"
    rev_parse_counter = {"n": 0}
    calls = []

    def run(argv, *, cwd=None, capture_output=True, text=True, **kwargs):
        calls.append({"argv": list(argv)})
        if argv[:2] == ["git", "rev-parse"]:
            rev_parse_counter["n"] += 1
            sha = pre_sha if rev_parse_counter["n"] == 1 else post_sha
            return SimpleNamespace(returncode=0, stdout=sha + "\n", stderr="")
        if argv[:2] == ["git", "push"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="append",
        target="",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    assert result.failure_stage == "push"
    reset_calls = [c["argv"] for c in calls
                   if c["argv"][:3] == ["git", "reset", "--hard"]]
    assert reset_calls == [["git", "reset", "--hard", pre_sha]]


def test_push_fail_falls_back_to_head_tilde_1_when_pre_sha_unknown(tmp_path):
    """If pre-commit `git rev-parse HEAD` fails (e.g. fresh repo), the revert
    still happens — but targets `HEAD~1` as the fallback.
    """
    calls = []
    rev_parse_counter = {"n": 0}

    def run(argv, *, cwd=None, capture_output=True, text=True, **kwargs):
        calls.append({"argv": list(argv)})
        if argv[:2] == ["git", "rev-parse"]:
            rev_parse_counter["n"] += 1
            # First rev-parse (pre-commit) fails; second (post-commit) succeeds
            if rev_parse_counter["n"] == 1:
                return SimpleNamespace(returncode=1, stdout="", stderr="no HEAD")
            return SimpleNamespace(returncode=0, stdout="postsha\n", stderr="")
        if argv[:2] == ["git", "push"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    result = l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="append",
        target="",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    assert result.failure_stage == "push"
    reset_calls = [c["argv"] for c in calls
                   if c["argv"][:3] == ["git", "reset", "--hard"]]
    assert reset_calls == [["git", "reset", "--hard", "HEAD~1"]]


def test_push_fail_surfaces_diagnostic(tmp_path):
    run, _ = _make_runner(fail_command_prefix=("git", "push"))
    result = l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="append",
        target="",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    assert "push failed" in result.failure_detail
    assert "simulated failure" in result.failure_detail
    assert "no automatic retry" in result.failure_detail.lower()


def test_push_fail_does_not_retry(tmp_path):
    """Per AC5: no automatic retry. The runner sees git push exactly ONCE."""
    run, calls = _make_runner(fail_command_prefix=("git", "push"))
    l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="append",
        target="",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    push_count = sum(1 for c in calls if c["argv"][:2] == ["git", "push"])
    assert push_count == 1


# ---------------------------------------------------------------------------
# AC6: atomic-replace property
# ---------------------------------------------------------------------------

def test_atomic_write_crash_simulation_leaves_no_partial_file(tmp_path):
    """Simulate a crash by raising during the write phase BEFORE os.replace.

    After the failure, the target file (if it existed prior) is unchanged
    and no partial content is visible at the final path.
    """
    target_dir = tmp_path / ".squidsquad" / "project"
    target_dir.mkdir(parents=True)
    target = target_dir / "pm.md"
    # Pre-existing L4 — must remain untouched after the failed write
    target.write_text("# Project L4 — PM\n\n(prior content)\n", encoding="utf-8")
    original = target.read_text(encoding="utf-8")

    # Monkey-patch Path.write_text on the .tmp path to raise
    real_write = Path.write_text

    def flaky_write(self, content, *args, **kwargs):
        if self.name.endswith(".md.tmp"):
            raise OSError("simulated crash mid-write")
        return real_write(self, content, *args, **kwargs)

    run, _ = _make_runner()
    import unittest.mock
    with unittest.mock.patch.object(Path, "write_text", flaky_write):
        result = l4_write_commit.write_and_commit_l4(
            role_class="pm",
            staged_l4_text=_STAGED_L4,
            op_type="append",
            target="",
            slot="instructions",
            source_directive=_DIRECTIVE,
            authored_by="pm-lead",
            target_root=tmp_path,
            generated_at=_GENERATED_AT,
            runner=run,
        )

    assert result.failure_stage == "write"
    # Target file unchanged from the prior content
    assert target.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# Commit failure path
# ---------------------------------------------------------------------------

def test_commit_fail_returns_commit_failure_stage(tmp_path):
    """git commit failure surfaces failure_stage='commit' + the diagnostic."""
    run, _ = _make_runner(fail_command_prefix=("git", "commit"))
    result = l4_write_commit.write_and_commit_l4(
        role_class="pm",
        staged_l4_text=_STAGED_L4,
        op_type="append",
        target="",
        slot="instructions",
        source_directive=_DIRECTIVE,
        authored_by="pm-lead",
        target_root=tmp_path,
        generated_at=_GENERATED_AT,
        runner=run,
    )
    assert result.failure_stage == "commit"
    assert "commit failed" in result.failure_detail


# ---------------------------------------------------------------------------
# WriteResult surface
# ---------------------------------------------------------------------------

def test_write_result_ok_property():
    assert l4_write_commit.WriteResult(pushed=True).ok is True
    assert l4_write_commit.WriteResult(failure_stage="push").ok is False

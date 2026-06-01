"""C6: atomic L4 write + commit + push with §7.5 metadata (#10655, PRD-C C6).

After all three gates pass (DS audit + mini-CQ + compose dry-run), this
module persists the staged L4 content to ``.squidsquad/project/<role-class>.md``,
commits with the §7.5-prescribed message + body + metadata trailer, and
pushes to the remote.

The write itself is atomic: write to ``<file>.tmp`` then ``os.replace()``
to the final path. Even a crash mid-write leaves the on-disk L4 file
unchanged — only the ``.tmp`` file exists, and the next write cleans it
up via ``unlink(missing_ok=True)``. The push is intentionally NOT
retried on failure; per AC5 the local commit is rolled back with
``git reset --hard HEAD~1`` and the human is surfaced with the
diagnostic so they can decide the next step.

Per §9a coexistence the write targets ``.squidsquad/project/<role-class>.md``
which v1 compose does not read — v1 output stays byte-identical (the
§9a gate confirms this regardless of L4 churn).
"""

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_L4_PROJECT_DIR = _REPO_ROOT / ".squidsquad" / "project"


@dataclass
class WriteResult:
    """Outcome of one ``write_and_commit_l4`` invocation.

    ``written`` is the absolute path to the on-disk L4 file when the
    write phase succeeded (even if push later failed and the local
    commit was reverted); ``None`` on atomic-write failure.

    ``committed_sha`` is the commit SHA when commit succeeded; ``None``
    otherwise. ``pushed`` is True iff the push to remote succeeded.

    ``failure_stage`` is one of ``"write"`` / ``"commit"`` / ``"push"``
    / ``""`` (empty on full success); callers branch on this to render
    stage-specific human guidance.

    ``failure_detail`` is the diagnostic surfaced to the human verbatim
    when ``failure_stage`` is non-empty.
    """

    written: Path | None = None
    committed_sha: str | None = None
    pushed: bool = False
    failure_stage: str = ""
    failure_detail: str = ""

    @property
    def ok(self):
        return self.failure_stage == ""


def write_and_commit_l4(
    *,
    role_class,
    staged_l4_text,
    op_type,
    target,
    slot,
    source_directive,
    authored_by,
    target_root=None,
    generated_at=None,
    runner=None,
):
    """Atomic-write L4 + commit + push. Returns :class:`WriteResult`.

    Per AC1 the write is atomic: ``<file>.tmp`` + ``os.replace``. Per AC2
    the commit subject is ``<role-class>: L4 write — <slot>/<op-type>/<target>``.
    Per AC3 the commit body quotes the source directive verbatim and
    includes the §7.5 HTML-comment metadata trailer. Per AC4 the push
    honors the merge-not-rebase rule (no ``--rebase``, no ``--force``).
    Per AC5 a push failure reverts the local commit and surfaces the
    diagnostic; never automatically retried.

    ``runner`` is an optional injected callable matching the
    :func:`subprocess.run` signature — tests pass a stub so the suite
    runs without git. ``generated_at`` accepts an explicit
    :class:`datetime` for deterministic metadata-trailer testing.
    ``target_root`` overrides ``REPO_ROOT`` so tests can drive the
    write into a tmp_path.
    """
    if target_root is None:
        target_root = _REPO_ROOT
    target_root = Path(target_root)
    if runner is None:
        runner = subprocess.run
    if generated_at is None:
        generated_at = datetime.now(timezone.utc)

    target_file = target_root / ".squidsquad" / "project" / f"{role_class}.md"

    # Phase 1 — atomic write. The .tmp file path lives in the same
    # directory as the target so os.replace is atomic on every common
    # filesystem (POSIX + Windows). Cleanup any leftover .tmp from a
    # prior crash before writing the new one.
    try:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_file.with_suffix(target_file.suffix + ".tmp")
        tmp_path.unlink(missing_ok=True)
        tmp_path.write_text(_apply_metadata_trailer(
            staged_l4_text, authored_by=authored_by,
            generated_at=generated_at, source_directive=source_directive,
        ), encoding="utf-8")
        os.replace(tmp_path, target_file)
    except OSError as e:
        return WriteResult(
            failure_stage="write",
            failure_detail=f"atomic write failed for {target_file}: {e}",
        )

    # Phase 2 — git commit. Stage just the L4 file (never -A or .).
    # Capture pre-commit SHA so the push-fail revert path targets an
    # explicit commit rather than relying on HEAD~1 — defends against the
    # case where the working tree was dirty at entry and `git commit`
    # accidentally included unrelated staged changes.
    pre_commit_sha = _resolve_head_sha(runner, target_root)
    subject = _commit_subject(role_class, slot, op_type, target)
    body = _commit_body(source_directive)
    relative = target_file.relative_to(target_root).as_posix()
    add_result = runner(
        ["git", "add", "--", relative],
        cwd=str(target_root), capture_output=True, text=True,
    )
    if add_result.returncode != 0:
        return WriteResult(
            written=target_file,
            failure_stage="commit",
            failure_detail=f"git add failed: {add_result.stderr.strip() or add_result.stdout.strip()}",
        )
    commit_result = runner(
        ["git", "commit", "-m", subject, "-m", body],
        cwd=str(target_root), capture_output=True, text=True,
    )
    if commit_result.returncode != 0:
        return WriteResult(
            written=target_file,
            failure_stage="commit",
            failure_detail=f"git commit failed: {commit_result.stderr.strip() or commit_result.stdout.strip()}",
        )
    sha = _resolve_head_sha(runner, target_root)

    # Phase 3 — push. Plain `git push` (no --rebase, no --force) per AC4.
    push_result = runner(
        ["git", "push"],
        cwd=str(target_root), capture_output=True, text=True,
    )
    if push_result.returncode != 0:
        # AC5: revert local commit, surface diagnostic, do NOT retry.
        # Reset to the explicit pre-commit SHA when known — safer than
        # HEAD~1 if anything else landed between phases.
        revert_target = pre_commit_sha if pre_commit_sha else "HEAD~1"
        runner(
            ["git", "reset", "--hard", revert_target],
            cwd=str(target_root), capture_output=True, text=True,
        )
        return WriteResult(
            written=target_file,
            committed_sha=sha,
            pushed=False,
            failure_stage="push",
            failure_detail=(
                f"git push failed: {push_result.stderr.strip() or push_result.stdout.strip()}. "
                f"Local commit {sha[:8] if sha else '?'} reverted via "
                f"`git reset --hard {revert_target[:8] if revert_target != 'HEAD~1' else revert_target}`. "
                f"Operator decides next step — no automatic retry."
            ),
        )

    return WriteResult(written=target_file, committed_sha=sha, pushed=True)


def _commit_subject(role_class, slot, op_type, target):
    """Format AC2 commit subject: ``<role-class>: L4 write — <slot>/<op-type>/<target>``.

    The op-type token uses just the op verb (``append`` / ``replace`` /
    ``insert-before`` / ``insert-after``); the step-id target (when present)
    goes in the ``<target>`` slot. Empty target renders without the
    trailing ``/<target>``.
    """
    op_verb = op_type.split()[0] if op_type else ""
    if target:
        return f"{role_class}: L4 write — {slot}/{op_verb}/{target}"
    return f"{role_class}: L4 write — {slot}/{op_verb}"


def _commit_body(source_directive):
    """Format AC3 commit body: quote the human directive verbatim.

    Verbatim means the human's message is reproduced unchanged inside a
    fenced code block so ``git log`` readers see exactly what was said —
    including directives that themselves contain ``>`` quote prefixes,
    backticks, or other markdown that a line-prefix quoter would mangle.
    Uses a fence length that adapts if the directive embeds backticks of
    its own (so the fence is always longer than the longest inner run).
    """
    longest_run = 0
    run = 0
    for ch in source_directive:
        if ch == "`":
            run += 1
            longest_run = max(longest_run, run)
        else:
            run = 0
    fence = "`" * max(3, longest_run + 1)
    return f"Source directive:\n\n{fence}\n{source_directive.rstrip()}\n{fence}\n"


def _apply_metadata_trailer(staged_text, *, authored_by, generated_at,
                             source_directive):
    """Append the §7.5 HTML-comment metadata trailer to the staged text.

    The trailer follows the last H3 op block so ``git blame`` on the L4
    file attributes the op to the writing agent. Files accumulate one
    trailer per H3 op over time, mirroring the §7.3 worked example in
    COMPOSE-ARCHITECTURE.md.
    """
    trailer = _format_trailer(
        authored_by=authored_by,
        generated_at=generated_at,
        source_directive=source_directive,
    )
    return staged_text.rstrip() + "\n\n" + trailer + "\n"


def _format_trailer(*, authored_by, generated_at, source_directive):
    """Build the literal §7.5 trailer text.

    Sanitizes ``source-conversation`` to a single line by replacing
    newlines with ``\\n`` escapes — the §7.3 worked example uses single-
    line trailer values for readability in ``git log -p`` output.
    """
    single_line = source_directive.replace("\n", " ").replace("\r", " ").strip()
    iso = generated_at.isoformat(timespec="seconds")
    return (
        f"<!--\n"
        f"authored-by: {authored_by}\n"
        f"authored-at: {iso}\n"
        f"source-conversation: {single_line}\n"
        f"-->"
    )


def _resolve_head_sha(runner, target_root):
    """Resolve HEAD's SHA via ``git rev-parse HEAD``. Returns None on failure."""
    result = runner(
        ["git", "rev-parse", "HEAD"],
        cwd=str(target_root), capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None

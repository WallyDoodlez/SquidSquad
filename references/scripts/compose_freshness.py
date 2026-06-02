"""E1: Harness boot-time compose-freshness check (#10680, PRD-E E1).

Layer 1 of the compose-freshness chain. The harness runs this check
ONCE at boot, BEFORE spawning any agent — per PRD-E §8.1's "primary
gate" rule. The check:

1. Computes a deterministic SHA256 over the compose-input source tree
   (``compute_compose_checksum``).
2. Compares against the ``last_compose_checksum`` field that E2
   (#10681) plumbed into ``.harness-state.json``.
3. On drift OR first boot OR missing checksum: runs
   ``compose.py deploy-all`` and stores the post-compose checksum.
4. On compose failure: returns ``status="failed"`` per AC4. The caller
   (the harness lifespan) MUST refuse to spawn agents — no fall-back
   to last-known-good, no degraded boot.

The module exposes pure functions so unit tests drive the logic
directly without spinning up FastAPI or watchdog; the harness owns
the wiring + the spawn-refusal flag (see ``harness._deferred_init``).

Per AC5 the post-compose checksum is the NEW hash of the source tree
AFTER ``compose.py deploy-all`` writes its outputs — those outputs
land outside the checksumed input set (in ``.squidsquad/<alias>/``)
so the post-compose source-tree checksum equals the pre-compose one
unless the operator concurrently edited a source file. We re-checksum
the inputs to capture that race correctly.
"""

import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# AC2: file sets that contribute to the checksum. Listed by repo-rooted
# glob shape. Globs are evaluated against ``repo_root`` at check time.
# The ordering is informational; ``compute_compose_checksum`` sorts the
# resolved paths deterministically before hashing.
#
# Note: ``references/sub-skills/**/*.md`` already covers
# ``references/sub-skills/manifest.md`` since the ``**`` segment matches
# zero or more intermediate directories. No separate entry for
# manifest.md — listing it twice would double-hash the file and create
# a regression-risk surface if a later cleanup removes the duplicate
# (per DS-10680 review F2).
COMPOSE_INPUT_GLOBS = (
    # Per-install config — affects which aliases compose deploys and
    # which manifest each role-class reads (post-D5/D6 unification).
    ".squidsquad/config.md",
    # L4 project-local layer — every role-class's overlay file.
    ".squidsquad/project/*.md",
    # L1 sub-skill bodies — common + common-events + per-role —
    # AND the top-level ``manifest.md`` (``**`` matches zero dirs).
    "references/sub-skills/**/*.md",
    # L1-L3 source files — base roles + per-role-class subdirs +
    # variant subdirs (worker/skill etc.).
    "references/roles/**/*",
)


@dataclass
class FreshnessResult:
    """Outcome of one ``check_and_repair`` invocation.

    ``status`` is one of:

    - ``"clean"`` — source-tree checksum matches the stored value; no
      compose ran. Caller proceeds with normal boot.
    - ``"repaired"`` — drift / first boot / missing checksum; compose
      ran successfully and the stored checksum was updated.
    - ``"failed"`` — compose itself failed. Per AC4 the caller MUST
      refuse to spawn agents until the operator resolves the source
      issue; no fall-back.

    ``new_checksum`` carries the post-compose checksum when
    ``status == "repaired"`` (the value the caller persists). On
    ``"clean"`` it equals the input ``stored_checksum``. On
    ``"failed"`` it is empty — nothing was persisted.

    ``diagnostic`` is a one-line operator-readable message; safe to
    print to stderr or log file. ``compose_stderr`` holds the
    compose subprocess's stderr (capped) when ``status == "failed"``
    so the operator can see what broke without re-running compose.
    """

    status: str
    new_checksum: str = ""
    diagnostic: str = ""
    compose_stderr: str = ""


# Cap compose stderr captured into ``FreshnessResult.compose_stderr``
# so a 10 MB pyyaml traceback doesn't balloon the log line.
_COMPOSE_STDERR_MAX = 4000


def iter_compose_input_files(repo_root):
    """Yield every file path that contributes to the checksum.

    Public API per DS-10683 F2 (used by ``squidsquad_cli.cmd_check``'s
    drift report). The leading-underscore private name still exists
    as an alias below for backwards compatibility with any pre-#10683
    importer.

    Resolution: each glob in ``COMPOSE_INPUT_GLOBS`` is expanded
    against ``repo_root``. Symlinks are followed only one level
    (``glob`` semantics); directories produced by ``**/*`` are
    filtered to files only. Paths are returned as ``Path`` objects
    rooted at ``repo_root``.

    Stable ordering is the caller's concern — this iterator yields
    in glob-resolution order which is implementation-defined.
    """
    repo_root = Path(repo_root)
    for pattern in COMPOSE_INPUT_GLOBS:
        for path in repo_root.glob(pattern):
            if path.is_file():
                yield path


# Backwards-compat alias for any pre-#10683 importer.
_iter_compose_input_files = iter_compose_input_files


def compute_compose_checksum(repo_root):
    """Return a deterministic SHA256 over the compose-input set.

    Algorithm (per AC2 "deterministic SHA256 over sorted file paths +
    contents"):

    1. Enumerate every file matching ``COMPOSE_INPUT_GLOBS`` under
       ``repo_root``.
    2. Sort by repo-relative POSIX path so the order is platform-
       independent.
    3. For each file, hash the path bytes + a separator + the file
       contents into the running SHA256. Including the path in the
       hash ensures a rename surfaces as drift even if the contents
       moved verbatim.
    4. Return the hex digest.

    Files that disappear between enumeration and read are silently
    skipped — racing the file-watch is not the gate's failure mode;
    a missing source file shows up as a compose error a moment later.
    """
    repo_root = Path(repo_root)
    h = hashlib.sha256()
    rel_paths = []
    seen = set()
    for path in _iter_compose_input_files(repo_root):
        try:
            rel = path.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        # Per DS-10680 review F2: dedup so any future glob-overlap
        # never double-hashes a file. The single-glob layout today
        # makes this defensive — if a maintainer re-adds an explicit
        # entry that overlaps ``**/*.md``, the hash stays stable.
        if rel in seen:
            continue
        seen.add(rel)
        rel_paths.append((rel, path))
    rel_paths.sort(key=lambda t: t[0])
    for rel, path in rel_paths:
        try:
            content = path.read_bytes()
        except OSError:
            continue
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(content)
        h.update(b"\x00")
    return h.hexdigest()


def _default_compose_runner(repo_root):
    """Shell out to ``compose.py deploy-all`` and return
    ``(returncode, stdout, stderr)``.

    Caller-injectable via ``check_and_repair(..., runner=...)`` so
    unit tests drive without spawning a Python subprocess.
    """
    cmd = [
        sys.executable,
        str(Path(repo_root) / "references" / "scripts" / "compose.py"),
        "deploy-all",
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(repo_root),
        env={**os.environ},
    )
    return proc.returncode, proc.stdout, proc.stderr


def check_and_repair(
    *,
    repo_root,
    stored_checksum,
    runner=None,
    compute_checksum=None,
):
    """Run the E1 freshness check + repair sequence.

    Returns a :class:`FreshnessResult`. Pure orchestration — does NOT
    write the state file or set any harness flag. The caller (harness
    lifespan) persists the ``new_checksum`` via
    ``HarnessState.set_last_compose_checksum`` on ``"repaired"`` and
    enforces the spawn-refusal contract on ``"failed"``.

    ``stored_checksum`` is the value read from ``.harness-state.json``
    via ``HarnessState.get_last_compose_checksum`` — ``None`` (or
    empty string) indicates first boot or a legacy state file, both
    of which trigger compose per AC3.

    ``runner`` and ``compute_checksum`` are injection seams for tests.
    """
    if compute_checksum is None:
        compute_checksum = compute_compose_checksum
    if runner is None:
        runner = _default_compose_runner

    current = compute_checksum(repo_root)

    if stored_checksum and current == stored_checksum:
        return FreshnessResult(
            status="clean",
            new_checksum=current,
            diagnostic="compose inputs unchanged since last boot",
        )

    # Drift / first boot / missing checksum — repair.
    try:
        returncode, _stdout, stderr = runner(repo_root)
    except Exception as exc:  # noqa: BLE001 — defensive against runner bugs
        return FreshnessResult(
            status="failed",
            new_checksum="",
            diagnostic=(
                f"compose runner raised: {exc!r}. Harness will NOT "
                f"spawn agents until the operator resolves this."
            ),
            compose_stderr="",
        )
    if returncode != 0:
        truncated = (stderr or "")[:_COMPOSE_STDERR_MAX]
        return FreshnessResult(
            status="failed",
            new_checksum="",
            diagnostic=(
                f"compose.py deploy-all exited non-zero ({returncode}). "
                f"Harness will NOT spawn agents until the source issue "
                f"is fixed. See compose_stderr for details."
            ),
            compose_stderr=truncated,
        )

    # Re-checksum AFTER compose succeeded — see module docstring re:
    # the operator-concurrent-edit race.
    post_checksum = compute_checksum(repo_root)
    diagnostic = (
        "first boot — checksum stored"
        if not stored_checksum
        else "drift detected — compose ran cleanly"
    )
    return FreshnessResult(
        status="repaired",
        new_checksum=post_checksum,
        diagnostic=diagnostic,
    )

"""Gate 3: compose dry-run via A4.5 staged --check (#10654, PRD-C C5).

After Gate 2 (mini-CQ) approves, ``l4-curation`` writes the proposed L4
file to a temp path and invokes the per-alias staged-content check
``compose.py deploy <alias> --check --staged-l4 <tmp>`` for EVERY alias
of the affected role-class. Any failure aborts the write.

This module wraps the per-alias dispatch + result aggregation. The
underlying validation work was done by A4.5 (#10395) which exposes
``compose.check_alias_staged_l4`` for in-process callers; this module
calls THAT directly rather than subprocessing the CLI so the audit
runs in the agent's process.

The staged L4 file is written to ``.squidsquad/tmp/l4-dryrun/`` so it
stays inside the model_router sandbox boundary (the lesson #10444 left
us with: every Python helper that touches inputs the router will see
must keep the path under REPO_ROOT). Even though Gate 3 does not
itself call the router, keeping tempfiles under REPO_ROOT prevents the
audit trail from referencing system paths.
"""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DRYRUN_TMP_ROOT = _REPO_ROOT / ".squidsquad" / "tmp" / "l4-dryrun"


@dataclass
class DryrunFailure:
    """One alias's failure during the staged-content dry-run.

    ``rule`` is the R1-R7 label when A4.5 returns a
    :class:`LinkStageValidationError`; otherwise ``"<setup>"`` for
    setup errors (missing alias, missing staged file, parse failure)
    or ``"<other>"`` for any unexpected exception.

    ``detail`` is the diagnostic surfaced verbatim to the human per
    AC2 ("Dry-run failed: <reason>").
    """

    alias: str
    rule: str
    detail: str


@dataclass
class DryrunResult:
    """Outcome of dispatching the staged-content dry-run to every alias.

    ``passed`` is ``True`` iff EVERY alias passes (per AC3). Even one
    failure trips this to ``False`` and ``failures`` records each alias
    that failed (so callers can render a list to the human when more
    than one alias is broken — e.g. an L4 op that targets a step which
    exists in one variant but not another).
    """

    passed: bool
    failures: list = field(default_factory=list)


def dryrun_l4(
    staged_l4_text,
    role_class,
    *,
    target_root=None,
    registry=None,
    check_alias_staged_l4_fn=None,
):
    """Stage ``staged_l4_text`` to a tempfile + run A4.5 check for every alias of ``role_class``.

    Returns :class:`DryrunResult`. Never raises — every failure mode
    (validation, setup, unexpected exception) is captured into the
    result so the caller can branch cleanly per AC2/AC3.

    Per AC4 the staged file is NOT written over the on-disk L4. The
    function writes the staged content to a tempfile under
    ``.squidsquad/tmp/l4-dryrun/`` and passes its path as the
    ``--staged-l4`` argument; A4.5's helper uses this for the specified
    alias while the on-disk L4 (the live file) is what the OTHER
    aliases of the role-class still read at the same compose run. We
    test the cross-alias-validation property by running the staged
    check once per alias against the same tempfile (the OTHER aliases
    of the role-class share the L4 file, but each alias still resolves
    via A2d's walk against the same staged text — A4.5's call shape).

    Injection seams:
    - ``target_root``: where the staged file's parent directory lives
      (defaults to ``REPO_ROOT``). Tests pass a tmp_path.
    - ``registry``: pre-parsed alias registry. When omitted, the
      A4.5 helper resolves it from ``.squidsquad/config.md`` via
      ``parse_aliases_registry``.
    - ``check_alias_staged_l4_fn``: stub for tests so the suite can
      simulate per-alias pass/fail without running the full link
      stage. Defaults to ``compose.check_alias_staged_l4``.
    """
    if check_alias_staged_l4_fn is None:
        import compose as _compose
        check_alias_staged_l4_fn = _compose.check_alias_staged_l4
    if registry is None:
        from config import parse_aliases_registry
        registry = parse_aliases_registry()

    aliases_for_role = [
        alias for alias, (rc, _l3) in registry.items() if rc == role_class
    ]
    if not aliases_for_role:
        return DryrunResult(
            passed=False,
            failures=[DryrunFailure(
                alias="<none>",
                rule="<setup>",
                detail=(
                    f"no aliases of role-class `{role_class}` in the install's "
                    f"`## Aliases` registry; nothing to dry-run against. "
                    f"Confirm the role-class is in `.squidsquad/config.md` "
                    f"before retrying."
                ),
            )],
        )

    _DRYRUN_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"dryrun-{role_class}-",
                                     dir=str(_DRYRUN_TMP_ROOT)) as td:
        staged_path = Path(td) / f"{role_class}.staged.md"
        staged_path.write_text(staged_l4_text, encoding="utf-8")

        failures = []
        for alias in aliases_for_role:
            failure = _dryrun_one_alias(
                alias=alias,
                staged_path=staged_path,
                target_root=target_root,
                registry=registry,
                check_fn=check_alias_staged_l4_fn,
            )
            if failure is not None:
                failures.append(failure)

    if failures:
        return DryrunResult(passed=False, failures=failures)
    return DryrunResult(passed=True)


def _dryrun_one_alias(*, alias, staged_path, target_root, registry, check_fn):
    """Invoke A4.5's helper for one alias. Return ``DryrunFailure`` or ``None``."""
    # Late import so test stubs don't have to install A4.5 dependencies
    # to use the injection seam.
    try:
        from link_stage_validator import LinkStageValidationError
    except ImportError:
        LinkStageValidationError = ValueError  # noqa: N806 — fallback for test stubs

    try:
        check_fn(alias, staged_path, target_root=target_root, registry=registry)
    except LinkStageValidationError as e:
        return DryrunFailure(
            alias=alias,
            rule=getattr(e, "rule", "<validation>"),
            detail=str(e),
        )
    except (FileNotFoundError, KeyError) as e:
        # Setup-class errors per A4.5 contract: missing alias, missing
        # staged file, registry resolution fault.
        return DryrunFailure(
            alias=alias,
            rule="<setup>",
            detail=str(e),
        )
    except Exception as e:  # noqa: BLE001 — anything else is a Gate 3 abort
        return DryrunFailure(
            alias=alias,
            rule="<other>",
            detail=f"{type(e).__name__}: {e}",
        )
    return None


def format_failure_for_human(result):
    """Render the failures in :class:`DryrunResult` as one human-facing string.

    Matches the AC2 phrasing ("Dry-run failed: <reason>") and handles
    the multi-alias case by enumerating each alias's failure on its
    own line. Returns the empty string when the result passed (callers
    branch on ``passed``; this helper exists for the surface step).
    """
    if result.passed:
        return ""
    if len(result.failures) == 1:
        f = result.failures[0]
        return f"Dry-run failed for alias `{f.alias}`: [{f.rule}] {f.detail}"
    lines = [f"Dry-run failed for {len(result.failures)} alias(es):"]
    for f in result.failures:
        lines.append(f"  - `{f.alias}`: [{f.rule}] {f.detail}")
    return "\n".join(lines)

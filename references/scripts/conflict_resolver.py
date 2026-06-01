"""Higher-L-wins conflict resolver (#10446, PRD-B Story B5).

Per COMPOSE-ARCHITECTURE §4.6 the assemble pass collapses layered prose
into one coherent voice with **higher-L wins** precedence (L4 > L3 > L2
> L1). The LLM does the rewrite; B5 verifies it did the job:

- For every ``Conflict`` record from B4, the lower-layer ``loser_quote``
  must NOT appear in the final assembled body (the lower-L prose was
  dropped — recorded in ``CLAUDE.conflicts.md`` for audit, NOT carried
  into runtime).
- The assembled body should still satisfy B2's preservation pass and
  B3's length-floor + code-block-parity checks against the linked input
  AFTER the resolver runs.

B5 is pure verification — no rewriting. When the LLM fails to honor the
precedence rule, the resolver raises ``ResolverError`` so B7's atomic-
write contract can route to the abort path (zero partial artifacts on
preservation-fail per §4.6).
"""

from dataclasses import dataclass

# Late-imported in re_verify_preservation so the resolver module stays
# loadable even if the assemble_verifier surface changes shape later.
# (B2 and B3 ship in the same module.)


@dataclass
class ResolverIssue:
    """One unresolved conflict detected by ``verify_higher_l_wins``."""

    conflict_index: int  # 1-based, matches CONFLICT-NNN in the report
    slot: str
    loser_layer: str
    winner_layer: str
    detail: str  # human-readable description of the violation


class ResolverError(ValueError):
    """Raised when the resolver detects a higher-L-wins violation.

    Carries ``issues`` (list[ResolverIssue]) so B7's caller can render
    a precise diagnostic before aborting. The first issue is included
    in the str() message for the common single-violation case.
    """

    def __init__(self, issues):
        self.issues = list(issues)
        first = self.issues[0] if self.issues else None
        if first is None:
            super().__init__("higher-L-wins violation (no issue details)")
        else:
            super().__init__(
                f"higher-L-wins violation: CONFLICT-{first.conflict_index:03d} "
                f"(slot={first.slot}, precedence={first.winner_layer}>{first.loser_layer}): "
                f"{first.detail}"
            )


def verify_higher_l_wins(assembled_body, conflicts, *, raise_on_issue=False):
    """Verify each Conflict's loser_quote is absent from the assembled body.

    Returns a list of :class:`ResolverIssue` records (empty when clean).
    When ``raise_on_issue=True`` and the list is non-empty, raises
    :class:`ResolverError`.

    Empty / whitespace-only loser quotes are skipped — they convey no
    actionable check (the LLM emitted a placeholder, B7's audit-gap
    logic owns that). The match is whitespace-insensitive: each
    whitespace run is normalized to a single space before substring
    comparison, so cosmetic reformatting of long quotes doesn't cause
    false negatives.
    """
    issues = []
    normalized_body = _normalize_whitespace(assembled_body)
    for idx, conflict in enumerate(conflicts, start=1):
        loser = (conflict.loser_quote or "").strip()
        if not loser:
            continue
        if _normalize_whitespace(loser) in normalized_body:
            issues.append(ResolverIssue(
                conflict_index=idx,
                slot=conflict.slot,
                loser_layer=conflict.loser_layer,
                winner_layer=conflict.winner_layer,
                detail=(
                    f"lower-layer prose still present in assembled body: "
                    f"{loser[:120]!r}"
                ),
            ))
    if issues and raise_on_issue:
        raise ResolverError(issues)
    return issues


def re_verify_preservation(assembled_body, linked_body):
    """Re-run B2 + B3 against the assembled body. Returns a ``ReVerifyResult``.

    Per #10446 AC: "Re-verification after resolver runs (the conflict
    report still satisfies B2/B3 preservation checks against the linked
    input)". Re-running here lets B7 short-circuit the atomic-write
    contract if the LLM degraded the body during the rewrite.
    """
    # Imported lazily so this module loads in environments where
    # assemble_verifier isn't on the path (e.g. early unit tests).
    from assemble_verifier import (  # noqa: WPS433
        verify_preservation,
        check_length_floor,
        check_code_block_parity,
    )
    preservation = verify_preservation(linked_body, assembled_body)
    floor_ok = check_length_floor(linked_body, assembled_body)
    parity_ok = check_code_block_parity(linked_body, assembled_body)
    return ReVerifyResult(
        preservation_ok=preservation.ok,
        preservation=preservation,
        length_floor_ok=floor_ok,
        code_block_parity_ok=parity_ok,
    )


@dataclass
class ReVerifyResult:
    """Outcome of ``re_verify_preservation`` — one boolean per B2/B3 check."""

    preservation_ok: bool
    preservation: object  # PreservationResult from B2 (kept for diagnostics)
    length_floor_ok: bool
    code_block_parity_ok: bool

    @property
    def all_ok(self):
        return (
            self.preservation_ok
            and self.length_floor_ok
            and self.code_block_parity_ok
        )


def resolve(assembled_body, conflicts, linked_body):
    """One-call resolver: verify higher-L-wins + re-verify B2/B3 preservation.

    Returns ``(resolver_issues, reverify_result)``. The caller (B7) inspects
    both — any non-empty ``resolver_issues`` OR any False boolean on
    ``reverify_result`` is a preservation-fail per §4.6 and aborts the
    write.
    """
    issues = verify_higher_l_wins(assembled_body, conflicts)
    reverify = re_verify_preservation(assembled_body, linked_body)
    return issues, reverify


def _normalize_whitespace(text):
    """Collapse all runs of whitespace to a single space.

    Used to make substring checks robust against cosmetic reformatting
    of long verbatim quotes between linked input and assembled output.
    """
    return " ".join(text.split())

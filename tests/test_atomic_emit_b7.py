"""Tests for references/scripts/atomic_emit.py (#10447, PRD-B Story B7)."""

import os
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import atomic_emit as ae  # noqa: E402
from conflict_detector import Conflict  # noqa: E402
from conflict_resolver import ReVerifyResult, ResolverIssue  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers — minimal linked composite + stub injection seams
# ---------------------------------------------------------------------------

_LINKED_COMPOSITE = (
    "## Identity\n\n"
    "Base identity prose.\n\n"
    "## Responsibility\n\n"
    "Worker is responsible for implementation.\n\n"
    "## Soul\n\n"
    "Base soul prose.\n\n"
    "## Instructions\n\n"
    "### step:cycle/boot\n→ run sub-skill: boot-bootstrap\nBoot body.\n\n"
    "### step:cycle/work\n→ run sub-skill: triage-issues\nWork body.\n\n"
    "## Project Context\n\n"
    "Project context body (verbatim slot).\n\n"
    "## Vault\n\n"
    "Vault body (verbatim slot).\n"
)


def _ok_preservation():
    """Stand-in for B2's PreservationResult.ok=True."""
    class _PR:
        ok = True
        missing_sub_skills = []
        extra_sub_skills = []
        missing_step_ids = []
        extra_step_ids = []
    return _PR()


def _all_ok_reverify():
    return ReVerifyResult(
        preservation_ok=True,
        preservation=_ok_preservation(),
        length_floor_ok=True,
        code_block_parity_ok=True,
    )


def _stubs(*, assembled="ASSEMBLED\n", conflicts=None, issues=None, reverify=None,
            report="# Compose Conflict Report — worker\nTotal conflicts resolved: 0\n"):
    """Build a dict of injection seams returning canned results."""
    conflicts = conflicts if conflicts is not None else []
    issues = issues if issues is not None else []
    reverify = reverify if reverify is not None else _all_ok_reverify()

    def assemble_slot_fn(slot, linked_body):
        return f"<{slot} llm output>"

    def parse_output_fn(llm_output):
        return assembled, conflicts

    def resolve_fn(body, conflicts_arg, linked_body):
        return issues, reverify

    def emit_report_fn(conflicts_arg, *, role_class, model_id="<unknown>",
                       commit_sha="<unknown>", generated_at=None):
        return report

    return dict(
        assemble_slot_fn=assemble_slot_fn,
        parse_output_fn=parse_output_fn,
        resolve_fn=resolve_fn,
        emit_report_fn=emit_report_fn,
    )


# ---------------------------------------------------------------------------
# AC: atomic write of triple via .tmp + rename
# ---------------------------------------------------------------------------

def test_success_writes_all_three_files(tmp_path):
    paths = ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        **_stubs(),
    )
    assert all(p.exists() for p in paths)
    names = {p.name for p in paths}
    # PRD-B B9 (#10763 AC2 + AC3): default filename_suffix=".v2.md"
    # so the triple lands at the §9a-safe v2 paths. v1 paths are only
    # written when the caller explicitly passes filename_suffix="".
    assert names == {"CLAUDE.v2.md", "CLAUDE.linked.v2.md", "CLAUDE.conflicts.v2.md"}


def test_success_no_tmp_files_remain(tmp_path):
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker", **_stubs(),
    )
    leftover = list(tmp_path.glob("*.tmp"))
    assert leftover == [], f"unexpected .tmp leftovers: {leftover}"


def test_success_claude_linked_md_equals_input(tmp_path):
    """The linked artifact is the input composite verbatim."""
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker", **_stubs(),
    )
    on_disk = (tmp_path / "CLAUDE.linked.v2.md").read_text(encoding="utf-8")
    assert on_disk == _LINKED_COMPOSITE


def test_success_claude_md_contains_six_h2_sections_in_order(tmp_path):
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker", **_stubs(),
    )
    claude = (tmp_path / "CLAUDE.v2.md").read_text(encoding="utf-8")
    h2 = [ln for ln in claude.splitlines() if ln.startswith("## ")]
    assert h2 == [
        "## Identity",
        "## Responsibility",
        "## Soul",
        "## Instructions",
        "## Project Context",
        "## Vault",
    ]


def test_success_verbatim_slots_carry_linked_body_through(tmp_path):
    """project-context + vault skip assemble_slot — linked body becomes assembled body."""
    seen_slots = []

    def assemble_slot_fn(slot, linked_body):
        seen_slots.append(slot)
        return f"<{slot} llm output>"

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker", **stubs,
    )
    assert "project-context" not in seen_slots
    assert "vault" not in seen_slots
    # The other four slots were dispatched.
    assert set(seen_slots) == {"identity", "responsibility", "soul", "instructions"}


# ---------------------------------------------------------------------------
# AC: failure modes from §4.6 table
# ---------------------------------------------------------------------------

def test_llm_error_aborts_and_writes_nothing(tmp_path):
    def boom(slot, linked_body):
        raise RuntimeError("model unreachable")

    stubs = _stubs()
    stubs["assemble_slot_fn"] = boom
    with pytest.raises(ae.LLMError) as exc:
        ae.assemble_and_emit(
            _LINKED_COMPOSITE, tmp_path, role_class="worker", **stubs,
        )
    assert "model unreachable" in str(exc.value)
    assert list(tmp_path.iterdir()) == []  # AC: zero partial artifacts


def test_preservation_fail_aborts_and_writes_nothing(tmp_path):
    bad_preservation = ReVerifyResult(
        preservation_ok=False,
        preservation=_ok_preservation(),  # the .missing_* lists are part of str()
        length_floor_ok=True,
        code_block_parity_ok=True,
    )
    stubs = _stubs(reverify=bad_preservation)
    with pytest.raises(ae.PreservationFail):
        ae.assemble_and_emit(
            _LINKED_COMPOSITE, tmp_path, role_class="worker", **stubs,
        )
    assert list(tmp_path.iterdir()) == []


def test_length_floor_fail_aborts(tmp_path):
    bad = ReVerifyResult(
        preservation_ok=True, preservation=_ok_preservation(),
        length_floor_ok=False, code_block_parity_ok=True,
    )
    stubs = _stubs(reverify=bad)
    with pytest.raises(ae.FloorParityFail) as exc:
        ae.assemble_and_emit(
            _LINKED_COMPOSITE, tmp_path, role_class="worker", **stubs,
        )
    assert "length_floor_ok=False" in str(exc.value)
    assert list(tmp_path.iterdir()) == []


def test_code_block_parity_fail_aborts(tmp_path):
    bad = ReVerifyResult(
        preservation_ok=True, preservation=_ok_preservation(),
        length_floor_ok=True, code_block_parity_ok=False,
    )
    stubs = _stubs(reverify=bad)
    with pytest.raises(ae.FloorParityFail) as exc:
        ae.assemble_and_emit(
            _LINKED_COMPOSITE, tmp_path, role_class="worker", **stubs,
        )
    assert "code_block_parity_ok=False" in str(exc.value)
    assert list(tmp_path.iterdir()) == []


def test_precedence_violation_aborts(tmp_path):
    """B5 issues -> PrecedenceViolation."""
    issues = [
        ResolverIssue(
            conflict_index=1,
            slot="instructions",
            loser_layer="L2",
            winner_layer="L4",
            detail="loser still present",
        )
    ]
    stubs = _stubs(issues=issues)
    with pytest.raises(ae.PrecedenceViolation) as exc:
        ae.assemble_and_emit(
            _LINKED_COMPOSITE, tmp_path, role_class="worker", **stubs,
        )
    assert "CONFLICT-001" in str(exc.value)
    assert "L4>L2" in str(exc.value)
    assert list(tmp_path.iterdir()) == []


def test_link_stage_fail_aborts_without_dispatching_llm(tmp_path):
    """A composite with no canonical H2 headings is the link stage's fault."""
    bad_composite = "no headings here, just prose\n"
    called = {"llm": 0}

    def assemble_slot_fn(slot, body):
        called["llm"] += 1
        return ""

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    with pytest.raises(ae.LinkStageFail):
        ae.assemble_and_emit(
            bad_composite, tmp_path, role_class="worker", **stubs,
        )
    assert called["llm"] == 0
    assert list(tmp_path.iterdir()) == []


# ---------------------------------------------------------------------------
# AC: failure during write phase — no partial artifacts
# ---------------------------------------------------------------------------

def test_write_failure_unlinks_tmp_files_and_raises(tmp_path, monkeypatch):
    """If a .tmp write fails, all .tmp files are cleaned up before raising."""
    real_write = Path.write_text
    call_count = {"writes": 0}

    def flaky_write(self, content, *args, **kwargs):
        call_count["writes"] += 1
        if call_count["writes"] == 2:
            raise OSError("disk full simulation")
        return real_write(self, content, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky_write)

    with pytest.raises(ae.AssembleError):
        ae.assemble_and_emit(
            _LINKED_COMPOSITE, tmp_path, role_class="worker", **_stubs(),
        )
    leftover_tmp = list(tmp_path.glob("*.tmp"))
    assert leftover_tmp == [], f"tmp leftovers after write fail: {leftover_tmp}"
    final = list(tmp_path.glob("CLAUDE*.md"))
    assert final == [], f"no final files should exist: {final}"


def test_conflict_report_write_failure_raises_specific_subclass(tmp_path, monkeypatch):
    """OSError on the conflicts file specifically -> ConflictReportWriteFail."""
    real_write = Path.write_text

    def selective_fail(self, content, *args, **kwargs):
        if self.name == "CLAUDE.conflicts.v2.md.tmp":
            raise OSError(f"simulated failure on {self.name}")
        return real_write(self, content, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", selective_fail)
    with pytest.raises(ae.ConflictReportWriteFail):
        ae.assemble_and_emit(
            _LINKED_COMPOSITE, tmp_path, role_class="worker", **_stubs(),
        )
    assert list(tmp_path.glob("*.tmp")) == []
    assert list(tmp_path.glob("CLAUDE*.md")) == []


# ---------------------------------------------------------------------------
# AC: zero-conflict report still emitted with "Total conflicts resolved: 0"
# ---------------------------------------------------------------------------

def test_zero_conflicts_still_emits_report_file(tmp_path):
    """The conflicts file is always part of the triple, even when empty."""
    report_capture = {"text": None}

    def emit_report_fn(conflicts, *, role_class, model_id="<unknown>",
                       commit_sha="<unknown>", generated_at=None):
        out = (
            "# Compose Conflict Report — worker\n"
            f"Total conflicts resolved: {len(conflicts)}\n"
        )
        report_capture["text"] = out
        return out

    stubs = _stubs()
    stubs["emit_report_fn"] = emit_report_fn
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker", **stubs,
    )
    on_disk = (tmp_path / "CLAUDE.conflicts.v2.md").read_text(encoding="utf-8")
    assert "Total conflicts resolved: 0" in on_disk
    assert on_disk == report_capture["text"]


# ---------------------------------------------------------------------------
# PRD-B B9 (#10763 AC3) — filename_suffix parameter
# ---------------------------------------------------------------------------


def test_filename_suffix_default_is_v2(tmp_path):
    """Default filename_suffix is ``.v2.md`` so the triple lands at
    the §9a-safe v2 paths."""
    paths = ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker", **_stubs(),
    )
    names = sorted(p.name for p in paths)
    assert names == [
        "CLAUDE.conflicts.v2.md",
        "CLAUDE.linked.v2.md",
        "CLAUDE.v2.md",
    ]


def test_filename_suffix_empty_writes_v1_canonical_paths(tmp_path):
    """``filename_suffix=""`` is the seam the E6 V2 CUTOVER PR uses to
    atomically flip the default onto v1 canonical names. The same
    helper writes either path family with no other change."""
    paths = ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        filename_suffix="",
        **_stubs(),
    )
    names = sorted(p.name for p in paths)
    assert names == [
        "CLAUDE.conflicts.md",
        "CLAUDE.linked.md",
        "CLAUDE.md",
    ]
    # And the v2 outputs are NOT written when v1 is selected.
    assert not (tmp_path / "CLAUDE.v2.md").exists()
    assert not (tmp_path / "CLAUDE.linked.v2.md").exists()
    assert not (tmp_path / "CLAUDE.conflicts.v2.md").exists()


def test_filename_suffix_v2_does_not_write_v1_paths(tmp_path):
    """§9a coexistence check (AC2): v2 path must NEVER write v1
    canonical filenames. Operator's v1 CLAUDE.md is untouched."""
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker", **_stubs(),
    )
    assert not (tmp_path / "CLAUDE.md").exists()
    assert not (tmp_path / "CLAUDE.linked.md").exists()
    assert not (tmp_path / "CLAUDE.conflicts.md").exists()


# ---------------------------------------------------------------------------
# Multi-slot conflict aggregation
# ---------------------------------------------------------------------------

def test_aggregates_conflicts_from_multiple_slots(tmp_path):
    """Conflicts from every non-verbatim slot are aggregated into the single report."""
    seen_conflict_counts = {"all": 0}

    def parse_output_fn(llm_output):
        # Each slot's LLM output yields exactly one conflict.
        c = Conflict(
            slot=llm_output.split()[0].strip("<>"),
            winner_layer="L4", loser_layer="L2",
            winner_path="x", loser_path="y",
            winner_quote="winner", loser_quote="",  # empty so resolver skips
            why="w", resolution="r",
        )
        return "ASSEMBLED\n", [c]

    def emit_report_fn(conflicts, *, role_class, model_id="<unknown>",
                       commit_sha="<unknown>", generated_at=None):
        seen_conflict_counts["all"] = len(conflicts)
        return f"Total conflicts resolved: {len(conflicts)}\n"

    stubs = _stubs()
    stubs["parse_output_fn"] = parse_output_fn
    stubs["emit_report_fn"] = emit_report_fn
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker", **stubs,
    )
    # 4 non-verbatim slots × 1 conflict each = 4.
    assert seen_conflict_counts["all"] == 4


# ---------------------------------------------------------------------------
# Helper: _split_linked_into_slots
# ---------------------------------------------------------------------------

def test_split_linked_returns_canonical_slot_keys():
    out = ae._split_linked_into_slots(_LINKED_COMPOSITE)
    assert set(out) == {
        "identity", "responsibility", "soul",
        "instructions", "project-context", "vault",
    }


def test_split_linked_ignores_unknown_h2_headings():
    composite = "## Not A Slot\nbody\n\n## Identity\nidbody\n"
    out = ae._split_linked_into_slots(composite)
    assert set(out) == {"identity"}


def test_split_linked_handles_closing_hashes_in_heading():
    """Markdown allows `## Foo ##` — should still recognize the slot."""
    composite = "## Identity ##\nbody\n"
    out = ae._split_linked_into_slots(composite)
    assert "identity" in out


# ---------------------------------------------------------------------------
# AC: cache corruption — retry LLM once, then abort if retry also fails
# ---------------------------------------------------------------------------

def test_cache_hit_with_valid_body_skips_llm(tmp_path):
    """A valid cached body means assemble_slot_fn is NEVER called for that slot."""
    llm_calls = []

    def assemble_slot_fn(slot, linked_body):
        llm_calls.append(slot)
        return "fresh from LLM\n"

    def cache_lookup_fn(slot, linked_body):
        return "CACHED-BODY for " + slot

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        cache_lookup_fn=cache_lookup_fn,
        **stubs,
    )
    assert llm_calls == [], f"LLM should not be called on cache hit; got {llm_calls}"


def test_cache_corruption_triggers_one_retry_and_succeeds(tmp_path):
    """Cache hit with corrupt body -> ONE retry per slot; retry succeeds -> use retry body."""
    llm_call_count = {"n": 0}

    def assemble_slot_fn(slot, linked_body):
        llm_call_count["n"] += 1
        return "RETRY-OUTPUT for " + slot

    def cache_lookup_fn(slot, linked_body):
        return "CACHED-BUT-CORRUPT for " + slot

    def parse_output_fn(llm_output):
        return llm_output, []

    seq = {"resolve": 0}

    def resolve_fn(body, conflicts, linked_body):
        seq["resolve"] += 1
        # Odd resolves = cached-body verify (fail). Even = retry verify (pass).
        if seq["resolve"] % 2 == 1:
            return [ResolverIssue(
                conflict_index=1, slot="instructions",
                loser_layer="L2", winner_layer="L4",
                detail="cached body corrupt",
            )], _all_ok_reverify()
        return [], _all_ok_reverify()

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    stubs["parse_output_fn"] = parse_output_fn
    stubs["resolve_fn"] = resolve_fn
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        cache_lookup_fn=cache_lookup_fn,
        **stubs,
    )
    # 4 non-verbatim slots × 1 retry each = 4. No double retries.
    assert llm_call_count["n"] == 4


def test_cache_corruption_retry_also_fails_raises_cache_corruption(tmp_path):
    """Both cached body AND retry body fail verification -> CacheCorruption, no partial artifacts."""
    def assemble_slot_fn(slot, linked_body):
        return "BAD-RETRY"

    def cache_lookup_fn(slot, linked_body):
        return "BAD-CACHED"

    def parse_output_fn(llm_output):
        return llm_output, []

    def resolve_fn(body, conflicts, linked_body):
        # Always fail — both cached and retry.
        return [ResolverIssue(
            conflict_index=1, slot="instructions",
            loser_layer="L2", winner_layer="L4",
            detail="loser still present",
        )], _all_ok_reverify()

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    stubs["parse_output_fn"] = parse_output_fn
    stubs["resolve_fn"] = resolve_fn
    with pytest.raises(ae.CacheCorruption) as exc:
        ae.assemble_and_emit(
            _LINKED_COMPOSITE, tmp_path, role_class="worker",
            cache_lookup_fn=cache_lookup_fn,
            **stubs,
        )
    assert exc.value.slot in {"identity", "responsibility", "soul", "instructions"}
    assert list(tmp_path.iterdir()) == []


def test_cache_corruption_retry_succeeds_stores_new_body(tmp_path):
    """When the retry succeeds, the new body is stored to the cache (write-through)."""
    store_calls = []

    def assemble_slot_fn(slot, linked_body):
        return "RETRY-FOR-" + slot

    def cache_lookup_fn(slot, linked_body):
        return "BAD-CACHED-FOR-" + slot

    def cache_store_fn(slot, linked_body, output):
        store_calls.append(slot)

    def parse_output_fn(llm_output):
        return llm_output, []

    seq = {"n": 0}

    def resolve_fn(body, conflicts, linked_body):
        seq["n"] += 1
        if seq["n"] % 2 == 1:
            return [ResolverIssue(
                conflict_index=1, slot="instructions",
                loser_layer="L2", winner_layer="L4",
                detail="cache corrupt",
            )], _all_ok_reverify()
        return [], _all_ok_reverify()

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    stubs["parse_output_fn"] = parse_output_fn
    stubs["resolve_fn"] = resolve_fn
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        cache_lookup_fn=cache_lookup_fn,
        cache_store_fn=cache_store_fn,
        **stubs,
    )
    assert set(store_calls) == {"identity", "responsibility", "soul", "instructions"}


def test_cache_miss_runs_llm_and_stores_on_success(tmp_path):
    """Cache miss -> LLM dispatch; success -> body stored via cache_store_fn."""
    llm_calls = []
    store_calls = []

    def assemble_slot_fn(slot, linked_body):
        llm_calls.append(slot)
        return "FRESH-FOR-" + slot

    def cache_lookup_fn(slot, linked_body):
        return None

    def cache_store_fn(slot, linked_body, output):
        store_calls.append(slot)

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        cache_lookup_fn=cache_lookup_fn,
        cache_store_fn=cache_store_fn,
        **stubs,
    )
    assert set(llm_calls) == {"identity", "responsibility", "soul", "instructions"}
    assert set(store_calls) == {"identity", "responsibility", "soul", "instructions"}


def test_cache_miss_with_fresh_failure_does_not_retry(tmp_path):
    """A fresh LLM run that fails verification is NOT cache_corruption — no retry."""
    llm_calls = []

    def assemble_slot_fn(slot, linked_body):
        llm_calls.append(slot)
        return "BAD-FRESH"

    def cache_lookup_fn(slot, linked_body):
        return None  # miss -> no retry semantics

    def parse_output_fn(llm_output):
        return llm_output, []

    def resolve_fn(body, conflicts, linked_body):
        return [ResolverIssue(
            conflict_index=1, slot="instructions",
            loser_layer="L2", winner_layer="L4",
            detail="precedence violation on first try",
        )], _all_ok_reverify()

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    stubs["parse_output_fn"] = parse_output_fn
    stubs["resolve_fn"] = resolve_fn
    with pytest.raises(ae.PrecedenceViolation):
        ae.assemble_and_emit(
            _LINKED_COMPOSITE, tmp_path, role_class="worker",
            cache_lookup_fn=cache_lookup_fn,
            **stubs,
        )
    # Exactly one LLM call for the first non-verbatim slot — no retry on fresh fail.
    assert len(llm_calls) == 1


def test_cache_lookup_exception_is_treated_as_miss(tmp_path):
    """A flaky cache backend raising on lookup must not break the assemble run."""
    llm_calls = []

    def assemble_slot_fn(slot, linked_body):
        llm_calls.append(slot)
        return "FRESH"

    def cache_lookup_fn(slot, linked_body):
        raise IOError("cache disk offline")

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        cache_lookup_fn=cache_lookup_fn,
        **stubs,
    )
    assert len(llm_calls) == 4


def test_cache_store_failure_does_not_abort_run(tmp_path):
    """cache_store_fn raising must not turn a successful assemble into a failure."""
    def assemble_slot_fn(slot, linked_body):
        return "FRESH"

    def cache_store_fn(slot, linked_body, output):
        raise IOError("cache disk offline")

    stubs = _stubs()
    stubs["assemble_slot_fn"] = assemble_slot_fn
    paths = ae.assemble_and_emit(
        _LINKED_COMPOSITE, tmp_path, role_class="worker",
        cache_store_fn=cache_store_fn,
        **stubs,
    )
    assert all(p.exists() for p in paths)

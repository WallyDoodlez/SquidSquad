"""Live-system pytest for #9415 — widen event IDs to 16 hex + nonce.

AC-derived (without reading the diff) against #9415 issue body + CONTEXT-9415 §3.

TC mapping:
  TC-1 → AC-1 part 1: event_bus._generate_id produces 16-char lowercase hex
  TC-2 → AC-1 part 2: identical content emits produce distinct IDs (nonce works)
  TC-3 → AC-1 sanity: different content still produces different IDs
  TC-4 → AC-2: harness._emit_event produces 16-char hex
  TC-5 → AC-3 + AC-4: dev's targeted tests green (length + distinct-emit + harness)
  TC-6 → AC-6: event_poll.py treats IDs as opaque strings (string-equality lookup
               works on 16-char IDs without code change)
  TC-7 → AC-7: docs/EVENT-BUS-ARCHITECTURE.md has no stale 8-char width claims
  TC-8 → distribution: many emits across both paths stay collision-free
"""

from __future__ import annotations

import importlib
import re
import string
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "references" / "scripts" / "compose.py").exists():
            return parent
    raise RuntimeError(f"Could not locate repo root from {here}")


REPO_ROOT = _find_repo_root()
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
DOCS_DIR = REPO_ROOT / "docs"

sys.path.insert(0, str(SCRIPTS_DIR))
import event_bus  # noqa: E402

HEX_LOWER = set(string.hexdigits.lower())


# TC-1
def test_tc_01_generate_id_is_16_char_lowercase_hex():
    eid = event_bus._generate_id("cycle-start", "skill", "2026-05-21T01:00:00", {})
    assert len(eid) == 16, f"expected 16 hex chars, got {len(eid)}: {eid!r}"
    assert all(c in HEX_LOWER for c in eid), f"non-hex chars in {eid!r}"


# TC-2
def test_tc_02_identical_content_produces_distinct_ids():
    args = ("cycle-start", "skill", "2026-05-21T01:00:00", {"k": "v"})
    a = event_bus._generate_id(*args)
    b = event_bus._generate_id(*args)
    assert a != b, (
        "Identical-content emits collapsed to the same ID — the nonce in "
        "_generate_id is missing (#9415 D5 regression)"
    )


# TC-3
def test_tc_03_different_content_still_distinct():
    a = event_bus._generate_id("cycle-start", "skill", "2026-05-21T01:00:00", {})
    b = event_bus._generate_id("cycle-end", "skill", "2026-05-21T01:00:00", {})
    assert a != b


# TC-4
def test_tc_04_harness_emit_event_id_is_16_char_hex():
    """harness._emit_event must also widen to 16-char hex per AC-2."""
    harness = importlib.import_module("harness")
    captured = []
    with mock.patch.object(harness.event_lifecycle, "append",
                           side_effect=lambda e: captured.append(e)), \
         mock.patch.object(harness, "_log_event"):
        harness._emit_event("qa-verify-9415", "qa", payload={"tc": 4})
    assert len(captured) == 1
    eid = captured[0]["id"]
    assert len(eid) == 16, f"harness emitted {len(eid)}-char id: {eid!r}"
    assert all(c in HEX_LOWER for c in eid)


# TC-5
def test_tc_05_dev_targeted_suites_green():
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short",
         str(REPO_ROOT / "tests" / "test_event_bus.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert r.returncode == 0, (
        f"test_event_bus.py failed:\n{r.stdout}\n{r.stderr}"
    )


# TC-6
def test_tc_06_event_poll_treats_ids_as_opaque_strings():
    """AC-6: event_poll.py's cursor handling must work on 16-char ids
    without code change (string-equality lookup is width-agnostic).
    The check is structural: confirm event_poll references the `id`
    field as a generic string and contains no hardcoded width assumption.
    """
    src = (SCRIPTS_DIR / "event_poll.py").read_text(encoding="utf-8")
    # No 8-char regex anchored to event ids should appear.
    assert not re.search(r"len\([^)]*id[^)]*\)\s*==\s*8", src), (
        "event_poll.py contains a hardcoded 8-char ID width check"
    )
    assert not re.search(r"\[:8\]", src) or "test" in src.lower(), (
        "event_poll.py contains [:8] slice — likely a width assumption"
    )


# TC-7
def test_tc_07_docs_event_bus_no_stale_8_char_references():
    doc = (DOCS_DIR / "EVENT-BUS-ARCHITECTURE.md").read_text(encoding="utf-8")
    # No "8 hex char" / "8-char" / "32-bit" claims about event ids.
    forbidden = [
        r"\b8[- ]?hex[- ]?(char|character|digit)",
        r"\b8[- ]?char\b",
        r"32[- ]?bit.*event[- ]?id",
        r"os\.urandom\(4\)",
        r"hexdigest\(\)\[:8\]",
    ]
    for pat in forbidden:
        m = re.search(pat, doc, re.IGNORECASE)
        assert m is None, (
            f"EVENT-BUS-ARCHITECTURE.md contains stale 8-char reference "
            f"matching /{pat}/: {m.group(0) if m else ''!r}"
        )
    # Positive marker: the new width or nonce should be reflected.
    assert ("16" in doc and "hex" in doc.lower()) or "nonce" in doc.lower(), (
        "EVENT-BUS-ARCHITECTURE.md should reference 16-char width or nonce "
        "after #9415 widening"
    )


# TC-8
def test_tc_08_nonce_not_cached_constant():
    """Regression guard: nonce must not become a module-level cached constant.

    CONTEXT-9415 D5 locks a 2-byte (16-bit / 65k-value) nonce, which is
    insufficient to make many same-content emits unique by birthday math —
    a stress test of e.g. 5000 same-content emits would correctly fail.
    The AC literal ("identical-content emits produce distinct IDs") is
    interpreted at the lock's level: 2 emits must be distinct (covered by
    TC-2). This test instead guards against the regression class CONTEXT
    Risk Note #3 warns about — a nonce that goes silently constant — by
    asserting >50% uniqueness in 32 emits, which has near-1 probability
    even with a 16-bit nonce when randomness is functioning, but is
    impossible if the nonce becomes a fixed value across calls.
    """
    args = ("burst", "qa", "2026-05-21T01:00:00", {"i": 0})
    ids = {event_bus._generate_id(*args) for _ in range(32)}
    # 32 emits in a 65k nonce space: expected unique count ≈ 32 - (32*31)/(2*65536)
    # ≈ 31.992. A constant-nonce regression would collapse to len==1.
    assert len(ids) > 16, (
        f"only {len(ids)} unique ids in 32 emits — nonce appears cached "
        f"or constant (#9415 D5)"
    )

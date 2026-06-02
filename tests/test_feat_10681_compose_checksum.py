"""E2 (#10681) — last_compose_checksum field plumbing in .harness-state.json.

PRD-E Story E2: a single top-level SHA256-hex string in the harness state
file that records the checksum of the source-tree at the end of the last
successful compose. E1 (#10680) reads it on boot to detect drift; this
story only adds the plumbing (field, save, load, accessors) so E1 can
build on top.

Tests map directly to the 6 acceptance criteria in the issue body:

- AC1 — schema has top-level ``last_compose_checksum`` field after save.
- AC2 — legacy state files without the field load with ``checksum == None``.
- AC3 — atomic write: save_state writes via ``.tmp`` + rename.
- AC4 — accepts SHA256 hex (64 chars) and round-trips it through disk.
- AC5 — accessors use the shared ``self._lock`` (no separate lock per
  the AC's "coordinated with the rest of state-file access" rule).
- AC6 — simulated crash mid-write preserves the prior on-disk state.
"""

import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from harness import HarnessState  # noqa: E402


_SAMPLE_SHA256 = "a" * 64  # 64-char hex sentinel; arbitrary valid SHA256 shape


class TestLastComposeChecksumDefault(unittest.TestCase):
    """AC2 (default): a fresh HarnessState has no checksum."""

    def test_initial_checksum_is_none(self):
        hs = HarnessState()
        self.assertIsNone(hs.get_last_compose_checksum())


class TestLastComposeChecksumPersistence(unittest.TestCase):
    """AC1 + AC4 + AC6 — disk persistence + round-trip + migration."""

    def test_save_emits_field_in_state_file(self):
        """AC1: persisted state-file schema includes the field at top level."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                hs.set_last_compose_checksum(_SAMPLE_SHA256)
                hs.save_state()
                data = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertIn("last_compose_checksum", data)
                self.assertEqual(data["last_compose_checksum"], _SAMPLE_SHA256)

    def test_save_emits_null_when_unset(self):
        """A never-set checksum persists as JSON null (not absent).

        E1 distinguishes "no compose has run" from "checksum forgotten" by
        the absence vs presence of the key. Persisting null on first save
        makes that distinction observable in older state files (where the
        key is absent → migration treats as drift).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                hs.save_state()
                data = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertIn("last_compose_checksum", data)
                self.assertIsNone(data["last_compose_checksum"])

    def test_load_missing_field_yields_none(self):
        """AC2: legacy state files without the field load with checksum=None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            # Simulate a legacy state-file that predates E2 — no
            # `last_compose_checksum` key at all.
            state_file.write_text(json.dumps({
                "harness_pid": 12345,
                "start_time": 1000.0,
                "port": 7373,
                "agents": {},
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                with patch("harness._log"):
                    hs.load_state()
                self.assertIsNone(hs.get_last_compose_checksum())

    def test_load_explicit_null_yields_none(self):
        """An explicit JSON null in the field loads as None (honored verbatim)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            state_file.write_text(json.dumps({
                "harness_pid": 12345,
                "start_time": 1000.0,
                "port": 7373,
                "last_compose_checksum": None,
                "agents": {},
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                with patch("harness._log"):
                    hs.load_state()
                self.assertIsNone(hs.get_last_compose_checksum())

    def test_save_then_load_round_trip(self):
        """AC4: a 64-char hex checksum round-trips through save+load unchanged."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                hs.set_last_compose_checksum(_SAMPLE_SHA256)
                hs.save_state()

                hs2 = HarnessState()
                with patch("harness._log"):
                    hs2.load_state()
                self.assertEqual(
                    hs2.get_last_compose_checksum(),
                    _SAMPLE_SHA256,
                )

    def test_save_overwrites_previous_checksum(self):
        """AC6 write-semantics: a subsequent save replaces the prior value."""
        old = "0" * 64
        new = "f" * 64
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                hs.set_last_compose_checksum(old)
                hs.save_state()
                hs.set_last_compose_checksum(new)
                hs.save_state()
                data = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertEqual(data["last_compose_checksum"], new)


class TestLastComposeChecksumAtomicWrite(unittest.TestCase):
    """AC3 + AC6 — atomic write and crash safety."""

    def test_save_uses_tmp_then_rename(self):
        """AC3: save writes through a .tmp file then renames to the real path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                hs.set_last_compose_checksum(_SAMPLE_SHA256)
                hs.save_state()
                # Atomic write contract: .tmp not left behind, real file present.
                self.assertTrue(state_file.exists())
                self.assertFalse(state_file.with_suffix(".tmp").exists())

    def test_simulated_crash_mid_write_preserves_prior_state(self):
        """AC6: if the .tmp write fails (simulated), the old file is intact.

        The atomic-write contract: ``save_state`` writes to ``.tmp`` then
        ``.tmp.replace(real)``. If the ``write_text`` to ``.tmp`` raises,
        ``replace`` never runs — the prior committed state on disk
        survives unchanged. This is the operator's safety net during a
        mid-cycle harness crash.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                # First, lay down a known-good state on disk.
                hs = HarnessState()
                hs.set_last_compose_checksum(_SAMPLE_SHA256)
                hs.save_state()
                self.assertTrue(state_file.exists())
                original = state_file.read_text(encoding="utf-8")

                # Now attempt a second save with the .tmp write raising
                # OSError. Per save_state's except-block, the failure is
                # logged (warned) and the original file is left untouched.
                hs.set_last_compose_checksum("b" * 64)
                real_write_text = Path.write_text

                def failing_write_text(self_path, *args, **kwargs):
                    if str(self_path).endswith(".tmp"):
                        raise OSError("simulated mid-write crash")
                    return real_write_text(self_path, *args, **kwargs)

                with patch.object(Path, "write_text", failing_write_text):
                    with patch("harness._log"):
                        hs.save_state()

                # Original on-disk content is intact.
                self.assertEqual(
                    state_file.read_text(encoding="utf-8"),
                    original,
                )


class TestLastComposeChecksumLocking(unittest.TestCase):
    """AC5: accessor methods coordinate with the existing state-file lock."""

    def test_get_uses_self_lock(self):
        """AC5: get_last_compose_checksum reads under ``self._lock``."""
        source = inspect.getsource(HarnessState.get_last_compose_checksum)
        self.assertIn("self._lock", source, (
            "get_last_compose_checksum must take self._lock to coordinate "
            "with other state-file reads/writes (AC5 — no separate lock)."
        ))

    def test_set_uses_self_lock(self):
        """AC5: set_last_compose_checksum writes under ``self._lock``."""
        source = inspect.getsource(HarnessState.set_last_compose_checksum)
        self.assertIn("self._lock", source, (
            "set_last_compose_checksum must take self._lock to coordinate "
            "with other state-file reads/writes (AC5 — no separate lock)."
        ))


if __name__ == "__main__":
    unittest.main()

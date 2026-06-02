"""Tests for PRD-E E5 (#10684): wire freshness check into harness
restart-safety (step 1b).

E1 (#10680) wired ``compose_freshness.check_and_repair`` into the
lifespan synchronously before yield — which IS the restart-safety
path on harness reboot (the lifespan body runs every time the
harness starts, fresh or after a crash). E5 adds the operator
escape hatch (``--no-freshness-check`` / env var) and pins the
restart-specific contracts:

- AC1 (step 1b ordering): the freshness check lives in lifespan
  AFTER ``state.load_state()`` (step 1) and BEFORE the deferred-init
  thread launches the PID-verification + auto-start sequence
  (step 2+). E1's tests already locked this; this module adds an
  end-to-end view of the order.
- AC2 (restart-abort semantics): on compose failure, the lifespan
  flips ``compose_freshness_failed=True`` and the rest of the boot
  flow refuses to spawn — restart "aborts" in the sense that no
  agents start. Locked by E1's tests.
- AC3 (escape hatch): ``--no-freshness-check`` and
  ``SQUIDSQUAD_HARNESS_NO_FRESHNESS_CHECK=1`` skip the check
  entirely; the lifespan logs ONCE that the gate was bypassed.
- AC4 (test scenarios): clean restart / drift restart / failed-
  compose restart all surface in static-grep + module surface
  shape tests below.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _harness_source():
    return (SCRIPTS / "harness.py").read_text(encoding="utf-8")


class TestEscapeHatchFlag:
    """AC3 — `--no-freshness-check` CLI flag + env var bypass the gate.

    Static-grep instead of subprocess so the test runs without spinning
    up FastAPI or actually invoking the harness binary."""

    def test_module_level_flag_defaults_false(self):
        try:
            import harness
        except Exception:
            pytest.skip("harness module unavailable (likely missing fastapi)")
        assert hasattr(harness, "_NO_FRESHNESS_CHECK")
        assert harness._NO_FRESHNESS_CHECK is False

    def test_argparse_registers_no_freshness_check(self):
        src = _harness_source()
        # `main()`'s argparse block must register the flag.
        assert '"--no-freshness-check"' in src, (
            "main() must register the --no-freshness-check argparse flag "
            "per AC3"
        )

    def test_argparse_reads_env_var(self):
        src = _harness_source()
        assert "SQUIDSQUAD_HARNESS_NO_FRESHNESS_CHECK" in src, (
            "main() must honor SQUIDSQUAD_HARNESS_NO_FRESHNESS_CHECK env "
            "var so callers that don't go through argparse (test "
            "harnesses, restart scripts) can opt in"
        )

    def test_argparse_or_env_drives_module_flag(self):
        # Both should land in _NO_FRESHNESS_CHECK via the same logical-
        # OR pattern the other escape hatches use.
        src = _harness_source()
        # Find the env-var assignment block.
        idx = src.index("env_freshness =")
        # The assignment to _NO_FRESHNESS_CHECK must come right after.
        block = src[idx:idx + 400]
        assert "_NO_FRESHNESS_CHECK" in block, (
            "the env-var read must drive _NO_FRESHNESS_CHECK"
        )
        assert "args.no_freshness_check" in block, (
            "the CLI flag must drive _NO_FRESHNESS_CHECK (logical-or "
            "with the env var)"
        )

    def test_lifespan_skips_check_when_flag_set(self):
        src = _harness_source()
        start = src.index("async def lifespan(")
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        # The flag is consulted before the check fires.
        flag_idx = block.find("_NO_FRESHNESS_CHECK")
        check_idx = block.find("check_and_repair")
        assert flag_idx != -1, (
            "lifespan must consult _NO_FRESHNESS_CHECK before running "
            "the freshness check"
        )
        assert flag_idx < check_idx, (
            "_NO_FRESHNESS_CHECK guard must come BEFORE the "
            "check_and_repair call so the flag actually short-circuits "
            "the compose subprocess"
        )

    def test_lifespan_logs_bypass(self):
        src = _harness_source()
        start = src.index("async def lifespan(")
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        # The bypass must surface in the log so the audit trail
        # captures who opted out and when (AC3's "logged once" intent).
        assert "SKIPPED" in block and "no-freshness-check" in block, (
            "lifespan must log the bypass (operator audit trail) when "
            "_NO_FRESHNESS_CHECK is set"
        )


class TestRestartStep1bOrdering:
    """AC1 — the freshness check runs at HARNESS-ARCH §10 step 1b,
    AFTER state.load_state() (step 1) and BEFORE the PID-verification
    path (step 2+) which lives in update_health / deferred init."""

    def test_load_state_runs_before_freshness_check(self):
        src = _harness_source()
        start = src.index("async def lifespan(")
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        # Use the lifespan-local sites (not the docstrings).
        load_idx = block.index("state.load_state()")
        check_idx = block.index("check_and_repair")
        assert load_idx < check_idx, (
            "step 1 (load_state) must run BEFORE step 1b (freshness "
            "check) per HARNESS-ARCH §10"
        )

    def test_freshness_check_runs_before_deferred_init_thread(self):
        # The deferred-init thread runs the auto-start sequence which
        # IS the spawn path that step 2+ leads into; the freshness
        # gate must decide BEFORE that thread launches so a failed
        # compose can short-circuit auto-start.
        src = _harness_source()
        start = src.index("async def lifespan(")
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        check_idx = block.index("check_and_repair")
        thread_idx = block.index("threading.Thread(target=_deferred_init")
        assert check_idx < thread_idx, (
            "freshness check (step 1b) must run BEFORE the deferred-init "
            "thread launches the spawn sequence (step 2+)"
        )


class TestRestartAbortContract:
    """AC2 — on compose failure the restart aborts in the sense that no
    agents are spawned. Implementation lives in E1; this test pins the
    contract from the restart-safety perspective."""

    def test_failed_status_sets_persistent_flag(self):
        src = _harness_source()
        start = src.index("async def lifespan(")
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        assert 'status == "failed"' in block, (
            "lifespan must branch on the failed status returned by "
            "check_and_repair"
        )
        assert "compose_freshness_failed = True" in block, (
            "lifespan must persist the failed flag on HarnessState so "
            "every downstream spawn path can refuse"
        )


class TestEscapeHatchDoesNotBypassPersistedFailure:
    """The escape hatch skips the CHECK, but does NOT clear a previously-
    persisted `compose_freshness_failed=True`. If a prior boot failed
    and the operator restarts with --no-freshness-check, spawn paths
    still see the persisted flag and refuse."""

    def test_no_freshness_check_does_not_reset_failed_flag(self):
        # HarnessState.__init__ initializes compose_freshness_failed=False,
        # but load_state() reads from disk and could restore it from a
        # prior crash. The escape hatch must NOT call
        # state.compose_freshness_failed = False.
        src = _harness_source()
        start = src.index("async def lifespan(")
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        # In the `_NO_FRESHNESS_CHECK` branch we set _freshness = None
        # and continue. The branch must NOT write False to the flag.
        nfc_idx = block.index("_NO_FRESHNESS_CHECK")
        # Look forward 1000 chars at the bypass block.
        bypass_block = block[nfc_idx:nfc_idx + 800]
        assert "compose_freshness_failed = False" not in bypass_block, (
            "the escape hatch must NOT reset compose_freshness_failed — "
            "a prior persisted failure should still block spawns"
        )


class TestPersistenceAcrossRestart:
    """DS-10684 F1 + F2 regression — ``compose_freshness_failed`` must
    survive harness restart. The escape hatch's documented protection
    against a prior failure depends on the flag being persisted to
    ``.harness-state.json`` and restored on the next boot."""

    def test_save_state_writes_failed_flag(self, tmp_path, monkeypatch):
        try:
            import harness
        except Exception:
            pytest.skip("harness module unavailable (likely missing fastapi)")
        # Redirect the state file to tmp_path so we don't clobber the
        # real one. The module reads HARNESS_STATE_FILE at write time.
        state_file = tmp_path / ".harness-state.json"
        monkeypatch.setattr(harness, "HARNESS_STATE_FILE", state_file)
        s = harness.HarnessState()
        s.compose_freshness_failed = True
        s.save_state()
        import json
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert data["compose_freshness_failed"] is True

    def test_load_state_restores_failed_flag(self, tmp_path, monkeypatch):
        try:
            import harness
        except Exception:
            pytest.skip("harness module unavailable (likely missing fastapi)")
        state_file = tmp_path / ".harness-state.json"
        monkeypatch.setattr(harness, "HARNESS_STATE_FILE", state_file)
        # Hand-write a state file with the flag set.
        import json
        state_file.write_text(json.dumps({
            "harness_pid": 0,
            "start_time": 0,
            "port": 7373,
            "last_compose_checksum": None,
            "compose_freshness_failed": True,
            "agents": {},
        }), encoding="utf-8")
        s = harness.HarnessState()
        assert s.compose_freshness_failed is False  # default
        s.load_state()
        assert s.compose_freshness_failed is True, (
            "load_state() must restore compose_freshness_failed so a "
            "prior boot's failure persists across restart"
        )

    def test_legacy_state_file_defaults_failed_flag_to_false(
        self, tmp_path, monkeypatch,
    ):
        # Legacy state files (written before E5) lack the field. The
        # restore must default safely to False so a clean install
        # doesn't suddenly refuse to spawn.
        try:
            import harness
        except Exception:
            pytest.skip("harness module unavailable (likely missing fastapi)")
        state_file = tmp_path / ".harness-state.json"
        monkeypatch.setattr(harness, "HARNESS_STATE_FILE", state_file)
        import json
        state_file.write_text(json.dumps({
            "harness_pid": 0,
            "start_time": 0,
            "port": 7373,
            "last_compose_checksum": None,
            # No compose_freshness_failed key — legacy state file.
            "agents": {},
        }), encoding="utf-8")
        s = harness.HarnessState()
        s.load_state()
        assert s.compose_freshness_failed is False

    def test_lifespan_failed_branch_flushes_state(self):
        # DS-10684 F2: the failed branch must call state.save_state()
        # so the flag persists even if the harness crashes before any
        # other path triggers a save. Static-grep instead of running
        # the lifespan.
        src = _harness_source()
        start = src.index("async def lifespan(")
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        failed_idx = block.index('status == "failed"')
        # The save_state() call must appear AFTER the flag-set line
        # AND BEFORE the diagnostic logs end the branch — within the
        # next ~500 chars.
        branch_block = block[failed_idx:failed_idx + 800]
        assert "state.save_state()" in branch_block, (
            "the failed branch must call state.save_state() so the "
            "flag persists across a crash before the next save-state-"
            "triggering event (DS-10684 F2)"
        )

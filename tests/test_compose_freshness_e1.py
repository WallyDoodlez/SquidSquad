"""Tests for references/scripts/compose_freshness.py (#10680, PRD-E E1).

AC6 mandates tests for:
  (a) clean install (no drift) → no compose run, status="clean"
  (b) drifted install → compose runs, checksum updates, status="repaired"
  (c) first boot (no checksum) → compose runs, status="repaired"
  (d) compose failure → harness refuses to spawn, status="failed"

Plus structural tests for the checksum algorithm (determinism, path
sensitivity, content sensitivity) and the harness lifespan wiring
(static-grep gate so the actor named in the AC is actually invoked
from the production caller — per the audit-pattern memo).
"""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose_freshness as cf  # noqa: E402


def _stage_minimal_repo(tmp_path):
    """Build a tiny repo-root with at least one file per
    ``COMPOSE_INPUT_GLOBS`` shape so the checksum has something to
    hash. Returns the repo_root path.
    """
    repo = tmp_path
    (repo / ".squidsquad").mkdir()
    (repo / ".squidsquad" / "config.md").write_text("- v: 1\n", encoding="utf-8")
    (repo / ".squidsquad" / "project").mkdir()
    (repo / ".squidsquad" / "project" / "pm.md").write_text(
        "# pm L4\n", encoding="utf-8")
    (repo / "references" / "sub-skills" / "common").mkdir(parents=True)
    (repo / "references" / "sub-skills" / "common" / "boot.md").write_text(
        "# boot\n", encoding="utf-8")
    (repo / "references" / "sub-skills" / "manifest.md").write_text(
        "# manifest\n", encoding="utf-8")
    (repo / "references" / "roles").mkdir(parents=True)
    (repo / "references" / "roles" / "identity.md").write_text(
        "# identity\n", encoding="utf-8")
    (repo / "references" / "roles" / "pm").mkdir()
    (repo / "references" / "roles" / "pm" / "instructions.md").write_text(
        "# pm instructions\n", encoding="utf-8")
    return repo


# ---------------------------------------------------------------------------
# compute_compose_checksum — determinism + sensitivity
# ---------------------------------------------------------------------------


class TestComputeChecksum:

    def test_deterministic_across_runs(self, tmp_path):
        repo = _stage_minimal_repo(tmp_path)
        a = cf.compute_compose_checksum(repo)
        b = cf.compute_compose_checksum(repo)
        assert a == b
        assert len(a) == 64  # SHA256 hex digest

    def test_content_change_rolls_checksum(self, tmp_path):
        repo = _stage_minimal_repo(tmp_path)
        a = cf.compute_compose_checksum(repo)
        # Mutate one input file.
        (repo / "references" / "sub-skills" / "common" / "boot.md").write_text(
            "# boot v2\n", encoding="utf-8")
        b = cf.compute_compose_checksum(repo)
        assert a != b

    def test_rename_rolls_checksum(self, tmp_path):
        repo = _stage_minimal_repo(tmp_path)
        a = cf.compute_compose_checksum(repo)
        # Rename a file — same content, different path.
        old = repo / "references" / "sub-skills" / "common" / "boot.md"
        new = repo / "references" / "sub-skills" / "common" / "boot-renamed.md"
        old.rename(new)
        b = cf.compute_compose_checksum(repo)
        assert a != b, (
            "rename must roll the checksum (path is part of the hash)"
        )

    def test_unrelated_file_does_not_affect_checksum(self, tmp_path):
        repo = _stage_minimal_repo(tmp_path)
        a = cf.compute_compose_checksum(repo)
        # File outside the compose-input set.
        (repo / "README.md").write_text("# unrelated\n", encoding="utf-8")
        (repo / ".squidsquad" / "skill").mkdir()
        (repo / ".squidsquad" / "skill" / "working-state.md").write_text(
            "# state\n", encoding="utf-8")
        b = cf.compute_compose_checksum(repo)
        assert a == b, (
            "files outside COMPOSE_INPUT_GLOBS must not change the hash"
        )


# ---------------------------------------------------------------------------
# check_and_repair — the four AC6 scenarios
# ---------------------------------------------------------------------------


def _ok_runner(_repo):
    return 0, "deployed\n", ""


def _fail_runner(_repo):
    return 1, "", "compose: yaml.scanner.ScannerError: mapping values not allowed here"


class TestCheckAndRepair:

    def test_clean_install_no_compose_run(self, tmp_path):
        # AC6(a): stored checksum matches current source-tree → no
        # compose, no state change.
        repo = _stage_minimal_repo(tmp_path)
        current = cf.compute_compose_checksum(repo)
        runner_calls = []

        def tracking_runner(r):
            runner_calls.append(r)
            return _ok_runner(r)

        result = cf.check_and_repair(
            repo_root=repo,
            stored_checksum=current,
            runner=tracking_runner,
        )
        assert result.status == "clean"
        assert result.new_checksum == current
        assert runner_calls == []  # compose NOT invoked

    def test_drift_runs_compose_and_updates_checksum(self, tmp_path):
        # AC6(b): stored checksum differs → compose runs → result
        # carries the post-compose checksum.
        repo = _stage_minimal_repo(tmp_path)
        runner_calls = []

        def tracking(r):
            runner_calls.append(r)
            return _ok_runner(r)

        result = cf.check_and_repair(
            repo_root=repo,
            stored_checksum="0" * 64,  # bogus prior checksum
            runner=tracking,
        )
        assert result.status == "repaired"
        # The post-compose checksum is computed against the same source
        # tree (compose writes outputs elsewhere) so it equals current.
        assert result.new_checksum == cf.compute_compose_checksum(repo)
        assert len(runner_calls) == 1
        assert "drift detected" in result.diagnostic

    def test_first_boot_no_stored_checksum_runs_compose(self, tmp_path):
        # AC6(c): legacy state file (no checksum field) OR fresh
        # install (no state file) → triggers compose.
        repo = _stage_minimal_repo(tmp_path)
        runner_calls = []

        def tracking(r):
            runner_calls.append(r)
            return _ok_runner(r)

        result = cf.check_and_repair(
            repo_root=repo,
            stored_checksum=None,
            runner=tracking,
        )
        assert result.status == "repaired"
        assert "first boot" in result.diagnostic
        assert len(runner_calls) == 1

    def test_empty_string_checksum_treated_as_first_boot(self, tmp_path):
        repo = _stage_minimal_repo(tmp_path)

        def ok(r):
            return _ok_runner(r)

        result = cf.check_and_repair(
            repo_root=repo, stored_checksum="", runner=ok,
        )
        assert result.status == "repaired"

    def test_compose_failure_returns_failed_status(self, tmp_path):
        # AC6(d): compose itself fails → status="failed" + diagnostic
        # + stderr captured. Per AC4 the caller refuses to spawn.
        repo = _stage_minimal_repo(tmp_path)
        result = cf.check_and_repair(
            repo_root=repo,
            stored_checksum=None,  # forces compose
            runner=_fail_runner,
        )
        assert result.status == "failed"
        assert result.new_checksum == ""  # nothing to persist
        assert "WILL NOT" in result.diagnostic.upper() or \
               "refuses" in result.diagnostic.lower() or \
               "fix" in result.diagnostic.lower() or \
               "non-zero" in result.diagnostic.lower()
        assert "yaml.scanner" in result.compose_stderr

    def test_compose_runner_raise_is_treated_as_failure(self, tmp_path):
        repo = _stage_minimal_repo(tmp_path)

        def boom(_repo):
            raise RuntimeError("subprocess unavailable")

        result = cf.check_and_repair(
            repo_root=repo, stored_checksum=None, runner=boom,
        )
        assert result.status == "failed"
        assert "subprocess unavailable" in result.diagnostic


# ---------------------------------------------------------------------------
# Harness wiring — static-grep gate per feedback-no-deferred-wiring
# ---------------------------------------------------------------------------


class TestHarnessWiring:
    """The AC names the harness as the actor: 'on every harness start,
    BEFORE spawning any agent...'. Per the audit-pattern memo, the
    wiring is in-scope, not a follow-up. These guards block the
    regression at parse time."""

    def test_harness_imports_compose_freshness(self):
        src = (SCRIPTS / "harness.py").read_text(encoding="utf-8")
        assert "import compose_freshness" in src, (
            "harness.py must import compose_freshness so the E1 boot "
            "gate actually runs (per feedback-no-deferred-wiring)"
        )

    def test_deferred_init_calls_check_and_repair(self):
        src = (SCRIPTS / "harness.py").read_text(encoding="utf-8")
        # Locate the deferred-init block where the wiring lives.
        start = src.index("def _deferred_init")
        # The deferred init body ends at the threading.Thread call
        # that schedules it.
        end = src.index("threading.Thread(target=_deferred_init", start)
        block = src[start:end]
        assert "check_and_repair" in block, (
            "_deferred_init must call check_and_repair so the freshness "
            "gate fires on the boot path"
        )
        assert "compose_freshness_failed" in block, (
            "_deferred_init must set state.compose_freshness_failed on "
            "compose failure per AC4 — without it the caller can't enforce "
            "the spawn-refusal contract"
        )

    def test_harness_state_carries_failure_flag(self):
        # The flag must live on HarnessState so spawn paths beyond
        # _deferred_init's auto-start loop can also gate on it.
        try:
            import harness
        except Exception:
            pytest.skip("harness module unavailable (likely missing fastapi)")
        s = harness.HarnessState()
        assert hasattr(s, "compose_freshness_failed")
        assert s.compose_freshness_failed is False

    def test_lifespan_runs_check_synchronously_before_yield(self):
        # DS-10680 review F3: the check must run in lifespan() BEFORE
        # ``yield``, not inside the deferred-init thread, otherwise the
        # server accepts spawn requests while the gate is still
        # deciding (10-60s race during compose subprocess).
        src = (SCRIPTS / "harness.py").read_text(encoding="utf-8")
        start = src.index("async def lifespan(")
        # lifespan() ends at the next top-level FastAPI binding.
        end = src.index("app = FastAPI(", start)
        block = src[start:end]
        # The synchronous check uses the module-level import +
        # check_and_repair call before the threading.Thread launch.
        # Use line-anchored match for the actual ``yield`` statement
        # so comments mentioning "yield" don't false-positive.
        import re as _re
        check_idx = block.find("check_and_repair")
        thread_idx = block.find("threading.Thread(target=_deferred_init")
        yield_match = _re.search(r"(?m)^\s+yield\s*$", block)
        assert check_idx != -1, (
            "lifespan() must call check_and_repair synchronously "
            "(DS-10680 F3 regression — TOCTOU race against spawn "
            "requests during compose subprocess)"
        )
        assert check_idx < thread_idx, (
            "check_and_repair must run BEFORE deferred-init thread starts"
        )
        assert yield_match is not None, (
            "lifespan() must contain a ``yield`` statement"
        )
        assert check_idx < yield_match.start(), (
            "check_and_repair must run BEFORE lifespan yields — the "
            "server must not accept connections while the gate is "
            "still deciding"
        )

    def test_http_start_endpoints_gate_on_failure_flag(self):
        # DS-10680 review F1: both /agents/all/start and
        # /agents/{role}/start must read compose_freshness_failed and
        # return 503. Static-grep the endpoint bodies.
        src = (SCRIPTS / "harness.py").read_text(encoding="utf-8")
        for endpoint_marker in (
            'app.post("/agents/all/start")',
            'app.post("/agents/{role}/start")',
        ):
            start = src.index(endpoint_marker)
            # Endpoint body ends at the next @app or top-level def.
            try:
                end_app = src.index("\n@app.", start + 1)
            except ValueError:
                end_app = len(src)
            try:
                end_def = src.index("\ndef ", start + 1)
            except ValueError:
                end_def = len(src)
            end = min(end_app, end_def)
            block = src[start:end]
            assert "compose_freshness_failed" in block, (
                f"endpoint {endpoint_marker} must gate on "
                f"compose_freshness_failed (DS-10680 F1 — every spawn "
                f"path enforces AC4's refusal contract)"
            )
            assert "503" in block, (
                f"endpoint {endpoint_marker} must return 503 on the "
                f"freshness-failed branch (DS-10680 F1)"
            )

    def test_health_poller_reboot_gates_on_failure_flag(self):
        # DS-10680 review F4: the auto-reboot loop in update_health
        # must also check the flag — otherwise a harness restart with
        # alive-running agents would auto-respawn them past the gate.
        src = (SCRIPTS / "harness.py").read_text(encoding="utf-8")
        update_health_start = src.index("def update_health(self)")
        # Reboot loop ends at the next def (start_poller).
        update_health_end = src.index("\n    def start_poller", update_health_start)
        block = src[update_health_start:update_health_end]
        assert "self.compose_freshness_failed" in block, (
            "update_health auto-reboot loop must gate on the flag "
            "(DS-10680 F4 — defense-in-depth complement to F1)"
        )

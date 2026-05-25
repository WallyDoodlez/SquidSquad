"""Tests for references/scripts/shared_fs.py — shared filesystem at ~/.squidsquad/."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shared_fs


class TestGetHome:
    def test_returns_path_under_home(self):
        home = shared_fs.get_home()
        assert home == Path.home() / ".squidsquad"

    def test_returns_path_object(self):
        assert isinstance(shared_fs.get_home(), Path)


class TestInit:
    def test_creates_structure(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
        assert fake_home.exists()
        assert (fake_home / "secrets").exists()
        assert (fake_home / "config").exists()
        assert (fake_home / "clones").is_dir()

    def test_idempotent(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            # Write a secret, then re-init — should not overwrite
            (fake_home / "secrets").write_text("MY_KEY=my_value\n")
            shared_fs.init()
        content = (fake_home / "secrets").read_text()
        assert "MY_KEY=my_value" in content

    def test_secrets_has_comment_header(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
        content = (fake_home / "secrets").read_text()
        assert content.startswith("#")


class TestSecrets:
    def test_write_and_read(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("OPENAI_API_KEY", "sk-test123")
            value = shared_fs.read_secret("OPENAI_API_KEY")
        assert value == "sk-test123"

    def test_read_missing_key(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            value = shared_fs.read_secret("NONEXISTENT")
        assert value is None

    def test_read_no_file(self, tmp_path):
        fake_home = tmp_path / ".squidsquad-missing"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            value = shared_fs.read_secret("ANY_KEY")
        assert value is None

    def test_update_existing_secret(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("KEY", "old_value")
            shared_fs.write_secret("KEY", "new_value")
            value = shared_fs.read_secret("KEY")
        assert value == "new_value"

    def test_multiple_secrets(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("KEY_A", "val_a")
            shared_fs.write_secret("KEY_B", "val_b")
            assert shared_fs.read_secret("KEY_A") == "val_a"
            assert shared_fs.read_secret("KEY_B") == "val_b"

    def test_comments_ignored(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        fake_home.mkdir(parents=True)
        (fake_home / "secrets").write_text("# comment\nKEY=value\n# another\n")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            assert shared_fs.read_secret("KEY") == "value"
            assert shared_fs.read_secret("#") is None


class TestReadSecretOrEnv:
    def test_prefers_secrets_file(self, tmp_path, monkeypatch):
        fake_home = tmp_path / ".squidsquad"
        monkeypatch.setenv("TEST_KEY", "from_env")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("TEST_KEY", "from_file")
            value = shared_fs.read_secret_or_env("TEST_KEY")
        assert value == "from_file"

    def test_falls_back_to_env(self, tmp_path, monkeypatch):
        fake_home = tmp_path / ".squidsquad-empty"
        monkeypatch.setenv("TEST_KEY2", "from_env")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            value = shared_fs.read_secret_or_env("TEST_KEY2")
        assert value == "from_env"

    def test_returns_none_if_nowhere(self, tmp_path, monkeypatch):
        fake_home = tmp_path / ".squidsquad-empty"
        monkeypatch.delenv("MISSING_KEY_XYZ", raising=False)
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            value = shared_fs.read_secret_or_env("MISSING_KEY_XYZ")
        assert value is None

    def test_empty_string_secret_not_dropped(self, tmp_path, monkeypatch):
        """#4050 regression: empty-string secret must not fall through to env."""
        fake_home = tmp_path / ".squidsquad"
        monkeypatch.setenv("EMPTY_KEY", "from_env")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_secret("EMPTY_KEY", "")
            value = shared_fs.read_secret_or_env("EMPTY_KEY")
        # Secrets file takes precedence — even for empty string
        assert value == ""


class TestClones:
    def test_write_and_read(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            shared_fs.write_clone("skill", "/path/to/skill-clone")
            shared_fs.write_clone("pm", "/path/to/pm-clone")
            clones = shared_fs.read_clones()
        assert clones["skill"] == "/path/to/skill-clone"
        assert clones["pm"] == "/path/to/pm-clone"

    def test_empty_clones(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.init()
            clones = shared_fs.read_clones()
        assert clones == {}

    def test_no_clones_dir(self, tmp_path):
        fake_home = tmp_path / ".squidsquad-missing"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            clones = shared_fs.read_clones()
        assert clones == {}


class TestCLI:
    def test_help(self, capsys):
        sys.argv = ["shared_fs.py", "--help"]
        result = shared_fs.main()
        assert result == 0
        output = capsys.readouterr().out
        assert "shared_fs.py" in output

    def test_home(self, capsys):
        sys.argv = ["shared_fs.py", "home"]
        shared_fs.main()
        output = capsys.readouterr().out.strip()
        assert ".squidsquad" in output

    def test_init(self, tmp_path):
        fake_home = tmp_path / ".squidsquad"
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            sys.argv = ["shared_fs.py", "init"]
            shared_fs.main()
        assert fake_home.exists()

    def test_read_secret_empty_value_not_false_negative(self, tmp_path, capsys):
        """#6818: read-secret CLI must return exit 0 for empty secret, not 'not found'."""
        fake_home = tmp_path / ".squidsquad"
        fake_home.mkdir()
        secrets = fake_home / "secrets"
        secrets.write_text("EMPTY_KEY=\n", encoding="utf-8")
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            sys.argv = ["shared_fs.py", "read-secret", "EMPTY_KEY"]
            result = shared_fs.main()
        assert result is None or result == 0, (
            f"#6818: read-secret returned {result} for empty secret — should be 0"
        )


# ---------------------------------------------------------------------------
# #9932 — write_secret atomic write
# ---------------------------------------------------------------------------


class TestWriteSecretAtomic9932:
    """#9932: write_secret must write atomically — a crash between
    truncate and final flush must NOT leave the secrets file empty,
    because that loses every other API key the user had configured.
    """

    def test_basic_round_trip(self, tmp_path):
        """Sanity: write then read still works after the atomic refactor."""
        fake_home = tmp_path / ".squidsquad"
        fake_home.mkdir()
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.write_secret("MY_KEY", "my-value")
            assert shared_fs.read_secret("MY_KEY") == "my-value"

    def test_existing_secrets_preserved_on_update(self, tmp_path):
        """Updating one secret must NOT delete the others — the
        scenario the bug report described. Old code's truncate-first
        approach could empty the file mid-write and lose everything.
        """
        fake_home = tmp_path / ".squidsquad"
        fake_home.mkdir()
        secrets = fake_home / "secrets"
        secrets.write_text(
            "OPENAI_API_KEY=sk-aaa\n"
            "DEEPSEEK_API_KEY=ds-bbb\n"
            "ANTHROPIC_API_KEY=sk-ant-ccc\n",
            encoding="utf-8",
        )
        with patch.object(shared_fs, "get_home", return_value=fake_home):
            shared_fs.write_secret("OPENAI_API_KEY", "sk-NEW")
            assert shared_fs.read_secret("OPENAI_API_KEY") == "sk-NEW"
            assert shared_fs.read_secret("DEEPSEEK_API_KEY") == "ds-bbb"
            assert shared_fs.read_secret("ANTHROPIC_API_KEY") == "sk-ant-ccc"

    def test_secrets_file_survives_write_failure(self, tmp_path):
        """If the tmp-file write itself raises mid-way (simulate disk
        full / SIGKILL / IOError), the ORIGINAL secrets file must be
        completely untouched. This is the core #9932 invariant — the
        pre-fix code couldn't satisfy it because write_text truncated
        first, so a mid-write crash would leave the file empty.
        """
        fake_home = tmp_path / ".squidsquad"
        fake_home.mkdir()
        secrets = fake_home / "secrets"
        original = (
            "OPENAI_API_KEY=sk-original\n"
            "DEEPSEEK_API_KEY=ds-original\n"
        )
        secrets.write_text(original, encoding="utf-8")

        # Patch os.fdopen to raise as soon as the tmpfile is opened —
        # simulates a crash AFTER mkstemp succeeded but BEFORE the
        # content lands. The original file must remain intact.
        def crashing_fdopen(fd, *args, **kwargs):
            try:
                os.close(fd)
            except OSError:
                pass
            raise OSError("simulated disk full")

        with patch.object(shared_fs, "get_home", return_value=fake_home), \
             patch.object(shared_fs.os, "fdopen", side_effect=crashing_fdopen):
            with pytest.raises(OSError, match="simulated disk full"):
                shared_fs.write_secret("NEW_KEY", "should-not-land")

        # The original secrets file must be byte-for-byte unchanged.
        assert secrets.read_text(encoding="utf-8") == original, (
            "#9932: secrets file was modified after a simulated mid-write "
            "crash — atomic-write invariant violated"
        )
        # And no leftover .tmp files should clutter the secrets dir.
        leftover_tmps = list(fake_home.glob(".secrets-*.tmp"))
        assert not leftover_tmps, (
            f"tmp file not cleaned up after failure: {leftover_tmps}"
        )

    def test_uses_atomic_pattern_in_source(self):
        """Source-level invariant: write_secret must use ``os.replace``
        (the atomic rename) and tempfile + .tmp pattern. A future
        refactor that drops back to ``write_text`` would regress #9932,
        so we lock the pattern at the source level too."""
        import inspect
        source = inspect.getsource(shared_fs.write_secret)
        assert "os.replace" in source, (
            "#9932: write_secret must use os.replace for atomic swap"
        )
        assert "mkstemp" in source or "NamedTemporaryFile" in source, (
            "#9932: write_secret must write to a tempfile before renaming"
        )
        # Defense in depth: the old `secrets_file.write_text(...)` line
        # (which truncates before writing) must NOT be present.
        assert "secrets_file.write_text" not in source, (
            "#9932 regression: write_secret reverted to direct write_text "
            "(non-atomic — truncates before writing)"
        )


class TestAtomicWriteText:
    """#10007: shared atomic_write_text helper for concurrent-read safety."""

    def test_basic_write(self, tmp_path):
        p = tmp_path / "out.txt"
        shared_fs.atomic_write_text(p, "hello world")
        assert p.read_text(encoding="utf-8") == "hello world"

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / "out.txt"
        p.write_text("old", encoding="utf-8")
        shared_fs.atomic_write_text(p, "new")
        assert p.read_text(encoding="utf-8") == "new"

    def test_unicode_roundtrip(self, tmp_path):
        p = tmp_path / "out.md"
        content = "Task: #9965 — em-dash and 中文 mix\n"
        shared_fs.atomic_write_text(p, content)
        assert p.read_text(encoding="utf-8") == content

    def test_no_tmp_leftover_after_success(self, tmp_path):
        p = tmp_path / "out.txt"
        shared_fs.atomic_write_text(p, "x")
        leftovers = [f for f in tmp_path.iterdir() if f.suffix == ".tmp"]
        assert leftovers == []

    def test_crash_mid_write_leaves_original_intact(self, tmp_path, monkeypatch):
        """If the inner write raises, the original file must be untouched."""
        p = tmp_path / "out.txt"
        shared_fs.atomic_write_text(p, "original")

        import builtins
        real_open = builtins.open

        def boom(*args, **kwargs):
            # Only intercept the inner write-to-tmp call (mode 'w');
            # leave read calls (mode 'r' or no mode) alone.
            if len(args) >= 2 and args[1] == "w":
                raise RuntimeError("simulated crash")
            return real_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", boom)

        with pytest.raises(RuntimeError):
            shared_fs.atomic_write_text(p, "should not land")

        # Critical invariant: the original file is untouched.
        assert p.read_text(encoding="utf-8") == "original"

    def test_crash_mid_write_cleans_up_tmp(self, tmp_path, monkeypatch):
        """If the inner write raises, the tmp sibling must be deleted."""
        p = tmp_path / "out.txt"
        shared_fs.atomic_write_text(p, "original")

        import builtins
        real_open = builtins.open

        def boom(*args, **kwargs):
            if len(args) >= 2 and args[1] == "w":
                raise RuntimeError("simulated crash")
            return real_open(*args, **kwargs)

        monkeypatch.setattr(builtins, "open", boom)

        with pytest.raises(RuntimeError):
            shared_fs.atomic_write_text(p, "x")

        leftovers = [f for f in tmp_path.iterdir() if f.suffix == ".tmp"]
        assert leftovers == [], f"tmp file leaked: {leftovers}"

    def test_large_write_roundtrip(self, tmp_path):
        """Large content round-trips correctly through the helper.

        The actual concurrent-read safety is a structural guarantee of
        ``os.replace`` on a same-filesystem path — see
        ``test_uses_os_replace_for_atomic_swap`` for the source-level lock.
        This test just locks in that the helper handles non-trivial payload
        sizes (#10007 DS review Finding 3 — renamed from
        test_concurrent_reader_never_sees_partial_write because the original
        name implied a behavioral assertion the test body didn't make)."""
        p = tmp_path / "out.txt"
        shared_fs.atomic_write_text(p, "v1" * 1000)
        assert p.read_text(encoding="utf-8") == "v1" * 1000

    def test_uses_os_replace_for_atomic_swap(self):
        """Source-level lock: the helper must call ``os.replace`` (atomic
        on POSIX and Windows for same-filesystem paths). A future refactor
        that drops to ``shutil.move`` or similar non-atomic primitive would
        break the core guarantee (#10007 DS review Finding 3 — companion
        source-level assertion to the test rename above)."""
        import inspect
        source = inspect.getsource(shared_fs.atomic_write_text)
        assert "os.replace" in source, (
            "atomic_write_text must use os.replace for the swap step."
        )
        assert "mkstemp" in source, (
            "atomic_write_text must write to a sibling tmp file before swap."
        )

    def test_preserves_path_write_text_newline_behavior(self, tmp_path):
        """#10007 DS review Finding 1: the helper must match Path.write_text
        newline behavior so existing state files don't acquire a phantom
        git diff from line-ending changes when the helper is first deployed."""
        p_helper = tmp_path / "helper.txt"
        p_native = tmp_path / "native.txt"
        content = "line1\nline2\nline3\n"
        shared_fs.atomic_write_text(p_helper, content)
        p_native.write_text(content, encoding="utf-8")
        # Compare raw bytes — text mode normalizes, defeating the check.
        assert p_helper.read_bytes() == p_native.read_bytes(), (
            "atomic_write_text must produce byte-identical output to "
            "Path.write_text (same newline translation behavior)."
        )


class TestCallSitesUseAtomicWrite:
    """#10007 regression locks: every call site listed in the issue body
    must route through atomic_write_text (not Path.write_text). Source-level
    invariants — a future refactor that drops back to direct write_text on
    a concurrently-read state file would regress this issue."""

    @pytest.mark.parametrize("module_name,function_name", [
        ("vault_remember", "_write_working_state_field"),
        ("vault_remember", "_upsert_vault_writes"),
        ("cycle", "set_counter"),
        ("cycle_post", "_do_working_state_update"),
        ("cycle_post", "_do_version_bump"),
        ("soul_adaptation", "add_adaptation"),
        ("soul_adaptation", "render_soul"),
        ("config", "set_field"),
        ("config", "write_event_reactions"),  # #10007 DS review Finding 5
        ("diagnostics", "rotate"),
    ])
    def test_call_site_uses_atomic_write_text(self, module_name, function_name):
        import importlib
        import inspect
        mod = importlib.import_module(module_name)
        fn = getattr(mod, function_name)
        source = inspect.getsource(fn)
        assert "atomic_write_text" in source, (
            f"#10007 regression: {module_name}.{function_name} must call "
            f"atomic_write_text (not Path.write_text) — concurrent readers "
            f"can see torn writes on the state file it manages."
        )

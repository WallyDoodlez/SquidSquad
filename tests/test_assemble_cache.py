"""Tests for references/scripts/assemble_cache.py (#10443, PRD-B Story B6)."""

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import assemble_cache  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_repo(tmp_path, monkeypatch):
    """Point the cache module at a tmp_path repo root so writes are sandboxed."""
    monkeypatch.setattr(assemble_cache, "_REPO_ROOT", tmp_path)
    return tmp_path


_INPUTS = ("linked body text", "identity", "what this role is", "sonnet", "v1")


# ---------------------------------------------------------------------------
# cache_key
# ---------------------------------------------------------------------------

def test_cache_key_is_sha256_hex():
    key = assemble_cache.cache_key(*_INPUTS)
    assert isinstance(key, str)
    assert len(key) == 64
    assert all(c in "0123456789abcdef" for c in key)


def test_cache_key_identical_inputs_identical_keys():
    a = assemble_cache.cache_key(*_INPUTS)
    b = assemble_cache.cache_key(*_INPUTS)
    assert a == b


@pytest.mark.parametrize("index", range(5))
def test_cache_key_each_input_invalidates(index):
    base = list(_INPUTS)
    mutated = list(_INPUTS)
    mutated[index] = mutated[index] + "_X"
    assert assemble_cache.cache_key(*base) != assemble_cache.cache_key(*mutated)


def test_cache_key_separator_prevents_boundary_collision():
    # ("ab","c","x","y","z") must not collide with ("a","bc","x","y","z").
    k1 = assemble_cache.cache_key("ab", "c", "x", "y", "z")
    k2 = assemble_cache.cache_key("a", "bc", "x", "y", "z")
    assert k1 != k2


def test_cache_key_accepts_bytes_inputs():
    # Bytes are passed through; equivalent UTF-8 str must hash identically.
    str_key = assemble_cache.cache_key("body", "slot", "purpose", "model", "v1")
    bytes_key = assemble_cache.cache_key(b"body", b"slot", b"purpose", b"model", b"v1")
    assert str_key == bytes_key


# ---------------------------------------------------------------------------
# cache_lookup
# ---------------------------------------------------------------------------

def test_cache_lookup_miss_returns_none(tmp_repo):
    assert assemble_cache.cache_lookup("pm", "deadbeef" * 8) is None


def test_cache_lookup_miss_when_dir_absent(tmp_repo):
    # Even the alias dir doesn't exist — must not raise.
    assert assemble_cache.cache_lookup("never-existed", "abc123") is None


def test_cache_lookup_hit_returns_body_and_logs_to_stderr(tmp_repo, capsys):
    key = assemble_cache.cache_key(*_INPUTS)
    assemble_cache.cache_store("pm", key, "ASSEMBLED BODY\n")

    body = assemble_cache.cache_lookup("pm", key, slot_name="identity")

    assert body == "ASSEMBLED BODY\n"
    captured = capsys.readouterr()
    assert captured.err.strip() == "[cache hit] alias=pm slot=identity"


def test_cache_lookup_log_uses_question_mark_when_slot_omitted(tmp_repo, capsys):
    key = assemble_cache.cache_key(*_INPUTS)
    assemble_cache.cache_store("dm", key, "BODY")

    assemble_cache.cache_lookup("dm", key)

    assert capsys.readouterr().err.strip() == "[cache hit] alias=dm slot=?"


def test_cache_lookup_no_log_on_miss(tmp_repo, capsys):
    assemble_cache.cache_lookup("pm", "0" * 64, slot_name="identity")
    assert capsys.readouterr().err == ""


# ---------------------------------------------------------------------------
# cache_store + round-trip
# ---------------------------------------------------------------------------

def test_cache_store_creates_directory_and_file(tmp_repo):
    key = assemble_cache.cache_key(*_INPUTS)
    assemble_cache.cache_store("pm", key, "body")

    path = tmp_repo / ".squidsquad" / "pm" / ".assemble-cache" / f"{key}.md"
    assert path.is_file()


def test_cache_store_no_tmp_left_behind(tmp_repo):
    key = assemble_cache.cache_key(*_INPUTS)
    assemble_cache.cache_store("pm", key, "body")

    cache_dir = tmp_repo / ".squidsquad" / "pm" / ".assemble-cache"
    tmp_files = list(cache_dir.glob("*.tmp"))
    assert tmp_files == []


def test_cache_round_trip_preserves_bytes(tmp_repo):
    key = assemble_cache.cache_key(*_INPUTS)
    body = "Line 1\nLine 2\n\n```python\nprint('x')\n```\n← unicode arrow\n"
    assemble_cache.cache_store("pm", key, body)
    assert assemble_cache.cache_lookup("pm", key) == body


def test_cache_store_overwrites_existing(tmp_repo):
    key = assemble_cache.cache_key(*_INPUTS)
    assemble_cache.cache_store("pm", key, "first")
    assemble_cache.cache_store("pm", key, "second")
    assert assemble_cache.cache_lookup("pm", key) == "second"


def test_cache_isolated_per_alias(tmp_repo):
    key = assemble_cache.cache_key(*_INPUTS)
    assemble_cache.cache_store("pm", key, "pm-body")
    assemble_cache.cache_store("dm", key, "dm-body")
    assert assemble_cache.cache_lookup("pm", key) == "pm-body"
    assert assemble_cache.cache_lookup("dm", key) == "dm-body"


# ---------------------------------------------------------------------------
# Coexistence guard (PRD-B §9a): .gitignore must NOT exclude .assemble-cache/
# ---------------------------------------------------------------------------

def test_gitignore_does_not_exclude_assemble_cache():
    repo_root = Path(__file__).resolve().parent.parent
    gitignore = repo_root / ".gitignore"
    try:
        content = gitignore.read_text(encoding="utf-8")
    except FileNotFoundError:
        return  # no .gitignore → nothing excludes .assemble-cache
    assert ".assemble-cache" not in content


# ---------------------------------------------------------------------------
# Alias validation (path-traversal guard)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "bad_alias",
    ["..", "../etc", "a/b", "a\\b", "", ".hidden", "with space", "a\x00b", None, 42],
)
def test_invalid_alias_rejected(tmp_repo, bad_alias):
    key = "f" * 64
    with pytest.raises((ValueError, TypeError)):
        assemble_cache.cache_store(bad_alias, key, "body")
    with pytest.raises((ValueError, TypeError)):
        assemble_cache.cache_lookup(bad_alias, key)


@pytest.mark.parametrize("ok_alias", ["pm", "dm", "skill", "qa", "agent-1", "role_2", "a.b"])
def test_valid_alias_accepted(tmp_repo, ok_alias):
    key = "a" * 64
    assemble_cache.cache_store(ok_alias, key, "body")
    assert assemble_cache.cache_lookup(ok_alias, key) == "body"


# ---------------------------------------------------------------------------
# Atomic store failure path: .tmp must not linger on os.replace error
# ---------------------------------------------------------------------------

def test_cache_store_unlinks_tmp_on_replace_failure(tmp_repo, monkeypatch):
    key = "b" * 64

    def boom(src, dst):
        raise OSError(32, "ERROR_SHARING_VIOLATION (simulated)")

    monkeypatch.setattr(assemble_cache.os, "replace", boom)
    with pytest.raises(OSError):
        assemble_cache.cache_store("pm", key, "body")

    cache_dir = tmp_repo / ".squidsquad" / "pm" / ".assemble-cache"
    assert list(cache_dir.glob("*.tmp")) == []

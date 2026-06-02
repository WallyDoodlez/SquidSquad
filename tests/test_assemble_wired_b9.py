"""Tests for PRD-B B9 (#10763): wire B1-B7 assemble pipeline into
``compose.deploy_alias_v2``.

Covers AC1 (assemble invoked), AC2 (§9a v2 paths), AC4 (cache adapter),
AC5 (sonnet locked). AC3 (filename_suffix) is covered by the existing
``test_atomic_emit_b7.py`` tests. AC6 (temperature ≤ 0.3) is enforced
at the provider layer (``providers/openai/adapter.py:76`` sets
``temperature=0.2``); a static-grep test pins that.
"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402
import atomic_emit  # noqa: E402
import model_router  # noqa: E402
import assemble_adapter  # noqa: E402
import assemble_cache  # noqa: E402


@pytest.fixture(autouse=True)
def _stage_repo(tmp_path, monkeypatch):
    """Build a minimal install + catalog so the v2 link stage + catalog
    gate succeed; tests stub atomic_emit to skip the live LLM call."""
    # config.md with the canonical aliases table.
    sq = tmp_path / ".squidsquad"
    sq.mkdir()
    (sq / "config.md").write_text(
        "## Aliases\n\n"
        "| alias | role-class | L3 domain |\n"
        "|---|---|---|\n"
        "| pm | pm | — |\n",
        encoding="utf-8",
    )
    # Catalog so D3 gate doesn't abort.
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "sub-skill-catalog.md").write_text(
        "## `common/` — common\n\n"
        "| Sub-skill | One-liner | Used by |\n"
        "|---|---|---|\n"
        "| `boot-bootstrap` | x | all |\n",
        encoding="utf-8",
    )
    # Source frontmatter files for emit_v2_linked to find.
    refs = tmp_path / "references"
    for slot, ordinal, body in (
        ("identity", 10, "Identity base.\n"),
        ("responsibility", 10, "Responsibility base.\n"),
        ("soul", 10, "Soul base.\n"),
        ("instructions", 10, "### step:cycle/boot\nBoot body.\n"),
        ("vault", 10, "Vault base.\n"),
    ):
        path = refs / "roles" / f"{slot}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"---\nslot: {slot}\nordinal: {ordinal}\n---\n\n{body}",
            encoding="utf-8",
        )
    return tmp_path


# ---------------------------------------------------------------------------
# AC1 — deploy_alias_v2 invokes atomic_emit.assemble_and_emit
# ---------------------------------------------------------------------------


class TestAssembleWired:

    def test_deploy_alias_v2_invokes_assemble_and_emit(
        self, _stage_repo, monkeypatch,
    ):
        calls = []

        def tracking(
            linked_composite, output_dir, *, role_class, model_id="<unknown>",
            commit_sha="<unknown>", generated_at=None,
            filename_suffix=".v2.md", **kwargs,
        ):
            calls.append({
                "linked_composite_len": len(linked_composite),
                "output_dir": Path(output_dir),
                "role_class": role_class,
                "model_id": model_id,
                "filename_suffix": filename_suffix,
                "has_cache_lookup": "cache_lookup_fn" in kwargs and kwargs["cache_lookup_fn"] is not None,
                "has_cache_store": "cache_store_fn" in kwargs and kwargs["cache_store_fn"] is not None,
            })
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            paths = (
                output_dir / f"CLAUDE{filename_suffix}",
                output_dir / f"CLAUDE.linked{filename_suffix}",
                output_dir / f"CLAUDE.conflicts{filename_suffix}",
            )
            for p in paths:
                p.write_text(linked_composite, encoding="utf-8")
            return paths

        monkeypatch.setattr(atomic_emit, "assemble_and_emit", tracking)
        compose.deploy_alias_v2("pm", target_root=_stage_repo)
        assert len(calls) == 1
        c = calls[0]
        assert c["role_class"] == "pm"
        # AC5: model_id passed to atomic_emit is the locked "sonnet".
        assert c["model_id"] == "sonnet"
        # AC4: cache seams plumbed through.
        assert c["has_cache_lookup"] is True
        assert c["has_cache_store"] is True
        # AC3: §9a-safe default.
        assert c["filename_suffix"] == ".v2.md"


# ---------------------------------------------------------------------------
# AC2 — outputs land at v2 paths; v1 paths untouched
# ---------------------------------------------------------------------------


class TestV2PathCoexistence:

    def _stub(self, monkeypatch):
        def fake(
            linked_composite, output_dir, *, role_class, model_id="<unknown>",
            commit_sha="<unknown>", generated_at=None,
            filename_suffix=".v2.md", **kwargs,
        ):
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            paths = (
                output_dir / f"CLAUDE{filename_suffix}",
                output_dir / f"CLAUDE.linked{filename_suffix}",
                output_dir / f"CLAUDE.conflicts{filename_suffix}",
            )
            for p in paths:
                p.write_text(linked_composite, encoding="utf-8")
            return paths

        monkeypatch.setattr(atomic_emit, "assemble_and_emit", fake)

    def test_v2_triple_lands_at_v2_paths(self, _stage_repo, monkeypatch):
        self._stub(monkeypatch)
        out = compose.deploy_alias_v2("pm", target_root=_stage_repo)
        alias_dir = _stage_repo / ".squidsquad" / "pm"
        assert (alias_dir / "CLAUDE.v2.md").exists()
        assert (alias_dir / "CLAUDE.linked.v2.md").exists()
        assert (alias_dir / "CLAUDE.conflicts.v2.md").exists()
        # deploy_alias_v2 returns the assembled CLAUDE.v2.md.
        assert out == alias_dir / "CLAUDE.v2.md"

    def test_v1_canonical_paths_not_written(self, _stage_repo, monkeypatch):
        # AC2: §9a coexistence. v2 path must NEVER write v1 canonical
        # filenames. Operator's v1 CLAUDE.md is sacred until E6.
        self._stub(monkeypatch)
        compose.deploy_alias_v2("pm", target_root=_stage_repo)
        alias_dir = _stage_repo / ".squidsquad" / "pm"
        assert not (alias_dir / "CLAUDE.md").exists()
        assert not (alias_dir / "CLAUDE.linked.md").exists()
        assert not (alias_dir / "CLAUDE.conflicts.md").exists()


# ---------------------------------------------------------------------------
# AC4 — cache adapter round-trips through B6's real cache_lookup/store
# ---------------------------------------------------------------------------


class TestCacheAdapter:

    def test_adapter_lookup_returns_none_on_cold_cache(self, tmp_path, monkeypatch):
        # Redirect the cache root to tmp_path so we don't touch the
        # real repo's cache.
        monkeypatch.setattr(assemble_cache, "_REPO_ROOT", tmp_path)
        lookup, _store = assemble_adapter.make_b6_cache_adapter(
            alias="pm", model_id="sonnet", prompt_version="v1",
        )
        assert lookup("identity", "linked body") is None

    def test_adapter_store_then_lookup_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(assemble_cache, "_REPO_ROOT", tmp_path)
        lookup, store = assemble_adapter.make_b6_cache_adapter(
            alias="pm", model_id="sonnet", prompt_version="v1",
        )
        store("identity", "linked body", "assembled body")
        assert lookup("identity", "linked body") == "assembled body"

    def test_adapter_keys_differ_per_slot(self, tmp_path, monkeypatch):
        monkeypatch.setattr(assemble_cache, "_REPO_ROOT", tmp_path)
        lookup, store = assemble_adapter.make_b6_cache_adapter(
            alias="pm", model_id="sonnet", prompt_version="v1",
        )
        # Same linked body, different slot → cache hit/miss are
        # independent (the slot name + purpose are baked into the key).
        store("identity", "linked", "ID assembled")
        assert lookup("soul", "linked") is None
        assert lookup("identity", "linked") == "ID assembled"

    def test_adapter_model_id_invalidates_cache(self, tmp_path, monkeypatch):
        # PRD-B SC7 + B9 AC4: switching models must not produce a
        # silent cache hit on stale prose. Same alias + slot + body +
        # prompt_version but a different model_id → cache miss.
        monkeypatch.setattr(assemble_cache, "_REPO_ROOT", tmp_path)
        sonnet_lookup, sonnet_store = assemble_adapter.make_b6_cache_adapter(
            alias="pm", model_id="sonnet", prompt_version="v1",
        )
        haiku_lookup, _ = assemble_adapter.make_b6_cache_adapter(
            alias="pm", model_id="haiku", prompt_version="v1",
        )
        sonnet_store("identity", "linked", "ID by sonnet")
        assert sonnet_lookup("identity", "linked") == "ID by sonnet"
        assert haiku_lookup("identity", "linked") is None

    def test_adapter_prompt_version_invalidates_cache(
        self, tmp_path, monkeypatch,
    ):
        monkeypatch.setattr(assemble_cache, "_REPO_ROOT", tmp_path)
        v1_lookup, v1_store = assemble_adapter.make_b6_cache_adapter(
            alias="pm", model_id="sonnet", prompt_version="v1",
        )
        v2_lookup, _ = assemble_adapter.make_b6_cache_adapter(
            alias="pm", model_id="sonnet", prompt_version="v2",
        )
        v1_store("identity", "linked", "ID v1")
        assert v1_lookup("identity", "linked") == "ID v1"
        assert v2_lookup("identity", "linked") is None


# ---------------------------------------------------------------------------
# AC5 — assemble model locked to "sonnet"
# ---------------------------------------------------------------------------


class TestAssembleModelLocked:

    def test_get_model_for_task_assemble_returns_sonnet(self):
        # Compose-time constant per PRD-B SC10 — NOT resolved from
        # config.md. The branch fires BEFORE the SQUIDSQUAD_MODEL_OVERRIDE
        # env var check + config-routing fall-through so an operator
        # cannot accidentally swap the model.
        assert model_router.get_model_for_task("assemble") == "sonnet"

    def test_assemble_model_lock_overrides_env_var(self, monkeypatch):
        monkeypatch.setenv("SQUIDSQUAD_MODEL_OVERRIDE", "haiku")
        # Lock wins.
        assert model_router.get_model_for_task("assemble") == "sonnet"


# ---------------------------------------------------------------------------
# AC6 — temperature ≤ 0.3 enforced in provider adapter
# ---------------------------------------------------------------------------


class TestAssembleTemperatureLock:

    def test_openai_adapter_caps_temperature_at_or_below_0_3(self):
        # Static-grep on the OpenAI adapter — the only call-site that
        # constructs the chat.completions.create kwargs for the
        # assemble task. The adapter pre-#10763 already hardcoded
        # ``temperature: 0.2`` (which satisfies AC6's ≤ 0.3); this test
        # pins that value so a future refactor that bumps it surfaces
        # as a clear regression naming AC6.
        adapter_src = (
            SCRIPTS / "providers" / "openai" / "adapter.py"
        ).read_text(encoding="utf-8")
        # Extract any literal `"temperature": <num>` occurrence.
        import re
        matches = re.findall(r'"temperature"\s*:\s*([0-9.]+)', adapter_src)
        assert matches, (
            "openai adapter must set a literal temperature value in the "
            "chat.completions.create kwargs (PRD-B B9 #10763 AC6)"
        )
        for raw in matches:
            value = float(raw)
            assert value <= 0.3, (
                f"openai adapter temperature {value} > 0.3 — violates "
                f"PRD-B B9 #10763 AC6"
            )

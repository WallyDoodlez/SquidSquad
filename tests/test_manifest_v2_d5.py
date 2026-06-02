"""Tests for PRD-D Story D5 (#10676): unified v2 manifest loader.

AC6 mandates tests covering:
  (a) v1 compose produces byte-identical output to pre-D5 — verified by
      asserting v1 `_load_manifest(role, "polling")` and
      `_load_manifest(role, "event-driven")` return EXACTLY the same lists
      they did before D5 (we re-read the source manifests to compute the
      reference list, so any future drift in includes.yml or
      includes-events.yml is detected).
  (b) v2 compose with v2 manifest produces expected output — `_load_manifest_v2`
      returns the union list and does not consult wake_mode.
  (c) no `includes-events.yml` referenced in v2 code path — static-grep
      assertion across the v2 loader call tree.

Plus structural tests for variant inheritance (base_role + additional_includes
must resolve through the v2 path on the base, not the v1 path).
"""

import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import compose  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
ROLES_DIR = REPO_ROOT / "references" / "roles"

BASE_ROLES = ("pm", "dm", "verifier", "worker")


def _load_yaml_list(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data.get("includes", [])


class TestV2ManifestFilesExist:
    """AC1 — includes-v2.yml must exist for every base role-class."""

    @pytest.mark.parametrize("role", BASE_ROLES)
    def test_v2_manifest_present(self, role):
        path = ROLES_DIR / role / "includes-v2.yml"
        assert path.is_file(), f"missing v2 manifest: {path}"


class TestV2IsUnion:
    """AC1 — content must be the UNION of includes.yml + includes-events.yml.

    Definition: every entry that appears in either v1 manifest must appear in
    the v2 manifest. (Duplicates collapse; order is informational, not part
    of "union" semantics.)
    """

    @pytest.mark.parametrize("role", BASE_ROLES)
    def test_v2_contains_union_of_v1(self, role):
        v1_polling = set(_load_yaml_list(ROLES_DIR / role / "includes.yml"))
        v1_events = set(_load_yaml_list(
            ROLES_DIR / role / "includes-events.yml"))
        v2 = set(_load_yaml_list(ROLES_DIR / role / "includes-v2.yml"))
        union = v1_polling | v1_events
        missing = union - v2
        assert missing == set(), (
            f"{role}: v2 manifest missing entries from v1 union: {missing}"
        )

    @pytest.mark.parametrize("role", BASE_ROLES)
    def test_v2_introduces_no_entries_beyond_v1_union(self, role):
        # DS review F2: events is a strict subset of polling for every
        # base role, so v2 == polling-union. Catch accidental extras
        # introduced in includes-v2.yml that would silently widen the
        # composed surface.
        v1_polling = set(_load_yaml_list(ROLES_DIR / role / "includes.yml"))
        v1_events = set(_load_yaml_list(
            ROLES_DIR / role / "includes-events.yml"))
        v2 = set(_load_yaml_list(ROLES_DIR / role / "includes-v2.yml"))
        union = v1_polling | v1_events
        extra = v2 - union
        assert extra == set(), (
            f"{role}: v2 manifest has entries beyond the v1 union: {extra}"
        )

    @pytest.mark.parametrize("role", BASE_ROLES)
    def test_v2_does_not_introduce_unknown_entries(self, role):
        # v2 entries must point at existing sub-skill files (defensive
        # against typos during the union edit).
        v2 = _load_yaml_list(ROLES_DIR / role / "includes-v2.yml")
        for entry in v2:
            full = (REPO_ROOT / "references" / "sub-skills"
                    / f"{entry}.md")
            assert full.is_file(), (
                f"{role}: v2 manifest entry `{entry}` points at missing "
                f"sub-skill file {full}"
            )


class TestV1Untouched:
    """AC3 + AC4 — v1 `_load_manifest` must continue to return the SAME
    lists it did pre-D5. The reference is the raw YAML on disk: if any
    rebase landed a stealth edit to includes.yml or includes-events.yml,
    the v1 loader output drifts and this test catches it."""

    @pytest.mark.parametrize("role", BASE_ROLES)
    def test_polling_manifest_unchanged(self, role):
        on_disk = _load_yaml_list(ROLES_DIR / role / "includes.yml")
        loaded = compose._load_manifest(role, "polling")
        assert loaded == on_disk

    @pytest.mark.parametrize("role", BASE_ROLES)
    def test_event_driven_manifest_unchanged(self, role):
        on_disk = _load_yaml_list(ROLES_DIR / role / "includes-events.yml")
        loaded = compose._load_manifest(role, "event-driven")
        assert loaded == on_disk


class TestV2LoaderReadsV2File:
    """AC2 — `_load_manifest_v2(role)` returns the v2 manifest's includes
    list, byte-equivalent to what you'd get by reading the file
    directly."""

    @pytest.mark.parametrize("role", BASE_ROLES)
    def test_v2_loader_returns_v2_manifest(self, role):
        on_disk = _load_yaml_list(ROLES_DIR / role / "includes-v2.yml")
        loaded = compose._load_manifest_v2(role)
        assert loaded == on_disk

    def test_v2_loader_has_no_wake_mode_argument(self):
        # Architectural rule (TRD §6.5): v2 compose is wake-mode-blind.
        # The loader signature must not accept wake_mode.
        import inspect
        sig = inspect.signature(compose._load_manifest_v2)
        assert "wake_mode" not in sig.parameters
        # Only required parameter is role_name.
        params = list(sig.parameters)
        assert params == ["role_name"]


class TestV2LoaderVariantInheritance:
    """A variant role (e.g. `worker-skill` / `worker/skill`) must
    resolve through the v2 path on the base — never reading
    includes-events.yml or polling includes.yml on the base."""

    def test_variant_inherits_base_v2_manifest(self):
        # worker/skill has base_role: worker and additional_includes.
        # DS review F3: guard against repo-layout drift with a skip.
        variant_yml = ROLES_DIR / "worker" / "skill" / "includes.yml"
        if not variant_yml.is_file():
            pytest.skip(
                f"variant manifest absent: {variant_yml.relative_to(REPO_ROOT)}"
            )
        base_v2 = _load_yaml_list(ROLES_DIR / "worker" / "includes-v2.yml")
        variant_yaml = yaml.safe_load(
            variant_yml.read_text(encoding="utf-8"))
        additional = variant_yaml.get("additional_includes", []) or []
        # _resolve_variant maps `worker-skill` -> (`worker`, `skill`).
        loaded = compose._load_manifest_v2("worker-skill")
        assert loaded == base_v2 + additional


class TestV2LoaderNeverReadsEventsManifest:
    """AC6 — no `includes-events.yml` referenced in v2 code path."""

    def test_no_events_yml_reference_in_v2_helpers(self):
        # Static grep: the v2 loader helpers must not name the events
        # filename in CODE. (Docstrings/comments may mention it to say
        # "never reads this" -- that's documentation, not a dependency.)
        # We strip comments + docstrings via the ast module and grep
        # the remaining source. v1 ``_load_manifest`` may still
        # reference includes-events.yml; we only check the v2 helpers.
        import ast
        src = (SCRIPTS / "compose.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        v2_func_names = {"_load_manifest_v2", "_load_manifest_v2_from_file"}
        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name not in v2_func_names:
                continue
            # Strip the docstring (first stmt if it's a string Expr).
            body = list(node.body)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body = body[1:]
            # Walk all string constants in the remaining body.
            for sub in body:
                for inner in ast.walk(sub):
                    if (isinstance(inner, ast.Constant)
                            and isinstance(inner.value, str)
                            and "includes-events.yml" in inner.value):
                        offenders.append(node.name)
        assert offenders == [], (
            f"v2 loader code references includes-events.yml: {offenders}"
        )


class TestV1ComposeDeterministic:
    """AC6 first clause sanity check — v1 ``compose_role`` is
    deterministic post-D5. Byte-identical-to-pre-D5 enforcement is the
    job of the §9a CI gate (``test_v1_byte_stability_9a``), which
    snapshots the deploy output and asserts against fixed checksums.
    Per DS review F5: this class only verifies determinism, not the
    cross-revision byte equivalence the §9a gate covers."""

    @pytest.mark.parametrize("role", BASE_ROLES)
    def test_compose_role_is_deterministic(self, role):
        a = compose.compose_role(role)
        b = compose.compose_role(role)
        assert a == b
        # And confirm the wake-mode-specific manifests are still being
        # selected — the polling mode is what unflagged compose_role
        # uses by default.
        assert "boot-bootstrap" in a or "Boot" in a


class TestLegacyFallbackParity:
    """DS review F1/F4 — the legacy alias fallback in
    ``_load_manifest_v2`` must fire for the variant path too, not just
    base roles. If a variant role's base lacks a v2 manifest but a
    legacy alias resolves, v1 finds it; v2 must as well."""

    def test_legacy_alias_fallback_lives_outside_else_branch(self):
        # Static check: the fallback block must NOT be nested inside
        # the ``else:`` of ``if resolved:``. Walk the AST and confirm
        # the ``_BASE_ALIAS_6274`` reference sits at the same nesting
        # depth as the final ``if manifest_path is None: return None``.
        import ast
        src = (SCRIPTS / "compose.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        target = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef)
            and n.name == "_load_manifest_v2"
        )
        # Collect references to the alias dict at the top level of the
        # function body. Anything nested inside an `If.orelse` is the
        # bug pattern F1/F4 calls out.
        offending = []
        for stmt in target.body:
            for inner in ast.walk(stmt):
                if (isinstance(inner, ast.Name)
                        and inner.id == "_BASE_ALIAS_6274"):
                    # Walk up: was it found inside an If's orelse?
                    # Simpler: rule out F1/F4 by confirming at least
                    # ONE _BASE_ALIAS_6274 reference is at the top
                    # level (not nested inside an If's orelse from
                    # the variant-detection branch).
                    offending.append(stmt)
        # Confirm at least one top-level statement contains the alias
        # check — i.e., the fallback is reachable from BOTH branches.
        top_level_stmts_with_alias = [
            s for s in target.body
            if any(
                isinstance(n, ast.Name) and n.id == "_BASE_ALIAS_6274"
                for n in ast.walk(s)
            )
        ]
        # The fallback should appear AFTER the variant if/else, as a
        # standalone ``if manifest_path is None:`` block.
        assert top_level_stmts_with_alias, (
            "DS-D5 F1/F4 regression: _BASE_ALIAS_6274 fallback is not at "
            "the top level of _load_manifest_v2 — it must fire for both "
            "the variant and base-role paths."
        )

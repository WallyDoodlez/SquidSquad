"""#14055 -- wrong-target code-review guard + stale-artifact hygiene.

An agentic routed reviewer (repo read access) latched onto two stale
committed .deepseek-*.diff artifacts instead of the submitted patch and
returned a wrong-target review with exit 0 (live occurrence 2026-07-20,
task-id 13859-t3). The guard makes that failure loud: a code-review response
that references NONE of the submitted input basenames (nor any path from the
inputs' unified-diff headers) is discarded with exit 1, so the caller's
Claude fallback fires. NO_FINDINGS is exempt (a clean review legitimately
names nothing). The two stray artifacts are removed and the pattern
gitignored.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import model_router  # noqa: E402


class TestReviewTargetTokens:
    def test_basenames_collected(self, tmp_path):
        f = tmp_path / "my-change.patch"
        f.write_text("not a diff at all\n", encoding="utf-8")
        tokens = model_router._review_target_tokens(str(f))
        assert "my-change.patch" in tokens

    def test_diff_header_paths_collected(self, tmp_path):
        f = tmp_path / "t3.patch"
        f.write_text(
            "diff --git a/references/scripts/foo.py b/references/scripts/foo.py\n"
            "--- a/references/scripts/foo.py\n"
            "+++ b/references/scripts/foo.py\n"
            "@@ -1 +1 @@\n-old\n+new\n"
            "+++ b/tests/test_foo.py\n",
            encoding="utf-8",
        )
        tokens = model_router._review_target_tokens(str(f))
        assert "foo.py" in tokens
        assert "test_foo.py" in tokens
        assert "t3.patch" in tokens

    def test_multiple_and_missing_inputs(self, tmp_path):
        f = tmp_path / "ctx.txt"
        f.write_text("context\n", encoding="utf-8")
        tokens = model_router._review_target_tokens(
            f"{f},{tmp_path / 'does-not-exist.patch'}")
        # Unreadable input still contributes its basename (the reviewer was
        # told about it); only content parsing is skipped.
        assert "ctx.txt" in tokens
        assert "does-not-exist.patch" in tokens

    def test_empty_input_empty_tokens(self):
        assert model_router._review_target_tokens("") == set()
        assert model_router._review_target_tokens(None) == set()


class TestReviewReferencesTargets:
    def test_wrong_target_review_detected(self, tmp_path):
        """The live hijack shape: review discusses entirely different files."""
        f = tmp_path / "t3-diff.patch"
        f.write_text("+++ b/references/skills/vault-search/scripts/compact-telemetry.mjs\n",
                     encoding="utf-8")
        hijacked = ("### Finding 1\n- **File**: `.deepseek-9930.diff` (state_bus.py)\n"
                    "- **Issue**: rebase violates the operator rule\n")
        assert model_router.review_references_targets(hijacked, str(f)) is False

    def test_genuine_review_by_container_basename(self, tmp_path):
        f = tmp_path / "t3-diff.patch"
        f.write_text("some content\n", encoding="utf-8")
        review = "Finding 1: in t3-diff.patch line 4, the loop is wrong."
        assert model_router.review_references_targets(review, str(f)) is True

    def test_genuine_review_by_inner_diff_path(self, tmp_path):
        f = tmp_path / "t3-diff.patch"
        f.write_text("+++ b/references/scripts/vault_optimize.py\n", encoding="utf-8")
        review = ("### Finding 1\n- **File**: references/scripts/vault_optimize.py\n"
                  "- **Issue**: subprocess timeout unhandled\n")
        assert model_router.review_references_targets(review, str(f)) is True

    def test_no_tokens_fails_open(self):
        assert model_router.review_references_targets("anything", "") is True


class TestArtifactHygiene:
    def test_stray_artifacts_removed_from_tree(self):
        # Full sweep per PM's enumeration on #14055 (root .diff/.out pairs +
        # the PM-planning stray, folded in with PM's authorization).
        for stray in (".deepseek-9902.diff", ".deepseek-9930.diff",
                      ".deepseek-9902.out", ".deepseek-9930.out",
                      ".squidsquad/pm/planning/.deepseek-13213.diff"):
            assert not (REPO / stray).exists(), stray

    def test_patterns_gitignored(self):
        lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
        assert ".deepseek-*.diff" in lines
        assert ".deepseek-*.out" in lines
        assert ".squidsquad/*/planning/.deepseek-*" in lines


class TestRouteGuardWiring:
    """The guard must live on route()'s code-review success path: non-sentinel
    response referencing no target -> exit 1, error-stub output, diagnostic
    action wrong-target-review; sentinel and on-target responses unaffected."""

    def _run_route(self, monkeypatch, tmp_path, response_text):
        calls = {}

        class FakeAdapter:
            @staticmethod
            def call(**kwargs):
                return response_text

        monkeypatch.setattr(model_router, "get_model_for_task", lambda t: "deepseek-chat")
        monkeypatch.setattr(model_router, "_load_provider_manifest",
                            lambda m: ("fake", {"auth": {}}))
        monkeypatch.setattr(model_router, "_ensure_deps", lambda m: None)
        monkeypatch.setattr(model_router, "_load_adapter", lambda m: FakeAdapter)
        monkeypatch.setattr(model_router, "_log_diagnostic",
                            lambda e: calls.setdefault("actions", []).append(e.get("action")))
        patch = tmp_path / "change.patch"
        patch.write_text("+++ b/references/scripts/foo.py\n", encoding="utf-8")
        out = tmp_path / "REVIEW.md"
        code = model_router.route("code-review", "14055-test", str(patch), str(out), "ctx")
        return code, out, calls

    def test_wrong_target_exits_1_with_error_stub(self, monkeypatch, tmp_path):
        long_off_target = ("### Finding 1\n- **File**: `.deepseek-9930.diff`\n"
                          "- **Issue**: something about state_bus entirely\n") * 10
        code, out, calls = self._run_route(monkeypatch, tmp_path, long_off_target)
        assert code == 1
        assert out.read_text(encoding="utf-8").startswith("# STATUS: error -- wrong-target")
        assert "wrong-target-review" in calls["actions"]

    def test_on_target_review_passes(self, monkeypatch, tmp_path):
        on_target = ("### Finding 1\n- **File**: references/scripts/foo.py\n"
                     "- **Issue**: detailed, plausible, long enough finding\n") * 10
        code, out, calls = self._run_route(monkeypatch, tmp_path, on_target)
        assert code == 0
        assert "foo.py" in out.read_text(encoding="utf-8")
        assert "wrong-target-review" not in calls.get("actions", [])

    def test_no_findings_sentinel_exempt(self, monkeypatch, tmp_path):
        code, out, calls = self._run_route(monkeypatch, tmp_path, "NO_FINDINGS")
        assert code == 0
        assert "NO_FINDINGS" in out.read_text(encoding="utf-8")
        assert "wrong-target-review" not in calls.get("actions", [])

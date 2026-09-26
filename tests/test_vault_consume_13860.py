"""#13860 P4 commit 2 -- lineage + receipt seams (VAULT-ARCH 9.3/9.4/9.9).

vault_consume.py makes the deterministic parts of the consumption pipeline
scripts: the single canonical lineage file per issue, the receipt gate the
verifier runs, the bug-flow fix-plan skeleton, and honest engine degradation.
git_ops._is_lineage_file lets that file ride the task branch into the PR diff
(the gate requires it there).
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops  # noqa: E402
import vault_consume as vc  # noqa: E402

NODE = shutil.which("node")


@pytest.fixture
def sq(tmp_path):
    d = tmp_path / ".squidsquad"
    for role in ("pm", "skill", "qa"):
        (d / role / "planning").mkdir(parents=True)
    return d


def write(sq, rel, text="x\n"):
    p = sq / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


GOOD = """# Plan

## Vault context consumed

- [[decision-merge-policy]] -- merge, never rebase; shapes the sync step

## Applicable rules

- None matched (searched rules lane: git, merge)
"""


class TestResolveLineage:
    def test_nothing_exists(self, sq):
        assert vc.resolve_lineage(42, sq) is None

    def test_context_beats_plan_body_beats_fix_plan(self, sq):
        write(sq, "skill/planning/42-fix-plan.md")
        assert vc.resolve_lineage(42, sq)["kind"] == "fix-plan"
        write(sq, "pm/planning/42-body.md")
        assert vc.resolve_lineage(42, sq)["kind"] == "plan-body"
        write(sq, "pm/planning/CONTEXT-42.md")
        res = vc.resolve_lineage(42, sq)
        assert res == {"path": ".squidsquad/pm/planning/CONTEXT-42.md", "kind": "context", "exists": True}

    def test_other_issue_numbers_and_bundle_context_ignored(self, sq):
        write(sq, "pm/planning/CONTEXT.md")
        write(sq, "pm/planning/CONTEXT-420.md")
        write(sq, "pm/planning/FEAT-PM-42-CONTEXT.md")
        assert vc.resolve_lineage(42, sq) is None

    def test_pm_dir_searched_first(self, sq):
        write(sq, "skill/planning/CONTEXT-42.md")
        write(sq, "pm/planning/CONTEXT-42.md")
        assert vc.resolve_lineage(42, sq)["path"] == ".squidsquad/pm/planning/CONTEXT-42.md"


class TestInitFixPlan:
    def test_creates_lean_skeleton(self, sq):
        res = vc.init_fix_plan(7, "skill", sq)
        assert res == {"path": ".squidsquad/skill/planning/7-fix-plan.md", "kind": "fix-plan",
                       "exists": True, "created": True}
        text = (sq / "skill/planning/7-fix-plan.md").read_text(encoding="utf-8")
        for h in ("## Root cause", "## Intended direction", "## Impact",
                  "## Vault context consumed", "## Applicable rules"):
            assert h in text
        assert not (sq / "skill/planning/7-fix-plan.md.tmp").exists()

    def test_skeleton_alone_fails_the_gate(self, sq):
        """Placeholders are not receipts -- a skeleton nobody filled must not pass."""
        vc.init_fix_plan(7, "skill", sq)
        assert vc.check_receipts(7, sq)["verdict"] == "fail"

    def test_idempotent_and_never_splits_lineage(self, sq):
        write(sq, "pm/planning/CONTEXT-7.md", "keep\n")
        res = vc.init_fix_plan(7, "skill", sq)
        assert res["kind"] == "context" and res["created"] is False
        assert not (sq / "skill/planning/7-fix-plan.md").exists()
        assert (sq / "pm/planning/CONTEXT-7.md").read_text(encoding="utf-8") == "keep\n"


class TestCheckSection:
    @pytest.mark.parametrize("body,status", [
        ("- [[a]] -- why\n- [[b|B]] — why too\n", "cited"),
        ("- [[a]]: why\n", "cited"),
        ("- None relevant (searched: x)\n", "none"),
        ("- Engine unavailable: node not installed\n", "unavailable"),
        ("", "empty"),
        ("_Filled at pickup consultation._\n", "empty"),
        ("- [[a]]\n", "malformed"),               # citation without relevance
        ("- see the decision note\n", "malformed"),
        ("- [[a]] -- why\n- None relevant\n", "malformed"),
        ("- Engine unavailable: x\n- [[a]] -- y\n", "malformed"),
    ])
    def test_context_section(self, body, status):
        text = f"## Vault context consumed\n\n{body}\n## Next\n- [[z]] -- elsewhere\n"
        assert vc.check_section(text, vc.CONTEXT_SECTION)[0] == status

    def test_rules_none_variant_is_none_matched(self):
        assert vc.check_section("## Applicable rules\n- None matched\n", vc.RULES_SECTION)[0] == "none"
        # the context-section wording does not satisfy the rules section
        assert vc.check_section("## Applicable rules\n- None relevant\n", vc.RULES_SECTION)[0] == "malformed"

    def test_missing(self):
        assert vc.check_section("# nothing\n", vc.RULES_SECTION)[0] == "missing"

    def test_last_occurrence_wins(self):
        text = "## Applicable rules\n- None matched\n\n## Applicable rules\n- [[rule-x]] -- applies\n"
        assert vc.check_section(text, vc.RULES_SECTION)[0] == "cited"


class TestCheckReceipts:
    def test_no_lineage_fails(self, sq):
        res = vc.check_receipts(9, sq)
        assert res["verdict"] == "fail" and "no lineage file" in res["problems"][0]

    def test_good_receipts_pass(self, sq):
        write(sq, "skill/planning/9-fix-plan.md", GOOD)
        assert vc.check_receipts(9, sq)["verdict"] == "pass"

    def test_engine_unavailable_passes_with_note(self, sq):
        write(sq, "skill/planning/9-fix-plan.md", GOOD.replace(
            "- [[decision-merge-policy]] -- merge, never rebase; shapes the sync step",
            "- Engine unavailable: node not installed"))
        res = vc.check_receipts(9, sq)
        assert res["verdict"] == "pass-with-note" and res["notes"]

    def test_lineage_must_be_in_diff(self, sq):
        write(sq, "skill/planning/9-fix-plan.md", GOOD)
        path = ".squidsquad/skill/planning/9-fix-plan.md"
        tree = vc.WorkTree(sq)
        assert vc.check_receipts(9, diff_base="origin/main", tree=tree,
                                 changed_files={path, "a.py"})["verdict"] == "pass"
        res = vc.check_receipts(9, diff_base="origin/main", tree=tree, changed_files={"a.py"})
        assert res["verdict"] == "fail" and "not in the PR diff" in res["problems"][0]

    def test_cli_exit_codes(self, sq, monkeypatch, capsys):
        monkeypatch.setattr(vc, "SQ_DIR", sq)
        assert vc.main(["check-receipts", "9"]) == 1
        assert json.loads(capsys.readouterr().out)["verdict"] == "fail"
        write(sq, "skill/planning/9-fix-plan.md", GOOD)
        assert vc.main(["check-receipts", "9"]) == 0
        assert json.loads(capsys.readouterr().out)["verdict"] == "pass"


class TestGateReadsCommittedTree:
    """With --diff-base the gate judges the COMMITTED lineage file (review
    finding on commit 2): an uncommitted working-tree fix must not pass."""

    @pytest.fixture
    def repo(self, tmp_path):
        def git(*a):
            subprocess.run(["git", *a], cwd=tmp_path, check=True, capture_output=True)
        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        write(tmp_path / ".squidsquad", "skill/planning/9-fix-plan.md",
              "## Vault context consumed\n\n## Applicable rules\n")
        git("add", "-A")
        git("commit", "-q", "-m", "bad receipts")
        return tmp_path

    def test_uncommitted_fix_does_not_pass(self, repo):
        write(repo / ".squidsquad", "skill/planning/9-fix-plan.md", GOOD)  # dirty, uncommitted
        path = ".squidsquad/skill/planning/9-fix-plan.md"
        res = vc.check_receipts(9, diff_base="base", changed_files={path},
                                tree=vc.GitTree("HEAD", cwd=repo))
        assert res["verdict"] == "fail"
        # the same content passes once committed
        subprocess.run(["git", "commit", "-qam", "fix"], cwd=repo, check=True, capture_output=True)
        res = vc.check_receipts(9, diff_base="base", changed_files={path},
                                tree=vc.GitTree("HEAD", cwd=repo))
        assert res["verdict"] == "pass"

    def test_uncommitted_lineage_file_is_not_found(self, repo):
        write(repo / ".squidsquad", "pm/planning/CONTEXT-9.md", GOOD)  # untracked
        res = vc.resolve_lineage(9, tree=vc.GitTree("HEAD", cwd=repo))
        assert res["kind"] == "fix-plan"


class TestEngineDegradation:
    def test_node_missing_is_honest_unavailable(self, monkeypatch):
        monkeypatch.setattr(vc.shutil, "which", lambda _: None)
        payload, reason = vc.search("skill", 1, tags=["x"])
        assert payload is None and reason == "node not installed"

    def test_engine_missing(self, monkeypatch):
        monkeypatch.setattr(vc.shutil, "which", lambda _: "node")
        monkeypatch.setattr(vc, "ENGINE_DIRS", (Path("/nonexistent"),))
        payload, reason = vc.search("skill", 1, tags=["x"])
        assert payload is None and "not installed" in reason

    def test_engine_nonzero_exit(self, monkeypatch):
        monkeypatch.setattr(vc.shutil, "which", lambda _: "node")
        proc = MagicMock(returncode=2, stdout="", stderr="bad args")
        payload, reason = vc.search("skill", 1, tags=["x"], runner=lambda *a, **k: proc)
        assert payload is None and "exited 2" in reason

    def test_cli_unavailable_exit_3(self, monkeypatch, capsys):
        monkeypatch.setattr(vc.shutil, "which", lambda _: None)
        assert vc.main(["search", "--alias", "skill", "--tags", "x"]) == 3
        assert json.loads(capsys.readouterr().out)["engine_unavailable"] is True

    def test_search_requires_query(self, capsys):
        assert vc.main(["search", "--alias", "skill"]) == 2

    def test_identity_falls_back_to_unprovisioned(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vc, "INSTANCE_ID_FILE", tmp_path / "absent")
        assert vc.identity_args("skill", 5) == ["--instance-id", "unprovisioned", "--alias", "skill", "--task", "5"]


@pytest.mark.skipif(NODE is None, reason="node unavailable")
class TestEngineLive:
    def test_search_and_cite_round_trip(self, tmp_path):
        vault = tmp_path / "vault"
        (vault / "galaxy").mkdir(parents=True)
        shutil.copy(REPO / "references" / "vault-schema-default.json", vault / "vault-schema.json")
        (vault / "galaxy" / "rule-x.md").write_text(
            "---\ntype: rule\ntags: [git]\nupdated: 2026-09-01\n---\n# X\n", encoding="utf-8")
        payload, reason = vc.search("skill", 13860, tags=["git"], types=["rule"], vault=vault)
        assert reason is None and [r["slug"] for r in payload["results"]] == ["rule-x"]
        payload, reason = vc.cite("skill", 13860, ["rule-x"], vault=vault)
        assert reason is None
        shards = list((vault / ".telemetry").glob("*.jsonl"))
        events = [json.loads(line) for s in shards for line in s.read_text(encoding="utf-8").splitlines()]
        assert {(e["slug"], e["counter"], e["task"]) for e in events} >= {
            ("rule-x", "impression", 13860), ("rule-x", "used", 13860)}


class TestLineageGuardExemption:
    @pytest.mark.parametrize("path", [
        ".squidsquad/pm/planning/12750-body.md",
        ".squidsquad/pm/planning/CONTEXT-13860.md",
        ".squidsquad/skill/planning/13860-fix-plan.md",
    ])
    def test_lineage_files_match(self, path):
        assert git_ops._is_lineage_file(path) is True

    @pytest.mark.parametrize("path", [
        ".squidsquad/pm/planning/CONTEXT.md",
        ".squidsquad/pm/planning/CONTEXT-9873-A.md",
        ".squidsquad/pm/planning/FEAT-PM-1075-CONTEXT.md",
        ".squidsquad/skill/planning/draft-fix-plan.md",
        ".squidsquad/skill/planning/sub/1-fix-plan.md",
        ".squidsquad/skill/working-state.md",
        ".squidsquad/vault/galaxy/decision-x.md",
        ".squidsquad/config.md",
        "references/scripts/git_ops.py",
    ])
    def test_non_lineage_do_not_match(self, path):
        assert git_ops._is_lineage_file(path) is False

    def test_guard_keeps_fix_plan_strips_state(self):
        staged = [".squidsquad/skill/planning/13860-fix-plan.md",
                  ".squidsquad/pm/planning/CONTEXT-13860.md",
                  ".squidsquad/pm/planning/CONTEXT-777.md",  # another issue's: stripped
                  ".squidsquad/skill/working-state.md"]
        resets = []

        def fake_run_list(cmd, check=True):
            r = MagicMock(stderr="", returncode=0, stdout="")
            if cmd[:4] == ["git", "diff", "--cached", "--name-only"]:
                r.stdout = "\n".join(staged) + "\n"
            elif cmd[:3] == ["git", "diff", "--cached"] and "--quiet" in cmd:
                r.returncode = 1
            elif cmd[:2] == ["git", "reset"]:
                resets.append(cmd[-1])
            return r

        with patch.object(git_ops, "_get_working_branch", return_value="main"), \
                patch.object(git_ops, "_run", return_value=MagicMock(stdout="squidsquad/task/13860\n", returncode=0)), \
                patch.object(git_ops, "_run_list", side_effect=fake_run_list):
            unstaged = git_ops.guard_staged_state()
        assert unstaged == [".squidsquad/pm/planning/CONTEXT-777.md", ".squidsquad/skill/working-state.md"]
        assert resets == unstaged

    def test_merge_gate_allows_lineage_in_pr(self):
        declared = [".squidsquad/skill/planning/13860-fix-plan.md",
                    ".squidsquad/skill/working-state.md", "a.py"]
        with patch.object(git_ops, "_pr_declared_files", return_value=declared), patch.object(git_ops, "_pr_head_issue", return_value=13860):
            assert git_ops._pr_state_scope_violations(1) == [".squidsquad/skill/working-state.md"]

    def test_merge_gate_refuses_other_issues_lineage(self):
        declared = [".squidsquad/skill/planning/777-fix-plan.md", "a.py"]
        with patch.object(git_ops, "_pr_declared_files", return_value=declared), patch.object(git_ops, "_pr_head_issue", return_value=13860):
            assert git_ops._pr_state_scope_violations(1) == [".squidsquad/skill/planning/777-fix-plan.md"]

    @pytest.mark.parametrize("path,issue,expected", [
        (".squidsquad/skill/planning/13860-fix-plan.md", 13860, True),
        (".squidsquad/skill/planning/13860-fix-plan.md", 777, False),
        (".squidsquad/pm/planning/CONTEXT-777.md", 13860, False),
        (".squidsquad/pm/planning/777-body.md", None, True),  # shape-only form
    ])
    def test_issue_scoping(self, path, issue, expected):
        assert git_ops._is_lineage_file(path, issue) is expected

    def test_issue_from_branch(self):
        assert git_ops._issue_from_branch("squidsquad/task/13860") == 13860
        assert git_ops._issue_from_branch("squidsquad/task/abc") is None
        assert git_ops._issue_from_branch("feature/x") is None
        assert git_ops._issue_from_branch("") is None


class TestIntakeInjection:
    PAYLOAD = {"results": [{"slug": "decision-a", "title": "A decision", "tier": "tag"},
                           {"slug": "rule-b", "title": "", "tier": "filename"}],
               "traversed": [{"slug": "system-c", "title": "C hub", "tier": "walked"}]}

    def test_render_cited(self):
        out = vc.render_context_section(self.PAYLOAD, None, "x")
        assert out.splitlines() == [
            "## Vault context", "",
            "- [[decision-a]] -- A decision (tag match)",
            "- [[rule-b]] -- rule-b (filename match)",
            "- [[system-c]] -- C hub (linked from a match)"]

    def test_render_caps_at_intake_top(self):
        many = {"results": [{"slug": f"n{i}", "title": "t", "tier": "content"} for i in range(9)],
                "traversed": []}
        out = vc.render_context_section(many, None, "x")
        assert out.count("- [[") == vc.INTAKE_TOP

    def test_render_none_and_unavailable(self):
        assert "- None relevant (searched: git, merge)" in vc.render_context_section(
            {"results": [], "traversed": []}, None, "git, merge")
        assert "- Engine unavailable: node not installed" in vc.render_context_section(
            None, "node not installed", "x")

    def test_replace_section_appends_then_replaces(self):
        body = "Intro\n\n## Acceptance Criteria\n1. a\n"
        once = vc.replace_section(body, vc.INTAKE_SECTION, "## Vault context\n\n- [[x]] -- y\n")
        assert once.endswith("## Vault context\n\n- [[x]] -- y\n")
        twice = vc.replace_section(once, vc.INTAKE_SECTION, "## Vault context\n\n- [[z]] -- w\n")
        assert twice.count("## Vault context") == 1 and "[[x]]" not in twice and "[[z]]" in twice
        assert "## Acceptance Criteria\n1. a" in twice

    def test_replace_keeps_following_sections(self):
        body = "## Vault context\n\n- old\n\n## Out of scope\n- b\n"
        out = vc.replace_section(body, vc.INTAKE_SECTION, "## Vault context\n\n- new\n")
        assert out == "## Vault context\n\n- new\n\n## Out of scope\n- b\n"

    def test_consumed_heading_is_not_the_intake_heading(self):
        body = "## Vault context consumed\n- [[a]] -- b\n"
        out = vc.replace_section(body, vc.INTAKE_SECTION, "## Vault context\n\n- new\n")
        assert "## Vault context consumed\n- [[a]] -- b" in out and out.count("## Vault context\n") == 1

    def test_inject_attributes_to_issue_and_writes_body(self):
        calls = {}

        def fake_search(alias, task, entities, tags, terms, top=None):
            calls["search"] = (alias, task, tuple(tags), top)
            return self.PAYLOAD, None

        def fake_view(n):
            return MagicMock(returncode=0, stdout="Body\n", stderr="")

        def fake_edit(n, body):
            calls["edit"] = (n, body)
            return MagicMock(returncode=0, stderr="")

        section = vc.inject_context(77, "pm", tags=["git"], search_fn=fake_search,
                                    view_fn=fake_view, edit_fn=fake_edit)
        assert calls["search"] == ("pm", 77, ("git",), vc.INTAKE_TOP)
        assert calls["edit"][0] == 77 and calls["edit"][1] == "Body\n\n" + section

    def test_inject_raises_when_edit_fails(self):
        with pytest.raises(RuntimeError, match="edit"):
            vc.inject_context(1, "pm", tags=["x"],
                              search_fn=lambda *a, **k: (None, "node not installed"),
                              view_fn=lambda n: MagicMock(returncode=0, stdout="B", stderr=""),
                              edit_fn=lambda n, b: MagicMock(returncode=1, stderr="nope"))

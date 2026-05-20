"""Regression tests for the #9574 comprehension-runner output contract.

Background: `references/scripts/run_comprehension_test.py` spawns two
`claude -p` subagents — a test agent that produces answers and an
eval agent that produces pass/fail JSON. The pre-#9574 design asked
both agents to invoke the `Write` tool to persist their output to
disk; in headless `claude -p` on Windows that path was unreliable
(the inner agent narrated permission-grant requirements that have no
interactive prompt to satisfy, then exited rc=0 with no file). #9574
switches the contract to `--output-format json` and harvests the
assistant's final message text (the `result` field); the runner does
the on-disk write from Python. The Write-tool dependency is gone.

This file pins:

1. Behavioral — `run_test()` exits non-zero when the inner agent
   returns no usable text. The pre-fix runner wrote a placeholder
   answers file and continued, masking the regression.

2. Behavioral — when the agent returns valid text, the runner DOES
   write `answers.md` to disk (proving the Python-side write path is
   wired up end-to-end without needing a real `claude` call).

3. Contract — `_run_agent` invokes `claude` with
   `--output-format json` and parses the `result` field. A future
   refactor that reverts to `text` output + a Write-tool prompt step
   reintroduces the exact failure mode #9574 fixed.
"""

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
RUNNER_PATH = REPO_ROOT / "references" / "scripts" / "run_comprehension_test.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "_runner_for_9574", RUNNER_PATH
    )
    if not (spec and spec.loader):
        raise ImportError(f"cannot load {RUNNER_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_proc(stdout="", stderr="", returncode=0):
    """Build a CompletedProcess-shaped object for the test mocks."""
    class _Proc:
        pass
    p = _Proc()
    p.stdout = stdout
    p.stderr = stderr
    p.returncode = returncode
    return p


class TestRunnerExitsNonZeroOnEmptyAgentOutput(unittest.TestCase):
    """When the test subagent returns no usable assistant text, the
    runner must exit 1. The pre-#9574 runner wrote a fallback
    ('# No answers generated') answers.md and continued, which hid
    the prompt-following bug end-to-end."""

    def setUp(self):
        self.runner = _load_runner()
        self.tmpdir = Path(tempfile.mkdtemp(prefix="cq9574-"))
        self.spec_path = self.tmpdir / "fake_spec.json"
        self.spec_path.write_text(
            json.dumps({
                "issue": 9999,
                "title": "fake spec for runner contract test",
                "files": ["README.md"],
                "questions": [
                    {"id": "q1", "question": "what?",
                     "expected": "anything"}
                ],
            }),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_agent_text_causes_nonzero_exit(self):
        """Simulate the #9574 failure mode: subagent returns rc=0 but
        empty assistant text. Runner must exit 1, not paper over with
        a placeholder file."""
        with mock.patch.object(
            self.runner, "_run_agent",
            return_value=("", _make_proc(stdout="{}", returncode=0)),
        ), mock.patch.object(
            self.runner, "_find_claude", return_value="/fake/claude",
        ), mock.patch.dict(os.environ, {"FORCE_CQ": "1"}):
            with self.assertRaises(SystemExit) as cm:
                self.runner.run_test(self.spec_path)
            self.assertNotEqual(
                cm.exception.code, 0,
                msg=(
                    "Runner must exit non-zero when the test agent's "
                    "JSON `result` field is empty. The pre-#9574 "
                    "silent-fallback behavior hid the regression for "
                    "months."
                ),
            )

    def test_no_placeholder_answers_file_on_empty_output(self):
        """The pre-#9574 runner wrote '# No answers generated' to
        answers.md when the agent gave nothing. That fallback masked
        the failure (eval stage proceeded against fake content,
        runner reported a clean FAIL row instead of a runner error).
        Make sure no placeholder is written under the new contract."""
        output_dir = self.tmpdir / ".out"
        with mock.patch.object(
            self.runner, "_run_agent",
            return_value=("", _make_proc(stdout="{}", returncode=0)),
        ), mock.patch.object(
            self.runner, "_find_claude", return_value="/fake/claude",
        ), mock.patch.dict(os.environ, {"FORCE_CQ": "1"}):
            try:
                self.runner.run_test(self.spec_path, output_dir=output_dir)
            except SystemExit:
                pass

        placeholder = output_dir / "answers.md"
        self.assertFalse(
            placeholder.exists(),
            msg=(
                "Runner must not write a placeholder answers.md when "
                "the test agent returns empty content (#9574)."
            ),
        )

    def test_valid_agent_output_writes_files_from_python(self):
        """Positive path: when the test agent returns markdown
        answers and the eval agent returns a valid JSON array, the
        runner writes both files from Python. Proves the on-disk
        path is wired end-to-end without needing a real claude
        subprocess — the inner agent's text is the contract."""
        output_dir = self.tmpdir / ".out2"
        answers_md = "### Q-q1\nA fine answer.\n"
        results_json = '[{"id":"q1","pass":true,"reason":"fine"}]'

        # First call = test agent (returns markdown);
        # second call = eval agent (returns JSON).
        call_outputs = iter([
            (answers_md, _make_proc(returncode=0)),
            (results_json, _make_proc(returncode=0)),
        ])
        with mock.patch.object(
            self.runner, "_run_agent",
            side_effect=lambda *a, **kw: next(call_outputs),
        ), mock.patch.object(
            self.runner, "_find_claude", return_value="/fake/claude",
        ), mock.patch.dict(os.environ, {"FORCE_CQ": "1"}):
            results, returned_dir = self.runner.run_test(
                self.spec_path, output_dir=output_dir
            )

        self.assertEqual(returned_dir, output_dir)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["pass"])
        ans = output_dir / "answers.md"
        res = output_dir / "results.json"
        self.assertTrue(ans.exists(), msg="answers.md must be written by Python")
        self.assertTrue(res.exists(), msg="results.json must be written by Python")
        # results.json should be valid JSON (round-trip-able)
        parsed = json.loads(res.read_text(encoding="utf-8"))
        self.assertEqual(parsed[0]["id"], "q1")


class TestRunAgentUsesJsonOutputFormat(unittest.TestCase):
    """The runner's `_run_agent` MUST invoke `claude` with
    `--output-format json` and parse the assistant text from the
    `result` field. A future refactor back to `--output-format text`
    + a Write-tool prompt step reintroduces #9574."""

    def setUp(self):
        self.runner = _load_runner()

    def test_run_agent_passes_json_output_format(self):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return _make_proc(
                stdout='{"is_error":false,"result":"hello"}',
                returncode=0,
            )

        with mock.patch.object(self.runner.subprocess, "run",
                               side_effect=fake_run):
            text, _proc = self.runner._run_agent(
                "/fake/claude", "prompt", REPO_ROOT,
            )
        self.assertEqual(text, "hello")
        self.assertIn("--output-format", captured["cmd"])
        idx = captured["cmd"].index("--output-format")
        self.assertEqual(
            captured["cmd"][idx + 1], "json",
            msg=(
                "_run_agent must request JSON output so the runner "
                "can harvest the assistant text via the `result` "
                "field — text output + Write-tool persistence was "
                "the #9574 failure mode."
            ),
        )

    def test_output_format_precedes_allowed_tools(self):
        """`--allowedTools <tools...>` is variadic and greedily eats
        subsequent positional values up to the next flag. If
        `--output-format json` lands AFTER it, `json` gets absorbed
        as a tool name, claude falls back to text output, and the
        runner's JSON parse fails with no useful diagnostics
        (this took an hour of #9574 to track down). Pin the order."""
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return _make_proc(
                stdout='{"is_error":false,"result":"ok"}',
                returncode=0,
            )

        with mock.patch.object(self.runner.subprocess, "run",
                               side_effect=fake_run):
            self.runner._run_agent(
                "/fake/claude", "prompt", REPO_ROOT, allowed_tools="Read",
            )

        cmd = captured["cmd"]
        self.assertIn("--output-format", cmd)
        self.assertIn("--allowedTools", cmd)
        self.assertLess(
            cmd.index("--output-format"), cmd.index("--allowedTools"),
            msg=(
                "--output-format MUST come before --allowedTools — "
                "the latter is variadic in the claude CLI and "
                "absorbs any subsequent positional arg as a tool "
                "name, including the literal string 'json'."
            ),
        )

    def test_allowed_tools_omitted_when_empty(self):
        """Passing `--allowedTools ""` is unsafe — argparse-style
        variadic flags can interpret the empty string as the start
        of an arg list and greedily consume what follows. The eval
        stage uses no tools at all; the flag must be omitted, not
        passed with an empty value."""
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return _make_proc(
                stdout='{"is_error":false,"result":"ok"}',
                returncode=0,
            )

        with mock.patch.object(self.runner.subprocess, "run",
                               side_effect=fake_run):
            self.runner._run_agent(
                "/fake/claude", "prompt", REPO_ROOT, allowed_tools="",
            )
        self.assertNotIn(
            "--allowedTools", captured["cmd"],
            msg=(
                "When the caller asks for no tools, --allowedTools "
                "must be omitted entirely — passing it with an "
                "empty value risks variadic absorption of the next "
                "argument (#9574)."
            ),
        )

    def test_run_agent_returns_empty_on_is_error(self):
        """When the JSON envelope reports is_error=True, the runner
        treats it as no usable output (caller surfaces the failure)."""
        def fake_run(cmd, **kwargs):
            return _make_proc(
                stdout='{"is_error":true,"result":"partial output"}',
                returncode=0,
            )
        with mock.patch.object(self.runner.subprocess, "run",
                               side_effect=fake_run):
            text, _proc = self.runner._run_agent(
                "/fake/claude", "prompt", REPO_ROOT,
            )
        self.assertEqual(text, "")

    def test_run_agent_returns_empty_on_malformed_json(self):
        """A subprocess that prints non-JSON to stdout (CLI broken,
        binary mismatch, etc.) must be surfaced as empty text rather
        than crashing the runner with a JSONDecodeError."""
        def fake_run(cmd, **kwargs):
            return _make_proc(stdout="not json at all", returncode=0)
        with mock.patch.object(self.runner.subprocess, "run",
                               side_effect=fake_run):
            text, _proc = self.runner._run_agent(
                "/fake/claude", "prompt", REPO_ROOT,
            )
        self.assertEqual(text, "")


class TestPromptDoesNotAskForWriteTool(unittest.TestCase):
    """Prompts must NOT instruct the inner agent to invoke the Write
    tool — the runner does the file write from Python under #9574.
    A regression here ("3. Use the Write tool to ...") reintroduces
    the headless-permission failure mode this fix removed.
    """

    def setUp(self):
        self.source = RUNNER_PATH.read_text(encoding="utf-8")

    def test_runner_source_does_not_instruct_write_tool(self):
        # Grep for the assignment of test_prompt / eval_prompt bodies
        # and assert neither contains "Write tool" in an instructional
        # imperative. We allow Write to be mentioned in comments or
        # function docstrings (which discuss the bug history) — only
        # the prompt bodies are off-limits.
        for varname in ("test_prompt", "eval_prompt"):
            m = re.search(
                rf'\b{varname}\s*=\s*f?"""(.*?)"""',
                self.source,
                re.DOTALL,
            )
            self.assertIsNotNone(
                m,
                msg=f"prompt assignment `{varname}` not found — if it "
                    f"was renamed, update this test.",
            )
            body = m.group(1).lower()
            # Look for any Write-tool imperative phrasing.
            forbidden = [
                "invoke the write tool",
                "use the write tool",
                "call the write tool",
                "your final action must be the write",
            ]
            offending = [p for p in forbidden if p in body]
            self.assertEqual(
                offending, [],
                msg=(
                    f"{varname} body must not instruct the inner agent "
                    f"to invoke the Write tool — #9574 moved file "
                    f"persistence to the Python side via "
                    f"--output-format json. Re-introducing a Write "
                    f"imperative resurrects the headless-permission "
                    f"failure mode. Forbidden phrases found: {offending}"
                ),
            )


if __name__ == "__main__":
    unittest.main()

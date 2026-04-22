#!/usr/bin/env python3
"""Comprehension test pipeline — spawn test + eval agents via claude CLI.

Usage:
    python references/scripts/run_comprehension_test.py <spec.json> [--output-dir <dir>]

The spec JSON defines:
    - files: list of file paths the test agent can read
    - questions: array of {id, question, expected} objects

Pipeline:
    1. Spawn test agent: reads listed files, answers questions, writes answers.md
    2. Spawn eval agent: reads answers.md + spec, evaluates, writes results.json
    3. Exit 0 if all pass, exit 1 if any fail
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent


def _find_claude():
    """Find the claude CLI executable."""
    claude = shutil.which("claude")
    if claude:
        return claude
    # Windows fallback paths
    for candidate in [
        Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd",
        Path(os.environ.get("APPDATA", "")) / "npm" / "claude",
    ]:
        if candidate.exists():
            return str(candidate)
    return None


def _run_agent(claude_bin, prompt, workdir, allowed_tools="Read,Write"):
    """Run a claude agent with the given prompt and tools."""
    cmd = [
        claude_bin, "-p", prompt,
        "--allowedTools", allowed_tools,
        "--output-format", "text",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(workdir),
        timeout=300,
    )
    return result


def run_test(spec_path, output_dir=None):
    """Run the comprehension test pipeline.

    Args:
        spec_path: Path to the spec JSON file.
        output_dir: Directory for answers.md and results.json. Defaults to
                    a temp directory next to the spec file.

    Returns:
        (results, output_dir) where results is a list of {id, pass, reason} dicts.
    """
    spec_path = Path(spec_path).resolve()
    if not spec_path.exists():
        print(f"ERROR: spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    files = spec.get("files", [])
    questions = spec.get("questions", [])

    if not questions:
        print("ERROR: spec has no questions", file=sys.stderr)
        sys.exit(1)

    claude_bin = _find_claude()
    if not claude_bin:
        print("ERROR: claude CLI not found in PATH", file=sys.stderr)
        sys.exit(1)

    if output_dir is None:
        output_dir = spec_path.parent / f".comprehension-{spec_path.stem}"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    answers_path = output_dir / "answers.md"
    results_path = output_dir / "results.json"

    # --- Stage 1: Test agent ---
    file_list = "\n".join(f"- {f}" for f in files)
    question_list = "\n".join(
        f"### Q-{q['id']}\n{q['question']}" for q in questions
    )

    test_prompt = f"""You are a comprehension test agent. Read ONLY the files listed below and answer each question based solely on what you find in those files. Do not use prior knowledge.

## Files to read
{file_list}

## Questions
{question_list}

## Instructions
1. Read each file listed above using the Read tool.
2. For each question, write your answer under the matching heading.
3. Write ALL answers to: {answers_path}

Use this exact format in answers.md:
```
### Q-<id>
<your answer, quoting relevant file content>
```

Answer every question. If you cannot find the answer in the listed files, say "NOT FOUND IN FILES".
"""

    print("Stage 1: Spawning test agent...")
    test_result = _run_agent(claude_bin, test_prompt, REPO_ROOT)
    if test_result.returncode != 0:
        print(f"WARNING: test agent exited with code {test_result.returncode}", file=sys.stderr)
        if test_result.stderr:
            print(f"  stderr: {test_result.stderr[:500]}", file=sys.stderr)

    if not answers_path.exists():
        print(f"ERROR: test agent did not write {answers_path}", file=sys.stderr)
        # Write a fallback so eval agent can still run
        answers_path.write_text("# No answers generated\n", encoding="utf-8")

    # --- Stage 2: Eval agent ---
    expected_list = "\n".join(
        f"### Q-{q['id']}\n**Expected behavior**: {q['expected']}" for q in questions
    )

    eval_prompt = f"""You are an evaluation agent. Compare the test agent's answers against expected behaviors and write structured results.

## Answers file
Read: {answers_path}

## Expected behaviors
{expected_list}

## Instructions
1. Read the answers file using the Read tool.
2. For each question, compare the answer against the expected behavior.
3. A question PASSES if the answer demonstrates correct understanding of the expected behavior. Minor wording differences are OK — judge behavioral correctness, not exact phrasing.
4. A question FAILS if the answer contradicts the expected behavior, is missing, or says "NOT FOUND IN FILES".
5. Write results as a JSON array to: {results_path}

Use this exact JSON format (no markdown fences, just raw JSON):
[
  {{"id": "<question-id>", "pass": true/false, "reason": "<brief explanation>"}}
]

Write ONLY the JSON array to the results file. No other text.
"""

    print("Stage 2: Spawning eval agent...")
    eval_result = _run_agent(claude_bin, eval_prompt, REPO_ROOT)
    if eval_result.returncode != 0:
        print(f"WARNING: eval agent exited with code {eval_result.returncode}", file=sys.stderr)

    if not results_path.exists():
        print(f"ERROR: eval agent did not write {results_path}", file=sys.stderr)
        sys.exit(1)

    # Parse results
    raw = results_path.read_text(encoding="utf-8").strip()
    # Strip markdown fences if eval agent wrapped them
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(l for l in lines if not l.startswith("```"))

    try:
        results = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: failed to parse results.json: {e}", file=sys.stderr)
        print(f"  Content: {raw[:500]}", file=sys.stderr)
        sys.exit(1)

    # Summary
    passed = sum(1 for r in results if r.get("pass"))
    total = len(results)
    print(f"\nResults: {passed}/{total} passed")
    for r in results:
        status = "PASS" if r.get("pass") else "FAIL"
        print(f"  Q-{r['id']}: {status} — {r.get('reason', '')}")

    return results, output_dir


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)

    spec_path = args[0]
    output_dir = None
    if "--output-dir" in args:
        idx = args.index("--output-dir")
        if idx + 1 < len(args):
            output_dir = args[idx + 1]

    results, out_dir = run_test(spec_path, output_dir)

    # Exit code based on results
    all_pass = all(r.get("pass") for r in results)
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()

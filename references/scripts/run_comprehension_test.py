#!/usr/bin/env python3
"""Comprehension test pipeline — spawn test + eval agents via claude CLI.

Usage:
    python references/scripts/run_comprehension_test.py <spec.json> [--output-dir <dir>] [--force]

The spec JSON defines:
    - files: list of file paths the test agent can read
    - questions: array of {id, question, expected} objects

Pipeline:
    1. Check content-hash cache — skip if spec + files unchanged since last PASS
    2. Spawn test agent: reads listed files, answers questions, writes answers.md
    3. Spawn eval agent: reads answers.md + spec, evaluates, writes results.json
    4. Exit 0 if all pass (update cache), exit 1 if any fail (cache unchanged)

Cache bypass: --force flag or FORCE_CQ=1 env var
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CACHE_DIR = REPO_ROOT / "tests" / "comprehension" / ".cache"


# ---------------------------------------------------------------------------
# Content-hash caching
# ---------------------------------------------------------------------------

def _compute_hash(spec_path, files):
    """Compute SHA256 over spec file + all listed files. Returns hex digest."""
    h = hashlib.sha256()
    # Hash the spec file itself (question changes trigger re-run)
    try:
        h.update(Path(spec_path).read_bytes())
    except OSError:
        return None
    # Hash each listed file
    for f in files:
        fpath = Path(f)
        if not fpath.is_absolute():
            fpath = REPO_ROOT / f
        try:
            h.update(fpath.read_bytes())
        except OSError:
            # File missing — force re-run
            return None
    return h.hexdigest()


def _cache_path(spec_path):
    """Return the cache file path for a given spec."""
    return CACHE_DIR / f"{Path(spec_path).stem}.hash"


def _check_cache(spec_path, files):
    """Return True if cache hit (files unchanged since last PASS)."""
    cp = _cache_path(spec_path)
    if not cp.exists():
        return False
    current = _compute_hash(spec_path, files)
    if current is None:
        return False
    try:
        cached = cp.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return current == cached


def _write_cache(spec_path, files):
    """Write cache file after a PASS. Atomic write-then-rename."""
    digest = _compute_hash(spec_path, files)
    if digest is None:
        return
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _cache_path(spec_path).with_suffix(".tmp")
    tmp.write_text(digest, encoding="utf-8")
    tmp.replace(_cache_path(spec_path))


def _find_claude():
    """Find the claude CLI executable.

    Prefers ``claude.exe`` over ``claude.cmd`` on Windows. The .cmd
    batch wrapper is just `"claude.exe" %*`, but `%*` mangles
    multi-line arguments — newlines in the prompt get collapsed and
    the inner agent ends up seeing a malformed prompt with the file
    list and questions truncated away. The inner agent then narrates
    "your message doesn't include the list of files to read" and
    exits cleanly with a non-JSON response, which the runner can't
    parse (#9574). Calling the .exe directly bypasses cmd.exe arg
    parsing entirely and CreateProcessW preserves the literal prompt.
    """
    # Try the npm-installed .exe first (Windows): skip the .cmd wrapper.
    if sys.platform == "win32":
        npm_exe = (
            Path(os.environ.get("APPDATA", "")) / "npm" / "node_modules"
            / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
        )
        if npm_exe.exists():
            return str(npm_exe)

    claude = shutil.which("claude")
    if claude:
        # Final defence: if PATH resolution returned the .cmd, try to
        # find a .exe alongside it.
        if claude.lower().endswith(".cmd"):
            sibling_exe = Path(claude).with_suffix(".exe")
            if sibling_exe.exists():
                return str(sibling_exe)
        return claude
    # Last-resort fallback for non-standard installs (custom npm
    # prefix, scoop/winget/choco, etc.) where neither the win32
    # hardcoded path above nor shutil.which resolved anything. Prefer
    # .exe siblings if present — returning a raw .cmd here
    # resurrects the original #9574 multi-line-prompt bug.
    for candidate in [
        Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd",
        Path(os.environ.get("APPDATA", "")) / "npm" / "claude",
    ]:
        if candidate.exists():
            if candidate.suffix.lower() == ".cmd":
                exe_alt = candidate.with_suffix(".exe")
                if exe_alt.exists():
                    return str(exe_alt)
            return str(candidate)
    return None


def _strip_outer_fences(text):
    """Strip a single layer of ```...``` fences if present.

    The agent is instructed not to use fences, but occasionally wraps
    its output in ```markdown or ```json anyway. We tolerate exactly
    one outer layer; deeper escaping is the agent's bug to fix.
    """
    s = text.strip()
    if not s.startswith("```"):
        return text
    nl = s.find("\n")
    if nl < 0:
        return text
    body = s[nl + 1:]
    if body.rstrip().endswith("```"):
        body = body.rstrip()
        body = body[: body.rfind("```")].rstrip()
    return body


def _run_agent(claude_bin, prompt, workdir, allowed_tools="Read"):
    """Run a claude agent with ``--output-format json`` and return its
    final assistant text plus the raw CompletedProcess.

    Returns ``(result_text, completed_process)``. ``result_text`` is
    the empty string if the agent reported an error or the JSON could
    not be parsed; the caller is expected to surface that as a runner
    failure.

    #9574 design notes: the prior implementation used
    ``--output-format text`` and asked the inner agent to invoke the
    ``Write`` tool to persist answers/results to disk. That path was
    unreliable in headless ``claude -p`` on Windows — the inner agent
    reliably narrated a permission-grant requirement (which has no
    interactive prompt to satisfy in subprocess mode) and exited
    rc=0 with no file written. ``--output-format json`` is the
    documented contract for headless callers: the ``result`` field
    contains the assistant's final message and is the path the SDK
    itself uses. We collect that text and let the runner do the
    on-disk write from Python, eliminating the Write-tool dependency
    entirely. Tool budget is now read-only (default ``Read``) —
    callers needing more should pass ``allowed_tools`` explicitly.
    """
    # Flag order matters: `--allowedTools <tools...>` is variadic
    # and greedily consumes subsequent positional values until the
    # next flag. Putting `--output-format json` AFTER it caused
    # `json` to be absorbed as a tool name, claude fell back to its
    # default text output, the runner's JSON parse failed, and we
    # got the dread "your message doesn't include the list of
    # files" hallucination from a half-running agent (#9574 first
    # JSON-pivot attempt). Keep `--output-format` before
    # `--allowedTools`, and omit `--allowedTools` entirely when no
    # tools are needed (empty-string value would tickle the same
    # variadic-consumption hazard).
    cmd = [
        claude_bin, "-p", prompt,
        "--output-format", "json",
    ]
    if allowed_tools:
        cmd.extend(["--allowedTools", allowed_tools])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(workdir),
        timeout=300,
    )
    if proc.returncode != 0:
        return "", proc
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "", proc
    if data.get("is_error"):
        return "", proc
    return str(data.get("result") or ""), proc


def run_test(spec_path, output_dir=None, force=False):
    """Run the comprehension test pipeline.

    Args:
        spec_path: Path to the spec JSON file.
        output_dir: Directory for answers.md and results.json. Defaults to
                    a temp directory next to the spec file.
        force: If True, bypass the content-hash cache.

    Returns:
        (results, output_dir) where results is a list of {id, pass, reason} dicts,
        or (None, None) if skipped due to cache hit.
    """
    spec_path = Path(spec_path).resolve()
    if not spec_path.exists():
        print(f"ERROR: spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    files = spec.get("files", [])
    questions = spec.get("questions", [])

    # Content-hash cache check
    force = force or os.environ.get("FORCE_CQ") == "1"
    if not force and _check_cache(spec_path, files):
        print(f"Skipped — files unchanged since last PASS ({spec_path.name})")
        return None, None

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

    # #9574: prompt asks the inner agent to OUTPUT answers in chat
    # (assistant final message), not to invoke the Write tool. The
    # runner harvests the assistant text from --output-format json's
    # `result` field and writes the file from Python. Rationale: the
    # Write-tool path was unreliable in headless `claude -p` (silent
    # permission-pending exits, hallucinated denial narratives) and
    # added a layer that didn't earn its keep — the agent's *answers*
    # were always going to come through the assistant text anyway.
    test_prompt = f"""You are a comprehension test agent. Read ONLY the files listed below and answer each question based solely on what you find in them. Do not use prior knowledge.

## Files to read (use the Read tool on each)
{file_list}

## Questions
{question_list}

## Required output (your final assistant message — nothing else)
Respond with a single markdown body, no preamble, no closing remarks, no code fences. Exactly one block per question, in this format:

### Q-<id>
<your answer, quoting relevant file content>

If you cannot find a question's answer in the listed files, write `NOT FOUND IN FILES` under that heading.

## Procedure
1. Read every file listed under "Files to read" using the Read tool.
2. Compose your final assistant message as the markdown body described above. Your entire reply must be the answers — the runner harvests this text verbatim and writes it to disk.
"""

    print("Stage 1: Spawning test agent...")
    try:
        answers_text, test_proc = _run_agent(
            claude_bin, test_prompt, REPO_ROOT, allowed_tools="Read",
        )
    except subprocess.TimeoutExpired:
        print("ERROR: test agent timed out after 300s", file=sys.stderr)
        sys.exit(1)
    if test_proc.returncode != 0:
        print(f"WARNING: test agent exited with code {test_proc.returncode}",
              file=sys.stderr)
        if test_proc.stderr:
            print(f"  stderr: {test_proc.stderr[:500]}", file=sys.stderr)

    if not answers_text.strip():
        # #9574: surface this loudly rather than papering over with a
        # placeholder file. Callers (CI, skill verification) must see
        # the regression if it reappears.
        print(
            f"ERROR: test agent returned empty content "
            f"(rc={test_proc.returncode}) — runner exiting 1.",
            file=sys.stderr,
        )
        print(
            f"  raw stdout (first 500 chars): {test_proc.stdout[:500]!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Strip markdown fences if the agent wrapped its reply despite the
    # instruction. Cheap defence; fences are the only common deviation.
    answers_text = _strip_outer_fences(answers_text)
    answers_path.write_text(answers_text, encoding="utf-8")

    # --- Stage 2: Eval agent ---
    expected_list = "\n".join(
        f"### Q-{q['id']}\n**Expected behavior**: {q['expected']}" for q in questions
    )

    # #9574: answers are embedded directly in the eval prompt so the
    # eval agent needs no tools at all — pure text-in, text-out.
    eval_prompt = f"""You are an evaluation agent. Compare the test agent's answers (provided in full below) against the expected behaviors and respond with a raw JSON array. No tool calls are necessary.

## Answers (verbatim from the test agent)
{answers_text}

## Expected behaviors (one per question)
{expected_list}

## Evaluation rules
- PASS = the answer demonstrates correct understanding of the expected behavior. Minor wording differences are OK — judge behavioral correctness, not exact phrasing.
- FAIL = the answer contradicts the expected behavior, is missing, or says `NOT FOUND IN FILES`.

## Required output (your final assistant message — nothing else)
Respond with a raw JSON array. No code fences, no preamble, no closing remarks. One object per question id in this shape:

[
  {{"id": "<question-id>", "pass": true, "reason": "<brief explanation>"}},
  {{"id": "<question-id>", "pass": false, "reason": "<brief explanation>"}}
]

The runner parses your reply directly as JSON.
"""

    print("Stage 2: Spawning eval agent...")
    try:
        results_text, eval_proc = _run_agent(
            claude_bin, eval_prompt, REPO_ROOT, allowed_tools="",
        )
    except subprocess.TimeoutExpired:
        print("ERROR: eval agent timed out after 300s", file=sys.stderr)
        sys.exit(1)
    if eval_proc.returncode != 0:
        print(f"WARNING: eval agent exited with code {eval_proc.returncode}",
              file=sys.stderr)

    if not results_text.strip():
        print(
            f"ERROR: eval agent returned empty content "
            f"(rc={eval_proc.returncode}) — runner exiting 1.",
            file=sys.stderr,
        )
        print(
            f"  raw stdout (first 500 chars): {eval_proc.stdout[:500]!r}",
            file=sys.stderr,
        )
        sys.exit(1)

    raw = _strip_outer_fences(results_text).strip()

    try:
        results = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: failed to parse results JSON: {e}", file=sys.stderr)
        print(f"  Content: {raw[:500]}", file=sys.stderr)
        sys.exit(1)

    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    if not results:
        print("ERROR: eval agent produced empty results — treating as failure",
              file=sys.stderr)
        return [], output_dir

    # Summary
    passed = sum(1 for r in results if r.get("pass"))
    total = len(results)
    all_pass = all(r.get("pass") for r in results)
    print(f"\nResults: {passed}/{total} passed")
    for r in results:
        status = "PASS" if r.get("pass") else "FAIL"
        print(f"  Q-{r['id']}: {status} — {r.get('reason', '')}")

    # Write cache only on PASS — failed runs must not update cache
    if all_pass:
        _write_cache(spec_path, files)

    return results, output_dir


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)

    spec_path = args[0]
    output_dir = None
    force = "--force" in args

    if "--output-dir" in args:
        idx = args.index("--output-dir")
        if idx + 1 < len(args):
            output_dir = args[idx + 1]

    results, out_dir = run_test(spec_path, output_dir, force=force)

    # Cache hit — skipped, exit 0
    if results is None:
        sys.exit(0)

    # Exit code based on results — empty results = failure
    all_pass = results and all(r.get("pass") for r in results)
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()

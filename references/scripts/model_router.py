#!/usr/bin/env python3
"""SquidSquad model router — route subagent work to external models via API.

Provides a universal subagent runner with read-only tool access (Read, Grep,
Glob) and per-task prompt templates. Uses PID-based liveness, not .health.

Usage:
    python scripts/model_router.py <task-type> \\
      --task-id <ID> \\
      --input-files <comma-separated paths> \\
      --output-file <path> \\
      --context <additional context string>

    python scripts/model_router.py --help

Task types: research, discussion-prep, test-plan, improvement-scan,
            qa-execution, comprehension

Exit codes:
    0 — success (output file written)
    1 — API failure or claude-only task (parent should fall back to Agent tool)
    2 — configuration error (missing API key, invalid config)
"""

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_PATH = REPO_ROOT / ".squidsquad" / "config.md"
PROMPTS_DIR = SCRIPT_DIR.parent / "prompts"
PROVIDERS_DIR = SCRIPT_DIR / "providers"
DIAGNOSTICS_DIR = REPO_ROOT / ".squidsquad" / "diagnostics"

# Tasks that are always Claude-only regardless of config
CLAUDE_LOCKED_TASKS = {"comprehension", "qa-execution"}

# Sensitive files that must never be read by external models
SENSITIVE_PATTERNS = [
    ".env", ".env.*", "*.key", "*.pem", "*.p12", "*.pfx",
    ".git/config", "*.secret", "credentials.*",
]

# Maximum file size for Read tool (bytes) — truncate beyond this
MAX_FILE_READ_BYTES = 500_000  # ~500KB

# Minimum acceptable output length (chars) — below this triggers fallback
MIN_OUTPUT_LENGTH = 200


# ---------------------------------------------------------------------------
# Config parsing
# ---------------------------------------------------------------------------

def _read_config():
    """Read config.md, return text. Returns None if missing."""
    if not CONFIG_PATH.exists():
        return None
    return CONFIG_PATH.read_text(encoding="utf-8")


def _parse_model_routing(text):
    """Parse ## Model Routing section from config.md."""
    if text is None:
        return {}
    result = {}
    in_section = False
    for line in text.splitlines():
        if re.match(r"^##\s+Model Routing", line):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+", line):
            break
        if in_section:
            m = re.match(r"-\s*\*\*(.+?)\*\*:\s*(.+)", line)
            if m:
                key = m.group(1).strip().lower().replace(" ", "-")
                result[key] = m.group(2).strip()
    return result


def get_model_for_task(task_type):
    """Determine which model to use for a task type.

    Returns model name string (e.g. 'gpt-5.2', 'claude').
    Claude-locked tasks always return 'claude'.
    """
    if task_type in CLAUDE_LOCKED_TASKS:
        return "claude"

    config_text = _read_config()
    routing = _parse_model_routing(config_text)

    # Map task type to config key
    key_map = {
        "research": "research-model",
        "discussion-prep": "discussion-prep-model",
        "test-plan": "test-plan-model",
        "improvement-scan": "improvement-scan-model",
        "qa-execution": "qa-execution-model",
        "comprehension": "comprehension-model",
    }

    key = key_map.get(task_type, f"{task_type}-model")
    model = routing.get(key, routing.get("default-model", "claude"))

    return model


def get_timeout():
    """Read API timeout from config. Default 120s."""
    config_text = _read_config()
    routing = _parse_model_routing(config_text)
    try:
        return int(routing.get("api-timeout-seconds", "120"))
    except ValueError:
        return 120


# ---------------------------------------------------------------------------
# Provider loading
# ---------------------------------------------------------------------------

def _load_provider_manifest(model):
    """Find and load the provider manifest for a model name.

    Searches providers/ directories for manifests that list the model.
    Returns (provider_name, manifest_dict) or (None, None).
    """
    if not PROVIDERS_DIR.exists():
        return None, None

    # Try importing yaml
    try:
        import yaml
    except ImportError:
        # PyYAML not available, try installing
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyyaml"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import yaml

    for provider_dir in PROVIDERS_DIR.iterdir():
        if not provider_dir.is_dir():
            continue
        manifest_path = provider_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue
        try:
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            if model in manifest.get("models", {}):
                return manifest["name"], manifest
            if model == manifest.get("default_model"):
                return manifest["name"], manifest
        except Exception:
            continue

    return None, None


def _ensure_deps(manifest):
    """Auto-install pip dependencies from provider manifest."""
    deps = manifest.get("deps", [])
    for dep in deps:
        pkg_name = re.split(r"[><=!]", dep)[0].strip()
        try:
            __import__(pkg_name)
        except ImportError:
            print(f"[model_router] Installing {dep}...", file=sys.stderr)
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", dep],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


# ---------------------------------------------------------------------------
# Security — 4-layer enforcement
# ---------------------------------------------------------------------------

def _is_path_in_sandbox(path_str):
    """Layer 2: Check if a path is within the repo root."""
    try:
        resolved = Path(path_str).resolve()
        repo_resolved = REPO_ROOT.resolve()
        return str(resolved).startswith(str(repo_resolved))
    except Exception:
        return False


def _is_sensitive_file(path_str):
    """Layer 4: Check if a path matches the sensitive file deny-list."""
    name = Path(path_str).name
    rel = str(Path(path_str))
    for pattern in SENSITIVE_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(rel, pattern):
            return True
    # Check for .git/ subdirectory access
    try:
        resolved = Path(path_str).resolve()
        git_dir = (REPO_ROOT / ".git").resolve()
        if str(resolved).startswith(str(git_dir)):
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Tool implementations (Python-native, sandboxed)
# ---------------------------------------------------------------------------

def _tool_read(args):
    """Read a file. Returns file content or error string."""
    file_path = args.get("file_path", "")

    # Resolve relative to repo root
    if not os.path.isabs(file_path):
        file_path = str(REPO_ROOT / file_path)

    if not _is_path_in_sandbox(file_path):
        return "ERROR: Path outside repository boundary."

    if _is_sensitive_file(file_path):
        return "ERROR: Access to sensitive file denied."

    try:
        p = Path(file_path)
        if not p.exists():
            return f"ERROR: File not found: {file_path}"
        if not p.is_file():
            return f"ERROR: Not a file: {file_path}"

        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > MAX_FILE_READ_BYTES:
            content = content[:MAX_FILE_READ_BYTES] + \
                f"\n\n[TRUNCATED — file exceeds {MAX_FILE_READ_BYTES} bytes]"

        # Add line numbers
        lines = content.splitlines()
        offset = args.get("offset", 0)
        limit = args.get("limit", len(lines))
        selected = lines[offset:offset + limit]
        numbered = [f"{i + offset + 1}\t{line}" for i, line in enumerate(selected)]
        return "\n".join(numbered)
    except Exception as e:
        return f"ERROR: {e}"


def _tool_grep(args):
    """Search for a pattern in files. Returns matching file paths or content."""
    pattern = args.get("pattern", "")
    path = args.get("path", str(REPO_ROOT))
    glob_filter = args.get("glob", None)
    output_mode = args.get("output_mode", "files_with_matches")

    if not os.path.isabs(path):
        path = str(REPO_ROOT / path)

    if not _is_path_in_sandbox(path):
        return "ERROR: Path outside repository boundary."

    try:
        cmd = ["rg", "--no-heading", pattern, path]
        if glob_filter:
            cmd.extend(["--glob", glob_filter])
        if output_mode == "files_with_matches":
            cmd.append("-l")
        elif output_mode == "count":
            cmd.append("-c")

        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=30
        )
        output = result.stdout.strip()
        if not output:
            return "No matches found."
        # Limit output
        lines = output.splitlines()[:50]
        return "\n".join(lines)
    except FileNotFoundError:
        # rg not available, fall back to Python regex
        return _grep_python(pattern, path, glob_filter, output_mode)
    except subprocess.TimeoutExpired:
        return "ERROR: Search timed out."
    except Exception as e:
        return f"ERROR: {e}"


def _grep_python(pattern, path, glob_filter, output_mode):
    """Fallback grep using Python regex."""
    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"ERROR: Invalid regex: {e}"

    matches = []
    root = Path(path)
    if root.is_file():
        files = [root]
    else:
        files = sorted(root.rglob("*"))

    for f in files:
        if not f.is_file():
            continue
        if glob_filter and not fnmatch.fnmatch(f.name, glob_filter):
            continue
        if _is_sensitive_file(str(f)):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            if regex.search(content):
                if output_mode == "files_with_matches":
                    matches.append(str(f))
                elif output_mode == "count":
                    count = len(regex.findall(content))
                    matches.append(f"{f}:{count}")
                else:
                    for i, line in enumerate(content.splitlines(), 1):
                        if regex.search(line):
                            matches.append(f"{f}:{i}:{line}")
        except Exception:
            continue
        if len(matches) >= 50:
            break

    return "\n".join(matches) if matches else "No matches found."


def _tool_glob(args):
    """Find files matching a glob pattern."""
    pattern = args.get("pattern", "")
    path = args.get("path", str(REPO_ROOT))

    if not os.path.isabs(path):
        path = str(REPO_ROOT / path)

    if not _is_path_in_sandbox(path):
        return "ERROR: Path outside repository boundary."

    try:
        root = Path(path)
        matches = sorted(root.glob(pattern))
        results = []
        for m in matches[:100]:
            if m.is_file() and not _is_sensitive_file(str(m)):
                results.append(str(m.relative_to(REPO_ROOT)))
        return "\n".join(results) if results else "No matches found."
    except Exception as e:
        return f"ERROR: {e}"


# Layer 1: Tool whitelist
TOOL_REGISTRY = {
    "read": _tool_read,
    "grep": _tool_grep,
    "glob": _tool_glob,
}


def _handle_tool_call(name, args):
    """Layer 1: Only whitelisted tools are callable. Layer 3: No shell access."""
    handler = TOOL_REGISTRY.get(name)
    if handler is None:
        return f"ERROR: Tool '{name}' is not available. Available tools: {', '.join(TOOL_REGISTRY.keys())}"
    return handler(args)


# ---------------------------------------------------------------------------
# OpenAI function-calling tool definitions
# ---------------------------------------------------------------------------

OPENAI_TOOL_DEFS = [
    {
        "type": "function",
        "function": {
            "name": "read",
            "description": "Read a file from the repository. Returns file content with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative to repo root or absolute)",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Line number to start reading from (0-based). Default: 0",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of lines to read. Default: all",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search for a regex pattern in files. Returns matching file paths or content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Regular expression pattern to search for",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search in (default: repo root)",
                    },
                    "glob": {
                        "type": "string",
                        "description": "Glob pattern to filter files (e.g. '*.py', '*.md')",
                    },
                    "output_mode": {
                        "type": "string",
                        "enum": ["content", "files_with_matches", "count"],
                        "description": "Output mode. Default: files_with_matches",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "Find files matching a glob pattern in the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (e.g. '**/*.py', 'src/**/*.ts')",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory to search in (default: repo root)",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Prompt assembly
# ---------------------------------------------------------------------------

def _load_prompt_template(task_type):
    """Load prompt template for a task type."""
    template_map = {
        "research": "research.md.j2",
        "discussion-prep": "discussion-prep.md.j2",
        "test-plan": "test-plan.md.j2",
        "improvement-scan": "improvement-scan.md.j2",
    }
    filename = template_map.get(task_type)
    if not filename:
        return None

    template_path = PROMPTS_DIR / filename
    if not template_path.exists():
        return None

    return template_path.read_text(encoding="utf-8")


def _read_input_files(input_files_str):
    """Read input files and return combined content."""
    if not input_files_str:
        return ""

    parts = []
    for fpath in input_files_str.split(","):
        fpath = fpath.strip()
        if not fpath:
            continue
        full_path = Path(fpath) if os.path.isabs(fpath) else REPO_ROOT / fpath
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            parts.append(f"### File: {fpath}\n\n{content}")
        except Exception as e:
            parts.append(f"### File: {fpath}\n\nERROR reading file: {e}")

    return "\n\n---\n\n".join(parts)


def assemble_prompt(task_type, task_id, input_files, context):
    """Assemble the full prompt from template + input files + context."""
    template = _load_prompt_template(task_type)
    if not template:
        # Fallback: simple prompt
        file_contents = _read_input_files(input_files)
        return (
            f"Task: {context}\n\n"
            f"Input files:\n\n{file_contents}\n\n"
            f"Produce a structured analysis document."
        )

    file_contents = _read_input_files(input_files)

    # Simple template variable substitution (no Jinja2 dependency)
    prompt = template
    prompt = prompt.replace("{{ context }}", context or "")
    prompt = prompt.replace("{{ task_id }}", task_id or "")
    prompt = prompt.replace("{{ file_contents }}", file_contents)

    return prompt


# ---------------------------------------------------------------------------
# Diagnostics logging
# ---------------------------------------------------------------------------

def _log_diagnostic(entry):
    """Append a JSON line to diagnostics log."""
    try:
        DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
        log_path = DIAGNOSTICS_DIR / "model-routing.log"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main routing logic
# ---------------------------------------------------------------------------

def route(task_type, task_id, input_files, output_file, context):
    """Route a subagent task to the configured model.

    Returns 0 on success, 1 on API failure (fallback), 2 on config error.
    """
    model = get_model_for_task(task_type)

    # Claude-only: signal parent to use Agent tool
    if model == "claude":
        _log_diagnostic({
            "timestamp": time.time(),
            "task_type": task_type,
            "task_id": task_id,
            "model": "claude",
            "action": "delegate-to-agent-tool",
        })
        return 1

    # Load provider
    provider_name, manifest = _load_provider_manifest(model)
    if not manifest:
        print(
            f"[model_router] No provider found for model '{model}'. "
            f"Falling back to Claude.",
            file=sys.stderr,
        )
        return 1

    # Check API key
    auth_env = manifest.get("auth", {}).get("env_var", "")
    if auth_env and not os.environ.get(auth_env):
        print(
            f"[model_router] ERROR: {auth_env} environment variable not set. "
            f"Required for {provider_name} provider.",
            file=sys.stderr,
        )
        return 2

    # Auto-install deps
    _ensure_deps(manifest)

    # Assemble prompt
    prompt = assemble_prompt(task_type, task_id, input_files, context)
    system_prompt = (
        "You are a SquidSquad subagent. You have access to read, grep, and glob "
        "tools to explore the repository. Use them to gather information, then "
        "produce your output. Be specific — reference actual file paths and line "
        "numbers. Do not hallucinate files or functions."
    )

    timeout = get_timeout()

    # Call provider adapter
    start_time = time.time()
    try:
        if provider_name == "openai":
            from providers.openai.adapter import call as openai_call
            response = openai_call(
                model=model,
                system_prompt=system_prompt,
                user_prompt=prompt,
                tools=OPENAI_TOOL_DEFS,
                tool_handler=_handle_tool_call,
                timeout=timeout,
            )
        else:
            print(
                f"[model_router] Unknown provider '{provider_name}'. "
                f"Falling back to Claude.",
                file=sys.stderr,
            )
            return 1
    except Exception as e:
        elapsed = time.time() - start_time
        _log_diagnostic({
            "timestamp": time.time(),
            "task_type": task_type,
            "task_id": task_id,
            "model": model,
            "provider": provider_name,
            "action": "api-error",
            "error": str(e),
            "elapsed_seconds": round(elapsed, 1),
        })
        print(f"[model_router] API error: {e}. Falling back to Claude.", file=sys.stderr)
        return 1

    elapsed = time.time() - start_time

    # Quality gate: check minimum output length
    if len(response.strip()) < MIN_OUTPUT_LENGTH:
        _log_diagnostic({
            "timestamp": time.time(),
            "task_type": task_type,
            "task_id": task_id,
            "model": model,
            "provider": provider_name,
            "action": "quality-gate-fail",
            "response_length": len(response),
            "elapsed_seconds": round(elapsed, 1),
        })
        print(
            f"[model_router] Output below minimum length threshold "
            f"({len(response)} < {MIN_OUTPUT_LENGTH}). Falling back to Claude.",
            file=sys.stderr,
        )
        # Clean up partial output
        try:
            Path(output_file).unlink(missing_ok=True)
        except Exception:
            pass
        return 1

    # Write output
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(response, encoding="utf-8")
    except Exception as e:
        print(f"[model_router] Failed to write output: {e}", file=sys.stderr)
        return 1

    _log_diagnostic({
        "timestamp": time.time(),
        "task_type": task_type,
        "task_id": task_id,
        "model": model,
        "provider": provider_name,
        "action": "success",
        "response_length": len(response),
        "elapsed_seconds": round(elapsed, 1),
    })

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SquidSquad model router — route subagent work to external models.",
        epilog=(
            "Exit codes:\n"
            "  0 — success (output file written)\n"
            "  1 — API failure (parent should fall back to Agent tool)\n"
            "  2 — configuration error (missing API key)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "task_type",
        choices=[
            "research", "discussion-prep", "test-plan",
            "improvement-scan", "qa-execution", "comprehension",
        ],
        help="Type of subagent task to route",
    )
    parser.add_argument("--task-id", required=True, help="Task identifier (e.g. FEAT-PM-1291)")
    parser.add_argument("--input-files", default="", help="Comma-separated input file paths")
    parser.add_argument("--output-file", required=True, help="Path for output file")
    parser.add_argument("--context", default="", help="Additional context string")

    args = parser.parse_args()

    code = route(args.task_type, args.task_id, args.input_files, args.output_file, args.context)
    sys.exit(code)


if __name__ == "__main__":
    main()

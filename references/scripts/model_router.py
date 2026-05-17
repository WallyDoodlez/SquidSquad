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
# Resolve diagnostics path via state_bus if available (#3664)
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from state_bus import state_path as _state_path
    DIAGNOSTICS_DIR = _state_path("diagnostics")
except ImportError:
    DIAGNOSTICS_DIR = REPO_ROOT / ".squidsquad" / "diagnostics"

# Tasks that are always Claude-only regardless of config
CLAUDE_LOCKED_TASKS = {"comprehension", "qa-execution"}


def _ensure_yaml():
    """Import yaml, auto-installing PyYAML if missing (#5125).

    Returns the yaml module or None on failure.
    """
    try:
        import yaml
        return yaml
    except ImportError:
        pass
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "pyyaml"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        import yaml
        return yaml
    except (subprocess.CalledProcessError, ImportError) as e:
        print(f"[model_router] ERROR: Could not install PyYAML: {e}",
              file=sys.stderr)
        return None

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

    # Allow override for testing (live integration tests force gpt-5.2)
    override = os.environ.get("SQUIDSQUAD_MODEL_OVERRIDE")
    if override:
        return override

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
        "code-review": "code-review-model",  # #5932
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

    yaml = _ensure_yaml()
    if yaml is None:
        return None, None

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


def list_providers():
    """Discover all available providers by scanning providers/*/manifest.yaml.

    Returns a list of dicts, each with: name, display_name, default_model,
    models (list of model names), auth_env_var.
    """
    if not PROVIDERS_DIR.exists():
        return []

    yaml = _ensure_yaml()
    if yaml is None:
        return []

    providers = []
    for provider_dir in sorted(PROVIDERS_DIR.iterdir()):
        if not provider_dir.is_dir():
            continue
        manifest_path = provider_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue
        try:
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            providers.append({
                "name": manifest.get("name", provider_dir.name),
                "display_name": manifest.get("display_name", provider_dir.name),
                "default_model": manifest.get("default_model", ""),
                "models": list(manifest.get("models", {}).keys()),
                "auth_env_var": manifest.get("auth", {}).get("env_var", ""),
            })
        except Exception:
            continue

    return providers


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
        return resolved.is_relative_to(repo_resolved)
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

        # Check file size before reading to avoid loading oversized files into memory
        file_size = p.stat().st_size
        if file_size > MAX_FILE_READ_BYTES:
            with p.open("r", encoding="utf-8", errors="replace") as f:
                content = f.read(MAX_FILE_READ_BYTES)
            content += f"\n\n[TRUNCATED — file exceeds {MAX_FILE_READ_BYTES} bytes]"
        else:
            content = p.read_text(encoding="utf-8", errors="replace")

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
        "code-review": "code-review.md.j2",  # #5932
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

    Returns 0 on success, 1 on API failure (fallback), 2 on config error, 3 on timeout.
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

    # Check API key — ~/.squidsquad/secrets first, then env var
    auth_env = manifest.get("auth", {}).get("env_var", "")
    if auth_env:
        try:
            from shared_fs import read_secret_or_env
            api_key = read_secret_or_env(auth_env)
        except ImportError:
            api_key = os.environ.get(auth_env)
        if api_key:
            # Make available to provider adapters via env
            os.environ[auth_env] = api_key
    if auth_env and not os.environ.get(auth_env):
        print(
            f"[model_router] {auth_env} not set (checked ~/.squidsquad/secrets and env) — "
            f"skipping {provider_name}, falling back to Claude for {task_type}.",
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

    # Write progress indicator to output file (#5046)
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"# STATUS: generating...\n# Task: {task_id}\n# Model: {model}\n",
            encoding="utf-8",
        )
    except OSError:
        pass

    # Call provider adapter
    start_time = time.time()
    try:
        # Load the provider's adapter module dynamically
        adapter_module = _load_adapter(manifest)
        if adapter_module and hasattr(adapter_module, "call"):
            # Read base_url and auth env var from manifest for OpenAI-compatible providers
            api_base = manifest.get("api_base", "")
            auth_env_var = manifest.get("auth", {}).get("env_var", "OPENAI_API_KEY")
            response = adapter_module.call(
                model=model,
                system_prompt=system_prompt,
                user_prompt=prompt,
                tools=OPENAI_TOOL_DEFS,
                tool_handler=_handle_tool_call,
                timeout=timeout,
                base_url=api_base if api_base else None,
                api_key_env=auth_env_var,
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
        error_str = str(e).lower()
        is_timeout = (
            "timeout" in error_str
            or "timed out" in error_str
            or type(e).__name__ in ("TimeoutError", "ReadTimeout", "ConnectTimeout")
        )
        is_quota = (
            "429" in str(e)
            or "rate_limit" in error_str
            or "rate limit" in error_str
            or "quota" in error_str
            or "insufficient_quota" in error_str
            or "billing" in error_str
            or type(e).__name__ == "RateLimitError"
        )

        action = "timeout" if is_timeout else ("quota-exceeded" if is_quota else "api-error")
        _log_diagnostic({
            "timestamp": time.time(),
            "task_type": task_type,
            "task_id": task_id,
            "model": model,
            "provider": provider_name,
            "action": action,
            "error": str(e),
            "elapsed_seconds": round(elapsed, 1),
        })

        # Write error status to output file (#5046)
        try:
            error_detail = "quota exceeded" if is_quota else str(e)[:200]
            Path(output_file).write_text(
                f"# STATUS: error -- {error_detail}\n",
                encoding="utf-8",
            )
        except OSError:
            pass

        if is_quota:
            # Prominent human-visible notification — not buried in stderr
            print(
                f"\n{'=' * 60}\n"
                f"EXTERNAL MODEL QUOTA EXCEEDED\n"
                f"  Provider: {provider_name} ({model})\n"
                f"  Error: {e}\n"
                f"  Action: Add credits or check your plan.\n"
                f"  Falling back to Claude for this task.\n"
                f"{'=' * 60}\n"
            )
        elif is_timeout:
            print(f"[model_router] API timeout after {round(elapsed, 1)}s. Falling back to Claude.", file=sys.stderr)
            return 3
        else:
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
        # Write error status instead of deleting (#5046)
        try:
            Path(output_file).write_text(
                f"# STATUS: error -- output below minimum length ({len(response)} chars)\n",
                encoding="utf-8",
            )
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
# Provider setup and validation
# ---------------------------------------------------------------------------


def _find_provider_manifest(provider_name):
    """Find a provider manifest by name. Returns (manifest_path, manifest_dict) or (None, None)."""
    if not PROVIDERS_DIR.exists():
        return None, None

    yaml = _ensure_yaml()
    if yaml is None:
        return None, None

    for provider_dir in PROVIDERS_DIR.iterdir():
        if not provider_dir.is_dir():
            continue
        manifest_path = provider_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue
        try:
            manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("name", "").lower() == provider_name.lower():
                return manifest_path, manifest
        except Exception:
            continue
    return None, None


def setup_provider(provider_name):
    """Guide API key setup for a provider. Returns exit code."""
    manifest_path, manifest = _find_provider_manifest(provider_name)
    if not manifest:
        print(f"ERROR: Provider '{provider_name}' not found.", file=sys.stderr)
        print("Available providers:", file=sys.stderr)
        for p in list_providers():
            print(f"  - {p['name']}: {p['display_name']}", file=sys.stderr)
        return 2

    auth = manifest.get("auth", {})
    env_var = auth.get("env_var", "")
    display = manifest.get("display_name", provider_name)
    models = list(manifest.get("models", {}).keys())
    secrets_path = Path.home() / ".squidsquad" / "secrets"

    print(f"\n=== {display} Setup ===\n")
    print(f"Provider: {display}")
    print(f"Available models: {', '.join(models)}")
    print(f"Default model: {manifest.get('default_model', 'N/A')}")

    if env_var:
        print(f"\nAPI Key Configuration:")
        print(f"  Environment variable: {env_var}")
        print(f"  Secrets file: {secrets_path}")
        print(f"\nTo configure, either:")
        print(f"  1. Set env var: export {env_var}=your-api-key-here")
        print(f"  2. Write to secrets: python references/scripts/shared_fs.py write-secret {env_var} your-api-key-here")
        print(f"\nThe secrets file ({secrets_path}) is recommended — it persists across sessions")
        print(f"and is shared by all agents.")

    # Open manifest in editor
    print(f"\nManifest file: {manifest_path}")
    print("Opening manifest in editor...")
    try:
        import platform as plat
        system = plat.system().lower()
        if system == "windows":
            os.startfile(str(manifest_path))
        elif system == "darwin":
            subprocess.Popen(["open", str(manifest_path)])
        else:
            subprocess.Popen(["xdg-open", str(manifest_path)])
    except Exception as e:
        print(f"  Could not open editor: {e}", file=sys.stderr)
        print(f"  Open manually: {manifest_path}")

    print(f"\nAfter setting your API key, validate with:")
    print(f"  python references/scripts/model_router.py validate {provider_name}")

    return 0


def validate_provider(provider_name):
    """Test API key for a provider with a cheap call. Returns exit code."""
    _, manifest = _find_provider_manifest(provider_name)
    if not manifest:
        print(f"ERROR: Provider '{provider_name}' not found.", file=sys.stderr)
        return 2

    auth = manifest.get("auth", {})
    env_var = auth.get("env_var", "")
    display = manifest.get("display_name", provider_name)

    if not env_var:
        print(f"{display}: No API key required.")
        return 0

    # Check for API key
    try:
        from shared_fs import read_secret_or_env
        api_key = read_secret_or_env(env_var)
    except ImportError:
        api_key = os.environ.get(env_var)

    if not api_key:
        print(
            f"FAIL: {env_var} not set. "
            f"Set it via env var or ~/.squidsquad/secrets.",
            file=sys.stderr,
        )
        return 1

    # Try loading the provider adapter and making a cheap test call
    default_model = manifest.get("default_model", "")
    if not default_model:
        models = list(manifest.get("models", {}).keys())
        default_model = models[0] if models else ""

    print(f"Validating {display} (model: {default_model})...")
    os.environ[env_var] = api_key

    try:
        adapter_module = _load_adapter(manifest)
        if adapter_module and hasattr(adapter_module, "validate"):
            ok, msg = adapter_module.validate(api_key, default_model)
            if ok:
                print(f"OK: {msg}")
                return 0
            else:
                print(f"FAIL: {msg}", file=sys.stderr)
                return 1

        # Fallback: try a minimal API call via the adapter's run function
        print(f"OK: API key is set ({len(api_key)} chars). "
              f"No validation endpoint available — key format looks valid.")
        return 0
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1


def _load_adapter(manifest):
    """Load the provider adapter module. Returns module or None."""
    provider_name = manifest.get("name", "")
    adapter_path = PROVIDERS_DIR / provider_name / "adapter.py"
    if not adapter_path.exists():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        f"provider_{provider_name}", str(adapter_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SquidSquad model router — route subagent work to external models.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # Route subcommand (default behavior)
    route_parser = subparsers.add_parser(
        "route", help="Route a subagent task to an external model",
        aliases=[
            "research", "discussion-prep", "test-plan",
            "improvement-scan", "qa-execution", "comprehension", "code-review",
        ],
    )
    route_parser.add_argument(
        "--task-type", default="research",
        choices=["research", "discussion-prep", "test-plan",
                 "improvement-scan", "qa-execution", "comprehension", "code-review"],
        help="Task type when using bare 'route' subcommand (default: research)",
    )
    route_parser.add_argument("--task-id", required=True, help="Task identifier")
    route_parser.add_argument("--input-files", default="", help="Comma-separated input file paths")
    route_parser.add_argument("--output-file", required=True, help="Path for output file")
    route_parser.add_argument("--context", default="", help="Additional context string")

    # List providers subcommand
    subparsers.add_parser("list-providers", help="List available model providers (JSON)")

    # Setup provider subcommand
    setup_parser = subparsers.add_parser(
        "setup-provider", help="Guide API key setup for a provider",
    )
    setup_parser.add_argument("provider", help="Provider name (e.g. openai)")

    # Validate subcommand
    validate_parser = subparsers.add_parser(
        "validate", help="Test API key for a provider with a cheap call",
    )
    validate_parser.add_argument("provider", help="Provider name (e.g. openai)")

    args = parser.parse_args()

    if args.command == "list-providers":
        providers = list_providers()
        print(json.dumps(providers, indent=2))
        sys.exit(0)
    elif args.command == "setup-provider":
        code = setup_provider(args.provider)
        sys.exit(code)
    elif args.command == "validate":
        code = validate_provider(args.provider)
        sys.exit(code)
    elif args.command in (
        "route", "research", "discussion-prep", "test-plan",
        "improvement-scan", "qa-execution", "comprehension", "code-review",
    ):
        task_type = args.command if args.command != "route" else args.task_type
        code = route(task_type, args.task_id, args.input_files, args.output_file, args.context)
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""SquidSquad Forgejo deployment automation.

Deploys a local Forgejo instance via Docker Compose, creates a repo,
generates an API token, and configures SquidSquad to use it.

Usage:
    python scripts/forgejo_setup.py check-docker       # Verify Docker is available
    python scripts/forgejo_setup.py deploy              # Deploy Forgejo via Docker Compose
    python scripts/forgejo_setup.py status              # Check if Forgejo is running
    python scripts/forgejo_setup.py create-repo NAME    # Create a repo on the Forgejo instance
    python scripts/forgejo_setup.py create-token USER   # Generate API token
    python scripts/forgejo_setup.py teardown            # Stop and remove Forgejo containers
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
COMPOSE_TEMPLATE = SCRIPT_DIR.parent / "templates" / "forgejo-compose.yaml"
DEPLOY_DIR = Path.home() / ".squidsquad" / "forgejo"

DEFAULT_PORT = 3000
DEFAULT_SSH_PORT = 2222
FORGEJO_URL = f"http://localhost:{DEFAULT_PORT}"


def check_docker():
    """Check if Docker and Docker Compose are available.

    Returns dict: {ok, docker_version, compose_version, message}
    """
    result = {"ok": False, "docker_version": None, "compose_version": None, "message": ""}

    # Check docker
    try:
        proc = subprocess.run(
            ["docker", "--version"], capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            result["message"] = "Docker not found. Install Docker Desktop or Docker Engine."
            return result
        result["docker_version"] = proc.stdout.strip()
    except FileNotFoundError:
        result["message"] = "Docker not found. Install Docker Desktop or Docker Engine."
        return result

    # Check docker compose
    try:
        proc = subprocess.run(
            ["docker", "compose", "version"], capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            result["message"] = "Docker Compose not found. Install Docker Compose v2."
            return result
        result["compose_version"] = proc.stdout.strip()
    except FileNotFoundError:
        result["message"] = "Docker Compose not found."
        return result

    # Check if Docker daemon is running
    try:
        proc = subprocess.run(
            ["docker", "info"], capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            result["message"] = "Docker daemon not running. Start Docker Desktop or dockerd."
            return result
    except Exception:
        result["message"] = "Cannot communicate with Docker daemon."
        return result

    # Check port availability — skip if our own Forgejo container is using them
    is_our_container = False
    try:
        container_check = subprocess.run(
            ["docker", "ps", "--filter", "name=squidsquad-forgejo", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=False,
        )
        is_our_container = "squidsquad-forgejo" in container_check.stdout
    except Exception:
        pass

    if not is_our_container:
        import socket
        for port in [DEFAULT_PORT, DEFAULT_SSH_PORT]:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("localhost", port)) == 0:
                    result["message"] = f"Port {port} already in use. Stop the conflicting service."
                    return result

    result["ok"] = True
    result["message"] = "Docker ready"
    return result


def deploy():
    """Deploy Forgejo via Docker Compose.

    Creates ~/.squidsquad/forgejo/ with docker-compose.yaml and starts it.
    Returns dict: {ok, url, message}
    """
    result = {"ok": False, "url": "", "message": ""}

    # Check Docker first
    docker_check = check_docker()
    if not docker_check["ok"]:
        result["message"] = docker_check["message"]
        return result

    # Create deploy directory
    DEPLOY_DIR.mkdir(parents=True, exist_ok=True)

    # Copy compose template
    compose_dest = DEPLOY_DIR / "docker-compose.yaml"
    if COMPOSE_TEMPLATE.exists():
        compose_dest.write_text(
            COMPOSE_TEMPLATE.read_text(encoding="utf-8"), encoding="utf-8",
        )
    else:
        # Write inline template if file doesn't exist
        compose_dest.write_text(_default_compose_yaml(), encoding="utf-8")

    # Start Forgejo
    proc = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=str(DEPLOY_DIR),
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        result["message"] = f"Docker Compose failed: {proc.stderr}"
        return result

    # Wait for Forgejo to be ready
    ready = _wait_for_forgejo(timeout=60)
    if not ready:
        result["message"] = "Forgejo started but not responding after 60s"
        return result

    result["ok"] = True
    result["url"] = FORGEJO_URL
    result["message"] = f"Forgejo running at {FORGEJO_URL}"
    return result


def _wait_for_forgejo(timeout=60):
    """Wait for Forgejo to respond to API requests."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(f"{FORGEJO_URL}/api/v1/version")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def status():
    """Check if Forgejo is running.

    Returns dict: {running, url, version, message}
    """
    result = {"running": False, "url": FORGEJO_URL, "version": None, "message": ""}
    try:
        req = urllib.request.Request(f"{FORGEJO_URL}/api/v1/version")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            result["running"] = True
            result["version"] = data.get("version", "unknown")
            result["message"] = f"Forgejo {result['version']} running at {FORGEJO_URL}"
    except Exception:
        result["message"] = f"Forgejo not reachable at {FORGEJO_URL}"
    return result


def create_repo(name, token, owner="squid"):
    """Create a repository on the Forgejo instance.

    Returns dict: {ok, clone_url, message}
    """
    result = {"ok": False, "clone_url": "", "message": ""}
    try:
        data = json.dumps({
            "name": name,
            "description": "SquidSquad managed project",
            "private": False,
            "auto_init": True,
            "default_branch": "main",
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{FORGEJO_URL}/api/v1/user/repos",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"token {token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            repo_data = json.loads(resp.read().decode("utf-8"))
            result["ok"] = True
            result["clone_url"] = repo_data.get("clone_url", "")
            result["message"] = f"Repo '{name}' created"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        if "already exists" in body.lower():
            result["ok"] = True
            # Query the actual repo to get the correct clone_url
            try:
                repo_req = urllib.request.Request(
                    f"{FORGEJO_URL}/api/v1/repos/{owner}/{name}",
                    headers={"Authorization": f"token {token}"},
                )
                with urllib.request.urlopen(repo_req, timeout=10) as repo_resp:
                    repo_data = json.loads(repo_resp.read().decode("utf-8"))
                    result["clone_url"] = repo_data.get("clone_url", f"{FORGEJO_URL}/{owner}/{name}.git")
            except Exception:
                result["clone_url"] = f"{FORGEJO_URL}/{owner}/{name}.git"
            result["message"] = f"Repo '{name}' already exists"
        else:
            result["message"] = f"Failed to create repo: HTTP {e.code} — {body}"
    except Exception as e:
        result["message"] = f"Failed to create repo: {e}"
    return result


def create_token(username, password):
    """Create an API token on the Forgejo instance.

    Uses basic auth to create a token. Returns dict: {ok, token, message}
    """
    result = {"ok": False, "token": "", "message": ""}
    try:
        import base64
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()

        data = json.dumps({
            "name": f"squidsquad-{int(time.time())}",
            "scopes": ["all"],
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{FORGEJO_URL}/api/v1/users/{username}/tokens",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {credentials}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
            result["ok"] = True
            result["token"] = token_data.get("sha1", "")
            result["message"] = "Token created"
    except Exception as e:
        result["message"] = f"Failed to create token: {e}"
    return result


def teardown():
    """Stop and remove Forgejo containers.

    Returns dict: {ok, message}
    """
    result = {"ok": False, "message": ""}
    if not DEPLOY_DIR.exists():
        result["ok"] = True
        result["message"] = "No Forgejo deployment found"
        return result

    proc = subprocess.run(
        ["docker", "compose", "down", "-v"],
        cwd=str(DEPLOY_DIR),
        capture_output=True, text=True, check=False,
    )
    if proc.returncode == 0:
        result["ok"] = True
        result["message"] = "Forgejo stopped and removed"
    else:
        result["message"] = f"Teardown failed: {proc.stderr}"
    return result


def _default_compose_yaml():
    """Default docker-compose.yaml for Forgejo."""
    return f"""version: "3"

services:
  forgejo:
    image: codeberg.org/forgejo/forgejo:9
    container_name: squidsquad-forgejo
    environment:
      - USER_UID=1000
      - USER_GID=1000
      - FORGEJO__server__ROOT_URL=http://localhost:{DEFAULT_PORT}/
      - FORGEJO__server__HTTP_PORT={DEFAULT_PORT}
      - FORGEJO__server__DISABLE_SSH=false
      - FORGEJO__server__SSH_PORT={DEFAULT_SSH_PORT}
      - FORGEJO__database__DB_TYPE=sqlite3
      - FORGEJO__service__DISABLE_REGISTRATION=false
      - FORGEJO__service__REQUIRE_SIGNIN_VIEW=false
    volumes:
      - forgejo-data:/data
    ports:
      - "{DEFAULT_PORT}:{DEFAULT_PORT}"
      - "{DEFAULT_SSH_PORT}:22"
    restart: unless-stopped

volumes:
  forgejo-data:
"""


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        return 0

    cmd = args[0]

    if cmd == "check-docker":
        result = check_docker()
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    elif cmd == "deploy":
        result = deploy()
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    elif cmd == "status":
        result = status()
        print(json.dumps(result, indent=2))
        return 0 if result["running"] else 1
    elif cmd == "create-repo":
        if len(args) < 2:
            print("Usage: forgejo_setup.py create-repo NAME", file=sys.stderr)
            return 2
        # Read token from secrets
        sys.path.insert(0, str(SCRIPT_DIR))
        from shared_fs import read_secret_or_env
        token = read_secret_or_env("FORGEJO_TOKEN") or ""
        if not token:
            print("FORGEJO_TOKEN not set in ~/.squidsquad/secrets", file=sys.stderr)
            return 2
        result = create_repo(args[1], token)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    elif cmd == "create-token":
        if len(args) < 2:
            print("Usage: forgejo_setup.py create-token USERNAME", file=sys.stderr)
            return 2
        import getpass
        password = getpass.getpass(f"Password for {args[1]}: ")
        result = create_token(args[1], password)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    elif cmd == "teardown":
        result = teardown()
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())

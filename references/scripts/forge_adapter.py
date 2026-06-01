#!/usr/bin/env python3
"""SquidSquad forge adapter — unified interface for GitHub and Forgejo backends.

Provides a common API surface for issue tracking, PR management, and label
operations. The GitHub backend wraps `gh` CLI. The Forgejo backend uses
direct HTTP calls (urllib, zero dependencies).

Usage:
    from forge_adapter import get_adapter
    adapter = get_adapter()  # reads config.md for provider
    adapter.list_issues(labels=["role:skill", "status:open"])
    adapter.create_issue(title="...", body="...", labels=["..."])
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_MD = REPO_ROOT / ".squidsquad" / "config.md"


def _read_forge_config():
    """Read Forge Backend section from config.md.

    Returns dict with keys: provider, endpoint, owner, repo.
    Defaults to GitHub if not configured.
    """
    defaults = {
        "provider": "github",
        "endpoint": "https://api.github.com",
        "owner": "",
        "repo": "",
    }

    if not CONFIG_MD.exists():
        return defaults

    try:
        import re
        text = CONFIG_MD.read_text(encoding="utf-8")

        # Parse Forge Backend section
        section_match = re.search(
            r"## Forge Backend\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL
        )
        if not section_match:
            return defaults

        section = section_match.group(1)
        fields = {
            "provider": r"\*\*Provider\*\*:\s*(.+)",
            "endpoint": r"\*\*Endpoint\*\*:\s*(.+)",
            "owner": r"\*\*Owner\*\*:\s*(.+)",
            "repo": r"\*\*Repo\*\*:\s*(.+)",
        }
        result = dict(defaults)
        for key, pattern in fields.items():
            m = re.search(pattern, section)
            if m:
                result[key] = m.group(1).strip()

        return result
    except Exception:
        return defaults


def _get_gh_repo_info():
    """Get owner/repo from git remote (for GitHub backend)."""
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "owner,name"],
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout.strip())
            return data.get("owner", {}).get("login", ""), data.get("name", "")
    except Exception:
        pass
    return "", ""


class ForgeAdapter:
    """Base class for forge backend adapters."""

    def __init__(self, config):
        self.config = config
        self.provider = config["provider"]
        self.endpoint = config["endpoint"]
        self.owner = config["owner"]
        self.repo = config["repo"]

    def list_issues(self, labels=None, state="open", limit=50):
        """List issues. Returns list of dicts with number, title, labels."""
        raise NotImplementedError

    def create_issue(self, title, body, labels=None):
        """Create an issue. Returns dict with number, url."""
        raise NotImplementedError

    def view_issue(self, number):
        """View issue details. Returns dict with title, body, labels, comments."""
        raise NotImplementedError

    def close_issue(self, number):
        """Close an issue."""
        raise NotImplementedError

    def add_comment(self, number, body):
        """Add a comment to an issue."""
        raise NotImplementedError

    def add_labels(self, number, labels):
        """Add labels to an issue."""
        raise NotImplementedError

    def remove_labels(self, number, labels):
        """Remove labels from an issue."""
        raise NotImplementedError

    def edit_labels(self, number, add=None, remove=None):
        """Add and remove labels in one operation."""
        if remove:
            self.remove_labels(number, remove)
        if add:
            self.add_labels(number, add)

    def create_pr(self, title, body, head, base="main", draft=True):
        """Create a pull request. Returns dict with number, url."""
        raise NotImplementedError

    def merge_pr(self, number, strategy="squash"):
        """Merge a pull request. Returns (success, message)."""
        raise NotImplementedError

    def view_pr(self, number):
        """View PR details. Returns dict."""
        raise NotImplementedError

    def list_prs(self, state="open", search="", limit=20):
        """List pull requests. Returns list of dicts."""
        raise NotImplementedError

    def pr_ready(self, number):
        """Convert draft PR to ready."""
        raise NotImplementedError

    def check_connection(self):
        """Verify connectivity to the forge. Returns (ok, message)."""
        raise NotImplementedError


class GitHubAdapter(ForgeAdapter):
    """GitHub backend — wraps `gh` CLI for full compatibility."""

    def _gh(self, args, check=False):
        """Run a gh CLI command. Returns subprocess result."""
        result = subprocess.run(
            ["gh"] + args,
            capture_output=True, text=True, check=False,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"gh command failed: {result.stderr}")
        return result

    def list_issues(self, labels=None, state="open", limit=50):
        args = ["issue", "list", "--state", state,
                "--json", "number,title,labels", "--limit", str(limit)]
        if labels:
            for label in labels:
                args.extend(["--label", label])
        result = self._gh(args)
        if result.returncode != 0:
            return []
        return json.loads(result.stdout.strip() or "[]")

    def create_issue(self, title, body, labels=None):
        args = ["issue", "create", "--title", title, "--body", body]
        if labels:
            for label in labels:
                args.extend(["--label", label])
        result = self._gh(args)
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        # Extract number from URL
        number = url.rstrip("/").split("/")[-1] if url else ""
        return {"number": number, "url": url}

    def view_issue(self, number):
        result = self._gh(["issue", "view", str(number),
                           "--json", "title,body,labels,comments"])
        if result.returncode != 0:
            return None
        return json.loads(result.stdout.strip())

    def close_issue(self, number):
        return self._gh(["issue", "close", str(number)]).returncode == 0

    def add_comment(self, number, body):
        return self._gh(["issue", "comment", str(number),
                         "--body", body]).returncode == 0

    def add_labels(self, number, labels):
        args = ["issue", "edit", str(number)]
        for label in labels:
            args.extend(["--add-label", label])
        return self._gh(args).returncode == 0

    def remove_labels(self, number, labels):
        args = ["issue", "edit", str(number)]
        for label in labels:
            args.extend(["--remove-label", label])
        return self._gh(args).returncode == 0

    def create_pr(self, title, body, head, base="main", draft=True):
        args = ["pr", "create", "--title", title, "--body", body,
                "--head", head, "--base", base]
        if draft:
            args.append("--draft")
        result = self._gh(args)
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        number = url.rstrip("/").split("/")[-1] if url else ""
        return {"number": number, "url": url}

    def merge_pr(self, number, strategy="squash"):
        result = self._gh(["pr", "merge", str(number),
                           f"--{strategy}", "--delete-branch"])
        if result.returncode == 0:
            return True, "merged"
        return False, result.stderr.strip()

    def view_pr(self, number):
        result = self._gh(["pr", "view", str(number),
                           "--json", "number,title,state,headRefName,mergeable,isDraft"])
        if result.returncode != 0:
            return None
        return json.loads(result.stdout.strip())

    def list_prs(self, state="open", search="", limit=20):
        args = ["pr", "list", "--state", state,
                "--json", "number,title,headRefName,mergeable,isDraft",
                "--limit", str(limit)]
        if search:
            args.extend(["--search", search])
        result = self._gh(args)
        if result.returncode != 0:
            return []
        return json.loads(result.stdout.strip() or "[]")

    def pr_ready(self, number):
        return self._gh(["pr", "ready", str(number)]).returncode == 0

    def check_connection(self):
        result = self._gh(["auth", "status"])
        if result.returncode == 0:
            return True, "GitHub CLI authenticated"
        return False, result.stderr.strip()


class ForgejoAdapter(ForgeAdapter):
    """Forgejo backend — direct HTTP calls via urllib."""

    def __init__(self, config):
        super().__init__(config)
        self._token = self._load_token()

    def _load_token(self):
        """Load Forgejo token from ~/.squidsquad/secrets."""
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from shared_fs import read_secret_or_env
            return read_secret_or_env("FORGEJO_TOKEN") or ""
        except ImportError:
            return os.environ.get("FORGEJO_TOKEN", "")

    def _api(self, method, path, data=None):
        """Make an API call to Forgejo. Returns parsed JSON or None."""
        url = f"{self.endpoint.rstrip('/')}/api/v1{path}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._token:
            headers["Authorization"] = f"token {self._token}"

        body = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status == 204:
                    return {}
                body = resp.read().decode("utf-8")
                return json.loads(body) if body.strip() else {}
        except urllib.error.HTTPError as e:
            print(f"[forge] HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}",
                  file=sys.stderr)
            return None
        except Exception as e:
            print(f"[forge] Request failed: {e}", file=sys.stderr)
            return None

    def _repo_path(self):
        return f"/repos/{self.owner}/{self.repo}"

    def list_issues(self, labels=None, state="open", limit=50):
        params = {"state": state, "limit": str(limit), "type": "issues"}
        if labels:
            params["labels"] = ",".join(labels)
        query = urllib.parse.urlencode(params)
        data = self._api("GET", f"{self._repo_path()}/issues?{query}")
        if not data:
            return []
        return [
            {
                "number": i["number"],
                "title": i["title"],
                "labels": [{"name": l["name"]} for l in i.get("labels", [])],
            }
            for i in data
        ]

    def create_issue(self, title, body, labels=None):
        payload = {"title": title, "body": body}
        if labels:
            # Forgejo accepts label IDs, not names. Look up IDs first.
            label_ids = self._resolve_label_ids(labels)
            if label_ids:
                payload["labels"] = label_ids
        data = self._api("POST", f"{self._repo_path()}/issues", payload)
        if not data:
            return None
        return {
            "number": data["number"],
            "url": data.get("html_url", ""),
        }

    def _resolve_label_ids(self, label_names):
        """Look up label IDs by name."""
        all_labels = self._api("GET", f"{self._repo_path()}/labels?limit=100")
        if not all_labels:
            return []
        name_to_id = {l["name"]: l["id"] for l in all_labels}
        return [name_to_id[n] for n in label_names if n in name_to_id]

    def view_issue(self, number):
        data = self._api("GET", f"{self._repo_path()}/issues/{number}")
        if not data:
            return None
        comments_data = self._api("GET", f"{self._repo_path()}/issues/{number}/comments") or []
        return {
            "title": data["title"],
            "body": data["body"],
            "labels": [{"name": l["name"]} for l in data.get("labels", [])],
            "comments": [
                {
                    "body": c["body"],
                    "author": {"login": c.get("user", {}).get("login", "")},
                    "createdAt": c.get("created_at", ""),
                }
                for c in comments_data
            ],
        }

    def close_issue(self, number):
        data = self._api("PATCH", f"{self._repo_path()}/issues/{number}",
                         {"state": "closed"})
        return data is not None

    def add_comment(self, number, body):
        data = self._api("POST", f"{self._repo_path()}/issues/{number}/comments",
                         {"body": body})
        return data is not None

    def add_labels(self, number, labels):
        label_ids = self._resolve_label_ids(labels)
        if not label_ids:
            return False
        data = self._api("POST", f"{self._repo_path()}/issues/{number}/labels",
                         {"labels": label_ids})
        return data is not None

    def remove_labels(self, number, labels):
        label_ids = self._resolve_label_ids(labels)
        all_ok = True
        for lid in label_ids:
            result = self._api("DELETE", f"{self._repo_path()}/issues/{number}/labels/{lid}")
            if result is None:
                all_ok = False
        return all_ok

    def create_pr(self, title, body, head, base="main", draft=True):
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
            "draft": draft,
        }
        data = self._api("POST", f"{self._repo_path()}/pulls", payload)
        if not data:
            return None
        return {
            "number": data["number"],
            "url": data.get("html_url", ""),
        }

    def merge_pr(self, number, strategy="squash"):
        # Per operator rule [[feedback_never_rebase_merge_instead]], rebase
        # is not exposed as a merge strategy here. Squash (default) and
        # merge-commit are the supported options.
        merge_map = {"squash": "squash", "merge": "merge"}
        data = self._api("POST", f"{self._repo_path()}/pulls/{number}/merge",
                         {"Do": merge_map.get(strategy, "squash"),
                          "delete_branch_after_merge": True})
        if data is not None:
            return True, "merged"
        return False, "merge failed"

    def view_pr(self, number):
        data = self._api("GET", f"{self._repo_path()}/pulls/{number}")
        if not data:
            return None
        return {
            "number": data["number"],
            "title": data["title"],
            "state": data.get("state", "").upper(),
            "headRefName": data.get("head", {}).get("ref", ""),
            "mergeable": data.get("mergeable", False),
            "isDraft": data.get("draft", False),
        }

    def list_prs(self, state="open", search="", limit=20):
        params = {"state": state, "limit": str(limit)}
        query = urllib.parse.urlencode(params)
        data = self._api("GET", f"{self._repo_path()}/pulls?{query}")
        if not data:
            return []
        results = [
            {
                "number": p["number"],
                "title": p["title"],
                "headRefName": p.get("head", {}).get("ref", ""),
                "mergeable": p.get("mergeable", False),
                "isDraft": p.get("draft", False),
            }
            for p in data
        ]
        if search:
            results = [r for r in results if search.lower() in r.get("headRefName", "").lower()
                       or search.lower() in r.get("title", "").lower()]
        return results[:limit]

    def pr_ready(self, number):
        # Forgejo doesn't have a direct "ready" endpoint — update draft to false
        data = self._api("PATCH", f"{self._repo_path()}/pulls/{number}",
                         {"draft": False})
        return data is not None

    def check_connection(self):
        try:
            url = f"{self.endpoint.rstrip('/')}/api/v1/version"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                version = data.get("version", "unknown")
                return True, f"Forgejo {version} at {self.endpoint}"
        except Exception as e:
            return False, f"Cannot reach Forgejo at {self.endpoint}: {e}"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_adapter_cache = None


def get_adapter(config=None):
    """Get the forge adapter for the configured backend.

    Reads config.md Forge Backend section. Defaults to GitHub.
    Caches the adapter instance for reuse within a session.
    """
    global _adapter_cache
    if _adapter_cache is not None and config is None:
        return _adapter_cache

    if config is None:
        config = _read_forge_config()

    # Fill in owner/repo from git remote if not in config
    if not config["owner"] or not config["repo"]:
        if config["provider"] == "github":
            config["owner"], config["repo"] = _get_gh_repo_info()

    provider = config["provider"].lower()
    if provider == "github":
        adapter = GitHubAdapter(config)
    elif provider in ("forgejo", "forgejo-local", "forgejo-remote"):
        adapter = ForgejoAdapter(config)
    else:
        print(f"[forge] Unknown provider '{provider}', falling back to GitHub",
              file=sys.stderr)
        adapter = GitHubAdapter(config)

    _adapter_cache = adapter
    return adapter


def reset_cache():
    """Clear the adapter cache (for testing)."""
    global _adapter_cache
    _adapter_cache = None

#!/usr/bin/env python3
"""Locate the real claude binary across install variants.

Prototype supporting docs/HARNESS-ARCH.md §14 (Proposed simplification).
The current architecture uses `shutil.which("claude")` which on Windows
returns the npm `claude.cmd` shim, not the real `claude.exe`. This
script tries to resolve to the actual binary so `Popen()` can target
it directly — eliminating the descendant-walker in thin_launcher.py.

Run:
    python references/experiments/resolve_claude.py [--verify]

`--verify` additionally Popens `--version` against the resolved path
to confirm the binary actually works.

Exits 0 on success, non-zero on resolution failure. Prints the
resolved absolute path on stdout.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


# Windows .cmd / .bat shim patterns. npm has shipped two forms:
#   newer multi-line: SET dp0=%~dp0   then   "%dp0%\path\to\bin.exe" %*
#   older one-line:   @"%~dp0\path\to\bin.exe" %*
# Match either. Greedy on the path so we catch subdirectories.
_WIN_CMD_DP0 = re.compile(r'"%dp0%\\(?P<rel>[^"]+\.exe)"', re.IGNORECASE)
_WIN_CMD_TILDE = re.compile(r'"%~dp0\\?(?P<rel>[^"]+\.exe)"', re.IGNORECASE)

# PowerShell shim (less common). Matches `& "$basedir/path/binary.exe"`.
_PS_FORWARD = re.compile(
    r'"\$basedir[/\\](?P<rel>[^"\']+\.exe)"',
    re.IGNORECASE,
)

# POSIX npm shim. Real format is:
#     exec "$basedir/node"  "$basedir/../node_modules/foo/bin/cli.js" "$@"
# (separator inside the quotes, often with an `exec node` fallback for
# missing-basedir-node case). We want the LAST $basedir-rooted argument
# on the exec line — that's the script we should Popen.
_SH_EXEC_LINE = re.compile(r'^\s*exec\s+.+$', re.MULTILINE)
_SH_BASEDIR_ARG = re.compile(r'"\$\{?basedir\}?/(?P<rel>[^"]+)"')


def _parse_shim(shim_path: Path) -> Path | None:
    """Parse a Windows/POSIX npm shim and return the forwarded binary path.

    Returns None if the file does not parse as a known shim format.
    Callers MUST NOT treat None as "use this path as-is" — that was the
    silent-fallback bug. Use `_walk_shim_chain` which surfaces the error.
    """
    try:
        text = shim_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    suffix = shim_path.suffix.lower()
    if suffix in (".cmd", ".bat"):
        # Try the newer multi-line form first, then the older one-line form.
        for pattern in (_WIN_CMD_DP0, _WIN_CMD_TILDE):
            m = pattern.search(text)
            if m:
                rel = m.group("rel").replace("/", "\\").lstrip("\\")
                return (shim_path.parent / rel).resolve()
        return None
    if suffix == ".ps1":
        m = _PS_FORWARD.search(text)
        if m:
            return (shim_path.parent / m.group("rel")).resolve()
        return None
    if suffix in ("", ".sh"):
        # POSIX npm shim: find the exec line, then grab the LAST
        # "$basedir/..." argument on it (the script the shim is forwarding to).
        for exec_line in _SH_EXEC_LINE.findall(text):
            args = _SH_BASEDIR_ARG.findall(exec_line)
            if args:
                # Last $basedir-rooted arg = the script / target.
                # For `exec "$basedir/node" "$basedir/cli.js"`, this is cli.js.
                # For `exec "$basedir/binary"`, this is the binary.
                return (shim_path.parent / args[-1]).resolve()
        return None
    # Unknown suffix → not a shim we recognize.
    return None


class BrokenShimChain(FileNotFoundError):
    """A shim forwarded to a path that doesn't exist on disk."""


def _walk_shim_chain(start: Path, max_hops: int = 4) -> tuple[Path, list[Path]]:
    """Follow shim -> shim -> ... -> real-binary, returning (final, chain).

    Raises:
        BrokenShimChain: if a shim's target doesn't exist on disk. Earlier
            versions silently returned the broken-shim path, which is the
            §3.1-defeating bug (caller would still Popen the .cmd wrapper).

    `chain` includes every intermediate path. Capped at `max_hops` to
    avoid infinite loops on misconfigured installs.
    """
    chain = [start]
    current = start
    for _ in range(max_hops):
        nxt = _parse_shim(current)
        if nxt is None:
            # Not a shim (or unrecognized format) — current is the final.
            return current, chain
        if not nxt.exists():
            raise BrokenShimChain(
                f"shim {current} points to {nxt} which does not exist on disk. "
                f"Resolver cannot safely fall back to the shim itself — that "
                f"would re-introduce the cmd.exe wrapper PID this resolver "
                f"exists to avoid."
            )
        chain.append(nxt)
        current = nxt
    return current, chain


def resolve_claude() -> tuple[Path, list[Path], str]:
    """Locate the real claude binary.

    Returns (resolved_path, full_chain, mechanism). `mechanism` is a
    short string describing how we found it (for logging).

    Raises FileNotFoundError if claude is not installed.
    """
    # Start point: whatever shutil.which returns
    on_path = shutil.which("claude")
    if not on_path:
        raise FileNotFoundError(
            "`claude` not found on PATH. Is Claude Code installed?"
        )
    entry = Path(on_path).resolve()

    # POSIX: shutil.which can return a symlink; follow it first
    if entry.is_symlink():
        entry = entry.resolve()

    final, chain = _walk_shim_chain(entry)

    # Mechanism narrative
    if len(chain) == 1:
        mechanism = "direct (no shim chain)"
    else:
        hops = " -> ".join(p.name for p in chain)
        mechanism = f"shim chain: {hops}"

    return final, chain, mechanism


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true",
                    help="Popen --version against resolved path to confirm it runs")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="Print resolution chain and metadata")
    args = ap.parse_args()

    try:
        resolved, chain, mechanism = resolve_claude()
    except BrokenShimChain as e:
        print(f"FAIL (broken shim chain): {e}", file=sys.stderr)
        return 6
    except FileNotFoundError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1

    print(str(resolved))

    if args.verbose:
        print(f"  mechanism: {mechanism}", file=sys.stderr)
        if len(chain) > 1:
            for i, p in enumerate(chain):
                tag = "ENTRY" if i == 0 else f"HOP {i}"
                print(f"  {tag}: {p}", file=sys.stderr)
            print(f"  FINAL: {resolved}", file=sys.stderr)
        print(f"  exists: {resolved.exists()}", file=sys.stderr)
        print(f"  size: {resolved.stat().st_size:,} bytes" if resolved.exists()
              else "  size: N/A", file=sys.stderr)

    if args.verify:
        if not resolved.exists():
            print("FAIL: resolved path does not exist", file=sys.stderr)
            return 2
        try:
            # Run --version with a short timeout. This proves Popen works
            # against the resolved path without the cmd shim.
            result = subprocess.run(
                [str(resolved), "--version"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired:
            print("FAIL: --version timed out (15s)", file=sys.stderr)
            return 3
        except OSError as e:
            print(f"FAIL: Popen raised {type(e).__name__}: {e}", file=sys.stderr)
            return 4

        if result.returncode != 0:
            print(f"FAIL: --version exited {result.returncode}", file=sys.stderr)
            print(f"  stderr: {result.stderr.strip()[:200]}", file=sys.stderr)
            return 5

        version = result.stdout.strip()
        print(f"  verify: --version OK -> {version!r}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

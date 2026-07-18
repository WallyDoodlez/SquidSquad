"""Windows shell scripts must be parseable by Windows PowerShell 5.1.

Regression guard for the em-dash launcher breakage: ``.squidsquad/start.ps1`` was
saved UTF-8 *without a BOM* and contained em-dash characters (U+2014). Windows
PowerShell 5.1 (``powershell.exe``) decodes a BOM-less script as the system ANSI
codepage (1252), not UTF-8, so the em-dash's bytes ``E2 80 94`` become ``â€"`` —
and that trailing byte decodes to U+201D (``"``), a *smart quote*. PowerShell
treats smart quotes as valid string delimiters, so the injected quote silently
unbalanced every string after it, cascading into "array index expression",
"missing terminator", and "missing closing brace" parse errors — the harness
would not launch at all.

The crisp invariant that prevents this, independent of the operator's active
codepage: **every Windows shell script must be pure ASCII, or carry a UTF-8 BOM.**
Either one makes Windows PowerShell decode it correctly. This is byte inspection
only (no PowerShell needed), so it runs on CI/Linux too.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Windows-consumed script extensions. .sh is intentionally excluded — those are
# POSIX scripts pinned to LF and read as UTF-8 by the shell.
_WINDOWS_SCRIPT_GLOBS = ("*.ps1", "*.bat", "*.cmd")

_UTF8_BOM = b"\xef\xbb\xbf"

# Characters that are especially dangerous in PowerShell because it accepts them
# as string/quote delimiters — a stray one flips the parser's string state.
_SMART_QUOTES = {
    0x2018: "‘ (U+2018 left single quote)",
    0x2019: "’ (U+2019 right single quote)",
    0x201C: "“ (U+201C left double quote)",
    0x201D: "” (U+201D right double quote)",
}


def _windows_scripts():
    seen = []
    for pattern in _WINDOWS_SCRIPT_GLOBS:
        for path in REPO_ROOT.rglob(pattern):
            # Skip VCS internals; everything else (incl. test fixtures) must comply.
            if ".git" in path.parts or "node_modules" in path.parts:
                continue
            seen.append(path)
    return sorted(seen)


def _first_non_ascii(text):
    """Return (line_no, col, codepoint) of the first non-ASCII char, or None."""
    for line_no, line in enumerate(text.splitlines(), start=1):
        for col, ch in enumerate(line, start=1):
            if ord(ch) > 127:
                return line_no, col, ord(ch)
    return None


# Collect once so the id shows the offending file in test output.
_SCRIPTS = _windows_scripts()


def test_repo_has_windows_scripts_to_guard():
    # Sanity: the guard is meaningless if the glob silently matches nothing
    # (e.g. a future refactor moves launchers). Keep it honest.
    assert _SCRIPTS, "expected at least the launcher .ps1 scripts under the repo"


@pytest.mark.parametrize("script", _SCRIPTS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_windows_script_is_ascii_or_has_bom(script):
    raw = script.read_bytes()
    has_bom = raw.startswith(_UTF8_BOM)
    text = raw.decode("utf-8")  # any decode error here is itself a real defect

    hit = _first_non_ascii(text)
    if hit is None:
        return  # pure ASCII — always safe

    line_no, col, cp = hit
    rel = script.relative_to(REPO_ROOT)
    smart = _SMART_QUOTES.get(cp)
    detail = (
        f"{rel} contains non-ASCII char U+{cp:04X} at line {line_no} col {col}"
        + (f" [{smart}]" if smart else "")
    )
    assert has_bom, (
        detail
        + " — and the file has NO UTF-8 BOM. Windows PowerShell 5.1 will decode it "
        "as the ANSI codepage and mis-parse it. Fix: replace the char with ASCII, "
        "or save the file with a UTF-8 BOM."
    )


@pytest.mark.parametrize(
    "launcher", [".squidsquad/start.ps1"], ids=lambda p: p
)
def test_critical_launcher_is_strictly_ascii(launcher):
    # The primary launcher is the one an operator runs first; hold it to the
    # stricter bar (pure ASCII, no BOM reliance) so it can never regress the way
    # the em-dash break did — regardless of how any editor handles the BOM.
    path = REPO_ROOT / launcher
    if not path.is_file():
        pytest.skip(f"{launcher} not present in this checkout")
    hit = _first_non_ascii(path.read_text(encoding="utf-8"))
    assert hit is None, (
        f"{launcher} must be pure ASCII; found U+{hit[2]:04X} at line {hit[0]} col {hit[1]}"
    )

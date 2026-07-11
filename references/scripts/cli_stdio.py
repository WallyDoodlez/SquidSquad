"""Shared CLI stdout/stderr hardening for SquidSquad scripts (#13198).

Windows consoles default to the cp1252 code page, which cannot encode many
characters that show up decoratively in script output (e.g. U+2192 '->',
U+2014 em-dash, U+2022 bullet). A script that prints such a character to a
cp1252 console raises ``UnicodeEncodeError`` — and when that crash lands in
a SUCCESS print *after* a side effect has already happened, the non-zero exit
is a FALSE FAILURE that invites a harmful retry (the #13185 ``tracker.py
work-assign`` double-emit: the wake fired, the success line crashed, exit 1,
caller retries → double wake).

``harden_stdio()`` reconfigures stdout/stderr with ``errors="backslashreplace"``
so no unencodable character can crash the CLI again. It keeps the console's own
encoding (ordinary ASCII output is untouched; the rare non-ASCII char is
backslash-escaped instead of raising), which is less surprising than forcing
UTF-8 (that would mojibake every non-ASCII char on a legacy console).

Call it ONCE at the top of a script's ``main()`` / CLI entry — **never at
import time**: these modules are also imported as libraries, and reconfiguring
a library consumer's global stdio would be wrong. It is best-effort: a stream
that cannot be reconfigured (already detached / replaced / captured without a
``reconfigure`` method) is left as-is rather than raising. Python 3.7+
(SquidSquad targets 3.10+).
"""

import sys


def harden_stdio():
    """Make ``sys.stdout`` / ``sys.stderr`` crash-proof on a console whose
    encoding cannot represent every printed character.

    Idempotent and best-effort. See the module docstring for why this is
    CLI-entry-only (not import-time) and why ``backslashreplace`` over UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError, OSError):
            # AttributeError: not a reconfigurable TextIOWrapper (e.g. a
            # replaced/captured stream). ValueError/OSError: stream detached or
            # otherwise not reconfigurable. Best-effort — never crash the CLI
            # while trying to make the CLI crash-proof.
            pass

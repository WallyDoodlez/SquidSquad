"""Assemble-pass cache layer — pure I/O (#10443, PRD-B Story B6).

Stores and retrieves assembled outputs keyed on a SHA256 of the inputs
that uniquely determine an assemble call: linked body, slot name, slot
purpose, model id, and prompt template version.

Per PRD-B success criterion 8 + TRD §4.6, the cache lives at
``.squidsquad/<alias>/.assemble-cache/`` and is git-tracked. The first
uncached run is stochastic (LLM rewrite); committing the cache makes
subsequent re-runs with unchanged inputs deterministic.

No LLM dependency. No eviction (cache grows monotonically with git).
"""

import hashlib
import os
import re
import sys
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CACHE_DIRNAME = ".assemble-cache"
# ASCII Unit Separator (0x1F) — boundary byte so that ("ab","c") and
# ("a","bc") hash to different keys. The tokenization is injective
# under the assumption that no input part itself contains a 0x1F byte;
# real inputs are markdown / human prose where 0x1F never appears.
_SEPARATOR = b"\x1f"
# Aliases come from config but `_cache_dir` is the only path-construction
# site, so we validate here to refuse any value that could escape
# `.squidsquad/<alias>/` (e.g. `..`, slashes, NULs).
_ALIAS_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")


def cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version):
    """Return the SHA256 hex digest of the five inputs joined by 0x1F.

    Each part is UTF-8 encoded if it's a ``str``; bytes are used as-is.
    Order matters — callers must always pass the parts in the same
    order or the key will differ.
    """
    h = hashlib.sha256()
    for part in (linked_body, slot_name, slot_purpose, model_id, prompt_version):
        if isinstance(part, str):
            part = part.encode("utf-8")
        h.update(part)
        h.update(_SEPARATOR)
    return h.hexdigest()


def _cache_dir(alias):
    if not isinstance(alias, str) or not _ALIAS_RE.match(alias):
        raise ValueError(f"Invalid alias: {alias!r}")
    return _REPO_ROOT / ".squidsquad" / alias / _CACHE_DIRNAME


def cache_lookup(alias, key, *, slot_name=None):
    """Return the cached assembled body for ``(alias, key)`` or ``None``.

    On hit, emits ``[cache hit] alias=<a> slot=<s>`` to stderr per
    PRD-B success criterion 8. ``slot_name`` is an optional kwarg used
    only for the log line; when omitted the slot field renders as ``?``.
    The literal positional signature ``(alias, key)`` matches the AC.
    """
    path = _cache_dir(alias) / f"{key}.md"
    if not path.is_file():
        return None
    body = path.read_text(encoding="utf-8")
    slot_repr = slot_name if slot_name is not None else "?"
    print(f"[cache hit] alias={alias} slot={slot_repr}", file=sys.stderr)
    return body


def cache_store(alias, key, assembled_body):
    """Atomically write ``assembled_body`` to the alias's cache dir.

    Creates ``.squidsquad/<alias>/.assemble-cache/`` if needed, then
    writes to ``<key>.md.tmp`` and ``os.replace`` swaps it into the
    final ``<key>.md`` so a concurrent reader never sees a partial file.
    """
    cache_dir = _cache_dir(alias)
    cache_dir.mkdir(parents=True, exist_ok=True)
    final = cache_dir / f"{key}.md"
    tmp = cache_dir / f"{key}.md.tmp"
    tmp.write_text(assembled_body, encoding="utf-8")
    try:
        os.replace(tmp, final)
    except OSError:
        # On Windows os.replace can raise ERROR_SHARING_VIOLATION if a
        # concurrent cache_lookup has the destination open mid-read.
        # Leave no .tmp behind for the next store.
        tmp.unlink(missing_ok=True)
        raise

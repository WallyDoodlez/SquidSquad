"""B9 cache adapter (#10763 AC4): bridge B7's seam signatures to
B6's real cache API.

B7's ``atomic_emit.assemble_and_emit`` expects two callables with
small, slot-shaped signatures:

  - ``cache_lookup_fn(slot, linked_slot_body) -> str | None``
  - ``cache_store_fn(slot, linked_slot_body, assembled_body)``

B6's ``assemble_cache`` exposes a richer key-shaped API:

  - ``cache_key(linked_body, slot_name, slot_purpose, model_id,
      prompt_version) -> str``
  - ``cache_lookup(alias, key, *, slot_name=None) -> str | None``
  - ``cache_store(alias, key, assembled_body) -> None``

The two surfaces talk past each other — there's no in-tree caller
that constructs the key, threads alias / model_id / prompt_version,
and converts the slot-tuple into the B6 shape. Without this adapter
the assemble pipeline runs cache-disabled (B6 dead code, B7 cache
seams unwired), violating PRD-B SC8 (cache hit logging) and SC7
(cache key over model_id) at first run.

This module is the only consumer of both surfaces. Tests cover the
adapter's lookup/store round-trip + cache-key composition + the
stability invariants the cache_key SHA depends on (slot name,
model_id, prompt_version, slot_purpose all baked in).

Slot purposes (the third cache_key parameter) — a stable per-slot
descriptor folded into the SHA so that, e.g., the same linked body
under ``identity`` and ``soul`` hashes to two distinct keys. Values
are stable strings; changing one invalidates the corresponding
slot's cache entries by design.
"""

from typing import Callable, Optional

import assemble_cache as _ac


# Stable slot → purpose strings. Each value describes the slot's
# rewrite intent for the LLM and contributes entropy to the cache key
# so the same linked body across slots doesn't collide. The values
# are load-bearing for cache identity — DO NOT edit casually. Each
# edit invalidates every cache entry for that slot.
DEFAULT_SLOT_PURPOSES = {
    "identity":         "rewrite identity-slot composite to one voice",
    "responsibility":   "rewrite responsibility-slot composite to one voice",
    "soul":             "rewrite soul-slot composite to one voice",
    "instructions":     "rewrite instructions-slot composite to one voice",
    # project-context and vault are verbatim slots — atomic_emit skips
    # the LLM call entirely. They still appear here so callers iterating
    # the full slot set don't trip a KeyError if a future refactor passes
    # them through the cache path.
    "project-context":  "verbatim — no rewrite",
    "vault":            "verbatim — no rewrite",
}


def make_b6_cache_adapter(
    *,
    alias: str,
    model_id: str,
    prompt_version: str,
    slot_purposes: Optional[dict] = None,
):
    """Return ``(cache_lookup_fn, cache_store_fn)`` wired to B6's cache.

    The pair plugs into ``atomic_emit.assemble_and_emit``'s
    ``cache_lookup_fn=`` / ``cache_store_fn=`` seams.

    ``alias`` — the per-install agent alias (e.g. ``"pm"`` /
    ``"frontend-1"``). B6's cache files land under
    ``.squidsquad/<alias>/.assemble-cache/``.

    ``model_id`` — the LLM model whose output is being cached. Folded
    into the cache key so switching models cannot produce a silent
    cache-hit on stale prose (PRD-B SC7).

    ``prompt_version`` — a stable identifier for the assemble prompt
    template's current shape. Bumping this invalidates every cache
    entry — used when ``assemble_pass``'s prompt prose is rewritten
    in a way that should change the LLM's output.

    ``slot_purposes`` — optional override of :data:`DEFAULT_SLOT_PURPOSES`.
    Tests inject this; production callers should pass ``None`` so the
    stable defaults are used.
    """
    if slot_purposes is None:
        slot_purposes = DEFAULT_SLOT_PURPOSES

    def _key_for(slot: str, linked_slot_body: str) -> str:
        slot_purpose = slot_purposes.get(slot, "")
        return _ac.cache_key(
            linked_slot_body,
            slot,
            slot_purpose,
            model_id,
            prompt_version,
        )

    def cache_lookup_fn(slot: str, linked_slot_body: str) -> Optional[str]:
        key = _key_for(slot, linked_slot_body)
        return _ac.cache_lookup(alias, key, slot_name=slot)

    def cache_store_fn(slot: str, linked_slot_body: str,
                       assembled_body: str) -> None:
        key = _key_for(slot, linked_slot_body)
        _ac.cache_store(alias, key, assembled_body)

    return cache_lookup_fn, cache_store_fn

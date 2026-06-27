---
type: learning
role: dm
created: 2026-06-20
tags: [dm, config, counter, ship-gate, gotcha]
owner: dm-lead
status: active
confidence: high
source: observation
links: [learning-config-merge-ours-drops-concurrent-changes, feedback_ship_counter_manual]
---

# Post-#12823, set the ship counter with the canonical key `shipped-since-bump` — NOT the display name

Since #12823 (SHIPPED 2026-06-20), the ship counter lives in `.squidsquad/.ship-counter`, not in `config.md`. `config.py` redirects counter access to that file **only when the field is the canonical key `shipped-since-bump`** (`config.py:_SHIP_COUNTER_FIELD`). 

## The gotcha

`python config.py set "Shipped Since Last Bump" <N>` (the human-readable DISPLAY name) does **not** match the redirect condition — it writes the value back into `config.md`'s now-vestigial field instead of `.ship-counter`. The value still *reads* back correct (a config.md migration fallback + `_parse_all` overlay paper over it), so the mistake is silent. But the authoritative `.ship-counter` file is never written.

Observed live shipping #12823 itself: a first `set "Shipped Since Last Bump" 53` only touched config.md (no `.ship-counter` created); re-running `set shipped-since-bump 53` materialized `.ship-counter=53`.

## Apply

- **Counter writes** (the per-ship increment and the bump-reset): use the canonical key — `python references/scripts/config.py set shipped-since-bump <N>`. The `delivery-packaging` and `version-bumps` sub-skills already use this form; the trap is only in ad-hoc/inline invocations using the display name.
- **Counter reads**: either key returns the right number (the overlay handles it), so reads are safe — but prefer `get shipped-since-bump` for clarity.
- `.squidsquad/.ship-counter` is a tracked file (git_ops commit allowlist, `merge=ours`); the legacy `config.md` "Shipped Since Last Bump" field is vestigial once `.ship-counter` exists. Counter ownership/manual-increment discipline is unchanged ([[feedback_ship_counter_manual]]).

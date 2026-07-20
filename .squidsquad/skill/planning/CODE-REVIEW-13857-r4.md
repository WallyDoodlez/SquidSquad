NO_FINDINGS

The round-3 fix on lines 506–510 correctly handles all edge cases:

- `Math.trunc()` (not `Math.floor()`) properly truncates toward zero, so `-3.7` → `-3` (not `-4`), which is then clamped by `Math.max(0, …)` to `0`.
- The guard `args.top != null && Number.isFinite(args.top)` correctly rejects `null`, `undefined`, `NaN`, and `Infinity`, falling back to `cfg.searchTopK`.
- `topK = 0` causes `buildEvents` on line 396 to call `.slice(0, 0)`, returning an empty array — zero events, matching the "fail closed to 0" intent.
- Positive `--top` values (including floats like `3.7`) are truncated and passed through normally.
- No `--top` falls through to the config value, which is also clamped identically.

No new defects in this file.
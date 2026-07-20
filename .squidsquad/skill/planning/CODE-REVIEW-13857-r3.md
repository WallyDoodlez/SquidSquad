I've carefully reviewed the single changed file `vault-query.mjs` against the stated acceptance criteria and locks. Here are my findings.

---

### Finding 1

- **File**: references/skills/vault-search/scripts/vault-query.mjs
- **Line**: 432 (and the `buildEvents` slice at line 296)
- **Severity**: warning
- **Issue**: Negative `--top` values (e.g. `--top -1`) are not rejected or clamped, and propagate directly into `Array.slice(0, topK)`. In JavaScript, `slice(0, -1)` returns *all elements except the last*, which is the opposite of "cap results" — it silently truncates the lowest-ranked item while surfacing everything else, completely subverting the intended top-K cap.
- **Evidence**: 
  - Line 415: `else if (a === '--top') out.top = Number(argv[++i]);` — accepts any numeric, including negative.
  - Line 432: `const topK = args.top != null && Number.isFinite(args.top) ? args.top : cfg.searchTopK;` — passes negative values through (negative numbers are finite).
  - Line 296: `const surfaced = [...results, ...traversed].slice(0, topK);` — `slice(0, -1)` drops exactly the last element instead of capping at N.
  - A user intending `--top 0` but who mistypes `--top -1` (or a script generating a negative value) would get the opposite of the expected behavior, and events would fire for nearly all results rather than zero.
- **Suggested fix**: Clamp `topK` to a non-negative integer before use. For example, after line 432:

  ```javascript
  const topK = Math.max(0, args.top != null && Number.isFinite(args.top) ? args.top : cfg.searchTopK);
  ```

  This guarantees `--top -1` (or any negative) degrades to zero results / zero events, which is the safest fail-closed behavior for an unexpected input.

---

## Lock verification summary

All five locks pass re-inspection:

| Lock | Status | Evidence |
|------|--------|----------|
| **Telemetry only via `appendEvents` to caller's shard** | ✅ | Lines 440–449: writes go through `appendEvents(args.vault, args.instanceId, args.alias, events, deps)`; shard path derived from instance ID + alias via `shardPath`. |
| **`impression` / `walked` only; `used` never written** | ✅ | Line 299: `makeEvent(…, item.direct ? 'impression' : 'walked', …)`. No `'used'` string anywhere in the write path. |
| **`--no-write` → zero events** | ✅ | Lines 435–437: `!args.write` branch sets `written = { events: 0, … }` and skips `buildEvents`/`appendEvents` entirely. |
| **Caller identity required** | ✅ | Lines 426–429: empty `instanceId` or `alias` → exit 2 with explicit error message referencing §8.5. |
| **Fail-open on telemetry write failure** | ✅ | Lines 444–447: `appendEvents` failure caught, logged to stderr as a warning, does not change exit code (still 0). |

## `--task` fix confirmed

Lines 397–403:

```javascript
const n = Number.parseInt(argv[++i], 10);
out.task = Number.isFinite(n) && n >= 1 ? n : null;
```

- `--task 0` → 0, fails `n >= 1` → `null` ✓
- `--task -5` → -5, fails `n >= 1` → `null` ✓
- `--task abc` → NaN, `Number.isFinite(NaN)` → false → `null` ✓
- `--task 1` → 1, passes → `1` ✓
- `--task` omitted → stays at initial `null` ✓

This matches the stated requirement: *"0/negative/garbage degrade to null, matching record-consumption."*
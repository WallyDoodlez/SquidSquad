I've thoroughly reviewed the diff, the surrounding code, the global exception handler, and the import/usage patterns.

**Analysis summary:**

- **Correctness**: The try/except wraps ONLY `await request.json()`, so there's no risk of a broad `ValueError` catching exceptions from other code paths. `json.JSONDecodeError` is indeed a `ValueError` subclass, so the tuple `(json.JSONDecodeError, ValueError)` is technically redundant but explicit — the comment correctly notes this also covers `UnicodeDecodeError` (another `ValueError` subclass) for defense-in-depth.

- **Response contract**: The existing contract (documented at lines 3063–3073) covers 200, 204, and 400 (missing fields). A new 400 for a malformed body is entirely consistent. The global handler at line 2401 explicitly re-raises `HTTPException` instances, guaranteeing the 400 passes through as a response rather than being captured as a 500.

- **Edge cases**: Empty body → `JSONDecodeError` → 400 (correct, it's malformed). Non-UTF-8 binary body → `UnicodeDecodeError` → caught by `ValueError` → 400 (correct). Valid non-dict JSON like `[1,2,3]` or `null` → passes `request.json()` → would hit `body.get(...)` and raise `AttributeError` → 500 (pre-existing, not introduced by this change, and outside the scope of the JSON-parse fix).

- **Integration**: `HTTPException` (FastAPI → Starlette) is the same exception class used throughout the file for 400/404/409/503 responses. The `_log` call provides diagnostic visibility matching the existing pattern used for the unknown-role DROP (line 3111–3113).

- **No regression**: The only behavioral change is converting a 500 (crash) into a 400 (clean rejection) for malformed JSON bodies. Valid requests are unaffected.

NO_FINDINGS
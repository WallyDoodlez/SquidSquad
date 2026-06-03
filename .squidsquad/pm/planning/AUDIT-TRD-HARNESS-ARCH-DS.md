Now I have all the evidence needed. Let me compile the systematic audit.

---

# Harness Architecture Audit: HARNESS-ARCH.md vs Manifest

## Evidence Sources
- `docs/HARNESS-ARCH.md` (lines 1–576)
- `.squidsquad/pm/planning/AUDIT-MANIFEST-IN-PROGRESS.md`
- `references/scripts/harness.py` (FastAPI routes at lines 1618–2755; EAD at lines 3110–3140)
- `.squidsquad/pm/working/bundled-task-body.md` (#10182 scope)
- `.squidsquad/skill/planning/REVIEW-ROLE-ALIAS-AUDIT.md` (#10358 status)
- `CHANGELOG.md` (v0.40.0–v0.43.0 shipped items)

---

## Finding 1: `POST /events/{event_id}/complete` exists in code but doc claims it doesn't

- **TRD section**: §4.2, line 102 — "No completion endpoint (locked, per AGENT-RUNTIME §4.1 principle #4): there is no `POST /events/{event_id}/complete`."
- **Verdict**: DRIFT
- **Evidence**: `references/scripts/harness.py:2249` — `@app.post("/events/{event_id}/complete")` with a full handler (lines 2250–2304) that acks events and executes mechanical side effects. The endpoint exists and is functional.
- **Severity**: high
- **Suggested action**: Either (a) the doc's "no completion endpoint" claim is wrong and must be corrected to document the existing endpoint (with any deprecation notice if applicable), or (b) the endpoint must be removed from code if the locked principle truly forbids it. The AGENT-RUNTIME.md rev-10 entry (line 1233) says the permission table was retired in favor of alias-existence checks, and `ack-cursor` is the new ack mechanism — but the old `/complete` endpoint remains. Reconcile doc and code.

---

## Finding 2: `POST /work/assign` is documented but does not exist in code

- **TRD section**: §4.3, lines 106–110 — Documents `POST /work/assign` with request body `{issue_number, target_alias, event_context}` and validation rules.
- **Verdict**: DRIFT
- **Evidence**: `references/scripts/harness.py` — complete FastAPI route listing (lines 1618–2755) has no `/work/assign` route. Grep for `@app.post.*assign` returns zero hits. The endpoint is extensively referenced in `docs/AGENT-RUNTIME.md` §7.3, the vault decision `decision-class-vs-alias-routing-model.md`, and `bundled-task-body.md` (#10182 ACs), but it is not implemented in the harness.
- **Severity**: high
- **Suggested action**: Either implement `POST /work/assign` in `harness.py` per the documented contract, or mark §4.3 as aspirational/planned (similar to the §4.1 aspirational note). The bundled task #10182 assumes this endpoint exists as the foundation for replacing permission-table logic with alias-existence checks. Without it, the target architecture described in both HARNESS-ARCH.md and AGENT-RUNTIME.md cannot function as described.

---

## Finding 3: `POST /merge` exists in code but is not documented

- **TRD section**: §4 (HTTP API surface) — No mention of `/merge` endpoint.
- **Verdict**: DRIFT
- **Evidence**: `references/scripts/harness.py:2755` — `@app.post("/merge", status_code=202)` with a handler (lines 2756–2805+) that merges PRs asynchronously, detects `references/` changes, runs compose if needed, and emits `pr-merged` + `compose-completed` events. This endpoint is absent from the §4 endpoint tables and has no documentation anywhere in HARNESS-ARCH.md.
- **Severity**: medium
- **Suggested action**: Add `POST /merge` to the §4 API surface documentation (either §4.1 or a new subsection). Document purpose, request body shape, response semantics, and async behavior (202 Accepted).

---

## Finding 4: §4.1 endpoint response shapes are aspirational — doc claims descriptive

- **TRD section**: §4.1 table (lines 70–83) + response-shape status note (lines 85–87).
- **Verdict**: DRIFT
- **Evidence**: The status banner (line 3) says "§§1–13 are a descriptive snapshot of the harness as it exists in code today." But §4.1 lines 85–87 explicitly say the response shapes are "aspirational" and document the post-#10358 target. Current `AgentState.to_dict()` returns `role` (not `alias`), `claude_pid` + `terminal_pid` (not `pid`). The table rows show `{role, alias, intent, status, pid, ...}` which doesn't match current code output.
- **Severity**: medium
- **Suggested action**: Either (a) update the §4.1 table to reflect actual current response shapes (with a footnote about the post-#10358 target), or (b) narrow the status banner to say "§§1–13 describe the harness as it exists in code today, except §4.1 response shapes which are aspirational." Currently the doc contradicts its own status banner.

---

## Finding 5: §4.2 uses `{alias}` path parameters; code uses `{role}`

- **TRD section**: §4.2 table (lines 91–98) + path-parameter note (lines 100–102).
- **Verdict**: DRIFT
- **Evidence**: The doc table shows `/events/for/{alias}`, `/events/cursor/{alias}`, `/events/in-flight/{alias}`. But `harness.py:2158` has `@app.get("/events/for/{role}")`, line 2228 has `@app.get("/events/cursor/{role}")`, line 2307 has `@app.get("/events/in-flight/{role}")`. The doc note acknowledges this but the table still diverges from code. The `{alias}` token in the table does not match the actual FastAPI route parameter name.
- **Severity**: low
- **Suggested action**: The doc note already explains the mismatch. Either change the table to use `{role}` to faithfully track current code (with the note explaining the semantic value is an alias), or leave as-is but acknowledge this is another aspirational element alongside §4.1.

---

## Finding 6: `#10358` (`role` → `alias` rename) — not tracked in manifest

- **TRD section**: §3 line 59, §4.1 lines 85–87, §4.2 line 100, §9 lines 386–387, §14.2 line 507.
- **Verdict**: GAP
- **Evidence**: HARNESS-ARCH.md references #10358 in at least five locations as the task that will close the code-level `role` → `alias` naming mismatch. The code still uses `role` everywhere: `harness.py` FastAPI routes use `{role}` path parameters (lines 1759, 1773, 1824, 1864, 2158, 2228, 2307, 2465, 2488); EAD emits `target_role` field (lines 3117, 3123); event filtering checks `target_role` (line 2198). The manifest lists no entry for #10358 — not in-flight, not held, not shipped. The role-alias audit file (`.squidsquad/skill/planning/REVIEW-ROLE-ALIAS-AUDIT.md`) confirms doc-level edits landed on PR #10357 but the code rename remains deferred.
- **Severity**: medium
- **Suggested action**: Add #10358 to the manifest as either in-flight or held (it's currently "on hold pending PR #10357 merging and #10182 progressing" per HARNESS-ARCH.md §9). Without manifest tracking, this cross-cutting rename has no visibility in the project's work-tracking system.

---

## Finding 7: `#10182` (permission table removal) — not tracked in manifest

- **TRD section**: §13.5, lines 458–465 — Documents "removal in progress" with task #10182 "bundled, on hold pending PR #10004 merge."
- **Verdict**: GAP
- **Evidence**: `.squidsquad/pm/working/bundled-task-body.md` defines #10182's scope (7 coordinated changes including dropping `responsibility.md`, replacing permission table with alias-existence check, renaming `target_role` → `target_alias`, etc.) with status "ON HOLD — do not pick up until explicitly approved." Gated on PR #10004 merge. Not listed in the manifest's in-flight or held sections. The harness code still references `target_role` (lines 3117, 3123, 2198) and there's no `/work/assign` endpoint (Finding 2), so this work has not shipped.
- **Severity**: medium
- **Suggested action**: Add #10182 to the manifest's held section with its gate condition (PR #10004 merge). Currently it's invisible to the manifest-based audit process despite being a documented architectural dependency for #10358 and the `/work/assign` endpoint.

---

## Finding 8: `#8704` shipped `/human/queue` but `/queue/{alias}` generalization is untracked

- **TRD section**: §4.4 lines 114–122 + §13.6 lines 466–469.
- **Verdict**: GAP
- **Evidence**: CHANGELOG.md v0.40.0 (line 73) confirms #8704 shipped delivering `/human/queue`. But HARNESS-ARCH.md §4.4 documents `/queue/{alias}` as the principled generalized form, and §13.6 acknowledges the gap: "Current code only implements `/human/queue`." The migration plan (rename route, parameterize filter, 301 redirect for legacy path) has no corresponding work item in the manifest — not in-flight, not held. `harness.py:2410` still has only `@app.get("/human/queue")`.
- **Severity**: low
- **Suggested action**: File a follow-up ticket for the `/queue/{alias}` generalization and add it to the manifest (held or planned). Alternatively, if this is indefinitely deferred, update §4.4 to document `/human/queue` as the current state and move the `/queue/{alias}` shape to §14 (proposed) or §13 (known gaps).

---

## Finding 9: `#10182` gate condition `PR #10004 merge` may be stale

- **TRD section**: §13.5, line 464 — "Removal task: #10182 (bundled, on hold pending PR #10004 merge)."
- **Verdict**: STALE
- **Evidence**: The HARNESS-ARCH.md revision log (line 576) states the v1 draft was "Created alongside the class-vs-alias / permission-table-retirement architectural pass in PR #10004." The AGENT-RUNTIME.md revision log shows extensive revisions through rev 14 (2026-05-30) incorporating the target architecture decisions that PR #10004 was supposed to establish (alias-existence checks, `X-Squidsquad-Alias` header, harness `role:*` label writes). The `.squidsquad/pm/working/bundled-task-body.md` still says PR #10004 is "currently in review." If PR #10004 has merged (evidenced by its decisions being locked into AGENT-RUNTIME.md revs 10–14), then #10182's gate condition is satisfied and the task should be unblocked. If it hasn't merged, the docs are incorporating decisions from an unmerged PR.
- **Severity**: medium
- **Suggested action**: Verify PR #10004 status. If merged, update `bundled-task-body.md` to remove the gate and move #10182 toward `approved`. If not merged, the docs should not cite its decisions as locked/authoritative.

---

## Finding 10: `POST /shutdown` documented return shape differs from §4.1 aspirational note scope

- **TRD section**: §4.1 table, line 83 — Documents `POST /shutdown` returning `{ok: true, action: "shutdown-initiated"}` with HTTP 202.
- **Verdict**: DRIFT
- **Evidence**: The aspirational note at lines 85–87 says "the response shapes above are aspirational" but specifically attributes this to #10358 (the `role` → `alias` rename). However, the `/shutdown` return shape `{ok: true, action: "shutdown-initiated"}` — is this also aspirational or current? The note's scope is ambiguous: it says the shapes "document the target shape that lands with #10358" but #10358 is about identifier renames, not the `/shutdown` response shape. The actual `harness.py:2566` handler should be checked. The ambiguity means a reader can't tell which response shapes in the table are current vs. aspirational.
- **Severity**: low
- **Suggested action**: Clarify exactly which fields in the response-shape column are aspirational vs. current. The note currently ties all aspirational content to #10358, but some response-shape differences (like `pid` vs `claude_pid`/`terminal_pid`) are #10358-related while others may be independently aspirational.

---

## Finding 11: §14 proposed simplification — no manifest tracking

- **TRD section**: §14, lines 472–567 — "Proposed simplification: `wt → claude` direct spawn."
- **Verdict**: STALE
- **Evidence**: §14 is explicitly "not implemented" with ~95 lines of detailed design, implementation outline with 6 landing steps, validation evidence from `references/experiments/`, and net-impact estimates (~600 lines deleted). It has no corresponding work item in the manifest — not in-flight, not held. The experiments exist but the proposal has no tracking. The doc itself admits this is a proposal in a document whose primary status banner says §§1–13 are descriptive.
- **Severity**: low
- **Suggested action**: Either (a) file a tracking issue for the §14 simplification and add it to the manifest (held or planned), or (b) extract §14 into a separate design proposal document and replace it with a cross-reference. Leaving unimplemented proposals inside an architecture doc that claims to be a "descriptive snapshot" creates confusion about what is vs. isn't real.

---

## Finding 12: Known gaps §13.1–13.4 have no corresponding work items

- **TRD section**: §13.1–13.4, lines 442–457.
- **Verdict**: GAP (4 items)
- **Evidence**: Four architectural gaps are documented:
  - §13.1: No deque persistence ("not implemented and out of scope for the present architecture")
  - §13.2: No API authentication ("not on the immediate roadmap")
  - §13.3: No multi-host support ("not implemented")
  - §13.4: EAD polling is forge-specific ("EAD does not yet use it")
  
  None of these have corresponding work items in the manifest. Unlike §13.5 and §13.6 which reference specific tickets (#10182, #8704), these four are acknowledged gaps with no tracking. Per the manifest instructions, these are REAL GAPS — TRD-promised features (or documented architectural limitations) with no shipped, in-progress, or held work.
- **Severity**: low (all are explicitly documented as out-of-scope or not-on-roadmap)
- **Suggested action**: These are fine as documented gaps if they're genuinely not planned. The manifest audit framework just needs to acknowledge them. If any of these should be on the roadmap, file tickets and add to manifest.

---

## Finding 13: `#8692` and `#10101` referenced in §14.3 as deletable — not in manifest

- **TRD section**: §14.3, lines 519–520 — Lists `#8692` (Singleton race class) and `#10101` (Stale-wrapper-PID failure mode) as bugs that would be deleted by the §14 simplification.
- **Verdict**: STALE
- **Evidence**: These issue numbers are referenced as things that would be fixed by the unimplemented §14 proposal. Neither appears in the manifest. If §14 is not being actively pursued, these bugs remain open but invisible to the manifest-based tracking system.
- **Severity**: low
- **Suggested action**: If #8692 and #10101 are real bugs, they should be tracked independently of §14. If they only exist because of `thin_launcher.py` and have no impact in practice, note that explicitly.

---

## Summary Table

| Section | Feature/Claim | Verdict | Severity |
|---------|--------------|---------|----------|
| §1 | Goal & scope (descriptive framing) | CONFIRMED | — |
| §2 | Harness properties (singleton, stateful, localhost) | CONFIRMED | — |
| §2 | "One specific forge write: `role:*` label" | CONFIRMED | — |
| §3 | Process model, threading, shutdown | CONFIRMED | — |
| §4.1 | Lifecycle endpoints exist in code | CONFIRMED | — |
| §4.1 | Response shapes (aspirational post-#10358) | DRIFT | medium |
| §4.2 | Event bus endpoints exist in code | CONFIRMED | — |
| §4.2 | `POST /events/{event_id}/complete` "does not exist" | DRIFT | high |
| §4.2 | Path parameters use `{alias}` in doc, `{role}` in code | DRIFT | low |
| §4.3 | `POST /work/assign` exists | DRIFT | high |
| §4.4 | `/queue/{alias}` generalized endpoint | GAP | low |
| §5 | ELM: deque, cursors, in-flight, tasks | CONFIRMED | — |
| §5.3 | Event ID format (#9415) | CONFIRMED (shipped v0.42.0) | — |
| §6 | EAD: polling, cadence, restart safety | CONFIRMED | — |
| §7 | Agent lifecycle, intent/status machines | CONFIRMED | — |
| §7.2 | Spawn sequence, first-boot discovery | CONFIRMED | — |
| §7.5 | `.harness-state.json` shape | CONFIRMED | — |
| §8 | Port discovery, clone isolation | CONFIRMED | — |
| §9 | State files summary | CONFIRMED | — |
| §9 | Vocabulary note: `role` vs `alias` mismatch | DRIFT (code, not doc) | — |
| §10 | Restart safety sequence | CONFIRMED | — |
| §11 | Failure modes | CONFIRMED | — |
| §12 | Cross-references | CONFIRMED | — |
| §13.1 | No deque persistence | GAP | low |
| §13.2 | No API authentication | GAP | low |
| §13.3 | No multi-host support | GAP | low |
| §13.4 | EAD forge-specific | GAP | low |
| §13.5 | #10182 permission table removal | GAP (not in manifest) | medium |
| §13.5 | #10182 gate "PR #10004 merge" | STALE | medium |
| §13.6 | `/queue/{alias}` generalization | GAP (not in manifest) | low |
| §14 | Proposed `wt→claude` simplification | STALE (not tracked) | low |
| §14.3 | #8692, #10101 referenced as deletable | STALE (not tracked) | low |
| — | `POST /merge` exists in code, not in doc | DRIFT | medium |
| — | #10358 `role`→`alias` rename | GAP (not in manifest) | medium |
| §4.1 | `/shutdown` aspirational scope ambiguity | DRIFT | low |

### Verdict Counts

| Verdict | Count |
|---------|-------|
| CONFIRMED | 16 |
| DRIFT | 8 |
| GAP | 9 |
| STALE | 3 |
| IN PROGRESS | 0 |
| HELD | 0 |

### Critical Items (High Severity)

1. **Finding 1**: `POST /events/{event_id}/complete` exists in code but doc says "no completion endpoint" — code/doc contradiction on a locked architectural principle.
2. **Finding 2**: `POST /work/assign` is documented but not implemented — this is the backbone of the target routing architecture described in both HARNESS-ARCH.md and AGENT-RUNTIME.md.
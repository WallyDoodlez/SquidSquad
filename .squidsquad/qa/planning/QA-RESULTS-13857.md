# QA-RESULTS-13857 (round 1)

**Verdict: FAIL → back to in-progress**

## TC Results

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 | PASS | Live, non-mocked: deployed the packaged engine (`wizard.install_vault_engine()`, real function call) into an isolated scratch install, seeded one real vault note, ran `node .claude/skills/vault-search/scripts/vault-query.mjs --instance-id test-instance-ac1 --alias qa --task 13857 --vault .squidsquad/vault --entities auth --tags testing --top 5` exactly per SKILL.md's documented invocation. Output matches the documented top-K JSON shape (`query`/`results`/`traversed`/`written`) exactly; telemetry shard genuinely written to disk with the correct `{id,ts,agent,task,slug,counter}` schema. |
| TC2 | AC2 (installer) | PASS | Genuinely stripped `node`/`node.exe` from `PATH` (not `unittest.mock.patch` — real `os.environ['PATH']` surgery) and called the real `wizard.install_vault_engine()`: `{'deployed': ['vault-search'], 'node': None, 'degraded': True, 'telemetry_seeded': True}` — install not blocked, skills still deployed. |
| TC3 | AC2 (query) | PASS | With `node` genuinely absent from `PATH`, invoking `vault-query.mjs` directly fails with a clean shell "command not found" (exit 127) — an unambiguous, agent-detectable signal, not a hang or opaque error, supporting the honest-degradation behavior SKILL.md's prose instructs. |
| **TC4** | **AC3** | **FAIL** | See "AC3 finding" below. |
| TC5 | AC4 | PASS | Live: `vault-query.mjs ... --no-write` against the same real scratch vault returns `"written": {"events": 0, "shard": null, "skipped": true}`, and the `.telemetry/` directory has zero new `.jsonl` content after the call. |
| TC6 | AC5 | NOT YET DONE | Deferred to the re-verification round — see note below. |
| TC7 | — | PASS | `test_vault_engine_13857.py` + `test_vault_engine_boundary_13857.py` + `test_vault_engine_installer_13857.py` + `test_config_functions.py`: 135/135. |
| TC8 | — | not run | Not meaningful to run the full ship gate against a branch that's failing its own AC — deferred to the re-verification round. |

## AC3 finding (blocking)

**`test_vault_engine_boundary_13857.py`'s grep-audit ratchet only scans `references/sub-skills/` and `references/roles/` (`INSTRUCTION_ROOTS`). Two live, agent-reachable instruction sources outside that scope still teach the banned raw-grep vault-search pattern and are invisible to the audit:**

1. **`references/docs/vault-reference.md`** — titled "Vault Reference — Detailed Operations", section "Searching the Vault (vault-search)" states *"vault-search finds notes by tag, type, keyword, or wikilink traversal. It uses grep internally."* and gives 4 literal `grep -rl ... .squidsquad/vault/` commands as the sanctioned search modes — the exact v1 mechanism the engine boundary replaces. Confirmed live: shipped to every install (`references/installer-files.txt`) AND directly referenced from the live `references/sub-skills/common/vault-protocol.md` ("See `references/docs/vault-reference.md` for full search examples" — vault-protocol.md's OWN allowlisted grep sites point readers at this exact file for more detail).
2. **`references/prompts/research.md.j2`** — a Jinja2 template confirmed rendered by `references/scripts/model_router.py` into real research-task prompts sent to agents. Its "Consult the vault first" step instructs: `Search the vault for related notes: \`grep -rl "<keywords from task>" .squidsquad/vault/ --include="*.md"\`` — again the banned raw-grep pattern, in a live prompt path outside the audit's scope.

Independently re-derived the full set (POSIX-ERE-compatible regex, not the Python test's `(?:...)` syntax which plain shell `grep -E` doesn't support — first attempt at manual re-derivation silently under-counted for this reason, caught and corrected): exactly 7 files under `references/` contain raw vault-grep snippets — the 5 already frozen in `V1_ALLOWLIST` plus these 2 new ones.

**Why this blocks AC3**: AC3's own text is "grep-audit: vault sub-skills/scripts reach search only through the engine" — an audit that doesn't scan two real, live violation sites doesn't establish the claim, independent of whether those two sites would ultimately be judged P4-deferred (like the 5 allowlisted ones) or fixed now. Nobody has made that call for these two — they're simply missing from the audit's field of view.

**Suggested fix (either is fine)**: extend `INSTRUCTION_ROOTS` to also cover `references/docs/` and `references/prompts/` and add both files to `V1_ALLOWLIST` with their current line counts (mirroring the existing 5, if P4-deferred is the right call for these too — `vault-reference.md` in particular reads like it should probably be rewritten/retired now since it actively contradicts the new engine boundary, not just deferred); or fix the two files directly in this PR.

## AC5 (comprehension coverage) — deferred, not evaluated this round

Per house rule the verifier authors the CQ spec for `references/skills/vault-search/SKILL.md` once the artifact is in its final, review-passed shape. Holding off until the AC3 fix lands (unlikely to touch SKILL.md, but a re-verification round is coming regardless) rather than authoring a spec now that might need a baseline refresh next round — see [[learning-comprehension-staleness-refresh-is-pr-authorship-not-verifier-bookkeeping]].

## Conclusion

AC1/AC2/AC4 pass with live, non-mocked evidence. AC3's audit has a real, evidenced completeness gap (2 missed live violation sites). Zero-gap gate: back to in-progress. AC5 CQ-spec authoring resumes on re-verification.

I've now completed a thorough review of the changed file. Let me compile my findings.

---

### Finding 1

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 914 vs 958
- **Severity**: warning
- **Issue**: §8.1 states "mixed modes are not supported" (line 914), but §8.3 explicitly describes a scenario where mixed modes occur: when `event-driven: yes` but the harness is unreachable at boot, "the affected agent falls back to loop mode [...] while other agents in the same install may still enter event mode if their harness probe succeeds" (line 958). This is a de facto mixed-mode state — some agents in loop mode, others in event-driven mode.
- **Evidence**: The two statements directly contradict. §8.1 says the whole squad runs in one mode together; §8.3 says individual agents can diverge based on independent harness probes. The global-only mode flag design intent (rev 6) was to eliminate per-role mode selection, yet the fallback behavior reintroduces per-agent mode divergence at runtime.
- **Suggested fix**: Either (a) clarify §8.1 to say "mixed modes are not _configurable_ — the `event-driven:` flag is global — but degraded per-agent fallback can produce a transient mixed-mode state when the harness is partially unreachable"; or (b) change the fallback model to be install-wide: if _any_ agent's probe fails, all agents fall back to loop mode. Option (a) is simpler and preserves independent probe resilience.

---

### Finding 2

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 964
- **Severity**: warning
- **Issue**: §8.4 says "the agent falls back to loop mode [...] regardless of its `event-driven:` config." The phrase "regardless of its `event-driven:` config" is misleading because when `event-driven: no` the agent is already in loop mode — the fallback path is only relevant when `event-driven: yes`. The wording implies the config value is irrelevant to the outcome in all cases, which is false.
- **Evidence**: The boot decision tree (§8.3, line 934–956) shows two distinct paths: `event-driven: no` → always loop mode (not a "fallback"), `event-driven: yes` + probe fail → loop mode (actual fallback). The "regardless" phrasing collapses these two semantically different paths.
- **Suggested fix**: Rewrite line 964 to: "When the harness is unreachable at boot (probe fails per `common/boot-bootstrap` Step 2) and `event-driven:` is `yes`, the agent falls back to loop mode (`/loop 30m`)."

---

### Finding 3

- **File**: docs/AGENT-RUNTIME.md
- **Line**: 34, 918, 925, 1036, 1037
- **Severity**: info
- **Issue**: The term "sub-skill" appears in 5 places (not counting the rev log). The rev 6 description on line 1056 claims `no "skill"` was left behind, and indeed bare `skill` does not appear. However, "sub-skill" is arguably the same root term. The doc references `sub-skill-catalog.md`, `sub-skill-guide.md`, "sub-skill manifest", and "sub-skill set" as if these are the canonical names for composition fragments.
- **Evidence**: The grep for `\bskill\b` matches only "sub-skill" compounds and the rev log. If the terminology unification intended to purge "skill" in all forms, these remain. If "sub-skill" is the project's established composition-architecture term (distinct from the concrete-instance "skill" term that was removed), then this is not a finding.
- **Suggested fix**: If "sub-skill" _is_ the intended composition term: no change needed — close as intentional. If it was also supposed to be replaced: rename to match whatever the new term is (e.g., "fragment", "module", "include").

---

**Summary**: One MED contradiction (§8.1 vs §8.3 mixed-mode semantics), one LOW clarity issue (§8.4 "regardless" phrasing), and one borderline call on "sub-skill" terminology. The core terminology unification (verifier→qa, verifier-rejected→qa-rejected, no per-role event-driven flags) appears complete and consistent. No wire-format inconsistencies were found — `qa-rejected` is correctly used in the routing table (line 785), `verification-needed` is an activity description not a role name, and deprecated types like `verification-passed`/`verification-failed` are properly contextualized as pre-v2/loop-mode artifacts with clear migration notes.
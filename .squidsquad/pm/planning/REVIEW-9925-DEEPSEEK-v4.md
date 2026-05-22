Now I have a complete picture. Let me compile the findings.

---

### Finding 1

- **File**: `.squidsquad/pm/planning/CONTEXT-9925.md`
- **Line**: D7 (lines 162–189), esp. items 1–2 (lines 166–168)
- **Severity**: error
- **Issue**: D7 specifies adding `common/agent-boundaries` and `roles/<role>/responsibility` to each role's `includes.yml` and `includes-events.yml` manifest, but never specifies adding the corresponding `{{include: common/agent-boundaries}}` and `{{include: roles/<role>/responsibility}}` directives to each role's `instructions.md` template. Per compose.py:293–327 (`_resolve_includes_with_manifest`), an include is only triggered when BOTH a `{{include: path}}` directive appears in the template AND the path is present in the manifest. If the `{{include:}}` directive is absent, the manifest entry has no effect — the include is never invoked. This is a recurrence of DS F1 (compose wiring missing), which the resolution map claims D7 + AC2 + AC3 resolves — but D7 only covers the manifest half of the wiring.
- **Evidence**: The existing pattern in `references/roles/pm/instructions.md` lines 27–153 shows each include in the manifest has a corresponding `{{include: path}}` directive. `_resolve_includes_with_manifest` at line 293 matches `{{include:}}` directives; line 313 checks the manifest; line 324 skips directives not in the manifest. Without the directive, the resolver never reaches the manifest check.
- **Suggested fix**: Add to D7 items 1 and 2 (or a new item 4): "Each role's `references/roles/<role>/instructions.md` gains a `{{include: common/agent-boundaries}}` directive AND a `{{include: roles/<role>/responsibility}}` directive at the position where that content should appear in the composed output." Alternatively, place `{{include: common/agent-boundaries}}` in the base `references/roles/instructions.md` (Layer 1 of `_assemble_claude`) since D3 requires identical L1 content for all roles.

---

### Finding 2

- **File**: `.squidsquad/pm/planning/CONTEXT-9925.md`
- **Line**: D8 (line 192) vs D2 (lines 46–49)
- **Severity**: warning
- **Issue**: D8 says "Role roster is sorted alphabetically by manifest `id`." But D2 only specifies that `compose.py` extracts `display_name`, `tagline`, and `description` from each manifest. The `id` field is not listed in D2's extraction spec. An implementer reading only D2 would not know to extract `id` for D8's sorting requirement. While `id` does exist in every manifest (e.g., `references/roles/pm/manifest.yaml` line 13: `id: pm`), the locked decisions are internally inconsistent.
- **Evidence**: D2 line 46–49 lists three extracted fields; `id` is absent. D8 line 192 references "manifest `id`" as the sort key. The manifest files (e.g., pm/manifest.yaml line 13) contain `id` but D2 doesn't declare it as extracted.
- **Suggested fix**: Add `id` to D2's list of extracted fields: "Extract `id`, `display_name`, `tagline`, `description` from each." Or change D8's sort key to `display_name` if alphabetical by display name is acceptable.

---

### Finding 3

- **File**: `.squidsquad/pm/planning/CONTEXT-9925.md`
- **Line**: AC10 (line 228) — interaction with compose.py:920 (`agent_compose`)
- **Severity**: warning
- **Issue**: AC10 requires byte-identical output from two `compose.py deploy pm` runs with no source changes. However, `deploy_role` at compose.py:920 calls `agent_compose()` which, when enabled via `config.md` (`agent-compose: yes`), sends the composed content through an LLM coherence polish (compose.py:806–890). LLM output is inherently non-deterministic, so two runs would likely produce different output, violating AC10. Neither D8 nor AC10 mentions this dependency. AC12(g) says the test covers AC10 but doesn't explain how it handles the `agent_compose` variable.
- **Evidence**: compose.py:817 — `if not _is_agent_compose_enabled(): return deterministic_output`. compose.py:843–850 — calls `claude -p` for LLM polish. compose.py:885 — returns polished (non-deterministic) output on success. If `config.md` has `agent-compose: yes`, two compose runs would pass through the LLM and produce different results.
- **Suggested fix**: Either: (a) add a note to AC10 that the byte-identical test must disable `agent_compose` (or run in an environment where it's not enabled), or (b) add a flag to `compose.py deploy` to skip agent_compose for testing, or (c) note in D8 that byte-identical stability is only guaranteed when `agent_compose` is disabled.

---

### Finding 4

- **File**: `.squidsquad/pm/planning/CONTEXT-9925.md`
- **Line**: AC4 (line 211) vs D7 (line 171)
- **Severity**: warning
- **Issue**: AC4 requires "At least one rendered teammate entry per OTHER active role from `config.md`." But D7 says compose should "Discover all role manifests at `references/roles/*/manifest.yaml`" — producing a roster of ALL roles that have manifests, not just those active in `config.md`. These can differ: a manifest could exist for a role not configured in `config.md` (e.g., QA manifest exists but QA isn't installed). The implementer must choose between two different sources of truth for roster population. AC4 sets a floor ("at least config.md roles") but doesn't clarify whether non-active roles SHOULD or SHOULD NOT appear. A QA reviewer checking against AC4 would only verify active roles, potentially missing that non-active roles also appear.
- **Evidence**: D7 line 171: "Discover all role manifests at `references/roles/*/manifest.yaml`." AC4 line 211: "per OTHER active role from `config.md`." `config.md` may list a subset (e.g., only dev-skill) while manifests exist for all four base roles (pm, qa, dm, dev).
- **Suggested fix**: Align AC4 with D7: either (a) change AC4 to expect entries for ALL roles with manifests (not just config.md active ones), or (b) change D7 to filter roster to only roles active in `config.md`, and state that explicitly.

---

### Finding 5

- **File**: `.squidsquad/pm/planning/CONTEXT-9925.md`
- **Line**: D6b (lines 130–134)
- **Severity**: warning
- **Issue**: D6b describes three L4 filename-prefix routing cases: `<role-identity>-*.md` (matching role only), `shared-*.md` (all roles), and unprefixed `*.md` (all roles). But compose.py:404–410 also handles a fourth case: files whose prefix is NOT a known role identity (e.g., `setup-upgrade-gate.md` with prefix `setup`) are included for ALL roles. This undocumented case could mislead someone who creates a file like `my-custom-responsibility.md` expecting it to be excluded from non-matching roles, when in fact it would be included everywhere. The L4 stubs in this task all use known prefixes, so the gap doesn't affect the immediate deliverable, but the spec is the authoritative contract for future L4 usage.
- **Evidence**: compose.py:404–410: the condition `if file_prefix and file_prefix != "shared" and file_prefix in known_prefixes:` means a file like `setup-upgrade-gate.md` (prefix `setup` not in `known_prefixes` = `{dev, dm, pm, qa}`) falls through to inclusion for all roles. D6b lines 132–134 list three cases without mentioning this fourth.
- **Suggested fix**: Add a fourth bullet to D6b: "`<unknown-prefix>-*.md` where the prefix is not a known role identity — included for all roles (treated like unprefixed)."

---

### Finding 6

- **File**: `.squidsquad/pm/planning/CONTEXT-9925.md`
- **Line**: D7 item 3 (lines 170–174)
- **Severity**: warning
- **Issue**: D7 says to "Replace the `{{role-roster}}` marker in the inlined L1 `agent-boundaries.md` content" but does not specify WHERE in the compose pipeline this replacement occurs. The `_resolve_includes_with_manifest` function (compose.py:273–356) handles `{{include:}}`, `{{runtime:}}`, and `{{capability:}}` directives but has no `{{role-roster}}` handling. The implementer must choose: (a) post-process after `_resolve_includes_with_manifest` returns, (b) add a new directive type to `_resolve_includes_with_manifest`, or (c) substitute during `_assemble_claude` before include resolution. Each choice has different implications for where the roster appears relative to other content and whether the marker could appear in other contexts by accident. The spec should constrain this.
- **Evidence**: compose.py:293–296 matches three directive types; `{{role-roster}}` is not among them. D7 line 174 says "Replace the `{{role-roster}}` marker" but gives no pipeline stage. Without specification, two implementers could produce different internal architectures that both pass AC4 but behave differently under edge cases (e.g., if `{{role-roster}}` appears inside a code block in another file).
- **Suggested fix**: Specify the pipeline stage: e.g., "After `_resolve_includes_with_manifest` returns the fully-resolved content, scan for `{{role-roster}}` and replace it with the rendered roster block." Or: "Inside `_resolve_includes_with_manifest`, after inlining `agent-boundaries.md` content, perform the replacement on that content before appending it to output."
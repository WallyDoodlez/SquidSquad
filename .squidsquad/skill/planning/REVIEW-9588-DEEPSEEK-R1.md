Now I have a thorough understanding of the implementation. Let me compile my findings.

---

### Finding 1

- **File**: `references/scripts/compose.py`
- **Line**: 303–318
- **Severity**: HIGH
- **Issue**: The mechanism that skips mode-specific fragments (because they're absent from the manifest) relies on fragile variant-name matching. The code extracts a `base` name from the include path (line 307) and checks if any manifest entry's stem `startswith(base + "-")` (line 311). Because the mode-specific fragment `common-events/l1-base` has base `l1-base`, any future manifest entry whose stem starts with `l1-base-` (e.g., `common/l1-base-extended`) would match and cause `common-events/l1-base` to be silently re-inlined — defeating the lazy-load design.
- **Evidence**: 
  - Line 307: `base = include_path.rsplit("/", 1)[-1] if "/" in include_path else include_path`
  - Line 311: `if m_base.startswith(base + "-") or base.startswith(m_base + "-"):`
  - For `include_path = "common-events/l1-base"`, `base = "l1-base"`. A manifest entry `common/l1-base-extended` has `m_base = "l1-base-extended"`, and `"l1-base-extended".startswith("l1-base-")` is `True` → the variant match succeeds, `found = True`, and compose silently inlines the mode-specific fragment.
  - Same risk applies to all 8 removed mode-specific fragments (`ralph-loop-overview`, `event-driven-workflow`, `cursor-management`, `forge-read-pattern`, `idle-cooldown-loop`, `comment-handling`, `pr-merge-wait`).
- **Suggested fix**: Add an explicit exclusion set for runtime-Read fragments and check it before the variant-matching fallback. E.g., at line 304, after checking `include_path not in manifest_set`, check a `RUNTIME_READ_FRAGMENTS` set and `continue` if matched. Alternatively, check the skip BEFORE the variant-name resolution so the variant heuristic can't accidentally resurrect a deliberately-skipped include.

---

### Finding 2

- **File**: `references/roles/pm/instructions.md`, `references/roles/dm/instructions.md`, `references/roles/qa/instructions.md`, `references/roles/dev/instructions.md`
- **Line**: pm:29,33,35,37,39,41,43; dm:31,35,37,39,41,43,45,67; qa:29,33,35,37,39,41,43; dev:23,27,29,31,33,35,37
- **Severity**: MEDIUM
- **Issue**: All four `instructions.md` templates still contain `{{include:}}` directives for mode-specific fragments that are deliberately skipped at compose time (because the corresponding entries were removed from both `includes.yml` and `includes-events.yml` manifests). This creates a divergence between template and manifest that is a maintenance hazard: a future editor may see the template directive, think the manifest entry was accidentally dropped, reinstate it, and silently break the lazy-load design.
- **Evidence**:
  - `pm/instructions.md:29` — `{{include: roles/pm/ralph-loop-overview}}` (absent from both pm manifests)
  - `pm/instructions.md:33-43` — all six `{{include: common-events/...}}` directives (absent from both pm manifests)
  - Same pattern in dm, qa, dev instructions.md files
  - `dm/instructions.md:67` — `{{include: roles/dm/events/pr-merge-wait}}` (absent from both dm manifests)
  - The D7 regression test (`test_compose_9588.py:96-104`) guards against accidental re-inlining, but the template/manifest divergence is a latent trap.
- **Suggested fix**: Either (a) remove the `{{include:}}` directives from `instructions.md` and add a comment block listing which fragments are Read at runtime (the approach the manifests use), or (b) document at each directive site in the template that the fragment is lazy-loaded by the bootstrap and the manifest intentionally omits it.

---

### Finding 3

- **File**: `references/sub-skills/common/boot-bootstrap.md`
- **Line**: 8–12
- **Severity**: MEDIUM
- **Issue**: The bootstrap fragment instructs the agent to "Read `.squidsquad/config.md` and find the active wake mode" but does not specify behavior when `config.md` itself is **absent** (file doesn't exist). The enumerated branches cover field values (`yes`, `no`, absent, unparseable) but not the missing-file scenario. An agent encountering a missing `config.md` could error on the Read attempt rather than defaulting safely to polling mode.
- **Evidence**:
  - Lines 8–12: "Read `.squidsquad/config.md` and find the active wake mode:" followed by three bullet conditions, all of which assume the file was read successfully. No instruction for "if the file does not exist or cannot be read."
  - The compose-time `_get_wake_mode` function (`compose.py:34-67`) handles SystemExit/BaseException from missing config gracefully and returns `"polling"`. The runtime bootstrap should match this defensive posture.
  - Per CONTEXT D3, the fallback for any uncertainty is polling mode.
- **Suggested fix**: Add a guard before the field-value bullets: "If `.squidsquad/config.md` does not exist or cannot be read → **POLLING mode confirmed**, skip Step 2 and jump to Step 4 (polling branch)."

---

### Finding 4

- **File**: `references/sub-skills/common/boot-bootstrap.md`
- **Line**: 21
- **Severity**: LOW
- **Issue**: The curl probe command `curl -sf --max-time 5 http://127.0.0.1:<port>/ > /dev/null` uses a shell redirect to `/dev/null`, which does not exist on native Windows shells (cmd.exe, PowerShell). While most agents in this project operate in bash-compatible environments (Git Bash, WSL), a native Windows execution would cause the redirect to fail (or create a literal file named `dev/null`), making the curl pipeline return non-zero and forcing a permanent polling fallback even when the harness is reachable on the default port 7373.
- **Evidence**:
  - Line 21: `curl -sf --max-time 5 http://127.0.0.1:<port>/ > /dev/null`
  - `> /dev/null` is a shell redirect that only works in POSIX shells. This is the only use of `/dev/null` in any sub-skill `.md` file (grep confirmed zero hits across `references/sub-skills/**/*.md` outside this file).
  - Per CONTEXT D3: "ALWAYS Read polling fragment when harness is unreachable" — this would be incorrectly triggered on native Windows.
- **Suggested fix**: Replace `> /dev/null` with curl's built-in output suppression: `curl -sf --max-time 5 -o /dev/null http://127.0.0.1:<port>/status`. Note the `/status` path is also missing from the current curl command (the CONTEXT locked text uses `/status` but the current implementation uses `/`). Aligning the endpoint with the CONTEXT (`/status`) is also advisable. Alternatively, use `curl -sf --max-time 5 --output NUL http://...` and provide both variants, or note the platform assumption.
I'll review `references/scripts/config.py` systematically, tracing data flow through the parser, writer, and agent resolution paths.

### Finding 1

- **File**: references/scripts/config.py
- **Line**: 159–169
- **Severity**: error
- **Issue**: `get_alias()` only resolves aliases for the five hardcoded roles in `FIELD_MAP` (`skill`, `pm`, `dm`, `designer`, `qa`). For any dev role (e.g., `fe`, `be`, or custom roles), it silently returns the bare role name, even when the `## Aliases` section contains an explicit alias like `- **fe**: Frontend`.
- **Evidence**: `get_alias` looks up `f"alias-{role}"` in `FIELD_MAP` (line 163). If the key is absent, it returns `role` at line 169 without ever trying to parse the Aliases section for that role. Meanwhile, `_parse_agents_v1` (line 249) correctly calls `_parse_field_in_text(aliases_text, role)` for every role. Callers that use `get_alias` (e.g., the `alias` CLI subcommand, line 353) get wrong results for dev agents, which can break test-routing decisions that depend on correct alias resolution.
- **Suggested fix**: Add a fallback lookup in the Aliases section before returning the bare role name:

```python
    # Fallback: try the Aliases section directly
    val = _parse_field(text, "Aliases", role)
    if val:
        return val
    return role
```

### Finding 2

- **File**: references/scripts/config.py
- **Line**: 119–139 (`set_field`)
- **Severity**: warning
- **Issue**: `set_field` reconstructs section text via `_parse_sections`, which uses `str.splitlines()` (handles `\r\n`, `\n`, `\r`) but always joins lines back with `\n`. The result is then located in the original file text using `text.replace(section_text, new_section, 1)` at line 131. If the config.md file uses CRLF line endings (e.g., on Windows), `section_text` contains only LF, `text` contains CRLF, and `str.replace` silently fails to match — causing the write to be a no-op without any error.
- **Evidence**: `_parse_sections` (line 92) appends `"\n"` on line 100 regardless of the original line endings. `set_field` relies on exact substring matching at line 131. The same pattern also affects the `else` (non-section) branch at line 135–139, though there `re.sub` operates directly on `text` so the regex match will succeed; the problem is specific to the section-aware branch using `str.replace`.
- **Suggested fix**: Normalize the file to LF on read, or use regex-based section replacement (similar to `write_event_reactions`) instead of `str.replace`.

### Finding 3

- **File**: references/scripts/config.py
- **Line**: 293–305 (`_parse_agents_v2` setup block)
- **Severity**: warning
- **Issue**: The setup sub-block parser closes the setup scope (`in_setup = False`) on **any** line that doesn't match `_SETUP_FIELD_RE` (line 303–304). A blank line between setup fields will prematurely terminate the setup block, causing subsequent setup keys to be misinterpreted as top-level agent fields.
- **Evidence**: Given this valid markdown:
  ```
  - **qa**: QA
    - role: qa
    - setup:
      - script: ./setup.sh

      - env: FOO=bar
    - test_command: pytest
  ```
  The blank line at line 5 resets `in_setup = False` (line 304 falls through). Line 6 `    - env: FOO=bar` then fails the `_SETUP_FIELD_RE` check (since `in_setup` is now `False`) and falls to the `_NESTED_FIELD_RE` check at line 308, which doesn't match 4-space indentation. The `env` key is silently dropped rather than added to `current["setup"]`.
- **Suggested fix**: Skip blank lines without closing the setup block. Change the "anything else closes" logic at line 303–304 to:

```python
            if line.strip() == "":
                continue
            in_setup = False
```

### Finding 4

- **File**: references/scripts/config.py
- **Line**: 182–198 (`main` → `sync-agents`)
- **Severity**: warning
- **Issue**: `sync_agents` unconditionally calls `set_field("dev-agents", ...)` without checking the schema version. On a v2 config, this will error out (because v2 has no `- **Dev Agents**: ...` line), but the error message is `"Field 'dev-agents' not found in section 'Agents'"` — misleading because the real problem is a schema mismatch, not a missing field.
- **Evidence**: `sync_agents` (line 180) is callable via `config.py sync-agents` (line 358). On v2 configs, the Agents section uses per-agent entries (e.g., `- **fe**: alias`) instead of the v1 flat `- **Dev Agents**: fe, be` line. `set_field` will fail at line 129 with a confusing error rather than telling the user that `sync-agents` doesn't support v2.
- **Suggested fix**: Guard with a schema version check:

```python
def sync_agents():
    if detect_schema_version() == 2:
        print("ERROR: sync-agents is not supported for v2 config.md", file=sys.stderr)
        sys.exit(1)
    ...
```
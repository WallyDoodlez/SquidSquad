# Research: #5 — Add agent role command

**Date**: 2026-04-11
**Status**: Complete
**Issue**: #5 — Add agent role command: clone, configure, and boot any role from PM

---

## 1. Current State

### How cross-clone paths work today

- Each agent runs in its own full `git clone` (separate working directory to avoid file collisions)
- `.squidsquad/.active-role` — single line, e.g. `pm`. Written by the start script at boot. Gitignored.
- `.squidsquad/.local-config` — maps roles to absolute clone paths. Gitignored. Format:

```
# Local Config — cross-clone paths for agent health checks
# These paths are machine-specific and should NOT be committed.

- **skill**: D:\Dev\Dev\SquidSquad-2
- **dm**: D:\Dev\Dev\SquidSquad-3
```

- `health_check.py` reads `.local-config` to find each agent's clone, then probes `<clone>/.squidsquad/<role>/current-state` mtime
- `boot_remote.py` reads the health check output, finds the `clone_path` for each agent, locates `start-<role>.[sh|ps1]` in that clone, and spawns a terminal
- The PM clone (this repo root) is implicitly "self" — not listed in `.local-config` (health_check only checks entries in the file)

### What's manual today (the pain)

1. Human runs `git clone` N times to create sibling directories
2. Human edits `.local-config` in the PM clone with absolute paths
3. Human must also create `.local-config` in EACH other clone pointing back to the others (for cross-health-check)
4. Human starts each agent via `start-<role>.ps1` in the correct clone
5. If a new role is added later, ALL clones need their `.local-config` updated

### Gitignore coverage

All runtime files are properly gitignored:
- `.squidsquad/.active-role`
- `.squidsquad/.local-config`
- `.squidsquad/*/current-state`
- `.squidsquad/*/.pid`
- `.squidsquad/*/.stop`

---

## 2. What exists for #5

### Issue body

> Migrated from FEAT-SKILL-052. Slash command + PM sub-skill to add any role.

### Existing scripts in `references/scripts/`

| Script | Relevant? | Notes |
|---|---|---|
| `boot_remote.py` | Yes | Already spawns terminals; needs clone_path from health report |
| `health_check.py` | Yes | Reads `.local-config` to find clones |
| `compose.py` | Yes | `boot_role()` generates start scripts from templates; `boot_all()` iterates configured roles |
| `wizard.py` | Partial | `scaffold_install()` writes full `.squidsquad/` tree but does NOT handle cloning or `.local-config` |
| `config.py` | Peripheral | Reads/writes config.md values, agent aliases |

### Boot script generation

`compose.py boot <role>` generates `start-<role>.sh` and `start-<role>.ps1` from `references/templates/start-role.sh` and `start-role.ps1`. These templates use `{{ROLE}}` substitution. The generated scripts:
1. Write `.active-role`
2. Inject permissions
3. Run `config.py sync-agents`
4. Enter a PID-locked auto-restart loop calling `claude --dangerously-skip-permissions`

---

## 3. Implementation Approach

### Recommendation: New script `references/scripts/add_role.py`

**Why not extend wizard.py**: The wizard handles initial project setup (gh checks, intent classification, scaffold). Adding a role to an existing installation is a post-setup operation with different prerequisites (repo already exists, config.md already populated). Mixing concerns would complicate wizard re-run detection.

**Why not extend compose.py**: Compose handles content generation (Markdown composition, boot script templating). Cloning repos and updating configs across filesystems is infrastructure work, not composition.

### Proposed command interface

```
python references/scripts/add_role.py <role> [--target <path>] [--boot] [--dry-run] [--json]
```

- `<role>`: required, e.g. `skill`, `qa`, `designer`
- `--target <path>`: optional, defaults to `<parent>/<project>-N` (auto-numbered sibling)
- `--boot`: after cloning, immediately start the agent via `boot_remote.py --role <role>`
- `--dry-run`: print what would happen
- `--json`: machine-readable output

### Steps the script performs

1. **Validate**: role is known in config.md `Dev Agents` or is `pm`/`dm`/`qa`
2. **Determine target path**: if not specified, find next available `<ProjectName>-N` sibling
3. **Clone**: `git clone <origin-url> <target-path>` (full clone, see Section 4)
4. **Set active role**: write `<role>` to `<target>/.squidsquad/.active-role`
5. **Generate boot scripts**: run `python references/scripts/compose.py boot <role>` inside the new clone
6. **Update `.local-config` in ALL clones**:
   - Read current `.local-config` from source clone
   - Add the new role+path entry
   - Write updated config to source clone AND all other clones listed in config
   - Also write to the new clone itself
7. **Optionally boot**: if `--boot`, call `boot_remote.py --role <role>`

---

## 4. Git worktree vs git clone

### Git worktree

**Pros:**
- Lighter: shares `.git` directory, no duplicate object store
- Faster creation (near-instant vs clone over network)
- All worktrees share refs, so `git pull` in one updates all
- Disk-efficient for large repos

**Cons:**
- **Shared index/staging**: `git status`, `git add`, `git commit` in one worktree can interfere with another if both modify tracked files simultaneously. This is the #1 concern for SquidSquad where multiple agents commit concurrently.
- **Branch restriction**: each worktree must be on a different branch OR detached HEAD. All SquidSquad agents currently work on `main`. Worktrees would force each agent onto a separate branch, adding merge complexity.
- **Lock files**: git uses lock files per-worktree but shared pack files. Concurrent gc/repack can cause issues.
- **Windows support**: `git worktree` works on Windows but has had historical edge cases with long paths and symlinks.

### Git clone

**Pros:**
- Full isolation: each clone has its own `.git`, index, refs, remotes
- Agents can all be on `main` without conflicts
- No shared locks or state
- Simpler mental model

**Cons:**
- Full disk usage per clone
- Network round-trip for initial clone (mitigable with `--reference` or `--local`)
- `git pull` needed independently in each clone

### Recommendation: **git clone** with `--local` optimization

```
git clone --local /path/to/source /path/to/target
```

`--local` uses hardlinks for objects when cloning from a local path, making it nearly as fast and disk-efficient as worktree while maintaining full isolation. This is critical because:
- Multiple agents commit to `main` concurrently — they need separate indexes
- The `git pull --rebase` protocol (config.md) works naturally per-clone
- No branch gymnastics needed

For network-only scenarios (fresh install), fall back to regular `git clone <remote-url>`.

---

## 5. Cross-clone `.local-config` sync

### The problem

When a new clone is added, every existing clone needs its `.local-config` updated to include the new agent's path. Otherwise health checks and boot_remote won't see the new agent.

### Approach: Source-of-truth in the adding clone, broadcast to all

```python
def sync_local_configs(all_clones: dict[str, Path]):
    """Write identical .local-config to every clone.

    all_clones: {role: absolute_path} including self
    """
    config_text = render_local_config(all_clones)
    for role, clone_path in all_clones.items():
        target = clone_path / ".squidsquad" / ".local-config"
        target.write_text(config_text, encoding="utf-8")
```

### Edge cases

- **Clone path doesn't exist yet**: skip (clone hasn't been created). The script should clone first, then sync.
- **Clone path exists but `.squidsquad/` missing**: error — not a valid SquidSquad clone
- **Permission errors**: log warning, continue with other clones
- **Stale entries**: if a listed clone no longer exists on disk, leave the entry (health_check already handles "clone path does not exist" gracefully). Optionally add a `--prune` flag.

### PM clone self-reference

Currently the PM clone is NOT in `.local-config`. The add_role script should add the PM clone as well, since health_check benefits from having all agents listed. The PM clone path can be inferred as `REPO_ROOT` from where the script runs.

---

## 6. Integration with setup wizard

### Should the wizard auto-create clones?

**No, not during initial setup.** Reasons:
- The wizard runs once to scaffold `.squidsquad/` in a single repo. Clone creation is an operational step that happens after config is committed.
- The wizard doesn't know how many clones the user wants (they might add roles incrementally).
- Cloning requires the repo to be committed+pushed first (so there's a remote to clone from, or at least a local source).

### Post-setup flow

The natural sequence is:
1. `wizard.py scaffold` creates the project config in one clone
2. User commits and pushes
3. `add_role.py skill` clones and configures the skill agent
4. `add_role.py dm` clones and configures the DM agent (if wanted)
5. Each `add_role.py` call updates `.local-config` everywhere

### Wizard could offer a hint

At the end of the wizard scaffold step, print:

```
Next: add agent roles with:
  python references/scripts/add_role.py skill --boot
  python references/scripts/add_role.py dm --boot
```

---

## 7. Side effects, edge cases, upgrade path

### Side effects

| Side effect | Mitigation |
|---|---|
| Disk space from full clones | `git clone --local` uses hardlinks; typical SquidSquad repo is small |
| Network for remote clone | Detect if source is local; use `--local` when possible |
| Multiple `.local-config` writes | Atomic: write to temp file, then rename |
| Boot spawns a terminal | Only with explicit `--boot` flag |

### Edge cases

| Case | Handling |
|---|---|
| Role already has a clone | Check `.local-config` for existing entry; error with `--force` to override |
| Target directory already exists | Error unless `--force` |
| Source repo has uncommitted changes | Warning only (clone from remote URL, not local dirty state) |
| Windows path length limits | Use `\\?\` prefix for paths > 260 chars if needed |
| Role not in config.md | Error with suggestion to add it first |
| PM clone running — add_role modifies its `.local-config` | Safe: PM reads `.local-config` only during health checks, not continuously |
| Multiple `add_role` calls in parallel | File-level lock (same pattern as `boot-lock` in boot_remote.py) |

### Upgrade path

- **v1**: `add_role.py` as standalone script, called manually or by PM agent
- **v2**: PM sub-skill wraps the script so PM can run it as part of its Ralph Loop when it detects missing agents
- **v3**: Wizard integration — after scaffold, wizard offers to immediately create clones for all configured dev agents

### Backwards compatibility

- `.local-config` format is unchanged (same `- **role**: path` markdown)
- `health_check.py` and `boot_remote.py` need zero changes
- Existing manual clones continue to work; `add_role.py` can retroactively register them with `--register-existing <path>`

---

## 8. Recommended implementation plan

### Phase 1: Core script (MVP)

- `add_role.py` with clone + configure + sync
- Test on Windows (primary dev platform based on current `.local-config`)
- Test with `--dry-run` for safety

### Phase 2: Boot integration

- `--boot` flag calls `boot_remote.py`
- Verify boot scripts exist in new clone (compose.py generates them)

### Phase 3: PM sub-skill

- PM can call `add_role.py` when it detects a configured agent has no clone
- Ties into #347 (separate QA) and auto-boot flow

### Phase 4: Register existing

- `--register-existing <path>` to add manually-created clones to `.local-config`
- `--prune` to remove stale entries

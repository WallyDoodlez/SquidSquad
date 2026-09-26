# Vault Reference — Detailed Operations

The operational contract lives in the `vault-protocol` sub-skill; the design is
`docs/VAULT-ARCH.md` (v2). This page is the quick reference for both.

## Entity Model

Types and folders come from the type registry `.squidsquad/vault/vault-schema.json`
(framework default: `references/vault-schema-default.json`). The default profile:

| Type | Location | Purpose |
|------|----------|---------|
| `area` | `areas/*.md` | Ongoing concerns — human profile, conventions, design system (hub) |
| `project` | `projects/*.md` | Active project context, goals, constraints (hub) |
| `resource` | `resources/*.md` | Reference material, external docs, research |
| `system` | `systems/*.md` | One hub per subsystem; galaxy notes link into it |
| `decision` | `galaxy/decision-*.md` | Individual architectural/design/process decisions |
| `pattern` | `galaxy/pattern-*.md` | Recurring approaches, validated conventions |
| `learning` | `galaxy/learning-*.md` | Lessons learned, what worked / didn't |
| `rule` | `galaxy/rule-*.md` | Binding rules (Rule / Scope / Why) — matched at pickup, enforced by the verifier |

Notes retire by `status: superseded | archived`, never by moving to `archives/`
(which remains only as a legacy location).

## Searching the Vault

Search only through the engine — raw grep is banned because it leaves no
telemetry, so a useful note looks unused and gets proposed for pruning.

```bash
python references/scripts/vault_consume.py search --alias <alias> [--task N] \
    [--entities a,b] [--tags x,y] [--terms "free text"] [--types rule] [--top N] [--no-write]
```

- **Tiers**: filename > inbound-wikilink > tag > content. Matches then expand by
  budgeted wikilink traversal (galaxy hops cost budget, hub hops are free).
- **Ranking within a tier**: telemetry (`used`, `impression`, `walked`) + recency,
  times the type's weight; superseded/archived notes rank near zero.
- **Output**: metadata-only JSON; Read the bodies you need.
- **`--types rule`**: the binding-rules lane.
- **Exit 3**: engine unavailable (no `node`, or the engine is not installed) —
  report it honestly; never substitute a grep.
- **Recording use**: `vault_consume.py cite --alias <a> --task N --slugs a,b` writes
  `used` events for notes a committed artifact cites.

## Checks

| Command | Checks |
|---------|--------|
| `vault_check.py check-frontmatter` | Required fields: `type`, `tags`, `created`, `updated`, `owner`, `status` |
| `vault_check.py check-wikilinks` | Every `[[name]]` resolves to a note |
| `vault_check.py check-structure` | Folder / prefix / type consistency against the registry |
| `vault_check.py check-size` | Galaxy notes over 500 lines (advisory) |
| `vault_check.py check-hub-links` | Budgeted notes linked to no hub (advisory) |
| `vault_check.py list-orphans` | Notes nothing links to |

## Maintenance

Propose-only: `vault_optimize.py propose-prunes` turns the engine's impressions
report (cold / surfaced-never-used / stale buckets) into proposals for human
review; `vault_optimize.py compact-telemetry --alias <a>` compacts the caller's own
telemetry shard. Nothing is archived or deleted automatically.

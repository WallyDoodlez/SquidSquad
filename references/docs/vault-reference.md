# Vault Reference — Detailed Operations

## Entity Model

| Entity | Location | Purpose |
|--------|----------|---------|
| Human profile | `areas/human-profile.md` | Preferences, values, communication style |
| Company context | `areas/company-context.md` | Culture, standards, brand guidelines |
| Design system | `areas/design-system.md` | Colors, tokens, typography, component patterns |
| Code conventions | `areas/code-conventions.md` | Style, patterns, architecture decisions |
| Project context | `projects/{name}.md` | Goals, constraints, architecture, tech stack |
| Decisions | `galaxy/decision-*.md` | Individual architectural/design/process decisions |
| Patterns | `galaxy/pattern-*.md` | Recurring approaches, established conventions |
| Learnings | `galaxy/learning-*.md` | Lessons learned, what worked/didn't |
| Styles | `galaxy/style-*.md` | Visual style, writing tone, code style preferences |

## Searching the Vault (vault-search)

vault-search finds notes by tag, type, keyword, or wikilink traversal. It uses grep internally.

### Search modes:

1. **By tag**: Find notes whose `tags` frontmatter contains a specific tag.
   ```bash
   grep -rl "tags:.*\b<TAG>\b" .squidsquad/vault/ --include="*.md"
   ```

2. **By type**: Find notes with a specific `type` frontmatter value.
   ```bash
   grep -rl "^type: <TYPE>" .squidsquad/vault/ --include="*.md"
   ```

3. **By keyword** (full-text): Find notes containing a phrase.
   ```bash
   grep -rl "<KEYWORD>" .squidsquad/vault/ --include="*.md"
   ```

4. **By wikilink traversal**: Starting from a note, find connected notes.
   - **1-hop**: Outbound links (wikilinks in the note's body) + inbound links (other notes linking to this one).
     ```bash
     # Outbound: extract wikilinks from the note
     grep -o '\[\[[^]]*\]\]' .squidsquad/vault/<path> | sed 's/\[\[//g;s/\]\]//g'
     # Inbound: find notes linking TO this note
     grep -rl '\[\[<note-name>\]\]' .squidsquad/vault/ --include="*.md"
     ```
   - **2-hop**: For each 1-hop result, repeat the outbound+inbound search. Do NOT traverse beyond 2 hops.

**Result format**: Max 10 results, sorted by most recently updated.

**Caching**: Within a single cycle, cache search results to avoid repeated grep calls for the same query.

## Vault-Check Level 2 — Full Vault Sweep

Runs on-demand (invoked explicitly, not automatic). Checks every `.md` file in `.squidsquad/vault/`:

1. Run all Level 1 checks on every note.
2. **Orphan detection**: Find notes with zero inbound wikilinks that are not area notes. Area notes and BRIEFING.md are exempt.
3. **Staleness detection**: Find notes with `status: active` and `updated` date older than 30 days.
4. **Broken link census**: Aggregate all unresolved wikilinks across the vault.
5. **Health summary**: Print totals — note count, orphan count, stale count, broken link count.

```bash
# Quick orphan check: find notes never linked TO
for f in .squidsquad/vault/galaxy/*.md; do
  name=$(basename "$f" .md)
  if ! grep -rl "\[\[$name\]\]" .squidsquad/vault/ --include="*.md" -q 2>/dev/null; then
    echo "[vault-check] Orphan: $f"
  fi
done
```

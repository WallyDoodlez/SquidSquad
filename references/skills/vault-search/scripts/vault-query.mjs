#!/usr/bin/env node
// vault-query.mjs — SquidSquad vault search engine (#13857, PRD-VAULT-V2 P1).
//
// Forked from the reference system's vault-query.mjs (dmp-web, DMP-14042) and
// adapted to the SquidSquad contracts in docs/VAULT-ARCH.md:
//
//   - §6.2 search contract: tiered lexical match (filename > wikilink > tag >
//     content) + budgeted graph traversal (galaxy hops cost 1 of
//     traversalBudget, default 2; hub folders are free) + two-stage ranking
//     (tier, then telemetry-weighted tie-break × folder weight × status
//     multiplier). Top-K metadata-only JSON — no note bodies.
//   - §6.3 telemetry: counters are aggregated at read from the per-writer
//     JSONL shards under <vault>/.telemetry/ and written back as appended
//     events to the CALLER'S shard — never to note frontmatter.
//   - §8.5 caller identity: --instance-id and --alias are REQUIRED on every
//     call; --task carries the tracker issue number onto every event.
//   - §6.1: the engine writes `impression` (surfaced in top-K) and `walked`
//     (traversed connector surfaced in top-K) events only. `used` is written
//     only by consumers via record-consumption.mjs — never here.
//   - --no-write: dry run, zero telemetry events (§6.1 / AC4).
//
// ----------------------------------------------------------------------------
// Usage:
//   node .claude/skills/vault-search/scripts/vault-query.mjs
//        --instance-id <uuid> --alias <alias> [--task N]
//        [--vault <path>] [--entities a,b] [--tags x,y] [--terms "free text"]
//        [--top N] [--no-write]
//
//   --instance-id  harness instance UUID (shard identity) — required
//   --alias        acting agent alias, e.g. pm / skill      — required
//   --task         tracker issue number for event attribution (optional)
//   --vault        vault root (default ".squidsquad/vault", resolved vs CWD)
//   --entities     comma-separated entity names (filename / wikilink / tag / content)
//   --tags         comma-separated tag keywords (frontmatter tags: match)
//   --terms        free-text terms (content substring match); may repeat
//   --top          override config searchTopK for the surfaced/event cap
//   --no-write     dry run — emit zero telemetry events
//
// At least one of --entities / --tags / --terms is required, else exit 2.
// Missing --instance-id / --alias is exit 2 (caller identity is part of the
// engine contract, §8.5). Exit 0 on success (including zero matches).
//
// stdout is a single JSON object: { query, results, traversed, written }.
// ----------------------------------------------------------------------------

import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { pathToFileURL } from 'node:url';

import {
  loadConfig,
  deriveSchema,
  readTelemetry,
  makeEvent,
  appendEvents,
  shardPath,
  tieBreakScore,
} from './lib/consumption.mjs';

// Scan folders come from the vault-schema.json type registry (#13858, §3.1)
// — nothing hardcodes a taxonomy. BRIEFING.md and vault-schema.json live at
// the vault root, outside every registered folder, so they are structurally
// excluded from index, ranking, and telemetry (§6.2).
const DEFAULT_VAULT = join('.squidsquad', 'vault');

// Files that are navigation/scaffolding, never content notes.
const EXCLUDED_NAMES = new Set(['_template.md', 'README.md', 'INDEX.md']);

// Match tiers, strongest first (§6.2). Stage-1 ranking is by this order; a
// note that matches several tiers keeps its BEST (lowest-rank) tier. `walked`
// is the tier assigned to a traversed-only note (never a direct-match tier).
const TIER_ORDER = ['filename', 'wikilink', 'tag', 'content', 'walked'];

// ---- vault scan -------------------------------------------------------------

// Slug of a note file: its filename stem (basename without `.md`).
export function slugOf(name) {
  return name.replace(/\.md$/i, '');
}

// List every non-template note in the vault as { slug, folder, path, full }.
// `folders` defaults to the registry-derived scan list (§3.1); callers that
// already hold a loaded config pass its derived folders explicitly.
export function listNotes(vaultRoot, folders = null) {
  const notes = [];
  const scan = folders ?? deriveSchema(loadConfig(vaultRoot)).folders;
  for (const folder of scan) {
    const dir = join(vaultRoot, folder);
    let entries;
    try {
      entries = readdirSync(dir);
    } catch {
      continue; // folder may not exist yet — skip silently
    }
    for (const name of entries) {
      if (!name.endsWith('.md')) continue;
      if (EXCLUDED_NAMES.has(name)) continue;
      const full = join(dir, name);
      try {
        if (!statSync(full).isFile()) continue;
      } catch {
        continue;
      }
      notes.push({
        slug: slugOf(name),
        folder,
        path: relative(vaultRoot, full).split(sep).join('/'),
        full,
      });
    }
  }
  return notes;
}

// ---- frontmatter / content parsing (pure) -----------------------------------

// Split a note into its frontmatter block text and the raw content. Returns
// { fm, hasFm }. `fm` is the text between the leading `---` fences (no fences).
export function splitFrontmatter(content) {
  if (typeof content !== 'string' || !content.startsWith('---')) return { fm: '', hasFm: false };
  const end = content.indexOf('\n---', 3);
  if (end === -1) return { fm: '', hasFm: false };
  return { fm: content.slice(3, end), hasFm: true };
}

// A top-level scalar frontmatter field's value, or '' if none.
export function parseField(content, field) {
  const { fm, hasFm } = splitFrontmatter(content);
  if (!hasFm) return '';
  for (const raw of fm.split('\n')) {
    const line = raw.replace(/\r$/, '');
    if (/^\s/.test(line)) continue;
    const idx = line.indexOf(':');
    if (idx === -1) continue;
    if (line.slice(0, idx).trim() === field) {
      return line.slice(idx + 1).trim().replace(/^["']/, '').replace(/["']$/, '');
    }
  }
  return '';
}

// The note's `type:` from frontmatter, or '' if none.
export function parseType(content) {
  return parseField(content, 'type');
}

// The note's frontmatter `tags:` as a lower-cased string array. Supports the
// inline flow form `tags: [a, b]` and a plain comma list.
export function parseTags(content) {
  const { fm, hasFm } = splitFrontmatter(content);
  if (!hasFm) return [];
  const lines = fm.split('\n').map((l) => l.replace(/\r$/, ''));
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (/^\s/.test(line)) continue;
    const idx = line.indexOf(':');
    if (idx === -1) continue;
    if (line.slice(0, idx).trim() !== 'tags') continue;
    const val = line.slice(idx + 1).trim();
    if (val === '') {
      // Block list: collect following `  - tag` lines until dedent.
      const out = [];
      for (let j = i + 1; j < lines.length; j++) {
        if (!/^\s/.test(lines[j])) break;
        const m = /^\s*-\s*(.+)$/.exec(lines[j]);
        if (m) out.push(m[1].trim().replace(/^["']/, '').replace(/["']$/, '').toLowerCase());
      }
      return out.filter((t) => t !== '');
    }
    const inner = val.startsWith('[') && val.endsWith(']') ? val.slice(1, -1) : val;
    return inner
      .split(',')
      .map((t) => t.trim().replace(/^["']/, '').replace(/["']$/, '').toLowerCase())
      .filter((t) => t !== '');
  }
  return [];
}

// The note title: its first `# ` heading, else the filename stem (slug).
export function parseTitle(content, slug) {
  if (typeof content === 'string') {
    for (const raw of content.split('\n')) {
      const line = raw.replace(/\r$/, '');
      const m = /^#\s+(.+)$/.exec(line);
      if (m) return m[1].trim();
    }
  }
  return slug;
}

// All outbound wikilink target slugs in a note. Handles `[[slug]]` and the
// aliased `[[slug|label]]` (label dropped). Anywhere in the note, deduped,
// order-preserving. Empty targets are ignored.
export function parseLinksOut(content) {
  const out = [];
  const seen = new Set();
  if (typeof content !== 'string') return out;
  const re = /\[\[([^\]]+)\]\]/g;
  let m;
  while ((m = re.exec(content)) !== null) {
    let target = m[1];
    const bar = target.indexOf('|');
    if (bar !== -1) target = target.slice(0, bar);
    target = target.trim();
    if (target === '' || seen.has(target)) continue;
    seen.add(target);
    out.push(target);
  }
  return out;
}

// ---- matching (stage 1) -----------------------------------------------------

// Determine the best match tier for one note against the query. Returns null
// if no tier matched. Entities are tried first as filename then wikilink; if
// they miss there they still participate in tag and content matching
// alongside the dedicated tag/term inputs (§6.2 tier order).
export function matchTier(note, content, tags, query) {
  const slugLower = note.slug.toLowerCase();
  const contentLower = content.toLowerCase();
  const entities = query.entities.map((e) => e.toLowerCase());

  // Tier 1 — filename: an entity is a substring of this note's slug.
  for (const e of entities) {
    if (e !== '' && slugLower.includes(e)) return 'filename';
  }

  // Tier 2 — wikilink reverse-ref: the note links to a named entity.
  const linksOutLower = parseLinksOut(content).map((l) => l.toLowerCase());
  for (const e of entities) {
    if (e !== '' && linksOutLower.includes(e)) return 'wikilink';
  }

  // Tier 3 — tag: a tag keyword (or an entity) is present in frontmatter tags.
  const tagNeedles = [...query.tags.map((t) => t.toLowerCase()), ...entities].filter((t) => t !== '');
  for (const needle of tagNeedles) {
    if (tags.some((t) => t.includes(needle))) return 'tag';
  }

  // Tier 4 — content: a term (or an entity) appears anywhere in the note text.
  const termNeedles = [...query.terms.map((t) => t.toLowerCase()), ...entities].filter((t) => t !== '');
  for (const needle of termNeedles) {
    if (contentLower.includes(needle)) return 'content';
  }

  return null;
}

// Rank comparator honoring Stage-1 tier order then Stage-2 tie-break score,
// with a deterministic final tiebreak by slug. Stage 2 never crosses tiers.
function compareRanked(a, b) {
  const ta = TIER_ORDER.indexOf(a.tier);
  const tb = TIER_ORDER.indexOf(b.tier);
  if (ta !== tb) return ta - tb;
  if (b.score !== a.score) return b.score - a.score;
  return a.slug.localeCompare(b.slug);
}

// ---- traversal --------------------------------------------------------------

// A hop through a `traversal: budgeted` type's folder costs 1 unit of
// budget (§3.1/§6.2); `traversal: free` (hub) folders cost nothing. The
// registry (#13858) is the classification source — the P1 galaxy-only
// hardcode survives only as the default profile's registration.
function makeIsBudgeted(derived) {
  return (folder) => derived.budgetedFolders.has(folder);
}

// BFS outward from the direct-match set following outbound wikilinks, under
// the traversal budget: along any single path, at most `budget` budgeted
// (galaxy) notes may be visited (the start counts if it is budgeted). Free
// folders are still subject to the global visited set — "free" never means
// "re-visitable". Wikilinks to non-existent notes are ignored. Returns a map
// slug -> { note, walkedFrom:Set } for every note reached that is NOT itself
// a direct match.
export function traverse(directNotes, bySlug, budget, isBudgeted) {
  const directSlugs = new Set(directNotes.map((n) => n.slug));
  const visited = new Set(directNotes.map((n) => n.full)); // global, keyed by path
  const reached = new Map(); // slug -> { note, walkedFrom:Set<sourceSlug> }

  const frontier = [];
  for (const n of directNotes) {
    frontier.push({ note: n, kCount: isBudgeted(n.folder) ? 1 : 0 });
  }

  while (frontier.length > 0) {
    const { note, kCount } = frontier.shift();
    for (const targetSlug of parseLinksOut(note.content)) {
      const target = bySlug.get(targetSlug);
      if (!target) continue; // link to a non-existent note — ignore
      const nextK = kCount + (isBudgeted(target.folder) ? 1 : 0);
      // Budget: never exceed `budget` budgeted nodes on a path.
      if (isBudgeted(target.folder) && nextK > budget) continue;

      if (!directSlugs.has(target.slug)) {
        let entry = reached.get(target.slug);
        if (!entry) {
          entry = { note: target, walkedFrom: new Set() };
          reached.set(target.slug, entry);
        }
        entry.walkedFrom.add(note.slug);
      }

      if (visited.has(target.full)) continue;
      visited.add(target.full);
      frontier.push({ note: target, kCount: nextK });
    }
  }
  return reached;
}

// ---- query engine (pure over a loaded vault) --------------------------------

// Load every note's content once into { slug, folder, path, full, content }.
function loadVault(vaultRoot, folders) {
  const notes = listNotes(vaultRoot, folders);
  for (const n of notes) {
    try {
      n.content = readFileSync(n.full, 'utf8');
    } catch {
      n.content = '';
    }
  }
  return notes;
}

// Shape one ranked entry from a note + its aggregated telemetry.
function rankedEntry(n, tier, direct, telemetry, cfg, todayISO, derived) {
  const agg = telemetry.get(n.slug) ?? { impression: 0, used: 0, walked: 0, lastUsed: '' };
  const status = parseField(n.content, 'status');
  const updated = parseField(n.content, 'updated');
  const noteType = parseType(n.content) || n.folder;
  return {
    note: n,
    slug: n.slug,
    path: n.path,
    folder: n.folder,
    type: noteType,
    status,
    updated,
    tier,
    direct,
    score: tieBreakScore(
      { used: agg.used, impression: agg.impression, walked: agg.walked, updated, type: noteType, folder: n.folder, status },
      cfg,
      todayISO,
      derived,
    ),
    title: parseTitle(n.content, n.slug),
    used: agg.used,
    impression: agg.impression,
    walkedTotal: agg.walked,
    lastUsed: agg.lastUsed,
    linksOut: parseLinksOut(n.content),
  };
}

// Run the full query over an in-memory note list. Pure: computes results and
// traversed, but does NOT write. `telemetry` is the shard aggregate (may be
// empty — degraded ranking falls out of tieBreakScore, §6.2).
export function runQuery(notes, query, cfg, telemetry, todayISO, derived = null) {
  const d = derived ?? deriveSchema(cfg);
  const bySlug = new Map(notes.map((n) => [n.slug, n]));

  // Stage 1 — direct matches with best tier, plus Stage-2 tie-break score.
  const results = [];
  for (const n of notes) {
    const tags = parseTags(n.content);
    const tier = matchTier(n, n.content, tags, query);
    if (!tier) continue;
    results.push(rankedEntry(n, tier, true, telemetry, cfg, todayISO, d));
  }
  results.sort(compareRanked);

  // Budgeted traversal from the direct-match set (§3.1/§6.2).
  const reached = traverse(
    results.map((r) => r.note),
    bySlug,
    cfg.traversalBudget,
    makeIsBudgeted(d),
  );
  const traversed = [];
  for (const { note, walkedFrom } of reached.values()) {
    const entry = rankedEntry(note, 'walked', false, telemetry, cfg, todayISO, d);
    entry.walkedFrom = [...walkedFrom];
    traversed.push(entry);
  }
  // Traversed notes are ranked by tie-break score descending, slug as the
  // deterministic final tiebreak (all share the single 'walked' tier).
  traversed.sort((a, b) => {
    if (b.score !== a.score) return b.score - a.score;
    return a.slug.localeCompare(b.slug);
  });

  return { results, traversed };
}

// ---- telemetry emission -----------------------------------------------------

// Build the §6.1 events for one search: each surfaced top-K direct note gets
// an `impression` event; each surfaced traversed-only connector gets a
// `walked` event. Surfaced order is ranked results then ranked traversed,
// capped at K. Zero matches → zero events. `used` is NEVER written here.
export function buildEvents(results, traversed, topK, identity, deps = {}) {
  const surfaced = [...results, ...traversed].slice(0, topK);
  const events = [];
  for (const item of surfaced) {
    events.push(makeEvent(identity.alias, identity.task, item.slug, item.direct ? 'impression' : 'walked', deps));
  }
  return events;
}

// ---- CLI --------------------------------------------------------------------

// Split a comma-separated CLI list into trimmed, non-empty tokens.
function splitList(values) {
  const out = [];
  for (const v of values) {
    for (const tok of String(v).split(',')) {
      const t = tok.trim();
      if (t !== '') out.push(t);
    }
  }
  return out;
}

export function parseArgs(argv) {
  const out = {
    vault: DEFAULT_VAULT,
    entities: [],
    tags: [],
    terms: [],
    top: null,
    write: true,
    instanceId: '',
    alias: '',
    task: null,
  };
  const entities = [];
  const tags = [];
  const terms = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--vault') out.vault = argv[++i];
    else if (a === '--entities') entities.push(argv[++i]);
    else if (a === '--tags') tags.push(argv[++i]);
    else if (a === '--terms') terms.push(argv[++i]);
    else if (a === '--top') out.top = Number(argv[++i]);
    else if (a === '--no-write') out.write = false;
    else if (a === '--instance-id') out.instanceId = String(argv[++i] || '').trim();
    else if (a === '--alias') out.alias = String(argv[++i] || '').trim();
    else if (a === '--task') {
      // Issue numbers start at 1; 0/negative/garbage degrade to "no task"
      // (--task is optional here) so shard events never carry task: 0.
      const n = Number.parseInt(argv[++i], 10);
      out.task = Number.isFinite(n) && n >= 1 ? n : null;
    }
  }
  out.entities = splitList(entities);
  out.tags = splitList(tags);
  out.terms = splitList(terms);
  return out;
}

function todayISO() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

const USAGE =
  'usage: vault-query.mjs --instance-id <uuid> --alias <alias> [--task N]\n' +
  '       [--vault <path>] [--entities a,b] [--tags x,y] [--terms "free text"] [--top N] [--no-write]\n';

// Shape a ranked item into the public JSON result object (drops the internal
// note handle). `walkedFrom` is included only for traversed items.
function toPublic(item) {
  const pub = {
    slug: item.slug,
    path: item.path,
    folder: item.folder,
    type: item.type,
    status: item.status,
    tier: item.tier,
    direct: item.direct,
    score: item.score,
    title: item.title,
    updated: item.updated || '',
    used: item.used,
    impression: item.impression,
    walkedTotal: item.walkedTotal,
    lastUsed: item.lastUsed,
    linksOut: item.linksOut,
  };
  if (!item.direct) pub.walkedFrom = item.walkedFrom;
  return pub;
}

export function main(argv = process.argv.slice(2), deps = {}) {
  const stderr = deps.stderr ?? ((s) => process.stderr.write(s));
  const stdout = deps.stdout ?? ((s) => process.stdout.write(s));
  const today = deps.todayISO ?? todayISO();

  const args = parseArgs(argv);
  if (args.instanceId === '' || args.alias === '') {
    stderr(USAGE + 'error: --instance-id and --alias are required (engine caller identity, VAULT-ARCH §8.5)\n');
    return 2;
  }
  if (args.entities.length === 0 && args.tags.length === 0 && args.terms.length === 0) {
    stderr(USAGE + 'error: at least one of --entities / --tags / --terms is required\n');
    return 2;
  }

  const cfg = loadConfig(args.vault);
  // Clamp to a non-negative integer: a negative topK would reach
  // Array.slice(0, -N) in buildEvents and UNCAP the surfaced set (drop just
  // the tail) instead of capping it — fail closed to 0 instead.
  const topK = Math.max(0, Math.trunc(
    args.top != null && Number.isFinite(args.top) ? args.top : cfg.searchTopK));
  const query = { entities: args.entities, tags: args.tags, terms: args.terms };

  const derived = deriveSchema(cfg);
  const notes = loadVault(args.vault, derived.folders);
  const telemetry = readTelemetry(args.vault, deps);
  const { results, traversed } = runQuery(notes, query, cfg, telemetry, today, derived);

  let written;
  if (!args.write) {
    written = { events: 0, shard: null, skipped: true };
  } else {
    const events = buildEvents(results, traversed, topK, { alias: args.alias, task: args.task }, deps);
    let count = 0;
    try {
      count = appendEvents(args.vault, args.instanceId, args.alias, events, deps);
    } catch (err) {
      // §9.9: telemetry write failure — drop with a log line, never block.
      stderr(`warn: telemetry append failed (${err && err.message ? err.message : err}) — events dropped\n`);
    }
    written = { events: count, shard: shardPath(args.vault, args.instanceId, args.alias), skipped: false };
  }

  const payload = {
    query,
    results: results.map(toPublic),
    traversed: traversed.map(toPublic),
    written,
  };
  stdout(JSON.stringify(payload, null, 2) + '\n');
  return 0;
}

// Run the CLI only when invoked directly, not on import (so tests can import functions).
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(main());
}

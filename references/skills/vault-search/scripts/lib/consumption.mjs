// consumption.mjs — SquidSquad vault engine shared lib (#13857, PRD-VAULT-V2 P1).
//
// Forked from the reference system's vault-lib/consumption.mjs (dmp-web,
// DMP-14042) and adapted to the SquidSquad telemetry contract
// (docs/VAULT-ARCH.md §6.1–§6.3):
//
//   - Telemetry lives in git-tracked per-writer JSONL shards under
//     <vault>/.telemetry/<instance-id>-<alias>.jsonl — NOT in note
//     frontmatter. Notes stay pure content, forever (§6.3). The upstream
//     frontmatter read/write halves (parseCounters / bumpCounters /
//     setCounters and the whole counter-line rewriter) are therefore gone;
//     in their place: readTelemetry (shard aggregate, dedupe by event id,
//     sum per slug) and appendEvents (append-only shard write).
//   - Ranking recency comes from the note's own `updated:` frontmatter date
//     (§6.2) — telemetry-independent, so it survives the degraded path —
//     not from a last_impression counter.
//   - Config is <vault>/vault-schema.json (§3.1 registry, P2). Until the
//     registry ships, the DEFAULT_CONFIG below is the P1 default mapping:
//     PARAG folder weights, galaxy-only traversal budget, status
//     multipliers for superseded/archived.
//
// Zero dependencies, plain node ESM. Filesystem access only in loadConfig,
// readTelemetry, and appendEvents — all fail-open (§6.2 graceful
// degradation / §9.9): a missing or corrupt shard never throws past the
// aggregate; a failed append is the caller's log-and-continue concern.

import { readFileSync, readdirSync, appendFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';

// Defaults (§6.2 weights operator-locked). P2 (#13858): `types` is the §3.2
// default profile — the full registry shape of §3.1 — and is what an absent
// or typeless vault-schema.json degrades to. `folderWeights` survives as a
// LEGACY override layer (a pre-registry schema file may carry it; resolution
// order is type weight → folderWeights → 1). `archives` stays listed as a
// scan folder for v1-era vaults even though §3.4 retires the physical move.
export const DEFAULT_CONFIG = {
  searchTopK: 12,
  traversalBudget: 2,
  tieBreakWeights: { used: 2.0, impression: 0.25, walked: 0.5, recency: 0.25 },
  types: {
    project: { folder: 'projects', traversal: 'free', weight: 0.8, hub: true },
    area: { folder: 'areas', traversal: 'free', weight: 0.8, hub: true },
    resource: { folder: 'resources', traversal: 'free', weight: 0.6, hub: false },
    decision: { folder: 'galaxy', traversal: 'budgeted', weight: 1.0, hub: false, prefix: 'decision-' },
    pattern: { folder: 'galaxy', traversal: 'budgeted', weight: 1.0, hub: false, prefix: 'pattern-' },
    learning: { folder: 'galaxy', traversal: 'budgeted', weight: 1.0, hub: false, prefix: 'learning-' },
    system: { folder: 'systems', traversal: 'free', weight: 0.8, hub: true },
    archive: { folder: 'archives', traversal: 'free', weight: 0.5, hub: false },
  },
  folderWeights: {},
  statusMultipliers: { superseded: 0.01, archived: 0.01 },
};

// ---- config -----------------------------------------------------------------

// Load tuning config, deep-merging <vaultRoot>/vault-schema.json over
// DEFAULT_CONFIG. Nested objects are spread so a partial override never drops
// sibling defaults. Absent or malformed file → pure defaults.
export function loadConfig(vaultRoot, readFile = readFileSync) {
  try {
    const raw = readFile(join(vaultRoot, 'vault-schema.json'), 'utf8');
    const parsed = JSON.parse(raw);
    // `types` REPLACES the default set when provided (a custom taxonomy must
    // not inherit phantom default types, §3.1); scalars and the two legacy
    // maps deep-merge. A present-but-empty/malformed types{} degrades to the
    // default profile (fail-open, §6.2).
    const parsedTypes =
      parsed.types && typeof parsed.types === 'object' && Object.keys(parsed.types).length > 0
        ? parsed.types
        : DEFAULT_CONFIG.types;
    return {
      ...DEFAULT_CONFIG,
      ...parsed,
      types: parsedTypes,
      tieBreakWeights: { ...DEFAULT_CONFIG.tieBreakWeights, ...parsed.tieBreakWeights },
      folderWeights: { ...DEFAULT_CONFIG.folderWeights, ...parsed.folderWeights },
      statusMultipliers: { ...DEFAULT_CONFIG.statusMultipliers, ...parsed.statusMultipliers },
    };
  } catch {
    return DEFAULT_CONFIG;
  }
}

// ---- registry derivation (§3.1) ---------------------------------------------

// Derive the folder-level views the scanner and traversal need from the type
// registry: scan-folder list (registration order, deduped), the set of
// folders whose types are `traversal: budgeted`, and a per-folder default
// weight — used when a note's own `type:` is missing/unregistered. NOTE the
// documented contract: for a folder hosting several types the default is the
// FIRST-REGISTERED type's weight, so registration order in vault-schema.json
// is meaningful for untyped notes in shared folders (external review,
// #13858 — an explicit per-folder default field is a possible future
// refinement). Malformed type entries (no folder) are skipped.
export function deriveSchema(cfg) {
  const folders = [];
  const budgetedFolders = new Set();
  const folderDefaultWeight = {};
  for (const t of Object.values(cfg.types || {})) {
    if (!t || typeof t.folder !== 'string' || t.folder === '') continue;
    if (!folders.includes(t.folder)) folders.push(t.folder);
    if (t.traversal === 'budgeted') budgetedFolders.add(t.folder);
    if (!(t.folder in folderDefaultWeight) && Number.isFinite(t.weight)) {
      folderDefaultWeight[t.folder] = t.weight;
    }
  }
  return { folders, budgetedFolders, folderDefaultWeight };
}

// Per-note ranking weight (§3.1 `weight` × §6.2): the note's own registered
// type wins; unregistered/missing type falls back to the legacy
// folderWeights override, then the folder's first-registered type weight,
// then 1.
export function typeWeight(cfg, noteType, folder, derived = null) {
  const t = (cfg.types || {})[noteType];
  if (t && Number.isFinite(t.weight)) return t.weight;
  if (Number.isFinite(cfg.folderWeights?.[folder])) return cfg.folderWeights[folder];
  const d = derived ?? deriveSchema(cfg);
  if (Number.isFinite(d.folderDefaultWeight[folder])) return d.folderDefaultWeight[folder];
  return 1;
}

// ---- scalar coercion --------------------------------------------------------

// Coerce a value to a non-negative integer count. Garbage, negatives, and zero
// all collapse to 0 (they carry no consumption signal).
export function toCount(val) {
  const n = Number.parseInt(val, 10);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

// ---- telemetry read (shard aggregate) ---------------------------------------

const TELEMETRY_DIR = '.telemetry';
const COUNTERS = new Set(['impression', 'used', 'walked']);

// Read every shard under <vaultRoot>/.telemetry/*.jsonl and aggregate to a
// per-slug counter map:
//   Map slug -> { impression, used, walked, lastUsed }
// where lastUsed is the YYYY-MM-DD date of the newest `used` event for the
// slug ('' if never used). Events are deduped by `id` across all shards —
// merge=union double-merged lines and re-read aggregates are harmless (§6.3).
// Fail-open at every level (§6.2 degradation): unreadable dir → empty map;
// unreadable file → skip file; unparseable line → skip line.
export function readTelemetry(vaultRoot, deps = {}) {
  const readDir = deps.readdir ?? readdirSync;
  const readFile = deps.readFile ?? readFileSync;
  const bySlug = new Map();
  const seen = new Set();
  let entries;
  try {
    entries = readDir(join(vaultRoot, TELEMETRY_DIR));
  } catch {
    return bySlug; // no telemetry dir yet — cold start, degrade silently
  }

  const addCounts = (slug, imp, used, walked, lastUsed) => {
    let agg = bySlug.get(slug);
    if (!agg) {
      agg = { impression: 0, used: 0, walked: 0, lastUsed: '' };
      bySlug.set(slug, agg);
    }
    agg.impression += imp;
    agg.used += used;
    agg.walked += walked;
    if (lastUsed && lastUsed > agg.lastUsed) agg.lastUsed = lastUsed;
  };

  // Writer keys present as live shards and/or aggregates (§6.5: readers
  // treat aggregate + live shard as ONE logical stream per writer).
  const shardKeys = entries.filter((f) => f.endsWith('.jsonl')).map((f) => f.slice(0, -6));
  const aggKeys = entries.filter((f) => f.endsWith('.agg.json')).map((f) => f.slice(0, -9));
  const writers = [...new Set([...shardKeys, ...aggKeys])];

  for (const key of writers) {
    // 1. Aggregate totals (compacted history).
    let lastAbsorbedId = null;
    try {
      const parsed = JSON.parse(readFile(join(vaultRoot, TELEMETRY_DIR, `${key}.agg.json`), 'utf8'));
      if (parsed && parsed.counts && typeof parsed.counts === 'object') {
        lastAbsorbedId = parsed.lastAbsorbedId ?? null;
        for (const [slug, c] of Object.entries(parsed.counts)) {
          addCounts(slug, toCount(c.impression), toCount(c.used), toCount(c.walked), c.lastUsed || '');
        }
      }
    } catch {
      /* absent/corrupt aggregate — live shard alone (fail-open) */
    }

    // 2. Live shard events — positionally skipping the absorbed prefix when
    // lastAbsorbedId is still present (the §6.5 crash window: aggregate
    // written, shard not yet truncated — without this skip those events
    // would double-count, and dedup-by-id cannot catch it after the fact).
    let raw;
    try {
      raw = readFile(join(vaultRoot, TELEMETRY_DIR, `${key}.jsonl`), 'utf8');
    } catch {
      continue; // aggregate-only writer
    }
    const lines = raw.split('\n');
    // Locate the absorbed-prefix boundary by EXACT parsed id (mirrors
    // compact()'s search) — never by substring, which can false-positive on
    // an id-prefix collision or a corrupt line containing the marker text
    // and then silently drop every later event. Marker absent (the normal
    // truncated-shard case, or a corrupt marker line) → no skip; the worst
    // residual is a bounded transient over-count in the corrupt-marker +
    // crash-window intersection, never unbounded silent loss.
    let skipUntil = -1;
    if (lastAbsorbedId !== null) {
      for (let i = 0; i < lines.length; i++) {
        try {
          if (JSON.parse(lines[i]).id === lastAbsorbedId) {
            skipUntil = i;
            break;
          }
        } catch {
          continue;
        }
      }
    }
    for (let li = 0; li < lines.length; li++) {
      if (li <= skipUntil) continue; // inside the already-absorbed prefix
      const t2 = lines[li].trim();
      if (t2 === '') continue;
      let ev;
      try {
        ev = JSON.parse(t2);
      } catch {
        continue; // corrupt line (partial append, bad merge) — skip
      }
      if (!ev || typeof ev !== 'object') continue;
      if (typeof ev.slug !== 'string' || ev.slug === '') continue;
      if (!COUNTERS.has(ev.counter)) continue;
      if (typeof ev.id !== 'string' || ev.id === '') continue;
      if (seen.has(ev.id)) continue; // dedupe across union-merged duplicates
      seen.add(ev.id);
      const day = ev.counter === 'used' && typeof ev.ts === 'string' ? ev.ts.slice(0, 10) : '';
      addCounts(ev.slug,
        ev.counter === 'impression' ? 1 : 0,
        ev.counter === 'used' ? 1 : 0,
        ev.counter === 'walked' ? 1 : 0,
        /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : '');
    }
  }
  return bySlug;
}

// ---- telemetry write (shard append) -----------------------------------------

// Build one §6.1 event record. `task` is the tracker issue number (int) or
// null when the caller is outside any task.
export function makeEvent(alias, task, slug, counter, deps = {}) {
  const id = deps.uuid ?? randomUUID();
  const ts = deps.nowISO ?? new Date().toISOString();
  return { id, ts, agent: alias, task, slug, counter };
}

// The caller's shard path: one writer, one file (§6.3). The instance id comes
// from the harness (gitignored local state); the alias is the acting agent.
export function shardPath(vaultRoot, instanceId, alias) {
  return join(vaultRoot, TELEMETRY_DIR, `${instanceId}-${alias}.jsonl`);
}

// The caller's compaction aggregate (§6.5, #13859): same writer axis as the
// shard, naming fixed by the PRD.
export function aggregatePath(vaultRoot, instanceId, alias) {
  return join(vaultRoot, TELEMETRY_DIR, `${instanceId}-${alias}.agg.json`);
}

// Read one writer's aggregate: {lastAbsorbedId, counts:{slug:{impression,
// used, walked, lastUsed}}} or null when absent/corrupt (fail-open, §9.9).
export function readAggregate(vaultRoot, instanceId, alias, deps = {}) {
  const readFile = deps.readFile ?? readFileSync;
  try {
    const parsed = JSON.parse(readFile(aggregatePath(vaultRoot, instanceId, alias), 'utf8'));
    if (parsed && typeof parsed === 'object' && parsed.counts && typeof parsed.counts === 'object') {
      return { lastAbsorbedId: parsed.lastAbsorbedId ?? null, counts: parsed.counts };
    }
  } catch {
    /* fall through */
  }
  return null;
}

// Append events to the caller's own shard, one JSON line each, trailing
// newline (the §8.5 shard append discipline). Creates .telemetry/ on first
// write. Never touches any other shard, never seeds .gitattributes (that is
// installer work, §8.5). Returns the number of lines appended. Failures
// propagate to the caller, which logs and continues (§9.9: telemetry is
// operational signal — losing an event is fine, blocking work is not).
export function appendEvents(vaultRoot, instanceId, alias, events, deps = {}) {
  if (events.length === 0) return 0;
  const append = deps.appendFile ?? appendFileSync;
  const mkdir = deps.mkdir ?? mkdirSync;
  mkdir(join(vaultRoot, TELEMETRY_DIR), { recursive: true });
  const lines = events.map((e) => JSON.stringify(e)).join('\n') + '\n';
  append(shardPath(vaultRoot, instanceId, alias), lines, 'utf8');
  return events.length;
}

// ---- scoring ----------------------------------------------------------------

// Whole-days difference between an ISO date and `today`. null on malformed input.
export function ageInDays(iso, todayISO) {
  const a = isoToUTC(iso);
  const b = isoToUTC(todayISO);
  if (Number.isNaN(a) || Number.isNaN(b)) return null;
  return Math.floor((b - a) / 86400000);
}

function isoToUTC(iso) {
  if (typeof iso !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(iso.trim())) return NaN;
  return Date.parse(`${iso.trim()}T00:00:00Z`);
}

// 0–1 freshness score from the note's `updated:` frontmatter date (§6.2):
// 1/(1 + ageInDays), newer → higher. Missing/invalid date → 0. Deliberately
// telemetry-independent so it survives the degraded path.
export function recencyBonus(updatedISO, todayISO) {
  const age = ageInDays(updatedISO, todayISO);
  return age === null ? 0 : 1 / (1 + Math.max(0, age));
}

// Stage-2 tie-break score (§6.2): telemetry-weighted —
//   used×W.used + impression×W.impression + walked×W.walked + recency×W.recency
// — multiplied by the note's TYPE weight (registry-resolved via typeWeight,
// #13858; legacy folderWeights override honored) and by the status
// multiplier (superseded/archived rank near zero but stay discoverable).
// `fields` = { used, impression, walked, updated, type, folder, status }
// where the three counters are plain ints (missing → 0). With no telemetry
// at all the score degrades to recency × weights — i.e. tier + recency +
// type weight (§6.2 graceful degradation) with no special-casing.
export function tieBreakScore(fields, config, todayISO, derived = null) {
  const w = config.tieBreakWeights;
  const base =
    toCount(fields.used) * (w.used ?? 0) +
    toCount(fields.impression) * (w.impression ?? 0) +
    toCount(fields.walked) * (w.walked ?? 0) +
    recencyBonus(fields.updated, todayISO) * (w.recency ?? 0);
  const fw = typeWeight(config, fields.type, fields.folder, derived);
  const sm = config.statusMultipliers[String(fields.status || '').toLowerCase()] ?? 1;
  return base * fw * sm;
}

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

// P1 defaults (§6.2 weights operator-locked; folder weights and status
// multipliers are the P1 default mapping, tunable via vault-schema.json).
export const DEFAULT_CONFIG = {
  searchTopK: 12,
  traversalBudget: 2,
  tieBreakWeights: { used: 2.0, impression: 0.25, walked: 0.5, recency: 0.25 },
  folderWeights: { galaxy: 1.0, projects: 0.8, areas: 0.8, resources: 0.7, archives: 0.5 },
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
    return {
      ...DEFAULT_CONFIG,
      ...parsed,
      tieBreakWeights: { ...DEFAULT_CONFIG.tieBreakWeights, ...parsed.tieBreakWeights },
      folderWeights: { ...DEFAULT_CONFIG.folderWeights, ...parsed.folderWeights },
      statusMultipliers: { ...DEFAULT_CONFIG.statusMultipliers, ...parsed.statusMultipliers },
    };
  } catch {
    return DEFAULT_CONFIG;
  }
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
  let files;
  try {
    files = readDir(join(vaultRoot, TELEMETRY_DIR)).filter((f) => f.endsWith('.jsonl'));
  } catch {
    return bySlug; // no telemetry dir yet — cold start, degrade silently
  }
  for (const f of files) {
    let raw;
    try {
      raw = readFile(join(vaultRoot, TELEMETRY_DIR, f), 'utf8');
    } catch {
      continue; // unreadable shard — skip, never block the read path
    }
    for (const line of raw.split('\n')) {
      const t = line.trim();
      if (t === '') continue;
      let ev;
      try {
        ev = JSON.parse(t);
      } catch {
        continue; // corrupt line (partial append, bad merge) — skip
      }
      if (!ev || typeof ev !== 'object') continue;
      if (typeof ev.slug !== 'string' || ev.slug === '') continue;
      if (!COUNTERS.has(ev.counter)) continue;
      if (typeof ev.id !== 'string' || ev.id === '') continue;
      if (seen.has(ev.id)) continue; // dedupe across union-merged duplicates
      seen.add(ev.id);
      let agg = bySlug.get(ev.slug);
      if (!agg) {
        agg = { impression: 0, used: 0, walked: 0, lastUsed: '' };
        bySlug.set(ev.slug, agg);
      }
      agg[ev.counter] += 1;
      if (ev.counter === 'used' && typeof ev.ts === 'string') {
        const day = ev.ts.slice(0, 10);
        if (/^\d{4}-\d{2}-\d{2}$/.test(day) && day > agg.lastUsed) agg.lastUsed = day;
      }
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
// — multiplied by the folder/type weight and by the status multiplier
// (superseded/archived rank near zero but stay discoverable). `fields` =
// { used, impression, walked, updated, folder, status } where the three
// counters are plain ints (missing → 0). With no telemetry at all the score
// degrades to recency × weights — i.e. tier + recency + type weight (§6.2
// graceful degradation) with no special-casing.
export function tieBreakScore(fields, config, todayISO) {
  const w = config.tieBreakWeights;
  const base =
    toCount(fields.used) * (w.used ?? 0) +
    toCount(fields.impression) * (w.impression ?? 0) +
    toCount(fields.walked) * (w.walked ?? 0) +
    recencyBonus(fields.updated, todayISO) * (w.recency ?? 0);
  const fw = config.folderWeights[fields.folder] ?? 1;
  const sm = config.statusMultipliers[String(fields.status || '').toLowerCase()] ?? 1;
  return base * fw * sm;
}

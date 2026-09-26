#!/usr/bin/env node
// vault-impressions-report.mjs — SquidSquad vault usage reporter
// (#13859, PRD-VAULT-V2 P3 / VAULT-ARCH §6.4).
//
// The third §8.5 engine operation (search / record / REPORT): reads the
// per-writer telemetry shards (§6.3, via the shared lib's aggregate) and the
// note inventory, and screens every note against §4.4's three retirement
// buckets. Forked in spirit from the reference system's reporter, adapted to
// shard-based telemetry (the reference reads frontmatter counters, which
// SquidSquad notes never carry).
//
//   - cold:               zero events of any kind — never surfaced by search
//   - surfacedNeverUsed:  offered in top-K / traversed (impression+walked > 0)
//                         but never once cited by a consumer (used == 0)
//   - stale:              used at least once, but not within --stale-days
//   (a note in NO bucket is healthy and untouched)
//
// The report is the PURGE SIGNAL feeding vault_optimize.py's proposal run
// (§7.3) and PM's improvement scan. It RECOMMENDS — it never deletes, and it
// is strictly read-only: no telemetry write, hence no caller identity (the
// §8.5 report row carries none).
//
// Usage:
//   node vault-impressions-report.mjs [--vault <path>] [--today YYYY-MM-DD]
//        [--stale-days N] [--top N]
//
// stdout: one JSON object
//   { generatedAt, staleDays, vaultRoot,
//     counts: {total, cold, surfacedNeverUsed, stale, healthy},
//     rows: [{slug, path, folder, type, status, used, impression, walked,
//             lastUsed, cold, surfacedNeverUsed, stale}] }
// rows are sorted least-consumed-first (the purge-candidate ordering);
// --top caps the row list (counts stay full-inventory).

import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

import { listNotes, parseType, parseField } from './vault-query.mjs';
import { loadConfig, deriveSchema, readTelemetry, ageInDays, toCount } from './lib/consumption.mjs';

export function buildReport(vaultRoot, { todayISO, staleDays = 90, top = null, deps = {} } = {}) {
  const cfg = loadConfig(vaultRoot);
  const derived = deriveSchema(cfg);
  const notes = listNotes(vaultRoot, derived.folders);
  const telemetry = readTelemetry(vaultRoot, deps);
  const read = deps.readFile ?? readFileSync;

  const rows = [];
  for (const n of notes) {
    let content = '';
    try {
      content = read(n.full, 'utf8');
    } catch {
      content = '';
    }
    const agg = telemetry.get(n.slug) ?? { impression: 0, used: 0, walked: 0, lastUsed: '' };
    const used = toCount(agg.used);
    const surfaced = toCount(agg.impression) + toCount(agg.walked);
    const age = agg.lastUsed ? ageInDays(agg.lastUsed, todayISO) : null;
    const cold = used === 0 && surfaced === 0;
    const surfacedNeverUsed = used === 0 && surfaced > 0;
    const stale = used > 0 && (age === null || age > staleDays);
    rows.push({
      slug: n.slug,
      path: n.path,
      folder: n.folder,
      type: parseType(content) || n.folder,
      status: parseField(content, 'status'),
      used,
      impression: toCount(agg.impression),
      walked: toCount(agg.walked),
      lastUsed: agg.lastUsed || null,
      cold,
      surfacedNeverUsed,
      stale,
    });
  }

  // Least-consumed-first: cold, then surfaced-never-used, then stale, then
  // healthy; deterministic slug tiebreak inside each band.
  const band = (r) => (r.cold ? 0 : r.surfacedNeverUsed ? 1 : r.stale ? 2 : 3);
  rows.sort((a, b) => band(a) - band(b) || a.slug.localeCompare(b.slug));

  const counts = {
    total: rows.length,
    cold: rows.filter((r) => r.cold).length,
    surfacedNeverUsed: rows.filter((r) => r.surfacedNeverUsed).length,
    stale: rows.filter((r) => r.stale).length,
  };
  counts.healthy = counts.total - counts.cold - counts.surfacedNeverUsed - counts.stale;

  return {
    generatedAt: todayISO,
    staleDays,
    vaultRoot,
    counts,
    rows: top != null && Number.isFinite(top) && top >= 0 ? rows.slice(0, Math.trunc(top)) : rows,
  };
}

export function parseArgs(argv) {
  const out = { vault: '.squidsquad/vault', today: null, staleDays: 90, top: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--vault') out.vault = argv[++i];
    else if (a === '--today') out.today = argv[++i];
    else if (a === '--stale-days') {
      const n = Number.parseInt(argv[++i], 10);
      if (Number.isFinite(n) && n >= 1) out.staleDays = n;
    } else if (a === '--top') {
      const n = Number.parseInt(argv[++i], 10);
      out.top = Number.isFinite(n) && n >= 0 ? n : null;
    }
  }
  return out;
}

function todayISO() {
  const d = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function main(argv = process.argv.slice(2), deps = {}) {
  const stdout = deps.stdout ?? ((s) => process.stdout.write(s));
  const args = parseArgs(argv);
  const report = buildReport(args.vault, {
    todayISO: args.today || deps.todayISO || todayISO(),
    staleDays: args.staleDays,
    top: args.top,
    deps,
  });
  stdout(JSON.stringify(report, null, 2) + '\n');
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(main());
}

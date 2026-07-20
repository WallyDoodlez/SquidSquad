#!/usr/bin/env node
// compact-telemetry.mjs — telemetry shard compaction
// (#13859, PRD-VAULT-V2 P3 S3.4 / VAULT-ARCH §6.5).
//
// Rolls events older than the horizon out of the caller's OWN live shard
// into a per-writer aggregate file, truncating the raw shard. The three
// §6.5 invariants, all structural here:
//
//   1. OWNER-ONLY: --instance-id + --alias are required and select exactly
//      one shard — this tool can never rewrite another writer's shard, so
//      truncation can never race an append.
//   2. AGGREGATE-BEFORE-TRUNCATE, ONE COMMIT: the updated aggregate is
//      written before the truncated shard, and BOTH are left staged for the
//      caller's single commit (this tool never commits; the caller — the
//      vault_optimize maintenance pass — owns the commit).
//   3. IDEMPOTENT RE-COMPACTION: the aggregate records the id of the last
//      event it absorbed (`lastAbsorbedId`). A crash between the two file
//      writes leaves the aggregate updated and the shard untruncated; the
//      re-run (and the read path, see readTelemetry) skips shard events up
//      to and including `lastAbsorbedId` positionally, so nothing is ever
//      absorbed twice. This must hold structurally because aggregates carry
//      summed totals without per-event ids.
//
// Aggregate naming (fixed here per the PRD): `<instance-id>-<alias>.agg.json`
// alongside the shard. Horizon default: 30 days (fixed here per the PRD).
//
// Usage:
//   node compact-telemetry.mjs --instance-id <uuid> --alias <alias>
//        [--vault <path>] [--horizon-days N] [--today YYYY-MM-DD]
//
// stdout: {absorbed, remaining, aggregate, shard, skipped:false} JSON.
// Missing shard → {absorbed: 0, ...} exit 0 (nothing to compact, §9.9).

import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

import { shardPath, aggregatePath, readAggregate, ageInDays } from './lib/consumption.mjs';

export function compact(vaultRoot, instanceId, alias, { todayISO, horizonDays = 30, deps = {} } = {}) {
  const read = deps.readFile ?? readFileSync;
  const write = deps.writeFile ?? writeFileSync;
  const shard = shardPath(vaultRoot, instanceId, alias);
  const aggFile = aggregatePath(vaultRoot, instanceId, alias);

  let raw = '';
  try {
    raw = read(shard, 'utf8');
  } catch {
    return { absorbed: 0, remaining: 0, aggregate: aggFile, shard, note: 'no shard' };
  }

  const agg = readAggregate(vaultRoot, instanceId, alias, deps) ?? {
    lastAbsorbedId: null,
    counts: {},
  };

  // Positional skip past already-absorbed events (invariant 3): if the
  // aggregate's lastAbsorbedId is still present in the shard, everything up
  // to and including it was absorbed by a previous (possibly crashed) run.
  const lines = raw.split('\n').filter((l) => l.trim() !== '');
  let start = 0;
  if (agg.lastAbsorbedId) {
    for (let i = 0; i < lines.length; i++) {
      try {
        if (JSON.parse(lines[i]).id === agg.lastAbsorbedId) {
          start = i + 1;
          break;
        }
      } catch {
        continue;
      }
    }
  }

  const remainingLines = [];
  let absorbed = 0;
  let lastAbsorbed = agg.lastAbsorbedId;

  for (let i = start; i < lines.length; i++) {
    let ev;
    try {
      ev = JSON.parse(lines[i]);
    } catch {
      remainingLines.push(lines[i]); // corrupt line: keep in shard, never absorb
      continue;
    }
    const day = typeof ev.ts === 'string' ? ev.ts.slice(0, 10) : '';
    const age = /^\d{4}-\d{2}-\d{2}$/.test(day) ? ageInDays(day, todayISO) : null;
    const oldEnough = age !== null && age > horizonDays;
    // The absorbed range must stay a PREFIX (positional idempotency depends
    // on it): stop absorbing at the first too-young event.
    if (!oldEnough || remainingLines.length > 0) {
      remainingLines.push(lines[i]);
      continue;
    }
    if (!ev.slug || !ev.counter) {
      remainingLines.push(lines[i]);
      continue;
    }
    const c = (agg.counts[ev.slug] ??= { impression: 0, used: 0, walked: 0, lastUsed: '' });
    if (ev.counter in c && typeof c[ev.counter] === 'number') c[ev.counter] += 1;
    if (ev.counter === 'used' && day > (c.lastUsed || '')) c.lastUsed = day;
    lastAbsorbed = ev.id;
    absorbed += 1;
  }

  // Write when new events were absorbed OR an absorbed-but-untruncated
  // prefix is present (start > 0 — the invariant-3 crash window: a prior run
  // wrote the aggregate and died before truncating; this run completes the
  // truncation, otherwise the residue prefix lives in the shard forever).
  if (absorbed > 0 || start > 0) {
    // Invariant 2 ordering: aggregate first, then the truncated shard.
    agg.lastAbsorbedId = lastAbsorbed;
    write(aggFile, JSON.stringify(agg, null, 2) + '\n', 'utf8');
    write(shard, remainingLines.length ? remainingLines.join('\n') + '\n' : '', 'utf8');
  }
  return { absorbed, remaining: remainingLines.length, recoveredPrefix: start, aggregate: aggFile, shard };
}

export function parseArgs(argv) {
  const out = { vault: '.squidsquad/vault', instanceId: '', alias: '', horizonDays: 30, today: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--vault') out.vault = argv[++i];
    else if (a === '--instance-id') out.instanceId = String(argv[++i] || '').trim();
    else if (a === '--alias') out.alias = String(argv[++i] || '').trim();
    else if (a === '--today') out.today = argv[++i];
    else if (a === '--horizon-days') {
      const n = Number.parseInt(argv[++i], 10);
      if (Number.isFinite(n) && n >= 1) out.horizonDays = n;
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
  const stderr = deps.stderr ?? ((s) => process.stderr.write(s));
  const stdout = deps.stdout ?? ((s) => process.stdout.write(s));
  const args = parseArgs(argv);
  if (!args.instanceId || !args.alias) {
    stderr('usage: compact-telemetry.mjs --instance-id <uuid> --alias <alias> '
      + '[--vault <path>] [--horizon-days N] [--today YYYY-MM-DD]\n'
      + 'error: owner identity is required (6.5 invariant 1 -- owner-only compaction)\n');
    return 2;
  }
  const result = compact(args.vault, args.instanceId, args.alias, {
    todayISO: args.today || deps.todayISO || todayISO(),
    horizonDays: args.horizonDays,
    deps,
  });
  stdout(JSON.stringify(result, null, 2) + '\n');
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(main());
}

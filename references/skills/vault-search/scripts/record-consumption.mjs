#!/usr/bin/env node
// record-consumption.mjs — SquidSquad vault `used`-event recorder
// (#13857, PRD-VAULT-V2 P1).
//
// Forked from the reference system's record-consumption.mjs (dmp-web) and
// adapted to the SquidSquad telemetry contract (docs/VAULT-ARCH.md §6.1/§6.3/
// §8.5): the write is an append of `used` events to the CALLER'S own JSONL
// shard — never a note-frontmatter mutation. `used` is the strong consumption
// signal ("this note genuinely informed a committed artifact" — cited in a
// lineage file's receipt section, matched as a binding rule, relied on during
// implementation). It is written ONLY by consumers through this script; the
// search engine (vault-query.mjs) never writes it. The upstream `--counter
// impression` completeness mode is dropped — §8.5's record operation is `used`
// events, and impressions are the engine's own write.
//
// Usage:
//   node record-consumption.mjs --slugs a,b,c --task N
//        --instance-id <uuid> --alias <alias> [--vault <path>] [--no-write]
//
//   --slugs        comma-separated note slugs (filename stems, no `.md`). Required.
//   --task         tracker issue number the consumption belongs to. Required
//                  (per-task attribution is the point of the record op, §8.5).
//   --instance-id  harness instance UUID (shard identity). Required.
//   --alias        acting agent alias. Required.
//   --vault        vault root (default: .squidsquad/vault relative to CWD).
//   --no-write     dry run — resolve slugs and report, but append nothing.
//
// Output: one JSON object
//   { recorded: [...], unresolved: [...], events, shard, skipped }.
// A slug that matches no note is reported under `unresolved` (not an error —
// the caller may pass a slug that was renamed); exit stays 0. Missing
// --slugs / --task / --instance-id / --alias is exit 2, mirroring
// vault-query.mjs's arg contract.

import { pathToFileURL } from 'node:url';
import { listNotes } from './vault-query.mjs';
import { makeEvent, appendEvents, shardPath } from './lib/consumption.mjs';

// Split a repeatable/comma-bearing CLI list into trimmed, non-empty tokens.
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
  const out = { vault: '.squidsquad/vault', write: true, instanceId: '', alias: '', task: null };
  const slugs = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--vault') out.vault = argv[++i];
    else if (a === '--slugs') slugs.push(argv[++i]);
    else if (a === '--no-write') out.write = false;
    else if (a === '--instance-id') out.instanceId = String(argv[++i] || '').trim();
    else if (a === '--alias') out.alias = String(argv[++i] || '').trim();
    else if (a === '--task') {
      const n = Number.parseInt(argv[++i], 10);
      out.task = Number.isFinite(n) ? n : null;
    }
  }
  out.slugs = splitList(slugs);
  return out;
}

// Record a `used` event for each resolved slug by appending to the caller's
// shard. `deps` injects fs + clock/uuid for tests, exactly like
// vault-query.mjs. Returns the audit object.
export function record(vaultRoot, slugs, identity, deps = {}) {
  const doWrite = deps.write !== false;

  const bySlug = new Map();
  for (const n of listNotes(vaultRoot)) bySlug.set(n.slug, n);

  const recorded = [];
  const unresolved = [];
  const events = [];
  for (const slug of slugs) {
    if (!bySlug.has(slug)) {
      unresolved.push(slug);
      continue;
    }
    recorded.push(slug);
    events.push(makeEvent(identity.alias, identity.task, slug, 'used', deps));
  }

  let appended = 0;
  if (doWrite && events.length > 0) {
    appended = appendEvents(vaultRoot, identity.instanceId, identity.alias, events, deps);
  }
  return {
    recorded,
    unresolved,
    events: doWrite ? appended : 0,
    shard: shardPath(vaultRoot, identity.instanceId, identity.alias),
    skipped: !doWrite,
  };
}

const USAGE =
  'usage: record-consumption.mjs --slugs a,b,c --task N --instance-id <uuid> --alias <alias> [--vault <path>] [--no-write]\n';

export function main(argv = process.argv.slice(2), deps = {}) {
  const stderr = deps.stderr ?? ((s) => process.stderr.write(s));
  const stdout = deps.stdout ?? ((s) => process.stdout.write(s));

  const args = parseArgs(argv);
  if (args.instanceId === '' || args.alias === '') {
    stderr(USAGE + 'error: --instance-id and --alias are required (engine caller identity, VAULT-ARCH §8.5)\n');
    return 2;
  }
  if (args.slugs.length === 0) {
    stderr(USAGE + 'error: --slugs is required\n');
    return 2;
  }
  if (args.task === null) {
    stderr(USAGE + 'error: --task is required (per-task attribution, VAULT-ARCH §8.5)\n');
    return 2;
  }
  let result;
  try {
    result = record(
      args.vault,
      args.slugs,
      { instanceId: args.instanceId, alias: args.alias, task: args.task },
      { ...deps, write: args.write },
    );
  } catch (err) {
    // §9.9: telemetry write failure — report and exit 0; losing an event is
    // fine, blocking the caller's cycle is not.
    stderr(`warn: telemetry append failed (${err && err.message ? err.message : err}) — events dropped\n`);
    result = { recorded: [], unresolved: args.slugs, events: 0, shard: null, skipped: false };
  }
  stdout(JSON.stringify(result, null, 2) + '\n');
  return 0;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(main());
}

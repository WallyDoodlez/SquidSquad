# TEST-PLAN-13859

PRD-VAULT-V2 P3 — telemetry: event model, per-writer shards, ranking integration, impressions report, compaction (S3.1–S3.4). Derived independently from the issue body's story list + PRD-VAULT-V2.md §P3 + VAULT-ARCH.md §6.1–§6.5/§9.9 — not from skill's PR description. Per skill's own scoping note, S3.1 (event model/shards) and S3.2 (ranking integration) were substantially built in P1/P2; this round's genuinely new surface is S3.1's live two-clone concurrency AC + provisional instance-id mint, S3.3 (impressions report), and S3.4 (compaction).

## TCs

- **TC1 (S3.3, report bucketing)**: on an isolated scratch vault with 4 notes seeded with distinct telemetry event histories (zero events / impression-only / stale-used / recent-used), `vault-impressions-report.mjs` classifies each into exactly the right bucket (cold / surfacedNeverUsed / stale / healthy) per §4.4's definitions.
- **TC2 (S3.3, consumption AC)**: `vault_optimize.propose_prunes()` genuinely invokes the engine report as a subprocess and turns its buckets into real prune/review proposals — not a stub. Already-`archived`/`superseded` notes are excluded even when they'd otherwise bucket as cold.
- **TC3 (S3.3, engine-unavailable degrade)**: with `node` genuinely stripped from `PATH`, `propose_prunes()` degrades to an honest empty set with a reason, never an exception.
- **TC4 (S3.4, normal compaction)**: `compact-telemetry.mjs` on a shard with N old-enough events absorbs all of them into a fresh aggregate, truncates the shard to empty, and stamps `lastAbsorbedId` correctly.
- **TC5 (S3.4, kill-mid-compaction recovery)**: simulate the crash window (aggregate written, shard NOT truncated) plus one genuinely new event appended after the crash; a recovery run must positionally skip the already-absorbed prefix, absorb only the new event, and complete the truncation — no double-count.
- **TC6 (S3.4, read-side crash-window safety)**: `readTelemetry()` queried directly against a live crash-window state (aggregate absorbed, shard not yet truncated, one new event) — without any compaction run — must also avoid double-counting via the same exact-id positional boundary.
- **TC7 (S3.1, instance-id mint)**: `wizard.install_vault_engine()` mints a UUID into gitignored `.squidsquad/.instance-id` when absent; re-running is a no-op (mint-if-absent, never re-mints/orphans an existing writer identity); the file is confirmed invisible to `git status`.
- **TC8 (S3.1, two-clone concurrency — distinct shards)**: two real git clones, each writing its own uniquely-named shard via the engine, merge with zero conflicts; dedup-by-id holds at read (one `used` count per writer, not double-counted).
- **TC9 (S3.1, `.gitattributes` merge=union backstop — the AC's own listed deliverable)**: the documented §9.9 "same-shard divergence across machines (restored backup, cloned VM)" scenario — two clones both appending different lines to the exact SAME shard filename — must merge cleanly via `merge=union`, per the AC text itself ("`.gitattributes` `merge=union`"). Verify this protection is actually present in the **real, tracked repository state** (not just inside an isolated test's own throwaway scratch repo).
- **TC10 (S3.2, cold-start degrade)**: a scratch vault with a note but zero telemetry (no `.telemetry/` dir at all) still returns a valid, error-free tier+recency-ranked result.
- **TC11**: regression test suite (`test_vault_engine_13859.py` + adjacent P1/P2 vault test files) all pass.
- **TC12**: full ship gate (static + integration) passes clean.

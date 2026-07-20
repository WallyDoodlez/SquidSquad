---
name: vault-search
description: Search the SquidSquad vault (.squidsquad/vault) through the consumption engine — tiered match, budgeted wikilink traversal, telemetry-weighted ranking. Use for ANY vault lookup ("what do we know about X", "is there a decision/pattern/learning on X", dedup checks before vault writes). Never raw-grep the vault — grep leaves no telemetry trail and corrupts the maintenance signal.
---

# vault-search

Query the vault via the deterministic engine. The engine is the ONLY sanctioned
vault search path (VAULT-ARCH §6.2 raw-grep ban): a grep that finds the right
note leaves no `impression`/`used` trail, so the note reads as dead to the
impressions report and gets pruned.

## Instructions

1. Parse the caller's question into `--entities` (specific note/entity names),
   `--tags` (topic keywords), and/or `--terms` (free text). At least one is
   required.
2. Resolve your caller identity — both flags are REQUIRED on every call:
   - `--instance-id`: the harness instance UUID from
     `.squidsquad/.instance-id` (gitignored, minted by the harness). If the
     file is absent, use `unprovisioned`.
   - `--alias`: your own agent alias (your `SQUIDSQUAD_ROLE` value).
   - `--task`: the tracker issue number you are working, when in a task.
3. Run the engine (do NOT hand-execute the search):

   ```
   node .claude/skills/vault-search/scripts/vault-query.mjs \
        --instance-id <uuid> --alias <alias> [--task N] \
        [--vault .squidsquad/vault] [--entities a,b] [--tags x,y] \
        [--terms "free text"] [--top N] [--no-write]
   ```

4. The output is metadata-only JSON (`results` + `traversed`, ranked; no note
   bodies). Read the note bodies you actually need with the Read tool, then
   synthesize.
5. If a surfaced note genuinely informs a committed artifact (cited in a
   receipt section, matched as a binding rule, relied on in implementation),
   record the consumption — the engine cannot do this for you:

   ```
   node .claude/skills/vault-search/scripts/record-consumption.mjs \
        --slugs a,b,c --task N --instance-id <uuid> --alias <alias>
   ```

## Output Format

`vault-query.mjs` prints one JSON object:

```json
{
  "query": {"entities": ["auth"], "tags": [], "terms": []},
  "results": [
    {"slug": "decision-auth-flow", "path": "galaxy/decision-auth-flow.md",
     "folder": "galaxy", "type": "decision", "status": "active",
     "tier": "filename", "direct": true, "score": 2.75,
     "title": "Auth flow decision", "updated": "2026-07-19",
     "used": 1, "impression": 3, "walkedTotal": 0,
     "lastUsed": "2026-07-18", "linksOut": ["hub-auth"]}
  ],
  "traversed": [
    {"slug": "hub-auth", "tier": "walked", "direct": false,
     "walkedFrom": ["decision-auth-flow"], "...": "..."}
  ],
  "written": {"events": 2, "shard": ".squidsquad/vault/.telemetry/<id>-<alias>.jsonl", "skipped": false}
}
```

## Constraints

- Never grep/glob/Read-scan the vault folders to search — the engine is the
  implementation. (Reading a specific note body surfaced by the engine is the
  intended follow-up, not a violation.)
- Never write telemetry by hand; never edit `.telemetry/` shards other than
  through the engine scripts.
- Pass `--no-write` for diagnostic/side-effect-free searches (tests, CI,
  debugging) — telemetry must measure real consumption only.
- Exit 2 means the call was malformed (missing identity or query) — fix the
  invocation, do not fall back to grep.
- If `node` is unavailable or the engine fails, degrade honestly per
  VAULT-ARCH §9.9: state "engine unavailable" in your receipt line — never
  fabricate "none relevant", never substitute a manual search.
- `BRIEFING.md` is outside the engine (read it directly, no telemetry).

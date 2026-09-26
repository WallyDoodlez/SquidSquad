# QA-RESULTS-14123 — PASS (docs; main @ 5b24a1b16)
- AC1: literal count 1, not 0. Sole hit = the AC5-mandated change-history entry (VAULT-ARCH.md:714) describing the old behavior; no operative text uses it.
- AC2 PASS: 1 hit, line 469 inside 7.2. AC3 PASS: line 468 names direct, filename/wikilink/tag, status active, Jaccard slug+title+tags, dedupThreshold, 0.5, --no-write.
- AC4 PASS: 0 hits; 9.5 item 2 cites 7.2 merge-target test. AC5 PASS: entry dated 2026-09-26 citing #14123 (line 714).
- AC6: literal grep returns 3 lines: 468/469 (the 7.2 text incl. negative statement), 714 (history), 419 (false positive: "dedupes by id" in telemetry read path). No operative instruction treats Stage-2 as dedup signal; docs/references/sub-skills clean.
- AC7 PASS: PRD-VAULT-V2 S4.4 cites merge-target test, unrelated/content-tier-only/archived -> new note, probe -> zero telemetry.
- Static gate: 6351 tests; sole failure was staleness of 9184_spec vs Monitor-only recompose of qa/skill CLAUDE.md (unrelated to 14123) — baseline refreshed per precedent 4fd775750; staleness suite 10/10.
- Note: AC1/AC6 literal counts conflict with AC5 by construction; judged on intent, disclosed on the issue.

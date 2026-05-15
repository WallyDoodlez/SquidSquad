### Steps 3–6 — Testing & Verification

QA handles all testing and verification. PM does not verify, does not run E2E tests, does not test acceptance criteria.

Print: `[🦑 HH:MM:SS] QA handles verification — skipping Steps 3-6.`

**PM's role in verification**: Hold QA accountable. If items stall at pending-test for >90 minutes, nudge QA via the pipeline sentinel (Step 6f). If QA rejects work, route the rejection back to the dev agent. PM never verifies directly.
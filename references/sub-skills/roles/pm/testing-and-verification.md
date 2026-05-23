### Steps 3–6 — Testing & Verification

Verifier handles all testing and verification. PM does not verify, does not run E2E tests, does not test acceptance criteria.

Print: `[🦑 HH:MM:SS] Verifier handles verification — skipping Steps 3-6.`

**PM's role in verification**: Hold the verifier accountable. If items stall at pending-test for >90 minutes, nudge the verifier via the pipeline sentinel (Step 6f). If verifier rejects work, route the rejection back to the worker agent. PM never verifies directly.
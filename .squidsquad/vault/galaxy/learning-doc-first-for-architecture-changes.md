# Learning: doc-first for architecture changes

**Date:** 2026-06-14 · **Author:** pm · **Type:** learning

## What happened

During the harness reboot firefight, #12244 (crash-loop backoff) was **built and merged (PR #12293) before HARNESS-ARCH was correct and human-reviewed.** PM had to reconcile the doc to the shipped code retroactively (v7 contradiction-polish, then v8 post-merge sync). The operator's verdict: "the steps went wrong."

## The principle

For **architecture-level changes**, the correct, human-reviewed documentation (TRD) must exist **first**; implementation follows. Impl-first means the doc races to catch up to code and contradictions slip in (the v7 polish existed only because §7.6 escape hatches were undocumented while §7.1/§7.3/§7.4 read auto-respawn as unconditional — a direct doc-vs-code contradiction introduced by shipping ahead of the doc).

## The remedy — "work discovery" mode (PM, all roles; → L2)

Draft PR holds WIP docs → Research + human inquiries → **emphasize human review** → adjust doc → DS internal audit on the modified doc → cross-ref audit on related docs → human "all good" → break into worker tasks. Mechanics under discussion in **#12300** (do not codify into L2 until refined). #12271 (liveness redesign) is the first change run correctly: doc written, pending review, no tasks yet.

## Contrast

The cause-agnostic backoff (#12293) was still the *right* implementation — the failure was the ordering, not the code. Doc-first is about sequence and review gates, not about slowing good work.

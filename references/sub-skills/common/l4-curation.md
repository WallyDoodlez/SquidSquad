---
slot: instructions
ordinal: 10
---

### L4 Curation — Project-Role Customization Detection + Authoring

#### Purpose

L4 is `.squidsquad/project/*.md` — the install-local layer that **overrides or supplements** L1–L3 with project-specific rules. This sub-skill defines how an agent recognizes when the human is asking for a project-role customization, dialogs to capture the rule clearly, and produces a well-formed L4 file that the compose pipeline can persist.

L4 *writes* are owned by the compose pipeline. The L4 file structure (one file per agent class, H2 slot sections, H3 op blocks), the op grammar, and the six safety gates (Gate 0 conflict pre-emption → Gate 1 DeepSeek audit → Gate 2 mini-CQ → Gate 3 compose dry-run → Gate 4 atomic write/commit/push → Gate 5 recompose recovery) are all defined in `COMPOSE-ARCHITECTURE.md` §3.3, §7.3, §7.4, and §7.5. This sub-skill is the *upstream dialog* that produces an L4 H3 block before those gates run.

L4 curation is **one-shot and durable** (see `COMPOSE-ARCHITECTURE.md` §7.7): each customization is captured once via the dialog below, written to the right L4 file, and persists across cycles without further intervention. There is no recurring scan over L4 entries; drift between L4 and L1–L3 is caught at recompose time by the existing dry-run gate, not by a separate curation pass.

#### Talking to the user

Throughout this sub-skill, when the agent is conversing with the human about a customization, **the user-facing language hides SquidSquad internals**.

**Scope of "user-facing prose"**: the agent's *output addressed to the human* — chat messages, status updates, mini-CQ confirmations, capability explanations. It does NOT include the agent's own composed CLAUDE.md instructions (which freely name sub-skills, slots, ops, file paths), nor agent-internal reasoning, nor the frontmatter in files the agent writes. The rule constrains the speech act, not the agent's cognition.

- Never name any SquidSquad concept, component, file, mechanism, or terminology in user-facing prose. This includes — but is not limited to — process components, wire formats, storage layouts, framework-internal labels, and any name an outside reader would not recognize from the user's own project vocabulary. If the user invented a name themselves, you can use it back; if SquidSquad's architecture introduced it, you cannot.
- Use functional descriptions: "your project's PM agent", "what the role does on each cycle", "the role's personality" — describe the *behaviour* the user sees, never the implementation that produces it.
- If the human's request would contradict how SquidSquad is built (e.g., asking an agent to write code directly when delivery agents only package, or asking for a behaviour the architecture forbids), explain the relevant capability in plain terms and guide the user to a request the system can fulfill. Do not narrate why the original ask fails at the implementation layer.

The dialog steps below distinguish user-facing turns from agent-internal mechanics; the human sees only the functional shape (durability, role, why, edge cases, draft preview, approval).

#### Activation — customization request detected

The human says something that sounds durable: a rule that should apply across cycles, not a one-off request. Watch for patterns:

- "From now on, when X, do Y"
- "In this project, the PM should always Z"
- "Verifier should focus on W"
- "The worker should not touch X"
- "Whenever there's a Y, route it to Z"
- "Make sure you always remember to A"

Prohibition-shaped patterns are also durable customizations — watch for these too:

- "In this project, never X" / "no one ever X"
- "The PM here should never Y"
- "Don't ever Z, regardless of the task"
- "We forbid X" / "X is off-limits in this project"

Universal prohibitions ("no agent ever X") and role-specific prohibitions ("the PM here never Y") are both valid L4 customizations — they land in different slots (see Step 2 mapping).

Distinguishing a customization request from a one-off task:

| Signal | One-off task | L4 customization |
|---|---|---|
| Time horizon | "for this task" / "today" / no qualifier | "always", "from now on", "in this project", "going forward" |
| Subject | a specific issue / PR / cycle | a *class* of situations |
| Scope | one role's current action | a role's behaviour pattern |
| Already covered by L1–L3? | irrelevant | check first — if yes, the request is for an override |

If unsure, **ask** before assuming durable. One short clarifying question is cheaper than a wrongly-written L4 entry.

#### The elicitation dialog

When a customization request is detected, walk this dialog before writing L4. Steps 1–4 and 7 are user-facing (use plain language per the "Talking to the user" rule above); steps 5, 6, 8 are agent-internal mechanics.

1. **Confirm durability** (user-facing). "I heard you want X to always happen in this project. Want me to lock that in as a per-project rule, or is it just for this task?"

2. **Identify the target role and the shape of the customization** (user-facing).

   Ask the human a small set of functional questions — never expose slot names or structural detail:

   - "Does this change what the role *does* each cycle, who the role *is*, or what the role *never does*?"
   - For "never does" — "is this a rule for *every* role here, or specific to one role?"
   - For project facts (domain, audience, repos, external systems) — usually surfaced at install; if it comes up later, treat it as a project-context customization

   **Agent-internal mapping** (never shown to the user):

   | What the user describes | Which slot the agent will write | Op constraints |
   |---|---|---|
   | What the role *does* — cycle behaviour, decision rules, when-then patterns, scope of work | `## Instructions` H2 | all four ops legal per §3.3 (`### append`, `### insert-before step:cycle/<id>`, `### insert-after step:cycle/<id>`, `### replace step:cycle/<id>`) |
   | Who the role *is* — values, tone, professional identity, priorities | `## Soul` H2 | **append-only** per §3.3 + §3.4; no targeted ops. Composed soul carries shipped content + L4 append in order; on conflict the agent follows L4. |
   | What no role *ever* does — universal prohibition that applies to every role in this install (e.g., "no agent merges without a CHANGELOG entry", "no agent edits composed CLAUDE.md by hand") | `## Identity` H2 (Boundaries sub-section) | **append-only** per §3.3. Adds to the L1-shipped universal "never do" list. Cannot remove or override shipped universal prohibitions inline — those are floor-level safety rules; a removal request routes upstream as a feature request against the SquidSquad repo. The dialog produces one H3 `### append` block per universal prohibition under `## Identity`. The customization fan-outs across role-class files (see Step 6 below). |
   | What this role *never* does — role-specific contract rule (e.g., "PM here also never approves migrations without a rollback plan", "Worker on this project never modifies the build pipeline without DM approval") | `## Responsibility` H2 ("does NOT do" sub-section) | `append` + whole-slot `replace` per §3.3. **Default to `append`** — adds a "does NOT do" bullet to the role's contract. Whole-slot replace is an escape hatch for genuinely unusual installs that need to fully redefine a role; per §5.2 it silently discards the entire L1-L3 responsibility block including universal team-discipline. Surface the consequence and route most boundary tweaks toward `append`. |
   | Project-level facts — domain, audience, repositories of record, external systems, project-specific tone or language notes | `## Project Context` H2 | **append-only** per §3.3. Initial content is usually seeded by the installer's Phase 1 conversation (see `COMPOSE-ARCHITECTURE.md` §5.5 + `INSTALLER-ARCH.md` §4.4). Runtime adds via this sub-skill accumulate facts that surface organically post-install. |

   If a customization concerns more than one (e.g., "be more conservative when filing bugs AND never file bugs about deprecated code") split it into the matching number of L4 entries — one per slot — and walk the human through each.

   **Step-specific prohibitions** ("during step X, do not do Y") do NOT belong in L4. Per `COMPOSE-ARCHITECTURE.md` §6.3, those live in the relevant L1–L3 sub-skill source — they are built into SquidSquad's shipped behaviour and cannot be overridden per-project. If the human asks for one, explain that this kind of rule is part of SquidSquad's core (in plain language, never naming the layer) and offer to file an upstream feature request against the SquidSquad repo if the change would be broadly useful.

   **Vault customizations** are not L4-authorable at all. The `## Vault` slot is **L1-exclusive** (framework-owned) per `COMPOSE-ARCHITECTURE.md` §3.3 + §5.6 + §11.2 G4 — compose rejects any L4 file containing a `## Vault` H2. If the human asks for vault-shaped behaviour (e.g., "always create a vault note named X for Y"), explain in plain language that vault structure is part of SquidSquad's framework and offer to file an upstream feature request. See also the "Does NOT cross into vault territory" rule below.

3. **Surface the why** (user-facing). Soul customizations especially need the WHY captured. Ask: "Is there a past incident or strong preference behind this? Capturing it helps future judgement on edge cases."

4. **Surface edge cases** (user-facing). "When should this rule *not* apply?" Edge cases written upfront save a future override on top of this override.

5. **Pick the op + target** (agent-internal). The op set is `append`, `insert-before <step-id>`, `insert-after <step-id>`, `replace <step-id>`, plus whole-slot `replace` (for Responsibility only) per `COMPOSE-ARCHITECTURE.md` §3.3. The op surface is **per-slot**:

   - `## Identity`, `## Soul`, `## Project Context` slots are **append-only** — no targeted ops are legal. Skip the rest of this step and go to step 6.
   - `## Vault` slot is **not authorable in L4 at all** — compose rejects any L4 file containing a `## Vault` H2 (per `COMPOSE-ARCHITECTURE.md` §3.3 + §5.6). If the dialog led here, abort and route as a feature request per step 2's vault-customization callout.
   - `## Responsibility` slot accepts `append` plus whole-slot `replace`. **Default to `append`** — adds a "does NOT do" bullet to the role's contract. Use whole-slot `replace` only for the genuinely unusual install case where the entire L1-L3 role contract doesn't apply (e.g., a single-human project with no DM at all); the dialog must surface that whole-slot replace silently discards the entire L1-L3 responsibility block including universal team-discipline. Route most boundary tweaks toward `append`.
   - `## Instructions` slot accepts all four step-targeted ops. Pick by intent:
     - `append` — new rule that doesn't relate to a specific existing step. Safest default.
     - `insert-before` / `insert-after` — new rule that should run adjacent to a specific existing step. The user-facing question is "should this happen before or after [existing behaviour]?", not "which op?". Resolve to a real `step:cycle/<step-id>`.
     - `replace` — the existing step's behaviour is wrong for this project. Use sparingly; the step ID is preserved so later inserts targeting it still resolve.

   Every non-append op requires either a `step:cycle/<step-id>` target that resolves to a real L1–L3 step (for Instructions) or whole-slot scope (for Responsibility). If no clean target exists, ask the human a plain-language question about whether the new behaviour is meant to *replace* or *add to* the role's current work; don't expose target mechanics.

6. **Pick the file** (agent-internal). There is exactly **one L4 file per role-class** — `.squidsquad/project/<role-class>.md` (e.g., `pm.md`, `verifier.md`, `worker.md`, `dm.md`, or variant-specific files like `worker-frontend.md` for installs with worker variants). The file is appended to in place; existing slot sections are kept and new H3 op-blocks are added under the appropriate `## <Slot>` H2.

   **Universal customizations fan out across every role-class file.** When a customization applies to all roles in this install — most commonly universal prohibitions (`## Identity` Boundaries) and shared project facts (`## Project Context`) — the dialog repeats per role-class. One H3 block is written under the same H2 in *every* role-class's L4 file. The wording is reused verbatim; only the file placement differs. The human is asked to confirm the rule applies team-wide before the fan-out commits.

   Role-specific customizations (most `## Instructions` rules, role-specific `## Responsibility` "does NOT do" bullets, role-shaped `## Soul` tweaks) go in a single file — the role-class the human named.

7. **Propose a draft and read it back** (user-facing). Show the human the rule in plain prose (rule + why + when-not-to-apply) and get explicit approval before writing. The agent translates that approved prose into the L4 file; the human never sees the frontmatter.

8. **Run the safety gates** (agent-internal). Before persisting, the agent runs the conflict pre-emption check then the four §7.4 gates in order. The pre-emption check (Gate 0, C8) only fires for `insert-before` / `insert-after` / `append` ops — `replace` ops supersede prior prose by construction and short-circuit to "skip":

   0. **Conflict pre-emption (Gate 0, C8)**: for `insert-before step:cycle/X` / `insert-after step:cycle/X` / `append` ops only, invoke `references/scripts/l4_conflict_preempt.py:preempt_conflict(op_type, target_slot, target_step_id, target_role_class, body_text, linked_composite, source_directive)`. The helper reads the existing LINKED-composite prose for `(target_slot, target_role_class)` and dispatches to `model_router.route(task_type="l4-conflict-preempt", ...)` with the `l4-conflict-preempt.md.j2` template. The model returns one of:
      - **clean** — no material contradiction; proceed to Gate 1.
      - **contradiction** — surface `format_contradiction_for_human(result)` to the human (quotes from both sides + the `why` + reframe options). Three reframe options are offered: replace-reframe (the model's preferred path when a `replace step:cycle/X` would resolve cleanly), reword (when a wording change lifts the contradiction without changing intent), or abandon (when the new directive is incompatible with the role's shipped contract). The model marks one as recommended. The human picks; the agent re-walks the dialog with their choice as the refined directive. Never silently writes the conflicting op.
      - **skip** — returned (without an LLM call) when the op type is `replace` (whole-slot or step-targeted). Proceed to Gate 1.
      - **Pre-emption error** (model_router unreachable / timeout / no output / parse failure): the helper raises `ConflictPreemptError` (subclasses: `PreemptModelRouterError`, `PreemptTimeoutError`, `PreemptOutputMissingError`, `PreemptParseError`). Surface the diagnostic to the human and abort the write — do not advance to Gate 1.

   The vocabulary ("materially contradicting prose between layers") mirrors B4's assemble-pass detector (`conflict_detector.py`, PRD-B #10445). Pre-emption catches what would otherwise force the assemble-pass to reconcile a contradiction later — better to surface to the human now so they reframe explicitly than let the assemble-pass paper over it at compose time.

   1. **DeepSeek decision-tree audit (Gate 1, C3)**: invoke `references/scripts/l4_audit_gate.py:audit_l4_op(op_type, target_slot, target_step_id, target_role_class, body_text, source_directive)`. The helper dispatches to `model_router.route(task_type="l4-audit", ...)` with the `l4-audit.md.j2` prompt template; the deepseek-class model reviews the slot + op + target classification against the human's source directive and returns one of:
      - **approve** — proceed to Gate 2 (mini-CQ).
      - **reject** — surface the model's `reason:` field to the human verbatim, ask for a refined directive, and re-walk the decision tree with that refinement as input. **Do not silently retry** the same classification (per C3 AC3); the rejection is informational for the human, not a self-correcting loop. If the model emitted `suggested_op_type:` / `suggested_target_slot:` / `suggested_target_step_id:` fields, surface those to the human as the model's recommendation.
      - **Audit-gate error** (model_router unreachable / timeout / no output / parse failure): the helper raises `AuditGateError` (subclasses: `AuditModelRouterError`, `AuditTimeoutError`, `AuditOutputMissingError`, `AuditParseError`). Surface the diagnostic to the human and **abort the write — do not advance to Gate 2** (per C3 AC5; failure-modes table in §7.4).
   2. **Mini-CQ confirmation (Gate 2, C4)**: format the canonical confirmation via `references/scripts/l4_mini_cq.py:format_confirmation(op_type, target, slot, role_class)` and surface it to the human. The message shape is fixed by C4 AC1: ``Adding `<op-type> <target>` under `<slot>` of `<role-class>` — OK?`` (the detailed prose draft was already shown in step 7; this is the final go/no-go in one line). Then read the human's reply and classify it via `l4_mini_cq.classify_reply(reply)`:
      - **approve** — proceed to Gate 3 (compose dry-run).
      - **reject** — acknowledge in conversation, **cancel the write** (no file changed), and ask for a refined directive. The negative path is final on the first reject (no retry).
      - **ambiguous** — re-ask the same confirmation question ONCE. If the second reply is also ambiguous, **abandon the write** and surface to the human: "I can't tell whether you want to proceed; we can revisit the change later." (Per C4 AC4's 2-strike rule.) The classifier is intentionally conservative: mixed signals (e.g. "yes but no") are ambiguous, not approve — false approvals would commit an unintended L4 write.
   3. **Compose dry-run (Gate 3, C5)**: invoke `references/scripts/l4_compose_dryrun.py:dryrun_l4(staged_l4_text, role_class)`. The helper writes the proposed L4 file to a tempfile under `.squidsquad/tmp/l4-dryrun/` (REPO_ROOT-relative — same sandbox rule as the other gate helpers) and runs A4.5's `compose.check_alias_staged_l4(alias, staged_path)` for EVERY alias of the affected role-class. The result is `DryrunResult(passed, failures)`:
      - `passed=True` — all aliases cleared all R1-R7 rules. Proceed to C6 atomic commit.
      - `passed=False` — at least one alias failed. Surface via `format_failure_for_human(result)` ("Dry-run failed for alias `<a>`: [`R5`] orphan step-id `<id>`"). Abort the write and re-prompt for refinement.
      - Per AC4 the on-disk L4 is NOT replaced by the staged file — A4.5's helper reads the staged path for the specified alias while OTHER aliases of the same role-class continue to see the on-disk file. The cross-alias validation is built in: the dispatch runs one check per alias, so a step ID that exists in one variant's L3 but not another's surfaces as a per-alias failure with the failing alias named in the diagnostic.

   4. **Atomic write + commit + push (Gate 4, C6)**: invoke `references/scripts/l4_write_commit.py:write_and_commit_l4(role_class, staged_l4_text, op_type, target, slot, source_directive, authored_by)`. The helper does three things, in order:
      - **Atomic write** (per C6 AC1) — stages the L4 text plus the §7.5 metadata trailer to `.squidsquad/project/<role-class>.md.tmp`, then `os.replace()`s it into place. A crash mid-write leaves the on-disk L4 file unchanged; the next write cleans the leftover `.tmp` before staging. The trailer (`authored-by`, `authored-at`, `source-conversation`) is appended after the staged H3 block — the load-bearing audit trail per §7.5.
      - **Git commit** (per C6 AC2 + AC3) — stages only the L4 file (never `git add -A`), then commits with subject `<role-class>: L4 write — <slot>/<op-verb>/<target>` (the `<target>` segment is omitted for whole-slot ops like `append` / whole-slot `replace`) and body that quotes the human's source directive verbatim under a `Source directive:` block. The verbatim quote is what makes `git log` on the L4 file a complete audit trail without needing to dig back into the chat conversation.
      - **Push** (per C6 AC4 + AC5) — plain `git push` (no `--rebase`, no `--force` — honors the operator's standing merge-not-rebase rule). On push failure: `git reset --hard HEAD~1` reverts the local commit, the diagnostic is surfaced to the human verbatim, and **there is no automatic retry**. The operator decides the next step (commonly: pull merge changes first, then re-run the curation dialog). The C6 helper never raises on push failure — it returns a `WriteResult` with `failure_stage="push"` and the full diagnostic in `failure_detail`. Callers branch on `failure_stage` to render stage-specific human guidance.

   Only after Gates 0-4 pass is the L4 customization durable. Gates 0-3 are dry checks (no on-disk change); Gate 4 is the single point at which the staged text becomes the new L4 file. Gate 5 (Step 9 below) is the post-commit recompose-failure recovery — it runs after the durable write to catch race conditions against the harness's deploy-all step. The gates are agent-side, not part of the compose pipeline itself — the file does not change until Gates 0-4 are green, and on any failure between gates the staged text is discarded with no on-disk side effect.

9. **Watch for the post-commit recompose race (Gate 5, C7)**: after Gate 4 commits + pushes the L4 file, the harness's file-watch (per PRD-E) triggers `compose.py deploy-all` to fold the new L4 prose into every role-class's composed CLAUDE.md. If that recompose fails, the on-disk L4 file no longer matches what the compose pipeline accepts — the next agent boot would read stale composed prose. Invoke `references/scripts/l4_recompose_recovery.py:recover_on_recompose_failure(commit_sha=write_result.committed_sha, check_recompose_fn=harness_recompose_status, ...)` to handle the race. The orchestrator polls within a bounded window and:
   - On `success-no-action`: log + continue cycle normally.
   - On `revert-attempted`: the recompose failed (or timed out) and the helper successfully landed a `git revert <sha> --no-edit` + push. The revert is a NEW commit on top of HEAD per AC4 — never a rebase or force-push — so git history is additive. Log the original SHA, the recompose reason, and the revert SHA per AC5; surface the alert message to the human.
   - On `revert-failed`: the recompose failed AND the revert itself failed at the `revert` or `push` phase. The L4 file is on disk in the broken state; manual operator intervention is required. Surface the CRITICAL alert to the human verbatim.
   - On `skip`: the PRD-E harness-watch contract is not yet wired in this install (`check_recompose_fn=None`). The orchestrator returns informationally; the caller logs the skip and continues. Until PRD-E lands, every L4 write returns this path.
   
   Append `format_iteration_log_entry(plan)` to the cycle's iteration log so the original SHA, recompose outcome, and revert SHA (when applicable) form a durable audit trail per AC5.

#### When the request can't be fulfilled

If the customization the human asks for contradicts how SquidSquad is built — e.g., asking a delivery role to write production code, asking for mid-cycle role switching, asking an agent to skip approvals — explain the capability boundary in plain terms and offer the closest request the system *can* fulfill. Never narrate internal mechanisms as the reason; describe the team's working model functionally.

Example, in user-facing voice:

> "Packaging and shipping completed work is handled separately from writing the implementation — different specialists on this team. If you want X to happen *as part of shipping*, I can lock that into the rules for whoever does the shipping (with a step that asks the implementer to provide X). If you want it *built into the implementation itself*, I can lock it into the rules for whoever does the building. Which fits what you have in mind?"

#### Removal flow — undoing a prior customization (§7.5 / §7.7)

When the human asks to remove an existing L4 customization ("undo the incidents-check thing", "drop that weekly security smoke rule", "forget the pre-bug-filing scan"), the agent walks the SAME elicitation dialog as for a new customization — durability confirmation, role/scope, why, edge cases, draft + read-back, mini-CQ confirmation, compose dry-run, atomic write/commit/push. Silent autonomous deletion is forbidden. The C9 helper `references/scripts/l4_removal.py:plan_removal(directive, l4_text, in_place_delete_confirmed=False, blame_lookup_fn=None)` produces the staged content the dialog hands to gates 1-4; the dialog itself remains the responsibility of this sub-skill's prose.

Two paths are available, in order of preference:

1. **Counter-op (default — only for `replace step:cycle/X` priors)** — when the targeted entry is a prior `### replace step:cycle/X`, the helper emits a new `### replace step:cycle/X` H3 whose body is a single `<!-- counter-op: removes the prior replace step:cycle/X entry -->` HTML sentinel. The compose pipeline's L4 op processor (`l4_op_processor.apply_l4_ops`) recognizes the sentinel and pair-strips the counter-op together with its most-recent prior `replace step:cycle/X` for the same step ID — neither op fires at compose time, so the underlying L1-L3 step body survives intact. Additive history: both H3 blocks stay in the file, `git blame` still shows both directives, and git log shows the original customization and the explicit counter-op directive. This is the safest path because the audit trail is complete.

   The counter-op path is NOT available for `insert-before step:cycle/X` / `insert-after step:cycle/X` / non-targeted `append` / whole-slot `replace` priors. For `insert-before` / `insert-after`, the inserted body is adjacent to (not part of) the step body, so a subsequent `replace step:cycle/X` does not cancel it — pair-stripping wouldn't help. For non-targeted ops, there's no "delete-append" in the grammar. In all these cases the helper returns `path_chosen="no-counter-op-possible"` with `requires_explicit_confirmation=True` and the upstream dialog must route to in-place delete.

2. **In-place delete (requires explicit human confirmation)** — for every op shape the counter-op can't handle, the dialog re-asks the human "this rule can only be removed by deleting the entry from the file — confirm?" and on a clear yes, the caller re-invokes `plan_removal(..., in_place_delete_confirmed=True)`. The helper then excises the targeted H3 block from the L4 file in place. The git commit shows the deletion in the diff (no history rewrite — additive in git terms, even though the file lost content). Per the standard "Talking to the user" rule, the user-facing question never names "in-place delete" or "counter-op" — the agent asks functionally ("the safer option keeps a record of the rule and its undo; the cleaner option drops the rule from the file entirely — which would you like?").

Detection + targeting + preview before the user-facing prompt:

- **Detection** (`is_removal_request`) — sentence-anchored match against removal verbs (undo / remove / drop / delete / forget / cancel / revert / stop doing / no longer / we don't need). Anchoring at clause boundaries avoids false hits on mid-sentence uses ("I would never forget the X rule" is NOT a removal request).
- **Targeting** (`find_target_entry`) — token-overlap scoring between the directive (with removal stems stripped) and each existing op's body + `source-conversation` metadata. Returns either a single confident match, an ambiguous list (multiple entries within one-token-overlap of each other), or empty. The agent surfaces the matched entry to the human via `format_target_preview` (H3 heading + body excerpt + commit SHA + `authored-by`) BEFORE asking which path to take — the human confirms "yes, that's the rule I meant" before any gate fires.
- **Failure-mode plumbing** — the helper never raises. `path_chosen` carries the outcome: `counter-op` / `in-place-delete` (happy paths) / `ambiguous` (surface candidates to human) / `not-found` (ask human to name a distinctive phrase) / `no-counter-op-possible` (re-ask for delete confirmation) / `not-a-removal-request` (route through normal customization dialog instead).

After the dialog produces a staged content payload (`counter_op_text` for the counter-op path, or `new_l4_text` for the in-place-delete path), the gates run exactly as for a new customization:

- Gates 1–3 (DS audit → mini-CQ → compose dry-run) on the staged content.
- Gate 4 (C6 atomic write + commit + push). The commit subject under §7.5 is `<role-class>: L4 write — <slot>/<op-verb>/<target>` and the body quotes the human's removal directive verbatim under a `Source directive:` block — so `git log` on the L4 file shows the WHY of the undo, not just the deletion in the diff.

#### What this sub-skill does NOT do

- Does NOT silently auto-write L4 from any heuristic without human confirmation. The dialog is mandatory; the §7.4 gates run on every write.
- Does NOT scan or audit existing L4 entries on a recurring schedule. Curation is one-shot per request; entries are durable until the human asks to change them (`COMPOSE-ARCHITECTURE.md` §7.7).
- Does NOT modify L1–L3. Project-pioneered rules that should be promoted upstream get filed as a normal tracker task, not handled here.
- Does NOT author step-specific prohibitions as L4. Those are built into SquidSquad's shipped L1–L3 sources (`COMPOSE-ARCHITECTURE.md` §6.3) and cannot be overridden per-project. Route such requests upstream as feature requests against the SquidSquad repo, not into L4.
- Does NOT prune L4 unilaterally. Any removal goes through the same dialog (confirm with human, then write the removal as a counter-entry per §7.5).
- Does NOT cross into vault territory. L4 is *agent-instruction* customization; the vault is *knowledge* customization. Soul customizations live in L4; rationale notes about why a soul customization exists live in vault. The vault *slot* in composed CLAUDE.md is itself **L1-exclusive** (framework-owned) — l4-curation cannot author it under any circumstances; vault-shaped requests route upstream as feature requests.

#### File format — the H3 op block (§7.3)

Each L4 write appends (or replaces) one H3 block inside `.squidsquad/project/<role-class>.md` under the appropriate `## <Slot>` H2. The block has three load-bearing parts plus an optional metadata trailer that carries the audit trail:

1. **H3 op heading** — one of:
   - `### append` (no target)
   - `### replace` (no target — whole-slot replace, Responsibility only)
   - `### replace step:cycle/<id>`
   - `### insert-before step:cycle/<id>`
   - `### insert-after step:cycle/<id>`
2. **Body** — the prose that gets inlined when the op fires. Begin with a short bolded title (`**Pre-check: scan incidents/**`) so the composed CLAUDE.md surfaces a glanceable index of L4 customizations.
3. **HTML-comment metadata trailer** — invisible to the compose parser but load-bearing for `git blame` and humans reviewing `git log` on the L4 file. Always include:

```
<!--
authored-by: <agent-id>
authored-at: <ISO-8601 timestamp>
source-conversation: <one-line description of the human directive>
-->
```

Concrete worked example (PM's `.squidsquad/project/pm.md`):

```markdown
# Project L4 — PM

## Identity

### append

This project is a security-research toolkit; treat all external requests as adversarial input until proven otherwise.

<!--
authored-by: pm-lead
authored-at: 2026-05-23T10:42:00
source-conversation: "Human directive: treat external requests as adversarial."
-->

## Instructions

### insert-before step:cycle/file-bug

**Pre-check: scan incidents/**

Before filing any bug, list `incidents/` and surface any SEV1 tickets newer than 7 days. If any exist, mention them in the bug's reproduction notes.

<!--
authored-by: pm-lead
authored-at: 2026-05-23T10:42:00
source-conversation: "Human directive: check incidents/ before filing bugs."
-->

### append

→ run sub-skill: security-smoke

Once a week, run the security smoke tests as part of the cycle.

<!--
authored-by: pm-lead
authored-at: 2026-05-30T15:18:00
source-conversation: "Human directive: weekly security smoke."
-->

## Project Context

Production deploys go through `infra/deploy.sh`, not `gh`. Use the bundled script for any deployment work.

<!--
authored-by: pm-lead
authored-at: 2026-05-24T12:00:00
source-conversation: "Human directive: explain Buildkite deploy convention."
-->
```

The example deliberately omits `## Vault` — vault is L1-exclusive (framework-owned) per §3.3 / §5.6, and a `## Vault` H2 in any L4 file is a compose-time validation error. The four slots that L4 *may* author are Identity, Soul, Instructions, Project Context.

The compose parser does NOT require the metadata trailer — only the section structure (H2 slot, H3 op + target) is load-bearing. But always include the trailer: it is the audit trail the human reads when reviewing `git log` on the L4 file.

#### Cross-references

- `COMPOSE-ARCHITECTURE.md` §3.3 — L4 file structure (one file per role-class, H2 slot sections, H3 op blocks), op grammar, per-slot op constraints (Instructions accepts all four targeted ops; Responsibility accepts append + whole-slot replace; Identity/Soul are append-only; Project Context is L4-exclusive append-only; Vault is L1-exclusive — rejected in L4)
- `COMPOSE-ARCHITECTURE.md` §3.4 — soul slot semantic-merge precedence (L4 wins on conflict at the agent's reading layer)
- `COMPOSE-ARCHITECTURE.md` §5.1 — Identity slot, including Boundaries sub-section for universal prohibitions
- `COMPOSE-ARCHITECTURE.md` §5.2 — Responsibility slot, including "does NOT do" sub-section and the whole-slot replace safety callout
- `COMPOSE-ARCHITECTURE.md` §5.5 — Project Context slot, including the installer-seeded + agent-curated two-source model
- `COMPOSE-ARCHITECTURE.md` §6.3 — step-specific prohibitions live in sub-skills, not L4
- `COMPOSE-ARCHITECTURE.md` §7.3 — concrete L4 file format with worked example
- `COMPOSE-ARCHITECTURE.md` §7.4 — the six safety gates (Gate 0 conflict pre-emption → Gate 1 DeepSeek audit → Gate 2 mini-CQ → Gate 3 compose dry-run → Gate 4 atomic write/commit/push → Gate 5 recompose recovery)
- `COMPOSE-ARCHITECTURE.md` §7.7 — one-shot + durable model; drift caught at recompose time

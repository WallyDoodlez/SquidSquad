# Cross-Doc Consistency Audit — 2026-05-28

**Scope**: Full 10-pair cross-validation of the 5 architecture TRDs (AGENT-RUNTIME, COMPOSE-ARCHITECTURE, HARNESS-ARCH, INSTALLER-ARCH, VAULT-ARCH).

**Method**: Each pair sent to DeepSeek as a focused contradiction-finding audit (system prompt asks for cited contradictions only, excludes within-doc consistency / known sweeps / retired sub-skill mentions). 6 of the 10 pairs were run this cycle; 4 (AGENT-RUNTIME pivot pairs) were run in cycle 1801 and are referenced for completeness.

**Coverage matrix**:

|              | AGENT-RT | COMPOSE-ARCH | HARNESS-ARCH | INSTALLER-ARCH | VAULT-ARCH |
|--------------|----------|--------------|--------------|----------------|------------|
| AGENT-RT     | —        | ✅ c1801     | ✅ c1801     | ✅ c1801       | ✅ c1801   |
| COMPOSE      | —        | —            | ✅ c1835     | ✅ c1835       | ✅ c1835   |
| HARNESS      | —        | —            | —            | ✅ c1835       | ✅ c1835   |
| INSTALLER    | —        | —            | —            | —              | ✅ c1835   |
| VAULT        | —        | —            | —            | —              | —          |

**Document versions audited**:

- `AGENT-RUNTIME.md` — from branch `docs/agent-runtime-internal-fixes` (PR #10364)
- `COMPOSE-ARCHITECTURE.md` — from branch `docs/responsibility-slot` (PR #10359)
- `HARNESS-ARCH.md`, `INSTALLER-ARCH.md`, `VAULT-ARCH.md` — from `main`

---

## Summary

Across the 6 new pairs:

| Pair                          | HIGH | MED  | LOW  | Total |
|-------------------------------|------|------|------|-------|
| COMPOSE × HARNESS             | 1    | 1    | 1    | 3     |
| COMPOSE × INSTALLER           | 1    | 1    | 1    | 3     |
| COMPOSE × VAULT               | 1    | 2    | 1    | 4     |
| HARNESS × INSTALLER           | 2    | 2    | 2    | 6     |
| HARNESS × VAULT               | 1    | 1    | 1    | 3     |
| INSTALLER × VAULT             | 1    | 1    | 1    | 3     |
| **Subtotal (new this cycle)** | **7**| **8**| **7**| **22**|
| Cycle-1801 AGENT-RT pivots    | 5    | 7    | 8    | 20    |
| **GRAND TOTAL (10 pairs)**    | **12** | **15** | **15** | **42** |

**Dominant themes across all 22 new findings**:

1. **`role` vs `alias` terminology drift** — multiple docs use `role` in identifiers where the value is actually the alias; the harness doc has a vocabulary note about this but other docs don't reflect it consistently
2. **L4 file structure mismatch** — INSTALLER-ARCH still documents the legacy multi-file L4 pattern (`*-instructions.md`, `*-responsibility.md`, `*-soul-directives.md`, `shared-*`, `setup-upgrade-gate.md`); COMPOSE-ARCHITECTURE PR #10359 declares the target as one unified `<role-class>.md` per role-class
3. **Vault scaffold ownership** — INSTALLER claims to create the vault skeleton at install time; VAULT-ARCH says `vault-init` (in the `vault-protocol` sub-skill) does it at runtime
4. **Runtime state file ownership** — INSTALLER-ARCH lists `.harness-port`, `.harness-state.json`, `.event-state.json` as installer outputs (with a note that they're "runtime"); HARNESS-ARCH unambiguously says these are harness-owned and created at boot
5. **Stale `responsibility.md` references** — HARNESS-ARCH §13.5 references reading `responsibility.md` `## Bus contract` sections at boot; COMPOSE-ARCHITECTURE retires this file entirely (responsibility becomes a dedicated compose slot)

---

## HIGH findings (7)

### H1 — COMPOSE × HARNESS: `role` vs `alias` in output directory path

- **COMPOSE-ARCHITECTURE** defines composed output at `.squidsquad/<role>/CLAUDE.md` with `<role>` = L2 categorical role
- **HARNESS-ARCH §9** says per-agent directories are keyed by **alias** (`skill`, `verifier`, `human`, ...), not by L2 categorical role
- **Reconciliation**: COMPOSE-ARCHITECTURE should change output path references to `<alias>` for the directory; the six-section structure and L4 file naming (by role-class) stay correct

### H2 — COMPOSE × INSTALLER: L4 file structure (unified vs multi-file)

- **COMPOSE-ARCHITECTURE §3.3 + §7.3** declares the target: one unified `.squidsquad/project/<role-class>.md` per role-class with H2 slot sections; explicitly deprecates the multi-file pattern
- **INSTALLER-ARCH §5 File layout** still scaffolds the legacy multi-file pattern (`shared-*`, `<role>-instructions.md`, `<role>-responsibility.md`, `<role>-soul-directives.md`, `setup-upgrade-gate.md`)
- **Reconciliation**: INSTALLER-ARCH §5 updates to the unified per-role-class file model; remove legacy seed file names

### H3 — COMPOSE × VAULT: Vault slot count (5 vs 6 sections)

- **COMPOSE-ARCHITECTURE §5** = six sections: Identity / Responsibility / Soul / Instructions / Project Context / Vault
- **VAULT-ARCH §12.1** says "Vault is one of the 5 composed-output slots (identity / soul / instructions / project-context / vault)" — drops Responsibility
- **Reconciliation**: VAULT-ARCH §12.1 list updates to include `responsibility`

### H4 — HARNESS × INSTALLER: Runtime state file ownership

- **HARNESS-ARCH §9** says `.harness-port`, `.harness-state.json`, `.event-state.json` are harness-owned, written at harness boot
- **INSTALLER-ARCH §3.2 + §5** lists these files in the installer outputs / file layout (with a "runtime" annotation) — confusing because they are NOT installer outputs
- **Reconciliation**: INSTALLER-ARCH §3.2 + §5 remove these files from installer outputs entirely (the "not by the installer" note is correct but the listing is misleading)

### H5 — HARNESS × INSTALLER: Clone registry ownership gap

- **HARNESS-ARCH §1.2** says the harness reads `~/.squidsquad/clones/<alias>` at boot; doesn't say who creates it
- **INSTALLER-ARCH §3.2** says the installer creates the registry; doesn't say who reads it
- **Reconciliation**: both docs explicitly state the complementary half (installer creates, harness reads) and cross-reference each other

### H6 — HARNESS × VAULT: Vault dependency on harness reachability

- **HARNESS-ARCH §11** says agents fall through to loop-mode when harness is unreachable (no event-bus ops, no cycle wrapper)
- **VAULT-ARCH §9.6** says vault operations are "local file I/O + git commits with no harness dependency"
- **Why contradiction**: vault sub-skills run inside the cycle wrapper (post-cycle steps); if the cycle wrapper itself is harness-dependent, vault ops are too
- **Reconciliation**: VAULT-ARCH §9.6 clarify that when harness is unreachable, vault writes defer until next reachable cycle (file I/O is harness-independent in isolation, but the cycle-wrapper trigger is not)

### H7 — INSTALLER × VAULT: Vault initialization ownership

- **INSTALLER-ARCH §3.2 + §4.8 + §5** says installer creates the vault skeleton (folders + BRIEFING.md + etc.)
- **VAULT-ARCH §7.1** says `vault-protocol`'s `vault-init` step creates the PARAG structure + bootstrap files at runtime (idempotent)
- **Reconciliation**: clean split — INSTALLER-ARCH §4.8 says "creates empty vault directory structure (folders only)"; vault content bootstrap stays at runtime via vault-init. OR delegate entirely to vault-init and have the installer skip the vault folder creation.

---

## MED findings (8)

### M1 — COMPOSE × HARNESS: Stale `responsibility.md` reference

- **HARNESS-ARCH §13.5** says harness reads `responsibility.md` `## Bus contract` sections at boot
- **COMPOSE-ARCHITECTURE §5.2** retires the standalone `responsibility.md` file (responsibility becomes a dedicated compose slot)
- **Reconciliation**: HARNESS-ARCH §13.5 update — either clarify it reads the composed `.squidsquad/<alias>/CLAUDE.md` responsibility section, or remove the reference entirely since the permission table is being retired

### M2 — COMPOSE × INSTALLER: L4 seed enrichment path

- **INSTALLER-ARCH §4.8 Phase 5** says it enriches seed templates from `references/sub-skills/project/`
- **COMPOSE-ARCHITECTURE §3.3** says those legacy seeds collapse to one per role-class
- **Reconciliation**: INSTALLER-ARCH §4.8 either names the exact unified seed files it operates on, OR references `sub-skill-catalog.md`'s L4-seed section as the authoritative list

### M3 — COMPOSE × VAULT: Vault slot specification ownership

- **COMPOSE-ARCHITECTURE §11.2 G4** says "Vault slot is the most underspecified"
- **VAULT-ARCH §12.1** says G4 can be closed by referencing VAULT-ARCH §3/§4/§5
- **COMPOSE-ARCHITECTURE §5.5** says "most vault detail belongs in `references/sub-skills/common/vault-protocol.md`"
- **Why contradiction**: §5.5 points at the sub-skill; G4 points at VAULT-ARCH; circular delegation with no single canonical home
- **Reconciliation**: §5.5 adds explicit cross-ref to VAULT-ARCH as the canonical slot spec; §11.2 G4 marks closed with that cross-ref

### M4 — COMPOSE × VAULT: Vault sub-skill composition model (inline vs reference)

- **COMPOSE-ARCHITECTURE §4.1 step 4** says instructions slot emits **references**, not inlined bodies
- **VAULT-ARCH §7** says vault sub-skills are **inlined** into composed CLAUDE.md by compose.py
- **Why contradiction**: VAULT-ARCH describes v1 (inlining); COMPOSE-ARCHITECTURE describes v2 (references). Neither acknowledges the migration
- **Reconciliation**: VAULT-ARCH §7 adds a note that current inlining is v1 behavior; vault sub-skills transition to reference-only per COMPOSE-ARCHITECTURE §4.1; specify any sub-skills that intentionally stay inlined (mandatory-tier per the catalog)

### M5 — HARNESS × INSTALLER: Port file as installer output

- **HARNESS-ARCH §8** says harness writes `.harness-port` at startup
- **INSTALLER-ARCH §3.2 + §5** lists it as a runtime file under installer outputs
- **Reconciliation**: same fix as H4 — remove from installer outputs (the "runtime" note doesn't make it an installer output)

### M6 — HARNESS × INSTALLER: `.claude-pid` not in installer file layout

- **HARNESS-ARCH §9** lists `.claude-pid` as agent-owned (thin_launcher singleton sentinel)
- **INSTALLER-ARCH §5** per-alias directory listing omits `.claude-pid`
- **Reconciliation**: INSTALLER-ARCH §5 adds `.claude-pid` with note "created at runtime by thin_launcher"

### M7 — HARNESS × VAULT: `tracker.py create-task` invocation model

- **HARNESS-ARCH §13.6** documents the generic `/queue/{alias}` endpoint as not-yet-implemented
- **VAULT-ARCH §7.4** references `tracker.py create-task` as a script vault-synthesis calls
- **Reconciliation**: VAULT-ARCH §7.4 clarifies the invocation path (direct CLI vs harness HTTP API); reference HARNESS-ARCH §13.6 if dependent on endpoint implementation

### M8 — INSTALLER × VAULT: Vault write access model

- **INSTALLER-ARCH §5** asserts "PM + workers R/W, verifiers + DM read-only" in the vault directory annotation
- **VAULT-ARCH §1** explicitly delegates per-role access model to AGENT-RUNTIME / COMPOSE-ARCHITECTURE
- **Reconciliation**: INSTALLER-ARCH §5 removes the access-model assertion and cross-refs the canonical source

---

## LOW findings (7)

### L1 — COMPOSE × HARNESS: `bootup-complete` vs `booted` event naming

- **COMPOSE-ARCHITECTURE §5.7.2** names the step `step:boot/bootup-complete`
- **HARNESS-ARCH §7.2** says harness waits for `booted` event
- **Reconciliation**: COMPOSE-ARCHITECTURE step ID → `step:boot/booted` to match wire-format

### L2 — COMPOSE × INSTALLER: `compose.py deploy <role>` parameter resolution

- **INSTALLER-ARCH §4.9** passes alias to `compose.py deploy <role>` with parenthetical note "param name predates alias concept"
- **COMPOSE-ARCHITECTURE §3.3 + §4.2** describes deploy operating on role-class
- **Reconciliation**: specify the alias→role-class resolution mechanism (config.md mapping? team-preset lookup?)

### L3 — COMPOSE × VAULT: Vault slot L4 op constraints circular delegation

- **COMPOSE-ARCHITECTURE §3.3** says vault slot is "append only — see VAULT-ARCH for vault-specific overlay rules"
- **VAULT-ARCH §1** says L4 project-local is "different system; see COMPOSE-ARCHITECTURE.md §3"
- **Reconciliation**: one doc owns the vault-slot L4 op semantics (recommend VAULT-ARCH adds the spec; COMPOSE-ARCHITECTURE §3.3 keeps the cross-ref)

### L4 — HARNESS × INSTALLER: `compose.py deploy` arg naming consistency

- Both docs acknowledge the `role` vs `alias` mismatch but describe it differently (env var name in HARNESS-ARCH §14.2; CLI arg name in INSTALLER-ARCH §4.9)
- **Reconciliation**: INSTALLER-ARCH cross-refs HARNESS-ARCH §9's vocabulary note for unified terminology

### L5 — HARNESS × INSTALLER: Upgrade-flow restart mechanism

- **HARNESS-ARCH §7.1** describes restart via intent state machine (cooperative exit-42 + respawn)
- **INSTALLER-ARCH §10** describes upgrade as `POST /agents/<role>/stop` + `POST /agents/<role>/start` (separate calls)
- **Reconciliation**: INSTALLER-ARCH §10 uses `POST /agents/<role>/restart` to match the harness's cooperative protocol

### L6 — HARNESS × VAULT: `role` vs `alias` in vault owner field

- **HARNESS-ARCH §9** establishes that codebase `role` identifiers carry alias values
- **VAULT-ARCH §10.3** treats vault `owner:` field values (`skill`, `pm`) as L2 categorical roles; flags `-lead` suffix variants as "non-spec drift"
- **Why contradiction**: if `owner:` is alias-typed, `-lead` suffixes might be valid alias variants, not drift
- **Reconciliation**: VAULT-ARCH §10.3 clarifies whether `owner:` is alias-typed or role-typed; if alias-typed, accept `-lead` variants

### L7 — INSTALLER × VAULT: Vault template source path

- **INSTALLER-ARCH §4.8** references `references/sub-skills/project/` for seed templates
- **VAULT-ARCH §7.1** references `references/vault-templates/` for vault bootstrap files
- **Reconciliation**: INSTALLER-ARCH §3.2 clarifies vault-template path (or defers entirely to vault-init per H7)

---

## Disposition

This audit captures the contradictions; it does not fix them inline. Each finding is small enough to fix in a targeted doc PR; HIGH findings should clear before TRDs are considered settled.

**Existing tracker tasks that overlap with these findings**:

- **#10361** (AGENT-RUNTIME alignment with PR #10359 + `.squidsquad/config.md` path sweep across all arch docs) — overlaps with terminology/path drift findings
- **#10363** (Cross-doc consistency fixes from cycle-1801 AGENT-RUNTIME pivot audits) — should expand to cover the 22 new findings

**Recommended next step**: extend #10363's scope to include the 22 findings here. Per the TRD → PRD → Stories → Tasks model (memory `project_trd_prd_delivery_model`), this audit's purpose is to finish polishing the TRDs before we enter the PRD phase — fixes are doc-only, no implementation impact.

---

## Raw audit outputs

The full DeepSeek findings (with exact section quotes) are preserved at `C:/Users/naaht/audit-tmp/ds_output_cross_*.md` for reference. This summary doc is the canonical reading; the raw outputs are the source.

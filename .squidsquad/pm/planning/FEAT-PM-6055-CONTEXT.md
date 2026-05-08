# FEAT-PM-6055 Context — Enforce Role Separation

## Scope

Enforce that PM, QA (verifier), and DM are mandatory roles in every SquidSquad team. Remove all fallback paths where one role absorbs another's duties. The only valid variation is the number of dev/worker agents.

## Locked Decisions (human decided)

- **Four mandatory L2 roles**: PM (coordinator), dev/worker (one or more), QA/verifier, DM (delivery). Every team must have all four
- **No opt-in flags**: PM, QA, and DM are not optional. No configuration for absent roles
- **No fallback paths**: PM never verifies (QA's job), PM never delivers (DM's job), QA never plans (PM's job), DM never coordinates (PM's job)
- **Only variation**: Number of dev/worker agents (1+). PM, QA, DM are always exactly one each
- **Setup enforcement**: /squidsquad-setup always creates PM + QA + DM + dev agents. No option to skip QA or DM

## Dev Discretion (dev agent can choose)

- How to remove fallback code (delete vs guard with assertion)
- Error messaging when someone tries to run without QA/DM
- Whether to add a startup preflight check vs compose-time check

## Side Effect Mitigations (required)

- Remove `testing-and-verification.md` PM→QA fallback (Steps 3-6 skip logic)
- Remove `delivery-fallback.md` PM→DM fallback entirely (Step 6d)
- Remove `cycle_post.py` CHANGELOG fallback when DM absent
- Update PM SOUL — remove "almost half a QA agent" wording
- Update PM prohibitions — add "Never verify, never deliver"
- Update QA instructions — remove assumption that PM→DM fallback exists
- Update setup wizard — QA and DM are always created, not optional
- Update SKILL.md — DM listed as "always present" not "optional"
- Existing installs without QA or DM: upgrade must detect and prompt user to add missing roles

## Upgrade Path (required)

- Existing installs may not have QA or DM. `/squidsquad-upgrade` must detect missing mandatory roles and guide user through adding them
- `compose.py deploy-all` fails if mandatory roles are missing — clear error message
- Backward compatible during transition: old agents with fallback code still work until recompose

## Out of Scope

- Multiple QA or DM agents (one each, always)
- Domain-specific verifier types (L3 concern)
- Role-specific configuration (opt-in flags eliminated)

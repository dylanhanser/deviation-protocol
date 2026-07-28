# Deviation Protocol Roadmap

This document is the authority for detailed project status and roadmap
placement. Feature and architecture decisions remain in their linked canonical
documents.

## Status language

- **Implemented:** supported by current code and verification evidence.
- **Accepted design / Approved product design:** decided and documented, but not
  implemented.
- **Deferred:** direction or detail remains undecided.
- **Planned phase:** assigned to a future phase whose implementation has not
  started.

## Current baseline

- Branch: `main`
- Local `origin/main` and `HEAD`:
  `afa9f9c21900eebd4e08d65071a26903e83d4a65`
- HEAD subject: `docs(domain): freeze structured player character phase 2 plan`
- Ahead/behind: `0/0`
- Codex does not push; the user performs every push manually.
- Phase 3.2b historical implementation baseline:
  `a0fbc7a749d9774785aa78ffe2b48b4dcf9e3dce`
- Latest completed subphase: **Phase 3.2b**
- Phase 3.2a authoritative commit:
  `f1fd5e2cd07d342e852430e9352f64b84014c88e`
- Phase 3.2b: **implemented, verified, accepted, and closed**
- Phase 3.2 as a whole: **implemented and complete**

## Phase status

| Phase | Status | Canonical detail |
| --- | --- | --- |
| Phase 1 | Implemented and complete | [Architecture](docs/architecture.md) |
| Phase 2.1 | Implemented and complete | [Architecture](docs/architecture.md) |
| Phase 2.2 | Implemented and complete | [Narrative Provider](docs/narrative_provider.md) |
| Phase 2.3 | Implemented and complete | [Player memory](docs/player_memory.md) |
| Phase 2.4 | Implemented and complete | [Playable vertical slice](docs/playable_vertical_slice.md) |
| Phase 3.0 | Implemented and complete | [Public client contract](docs/public_client_contract.md) |
| Phase 3.1a | Implemented and complete | [Architecture](docs/architecture.md) |
| Phase 3.1b | Implemented and complete | [Public client contract](docs/public_client_contract.md) |
| Phase 3.1c | Implemented and complete | [Canonical same-tab recovery contract](docs/architecture.md#phase-31c-web-same-tab-recovery-contract) |
| Phase 3.2a | **Implemented, verified, committed, and closed** | [Phase 3.2 specification and evidence](docs/phase_3_2_deterministic_demo_environment.md) |
| Phase 3.2b | **Implemented, verified, accepted, and closed** | [Phase 3.2 specification and evidence](docs/phase_3_2_deterministic_demo_environment.md) |
| Phase 3.3 | **Approved product design — not implemented** | [Run Protocol, difficulty, and world profiles](docs/run_protocol.md) |
| Phase 3.4 | **Approved product design — not implemented** | [NPC Relationship and Temporary Residence](docs/npc_relationship_residence.md) |
| Phase 4.0 | **Accepted architectural direction — not implemented** | [ADR 0001: Production Provider Distribution](docs/decisions/0001-production-provider-distribution.md) |

## Implemented baseline through Phase 3.2b

The implemented engine and public application boundary include:

- deterministic domain rules, trusted authority policies, transactional
  persistence, idempotent action handling, and authoritative scenario state;
- the supplier-neutral application `NarrativeProvider` interface and normally
  configured DeepSeek infrastructure adapter;
- a public scenario/session/action/View contract whose controls come only from
  the latest authoritative `action_affordances`;
- the complete public `death_certificate` vertical-slice paths and bounded
  player-memory projection;
- the React/Vite action loop with same-tab recovery for a Session and
  server-confirmed pending requests, without action replay, as defined by the
  [canonical Phase 3.1c recovery
  contract](docs/architecture.md#phase-31c-web-same-tab-recovery-contract); and
- the isolated Phase 3.2a Demo backend runtime: deterministic Provider,
  process-local transactional persistence, independent composition root,
  deterministic IDs/seeds/logical clock, exact two-process replay evidence, and
  external-I/O denial evidence; and
- the Phase 3.2b local Web layer: Demo-only Vite
  dotenv isolation, conditional local/temporary/non-production presentation,
  exact 19-action React/MSW regression, same-tab Demo recovery regressions,
  one-command launcher, direct production-Zod catalog validator, and bounded
  startup/proxy/sentinel/build smoke.

`death_certificate_v1` is the canonical current Demo and vertical-slice
scenario. This is not a permanent product decision that it must be the first
world in the production game.

## Phase 3.2: Deterministic Demo Environment

### Phase 3.2a — Deterministic Demo Environment

Status: **Implemented, verified, committed, and closed.**

Authoritative commit:
`f1fd5e2cd07d342e852430e9352f64b84014c88e`.

The closed subphase provides the isolated Demo backend runtime. It does not
provide the Phase 3.2b Web launch/walkthrough layer, production deployment,
commercial Provider routing, billing, Run Protocol, difficulty/world profiles,
or NPC residence.

Implementation and evidence are recorded in
[the historical Phase 3.2 specification](docs/phase_3_2_deterministic_demo_environment.md).

### Phase 3.2b — Demo Web and Full Playable Walkthrough

Status: **Implemented, verified, accepted, and closed.**

The implementation provides:

- Demo Web/Vite mode and dotenv isolation;
- one PowerShell launcher for the local Demo;
- an unmistakable local-only, temporary, non-production label;
- the full Web-loop regression through the canonical complete path;
- bounded startup/proxy/sentinel/schema/build validation; and
- preserved same-tab recovery with safe missing-Session invalidation after a
  backend restart.

The supported local commands are:

```powershell
pwsh -NoProfile -File .\scripts\start-demo.ps1
pwsh -NoProfile -File .\scripts\smoke-demo.ps1
```

The launcher binds both children to loopback and uses the isolated Demo
composition. Demo state is process-local and temporary. The bounded smoke
creates only owned temporary build/response data plus a create-new dotenv
sentinel, validates the proxied scenario catalog through the production Web
schema, executes the exact-warning React presentation probe with the effective
mode copied from the launched Web child, and cleans its owned resources.

The 2026-07-23 correction round passed the Offline verifier, all Web commands,
the exact cross-process replay, the focused executable PowerShell lifecycle
suite, and the corrected bounded smoke. The subsequent controlled manual
acceptance passed the canonical 19-action browser walkthrough to version 19 and
`ENDED`, same-tab recovery after backend restart, Ctrl+C launcher shutdown, and
final owned-process and port cleanup.

Phase 3.2b reuses the Phase 3.2a backend and existing public client contract.
It does not own Run Protocol, difficulty/world profiles, relationship or
residence systems, production commercial routing, quotas, or billing.

Phase 3.2b and Phase 3.2 are complete. This deterministic local Demo acceptance
does not establish production readiness or implement later final-product work.

## Cross-phase final narrative experience design

Status: **Approved and frozen canonical cross-phase product specification —
not implemented; third independent read-only review passed.**

The canonical product-level authority for the reading-first final experience,
persistent player character, NPC importance and golden long-term memory,
multi-genre and cross-scenario continuity, generalized narrative conflict, and
their model/server authority boundary is
[Final Narrative Experience and Long-Term Systems](docs/final_narrative_experience.md).
It preserves the deterministic Demo as a validation fixture and records a
bounded future implementation sequence without assigning implementation status
to any deferred system.

The approved final narrative experience specification remains frozen and not
implemented. Phase 3.2b remains closed.

The
[structured player-character contract](docs/structured_player_character_contract.md)
is an **approved and frozen structured player-character product specification —
partially implemented by the committed and pushed Phase 1 pure domain/protocol
foundation and a local, uncommitted Phase 2 Slice 1 candidate. Phase 1 has
passed fresh independent read-only acceptance for the exact nine-path candidate
and is accepted; the overall implementation plan remains only partially
implemented. Phase 2 Slice 1 final independent acceptance is pending.** Its
first independent read-only review found one HIGH issue
concerning stable same-story-line identity continuity, one MEDIUM issue
concerning permanent `player_character_id` non-reuse, and one MEDIUM issue
concerning `controller_binding` lifecycle presence. The first controlled
correction addressed those three issues locally. The first independent
re-review confirmed that all three original findings were closed but found one
new MEDIUM omission concerning silent applicable-version switching at scenario
and Run-authorized later-world boundaries. The second controlled correction
addressed that omission locally without selecting pinned, floating,
checkpointed, or other revision-following behavior.

The second fresh independent read-only review confirmed that all four
historical findings were closed, found no new HIGH, MEDIUM, or LOW issue
requiring correction, and returned
`APPROVED_STRUCTURED_PLAYER_CHARACTER_CONTRACT`. This separate controlled
documentation closeout then recorded the earned approval and frozen status and
created the local documentation commit. It was not an independent review,
changed no runtime, database, migration, Provider, public-client, API, or other
implementation behavior, made no additional product decision, and did not
push. Approval and freeze do not authorize runtime work. Implementation
requires a separately approved downstream implementation plan and task.

The
[structured player-character downstream implementation plan](docs/structured_player_character_implementation_plan.md)
translates that approved and frozen product contract into proposed
repository-specific implementation work. The historical plan and its technical
prerequisites were **approved and frozen; the current four-document candidate
requires fresh independent approval.** Phase 1 has passed fresh independent read-only acceptance for the exact
nine-path candidate. Its original implementation commit is
`c8808f66e8d97bc4386a481bf21669cfddcd222e`; the current completed and pushed
Phase 1 implementation baseline is
`4acb8b993f15a1fdee20edc3140324730447fc9f`
(`fix(domain): preserve exact opaque identifiers`). The complete plan remains
partially implemented. The Phase 2 product scope and technical prerequisites
historically received the independent verdict
`STRUCTURED_PLAYER_CHARACTER_PHASE_2_TECHNICAL_FREEZE_APPROVED`; the exact
then-approved candidate was committed and pushed unchanged as
`1fd29798fe256593e56029baca743484cc221ae4`
(`docs(domain): freeze structured player-character phase 2 prerequisites`).
That commit remains the technical-freeze history, but it predates the current
Phase 1 opaque-identifier correction and does not approve the current locked
candidate.

Phase 2 Slice 1 now exists only as a local candidate: its application ports,
exact six-family offline persistence carriers, canonical codecs, aggregate
validation, and bounded tests are implemented. The five findings from its
first independent review have been corrected locally, and the corrected
source/test candidate passed 94 persistence tests, 190 unchanged Phase 1
regressions, 284 combined contract tests, compileall, and Offline verification
with 1,346 passed and 48 skipped. Final independent acceptance is still
pending; nothing is staged, committed, or pushed. Slice 2 has not begun. No ORM,
migration, database adapter or verification, transaction or recovery behavior,
production composition, public route, frontend behavior, Provider integration,
or story/Run activation exists. Phase 3 and every later structured-player-
character phase remain blocked.

The implementation-order amendment below is a new review candidate, distinct
from the frozen technical prerequisites. It becomes operative automatically,
without another status-only documentation edit, only after all of these ordered
conditions are satisfied:

1. A fresh independent read-only review returns
   `STRUCTURED_PLAYER_CHARACTER_PHASE_2_PLAN_APPROVED` for the exact complete
   four-document candidate and its four SHA-256 hashes.
2. Separate authorization is obtained to stage and commit exactly those four
   approved documents, and the staged and committed bytes retain the approved
   hashes.
3. The documentation-only commit is pushed through the repository's
   established authorized push workflow.
4. After the push, a new clean baseline is confirmed: `main` is checked out,
   `HEAD` equals local `origin/main`, ahead/behind is `0/0` without an
   unnecessary fetch unless separately authorized, the worktree and index are
   clean, no staged or normal untracked path remains, and the pushed commit
   contains exactly the approved documentation scope.
5. A separately authorized Phase 2 implementation task may then begin.

Before exact-candidate approval, staging and commit are prohibited. Approval
alone or a local documentation commit alone does not authorize Phase 2
implementation; implementation remains blocked until the pushed clean baseline
is confirmed. Slice 1 still requires the separate explicit authorization in
condition 5. Approval of this amendment does not itself authorize
implementation, migration execution, database access, staging, commit, or
push.

Subject to that gate and later slice-specific authorization, the deterministic
Phase 2 order is:

1. **Slice 1 — Offline persistence contracts and canonical stored-record
   codec.**
2. **Slice 2 — Exact six-family SQLAlchemy metadata and linear Alembic
   migration.**
3. **Slice 3 — MySQL repositories, locking, CAS, and strict reconstruction.**
4. **Slice 4 — SQLAlchemy Unit of Work wiring and atomic Phase 2 integration
   proof.**

The detailed scope, paths, dependencies, exclusions, verification level, and
completion criteria for every slice are authoritative in the implementation
plan. Its existing receipt/history integrity design requires internally derived
canonical state-record fingerprints that bind each receipt to its exact
authoritative revision record(s). No database receipt schema, canonical character persistence,
public/runtime route, Provider integration, frontend flow, or Run/story-line
activation exists today. Phase 1 acceptance and the historical Phase 2
technical-freeze approval do not themselves authorize Phase 2 implementation.
Phase 3.2b remains closed.

## Phase 3.3: Run Protocol and Difficulty/World Profiles

Status: **Approved product design — not implemented.**

Phase 3.3 owns the engine/world parameters, pre-game profiles and permitted
overrides, versioned frozen Run Protocol, deterministic resolution, and the
separation between objective difficulty, character definition, narrative
presentation, and relationship atmosphere. It also owns the approved,
not-implemented rule that a player chooses an entry world only from a small
authored eligible set, freezes its ID/version at run start, and the engine
selects later worlds deterministically from the eligible pool. Exact catalogues,
weighting, anti-repeat, progression, and priority-injection rules remain
Deferred. An important authored world may remain eligible for a meaningful,
engine-selected revisit that preserves confirmed world/NPC state and
consequences. Players cannot choose, request, approve, veto, or otherwise
authorize it; the complete revisit decision remains engine-owned. Detailed
revisit, region-unlock, anti-farming, recovery-priority, and world-line rules
remain Deferred.

The canonical design is
[Run Protocol, Difficulty, and World Profiles](docs/run_protocol.md).

## Phase 3.4: NPC Relationship and Temporary Residence

Status: **Approved product design — not implemented.**

Phase 3.4 owns engine-confirmed relationship progression, residence eligibility
and lifecycle, bounded dialogue, temporary fixed-scene activities, departure,
and structured relational memory integration.

The canonical design is
[NPC Relationship and Temporary Residence](docs/npc_relationship_residence.md).

## Phase 4.0: Production Provider Distribution

Status: **Accepted architectural direction — not implemented.**

Phase 4.0 owns player-selected Provider/model channels, the self-controlled
Production Distribution Gateway, server-side credentials, explicit
Provider-preserving failures, commercial quotas, metering, rate limiting, and
abuse control. Silent cross-Provider fallback is prohibited.

The canonical decision is
[ADR 0001: Production Provider Distribution](docs/decisions/0001-production-provider-distribution.md).

## Deferred

- The eligible initial-world catalogue and later-world weighting, anti-repeat,
  progression, and priority-injection details.
- Exact Phase 3.3 parameter values, serialization, and compatibility policy.
- Exact Phase 3.4 relationship thresholds, residence duration, memory schema,
  and dialogue allowance.
- The Phase 4.0 gateway implementation, model catalogue, pricing/quota formula,
  regional availability policy, and key-pool policy.
- Memory rebuild and compaction.
- Scenario replay and `scenario_run_id`.
- Exact cross-scenario NPC identity and compatibility schema.
- `DeviationEvaluator`.
- Generalized conflict/combat schema, resolution rules, and implementation.
- Worker, queue, or distributed orchestration.

## Stable implemented authority decisions

- Models generate untrusted narrative candidates.
- The engine and trusted server policies own objective mechanics, facts,
  permanent state, and canon.
- Public clients act only through authoritative affordances and refresh the
  complete authoritative View.
- Ordinary creative actions do not become anomaly candidates.
- The deterministic Demo Provider remains isolated from normal Provider
  composition and future production distribution.
- MySQL is the only production database target; there is no SQLite fallback.
- Live Provider calls are not a normal verification dependency.

## Workflow

Before independent audit, a phase-completion claim, or a request for commit
authorization, complete the canonical
[documentation-synchronization checklist](docs/engineering/codex_workflow.md#canonical-documentation-synchronization-checklist).

Codex may create a local commit only when the user explicitly authorizes that
exact commit operation. Codex never pushes; the user performs every push
manually.

## Document ownership

- Project status and roadmap: `PLANS.md`.
- Final player experience and cross-phase long-term system direction:
  [`docs/final_narrative_experience.md`](docs/final_narrative_experience.md).
- Approved and frozen, partially implemented downstream structured
  player-character implementation plan:
  [`docs/structured_player_character_implementation_plan.md`](docs/structured_player_character_implementation_plan.md).
- Implemented architecture and composition roots:
  [`docs/architecture.md`](docs/architecture.md).
- Production Provider distribution:
  [`docs/decisions/0001-production-provider-distribution.md`](docs/decisions/0001-production-provider-distribution.md).
- Run Protocol and difficulty/world profiles:
  [`docs/run_protocol.md`](docs/run_protocol.md).
- NPC relationship and temporary residence:
  [`docs/npc_relationship_residence.md`](docs/npc_relationship_residence.md).
- Documentation and Git workflow:
  [`docs/engineering/codex_workflow.md`](docs/engineering/codex_workflow.md).
- Phase 3.2 specification and evidence:
  [`docs/phase_3_2_deterministic_demo_environment.md`](docs/phase_3_2_deterministic_demo_environment.md).

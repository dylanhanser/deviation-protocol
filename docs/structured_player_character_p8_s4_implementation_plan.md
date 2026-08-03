# Structured Player Character P8-S4 implementation plan candidate

## A. Status and task identity

**Plan status:** Draft implementation plan  independent review pending; not approved; not implemented.

**Task identity:**
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_PLAN_CORRECTION`

**Implementation-slice identity:** P8-S4 — Deterministic Demo parity.

**Repository baseline:**

- repository: `D:\deviation-protocol`;
- branch: `main`;
- `HEAD`, local `main`, and local `origin/main`:
  `753b3967aa6819cefbcd33ffe1844c75e22e330a`;
- baseline subject: `docs(player-character): amend P8-S4 test budget`;
- sole parent and preceding published P8-S3 status-sync baseline:
  `62923823232ed56efde9085bc319e02c47eb3081`;
- completed P8-S3 implementation:
  `ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`;
- ahead/behind at authoring: `0/0`.

The published parent amendment received the exact historical review-success
verdict
`STRUCTURED_PLAYER_CHARACTER_P8_S4_PARENT_TEST_BUDGET_AMENDMENT_INDEPENDENT_REVIEW_APPROVED`
for its exact reviewed bytes and was committed and user-published at
`753b3967aa6819cefbcd33ffe1844c75e22e330a`. That token binds only the already-
published parent amendment. It cannot approve this implementation-plan
candidate or the future implementation, and the parent's publication does not
automatically approve either one. Correcting this candidate is likewise not an
approval and authorizes no staging, commit, push, publication, or implementation.

This candidate is not frozen or approved. It has no implementation authority,
commit authority, or publication status. The sole operative success verdict for
the fresh independent read-only review of this plan is exactly:

`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_PLAN_INDEPENDENT_REVIEW_APPROVED`

That verdict applies only to the exact complete candidate bytes and SHA-256
inspected and reported by the independent reviewer. Any later byte change
invalidates it and requires new identity evidence plus a fresh review. This plan
must not attempt to embed a self-referential checksum into its own bytes; the
reviewer's report supplies the binding reviewed SHA-256. “Approved,” “approval
token,” “sole authorized success verdict,” or any other generic phrase cannot
substitute for the exact verdict above.

The complete plan-to-implementation gate is:

1. correct this implementation-plan candidate without treating correction as
   approval;
2. return and freeze its new exact raw-byte count and SHA-256;
3. conduct a fresh independent read-only review of the complete corrected
   candidate;
4. receive exactly
   `STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_PLAN_INDEPENDENT_REVIEW_APPROVED`,
   with that approval bound to the exact reviewed SHA-256;
5. perform a separate candidate-plan commit-only task only after separate
   authorization, committing only the independently approved plan;
6. return control to the user for manual publication;
7. do not conduct another substantive plan review after commit or publication
   or schedule a standalone post-publication baseline-confirmation task;
8. begin the later separately authorized P8-S4 implementation task with a short
   preflight confirming the published plan commit, aligned refs, clean index,
   and expected worktree state; stop before implementation if it fails, or
   proceed with P8-S4 implementation in that same task if it passes;
9. independently review the later implementation candidate before any
   implementation commit or publication; and
10. do not begin P8-S5 or P8-S6 during any P8-S4 planning or implementation
    gate.

The sole future P8-S4 implementation-review success verdict is exactly:

`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It is distinct from the current plan-review verdict. It is reachable only after
the implementation candidate satisfies this frozen plan and all required
evidence, and it binds only the exact implementation candidate state and
reviewed diff. By itself it authorizes no commit, push, publication,
documentation synchronization, P8-S5, or P8-S6. No generic approval phrase may
substitute for either exact verdict.

The test-budget correction and every later gate remain separate. Corrected
budget wording is not plan approval or implementation approval. This draft
records none of these later states as complete: plan independently approved;
plan committed; plan user-published; clean published baseline confirmed;
implementation authorized; implementation candidate complete; implementation
independently approved; implementation committed; implementation user-published;
and post-publication status synchronized.

The chronology this plan preserves is:

1. P4-S1 historically stopped at a constructible Run whose lifecycle was
   `pre_first_turn`.
2. P8-S2 implemented the narrow Session-backed Run-entry transaction. That
   application service creates Run revisions 1, 2, and 3 and owns the revision-3
   transition to `active`.
3. P8-S3 published the normal public adapter and normal composition that reach
   the P8-S2 service. P8-S3 did not originate the activation transition.
4. The baseline contains no P8-S4 implementation.
5. P8-S4, P8-S5, and P8-S6 are unstarted. Broader Phase 4 and full Run Protocol
   Phase 3.3 remain incomplete.
6. Phase 8, the Structured Player Character programme, and the overall project
   remain incomplete.

## B. Authority and precedence

### Scope owner

The approved and published Phase 8 owner is
`docs/structured_player_character_run_playable_loop_plan.md`. Its decisive
P8-S4 authority is:

- lines 1124-1204: purpose, exact production/test/support/documentation maxima,
  transaction boundary, and required evidence;
- lines 684-696: process-local repository/UoW parity, deterministic service
  composition, fixed Demo principal, and the necessary exposure of existing
  Player Character routes;
- lines 814-844: path-budget meaning and the exact seven Phase 8 documentation
  owners;
- lines 1359-1376: P8-S4 local verification tier;
- lines 1432-1454: documentation/status synchronization rules;
- lines 1206-1292: the separate P8-S5 and P8-S6 allocations.

Those passages define P8-S4 as Demo parity. They do not authorize a new
application transaction, a second route adapter, Web work, or final Phase 8
closure.

### Narrower contract owners

The following current authorities were inspected and have narrower ownership:

- `PLANS.md` lines 137-143, 405-431, 489-492, 674-734, and 757-768 own roadmap
  status, chronology, slice allocation, and the no-live-Provider baseline.
- `docs/structured_player_character_implementation_plan.md` lines 3771-3816
  and 3897-3921 own the broader Structured Player Character implementation
  chronology and retain P8-S4 through P8-S6 as incomplete.
- `docs/structured_player_character_contract.md` lines 852-913 and 1078-1109
  own the structured character identity, lifecycle, applicable-reference, and
  downstream status contract.
- `docs/run_protocol.md` lines 141-232 own the narrow Session-backed Run
  amendment, revisions 1/2/3, one-UoW authority, and incomplete broader Run
  Protocol boundary.
- `docs/public_client_contract.md` lines 945-1052 own the already-published
  `POST /v1/runs` request, response, error, replay, privacy, DTO, and OpenAPI
  boundary.
- `docs/architecture.md` lines 539-617 and 619-694 own the current composition,
  schema, Demo-process, and Web separation.
- `docs/engineering/guardrails.md` was inspected in full for persistence,
  authority, testing, Provider, and documentation rules.
- `docs/engineering/codex_workflow.md` was inspected in full for baseline
  invalidation, review, verification, documentation synchronization, and Git
  handoff rules.

Historical context was also inspected:

- `docs/structured_player_character_p8_s3_implementation_plan.md`, especially
  lines 65-157, 308-450, 904-1058, and 1060-1149, supplies prior-plan structure
  and chronology only. It is frozen historical evidence, not P8-S4
  implementation authority. Its verified identity is 1,165 lines, 67,566 raw
  bytes, SHA-256
  `f56ac9975667f2c0bd1547286897a1dd6e84b7c0e0be820f861369c1671c027d`.
- `docs/phase_3_2_deterministic_demo_environment.md` lines 103-219,
  519-692, and 1087-1195 describe the completed historical deterministic Demo
  baseline. Its old generator trace and route inventory are frozen evidence for
  that earlier topology, not a prohibition on the P8-S4 additions explicitly
  authorized by the current Phase 8 owner.

### Direct implementation evidence inspected

The plan also derives its path and symbol decisions from:

- `src/deviation_protocol/infrastructure/demo_persistence.py` lines 39-99,
  125-323, and 474-717;
- `src/deviation_protocol/infrastructure/demo_generators.py` lines 8-64;
- `src/deviation_protocol/api/demo_composition.py` lines 260-316;
- `src/deviation_protocol/api/dependencies.py`, especially `ApiServices`,
  `get_demo_dev_principal`, and the fail-closed service dependencies;
- `src/deviation_protocol/api/main.py`, especially the service-conditional
  Player Character and Run-entry route registration;
- `src/deviation_protocol/application/ports.py` lines 99-180 and 272-521;
- `src/deviation_protocol/application/player_character_service.py`, especially
  creation, discovery, retirement, and `lock_owned_for_binding`;
- `src/deviation_protocol/application/run_service.py` and
  `src/deviation_protocol/application/run_entry_service.py`, especially
  `RunEntryService.enter` and its replay reconstruction;
- `src/deviation_protocol/application/session_service.py`, especially the
  existing Run-entry preparation/staging split and its Session ID, seed, and
  initialization-event issuance order;
- `src/deviation_protocol/infrastructure/player_character_authority.py` and
  `src/deviation_protocol/infrastructure/run_authority.py` for existing issuers
  and controller-resolution seams, plus
  `src/deviation_protocol/domain/player_character_policies.py` and the existing
  domain authority-source reference types;
- `src/deviation_protocol/infrastructure/repositories.py` for the current
  `SqlAlchemyPlayerCharacterRepository`,
  `SqlAlchemyPlayerCharacterCreationReceiptRepository`,
  `SqlAlchemyPlayerCharacterMutationReceiptRepository`, Player Character
  current-row compare-and-swap, `SqlAlchemyRunRepository`,
  `SqlAlchemyRunCreationReceiptRepository`,
  `SqlAlchemyRunMutationReceiptRepository`, and
  `SqlAlchemyRunSessionParticipationRepository`; these own the applicable Run
  current-row compare-and-swap, participation and active-binding uniqueness
  enforcement, database conflict classification/translation, and repository-
  level operation ordering;
- `src/deviation_protocol/infrastructure/player_character_persistence.py` and
  `src/deviation_protocol/infrastructure/run_persistence.py` for stored
  carriers, canonical codecs, serialization/deserialization, domain
  reconstruction, and complete record-family integrity validation;
- `src/deviation_protocol/infrastructure/unit_of_work.py` for the existing
  SQLAlchemy one-session UoW composition;
- the current Demo unit, composition, script, and cross-process tests named in
  section G; and
- the P8-S2/P8-S3 service, API, composition, and real-MySQL tests as behavior
  evidence, not as P8-S4 edit targets.

### Precedence and dated wording

The hierarchy is: the current published Phase 8 plan owns slice allocation;
current contract documents own their narrower contracts; current source and
tests prove implemented behavior; a frozen slice plan describes its own
historical candidate; and older phase documents are read in their dated
context. A current narrower contract cannot expand P8-S4 beyond the parent
allocation, while implementation details cannot weaken a published invariant.

There is no material conflict. Statements that P4-S1 leaves Run at
`pre_first_turn`, that the historical Phase 3.2 Demo had no Player Character
service, and that P8-S3 left Demo entry unavailable are accurate at their
respective dates. The current Phase 8 owner expressly allocates removal of the
last limitation to P8-S4. The narrowest faithful interpretation is to extend
only the existing Demo persistence, deterministic generators, composition, and
their exact evidence owners.

## C. Problem statement

### Present behavior

Normal composition can execute the complete backend admission transaction
through the P8-S3 `POST /v1/runs` adapter. Demo composition cannot. At the
baseline:

- `DemoProcessStore` and `DemoUnitOfWork` implement only existing Session,
  turn-request, narrative-job, event, snapshot, and Provider-progress families;
- `DemoGenerators` has no deterministic Player Character, Run, or continuous-
  story-line identity family;
- `build_demo_runtime` constructs only `SessionService`, the narrative turn
  orchestrator, and deterministic narrative Provider;
- `ApiServices.player_character_service`, `.run_service`, and
  `.run_entry_service` remain unset; and
- service-conditional registration consequently omits the existing Player
  Character routes and `POST /v1/runs` from the Demo application.

The result is a playable-loop parity gap: the local deterministic backend still
starts by directly creating a legacy Session, instead of creating a structured
Player Character, discovering it, entering a Run, reading the authoritative
View, and following the existing action loop.

### Required post-P8-S4 behavior

One fresh Demo process must execute the already-published backend journey with
the fixed Demo principal:

```text
GET scenarios
-> POST player character
-> GET eligible player characters
-> POST run entry
-> GET authoritative Session View
-> existing canonical action/request-status/View loop
```

The Demo process must use deterministic Player Character, Run, line, Session,
event, job, lease, worker, seed, and clock sequences; process-local repository
and UoW implementations of every port exercised by the existing services; one
atomic store publication per mutation; detached reads; exact replay and
conflict behavior; and no MySQL or external Provider I/O.

This belongs to P8-S4 because the parent plan explicitly names it
“Deterministic Demo parity.” P8-S2 continues to own the atomic Run-entry
transaction and revision-3 activation; P8-S3 continues to own the public
adapter and DTO/OpenAPI behavior. P8-S5 owns Web connection. P8-S6 owns final
cross-surface evidence and programme-status closure.

## D. Goals and non-goals

### Goals

1. Implement all existing Player Character and Run repository/UoW ports inside
   the process-local Demo store with lock, CAS, receipt, uniqueness, rollback,
   atomic-publication, and detached-reconstruction parity.
2. Add independent deterministic identity sequences for Player Character, Run,
   and continuous-story-line identities without disturbing existing sequence
   families.
3. Compose the existing `PlayerCharacterService`, `RunService`, and
   `RunEntryService` in Demo with the existing fixed Demo principal and one
   shared process store, clock, scenario catalogue, and `SessionService`.
4. Make the already-completed Player Character create/read/retirement routes
   and P8-S3 `POST /v1/runs` route appear naturally through existing
   service-conditional route registration.
5. Prove deterministic create/list/enter success and replay, conflict and
   rollback behavior, revision-3 active state, exact binding and participation,
   process restart loss, two-process determinism, complete generator/store
   reconstruction, canonical action continuity, and absence of external I/O.

### Non-goals

- P8-S5 Web API methods, controller/store/view work, browser recovery, or UI.
- P8-S6 cross-surface closure, Full verification, final Phase 8 evidence
  consolidation, or completion claims.
- Any broader Phase 4 lifecycle, multi-Session Run, terminal Run, Run resume,
  later scenario, world, visit, line-continuation, or Phase 3.3 work.
- Any new public route, request field, response field, error code, DTO, OpenAPI
  schema, authentication mechanism, or public retirement control.
- Any Provider selection, real Provider call, network fallback, credential
  access, prompt change, or deterministic narrative behavior change.
- Any ORM, Alembic, MySQL schema, persistence-port, or migration redesign.
- Any dependency, configuration, generated-artifact, normal-composition, or
  production-ASGI change.
- Broad refactoring, formatting, historical-document rewriting, or unrelated
  documentation cleanup.
- Changing P8-S2 replay/transaction policy or moving its one-commit authority
  into Demo composition.
- Treating Demo process-local receipts as durable across a process restart.

## E. Existing reusable mechanisms

### Application and authority

1. `src/deviation_protocol/application/player_character_service.py` —
   `PlayerCharacterService`, including `create`, discovery/read, retirement,
   and `lock_owned_for_binding`.
   It owns declaration policy, controller authority, lifecycle, receipts,
   projections, and commits. P8-S4 constructs it unchanged over Demo ports. It
   must not duplicate character policy or ownership decisions in persistence or
   composition.

2. `src/deviation_protocol/application/run_service.py` — `RunService` and its
   staged revision/binding/session-attachment helpers.
   It owns canonical Run transitions and receipt construction. P8-S4 supplies
   its existing ports and deterministic issuers; it must not hand-build Run
   models in the Demo adapter.

3. `src/deviation_protocol/application/run_entry_service.py` —
   `RunEntryService.enter` and replay reconstruction.
   It already owns controller resolution, Player Character lock/admission,
   server identity issuance, revisions 1/2/3, Session creation, participation,
   activation, receipts, exact replay, one commit, and result projection. P8-S4
   composes it unchanged and implements the locking reads it calls. No second
   coordinator is permitted.

4. `src/deviation_protocol/application/session_service.py` — `SessionService`.
   It already stages initialization into a caller-supplied UoW and supports the
   existing legacy Session route. Demo composition must build exactly one
   instance and pass that same instance both to `ApiServices` and the entry
   service.

5. `src/deviation_protocol/infrastructure/player_character_authority.py` —
   `ConfiguredControllerBindingResolver`, `ConfiguredControllerBinding`,
   and `Uuid4PlayerCharacterIdIssuer`; and
   `src/deviation_protocol/domain/player_character_policies.py` —
   `CreatePlayerCharacterPolicy`.
   Demo must instantiate the resolver from explicit fixed Demo values rather
   than environment, and adapt deterministic strings to the existing typed ID
   issuer protocol. It must not reuse production UUID, wall-clock, or
   environment-loading builders.

6. `src/deviation_protocol/infrastructure/run_authority.py` —
   `Uuid4RunIdIssuer` and `Uuid4ContinuousStoryLineIdIssuer`, together with the
   issuer protocols in `application/ports.py` and `RunAuthoritySourceRef` in
   `domain/run.py`.
   Demo uses typed wrappers around deterministic strings and a fixed Demo source
   reference. It does not expose these internals publicly.

### Ports, persistence behavior, and errors

7. `src/deviation_protocol/application/ports.py` lines 99-180 and 291-521 —
   the complete Session, Player Character, Run, receipt, participation, and UoW
   contracts.
   P8-S4 implements these exact ports in `demo_persistence.py`. It must not add a
   parallel interface or weaken locking methods into unlocked fallbacks.

8. `src/deviation_protocol/infrastructure/demo_persistence.py` —
   `DemoProcessStore.snapshot`, `DemoSessionRepository`, and `DemoUnitOfWork`.
   The current design already provides deep/detached reads, per-aggregate locks,
   staged mutation, rollback, commit serialization, copy-on-write validation,
   and all-at-once publication. P8-S4 extends the same store and publication,
   rather than constructing a second store or committing repositories
   independently.

9. `src/deviation_protocol/infrastructure/repositories.py` — current
   `SqlAlchemyPlayerCharacterRepository`,
   `SqlAlchemyPlayerCharacterCreationReceiptRepository`,
   `SqlAlchemyPlayerCharacterMutationReceiptRepository`,
   `SqlAlchemyRunRepository`, `SqlAlchemyRunCreationReceiptRepository`,
   `SqlAlchemyRunMutationReceiptRepository`, and
   `SqlAlchemyRunSessionParticipationRepository`.
   This is inspection-only operational evidence for current-row CAS execution,
   locking, repository call ordering, participation and active-binding
   uniqueness, and database conflict classification/translation. P8-S4 mirrors
   the applicable port semantics in Demo but does not edit or import the
   SQLAlchemy implementation.

10. `src/deviation_protocol/infrastructure/player_character_persistence.py` —
   `PlayerCharacterStoredRecordIntegrityError`, canonical record/receipt
   round-trip helpers, and `validate_stored_player_character_record_set`.
   These pure stored-carrier dataclasses and codecs define integrity and
   detached reconstruction without depending on ORM rows. Demo must store those
   carriers, reconstruct through those codecs, validate the complete carrier
   family, and fail closed on corrupt evidence rather than inventing a weaker
   in-memory representation.

11. `src/deviation_protocol/infrastructure/run_persistence.py` —
    stored carriers, shared Run integrity/repository error-type definitions,
    receipt and creation-evidence codecs, canonical reconstruction, and
    `validate_stored_run_record_set`.
    Demo must store these pure carrier records, preserve exact evidence bytes,
    and reconstruct fresh canonical objects through these helpers. It must not
    return aliases, create a second receipt/evidence serialization, or treat
    this carrier module as the owner of SQL CAS, database uniqueness
    enforcement, or database conflict translation.

12. `src/deviation_protocol/infrastructure/unit_of_work.py` —
    `SqlAlchemyUnitOfWork`.
    This is semantic parity evidence: every repository shares one transaction,
    repositories do not commit, and the UoW is the publication boundary. Demo
    must reproduce those semantics without importing SQLAlchemy or MySQL.

### API, DTO, privacy, and composition

13. `src/deviation_protocol/api/dependencies.py` — `ApiServices`, fixed
    `get_demo_dev_principal`, and fail-closed service dependencies.
    P8-S4 fills the three existing optional service slots. It must not create a
    new principal path or allow request data to establish authority.

14. `src/deviation_protocol/api/main.py` — existing conditional Player
    Character and Run-entry registration and existing adapters.
    Supplying services is sufficient to expose the routes. P8-S4 changes no
    adapter, DTO, error mapping, serialization, or OpenAPI declaration.

15. `src/deviation_protocol/api/demo_composition.py` —
    `build_demo_runtime` and `DemoRuntime`.
    This remains the sole explicit Demo composition root. It retains the
    deterministic Provider guard and `engine=None`, and adds the existing
    services over the same store/generators/catalogue.

16. `src/deviation_protocol/infrastructure/demo_generators.py` —
    `DemoStringSequence`, `DemoLogicalClock`, `DemoSeedSequence`,
    `DemoGenerators`, and `new_demo_generators`.
    P8-S4 adds independent fields using the existing sequence mechanism. It
    must not couple new identity consumption to any old category.

### Test topology

17. `tests/unit/test_demo_persistence.py` — existing rollback, atomicity,
    optimistic-lock, and detached-read fixtures are extended for the new port
    families.
18. `tests/unit/test_demo_composition.py` — current line 46 test deliberately
    proves Player Character routes are absent; it becomes the exact route and
    service parity assertion. Lines 960-973 freeze generator independence and
    must include all new fields.
19. `tests/unit/test_run_composition.py` —
    `test_demo_composition_remains_independent_of_run_entry` still freezes the
    older Demo-exclusion expectation. P8-S4 replaces only that obsolete
    assertion with Demo Run-entry composition ownership while preserving every
    unrelated normal-composition assertion.
20. `tests/unit/test_player_character_api.py` —
    `test_demo_composition_gets_no_player_character_route_or_schema` still
    freezes the older Demo-exclusion expectation. P8-S4 replaces only that
    obsolete assertion with the already-existing Player Character route/schema
    exposure produced by Demo service composition.
21. `tests/e2e/test_demo_cross_process_replay.py` and
    `tests/e2e/support/demo_replay_child.py` — the existing two-process harness,
    trace protocol, no-network guard, public transcript, child-side complete
    field manifests, private source representation, and canonical 19-action
    sequence are expanded in place.
22. `tests/unit/test_demo_scripts.py` is conditional only if the later
    implementation preflight proves that its launcher or smoke assertions
    enumerate the exact affected route inventory. A complete current read and
    exact route-literal search found no such assertion, so the predicate remains
    inactive.

## F. Contract and invariant preservation

P8-S4 must preserve all of the following:

1. The server owns principal/controller resolution, identity issuance,
   lifecycle, revisions, scenario validation, binding, Session initialization,
   participation, receipts, and all state mutation.
2. Demo authority is the existing fixed principal (`demo-player` under
   authentication scheme `demo-dev-only`) resolved to one explicit fixed
   controller binding. Public bodies, query strings, and idempotency keys never
   establish ownership or controller authority.
3. Player Character ownership is part of the repository query/lock boundary.
   Missing, foreign, and unavailable ownership remain non-enumerating.
4. `PlayerCharacterId`, `RunId`, `ContinuousStoryLineId`, and Session identity
   remain distinct opaque types. Deterministic values must satisfy their
   existing grammar and length limits.
5. Character revision and lifecycle checks remain application-owned. Run entry
   accepts only the exact owned, active, currently unbound revision selected by
   the client from an authoritative projection.
6. Run revision 1 is creation at `pre_first_turn`; revision 2 records the exact
   immutable applicable-character binding; revision 3 attaches the first
   Session participation and changes the Run to `active`. P8-S2 remains the
   origin of this transition.
7. Current supported state versions, event types, mutation kinds, receipt
   schemas, and scenario initialization event remain unchanged. P8-S4 creates
   no new domain token.
8. The scenario's static character definition remains a current Session
   compatibility fixture and is never substituted for the Run-bound Structured
   Player Character.
9. One application service owns each mutation transaction. All Demo
   repositories stage only; one `DemoUnitOfWork.commit` validates and publishes
   every involved family atomically.
10. Rollback, cancellation before publication, CAS failure, uniqueness failure,
    or integrity failure publishes none of a mutation's staged families, but it
    never rewinds a deterministic value that a generator has already emitted.
11. Lock semantics must serialize controller creation, character binding,
    active-Run lookup, Run replay, and Session identity claims in the same
    aggregate order expected by the existing services. Locks are released on
    commit, rollback, exception, and cancellation.
12. Character current/revision/allocation and Run current/revision/binding/
    participation relationships are complete and internally consistent at
    every published snapshot.
13. Player Character creation/mutation receipts and Run creation/mutation
    receipts are controller-scoped and operation-scoped exactly as their
    existing key types require. Receipt evidence is canonical and reconstructed
    strictly.
14. Exact receipt replay returns the original stable result before any generator
    is invoked. It consumes no new clock, Player Character, Run, line, Session,
    seed, event, job, lease, or worker value; mutates no state; advances no
    version; creates no Session; and performs no commit. Same-key incompatible
    evidence remains an idempotency conflict.
15. A different key for an already-bound character remains ineligible and does
    not reveal the existing Run. A losing race cannot publish a second Run,
    Session, participation, or binding.
16. Process-local receipt recovery is available only for the life of one Demo
    process. Restart intentionally loses all authoritative state and receipts;
    this is proved, not hidden or converted into durable recovery.
17. All repository reads and `DemoStoreSnapshot` values are detached. Caller
    mutation can never mutate authoritative state or future replay evidence.
18. Public success and error serialization continues through the P8-S1/P8-S3
    DTOs and adapters. No domain model, persistence carrier, receipt,
    controller binding, issuer/source, line ID, SQL, lock, or Provider detail is
    added to public output or OpenAPI.
19. Expected domain rejections retain their exact public status/code. Corrupt
    evidence, impossible state, persistence errors, and externally uncertain
    public outcomes retain their existing sanitized/recovery contract.
    Cancellation propagates. The process-local, non-awaiting final publication
    sequence does not invent a database/network commit-uncertainty window.
20. A View read after committed Run entry is a separate authoritative read. A
    View failure does not undo the committed admission; retry uses the returned
    Session ID and existing View recovery rules.
21. Existing action, request-status, View, stale, pending, uncertain, and
    Provider-failure rules remain unchanged after admission.
22. Scenario completion ends the Session projection but not the Run. The Run
    remains `active`, bound, and linked to immutable participation.
23. Demo remains process-local, temporary, deterministic, non-production,
    `engine=None`, and isolated from normal composition.
24. No real Provider, database, external network, credentials, environment-based
    Provider selection, or live model is contacted by P8-S4. The existing
    cross-process harness may use loopback-only HTTP under its socket guard.

### Deterministic generator issuance and transaction boundary

The generator boundary is process-lifetime monotonic state, separate from
transactionally published persistence state. The rule applies independently to
every generator field the current Demo exposes or P8-S4 requires: existing
`clock`, `session_id`, `event_id`, `job_id`, `lease_token`, `worker_id`, and
`seed`, plus the authorized new `player_character_id`, `run_id`, and
`continuous_story_line_id` fields. No other generator category is introduced.

1. **Rejection before issuance.** If an expected rejection, validation failure,
   ownership failure, receipt replay, receipt mismatch, or other decision is
   completed before any generator is invoked, no generator position advances,
   no value is consumed, and no staged or authoritative entity is created.
   Exact idempotent receipt replay must return its recorded result before
   invoking any generator and consume no new clock, identity, Session, seed, or
   event value.
2. **Value already issued.** Once a generator call has emitted a value, that
   value is permanently consumed for the lifetime of the current process.
   Rollback, cancellation, a later conflict or integrity rejection, and
   exception exit do not rewind it; no later entity or transaction in that
   process may reuse it.
3. **Partial issuance.** If a service emits some values and then fails or is
   cancelled before later generators are invoked, every emitted value remains
   consumed, every not-yet-invoked stream remains unconsumed, and independent
   streams do not shift merely because another stream advanced. The current
   fresh Run-entry order is clock, Run ID, continuous-story-line ID, Session ID,
   seed, then initialization-event ID. The current first-controller character
   creation may consume its binding timestamp before Player Character identity;
   later call-site validation and staging must preserve the same partial-
   issuance rule rather than infer a transactional counter reset.
4. **Authoritative commit.** A successful commit validates and atomically
   publishes all staged persistence families and retains every value already
   consumed during the service call. Commit success does not itself invoke a
   generator or advance one a second time. Generator counters must not enter
   `DemoStoreSnapshot`, the authoritative store maps, UoW staged state, clone
   validation, atomic publication, or rollback state.
5. **Cancellation and publication.** Before atomic publication, cancellation
   discards staged persistence and releases locks while already emitted values
   remain consumed. The final process-local publication sequence performs no
   await or external database/network operation. After it completes, the
   authoritative mutation remains committed even if cancellation or a View/
   projection failure occurs later. Existing outward uncertain-result and
   receipt-recovery behavior remains public contract, but it must not be
   described as an uncertain process-local database commit.
6. **Process restart.** A fresh process alone resets generator positions. It
   begins with empty Demo storage and the deterministic initial generator state,
   so it may reproduce the canonical fresh-process journey. Restart determinism
   never permits same-process reuse after rollback, conflict, exception, or
   cancellation.

## G. Exact future implementation inventory

The inventories below are the only authorized forecast for a later separately
authorized P8-S4 implementation. They do not authorize edits now.

### 1. Mandatory production paths — 3

1. `src/deviation_protocol/infrastructure/demo_persistence.py`
   Extend `DemoStoreSnapshot`, `DemoProcessStore`, repository implementations,
   and `DemoUnitOfWork` with all existing Player Character and Run port
   families; genuine locking reads; CAS and uniqueness; receipt/evidence
   storage; Session replay reads; detached reconstruction; staged rollback; and
   one complete atomic publication.
2. `src/deviation_protocol/infrastructure/demo_generators.py`
   Add independent deterministic `player_character_id`, `run_id`, and
   `continuous_story_line_id` fields with exact first values
   `pc.demo-00000001`, `run.demo-00000001`, and `csl.demo-00000001` and
   eight-digit monotonically increasing suffixes. Existing sequence outputs and
   independence remain unchanged.
3. `src/deviation_protocol/api/demo_composition.py`
   Build one explicit fixed Demo controller resolver, typed deterministic
   issuers, `PlayerCharacterService`, `RunService`, the existing single
   `SessionService`, and `RunEntryService`; populate the existing `ApiServices`
   slots while preserving the deterministic Provider guard and zero normal-
   composition fallback.

`src/deviation_protocol/infrastructure/repositories.py` is inspection-only
operational evidence and remains outside this mandatory production inventory.
Its SQLAlchemy CAS, uniqueness, conflict-translation, and operation-ordering
behavior is not edited or imported into Demo.

### 2. Mandatory test/support paths — 6

1. `tests/unit/test_demo_persistence.py`
   Add focused port-parity, detached-reconstruction, CAS, receipt, uniqueness,
   lock/race, rollback, and one-publication tests for every new store family.
2. `tests/unit/test_demo_composition.py`
   Replace the deliberate no-route assertion with exact service/route/OpenAPI
   parity; extend generator and isolation tests; and prove the full in-process
   public create/list/enter/View/action path plus replay/conflict behavior.
3. `tests/unit/test_run_composition.py`
   Replace only `test_demo_composition_remains_independent_of_run_entry` and
   preserve every unrelated normal-composition assertion. Prove that Demo owns
   the already-existing Run-entry service slot without changing normal
   composition or P8-S2 transaction ownership.
4. `tests/unit/test_player_character_api.py`
   Replace only
   `test_demo_composition_gets_no_player_character_route_or_schema` and preserve
   every unrelated Player Character API assertion. Prove that populating the
   existing Demo service slot exposes the already-existing routes and schemas;
   no new adapter, DTO, or OpenAPI shape is added.
5. `tests/e2e/test_demo_cross_process_replay.py`
   Expand trace categories, transcript normalization, expected generator
   sequence, two-fresh-process comparisons, restart-loss evidence, public
   backend journey, and frozen digests while preserving the canonical action
   sequence and harness hardening.
6. `tests/e2e/support/demo_replay_child.py`
   Reconstruct every expanded `DemoGenerators` field; enumerate every expanded
   `DemoStoreSnapshot` field; serialize and validate the complete private
   Player Character/Run/receipt/participation representation; execute the new
   public journey; and retain no-network enforcement.

The first five paths are direct pytest test owners. The executable child
`tests/e2e/support/demo_replay_child.py` is mandatory support evidence and
counts toward the test/support budget because the cross-process owner launches
it. It need not be invoked as an independent pytest target unless repository
structure later requires that behavior.

**Mandatory implementation-and-test total:** 9 unique paths: 3 production plus
6 test/support paths.

### 3. Mandatory migration paths — 0

No migration or ORM path is required or permitted. P8-S4 is process-local; the
existing port contracts already cover its data, and published schema
`20260729_0005` already supports the normal/MySQL behavior. Evidence that any
migration or ORM edit is necessary is a stop condition.

### 4. Mandatory configuration, dependency, and generated paths — 0

**Configuration paths:** 0. **Dependency paths:** 0. **Generated paths:** 0.

No configuration, dependency manifest/lockfile, environment file, generated
OpenAPI file, generated client, scenario pack, launcher, Provider-selection, or
normal-composition path is required. Runtime OpenAPI is verified from the
existing app. A newly generated or dependency path is a stop condition.

**Mandatory migrations/configuration/dependencies/generated total:** 0 paths.

### 5. Mandatory post-publication documentation synchronization — 7

After the P8-S4 implementation candidate receives exactly
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`,
then receives separate commit authorization, is committed, and is
user-published, inspect and synchronize these exact owners in a separate status
candidate. The implementation-review verdict alone does not authorize this
documentation synchronization:

1. `PLANS.md`;
2. `docs/architecture.md`;
3. `docs/public_client_contract.md`;
4. `docs/run_protocol.md`;
5. `docs/structured_player_character_contract.md`;
6. `docs/structured_player_character_implementation_plan.md`;
7. `docs/structured_player_character_run_playable_loop_plan.md`.

**Mandatory post-publication documentation-sync total:** 7 unique paths.
These are outside both the 9-path mandatory implementation/test budget and the
10-path conditional maximum. All seven remain later status or contract owners
and may be synchronized only after the separately reviewed P8-S4 implementation
is committed and user-published. Neither this plan-correction task nor the
future implementation candidate authorizes their earlier edit. No eighth
documentation path is necessary solely because of this correction.

### 6. Conditional path — 1 maximum, presently inactive

`tests/unit/test_demo_scripts.py` may change only if the later implementation
preflight proves that its launcher or smoke assertions enumerate the exact
affected route inventory. A complete current read and exact search found no
such assertion, so this objective predicate remains inactive.

If activated without authority drift, the only permitted change is the narrow
expected route inventory; no script, launcher, smoke process, scenario
validation, environment, or dependency behavior may change. This makes the
test/support maximum 7 and the implementation/test maximum 10. Any different
reason to edit that path, or any other conditional path, requires plan
reassessment. No second conditional path is authorized.

## H. Detailed implementation sequence

### Step 0 — freeze and revalidate the candidate

- **Paths/symbols:** this plan, the P8-S3 frozen plan, Git refs, and inventories
  in section G.
- **Behavior:** verify the later approved P8-S4 plan identity, the reviewer's
  binding SHA-256, the exact plan-review verdict
  `STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_PLAN_INDEPENDENT_REVIEW_APPROVED`,
  the clean published baseline, and the conditional-test predicate before
  editing.
- **Boundary:** read-only inputs; no production output.
- **Invariant:** no work begins from drift, a byte/hash mismatch, a generic or
  differently named verdict, an unpublished plan, or an implementation task not
  separately bound to the clean published baseline.
- **Failure:** stop on any section M condition.
- **Evidence before continuing:** exact hashes/status/ref checks and an explicit
  nine-mandatory-path implementation/test budget, the sole inactive
  conditional path and 10-path maximum, and zero migration/configuration/
  dependency/generated paths.
- **P8-S2/P8-S3 interaction:** confirm their implementations remain unchanged.

### Step 1 — add deterministic identity families

- **Path/symbol:** `src/deviation_protocol/infrastructure/demo_generators.py` —
  `DemoGenerators` and `new_demo_generators`.
- **Behavior:** add three independent callable fields producing valid,
  recognizable, monotonically numbered Player Character, Run, and line IDs.
  Use `DemoStringSequence("pc.demo-", width=8)`,
  `DemoStringSequence("run.demo-", width=8)`, and
  `DemoStringSequence("csl.demo-", width=8)`; do not alter old families.
- **Input/output:** no input beyond process-local counter state; output existing
  opaque-ID-compatible strings, later wrapped as domain ID values. Each call
  advances its own process-lifetime position when it emits the value.
- **Invariant:** independent monotonic deterministic consumption; no UUID, wall
  clock, random source, environment, cross-family counter, UoW snapshot, or
  rollback-restorable counter state.
- **Failure:** sequence exhaustion before emission consumes nothing. Once a
  value is emitted, later typed-ID validation failure, exception, conflict,
  rollback, or cancellation leaves it consumed.
- **Evidence:** focused generator and service-boundary tests prove first/second
  values, grammar, width, old outputs, pre-issuance non-consumption,
  post-issuance permanent consumption, partial issuance, and independence.
- **Reuse:** existing Demo sequences replace only production issuers; P8-S2
  still decides when identity issuance occurs, including no issuance on replay.

### Step 2 — define complete process-store state and detached clones

- **Path/symbol:** `src/deviation_protocol/infrastructure/demo_persistence.py` —
  clone helpers, `DemoStoreSnapshot`, and `DemoProcessStore`.
- **Behavior:** use the existing pure carrier types from
  `player_character_persistence.py` and `run_persistence.py`. Add these exact
  snapshot/store maps: `controller_bindings` keyed by binding value;
  `player_character_id_allocations` keyed by character ID;
  `player_character_revisions` keyed by `(character_id, revision)`;
  `player_character_current` keyed by character ID;
  `player_character_creation_receipts` keyed by normalized
  `(controller, namespace, operation_id)`;
  `player_character_mutation_receipts` keyed by normalized
  `(character_id, namespace, operation_id)`; `run_revisions` keyed by
  `(run_id, state_version)`; `run_current` keyed by Run ID;
  `run_participations` keyed by Session ID; `run_creation_receipts` keyed by
  `(namespace, operation_id)`; and `run_mutation_receipts` keyed by
  `(run_id, namespace, operation_id)`. Player Character receipt carriers retain
  their strictly derived command/source evidence; Run creation receipt carriers
  retain the canonical P8-S2 creation-evidence bytes. Add private controller,
  character, Run, and Session lock registries. `snapshot()` returns a complete
  detached copy of every public store field; locks remain private and absent
  from it. Generator positions remain outside the store, snapshot, UoW, staged
  state, and publication clone.
- **Input/output:** existing services supply canonical domain/receipt values;
  repository staging converts them to the existing frozen stored-carrier
  records and canonical bytes; reads return strictly reconstructed detached
  domain values. Normalized string/tuple keys are derived only from already
  validated typed opaque values and are rendered explicitly only by tests.
- **Invariant:** no alias reaches authoritative state; all record families can
  be validated as a complete set; lock registries are not exposed as persisted
  snapshot fields.
- **Failure:** malformed stored objects, mismatched keys, versions, ownership,
  binding, evidence bytes, or family relationships raise the existing relevant
  integrity error and never become a normal miss.
- **Evidence:** snapshot field-manifest, clone-mutation, corrupt-carrier, and
  complete-family tests pass before repository composition begins.
- **Reuse:** preserve current Session/store fields and the P8-S2 carrier shapes;
  do not duplicate SQL row schema.

### Step 3 — implement Player Character repositories

- **Path/symbol:** `demo_persistence.py` — new
  `DemoControllerBindingRegistryRepository`,
  `DemoPlayerCharacterRepository`,
  `DemoPlayerCharacterCreationReceiptRepository`, and
  `DemoPlayerCharacterMutationReceiptRepository`, implementing their like-named
  existing port contracts.
- **Behavior:** implement get/lock/add for controller bindings; allocation
  reservation; detached get and genuine `get_for_update`; stable bounded
  eligible listing; initial/revision writes; current CAS; and exact receipt
  reads/writes. Reads see authoritative plus same-UoW staged values where the
  application contract requires it.
- **Input/output:** existing domain IDs, bindings, canonical records, receipt
  keys, receipts, revisions, and timestamps only.
- **Invariant:** one controller maps to itself, allocations never recycle,
  current and revision rows agree, revision history is immutable, listing is
  owned/active/unbound and capped by the service, CAS checks the expected old
  revision, and receipt keys/evidence are exact.
- **Failure:** known binding, write, mutation-receipt, or CAS races use existing
  conflict categories; corrupt state uses the existing stored-record integrity
  category; nothing commits at repository level.
- **Evidence:** create/replay, listing/filter/cap/order, foreign/missing,
  retirement receipt/CAS, duplicate, corruption, lock serialization, detached
  reads, and rollback tests.
- **Reuse:** `PlayerCharacterService` remains the only policy/commit owner;
  `lock_owned_for_binding` consumes this genuine character lock. Mirror the
  current SQLAlchemy CAS, receipt, conflict-classification, and operation-order
  semantics inspected in `repositories.py`; use
  `player_character_persistence.py` only for carrier, codec, reconstruction,
  and complete-family-validation responsibilities.

### Step 4 — implement Run, receipt, and participation repositories

- **Path/symbol:** `demo_persistence.py` — new `DemoRunRepository`,
  `DemoRunCreationReceiptRepository`, `DemoRunMutationReceiptRepository`, and
  `DemoRunSessionParticipationRepository`, implementing their existing port
  contracts.
- **Behavior:** implement detached get and `get_for_update`; active-character
  lookup and locking lookup; session-attachment lock evidence; initial and
  immutable revision writes; current CAS; exact creation evidence and receipt
  reconstruction; mutation receipts; and immutable Session participation.
- **Input/output:** existing `RunId`, `PlayerCharacterId`, canonical Runs,
  `RunReceiptKey`, success receipts, `RunEntryCreationEvidence`, participation,
  state versions, and timestamps.
- **Invariant:** Run/line IDs are unique, revision history is immutable and
  contiguous for service-issued transitions, current equals the latest
  revision, at most one active Run binds a character, each Session has one
  participation, evidence canonical bytes match the typed evidence, and CAS
  uses the expected prior state version.
- **Failure:** use the existing Run write, active-binding, participation, and
  receipt uniqueness categories so `RunEntryService` can map known races;
  impossible/corrupt families fail as integrity errors.
- **Evidence:** revisions 1/2/3, active binding, participation, creation
  evidence, exact/incompatible receipt, CAS, duplicate/race, detached read,
  corruption, and rollback tests.
- **Reuse:** `RunService` builds every record/receipt; the Demo repository only
  stores, reconstructs, locks, compares, and stages it. Mirror the current
  SQLAlchemy Run CAS, receipt, participation/active-binding uniqueness,
  conflict-translation, and operation-order semantics inspected in
  `repositories.py`; use `run_persistence.py` only for carrier, codec,
  reconstruction, complete-family-validation, and shared error-type-definition
  responsibilities.

### Step 5 — complete Session replay reads and atomic UoW publication

- **Path/symbol:** `demo_persistence.py` — `DemoSessionRepository` methods
  `get_owned_for_update`, `get_latest_snapshot_for_update`, and
  `get_initialization_event`; `DemoUnitOfWork.__aenter__`, `commit`, `rollback`,
  lock release, staged state, validation, and `_publish_atomically`.
- **Behavior:** provide genuine locking reads required by P8 replay. Attach all
  new repositories to one UoW. Clone every existing and new map under the commit
  lock, recheck CAS/uniqueness/integrity against the latest store, apply all
  pending values to clones, then swap every store family as one publication.
  Clear staged state and release all held locks on every exit path. Do not clone,
  stage, publish, restore, or otherwise transact any generator counter.
- **Input/output:** the staged outputs of existing services; one complete new
  store state or no state change.
- **Invariant:** no partially visible Player Character, Run, line, Session,
  snapshot, event, participation, or receipt family; replay locking cannot use
  the base unlocked fallback; existing narrative UoW behavior remains intact.
- **Failure:** pre-publication exception/cancellation discards staged
  persistence but retains all values already emitted; a conflict detected at
  final validation raises its exact category without rewinding generators; no
  automatic retry. Streams not yet invoked remain unconsumed. The final
  publication sequence contains no await or external I/O. Once the single
  in-memory publication completes, the commit is authoritative; later
  cancellation or projection failure does not undo it.
- **Evidence:** injected failure at each family and generator boundary,
  concurrent loser, replay with locks, cancellation before/after issuance,
  commit-once with no second advance, rollback-idempotence for persistence plus
  permanent generator consumption, and old Session/turn/Provider tests all
  pass.
- **Reuse:** P8-S2 continues to call one `uow.commit`; P8-S3 adapter owns no UoW.

### Step 6 — compose existing services in Demo

- **Path/symbol:** `src/deviation_protocol/api/demo_composition.py` —
  `build_demo_runtime`.
- **Behavior:** instantiate one explicit fixed Demo controller binding/resolver;
  deterministic typed ID issuers and Demo authority sources; the existing
  create policy; one `PlayerCharacterService`; one `SessionService`; one
  `RunService`; and one `RunEntryService` through the existing pure
  `build_run_entry_service(run_service=..., session_service=...)` helper using
  those exact instances and the shared store/catalogue/clock. Populate existing
  `ApiServices` fields. Retain the existing deterministic Provider, guard,
  orchestrator, and `engine=None`.
- **Input/output:** optional injected process store, generators, and
  deterministic Provider in; `DemoRuntime` with the same public shape but a
  complete service set out.
- **Exact authority/constants:** bind (`authentication_scheme="demo-dev-only"`,
  `player_id="demo-player"`) to `controller_id="binding.demo-player"`; use
  `AuthoritySourceRef(value="source.demo-player-character")` and
  `RunAuthoritySourceRef(value="source.demo-run")`. Private typed issuer
  classes `_DemoPlayerCharacterIdIssuer`, `_DemoRunIdIssuer`, and
  `_DemoContinuousStoryLineIdIssuer` call the three new generator fields and
  construct the existing `PlayerCharacterId`, `RunId`, and
  `ContinuousStoryLineId` types. Set the existing Player Character
  `binding_integrity_guard_enabled=True` exactly as normal composition does.
- **Invariant:** the fixed dependency principal resolves to the fixed controller;
  no environment, SQL engine, production builder, UUID, wall clock, network, or
  external Provider construction; no duplicate `SessionService` or store.
- **Failure:** invalid fixed composition is startup failure, never a request-time
  fallback to production.
- **Evidence:** exact service identity/wiring assertions, forbidden-constructor
  probes, isolated ASGI import, and exact route/OpenAPI inventory.
- **Reuse:** existing conditional route registration exposes already-completed
  endpoints; no P8-S3 API code changes.

### Step 7 — prove the public journey and correct obsolete composition exclusions

- **Paths/symbols:** `tests/unit/test_demo_composition.py` — Demo ASGI tests;
  `tests/unit/test_run_composition.py` —
  `test_demo_composition_remains_independent_of_run_entry`; and
  `tests/unit/test_player_character_api.py` —
  `test_demo_composition_gets_no_player_character_route_or_schema`.
- **Behavior:** drive valid minimal character creation with an idempotency key;
  discover the detached eligible projection; enter using revision 1 and the
  canonical scenario; assert the stable result; read View; and continue through
  representative existing action behavior. Repeat exact create and enter keys,
  exercise incompatible reuse/stale/already-bound/foreign behavior, and inspect
  authoritative snapshots after each result. Replace only the two named older
  Demo-exclusion assertions with expectations matching the existing service-
  conditional registration; preserve all unrelated normal-composition and
  Player Character API assertions.
- **Input/output:** public HTTP only for journey assertions; private snapshot
  only for test evidence.
- **Invariant:** public DTO/error/OpenAPI identity is unchanged, replay consumes
  no generators and mutates nothing, and public output leaks no internal fields.
- **Failure:** expected errors retain exact sanitized envelopes; a forced View
  failure leaves successful Run entry committed and recoverable by a View retry.
- **Evidence:** the three focused pytest owners pass with exact state/public
  assertions and narrow proof that Demo gains the existing Run-entry and Player
  Character surfaces without changing normal composition, routes, schemas, or
  DTOs.
- **Reuse:** the P8-S3 route/DTO is exercised, not reimplemented.

### Step 8 — expand cross-process deterministic evidence

- **Paths/symbols:** `tests/e2e/support/demo_replay_child.py` complete generator/
  snapshot reconstruction and public driver; then
  `tests/e2e/test_demo_cross_process_replay.py` trace parser, expectations,
  digests, process/restart tests.
- **Behavior:** make character create/discovery/entry the canonical setup before
  the unchanged 19 actions. Add exact new trace categories and full private
  store families. Compare two fresh processes under distinct hash seeds for
  byte-identical public and generator traces; prove caller-identity
  normalization where already supported; start another process and prove state
  loss plus deterministic sequence reset.
- **Input/output:** loopback-only child ASGI HTTP and dedicated generator trace
  pipe; deterministic transcript, trace, and complete private representation.
- **Invariant:** child reconstructs every field explicitly; no category or store
  family can be silently omitted; no non-loopback I/O; canonical action order
  and terminal state stay unchanged; frozen digests update only for the
  authorized topology.
- **Failure:** unexpected field/category, partial trace, child hang/nonzero,
  external socket, digest drift, or restart persistence fails the test.
- **Evidence:** focused cross-process file passes all normal and hardened harness
  cases in two fresh OS processes.
- **Reuse:** retain the existing executable child and harness; do not create a
  second replay program.

### Step 9 — evaluate the conditional script-test path

- **Path/symbol:** `tests/unit/test_demo_scripts.py`, only if the later
  implementation preflight proves that its launcher or smoke assertions
  enumerate the exact affected route inventory.
- **Behavior:** repeat the exact route-inventory search after preceding edits.
- **Input/output:** test text/collection in; either no edit or a narrow expected
  route-set update.
- **Invariant:** launchers and smoke behavior remain unchanged.
- **Failure:** any required non-inventory change stops for reassessment.
- **Evidence:** record the predicate and focused result.
- **Reuse:** no new launcher or smoke script.

### Step 10 — verify and preserve the later synchronization boundary

- **Paths/symbols:** the exact implementation/test inventory in section G during
  implementation; only the exact seven documentation owners in section G.5 in
  a later, separate post-publication synchronization candidate.
- **Behavior:** complete focused and broad local verification and freeze the
  implementation candidate without editing the seven documentation owners.
  Only after independent implementation approval, a separately authorized
  implementation commit, and user publication may a separate candidate record
  the actual implementation identity and remaining-slice status.
- **Invariant:** historical statements remain historical; P8-S5/P8-S6,
  Phase 8, broader programmes, and project remain incomplete. None of the seven
  documentation owners enters the 9-path mandatory implementation/test budget
  or the 10-path conditional maximum.
- **Failure:** unknown publication identity, stale baseline, or path maximum
  stops synchronization.
- **Evidence:** canonical documentation checklist, exact path inventory, hashes,
  diff checks, and independent review appropriate to each candidate.
- **Reuse:** never edit the frozen P8-S3 plan or the P8-S4 plan bytes bound to
  the exact section A plan-review verdict as status documents.

## I. Error and recovery behavior

### Expected public/domain rejection

- Malformed headers or strict bodies continue through existing framework and
  adapter validation. The fixed public 422 envelope remains unchanged and no
  service call occurs.
- Missing/foreign/unavailable Player Character ownership remains 404
  `PLAYER_CHARACTER_NOT_FOUND` without enumeration.
- A stale requested character revision remains 409
  `PLAYER_CHARACTER_STALE`.
- Retired, deceased, bound, exhausted, or otherwise ineligible owned state
  remains 409 `PLAYER_CHARACTER_NOT_ELIGIBLE`.
- Same controller-scoped operation key with incompatible evidence remains 409
  `IDEMPOTENCY_CONFLICT`.
- A concurrency, CAS, active-binding, participation, or receipt conflict not
  explained by exact replay remains 409 `RUN_ENTRY_CONFLICT`.
- An unavailable/invalid scenario remains 422
  `INVALID_SCENARIO_DEFINITION` through existing catalogue authority.
- Existing Player Character create/read/retirement errors remain exactly those
  already implemented; P8-S4 adds no Demo-only public error.

For every rejection above, tests must identify its actual service call boundary.
If the decision completes before the first generator call, it has zero generator
delta and creates no staged or authoritative entity. If source ordering has
already emitted one or more values before a later rejection, those exact values
remain consumed, later uninvoked streams remain unchanged, and rollback removes
only staged persistence. A rejection must never be used as a generic reason to
restore generator positions.

### Integrity and impossible state

Malformed canonical records, mismatched current/revision families, invalid
receipt evidence, missing initialization evidence, contradictory participation,
or impossible service results are internal integrity failures. They are not
converted to not-found, stale, or conflict. Existing exception sanitization
returns the safe 500 `INTERNAL_ERROR` envelope without exception strings,
storage values, controller data, keys, receipts, or trace detail.

### Transaction, publication boundary, and cancellation

The Demo transaction validates and publishes one complete replacement store
state while holding its commit lock. Any failure or cancellation before the
final publication leaves the old store authoritative, discards staged values,
and releases locks, but does not rewind any generator value already emitted.
The final process-local publication sequence has no await and no external
database/network operation. Once that atomic publication completes, the
authoritative mutation remains committed; cancellation delivered later and any
later View/projection failure do not roll it back. Commit performs no generator
call and no second advance.

There is no generic retry, compensation, outbox, saga, or uncertain external-
database commit state in this process-local sequence. Preserve the existing
public uncertain-result and receipt-recovery contract for response loss,
cancellation, a sanitized response, or other caller-side uncertainty: an
explicit retry uses the exact same operation evidence and receipt path. That is
uncertainty about the result observed by the caller, not uncertainty about
whether the non-awaiting process-local publication crossed its boundary. Do not
guess, issue replacement identities, or reuse consumed values.

### Receipt recovery and process lifetime

Within one process, exact character-creation and Run-entry replay returns the
stored successful result before invoking any generator, without state mutation
or new clock, identity, Session, seed, event, job, lease, or worker consumption.
Incompatible evidence is rejected before issuance when the existing service
decision ordering reaches it there. Across a process restart, the store and all
receipts are intentionally absent and every deterministic stream starts at its
fresh-process origin. Restart is the only generator reset boundary; it does not
permit same-process value reuse after rollback, conflict, exception, or
cancellation, and it does not claim durable idempotency recovery.

### View failure after mutation

Run-entry success is authoritative before the client performs its mandated View
read. If View fails, the Run, binding, Session, participation, activation, and
receipts remain committed. Retry the existing View endpoint with the returned
Session ID. Do not repeat admission under a new key, undo Run entry, or add a
Demo-specific recovery route.

### Framework behavior

The P8-S3 raw request validation, exact header grammar, strict JSON schema,
response projection, OpenAPI, and exception mapping remain the only public
boundary. FastAPI-generated detail bodies, Python validation structures, and
repository exceptions must never escape.

## J. Test plan

### Required generator checkpoint allocation

The generator-specific evidence is allocated to four owners within the six
mandatory test/support paths; no new test/support path is permitted:

- `tests/unit/test_demo_persistence.py` must prove that rollback discards every
  staged persistence family while an already-emitted external generator value
  remains consumed and a not-yet-invoked stream remains unconsumed.
- `tests/unit/test_demo_composition.py` must checkpoint every complete
  `DemoGenerators` field and prove: rejection completed before issuance consumes
  no value; exact receipt replay consumes no value; successful commit consumes
  each actually requested value exactly once and commit itself consumes none;
  failure after Player Character, Run, line, or Session identity issuance leaves
  each emitted identity consumed; failure after clock, seed, or event issuance
  leaves each emitted value consumed; cancellation after issuance leaves every
  emitted value consumed; failure before a later stream is invoked does not
  advance that later stream; and independent Player Character, Run, line, and
  Session identity streams do not shift one another. The same rule applies to
  existing job, lease, and worker streams at call sites that actually request
  them.
- `tests/e2e/support/demo_replay_child.py` must continue to reconstruct and
  trace every generator field explicitly, including the three new identity
  fields; it may not infer consumption from expected persistence.
- `tests/e2e/test_demo_cross_process_replay.py` must prove that a fresh process
  restores the canonical initial store and generator sequence and that two
  fresh processes still produce identical canonical public output and complete
  generator traces.

These checkpoints distinguish pre-issuance rejection, post-issuance failure,
partial issuance, rollback, cancellation, successful publication, exact replay,
and restart. They must never assert or implement same-process generator rewind.

### Unit — Demo persistence

All cases belong in `tests/unit/test_demo_persistence.py` and reuse current
store/UoW fixtures where possible.

1. `test_player_character_repository_round_trips_complete_detached_family`
   stages binding/allocation/revision/current/receipt, commits, mutates returned
   copies, and reloads unchanged authority. It proves complete detached
   reconstruction; current Session tests do not cover these families.
2. `test_player_character_listing_is_owned_active_unbound_stable_and_bounded`
   seeds owned/foreign/retired/bound candidates, lists with a limit, and expects
   only stable ordered eligible projections. It proves P8-S1 port parity.
3. `test_player_character_lock_cas_and_receipt_conflicts_publish_no_partial_state`
   races two UoWs and injects duplicate/CAS cases. Exactly one current revision
   and receipt may publish; existing tests cover only Session optimistic locks.
4. `test_run_repository_round_trips_revisions_binding_receipts_and_participation`
   stages canonical revisions 1/2/3 plus creation evidence and participation,
   then reloads fresh values. It proves the P8-S2 storage family.
5. `test_run_active_binding_participation_and_receipt_uniqueness_are_atomic`
   races competing entries. Exactly one complete Run family publishes and the
   loser gets the expected conflict class.
6. `test_run_entry_replay_lock_reads_return_complete_current_evidence`
   exercises Run, owned Session, initialization event, and latest snapshot
   locking reads. It proves the base unlocked/unimplemented fallbacks are not
   used.
7. `test_expanded_uow_rolls_back_every_new_and_existing_family_together`
   injects a late conflict/failure after all families stage. Authoritative
   Player Character, Run, Session, snapshot, event, participation, and receipt
   counts remain unchanged, while every generator value emitted before that
   failure remains consumed and every later uninvoked stream remains unchanged.
8. `test_expanded_snapshot_is_complete_and_detached`
   checks the exact dataclass field manifest and deep independence for all old
   and new maps.
9. Integrity probes corrupt one relationship at a time and expect the relevant
   stored-record integrity error, never a normal miss.
10. Existing Demo persistence tests remain green, proving no regression to
    narrative/action transactions.

### Unit/API/OpenAPI/composition — Demo runtime

All cases belong in `tests/unit/test_demo_composition.py`.

1. Replace `test_demo_composition_does_not_register_player_character_routes`
   with an exact service and route inventory: `GET
   /v1/player-characters/eligible-for-run-entry`, `POST
   /v1/player-characters`, `GET
   /v1/player-characters/{player_character_id}`, `POST
   /v1/player-characters/{player_character_id}/retirement`, and `POST
   /v1/runs`. Assert matching runtime OpenAPI and no extra Demo-only operation.
2. Extend `test_generator_families_are_exact_and_independent` with all new
   fields, exact first values, type grammar, and proof that consuming one family
   does not advance another or make its value transactionally rewindable.
3. Add `test_demo_services_share_store_clock_catalog_session_and_fixed_authority`
   and assert instance identity at the relevant seams. This detects accidental
   duplicate UoWs/services or environment resolution.
4. Add a full ASGI create/discover/enter/View test. Setup uses the existing
   minimal valid structured character body, fixed Demo principal, canonical
   scenario, and explicit idempotency keys. Expected authority is character
   revision 1, Run revisions 1/2/3, `active` current Run, exact binding, one
   Session and participation, and one initialization snapshot/event. Expected
   public result is the existing stable DTO and View.
5. Add exact create and entry replay assertions. Snapshot and generator
   checkpoints before/after replay are identical, including clock, every
   identity, Session, seed, event, job, lease, and worker stream.
6. Add incompatible key, stale revision, already-bound new-key, and
   foreign/missing probes with exact public codes and no leaked existing Run.
7. Inject a late UoW conflict and an integrity failure; assert sanitized public
   output and no partial state. Check the generator positions at each injected
   boundary so already-emitted values remain consumed and later streams do not
   advance.
8. Force the first View read to fail after successful admission, then retry View
   and assert the same committed Session/Run state.
9. Extend no-engine/no-external-provider and dedicated-entrypoint tests so new
   service construction cannot call production builders, environment loaders,
   MySQL, UUID/wall-clock issuers, or an external Provider.
10. Preserve representative existing action behavior after Run entry.
11. Add pre-issuance validation/ownership/receipt-mismatch probes and assert zero
    generator deltas; exact replay remains a separate zero-delta case.
12. Add success, exception, conflict, and cancellation probes after each
    applicable identity and clock/seed/event issuance boundary; assert exactly
    one advance for every emitted value, no commit-time advance, no rewind, and
    no advance for a later stream not yet invoked.

No new generic API test file is needed: P8-S3 already exhaustively tests the
adapter/DTO/OpenAPI boundary, and P8-S4 changes no API code. The Demo composition
test proves that exact adapter is registered and reachable in this composition.

### Mandatory existing composition-owner maintenance

Both files are direct pytest owners and mandatory even though P8-S4 adds no new
route or schema:

1. In `tests/unit/test_run_composition.py`, replace only
   `test_demo_composition_remains_independent_of_run_entry` with the P8-S4 Demo
   Run-entry composition expectation. Preserve unrelated normal-composition
   construction, laziness, route, Provider, and service-identity evidence.
2. In `tests/unit/test_player_character_api.py`, replace only
   `test_demo_composition_gets_no_player_character_route_or_schema` with the
   P8-S4 Demo service-conditional route/schema expectation. Preserve all
   unrelated Player Character adapter, DTO, OpenAPI, ownership, and normal-
   composition evidence.

These are narrow expectation updates for existing surfaces, not P8-S5 Web work
or P8-S6 cross-surface closure.

### Cross-process E2E

Both exact paths are mandatory:
`tests/e2e/test_demo_cross_process_replay.py` is the direct pytest owner, and
`tests/e2e/support/demo_replay_child.py` is mandatory executable support
evidence launched by that owner. The helper counts toward the mandatory
test/support budget but need not be collected independently by pytest unless
repository structure requires it.

1. Child setup performs public scenario discovery, character creation,
   eligible discovery, Run entry, and first View before the existing canonical
   19 actions.
2. Transcript expectations include exact replay for creation and entry and one
   incompatible/conflict probe without disturbing the successful journey.
3. Trace protocol enumerates every old and new generator category. Expected
   counts/values prove replay consumes none and independent families stay exact.
4. Child field manifests include every `DemoGenerators` and
   `DemoStoreSnapshot` field. The complete private representation includes all
   character/Run revisions and currents, allocations, bindings, receipts,
   evidence, participation, and existing gameplay families.
5. Two fresh child processes under distinct hash seeds produce identical public
   and generator traces and equivalent complete private authority.
6. A further fresh process proves prior IDs/receipts/state are absent and
   deterministic sequences restart.
7. Socket guards continue to reject non-loopback I/O. External Provider call
   count remains zero.
8. Existing pipe failure, hang, diagnostic, partial-write, and schema-complete
   reconstruction cases remain green.
9. The canonical 19-action sequence and terminal Session projection remain
   unchanged; the final Run remains active and bound.
10. Frozen transcript/trace/private digests are recalculated only after all
    semantic assertions pass and are reviewed as an intentional topology
    change, never blindly accepted.

### Integration and real MySQL

No new integration or real-MySQL test path is part of P8-S4. This is not a mock
substitution: P8-S4 deliberately changes only process-local Demo adapters, while
P8-S2/P8-S3 already hold real-MySQL transaction/public evidence. The parent
verification matrix requires no MySQL command for P8-S4. A finding that Demo
parity depends on a MySQL/ORM change stops the slice rather than activating an
unplanned probe.

### Verification-script coverage

The canonical Offline verification script is the required broader tier after
focused tests and compilation. `test_demo_scripts.py` changes only under the
exact section G.6 predicate. P8-S4 does not run or alter Full, E2E-as-a-broad-
tier, MySQL, launcher, or smoke scripts merely for ceremony.

## K. Verification strategy

Relevant local verification may not be deferred to CI.

### 1. Focused during implementation

Run after each layer stabilizes:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_demo_persistence.py
.\.venv\Scripts\python.exe -m pytest tests/unit/test_demo_composition.py
.\.venv\Scripts\python.exe -m pytest tests/unit/test_run_composition.py
.\.venv\Scripts\python.exe -m pytest tests/unit/test_player_character_api.py
.\.venv\Scripts\python.exe -m pytest tests/e2e/test_demo_cross_process_replay.py
```

Add the conditional owner only if the later implementation preflight proves
that its launcher or smoke assertions enumerate the exact affected route
inventory:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_demo_scripts.py
```

Then run the five mandatory direct pytest owners together, plus
`tests/unit/test_demo_scripts.py` as a sixth direct owner only if that exact
predicate activates, to detect shared fixture/order effects. The mandatory
support helper `tests/e2e/support/demo_replay_child.py` is exercised by the
cross-process pytest owner and need not be invoked as an independent pytest
target unless repository structure requires it. Record actual selected, passed,
skipped, and failed counts; never predict counts in advance.

### 2. Relevant integration/MySQL evidence

The required local integration evidence is the real two-process Demo harness,
not MySQL. Run it with the project venv as above and retain its no-network,
restart-loss, trace, and private-state assertions. Do not replace it with mocks
or an in-process-only test. No MySQL probe is required or authorized for this
slice under the published matrix.

### 3. API/OpenAPI/composition checks

The focused Demo composition selection must assert:

- exact registered methods/paths;
- exact existing runtime OpenAPI operations and absence of internal schemas;
- fixed Demo principal/controller ownership;
- one shared service/store/clock/catalogue composition;
- existing public request/response/error projections;
- no normal builder, SQL engine, external Provider, or environment fallback.

### 4. Broader repository tier

After focused tests pass:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
.\scripts\verify.ps1 -Mode Offline
```

Offline is the authoritative broader tier for P8-S4. Do not substitute Full or
MySQL, and do not call a real Provider. If Offline mode is unavailable, stop and
report it instead of running another tier.

### 5. Final scope and artifact checks

Run non-mutating checks for:

- `git diff --check`;
- exact changed-path inventory against 3 production + 6 mandatory test/support
  paths for 9 mandatory implementation/test paths, plus only the separately
  evaluated conditional test/support path for a maximum of 10;
- exact confirmation that the seven later documentation-sync owners remain
  separate from both implementation/test totals and unchanged until the
  independently approved implementation is committed and user-published;
- empty index unless a later explicitly authorized staging workflow is active;
- final generated-content and artifact inventory proving no untracked generated,
  cache, or coverage artifact;
- no migration, ORM, dependency, config, scenario, normal-composition, or
  frozen-plan diff;
- P8-S3 frozen plan identity;
- plan/candidate hashes and exact plan-review/implementation-review verdict
  consistency;
- generator counters absent from store/UoW rollback/publication state and the
  complete pre-issuance, post-issuance, partial-issuance, cancellation, commit,
  replay, and restart checkpoints in section J;
- complete documentation checklist; and
- P8-S5/P8-S6 still unstarted.

### Environment limitation reporting

If the exact required command is blocked specifically by the sandbox, verify
its command and target and immediately request permission to rerun that exact
operation. If escalation is denied/unavailable, or the project `.venv` is
missing/broken, stop and report the unrun command and missing evidence. Never
recreate the venv, install globally, silently reduce the selection, treat CI as
a substitute, or replace the cross-process/Offline evidence with mocks.

## L. Documentation synchronization

The following publication-status changes occur only after the P8-S4
implementation candidate receives exactly
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`,
then receives separate commit authorization, is committed, and is
user-published. That verdict alone does not authorize documentation
synchronization. Before publication, all seven owners remain unchanged; the
implementation candidate's exact verification and review state is reported
without anticipating a commit or publication identity.

1. `PLANS.md`
   Current stale-after-publication meaning: P8-S4 is unstarted and only P8-S1
   through P8-S3 are complete. Record the actual P8-S4 implementation/publication
   identity, Demo parity capability, exact evidence, and next P8-S5 priority.
   Preserve P4-S1's historical `pre_first_turn` limit, P8-S2 ownership of
   revision-3 activation, P8-S3 normal adapter ownership, and broader Phase 4/
   project incompleteness.

2. `docs/architecture.md`
   Current stale-after-publication meaning at lines 562-579: Demo has no entry
   service or `/v1/runs`. Replace only that current-state description with the
   implemented process-local repositories, deterministic composition, and
   route parity. Preserve the historical P8-S3 statement, one transaction owner,
   no migration/Provider/normal-composition change, and deferred Web/full Run
   architecture.

3. `docs/public_client_contract.md`
   Current stale-after-publication meaning at lines 947-949: Demo parity remains
   deferred. State that Demo now reaches the same existing create/discovery/
   entry DTO, error, replay, privacy, and OpenAPI contract. Do not add a
   Demo-specific public shape, Web implementation claim, or new recovery rule.

4. `docs/run_protocol.md`
   Current status wording must record that the existing P8-S2 amendment is now
   reachable in deterministic Demo, without suggesting P8-S4 created revisions
   1/2/3 or activation. Preserve the historical P4-S1 baseline, unchanged
   Session-backed amendment, active Run after Session ending, no migration, and
   incomplete full Phase 3.3.

5. `docs/structured_player_character_contract.md`
   Current stale-after-publication meaning at lines 1103-1106 says P8-S4 has not
   started and Demo parity remains P8-S4. Record exact P8-S4 completion evidence
   only. Preserve the frozen contract, existing lifecycle/reference rules,
   P8-S5/P8-S6 allocations, and incomplete Phase 6/7/programme/project status.

6. `docs/structured_player_character_implementation_plan.md`
   Current stale-after-publication meaning at lines 3806-3810 and 3897-3910 says
   P8-S4 is unstarted. Record its actual implementation/publication and narrow
   Demo ownership. Preserve completed earlier phases, historical Demo phase
   closure, and all unimplemented P8-S5/P8-S6 and broader programme work.

7. `docs/structured_player_character_run_playable_loop_plan.md`
   Current stale-after-publication meaning at line 805 and section 20.5 says
   P8-S4 has not started and describes future evidence. Record actual paths,
   checks, review verdict, commit/publication identity, and residual boundaries.
   Preserve the approved slice definition, P8-S2/P8-S3 chronology, P8-S5 Web
   allocation, P8-S6 closure allocation, and Phase 8/project incompleteness.

All seven documents must be inspected and, because each presently owns an
unstarted/deferred P8-S4 fact, synchronized after publication. The unique
post-publication path total is seven. It is never folded into the 9-path
mandatory implementation/test total or the 10-path conditional maximum. This
plan correction authorizes none of those later edits, and no eighth
documentation path is needed solely because of the corrected budget. The
frozen P8-S3 plan and this eventually frozen P8-S4 plan are historical
candidates and are not status-sync targets.

## M. Stop conditions

The later implementer must stop without improvising if any of these occurs:

1. `HEAD`, local `main`, `origin/main`, branch, parent, subject, ahead/behind,
   clean index/worktree, or preservation state differs from the separately
   authorized implementation baseline.
2. This plan has not received the exact verdict
   `STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_PLAN_INDEPENDENT_REVIEW_APPROVED`
   for the exact bytes and reviewer-reported SHA-256 being used; that verdict is
   stale after any byte change; the reviewed identity differs; the approved plan
   has not been user-published and confirmed as a clean aligned baseline; or the
   P8-S3 frozen plan differs from 1,165 lines / 67,566 bytes / the SHA-256 in
   section B.
3. The exact mandatory production inventory of three, mandatory test/support
   inventory of six, 9-path mandatory implementation/test total, sole
   conditional test/support path and 10-path conditional maximum, or separate
   exact post-publication documentation inventory of seven cannot contain the
   required work.
4. Any authority materially contradicts deterministic process-local Demo
   parity, exact port reuse, P8-S2 transaction ownership, or P8-S5/P8-S6
   separation.
5. An ORM, Alembic migration, MySQL schema, configuration, dependency,
   generated artifact, scenario, external Provider, or normal-composition
   change appears necessary.
6. Existing public request/response/error/OpenAPI/privacy behavior cannot be
   preserved without editing an API adapter, DTO, dependency, or contract path.
7. Evidence shows the proposed work is Web connection/recovery (P8-S5) or final
   cross-surface evidence/status closure (P8-S6).
8. A required new source, test, fixture, support, launcher, or generated file is
   outside section G, or `tests/unit/test_demo_scripts.py` would be edited
   without the later implementation preflight proving that its launcher or
   smoke assertions enumerate the exact affected route inventory.
9. Demo port parity would require changing application/domain ports or moving
   transaction/commit/replay decisions out of existing services.
10. Complete detached reconstruction, receipt evidence, genuine locking reads,
     atomic publication, rollback, or uniqueness cannot be achieved in the
     authorized persistence path.
11. Generator values would need to participate in UoW rollback/publication,
    rewind after emission, or be reused in the same process; the cross-process
    child cannot enumerate every expanded generator/store field; or
    deterministic/no-network/restart-loss evidence cannot run locally.
12. The project `.venv` is absent/broken, Offline verification is unavailable,
    or a required local command remains blocked after the prescribed escalation
    path.
13. A hook, formatter, verification script, test, or generator mutates unrelated
    content, creates an unapproved artifact, or changes frozen bytes. Do not
    clean, restore, stage, or absorb that mutation; report exact state.
14. Post-publication documentation truthfulness would require more than the
    exact seven owners, documentation synchronization would need to precede the
    separately reviewed implementation commit and user publication, or any
    review prompt cannot return the exact applicable plan-review or
    implementation-review verdict required by sections A and N for the exact
    candidate it inspects.
15. A real external Provider or credential would be needed or contacted.

## N. Completion criteria

### Implementation candidate complete

This state requires all of the following and proves only a candidate:

- exactly the mandatory three production and six test/support paths changed,
  for 9 mandatory implementation/test paths, plus only the sole conditional
  test/support path if its exact objective predicate activated, for a maximum
  of 10;
- every new repository/UoW port and service composition behavior in sections
  F-H is implemented without API/application/domain redesign;
- focused persistence, composition, and cross-process tests pass;
- compilation and canonical Offline verification pass locally;
- exact route/OpenAPI, state/revision/binding/participation, replay/conflict/
  rollback, detached reconstruction, pre-/post-/partial-issuance generator
  behavior, cancellation, commit-without-second-advance, same-process non-reuse,
  two-process determinism, restart loss/reset, canonical action, and no-
  external-I/O evidence is recorded;
- no migration/config/dependency/generated/normal-composition path changes;
- the exact seven documentation owners remain outside the implementation/test
  candidate and reserved for separate synchronization only after the approved
  implementation is committed and user-published; and
- exact diff, path totals, bytes/hashes, Git preservation, and residual limits
  are reported while P8-S5/P8-S6 remain unstarted.

### Implementation independently approved

This is a later state distinct from plan review. Only after the implementation
candidate satisfies the frozen plan and all required evidence may a separate
read-only reviewer inspect its exact complete state and reviewed diff and return
the sole future implementation-review success verdict:

`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

That verdict binds only the exact implementation candidate state and reviewed
diff. Any byte or diff change invalidates it and requires new identities and a
fresh review. The verdict alone authorizes no commit, push, publication,
documentation synchronization, P8-S5, or P8-S6, and it cannot be substituted by
the current plan-review verdict or a generic approval phrase.

### Implementation committed

This requires separate user authorization for the exact reviewed candidate,
intentional staging of only reviewed paths, successful hooks, and verification
that the commit tree contains the reviewed bytes. The exact implementation-
review verdict alone is not commit authority.

### Pushed/published

The user performs every push manually. Publication requires the user-confirmed
remote update and aligned clean baseline. A local commit does not prove a push,
and this repository must never be pushed by Codex.

### Post-publication status synchronized

Only after publication may the separate exact-seven documentation candidate in
section L record the actual published identity and P8-S4 completion. It needs
its own exact hashes, read-only review, separate commit authorization, local
documentation commit, user push, and aligned-baseline confirmation. Until that
sequence completes, publication status synchronization is incomplete. P8-S5 and
P8-S6 remain unstarted throughout.

## O. Exact next action

Return control to the user. Preserve this one-file corrected P8-S4
implementation-plan candidate unchanged, untracked, unstaged, and uncommitted.
Submit its exact new bytes and SHA-256 to a fresh independent read-only plan
review in a new session, whose only success verdict is exactly
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_PLAN_INDEPENDENT_REVIEW_APPROVED`.
Do not commit the plan, implement P8-S4, or begin P8-S5 or P8-S6 now. If that
independent approval is bound to the exact reviewed candidate SHA-256, the
remaining chronology is:

1. perform one separately authorized candidate-plan commit-only task;
2. return control to the user for manual `git push`;
3. do not conduct another substantive plan review after commit or publication;
4. do not schedule or require a standalone post-publication baseline-
   confirmation task;
5. later, separately authorize the P8-S4 implementation task;
6. inside Step 0 of that authorized implementation task, confirm the published
   plan commit, aligned refs, clean index, and expected worktree state;
7. stop before implementation if that opening preflight fails;
8. if it passes, continue directly into P8-S4 implementation in that same task
   without returning control;
9. independently review the resulting implementation candidate before any
   implementation commit or publication; and
10. do not begin P8-S5 or P8-S6.

The Step 0 preflight is a safety check inside the authorized implementation
task. It is not a standalone task, a gate before implementation authorization,
or another review or approval of the plan.

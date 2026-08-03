# Structured Player Character P8-S3 Normal API and Composition Activation Implementation Plan

## 1. Title, status, and exact review gate

Status: **Review-ready implementation-plan candidate for P8-S3 — Normal API
and composition activation. This candidate has not been independently
reviewed, approved, implemented, staged, committed, or published.**

This document is the standalone implementation procedure for only:

> **P8-S3 — Normal API and composition activation**

Its creation does not authorize implementation. It creates no route, runtime
capability, test evidence, database effect, Demo behavior, Web behavior,
commit, or publication.

The sole operative successful verdict for an independent read-only review of
the exact complete eight-document candidate is:

```text
STRUCTURED_PLAYER_CHARACTER_P8_S3_PLAN_REVIEW_APPROVED
```

The eight-document candidate is this new plan plus the seven minimally
synchronized status owners named in section 10. Generic `APPROVED`, the
candidate-preparation verdict
`STRUCTURED_PLAYER_CHARACTER_P8_S3_PLAN_CANDIDATE_COMPLETE`, P8-G0/P8-S1/P8-S2
verdicts, implementation-review verdicts, failure verdicts, and differently
named tokens are non-operative. Review approval binds the exact complete
candidate bytes and the SHA-256 identities recorded after authoring. Any byte
change to any of the eight documents invalidates that inventory and requires a
fresh independent read-only plan review.

The only permitted next step after this candidate is frozen is that separate
independent read-only P8-S3 plan review. Plan creation and plan review must not
be combined.

## 2. Repository baseline and controlling authority

### 2.1 Authoring baseline

This candidate was authored from the following verified local baseline without
fetching or contacting a remote:

| Fact | Verified value |
| --- | --- |
| Repository | `D:\deviation-protocol` |
| Branch | `main` |
| `HEAD` | `70815b181624e5475d2d978bef0db1ed3b22324e` |
| Local `main` | `70815b181624e5475d2d978bef0db1ed3b22324e` |
| Local `origin/main` tracking ref | `70815b181624e5475d2d978bef0db1ed3b22324e` |
| Ahead/behind | `0/0` |
| `HEAD` subject | `feat(player-character): add durable run-entry initialization` |
| Initial worktree | Clean; no modified, deleted, untracked, or unmerged path |
| Initial index | Empty |
| Active Git operation | None |
| Remote activity | None |

A relevant baseline change while this plan is pending invokes the
[pending-plan baseline-invalidation rule](engineering/codex_workflow.md#pending-plan-baseline-invalidation).
If any recorded fact becomes stale, the candidate, hashes, approval condition,
path inventory, and safest next step must be reassessed. A stale candidate hash
or approval is never preserved for convenience.

### 2.2 Authority and precedence

Narrower authority controls its own subject. The implementation task must read
the then-current versions of these authorities before changing code:

1. repository constraints in `AGENTS.md`;
2. [Codex Workflow](engineering/codex_workflow.md) and
   [Engineering Guardrails](engineering/guardrails.md), especially `DB-001`,
   `AUTH-001`, `API-001`, and `PLAY-001`;
3. [`PLANS.md`](../PLANS.md) for roadmap and current status;
4. the approved and published
   [Phase 8 playable-loop plan](structured_player_character_run_playable_loop_plan.md)
   for slice order, public outcome, path ceilings, deferrals, and evidence;
5. the frozen historical
   [P8-S2 atomic Run-entry plan](structured_player_character_p8_s2_implementation_plan.md)
   plus the committed P8-S2 source for the internal command/result/decision,
   transaction, replay, persistence, lock, and cancellation behavior;
6. the [Public Client Contract](public_client_contract.md) for the exact wire,
   privacy, error, OpenAPI, and recovery contract;
7. the [Run Protocol](run_protocol.md) for the narrow Session-backed admission
   amendment and the continued exclusion of full Phase 3.3 behavior;
8. the [Structured Player Character Contract](structured_player_character_contract.md)
   and [downstream implementation plan](structured_player_character_implementation_plan.md)
   for character identity, ownership, applicable revision, active-binding,
   projection, and Phase 6/7 boundaries; and
9. [Architecture](architecture.md) and committed production/test source for
   current composition, UoW, Session, action, View, request-status, Provider,
   and Demo facts.

This plan translates those authorities into a bounded procedure. It does not
renegotiate a product behavior or replace the P8-S2 transaction authority. A
material contradiction is a stop condition, not permission to select a new
semantic locally.

## 3. Historical state and prerequisites

The following state is closed and must be treated as history:

- P8-G0 is complete and published at
  `de4d8c0e35c7864948306d751a00aaf295ff77ff`.
- P8-S1 eligible-character discovery is implemented, independently accepted,
  committed, and published at
  `95ffe4019e2a69967dfae1fee2a1ecba4a628381`.
- P8-S2 atomic internal Run entry is implemented, accepted, committed, and
  published at `70815b181624e5475d2d978bef0db1ed3b22324e`
  (`feat(player-character): add durable run-entry initialization`). Its
  implementation and F1/F2/F3 evidence are closed.
- P8-S2 is not reopened by this plan. Its plan, production source, tests,
  persistence protocol, decision precedence, and evidence receive no review,
  correction, expansion, or implementation change in P8-S3 planning.
- `RunEntryService.enter()` exists and is the sole P8-S2 entry coordinator.
- P8-S3 is the canonical next slice.
- P8-S4 Demo parity, P8-S5 Web connection, and P8-S6 cross-surface evidence and
  final status closure remain unimplemented.
- Phase 6 and Phase 7 remain separately allocated and unimplemented. Neither
  is a P8-S3 prerequisite.
- The current schema and migration head already represent P8-S3. No ORM or
  migration change is authorized.

The prerequisite for implementation is not merely the existence of this file.
The exact plan-and-status candidate must first pass the gate in section 21, be
separately committed and user-published unchanged, and be confirmed as a clean
aligned baseline. A later, separate explicit task must then authorize P8-S3
implementation.

## 4. Purpose and acceptance boundary

P8-S3 has one purpose: expose the already approved normal-application
`POST /v1/runs` operation and lazily compose the existing P8-S2
`RunEntryService` behind it.

The accepted implementation boundary is exactly:

```text
trusted RequestPrincipal
  + one required public Idempotency-Key
  + one strict three-field JSON body
  -> public transport validation
  -> exact RunEntryCommand construction
  -> RunEntryService.enter(...) once at most
  -> explicit allowlist RunEntryResponse or one fixed public error
```

P8-S3 succeeds only when the normal public path is reachable and proven while
all domain, ownership, eligibility, identifier issuance, replay, lock,
transaction, persistence, Session initialization, participation, and Run
activation behavior stays in P8-S2 and its reused services/repositories.

P8-S3 does not make Phase 8 complete. It activates neither Demo nor Web and
does not add a public Run read/list/recovery surface. Its local evidence
includes one focused real-MySQL public entry-to-terminal journey because
`PLAY-001` requires production public reachability evidence; final cross-
surface reruns and Phase 8 closure remain P8-S6 work.

## 5. Canonical public contract

### 5.1 Method, path, authentication, and media type

The only new operation is:

```http
POST /v1/runs
Idempotency-Key: <opaque key>
Content-Type: application/json
```

Authentication uses the existing trusted `get_current_principal` dependency
and forwards the resulting exact `RequestPrincipal` as the separate first
argument to `RunEntryService.enter()`. No request path, query, header, or body
field may supply or override player, principal, authentication scheme,
controller, ownership, or authority.

Transport requires exactly one raw `Content-Type` header and exactly one raw
`Idempotency-Key` header. The existing Player Character raw transport
convention is reused:

- header names remain case-insensitive under HTTP;
- each admitted raw value must be ASCII;
- the media type before the first `;`, after only HTTP whitespace trimming and
  ASCII case folding, must be exactly `application/json`;
- a missing, duplicate, malformed, non-ASCII, over-bound, or non-JSON header
  fails with the approved 422 envelope before the entry service is called;
- no alternate header, query, cookie, or body member supplies the key; and
- the key is preserved byte-for-byte/case-for-case after ASCII decoding. It is
  never stripped, normalized, case-folded, interpreted, or treated as
  authority.

The key uses `RunEntryPublicOperationKey`: the exact grammar
`^[A-Za-z0-9][A-Za-z0-9_.:-]*$`, ASCII, and 1 through 128 characters. The API
adapter may reuse the current raw transport validator and convert only its
already validated exact value into `RunEntryPublicOperationKey`; it must not
change the completed Player Character routes' transport behavior.

### 5.2 Exact request DTO

`RunEntryRequest` is a new public API DTO in `api/schemas.py`. It is strict,
frozen, revalidates instances, forbids extras, performs no string trimming or
case normalization, and contains exactly these required fields in this order:

| Field | Exact public type and bound | Internal construction |
| --- | --- | --- |
| `player_character_id` | JSON string; exact opaque grammar `^[A-Za-z0-9][A-Za-z0-9_.:-]*$`; 1..128 ASCII characters | `PlayerCharacterId(value=...)` |
| `expected_record_revision` | JSON integer, not boolean/float/string; 1..`9223372036854775807` | `PlayerCharacterRevision(value=...)` |
| `scenario_id` | JSON string; exact safe opaque grammar `^[A-Za-z0-9][A-Za-z0-9_.:-]*$`; 1..128 ASCII characters | `DefinitionId` validation through `RunEntryCommand` |

The request accepts no path parameter and no query input. It admits no
principal, controller, ownership, Run, line, Session, world, visit, lifecycle,
binding, applicable-reference object, contract version, character definition,
snapshot, state, receipt, operation namespace, internal operation ID, source,
seed, event, Provider, retry, replay, or recovery field. Unknown fields and
wrong JSON types fail with the fixed public 422 envelope before the service is
called.

The adapter constructs exactly one `RunEntryCommand`:

```text
RunEntryCommand(
    public_operation_key=RunEntryPublicOperationKey(value=<header>),
    player_character_id=PlayerCharacterId(value=<body.player_character_id>),
    expected_record_revision=PlayerCharacterRevision(
        value=<body.expected_record_revision>
    ),
    scenario_id=<body.scenario_id>,
)
```

No domain field is defaulted, inferred from prose, or copied from an untrusted
authority field.

### 5.3 Exact success and replay DTO

First committed success and exact replay both return HTTP 200 and the same
exact four-field top-level `RunEntryResponse`:

```json
{
  "run_id": "run.example",
  "session_id": "session-example",
  "scenario_id": "death_certificate",
  "player_character": {
    "player_character_id": {"value": "pc.example"},
    "contract_version": "structured-player-character/v1",
    "record_revision": {"value": 1},
    "lifecycle": "active"
  }
}
```

`RunEntryResponse` is strict, frozen, revalidates instances, forbids extras,
and contains:

- `run_id`: exact safe opaque string, 1..128 characters;
- `session_id`: exact safe opaque string, 1..64 characters;
- `scenario_id`: exact safe opaque string, 1..128 characters; and
- `player_character`: the existing detached four-field
  `PlayerCharacterSelfProjection`.

The route must first strictly revalidate an exact `RunEntryResult`, then build
a new `RunEntryResponse` field by field. It must build a new nested
`PlayerCharacterSelfProjection` field by field from the validated result. It
must not return the internal result directly, call `model_dump()` on an
internal model, use `exclude=...`, or serialize a domain/ORM object. A malformed,
impossible, or cross-bound success object fails closed through the sanitized
500 boundary and is never repaired into success.

The replay response remains stable after Session gameplay advances because it
contains no mutable Session or Run projection. Clients next read
`GET /v1/sessions/{session_id}/view`.

### 5.4 Exact OpenAPI operation

OpenAPI must contain exactly one `post` operation at `/v1/runs` with:

- tag `runs`;
- `operationId: enter_run`;
- summary `Enter a Run`;
- response description `Run entered or exactly replayed.` for 200;
- one required header parameter named exactly `Idempotency-Key`, with the
  string pattern and 1..128 bounds above;
- one required `application/json` request body whose schema is exactly
  `RunEntryRequest`;
- the 200 schema exactly `RunEntryResponse`;
- exactly the response status set `200`, `404`, `409`, `422`, and `500`;
- `ErrorResponse` for every error status, including 422; and
- no FastAPI `HTTPValidationError` as the public 422 schema.

`RunEntryRequest` must expose exactly three required properties and
`additionalProperties: false`. `RunEntryResponse` must expose exactly four
required properties and `additionalProperties: false`. All local `$ref` values
must resolve. No `RunEntryCommand`, `RunEntryResult`, `RunEntryDecision`,
`CanonicalRun`, applicable-reference, receipt, fingerprint, evidence,
controller, persistence, Session snapshot, Provider, or other internal model
may appear as an OpenAPI component or field.

The operation description must state, without expanding semantics, that the
trusted server derives controller authority; the key is required but is not
authority; first success and exact replay share HTTP 200; the server rechecks
ownership/eligibility and issues Run/line/Session identities; the response is a
stable entry projection rather than a current View; clients read the returned
Session View next; and Demo, production authentication, and Internet
deployment are not activated by P8-S3.

## 6. Reuse and ownership boundaries

P8-S3 must reuse, unchanged:

- P8-S1 eligible-character discovery as advisory discovery only;
- `RunEntryService.enter()` as the sole P8-S2 coordinator;
- `RunEntryCommand`, `RunEntryResult`, `RunEntryDecision`,
  `RunEntryDecisionCode`, `RunEntryPublicOperationKey`, and all existing typed
  identifiers, snapshots, and projections;
- the trusted `RequestPrincipal` dependency;
- current server-side `ConfiguredControllerBindingResolver` behavior and
  `PlayerCharacterService.lock_owned_for_binding()` evidence through the
  existing composition graph;
- the one normal `SqlAlchemyUnitOfWork` factory and its shared Session, Player
  Character, Run, participation, and receipt repository graph;
- the already built normal `SessionService`, including its catalogues,
  `DeterministicStoryDirector`, memory-rule engine, Session/event/seed issuers,
  and clock;
- the existing `RunService` production Run/line issuers, trusted Run source,
  clock, controller resolver, and Player Character evidence dependency;
- current strict DTO, raw-header, validation, fixed-error, cancellation, and
  OpenAPI conventions;
- the existing Session View, action submission, 202 response, request-status,
  refresh, and settlement lifecycle; and
- the existing scripted no-network Provider seam for tests only.

The following are prohibited:

- a second eligibility implementation;
- duplicate Run-entry orchestration in the route or composition root;
- direct API calls to a repository, UoW, issuer, Run staging helper, Session
  staging helper, or persistence codec;
- client-authoritative ownership, controller, binding, lifecycle, replay, or
  identity fields;
- a route-owned or composition-owned transaction;
- calling `RunService.create_run()`, `bind_player_character_internal()`,
  `attach_session()`, or `SessionService.create()` to reconstruct the composite
  workflow; and
- changing P8-S1 or P8-S2 code to make the adapter easier to write.

## 7. Transaction and idempotency invariants

The API route owns no UoW and no commit. Normal composition owns no UoW,
transaction, SQL, commit, identity issuance, or mutation. For one HTTP request:

1. framework dependencies and public DTO validation complete;
2. the raw header/media-type boundary validates;
3. the adapter constructs one exact `RunEntryCommand`;
4. the adapter calls `RunEntryService.enter(principal, command=command)` zero
   times on any earlier failure and otherwise exactly once;
5. the adapter maps the one returned result/decision; and
6. it performs no persistence or post-result mutation.

There is no API-level retry, receipt lookup, replay loop, second service call,
identity retry, exception recovery, commit retry, compensation, or
post-result persistence. The route must not attempt to resolve an uncertain
commit. An explicit later request with the exact same controller/key/body is a
new public request and follows the existing P8-S2 ownership-first algorithm.

The public key remains scoped by server-resolved controller inside P8-S2. The
adapter neither derives internal IDs nor inspects a receipt. Exact replay,
same-key conflict, stale revision, eligibility, scenario validation, and fresh
write concurrency retain the exact ordering already implemented in
`RunEntryService.enter()`:

```text
principal validation and controller resolution
  -> one UoW
  -> target Player Character ownership lock/proof
  -> creation receipt evaluation
  -> replay controller/equivalence/integrity checks
  -> fresh stale revision
  -> fresh lifecycle/successor/active-binding eligibility
  -> fresh scenario/default validation
  -> staged-write conflict classification
```

The route must not pre-check a current character, eligible collection, receipt,
scenario, or active binding in a way that changes this precedence.

Cancellation must propagate. No ORM model, migration, repository, UoW, domain,
application-service, receipt, or persistence-codec change is permitted.

## 8. Exact production path budget

P8-S3 production work is capped at these four existing paths. Three are
expected implementation owners; `api/errors.py` is an admitted but currently
unnecessary contingency, not a requirement to edit it.

| Path | Why it may need change | Exact assigned responsibility | Must not own | Inclusion evidence |
| --- | --- | --- | --- | --- |
| `src/deviation_protocol/api/schemas.py` | The public request and response DTOs do not exist | Add only strict `RunEntryRequest` and explicit `RunEntryResponse`, with the exact bounds and allowlists in section 5 | Internal command/result/decision models, eligibility, ownership, replay, persistence, transaction, or domain policy | Existing public DTOs live here; `API-001` requires explicit allowlists and OpenAPI uses these same DTOs |
| `src/deviation_protocol/api/errors.py` | It is the central safe-envelope owner if a narrow fixed Run-entry error helper proves necessary | Prefer no change. If changed, add only fixed status/code/message response construction or a narrow handler that preserves the section 12 mapping | Decision precedence, broad Run-entry exception translation, cancellation handling, logging of values, route-specific orchestration, or changed unrelated-route behavior | Existing `error_response`, 404/validation/scenario/idempotency handlers, and sanitized 500 already appear sufficient; inspection and focused tests decide whether bytes remain unchanged |
| `src/deviation_protocol/api/dependencies.py` | `ApiServices` has no entry-service slot/getter | Add optional `run_entry_service: RunEntryService | None = None` and `get_run_entry_service()` that returns it or raises fixed fail-closed `RuntimeError` | Construction, UoW entry, fallback service, Demo substitution, transaction, or public error policy | Existing optional Player Character/Run service slots and fail-closed Player Character getter establish the normal pattern |
| `src/deviation_protocol/api/main.py` | The route and normal entry-service composition do not exist | Add exact transport adaptation, command/result/decision mapping, lazy builder/composition, conditional route registration, and exact route metadata | Domain/repository orchestration, UoW/commit, retry/recovery, second eligibility, direct internal-model serialization, Demo composition, or changes to completed routes | Current normal builders, shared UoW factory, conditional Player Character registration, raw header validator, public error helpers, and ASGI routes supply every required seam |

No permitted path must change merely because it is listed. In particular,
`api/errors.py` remains byte-unchanged if the current fixed helpers and global
handlers satisfy every P8-S3 case. A required fifth production path is a stop
condition.

## 9. Exact test path budget

P8-S3 tests are capped at these five paths:

| Path | Why it may need change | Exact assigned evidence | Must not own | Inclusion evidence |
| --- | --- | --- | --- | --- |
| new `tests/unit/test_run_entry_api.py` | No focused public Run-entry adapter suite exists | Raw transport/header/media type, strict body, command/principal forwarding, exactly-one call, response allowlist, all decisions/precedence, privacy, failure sanitization, cancellation, dependency and route metadata | P8-S2 service algorithm re-testing through fake repositories, MySQL persistence, Demo, or Web | Existing Player Character API tests demonstrate the raw-ASGI, spy-service, exception-identity, projection, and route patterns |
| `tests/unit/test_run_composition.py` | Current inventory and object-graph assertions stop before P8-S3 | One lazy entry-service instance, identity reuse with `RunService`, shared Session/UoW/resolver/evidence graph, zero composition-time UoW/ID work, fail-closed absence, and Demo independence | Entry transaction behavior, Demo implementation, or external Provider work | This file already owns normal Run composition and exact public route inventory |
| `tests/unit/test_api.py` | Cross-route application behavior may need a narrow inventory/lifespan/error regression | Preserve import/lifespan laziness, dependency override behavior, existing route behavior, fixed envelope, and no accidental UoW/Provider work during entry | Detailed Run-entry matrix already owned by the new focused file | This is the existing general API and central error-regression owner |
| `tests/unit/test_phase_3_0_public_client_contract.py` | The public contract/OpenAPI inventory lacks `/v1/runs` | Exact operationId/tag/summary/description, required header, request/response schemas, exact statuses, `ErrorResponse`, resolved refs, and internal-component exclusions; preserve action 200/202 and request-status schemas | Service call ordering or database behavior | This file owns cross-operation public DTO/OpenAPI safety and component exclusions |
| new `tests/integration/test_mysql_run_entry_playthrough.py` | No public Run-entry MySQL adapter suite or joined entry-to-terminal proof exists | Focused public-route/real-service decision, replay, privacy, and no-write cases plus the exact production ASGI/MySQL journey in section 16, including 202/poll/committed lifecycle, every canonical action, View refresh, persistence/cardinality, Provider interaction count, and cleanup | Reopening P8-S2's internal atomicity matrix, Demo/in-memory substitutes, legacy Session-create entry, duplicate historical playtest, schema change, or live Provider | `PLAY-001`, the existing P8-S2 MySQL topology, and Phase 2.4a/2.4b public playtests require focused public-boundary evidence and one joined production path |

A listed existing test path changes only if its owning assertion needs P8-S3
synchronization. No sixth test path is permitted. A confirmed defect that
cannot receive a regression within this budget stops the slice for plan
reassessment.

## 10. Documentation and status boundary

The later P8-S3 implementation candidate may update at most these seven
status/authority owners:

| Path | Why it may need change | Exact assigned responsibility | Must not own | Inclusion evidence |
| --- | --- | --- | --- | --- |
| `PLANS.md` | Its current-phase ledger and canonical next-action inventory must advance only after accepted P8-S3 implementation | Record exact P8-S3 implementation/evidence/review/publication state and the truthful next slice | Public wire semantics, implementation detail, test design, or Phase 8 closure before P8-S6 | It is the repository-wide phase/status owner and currently names P8-S3 as the next unapproved plan candidate |
| `docs/architecture.md` | Its Phase 8 architecture status and implemented composition boundary may become stale | Record only the actual normal route/composition activation and preserved transaction/Demo boundaries | New architecture, authority redesign, Demo/Web activation, or completion claims | It owns the normal-composition, transaction, and high-level Phase 8 status description |
| `docs/public_client_contract.md` | The planned `/v1/runs` wire contract will become implemented public behavior | Change status tense/evidence only while preserving every frozen request, response, error, privacy, and recovery rule | New fields, statuses, retry semantics, public Run reads, or client expansion | It is the canonical public wire/OpenAPI/recovery authority for Run entry |
| `docs/run_protocol.md` | Its Phase 8 amendment must distinguish implemented public activation from later lifecycle work | Record the exact reachable normal admission seam and retained Run/Session authority | Full Run protocol, completion/termination, world/visit, historicalization, or lifecycle redesign | It owns Run lifecycle and the bounded Phase 8 Session-backed activation exception |
| `docs/structured_player_character_contract.md` | Its downstream implementation-status appendix must remain truthful | Record that normal public entry is implemented without changing the frozen Player Character contract | Character schema, lifecycle, ownership, binding, retirement, or permanent-data changes | It owns the Structured Player Character authority and downstream implementation status |
| `docs/structured_player_character_implementation_plan.md` | Its programme status/current implementation map must advance from internal entry to normal activation | Record only actual P8-S3 status/evidence and that P8-S4 is next when warranted | Reopening Phase 5, marking Phase 6/7/8 complete, or rewriting historical plans | It is the programme implementation/status owner and current capability inventory |
| `docs/structured_player_character_run_playable_loop_plan.md` | Its slice ledger and P8-S3 scope/evidence record must reflect the accepted implementation | Record exact path/evidence/review/publication facts while preserving P8-S4/S5/S6 ownership | Editing the frozen P8-S2 plan, absorbing Demo/Web/closure, or changing P8-G0 authority | It is the approved Phase 8 slice-sequence, budget, and evidence authority |

This plan file becomes frozen immediately after independent approval. Its
approved bytes must then remain unchanged through the separate commit and user
publication, and it must not be edited during implementation merely to fit the
implementation candidate. If a material factual correction to this plan is
necessary, P8-S3 stops for a new exact-byte plan amendment and review before
implementation continues.

The documentation maximum is not an instruction to touch every owner
mechanically. Each applicable owner must nevertheless be truthful before
implementation review. No completed P8-S1 or P8-S2 plan is edited. No other
documentation path is admitted.

## 11. Path-by-path implementation procedure

The implementation task must proceed in this order.

### 11.1 Public DTOs

1. Add `RunEntryRequest` and `RunEntryResponse` to `api/schemas.py` with the
   exact field order, JSON types, bounds, extra-forbid behavior, strictness,
   frozen behavior, and no string normalization described in section 5.
2. Reuse `PlayerCharacterSelfProjection` only as the nested public type.
3. Do not import an ORM model or persistence carrier.
4. Confirm their validation-mode JSON schemas contain no internal models and
   that booleans, floats, numeric strings, whitespace-padded identifiers,
   controls, and extras fail where required.

### 11.2 Dependency container and fail-closed getter

1. Add one optional `RunEntryService` slot to `ApiServices`.
2. Add `get_run_entry_service(request)` that reads only that slot and raises
   `RuntimeError("Run entry service is not configured")` when absent.
3. Do not construct a fallback service, UoW, engine, resolver, issuer, or Demo
   object in the getter.

### 11.3 One lazy normal-composition instance

1. In `build_default_services()`, construct the normal `SessionService` once
   and retain it in a local variable instead of constructing it only inside
   the `ApiServices` return expression.
2. Construct the existing `PlayerCharacterService` once.
3. Construct the existing `RunService` once.
4. Add a narrow `build_run_entry_service(*, run_service, session_service)`
   helper, or an equivalently explicit local construction, that creates
   exactly one `RunEntryService` using:
   - `run_service.uow_factory`;
   - `run_service.run_id_issuer`;
   - `run_service.continuous_story_line_id_issuer`;
   - `run_service.source_reference`;
   - `run_service.clock`;
   - `run_service.controller_binding_resolver`;
   - `run_service.player_character_binding_evidence`; and
   - the exact already-built normal `session_service`.
5. Store the exact resulting instance in `ApiServices.run_entry_service`.
6. Assert by identity that entry, Run, Player Character, Session, and turn
   orchestration use the same normal `uow_factory`; entry and Run share the
   same Run/line issuers, source, clock, resolver, and Player Character
   evidence object; and entry uses the exact public Session service.
7. Construction must perform zero UoW factory calls, SQL, commit, identity
   issuance, Provider call, or application mutation.

The entry service receives catalogues, Session/seed/event issuers,
`DeterministicStoryDirector`, memory rules, and the Session clock through the
single reused `SessionService`; it receives the production Run/line issuers,
source, and clock through the reused `RunService`. It does not receive or call
the narrative Provider during entry.

### 11.4 Route and transport adapter

1. Register `/v1/runs` only when `services is None` or
   `services.run_entry_service is not None`. A supplied composition with the
   slot absent registers no route and no Run-entry OpenAPI components.
2. Declare the exact route metadata and response set from section 5.
3. Bind the public body to `RunEntryRequest`, the required header to the
   existing exact `Idempotency-Key` header schema, the principal to
   `get_current_principal`, and the service to `get_run_entry_service`.
4. Reuse the existing raw Content-Type/Idempotency-Key validator through a
   thin Run-entry conversion that returns `RunEntryPublicOperationKey`. Do not
   alter completed Player Character transport behavior.
5. Construct one exact `RunEntryCommand` and invoke `enter()` once.
6. For a `RunEntryResult`, strictly validate and project it field by field into
   `RunEntryResponse`.
7. For a `RunEntryDecision`, apply only section 12's table.
8. Treat an unexpected return type, impossible decision, malformed success,
   or mapping invariant failure as an ordinary internal failure handled by the
   existing sanitized 500 edge. Do not retry or call the service again.
9. Do not catch `CancelledError` or `BaseException`.

### 11.5 OpenAPI and global compatibility

1. Generate request OpenAPI from the public `RunEntryRequest`, not the internal
   command.
2. Use `RunEntryResponse` as the response model.
3. Use `_public_error_responses(404, 409, 422, 500)` so runtime and OpenAPI use
   the same envelope and existing descriptions.
4. Confirm the custom Player Character OpenAPI installer remains atomic and
   unchanged in behavior; Run-entry DTOs must not collide with its components.
5. Preserve every existing route, status, operation schema, lifespan cleanup,
   exception handler, and Demo route inventory.

## 12. Decision and public error mapping

### 12.1 Exact decision mapping

The adapter maps the exact P8-S2 decision codes as follows:

| `RunEntryDecisionCode` | HTTP | `error.error_code` | Fixed public message | Mapping mechanism |
| --- | ---: | --- | --- | --- |
| `AUTHORIZATION_FAILED` | 404 | `PLAYER_CHARACTER_NOT_FOUND` | `Player character was not found` | Raise the existing `PlayerCharacterNotFoundError` boundary or return its exact existing envelope |
| `IDEMPOTENCY_CONFLICT` | 409 | `IDEMPOTENCY_CONFLICT` | `Idempotency key was reused` | Raise the existing `IdempotencyConflictError` boundary or return its exact existing envelope |
| `PLAYER_CHARACTER_STALE` | 409 | `PLAYER_CHARACTER_STALE` | `Player character revision is stale` | Fixed `error_response`; no internal value in the message |
| `PLAYER_CHARACTER_NOT_ELIGIBLE` | 409 | `PLAYER_CHARACTER_NOT_ELIGIBLE` | `Player character is not eligible for Run entry` | Fixed `error_response`; do not disclose lifecycle, binding, Run, or exhaustion detail |
| `INVALID_SCENARIO_DEFINITION` | 422 | `INVALID_SCENARIO_DEFINITION` | `Scenario definition is not available` | Raise the existing `InvalidScenarioDefinitionError` boundary or return its exact existing envelope |
| `RUN_ENTRY_CONFLICT` | 409 | `RUN_ENTRY_CONFLICT` | `Run entry conflicts with current state` | Fixed `error_response`; do not disclose table, key, CAS, participation, or competing identity |

Messages are fixed literals. They must not interpolate a request value,
principal, controller, character ID, Run ID, Session ID, exception, SQL detail,
constraint, or state.

### 12.2 Precedence and non-decision failures

The route preserves the service's established decision precedence. It may not
pre-map an advisory eligible result or perform a second query. The observable
boundaries are:

| Condition | Public behavior | Service calls | Persistence owned by API |
| --- | --- | ---: | ---: |
| Missing/malformed/duplicate header, non-JSON media type, invalid JSON/body/type/extra | 422 `REQUEST_VALIDATION_FAILED` | 0 | 0 |
| Dependency unavailable or unexpected dependency failure | sanitized 500 `INTERNAL_SERVER_ERROR` unless the existing framework gives a narrower approved envelope | 0 | 0 |
| Exact `RunEntryResult` | 200 exact `RunEntryResponse` | 1 | 0 |
| Exact replay result | 200 byte/JSON-equivalent stable projection | 1 | 0 |
| Any expected decision | table above | 1 | 0 |
| Corrupt/impossible result or decision, `RunEntryIntegrityError`, repository/integrity/persistence/generator/commit/programming error | sanitized 500 `INTERNAL_SERVER_ERROR` | 1 at most | 0 |
| `asyncio.CancelledError` before/during the service call | propagates; no public translation or success claim | 0 or 1 | 0 |

The API must not broadly translate exceptions into one of the six business
decisions. That would hide integrity failures and change P8-S2 authority.

## 13. Public projection and privacy rules

The success response is an allowlist, not a filtered internal model. Exact
top-level keys are `run_id`, `session_id`, `scenario_id`, and
`player_character`. Exact nested character keys are `player_character_id`,
`contract_version`, `record_revision`, and `lifecycle`.

The response and every error must exclude, by key and serialized value:

- continuous-story-line identity;
- Run state version, lifecycle, revisions, mutation provenance, source, and
  transaction time;
- controller binding, principal fields, ownership proof, authority source,
  operation IDs/namespaces, fingerprints, receipts, creation evidence, and
  replay diagnostics;
- applicable-reference internals beyond the detached public four-field
  projection;
- active-binding records/times, participation internals, static character
  definition, random seed, initial event IDs, snapshot, hidden scenario state,
  memory internals, job/lease/request internals, Provider data, SQL, constraint
  names, database URLs, paths, tracebacks, or exception text; and
- any field added later to an internal model unless a separately reviewed
  public allowlist explicitly adds it.

Foreign, missing, and unavailable-authority targets remain the identical 404.
Malformed or corrupt surviving ownership/state evidence is not disguised as a
404; it reaches only the sanitized 500 envelope. `PLAYER_CHARACTER_NOT_ELIGIBLE`
must not say whether the character is retired, deceased, bound,
version-exhausted, or otherwise ineligible. `RUN_ENTRY_CONFLICT` must not name
the losing repository or competing identity.

Privacy tests must scan both field names and serialized values across success,
replay, every decision, malformed internal results, and injected failures.

## 14. Normal composition design

The required object graph is:

```text
one normal session_factory
  -> one lazy uow_factory returning SqlAlchemyUnitOfWork(session_factory)
       -> SessionService
       -> DurableNarrativeTurnOrchestrator
       -> PlayerCharacterService
       -> RunService
            -> production Run/line issuers
            -> source.production-run
            -> normal Run clock
            -> configured controller resolver
            -> exact PlayerCharacterService evidence object
       -> RunEntryService
            -> exact same uow_factory
            -> exact RunService issuers/source/clock/resolver/evidence
            -> exact same SessionService
```

`ApiServices` owns references only. `get_run_entry_service()` retrieves the
already composed entry service. Neither performs work merely by being
constructed or read.

Normal Provider composition remains independent from Run entry. The existing
`DurableNarrativeTurnOrchestrator` may use the normally configured Provider for
later gameplay actions, but `POST /v1/runs` and every View/status query perform
no Provider call. P8-S3 introduces no deterministic Provider fallback into
normal composition.

Demo remains a separate composition root. `build_demo_runtime()` continues to
construct `ApiServices` with no Player Character, Run, or Run-entry service.
Because route registration is conditional on `run_entry_service`, Demo exposes
no `/v1/runs` path or Run-entry schemas in P8-S3. P8-S4 alone owns process-local
Player Character/Run persistence and Demo route activation. No Demo source or
test path is edited in P8-S3.

## 15. Unit and OpenAPI evidence matrix

The focused tests must discriminate behavior, not merely execute filenames.

| Evidence case | Stimulus | Required observations |
| --- | --- | --- |
| Route inventory | Normal default app and supplied service/absent-service compositions | Exactly one normal `POST /v1/runs`; no alternate method/path; absent service and Demo-like composition expose neither path nor schema; every existing route remains |
| Authentication | Override `get_current_principal`; attempt query/body/header identity injection | Exact trusted principal object reaches `enter()`; untrusted identity fields reject/ignore only as the contract directs; no principal derivation from request data |
| Required key | Missing key | Fixed 422, zero route service call |
| Single raw key | Duplicate raw headers, comma-folded value, alternate spelling source, non-ASCII, controls, whitespace, 0/129 length, bad first character/punctuation | Fixed 422, zero service call; exact valid 1/128 boundaries and case are preserved |
| JSON media type | Missing, duplicate, conflicting, non-ASCII, or non-`application/json` Content-Type; valid case/parameter forms | Invalid cases fixed 422 and zero call; admitted JSON form constructs the exact command |
| Strict body | Missing each field, null, boolean/float/string revision, zero/overflow revision, malformed/over-bound/control/whitespace IDs, extra/internal fields, arrays/scalars/top-level malformed JSON | Fixed 422 and zero service call; exact three-field valid JSON succeeds |
| Exact command | Boundary-valued valid request | One `RunEntryCommand` with exact `RunEntryPublicOperationKey`, `PlayerCharacterId`, `PlayerCharacterRevision`, and scenario; no normalization/default/inferred field |
| One call/no API UoW | Spy service and forbidden UoW/repository/commit sentinels | `enter()` exactly once after valid transport; no API/composition UoW or commit; failures before call produce zero calls; decisions/results never trigger a second call |
| Success allowlist | Valid exact internal result containing canonical IDs/projection | 200 and exact four/four keys; public Run/session/scenario scalar forms; new detached nested projection; no internal dump/exclusion projection |
| Impossible success | Actual-state mutation, wrong nested lifecycle/revision/identity, unexpected result type | Sanitized 500, one call, no repair/retry, no private value |
| Exact replay | Service returns the same persisted result on repeated exact HTTP request | Identical 200 JSON; each HTTP request calls the service once; adapter adds no mutable View/Run state |
| Decision mapping | Each of six decision codes | Exact status/code/message table; one service call; no second query or retry |
| Decision precedence | Spy results representing authorization, replay/key conflict, stale, eligibility, scenario, and write conflict boundaries | Adapter does not reorder or replace the service result; ownership 404 remains non-enumerating; stale/eligibility are not evaluated by API |
| Sanitized failures | `RunEntryIntegrityError`, validation/integrity/repository/commit-like errors containing SQL, URL, path, IDs, or constraint text | Fixed 500 body contains none of the injected text; logger/public response exposes type only under existing policy; one call at most |
| Cancellation | Exact `CancelledError` from dependency/body/service | Same exception identity propagates where the ASGI harness permits observation; no public mapping, retry, success, or second call |
| Dependency fail-closed | `run_entry_service=None` and direct getter call; failing dependency | Getter raises fixed not-configured error; route is absent when composition declares no service; failures cannot select Run or Player Character services as fallback |
| Lazy composition | Instrument UoW factory, issuers, engine/session factory, provider | One entry-service object; shared identities described in section 14; zero UoW/ID/Provider call at construction/import; first explicit service call alone can enter UoW |
| Demo independence | Build or represent the existing Demo `ApiServices` | `run_entry_service is None`; no `/v1/runs`; no Run-entry schema; no normal engine/config/resolver/Provider credential access caused by P8-S3 |
| OpenAPI operation | Inspect complete schema | Exact method/path, tag, operationId, summary/description, one required header, one required JSON body, status set, response refs, and public envelope |
| OpenAPI DTOs | Inspect components and resolve every local ref | Exact request three-field schema and response four-field schema; exact numeric/string bounds; `additionalProperties: false`; no internal components; existing action 200/202 and request-status contracts unchanged |
| Unrelated behavior | Exercise health, Player Character discovery/create/read/retirement, scenario, legacy Session, View, action, and status inventories as owned by existing tests | No changed status/envelope/route behavior; P8-S1/P8-S2 remain closed; no public Run operation other than POST entry |

Framework, body, dependency, and route failures must use the current approved
public envelope where that route is part of the public contract. Tests must not
assert raw FastAPI validation details as public behavior.

## 16. Real-MySQL public entry-to-terminal playthrough

The new integration file contains a focused public/MySQL boundary group and
exactly one joined production-path playthrough. Neither reopens P8-S2's closed
internal atomicity/concurrency/rollback matrix or copies the historical Phase
2.4 tests under another name.

### 16.1 Focused public/MySQL boundary cases

Using the production ASGI route, real `SqlAlchemyUnitOfWork`/repositories,
normal production service graph, deterministic issuers/clocks, trusted
principal override, and scoped MySQL rows, focused tests must prove:

| Case | Public observation | Fresh persistence/interaction observation |
| --- | --- | --- |
| First success then exact replay | Exact 200 four-field projection twice | One admission family, one issuance set, no replay write/commit/state advance, no Provider call |
| Same controller/key with changed public command | Exact 409 `IDEMPOTENCY_CONFLICT` envelope | Original family unchanged; no new identity, Session, participation, binding, receipt, or Provider call |
| Missing/foreign target and unavailable controller mapping | Byte/JSON-identical 404 `PLAYER_CHARACTER_NOT_FOUND` envelopes | No private row/value disclosure and no mutation/issuance/Provider call |
| Receipt-absent stale revision followed separately by owned ineligible/bound target | Exact respective 409 `PLAYER_CHARACTER_STALE` and `PLAYER_CHARACTER_NOT_ELIGIBLE` envelopes | No admission family or state mutation; the adapter performs no eligibility query or retry |
| Unavailable current scenario/default definition | Exact 422 `INVALID_SCENARIO_DEFINITION` envelope | No Run/Session/admission write, identity issuance, commit, or Provider call |

Each case starts from its own explicit scoped state and inspects fresh database
state after the public response. Setup may call production services, but the
claimed behavior begins at `POST /v1/runs`; no test calls
`RunEntryService.enter()` as a substitute. These cases test P8-S3 transport and
composition reachability across real persistence. They must not duplicate the
already closed P8-S2 staged-failure, tamper, concurrency, or uncertain-commit
matrix.

### 16.2 Exact playthrough setup

The test must:

1. use the existing `mysql_session_factory` fixture, which fail-closes unless
   the URL is `mysql+asyncmy` and the database is exactly
   `deviation_protocol_test`;
2. load the real `death_certificate` scenario/content catalogue;
3. create a unique trusted `RequestPrincipal`, controller binding, Player
   Character ID, Run ID, line ID, Session ID, and scoped cleanup inventory;
4. use a configured/test resolver that maps only that exact principal to that
   exact controller;
5. create the eligible active unbound Player Character through the production
   `PlayerCharacterService.create()` authorized setup boundary, with the real
   repositories/UoW, deterministic Player Character issuer, and fixed UTC
   clock; verify it is revision 1 and unbound;
6. build one shared `uow_factory = lambda:
   SqlAlchemyUnitOfWork(mysql_session_factory)`;
7. construct the real production `SessionService`, `PlayerCharacterService`,
   `RunService`, `RunEntryService`, and
   `DurableNarrativeTurnOrchestrator` graph exactly as section 14 requires;
8. substitute only deterministic IDs/seeds/event/job/lease/worker values,
   fixed UTC clock, and a blocking wrapper over the existing scripted
   no-network Provider seam;
9. construct `ApiServices` with those exact production services and
   `create_app(services=...)`, then override only the trusted principal
   dependency; and
10. begin the claimed public admission path at `POST /v1/runs`, never legacy
    `POST /v1/sessions`, a direct `RunEntryService.enter()` call, Demo storage,
    or an in-memory repository.

The blocking wrapper pauses only canonical action 2's `CUSTOM` call for the
section 16.4 lifecycle. Canonical actions 10, 11, and 13 use the same scripted
seam without blocking; no other canonical action invokes it. The scripted
Provider performs no network I/O. `RUN_LIVE_DEEPSEEK_TEST` remains disabled.
The test must not read Provider credentials.

### 16.3 Admission, replay, and initial observations

Send one real ASGI request with exact JSON headers/body. Require:

- HTTP 200 and the exact four-field/four-field public projection;
- returned Run, Session, scenario, and character values equal the deterministic
  trusted setup and no other identity is public;
- Run/line/Session issuers each called exactly once;
- zero scripted Provider calls during entry;
- immediate exact same-key/same-body replay returns identical JSON, issues no
  identity, changes no row, advances no state, commits no second admission,
  and still makes zero Provider calls; and
- an initial `GET /v1/sessions/{returned_session_id}/view` succeeds, belongs to
  the exact returned Session, has state version 0, exposes the bound
  `DECISION` affordance with the canonical opening `CHOOSE` among its displayed
  choices, and advertises no free `CUSTOM` action.

From fresh `SqlAlchemyUnitOfWork`/SQLAlchemy reads after admission, require:

- one Run current row at state version 3 and lifecycle `active`;
- exactly Run revisions 1/2/3 with `CREATE`, `BIND_PLAYER_CHARACTER`, and
  `ATTACH_SESSION` semantics;
- exactly one Run creation receipt and two Run mutation receipts;
- exactly one active immutable binding to the setup Player Character and its
  revision-1 `ApplicableCharacterReference`;
- exactly one participation joining the returned Session at Run version 3;
- exactly one Session row, one version-zero initial snapshot, and exactly one
  sequence-one `ScenarioStarted` initialization event before gameplay;
- the Session owner/scenario/version/default static character definition match
  server-selected authoritative data;
- the Player Character remains unchanged at active revision 1; and
- no second Run, Session, participation, binding, or admission receipt exists.

### 16.4 Genuine 202 and request-status lifecycle

Before starting Provider-backed work:

1. use the initial View's bound `decision_id` and displayed
   `death_certificate.action.move_fingers_rhythmically` choice to submit
   canonical action 1 as `CHOOSE` through the public action endpoint;
2. require HTTP 200, resulting state version 1, and zero Provider call or
   narrative-job row for that trusted decision action; and
3. refresh the authoritative Session View, require state version 1 and
   `FREE_ACTIONS`, and require that it now advertises `CUSTOM` with the current
   description input contract.

Only then, for the following canonical `CUSTOM` narrative action at ordinal 2:

1. start the public action POST in a task and block only inside the scripted
   Provider after its durable job is prepared/claimed;
2. submit an exact concurrent duplicate of the same Session/turn/request/body;
3. require that duplicate action response to be HTTP 202 with the existing
   exact pending `ActionResponse` and no second Provider call;
4. `GET /v1/sessions/{session_id}/requests/{client_request_id}` while blocked
   and require HTTP 200, `PENDING`, `POLL_SAME_REQUEST`, and the existing
   `Retry-After` contract;
5. refresh the Session View while pending and prove it remains the last
   committed state and the read changes no job, View, Session, snapshot, or
   Run;
6. release the Provider, require the original action POST to return HTTP 200
   `COMMITTED`, and require exactly one Provider call;
7. poll the same request-status path and require `COMMITTED`,
   `RESPONSE_AVAILABLE`, and a nested response exactly equal to the committed
   action response; and
8. refresh the authoritative View and bind every later step to that current
   View.

This is a real production request-status lifecycle. A fake 202 response, a
direct repository status mutation, or a component-only status call is not
acceptable.

### 16.5 Exact canonical action journey

Continue through the existing happy terminal path using only the public action
endpoint and the current server-provided View affordances. The 19 unique
action requests, in order, are:

1. `CHOOSE` — displayed
   `death_certificate.action.move_fingers_rhythmically` opening choice from the
   initial bound decision View;
2. `CUSTOM` — the refreshed View's advertised clinical-recheck action and the
   blocking/202 lifecycle above;
3. `CONTINUE` — life-disputed step 1;
4. `CONTINUE` — life-disputed step 2;
5. `CHOOSE` — displayed `death_certificate.action.prove_vitals` early-strategy
   choice from the current View;
6. `CONTINUE` — escape step 1;
7. `CONTINUE` — escape step 2;
8. `CONTINUE` — investigation step;
9. `CHOOSE` — displayed `death_certificate.action.inspect_archive`
   investigation choice from the current View;
10. `EXPLORE` — records/archive evidence;
11. `EXPLORE` — audit/log evidence;
12. `CHOOSE` — displayed `death_certificate.action.open_observation` second
    investigation choice from the current View;
13. `OBSERVE` — underground patient evidence;
14. `CONTINUE` — truth step 1;
15. `CONTINUE` — truth step 2;
16. `CHOOSE` — displayed `death_certificate.action.pause_protocol`
    core-conflict window 1 choice;
17. `CHOOSE` — displayed `death_certificate.action.ask_coordinator`
    core-conflict window 2 choice;
18. `CHOOSE` — displayed `death_certificate.action.public_override`
    core-conflict window 3 choice; and
19. `CHOOSE` — displayed `death_certificate.action.final_suspend`
    core-conflict window 4 choice and trusted local terminal settlement.

Before every submission and after every completed action, read the
authoritative Session View and require its metadata/state version, scenario
lifecycle, current Frame, presentation, and affordances to agree with the last
committed response. Submit `CHOOSE` only from a `DECISION` View and use its
displayed `decision_id` and choice ID. Submit every non-choice action only from
a `FREE_ACTIONS` View that advertises that exact action type and input contract.
The exact choice IDs named above are assertions against the current View; the
test never calls a private issuer or copies a scenario rule into authority.

The four narrative actions at ordinals 2, 10, 11, and 13 (`CUSTOM`, the two
`EXPLORE` actions, and `OBSERVE`) produce exactly four scripted Provider calls.
`POST /v1/runs`, entry replay, View/status reads, `CONTINUE`, `CHOOSE`, and
local terminal settlement produce none. The final local settlement job remains
the existing trusted server-template, attempt-zero path.

### 16.6 Terminal persistence and cardinality assertions

At terminal state, require fresh production persistence reads to prove:

- the exact Session returned by `POST /v1/runs` is `ENDED` and its View is
  `ENDED` with `ending_status=RESOLVED`, the authoritative ending presentation,
  no action affordance, and completed scenario memory;
- the Session row and latest snapshot have the same final state version;
- snapshot runtime ending and memory agree with the View;
- event sequence numbers are contiguous and contain exactly one initialization
  `ScenarioStarted`, the required narrative/auto-beat/decision/ending events,
  and no duplicate caused by the 202 retry;
- exactly 19 unique turn-request rows exist; the concurrent duplicate shares
  canonical action 2's `CUSTOM` request identity and creates no second durable
  request/response row;
- exactly five committed narrative-job rows exist: four scripted Provider jobs
  and one `local-server-template-v1` attempt-zero terminal job;
- exactly four Provider calls occurred and no Provider call overlapped an
  active entry transaction;
- the Run still has exactly three revisions, one creation receipt, two mutation
  receipts, one participation, state version 3, lifecycle `active`, and the
  same immutable active Player Character binding;
- the Player Character remains active at revision 1; scenario ending did not
  retire, unbind, historicalize, complete, or terminate anything; and
- an exact Run-entry replay after terminal gameplay still returns the original
  stable 200 projection without new issuance, admission rows, state advance,
  commit, or Provider call.

Cleanup must delete only the test's explicitly tracked Run, Session, Player
Character, receipt, binding, event, snapshot, request, and job rows in
foreign-key-safe order. Fresh scoped counts after cleanup must all be zero.
The test must not clean unrelated rows or rely on broad database truncation.

## 17. Verification sequence

The later implementation task must run the following sequence with PowerShell
7+ and the explicit project interpreter. These commands are implementation
obligations; they are not authorized during this plan-authoring task.

1. Focused Run-entry API tests:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/unit/test_run_entry_api.py
   ```

2. Focused normal-composition tests:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/unit/test_run_composition.py
   ```

3. Focused general public-contract/OpenAPI tests:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/unit/test_api.py tests/unit/test_phase_3_0_public_client_contract.py
   ```

4. Focused real-MySQL Run-entry public-boundary cases and the dedicated single
   public entry-to-terminal playthrough:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/integration/test_mysql_run_entry_playthrough.py
   ```

5. Alembic stability:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic heads
   .\.venv\Scripts\python.exe -m alembic history
   ```

6. Compilation:

   ```powershell
   .\.venv\Scripts\python.exe -m compileall -q src tests alembic
   ```

7. Canonical local verification:

   ```powershell
   .\scripts\verify.ps1 -Mode Offline
   .\scripts\verify.ps1 -Mode MySQL
   ```

8. Diff validation:

   ```powershell
   git diff --check
   ```

Full verification is reserved for P8-S6 and is not a P8-S3 local requirement.
No live external Provider call is permitted. Required affected unit/OpenAPI
tests and real-MySQL evidence may not be skipped merely because CI may run
later. An environmental check that cannot safely run must be reported as
blocked with its exact prerequisite; it must not be represented as passing or
silently replaced with a weaker mode.

## 18. Explicit exclusions and deferrals

P8-S3 explicitly excludes and defers:

- Demo persistence, repositories, issuers, composition, and route activation
  to P8-S4;
- Web/frontend connection and retry/recovery UI to P8-S5;
- final cross-surface reruns, Full verification, and Phase 8 closure to P8-S6;
- public Run read, list, search, patch, bind, rebind, attach, resume, complete,
  terminate, exit, delete, or administrative operations;
- later Session admission, later scenario selection, continuous-line
  continuation, Run resume/discovery, or post-ending reuse;
- Run completion/termination and binding historicalization;
- unbinding, rebinding, character switching, replacement, transfer, or
  revision-following policy;
- new scenario, world, visit, profile, difficulty, gameplay, or content
  behavior;
- Provider integration, Provider selection, live network behavior, fallback,
  credentials, billing, or distribution;
- narrative-system changes, world/profile compilation, NPC, relationship,
  memory-subject, combat, inventory, equipment, economy, reward, progression,
  or general character-development systems;
- authentication redesign, production authentication, deployment, release,
  monitoring, CORS, quota, or abuse controls;
- schema, ORM, migration, backfill, dependency, configuration, fixture,
  generated, or lock-file changes;
- P8-S1 eligible-discovery redesign or test expansion outside the admitted
  P8-S3 paths;
- P8-S2 service, transaction, replay, persistence, plan, implementation,
  review, correction, or evidence changes; and
- unrelated API, Session, Run, Demo, Web, Provider, test, or documentation
  cleanup.

These exclusions are slice discipline, not permanent product rejection.

## 19. Failure, cancellation, and rollback expectations

Every failure before `RunEntryService.enter()` produces no entry-service call
and no application mutation. Every returned decision is mapped once without
post-result persistence. Every unexpected `Exception` at the public edge uses
the current fixed sanitized 500 envelope; exception messages, SQL, URLs,
paths, constraints, internal IDs, and tracebacks remain private.

The route does not catch `asyncio.CancelledError`, `BaseException`, or broad
application errors. Cancellation propagates into the existing P8-S2 UoW
cleanup. The service remains solely responsible for rollback/close of
uncommitted, exceptional, cancellation, replay-read, and controlled conflict
paths.

If the service's one `commit()` raises or is cancelled, durability may be
unknown. The API returns no success, performs no second call/read/commit, and
does not claim rollback or failure certainty. A later explicit exact-key/body
request follows ordinary P8-S2 authority. A later non-enumerating 404 does not
prove the earlier attempt did not commit.

No broad exception handler may convert programming or integrity errors into an
expected 404/409/422 decision. No API-level rollback assertion may claim more
than the service/UoW evidence actually proves.

## 20. Implementation stop conditions

P8-S3 implementation must stop and report the exact blocker if any of these is
true:

- the implementation baseline is not the independently approved and published
  exact plan-and-status candidate;
- P8-S2 is not closed at
  `70815b181624e5475d2d978bef0db1ed3b22324e` or its public-facing internal
  contract differs materially;
- a public field, status, decision precedence, ownership rule, replay rule,
  transaction boundary, or privacy rule is contradictory or unresolved;
- the adapter would need a second `enter()` call, direct repository/UoW work,
  a second eligibility check, post-result persistence, or retry/recovery;
- the exact DTO/error/OpenAPI contract cannot be represented within the four
  production paths;
- the required discriminating evidence cannot fit the five test paths;
- truthful implementation status cannot fit the seven documentation owners;
- a migration, ORM, repository, UoW, application, domain, dependency,
  configuration, fixture, generated, Demo, or Web path is required;
- normal composition cannot reuse one shared UoW graph and the exact existing
  Run/Session/Player Character dependencies lazily;
- Demo gains `/v1/runs` or Run-entry schemas before P8-S4;
- the real-MySQL proof cannot begin at public `POST /v1/runs`, use the returned
  Session for every canonical step, exercise a genuine 202/request-status
  lifecycle, or prove persisted admission/gameplay state;
- a live Provider or non-MySQL fallback would be required;
- any required local check is skipped, weakened, or falsely reported; or
- this approved plan would need editing during implementation to fit the
  candidate.

No stop condition authorizes path-budget expansion or a semantic default.

## 21. Review and approval gates

The plan gate is:

1. freeze the exact eight-document candidate and record all eight SHA-256
   identities;
2. conduct a fresh independent read-only review in a separate task;
3. require the exact sole verdict
   `STRUCTURED_PLAYER_CHARACTER_P8_S3_PLAN_REVIEW_APPROVED` for the exact files
   and hashes;
4. if any byte changes, invalidate the hashes/verdict and repeat the review;
5. obtain separate explicit authorization for the exact documentation commit;
6. verify the staged and committed bytes/scope against the approved hashes;
7. the user publishes manually;
8. confirm `main`, `HEAD`, and local `origin/main` are aligned at the published
   documentation commit with `0/0`, a clean worktree, empty index, no normal
   untracked path, and no active Git operation; and
9. obtain a separate explicit P8-S3 implementation task.

The plan review is read-only. It must not implement, correct, approve and
commit in one task, stage, commit, push, or begin P8-S3. P8-S2 remains closed
throughout.

After implementation and the section 17 evidence, the exact complete P8-S3
implementation/status candidate requires a fresh independent implementation
review under separately defined authority. Plan approval does not pre-approve
that later candidate or P8-S4.

## 22. Commit and publication boundary

This authoring task performs no staging, commit, push, or publication. The
candidate remains seven modified tracked files plus this one new untracked
plan.

After successful plan review, a local documentation commit requires separate
authorization for that exact operation and exact eight paths. Codex never
pushes this repository; the user performs publication. No implementation may
begin before the approved plan bytes are published and the clean aligned
baseline is confirmed.

The later P8-S3 implementation candidate has its own separate review and commit
boundary. It is limited to the `4 + 5 + 7` maxima above, excludes this frozen
plan file, and grants no P8-S4 authority.

## 23. Completion criteria

### 23.1 Plan-candidate completion

This plan-authoring candidate is complete only when:

- exactly this one new P8-S3 plan exists;
- exactly the seven authorized status owners are minimally synchronized;
- all eight documents truthfully record P8-G0/P8-S1/P8-S2 closure, P8-S2's
  publication commit, P8-S3 candidate-only status, and P8-S4/P8-S5/P8-S6
  deferrals;
- no production, test, migration, dependency, configuration, fixture,
  generated, or ninth documentation path changes;
- the index remains empty;
- the complete diff is inspected;
- status contradiction searches are resolved;
- `git diff --check` passes; and
- line count, raw byte length, and SHA-256 are recorded for all eight changed
  documents.

### 23.2 Later P8-S3 implementation completion

P8-S3 implementation is complete only when:

- normal composition exposes exactly the approved `POST /v1/runs` route;
- the exact public DTO/error/OpenAPI contract passes;
- the route constructs one command, forwards the trusted principal, and calls
  `RunEntryService.enter()` at most once;
- API/composition perform no UoW, commit, retry, recovery, or persistence;
- result projection, replay, all decisions, precedence, privacy, sanitization,
  and cancellation pass focused evidence;
- the single entry-service instance shares the exact normal Run/Session/Player
  Character/UoW graph lazily;
- Demo remains unactivated;
- the real-MySQL public entry-to-terminal proof passes with the genuine 202
  lifecycle on ordinal-2 `CUSTOM`, all 19 canonical View-driven actions, four
  Provider calls, five narrative-job rows, terminal View, still-active Run, and
  zero scoped residual rows;
- every command in section 17 passes or an environmental blocker is reported
  truthfully;
- applicable seven-owner implementation status is synchronized without
  changing this frozen plan; and
- a fresh independent P8-S3 implementation review approves the exact
  candidate before any implementation commit.

P8-S3 completion does not complete Phase 8 and does not authorize P8-S4.

## 24. Unresolved decisions

**None.**

Current repository authority fixes every material P8-S3 choice: public fields,
bounds, statuses, decision precedence, ownership/non-enumeration, replay,
transaction ownership, normal composition dependencies, Demo separation,
schema stability, path budgets, required evidence, exclusions, and workflow
gates. Implementation must stop rather than silently reopen any of them.

## 25. Guardrail impact

None. This plan applies existing `DB-001`, `AUTH-001`, `API-001`, and
`PLAY-001`; no confirmed defect in this plan-authoring task creates or changes
a reusable guardrail.

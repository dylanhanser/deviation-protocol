# Structured Player-Character P5-S1 Owned-read Activation Implementation Plan

## 1. Status and purpose

Status: **Approved for implementation after a fresh independent read-only review
returned the required successful verdict for the exact pre-record candidate
(SHA-256 `a5f66316265fcf996f8aa683595c41e710bc849b09be1128d63bc02d611fe986`).
Implementation has not started and remains separately authorized.**

This document defines the smallest coherent P5-S1 unit: expose one
authenticated-controller read of one already committed canonical Player
Character through the normal public HTTP boundary by reusing the completed
Phase 3 owned-read service and its accepted detached self projection.

P5-S1 is read-only. It does not create or mutate a Player Character, bind one to
a Run, advance a Run, list or search characters, grant administrator access, or
activate any frontend, Demo, Provider, narrative, scenario, world, action, or
gameplay behavior.

The implementation baseline for this draft is:

- repository root: `D:\deviation-protocol`;
- branch: `main`;
- `HEAD`: `92c5ad4414e486f1131b907097ee3103d811418d`;
- local `origin/main`: `92c5ad4414e486f1131b907097ee3103d811418d`;
- ahead/behind: `0/0`;
- `HEAD` subject: `docs(player-character): synchronize P4-S1 status`;
- clean worktree and index;
- no visible untracked or unmerged paths; and
- no active Git operation.

At authoring time, this document is the sole new untracked path. It changes no
runtime, schema, migration, dependency, API, frontend, Demo, Provider, or
database behavior.

## 2. Authority hierarchy and evidence classification

Authority remains divided by subject. A broader document does not displace a
narrower retained authority.

### 2.1 Frozen authority

1. [`structured_player_character_contract.md`](structured_player_character_contract.md)
   governs Player Character identity, controller ownership, canonical-record
   validation, lifecycle, projection, privacy, and non-enumeration.
2. [`final_narrative_experience.md`](final_narrative_experience.md) governs the
   cross-phase persistent-character product boundary and model/server authority.
3. [`public_client_contract.md`](public_client_contract.md) retains authority
   over the current public error envelope, safe projection, OpenAPI, and
   non-enumeration conventions.
4. [`run_protocol.md`](run_protocol.md) retains Run lifecycle and world/Run
   authority. It supplies no authority to activate binding or lifecycle work in
   P5-S1.
5. [`architecture.md`](architecture.md) is the retained authority for
   implemented dependency direction, composition roots, principal handling,
   public routing, and current runtime behavior.
6. [`engineering/guardrails.md`](engineering/guardrails.md), especially
   `AUTH-001`, `STATE-001`, `API-001`, and `PLAY-001`, remains binding.

### 2.2 Approved implementation plans

- [`structured_player_character_implementation_plan.md`](structured_player_character_implementation_plan.md)
  assigns P5-S1 the thin authenticated public read over the accepted detached
  projection and leaves create, mutation, and UI to later separately authorized
  units.
- [`minimum_run_core_implementation_plan.md`](minimum_run_core_implementation_plan.md)
  and
  [`structured_player_character_p4_s1_implementation_plan.md`](structured_player_character_p4_s1_implementation_plan.md)
  define the completed internal Run boundary that P5-S1 must not widen.
- [`engineering/codex_workflow.md`](engineering/codex_workflow.md) controls
  baseline invalidation, one operative approval verdict, documentation
  synchronization, verification, and Git handoff.

These plans are normative only within their approved scopes. Prospective
inventory and historical wording are not promoted over current frozen
authority or committed behavior.

### 2.3 Committed implementation behavior

| Commit | Classification | Material evidence used by P5-S1 |
| --- | --- | --- |
| `cafb12272e703e8751c78bb6852cec90d7d7ec8d` | Committed implementation behavior | Completed Phase 3 `PlayerCharacterService.get_owned`, `PlayerCharacterSelfProjection`, configured controller resolver, UUIDv4 issuer, normal composition, and their tests |
| `e821cd922b61868097667b12c2b64cf8089a9681` | Committed implementation behavior | Minimum Run Core, Run-owned UoW/repositories, reserved binding representation, and no public Run route |
| `748003319ececa548b68b351746afbb2d54c66bb` | Committed implementation behavior | P4-S1a lifecycle-integrity guard and internal binding evidence seam |
| `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f` | Committed implementation behavior | P4-S1b internal atomic binding service/repositories/composition while the reserved public command remains rejected |
| `92c5ad4414e486f1131b907097ee3103d811418d` | Status-record commit | Documentation-only P4-S1 closeout and identification of P5-S1 as the next canonical unit |

The current source and tests, not commit summaries alone, establish the
implemented behavior described in section 3.

### 2.4 Test evidence

The principal evidence is:

- `tests/unit/test_player_character_read.py` for successful projection,
  detachment, exact allowlist, missing/wrong-owner equivalence, authorization
  before UoW construction, validation, and no commit;
- `tests/unit/test_player_character_composition.py` for exact configured
  principal-to-controller resolution, fail-closed configuration, and lazy
  normal composition;
- `tests/integration/test_mysql_player_character_service.py` and
  `tests/integration/test_mysql_player_character.py` for the real repository,
  strict reconstruction, transaction, and current-state behavior;
- `tests/unit/test_api.py` and
  `tests/unit/test_phase_3_0_public_client_contract.py` for principal dependency,
  path validation, sanitized public errors, and OpenAPI conventions;
- `tests/unit/test_run_composition.py`,
  `tests/unit/test_run_operations.py`, and
  `tests/integration/test_mysql_player_character_run_binding.py` for the
  internal-only P4-S1/public-non-activation boundary; and
- `tests/unit/test_demo_composition.py` for the independent Demo composition.

Tests are evidence of committed behavior. They do not create product authority.

### 2.5 Status records and planner inference

`PLANS.md` and the status portions of the listed phase documents are status
records. The exact route, path carrier, public not-found code, conditional route
registration, file inventory, and acceptance-to-test allocation below are
planner decisions made from frozen authority, current conventions, and the
smallest coherent slice. They become implementation authority only after this
exact plan receives independent approval and completes the workflow gate in
section 19.

## 3. Verified current repository state

The current implementation already provides all application and persistence
capability needed for the read:

- `RequestPrincipal` is a strict, frozen trusted-application identity with a
  bounded `player_id` and `authentication_scheme`.
- `ConfiguredControllerBindingResolver` exact-matches the complete
  `(authentication_scheme, player_id)` principal against an immutable
  configured allowlist and returns only its configured `ControllerBindingRef`.
  Unknown or invalid principals receive no controller authority.
- `PlayerCharacterService.get_owned` resolves that authority before creating a
  UoW; revalidates the typed `PlayerCharacterId`; uses
  `uow.player_characters.get`; strictly validates the canonical record; checks
  the stored controller binding; and returns `None` for absent, unknown-
  controller, or wrong-owner access.
- `SqlAlchemyPlayerCharacterRepository.get` is a non-locking current read. It
  strictly reconstructs and cross-validates current state, immutable revision
  history, allocation, controller binding, and successful receipt evidence. A
  missing current row with surviving canonical evidence is an integrity error,
  not ordinary absence.
- `PlayerCharacterSelfProjection` is strict, frozen, detached, and allowlisted.
  It contains exactly Player Character ID, contract version, current record
  revision, and lifecycle.
- The owned read performs no service-level receipt operation, lock, write,
  commit, retry, winner recovery, identity issuance, policy mutation, or Run
  work. Existing repository reconstruction may read immutable receipt evidence
  to validate the record set; that is not a receipt mutation or a separate
  service receipt workflow.
- `build_default_services()` already provides the service as
  `ApiServices.player_character_service` over the shared lazy
  `SqlAlchemyUnitOfWork` factory.
- No HTTP dependency getter, route, public operation, frontend method, or Demo
  Player Character service exists today.

The accepted Player Character public-read capability is therefore present
behind the application boundary but not reachable through HTTP.

## 4. Product and architecture boundary

The P5-S1 data flow is exactly:

```text
GET /v1/player-characters/{player_character_id}
  -> FastAPI path validation
  -> trusted RequestPrincipal dependency
  -> existing normal-composed PlayerCharacterService
  -> configured principal-to-controller resolver
  -> one read-only UnitOfWork
  -> existing PlayerCharacterRepository.get
  -> strict canonical reconstruction and ownership check
  -> existing detached PlayerCharacterSelfProjection
  -> public JSON response
```

This preserves `api/infrastructure -> application -> domain`. FastAPI and HTTP
status choices remain in `api`; controller resolution and ownership stay in the
application service; canonical validation stays in the domain/persistence
authorities; and no infrastructure or ORM object crosses the public boundary.

P5-S1 returns the current accepted canonical projection for every valid
canonical lifecycle (`active`, `retired`, or `deceased`). It does not interpret
retirement or death as absence. A rejected creation or mutation candidate never
becomes canonical and therefore cannot be returned.

## 5. Included scope

P5-S1 includes only:

1. one normal-runtime HTTP GET route for one caller-supplied opaque Player
   Character ID;
2. one API dependency getter for the already composed service;
3. one stable public Player Character not-found classification and mapping;
4. direct serialization of the accepted detached projection;
5. exact OpenAPI declaration for the operation, path parameter, success DTO,
   and public errors;
6. conditional route registration that preserves the independent Demo surface;
7. focused unit, ASGI transport, real-MySQL integration, route-inventory, and
   Demo-non-activation evidence; and
8. the exact documentation synchronization listed in section 15.

## 6. Explicit exclusions and deferred work

P5-S1 does not authorize:

- Player Character creation, replayed creation, mutation, retirement,
  reactivation, final death, continuity return, transfer, deletion, or
  replacement;
- list, search, discovery, count, pagination, batch read, lookup by controller,
  or administrator access;
- public Run creation/read, Player Character binding, Session participation,
  Run resume, or any Run command;
- any transition from `pre_first_turn` to `active`, or any other Run lifecycle
  transition;
- scenario, world, visit, narrative, memory, relationship, NPC, combat,
  content, player-action, or gameplay integration;
- frontend, Web client, browser, or deterministic Demo implementation;
- Provider, prompt, model, live-service, or network integration;
- production account, authentication, authorization-administration, identity
  recovery, token, cookie, header, CORS, abuse-control, rate-limit, quota,
  deployment, or Internet-readiness design;
- profile fields, character declarations, narration preferences,
  `character_development`, continuity internals, applicable Run reference,
  controller binding, authority provenance, receipts, or ORM state in the
  response;
- schema, ORM, Alembic, database-data, dependency, or configuration-format
  changes;
- a new repository, UoW, projection, validation framework, or parallel service;
- reopening P4-S1 or optional P4-S1 cleanup;
- definition of any P4-S2 objective; or
- drafting or changing `DB-001`.

P5-S2, P5-S3, broader Phase 5, broader Phase 4, and the complete Run Protocol
remain separately gated. Completing P5-S1 will not complete any of them.

## 7. Exact public contract decision

### 7.1 Method and route

The sole new operation is:

```http
GET /v1/player-characters/{player_character_id}
```

The route tag is `player-characters`. There is no alternate `/self`, `/owned`,
collection, query-parameter, controller-ID, Session, Run, or body-carried
route. The explicit path ID keeps Player Character identity distinct from the
principal and makes this one-resource read consistent with existing Session
resource routes.

### 7.2 Success representation

Success is HTTP `200` with `response_model=PlayerCharacterSelfProjection`.
There is no transport copy, flattening adapter, ORM serialization, generic
`model_dump(exclude=...)`, or additive profile envelope.

The exact JSON shape is:

```json
{
  "player_character_id": {
    "value": "pc.example"
  },
  "contract_version": "structured-player-character/v1",
  "record_revision": {
    "value": 1
  },
  "lifecycle": "active"
}
```

Only the values vary. The same shape represents `retired` and `deceased`
current records. All four fields are required. No `null` field and no
`response_model_exclude_none` behavior is needed.

This nested typed-value representation is the already accepted and tested
application projection. Changing it to flat strings or adding profile fields
would be a separate reviewed public-contract decision and is outside P5-S1.

## 8. Authentication and ownership decision

The route obtains its principal only through
`Depends(get_current_principal)`. It accepts no principal, player, controller,
ownership, authentication scheme, administrator, or role claim from the path,
query, body, or public DTO.

`PlayerCharacterService.get_owned` remains the ownership authority:

1. the injected trusted principal is passed unchanged;
2. the existing configured resolver exact-matches the complete principal;
3. missing or invalid controller resolution returns no result before UoW
   construction;
4. the existing repository loads and validates the exact target;
5. the service exact-matches the stored `controller_binding`; and
6. only then is the accepted self projection constructed.

No transport check may replace or duplicate that service ownership check. No
controller binding is returned.

The fixed `demo-player` / `demo-dev-only` principal remains the current concrete
default dependency. It is a development identity, not production
authentication. Section 17 records the resulting deployment limitation.

## 9. Identifier carrier and request budgets

`player_character_id` is a path string constrained before service invocation by
a new `PlayerCharacterPathId` alias in `api/main.py`:

- minimum length: 1 character;
- maximum length: 128 characters;
- pattern: `^[A-Za-z0-9][A-Za-z0-9_.:-]*$`.

The handler then constructs `PlayerCharacterId(value=player_character_id)`.
This preserves the domain's exact opaque-reference validation and 128-character
budget. Because the admitted alphabet is ASCII, the carrier is also bounded to
128 UTF-8 bytes. It is not trimmed, case-folded, semantically parsed, or
normalized into another identifier.

The route must not require the production issuer's `pc.<UUIDv4-hex>` shape.
`pc.` is the current issuance convention, while `PlayerCharacterId` is the
governing read-domain validator and also admits already accepted opaque IDs.

The operation declares no request body and no query parameter. Therefore
P5-S1 adds zero body fields and no data-bearing request-payload budget beyond
the bounded path carrier. OpenAPI must contain no `requestBody` for this
operation. Authentication transport and whole-server request-line/body limits
remain outside this slice; P5-S1 must not claim that a route which does not read
a body establishes a new server-wide zero-byte wire limit.

## 10. Non-enumeration and failure semantics

The response contract is exact:

| Condition | HTTP | Public envelope |
| --- | ---: | --- |
| Exact owned, strictly valid canonical current record in any admitted lifecycle | 200 | Exact four-field `PlayerCharacterSelfProjection` |
| Syntactically valid ID with no canonical character and no surviving integrity evidence | 404 | `PLAYER_CHARACTER_NOT_FOUND` / `Player character was not found` |
| Valid character owned by another controller | 404 | The identical `PLAYER_CHARACTER_NOT_FOUND` envelope |
| Unknown, invalid, or unmapped trusted principal/controller resolution | 404 | The identical `PLAYER_CHARACTER_NOT_FOUND` envelope |
| Rejected/uncommitted candidate or otherwise unavailable non-canonical target | 404 | The identical `PLAYER_CHARACTER_NOT_FOUND` envelope when there is no canonical current record |
| Invalid path carrier | 422 | Existing `REQUEST_VALIDATION_FAILED` / `Request validation failed` |
| Corrupt, contradictory, unsupported, or mismatched stored canonical evidence | 500 | Existing sanitized `INTERNAL_SERVER_ERROR` / `Internal server error` |
| Repository, UoW, composition, or unexpected application failure | 500 | The identical sanitized `INTERNAL_SERVER_ERROR` envelope |

The route must not return `401`, `403`, `409`, or a distinct foreign-owner
error under the current concrete boundary:

- there is no production authentication adapter in this slice to define a
  truthful `401` contract;
- authorization failure and absence intentionally collapse to one `404`;
- the read carries no expected revision and has no stale-write conflict; and
- canonical integrity failures remain internal failures rather than being
  mislabeled as ordinary absence.

Response equality, not constant-time execution, is the non-enumeration
guarantee. No timing guarantee is claimed.

The API handler converts only `get_owned(...) is None` to a new
`PlayerCharacterNotFoundError`. The central API exception handler maps that
type to the exact `404` envelope. It must not broadly catch validation,
integrity, repository, UoW, cancellation, or unknown exceptions.

## 11. Application, repository, UoW, and composition design

### 11.1 Application service

Reuse `PlayerCharacterService.get_owned` unchanged. It already has the exact
entry point and semantics P5-S1 requires. P5-S1 must not add an HTTP-aware
method, an alternate owned-read service, a public repository call, a lifecycle
filter, or a projection wrapper.

### 11.2 Repository and Unit of Work

The existing service owns one UoW and invokes only
`uow.player_characters.get(player_character_id)`. The repository performs its
existing strict reconstruction without `FOR UPDATE`. No new repository or UoW
method is needed.

The read performs no write and no explicit `commit()`. Normal UoW exit follows
the existing uncommitted read cleanup path, rolling back any implicit read
transaction and closing the session. P5-S1 must not optimize this by changing
global UoW semantics.

### 11.3 Dependency and route activation

Add `get_player_character_service(request)` in `api/dependencies.py`. It reads
`ApiServices.player_character_service`, returns the existing service when
present, and fails closed with an internal error if an app state is
misconfigured. It does not construct a service or UoW.

The shared `create_app` factory is used by both the normal application and the
independent deterministic Demo. The route-registration rule is therefore:

```text
register P5-S1 route when
  services is None
  OR services.player_character_service is not None
```

Consequences:

- `deviation_protocol.api.main:app`, created with `services=None`, exposes the
  route and resolves the normal service lazily during lifespan;
- a test or injected normal app exposes it only when its supplied
  `ApiServices` contains the Player Character service; and
- the Demo runtime, whose supplied `ApiServices.player_character_service` is
  `None`, does not register or advertise the route.

This conditional registration is the minimal change required to activate the
normal boundary without changing Demo composition, storage, routes, OpenAPI,
or behavior. No Demo service or fake Player Character repository may be added.

## 12. DTO and OpenAPI design

`PlayerCharacterSelfProjection` remains in
`application/player_character_projection.py`, where it already acts as a
strict application/public projection independent of FastAPI and
infrastructure. `api/schemas.py` receives no duplicate response DTO.

For the normal app, OpenAPI must show:

- path `/v1/player-characters/{player_character_id}`;
- method `get`;
- one required string path parameter with the exact 1–128 and pattern
  constraints;
- no request body and no query parameter;
- success `200` referencing `PlayerCharacterSelfProjection`;
- errors `404`, `422`, and `500`, each referencing `ErrorResponse`;
- the safe nested Player Character ID/revision value types and closed
  contract/lifecycle values needed by that public projection; and
- no canonical aggregate, controller binding, authority provenance, receipt,
  repository, UoW, ORM, Run binding, Provider, snapshot, or other internal
  schema.

The Demo app must not show this path. The existing Session public schemas and
the meaning of `PlayerVisibleStateProjection.player_id` and
`character_definition_id` remain unchanged.

## 13. Exact production implementation inventory

The implementation candidate may change exactly four production paths:

| Path | Exact responsibility |
| --- | --- |
| `src/deviation_protocol/application/errors.py` | Add only `PlayerCharacterNotFoundError` with stable code `PLAYER_CHARACTER_NOT_FOUND`; do not create a generic Player Character error hierarchy |
| `src/deviation_protocol/api/errors.py` | Map only `PlayerCharacterNotFoundError` to the exact safe 404 envelope |
| `src/deviation_protocol/api/dependencies.py` | Add the fail-closed getter for the already composed `PlayerCharacterService` |
| `src/deviation_protocol/api/main.py` | Add `PlayerCharacterPathId`, imports, conditional normal-runtime route registration, typed ID construction, `get_owned` delegation, `None`-to-not-found conversion, response model, tags, and exact OpenAPI errors |

No other production path is expected or authorized. In particular, the
following remain unchanged:

- `src/deviation_protocol/application/player_character_service.py`;
- `src/deviation_protocol/application/player_character_projection.py`;
- `src/deviation_protocol/application/ports.py`;
- `src/deviation_protocol/domain/player_character.py`;
- `src/deviation_protocol/infrastructure/player_character_authority.py`;
- `src/deviation_protocol/infrastructure/repositories.py`;
- `src/deviation_protocol/infrastructure/unit_of_work.py`;
- `src/deviation_protocol/infrastructure/orm_models.py`;
- `src/deviation_protocol/api/schemas.py`;
- `src/deviation_protocol/api/demo.py`;
- `src/deviation_protocol/api/demo_composition.py`;
- all Run, narrative, scenario, world, Provider, frontend, and Web paths;
- all Alembic paths; and
- dependency and lock files.

If implementation preflight proves that any fifth production path is required,
implementation stops. The plan must be amended and independently re-reviewed;
an implementer must not select a convenient new location or widen the slice.

## 14. Exact test inventory and allocation

The implementation candidate may change exactly four test paths:

| Path | Change | Exact allocation |
| --- | --- | --- |
| `tests/unit/test_player_character_api.py` | New | ASGI transport success; exact principal and typed-ID forwarding; all lifecycle serialization; exact four-field/key-and-value privacy scan; identical absent/foreign/unmapped 404; invalid 1–128/pattern boundary 422; unknown/internal error sanitization; no body/query authority; dependency fail-closed behavior; exact normal OpenAPI operation and exclusion of internal models |
| `tests/integration/test_mysql_player_character_api.py` | New | Real MySQL current-record read through the public ASGI route and existing service/repository/UoW; owned success after strict reconstruction; absent and foreign-owner identical 404; no revision/current/allocation/binding/receipt write or commit side effect; cleanup of only test-owned rows |
| `tests/unit/test_run_composition.py` | Modify | Update the exact normal public-route inventory to admit only the P5-S1 GET while retaining the assertion that no Run/binding route is public and the reserved binding command stays outside HTTP |
| `tests/unit/test_demo_composition.py` | Modify | Assert that Demo OpenAPI and route inventory do not contain `/v1/player-characters/{player_character_id}` and that no Demo Player Character service/storage is constructed |

No other test path is expected to change. The following committed tests must be
run unchanged as compatibility evidence:

- `tests/unit/test_player_character_read.py`;
- `tests/unit/test_player_character_composition.py`;
- `tests/unit/test_player_character_service.py`;
- `tests/unit/test_api.py`;
- `tests/unit/test_phase_3_0_public_client_contract.py`;
- `tests/unit/test_run_operations.py`;
- `tests/integration/test_mysql_player_character_service.py`; and
- `tests/integration/test_mysql_player_character_run_binding.py`.

Test ownership is exact:

- application unit behavior remains owned by
  `test_player_character_read.py`;
- HTTP transport, DTO, error, identifier, and OpenAPI behavior belongs to the
  new unit API module;
- real persistence-to-public-boundary behavior belongs to the new MySQL API
  module;
- P4-S1 public non-activation belongs to `test_run_composition.py` and the
  unchanged Run operation tests; and
- Demo non-activation belongs to `test_demo_composition.py`.

No browser, Web, live Provider, or public action test belongs to P5-S1.

## 15. Documentation synchronization inventory

Before independent implementation audit, a P5-S1 completion claim, or a request
for commit authorization, the implementation candidate must synchronize
exactly these documentation paths:

| Path | Required synchronization |
| --- | --- |
| `PLANS.md` | Record only the implemented P5-S1 boundary and keep broader Phase 5, Phase 4, and Run Protocol incomplete |
| `docs/architecture.md` | Record the normal public route, existing service flow, conditional Demo exclusion, and development-principal limitation as implemented facts |
| `docs/public_client_contract.md` | Add the exact owned-read route, response, path budget, non-enumeration, errors, and OpenAPI contract without changing Session/action behavior |
| `docs/structured_player_character_contract.md` | Update only implementation-status wording needed to acknowledge P5-S1; do not alter frozen product rules |
| `docs/structured_player_character_implementation_plan.md` | Mark only P5-S1 implemented after evidence and preserve all later slices as deferred/separately gated |
| `docs/structured_player_character_p5_s1_implementation_plan.md` | Record implementation/review evidence and exact completion status without changing the approved scope |

No P4-S1, Run Protocol, minimum Run-core, guardrail, DB-001, Provider, Demo
phase, frontend, or other document is expected to change. A confirmed reusable
defect may trigger the repository's guardrail workflow, but that would be a
separate scope reassessment, not a speculative P5-S1 edit.

## 16. Ordered implementation slices

### P5-S1a — Public read seam and transport contract

1. Reconfirm the approved-plan implementation baseline and exact path budget.
2. Add the narrow application not-found error and central API mapping.
3. Add the service dependency getter.
4. Add conditional normal-runtime route registration and the exact GET handler.
5. Add `tests/unit/test_player_character_api.py`.
6. Update the Run route-inventory regression.

Checkpoint requirements:

- the normal app exposes exactly the one new GET;
- the service and projection remain unchanged;
- missing/foreign/unmapped results share the exact 404;
- invalid identifiers receive the existing 422 envelope;
- no mutation method or Run route is added; and
- no implementation path outside the P5-S1a inventory has changed.

### P5-S1b — Persistence boundary and composition preservation

1. Add the real-MySQL public-read integration module.
2. Add the Demo route-absence regression.
3. Prove no read-side write, explicit commit, identity issuance, receipt
   mutation, Run interaction, or Demo activation.
4. Run the focused compatibility selections.

Checkpoint requirements:

- the real repository returns only a strictly reconstructed accepted record;
- the public response remains detached and allowlisted;
- absent and foreign-owned records remain non-enumerable;
- Demo route and storage behavior remain unchanged; and
- P4-S1 public non-activation remains intact.

### P5-S1c — Documentation, full verification, and review candidate

1. Complete the exact documentation inventory and canonical synchronization
   checklist.
2. Run validation in section 18 in order.
3. Inspect the complete diff and exact inventory.
4. Freeze the candidate for a fresh independent read-only implementation
   review.

No slice authorizes staging, commit, or push.

## 17. Impact and security assessment

| Surface | P5-S1 impact |
| --- | --- |
| Public API | One new normal-runtime authenticated-principal GET and its OpenAPI operation |
| Existing Session/action API | None; paths, DTOs, recovery, meanings, and actions remain unchanged |
| Player Character aggregate | Read only; no lifecycle or revision change |
| Repository/UoW | Reuse existing non-locking read and uncommitted UoW cleanup; no new port or transaction behavior |
| Schema/ORM | None |
| Alembic/migrations | None; current linear head remains unchanged |
| Database data | None outside test-owned integration fixtures, which must be cleaned |
| Dependencies/configuration | None |
| Provider/model/prompt | None; no call or schema |
| Frontend/Web/browser | None |
| Demo | None; route remains unregistered and no service/storage is added |
| Run binding | None; `RunService.bind_player_character_internal` remains internal-only |
| Reserved public binding | Remains rejected through `RunService.bind_player_character(...)` |
| Run lifecycle | None; no `pre_first_turn -> active` or other transition |
| Scenario/world/player action | None |
| Administrator access/listing/search | None |

The endpoint discloses an opaque Player Character ID, contract version, record
revision, and lifecycle only after controller authorization. These are the
already approved controller-self fields. It discloses no authentication
material, internal controller ID, declaration/profile content, continuity
internals, provenance, receipt, Run reference, hidden fact, Provider data,
database detail, or stack trace.

### Production identity limitation

The current `get_current_principal` implementation always returns the fixed
`demo-player` / `demo-dev-only` principal. Dependency override tests prove the
trusted seam, but the repository has no production authentication adapter.
Consequently:

- P5-S1 does not make the normal app safe for Internet deployment;
- a deployment must not treat the fixed principal as user authentication;
- `PLAYER_CHARACTER_CONTROLLER_BINDINGS` and the configured resolver establish
  controller authorization only after a trusted principal exists; they do not
  authenticate a request;
- production authentication, credential/session transport, failure status
  policy, abuse controls, and deployment remain separately owned future work;
  and
- until that work is explicitly authorized and implemented, the existing
  development-only deployment guardrail remains in force.

This limitation does not weaken P5-S1 ownership checks and must be visible in
the synchronized public/architecture documentation.

## 18. Validation matrix and execution order

The later implementation task must use PowerShell 7+ and only
`.\.venv\Scripts\python.exe`. `RUN_LIVE_DEEPSEEK_TEST` remains disabled.

Run these tiers in order:

1. **Inventory and static preflight**
   - confirm the approved baseline and exact changed/untracked inventory;
   - confirm `.venv` is present and usable;
   - inspect every production and test diff;
   - search for unauthorized routes, mutations, bindings, lifecycle
     transitions, Demo/Provider/frontend work, and internal DTO exposure.
2. **Focused unit/transport**

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/unit/test_player_character_api.py tests/unit/test_player_character_read.py tests/unit/test_player_character_composition.py tests/unit/test_player_character_service.py tests/unit/test_api.py tests/unit/test_phase_3_0_public_client_contract.py tests/unit/test_run_composition.py tests/unit/test_run_operations.py tests/unit/test_demo_composition.py
   ```

3. **Focused real MySQL**, only with the repository-approved
   `mysql+asyncmy` `deviation_protocol_test` target:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest tests/integration/test_mysql_player_character_api.py tests/integration/test_mysql_player_character_service.py tests/integration/test_mysql_player_character_run_binding.py
   ```

4. **Canonical Offline verification**

   ```powershell
   .\scripts\verify.ps1 -Mode Offline
   ```

5. **Canonical MySQL verification**

   ```powershell
   .\scripts\verify.ps1 -Mode MySQL
   ```

6. **Canonical Full verification**

   ```powershell
   .\scripts\verify.ps1 -Mode Full
   ```

   This supplies the repository-required full tests, `compileall`, dependency
   check, Alembic heads/history, and Git whitespace validation.
7. **Final targeted metadata and inventory confirmation**

   ```powershell
   .\.venv\Scripts\python.exe -m alembic heads
   .\.venv\Scripts\python.exe -m alembic history
   git diff --check
   git status --short
   ```

The Alembic commands are metadata checks only; P5-S1 runs no migration. Browser,
Web, Demo smoke, live Provider, and live-model verification are not required
because those surfaces do not change.

Every warning, retry, failure, skip relevant to the new surface, and nonzero
exit must be reported. No passing count is predicted by this plan.

## 19. Approval, baseline, and Git gate

The sole operative success verdict for the independent read-only review of this
plan is:

```text
APPROVED
```

Historical Player Character, Run, P4-S1, or documentation verdicts cannot
satisfy this gate. Author-completion, candidate-ready, changes-required,
blocked, example, or differently named tokens are non-operative.

The required order is:

1. freeze the exact one-file plan candidate and record its SHA-256 outside the
   candidate;
2. conduct a fresh independent read-only review of the exact bytes;
3. if any byte changes, invalidate the prior hash/verdict and repeat the review;
4. obtain the exact operative approval verdict;
5. obtain separate authorization to stage and commit only the approved plan;
6. verify staged and committed bytes and inventory;
7. the user performs the push manually;
8. confirm a new clean, remote-aligned implementation baseline; and
9. begin P5-S1 implementation only under separate explicit authorization.

This draft authoring task performs none of steps 2–9. Codex never pushes.

## 20. Acceptance criteria

P5-S1 implementation is acceptable only when all of the following are true:

1. the exact approved baseline and file inventory were preserved;
2. the normal app exposes only
   `GET /v1/player-characters/{player_character_id}`;
3. the path identifier uses the exact safe opaque 1–128 ASCII carrier and is
   revalidated as `PlayerCharacterId`;
4. the principal comes only from the trusted dependency;
5. controller resolution and stored ownership remain in the existing
   application service;
6. absent, foreign-owned, unmapped, and otherwise unavailable non-canonical
   targets return the identical 404 envelope;
7. invalid path input returns the existing public 422 envelope;
8. corrupt/internal failures return only the sanitized 500 envelope;
9. success returns exactly the existing detached four-field projection;
10. no mutable aggregate, ORM row, repository object, UoW, receipt, provenance,
    controller binding, private profile field, or Run reference is exposed;
11. the read performs no lock, write, explicit commit, retry, recovery,
    identity issuance, policy mutation, Run work, or Provider work;
12. OpenAPI exposes only the exact safe operation and DTO/error schemas;
13. the Demo does not register, advertise, or implement the route;
14. no frontend, browser, public action, list/search, admin, create, or mutation
    behavior is introduced;
15. no schema, migration, dependency, configuration-format, or database-data
    change is introduced;
16. the internal P4-S1 binding remains internal-only, the reserved public
    binding command remains rejected, and the Run lifecycle remains
    `pre_first_turn`;
17. all focused and canonical validation passes, with evidence recorded;
18. documentation is synchronized without claiming broader phase completion;
19. a fresh independent implementation review finds no blocking issue;
20. the fixed development principal is still explicitly unsuitable for
    Internet deployment; and
21. nothing is staged, committed, or pushed without its separate exact
    authorization.

## 21. Stop conditions

Stop implementation without widening or repairing scope if:

- the approved implementation baseline, plan bytes/hash, or predecessor status
  is stale;
- P3-S3 `get_owned`, the accepted projection, P3-S4 composition, or P4-S1
  public non-activation no longer matches this plan;
- a public response requires profile fields, a flattened replacement DTO, a Run
  reference, or any authority-bearing/private field;
- ownership cannot remain in the existing service or controller resolution
  cannot occur before UoW construction;
- non-enumeration would require distinguishing absent from foreign ownership;
- a repository/UoW/service/projection/domain change is required;
- Demo exclusion cannot be preserved by the bounded conditional-registration
  rule;
- implementation requires a fifth production path, fifth changed test path, a
  schema/migration/dependency/configuration change, or a document outside the
  exact synchronization inventory;
- production authentication design is required to make an Internet-readiness
  claim;
- public Run binding, a Run lifecycle transition, scenario/world/action
  integration, Provider work, or frontend behavior becomes necessary;
- a material conflict between controlling authorities appears; or
- any required validation fails and cannot be corrected within the exact
  approved boundary.

An ordinary naming or formatting preference is not a stop condition. A material
authority, privacy, ownership, transaction, scope, or evidence conflict is.

## 22. Completion and status synchronization

P5-S1 may be described as implemented only after:

- its approved implementation candidate satisfies every acceptance criterion;
- all required tests and validation pass;
- the canonical documentation-synchronization checklist is complete;
- a fresh independent read-only implementation review accepts the exact
  candidate;
- the implementation and documentation receive separate exact commit
  authorization; and
- status documents record only the capability actually proved.

P5-S1 completion must not say or imply that:

- all of Phase 5 is implemented;
- all of Phase 4 is implemented;
- the full Run Protocol is implemented;
- public Player Character creation or mutation exists;
- public Run binding or `active` lifecycle transition exists;
- frontend or Demo parity exists; or
- production authentication or Internet deployment is ready.

P4-S1 remains closed. No P4-S2 objective is defined. `DB-001` remains
unchanged. Guardrail impact for this plan draft: **None**.

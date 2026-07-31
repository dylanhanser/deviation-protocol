# Structured Player Character P5-S2 Implementation Plan

## 1. Status, purpose, and approval gate

This document is the implementation authority for **P5-S2 — thin
authenticated Player Character creation/replay API activation**. Its bounded
candidate adds one normal-application `POST /v1/player-characters` route.

The controlling public wire contract is
[Public Client Contract](public_client_contract.md), frozen and published by
`245caff3903666fcd2dd9a318785f323117deb24`
(`docs(player-character): define P5-S2 public contract`). The implementation
must reproduce that contract mechanically. It may not reinterpret or improve
the accepted wire decisions.

P5-S1 is completed and published by
`5955c47eac07429107b93ef85da6a055bd2044ef`
(`feat(player-character): activate owned-read API`). Its authenticated owned
`GET /v1/player-characters/{player_character_id}` remains preserved. P5-S2
implementation and its assigned local verification are complete in the current
unstaged working-tree candidate. Its fresh independent read-only review,
separate staging and commit authorization, commit, and publication remain
pending. P5-S3 remains deferred.

This plan's historical approval evidence is:

`STRUCTURED_PLAYER_CHARACTER_P5_S2_PLAN_APPROVED`

That verdict approved only the complete historical three-document planning
candidate and its reviewed SHA-256 identities. It is non-operative for final
review of the current implementation candidate and does not approve
implementation, staging, commit, push, publication, activation, release, or
deployment.

The sole operative successful verdict for the final P5-S2 implementation
review is:

`STRUCTURED_PLAYER_CHARACTER_P5_S2_REVIEW_APPROVED`

The current implementation candidate is not independently approved. Only a
fresh independent exact-candidate review that returns the operative verdict
above can approve it; implementation and local verification, documentation
synchronization, review, approval, staging, commit, and publication remain
distinct states.

The published
[Parsing-Design Authority Amendment](structured_player_character_p5_s2_parsing_design_authority_amendment.md)
is controlling authority only for its narrow raw-body JSON-mode parsing,
direct-binding, and descriptive OpenAPI-schema scope. Its approval does not
approve the P5-S2 implementation candidate or any other plan requirement.

The required sequence is:

1. freeze the exact complete implementation candidate and record all hashes;
2. conduct a fresh independent final read-only implementation review whose
   successful branch can
   return the exact operative verdict above;
3. obtain that exact verdict;
4. obtain separate authorization for the exact staging and local commit
   operation;
5. verify staged and committed bytes and scope;
6. have the user push;
7. confirm the new clean, aligned, published baseline.

## 2. Evidence classification

| Classification | Evidence and consequence |
| --- | --- |
| Frozen authority | The complete [Public Client Contract](public_client_contract.md) at `245caff3903666fcd2dd9a318785f323117deb24` controls every P5-S2 wire decision. [Structured Player Character Contract](structured_player_character_contract.md), [Architecture](architecture.md), [engineering guardrails](engineering/guardrails.md), and [Codex workflow](engineering/codex_workflow.md) continue to control domain, authority, persistence, verification, and handoff boundaries. |
| Implemented prerequisite | P3-S1 creation/replay and its bounded race recovery were completed at `7606e51523338247ea33ed9329346fdba046d29b`; P3-S2 through P3-S4 completed with Phase 3 at `cafb12272e703e8751c78bb6852cec90d7d7ec8d`. `PlayerCharacterService.create`, strict command models, operation identity, fingerprinting, receipts, stored-result reconstruction, controller resolution, UUID issuance, repositories, and Unit of Work behavior already exist. |
| Currently activated behavior | P5-S1 at `5955c47eac07429107b93ef85da6a055bd2044ef` activates the authenticated owned GET route in the normal application. The Demo composition omits the Player Character service and routes. |
| Current implementation candidate | P5-S2 adds exactly one normal-application POST route that parses the frozen transport contract, invokes `PlayerCharacterService.create` once, translates its result or decision, and returns `PlayerCharacterSelfProjection`. Its assigned unit, composition, Demo, and real-MySQL API evidence is complete; independent review and commit remain pending. |
| Deferred implementation | P5-S3 and later phases remain deferred. Demo/frontend creation, public Run behavior, production authentication, and Internet deployment remain unimplemented. |
| Planner inference | The frozen contract requires exact repeated-header detection and an `application/json` boundary but does not name a framework helper. Repository dependencies provide FastAPI/Starlette `Request.scope["headers"]`; P5-S2 will use those raw ASGI header occurrences plus one documented FastAPI `Header` parameter. This is the narrow existing-framework seam that enforces the accepted contract without a DTO, dependency, or idempotency redesign. |

Git history is status evidence, not a substitute for the frozen contract.
Existing source and tests are implementation evidence, not authority to alter
the public wire contract.

## 3. Slice identity, objective, and prerequisites

P5-S2's exact objective is:

> Activate one thin authenticated `POST /v1/player-characters` creation/replay
> route in the normal application, exposing the frozen public
> `CharacterCreationCommand` request and `PlayerCharacterSelfProjection`
> response while delegating all controller ownership, operation namespace,
> fingerprint, receipt, replay, race recovery, persistence, and transaction
> behavior to the completed application service.

The prerequisite relationship is exact:

- P3-S1 owns `PlayerCharacterService.create`, controller-first authorization,
  `player-character.create/v1`, request fingerprinting, successful creation
  receipts, exact replay, idempotency conflict, server UUID allocation,
  initial record creation, ownership, atomic commit, and the one admitted
  binding-add uniqueness-race recovery.
- P3-S4 owns the normal application's canonical service composition:
  `ConfiguredControllerBindingResolver`, `Uuid4PlayerCharacterIdIssuer`,
  `CreatePlayerCharacterPolicy`, `SqlAlchemyUnitOfWork`, and existing
  repositories.
- P5-S1 owns the reusable public seams:
  `get_current_principal`, `get_player_character_service`, normal-versus-Demo
  route registration, `PlayerCharacterSelfProjection`, `ErrorResponse`,
  sanitized exception handlers, `_public_error_responses`, and OpenAPI
  construction.
- The frozen public contract owns all P5-S2 route, header, body, response,
  error, warning, and non-activation decisions.

P5-S2 does not create a second workflow. The service call is the only
application operation.

## 4. Scope and preservation boundary

### 4.1 Included

- one normal-application `POST /v1/player-characters` route;
- direct raw-body JSON-mode validation of `CharacterCreationCommand`;
- exact `Idempotency-Key` transport enforcement and construction of
  `PlayerCharacterOperationId`;
- reuse of the P5-S1 principal and service dependencies;
- exact translation of creation service results and protocol decisions;
- the existing sanitized public error envelope;
- the frozen OpenAPI declaration;
- focused unit, composition, Demo-regression, and MySQL API evidence; and
- canonical documentation synchronization after implementation.

### 4.2 Excluded

P5-S2 does not authorize:

- modification of the frozen public contract;
- another creation service, DTO, idempotency protocol, operation identifier,
  receipt, fingerprint, ownership model, controller resolver, ID issuer,
  repository, Unit of Work, composition root, or development principal;
- client-supplied controller identity or any public controller-binding value;
- listing, search, update, deletion, administration, binding, mutation, or
  action routes;
- P5-S3 controller-mutation activation;
- a P4-S2 objective;
- schema, migration, persistence, transaction, or dependency changes;
- generic retry, ID-collision retry, or recovery after commit failure or
  uncertain durability;
- production authentication, a credential mechanism, 401 challenge, 403
  ownership response, or OpenAPI security scheme;
- frontend or Demo integration;
- Run lifecycle or Run Protocol expansion;
- Session, scenario, world, Provider, narrative, NPC, memory, relationship,
  combat, content, or broader gameplay behavior; or
- speculative Phase 6 or Phase 7 work.

DB-001 remains unchanged. MySQL 8, `AsyncSession`, `asyncmy`, repository
`flush()` behavior, and application-owned Unit of Work commit boundaries remain
authoritative.

## 5. Exact closed future implementation path budget

The current implementation candidate changes exactly the paths in sections
5.1 through 5.3. A need for any additional path stops implementation and
requires a corrected, independently reviewed plan before work continues.

### 5.1 Production path

| Action | Exact path | Exact symbols or sections | Necessity and why existing code alone is insufficient |
| --- | --- | --- | --- |
| Modify | `src/deviation_protocol/api/main.py` | Add `_PLAYER_CHARACTER_IDEMPOTENCY_KEY_PATTERN`, `PlayerCharacterIdempotencyKeyHeader`, `_raw_header_values`, `_request_validation_failure`, `_validate_player_character_creation_transport`, `_project_creation_success`, `_translate_creation_decision`, and route function `create_player_character`; extend the existing Player Character route-registration block, its imports, and the route decorator's `response_description` | P3/P5-S1 already provide every application, dependency, projection, error, composition, and OpenAPI seam, but no POST route currently parses the required header/body, calls `PlayerCharacterService.create`, translates its result, or registers the frozen OpenAPI operation. Keeping all transport-only work beside the P5-S1 route avoids a parallel abstraction. |

No production file is created. No other production file is modified.
`api/dependencies.py`, `api/errors.py`, `api/schemas.py`,
`application/errors.py`, `application/player_character_service.py`,
`application/player_character_operations.py`, domain modules, infrastructure
modules, and migrations remain byte-for-byte unchanged.

### 5.2 Test paths

| Action | Exact path | Exact symbols or sections | Necessity and why existing tests alone are insufficient |
| --- | --- | --- | --- |
| Modify | `tests/unit/test_player_character_api.py` | Extend the existing P5-S1 API fake/service setup; add POST request helpers and P5-S2 transport, result, decision, failure, cancellation, and OpenAPI tests while retaining every owned-read assertion | Existing tests prove only the GET boundary. This path is the established in-process API and OpenAPI seam for exact route behavior and sanitized envelopes. |
| Modify | `tests/integration/test_mysql_player_character_api.py` | Extend the existing real-service API fixture and family-count helpers; add first-create, replay, conflict, distinct-key, ownership, durable-reload, rollback/failure, and current-state GET tests | Unit fakes cannot prove that the HTTP route reuses the real creation receipt, allocation, record, controller-binding, and Unit of Work behavior or that replay performs no second durable write. |
| Modify | `tests/unit/test_run_composition.py` | Replace the P5-S1 path-only route inventory assertion with an exact public `(path, methods)` inventory that admits POST and GET only on their accepted Player Character paths and continues to exclude Run routes | POST shares the `/v1/player-characters` family, and the current path-only inventory cannot prove exact method activation or the continued absence of Run activation. |
| Modify | `tests/unit/test_demo_composition.py` | Rename and extend `test_demo_composition_does_not_register_player_character_read` to assert absence of both the owned GET and creation POST from route methods and Demo OpenAPI | The current regression protects only the P5-S1 GET. P5-S2 must remain absent when `ApiServices.player_character_service is None`. |

No test file is created. No other test file is modified. Existing domain,
operation, service, repository, persistence, composition, MySQL service, and
migration tests remain unchanged regression evidence and are run in the
validation sequence.

### 5.3 Documentation synchronization paths

| Action | Exact path | Exact synchronization |
| --- | --- | --- |
| Modify | `PLANS.md` | Mark P5-S2 implemented only after code and all required verification pass; preserve P4-S1 closed, no P4-S2, P5-S1 completed, P5-S3 deferred, and DB-001. |
| Modify | `docs/architecture.md` | Add only the activated POST boundary and its continued development-authentication/Internet-deployment limits to the current runtime inventory. |
| Modify | `docs/structured_player_character_contract.md` | Synchronize implementation status without changing domain authority, P3 behavior, ownership, replay, persistence, or Phase 4 boundaries. |
| Modify | `docs/structured_player_character_implementation_plan.md` | Mark P5-S2 implemented with exact implementation and verification evidence while preserving historical phases and deferred work. |
| Modify | `docs/structured_player_character_p5_s2_implementation_plan.md` | Record completed implementation paths, exact validation evidence, review status, and remaining non-activation boundaries. |

The frozen `docs/public_client_contract.md` is not in the later change budget:
its accepted wire decisions and its history-based status language require no
implementation edit. Guardrails are not in the budget because no confirmed
defect created or changed a reusable rule. If implementation confirms such a
defect, stop; do not expand this budget silently.

## 6. Exact production symbols and responsibilities

All new symbols live in `src/deviation_protocol/api/main.py`.

### 6.1 `_PLAYER_CHARACTER_IDEMPOTENCY_KEY_PATTERN`

This compiled full-match expression is exactly:

`^[A-Za-z0-9][A-Za-z0-9_.:-]*$`

It exists only to perform the raw accepted-value check. It does not define an
operation namespace, equivalence rule, normalization, or authorization rule.

### 6.2 `PlayerCharacterIdempotencyKeyHeader`

This `Annotated[str, Header(...)]` alias declares:

- alias `Idempotency-Key`;
- required parameter status through a non-default route parameter;
- `min_length=1`;
- `max_length=128`; and
- the exact pattern above.

It is the OpenAPI parameter seam and a first framework validation layer.
The raw-header helper remains authoritative for occurrence count and ASCII
preservation.

### 6.3 `_raw_header_values`

This helper reads `request.scope["headers"]`, compares lower-cased raw byte
names to an exact lower-case byte name, and returns the matching raw values in
transport order. It performs no joining, comma splitting, trimming, decoding,
case folding of values, or Unicode normalization.

### 6.4 `_request_validation_failure`

This helper raises `fastapi.exceptions.RequestValidationError` with no public
field details. The already installed `request_validation_handler` converts it
to the exact frozen 422 `ErrorResponse`.

### 6.5 `_validate_player_character_creation_transport`

This helper:

1. requires exactly one raw `Content-Type` occurrence, decodes it as ASCII,
   takes the bytes before the first semicolon, strips only HTTP optional
   whitespace (`SP` and `HTAB`) from that media-type token, and compares its
   ASCII-lowercased value to `application/json`; the parameter suffix after the
   first semicolon is not interpreted and therefore does not alter the
   media-type token;
2. requires exactly one raw `Idempotency-Key` occurrence;
3. decodes that raw value as ASCII and rejects any decoding failure;
4. enforces 1–128 raw bytes;
5. full-matches the frozen alphabet;
6. verifies that the raw decoded value equals the FastAPI header parameter,
   preventing framework coalescing from changing the accepted value; and
7. constructs `PlayerCharacterOperationId(value=raw_value)` and returns it.

Any failure raises the standard sanitized request-validation failure before
the service is called. The helper never strips, lowercases, Unicode-normalizes,
percent-decodes, semantically parses, or otherwise changes the key.

Requiring an unambiguous JSON media-type occurrence is the mechanical
enforcement of the frozen `application/json` contract. Its failure maps to 422
because the frozen P5-S2 response budget contains request validation rather
than a 400 or 415 response.

### 6.6 `_project_creation_success`

This helper constructs `PlayerCharacterSelfProjection` field by field:

| `CreationSuccessResult` source | Public projection field |
| --- | --- |
| `player_character_id` | `player_character_id` |
| `contract_version` | `contract_version` |
| `resulting_revision` | `record_revision` |
| `resulting_lifecycle` | `lifecycle` |

It omits `result_schema_version`. It has no replay argument and no access to
receipt, fingerprint, controller, persistence, or transaction state.

### 6.7 `_translate_creation_decision`

This helper first requires
`decision.operation_namespace is CharacterOperationNamespace.CREATE_V1`.
It then translates:

- `AUTHORIZATION_FAILED` to
  `PlayerCharacterNotFoundError("player-character.create")`;
- `IDEMPOTENCY_CONFLICT` to
  `IdempotencyConflictError("player-character.create")`; and
- `STORED_RECEIPT_INTEGRITY_FAILURE` to a fixed internal `RuntimeError`.

Every other returned protocol code is an impossible P5-S2 service result and
raises the same fixed internal `RuntimeError`. `READY_FOR_NEW_OPERATION` and
`EXACT_REPLAY` are consumed inside `PlayerCharacterService.create`; mutation
codes cannot be accepted on the creation route. No stored result, operation
key, decision detail, or internal exception text enters the raised message.

### 6.8 `create_player_character`

This route function is the sole new public operation. It accepts `Request`,
`PlayerCharacterIdempotencyKeyHeader`,
`RequestPrincipal = Depends(get_current_principal)`, and
`PlayerCharacterService = Depends(get_player_character_service)`. It validates
the transport, reads the raw body exactly once, validates it through
`CharacterCreationCommand.model_validate_json`, calls the service exactly once, projects
`CreationSuccessResult`, and otherwise invokes the decision translator.

Its route decorator uses
`response_description="Player Character created or exactly replayed."` to
control the OpenAPI 200 response description.

It does not catch `BaseException`, open a Unit of Work, access a repository,
resolve a controller binding, compute a fingerprint, inspect a receipt,
allocate an identifier, inspect a database exception, retry, or determine
whether success was a first creation or replay.

## 7. Route and transport flow

The mechanical request flow is:

1. `create_app` registers `POST /v1/player-characters` inside the same
   `if services is None or services.player_character_service is not None`
   block that owns the P5-S1 GET route.
2. FastAPI resolves the trusted dependencies and declared header string; it
   does not bind `CharacterCreationCommand` as a route parameter.
3. `_validate_player_character_creation_transport` enforces the exact raw
   content-type and idempotency-header contract and constructs
   `PlayerCharacterOperationId`.
4. The route reads the raw body exactly once and validates the strict command
   graph with `CharacterCreationCommand.model_validate_json`.
5. `get_current_principal` supplies the fixed development principal. No body,
   header, query, or path value supplies authority.
6. `get_player_character_service` retrieves the already composed canonical
   service and fails closed if it is absent.
7. The route invokes exactly:

   ```python
   await service.create(
       principal,
       operation_id=operation_id,
       command=command,
   )
   ```

8. A `CreationSuccessResult` is mapped field by field to
   `PlayerCharacterSelfProjection` and returned.
9. A `CharacterOperationProtocolDecision` is translated through the fixed
   decision mapping.
10. Existing exception handlers produce the fixed public envelope.

The decorator declares `status_code=status.HTTP_200_OK`,
`response_model=PlayerCharacterSelfProjection`,
`response_description="Player Character created or exactly replayed."`,
`operation_id="create_player_character"`,
`summary="Create or replay a Player Character"`,
`tags=["player-characters"]`, and
`responses=_public_error_responses(404, 409, 422, 500)`.

No explicit `Response` is constructed. FastAPI serializes the projection as
`application/json`; no `Location` header or replay metadata is added.

## 8. Authentication, controller identity, ownership, and non-enumeration

The existing dependency `get_current_principal` is reused without
modification. It delegates to `get_demo_dev_principal`, which returns the
development-only `RequestPrincipal(authentication_scheme="demo-dev-only",
player_id="demo-player")`.

The principal enters the workflow only as the first positional argument to
`PlayerCharacterService.create`. The service's existing
`controller_binding_resolver.resolve(principal)` remains the authoritative
controller-resolution boundary. The normal service uses
`ConfiguredControllerBindingResolver`, which exact-matches the complete
`(authentication_scheme, player_id)` pair and returns a private
`ControllerBindingRef` or `None`.

Controller identity is absent from:

- the route path;
- query parameters;
- `Idempotency-Key`;
- `CharacterCreationCommand`;
- `PlayerCharacterSelfProjection`; and
- every public error body.

Unknown query values are ignored as non-authoritative transport noise and do
not enter the command or service call. Unknown body fields are rejected.

Non-enumeration is preserved because unresolved principal authority, malformed
resolved authority, stored binding mismatch, and changed or missing recovery
authority all become the same `AUTHORIZATION_FAILED` decision and the same
fixed 404 envelope. The API does not reveal whether a binding, operation key,
receipt, or durable character exists.

P5-S2 adds no 401 challenge, 403 response, credential parser, production
authentication, security scheme, or user-selectable development identity.
OpenAPI explicitly warns that authentication is development-only and Internet
deployment remains unsupported.

## 9. Exact `Idempotency-Key` implementation

Each frozen requirement maps to one implementation action:

| Frozen requirement | Exact action |
| --- | --- |
| Header name matching is case-insensitive | Compare raw ASGI header names after byte-wise lowercasing to `b"idempotency-key"`; declare OpenAPI alias `Idempotency-Key`. |
| Exactly one occurrence | Count raw occurrences; any count other than one raises request validation. |
| Required | The non-default FastAPI header parameter rejects absence; the raw count check independently requires one occurrence. |
| ASCII | Decode the sole raw value with the ASCII codec; reject decoding failure. |
| 1–128 characters/bytes | Enforce raw byte length 1–128 and declare matching OpenAPI lengths. |
| Exact alphabet | Full-match `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` and declare the same OpenAPI pattern. |
| Opaque, case-sensitive | Preserve the decoded bytes exactly; `"Key"` and `"key"` construct distinct values. |
| No normalization | Perform no trim, case fold, Unicode normalization, percent decoding, token parsing, or semantic interpretation. |
| Sole public operation identity | Construct exactly one `PlayerCharacterOperationId`; no body or query fallback exists. |
| Internal namespace | Pass the ID to `PlayerCharacterService.create`; its existing `CreationReceiptKey` and fingerprint protocol fix `CharacterOperationNamespace.CREATE_V1`, value `player-character.create/v1`. |
| Not authorization | Pass the key only as `operation_id`; pass the separately derived principal as the authority argument. |
| Replay and conflict application-owned | Do not query receipts or compare requests in the API; translate only the service's final result or decision. |

The API neither logs nor returns the accepted key. A key reused by another
controller is scoped by that controller's private binding in the existing
receipt key and does not grant access.

## 10. Request model and validation

The route obtains the existing
`deviation_protocol.application.player_character_operations.CharacterCreationCommand`
only through one raw-body `model_validate_json` call. No public DTO or mapping
copy is added.

The exact graph is:

- `CharacterCreationCommand`
  - `contract_version: PlayerCharacterContractVersion`;
  - `character_core: CharacterCore`;
  - `narration_preferences: NarrationPreferences`.
- `CharacterCore`
  - `name_or_code_name`;
  - `preferred_form_of_address`;
  - `adult_identity_and_gender_expression`;
  - `broad_adult_age_presentation`;
  - `broad_appearance_direction`;
  - `distinguishing_features`;
  - `outward_presentation`;
  - `inward_tendency`;
  - `reality_anchor`; and
  - `custom_values`.
- `NarrationPreferences`
  - `internal_thoughts`.

Each declaration uses the existing strict `Declaration` graph with states
`omitted`, `explicitly-absent`, `declared`, and
`intentionally-undecided`. Only `declared` carries a non-null typed value; all
other states require `value` to be null or omitted. Existing nested types
remain `PlayerDeclaredText`, `AdultAgePresentation`,
`DistinguishingFeatures`, `CustomValues`/`CustomValueEntry`, and
`PlayerNarrationPreference`.

The direct graph preserves these exact leaf decisions:

- `contract_version` is exactly `structured-player-character/v1`;
- `PlayerDeclaredText.authority` is exactly `player-expression` or
  `player-confirmation`;
- `PlayerDeclaredText.text` is non-empty valid Unicode, is NFC-normalized,
  forbids NUL, and has no trimming, case-folding, or field-specific length
  limit;
- `AdultAgePresentation.adult_only` is the literal `true`;
- `DistinguishingFeatures.features` is an ordered array that may be empty,
  rejects duplicate `(authority, NFC text)` entries, and has no item-count
  limit outside the aggregate declaration envelope;
- `CustomValues.entries` is an ordered array that may be empty and has no
  item-count limit outside the aggregate declaration envelope;
- each `CustomValueEntry.key` is non-empty valid Unicode, NFC-normalized,
  NUL-free, untrimmed, and unique after normalization;
- each `CustomValueEntry.declaration` is a required declaration of
  `PlayerDeclaredText`; and
- `PlayerNarrationPreference.authority` uses the same two player-authority
  values, while its value is exactly `high-immersion`, `balanced`, or
  `high-agency`, with no selected default or case normalization.

The validation boundary is exact:

1. The route reads the required JSON body once after transport validation.
2. Pydantic JSON-mode validates the strict frozen
   `CharacterCreationCommand` graph.
3. `extra="forbid"` rejects unknown fields at every model level.
4. Required top-level fields reject omission and null. Defaulted declaration
   slots preserve omission as the domain's `omitted` state; explicit null is
   not a substitute for a declaration object.
5. Existing validators enforce exact enums, conditional declaration values,
   adult-only presentation, NFC text behavior, non-empty/no-NUL Unicode,
   duplicate distinguishing-feature rejection, unique NFC custom keys, and
   the fixed narration preference vocabulary.
6. `CharacterCreationCommand.validate_declaration_envelope` calls
   `canonical_player_declaration_bytes` over the fully materialized
   `character_core` and `narration_preferences`; the canonical NFC UTF-8 JSON
   envelope must be at most 65,536 bytes.
7. The service and creation policy retain defensive complete-instance
   revalidation. They do not replace the public validation boundary.

Every validation failure attributable to the submitted public body is
completed before `PlayerCharacterService.create`, so it becomes the fixed
sanitized 422 response and opens no creation Unit of Work. A defensive
validation or integrity failure arising after an already accepted command is
an internal failure and remains 500; storage-integrity `ValueError` subclasses
must never be broadly translated to 422.

No public model contains controller identity, operation namespace, internal
operation ID, receipt, fingerprint, allocation, provenance, Unit of Work,
transaction, persistence, recovery, or lifecycle-command metadata.

## 11. Success and replay response

For both first success and exact replay:

- status is `200 OK`;
- media type is `application/json`;
- body schema is exactly `PlayerCharacterSelfProjection`;
- body fields are `player_character_id`, `contract_version`,
  `record_revision`, and `lifecycle`;
- no replay indicator exists; and
- no `Location` header exists.

The route cannot distinguish the cases. `PlayerCharacterService.create`
returns `CreationSuccessResult` for both. On exact replay, the service returns
the stored receipt's original `CreationSuccessResult` without allocation,
policy, initial-state write, receipt creation, or commit. The API maps that
stored result in the same function used for first success.

The public body omits `result_schema_version`, receipt identity, request
fingerprint, controller binding, ownership evidence, authority provenance,
recovery state, transaction state, and persistence details.

If later mutations have advanced the record, creation replay still returns the
stored original revision-one creation result. Clients use the completed P5-S1
owned GET route for the current state.

## 12. Complete error and cancellation mapping

All public envelopes contain only `error.error_code` and `error.message`.
Field-level details are prohibited in every row.

| Condition | Actual source or failure boundary | Translation location | HTTP, code, message | Non-enumeration and internal preservation |
| --- | --- | --- | --- | --- |
| Malformed JSON; missing/null/wrong-type body; unknown field; unsupported version; invalid nested declaration; duplicate declaration item; invalid Unicode/NUL; canonical envelope over 65,536 bytes; other submitted-body creation/domain validation | The route's raw-body `CharacterCreationCommand.model_validate_json` boundary | Existing `request_validation_handler` | 422, `REQUEST_VALIDATION_FAILED`, `Request validation failed` | No field details; service is not called and no internal validator text is returned. |
| Missing, empty, duplicate, non-ASCII, overlength, invalid-alphabet, normalized-only, or otherwise invalid `Idempotency-Key`; missing or ambiguous non-JSON media type | FastAPI header validation plus `_validate_player_character_creation_transport` | `_request_validation_failure` then existing request-validation handler | 422, `REQUEST_VALIDATION_FAILED`, `Request validation failed` | No operation key, receipt lookup, authority inference, or raw submitted value is disclosed. |
| Principal cannot resolve; resolved controller is invalid; stored binding authorization fails; race recovery authority changes/disappears or cannot be relocked | `PlayerCharacterService.create` returns `AUTHORIZATION_FAILED` | `_translate_creation_decision` raises existing `PlayerCharacterNotFoundError`; existing handler serializes | 404, `PLAYER_CHARACTER_NOT_FOUND`, `Player character was not found` | One identical envelope reveals no principal, binding, receipt, key, or character existence. |
| Same authorized controller scope and operation ID with non-equivalent command | Service receipt protocol returns `IDEMPOTENCY_CONFLICT` | `_translate_creation_decision` raises existing `IdempotencyConflictError`; existing handler serializes | 409, `IDEMPOTENCY_CONFLICT`, `Idempotency key was reused` | Stored result and fingerprint remain absent; the exception receives only a static internal operation label. |
| `STORED_RECEIPT_INTEGRITY_FAILURE`, corrupt receipt/result, contradictory binding, or missing winner evidence | Service protocol decision or repository/persistence integrity exception | Decision translator raises a fixed internal error, or original exception reaches existing `unknown_handler` | 500, `INTERNAL_SERVER_ERROR`, `Internal server error` | Receipt, result, fingerprint, binding, and recovery details remain private. The original exception object and chaining remain internal until the public handler. |
| Allocation collision; initial record or receipt conflict; unsupported uniqueness conflict; persistence read/write failure; exact race recovery failure; ID issuer, clock, policy, or Unit of Work failure | Existing service, repositories, issuer, policy, and Unit of Work | No route catch; existing `unknown_handler` | 500, `INTERNAL_SERVER_ERROR`, `Internal server error` | No generic retry, SQL, constraint, database identity, submitted values, or internal exception text is exposed. |
| Commit failure or uncertain durability | Existing `uow.commit()` propagates the original exception; service performs no recovery reread | No route catch; existing `unknown_handler` | 500, `INTERNAL_SERVER_ERROR`, `Internal server error` | No success/replay claim or exactly-once claim; original exception identity is preserved internally. |
| Unexpected application, dependency, composition, projection, namespace, or impossible decision failure | Existing dependency/route/helper boundary | Existing unknown handler, with fixed internal helper errors for impossible decisions | 500, `INTERNAL_SERVER_ERROR`, `Internal server error` | Handler logs only exception type; no stack trace, path, transaction, or exception message enters the response. |
| Cancellation | `asyncio.CancelledError` or another cancellation `BaseException` from dependency, service, repository, Unit of Work, or response path | No translation | No promised HTTP response | Route and current `@app.exception_handler(Exception)` do not catch `BaseException`; the original cancellation propagates. |

The API does not expose SQL, constraint details, database identity,
controller-binding existence, receipt existence, fingerprints, submitted
sensitive values, stack traces, internal exception text, transaction state, or
race-recovery details.

## 13. Dependency and composition reuse

P5-S2 reuses, without modification:

- `get_current_principal`;
- `get_demo_dev_principal`;
- `get_player_character_service`;
- `ApiServices.player_character_service`;
- `build_player_character_service`;
- `build_default_services`;
- `ConfiguredControllerBindingResolver`;
- `Uuid4PlayerCharacterIdIssuer`;
- `CreatePlayerCharacterPolicy`;
- the shared lazy `SqlAlchemyUnitOfWork` factory;
- `SqlAlchemyControllerBindingRegistryRepository`;
- `SqlAlchemyPlayerCharacterRepository`;
- `SqlAlchemyPlayerCharacterCreationReceiptRepository`;
- `PlayerCharacterService.create`;
- `PlayerCharacterNotFoundError`;
- `IdempotencyConflictError`;
- `ErrorResponse`;
- `install_exception_handlers`;
- `_public_error_responses`;
- `create_app`; and
- FastAPI's existing OpenAPI construction.

No dependency function changes. No new dependency function exists.
The route receives the same service instance composed for P5-S1 and Run
internal binding evidence. Composition remains lazy: route registration opens
no connection, Unit of Work, SQL session, or Provider.

## 14. Runtime activation and non-activation boundary

In the current implementation candidate:

- normal `deviation_protocol.api.main:app` exposes POST creation/replay and the
  existing owned GET;
- `create_app()` with normal dependency composition exposes both operations;
- `create_app(services=...)` exposes the routes only when
  `services.player_character_service` is not `None`;
- Demo composition continues to supply `None` and exposes neither operation;
- P5-S1 GET behavior and error/OpenAPI contracts remain unchanged;
- no frontend method or UI calls the new route;
- no Run route is registered;
- no P5-S3 mutation route is registered; and
- no other route inventory changes.

This is two narrow Player Character operations, not general Player Character
API activation. Development authentication remains fixed and non-production.
Internet deployment remains unsupported.

## 15. OpenAPI implementation

The current route decorator and descriptive-only OpenAPI schema mechanism
generate exactly:

| Property | Exact declaration |
| --- | --- |
| Path and method | `POST /v1/player-characters` |
| `operationId` | `create_player_character` |
| Tag | `player-characters` |
| Summary | `Create or replay a Player Character` |
| Header | One required `Idempotency-Key` string parameter with `minLength: 1`, `maxLength: 128`, and pattern `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` |
| Request body | Required `application/json` referencing `CharacterCreationCommand` |
| Success | `200` `application/json` referencing `PlayerCharacterSelfProjection`, with description `Player Character created or exactly replayed.` supplied by the route decorator's `response_description` argument |
| Errors | `404`, `409`, `422`, and `500`, each `application/json` referencing `ErrorResponse` |
| Security | No production security scheme |

The operation description states all six frozen facts:

1. controller identity is derived only from the trusted server-side principal;
2. `Idempotency-Key` is required and is not authorization;
3. first success and exact replay share HTTP 200 and body semantics;
4. replay returns the original creation result and the owned GET supplies
   current state;
5. controller binding, receipt, fingerprint, provenance, Run, persistence,
   transaction, and recovery internals are never exposed; and
6. authentication is development-only, production authentication is absent,
   and Internet deployment is unsupported.

Explicit `responses=_public_error_responses(404, 409, 422, 500)` prevents
FastAPI's generated validation response schema from advertising its internal
detail body. The transport helper maps invalid media type to the accepted 422
rather than introducing 400 or 415. The route declares 200, so no 201 is
generated. The selected and only success-description seam is the route
decorator's `response_description` argument, not an explicit `responses[200]`
description or another mechanism. The exact route/method inventory test detects
any unsupported operation. FastAPI's handling of requests to a different
trailing-slash path is outside the declared contract and does not add an OpenAPI
operation.

Internal schemas excluded from the public operation include
`ControllerBindingRef`, `PlayerCharacterOperationId`,
`CharacterOperationFingerprint`, `CreationReceiptKey`,
`StoredCreationSuccessReceipt`, `CreationSuccessResult`,
`CharacterOperationProtocolDecision`, persistence rows, and Unit of Work
types.

## 16. Exact test matrix and allocation

### 16.1 `tests/unit/test_player_character_api.py`

The existing `_FakePlayerCharacterService` is extended with a `create` method,
recorded principal/operation/command calls, configurable result or raised
`BaseException`, and no persistence behavior. Existing GET behavior stays
intact.

This path adds exact evidence for:

1. first success returns 200, `application/json`, exact projection, no
   `Location`, no replay field, and one exact service invocation;
2. exact replay represented by the same stored result returns byte-equivalent
   JSON semantics with the same status and headers;
3. `AUTHORIZATION_FAILED`, `IDEMPOTENCY_CONFLICT`, and
   `STORED_RECEIPT_INTEGRITY_FAILURE` map to exact 404, 409, and 500 envelopes;
4. every impossible or wrong-namespace decision maps to the fixed 500;
5. unexpected service/composition/projection exceptions are sanitized;
6. `CancelledError` propagates and is not converted to a response;
7. missing and duplicate `Idempotency-Key` fail with 422 before service;
8. empty, 129-byte, non-ASCII, leading punctuation, whitespace, comma-joined,
   percent-encoded, and other invalid keys fail before service;
9. minimum and maximum valid keys pass;
10. `"Key.Case"` and `"key.case"` pass unchanged as distinct case-sensitive
    `PlayerCharacterOperationId` values;
11. no whitespace trim, Unicode normalization, decoding, or alternate body/
    query operation identity is accepted;
12. missing, wrong, or ambiguous `Content-Type` fails with 422; exact
    `application/json` and a valid charset parameter pass;
13. the complete valid `CharacterCreationCommand` public graph reaches the
    service unchanged;
14. smallest valid omitted-declaration graph is accepted;
15. invalid nested declaration, unknown top-level and nested fields, top-level
    null/omission, illegal declaration null/value combinations, duplicate
    features/custom keys, invalid Unicode/NUL, non-adult age, invalid enums,
    and a 65,537-byte canonical declaration envelope fail with sanitized 422
    before service;
16. 65,536-byte canonical declaration boundary behavior remains the existing
    model behavior;
17. path, query, header, and body attempts to supply or override controller
    identity either fail as unknown body data or never enter the service
    principal;
18. the principal passed to create is exactly the dependency-provided
    `RequestPrincipal`;
19. response schema omits result schema version, receipt, fingerprint,
    ownership, recovery, transaction, and persistence data;
20. P5-S1 owned read tests remain unchanged and passing; and
21. OpenAPI asserts exact method, operation ID, tag, summary, six-part
    description, required header constraints, request schema, 200 projection,
    and exact 200 response description `Player Character created or exactly
    replayed.`, 404/409/422/500 `ErrorResponse`, no 201/400/401/403/415, no
    security scheme, and no internal creation schemas.

Equivalent-request replay at this layer uses requests whose parsed command
models compare equal, including accepted NFC equivalence. The real
fingerprint/replay proof remains in existing operation/service tests and the
MySQL API test below.

### 16.2 `tests/integration/test_mysql_player_character_api.py`

This path reuses its normal app construction, configured controller resolver,
real `SqlAlchemyUnitOfWork`, cleanup scope, and durable family-count queries.
It adds:

1. first POST success and durable reload of controller binding, allocation,
   current row, revision-one history, and creation receipt;
2. exact replay by the same caller, key, and equivalent request returns an
   equal public body and leaves all family counts unchanged;
3. replay proves no second allocation, current/history write, receipt,
   controller-binding insertion, or commit by using a test-only counting
   wrapper around the real `SqlAlchemyUnitOfWork`;
4. same caller/key with changed command returns the exact 409 and leaves counts
   unchanged;
5. different keys create distinct operations and server-issued character IDs;
6. another configured principal using the same key is a distinct
   controller-scoped operation and gains no access to the first controller's
   receipt or character;
7. an unconfigured principal receives the same non-enumerating 404 without a
   receipt lookup or write;
8. a controlled pre-commit/persistence failure returns sanitized 500 and leaves
   no partial durable family;
9. corrupt stored receipt/result evidence returns sanitized 500 without
   internal detail;
10. admitted binding-add race recovery returns the durable winner once, while
    unsupported allocation/receipt uniqueness and recovery failures remain
    sanitized 500 with no generic retry;
11. controlled uncertain commit returns sanitized 500 and performs no recovery
    reread or success claim;
12. cancellation propagates through the API call and rolls back the
    transaction; and
13. P5-S1 owned GET returns current state after creation and remains
    non-enumerating and write-free.

The test uses existing MySQL fixtures and repository/UoW wrappers. It adds no
concurrency framework, schema, migration, external service, or database
fallback.

### 16.3 `tests/unit/test_run_composition.py`

The exact `(path, methods)` inventory after implementation includes:

- `GET /health`;
- `GET /v1/player-characters/{player_character_id}`;
- `POST /v1/player-characters`;
- `GET /v1/scenarios`;
- `POST /v1/sessions`;
- `GET /v1/sessions/{session_id}`;
- `GET /v1/sessions/{session_id}/state`;
- `GET /v1/sessions/{session_id}/view`;
- `GET /v1/sessions/{session_id}/requests/{client_request_id}`;
- `POST /v1/sessions/{session_id}/actions`; and
- no Run path or other Player Character method.

The test also proves normal `build_default_services` continues to share one
controller resolver and one lazy MySQL Unit of Work graph between the canonical
services. No new composition root or repository is introduced.

### 16.4 `tests/unit/test_demo_composition.py`

The focused regression proves:

- `runtime.services.player_character_service is None`;
- neither Player Character GET nor POST route/method is present;
- neither operation is present in Demo OpenAPI; and
- Demo Provider and gameplay composition remain unchanged.

### 16.5 Unchanged regression evidence

The later validation runs these existing paths without modifying them:

- `tests/unit/test_player_character.py`;
- `tests/unit/test_player_character_operations.py`;
- `tests/unit/test_player_character_service.py`;
- `tests/unit/test_player_character_composition.py`;
- `tests/integration/test_mysql_player_character.py`;
- `tests/integration/test_mysql_player_character_service.py`; and
- `tests/integration/test_mysql_player_character_run_binding.py`.

They retain the authoritative evidence for model validation, fingerprint
equivalence, stored-result reconstruction, no second replay mutation, race-safe
recovery, original exception preservation, uncertain commit, cancellation,
ownership, persistence, and P4-S1 binding preservation.

There is no Player Character client seam under `web/`; the closed path budget
prohibits a frontend change. The normal/Demo route inventories are the focused
runtime non-activation regressions. Run non-activation is enforced by the
method inventory and unchanged P4-S1 tests.

## 17. Local validation sequence and current candidate evidence

This sequence governs implementation and handoff verification. The current
candidate completed the assigned focused evidence: syntax compilation; the
complete MySQL API target (`11 passed`); MySQL player-character service
regression (`8 passed`); the P5-S2 API/composition/P5-S1 unit group (`155
passed`); the Demo composition target (`40 passed`); the direct Run composition
target (`10 passed`); and the plan-linked Player Character unit group (`358
passed`). `git diff --check` and `git diff --cached --check` passed. This
documentation synchronization does not rerun those already-passing suites.

1. Confirm the separately approved clean implementation baseline, exact branch
   and hashes, empty index, no untracked or unmerged paths, no active Git
   operation, intact `.venv`, PowerShell 7+, and the five-code/five-doc closed
   path budget.
2. Run the repository environment doctor without printing secrets:

   ```powershell
   .\scripts\doctor.ps1 -Strict
   ```

3. Run import/compilation checks:

   ```powershell
   .\.venv\Scripts\python.exe -m compileall -q src tests alembic
   ```

4. Run focused unit/API/model/operation/service tests:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q tests/unit/test_player_character_api.py tests/unit/test_player_character.py tests/unit/test_player_character_operations.py tests/unit/test_player_character_service.py
   ```

5. Run focused composition, OpenAPI, P5-S1, Demo, and Run inventory tests:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q tests/unit/test_player_character_composition.py tests/unit/test_run_composition.py tests/unit/test_demo_composition.py tests/unit/test_player_character_read.py
   ```

6. In the caller environment with `TEST_DATABASE_URL` available, after safely
   confirming only `mysql+asyncmy` and `deviation_protocol_test` without
   displaying a complete URL, run focused MySQL
   creation/replay/ownership/receipt/transaction tests:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q tests/integration/test_mysql_player_character_api.py tests/integration/test_mysql_player_character_service.py tests/integration/test_mysql_player_character.py tests/integration/test_mysql_player_character_run_binding.py
   ```

7. Invoke the repository-required sanitized Offline profile:

    ```powershell
    .\scripts\verify.ps1 -Mode Offline
    ```

   `verify.ps1 -Mode Offline` owns an isolated child process that removes or
   excludes `TEST_DATABASE_URL`, `DATABASE_URL`, `DEEPSEEK_API_KEY`, and
   `RUN_LIVE_DEEPSEEK_TEST`, then runs its Offline preflight and
   `doctor.ps1 -Strict -RequireOffline` there. Do not invoke the offline doctor
   directly in the database-enabled caller environment. Do not persistently
   remove, overwrite, print, reconstruct, or manually copy `TEST_DATABASE_URL`.
   After the child exits, the unchanged caller environment retains
   `TEST_DATABASE_URL` for the MySQL profile.

8. Run the repository-required MySQL profile:

   ```powershell
   .\scripts\verify.ps1 -Mode MySQL
   ```

9. Run the repository-required Full profile:

   ```powershell
   .\scripts\verify.ps1 -Mode Full
   ```

10. Inspect Alembic without creating or applying a migration:

    ```powershell
    .\.venv\Scripts\python.exe -m alembic heads
    .\.venv\Scripts\python.exe -m alembic history
    ```

    The head and history must be unchanged from the approved implementation
    baseline.

11. Complete the canonical documentation-synchronization checklist, including
    implementation evidence, phase status, guardrail impact, and exact path
    inventory.
12. Run documentation link, approval-token, whitespace, code-fence, BOM,
    line-ending, placeholder, stale-status, and generated-artifact checks.
13. Run:

    ```powershell
    git diff --check
    ```

14. Inspect complete diffs for every changed path, all untracked paths, index
    state, unmerged paths, active Git operations, branch, HEAD, local
    `main`, local `origin/main`, ahead/behind, and the final changed-path
    inventory.

CI is not a substitute for any local check. No Provider or live model call is
permitted. `RUN_LIVE_DEEPSEEK_TEST` remains disabled.

## 18. Candidate review and handoff stop conditions

Stop without silently broadening scope if:

1. the approved implementation baseline, branch, refs, ahead/behind, worktree,
   index, untracked, unmerged, or active-operation state differs;
2. the frozen contract differs from its published authority;
3. any path outside the closed budget must change;
4. the public contract or architecture must change before implementation can
   begin;
5. any route, header, body, response, error, OpenAPI, authentication, or
   deployment decision is contradictory or unresolved;
6. exact duplicate-header, ASCII, length, alphabet, opacity, case sensitivity,
   or no-normalization behavior cannot be enforced through the named seam;
7. implementation requires a second creation, receipt, fingerprint, replay,
   ownership, controller-resolution, ID, repository, transaction, or Unit of
   Work model;
8. implementation requires schema, migration, dependency, persistence, or
   transaction behavior changes;
9. implementation requires authentication redesign, production credentials,
   401, 403, or a security scheme;
10. non-enumeration cannot be preserved for unresolved, invalid, mismatched, or
    changed controller authority;
11. application creation semantics, operation namespace, request equivalence,
    stored-result replay, or allocation behavior must change;
12. generic retry, another race recovery, or uncertain-commit recovery is
    proposed;
13. frontend, Demo, mutation, Run, Session, Provider, narrative, scenario,
    world, NPC, memory, relationship, combat, content, or another runtime
    surface would activate;
14. a confirmed defect requires a guardrail edit outside the budget;
15. `.venv` is absent or broken;
16. the Offline sanitizer or its child doctor/preflight, Offline profile, MySQL
    profile, Full profile, focused, compilation, Alembic, documentation, or Git
    verification fails or cannot run safely, or `TEST_DATABASE_URL` is not
    preserved unchanged in the caller environment for the MySQL profile; or
17. final path, index, or Git state contains unrelated work.

A stop requires an exact report and a corrected authority candidate where
applicable. It does not authorize a partial implementation, weaker validation,
fallback database, dependency installation, external call, or contract edit.

## 19. Candidate completion and handoff criteria

The current candidate is ready for fresh independent read-only review only when:

1. the exact one-production/four-test/five-document candidate is implemented;
2. every frozen wire detail, including the exact OpenAPI 200 response
   description, is mechanically satisfied;
3. the route remains thin and calls `PlayerCharacterService.create` exactly
   once;
4. first success and replay are indistinguishable at the public boundary;
5. P5-S1 remains unchanged and passing;
6. Demo, frontend, Run, P5-S3, and every excluded surface remain inactive;
7. the assigned candidate validation in section 17 is recorded;
8. canonical documentation synchronization is complete;
9. its exact bytes and evidence are frozen for independent review.

Independent approval, separate staging and commit authorization, commit, and
publication remain later handoff steps. Completion of the implementation and
assigned local verification in this working-tree candidate does not claim any
of those states.

This plan resolves every architectural, contract, product, authentication,
ownership, persistence, transaction, transport, error, OpenAPI, test,
verification, and handoff decision required for the bounded slice.

## 20. Guardrail impact

None. This plan applies existing ENV-001, ENV-002, DB-001, AUTH-001,
STATE-001, API-001, and PLAY-001 constraints. It records no confirmed defect
and creates no reusable engineering or safety rule.

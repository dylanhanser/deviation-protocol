# Public Client Contract

Phase 3.0 defines the server-owned read contract for a shared Web client and a
future desktop wrapper. It does not provide public identity, abuse controls,
deployment, a browser application, or a desktop adapter. The default principal
is still the fixed `demo-player`/`demo-dev-only` identity and is unsafe for an
Internet-facing deployment.

This document also defines the published P5-S2 Player Character creation/replay
contract and the bounded P5-S3 retirement-contract amendment. P5-S2 was
independently approved, committed, and published at
`4ba66d8f277988325795c905fdf6fd9e416d7457`. P5-S3 received
`STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`. Its first local
implementation candidate received `CHANGES_REQUIRED`; its first corrected and
re-corrected candidates each received a further fresh `CHANGES_REQUIRED`
review. The third review found no production-code defect and requested corrected
SQL-race, durable-state, unit/OpenAPI, and documentation-history evidence. The
later evidence candidate produced a receipt-add 1062 only through a
mid-operation rollback-and-resume topology. The focused investigation returned
`P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`; normal
production retirement writers serialize at the Player Character aggregate
lock. The accepted implementation replaced the
unreachable race claim with normal concurrent HTTP replay/conflict evidence and
explicitly labels recovery evidence as bounded fault injection. Its correction
validation completed locally (canonical Offline 1,814 passed/124 expected skips,
  MySQL 136 passed, and Full 1,937 passed/one opt-in Provider skip). Its focused
  final independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED`, finding no
  material scoped defect. It accepted real-MySQL aggregate-lock serialization,
  exact replay or ordinary idempotency conflict, and one durable mutation; fault
  injection is bounded defensive recovery only, and the unreachable receipt-add
  race is not a requirement. P5-S3 was committed and published as
  `34d063e387cde69500e4dc018ff087e87f3eee74`
  (`feat(player-character): add idempotent retirement endpoint`). Phase 5 is
  complete at P5-S3; no P5-S4 exists and no P5-S3 review remains pending. No
  Demo, public Run, frontend, Web, administration, production-authentication,
  deployment, release, or Provider activation followed from Phase 5.

## Owned Player Character read

The normal application exposes `GET /v1/player-characters/{player_character_id}`
for one controller-owned canonical Player Character. The required opaque path
carrier is ASCII, 1–128 characters, and matches
`^[A-Za-z0-9][A-Za-z0-9_.:-]*$`; it has no request body or query authority.
Success returns only the detached `PlayerCharacterSelfProjection`: nested
`player_character_id`, closed `contract_version`, nested `record_revision`, and
closed `lifecycle`. No profile, controller binding, provenance, receipt, Run,
ORM, repository, or persistence detail is public.

The trusted principal comes only from the application dependency and the
existing configured controller resolver plus owned-read service remains the
ownership authority. Absent, foreign-owned, unmapped, noncanonical, and
otherwise unavailable targets return the identical 404 `ErrorResponse` with
`PLAYER_CHARACTER_NOT_FOUND` and `Player character was not found`. Invalid path
syntax returns the existing sanitized 422 envelope. Integrity, repository,
composition, and unexpected failures return only the sanitized 500 envelope.
The current fixed development principal is not production authentication and
does not make the normal application Internet-ready. The independent Demo does
not register this route.

## P5-S2 Player Character creation/replay

### Contract boundary

The P5-S2 operation is exactly:

```http
POST /v1/player-characters
```

It is one authenticated creation/replay endpoint under the
`player-characters` tag. It adds no list, search, update, delete, mutation,
binding, administration, action, Run, or lifecycle route. It has no path or
query parameter. Undeclared query values carry no authority and do not enter
the application command.

The route accepts one strict JSON body and one required `Idempotency-Key`
header, resolves the caller through the same trusted-principal boundary used by
the owned read, delegates once to the existing
`PlayerCharacterService.create`, and projects that service's
`CreationSuccessResult` into the existing
`PlayerCharacterSelfProjection` allowlist. The controller resolver, creation
policy, identifier issuer, receipt protocol, repositories, and Unit of Work
remain application or infrastructure authorities; the route does not reproduce
them.

The fixed `demo-player` / `demo-dev-only` dependency remains a
development-only principal, not production authentication. P5-S2 supplies no
credential transport, authentication failure protocol, account system, abuse
control, rate limit, CORS policy, or Internet-deployment authority. It does not
activate this route in the independent Demo.

### Authentication, caller identity, and ownership

The route requires the existing trusted `RequestPrincipal` dependency. The
server passes that principal unchanged to the existing configured
principal-to-controller resolver. Only the complete exact trusted
`(authentication_scheme, player_id)` principal may resolve a
`ControllerBindingRef`.

The request path, query, headers, and JSON body contain no controller,
principal, player, owner, authentication-scheme, role, or administrator field.
A client cannot create for another controller or override the resolved
controller. The server-selected controller binding scopes creation replay but
is never returned.

An invalid or unmapped trusted principal, a missing or contradictory resolved
binding, and a changed binding during the existing narrow race-recovery read
all produce the same non-enumerating public outcome defined below. Receipt
lookup and stored-result disclosure remain behind successful controller
authorization. An operation identity is not authorization.

The repository has no production authentication adapter. Consequently this
contract does not invent a `401` challenge, `403` credential policy, OpenAPI
security scheme, cookie, bearer token, or other authentication mechanism. A
future production authentication contract must define rejection before this
route can be Internet-deployed. Under the P5-S2 boundary, an invalid or
unmapped principal that reaches the application service is an authorization
failure, not proof that any controller binding or receipt exists.

### Operation and idempotency identity

`Idempotency-Key` is the sole public carrier for the required client-supplied
creation operation identity.

| Property | Exact contract |
| --- | --- |
| Header name | `Idempotency-Key`; HTTP header-name matching is case-insensitive |
| Requiredness | Required exactly once for every request; no body or query fallback |
| Value type | ASCII string |
| Length | 1–128 characters, therefore also 1–128 UTF-8 bytes |
| Pattern | `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` |
| Null/empty behavior | Headers have no JSON null form; missing, empty, repeated with an ambiguous combined value, or invalid values fail request validation |
| Normalization | The application does not trim, case-fold, Unicode-normalize, decode, or semantically parse the value; value comparison is exact and case-sensitive |
| Internal mapping | Construct `PlayerCharacterOperationId(value=<exact header value>)` |
| Internal namespace | Server-selected `player-character.create/v1`; never client-supplied |

The internal receipt scope remains the exact resolved controller binding,
server-selected namespace, and operation ID. The client never receives or
submits that composite key, controller binding, receipt ID, receipt row,
fingerprint, or stored-result schema metadata.

After the same caller has again resolved to the same controller authority:

- the same operation ID and an equivalent validated
  `CharacterCreationCommand` replay the original stored successful result;
- the same operation ID with a non-equivalent validated command returns the
  idempotency conflict below and performs no allocation or mutation;
- a different operation ID is a distinct creation operation even when its
  validated body is equivalent and may therefore allocate a different
  Player Character; P5-S2 adds no profile-content deduplication or
  controller character limit;
- another controller may use the same header value in its separate private
  scope; and
- possession or guessing of an operation ID grants no access and cannot
  replace authentication or controller resolution.

Request equivalence is the existing P3 creation-fingerprint equivalence after
strict typed validation. It uses NFC player text and keys, sorted object keys,
ordered sequences, exact declaration-state distinctions, exact enum values,
and the supported contract version. It does not case-fold, collapse meaningful
whitespace, sort ordered arrays, merge omitted with explicitly absent or
intentionally undecided, or include the header value or not-yet-issued Player
Character ID in the command fingerprint.

### Request body

The request media type is `application/json`. The public request schema is the
existing strict `CharacterCreationCommand`; it contains only values the
controller may choose and adds no transport copy or parallel creation DTO.
Unknown fields are forbidden at every object level.

The smallest valid body is:

```json
{
  "contract_version": "structured-player-character/v1",
  "character_core": {},
  "narration_preferences": {}
}
```

The top-level inventory is:

| JSON field | Type | Required/null | Validation and internal mapping |
| --- | --- | --- | --- |
| `contract_version` | String enum | Required; null forbidden | Exact value `structured-player-character/v1`; maps unchanged to `CharacterCreationCommand.contract_version` |
| `character_core` | Object | Required; null forbidden | Strict `CharacterCore`; maps unchanged to `CharacterCreationCommand.character_core` |
| `narration_preferences` | Object | Required; null forbidden | Strict `NarrationPreferences`; maps unchanged to `CharacterCreationCommand.narration_preferences` |

`character_core` contains exactly these declaration slots:

| JSON field | Value when present | Required/null | Omitted-field behavior |
| --- | --- | --- | --- |
| `name_or_code_name` | Declaration of `PlayerDeclaredText` | Optional; null forbidden | Materializes the declaration state `omitted` |
| `preferred_form_of_address` | Declaration of `PlayerDeclaredText` | Optional; null forbidden | Materializes `omitted` |
| `adult_identity_and_gender_expression` | Declaration of `PlayerDeclaredText` | Optional; null forbidden | Materializes `omitted` |
| `broad_adult_age_presentation` | Declaration of `AdultAgePresentation` | Optional; null forbidden | Materializes `omitted` |
| `broad_appearance_direction` | Declaration of `PlayerDeclaredText` | Optional; null forbidden | Materializes `omitted` |
| `distinguishing_features` | Declaration of `DistinguishingFeatures` | Optional; null forbidden | Materializes `omitted` |
| `outward_presentation` | Declaration of `PlayerDeclaredText` | Optional; null forbidden | Materializes `omitted` |
| `inward_tendency` | Declaration of `PlayerDeclaredText` | Optional; null forbidden | Materializes `omitted` |
| `reality_anchor` | Declaration of `PlayerDeclaredText` | Optional; null forbidden | Materializes `omitted` |
| `custom_values` | Declaration of `CustomValues` | Optional; null forbidden | Materializes `omitted` |

`narration_preferences` contains exactly:

| JSON field | Value when present | Required/null | Omitted-field behavior |
| --- | --- | --- | --- |
| `internal_thoughts` | Declaration of `PlayerNarrationPreference` | Optional; null forbidden | Materializes the declaration state `omitted`; no narration preference is silently selected |

Every declaration object has this exact shape:

| JSON field | Type | Required/null | Rule |
| --- | --- | --- | --- |
| `state` | String enum | Required; null forbidden | Exact value `omitted`, `explicitly-absent`, `declared`, or `intentionally-undecided` |
| `value` | Slot-specific object | Conditional; see below | Required and non-null only when `state=declared`; otherwise it must be absent or null |

Omitting a declaration field from its containing group and explicitly sending
`{"state":"omitted"}` are equivalent after typed validation. They are not
equivalent to `explicitly-absent` or `intentionally-undecided`. A declaration
with `state=declared` and a missing or null value is invalid. A non-declared
state carrying a non-null value is invalid.

The slot-specific declared values are:

| Type and JSON field | Type | Required/null | Bounds, normalization, and validation |
| --- | --- | --- | --- |
| `PlayerDeclaredText.authority` | String enum | Required; null forbidden | Exact `player-expression` or `player-confirmation`; no case normalization |
| `PlayerDeclaredText.text` | String | Required; null forbidden | Non-empty valid Unicode, NFC-normalized, NUL forbidden; no trimming, case-folding, or field-specific length limit |
| `AdultAgePresentation.adult_only` | Boolean literal | Required; null forbidden | Must be exactly `true`; false is rejected |
| `DistinguishingFeatures.features` | Array of `PlayerDeclaredText` | Required; null forbidden | Ordered; may be empty; duplicate `(authority, NFC text)` entries are rejected; no item-count limit other than the aggregate declaration envelope |
| `CustomValues.entries` | Array of `CustomValueEntry` | Required; null forbidden | Ordered; may be empty; no item-count limit other than the aggregate declaration envelope |
| `CustomValueEntry.key` | String | Required; null forbidden | Non-empty valid Unicode, NFC-normalized, NUL forbidden; keys must be unique after normalization; no trimming or field-specific length limit |
| `CustomValueEntry.declaration` | Declaration of `PlayerDeclaredText` | Required; null forbidden | Uses the same declaration-state and value rules above |
| `PlayerNarrationPreference.authority` | String enum | Required; null forbidden | Exact `player-expression` or `player-confirmation`; no case normalization |
| `PlayerNarrationPreference.value` | String enum | Required; null forbidden | Exact `high-immersion`, `balanced`, or `high-agency`; no default or case normalization |

The `authority` inside a player declaration or narration preference records
the player's own expression or confirmation semantics. It is not a server
authority class, authentication claim, controller binding, other actor's
response, capability, or permission.

All nested objects are strict: unknown keys, wrong JSON types, unknown enum
values, unsupported contract versions, invalid declaration combinations,
duplicate distinguishing features, and duplicate normalized custom-value keys
fail the complete request. Integers and floats are not coerced to strings or
booleans.

The existing canonical player-declaration envelope applies across the fully
materialized `character_core` and `narration_preferences` together: their
canonical NFC UTF-8 JSON must not exceed 65,536 bytes. This is a semantic
canonical-envelope limit, not a claim that the raw HTTP body has the same byte
count. No narrower per-string or per-array limit may be invented by P5-S2.
Object member order is not meaningful; array order is preserved.

After successful transport validation, the route passes the resulting
`CharacterCreationCommand` unchanged to the existing service. It does not
accept or construct client-supplied controller data, operation namespace,
receipt data, fingerprint data, persistence or transaction metadata,
provenance, lifecycle, revision, source reference, character ID, Run binding,
or character-development data.

### Success and exact replay

Both a newly committed creation and an authorized exact replay return:

- HTTP `200 OK`;
- media type `application/json`;
- the same `PlayerCharacterSelfProjection` schema;
- no explicit `created`, `replayed`, replay-status, receipt, or operation field;
  and
- no `Location` header.

The exact response shape is:

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

The response fields are:

| JSON field | Type | Required/null | Exact creation meaning |
| --- | --- | --- | --- |
| `player_character_id` | Object | Required; null forbidden | The server-issued public opaque resource identity |
| `player_character_id.value` | ASCII string | Required; null forbidden | 1–128 characters matching `^[A-Za-z0-9][A-Za-z0-9_.:-]*$`; no generation detail is exposed |
| `contract_version` | String enum | Required; null forbidden | Exact `structured-player-character/v1` |
| `record_revision` | Object | Required; null forbidden | The committed creation-result revision |
| `record_revision.value` | Integer | Required; null forbidden | Exactly `1` for this creation result |
| `lifecycle` | String enum | Required; null forbidden | Exactly `active` for this creation result |

The API maps `CreationSuccessResult.player_character_id`,
`contract_version`, `resulting_revision`, and `resulting_lifecycle` field by
field to the existing projection's `player_character_id`,
`contract_version`, `record_revision`, and `lifecycle`. It does not expose
`result_schema_version`.

P3 returns the same `CreationSuccessResult` type for first success and replay
and intentionally exposes no trustworthy replay discriminator. P5-S2 therefore
uses one stable `200` status and wire-identical body semantics for both paths.
It does not change the service merely to manufacture a transport distinction.
Returning `201` for every result would incorrectly claim that an exact replay
created a resource, while selecting `201` versus `200` would require a new
application-level signal.

An exact replay returns the original stored creation success even if the
canonical character has since advanced to another revision or lifecycle. The
POST response therefore proves the original creation outcome; it is not a
fresh-current-state guarantee. A client that needs current state uses the
separate authorized
`GET /v1/player-characters/{player_character_id}` operation.

Success is never returned before the new operation's existing Unit of Work
commits. Replay performs no allocation, policy call, write, receipt insertion,
or commit. The existing narrow binding-insert race recovery may return only
the already committed winner after the failed Unit of Work has rolled back,
closed, and been discarded.

### Public error mapping and failure preservation

Every HTTP error uses the existing `ErrorResponse` envelope with exactly
`error.error_code` and `error.message`. No field-detail collection, submitted
value, internal identifier, or exception text is returned.

| Condition | HTTP | Stable public code | Exact public message | Field details and internal behavior |
| --- | ---: | --- | --- | --- |
| Malformed JSON or missing/null/wrong-type body | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` | No field details; creation service is not called |
| Unknown body field, unsupported contract version, invalid declaration state/value, non-adult age presentation, duplicate declaration entry, invalid Unicode/NUL, or declaration envelope over 65,536 canonical bytes | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` | No field details; no creation UoW, allocation, receipt, or write |
| Missing, empty, repeated ambiguously, overlength, or syntactically invalid `Idempotency-Key` | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` | No field details; no operation key or receipt lookup is constructed |
| Trusted principal cannot resolve to a valid controller, stored binding authorization fails, or recovery authority changes/disappears | 404 | `PLAYER_CHARACTER_NOT_FOUND` | `Player character was not found` | Identical envelope; no controller/binding/receipt-existence disclosure |
| Same authorized controller scope and operation ID reused with a non-equivalent request | 409 | `IDEMPOTENCY_CONFLICT` | `Idempotency key was reused` | No stored result or fingerprint is disclosed; no allocation, mutation, or commit |
| Public creation/domain validation attributable to the submitted body | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` | Complete request rejected; no salvage and no field details |
| `STORED_RECEIPT_INTEGRITY_FAILURE`, malformed durable receipt, contradictory stored result, or missing winner evidence during approved race recovery | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` | No receipt, fingerprint, binding, race, or persistence detail |
| Allocation collision, initial-state/receipt conflict, unsupported race condition, recovery failure outside the exact admitted result mappings, or repository/UoW/integrity failure | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` | No generic retry and no internal error text |
| Commit failure or uncertain commit durability | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` | No recovery read, replay claim, success claim, or exactly-once claim |
| Unexpected application or composition failure | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` | Fixed sanitized envelope only |

Creation has no client-supplied referenced Session, Run, character, world,
scenario, content, or persistence state. A missing or invalid referenced-state
error is therefore not an applicable P5-S2 outcome and must not be added to its
OpenAPI contract.

There is no active production authentication transport from which P5-S2 can
truthfully define a pre-route unauthenticated HTTP outcome. The fixed
development principal always supplies a principal; invalid or unmapped
principals reaching the service use the identical 404 mapping above. A later
production authentication adapter must separately define any pre-route `401`
or `403` behavior and amend the public contract before Internet deployment.
P5-S2 OpenAPI does not advertise either status.

Cancellation is not converted into an HTTP success or an application retry.
The original cancellation `BaseException` propagates through the existing
rollback/close boundary, so a disconnected or cancelled request has no
guaranteed HTTP response. If an ordinary non-cancellation exception reaches
the installed public exception handler, the response is the sanitized 500
envelope above.

The route translates only the exact creation protocol decisions listed in this
section. A creation `READY_FOR_NEW_OPERATION` or mutation-only protocol code
escaping the service is an internal failure, never a public business outcome.
The API does not catch broad validation, repository, database, commit,
rollback, close, or cancellation failures to relabel them as replay or
conflict.

Original exception identity, traceback, and `__cause__` remain available only
inside the existing application/infrastructure execution boundary. Public
translation neither repairs nor replaces them and never serializes their
messages. Existing logging remains type-only at the public edge.

### Non-enumeration and sanitization

Controller authorization occurs before receipt disclosure. The same 404 body
is used for an unresolved or invalid trusted controller, a contradictory
stored binding, and a changed or missing recovery binding. The route never
answers whether a controller-binding registry row or receipt exists.

An idempotency conflict reveals only that the submitted operation ID cannot be
reused with that request inside the already authorized controller scope. It
does not return the winner, resource ID, original body, receipt, fingerprint,
controller binding, row key, or current character state. Another controller's
scope is never queried.

No public success or error may contain:

- controller, principal, binding, authentication, or account identifiers;
- internal namespace, receipt key, receipt payload, fingerprint, result-schema
  version, or recovery classification;
- authority provenance, source references, transaction state, SQL, constraint
  names, repository/UoW objects, or database URLs;
- stack traces, exception messages, local paths, Provider data, Run bindings,
  or hidden gameplay state; or
- server identifier-generation internals.

Response equality is the non-enumeration guarantee. No constant-time or
cross-request timing guarantee is claimed.

### P5-S2 OpenAPI contract

The published P5-S2 implementation exposes exactly this normal-application
OpenAPI operation:

| OpenAPI property | Required value |
| --- | --- |
| Path and method | `POST /v1/player-characters` |
| `operationId` | `create_player_character` |
| Tag | `player-characters` |
| Summary | `Create or replay a Player Character` |
| Request header | One required `Idempotency-Key` string header with `minLength: 1`, `maxLength: 128`, and pattern `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` |
| Request body | Required `application/json` body referencing `CharacterCreationCommand` |
| Success | `200` `application/json` referencing `PlayerCharacterSelfProjection`, described as created or exactly replayed |
| Errors | `404`, `409`, `422`, and `500`, each with `application/json` referencing `ErrorResponse` |
| Security metadata | No invented production security scheme; the description states that the trusted-principal dependency is development-only and that production authentication and Internet deployment are unsupported |

The operation description must state all of the following:

- controller identity is derived only from the trusted server-side principal;
- `Idempotency-Key` is required and is not authorization;
- first success and exact replay share HTTP 200 and the same body semantics;
- replay returns the original creation result and clients use the owned GET for
  current state;
- no controller binding, receipt, fingerprint, provenance, Run, persistence,
  or transaction data is public; and
- the fixed development principal is not production authentication and the
  route does not make the application Internet-ready.

OpenAPI must enumerate the exact strict declaration DTO graph described above
and must not include `CanonicalPlayerCharacter`, `ControllerBindingRef`,
`CreationReceiptKey`, `StoredCreationSuccessReceipt`,
`CharacterOperationFingerprint`, authority provenance, repositories,
UnitOfWork, ORM, Run, Provider, snapshot, or other internal schemas.
Framework-default validation bodies are not part of the contract; every
declared 422 references the existing `ErrorResponse`.

This is the exact published P5-S2 OpenAPI shape. This document does not register
the operation; runtime exposure is established by the implementation and Git
history. The independent Demo does not gain the route or advertise it merely
because this contract exists.

### Preserved deferrals

P5-S2 changes no existing Session/action contract and does not authorize:

- public Player Character listing, search, update, delete, retirement,
  reactivation, final death, continuity return, transfer, recovery,
  administration, or general mutation;
- public Run creation, read, binding, Session participation, lifecycle
  transition, or `pre_first_turn -> active` transition;
- frontend, Web, browser, or independent Demo activation;
- Provider, narrative, scenario, world, NPC, memory, relationship, combat,
  content, or broader gameplay integration;
- character-creation drafts, templates, additional fields, account/controller
  limits, profile completion, or gameplay customization;
- production authentication, deployment, CORS, abuse controls, rate limits,
  quotas, billing, or Internet readiness;
- a new creation workflow, ownership model, receipt model, generic retry,
  repository/UoW transaction design, schema, migration, dependency, or DB-001
  change; or
- any P4-S2 objective.

## P5-S3 Player Character retirement contract amendment

### Status and exact boundary

This section is the narrow public-contract amendment for the dedicated
[approved P5-S3 plan](structured_player_character_p5_s3_implementation_plan.md).
Its first, first-corrected, and re-corrected local implementation candidates
each received `CHANGES_REQUIRED`; a later evidence candidate was followed by
the focused not-reachable verdict recorded above. The accepted implementation
  candidate received
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED` with no
  material scoped defect and was committed and published at
  `34d063e387cde69500e4dc018ff087e87f3eee74`. The accepted
  real-MySQL evidence proves aggregate-lock serialization, replay/conflict, and
  one durable mutation; fault injection proves bounded defensive recovery only,
  and the unreachable receipt-add race is not a requirement. It specifies the
  one normal-application operation:

```http
POST /v1/player-characters/{player_character_id}/retirement
```

This is a retirement-only command endpoint under the existing
`player-characters` tag. It is not a general mutation, update, action, delete,
binding, Run, administration, or lifecycle endpoint. It is registered only in
the normal application's existing Player Character route block when the
canonical service is composed. It is absent from the independent Demo, public
Run routes, frontend, Web, browser, and administration surfaces.

The route accepts one opaque path identifier, one strict JSON body, and one
required `Idempotency-Key`. It receives the trusted principal and existing
`PlayerCharacterService` through the established dependencies, constructs the
existing retirement `CharacterMutationCommand`, calls
`PlayerCharacterService.mutate` at most once, and projects only an existing
`MutationSuccessResult` into `PlayerCharacterSelfProjection`.

### Path, authentication, ownership, and non-enumeration

`player_character_id` uses the same public carrier as the owned read: the
framework-decoded value must be ASCII, 1–128 characters, and match
`^[A-Za-z0-9][A-Za-z0-9_.:-]*$`. The accepted decoded string is revalidated as
`PlayerCharacterId` without trimming, case-folding, Unicode normalization,
semantic parsing, or another decode. It appears only in the path; no body,
query, or header fallback may target another character.

Controller identity comes only from the dependency-derived
`RequestPrincipal` and the existing configured resolver. The route passes that
principal unchanged to the service. It accepts no controller, owner, account,
player, role, authentication scheme, binding, administrator, or authority
field. The existing service locks the target, verifies the current stored
controller binding, and performs receipt disclosure only after ownership.

An invalid or unmapped principal, absent character, foreign-owned character,
invalid stored ownership, or changed ownership during the existing narrow
receipt-race recovery receives the same 404 response. Malformed path syntax
receives the sanitized 422 response before resource lookup and discloses no
existence fact. Operation-ID possession is never authorization.

The repository still has no production authentication transport. P5-S3 does
not invent credentials, a challenge, a cookie, a bearer token, a `401`, a
`403`, or an OpenAPI security scheme. A missing or invalid principal that
reaches the existing controller-resolution boundary maps to the same
non-enumerating 404. A future pre-route production-authentication contract
would require separate authority before Internet deployment.

### Operation identity

`Idempotency-Key` is the only public carrier for the retirement operation ID.
It inherits the complete P5-S2 convention:

| Property | Exact P5-S3 contract |
| --- | --- |
| Header name | `Idempotency-Key`; header-name matching is case-insensitive |
| Requiredness | Exactly one occurrence; no body, path, or query fallback |
| Value | ASCII string, 1–128 bytes/characters, matching `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` |
| Normalization | None: no trim, case-fold, Unicode normalization, decoding, or semantic parsing; comparison is exact and case-sensitive |
| Internal operation ID | `PlayerCharacterOperationId(value=<exact header value>)` |
| Internal namespace | Existing server-selected `player-character.mutate/v1`; never client-supplied |
| Durable receipt scope | Existing exact `(player_character_id, player-character.mutate/v1, operation_id)` key, after current-owner authorization |

Missing, empty, duplicate, non-ASCII, overlength, alphabet-invalid,
comma-combined, normalized-only, or otherwise invalid values fail with the
sanitized 422 before service invocation. The header value is not a capability
and is never returned.

### Strict request body and explicit confirmation

The required media type is `application/json`. Exactly one raw `Content-Type`
header must be present. Its ASCII media-type token, before the first semicolon
and after stripping only HTTP SP/HTAB, is compared case-insensitively with
`application/json`; parameters are accepted and carry no authority. Missing,
duplicate, non-ASCII, or other media types fail with the sanitized 422.

The public request DTO is `PlayerCharacterRetirementRequest` with exactly these
fields and no defaults:

```json
{
  "contract_version": "structured-player-character/v1",
  "expected_revision": {
    "value": 1
  },
  "confirm_retirement": true
}
```

| JSON field | Type | Required/null | Exact meaning |
| --- | --- | --- | --- |
| `contract_version` | String enum | Required; null forbidden | Must equal `structured-player-character/v1`; becomes the existing command contract version and applicable-reference version |
| `expected_revision` | `PlayerCharacterRevision` object | Required; null forbidden | Contains exactly `value`, a strict JSON integer from 1 through 9223372036854775807; becomes both the command expected revision and applicable-reference revision |
| `confirm_retirement` | Boolean literal | Required; null forbidden | Must be the JSON literal `true`; it is the transport-visible explicit controller confirmation from which the server constructs the existing bound `PlayerConfirmation` |

The DTO and nested revision object forbid unknown fields. Missing fields,
`confirm_retirement=false`, strings such as `"true"`, numeric `1`, null,
wrong types, unsupported versions, malformed JSON, scalar or array top levels,
unknown fields, and any duplicate JSON object-member name at any depth fail the
complete request with the sanitized 422. Duplicate-member rejection occurs
before typed command construction so conflicting confirmation members cannot
be resolved by last-value behavior. No subset is salvaged and the service is
not called.

The route inherits P5-S2 raw-body acquisition: after dependency, path, media
type, and operation-header acceptance and one operation-ID construction, it
calls `await Request.body()` exactly once and buffers the complete raw body.
There is no raw transport-size or `Content-Length` limit. A narrow duplicate-
member preflight is followed by JSON-mode validation through
`PlayerCharacterRetirementRequest.model_validate_json(raw_body)`; neither step
reads the request body again. The absence of a raw body cap and full buffering
are explicit residual risks, not permission to add a different limit during
implementation.

### Exact command construction and application boundary

The API constructs one existing `CharacterMutationCommand` as follows:

| Command field | Exact value/source |
| --- | --- |
| `contract_version` | Parsed request `contract_version` |
| `command_kind` | Server-selected `PlayerCharacterMutationKind.RETIRE` |
| `target_player_character_id` | Validated path `PlayerCharacterId` |
| `expected_revision` | Parsed request `expected_revision` |
| `applicable_reference` | Existing `ApplicableCharacterReference` built from the exact target ID, contract version, and expected revision |
| `confirmation.player_character_id` | Exact target ID |
| `confirmation.expected_revision` | Exact expected revision |
| `confirmation.operation_id` | Exact `PlayerCharacterOperationId` from `Idempotency-Key` |
| `confirmation.mutation_kind` | Server-selected `RETIRE` |
| `confirmation.source_reference` | Fixed trusted `AuthoritySourceRef(value="source.public-player-character-retirement")` |
| `final_death_evidence` | `None` |

The public boolean is evidence of an explicit transport choice; it is not
itself canonical authority. The server binds that accepted choice to the exact
character, revision, operation ID, mutation kind, and fixed trusted source in
the already validated command.

The API owns only raw transport validation, strict DTO parsing, safe command
construction, dependency resolution, one service call, decision-to-public-
error translation, and field-by-field success projection. It owns no
repository, Unit of Work, transaction, receipt, fingerprint, replay lookup,
CAS, active-binding query, rollback, retry, race recovery, or domain policy.

### Mutation, replay, and active-binding behavior

The route reuses the existing `player-character.mutate/v1` command protocol.
Strict transport and DTO validation remain at the API boundary. After the
service has resolved current-owner authority and revalidated the current record,
typed command, and operation ID, the existing signed-64-bit successor-capacity
gate runs before fingerprint construction or durable receipt lookup.

For `expected_revision = 9223372036854775807`, that gate returns the internal
`REVISION_EXHAUSTED` outcome before request-fingerprint construction, receipt
lookup, exact-replay evaluation, different-fingerprint comparison,
current-state stale-revision evaluation, active-binding evaluation, or
lifecycle evaluation. The public route maps the outcome to the existing 409
`PLAYER_CHARACTER_REVISION_CONFLICT` envelope with no details. No successful
mutation or durable success receipt can be created from that rejected request.

Only after all existing pre-receipt validation and revision-capacity gates
succeed does the existing fingerprint bind the exact applicable reference,
`RETIRE` kind, contract version, expected revision, target ID, namespace, and
complete server-constructed confirmation: target ID, expected revision,
operation ID, `RETIRE` kind, and fixed source reference. The public
confirmation boolean has no alternate successful value and is represented by
those bound confirmation facts.

After current-owner authorization:

- for a valid, non-exhausted request that passes every pre-receipt gate, the
  same operation ID and exact fingerprint return the stored original
  `MutationSuccessResult` without policy evaluation, history append, CAS,
  receipt insertion, revision increment, or commit;
- for a valid, non-exhausted request that passes every pre-receipt gate, the
  same operation ID with a different fingerprint returns the fixed 409
  idempotency conflict and performs no mutation;
- for a new operation ID with an ordinary, non-exhausted applicable revision,
  a character already `retired` or `deceased` reaches the existing retirement
  policy, returns the fixed invalid-lifecycle 409, creates no receipt, and
  changes no revision;
- any request carrying the maximum expected revision returns the revision 409
  before receipt or lifecycle evaluation, regardless of whether its operation
  ID was used successfully before or the character is already retired; and
- an exact replay remains valid after later canonical revisions and returns the
  original retirement result rather than claiming to be current state.

A successfully executed retirement cannot have used the exhausted maximum as
its expected revision. Its exact replay therefore continues to carry the
original valid, non-exhausted request and reaches normal receipt evaluation.

The normative precedence cases are:

| Case | Request conditions and ordering | Public result | Preservation |
| --- | --- | --- | --- |
| A — ordinary exact replay | Original successful operation ID; identical valid request; non-exhausted expected revision; pre-receipt gates pass; stored fingerprint matches | 200 exact replay of the stored original retirement projection | No second mutation, receipt, commit, or revision increment |
| B — ordinary different-request reuse | Existing operation ID; valid non-exhausted request; fields differ from the stored successful request; pre-receipt gates pass; stored fingerprint differs | 409 `IDEMPOTENCY_CONFLICT` | No mutation, new receipt, or revision change |
| C — existing operation ID with maximum revision | Existing operation ID; request carries `expected_revision = 9223372036854775807`; its fields would differ from the earlier successful request, but the revision-capacity gate rejects before fingerprint construction or receipt lookup | 409 `PLAYER_CHARACTER_REVISION_CONFLICT`, from internal `REVISION_EXHAUSTED`; not idempotency conflict | Original receipt and canonical state remain unchanged |
| D — new operation after retirement, ordinary revision | New operation ID; valid non-exhausted applicable revision; no receipt preempts evaluation; retired lifecycle is evaluated | 409 `PLAYER_CHARACTER_LIFECYCLE_CONFLICT` | No receipt or state change |
| E — new operation after retirement, maximum revision | New operation ID; request carries the maximum expected revision; the capacity gate rejects before receipt and lifecycle evaluation | 409 `PLAYER_CHARACTER_REVISION_CONFLICT`; not lifecycle conflict | No receipt or state change |

These deterministic outcomes do not expose whether a receipt exists for any
supplied operation ID. Responses disclose only the fixed public result allowed
for the safe request condition that wins precedence.

A genuinely new accepted operation is permitted only when the current
canonical record is owned by the resolved controller, has the exact expected
revision and contract/reference, is `active`, has a representable successor,
and has no current active Run binding. Success preserves the exact
`player_character_id`, contract version, and `controller_binding`, changes only
the admitted complete-record lifecycle/provenance consequences from `active`
to `retired`, appends one immutable revision, CAS-updates current state,
inserts one durable mutation success receipt, commits once, and advances the
canonical revision exactly once.

The P4-S1 seam remains authoritative for current active-binding evidence. If a
valid current active binding exists, the existing internal
`ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` policy decision maps to
the fixed public binding-conflict response below. The character, revision,
receipt families, Run, binding, and Run version remain unchanged. The API does
not end or terminate a Run, historicalize or remove a binding, issue a Run
command, perform a compensating action, or retry retirement. Those operations
remain later Run-owned atomic work.

Persistence and transaction behavior is unchanged. Any rejected, stale,
invalid, bound, CAS-losing, or pre-commit-failing operation exits without a
successful receipt or revision change and rolls back uncommitted work. Only the
existing exact mutation-receipt-add uniqueness conflict may dispose the failed
initial Unit of Work and open at most one fresh read-only recovery Unit of Work
to return a durable winner or conflict. There is no third Unit of Work, policy
retry, write retry, commit retry, generic retry, or uncertain-commit recovery.
All other persistence and commit exceptions preserve their original internal
identity and reach the sanitized public boundary.

That recovery is bounded defensive behavior, not a currently reachable race
between two legitimate retirement requests. Through the normal HTTP route and
production service/UoW graph, distinct real database connections first contend
on the existing Player Character `FOR UPDATE` lock. The waiter cannot look up a
receipt, evaluate policy, write a revision, perform CAS, or add a receipt until
the winner commits. It then returns the stored projection for an identical
fingerprint or the ordinary public idempotency conflict for a different
fingerprint. Exactly one durable revision advance and one mutation receipt
remain, with no duplicate policy mutation, recovery UoW, receipt-add conflict,
or MySQL 1062. Fresh independent reads must prove that state.

The defensive branch remains covered by explicitly labelled narrow
receipt-add fault injection in the service tests, including failed-UoW disposal,
one fresh read-only recovery UoW, authority re-resolution, durable receipt
reread, replay/fingerprint conflict, and absence of a third UoW, mutation retry,
generic retry, recovery write/commit, or uncertain-commit recovery. Direct
repository duplicate-flush evidence is synthetic out-of-topology constraint
translation only. Real receipt-add 1062 race evidence becomes mandatory only if
a future composed runtime writer or changed transaction topology can
legitimately reach receipt uniqueness without first serializing on the
aggregate lock; this amendment neither approves nor requires such a topology.

If commit raises after durability may have occurred, the response is the fixed
500 with no success or replay claim. The service does not reread, recover, or
claim exactly once. A later exact client retry may resolve from durable receipt
state, but the failed request itself makes no durability claim.

### Success response

First committed retirement and authorized exact replay both return:

- HTTP `200 OK`;
- media type `application/json`;
- the existing `PlayerCharacterSelfProjection` response model;
- no `Location` header; and
- no operation ID, replay indicator, receipt, command result, source reference,
  binding, Run, transaction, or recovery metadata.

For an initial revision of 1, the exact shape is:

```json
{
  "player_character_id": {
    "value": "pc.example"
  },
  "contract_version": "structured-player-character/v1",
  "record_revision": {
    "value": 2
  },
  "lifecycle": "retired"
}
```

The route maps `MutationSuccessResult.player_character_id`,
`contract_version`, `resulting_revision`, and `resulting_lifecycle` to the same
four public fields. On first success, `record_revision.value` is exactly the
submitted expected revision plus one and `lifecycle` is `retired`. On replay,
the complete response has the same status, media type, projection semantics,
and original resulting revision/lifecycle. Clients use the owned GET for the
current record after any later mutation.

### Safe public error mapping

Every error body is the existing `ErrorResponse` containing only
`error.error_code` and `error.message`; there is no `details` member.

| Condition | HTTP | Public code | Exact message | Required preservation |
| --- | ---: | --- | --- | --- |
| Invalid, absent, or unmapped principal reaching controller resolution | 404 | `PLAYER_CHARACTER_NOT_FOUND` | `Player character was not found` | Same as missing and non-owned; disclose no controller or authentication fact |
| Malformed path identifier | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` | No lookup and no submitted-value detail |
| Missing or non-owned character, invalid stored ownership, or changed recovery authority | 404 | `PLAYER_CHARACTER_NOT_FOUND` | `Player character was not found` | Identical body for all cases; no existence, owner, binding, or receipt disclosure |
| Malformed/missing/null/wrong-type body; unknown or duplicate member; unsupported contract version; invalid revision; missing, false, malformed, or incorrectly typed confirmation | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` | No field details and no service call |
| Missing, duplicate, non-ASCII, empty, overlength, alphabet-invalid, or otherwise invalid `Idempotency-Key`; invalid or ambiguous `Content-Type` | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` | No raw value, operation key, or receipt disclosure |
| Maximum `expected_revision = 9223372036854775807` | 409 | `PLAYER_CHARACTER_REVISION_CONFLICT` | `Player character revision does not permit retirement` | Capacity gate wins before fingerprint, receipt, stale-current, binding, or lifecycle evaluation; no receipt or state change |
| Ordinary stale expected revision or CAS loss after the pre-receipt gates succeed | 409 | `PLAYER_CHARACTER_REVISION_CONFLICT` | `Player character revision does not permit retirement` | No history, current-row, receipt, or revision change |
| Current lifecycle is not `active`, including a new operation after retirement with an ordinary non-exhausted applicable revision | 409 | `PLAYER_CHARACTER_LIFECYCLE_CONFLICT` | `Player character cannot be retired` | No receipt or revision change; do not disclose private state beyond the safe conflict |
| Current active Run binding triggers the existing P4-S1 guard | 409 | `PLAYER_CHARACTER_ACTIVE_BINDING_CONFLICT` | `Player character is bound to an active Run` | Character, revision, receipt, Run, and binding remain unchanged; no compensation |
| Same character/namespace/operation ID reused by an ordinary valid non-exhausted request whose fingerprint differs, after all pre-receipt gates succeed | 409 | `IDEMPOTENCY_CONFLICT` | `Idempotency key was reused` | Stored result and fingerprint remain private; no mutation or commit |
| Recognized retirement-policy rejection | The revision, lifecycle, or active-binding 409 mapping above | Corresponding fixed code | Corresponding fixed message | Only `STALE_REVISION`, `REVISION_EXHAUSTED`, `INVALID_TRANSITION`, and `ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` are public-safe retirement rejections |
| Stored-receipt integrity failure, impossible/wrong-namespace decision, command/result contradiction, or any other domain/application decision | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` | Treat as internal failure; never publish raw policy code or internal details |
| Repository, binding-evidence integrity, persistence, rollback, close, projection, composition, or other ordinary infrastructure failure | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` | Preserve original error internally; expose no SQL, constraint, path, identifier, or exception text |
| Commit failure or uncertain durability | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` | No reread, recovery, success, replay, or exactly-once claim |

Cancellation remains outside ordinary exception translation and has no promised
HTTP response. Internal exceptions, SQL and constraint details, ownership
facts, controller/principal identifiers, source references, policy traces,
receipts, fingerprints, Run IDs, binding evidence, transaction state, stack
traces, and submitted values are never returned.

The selected mapping uses the existing `error_response`/`ErrorResponse` helper
from `api.errors` directly from the route's private decision translator. No
change to `src/deviation_protocol/api/errors.py` or
`src/deviation_protocol/application/errors.py` is required or authorized.

### P5-S3 OpenAPI contract

P5-S3 is not a current unstaged candidate. Its accepted and published
normal-application operation is exactly:

| OpenAPI property | Required value |
| --- | --- |
| Path and method | `POST /v1/player-characters/{player_character_id}/retirement` |
| `operationId` | `retire_player_character` |
| Tag | `player-characters` |
| Summary | `Retire a Player Character` |
| Path parameter | Required `player_character_id` string, `minLength: 1`, `maxLength: 128`, pattern `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` |
| Header parameter | One required `Idempotency-Key` string, `minLength: 1`, `maxLength: 128`, pattern `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` |
| Request body | One required `application/json` body referencing `PlayerCharacterRetirementRequest` |
| Success | `200` `application/json` referencing `PlayerCharacterSelfProjection`, description `Player Character retired or exactly replayed.` |
| Errors | Only `404`, `409`, `422`, and `500`, each `application/json` referencing `ErrorResponse` |
| Security | No invented production security scheme |

The operation description states that controller identity is dependency-derived;
`Idempotency-Key` is required but is not authorization; `confirm_retirement`
must be the literal `true`; only an owned, active, unbound character can retire;
first success and exact replay share one 200 projection; replay returns the
original retirement result; maximum expected revision deterministically returns
the revision-conflict envelope before idempotency or lifecycle evaluation;
active binding is rejected without Run or character mutation; the operation
does not end a Run or historicalize a binding; the owned GET supplies current
state; and the development principal is not production authentication or
Internet-deployment authority.

OpenAPI includes the strict three-field request graph and existing response/error
schemas. It does not advertise final death, deletion, reactivation, continuity
return, general update/mutation, binding changes, Run termination, controller
data, confirmation provenance, receipts, fingerprints, persistence types, or
internal command/result models. Framework-default validation bodies are not the
public 422 contract. The normal route inventory gained only this published POST;
Demo and public Run inventories gained nothing. Phase 5 is closed at P5-S3, no
P5-S4 exists, and Phase 8 planning does not reopen it.

### P5-S3 exclusions

This amendment does not authorize final death; reactivation or continuity
return; general character updates; binding, unbinding, replacement, switching,
or transfer; deletion, listing, search, or administration; retirement of an
actively bound character; ending or terminating a Run; historicalizing a Run
binding; Run lifecycle redesign; frontend, Web, browser, or Demo activation;
Provider or narrative integration; production authentication; scenario, world,
NPC, memory, relationship, combat, content, or broader gameplay work; schema,
ORM, migration, repository, Unit-of-Work, receipt, CAS, transaction, or
dependency redesign; generic retry; uncertain-commit recovery; or a P4-S2
objective.

## Phase 8 Player Character discovery and Run entry

Status: **P8-S5 consumption of the existing Player Character, Run-entry, and
Session gameplay contracts is implemented, independently approved, committed,
published, and complete. P8-S6 fresh contract evidence has passed; its
documentation implementation candidate remains unapproved, uncommitted,
unpublished, and Phase 8-incomplete.**

The dedicated authority is the
[Phase 8 Structured Player Character Run Entry and Minimum Playable Loop plan](structured_player_character_run_playable_loop_plan.md).
Its original seven-document planning candidate received
`STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED` and was
committed and published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`.
Later modifications to those canonical planning bytes require fresh exact-byte
independent review before a separately authorized documentation commit; that
commit precedes user publication and clean published-baseline confirmation.
P8-G0 is complete and published. P8-S1 eligible-character discovery is
implemented, accepted, committed, and published. P8-S2 atomic internal Run
entry is implemented, accepted, committed, and published at
`70815b181624e5475d2d978bef0db1ed3b22324e`; its implementation and F1/F2/F3
evidence are closed and are not reopened. The
[P8-S3 implementation plan](structured_player_character_p8_s3_implementation_plan.md)
was independently approved and committed/published at
`e17172ad0a9febe4ec9e3a96e7be8204c9722d29`. Its exact normal public-entry
implementation candidate introduced `POST /v1/runs`. Its first independent
implementation review returned `CHANGES_REQUIRED` with five bounded findings,
and all five corrections are complete. The subsequent independent read-only
re-review found no remaining actionable runtime, API, strict-transport,
OpenAPI, MySQL, privacy, architecture, or test-discrimination defect but
formally returned `CHANGES_REQUIRED` solely for one Medium documentation-
synchronization finding. The complete 15-path candidate then received focused
independent read-only approval and was committed and published at
`ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`. P8-S3 is complete. The dedicated
[P8-S4 implementation plan](structured_player_character_p8_s4_implementation_plan.md)
was independently approved and committed/published at
`375a2a7ae018c9c9c79272e5de7da703818d1f20`. Its implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
was committed as `187d41ba3035c8d717c2fb2578a805402255d979`, and was
manually published by the user. P8-S4 composes the existing public Player
Character create/read/retirement, eligible discovery, and Run-entry operations
in deterministic Demo without adding a Demo-specific request, response, error,
privacy, recovery, route, or OpenAPI contract. The dedicated
[P8-S5 implementation plan](structured_player_character_p8_s5_implementation_plan.md)
was independently approved and committed/published at
`dceecaf0d7a33ccde07f519f83997489acd5fc86`, remained frozen during
implementation, and its corrected implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S5_CORRECTED_IMPLEMENTATION_REVIEW_APPROVED`.
The exact eight-path Web implementation was committed and published at
`2ce56a757beed8a3989d38453da3b6d80342ca05`. P8-S5 consumes the existing
contracts without changing any public DTO, error, privacy, recovery, route, or
OpenAPI authority. The frozen P8-S6 implementation plan was approved and
published at `4edf2e3341e60632765b85796e8554797c645692`. Fresh focused API,
OpenAPI, public-client, rendered-Web, deterministic Demo, real-MySQL, Offline,
MySQL, and Full evidence passed without changing those contracts. It proves the
existing primary path from eligible discovery or minimal creation through
`POST /v1/runs`, persisted same-tab Session recovery, authoritative View,
action/request-status recovery, and terminal rendering; the legacy
`POST /v1/sessions` operation remains available but unused by that primary
journey. Error, non-enumeration, response-identity, strict action/status DTO,
uncertain-POST no-auto-retry, GET-only confirmed-202 recovery, and privacy
semantics remain unchanged. These current documentation bytes are only the
unapproved, unstaged, uncommitted, and unpublished P8-S6 implementation
candidate. Phase 8 and the overall project remain incomplete. Phase 5 remains
complete at P5-S3; no P5-S4 exists. Existing Phase 6 and Phase 7 allocations
remain planned and unimplemented, and neither is a Phase 8 prerequisite.

### Eligible-character collection

P8-S1 implements one purpose-specific operation. Published P8-S4 now exposes
that same existing contract in deterministic Demo composition:

```http
GET /v1/player-characters/eligible-for-run-entry
```

It accepts no path parameter, query, body, filter, search, sorting, page,
cursor, count, controller, lifecycle, binding, or administration input. The
server resolves the trusted principal to controller authority before reading
private data.

The exact success body is:

```json
{
  "eligible_player_characters": [
    {
      "player_character_id": {"value": "pc.example"},
      "contract_version": "structured-player-character/v1",
      "record_revision": {"value": 1},
      "lifecycle": "active"
    }
  ],
  "truncated": false
}
```

Every item is the existing detached four-field
`PlayerCharacterSelfProjection`. Only records owned by the resolved controller,
currently `active`, and without an active Run binding are returned. Results use
exact case-sensitive `player_character_id` ascending order. The service reads
at most 33 eligible rows, returns at most 32, and sets `truncated=true` only
when another eligible row exists. The cap is a response-safety bound, not an
account limit. No total count or pagination contract exists.

A resolved controller with no eligible character receives HTTP 200 with an
empty tuple/list and `truncated=false`. Unavailable controller authority uses
the existing non-enumerating 404 Player Character envelope. Invalid transport
uses the existing safe 422 envelope; unexpected or integrity failures use the
existing safe 500 envelope. The read performs no lock, write, receipt, commit,
or recovery.

### Run-entry request

The published P8-S3 implementation provides one normal-application mutation.
Published P8-S4 exposes the same operation and contract in deterministic Demo
composition without a second adapter or public shape:

```http
POST /v1/runs
Idempotency-Key: <opaque operation identity>
Content-Type: application/json

{
  "player_character_id": "pc.example",
  "expected_record_revision": 1,
  "scenario_id": "death_certificate"
}
```

`Idempotency-Key` uses the existing Player Character/Run opaque ASCII grammar
and 1-through-128-character bound. It is scoped by the server-resolved
controller and is never authority. The strict extra-forbid JSON body admits
only:

| Field | Public rule |
| --- | --- |
| `player_character_id` | Exact opaque `PlayerCharacterId` grammar and 1-through-128 ASCII-character bound |
| `expected_record_revision` | Positive signed-64-bit current Player Character revision selected from an authoritative projection |
| `scenario_id` | Exact safe opaque scenario ID selected from `GET /v1/scenarios`, then revalidated by the server |

The request admits no principal, controller, ownership, Run, continuous-story-
line, Session, world, visit, lifecycle, binding, applicable-reference object,
character-definition, snapshot, state, receipt, operation namespace, seed,
event, Provider, or recovery field. The server issues Run/line/Session
identities, derives internal operation identities, selects the scenario's
validated default static character definition for current Session
initialization, and owns every authoritative state transition.

First committed success and exact replay both return HTTP 200:

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

All four top-level fields are required. The response is intentionally stable
after gameplay advances: it contains no Session phase/version/timestamps,
initial Frame, current View, or Run state version. The client must immediately
read `GET /v1/sessions/{session_id}/view` and then follow existing authoritative
affordances.

The response never exposes continuous-story-line identity, controller binding,
full applicable reference, operation IDs, fingerprints, receipts, authority
source, binding state/times, static character definition, world/visit identity,
snapshot, hidden scenario state, SQL, Provider, transaction, lock, or recovery
data.

### Run-entry authority and replay

The server proves ownership before targeted receipt disclosure. For a new
operation it requires the exact current revision, lifecycle `active`, and no
active Run binding under the Player Character lock. It validates the scenario
through existing catalogue authority. One application-owned UoW then creates
the Run/line, writes the immutable exact character binding, creates the Session
and initial scenario state, adds separate Session participation, activates the
Run, writes successful receipts, and commits once.

Exact replay returns the original stable body without identity issuance,
mutation, state-version advance, Session creation, or commit. Incompatible use
of the same controller-scoped key returns the existing 409
`IDEMPOTENCY_CONFLICT`. A different key for an already-bound character returns
409 `PLAYER_CHARACTER_NOT_ELIGIBLE`; it does not disclose or resume the
existing Run. A stale expected revision returns 409
`PLAYER_CHARACTER_STALE`. A concurrency/CAS/participation conflict not
explained by exact replay returns 409 `RUN_ENTRY_CONFLICT`.

Foreign ownership, missing ownership, and unavailable authoritative ownership
mapping converge on the same 404 `PLAYER_CHARACTER_NOT_FOUND`. Malformed or
corrupt surviving canonical ownership evidence or state is an integrity
failure, is never disguised as a normal ownership miss, and uses the existing
safe 500 envelope without raw integrity or storage detail. Retired, deceased,
bound, version-exhausted, or otherwise ineligible owned characters use
`PLAYER_CHARACTER_NOT_ELIGIBLE`. An unavailable scenario uses the existing 422
`INVALID_SCENARIO_DEFINITION`. Other corrupt stored evidence, impossible
internal results, persistence errors, and uncertain commit outcomes also use
the existing safe 500 envelope and disclose no internal detail. Cancellation
propagates and uncommitted state rolls back. There is no generic or automatic
retry.

### OpenAPI boundary

P8-S3 OpenAPI must describe exactly:

- the eligible collection's 200, 404, 422, and 500 responses;
- the Run-entry operation's required `Idempotency-Key`, exact strict body,
  exact 200 success DTO, and 404/409/422/500 error responses;
- the existing `ErrorResponse` envelope for every error; and
- no internal domain, persistence, receipt, authority, or Provider model.

Runtime and OpenAPI must use the same DTOs and status set. FastAPI's default
validation body is not public contract.

### Client and recovery boundary

The primary Web client now discovers public scenarios and eligible Player
Characters, creates one minimal character through the existing route only when
the eligible collection is empty, selects one exact eligible projection and one
scenario, submits Run entry as one logical attempt, validates the response,
persists the existing same-tab Session recovery record, reads the authoritative
View, and reuses the current action, polling, refresh, recovery, and terminal
loop. That journey does not use the legacy `POST /v1/sessions` route; the route
and `PublicApiClient.createSession` remain available for existing uses.

For both Player Character creation and Run entry, one logical mutation attempt
has one exact idempotency key and one exact request body. The Web client MUST:

1. generate the key before issuing the first POST and freeze the exact body at
   the same boundary;
2. retain that key/body pair in component/process memory while durability is
   uncertain, never attach a different body to the retained key, and never
   silently generate a replacement key for the unresolved attempt;
3. perform no automatic retry; only an explicit user-triggered manual retry is
   allowed, and it resends the exact same key and exact same body;
4. treat a directly received contract-defined 404 as clearable only when no
   earlier send for that retained key/body pair has produced a
   durability-unknown outcome;
5. clear a Player Character creation attempt after an authoritative 200
   success/replay; subject to the history-sensitive 404 rule above, the route's
   documented definitive 404, 409, or 422 rejection may also clear it;
6. after an authoritative 200 Run-entry success/replay, validate the response,
   store its `session_id` through the existing same-tab recovery helper, and
   only then clear the retained Run-entry attempt; subject to the same
   history-sensitive 404 rule, the route's documented definitive 404, 409, or
   422 rejection may also clear it;
7. after transport loss, timeout, response loss, cancellation, the sanitized
   500 envelope, an unrecognized response, or any other outcome whose commit
   status is unknown, mark the retained logical attempt as uncertainty-tainted
   and retain its exact key/body pair. Because the same public 500 covers both
   ordinary internal failure and uncertain commit durability, a client cannot
   classify it as a definitive rejection; and
8. while uncertainty-tainted, never treat a later authorization, ownership,
   unavailable-authority, or non-enumerating 404 as proof that the earlier send
   did not commit, and never clear the retained pair because of that 404. The
   client keeps the exact same key and exact frozen body, generates no
   replacement key, attaches no different body, performs no automatic or
   silent retry, and permits only a later explicit user-triggered retry using
   that exact pair. A tainted attempt may clear only when an operation-specific
   authoritative result resolves the earlier uncertainty under this public
   contract. The existing authoritative-success behavior and the documented
   classification of responses other than this history-sensitive 404 remain
   unchanged.

The retained attempt exists only in component/process memory for the currently
loaded Web experience. Reload before an authoritative response—and, for Run
entry, before the Session recovery record is stored—cannot recover that
pending attempt and remains unsupported. Browser close, cross-tab,
cross-browser, cross-device, and multi-device pending-operation recovery are
also unsupported. Phase 8 adds no `localStorage`, new `sessionStorage`
pending-operation record, IndexedDB, receipt-discovery route, Run-discovery
route, other server discovery route, durable pending-operation store,
automatic recovery, or background retry.

After a validated Run-entry success, the client persists the Session recovery
record before its first authoritative View read and before clearing the
retained Run-entry pair. Once that record is durable in the current tab, safe
View recovery uses `GET /v1/sessions/{session_id}/view` and never replays the
Run-entry mutation. Single-flight and component-generation ownership prevent
duplicate sends and stale completions; public UI, errors, URLs, logs, and
storage do not expose the idempotency key or private authority/persistence
detail.

The client does not infer eligibility, binding, lifecycle, scenario outcome, or
Run state. It adds no Run/character recovery record, optimistic state,
`localStorage`, URL authority, automatic entry/action replay, cross-tab,
browser-close, cross-browser, cross-device, or multi-device guarantee.
Explicitly clearing the current tab's Session does not end a Run, detach or
retire a character, or delete server state.

Scenario settlement remains the current Session `ENDED` and
`RESOLVED`/`FAILED` projection. It does not complete or terminate the Run,
which remains active and bound for later separately authorized continuation.

### Phase 8 public exclusions

Phase 8 adds no general character list/search/filter/page/count/admin or profile
UI; no public Run read/list/patch/bind/rebind/attach/complete/terminate/resume/
exit/delete operation; no character switching, transfer, retirement change,
reactivation, final death, or binding historicalization; no world/profile/
visit contract; no new scenario/content; no Provider behavior; no production
authentication/deployment; and no schema or migration.

## Public scenario discovery

`GET /v1/scenarios` returns a bounded catalog sorted by `scenario_id`. Only a
scenario with an explicit `public_client` block in its versioned scenario pack
is listed. The response is built field by field and contains:

- `scenario_id` and `content_version` from `ScenarioDefinition`;
- public `title`, `hook`, character descriptions and default character from the
  scenario's `public_client` block;
- character display names from the matching versioned `ContentCatalog` entry.

The endpoint never serializes `ScenarioDefinition`. Facts, clues, transitions,
outcome and memory rules, NPC knowledge, phase identifiers, clocks, endings and
future-scene metadata are not part of this response. A public metadata block is
strictly bounded and catalog loading verifies all referenced characters, every
scene/ending presentation, unique action labels and the default character.

## Session view presentation

`GET /v1/sessions/{session_id}/view` retains the existing reconnect-safe
projections and adds two explicit objects:

- `presentation`: public scenario title plus only the current scene title and
  summary. `ending` is omitted while ACTIVE and contains only the matching
  public title and summary after the runtime has ended.
- `action_affordances`: the current UI action contract described below.

The projection looks up public copy by the validated runtime's current phase and
ending, but does not emit those internal lookup keys in the new presentation
objects. A missing or inconsistent binding is handled as `SNAPSHOT_INVALID`.
View reads do not advance the Director, claim a lease, invoke a Provider, or
write sessions, snapshots, events, turn requests or narrative jobs.

`scenario_status` remains the two-value page lifecycle (`ACTIVE` or `ENDED`).
The always-present `ending_status` field supplies the settlement classification:
it is `null` while ACTIVE, `RESOLVED` after a successful ending and `FAILED`
after a failure ending. The value is projected only from the restored
authoritative scenario runtime status. Clients must not infer success or
failure from `ending_id`, ending presentation, narrative text or player memory.

## Action affordances

`action_affordances.mode` has three states:

| Mode | Public payload | Client behavior |
| --- | --- | --- |
| `DECISION` | Bound public `decision_id` and `CHOOSE` choices | Submit one displayed choice; no free-action entry is advertised. |
| `FREE_ACTIONS` | Zero or more typed actions | Render the declared input and optional visible targets. |
| `ENDED` | No actions or choices | Render settlement only. |

Decision choices are copied from the current safe Frame. Their public Frame
type is the non-semantic value `choice`; internal scenario action types and
custom-action constraints are removed at the public decision binding. On
submission, `ScenarioDecisionResponsePolicy` uses the public choice ID to look
up the current versioned definition again, and only the trusted definition can
provide event or state effects.

Free narrative action types come from the same structurally eligible
`narrative_outcome_rules` used by `allowed_narrative_outcomes`. The shared query
applies current phase, location, decision, clue, fact, visible-NPC and once-only
conditions but does not reveal rule identity or text matchers. Submitted text is
still checked by the full outcome policy. `input_kind` and maximum length come
from `InputContractPolicy`, which also validates submissions. Labels come from
the versioned public content block. `CONTINUE` appears only when
`ScenarioContinuePolicy` authorizes the current state and Frame.

The affordance is a UI description, not a capability. `ActionGateway`, the
decision/continue policies, locked state reload and narrative outcome policy
remain final authority. Clients must handle a later rejection or stale view.

## Response status and error contract

`POST /v1/sessions/{session_id}/actions` returns an `ActionResponse` with 200
when the request completes synchronously and with 202 when narrative work is
pending. The client polls the existing request-status endpoint exactly as
directed by that response; the status distinction does not change the action
body or idempotency semantics.

Public errors use the single `ErrorResponse` envelope containing only
`error.error_code` and `error.message`. This includes request-validation 422
responses; FastAPI's default validation body is not part of the public
contract. OpenAPI declares the actual error statuses for each public route and
describes public DTOs only. It must not expose scenario definitions, narrative
jobs, receipts, Provider data or other internal models.

### Targets and TALK

Targets contain only current runtime NPC IDs and display names already present
in the player-visible state and current Frame. Definition IDs, invisible NPCs
and rule-required subjects are not disclosed by the target projection.

Existing production policy allows `TALK` with dialogue and no target; Phase 3.0
therefore exposes `target_required=false`. A client may offer the current
visible NPCs as optional targets. The server continues to reject every supplied
target that is not currently visible/interactable. Changing TALK to require a
target would be a separate domain-contract change, not a UI assumption.

## Client submission rules

- `NONE` means no player-authored input; currently this is `CONTINUE`.
- `DESCRIPTION` uses `description`, currently with a 150-character limit.
- `DIALOGUE` uses `dialogue`, currently with a 200-character limit.
- A decision uses `CHOOSE`, the current public `decision_id`, and one displayed
  `choice_id`; it has no text, target or tool payload.
- Clients never infer action type, decision state or ending from narrative text.
- Clients do not parse public tokens or internal IDs and do not copy scenario
  rules. A refreshed View replaces all earlier affordances.

All narrative and public copy is plain text. The public contract contains no
write endpoint for facts, clues, memory, rewards, clocks, endings or world
state. It contains no snapshot, job, proposal, Provider, receipt, memory-rule or
event-sequence DTO.

## Verification boundary

Contract tests enforce exact response keys, hidden-value scans, ACTIVE/ENDED
ending visibility and RESOLVED/FAILED classification, decision/free/continue
modes, safe targets, shared Gateway input contracts, ownership 404,
`SNAPSHOT_INVALID`, read-only queries, OpenAPI response/error schemas and model
exclusions, and absence of scenario-ID branches. Browser and MySQL tests use
Scripted Providers; live DeepSeek remains opt-in and is not used here.

## Experimental dynamic suggestion extension

The DNVS candidate adds one optional `suggested_actions` member to
`action_affordances`. Its absence preserves the existing deterministic public
contract. When present, each entry contains server-owned `suggestion_id`,
zero-based `ordinal`, equal plain-text `label` and `description`, and a complete
nested action submission containing `turn_id`, `client_request_id`, `CUSTOM`,
and `description`. The client must submit that nested object unchanged and must
not generate, parse, or replace either identity.

Dynamic active Views expose exactly one free `CUSTOM` description affordance
with the scenario-authoritative label and exactly three current server
suggestions. Suggestions from a stale View are not capabilities: the server
revalidates their complete normalized 13-field submission and current
presentation binding. A successful action is not rendered as progression until
the server returns or polling resolves to an authoritative response and a fresh
View is loaded. Pending, stale, outcome-unknown, capacity, and terminal failure
continue to use the existing sanitized response/error and recovery rules; the
client never retries an action automatically.

The product-facing generation requirement is natural Simplified Chinese for
every server-authored Dynamic action label, description, and suggestion.
Separately, the deterministic minimum zh-CN affordance check requires at least
one Unicode CJK Unified Ideograph and rejects every ASCII letter; candidate
suggestions and current authoritative projections both pass that same check.
This bounded mechanical rule does not distinguish Simplified from Traditional
Chinese, prove that every accepted CJK string is semantically Chinese, or act
as a full language-identification system. Non-Chinese CJK text can therefore
pass mechanically even though it is not desired product prose. Punctuation,
permitted whitespace, Arabic numerals, and emoji do not independently
invalidate otherwise compliant Chinese text. Stable protocol keys,
identifiers, action types, and enum literals remain English. The Web client
renders and submits authoritative text verbatim and must not translate,
replace, or maintain a divergent client-only label. Free-action test input is a
natural Chinese sentence, but the submitted protocol shape remains `CUSTOM`
with its unchanged English identifiers.

This additive extension remains experimental, but its runtime and Web behaviors
exist in published history. It does not complete production or evidence work
and does not alter Phase 6, Phase 7, or completed Phase 8.

### Committed Dynamic Narrative public-fact count

The implemented D1 contract makes the smallest compatible extension to the
existing nested `feedback_parameters` object. It adds no top-level Action DTO
or View field. An exact v2 committed Dynamic Narrative Action response includes
an object equivalent to this canonical JSON excerpt:

```json
{"feedback_parameters":{"outcome_result":"SUCCESS","public_fact_count":0}}
```

`public_fact_count` is required for every exact v2
`DYNAMIC_NARRATIVE_COMMITTED` success result. It is an exact non-Boolean integer
from `0` through `3`; integer `0` must be serialized and preserved and is not
semantically equivalent to a missing member. The value represents only the
public facts newly accepted and committed by that Action.

The server-owned atomic finalization seam calculates the scalar prospectively as
`len(allocated_public_facts)`. The source is the final allocated public-fact
tuple of the final complete validated candidate, after any authorized
application replacement has selected that candidate. Before the normal UoW
commit, the same derived value is included consistently in the private event,
stored `TurnResponse`, replay material, committed request-status response
material, and direct response material. Only the final candidate contributes;
rejected, failed, superseded, or non-published generations contribute zero and
are not double-counted.

Until normal UoW commit succeeds, that prospectively derived value is staged
candidate material only: it has no authoritative committed or publicly
claimable meaning. Commit success gives the event, stored response, replay,
committed request-status projection, and direct committed response the same
meaning atomically. Failure or rollback must not publish or preserve a claimed
committed count.

The `COMPLETE_NEW` path prospectively constructs the expected response and event
from the same final allocated tuple and the same derivation rule, then uses the
existing reconciliation seam to compare that expectation with authoritative
existing committed state. The scalar becomes authoritative and publicly
claimable through that path only when reconciliation establishes
`COMPLETE_NEW`, converging on the same result as normal commit success. It does
not mutate an already committed response.

The same committed value is preserved in a direct HTTP `200` response, stored
response/replay, and a committed request-status response. Browser presentation
may claim the value only from a committed Dynamic Narrative result bound to the
current Session and the exact resulting authoritative revision. Missing,
malformed, out-of-range, wrong-lifecycle, wrong-Session, or wrong-revision data
fails closed and cannot produce a browser-visible claimed count.

Committed-response recovery is schema-epoch aware. Trusted durable
`NarrativeJob.prompt_schema_version`, not response-controlled data, selects the
contract:

- genuine historical v1 requires exact feedback
  `{"outcome_result": <validated result>}` and does not synthesize the v2
  member; and
- v2 requires exact feedback
  `{"outcome_result": <validated result>, "public_fact_count": <exact non-Boolean integer 0..3>}`.

For a committed Dynamic result, the durable job and stored response/receipt
must agree on Session ID, client request ID, action signature, and durable turn
ID. The turn ID is an internal recovery association and adds no public response
or request-status field. Trusted Dynamic-job status and the complete committed
lifecycle/stable-code shape are mandatory; contradictory response-controlled
lifecycle or stable-code fields cannot disguise another response as a valid
Dynamic commitment. POST replay and GET request-status recovery call the same
validation authority and fail closed on the same boundary.

Malformed or contradictory stored data returns exactly HTTP `409` with the
established sanitized envelope:

```json
{"error":{"error_code":"STORED_TURN_RESPONSE_INVALID","message":"Session state is unavailable or incompatible"}}
```

The serialized message is periodless. Recovery validation performs no Provider
call, allocation, persistence mutation, or commit. No private fact key/value,
Provider fragment, private-memory canary, malformed stored field, Pydantic
validation detail, or other internal value may enter the public body or a
retained direct exception cause/context chain.

The scalar exposes no fact value, generated key, allocation information, slot,
collision input, hidden reference, or Provider data. It adds no top-level Action
field, does not change the `PlayerSessionView` schema, and does not create a
general debug or observability contract. Non-Dynamic-Narrative outcomes remain
unchanged unless their existing authority already specifies otherwise. The
scalar is not first derived after commit, requires no post-commit response
mutation or second database write, and is never reconstructed from the
successor View, fact-ring net growth, logs, UI totals, memory categories,
Provider responses, or generated keys. Missing, malformed, or out-of-range data
is invalid, not zero.

The Web summary remains associated with the exact Session and authoritative
revision. Established evidence is cleared across terminal action failure,
outcome uncertainty, post-commit View failure, manual Session replacement, API
client identity replacement, same-tab recovery restart, explicit Session
clear, stale or late completion, and unmount. Feedback privacy tests are
removal-sensitive: the prior evidence and every private canary must be absent,
not merely hidden by another rendering path. The existing `web/src/App.tsx`
production behavior already enforced these boundaries; the current correction
strengthens its regression evidence without changing that file.

Historical implementation entered commit `7ceb93e` and was pushed, while its
pre-publication procedural compliance remains unproven. The six-path
recovery/sanitization correction was independently approved under
`DYNAMIC_NARRATIVE_D1_COMMITTED_RESPONSE_RECOVERY_SANITIZATION_CORRECTION_REVIEW_APPROVED`
and the three-document reconciliation was independently approved under
`DYNAMIC_NARRATIVE_D1_POST_PUBLICATION_DOCUMENTATION_RECONCILIATION_REVIEW_APPROVED`.
Both are published in `12485f309860c496ff4aebae0e5e834779e485d7`; the
correction is no longer unstaged, and the reconciliation no longer awaits
approval. Neither review nor publication retroactively satisfies a historical
gate. The published correction introduced no route, error code, new public
`turn_id` field, DTO, response shape, OpenAPI schema, database schema, or
migration.

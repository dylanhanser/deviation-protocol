# Public Client Contract

Phase 3.0 defines the server-owned read contract for a shared Web client and a
future desktop wrapper. It does not provide public identity, abuse controls,
deployment, a browser application, or a desktop adapter. The default principal
is still the fixed `demo-player`/`demo-dev-only` identity and is unsafe for an
Internet-facing deployment.

This document also defines the bounded public-contract candidate for the
P5-S2 Player Character creation/replay route. The document does not itself
implement or activate that route. At this candidate's authoring baseline,
P5-S1's owned read is the only activated public Player Character operation;
later acceptance, implementation, integration, and publication state must be
established from applicable exact-candidate review evidence and Git history.

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

Any separately authorized P5-S2 implementation must expose exactly this normal
application OpenAPI operation:

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

This is the exact P5-S2 OpenAPI shape proposed by this contract candidate.
Candidate acceptance is established only by applicable
exact-candidate review evidence. It is distinct from runtime exposure: this
document does not register the operation, and whether a later normal
application exposes it must be established from applicable implementation and
Git history. The independent Demo does not gain the route or advertise it
merely because this contract exists.

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

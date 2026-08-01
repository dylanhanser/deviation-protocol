# Structured Player Character P5-S3 Retirement Activation Implementation Plan

## 1. Status, purpose, and present authority

Status: **Plan approved. The first, first-corrected, and re-corrected local
implementation candidates each received a fresh `CHANGES_REQUIRED` review. The
third review found no demonstrated production-code defect and requested stronger
SQL-race, durable-state, complete unit/OpenAPI, and documentation-history
evidence. The later evidence candidate's receipt-add 1062 depended on rolling
back the original mutation transaction and resuming stale in-memory work. A
focused investigation returned
`P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`. The
present acceptance-boundary-corrected unstaged local candidate instead requires
normal HTTP serialization evidence and explicitly labelled defensive fault
injection. Correction validation completed locally (canonical Offline 1,814
passed/124 expected skips, MySQL 136 passed, and Full 1,937 passed/one opt-in
  Provider skip). Its focused final independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED`, finding no
  material scoped defect. The accepted real-MySQL evidence proves aggregate-lock
  serialization, exact replay or ordinary idempotency conflict, and one durable
  mutation; defensive fault injection proves bounded recovery only, and the
  unreachable receipt-add race is not a requirement. P5-S3 is independently
  approved and eligible for exact-scope commit; P5-S4 and all unrelated deferred
  work have not begun. Push, deployment, release, runtime activation, and
  Provider work remain deferred.**

This document is the dedicated implementation-plan candidate for **P5-S3 —
narrow normal-application public activation of controller-authorized Player
Character retirement**. It specifies the single corrected-candidate route:

```http
POST /v1/player-characters/{player_character_id}/retirement
```

The approved plan is now implemented only as an unstaged local candidate. It
does not authorize its own independent implementation approval, staging,
commit, push, publication, release, deployment, or activation beyond the
normal application's candidate route. The six-file documentation candidate was:

1. `PLANS.md`;
2. `docs/architecture.md`;
3. `docs/public_client_contract.md`;
4. `docs/structured_player_character_contract.md`;
5. `docs/structured_player_character_implementation_plan.md`; and
6. this new document.

The sole operative successful verdict for independent review of this exact
six-file plan candidate is:

```text
STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED
```

This drafting task names that verdict but does not issue it. Historical P5-S1,
P5-S2, Phase 3, P4-S1, generic `APPROVED`, candidate-complete, implementation-
review, amendment, status-correction, or differently named tokens cannot
satisfy this gate.

## 2. Authority scope and precedence

This plan owns only the exact P5-S3 transport, safe public mapping, later path
budget, evidence allocation, verification, and handoff gate. It does not amend
the frozen product lifecycle or Run authority.

Precedence is:

1. [Structured Player Character Contract](structured_player_character_contract.md)
   and [Final Narrative Experience and Long-Term Systems](final_narrative_experience.md)
   for frozen lifecycle, identity, controller-binding, continuity, and product
   authority;
2. [Public Client Contract](public_client_contract.md), including the narrow
   P5-S3 amendment in this candidate, for public wire/API authority;
3. [Run Protocol](run_protocol.md), completed P4-S1, and its binding authority
   for Run ownership, active-binding evidence, lock order, line ending, and
   binding historicalization;
4. [Architecture](architecture.md), committed implementation, and the parent
   [Structured Player Character Downstream Implementation Plan](structured_player_character_implementation_plan.md)
   for repository-specific behavior;
5. [PLANS.md](../PLANS.md) for roadmap and status; and
6. [Codex Workflow](engineering/codex_workflow.md) and
   [engineering guardrails](engineering/guardrails.md) for process and safety.

A conflict is a stop condition. Later implementation must not weaken or
reinterpret a higher authority merely to fit this plan.

## 3. Verified planning baseline and predecessor status

This candidate was drafted from the required clean local baseline:

| Fact | Required and inspected value |
| --- | --- |
| Branch | `main` |
| `HEAD` | `4ba66d8f277988325795c905fdf6fd9e416d7457` |
| Local `main` | `4ba66d8f277988325795c905fdf6fd9e416d7457` |
| Local `origin/main` tracking ref | `4ba66d8f277988325795c905fdf6fd9e416d7457` |
| Ahead/behind | `0/0` |
| Parent of `HEAD` | `606e86534ef7fdd87f21efbb54de68b346bb5a7e` |
| Worktree/index | Clean; no modified, untracked, staged, unmerged, or active Git-operation state |
| Network action | No fetch or other remote contact |

P5-S1 is published at
`5955c47eac07429107b93ef85da6a055bd2044ef`. The P5-S2 contract is published at
`245caff3903666fcd2dd9a318785f323117deb24`; its implementation was
independently approved, committed, and published at the planning baseline
`4ba66d8f277988325795c905fdf6fd9e416d7457`. P5-S2 supplies the active public
baseline for raw JSON acquisition, exact header parsing, safe envelopes,
projection, OpenAPI component installation, conditional normal composition,
and Demo non-activation.

Any relevant baseline change before plan review, approval, implementation,
staging, or commit requires the pending-plan baseline-invalidation assessment in
the workflow. A factual change invalidates locked hashes and requires an updated
candidate and fresh independent review.

## 4. Exact product outcome

P5-S3 has one outcome:

> An authenticated controller may explicitly retire an owned, active, unbound
> canonical Player Character through one normal-application route. Committed
> success preserves character identity and controller binding, changes
> lifecycle from `active` to `retired`, advances the canonical revision exactly
> once, and reuses the existing durable mutation receipt and replay protocol.

An actively Run-bound character is not retired. The existing P4-S1
`ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` guard rejects the
operation before any Player Character or Run write. Ending a Run/line and
historicalizing its binding remain later Run-owned work.

P5-S3 is not a general character-mutation API.

## 5. Included scope and explicit exclusions

### 5.1 Included

- the single normal-application retirement route;
- dependency-derived trusted principal and existing service resolution;
- exact owned-path, JSON, explicit-confirmation, and operation-ID parsing;
- construction of the existing `CharacterMutationCommand` for `RETIRE`;
- at most one call to `PlayerCharacterService.mutate`;
- safe translation of the existing mutation result and decisions;
- the existing four-field `PlayerCharacterSelfProjection` on success/replay;
- exact OpenAPI declaration;
- focused API, composition, Demo, Run-inventory, and real-MySQL evidence; and
- canonical documentation synchronization after later implementation.

### 5.2 Excluded

P5-S3 does not include:

- final death;
- reactivation or authorized continuity return;
- general character updates, patches, or a generic mutation endpoint;
- binding, unbinding, rebinding, replacement, switching, transfer, shared
  control, or ownership recovery;
- deletion, listing, search, or administration;
- retirement of an actively bound character;
- ending or terminating a Run or continuous story line;
- historicalizing, clearing, or changing a Run binding;
- Run lifecycle redesign or the unimplemented `pre_first_turn -> active`
  transition;
- frontend, Web, browser, or Demo activation;
- Provider or narrative integration;
- production authentication, credentials, CORS, abuse controls, rate limits,
  deployment, or Internet readiness;
- scenario, world, NPC, memory, relationship, combat, content, or broader
  gameplay work;
- schema, ORM, migration, repository, Unit-of-Work, receipt, CAS, transaction,
  dependency, or lockfile redesign;
- generic retry, commit retry, policy retry, or uncertain-commit recovery;
- a P4-S2 objective; or
- unrelated refactoring, cleanup, or documentation rewriting.

## 6. Inspected committed prerequisites and no-defect finding

The baseline already contains every non-transport prerequisite:

- `PlayerCharacterService.mutate` resolves the trusted controller, locks and
  validates the current character, checks stored ownership before receipt
  disclosure, rejects an exhausted expected revision before fingerprint or
  receipt work, evaluates replay before stale revision only after that capacity
  gate succeeds, dispatches one policy, validates the complete successor,
  appends history, CAS-updates current state, inserts one mutation receipt, and
  commits once;
- `CharacterMutationCommand`, `PlayerConfirmation`,
  `ApplicableCharacterReference`, `PlayerCharacterOperationId`, and
  `player-character.mutate/v1` already define the exact typed command and
  operation identity;
- `mutation_fingerprint` already binds target, contract, expected revision,
  applicable reference, namespace, kind, and complete confirmation;
- `RetirePlayerCharacterPolicy` already requires `active`, exact revision and
  reference, exact confirmation binding, and produces one `retired` successor
  with preserved identity/controller binding and one successor revision;
- durable mutation receipt creation, exact replay, incompatible reuse,
  receipt-integrity checks, CAS loss, original-error propagation, and the one
  admitted mutation-receipt uniqueness-winner recovery already exist;
- normal composition sets `binding_integrity_guard_enabled=True` and reuses the
  existing P4-S1 `get_active_for_player_character_for_update` seam; and
- P5-S2 already supplies the public header parsing, raw-body acquisition,
  safe envelope, projection, normal/Demo registration, OpenAPI helper, and test
  organization to extend.

No concrete prerequisite defect was found. Therefore later P5-S3 implementation
must not change:

- `application/player_character_service.py`;
- `application/player_character_operations.py`;
- `domain/player_character_policies.py`;
- `application/ports.py`;
- any repository, Unit of Work, persistence codec, ORM model, migration, schema,
  or transaction path; or
- either existing error module.

If implementation cannot satisfy this plan without such a change, it must stop
as blocked and return to plan authority rather than widen the budget.

## 7. Exact route, registration, authentication, and target

### 7.1 Method and route

The exact operation is:

```http
POST /v1/player-characters/{player_character_id}/retirement
```

`PATCH`/`PUT` on the character resource, `DELETE`, `/retire`, `/mutations`, a
body-selected action, and every other route are rejected alternatives. The
selected noun subresource is the narrowest operation-specific addition to the
existing Player Character API family without implying general mutation.

### 7.2 Registration boundary

The route is declared inside the existing
`if services is None or services.player_character_service is not None` block in
`create_app`, beside P5-S1 and P5-S2. Consequently:

- the normal default application registers it;
- an explicitly composed normal application registers it only when the
  canonical Player Character service is present;
- Demo, whose service is `None`, registers no Player Character path or schema;
- public Run routes gain nothing; and
- no frontend, browser, Web, or administration surface is created.

Registration performs no Unit-of-Work construction, SQL, ID issuance, mutation,
Provider call, or other side effect.

### 7.3 Principal, ownership, and non-enumeration

The endpoint receives exactly:

- `Request` for raw headers/body;
- `player_character_id: PlayerCharacterPathId`;
- `idempotency_key: PlayerCharacterIdempotencyKeyHeader`;
- `principal: RequestPrincipal = Depends(get_current_principal)`; and
- `service: PlayerCharacterService = Depends(get_player_character_service)`.

No body, path, query, or header value supplies controller identity. The
dependency-provided principal is passed unchanged to the service; the existing
resolver and current stored binding remain the only ownership authority.

Missing, non-owned, invalidly owned, and unresolved targets converge on the
existing 404 envelope. A malformed path receives the standard sanitized 422
before lookup, revealing no resource fact. There is no 401/403 or production
security scheme because no production authentication transport exists.

### 7.4 Canonical path identifier

The framework-decoded path value must be ASCII, 1–128 characters, and match
`^[A-Za-z0-9][A-Za-z0-9_.:-]*$`. The exact decoded value is then constructed as
`PlayerCharacterId(value=player_character_id)`. There is no trim, case-fold,
Unicode normalization, semantic parsing, second decode, body override, or query
fallback.

## 8. Exact request and transport parsing

### 8.1 Media type and operation header

The route reuses the existing P5-S2 raw transport helper behavior without
relaxation:

1. require exactly one raw `Content-Type` occurrence;
2. decode it as ASCII;
3. take the token before the first semicolon, strip only SP/HTAB, lowercase it,
   and require `application/json`;
4. require exactly one raw `Idempotency-Key` occurrence;
5. decode its bytes as ASCII and require 1–128 bytes, the exact pattern
   `^[A-Za-z0-9][A-Za-z0-9_.:-]*$`, and equality with the declarative header;
6. perform no trim, case-fold, normalization, decoding, or alternate carrier;
   and
7. construct exactly one `PlayerCharacterOperationId` before body receipt.

The existing private `_validate_player_character_creation_transport` helper is
reused unchanged despite its historical P5-S2 name. Renaming or generalizing it
is not necessary for this slice and would create avoidable P5-S2 churn.

Every invalid media type or operation header produces only the standard 422
envelope before service invocation.

### 8.2 Public request DTO

Add one strict public DTO in `api/main.py`:

```python
class PlayerCharacterRetirementRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        revalidate_instances="always",
    )

    contract_version: PlayerCharacterContractVersion
    expected_revision: PlayerCharacterRevision
    confirm_retirement: Literal[True]
```

Its complete JSON form is:

```json
{
  "contract_version": "structured-player-character/v1",
  "expected_revision": {
    "value": 1
  },
  "confirm_retirement": true
}
```

All three fields are required and non-null. `contract_version` has the sole
supported value `structured-player-character/v1`. `expected_revision` contains
exactly `value`, a strict JSON integer in the existing positive signed-64-bit
revision domain. `confirm_retirement` must be the JSON boolean literal `true`.
The values `false`, `1`, `"true"`, null, an object, or an array are invalid.

There are no defaulted fields, aliases, alternate confirmation strings, generic
action values, source-reference fields, controller fields, target fields,
operation-ID body fields, Run fields, or hidden body authority.

### 8.3 Duplicate JSON members and JSON-mode validation

The retirement parser performs one narrow duplicate-member preflight using the
standard-library `json.loads(raw_body, object_pairs_hook=...)`. The private
object-pairs hook rejects any repeated decoded member name at any nesting depth;
the parsed object is discarded. This is transport-shape validation only, not a
second DTO or domain validator.

After that preflight, the exact original bytes are passed to
`PlayerCharacterRetirementRequest.model_validate_json(raw_body)`. The helper
catches only the standard JSON/Unicode/duplicate-member/Pydantic validation
failures needed to invoke `_request_validation_failure`. It does not catch
arbitrary body-read failures, internal defects, `BaseException`, or
`CancelledError`.

Missing/empty/truncated/malformed JSON, top-level non-objects, unknown fields,
duplicate fields, missing fields, null, wrong types, unsupported versions,
invalid revision objects, and any confirmation other than literal true receive
the same 422 without field details. No partial object is salvaged and the
service is not called.

### 8.4 Body acquisition and size

After dependencies, path, raw media type, raw operation header, and one
operation-ID construction succeed, the route executes exactly one
`raw_body = await http_request.body()` application call. No production code
streams, decodes, rereads, or replaces the body. The duplicate preflight and
Pydantic JSON-mode validation use those cached bytes.

P5-S3 inherits P5-S2's explicit size boundary: there is no raw transport-body
or `Content-Length` cap. `Request.body()` buffers the full raw body. The small
typed DTO bounds accepted semantic content but whitespace and rejected raw
input can still be large. Full buffering and the absent raw cap are residual
risks; implementation may not silently invent another limit.

### 8.5 Exact validation order

The route order is:

```text
raw ASGI request
-> trusted principal and service dependencies
-> declarative path/header validation
-> route entry
-> raw Content-Type validation
-> raw Idempotency-Key occurrence/byte/equality validation
-> one PlayerCharacterOperationId construction
-> one Request.body() call
-> duplicate-member preflight
-> PlayerCharacterRetirementRequest.model_validate_json
-> existing retirement command construction
-> at most one PlayerCharacterService.mutate call
-> success projection or safe decision translation
```

No alternative precedence is left open.

## 9. Thin API command construction and flow

### 9.1 Fixed trusted source

The API uses the exact fixed internal source reference:

```python
AuthoritySourceRef(value="source.public-player-character-retirement")
```

It is never submitted or returned. It records that the accepted explicit
choice entered through this trusted public route; it is not client authority.

### 9.2 Existing retirement command

After parsing, construct exactly one existing `CharacterMutationCommand`:

```python
CharacterMutationCommand(
    contract_version=request.contract_version,
    command_kind=PlayerCharacterMutationKind.RETIRE,
    target_player_character_id=target,
    expected_revision=request.expected_revision,
    applicable_reference=ApplicableCharacterReference(
        player_character_id=target,
        contract_version=request.contract_version,
        record_revision=request.expected_revision,
    ),
    confirmation=PlayerConfirmation(
        player_character_id=target,
        expected_revision=request.expected_revision,
        operation_id=operation_id,
        mutation_kind=PlayerCharacterMutationKind.RETIRE,
        source_reference=_PUBLIC_RETIREMENT_SOURCE_REFERENCE,
    ),
    final_death_evidence=None,
)
```

The path supplies the target; the body supplies only version, expected revision,
and explicit confirmation. Server construction binds confirmation to target,
revision, operation ID, kind, and source. The API does not duplicate policy.

### 9.3 One service call

Invoke exactly:

```python
await service.mutate(
    principal,
    operation_id=operation_id,
    command=command,
)
```

The route invokes this method zero times on transport/DTO/command-construction
failure and at most once otherwise. It never invokes `get_owned`, `create`, a
repository, a Run service, or another application service.

### 9.4 API-owned and non-API-owned work

The API owns only parsing, dependency resolution, safe typed mapping, one
service invocation, result projection, and safe error mapping. It does not own
repositories, receipts, transaction entry/exit, rollback, commit, lock order,
CAS, active-binding queries, retries, race recovery, uncertain-commit handling,
or domain policy.

## 10. Existing mutation, receipt, and replay semantics

### 10.1 Namespace, receipt key, and fingerprint

Reuse `CharacterOperationNamespace.MUTATE_V1`, whose value is
`player-character.mutate/v1`. The existing receipt key is the exact target
`player_character_id`, namespace, and operation ID. Current controller
authorization precedes lookup and stored-result disclosure.

Strict transport and DTO validation remain at their existing API boundaries.
Inside the application service, trusted controller resolution, current-record
locking and validation, stored-owner authorization, and typed command and
operation-ID revalidation remain the pre-receipt boundaries. The existing
successor-capacity gate then rejects
`expected_revision = 9223372036854775807` as `REVISION_EXHAUSTED` before
`MutationReceiptKey` construction, request-fingerprint construction, durable
receipt lookup, exact-replay evaluation, different-fingerprint comparison,
current-state stale-revision evaluation, active-binding evaluation, lifecycle
evaluation, or any write.

The existing fingerprint inputs are frozen unchanged:

- `applicable_reference` containing exact target, contract version, and
  expected revision;
- `command_kind=RETIRE`;
- exact contract version;
- expected revision integer;
- target Player Character ID;
- `operation_namespace=player-character.mutate/v1`; and
- complete confirmation containing `RETIRE`, operation ID, target ID, fixed
  source reference, and expected revision.

The API does not compute, serialize, store, compare, or expose the fingerprint.
For a maximum-revision request whose fields would differ from an earlier
successful request, no different fingerprint is constructed or compared; the
capacity gate has already returned `REVISION_EXHAUSTED`.

### 10.2 Exact replay

After current-owner authorization and only after every existing pre-receipt
validation and revision-capacity gate succeeds, an existing receipt is
evaluated before current-state stale-revision or lifecycle rejection. Exact key
and fingerprint reuse returns its original validated `MutationSuccessResult`.

Exact replay performs no policy call, active-binding query for a new operation,
successor construction, history append, current-row CAS, receipt insertion,
revision increment, or commit. It cannot cause a second lifecycle transition.
The response is the same public projection semantics as first success.

Replay remains the original retirement result even if a later separately
authorized mutation advanced the character. It is not a current-state claim;
the owned GET remains the current projection.

A successfully executed retirement cannot have used the exhausted maximum as
its expected revision because that value has no representable successor. Its
exact replay therefore carries the original valid, non-exhausted request and
continues to use the ordinary replay path.

### 10.3 Incompatible operation-ID reuse

For a valid, non-exhausted request that has passed all pre-receipt gates, the
same target/namespace/operation ID with a different fingerprint returns
`IDEMPOTENCY_CONFLICT` before current-state stale/lifecycle policy and makes no
write. No stored command, result, receipt, fingerprint, current state, or
controller data is returned.

The same header value on a different character uses a different existing
receipt key and is not a cross-character receipt lookup. The same value never
grants ownership.

### 10.4 New operation after retirement

A new operation ID with an ordinary, non-exhausted applicable revision has no
compatible receipt. If the character is already `retired` or `deceased`,
`RetirePlayerCharacterPolicy` returns `INVALID_TRANSITION`. The API returns the
fixed lifecycle 409. The revision, record, binding, history, and receipt
families remain unchanged. Rejection does not create a failure receipt.

With the maximum expected revision, the capacity gate returns
`REVISION_EXHAUSTED` before receipt or lifecycle evaluation. The API therefore
returns the fixed revision 409, not the lifecycle conflict.

### 10.5 Normative precedence matrix

| Case | Exact conditions and ordering | Internal/public result | Required preservation |
| --- | --- | --- | --- |
| A — ordinary exact replay | Original successful operation ID; identical valid request; non-exhausted expected revision; all pre-receipt gates pass; stored fingerprint matches | Existing `EXACT_REPLAY`; HTTP 200 with the stored original retirement projection | No second policy call, mutation, history append, CAS, receipt add, commit, or revision increment |
| B — ordinary different-fingerprint reuse | Existing operation ID; valid non-exhausted request; request fields differ from the stored successful request; all pre-receipt gates pass; stored fingerprint differs | `IDEMPOTENCY_CONFLICT`; HTTP 409 `IDEMPOTENCY_CONFLICT` | No mutation, new receipt, receipt alteration, or revision change |
| C — existing operation ID with maximum expected revision | Existing operation ID; request carries `expected_revision = 9223372036854775807`; its fields would differ from the earlier successful request; capacity gate rejects before fingerprint construction or receipt lookup | `REVISION_EXHAUSTED`; HTTP 409 `PLAYER_CHARACTER_REVISION_CONFLICT`; not idempotency conflict | Original receipt and canonical state remain unchanged |
| D — new operation after retirement with ordinary revision | New operation ID; valid non-exhausted applicable revision; no receipt preempts evaluation; retired lifecycle is evaluated | `INVALID_TRANSITION`; HTTP 409 `PLAYER_CHARACTER_LIFECYCLE_CONFLICT` | No receipt or state change |
| E — new operation after retirement with maximum revision | New operation ID; request carries the maximum expected revision; capacity gate rejects before receipt and lifecycle evaluation | `REVISION_EXHAUSTED`; HTTP 409 `PLAYER_CHARACTER_REVISION_CONFLICT`; not lifecycle conflict | No receipt or state change |

No successful mutation or durable success receipt can be created from a
request rejected by revision exhaustion. Receipt-first behavior is conditional
on successful completion of every existing pre-receipt validation and
revision-capacity gate; P5-S3 does not redesign that committed order.

### 10.6 First success, CAS, rollback, and recovery

A genuinely new accepted retirement:

1. locks and validates the current owned character;
2. validates receipt absence and exact expected revision;
3. proves no active binding through the existing P4-S1 seam;
4. evaluates exactly one existing retirement policy;
5. validates the complete successor and preserved identity, contract, and
   controller binding;
6. appends one immutable revision;
7. CAS-updates current state from the exact prior revision;
8. inserts one immutable success receipt;
9. commits once; and
10. returns only after commit succeeds.

The resulting revision is exactly expected revision plus one. A rejection or
pre-commit failure changes no durable record/revision/receipt. CAS false returns
the stale protocol decision from inside the uncommitted Unit of Work, whose exit
rolls back the already flushed history.

Only the existing exact `MutationReceiptUniquenessConflictError` escaping from
the precise receipt-add flush with the same recorded exception instance may
authorize one disposed-then-fresh recovery Unit of Work. Recovery re-resolves
authority, locks current state, and rereads only the receipt; it can return a
durable exact winner, incompatible conflict, or integrity failure. It does not
write or commit. There is no third Unit of Work.

This is bounded defensive behavior, not a currently reachable race between two
legitimate retirement requests. The production mutation transaction's first
aggregate read locks `player_character_current` with `FOR UPDATE`; a second
normal writer waits there before receipt lookup, policy, revision write, CAS,
or receipt add. Existing service tests cover this recovery using explicitly
labelled narrow receipt-add fault injection. Direct repository duplicate-flush
tests are synthetic out-of-topology constraint-translation evidence only.

All other repository, binding-evidence, rollback, close, or commit failures
preserve the original exception internally and authorize no recovery. Generic
retry and uncertain-commit recovery remain prohibited.

Real MySQL 1062 receipt-add race evidence becomes mandatory only if a future
composed runtime writer or changed transaction topology can legitimately reach
the receipt uniqueness boundary without first serializing on the aggregate
lock. This plan neither approves nor requires such a writer or topology.

### 10.7 Uncertain commit

If `commit()` raises after durability may have occurred, the request receives
the sanitized 500 with no success, replay, or exactly-once claim. The route and
service do not reread. A later client retry may independently discover a
durable receipt; that does not retroactively make the original response a
success.

## 11. Active-binding guard

Retirement is allowed only for an owned canonical character that is both
`active` and unbound from a current active Run/line.

For a genuinely new `RETIRE` operation, the existing service holds the Player
Character current lock and calls the P4-S1
`get_active_for_player_character_for_update` seam. Valid active binding
evidence returns the existing
`PlayerCharacterPolicyCode.ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED`
decision before domain policy or any write.

The API maps that decision to:

```text
409 PLAYER_CHARACTER_ACTIVE_BINDING_CONFLICT
Player character is bound to an active Run
```

On this rejection:

- the canonical character and revision are unchanged;
- no history or mutation receipt is written;
- the Run, Run version, binding, and binding history are unchanged;
- no commit, compensating action, unbind, or retry occurs; and
- no Run endpoint or service is invoked by the API.

Malformed, contradictory, or corrupt binding evidence remains an internal
integrity failure and becomes only the sanitized 500. It is never treated as
unbound.

Ending a Run line and making the binding historical must eventually be one
Run-owned atomic transaction. P5-S3 neither designs nor implements it.

## 12. Exact success contract

Both first committed success and exact replay return:

- status `200 OK`;
- media type `application/json`;
- response model `PlayerCharacterSelfProjection`;
- response description `Player Character retired or exactly replayed.`; and
- no `Location` header.

The projection contains exactly:

1. `player_character_id` — the existing nested opaque ID;
2. `contract_version` — `structured-player-character/v1`;
3. `record_revision` — the existing nested revision; first success is exactly
   expected plus one, replay is the stored original result; and
4. `lifecycle` — `retired`.

The API maps those four fields from `MutationSuccessResult` field by field. It
does not create another character representation and omits result schema,
command kind/result, operation/replay metadata, controller binding, authority
provenance, source reference, receipt, fingerprint, Run/binding, transaction,
CAS, or recovery data.

## 13. Exact safe error mapping

All promised errors use the existing `ErrorResponse` with only
`error.error_code` and `error.message`. Details are always omitted.

| Condition | Source decision/boundary | HTTP | Public code | Exact message |
| --- | --- | ---: | --- | --- |
| Invalid/missing/unmapped principal reaching resolution | `AUTHORIZATION_FAILED` | 404 | `PLAYER_CHARACTER_NOT_FOUND` | `Player character was not found` |
| Malformed path identifier | FastAPI path validation | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` |
| Missing or non-owned character; invalid/changed stored controller authority | `AUTHORIZATION_FAILED` | 404 | `PLAYER_CHARACTER_NOT_FOUND` | `Player character was not found` |
| Malformed body; missing/null/wrong type; unknown/duplicate field; unsupported version; invalid revision; missing, false, malformed, or incorrectly typed confirmation | Retirement parser | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` |
| Invalid/missing/duplicate media type or operation ID | Existing raw/declarative transport validation | 422 | `REQUEST_VALIDATION_FAILED` | `Request validation failed` |
| Maximum `expected_revision = 9223372036854775807` | Pre-fingerprint/pre-receipt protocol `REVISION_EXHAUSTED` | 409 | `PLAYER_CHARACTER_REVISION_CONFLICT` | `Player character revision does not permit retirement` |
| Ordinary stale expected revision or CAS loss after pre-receipt gates succeed | Protocol/policy `STALE_REVISION` | 409 | `PLAYER_CHARACTER_REVISION_CONFLICT` | `Player character revision does not permit retirement` |
| Already retired/deceased or otherwise invalid lifecycle after an ordinary non-exhausted request reaches policy | Policy `INVALID_TRANSITION` | 409 | `PLAYER_CHARACTER_LIFECYCLE_CONFLICT` | `Player character cannot be retired` |
| Valid current active binding | Policy `ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` | 409 | `PLAYER_CHARACTER_ACTIVE_BINDING_CONFLICT` | `Player character is bound to an active Run` |
| Same operation ID, different fingerprint after every pre-receipt gate succeeds for a valid non-exhausted request | Protocol `IDEMPOTENCY_CONFLICT` | 409 | `IDEMPOTENCY_CONFLICT` | `Idempotency key was reused` |
| Safe domain/application rejection | Exactly `STALE_REVISION`, `REVISION_EXHAUSTED`, `INVALID_TRANSITION`, or `ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` | Corresponding 409 | Corresponding fixed code | Corresponding fixed message |
| Stored receipt integrity failure | `STORED_RECEIPT_INTEGRITY_FAILURE` | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` |
| Any target/reference/confirmation mismatch escaping server construction, wrong namespace, impossible decision, contradictory success, or other application/domain outcome | Private translator invariant | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` |
| Repository, binding-evidence, persistence, rollback, close, dependency, composition, projection, or other infrastructure failure | Original exception | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` |
| Commit failure or uncertain commit | Original exception | 500 | `INTERNAL_SERVER_ERROR` | `Internal server error` |

The translator accepts only `MUTATE_V1` and the exact decisions above. It maps
recognized safe conflicts through the existing `error_response` helper. All
other decisions raise one fixed internal `RuntimeError` for the existing
unknown handler. Unexpected ordinary exceptions retain their identity and are
not relabeled. Cancellation propagates and has no promised response.

No internal exception text, SQL, constraint, path, stack trace, ownership fact,
controller/principal identifier, submitted value, operation key, receipt,
fingerprint, policy trace, source reference, Run ID, binding evidence, CAS
state, transaction state, or recovery detail is public.

### 13.1 Error-module determination

No error-module change is required. `src/deviation_protocol/api/errors.py`
already supplies `error_response`, `ErrorResponse` serialization through the
same envelope, sanitized request validation, existing not-found/idempotency
handlers, and the fixed unknown handler. `api/main.py` must import and call
`error_response` from a private retirement decision translator. Neither
`api/errors.py` nor `application/errors.py` is in the later path budget.

## 14. Exact OpenAPI contract

The operation must publish exactly:

| Property | Frozen value |
| --- | --- |
| Path/method | `POST /v1/player-characters/{player_character_id}/retirement` |
| `operationId` | `retire_player_character` |
| Tag | `player-characters` |
| Summary | `Retire a Player Character` |
| Path parameter | Required `player_character_id`, 1–128, `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` |
| Header | Required `Idempotency-Key`, 1–128, same exact pattern |
| Request body | Required `application/json` reference to `PlayerCharacterRetirementRequest` |
| Success | `200 application/json`, reference to `PlayerCharacterSelfProjection`, description `Player Character retired or exactly replayed.` |
| Errors | Exactly 404, 409, 422, and 500, each `application/json` reference to `ErrorResponse` |
| Security | No production security scheme |

Because runtime parsing uses raw bytes, add
`_PLAYER_CHARACTER_RETIREMENT_OPENAPI_EXTRA` with a single required
`application/json` request body reference. Replace the creation-only installer
with one `_install_player_character_openapi_schemas` helper that preserves the
existing failure-atomic deep-copy/collision/reference checks and installs the
complete generated validation-schema component sets for both
`CharacterCreationCommand` and `PlayerCharacterRetirementRequest`. Call it once
only inside the conditional Player Character registration block. Existing
P5-S2 schema and behavior must remain byte-semantically unchanged.

The retirement request schema shows all three required fields,
`additionalProperties: false`, the exact contract-version enum, the nested
strict revision schema, and a boolean `const: true` for confirmation. Runtime
duplicate-member rejection and raw-size behavior are described textually; the
schema must not claim that OpenAPI enforces them.

The operation description states all of these facts:

1. controller identity is dependency-derived;
2. the operation ID is required but is not authorization;
3. `confirm_retirement` must be literal true;
4. only an owned, active, unbound character with a representable successor may
   retire;
5. first success and exact replay share 200 and the same projection semantics;
6. replay returns the original retirement result and GET supplies current state;
7. maximum expected revision returns the revision conflict before fingerprint,
   receipt, idempotency, binding, or lifecycle evaluation;
8. active binding rejects without changing the character, Run, or binding;
9. the route does not end a Run or historicalize its binding;
10. no receipt, fingerprint, controller, provenance, Run, persistence,
   transaction, or recovery data is public; and
11. the fixed development principal is not production authentication and the
    route does not make the application Internet-ready.

OpenAPI must not imply final death, deletion, reactivation, continuity return,
general mutation, binding change, Run termination, or Demo/frontend activation.
The normal route inventory gains only the retirement POST; Demo and public Run
inventories gain no route.

## 15. Closed later implementation candidate path budget

The complete later implementation candidate may change exactly 11 paths: five
production/test paths plus six canonical documentation synchronization paths.

### 15.1 Production path — exactly one

1. `src/deviation_protocol/api/main.py`

This file adds only the strict retirement DTO/parser, duplicate-member
preflight, fixed source/command mapper, mutation result projection, safe
decision translator, route, OpenAPI metadata/components, and required imports.
It must mechanically generalize the existing OpenAPI installer exactly as
section 14 specifies. No other production file changes.

### 15.2 Test paths — exactly four

2. `tests/unit/test_player_character_api.py`
3. `tests/integration/test_mysql_player_character_api.py`
4. `tests/unit/test_run_composition.py`
5. `tests/unit/test_demo_composition.py`

### 15.3 Documentation synchronization paths — exactly six

6. `PLANS.md`
7. `docs/architecture.md`
8. `docs/public_client_contract.md`
9. `docs/structured_player_character_contract.md`
10. `docs/structured_player_character_implementation_plan.md`
11. `docs/structured_player_character_p5_s3_implementation_plan.md`

After verified implementation, these documents may record only proven P5-S3
implementation, evidence, review status, and preserved exclusions. No wire
decision changes. Guardrails change only if a confirmed reusable defect requires
returning to authority; they are not pre-authorized.

### 15.4 Explicit path-budget findings

- No error module is included.
- No schema, ORM, migration, repository, Unit of Work, receipt, CAS,
  transaction, application service, operation-helper, domain policy, port,
  dependency, frontend, Demo runtime, Run service, Provider, or lockfile path is
  included.
- A need for any twelfth path is a blocker, not implied authorization.
- A prerequisite application/domain/persistence defect is a blocker and must
  not be repaired inside P5-S3.

## 16. Required focused API evidence

The corrected precedence must be allocated across only the two already-budgeted
API test paths:

| Case | `tests/unit/test_player_character_api.py` | `tests/integration/test_mysql_player_character_api.py` |
| --- | --- | --- |
| A — ordinary exact replay | Project the existing retirement success result as the same 200 four-field body with no replay metadata and at most one service call | Retry the original valid non-exhausted request and prove the stored retirement projection plus no second mutation, revision increment, receipt, policy execution, or commit |
| B — ordinary different-fingerprint reuse | Map ordinary `IDEMPOTENCY_CONFLICT` to its exact sanitized 409 | Reuse the successful operation ID with an ordinary valid non-exhausted request whose fields differ; prove idempotency 409 and unchanged canonical/receipt families |
| C — existing operation ID with maximum revision | Map `REVISION_EXHAUSTED` to 409 `PLAYER_CHARACTER_REVISION_CONFLICT`, never idempotency conflict | Reuse the successful operation ID with maximum expected revision; prove revision 409, no receipt lookup-based conflict exposed, no new or altered receipt, no canonical mutation, and no revision change |
| D — new operation after retirement with ordinary revision | Map `INVALID_TRANSITION` to 409 `PLAYER_CHARACTER_LIFECYCLE_CONFLICT` | Use a new operation ID and ordinary applicable revision against the retired character; prove lifecycle 409 and no receipt or state change |
| E — new operation after retirement with maximum revision | Map `REVISION_EXHAUSTED` to 409 `PLAYER_CHARACTER_REVISION_CONFLICT`, never lifecycle conflict | Use a new operation ID and maximum expected revision against the retired character; prove revision 409 before receipt/lifecycle evaluation and no receipt or state change |

The already committed service-level
`test_mutate_revision_exhaustion_precedes_receipt_lookup` remains a mandatory
verification target for the pre-key/pre-lookup application order. It is not
duplicated or added to the modification budget. Focused service verification
must also retain the operation-level proof that maximum revision rejects before
fingerprint construction.

`tests/unit/test_player_character_api.py` must add substantive evidence for:

1. authorized retirement returns exact 200/application-json projection with
   target ID, v1 contract, expected-plus-one revision, and `retired` lifecycle;
2. the fake service receives the dependency principal, exact operation ID, and
   exact constructed `CharacterMutationCommand` once;
3. route signature has raw `Request`, path/header parameters, dependencies, no
   executable FastAPI body binding, and one body read;
4. literal `true` is accepted; missing, false, null, string, numeric, object,
   array, and duplicate confirmation are sanitized 422 before service;
5. duplicate JSON member names at the top level and nested revision level fail;
6. strict JSON rejects missing/empty/malformed/scalar bodies, unknown fields,
   wrong types, unsupported contract versions, invalid revisions, floats,
   booleans-as-integers, and extra nested fields;
7. exact P5-S2 raw `Content-Type` and `Idempotency-Key` occurrence, ASCII,
   length, alphabet, case preservation, no normalization, and precedence are
   preserved;
8. invalid/missing/unmapped principal, missing target, and non-owner decisions
   use the identical non-enumerating 404;
9. malformed path uses the sanitized 422 and never reaches service;
10. ordinary stale revision and exhausted maximum revision both map to the
    exact revision 409, while remaining distinct internal decisions;
11. maximum expected revision maps to revision conflict rather than
    idempotency or lifecycle conflict for both reused and new operation IDs;
12. invalid lifecycle for an ordinary non-exhausted new operation maps to the
    exact lifecycle 409;
13. active binding maps to the exact active-binding 409;
14. incompatible operation-ID reuse maps to the existing idempotency 409 only
    for an ordinary valid non-exhausted request after pre-receipt gates;
15. stored-receipt integrity, impossible namespace/decision/result, service,
    projection, body-read, dependency, and other ordinary failures sanitize to
    500 without internal text;
16. original exception identity remains available internally when exception
    propagation is inspected with raised app exceptions;
17. cancellation is not translated;
18. exact replay result is projected identically and creates no public replay
    metadata;
19. the OpenAPI path, operation ID, tag, summary, description, parameters,
    request schema, literal confirmation, response description/model, and exact
    404/409/422/500 envelopes are correct;
20. OpenAPI describes the maximum-revision public precedence without exposing
    receipts, fingerprints, or internal `REVISION_EXHAUSTED` as a public code;
21. OpenAPI contains no default validation schema, 201, 400, 401, 403, 415,
    Location header, security scheme, internal command/result/receipt schema, or
    unsupported lifecycle implication;
22. the combined OpenAPI installer remains failure-atomic, collision-safe,
    reference-complete, cache-stable, and P5-S2-compatible;
23. normal route registration contains P5-S1 GET, P5-S2 POST, and only the one
    new P5-S3 POST in the Player Character family;
24. Demo has no Player Character route or schema; and
25. no public Run, frontend, administration, final-death, reactivation,
    deletion, general update, binding, or other mutation route appears.

The at-most-one-service-call assertion applies to every service-reaching result
and rejection, not only the happy path.

## 17. Required real-MySQL API evidence

`tests/integration/test_mysql_player_character_api.py` must use the real
`PlayerCharacterService`, configured principal/controller resolution,
`SqlAlchemyUnitOfWork`, repositories, receipts, CAS, and P4-S1 Run evidence
seam. It must prove:

1. an owned active unbound character retires through the HTTP route;
2. the same `player_character_id`, contract version, and exact
   `controller_binding` persist;
3. lifecycle changes from active to retired;
4. revision advances exactly once and one immutable retirement revision is
   added;
5. exactly one durable mutation success receipt is created with the existing
   namespace/key/result semantics;
6. exact retry with the original valid non-exhausted operation ID/body returns
   an equal public response and causes no second history/current/receipt write,
   revision increment, policy execution, or commit;
7. the successful operation ID reused with an ordinary valid non-exhausted
   different request returns exact 409 `IDEMPOTENCY_CONFLICT` and leaves every
   durable family unchanged;
8. the successful operation ID reused with
   `expected_revision = 9223372036854775807` returns exact 409
   `PLAYER_CHARACTER_REVISION_CONFLICT`, not idempotency conflict, with no
   receipt-based conflict exposed, no receipt lookup through an instrumented
   repository wrapper, no new or altered receipt, no canonical mutation, and
   no revision change;
9. an ordinary stale expected revision returns exact revision 409 without
   durable mutation;
10. a new operation ID after retirement with an ordinary applicable revision
    returns lifecycle 409 without a second receipt or revision;
11. a new operation ID after retirement with maximum expected revision returns
    exact revision 409, not lifecycle conflict, before receipt/lifecycle
    evaluation and with no receipt or state change;
12. nonexistent and foreign-owned targets return the identical 404 and disclose
    no receipt or ownership fact;
13. an actively bound character returns active-binding 409 through the existing
    P4-S1 seam;
14. active-binding rejection leaves character current/history/revision/receipt,
    Run current/history/version/receipt, and binding evidence unchanged;
15. the API does not terminate the Run, historicalize the binding, invoke a
    compensating operation, or open an independent Run transaction;
16. a controlled pre-commit failure returns sanitized 500 and leaves the
    character, history, current row, receipt, controller binding, and Run
    evidence at their prior durable state;
17. a controlled uncertain commit returns sanitized 500, performs no recovery
    read or retry, makes no response durability claim, and uses no second/third
    Unit of Work;
18. counting wrappers show one initial Unit of Work for ordinary success,
    replay, safe rejection, and uncertain commit;
19. two normal identical HTTP retirements use distinct real MySQL connections
    and Unit of Work instances; the second is observed entering but not
    completing the delegated aggregate `FOR UPDATE` read while the first
    transaction remains open;
20. after the first commit, the identical waiter exact-replays the same safe
    projection, with exactly one policy evaluation, revision advance, mutation
    receipt, and durable retirement, and with no recovery UoW, duplicate
    mutation, receipt-add conflict, or MySQL 1062;
21. two normal HTTP requests with the same idempotency identity but a different
    fingerprint serialize at the same aggregate lock; after the winner commits,
    the loser returns ordinary public idempotency conflict without another
    policy evaluation or write;
22. fresh independent database sessions confirm the final current row, complete
    revision history, and exactly one mutation receipt after each concurrency
    case;
23. explicitly labelled narrow receipt-add fault injection proves that the
    failed mutation UoW is rolled back/disposed, exactly one fresh read-only
    recovery UoW re-resolves authority and rereads the durable receipt, and
    replay or fingerprint conflict follows without a third UoW, mutation retry,
    generic retry, recovery write/commit, or uncertain-commit recovery; and
24. SQL, constraints, controller IDs, binding IDs, receipts, fingerprints,
    internal exceptions, and database identity never enter public responses.

The test module may extend its existing cleanup scope for Run rows created by
the active-binding probe, but no shared fixture or production path may change.
All cleanup remains exact, owned, and restrictive-FK-safe.

## 18. Composition and non-activation evidence

### 18.1 `tests/unit/test_run_composition.py`

Update the exact normal route/method inventory to include only:

- P5-S1 `GET /v1/player-characters/{player_character_id}`;
- P5-S2 `POST /v1/player-characters`; and
- P5-S3 `POST /v1/player-characters/{player_character_id}/retirement`.

The test must continue to prove shared lazy composition, enabled P4-S1 guard,
no public Run route, no binding/lifecycle Run command, and no extra Player
Character method.

### 18.2 `tests/unit/test_demo_composition.py`

The Demo test must prove:

- `player_character_service is None`;
- no owned-read, creation, or retirement route/method is registered;
- no Player Character path or retirement request schema is in Demo OpenAPI;
- no frontend/button/browser behavior is introduced; and
- existing isolated Demo Provider/gameplay composition is unchanged.

The absence of a frontend path is also established by the closed later path
budget and a repository search showing no new `web/` change or caller.

## 19. Existing regression evidence that later implementation must run

P5-S3 reuses rather than rewrites committed authority. Later verification must
include applicable existing tests for:

- `RetirePlayerCharacterPolicy`, explicit bound confirmation, invalid
  lifecycle, stale/reference mismatch, revision exhaustion, identity and
  controller-binding preservation;
- mutation fingerprint vectors, receipt evaluation, exact replay, incompatible
  reuse, stored-result integrity, and replay after later revisions;
- `PlayerCharacterService.mutate` transaction order, CAS rollback, receipt-add
  recovery through the explicitly labelled narrow fault injection in
  `test_exact_mutation_receipt_conflict_recovers_one_committed_winner`, original
  exception provenance, no third Unit of Work, uncertain commit, cancellation,
  ownership, and active-binding guard;
- the synthetic, direct-repository, out-of-topology MySQL constraint-translation
  test `test_mysql_only_final_mutation_receipt_flush_is_narrow`, which must not
  be cited as current production-race reachability; and
- real-MySQL P4-S1 binding evidence, lock order, guard atomicity, corruption
  failure, and bind-versus-lifecycle serialization.

Passing old tests alone does not replace the new HTTP and real-MySQL evidence in
sections 16–18.

## 20. Later implementation verification ladder

Use PowerShell 7+ and only `.\.venv\Scripts\python.exe`. Keep
`RUN_LIVE_DEEPSEEK_TEST` disabled. Local relevant checks are mandatory even if
CI will run broader suites.

1. Confirm the approved/published plan baseline, exact approved plan hashes,
   clean Git state, intact `.venv`, and the exact 11-path later budget.
2. Run the strict environment doctor without printing secrets:

   ```powershell
   .\scripts\doctor.ps1 -Strict
   ```

3. Run affected compilation/import checks:

   ```powershell
   .\.venv\Scripts\python.exe -m compileall -q src tests alembic
   ```

4. Run focused policy, operation, and service regressions:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q tests/unit/test_player_character_policies.py tests/unit/test_player_character_operations.py tests/unit/test_player_character_service.py
   ```

5. Run focused API, OpenAPI, owned-read, composition, Run, and Demo tests:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q tests/unit/test_player_character_api.py tests/unit/test_player_character_read.py tests/unit/test_player_character_composition.py tests/unit/test_run_composition.py tests/unit/test_demo_composition.py
   ```

6. After safely confirming only `mysql+asyncmy` and the exact
   `deviation_protocol_test` database without printing a URL, run the real-MySQL
   retirement/service/binding selections:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q tests/integration/test_mysql_player_character_api.py tests/integration/test_mysql_player_character_service.py tests/integration/test_mysql_player_character.py tests/integration/test_mysql_player_character_run_binding.py
   ```

7. Run explicit route-inventory and OpenAPI assertions through the focused test
   files above and record that normal exposes retirement while Demo/public Run
   do not.
8. Run canonical sanitized Offline verification:

   ```powershell
   .\scripts\verify.ps1 -Mode Offline
   ```

9. Run canonical MySQL verification:

   ```powershell
   .\scripts\verify.ps1 -Mode MySQL
   ```

10. Run canonical Full verification:

    ```powershell
    .\scripts\verify.ps1 -Mode Full
    ```

11. Confirm Alembic head/history are unchanged and no migration exists:

    ```powershell
    .\.venv\Scripts\python.exe -m alembic heads
    .\.venv\Scripts\python.exe -m alembic history
    ```

12. Complete the canonical documentation-synchronization checklist and run
    applicable link, approval-token, status, route, lifecycle, exclusion,
    placeholder, generated-artifact, BOM, UTF-8, line-ending, final-newline,
    Markdown-fence, and local-link checks.
13. Inspect every changed/untracked path and the complete diff, then run:

    ```powershell
    git diff --check
    git diff --cached --check
    ```

14. Confirm exact final branch, `HEAD`, local `main`, local `origin/main`,
    ahead/behind, active-operation, unmerged, staged, untracked, and 11-path
    candidate state. Record SHA-256 for every later candidate file.

No browser, Demo runtime, application launch, frontend, Provider, live model, or
external service belongs in this verification. Every relevant failure, warning,
skip, retry, and environment limitation must be reported.

## 21. Documentation synchronization after later implementation

Only after code and all assigned local verification pass may the six
documentation paths in section 15.3 record:

- P5-S3 implemented in the exact candidate, but not independently approved,
  committed, published, deployed, or released until each later gate occurs;
- the exact route, tests, verification counts, path inventory, and residual
  risks actually demonstrated;
- P5-S1 and P5-S2 preservation;
- continued Demo/frontend/public-Run non-activation;
- no schema/migration/persistence/application/domain/error-module change; and
- all continuing exclusions and production-authentication limitations.

Documentation must not describe P5-S3 or Phase 5 as complete before its own
implementation review and applicable handoff. It must not rewrite unrelated
history.

## 22. Plan approval and implementation gate

The required non-circular sequence is:

1. freeze this exact complete six-file documentation candidate and record all
   six SHA-256 identities;
2. conduct one fresh GPT-5.6-sol High independent read-only review of those
   exact bytes;
3. obtain the sole operative verdict
   `STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`;
4. if any candidate byte changes, invalidate the hashes/verdict and repeat from
   step 1;
5. obtain separate authorization to stage and commit only the approved six
   documentation files;
6. verify staged and committed bytes, parent, and path inventory;
7. the user performs the push manually;
8. confirm a new clean remote-aligned baseline without an unnecessary fetch;
   and
9. begin implementation only under a separate explicit P5-S3 implementation
   authorization against that baseline.

This drafting task performs only candidate creation and local documentation
verification. It does not perform steps 2–9.

Any later implementation candidate requires its own fresh independent review
of its exact complete bytes before commit. That later review is distinct from
plan approval; this plan does not pre-issue or name a competing implementation
approval token.

No amendment document, umbrella token, status-correction token, or extra
approval layer is required or authorized.

## 23. Stop conditions for later implementation

Stop without widening scope if:

1. the approved plan bytes/hashes, predecessor status, or implementation
   baseline is stale;
2. any route, body, confirmation, operation-ID, response, replay, error,
   OpenAPI, authentication, ownership, or non-enumeration decision is unresolved
   or contradictory;
3. the existing service cannot accept the exact constructed command at most
   once;
4. ownership cannot remain in the existing resolver/service or receipt
   disclosure can occur before ownership;
5. after all existing pre-receipt validation and revision-capacity gates
   succeed, exact replay cannot precede current-state stale/lifecycle rejection
   or would cause a second mutation/revision increment;
6. active binding cannot use the existing P4-S1 seam/guard without changing
   either aggregate;
7. success would end a Run, historicalize a binding, clear controller binding,
   replace identity, or do compensating work;
8. a domain, application-service, operation, port, repository, Unit-of-Work,
   receipt, CAS, transaction, schema, ORM, migration, dependency, error-module,
   Run, frontend, or Demo runtime change is required;
9. a twelfth path is required;
10. generic retry, write retry, commit retry, a third Unit of Work, or uncertain-
    commit recovery is proposed;
11. production authentication, frontend, Demo, public Run, Provider, narrative,
    scenario, world, or another excluded surface becomes necessary;
12. `.venv` is missing or broken;
13. any focused, MySQL, Offline, Full, compile, Alembic, documentation, OpenAPI,
    route-inventory, Git, or path-budget verification fails and cannot be fixed
    within the exact authority; or
14. a confirmed reusable defect requires a guardrail/workflow change outside
    the approved budget.

A stop returns a concrete blocker and requires corrected authority. It does not
authorize partial implementation, weaker parsing, a fallback database, a new
error system, or unrelated cleanup.

## 24. Later implementation acceptance criteria

The later P5-S3 candidate is review-ready only when all of these are true:

1. exactly the 11 authorized paths changed;
2. the normal application exposes the exact retirement route and no other new
   route;
3. Demo, public Run, frontend, Web, and administration expose nothing new;
4. the target/path, principal, ownership, JSON, confirmation, media type, and
   operation ID match this plan exactly;
5. the API constructs the exact existing `RETIRE` command and calls mutate at
   most once;
6. committed success preserves identity/controller binding, changes active to
   retired, and advances revision once;
7. exact replay returns the original public result without a second mutation;
8. ordinary incompatible reuse, ordinary stale revision, invalid lifecycle,
   and active binding return their exact safe 409 mappings without state
   change;
9. maximum expected revision returns revision conflict before fingerprint,
   receipt, stale-current, binding, or lifecycle evaluation, for both reused
   and new operation IDs, without receipt or state change;
10. missing/non-owner/unmapped cases are the identical 404;
11. parsing failures are the identical detail-free 422;
12. infrastructure, integrity, impossible, and uncertain-commit failures are
    the identical detail-free 500;
13. the existing P4-S1 guard leaves character, Run, receipts, and binding
    unchanged;
14. normal real-MySQL HTTP concurrency proves distinct connections/UoWs
    serialize at the aggregate lock, then exact replay or ordinary idempotency
    conflict after exactly one durable revision advance and mutation receipt;
15. those normal concurrency cases perform no duplicate policy mutation,
    receipt-add recovery, or MySQL 1062 and use fresh independent durable-state
    reads;
16. explicitly labelled narrow receipt-add fault injection proves at most one
    fresh read-only recovery UoW, with authority re-resolution and durable
    receipt reread but no generic retry, mutation retry, third UoW, recovery
    write/commit, or uncertain-commit recovery;
17. the exact success projection and OpenAPI contract are mechanically proved;
18. focused and canonical verification passes locally;
19. canonical documentation is synchronized without a broader completion or
    deployment claim;
20. all exact candidate hashes are recorded; and
21. one fresh independent implementation review approves that later candidate
    before any separately authorized commit.

Implementation completion does not itself mean approved, committed, published,
deployed, activated in Demo/frontend, production-authenticated, or Phase 5
complete.

## 24.1 Candidate verification and correction history

The P5-S3 lifecycle is, in order:

1. The published P5-S2 baseline remains
   `4ba66d8f277988325795c905fdf6fd9e416d7457`.
2. The exact P5-S3 plan was independently approved against that baseline; its
   approval did not approve implementation.
3. The first exact eleven-path unstaged P5-S3 implementation candidate passed
   its then-required local ladder: strict doctor; compile/import; 188 focused
   policy/operation/service tests; 193 focused
   API/read/composition/Run/Demo tests; 74 focused real-MySQL tests; canonical
   Offline verification outside the sandbox (1,736 passed, 118 expected
   offline skips); canonical MySQL (130 passed); and canonical Full outside the
   sandbox (1,853 passed, one opt-in live-test skip).
4. Its first fresh independent GPT-5.6-sol High review returned
   `CHANGES_REQUIRED`; implementation was not approved.
5. The first corrected exact eleven-path unstaged candidate corrected the
   literal-boolean and command-bound projection evidence and passed: strict
   doctor; compile/import; 188 focused policy/operation/service tests; 225
   focused API/read/composition/Run/Demo tests; 78 focused real-MySQL tests;
   canonical Offline (1,768 passed, 122 expected offline skips); canonical
   MySQL (134 passed); and canonical Full (1,889 passed, one opt-in live-test
   skip).
6. Its second fresh independent review confirmed those corrections and returned
   `CHANGES_REQUIRED` for the empty-ID router gap, incomplete retirement API
   evidence, incomplete raw-header/body/OpenAPI evidence, and absent
   mutation-receipt-add recovery instrumentation. Implementation was not
   approved.
7. The re-corrected exact eleven-path unstaged candidate addressed those four
   findings and passed: strict doctor; compile/import; 188 focused
   policy/operation/service tests; 237 focused
   API/read/composition/Run/Demo tests; 212 focused API/Demo/Run rerun tests;
   79 focused real-MySQL tests; direct route/OpenAPI checks; canonical Offline
   (1,780 passed, 123 expected skips); canonical MySQL (135 passed); and
   canonical Full (1,902 passed, one opt-in live-test skip).
8. Its third fresh independent review returned `CHANGES_REQUIRED` without a
    demonstrated production-code defect. It criticized the then-current
    receipt-conflict test and production counts, noted missing durable-MySQL and
    unit/header/body/identity/OpenAPI assertions, and found that this correction
    history did not yet record the full review sequence. Under the
    then-operative acceptance text it requested a receipt-uniqueness
    interleaving that the later focused investigation adjudicated unreachable.
    Implementation was not approved.
9. The following evidence-corrected exact eleven-path candidate replaced the
    artificial race repositories and direct test-thrown conflict with delegated
    production repository SQL, an independently durable competing service
    transaction, and an original receipt flush that lost to MySQL duplicate key
    1062. It also added fresh-session durable-state assertions and
    completed the required unit, identity, raw-header, OpenAPI, and route
    inventory evidence. Its test topology rolled back the original production
    mutation session mid-operation, released its aggregate/range/parent locks,
    committed the competing transaction, and resumed the stale in-memory
    operation in a new implicit transaction. It remained local, unstaged,
    uncommitted, and unapproved.
10. Local verification for that previous evidence candidate completed:
    strict doctor; compile/import; 91 retirement-focused API unit tests; 196
    complete Player Character API unit tests; 188 focused
    policy/operation/service tests; 271 focused
    API/read/composition/Run/Demo tests; 246 focused API/Demo/Run rerun tests;
    79 focused real-MySQL API/service/binding tests; four direct route/OpenAPI
    checks; canonical Offline (1,814 passed, 123 expected skips); canonical
    MySQL (135 passed); canonical Full (1,936 passed, one expected opt-in live
    Provider skip); and unchanged Alembic head `20260729_0005`. The first
    current-candidate Offline invocation was terminated only by its command
    runner's 120-second timeout; it was not the documented ACL cleanup case and
    was not treated as a pass. The exact unchanged command then completed in
    124.6 seconds with the result recorded above.
11. A separate focused read-only reachability investigation traced the actual
    production lock order and returned the binding verdict
    `P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`. The
    first aggregate database read locks the existing
    `player_character_current` row `FOR UPDATE`, so a second legitimate writer
    waits before receipt lookup, policy, revision write, CAS, or receipt add.
    After the winner commits, the waiter can only exact-replay the same
    fingerprint or return ordinary idempotency conflict for a different one.
12. The present acceptance-boundary/test correction removes the previous
    candidate's false production-race claim and its rollback-and-resume test. It
    adds real-MySQL normal HTTP concurrency evidence for aggregate-lock waiting,
    identical exact replay, different-fingerprint conflict, distinct real
    connections/UoWs, one durable revision advance and receipt, no duplicate
    policy mutation, no receipt-add recovery, and no 1062. Existing service-unit
    receipt-add fault injection remains the bounded defensive recovery evidence;
    direct repository uniqueness evidence remains explicitly synthetic and
    out-of-topology. The production branch is preserved unchanged.
13. Local validation for the present acceptance-boundary-corrected exact
    eleven-path candidate completed on 2026-08-01: strict doctor; compile/import;
    two focused corrected concurrency tests; 18 complete real-MySQL retirement
    API tests; 188 focused policy/operation/service tests; 196 complete Player
    Character API unit tests; 75 owned-read/composition/Run/Demo tests; 80
    focused real-MySQL API/service/repository/binding tests; four direct
    route/OpenAPI checks; canonical Offline (1,814 passed, 124 expected skips);
    canonical MySQL (136 passed); canonical Full (1,937 passed, one expected
    opt-in live Provider skip); and unchanged Alembic head `20260729_0005`.
14. A fresh focused final independent review of this exact corrected eleven-path
    candidate and its final hashes returned
    `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED`, finding
    no material scoped defect. It accepted the real-MySQL aggregate-lock
    serialization, exact replay or ordinary idempotency conflict, and one durable
    mutation evidence; defensive fault injection proves bounded recovery only,
    and the unreachable receipt-add race is not a requirement. P5-S3 is
    independently approved and eligible for exact-scope commit; P5-S4 and all
    unrelated deferred work have not begun. Runtime activation, deployment,
    release, and Provider work remain deferred.

The earlier first-candidate sandbox Offline and Full assertion runs reached the
documented Windows user-Temp `pytest-current` cleanup ACL failure only after all
test assertions passed; only their exact unchanged canonical commands were
rerun outside the sandbox. Nothing in this history claims P5-S3 implementation
approval, commit, publication, push, deployment, release, runtime activation,
or Demo, frontend, public-Run, administration, Web, Provider, or production-
authentication activation.

## 25. Guardrail impact and residual risks

Guardrail impact: **None.** No confirmed defect establishes or changes a
reusable engineering, safety, environment, review, or Git rule. This plan
applies existing `API-001`, `AUTH-001`, `DB-001`, `STATE-001`, `ENV-001`,
`ENV-002`, and workflow approval/baseline rules.

Real residual risks are:

- the inherited raw request has no transport-size cap and is fully buffered
  before DTO validation;
- duplicate-member rejection adds a second JSON syntax pass over the same
  cached bytes, though not a second body read or domain-validation graph;
- the fixed development principal remains unsuitable for Internet deployment;
- uncertain commit intentionally has no recovery or exactly-once guarantee;
- only explicitly injected receipt-add conflict, an out-of-topology writer, or
  a future changed transaction topology may reach the bounded second read-only
  recovery Unit of Work; normal current retirement requests serialize earlier;
- active bound retirement remains unavailable until later Run-owned atomic
  line-ending/binding-historicalization authority exists; and
- exact replay returns the stored original retirement result, not necessarily
  current character state after future mutations.

These risks are explicit and do not authorize scope expansion.

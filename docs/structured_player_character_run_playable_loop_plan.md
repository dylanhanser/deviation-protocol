# Phase 8 — Structured Player Character Run Entry and Minimum Playable Loop

## 1. Status and authority

Status: **Approved and published Phase 8 planning authority. Its seven-document
planning candidate received independent approval with
`STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED` and was
committed and published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`
(`docs(player-character): approve phase 8 playable-loop plan`). This plan does
not authorize implementation.**

Phase 5 is complete at the published P5-S3 baseline
`34d063e387cde69500e4dc018ff087e87f3eee74`
(`feat(player-character): add idempotent retirement endpoint`). No P5-S4 exists
or has begun. Phase 6 remains planned and unimplemented for subject-reference
compatibility hooks, and Phase 7 remains planned and unimplemented for
regression, documentation, and closeout. Neither is a Phase 8 prerequisite,
marked complete, or absorbed by Phase 8.

P8-S1 eligible-character discovery is implemented, independently accepted,
committed, and published at
`95ffe4019e2a69967dfae1fee2a1ecba4a628381`. P8-S2 atomic internal Run entry
is implemented, accepted, committed, and published at
`70815b181624e5475d2d978bef0db1ed3b22324e`
(`feat(player-character): add durable run-entry initialization`); its
implementation and F1/F2/F3 evidence are closed, and P8-S2 is not being
reopened. The
[P8-S3 implementation plan](structured_player_character_p8_s3_implementation_plan.md)
was independently approved and committed/published at
`e17172ad0a9febe4ec9e3a96e7be8204c9722d29`. Its exact implementation
candidate received a first independent read-only implementation review that
returned `CHANGES_REQUIRED` with five bounded findings. All five corrections
are complete; their correction thread reported canonical Offline
`1919 passed, 182 skipped` and MySQL `194 passed`. A subsequent independent
read-only re-review found no remaining actionable technical defect but formally returned
`CHANGES_REQUIRED` solely for one Medium documentation-synchronization finding.
This seven-owner documentation-only correction awaits its own focused
independent read-only re-review, so the P8-S3 implementation candidate is not
independently approved and remains unstaged, uncommitted, and unpublished.
P8-S4 Demo parity, P8-S5 Web connection, and P8-S6 cross-surface evidence/final
status closure have not started, and Phase 8 and the overall project remain
incomplete.

This document is the dedicated implementation plan for:

> **Phase 8 — Structured Player Character Run Entry and Minimum Playable Loop**

It records an approved planning boundary only. It creates no runtime capability, route,
test, migration, frontend behavior, Demo behavior, Provider behavior,
deployment, or production activation.

The sole operative successful verdict for an independent review of the exact
complete seven-document planning candidate is:

```text
STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED
```

The historical `P8-REV-002` correction made this exact reachable review verdict
the only operative token; no alias or older alternative is accepted. Generic
`APPROVED`, P5-S1/P5-S2/P5-S3, Phase 6, Phase 7, implementation-review,
historical, blocked, and differently named tokens cannot satisfy the gate.
Review binds the exact complete candidate bytes and the SHA-256 inventory
recorded after the candidate is frozen. Any byte change invalidates that
inventory and requires a fresh independent planning review.

An earlier fresh independent read-only review returned `CHANGES_REQUIRED`.
That is a preserved historical review record, not the operative planning
verdict. A subsequent fresh independent read-only review returned
`STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED`; the
approved exact seven-document candidate was then committed and published at
`de4d8c0e35c7864948306d751a00aaf295ff77ff`
(`docs(player-character): approve phase 8 playable-loop plan`). P8-G0's
planning-approval and publication conditions are therefore satisfied.

Any later modification to these published planning-authority bytes produces new
candidate bytes and SHA-256 identities. It cannot rely on the published
approval. Its exact changed bytes require a fresh independent read-only review
before a separately authorized documentation commit; that authorized commit
precedes user publication and clean published-baseline confirmation. Only then
may the synchronized authority support the next applicable Phase 8 task. This
later correction workflow does not reopen or become part of the completed
original P8-G0 approval and publication gate.

## 2. Verified planning baseline

The candidate was authored from this read-only verified baseline:

| Fact | Verified value |
| --- | --- |
| Repository | `D:\deviation-protocol` |
| Branch | `main` |
| `HEAD` | `34d063e387cde69500e4dc018ff087e87f3eee74` |
| Local `main` | `34d063e387cde69500e4dc018ff087e87f3eee74` |
| Local `origin/main` tracking ref | `34d063e387cde69500e4dc018ff087e87f3eee74` |
| Ahead/behind | `0/0` |
| `HEAD` parent | `4ba66d8f277988325795c905fdf6fd9e416d7457` |
| `HEAD` subject | `feat(player-character): add idempotent retirement endpoint` |
| Initial worktree/index | Clean; no modified, staged, untracked, or unmerged path |
| Remote action | No fetch or other remote contact |

A relevant baseline change before review, approval, implementation, staging,
or commit triggers the pending-plan baseline-invalidation rule in
[Codex Workflow](engineering/codex_workflow.md). If any recorded fact becomes
stale, all candidate hashes and approvals are invalid.

## 3. User-approved product outcome and phase placement

The approved product priority is the narrowest genuine playable connection
between an owned Structured Player Character and the existing gameplay loop:

1. create a new owned Structured Player Character or reuse an eligible one;
2. identify and, when more than one is eligible, select it;
3. select one currently public scenario;
4. enter one server-created Run whose continuous story line is immutably bound
   to that exact character and applicable character reference;
5. receive one server-created Session participating in that Run;
6. advance only through the existing authoritative Session/action protocol;
7. surface the existing same-tab recovery, pending-request recovery, and
   authoritative terminal scenario View without inventing a new lifecycle.

This is a playable backbone, not completion of the whole game. Phase 8 does
not implement full Phase 3.3 world/profile behavior, character-to-mechanics or
character-to-prompt compilation, later-world movement, post-scenario Run
continuation, Run termination, or any future feature listed in section 25.

Phase 8 is the currently selected planning priority. That ordering does not
assert that Phase 6 or Phase 7 is implemented, and it does not renumber,
replace, reinterpret, or complete either allocation.

## 4. Authority and precedence

Authority remains divided by subject:

| Authority | Status used by this plan | Controlling concern |
| --- | --- | --- |
| [Final Narrative Experience](final_narrative_experience.md) | Approved product authority | Persistent character and Run identity; model/server separation; minimum reading-first direction |
| [Structured Player Character Contract](structured_player_character_contract.md) | Approved and frozen, partially implemented | Character identity, lifecycle, ownership, applicable reference, binding cardinality, privacy |
| [Run Protocol](run_protocol.md), including the approved and published Phase 8 amendment | Approved Phase 3.3 design plus a corrected local P8-S3 exception candidate whose documentation synchronization awaits focused re-review | Run lifecycle, Run/line ownership, Session-backed minimum admission, world/protocol non-claims |
| [Public Client Contract](public_client_contract.md), including the approved and published Phase 8 amendment | Current public authority plus discovery implemented at P8-S1, internal admission implemented at P8-S2, and a corrected local P8-S3 public-admission candidate whose documentation synchronization awaits focused re-review | Exact discovery/admission wire contract, errors, OpenAPI, client trust |
| [Minimum Run Core Plan](minimum_run_core_implementation_plan.md) | Completed historical implementation authority | Run schema, repositories, UoW, identities, participation, receipts, transaction precedent |
| [Structured Player Character Downstream Plan](structured_player_character_implementation_plan.md) | Approved, partially implemented, and synchronized with the approved and published Phase 8 planning authority | Completed Phase 5, retained Phase 6/7 allocations, repository implementation sequence |
| [Architecture](architecture.md) and committed source | Current implemented fact | Composition, Session lifecycle, Demo isolation, persistence and dependency direction |
| [`PLANS.md`](../PLANS.md) | Roadmap/status authority | Phase placement, completion status, selected priority |
| [Engineering Guardrails](engineering/guardrails.md) and [Codex Workflow](engineering/codex_workflow.md) | Binding safety/workflow | Authority, persistence, public DTOs, playability evidence, review and Git gates |

The Phase 8 amendments do not retroactively make behavior implemented. A
conflict with a higher or narrower retained authority is a stop condition. An
implementer must not weaken authority merely to fit a preferred route or file
layout.

## 5. Completed capabilities reused unchanged

### 5.1 Structured Player Character

Phase 8 relies on, and does not recreate or reopen:

- **P5-S1:** normal-application controller-owned read through the detached
  four-field `PlayerCharacterSelfProjection`;
- **P5-S2:** normal-application creation and exact replay, with server-derived
  controller authority, permanent ID issuance, durable receipts, and bounded
  winner recovery; and
- **P5-S3:** normal-application idempotent retirement through the existing
  mutation service and P4-S1 active-binding guard.

P5-S3's endpoint, aggregate-lock serialization, replay/conflict behavior,
defensive recovery classification, unreachable receipt-add race, tests, and
documentation history are closed. Phase 8 changes none of them. A character
with an active Run binding remains ineligible for P5-S3 retirement because
Phase 8 does not implement Run ending plus atomic retirement.

### 5.2 Run and persistence

Phase 8 reuses:

- distinct `RunId`, `ContinuousStoryLineId`, `RunOperationId`, and
  `RunStateVersion` carriers;
- one Run permanently owning one continuous story line;
- lifecycle values `pre_first_turn`, `active`, `completed`, and `terminated`;
- immutable Run revisions, current-row CAS, creation and mutation receipts;
- separate immutable Session participation;
- the P4-S1 same-UoW owned-character evidence seam;
- the active-binding uniqueness backstop and exact immutable applicable
  character reference;
- Run-owned transaction and lock-order precedent; and
- normal `SqlAlchemyUnitOfWork` composition over the same `AsyncSession` as
  Session and Player Character repositories.

### 5.3 Existing gameplay and client

Phase 8 reuses unchanged:

- bounded `GET /v1/scenarios` discovery;
- authoritative scenario selection and server-frozen scenario content version;
- Session initialization, snapshot, initial event, and initial Frame behavior;
- `GET /v1/sessions/{session_id}/view` as the complete authoritative client
  refresh;
- existing action submission, idempotency, request-status polling, stale View,
  uncertain-result, Provider-failure, and rollback behavior;
- `ACTIVE`/`ENDED` scenario status and `RESOLVED`/`FAILED` settlement;
- existing same-tab `sessionStorage` recovery containing only Session and an
  optional already-confirmed pending request identity;
- explicit local clear as a client-only exit from the current tab; and
- the deterministic Demo Provider, scenario, action sequence, and process-local
  trust boundary.

No existing Session is inferred to belong to a Run. Only new Phase 8 admission
creates participation.

## 6. Current local connection state

Published P8-S2 now supplies the trusted internal operation joining:

```text
owned active Player Character
  + server-created Run/line
  + immutable P4-S1 binding
  + server-created gameplay Session
  + Run-owned Session participation
  -> existing public action loop
```

P8-S1 already discovers reusable eligible characters. P8-S2's internal
`RunEntryService` now creates Run revisions 1/2/3, binds the character, creates
the Session, adds participation, and activates the Run in one UoW. The normal
`POST /v1/runs` adapter and entry-service dependency now exist in the current
local P8-S3 implementation candidate. An independent implementation review
returned `CHANGES_REQUIRED` with five bounded findings, and all five corrections
are complete. The subsequent independent read-only re-review returned
`CHANGES_REQUIRED` solely for one Medium documentation-synchronization finding.
The current documentation-only correction awaits focused independent read-only
re-review; the candidate remains uncommitted and unpublished. The public legacy
Session-create route remains unbound. Demo composition still has no Player
Character or Run repositories/services, and Web has no Player Character or
Run-entry methods.

Those are the only connections Phase 8 fills.

## 7. Canonical minimum playable journey

The canonical Phase 8 journey is:

```text
GET eligible owned Player Characters
  -> choose one, or POST the existing Player Character creation route
  -> GET the existing public scenario catalogue
  -> POST one idempotent Run-entry request
       -> server resolves principal/controller
       -> server locks and validates the owned active unbound character
       -> server creates Run/line identities
       -> server binds the exact applicable character reference
       -> server selects the scenario's existing default static character
          definition for current Session initialization
       -> server creates the Session and Run participation
       -> server activates the Run
       -> one UoW commit
  -> GET the returned Session's authoritative View
  -> submit only server-advertised existing actions
  -> poll or refresh only as the existing contract directs
  -> render the existing authoritative ended View when the scenario settles
```

The static `character_definition_id` used by current Session initialization is
not the canonical Structured Player Character identity. Phase 8 selects the
scenario's already validated default definition server-side as a compatibility
fixture. It does not claim that Structured Player Character declarations,
development, or narration preferences affect mechanics or prompts yet.

## 8. Exact Phase 8 definition of done

Phase 8 is complete only when accepted implementation and evidence prove:

1. an authenticated controller can discover a bounded set of owned, active,
   currently unbound Structured Player Characters or observe an empty state;
2. the existing creation route can supply a new candidate without changing its
   contract;
3. one normal-app Run-entry request atomically creates and activates a new Run,
   binds the selected character immutably, creates one gameplay Session, and
   attaches that Session to the Run;
4. replay returns the same stable public Run/session/character identifiers and
   incompatible key reuse conflicts without another effect;
5. ownership, eligibility, expected revision, active-binding cardinality, and
   non-enumeration remain server authoritative;
6. the selected Run can never switch character through any Phase 8 surface;
7. the current gameplay View/action/request-status lifecycle remains the only
   progression protocol;
8. the deterministic Demo and existing Web client can execute the complete
   create-or-reuse, select, enter, play, recover, and terminal-View journey;
9. existing schema and migration head remain unchanged;
10. no Provider, world/profile, content, combat, progression, inventory, NPC,
    relationship, or general profile feature is added;
11. all required unit, API, OpenAPI, composition, Demo, Web, real-MySQL, and
    canonical evidence passes without a live Provider call; and
12. final documentation and status are synchronized and the complete candidate
    receives a fresh independent review before any completion commit.

Scenario settlement does not complete or terminate the Run. The Run remains
`active`, preserving a continuing line for later explicitly authorized
scenario/world progression. Phase 8 therefore does not release the character's
active binding or make it eligible for another Run after that one scenario.
That is a deliberate narrow boundary, not an accidental lifecycle claim.

## 9. Identity model

| Identity | Phase 8 source and use | Never means |
| --- | --- | --- |
| `RequestPrincipal` | Trusted dependency; Session-owner/controller-resolution input | Character, Run, Session, or operation identity |
| `ControllerBindingRef` | Server-resolved owner of Player Character records | Public credential or caller claim |
| `PlayerCharacterId` | Selected owned canonical character | Static character definition or Session player ID |
| `ApplicableCharacterReference` | Exact contract version and committed revision frozen into Run binding | Automatic current-revision following |
| `RunId` | Server-issued permanent Run aggregate identity | Session, world, scenario, or line identity |
| `ContinuousStoryLineId` | Server-issued line permanently owned by the Run | Browser or scenario identity |
| `session_id` | Server-issued gameplay Session and recovery target | Run, line, or character authority |
| `scenario_id` | Client selection only from the public authored catalogue, revalidated by server | World, visit, Run, or character identity |
| `character_definition_id` | Server-selected current scenario default for legacy Session initialization | Structured Player Character identity |
| Public `Idempotency-Key` | Controller-scoped Run-entry operation identity | Authority, character, Run, Session, or request capability |
| Action `client_request_id` | Existing Session-scoped turn/request replay identity | Run-entry operation identity |

Run and line IDs are server-issued. The client cannot submit them on entry.
The client cannot submit a Session ID, world ID, visit ID, lifecycle value,
binding state, applicable character contract/revision object, static character
definition, or authoritative state.

## 10. Public API and client-contract effects

### 10.1 Eligible-character discovery

Phase 8 adds exactly one purpose-specific collection operation:

```http
GET /v1/player-characters/eligible-for-run-entry
```

Successful response:

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

The operation:

- resolves the trusted principal/controller before database work;
- returns only current records owned by that controller whose lifecycle is
  `active` and which have no active Run binding;
- reuses the detached four-field projection for each item;
- orders by exact case-sensitive `player_character_id` ascending;
- reads at most 33 eligible rows, returns at most 32, and sets `truncated=true`
  only when an additional eligible row exists;
- returns `eligible_player_characters=[]` and `truncated=false` when the
  resolved controller has none;
- returns the existing non-enumerating Player Character 404 when controller
  authority cannot be resolved; and
- accepts no query, body, filter, search, sort, page, cursor, controller,
  lifecycle, binding, count, or administrator input.

The fixed 32-item projection cap follows the existing public scenario-catalog
bound and is only a response-safety bound. It is not an account character
limit. There is no total count or pagination framework. A truncated result is
still sufficient for the minimum loop; the existing owned single-resource GET
continues to support a known ID.

### 10.2 Run entry

The local P8-S3 implementation candidate provides exactly one normal-
application mutation; P8-S4 separately owns Demo parity:

```http
POST /v1/runs
Idempotency-Key: <1..128 exact opaque ASCII characters>
Content-Type: application/json

{
  "player_character_id": "pc.example",
  "expected_record_revision": 1,
  "scenario_id": "death_certificate"
}
```

The accepted `P8-FRESH-005` correction uses `death_certificate`, the
authoritative public catalogue scenario ID. The
`config/scenarios/death_certificate_v1.json` filename remains unchanged and is
not a public request identity.

The request model is strict and extra-forbid. Identifiers use their existing
public/domain bounds. `expected_record_revision` is a positive signed-64-bit
value. No other body or query field is admitted.

First committed success and exact replay both return HTTP 200 with the same
stable shape:

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

The response omits continuous-story-line identity, Run state version,
operation IDs, receipts, fingerprints, controller binding, provenance,
applicable-reference internals, static character definition, snapshot, world,
visit, Provider, transaction, lock, and recovery data. The client next reads
the complete existing Session View; the entry response does not duplicate an
initial or current View.

### 10.3 Existing routes preserved

Phase 8 does not remove or reinterpret:

- the three completed Player Character routes;
- `GET /v1/scenarios`;
- legacy `POST /v1/sessions` for compatibility;
- Session metadata/state/View reads;
- action submission or request-status polling; or
- current public errors and stale/uncertain recovery rules.

There is no public Run read, list, patch, bind, rebind, attach-Session,
complete, terminate, exit, resume-by-Run, or delete route.

## 11. Ownership, eligibility, and non-enumeration

For a new Run entry, the server must:

1. validate the public operation identity and typed request;
2. resolve `RequestPrincipal` to a trusted `ControllerBindingRef` before
   private disclosure;
3. enter one Run-entry UoW and lock the target Player Character;
4. return the same non-enumerating 404 for foreign ownership, missing
   ownership, or unavailable authoritative ownership mapping;
5. treat malformed or corrupt surviving canonical ownership evidence or state
   as an integrity failure mapped to the sanitized 500 path, never disguise it
   as a normal ownership miss, and expose no raw integrity or storage detail;
6. evaluate compatible replay/conflicting key reuse after ownership is proven
   and before new-operation stale/eligibility rejection;
7. require exact target identity, supported contract, expected current
   revision, lifecycle `active`, and no active Run binding;
8. validate `scenario_id` through the existing public scenario catalogue and
   select its validated default static character definition server-side; and
9. create every Run, line, Session, binding, participation, version, receipt,
   timestamp, seed, event, and authoritative state value on the server.

A retired or deceased owned character, stale expected revision, already-bound
owned character, or version-exhausted record receives a stable 409 without any
write. Missing and wrong-owner targets remain indistinguishable. A client may
display eligibility but that display is not a capability; entry rechecks it
under lock.

The accepted `P8-FRESH-002` correction changes no current authentication,
ownership, or non-enumeration boundary. Foreign ownership and unavailable
authority remain ordinary non-enumerating misses; malformed or corrupt
surviving canonical evidence remains an internal integrity failure.

## 12. Run admission and lifecycle amendment

### 12.1 Minimum Session-backed activation

Phase 8 expressly authorizes one narrow Run lifecycle amendment:

- canonical creation still begins at Run revision 1 and
  `pre_first_turn`;
- immutable character binding is revision 2 and remains active;
- first trusted Session participation is revision 3 and atomically changes
  lifecycle from `pre_first_turn` to `active`;
- `ATTACH_SESSION` remains the mutation kind for that first participation and
  for any future separately authorized participation; no new mutation token is
  introduced in Phase 8; and
- the active character binding and applicable reference remain byte-equivalent
  across the activation.

This is a compatibility path for the current Session/scenario engine. It does
not pretend that `scenario_id` is a world, invent an `entry_world_id`, store a
Run Protocol, or satisfy full Phase 3.3 world/profile acceptance. The broader
Phase 3.3 requirement to resolve and freeze protocol and entry-world identity
continues to govern future Phase 3.3-native Runs. A later Phase 3.3 plan must
explicitly preserve or migrate these legacy Session-backed active Runs; Phase 8
does not preselect that later representation.

### 12.2 No character switching or terminal transition

No Phase 8 command can replace, clear, update, follow, or switch the Run's
character or applicable revision. A second binding attempt conflicts.

An existing scenario ending is not a Run ending. `RESOLVED` and `FAILED` remain
scenario settlement classifications only. The Run stays `active`, its binding
stays active, and its immutable participation remains. `completed`,
`terminated`, binding historicalization, later Session admission, later
scenario selection, and line continuation remain future Run-owned work.

## 13. Transaction, lock, and concurrency model

Published P8-S2 implements `RunEntryService` as the single transaction owner.
P8-S3 reuses that exact service and may not rename, replace, duplicate, or
reopen its ownership.

The new-operation order is:

1. validate principal, public key, request, and trusted source;
2. resolve controller authority before UoW construction;
3. derive domain-separated internal Run create, bind, attach, and Session
   creation operation identities from the controller plus public key using a
   deterministic server-owned SHA-256 construction;
4. enter one UoW;
5. lock and strictly reconstruct the target Player Character using the P4-S1
   same-UoW evidence seam;
6. read/evaluate the derived Run creation receipt before stale/eligibility
   rejection;
7. for an exact replay, validate the referenced Run revisions, immutable
   binding, first participation, owned Session, scenario, and safe result, then
   return without mutation or commit;
8. for a new operation, validate expected revision, active lifecycle, no
   active Run, and scenario/default-definition eligibility;
9. issue and validate one Run ID, one line ID, and one Session ID;
10. stage Run revision/current 1 plus creation receipt;
11. stage binding revision 2, current CAS, and binding receipt using the
    existing P4-S1 pure construction and evidence rules;
12. stage the existing Session initial row, snapshot, initial scenario event,
    and memory effects without a nested UoW or commit;
13. stage active participation revision 3, participation row, current CAS, and
    attachment receipt;
14. commit once; and
15. return success only after that commit returns.

Repositories flush and never commit. `PlayerCharacterService`, `RunService`,
and `SessionService` may expose narrow same-UoW staging helpers, but none may
open a nested UoW or commit when called by `RunEntryService`. Existing public
methods retain their current transaction ownership.

Lock order is Player Character first, then any existing Run evidence, then
Session creation records. A new Run has no pre-existing aggregate row to lock.
Two admissions for one character serialize on the Player Character lock; the
winner establishes the active-Run uniqueness row, and the loser observes exact
replay, key conflict, or already-bound ineligibility. The database unique
backstops remain final defense. No generic retry, write retry, identity retry,
commit retry, outbox, saga, compensation, or uncertain-commit recovery is
authorized.

## 14. Idempotency and replay

The public `Idempotency-Key` is scoped to the resolved controller. It is not
used directly as a global Run receipt key. Server-owned derivation produces
bounded, domain-separated internal IDs for:

- `run.create/v1`;
- `run.bind-player-character/v1`;
- `run.attach-session/v1`; and
- the existing Session creation-request identity.

The Run creation fingerprint for this composite entry binds at least the
controller-scoped operation, target Player Character ID, expected character
revision, selected scenario ID, resolved scenario content version, selected
server default character-definition ID, and trusted source. Bind and attach
receipts retain their existing exact Run/line/character/Session/version
fingerprints.

The accepted `P8-REV-001` correction made that composite fingerprint durable,
not merely an in-memory admission check. P8-S2 introduced the strict Phase 8
composite creation-evidence model and backward-compatible creation-evidence
codec. The complete composite evidence is written through the existing
`run_creation_receipts.operation_evidence_canonical` carrier and decoded from
that same carrier after repository reload. The Run creation-receipt repository
must accept the already-validated evidence from the transaction owner instead
of reconstructing Phase 8 evidence from revision-one `source_reference` alone.
The load path independently decodes the stored evidence, recomputes the
fingerprint, cross-checks the receipt key/result and the authoritative Run
revision family, and reconstructs the same composite components. Mutation of
the controller-scoped operation, Player Character identity, expected revision,
scenario ID, scenario content version, default character-definition ID, or
trusted source must fail integrity validation.

The codec must continue to decode the exact historical source-only
`CreateRunCommand` evidence written before Phase 8, recompute its existing
source-only fingerprint, and validate its revision-one source binding. It must
not rewrite, reinterpret, or weaken those receipts, treat a composite receipt
as source-only, accept ambiguous/non-canonical evidence, or introduce a second
evidence store. The existing table and `operation_evidence_canonical` column
remain the sole carrier; no ORM or Alembic change is authorized. The public
replay result is recovered only from the persisted receipt plus independently
validated Run/binding/participation/Session evidence. All writes and the
resulting receipt remain inside the one Run-entry UoW and one commit; no retry,
compensation, or post-commit repair is added.

Exact replay is evaluated only after ownership proof. It returns the original
Run ID, first participating Session ID, selected scenario ID, and exact bound
four-field character projection. It does not return current Session state and
therefore remains stable after gameplay advances. Incompatible reuse returns
the existing public `IDEMPOTENCY_CONFLICT`. A different key targeting an
already-bound character returns character-ineligible conflict; it does not
discover or resume that Run.

Only committed successes have receipts. Validation, authorization,
ineligibility, stale revision, scenario failure, CAS loss, persistence failure,
cancellation, and commit failure create no successful entry receipt. An
uncertain commit result is not retried or declared failed/successful; the caller
may explicitly repeat the exact same key/body. Current authority can still
preempt receipt disclosure, so a later authorization/non-enumerating 404 does
not resolve the earlier uncertainty and does not clear the retained attempt.

## 15. Error and recovery behavior

| Condition | Public result | Required state behavior |
| --- | --- | --- |
| Foreign ownership, missing ownership, or unavailable authoritative ownership mapping | 404 `PLAYER_CHARACTER_NOT_FOUND` | No disclosure, write, issuance, or commit |
| Empty eligible collection | 200 empty collection | Read only |
| Invalid body/header/path/scenario carrier | 422 existing safe envelope | No service mutation |
| Scenario unavailable after typed request | 422 `INVALID_SCENARIO_DEFINITION` | No Run or Session write |
| Exact replay | 200 original stable entry result | No issuance, state advance, or commit |
| Same key, different fingerprint | 409 `IDEMPOTENCY_CONFLICT` | No write |
| Stale character revision | 409 `PLAYER_CHARACTER_STALE` | No write |
| Retired, deceased, bound, or version-exhausted owned character | 409 `PLAYER_CHARACTER_NOT_ELIGIBLE` | No write |
| Participation/unique/CAS concurrency loss not explained by exact replay | 409 `RUN_ENTRY_CONFLICT` | Complete rollback |
| Malformed or corrupt surviving canonical ownership evidence/state, corrupt stored receipt/state, ordinary persistence failure, or impossible internal result | 500 existing safe envelope | Integrity path and complete rollback; never disguise corruption as an ownership miss and expose no raw integrity, storage, or other private detail |
| Cancellation | Propagates | UoW rollback/close; no success claim |
| Uncertain commit | Safe 500 boundary; no automatic retry | No success claim; an explicit exact-key/body retry may inspect durable evidence only when current authority permits, and a later authorization/non-enumerating 404 does not resolve or clear the tainted attempt |

After entry, all recovery is the existing Session recovery. Phase 8 adds no
Run recovery record, action replay, cross-tab coordination, browser-close,
cross-device, or resume-by-character guarantee. Explicitly clearing the tab's
Session record does not end the Run, detach the character, delete the Session,
or mutate authoritative state.

## 16. Composition and dependency ownership

Dependency direction remains:

```text
api/infrastructure -> application -> domain
```

Normal composition constructs one `RunEntryService` from the already shared
UoW factory, controller resolver, Player Character binding evidence,
Run/line/Session issuers, catalogues, story director, memory rule engine, and
clock. Composition performs no SQL, UoW entry, ID issuance, mutation, or
Provider call.

The API dependency getter fails closed when the entry service is absent. The
new routes register only when their exact required service is configured.
Existing Player Character route registration remains unchanged.

The deterministic Demo must use its independent process-local store and
deterministic issuers. It must not create a database engine, read normal
controller configuration, read Provider credentials, or fall back to normal
composition. Demo-only controller and ID policy remains unmistakably local and
must satisfy domain validation without becoming production policy.

## 17. Minimal Demo and Web boundary

### 17.1 Demo

Demo gains process-local implementations of the already existing Player
Character and Run repository/UoW ports, including locks, CAS, receipts, binding
uniqueness, participation uniqueness, rollback, and detached reconstruction.
It composes the existing Player Character service, Run service, and new entry
service with deterministic identities and the existing fixed Demo principal.

This necessarily makes the already completed Player Character create/read/
retirement routes available in Demo composition because current route
registration is service-based. Their behavior is reused unchanged; Phase 8
adds no retirement control to the Web and does not reopen P5-S3. Demo remains
process-local, temporary, deterministic, and non-production.

### 17.2 Web

The existing client adds only:

- runtime schemas and client methods for the existing Player Character create
  route, the eligible collection, and Run entry;
- a compact eligible-character selector with empty-state creation;
- reuse of the existing scenario selector;
- one start control that posts the selected server projection identity and
  revision;
- immediate write of the returned `session_id` through the existing
  same-tab recovery helper;
- an authoritative View GET before rendering gameplay; and
- the existing action, polling, recovery, stale, uncertain, clear, and terminal
  presentation unchanged.

The accepted `P8-REV-003` correction freezes the logical-mutation lifetime for
both Player Character creation and Run entry. The accepted `P8-FRESH-001`
correction makes 404 clearing explicitly history-sensitive after an earlier
durability-unknown send. For each logical attempt, the Web client must:

1. generate the idempotency key before the first POST and freeze the exact
   request body associated with it;
2. retain that exact key/body pair in component/process memory while the
   outcome is uncertain, block a different body from being attached to the
   retained key, and never silently replace the key for the unresolved logical
   attempt;
3. perform no automatic retry and permit only an explicit user-triggered
   manual retry, which resends the exact same key and exact same body;
4. treat a directly received contract-defined 404 as clearable only when no
   earlier send for that retained key/body pair has produced a
   durability-unknown outcome;
5. clear the retained creation attempt after an authoritative 200
   success/replay; subject to the history-sensitive 404 rule above, a
   creation-contract definitive 404, 409, or 422 rejection may also clear it;
6. on authoritative Run-entry success/replay, validate the response, write the
   returned `session_id` through the existing same-tab Session recovery helper,
   and only then clear the retained entry attempt; subject to the same
   history-sensitive 404 rule, a Run-entry-contract definitive 404, 409, or 422
   rejection may also clear it;
7. after transport loss, timeout, response loss, cancellation, any safe 500
   response, any unrecognized response, or any other outcome whose commit
   status remains unknown, mark the retained logical attempt as
   uncertainty-tainted and retain its exact key/body pair. The public 500
   envelope does not distinguish an ordinary internal failure from uncertain
   durability, so it is not a definitive rejection for this client rule; and
8. while uncertainty-tainted, never treat a later authorization, ownership,
   unavailable-authority, or non-enumerating 404 as proof that the earlier send
   did not commit, and never clear the retained pair because of that 404. Keep
   the exact same key and exact frozen body, generate no replacement key,
   attach no different body, perform no automatic or silent retry, and permit
   only a later explicit user-triggered retry using that exact pair. A tainted
   attempt may clear only when an operation-specific authoritative result
   resolves the earlier uncertainty under the public contract. Existing
   authoritative-success behavior and response classifications other than this
   history-sensitive 404 remain unchanged.

This retention is only component/process memory in the current loaded Web
experience. Reload before an authoritative response and, for Run entry, before
the Session recovery record is stored remains unsupported. Browser close,
cross-tab, cross-browser, cross-device, and multi-device pending-operation
recovery remain unsupported. Phase 8 adds no `localStorage`, new
`sessionStorage` pending-operation record, IndexedDB, receipt-discovery route,
Run-discovery route, other server discovery route, durable pending-operation
store, automatic recovery, or background retry.

No new `localStorage`, URL, run/character recovery record, optimistic binding,
client lifecycle state machine, profile editor, search, pagination, visual
system, or frontend architecture is authorized. The client renders only
server-provided lifecycle, eligibility, View, affordance, and terminal state.

## 18. Database and migration assessment

Inspection of current ORM, migration `20260729_0005`, repositories, and UoW
shows that the existing schema already represents the Phase 8 invariant:

- `run_revisions` and `run_current` already admit `pre_first_turn` and
  `active`;
- `CREATE`, `BIND_PLAYER_CHARACTER`, and `ATTACH_SESSION` already represent
  the exact three admission revisions;
- active and historical binding matrices already exist;
- active-character uniqueness already enforces one active line per character;
- Run creation/binding/attachment receipts already store the necessary stable
  Run result references;
- Session participation already references the exact Session and Run revision;
  and
- Player Character current rows already have the controller/identity index
  needed for a bounded owned query.

Therefore **Phase 8 authorizes no ORM or Alembic change and no migration**.
The current linear head remains `20260729_0005`. No backfill is permitted;
legacy Sessions remain unbound.

If implementation proves that the admitted three-revision transaction cannot
be represented without changing a table, check, key, index, or receipt schema,
the affected slice stops. It must return for a separately reviewed plan
amendment that explains the missing invariant and isolates forward/downgrade
behavior. An implementer must not create a convenience migration.

## 19. Ordered slice sequence

| Slice | Canonical purpose | Prerequisite | Completion state |
| --- | --- | --- | --- |
| P8-G0 | Freeze this seven-document plan and exact public/Run authority amendments | Clean published P5-S3 baseline | Planning approval and publication satisfied at `de4d8c0e35c7864948306d751a00aaf295ff77ff`; any later correction requires exact-byte independent review, a separately authorized documentation commit, user publication, and clean-baseline confirmation |
| P8-S1 | Add bounded owned active-unbound character discovery | Approved/published P8-G0 | Implemented, accepted, committed, and published at `95ffe4019e2a69967dfae1fee2a1ecba4a628381` |
| P8-S2 | Implement one atomic internal Run-entry transaction and Session-backed activation | Accepted P8-S1 | Implemented, accepted, committed, and published at `70815b181624e5475d2d978bef0db1ed3b22324e`; closed with no public route |
| P8-S3 | Activate normal-app Run-entry API and composition | Accepted/published P8-S2 | Plan approved and published at `e17172ad0a9febe4ec9e3a96e7be8204c9722d29`; five bounded first-review corrections are complete, the subsequent re-review returned `CHANGES_REQUIRED` solely for one Medium documentation-synchronization finding, and the unstaged, uncommitted, unpublished correction awaits focused independent read-only re-review |
| P8-S4 | Add deterministic Demo persistence/composition parity | Accepted P8-S3 | Unimplemented; Demo parity remains deferred here |
| P8-S5 | Connect the existing Web client to the minimum journey | Accepted P8-S4 | Unimplemented; Web connection remains deferred here |
| P8-S6 | Run cross-surface evidence, synchronize status, and close the stage candidate | Accepted P8-S5 | Unimplemented; cross-surface evidence and final status closure remain deferred here |

Each slice is separately authorized, leaves an unstaged reviewable candidate,
receives a fresh independent review, and has a separately authorized local
commit boundary. No slice authorizes the next one. The user performs every
push manually.

## 20. Per-slice scope and path budgets

Path inventories are bounded expectations based on current composition. A
listed path is not permission to edit it before the corresponding separately
authorized implementation task. If a required path exceeds a slice's maximum,
that slice stops for plan reassessment.

The accepted `P8-FRESH-004` correction freezes one common documentation-
synchronization allowance for each of P8-S1, P8-S2, P8-S3, P8-S4, and P8-S5.
Each slice may edit at most these exact seven Phase 8 authority/status owners:

1. `PLANS.md`;
2. `docs/architecture.md`;
3. `docs/public_client_contract.md`;
4. `docs/run_protocol.md`;
5. `docs/structured_player_character_contract.md`;
6. `docs/structured_player_character_implementation_plan.md`; and
7. `docs/structured_player_character_run_playable_loop_plan.md`.

Seven is a permitted documentation-path maximum, not an instruction to modify
unchanged documents mechanically. Each slice edits only owners whose current
authority, status, evidence, or next-action wording actually needs
synchronization. Before that slice's independent review, every applicable
owner must be truthful under the canonical documentation-synchronization
checklist. The separately frozen production- and test-path budgets remain
unchanged. This documentation allowance admits no production, test, migration,
generated, dependency, or configuration path. Required synchronization is part
of that slice's candidate, independent review, and commit boundary; a slice
must not enter review or commit with known documentation drift. P8-S6 retains
its final cross-surface evidence and closure responsibility.

### 20.1 P8-G0 — Authority and plan freeze

**Purpose:** publish the exact plan, Phase 5 closure correction, Phase 8
allocation, public contract, and Run lifecycle amendment before code.

**Scope:** planning documentation only; no implementation.

**Exact path budget: seven documentation paths:**

1. `PLANS.md`;
2. `docs/architecture.md`;
3. `docs/public_client_contract.md`;
4. `docs/run_protocol.md`;
5. `docs/structured_player_character_contract.md`;
6. `docs/structured_player_character_implementation_plan.md`;
7. `docs/structured_player_character_run_playable_loop_plan.md`.

**Validation:** focused searches, link/fence inspection if directly available,
`git diff --check`, exact seven-path diff inspection, and final Git identity.
No runtime test or database command.

**Completion gate:** P8-G0's planning approval and publication conditions were
satisfied when the exact seven-document candidate received
`STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED` and was
committed and published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`
(`docs(player-character): approve phase 8 playable-loop plan`). Any later
correction is a new candidate whose exact bytes require a fresh independent
review before a separately authorized documentation commit. That authorized
commit precedes user publication and clean published-baseline confirmation;
only then may the synchronized authority support the next applicable Phase 8
task. This later workflow is not part of the completed original P8-G0 gate.

**Exclusions:** every code, test, migration, dependency, generated, Provider,
deployment, staging, commit, and push action.

### 20.2 P8-S1 — Eligible-character discovery

**Purpose:** make an existing owned character discoverable without general
listing/search infrastructure.

**Production path budget: at most five:**

- `src/deviation_protocol/application/ports.py`;
- `src/deviation_protocol/application/player_character_projection.py`;
- `src/deviation_protocol/application/player_character_service.py`;
- `src/deviation_protocol/infrastructure/repositories.py`;
- `src/deviation_protocol/api/main.py`.

`api/errors.py` is inspection-only unless the existing not-found handler cannot
represent unmapped authority; adding another production path requires plan
reassessment.

**Test path budget: at most six:**

- `tests/unit/test_player_character_read.py`;
- `tests/unit/test_player_character_repositories.py`;
- `tests/unit/test_player_character_api.py`;
- `tests/integration/test_mysql_player_character_api.py`;
- `tests/unit/test_run_composition.py`;
- `tests/unit/test_demo_composition.py`.

**Documentation path budget: at most seven:** limited to the common exact seven
Phase 8 owners above. Edit only applicable owners, and make all applicable
authority/status/evidence/next-action wording truthful before P8-S1 independent
review.

**Transaction/persistence:** read-only UoW, no lock, write, receipt, commit,
schema, or migration. Query reads at most 33 eligible rows using the existing
controller/identity and active-binding indexes.

**Evidence:** exact ordering/cap/truncation/empty state, ownership,
non-enumeration, lifecycle/binding exclusion, detachment, key/value privacy,
OpenAPI, real-MySQL query, no-write, and Demo non-activation.

### 20.3 P8-S2 — Atomic internal Run entry

The exact persistent byte contract, decoder selection, internal-ID derivation,
fingerprint mapping, transaction/replay algorithm, closed path allowlists, and
implementation gates remain frozen in the historical
[P8-S2 implementation plan](structured_player_character_p8_s2_implementation_plan.md).
P8-S2 is implemented, accepted, committed, and published at
`70815b181624e5475d2d978bef0db1ed3b22324e`; its implementation and F1/F2/F3
evidence are closed. P8-S3 reuses that completed service and does not edit,
review, correct, or expand P8-S2 or its frozen plan.

**Purpose:** supply one application-owned transaction that creates Run/line,
binds the character, creates Session state, adds participation, and activates
the Run.

**Production path budget: at most eight:**

- `src/deviation_protocol/domain/run.py`;
- `src/deviation_protocol/application/run_operations.py`;
- `src/deviation_protocol/application/run_service.py`;
- new `src/deviation_protocol/application/run_entry_service.py`;
- `src/deviation_protocol/application/session_service.py`;
- `src/deviation_protocol/application/ports.py`;
- `src/deviation_protocol/infrastructure/run_persistence.py`, for the strict
  backward-compatible historical/source-only and Phase 8 composite creation-
  evidence codec, independent fingerprint recomputation, and complete stored-
  family integrity validation; and
- `src/deviation_protocol/infrastructure/repositories.py`, for the narrow
  already-schema-supported creation-evidence write/load mapping and any proven
  replay/load query.

`player_character_service.py`, `player_character_persistence.py`,
`orm_models.py`, `unit_of_work.py`, and migration paths are inspection-only. A
need to edit them is a stop/reassessment condition except for a proven narrow
same-UoW helper in `player_character_service.py`, which must replace another
budgeted path rather than expand the maximum. The increase from seven to eight
production paths is the smallest justified increase because the existing Run
persistence codec is the authority that decodes and independently validates
`operation_evidence_canonical`; that responsibility cannot be moved into the
repository mapper without weakening the current separation.

**Test path budget: at most nine:**

- `tests/unit/test_run.py`;
- `tests/unit/test_run_operations.py`;
- `tests/unit/test_run_service.py`;
- new `tests/unit/test_run_entry_service.py`;
- `tests/unit/test_session_service.py`;
- `tests/unit/test_run_persistence.py`;
- `tests/unit/test_run_repositories.py`;
- `tests/integration/test_mysql_run.py`;
- `tests/integration/test_mysql_player_character_run_binding.py`.

The two added unit paths are the exact existing codec and SQLAlchemy mapping
surfaces. They cannot be replaced by service-only assertions: one must prove
canonical evidence encode/decode/reconstruction and component tamper rejection,
and the other must prove that the repository writes and reloads the supplied
evidence rather than synthesizing a source-only command. The existing seven
domain/service/MySQL paths remain necessary for the accepted three-revision,
Session-staging, concurrency, and atomicity topology, so nine is the smallest
truthful test maximum.

**Documentation path budget: at most seven:** limited to the common exact seven
Phase 8 owners above. Edit only applicable owners, and make all applicable
authority/status/evidence/next-action wording truthful before P8-S2 independent
review.

**Transaction/persistence:** exactly one UoW/commit owned by entry service;
existing tables only. Mandatory real-MySQL evidence covers atomic success,
every staged-write rollback point, fresh-session reconstruction, exact replay,
same-key conflict, same-character concurrent admission, active-binding
uniqueness, participation uniqueness, CAS loss, and uncertain-commit
non-recovery.

**Composite creation-evidence acceptance:** P8-S2 evidence must additionally
prove all of the following:

1. a new Phase 8 composite creation receipt survives write, fresh repository
   load, strict codec decode, and independent reconstruction with the same
   public replay result;
2. the controller-scoped operation, Player Character ID and expected revision,
   scenario ID and content version, server default character-definition ID,
   and trusted source all participate in independent fingerprint/integrity
   validation;
3. mutation of any one bound component, the canonical evidence bytes, receipt
   fingerprint, receipt key/result, or revision-family cross-binding is
   rejected rather than repaired;
4. existing pre-Phase-8 source-only Run creation receipts still decode,
   recompute their historical source-only fingerprint, and validate;
5. replay obtains its stable public Run/Session/character result from
   authoritative persisted receipt, Run revision, immutable binding,
   participation, and Session evidence rather than the incoming request or
   newly issued identities; and
6. the composite receipt is staged and committed with every other admission
   write inside the same one-UoW transaction, with rollback at every injected
   failure point and no second store, retry, or compensation.

### 20.4 P8-S3 — Normal API and composition activation

The standalone
[P8-S3 implementation plan](structured_player_character_p8_s3_implementation_plan.md)
freezes the exact route, DTO, decision mapping, composition graph, path
responsibilities, discriminating evidence, and workflow gates. It received
`STRUCTURED_PLAYER_CHARACTER_P8_S3_PLAN_REVIEW_APPROVED` and was committed and
published at `e17172ad0a9febe4ec9e3a96e7be8204c9722d29`. Its exact local
implementation candidate exposes the normal adapter and composition. An
independent implementation review returned `CHANGES_REQUIRED`; the candidate is
now corrected for all five bounded findings. The subsequent independent
read-only re-review found no remaining actionable technical defect but returned
`CHANGES_REQUIRED` solely for one Medium documentation-synchronization finding.
This documentation-only correction awaits focused independent read-only
re-review and is not an approval; the candidate remains unstaged, uncommitted,
and unpublished.

**Purpose:** expose only the approved normal-app `POST /v1/runs` operation and
compose its service lazily.

**Production path budget: at most four:**

- `src/deviation_protocol/api/schemas.py`;
- `src/deviation_protocol/api/errors.py`;
- `src/deviation_protocol/api/dependencies.py`;
- `src/deviation_protocol/api/main.py`.

**Test path budget: at most five:**

- new `tests/unit/test_run_entry_api.py`;
- `tests/unit/test_run_composition.py`;
- `tests/unit/test_api.py`;
- `tests/unit/test_phase_3_0_public_client_contract.py`;
- new `tests/integration/test_mysql_run_entry_playthrough.py`.

The dedicated MySQL playthrough path replaces the earlier planned
`tests/integration/test_mysql_player_character_api.py` P8-S3 slot and preserves
the five-path maximum. Player Character endpoint/query MySQL evidence remains
owned by P8-S1 and completed earlier character slices. The new path is focused
on the joined production journey; it follows the PLAY-001 per-step precedent in
`tests/integration/test_mysql_phase_2_4a_api.py` and the existing terminal
public-API/persistence topology in
`tests/integration/test_mysql_phase_2_4b_api.py` without modifying or
duplicating those historical tests.

**Documentation path budget: at most seven:** limited to the common exact seven
Phase 8 owners above. Edit only applicable owners, and make all applicable
authority/status/evidence/next-action wording truthful before P8-S3 independent
review.

**Transaction/persistence:** API and composition own no UoW or commit. The
route calls entry service at most once. Required evidence covers raw operation
identity, strict body, principal forwarding, result/error mapping, exact safe
DTO, exact OpenAPI statuses/components, route inventory, normal lazy
composition, cancellation, no Provider call during Run entry, and real-MySQL
ASGI vertical entry.

The accepted `P8-REV-004` correction requires that the focused
`tests/integration/test_mysql_run_entry_playthrough.py` test:

1. uses `create_app` with the normal production service object graph,
   `SqlAlchemyUnitOfWork`, production SQLAlchemy repositories, and real MySQL;
   only deterministic test identities/clock and the existing scripted
   no-network Provider seam may be substituted;
2. creates or prepares the eligible owned Player Character through an
   authorized setup boundary, then begins the claimed public journey at
   `POST /v1/runs` rather than legacy `POST /v1/sessions`;
3. receives the authoritative Run and Session identities, reads the
   authoritative Session View, submits every step in the canonical
   server-provided action sequence through the public action endpoint, follows
   the existing request-status operation whenever an action returns 202, and
   refreshes the authoritative View as required after each step;
4. continues to the existing terminal Session/View and proves that the public
   action path consumes the exact Session created by `POST /v1/runs`;
5. verifies from fresh production-repository/database reads: Run revision 3
   immediately after admission, the exact immutable Player Character binding,
   first Session participation, Session identity and lifecycle, relevant
   gameplay events/turn requests/jobs/snapshot state, terminal Session/View
   state, and the intentionally still-`active` Run; and
6. cleans up its owned rows and never substitutes Demo storage, an in-memory
   repository, a mock repository, or separate unrelated tests for any step of
   this vertical path.

This focused evidence addition changes no P8-S3 production scope and does not
require the same full playthrough in another implementation slice.

The pre-review candidate produced the earlier comparison evidence of 49 focused
Run-entry API tests, 13 normal-composition tests, 104 existing API/public-
contract tests, both dedicated real-MySQL tests, 1,918 canonical Offline tests,
and 194 canonical MySQL tests. The independent review nevertheless returned
`CHANGES_REQUIRED` because the candidate lacked discriminating service-name,
raw duplicate-member, terminal-job ordinal, documentation-state, and complete
cleanup-recount evidence. The bounded correction completed only those five
findings. Its correction thread reported 27 canonical Run-entry service
tests, 50 focused Run-entry API tests, 13 normal-composition tests, 104 existing
API/public-contract tests, both dedicated real-MySQL tests, 1,919 canonical
Offline tests, and 194 canonical MySQL tests; compilation, Alembic heads/history,
and diff validation also passed. The subsequent independent read-only re-review
found no remaining actionable runtime, API, strict-transport, OpenAPI, MySQL,
persistence, privacy, architecture, cleanup, or test-discrimination defect but
formally returned `CHANGES_REQUIRED` solely for one Medium documentation-
synchronization finding. The current documentation-only correction awaits
focused independent read-only re-review and is not an approval. The P8-S3
candidate remains uncommitted and unpublished; P8-S4, P8-S5, and P8-S6 have not
started, Phase 8 and the overall project remain incomplete, and no live Provider
was called.

### 20.5 P8-S4 — Deterministic Demo parity

**Purpose:** make the planned backend journey executable locally without MySQL
or external Provider I/O.

**Production path budget: at most three:**

- `src/deviation_protocol/infrastructure/demo_persistence.py`;
- `src/deviation_protocol/infrastructure/demo_generators.py`;
- `src/deviation_protocol/api/demo_composition.py`.

**Test path budget: at most five:**

- `tests/unit/test_demo_persistence.py`;
- `tests/unit/test_demo_composition.py`;
- `tests/e2e/test_demo_cross_process_replay.py`;
- `tests/e2e/support/demo_replay_child.py`; and
- `tests/unit/test_demo_scripts.py`, only if launcher/smoke expectations need a
  narrow route-inventory update.

The accepted `P8-FRESH-003` correction authorizes the executable child because
`test_demo_cross_process_replay.py` launches that exact path. The child
explicitly reconstructs every `DemoGenerators` field, freezes the complete
generator-category trace, validates the complete `DemoStoreSnapshot` field
manifest, and builds the schema-complete private snapshot representation. P8-S4
adds Player Character and Run-entry persistence families and deterministic
identities to that topology, so the cross-process evidence would be incomplete
if the executed reconstruction owner remained inspection-only. The five-path
maximum adds no unrelated Demo test or support path and changes no P8-S4
production scope.

**Documentation path budget: at most seven:** limited to the common exact seven
Phase 8 owners above. Edit only applicable owners, and make all applicable
authority/status/evidence/next-action wording truthful before P8-S4 independent
review.

**Transaction/persistence:** one process-local atomic store publication; exact
rollback and lock semantics matching application contracts. No database,
migration, network, credential, Provider-selection, or normal-composition
change.

**Evidence:** deterministic ID trace, create/list/enter replay, conflict,
rollback, active binding, participation, process restart state loss, two fresh
processes with identical public/generator traces, executable-child
reconstruction of every generator field/category and the complete expanded
store snapshot, no external I/O, and preserved canonical action sequence.

### 20.6 P8-S5 — Minimum Web connection

**Purpose:** connect existing rendered controls to server authority without a
frontend redesign.

**Production path budget: at most four:**

- `web/src/api/schemas.ts`;
- `web/src/api/client.ts`;
- `web/src/App.tsx`;
- `web/src/styles.css`, only for bounded layout support.

`web/src/sessionRecovery.ts` is inspection-only and must remain byte-unchanged
unless a proven correctness defect makes the existing Session-ID write
impossible. Such a defect is a stop condition, not silent scope growth.

**Test path budget: at most six:**

- `web/src/api/client.test.ts`;
- `web/src/App.test.tsx`;
- `web/src/App.action-loop.test.tsx`;
- `web/src/App.recovery.test.tsx`;
- `web/src/test/fixtures.ts`;
- `web/src/test/server.ts`.

**Documentation path budget: at most seven:** limited to the common exact seven
Phase 8 owners above. Edit only applicable owners, and make all applicable
authority/status/evidence/next-action wording truthful before P8-S5 independent
review.

**Persistence:** existing Session `sessionStorage` record only, plus unresolved
Player Character creation and Run-entry key/body pairs in current component/
process memory. There is no authoritative or durable pending-operation client
state.

**Evidence:** empty-state create, multi-item selection, truncated indicator,
scenario selection, key creation before each logical mutation's first POST,
exact frozen body/key retention, explicit same-key/same-body manual retry after
simulated response loss or another uncertain result, no automatic retry, no
replacement key or changed body while uncertain, clearing after authoritative
success/replay, history-sensitive clearing after a directly received
contract-defined 404, retention after timeout/transport loss/safe 500/uncertain
outcome, Session record write before clearing successful Run-entry evidence,
View GET, complete existing action path, pending/stale/uncertain behavior,
supported reload only after Session storage with zero duplicate start/action
POST, an explicit test that reload before authoritative entry response/Session
storage cannot recover the component-memory attempt, terminal View, clear
behavior, cancellation/late-response isolation, runtime schema rejection,
build, typecheck, lint, and deterministic-demo mode.

Within the already authorized `web/src/App.recovery.test.tsx` path, P8-S5 must
add one mandatory history-sensitive regression proving all of the following:

1. the first POST commits, or is simulated as committed, but its response is
   lost;
2. that logical attempt remains uncertainty-tainted;
3. a manual retry reuses the exact same key and exact same frozen body and
   receives an authorization/non-enumerating 404;
4. the 404 does not clear the retained key/body pair;
5. no replacement key is generated;
6. no automatic or silent retry occurs; and
7. the retained key cannot be paired with or sent using a different body.

This evidence adds no new test path, automatic recovery, receipt/Run discovery,
background retry, or durable pending-operation client store.

### 20.7 P8-S6 — Evidence and status closure

**Purpose:** prove the complete cross-surface backbone and synchronize only
facts actually implemented.

**Production path budget:** zero expected. A production fix requires return to
the owning implementation slice and a fresh review.

**Test path budget:** zero expected changes; run the accepted suites, including
the focused real-MySQL public entry-to-terminal playthrough already created and
owned by P8-S3, plus the accepted Demo/Web journey evidence. P8-S6 does not
create or modify a duplicate production test. A confirmed defect returns to
its owning slice and receives a regression test there.

**Documentation path budget: at most the seven P8-G0 paths.** No completed
P5-S1/P5-S2/P5-S3 plan is edited.

**Completion:** canonical documentation checklist, exact evidence record,
Guardrail impact assessment, complete changed-path/hash inventory, fresh
independent implementation review, separate commit authorization, and manual
user push. No deployment or release claim.

### 20.8 Per-slice authority and gate summary

The following requirements apply together with the detailed budgets above:

| Slice | Public/authority effect | Persistence and transaction boundary | Slice exclusions | Local completion evidence | Review and commit boundary |
| --- | --- | --- | --- | --- | --- |
| P8-G0 | Freeze Phase 8 allocation plus the planned discovery, entry, and Session-backed Run amendment | Documentation only; no UoW, schema, or migration | All implementation, tests, generated output, Provider, deployment, staging, and runtime activation | Exact seven-path inspection, focused status/link/fence checks, `git diff --check`, clean index and unchanged Git identity | Planning review and publication completed at `de4d8c0e35c7864948306d751a00aaf295ff77ff`; later changed bytes require fresh independent review, a separately authorized documentation commit, user publication, and clean-baseline confirmation |
| P8-S1 | Implement only `GET /v1/player-characters/eligible-for-run-entry` and its exact DTO/OpenAPI contract | Read-only repository/UoW; no lock, receipt, write, commit, schema, or migration | No general list/search/filter/page/count/admin, Run mutation, Demo activation, or Web work | Focused unit/API/OpenAPI plus real-MySQL ordering/bound/ownership/no-write evidence, `compileall`, Offline, and diff checks | Synchronize every applicable Phase 8 owner within the seven-document maximum, then fresh P8-S1 implementation review and separately authorized P8-S1 commit before P8-S2 |
| P8-S2 | No public route; implement only trusted composite admission and the narrow Run activation authority | Existing tables; one entry-owned UoW/commit; repositories only flush | No API/composition activation, Demo/Web, terminal Run transition, later Session, Provider, schema, or migration | Focused domain/service plus real-MySQL atomicity, replay, concurrency, rollback, reconstruction, Alembic-parity, `compileall`, Offline/MySQL, and diff checks | Synchronize every applicable Phase 8 owner within the seven-document maximum, then fresh P8-S2 implementation review and separately authorized P8-S2 commit before P8-S3 |
| P8-S3 | Implement only normal-app `POST /v1/runs`, exact DTO/errors/OpenAPI, and lazy composition | API/composition own no transaction; entry service remains sole UoW/commit owner; no schema or migration | No public Run read/list/bind/attach/terminal/admin, Demo/Web, Provider, deployment, or auth redesign | Focused API/OpenAPI/composition plus one real-MySQL public `POST /v1/runs`-to-terminal playthrough through every canonical action/request-status/View step and persisted Run/Session/gameplay state, cancellation, privacy, `compileall`, Offline/MySQL, and diff checks | Synchronize every applicable Phase 8 owner within the seven-document maximum, then fresh P8-S3 implementation review and separately authorized P8-S3 commit before P8-S4 |
| P8-S4 | Add deterministic Demo parity for the already frozen Player Character discovery/create and Run-entry routes | One process-local atomic publication with rollback/lock parity; no database or migration | No normal-composition change, Web work, external I/O, credentials, Provider, or persistence guarantee after process exit | Focused Demo repository/composition/e2e determinism, executable-child complete generator/snapshot reconstruction, and complete backend journey, `compileall`, Offline, and diff checks | Synchronize every applicable Phase 8 owner within the seven-document maximum, then fresh P8-S4 implementation review and separately authorized P8-S4 commit before P8-S5 |
| P8-S5 | Consume only the frozen create/discovery/entry contracts and existing Session gameplay protocol | Existing same-tab Session `sessionStorage` record plus unresolved key/body pairs in current component/process memory only; no durable pending-operation state | No server behavior, client lifecycle authority, optimistic binding, profile/search/admin UI, redesign, automatic retry, or reload/cross-context pending-operation recovery guarantee | Focused runtime-schema/client/rendered-loop/recovery tests prove pre-POST key creation, exact manual same-key/body retry, no automatic/replacement retry, history-sensitive 404 retention after an uncertainty-tainted send, precise clear/retain outcomes, honest pre-Session-storage reload limitation, plus typecheck, lint, build, Demo-backed playthrough, and diff checks | Synchronize every applicable Phase 8 owner within the seven-document maximum, then fresh P8-S5 implementation review and separately authorized P8-S5 commit before P8-S6 |
| P8-S6 | Synchronize implemented facts and close only Phase 8 | No expected production/test mutation; documentation/status only unless work returns to an owning slice | No late feature, duplicate production playthrough, defect fix without regression ownership, deployment, release, Provider, or Phase 6/7 completion | Re-run P8-S3's accepted MySQL entry-to-terminal test and applicable focused/Offline/MySQL/Full/Alembic/Web/Demo evidence; canonical documentation synchronization | Fresh independent complete-Phase-8 review, then separate completion-commit authorization; user push only |

## 21. Acceptance and evidence matrix

| Authorized behavior | Minimum binding evidence | Not a gate |
| --- | --- | --- |
| Eligible collection | Unit query/projection/API/OpenAPI plus real-MySQL bounded ordering and no-write evidence | General search, arbitrary large-owner load test |
| Ownership/non-enumeration | Missing/foreign/unavailable authoritative mapping use the identical 404; malformed/corrupt surviving canonical ownership evidence uses the sanitized 500 integrity path; no pre-authority disclosure | Production authentication implementation |
| Atomic admission | Unit call-order/rollback plus real-MySQL complete write-family/fresh-read proof, including backward-compatible composite creation-evidence persistence/reconstruction and component tamper rejection | Distributed transaction or generic retry |
| Same-character concurrency | Real MySQL, distinct connections/UoWs, one durable Run/binding/Session/participation | Copying P5-S3 receipt-add race evidence |
| Exact replay/key conflict | Unit, ASGI, and MySQL stable result/no-second-effect evidence | Exactly-once execution or billing claim |
| Run activation | Domain/operation/persistence proof of revisions 1/2/3 and `active` state | `completed`/`terminated` transitions |
| Immutable character binding | Unit/MySQL second-binding rejection and exact-reference reload | Revision-following policy |
| Public contract | Exact response key/value privacy scans, error envelopes, OpenAPI status/schema and route inventories | Public Run read/list/admin |
| Normal composition | Object-graph/lazy construction and one-route reachability | Deployment, production auth, Provider availability |
| Demo | Process-local repository/UoW tests, two-process determinism, executable-child reconstruction of every generator field/category and the complete expanded store snapshot, external-I/O denial | MySQL durability or post-restart persistence |
| Web | Runtime schema/client tests for both logical-mutation key/body lifetimes, including uncertainty-tainted retention through a later authorization/non-enumerating 404, and rendered full loop through existing terminal View | Durable pending-operation storage, reload-before-Session-storage or cross-device recovery, redesign, profile UI |
| Existing gameplay | P8-S3 real-MySQL public Run-entry-to-terminal path plus Demo/Web paths through every canonical action step | New scenario/content or Provider behavior |
| Schema stability | ORM/metadata parity, Alembic `heads`/`history`, no migration diff | New migration |
| Documentation | For each P8-S1 through P8-S5 candidate, truthful synchronization of every applicable owner within the exact seven-document maximum before independent review; focused links/fences, `git diff --check`, canonical checklist | Mechanical edits to unchanged owners or admission of production/test/migration/generated/dependency/configuration paths through the documentation allowance |

Optional additional fuzzing, load testing, manual browser exploration, or UX
polish may be useful but is not a Phase 8 acceptance gate unless a confirmed
defect makes focused evidence necessary.

## 22. Canonical local verification by slice

Later implementation uses PowerShell 7+ and the explicit repository Python.
Live Provider calls remain disabled.

### P8-S1

```powershell
.\.venv\Scripts\python.exe -m pytest <P8-S1 focused unit/API paths>
.\.venv\Scripts\python.exe -m pytest <P8-S1 focused MySQL paths>
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
.\scripts\verify.ps1 -Mode Offline
git diff --check
```

### P8-S2 and P8-S3

```powershell
.\.venv\Scripts\python.exe -m pytest <Run-entry domain/service/API focused paths>
.\.venv\Scripts\python.exe -m pytest <Run-entry real-MySQL focused paths>
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic history
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
.\scripts\verify.ps1 -Mode Offline
.\scripts\verify.ps1 -Mode MySQL
git diff --check
```

### P8-S4

```powershell
.\.venv\Scripts\python.exe -m pytest <Demo persistence/composition/e2e paths>
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
.\scripts\verify.ps1 -Mode Offline
git diff --check
```

### P8-S5

```powershell
npm --prefix web run test:run -- <focused Web paths>
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
git diff --check
```

### P8-S6

Run focused complete Phase 8 selections, canonical Offline, MySQL, and Full
verification, `compileall`, Alembic heads/history, all Web test/typecheck/lint/
build commands, the existing bounded Demo smoke if directly applicable, and
`git diff --check`. Re-run the P8-S3-owned real-MySQL public
`POST /v1/runs`-to-terminal evidence through every canonical action,
request-status when 202, authoritative View refresh, and persisted admission/
gameplay assertion. P8-S6 creates no duplicate test. The deterministic Demo/Web
evidence separately covers the complete canonical gameplay path, not merely the
first action.

No slice calls a live Provider. No test count is predicted; record only actual
results.

## 23. Review and commit sequence

The published P8-G0 sequence was:

1. freeze the exact P8-G0 seven-document candidate and record all file hashes;
2. obtain one fresh independent read-only review with the sole operative
   verdict
   `STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED`;
3. if any candidate byte changes, invalidate hashes/approval and repeat;
4. obtain separate authorization for the exact documentation commit;
5. verify staged and committed bytes and scope;
6. the user pushes manually and confirms a clean aligned baseline;
7. implement P8-S1 only under separate explicit authorization;
8. for each implementation slice, synchronize every applicable Phase 8 owner
   within the exact seven-document documentation maximum, freeze its exact
   candidate, run its required local validation, obtain a fresh independent
   review only after all applicable owners are truthful, obtain separate commit
   authorization, and let the user push before beginning the next slice; and
9. after P8-S6, obtain one fresh independent review of the complete Phase 8
   implementation and synchronized documentation before any completion commit.

Any post-publication correction repeats steps 1 through 6 for its exact
corrected bytes before it may be relied upon to begin P8-S1. This plan
pre-issues no implementation approval.

Each later review prompt must
define exactly one success verdict reachable by that review and bind it to the
exact candidate hashes.

## 24. Documentation and status synchronization

After each accepted implementation slice, update only owning facts. Before
independent audit, completion, or commit request, complete the canonical
documentation-synchronization checklist.

The final Phase 8 documentation candidate may update at most:

- `PLANS.md` for exact stage/slice status;
- `docs/architecture.md` for implemented transaction, composition, Demo, and
  client boundaries;
- `docs/public_client_contract.md` for exact implemented route/DTO/error/
  recovery status;
- `docs/run_protocol.md` for implemented Session-backed activation evidence;
- `docs/structured_player_character_contract.md` for truthful downstream
  implementation status only;
- `docs/structured_player_character_implementation_plan.md` for Phase 8 slice
  status while preserving Phase 6/7; and
- this plan for actual paths, evidence, reviews, and residual limits.

Do not edit completed P5-S1, P5-S2, or P5-S3 plans. Do not describe Phase 8 as
complete while required evidence, synchronization, or independent review is
missing.

## 25. Explicit exclusions

Phase 8 does not authorize:

- P5-S4 or any reinterpretation of Phase 5;
- any P5-S3 change, re-review, validation repeat, race reopening, or new
  retirement behavior;
- Phase 6 subject-reference implementation or Phase 7 implementation;
- full Phase 3.3 Run Protocol, difficulty/world profiles, entry-world
  catalogue, world/visit identity, later-world selection, revisits, or
  world-line transitions;
- public Run read/list/search/admin, later Session admission, resume by Run or
  character, Run completion/termination, binding historicalization, unbinding,
  rebinding, switching, transfer, or replacement;
- reactivation, resurrection, continuity return, final-death redesign, or
  bound-character retirement;
- structured character profile editing, general patch, deletion, search,
  administration, full profile UI, or bulk operations;
- use of Structured Player Character declarations/development/preferences in
  mechanics, snapshots, prompts, Provider input, narrative, or content;
- Provider integration, protocol expansion, model selection, live calls,
  production credentials, billing, fallback, or candidate authority;
- production authentication, deployment, rollout, release, monitoring,
  production data, CORS, quotas, rate limits, or abuse controls;
- new narrative-generation systems, scenarios, worlds, content packs, NPC
  systems, relationship expansion, golden memory, combat, inventory, items,
  equipment, economy, rewards, progression, or broad character growth;
- frontend redesign, new visual systems, client-owned lifecycle logic,
  optimistic authoritative state, localStorage, URL authority, cross-tab,
  browser-close, cross-browser, cross-device, or multi-device recovery;
- schema, ORM, migration, dependency, configuration, generated, or lockfile
  changes;
- speculative future schema, generalized repositories, generic retry, outbox,
  saga, compensation, worker, queue, or distributed orchestration; and
- unrelated Run, Demo, Session, API, client, or documentation cleanup.

These exclusions are phase discipline, not permanent product rejection.

## 26. Risks and stop conditions

| Risk | Required response |
| --- | --- |
| Phase 8 is found already allocated or numbering authority changes | Stop for stage-identity adjudication; never select another number silently |
| P8-G0 approval or baseline becomes stale | Invalidate hashes/approval and refresh the candidate |
| Owned GET is treated as sufficient discovery despite no known ID | Keep P8-S1; do not require users to memorize opaque IDs |
| Collection becomes general search/admin/pagination | Stop and narrow to the fixed eligible collection |
| Static character definition is conflated with Structured Player Character | Fail tests/review; keep it server-selected and explicitly separate |
| Scenario is relabeled as world or visit | Stop; Phase 8 has no world/visit identity |
| Client can submit Run/line/Session/lifecycle/binding authority | Reject the design before implementation |
| Admission splits across independently committed services | Stop; preserve one entry-owned UoW/commit |
| Exact replay cannot be reconstructed stably from existing records | Stop for plan amendment; do not add a receipt table silently |
| Existing schema cannot represent revisions 1/2/3 and active state | Stop for separately reviewed migration assessment |
| Same-character concurrency bypasses the Player Character-first lock/order | Stop and correct topology-specific evidence; do not copy P5-S3 assumptions |
| Scenario ending is treated as Run completion/termination | Stop; keep the Run active until later authority exists |
| Active binding is cleared to make the character reusable | Stop; historicalization requires later Run-owned terminal authority |
| Demo implementation weakens production invariants or reads normal secrets | Stop; preserve independent process-local composition |
| Web needs a new recovery identity or cached authority | Stop for explicit contract review; do not extend storage silently |
| Phase 6 memory subject work becomes necessary | Record it as an external prerequisite; do not absorb it into Phase 8 |
| A Phase 7 closeout feature is required | Reuse only an already implemented seam; do not mark Phase 7 complete |
| Any path budget, required verification, documentation sync, or independent review fails | Stop in the owning slice and report the exact blocker |

## 27. Phase 6/7 prerequisite assessment and future seams

Phase 6 is **not a Phase 8 prerequisite**. Phase 8 creates no new
memory/relationship/consequence fact and does not change current
`PlayerMemoryState`. Session participation supplies explicit Run association,
but current Session-local memory remains under its existing authority. Any
future promotion of gameplay facts to persistent character subjects must use
Phase 6 or another separately approved adjacent-system contract.

Phase 7 is **not a Phase 8 prerequisite**. Its existing generic regression and
closeout allocation remains unimplemented. Phase 8 defines its own bounded
evidence/status slice and does not import or complete Phase 7.

Future separately approved stages may add:

- Phase 3.3-native protocol/world admission and compatibility for Phase 8
  Session-backed Runs;
- additional Sessions/scenarios within the same active line;
- Run completion/termination and atomic binding historicalization;
- explicit Run resume/discovery;
- Structured Player Character context compilation for mechanics/narration;
- Phase 6 subject-bound memory/relationship/consequence facts;
- profile UI, progression, content, NPC, combat, inventory, and production
  platform work.

These are non-binding extension seams. Phase 8 remains only the minimum
playable backbone.

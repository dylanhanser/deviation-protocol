# Structured Player Character P8-S2 Atomic Run Entry Implementation Plan

## 1. Status, authority, and exact gate

Status: **Dedicated P8-S2 implementation-plan candidate created from the clean
published P8-S1 baseline and corrected after terminal independent review. That
review accepted the 32-character persistence and MySQL-current-read corrections
but found one material defect in the catalogue-independent snapshot
reconstruction. The candidate now corrects that single defect with the verified
strict JSON-mode entry and complete structural round trip. One narrow
independent read-only re-review of this correction and its direct regression is
pending. This candidate is not approved, implemented, staged, committed,
pushed, or published.**

This document is the implementation-executable refinement for only Phase 8
Slice P8-S2, **Atomic internal Run entry**. It is subordinate to the published
[Phase 8 plan](structured_player_character_run_playable_loop_plan.md) and the
narrower retained authorities listed in section 3. It resolves the persistent
protocol details deliberately left for the dedicated slice plan without
changing the approved product outcome, public contract, or later-slice
allocation.

The sole operative successful verdict for an independent review of the exact
complete four-document planning candidate is:

```text
STRUCTURED_PLAYER_CHARACTER_P8_S2_PLAN_REVIEW_APPROVED
```

The four-document candidate consists exactly of this new document plus the
minimal candidate-registration edits in `PLANS.md`,
`docs/structured_player_character_run_playable_loop_plan.md`, and
`docs/structured_player_character_implementation_plan.md`. Candidate hashes
are recorded outside the candidate after all edits are frozen. Generic
`APPROVED`, this document's candidate-preparation verdict, the earlier Phase 8
planning verdict, implementation-review verdicts, failure verdicts, and any
differently named token are non-operative. Any byte change to any of the four
files invalidates the hashes and any approval.

Implementation may not begin until all of these conditions hold in order:

1. one narrow independent read-only re-review of the strict JSON-mode
   correction, its direct structural-round-trip regression, and preservation of
   the two terminally accepted corrections inspects the exact four files and
   hashes and returns the sole verdict above;
2. separate authorization stages and commits exactly those approved bytes;
3. the user pushes that documentation commit;
4. `main`, `HEAD`, and local `origin/main` are then equal at the pushed commit,
   ahead/behind is `0/0`, and the index, worktree, and normal untracked set are
   clean; and
5. the user separately authorizes P8-S2 implementation against that clean
   published baseline.

This candidate does not satisfy any of those future gates by describing them.

## 2. Candidate baseline and present boundary

| Fact | Frozen planning value |
| --- | --- |
| Repository | `D:\deviation-protocol` |
| Branch | `main` |
| `HEAD` | `95ffe4019e2a69967dfae1fee2a1ecba4a628381` |
| Local `main` | `95ffe4019e2a69967dfae1fee2a1ecba4a628381` |
| Local `origin/main` | `95ffe4019e2a69967dfae1fee2a1ecba4a628381` |
| Ahead/behind | `0/0` |
| Baseline subject | `feat(player-character): add eligible Run-entry discovery` |
| P8-S1 | Implemented, independently accepted, committed, and published |
| P8-S2 | Strict JSON-mode correction applied after terminal review; narrow independent re-review pending; runtime work not begun |
| Initial Git state | Clean worktree, empty index, no untracked path |
| Remote activity | None |

A relevant baseline change while this candidate is pending invokes the
pending-plan baseline-invalidation rule in
[Codex Workflow](engineering/codex_workflow.md). Stale facts require corrected
candidate bytes, new identities, and a fresh independent review; a prior hash
or verdict cannot be preserved for convenience.

P8-S2 makes no public API, OpenAPI, Demo, Web, migration, schema, dependency,
configuration, or Provider change. It creates no runtime capability during
this planning task.

## 3. Controlling authority and precedence

The following authorities were used, with narrower authority controlling its
own subject:

1. `AGENTS.md`,
   [Engineering Guardrails](engineering/guardrails.md), and
   [Codex Workflow](engineering/codex_workflow.md) control repository,
   authority, persistence, verification, review, and Git safety.
2. [`PLANS.md`](../PLANS.md) controls current stage status and roadmap
   placement.
3. The
   [Phase 8 plan](structured_player_character_run_playable_loop_plan.md)
   controls the accepted P8-S2 outcome, slice order, transaction boundary,
   exclusions, and maximum path budgets.
4. The
   [Structured Player Character downstream plan](structured_player_character_implementation_plan.md)
   and
   [contract](structured_player_character_contract.md) control character
   identity, controller ownership, lifecycle, exact revision references, and
   active-binding cardinality.
5. The [Run Protocol](run_protocol.md) controls the narrow Session-backed
   activation amendment and preserves the deferral of full Phase 3.3 behavior.
6. [Architecture](architecture.md), the
   [Public Client Contract](public_client_contract.md), migration
   `20260729_0005`, and committed source control current implementation facts,
   existing public effects, storage, and dependency direction.

A conflict with one of those retained boundaries is a stop condition. This
plan does not reinterpret P8-S1 discovery as an authorization capability.

## 4. Frozen slice outcome and exclusions

### 4.1 Normative outcome

P8-S2 adds one internal application operation and one transaction owner. For a
fresh eligible request, exactly one UoW and one successful commit atomically:

1. create Run/current revision 1 at `pre_first_turn` and its existing creation
   receipt;
2. immutably bind the exact active Player Character reference in Run revision
   2 and write the existing binding mutation receipt;
3. create the existing initial Session row, `ScenarioStarted` event, memory
   effects, and version-zero snapshot;
4. create first Session participation in Run revision 3, retain
   `ATTACH_SESSION`, change the Run lifecycle to `active`, and write the
   existing attachment mutation receipt; and
5. publish success only after the one commit returns.

The Player Character itself is not mutated. Its locked pre-entry revision is
the immutable revision referenced by Run revisions 2 and 3. “Revision 1/2/3”
in this slice always means the Run revision family, not three Player Character
revisions.

### 4.2 Preserved decisions

- Controller authority is server-resolved before UoW construction.
- Discovery output is advisory; all ownership and eligibility are rechecked
  under the Player Character lock.
- The existing `run_creation_receipts.operation_evidence_canonical` column is
  the only composite-evidence carrier.
- One independently decodable composite representation is stored. No P8
  receipt table, reservation store, pending row, or second evidence store is
  added.
- Existing creation and mutation receipt tables continue to hold the Run
  creation, binding, and attachment receipts. Their existence is not a new P8
  store.
- Historical source-only Run creation receipts remain readable and retain
  their original fingerprint and revision-one validation rules.
- Exact entry replay occurs only after current controller ownership and stored
  evidence integrity are proven. It returns persisted stable result data with
  no mutation and no commit.
- Incompatible key reuse is `IDEMPOTENCY_CONFLICT`.
- There is no generic retry, nested commit, second UoW recovery, saga, outbox,
  compensation, or uncertain-commit recovery.

### 4.3 Exclusions

P8-S2 does not implement or alter:

- P8-S3 `POST /v1/runs`, API composition, public DTOs/errors, or OpenAPI;
- P8-S4 Demo persistence/composition;
- P8-S5 Web/client behavior;
- P8-S6 cross-surface evidence or Phase 8 closure;
- Run completion or termination, binding historicalization, unbinding,
  rebinding, character switching, or transfer;
- later Session or scenario admission, scenario selection after admission,
  Run discovery/resume, or continuous-line continuation;
- world, visit, entry-world, full Run Protocol, Provider, narrative, content,
  profile, memory-subject, NPC, combat, inventory, or progression behavior;
- a schema, ORM model, Alembic migration, backfill, historical receipt rewrite,
  dependency, or configuration change; or
- any public behavior.

## 5. Internal application contract

### 5.1 Command and result

`application/run_entry_service.py` introduces strict, frozen, extra-forbid
application models with these exact logical shapes. They are internal models,
not public request or response DTOs.

```text
RunEntryCommand
  public_operation_key: RunEntryPublicOperationKey
  player_character_id: PlayerCharacterId
  expected_record_revision: PlayerCharacterRevision
  scenario_id: DefinitionId

RunEntryResult
  run_id: RunId
  session_id: str
  scenario_id: DefinitionId
  player_character: PlayerCharacterSelfProjection
```

`RunEntryPublicOperationKey` has exactly the existing opaque identifier grammar
`^[A-Za-z0-9][A-Za-z0-9_.:-]*$`, is ASCII, and is 1 through 128 characters.
`session_id` is revalidated under the existing opaque Session/Run bound and is
1 through 64 characters in the current schema. The result's character is a
new detached four-field projection built only after the immutable referenced
Player Character revision has been validated. It is never a live aggregate
reference.

The service signature is conceptually:

```text
RunEntryService.enter(
    principal: RequestPrincipal,
    *,
    command: RunEntryCommand,
) -> RunEntryResult | RunEntryDecision
```

The `RequestPrincipal` remains a separate trusted application argument. It is
not embedded in the command, composite evidence, receipt result, or public
result.

### 5.2 Decisions and exceptions

`RunEntryDecision` carries exactly one of these expected decision codes:

| Code | Meaning | Future P8-S3 mapping |
| --- | --- | --- |
| `AUTHORIZATION_FAILED` | Principal cannot resolve, target is missing/foreign, or a decoded receipt belongs to another controller | sanitized 404 |
| `IDEMPOTENCY_CONFLICT` | Same controller-scoped internal key has valid but non-equivalent evidence, including a valid historical receipt | 409 |
| `PLAYER_CHARACTER_STALE` | Receipt is absent and locked current revision differs from the command | 409 |
| `PLAYER_CHARACTER_NOT_ELIGIBLE` | Receipt is absent and character is inactive, version-exhausted, or already actively bound | 409 |
| `INVALID_SCENARIO_DEFINITION` | Receipt is absent and current public scenario/default-definition eligibility fails | 422 |
| `RUN_ENTRY_CONFLICT` | A fresh write loses a Run, Session, participation, receipt, active-binding, or CAS uniqueness race not resolved by the already ordered receipt check | 409 |

Malformed trusted inputs, corrupt or impossible persisted evidence, repository
failures, generator failures, and commit failures are not ordinary decisions.
Their existing narrow exceptions propagate to the future adapter's sanitized
500 boundary. `asyncio.CancelledError` propagates unchanged. P8-S2 adds no
broad exception translation.

## 6. Composite creation-evidence byte contract

### 6.1 Binary envelope and version namespace

The P8-S2 composite stored value is:

```text
FAMILY_MAGIC || VERSION_OCTET || CANONICAL_JSON
```

The exact 12-byte family magic is:

```text
89 44 50 38 53 32 43 45 0d 0a 1a 0a
```

That is `0x89` followed by ASCII `DP8S2CE`, CR, LF, SUB, LF. Byte offset 12 is
the unsigned version octet. P8-S2 admits only `0x01`. Byte offset 13 begins the
UTF-8 JSON payload. There is no BOM, delimiter, terminator, compression,
encryption, base64 wrapper, or trailing byte.

The first byte `0x89` reserves the complete composite family namespace. All
future versions in this family must retain the same first byte and 12-byte
magic and select another version octet. P8-S2 does not define or accept such a
version.

The complete stored value must be between 14 and 4,096 bytes inclusive, so the
JSON payload is between 1 and 4,083 bytes. The actual required object is larger
than the mechanical minimum; an empty or incomplete payload is rejected. The
database column remains `MEDIUMBLOB`, but the application codec enforces this
smaller bound both before write and after load.

### 6.2 Exact logical object

After the header, the JSON payload is one object represented in the application
as `RunEntryCreationEvidence`, with exactly these required fields and no
others:

```json
{
  "controller_operation": {
    "controller_binding": {"value": "controller.example"},
    "public_operation_key": "entry.example"
  },
  "evidence_schema": "run-entry.creation-evidence/v1",
  "player_character": {
    "player_character_id": {"value": "pc.example"},
    "pre_entry_record_revision": {"value": 1}
  },
  "scenario": {
    "content_version": "death-certificate-1.1.0",
    "default_character_definition_id": "character.death_certificate.investigator",
    "scenario_id": "death_certificate"
  },
  "trusted_run_source": {
    "source_reference": {"value": "source.production-run"}
  }
}
```

In this section, “ASCII opaque grammar” and “ASCII safe-ID grammar” both mean
the repository's exact `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` regular expression;
each admitted character is one byte in ASCII/UTF-8. The exact field contract
is:

| Path | JSON type | Required value/bound |
| --- | --- | --- |
| `evidence_schema` | string | exact ASCII `run-entry.creation-evidence/v1` |
| `controller_operation` | object | exact two fields below |
| `.controller_binding` | object | exact sole field `value` |
| `.controller_binding.value` | string | `ControllerBindingRef`; ASCII opaque grammar; 1..128 bytes |
| `.public_operation_key` | string | `RunEntryPublicOperationKey`; ASCII opaque grammar; 1..128 bytes |
| `player_character` | object | exact two fields below |
| `.player_character_id` | object | exact sole field `value` |
| `.player_character_id.value` | string | `PlayerCharacterId`; ASCII opaque grammar; 1..128 bytes |
| `.pre_entry_record_revision` | object | exact sole field `value` |
| `.pre_entry_record_revision.value` | integer | positive signed-64-bit; `1..9223372036854775807` |
| `scenario` | object | exact three fields below |
| `.scenario_id` | string | `DefinitionId`; ASCII safe-ID grammar; 1..128 bytes |
| `.content_version` | string | `DefinitionId` narrowed for existing Session persistence; ASCII safe-ID grammar; 1..32 characters and therefore 1..32 ASCII/UTF-8 bytes |
| `.default_character_definition_id` | string | `DefinitionId`; ASCII safe-ID grammar; 1..128 bytes |
| `trusted_run_source` | object | exact sole field `source_reference` |
| `.source_reference` | object | exact sole field `value` |
| `.source_reference.value` | string | `RunAuthoritySourceRef`; ASCII opaque grammar; 1..128 bytes |

There are no optional fields. `null`, arrays, floats, exponent forms, negative
or zero revisions, JSON booleans, and byte-valued data fields are forbidden.
The fixed binary header is not a data field and has no alternative textual
representation.

The `scenario.content_version` maximum is the existing
`game_sessions.scenario_version VARCHAR(32)`/ORM `String(32)` width. MySQL and
SQLAlchemy express this width in characters. The admitted `DefinitionId`
grammar is ASCII-only, so every admitted character is one Unicode code point
and one UTF-8 byte; the persistence, composite, Session, event, snapshot, and
comparison limits are therefore the same exact 32-character/32-byte maximum.
The broader 128-character `DefinitionId` maximum does not widen this one P8-S2
field.

Every advisory/discovered scenario content version and the authoritative
current value re-resolved for fresh entry must independently satisfy this
limit. The transaction-time value is checked again by the Session staging
helper before it constructs a `GameSession` and before any P8-S2 row is staged.
An over-bound current public/default scenario definition is
`INVALID_SCENARIO_DEFINITION`; it does not reach a repository or database
error. On replay, the strict composite decoder rejects a 33-through-128-
character stored component as malformed trusted evidence, and the persisted
Session/snapshot validation independently enforces the same bound as an
integrity condition. There is no truncation, trimming, normalization, hashing
substitute, alternate value, new column, or migration. The exact admitted
value is reused unchanged in evidence, fingerprint input, receipt validation,
Session persistence, `ScenarioStarted`, snapshot bindings, and every replay
comparison. `RunEntryCommand` carries only the scenario ID and has no caller-
supplied content-version override; command evaluation and replay equivalence
therefore bind that scenario ID to this one exact server-derived value.

### 6.3 Canonical JSON and exact-input rules

The payload uses the repository's standard-library-backed
`canonical_run_operation_bytes` rules:

- every string and object key is NFC-normalized before encoding;
- all admitted values in this schema must additionally pass their ASCII
  identifier grammar, so normalization cannot create a second admitted form;
- object keys at every level are sorted in ascending Unicode-code-point order;
- arrays are not present;
- the sole integer is emitted as its shortest positive base-10 JSON integer,
  with no sign, leading zero, decimal point, or exponent;
- `ensure_ascii=False`, `allow_nan=False`, separators `,` and `:` and no
  indentation produce UTF-8 with no whitespace outside string values;
- `/` is not escaped, although no current field needs it; ASCII identifier
  characters are emitted literally;
- there is no leading/trailing whitespace, BOM, or trailing newline; and
- total bytes are the fixed header followed immediately by that JSON.

The decoder first enforces the byte bound, family/version selection, strict
UTF-8, and one top-level object. It rejects duplicate members at every nesting
level before model construction, rejects floats and non-standard constants,
validates strict extra-forbid typed models, re-encodes the validated model, and
requires byte-for-byte equality with the complete stored value. Therefore
alternate key order, any whitespace, `\u` spelling of an ASCII character,
unknown members, duplicate members, missing members, overlong identifiers,
invalid Unicode, noncanonical integers, or trailing bytes fail closed. Nothing
is trimmed, case-folded, repaired, filled from defaults, or salvaged.

### 6.4 Normative bytes and hash vector

For the object shown in section 6.2, the exact canonical JSON is this one line:

```text
{"controller_operation":{"controller_binding":{"value":"controller.example"},"public_operation_key":"entry.example"},"evidence_schema":"run-entry.creation-evidence/v1","player_character":{"player_character_id":{"value":"pc.example"},"pre_entry_record_revision":{"value":1}},"scenario":{"content_version":"death-certificate-1.1.0","default_character_definition_id":"character.death_certificate.investigator","scenario_id":"death_certificate"},"trusted_run_source":{"source_reference":{"value":"source.production-run"}}}
```

It is 518 UTF-8 bytes. The 13-byte header including version is:

```text
89445038533243450d0a1a0a01
```

The complete stored evidence is 531 bytes. The exact bytes hashed for the P8
creation fingerprint are all 531 bytes—header, version octet, and JSON—with no
extra newline. Their SHA-256 is:

```text
98a071065169ed5ad2f3052816da493dd1cd9cff8838d8f050af9ce3c555ee55
```

The example content version `death-certificate-1.1.0` is 23 ASCII characters,
so the corrected persistence limit changes none of these canonical bytes,
their 531-byte count, or this digest.

No dependency is added. The implementation uses `json`, `unicodedata`,
`hashlib`, existing strict Pydantic models, and the existing canonical Run
encoder.

## 7. Historical/composite decoder selection

`run_persistence.py` adds one compatibility entry point while leaving the
existing strict historical `creation_operation_evidence_from_storage()`
decoder and its encoder unchanged.

Selection is exact and mutually exclusive:

1. Empty input fails immediately.
2. If byte zero is `0x89`, select the composite branch only. Require the full
   12-byte magic. A short, damaged, or different magic is malformed composite
   evidence. Require a version octet. Version `0x01` uses the P8 decoder; every
   other version is an unknown composite version. Neither condition may call
   the historical decoder.
3. If byte zero is `0x7b` (`{`), select the historical branch only and call the
   unchanged strict source-only decoder. Failure may not call the composite
   decoder.
4. Every other first byte is malformed creation evidence and selects neither
   decoder.

The non-overlap proof is structural:

- a valid historical `CreateRunCommand` is canonical JSON for one object and
  therefore always begins with `0x7b`; its only field is
  `source_reference`, and strict extra-forbid revalidation plus exact
  re-encoding rejects a composite JSON object;
- every valid composite begins with reserved byte `0x89`, which is neither
  `{` nor a valid leading byte for the historical UTF-8 JSON object; and
- an unknown future composite version retains the `0x89` family namespace and
  is rejected in the composite branch before any JSON model or historical
  decoder is selected.

Calling the historical decoder directly with intact composite bytes rejects
strict UTF-8/JSON and is covered by a regression. If a stored P8 value is
substituted wholesale with otherwise valid historical bytes, it can only enter
the historical branch; its independently recomputed historical fingerprint
cannot equal the stored P8 composite fingerprint, and the P8 entry service
also refuses a valid historical family as entry replay. It is never silently
reinterpreted as a composite success.

A valid historical receipt continues to work through the legacy
`RunService.create_run()` and complete Run-family reconstruction under its
original source-only fingerprint rules. If such a receipt is encountered under
the derived P8 entry lookup key, `RunEntryService` returns
`IDEMPOTENCY_CONFLICT` after ownership and complete historical integrity are
proven; it does not rewrite it, add composite evidence, or infer a P8 result.

## 8. Composite component authority and comparison

| Component | Authoritative source | Canonical representation | Fingerprint/load comparison | Failure meaning |
| --- | --- | --- | --- | --- |
| Controller-scoped public operation | Server-resolved `ControllerBindingRef` plus validated public key | `controller_operation` object | Recompute all four internal IDs; compare stored controller to current resolved controller and stored key to incoming key | another controller is authorization failure; same controller with another key under the same digest is conflict; stored-byte/ID mismatch is integrity failure |
| Pre-entry Player Character | Current canonical record returned by P4-S1 same-UoW owned lock | `player_character_id` plus exact positive `pre_entry_record_revision` | Fresh: compare to locked current and command. Replay: compare incoming public fields to stored evidence, then compare to revision-2/3 binding and repository-validated immutable Player Character revision | current mismatch on fresh is stale; inactive/version-exhausted/bound fresh state is ineligible; stored substitution is integrity failure |
| Scenario | Incoming `scenario_id`, admitted only through current public `ScenarioCatalog` | `scenario_id` and exact server-resolved `content_version`, with the latter narrowed to 1..32 ASCII characters | Fresh: current public definition, re-resolved and revalidated before Session construction or staging. Replay: strict composite plus persisted Session row, exact initial `ScenarioStarted` event, and strict current snapshot, never the current catalogue | unavailable/ineligible/over-bound fresh definition is invalid scenario; over-bound or mismatched persisted evidence is integrity failure |
| Current server default definition | Current scenario `public_client.default_character_definition_id`, cross-validated against the current `ContentCatalog` and playable/default rules | `default_character_definition_id` | Fresh: current scenario/content catalog. Replay: persisted Session `character_definition_id` plus the strictly reconstructed current snapshot's unchanged player-definition binding, not a newly selected default | fresh absence or invalid default is invalid scenario; persisted substitution is integrity failure |
| Trusted historical Run source | Entry service's configured `RunAuthoritySourceRef`, identical to the source used by Run create/bind/attach staging | exact nested historical `source_reference` object | Compare to revision-one creation provenance and to binding/attachment command/provenance evidence | any difference is trusted-evidence tampering/integrity failure |

The public operation key, Player Character ID/revision, and scenario ID are
public inputs. Controller binding, scenario content version, default static
character-definition ID, and Run source are server-derived. Revision-one
source provenance, the immutable Player Character revision, Run history,
receipts, Session row/event/snapshot, binding, and participation are trusted
persisted evidence only after their existing strict repositories validate
them.

An earlier public-catalogue discovery is advisory and supplies no content-
version authority to `RunEntryCommand`. Fresh entry re-resolves the current
scenario/default through the Session application-service path, applies the
32-character limit to any discovered value and again to that transaction-time
authoritative value, and uses only the latter exact value. A change between
discovery and entry is ordinary staleness: the current value either passes all
fresh gates and is used consistently or yields `INVALID_SCENARIO_DEFINITION`;
no discovered value is silently retained. Replay performs no such current-
catalogue resolution and trusts only cross-validated persisted evidence.

Replay never reapplies the fresh “unbound”, current revision, active lifecycle,
successor-capacity, or current-catalogue gates to the already committed entry.
It proves current ownership through the locked current character, then validates
the original immutable pre-entry revision and persisted Session/Run family.
This permits a stable replay if the current catalogue later changes while
preventing a new operation from using an unavailable current definition.

## 9. Deterministic internal identifier construction

### 9.1 Inputs and preimage

No existing general identity primitive satisfies all four roles and the
controller-scoped deterministic requirement. P8-S2 therefore adds one small
pure derivation in `application/run_operations.py`.

For each purpose, let:

- `P` be the exact ASCII purpose bytes from the closed set below;
- `C` be `controller_binding.value` encoded as strict ASCII/UTF-8;
- `K` be the exact public operation-key characters encoded as strict
  ASCII/UTF-8; and
- `U16BE(n)` be exactly two unsigned big-endian bytes. Length is measured in
  bytes after validation, not in code points.

The exact preimage is:

```text
ASCII("deviation-protocol:p8-s2:internal-id:v1")
|| 00
|| U16BE(len(P)) || P
|| U16BE(len(C)) || C
|| U16BE(len(K)) || K
```

The closed purposes are:

| Role | Exact `P` bytes |
| --- | --- |
| Run creation operation ID | ASCII `run.create/v1` |
| Run binding operation ID | ASCII `run.bind-player-character/v1` |
| Run first-participation operation ID | ASCII `run.attach-session/v1` |
| Session creation-request ID | ASCII `session.create/v1` |

Controller and key are each 1..128 bytes. The longest purpose is 28 bytes; the
complete preimage is therefore at most 330 bytes. NUL cannot occur in a
component under the opaque grammar, but length prefixes are still mandatory;
no delimiter-only or ambiguous concatenation is permitted.

### 9.2 Digest, output, equality, and collision treatment

The output for every role is the 64-character lowercase hexadecimal encoding
of `SHA-256(preimage)`, with no prefix, braces, hyphens, or terminator. Run
outputs are revalidated as `RunOperationId`. The Session output is revalidated
as the existing 1..64 Session creation-request identity and fits the existing
`game_sessions.creation_client_request_id VARCHAR(64)` column.

Equality is exact, case-sensitive value equality after type validation.
Fingerprint or ID equality alone never establishes command equivalence. On
load/replay the implementation must:

1. decode and byte-revalidate the stored composite;
2. recompute each internal ID from the decoded controller/key;
3. compare the creation ID to receipt key and revision-one provenance, the
   binding ID to the immutable binding plus revision-two receipt/provenance,
   the attachment ID to participation plus revision-three
   receipt/provenance, and the Session ID to
   `creation_client_request_id`;
4. separately compare all decoded typed fields to incoming public fields and
   authoritative persisted targets.

A hypothetical digest collision is never accepted as replay merely because
the 64 hexadecimal characters match. Another decoded controller produces
`AUTHORIZATION_FAILED`; the same controller with a different key or different
public command fields produces `IDEMPOTENCY_CONFLICT`; inconsistent persisted
bindings produce an integrity failure. A fresh database uniqueness collision
without an already validated exact receipt is `RUN_ENTRY_CONFLICT` and rolls
back. There is no identity retry.

### 9.3 Normative derivation vectors

With controller `controller.example` and key `entry.example`, the exact outputs
are:

| Purpose | Derived value |
| --- | --- |
| `run.create/v1` | `a36075084453ebcccb61be1755c270c7e03f177181fdd2871d467684f847ef3a` |
| `run.bind-player-character/v1` | `e2cbe6dfd4475fd62a650ea3f01d7f4d37fb35e5863e4b53c1a07dc35f232277` |
| `run.attach-session/v1` | `a3759a0a0e2d2d67349d37bcb264d76e10507abeb015ebe4cc92d45caff4c62c` |
| `session.create/v1` | `19891ce8ad0511e9c02ec73c7b9e05a619a0b211edbe06bbe72fb599e9e21f9e` |

The complete `run.create/v1` preimage is 90 bytes and has this hexadecimal
form:

```text
646576696174696f6e2d70726f746f636f6c3a70382d73323a696e7465726e616c2d69643a763100000d72756e2e6372656174652f76310012636f6e74726f6c6c65722e6578616d706c65000d656e7472792e6578616d706c65
```

## 10. Fingerprints and existing-schema mapping

### 10.1 Creation receipt

For P8 composite creation only:

- algorithm: SHA-256;
- exact input: the complete canonical composite bytes from section 6,
  including the 13-byte magic/version header;
- application form: `RunOperationFingerprint.value`, 64 lowercase hex;
- `run_creation_receipts.fingerprint`: the exact raw 32 digest bytes;
- `run_creation_receipts.receipt_canonical`: the existing canonical
  `StoredRunSuccessReceipt`, whose fingerprint field contains the same
  lowercase hex;
- `run_creation_receipts.operation_evidence_canonical`: the exact complete
  composite bytes; and
- result columns: unchanged revision-one `run.create-result/v1`, Run/line ID,
  `pre_first_turn`, and state version 1.

Creation computes the composite bytes once from the validated application
model, computes SHA-256, constructs the receipt, and gives the validated model
to the narrow repository `add_with_evidence` method. The repository independently
re-encodes it, recomputes SHA-256, compares receipt/row values, and refuses a
caller-supplied arbitrary byte blob.

Load selects exactly one decoder, exact-reencodes the model, recomputes the
digest, and compares in this order:

1. namespace/key/command/result scalar columns to the canonical receipt;
2. raw row fingerprint to SHA-256 of independently reconstructed evidence;
3. canonical receipt fingerprint hex to that same digest;
4. receipt result to revision-one `creation_result`;
5. decoded trusted source, derived create operation ID, and receipt timestamp
   to revision-one provenance; and
6. P8-only component bindings to the complete Run/Session/character family.

Historical source-only receipts retain the current algorithm and exact bytes:
`create_run_fingerprint(CreateRunCommand)` remains SHA-256 over canonical JSON
containing `command_kind`, `operation_namespace`, and `source_reference`.
Their `operation_evidence_canonical` remains the exact canonical
`CreateRunCommand` bytes. No historical row or digest changes.

### 10.2 Binding and participation receipts

The existing algorithms remain unchanged:

| Receipt | SHA-256 input | Persistence |
| --- | --- | --- |
| Revision-2 binding | canonical JSON with exact `command_kind=BIND_PLAYER_CHARACTER`, line ID, `expected_state_version=1`, derived binding operation ID, namespace `run.bind-player-character/v1`, Run ID, trusted source, and target Player Character ID | raw digest in `run_mutation_receipts.fingerprint`; hex in `receipt_canonical`; exact `BindPlayerCharacterCommand` in `operation_evidence_canonical` |
| Revision-3 participation/activation | canonical JSON with exact `command_kind=ATTACH_SESSION`, line ID, `expected_state_version=2`, derived attachment operation ID, namespace `run.attach-session/v1`, Run ID, issued Session ID, and trusted source | raw digest in `run_mutation_receipts.fingerprint`; hex in `receipt_canonical`; exact `AttachSessionCommand` in `operation_evidence_canonical` |

Their load path continues to decode command evidence, recompute with the
persisted operation ID, compare raw/hex fingerprint forms, validate result
columns, and bind each receipt to its adjacent immutable revision. Activation
changes only the revision-3 lifecycle/result value from the earlier generic
pre-first-turn behavior to the authorized `active` value; it adds no field or
fingerprint component.

### 10.3 Complete replay cross-check

No row is trusted merely because two stored values agree. Exact P8 replay
requires all of these independent comparisons:

- decoded controller/key -> recomputed creation operation ID -> receipt key and
  revision-one creation provenance;
- composite bytes -> SHA-256 -> raw fingerprint column and canonical receipt;
- receipt result Run/line/revision -> immutable revision 1;
- nested historical source -> revision-one source and the configured trusted
  Run source;
- decoded Player Character ID/pre-entry revision -> revision-2 binding and the
  independently loaded immutable Player Character revision; that revision must
  be supported and `active` at binding time;
- derived binding ID -> revision-2 provenance, binding envelope, and binding
  receipt;
- current Run -> exact revision 3, lifecycle `active`, unchanged active
  binding, one participation joined at version 3, and complete 1/2/3 history;
- derived attachment ID -> revision-3 provenance, participation, and attachment
  receipt;
- participation Session ID -> current-read locked Session row;
- derived Session creation-request ID -> Session
  `creation_client_request_id`;
- composite scenario ID/version/default definition -> Session row, exact
  initial `ScenarioStarted` event, and the explicit current-read Session
  snapshot, strictly reconstructed without a catalogue, whose stable Session,
  scenario/version, player, and player-definition bindings match; and
- creation/binding/attachment/Session timestamps -> the one transaction time
  wherever existing rows persist that time.

The stable `RunEntryResult` is then built from the receipt Run ID, first
participation Session ID, composite/persisted scenario ID, and exact immutable
bound four-field Player Character projection. It is not built from newly issued
identities, current catalogue defaults, current Session phase, or the incoming
request alone.

## 11. Domain and service changes

### 11.1 Run domain

`domain/run.py` admits one new constructible active shape and no new token:

- revision 1: `CREATE`, `pre_first_turn`, unbound, no participation;
- revision 2: `BIND_PLAYER_CHARACTER`, `pre_first_turn`, exact active binding,
  no participation; and
- revision 3: `ATTACH_SESSION`, `active`, the same byte-equivalent binding, and
  exactly one participation whose `joined_state_version` is 3.

A new pure operation in `application/run_operations.py` constructs that exact
revision-3 successor. It requires revision 2, `pre_first_turn`, an active
binding, no prior participation, expected version 2, and matching Run/line.
It preserves binding and creation provenance exactly, uses mutation kind
`ATTACH_SESSION`, and changes only the authorized lifecycle/participation/
provenance/version fields. The generic historical attachment helper remains
unchanged and cannot be used by entry activation. The validator rejects an
active unbound Run, active revision 1 or 2, active state without exactly the
first participation, or a P8 entry successor beyond revision 3. Later Session
admission remains outside this slice.

### 11.2 Layer ownership

| Owner | Exact responsibility |
| --- | --- |
| `application/run_operations.py` | Strict composite models, deterministic header+canonical encoding used for creation-time hashing, SHA-256 function, internal-ID derivation, pure revision-3 activation, and existing receipt fingerprints |
| `infrastructure/run_persistence.py` | Stored-byte size check, mutually exclusive family/version selector, strict composite decode, unchanged historical decoder entry, exact re-encoding, independent fingerprint recomputation, and complete stored-family validation |
| `infrastructure/repositories.py` | SQL row mapping, narrow `get_with_evidence`/`add_with_evidence`, authoritative Run-family reconstruction, immutable Player Character revision load, initial Session-event load, an explicit locking/current Session-snapshot read, flush-only writes, and precise uniqueness translation |
| `application/run_service.py` | Same-UoW Run staging helpers for entry creation, binding, and first-participation activation; no UoW construction or commit in those helpers |
| `application/session_service.py` | Current public-scenario/default resolution with the 32-character persistence check, detached initial Session construction, same-UoW initialization staging, and strict catalogue-independent reconstruction/validation of persisted Session initialization |
| `application/run_entry_service.py` | Controller resolution, four ID derivations, one-UoW orchestration, ordering, decisions, stable replay construction, one commit, and no transport concerns |
| `application/ports.py` | Application-owned evidence/result carriers and narrow initialization-event/current-snapshot repository methods; no SQLAlchemy type |

`ports.py` defines frozen `StoredRunCreationEvidence` with exactly
`receipt: StoredRunSuccessReceipt`, `evidence: CreateRunCommand |
RunEntryCreationEvidence`, and `evidence_canonical: bytes`.
`RunCreationReceiptRepository.get_with_evidence(key: RunReceiptKey) ->
StoredRunCreationEvidence | None` loads and validates that carrier, while
`add_with_evidence(receipt: StoredRunSuccessReceipt, evidence:
RunEntryCreationEvidence, *, created_at: datetime) -> None` accepts only the P8
composite model. `get()`/`add()` remain available with their historical
semantics and must not rewrite or synthesize composite evidence.

`GameSessionRepository` gains exactly two narrow replay methods:

- `get_initialization_event(session_id: str) -> DomainEvent | None` loads the
  immutable `sequence_no=1` event as a detached domain value for the Session
  service to validate as exact `ScenarioStarted` evidence; it never returns an
  ORM row; and
- `get_latest_snapshot_for_update(session_id: str) -> PersistedSnapshot | None`
  requires a genuine current/locking read of the one `game_snapshots` row whose
  primary key is that Session ID. The application-port default fails closed
  with `NotImplementedError`; it never falls back to `get_latest_snapshot()`.
  The SQLAlchemy repository implements an explicit
  `select(GameSnapshotRow).where(...).execution_options(populate_existing=True).with_for_update()`
  equivalent through the existing `AsyncSession`, then returns the same
  detached `PersistedSnapshot` carrier. `populate_existing` prevents an
  identity-map value from defeating the database current read.

Existing `get_owned_for_update()`, non-locking `get_latest_snapshot()`,
`get_by_creation_request()`, `add_initial_session()`, `next_event_sequence_no()`,
`persist_events()`, and `add_initial_snapshot()` remain the primitive Session
repository methods for their existing callers. No general event search or
general locking-query option is introduced. The non-abstract fail-closed port
default avoids forcing P8-S4 Demo persistence into this slice; normal P8-S2
composition uses the required SQLAlchemy override.

The coordinator also reuses `ControllerBindingResolver.resolve()`,
`PlayerCharacterBindingEvidenceReader.lock_owned_for_binding()`,
`ScenarioCatalog.scenario()`, and the existing Run repository append/current
CAS, binding, participation, and receipt methods. New Run/Session service
helpers only expose the pure and no-commit portions already assigned in the
table above; they are not new transaction owners.

Dependencies remain:

```text
api/infrastructure -> application -> domain
```

Domain and application import neither SQLAlchemy nor FastAPI. P8-S2 does not
touch API composition.

### 11.3 Strict catalogue-independent persisted Session validation

`SessionService.validate_run_entry_replay_initialization(...)` is the existing
authorized application-service path's internal helper for this responsibility.
It accepts only existing internal representations: the current-read
`PersistedSession`, current-read `PersistedSnapshot`, detached sequence-one
`DomainEvent`, the decoded `RunEntryCreationEvidence`, the derived Session
creation-request ID, and the already validated Run participation/binding/time
values. It creates no public DTO and does not own a UoW, query, mutation, or
commit. It returns a trusted detached `GameState` only after all checks pass.

The helper does **not** call `GameState.from_snapshot`,
`migrate_snapshot_payload`, `GameState.validate_against`,
`validate_player_memory_against`, `ScenarioCatalog`, or `ContentCatalog`.
P8-S2 snapshots are newly written current-schema evidence, so it requires
exact `schema_version == 3`. `PersistedSnapshot.state` is the repository's
actual JSON-compatible representation: SQLAlchemy loads the MySQL `JSON` value
as nested dictionaries, lists, and JSON scalars, and the repository detaches it
with `dict(row.state_json)`. The helper deep-copies that already-loaded mapping
as `original_payload`, preserves it unchanged for the complete comparison
below, and constructs the validation input with the existing standard-library
snapshot JSON behavior used by `GameState.memory_authority_fingerprint()` and
the Session snapshot stability evidence:

```python
canonical_json_bytes = json.dumps(
    original_payload,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("utf-8")
state = GameState.model_validate_json(canonical_json_bytes, strict=True)
```

These bytes are only an internal validation-input bridge derived from the
already-loaded persisted mapping. They do not replace or redefine the MySQL
snapshot value, any receipt encoding, API representation, the 518-byte
composite JSON body, or the complete 531-byte composite contract; they are not
written back or exposed and do not by themselves establish successful replay.
No alternate options, public serializer, or second persisted format are
introduced.

Strict JSON input validation permits only the JSON-to-internal representation
conversions inherent to Pydantic's strict JSON mode and required by the existing
models, including JSON array to tuple, JSON array to frozen set, and JSON string
to Enum. It is not a generally permissive or coercive validation mode. Existing
strict fields, extra-forbid model configurations, nested validators, identifier
bounds, Enum definitions, collection bounds, and model-version checks continue
to reject invalid scalar types and values, invalid Enum values, malformed
nested structures, unknown model fields, invalid identifiers, duplicate typed
records, bounded-collection overflow, and other violations of the current
model contract.

After that strict JSON-mode admission, the helper requires the complete
`state.to_snapshot() == original_payload` structural equality. This separate
structural round trip rejects a field dropped
or silently discarded, an unknown field accepted anywhere contrary to the
contract, a missing field supplied by a default, value normalization,
structural or collection-shape change, an altered persisted Enum
representation, reordered array data where order is semantically significant,
and any other non-identical persisted representation, including a value a
model validator would otherwise repair or canonicalize. A MySQL JSON object is
already a mapping with unique member names; no raw duplicate-member JSON parser
or parallel snapshot DTO is invented. The input mapping, locked Session,
detached event, ORM state, and stored JSON remain unchanged.

Only after strict JSON input validation and complete structural equality
succeed does the helper perform the following semantic replay validation. This
third stage binds the structurally trusted state to the authoritative Run,
Session, scenario, Player Character, participation, activation, and
initialization evidence without consulting mutable catalogue content:

1. Session and snapshot state versions are strict non-negative signed-64-bit
   integers and equal; Session/Run/participation identities and revisions have
   already passed their strict typed/repository checks.
2. Session ID/player, derived creation-request ID, scenario ID, exact 1..32-
   character scenario version, stored default character-definition ID,
   creation time, participation, active revision-3 Run, immutable revision-2
   Player Character binding, and revision-1/2/3 provenance agree with the
   decoded composite and existing receipts.
3. Snapshot `content_version`, player ID, player character-definition ID, and a
   required non-null scenario runtime's scenario ID/content version agree with
   the locked Session row and composite. The matching player-memory scenario
   record must exist with the same scenario/version and remain internally
   consistent with the runtime and memory sequence fields.
4. The immutable sequence-one event has the exact Session ID, turn ID
   `session-created`, sequence `1`, type `ScenarioStarted`, exact two-field
   scenario/version payload, and original transaction timestamp.
5. If the locked Session and snapshot still claim state version `0`, they must
   also claim turn `0`, `AWAITING_ACTION`, an active runtime, and an initial
   `STARTED` scenario-memory record sourced from that sequence-one event.
   A version-zero ended/advanced/missing-runtime shape is impossible. A later
   positive state version remains replayable, as already accepted, but must
   preserve every stable identity/version/definition binding above and satisfy
   the strict complete current snapshot structure.

Malformed structure maps to the existing `SnapshotInvalidError`; schema,
state-version, content-version, missing-snapshot, and Session-binding failures
retain the existing narrow `Snapshot*` classifications. Missing or mismatched
Session/event/Run/Player Character/binding/participation/activation evidence
after receipt ownership is proven is persisted integrity/impossible state and
propagates to the future sanitized 500 boundary, never an ordinary decision or
404. The helper never accepts two stored digests merely because they match,
never consults or substitutes the current catalogue, never mutates the Session
or returned input, never rewrites persisted JSON, and never commits. Therefore
removing or changing a current catalogue cannot change exact replay of valid
persisted P8-S2 evidence.

## 12. Exact transaction and replay algorithm

### 12.1 Work before the UoW

For every call, in order:

1. Strictly revalidate the actual `RequestPrincipal`, actual
   `RunEntryCommand`, and all nested carrier instances. No lossy dump/rebuild
   establishes trust.
2. Resolve the principal through `ControllerBindingResolver`. Missing,
   malformed, or noncanonical resolution returns `AUTHORIZATION_FAILED`; no
   UoW or identifier issuer is touched.
3. Derive the four deterministic internal IDs from the resolved controller and
   public key. Revalidate all outputs. These computations issue no Run, line,
   Session, seed, or event identity and make no write.
4. Construct one UoW. No other UoW is constructed anywhere in the call.

### 12.2 Common ownership lock and receipt placement

Inside the UoW:

1. Call the existing P4-S1
   `PlayerCharacterBindingEvidenceReader.lock_owned_for_binding()` first. It
   locks and strictly reconstructs the target current Player Character in the
   same UoW.
2. Missing or wrong-owner target returns `AUTHORIZATION_FAILED`. Malformed or
   mismatched surviving evidence raises the existing integrity error.
3. Validate only the returned target identity/controller proof at this common
   point. Do not yet reject current revision, lifecycle, successor capacity, or
   active binding.
4. Query the derived `run.create/v1` receipt key through
   `get_with_evidence()`. Receipt evaluation is therefore after ownership proof
   but before fresh-entry stale/eligibility/current-scenario rejection.

This placement lets an already-bound exact replay succeed without treating its
successful binding as fresh ineligibility, while a foreign or missing incoming
target cannot use a key to discover a receipt.

### 12.3 Existing-receipt path

If a receipt exists, perform these steps in order:

1. Require its strict receipt, selected evidence family, fingerprint, result
   columns, revision-one source binding, and complete referenced Run family to
   have passed repository validation. A malformed value never becomes a
   protocol decision.
2. If the selected family is valid historical source-only evidence, return
   `IDEMPOTENCY_CONFLICT`. Do not reinterpret or rewrite it.
3. For composite evidence, compare its controller with the currently resolved
   controller before exposing any result. A different controller returns
   `AUTHORIZATION_FAILED` and reveals no Run/Session/character value.
4. Recompute all four internal IDs from the decoded stored controller/key and
   cross-check their persisted targets. A stored-ID mismatch is integrity
   failure.
5. Compare the incoming public key, Player Character ID, expected revision,
   and scenario ID to the decoded composite with exact typed equality. Any
   difference returns `IDEMPOTENCY_CONFLICT`.
6. Lock the receipt result Run/current row and related immutable Run family by
   `RunRepository.get_for_update()`. Require the exact three-revision P8 shape,
   active binding, first participation, receipts, source, IDs, and immutable
   referenced Player Character revision described in section 10.3.
7. Extract the sole version-3 participation Session ID. Lock that exact Session
   row after the Run through `get_owned_for_update(session_id,
   current_principal.player_id)`. This SQLAlchemy `SELECT ... FOR UPDATE` is a
   MySQL current read. A missing/mismatched row after the receipt/controller/Run
   bindings are proven is impossible-state integrity failure, not a normal
   404.
8. Load and validate the immutable sequence-one initialization event only after
   the Session row lock. Then call
   `get_latest_snapshot_for_update(session_id)` for the exact same Session. Its
   explicit `SELECT ... FOR UPDATE` plus `populate_existing` must return the
   latest committed `game_snapshots` row even if the earlier receipt read
   established an older `REPEATABLE READ` consistent-read view. Absence is
   `SnapshotNotFoundError`; a repository/read/lock failure propagates.
9. Pass the locked/current detached Session and snapshot plus the event,
   decoded composite, derived Session ID, and already validated Run/character
   evidence to
   `SessionService.validate_run_entry_replay_initialization(...)`. Apply the
   exact catalogue-independent schema/round-trip/semantic checks in section
   11.3, including the 32-character version bound. No current content or
   scenario catalogue is read.
10. Construct the detached stable result from persisted evidence and return it.
   Do not call any issuer, append or CAS method, receipt add, Session create,
   explicit commit, or second UoW.

UoW exit performs the established read-only rollback/close because no commit
occurred. That rollback releases the Session/snapshot validation locks without
making a successful commit. Exact replay remains valid if the strictly
validated current Session gameplay state has advanced; the response contains
none of that mutable state.

### 12.4 Fresh-execution path

If the receipt is absent, perform these steps in order:

1. Compare the command revision to the locked current Player Character
   revision. Difference returns `PLAYER_CHARACTER_STALE`.
2. Require lifecycle `active` and a revision with successor capacity as
   retained Phase 8 eligibility rules. Otherwise return
   `PLAYER_CHARACTER_NOT_ELIGIBLE`.
3. Call `RunRepository.get_active_for_player_character_for_update()` while the
   Player Character lock remains held. If canonical active-binding evidence
   exists, return `PLAYER_CHARACTER_NOT_ELIGIBLE`; contradictory surviving
   evidence is integrity failure.
4. Re-resolve the current scenario through the existing Session-service
   scenario catalogue and require it to be public. Revalidate any earlier
   discovered value and this transaction-time authoritative definition
   independently. Require exact catalogue content-version consistency, the
   1..32 ASCII-character persistence bound, an existing non-NPC default
   definition, and the existing public playable/default rules. Any unavailable,
   inconsistent, or over-bound current definition returns
   `INVALID_SCENARIO_DEFINITION` before any P8-S2 mutation is staged.
5. Build the strict composite from the resolved controller/key, locked
   Player Character ID/revision, current scenario ID/version/default, and
   configured trusted Run source. Encode it, enforce 4,096 bytes, compute its
   SHA-256, and self-check all four derived IDs. The composite codec independently
   requires the same content-version maximum; no truncation or substitute is
   possible.
6. Check the derived Session creation-request identity through
   `sessions.get_by_creation_request()` only after Player Character/Run locks
   and scenario validation. Any existing Session without an exact P8 receipt
   is `RUN_ENTRY_CONFLICT`; it is never adopted as a winner.
7. Obtain one exact UTC timestamp from the entry/Run clock. Issue and strictly
   validate one new Run ID and one new line ID. Ask the Session helper to
   issue/validate one Session ID, seed, and initial event ID and to construct
   the detached Session, initialized pre-memory state, initial Frame, and
   `ScenarioStarted` event candidate. The final memory-applied snapshot is not
   constructed yet: under existing `AUTH-001` authority it requires the
   repository-issued receipt returned only after that event is flushed. No
   write has occurred if an issuer or pure pre-event validation fails. Before
   constructing the detached `GameSession`, the helper independently checks
   that the exact transaction-time content version is 1..32 ASCII characters.
8. Purely construct and validate Run revision 1, revision 2 with the exact
   immutable applicable character reference, and revision 3 with the prepared
   Session participation and lifecycle `active`. Require source, time, IDs,
   versions 1/2/3, binding preservation, and receipt inputs to agree before
   staging. The Session's post-event memory/snapshot validation remains an
   ordered in-UoW step below.
9. Stage and flush in this exact repository order:
   1. Run revision/current 1;
   2. composite Run creation receipt through `add_with_evidence()`;
   3. immutable Run revision 2;
   4. current-row CAS from version 1 to 2, requiring exactly one row;
   5. existing binding mutation receipt;
   6. Session row, then sequence number 1, then the exact initial
      `ScenarioStarted` event flush; use only its repository-issued receipt to
      apply memory rules, fully validate the resulting state, and stage the
      version-zero snapshot through the no-commit Session helper;
   7. immutable Run revision 3;
   8. immutable Session participation;
   9. current-row CAS from version 2 to 3, requiring exactly one row; and
   10. existing attachment mutation receipt.
10. Treat each known uniqueness/CAS loss narrowly. No helper commits, opens a
    UoW, or performs winner recovery. A conflict decision exits the same UoW
    and rolls back every staged row.
11. After every pure and repository validation has passed, call `uow.commit()`
    exactly once.
12. Return the already validated stable result only after commit returns.

The Session helper extracts/refactors the current `_create_once` initialization
logic; it does not call `SessionService.create()`, because that public method
owns a UoW, commit, and a fresh-UoW winner recovery. The Run helpers similarly
extract/reuse current pure construction, receipt, append, participation, and
CAS rules without calling the transaction-owning public Run methods.

### 12.5 Lock/read order and races

The mandatory replay lock/read order is:

| Order | Evidence | Required semantics |
| --- | --- | --- |
| 1 | target Player Character current row and immutable referenced revision | existing owned binding-evidence lock/reconstruction |
| 2 | derived creation receipt and decoded evidence | immutable strict read after ownership; it may establish a MySQL consistent-read snapshot but acquires no Session lock |
| 3 | receipt-result Run current plus revision 1/2/3, binding, participation, activation, and related receipts | `RunRepository.get_for_update()` current/locking read and its existing related-family validation |
| 4 | exact participation Session row | owned `get_owned_for_update()` current/locking read by Session ID and current principal player ID |
| 5 | exact sequence-one `ScenarioStarted` event | immutable detached read after the Session row lock |
| 6 | exact Session `game_snapshots` row | `get_latest_snapshot_for_update()` current/locking read with `populate_existing`, after the Session row and before validation |

A fresh Run has no pre-existing Run row to lock. Repository helper queries may
validate immutable receipt/revision rows, but they may not acquire a Session
row or snapshot lock before an existing Run lock. The Session row precedes its
snapshot row, matching existing Session writers. The snapshot locking read is
not a mutation and does not authorize a replay commit.

Under MySQL `REPEATABLE READ`, ordinary non-locking `SELECT` reads share the
transaction's earlier consistent-read view, whereas `SELECT ... FOR UPDATE` is
a current read. Therefore, after any concurrent Session writer commits, the
ordered Session-row and snapshot-row locking reads wait as necessary and then
observe the latest committed row versions rather than the view established by
the earlier receipt read. The equality check between locked Session
`state_version` and current-read snapshot `state_version` then proves one
coherent current persisted state.

- Same character, same key/body: the Player Character lock serializes calls;
  one commits and the waiter observes and validates exact replay with no
  second commit.
- Same character, different key: one commits; the waiter observes active
  binding and returns character ineligible.
- Same derived key against different owned characters: independent character
  locks may race at the global creation-receipt unique key. One may commit; the
  loser returns idempotency conflict and rolls back its whole staged family.
- Run/line/Session identity, active-binding, participation, revision, or CAS
  uniqueness loss without an already validated exact receipt returns
  `RUN_ENTRY_CONFLICT`; no identity or write retry occurs.
- Stale discovery is ordinary: the locked current revision/lifecycle/binding
  and current scenario/default checks decide the fresh attempt.

### 12.6 Exceptions, cancellation, and commit uncertainty

Any exception before the commit call leaves the UoW uncommitted; established
`__aexit__` rollback restores in-memory pending Session versions and rolls back
all flushed rows. Cancellation propagates through the same cleanup.

For exact replay there are no pending writes, but the same `__aexit__` path
rolls back the read transaction, releases the Run/Session/snapshot locks, and
closes/discards the `AsyncSession`; it never calls `commit()`. Missing rows,
integrity mismatches, current-read failures, lock wait failures, ordinary
exceptions, and `CancelledError` all leave through that cleanup. No replay
failure authorizes a recovery transaction or second UoW.

If `commit()` raises or is cancelled, the service does not know whether the
database made the commit durable. It must not construct a second UoW, retry the
commit, query for a winner, compensate, or return success. The exception or
cancellation propagates. A future adapter uses its safe 500 behavior for an
ordinary exception; cancellation itself is not translated. The caller may
later make one explicit request with the exact same controller/key/body. That
new call follows the ordinary ownership-first receipt algorithm. A later 404
does not resolve prior uncertainty.

## 13. Normative decision tables

### 13.1 Receipt, eligibility, and integrity

| Case | Mutation | Commit | Internal result | Future P8-S3 |
| --- | --- | --- | --- | --- |
| No receipt + fully eligible character/current scenario | allowed exactly as section 12.4 | exactly one, after complete staging | `RunEntryResult` | 200 |
| Exact composite replay | forbidden | forbidden | persisted `RunEntryResult` | 200 |
| Same key, same controller, different public command/evidence | forbidden | forbidden | `IDEMPOTENCY_CONFLICT` | 409 |
| Receipt composite names another controller | forbidden | forbidden | `AUTHORIZATION_FAILED`; reveal no receipt result | sanitized 404 |
| Stale character revision, receipt absent | forbidden | forbidden | `PLAYER_CHARACTER_STALE` | 409 |
| Inactive or version-exhausted character, receipt absent | forbidden | forbidden | `PLAYER_CHARACTER_NOT_ELIGIBLE` | 409 |
| Active binding already present, receipt absent | forbidden | forbidden | `PLAYER_CHARACTER_NOT_ELIGIBLE` | 409 |
| Scenario or current default definition no longer eligible, receipt absent | forbidden | forbidden | `INVALID_SCENARIO_DEFINITION` | 422 |
| Current scenario content version is 33..128 characters, receipt absent | forbidden before Session/composite/Run staging | forbidden | `INVALID_SCENARIO_DEFINITION`; no truncation or database-error validation | 422 |
| Malformed/incomplete/over-bound/noncanonical composite | forbidden | forbidden | integrity exception | sanitized 500 |
| Composite, Session, event, or snapshot content version exceeds 32 characters or disagrees | forbidden | forbidden | persisted integrity exception | sanitized 500 |
| Recognized composite family with unknown version | forbidden | forbidden | integrity exception; no historical fallback | sanitized 500 |
| Tampered component, evidence bytes, raw fingerprint, or receipt fingerprint | forbidden | forbidden | integrity exception | sanitized 500 |
| Inconsistent Run/current/Session/character/binding/participation family | forbidden | forbidden | integrity/impossible-state exception | sanitized 500 |
| Valid historical source-only receipt under P8 lookup key | forbidden | forbidden | `IDEMPOTENCY_CONFLICT`; historical row unchanged | 409 |
| Malformed historical receipt/evidence | forbidden | forbidden | integrity exception | sanitized 500 |
| Composite bytes passed directly to historical decoder | forbidden | forbidden | strict decoder error | sanitized 500 if reached through future adapter |
| Missing, malformed, stale-view-only, or cross-bound current Session snapshot | forbidden | forbidden | narrow snapshot/integrity exception after current locking read | sanitized 500 |

Transport validation itself belongs to P8-S3. The 404/409/422/500 column is a
future mapping requirement, not P8-S2 API implementation.

### 13.2 Concurrency and failure

| Case | Mutation | Commit | Internal result | Future P8-S3 |
| --- | --- | --- | --- | --- |
| Concurrent identical fresh requests | one winner stages/mutates; waiter does not | winner one; waiter none | winner success; waiter exact replay | 200 for both completed calls |
| Concurrent different keys for one character | one winner; loser none after rollback | winner one; loser none | winner success; loser character ineligible | 200 / 409 |
| Unique/CAS race not explained by exact receipt | loser staged state is discarded | loser forbidden | `RUN_ENTRY_CONFLICT` | 409 |
| Another operation wins the same derived receipt key with non-equivalent evidence | loser staged state is discarded | loser forbidden | `IDEMPOTENCY_CONFLICT` | 409 |
| Concurrent Session update commits after replay's earlier consistent read but before Session validation | forbidden on replay | forbidden | Session/snapshot current reads observe latest committed state; valid state replays, mismatch fails closed | 200 or sanitized 500 by current evidence |
| Pre-commit exception | staged values, if any, are rollback-only | forbidden | narrow exception propagates | sanitized 500 |
| Cancellation before commit | staged values, if any, are rollback-only | forbidden | `CancelledError` propagates | no P8-S2 mapping |
| Cancellation during commit | no second mutation; durability unknown | the single attempt may already have reached MySQL; no second commit | `CancelledError` propagates; no success claim | no translation; caller observes cancellation |
| Commit exception / uncertain outcome | no retry or compensation; durability unknown | exactly the one attempted commit, never another | exception propagates; no success claim | sanitized 500 |

## 14. Exact future implementation path budget

Safe implementation requires no path outside the published maximum. The exact
allowlist is closed as follows.

### 14.1 Production — exactly eight paths

| Status | Path | Required reason |
| --- | --- | --- |
| existing | `src/deviation_protocol/domain/run.py` | admit and validate only the exact P8 revision-3 active shape |
| existing | `src/deviation_protocol/application/run_operations.py` | composite types/bytes/fingerprint, internal IDs, and pure first-participation activation |
| existing | `src/deviation_protocol/application/run_service.py` | no-UoW/no-commit entry staging helpers over existing Run operations |
| **new** | `src/deviation_protocol/application/run_entry_service.py` | sole P8-S2 transaction/replay coordinator and internal command/result/decision boundary |
| existing | `src/deviation_protocol/application/session_service.py` | 32-character current scenario/default validation, no-commit initial staging, and strict catalogue-independent persisted-snapshot replay validation |
| existing | `src/deviation_protocol/application/ports.py` | decoded-evidence and Session-initialization carriers plus narrow initialization-event and fail-closed current-snapshot repository methods |
| existing | `src/deviation_protocol/infrastructure/run_persistence.py` | disjoint historical/composite codec and complete independent integrity validation |
| existing | `src/deviation_protocol/infrastructure/repositories.py` | existing-column evidence mapping, replay loads, initial-event read, explicit SQLAlchemy Session-snapshot `FOR UPDATE` current read, and flush-only writes |

`player_character_service.py`, `player_character_persistence.py`,
`orm_models.py`, `unit_of_work.py`, API paths, Demo paths, and migrations are
inspection-only. The existing `lock_owned_for_binding` seam is sufficient, so
no substitution of `player_character_service.py` for an allowed path is
needed. A future need outside these eight paths blocks implementation and
requires a separately reviewed plan amendment.

### 14.2 Tests — exactly nine paths

| Status | Path | Required evidence |
| --- | --- | --- |
| existing | `tests/unit/test_run.py` | exact active revision-3 domain invariants and rejected shapes |
| existing | `tests/unit/test_run_operations.py` | deterministic composite fingerprint, ID vectors, and pure activation |
| existing | `tests/unit/test_run_service.py` | same-UoW staging, receipt ordering, CAS/receipt behavior, and no commit |
| **new** | `tests/unit/test_run_entry_service.py` | complete coordinator order, decisions, replay, rollback, cancellation, and commit counts |
| existing | `tests/unit/test_session_service.py` | 32/33-character scenario/default resolution, initial staging, and catalogue-independent strict snapshot replay validation |
| existing | `tests/unit/test_run_persistence.py` | mutually exclusive codecs, bounds, canonical vectors, and tamper rejection |
| existing | `tests/unit/test_run_repositories.py` | supplied composite write/reload, row mapping, family validation, exact ports, and a genuine `FOR UPDATE`/`populate_existing` snapshot query |
| existing | `tests/integration/test_mysql_run.py` | schema parity including the existing 32-character Session column, composite carrier, atomic Run/Session family, current-read reload, and historical compatibility |
| existing | `tests/integration/test_mysql_player_character_run_binding.py` | Player Character -> Run -> Session -> snapshot locking, `REPEATABLE READ` current-state concurrency, rollback, cancellation cleanup, and complete cross-family consistency |

No additional test path is speculative or authorized. A required regression
outside these nine paths is a stop condition for plan reassessment.

## 15. Required future verification evidence

### 15.1 Unit evidence

Tests must prove:

- canonical composite encoding is deterministic and matches the normative
  531-byte/SHA-256 vector;
- historical and composite decoder branches are mutually exclusive;
- unknown composite versions, damaged magic, malformed UTF-8/JSON, duplicate
  members at every level, unknown fields, missing fields, alternate key order,
  whitespace, escaped ASCII, invalid Unicode, floats/booleans/null, noncanonical
  integers, overlong fields, and total evidence over 4,096 bytes fail closed;
- every component affects the independently recomputed composite fingerprint;
- all four internal ID derivations use the exact domain bytes, `U16BE` field
  boundaries, and normative outputs;
- typed field comparisons prevent digest equality alone from authorizing
  replay;
- valid historical source-only evidence remains readable and keeps its
  historical fingerprint, while composite bytes cannot be accepted by the
  historical codec;
- exact replay locks/proves ownership, validates the complete family, and has
  zero issuer, mutation, receipt-add, CAS, and commit calls;
- a valid persisted current-schema initial Session snapshot containing
  scenario-runtime and player-memory records is rejected by
  `GameState.model_validate(payload, strict=True)` on its JSON arrays and Enum
  strings but accepted when the exact established JSON bytes are passed to
  `GameState.model_validate_json(..., strict=True)`; replacing the JSON-mode
  entry with the Python strict-mode entry must make this regression fail;
- valid persisted JSON arrays reconstruct the required internal tuple and
  frozen-set fields, valid persisted Enum strings reconstruct the required
  Enum instances, and `state.to_snapshot()` exactly equals the complete
  original persisted payload;
- changing, replacing, or removing the current scenario or content catalogue
  cannot affect the catalogue-independent validation of valid persisted
  evidence, and no catalogue argument or lookup is available to this path;
- unknown model fields are rejected rather than silently discarded; malformed
  scalar types, invalid Enum values, malformed nested structures, invalid
  identifiers, over-bound values, and impossible version-zero state fail
  closed during strict JSON-mode or existing nested validation;
- a missing field that model construction could supply from a default is
  rejected by the complete structural comparison, and a structurally altered
  or reordered persisted collection that model validation would normalize is
  likewise rejected because its round trip is not identical;
- semantic player/Session/scenario/runtime/memory/Run/participation/activation
  identity and initial-state mismatches still fail closed after strict JSON
  validation and structural equality have succeeded;
- the validation path preserves the original payload and every detached input,
  performs no mutation, repository write, or successful commit, and returns
  only the detached trusted `GameState`; and
- direct protection-removal regressions fail if either
  `GameState.model_validate_json(..., strict=True)` is replaced with the Python
  strict-mode entry or the complete `state.to_snapshot() == original_payload`
  check is removed, while the existing stable semantic cross-check remains
  independently protected;
- 32-character scenario content versions are accepted; 33-character current
  definitions are deterministically rejected as `INVALID_SCENARIO_DEFINITION`
  before staging, without truncation or a repository/database call; composite,
  Session, event, snapshot, fingerprint, receipt, and comparison paths enforce
  one exact unchanged value and the same bound;
- the repository current-snapshot method issues a real row-targeted
  `FOR UPDATE` query with `populate_existing`; the port default fails closed
  and cannot fall back to the existing non-locking snapshot load;
- conflicting reuse, another-controller evidence, valid historical evidence,
  stale revision, inactive/version-exhausted/bound character, and unavailable
  current scenario/default select the exact decisions and precedence above;
- replay does not reapply fresh active/unbound/current-revision/current-catalog
  checks;
- revision 1/2/3, source, binding, participation, Session, and stable result
  cross-checks reject every one-component substitution;
- pre-commit exception, rollback, cancellation, CAS/uniqueness loss,
  impossible state, and commit failure preserve the one-UoW/at-most-one-commit
  rules; and
- narrow exceptions and `CancelledError` propagate without broad translation.

Critical protections need direct negative tests that fail if the magic/version
branch, duplicate/canonical equality check, controller comparison, ID
recomputation, component fingerprint, immutable character revision check,
catalogue-independent Session structural/semantic check, 32-character boundary,
current-snapshot locking read, or one-commit rule is removed. No mutation-
testing framework is required.

### 15.2 Real-MySQL evidence

Against MySQL 8 through `AsyncSession`/`asyncmy`, tests must prove:

- the complete fresh Run revision/current 1/2/3, creation receipt, binding
  receipt, active binding, Session row/event/snapshot/memory effects,
  participation, and attachment receipt commit atomically;
- fresh repository sessions reconstruct the same composite, Run/current,
  immutable Player Character revision, Session initialization, participation,
  and stable result;
- the existing `game_sessions.scenario_version VARCHAR(32)` accepts an exact
  32-ASCII-character current definition, while a 33-character definition is
  rejected by the application before any P8-S2 flush/staging; no truncation,
  normalization, database error, migration, or alternate value participates;
- exact replay produces no second Run, Session, event, snapshot, memory effect,
  binding, participation, receipt, revision, CAS, or commit;
- a two-transaction `REPEATABLE READ` regression first establishes the replay
  transaction's consistent-read view through its earlier receipt read, then
  commits a relevant Session-row/snapshot advance in another transaction
  before replay Session validation. The ordered Session-row and snapshot-row
  `FOR UPDATE` reads must observe the latest committed equal state versions;
  valid current state replays successfully, while a current malformed/tampered
  or cross-bound state fails closed. The case must fail if the snapshot read is
  changed back to non-locking `AsyncSession.get()`;
- exact replay, current-state mismatch, snapshot read/lock failure, and
  cancellation perform no mutation or successful commit, release every lock by
  UoW rollback/close, permit a following transaction to acquire the same rows,
  and preserve the declared Player Character -> Run -> Session -> snapshot
  order;
- stale expected revision is rejected after the character lock;
- active-binding and same-character concurrent-entry races have one durable
  winner, with exact same-key replay and different-key ineligibility;
- same derived key/non-equivalent evidence and Session/Run/line identity or
  participation uniqueness races roll back the entire losing family;
- injected failure after every staged-write boundary and before commit leaves
  no partial family;
- Run/current revision 3 is `active`, revision 2 owns the exact binding,
  revision 3 preserves it byte-equivalently, and participation/Session/source/
  timestamps/derived IDs agree;
- mutation of each composite component, canonical evidence bytes, raw
  fingerprint, canonical receipt fingerprint, result/key, binding,
  participation, immutable character revision, Session row, or initial event
  is rejected rather than repaired;
- valid historical receipts still load through fresh repositories, retain
  source-only bytes, and are never rewritten;
- the unchanged `MEDIUMBLOB` stores the bounded composite and current metadata
  matches migration `20260729_0005` with no migration; and
- instrumented UoW/connection evidence records one UoW and one successful
  commit for fresh success, one UoW and zero commits for replay/rejection, and
  no second UoW after conflict, exception, cancellation, or uncertain commit.

### 15.3 Commands for the later implementation task

During implementation, run the exact focused paths first:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_run.py tests/unit/test_run_operations.py tests/unit/test_run_service.py tests/unit/test_run_entry_service.py tests/unit/test_session_service.py tests/unit/test_run_persistence.py tests/unit/test_run_repositories.py
.\.venv\Scripts\python.exe -m pytest tests/integration/test_mysql_run.py tests/integration/test_mysql_player_character_run_binding.py
```

Before the implementation candidate enters independent review, also run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic history
.\scripts\verify.ps1 -Mode Offline
.\scripts\verify.ps1 -Mode MySQL
git diff --check
```

The broader implementation-completion gate additionally runs
`.\scripts\verify.ps1 -Mode Full` and the repository's applicable Alembic
metadata/migration-parity evidence. No live Provider call is permitted. These
are future implementation commands; none is run while preparing this plan.

## 16. Implementation, review, documentation, and publication gates

### 16.1 Implementation completion

P8-S2 implementation is complete only when:

1. only the exact eight production and nine test paths were added/changed;
2. every normative byte, decoder, ID, fingerprint, 32-character persistence
   bound, catalogue-independent snapshot validation, current-read lock/order,
   transaction, replay, error, and compatibility rule above is implemented
   without a deferred persistent choice;
3. focused unit and real-MySQL evidence passes, including protection-removal
   regressions;
4. full Run/Session/Player Character state commits once or rolls back without a
   partial family;
5. historical receipts remain exact and schema/migration bytes are unchanged;
6. no public, Demo, Web, later-Session, terminal-Run, Provider, or later-slice
   behavior appears;
7. all required local commands pass and actual results are recorded; and
8. the canonical documentation-synchronization checklist is complete.

### 16.2 Focused independent implementation review

A fresh read-only review must inspect the complete implementation diff,
including untracked files, and verify:

- exact conformance to the approved plan bytes and path allowlists;
- no ambiguous decoder fallback or stored-only trust;
- precise ownership-before-disclosure and replay-before-fresh-eligibility
  ordering;
- lock/repository/staging/commit order, explicit latest-Session-snapshot current
  read, and real-MySQL `REPEATABLE READ` concurrency evidence;
- all component, revision-family, Session, source, and fingerprint
  cross-checks;
- strict catalogue-independent current-schema snapshot reconstruction and the
  consistent 32-character composite/Session boundary;
- rollback/cancellation/uncertain-commit behavior and absence of a second UoW;
- historical compatibility with no rewrite;
- no schema, migration, public, Demo, Web, or later-slice change; and
- truthful synchronized documentation and guardrail assessment.

Implementation self-review is not independent approval. Any correction changes
the reviewed bytes and requires refreshed identities and review.

### 16.3 Documentation synchronization after implementation

The dedicated approved plan is intended to remain byte-unchanged as the exact
implementation authority. Actual implementation status, paths, evidence,
review, and next action are synchronized within the Phase 8 plan's already
published maximum of these seven existing owners, editing only owners whose
facts changed:

1. `PLANS.md`;
2. `docs/architecture.md`;
3. `docs/public_client_contract.md`;
4. `docs/run_protocol.md`;
5. `docs/structured_player_character_contract.md`;
6. `docs/structured_player_character_implementation_plan.md`; and
7. `docs/structured_player_character_run_playable_loop_plan.md`.

This introduces no eighth implementation-documentation path. The public
contract may record that internal P8-S2 exists while `POST /v1/runs` remains
unimplemented; it may not claim a public behavior change. Do not describe
P8-S2 or Phase 8 as complete before the applicable evidence and review pass.

### 16.4 Commit/publication and P8-S3 entry

After implementation approval, a separate explicit authorization is required
to stage and commit the exact approved implementation and synchronized
documentation. Codex never pushes; the user performs the push. P8-S3 may begin
only after the P8-S2 implementation commit is pushed and a clean aligned
`main`/`origin/main` baseline is confirmed. P8-S2 approval does not authorize
P8-S3 planning or implementation.

## 17. Stop conditions

Stop and return for a separately reviewed plan amendment if implementation
requires:

- a path outside either closed allowlist;
- any ORM, migration, schema, backfill, or historical-row rewrite;
- another receipt/evidence/reservation store or pending state;
- a public/API/OpenAPI, Demo, Web, Provider, later-Session, or terminal-Run
  change;
- a different composite discriminator, version, object field, bound, canonical
  encoding, hashed bytes, internal-ID construction, or compatibility rule;
- current-catalogue revalidation for exact replay;
- receipt disclosure before ownership proof;
- a lock order other than Player Character -> existing Run -> Session row ->
  Session snapshot;
- a nested/second UoW, more than one commit attempt, retry, compensation,
  outbox, saga, or uncertain-commit recovery;
- acceptance based only on matching stored fingerprints; or
- a contradiction in retained character, Run, Session, or public authority.

## 18. Guardrail impact

These three candidate-specific plan corrections create or change no reusable
engineering or safety rule. Existing `DB-001`, `AUTH-001`, and workflow rules
remain sufficient.

Guardrail impact: None.

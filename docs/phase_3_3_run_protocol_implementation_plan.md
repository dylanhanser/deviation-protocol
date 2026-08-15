# Phase 3.3 Run Protocol Implementation Plan Candidate

Status: **Documentation-only candidate authored against
`49bb7c9c8f616e4036cbe56549f9621544ebf84b`; awaiting fresh independent
read-only re-review after a first independent verdict of `CHANGES_REQUIRED`.
It is not approved, frozen, published, commit-ready, or implementation
authorization. Phase 3.3 is not implemented and has not begun.**

Classification:
`PHASE_3_3_NEW_FROZEN_IMPLEMENTATION_PLAN_REQUIRED`, following the authoritative
readiness result `PHASE_3_3_IMPLEMENTATION_READINESS_RECONSTRUCTION_COMPLETE`.

Phase ownership: **Phase 3.3**

Candidate scope: exactly this file, [`run_protocol.md`](run_protocol.md), and
[`../PLANS.md`](../PLANS.md).

Correction scope: exactly B1-B4 from the first independent review. B1 removes
premature freeze claims; B2 corrects the sequence to P3.3-G0 plus P3.3-S1
through P3.3-S7, adds dedicated P3.3-S5 objective mechanics/trusted
prompt-context compilation, and adds complete acceptance-criterion coverage;
B3 fixes the complete exact P3.3-S1 symbol and callable contracts; B4 restricts
important-NPC recovery to already-authorized identity/world predicates. No
implementation or additional product feature is included.

## Baseline and authority

This candidate is authored against the following exact clean published
baseline, supplied by the outer session and not re-audited here:

| Baseline fact | Exact value |
| --- | --- |
| Branch | `main` |
| `HEAD`, local `main`, local `origin/main` | `49bb7c9c8f616e4036cbe56549f9621544ebf84b` |
| Ahead/behind | `0/0` |
| Subject | `docs(narrative): close recovery correction publication` |
| Parent | `12485f309860c496ff4aebae0e5e834779e485d7` |
| Worktree/index | Clean; no untracked paths, conflicts, operations, or locks |

The table identifies the clean published implementation base, not the current
documentation worktree. The correction preflight retained exactly modified
`PLANS.md`, untracked
`docs/phase_3_3_run_protocol_implementation_plan.md`, and modified
`docs/run_protocol.md`, with an empty index, zero conflicts, and no active Git
operation or lock. All pre-correction per-path identities are invalid and
non-operative. The pre-correction canonical ordered complete patch of `57,908`
bytes with SHA-256
`e9715b761f0030b30bcd6c136b3b7c016fcdddbf1243c1ffb272811c6c08bcad` is
also invalid and cannot satisfy the corrected candidate's review gate.

Product authority remains in [`run_protocol.md`](run_protocol.md),
[`final_narrative_experience.md`](final_narrative_experience.md), and
[`npc_relationship_residence.md`](npc_relationship_residence.md). Repository
status and phase ordering remain in [`../PLANS.md`](../PLANS.md). Architecture,
public-client, Provider, scenario, and workflow authority remain in their
existing canonical documents. This plan translates those authorities into a
repository-specific implementation sequence; it does not supersede them or
rewrite any already frozen implementation plan.

The current boundary is:

- Phase 8 is implemented and complete at its published P8-S6 closure baseline
  `7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`; no P8-S7 exists.
- Dynamic Narrative Vertical Spike work and the bounded autonomous improvement
  lifecycle are closed.
- Phase 6 is paused under `PHASE_6_NO_CURRENT_EXECUTABLE_SURFACE`; Phase 7 is
  inactive.
- Phase 3.4 remains later. Production Provider Distribution remains deferred.
- The current public Run entry is one transaction owned by `RunEntryService`.
  It stages and commits exactly once revision 1 as unbound `pre_first_turn`,
  revision 2 as immutably character-bound `pre_first_turn`, revision 3 as the
  first Session participation plus `active`, the current Run row, receipts,
  character binding, and Session initialization/event/snapshot/participation.
- No current Run record contains a resolved Run Protocol, profile identity,
  authored-world identity/version, visit identity, region identity, or durable
  world state. `scenario_id` is scenario-definition identity only.

No defect is asserted by this plan. The readiness reconstruction found a new
planning requirement, not a correction to the current Phase 8 implementation.

## Decision provenance

This plan uses the following authority labels:

- **Current implemented fact:** behavior proved by current code and status
  authorities, principally the Phase 8 legacy family described above.
- **Approved product requirement:** behavior already accepted in
  `run_protocol.md` or another retained product authority but not implemented.
- **Repository-specific technical decision proposed for freeze:** an exact P3.3-G0
  compatibility, representation, version, sequencing, or verification choice
  introduced by this three-document candidate. It becomes frozen only after
  exact independent approval, separately authorized commit, user-controlled
  push, and clean published-baseline confirmation.
- **Later-slice decision:** a decision allocated to P3.3-S2 through P3.3-S7 that must be made in
  that slice's separately reviewed plan before implementation.
- **Deferred detail:** a value or representation deliberately left undecided,
  with its owner, freeze gate, and stop condition recorded below.
- **Exclusion:** work this plan does not authorize or absorb.

The current-boundary section records implemented facts; `run_protocol.md`
remains the product-requirement authority; the compatibility, P3.3-S1 canonical,
version, sequence, and verification sections are repository-specific technical
decisions proposed for freeze; and the slice/deferred tables identify later
decisions and deliberate deferrals. No planned statement is an implementation
claim.

## Approval, publication, and freeze contract

There is exactly one operative success verdict for this candidate:

`PHASE_3_3_RUN_PROTOCOL_IMPLEMENTATION_PLAN_INDEPENDENT_REVIEW_APPROVED`

It is operative only when returned by a fresh independent read-only review of
the exact three candidate files and their recorded hashes on the exact baseline.
Every historical, illustrative, superseded, implementation, failure,
changes-required, blocked, authoring, or other approval-looking token is
non-operative for this candidate. In particular,
`PHASE_3_3_RUN_PROTOCOL_IMPLEMENTATION_PLAN_CANDIDATE_COMPLETE` is only a
non-operative authoring label and cannot approve or freeze anything.

Any byte change in any of the three approval-bound candidate documents after
hashing invalidates the recorded candidate hash set and every review of that
set. A changed candidate must be re-hashed and receive a fresh independent
read-only review. Approval of this documentation never authorizes a commit,
push, or implementation. The proposed decisions become frozen only after the
exact reviewed bytes receive the operative verdict, a separately authorized
exact three-path commit, user-controlled push, and clean aligned
published-baseline confirmation. P3.3-S1 then still requires separate
authorization.

## Scope

Phase 3.3 owns:

- a strict, versioned Run Protocol/profile representation;
- trusted profile authorization and deterministic engine resolution;
- permitted pre-entry overrides with exact precedence and authority;
- durable legacy/native distinction and a native Run's frozen resolved-protocol
  binding;
- an authored eligible entry-world authority with explicit world ID/version;
- atomic native admission, evidence, replay, recovery, and projections;
- deterministic later-world selection, visits, regions, revisits, world state,
  progression priorities, anti-repeat, anti-farming, and continuous-world-line
  canon within separately bounded later slices.

Phase 3.3 excludes:

- Phase 3.4 residence and relationship progression;
- golden memory or cross-scenario logical NPC identity;
- Phase 6 subject-reference hooks or Phase 7 closeout work;
- production Provider selection/distribution or any Provider-owned mechanics;
- model-authored protocol, profile, world, visit, region, state, or canon;
- copying names, plots, prose, equipment, skills, or setting details from
  reference fiction;
- treating ordinary creative actions as deviation candidates;
- generalized combat, deployment, authentication, pricing, quota, or live-call
  work;
- rewriting old Phase 8 evidence or changing a frozen old implementation plan.

## Proposed compatibility classes

### Legacy Session-backed Runs

The candidate proposes that all Runs created by the current Phase 8 entry
family remain valid legacy Runs. The following preservation decisions are not
yet frozen by this unapproved candidate:

- revisions 1, 2, and 3 retain their existing meanings, with revision 3 active;
- the character binding remains immutable and the first Session participation
  remains immutable;
- the Session initialization, initial event, initial snapshot, and participation
  family remains one atomic admission result;
- every existing V1 namespace, magic/version discriminator, canonical
  fingerprint, stored evidence byte, receipt rule, replay result, recovery rule,
  error precedence, and production/Demo/Web/Dynamic Narrative contract remains
  unchanged.

An existing row may be classified as legacy only from trusted stored historical
proof that passes its existing strict decoder and complete cross-row integrity
checks. For the current public family, that proof includes the stored V1
Run-entry creation evidence and receipt plus the exact Run revision/current,
binding, participation, and Session initialization family. A caller-controlled
omission, `null`, missing new column, request shape, model output, scenario
choice, or decode failure must never select legacy handling.

Legacy Runs are readable and replayable only under that trusted proof. They are
not Phase-3.3-native and must not be rewritten, backfilled, refingerprinted,
relabelled, upgraded, or supplied with synthesized protocol/profile/world/visit/
region/world-state data. They grant no Provider, world, visit, region, or canon
authority. Their `scenario_id` remains only scenario identity.

### Phase-3.3-native Runs

A native Run is distinguished only by explicit, trusted, server-owned,
versioned durable state introduced in P3.3-S3. It requires an exact validated and
authorized protocol/profile binding. Before native admission can activate in
P3.3-S4 it also requires an exact authored entry-world ID and version. Missing,
malformed, unknown, contradictory, unsupported, or mutually incompatible
native state fails closed as stored integrity failure; it never falls back to
legacy and is never repaired on read.

P3.3-S1 and P3.3-S2 create no native Runs. P3.3-S3 establishes persistence and reconstruction
but no public/native admission. P3.3-S4 is the first slice allowed to bind the
resolved protocol and entry world into an atomic internal admission path.

## Identity and authority separation

The following identities are permanently separate domains:

1. `RunId`: one durable Run aggregate.
2. `ContinuousStoryLineId`: the one continuous line permanently owned by that
   Run.
3. Structured Player Character identity plus the exact applicable character
   revision and contract/reference captured by the immutable Run binding.
4. Session identity and immutable Run-owned participation.
5. Scenario definition identity and content version.
6. Future authored-world identity and authored-world version.
7. Visit identity: one occurrence of entering or revisiting an authored world.
8. Region identity and its state within the applicable world/visit rules.
9. Run Protocol schema identity, authorized profile identity/version, and the
   resolved-protocol version/binding.

`scenario_id` must never stand in for world, visit, region, or protocol identity.
Reuse of a definition, name, template, catalogue/config entry, scenario, or
authored world never proves identity continuity. Continuity requires the exact
trusted identity and version references selected by the owning domain.

Clients may request only explicitly published choices. Models may render only
trusted results. Neither may choose schema versions, authorize profiles,
resolve engine values, select legacy/native handling, issue identities, bind a
Run, select later worlds, mutate world state, or approve canon.

## P3.3-S1 canonical representation proposed freeze

P3.3-S1 is a pure no-migration foundation. This candidate proposes the exact
representation semantics and strict no-I/O record/codec round trip to freeze;
they are not frozen while the candidate awaits fresh review, approval, commit,
user push, and clean published-baseline confirmation. Even after an authorized
P3.3-S1 implementation, this representation is deliberately insufficient to be
a durable frozen Run Protocol.

### Exact v1 carriers

All P3.3-S1 carriers are strict, immutable Pydantic repository models with
`extra="forbid"`, `strict=True`, `frozen=True`, and
`revalidate_instances="always"`. They expose no aliases, defaults, computed
fields, private attributes, extension dictionaries, or permissive constructors.
The public validation and encoding boundaries inspect and revalidate the
original actual instance state recursively before serialization; they do not
first dump, coerce, repair, default, or discard source state.

The exact representation is:

```text
RunProtocolProfileId
  value: ASCII opaque identifier, 1..128 bytes and code points,
         regex [A-Za-z0-9][A-Za-z0-9_.:-]*

RunProtocolProfileVersion
  value: JSON integer, 1..9223372036854775807 inclusive

RunProtocolProfileRefV1
  profile_id: RunProtocolProfileId
  profile_version: RunProtocolProfileVersion

RunProtocolEnvelopeV1
  schema_version: literal "run-protocol-envelope/v1"
  profile_ref: RunProtocolProfileRefV1
  world_tone: exactly "grim" | "balanced" | "heroic"
  reality_boundary: exactly "lawful" | "deviant" | "chaotic"
  relationship_overlay: exactly "off" | "veiled" | "charged"

StoredRunProtocolEnvelopeRecordV1
  schema_epoch: literal "run-protocol-envelope"
  record_version: Python integer exactly 1
  canonical_payload: strict bytes containing one canonical
                     RunProtocolEnvelopeV1
```

The stored-record carrier is an in-memory, no-I/O storage-bound representation
only. Its epoch/version are trusted decoder-selection inputs and must agree with
the payload literal. It adds no ORM field, table, migration, repository method,
Run binding, receipt, or public shape.

The v1 envelope contains no numeric engine value, difficulty range, resource
quantity, success modifier, severity, catalogue definition/default, override,
seed, world ID/version, visit, region, relationship state, memory, scenario,
character, Run, line, Session, raw prose, secret, credential, Provider output,
or arbitrary metadata. Arrays are forbidden in v1.

### Exact P3.3-S1 symbol and callable contract

This table is the complete module-level P3.3-S1 production contract. A symbol
not listed here is not part of P3.3-S1 and must not be imported across modules.
Every class below uses its exact field declaration shown above and has no
defaulted field. Direct Pydantic field construction is strict and invalid field
values raise `pydantic.ValidationError`; the public validation and codec functions translate
failures into the exact taxonomy below. Every listed callable is synchronous,
deterministic, pure, and performs no filesystem, environment, clock, random,
database, network, logging, Provider, repository, or Unit of Work operation.
Calling a listed keyword-only constructor with positional arguments or an
invalid keyword signature raises Python `TypeError`; invalid field values raise
the row's stated exception. The final column explicitly distinguishes
P3.3-S1-test use from the intended P3.3-S2/P3.3-S3 seam.

| Exact module and name | Visibility/category | Exact signature or value | Validation responsibility and trust | Exact return and exception | Consumer and seam |
| --- | --- | --- | --- | --- | --- |
| `deviation_protocol.domain.run_protocol.RUN_PROTOCOL_ENVELOPE_EPOCH` | Public constant; domain epoch authority | `str = "run-protocol-envelope"` | Server-owned schema epoch; never caller/model authority | Exact string; no exception | P3.3-S1 dispatcher and infrastructure record construction; intended P3.3-S3 durable discriminator seam |
| `deviation_protocol.domain.run_protocol.RUN_PROTOCOL_ENVELOPE_V1_RECORD_VERSION` | Public constant; domain version authority | `int = 1` | Exact non-Boolean trusted record version for v1 | Exact integer; no exception | P3.3-S1 dispatcher and infrastructure record construction; intended P3.3-S3 durable discriminator seam |
| `deviation_protocol.domain.run_protocol.RUN_PROTOCOL_ENVELOPE_V1_SCHEMA` | Public constant; payload literal authority | `str = "run-protocol-envelope/v1"` | Exact payload literal corresponding only to record version `1` | Exact string; no exception | `RunProtocolEnvelopeV1`; P3.3-S1 codec; intended P3.3-S2/P3.3-S3 seam |
| `deviation_protocol.domain.run_protocol.MAX_RUN_PROTOCOL_ENVELOPE_RAW_BYTES` | Public constant; raw decode ceiling | `int = 1_024` | Applied to supplied bytes before UTF-8 or JSON parsing | Exact integer; no exception | P3.3-S1 decoder and persistence reconstruction; intended P3.3-S3 seam |
| `deviation_protocol.domain.run_protocol.MAX_RUN_PROTOCOL_ENVELOPE_CANONICAL_BYTES` | Public constant; canonical encode ceiling | `int = 1_024` | Applied after exact canonical encoding | Exact integer; no exception | P3.3-S1 encoder and golden tests; intended P3.3-S2 fingerprint/P3.3-S3 storage seam |
| `deviation_protocol.domain.run_protocol.RunProtocolValidationError` | Public exception/category | `class RunProtocolValidationError(ValueError)` | Classifies malformed carriers, actual-instance state, selectors, UTF-8/JSON, grammar, bounds, non-canonical bytes, and record/payload contradiction | Constructed exception; consumers catch this exact base for representation failure | P3.3-S1 domain tests; intended P3.3-S2 validation boundary and P3.3-S3 infrastructure translation seam |
| `deviation_protocol.domain.run_protocol.UnsupportedRunProtocolVersionError` | Public exception/category | `class UnsupportedRunProtocolVersionError(RunProtocolValidationError)` | Classifies a well-typed trusted `(expected_epoch, expected_version)` pair other than `("run-protocol-envelope", 1)`; never classifies malformed v1 bytes | Constructed exception; exact subtype of `RunProtocolValidationError` | P3.3-S1 dispatch tests; intended P3.3-S3 fail-closed decoder-selection seam |
| `deviation_protocol.domain.run_protocol.RunProtocolProfileId` | Public strict immutable Pydantic carrier | `RunProtocolProfileId(*, value: str) -> RunProtocolProfileId` | Untrusted construction input; exact `str`, 1..128 code points and UTF-8 bytes, ASCII regex `[A-Za-z0-9][A-Za-z0-9_.:-]*`; no authority/existence lookup | New carrier; direct construction raises `pydantic.ValidationError` | P3.3-S1 tests; intended P3.3-S2 authorized-profile seam |
| `deviation_protocol.domain.run_protocol.RunProtocolProfileVersion` | Public strict immutable Pydantic carrier | `RunProtocolProfileVersion(*, value: int) -> RunProtocolProfileVersion` | Untrusted construction input; `type(value) is int`, `1..9223372036854775807`; Boolean and coercion rejected | New carrier; direct construction raises `pydantic.ValidationError` | P3.3-S1 tests; intended P3.3-S2 authorized-profile seam |
| `deviation_protocol.domain.run_protocol.RunProtocolProfileRefV1` | Public strict immutable Pydantic carrier | `RunProtocolProfileRefV1(*, profile_id: RunProtocolProfileId, profile_version: RunProtocolProfileVersion) -> RunProtocolProfileRefV1` | Untrusted construction input; exact nested carrier types; extra/missing/coerced state rejected | New carrier; direct construction raises `pydantic.ValidationError` | P3.3-S1 envelope/tests; intended P3.3-S2 lookup/resolution seam |
| `deviation_protocol.domain.run_protocol.RunProtocolWorldTone` | Public `StrEnum` presentation carrier | Members `GRIM="grim"`, `BALANCED="balanced"`, `HEROIC="heroic"` | Untrusted construction token; only exact member values admitted; presentation only | Enum member; invalid direct construction raises `ValueError` | P3.3-S1 envelope/tests; intended P3.3-S2 recommendation and P3.3-S5 presentation seam |
| `deviation_protocol.domain.run_protocol.RunProtocolRealityBoundary` | Public `StrEnum` presentation carrier | Members `LAWFUL="lawful"`, `DEVIANT="deviant"`, `CHAOTIC="chaotic"` | Untrusted construction token; only exact member values admitted; presentation only | Enum member; invalid direct construction raises `ValueError` | P3.3-S1 envelope/tests; intended P3.3-S2 recommendation and P3.3-S5 presentation seam |
| `deviation_protocol.domain.run_protocol.RunProtocolRelationshipOverlay` | Public `StrEnum` presentation carrier | Members `OFF="off"`, `VEILED="veiled"`, `CHARGED="charged"` | Untrusted construction token; only exact member values admitted; presentation only | Enum member; invalid direct construction raises `ValueError` | P3.3-S1 envelope/tests; intended P3.3-S2 recommendation and P3.3-S5 presentation-only seam |
| `deviation_protocol.domain.run_protocol.RunProtocolEnvelopeV1` | Public strict immutable Pydantic carrier | `RunProtocolEnvelopeV1(*, schema_version: Literal["run-protocol-envelope/v1"], profile_ref: RunProtocolProfileRefV1, world_tone: RunProtocolWorldTone, reality_boundary: RunProtocolRealityBoundary, relationship_overlay: RunProtocolRelationshipOverlay) -> RunProtocolEnvelopeV1` | Untrusted construction input; exact five fields/types; strict recursive validation; no numeric mechanics or authority | New carrier; direct construction raises `pydantic.ValidationError` | P3.3-S1 tests/codec; intended P3.3-S2 resolution input and P3.3-S3 durable payload seam |
| `deviation_protocol.domain.run_protocol.validate_run_protocol_envelope_v1` | Public original-structure validation callable | `validate_run_protocol_envelope_v1(value: RunProtocolEnvelopeV1) -> RunProtocolEnvelopeV1` | Revalidates `type(value) is RunProtocolEnvelopeV1`, exact `__dict__` fields, empty/absent Pydantic extra/private state, `__pydantic_fields_set__` exactly equal to declared field names at every model, every nested actual instance, and complete model invariants before any dump | Returns the exact input instance; wrong exact top-level type raises `TypeError`; every invalid actual/model state raises `RunProtocolValidationError` | P3.3-S1 tests/encoder; intended P3.3-S2 trusted representation boundary |
| `deviation_protocol.domain.run_protocol.encode_run_protocol_envelope_v1` | Public canonical encoder | `encode_run_protocol_envelope_v1(value: RunProtocolEnvelopeV1) -> bytes` | Calls the original-structure validator, serializes the explicit five-field allowlist, applies NFC, sorted keys, compact JSON, direct non-ASCII UTF-8, signed-integer rules, and the canonical byte ceiling | New immutable canonical bytes; wrong exact top-level type raises `TypeError`; invalid state or byte bound raises `RunProtocolValidationError` | P3.3-S1 golden/persistence tests; intended P3.3-S2 fingerprint and P3.3-S3 payload seam |
| `deviation_protocol.domain.run_protocol.decode_run_protocol_envelope_v1` | Public version-specific canonical decoder | `decode_run_protocol_envelope_v1(payload: bytes) -> RunProtocolEnvelopeV1` | Treats payload as untrusted; requires exact `bytes`, 1..1,024 raw bytes, no BOM, strict UTF-8, exact JSON grammar/shape, duplicate rejection, exact v1 carrier, original-state validation, and byte-identical re-encode | New detached envelope; every failure raises `RunProtocolValidationError` | P3.3-S1 malformed/golden tests; called only by dispatcher; intended P3.3-S3 decode seam |
| `deviation_protocol.domain.run_protocol.decode_run_protocol_envelope` | Public trusted-version dispatcher | `decode_run_protocol_envelope(payload: bytes, *, expected_epoch: str, expected_version: int) -> RunProtocolEnvelopeV1` | `payload` is untrusted; selectors are trusted server inputs but require exact `str`/non-Boolean `int`; only the exact v1 pair dispatches; payload literal is then cross-checked by the v1 decoder | New detached v1 envelope; malformed selector/payload raises `RunProtocolValidationError`; a well-typed unsupported pair raises `UnsupportedRunProtocolVersionError` | P3.3-S1 dispatch tests and infrastructure reconstruction; intended P3.3-S3 durable dispatch seam |
| `deviation_protocol.infrastructure.run_protocol_persistence.RunProtocolStoredRecordIntegrityError` | Public infrastructure exception/category | `class RunProtocolStoredRecordIntegrityError(ValueError)` | Classifies malformed, partial, non-canonical, unsupported-version, or contradictory stored protocol evidence | Constructed exception; exact infrastructure boundary for stored corruption | P3.3-S1 persistence tests; intended P3.3-S3 repository reconstruction seam |
| `deviation_protocol.infrastructure.run_protocol_persistence.StoredRunProtocolEnvelopeRecordV1` | Public frozen slotted dataclass carrier | `StoredRunProtocolEnvelopeRecordV1(schema_epoch: str, record_version: int, canonical_payload: bytes) -> StoredRunProtocolEnvelopeRecordV1` | Carrier construction performs no validation and grants no trust; values from storage remain untrusted until reconstruction; `record_version` is the trusted integer selector only after repository binding in P3.3-S3 | New carrier; Python raises `TypeError` only for constructor arity/keyword errors | P3.3-S1 in-memory corruption tests; intended P3.3-S3 row-to-codec seam |
| `deviation_protocol.infrastructure.run_protocol_persistence.run_protocol_envelope_to_storage` | Public no-I/O stored-record construction | `run_protocol_envelope_to_storage(value: RunProtocolEnvelopeV1) -> StoredRunProtocolEnvelopeRecordV1` | Revalidates/encodes the input with the domain authority; writes exact epoch, integer record version `1`, and canonical payload; performs no persistence | New frozen slotted record; any domain type/validation/encoding failure raises `RunProtocolStoredRecordIntegrityError` with the domain exception as cause | P3.3-S1 persistence round trip; intended P3.3-S3 repository write seam |
| `deviation_protocol.infrastructure.run_protocol_persistence.run_protocol_envelope_from_storage` | Public no-I/O stored-record reconstruction | `run_protocol_envelope_from_storage(stored: StoredRunProtocolEnvelopeRecordV1) -> RunProtocolEnvelopeV1` | Treats the complete record as untrusted; requires exact record type, exact `str` epoch, exact non-Boolean `int` version, exact `bytes` payload, then calls trusted dispatcher and rechecks record/payload agreement | New detached v1 envelope; every wrong type, malformed value, unsupported version, contradiction, or non-canonical payload raises `RunProtocolStoredRecordIntegrityError`; an unsupported domain exception is retained only as its cause | P3.3-S1 persistence corruption/round-trip tests; intended P3.3-S3 repository read seam |

There is no distinct serialized wrapper codec in P3.3-S1. The only stored bytes
are `canonical_payload`, produced and consumed by the domain encoder/dispatcher;
the dataclass is an in-memory persistence carrier until P3.3-S3 selects a
reviewed physical schema. No P3.3-S1 symbol performs profile authorization,
resolution, persistence, migration, Run binding, mechanics, prompt compilation,
or public projection.

### Exact JSON grammar and limits

The decoded JSON value must be one object with exactly the five envelope members
above. `profile_ref` must be one object with exactly its two members. Thus a v1
payload has exactly two object nodes, seven object members in total, six scalar
leaves, no arrays, and maximum object depth two where the root is depth one.

The encoded payload must be between 1 and 1,024 bytes inclusive. String bounds
are the exact literal/enum bounds above and the 128-byte/code-point profile-ID
bound. The only JSON number is `profile_version`, whose token must represent the
exact signed-positive integer domain above. A leading plus sign, leading zero,
negative value, exponent, decimal point, or out-of-range integer is rejected.

At every depth reject duplicate object keys, unknown or missing fields, aliases,
`null`, booleans in integer positions, floats, `NaN`, `Infinity`, `-Infinity`,
numeric or string coercion, invalid UTF-8, unpaired surrogates, a BOM, trailing
bytes, comments, arrays, and ambiguous values. Actual model instances with
unexpected `__dict__` keys, `__pydantic_extra__`, `__pydantic_private__`, or
contradictory fields-set state are rejected rather than copied or repaired.

### Canonical JSON bytes

Canonical bytes are strict UTF-8 with no BOM. All strings are NFC-normalized in
the same manner as the repository's current canonical Run-operation encoder.
Object keys are sorted lexicographically by Unicode code point, separators are
exactly `,` and `:`, whitespace is absent, non-ASCII characters are emitted
directly rather than escaped, and non-finite numbers are impossible. Objects
are semantically order-independent and sequences are semantically ordered; v1
contains no sequence field.

The decoder must:

1. receive the trusted expected epoch/version separately;
2. enforce the raw byte and UTF-8/BOM limits before JSON materialization;
3. parse with duplicate-key rejection at every depth and non-finite-number
   rejection;
4. validate the exact version-specific carrier and actual instance state;
5. cross-check record epoch/version against the payload literal;
6. re-encode the detached value canonically; and
7. accept only when the re-encoded bytes are byte-for-byte identical to the
   supplied payload.

The equality rule rejects reordered stored objects, alternate escaping,
decomposed Unicode, insignificant whitespace, or alternate integer spellings,
even though an independently materialized object has order-independent
semantics. There is no generic or fallback decoder.

### Golden vector V1-REP-001

`profile.example` is deliberately a representation-only test identifier. The
golden does not declare it an authorized or resolvable production profile.

Exact UTF-8 bytes, shown as their literal ASCII rendering:

```json
{"profile_ref":{"profile_id":"profile.example","profile_version":1},"reality_boundary":"lawful","relationship_overlay":"off","schema_version":"run-protocol-envelope/v1","world_tone":"balanced"}
```

- byte length: `193`
- SHA-256:
  `a7e0149e8241f1b4d1c74487da2b8bcf36c93d05310c76a9b847d4e57c5a3a8a`
- exact lowercase hexadecimal bytes:

```text
7b2270726f66696c655f726566223a7b2270726f66696c655f6964223a2270726f66696c652e6578616d706c65222c2270726f66696c655f76657273696f6e223a317d2c227265616c6974795f626f756e64617279223a226c617766756c222c2272656c6174696f6e736869705f6f7665726c6179223a226f6666222c22736368656d615f76657273696f6e223a2272756e2d70726f746f636f6c2d656e76656c6f70652f7631222c22776f726c645f746f6e65223a2262616c616e636564227d
```

Encoding this carrier must produce those exact bytes. Decoding those bytes
through the trusted V1 record must reproduce an equal detached carrier and the
same bytes. The same semantic object with any different member order is an
explicit non-canonical decoder rejection vector.

### Representation is not authorization

P3.3-S1 answers only whether a value has the exact v1 representation. It does not
answer whether a profile exists, is enabled, is compatible with a scenario or
world, is available to a principal, has approved defaults, accepts an override,
or resolves to engine values. A representation-valid reference may therefore
fail later authorization/profile lookup. That failure must not be repaired by
substitution or a default.

## Version and decoder behavior

The initial schema epoch is `run-protocol-envelope`; its only supported version
is integer `1`, corresponding to payload literal
`run-protocol-envelope/v1`. Profile version is an independent positive signed
64-bit value and never selects an envelope decoder.

The server selects the decoder from trusted stored epoch/version state. A model
or public client cannot choose it. In P3.3-S1 the expected record version is an
explicit internal test/application input; in P3.3-S3 it becomes trusted durable
state. Decode and full actual-state revalidation always precede profile lookup,
resolution, replay comparison, projection, or gameplay use.

Unknown future versions, malformed or non-canonical bytes, contradictory record
and payload versions, incompatible bindings, and partial data fail closed.
There is no default version, heuristic detection, automatic upgrade or
downgrade, reinterpretation by a newer carrier, permissive fallback, or
write-on-read repair. Old bytes, evidence, receipts, and fingerprints remain
preserved. Any successor schema requires explicit product planning, decoder and
golden vectors, compatibility/migration rules, independent review, and separate
implementation authorization.

## Transaction, replay, concurrency, recovery, and cancellation

P3.3-S1 and P3.3-S2 are pure and perform no I/O. P3.3-S5's mechanics policies
and prompt-context compiler are also deterministic and Provider-independent;
Provider calls remain outside database transactions. Starting with P3.3-S3:

- one application service owns each mutation transaction; repositories stage
  and flush but never commit;
- protocol/profile/world binding must participate in the same atomic state,
  revision, evidence, receipt, participation, and Session operation required by
  its slice—never a second best-effort commit;
- replay checks trusted stored evidence before fresh eligibility/staleness only
  where the existing authority and disclosure rules require that precedence;
- exact replay returns the original allowlisted result without mutation,
  identity issuance, clock use, Provider call, or commit;
- the same operation key with different canonical evidence is an exact conflict;
- optimistic compare-and-swap, unique constraints, locks, and repository
  integrity checks must leave exactly one complete winner and no partial loser;
- corrupt, partial, cross-bound, unknown-version, or contradictory stored state
  is an integrity failure, never legacy fallback or successful replay;
- pre-commit exceptions and cancellation propagate through exceptional UoW
  cleanup and roll back every staged family;
- a commit failure or cancellation receives one commit attempt and no claimed
  success; uncertain commit state is resolved only by an explicitly authorized
  exact-evidence replay/read protocol, never by an automatic replacement write;
- ordinary Phase 3.3 code performs no Provider call, and no database lock may be
  held around a Provider operation.

Session recovery remains GET/exact-replay based under the current published
contract. The Web
client must not infer a native Run or recreate a protocol from local state.

## Persistence and migration strategy

- **P3.3-S1:** no database representation and no migration. The stored-record carrier
  is exercised only in memory.
- **P3.3-S2:** no durable binding and no public activation.
- **P3.3-S3:** a dedicated, separately reviewed P3.3-S3 slice plan must select the exact
  table/column representation, constraints, indexes, evidence binding, ORM
  shape, repository/UoW methods, migration revision, downgrade policy, and
  reconstruction rules. MySQL 8, SQLAlchemy `AsyncSession`, and `asyncmy` remain
  mandatory. The matching Alembic migration is part of P3.3-S3.
- Existing rows receive no synthetic discriminator or protocol. The migration
  must preserve them byte-for-byte and classify legacy only from trusted stored
  proof. Native state uses an explicit server-owned discriminator and required
  protocol binding; null/absence is not a mode.
- P3.3-S3 must prove rollback, cancellation, CAS/unique/concurrency behavior, old-row
  reconstruction, exact legacy/native distinction, and corruption rejection.
  It must not activate native public admission.
- **P3.3-S4:** separately versions the native admission evidence/fingerprint and
  atomically binds the resolved protocol plus authored entry-world identity/
  version. It must not mutate the existing V1 legacy evidence family.
- **P3.3-S5:** applies mechanics and compiles trusted prompt context without a
  new persistence family unless its separately reviewed bounded plan proves one
  is required; such a finding is a stop condition, not migration permission.
- Physical visit, region, world-state, and later-world storage remains deferred
  to the applicable reviewed P3.3-S7 subdivision; P3.3-S3 must not pre-empt it.

## Public, Demo, Web, and Dynamic Narrative preservation

Through P3.3-S5, the current public API/OpenAPI, deterministic Demo, Web schemas and
same-tab recovery, and Dynamic Narrative entry behavior remain byte/shape
compatible unless P3.3-S6 receives an explicit public-contract review.
In particular:

- existing `POST /v1/runs` request/response fields and idempotency behavior
  remain valid for the published legacy family;
- scenario discovery remains scenario discovery; it must not be repurposed as
  profile or world discovery;
- V1 evidence, fingerprints, error precedence, replay/no-write behavior,
  Session recovery, and allowlisted projections remain unchanged;
- Demo uses the same application authority with deterministic process-local
  persistence and no database or external Provider fallback;
- Web stores confirmed Session recovery before View retrieval, uses exact
  mutation evidence after uncertainty, and never synthesizes protocol/world
  authority;
- Dynamic Narrative may consume only an already trusted admitted context and
  remains untrusted for all mechanics, identities, versions, state, and canon.

P3.3-S6 is the only slice allocated to reviewed public discovery/override/
admission projection and production/Demo/Web parity. Browser evidence is not
implicit in P3.3-S6 authorization and requires separate authorization.
P3.3-S6 does not add a production Provider.

## Ordered implementation sequence

Every slice starts from a clean, aligned, published baseline and requires its
own bounded plan where this document says so. No later slice may begin before
the preceding slice is independently reviewed, separately authorized,
committed, manually pushed by the user, and confirmed clean/aligned.

### P3.3-G0 — Plan and compatibility freeze candidate

P3.3-G0 is exactly the unapproved documentation-only three-file candidate named
at the top of this plan. It performs no code, schema, runtime, test, staging,
commit, or publication action. Its proposed decisions are not frozen by
authoring or hashing. Stop until its exact corrected bytes are measured,
independently approved, separately authorized and committed, manually pushed by
the user, and confirmed as a clean aligned published baseline.

### P3.3-S1 — No-migration protocol/profile foundation

Implement only the exact strict identifiers/references, v1 envelope, validation,
canonical encoder/version-specific decoder, unknown/malformed/non-canonical
rejection, golden vectors, and no-I/O stored-record/codec round trip proposed
by this plan. The exact symbol/callable table above is mandatory.

P3.3-S1 has no Run binding, ORM, migration, repository I/O, entry integration,
profile lookup, authorization catalogue, deterministic resolution, numeric
engine values, defaults, overrides, API, Demo, Web, Provider, scenario, world,
visit, region, relationship, memory, or gameplay behavior. It cannot claim a
durably frozen Run Protocol.

P3.3-S1's exact path budget is:

| Kind | Exact paths |
| --- | --- |
| Production | `src/deviation_protocol/domain/run_protocol.py`; `src/deviation_protocol/infrastructure/run_protocol_persistence.py` |
| Tests | `tests/unit/test_run_protocol.py`; `tests/unit/test_run_protocol_persistence.py` |
| Documentation synchronization | `PLANS.md`; `docs/architecture.md`; `docs/run_protocol.md` |

No other path may change in P3.3-S1. The published planning authority is not
edited during implementation. If architecture review shows that these exact
paths cannot preserve dependency direction, stop and revise/re-review the plan;
do not silently widen the slice. If an eighth path is required, stop without
editing that path and report the blocker.

### P3.3-S2 — Deterministic profile resolution

First author, independently approve, publish, and confirm a commit-sized
P3.3-S2 slice plan. It must
select the exact engine domains and numeric ranges, authorized profile
catalogue/default values, permitted override catalogue, authority rules,
precedence, incompatibility behavior, deterministic resolver version, and
canonical resolution input/seed construction. The exact seed input must bind
the resolver version, authorized profile ID/version, canonical v1 envelope,
exact authorized overrides, applicable scenario/content version where relevant,
and any server-issued identity used by the selected algorithm; field order,
encoding, domain separation, and algorithm must be golden-tested.

Resolution is pure and deterministic: identical trusted inputs produce identical
resolved output and fingerprint independent of mapping insertion order, process,
locale, or hash seed. Presentation values never rewrite objective mechanics.
P3.3-S2 has no durable/public activation. Stop if any range/default/override/seed
detail is still implicit or if a model/client can influence an unapproved value.

### P3.3-S3 — Persistence and legacy/native compatibility

Author and independently approve a dedicated commit-sized P3.3-S3 slice plan and
migration review before code. Select the durable representation and migration,
then implement ORM, strict stored records/reconstruction, repositories/UoW,
trusted legacy/native distinction, required native protocol/profile binding,
evidence/fingerprint versioning as needed, rollback/cancellation, CAS/unique/
concurrency behavior, and corruption rejection.

Old rows remain untouched legacy rows under trusted stored proof. Native records
must carry explicit required state. P3.3-S3 has no public/native admission and no
world binding. Stop for a missing downgrade/data-safety decision, ambiguous
legacy proof, nullable-mode inference, backfill, refingerprint, or incomplete
real-MySQL concurrency plan.

### P3.3-S4 — Native Run admission and entry-world freezing

Author and independently approve and publish a commit-sized P3.3-S4 plan. Define an authored,
eligible entry-world authority with exact world ID/version; bind the authorized
resolved protocol and selected entry world atomically into native Run entry;
version native replay/evidence/fingerprints; preserve fixed scenario facts and
the scenario/world identity separation; and retain current legacy V1 behavior.

The P3.3-S4 plan must fix the native revision/mutation/evidence sequence without
changing legacy revision 1/2/3 meanings. Public-contract review is mandatory
before any request, response, error, or OpenAPI shape changes. Stop if admission
can partially create a Run/Session, select a world from scenario ID, accept
caller/model authority, or rewrite existing V1 bytes.

### P3.3-S5 — Objective mechanics application and trusted prompt-context compilation

Before implementation, author a dedicated bounded P3.3-S5 implementation plan
and obtain fresh independent read-only approval, a separately authorized commit,
user-controlled push, and clean published-baseline confirmation. P3.3-S5 must
not call a real Provider.

P3.3-S5 owns deterministic server-policy application of all five engine-owned
objective parameters: `resource_pressure`, `social_trust`,
`consequence_severity`, `information_opacity`, and `conflict_intensity`. Each
parameter's effects are applied by independent server-owned policy classes and
tested independently from prompt construction. Objective mechanics and
presentation remain strict separate authorities: `world_tone`,
`reality_boundary`, and `relationship_overlay` may change permitted expression
only and cannot change any engine outcome, cost, probability, resource,
relationship, death, world, permanent state, or canon fact.

P3.3-S5 also owns a deterministic, pure or side-effect-free,
Provider-independent trusted prompt-context compiler. It accepts only validated
trusted protocol/profile/mechanics/current-authority inputs frozen or resolved
by preceding slices, rejects untrusted or contradictory state, and emits one
deterministic canonical context byte sequence or one exact deterministic
structured representation fixed by the dedicated P3.3-S5 plan. Identical
trusted input produces identical compiled context independent of mapping order,
process, locale, hash seed, wall clock, Provider, or prose. Compilation performs
no persistence, network access, Provider call, outcome selection, or state
mutation. Provider calls remain outside database transactions and locks.

Compiled context grants the model no outcome, resource, relationship, death,
world-selection, permanent-state, or canon authority. Model output cannot
create, change, or override mechanics or canon. Regression evidence must prove
those negatives and prove that server-owned mechanics policies behave
identically when prompt construction is absent or its presentation varies.
Relationship overlay is presentation-only and cannot mutate or anticipate
Phase 3.4 relationship/residence state. Stop if mechanics are encoded only as
prompt instructions, if prompt construction applies an objective effect, if a
model can select a mechanic, if compiler input is not validated trusted state,
if canonical output remains undecided, or if a real Provider/Live call is
required for verification.

### P3.3-S6 — Public API, Demo, Web, projection, and recovery parity

Author and independently approve and publish a commit-sized P3.3-S6 plan. Add
only the approved profile/world discovery, permitted override submission,
native admission, and allowlisted projection needed by the approved product
design, with production API/OpenAPI, deterministic Demo, Web, exact replay,
uncertainty handling, and recovery parity. Do not add production Provider
integration.

Stop until the public discovery shape and authority, compatibility behavior,
response allowlists, recovery semantics, and separately authorized browser
evidence are explicit. If browser evidence is not separately authorized, omit
it and do not weaken the deterministic contract evidence.

### P3.3-S7 — Later worlds, visits, regions, revisits, progression, and persistent world continuity

Before any implementation, subdivide P3.3-S7 into independently reviewed,
commit-sized plans. Together they may implement deterministic later-world
selection, visit/region identity and state, revisits, priority injection,
anti-repeat, required progression, anti-farming, world-line transitions, and
canon preservation. Each subdivision must identify its exact identities,
state mutations, persistence/migration, evidence/replay/recovery, and regression
paths.

P3.3-S7 is a Phase 3.3 slice and is unrelated to the nonexistent P8-S7. Phase 8
remains implemented and complete at P8-S6. P3.3-S7 must not implement Phase
3.4, golden memory, cross-scenario logical NPC identity, Phase 6 hooks, or
Provider-owned selection. Stop if any listed deferred decision remains implicit
or if one commit-sized subdivision cannot be reviewed independently.

Important-NPC recovery priority is engine-owned and may consume only an
already-authorized logical-NPC-identity predicate and authored-world predicate
published by their owning authorities before the applicable P3.3-S7
subdivision. It must never derive logical identity from runtime `npc_id`, treat
a scenario NPC definition as cross-scenario identity, or match by name,
appearance, role, template, model output, or semantic similarity. It must not
create a counterpart, reincarnation, copy, successor, replacement, or other
continuity relation. It must not read or mutate relationship state, golden
memory, cross-scenario NPC persistence, Phase 6 subject-reference hooks, an
identity-resolution schema, or a memory schema.

If no already-authorized predicate exists, important-NPC priority is
unavailable and the selector continues deterministically using other authorized
eligibility and progression inputs. Absence must not manufacture identity,
block unrelated valid selection, imply a Provider decision, promote a runtime
NPC, or pull Phase 3.4 or Phase 6 into Phase 3.3. Future integration requires a
separately published identity/memory authority and a fresh bounded P3.3-S7
subdivision review before implementation.

## Deferred decisions and freeze owners

| Decision | Owner | Freeze gate | Stop condition |
| --- | --- | --- | --- |
| Numeric ranges | P3.3-S2 product/engine plan | Before P3.3-S2 implementation review | Any bound, unit, sign, or extreme remains implicit |
| Profile defaults | P3.3-S2 product/engine plan | Before P3.3-S2 implementation review | A missing/unknown profile can silently select a default |
| Override catalogue | P3.3-S2 product/authority plan | Before P3.3-S2 implementation review | A client/model value is accepted outside an exact allowlist |
| Objective-parameter mechanics policies | P3.3-S5 mechanics plan | Before P3.3-S5 implementation | Any effect, input, ordering, composition rule, mutation owner, or failure behavior remains implicit |
| Trusted prompt-context representation | P3.3-S5 compiler plan | Before P3.3-S5 implementation | Trusted input allowlist, canonical output, byte/structure bounds, or authority separation is unresolved |
| Public discovery shape | P3.3-S6 public-contract review | Before P3.3-S6 implementation | Request/response/OpenAPI/Demo/Web shapes or authority are unresolved |
| Initial-world catalogue | P3.3-S4 authored-content/engine authority | Before P3.3-S4 implementation | Eligibility, ID, version, ordering, or scenario compatibility is implicit |
| Visit/region representation | First applicable P3.3-S7 subdivision | Before its persistence design | Visit occurrence or region identity can be inferred from names/templates |
| Later-world weighting | P3.3-S7 selection subdivision | Before selector implementation | Weight domain, seed input, ordering, or tie-break is implicit |
| Anti-repeat | P3.3-S7 selection subdivision | Before selector implementation | Candidate exclusion/history window has no exact deterministic rule |
| Important-world designation | P3.3-S7 selection subdivision | Before priority/revisit implementation | Importance can be asserted by client/model or mutable prose |
| Revisit cooldown | P3.3-S7 revisit subdivision | Before revisit implementation | Cooldown unit, boundary, or authority is implicit |
| World-state schema | P3.3-S7 world-state subdivision | Before migration/implementation | State fields, mutability, provenance, or reconstruction are unresolved |
| Region unlocking | P3.3-S7 region subdivision | Before unlocking implementation | Unlock prerequisites/order/state mutation are implicit |
| Anti-farming | P3.3-S7 progression subdivision | Before reward/progression implementation | Revisit rewards can be repeated without exact bounded authority |
| Important-NPC recovery integration | P3.3-S7 recovery subdivision | Before recovery implementation | No separately published owning authority supplies both an already-authorized logical-identity predicate and authored-world predicate |
| World-line transition | P3.3-S7 continuity subdivision | Before transition implementation | Run/line/visit/canon continuity or atomic transition is implicit |
| Later migration/table/column design | P3.3-S3 for protocol binding; applicable P3.3-S7 subdivision for later state | Before each migration review | Physical design is preselected early, lacks up/down safety, or changes old rows |

## Verification matrix

CI is supplementary evidence and never substitutes for required local focused
verification. Ordinary Phase 3.3 verification requires no real Provider or
Live call.

### P3.3-S1

- strict focused unit tests for every carrier and actual-state revalidation;
- exact canonical golden bytes/length/hash and reordered-object rejection;
- encoder/decoder/no-I/O stored-record round trip;
- unknown record/payload version and contradictory-version rejection;
- malformed UTF-8/BOM/trailing/size/depth rejection;
- missing/extra/alias/private/duplicate-key/array/bool-as-int/float/non-finite/
  coercion/out-of-range rejection;
- the relevant existing unit suites at `tests/unit/test_run.py`,
  `tests/unit/test_run_operations.py`, `tests/unit/test_run_persistence.py`,
  `tests/unit/test_run_repositories.py`, `tests/unit/test_run_service.py`,
  `tests/unit/test_run_entry_service.py`, `tests/unit/test_run_entry_api.py`, and
  `tests/unit/test_run_composition.py`;
- `.\.venv\Scripts\python.exe -m compileall -q src tests alembic` and
  `.\scripts\verify.ps1 -Mode Offline` under the repository workflow.

P3.3-S1 runs no MySQL, Alembic, Provider, browser, or Live verification.

### P3.3-S2

- complete domain/range/default/override matrices;
- precedence, incompatibility, authority, and representation-vs-resolution
  tests;
- mapping-order, process/hash-seed, resolver-version, seed/input, and golden
  deterministic vectors;
- proof that presentation fields do not mutate objective mechanics.

### P3.3-S3

- focused unit and real-MySQL integration tests;
- migration upgrade and safe downgrade behavior, plus exact old-row preservation;
- legacy/native reconstruction and caller-absence non-selection;
- rollback, cancellation, CAS loss, unique collisions, concurrent winners,
  exact replay/conflict, uncertain outcome, and corrupt/partial/cross-bound
  rejection;
- Alembic heads/history and matching metadata/schema checks;
- Offline, MySQL, and Full verification modes as required by the workflow.

### P3.3-S4

- atomic native entry and exact replay/conflict matrices;
- unchanged legacy V1 namespaces, evidence, fingerprints, revisions, replay,
  recovery, and public behavior;
- native evidence/version goldens and protocol/world binding reconstruction;
- scenario/world identity separation and fixed-scenario-fact preservation;
- rollback/cancellation/CAS/uniqueness/concurrency/uncertain-commit cases with
  no partial Run, binding, participation, Session, protocol, or world state.

### P3.3-S5

- complete deterministic effect matrices for `resource_pressure`,
  `social_trust`, `consequence_severity`, `information_opacity`, and
  `conflict_intensity`, with each server-owned policy tested independently from
  prompt construction;
- cross-product regressions proving presentation changes expression only and
  cannot change mechanics, outcome, cost, probability, resource, relationship,
  death, world selection, permanent state, or canon;
- exact trusted-input allowlist, rejection of malformed/untrusted/cross-bound
  state, and golden canonical prompt-context bytes or exact structured
  representation;
- mapping-order, process/hash-seed, locale, and repeat-run deterministic
  compiler evidence with no clock/random/I/O dependency;
- regressions proving model output cannot create, change, or override mechanics
  or canon and compiled context grants no mutation authority;
- relationship-overlay regressions proving no Phase 3.4 state is read or
  mutated;
- Provider-independent fake/offline evidence only, with no real Provider,
  browser, or Live call; and
- transaction instrumentation proving compilation and every Provider call occur
  with no active UoW, `AsyncSession`, or database lock.

### P3.3-S6

- strict API request/response/error and OpenAPI compatibility tests;
- deterministic Demo parity and no external Provider/database fallback;
- Web schema, discovery/override, exact replay, response uncertainty, Session
  storage-before-View, GET-only recovery, and no automatic replacement write;
- browser evidence only under separate authorization; no Provider/Live call.

### P3.3-S7

- deterministic selection, weighting/order/tie-break and anti-repeat vectors;
- visit/revisit/region/world-state identity and reconstruction;
- important-world priority, cooldown, required progression, anti-farming, and
  recovery behavior;
- important-NPC priority tests consuming only separately published authorized
  logical-identity/world predicates, plus predicate-absence tests proving other
  authorized eligibility/progression selection continues without identity
  manufacture, runtime-NPC promotion, Provider choice, or Phase 3.4/6 state;
- rejection vectors for runtime `npc_id`, scenario NPC definition, name,
  appearance, role, template, model output, semantic similarity, counterpart,
  reincarnation, copy, successor, replacement, relationship, golden-memory,
  cross-scenario-persistence, Phase 6 subject-reference, identity-resolution,
  and memory-schema inputs;
- continuous-world-line transition and canon/fixed-fact preservation;
- atomic state mutation, replay, cancellation, corruption, and concurrency for
  every independently planned subdivision.

## Requirement-to-slice coverage matrix

Every numbered Phase 3.3 implementation acceptance criterion in
[`run_protocol.md`](run_protocol.md#implementation-acceptance-criteria) has one
terminal owning slice below. Prerequisites may supply part of the proof, but the
owner cannot declare its criterion complete without the listed implementation
and verification evidence. No unowned criterion remains after P3.3-S7.

| Criterion | Owning slice | Prerequisite slices | Required implementation evidence | Required verification evidence | Stop condition |
| --- | --- | --- | --- | --- | --- |
| 1. Validated versioned profile and frozen Run Protocol boundary | P3.3-S4 | P3.3-S1, P3.3-S2, P3.3-S3 | Strict v1 representation, authorized resolved profile, explicit durable native binding, atomic admission freeze | P3.3-S1 codec goldens; P3.3-S2 authorization/resolution vectors; P3.3-S3 reconstruction/legacy-native tests; P3.3-S4 atomic binding/replay tests | Any missing/nullable/defaulted/unknown protocol or profile state can admit, reconstruct, replay, or fall back |
| 2. Defaults and permitted overrides resolved before first turn | P3.3-S4 | P3.3-S1, P3.3-S2, P3.3-S3 | P3.3-S2 resolver produces one authorized result; P3.3-S4 admits only that result before activation | Precedence/override matrix and native-entry rejection after activation or with unresolved inputs | Resolution can occur, change, or silently default after first-turn admission |
| 3. Objective effects independent from presentation | P3.3-S5 | P3.3-S1 through P3.3-S4 | Five independent server-owned mechanics policies; presentation-only compiler path | Per-policy effect matrices and mechanics-without-prompt/presentation-variation regressions | Any objective effect exists only in prompt text or changes with presentation |
| 4. Character authority separate from difficulty and presentation | P3.3-S5 | P3.3-S1 through P3.3-S4 | Typed trusted compiler/mechanics inputs preserve character/profile/presentation domains | Cross-domain substitution and mutation rejection; identical character authority under presentation variation | Profile or presentation rewrites character identity, abilities, knowledge, personality, viewpoint, or applicable version |
| 5. Relationship atmosphere cannot mutate objective relationship state | P3.3-S5 | P3.3-S1 through P3.3-S4 | Relationship overlay is compiler presentation input only; no Phase 3.4 dependency or mutation port | Off/veiled/charged equivalence for objective state plus absence-of-write/capability tests | Overlay reads, creates, changes, or anticipates relationship/residence state |
| 6. Identical trusted inputs produce identical engine-owned outcomes | P3.3-S5 | P3.3-S1 through P3.3-S4 | Deterministic policy composition and canonical compiler input/output | Repeat, mapping-order, locale, process/hash-seed, clock/random-denial, and golden vectors | Outcome or compiled context depends on unordered iteration, process, locale, wall clock, Provider, or prose |
| 7. Prompt construction uses only validated frozen state and grants no model authority | P3.3-S5 | P3.3-S1 through P3.3-S4 | Pure Provider-independent trusted context compiler over validated protocol/mechanics/current authority | Untrusted/cross-bound input rejection and model-no-authority regressions for outcome/resource/relationship/death/world/permanent-state/canon | Compiler accepts unvalidated state, mutates state, calls Provider, or exposes a mechanics/canon mutation route |
| 8. `Grim`, `Heroic`, and `Chaotic` limits have regression coverage | P3.3-S5 | P3.3-S1 through P3.3-S4 | Presentation policies permit expression only and bind no fixed-fact mutation | Grim cannot spoil/lower a valid resource; Heroic cannot create success; Chaotic cannot create permanent canon; objective result equivalence | Any presentation token changes established mechanics, facts, result, or canon |
| 9. Current scenarios retain fixed facts absent trusted engine event | P3.3-S5 | P3.3-S1 through P3.3-S4 | Mechanics and compiler consume fixed facts read-only; only existing trusted event authority may change mutable facts | Existing fixed-fact suites plus adversarial compiled-context/model-output regressions | Protocol, compiler, mechanics presentation, or model output rewrites a fixed scenario fact |
| 10. Authored entry-world freeze and deterministic later-world progression/recovery | P3.3-S7 | P3.3-S1 through P3.3-S6; P3.3-S4 owns entry-world freeze | P3.3-S4 immutable authored entry-world binding; P3.3-S7 deterministic eligible-pool selector with progression priority | P3.3-S4 ID/version freeze tests; P3.3-S7 ordering/seed/tie-break/progression/recovery vectors | Arbitrary/caller/model world choice, scenario-as-world, mutable entry world, nondeterminism, or required progression stranded |
| 11. Important-world revisits preserve state, authorize content, resist farming, and remain recoverable | P3.3-S7 | P3.3-S1 through P3.3-S6 | Explicit visit/region/world-state identity, authored revisit eligibility, priority, continuity, and anti-farming policies | Reconstruction, state/consequence preservation, region authorization, cooldown/anti-repeat/anti-farming, recovery, replay, and concurrency suites | Revisit resets/copies world state, unlocks unauthorized content, repeats reward, loses authored recovery, or relies on Provider choice |
| 12. Documentation and phase status synchronized | P3.3-S7 | P3.3-G0 and every completed P3.3-S1 through P3.3-S6 slice | Each slice updates its owned authorities; P3.3-S7 closeout reconciles complete Phase 3.3 status without altering historical records | Canonical documentation-synchronization checklist, complete diff including untracked paths, targeted status searches, and Git diff checks | Any behavior/interface/evidence/migration/status fact lacks an owning synchronized document or Phase 3.3 is called complete early |

## Documentation-synchronization requirements

P3.3-G0 and every later slice must complete the canonical checklist in
`docs/engineering/codex_workflow.md` before independent review, a completion
claim, or a commit-authorization request. Each slice must:

1. identify every behavior, interface, evidence, migration, verification, and
   status fact it changes and the canonical document that owns that fact;
2. update all owned documentation in the same candidate while preserving
   candidate-time wording in frozen historical plans;
3. distinguish implemented behavior, approved product design, the planned
   slice, and still-deferred work;
4. reconcile `PLANS.md`, `docs/run_protocol.md`, `docs/architecture.md`, public
   contract documentation, migration authority, and applicable slice plans only
   where the slice actually changes their owned facts;
5. assess guardrail impact without recording speculative or unconfirmed rules;
   and
6. stop rather than silently adding an unreviewed path or claiming completion
   with missing documentation.

## Independent review, candidate hashing, baseline invalidation, and publication

The approval/publication/freeze section above names the only operative success verdict.
Review applies only to the exact complete candidate, baseline, three-path
inventory, and recorded hashes. A relevant baseline change or any byte change
to an approval-bound document invalidates the hash set and review; the corrected
candidate must be re-hashed and independently re-reviewed. Historical or subset
approval cannot satisfy this gate.

Identity measurements are not approval, freeze, publication, commit readiness,
or implementation authorization. Because writing a measured hash into an
approval-bound file would change that file, the final per-path line/byte/SHA-256
identities and canonical ordered complete-patch byte count/SHA-256 are measured
after the last correction and supplied externally with the fresh review prompt.
The review binds those exact measurements, the exact baseline, the three-path
inventory, and the complete bytes. Any subsequent byte change invalidates the
measurement set and review. Candidate semantics become frozen only after the
review approves those exact bytes, the user separately authorizes the exact
commit, that exact commit is created, the user pushes it, and a clean aligned
published baseline is confirmed.

### Slice workflow and stop conditions

For P3.3-G0 and every implementation slice:

1. Confirm a clean, aligned published baseline and read the current authorities.
2. Author the exact commit-sized candidate and synchronize every affected
   canonical document using the workflow checklist.
3. Record SHA-256 for every approval-bound path. Any baseline change relevant to
   candidate facts or any byte change invalidates the hash/review.
4. Obtain a fresh independent read-only review of exact bytes and hashes. The
   review prompt's success verdict must satisfy the candidate's exact approval
   condition.
5. Stop on unresolved Critical/High/Medium findings, scope drift, stale hashes,
   an incompatible authority, a required fourth P3.3-G0 path, or a verification gap.
6. After review success, obtain separate explicit user authorization for one
   exact local commit. Review approval is not commit authorization.
7. Stage only the authorized paths, verify the staged diff, path set, hashes,
   baseline, and approval binding, then create only that authorized local commit.
8. Never push. The user pushes manually.
9. Confirm the pushed commit is a clean aligned published baseline before
   requesting or beginning separately authorized implementation.

For this P3.3-G0 candidate, the documentation commit path set is exactly:

```text
PLANS.md
docs/phase_3_3_run_protocol_implementation_plan.md
docs/run_protocol.md
```

No implementation may begin merely because this candidate was authored,
reviewed, committed, or published. Each slice requires separate authorization.

## Residual limitations and deferred work

Even after P3.3-S1, the repository has no authorized profiles, numeric resolution,
durable protocol binding, native Run, authored world, visit, region, world state,
mechanics application, trusted prompt context, or public protocol surface.
P3.3-S2 still has no durable/public activation. P3.3-S3 still has no world or
public/native admission. P3.3-S4 remains internal. P3.3-S5 adds no public
surface or real Provider call. P3.3-S6 does not add later-world continuity.
P3.3-S7 requires its own subdivisions and does not complete Phase 3.4, Phase 6,
Phase 7, production Provider distribution, golden memory, or cross-scenario NPC
identity.

The current legacy family remains supported throughout. No slice may claim full
Phase 3.3 completion until all required P3.3-S1 through P3.3-S7 work,
documentation synchronization, independent review, authorized commits, user
publication, and clean aligned baseline confirmation are complete.

## Guardrail impact

Assessed guardrails: `DB-001`, `AUTH-001`, `STATE-001`, `API-001`, `SCENE-001`,
`MODEL-001`, `MODEL-002`, `CONTENT-001`, `PLAY-001`, `GIT-001`, and `ENV-002`.
This candidate applies their existing reusable rules and establishes no new
confirmed defect-derived reusable rule.

Guardrail impact: None

## P3.3-S1 review-authority amendment

Status and effect: **This is a documentation-authority predecessor amendment
candidate authored against published baseline
`76064d200d1aa5af7cddff22d33acb03e608e598`. It changes only the review
governance and verification interpretation for P3.3-S1. Until its exact bytes
are independently approved, separately committed, user-pushed, and confirmed
as a published authority baseline, it grants no implementation or Git
authority.**

This section is a clearly bounded amendment to the plan above. It preserves the
original P3.3-G0 candidate-time narrative as history while superseding only its
now-stale current-status, next-action, S1 review-verdict, and canonical-ceiling
test-interpretation wording. It does not reopen or alter any P3.3-G0 product,
representation, schema, compatibility, sequencing, symbol, or runtime decision.

### Current authority and candidate status

- P3.3-G0 remains approved, published, frozen, and complete at
  `76064d200d1aa5af7cddff22d33acb03e608e598`.
- The exact local seven-path P3.3-S1 implementation candidate remains
  unapproved, unstaged, uncommitted, unpublished, and incomplete. Its first
  independent read-only review returned `CHANGES_REQUIRED`.
- The current seven-path hashes, its complete-patch identity, and every prior
  implementation-authoring label are preservation and history facts only. They
  are non-operative for approval and must not be reused after correction.
- The seven implementation paths must remain byte-identical throughout this
  one-path predecessor authority task. No review finding is corrected in those
  paths by this amendment.
- After this amendment is approved and published, the preserved seven-path
  candidate must be corrected for every independent-review finding, fully
  remeasured, reverified where required, and freshly independently reviewed.
- P3.3-S1 is not complete. Phase 3.3 remains incomplete. P3.3-S2 through
  P3.3-S7 remain unauthorized.

The preservation-only pre-amendment implementation manifest is:

| Exact path | Lines | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `PLANS.md` | 1,407 | 87,348 | `6983b28f323599c852f0500499a5796ca5b0de4532d2fd8bb6f316641f7153c6` |
| `docs/architecture.md` | 1,298 | 109,672 | `fa4a579ecf06063306ed61a5e010bf7a9c2e5773fa7875c2fefabf322179603d` |
| `docs/run_protocol.md` | 754 | 39,294 | `f12be164b2aba2708b5ab837f482a8aaceb67ff06aa8d1fa9d6c4c31d2467d3b` |
| `src/deviation_protocol/domain/run_protocol.py` | 449 | 15,391 | `db79005aa28662c4be3516b2f67c8c826a3b3cee8f0db23de1e3cd2505074a16` |
| `src/deviation_protocol/infrastructure/run_protocol_persistence.py` | 85 | 3,381 | `31f1befca159113f0ef98c381f4026fb8e8b68131b76cd44beba2ea18c420196` |
| `tests/unit/test_run_protocol.py` | 621 | 21,709 | `25a4b5463038e862795aa0bd8e060203675105158c4f577225ecc84ed5cd37bc` |
| `tests/unit/test_run_protocol_persistence.py` | 327 | 11,141 | `0d4baabc82e39def27930610ca1318dd42f0effc40b55db7a702dc1e6964e792` |

Their canonical ordered isolated seven-path patch is exactly `80,019` bytes
with SHA-256
`064dd425f1b412495ddbf62e6995b18d1266c5b0b7dc2ab7d12b41c6e58bfe25`.
This manifest must remain exact during the amendment task, but neither it nor
its prior review can satisfy a future implementation approval gate.

### Operative review verdict for this one-path authority amendment

There is exactly one operative success verdict for independent review of this
exact one-path authority-amendment candidate:

`PHASE_3_3_S1_REVIEW_AUTHORITY_AMENDMENT_INDEPENDENT_REVIEW_APPROVED`

The verdict is valid only when all of these conditions hold:

1. It is returned by a fresh independent read-only review of exactly
   `docs/phase_3_3_run_protocol_implementation_plan.md` as the sole amendment
   path. It applies to no implementation path or other documentation path.
2. The review prompt binds branch `main`; exact `HEAD`, local `main`, and local
   `origin/main` baseline
   `76064d200d1aa5af7cddff22d33acb03e608e598`; ahead/behind `0/0`; the exact
   amended-plan bytes and per-file line/byte/SHA-256 identity; and the exact
   isolated one-path amendment-patch byte count and SHA-256 against that
   baseline.
3. The amended-plan and isolated amendment-patch identities are measured only
   after authoring is complete and are supplied externally with the review
   prompt. They are not written back into this approval-bound file.
4. Any byte change to the amended plan or any relevant baseline, inventory, or
   identity change invalidates the measurements and every review of them. The
   changed candidate must be remeasured and freshly independently reviewed.
5. Historical P3.3-G0 approval, including
   `PHASE_3_3_RUN_PROTOCOL_IMPLEMENTATION_PLAN_INDEPENDENT_REVIEW_APPROVED`,
   cannot satisfy this gate. No historical or subset review can satisfy it.
6. The non-operative authoring-complete label
   `PHASE_3_3_S1_REVIEW_AUTHORITY_AMENDMENT_CANDIDATE_COMPLETE` cannot satisfy
   this gate. No prior P3.3-S1 implementation authoring label can satisfy it.
7. The future
   `PHASE_3_3_S1_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED` verdict cannot
   satisfy this gate and is not a substitute for amendment review.
8. Approval authorizes no staging, commit, push, implementation correction,
   implementation acceptance, publication claim, or P3.3-S2 through P3.3-S7
   work.
9. After approval, a separate explicit authorization is required for one exact
   local commit containing only the approved plan amendment. The user performs
   the push. The pushed amendment must then be confirmed as the published
   authority baseline before the seven-path implementation may be corrected.

Every other success-looking, authoring, historical, implementation, failure,
blocked, changes-required, or differently scoped verdict is non-operative for
this exact one-path amendment.

### Operative review verdict for the future corrected S1 implementation

The sole operative success verdict for a future corrected exact seven-path
P3.3-S1 implementation candidate is:

`PHASE_3_3_S1_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

This token is defined now so the implementation gate is reachable and
unambiguous, but it is not usable for the current amendment or the current
uncorrected implementation candidate. It becomes usable only after this exact
authority amendment has received its own operative approval, has been committed
under separate one-path authorization, has been pushed manually by the user,
and has been confirmed as the published authority baseline.

The future implementation verdict is valid only when all of these conditions
hold:

1. It is returned by a fresh independent read-only review of one corrected
   candidate containing exactly these seven paths and no others:

   ```text
   PLANS.md
   docs/architecture.md
   docs/run_protocol.md
   src/deviation_protocol/domain/run_protocol.py
   src/deviation_protocol/infrastructure/run_protocol_persistence.py
   tests/unit/test_run_protocol.py
   tests/unit/test_run_protocol_persistence.py
   ```

2. That implementation candidate is authored against the later exact published
   authority baseline containing this amendment. The review binds that exact
   baseline and branch/ref topology, the exact seven-path inventory, every
   file's line/byte/SHA-256 identity, the complete canonical ordered binary-safe
   seven-path patch byte count and SHA-256, and the complete candidate bytes.
3. The review binds the required verification evidence, the exact 22-symbol
   P3.3-S1 production contract, canonical documentation synchronization, and
   every P3.3-S1 acceptance and verification requirement in this amended plan.
4. Any candidate byte change or relevant baseline, inventory, identity,
   contract, evidence, or authority change invalidates approval. A changed
   candidate must be remeasured, reverified as required, and freshly
   independently reviewed.
5. The historical P3.3-G0 token, this authority-amendment token, any authoring
   token, the first `CHANGES_REQUIRED` review, any other historical review, and
   any subset review cannot satisfy the future implementation gate.
6. Implementation approval authorizes no staging, commit, push, publication,
   or P3.3-S2 through P3.3-S7 work. A separate exact implementation-commit
   authorization remains mandatory, and the user performs every push.

### Canonical-envelope ceiling clarification

This amendment preserves without modification:

- the `1,024`-byte raw ceiling;
- the `1,024`-byte canonical ceiling;
- envelope epoch `run-protocol-envelope` and record version `1`;
- schema literal `run-protocol-envelope/v1`;
- the exact 22-symbol P3.3-S1 contract;
- golden vector V1-REP-001, its exact `193` bytes, and SHA-256
  `a7e0149e8241f1b4d1c74487da2b8bcf36c93d05310c76a9b847d4e57c5a3a8a`;
- the profile-ID grammar and its `128`-byte/code-point maximum;
- all enum values and canonical encoding rules; and
- the exact seven-path P3.3-S1 implementation budget.

The canonical `1,024`-byte limit is a defensive version-envelope ceiling and
reserved headroom. It is not a claim that the current v1 grammar can produce a
valid envelope at that size. The ceiling must not be reduced or increased, and
the v1 grammar must not be expanded merely to make the ceiling reachable.

For v1, canonical length is exactly the fixed `160` bytes of object framing,
field names, punctuation, quotes, and fixed schema literal, plus the UTF-8 byte
lengths of profile ID, decimal profile version, world tone, reality boundary,
and relationship overlay. The independent maximum is therefore:

```text
160 + 128 + 19 + 8 + 7 + 7 = 329 UTF-8 bytes
```

The maxima are a legal `128`-byte ASCII profile ID, positive signed 64-bit
profile version `9223372036854775807` (`19` digits), `balanced` (`8` bytes),
either `deviant` or `chaotic` (`7` bytes), and `charged` (`7` bytes). There are
no other variable-length v1 fields. Thus the largest valid canonical v1
envelope is `329` bytes, leaving `695` bytes of defensive headroom. A genuine
valid canonical v1 envelope of `1,024` or `1,025` bytes is mathematically
unreachable under the frozen grammar.

The future correction test must fix one maximum-length representation
independently of the production serializer. Its exact construction is:

```python
MAXIMUM_V1_CANONICAL_BYTES = (
    b'{"profile_ref":{"profile_id":"'
    + (b"A" * 128)
    + b'","profile_version":9223372036854775807},'
    + b'"reality_boundary":"deviant",'
    + b'"relationship_overlay":"charged",'
    + b'"schema_version":"run-protocol-envelope/v1",'
    + b'"world_tone":"balanced"}'
)
```

That exact independently constructed byte string has length `329` and SHA-256
`0e0b1f498e1bf51656f1c5e5c742074e864da9678964c048087f52bdf5066e78`.
Selecting `chaotic` instead of the fixed `deviant` vector also reaches the same
maximum length but produces different bytes and is not the fixed digest vector.

The corrected P3.3-S1 evidence must satisfy all of the following:

1. No test may fabricate or describe a `1,024`- or `1,025`-byte string as a
   genuine valid serialized v1 envelope.
2. Branch-isolation testing of the encoder's post-canonicalization inclusive
   `1,024`/reject-`1,025` guard is explicitly acceptable. It must be named and
   described as internal defensive-branch evidence and may replace the internal
   canonical-byte helper solely to isolate that otherwise unreachable branch.
   It is not end-to-end valid-envelope or real-serializer boundary evidence.
3. Independent genuine serializer evidence must construct an envelope from the
   exact maximum legal inputs fixed above, exercise the real production
   canonical serializer without replacing its helper, and compare the result
   with `MAXIMUM_V1_CANONICAL_BYTES` or another equally independent exact fixed
   representation.
4. That genuine test must assert exact length `329`, separately fixed SHA-256
   `0e0b1f498e1bf51656f1c5e5c742074e864da9678964c048087f52bdf5066e78`,
   and that `329 < 1_024`. Expected bytes or digest must not be calculated by
   calling the production serializer or its canonical helper.
5. The raw `1,024`/`1,025` boundary must continue to be exercised genuinely
   through the public decoder: an exact `1,024`-byte raw payload reaches parsing
   and the expected later canonicality rejection, while an exact `1,025`-byte
   raw payload fails the pre-parse raw ceiling.
6. The production encoder must continue enforcing the `1,024`-byte canonical
   defensive ceiling even though valid current v1 values cannot reach it.
7. Any future envelope version or grammar expansion requires separate authority,
   compatibility analysis, new exact bounds/vectors, independent review, and
   implementation authorization. It cannot silently consume the reserved
   headroom.

### Required predecessor and correction order

The only authorized order is:

1. Author this exact one-path authority-amendment candidate.
2. Obtain fresh independent read-only review whose sole success verdict is
   `PHASE_3_3_S1_REVIEW_AUTHORITY_AMENDMENT_INDEPENDENT_REVIEW_APPROVED`.
3. Obtain separate explicit authorization for one exact local one-path commit.
4. Commit only the exact independently approved plan amendment.
5. The user pushes that commit manually.
6. Confirm the amended authority as the published baseline.
7. Correct the preserved seven-path P3.3-S1 implementation candidate for exact
   scalar pre-normalization validation; scalar-subclass and `StrEnum`/`IntEnum`
   regressions; genuine 329-byte maximum-envelope evidence; explicit internal
   defensive-branch characterization of the 1,024/1,025 canonical guard test;
   and stale architecture status passages.
8. Rerun every verification required for the corrected P3.3-S1 candidate.
9. Recompute all seven per-file identities and the complete binary-safe
   seven-path patch identity against the new published authority baseline.
10. Obtain fresh independent read-only review whose sole success verdict is
    `PHASE_3_3_S1_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`.
11. Only after that approval may a separately authorized exact implementation
    commit be considered. Approval alone is not commit authorization.

No step may be collapsed, reordered, inferred from a prior review, or treated
as authority for the next step.

### Amendment scope and document ownership

This one-path amendment changes S1 review governance and verification
interpretation only. The plan is the canonical owner of its slice gate,
verification interpretation, and ordered predecessor/correction sequence; no
second document is required for this authority correction.

This amendment changes no runtime or product behavior, public contract,
canonical envelope byte, ceiling constant, epoch, record version, schema,
profile-ID grammar, enum, symbol contract, golden vector, canonical encoding
rule, database or migration authority, P3.3-S2 through P3.3-S7 behavior, current
seven-path implementation byte, or historical P3.3-G0 approval fact. It grants
no authority to correct the implementation during this predecessor task.

Guardrail impact: None. The confirmed approval-token reachability failure is
already governed by the approval-token consistency rule in
`docs/engineering/codex_workflow.md`; this bounded amendment applies that
existing rule and creates no new reusable guardrail.

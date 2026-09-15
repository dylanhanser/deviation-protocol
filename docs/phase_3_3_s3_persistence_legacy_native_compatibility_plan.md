# Phase 3.3 S3 Persistence and Legacy/Native Compatibility Plan Third Correction Candidate

Status: **Unapproved, unstaged, uncommitted, unpublished documentation-only
third corrected candidate authored on 2026-09-16 against
`20eab60a99c093f2ccf0224dee200e142fc194b6`. P3.3-S3 implementation has not
begun, and no migration has been created or executed.**

Phase ownership: **P3.3-S3 only**

Candidate scope: exactly this file, [`../PLANS.md`](../PLANS.md), and
[`run_protocol.md`](run_protocol.md). Plan approval alone grants no
implementation, database, staging, commit, push, publication, or later-slice
authority.

## 1. Baseline, lifecycle, and controlling authority

| Fact | Exact value |
| --- | --- |
| Repository | `D:\deviation-protocol` |
| Branch | `main` |
| `HEAD`, local `main`, local `origin/main` | `20eab60a99c093f2ccf0224dee200e142fc194b6` |
| Ahead/behind | `0/0` |
| Subject | `feat(run): implement Phase 3.3 S2 profile resolution` |
| Parent | `2f3f84a4d63d00d2e3bbbe0e4eb6dafd9c3435fe` |
| Supplied pre-correction worktree | modified `PLANS.md`; modified `docs/run_protocol.md`; untracked this plan; no fourth path |
| Supplied index/operations | empty; no conflicts, active Git operations, or locks |

P3.3-S1 is published and closed: implementation commit `6212a760a549920c1c11dcb01e07566945df5556`
and closeout commit `4d146679e782ff555819b411fc5048e55299de4d`.
The exact S2 plan is published at
`2f3f84a4d63d00d2e3bbbe0e4eb6dafd9c3435fe`, and its exact implementation is
published at `20eab60a99c093f2ccf0224dee200e142fc194b6`. P3.3-S3 is the next
sequential planning subject. This candidate is not approval. No S3
implementation has begun; no migration exists or has run; S4 through S7 remain
unauthorized; Phase 3.3 remains incomplete.

The first independent S3 plan review returned `CHANGES_REQUIRED` with exactly
five material findings: (1) a hidden production test writer, (2) an
unimplementable and conflated legacy proof, (3) a race-unsafe downgrade, (4)
unsupported MySQL 1062 key identification, and (5) non-executable vector
definitions. The first correction completed. The second independent review
returned `CHANGES_REQUIRED` with exactly five Medium findings: named-lock
outcomes, four-exception ownership, native first-failure order, V02/V03 setup,
and vector-to-suite allocation. The second correction completed. The third
independent review returned `CHANGES_REQUIRED` with exactly three findings:
(1) a plain downgrade probe could miss a committed row behind an older
REPEATABLE READ snapshot, (2) complete bound-Run validation preceded loading
its required immutable character revision, and (3) state-detected connection
loss between destructive DDL statements lacked explicit branches. This document
is the third corrected candidate. None of the three reviews was approval; none
grants implementation or Git authority.

The frozen parent plan and frozen S2 plan remain byte-preserved historical
authority. S1 supplies strict canonical envelope representation and no-I/O
storage conversion. S2 supplies pure deterministic profile resolution. S3
adds durable representation and reconstruction only. S4 remains the first
slice allowed to admit a native Run and bind its authored entry-world
identity/version.

## 2. Purpose and non-goals

S3 owns exactly:

- durable protocol/profile binding representation;
- trusted legacy/native classification;
- strict reconstruction;
- ORM mapping;
- Repository and Unit-of-Work seams;
- one matching Alembic migration and its downgrade policy;
- rollback and cancellation behavior;
- existing Run CAS preservation, physical uniqueness, and concurrency integrity;
- corruption and partial-state rejection; and
- focused unit and real-MySQL verification.

S3 does not own public/native admission; entry-world selection or binding;
objective mechanics application; prompt compilation; API or OpenAPI changes;
Demo or Web changes; Provider calls; visit, region, world-state, or continuity
storage; migration or rewriting of legacy rows; or implementation authority
for S4 through S7 or any other phase. S3 creates no production application
service, public admission route, or internal production command that can admit
a native Run.

## 3. Persisted legacy proof and ownership boundary

S3 classifies stored families. It does not authorize a caller. In particular,
`RunEntryCreationEvidence` contains exactly `controller_operation`,
`player_character`, `scenario`, and `trusted_run_source` plus its schema literal.
It contains no Session `player_id`. The classifier never compares a caller
principal with creation evidence and never represents its result as permission
to replay, recover, disclose, or enter a Run.

The private infrastructure legacy-proof algorithm loads persisted rows in this
exact order and stops at the first failure:

1. Select `run_current` by exact `run_id`; then select all `run_revisions`
   ordered by `state_version`, all `run_session_participations` ordered by
   `(joined_state_version, session_id)`, the single `run_creation_receipts` row
   by `result_run_id`, and all `run_mutation_receipts` ordered by
   `(resulting_state_version, operation_id)`. Convert field-for-field frozen
   stored carriers, then perform L01-L04 in section 3.0, including loading and
   decoding the referenced immutable character revision before calling the
   unchanged `validate_stored_run_record_set`. Outer classifier step 2 performs
   this once; legacy evaluation reuses its rows and validated result.
2. Require exactly revisions 1, 2, and 3 on one Run/line: revision 1 is
   `CREATE`/`pre_first_turn`; revision 2 is
   `BIND_PLAYER_CHARACTER`/`pre_first_turn`; revision 3 is
   `ATTACH_SESSION`/`active`; `run_current` equals revision 3 in every canonical
   Run field, contains the same active character, and has the existing exact
   audit-time relationship. Revision 1 is unbound; revisions 2 and 3 contain
   the same active `ReservedPlayerCharacterBinding`.
3. Require the sole `run.create/v1` receipt for revision 1. Its evidence starts
   with `P8_S2_EVIDENCE_MAGIC = 89 44 50 38 53 32 43 45 0d 0a 1a 0a`, byte 12
   is `P8_S2_EVIDENCE_VERSION = 1`, and the remainder strictly and canonically
   decodes as `RunEntryCreationEvidence` schema
   `run-entry.creation-evidence/v1`. Re-encode the exact evidence and require
   the receipt fingerprint to equal SHA-256 of the complete magic/version/
   payload bytes. Require receipt columns, canonical receipt, revision-1
   result, operation ID, source, and timestamp to agree.
4. Require exactly one `run.bind-player-character/v1` mutation receipt for
   revision 2 and one `run.attach-session/v1` mutation receipt for revision 3.
   Strictly decode and canonically re-encode both receipts and command-evidence
   values; require their fingerprints, namespaces, result schemas, result
   columns, expected/result versions, operation IDs, source references,
   participation/character columns, adjacent revisions, and timestamps to
   agree.
5. Derive the creation, character-binding, attachment, and Session-creation IDs
   from persisted `controller_operation.controller_binding` and
   `controller_operation.public_operation_key` with the existing deterministic
   `derive_run_entry_internal_id` function. Require those IDs to equal the
   three Run operations and `game_sessions.creation_client_request_id`.
6. Perform the active player-character/controller stored-consistency algorithm
   in section 3.1.
7. Require exactly one revision-3 participation and compare its `session_id`,
   `run_id`, `continuous_story_line_id`, `joined_state_version = 3`,
   `operation_id`, `source_reference`, and `joined_at` with revision 3, the
   attachment receipt, and the common transaction time.
8. Perform the private structural Session algorithm in section 3.2.
9. Require the source in creation evidence to equal the creation, binding,
   attachment, and participation source columns. This proves stored source
   consistency only. Comparison with the currently configured trusted source
   remains in the unchanged `RunEntryService`.

The namespaces and versions remain exactly `run.create/v1`,
`run.bind-player-character/v1`, `run.attach-session/v1`, their three
`run.*-result/v1` schemas, `run-entry.creation-evidence/v1`, P8 evidence version
1, canonical Run receipts, and their existing SHA-256 fingerprints. Existing
primary keys, foreign keys, unique constraints, and Run CAS behavior remain
unchanged. S3 adds no receipt, evidence namespace, replay protocol, or write.

### 3.0 Shared Run loading prerequisite and complete validation

This sequence applies to every existing Run, before legacy membership or native
reconstruction; it uses only persisted rows, never a caller principal, creation
evidence decoded later, or a not-yet-validated `CanonicalRun` to select the
immutable character row. The unchanged repository already loads that row before
the complete Run validator; S3 reads directly and calls the same pure codecs,
not the existing repository's private validation/write methods.

1. **L01 — stored Run carriers.** After the section-3 step-1 selects/conversions,
   require the stored current Run identity to equal the requested `RunId`.
   Read the persisted triplet `current.binding_player_character_id`,
   `current.binding_contract_version`, `current.binding_record_revision`.
2. **L02 — reference selection.** If all three are `None`, perform no character
   lookup and supply `None` at L04; this is not legacy/native classification.
   The complete Run codec still rejects any other partial/lost binding evidence.
   If only some are `None`, raise S3-origin stored integrity with no cause.
   Otherwise require exact `str`, `str`, and non-Boolean `int`, respectively,
   with revision in `1..9223372036854775807`; physical failure is S3-origin
   stored integrity with no cause. In that order construct `PlayerCharacterId`,
   `PlayerCharacterContractVersion`, and `PlayerCharacterRevision`, then
   `ApplicableCharacterReference`, using their existing public constructors.
   Constructor `pydantic.ValidationError`, `TypeError`, or `ValueError` is
   wrapped once in S3 stored integrity with that exact exception as direct
   cause under section 9; there is no intermediate Run-storage wrapper.
3. **L03 — immutable prerequisite.** Select `player_character_revisions` by
   that persisted `(binding_player_character_id, binding_record_revision)`.
   A missing row raises S3-origin stored integrity with no cause. Convert its
   complete mapped values to `StoredPlayerCharacterRevisionRecord` and call
   `canonical_record_from_revision_storage`. Wrap its exact
   `PlayerCharacterStoredRecordIntegrityError` once directly in S3 stored
   integrity, preserving its nested cause. After successful decode require
   decoded ID, contract version, and revision to equal the L02 reference and
   lifecycle to be `active`; a crossed valid decoded reference or inactive
   lifecycle raises S3-origin stored integrity with no cause. A mismatch between
   the character row's own columns and canonical bytes instead fails inside
   the character codec and keeps that codec exception as direct cause.
4. **L04 — complete Run validation.** Call `validate_stored_run_record_set`
   once with the five original Run carrier inputs and the exact decoded
   object supplied as `referenced_player_character_revision=decoded_revision`
   (or `None` only for the all-absent triplet at L02). Its
   `RunStoredRecordIntegrityError` is wrapped once directly in S3 stored
   integrity. The unchanged validator retains its full history, binding,
   receipt, participation, and character-reference checks; none is skipped.

L01-L04 stop at their first failure. Thus malformed immutable bytes win before
a simultaneous Run-history mismatch; a valid matching immutable prerequisite
allows that mismatch to reach the unchanged Run validator. No current-character
or controller-row check, optional binding read, legacy proof, or N01-N15 work
precedes L04 success. Read failures at any select/result retrieval use the
repository exception and exact direct cause from section 9. All successful
objects are detached; no repair, write, retry, or caller authorization occurs.

### 3.1 Active player-character/controller stored-consistency algorithm

After L04 and legacy steps 2-5 establish the revision-3 binding and creation
evidence, reuse the immutable revision decoded at L03 without reloading it.
The repository now queries exactly: the `player_character_current` row by the
validated binding's `binding_player_character_id`; and the
`player_character_controller_bindings` row by the persisted controller value.
The controller query uses the L03 decoded revision's `controller_binding`, not
a request principal. The non-locking read uses plain `SELECT`. The locking read
applies `FOR UPDATE` in this exact order: `run_current`, the Run family in
section-3 step-1 order, the immutable revision at L03, then (only at this legacy
step) `player_character_current` and the controller-binding row. `FOR UPDATE`
is an exclusive row lock, including on the immutable revision; no shared-lock
syntax or later revision reload is implied.

Validation order is exact:

1. Reuse the L03 object already supplied to L04; its ID, contract version,
   revision, and active lifecycle have already matched the persisted reference
   and complete Run binding. Do not defer its first decode to this step.
2. Require `player_character_current` to exist. Decode it through
   `canonical_record_from_current_storage`; require exact equality with the
   immutable revision, which compares ID, contract version, record revision,
   controller binding, lifecycle, and canonical record bytes.
3. Require `run_current.active_player_character_id`,
   `run_current.binding_player_character_id`, both decoded character IDs, and
   `RunEntryCreationEvidence.player_character.player_character_id` to be the
   same value. Require the evidence pre-entry revision to equal the bound/current
   revision.
4. Require evidence `controller_operation.controller_binding`, immutable
   revision `controller_binding`, current row `controller_binding`, and the
   queried controller-binding primary key to be identical.

A missing immutable revision fails at L03; missing current/controller rows and
crossed current/evidence/controller comparisons fail here. Each S3-origin
check raises `RunProtocolBindingStoredIntegrityError` with `__cause__ is None`.
A player-character codec failure (revision at L03, current here) is wrapped in
that subtype with the exact `PlayerCharacterStoredRecordIntegrityError` as
direct cause. L02 constructor and L04 Run-codec causes remain those in 3.0.
No partial result is returned. These comparisons prove persisted consistency,
not that the controller belongs to the current request and not that any Session
player is named in creation evidence.

### 3.2 Private structural Session storage algorithm

S3 does not instantiate or call `SessionService`. The infrastructure adapter
queries exactly `game_sessions` by participation `session_id`, `domain_events`
by `(session_id, sequence_no = 1)`, and `game_snapshots` by `session_id`. The
locking classifier locks them after the character rows in table order
`game_sessions`, `domain_events`, `game_snapshots`; the non-locking classifier
uses plain reads. The private validator then performs these checks in order:

1. Require all three rows. Convert every mapped `game_sessions` column:
   `session_id`, `player_id`, `creation_client_request_id`,
   `character_definition_id`, `scenario_id`, `scenario_version`, `phase`,
   `turn_number`, `state_version`, `random_seed`, `created_at`, and `updated_at`.
   Require Session identity/player ID in their existing 1..64 opaque domains;
   scenario/character IDs in 1..128; scenario version in 1..32; phase as an
   exact 1..32 string; exact integers for nonnegative turn/state version and
   `random_seed` in `0..2^63-1`; the derived creation request as 64 lowercase
   hex; and exact UTC datetimes. `updated_at` and `random_seed` receive no
   controller, mode, ordering, or caller-authority meaning.
2. Require snapshot `state_version == game_sessions.state_version`; deep-copy
   `state_json`; require `schema_version == 3`; serialize with sorted keys,
   compact separators, UTF-8, and `allow_nan=False`; strict-decode `GameState`;
   and require `state.to_snapshot()` to equal the original JSON object.
3. Compare stored Session/snapshot values only: snapshot
   `state.player.player_id == game_sessions.player_id`; Session and snapshot
   scenario/content versions equal the evidence scenario; Session
   `character_definition_id` and snapshot character definition equal the
   evidence default definition. The Session player ID is never compared with a
   nonexistent creation-evidence field.
4. Convert all initialization-event columns `event_id`, `session_id`, `turn_id`,
   `sequence_no`, `event_type`, `payload_json`, and `occurred_at`, plus snapshot
   columns `session_id`, `state_version`, `state_json`, and `updated_at`, with
   exact stored types and UTC audit datetimes. Require participation, Session,
   event, and snapshot Session identities to agree; require the derived creation
   request ID; require event `turn_id = "session-created"`, `sequence_no = 1`,
   `event_type = "ScenarioStarted"`, payload exactly the evidence scenario ID
   and content version, and `occurred_at` equal the transaction time. Require
   Session `created_at` and participation `joined_at` to equal that time.
5. Require a scenario runtime with matching scenario ID/content version and
   exactly one matching player-memory scenario record with matching content
   version. When Session state version is zero, additionally require turn zero,
   phase `AWAITING_ACTION`, active ending status, STARTED memory with no ending,
   the STARTED milestone, and the exact event ID/sequence bindings already
   enforced by `SessionService.validate_run_entry_replay_initialization`.

Later domain events and the current mutable Session/snapshot state remain under
existing Session behavior; their existence does not change immutable sequence-1
entry proof. The algorithm grants no behavioral replay, caller ownership,
disclosure, recovery, or public access.

### 3.3 Caller-specific authority remains unchanged

`RunEntryService.enter` remains the sole owner of resolving the principal to a
controller, locking the currently owned active character through
`lock_owned_for_binding`, comparing replay evidence with the resolved
controller and request, loading the Session through
`get_owned_for_update(participation.session_id, principal.player_id)`, binding
an authorized replay result to that principal, applying request-specific
first-failure/disclosure behavior, and comparing persisted sources with its
configured `source_reference`. `SessionService` remains the owner of behavioral
Session validation and application replay semantics. S3 calls and duplicates
neither application authorization boundary. A classified legacy result is a
stored-family value only.

`scenario_id` remains scenario-definition identity only. Omission, `null`, a
missing binding row, request shape, model output, and decode failure never
select legacy. Legacy rows receive no synthesized protocol, profile,
authored-world, visit, region, Provider, or canon authority.

## 4. Exact stored-family classifier and first-failure order

The adapter uses this outer sequence, stopping at the first failure. Section 9
owns every exception crossing this boundary; lower Run/Session exceptions are
wrapped exactly once, never optionally passed through.

1. Validate requested `RunId` exact type/state before SQL. Read `run_current`.
   If missing, probe Run evidence tables and `run_protocol_bindings`: orphan
   evidence raises stored integrity; a genuinely absent Run returns `None`.
2. Execute section-3 step-1 row loading and L01-L04 exactly once: persisted
   reference selection, immutable revision load/decode/comparison, then complete
   strict Run validation with `referenced_player_character_revision` supplied.
   Do not first call the complete validator without its bound-Run prerequisite.
3. Read the optional binding by that Run ID. Evaluate the complete legacy proof
   in section-3 steps 2-9, 3.1, and 3.2, reusing the L03/L04 results. Missing
   legacy membership (for example a valid
   revision-1 native family without P8 receipts) means no legacy proof; corrupt
   existing legacy evidence fails immediately and is never ignored.
4. If a binding exists, execute N01-N15 below. N15 checks family exclusion
   before construction: both complete proofs raise `ContradictoryRunFamilyError`.
   Without a binding, complete legacy proof returns `LegacyRunCompatibilityV1`;
   incomplete proof raises `RunProtocolBindingStoredIntegrityError`. Absence
   never selects a mode. Native failure never falls back to legacy.

### 4.1 Single normative native order

Each numbered phase completes before the next begins. Within a phase visit
columns in section-5 order; objective order is columns 13-17. These are the
only native first-failure positions used by codecs, repositories, and vectors.

1. **N01 — object/column allowlist.** Require exact `RunProtocolBindingRow`
   (no subclass), the same loading Session, matching identity-map key, exactly
   all 19 loaded mapped columns and SQLAlchemy `_sa_instance_state` only; no
   missing/deferred/expired/extra/relationship-like state. Copy to the exact
   private frozen slotted `_StoredRunProtocolBindingV1` with those 19 fields. The no-I/O
   carrier reconstructor instead requires that exact carrier and field set.
2. **N02 — physical nonnumeric types.** Columns 1,2,4,5,7,10 are exact `str`;
   9,12,18 exact immutable `bytes`; 19 exact `datetime` in the MySQL-naive-UTC
   representation. No implicit decoding, coercion, descriptor access, or I/O.
3. **N03 — physical integer types.** Columns 3,6,8,11,13-17 require
   `type(value) is int`, rejecting `bool` and integer subclasses.
4. **N04 — lengths/ranges.** IDs are 1..128 ASCII bytes with the section-5
   grammar; discriminator 1..32 and epochs 1..64 ASCII bytes; revision and
   record versions 1..9223372036854775807; payloads 1..1024 bytes; objectives
   0..100 divisible by 5; fingerprint exactly 32 bytes; datetime in the MySQL
   year 1000..9999 domain, no timezone offset, exact microseconds. Reattach UTC
   only in the detached value. No selector literal is dispatched here.
5. **N05 — physical association.** Run ID equals requested and reconstructed
   Run; line matches; bound revision exists for that Run/line and equals the
   binding's reference. No character, Session, or caller authority is inferred.
6. **N06 — binding semantic dispatch.** Check discriminator, binding epoch,
   binding version, in that order, against the exact section-5 literals.
   A well-typed unsupported value raises the S3 unsupported subtype directly.
7. **N07 — S1 semantic dispatch.** Call public `decode_run_protocol_envelope`
   with stored envelope bytes and exact out-of-band envelope epoch/version.
   Its unsupported selector wins before its payload decoder, as frozen by S1.
8. **N08 — S1 canonical reconstruction.** The same S1 call fully decodes,
   validates the envelope/schema, and proves canonical byte-identical re-encode.
   Use the domain dispatcher directly, not the S1 storage wrapper; its owning
   S1 exception is the direct S3 cause. No S2 work precedes completion.
9. **N09 — authoritative profile.** Call `lookup_run_protocol_profile` with
   the validated envelope profile pair; reacquire the actual catalogue object.
10. **N10 — S2 semantic dispatch.** For unsupported out-of-band resolver
    epoch/version call public `resolve_run_protocol_objectives` with the valid
    envelope, an empty exact override proposal, and those stored selectors;
    its selector rejection occurs before proposal use. Supported selectors
    proceed to strict JSON decoding and the exact six-member allowlist, then
    check schema and embedded resolver version. Unsupported embedded version
    or schema raises `UnsupportedRunProtocolResolverVersionError` directly
    inside the private decoder, then the one S3 wrapper. Invalid JSON/shape
    raises `RunProtocolResolutionIntegrityError`; strict parser exceptions
    remain its cause. This necessary structural parse is not full input
    reconstruction. Physical S2 selector validation at N02/N03 is not dispatch.
11. **N11 — S2 canonical reconstruction.** Validate envelope hex equality;
    profile pair equality with S1 and catalogue; ordered exact override entries;
    construct public proposal/override/input carriers using public S2 APIs;
    require `encode_run_protocol_resolution_input_v1` byte equality; invoke
    `resolve_run_protocol_objectives` with the stored supported selectors.
    Noncanonical S2 bytes raise `RunProtocolResolutionIntegrityError` with
    `__cause__ is None` before the S3 wrapper. Public S2 functions retain their
    own internal validation order; S3 does not change or bypass that authority.
12. **N12 — objectives.** Compare the five stored scalars to the resolved
    values, in published order. Mismatch is S3-origin stored integrity.
13. **N13 — fingerprint.** Compare all raw 32 bytes with the resolved lowercase
    SHA-256 converted to bytes. Mismatch is S3-origin stored integrity.
14. **N14 — final cross-bound checks.** Require the reconstructed envelope,
    profile, override/input and resolved-result associations to agree with the
    validated stored Run/line/revision and all earlier compared values.
15. **N15 — trusted result.** The repository passes its fully validated legacy
    proof (or `None` if none was established) as a separate private context
    argument, never as a stored selector or caller authorization. Reject
    simultaneous complete legacy/native proofs;
    otherwise create one fresh detached `NativeRunProtocolBindingV1`. No
    partially reconstructed value escapes any earlier phase.

S3-origin physical, association, comparison, or completeness failures have
`__cause__ is None`. Lower codec failures have exactly the direct cause in
section 9. Wrong physical S2 selector types outrank S1 payload errors; well-typed
unsupported S2 selectors do not outrank S1 dispatch/decode. The following are
mandatory variations inside the named blocks, not additional vector blocks:

| Simultaneous corruptions | Winning phase / top-level exception / direct cause | Owning block |
| --- | --- | --- |
| S1 payload `b"{"`; resolver version 2 | N08 / stored integrity / `RunProtocolValidationError` | S3-V05 |
| Envelope version 2; resolver version 2 | N07 / stored integrity / `UnsupportedRunProtocolVersionError` | S3-V05 |
| Resolver version `"2"`; S1 payload `b"{"` | N03 / stored integrity / `None` | S3-V06 |
| Binding version 2; S1 payload `b"{"` | N06 / `UnsupportedRunProtocolBindingVersionError` / `None` | S3-V05 |
| Resource pressure 101; resolver version 2 | N04 / stored integrity / `None` | S3-V06 |
| Valid S1; resolver version 2 | N10 / stored integrity / `UnsupportedRunProtocolResolverVersionError` | S3-V06 |

No nullable-mode inference, repair, rewrite, fallback, caller authorization,
clock use, or write occurs during classification/reconstruction.

## 5. Exact MySQL 8 physical representation

S3 creates one separate table. It adds no column to `run_current` or
`run_revisions` because that would make absence tempt mode inference, duplicate
immutable history, and reserve S4/S7 state. The one-to-zero-or-one table makes
native state explicit while leaving every old row untouched.

Table: `run_protocol_bindings`, InnoDB, default charset `utf8mb4`, default
collation `utf8mb4_bin`. `_ascii_varchar` fields use `ascii`/`ascii_bin`.
Column order is normative:

| # | Column | MySQL type | Null/default | Authority and bound |
| ---: | --- | --- | --- | --- |
| 1 | `run_id` | `VARCHAR(128) CHARACTER SET ascii COLLATE ascii_bin` | NOT NULL; no server/application default; PK | exact `RunId` |
| 2 | `continuous_story_line_id` | same | NOT NULL; no default | exact owned line |
| 3 | `bound_state_version` | signed `BIGINT` | NOT NULL; no default | `1..9223372036854775807` |
| 4 | `family_discriminator` | ASCII `VARCHAR(32)` | NOT NULL; no default | exact `phase_3_3_native` |
| 5 | `binding_epoch` | ASCII `VARCHAR(64)` | NOT NULL; no default | exact `run-protocol-binding` |
| 6 | `binding_record_version` | signed `BIGINT` | NOT NULL; no default | exact `1` |
| 7 | `envelope_epoch` | ASCII `VARCHAR(64)` | NOT NULL; no default | exact S1 epoch |
| 8 | `envelope_record_version` | signed `BIGINT` | NOT NULL; no default | exact S1 version 1 |
| 9 | `envelope_canonical` | `BLOB` | NOT NULL; no default | 1..1024 bytes |
| 10 | `resolver_epoch` | ASCII `VARCHAR(64)` | NOT NULL; no default | exact S2 epoch |
| 11 | `resolver_record_version` | signed `BIGINT` | NOT NULL; no default | exact S2 version 1 |
| 12 | `resolution_input_canonical` | `BLOB` | NOT NULL; no default | 1..1024 bytes |
| 13 | `resource_pressure` | `SMALLINT UNSIGNED` | NOT NULL; no default | 0..100, step 5 |
| 14 | `social_trust` | `SMALLINT UNSIGNED` | NOT NULL; no default | 0..100, step 5 |
| 15 | `consequence_severity` | `SMALLINT UNSIGNED` | NOT NULL; no default | 0..100, step 5 |
| 16 | `information_opacity` | `SMALLINT UNSIGNED` | NOT NULL; no default | 0..100, step 5 |
| 17 | `conflict_intensity` | `SMALLINT UNSIGNED` | NOT NULL; no default | 0..100, step 5 |
| 18 | `resolution_fingerprint` | `BINARY(32)` | NOT NULL; no default | decoded lowercase S2 SHA-256 |
| 19 | `created_at` | `DATETIME(6)` | NOT NULL; no default | trusted caller/UoW time; immutable audit only |

Primary key: explicit
`PrimaryKeyConstraint("run_id", name="pk_run_protocol_bindings")`. Foreign key
`fk_run_protocol_bindings_revision(run_id, continuous_story_line_id, bound_state_version)`
references
`run_revisions(run_id, continuous_story_line_id, state_version)` with
`ON DELETE RESTRICT ON UPDATE RESTRICT`. Explicit supporting index
`ix_run_protocol_bindings_revision` uses those three columns in that order.
There is no other unique constraint: the primary key enforces one binding per
Run, while the referenced Run schema already fixes one line per Run.

Named checks and exact SQL expressions:

- `ck_run_protocol_bindings_identity_version`:
  `CHAR_LENGTH(run_id) >= 1 AND run_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' AND CHAR_LENGTH(continuous_story_line_id) >= 1 AND continuous_story_line_id REGEXP '^[A-Za-z0-9][A-Za-z0-9_.:-]*$' AND bound_state_version BETWEEN 1 AND 9223372036854775807`;
- `ck_run_protocol_bindings_discriminators`:
  `family_discriminator = 'phase_3_3_native' AND binding_epoch = 'run-protocol-binding' AND binding_record_version = 1 AND envelope_epoch = 'run-protocol-envelope' AND envelope_record_version = 1 AND resolver_epoch = 'run-protocol-resolution' AND resolver_record_version = 1`;
- `ck_run_protocol_bindings_payload_sizes`:
  `OCTET_LENGTH(envelope_canonical) BETWEEN 1 AND 1024 AND OCTET_LENGTH(resolution_input_canonical) BETWEEN 1 AND 1024 AND OCTET_LENGTH(resolution_fingerprint) = 32`; and
- `ck_run_protocol_bindings_objectives`:
  `resource_pressure BETWEEN 0 AND 100 AND MOD(resource_pressure, 5) = 0 AND social_trust BETWEEN 0 AND 100 AND MOD(social_trust, 5) = 0 AND consequence_severity BETWEEN 0 AND 100 AND MOD(consequence_severity, 5) = 0 AND information_opacity BETWEEN 0 AND 100 AND MOD(information_opacity, 5) = 0 AND conflict_intensity BETWEEN 0 AND 100 AND MOD(conflict_intensity, 5) = 0`.

There is no database-generated timestamp, application default, nullable
selector, mutable `updated_at`, binding CAS column, delete cascade, or ORM
cascade. The schema exposes physical primary/foreign/check integrity; S3
production code never inserts, updates, or deletes a binding. Future S4 owns
the first production insert, its enclosing Run CAS/admission sequence, and its
conflict contract; S3 does not select or pre-authorize them.

## 6. Persisted protocol/profile state and reconstruction

Persisted exactly: binding discriminator/epoch/version; S1 envelope
epoch/version and exact canonical bytes; S2 resolver epoch/version and exact
canonical resolution-input bytes; the five final numeric objectives; the S2
fingerprint as 32 raw bytes; Run/line/bound revision; and creation audit time.

Reconstructed, not separately stored: S1 schema literal; profile ID and
profile version; S2 schema literal; authorized override presence/values; the
authoritative catalogue profile object; and all S2 carrier objects. Those
values already exist in the canonical bytes and are deliberately not a second
authority. S3 adds no evidence namespace beyond exact
`run-protocol-binding`/version 1 and the explicit native discriminator.

| Value | Test-local setup/schema evidence | Production read validator / consistency | Corruption outcome |
| --- | --- | --- | --- |
| Envelope selectors/bytes | fixture supplies S1 output; checks enforce 1..1024 | S1 dispatcher, byte-identical re-encode, schema cross-check | S3 stored-integrity wrapper with direct S1 cause |
| Resolver selectors/input bytes | fixture supplies S2 output; checks enforce 1..1024 | N09 authoritative lookup, N10 private strict six-field decoder, N11 public S2 re-encode | S3 stored-integrity wrapper with direct S2 cause |
| Profile ID/version | exact S1 envelope supplied by fixture | equal in envelope, S2 canonical input, override set, and catalogue identity | stored-integrity failure |
| Final objectives | exact five S2 values supplied by fixture | value equality with newly rerun S2 result; object identity is not required | stored-integrity failure |
| Fingerprint | fixture converts exact lowercase S2 hex to 32 bytes | byte equality with rerun S2 fingerprint; storage round trip returns lowercase hex | stored-integrity failure |
| Run/line/revision | existing test-owned Run rows plus direct binding row | value equality and FK association | stored-integrity failure |
| `created_at` | fixture supplies exact UTC microsecond value in MySQL representation | attach UTC on read and require exact microsecond round-trip; it grants no ordering or mode authority | stored-integrity failure |

Canonical encodings and maxima remain the published S1/S2 1,024-byte limits;
no new decoder is added to S1 or S2. The S3 private S2 decoder accepts only the
published six-field compact sorted JSON grammar—`authorized_overrides`,
`authorized_profile_id`, `authorized_profile_version`,
`canonical_envelope_hex`, `resolver_version`, and `schema` are the exact
semantic values, with `authorized_overrides` being the sole nested array—exact
override order and types, lowercase envelope hex, strict UTF-8/no BOM/no
duplicate/extra/missing
members, and byte-identical S2 re-encoding. It is not exported and has no
fallback, correction, proof, or catalogue-copy helper.

## 7. S3/S4 ownership reconciliation

S3 production code is read-only with respect to native protocol bindings. It
establishes the table, immutable result carriers, strict stored-family
classifier/reconstructor, two Repository read methods, UoW exposure, migration,
and verification. It has no native-binding add/insert/write/stage method,
hidden writer, test writer, sentinel authority, importable row-creation
capability, insertion-conflict translation, admission command/service, or
test-row factory.

P3.3-S4 exclusively owns the first production native-binding write method,
production insert-conflict translation, atomic admission evidence,
entry-world binding, and every operation-specific replay/conflict contract for
admission. S4 must separately plan and review those capabilities. The S3 table
and read adapters neither authorize nor imply them.

Future S3 integration tests create native rows only in
`tests/integration/test_mysql_run_protocol_binding.py`, through this exact
test-local helper in that file:

```python
async def _add_native_binding_row(
    session: AsyncSession,
    *,
    run_id: str,
    continuous_story_line_id: str,
    bound_state_version: int,
    family_discriminator: str,
    binding_epoch: str,
    binding_record_version: int,
    envelope_epoch: str,
    envelope_record_version: int,
    envelope_canonical: bytes,
    resolver_epoch: str,
    resolver_record_version: int,
    resolution_input_canonical: bytes,
    resource_pressure: int,
    social_trust: int,
    consequence_severity: int,
    information_opacity: int,
    conflict_intensity: int,
    resolution_fingerprint: bytes,
    created_at: datetime,
    flush: bool,
) -> RunProtocolBindingRow: ...
```

The helper receives the test-owned `AsyncSession`, constructs exactly one
`RunProtocolBindingRow` from those 19 values, calls `session.add(row)` directly,
and awaits `session.flush()` only when `flush=True` is required by that test. It
never commits, calls no production admission/repository writer, constructs no
entry-world state, and returns no authority. Its test-owned UoW/session fixture
retains commit/rollback ownership and always rolls back and restores all test
state during cleanup. No production test-utility module exists.

## 8. Domain, ORM, Repository, and UoW contract

New `domain.run_protocol_binding` owns:

- constants `RUN_PROTOCOL_BINDING_EPOCH = "run-protocol-binding"`,
  `RUN_PROTOCOL_BINDING_V1_VERSION = 1`, and
  `RUN_FAMILY_NATIVE_V1 = "phase_3_3_native"`;
- frozen `LegacyRunCompatibilityV1(canonical_run: CanonicalRun,
  session_id: str)`; and
- frozen `NativeRunProtocolBindingV1(run_id, continuous_story_line_id,
  bound_state_version, resolved_protocol)` with complete original-state and
  cross-binding validation.

The union alias is private; no package re-export is added.

New ORM model
`deviation_protocol.infrastructure.orm_models.RunProtocolBindingRow` maps the
19 columns above. It declares no SQLAlchemy relationship in either direction,
uses no lazy/eager loader, and has no cascade. Repository selects are explicit.
SQLAlchemy construction and the identity map grant no trust. Every row is
copied field-for-field into a frozen slotted stored carrier in new
`infrastructure.run_protocol_binding_persistence`, then strictly reconstructed.
Deferred, missing, expired, cross-Session, wrong-identity, or unexpected ORM
state fails before trusted use.

New read-only application port in `application.ports`:

```python
class RunProtocolBindingRepository(ABC):
    async def get_classified(
        self, *, run_id: RunId
    ) -> LegacyRunCompatibilityV1 | NativeRunProtocolBindingV1 | None: ...

    async def get_classified_for_update(
        self, *, run_id: RunId
    ) -> LegacyRunCompatibilityV1 | NativeRunProtocolBindingV1 | None: ...
```

The concrete
`SqlAlchemyRunProtocolBindingRepository(session: AsyncSession)` implements only
those two methods. `get_classified` performs read-only selects and executes
L01-L04 before legacy/native proof: persisted reference, decoded immutable
revision, then complete Run validator with its exact required keyword input.
The locking form locks the exact rows and order frozen in sections 3.0, 3.1,
and 3.2 and never holds a lock across external work. A genuinely absent Run
returns `None`; an incomplete
existing family raises stored integrity. SQLAlchemy/driver failures from those
reads become `RunProtocolBindingRepositoryError` with the original exception as
direct cause. S3 adds no update CAS and preserves the existing Run repository's
row-count CAS behavior without invoking it.

`UnitOfWork` gains attribute
`run_protocol_bindings: RunProtocolBindingRepository`.
`SqlAlchemyUnitOfWork.__aenter__` constructs the concrete adapter over the same
`AsyncSession`. Entry remains lazy; repositories never commit; explicit future
application operations own one transaction. Exceptional exit, cancellation,
flush failure, and uncommitted normal exit roll back and close. No package
`__init__.py` export is allowed.

`RunProtocolBindingRow` has ordinary infrastructure-module visibility because
SQLAlchemy metadata and the migration tests require it; S3 production code only
loads it. The one authorized test-local helper constructs it directly. Loaded
instances may share SQLAlchemy identity within one session; each successful read
still returns a freshly validated detached domain value. S3 never mutates or
deletes rows. Row conversion permits SQLAlchemy's exact `_sa_instance_state`
bookkeeping only; every other non-mapped instance attribute, missing mapped
attribute, and relationship-like injected state is stored corruption.

## 9. Exception taxonomy and exact boundary ownership

Exactly four S3 exception classes live in
`infrastructure.run_protocol_binding_persistence`, visible from that module
only; none is exported by `application.ports` or any package `__init__.py`.
Migration failures use built-in `RuntimeError` instances local to the migration
(section 10); they add no fifth S3 exception class.

In the lower-boundary table, "stored integrity" means exactly
`RunProtocolBindingStoredIntegrityError` and "repository error" means exactly
`RunProtocolBindingRepositoryError`; neither is an alternative type choice.

| Exact class and inheritance | Creation boundary / semantic ownership | Direct-cause rule | Pass-through exclusions / first failure / vectors |
| --- | --- | --- | --- |
| `RunProtocolBindingStoredIntegrityError(ValueError)` | S3 stored classifier/converter/reconstructor; malformed or incomplete persisted evidence | exact caught lower exception on one wrapper; `None` for S3-origin checks | never leak lower stored-integrity failures; already-created S3 instances pass unchanged; outer 1-4 then N01-N15; V01-A, V03, V05-V13, V15-V17, V19-V21-B, V28, V35 |
| `UnsupportedRunProtocolBindingVersionError(RunProtocolBindingStoredIntegrityError)` | only N06, unsupported discriminator/binding epoch/version | `None` | no S1/S2 selector ownership, no rewrap; V04, V05 variation, V18 |
| `ContradictoryRunFamilyError(RunProtocolBindingStoredIntegrityError)` | only N15, two complete proofs | `None` | no partial proof or invalid-native translation, no rewrap; V14 |
| `RunProtocolBindingRepositoryError(RuntimeError)` | SQL read execution/result retrieval, before interpreting rows | original SQLAlchemy exception, or original unwrapped driver exception | no codec/structural/cancellation/UoW translation; pass existing S3 instance unchanged; first failing read at its actual outer/legacy/native position; V01-A read-failure variations |

For every S3 wrapping action below, `top.__cause__ is lower`, preserving the exact
lower object and its existing nested chain; the lower exception is directly
accessible. Never unwrap an existing lower storage wrapper to choose its nested
cause. Every pass-through keeps object identity and its existing `__cause__`
unchanged. Retry by this repository is prohibited on every row. The right-hand
vector owns mandatory exception variations within its one counted block.

| Lower exception/outcome at S3 boundary | One exact action / top-level type | Exact cause and accessibility | First-failure position / vector |
| --- | --- | --- | --- |
| `RunStoredRecordIntegrityError` | wrap once / `RunProtocolBindingStoredIntegrityError` | lower directly | outer 2 L04 after immutable prerequisite, or legacy receipt codec / V13 |
| `PlayerCharacterStoredRecordIntegrityError` | wrap once / stored integrity | lower directly; no intermediate Run wrapper | outer 2 L03 immutable codec, then later legacy 3.1 current codec / V13 |
| `pydantic.ValidationError`, `TypeError`, or `ValueError` from L02 persisted-reference constructors | wrap once / stored integrity | exact constructor exception directly; no intermediate Run wrapper | outer 2 L02, before immutable SELECT / V13 |
| `pydantic.ValidationError` from Session `GameState` or stored carrier construction | wrap once / stored integrity | lower directly | legacy 3.2 or native constructor phase / V01-A, V09 |
| `DomainRuleViolation` from strict Session state reconstruction | wrap once / stored integrity | lower directly | legacy 3.2 step 2 / V01-A |
| `TypeError` from stored-only validators | wrap once / stored integrity | lower directly | actual owning legacy/native phase / V01-A, V09 |
| `ValueError` from stored-only validators, excluding all named subclasses handled here | wrap once / stored integrity | lower directly | actual owning phase / V01-A, V09 |
| `AttributeError` from an invoked stored codec | wrap once / stored integrity | lower directly | actual owning codec / V13 |
| `RunProtocolValidationError` (excluding its unsupported subtype) | wrap once / stored integrity | lower directly | N08 or nested public S2 S1 validation / V05, V07 |
| `UnsupportedRunProtocolVersionError` | wrap once / stored integrity | lower directly | N07 / V05 |
| `RunProtocolStoredRecordIntegrityError` if supplied by a lower storage conversion | wrap once / stored integrity | storage wrapper directly, its S1 cause remains nested | N07/N08 injected boundary propagation only; normal algorithm calls domain dispatcher / V07 |
| `RunProtocolResolutionError` base instance | wrap once / stored integrity | lower directly | public S2 call at N09-N11 / V09 |
| `RunProtocolProfileLookupError` | wrap once / stored integrity | lower directly | N09 / V08 |
| `UnsupportedRunProtocolResolverVersionError` | wrap once / stored integrity | lower directly | N10 / V06 |
| `RunProtocolOverrideValidationError` | wrap once / stored integrity | lower directly | N11 / V09 |
| `RunProtocolResolutionIntegrityError` | wrap once / stored integrity | lower directly | N09 catalogue, N10 JSON, N11 input/resolution / V09, V35-A |
| `UnicodeDecodeError` or `json.JSONDecodeError` from private S2 parser | wrap once in `RunProtocolResolutionIntegrityError` at N10, then that named lower error is wrapped once at S3 / stored integrity | direct S2 error; parser object at `top.__cause__.__cause__` | N10 / V35-A |
| `sqlalchemy.exc.SQLAlchemyError`, including `DBAPIError`, `DatabaseError`, `OperationalError`, `InterfaceError`, `IntegrityError`, `ProgrammingError`, `DataError`, `InternalError`, `NotSupportedError`, `StatementError`, `InvalidRequestError` and `TimeoutError` from reads | wrap once / `RunProtocolBindingRepositoryError` | exact SQLAlchemy object directly; its driver `orig` stays intact | first failing select/result retrieval / V01-A |
| `asyncmy.errors.Error`, including `InterfaceError`, `DatabaseError`, `OperationalError`, `IntegrityError`, `ProgrammingError`, `DataError`, `InternalError`, `NotSupportedError` escaping without SQLAlchemy wrapping | wrap once / repository error | driver object directly | first failing read / V01-A |
| Any of the four already-created S3 exceptions | pass through unchanged / same exact subtype | existing cause unchanged and accessible; never self-chain | original phase wins / V01-A, V04, V14 |
| Genuine missing Run (no evidence anywhere) | return `None` | no exception/cause | outer 1 / V15 |
| Missing current with orphan evidence; missing required Run/character/Session/event/snapshot row; missing binding and incomplete legacy | create stored integrity directly | `None`, no invented lower exception | first required-row check; immutable character at L03 before L04, current/controller later at 3.1 / V15, V01-A, V13 |
| L01 identity mismatch; L02 partial triplet or physical type/range failure; L03 decoded-reference/lifecycle mismatch after successful codec | create stored integrity directly | `None`; column/canonical mismatch inside the character codec instead follows its named lower-exception row | outer 2 L01/L02/L03, before complete Run validation / V13 |
| S3 classifier-origin structural/type/range/association/comparison failure | create stored integrity directly | `None` | exact outer or N phase / V10-V12, V16-V21-B, V28, V35-B |
| Unsupported S3 selector; both complete families | create exact subtype from first table | `None` | N06 / V04, V18; N15 / V14 |
| Invalid caller `RunId` or closed signature | pass unchanged / `TypeError`; invalid exact RunId state retains owning `ValueError` or `pydantic.ValidationError` | existing cause unchanged; no SQL | outer 1 / V34, V36 |
| `asyncio.CancelledError`, `KeyboardInterrupt`, `SystemExit` | pass unchanged / original exact type | existing cause unchanged | point of interruption / V27; boundary interruption variations in V01-A |
| UoW commit/rollback/close exception | outside S3 classification; pass unchanged at UoW owner | original cause unchanged | UoW exit; existing `tests/unit/test_repository_and_uow.py` regression |

Session application exceptions `SnapshotNotFoundError`,
`SnapshotInvalidError`, `SnapshotSchemaVersionMismatchError`,
`SnapshotStateVersionMismatchError`, `SnapshotSessionMismatchError`, and
`SnapshotContentVersionMismatchError` are not emitted by S3: `SessionService`
is neither called nor duplicated. S3's private structural checks create stored
integrity with no cause; underlying `GameState` validation uses the rows above.
If one of these six exceptions is injected at a lower stored-validator seam,
the single defensive boundary rule is to wrap it once in stored integrity with
that exact object as direct cause (V01-A), never pass it through. Existing
`RunRepositoryError`/`RunRepositoryConflictError` and application write-conflict
exceptions are unreachable: the adapter reads rows directly and invokes only
the pure Run codec, never an existing repository write/CAS or Session service.

Direct callers of S1/S2 outside S3 retain their published exceptions. This
does not create a second outcome for stored reconstruction. Scope catches to
the specified codec/read call, handle named subclasses before base classes,
and propagate unexpected programming errors unchanged; no blanket repair or
success conversion is permitted. Every variation asserts identity of the
direct cause, no later phase, no retry, no mutation, and no partial result.

Physical insertion evidence is test-only: duplicate-PK flush raises
`sqlalchemy.exc.IntegrityError` with `asyncmy.errors.IntegrityError` numeric
1062 as driver cause/`orig`. Assert family and numeric code, never key-name or
localized message. Roll back the failed transaction; no S3 production 1062
translation exists. Existing Run CAS remains its original `False` result.

## 10. Migration freeze

Current metadata-only Alembic head is independently verified as
`20260729_0005`. The exact next revision is:

- revision ID: `20260828_0006`;
- `down_revision`: `20260729_0005`;
- filename:
  `alembic/versions/20260828_0006_run_protocol_bindings.py`;
- description: `add native run protocol binding persistence`.

Upgrade order: create the table with columns and named checks; create
`ix_run_protocol_bindings_revision`; then add
`fk_run_protocol_bindings_revision`. This matches the repository convention of
declaring child indexes before foreign keys and avoids MySQL-created hidden
indexes. The operation is additive DDL: it may take metadata locks but performs
no `SELECT`/copy/backfill/update of old application rows. Old table bytes and
row counts remain identical.

The exact Alembic calls are one `op.create_table` with the 19 columns in table
order, the named primary key and four named checks, plus
`mysql_engine="InnoDB"`, `mysql_charset="utf8mb4"`, and
`mysql_collate="utf8mb4_bin"`; one `op.create_index` for the exact non-unique
three-column index; and one `op.create_foreign_key` with the exact local/remote
column order and `RESTRICT` actions. There is no implicit unique constraint,
trigger, generated column, DML, or server default.

Downgrade uses one mandatory MySQL 8 connection-owned named advisory lock. The
exact lock identity is
`deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1` (60 ASCII bytes).
The Alembic connection returned by `op.get_bind()` owns the lock and all probe/
DDL statements. Before the empty probe it executes exactly:

```sql
SELECT GET_LOCK(
  'deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1',
  30
)
```

### 10.1 Exact migration-local errors and cleanup vocabulary

The timeout is exactly 30 seconds. Only `type(result) is int and result == 1`
enters the protected body. No acquisition branch is retried automatically.
All migration-created failures have exact type built-in `RuntimeError`, not a
new S3 class, and exact message `P3.3-S3 downgrade <CODE>` with the code below.
Raise it from the specified direct cause; `None` means explicit `from None`.
Original non-disconnect probe/DDL exceptions retain identity and their original
cause. Data refusal remains exactly
`RuntimeError("Refusing to downgrade P3.3-S3: native Run Protocol binding data exists; recovery must be forward-only")`
with no cause.

Capture the owning MySQL `CONNECTION_ID()` before attempting the lock. A
preflight failure uses acquisition-before loss below; failure of this read
without disconnect uses `ACQUIRE_STATEMENT_FAILED` with that exact exception.
Loss means SQLAlchemy `DBAPIError.connection_invalidated`, an already
invalidated/closed connection, or a driver disconnect reported by that owning
connection. A live-looking connection is not proof of liveness: if loss is
discovered by the next statement, classify at that statement. Never reconnect
or let `op.get_bind()` switch connections during this attempt.

Cleanup **C0**: no ownership obtained; assert no probe/DDL/release, unchanged
schema/data, and no lock owned by this connection (a competing holder is
allowed). **C1**: confirmed explicit release; assert this owner no longer owns
the lock, plus exact schema/data and stopped-statement trace. **CL**: invalidate
and physically discard/close the owning DBAPI connection (not merely return it
to a pool); MySQL automatically releases a named lock when that server session
terminates, not when a transaction rolls back or DDL commits. Loss detection
does not prove termination has already happened. A separate real-MySQL observer
must see `IS_USED_LOCK(name)` no longer equal the old connection ID, and after
all test holders finish `IS_FREE_LOCK(name) = 1`. Use a five-second bounded
observer wait after explicit server-side termination/confirmed disconnect;
timeout fails the test and never means successful downgrade. Inspect schema
and revision on the observer; do not assume DDL rollback. All fixture recovery
occurs after the failure is asserted and outside the failed migration attempt.

### 10.2 Acquisition matrix

Every failure aborts migration, returns no success, permits no probe or DDL,
and attempts no `RELEASE_LOCK`; acquisition success is the sole exception.
`e` below is the exact observed SQLAlchemy/driver exception, including its
existing nested cause; if loss was detected solely by connection state there
is no exception and the direct cause is `None`.

| Outcome | Acquired? | Exact result/error code / direct cause | Release / probe / DDL | Invalidation / cleanup | Proof block |
| --- | --- | --- | --- | --- | --- |
| Integer 1 | yes, confirmed | continue / no exception | release after body; probe yes; DDL only after empty probe | keep valid / C1 or later CL | V30-A |
| Integer 0 | no, timeout | `ACQUIRE_TIMEOUT` / `None` | no / no / no | remains valid / C0 | V31-D |
| SQL NULL | no grant confirmed; treat as acquisition error | `ACQUIRE_NULL` / `None` | no / no / no | conservatively invalidate / CL | V31-D |
| Statement raises without disconnect | unknown, no grant confirmed | `ACQUIRE_STATEMENT_FAILED` / exact `e` | no / no / no | invalidate to eliminate possible ownership / CL | V31-D |
| Lost before acquisition statement | no attempt, no acquisition | `ACQUIRE_CONNECTION_LOST_BEFORE` / `e` or `None` as defined above | no / no / no | invalidated / CL; C0 statement trace | V31-D |
| Lost while acquisition pending | ownership uncertain; server could have granted | `ACQUIRE_CONNECTION_LOST_PENDING` / `e` | no / no / no | invalidated / CL | V31-D |
| Lost immediately after return 1 | acquired, then session loss | `ACQUIRE_CONNECTION_LOST_AFTER` / `e` or `None` | no / no / no | invalidated / CL | V31-D |

Any other physical return, including Boolean true, is
`ACQUIRE_INVALID_RESULT` with no cause, no body or release, invalidation and CL;
its defensive variation belongs to V31-D. Acquisition-after means loss detected
before entering the protected body. Once the body is entered, use 10.3.

### 10.3 Protected body and connection-loss matrix

At downgrade entry, retain any already-active transaction on the exact
`op.get_bind()` connection, including an established REPEATABLE READ snapshot.
If no transaction is active, call that connection's `begin()` before the
connection-ID preflight and acquisition; use normal transactional execution,
not DBAPI autocommit. Do not commit, roll back, change isolation, start a nested
transaction, or replace the connection to refresh a snapshot. After acquisition
returns exact integer 1, in that same transaction and on that same physical
lock-owning connection, execute exactly:

```sql
SELECT 1 FROM run_protocol_bindings LIMIT 1 FOR UPDATE
```

This is an InnoDB current/locking read, not a consistent snapshot read. It sees
committed bindings even when they postdate a consistent-read snapshot already
established on this connection. Acquiring the named lock does not refresh that
snapshot; the locking read is the required visibility mechanism. No plain
snapshot SELECT, cached empty result, or read on another connection substitutes
for this probe. A visible row causes the exact no-cause data refusal before
every destructive DDL statement. An empty result permits exactly:
`op.drop_constraint("fk_run_protocol_bindings_revision", "run_protocol_bindings", type_="foreignkey")`,
`op.drop_index("ix_run_protocol_bindings_revision", table_name="run_protocol_bindings")`,
then `op.drop_table("run_protocol_bindings")`. No later statement runs after
any failure. DDL implicit commits end transactional row/gap locks but do not
release the connection-owned named lock. It remains held throughout the current
probe and all three DDL statements, excluding compliant writers even across
those commits. This advisory protocol does not exclude arbitrary SQL writers
that do not acquire the same lock. After refusal or a pre-DDL failure, checked
named-lock cleanup follows 10.4, then the migration caller rolls back/closes the
remaining transaction before returning the connection to a pool; it must not
leave probe row/gap locks behind. That rollback is not named-lock release and
never replaces the saved primary error. No destructive DDL follows refusal.

| Loss point | Primary RuntimeError code / exact direct cause | Database knowledge / later DDL | Release and final failure / real-MySQL proof |
| --- | --- | --- | --- |
| Before probe, body entered | `BODY_CONNECTION_LOST_BEFORE_PROBE` / `e` or `None` | unchanged schema/data; no probe or DDL | no explicit release on dead connection; invalidate, automatic server release on termination, CL; migration failed / V30-C |
| During probe | `BODY_CONNECTION_LOST_PROBE` / `e` | probe answer unknown, no destructive DDL issued; schema/data unchanged | no explicit release; invalidate, automatic release, CL; migration failed / V30-C |
| After empty result, before DDL | `BODY_CONNECTION_LOST_BEFORE_DDL` / `e` or `None` | table known present at last confirmed response; no DDL issued; never reuse emptiness on another connection | no explicit release; invalidate, automatic release, CL; migration failed / V30-D1 |
| State detected after acknowledged FK removal, before issuing index removal | `BODY_CONNECTION_LOST_BEFORE_INDEX` / `None` | FK removal committed; table, supporting index, PK and four checks remain, zero binding rows; index/table removal must never be issued | no explicit release; invalidate/discard, CL and 10.4 saved-primary precedence; independently inspect/restore partial schema / V30-D2(c) |
| State detected after acknowledged index removal, before issuing table removal | `BODY_CONNECTION_LOST_BEFORE_TABLE` / `None` | FK and supporting index removals committed; table, PK and four checks remain, zero binding rows; table removal must never be issued | no explicit release; invalidate/discard, CL and 10.4 saved-primary precedence; independently inspect/restore partial schema / V30-D3(c) |
| During FK/index/table destructive DDL | `BODY_CONNECTION_LOST_DDL_FK` / `e`, `BODY_CONNECTION_LOST_DDL_INDEX` / `e`, or `BODY_CONNECTION_LOST_DDL_TABLE` / `e` | current DDL outcome uncertain; earlier acknowledged DDL committed; later DDL prohibited | no explicit release; invalidate, automatic release, CL; inspect exact resulting partial schema; migration failed / V30-D1, D2, D3 respectively |
| After acknowledged table removal, before explicit release | `BODY_CONNECTION_LOST_AFTER_TABLE` / `e` or `None` | table removal known committed, migration revision not claimed; later DDL prohibited | no explicit release; invalidate, automatic release, CL; migration failed despite completed DDL / V30-E |

The last row is detected while still in body completion. Loss first detected
in cleanup follows the release matrix. An unobserved break between statements
is diagnosed when the next actual statement fails; tests freeze the detection
point explicitly. No connection-loss branch claims successful downgrade.

After each acknowledged DDL call returns and immediately before the next DDL
call, inspect the owning connection's closed/invalidated state without SQL.
The two between-statement rows apply when that state check detects loss with
no observed underlying exception: raise the specified built-in RuntimeError
`from None`, not a fabricated DBAPI exception or the next statement's loss
code. With no such state indication, a subsequent issued statement that raises
a disconnect uses the corresponding during-DDL row and exact observed cause;
its outcome is uncertain, unlike an unissued statement. Never reconnect and
continue DDL or claim a revision downgrade after either state-only failure.
Cleanup records `RuntimeError("P3.3-S3 downgrade RELEASE_CONNECTION_LOST_BEFORE")`
with no cause in `primary.cleanup_error`, re-raises the identical primary with
no cause, and invalidates/physically discards the owner. Discard errors follow
10.4 and cannot replace that primary. Client-side state detection alone does
not prove immediate server-side lock release; require the separate CL observer
evidence after confirmed session termination. The observer inspects the known
partial schema and unchanged revision before any fixture restoration; only
then may the test fixture rebuild it outside the failed migration attempt.

### 10.4 Release matrix and exact primary-error precedence

After confirmed acquisition, execute exactly
`SELECT RELEASE_LOCK('deviation_protocol:p33:s3:run_protocol_bindings:ddl_write:v1')`
once if that same connection remains valid. A finally cleanup records, rather
than immediately raises, its error. Never issue release after invalidation and
never reacquire/reconnect to release. Only exact integer 1 confirms release.

| Outcome | Cleanup result/error code / direct cause | Automatic release relied on? | Body status / assertion / proof block |
| --- | --- | --- | --- |
| Integer 1 | no cleanup error | no | prior body result unchanged; successful body permits migration success; C1 / V30-A and V30-C/D |
| Integer 0 | `RELEASE_NOT_OWNER` / `None` | yes, conservative discard | acknowledged DDL facts remain known, overall migration fails; CL / V30-E |
| SQL NULL | `RELEASE_NULL` / `None` | yes, conservative discard | acknowledged DDL facts known, overall migration fails; CL / V30-E |
| Statement raises, no disconnect | `RELEASE_STATEMENT_FAILED` / exact `e` | yes, force discard | lock release uncertain; body facts retained but migration fails; CL / V30-E |
| Already invalidated/lost at cleanup entry | `RELEASE_CONNECTION_LOST_BEFORE` / observed `e` or `None` | yes, on server termination | no explicit SQL; body facts retained, no successful migration; CL / V30-E |
| Connection lost while release pending | `RELEASE_CONNECTION_LOST_PENDING` / exact `e` | yes, on server termination | release acknowledgement uncertain; completed DDL remains committed, migration fails; CL / V30-E |

Other physical release returns use `RELEASE_INVALID_RESULT` with no cause and
CL (V30-E). Freeze precedence as this one algorithm:

1. Save any body exception as `primary` with its exact original traceback and
   direct cause. Disconnect creates the matching body RuntimeError above.
2. Perform the one eligible release; capture its exact cleanup RuntimeError as
   `cleanup_error`. Invalidated/lost connection produces the before-release
   cleanup error without SQL, with cause equal to the same observed loss object
   used by the primary, or `None` if state-only detection. Invalidate/discard
   whenever cleanup failed or connection loss occurred.
3. If `primary` exists, attach `primary.cleanup_error = cleanup_error`
   (exact cleanup object, or `None`), then re-raise the identical primary with
   unchanged `__cause__`. Never raise cleanup from primary or replace primary.
4. Without a primary, raise cleanup if present, using its own exact direct
   cause. Without either error, and only after release 1, return success.

Thus body success/release failure raises cleanup; body failure/release success
raises original body; both failures raise original body with separately
accessible cleanup; body disconnect raises its loss primary and prohibits
release SQL; DDL success followed by lost release confirmation always fails.
Physical discard failure is recorded as `cleanup_error.close_error` (or
`primary.close_error` if no cleanup error exists), never replaces either
selected error, never permits success, and requires operator/fixture-confirmed
server termination. No arbitrary blanket exception catch converts cancellation
or process-control exceptions to success; preserve those original primaries
while doing eligible cleanup with the same precedence.

### 10.5 Downgrade decision matrix and cooperative writers

| Condition | Frozen outcome |
| --- | --- |
| Committed native data, including commits newer than an established snapshot | acquisition 1; current/locking probe row; exact data-refusal primary; cleanup according to 10.4; no DDL, data preserved |
| Empty/no writer | acquisition 1; empty probe; ordered FK/index/table DDL; release 1; only then success permitting revision `20260729_0005` |
| Writer holds lock beyond 30 seconds | acquisition timeout branch, zero body/release; holder unaffected |
| Writer commits then releases within timeout | acquire next in the existing transaction, current/locking read observes row even behind an older snapshot, refuse; no DDL |
| Writer rolls back then releases within timeout | acquire next, empty probe, ordered DDL and checked release |
| Writer arrives during protected interval | its GET_LOCK waits; no insert/flush/commit before lock grant |
| Non-disconnect probe failure | original exception primary; no DDL; exact cleanup precedence |
| Non-disconnect DDL failure | original exception primary; no later DDL, preceding committed DDL stays; exact cleanup precedence |
| Any acquisition/body/release loss or cleanup failure | exact 10.2-10.4 code/cause; migration failed, no revision-success claim; inspect/forward-recover schema after CL |
| Explicit later retry after refusal/timeout | fresh independently authorized attempt, full 30-second acquisition/probe; no automatic retry or state inference |
| Independently prepared absent table, repeated manual function call | acquire, probe raises original SQLAlchemy ProgrammingError / asyncmy 1146, checked release; migration fails |

Future S4-or-later native writers must cooperatively acquire the same lock on
their exact insertion connection before staging/flushing, require exact integer
1, hold through commit/rollback, and perform checked release with preserved
primary-error precedence. They cannot bypass the empty-table decision. This
constraint creates no S3 writer or S4 implementation authority; S4 must plan
its own complete operation. A transaction rollback alone is not lock cleanup.

Deleting native rows to make downgrade pass is not authorized.

No synthetic legacy/native discriminator, data copy, protocol/profile
backfill, refingerprint, relabel, receipt/evidence rewrite, reinterpretation of
old revisions, SQLite fallback, or database access occurs during planning.
Migration tests must compare the complete migration table signature with ORM
metadata, require one head `20260828_0006`, and require linear history through
`20260729_0005`. The fresh independent review of this plan must review this
complete migration design before implementation may be authorized.

## 11. Transaction, uniqueness, and downgrade-concurrency semantics

| Event | Frozen behavior |
| --- | --- |
| Successful production S3 read | no row staged; detached fully validated result returned; caller UoW retains transaction ownership |
| Production read failure | exact S3 integrity/repository exception; no partial result and no write |
| Production locking read cancellation | original cancellation; UoW rollback/close releases row locks |
| Test-local helper with `flush=False` | one pending ORM row in the test-owned session; zero flush and zero commit |
| Test-local helper with `flush=True` | one row added and flushed only in the test transaction; fixture owns rollback |
| Test-local duplicate-PK flush failure | `sqlalchemy.exc.IntegrityError` caused by `asyncmy.errors.IntegrityError` 1062; transaction failed until rollback; no production translation |
| Test-local check failure | `sqlalchemy.exc.OperationalError` caused by `asyncmy.errors.OperationalError` 3819; transaction failed until rollback; no production translation |
| Test-local exception/cancellation after flush | fixture rollback removes the row; no commit |
| Existing Run CAS | preserved unchanged; S3 does not invoke it for a native write |
| Competing raw test inserts | database primary key permits one committed winner; losing flush has the exact exception/failed-transaction state in section 9 |
| Corrupt persisted row | later production read raises stored integrity; no repair, replacement, or fallback |
| Downgrade exclusion | connection-owned named lock spans acquisition, current/locking probe, DDL, and release as section 10 freezes; no snapshot-refresh assumption |

`get_classified_for_update` row locks are released by UoW commit/rollback/close
and are never held across Provider or external work. S3 performs no Provider
call. Exact-evidence replay exists only in unchanged `RunEntryService`; the S3
classifier creates no replay protocol. There is no S3 production binding write,
second transaction, best-effort mutation, compensation, retry, or exactly-once
claim.

The future real-MySQL concurrency proof lives in
`tests/integration/test_mysql_run_protocol_binding.py` and uses two independent
connections plus test-local synchronization. Connection A runs the real
downgrade function while a test-local wrapper around `op.drop_constraint`
signals `empty_probe_complete` on entry and waits on `allow_destructive_ddl`;
this introduces no migration test hook. At that point A owns the named lock and
has observed an empty table, but has executed no destructive DDL. Connection B
then begins the exact compliant insertion exclusion protocol by executing the
same `GET_LOCK(..., 30)`. A 250-millisecond bounded observation must show B's
acquisition task still pending, B has issued no `INSERT`, and B cannot commit.

For the success branch, the test signals `allow_destructive_ddl`; A drops the
FK, index, and table, releases the lock, and completes downgrade. B then obtains
result `1`, executes its raw `INSERT`, receives
`sqlalchemy.exc.ProgrammingError` caused by `asyncmy.errors.ProgrammingError`
with MySQL error 1146 because the table no longer exists, rolls back, and
releases the named lock with result `1`. The test verifies no native row was
committed before the empty decision, no row was silently destroyed, then
re-upgrades in fixture cleanup and proves `IS_FREE_LOCK(lock_name) = 1`.

For the injected-failure branch, the wrapper raises a test-local sentinel before
delegating to the first DDL. A propagates that exact sentinel and releases the
lock. The migration caller then rolls back A's still-active probe transaction
and signals `probe_transaction_closed`; this releases the current-read gap/row
locks, not the already-released named lock. B acquires result `1`, waits for
that transaction-closed barrier before insertion, and uses `_add_native_binding_row(...,
flush=True)` successfully against the still-present table, rolls back instead
of committing, releases result `1`, and fixture cleanup proves zero row plus
`IS_FREE_LOCK(lock_name) = 1`. Every acquisition failure in 10.2 is a mandatory
variation inside V31-D; acquisition 1 is owned by V30-A. V30-C owns both probe loss points, V30-D1 owns pre-DDL
and FK loss, D2/D3 own during-index/table loss and state-detected loss before
index/table issuance after the preceding acknowledged DDL, and V30-E owns all release outcomes,
post-table loss, and the full body/cleanup precedence combinations. These are
iterations within their existing counted blocks, not extra vector IDs or
separately counted named subcases. Non-disconnect statement/result faults use
test-local wrappers over real MySQL connections; true loss uses a separate
test-owned connection to terminate the owner at the specified barrier. No
production hook, database access during authoring, or mock-only claim of real
server lock cleanup is permitted. Assert zero later statements, exact exception
identity/cause/cleanup_error, no false Alembic success, observer schema/revision,
and C0/C1/CL. Each variation independently creates and restores its schema,
parent rows and connections. V30-E repeats every release failure with successful
body and with an injected body error, plus data refusal; body identity/cause
must survive. Fault-injected scalar 0/NULL proves client branching; ordinary
real-MySQL not-owner/nonexistent-lock calls separately establish scalar meaning
within the same block. No injected result is described as a spontaneous server
outcome. Previously committed native rows are never destroyed.

V30-D2 and V30-D3 each enumerate three mandatory variations in their block:
(a) non-disconnect failure before delegating the targeted DDL, (b) disconnect
during an issued targeted DDL with uncertain outcome, and (c) state-only loss
after the preceding DDL returns successfully but before the targeted DDL is
issued. The (c) test-local wrapper delegates the preceding real DDL, records its
successful acknowledgement, signals `preceding_ddl_acknowledged`, and waits at
`owner_invalidated`. A separate test-owned connection terminates the captured
owning server session; the test marks/discards the owning connection via
SQLAlchemy invalidation without executing another SQL statement and without
injecting a body exception. Only then does the wrapper return. The migration's
own between-statement state check must raise the new exact primary before
invoking the next `op.drop_*`. A wrapper alone raising that primary is not proof.
The independent observer confirms termination/lock cleanup and inspects the
partial schema before the fixture restores the full head schema/revision and
parent rows. Each (a), (b), and (c) variation starts from its own complete empty
binding table and restores independently; none consumes another's partial
schema or objects. These six variations occupy the same two primary M blocks.
V31-B has two independently initialized variations: a fresh transaction and
the established-old-snapshot interleaving frozen in its block. Both require
the exact current/locking probe, refusal, and row/full-schema preservation.


## 12. Legacy preservation matrix

| Case | Stored proof and reconstruction | Classifier result | Prohibited mutation | Caller/replay owner | Corruption |
| --- | --- | --- | --- | --- | --- |
| Revision 1 creation state | exact Run revision/current plus `run.create/v1` receipt and canonical evidence | no legacy classification without revisions 2/3 and Session family | no S3 row synthesis or rewrite | existing create-receipt owner only | `RunProtocolBindingStoredIntegrityError` at S3 boundary |
| Revision 2 bound state | revisions 1/2, exact character revision/current/controller rows, creation and binding receipts | no legacy classification without revision 3 and Session family | no protocol/world synthesis | existing binding-receipt owner only | `RunProtocolBindingStoredIntegrityError` at S3 boundary |
| Revision 3 active P8 current | complete sections 3, 3.1, and 3.2 stored proof | `LegacyRunCompatibilityV1` with no caller authority | no native row, discriminator, protocol/profile/world write | unchanged `RunEntryService` authorizes principal/controller/replay; unchanged `SessionService` owns behavior | S3 wrapper retains direct existing cause |
| Revision 3 after Session advances | immutable entry event/evidence remain exact; current Session/snapshot strictly reconstruct and remain cross-bound | same stored-family result; Run remains active/bound | no Run completion or protocol synthesis | existing action replay/request-status/View recovery only | exact S3 wrapper on structural corruption |
| Terminal Session (`ENDED`, `RESOLVED`/`FAILED`) | complete immutable entry proof plus valid current terminal Session/snapshot | same stored-family result; scenario settlement is not Run termination | no lifecycle/binding/world mutation | unchanged application services decide disclosure/replay | fail closed with exact S3 subtype |

Revision numbers retain their exact meanings: 1 is creation, 2 is immutable
character binding, and 3 is first Session participation plus activation.
Fingerprints remain SHA-256 over their existing canonical operation or P8
evidence bytes. S3 neither changes nor reinterprets any legacy evidence.

## 13. Ordered native/corruption vectors

Every entry below states, in order: initial persisted setup; mutation/concurrency
setup; owning boundary; invoked operation; exact test path; validation/locking
order; return/exception; direct cause; SQL/physical outcome; transaction state;
row outcome; partial-result rule; subsequent-state assertion; and cleanup.
Each mandatory variation has one frozen outcome; no optional outcome is
+permitted. Named subcase blocks do not add top-level IDs.

### 13.1 Frozen literal definitions and isolation

Every vector builds its own setup. A reference to another vector's shape means
copying the literal definition only, never its transaction, execution order,
rows, objects, or retained state. Each counted block includes all mandated
variations assigned to it; variations do not contribute additional blocks.
`Cause` in older prose denotes the factual trigger; exact Python `__cause__`
is exclusively section 9 or 10. Successful results have no exception/cause.

Literal native fixture **L** is a controlled in-memory snapshot: valid Run
current/revision 1 with its ordinary creation receipt, no P8 legacy proof, no
Session/participation rows, and exact Run/line identities below. Test-owned
parent rows use the unchanged Run codec's canonical representation. The binding
carrier has exactly these 19 values, in physical column order:

1. `run_id = "run.s3.literal"`;
2. `continuous_story_line_id = "line.s3.literal"`;
3. `bound_state_version = 1`;
4. `family_discriminator = "phase_3_3_native"`;
5. `binding_epoch = "run-protocol-binding"`;
6. `binding_record_version = 1`;
7. `envelope_epoch = "run-protocol-envelope"`;
8. `envelope_record_version = 1`;
9. `envelope_canonical = L_S1`;
10. `resolver_epoch = "run-protocol-resolution"`;
11. `resolver_record_version = 1`;
12. `resolution_input_canonical = L_S2`;
13. `resource_pressure = 60`;
14. `social_trust = 45`;
15. `consequence_severity = 65`;
16. `information_opacity = 60`;
17. `conflict_intensity = 60`;
18. `resolution_fingerprint = bytes.fromhex("2cca2a7d1bc1308ca6c0cb93b440eb0f5152ecbcda313162b7c9e6ab49f795ac")`;
19. `created_at = datetime(2026, 8, 28, 0, 0, 0, 123456)` (naive UTC storage).

Exact immutable bytes (one line each, no trailing newline in either payload):

```python
L_S1 = b'{"profile_ref":{"profile_id":"difficulty.fragile-alliance","profile_version":1},"reality_boundary":"lawful","relationship_overlay":"off","schema_version":"run-protocol-envelope/v1","world_tone":"balanced"}'
L_S2 = b'{"authorized_overrides":[],"authorized_profile_id":"difficulty.fragile-alliance","authorized_profile_version":1,"canonical_envelope_hex":"7b2270726f66696c655f726566223a7b2270726f66696c655f6964223a22646966666963756c74792e66726167696c652d616c6c69616e6365222c2270726f66696c655f76657273696f6e223a317d2c227265616c6974795f626f756e64617279223a226c617766756c222c2272656c6174696f6e736869705f6f7665726c6179223a226f6666222c22736368656d615f76657273696f6e223a2272756e2d70726f746f636f6c2d656e76656c6f70652f7631222c22776f726c645f746f6e65223a2262616c616e636564227d","resolver_version":1,"schema":"run-protocol-resolution/v1"}'
```

These literals copy published S2 golden 001; no encoder generates expected
bytes during a test. Expected output has the exact profile pair
`difficulty.fragile-alliance`/1, empty overrides, balanced/lawful/off envelope,
the five scalars above and the raw fingerprint above. The pure private method
`_reconstruct_native_binding(stored, *, canonical_run, legacy_proof)` in the planned
infrastructure persistence module is synchronous and has no I/O. Repository
ORM validation supplies N01 and invokes that same N02-N15 pipeline; the pure
method checks its own exact stored-carrier N01 first. It is not exported.

Unit stored snapshots are controlled fake SELECT results; no real SQL is
executed and no database transaction exists. Their "read-only transaction"
wording denotes the mocked boundary only. All state is recreated per invocation
or per variation and discarded in fixture cleanup. No test relies on another
suite's transaction. All unmentioned fields in native corruption vectors equal
L. All lower-exception variations in section 9 inject a single exact exception
instance at its stated lower seam and prove direct-cause identity, no retry,
no later invocation, no partial result, and unchanged snapshot.

### 13.2 Exactly 56 vector/subcase blocks

- **S3-V01-A** — Initial: complete revisions 1/2/3, receipts, active character/
  controller, participation, Session, sequence-1 event, snapshot, no binding row.
  Mutation: none. Boundary: production stored-family classification. Invoke:
  `get_classified(run_id=exact_id)`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: sections 3 and
  4, plain reads: stored Run rows, L02 persisted reference, L03 immutable
  character decode, L04 complete Run validator, then legacy/current/controller/
  Session checks. A spy proves the exact decoded L03 object is passed once as
  `referenced_player_character_revision`, not omitted or first loaded at 3.1.
  Outcome: `LegacyRunCompatibilityV1` for the exact Run and Session IDs; no
  exception/cause. SQL: selects only. Transaction:
  read transaction, zero staged state. Rows: unchanged. Partial: prohibited.
  State: result grants no caller authority. Cleanup: test UoW rollback/close.
- **S3-V01-B** — Initial: independently prepared complete legacy rows and a principal resolving to a different
  controller. Mutation: replay request. Boundary: unchanged Run-entry caller
  authorization. Invoke: `RunEntryService.enter`. Path:
  `tests/unit/test_run_entry_service.py`. Order: resolve principal, lock owned
  active character, compare persisted controller before disclosure. Outcome:
  `RunEntryDecision(AUTHORIZATION_FAILED)`. Cause: controller mismatch. SQL:
  existing Run-entry reads only. Transaction: existing UoW exits without commit.
  Rows: unchanged. Partial: no classified value is disclosed. State: replay is
  denied. Cleanup: existing fixture reset.
- **S3-V02** — Initial: real MySQL has all valid L Run/revision/current,
  creation receipt and required parent-family rows, but no binding for the
  target Run/revision. Test memory holds detached exact 19-field L inputs.
  Invoke the test-local helper once with `flush=True`: it constructs the sole
  `RunProtocolBindingRow`, calls `AsyncSession.add()` once and flushes once.
  Then call production `get_classified(run_id=RunId(value="run.s3.literal"))`.
  Path: `tests/integration/test_mysql_run_protocol_binding.py`. Order: outer
  classifier then N01-N15. Outcome: exact trusted detached native result L;
  no exception or cause, no entry-world state. Exactly one INSERT, subsequent
  SELECTs, zero commit; no duplicate insertion. Assert one pending/staged object
  before flush, exactly one persisted row visible in the same transaction after
  flush and reconstruction, no production mutation, no partial result. Fixture
  rollback removes it; a fresh Session sees zero target binding rows. Cleanup
  restores its own parent fixture and closes all test Sessions.
- **S3-V03** — Initial: unit-local exact frozen slotted
  `_StoredRunProtocolBindingV1` containing
  all 19 L values and detached codec-valid canonical Run/revision-1 snapshot;
  no ORM Session, MySQL connection, or database transaction. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Invoke the production
  private `_reconstruct_native_binding(stored, canonical_run=canonical_run,
  legacy_proof=None)`
  exactly twice on the same immutable input. Both calls run N01-N15 and return
  value-equal `NativeRunProtocolBindingV1` with all literal L bytes/scalars and
  fingerprint. Results, resolved carriers and envelope/input carriers are
  distinct by identity; the direct N09 lookup is called once per invocation,
  twice total, and returns the published singleton catalogue identity. Public
  S2 APIs retain their own internal revalidation/lookups. No
  exception/cause; no partial result. Compare input snapshots before/after;
  assert zero mutation, clock calls, SQL/network/file I/O, and module/instance
  cache or retained per-call state. Stored data is unchanged; discard the local
  objects and restore spies. No V02 execution or transaction is involved.
- **S3-V04** — Initial: native ORM carrier with `binding_record_version=2`.
  Mutation: none. Boundary: production binding selector classification. Invoke:
  `get_classified`. Path: `tests/unit/test_run_protocol_binding_persistence.py`.
  Order: N01-N05, then N06 binding version. Outcome:
  `UnsupportedRunProtocolBindingVersionError`. Cause: exact unsupported binding
  version. SQL: mocked select. Transaction: read-only. Rows: unchanged. Partial:
  no result. State: S1/S2 not invoked. Cleanup: fixture reset.
- **S3-V05** — Initial: independently constructed complete L native ORM
  snapshot, valid parent Run and no legacy proof, controlled SELECTs only in
  `tests/unit/test_run_protocol_binding_persistence.py`. Invoke
  `get_classified` once per fresh variation: (a) envelope version 2 alone;
  (b) envelope version 2 plus resolver version 2; (c) S1 bytes `b"{"` plus
  resolver version 2; (d) binding version 2 plus S1 bytes `b"{"`. All other
  values are exactly L. N01-N05 pass. Winning phases: (a,b) N07, S3 stored
  integrity with direct `UnsupportedRunProtocolVersionError`; (c) N08, S3
  stored integrity with direct `RunProtocolValidationError`; (d) N06,
  `UnsupportedRunProtocolBindingVersionError` with `__cause__ is None`.
  Spies assert zero later-stage invocations after each winner, specifically no
  S2 profile lookup, semantic dispatch, canonical reconstruction or comparison;
  (d) also zero S1 calls, (a,b) zero S1 payload decoder calls. No real transaction,
  zero writes/commit/retry, no partial result; snapshot unchanged. Restore spies
  and discard each variation's local fixture independently.
- **S3-V06** — Initial: independently constructed complete L native ORM
  snapshot, valid parent Run and no legacy proof in
  `tests/unit/test_run_protocol_binding_persistence.py`. Invoke
  `get_classified` once per fresh variation: (a) resolver version 2 alone;
  (b) resolver version `"2"` and S1 bytes `b"{"`; (c) resource pressure 101
  and resolver version 2. All unmentioned values equal L. Winners: (a) N10,
  `RunProtocolBindingStoredIntegrityError` directly caused by
  `UnsupportedRunProtocolResolverVersionError`, after successful S1 N07/N08
  and N09 catalogue reacquisition; (b) N03 stored integrity, no cause, before
  S1; (c) N04 stored integrity, no cause, before S1/S2. Spies prove all later
  phases uninvoked, including canonical S2 decode/comparison for (a), every
  semantic dispatcher for (b,c). Controlled SELECTs only, no database
  transaction, zero mutation/commit/retry, unchanged snapshot and no partial
  result. Cleanup restores spies and discards local fixtures. This is exactly
  the same N01-N15 order as V05.
- **S3-V07** — Initial: native carrier with valid S1 JSON plus non-canonical byte
  ordering. Mutation: none. Boundary: production S1 reconstruction. Invoke:
  `get_classified`. Path: `tests/unit/test_run_protocol_binding_persistence.py`.
  Order: S1 decode then re-encode comparison. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: direct
  `RunProtocolValidationError`. SQL: mocked select. Transaction: read-only. Rows:
  unchanged. Partial: no result. State: S2 not invoked. Cleanup: fixture reset.
- **S3-V08** — Initial: native carrier whose strict S2 bytes name a profile pair
  different from the S1 envelope. Mutation: none. Boundary: production native
  cross-binding. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: N07/N08 S1, N09 catalogue, N10 S2 dispatch/shape,
  N11 envelope-hex then profile-pair comparison. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: exact profile-pair mismatch.
  SQL: mocked select. Transaction: read-only. Rows: unchanged. Partial: no
  result. State: N09 catalogue lookup completed; resolver not invoked. Cleanup: fixture reset.
- **S3-V09** — Initial: semantic S2 input encoded with non-canonical member
  order. Mutation: none. Boundary: production S2 canonical reconstruction.
  Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: N09 profile lookup, N10 strict decode,
  N11 public re-encode and byte comparison. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: direct
  `RunProtocolResolutionIntegrityError`. SQL: mocked select. Transaction:
  read-only. Rows: unchanged. Partial: no result. State: resolver not invoked.
  Cleanup: fixture reset.
- **S3-V10** — Initial: complete native carrier with stored
  `resource_pressure` one valid step above resolver output. Mutation: none.
  Boundary: production objective comparison. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: full decode,
  resolver, objective order beginning with resource pressure. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: resource-pressure mismatch.
  SQL: mocked select. Transaction: read-only. Rows: unchanged. Partial: no
  result. State: fingerprint comparison not reached. Cleanup: fixture reset.
- **S3-V11** — Initial: complete native carrier with one flipped fingerprint
  byte. Mutation: none. Boundary: production fingerprint comparison. Invoke:
  `get_classified`. Path: `tests/unit/test_run_protocol_binding_persistence.py`.
  Order: all prior native checks then 32-byte comparison. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: fingerprint mismatch. SQL:
  mocked select. Transaction: read-only. Rows: unchanged. Partial: no result.
  State: detached result not constructed. Cleanup: fixture reset.
- **S3-V12** — Initial: injected ORM binding row whose line/revision differs
  from the already loaded Run; no SQL insertion is attempted. Mutation: none.
  Boundary: production stored association read. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: outer Run/legacy checks, N01-N04, then N05
  binding Run identity, line and revision. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: exact Run association
  mismatch. SQL: mocked `SELECT` only. Transaction: read-only. Rows: unchanged.
  Partial: no result. State: native decoder not invoked. Cleanup: fixture reset.
- **S3-V13** — Initial: independently built complete legacy stored snapshot
  from sections 3/3.0/3.1/3.2. Invoke `get_classified` once per isolated
  variation in `tests/unit/test_run_protocol_binding_persistence.py`:
  (a) current Run binds A while its matching revision binds B; provide a valid
  immutable A row selected by current's persisted reference, so L03 passes
  and L04 raises `RunStoredRecordIntegrityError`, wrapped once directly;
  (b) malformed immutable character bytes fail at L03 with exact
  `PlayerCharacterStoredRecordIntegrityError` as direct S3 cause, before L04;
  (c) a self-consistent decoded B row returned for A's reference fails the L03
  comparison with S3 stored integrity and no cause;
  (d) missing immutable row fails at L03 with that same no-cause S3 result;
  (e) missing character-current row and (f) missing controller-binding row each
  fail at 3.1 with no-cause S3 integrity, after L04 and legacy steps 2-5 pass;
  (g) partial persisted reference triplet fails at L02 with no-cause S3 integrity;
  (h) six independently reset physical triplet variations fail at L02 with
  no-cause S3 integrity: integer ID `1`, integer contract version `1`, revision
  string `"1"`, revision `True`, revision `0`, revision `9223372036854775808`;
  (i) three independently reset constructor variations at L02: ID `""` raises
  `pydantic.ValidationError`, contract version `"unsupported"` raises
  `ValueError`, and an injected constructor `TypeError` remains that exact
  object; each is the direct cause of one S3 wrapper, with zero immutable SELECTs;
  (j) injected codec `AttributeError` wraps once with that object directly;
  (k) malformed immutable bytes plus the (a) Run mismatch fails at L03 exactly
  as (b), with zero complete Run-validator calls. All top-level failures are
  exactly `RunProtocolBindingStoredIntegrityError`. In (a), later current/
  controller/Session/native checks are not reached; the prerequisite immutable
  lookup/decode did occur. Each other variation stops at its stated first phase.
  Controlled reads only, no real SQL transaction, no mutation/retry/partial
  result; snapshot unchanged, all later phases uninvoked. Reset each fixture.
- **S3-V14** — Initial: its own complete valid revisions 1/2/3 legacy family,
  including the immutable character row matching current's persisted reference,
  current/controller rows, all receipts, participation, Session, event and
  snapshot; no native row initially. Use the sole test-local helper once with
  `flush=True` to add a native row whose Run/line match that family,
  `bound_state_version=3`, and remaining native fields equal valid L values.
  Boundary: production family exclusion.
  Invoke: `get_classified`. Path:
  `tests/integration/test_mysql_run_protocol_binding.py`. Order: immutable
  prerequisite L03 decode, L04 with that exact object supplied, complete legacy
  proof and current/controller/Session checks, then N01-N14 native proof and
  N15 exclusion decision. Assert every preceding validation succeeds; no missing
  immutable-input or association error substitutes for the intended verdict.
  Outcome: exact `ContradictoryRunFamilyError`, `__cause__ is None`. SQL:
  helper `INSERT`, production reads. Transaction: test-owned, uncommitted. Rows:
  legacy rows plus one flushed native row. Partial: neither result returned.
  State: no fallback and zero production mutation; legacy row hashes unchanged.
  Cleanup: rollback removes the native row, a fresh Session proves absence,
  and the fixture restores its own parent family and closes its Sessions.
- **S3-V15** — Initial: revision-1 legacy Run without revisions 2/3, Session
  family, and native row. Mutation: none. Boundary: production family
  completeness. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: Run codec then
  legacy completeness. Outcome: `RunProtocolBindingStoredIntegrityError`.
  Cause: incomplete persisted family. SQL: reads only. Transaction: read-only.
  Rows: unchanged. Partial: no result. State: absence did not select legacy.
  Cleanup: fixture reset.
- **S3-V16** — Initial: injected ORM native instance missing mapped attribute
  `resolution_fingerprint`. Mutation: none. Boundary: production ORM-to-stored
  conversion. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: physical mapped
  attributes through the missing field. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: exact missing mapped
  attribute. SQL: mocked select. Transaction: read-only. Rows: unchanged.
  Partial: no carrier. State: reconstruction not invoked. Cleanup: fixture reset.
- **S3-V17** — Initial: injected ORM native instance with
  `family_discriminator=None`. Mutation: none. Boundary: production physical
  row validation. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: N01 allowlist, then N02 discriminator type. Outcome: `RunProtocolBindingStoredIntegrityError`.
  Cause: discriminator is not an exact string. SQL: mocked select. Transaction:
  read-only. Rows: unchanged. Partial: no carrier. State: version dispatch not
  invoked. Cleanup: fixture reset.
- **S3-V18** — Initial: injected ORM native instance with exact string
  discriminator `phase_3_4_native`. Mutation: none. Boundary: production family
  dispatch. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: N01-N05, then N06 supported discriminator literal. Outcome:
  `UnsupportedRunProtocolBindingVersionError`. Cause: unknown discriminator.
  SQL: mocked select. Transaction: read-only. Rows: unchanged. Partial: no
  carrier. State: S1 not invoked. Cleanup: fixture reset.
- **S3-V19** — Initial: injected ORM native instance with
  `binding_record_version=True`. Mutation: none. Boundary: production exact-type
  validation. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: N01/N02, then N03 binding integer type. Outcome: `RunProtocolBindingStoredIntegrityError`. Cause:
  Boolean is not exact integer. SQL: mocked select. Transaction: read-only.
  Rows: unchanged. Partial: no carrier. State: selector dispatch not invoked.
  Cleanup: fixture reset.
- **S3-V20-A** — Initial: injected ORM row with integer `run_id`. Mutation:
  none. Boundary: production physical validation. Invoke: `get_classified`.
  Path: `tests/unit/test_run_protocol_binding_persistence.py`. Order: N01, then N02 column 1 exact string type. Outcome: `RunProtocolBindingStoredIntegrityError`. Cause:
  Run ID type mismatch. SQL: mocked select. Transaction: read-only. Rows:
  unchanged. Partial: no carrier. State: no later numeric/range/semantic phase invoked. Cleanup: reset.
- **S3-V20-B** — Initial: injected ORM row with string
  `envelope_canonical`. Mutation: none. Boundary: production physical
  validation. Invoke: `get_classified`. Path: same unit file. Order: N01, then N02 nonnumeric types through column 9. Outcome: `RunProtocolBindingStoredIntegrityError`. Cause: envelope
  byte type mismatch. SQL: mocked select. Transaction: read-only. Rows:
  unchanged. Partial: no carrier. State: S1 unread. Cleanup: reset.
- **S3-V20-C** — Initial: injected ORM row with string `resource_pressure`.
  Mutation: none. Boundary: production physical validation. Invoke:
  `get_classified`. Path: same unit file. Order: N01/N02, then N03 integer types through column 13. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: objective type mismatch. SQL:
  mocked select. Transaction: read-only. Rows: unchanged. Partial: no carrier.
  State: later N03 integer fields and semantic phases uninvoked. Cleanup: reset.
- **S3-V20-D** — Initial: injected ORM row with string `created_at`. Mutation:
  none. Boundary: production physical validation. Invoke: `get_classified`.
  Path: same unit file. Order: N01, then N02 nonnumeric types through column 19; N03 not reached. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: datetime type mismatch. SQL:
  mocked select. Transaction: read-only. Rows: unchanged. Partial: no carrier.
  State: reconstruction absent. Cleanup: reset.
- **S3-V21-A** — Initial: exact revision-1 Run; helper receives a 1025-byte
  envelope. Mutation: direct helper add plus flush. Boundary: test-local physical
  schema evidence. Invoke: `_add_native_binding_row(..., flush=True)`. Path:
  `tests/integration/test_mysql_run_protocol_binding.py`. Order: add then flush.
  Outcome: `sqlalchemy.exc.OperationalError`. Cause: direct
  `asyncmy.errors.OperationalError` with MySQL check error 3819. SQL: `INSERT`
  rejected by `ck_run_protocol_bindings_payload_sizes`. Transaction: failed
  until rollback. Rows: zero persisted binding rows. Partial: no production
  result. State: Run rows unchanged. Cleanup: fixture rollback.
- **S3-V21-B** — Initial: injected loaded ORM row with 1025-byte
  `resolution_input_canonical`; no SQL insertion. Mutation: none. Boundary:
  production read validation. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: physical payload
  lengths. Outcome: `RunProtocolBindingStoredIntegrityError`. Cause: S2 payload
  exceeds 1024. SQL: mocked `SELECT`. Transaction: read-only. Rows: unchanged.
  Partial: no result. State: S2 decoder not invoked. Cleanup: fixture reset.
- **S3-V22** — Initial: first exact binding row flushed in session A and
  committed for physical evidence. Mutation: session B helper flushes identical
  primary key. Boundary: test-local uniqueness evidence. Invoke:
  `_add_native_binding_row(..., flush=True)`. Path:
  `tests/integration/test_mysql_run_protocol_binding.py`. Order: A commit, B add,
  B flush. Outcome: `sqlalchemy.exc.IntegrityError`. Cause: direct
  `asyncmy.errors.IntegrityError` numeric 1062. SQL: primary key rejects B.
  Transaction: B failed until rollback. Rows: exactly A row. Partial: no S3
  production exception. State: A row unchanged. Cleanup: B rollback, fixture
  removes A through test database cleanup.
- **S3-V23** — Initial: existing Run at version 1, no binding row. Mutation:
  existing Run repository CAS uses stale expected version. Boundary: unchanged
  Run persistence. Invoke: existing Run CAS method. Path:
  `tests/unit/test_run_repositories.py`. Order: Run update before any test helper.
  Outcome: `False`. Cause: rowcount zero. SQL: existing Run `UPDATE`. Transaction:
  caller rolls back. Rows: no binding row because helper is never invoked.
  Partial: no native result. State: Run unchanged. Cleanup: UoW rollback.
- **S3-V24** — Initial: exact Run owner, empty binding table. Mutation: two
  separate sessions concurrently add identical rows, acquire downgrade lock in
  sequence, then flush/commit. Boundary: test-local MySQL uniqueness. Invoke:
  helper in each session. Path: `tests/integration/test_mysql_run_protocol_binding.py`.
  Order: named-lock acquisition, insert, commit, release per session. Outcome:
  first session commits; second flush raises `sqlalchemy.exc.IntegrityError`
  caused by asyncmy numeric 1062. Cause: duplicate primary key. SQL: one PK winner. Transaction: winner
  committed, loser failed then rolled back. Rows: exactly one. Partial: no
  production result. State: winner bytes unchanged. Cleanup: fixture removes row.
- **S3-V25** — Initial: exact Run owner, empty binding table. Mutation: two
  sessions submit different payloads under the same Run primary key using the
  named-lock protocol. Boundary: test-local MySQL uniqueness. Invoke: helper in
  each session. Path: `tests/integration/test_mysql_run_protocol_binding.py`.
  Order: first lock/insert/commit/release, second lock/insert/flush. Outcome:
  first commits; second raises `sqlalchemy.exc.IntegrityError` caused by asyncmy
  numeric 1062. Cause: duplicate PK. SQL: second `INSERT` rejected. Transaction:
  loser failed then rolled back. Rows: exact first payload. Partial: no merged
  row. State: winner unchanged. Cleanup: fixture removes winner.
- **S3-V26** — Initial: exact Run owner and helper-flushed binding in a test UoW.
  Mutation: test-local sentinel raised after flush. Boundary: test fixture
  transaction. Invoke: helper then sentinel. Path:
  `tests/integration/test_mysql_run_protocol_binding.py`. Order: add, flush,
  raise, UoW exit. Outcome: exact sentinel propagates. Cause: injected test
  failure. SQL: insert then rollback. Transaction: rolled back. Rows: zero.
  Partial: no production result. State: subsequent fresh session finds no row.
  Cleanup: fixture confirms and closes.
- **S3-V27** — Initial: exact Run owner and helper-flushed binding in a test UoW.
  Mutation: task cancellation after flush. Boundary: test fixture transaction.
  Invoke: helper then cancellation point. Path:
  `tests/integration/test_mysql_run_protocol_binding.py`. Order: add, flush,
  cancel, exceptional exit. Outcome: original `asyncio.CancelledError`. Cause:
  task cancellation. SQL: insert then rollback. Transaction: rolled back. Rows:
  zero. Partial: no result. State: fresh session finds no row. Cleanup: fixture
  awaits cleanup and closes.
- **S3-V28-A** — Initial: injected ORM binding row missing
  `bound_state_version`. Mutation: none. Boundary: production ORM conversion.
  Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: mapped physical
  fields. Outcome: `RunProtocolBindingStoredIntegrityError`. Cause: missing
  mapped revision field. SQL: mocked select. Transaction: read-only. Rows:
  unchanged. Partial: no result. State: association checks not reached. Cleanup:
  fixture reset.
- **S3-V28-B** — Initial: injected ORM binding row points at another line while
  retaining the requested Run ID. Mutation: none. Boundary: production
  association check. Invoke: `get_classified`. Path:
  `tests/unit/test_run_protocol_binding_persistence.py`. Order: outer Run/legacy checks and N01-N04, then N05 Run/line comparison. Outcome: `RunProtocolBindingStoredIntegrityError`. Cause:
  crossed line. SQL: mocked select. Transaction: read-only. Rows: unchanged.
  Partial: no result. State: native decoding not reached. Cleanup: fixture reset.
- **S3-V28-C** — Initial: exact ORM row plus injected attribute `run_family`.
  Mutation: none. Boundary: production ORM-state allowlist. Invoke:
  `get_classified`. Path: `tests/unit/test_run_protocol_binding_persistence.py`.
  Order: N01 mapped/instance-state allowlist before any field value. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: relationship-like injected
  state. SQL: mocked select. Transaction: read-only. Rows: unchanged. Partial:
  no result. State: detached carrier not constructed. Cleanup: remove injection.
- **S3-V29** — Initial: complete legacy family hashed field-by-field before
  upgrade. Mutation: upgrade `20260729_0005` to `20260828_0006`. Boundary:
  migration upgrade then production classification. Invoke: Alembic upgrade,
  `get_classified`. Path: `tests/integration/test_mysql_run_protocol_binding.py`.
  Order: create table/checks/index/FK; rehash old rows; load persisted Run
  reference, decode its existing immutable character revision at L03, supply
  that exact object as `referenced_player_character_revision` at L04, then
  complete legacy/current/controller/Session proof. The initial family includes
  every matching character revision/current/controller row; no synthetic repair
  supplies missing evidence. Outcome: `LegacyRunCompatibilityV1`, no exception
  or cause. SQL:
  additive DDL plus selects, zero old-row DML. Transaction: migration semantics.
  Rows: all old hashes equal. Partial: prohibited. State: new table empty.
  Cleanup: migration fixture restores head state.
- **S3-V30-A** — Initial: upgraded empty binding table. Mutation: downgrade.
  Boundary: migration downgrade. Invoke: `downgrade()`. Path:
  `tests/integration/test_mysql_run_protocol_binding.py`. Order: GET_LOCK result
  1, empty current/locking probe, FK drop, index drop, table drop, RELEASE_LOCK result 1.
  Outcome: revision `20260729_0005`. Cause: empty protected interval. SQL: exact
  section-10 sequence. Transaction: MySQL DDL commits; named lock remains held
  through DDL. Rows: zero destroyed. Partial: no schema-success claim before all
  DDL. State: lock free. Cleanup: re-upgrade.
- **S3-V30-B** — Initial: independently provisioned revision `20260729_0005` schema with no binding table. Mutation: direct repeated
  migration-function invocation. Boundary: migration defensive evidence.
  Invoke: `downgrade()`. Path: same integration file. Order: acquire, probe
  absent table, checked cleanup release under section 10.4. Outcome: `sqlalchemy.exc.ProgrammingError`
  caused by asyncmy MySQL 1146. Cause: missing table. SQL: probe fails.
  Transaction: no S3 DDL. Rows: none. Partial: no success. State: lock free.
  Cleanup: re-upgrade.
- **S3-V30-C** — Initial: empty table; test injects a probe exception. Mutation:
  downgrade. Boundary: migration exceptional path. Invoke: `downgrade()`. Path:
  same integration file. Order: acquire, failing probe, release. Outcome: exact
  injected database exception. Cause: probe failure. SQL: zero destructive DDL.
  Transaction: connection remains subject to migration cleanup. Rows: zero.
  Partial: no success. State: table present, lock free. Cleanup: fixture reset.
- **S3-V30-D1** — Initial: empty table; FK-drop exception injected. Mutation:
  downgrade. Boundary: migration exceptional DDL. Invoke: `downgrade()`. Path:
  same integration file. Order: acquire, probe, FK drop fails, release. Outcome:
  exact injected exception. Cause: first DDL. SQL: index/table remain.
  Transaction: no destructive DDL committed. Rows: zero destroyed. Partial: no
  success. State: lock free, full table present. Cleanup: reset.
- **S3-V30-D2** — Initial: empty table; index-drop exception injected. Mutation:
  downgrade. Boundary: migration exceptional DDL. Invoke: `downgrade()`. Path:
  same integration file. Order: acquire, probe, FK drop, index drop fails,
  release. Outcome: exact injected exception. Cause: second DDL. SQL: FK absent,
  index/table remain. Transaction: FK drop committed. Rows: zero destroyed.
  Partial: no success. State: lock free, exact partial schema. Cleanup: rebuild.
  Mandatory independently initialized/restored variations are (a) this original
  non-disconnect pre-delegation failure; (b) loss during the issued index DDL,
  raising `RuntimeError("P3.3-S3 downgrade BODY_CONNECTION_LOST_DDL_INDEX")`
  with the exact observed disconnect as direct cause, FK known removed but
  index outcome uncertain, no table DDL; (c) after acknowledged FK removal,
  before any index DDL, section-11 barriers make closed/invalidated state
  observable without an underlying body exception. The migration raises
  `RuntimeError("P3.3-S3 downgrade BODY_CONNECTION_LOST_BEFORE_INDEX")`
  `from None`; index and table DDL are never invoked. Known schema in (c):
  table, supporting index, PK and four checks present, FK absent, zero binding
  rows. For (b,c), apply CL and 10.4: no release SQL on the invalidated owner,
  exact primary preserved with before-release cleanup error attached (cause
  is the observed loss in (b), `None` in (c)), physical discard, no reconnect
  or successful revision update. Observer proves termination/lock release and
  actual schema/revision before restoration; client loss alone is insufficient.
  Fixture restores full schema, head revision, parent rows and connections after
  each variation. No partial schema/result counts as success.
- **S3-V30-D3** — Initial: empty table; table-drop exception injected. Mutation:
  downgrade. Boundary: migration exceptional DDL. Invoke: `downgrade()`. Path:
  same integration file. Order: acquire, probe, FK drop, index drop, table drop
  fails, release. Outcome: exact injected exception. Cause: third DDL. SQL:
  table remains without FK/index. Transaction: prior DDL committed. Rows: zero
  destroyed. Partial: no success. State: lock free, exact partial schema.
  Cleanup: rebuild. Mandatory independently initialized/restored variations are
  (a) this original non-disconnect pre-delegation failure; (b) loss during issued
  table DDL, raising `RuntimeError("P3.3-S3 downgrade BODY_CONNECTION_LOST_DDL_TABLE")`
  with the exact observed disconnect as direct cause, FK/index known removed
  but table outcome uncertain; (c) after acknowledged index removal, before
  any table DDL, the section-11 state-only barrier yields
  `RuntimeError("P3.3-S3 downgrade BODY_CONNECTION_LOST_BEFORE_TABLE")`
  `from None`; table DDL is never invoked. Known schema in (c): FK/supporting
  index absent, table/PK/four checks present, zero binding rows. For (b,c), no
  release SQL follows invalidation; preserve the primary with the before-release
  cleanup error attached (same loss cause in (b), `None` in (c)), invalidate/
  physically discard, never reconnect/continue or report revision success.
  CL observer evidence establishes termination/lock release and actual schema/
  revision; client detection alone proves neither immediate server release nor
  an uncertain DDL outcome. Each fixture restores full schema/head revision,
  parent rows and connections only after these assertions.
- **S3-V30-E** — Initial: empty table; release result injected as 0 after ordered
  DDL. Mutation: downgrade. Boundary: migration release contract. Invoke:
  `downgrade()`. Path: same integration file. Order: acquire, probe, DDL,
  release check. Outcome: `RuntimeError("P3.3-S3 downgrade RELEASE_NOT_OWNER")`;
  `__cause__ is None`. Trigger: result 0. All section-10.4 release and
  precedence variations are mandatory within this block. SQL:
  table dropped. Transaction: Alembic revision update not claimed. Rows: zero
  destroyed. Partial: no success. State: connection close frees lock. Cleanup:
  restore schema and revision.
- **S3-V31-A** — Initial: one committed native row. Mutation: downgrade.
  Boundary: migration data guard. Invoke: `downgrade()`. Path:
  `tests/integration/test_mysql_run_protocol_binding.py`. Order: acquire, probe
  returns 1, refusal, release. Outcome: exact data-present `RuntimeError`. Cause:
  committed row. SQL: zero DDL. Transaction: migration aborts. Rows: one remains.
  Partial: no schema change. State: lock free. Cleanup: fixture removes row.
- **S3-V31-B** — Two independent variations in the same integration block:
  (a) the writer commits/releases before a fresh migration transaction's probe;
  (b) the migration transaction already has an older consistent-read snapshot.
  Each starts with its own complete upgraded empty binding table and committed
  valid parent Run family. Use distinct physical connections A (migration),
  B (test writer with its bound test-owned AsyncSession), and O (observer).
  Capture their connection IDs and roll back incidental identity-read
  transactions before setting A's isolation or starting the interleaving;
  retain the pinned physical connections, with no swapping or pool reuse.
  B's bound Session uses `join_transaction_mode="control_fully"` and owns the
  insertion transaction: GET_LOCK, helper add/flush, commit and checked release
  use that Session on B, with no separate external transaction left uncommitted.
  B acquires the exact section-10 named lock with result 1 before
  staging/flush and waits for `snapshot_established` in (b).
  In (b), A sets REPEATABLE READ before beginning its transaction, explicitly
  begins, and executes plain `SELECT 1 FROM run_protocol_bindings LIMIT 1`,
  observing empty and establishing its consistent-read snapshot. It signals
  `snapshot_established` without ending/changing that transaction. In (a), A
  establishes no prior consistent snapshot. B calls the sole helper once with
  valid detached inputs and `flush=True`, then signals `writer_flushed` and
  waits for `allow_writer_commit`; the helper never commits.
  Invoke the real `downgrade()` on A. A retains its existing transaction in
  (b); its GET_LOCK waits behind B. After a 250-ms observation proves A pending
  and zero migration probe/DDL issued, signal `allow_writer_commit`. Within
  the 30-second acquisition timeout B commits, checks RELEASE_LOCK result 1,
  and signals `writer_committed_and_released`. A acquires result 1 and performs
  exactly the current read `SELECT 1 FROM run_protocol_bindings LIMIT 1 FOR UPDATE`
  on the same physical connection/transaction, observing the binding committed
  after its old snapshot in (b). No refresh/commit/rollback on A is permitted
  between its snapshot and probe. Both variations raise exactly the section-10.1
  data-present RuntimeError with `__cause__ is None`; `primary.cleanup_error`
  is `None` after A's checked release 1. Every destructive DDL call count is
  zero. The migration caller rolls back/closes A's remaining transaction;
  B's row remains committed. O in a fresh transaction independently verifies
  the exact row bytes, full 19-column/PK/four-check/FK/index signature, unchanged
  head revision, and `IS_FREE_LOCK(name)=1`. No partial result or false downgrade
  success is returned. Only after assertions does fixture cleanup remove its
  own row/parents, restore the starting schema/revision, and close A/B/O. Each
  variation owns its barriers, sessions, rows and cleanup; neither is an S3
  production writer or depends on another block's execution.
- **S3-V31-C** — Initial: writer owns named lock, flushes, rolls back, releases
  within 30 seconds. Mutation: downgrade waiting concurrently. Boundary:
  cooperative exclusion. Invoke: helper protocol and `downgrade()`. Path: same
  integration file. Order: writer rollback/release, downgrade acquire, empty
  probe, ordered DDL, release. Outcome: revision `20260729_0005`. Cause: no
  committed row. SQL: ordered DDL. Transaction: writer rolled back. Rows: zero.
  Partial: no row loss. State: lock free. Cleanup: re-upgrade.
- **S3-V31-D** — Initial: second connection holds named lock longer than 30
  seconds without inserting. Mutation: downgrade. Boundary: migration lock
  acquisition. Invoke: `downgrade()`. Path: same integration file. Order:
  GET_LOCK waits then returns 0. Outcome: `RuntimeError("P3.3-S3 downgrade ACQUIRE_TIMEOUT")`;
  `__cause__ is None`. All section-10.2 acquisition failure variations are mandatory
  within this block. Trigger: timeout. SQL: zero probe and zero DDL. Transaction: migration aborts. Rows:
  unchanged. Partial: no success. State: table present. Cleanup: holder releases.
- **S3-V31-E** — Initial: this test independently commits one native row and performs its own
  first refused downgrade. Mutation: repeat within this test.
  Boundary: migration repeat after refusal. Invoke: `downgrade()`. Path: same
  integration file. Order: acquire, probe, refusal, release. Outcome: same exact
  data-present `RuntimeError`. Cause: same row. SQL: zero DDL. Transaction:
  abort. Rows: unchanged. Partial: no success. State: lock free. Cleanup: remove
  row.
- **S3-V31-F** — Initial: lock holder remains beyond a second 30-second window.
  Mutation: this test performs its own first timeout, then repeats downgrade. Boundary: migration repeat after
  timeout. Invoke: `downgrade()`. Path: same integration file. Order: fresh
  GET_LOCK returns 0. Outcome: `RuntimeError("P3.3-S3 downgrade ACQUIRE_TIMEOUT")`,
  `__cause__ is None`. Trigger: second timeout.
  SQL: zero probe and DDL. Transaction: abort. Rows: unchanged. Partial: no
  success. State: table present. Cleanup: holder releases.
- **S3-V32-A** — Initial: empty table; connection A pauses after empty probe;
  connection B starts the named-lock insertion protocol. Mutation: release DDL
  barrier. Boundary: real-MySQL downgrade/write exclusion. Invoke: real
  `downgrade()` plus B `GET_LOCK` and raw insert. Path: same integration file.
  Order: exact section-11 synchronization. Outcome: B remains pending during
  protection, then B insert raises `sqlalchemy.exc.ProgrammingError` caused by
  asyncmy MySQL 1146. Cause: A removed empty table before releasing. SQL: no B
  insert commits. Transaction: B rolls back. Rows: zero destroyed. Partial: no
  native result. State: lock free after both releases. Cleanup: re-upgrade.
- **S3-V32-B** — Initial: independently created empty table and section-11 two-connection
  pause, with first DDL replaced by an injected
  sentinel. Mutation: allow failing DDL wrapper. Boundary: real-MySQL failure
  exclusion. Invoke: real downgrade path and B helper protocol. Path: same
  integration file. Order: B pending, A sentinel, A release, B acquire, helper
  flush only after A's caller rolls back the probe transaction and signals
  `probe_transaction_closed`, B rollback, B release. Outcome: A sentinel plus successful B flush.
  Cause: injected pre-DDL failure. SQL: table remains; B insert never commits.
  Transaction: B rolled back. Rows: zero. Partial: no production result. State:
  lock free. Cleanup: fixture reset.
- **S3-V33** — Initial: built application composition and OpenAPI snapshot from
  unchanged production modules. Mutation: inspect symbols/routes. Boundary:
  production public surface. Invoke: composition factory and schema generation.
  Path: `tests/unit/test_run_repositories.py`. Order: import, compose, enumerate.
  Outcome: no native admission service/command/route and no public shape change.
  Cause: S3 exposes reads only. SQL: zero. Transaction: none. Rows: none.
  Partial: no hidden writer reference. State: existing API unchanged. Cleanup:
  fixture close.
- **S3-V34** — Initial: concrete read-only repository mock. Mutation: caller
  passes `entry_world_id` to `get_classified`. Boundary: production closed read
  signature. Invoke: `get_classified(run_id=..., entry_world_id=...)`. Path:
  `tests/unit/test_run_repositories.py`. Order: Python signature binding before
  method body. Outcome: `TypeError`. Cause: unexpected keyword argument. SQL:
  zero. Transaction: not opened. Rows: unchanged. Partial: no result. State: no
  character/world authority. Cleanup: mock reset.
- **S3-V35-A** — Initial: injected strict S2 JSON with extra member `world_id`.
  Mutation: none. Boundary: production private S2 decoder. Invoke:
  `get_classified`. Path: `tests/unit/test_run_protocol_binding_persistence.py`.
  Order: strict JSON member allowlist. Outcome:
  `RunProtocolBindingStoredIntegrityError`. Cause: direct
  `RunProtocolResolutionIntegrityError`. SQL: mocked read. Transaction:
  read-only. Rows: unchanged. Partial: no result. State: N09 profile lookup completed; N11 input construction absent.
  Cleanup: fixture reset.
- **S3-V35-B** — Initial: exact ORM row with extra attribute `writer`. Mutation:
  none. Boundary: production ORM-state allowlist. Invoke: `get_classified`.
  Path: same unit file. Order: N01 mapped/instance-state allowlist before any field value.
  Outcome: `RunProtocolBindingStoredIntegrityError`. Cause: injected attribute.
  SQL: mocked read. Transaction: read-only. Rows: unchanged. Partial: no result.
  State: detached carrier absent. Cleanup: remove attribute.
- **S3-V36** — Initial: repository mock with no persisted reads configured.
  Mutation: caller supplies `run_id=None`. Boundary: production closed
  classification input. Invoke: `get_classified(run_id=None)`. Path:
  `tests/unit/test_run_repositories.py`. Order: exact `RunId` input validation
  before SQL. Outcome: `TypeError`. Cause: absence is not `RunId`. SQL: zero.
  Transaction: not opened. Rows: unchanged. Partial: no classification. State:
  no legacy/native mode selected. Cleanup: mock reset.

The top-level sequence remains exactly `S3-V01` through `S3-V36`. S3-V02 and
S3-V32 are positive boundary evidence, not authority to bind a world or create
a production writer.

### 13.3 Exact vector-to-suite allocation

Suite aliases below resolve to one exact test path and mandatory environment.
Each allocation row inherits its alias's classification, DB requirement, and
environment. Function names are frozen future names unless marked existing.
Each row contributes exactly **1** primary block; internal variation loops
contribute **0** extra. No block has two primary owners. Existing E/C regression
files are run unchanged; they are not additions to the 15-path edit budget.

| Alias | Exact test path | Classification / database / mandatory environment |
| --- | --- | --- |
| P | `tests/unit/test_run_protocol_binding_persistence.py` | unit / no DB / repository .venv, sanitized offline, no DB/Provider/Live variables |
| R | `tests/unit/test_run_repositories.py` | unit / no DB / same offline environment; new composition assertions stay here |
| E | `tests/unit/test_run_entry_service.py` | existing unit / no DB / same offline environment; existing function unchanged |
| M | `tests/integration/test_mysql_run_protocol_binding.py` | real MySQL / DB required / MySQL 8, mysql+asyncmy, deviation_protocol_test only, Live disabled; zero environment skips |
| C | `tests/unit/test_run_composition.py` | existing unit secondary proof only / no DB / same offline environment |

| Exact vector/subcase | Primary suite | Exact function | Expected result/exception | Secondary proof | Aggregate contribution |
| --- | --- | --- | --- | --- | ---: |
| S3-V01-A | P | `test_s3_v01_a` | Legacy result; section-9 variations | none | 1 |
| S3-V01-B | E | `test_other_controller_receipt_fails_authorization_before_disclosure` | RunEntryDecision(AUTHORIZATION_FAILED) | none | 1 |
| S3-V02 | M | `test_s3_v02` | exact native L result; one row then rollback zero | none | 1 |
| S3-V03 | P | `test_s3_v03` | two detached value-equal L results | none | 1 |
| S3-V04 | P | `test_s3_v04` | UnsupportedRunProtocolBindingVersionError | none | 1 |
| S3-V05 | P | `test_s3_v05` | N07/N08/N06 outcomes in V05 | none | 1 |
| S3-V06 | P | `test_s3_v06` | N10/N03/N04 outcomes in V06 | none | 1 |
| S3-V07 | P | `test_s3_v07` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V08 | P | `test_s3_v08` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V09 | P | `test_s3_v09` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V10 | P | `test_s3_v10` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V11 | P | `test_s3_v11` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V12 | P | `test_s3_v12` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V13 | P | `test_s3_v13` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V14 | M | `test_s3_v14` | ContradictoryRunFamilyError | none | 1 |
| S3-V15 | P | `test_s3_v15` | stored integrity; genuine-absence variation returns None | none | 1 |
| S3-V16 | P | `test_s3_v16` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V17 | P | `test_s3_v17` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V18 | P | `test_s3_v18` | UnsupportedRunProtocolBindingVersionError | none | 1 |
| S3-V19 | P | `test_s3_v19` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V20-A | P | `test_s3_v20_a` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V20-B | P | `test_s3_v20_b` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V20-C | P | `test_s3_v20_c` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V20-D | P | `test_s3_v20_d` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V21-A | M | `test_s3_v21_a` | SQLAlchemy OperationalError / asyncmy 3819 | none | 1 |
| S3-V21-B | P | `test_s3_v21_b` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V22 | M | `test_s3_v22` | SQLAlchemy IntegrityError / asyncmy 1062 | none | 1 |
| S3-V23 | R | `test_s3_v23` | False; unchanged Run | none | 1 |
| S3-V24 | M | `test_s3_v24` | one winner; IntegrityError / 1062 loser | none | 1 |
| S3-V25 | M | `test_s3_v25` | first payload wins; IntegrityError / 1062 loser | none | 1 |
| S3-V26 | M | `test_s3_v26` | original injected sentinel; rollback zero | none | 1 |
| S3-V27 | M | `test_s3_v27` | original CancelledError; rollback zero | none | 1 |
| S3-V28-A | P | `test_s3_v28_a` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V28-B | P | `test_s3_v28_b` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V28-C | P | `test_s3_v28_c` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V29 | M | `test_s3_v29` | Legacy result; old rows byte-equal | none | 1 |
| S3-V30-A | M | `test_s3_v30_a` | successful downgrade and release 1 | none | 1 |
| S3-V30-B | M | `test_s3_v30_b` | SQLAlchemy ProgrammingError / asyncmy 1146 | none | 1 |
| S3-V30-C | M | `test_s3_v30_c` | original probe failure or exact probe loss code | none | 1 |
| S3-V30-D1 | M | `test_s3_v30_d1` | original FK failure or pre-DDL/FK loss code | none | 1 |
| S3-V30-D2 | M | `test_s3_v30_d2` | (a) original index failure; (b) during-index loss; (c) BEFORE_INDEX state-only loss | none | 1 |
| S3-V30-D3 | M | `test_s3_v30_d3` | (a) original table failure; (b) during-table loss; (c) BEFORE_TABLE state-only loss | none | 1 |
| S3-V30-E | M | `test_s3_v30_e` | 10.4 release/precedence matrix; post-table loss | none | 1 |
| S3-V31-A | M | `test_s3_v31_a` | exact data-refusal RuntimeError | none | 1 |
| S3-V31-B | M | `test_s3_v31_b` | exact no-cause data refusal with (a) fresh transaction and (b) old snapshot/current probe | none | 1 |
| S3-V31-C | M | `test_s3_v31_c` | successful empty downgrade | none | 1 |
| S3-V31-D | M | `test_s3_v31_d` | 10.2 acquisition matrix; no body on failure | none | 1 |
| S3-V31-E | M | `test_s3_v31_e` | same data-refusal RuntimeError on two local attempts | none | 1 |
| S3-V31-F | M | `test_s3_v31_f` | ACQUIRE_TIMEOUT on two local attempts | none | 1 |
| S3-V32-A | M | `test_s3_v32_a` | writer pending then ProgrammingError / 1146 | none | 1 |
| S3-V32-B | M | `test_s3_v32_b` | original sentinel; B flush succeeds then rollback | none | 1 |
| S3-V33 | R | `test_s3_v33` | closed writer/public surface; unchanged OpenAPI | C: route regression (0) | 1 |
| S3-V34 | R | `test_s3_v34` | TypeError before body | none | 1 |
| S3-V35-A | P | `test_s3_v35_a` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V35-B | P | `test_s3_v35_b` | RunProtocolBindingStoredIntegrityError; cause per section 9 | none | 1 |
| S3-V36 | R | `test_s3_v36` | TypeError before SQL | none | 1 |

The sole intentional secondary assignment is C for V33:
`test_run_composition_activates_only_authorized_player_character_routes`,
existing unchanged route allowlist proof; it contributes zero aggregate blocks.
R owns V33's new symbol/read-port/OpenAPI assertions and the primary result.
E's existing other-controller test independently prepares its own fresh/replay
fixtures and already proves V01-B; no new test or edit to that file is required.

Recount: **36 top-level IDs, 56 primary blocks**. P owns 27; R owns 4;
E owns 1; M owns 24. Unit total 32 plus real-MySQL 24 equals 56.
C owns zero primary and one secondary assignment. All other authorized test
paths, including `tests/unit/test_run_protocol_binding.py` and
`tests/unit/test_repository_and_uow.py`, remain mandatory carrier/UoW regression
evidence with zero vector-primary assignments. Other adjacent unchanged Run,
S1 and S2 suites are regression evidence, not additional block contributions.

Aggregate coverage is the set union of the 56 allocation rows, checked against
the 56 section-13.2 block headings and exact collected owner/function pairs.
Every internal variation in sections 4/9/10 must pass before its one block is
complete. Duplicate execution by Offline/MySQL/Full does not add coverage.
No suite may claim aggregate completion alone. Missing, duplicate, wrong-suite,
or extra primary assignments, skipped mandatory variations, and cross-suite
transaction dependencies stop approval.

## 14. Verification plan (future implementation only)

No command in this section is executed during plan authoring.

| Command/evidence | Prerequisite and class | Exact scope / policy | Approval status |
| --- | --- | --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_run_protocol_binding.py tests/unit/test_run_protocol_binding_persistence.py` | working `.venv`; unit/offline | carrier regression (0 blocks); P owns 27 allocated blocks with all first-failure variations | mandatory |
| `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_run_repositories.py tests/unit/test_repository_and_uow.py` | working `.venv`; unit/offline | R owns 4 allocated blocks; UoW same-session/cleanup regression contributes 0 | mandatory |
| `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_run.py tests/unit/test_run_operations.py tests/unit/test_run_persistence.py tests/unit/test_run_repositories.py tests/unit/test_run_service.py tests/unit/test_run_entry_service.py tests/unit/test_run_entry_api.py tests/unit/test_run_composition.py` | working `.venv`; unit/offline | exact eight-suite adjacent Run regression; E owns 1 block, C provides 1 secondary proof worth 0; R counts only once | mandatory |
| `.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_mysql_run_protocol_binding.py` | approved MySQL 8 `deviation_protocol_test` via `mysql+asyncmy`; real MySQL | M owns exactly 24 blocks, all assigned acquisition/body-loss/release/precedence variations, V31-B (a,b) current-read visibility, V30-D2/D3 (a,b,c), plus metadata parity | mandatory; zero skips |
| `.\.venv\Scripts\python.exe -m pytest -q tests/integration/test_mysql_run.py tests/integration/test_mysql_run_entry_playthrough.py tests/integration/test_mysql_session_api_persistence.py tests/integration/test_mysql_player_character_run_binding.py` | same real MySQL | existing Run and complete legacy P8 regression | mandatory; zero environment-caused skips |
| `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_run_protocol.py tests/unit/test_run_protocol_persistence.py` | offline | published S1 regression unchanged | mandatory |
| `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_run_protocol_resolution.py` | offline; long-running exhaustive evidence | published S2 regression without sampling or weakened counters | mandatory |
| `.\.venv\Scripts\python.exe -m compileall -q src tests alembic` | working `.venv`; offline | all Python sources | mandatory |
| `.\.venv\Scripts\python.exe -m alembic heads` and `history` | sanitized metadata-only process | one head `20260828_0006`, linear history | mandatory; no DB URL |
| `.\scripts\verify.ps1 -Mode Offline` | sanitized child, no DB/Provider/Live variables | canonical offline suite, compile, dependency, metadata checks, diff | mandatory |
| `.\scripts\verify.ps1 -Mode MySQL` | approved test DB only | canonical real-MySQL suite | mandatory |
| `.\scripts\verify.ps1 -Mode Full` | approved workflow prerequisites; Live flag disabled | complete non-Live repository evidence | mandatory |

The focused MySQL suite must hash every pre-existing legacy row column and
binary payload before upgrade and compare after upgrade; prove migration
upgrade and every section-10 downgrade branch; compare ORM/migration/live
schema; run only its exact M-assigned integration, migration, locking,
constraint, and concurrency blocks from section 13.3; use genuinely separate
connections/tasks; and prove exact winner/loser counts. Each mandatory unit
suite passes its assigned blocks. Their union covers exactly all 56 blocks
across 36 IDs, with aggregate coverage checked against the static allocation
table and exact collected owner/function pairs. No suite alone owns all blocks. A
required test skip, unexpected xfail, missing DB,
wrong driver/database, migration mismatch, or first failure stops approval.
There is no SQLite substitution. Provider, Live, browser, runtime, deployment,
or network evidence is prohibited unless a later separately authorized task
requires it.

## 15. Closed implementation path budget

Only these exact paths may change in a future separately authorized S3
implementation:

| Path | State | Exact S3 responsibility and later-slice boundary |
| --- | --- | --- |
| `src/deviation_protocol/domain/run_protocol_binding.py` | new | immutable legacy/native result and binding carriers; no admission/world/mechanics/public behavior |
| `src/deviation_protocol/infrastructure/run_protocol_binding_persistence.py` | new | frozen stored carriers, private S2 and structural legacy decoders, strict N01-N15 reconstruction and section-9 four-exception wrapping; no row factory or S1/S2 public change |
| `src/deviation_protocol/application/ports.py` | modified | two read contracts and UoW attribute only; no application admission service |
| `src/deviation_protocol/infrastructure/orm_models.py` | modified | exact one-table mapping only; no relationships or S4/S7 columns |
| `src/deviation_protocol/infrastructure/repositories.py` | modified | stored-family classifier and exact strict reads/locks only; no binding add/flush/translation/admission capability |
| `src/deviation_protocol/infrastructure/unit_of_work.py` | modified | same-session adapter exposure only |
| `alembic/versions/20260828_0006_run_protocol_bindings.py` | new | exact additive table, section-10 complete lock/loss matrices and primary-error precedence; no old-row writes |
| `tests/unit/test_run_protocol_binding.py` | new | domain carriers and classification result contract |
| `tests/unit/test_run_protocol_binding_persistence.py` | new | P-assigned codec/canonical/corruption/order and lower-exception variations, exact literal V03 |
| `tests/unit/test_run_repositories.py` | modified | R-assigned read-only port/adapter, CAS preservation, missing-row and closed write/composition/OpenAPI assertions |
| `tests/unit/test_repository_and_uow.py` | modified | same-session wiring and cleanup/cancellation |
| `tests/integration/test_mysql_run_protocol_binding.py` | new | sole direct-row helper; only M-assigned blocks, all lock/loss/error-precedence variations, schema/constraint/concurrency proof |
| `PLANS.md` | modified | implementation lifecycle only |
| `docs/architecture.md` | modified | S3 persistence/classifier architecture synchronization only |
| `docs/run_protocol.md` | modified | implemented/deferred product boundary only |

The independent recount remains exactly 15 paths: six modified/new production
paths, one new migration, five test paths, and three documentation paths. The
test-local helper fits the one listed integration path; the complete structural
legacy algorithm fits the listed infrastructure persistence/repository paths;
no composition change is required because `RunEntryService` and
`SessionService` remain unchanged. No wildcard, directory allowance, package
export, API, Demo, Web, S1, S2, application service, existing migration, or
additional test/document path is permitted. If implementation proves another
path necessary, stop, revise, and independently re-review this plan.

### 15.1 Future implementation sequence

1. Add the exact immutable domain/stored carriers and four exceptions; implement
   the section-9 one-wrapper contract, explicit unreachable lower boundaries,
   and exact direct causes before adding adapter use.
2. Implement N01-N15 once, with the direct S1 dispatcher, profile reacquisition,
   S2 semantic/structural dispatch and canonical reconstruction in that order;
   add independent V03 and all V05/V06 multiple-defect variations in P.
3. Map the unchanged 19-column schema and wire only the two read methods and
   same-session UoW exposure. Implement L01-L04 immutable-preload/complete-Run
   order before later legacy current/controller checks, with V01-A/V13/V14/V29
   input/cause assertions. Keep caller authorization and production writers
   outside S3. Implement R-assigned assertions; run existing E/C unchanged.
4. Create only the frozen migration; implement every acquisition/body-loss/
   release branch and saved-primary cleanup algorithm, including both
   between-DDL state checks and the same-transaction current/locking probe,
   before destructive DDL proof. Add the V31-B old-snapshot interleaving,
   V30-D2/D3 (a,b,c), test-local direct row setup with one add/flush for V02 and all
   independently reset real-MySQL variations owned by M.
5. Run each mandatory assigned unit suite, then the exact M subset with zero
   environment skips. Check the 36-ID/56-block union and one-primary-owner
   invariant, plus all remaining section-14 regressions. Synchronize lifecycle
   documents only after actual implementation evidence and independent review.

This is a future sequence, not authorization or evidence that any code, tests,
migration, or database operation has begun.

## 16. Acceptance criteria and stop conditions

S3 is acceptable only when the exact table, read-only classifier/reconstruction,
Repository/UoW seams, four-exception taxonomy, named-lock downgrade,
concurrency proof, legacy matrix, S3-V01–V36 and all named subcases, old-row
byte preservation, metadata parity, and all mandatory verification above pass
with no weakened S1/S2 evidence; the sole native-row setup is test-local; no
production native writer/admission or caller-authorization inference exists;
and documentation is synchronized. Each mandatory unit suite must pass all
assigned blocks; focused MySQL must pass exactly its M-assigned subset without
environment skips. Their statically allocated union must cover exactly 56
blocks, 36 top-level IDs and every mandated within-block variation. Acceptance
requires every lock/loss branch and primary/cleanup cause assertion, the one
N01-N15 order (including V05/V06 multiple defects), and exactly four S3 types.
It also requires L01-L04 with the immutable object supplied before complete
bound-Run validation; V01-A/V29 successful legacy and V14 contradiction proof;
V31-B (a,b) including the old-snapshot current-read refusal; and V30-D2/D3
(a,b,c), with state-only no-cause failures and independently inspected/restored
partial schemas. These variations add no top-level ID, primary block, or suite.
Migration errors are built-in RuntimeError, not additional S3 classes.

Stop on ambiguous legacy proof; nullable/missing-state mode inference; any old-
row backfill; missing downgrade/data-safety decision; a downgrade writer that
does not share the exact named lock; incomplete genuine real-MySQL concurrency
proof; any production S3 binding write; public/native admission; entry-world
binding; API/OpenAPI change; S1/S2 contract modification; a package export;
missing exact path budget; migration revision conflict; database portability
replacing mandatory MySQL behavior; Provider or external I/O; unresolved
exception ownership; divergent native order; missing or duplicate vector allocation;
cross-vector execution-state dependency; false MySQL-only aggregate coverage;
cleanup replacing a primary error; a snapshot-only downgrade probe; omitted
immutable input to complete bound-Run validation; unclassified between-DDL
state loss; success after connection loss; unresolved S3/S4 boundary; or any `TODO`, `TBD`,
placeholder, “as needed,” optional design, or alternative representation in
the implementation candidate.

## 17. Review and publication gate

There is exactly one operative success verdict for fresh independent read-only
review of these exact three documentation files:

`PHASE_3_3_S3_PERSISTENCE_LEGACY_NATIVE_COMPATIBILITY_PLAN_INDEPENDENT_REVIEW_APPROVED`

Its literal presence here states only the required future reviewer verdict; it
does not approve the candidate. Review must bind the exact baseline, complete
three-file bytes, per-file identities, isolated patches, raw lexicographic
aggregate patch, migration design, decisions, path budget, and stop conditions.
Any byte or relevant baseline change invalidates review. After approval, a
separate exact commit authorization, user manual push, and clean aligned
publication confirmation are required before any implementation task may be
authorized.

The sole future implementation-review verdict is dormant and non-operative:

`PHASE_3_3_S3_PERSISTENCE_LEGACY_NATIVE_COMPATIBILITY_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It cannot operate until this exact plan is approved, separately committed,
manually published, confirmed clean/aligned, and a separately authorized exact
15-path implementation candidate completes all required evidence and fresh
independent review. Neither token grants staging, commit, push, database,
implementation, S4–S7, or other authority. The third corrected candidate remains
unapproved, unstaged, uncommitted, and unpublished; no implementation or
migration has begun.

## 18. Guardrail assessment

Applicable existing rules are `ENV-001`, `ENV-002`, `GIT-001`, `DB-001`,
`AUTH-001`, `STATE-001`, `API-001`, `MODEL-002`, and `PLAY-001`. This plan
applies them and records no confirmed new reusable defect-derived rule.

Guardrail impact: None

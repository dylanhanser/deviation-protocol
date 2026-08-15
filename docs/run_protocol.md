# Run Protocol, Difficulty, and World Profiles

Status: **Approved product design. P3.3-G0 is approved, published, frozen, and
complete. The corrected exact no-migration P3.3-S1 implementation is
independently approved, committed, manually published by the user, and
confirmed clean/aligned at
`6212a760a549920c1c11dcb01e07566945df5556`. Its exact three-document
post-publication status synchronization remains governed by the explicitly
temporal closeout below. P3.3-S2 through P3.3-S7 remain unimplemented and
unauthorized, and Phase 3.3 remains incomplete.**

Phase ownership: **Phase 3.3**

Phase 8 historical planning amendment: **The approved and published Phase 8 Structured
Player Character Run Entry and Minimum Playable Loop planning authority defines
one narrow Session-backed activation path below. Its planning bytes were
published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`, so P8-G0 is complete.
P8-S1 discovery and P8-S2 atomic internal admission are implemented and
published; P8-S2 is closed at `70815b181624e5475d2d978bef0db1ed3b22324e`.
The P8-S3 plan is approved and published at
`e17172ad0a9febe4ec9e3a96e7be8204c9722d29`, and its implementation introduced
normal public `POST /v1/runs` activation. The first independent implementation
review returned `CHANGES_REQUIRED` with five bounded findings, and all five
corrections are complete. A subsequent independent read-only re-review found no
remaining actionable technical defect but formally returned `CHANGES_REQUIRED`
solely for one Medium documentation-synchronization finding. The complete
15-path candidate then received focused independent read-only approval and was
committed and published at `ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`.
P8-S3 is complete. The dedicated P8-S4 implementation plan was independently
approved and committed/published at
`375a2a7ae018c9c9c79272e5de7da703818d1f20`. Its implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
was committed as `187d41ba3035c8d717c2fb2578a805402255d979`, and was
manually published by the user. P8-S4 deterministic Demo parity is complete;
the dedicated P8-S5 implementation plan was independently approved and
committed/published at `dceecaf0d7a33ccde07f519f83997489acd5fc86`, remained
frozen during implementation, and its corrected implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S5_CORRECTED_IMPLEMENTATION_REVIEW_APPROVED`.
The exact eight-path Web implementation was committed and published at
`2ce56a757beed8a3989d38453da3b6d80342ca05`. P8-S5 is complete. The frozen
P8-S6 implementation plan was approved and published at
`4edf2e3341e60632765b85796e8554797c645692`. At the historical P8-S6 candidate
checkpoint, its executable evidence had passed through C21 while those
documentation bytes were unapproved, unstaged, uncommitted, and unpublished;
Phase 8 and the overall project were then incomplete. That candidate-time
status did not mark Phase 3.3, Phase 6, or Phase 7 complete.** This paragraph
preserves the historical P8-S6 candidate record. Current status: P8-S1 through
P8-S6 are implemented and
complete; the closure documentation was independently approved, committed, and
published at `7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`, and no P8-S7 exists.

P4-S1 status: **Minimum Run Core is the historical prerequisite at
`e821cd922b61868097667b12c2b64cf8089a9681` (`feat(run): implement minimum run
core`). P4-S1a is implemented at `748003319ececa548b68b351746afbb2d54c66bb`
and P4-S1b at `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`. The completed binding
is internal-only; no public route exists, the reserved public
`RunService.bind_player_character(...)` command remains rejected, and the
constructible lifecycle remains `pre_first_turn`.**

## Goals

- Give players bounded pre-game control over world pressure and narrative
  presentation.
- Keep objective mechanics, character definition, presentation, and
  relationship atmosphere under separate authorities.
- Resolve all permitted choices before play, then freeze a versioned protocol
  for deterministic use throughout the run.
- Let a narrative model render confirmed state and results without giving it
  authority to invent mechanics, permanent state, or canon.

## Non-goals

- Completing Phase 3.3 or implementing P3.3-S2 through P3.3-S7 through the
  bounded P3.3-S1 foundation or its documentation closeout.
- Letting prose or model preference change resources, success, betrayal, death,
  relationship progression, or permanent facts.
- Replacing scenario-authored facts, character definitions, or engine rules.
- Defining NPC residence progression or production Provider pricing.
- Letting a player freely select an arbitrary world or directly select every
  later world.

## Published Phase 3.3 plan, implemented P3.3-S1, and publication closeout

The repository-specific
[Phase 3.3 Run Protocol implementation plan](phase_3_3_run_protocol_implementation_plan.md)
was originally authored against
`49bb7c9c8f616e4036cbe56549f9621544ebf84b`. Its first independent review
returned `CHANGES_REQUIRED`; the bounded B1-B4 correction later received
`PHASE_3_3_RUN_PROTOCOL_IMPLEMENTATION_PLAN_INDEPENDENT_REVIEW_APPROVED`, was
separately committed and user-published as
`76064d200d1aa5af7cddff22d33acb03e608e598`, and was confirmed at a clean,
aligned baseline. P3.3-G0 is approved, published, frozen, and complete.

The frozen plan records the exact repository compatibility boundary without
changing current legacy runtime behavior:

- existing Phase 8 revisions 1/2/3, immutable character binding, first Session
  participation, Session initialization family, V1 evidence/fingerprints/
  replay, recovery, and production/Demo/Web/Dynamic Narrative compatibility are
  legacy behavior;
- existing rows are valid and replayable only when trusted stored legacy proof
  passes its current strict decoder and cross-row integrity checks. They receive
  no synthesized protocol, profile, world, visit, region, or world state and no
  rewrite, backfill, refingerprint, relabel, default, or Provider/canon authority;
- caller-controlled absence cannot select legacy handling;
- a Phase-3.3-native Run will require explicit trusted server-owned versioned
  state, an exact validated and authorized protocol/profile binding, and—before
  native admission—an explicit authored entry-world ID/version. Missing,
  malformed, unknown, contradictory, or incompatible state fails closed;
- `scenario_id` remains scenario-definition identity only. It is never world,
  visit, region, protocol, or profile identity.

The plan's no-migration P3.3-S1 representation has exactly one initial envelope
schema, `run-protocol-envelope/v1`. The independently approved and published
implementation supplies that representation, strict original-state validator,
canonical encoder, v1 decoder, trusted version dispatcher, golden and boundary
evidence, and no-I/O in-memory stored-record conversion/reconstruction
boundary. It contains only an exact versioned profile reference and the
approved presentation values `world_tone`, `reality_boundary`, and
`relationship_overlay`. It contains no numeric engine values, defaults,
overrides, catalogue definitions, scenario/world/visit/region fields, prose,
secrets, or Provider output. Representation validity remains separate from
profile authorization, lookup, and deterministic resolution, and S1 creates no
durable Run Protocol.

The implementation's first independent read-only review returned `CHANGES_REQUIRED`
for four findings: missing operative S1 review authority, missing exact
pre-normalization scalar-type enforcement, synthetic 1,024/1,025 canonical
branch evidence incorrectly characterized as genuine valid-envelope evidence,
and stale Phase 8/Dynamic Narrative status text in `architecture.md`. The
authority defect and ceiling clarification were independently approved and
published in commit `a722dbf7f07e6e55cd4918a80b5153d6043f2100`. That amendment
was separately committed, manually pushed by the user, and confirmed as the
published predecessor authority.

The corrected exact seven-path implementation preserved the complete frozen S1
contract. Its carrier validators require exact `str` for profile ID and schema
literal and exact `int` for profile version before Pydantic normalization, so
equal-valued subclasses, `StrEnum`, `IntEnum`, and Boolean-as-integer inputs fail
both direct construction and original-state revalidation. Genuine real-encoder
maximum evidence uses the frozen 128-byte `A` profile ID, maximum signed-positive
64-bit profile version, `balanced`, `deviant`, and `charged`; it is exactly 329
bytes with SHA-256
`0e0b1f498e1bf51656f1c5e5c742074e864da9678964c048087f52bdf5066e78`.
The internal 1,024/1,025 canonical-guard test is defensive branch-isolation
evidence only, while the public decoder retains genuine raw-input boundary
evidence at both sizes. Neither 1,024-byte ceiling changes.

The historical pre-correction seven-path patch identity of `80,019` bytes and
SHA-256 `064dd425f1b412495ddbf62e6995b18d1266c5b0b7dc2ab7d12b41c6e58bfe25`
is non-operative after correction. The corrected candidate received
`PHASE_3_3_S1_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED` and was committed
byte-identically as the one-parent non-merge commit
`6212a760a549920c1c11dcb01e07566945df5556`, directly after `a722dbf7`, with
exact subject `feat(run): implement Phase 3.3 S1 protocol envelope`. The user
manually pushed `a722dbf..6212a76, main -> main`. Public `main` was confirmed
identical to that commit, and local `main` and local `origin/main` were aligned
at ahead/behind `0/0`, with a clean worktree and empty index. The implementation
publication is complete and awaits no further implementation review, commit,
push, or published-baseline confirmation.

The published implementation inventory is exactly:

| Kind | Exact path | Diff |
| --- | --- | ---: |
| Documentation | `PLANS.md` | `+99/-46` |
| Documentation | `docs/architecture.md` | `+107/-18` |
| Documentation | `docs/run_protocol.md` | `+90/-26` |
| Production | `src/deviation_protocol/domain/run_protocol.py` | `+463/-0` |
| Production | `src/deviation_protocol/infrastructure/run_protocol_persistence.py` | `+85/-0` |
| Tests | `tests/unit/test_run_protocol.py` | `+760/-0` |
| Tests | `tests/unit/test_run_protocol_persistence.py` | `+327/-0` |

That is exactly seven files, 1,931 insertions, 90 deletions, and a complete
binary-safe patch of 95,987 bytes with SHA-256
`30e592f751937786d58f64e90a36aa0355b66803c7fb06eafea96f4ab7371e23`.

The former authoring verification (`126` focused tests, `222` adjacent Run
tests, and Offline `2,463 passed, 182 skipped`) is historical evidence for the
pre-correction bytes.

The final corrected and independently reviewed evidence accepted for the exact
published implementation is 141 focused P3.3-S1 tests, 222 tests across the
eight adjacent Run suites, passing `compileall`, and canonical Offline
verification at `2,478 passed, 182 skipped`. Dependency consistency passed.
Alembic `heads` and `history` were metadata-only at head `20260729_0005`, with
a linear migration graph from `20260719_0001` through `20260729_0005`. There
was no database connection and no Provider, Live, or network operation. These
results are accepted publication evidence, not merely authoring evidence, and
they are not rerun by the later documentation-only closeout task.

### Exact implemented and deferred boundary

The exact 22-symbol S1 contract and public signatures remain frozen. The 18
domain symbols own only the exact envelope epoch and trusted record-version
constants, profile ID/version/reference carriers, three presentation enums,
strict v1 envelope, validation and unsupported-version exceptions, original-
state validator, canonical encoder, v1 decoder, and trusted version dispatcher.
The four infrastructure symbols own only the frozen slotted no-I/O stored
carrier, stored-record integrity exception, deterministic storage conversion,
and detached reconstruction. Domain remains independent of infrastructure.

The published implementation preserves strict exact types, UTF-8 without BOM,
NFC, duplicate-key rejection, byte-identical canonical compact JSON, positive
signed-int64 profile versions, closed enum values, exact corruption taxonomy,
both 1,024-byte ceilings, detached no-I/O reconstruction, and no fallback,
repair, upgrade, downgrade, coercion, or default. The exact 193-byte golden and
329-byte genuine maximum identities above remain normative S1 evidence. Raw
1,024/1,025 decoder tests are genuine input-boundary evidence; the unreachable
canonical guard test remains defensive branch isolation only.

P3.3-S1 does not implement durable Run Protocol persistence; an ORM model;
database table or column; migration; repository or Unit of Work integration;
Run binding; profile catalogue, lookup, default, override, or deterministic
resolution; objective numeric mechanics; native Run admission; entry-world
freezing; public API or projection; Demo, Web, or Provider integration; world,
visit, region, revisit, progression, or continuity behavior; identity or memory
schema; or P3.3-S2 through P3.3-S7. It does not implement the complete Run
Protocol or complete Phase 3.3.

Legacy Run revisions 1/2/3 remain unchanged. Their existing strict proof,
binding, participation, V1 evidence, replay, recovery, production, Demo, Web,
and Dynamic Narrative behavior remains unchanged. No legacy Run receives
synthesized protocol, profile, world, visit, region, or world-state authority.
`scenario_id` remains scenario-definition identity only.

Phase 3.4 remains later. Phase 6 remains paused under
`PHASE_6_NO_CURRENT_EXECUTABLE_SURFACE`, and Phase 7 remains inactive. Phase 8
is complete at P8-S6 and no P8-S7 exists. Dynamic Narrative corrective and
publication work remains closed. Production Provider Distribution remains
deferred.

### Post-publication status-synchronization closeout

At the 2026-08-15 authoring checkpoint represented by the exact closeout
candidate bytes, only `PLANS.md`, `docs/architecture.md`, and this document are
modified; the candidate is unapproved, unstaged, uncommitted, and unpublished.
This statement is explicitly commit-bound candidate-time history, not a durable
claim about the later disposition of byte-identical files.

The exact next action at that checkpoint is fresh independent read-only review
of the complete three-document candidate. After a successful review, the user
must separately authorize the exact three-path local documentation commit. The
user then separately controls the manual push, after which the repository must
receive a clean aligned published-baseline confirmation. Only after that exact
review/commit/push/confirmation sequence may P3.3-S1 be called fully closed.
Once the same exact bytes complete the sequence, these published words durably
record that closure; no second status-synchronization task is required.

After P3.3-S1 closure, P3.3-S2 becomes the next sequential planning subject but
remains unauthorized. Its dedicated commit-sized plan must be separately
authored, independently approved, committed, manually pushed by the user, and
confirmed at a clean aligned published baseline before implementation. This
closeout selects or authorizes no P3.3-S2 decision, plan content, or code.

### Sole operative independent-review gate for this closeout

There is exactly one operative success token for independent review of this
exact three-document closeout candidate:

`PHASE_3_3_S1_POST_PUBLICATION_STATUS_SYNCHRONIZATION_INDEPENDENT_REVIEW_APPROVED`

The token is valid only when a fresh independent read-only review binds all of
the following:

1. baseline `6212a760a549920c1c11dcb01e07566945df5556` on `main`;
2. exactly `PLANS.md`, `docs/architecture.md`, and `docs/run_protocol.md`, with
   no fourth path;
3. the final line, byte, and SHA-256 identity of each of those three files and
   the complete lexicographically ordered binary-safe three-path patch byte
   count, SHA-256, and bytes, all measured after the last authoring change and
   supplied externally with the review prompt;
4. the complete P3.3-G0, first-review, predecessor-amendment, corrected-
   candidate, implementation-approval, exact-commit, manual-push, and clean
   published-baseline lifecycle facts recorded here;
5. byte preservation of the frozen plan at 1,233 lines, 83,331 bytes, and
   SHA-256
   `09ef2ffe9fc03fc60cd069df116463b2cc27d08f50fbbddc658b28d975683e1b`,
   plus byte preservation of the two S1 production and two S1 test files at
   commit `6212a760`; and
6. preservation of the exact implemented/deferred boundary and the absence of
   any P3.3-S2 or later-slice authority.

Any byte change to an approval-bound closeout document after review invalidates
the token and requires new identities and fresh independent read-only review.
The token grants no editing, staging, commit, push, publication, implementation,
or P3.3-S2 authority. Even after approval, a separate explicit authorization
is required for the exact local three-path documentation commit, and the user
performs every push. Every historical implementation/plan/amendment verdict,
authoring-complete label, differently scoped success-looking label, subset
review, failure, or changes-required result is non-operative for this closeout
and cannot approve it.

The published frozen planning allocation is exactly:

1. **P3.3-G0 — Plan and compatibility freeze candidate**;
2. **P3.3-S1 — No-migration protocol/profile foundation**;
3. **P3.3-S2 — Deterministic profile resolution**;
4. **P3.3-S3 — Persistence and legacy/native compatibility**;
5. **P3.3-S4 — Native Run admission and entry-world freezing**;
6. **P3.3-S5 — Objective mechanics application and trusted prompt-context compilation**;
7. **P3.3-S6 — Public API, Demo, Web, projection, and recovery parity**; and
8. **P3.3-S7 — Later worlds, visits, regions, revisits, progression, and persistent world continuity**.

P3.3-S7 belongs to Phase 3.3 and is unrelated to the nonexistent P8-S7.
Phase 8 remains implemented and complete at P8-S6. Publication of this
allocation did not authorize any implementation slice. P3.3-S1 was separately
authorized, independently approved, and published as the bounded foundation
described above. P3.3-S2 through P3.3-S7 remain unimplemented and unauthorized.
The only open S1 governance at the recorded authoring checkpoint is the exact
three-document closeout sequence above; it grants no later-slice authority.

P3.3-S5 must receive its own bounded implementation plan and independent
review before implementation. It owns deterministic application by
server-owned policies of `resource_pressure`, `social_trust`,
`consequence_severity`, `information_opacity`, and `conflict_intensity`, with
objective mechanics tested independently from prompt construction. It also owns
a deterministic, pure or side-effect-free, Provider-independent compiler from
validated trusted protocol state to canonical context bytes or one exact
deterministic structured representation fixed by that plan. It must not call a
real Provider. Provider calls remain outside database transactions and locks.

The P3.3-S5 compiled context grants no outcome, resource, relationship, death,
world-selection, permanent-state, or canon authority. Presentation changes
permitted expression only. Regression evidence must prove that model output
cannot create, change, or override mechanics or canon. Relationship overlay is
presentation-only and cannot mutate Phase 3.4 relationship or residence state.

## Minimum Run-core prerequisite for player-character Phase 4

The complete Run Protocol remains approved product design and is not complete
or durably implemented. The independently approved and published P3.3-S1
foundation now supplies only the standalone no-migration boundary described
above. Before Structured Player Character P4-S1, only the smaller
prerequisite specified by the
[Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md)
has been implemented, independently finally approved, committed, and pushed.

That prerequisite freezes:

- distinct strict opaque `RunId` and `ContinuousStoryLineId` carriers;
- one Run permanently owning exactly one continuous story line, rather than a
  generalized container for unrelated lines;
- a canonical current Run record, immutable Run revisions, and a positive
  monotonic `RunStateVersion` with compare-and-swap persistence;
- the closed minimum lifecycle values `pre_first_turn`, `active`, `completed`,
  and `terminated`;
- a separate immutable Run-owned Session participation record, with no Run,
  line, or character-binding column added to `game_sessions`;
- a Run application service as the one transaction owner for minimum Run
  mutations and the future character binding; and
- an all-null authoritative storage seam for the future exact
  player-character and applicable contract/revision reference.

`pre_first_turn` and `active` are active continuous-story-line states for
binding exclusivity. `completed` and `terminated` are non-active historical
states. The minimum core creates only `pre_first_turn`; it does not implement
the transition to any other lifecycle value. When a later authorized terminal
transition has a character binding, Run authority must make the binding
historical in the same atomic change.

The minimum aggregate is allocated before the first turn and therefore does
not pretend that a resolved protocol, entry world, current visit, or scenario
already exists. The existing lifecycle below remains authoritative: before
the first turn can begin, the resolved protocol plus
`entry_world_id`/`entry_world_version` must receive their Run binding and be
frozen. Full Phase 3.3 implementation continues to own that transition,
world/visit identity, later-world selection, revisits, and world-line rules.

Session participation is created only through trusted Run orchestration.
Caller-supplied Session data cannot select or replace a Run; participation
does not grant character ownership or controller authority. Multiple distinct
trusted Sessions may participate in the same Run, while one Session cannot
participate in conflicting Runs. This record does not activate public resume,
reconnect, cross-tab, browser-restart, or multi-device behavior.

The completed minimum Run core and its production composition remain internal.
The reserved character-binding seam was populated by the completed separately
authorized P4-S1 work. That internal completion does not activate a public
binding route or the `active` lifecycle transition.

## Phase 8 Session-backed minimum admission

Status: **Implemented and complete through independently approved, committed,
and published P8-S6 closure at
`7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`; no P8-S7 exists**

The explicit Phase 8 allocation and detailed implementation boundary are owned
by the
[Structured Player Character Run Entry and Minimum Playable Loop plan](structured_player_character_run_playable_loop_plan.md).
The original exact seven-document planning candidate received
`STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED` and was
committed and published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`.
Later modifications to the canonical planning bytes require fresh exact-byte
independent review before a separately authorized documentation commit; that
commit precedes user publication and clean published-baseline confirmation.
P8-G0 is complete and published. P8-S1 eligible-character discovery is
implemented, accepted, committed, and published. P8-S2 atomic internal Run
entry is implemented, accepted, committed, and published at
`70815b181624e5475d2d978bef0db1ed3b22324e`; its implementation and F1/F2/F3
evidence are closed, and P8-S2 is not being reopened. The
[P8-S3 implementation plan](structured_player_character_p8_s3_implementation_plan.md)
was independently approved and committed/published at
`e17172ad0a9febe4ec9e3a96e7be8204c9722d29`. Its implementation reaches
the existing atomic admission authority through normal production composition
and public `POST /v1/runs`, with real-MySQL replay/no-write decisions and the
canonical Session terminal journey verified. The API owns no transaction and
the Run remains active and immutably bound after scenario settlement.
Its five bounded first-review corrections are complete. The subsequent
independent read-only re-review found only the Medium documentation-
synchronization finding described above and returned `CHANGES_REQUIRED`. The
complete 15-path candidate later received focused independent read-only approval
and was committed and published at
`ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`. P8-S3 is complete. P8-S4 Demo
parity was then implemented under the dedicated approved plan, independently
approved with
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
committed as `187d41ba3035c8d717c2fb2578a805402255d979`, and manually
published by the user. P8-S4 is complete. The dedicated
[P8-S5 implementation plan](structured_player_character_p8_s5_implementation_plan.md)
was independently approved and committed/published at
`dceecaf0d7a33ccde07f519f83997489acd5fc86`, remained frozen during
implementation, and its corrected implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S5_CORRECTED_IMPLEMENTATION_REVIEW_APPROVED`.
The exact eight-path Web implementation was committed and published at
`2ce56a757beed8a3989d38453da3b6d80342ca05`. P8-S5 is complete. P8-S6
fresh evidence now confirms the unchanged Session-backed Run protocol. The
designated MySQL 8 production-ASGI journey entered one active, immutably bound
Run and played all 19 authoritative actions to Session settlement; replay
produced no extra Provider call or durable write, and the Run remained active
and bound at state version 3 after the terminal `ENDED`/`RESOLVED` View. The
deterministic Demo journey separately completed the same canonical action,
request-status, authoritative-View, and terminal sequence with exactly four
completed guarded Provider calls. Focused Web evidence confirmed Session ID
storage before the first View GET, a single action POST, confirmed-202 GET-only
status polling, authoritative View refresh, and no automatic replay. Those
results and the synchronized closure documentation were independently approved,
committed, and manually published at the P8-S6 closure baseline. They complete
Phase 8 only; they do not implement or approve Phase 3.3, Phase 6, or Phase 7.

### Narrow authority amendment

Phase 8 authorizes one composite trusted operation for the current
Session/scenario engine:

```text
owned active unbound Player Character
  -> create Run revision 1 at pre_first_turn
  -> bind exact character/reference in revision 2
  -> create one existing gameplay Session
  -> attach first Session participation in revision 3
  -> change Run lifecycle to active in that same revision
  -> one Run-entry-owned UnitOfWork commit
```

The first participation retains `ATTACH_SESSION` as its Run mutation kind. No
new Run lifecycle value or mutation token is selected. The existing active
binding and `ApplicableCharacterReference` remain exact and immutable across
activation. A Run may not change character through any Phase 8 surface.

This is a narrow compatibility amendment to the earlier rule that an active
Run must already have a full resolved protocol and entry-world binding. The
amendment applies only to Phase 8 Session-backed Runs using the current
implemented scenario lifecycle. It does not implement, simulate, or claim:

- a resolved/frozen Run Protocol;
- `entry_world_id`, `entry_world_version`, world, visit, or region identity;
- world/profile parameters or permitted overrides;
- later-world selection, revisits, world-line movement, or progression; or
- Phase 3.3-native Run acceptance.

The request's `scenario_id` remains the existing versioned scenario identity
and MUST NOT be relabelled as a world or visit. The server selects the
scenario's already validated default static character definition for current
Session initialization. That definition remains distinct from the Run-bound
Structured Player Character.

When full Phase 3.3 is implemented, its plan must explicitly preserve,
version, or migrate these legacy Session-backed active Runs before applying a
Phase 3.3-native protocol/world requirement to them. Phase 8 selects no future
column, migration, backfill, or compatibility representation.

### Admission authority and transaction

The public client may submit only an owned Player Character ID, its expected
current revision, one scenario selected from the existing bounded public
catalogue, and an idempotency key. It cannot submit Run, line, Session, world,
visit, lifecycle, binding, applicable-reference, static character-definition,
state, or authority data.

One application entry service resolves principal/controller authority, locks
and validates the exact active unbound character, evaluates compatible replay
before new-operation stale/eligibility rejection, creates all identities and
authoritative state server-side, and commits the Run revisions/current rows,
binding, existing Session initialization family, participation, and successful
receipts in one UoW. Repositories flush and never commit. No nested service
commit, generic retry, compensation, outbox, saga, or uncertain-commit recovery
is permitted.

Concurrent admissions for one character serialize at the Player Character
lock and retain the unique active-character database backstop. Exactly one new
Run may commit. The loser receives exact replay, incompatible-key conflict, or
already-bound ineligibility without a second Run, Session, participation, or
binding.

Published P8-S4 makes this same established admission service reachable in the
deterministic Demo through process-local Player Character, Run, receipt,
participation, and Session repositories sharing one UoW publication boundary.
It does not originate revisions 1/2/3 or activation. Exact entry replay returns
the committed Run/Session result without another mutation or generator
consumption, while conflicts and rollback publish no partial authority and do
not reuse an already emitted deterministic identity.

### Progression, completion, recovery, and exit

After admission, the existing Session View/action/request-status protocol is
the only Phase 8 progression authority. Current stale, pending, uncertain,
Provider-failure, rollback, and same-tab recovery rules remain unchanged.

Published P8-S5 now connects the primary Web journey to the existing public
Player Character discovery/create and Run-entry contracts, then to the existing
Session progression protocol. It does not use the legacy `POST /v1/sessions`
route for that journey; the route remains available for existing uses. A
validated Run-entry success is persisted through the existing same-tab Session
recovery record before the authoritative View is loaded. Thereafter safe View
recovery is GET-only and never replays Run entry. Mutation uncertainty retains
the exact pre-POST idempotency key/body pair for explicit manual retry only,
with no automatic retry, duplicate in-flight send, stale-completion authority,
or disclosure of the key or private Run authority.

The accepted rendered provider-backed action path continues through the
established `202` response, request-status `PENDING`, request-status
`COMMITTED`, and authoritative View refresh. Existing terminal behavior remains
the Session/scenario behavior below; P8-S5 adds no Run terminal transition.

In Demo, a failed View read after committed admission likewise does not undo
the Run, binding, Session, participation, activation, or receipts. The returned
Session identity remains the authority for retrying the existing View read; no
Demo-specific recovery operation exists.

An existing scenario ending is not a Run ending. `ENDED`, `RESOLVED`, and
`FAILED` remain Session/scenario projections. The Run remains `active`, its
character binding remains active, and participation remains immutable. Phase 8
does not implement `completed`, `terminated`, binding historicalization,
later-Session attachment, later-scenario admission, Run resume/discovery, or
line continuation. Clearing browser/sessionStorage state is client-only and
never mutates the Run or character.

### Phase relationship

Phase 6 subject-reference hooks are not a prerequisite because Phase 8 creates
no new memory/relationship/consequence fact. Phase 7 remains separately
allocated and unimplemented; Phase 8 owns only its own bounded final evidence
and status slice. Neither allocation is absorbed, reinterpreted, or marked
complete.

The current schema and migration `20260729_0005` already admit Run lifecycle
`active`, the three existing mutation kinds, active binding, Session
participation, CAS, and the required receipt families. Phase 8 therefore
authorizes no ORM or migration change. A contrary implementation finding is a
plan stop condition.

## Responsibility separation

The pre-game UI may expose these choices together, but their internal authority
remains separate:

| Concern | Authority | Effect |
| --- | --- | --- |
| Difficulty/world rules | Engine-owned world profile | Objective resources, trust environment, failure consequences, information opacity, and conflict incentives |
| Character definition | Versioned character definition | Abilities, knowledge boundaries, personality, and viewpoint |
| Run Protocol | Frozen structured presentation contract | How confirmed state and results are narrated |
| Relationship atmosphere | Presentation overlay | Tension and expression only; never objective relationship progression |

Difficulty may recommend presentation defaults, and a character may recommend
viewpoint-compatible defaults. Neither merges its authority into the Run
Protocol. Relationship atmosphere is not world tone.

## World selection and ordering

Status: **Approved product design — not implemented**

- At the beginning of a run, the player may select the entry world only from a
  small, explicitly authored set of eligible initial worlds.
- The player cannot freely select an arbitrary world.
- Once selected and the run begins, `entry_world_id` and
  `entry_world_version` are frozen for that run and cannot be changed.
- The player does not select later worlds directly.
- Later worlds are selected dynamically by the engine from the currently
  eligible world pool.
- Dynamic selection is deterministic and reproducible from engine-owned state
  and seed. It does not rely on uncontrolled model randomness.
- Selection may consider prerequisites, completed worlds, current run state,
  difficulty/world profile, major hidden-setting requirements, and only the
  important-NPC recovery predicate boundary defined below.
- Pure randomness must not prevent required narrative progression or recovery
  of a major hidden setting or important NPC.

`death_certificate_v1` is the current canonical Demo and vertical-slice
scenario. It is not permanently designated as the production entry world.

The exact eligible initial-world catalogue, weighting algorithm, anti-repeat
rules, progression constraints, and priority-injection rules remain Deferred.

### Important-world revisits

Status: **Approved product design — not implemented**

- An explicitly authored important world may remain eligible for later engine
  selection after the player has already visited it.
- The player cannot directly choose or request a later-world revisit and cannot
  approve, veto, or otherwise authorize an engine-proposed revisit. The
  complete revisit decision is engine-owned.
- Revisiting a world is not automatically a scenario restart or state reset.
- Confirmed world state, important NPC state, player-caused consequences,
  discovered facts, and unresolved events persist unless an engine-authorized
  world-line transition explicitly changes them.
- A world's first accessible region does not define the power level, scale, or
  narrative depth of the entire world.
- An initial world may appear beginner-oriented only because the player begins
  in a remote, protected, or peripheral region.
- Later visits may reveal previously inaccessible regions, major factions,
  powerful inhabitants, hidden history, and higher-level conflicts within the
  same persistent world.
- Re-entry must provide meaningful progression, revelation, or consequence
  rather than unrestricted repetition, duplicated rewards, or resource
  farming.
- The engine may prioritize an important-world revisit when required for:
  - a major hidden-setting revelation;
  - an important NPC's recovery or later arc;
  - unresolved world consequences;
  - access to a newly eligible region;
  - a major scenario or world-line event.
- Ordinary worlds do not require later recovery merely because they were
  previously visited.
- Anti-repeat rules and random weighting must not permanently exclude an
  important world whose authored recovery conditions have become true.
- Re-entry eligibility, persistent world state, region unlocking, and recovery
  priority are engine-owned.
- The model must not independently return the player to a world, reset world
  state, unlock a region, or invent a required recovery event.

### Important-NPC recovery predicate boundary

P3.3-S7 recovery priority is engine-owned. It may consume only an
already-authorized logical-NPC-identity predicate and authored-world predicate
published by their owning authorities before the applicable P3.3-S7
subdivision. It must not derive logical identity from runtime `npc_id`, treat a
scenario NPC definition as cross-scenario identity, or match by name,
appearance, role, template, model output, or semantic similarity. It must not
create counterpart, reincarnation, copy, successor, replacement, or other
continuity relations.

P3.3-S7 recovery priority must not read or mutate relationship state, golden
memory, cross-scenario NPC persistence, Phase 6 subject-reference hooks, an
identity-resolution schema, or a memory schema. If no already-authorized
predicate exists, important-NPC priority is unavailable and selection continues
deterministically using other authorized eligibility and progression inputs.
Absence must not manufacture identity, block unrelated valid selection, imply a
Provider decision, promote a runtime NPC, or pull Phase 3.4 or Phase 6 into
Phase 3.3. Future integration requires a separately published identity/memory
authority and a fresh bounded P3.3-S7 subdivision review.

The design distinguishes three conceptual identities without defining current
schema fields:

1. the persistent identity of an authored world;
2. an individual visit or run-local entry identity; and
3. the region or scenario content accessible during that visit.

These identities prevent a revisit from being treated as a fresh copy of the
world while allowing each visit to expose different authored content.

## Main pre-game dimensions

### World tone

- `Grim`
- `Balanced`
- `Heroic`

### Resource pressure

- `Scarce`
- `Fluid`
- `Generous`

Resource pressure becomes an engine-owned world/difficulty input. A model may
narrate its confirmed effects but cannot directly add, remove, restore, spoil,
or otherwise modify resources.

### Reality boundary

- `Lawful`
- `Deviant`
- `Chaotic`

### Relationship atmosphere overlay

- `off`
- `veiled`
- `charged`

This overlay changes presentation only. It cannot create affection, change a
relationship stage, satisfy a relationship flag, or unlock residence.

## Difficulty/world parameters

The engine owns these parameters:

- `resource_pressure`
- `social_trust`
- `consequence_severity`
- `information_opacity`
- `conflict_intensity`

Profiles provide defaults. Permitted player overrides occur only before the run
starts.

### Extreme — Silent Hunting Ground

- Extreme scarcity.
- Severe consequences.
- Opaque information.
- Very low default social trust.
- High cooperation cost.
- High betrayal incentives.
- Dark-forest-like conflict.

### Standard — Fragile Alliance

- Local scarcity.
- Trust must be earned.
- Cooperation and betrayal are both meaningful.
- Betrayal is possible but not universal.

### Easier — Open Expedition

- Sufficient resources.
- Trade, rescue, and cooperation are more common.
- Betrayal incentives are lower.
- Conflict intensity is reduced, but narrative conflict still exists.

## Determinism and authority

- Difficulty controls objective mechanics and world conditions.
- Character definition controls abilities, knowledge, personality, and
  viewpoint.
- Protocol presets control presentation.
- Difficulty and character may supply recommended defaults.
- Player-approved overrides are resolved before the first turn.
- The resolved protocol is versioned and frozen when the first turn begins.
- Fluid behavior is resolved deterministically by the engine using state and
  seed.
- The model does not perform its own uncontrolled random selection.
- The model does not invent resource loss, betrayal, death, permanent state
  changes, or major canon facts.
- `Grim` may intensify language, but cannot make a valid potion expired or an
  on-time rescue late unless the engine established that fact.
- `Heroic` may emphasize opportunity and reversal, but cannot manufacture
  success.
- `Chaotic` may add dreamlike, surreal, or limited meta presentation.
- Permanent canon arising from `Chaotic` presentation requires engine
  authorization and world-line consistency validation.
- Relationship atmosphere affects tension and expression, not objective
  relationship state.

These rules preserve the existing authority principle: the model narrates
confirmed state and results; the engine owns objective mechanics and permanent
state.

## Structured prompt input

The accepted direction is:

```text
difficulty + character + permitted pre-game overrides
  -> resolved, versioned Run Protocol
  -> fixed structured prompt prefix
```

A proposed representation is:

```text
[RUN_PROTOCOL v1]
difficulty_profile=<resolved profile>
character_id=<resolved character>
world_tone=<grim|balanced|heroic>
resource_pressure=<scarce|fluid|generous>
social_trust=<resolved value>
consequence_severity=<resolved value>
information_opacity=<resolved value>
conflict_intensity=<resolved value>
reality_boundary=<lawful|deviant|chaotic>
relationship_overlay=<off|veiled|charged>
preset_version=1
[/RUN_PROTOCOL]
```

The structured, versioned boundary is accepted. The frozen P3.3-S1 plan fixes
the exact `run-protocol-envelope/v1` representation and the published S1
foundation implements its standalone codec/validation evidence. This does not
select or implement the illustrative prompt block above; no `RUN_PROTOCOL`
block exists in the implemented prompt today.

## Lifecycle

1. The game offers engine-approved profile, character, and eligible
   initial-world choices.
2. Difficulty and character definitions supply defaults or recommendations.
3. The player selects one eligible entry world and applies only permitted
   pre-game overrides.
4. The engine validates and resolves the complete profile.
5. The resolved protocol, `entry_world_id`, and `entry_world_version` receive
   their run binding and are frozen at the first turn.
6. Each turn uses the frozen protocol with current engine-confirmed state.
7. The engine resolves any fluid behavior deterministically from state and
   seed; the Provider only renders the permitted presentation.
8. When a later world is required, the engine deterministically selects it from
   the eligible pool while preserving required progression and recovery.
9. Replay uses the same frozen protocol, authoritative state, and deterministic
   inputs.

## Deterministic requirements

- Resolution order, defaults, override precedence, and validation are stable.
- No setting depends on unordered collection iteration, wall-clock time, or a
  Provider-selected random value.
- Entry-world identity remains frozen, and later-world selection is
  reproducible from engine-owned state and seed.
- Required progression and engine-confirmed major-setting constraints take
  priority over pure random weighting. Important-NPC priority participates only
  when the already-authorized logical-identity and authored-world predicates
  required by the boundary above exist.
- The stored/frozen representation is sufficient to reproduce presentation
  inputs for a run.
- Objective results are reproducible independently of prose variation.
- A missing, unknown, incompatible, or mutated protocol fails explicitly; it
  does not silently select new defaults mid-run.

## Implementation acceptance criteria

Phase 3.3 is acceptable only when:

1. The engine has a validated, versioned world/difficulty profile and frozen
   Run Protocol boundary.
2. Profile defaults and permitted overrides are resolved before the first turn.
3. Objective parameter effects are implemented and tested independently from
   presentation settings.
4. Character authority remains separate from difficulty and presentation.
5. Relationship atmosphere cannot mutate objective relationship state.
6. Identical state, seed, character, and resolved settings produce identical
   engine-owned outcomes.
7. Prompt construction uses only the validated frozen representation and does
   not grant model authority over resources, betrayal, death, or canon.
8. `Grim`, `Heroic`, and `Chaotic` authority limits have regression coverage.
9. Current scenarios retain their fixed facts unless a trusted engine event
   changes a mutable fact.
10. Entry-world selection is limited to an authored eligible set, freezes the
    selected ID/version, and later-world selection is deterministic,
    reproducible, and cannot strand required progression or recovery.
11. Important-world revisits preserve confirmed state and consequences, expose
    only engine-authorized regions/content, resist reward farming, and cannot
    be permanently excluded after authored recovery conditions become true.
12. Documentation and phase status are synchronized before audit or completion.

## Deferred questions

- Successor-version compatibility, durable schema/migration, and later decoder
  policy beyond the frozen standalone v1 representation.
- Exact numeric/value ranges for the five engine-owned parameters.
- Profile-to-parameter default values.
- Which overrides are offered for each game mode or character.
- Compatibility and migration policy for future protocol versions.
- World/profile discovery and unlock policy.
- Exact eligible initial-world catalogue.
- Later-world weighting algorithm and general anti-repeat rules.
- Progression constraints and priority-injection rules for required story
  progression and major hidden settings; important-NPC integration remains
  unavailable until separately published owning authorities supply the required
  logical-identity and authored-world predicates.
- Important-world designation schema.
- Revisit limits and cooldowns.
- Region-unlock rules.
- Reward anti-farming rules.
- Recovery-priority weighting.
- World-line transition representation.
- How world-line consistency validation represents permanent canon approved
  after `Chaotic` presentation.

## Related documents

- [Project roadmap](../PLANS.md)
- [Minimum Run Core Implementation Plan](minimum_run_core_implementation_plan.md)
- [Narrative Provider boundary](narrative_provider.md)
- [NPC Relationship and Temporary Residence](npc_relationship_residence.md)
- [Current scenario specification](scenarios/death_certificate_v1.md)

## Experimental Dynamic Narrative Vertical Spike boundary

The DNVS candidate reuses the current implemented Run-entry operation and its
one active Player Character binding. It creates the Session, participation,
snapshot, initial event, and declared runtime NPCs atomically, assigning NPC
instance IDs from scenario declaration order as `scenario-npc-1..N`. Dynamic
story state remains Session/GameState authority; Run identity, continuous-story
line identity, participation, binding, lifecycle, and ownership remain unchanged
and are revalidated on every reconstruction.

This experimental composition neither implements nor amends the deferred formal
Run Protocol described in this document. It is outside Phase 8, creates no
P8-S7, and leaves completed P8-S6/Phase 8, paused Phase 6, and inactive Phase 7
exactly as recorded in `PLANS.md`. The DNVS and its bounded autonomous
improvement lifecycle are closed; neither supplies Phase 3.3 implementation
evidence or Provider/world authority.

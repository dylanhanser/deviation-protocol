# Structured Player-Character P4-S1 Implementation Plan

## Status and authority

Status: **Bounded candidate implementation plan; not yet independently
approved, not frozen, not implemented, and review pending.**

Baseline: `e821cd922b61868097667b12c2b64cf8089a9681`
(`feat(run): implement minimum run core`). Minimum Run Core is the completed,
independently finally approved, committed, and pushed prerequisite. Its binding seam is
null-only and unpopulated, and `run.bind-player-character/v1` remains reserved
and rejected. This candidate neither emits nor satisfies an approval token.

The sole operative future review-success token for this exact complete
candidate is `STRUCTURED_PLAYER_CHARACTER_P4_S1_PLAN_APPROVED`. Only an
independent read-only reviewer may return it after reviewing the complete
candidate and its recorded hashes. Writing this candidate does not return,
earn, or satisfy that token.

Authority precedence follows the Structured Player-Character Contract for
character identity and lifecycle; the Run Protocol for Run and line lifecycle;
the completed Minimum Run Core plan and Architecture for implementation facts;
this document for this bounded implementation contract; `PLANS.md` for status
and ordering; then engineering guardrails and workflow. A semantic conflict
blocks work rather than widening an authority.

## Frozen capability and exclusions

P4-S1 is one internal canonical mutation: bind one existing active-line Run to
the current exact applicable reference of one existing controller-owned active
canonical Player Character. Success populates the complete Run-owned binding
envelope, advances the Run version exactly once, appends exactly one immutable
Run revision, CAS-updates `run_current`, writes exactly one immutable successful
`run.bind-player-character/v1` receipt, leaves the Run lifecycle unchanged,
creates no Session participation, makes no Player Character mutation/revision/
CAS/write, commits once, and returns only after commit.

One line holds at most one binding; the P4-S1 binding is immutable. One Player
Character occupies at most one active line. Historical non-active bindings may
coexist only after later authorized terminal transitions, which P4-S1 does not
implement. It does not transition `pre_first_turn` to `active`.

The stored `ApplicableCharacterReference` is the exact immutable pointer
`(player_character_id, contract_version, record_revision)` to one canonical
stored revision, not a copied aggregate or a live current-revision lookup.
Reference following remains deferred. Controller ownership remains authoritative
only in the Player Character aggregate and is not copied into Run. Session
identity is absent from the binding and grants neither Run-selection nor
character authority.

The envelope contains owning Run and line IDs, the exact reference,
`binding_state=active`, binding operation ID, trusted Run authority-source
reference, server UTC `bound_at`, and absent `inactivated_at`. Binding mutation
provenance cross-binds Run/line IDs, prior/resulting Run versions,
`BIND_PLAYER_CHARACTER`, operation ID, trusted source, and server UTC time.

Eligibility requires strictly reconstructible Player Character and Run,
current controller ownership, active character lifecycle, `pre_first_turn` or
`active` Run lifecycle, no existing Run binding, successor version, and no
other active line occupied by that character.

Excluded: unbinding, rebinding, replacement, switching, transfer, cloning,
reference change/following, and the complete authoritative retirement/death/
return integration. P4-S1 nevertheless implements the temporary fail-closed
lifecycle-integrity gate below: it prevents `RETIRE` and `FINAL_DEATH` from
making a character inactive while a current active binding exists. No public
route, DTO, frontend, Demo, browser, Provider, scenario, world, or gameplay
behavior is activated.

## Frozen lifecycle-integrity gate

For exactly `RETIRE` and `FINAL_DEATH`, the canonical Player Character mutation
path must, inside its existing canonical mutation Unit of Work and after it has
locked the Player Character current row, use the P4-S1 active-line/binding
evidence seam to determine whether that character currently participates in a
current active Run or continuous-story-line binding. This is the same canonical
evidence seam used by P4-S1 binding; it is not a second source of truth.

If complete, valid current active-binding evidence exists, the mutation returns
the internal `PlayerCharacterPolicyCode.ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED`
outcome. No existing policy or protocol outcome is semantically compatible:
`AUTHORIZATION_FAILED`, absence, replay conflict, and integrity failure would
misclassify a valid binding, while `CONTINUITY_RETURN_POLICY_UNAVAILABLE` is
about return rather than this required lifecycle transaction. The new outcome is
internal only, receives no public mapping or durable receipt, and states that a
future authoritative atomic lifecycle transition is required. It is returned
before the domain policy transition, successor construction, Player Character
revision/current-row write, Run mutation, CAS, receipt insertion, or commit.
The operation therefore performs no Player Character or Run mutation, version
advance, partial write, or persistence effect.

If no current active binding and no surviving binding evidence exists, existing
`RETIRE` and `FINAL_DEATH` behavior is unchanged. If binding, active-line,
current-row, immutable-revision, ownership, or related canonical evidence is
malformed, contradictory, missing despite surviving evidence, or otherwise
corrupt, the guard fails closed as an integrity failure. It must never treat
that character as unbound or apply either mutation, and it performs no partial
write. Other Player Character mutations remain unchanged.

`ContinuityEffect.END_CURRENT_LINE_IF_PRESENT` remains a policy declaration of
the authority-required effect; P4-S1 must not ignore it once binding is active.
Until the complete transaction exists, the gate rejects the two guarded
mutations instead of independently applying the Player Character transition.

The global lock order remains Player Character current then relevant Run
current. `RETIRE`/`FINAL_DEATH` and binding operations first serialize on the
Player Character current lock. With that lock held, the guard checks binding
evidence and locks the relevant Run current row where the evidence seam requires
it, preserving that order. An already-bound character is rejected; if the
lifecycle mutation completed first while unbound, its later inactive state fails
the binding operation's existing active-character eligibility check. Thus no
sequential or concurrent P4-S1 execution can commit a retired or finally
deceased character while its Run binding remains current and active.

This is not the complete retirement/death-to-Run integration. The guard may be
removed or relaxed only by a separately reviewed phase that atomically performs
every authority-required effect: as applicable, retirement or final death;
ending the current Run or continuous story line; historicalizing the binding;
clearing the current active-binding representation; preserving immutable history
and receipts; and committing all related state changes in one canonical
transaction. That future integration remains deferred and is not authorized by
P4-S1.

## Internal operation and decisions

The strict extra-forbid internal command is `BindPlayerCharacterCommand` with
exactly `run_id`, `continuous_story_line_id`, `target_player_character_id`,
`expected_state_version`, and trusted `source_reference`. `RunOperationId` is a
separate required service argument; `RequestPrincipal` is trusted service
context, not command data. The command accepts no controller claim, character
contract/revision, Session ID, lifecycle, binding state/timestamp, public
authority claim, or second optional client request ID. Opaque identifiers are
preserved exactly: no trim, case fold, coercion, or semantic parsing. The exact
reference is derived from the locked canonical character.

The binding fingerprint includes namespace `run.bind-player-character/v1`,
`BIND_PLAYER_CHARACTER`, Run ID, line ID, target character ID, expected Run
version, operation ID, and trusted source reference. It excludes the derived
character revision so exact replay returns its stored result after a later
character revision. Receipt scope is `(run_id, run.bind-player-character/v1,
operation_id)`. The safe `run.bind-player-character-result/v1` contains Run ID,
line ID, unchanged lifecycle, resulting version, exact reference, and no
participation reference.

Receipt evaluation first validates the minimum authoritative evidence for
identity, ownership/non-enumeration, receipt scope, and stored-state integrity.
Under one valid receipt scope/key, changed caller intent or a changed intent
fingerprint returns `RunReplayDecisionCode.CONFLICT`. A stored result is not
caller-supplied intent and is never classified as a changed caller request.
Malformed, structurally invalid, incompatible, contradictory, or corrupt stored
receipt schema, stored result, stored key evidence, referenced revision, Run
history, or adjacent immutable evidence is an integrity failure, not
`RunReplayDecisionCode.CONFLICT`.

After that validation, an exact compatible receipt returns the validated
original stored safe result. It does not derive a new current Player Character
reference, compare any newly derived reference with the stored result, or
perform eligibility re-evaluation, mutation, CAS, receipt insertion, version
advance, commit, or a new eligibility query. A later valid Player Character
revision therefore neither changes the original result nor creates a replay
conflict.

The following rules are normative and implementable:

| Condition and ordering | Required result |
| --- | --- |
| Target character is genuinely absent and no canonical current, allocation, revision, receipt, binding, or other immutable evidence exists | `AUTHORIZATION_FAILED` |
| Valid existing target character is owned by another controller | `AUTHORIZATION_FAILED`, preserving non-enumeration |
| Character current row is missing while allocation, immutable revision, receipt, binding, or other canonical evidence survives | Integrity failure |
| Character current row, history, ownership, allocation, revision, or referenced-revision evidence is corrupt or contradictory | Integrity failure |
| Immutable Player Character revision referenced by a stored binding or receipt is missing | Integrity failure |
| Exact compatible receipt after the required evidence validation | Return its original validated safe result before new-operation lifecycle eligibility; require neither current character revision equality nor a newly derived current result comparison; perform no Run/Player Character mutation, CAS, receipt insertion, version advance, commit, or new eligibility query |
| Character later has another valid current revision | Exact replay returns the originally stored `ApplicableCharacterReference` |
| Character later becomes inactive after a future authority-compliant atomic lifecycle operation has ended/historicalized the line and preserved required immutable receipt and revision evidence | Exact replay occurs before the active-character lifecycle check and returns the original validated safe result; it neither reactivates the binding nor claims that the inactive character has a current active binding |
| Run later has valid successor revisions, including a valid `ATTACH_SESSION` successor that preserves the binding | Exact replay returns the original result before stale-version or other new-operation eligibility checks |
| Required current or immutable evidence is missing or corrupt | Integrity failure; never claim replay success |
| No compatible or conflicting receipt exists for the submitted scope | This is a genuinely new operation: only now evaluate expected Run version, successor-version availability, active-line Run lifecycle/classification, active Player Character lifecycle, absent existing Run binding, absence of another active line occupied by the Player Character, and the already-frozen remaining new-operation eligibility rules |

Missing Run returns `RUN_NOT_FOUND`; line mismatch `TARGET_MISMATCH`;
terminal/non-active line `NON_ACTIVE_RUN`; exhausted version
`VERSION_EXHAUSTED`; stale expected version `STALE_VERSION`; and CAS loss
`CONCURRENT_STATE_CONFLICT`.

Only two new internal service classifications are admitted:

- `PLAYER_CHARACTER_INELIGIBLE`: the owned character exists but is not active.
- `PLAYER_CHARACTER_BINDING_CONFLICT`: the Run is bound, the character occupies
  another active line, or the database uniqueness backstop detects that race.

They receive no public mapping. Corrupt Player Character, Run, history,
receipt, or referenced revision fails closed as integrity error. Persistence
and commit failure propagate; only committed bindings receive success receipts.

## Transaction, locking, and persistence

The one-Run-UoW order is: validate principal/command/source/operation/IDs;
resolve configured controller authority before UoW; lock and strictly reconstruct
the target character through a narrow same-UoW internal evidence seam; prove
ownership and identity; lock/reconstruct target Run; validate receipt scope and
stored-state integrity; return exact replay if compatible; return conflict only
for changed caller intent/fingerprint; and, only when receipt absence establishes
a genuinely new operation, validate line, active line, successor, expected
version, active character, absent binding, and active occupancy; construct
successor; append revision; CAS `run_current` by exact Run/line/prior version
while setting `active_player_character_id`; insert receipt; commit once; then
return.

Global lock order is Player Character current then target Run current. Character
mutations lock only character state; Session attachment locks Session before
Run; no current operation locks Run then Player Character. The occupancy lookup
is a strict current read, not a second Run lock. The character lock serializes
conforming binders; the active-character database uniqueness is the final race
backstop. No automatic retry, winner recovery, saga, outbox, nested UoW,
independent character commit, or uncertain-commit recovery is authorized.

No ORM or Alembic change is planned: migration `20260729_0005` already reserves
the representation. Populate these existing `run_revisions` and `run_current`
fields: `binding_player_character_id`, `binding_contract_version`,
`binding_record_revision`, `binding_state`, `binding_operation_id`,
`binding_authority_source_ref`, `bound_at`, and `inactivated_at`; additionally
set `run_current.active_player_character_id` to the binding character ID.
The receipt carrier uses binding namespace/command/result schema, result
character ID/contract/revision, and null participation fields.

Strict reconstruction accepts either all-null legacy binding or complete active
P4-S1 binding, and rejects partial carriers. It enforces exact Run/line and
reference identity; referenced revision contract consistency; active binding
only on active-line Run; matching current-row backstop; binding
operation/source/time equal to binding-revision provenance; immutable creation
provenance; one binding transition; absent prior binding; unchanged binding on
later `ATTACH_SESSION`; participation only on `ATTACH_SESSION`, never binding;
matching receipt/fingerprint/result/history; current equals latest revision;
positive uninterrupted versions; exact UTC timestamps; and failure on naïve,
contradictory, impossible, missing, cross-Run-substituted, or duplicate evidence.
Legacy unbound MRC Runs reconstruct unchanged. Historical binding state stays
reserved and unwritable.

## Composition and exact implementation inventory

Internal composition may construct Player Character service once and pass its
narrow internal read seam to `RunService`, retaining the shared lazy UoW factory;
the same seam supports the binding-aware lifecycle guard within the Player
Character mutation Unit of Work.
`ApiServices.run_service` may make only this internal operation available. No
API dependency getter, route, request/response DTO, OpenAPI entry, public Run
read/create, frontend, Demo, Provider, Session resume/routing, scenario/world
execution, or public reachability is added.

Production modifications and responsibility:

- `src/deviation_protocol/domain/run.py` — binding model, validation, provenance.
- `src/deviation_protocol/domain/player_character_policies.py` — only the
  smallest domain-policy change and directly relevant support required to add
  the frozen internal
  `PlayerCharacterPolicyCode.ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED`
  member to the existing `PlayerCharacterPolicyCode` enum; no duplicate or
  competing policy identity.
- `src/deviation_protocol/application/run_operations.py` — command, fingerprint,
  safe result, replay protocol.
- `src/deviation_protocol/application/run_service.py` — atomic internal workflow.
- `src/deviation_protocol/application/player_character_service.py` — narrow
  same-UoW locked evidence seam and binding-aware lifecycle guard; it consumes
  the domain-owned existing-enum outcome without a new public path.
- `src/deviation_protocol/application/ports.py` — narrow seam/port contracts.
- `src/deviation_protocol/infrastructure/run_persistence.py` — binding codecs and
  strict reconstruction.
- `src/deviation_protocol/infrastructure/repositories.py` — locked reads,
  occupancy/current CAS/receipt persistence.
- `src/deviation_protocol/api/main.py` — internal lazy composition only.

There are no new production paths. `orm_models.py` and Alembic are excluded
unless a separately proven representational defect appears.

Test modifications and responsibility:

- `tests/unit/test_run.py` — aggregate binding/integrity.
- `tests/unit/test_run_operations.py` — strict command, fingerprint, results.
- `tests/unit/test_run_service.py` — workflow/replay/rejections/rollback.
- `tests/unit/test_run_persistence.py` — codec and reconstruction corruption.
- `tests/unit/test_run_repositories.py` — locks, CAS, receipts, race mapping.
- `tests/unit/test_run_composition.py` — lazy internal composition/non-activation.
- `tests/unit/test_player_character_service.py` — read-only evidence seam.
- `tests/integration/test_mysql_run.py` — Run persistence, rollback/concurrency.
- New `tests/integration/test_mysql_player_character_run_binding.py` — real-MySQL
  cross-aggregate binding atomicity, FK, reload, corruption, and races.

## Bounded checkpoints

**P4-S1a — protocol, integrity, and Player Character evidence seam:** freeze and
test the guarded-mutation contract, exact rejection semantics, integrity
behavior, and same-UoW binding evidence seam, alongside modifications to
`domain/run.py`,
`src/deviation_protocol/domain/player_character_policies.py` only for the
smallest domain-policy change and directly relevant support required to add the
frozen internal
`PlayerCharacterPolicyCode.ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED`
member to the existing `PlayerCharacterPolicyCode` enum,
`application/run_operations.py`,
`application/player_character_service.py`, and `infrastructure/run_persistence.py`,
with `test_run.py`, `test_run_operations.py`, `test_player_character_service.py`,
and `test_run_persistence.py`. The Player Character mutation path rejects
`RETIRE`/`FINAL_DEATH` with
`ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED` only when valid active
binding evidence exists, while successful binding persistence remains rejected.
At this unstaged checkpoint RunService still rejects binding, repositories refuse
populated writes, no binding commits, and no public behavior activates.

**P4-S1b — atomic service, repository, and composition activation:** modify
`application/ports.py`, `application/run_service.py`,
`infrastructure/repositories.py`, and `api/main.py`, with
`test_run_service.py`, `test_run_repositories.py`, `test_run_composition.py`,
`test_mysql_run.py`, and the new MySQL binding module. It activates the complete
internal atomic binding service and the binding-aware Player Character mutation
guard together; successful binding must not activate unless that guard is active
in the same completed slice. It preserves public non-activation/no migration,
and remains unstaged through final review.

## Test, verification, and gate

Coverage is separated across domain, command/parser, persistence reconstruction,
repositories/UoW, Player Character evidence seam, RunService, composition, API
non-activation, and safe MySQL integration. It covers first success; exact and
changed-caller-intent replay (the latter producing `CONFLICT`); later valid
Player Character revision, a later inactive Player Character only after a future
authority-compliant atomic lifecycle operation has ended/historicalized its line,
and later valid Run successor exact replay; proof that exact replay does not compare against a newly
derived current result; stale/changed Run-line-target; strict injected
Session/authority rejection; genuinely absent character with no evidence;
missing current row with surviving immutable evidence; missing referenced
immutable revision; corrupt current/history/ownership evidence; missing/foreign/
inactive/retired/deceased character; bound Run and occupied character; malformed
or contradictory stored receipt/result/schema/history evidence producing an
integrity failure; proof that lifecycle, stale-version, and other new-operation
eligibility checks occur only after receipt absence; same-Run/different-character
and same-character/different-Run concurrency; CAS and uniqueness races;
rollback; no character mutation/no participation; populated/legacy
reconstruction; partial, wrong reference, missing revision/receipt, naïve time,
impossible lifecycle, discontinuous history, and later attachment preservation;
unchanged route inventory; lazy no-SQL/no-UoW composition; and real-MySQL reload,
FK, atomicity, concurrency, corruption, and rollback evidence. It additionally
requires tests that `RETIRE` and `FINAL_DEATH` each reject before any write when
a current active binding exists; use exactly
`ACTIVE_BINDING_ATOMIC_LIFECYCLE_TRANSITION_REQUIRED`; make no Player Character
revision/current-row mutation, Run mutation/version advance, receipt, or partial
write; retain existing behavior for unbound retire and final death; fail closed
as integrity failure for corrupt/contradictory evidence and for missing current
evidence with surviving immutable binding evidence; deterministically serialize
concurrent bind versus each guarded mutation with the losing path leaving no
partial state; and permit future authority-compliant inactivity plus a
historicalized binding to replay the original immutable result without
reactivating that binding. These are future tests only.

Later verification records focused unit and MySQL selections, `compileall`,
Offline/MySQL/Full modes as required, Alembic head/history, and `git diff
--check`. Live-model flags stay disabled. No Provider, browser, frontend, Demo,
or public gameplay test belongs here.

The required order is: create candidate; record exact inventory and SHA-256;
independent review returning the sole token; separate commit authority; user
manual push; confirm clean remote-aligned baseline; separate P4-S1a authority
and unstaged review; separate P4-S1b authority and complete unstaged review;
documentation synchronization; separate milestone-commit authority; user manual
push. This authoring task completes only candidate creation and hash evidence.

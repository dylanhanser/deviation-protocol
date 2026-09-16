# P3.3-S5 Objective Mechanics and Trusted Prompt Context Plan

Status: **Corrected documentation candidate awaiting focused re-review; not approved.
S5 implementation has not started.** Authored 2026-09-17 on `main` at
`34dc752295ba270617e5d29020f3a0c0b133544e`. HEAD, local main and local
origin/main matched, ahead/behind was `0/0`, and worktree/index were clean,
without conflicts or active Git operations; verification was local only.

S4 is independently approved and published at that baseline. Its earlier
changes-required review and frozen candidate wording remain history. DF-001
remains deferred. Phase 3.3 remains incomplete. This candidate authorizes no
implementation, runtime test, database, Provider/Live, browser, deployment or
Git write. The independent review returned `CHANGES_REQUIRED` with one
finding; the correction below awaits focused re-review by the previous
independent reviewer, preserving earlier conclusions.

## 1. Deliverable, authority and observed integration

Deliver five deterministic policies, one native-turn application coordinator,
and one pure trusted-context compiler, connected to normal production
`build_default_services`. Internally admit a native Run through S4, play through
the existing Session turn service, atomically save mechanics and narrative
results, reload and replay. This is internal component integration; public
native admission, discovery, API/OpenAPI, Demo/Web activation and recovery
projection remain S6. Later worlds/visits/progression/continuity remain S7;
relationship/residence state remains Phase 3.4.

Controlling documents are [AGENTS.md](../AGENTS.md), the
[workflow](engineering/codex_workflow.md), [guardrails](engineering/guardrails.md),
[findings register](engineering/deferred_findings.md),
[parent/S1 contract](phase_3_3_run_protocol_implementation_plan.md),
[S2](phase_3_3_s2_deterministic_profile_resolution_plan.md),
[S3](phase_3_3_s3_persistence_legacy_native_compatibility_plan.md), and
[S4](phase_3_3_s4_native_run_admission_entry_world_plan.md). Published plans,
S1/S2 codecs/catalogue/values, S3/S4 binding semantics and guardrails stay frozen.
The workflow governs successful disposition and proportionate evidence reuse.

| Existing path/symbol (under `src/deviation_protocol`) | Actual seam and S5 use |
| --- | --- |
| `api/main.py:build_default_services` | Composes `DurableNarrativeTurnOrchestrator`, ordinary SQLAlchemy UoWs, `SessionService`, and internal native admission. Wire the S5 loader/coordinator here. Dynamic Narrative in Demo is a different composition and stays unchanged. |
| `application/ports.py:RunSessionParticipationRepository.get`, `RunProtocolBindingRepository.get_classified` | Resolve a Session's stored participation to complete `NativeRunAdmissionV1`, or positively established legacy. S3 component-only native binding is insufficient. |
| `infrastructure/orm_models.py:RunMutationReceiptRow.participation_session_id` | Existing indexed, FK-bound reverse attachment evidence permits a read-only orphan check before treating a nonparticipating Session as standalone; no schema addition is needed. |
| `infrastructure/repositories.py:SqlAlchemyRunProtocolBindingRepository._classify` | Already validates Run revisions, immutable character, native receipt/protocol equalities, world, participation and initial Session family, including progressed Sessions. Reuse; do not reconstruct authority from request fields. |
| `application/action_context.py`, `domain/policies.py`, `application/rule_resolver.py` | Existing sealed context and gateway enforce ownership, feasibility, agency and local actions before any S5 charge. Keep local item/skill effects and `SkillResourceSpent` unchanged. |
| `application/narrative_outcome_policy.py:allowed_narrative_outcomes` | Matches authored structural/intent rules, resolves mutex priority and produces turn-bound candidates. S5 selects one native rule/result deterministically before rendering; legacy proposal selection stays as implemented. |
| `application/story_director.py:advance_after_verified_result`, `_advance_clocks` | Own authored action/auto-beat costs, threshold events, clue groups, transitions and endings. Accept a bound S5 clock plan at the existing clock-advance point, before thresholds/transitions/endings. No second advance pass. |
| `domain/state.py:consume_resource`; `application/turn_orchestrator.py:_persist_state_change` | Existing resource mutation and Session snapshot/event/receipt/version owner. S5 plans deltas first, then applies on the detached candidate and uses this persistence path. |
| `application/narrative_turn_orchestrator.py` | Existing prepare/claim/call/validate/finalize lifecycle. Prepare native decisions; detach after database reads; compile outside every UoW; revalidate decisions at finalize. |
| `application/narrative_prompt.py:PromptBuilder.build`, `application/narrative_models.py:NarrativeRequest` | Attach only compiler-produced context to the internal request; include it as JSON data in `server_public_context`. No mechanics run in either builder or compiler. |
| `application/session_service.py` | Existing owner checks, safe Frames, resource views and GET recovery remain the disclosure boundary. No new public protocol field or projection is introduced. |

The admitted `world.death_certificate@1` maps to the existing scenario/version
and investigator. Its player resource is `composure` (maximum 6); the pack has
no usable skill-cost path. Restricting resource pressure to `_use_skill` would
therefore not deliver the native gameplay effect. Its authored action clock
costs, narrative result templates and disclosure checks are usable now.

## 2. Proposed mechanics v1: exact scope and balance

Everything in this section is a **new proposed game-balance decision requiring
plan approval**, not a previously approved coefficient or illustrative-doc
threshold. S2 supplies exact integers `0..100`, step 5. Preserve those integers,
profile/override provenance and fingerprints without replacement, rounding or
clamping. Domain policies validate this domain; production additionally requires
the exact S2-resolved admitted values and profile-specific bounds.

Use `q(x) = x // 50`: `0..45 -> 0`, `50..95 -> 1`, `100 -> 2`, on the valid
S2 lattice only. This deliberately coarse first playable balance caps each
additional pressure at two units; not every five-point step changes an integer
cost. It makes parameter effects observable without introducing probability,
randomness, accumulated fractional debt or new persistence. Preserve authored
base costs as floors: profile pressure never cancels required conflict or fixed
consequences. Saturation affects a *derived delta*, never an S2 value.

Add a small, immutable S5 mechanics catalogue in
`domain/run_protocol_mechanics.py`, version `run-mechanics/v1`. Its one production
entry binds `(world.death_certificate, 1, death_certificate,
death-certificate-1.1.0, character.death_certificate.investigator)` to resource
`composure`. Validate all associations/resource existence against the already
loaded authored catalogues at composition. This is native mechanics authoring,
not an edit to the world catalogue, scenario facts or character definition.
Unknown mappings reject; no first-resource heuristic or zero-cost fallback.
Other worlds need their owning later reviewed content decision. Tests may use
an injected non-hospital catalogue without adding a production world.

Definitions used by every policy:

- A narrative action means a gateway-approved `NARRATIVE_REQUIRED` action with
  a server-selected authored result. Local queries/rejections, CHOOSE, CONTINUE,
  item/skill actions and initialization incur no S5 resource charge.
- `B` is the original current phase's authored positive clock-advance vector:
  the selected verified event's `action_type` cost, or auto-beat vector for
  CONTINUE. Select it exactly as the Director does today; never infer a clock
  from its name, a hidden threshold, prose or a later phase. Empty stays empty.
- Social friction qualifies only when the submitted type is TALK and the
  matching rule requires at least one currently visible runtime NPC through
  `required_visible_npc_definition_ids`. Discovery qualifies only when the
  chosen effect contains at least one not-yet-discovered clue, after existing
  phase, profession and reveal-event authorization checks succeed.
- An adverse result means AMBIGUOUS, FAILURE or NO_EFFECT. Rejection is not an
  adverse committed action. A chosen SUCCESS is not made adverse by prose.

| Policy / trusted input and source | Exact rule and integration/order | Observable example | Mutation/event owner and persistence | Failure and meaningful regressions |
| --- | --- | --- | --- | --- |
| `ResourcePressurePolicy`: admitted `resource_pressure`; catalogue-bound resource current from validated GameState; approved action classification | On a narrative action plan requested depletion `q(p)` and actual depletion `min(current, q(p))`. No restoration, maximum change or exhaustion penalty. Only if actual depletion is positive, the coordinator calls existing `consume_resource` exactly once with that positive actual amount on the candidate before Director advancement. If actual depletion is zero, call it zero times and emit no `RunProtocolResourceSpent`; do not reject or return early, and continue Director advancement and other planned effects. Local skill/consumable economics stay unchanged. | Current composure 6: pressure 45 spends 0, 50 spends 1, 100 spends 2. Current 1 at 100 spends 1; current 0 spends 0 and the required narrative path can still progress. Scarcity depletes an existing resource, without inventing death at zero. | Coordinator owns a `RunProtocolResourceSpent` DomainEventDraft only for positive actual depletion, with resource ID, requested/actual amount and before/after. Existing event ledger, GameState snapshot and turn commit own durability. | Missing/wrong resource or negative/malformed current is integrity failure, not saturation. Test 0/45/50/95/100, current 0/1/2/6, no mutation on rejected/local/replayed turns, and event/snapshot rollback. |
| `SocialTrustPolicy`: admitted `social_trust`; submission type plus structurally eligible authored rule and visible NPCs | On qualifying TALK add `q(100-t)` to each component of `B`. This is extra time spent obtaining cooperation, not a relationship score or altered NPC fact. Compute before mutation; never charge a clock absent from `B`. | Clinical recheck via TALK uses authored `investigate` cost 1. Trust 0/50/100 gives social-only clock advances 3/2/1. A forced authored acknowledgement remains the same acknowledgement. | Director consumes the composed vector; existing runtime clock snapshot/threshold events persist. No relationship write or memory fabrication. | Invisible/foreign NPC never qualifies by caller claim; eligibility still rejects through its existing owner. Test t=0/5/50/55/100, TALK versus OBSERVE for the same allowed recheck, no NPC rule and empty `B`. |
| `ConsequenceSeverityPolicy`: admitted severity and the server-selected authored result | On adverse narrative results add `q(s)` to each component of `B`; zero severity retains the full authored base. Never rewrite an effect's facts, clues, acknowledgement, death or ending. | Base clock advance 1 on an authored NO_EFFECT becomes 1/2/3 at severity 0/50/100. Failed effort uses more of the existing deadline; it does not create a new punishment subsystem. | Director, existing threshold/event/ending logic, same atomic Session commit. | Unknown result or unbound selection fails before candidate mutation. Test all four result kinds, s=0/45/50/95/100, authored fixed failure at zero, and once-only threshold crossing at maximum. |
| `InformationOpacityPolicy`: admitted opacity; selected effect's new-clue set validated by Director's existing reveal checks | On qualifying discovery add `q(o)` to each component of `B`. Pay additional investigation time, then reveal exactly the authored authorized clue set. Never hide already-known clues or invent thresholds for disclosure. | Record investigation costs base 1 per authored clock: opacity 0/50/100 costs 1/2/3, while all three reveal exactly the same verified records. Opacity 0 exposes no otherwise-hidden fact. | Director applies cost and clue updates on one detached candidate; existing discovery/evidence/clock snapshot and events share one commit. | Unauthorized reveal aborts the whole candidate before depletion or cost application. Test old versus new clues, zero opacity hidden-fact protection, required profession/phase/event failures, and retry without duplicate clue/cost. |
| `ConflictIntensityPolicy`: admitted intensity; `B` from authored event or auto-beat | Add `q(c)` to every component of nonempty `B` for native timed advancement, including CHOOSE and CONTINUE. No extra clock, event, beat, decision or encounter is created. Local queries/untimed actions do not advance. | An authored automatic deadline tick of 1 becomes 1/2/3 at intensity 0/50/100. Existing required conflict still occurs at zero. | Director owns threshold generation, transition and ending evaluation; existing persistence mechanism. | Reject contradictory action/base-vector association. Test c=0/45/50/95/100, empty vector, terminal/query exclusion, clock saturation and several thresholds crossed exactly once. |

Clock composition is additive from the unchanged base, **not successive scaling**:
for each authored `(clock_id, b)`, compute
`a = b + social_extra + severity_extra + opacity_extra + conflict_extra`.
Resource planning, social, severity, opacity, conflict is the fixed policy order;
all read the same pre-turn state and selected result. Validate the whole plan,
then apply positive actual resource depletion (skip only that call and spend
event when zero), apply the authored event, advance each clock once,
complete clue groups, evaluate transitions/endings and open a decision in the
existing Director order. Use integer arithmetic only. The Director applies
`after = min(clock.maximum, before + a)` and existing ordered thresholds.
Do not reconstruct `a` as a content `ClockAdvanceDefinition` if its authored
counter bound would reject the added delta; the bound for planned `a` is
`1..MAX_SCENARIO_COUNTER+8`. No negative/overflow/wrapped value is accepted.
Record actual saturation rather than claiming the whole requested advance.

Preserve `GameState.consume_resource(resource_id, amount)` and its
`_require_positive_amount` validator unchanged: amount must be a positive
integer, excluding bool, and zero raises `INVALID_AMOUNT`. Keep computed charge
(requested depletion `q(p)`) distinct from actual depletion
`min(current, q(p))`. A zero charge or an exhausted resource therefore skips
only the resource call and `RunProtocolResourceSpent`, leaving the resource
unchanged. Neither condition rejects an otherwise valid action or returns early
from the turn. Director advancement, authored events, clock/clue effects and
`RunProtocolMechanicsApplied` continue under the same ordering, atomic commit
and replay requirements. A positive actual depletion uses the unchanged API
once and the successful-spend draft specified in the matrix.

Combined example: TALK clinical recheck, base disposal tick 1, current composure
6, valid Standard overrides `(75,30,80,75,75)` give resource depletion 1, social 1, severity
0 (SUCCESS), opacity 1, conflict 1: clock advance 4 and composure 5. A comparable
adverse non-discovery TALK gives severity 1 and opacity 0, also 4. Each additive
component must be asserted separately so equal totals do not hide swapped rules.

Emit one internal `RunProtocolMechanicsApplied` draft for each native timed
advancement with schema `run-mechanics/v1`, binding digest, original state
version, selected rule/result when narrative (null otherwise), resource plan
and sorted clock rows `(id,before,base,social,severity,opacity,conflict,after)`.
It contains no new scenario event authority. The existing event envelope owns
sequence/time/ID; this draft is not a new table, receipt family or public field.
Zero-effect timed plans are still auditable. No audit draft on queries/rejection.

### Deterministic native outcome decision

After existing intent/structural checks and mutex selection, select one rule by
descending authored priority, then ascending ASCII rule ID. Choose its first
available result in `SUCCESS, AMBIGUOUS, NO_EFFECT, FAILURE` order. Empty candidates
retain `NarrativeOutcomeUnavailableError`. This is an explicit new S5 selection
rule for native gameplay, with no skill-success probability or semantic NLP.
It never manufactures a result missing from the authored template. For example,
the opening purposeful life signal selects authored SUCCESS; quiet observation
selects AMBIGUOUS because SUCCESS is absent. Eligibility/once/visibility still
apply before selection. Social trust affects cooperation cost, not this ordering.

Pass exactly one candidate with one allowed result to the renderer. Native
`NarrativeOutcomePolicy.authorize` must recompute and require that exact pair;
merely belonging to the old broader allowed set is insufficient. Issuer and
Director retain their existing sealed-event and fixed-fact checks. A different
model choice is rejected with no gameplay mutation, not used as a fallback.
Costs/outcomes can be computed and executed with prompt construction absent;
Provider availability/validity governs rendering completion, never the decision.

## 3. Native loading, composition and atomic application

Add an application-owned `NativeTurnMechanicsCoordinator` and a detached sealed
`TrustedNativeTurnInputs` carrier. This is derived authority within the existing
Session transaction owner, not a new admission service or external capability.
The policy module depends only on domain types; the application loads repositories.

1. Retain existing principal/Session ownership checks before public dispatch.
   Inside the turn UoW acquire the existing Session lock and inspect the stored
   request first. Exact committed replay returns its original response before
   fresh mechanics, clock, compiler or Provider work; conflicting signatures
   retain existing conflict behavior. A corrupt stored response still fails.
2. For fresh work, load and validate Session/latest snapshot/version/player and
   scenario as today. Load participation by **Session ID**, never a caller Run
   ID. Also read the distinct Run IDs of attach receipts indexed by
   `RunMutationReceiptRow.participation_session_id`, using the new read-only
   `RunSessionParticipationRepository.find_attachment_run_ids(session_id)`.
   Select distinct `result_run_id` ordered by that ASCII column. Its result is
   a sorted tuple of validated Run IDs, with a two-row detection
   ceiling: multiple associations are integrity failure. Require exactly the
   participation's Run ID when participation exists, and no attachment receipt
   when it does not. A missing participation with retained receipt evidence is
   corruption, not standalone. With participation, call
   `get_classified(run_id=participation.run_id)`
   using the same UoW's repository. Complete native classification must return
   `NativeRunAdmissionV1`. Component-only native, missing classified Run,
   missing world/protocol/evidence or corruption rejects; never legacy fallback.
3. Cross-check classification's Run/line/sole participation with this Session,
   admitted Run revision 3 and active lifecycle; exact applicable immutable
   character reference with initialization evidence and Session character;
   player/controller association through existing ownership and creation
   evidence; world reference with authored lookup and Session scenario/version;
   snapshot player, content version, state version and fingerprint. The current
   character revision is not a replacement for the admitted reference. S4's
   receipt-input and resolution-fingerprint equalities remain mandatory.
4. The ordinary read classifier performs no repair or additional commit. Use its
   non-locking complete read under the Session lock, not the S4 admission UoW or
   named DDL lock. S5 never mutates Run revisions, participation, character or
   protocol/world rows. Those admitted associations are immutable at this slice;
   future S7 lifecycle/concurrency changes must reassess this read contract.
5. A Session with no participation **and no reverse attachment evidence** retains
   the existing standalone Session path;
   this is not native/legacy Run classification. A participating legacy Run must
   have positive `LegacyRunCompatibilityV1` proof. Both paths run unchanged
   mechanics, prompts and persistence without any native numeric default. Do
   not catch missing repository support and call it legacy. Demo composition
   does not install the native loader and retains its explicit existing path.
6. Build the sealed detached carrier only after all checks. Bind Run ID/revision,
   line, Session/player, applicable character, world/scenario/content, S2
   resolution fingerprint, mechanics version, snapshot version/fingerprint,
   turn/request/action signature, and safe Frame digest. Revalidate original
   nested state, exact types and authenticity before reading carrier fields.
   No ORM object, session, repository, callable mutation port or mutable alias
   leaves the loader. Re-mint after trusted reconstruction; serialized seals
   or hashes alone never confer authority.
7. Gateway and existing local resolver run first. For CHOOSE/CONTINUE, augment
   only the Director's clock plan in `_coordinate_scenario`; other local
   economics stay unchanged. For narrative work, select the rule/result and
   compute the full resource/clock plan before any candidate mutation or job
   preparation. Preflight authored reveal prerequisites by extracting/reusing
   the Director's pure validation from `_apply_verified_event`; this grants no
   event seal. Full transition/ending feasibility remains the Director's
   detached application at finalize, after the existing issuer authorizes and
   seals the exact selected result. No Provider proposal or synthetic seal is
   needed to compute a mechanics decision.
8. Local state changes reuse `_persist_state_change` and the existing single
   turn-request commit. Narrative preparation stores only detached evidence
   and the decision, without gameplay mutation. Finalize freshly reloads all
   associations, state and eligibility, recomputes and compares the complete
   plan, then applies it once through the existing detached candidate, event
   receipt/memory/snapshot/response/job/CAS transaction. No second best-effort
   mechanics commit and no resource charge during prepare or Provider call.

The Director authenticates the plan before field access and validates its
input against the original snapshot plus precisely the declared resource
depletion. The coordinator validates that original snapshot before making the
copy. Do not compare the post-depletion fingerprint to the unchanged original
fingerprint, or permit an arbitrary candidate merely because it carries a seal.
The new reverse-read port is a non-abstract method that raises
`NotImplementedError` unless implemented; no default empty result. Existing
Demo adapters never call it because their composition does not install the
native coordinator. Production composition must provide its SQL implementation.

Concurrent identical requests have one persisted winner; losers restore the
existing response after rollback. PROPOSAL_VALIDATED resume revalidates and
finalizes without another Provider call. A stale binding/state/decision fails
before any mechanics mutation. Pre-commit exceptions/cancellation roll back
every staged family; uncertain commit retains existing conservative handling
and exact replay/read recovery, never an automatic replacement charge. Claim
atomic committed application, not exactly-once Provider billing.

## 4. Detached narrative job and transaction boundary

Reuse `NarrativeJob.narrative_request`'s existing bounded JSON column. Native
jobs use exactly this internal envelope, version `native-turn-request/v1`:

| Field | Required contents |
| --- | --- |
| `schema` | Exact `native-turn-request/v1` |
| `request` | Existing allowlisted `NarrativeRequest` JSON, with the singleton server-selected outcome candidate |
| `binding` | Exact carrier binding fields enumerated in section 3.6; wrappers encoded using their existing codecs, fingerprints lowercase hex |
| `mechanics` | `run-mechanics/v1`, exact five S2 integers, selected rule ID/result, requested/actual resource plan and sorted clock component rows from section 2 |

No arbitrary context map, new private fact dump, compiled text, model-supplied
mechanics or new database schema. Strictly bound all IDs by their owning
contracts, integers by owning counters, lists by authored clock count; use the
existing depth 24/collection 512/string 10,000/UTF-8 128,000 job JSON limits.
Extra/missing/duplicate fields, unknown versions and over-budget content fail
closed. The existing request fingerprint covers the **whole** native envelope.
All parsing paths (`handle`, finalize, resume, pending response and submission
recovery) dispatch explicitly between this envelope and legacy request JSON.
Do not change legacy serialized bytes or fingerprints. Pre-S5 active jobs for
a native Session lack this evidence and become STALE without Provider recall;
committed historical responses still replay their stored result unchanged.

Freeze the binding object's keys as `run_id`, `run_revision`,
`continuous_story_line_id`, `session_id`, `player_id`,
`applicable_character_reference`, `entry_world`, `scenario_id`,
`scenario_content_version`, `resolution_fingerprint`, `mechanics_version`,
`state_version`, `state_fingerprint`, `turn_id`, `client_request_id`,
`action_signature`, `frame_digest`. The two nested references use their existing
strict field allowlists. All other identifiers are scalar owning-contract
values; Run revision is exactly 3. `binding_digest` in internal audit events is
lowercase SHA-256 of `b"deviation-protocol:native-turn-binding:v1\0"` followed
by compact, sorted-key UTF-8 JSON of this object. Frame digest uses the existing
canonical JSON digest over the validated safe Frame. This digest binds evidence,
not authority. Clock audit rows are sorted by ASCII ID; application traverses
the original authored vector order, preserving generated-event ordering.

Preparation and job staging stay inside the current UoW. Following claim, use
a short ordinary UoW to freshly verify job/evidence/bindings and detach the
compiler input. Exit it completely, closing its AsyncSession and releasing
locks, **then** compile and build the Provider request. Do not compile in
`_prepare_or_execute`, `_claim`, `_finalize`, a repository, an ORM callback or
while any surrounding UoW remains active. Persisting detached input is not
compilation. The compiler performs neither serialization of private job
evidence nor a hash of arbitrary GameState: those are loader responsibilities.

Finalize compares freshly recomputed typed decisions/evidence; it does not call
the compiler under lock. A concurrent change after detachment may make a
rendering attempt stale; finalize then rejects it atomically. Pure compilation
cannot query the database to promise instantaneous freshness. Tests must state
this distinction and prove the final recheck. Existing one-attempt leases and
OUTCOME_UNKNOWN semantics remain unchanged.

## 5. Pure trusted prompt-context compiler

`compile_run_protocol_context(inputs: TrustedNativeTurnInputs,
decision: NativeMechanicsDecision) -> CompiledRunProtocolContextV1` is
side-effect-free and Provider-independent. Authenticate both carriers before
reading fields; revalidate original state and require equal bindings, state
version/fingerprint, action signature, selected result and mechanics version.
The loader has already reacquired the S2 catalogue-owned profile and performed
S3/S4 reconstruction. The compiler checks that the decision's parameter values
equal those trusted resolved values; it never resolves overrides or selects an
outcome. A caller dictionary, model copy, JSON string or constructed fake
carrier is not an input authority.

Output is exactly one canonical UTF-8 JSON byte string, at most 1,024 bytes,
with no BOM, whitespace, trailing LF or delimiter block. The illustrative
`[RUN_PROTOCOL]` text in older design docs is **not** this representation.
Lexicographically sort all object keys; use compact separators, no ASCII
escaping, NaN/floats forbidden, and no Unicode normalization/coercion. The
closed values below are ASCII, so process/locale normalization is irrelevant.
No optional output fields, arrays, nulls or free text are allowed.

| Output field | Exact allowlist and trusted source |
| --- | --- |
| `schema` | `run-prompt-context/v1`, compiler constant |
| `mechanics_version` | `run-mechanics/v1`, validated decision/catalogue version |
| `objectives` | Exactly `resource_pressure`, `social_trust`, `consequence_severity`, `information_opacity`, `conflict_intensity`, each original exact S2 integer |
| `presentation` | Exactly `world_tone` (`grim/balanced/heroic`), `reality_boundary` (`lawful/deviant/chaotic`), `relationship_overlay` (`off/veiled/charged`), from the validated frozen S1 envelope |
| `resource_pressure_label` | Numeric projection below, recomputed internally, never caller input |
| `selected_result` | Exact server decision's `SUCCESS/AMBIGUOUS/NO_EFFECT/FAILURE`; only narrative decisions compile |

Do not emit Run/Session/player/character/world/profile IDs, fingerprints, seals,
rule IDs, override intent, hidden facts/clues, private clocks/thresholds, NPC
private knowledge, raw snapshots, biographies, controller data or relationship
state. Bindings are checked but not printed. Existing safe Frame, public memory,
visible character tags and accepted recent prose keep their existing separately
validated prompt fields; they are not compiler inputs or new authority.

Resource label projection is proposed and exact: **Generous = 0..30; Fluid =
35..65; Scarce = 70..100**, on the S2 lattice. These nearly equal width bands
describe pressure, with larger numbers meaning scarcer. They are independent
of integer charge thresholds: 30/35 and 65/70 change the label, while 45/50 and
95/100 change the charge. Labels are never input aliases or stored replacement
values. S5 owns this internal prompt projection; public/client labels remain
S6-owned and are not added to responses or OpenAPI.

The opaque output carrier holds only validated bytes and compiler provenance,
with no mutation capability. Attach it to `NarrativeRequest` through a private,
nonserialized, validated `with_compiled_run_protocol_context` method, analogous
to the existing private Dynamic generation-instruction handoff. Do not add an
optional public DTO field. `PromptBuilder.build` inserts its parsed closed
object as `server_public_context.run_protocol_context` using existing canonical
JSON escaping and total prompt character/UTF-8 budgets. Absent attachment
produces byte-identical legacy prompt output. The builder authenticates the
carrier but does not compile, compute costs or interpret a result as permission
to mutate. Native orchestration alone can attach it after fresh trusted loading.

Add fixed system instructions explaining the three presentation enums only
when native context is attached: grim changes diction, not usable resources;
heroic changes expression, not success; lawful/deviant/chaotic cannot change
facts, laws or canon; off/veiled/charged changes permitted interpersonal
atmosphere only, within current safe Frame and character authority. No overlay
may read/create/anticipate Phase 3.4 relationship or residence state. Canonical
character identity, abilities, knowledge, personality and viewpoint stay owned
by the applicable character/reference and existing Frame. Compiled text and
all model output remain non-authoritative data, including valid output.

### Independent golden examples and failures

These literal expected bytes are authored independently of the future encoder;
tests must not generate their expected value by calling compiler helpers.
Use valid admitted fixtures for each corresponding profile/presentation pair;
the second uses Extreme overrides resource=90 and severity=90.
The JSON lines have no final newline in the expected byte value.

```json
{"mechanics_version":"run-mechanics/v1","objectives":{"conflict_intensity":60,"consequence_severity":65,"information_opacity":60,"resource_pressure":60,"social_trust":45},"presentation":{"reality_boundary":"lawful","relationship_overlay":"off","world_tone":"balanced"},"resource_pressure_label":"Fluid","schema":"run-prompt-context/v1","selected_result":"SUCCESS"}
```

```json
{"mechanics_version":"run-mechanics/v1","objectives":{"conflict_intensity":90,"consequence_severity":90,"information_opacity":90,"resource_pressure":90,"social_trust":10},"presentation":{"reality_boundary":"lawful","relationship_overlay":"off","world_tone":"grim"},"resource_pressure_label":"Scarce","schema":"run-prompt-context/v1","selected_result":"AMBIGUOUS"}
```

The Easier profile's base values provide the Generous golden:

```json
{"mechanics_version":"run-mechanics/v1","objectives":{"conflict_intensity":35,"consequence_severity":35,"information_opacity":30,"resource_pressure":25,"social_trust":70},"presentation":{"reality_boundary":"lawful","relationship_overlay":"off","world_tone":"balanced"},"resource_pressure_label":"Generous","schema":"run-prompt-context/v1","selected_result":"SUCCESS"}
```

Also assert exact 30/35/65/70 projection boundaries. S2 allows all 27
presentation combinations for every valid profile/override set. Domain-only
boundary values outside a profile's override range are not native admission
examples. No arbitrary full cross-product or vector-count quota is required.

S1/S2/S3/S4 validation exceptions retain their existing owners. New application
failures are `NativeTurnBindingError` (a `SnapshotInvalidError` subtype for
contradictory complete association), `NativeMechanicsIntegrityError` (a
`CandidateStateInvalidError` subtype for invalid original decision/catalogue/plan) and
`RunPromptContextError` with closed reasons `UNTRUSTED_INPUT`, `BINDING_MISMATCH`,
`STALE_INPUT`, `INVALID_VALUE`, `SIZE_LIMIT`. A false seal fails before field
access; unequal Session/Run/world/character/action binds fail before output;
changed snapshot version/fingerprint fails STALE_INPUT; bool/float/51/string
objective, categorical alias, extra field, altered nested enum or unknown
version fails its owning validator. Oversize constructed output is defensive
guard evidence (valid v1 output is well below 1,024), not a valid maximum vector.
No partial output, fallback context, exception repr of private state or repair.
Map compiler rejection at its orchestration caller to the existing safe
`NarrativeRequestRejectedError`; retain its closed internal reason without
private state. Integrity failures use existing safe application error handling;
no new public error enum/schema. Unexpected programmer exceptions must not be swallowed.

## 6. Dependency-derived future implementation inventory

Paths below are proposed edit paths, not a numerical cap. Paths are relative to
the repository; application/domain entries have prefix `src/deviation_protocol/`.
No implementation is authorized now. An unforeseen storage/public-contract
dependency stops for scope reassessment; do not quietly create a migration or
turn implementation review into another planning gate.

| Edit path | Concrete responsibility |
| --- | --- |
| `domain/run_protocol_mechanics.py` (new) | Five independent policy classes, exact integer rules, immutable mechanics catalogue, typed pure plans and clock bounds; no application/infrastructure dependency |
| `application/native_turn_mechanics.py` (new) | Same-UoW admitted-family loader, carrier sealing, cross-binding, native selection, deterministic composition/preflight, detached job evidence codec and resource/event application |
| `application/run_protocol_prompt_context.py` (new) | Pure compiler, closed canonical output and output-carrier validation; no repository/Provider imports |
| `application/turn_orchestrator.py` | Optional explicitly composed native coordinator; fresh local native loading and bound CHOOSE/CONTINUE clock handoff; reuse existing atomic persistence |
| `application/narrative_turn_orchestrator.py` | Native prepare/detach/compile/finalize wiring, native job dispatch in every parsing/recovery path, singleton renderer candidate and final revalidation |
| `application/narrative_outcome_policy.py` | Require exact native preselected pair while retaining legacy authorization and event-issuer semantics |
| `application/story_director.py` | Validate a native bound plan, preflight reveal requirements, replace one clock-advance vector at the existing point and retain threshold/transition/ending order |
| `application/narrative_models.py` | Private validated nonserialized compiled-context attachment preserving legacy request bytes |
| `application/narrative_prompt.py` | Explicit native JSON context insertion and fixed expression-only instructions under existing prompt budgets |
| `api/main.py` | Normal production wiring and catalogue compatibility check without database or Provider construction work beyond existing composition |
| `application/ports.py`, `infrastructure/repositories.py` | Read-only indexed reverse attachment lookup on existing mutation receipts; reject orphan/multiple associations without changing classifier or write semantics |
| `tests/unit/test_run_protocol_mechanics.py` (new) | Independent arithmetic oracle, all lattice points, resource/clock bounds, eligibility exclusions and combined ordering |
| `tests/unit/test_native_turn_mechanics.py` (new) | Trusted loading, selection, detached evidence codec, cross-binding, replay/stale/failure and legacy split |
| `tests/unit/test_run_protocol_prompt_context.py` (new) | Literal goldens, forged/malformed inputs, label boundaries, determinism, hidden-data and no-I/O/presentation equivalence |
| `tests/unit/test_story_director.py` | Planned vector application, multiple threshold crossings, clue authorization and non-hospital generic behavior |
| `tests/unit/test_narrative_outcome_policy.py` | Native singleton result enforcement and adversarial model proposals |
| `tests/unit/test_narrative_provider.py` | Attachment/prompt budgets, literal legacy equality, no leaks or output authority |
| `tests/unit/test_turn_orchestrator.py` | Native local dispatch, no query charge, exact replay and rollback/finalize coordination with instrumented UoWs |
| `tests/unit/test_run_composition.py` | Default production graph installs real native mechanics/compiler path without activating Demo or public entry |
| `tests/unit/test_run_repositories.py` | Reverse lookup identity, duplicate/orphan evidence, same-session repository use and no-write assertions |
| `tests/integration/test_mysql_native_turn_mechanics.py` (new) | Production-composed S4 admission -> native turn -> reload/replay/ending, zero-charge/zero-depletion/positive-spend controls, real atomicity/concurrency/faults, compiler/Provider outside Sessions and locks |
| `PLANS.md`, `docs/run_protocol.md`, `docs/architecture.md`, `docs/narrative_provider.md` | Record implemented scope/evidence, actual pipeline and internal request/prompt contract at implementation; preserve this frozen plan |

No edit is presently required in `application/session_service.py`,
`application/rule_resolver.py`, `application/effect_executor.py`, UoWs, ORM,
migrations, scenario JSON, S1-S4 domain/codec/service modules or Demo/Web.
Existing state/event/job storage can express every proposed delta. In particular
there is no relationship score, fractional debt, per-run new counter or hidden
clue persistence requirement. If strict existing event consumers cannot accept
the two bounded new internal event types, identify that exact consumer before
implementation proceeds and adjust the inventory within S5; never bypass it.

Execution-only regressions: `test_action_gateway.py`, `test_rule_resolver.py`,
`test_character_state.py`, `test_story_mutations.py`, `test_session_service.py`,
`test_scenario_event_bridge.py`, `test_narrative_jobs.py`, `test_player_memory.py`,
S1/S2/S3/S4 unit suites, `test_demo_composition.py`, `test_dynamic_narrative.py`,
`test_run_entry_api.py`, `test_phase_3_0_public_client_contract.py`, and relevant
MySQL suites `test_mysql_narrative_coordination.py`,
`test_mysql_native_run_admission.py`, `test_mysql_run_entry_playthrough.py`,
`test_mysql_session_api_persistence.py`. These names are under their existing
`tests/unit` or `tests/integration` directories. Changes there need a concrete
dependency explanation, not an arbitrary file-budget exception. Migration
fault matrices are not rerun merely for this plan or unchanged schema.

## 7. Executable acceptance and proportionate verification

| Acceptance family | Required executable assertions |
| --- | --- |
| Five objective policies | Independent expected arithmetic at every valid S2 scale point, especially q boundaries and reversed trust; resource saturation, missing resource, each result/discovery/NPC qualifier, empty vectors, authored floors and clock maxima. Invalid bool/float/off-step values fail. Tests cover every state mutation. |
| Combined mechanics | Assert each component and final candidate/event set for section 2's examples, multi-clock authored order, no double scaling, and exactly one Director threshold pass before transitions/endings. Repeat from the same input yields identical decision and state (event envelope IDs/time are injected separately). |
| Presentation separation | Exercise all 27 admitted presentations at each published profile default while holding objectives/state/action fixed. Compare selected rule/result, costs, probabilities (none added), resources, relationship/death/world/permanent/canon state, semantic events and memory effects. Exclude audit-only resolution/binding/proposal digests and existing envelope metadata, which legitimately differ; do not exclude semantic deltas. Compile on/off and PromptBuilder replaced with a raising sentinel must not alter pure mechanics results. No Phase 3.4 read/write port is present. |
| Trust and stale state | Forged carriers, constructed/mutated nested models, A/B protocol substitution, wrong Run/line/Session/player/controller/character revision/world/scenario, missing native family and old snapshot/version/action signature fail before mutation or output. Positive legacy proof and standalone Sessions remain separate. Changes between prepare/detach/finalize reject. |
| Compiler determinism | Exact independent JSON bytes, repeat compilation, reversed mapping insertion, child processes with different PYTHONHASHSEED and available locales; deny clock/random/network/filesystem during compiler invocation. Record unavailable locale as unavailable, not as a pass. Numeric/label boundary cases and malformed outcomes have exact reasons. |
| Disclosure/model authority | Scan full serialized prompts and outputs for sentinel hidden facts, private NPC data, undiscovered clues, private clocks and binding IDs. At opacity zero no extra disclosure. Grim cannot spoil resources, Heroic cannot turn failure into success, Chaotic cannot create permanent canon. Fake model changes result/token, emits grants/relationships/death/world/canon/extra fields: reject and prove unchanged durable gameplay rows. |
| Actual native turns | Use normal `build_default_services`, its S4 admission service and its turn orchestrator with an injected fake Provider. On the admitted scenario prove resource depletion, TALK recheck social friction, discovery friction, adverse-result severity and CONTINUE conflict pressure; reload through SessionService and inspect durable state. Play an authored route to a valid ending for each published profile default; use paired valid overrides to isolate effects. No test-only production world or mechanics bypass. |
| Resource application integration | In the production-composed real-MySQL native-turn suite, instrument the existing `consume_resource` call without replacing its validator. Complete valid narrative turns for (1) Easier default `resource_pressure=25`, current composure 6: requested charge 0, actual depletion 0; (2) Standard default pressure 60, composure already 0 in the valid persisted pre-turn state: requested charge 1, actual depletion 0; (3) Standard default pressure 60, composure 6: requested/actual 1, resulting composure 5. For each zero case assert zero resource calls, no `RunProtocolResourceSpent`, unchanged persisted resource, subsequent Director advancement executes, and the selected authored event, applicable clock/clue effects and `RunProtocolMechanicsApplied` persist without suppression. For the positive control assert exactly one call with positive amount 1 and exactly one successful-spend event containing the bound resource ID, requested/actual 1 and before/after 6/5. All cases retain the existing atomicity and replay assertions below; committed replay makes no resource call or duplicate spend event. |
| Replay/atomicity | Exact committed replay invokes zero mechanics/compiler/Provider writes; altered key evidence conflicts. Concurrent same-key attempts have one winner. Crash after validated proposal resumes once without Provider recall. Inject failures/cancellation before events, after events, before snapshot/response/job/CAS commit; real MySQL proves no partial resource/clock/memory state. Test acknowledged and uncertain commit recovery under existing protocol. |
| Outside transaction/lock | Instrument actual UoW enter/exit, AsyncSession creation/close and compiler/PromptBuilder/fake Provider entry. Require zero active UoW and zero unclosed AsyncSession at compilation/rendering. Independent MySQL connection acquires the same Session row lock while compiler/fake Provider is suspended; no S4 named lock is held. Recheck at resume and stale finalize paths. Mock counters alone cannot establish database-lock release. |
| Compatibility | Existing local item/skill, decision, CONTINUE, legacy request/prompt/fingerprint/replay, public schema and Demo/Dynamic behavior remain unchanged. Native mechanics leave immutable Run revision 3, character and protocol/world rows byte-identical. Session ending still does not transition the Run (S7). |

Implement in dependency order: pure policies/catalogue and compiler; trusted
loader/job codec and outcome choice; orchestration/Director/composition; focused
tests and documentation; stable integrated acceptance. Use focused
`.\.venv\Scripts\python.exe -m pytest` selections during implementation in the
authorized sanitized environment. At stable code run the repository's
`.\scripts\verify.ps1 -Mode Offline` for the shared engine/prompt changes.
Real-MySQL evidence in the new native-turn suite and listed transaction/legacy
regressions is mandatory because orchestration and JSON job persistence change;
run through authorized `verify.ps1 -Mode MySQL` on the designated test database.
No SQLite or mocks substitute. Run compileall for these shared Python edits;
schema changes are not planned, so Alembic checks are metadata-only unless an
explicitly reassessed dependency changes that scope. Live stays disabled.

Reuse expensive unchanged S2 evidence only after locating the external
`s3-implementation-20260916-audit/correction` manifest referenced in
[published S3/S4 evidence](run_protocol.md#p33-s4-implementation-candidate-evidence).
It records 23 tests and 5,624,910 direct resolver calls. The summary alone is
insufficient: verify hashes of S1/S2 source/catalogue/tests, Python/Pydantic and
other relevant dependencies, platform/environment assumptions, exact command,
exit status and counters. Preserve original manifests/logs; create a separate
implementation evidence manifest with absolute locations and applicability
comparison. If unavailable/inapplicable, run the required exhaustive node;
never silently waive it. If reused, explicitly deselect only
`tests/unit/test_run_protocol_resolution.py::test_complete_direct_exhaustive_public_resolution_domain`
using process-local `PYTEST_ADDOPTS=--deselect=tests/unit/test_run_protocol_resolution.py::test_complete_direct_exhaustive_public_resolution_domain`
in the authorized verification subprocess, restoring it afterward; execute the
remaining S2 tests and native reconstruction cases. Report executed, reused,
skipped, failed and deselected counts separately. No Full/Offline rerun is
needed merely after documentation-only edits once relevant evidence is stable.
Apply DF-001's process-local containment; do not attribute other failures to it.

## 8. Current candidate, review and handoff

The documentation candidate is exactly `PLANS.md`, `docs/architecture.md`,
`docs/run_protocol.md`, and this new plan. Deferred findings need no edit:
no new confirmed eligible defect was established; DF-001 remains deferred.
There is no unresolved product choice hidden behind an inert parameter: the
resource binding, saturation behavior, cost coefficients, outcome preference,
label bands and presentation instructions above are explicit proposals for
this plan's substantive review. Rejection of any is a precise balance decision
to revise here, not permission to invent relationship state or another subsystem.

Independent review of the incoming four-document candidate returned
`CHANGES_REQUIRED` with one finding: the unconditional resource call would
pass zero to the existing positive-amount validator, rejecting valid turns at
Easier default pressure or when composure is exhausted. That reviewed candidate
was +679/-61, 80,646 patch bytes, SHA-256
`4785fdfe44a7feaec319da6bd3cea2ea598da1530740613f1e3c637eaa5b1ab9`;
this identity is historical, not the corrected candidate binding. The bounded
correction conditions only the resource call/spend event on positive actual
depletion and requires the three integration controls in section 7. It changes
no API, coefficient, saturation, resource bound or other policy decision.
The corrected candidate remains unapproved; next is focused re-review by the
previous independent reviewer of this correction and its direct dependencies,
preserving earlier conclusions. No new deferred finding or approval stage is
introduced; DF-001 remains deferred.

The operative success token is:

`PHASE_3_3_S5_OBJECTIVE_MECHANICS_PROMPT_CONTEXT_PLAN_INDEPENDENT_REVIEW_APPROVED`

Both successful dispositions `APPROVED` and `APPROVED_WITH_DEFERRED_FINDINGS`
must emit that same exact token, bind the complete candidate and evidence, and
satisfy all technical requirements. Disposition names are not alternate tokens.
The sole dormant implementation token is:

`PHASE_3_3_S5_OBJECTIVE_MECHANICS_PROMPT_CONTEXT_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It is non-operative until plan approval, separately authorized exact local
documentation commit, user-controlled push, clean published-baseline confirmation,
and separately authorized implementation. Its future review supports both
successful dispositions with that same token. No extra approval stage is added.
Neither token grants staging/commit/push, implementation or later-slice authority.

Freeze identities after the last byte edit, externally to the hashed documents:
baseline/ref topology, exact paths, each file's UTF-8 bytes/lines/SHA-256 and
each binary-safe patch's bytes/SHA-256, plus the lexicographically ordered
complete patch size/hash and insertions/deletions. Include the untracked new
plan using a `/dev/null` new-file diff; tracked diff alone is incomplete. Any
candidate byte change invalidates approval. Relevant baseline changes require
reassessment and new identities under the workflow before review proceeds.

Documentation synchronization for this candidate: the plan owns proposed rules,
compiler/inventory/acceptance; roadmap owns S4 publication and S5 planning status;
protocol owns current implemented/deferred boundaries; architecture owns the
existing production path and planned integration. Historical evidence remains
historical, with no new runtime pass claimed. Only document scope, references,
status, whitespace, UTF-8/LF and final-newline checks are due now. S5 remains
unimplemented and Phase 3.3 incomplete; no trial or release readiness is implied.

## Guardrail impact

None. This plan applies existing AUTH-001, STATE-001, SCENE-001, MODEL-001,
MODEL-002, DB-001, DB-002, API-001, PLAY-001, CONTENT-001, ENV-001/002 and
GIT-001. Published technical guardrails and workflow remain unchanged.

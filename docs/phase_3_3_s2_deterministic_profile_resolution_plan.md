# Phase 3.3 S2 Deterministic Profile Resolution Plan Candidate

Status: **New documentation-only candidate authored on 2026-08-16 against
`4d146679e782ff555819b411fc5048e55299de4d`. Every S2 decision below is
proposed and unapproved. P3.3-S2 implementation has not begun.**

Phase ownership: **P3.3-S2**

Candidate scope: exactly this file, [`../PLANS.md`](../PLANS.md), and
[`run_protocol.md`](run_protocol.md).

This file is deliberately candidate-time authority. If these exact bytes later
receive the operative independent-review verdict, a separately authorized
commit, the user's manual push, and clean aligned published-baseline
confirmation, the decisions become the frozen S2 implementation plan without
requiring a second status-edit loop. Until all four events occur, every decision
in this file remains proposed and unapproved.

The first independent read-only review returned `CHANGES_REQUIRED` for four
material findings. The second independent read-only review returned
`CHANGES_REQUIRED` for exactly two remaining Medium findings: the unfrozen
universal-verification method and overlapping exception ownership for the S1
profile reference nested in an S2 catalogue entry. The third independent
read-only review returned `CHANGES_REQUIRED` for exactly one remaining Medium
finding: repeat and aggregate public-resolver invocation counts were not frozen
or asserted. None of the three reviews emitted a plan or implementation
approval verdict. This third correction is authoring only. Any correction-
complete label is non-operative, and these changed bytes require a fresh
independent read-only re-review.

## 1. Baseline and authority

| Baseline fact | Exact value |
| --- | --- |
| Repository | `D:\deviation-protocol` |
| Branch | `main` |
| `HEAD`, local `main`, local `origin/main` | `4d146679e782ff555819b411fc5048e55299de4d` |
| Ahead/behind | `0/0` |
| Subject | `docs(run): close Phase 3.3 S1 publication` |
| Parent | `6212a760a549920c1c11dcb01e07566945df5556` |
| Starting worktree/index | Clean; no untracked paths, conflicts, active Git operations, or locks |

P3.3-G0 is approved, published, frozen, and complete at
`76064d200d1aa5af7cddff22d33acb03e608e598`. The exact P3.3-S1
implementation is independently approved and published at
`6212a760a549920c1c11dcb01e07566945df5556`. Its three-document publication
closeout is published at this candidate's baseline
`4d146679e782ff555819b411fc5048e55299de4d`; P3.3-S1 is fully closed and
requires no further synchronization. Phase 3.3 remains incomplete. P3.3-S2
through P3.3-S7 are unimplemented, and no later slice is authorized here.

The frozen parent plan remains historical authority and must not be edited:

- `docs/phase_3_3_run_protocol_implementation_plan.md`;
- mode `100644`;
- 1,233 lines;
- 83,331 bytes; and
- SHA-256
  `09ef2ffe9fc03fc60cd069df116463b2cc27d08f50fbbddc658b28d975683e1b`.

The published S1 identities protected throughout this planning candidate are:

| Path | SHA-256 |
| --- | --- |
| `src/deviation_protocol/domain/run_protocol.py` | `2efc4d2914601d819fb440baa15022ad7e89a2b1e164fda5708245e486acd2e5` |
| `src/deviation_protocol/infrastructure/run_protocol_persistence.py` | `31f1befca159113f0ef98c381f4026fb8e8b68131b76cd44beba2ea18c420196` |
| `tests/unit/test_run_protocol.py` | `5bbd223b9b6ff2c8070ffe5dce5018943d5f827c266bf0153d6d4eb8028c98a9` |
| `tests/unit/test_run_protocol_persistence.py` | `0d4baabc82e39def27930610ca1318dd42f0effc40b55db7a702dc1e6964e792` |

This plan preserves the complete 22-symbol S1 contract, envelope epoch
`run-protocol-envelope`, trusted record version `1`, schema literal
`run-protocol-envelope/v1`, canonical v1 codec, both 1,024-byte defensive
ceilings, the 193-byte golden, the genuine 329-byte legal maximum, the no-I/O
stored-carrier reconstruction boundary, and the S1 exception distinctions.
Legacy Run revisions 1/2/3 remain unchanged. `scenario_id` remains scenario
identity only, and no legacy Run receives synthesized protocol, profile, world,
visit, region, or world-state authority.

Product authority is [`run_protocol.md`](run_protocol.md). Repository status
and phase ordering are owned by [`../PLANS.md`](../PLANS.md). Implemented
architecture remains in [`architecture.md`](architecture.md), which this
documentation-only task does not modify. Workflow and guardrails remain in
`docs/engineering/codex_workflow.md` and `docs/engineering/guardrails.md`.

## 2. Lifecycle position

The exact order remains P3.3-G0, S1, S2, S3, S4, S5, S6, then S7. S2 supplies
only a pure deterministic profile catalogue, validation, resolution, canonical
input, and fingerprint boundary. It creates no durable or public activation.

The lifecycle gates for these exact plan bytes are:

1. finish and measure the three-path documentation candidate;
2. obtain fresh independent read-only approval of the exact baseline, bytes,
   identities, patch, and decisions;
3. obtain separate explicit authorization for one exact local documentation
   commit;
4. the user manually pushes that commit; and
5. confirm the exact commit at a clean aligned published baseline before any
   separately authorized S2 implementation begins.

Authoring, hashing, review, commit, or publication of this plan does not itself
authorize implementation. A relevant baseline change or any candidate byte
change invalidates recorded identities and approval.

## 3. Goals and non-goals

### Goals

- Freeze exact domains for the five engine-owned objective parameters.
- Freeze three positive-version authorized product profiles and every default.
- Freeze an exhaustive, player-proposed and server-authorized override matrix.
- Define one complete fail-closed precedence algorithm.
- Define a pure resolver with explicit version dispatch and no randomness.
- Bind the canonical S1 envelope, authorized profile pair, and exact override
  presence into canonical bytes and a domain-separated SHA-256 fingerprint.
- Freeze an exact future module symbol contract, path budget, and verification
  matrix.
- Prove presentation/objective independence mechanically.

### Non-goals

S2 excludes durable profile or resolution persistence; ORM; schema or
migration; repositories; Unit of Work; transactions; CAS; rollback;
concurrency; legacy/native Run reconstruction; Run binding or admission;
entry-world identity or freezing; world, visit, region, revisit, or continuity
state; application of the five mechanics to gameplay; prompt-context or
`[RUN_PROTOCOL]` compilation; Provider integration; public API or OpenAPI;
Demo, Web, projections, recovery/replay integration; later-world selection;
NPC identity, memory, relationship, counterpart, or canon systems; every
P3.3-S3 through P3.3-S7 implementation; and Phase 6, Phase 7, or Phase 8 work.

S3 owns persistence and reconstruction. S4 owns native admission and
entry-world/protocol freezing. S5 owns mechanics application, the exact
numeric-to-categorical mechanics/prompt projection for the product labels
`Scarce`, `Fluid`, and `Generous`, and trusted Provider-independent
prompt-context compilation. S6 owns any public API, OpenAPI, Demo, Web,
projection, recovery, or client representation of those labels, plus its other
reviewed public parity. S7 owns later-world, visit, region, continuity,
progression, canon, and authorized identity-related selection.

## 4. Exact objective parameter domains

Every parameter is an exact Python `int`, never `bool`, `IntEnum`, an integer
subclass, float, decimal, string, or coerced value. Its inclusive domain is
`0..100` in exact increments of `5`, giving 21 discrete values. The unit is a
normalized **engine profile point**. It is an ordinal policy input, not a
percentage, probability, quantity, multiplier, resource count, or public
promise. S5 will separately freeze how each value affects mechanics.

Canonical scalar spelling is the shortest ordinary base-10 JSON integer token:
`0`, `5`, ..., `100`, with no sign, leading zero, decimal point, exponent, or
locale-specific formatting.

| Parameter | Direction and exact endpoint semantics | Intermediate semantics | Direct override | Cross-parameter rule |
| --- | --- | --- | --- | --- |
| `resource_pressure` | `0`: no profile-created scarcity pressure; `100`: maximum authorized scarcity pressure. Higher is harsher. | Discrete monotonic scarcity pressure; it does not itself remove/add a resource. | Yes, only within the selected profile's range below. | None beyond its selected-profile range and step. |
| `social_trust` | `0`: no profile-created baseline willingness to trust; `100`: maximum authorized baseline willingness. Higher is more trusting. | Discrete monotonic environment prior; never a relationship, memory, or NPC-state value. | Yes, only within the selected profile's range below. | None beyond its selected-profile range and step. |
| `consequence_severity` | `0`: least profile severity; `100`: maximum authorized severity. Higher is harsher. | Discrete monotonic consequence pressure; `0` is not immunity and cannot cancel a fixed consequence. | Yes, only within the selected profile's range below. | None beyond its selected-profile range and step. |
| `information_opacity` | `0`: maximum transparency permitted by authored facts; `100`: maximum authorized opacity. Higher is more opaque. | Discrete monotonic discovery friction; `0` never reveals hidden or unauthorized facts. | Yes, only within the selected profile's range below. | None beyond its selected-profile range and step. |
| `conflict_intensity` | `0`: no optional profile-created ambient conflict pressure; `100`: maximum authorized conflict pressure. Higher is more intense. | Discrete monotonic pressure; `0` cannot suppress authored required conflict. | Yes, only within the selected profile's range below. | None beyond its selected-profile range and step. |

### Numeric resource-pressure authority and categorical deferral

P3.3-S2 resolves only the exact numeric objective value
`resource_pressure`. The product labels `Scarce`, `Fluid`, and `Generous` are
not S2 resolver inputs, S2 profile identities, S2 override values, S1
presentation fields, alternative objective values, or currently implemented
runtime authority. No categorical label, including a case or spelling variant,
may be accepted as an alias for a numeric S2 value.

P3.3-S5 alone owns the separately reviewed exact numeric-to-categorical
mechanics and prompt projection. P3.3-S6 alone owns any separately reviewed
public API, OpenAPI, Demo, Web, projection, recovery, or client representation
of the labels. Neither slice may change, round, clamp, replace, or otherwise
reinterpret the numeric S2 value; each may only define a separately reviewed
projection from that already-resolved exact value.

Until P3.3-S5 and P3.3-S6 are each independently planned, approved,
implemented, and published, no categorical projection is authoritative, the
illustrative `[RUN_PROTOCOL]` block in `docs/run_protocol.md` is not
implemented, and no exact threshold, band, or other numeric-to-categorical
mapping exists. S2 emits no categorical resource-pressure value.

The compatibility domain is deliberately the Cartesian product of the five
validated per-profile ranges. There is no sum, ratio, ordering, coupling,
hidden sixth parameter, or presentation-dependent constraint. Cooperation cost
and betrayal incentive in product prose are composite interpretations of
resource pressure, social trust, and conflict intensity; they are not extra
S2 values.

## 5. Versioned profile catalogue and defaults

The authorized catalogue version is embedded in the code and resolver-v1
contract. It contains exactly the following three entries in the displayed
catalogue order and no aliases. Every profile version is the positive integer
`1`.

| Stable ID/version | Human label | Product interpretation | Server-selected default |
| --- | --- | --- | --- |
| `difficulty.silent-hunting-ground` / `1` | `Extreme — Silent Hunting Ground` | Extreme scarcity, severe consequences, opaque information, very low trust, high cooperation cost, high betrayal incentive, and dark-forest-like conflict. | Never. S2 has no default-selection rule. |
| `difficulty.fragile-alliance` / `1` | `Standard — Fragile Alliance` | Local scarcity, earned trust, meaningful cooperation and betrayal, with betrayal possible but not universal. | Never. S2 has no default-selection rule. |
| `difficulty.open-expedition` / `1` | `Easier — Open Expedition` | Sufficient resources, more common trade/rescue/cooperation, lower betrayal incentive, and lower but nonzero conflict. | Never. S2 has no default-selection rule. |

Exact base values are:

| Profile ID/version | `resource_pressure` | `social_trust` | `consequence_severity` | `information_opacity` | `conflict_intensity` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `difficulty.silent-hunting-ground` / `1` | 95 | 10 | 95 | 90 | 90 |
| `difficulty.fragile-alliance` / `1` | 60 | 45 | 65 | 60 | 60 |
| `difficulty.open-expedition` / `1` | 25 | 70 | 35 | 30 | 35 |

An explicitly selected exact `(profile_id, profile_version)` in a validated S1
envelope is mandatory. Missing, unknown, retired, or unsupported pairs raise
`RunProtocolProfileLookupError`. The initial retired-pair set is empty; a
future retired pair is not an alias and is absent from the active resolver-v1
catalogue. There is no silent Standard selection, case folding, alias, nearest
version, upgrade, downgrade, fallback, or configured runtime catalogue.

A future server default would require a separately reviewed versioned rule and
cannot be inferred from absence. Character or difficulty recommendations are
display advice only. S2 accepts no recommendation field, and a recommendation
cannot select a profile, create an override, or mutate a value.

## 6. Exhaustive override authority and matrix

Only a human player may propose objective overrides, through a future trusted
pre-entry boundary. The trusted server must confirm the exact selected profile
pair, the exact parameter/value pairs the player approved, and the full matrix
below before calling S2. A caller, client, character model, Provider, prompt,
generated narrative, configuration file, or recommendation supplies no
authority. S2 has no public/runtime integration, so its future pure entry point
is internal and assumes the passed proposal is the exact player-confirmed
proposal; it still revalidates every key and value against this allowlist.

Every listed range is inclusive and uses step `5`. No parameter outside the
five-row allowlist exists.

| Parameter | Extreme range | Standard range | Easier range | Proposer | Authorizer |
| --- | ---: | ---: | ---: | --- | --- |
| `resource_pressure` | 80..100 | 40..75 | 10..40 | Human player | Trusted pre-entry server policy after exact confirmation |
| `social_trust` | 0..25 | 30..65 | 55..85 | Human player | Trusted pre-entry server policy after exact confirmation |
| `consequence_severity` | 80..100 | 45..80 | 20..50 | Human player | Trusted pre-entry server policy after exact confirmation |
| `information_opacity` | 75..100 | 40..75 | 15..45 | Human player | Trusted pre-entry server policy after exact confirmation |
| `conflict_intensity` | 75..100 | 40..75 | 20..50 | Human player | Trusted pre-entry server policy after exact confirmation |

The exhaustive structural rules are:

1. The proposal contains the exact selected profile reference and an explicit
   tuple of zero through five entries. An explicit empty tuple means no
   overrides; the argument itself has no default and cannot be omitted.
2. Each entry has exactly `parameter` and `value`; both fields are required.
3. Unknown keys, missing values, extra fields, raw strings in enum positions,
   Boolean-as-integer, enum/subclass integers, floats, coercion, values outside
   `0..100`, wrong-step values, and values outside the selected profile's
   narrower range reject the complete proposal.
4. Two entries for one parameter are always a duplicate and reject the whole
   proposal, even when their values are equal. There is no last/first winner.
5. The proposal profile reference must equal the envelope profile reference
   and the looked-up catalogue entry. A mismatch is contradictory trusted input
   and fails before final values or fingerprint construction.
6. Valid entries are copied into a new immutable set in this exact canonical
   order: `resource_pressure`, `social_trust`, `consequence_severity`,
   `information_opacity`, `conflict_intensity`. Caller order and source-mapping
   insertion order have no effect.
7. An absent key means use the selected profile base value. It is not a missing
   entry value and does not create an implicit override.
8. An override equal to its profile base is preserved as an explicit entry.
   Override presence remains separately represented in the resolution input
   and fingerprint even when the final scalar equals the base.
9. The five per-profile ranges are the entire compatibility matrix. Every
   Cartesian combination of valid per-parameter entries is compatible; no
   additional cross-parameter correction, clamp, or hidden rule exists.
10. On any error there is no partial override set, final output, or
    fingerprint.

## 7. Presentation-only separation

The S1 values remain exactly:

- `world_tone`: `grim`, `balanced`, `heroic`;
- `reality_boundary`: `lawful`, `deviant`, `chaotic`; and
- `relationship_overlay`: `off`, `veiled`, `charged`.

The resolver validates and binds the entire canonical S1 envelope for identity
and audit. It never branches on these three fields while constructing base or
final objective values. There is no presentation-to-mechanics lookup,
recommendation, alias, default, or compatibility rule.

For every exact profile and every valid override set, the complete 3 × 3 × 3
presentation cross-product must resolve to identical objective values. The
fingerprint normally differs because the canonical envelope bytes are
audit-bound; objective equality and input identity are separate facts.

### Direct exhaustive finite-domain execution

The future implementation must place the universal positive-contract test in
`tests/unit/test_run_protocol_resolution.py`. The sole accepted method is
direct generation and execution of every finite valid combination through the
public S2 facade `resolve_run_protocol_objectives`. Source inspection, a static
or property argument in place of execution, representative cases, random or
Hypothesis sampling, partial enumeration, and deduplication or short-circuiting
of combinations do not satisfy this contract.

The test oracle must be independent of
`RUN_PROTOCOL_PROFILE_CATALOGUE_V1`. It must define the following literal
profile IDs, versions, five-value defaults, and permitted-value tuples directly
in the test. Production catalogue values may be compared with these literals
but may not create, parameterize, or alter the expected oracle:

| Exact profile ID/version | Default tuple in product order | `resource_pressure` | `social_trust` | `consequence_severity` | `information_opacity` | `conflict_intensity` |
| --- | --- | --- | --- | --- | --- | --- |
| `difficulty.silent-hunting-ground` / `1` | `(95, 10, 95, 90, 90)` | `(80, 85, 90, 95, 100)` | `(0, 5, 10, 15, 20, 25)` | `(80, 85, 90, 95, 100)` | `(75, 80, 85, 90, 95, 100)` | `(75, 80, 85, 90, 95, 100)` |
| `difficulty.fragile-alliance` / `1` | `(60, 45, 65, 60, 60)` | `(40, 45, 50, 55, 60, 65, 70, 75)` | `(30, 35, 40, 45, 50, 55, 60, 65)` | `(45, 50, 55, 60, 65, 70, 75, 80)` | `(40, 45, 50, 55, 60, 65, 70, 75)` | `(40, 45, 50, 55, 60, 65, 70, 75)` |
| `difficulty.open-expedition` / `1` | `(25, 70, 35, 30, 35)` | `(10, 15, 20, 25, 30, 35, 40)` | `(55, 60, 65, 70, 75, 80, 85)` | `(20, 25, 30, 35, 40, 45, 50)` | `(15, 20, 25, 30, 35, 40, 45)` | `(20, 25, 30, 35, 40, 45, 50)` |

The parameter order used by this independent data and by every product is
exactly:

1. `resource_pressure`;
2. `social_trust`;
3. `consequence_severity`;
4. `information_opacity`; and
5. `conflict_intensity`.

The test must create exactly one sentinel with `ABSENT = object()` and compare
it only by identity. For each parameter dimension, its generation domain is a
tuple containing `ABSENT` first and then every independently specified valid
integer above in ascending numeric order. For each Cartesian product element,
the test constructs an override mapping in the fixed parameter order, omits
only sentinel-valued parameters, and retains every explicitly present integer.
An explicitly present integer equal to the selected profile default remains in
the mapping and in the resulting proposal; it is never normalized away.

Before the first resolver call, the test must materialize the complete mapping
sets and assert these exact counts:

- Extreme:
  `(5 + 1) × (6 + 1) × (5 + 1) × (6 + 1) × (6 + 1) = 12,348`;
- Standard: `9^5 = 59,049`;
- Easier: `8^5 = 32,768`; and
- complete override-map count:
  `12,348 + 59,049 + 32,768 = 104,165`.

Presentation input is also an independent literal oracle. The test must define
this exact tuple, which is in fixed nested order with `world_tone` outermost,
`reality_boundary` next, and `relationship_overlay` innermost:

```text
(
  ("grim", "lawful", "off"),
  ("grim", "lawful", "veiled"),
  ("grim", "lawful", "charged"),
  ("grim", "deviant", "off"),
  ("grim", "deviant", "veiled"),
  ("grim", "deviant", "charged"),
  ("grim", "chaotic", "off"),
  ("grim", "chaotic", "veiled"),
  ("grim", "chaotic", "charged"),
  ("balanced", "lawful", "off"),
  ("balanced", "lawful", "veiled"),
  ("balanced", "lawful", "charged"),
  ("balanced", "deviant", "off"),
  ("balanced", "deviant", "veiled"),
  ("balanced", "deviant", "charged"),
  ("balanced", "chaotic", "off"),
  ("balanced", "chaotic", "veiled"),
  ("balanced", "chaotic", "charged"),
  ("heroic", "lawful", "off"),
  ("heroic", "lawful", "veiled"),
  ("heroic", "lawful", "charged"),
  ("heroic", "deviant", "off"),
  ("heroic", "deviant", "veiled"),
  ("heroic", "deviant", "charged"),
  ("heroic", "chaotic", "off"),
  ("heroic", "chaotic", "veiled"),
  ("heroic", "chaotic", "charged"),
)
```

The test must also generate those values from the three independently written
tuples `("grim", "balanced", "heroic")`,
`("lawful", "deviant", "chaotic")`, and
`("off", "veiled", "charged")`, assert exact tuple equality with the
27-element literal tuple above, and assert `3 × 3 × 3 = 27` before resolution.
Neither the production catalogue nor production enum iteration may generate
this oracle.

For every one of the `104,165` profile/override maps, the test must start from
the independent five-value default, replace only keys explicitly present in the
generated mapping, and leave every absent key at that default. Acceptance is
established only when all 27 primary public resolver calls and all 27 immediate
repeat public resolver calls return a result. For each of those 27 primary
resolved results, assert all of the following:

1. the five objective values equal that independently computed tuple;
2. the resolution identifies the exact expected profile ID and version;
3. every explicitly present override remains present in the canonical
   resolution input, including an equal-to-default value;
4. every absent override key remains absent;
5. canonical override order is exactly the fixed five-parameter order filtered
   only by presence; and
6. no cross-parameter compatibility rejection occurs.

For each fixed profile/override map, the test must call
`resolve_run_protocol_objectives` for all 27 presentation combinations. The
first combination supplies only the comparison baseline for objective values.
Every primary result must equal the independent expected objective tuple and
the first primary result's objective tuple. The three presentation field names
and their values must be absent from the five-field objective carrier and must
never alter an objective value. Fingerprints may differ because the complete
canonical S1 envelope is audit-bound; the test must not require presentation
variants to share fingerprints.

The positive test traversal and call order is frozen for every exact trusted
profile/override/presentation input:

1. select the profile in the existing fixed Extreme, Standard, Easier order;
2. generate the override map in the existing fixed Cartesian order;
3. select the presentation triple in the existing fixed presentation order;
4. make one primary call to public `resolve_run_protocol_objectives`;
5. validate the primary result against the independently constructed expected
   result and the assertions above;
6. immediately make one repeat call to the same public callable using the exact
   same trusted input objects, or an exactly equivalent permitted detached input
   only where the relevant test expressly specifies detached reconstruction;
7. compare the primary and repeat results for exact equality of the complete
   resolved objective output, canonical resolution-input bytes, and fingerprint;
   and
8. increment the primary counter only after the primary public call returned
   successfully and the separate repeat counter only after the repeat public
   call returned successfully, then later assert every separately classified
   counter below.

The repeat call is a real second invocation of public
`resolve_run_protocol_objectives`. It must not be replaced by reuse of the
primary result, memoized test data, comparison of an object with itself, an
internal-helper call, source inspection, or a cached assertion that suppresses
the public invocation. It is immediate for its exact input and may not be
deferred to an unspecified later pass.

The test must keep separate semantic counters equivalent to primary count per
profile, repeat count per profile, aggregate primary count, aggregate repeat
count, combined count per profile, and aggregate combined public invocation
count. Exact private variable names are not prescribed. After the complete
traversal, separately assert:

- primary public calls:
  - Extreme: `12,348 × 27 = 333,396`;
  - Standard: `59,049 × 27 = 1,594,323`;
  - Easier: `32,768 × 27 = 884,736`; and
  - aggregate primary: `333,396 + 1,594,323 + 884,736 = 2,812,455`;
- repeat public calls:
  - Extreme: `333,396`;
  - Standard: `1,594,323`;
  - Easier: `884,736`; and
  - aggregate repeat: `333,396 + 1,594,323 + 884,736 = 2,812,455`;
- combined public-resolver invocations:
  - Extreme: `333,396 + 333,396 = 666,792`;
  - Standard: `1,594,323 + 1,594,323 = 3,188,646`;
  - Easier: `884,736 + 884,736 = 1,769,472`; and
  - aggregate combined public invocations:
    `2,812,455 + 2,812,455 = 5,624,910`.

The normative meanings remain distinct: there are `2,812,455` distinct trusted
inputs, `2,812,455` primary public calls, `2,812,455` repeat public calls, and
`5,624,910` aggregate public resolver invocations. A repeat call does not create
or replace a distinct trusted input.

Every one of the `2,812,455` distinct trusted inputs must actually reach the
public resolver once as a primary call and immediately once as a repeat call.
No combination or required invocation may be skipped, sampled,
short-circuited, deduplicated, or replaced by source inspection. An ordinary
test implementation optimization is permitted only when all `2,812,455`
primary public calls, all `2,812,455` repeat public calls, all `5,624,910`
aggregate public resolver invocations, and every required assertion still
occur.

Invalid evidence is a separate negative matrix and contributes zero to the
`104,165` map count and zero to the `2,812,455` distinct-input count. It must
retain exact cases for unknown keys, duplicate keys, missing values, wrong exact
types, Boolean-as-integer, enum and subclass values where applicable, values
outside global `0..100`, values outside the selected profile range, wrong step,
unknown profile, unsupported version, S1 and S2 corruption under their exact
owners, and contradictory profile references. Expected failures never satisfy
or increment a positive distinct-input count or any primary, repeat,
per-profile combined, or aggregate combined public-invocation counter.

## 8. Complete authority and precedence algorithm

The future dispatcher must execute these steps in order and return nothing on
failure:

1. **Resolver selection:** require keyword-only exact `str` epoch
   `run-protocol-resolution` and exact non-Boolean `int` version `1`. Malformed
   selectors are integrity errors; a well-typed unsupported pair raises the
   dedicated unsupported-version exception before reading the envelope.
2. **S1 validation:** require the exact `RunProtocolEnvelopeV1`, revalidate its
   complete original/nested Pydantic state, and produce its canonical bytes
   through `validate_run_protocol_envelope_v1` and
   `encode_run_protocol_envelope_v1`. A wrong exact top-level type raises the
   published `TypeError`; corruption of the envelope, its embedded
   `RunProtocolProfileRefV1`, any presentation enum, or any other nested
   S1-owned carrier raises `RunProtocolValidationError`. S2 does not catch,
   wrap, translate, or replace either outcome.
3. **Profile lookup:** pass the envelope's exact profile reference to
   `lookup_run_protocol_profile`, which performs the complete deterministic
   caller-S1, catalogue-S2, nested-catalogue-S1, match, and return order frozen
   below. Use only its exact ID/version to select the returned authoritative
   resolver-v1 catalogue object. Missing, unknown, retired, or unsupported
   pairs fail; no default is consulted.
4. **Context identity:** consume no scenario, content, Run, line, Session,
   world, visit, region, character, clock, or server-issued identity. None is
   applicable to S2's global non-random profile resolution.
5. **Recommendations:** accept no recommendation input. Character/difficulty
   recommendations are ignored before this boundary and cannot select or
   mutate anything.
6. **Override validation:** require the explicit player-approved proposal,
   validate its contained S1 profile-reference carrier through the exact S1
   adapter below before validating S2-owned proposal state, with post-
   construction S1 corruption retaining `RunProtocolValidationError` and its
   cause behavior; bind its profile reference to steps 2–3, reject duplicates/
   unknowns/missing or invalid values, and copy valid entries into canonical
   parameter order. No S1-owned failure is wrapped or translated to an S2
   exception.
7. **Compatibility:** validate every entry against the selected profile's exact
   allowlist/range/step. There is no further cross-parameter rule.
8. **Final values:** start with a new immutable copy of the five catalogue base
   values, then replace exactly the keys present in the canonical override set.
   Build fields explicitly in the fixed parameter order; never iterate an
   unordered mapping to define semantics.
9. **Resolution input:** construct the strict immutable v1 carrier and exact
   canonical byte sequence defined below from resolver version, authorized
   profile pair, canonical S1 envelope bytes, and exact override presence.
10. **Fingerprint:** hash the exact domain-separated, length-framed preimage
    below and emit lowercase hexadecimal SHA-256.
11. **Resolved output:** return one new immutable carrier containing the
    validated resolution input, final five values, and fingerprint. Revalidate
    the complete owner-specific nested original state before every public
    encode/fingerprint/resolve operation. Each S1-owned object is validated
    before any semantic read of that object's internals. Catalogue validation
    follows the exact outer-S2/association-S2/nested-S1 order below; S2
    integrity validation applies only to S2-owned state.

No step falls back, repairs, coerces, clamps, rounds, chooses a nearest value,
changes profile/version, drops an equal override, or accepts mutated state.

### Owner-specific corruption and exception order

Ownership is field-level and never propagates from an outer carrier into an
embedded carrier owned by another slice. Validation may inspect only the S2
outer shape needed to locate an embedded S1 object; it must not run a generic
recursive S2 validation that converts an S1 failure into
`RunProtocolResolutionIntegrityError`.

The exact published S1 distinctions remain:

| S1 boundary/state | Exact published outcome |
| --- | --- |
| Direct invalid construction of `RunProtocolProfileId`, `RunProtocolProfileVersion`, `RunProtocolProfileRefV1`, or `RunProtocolEnvelopeV1` | `pydantic.ValidationError` |
| Direct invalid S1 presentation-enum token | `ValueError` |
| `validate_run_protocol_envelope_v1` or `encode_run_protocol_envelope_v1` receives the wrong exact top-level type | `TypeError` |
| `validate_run_protocol_envelope_v1` or `encode_run_protocol_envelope_v1` detects malformed or corrupted state in an exact envelope, its embedded profile reference, a presentation enum, another nested S1 carrier, canonical state, or canonical bytes | `RunProtocolValidationError` |
| `decode_run_protocol_envelope` receives malformed selectors or payload | `RunProtocolValidationError` |
| `decode_run_protocol_envelope` receives a well-typed unsupported envelope epoch/version | `UnsupportedRunProtocolVersionError`, the published subclass of `RunProtocolValidationError` |
| Published no-I/O storage conversion or reconstruction rejects its stored boundary | `RunProtocolStoredRecordIntegrityError`, retaining the published domain cause distinctions |

S2 does not invoke the S1 storage boundary, but it must not intercept or
reclassify a `RunProtocolStoredRecordIntegrityError` produced before S2. A
required S1 slot missing from an already-corrupted S2 carrier is S2 outer-state
corruption; once an exact S1 object is present, mutation anywhere inside that
object remains S1-owned and follows the table above.

`RunProtocolResolutionIntegrityError` applies only to S2-owned override
proposal/set state outside embedded S1 objects, resolution-input and
resolved-output state outside embedded S1 objects, the exact catalogue state
enumerated below, S2 objective/rule carriers, and S2 fingerprint or canonical-
input state. This split is mandatory for every validation, encode, fingerprint,
resolve, lookup, and corruption-test path.

#### Exact catalogue field ownership

The complete S2-owned catalogue state is exactly:

1. the public `RUN_PROTOCOL_PROFILE_CATALOGUE_V1` binding's association with the
   one authoritative tuple, plus that tuple's exact built-in `tuple` type,
   cardinality three, frozen entry order, and three authoritative entry object
   identities;
2. each authoritative entry's exact `RunProtocolProfileDefinitionV1` type and
   identity; exact `__dict__` field names `profile_ref`, `label`, `base_values`,
   `override_rules`, and `server_default_eligible`; exact
   `__pydantic_fields_set__`; and empty-or-absent `__pydantic_extra__` and
   `__pydantic_private__` state;
3. `label`, including its exact `str` type and the exact per-entry literal in
   the profile table;
4. `base_values`, including its association from the entry, exact
   `ObjectiveParameterValuesV1` type and original-state metadata, the exact
   fields `resource_pressure`, `social_trust`, `consequence_severity`,
   `information_opacity`, and `conflict_intensity`, and each field's exact
   `ObjectiveParameterValue` type, original-state metadata, and `value`;
5. `override_rules`, including its association from the entry, exact built-in
   `tuple` type, cardinality five, fixed parameter order, and each rule's exact
   `RunProtocolOverrideRuleV1` type and original-state metadata; within each
   rule, the exact fields `parameter`, `minimum`, `maximum`, and `step`, the
   exact `ObjectiveParameterName` member, the exact
   `ObjectiveParameterValue` types and `value` fields for `minimum` and
   `maximum`, and exact non-Boolean integer `step == 5`;
6. `server_default_eligible`, whose exact value and type are
   built-in `bool` value `False` under the declared `Literal[False]`; and
7. `RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER`, including its association with the
   one authoritative tuple, exact built-in `tuple` type, cardinality five, and
   exact five members in product order.

For items 2, 4, and 5, "original-state metadata" has one closed meaning for
every listed S2 Pydantic carrier: exact declared `__dict__` keys, exact
`__pydantic_fields_set__`, and empty-or-absent `__pydantic_extra__` and
`__pydantic_private__`. Removal, duplication, or reordering of catalogue
entries; replacement of the tuple; replacement of an authoritative entry by a
newly constructed structurally equal entry; and mutation of any state in items
1–7 are S2 corruption and raise exactly
`RunProtocolResolutionIntegrityError`.

The complete S1-owned state nested in each catalogue entry is exactly the
already-associated `RunProtocolProfileRefV1` object; its exact carrier type;
its own original-state metadata; its `profile_id` and `profile_version` fields;
the nested `RunProtocolProfileId` and `RunProtocolProfileVersion` exact types,
original-state metadata, and `value` fields; and all published exact-type,
normalization, domain, validation, and original-state invariants for those S1
carriers. Corruption inside this already-associated object must raise the exact
published S1 outcome. S2 must not catch, wrap, translate, replace, or add a
cause layer to that outcome.

The boundary at the entry's `profile_ref` field is deliberately split without
overlap. Presence of the field and its association by object identity with the
one profile-reference object originally installed in that authoritative entry
are S2 catalogue structure. Internal state of that already-associated object is
S1 state. Rebinding `profile_ref` to any different object is S2 corruption even
when the replacement is structurally equal or independently malformed;
mutation inside the same already-associated object is S1 corruption. No object,
field value, or association matches both classifications.

#### Exact S1 profile-reference validation adapter

S1 publishes no standalone profile-reference validator. Therefore every S2
boundary that receives an already-constructed exact
`RunProtocolProfileRefV1` must use one private adapter to the actual published
S1 validation boundary. The adapter embeds the same reference object by
identity in an otherwise-valid private envelope created with
`RunProtocolEnvelopeV1.model_construct`, explicitly setting
`_fields_set` to exactly `schema_version`, `profile_ref`, `world_tone`,
`reality_boundary`, and `relationship_overlay`, supplying exactly those five
fields, using exact schema `run-protocol-envelope/v1`, and fixed presentation values
`RunProtocolWorldTone.BALANCED`, `RunProtocolRealityBoundary.LAWFUL`, and
`RunProtocolRelationshipOverlay.OFF`. It then calls
`validate_run_protocol_envelope_v1` and performs no S2 catch or translation.
The private envelope is validation scaffolding only; it is never resolved,
encoded, fingerprinted, returned, or used as presentation or objective input.

A wrong exact top-level type at an S2 callable remains that callable's specified
`TypeError`. Once the top-level value is an exact `RunProtocolProfileRefV1`,
the adapter preserves the published `RunProtocolValidationError` and its direct
cause behavior for hostile original-state corruption. This adapter is used for
both a caller-supplied lookup reference and an authoritative catalogue entry's
already-associated nested reference.

#### Deterministic catalogue lookup and first-failure order

`lookup_run_protocol_profile` must execute this exact sequence and stop at the
first failure:

1. require the caller-supplied `profile_ref` to have exact top-level type
   `RunProtocolProfileRefV1`, otherwise raise `TypeError`;
2. pass that same object through the exact S1 adapter above, propagating its
   published S1 outcome unchanged;
3. validate the S2 catalogue outer state in this order: exact built-in tuple
   type, identity of the authoritative catalogue tuple, cardinality three,
   authoritative entry identities at positions Extreme then Standard then
   Easier, and the complete
   `RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER` state from item 7 above;
4. for each entry in that frozen Extreme, Standard, Easier order:
   1. validate exact `RunProtocolProfileDefinitionV1` type and identity, then
      the entry's exact outer original-state metadata without recursively
      validating `profile_ref`;
   2. validate S2 fields in this exact order: `label`; `base_values` and its
      five fields in product order; `override_rules` and its five rules in
      product order, with each rule checked as `parameter`, `minimum`,
      `maximum`, then `step`; and `server_default_eligible`;
   3. require the `profile_ref` field to remain associated by identity with the
      exact catalogue-owned reference originally installed in that entry; and
   4. pass that already-associated reference through the exact S1 adapter,
      propagating its published outcome unchanged;
5. only after the complete catalogue passes, compare the validated caller
   reference's exact profile ID/version with the three entries in frozen order;
   an absent pair raises `RunProtocolProfileLookupError`; and
6. return the matching authoritative `RunProtocolProfileDefinitionV1` object
   itself, never a copy, reconstruction, fallback, or equal replacement.

This sequence also fixes every multiple-corruption outcome. Caller-reference S1
failure precedes every catalogue failure. Catalogue tuple/parameter-order
failure precedes entry failure. An earlier entry and earlier S2 field in the
orders above precede a later one. Within one entry, S2 field failure precedes
association failure, association failure precedes nested S1 validation, and a
malformed replacement `profile_ref` therefore raises exactly
`RunProtocolResolutionIntegrityError` without inspection of the replacement.
Only internal corruption of the still-associated object reaches S1 and raises
its exact published exception. Complete catalogue validation precedes unknown-
pair matching. No consumer may reorder, bypass, duplicate, or partially repeat
these checks.

## 9. Failure and incompatibility matrix

| Failure | Exact outcome |
| --- | --- |
| Missing profile reference/field during direct S1 construction | `pydantic.ValidationError`; no S2 lookup |
| Unknown, retired, or unsupported profile pair | `RunProtocolProfileLookupError` |
| Malformed resolver selector | `RunProtocolResolutionIntegrityError` |
| Well-typed unsupported resolver pair | `UnsupportedRunProtocolResolverVersionError` |
| Wrong exact S1 envelope top-level type | Published S1 `TypeError`, unchanged |
| Mutation/corruption of an exact S1 envelope or its nested S1 state, or of an exact standalone profile reference passed through the required S1 adapter | Published `RunProtocolValidationError` and cause behavior unchanged; no S2 output/fingerprint |
| Malformed S1 dispatcher input or well-typed unsupported S1 pair | Published `RunProtocolValidationError` or `UnsupportedRunProtocolVersionError`, respectively; S2 does not translate either |
| S1 stored-carrier corruption before S2 | Published `RunProtocolStoredRecordIntegrityError`; S2 does not translate it |
| Proposal/envelope/catalogue profile contradiction | `RunProtocolOverrideValidationError` |
| Duplicate override | `RunProtocolOverrideValidationError` |
| Unknown override key or missing value | Direct `pydantic.ValidationError`; if S2-owned validated state is mutated to contain it, `RunProtocolResolutionIntegrityError` |
| Invalid scalar exact type, Boolean-as-integer, enum, or subclass | Direct `pydantic.ValidationError`; if S2-owned validated state is mutated to contain it, `RunProtocolResolutionIntegrityError` |
| Global out-of-range or wrong-step value | Direct `pydantic.ValidationError`; if S2-owned validated state is mutated to contain it, `RunProtocolResolutionIntegrityError` |
| Selected-profile range violation | `RunProtocolOverrideValidationError` |
| Cross-parameter combination after all individual checks | Valid; the compatibility domain is the Cartesian product |
| Recommendation, scenario/content, server identity, seed, or arbitrary extra input | Python `TypeError` for the closed signature or direct `pydantic.ValidationError` for an extra carrier field |
| `Scarce`, `Fluid`, `Generous`, or any categorical resource-pressure alias/projection | Rejected at the closed signature/carrier boundary; never converted to a numeric value |
| Equal-to-base override | Valid and preserved as present |
| Mutation/corruption of S2-owned state after validation | `RunProtocolResolutionIntegrityError`; no output/fingerprint |
| Mapping insertion-order difference with identical entries | Same canonical override set, bytes, output, and fingerprint |
| Corruption of an exact S2-owned catalogue component enumerated in items 1–7 above | `RunProtocolResolutionIntegrityError`; no alternate catalogue/default |
| Corruption inside the still-associated `RunProtocolProfileRefV1` of an authoritative catalogue entry | Published `RunProtocolValidationError` and direct cause behavior unchanged; no S2 wrapper, translation, fallback, or output |

## 10. Resolver versioning and absence of a seed

The proposed resolver epoch is `run-protocol-resolution`; the only supported
version is exact integer `1`, with schema string
`run-protocol-resolution/v1`. The selector is a required, trusted,
keyword-only internal input. Caller-controlled absence cannot select v1 or a
legacy path. Future dispatch must be an explicit new branch with a separately
published plan, compatibility policy, vectors, and authorization. There is no
implicit upgrade or downgrade.

S2 performs no stochastic selection. It consumes no entropy, randomness, PRNG,
or numeric seed and defines no seed bytes. It therefore does not invent a
server-issued Run or other identity. Python `hash()`, `random`, clocks, process
state, mapping order, locale, time zone, Provider output, and client entropy are
prohibited. The canonical resolution input and deterministic fingerprint are
the complete reproducibility boundary.

The repository has trusted scenario/content-version fields only after loading
and validating the applicable catalogues. S2 has no scenario-specific profile
rule and no trusted selected scenario input, so those versions are not relevant
to this global resolution and are excluded. `scenario_id` remains scenario
identity only. No existing trusted server-issued identity is needed or
authorized for this algorithm.

## 11. Canonical resolution input and fingerprint

### 11.1 Exact canonical input object

The input bytes are one compact JSON object with exactly six fields. All keys
and string values are ASCII and therefore already NFC. Encoding is UTF-8 with
no BOM, sorted object keys, separators exactly `,` and `:`, no whitespace, and
direct characters rather than optional escaping. Numbers use the exact decimal
spelling above. No `null`, Boolean, float, non-finite number, optional field,
alias, duplicate member, or extra member is admitted.

Sorted root field order is exactly:

1. `authorized_overrides`;
2. `authorized_profile_id`;
3. `authorized_profile_version`;
4. `canonical_envelope_hex`;
5. `resolver_version`; and
6. `schema`.

Each override object has exactly `parameter` then `value`. The override array
uses the fixed product parameter order. No overrides is represented by `[]`,
never omission or `null`.

`canonical_envelope_hex` is the lowercase two-hex-digits-per-byte encoding of
the complete result of `encode_run_protocol_envelope_v1`. It binds every S1
byte, including presentation fields, without JSON-in-JSON escape ambiguity.
The repeated authorized profile ID/version must exactly match the envelope and
catalogue entry; the redundancy detects contradictory trusted state.

The canonical byte sequence must be between 1 and
`MAX_RUN_PROTOCOL_RESOLUTION_INPUT_BYTES = 1_024` bytes inclusive. Exhaustive
enumeration of the three v1 profiles, 27 presentation combinations, and every
valid override-presence/value combination establishes the genuine current
maximum as 863 bytes: Extreme with `balanced`/`deviant`/`charged` and all five
overrides at `100,25,100,100,100`. Thus 161 bytes are defensive version
headroom. A test may isolate the 1,024/1,025 encoder guard but must label that
evidence defensive, not a currently reachable carrier.

### 11.2 Included and excluded fields

| Field | Why included |
| --- | --- |
| Resolver version | Selects the exact algorithm/catalogue/encoding contract. |
| Authorized profile ID/version | Selects the exact static defaults and override matrix. |
| Complete canonical S1 envelope bytes as lowercase hex | Binds the strict selected profile reference and all presentation identity without granting presentation mechanics authority. |
| Exact canonical override array, including equal-to-base presence | Binds every authorized player deviation from the profile and distinguishes absence from explicit equality. |

Final values are derived, not a second input. Human labels and prose are
excluded because they are non-mechanical display text. Scenario/content,
character, Run/line/Session, world/visit/region, and server identity are
excluded because no S2 rule consumes them. Recommendations are excluded because
they have no authority. Time, locale, environment, process state, mapping
order, Provider/model data, and entropy are excluded because they are
nondeterministic or untrusted.

### 11.3 Fingerprint preimage

The exact public domain constant is the 57 ASCII bytes:

```text
deviation-protocol:run-protocol-resolution-fingerprint:v1
```

The fingerprint preimage is, in order:

1. those 57 bytes;
2. one `00` byte;
3. the canonical-input byte length as one unsigned 32-bit big-endian integer;
4. the exact canonical input bytes.

The algorithm is SHA-256. The carrier representation is exactly 64 lowercase
ASCII hexadecimal characters. Uppercase, prefixes, raw 32-byte values, or
other hash algorithms are not accepted. The maximum preimage is 1,086 bytes.

For equivalent trusted values, final objective values, canonical input bytes,
and the fingerprint must be identical across mapping insertion order, Python
hash seed, process, operating system, locale, time zone, repeated execution,
and legitimate detached reconstruction. Detached reconstruction begins from a
trusted profile ID/version, reacquires the exact authoritative
`RunProtocolProfileDefinitionV1` through `lookup_run_protocol_profile`, and
then combines that catalogue-owned object with freshly reconstructed
value-authoritative carriers. The catalogue profile object must never be
reconstructed, copied, deserialized, or replaced by a structurally equal
object.

Fresh reconstruction is permitted only for value-authoritative carriers: the
S1 envelope through its published decoder/reconstruction boundary, authorized
override proposals, S2 resolution-input carriers, equivalent immutable scalar
and collection values, and any other explicitly value-authoritative proposal
or input carrier. Those fresh carriers plus the reacquired catalogue object
must produce identical objective output, canonical resolution input, and
fingerprint. Catalogue object identity is checked as authority but is neither
serialized nor hashed; re-lookup restores that authority, so the identity rule
does not prevent legitimate detached resolution. No other object identity or
validation history is serialized or hashed.

## 12. Independently reproduced golden vectors

The vectors below were constructed using only the frozen field/ordering rules.
Their bytes and hashes were generated by Python standard-library JSON,
`struct`, and `hashlib`, then independently reconstructed from literal field
concatenation and verified with .NET UTF-8 and SHA-256. Neither implementation
uses current or proposed production S2 code.

For output tables, the field order is always `resource_pressure`,
`social_trust`, `consequence_severity`, `information_opacity`,
`conflict_intensity`.

### RPRES-V1-001 — Standard, no overrides

Carrier: profile `difficulty.fragile-alliance`/`1`, presentation
`balanced`/`lawful`/`off`, explicit empty override tuple.

Canonical S1 envelope, 205 bytes, SHA-256
`a8fb2964e1c50a1428b33277426098cec69b0c19a33673abf0617d39d00ca2ab`:

```json
{"profile_ref":{"profile_id":"difficulty.fragile-alliance","profile_version":1},"reality_boundary":"lawful","relationship_overlay":"off","schema_version":"run-protocol-envelope/v1","world_tone":"balanced"}
```

Canonical resolution input, 609 bytes:

```json
{"authorized_overrides":[],"authorized_profile_id":"difficulty.fragile-alliance","authorized_profile_version":1,"canonical_envelope_hex":"7b2270726f66696c655f726566223a7b2270726f66696c655f6964223a22646966666963756c74792e66726167696c652d616c6c69616e6365222c2270726f66696c655f76657273696f6e223a317d2c227265616c6974795f626f756e64617279223a226c617766756c222c2272656c6174696f6e736869705f6f7665726c6179223a226f6666222c22736368656d615f76657273696f6e223a2272756e2d70726f746f636f6c2d656e76656c6f70652f7631222c22776f726c645f746f6e65223a2262616c616e636564227d","resolver_version":1,"schema":"run-protocol-resolution/v1"}
```

Preimage length: 671. Fingerprint:
`2cca2a7d1bc1308ca6c0cb93b440eb0f5152ecbcda313162b7c9e6ab49f795ac`.
Resolved output: `60,45,65,60,60`.

### RPRES-V1-002 — valid Extreme overrides and reversed source order

Carrier: profile `difficulty.silent-hunting-ground`/`1`, presentation
`grim`/`deviant`/`charged`; source proposal order `social_trust=20`, then
`resource_pressure=85`. Canonical order is the reverse shown in the bytes.

Canonical S1 envelope, 211 bytes, SHA-256
`f35b6a40b591af8dfc203f66df98b55bcf1bcf5b7ac5cdc0a9318b5959be88fc`:

```json
{"profile_ref":{"profile_id":"difficulty.silent-hunting-ground","profile_version":1},"reality_boundary":"deviant","relationship_overlay":"charged","schema_version":"run-protocol-envelope/v1","world_tone":"grim"}
```

Canonical resolution input, 710 bytes:

```json
{"authorized_overrides":[{"parameter":"resource_pressure","value":85},{"parameter":"social_trust","value":20}],"authorized_profile_id":"difficulty.silent-hunting-ground","authorized_profile_version":1,"canonical_envelope_hex":"7b2270726f66696c655f726566223a7b2270726f66696c655f6964223a22646966666963756c74792e73696c656e742d68756e74696e672d67726f756e64222c2270726f66696c655f76657273696f6e223a317d2c227265616c6974795f626f756e64617279223a2264657669616e74222c2272656c6174696f6e736869705f6f7665726c6179223a2263686172676564222c22736368656d615f76657273696f6e223a2272756e2d70726f746f636f6c2d656e76656c6f70652f7631222c22776f726c645f746f6e65223a226772696d227d","resolver_version":1,"schema":"run-protocol-resolution/v1"}
```

Preimage length: 772. Fingerprint:
`e1caa4cabad5bd0c4df75140482d42852351f062ee837911bfc2bbcf48ddd2aa`.
Resolved output: `85,20,95,90,90`.

### RPRES-V1-003 — presentation-only variation

Carrier: the same profile and empty overrides as RPRES-V1-001, with
presentation `heroic`/`chaotic`/`charged`.

Canonical S1 envelope, 208 bytes, SHA-256
`f4556a2b47ad4b976770c8a57d32601c149ad59356c85da26e18d617e42605eb`:

```json
{"profile_ref":{"profile_id":"difficulty.fragile-alliance","profile_version":1},"reality_boundary":"chaotic","relationship_overlay":"charged","schema_version":"run-protocol-envelope/v1","world_tone":"heroic"}
```

Canonical resolution input, 615 bytes:

```json
{"authorized_overrides":[],"authorized_profile_id":"difficulty.fragile-alliance","authorized_profile_version":1,"canonical_envelope_hex":"7b2270726f66696c655f726566223a7b2270726f66696c655f6964223a22646966666963756c74792e66726167696c652d616c6c69616e6365222c2270726f66696c655f76657273696f6e223a317d2c227265616c6974795f626f756e64617279223a226368616f746963222c2272656c6174696f6e736869705f6f7665726c6179223a2263686172676564222c22736368656d615f76657273696f6e223a2272756e2d70726f746f636f6c2d656e76656c6f70652f7631222c22776f726c645f746f6e65223a226865726f6963227d","resolver_version":1,"schema":"run-protocol-resolution/v1"}
```

Preimage length: 677. Fingerprint:
`c4019fecafeeb1e23d9eb13663baf21653f04ee9fe70b3fbb7e4f2714c3218ed`.
Resolved output: `60,45,65,60,60`, exactly equal to RPRES-V1-001. The
fingerprint differs because presentation identity is audit-bound.

### RPRES-V1-004 — same-profile override variation

Carrier: RPRES-V1-001 plus explicit `conflict_intensity=65`.

The canonical S1 envelope is byte-identical to RPRES-V1-001. Canonical
resolution input, 654 bytes:

```json
{"authorized_overrides":[{"parameter":"conflict_intensity","value":65}],"authorized_profile_id":"difficulty.fragile-alliance","authorized_profile_version":1,"canonical_envelope_hex":"7b2270726f66696c655f726566223a7b2270726f66696c655f6964223a22646966666963756c74792e66726167696c652d616c6c69616e6365222c2270726f66696c655f76657273696f6e223a317d2c227265616c6974795f626f756e64617279223a226c617766756c222c2272656c6174696f6e736869705f6f7665726c6179223a226f6666222c22736368656d615f76657273696f6e223a2272756e2d70726f746f636f6c2d656e76656c6f70652f7631222c22776f726c645f746f6e65223a2262616c616e636564227d","resolver_version":1,"schema":"run-protocol-resolution/v1"}
```

Preimage length: 716. Fingerprint:
`ae94567793fb992eeaccfe7cadf3c5f10df3c1366224d6b0b98fbfbc8c3243ff`.
Resolved output: `60,45,65,60,65`. The fingerprint is distinct from
RPRES-V1-001.

### Negative vectors

Every expected-failure vector returns no resolved output and no fingerprint.
N18 and N19 are the two explicitly labelled positive controls.

| ID | Exact mutation/input | Expected failure |
| --- | --- | --- |
| N01 | Dispatcher epoch `run-protocol-resolution`, version `2`, payload otherwise invalid | `UnsupportedRunProtocolResolverVersionError` before payload inspection |
| N02 | Version selector `True` | `RunProtocolResolutionIntegrityError` |
| N03 | Remove S1 `profile_ref` during direct envelope construction | Published `pydantic.ValidationError` |
| N04 | Profile `difficulty.fragile-alliance` version `2` | `RunProtocolProfileLookupError` |
| N05 | Profile `difficulty.unknown` version `1` | `RunProtocolProfileLookupError` |
| N06 | Proposal profile differs from envelope profile | `RunProtocolOverrideValidationError` |
| N07 | Two `resource_pressure=60` entries | `RunProtocolOverrideValidationError` duplicate |
| N08 | Parameter token `resource_pressure_extra` | direct `pydantic.ValidationError`; mutation of validated state to that token is `RunProtocolResolutionIntegrityError` |
| N09 | Override entry missing `value` | direct `pydantic.ValidationError`; removal from validated state is `RunProtocolResolutionIntegrityError` |
| N10 | `resource_pressure=True`, `IntEnum(1)`, `int` subclass, `60.0`, or `"60"` | direct `pydantic.ValidationError`; insertion by later mutation is `RunProtocolResolutionIntegrityError` |
| N11 | `resource_pressure=-5`, `42`, or `105` | direct below-domain, wrong-step, or above-domain `pydantic.ValidationError`; insertion by later mutation is `RunProtocolResolutionIntegrityError` |
| N12 | Extreme `resource_pressure=75` | selected-profile range `RunProtocolOverrideValidationError` |
| N13 | Easier `conflict_intensity=0` | selected-profile range `RunProtocolOverrideValidationError` |
| N14 | Add recommendation, scenario/content, server ID, seed, entropy, or categorical `Scarce`/`Fluid`/`Generous` resource-pressure input | closed-signature/carrier rejection; no categorical alias conversion |
| N15 | Reorder canonical JSON root members while decoding as a future stored value | no S2 decoder exists; S3 must reject non-canonical storage if it later adds one |
| N16 | Mutate a validated S2-owned override/input/output/fingerprint value or its fields-set/private/extra state before an S2 operation | `RunProtocolResolutionIntegrityError` |
| N17 | Replace looked-up profile with an equal caller-constructed definition | `RunProtocolResolutionIntegrityError`; only the catalogue object returned by lookup is authority |
| N18 | Construct RPRES-V1-002 proposals from two mappings with reverse insertion order | positive equivalence: identical canonical bytes, output, and fingerprint |
| N19 | Explicit Standard `resource_pressure=60` | valid; entry remains present and produces a fingerprint distinct from absence |
| N20 | Retain the authoritative catalogue tuple and Standard entry, then use `object.__setattr__` to mutate only the S2-owned `base_values.resource_pressure.value` from `60` to valid step value `65` before lookup | Exactly `RunProtocolResolutionIntegrityError`, never an S1 exception or fallback |
| N21 | Mutate the exact S1 envelope's embedded profile reference, presentation enum, or other nested S1-owned fields-set/private/extra state before S2 resolution | Published `RunProtocolValidationError`, unchanged; never `RunProtocolResolutionIntegrityError` |
| N22 | Retain the authoritative catalogue tuple, Standard entry, and its exact associated `profile_ref`; use `object.__setattr__` exactly as in published S1 hostile original-state testing to change only `profile_ref.profile_version.value` from exact integer `1` to `True`; call `lookup_run_protocol_profile` with a separate valid Standard reference | Exact top-level type `RunProtocolValidationError` from `validate_run_protocol_envelope_v1`, exact direct cause type `pydantic.ValidationError`, and no S2 cause layer; never `RunProtocolResolutionIntegrityError`, wrapping, translation, fallback, output, or fingerprint |

The table has exactly 22 stable IDs, N01–N22. N18 and N19 remain explicit
positive controls inside the vector table; every expected-failure vector is
separate from and contributes zero to the `104,165` valid-map count, the
`2,812,455` distinct-input count, the separate `2,812,455` primary public-call
count, the separate `2,812,455` repeat public-call count, and the `5,624,910`
aggregate public-invocation count. N16 covers S2-owned resolution state, N17
rejects a fresh equal profile definition, N20 covers only the exact S2-owned
catalogue default field above, N21 covers its existing S1 envelope corruption
subject, and N22 alone covers internal S1 corruption inside an authoritative
catalogue entry.

## 13. Exact future implementation contract

The future implementation creates one module,
`deviation_protocol.domain.run_protocol_resolution`. It uses private aliases for
imports so only the 33 names below are public module-level symbols. It imports
the published S1 domain module but no application or infrastructure module.
All carriers are strict, frozen Pydantic models with `extra="forbid"`,
`strict=True`, `frozen=True`, and `revalidate_instances="always"`; all fields
are required unless their exact literal type says otherwise. Public callables
are synchronous, deterministic, pure, and side-effect-free.

Direct invalid S2 carrier construction raises `pydantic.ValidationError`. A
listed callable validates owner-specific complete original/nested instance
state before semantic reads: published S1 exceptions remain unchanged for
S1-owned objects, while the row's S2 exception applies only to S2-owned state.
Catalogue authority always requires the exact object returned by
`lookup_run_protocol_profile`; a detached consumer reacquires that object from
trusted ID/version and may rebuild only value-authoritative carriers. No symbol
is re-exported from a package `__init__.py`.

| # | Public symbol | Kind and exact signature/value | Validation, return, exception | Consumer/seam |
| ---: | --- | --- | --- | --- |
| 1 | `RUN_PROTOCOL_RESOLUTION_EPOCH` | constant `str = "run-protocol-resolution"` | Trusted epoch; no exception | Dispatcher; S3 stored selector seam |
| 2 | `RUN_PROTOCOL_RESOLUTION_V1_VERSION` | constant `int = 1` | Exact non-Boolean supported version | Dispatcher; S3 seam |
| 3 | `RUN_PROTOCOL_RESOLUTION_V1_SCHEMA` | constant `str = "run-protocol-resolution/v1"` | Canonical input literal | Input carrier/encoder |
| 4 | `MAX_RUN_PROTOCOL_RESOLUTION_INPUT_BYTES` | constant `int = 1_024` | Inclusive canonical-input ceiling | Encoder/tests; S3 seam |
| 5 | `RUN_PROTOCOL_RESOLUTION_FINGERPRINT_DOMAIN` | constant `bytes = b"deviation-protocol:run-protocol-resolution-fingerprint:v1"` | Exact 57-byte domain | Fingerprint/tests |
| 6 | `RUN_PROTOCOL_OBJECTIVE_PARAMETER_ORDER` | constant `tuple[ObjectiveParameterName, ...]` in the five-field order | Exact canonical order; catalogue completeness checked | Encoder/resolver/tests |
| 7 | `RunProtocolResolutionError` | exception `class RunProtocolResolutionError(ValueError)` | Base for S2 classified failures | S2/S3 consumers |
| 8 | `UnsupportedRunProtocolResolverVersionError` | exception subclass of `RunProtocolResolutionError` | Well-typed unsupported trusted selector | Dispatcher/S3 seam |
| 9 | `RunProtocolProfileLookupError` | exception subclass of `RunProtocolResolutionError` | Unknown/retired/unsupported pair | Lookup/dispatcher |
| 10 | `RunProtocolOverrideValidationError` | exception subclass of `RunProtocolResolutionError` | Proposal, range, duplicate, compatibility failure | Override/S4 seam |
| 11 | `RunProtocolResolutionIntegrityError` | exception subclass of `RunProtocolResolutionError` | Malformed selector or corrupt/contradictory S2 state | All S2 boundaries/S3 seam |
| 12 | `ObjectiveParameterName` | `StrEnum` with `RESOURCE_PRESSURE="resource_pressure"`, `SOCIAL_TRUST="social_trust"`, `CONSEQUENCE_SEVERITY="consequence_severity"`, `INFORMATION_OPACITY="information_opacity"`, `CONFLICT_INTENSITY="conflict_intensity"` | Exact enum only at nested carriers | S2; S5 mechanics seam |
| 13 | `ObjectiveParameterValue` | immutable carrier `ObjectiveParameterValue(*, value: int) -> ObjectiveParameterValue` | Exact `int`, `0..100`, `value % 5 == 0`; direct invalid construction raises `pydantic.ValidationError` | Defaults/overrides/final output; S5 seam |
| 14 | `ObjectiveParameterValuesV1` | immutable carrier with five required `ObjectiveParameterValue` fields in product order | Exact nested types, no map or default | Profile/final output; S5 seam |
| 15 | `RunProtocolObjectiveOverrideV1` | immutable carrier `(*, parameter: ObjectiveParameterName, value: ObjectiveParameterValue)` | Exact nested types, no missing/extra field | Proposal/set |
| 16 | `RunProtocolOverrideRuleV1` | immutable carrier `(*, parameter: ObjectiveParameterName, minimum: ObjectiveParameterValue, maximum: ObjectiveParameterValue, step: int)` | `step` exact `5`; ordered bounds; catalogue-only | Profile catalogue/tests |
| 17 | `RunProtocolOverrideProposalV1` | immutable non-authoritative carrier `(*, profile_ref: RunProtocolProfileRefV1, entries: tuple[RunProtocolObjectiveOverrideV1, ...])` | Exact tuple, length `0..5`; caller order retained; duplicates may exist only until validation | Trusted pre-entry proposal; S4/S6 seam |
| 18 | `RunProtocolOverrideSetV1` | immutable validated carrier with same exact fields as proposal | Exact canonical order, unique entries, selected-profile bounds; only validator constructs authoritative use | Resolution input/output; S3/S4 seam |
| 19 | `RunProtocolProfileDefinitionV1` | immutable carrier `(*, profile_ref: RunProtocolProfileRefV1, label: str, base_values: ObjectiveParameterValuesV1, override_rules: tuple[RunProtocolOverrideRuleV1, ...], server_default_eligible: Literal[False])` | `profile_ref` association is S2 catalogue structure while internal state of the already-associated object is S1-owned; the four remaining fields are exact S2 state enumerated above | Catalogue/lookup; S4/S6 discovery seam |
| 20 | `RunProtocolResolutionInputV1` | immutable carrier `(*, schema: Literal["run-protocol-resolution/v1"], resolver_version: Literal[1], envelope: RunProtocolEnvelopeV1, authorized_profile: RunProtocolProfileDefinitionV1, authorized_overrides: RunProtocolOverrideSetV1)` | Complete trusted in-memory input; no optional fields | Encoder/resolver; S3/S4 seam |
| 21 | `RunProtocolResolutionFingerprint` | immutable carrier `(*, value: str)` | Exact 64 lowercase hexadecimal characters | Resolved output; S3/S4 seam |
| 22 | `ResolvedRunProtocolObjectivesV1` | immutable carrier `(*, resolution_input: RunProtocolResolutionInputV1, final_values: ObjectiveParameterValuesV1, fingerprint: RunProtocolResolutionFingerprint)` | Complete immutable result; cross-validates derived values and fingerprint | S3 persistence, S4 binding, S5 mechanics |
| 23 | `RUN_PROTOCOL_PROFILE_CATALOGUE_V1` | constant `tuple[RunProtocolProfileDefinitionV1, RunProtocolProfileDefinitionV1, RunProtocolProfileDefinitionV1]` | Exact three entries/order/tables above; no mutation/config loading | Lookup; S4/S6 seam |
| 24 | `validate_objective_parameter_values_v1` | `validate_objective_parameter_values_v1(value: ObjectiveParameterValuesV1) -> ObjectiveParameterValuesV1` | Returns exact instance; wrong top type `TypeError`, corrupt state `RunProtocolResolutionIntegrityError` | All S2 boundaries; S5 seam |
| 25 | `lookup_run_protocol_profile` | `lookup_run_protocol_profile(profile_ref: RunProtocolProfileRefV1) -> RunProtocolProfileDefinitionV1` | Executes the exact six-step lookup order above; invalid caller top type: `TypeError`; corrupted exact caller ref: published `RunProtocolValidationError` and cause behavior; corrupted still-associated nested catalogue `profile_ref`: published `RunProtocolValidationError` and cause behavior; unknown pair: `RunProtocolProfileLookupError`; only enumerated S2 catalogue corruption: `RunProtocolResolutionIntegrityError`; returns the exact authoritative entry; no wrapping or fallback | Dispatcher; S4/S6 seam |
| 26 | `validate_run_protocol_overrides` | `validate_run_protocol_overrides(profile: RunProtocolProfileDefinitionV1, proposal: RunProtocolOverrideProposalV1) -> RunProtocolOverrideSetV1` | Requires the exact object returned by a complete ordered lookup; validates the proposal's nested S1 ref through the same S1 adapter before S2 proposal state; binds refs, requires unique allowlisted exact values, and copies/sorts; preserves S1 exceptions and uses lookup, override, or S2 integrity exceptions only for their exact owners | Dispatcher; S4/S6 seam |
| 27 | `validate_run_protocol_profile_compatibility` | `validate_run_protocol_profile_compatibility(profile: RunProtocolProfileDefinitionV1, overrides: RunProtocolOverrideSetV1) -> RunProtocolOverrideSetV1` | Reacquires and identity-checks the profile through the complete ordered lookup, including nested catalogue-ref S1 validation, then validates all per-profile bounds; returns the exact set; preserves S1 outcomes and raises lookup, override, or S2 integrity exceptions only for their exact owners | Resolver; S4 seam |
| 28 | `construct_run_protocol_resolution_input_v1` | `construct_run_protocol_resolution_input_v1(envelope: RunProtocolEnvelopeV1, *, authorized_profile: RunProtocolProfileDefinitionV1, authorized_overrides: RunProtocolOverrideSetV1) -> RunProtocolResolutionInputV1` | Calls published S1 validator/encoder first; requires the exact catalogue object reacquired by lookup and all refs equal; returns a new value-authoritative carrier; preserves S1 exceptions and raises S2 classified errors only for S2-owned failures | Dispatcher/tests; S3/S4 seam |
| 29 | `validate_run_protocol_resolution_input_v1` | `validate_run_protocol_resolution_input_v1(value: RunProtocolResolutionInputV1) -> RunProtocolResolutionInputV1` | Validates only enough S2 outer shape to locate embedded objects, preserves the published envelope validation outcome, runs the complete ordered lookup for catalogue identity and nested catalogue-ref S1 state, then validates override, compatibility, literals, and remaining S2 state; wrong top type `TypeError`, S1 corruption its exact published outcome/cause behavior, S2 corruption `RunProtocolResolutionIntegrityError` | Encoder/fingerprint/resolve |
| 30 | `encode_run_protocol_resolution_input_v1` | `encode_run_protocol_resolution_input_v1(value: RunProtocolResolutionInputV1) -> bytes` | Runs owner-specific validation, builds exact six-field JSON, and enforces 1..1,024; wrong top type `TypeError`, S1 failure unchanged, S2 invalid state/bound `RunProtocolResolutionIntegrityError` | Golden/S3/S4 seam |
| 31 | `fingerprint_run_protocol_resolution_input_v1` | `fingerprint_run_protocol_resolution_input_v1(value: RunProtocolResolutionInputV1) -> RunProtocolResolutionFingerprint` | Uses exact domain/NUL/u32be/input preimage and SHA-256 after owner-specific validation; same owner-specific exceptions as encoder | Golden/resolver; S3/S4 seam |
| 32 | `resolve_run_protocol_objectives_v1` | `resolve_run_protocol_objectives_v1(value: RunProtocolResolutionInputV1) -> ResolvedRunProtocolObjectivesV1` | Validates by owner, applies only explicit overrides to copied base fields, fingerprints, and cross-validates output; `TypeError`, exact S1 outcome, or S2 integrity error according to ownership | Version branch; S3/S4/S5 seam |
| 33 | `resolve_run_protocol_objectives` | `resolve_run_protocol_objectives(envelope: RunProtocolEnvelopeV1, approved_overrides: RunProtocolOverrideProposalV1, *, expected_epoch: str, expected_version: int) -> ResolvedRunProtocolObjectivesV1` | Exact precedence steps 1–11; required selector/override arguments; resolver-version, exact S1, lookup, override, and S2 integrity exceptions remain non-overlapping and unchanged | Sole S2 facade; later S4 internal consumer |

Every catalogue-consuming path in rows 26–33 delegates to the row-25 lookup
order rather than defining a second catalogue validator. Consequently nested
catalogue `profile_ref` corruption always retains the row-25 S1 outcome, while
only the exact S2 catalogue state enumerated above can produce
`RunProtocolResolutionIntegrityError`. Encoder, fingerprint, v1 resolver, and
dispatcher paths add no wrapper, fallback, or reordered check.

There are exactly **33 public symbols**: 6 constants, 5 exceptions, 11 enums/
immutable carriers, 1 catalogue constant, and 10 callables. There are no
aliases, wrappers, registries, dynamic plugins, package exports, compatibility
shims, decoders, persistence carriers, repository ports, or re-exports.

## 14. Exact future implementation path budget

The later S2 implementation may change exactly five paths:

| Kind | Exact path | Purpose |
| --- | --- | --- |
| Production | `src/deviation_protocol/domain/run_protocol_resolution.py` | All 33 pure domain symbols; imports published S1 only |
| Unit tests | `tests/unit/test_run_protocol_resolution.py` | Complete contract, matrices, vectors, determinism, and negative evidence |
| Documentation | `PLANS.md` | Implemented S2 status, exact evidence, and remaining phase status |
| Documentation | `docs/architecture.md` | Actual implemented pure S2 boundary and dependency facts |
| Documentation | `docs/run_protocol.md` | Implemented/deferred product boundary and exact S2 evidence |

No existing `__init__.py`, S1 file, configuration, catalogue JSON, service,
application, infrastructure, persistence, ORM, migration, API, Demo, Web,
Provider, scenario, or test file may change. This plan remains frozen historical
authority during implementation and is not an implementation path. If a sixth
path or package export is needed, stop and obtain a reviewed plan amendment
before editing it.

## 15. Detailed future implementation sequence

1. Reconfirm the published plan baseline, exact five-path budget, clean index/
   worktree, and protected S1/frozen-plan identities.
2. Add the isolated domain module with private imports and the exact 33-symbol
   public-surface test first.
3. Implement strict carriers and owner-specific original-state revalidation,
   preserving every published S1 exception and applying the exact caller-S1,
   catalogue-outer-S2, association-S2, and nested-catalogue-S1 order, then
   catalogue completeness validation.
4. Implement lookup, proposal validation/canonicalization, and compatibility
   with all failure precedence fixed above.
5. Implement resolution-input construction and the exact six-field encoder.
6. Implement domain-separated fingerprinting and the version-specific pure
   resolver, then the required trusted dispatcher.
7. Add the exact direct test specified above: independent literal profile,
   default, permitted-value, and 27-presentation tuples; absent-sentinel
   Cartesian generation; all `104,165` maps and `2,812,455` distinct trusted
   inputs in the frozen order; one primary public-resolver call followed
   immediately by one real repeat public-resolver call for each input; exact
   output/canonical-byte/fingerprint equality; separately asserted Extreme,
   Standard, Easier, and aggregate primary counts of `333,396`, `1,594,323`,
   `884,736`, and `2,812,455`; the same separately asserted repeat counts;
   combined profile counts of `666,792`, `3,188,646`, and `1,769,472`; and
   `5,624,910` aggregate public resolver invocations. Also add exact-type and
   owner-specific corruption negatives through N22; authoritative-catalogue
   detached reconstruction; and independent golden constants. No alternative
   argument, sampling, partial enumeration, skipped combination, or suppressed
   repeat public invocation is permitted.
8. Add subprocess determinism evidence and static no-I/O/dependency/public-
   symbol checks.
9. Synchronize exactly the three implementation documentation paths without
   editing this plan.
10. Run the exact verification below, inspect every changed/untracked path and
    complete diff, and stop without staging or committing.

## 16. Required future test and verification matrix

All commands run from the repository root in PowerShell 7 using the existing
`.venv`. Passing means exit code zero and no unexpected skip in the focused S2
file.

| Evidence | Exact command or focused test requirement | Required result |
| --- | --- | --- |
| Focused S2 | `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_run_protocol_resolution.py` | All S2 contract/matrix/vector tests pass |
| Existing S1 regression | `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_run_protocol.py tests/unit/test_run_protocol_persistence.py` | Published S1 behavior unchanged |
| Adjacent Run regression | `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_run.py tests/unit/test_run_operations.py tests/unit/test_run_persistence.py tests/unit/test_run_repositories.py tests/unit/test_run_service.py tests/unit/test_run_entry_service.py tests/unit/test_run_entry_api.py tests/unit/test_run_composition.py` | No import/contract regression |
| Exact public surface | Focused test enumerates module names | Exactly 33 public symbols, signatures, inheritance, constants, and no re-export |
| Catalogue completeness/defaults | Focused exhaustive test | Exactly three ID/version pairs, labels, five defaults, five ordered rules each, no alias/default/retired entry |
| Override allowlist/boundaries | Focused parameterized negative matrix | Adjacent out-of-range, every wrong-step, wrong-type, duplicate, missing, and unknown-key case is rejected separately from valid-domain execution |
| Independent exhaustive oracle | Literal expected profile IDs/versions, defaults, permitted-value tuples, and 27 presentation triples are declared directly in `tests/unit/test_run_protocol_resolution.py`; production catalogue and enum iteration do not generate them | Production values are checked against an independent oracle that cannot validate itself |
| Complete override domain | Use the one absent sentinel and fixed-order Cartesian generation to execute all `12,348` Extreme, `59,049` Standard, and `32,768` Easier maps through `resolve_run_protocol_objectives` | Exactly `104,165` maps accepted; outputs are defaults replaced only by explicitly present authorized values; absent keys stay absent; equal-to-default presence retained; canonical order exact; no hidden compatibility rejection |
| Duplicate/missing/unknown/conflict | Separate focused negative matrix N06–N14 plus N16, N17, and N20–N22; no expected failure increments the distinct-input count or a primary, repeat, per-profile combined, or aggregate combined public-invocation counter | Fail-closed non-overlapping exception taxonomy, categorical-alias rejection, catalogue identity, and no partial result |
| Precedence/version dispatch | Focused tests | Unsupported resolver dispatch precedes payload; envelope and caller/proposal S1 validation plus the exact catalogue outer-S2/association-S2/nested-S1 order precede their specified semantic reads; encode/fingerprint/resolve reuse that order; S2 never wraps S1 corruption |
| Presentation independence and invocation accounting | In fixed Extreme/Standard/Easier, Cartesian-map, and presentation order, directly call `resolve_run_protocol_objectives` for every one of `104,165` maps × the exact literal 27 presentations; validate each primary result, then immediately make one real repeat call with the same trusted input objects or the expressly permitted equivalent detached input; compare exact output, canonical resolution-input bytes, and fingerprint; increment each separate counter only after its corresponding public call returns | Distinct trusted inputs are `333,396`, `1,594,323`, `884,736`, aggregate `2,812,455`; separately asserted primary public-call counts are the same four values; separately asserted repeat public-call counts are the same four values; combined public-invocation counts are `666,792`, `3,188,646`, `1,769,472`, aggregate `5,624,910`; presentation never enters objective fields; no reuse, memoization, self-comparison, helper call, source inspection, cached suppression, or later repeat pass substitutes for the public repeat invocation; fingerprints may differ across presentations |
| Canonical bytes/fingerprints | RPRES-V1-001 through 004 plus genuine 863-byte maximum | Exact bytes, lengths, preimage lengths, lowercase digests, outputs, and defensive ceiling classification |
| Mapping order | Build equivalent proposals from forward/reverse insertion-ordered dictionaries and tuple orders | Identical canonical set, bytes, output, fingerprint |
| Python hash seed/process | Focused test launches `sys.executable` subprocess workers with `PYTHONHASHSEED=0`, `1`, `42`, and `random` | Each worker emits the four exact published digests and values |
| Locale/time-zone | Focused subprocess test always runs `C`; additionally runs every available locale among `English_United Kingdom.1252`, `German_Germany.1252`, and `Turkish_Turkey.1254`, with distinct `TZ` values | Available environments emit identical bytes/digests; unavailable named locales are reported as unsupported, not silently substituted |
| Repetition/detached equivalence | Focused test resolves each golden 100 times; then starts from trusted profile ID/version, reacquires the exact catalogue object through `lookup_run_protocol_profile`, and freshly rebuilds only value-authoritative S1/proposal/input carriers | Every repetition and permitted detached reconstruction emits identical values, bytes, and fingerprint; catalogue authority is never copied/reconstructed; N17 still rejects an equal fresh profile definition |
| Operating-system portability | Focused goldens plus static primitive check; the same tests are required on every supported host that reviews or publishes the implementation | Exact UTF-8/JSON/u32be/SHA-256 constants remain byte-identical; no platform-default encoding, path, newline, or environment input exists |
| Exact types | Focused Boolean, `IntEnum`, `StrEnum`, scalar subclass, float/string, mapping/sequence subclass tests | No normalization or coercion |
| S1 mutation/corruption ownership | Focused exact envelope, embedded profile-ref, presentation-enum, canonical, dispatcher, and published stored-boundary tests including N21; plus exact N22 corruption inside the authoritative catalogue entry's still-associated S1 `profile_ref` | Exact published `TypeError`, `pydantic.ValidationError`, `ValueError`, `RunProtocolValidationError`, direct S1 cause behavior, `UnsupportedRunProtocolVersionError`, and `RunProtocolStoredRecordIntegrityError` distinctions remain; S2 never wraps or translates them |
| S2 mutation/corruption ownership | Focused S2-owned `__dict__`, fields-set, private, extra, tuple, input, output, canonical-input, and fingerprint mutation tests including N16; exact N20 mutates only Standard `base_values.resource_pressure.value` | `RunProtocolResolutionIntegrityError` occurs only for S2-owned corruption before semantic read/output; N20 never mutates nested S1 state |
| Categorical resource-pressure deferral | Closed-signature/carrier negatives plus static public-surface scan | `Scarce`, `Fluid`, and `Generous` are never accepted/emitted as S2 inputs, aliases, profiles, overrides, S1 fields, or objective values; no thresholds/bands or projection exist |
| Catalogue authority | Positive detached flow plus N17, N20, and N22 | Trusted ID/version is looked up through the exact deterministic order each time; only exact catalogue-owned profile identity authorizes resolution; fresh value-authoritative carriers remain usable; S2 outer corruption and nested S1 corruption have disjoint outcomes |
| No randomness/I/O/dependency drift | AST/import and call-surface focused test | No application/infrastructure, filesystem, environment, locale, clock, random, UUID, network, database, Provider, logging, or Python `hash()` dependency |
| Compilation | `.\.venv\Scripts\python.exe -m compileall -q src tests alembic` | Compilation passes |
| Tracked whitespace | `git diff --check` | No diagnostics |
| New-file whitespace | `git diff --no-index --check -- NUL src/deviation_protocol/domain/run_protocol_resolution.py` and the same command for `tests/unit/test_run_protocol_resolution.py` | Exit `1` only for expected new-file differences; no whitespace diagnostics |
| Canonical Offline | `.\scripts\verify.ps1 -Mode Offline` | Sanitized child passes full pytest, compileall, dependency check, metadata-only Alembic checks, and diff check |

### Future S2 acceptance criteria

S2 implementation cannot be accepted unless the exact test above directly
executes all `104,165` valid profile/override maps and all `2,812,455` distinct
presentation inputs through the public resolver in the frozen profile,
Cartesian-map, and presentation order. For each input, it must validate one
primary public call, make one immediate real repeat call to the same public
callable with the exact same trusted input objects, or the exactly equivalent
permitted detached input only where the relevant test expressly specifies it,
and compare exact output, canonical resolution-input bytes, and fingerprint. It
must separately assert primary and repeat per-profile counts of `333,396`,
`1,594,323`, and `884,736`, aggregate primary and aggregate repeat counts of
`2,812,455` each, combined per-profile invocation counts of `666,792`,
`3,188,646`, and `1,769,472`, and `5,624,910` aggregate public resolver
invocations. Each corresponding counter increments only after that public call
returns successfully. It must also retain
explicit equal-to-default override presence and presentation-dependent
fingerprint permission; keep invalid-boundary, wrong-step, wrong-type,
duplicate, and unknown-key negatives separate; preserve the field-level S1/S2
catalogue split and N20/N22 outcomes; reject every categorical resource-pressure
alias or projection; and demonstrate detached equivalence only after
authoritative catalogue re-lookup while N17 continues to reject a fresh equal
profile definition. No static argument, property argument, representative or
sampled set, partial enumeration, source inspection, result reuse, memoized test
data, self-comparison, internal helper, cached suppression, or deferred repeat
pass can replace any required public resolver invocation.

Offline's `alembic heads` and `alembic history` stages are metadata-only graph
inspection. They do not connect to or mutate a database. S2 adds no migration,
so the existing single head and linear history must be unchanged. MySQL, Full,
Provider, Live, browser, application runtime, migration execution, and network
commands are neither required nor authorized.

## 17. Documentation synchronization for implementation

The later implementation must update exactly its three budgeted documentation
paths to record the 33-symbol boundary, five-path inventory, actual verification
evidence including the exhaustive finite domain and owner-specific exceptions,
implemented S2 status, numeric-only resource-pressure authority, authoritative
catalogue re-lookup for detached reconstruction, no durable/public/categorical
activation, and the still-unauthorized S3–S7 boundary. It must distinguish
implemented behavior from approved design and deferred work. This candidate
plan remains unchanged as historical frozen authority.

Before independent implementation review or a completion claim, apply the
canonical documentation-synchronization checklist, verify no sixth path,
assess guardrails, and ensure no stale text claims S1 or S2 is awaiting a gate
already completed at that future baseline.

## 18. Rollback and stop conditions

S2 defines no product/runtime rollback. For a future uncommitted implementation
candidate only, rollback means removing its one new production module, one new
test module, and reverting its exact S2 status edits before staging; it never
touches durable state. Do not use destructive Git commands for that candidate
cleanup.

Stop before or during implementation if:

- the published plan baseline or any approval-bound identity is stale;
- any parameter type, endpoint meaning, step, profile value, override bound,
  precedence, failure, canonical byte, fingerprint, or symbol remains implicit;
- a fourth authoring path or sixth implementation path becomes necessary;
- an appropriate trusted identity would be required for stochastic selection;
- a scenario/content identity becomes mechanically relevant without separately
  published authority;
- a client/model/Provider can introduce a non-allowlisted value;
- presentation changes an objective value;
- the S2 implementation accepts, emits, or projects `Scarce`, `Fluid`, or
  `Generous`, invents a categorical threshold/band, or otherwise treats a
  categorical label as an S2 alias or value;
- any sampling, representative-only set, partial enumeration, source
  inspection, deduplication, skipped call, result reuse, memoization,
  self-comparison, internal-helper substitution, cached suppression, or
  deferred repeat pass replaces the complete direct contract: `104,165` maps;
  `2,812,455` distinct trusted inputs; per-profile primary public-call counts
  `333,396`, `1,594,323`, and `884,736`, aggregate `2,812,455`; identical
  separately asserted repeat public-call counts made immediately after their
  primary calls; combined per-profile invocation counts `666,792`, `3,188,646`,
  and `1,769,472`; and `5,624,910` aggregate public resolver invocations;
- an S1-owned corruption is caught, wrapped, translated, or replaced by
  `RunProtocolResolutionIntegrityError` or any other S2 exception;
- catalogue validation treats `profile_ref` association and the associated S1
  object's internal state as one owner, changes the exact lookup order, or lets
  N20 and N22 converge on the same exception;
- detached reconstruction copies, reconstructs, deserializes, or substitutes
  an equal profile definition instead of reacquiring the exact catalogue-owned
  object through lookup;
- a default, fallback, upgrade, downgrade, clamp, round, repair, or coercion
  path appears;
- the current S1 contract or protected identity must change;
- persistence, migration, runtime, public, Provider, world, or later-slice work
  becomes necessary; or
- any required deterministic/golden evidence cannot be reproduced.

## 19. Deferred S3–S7 decisions and owners

| Deferred decision | Exact owner |
| --- | --- |
| Durable resolution/envelope/profile/fingerprint representation, reconstruction, migration, legacy/native proof | P3.3-S3 dedicated plan |
| Native Run binding, admission evidence, explicit authored entry-world ID/version, atomic freeze | P3.3-S4 dedicated plan |
| Mechanical meaning/application of each scale point, exact numeric-to-`Scarce`/`Fluid`/`Generous` mechanics or prompt projection, and trusted prompt-context compilation without changing the numeric S2 value | P3.3-S5 dedicated plan |
| Any public/client representation of `Scarce`/`Fluid`/`Generous`, public discovery, profile selection/override transport, API/OpenAPI, Demo/Web/projection/recovery parity, without changing the numeric S2 value | P3.3-S6 dedicated plan |
| Later-world selection, any actual random/weighted seed algorithm, visits, regions, revisits, continuity, progression, canon, identity predicate integration | P3.3-S7 subdivisions |
| Relationship/residence state and progression | Phase 3.4, not Phase 3.3 |
| Subject-reference compatibility and broader programme closeout | Phase 6 and Phase 7 respectively |

S2 intentionally decides no S3–S7 physical path, identity, schema, migration,
transaction, public shape, prompt format, mechanics effect, categorical
resource-pressure threshold/band/projection, authored-world catalogue,
selection weight, or continuity rule.

## 20. Plan independent-review, commit, publication, and freeze gate

There is exactly one operative success verdict for a fresh independent
read-only review of this exact plan candidate:

`PHASE_3_3_S2_DETERMINISTIC_PROFILE_RESOLUTION_PLAN_INDEPENDENT_REVIEW_APPROVED`

The verdict is valid only when the review binds:

1. baseline commit `4d146679e782ff555819b411fc5048e55299de4d`, branch/ref
   topology, clean starting state, and exact parent/subject;
2. exactly `PLANS.md`, this file, and `docs/run_protocol.md`, with no fourth
   candidate path;
3. final line, byte, and SHA-256 identity for all three candidate files;
4. every isolated binary-safe per-path patch byte sequence, byte count, and
   SHA-256, plus the complete lexicographically ordered binary-safe three-path
   patch bytes, byte count, SHA-256, and aggregate insertion/deletion counts;
5. every exact parameter, profile, default, override, authority, precedence,
   compatibility, resolver, canonical-input, fingerprint, and golden-vector
   decision in this file;
6. the exact 33-symbol future contract, five-path implementation budget,
   direct `104,165`-map/`2,812,455`-distinct-input contract with `2,812,455`
   primary and `2,812,455` immediate real repeat public calls, exact per-profile
   primary/repeat counts `333,396`, `1,594,323`, and `884,736`, combined counts
   `666,792`, `3,188,646`, and `1,769,472`, and `5,624,910` aggregate public
   resolver invocations, independent oracle, field-level exception ownership,
   deterministic catalogue order, N20/N22 split, detached-reconstruction
   requirements, stop conditions, and deferred owners;
7. all protected/frozen identities and S1 lifecycle facts; and
8. the absence of editing, Git, implementation, public/durable, S3–S7, or other
   authority.

Final identities are measured after the last candidate byte change and supplied
externally with the review prompt; writing them into this file would change an
approval-bound identity. Any byte, relevant baseline, inventory, decision, or
measurement change invalidates the verdict and requires fresh review.

The verdict grants no editing, staging, commit, push, publication,
implementation, or P3.3-S3 through P3.3-S7 authority. After approval, a
separate explicit authorization is required for the exact three-path local
documentation commit. The user performs every push, and clean aligned
publication confirmation is mandatory before separately authorized S2
implementation.

## 21. Dormant future implementation-review gate

The sole future S2 implementation-review verdict is:

`PHASE_3_3_S2_DETERMINISTIC_PROFILE_RESOLUTION_IMPLEMENTATION_INDEPENDENT_REVIEW_APPROVED`

It is dormant and non-operative until all of these preconditions hold:

1. this exact plan candidate receives its own operative approval;
2. a separately authorized exact plan commit is created;
3. the user manually pushes that exact commit;
4. a clean aligned published-baseline confirmation verifies it; and
5. a separately authorized exact implementation candidate is produced and
   freshly independently reviewed.

Only then may the verdict bind the exact implementation baseline; exact
five-path inventory; every file identity; complete binary-safe patch; exact
33-symbol contract; catalogue/domain/default/override decisions; canonical and
fingerprint vectors; documentation synchronization; and complete verification
evidence. Any change invalidates it. It grants no editing, staging, commit,
push, publication, S3, or later-slice authority. Historical plan approval,
authoring labels, subset reviews, and differently scoped tokens cannot satisfy
the future implementation gate.

## 22. Guardrail assessment

Applicable existing rules are `ENV-001`, `ENV-002`, `GIT-001`, `AUTH-001`,
`STATE-001`, `API-001`, `SCENE-001`, `MODEL-001`, `MODEL-002`, and
`CONTENT-001`. This plan applies existing authority, determinism, isolation,
and workflow rules. The confirmed review findings corrected across this
candidate, including the remaining invocation-count finding corrected here,
are candidate-specific specification defects; none establishes or changes a
reusable engineering or safety rule, so no guardrail document change is
required.

Guardrail impact: None

# Dynamic Narrative Provider Reliability Remediation Plan

## 1. Amendment status and authority

Base key-ownership status: `PLAN_AMENDMENT_PUBLISHED`.

D1 evidence correction status:
`AUTHORITY_CORRECTION_BOUNDED_CORRECTION_CANDIDATE_AWAITING_INDEPENDENT_REREVIEW`.

This document is the independently approved and published `DN-DKO-006`-
corrected deterministic generated-public-fact-key ownership amendment to the
published Prompt-only remediation plan.
The first candidate was authored after `PRE_REVIEW_LIVE_CANDIDATE_GATE_FAILED`
and `DYNAMIC_NARRATIVE_PROVIDER_FAILURE_DIAGNOSIS_COMPLETE`. Its first fresh
independent review returned
`DYNAMIC_NARRATIVE_DETERMINISTIC_KEY_OWNERSHIP_PLAN_AMENDMENT_INDEPENDENT_REVIEW_CHANGES_REQUIRED`
with findings `DN-DKO-001`, `DN-DKO-002`, and `DN-DKO-003`; the first bounded
two-document correction closed all three. A later fresh independent review
confirmed that `DN-DKO-001`, `DN-DKO-002`, and `DN-DKO-003` remain closed and
returned the same `CHANGES_REQUIRED` verdict only for `DN-DKO-004` and
`DN-DKO-005`. The subsequent focused independent review closed `DN-DKO-004`
and found `DN-DKO-005` not fully closed solely because of the remaining
maximum-current-version and deterministic-regression gap identified as
`DN-DKO-006`. This bounded two-document correction addressed only `DN-DKO-006`.
A fresh delta-focused independent review of the exact corrected two-document
amendment completed successfully and returned:

`DYNAMIC_NARRATIVE_DETERMINISTIC_KEY_OWNERSHIP_PLAN_AMENDMENT_INDEPENDENT_REVIEW_APPROVED`

That review fully closed `DN-DKO-006`; `DN-DKO-005` is therefore fully closed.
All amendment findings `DN-DKO-001` through `DN-DKO-006` are closed, and no
material finding remains within the approved review scope. The fresh review,
not the earlier authoring correction, supplied the sole operative approval. The
corrected key-ownership amendment is independently approved and published and
remains the base allocation authority. The current four-document D1 evidence
correction is a separate unapproved candidate. Its first independent review
returned
`DYNAMIC_NARRATIVE_D1_EVIDENCE_AUTHORITY_CORRECTION_INDEPENDENT_REVIEW_CHANGES_REQUIRED`
for exactly two blocking findings: the non-executable lifecycle over the
protected dirty candidate and the committed-scalar derivation timing. This
bounded correction addresses only those findings, is complete only as an
unstaged documentation candidate, and has not yet been independently
re-reviewed. No implementation completion, deterministic verification
completion, future Live diagnostic, candidate freeze, formal Gate,
implementation review, staging, commit, push, publication, production
readiness, or phase completion is claimed for that correction.

The token above applies only to the exact approved technical amendment.
Historical plan-review, implementation-review, Live-Gate, failure,
`CHANGES_REQUIRED`, `BLOCKED_BASELINE_MISMATCH`, and `INCOMPLETE` verdicts are
non-operative for this approval. This bounded publication records the approved
key-ownership lifecycle result without approving the current evidence
correction. The sole operative success verdict for the current exact
four-document candidate is
`DYNAMIC_NARRATIVE_D1_EVIDENCE_AUTHORITY_CORRECTION_INDEPENDENT_REREVIEW_APPROVED`.
The authoring results
`DYNAMIC_NARRATIVE_D1_EVIDENCE_AUTHORITY_CORRECTION_CANDIDATE_COMPLETE` and
`DYNAMIC_NARRATIVE_D1_EVIDENCE_AUTHORITY_CORRECTION_BOUNDED_CORRECTION_CANDIDATE_COMPLETE`,
and all historical, superseded, example, prohibited, failure,
`CHANGES_REQUIRED`, `BLOCKED`, and `INCOMPLETE` verdicts are non-operative for
its approval. Any byte change requires new hashes and a fresh independent
review. This correction does not authorize implementation, validation, Live
activity, or Git handoff.

This `DN-DKO-006` correction was authored against the following read-only local
identity, without fetch or pull:

| Check | Required and observed value |
| --- | --- |
| Repository root | `D:/deviation-protocol` |
| Branch | `main` |
| `HEAD` and local `origin/main` | `8af790cc280f78102fa2e736806362527043424e` |
| Subject | `docs(dynamic-narrative): publish provider reliability remediation plan` |
| Ahead/behind | `0/0` |
| Index, untracked paths, conflicts, active Git operations | empty/none/none/none |

The initial unstaged inventory for this `DN-DKO-006` correction was exactly:

1. `PLANS.md`, SHA-256
   `bbdee6f3267748908fe30ca78da9a429fededa6a507e6efd9fbd2b7083ac8ef7`;
2. `docs/dynamic_narrative_provider_reliability_remediation_plan.md`, SHA-256
   `7bbfffa00d669f3191d1c12cb3ec7be370dddf8f706d5838b523d9be52c5467e`;
3. `src/deviation_protocol/application/dynamic_narrative_models.py`, SHA-256
   `97a5306e9e40ee28873c45a3069b7b8e11621e1585af8624f9430daea30f766e`;
4. `tests/unit/test_dynamic_narrative.py`, SHA-256
   `db6c001b1d5766d29ef8a5c92bf4492026db31230a283607e0ba9f7b494ccd59`;
5. `tests/unit/test_narrative_provider.py`, SHA-256
   `ad5922d77c397993bc8c97de511cb06d62089f85d80fbbb078d20748599c2329`.

The runtime/test diff was exactly 29,177 bytes with SHA-256
`5d42807e250a6ac69793f12ac76f202b707a4e3932c52f0c2de5ed7f02495c68`;
the documentation-only diff was exactly 116,538 bytes with SHA-256
`610e5c6b3602362dd166a6a8b98c74fc3046e7031674955d0ed785239336e935`;
and the complete five-path diff was exactly 145,715 bytes with SHA-256
`85d2360b805b3e6b7cfedc3c86f4448415bd6aaeac1d3982fad4c99e35bf8890`.

The published Prompt-only operative instruction bundle was 42,865 UTF-8/LF
bytes with SHA-256
`50f251e70cdf0ddf0087e5aedcec7b8311b7669b9f1ff5a59a6658a74ca74291`.
That bundle and its prior Gate are superseded for future implementation and
acceptance by this amendment. They remain historical evidence and are not
retroactively reinterpreted as having passed.

Applicable authority, in descending specificity for this correction, is:

1. `AGENTS.md`;
2. `docs/engineering/guardrails.md`, especially `AUTH-001`, `MODEL-001`,
   `MODEL-002`, `STATE-001`, `API-001`, and `ENV-002`;
3. `docs/engineering/codex_workflow.md`;
4. this document's current D1 evidence correction, if and only if independently
   approved and its exact aggregate manifest is locked under the workflow's
   narrow dirty aggregate-candidate exception, layered over the published
   key-ownership amendment;
5. the matching amendment in `docs/public_client_contract.md`;
6. `docs/dynamic_narrative_vertical_spike_plan.md`;
7. `docs/narrative_provider.md` and `docs/architecture.md`;
8. the inspected application contracts, finalization implementation, and direct
   regressions.

A relevant baseline change before review, implementation, deterministic
validation, either real-Provider stage, implementation review, staging, or
commit invokes the pending-plan baseline invalidation and approval-token
consistency rules. This correction authorizes none of those later steps.

## 2. Established failure evidence

### 2.1 Formal Gate Case 1 is a separate unresolved failure family

The formal pre-review Gate stopped during fresh Case 1 after exactly one
suggested ordinal `0` submission. The public result was HTTP `409` with
`NARRATIVE_OUTCOME_UNKNOWN`; state version remained `0`; no new story segment
appeared; and the official DeepSeek request-count delta was `0`.

The completed read-only diagnosis established all of the following:

- absent `DEEPSEEK_API_KEY` prevents Live startup and therefore does not directly
  explain an Action-time HTTP `409`;
- the exact underlying cause of this Gate failure remains unresolved;
- the strongest inference is a Codex-owned launcher encountering sandbox or
  network availability failure before DeepSeek recorded a request; and
- a Codex sandbox or network failure does not prove that the configured Provider
  or key is invalid.

This environment/transport/publication family remains separate from the schema
defect below. The deterministic-key correction does not claim to resolve that
earlier HTTP `409`, and the earlier result does not prove a generated-key defect.

### 2.2 Real-Provider generated-key reliability defect is proven

Later user-operated Live play was launched from a PowerShell process that had
Provider configuration before launcher startup. It produced both successful
HTTP `200` narrative commits and HTTP `503` failures carrying these sanitized
diagnostics:

- `DNVS_LIVE_DIAG_RECOVERY_SCHEMA_GENERATED_PUBLIC_FACT_KEY_CONTRACT`;
- `DNVS_LIVE_DIAG_PRE_RESPONSE_SCHEMA_INVALID`; and
- `DNVS_LIVE_DIAG_FINAL_SCHEMA_GENERATED_PUBLIC_FACT_KEY_CONTRACT`.

The completed diagnosis established that initial and replacement generations
can both violate the generated public-fact key contract; normal `json_object`
mode enforces JSON syntax rather than the key regex; the current
`COMBINED_DEFAULT` Prompt-only candidate is probabilistically improved but not
reliable; and its prior candidate-selection evidence was only `6/8`
strict-valid. Prompt-only compliance cannot guarantee four consecutive Gate
passes.

The defect is an ownership error: authority-sensitive public-fact identifier
syntax was assigned to the LLM. A third generation, additional retry, relaxed
validation, post-failure salvage, key repair/normalization, or weakening the
protected/internal detector would preserve or expand the wrong authority
boundary and is prohibited.

### 2.3 Historical D1 evidence disposition

The original D1-D5 implementation diagnostic is closed as failed/incomplete.
Only historical D1 ran:

| Datum | Historical result |
| --- | --- |
| Original procedure case / Run alias | D1 / Run A |
| Action | Suggested ordinal `0` |
| Authoritative revision | `0 -> 1` |
| HTTP / lifecycle result | `200` / normally committed |
| New story segments / suggestions | `1` / `3` |
| Official DeepSeek Dashboard delta / Provider generations | `1` / `1` |
| Authorized application replacement / transport retries / third generation | none / `0` / none |
| Exact newly committed public-fact count | `UNKNOWN` |

Historical D1 is incomplete, not passed, not reconstructable, not
retroactively reinterpretable, and not repeatable within the original
procedure. Its fact count must not be inferred from long-term-memory category
totals, narrative prose, Provider proposal count, Dashboard request count,
fact-ring size, generated keys, logs, or later runtime evidence. D2-D5 were
never started. The original procedure may never resume at D2, replace or retry
D1, merge later evidence into D1, or be rewritten as successful.

The accepted read-only failure analysis returned
`DYNAMIC_NARRATIVE_D1_NEW_PUBLIC_FACTS_EVIDENCE_REMEDIATION_PLAN_COMPLETE`. It
confirmed that the Action API preserves a committed response's
`feedback_parameters`, but the React action loop discards that response before
rendering the refreshed View, and the View cannot safely reconstruct the exact
per-Action fact count. The selected correction is the bounded committed scalar
and associated browser evidence surface defined below; its implementation is
blocked until this exact authority correction receives its operative
independent-review approval.

## 3. Normative amendment decision and frozen boundaries

Generated public-fact keys are server-owned and deterministically allocated at
the application finalization boundary. The LLM may author bounded semantic
public-fact statements, but it must not invent, propose, select, repair,
normalize, transform, or receive an authority-bearing public-fact key.

This is a revised Provider/application contract boundary, not repair or salvage
of an invalid Provider response. The application first accepts or rejects the
complete keyless candidate under the strict Provider contract. Only a complete,
otherwise-valid candidate can reach server allocation. The application then
constructs new server data from locked current authority; it does not reinterpret
or edit a rejected Provider field.

The following boundaries remain frozen:

- strict local validation is authoritative;
- every Provider field remains untrusted and candidate-only;
- the global protected/internal identifier and secret-shape detectors remain
  complete and are not weakened or given a public-fact exemption;
- Provider output is not normalized into validity, repaired, salvaged,
  truncated, or partially accepted;
- dynamic Live composition has exactly zero Provider transport retries;
- one Action has one initial application generation and at most one complete
  application replacement, for at most two Provider generations total;
- there is no third generation and no deterministic narrative fallback;
- uncertain delivery or publication is never automatically resent;
- duplicate submission does not create another job, call, allocation, or
  commit;
- finalization is atomic and terminal failure leaves public state unchanged;
- no raw Provider request/response, prompt, secret, protected identifier, or
  internal state enters public evidence;
- current public error sanitization remains unchanged;
- the Action DTO gains no top-level field and non-Dynamic-Narrative outcomes
  remain unchanged; and
- the authoritative View contract remains unchanged.

A server-created key is not permission to accept an otherwise-invalid
candidate. Every other schema, length, semantic, safety, protected-reference,
authority, provenance, stale-state, transaction, and cancellation failure keeps
the existing replacement eligibility or terminal behavior.

## 4. Revised Provider candidate contract

### 4.1 Version and exact shape

The later implementation changes both application-owned wire versions:

- `DYNAMIC_PROMPT_SCHEMA_VERSION` becomes `dynamic-narrative-prompt-v2`;
- `DYNAMIC_CANDIDATE_SCHEMA_VERSION` becomes
  `dynamic-narrative-candidate-v2`.

The Prompt version bump binds prepared work to the new candidate contract. The
candidate version bump prevents a v1 response from being accepted under v2
semantics. A previously committed response remains replayable from its stored
`TurnResponse`; a non-committed v1 prepared or validated job becomes stale
without another Provider call or story commit.

The Provider-visible public-fact item is exactly:

```text
DynamicPublicFactProposal
  value: normalized public statement, 1..300 Unicode characters
```

`proposed_public_facts` remains an ordered tuple containing exactly zero, one,
two, or three such objects. Each object has the one required field `value` and
`additional_properties=false`. A `key`, `id`, `identifier`, `name`, legacy v1
field, or any other member is an extra forbidden field. It is classified by the
existing `REQUIRED_OR_EXTRA_FIELDS` schema family and is eligible only for the
same single complete replacement allowance as another first schema-invalid
candidate.

Normalized fact values must be pairwise distinct under the existing NFC,
collapsed-whitespace, trim, and Unicode-casefold comparison. A duplicate value
is `BOUNDS_OR_UNIQUENESS`; it is not assigned two identities by order.

The model continues to author only these semantic candidate fields:

1. `narrative_text`;
2. `result`;
3. zero to three `proposed_consequences` strings;
4. zero to three ordered `proposed_public_facts[*].value` statements;
5. `next_scene.title` and `next_scene.summary`;
6. exactly three `suggested_actions`; and
7. `continuation`.

The model owns no public-fact key or identifier field. The rendered schema,
Prompt instructions, and typed example must contain no instruction, grammar,
safe example, or recovery text asking the model to create one.

### 4.2 Schema-family disposition

`GENERATED_PUBLIC_FACT_KEY_CONTRACT` ceases to be a Provider-response schema
family because the v2 Provider candidate contains no key. Remove it from
`DynamicNarrativeSchemaFailureFamily`, schema precedence, generation
instructions, recovery/final diagnostic mappings, and Prompt recovery text.
The exact historical diagnostic strings remain documentation evidence only and
must be unreachable in the new runtime.

The generated-key grammar remains authoritative for server-produced public
state. `DynamicGeneratedPublicFactKeyGrammar` is retained and rewritten as the
single validator for an allocated key; its Provider-specific validation and
`prompt_contract()` responsibilities are removed. The contract-level helper
that scans decoded Provider documents for generated keys is removed. A legacy
key reaches ordinary extra-field rejection rather than a special key grammar
path.

## 5. Deterministic server allocation and fact-ring lifecycle

### 5.1 Narrow application abstraction

The implementation introduces exactly one narrow pure application abstraction,
`DynamicGeneratedPublicFactKeyAllocator`, in
`src/deviation_protocol/application/dynamic_narrative_models.py`. Its only
responsibility is to allocate and validate a collision-free public semantic key
from already authoritative scalar inputs. It performs no Provider call, prompt
work, repository read, state mutation, persistence, hashing, randomness, UUID
generation, clock read, normalization of Provider output, or storage-slot
selection.

The server-internal `DynamicAllocatedPublicFact` contains exactly `key` and
`value`. It is constructed only after a keyless `DynamicPublicFactProposal` has
passed the complete candidate boundary. It never appears in Provider input or
output.

### 5.2 Exact key algorithm

Only after finalization has locked current authority and freshly rebuilt and
revalidated both public and protected-reference records, the orchestrator
constructs one authoritative `unavailable_identifiers` application input. Its
contents are the union of:

1. every exact current public-fact `fact_id` exposed by the freshly rebuilt
   authoritative Frame, including declared public facts and all validated
   committed fact-ring entries;
2. `record.original` for every identifier-class record (`record.identifier is
   True`) in the exact freshly recomputed
   `_hidden_reference_index(current_resolved, None, self.catalog,
   live_provider_references=self.live_provider_references)` tuple; this is the
   repository's finite protected-reference collection from the same locked
   `ScenarioDefinition`, catalog, restored runtime, Session, Run, participation,
   Player Character binding, and applicable Live settings, and specifically
   includes each hidden `FactDefinition.fact_id` plus every other protected
   identifier capable of exactly equalling a generated public-fact key; and
3. every key selected for an earlier proposal in the same final candidate.

Human-text protected records do not become identifiers merely because they are
present in that tuple. The collection in item 2 is recomputed from the locked
authority and revalidated through the existing hidden-reference digest binding;
it is neither a pre-lock snapshot nor a Provider-derived collection. The
orchestrator passes the complete set as deterministic application input. The
allocator performs no repository read, dependency injection, persistence, or
independent state lookup.

The maximum-current precondition and successor handoff are authoritative. After
current authority is locked and revalidated, but before evaluating any
expression equivalent to `current_version + 1`, finalization validates that the
locked current version has a representable committed successor. The exact valid
locked-current range with a successor is `0..9223372036854775806`. A locked
current version of `9223372036854775807` is a valid committed current version
but fails closed before addition: the implementation does not construct
`9223372036854775808`, allocate a generated public-fact key, begin detached
successor-state mutation, mutate the fact ring, append or publish a story
segment, or commit. It must not rely on later model validation, database
overflow, or persistence failure, and it exposes only the existing sanitized
allocation/finalization failure boundary required by this plan.

For a representable successor, finalization performs this order exactly:

1. validate the locked current-version precondition;
2. compute the successor exactly once using ordinary integer addition;
3. validate that the computed successor is in
   `1..9223372036854775807`; and
4. use that same validated successor as the authoritative allocator and
   finalization input.

For each proposed fact, the allocator receives:

1. `successor_state_version`, the already validated authoritative successor
   computed exactly once by the locked finalization lifecycle only after its
   maximum-current precondition passes;
2. `proposal_ordinal`, the zero-based original tuple position `0`, `1`, or `2`;
3. the authoritative `unavailable_identifiers` set above, including any keys
   allocated earlier in the same candidate.

It enumerates collision probes in ascending decimal order from `000` through
`999`. The successor-version token uses this exact minimum-width decimal
encoding:

1. render the authoritative successor in ordinary base-10 decimal;
2. left-pad a value with fewer than six decimal digits using ASCII `0` until
   the token contains exactly six digits;
3. preserve a value with exactly six digits byte-for-byte;
4. preserve every decimal digit of a value with more than six digits;
5. perform no truncation, wraparound, modulo reduction, hashing, scientific
   notation, sign rewriting, or other normalization; and
6. keep the proposal ordinal and collision probe at fixed widths of two and
   three decimal digits respectively.

The complete constructed key is exactly:

```text
public-note-{minimum-width-six successor decimal}-{two-digit proposal ordinal}-{three-digit collision probe}
```

The following version-token examples are normative: successor version `1`
renders as `000001`, successor version `999999` renders as `999999`, successor
version `1000000` renders as `1000000`, and successor version
`9223372036854775807` is preserved in full as `9223372036854775807` and is
accepted. Proposal ordinal `0` at probe `000` therefore produces
`public-note-000001-00-000` for version `1`,
`public-note-999999-00-000` for version `999999`,
`public-note-1000000-00-000` for version `1000000`, and
`public-note-9223372036854775807-00-000` for version
`9223372036854775807`. The first constructed key
absent from the
`unavailable_identifiers` set under exact identifier equality is selected. There
is no casefolding, compatibility folding, whitespace normalization, rewriting, or other
normalization in this collision comparison. A collision with a current public
identifier, hidden/protected identifier, or earlier same-candidate allocation
advances monotonically to the next probe. The selected key is added to the same
unavailable set before the next proposal.

This scheme is reconciled with current repository bounds:

- `GameSessionRow.state_version` and `GameSnapshotRow.state_version` in
  `src/deviation_protocol/infrastructure/orm_models.py` use SQLAlchemy signed
  `BigInteger`; `src/deviation_protocol/application/session_service.py`
  explicitly revalidates authoritative Game Session state versions in the
  inclusive range `0..9223372036854775807` (`0..2**63 - 1`). The exact valid
  locked-current range with a committed successor is
  `0..9223372036854775806`, and the complete persistable authoritative
  successor range is exactly `1..9223372036854775807`. A locked current version
  of `9223372036854775807` follows the pre-addition failure above and is not
  truncated, wrapped, or reduced;
- the narrow server-generated public-fact-key structural grammar becomes
  `^public-note-(?:[0-9]{6}|[1-9][0-9]{6,18})-[0-9]{2}-[0-9]{3}$`, paired with
  separate semantic validation that the decoded successor is in the exact range
  above, the ordinal is `0..2`, and the probe is `0..999`; structural grammar
  acceptance does not imply semantic numeric-range acceptance. This accepts the
  complete repository-supported successor range while semantic validation
  rejects zero, negative successors, and values above `9223372036854775807`,
  without accepting a sign, leading zero on a token wider than six digits,
  truncation, or alternate numeric notation;
- generated keys are 25..38 ASCII characters. The maximum comes from the
  19-decimal-digit signed-`BIGINT` maximum and remains within the existing
  1..80 committed public-fact semantic-key boundary and its broader
  `^[A-Za-z0-9][A-Za-z0-9_.:-]*$` validator;
- the existing process-local 512-attempt ledger remains a runtime capacity
  boundary only; it does not narrow the authoritative persistence or grammar
  range;
- a scenario has at most 256 declared facts and the dynamic ring has exactly 12
  fact slots, so the public portion of the collision domain has at most 268
  identifiers; protected identifiers are also authoritative unavailable inputs,
  so the design does not assume that one of the 1,000 probes must be free; and
- the format contains no Session, Run, Player Character, job, lease, receipt,
  storage slot, event, Provider request, secret, hash, random value, UUID, clock,
  or protected/internal identifier.

No numeric ring slot is encoded in the public key. The existing slot ordinal is
intentionally private and cannot be reused as the public identity. The public
successor state version is already part of the Action/View contract, while the
proposal ordinal and collision probe carry only bounded allocation order.
`DynamicGeneratedPublicFactKeyGrammar.validate(...)` remains a narrow local
server-output validator in
`src/deviation_protocol/application/dynamic_narrative_models.py`; widening only
its successor-version component does not weaken unrelated public identifier
validation or the global protected/internal identifier detector. Provider
candidates remain strictly keyless, and a Provider-authored key remains an
extra forbidden field even if its text would match the server grammar.

The maximum-current precondition failure, an invalid successor version, invalid
proposal ordinal, impossible exhaustion of all 1,000 probes across the complete
public/protected/same-candidate domain, malformed current public-fact identity,
malformed committed ring, or failure of
`DynamicGeneratedPublicFactKeyGrammar.validate(...)` emits
only the new closed local
`DynamicNarrativeRejectionDiagnostic.FINAL_GENERATED_PUBLIC_FACT_KEY_ALLOCATION`
token
`DNVS_LIVE_DIAG_FINAL_GENERATED_PUBLIC_FACT_KEY_ALLOCATION`. Public behavior
remains the existing HTTP `503` envelope with
`NARRATIVE_PROPOSAL_REJECTED` / `Narrative processing failed`. The failure
produces no Provider replacement or third generation, exposes no candidate
value or conflicting protected identifier, and leaves public state unchanged.

For any ordinal, exhaustion means that every probe from `000` through `999` is
present in the complete unavailable set. It fails closed before detached
successor mutation or authoritative commit. No partial allocation becomes
public; public state, Session/story revision, story segments, and public facts
remain exact. It introduces no additional Provider generation, replacement,
transport retry, or third request. The existing sanitized allocation/finalization
failure boundary remains authoritative, and no conflicting protected identifier
may enter a public response, diagnostic, log evidence, or review evidence.

### 5.3 Exact application stage and ordering

Allocation occurs inside `DynamicNarrativeOrchestrator._finalize` in this exact
sequence:

1. the final initial-or-replacement Provider candidate passes the existing
   strict v2 keyless schema plus length, submitted-Action, storage, complete
   string-leaf, internal/secret, protected-reference, and semantic validation;
2. finalization locks Session then job and obtains complete current authority;
3. stale authority, Session/snapshot, Run, participation, Player Character and
   revision, dynamic story revision, View/frame, suggestion, request, public and
   protected-reference records/digests, fenced lease, and validated-proposal
   bytes/digest are freshly revalidated, and the authoritative Frame and
   committed fact ring are freshly reconstructed and validated;
4. before evaluating any expression equivalent to `current_version + 1`, the
   orchestrator validates that the locked current version is in the exact
   successor-bearing range `0..9223372036854775806`; a locked current version of
   `9223372036854775807` fails at the existing sanitized boundary before
   successor calculation, allocation, detached mutation, fact-ring mutation,
   story publication, or commit;
5. after that precondition passes, the orchestrator computes the successor
   exactly once using ordinary integer addition;
6. the orchestrator validates that the computed successor is in
   `1..9223372036854775807` and uses that same validated value as the
   authoritative allocator and finalization input;
7. the orchestrator derives the complete authoritative
   `unavailable_identifiers` set from that same locked and revalidated state;
8. the allocator evaluates proposals in stable zero-based original list order;
9. each proposal begins at probe `000`;
10. exact collision with a current public identifier, hidden/protected identifier,
   or earlier same-candidate allocation advances monotonically through `001` to
   `999`;
11. each selected key is added to the same-candidate unavailable set before the
    next proposal;
12. every selected server-produced key passes the existing local
    `DynamicGeneratedPublicFactKeyGrammar` validator and committed semantic-key
    validators; and
13. only the complete successfully allocated collection proceeds to
    `_apply_candidate_slots` and complete successor-candidate validation;
14. finalization prospectively derives `public_fact_count` exactly once as
    `len(allocated_public_facts)` from that final allocated tuple; and
15. before normal UoW commit, that same scalar is included in the private event
    and the `TurnResponse` material staged for persistence, direct return,
    replay, and committed request-status projection, together with the complete
    successor publication set.

No key is allocated for a rejected initial generation; only the final complete
strictly valid candidate can reach step 2. Allocation completes before any
event, response, accepted prose, or job transition is added to the UoW and
before the final commit begins. `_expected_finalize_publication` uses the same
pre-addition maximum-current guard, exactly-once ordinary successor calculation,
successor range validation, pure allocation, and exact unavailable-identifier
input established from the authority proven equal during locked finalization;
it does not calculate a successor before the guard, independently read a stale
repository, or introduce a persistence boundary. Identical proven authority and
candidate bytes therefore produce byte-identical expected keys during
commit-uncertainty reconciliation.

Zero proposed facts performs zero allocations and zero ring writes. For one,
two, or three facts, original Provider tuple order is authoritative only as
proposal order: ordinals are assigned before allocation and never sorted by
value, JSON key order, provider metadata, dictionary order, storage slot, or
generated key. Every proposal represents a new public observation. With no
model-owned identifier, it cannot select or revise an existing semantic fact.
Candidate-local duplicate normalized values reject earlier; equality with an
already committed value does not grant replacement authority and does not
change allocation order.

After allocation, the existing fact-ring storage algorithm is reused exactly
for capacity and rollover:

1. ring size remains 12 with storage slots `.00` through `.11`;
2. `base_slot = successor_state_version modulo 12`;
3. allocated fact ordinal `i` writes to `(base_slot + i) modulo 12`;
4. writes occur in ascending proposal ordinal;
5. an unrelated entry at a destination is evicted; and
6. the strict `{"key": ..., "value": ...}` wrapper remains the committed slot
   shape.

The old model-key no-op and same-key replacement branches are removed for new
v2 candidates because a Provider no longer owns semantic identity. Legacy
committed v1 ring entries remain valid input to reconstruction, collision
checking, rollover, later projection, and eviction; no storage migration is
required.

Every allocated key is revalidated by
`DynamicGeneratedPublicFactKeyGrammar`, the broader committed semantic-key
validator, and the fixed internal/protected-shape assertions before it becomes
candidate state. Only committed, well-shaped values in the 12 exact fact slots
enter later Frame and Prompt context. Storage keys and slot ordinals remain
unprojected.

### 5.4 Atomicity, replay, stale authority, and failure

Allocation does not advance authority. The accepted allocated facts become
public only in the existing one atomic finalization commit containing the
successor snapshot/state, fact ring and non-fact slots, event, response/receipt,
accepted prose/presentation, committed job, three suggestions, next View/frame,
and one successor Session version.

The following behavior is exact:

- a locked current version of `9223372036854775807` fails before successor
  calculation and allocation and leaves detached state, fact ring, story,
  version, and commit state exact;
- an otherwise-invalid initial candidate follows its existing one-replacement
  eligibility; an otherwise-invalid replacement terminalizes without a third
  generation;
- a legacy Provider `key` field is a complete schema failure, never stripped or
  reused;
- a server-allocation failure is finalization failure, not Provider failure, and
  never spends a replacement allowance;
- a stale revision or any other authority mismatch rejects before allocation is
  published and leaves every story artifact unchanged;
- two different same-View submissions may both call the Provider lock-free, but
  Session serialization allows at most one matching finalizer to allocate and
  commit the successor; the loser is stale with no losing fact;
- an exact concurrent duplicate has one owner, one job, one final key set, and
  one commit; the follower performs no allocation or Provider work;
- an exact post-completion replay returns the stored response and committed View
  without allocating, mutating, reserving, or calling the Provider;
- finalization retry for an already validated proposal under the existing fenced
  authority recomputes the same key set and does not call the Provider;
- commit failure or proven `COMPLETE_OLD` leaves the prior ring, version,
  response, prose, event, and View exact;
- `COMPLETE_NEW` requires the exact server-allocated successor keys as part of
  the expected ring and preserves the committed result; and
- `PARTIAL`, `IMPOSSIBLE`, or `UNKNOWN` keeps the existing sanitized
  `NARRATIVE_OUTCOME_UNKNOWN` behavior and never resends the Provider request.

### 5.5 Exact committed fact-count evidence

`NEW_PUBLIC_FACTS` means only the exact number of public facts newly accepted
and committed by the current Action. Its server-owned source is
`len(allocated_public_facts)`, where `allocated_public_facts` is the final
allocated fact tuple produced by `_allocate_public_facts` for the final complete
validated candidate. Providers propose zero to three keyless values, and the
complete candidate is deterministically accepted or rejected; there is no
partial per-fact filtering.

After any authorized application replacement decision has selected the final
candidate, allocation produces its final tuple. During the same atomic
finalization, before staging the event, stored response, committed request-
status material, or direct response and before normal UoW commit, finalization
prospectively derives the scalar from that tuple. The same prospective scalar
is carried in the private event and in the one `TurnResponse` that is stored and
later projected by direct success, replay, and committed request status. There
is no separate request-status write.

Before normal UoW commit succeeds, the derived value is staged candidate
material only. It is not yet an authoritative committed result and must not be
publicly claimed as committed. Normal commit success gives the event, stored
response, replay/status projection, and direct committed response the same
authoritative meaning atomically. Commit failure or rollback publishes and
preserves no claimed committed count.

`_expected_finalize_publication` constructs the expected `COMPLETE_NEW` event,
response, and successor publication prospectively from the same final validated
candidate, final allocated tuple, and `len(allocated_public_facts)` derivation.
The existing reconciliation seam compares that expected result with the
authoritative existing committed state. The scalar becomes authoritative and
publicly claimable through this path only when the complete reconciliation
establishes `COMPLETE_NEW`; reconciliation does not mutate an already committed
response. Normal commit success and `COMPLETE_NEW` therefore converge on the
same committed result.

Only the final successfully committed or reconciled candidate contributes.
Rejected, failed, superseded, and non-published generations contribute zero and
are never added to or double-counted with the final tuple. An authorized
application replacement contributes only its final selected candidate.

The committed response's exact Dynamic Narrative feedback semantics are:

```text
feedback_parameters={
  "outcome_result": <validated result>,
  "public_fact_count": <integer 0..3>
}
```

This rule explicitly supersedes the older exact map in
`docs/dynamic_narrative_vertical_spike_plan.md` that fixed committed Dynamic
Narrative feedback to only
`{"outcome_result": <validated result>}`. The existing `outcome_result` remains
required and the new `public_fact_count` is also required for an exact
`DYNAMIC_NARRATIVE_COMMITTED` result. Zero is explicitly serialized as integer
`0`; missing, null, boolean, non-integer, or out-of-range data is invalid and is
not interpreted as zero.

The same count is recorded by the private `DynamicNarrativeTurnCommitted`
event's `public_fact_count` and must agree with the normal response, stored
response/replay, committed request-status projection, and expected committed
response proven by `COMPLETE_NEW` reconciliation. A normal direct HTTP `200`
response and a `202` request that later projects `COMMITTED` therefore expose
the same stored committed value. No new top-level Action DTO field, API schema
or route, or `PlayerSessionView` field is introduced.

The scalar is not derived for the first time after commit and requires no post-
commit response mutation or second database write. It is not reconstructed from
the successor View, fact-ring net growth, logs, UI totals, memory categories,
Provider responses or raw proposal counts, generated keys, total Run facts,
narrative count, or suggestion count. It publishes no fact value, generated
key, storage slot, collision input, allocation detail, hidden identifier,
prompt, response, header, credential, exception body, or Provider metadata.

### 5.6 Browser-visible post-Action evidence

After an exact committed Dynamic Narrative Action and its immediate
authoritative View refresh, the browser retains the validated committed Action
response and may render this privacy-safe summary:

```text
REVISION=1
NEW_STORY_SEGMENTS=1
SUGGESTIONS=3
NEW_PUBLIC_FACTS=0
```

The evidence sources are exact:

- `REVISION` is the committed Action result's
  `resulting_state_version`—the resulting authoritative revision;
- `NEW_STORY_SEGMENTS` is the exact accepted narrative-addition count in that
  committed Dynamic Narrative result;
- `SUGGESTIONS` is the executable dynamic suggestion count in the successor
  View for the same Session and exact revision; and
- `NEW_PUBLIC_FACTS` is the committed response's
  `feedback_parameters.public_fact_count`.

The summary remains available after the immediate authoritative View refresh
and is retained from the committed response rather than reconstructed from the
View. It renders only when the response and successor View have the exact same
Session and revision association. Zero remains visibly distinct from missing.
Missing, malformed, out-of-range, wrong-lifecycle, wrong-Session, or
wrong-revision data fails closed and renders no claimed summary. The UI must not
render protected content, fact values, generated keys, allocation details,
hidden identifiers, or Provider material.

## 6. Historical disposition of the Prompt-only candidate

The three-path Prompt-only diff recorded when the published key-ownership
amendment was authored is historical. Its disposition remains design rationale;
it is not the current evidence-remediation budget and requires no edit in the
future four-path implementation:

| Historical material | Published key-ownership disposition |
| --- | --- |
| `COMBINED_DEFAULT` ordering, explicit decoded-control instruction, canonical request-as-data boundary, complete-object requirement, and no-fence/no-extra-field presentation | Retained as non-authoritative defense in depth, with the key-ownership text rewritten for the v2 keyless contract |
| Typed, canonical, strict-valid synthetic example and bounded suggestion-pool/Action-exclusion construction | Retained as non-authoritative defense in depth, but rewritten so each public-fact item contains only `value` and no generated key example |
| Namespace instruction requiring `proposed_public_facts[*].key` and the model to invent a `public-note-*` key | Removed; replaced by an instruction that facts contain semantic public statements only and that identifiers are server-owned and must not be emitted |
| `DynamicGeneratedPublicFactKeyGrammar.prompt_contract()` in the Prompt | Removed from the Prompt and from Provider ownership |
| Adapter/schema validation of model-generated key syntax | Removed; v2 validates the one-field fact object and rejects a legacy `key` as an extra field |
| `GENERATED_PUBLIC_FACT_KEY_CONTRACT`, its typed replacement instruction, and recovery/final diagnostic maps | Removed from live Provider classification; historical tokens remain documentation evidence only |
| `DynamicGeneratedPublicFactKeyGrammar` pattern and validator | Retained and rewritten as independently valid server-produced public-state validation |
| Direct Prompt/example tests for JSON completeness, controls, protected shapes, Action exclusion, and exact transport configuration | Retained but rewritten around the keyless example and absence of model-owned key instructions |
| Direct generated-key schema, recovery, precedence, and final diagnostic-family tests | Removed or rewritten to prove legacy-key extra-field rejection, obsolete-family unreachability, deterministic server allocation, and no extra generation |
| Existing tests for all other schema families, complete candidate scanning, protected/internal rejection, two-generation ceiling, zero transport retry, stale authority, replay, concurrency, atomic finalization, and public error sanitization | Retained unchanged where assertions remain contract-correct; revised only where candidate v2 fixtures must become keyless or expected committed keys become server-allocated |
| `_DynamicFakeProvider` in `src/deviation_protocol/api/demo_composition.py` constructing keyed `DynamicPublicFactProposal` values and a literal v1 candidate at that checkpoint | Minimally updated to emit the same strict candidate v2/keyless public-fact contract as the real Provider boundary while preserving its deterministic Fake/Demo schedule, request-derived semantics, failure ordinal, observation tokens, metadata, and lifecycle role |

No Prompt-only code or test is retained if it contradicts server key ownership.

## 7. Exact current inventory, future implementation delta, and aggregate manifest

Before and after this documentation-only bounded correction, the complete
worktree inventory is exactly these nine unstaged paths:

1. `PLANS.md`;
2. `docs/dynamic_narrative_provider_reliability_remediation_plan.md`;
3. `docs/public_client_contract.md`;
4. `docs/engineering/codex_workflow.md`;
5. `src/deviation_protocol/application/dynamic_narrative_models.py`;
6. `src/deviation_protocol/application/dynamic_narrative_orchestrator.py`;
7. `src/deviation_protocol/api/demo_composition.py`;
8. `tests/unit/test_dynamic_narrative.py`; and
9. `tests/unit/test_narrative_provider.py`.

The first four paths are the authority correction. The last five are the
protected existing runtime/test candidate and must retain their correction-
entry SHA-256 values throughout this task. The correction handoff records all
nine resulting per-path hashes and the complete nine-path diff byte size and
SHA-256. Those resulting values are the proposed baseline for the independent
re-review; this authoring task does not approve or lock them.

The later evidence-remediation implementation budget is exactly a **four
tracked-path delta with zero newly created files**:

| Exact path | Starting state | Exact responsibility |
| --- | --- | --- |
| `src/deviation_protocol/application/dynamic_narrative_orchestrator.py` | Already dirty in the nine-path candidate; hash may change only during separately authorized implementation | Derive the bounded count prospectively from the final allocated tuple at the common finalization seam and preserve it through committed response, replay/status, private event, and `COMPLETE_NEW` expectation/reconciliation. |
| `tests/unit/test_dynamic_narrative.py` | Already dirty in the nine-path candidate; hash may change only during separately authorized implementation | Prove exact count, final-candidate, replay/reconciliation, event agreement, failure, and privacy semantics. |
| `web/src/App.tsx` | Currently clean; permitted to become modified only during separately authorized implementation | Retain and validate the committed Action response through the authoritative View refresh and render the exact Session/revision-associated evidence summary. |
| `web/src/App.action-loop.test.tsx` | Currently clean; permitted to become modified only during separately authorized implementation | Prove direct-200, 202-to-`COMMITTED`, refresh retention, association, fail-closed, privacy, and preserved action-loop behavior. |

This four-path list is the technical implementation delta, not the complete
synchronized candidate. After successful implementation, the complete
aggregate worktree would ordinarily contain exactly eleven unstaged paths: all
nine paths above plus the two Web paths. It is not eleven newly implemented
paths. The four authority documents remain byte-exact at their independently
approved hashes during implementation. The three excluded existing code/test
paths—`dynamic_narrative_models.py`, `demo_composition.py`, and
`test_narrative_provider.py`—also remain hash-protected. Only the two already-
dirty implementation paths may change from the approved nine-path manifest,
and only the two named clean Web paths may join the dirty inventory. No path
outside the resulting eleven-path inventory may appear.

Implementation does not require and must not modify:

- `src/deviation_protocol/application/dynamic_narrative_models.py`;
- `src/deviation_protocol/api/demo_composition.py`;
- API schemas or routes;
- Session/View projection;
- Web schema/client modules;
- fixtures;
- database models or migrations;
- the Provider adapter; or
- `tests/unit/test_narrative_provider.py`.

A need for any other path stops implementation and requires a new authority
correction and independent review before that path is edited. This
documentation task does not authorize implementation.

### 7.1 Manifest lock and allowed transition

The independent re-review must freshly record and verify the repository root
and branch, `HEAD`, local `origin/main`, ahead/behind, exact nine-path inventory,
SHA-256 of every dirty path, complete nine-path diff byte size and SHA-256,
empty index, no untracked paths, no conflicts, and no active Git operation. If
and only if the re-review returns the operative approval verdict, that exact
resulting nine-path manifest becomes the authorized pre-implementation baseline
for this aggregate candidate under the workflow's manifest-locked dirty
aggregate-candidate exception. It is explicitly not a Git-clean baseline.

Before implementation and every later task, the applicable manifest must be
reverified. The allowed nine-to-eleven transition is exact: the four authority
paths and three excluded existing code/test paths remain at their approved
protected hashes; the orchestrator and backend test are the only already-dirty
paths whose hashes may change; the two named Web paths are the only clean paths
that may become modified. The implementation handoff records every final dirty
path's SHA-256 plus the complete final eleven-path diff byte size and SHA-256.
Any unexplained repository identity, path, hash, Git-state, or inventory drift
blocks the task.

The approved manifest is a substitute only for the ordinary pre-implementation
documentation publication and clean-baseline gate for this exact candidate.
The four authority paths are not separately staged, committed, or pushed. The
manifest authorizes no implementation, deterministic verification, Live
traffic, freeze, Gate, review, staging, commit, push, or unrelated edit; each
later action retains its separate authorization and evidence boundary.

### 7.2 Deterministic implementation responsibilities

The four-path implementation must prove all of the following with fake,
scripted, or synthetic inputs and no Provider or network request:

1. zero committed facts reports integer `0`;
2. one, two, and three committed facts report their exact counts;
3. zero is neither omitted nor converted to null or unknown;
4. the count comes from the final allocated tuple, not raw Provider proposals;
5. rejected candidates do not inflate it;
6. an authorized application replacement reports only the final accepted
   candidate;
7. normal response, stored replay, request-status completion, private event, and
   `COMPLETE_NEW` reconciliation agree;
8. browser direct-`200` rendering works;
9. browser `202`-to-`COMMITTED` rendering works;
10. the summary survives the authoritative View refresh;
11. Session and exact revision association are enforced;
12. invalid or missing feedback fails closed;
13. fact values, `public-note-*` keys, hidden identifiers, Provider material,
    prompts, headers, credentials, raw exceptions, and allocation details are
    not rendered;
14. stale, uncertain, failed, refresh, action-lock, single-submit, and
    no-manual-replay behavior remains unchanged; and
15. every test remains deterministic, unpaid, and offline.

No fixture, integration, API-schema, Provider-adapter, database, or migration
test path is added. Existing broader tests may be run for verification, but the
implementation edit budget remains the four exact paths above.

## 8. Exact deterministic validation before Live traffic

All commands run from `D:\deviation-protocol` in PowerShell 7+ with the
repository venv. `RUN_LIVE_DEEPSEEK_TEST` remains disabled. No database or
Provider variable is inherited by the canonical Offline gate.

The future implementation verification set is mandatory and ordered:

1. run the focused backend test node IDs covering every responsibility in
   section 7.2 and record those exact node IDs;
2. run the complete relevant Dynamic Narrative backend files:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_dynamic_narrative.py tests/unit/test_narrative_provider.py -q
```

3. run the focused Web action-loop file:

```powershell
npm --prefix web run test:run -- src/App.action-loop.test.tsx
```

4. run the complete Web test suite, typecheck, lint, and build:

```powershell
npm --prefix web run test:run
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

5. run compilation, package, migration, and diff checks:

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests alembic
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic history
git diff --check
```

6. run the complete required sanitized Offline verification:

```powershell
.\scripts\verify.ps1 -Mode Offline
```

No Live traffic may start until every command passes against one unchanged
four-path implementation-delta identity within one unchanged eleven-path
complete aggregate identity. Full or MySQL verification is not a substitute for
Offline. CI is not a substitute for any relevant local verification above.

Before Live traffic, freeze a sanitized successor manifest containing exact
repository and branch identity, parent `HEAD`, local `origin/main`,
ahead/behind, the approved nine-path starting manifest, the exact allowed
nine-to-eleven transition, all eleven dirty paths and their SHA-256 values, the
complete eleven-path diff byte size and SHA-256, deterministic command evidence,
approved-authority identity, empty index, no untracked path, no conflict, and no
active operation. The four-path delta identity is recorded within that complete
aggregate manifest; it does not replace it.

## 9. Future separately authorized user-operated real-Provider validation

Mocks, fixtures, source inspection, and deterministic tests are necessary but
not sufficient for a later Live claim. No Live execution is authorized by this
documentation correction. Only after the authority is independently approved
and its exact nine-path baseline is manifest-locked, the separately authorized
four-path implementation and complete local verification pass, and the Live-
evidence preflight in
`docs/engineering/codex_workflow.md` passes may a separate authorization permit
the two real-Provider stages below.
The user launches every Live process from a fresh PowerShell process in which
Provider configuration is present before launcher startup, and performs every
browser operation. Codex must never receive or inspect the API key, operate the
browser, issue a direct Provider/API substitute call, launch a network-restricted
process as authoritative Live evidence, or inspect raw Provider requests or
responses.

The exact launcher command for every case is:

```powershell
pwsh -File .\scripts\start-demo.ps1 -Mode DynamicNarrative -DynamicProvider Live
```

`DEEPSEEK_MAX_RETRIES` must be `0` in the launching process. The user confirms
that the official dashboard filter corresponds to the same configured key,
without recording the key, its label, or an absolute usage total.

For both stages, each case uses a fresh launcher process, browser Session, Run,
and eligible default investigator; begins at state version `0`; retrieves one
current View; submits one Action exactly once; performs no refresh, replay,
duplicate click, second Action, or unplanned Action; has no concurrent DeepSeek
activity; and shuts down before the next case. Only sanitized public results,
closed-set local diagnostic families, and the official per-case request-count
delta may be recorded.

### 9.1 New diagnostic epoch E1-E5: exactly 5 cases, maximum 10 requests

This is a new diagnostic epoch after a material runtime/evidence change. It is
not a continuation, repair, retry, replacement, or reinterpretation of
historical D1-D5. Historical D1 remains permanently incomplete, and no
historical result is combined with this epoch. The fixed matrix is:

| Case | Fresh Run | Exact one Action |
| --- | --- | --- |
| E1 | A | Submit suggested ordinal `0` with its complete nested payload unchanged |
| E2 | B | Submit custom text `Examine the sealed intake room for visible evidence that the death record is wrong.` |
| E3 | C | **Fixed zero-proposed-fact case, third in order:** submit suggested ordinal `1` with its complete nested payload unchanged |
| E4 | D | Submit suggested ordinal `2` with its complete nested payload unchanged |
| E5 | E | **Fixed non-empty allocation case:** submit custom text `Record the most concrete new public observation from the visible scene and continue cautiously.` |

The diagnostic contains exactly 5 gameplay Action submissions: 3 suggested and
2 custom. Every case permits one initial generation and at most one complete
replacement, exactly zero transport retries, and no third request. Its exact
maximum total Provider-request budget is 10.

E1 may exercise the same published scenario/action responsibility as historical
D1, but it is evidence only for epoch E1-E5. All five cases require fresh
launchers, browser Sessions, Runs, and eligible default investigators. The epoch
requires its own separately authorized Provider-generation budget. Historical
generations remain recorded, but do not consume or satisfy any part of the new
maximum-ten budget.

For each case record:

1. unchanged repository, approved authority, four-path implementation-delta,
   complete eleven-path aggregate, and complete-diff identities before and
   after;
2. selected ordinal or exact approved custom text;
3. public state version before and after;
4. HTTP status and sanitized public result/error;
5. the one final closed-set diagnostic family, if emitted;
6. the complete browser-visible post-Action evidence summary retained from the
   committed response and exact successor View:

   ```text
   REVISION=1
   NEW_STORY_SEGMENTS=1
   SUGGESTIONS=3
   NEW_PUBLIC_FACTS=<integer 0..3>
   ```

7. confirmation that response and View share the exact Session and revision,
   zero is distinct from missing, and no fact value, key, allocation detail,
   hidden identifier, or Provider material is rendered; and
8. the official per-case Provider-request delta, exactly `1` or `2` for a
   complete Provider case.

E3 is permanently designated before execution as the one successful zero-fact
case. Its Action remains exactly the third-case, fresh-Run-C suggested ordinal
`1` complete nested payload; it is not selected or changed after seeing output.
E3 passes this responsibility only if it returns a successful committed
narrative result, the summary reports revision `1`, one new story segment, three
suggestions, and integer `NEW_PUBLIC_FACTS=0`, and the official request delta is
exactly `1` or `2`. Existing declared public facts in the View are unrelated to
this per-Action count and cannot replace the committed scalar. Missing or
invalid count evidence makes E3 and the complete epoch incomplete.

E5 passes its fixed ownership-path responsibility only if its successful
committed response reports `NEW_PUBLIC_FACTS` in `1..3` through the exact
privacy-safe summary and the official request delta is exactly `1` or `2`.
Neither the browser nor the evidence record exposes a fact value, generated
key, allocation detail, hidden identifier, or Provider material. An E5 result
with integer `0`, missing or invalid count evidence, or wrong Session/revision
association makes E5 and the complete epoch incomplete.

The diagnostic epoch passes only if all 5 fixed cases return complete HTTP `200`
commits, each advances version exactly once from `0` to `1`, each adds exactly
one story segment and three suggestions, renders an exact associated summary,
emits no obsolete generated-key Provider diagnostic or other
schema/safety/authority/finalization family, binds every official delta exactly,
and satisfies both fixed responsibilities: E3 reports integer `0`, and E5
reports an integer in `1..3`. If either responsibility or any privacy/association
condition is absent, the complete epoch is incomplete and progression to
candidate freeze and the formal Gate stops.

Do not add a sixth case, replace an Action after observing output, refresh,
replay, duplicate-click, substitute an Action, or rerun until a favorable zero-
fact or non-empty sample appears. Another Provider schema family,
protected/internal material, official request-count mismatch, transport or
publication uncertainty, HTTP `409` `NARRATIVE_OUTCOME_UNKNOWN` with official
delta `0`, or any attempt to exceed the fixed request budget retains its
existing stop behavior. No diagnostic failure is hidden by restarting the
epoch or importing historical evidence. Absence of an obsolete generated-key
Provider diagnostic in these five stochastic samples is not proof of
unreachability; that guarantee remains owned
by the strict keyless schema, deterministic server allocation, and Offline
regressions.

### 9.2 Formal acceptance Gate: exactly 4 cases, maximum 8 requests

After the five-case diagnostic passes and the executable candidate identity is
frozen again, run a fresh Gate from Case 1:

| Case | Fresh Run | Exact one Action |
| --- | --- | --- |
| 1 | A | Submit suggested ordinal `0` with its complete nested payload unchanged |
| 2 | B | Submit custom text `Examine the sealed intake room for visible evidence that the death record is wrong.` |
| 3 | C | Submit suggested ordinal `1` with its complete nested payload unchanged |
| 4 | D | Submit suggested ordinal `2` with its complete nested payload unchanged |

The Gate contains exactly 4 gameplay Action submissions: exactly 3 suggested
and 1 custom. Every case permits one initial generation and at most one complete
replacement, exactly zero transport retries, and no third request. The exact
maximum total Provider-request budget is 8.

All 4 consecutive cases must satisfy the current complete HTTP `200`
`DYNAMIC_NARRATIVE_COMMITTED` public success contract, advance version exactly
once from `0` to `1`, add exactly one story segment and three suggestions,
publish no protected/internal material, produce no duplicate or uncertain
commit, and have an official per-case request delta of exactly `1` or `2`.
Repository, approved-authority, instruction, four-path implementation-delta,
complete eleven-path aggregate, and complete-diff identities must remain
unchanged before and after every isolated case.

An official-count mismatch, unavailable count view, or inability to bind the
count filter safely makes the case incomplete. An HTTP `409`
`NARRATIVE_OUTCOME_UNKNOWN` with official delta `0` requires separate
environment/transport/publication diagnosis and does not prove a generated-key
defect. A generated-key Provider schema failure after implementation means the
ownership correction is incomplete. Another schema family is a separate
reliability defect. A Codex sandbox/network failure does not prove Provider or
key invalidity. None authorizes a blind retry.

Any runtime or test byte change after either Live stage invalidates all later
Live evidence. Repeat the complete deterministic sequence and freeze a new
exact identity. Historical D1 is never repeated or reclassified. If epoch E1-E5
has already begun, the changed candidate requires a new separately named and
separately authorized five-case diagnostic epoch with the same fixed case
responsibilities; no result is carried across epochs. The formal Gate restarts
at Case 1 only after that complete new epoch passes.

## 10. Post-task lifecycle and publication boundaries

The published `DN-DKO-006` key-ownership correction and its operative approval
record remain historical completed steps. The current D1 evidence correction
does not inherit that approval. Its exact lifecycle keeps these stages
separate:

1. author the exact four-document authority-correction candidate;
2. conduct an independent new-session read-only review;
3. when that review returns findings, perform a bounded correction in the same
   exact four-document budget;
4. conduct an independent new-session read-only re-review of the corrected
   four-document candidate;
5. if and only if that re-review returns the operative approval verdict, lock
   the resulting exact nine-path dirty baseline by repository/branch identity,
   `HEAD`, local `origin/main`, ahead/behind, path inventory, every per-path
   SHA-256, complete-diff byte size/SHA-256, empty index, no untracked path, no
   conflict, and no active Git operation; do not separately stage, commit, or
   push the four authority documents;
6. separately authorize the exact four-path implementation delta;
7. perform complete deterministic/local verification;
8. separately authorize and, only then, run the future E1-E5 Live diagnostic
   epoch;
9. freeze the exact complete executable candidate after the diagnostic passes;
10. separately authorize and run the unchanged formal Gate from Case 1;
11. conduct a fresh independent implementation review;
12. under separate authorization, stage the complete approved aggregate
    candidate;
13. under separate exact authorization, create one intentional aggregate local
    commit;
14. have the user perform the manual push; and
15. confirm publication or separately authorize status synchronization or any
    later phase.

Stages 1 and 2 occurred, and stage 2 returned `CHANGES_REQUIRED` rather than
approval. This task completes stage 3 only as an unstaged documentation
candidate. Stage 4 is the unique next task. No implementation or Live activity
is authorized.

The ordinary repository rule still requires independently approved authority
documentation to be staged, committed, manually pushed, and confirmed as a new
clean baseline before implementation. This candidate qualifies for the
workflow's narrow manifest-locked dirty aggregate-candidate exception because
the intentionally preserved implementation candidate is already dirty in five
runtime/test paths while the correction occupies four documentation paths. A
four-document commit would not create a clean worktree; an aggregate nine-path
commit now would prematurely publish implementation before deterministic
verification, separately authorized Live evidence, freeze, formal Gate, and
independent implementation review. Cleanup, discard, stash, premature staging,
and either premature commit are prohibited.

If stage 4 approves, its exact nine-path manifest is therefore the authorized
substitute for the ordinary pre-implementation publication/clean-baseline gate
for this aggregate candidate only. It must never be described as Git-clean and
does not create permission to implement on an arbitrary dirty worktree. Every
later task verifies that manifest and the exact allowed transition in section
7.1 and stops on unexplained drift. Aggregate staging and the one aggregate
commit remain deferred until every named downstream gate has passed.

The implementation session must not review itself. The later implementation-
review approval binds exact candidate bytes and does not authorize a repository
edit merely to record that later verdict. Codex never pushes this repository.

## 11. Stop conditions

Stop without informal adaptation if:

- baseline or candidate identity differs;
- the separately authorized implementation does not begin from the exact
  independently approved nine-path manifest-locked baseline;
- any implementation path outside the exact four-path budget appears necessary;
- the scalar would not be derived prospectively from the final allocated tuple
  at the common finalization seam before publication material is staged, would
  require post-commit mutation, a second write, View/log reconstruction, or
  would treat missing/invalid data as zero;
- a Provider key/identifier field would remain or be reintroduced;
- an invalid response would be stripped, repaired, normalized, salvaged, or
  partially accepted;
- the protected/internal detector, strict validation, two-generation ceiling,
  zero-retry rule, stale binding, replay, or atomic finalization would weaken;
- any deterministic command or Offline verification fails;
- either Live matrix, request budget, evidence rule, or stop rule cannot be
  followed exactly;
- historical D1 would be retried, replaced, resumed at D2, reclassified, or
  combined with a future epoch;
- Live traffic would begin without separate authorization or without the
  complete Live-evidence preflight;
- a request count cannot be bound safely;
- a raw response, secret, key label, protected identifier, or internal state
  would need to be captured;
- either Live stage fails or is incomplete; or
- an unexplained Git identity, path, per-path hash, complete-diff identity,
  staged change, conflict, active Git operation, untracked path, or inventory
  transition differs from the applicable manifest.

No reset, restore, checkout, clean, unapproved retry, stage, commit, or push is
authorized as a remedy.

## 12. Completion criteria and residual uncertainty

This bounded four-document correction task is complete as an unstaged
documentation candidate only when
`PLANS.md`, this plan, `docs/public_client_contract.md`, and
`docs/engineering/codex_workflow.md` are the only paths changed by this task;
all protected pre-existing runtime/test bytes remain exact; the index remains
empty; the complete worktree identity is recorded; and all authorized read-only
documentation and hygiene checks pass. Candidate completion is not independent
approval. The prior review was not approved; this candidate addresses its two
findings but has not yet been independently re-reviewed. No later stage is
complete or authorized.

Even a later passed new diagnostic epoch and Gate prove only the exact bounded
candidate and nine consecutive user-operated cases. They do not prove long-run
Provider availability, schema reliability outside the observed matrix, billing behavior,
quality, moderation, production distribution, or production readiness. Strict
local validation remains mandatory and Provider output remains untrusted.

Guardrail impact: **None**. The narrow reusable manifest-locked dirty aggregate-
candidate exception belongs in the Codex workflow and adds or changes no
engineering guardrail ID.

The unique current next task is:

> An independent new-session read-only re-review of the corrected four-document authority candidate against the two prior independent-review findings.

Implementation is not the immediate next task and remains unauthorized unless
that re-review returns the exact operative approval verdict and verifies the
resulting nine-path manifest.

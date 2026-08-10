# Deviation Protocol Roadmap

This document is the authority for detailed project status and roadmap
placement. Feature and architecture decisions remain in their linked canonical
documents.

## Status language

- **Implemented:** supported by current code and verification evidence.
- **Accepted design / Approved product design:** decided and documented, but not
  implemented.
- **Deferred:** direction or detail remains undecided.
- **Planned phase:** assigned to a future phase whose implementation has not
  started.

## Dynamic Narrative Vertical Spike planning

The bounded
[Dynamic Narrative Provider Reliability Remediation Plan](docs/dynamic_narrative_provider_reliability_remediation_plan.md)
now contains the independently approved and published `DN-DKO-006`-corrected
deterministic generated-public-fact-key ownership amendment with status
`PLAN_AMENDMENT_PUBLISHED`. Historically, the focused independent review closed
`DN-DKO-004` and found `DN-DKO-005` not fully closed solely because of the
maximum-current-version and deterministic-regression gap identified as
`DN-DKO-006`. The bounded correction addressed only `DN-DKO-006`. A fresh
delta-focused independent review of the exact corrected two-document amendment
completed successfully and returned
`DYNAMIC_NARRATIVE_DETERMINISTIC_KEY_OWNERSHIP_PLAN_AMENDMENT_INDEPENDENT_REVIEW_APPROVED`.
That review fully closed `DN-DKO-006`; `DN-DKO-005` is therefore fully closed.
All amendment findings `DN-DKO-001` through `DN-DKO-006` are closed, and no
material finding remains within the approved review scope. The fresh review,
not the earlier authoring correction, supplied approval. The published
amendment remains the base key-allocation authority. For that amendment, the
strict candidate-v2/keyless compatibility edit for `_DynamicFakeProvider` in
`src/deviation_protocol/api/demo_composition.py` assigned values and order to
Fake/Provider output and keys to the orchestrator/server. Successor versions use
non-truncating minimum-width-six decimal encoding that preserves every digit
above `999999` through `9223372036854775807`. After current authority is locked
and before any successor addition, the plan now requires the locked current version to be in
`0..9223372036854775806`; it then computes the successor exactly once, validates
it in `1..9223372036854775807`, and reuses that validated value for allocation
and finalization. A maximum locked current version fails before calculation,
allocation, detached mutation, fact-ring mutation, story publication, or
commit, at only the existing sanitized failure boundary.

The original D1-D5 Live diagnostic is closed as failed/incomplete. It stopped
after historical D1 (Run A, suggested ordinal `0`) returned HTTP `200` and
normally committed revision `0 -> 1`, one new story segment, and three
suggestions. The official DeepSeek Dashboard delta and Provider-generation
count were both `1`; there was no authorized application replacement, transport
retry, or third generation. The exact newly committed public-fact count is
`UNKNOWN`, so D1 is incomplete, not passed, not reconstructable, and not
retroactively reinterpretable or repeatable within that procedure. D2-D5 were
never started, and the procedure may never resume at D2 or be rewritten as
successful.

The missing browser-visible committed fact-count evidence is confirmed. The
completed read-only analysis, with verdict
`DYNAMIC_NARRATIVE_D1_NEW_PUBLIC_FACTS_EVIDENCE_REMEDIATION_PLAN_COMPLETE`,
selected a privacy-safe bounded integer `public_fact_count` in the committed
Dynamic Narrative response's existing `feedback_parameters`. The React action
loop must retain that committed response across the authoritative View refresh
and render a Session- and revision-associated post-Action summary. It must not
reconstruct the count from the View, long-term-memory categories, prose,
Provider requests or proposals, fact-ring size, keys, or values.

The first independent review of the exact four-document authority-correction
candidate returned
`DYNAMIC_NARRATIVE_D1_EVIDENCE_AUTHORITY_CORRECTION_INDEPENDENT_REVIEW_CHANGES_REQUIRED`.
Its two blocking findings were the non-executable clean-baseline lifecycle and
the committed-scalar derivation timing. This bounded four-document correction
addresses only those findings. It is complete only as an unstaged documentation
candidate and has not yet received the required independent re-review or
approval.

The current complete worktree inventory remains exactly nine unstaged paths:

1. `PLANS.md`;
2. `docs/dynamic_narrative_provider_reliability_remediation_plan.md`;
3. `docs/public_client_contract.md`;
4. `docs/engineering/codex_workflow.md`;
5. `src/deviation_protocol/application/dynamic_narrative_models.py`;
6. `src/deviation_protocol/application/dynamic_narrative_orchestrator.py`;
7. `src/deviation_protocol/api/demo_composition.py`;
8. `tests/unit/test_dynamic_narrative.py`; and
9. `tests/unit/test_narrative_provider.py`.

The first four are the authority-document candidate. The last five are the
intentionally preserved existing runtime/test candidate. The post-correction
per-path hashes and complete nine-path diff size/hash are the proposed manifest
for the next independent re-review; they are not approved or locked merely by
this correction.

If and only if that re-review approves, the resulting exact nine-path dirty
state is locked as the authorized pre-implementation manifest under the narrow
manifest-locked dirty aggregate-candidate exception in the Codex workflow. It
is not a Git-clean baseline. The four documents are not separately staged,
committed, or pushed because that would leave the protected implementation
candidate dirty, while committing all nine paths would prematurely bypass the
remaining evidence and review gates. The ordinary published-clean-baseline rule
continues to apply outside this exact aggregate candidate.

The future implementation delta remains exactly four paths:

1. `src/deviation_protocol/application/dynamic_narrative_orchestrator.py`
   (application runtime);
2. `tests/unit/test_dynamic_narrative.py` (backend deterministic tests);
3. `web/src/App.tsx` (Web runtime); and
4. `web/src/App.action-loop.test.tsx` (Web deterministic tests).

That four-path list is a delta budget, not the complete candidate inventory.
The orchestrator and backend test are already dirty in the nine-path baseline
and may receive only the separately authorized implementation changes. The two
Web paths are currently clean and may become newly modified. After a successful
implementation, the complete aggregate worktree would ordinarily contain
exactly eleven unstaged paths: the original nine plus those two Web paths. The
four authority documents must remain exact at their approved hashes, as must
`dynamic_narrative_models.py`, `demo_composition.py`, and
`test_narrative_provider.py`; only the two already-dirty implementation paths
may change from the nine-path baseline, and no path outside the eleven-path
inventory may appear. The final eleven-path per-path hashes and complete-diff
size/hash must be recorded and verified.

The executable lifecycle is: four-document authority candidate; independent
read-only review; this bounded four-document correction; independent
new-session read-only re-review; if and only if approved, exact nine-path
manifest lock without separate document staging/commit/push; separately
authorized four-path implementation delta; deterministic local verification;
separately authorized E1-E5 Live diagnostic epoch; candidate freeze; formal
Gate; independent implementation review; complete aggregate staging; one
intentional aggregate commit; manual user push; and only then publication
confirmation or another separately authorized phase. Every later task must
verify the applicable manifest and stop on unexplained identity, path, hash, or
inventory drift. A manifest alone authorizes none of those later actions.

No implementation, deterministic verification, future Live diagnostic,
candidate freeze, formal Gate, implementation review, staging, commit, manual
push, publication, or later phase is complete or authorized by this correction.
The prior independent review was not approved. The unique current next task is:

> An independent new-session read-only re-review of the corrected four-document authority candidate against the two prior independent-review findings.

The separate experimental Dynamic Narrative Vertical Spike implementation was
published at `0eba2fd192b05c9455c73803a95a846c27307be9`; its automated
Live-smoke correction was published at
`e2678e6bba8497ed77bc5ba8c21b1ce8d001b2b9`. Its detailed canonical authority
remains the [DNVS plan](docs/dynamic_narrative_vertical_spike_plan.md). The
exact seven-path Manual Fake implementation was committed and published at
`d84a0528febb6c270494f35e2843e7e350fbd040`
(`feat(narrative): implement manual fake evidence mode`), closing its
implementation lifecycle.

The required Manual Fake browser walkthrough completed with
`DNVS_MANUAL_FAKE_BROWSER_EVIDENCE_EXECUTION_COMPLETE`: 8 submissions, 7
committed transitions, 1 intentional failure only at Fake ordinal 5, final
version 7, 8 consecutive Fake invocations, 1 reload, 0 retries, 0 ninth
submissions, 0 real Provider constructions/invocations, and 0 external Provider
HTTP requests. Item 5 retained version 4 and was never replayed; one reload
recovered it and items 6–8 completed successfully. The final continuity summary
was `The visible amber marker established earlier now identifies the route forward.`
The evidence task changed no repository file.
Automated Offline longevity evidence remains complete at exactly 510 turns,
510 Fake invocations, active state version 510, and 20 story slots. Automated
Live smoke evidence remains complete at one smoke execution, one real Provider
invocation, one Provider HTTP request, zero retries, and successful strict
schema validation. Optional Live browser evidence remains incomplete and
optional. At the historical prepublication checkpoint, the two-document
synchronization candidate awaited separate independent review and had no
staging or commit authorization. That synchronization and the seven-path
correction described below were subsequently completed, independently reviewed,
and published together at `eb1bb92b0c21639ad29fc9fdf1ffac537799e06b`.
The following prepublication candidate descriptions are retained only as
historical evidence, not as current work sequencing. The spike does not reopen
completed Phase 8 and is neither Phase 6 nor Phase 7.
P8-S6 and Phase 8 are
complete at the published aligned baseline
`7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`;
no P8-S7 exists. Phase 6 and Phase 7, the Structured Player Character programme,
and the overall project remain incomplete. Completing the spike would not
establish production Provider distribution. The completed automated Live smoke
does not constitute browser evidence or production Provider distribution.

DNVS remains closed as an evidence lifecycle and Phase 6 remains paused. The
first new-process/new-browser-Session Optional Live action exposed a genuine
below-minimum result and emitted the sanitized
`DNVS_LIVE_DIAG_PRE_LENGTH_BELOW_MINIMUM` token with HTTP 503 and no state
change. It
proved only a structurally parseable narrative shorter than the unchanged hard
350..900 Unicode-character range; the rejected text and exact length remain
unknown, and validation stopped before protected-reference scanning. The
resulting five-path candidate was then uncommitted and added the buffered
500..700 Unicode-character prompt target and at most one length-triggered
complete replacement generation. At that historical checkpoint, the next
new-process/new-browser-Session Action was
submitted once and returned HTTP 503
`NARRATIVE_PROVIDER_RESPONSE_INVALID` / `Narrative processing failed`, emitted
no `DNVS_LIVE_DIAG` token, was not repeated, and stopped before length and
protected-reference validation. Its raw content, parser subtype, schema defect,
narrative length/content, and hidden references all remain unknown; it proves
neither length recovery nor taxonomy correction. Manual evidence alone does not
prove Provider call count, atomicity, or parser subtype.

After response hardening, four actions were submitted across option choices and
free input, all under the same public Session ID `demo-session-00000001`. Each
ended with HTTP 503 and the final
`DNVS_LIVE_DIAG_PRE_LENGTH_BELOW_MINIMUM` token. In each case the final
structurally parsed candidate failed the then-existing 350-character minimum
before protected-reference validation; no transition succeeded, and changing
between option and free input did not avoid the result. The hard-350 policy was
therefore unusable in those attempts. Exact lengths, the initial failure class,
Provider-call count, raw content, and hidden references remain unknown; there
is no parser-failure claim for these four actions, and manual evidence does not
independently prove persistence atomicity. The protocol initially
authorized one action, but four were submitted. They were not replay and are
not described as four fresh processes.

The later repository-read-only real-Provider diagnostic exercised three fresh
production-backend actions through Live composition, ASGI character creation,
Run entry, current View, the first offered action, production submission, the
real DeepSeek adapter, strict parsing/schema validation, application
validation, terminal finalization, and replay. Action 1 stopped before an HTTP
response because of sandbox networking. Actions 2 and 3 reached DeepSeek and
returned HTTP 200 with strict, schema-valid preferred-band proposals of 372 and
379 Unicode characters. Both were rejected specifically in
`candidate.proposed_public_facts[0].key` at `PRE_INTERNAL_MARKER` /
`INTERNAL_IDENTIFIER_SHAPE` / `internal_id_prefix:fact`; the matched field was
not narrative prose. Neither key overlapped the protected-reference index, so
the evidence shows a prompt/schema/generated-public-key contract mismatch, not
disclosure of a real protected or authoritative identifier. It does not
establish the exact cause of unrecoverable historical Live failures. No
transition committed, and the diagnostic changed no repository file.

The then-uncommitted correction candidate preserved the protected-reference
source taxonomy and made `DynamicPromptBuilder` the sole hardened single-object
Prompt authority. The published implementation retains that design: it
distinguishes only sanitized unparseable-response and schema-invalid-response
categories at the real dynamic response boundary and
shares one application replacement allowance across those categories and
below-preferred and above-maximum outcomes. The Provider-visible preferred
output contract remains 350..900 inclusive with a 500..700 target and never
discloses the 120-character fallback. It defines the exact real-Provider
generated public-fact-key grammar
`^public-note-[a-z0-9]{2,6}(?:-[a-z0-9]{2,6}){0,3}$` and enforces that one
authority in both the prompt and the real DeepSeek proposal-schema boundary.
At that published v1 boundary, the deterministic Fake and persisted key
conventions remained compatible without a migration; that historical fact does
not remove the future Fake candidate-v2/keyless edit recorded above. A first
result below 350 or above 900 consumes the sole
complete-replacement allowance and never commits. Only a replacement in the
120..349 degraded band may become eligible, and it still traverses the complete
schema, semantic, marker/secret, protected-reference, player-isolation,
authority, provenance, stale-state, and transactional pipeline. A replacement
below the absolute 120 floor ends with the existing public HTTP 503 proposal
rejection and one final below-minimum token; anything above 900 ends with the
corresponding final above-maximum rejection and is never truncated or
committed. A preferred valid first result uses one application generation; an
eligible first failure uses at most two; every other first failure uses one; no
replacement failure causes a third. Degraded success has no public flag and no
diagnostic token. Invalid content and proposals are never persisted. Public
errors, Provider settings, transport retries, terminal replay, single-commit
atomicity, and non-Live behavior remain unchanged. The complete candidate scan
over all string mapping keys and string leaves is unchanged, with no
public-fact exemption or detector weakening. At that historical checkpoint, the
whole seven-path candidate remained uncommitted and had no successful
post-correction Live evidence. It was subsequently completed and published at
`eb1bb92b0c21639ad29fc9fdf1ffac537799e06b`; this publication did not create
post-correction gameplay Optional Live evidence.
The earlier generated-public-key correction checkpoint recorded focused pytest
`37 passed`, the complete affected-module pytest command `490 passed`, and
`git diff --check` passed; these overlapping historical counts are not a
unique-test total.

The later Provider-stability schema/contract correction addressed three runtime
findings without changing the preserved generation and commit bounds: sanitized
exception boundaries, ordinary finite JSON-float classification, and one named
submitted-action exclusion authority shared by contract rendering, prompt
construction, and runtime enforcement. Its first independent focused review
confirmed that all three runtime fixes were correct and returned changes
required only for two regression-evidence gaps: recursive malformed outer
response-envelope coverage through `DeepSeekNarrativeProvider.generate_dynamic`
and representative ordinary-float coverage at
`proposed_consequences[0]`, top-level `result`, and nested
`next_scene.summary`. A bounded single-test-file correction closed both gaps,
and the final independent focused review approved them with no blocking or
non-blocking finding and no residual evidence gap in scope.
The three runtime corrections and both test-evidence corrections are therefore
independently approved.

The five deterministic schema families and precedence, one-primary-plus-one-
replacement generation ceiling, zero Provider transport retries, no third
generation, complete validation/safety/authority/stale/provenance/transactional
finalization, duplicate suppression, commit atomicity, and absence of a
deterministic fallback all remain unchanged.

Historical final correction evidence recorded `4 passed` for the newly added
tests,
`17 passed` for the relevant correction selection, `427 passed` for the complete
authorized two-file suite, and canonical Offline verification at `2275 passed,
182 skipped`; compileall, pip check, Alembic heads/history, internal diff, and
`git diff --check` also passed. The final focused review separately recorded
`4 passed` for the two new test symbols, `16 passed` for directly relevant
preservation, and `git diff --check` passed. At that prepublication checkpoint,
the bounded two-document synchronization recorded the independently approved
implementation state and was complete as a documentation candidate awaiting one
fresh independent focused review. That historical review and publication were
subsequently completed at
`eb1bb92b0c21639ad29fc9fdf1ffac537799e06b`. Gameplay Optional Live remains
subject to separate authorization and `OPTIONAL_LIVE_INCOMPLETE`; it was not
performed by that documentation task. That historical synchronization did not
itself authorize Optional Live, staging, or commit.

## P4-S1 completion baseline

- Exact completed boundary: [P4-S1 implementation plan](docs/structured_player_character_p4_s1_implementation_plan.md).
- Branch: `main`
- P4-S1b implementation commit:
  `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`
- Baseline subject: `feat(player-character): implement P4-S1b run binding`
- Historical pre-closure Phase 3 baseline:
  `150074d58cdbf3aee08bea9c1084325b2b0f0a3f`
  (`docs(player-character): close phase 3 slice 1 status sync`)
- Historical structured player-character Phase 2 closure baseline:
  `ac5263fd5ca652665d23a082a19b3d66f8a047d1`
  (`feat(player-character): wire repositories into unit of work`)
- Structured player-character Phase 2 is independently accepted, committed,
  pushed, and closed at that historical baseline.
- P3-S1 canonical creation orchestration completed its bounded correction and
  final independent implementation review with
  `APPROVED_STRUCTURED_PLAYER_CHARACTER_PHASE_3_SLICE_1_IMPLEMENTATION`.
  The approved nine-path candidate was committed as
  `7606e51523338247ea33ed9329346fdba046d29b`
  (`feat(player-character): add race-safe creation recovery`) and pushed to
  `main`. Its three-document closure status synchronization was subsequently
  committed and pushed as the then-current baseline
  `150074d58cdbf3aee08bea9c1084325b2b0f0a3f`
  (`docs(player-character): close phase 3 slice 1 status sync`). P3-S1 is
  implemented, independently approved, committed, pushed, complete, and
  closed.
- Structured player-character Phase 3 is implemented and complete. P3-S1
  through P3-S4 are complete, and the complete Phase 3 code candidate received
  independent read-only approval with no implementation finding remaining
  open. The milestone is committed and pushed at
  `cafb12272e703e8751c78bb6852cec90d7d7ec8d`. Complete Phase 3 Offline
  verification recorded `1,469 passed, 79 skipped`; the existing focused
  MySQL player-character selection recorded `42 passed`.
- Minimum Run Core is the historical prerequisite implemented at
  `e821cd922b61868097667b12c2b64cf8089a9681` (`feat(run): implement minimum
  run core`). P4-S1a is implemented at
  `748003319ececa548b68b351746afbb2d54c66bb`
  (`feat(player-character): guard active binding lifecycle transitions`), and
  P4-S1b is implemented and pushed at
  `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`
  (`feat(player-character): implement P4-S1b run binding`). The functional
  P4-S1 boundary is complete: binding is internal-only, the constructible Run
  lifecycle remains `pre_first_turn`, and the reserved public
  `RunService.bind_player_character(...)` command remains rejected.
- Except for completed P4-S1, Phase 4 work remains unimplemented or deferred.
  No repository authority defines a P4-S2 objective. P4-S1 itself activated no
  API route, frontend, Demo, Provider, narrative, scenario, combat, or public
  gameplay behavior; subsequent Phase 5 and Phase 8 work is tracked below.
- P5-S1 owned-read API activation is completed and published at
  `5955c47eac07429107b93ef85da6a055bd2044ef`
  (`feat(player-character): activate owned-read API`).
- The P5-S2 creation/replay public contract is frozen and published at
  `245caff3903666fcd2dd9a318785f323117deb24`
  (`docs(player-character): define P5-S2 public contract`). Its bounded normal
  `POST /v1/player-characters` implementation was independently approved,
  committed, and published at
  `4ba66d8f277988325795c905fdf6fd9e416d7457`
  (`feat(player-character): add creation API`).
- [P5-S3](docs/structured_player_character_p5_s3_implementation_plan.md) has
  received `STRUCTURED_PLAYER_CHARACTER_P5_S3_PLAN_APPROVED`. Its first
  independently reviewed local implementation candidate received
  `CHANGES_REQUIRED`. A first corrected candidate and the later re-corrected
  candidate each received a further fresh `CHANGES_REQUIRED` review. The third
  review found no production-code defect but requested stronger SQL-race,
  durable-state, complete unit/OpenAPI, and documentation-history evidence. A
  subsequent evidence candidate supplied a MySQL 1062 only by rolling back the
  original mutation transaction and resuming its stale in-memory operation. A
  focused reachability investigation returned
  `P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`: the
  current production service instead serializes legitimate retirement writers
  at the Player Character `FOR UPDATE` lock before receipt lookup or mutation.
  The accepted and published P5-S3 result uses normal concurrent HTTP requests
  to prove exact replay or ordinary
  idempotency conflict after one durable mutation, and treats the existing
  receipt-add recovery only as bounded fault-injection/out-of-topology defense.
  Its correction validation completed locally: canonical Offline reported
  1,814 passed/124 expected skips, MySQL 136 passed, and Full 1,937 passed/one
  opt-in Provider skip. Its focused final independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED`, finding no
  material scoped defect. The accepted real-MySQL evidence proves aggregate-lock
  serialization, exact replay or ordinary idempotency conflict, and one durable
  mutation; fault injection remains bounded defensive recovery evidence, and the
  unreachable receipt-add race is not a requirement. P5-S3 was committed and
  published as `34d063e387cde69500e4dc018ff087e87f3eee74`
  (`feat(player-character): add idempotent retirement endpoint`). P5-S3 is not
  a current unstaged candidate, and no P5-S3 review remains pending. Phase 5
  ended with P5-S3; no P5-S4 exists or has begun. Phase 8 planning does not
  reopen Phase 5. Deployment, release, broader runtime activation, and Provider
  work remain deferred.
- Codex does not push; the user performs every push manually.
- Phase 3.2b historical implementation baseline:
  `a0fbc7a749d9774785aa78ffe2b48b4dcf9e3dce`
- Latest completed subphase: **Phase 3.2b**
- Phase 3.2a authoritative commit:
  `f1fd5e2cd07d342e852430e9352f64b84014c88e`
- Phase 3.2b: **implemented, verified, accepted, and closed**
- Phase 3.2 as a whole: **implemented and complete**

## Phase status

| Phase | Status | Canonical detail |
| --- | --- | --- |
| Phase 1 | Implemented and complete | [Architecture](docs/architecture.md) |
| Phase 2.1 | Implemented and complete | [Architecture](docs/architecture.md) |
| Phase 2.2 | Implemented and complete | [Narrative Provider](docs/narrative_provider.md) |
| Phase 2.3 | Implemented and complete | [Player memory](docs/player_memory.md) |
| Phase 2.4 | Implemented and complete | [Playable vertical slice](docs/playable_vertical_slice.md) |
| Phase 3.0 | Implemented and complete | [Public client contract](docs/public_client_contract.md) |
| Phase 3.1a | Implemented and complete | [Architecture](docs/architecture.md) |
| Phase 3.1b | Implemented and complete | [Public client contract](docs/public_client_contract.md) |
| Phase 3.1c | Implemented and complete | [Canonical same-tab recovery contract](docs/architecture.md#phase-31c-web-same-tab-recovery-contract) |
| Phase 3.2a | **Implemented, verified, committed, and closed** | [Phase 3.2 specification and evidence](docs/phase_3_2_deterministic_demo_environment.md) |
| Phase 3.2b | **Implemented, verified, accepted, and closed** | [Phase 3.2 specification and evidence](docs/phase_3_2_deterministic_demo_environment.md) |
| Phase 3.3 | **Approved product design — not implemented** | [Run Protocol, difficulty, and world profiles](docs/run_protocol.md) |
| Phase 3.4 | **Approved product design — not implemented** | [NPC Relationship and Temporary Residence](docs/npc_relationship_residence.md) |
| Phase 4.0 | **Accepted architectural direction — not implemented** | [ADR 0001: Production Provider Distribution](docs/decisions/0001-production-provider-distribution.md) |
| Structured Player Character Phase 5 | **Implemented and complete at P5-S3** | [Downstream implementation plan](docs/structured_player_character_implementation_plan.md) |
| Structured Player Character Phase 6 | **Planned phase — not implemented** | Subject-reference compatibility hooks in the [downstream implementation plan](docs/structured_player_character_implementation_plan.md#phase-6--subject-reference-compatibility-hooks) |
| Structured Player Character Phase 7 | **Planned phase — not implemented** | Regression, documentation, and closeout in the [downstream implementation plan](docs/structured_player_character_implementation_plan.md#phase-7--regression-documentation-and-closeout) |
| Phase 8 | **Implemented and complete at published P8-S6 closure baseline `7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`; no P8-S7 exists** | [Structured Player Character Run Entry and Minimum Playable Loop](docs/structured_player_character_run_playable_loop_plan.md) |

## Implemented baseline through Phase 3.2b

The implemented engine and public application boundary include:

- deterministic domain rules, trusted authority policies, transactional
  persistence, idempotent action handling, and authoritative scenario state;
- the supplier-neutral application `NarrativeProvider` interface and normally
  configured DeepSeek infrastructure adapter;
- a public scenario/session/action/View contract whose controls come only from
  the latest authoritative `action_affordances`;
- the complete public `death_certificate` vertical-slice paths and bounded
  player-memory projection;
- the React/Vite action loop with same-tab recovery for a Session and
  server-confirmed pending requests, without action replay, as defined by the
  [canonical Phase 3.1c recovery
  contract](docs/architecture.md#phase-31c-web-same-tab-recovery-contract); and
- the isolated Phase 3.2a Demo backend runtime: deterministic Provider,
  process-local transactional persistence, independent composition root,
  deterministic IDs/seeds/logical clock, exact two-process replay evidence, and
  external-I/O denial evidence; and
- the Phase 3.2b local Web layer: Demo-only Vite
  dotenv isolation, conditional local/temporary/non-production presentation,
  exact 19-action React/MSW regression, same-tab Demo recovery regressions,
  one-command launcher, direct production-Zod catalog validator, and bounded
  startup/proxy/sentinel/build smoke.

`death_certificate_v1` is the canonical current Demo and vertical-slice
scenario. This is not a permanent product decision that it must be the first
world in the production game.

## Phase 3.2: Deterministic Demo Environment

### Phase 3.2a — Deterministic Demo Environment

Status: **Implemented, verified, committed, and closed.**

Authoritative commit:
`f1fd5e2cd07d342e852430e9352f64b84014c88e`.

The closed subphase provides the isolated Demo backend runtime. It does not
provide the Phase 3.2b Web launch/walkthrough layer, production deployment,
commercial Provider routing, billing, Run Protocol, difficulty/world profiles,
or NPC residence.

Implementation and evidence are recorded in
[the historical Phase 3.2 specification](docs/phase_3_2_deterministic_demo_environment.md).

### Phase 3.2b — Demo Web and Full Playable Walkthrough

Status: **Implemented, verified, accepted, and closed.**

The implementation provides:

- Demo Web/Vite mode and dotenv isolation;
- one PowerShell launcher for the local Demo;
- an unmistakable local-only, temporary, non-production label;
- the full Web-loop regression through the canonical complete path;
- bounded startup/proxy/sentinel/schema/build validation; and
- preserved same-tab recovery with safe missing-Session invalidation after a
  backend restart.

The supported local commands are:

```powershell
pwsh -NoProfile -File .\scripts\start-demo.ps1
pwsh -NoProfile -File .\scripts\smoke-demo.ps1
```

The launcher binds both children to loopback and uses the isolated Demo
composition. Demo state is process-local and temporary. The bounded smoke
creates only owned temporary build/response data plus a create-new dotenv
sentinel, validates the proxied scenario catalog through the production Web
schema, executes the exact-warning React presentation probe with the effective
mode copied from the launched Web child, and cleans its owned resources.

The 2026-07-23 correction round passed the Offline verifier, all Web commands,
the exact cross-process replay, the focused executable PowerShell lifecycle
suite, and the corrected bounded smoke. The subsequent controlled manual
acceptance passed the canonical 19-action browser walkthrough to version 19 and
`ENDED`, same-tab recovery after backend restart, Ctrl+C launcher shutdown, and
final owned-process and port cleanup.

Phase 3.2b reuses the Phase 3.2a backend and existing public client contract.
It does not own Run Protocol, difficulty/world profiles, relationship or
residence systems, production commercial routing, quotas, or billing.

Phase 3.2b and Phase 3.2 are complete. This deterministic local Demo acceptance
does not establish production readiness or implement later final-product work.

## Cross-phase final narrative experience design

Status: **Approved and frozen canonical cross-phase product specification —
not implemented; third independent read-only review passed.**

The canonical product-level authority for the reading-first final experience,
persistent player character, NPC importance and golden long-term memory,
multi-genre and cross-scenario continuity, generalized narrative conflict, and
their model/server authority boundary is
[Final Narrative Experience and Long-Term Systems](docs/final_narrative_experience.md).
It preserves the deterministic Demo as a validation fixture and records a
bounded future implementation sequence without assigning implementation status
to any deferred system.

The approved final narrative experience specification remains frozen and not
implemented. Phase 3.2b remains closed.

The
[structured player-character contract](docs/structured_player_character_contract.md)
is an **approved and frozen structured player-character product specification —
partially implemented by the committed and pushed Phase 1 pure domain/protocol
foundation, Phase 2 Slice 1 persistence carriers, Phase 2 Slice 2 structured
persistence schema, the independently approved Phase 2 Slice 3 MySQL
Repository adapters, and the independently approved Slice 4 Unit of Work
wiring and atomicity evidence. The overall implementation plan remains only
partially implemented.** Its
first independent read-only review found one HIGH issue
concerning stable same-story-line identity continuity, one MEDIUM issue
concerning permanent `player_character_id` non-reuse, and one MEDIUM issue
concerning `controller_binding` lifecycle presence. The first controlled
correction addressed those three issues locally. The first independent
re-review confirmed that all three original findings were closed but found one
new MEDIUM omission concerning silent applicable-version switching at scenario
and Run-authorized later-world boundaries. The second controlled correction
addressed that omission locally without selecting pinned, floating,
checkpointed, or other revision-following behavior.

The second fresh independent read-only review confirmed that all four
historical findings were closed, found no new HIGH, MEDIUM, or LOW issue
requiring correction, and returned
`APPROVED_STRUCTURED_PLAYER_CHARACTER_CONTRACT`. This separate controlled
documentation closeout then recorded the earned approval and frozen status and
created the local documentation commit. It was not an independent review,
changed no runtime, database, migration, Provider, public-client, API, or other
implementation behavior, made no additional product decision, and did not
push. Approval and freeze do not authorize runtime work. Implementation
requires a separately approved downstream implementation plan and task.

The
[structured player-character downstream implementation plan](docs/structured_player_character_implementation_plan.md)
translates that approved and frozen product contract into proposed
repository-specific implementation work. The plan, technical prerequisites,
and ordered Phase 2 slice amendment are **approved, frozen, committed, and
pushed**; the ordering amendment baseline is
`afa9f9c21900eebd4e08d65071a26903e83d4a65`
(`docs(domain): freeze structured player character phase 2 plan`). Phase 1 has
passed fresh independent read-only acceptance for the exact nine-path candidate.
Its original implementation commit is
`c8808f66e8d97bc4386a481bf21669cfddcd222e`; the current completed and pushed
Phase 1 implementation baseline is
`4acb8b993f15a1fdee20edc3140324730447fc9f`
(`fix(domain): preserve exact opaque identifiers`). The complete plan remains
partially implemented. The Phase 2 product scope and technical prerequisites
historically received the independent verdict
`STRUCTURED_PLAYER_CHARACTER_PHASE_2_TECHNICAL_FREEZE_APPROVED`; the exact
then-approved candidate was committed and pushed unchanged as
`1fd29798fe256593e56029baca743484cc221ae4`
(`docs(domain): freeze structured player-character phase 2 prerequisites`).
That commit remains the technical-freeze history; the later ordering-amendment
baseline governs the current numbered implementation slices.

Phase 2 Slice 1 is implemented, independently accepted, committed, and pushed
at `3ad39c7bb7a2c7cc6b2571f6dcb69685b7234101`
(`feat(player-character): add persistence carrier validation`). Phase 2 Slice 2
is implemented and verified, received independent review with no remaining
substantive issue, was committed as
`a2802799b3d3a5497f4fc097b0cc05d573d8e0ca`
(`feat(player-character): add structured persistence schema`), and was pushed
to `origin/main`. Its seven-path approved surface adds exactly six SQLAlchemy
mappings and migration `20260728_0004` after `20260719_0003`, with exact MySQL
collations, keys, named checks, twelve restrictive foreign keys, complete index
inventory, no backfill, and fail-closed data-present downgrade refusal. The
completed schema includes the corrected
`ck_spc_revisions_provenance_matrix`, with explicit non-NULL `prior_revision`
requirements for both `RETIRE` and `FINAL_DEATH`. Relevant real-MySQL
verification passed with 64 tests, and the relevant Slice 1 regression passed
with 284 tests.

Phase 2 Slice 3 is implemented and independently approved. It provides the
four existing-port MySQL Repository adapters over caller-owned sessions,
including allocation and controller-binding storage, current and immutable
revision persistence, creation and mutation receipts, exact-row locking, and
current-row CAS. Reconstruction uses the committed Slice 1 codec and canonical
identity authorities; adapters flush authorized SQL but do not commit, roll
back, retry, recover transactions, or orchestrate application workflow. Its
two narrow infrastructure errors classify repository operation and known
immutable/unique conflicts. Real-MySQL and offline evidence covers
persistence, conflicts, concurrency/CAS, row locking, caller rollback,
constraints, corrupt state, and persistence boundaries.

Phase 2 Slice 4 is implemented and verified locally and received new-session
independent implementation approval with verdict
`PHASE_2_SLICE_4_IMPLEMENTATION_INDEPENDENTLY_APPROVED`; no blocking findings
remained. Production changes are limited to the four existing
Repository-adapter imports and their same-`AsyncSession` construction in
`SqlAlchemyUnitOfWork.__aenter__`.
Slice-specific unit and real-MySQL evidence is limited to
`tests/unit/test_repository_and_uow.py` and
`tests/integration/test_mysql_player_character.py`. It proves same-session
Repository wiring, lazy autobegin preservation, explicit UoW commit ownership,
normal, exceptional, and cancellation rollback, atomic creation and replay,
controlled pre-COMMIT failure rollback, a genuine uniqueness race with loser
rollback and fresh-UoW winner recovery, atomic mutation and replay after a
later revision, and mutation rollback across history, current row, and receipt.
Failed sessions are not reused, no automatic retry was added, and
uncertain-COMMIT recovery and exactly-once behavior remain excluded.

This session passed: focused UoW unit `16 passed`; focused structured-character
MySQL `34 passed`; MySQL verifier `81 passed`; Offline verifier `1,389 passed,
71 skipped`; and Full verifier `1,459 passed, 1 skipped`. `compileall`,
Alembic heads/history, dependency checks, and `git diff --check` also passed.
The initial sandboxed Full run completed the tests but could not clean pytest's
user temporary directory; the exact permitted rerun outside that sandbox
passed. Phase 2 is independently accepted, committed, pushed, and closed at
`ac5263fd5ca652665d23a082a19b3d66f8a047d1`
(`feat(player-character): wire repositories into unit of work`). No API,
public route, frontend, Demo, Provider, Run, narrative, content, or gameplay
integration was activated.

The structured player-character roadmap preserves the repository-authoritative
stages:

1. **Phase 3 — Trusted canonical application service: complete and pushed**
   - P3-S1 through P3-S4 are closed at the current accepted baseline.
2. **P4-G0 — Minimum Run-core authority freeze: approved and closed**
   - the independent read-only review returned
     `STRUCTURED_PLAYER_CHARACTER_P4_G0_REVIEW_APPROVED`; the resulting
     prerequisite is now implemented and pushed at
     `e821cd922b61868097667b12c2b64cf8089a9681`.
3. **Minimum Phase 3.3 Run-core prerequisite: historically completed**
   - completed at `e821cd922b61868097667b12c2b64cf8089a9681`
      (`feat(run): implement minimum run core`); its all-null seam was the
      historical pre-P4-S1 baseline.
4. **P4-S1 — Run-owned continuous-story-line binding: complete**
   - P4-S1a is `748003319ececa548b68b351746afbb2d54c66bb`; P4-S1b is
     `8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`. No concrete defect requires
     reopening P4-S1.
5. **Phase 5 — Public projection and narrow boundary integration: complete at P5-S3**
   - P5-S1 owned-read activation is completed and published at
     `5955c47eac07429107b93ef85da6a055bd2044ef`; it exposes only the approved
     owned single-resource read and does not complete Phase 5;
   - P5-S2's public creation/replay contract is frozen and published at
     `245caff3903666fcd2dd9a318785f323117deb24`; its bounded normal POST was
     independently approved, committed, and published at
     `4ba66d8f277988325795c905fdf6fd9e416d7457`; and
   - P5-S3's first, first-corrected, and re-corrected local retirement
     candidates each received `CHANGES_REQUIRED`. The later evidence candidate's
     receipt-add 1062 depended on a mid-operation rollback-and-resume topology.
     The focused reachability verdict
     `P5_S3_RECEIPT_ADD_RACE_NOT_REACHABLE_UNDER_CURRENT_PRODUCTION_PATH`
     corrected the present acceptance boundary to normal HTTP serialization at
     the aggregate lock plus explicitly labelled bounded fault injection. The
     exact eleven-path correction passed local validation (Offline 1,814/124,
      MySQL 136, Full 1,937/one live-test skip); its focused final independent
      review returned `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED`
      with no material scoped defect. It accepted real-MySQL aggregate-lock
      serialization, replay/conflict, and one durable mutation, and fault
      injection only as bounded defensive recovery; the unreachable receipt-add
      race is not a requirement. P5-S3 was committed and published as
      `34d063e387cde69500e4dc018ff087e87f3eee74`. No review remains pending;
      Phase 5 ended with P5-S3 and no P5-S4 exists.
6. **Phase 6 — Subject-reference compatibility hooks: allocated, not implemented**
   - its existing scope and prerequisites remain unchanged and are not imported
     into Phase 8.
7. **Phase 7 — Regression, documentation, and closeout: allocated, not implemented**
   - its existing scope remains unchanged and is not marked complete by current
     priority ordering.
8. **Phase 8 — Structured Player Character Run Entry and Minimum Playable Loop: implemented and complete**
   - explicit user allocation and the approved planning authority selected the
     minimum create-or-reuse, eligible character discovery, authoritative Run
     entry/binding, existing gameplay, deterministic Demo, and minimal Web
     backbone described in the
     [dedicated Phase 8 plan](docs/structured_player_character_run_playable_loop_plan.md).
   - P8-G0 is complete and published, and P8-S1 eligible-character discovery is
     complete and published. P8-S2 atomic internal Run entry is implemented,
     accepted,
     committed, and published at
     `70815b181624e5475d2d978bef0db1ed3b22324e`; its implementation and F1/F2/F3
     evidence are closed and are not reopened. The dedicated
     [P8-S3 implementation plan](docs/structured_player_character_p8_s3_implementation_plan.md)
     was independently approved and committed/published at
     `e17172ad0a9febe4ec9e3a96e7be8204c9722d29`. Its exact implementation
     candidate's five bounded implementation-review corrections are complete.
     A subsequent independent read-only re-review found only one remaining
     Medium documentation-synchronization issue and formally returned
     `CHANGES_REQUIRED`. The complete 15-path candidate then received focused
     independent read-only approval and was committed and published at
     `ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`
     (`feat(run): add P8-S3 playable-loop adapter`) with exactly three
     production, five test, and seven documentation paths. P8-S3 is complete.
     The dedicated
     [P8-S4 implementation plan](docs/structured_player_character_p8_s4_implementation_plan.md)
     was independently approved and published at
     `375a2a7ae018c9c9c79272e5de7da703818d1f20`. The implementation then
     received
     `STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
     was committed as `187d41ba3035c8d717c2fb2578a805402255d979`
     (`feat(player-character): complete P8-S4 demo persistence`), and was
     manually published by the user. P8-S4 deterministic Demo
     persistence/composition parity is complete. The dedicated
     [P8-S5 implementation plan](docs/structured_player_character_p8_s5_implementation_plan.md)
     was independently approved and published at
     `dceecaf0d7a33ccde07f519f83997489acd5fc86`, remained frozen during
     implementation, and its corrected implementation received
     `STRUCTURED_PLAYER_CHARACTER_P8_S5_CORRECTED_IMPLEMENTATION_REVIEW_APPROVED`.
     The exact eight-path Web implementation was committed and published at
     `2ce56a757beed8a3989d38453da3b6d80342ca05`
     (`feat(web): connect player characters to playable run flow`). P8-S5 is
     complete. The frozen P8-S6 implementation plan was approved and published
     at `4edf2e3341e60632765b85796e8554797c645692`. Fresh P8-S6 executable
     evidence E01-E14 and commands C01-C21 passed without a production, test,
     fixture, migration, dependency, configuration, deployment, generated-file,
     or public-contract change. The exact P8-S6 closure documentation received
     independent approval, was committed and manually published as
     `7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`
     (`docs(player-character): close P8-S6 evidence`), and was confirmed at the
     aligned `HEAD`, local `main`, and local `origin/main` baseline with
     ahead/behind `0/0`. P8-S6 and Phase 8 are complete; no P8-S7 exists. Phase
     8 neither implements nor completes Phase 6 or Phase 7. Phase 6, Phase 7,
     the Structured Player Character programme, and the overall project remain
     incomplete.

P3-S1 canonical creation orchestration is implemented, independently approved,
committed, pushed, complete, and closed at
`7606e51523338247ea33ed9329346fdba046d29b`
(`feat(player-character): add race-safe creation recovery`). Its bounded
correction resolved the earlier recovery-provenance defect: the same
controller-binding add exception instance must escape the failed initial Unit
of Work and be confirmed by the outer handler, while suppression fails closed
with the preserved original instance. The earlier typed-conflict ownership
contradiction and rejected amendment design remain historical: the shared
`PlayerCharacterRepositoryConflictError` cannot satisfy a
controller-binding-only application contract because it is used by unrelated
Repository paths.

The revised documentation-only authority amendment was independently approved,
committed, and pushed at
`c6d0220a2442887e89717b5b6facb14af4604236`. It adds the
narrow application-owned
`application.ports.ControllerBindingUniquenessConflictError` contract and the
binding-specific infrastructure
`infrastructure.errors.PlayerCharacterControllerBindingConflictError`.
The new concrete exception remains compatible with
`PlayerCharacterRepositoryConflictError`, while the shared error itself
remains outside the narrow contract. Only the MySQL duplicate-key translation
at the exact `ControllerBindingRegistryRepository.add` row flush may select the
new subtype, and `PlayerCharacterService` may catch only the application-owned
contract immediately around that exact call.

The completed P3-S1 implementation stayed within the exact
`4 + 2 + 3` budget: production may
change only `src/deviation_protocol/application/player_character_service.py`,
`src/deviation_protocol/application/ports.py`,
`src/deviation_protocol/infrastructure/errors.py`, and
`src/deviation_protocol/infrastructure/repositories.py`; tests may change only
`tests/unit/test_player_character_service.py` and
`tests/integration/test_mysql_player_character_service.py`; documentation
synchronization may change only `PLANS.md`, `docs/architecture.md`, and
`docs/structured_player_character_implementation_plan.md`. The committed
amendment changed documentation only and did not itself authorize
implementation. The later separately authorized implementation and bounded
correction completed final independent review, commit, and push. P3-S1 is
closed. At that historical point Phase 3 remained incomplete and P3-S2 had not
started.

The subsequent P3-S1 status synchronization was committed and pushed at the
pre-closure baseline `150074d58cdbf3aee08bea9c1084325b2b0f0a3f`
(`docs(player-character): close phase 3 slice 1 status sync`). The complete
Phase 3 milestone then added P3-S2 mutation orchestration, P3-S3 owned read and
detached projection, and P3-S4 normal production composition. It received
independent read-only approval with no open implementation finding and was
committed and pushed at
`cafb12272e703e8751c78bb6852cec90d7d7ec8d`. Phase 3 is complete. Phase 4
has started only through completed P4-S1: P4-S1a is complete at
`748003319ececa548b68b351746afbb2d54c66bb`, and P4-S1b is complete at
`8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`. P4-G0 documentation authority is
approved and closed. The implemented P4-S1 boundary is the internal Run-owned
continuous-story-line binding only; broader Phase 4 and the full Run Protocol
remain incomplete. The P4-S1 constructible baseline stopped at `pre_first_turn`;
the narrow P8-S2 Session-backed playable-loop entry now persists the revision-3
transition to `active`, while the broader Phase 4 lifecycle and full Run Protocol
Phase 3.3 remain incomplete.

Production controller authority is an explicit configured allowlist matched by
the complete exact `(authentication_scheme, player_id)` `RequestPrincipal`
identity. It returns only the configured `controller_id`; unknown or invalid
principals receive no authority. Configuration is immutable or defensively
copied, strict, duplicate-safe, and value-free in errors. Resolution performs
no database or UnitOfWork work and never auto-registers, falls back to a
development principal, partially matches, or derives ownership.
`PLAYER_CHARACTER_CONTROLLER_BINDINGS` supplies the required runtime JSON when
typed bindings are not provided directly. Missing, empty, malformed,
incomplete, non-canonical, duplicate-principal, or shared-controller
configuration fails closed before catalog, engine, database, or UnitOfWork
construction.

Production character-ID issuance directly uses standard-library
`uuid.uuid4()`, whose entropy comes from operating-system randomness. It emits
`pc.<32 lowercase UUIDv4 hexadecimal digits>` and validates the result through
`PlayerCharacterId`. The ID contains no principal, controller, timestamp,
sequence, or other user information, and production exposes no injection seam
that can replace UUIDv4 generation. Persistence uniqueness failures continue
to fail closed; no generalized creation retry was added.

Creation resolves trusted controller authority before constructing a
UnitOfWork; ownership is never caller supplied. Allocation, initial revision
and current state, and the creation receipt commit atomically, collisions and
persistence failures fail closed, and success is returned only after commit.
Mutation checks ownership before targeted receipt disclosure, evaluates a
receipt before stale-revision rejection, returns compatible replay read-only,
and conflicts safely on incompatible operation-ID reuse. A new operation
applies exactly one policy and validates successor, history, CAS, and receipt
persistence; CAS loss and failures roll back. Only the exact receipt-flush
conflict permits the narrow disposed-then-fresh-UnitOfWork recovery, with no
mutation or commit retry.

Owned read resolves authority before UnitOfWork construction. Missing and
wrong-owner characters both return `None`; stored identity and state are
revalidated, and the detached frozen allowlisted projection returns only ID,
contract version, current revision, and lifecycle. It performs no write, lock,
receipt operation, commit, retry, or recovery.

`build_default_services()` exposes the canonical service through
`ApiServices.player_character_service`, reusing the lazy
`SqlAlchemyUnitOfWork` factory and existing repositories and policies. Create,
mutate, and `get_owned` remain available, while composition itself performs no
UnitOfWork, SQL, ID issuance, or mutation. Supported startup fails closed when
required controller bindings are absent; no fake or development resolver or
fake issuer is installed.

P5-S1's owned GET, P5-S2's creation/replay route, and P5-S3's retirement route
are published. Controller
identity remains server-derived, and operation identity, durable replay,
allocation, receipts, ownership, and bounded race recovery remain in the
existing service and persistence authorities. At the Phase 5 baseline, Demo
supplies no Player Character service and exposes no Player Character route or
OpenAPI path; no frontend method calls the creation POST. P5-S3 adds only the
normal-application retirement route; its focused final independent review returned
  `STRUCTURED_PLAYER_CHARACTER_P5_S3_FOCUSED_FINAL_REVIEW_APPROVED` with no
  material scoped defect, accepting the real-MySQL serialization/replay-conflict/
  one-durable-mutation evidence and fault injection only as bounded defensive
  recovery. It was committed and published at
  `34d063e387cde69500e4dc018ff087e87f3eee74`; Phase 5 is complete at P5-S3,
  no P5-S4 exists, and P5-S3 remains closed. Frontend activation, Demo behavior,
  Provider behavior, broader Run Protocol and
lifecycle integration, narrative integration, scenario and world integration,
combat integration, content integration, public binding, and player-visible
gameplay activation remain deferred. The internal Run-owned continuous-story-
line binding is implemented only through P4-S1. DB-001, schema, migrations,
dependencies, persistence behavior, and transaction behavior remain unchanged.

The implementation-order amendment below was reviewed, approved, committed,
and pushed at `afa9f9c21900eebd4e08d65071a26903e83d4a65`, distinct from the
earlier frozen technical prerequisites. The following ordered conditions
controlled its activation:

1. A fresh independent read-only review returns
   `STRUCTURED_PLAYER_CHARACTER_PHASE_2_PLAN_APPROVED` for the exact complete
   four-document candidate and its four SHA-256 hashes.
2. Separate authorization is obtained to stage and commit exactly those four
   approved documents, and the staged and committed bytes retain the approved
   hashes.
3. The documentation-only commit is pushed through the repository's
   established authorized push workflow.
4. After the push, a new clean baseline is confirmed: `main` is checked out,
   `HEAD` equals local `origin/main`, ahead/behind is `0/0` without an
   unnecessary fetch unless separately authorized, the worktree and index are
   clean, no staged or normal untracked path remains, and the pushed commit
   contains exactly the approved documentation scope.
5. A separately authorized Phase 2 implementation task may then begin.

Those conditions were satisfied before Slice 1 began. Their satisfaction did
not authorize any implementation slice by itself: Slices 1 and 2 each received
separate scoped authorization, and every later slice still requires its own
accepted predecessor and authorization. No approval described here authorizes
staging, commit, push, database access, or implementation outside its exact
task.

Subject to that gate and later slice-specific authorization, the deterministic
Phase 2 order is:

1. **Slice 1 — Offline persistence contracts and canonical stored-record
   codec.**
2. **Slice 2 — Exact six-family SQLAlchemy metadata and linear Alembic
   migration.**
3. **Slice 3 — MySQL repositories, locking, CAS, and strict reconstruction.**
4. **Slice 4 — SQLAlchemy Unit of Work wiring and atomic Phase 2 integration
   proof.**

The detailed scope, paths, dependencies, exclusions, verification level, and
completion criteria for every slice are authoritative in the implementation
plan. Its existing receipt/history integrity design requires internally derived
canonical state-record fingerprints that bind each receipt to its exact
authoritative revision record(s). Slice 2 now provides the physical database
receipt schema, but no canonical character repository, public/runtime route,
Provider integration, frontend flow, or Run/story-line activation exists.
Phase 1 acceptance and the historical Phase 2 technical-freeze approval do not
themselves authorize later implementation. Phase 3.2b remains closed.

## Phase 3.3: Run Protocol and Difficulty/World Profiles

Status: **Approved product design — not implemented.**

Phase 3.3 owns the engine/world parameters, pre-game profiles and permitted
overrides, versioned frozen Run Protocol, deterministic resolution, and the
separation between objective difficulty, character definition, narrative
presentation, and relationship atmosphere. It also owns the approved,
not-implemented rule that a player chooses an entry world only from a small
authored eligible set, freezes its ID/version at run start, and the engine
selects later worlds deterministically from the eligible pool. Exact catalogues,
weighting, anti-repeat, progression, and priority-injection rules remain
Deferred. An important authored world may remain eligible for a meaningful,
engine-selected revisit that preserves confirmed world/NPC state and
consequences. Players cannot choose, request, approve, veto, or otherwise
authorize it; the complete revisit decision remains engine-owned. Detailed
revisit, region-unlock, anti-farming, recovery-priority, and world-line rules
remain Deferred.

The canonical design is
[Run Protocol, Difficulty, and World Profiles](docs/run_protocol.md).

P4-G0 documentation authority was approved and closed following independent
read-only review with `STRUCTURED_PLAYER_CHARACTER_P4_G0_REVIEW_APPROVED`. It
defined the smaller minimum Run-core prerequisite in
[Minimum Run Core Implementation Plan](docs/minimum_run_core_implementation_plan.md):
stable Run/line identity, minimum lifecycle and state version, durable
Run-owned persistence/UoW, separate trusted Session participation, and the
future atomic character-binding seam. The prerequisite is now implemented,
independently finally approved, committed, and pushed as
`e821cd922b61868097667b12c2b64cf8089a9681`
  (`feat(run): implement minimum run core`). That all-null seam is historical:
  P4-S1a (`748003319ececa548b68b351746afbb2d54c66bb`) and P4-S1b
  (`8eabf9d4c3c592ea1de50f443f1816de9a46dc8f`) complete the internal binding
  boundary. No public binding activation exists.

Neither P4-G0 nor the minimum prerequisite marks the full Run Protocol
implemented. World generation, profile resolution, scenario execution,
later-world selection, visits/revisits, world-line transitions, narrative
progression, and public Run behavior remain deferred beyond this gate.

## Phase 3.4: NPC Relationship and Temporary Residence

Status: **Approved product design — not implemented.**

Phase 3.4 owns engine-confirmed relationship progression, residence eligibility
and lifecycle, bounded dialogue, temporary fixed-scene activities, departure,
and structured relational memory integration.

The canonical design is
[NPC Relationship and Temporary Residence](docs/npc_relationship_residence.md).

## Phase 4.0: Production Provider Distribution

Status: **Accepted architectural direction — not implemented.**

Phase 4.0 owns player-selected Provider/model channels, the self-controlled
Production Distribution Gateway, server-side credentials, explicit
Provider-preserving failures, commercial quotas, metering, rate limiting, and
abuse control. Silent cross-Provider fallback is prohibited.

The canonical decision is
[ADR 0001: Production Provider Distribution](docs/decisions/0001-production-provider-distribution.md).

## Phase 8: Structured Player Character Run Entry and Minimum Playable Loop

Status: **Implemented and complete at published P8-S6 closure baseline
`7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`; no P8-S7 exists.**

Phase 8 delivered its selected product priority: create or reuse an owned
Structured Player Character, discover/select an eligible one, enter a
server-created Run immutably bound to it, create trusted Session participation,
and play through the existing authoritative Session lifecycle in the
deterministic Demo and minimal existing Web client.

The canonical approved and published planning authority is the
[Phase 8 implementation plan](docs/structured_player_character_run_playable_loop_plan.md).
It preserves the existing Phase 6 subject-reference and Phase 7 closeout
allocations exactly. Neither unfinished phase is a prerequisite for the minimum
backbone: Phase 8 creates no new memory/relationship/consequence fact and owns
its own bounded final evidence/status slice. Full world/profile behavior,
later-world progression, Run termination, Provider work, production
authentication, deployment, and broader game systems remain outside Phase 8.

The original exact seven-document planning candidate received
`STRUCTURED_PLAYER_CHARACTER_RUN_PLAYABLE_LOOP_PLAN_REVIEW_APPROVED` and was
committed and published at `de4d8c0e35c7864948306d751a00aaf295ff77ff`.
Planning publication does not authorize implementation. Later modifications to
the canonical planning bytes require fresh exact-byte independent review before
a separately authorized documentation commit; that commit precedes user
publication and clean published-baseline confirmation. P8-G0 is complete and
published. P8-S1 eligible-character discovery is implemented, independently
accepted, committed, and published at
`95ffe4019e2a69967dfae1fee2a1ecba4a628381`. P8-S2 atomic internal Run entry is
implemented, accepted, committed, and published at
`70815b181624e5475d2d978bef0db1ed3b22324e`
(`feat(player-character): add durable run-entry initialization`); its
implementation and F1/F2/F3 evidence are closed, and P8-S2 is not being
reopened. The dedicated
[P8-S3 implementation plan](docs/structured_player_character_p8_s3_implementation_plan.md)
received `STRUCTURED_PLAYER_CHARACTER_P8_S3_PLAN_REVIEW_APPROVED` and was
committed and published at `e17172ad0a9febe4ec9e3a96e7be8204c9722d29`.
The authorized implementation introduced the normal public
`POST /v1/runs` entry boundary. Its first independent implementation review
returned `CHANGES_REQUIRED` with five bounded findings. The bounded correction
completed all five: canonical `RunEntryService` identity and production wiring,
an effective raw duplicate-JSON-member regression, authoritative terminal-job
linkage to action ordinal 19, removal of stale current-state adapter-absence
claims, and complete MySQL cleanup recounts. Correction-thread verification
reported canonical Offline `1919 passed, 182 skipped` and MySQL `194 passed`.
Those totals did not by themselves pre-approve the documentation correction.
The subsequent independent read-only re-review found no remaining actionable
runtime, API, strict-transport, OpenAPI, MySQL, persistence, privacy,
architecture, cleanup, or test-discrimination defect, but formally returned
`CHANGES_REQUIRED` solely for one Medium documentation-synchronization finding.
A later focused independent read-only review approved the complete 15-path
candidate. It was committed and published at
`ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`
(`feat(run): add P8-S3 playable-loop adapter`) with exactly three production,
five test, and seven documentation paths. P8-S3 is complete. The dedicated
[P8-S4 implementation plan](docs/structured_player_character_p8_s4_implementation_plan.md)
was independently approved, committed, and published at
`375a2a7ae018c9c9c79272e5de7da703818d1f20`. Its exact nine-path implementation
received
`STRUCTURED_PLAYER_CHARACTER_P8_S4_IMPLEMENTATION_CORRECTION_INDEPENDENT_REVIEW_APPROVED`,
was committed as `187d41ba3035c8d717c2fb2578a805402255d979`
(`feat(player-character): complete P8-S4 demo persistence`), and was manually
published by the user. It completes deterministic Demo persistence/composition
parity by reusing the established Player Character, Run-entry, Session, and
gameplay services over process-local authority; the published P8-S4 plan defines
the detailed verification matrix, and the Phase 8 plan records its reviewed
completion evidence. The dedicated
[P8-S5 implementation plan](docs/structured_player_character_p8_s5_implementation_plan.md)
was independently approved and published at
`dceecaf0d7a33ccde07f519f83997489acd5fc86`, remained frozen during
implementation, and its corrected implementation received
`STRUCTURED_PLAYER_CHARACTER_P8_S5_CORRECTED_IMPLEMENTATION_REVIEW_APPROVED`.
The exact eight-path Web implementation was committed and published at
`2ce56a757beed8a3989d38453da3b6d80342ca05`
(`feat(web): connect player characters to playable run flow`). The primary Web
journey now connects eligible Player Character selection or minimal creation
and scenario discovery to Run entry, same-tab Session recovery storage, the
authoritative Session View, and the existing action/status/recovery/terminal
loop. It consumes the existing public Player Character and Run-entry contracts
and does not use the legacy Session-create route for that primary journey;
the legacy route remains available. P8-S5 is complete. The approved and
published frozen P8-S6 plan at
`4edf2e3341e60632765b85796e8554797c645692` has now been executed through its
fresh executable evidence boundary: E01-E14 and C01-C21 passed, including the
accepted real-MySQL, deterministic guarded Demo, Web, Offline, MySQL, Full,
compile, Alembic, build, and loopback-smoke evidence. The exact P8-S6 closure
documentation then received independent approval, was committed and manually
published as `7dae3f5bbd3055e60e33b8ce6b1e05ce75f4824d`
(`docs(player-character): close P8-S6 evidence`), and was confirmed at aligned
`HEAD`, local `main`, and local `origin/main` with ahead/behind `0/0`. P8-S6 and
Phase 8 are complete, and no P8-S7 exists. Phase 6, Phase 7, the Structured
Player Character programme, and the overall project remain incomplete. P8-S4
used no real Provider or non-loopback network dependency and did not claim
real-MySQL verification.

## Deferred

- Full Run Protocol behavior beyond the minimum prerequisite and the planned
  Phase 8 Session-backed minimum admission; Phase 3.4 NPC residence; later
  structured-character API work beyond Phase 8; Provider,
  narrative, scenario, world, NPC, memory, relationship, combat, content, and
  broader public gameplay integration.
- The eligible initial-world catalogue and later-world weighting, anti-repeat,
  progression, and priority-injection details.
- Exact Phase 3.3 parameter values, serialization, and compatibility policy.
- Exact Phase 3.4 relationship thresholds, residence duration, memory schema,
  and dialogue allowance.
- The Phase 4.0 gateway implementation, model catalogue, pricing/quota formula,
  regional availability policy, and key-pool policy.
- Memory rebuild and compaction.
- Scenario replay and `scenario_run_id`.
- Exact cross-scenario NPC identity and compatibility schema.
- `DeviationEvaluator`.
- Generalized conflict/combat schema, resolution rules, and implementation.
- Worker, queue, or distributed orchestration.

## Stable implemented authority decisions

- Models generate untrusted narrative candidates.
- The engine and trusted server policies own objective mechanics, facts,
  permanent state, and canon.
- Public clients act only through authoritative affordances and refresh the
  complete authoritative View.
- Ordinary creative actions do not become anomaly candidates.
- The deterministic Demo Provider remains isolated from normal Provider
  composition and future production distribution.
- MySQL is the only production database target; there is no SQLite fallback.
- Live Provider calls are not a normal verification dependency.

## Workflow

Before independent audit, a phase-completion claim, or a request for commit
authorization, complete the canonical
[documentation-synchronization checklist](docs/engineering/codex_workflow.md#canonical-documentation-synchronization-checklist).

Codex may create a local commit only when the user explicitly authorizes that
exact commit operation. Codex never pushes; the user performs every push
manually.

## Document ownership

- Project status and roadmap: `PLANS.md`.
- Final player experience and cross-phase long-term system direction:
  [`docs/final_narrative_experience.md`](docs/final_narrative_experience.md).
- Approved and frozen, partially implemented downstream structured
  player-character implementation plan:
  [`docs/structured_player_character_implementation_plan.md`](docs/structured_player_character_implementation_plan.md).
- Approved P5-S3 plan and independently approved and published retirement
  history:
  [`docs/structured_player_character_p5_s3_implementation_plan.md`](docs/structured_player_character_p5_s3_implementation_plan.md).
- Approved and published Phase 8 Structured Player Character Run entry and
  minimum playable-loop planning authority:
  [`docs/structured_player_character_run_playable_loop_plan.md`](docs/structured_player_character_run_playable_loop_plan.md).
- Approved and published P8-S3 normal API/composition implementation plan and
  completed, independently approved, committed, and published implementation at
  `ac07a5fe267adfb0281ec2658b2fcbd0085f6eb1`:
  [`docs/structured_player_character_p8_s3_implementation_plan.md`](docs/structured_player_character_p8_s3_implementation_plan.md).
- Approved and published P8-S4 deterministic Demo parity implementation plan
  and completed, independently approved, committed, and published implementation
  at `187d41ba3035c8d717c2fb2578a805402255d979`:
  [`docs/structured_player_character_p8_s4_implementation_plan.md`](docs/structured_player_character_p8_s4_implementation_plan.md).
- Approved and published, frozen P8-S5 minimum Web connection implementation
  plan and completed, independently approved, committed, and published
  implementation at `2ce56a757beed8a3989d38453da3b6d80342ca05`:
  [`docs/structured_player_character_p8_s5_implementation_plan.md`](docs/structured_player_character_p8_s5_implementation_plan.md).
- Implemented architecture and composition roots:
  [`docs/architecture.md`](docs/architecture.md).
- Production Provider distribution:
  [`docs/decisions/0001-production-provider-distribution.md`](docs/decisions/0001-production-provider-distribution.md).
- Run Protocol and difficulty/world profiles:
  [`docs/run_protocol.md`](docs/run_protocol.md).
- Minimum Run-core prerequisite implementation sequence, persistence,
  transaction, and evidence:
  [`docs/minimum_run_core_implementation_plan.md`](docs/minimum_run_core_implementation_plan.md).
- NPC relationship and temporary residence:
  [`docs/npc_relationship_residence.md`](docs/npc_relationship_residence.md).
- Documentation and Git workflow:
  [`docs/engineering/codex_workflow.md`](docs/engineering/codex_workflow.md).
- Phase 3.2 specification and evidence:
  [`docs/phase_3_2_deterministic_demo_environment.md`](docs/phase_3_2_deterministic_demo_environment.md).

# Engineering Guardrails

This file records reusable rules derived from failures that have already
occurred in this repository. It does not list hypothetical future risks.

## Maintenance

Add or update a guardrail only when:

1. the failure actually occurred or was reproduced;
2. its cause is understood;
3. the rule applies beyond one exact implementation detail;
4. a regression test or verification command enforces it.

One-off bugs belong in regression tests and commit history.

Do not store raw audit reports, secrets, complete database URLs, user paths,
reference fiction, or speculative concerns here.

## ENV-001: Use the repository toolchain

Observed failure:

- Codex selected system Python 3.14 without pytest.
- Windows PowerShell 5.1 displayed Chinese text as mojibake.
- Buffered PowerShell replay corrupted native-command diagnostics and delayed
  the first useful pytest error until the command had finished.

Rule:

- On Windows, use PowerShell 7+.
- Use only `.\.venv\Scripts\python.exe`.
- Repository text uses UTF-8 and LF.
- Stream native command output unless a bounded, non-sensitive result must be
  captured for parsing.
- If `.venv` is missing or broken, stop instead of recreating it silently.

Enforcement:

- `AGENTS.md`
- `.editorconfig`
- `.gitattributes`
- `scripts/doctor.ps1`
- `scripts/verify.ps1`

## ENV-002: Offline work must be truly offline

Observed failure:

- A no-database review inherited `TEST_DATABASE_URL` and ran MySQL tests.
- Provider availability differed between Codex and the user's local terminal.

Rule:

- Offline tasks must not inherit database, DeepSeek, or live-test variables.
- A sandbox network failure does not prove that an API key is invalid.
- Live DeepSeek calls require explicit user authorization.
- Never print environment-variable values.

Enforcement:

- `scripts/verify.ps1 -Mode Offline`
- `scripts/doctor.ps1 -RequireOffline`
- Live tests remain opt-in

## GIT-001: Inspect the staged result

Observed failure:

- `git diff --check` did not include untracked files.
- An unrelated file once appeared in the staged file list.
- CRLF/LF and EOF warnings repeatedly appeared.

Rule:

Before committing:

1. inspect untracked files;
2. stage only reviewed paths;
3. run `git diff --cached --check`;
4. inspect `git diff --cached --stat`;
5. inspect `git status --short`.

Never commit `.env`, reference files, generated drafts, audit transcripts,
`__pycache__`, `.pyc`, or test output.

## DB-001: MySQL and transaction rules are fixed

Observed failure:

- MySQL authentication required an undeclared runtime dependency.
- Idempotency, snapshot CAS, rollback, and detached version restoration had
  incomplete edge cases.

Rule:

- Use MySQL 8, SQLAlchemy `AsyncSession`, and `asyncmy`.
- Never add a SQLite fallback.
- Tests may write only to `deviation_protocol_test`.
- Repositories do not commit.
- State, snapshot, events, response, job state, and version commit atomically.
- Idempotency binds the complete request and uses locks plus unique constraints.

Enforcement:

- Repository, UoW, idempotency, rollback, and real MySQL tests
- Alembic consistency checks

## DB-002: Ending candidates require post-event memory validation

Observed failure:

- StoryDirector correctly produced an ended runtime and its ending event.
- Full candidate validation ran before that event was persisted and before its
  declarative completion rule could update `ScenarioMemoryRecord`.
- The valid ending was therefore rejected because memory still said STARTED,
  making public completion unreachable.

Rule:

- Pre-persistence validation may defer only the ending/memory invariant, and
  only when the same resolution contains an event matched by a catalog-declared
  `COMPLETE_SCENARIO` rule for the exact ending.
- Structural, content, runtime, and player bindings still validate before event
  persistence.
- Persist and flush the authoritative event before applying memory rules.
- Run full snapshot/catalog/memory validation after memory application and
  before saving the snapshot and response.
- Ending event, completed memory, snapshot, response, job, and version commit
  atomically; any failure rolls back all of them. Narrative actions use the
  normal Provider job. A deterministic local ending choice uses a distinct
  attempt-zero local-template job whose text comes only from trusted content.

Enforcement:

- Public ASGI success and deadline-ending playtests
- Real MySQL ending, rollback, duplicate-request, and cleanup tests

## AUTH-001: Player and model input never create authority

Observed failure:

- Callers could previously forge Gateway routes, skill authorization, trusted
  events, decision authority, or narrative outcomes.
- A memory-rule boundary once read `sequence_no` to sort receipt-like input
  before proving that each object was an authentic repository-issued receipt.
- Free-text phrase matching proved too weak to authorize hidden clues, and an
  opaque event ID was once confused with the rule identity needed by `once`.

Rule:

Players and models may submit intent or proposals only. They cannot create:

- system commands;
- Gateway decisions;
- reward or skill authorization;
- trusted facts or events;
- capabilities or seals;
- outcome authority;
- arbitrary state or event payloads.

Authority must be issued by a trusted server-side policy and rebound to the
current session, turn, action, state version, state fingerprint, and scenario.
Opaque capabilities and persisted-event receipts must be authenticated before
their bound fields are read, compared, sorted, or used to select a rule.
Hidden clue authority requires structural server state such as a bound public
decision, authoritative current location, and mechanical action type. Outcome
rule identity comes from persisted evidence, never from a public event ID.

Enforcement:

- Receipt construction, tamper, cross-binding, and ordinary-string tests
- Declarative memory-rule authority tests

## STATE-001: Authoritative state and candidates stay isolated

Observed failure:

- Candidate state and authoritative projections risked sharing mutable nested
  objects.
- Runtime IDs and definition IDs were previously confused.

Rule:

- All speculative work occurs on a deeply detached candidate.
- Failure returns no partial state, success event, or success fact.
- Runtime item/NPC IDs remain distinct from definition IDs.
- Catalog existence does not prove ownership, visibility, or learned skills.
- Public projections never expose mutable GameState.

Enforcement:

- Object-identity, rollback, ownership, visibility, and ID-collision tests

## API-001: Public responses expose safe projections only

Observed failure:

- API responses exposed `action_signature` and unsupported internal routes.
- Ownership and internal exception handling required leakage protection.
- Internal-model `dump(exclude=...)` projections could publish future fields by
  default, and an unreachable retry state was advertised publicly.
- View snapshot-integrity failures exposed multiple internal classifications.
- Value-level response scans found that key allowlists alone were insufficient
  to prove internal identifiers absent from nested text and views.
- A decision Frame exposed definition-level action semantics and custom-action
  constraints even though the public client must submit only bound choices.
- Outcome-rule target qualification was used to advertise a player input target
  as required even though the Gateway contract kept that field optional.

Rule:

Public responses must not expose snapshots, internal state, signatures,
fingerprints, policy traces, capabilities, leases, provider payloads, SQL,
stack traces, local paths, or internal rule IDs.

Public DTOs derived from internal models enumerate every allowed field; they do
not use dump/exclude projection. Public enums advertise only production-reachable
protocol behavior. Aggregate view endpoints map known snapshot-integrity
failures to one stable public code without catching unrelated failures.
Tests scan both keys and serialized public values across mutation, query,
rejection, request-status, and ended-session responses.
Public content discovery and current-scene/ending presentation use explicit
versioned allowlist definitions, never a full domain-model dump. Public action
affordances reuse authoritative action/outcome/continue policies. Input field
support and requiredness come only from `InputContractPolicy`; outcome-rule
intent constraints qualify specific results and never redefine the submission
contract. Decision projection exposes generic choices and re-resolves their IDs
server-side.

Missing and unauthorized sessions use the same safe response.

Enforcement:

- Exact top-level and nested public response allowlists
- OpenAPI enum and snapshot-integrity API regressions

## SCENE-001: Scenario logic remains data-driven and private

Observed failure:

- The first scenario risked leaking into the generic engine.
- Hidden facts, NPC knowledge, clocks, clues, and endings could affect public
  Frame output.
- A displayed decision could exist outside authoritative runtime state.

Rule:

- Generic code never branches on scenario IDs or first-scenario content.
- Hidden state never enters public Frames or Frame-derived side channels.
- Runtime NPC existence comes from GameState.
- Displayed decisions must exist in authoritative runtime state.
- Unresolved decisions block incompatible advancement.

Enforcement:

- Non-hospital fixture scenarios
- Hidden-information scans
- Scenario-specific identifier scans
- StoryDirector and decision tests

## SCENE-002: Static analysis must remain conservative and bounded

Observed failure:

- Static analysis confused declared sources, structural reachability, and
  guaranteed outcomes.
- Graph traversal could degrade exponentially on dense graphs.

Rule:

- Distinguish declared, structurally reachable, conditionally unknown, and
  guaranteed results.
- Player choices, trusted events, model outcomes, and combined conditions stay
  `unknown` unless formally proven.
- Graph analysis must be bounded.
- Heuristic cadence warnings never become authoritative runtime rules.

Enforcement:

- `docs/scenario_workbench.md`
- Conditional-analysis and dense-graph tests

## MODEL-001: Narrative models are untrusted and minimal

Observed failure:

- Prompt injection could enter through player text, history, or summaries.
- Provider output had duplicate-key, type, size, reference, and ownership gaps.
- Provider prose could contradict a fixed server acknowledgement even though it
  could not mutate state.

Rule:

- Send only minimal public context.
- Treat every prompt field and model output as untrusted data.
- Strictly validate JSON, sizes, types, IDs, ownership, and visibility.
- Valid model output is still not a world fact.
- Model prose never rewrites fixed facts.
- When an outcome carries fixed semantic meaning, accepted public prose comes
  from a fixed server template; Provider prose remains an internal candidate.
- Runtime-NPC evidence rejects every unknown instance ID, including extra IDs.

Enforcement:

- `docs/narrative_provider.md`
- Prompt injection and malformed-output tests

## MODEL-002: Provider calls and accepted prose use durable boundaries

Observed failure:

- Provider calls risked holding database locks.
- Retry and crash windows created ambiguous billing.
- Candidate prose and accepted prose were described inconsistently.

Rule:

- Provider calls occur outside database transactions and row locks.
- Default provider retry is zero.
- Ambiguous delivery becomes `OUTCOME_UNKNOWN` and is not automatically resent.
- Candidate prose is internal and non-authoritative.
- Only atomically committed accepted prose is visible, replayable, or usable as
  recent narrative context.
- Do not claim exactly-once provider billing.

Enforcement:

- Three-stage narrative orchestration
- Lease, crash, concurrency, and recent-context tests

## TOOL-001: Scenario scaffolds never overwrite or publish formal content

Observed failure:

- POSIX rename could replace an empty directory.
- Staging cleanup lacked identity binding.
- Draft output could target the formal scenario directory.
- Path, Markdown, and digest boundaries were incomplete.

Rule:

- `scenario new` never overwrites, merges, or replaces existing content.
- Cleanup applies only to staging owned by the current operation.
- Draft generation cannot target `config/scenarios`.
- Reject traversal, unsafe Windows names, ADS, and reparse-point escapes.
- Generated output is deterministic UTF-8/LF.
- Promotion to formal content is always manual.

Enforcement:

- `docs/scenario_workbench.md`
- Concurrent publication, path, cleanup, Markdown, and digest tests

## CONTENT-001: Reference material and anomaly behavior remain constrained

Observed failure:

- Reference fiction was repeatedly clarified as non-production material.
- Ordinary creative actions were incorrectly at risk of being treated as
  anomalies.
- Choice frequency initially risked being too high outside the core conflict.

Rule:

- Reference fiction is style-only; never copy its plot, names, prose,
  equipment, skills, or distinctive setting elements.
- Ordinary creative actions remain normal narrative actions.
- Only highly unusual and feasible approaches may later become eligible for
  deviation evaluation.
- Early scenario choices remain relatively sparse; decision frequency may rise
  near the core conflict.

Enforcement:

- `AGENTS.md`
- Scenario cadence tests
- ActionGateway tests
- Manual content review

## PLAY-001: Production reachability requires a production public entry point

Observed failure:

- StoryDirector already supported deterministic empty-event auto-beat advancement.
- After the opening Narrative committed into `life_disputed`, the public Frame
  required CONTINUE but the public ActionType/API had no CONTINUE entry point.
- Direct Director and private issuer tests therefore proved domain reachability
  while a real public ASGI request still failed with 422.
- The first MySQL regression stopped after one CONTINUE while the claimed public
  slice required three steps to reach the next decision.

Rule:

- Claim player/API reachability only when a production-authorized public entry
  point test covers ownership, validation, orchestration and persistence.
- Direct calls to StoryDirector, private event issuers or repository test helpers
  prove only domain or component reachability.
- A structural scenario graph or Workbench preview does not prove a playable
  production path.
- A claimed multi-step production slice is covered end-to-end for every step by
  the public API and production Repository on real MySQL.

Enforcement:

- Public ASGI vertical-slice playtest with real production application services
- Real MySQL public-entry regression through all three CONTINUE steps, with
  persisted version/beat/frame/events/response/snapshot and cleanup checks

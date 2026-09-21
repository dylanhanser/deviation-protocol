# Open-source comparison and bounded reading improvements

Inspection date: **2026-09-20**. Baseline:
`a35a1bff588c6eb24535820b150bae5566d7b5f7` (`main`, clean, local
`origin/main` aligned; no fetch). The user confirms manual publication and
independent approval of Phase 3.3/S7-5. Current status is synchronized in
[PLANS](../PLANS.md); frozen plans and the S7-5 candidate-time record are unchanged.

**Disposition:** research and a compatible Web implementation candidate, not
independent approval. Recommendations below are not approved product requirements.
No backend, gameplay, content, dependency, migration or Provider code changes.

## Existing implementation, not assumed gaps

| Area | Actual local path and behavior | Limit relevant to the player |
| --- | --- | --- |
| Reading | `web/src/App.tsx` consumes a validated `PlayerSessionView`; current choices come from `action_affordances`. Foreground ownership, generation checks, explicit consent, GET recovery and stale locks already exist. | Baseline put setup and technical metadata before prose, repeated the latest segment in recent history, flattened paragraph whitespace, and labelled historical Views current. This candidate changes presentation only. |
| Facts and history | `domain/facts.py`, `domain/scenario_runtime.py`, `application/story_director.py`, SQL/Demo repositories: fixed/deferred/mutable/dynamic facts, visibility, clocks, decisions, ending events, detached candidates, atomic event/snapshot/response commits. | Accepted prose is readable context, not a second source of mechanics or canon. Session ending and Run completion/termination remain distinct. |
| Memory | `application/player_memory.py`, `domain/player_memory.py`, `domain/memory_rules.py`: authenticated persisted-event receipts → declarative rules → sealed mutation plans → bounded index. Capacity pressure marks `REBUILD_REQUIRED`; public projection has independent truncation. | No golden-memory promotion, rebuild/compaction worker, cross-world NPC identity or retrieval service. The previous count-only display did not distinguish a complete index from a partial projection. |
| Prompt and Provider | `application/narrative_turn_orchestrator.py` prepare supplies up to six accepted Session-local fragments, public memory, and currently an empty `public_story_summary`. `narrative_prompt.py` compiles bounded JSON plus authenticated Run/visit annotations. Production DeepSeek and deterministic Demo are separate compositions. | There is no automatic summary refresh; a configured Provider already exists. No real Provider was called here. Candidate prose/continuity notes cannot write memory or select native results. |
| Cross-world continuity | `run_continuation_service.py`, `run_revisit_service.py`, `world_visit_context.py`, `session_service.py`: reconstruct owned Run/line/visit evidence, carry complete `PlayerState`, initialize destination-local runtime/memory, supply allowlisted arrival context, retain immutable old Sessions and GET history. | This is a real three-visit bounded journey, not an absent continuity system. It is not a merged character-wide memory index. Session memory must not be copied wholesale into a different scenario. |
| Resolution | `domain/actions.py`, independent `domain/policies.py`, `application/rule_resolver.py`, `effect_executor.py`: validated intents, owned targets/items/skills, local costs/effects and query/no-mutation branches. Native `native_turn_mechanics.py` chooses an authored result before rendering; five integer objective policies in `run_protocol_mechanics.py` adjust approved resources/clocks. | `conflict_intensity` is an approved clock contribution, not a general combat engine. No approved general participant roster, injury/death system, positional model or contested probability rule exists. |
| Content | Strict scenario definitions, reference validation, declarative outcome rules, a pinned `session_content_registry.py`, and Workbench validation already separate authored content from generic story logic. | Native `MECHANICS_CATALOGUE`, entry/continuation initializers and visit annotations intentionally enumerate the three approved hospital/receipt/archive scenarios and `composure`. A wuxia opening needs explicit catalogue/admission/mechanics mappings; renaming a pack is insufficient. |

These findings follow [architecture](architecture.md), [public contract](public_client_contract.md),
[memory](player_memory.md), [Provider](narrative_provider.md), the approved
[final experience](final_narrative_experience.md), and S5/S6/S7-2/S7-3/S7-4
contracts. General conflict and protected memory remain design requirements,
not already implemented subsystems or permission to invent balance.

## Four selected references

Public GitHub API metadata, raw fixed-commit files and hashes are retained in
the external evidence package. Stars are approximate attention indicators, not
quality or optional-subsystem adoption evidence. All four repositories reported
`archived=false`. Source/tests were read, not installed or executed.
Yarn Spinner was considered from the requested shortlist but not deeply surveyed:
ink covers the immediate authored-text/choice boundary, while the other three
provide distinct memory and conflict comparisons. No claim about Yarn quality
or adoption is made.

| Repository | Inspected commit / release | License checked at that commit | Attention and maintenance observed |
| --- | --- | --- | --- |
| [ink](https://github.com/inkle/ink) | `35c63e52f1d36060930dc7ed3cfba38ea224b528`; release `v1.2.1` published 2026-05-05 | [MIT][ink-license] | 4,944 stars (~4.9k); inspected head dated 2026-05-05; [release record](https://github.com/inkle/ink/releases/tag/v1.2.1). |
| [SillyTavern](https://github.com/SillyTavern/SillyTavern) | `06bde939fb1e9c4c8d8641d810f0a916b5bce127`, release branch; `1.19.0` | [AGPL-3.0][st-license] | 33,597 (~33.6k); head and release dated 2026-09-14. Frequent releases establish maintenance, not memory correctness. |
| [Evennia](https://github.com/evennia/evennia) | `a89a9b94e4d7ed0acfee86def533b77bf6baa512` | [BSD-3-Clause][evennia-license] | 2,104 (~2.1k); head dated 2026-08-19. GitHub releases endpoint returned an empty list; this is commit-based inspection, not a release claim. |
| [boardgame.io](https://github.com/boardgameio/boardgame.io) | `5e9a2c94bde803fae8b081958c406c4d0a7be8ae` | [MIT][bg-license] | 12,435 (~12.4k); head dated 2026-08-10. Releases endpoint empty; [maintainer discussion](https://github.com/boardgameio/boardgame.io/issues/1236) and [publishing issue](https://github.com/boardgameio/boardgame.io/issues/1255) warrant distinguishing recent commits from a reliable release pipeline. |

### ink: text, available choices and saved execution state

`Story.currentChoices` filters invisible defaults; `Continue`/`currentText`
expose narrative separately from selection. [Story.cs][ink-story] and
[Running Your Ink][ink-doc] demonstrate a host-owned presentation layer.
[StoryState.cs][ink-state] serializes execution state and checks save format;
[Tests.cs][ink-tests] includes `TestChoiceCount`, `TestDefaultChoices` and
`TestListSaveLoad` (the latter reloads and continues a modified list).

Adoption: the developer's [Heaven's Vault page](https://www.inklestudios.com/heavensvault/)
explicitly identifies ink in a shipped game. This supports engine adoption, not
proof of our ownership/recovery guarantees. [Issue #959](https://github.com/inkle/ink/issues/959)
reports fallback-choice visibility after reload; it is user-reported evidence,
not a reproduced defect in our project or in the inspected commit.

**Adopt:** keep readable output separate from available authoritative actions;
make earlier reading secondary and current/history identity unambiguous.
**Do not import:** ink runtime, save format, choice indices, compiler or a
client-owned story state. Our opaque bound choices and server receipts remain.

### SillyTavern: bounded context and summary scope

[Memory extension][st-memory] locates summaries in chat-message metadata,
checks chat/group/character identity before accepting delayed work, and invalidates
edited/deleted context. [World Info][st-world] combines chat/persona/character/global
lore, selects keyword matches and applies ordering, budget and recursion controls;
see the [official explanation](https://docs.sillytavern.app/usage/core-concepts/worldinfo/).
The inspected [chat-lore rename test][st-test] checks metadata binding after a
rename; its persona counterpart checks the other binding. Neither proves summary
accuracy, long-term recall or authority-safe retrieval. No such test proof is claimed.

Adoption evidence is actual tool use: [issue #5498](https://github.com/SillyTavern/SillyTavern/issues/5498)
reports summary settings and blocking behavior on desktop/mobile version 1.17.0.
This is an unreplicated report, not proof against 1.19.0. Stars/community activity
are attention evidence. No shipped-game integration was verified.

**Adopt:** explicit context scope, bounded inclusion, stale-summary rejection,
and separate completeness indicators. **Do not import:** editable chat summaries
as canon, keyword activation as fact/NPC authority, prompt concatenation as a
permission boundary, extensions, vectors or copied AGPL code. No code from this
project is included; a future dependency/code reuse needs its own license decision.

### Evennia: action policies and conflict lifecycle

[Basic combat][evennia-basic] separates rules and a turn handler but explicitly
implements HP, random attack/damage, room membership and a 30-second timeout.
[Tests][evennia-tests] exercise damage, action consumption, cleanup, turn advance
and joining. The [official contrib guide][evennia-doc] treats this as extensible
example code. [EvAdventure base][evennia-base] separates action `can_use`, execution
and post-execution; [turnbased handler][evennia-turn] manages participants,
queued actions, defeat and escape. These are tutorial/contrib designs, not
evidence that their balance fits a continuous novel.

Adoption: [Arx's own repository](https://github.com/Arx-Game/arxcode) identifies an
Evennia-based game. This establishes framework use, not use of turnbattle or
EvAdventure. The official live game index was unavailable through the research
tool; no active-player counts or current service-health claim is made.

**Adopt as a proposal:** separate legality, outcome/effect planning and lifecycle
termination. **Do not import:** Django/Twisted persistence, open-ended action-dict
attributes, real-time timers, repeating fallback actions, HP, dice or death rules.
Those conflict with our strict carriers, explicit submissions and atomic UoW.

### boardgame.io: allowed moves and phase termination

[Reducer][bg-reducer] checks move availability, game-over and active participants,
then applies the move and server flow; invalid/plugin-invalid paths preserve
prior state. [Flow][bg-flow] separates game phases, turns and player stages and
guards loops in phase termination. [Reducer tests][bg-reducer-tests] include
invalid and post-game moves; [flow tests][bg-flow-tests] exercise phase hooks,
`endIf` and order. [Phases][bg-phases] and [stages][bg-stages] explain the separation.

The official [site](https://boardgame.io/) supplies framework examples and feature
claims; no shipped-game adoption was independently verified in this bounded
inspection. [Issue #1294](https://github.com/boardgameio/boardgame.io/issues/1294)
reports old move signatures in examples: documentation popularity is not proof
that every example matches current implementation.

**Adopt as a proposal:** explicit participant eligibility and terminal checks
before effects; test result/phase transitions independently of prose.
**Do not import:** Redux/network/lobby stack, client speculation, undo/time travel
as gameplay mutation, generic plugins or JavaScript move functions in content.
Our historical reads remain GET-only and immutable.

## Ranked comparison matrix

Cost: S = this bounded Web slice; M = a separate small server/content contract;
L = new identity/persistence or gameplay rules. Ranking weighs immediate player
benefit, confidence from local evidence and cost, not stars.

| Rank / local limitation | Reference implementation | Adaptation / disposition | Player benefit | Cost / confidence | Authority / dependency effect | Smallest meaningful validation |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Setup/metadata dominate; repeated, flattened prose | ink output separate from choices | **Implemented:** story/actions precede setup during play; plain paragraphs; earlier segments in disclosure | Read the scene and decide without scanning a dashboard | S / high | Existing DTOs only; no dependency | Render order, multiline literal markup, one latest segment; current choice/recovery regressions |
| 2. Historical View labelled current; recency window looks like full history | ink save boundary; ST context identity | **Implemented:** read-only historical label, visit-scoped bounded recap, Session-keyed disclosures | Avoid confusing a past scene with current progress | S / high | No navigation, storage or POST change | Three-visit GET navigation, refresh/current return, stale/terminal controls |
| 3. Memory counters obscure scope and truncation | ST context limits; local projector already exposes flags | **Implemented:** distinguish lagging index from truncated projection, returned/total counts, explicit visit scope | Know what the game is showing and what is missing | S / high | No facts reconstructed from references or prose | CURRENT+truncated and REBUILD_REQUIRED+truncated render distinctly; source View unchanged |
| 4. No readable cross-world recap or summary refresh | ST bounded inclusion; ink explicit state | **Proposed D1:** server-rendered same-Run recap of approved public evidence | Recall why the next world matters | M / medium | Versioned read/prompt projection; no new database technology; new product scope decision | Both first-world endings → hold → archive; old content version; foreign Run; missing evidence; refresh adds no writes |
| 5. Existing rules lack general participant/objective contracts | Evennia actions; boardgame phases/moves | **Proposed D2:** closed conflict intent/context/plan with independent policies, one committed segment per submitted action | Combat, negotiation, pursuit and infiltration can change a situation meaningfully | M–L / medium | New mechanics/content contract; reuse UoW, no engine replacement | Two genres and two conflict objectives; illegal target; terminal; replay; failure consequence and rollback |
| 6. No approved wounds/probabilities/golden identity | Evennia exemplifies choices we must not silently inherit | **Proposed D3:** non-lethal authored prototype first; persistent injury/randomness separate | Playable feedback before permanent balance mistakes | L if persistent / medium | User chooses consequence scope; no silent HP/dice/death/rewards | Approved outcome table plus exact replay and source-of-truth checks |

## Product decisions

These are consolidated recommendations for later authorization, not a new gate
on the compatible changes already made.

| Choice | Exact recommended starting choice | Alternative / consequence |
| --- | --- | --- |
| D1 — next memory improvement | Same-Run, read-only **旅程回顾** built deterministically from already validated visit/ending/public-fact evidence; no model call. Proposed ceiling 2,000 characters inside the existing total prompt budget if later enabled for rendering. Default scope excludes other Runs even for the same character. | Character-wide recall needs explicit participation/provenance and logical identity across Runs; generated summaries also need quality evaluation, refresh and contradiction policy. Both cost more and must not reuse local scenario keys as global identity. |
| D2 — first general conflict slice | An authored, deterministic, non-lethal **escape/protection encounter**, using goal, participants, eligibility, position/conditions, approved costs/effects and explicit end conditions. Keep the same reading/action flow. Failure changes position, objective progress or a declared danger clock instead of forcing identical repeated attacks. | Begin with a lethal duel or universal combat mode: requires HP/injury/death and balance decisions immediately; begin with negotiation only: cheaper, weaker physical-conflict feedback. No dice probabilities are selected here. |
| D3 — initial consequences | Temporary, encounter-local named conditions and authored consequences; no new persistent injury, death, cooldown, reward or progression rule in the first prototype. Reuse an existing resource only when its authored contract explicitly permits that encounter cost; otherwise cost values await the encounter's reviewed table. | Persistent wounds/cross-world penalties have stronger continuity value but require character/world compatibility and persistence semantics. HP/damage is an optional later world mechanic, not the universal engine base. |

D1 design sketch: keep authoritative facts/events separate from replaceable
context. Every recap item must carry private provenance (owned Run/visit/Session,
source version, content identity, validated public fact/ending reference) and
derive fixed display text from approved content. Select required unresolved
consequences first, then recent public items within a fixed budget; stable tie
ordering. Refresh only when bound source versions change. Contradictory or missing
evidence fails closed; omit optional unavailable context with an explicit limit,
never rewrite a fixed fact or silently treat absence as falsity. A later generated
summary is disposable presentation, never an input to mechanics or a memory plan.
No vector/graph store is needed for this small bounded surface. Golden memory and
NPC promotion remain under their frozen future identity/capacity requirements.

D2 design sketch: `ConflictIntent` expresses the player's chosen intention;
server-owned `ConflictContext` supplies participants, goal and local rules;
independent policies produce a detached `ResolutionPlan` with approved outcome,
costs, effects and termination evidence. These are proposal names, not new models.
Resolve before Provider expression, revalidate under the existing finalization
transaction, and commit once with events/memory/snapshot/response. Pursuit uses
escape position, negotiation uses concessions, infiltration uses exposure;
share legality and lifecycle interfaces, not one universal numeric formula.
Reject unbound or invisible targets and preserve exact player intent on rejection.

## Portability and remaining presentation work

The new component branches on public current/history/ending state, never hospital,
receipt/archive IDs, resource names or genre. Existing resource and clock IDs
remain as supplied because the public contract has no localized display labels;
the client must not invent semantic names. A future wuxia opening can reuse the
reader, public affordances, declarative scenario machinery and UoW, but requires
original content, version/digest registration, approved admission/resource mappings
and explicit local capabilities/costs. Do not port medical nouns into a general
conflict abstraction or assume every world shares one power scale.

This candidate is not the final reading-first redesign. Fixed action forms remain
where the existing contract requires them; exactly-three-plus-free-action stays
limited to its approved dynamic surface. Full inventory/memory browsers, localized
resource labels, streaming, theme/font preferences and new narrative suggestions
are not implemented. Error/stale/recovery copy remains explicit, and consent and
terminal distinctions remain outside collapsed details.

CSS uses a bounded prose measure, responsive type, preserved line breaks,
wrapping and visible keyboard focus on native disclosure summaries. No forced
scroll, focus movement, animation, dependency or unsafe HTML rendering is added.
Real mobile layout, screen-reader announcements, keyboard focus across manual
Session replacement and visual contrast require authorized browser observation;
jsdom results cannot prove them.

## Verification and handoff

The external package contains exact commands, raw failed/passing logs, source
snapshots, path inventory, before/final Git identities, a complete patch and
per-file hashes. Fresh results: 11 focused Offline public-contract tests pass;
15 Web suites pass with 441 passed and one existing optional presentation-probe
skip. The eight new reading cases are included in that Web total. Type checking,
lint and the deterministic-demo build pass. Early failures and interrupted runs
are preserved separately, not added to successful totals. No exhaustive S2 or
migration matrix rerun is needed for a Web-only change. Precise commands and
accepted-evidence reuse qualifications are in the external handoff.

Later browser proof should cover: a long multiline scene at 320/390px and 200%
zoom; keyboard disclosure opening/closing; a pending/failed action with prose
remaining readable and submission locked; both ending classes; completed vs
terminated Run; 3→2→1→2→3 history and historical refresh; explicit clear after
backend restart with GET-only recovery. Observe storage/request order directly
where tooling supports it. No browser, listening Web/backend service or real
Provider was used here; automated Demo cases use the existing isolated ASGI
process bridge with external network denied.

DF-001 retains its process-local locale containment. DF-002 retains separate
discovery GET retries and backend-ready full-page refresh after explicit clear;
the startup race was not rerun and is not closed. S7-4/S7-5 historical evidence
keeps all limits: no new SQL atomicity, private identity, complete PlayerState,
storage-call-order, production Provider or release-readiness claim.

## Guardrail impact

None. Existing API-001, AUTH-001, STATE-001, MODEL-001/002 and the workflow cover
this presentation-only change. No newly established reusable authority rule.

[ink-license]: https://github.com/inkle/ink/blob/35c63e52f1d36060930dc7ed3cfba38ea224b528/LICENSE.txt
[ink-story]: https://github.com/inkle/ink/blob/35c63e52f1d36060930dc7ed3cfba38ea224b528/ink-engine-runtime/Story.cs#L37
[ink-state]: https://github.com/inkle/ink/blob/35c63e52f1d36060930dc7ed3cfba38ea224b528/ink-engine-runtime/StoryState.cs#L704
[ink-tests]: https://github.com/inkle/ink/blob/35c63e52f1d36060930dc7ed3cfba38ea224b528/tests/Tests.cs#L2908
[ink-doc]: https://github.com/inkle/ink/blob/35c63e52f1d36060930dc7ed3cfba38ea224b528/Documentation/RunningYourInk.md
[st-license]: https://github.com/SillyTavern/SillyTavern/blob/06bde939fb1e9c4c8d8641d810f0a916b5bce127/LICENSE
[st-memory]: https://github.com/SillyTavern/SillyTavern/blob/06bde939fb1e9c4c8d8641d810f0a916b5bce127/public/scripts/extensions/memory/index.js#L353
[st-world]: https://github.com/SillyTavern/SillyTavern/blob/06bde939fb1e9c4c8d8641d810f0a916b5bce127/public/scripts/world-info.js#L4595
[st-test]: https://github.com/SillyTavern/SillyTavern/blob/06bde939fb1e9c4c8d8641d810f0a916b5bce127/tests/frontend/WorldInfoRenameChatLore.e2e.js
[evennia-license]: https://github.com/evennia/evennia/blob/a89a9b94e4d7ed0acfee86def533b77bf6baa512/LICENSE.txt
[evennia-basic]: https://github.com/evennia/evennia/blob/a89a9b94e4d7ed0acfee86def533b77bf6baa512/evennia/contrib/game_systems/turnbattle/tb_basic.py
[evennia-tests]: https://github.com/evennia/evennia/blob/a89a9b94e4d7ed0acfee86def533b77bf6baa512/evennia/contrib/game_systems/turnbattle/tests.py#L117
[evennia-doc]: https://github.com/evennia/evennia/blob/a89a9b94e4d7ed0acfee86def533b77bf6baa512/docs/source/Contribs/Contrib-Turnbattle.md
[evennia-base]: https://github.com/evennia/evennia/blob/a89a9b94e4d7ed0acfee86def533b77bf6baa512/evennia/contrib/tutorials/evadventure/combat_base.py#L73
[evennia-turn]: https://github.com/evennia/evennia/blob/a89a9b94e4d7ed0acfee86def533b77bf6baa512/evennia/contrib/tutorials/evadventure/combat_turnbased.py#L291
[bg-license]: https://github.com/boardgameio/boardgame.io/blob/5e9a2c94bde803fae8b081958c406c4d0a7be8ae/LICENSE
[bg-reducer]: https://github.com/boardgameio/boardgame.io/blob/5e9a2c94bde803fae8b081958c406c4d0a7be8ae/src/core/reducer.ts#L462
[bg-flow]: https://github.com/boardgameio/boardgame.io/blob/5e9a2c94bde803fae8b081958c406c4d0a7be8ae/src/core/flow.ts#L225
[bg-reducer-tests]: https://github.com/boardgameio/boardgame.io/blob/5e9a2c94bde803fae8b081958c406c4d0a7be8ae/src/core/reducer.test.ts#L52
[bg-flow-tests]: https://github.com/boardgameio/boardgame.io/blob/5e9a2c94bde803fae8b081958c406c4d0a7be8ae/src/core/flow.test.ts#L23
[bg-phases]: https://github.com/boardgameio/boardgame.io/blob/5e9a2c94bde803fae8b081958c406c4d0a7be8ae/docs/documentation/phases.md
[bg-stages]: https://github.com/boardgameio/boardgame.io/blob/5e9a2c94bde803fae8b081958c406c4d0a7be8ae/docs/documentation/stages.md

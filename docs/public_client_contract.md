# Public Client Contract

Phase 3.0 defines the server-owned read contract for a shared Web client and a
future desktop wrapper. It does not provide public identity, abuse controls,
deployment, a browser application, or a desktop adapter. The default principal
is still the fixed `demo-player`/`demo-dev-only` identity and is unsafe for an
Internet-facing deployment.

## Public scenario discovery

`GET /v1/scenarios` returns a bounded catalog sorted by `scenario_id`. Only a
scenario with an explicit `public_client` block in its versioned scenario pack
is listed. The response is built field by field and contains:

- `scenario_id` and `content_version` from `ScenarioDefinition`;
- public `title`, `hook`, character descriptions and default character from the
  scenario's `public_client` block;
- character display names from the matching versioned `ContentCatalog` entry.

The endpoint never serializes `ScenarioDefinition`. Facts, clues, transitions,
outcome and memory rules, NPC knowledge, phase identifiers, clocks, endings and
future-scene metadata are not part of this response. A public metadata block is
strictly bounded and catalog loading verifies all referenced characters, every
scene/ending presentation, unique action labels and the default character.

## Session view presentation

`GET /v1/sessions/{session_id}/view` retains the existing reconnect-safe
projections and adds two explicit objects:

- `presentation`: public scenario title plus only the current scene title and
  summary. `ending` is omitted while ACTIVE and contains only the matching
  public title and summary after the runtime has ended.
- `action_affordances`: the current UI action contract described below.

The projection looks up public copy by the validated runtime's current phase and
ending, but does not emit those internal lookup keys in the new presentation
objects. A missing or inconsistent binding is handled as `SNAPSHOT_INVALID`.
View reads do not advance the Director, claim a lease, invoke a Provider, or
write sessions, snapshots, events, turn requests or narrative jobs.

## Action affordances

`action_affordances.mode` has three states:

| Mode | Public payload | Client behavior |
| --- | --- | --- |
| `DECISION` | Bound public `decision_id` and `CHOOSE` choices | Submit one displayed choice; no free-action entry is advertised. |
| `FREE_ACTIONS` | Zero or more typed actions | Render the declared input and optional visible targets. |
| `ENDED` | No actions or choices | Render settlement only. |

Decision choices are copied from the current safe Frame. Their public Frame
type is the non-semantic value `choice`; internal scenario action types and
custom-action constraints are removed at the public decision binding. On
submission, `ScenarioDecisionResponsePolicy` uses the public choice ID to look
up the current versioned definition again, and only the trusted definition can
provide event or state effects.

Free narrative action types come from the same structurally eligible
`narrative_outcome_rules` used by `allowed_narrative_outcomes`. The shared query
applies current phase, location, decision, clue, fact, visible-NPC and once-only
conditions but does not reveal rule identity or text matchers. Submitted text is
still checked by the full outcome policy. `input_kind` and maximum length come
from `InputContractPolicy`, which also validates submissions. Labels come from
the versioned public content block. `CONTINUE` appears only when
`ScenarioContinuePolicy` authorizes the current state and Frame.

The affordance is a UI description, not a capability. `ActionGateway`, the
decision/continue policies, locked state reload and narrative outcome policy
remain final authority. Clients must handle a later rejection or stale view.

### Targets and TALK

Targets contain only current runtime NPC IDs and display names already present
in the player-visible state and current Frame. Definition IDs, invisible NPCs
and rule-required subjects are not disclosed by the target projection.

Existing production policy allows `TALK` with dialogue and no target; Phase 3.0
therefore exposes `target_required=false`. A client may offer the current
visible NPCs as optional targets. The server continues to reject every supplied
target that is not currently visible/interactable. Changing TALK to require a
target would be a separate domain-contract change, not a UI assumption.

## Client submission rules

- `NONE` means no player-authored input; currently this is `CONTINUE`.
- `DESCRIPTION` uses `description`, currently with a 150-character limit.
- `DIALOGUE` uses `dialogue`, currently with a 200-character limit.
- A decision uses `CHOOSE`, the current public `decision_id`, and one displayed
  `choice_id`; it has no text, target or tool payload.
- Clients never infer action type, decision state or ending from narrative text.
- Clients do not parse public tokens or internal IDs and do not copy scenario
  rules. A refreshed View replaces all earlier affordances.

All narrative and public copy is plain text. The public contract contains no
write endpoint for facts, clues, memory, rewards, clocks, endings or world
state. It contains no snapshot, job, proposal, Provider, receipt, memory-rule or
event-sequence DTO.

## Verification boundary

Contract tests enforce exact response keys, hidden-value scans, ACTIVE/ENDED
ending visibility, decision/free/continue modes, safe targets, shared Gateway
input contracts, ownership 404, `SNAPSHOT_INVALID`, read-only queries, OpenAPI
model exclusions and absence of scenario-ID branches. Browser and MySQL tests
use Scripted Providers; live DeepSeek remains opt-in and is not used here.

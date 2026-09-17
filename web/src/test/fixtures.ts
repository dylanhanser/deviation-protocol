import type {
  RunEntryOptions, NativeRunEntryResponse,
  ActionResponse,
  EligiblePlayerCharacterCollection,
  MinimalPlayerCharacterCreationRequest,
  PlayerMemoryProjection,
  PlayerCharacterSelfProjection,
  PlayerSessionView,
  PublicScenarioCatalog,
  RunEntryRequest,
  RunEntryResponse,
  SessionCreationResult,
} from "../api/schemas";
import { objectiveNames } from "../api/schemas";

export const runOptionsFixture: RunEntryOptions = {
  schema_version:"run-entry-options/v1", native_entry_available:true,
  profiles: [
    {id:"difficulty.silent-hunting-ground",label:"Extreme — Silent Hunting Ground",defaults:[95,10,95,90,90],ranges:[[80,100],[0,25],[80,100],[75,100],[75,100]]},
    {id:"difficulty.fragile-alliance",label:"Standard — Fragile Alliance",defaults:[60,45,65,60,60],ranges:[[40,75],[30,65],[45,80],[40,75],[40,75]]},
    {id:"difficulty.open-expedition",label:"Easier — Open Expedition",defaults:[25,70,35,30,35],ranges:[[10,40],[55,85],[20,50],[15,45],[20,50]]},
  ].map((p) => ({profile_ref:{profile_id:p.id,profile_version:1},label:p.label,
    defaults:Object.fromEntries(objectiveNames.map((n,i) => [n,p.defaults[i]])) as RunEntryOptions["profiles"][number]["defaults"],
    override_rules:objectiveNames.map((parameter,i) => ({parameter,minimum:p.ranges[i]![0]!,maximum:p.ranges[i]![1]!,step:5 as const}))})),
  entry_worlds:[{entry_world:{entry_world_id:"world.death_certificate",entry_world_version:1},scenario_id:"scenario.public-alpha",
    scenario_content_version:"public-alpha-1.0.0",title:"起始世界",hook:"已公开的场景说明。",
    eligible_profiles:["difficulty.silent-hunting-ground","difficulty.fragile-alliance","difficulty.open-expedition"].map((profile_id) => ({profile_id,profile_version:1}))}],
  presentation_options:{world_tone:["grim","balanced","heroic"],reality_boundary:["lawful","deviant","chaotic"],relationship_overlay:["off","veiled","charged"]},
};

export function nativeEntryFixture(): NativeRunEntryResponse {
  const profile = runOptionsFixture.profiles[2]!;
  return structuredClone({session_id:"session-public-1",scenario_id:"scenario.public-alpha",scenario_content_version:"public-alpha-1.0.0",
    run_context:{schema_version:"public-run-context/v1",run_id:"run.native",player_character:structuredClone(playerCharacterFixture),
      entry_world:runOptionsFixture.entry_worlds[0]!.entry_world,profile_ref:profile.profile_ref,objectives:profile.defaults,
      presentation:{world_tone:"balanced",reality_boundary:"lawful",relationship_overlay:"off"},resource_pressure_label:"Generous"}});
}

export const minimalPlayerCharacterCreationFixture: MinimalPlayerCharacterCreationRequest = {
  contract_version: "structured-player-character/v1",
  character_core: {},
  narration_preferences: {},
};

export const playerCharacterFixture: PlayerCharacterSelfProjection = {
  player_character_id: { value: "pc.public-alpha" },
  contract_version: "structured-player-character/v1",
  record_revision: { value: 1 },
  lifecycle: "active",
};

export const eligiblePlayerCharactersFixture: EligiblePlayerCharacterCollection = {
  eligible_player_characters: [playerCharacterFixture],
  truncated: false,
};

export const runEntryRequestFixture: RunEntryRequest = {
  player_character_id: playerCharacterFixture.player_character_id.value,
  expected_record_revision: playerCharacterFixture.record_revision.value,
  scenario_id: "scenario.public-alpha",
};

export const runEntryResponseFixture: RunEntryResponse = {
  run_id: "run.public-alpha",
  session_id: "session-public-1",
  scenario_id: runEntryRequestFixture.scenario_id,
  player_character: playerCharacterFixture,
};

export const scenarioCatalogFixture: PublicScenarioCatalog = {
  scenarios: [
    {
      scenario_id: "scenario.public-alpha",
      content_version: "public-alpha-1.0.0",
      title: "雾港回声",
      hook: "在封锁解除前确认灯塔传来的公开信号。",
      playable_characters: [
        {
          character_definition_id: "character.public.observer",
          display_name: "观测员",
          description: "擅长记录与辨别公开线索。",
        },
        {
          character_definition_id: "character.public.medic",
          display_name: "医务员",
          description: "擅长检查现场人员状态。",
        },
      ],
      default_character_definition_id: "character.public.observer",
    },
  ],
};

export const playerMemoryFixture: PlayerMemoryProjection = {
  projection_version: 2,
  complete: true,
  sync_status: "CURRENT",
  scenarios: [],
  npcs: [],
  significant_experiences: [],
  known_public_facts: [],
  total_scenario_records: 0,
  total_npc_records: 0,
  total_significant_experiences: 0,
  total_known_public_facts: 0,
  truncated: false,
};

const activeFrame = {
  frame_id: "frame.public-alpha.1",
  scenario_id: "scenario.public-alpha",
  phase_id: "phase.public.arrival",
  mode: "DECISION" as const,
  current_location_id: "location.public.harbor",
  must_render_facts: [],
  may_render_facts: [],
  visible_entities: ["npc.public.guide"],
  visible_clues: [],
  must_render_event_types: [],
  recent_verified_events: [],
  npc_knowledge: [],
  tone_hints: ["克制"],
  target_length: 120,
  min_length: 80,
  max_length: 180,
  decision_required: true,
  decision_id: "decision.public.bound-token",
  decision_reason: "PLAYER_DIRECT_RESPONSE" as const,
  suggested_actions: [
    {
      action_id: "choice.public.inspect-light",
      action_type: "choice",
      label_hint: "检查灯塔信号",
      target_ids: [],
    },
  ],
  stop_condition: "AWAIT_PLAYER" as const,
  player_visible_clocks: [
    { clock_id: "clock.public.tide", value: 2, maximum: 8 },
  ],
};

const metadata = {
  session_id: "session-public-1",
  phase: "AWAITING_ACTION",
  state_version: 0,
  content_version: "public-alpha-1.0.0",
  created_at: "2026-07-21T10:00:00Z",
  updated_at: "2026-07-21T10:00:00Z",
  character_definition_id: "character.public.observer",
  character_display_name: "观测员",
};

export const sessionCreationFixture: SessionCreationResult = {
  ...metadata,
  scenario_id: "scenario.public-alpha",
  narrative_frame: activeFrame,
};

export const activeViewFixture: PlayerSessionView = {
  metadata,
  narrative_frame: activeFrame,
  player_state: {
    session_id: metadata.session_id,
    phase: metadata.phase,
    state_version: metadata.state_version,
    content_version: metadata.content_version,
    player_id: "player.public-demo",
    character_definition_id: metadata.character_definition_id,
    attributes: [
      ["focus", 5],
      ["resolve", 4],
    ],
    resources: [{ resource_id: "stamina", current: 8, maximum: 10 }],
    wallet: [],
    inventory: [],
    equipped_items: [],
    skills: [],
    visible_npcs: [
      {
        npc_id: "npc.public.guide",
        npc_definition_id: "npc.definition.guide",
        display_name: "引航员",
      },
    ],
    quests: [],
    player_memory: playerMemoryFixture,
  },
  player_memory: playerMemoryFixture,
  presentation: {
    title: "雾港回声",
    scene_title: "封锁线外",
    scene_summary: "潮声覆盖了远处灯塔的规律闪光。",
  },
  action_affordances: {
    mode: "DECISION",
    actions: [],
    decision_id: "decision.public.bound-token",
    choices: [
      {
        action_type: "CHOOSE",
        choice_id: "choice.public.inspect-light",
        label: "检查灯塔信号",
        target_ids: [],
      },
    ],
  },
  scenario_status: "ACTIVE",
  ending_status: null,
  public_clocks: activeFrame.player_visible_clocks,
  recent_narrative_texts: ["雾中的灯塔连续闪了三次。"],
};

export function freeActionViewFixture(
  stateVersion = 1,
): PlayerSessionView {
  const freeFrame = {
    ...activeFrame,
    frame_id: `frame.public-alpha.free-${stateVersion}`,
    mode: "FLOW" as const,
    decision_required: false,
    decision_id: undefined,
    decision_reason: undefined,
    suggested_actions: [],
    stop_condition: "CONTINUE" as const,
  };
  return {
    ...activeViewFixture,
    metadata: {
      ...metadata,
      state_version: stateVersion,
      updated_at: "2026-07-21T10:05:00Z",
    },
    narrative_frame: freeFrame,
    player_state: {
      ...activeViewFixture.player_state,
      state_version: stateVersion,
    },
    action_affordances: {
      mode: "FREE_ACTIONS",
      actions: [
        {
          action_type: "CONTINUE",
          label: "继续",
          input_kind: "NONE",
          target_required: false,
          targets: [],
        },
        {
          action_type: "TALK",
          label: "交谈",
          input_kind: "DIALOGUE",
          max_input_length: 200,
          target_required: false,
          targets: [
            { target_id: "npc.public.guide", display_name: "引航员" },
          ],
        },
        ...(["CUSTOM", "EXPLORE", "OBSERVE", "MOVE"] as const).map(
          (actionType) => ({
            action_type: actionType,
            label: {
              CUSTOM: "自由行动",
              EXPLORE: "探索",
              OBSERVE: "观察",
              MOVE: "移动",
            }[actionType],
            input_kind: "DESCRIPTION" as const,
            max_input_length: 150,
            target_required: false,
            targets: [
              { target_id: "npc.public.guide", display_name: "引航员" },
            ],
          }),
        ),
      ],
      choices: [],
    },
    recent_narrative_texts: [
      ...activeViewFixture.recent_narrative_texts,
      `权威 View 已推进到版本 ${stateVersion}。`,
    ],
  };
}

export function synchronousActionResponseFixture(
  clientRequestId = "action-request-1",
  stateVersion = 1,
): ActionResponse {
  return {
    session_id: "session-public-1",
    client_request_id: clientRequestId,
    resolution_kind: "RESOLVED_LOCAL",
    result_code: "SCENARIO_AUTO_BEAT_ADVANCED",
    feedback_code: "SCENARIO_AUTO_BEAT_ADVANCED",
    feedback_parameters: {},
    resulting_state_version: stateVersion,
    state_changed: true,
    narrative_required: false,
    narrative_pending: false,
    narrative_frame: freeActionViewFixture(stateVersion).narrative_frame,
    narrative_text: "服务器完成了一个确定性推进。",
    narrative_status: null,
    local_query_result: null,
  };
}

export function pendingActionResponseFixture(
  clientRequestId = "action-request-1",
): ActionResponse {
  return {
    session_id: "session-public-1",
    client_request_id: clientRequestId,
    resolution_kind: "NARRATIVE_REQUIRED",
    result_code: "VALIDATED_INTENT_REQUIRES_NARRATIVE",
    feedback_code: "NARRATIVE_REQUIRED",
    feedback_parameters: {},
    resulting_state_version: 0,
    state_changed: false,
    narrative_required: true,
    narrative_pending: true,
    narrative_frame: freeActionViewFixture().narrative_frame,
    narrative_text: null,
    narrative_status: "PENDING",
    local_query_result: null,
  };
}

export function committedActionResponseFixture(
  clientRequestId = "action-request-1",
  stateVersion = 1,
): ActionResponse {
  return {
    session_id: "session-public-1",
    client_request_id: clientRequestId,
    resolution_kind: "NARRATIVE_COMMITTED",
    result_code: "NARRATIVE_OUTCOME_COMMITTED",
    feedback_code: "NARRATIVE_COMMITTED",
    feedback_parameters: {},
    resulting_state_version: stateVersion,
    state_changed: true,
    narrative_required: true,
    narrative_pending: false,
    narrative_frame: freeActionViewFixture(stateVersion).narrative_frame,
    narrative_text: "服务器接受了已验证的公开叙事结果。",
    narrative_status: "COMMITTED",
    local_query_result: null,
  };
}

export function endedViewFixture(
  endingStatus: "RESOLVED" | "FAILED" = "RESOLVED",
): PlayerSessionView {
  const endedFrame = {
    ...activeFrame,
    frame_id: "frame.public-alpha.ended",
    mode: "SETTLEMENT" as const,
    decision_required: false,
    decision_id: undefined,
    decision_reason: undefined,
    suggested_actions: [],
    stop_condition: "SCENARIO_ENDED" as const,
  };
  return {
    ...activeViewFixture,
    metadata: {
      ...metadata,
      phase: "ENDED",
      state_version: 7,
      updated_at: "2026-07-21T10:20:00Z",
    },
    narrative_frame: endedFrame,
    player_state: {
      ...activeViewFixture.player_state,
      phase: "ENDED",
      state_version: 7,
    },
    presentation: {
      ...activeViewFixture.presentation,
      scene_title: "潮汐落定",
      scene_summary: "灯塔信号已经得到公开确认。",
      ending: {
        title: endingStatus === "RESOLVED" ? "回声确认" : "信号沉没",
        summary:
          endingStatus === "RESOLVED"
            ? "港口记录保留了这次确认。"
            : "最后的公开信号未能得到确认。",
      },
    },
    action_affordances: {
      mode: "ENDED",
      actions: [],
      choices: [],
    },
    scenario_status: "ENDED",
    ending_status: endingStatus,
    ending_id:
      endingStatus === "RESOLVED"
        ? "ending.public.confirmed"
        : "ending.public.failed",
    recent_narrative_texts: [
      ...activeViewFixture.recent_narrative_texts,
      "信号被记录在公开航海日志中。",
    ],
  };
}

export function errorFixture(errorCode: string, message: string) {
  return { error: { error_code: errorCode, message } };
}

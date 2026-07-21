import type {
  PlayerMemoryProjection,
  PlayerSessionView,
  PublicScenarioCatalog,
  SessionCreationResult,
} from "../api/schemas";

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

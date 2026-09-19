import { z } from "zod";

const safeIdPattern = /^[A-Za-z0-9][A-Za-z0-9_.:-]*$/;
const safeId64Schema = z.string().min(1).max(64).regex(safeIdPattern);
const safeId128Schema = z.string().min(1).max(128).regex(safeIdPattern);
const positiveSafeIntegerSchema = z.number().int().positive().safe();
const plainStringSchema = z.string();
const nonNegativeIntegerSchema = z.number().int().nonnegative();
export const nativeRunExitRequestSchema = z.object({
  expected_run_state_version: positiveSafeIntegerSchema,
  expected_session_state_version: nonNegativeIntegerSchema.safe(),
}).strict();
export const nativeRunStatusSchema = z.object({
  schema_version: z.literal("native-run-status/v1"),
  session_id: safeId64Schema,
  run_id: safeId128Schema,
  run_state_version: positiveSafeIntegerSchema,
  session_state_version: nonNegativeIntegerSchema.safe(),
  lifecycle_status: z.enum(["active", "terminated"]),
  can_exit: z.boolean(),
}).strict().refine((s) => s.lifecycle_status === "active"
  ? [3, 4, 5].includes(s.run_state_version) : [4, 5, 6].includes(s.run_state_version) && !s.can_exit);
export type NativeRunStatus = z.infer<typeof nativeRunStatusSchema>;
const dateTimeSchema = z.iso.datetime({ offset: true });

function unicodeCodePointLength(value: string): number {
  return Array.from(value).length;
}

const codePointBoundedStringSchema = (
  minimum: number,
  maximum: number,
  fieldName: string,
) =>
  z.string().superRefine((value, context) => {
    const length = unicodeCodePointLength(value);
    if (length < minimum) {
      context.addIssue({
        code: "custom",
        message: `${fieldName} must contain at least ${minimum} Unicode code point`,
      });
    }
    if (length > maximum) {
      context.addIssue({
        code: "custom",
        message: `${fieldName} exceeds ${maximum} Unicode code points`,
      });
    }
  });

export const publicPlayableCharacterSchema = z.object({
  character_definition_id: plainStringSchema,
  display_name: plainStringSchema,
  description: plainStringSchema,
});

export const publicScenarioDescriptionSchema = z
  .object({
    scenario_id: plainStringSchema,
    content_version: plainStringSchema,
    title: plainStringSchema,
    hook: plainStringSchema,
    playable_characters: z.array(publicPlayableCharacterSchema).max(16),
    default_character_definition_id: plainStringSchema,
  })
  .superRefine((scenario, context) => {
    const roleIds = new Set(
      scenario.playable_characters.map((role) => role.character_definition_id),
    );
    if (!roleIds.has(scenario.default_character_definition_id)) {
      context.addIssue({
        code: "custom",
        path: ["default_character_definition_id"],
        message: "default character is not present in playable characters",
      });
    }
  });

export const publicScenarioCatalogSchema = z.object({
  scenarios: z.array(publicScenarioDescriptionSchema).max(32),
});

export const idempotencyKeySchema = safeId128Schema;

export const minimalPlayerCharacterCreationRequestSchema = z
  .object({
    contract_version: z.literal("structured-player-character/v1"),
    character_core: z.object({}).strict(),
    narration_preferences: z.object({}).strict(),
  })
  .strict();

export const playerCharacterSelfProjectionSchema = z.object({
  player_character_id: z.object({ value: safeId128Schema }),
  contract_version: z.literal("structured-player-character/v1"),
  record_revision: z.object({ value: positiveSafeIntegerSchema }),
  lifecycle: z.enum(["active", "retired", "deceased"]),
});

export const playerCharacterCreationResultSchema =
  playerCharacterSelfProjectionSchema.superRefine((projection, context) => {
    if (projection.record_revision.value !== 1) {
      context.addIssue({
        code: "custom",
        path: ["record_revision", "value"],
        message: "creation result revision must be 1",
      });
    }
    if (projection.lifecycle !== "active") {
      context.addIssue({
        code: "custom",
        path: ["lifecycle"],
        message: "creation result lifecycle must be active",
      });
    }
  });

export const eligiblePlayerCharacterCollectionSchema = z
  .object({
    eligible_player_characters: z
      .array(playerCharacterSelfProjectionSchema)
      .max(32),
    truncated: z.boolean(),
  })
  .superRefine((collection, context) => {
    if (
      collection.truncated &&
      collection.eligible_player_characters.length !== 32
    ) {
      context.addIssue({
        code: "custom",
        path: ["truncated"],
        message: "truncated eligible collection must contain 32 items",
      });
    }
    collection.eligible_player_characters.forEach((projection, index) => {
      if (projection.lifecycle !== "active") {
        context.addIssue({
          code: "custom",
          path: ["eligible_player_characters", index, "lifecycle"],
          message: "eligible Player Character lifecycle must be active",
        });
      }
      const previous = collection.eligible_player_characters[index - 1];
      if (
        previous !== undefined &&
        previous.player_character_id.value >=
          projection.player_character_id.value
      ) {
        context.addIssue({
          code: "custom",
          path: ["eligible_player_characters", index, "player_character_id"],
          message: "eligible Player Characters must use authoritative ID order",
        });
      }
    });
  });

export const runEntryRequestSchema = z
  .object({
    player_character_id: safeId128Schema,
    expected_record_revision: positiveSafeIntegerSchema,
    scenario_id: safeId128Schema,
  })
  .strict();

export const runEntryResponseSchema = z.object({
  run_id: safeId128Schema,
  session_id: safeId64Schema,
  scenario_id: safeId128Schema,
  player_character: playerCharacterSelfProjectionSchema,
});

export const createSessionRequestSchema = z
  .object({
    client_request_id: safeId64Schema,
    character_definition_id: safeId128Schema,
    scenario_id: safeId128Schema,
  })
  .strict();

export const sessionPathIdSchema = safeId64Schema;
export const requestPathIdSchema = safeId64Schema;

const renderableFactSchema = z.object({
  fact_id: safeId128Schema,
  value: z.json(),
});

const npcKnowledgeFrameSchema = z.object({
  npc_id: safeId128Schema,
  npc_definition_id: safeId128Schema,
  known_facts: z.array(renderableFactSchema).default([]),
});

const verifiedEventFrameSchema = z.object({
  event_id: safeId128Schema,
  event_type: safeId128Schema,
});

export const suggestedActionSchema = z.object({
  action_id: safeId128Schema,
  action_type: safeId128Schema,
  label_hint: codePointBoundedStringSchema(
    1,
    160,
    "narrative action label",
  ),
  target_ids: z.array(safeId128Schema).default([]),
});

const allowedCustomActionConstraintsSchema = z.object({
  allowed_action_types: z.array(safeId128Schema),
  max_description_length: z.number().int().min(1).max(2_000),
  must_target_visible_entity: z.boolean(),
});

export const visibleClockSchema = z
  .object({
    clock_id: safeId128Schema,
    value: nonNegativeIntegerSchema,
    maximum: z.number().int().positive(),
  })
  .superRefine((clock, context) => {
    if (clock.value > clock.maximum) {
      context.addIssue({
        code: "custom",
        path: ["value"],
        message: "clock value exceeds its maximum",
      });
    }
  });

const decisionReasonSchema = z.enum([
  "IRREVERSIBLE_CONSEQUENCE",
  "RESOURCE_COMMITMENT",
  "ROUTE_DIVERGENCE",
  "NPC_COMMITMENT",
  "CORE_REVELATION",
  "TIME_CRITICAL",
  "MORAL_CONFLICT",
  "PLAYER_DIRECT_RESPONSE",
]);

export const narrativeFrameSchema = z
  .object({
    frame_id: safeId128Schema,
    scenario_id: safeId128Schema,
    phase_id: safeId128Schema,
    mode: z.enum(["FLOW", "DECISION", "RAPID_DECISION", "SETTLEMENT"]),
    current_location_id: safeId128Schema,
    must_render_facts: z.array(renderableFactSchema).max(256).default([]),
    may_render_facts: z.array(renderableFactSchema).max(256).default([]),
    visible_entities: z.array(safeId128Schema).max(128).default([]),
    visible_clues: z.array(safeId128Schema).max(512).default([]),
    must_render_event_types: z.array(safeId128Schema).max(128).default([]),
    recent_verified_events: z
      .array(verifiedEventFrameSchema)
      .max(128)
      .default([]),
    npc_knowledge: z.array(npcKnowledgeFrameSchema).max(128).default([]),
    tone_hints: z.array(z.string()).max(16).default([]),
    target_length: z.number().int().positive(),
    min_length: z.number().int().positive(),
    max_length: z.number().int().positive(),
    decision_required: z.boolean(),
    decision_id: safeId128Schema.nullish(),
    decision_reason: decisionReasonSchema.nullish(),
    suggested_actions: z.array(suggestedActionSchema).max(32).default([]),
    allowed_custom_action_constraints:
      allowedCustomActionConstraintsSchema.nullish(),
    stop_condition: z.enum(["CONTINUE", "AWAIT_PLAYER", "SCENARIO_ENDED"]),
    player_visible_clocks: z.array(visibleClockSchema).max(32).default([]),
  })
  .superRefine((frame, context) => {
    const factIds = [
      ...frame.must_render_facts,
      ...frame.may_render_facts,
    ].map((fact) => fact.fact_id);
    if (factIds.length !== new Set(factIds).size) {
      context.addIssue({
        code: "custom",
        path: ["must_render_facts"],
        message: "narrative frame repeats a renderable fact",
      });
    }
    const actionIds = frame.suggested_actions.map((action) => action.action_id);
    if (actionIds.length !== new Set(actionIds).size) {
      context.addIssue({
        code: "custom",
        path: ["suggested_actions"],
        message: "narrative frame repeats a suggested action",
      });
    }
    if (
      frame.min_length > frame.target_length ||
      frame.target_length > frame.max_length
    ) {
      context.addIssue({
        code: "custom",
        path: ["target_length"],
        message: "narrative length bounds are inconsistent",
      });
    }
    if (frame.decision_required) {
      if (
        frame.decision_id == null ||
        frame.decision_reason == null ||
        frame.suggested_actions.length === 0 ||
        frame.stop_condition !== "AWAIT_PLAYER"
      ) {
        context.addIssue({
          code: "custom",
          path: ["decision_required"],
          message: "decision frame is incomplete",
        });
      }
    } else if (
      frame.decision_id != null ||
      frame.decision_reason != null ||
      frame.suggested_actions.length > 0 ||
      frame.allowed_custom_action_constraints != null
    ) {
      context.addIssue({
        code: "custom",
        path: ["decision_required"],
        message: "flow frame contains a decision payload",
      });
    }
  });

const strictRenderableFactResponseSchema = renderableFactSchema.strict();
const strictNpcKnowledgeFrameResponseSchema = npcKnowledgeFrameSchema
  .extend({
    known_facts: z.array(strictRenderableFactResponseSchema).default([]),
  })
  .strict();
const strictVerifiedEventFrameResponseSchema =
  verifiedEventFrameSchema.strict();
const strictSuggestedActionResponseSchema = suggestedActionSchema.strict();
const strictAllowedCustomActionConstraintsResponseSchema =
  allowedCustomActionConstraintsSchema.strict();
const strictVisibleClockResponseSchema = visibleClockSchema.strict();

const strictNarrativeFrameResponseSchema = narrativeFrameSchema
  .safeExtend({
    must_render_facts: z
      .array(strictRenderableFactResponseSchema)
      .max(256)
      .default([]),
    may_render_facts: z
      .array(strictRenderableFactResponseSchema)
      .max(256)
      .default([]),
    recent_verified_events: z
      .array(strictVerifiedEventFrameResponseSchema)
      .max(128)
      .default([]),
    npc_knowledge: z
      .array(strictNpcKnowledgeFrameResponseSchema)
      .max(128)
      .default([]),
    suggested_actions: z
      .array(strictSuggestedActionResponseSchema)
      .max(32)
      .default([]),
    allowed_custom_action_constraints:
      strictAllowedCustomActionConstraintsResponseSchema.nullish(),
    player_visible_clocks: z
      .array(strictVisibleClockResponseSchema)
      .max(32)
      .default([]),
  })
  .strict();

export const sessionMetadataSchema = z.object({
  session_id: plainStringSchema,
  phase: plainStringSchema,
  state_version: nonNegativeIntegerSchema,
  content_version: plainStringSchema,
  created_at: dateTimeSchema,
  updated_at: dateTimeSchema,
  character_definition_id: plainStringSchema,
  character_display_name: plainStringSchema,
});

export const sessionCreationResultSchema = sessionMetadataSchema.extend({
  scenario_id: plainStringSchema,
  narrative_frame: narrativeFrameSchema,
});

const scenarioMemoryProjectionSchema = z
  .object({
    scenario_id: safeId128Schema,
    scenario_content_version: safeId128Schema,
    status: z.enum(["STARTED", "COMPLETED"]),
    ending_id: safeId128Schema.nullish(),
    milestone_refs: z
      .array(
        z.enum([
          "STARTED",
          "IMPORTANT_FACT_CONFIRMED",
          "COMPLETED",
          "ENDING_CONFIRMED",
        ]),
      )
      .max(32)
      .default([]),
    known_public_fact_refs: z.array(safeId128Schema).max(32).default([]),
  })
  .superRefine((record, context) => {
    if (record.status === "STARTED" && record.ending_id != null) {
      context.addIssue({
        code: "custom",
        path: ["ending_id"],
        message: "started scenario memory cannot contain an ending",
      });
    }
  });

const npcMemoryProjectionSchema = z.object({
  subject_key: safeId128Schema,
  scenario_id: safeId128Schema,
  npc_definition_id: safeId128Schema,
  interaction_milestones: z
    .array(
      z.enum([
        "FIRST_ENCOUNTER",
        "COOPERATED",
        "CONFLICT_OCCURRED",
        "ASSISTED_PLAYER",
        "TRUST_CONFIRMED",
      ]),
    )
    .max(32)
    .default([]),
  known_public_fact_refs: z.array(safeId128Schema).max(32).default([]),
});

const significantExperienceProjectionSchema = z.object({
  entry_id: safeId128Schema,
  scenario_id: safeId128Schema,
  category: z.enum([
    "SCENARIO_BEGIN",
    "SCENARIO_COMPLETION",
    "IMPORTANT_NPC_ENCOUNTER",
    "NPC_RELATIONSHIP_MILESTONE",
    "IMPORTANT_PUBLIC_DISCOVERY",
  ]),
  summary: z.enum([
    "SCENARIO_BEGAN",
    "SCENARIO_RESOLVED",
    "IMPORTANT_NPC_MET",
    "NPC_RELATIONSHIP_CHANGED",
    "CRITICAL_PUBLIC_FACT_LEARNED",
  ]),
  subject_refs: z.array(safeId128Schema).max(8).default([]),
  public_fact_refs: z.array(safeId128Schema).max(8).default([]),
});

const knownPublicFactProjectionSchema = z.object({
  scenario_id: safeId128Schema,
  fact_ref: safeId128Schema,
});

export const playerMemoryProjectionSchema = z
  .object({
    projection_version: z.literal(2).default(2),
    complete: z.boolean().default(true),
    sync_status: z.enum(["CURRENT", "REBUILD_REQUIRED"]).default("CURRENT"),
    scenarios: z.array(scenarioMemoryProjectionSchema).max(16).default([]),
    npcs: z.array(npcMemoryProjectionSchema).max(32).default([]),
    significant_experiences: z
      .array(significantExperienceProjectionSchema)
      .max(64)
      .default([]),
    known_public_facts: z
      .array(knownPublicFactProjectionSchema)
      .max(128)
      .default([]),
    total_scenario_records: nonNegativeIntegerSchema.default(0),
    total_npc_records: nonNegativeIntegerSchema.default(0),
    total_significant_experiences: nonNegativeIntegerSchema.default(0),
    total_known_public_facts: nonNegativeIntegerSchema.default(0),
    truncated: z.boolean().default(false),
  })
  .superRefine((memory, context) => {
    const totalsAndLengths = [
      [memory.total_scenario_records, memory.scenarios.length],
      [memory.total_npc_records, memory.npcs.length],
      [
        memory.total_significant_experiences,
        memory.significant_experiences.length,
      ],
      [memory.total_known_public_facts, memory.known_public_facts.length],
    ] as const;
    if (totalsAndLengths.some(([total, length]) => total < length)) {
      context.addIssue({
        code: "custom",
        message: "memory total is smaller than its public records",
      });
    }
    const hasOmittedRecords = totalsAndLengths.some(
      ([total, length]) => total > length,
    );
    if (hasOmittedRecords !== memory.truncated) {
      context.addIssue({
        code: "custom",
        path: ["truncated"],
        message: "memory truncation marker is inconsistent",
      });
    }
    if (memory.complete !== (memory.sync_status === "CURRENT")) {
      context.addIssue({
        code: "custom",
        path: ["complete"],
        message: "memory completeness marker is inconsistent",
      });
    }
  });

const publicResourceSchema = z.object({
  resource_id: plainStringSchema,
  current: nonNegativeIntegerSchema,
  maximum: nonNegativeIntegerSchema,
});

const publicInventoryItemSchema = z.object({
  item_instance_id: plainStringSchema,
  item_definition_id: plainStringSchema,
  display_name: plainStringSchema,
  quantity: z.number().int().positive(),
  durability: nonNegativeIntegerSchema.nullish(),
  charges: nonNegativeIntegerSchema.nullish(),
  equipped_slot: z.string().nullish(),
});

const publicSkillSchema = z.object({
  skill_definition_id: plainStringSchema,
  display_name: plainStringSchema,
  level: z.number().int().positive(),
  proficiency: nonNegativeIntegerSchema,
  cooldown_remaining: nonNegativeIntegerSchema,
  uses: nonNegativeIntegerSchema,
});

const publicNpcSchema = z.object({
  npc_id: plainStringSchema,
  npc_definition_id: plainStringSchema,
  display_name: plainStringSchema,
});

const publicQuestSchema = z.object({
  quest_definition_id: plainStringSchema,
  status: plainStringSchema,
});

export const playerVisibleStateProjectionSchema = z.object({
  session_id: plainStringSchema,
  phase: plainStringSchema,
  state_version: nonNegativeIntegerSchema,
  content_version: plainStringSchema,
  player_id: plainStringSchema,
  character_definition_id: plainStringSchema,
  attributes: z.array(z.tuple([z.string(), z.number().int()])),
  resources: z.array(publicResourceSchema),
  wallet: z.array(z.tuple([z.string(), z.number().int()])),
  inventory: z.array(publicInventoryItemSchema),
  equipped_items: z.array(publicInventoryItemSchema),
  skills: z.array(publicSkillSchema),
  visible_npcs: z.array(publicNpcSchema).default([]),
  quests: z.array(publicQuestSchema).default([]),
  player_memory: playerMemoryProjectionSchema.default(() =>
    playerMemoryProjectionSchema.parse({}),
  ),
});

const publicEndingPresentationSchema = z.object({
  title: plainStringSchema,
  summary: plainStringSchema,
});

export const publicScenarioPresentationSchema = z.object({
  title: plainStringSchema,
  scene_title: plainStringSchema,
  scene_summary: plainStringSchema,
  ending: publicEndingPresentationSchema.nullish(),
});

export const publicPlayableActionTypeSchema = z.enum([
  "CONTINUE",
  "TALK",
  "CUSTOM",
  "EXPLORE",
  "OBSERVE",
  "MOVE",
]);

const publicActionTargetSchema = z.object({
  target_id: plainStringSchema,
  display_name: plainStringSchema,
});

const publicActionAffordanceSchema = z
  .object({
    action_type: publicPlayableActionTypeSchema,
    label: plainStringSchema,
    input_kind: z.enum(["NONE", "DESCRIPTION", "DIALOGUE"]),
    max_input_length: z.number().int().min(1).max(2_000).nullish(),
    target_required: z.boolean(),
    targets: z.array(publicActionTargetSchema).max(128),
  })
  .superRefine((action, context) => {
    const expectedInput =
      action.action_type === "CONTINUE"
        ? { inputKind: "NONE", maxLength: null }
        : action.action_type === "TALK"
          ? { inputKind: "DIALOGUE", maxLength: 200 }
          : { inputKind: "DESCRIPTION", maxLength: 150 };
    if (
      action.input_kind !== expectedInput.inputKind ||
      (action.max_input_length ?? null) !== expectedInput.maxLength
    ) {
      context.addIssue({
        code: "custom",
        path: ["input_kind"],
        message: "action input contract does not match its action type",
      });
    }
    if (action.target_required) {
      context.addIssue({
        code: "custom",
        path: ["target_required"],
        message: "current public actions use optional targets",
      });
    }
    if (action.action_type === "CONTINUE" && action.targets.length > 0) {
      context.addIssue({
        code: "custom",
        path: ["targets"],
        message: "CONTINUE cannot advertise targets",
      });
    }
    const targetIds = action.targets.map((target) => target.target_id);
    if (targetIds.length !== new Set(targetIds).size) {
      context.addIssue({
        code: "custom",
        path: ["targets"],
        message: "action target IDs must be unique",
      });
    }
  });

const publicDecisionChoiceSchema = z.object({
  action_type: z.literal("CHOOSE"),
  choice_id: plainStringSchema,
  label: plainStringSchema,
  target_ids: z.array(plainStringSchema).max(16),
});

const publicSuggestedActionSubmissionSchema = z
  .object({
    turn_id: safeId64Schema,
    client_request_id: safeId64Schema,
    action_type: z.literal("CUSTOM"),
    description: z.string().min(1).max(150),
  })
  .strict();

export const publicSuggestedActionSchema = z
  .object({
    suggestion_id: safeId128Schema,
    ordinal: z.number().int().min(0).max(2),
    label: z.string().min(1).max(150),
    description: z.string().min(1).max(150),
    submission: publicSuggestedActionSubmissionSchema,
  })
  .strict()
  .superRefine((suggestion, context) => {
    if (
      suggestion.label !== suggestion.description ||
      suggestion.description !== suggestion.submission.description
    ) {
      context.addIssue({
        code: "custom",
        path: ["description"],
        message: "dynamic suggestion text copies do not match",
      });
    }
  });

export const publicActionAffordanceSetSchema = z
  .object({
    mode: z.enum(["FREE_ACTIONS", "DECISION", "ENDED"]),
    actions: z.array(publicActionAffordanceSchema).max(16),
    decision_id: z.string().nullish(),
    choices: z.array(publicDecisionChoiceSchema).max(32),
    suggested_actions: z
      .array(publicSuggestedActionSchema)
      .length(3)
      .optional(),
  })
  .superRefine((set, context) => {
    const isValid =
      set.mode === "DECISION"
          ? set.decision_id != null &&
          set.choices.length > 0 &&
          set.actions.length === 0 &&
          set.suggested_actions === undefined
        : set.mode === "FREE_ACTIONS"
          ? set.decision_id == null && set.choices.length === 0
          : set.decision_id == null &&
            set.choices.length === 0 &&
            set.actions.length === 0 &&
            set.suggested_actions === undefined;
    if (!isValid) {
      context.addIssue({
        code: "custom",
        path: ["mode"],
        message: "action affordance mode has an invalid shape",
      });
    }
    const actionTypes = set.actions.map((action) => action.action_type);
    if (actionTypes.length !== new Set(actionTypes).size) {
      context.addIssue({
        code: "custom",
        path: ["actions"],
        message: "action affordances repeat an action type",
      });
    }
    const choiceIds = set.choices.map((choice) => choice.choice_id);
    if (choiceIds.length !== new Set(choiceIds).size) {
      context.addIssue({
        code: "custom",
        path: ["choices"],
        message: "decision affordances repeat a choice ID",
      });
    }
    if (set.suggested_actions !== undefined) {
      const suggestions = set.suggested_actions;
      const validDynamicShape =
        set.mode === "FREE_ACTIONS" &&
        set.actions.length === 1 &&
        set.actions[0]?.action_type === "CUSTOM" &&
        suggestions.map((item) => item.ordinal).join(",") === "0,1,2" &&
        new Set(suggestions.map((item) => item.suggestion_id)).size === 3 &&
        new Set(suggestions.map((item) => item.submission.turn_id)).size === 3 &&
        new Set(suggestions.map((item) => item.submission.client_request_id)).size === 3 &&
        new Set(suggestions.map((item) => item.description)).size === 3;
      if (!validDynamicShape) {
        context.addIssue({
          code: "custom",
          path: ["suggested_actions"],
          message: "dynamic suggestion affordances have an invalid shape",
        });
      }
    }
  });

const playerActionTextSchema = (maximum: number) =>
  z
    .string()
    .refine((value) => !/[\p{Cc}\p{Cf}]/u.test(value), {
      message: "action text contains a Unicode control character",
    })
    .transform((value) => value.trim())
    .pipe(
      z
        .string()
        .min(1)
        .refine((value) => unicodeCodePointLength(value) <= maximum, {
          message: `action text exceeds ${maximum} Unicode characters`,
        }),
    );

const actionRequestIdentityShape = {
  turn_id: safeId64Schema,
  client_request_id: safeId64Schema,
};

const optionalTargetIdsSchema = z.array(safeId128Schema).max(16).optional();

export const actionRequestSchema = z.union([
  z
    .object({
      ...actionRequestIdentityShape,
      action_type: z.literal("CONTINUE"),
    })
    .strict(),
  z
    .object({
      ...actionRequestIdentityShape,
      action_type: z.literal("CHOOSE"),
      decision_id: safeId128Schema,
      choice_id: safeId128Schema,
    })
    .strict(),
  z
    .object({
      ...actionRequestIdentityShape,
      action_type: z.literal("TALK"),
      dialogue: playerActionTextSchema(200),
      target_ids: optionalTargetIdsSchema,
    })
    .strict(),
  z
    .object({
      ...actionRequestIdentityShape,
      action_type: z.enum(["CUSTOM", "EXPLORE", "OBSERVE", "MOVE"]),
      description: playerActionTextSchema(150),
      target_ids: optionalTargetIdsSchema,
    })
    .strict(),
]);

const jsonValueSchema = z.json();
type JsonValue = z.infer<typeof jsonValueSchema>;
const jsonObjectSchema = z.record(z.string(), jsonValueSchema);

function jsonValuesEqual(left: JsonValue, right: JsonValue): boolean {
  if (left === right) {
    return true;
  }
  if (Array.isArray(left) || Array.isArray(right)) {
    return (
      Array.isArray(left) &&
      Array.isArray(right) &&
      left.length === right.length &&
      left.every((value, index) => jsonValuesEqual(value, right[index]!))
    );
  }
  if (
    left === null ||
    right === null ||
    typeof left !== "object" ||
    typeof right !== "object"
  ) {
    return false;
  }
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  return (
    leftKeys.length === rightKeys.length &&
    leftKeys.every(
      (key) =>
        Object.prototype.hasOwnProperty.call(right, key) &&
        jsonValuesEqual(left[key]!, right[key]!),
    )
  );
}

export const actionResponseSchema = z
  .object({
    session_id: safeId64Schema,
    client_request_id: safeId64Schema,
    resolution_kind: z.enum([
      "RESOLVED_LOCAL",
      "REJECTED_LOCAL",
      "NARRATIVE_REQUIRED",
      "NARRATIVE_COMMITTED",
    ]),
    result_code: plainStringSchema,
    feedback_code: plainStringSchema,
    feedback_parameters: jsonObjectSchema,
    resulting_state_version: nonNegativeIntegerSchema,
    state_changed: z.boolean(),
    narrative_required: z.boolean(),
    narrative_pending: z.boolean(),
    narrative_frame: strictNarrativeFrameResponseSchema.nullable(),
    narrative_text: codePointBoundedStringSchema(
      1,
      10_000,
      "narrative text",
    ).nullable(),
    narrative_status: z.enum(["PENDING", "COMMITTED"]).nullable(),
    local_query_result: jsonObjectSchema.nullable(),
  })
  .strict()
  .superRefine((response, context) => {
    const isNarrative =
      response.resolution_kind === "NARRATIVE_REQUIRED" ||
      response.resolution_kind === "NARRATIVE_COMMITTED";
    const isPending = response.resolution_kind === "NARRATIVE_REQUIRED";
    if (
      response.narrative_required !== isNarrative ||
      response.narrative_pending !== isPending
    ) {
      context.addIssue({
        code: "custom",
        path: ["narrative_pending"],
        message: "narrative flags do not match resolution_kind",
      });
    }
    if (
      response.state_changed &&
      ![
        "RESOLVED_LOCAL",
        "NARRATIVE_COMMITTED",
      ].includes(response.resolution_kind)
    ) {
      context.addIssue({
        code: "custom",
        path: ["state_changed"],
        message: "only a committed resolution may change state",
      });
    }
    if (isNarrative) {
      const expectedStatus = isPending ? "PENDING" : "COMMITTED";
      if (
        response.narrative_status !== expectedStatus ||
        (response.narrative_text !== null) !==
          (response.resolution_kind === "NARRATIVE_COMMITTED")
      ) {
        context.addIssue({
          code: "custom",
          path: ["narrative_status"],
          message: "narrative payload does not match resolution_kind",
        });
      }
    } else if (
      response.narrative_status !== null ||
      (response.narrative_text !== null &&
        !(
          response.resolution_kind === "RESOLVED_LOCAL" &&
          response.state_changed
        ))
    ) {
      context.addIssue({
        code: "custom",
        path: ["narrative_status"],
        message: "non-narrative response carries an invalid narrative payload",
      });
    }
    const isLocalQuery =
      response.resolution_kind === "RESOLVED_LOCAL" &&
      !response.state_changed;
    if (
      (response.local_query_result !== null) !== isLocalQuery ||
      (isLocalQuery &&
        !jsonValuesEqual(
          response.local_query_result,
          response.feedback_parameters,
        ))
    ) {
      context.addIssue({
        code: "custom",
        path: ["local_query_result"],
        message: "local query result has an invalid shape",
      });
    }
  });

const requestStatusIdentityShape = {
  session_id: safeId64Schema,
  client_request_id: safeId64Schema,
};

export const narrativeRequestStatusResponseSchema = z
  .discriminatedUnion("status", [
    z
      .object({
        ...requestStatusIdentityShape,
        status: z.literal("PENDING"),
        client_action: z.literal("POLL_SAME_REQUEST"),
        error_code: z.null(),
        retry_after_seconds: z.number().int().min(1).max(60),
        response: z.null(),
      })
      .strict(),
    z
      .object({
        ...requestStatusIdentityShape,
        status: z.literal("COMMITTED"),
        client_action: z.literal("RESPONSE_AVAILABLE"),
        error_code: z.null(),
        retry_after_seconds: z.null(),
        response: actionResponseSchema,
      })
      .strict(),
    z
      .object({
        ...requestStatusIdentityShape,
        status: z.literal("STALE"),
        client_action: z.literal("REFRESH_VIEW"),
        error_code: z.literal("NARRATIVE_REQUEST_STALE"),
        retry_after_seconds: z.null(),
        response: z.null(),
      })
      .strict(),
    z
      .object({
        ...requestStatusIdentityShape,
        status: z.literal("OUTCOME_UNKNOWN"),
        client_action: z.literal("DO_NOT_RETRY"),
        error_code: z.literal("NARRATIVE_OUTCOME_UNKNOWN"),
        retry_after_seconds: z.null(),
        response: z.null(),
      })
      .strict(),
    z
      .object({
        ...requestStatusIdentityShape,
        status: z.literal("FAILED"),
        client_action: z.literal("DO_NOT_RETRY"),
        error_code: z.literal("NARRATIVE_REQUEST_FAILED"),
        retry_after_seconds: z.null(),
        response: z.null(),
      })
      .strict(),
  ])
  .superRefine((status, context) => {
    if (
      status.status === "COMMITTED" &&
      (status.response.session_id !== status.session_id ||
        status.response.client_request_id !== status.client_request_id)
    ) {
      context.addIssue({
        code: "custom",
        path: ["response"],
        message: "committed response does not match request status identity",
      });
    }
  });

export const objectiveNames = ["resource_pressure", "social_trust", "consequence_severity", "information_opacity", "conflict_intensity"] as const;
const objectiveValue = z.number().int().safe().min(0).max(100).multipleOf(5);
export const fiveObjectivesSchema = z.strictObject({
  resource_pressure: objectiveValue, social_trust: objectiveValue, consequence_severity: objectiveValue,
  information_opacity: objectiveValue, conflict_intensity: objectiveValue,
});
export const publicProfileRefSchema = z.strictObject({ profile_id: safeId128Schema, profile_version: positiveSafeIntegerSchema });
export const publicWorldRefSchema = z.strictObject({ entry_world_id: safeId128Schema, entry_world_version: positiveSafeIntegerSchema });
export const runPresentationSchema = z.strictObject({
  world_tone: z.enum(["grim", "balanced", "heroic"]), reality_boundary: z.enum(["lawful", "deviant", "chaotic"]),
  relationship_overlay: z.enum(["off", "veiled", "charged"]),
});
export const publicNativeRunContextSchema = z.strictObject({
  schema_version: z.literal("public-run-context/v1"), run_id: safeId128Schema,
  player_character: playerCharacterSelfProjectionSchema.extend({
    player_character_id: z.strictObject({ value: safeId128Schema }),
    record_revision: z.strictObject({ value: positiveSafeIntegerSchema }),
  }).strict(),
  entry_world: publicWorldRefSchema, profile_ref: publicProfileRefSchema, objectives: fiveObjectivesSchema,
  presentation: runPresentationSchema, resource_pressure_label: z.enum(["Generous", "Fluid", "Scarce"]),
}).refine((value) => value.player_character.lifecycle === "active" && value.resource_pressure_label ===
  (value.objectives.resource_pressure <= 30 ? "Generous" : value.objectives.resource_pressure <= 65 ? "Fluid" : "Scarce"));
export const publicRunProfileSchema = z.strictObject({
  profile_ref: publicProfileRefSchema, label: codePointBoundedStringSchema(1, 128, "profile label"), defaults: fiveObjectivesSchema,
  override_rules: z.array(z.strictObject({ parameter: z.enum(objectiveNames), minimum: objectiveValue,
    maximum: objectiveValue, step: z.literal(5) })).length(5),
}).refine((p) => p.override_rules.every((r, i) => r.parameter === objectiveNames[i] && r.minimum <= p.defaults[r.parameter] && p.defaults[r.parameter] <= r.maximum));
export const publicEntryWorldSchema = z.strictObject({
  entry_world: publicWorldRefSchema, scenario_id: safeId128Schema,
  scenario_content_version: z.string().min(1).max(32).regex(safeIdPattern),
  title: codePointBoundedStringSchema(1,120,"world title"), hook: codePointBoundedStringSchema(1,300,"world hook"),
  eligible_profiles: z.array(publicProfileRefSchema).length(3),
});
export const runEntryOptionsSchema = z.strictObject({
  schema_version: z.literal("run-entry-options/v1"), native_entry_available: z.boolean(),
  profiles: z.array(publicRunProfileSchema).max(3), entry_worlds: z.array(publicEntryWorldSchema).max(1),
  presentation_options: z.strictObject({
    world_tone: z.tuple([z.literal("grim"), z.literal("balanced"), z.literal("heroic")]),
    reality_boundary: z.tuple([z.literal("lawful"), z.literal("deviant"), z.literal("chaotic")]),
    relationship_overlay: z.tuple([z.literal("off"), z.literal("veiled"), z.literal("charged")]),
  }),
}).refine((c) => c.native_entry_available ? c.profiles.length === 3 && c.entry_worlds.length === 1 &&
  new Set(c.profiles.map((p) => JSON.stringify(p.profile_ref))).size === 3 &&
  c.entry_worlds.every((w) => w.eligible_profiles.every((p,i) => p.profile_id === c.profiles[i]?.profile_ref.profile_id && p.profile_version === c.profiles[i]?.profile_ref.profile_version))
  : c.profiles.length === 0 && c.entry_worlds.length === 0);
export const nativeRunEntryRequestSchema = z.strictObject({
  player_character_id: safeId128Schema, expected_record_revision: positiveSafeIntegerSchema,
  profile_ref: publicProfileRefSchema, entry_world: publicWorldRefSchema,
  overrides: z.array(z.strictObject({parameter: z.enum(objectiveNames), value: objectiveValue})).max(5),
  presentation: runPresentationSchema,
}).refine((v) => new Set(v.overrides.map((o) => o.parameter)).size === v.overrides.length);
export const nativeRunEntryResponseSchema = z.strictObject({
  session_id: safeId64Schema, scenario_id: safeId128Schema,
  scenario_content_version: z.string().min(1).max(32).regex(safeIdPattern), run_context: publicNativeRunContextSchema,
});
export type RunEntryOptions = z.infer<typeof runEntryOptionsSchema>;
export type PublicRunProfile = z.infer<typeof publicRunProfileSchema>;
export type PublicEntryWorld = z.infer<typeof publicEntryWorldSchema>;
export type PublicNativeRunContext = z.infer<typeof publicNativeRunContextSchema>;
export type NativeRunEntryRequest = z.infer<typeof nativeRunEntryRequestSchema>;
export type NativeRunEntryResponse = z.infer<typeof nativeRunEntryResponseSchema>;

export const playerSessionViewSchema = z
  .object({
    metadata: sessionMetadataSchema,
    run_context: publicNativeRunContextSchema.optional(),
    narrative_frame: narrativeFrameSchema,
    player_state: playerVisibleStateProjectionSchema,
    player_memory: playerMemoryProjectionSchema,
    presentation: publicScenarioPresentationSchema,
    action_affordances: publicActionAffordanceSetSchema,
    scenario_status: z.enum(["ACTIVE", "ENDED"]),
    ending_status: z.enum(["RESOLVED", "FAILED"]).nullable(),
    public_clocks: z.array(visibleClockSchema).max(32).default([]),
    recent_narrative_texts: z
      .array(
        codePointBoundedStringSchema(
          1,
          10_000,
          "recent narrative text",
        ),
      )
      .max(6)
      .default([]),
    ending_id: z.string().nullish(),
  })
  .superRefine((view, context) => {
    if (
      view.metadata.session_id !== view.player_state.session_id ||
      view.metadata.state_version !== view.player_state.state_version ||
      view.metadata.phase !== view.player_state.phase ||
      view.metadata.content_version !== view.player_state.content_version ||
      JSON.stringify(view.player_memory) !==
        JSON.stringify(view.player_state.player_memory) ||
      JSON.stringify(view.public_clocks) !==
        JSON.stringify(view.narrative_frame.player_visible_clocks)
    ) {
      context.addIssue({
        code: "custom",
        message: "player view projections do not share one authority",
      });
    }

    const isActive = view.scenario_status === "ACTIVE";
    const lifecycleIsValid = isActive
      ? view.ending_id == null &&
        view.ending_status == null &&
        view.presentation.ending == null &&
        view.action_affordances.mode !== "ENDED"
      : view.ending_id != null &&
        view.ending_status != null &&
        view.presentation.ending != null &&
        view.action_affordances.mode === "ENDED";
    if (!lifecycleIsValid) {
      context.addIssue({
        code: "custom",
        path: ["scenario_status"],
        message: "player view lifecycle fields are inconsistent",
      });
    }

    const decisionAffordanceIsValid =
      view.action_affordances.mode === "DECISION"
        ? view.narrative_frame.decision_required &&
          view.action_affordances.decision_id ===
            view.narrative_frame.decision_id
        : !view.narrative_frame.decision_required;
    if (!decisionAffordanceIsValid) {
      context.addIssue({
        code: "custom",
        path: ["action_affordances"],
        message: "action affordances do not match the current decision frame",
      });
    }

    const visibleNpcIds = new Set(
      view.player_state.visible_npcs.map((npc) => npc.npc_id),
    );
    const frameEntityIds = new Set(view.narrative_frame.visible_entities);
    const hasUnsafeTarget = view.action_affordances.actions.some((action) =>
      action.targets.some(
        (target) =>
          !visibleNpcIds.has(target.target_id) ||
          !frameEntityIds.has(target.target_id),
      ),
    );
    if (hasUnsafeTarget) {
      context.addIssue({
        code: "custom",
        path: ["action_affordances", "actions"],
        message: "action affordance exposes a target outside the current View",
      });
    }

    const recentCharacters = view.recent_narrative_texts.reduce(
      (total, text) => total + unicodeCodePointLength(text),
      0,
    );
    const recentBytes = view.recent_narrative_texts.reduce(
      (total, text) => total + new TextEncoder().encode(text).byteLength,
      0,
    );
    if (recentCharacters > 12_000 || recentBytes > 24_000) {
      context.addIssue({
        code: "custom",
        path: ["recent_narrative_texts"],
        message: "recent narrative texts exceed the public view budget",
      });
    }
  });

export const errorResponseSchema = z.object({
  error: z.object({
    error_code: z.string(),
    message: z.string(),
  }),
});

export type PublicPlayableCharacter = z.infer<
  typeof publicPlayableCharacterSchema
>;
export type PublicScenarioDescription = z.infer<
  typeof publicScenarioDescriptionSchema
>;
export type PublicScenarioCatalog = z.infer<typeof publicScenarioCatalogSchema>;
export type MinimalPlayerCharacterCreationRequest = z.infer<
  typeof minimalPlayerCharacterCreationRequestSchema
>;
export type PlayerCharacterSelfProjection = z.infer<
  typeof playerCharacterSelfProjectionSchema
>;
export type EligiblePlayerCharacterCollection = z.infer<
  typeof eligiblePlayerCharacterCollectionSchema
>;
export type RunEntryRequest = z.infer<typeof runEntryRequestSchema>;
export type RunEntryResponse = z.infer<typeof runEntryResponseSchema>;
export type CreateSessionRequest = z.infer<typeof createSessionRequestSchema>;
export type ActionRequest = z.infer<typeof actionRequestSchema>;
export type ActionResponse = z.infer<typeof actionResponseSchema>;
export type NarrativeRequestStatusResponse = z.infer<
  typeof narrativeRequestStatusResponseSchema
>;
export type SessionCreationResult = z.infer<
  typeof sessionCreationResultSchema
>;
export type NarrativeFrame = z.infer<typeof narrativeFrameSchema>;
export type PlayerMemoryProjection = z.infer<
  typeof playerMemoryProjectionSchema
>;
export type PlayerVisibleStateProjection = z.infer<
  typeof playerVisibleStateProjectionSchema
>;
export type PublicPlayableActionType = z.infer<
  typeof publicPlayableActionTypeSchema
>;
export type PublicActionAffordance = z.infer<
  typeof publicActionAffordanceSchema
>;
export type PublicDecisionChoice = z.infer<
  typeof publicDecisionChoiceSchema
>;
export type PublicSuggestedAction = z.infer<
  typeof publicSuggestedActionSchema
>;
export type PlayerSessionView = z.infer<typeof playerSessionViewSchema>;
export type ErrorResponse = z.infer<typeof errorResponseSchema>;

export const nativeWorldVisitSchema = z.object({visit_id:safeId128Schema, visit_ordinal:z.union([z.literal(1),z.literal(2)]),
  world_id:safeId128Schema,world_version:z.literal(1),region_id:safeId128Schema,region_version:z.literal(1)}).strict().refine(v =>
    v.visit_ordinal === 1 ? v.world_id === "world.death_certificate" && v.region_id === "region.death_certificate.facility"
      : v.world_id === "world.undelivered_receipt" && v.region_id === "region.undelivered_receipt.dispatch_hall");
export const nativeRunContinuationResultSchema = z.object({schema_version:z.literal("native-run-continuation-result/v1"),
  source_session_id:safeId64Schema,source_session_state_version:nonNegativeIntegerSchema.safe(),run_id:safeId128Schema,
  resulting_run_state_version:z.literal(4),session_id:safeId64Schema,initial_session_state_version:z.literal(0),
  scenario_id:z.literal("undelivered_receipt"),scenario_content_version:z.literal("undelivered-receipt-1.0.0"),
  run_context:publicNativeRunContextSchema,visit:nativeWorldVisitSchema}).strict().refine(r =>
    r.visit.visit_ordinal === 2 && r.source_session_id !== r.session_id && r.run_id === r.run_context.run_id);
export const nativeRunContinuationStatusSchema = z.object({schema_version:z.literal("native-run-continuation-status/v1"),
  session_id:safeId64Schema,run_id:safeId128Schema,run_state_version:z.union([z.literal(3),z.literal(4),z.literal(5)]),
  session_state_version:nonNegativeIntegerSchema.safe(),lifecycle_status:z.enum(["active","terminated"]),can_continue:z.boolean(),
  current_session_id:safeId64Schema,visit:nativeWorldVisitSchema.nullable(),
  predecessor:z.object({session_id:safeId64Schema,session_state_version:nonNegativeIntegerSchema.safe(),scenario_id:z.literal("death_certificate"),
    scenario_content_version:z.literal("death-certificate-1.1.0"),visit:nativeWorldVisitSchema}).strict().refine(p=>p.visit.visit_ordinal===1).nullable(),
  arrival:z.object({previous_ending_status:z.enum(["RESOLVED","FAILED"]),
    previous_ending_title:z.string().min(1).max(120),entry_notice:z.string().min(1).max(300)}).strict().refine(a =>
      a.previous_ending_status === "RESOLVED"
        ? ["规程已中断","记录已被质疑"].includes(a.previous_ending_title) && a.entry_notice === "上一世界已形成明确结果。你带着原有状态抵达发运大厅，当前队列从零开始计时。"
        : a.previous_ending_title === "记录成为现实" && a.entry_notice === "上一世界以失败结果结束。你带着原有状态抵达发运大厅，当前队列已经消耗四格期限。").nullable(),
  successor:nativeRunContinuationResultSchema.nullable()}).strict().refine(s=>{
    if ((s.arrival !== null) !== (s.visit?.visit_ordinal === 2)) return false;
    if (s.run_state_version !== (s.visit === null ? 3 : 4) + (s.lifecycle_status === "terminated" ? 1 : 0)) return false;
    if (s.can_continue && (s.run_state_version !== 3 || s.lifecycle_status !== "active" || s.visit !== null)) return false;
    if (s.visit === null) return s.predecessor === null && s.successor === null && s.current_session_id === s.session_id;
    if (s.visit.visit_ordinal === 2) return s.predecessor !== null && s.predecessor.session_id !== s.session_id && s.successor === null && s.current_session_id === s.session_id;
    return s.predecessor === null && s.successor !== null && s.successor.source_session_id === s.session_id &&
      s.successor.run_id === s.run_id && s.successor.session_id === s.current_session_id &&
      s.successor.source_session_state_version === s.session_state_version;
  });
export type NativeRunContinuationStatus = z.infer<typeof nativeRunContinuationStatusSchema>;
export type NativeRunContinuationResult = z.infer<typeof nativeRunContinuationResultSchema>;

export const nativeJourneyVisitSchema = z.strictObject({visit_id:safeId128Schema,
  visit_ordinal:z.union([z.literal(1),z.literal(2),z.literal(3)]),world_id:safeId128Schema,
  world_version:z.literal(1),region_id:safeId128Schema,region_version:z.literal(1)}).refine(v =>
    v.world_id === (v.visit_ordinal === 1 ? "world.death_certificate" : "world.undelivered_receipt") &&
    v.region_id === ["region.death_certificate.facility","region.undelivered_receipt.dispatch_hall",
      "region.undelivered_receipt.verification_archive"][v.visit_ordinal-1]);
export const nativeJourneyAssociationSchema = z.strictObject({session_id:safeId64Schema,
  session_state_version:nonNegativeIntegerSchema.safe(),scenario_id:safeId128Schema,
  scenario_content_version:z.string().min(1).max(32).regex(safeIdPattern),visit:nativeJourneyVisitSchema.nullable()}).refine(a => {
    const ordinal=a.visit?.visit_ordinal ?? 1;
    return a.scenario_id === ["death_certificate","undelivered_receipt","receipt_archive"][ordinal-1] &&
      a.scenario_content_version === ["death-certificate-1.1.0","undelivered-receipt-1.0.0","receipt-archive-1.0.0"][ordinal-1];
  });
export const ARCHIVE_NOTICE = "会签暂缓仍然有效，送达仍未得到证明。你进入核验档案室，决定如何保留这项待核记录；原有资源不会恢复。";
const journeyArrivalSchema = z.strictObject({previous_ending_status:z.enum(["RESOLVED","FAILED"]),
  previous_ending_title:codePointBoundedStringSchema(1,120,"ending title"),entry_notice:codePointBoundedStringSchema(1,300,"entry notice")});
export const nativeRunJourneySchema = z.strictObject({schema_version:z.literal("native-run-journey/v1"),
  session_id:safeId64Schema,run_id:safeId128Schema,run_state_version:z.union([z.literal(3),z.literal(4),z.literal(5),z.literal(6)]),
  lifecycle_status:z.enum(["active","terminated"]),run_context:publicNativeRunContextSchema,
  path:nativeJourneyAssociationSchema,current:nativeJourneyAssociationSchema,
  predecessor:nativeJourneyAssociationSchema.nullable(),successor:nativeJourneyAssociationSchema.nullable(),
  next_transition:z.strictObject({kind:z.enum(["first_continuation","regional_revisit"]),
    world_title:codePointBoundedStringSchema(1,120,"world title"),region_title:codePointBoundedStringSchema(1,120,"region title"),
    notice:codePointBoundedStringSchema(1,300,"notice")}).nullable(),arrival:journeyArrivalSchema.nullable()
}).refine(j => {
  const ordinal=j.path.visit?.visit_ordinal ?? 1, last=j.current.visit?.visit_ordinal ?? 1;
  if (j.session_id !== j.path.session_id || j.run_id !== j.run_context.run_id || ordinal>last ||
      j.run_state_version !== last+2+(j.lifecycle_status === "terminated" ? 1 : 0)) return false;
  const rows=[j.path,j.current,j.predecessor,j.successor].filter(a=>a!==null);
  if (rows.some(a=>(a.visit===null)!==(last===1))) return false;
  if ((j.predecessor===null)!==(ordinal===1) || (j.successor===null)!==(ordinal===last)) return false;
  if (j.predecessor && j.predecessor.visit?.visit_ordinal !== ordinal-1) return false;
  if (j.successor && j.successor.visit?.visit_ordinal !== ordinal+1) return false;
  for (let i=0;i<rows.length;i++) for (let k=i+1;k<rows.length;k++) {
    const a=rows[i]!, b=rows[k]!;
    if ((a.visit?.visit_ordinal ?? 1)===(b.visit?.visit_ordinal ?? 1)) {
      if (JSON.stringify(a)!==JSON.stringify(b)) return false;
    } else if (a.session_id===b.session_id || a.visit?.visit_id===b.visit?.visit_id) return false;
  }
  const offer=j.next_transition;
  if (offer && (j.lifecycle_status!=="active" || ordinal!==last || last===3 ||
      offer.kind!==(last===1 ? "first_continuation" : "regional_revisit") ||
      offer.world_title!=="未送达的回执" || offer.region_title!==(last===1 ? "发运大厅" : "核验档案室") ||
      (last===2 && offer.notice!==ARCHIVE_NOTICE))) return false;
  const a=j.arrival;
  if (ordinal===1) return a===null;
  if (!a) return false;
  if (ordinal===3) return a.previous_ending_status==="RESOLVED" && a.previous_ending_title==="回执待核，发运暂缓" && a.entry_notice===ARCHIVE_NOTICE;
  return a.previous_ending_status==="RESOLVED" ? ["规程已中断","记录已被质疑"].includes(a.previous_ending_title) &&
    a.entry_notice==="上一世界已形成明确结果。你带着原有状态抵达发运大厅，当前队列从零开始计时。" :
    a.previous_ending_title==="记录成为现实" && a.entry_notice==="上一世界以失败结果结束。你带着原有状态抵达发运大厅，当前队列已经消耗四格期限。";
});
export const nativeRunRevisitResultSchema = z.strictObject({schema_version:z.literal("native-run-revisit-result/v1"),
  source_session_id:safeId64Schema,source_session_state_version:nonNegativeIntegerSchema.safe(),run_id:safeId128Schema,
  resulting_run_state_version:z.literal(5),session_id:safeId64Schema,initial_session_state_version:z.literal(0),
  scenario_id:z.literal("receipt_archive"),scenario_content_version:z.literal("receipt-archive-1.0.0"),
  run_context:publicNativeRunContextSchema,visit:nativeJourneyVisitSchema}).refine(r=>r.visit.visit_ordinal===3 &&
    r.source_session_id!==r.session_id && r.run_id===r.run_context.run_id);
export type NativeRunJourney = z.infer<typeof nativeRunJourneySchema>;
export type NativeJourneyAssociation = z.infer<typeof nativeJourneyAssociationSchema>;
export type NativeRunRevisitResult = z.infer<typeof nativeRunRevisitResultSchema>;
export type NativeTransitionResult = NativeRunRevisitResult | NativeRunContinuationResult;

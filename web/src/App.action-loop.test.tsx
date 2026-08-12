import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import {
  PublicApiClient,
  type PublicActionSubmissionResult,
} from "./api/client";
import type {
  ActionResponse,
  EligiblePlayerCharacterCollection,
  NarrativeRequestStatusResponse,
  PlayerSessionView,
} from "./api/schemas";
import { readSessionRecoveryRecord } from "./sessionRecovery";
import {
  activeViewFixture,
  committedActionResponseFixture,
  eligiblePlayerCharactersFixture,
  endedViewFixture,
  errorFixture,
  freeActionViewFixture,
  minimalPlayerCharacterCreationFixture,
  pendingActionResponseFixture,
  playerCharacterFixture,
  runEntryResponseFixture,
  scenarioCatalogFixture,
  synchronousActionResponseFixture,
} from "./test/fixtures";
import { server } from "./test/server";

const apiOrigin = "http://action-ui.test";
const testClient = new PublicApiClient({ baseUrl: `${apiOrigin}/` });
const exactDemoWarning =
  "Deterministic Demo  local only  temporary data  not a production Provider";
const canonicalScenarioCatalog = {
  scenarios: [
    {
      scenario_id: "death_certificate",
      content_version: "death-certificate-1.1.0",
      title: "死亡证明已签发",
      hook: "你还活着，但系统已经签发了你的死亡证明。必须在处置规程完成前证明记录错了。",
      playable_characters: [
        {
          character_definition_id:
            "character.death_certificate.investigator",
          display_name: "调查者",
          description: "以开放方式调查现场、记录与目击者。",
        },
        {
          character_definition_id: "character.profession.clinical",
          display_name: "临床背景调查者",
          description: "擅长识别生命体征与临床矛盾。",
        },
        {
          character_definition_id: "character.profession.documents",
          display_name: "文书调查者",
          description: "擅长核验文书权威与证据链。",
        },
        {
          character_definition_id: "character.profession.response",
          display_name: "现场响应调查者",
          description: "擅长现场响应、脱险与降级冲突。",
        },
        {
          character_definition_id: "character.profession.systems",
          display_name: "系统分析调查者",
          description: "擅长追查系统顺序与自动规程。",
        },
      ],
      default_character_definition_id:
        "character.death_certificate.investigator",
    },
  ],
};

function scenarioHandler() {
  return http.get(`${apiOrigin}/v1/scenarios`, () =>
    HttpResponse.json(scenarioCatalogFixture),
  );
}

function eligibleHandler(
  collection: EligiblePlayerCharacterCollection = eligiblePlayerCharactersFixture,
) {
  return http.get(
    `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
    () => HttpResponse.json(collection),
  );
}

function deterministicActionIdentityFactory() {
  let next = 0;
  return () => {
    next += 1;
    return {
      turnId: `opaque-turn-${next}`,
      clientRequestId: `opaque-request-${next}`,
    };
  };
}

function renderActionApp(
  options: {
    client?: PublicApiClient;
    pollWait?: (milliseconds: number, signal: AbortSignal) => Promise<void>;
    actionIdentityFactory?: () => {
      turnId: string;
      clientRequestId: string;
    };
    idempotencyKeyFactory?: () => string;
    eligiblePlayerCharacters?: EligiblePlayerCharacterCollection;
  } = {},
) {
  server.use(eligibleHandler(options.eligiblePlayerCharacters));
  return render(
    <App
      client={options.client ?? testClient}
      idempotencyKeyFactory={
        options.idempotencyKeyFactory ?? (() => "opaque-mutation-request")
      }
      actionIdentityFactory={
        options.actionIdentityFactory ?? deterministicActionIdentityFactory()
      }
      {...(options.pollWait === undefined
        ? {}
        : { pollWait: options.pollWait })}
    />,
  );
}

function storedRecoveryRecord() {
  const result = readSessionRecoveryRecord();
  if (!result.ok) {
    throw new Error(`unexpected storage failure: ${result.failure.operation}`);
  }
  return result.value;
}

async function loadSession(
  user: ReturnType<typeof userEvent.setup>,
  sessionId = "session-public-1",
) {
  await user.type(await screen.findByLabelText("Session ID"), sessionId);
  await user.click(
    screen.getByRole("button", { name: "读取 PlayerSessionView" }),
  );
  await screen.findByText(`当前 Session：${sessionId}`);
}

function actionForm(buttonName: string): HTMLFormElement {
  const form = screen.getByRole("button", { name: buttonName }).closest("form");
  if (!(form instanceof HTMLFormElement)) {
    throw new Error(`missing action form for ${buttonName}`);
  }
  return form;
}

function withSessionId(
  view: PlayerSessionView,
  sessionId: string,
): PlayerSessionView {
  return {
    ...view,
    metadata: { ...view.metadata, session_id: sessionId },
    player_state: { ...view.player_state, session_id: sessionId },
  };
}

function dynamicCommittedActionResponse({
  clientRequestId,
  stateVersion,
  feedbackParameters,
}: {
  clientRequestId: string;
  stateVersion: number;
  feedbackParameters: ActionResponse["feedback_parameters"];
}): ActionResponse {
  return {
    ...committedActionResponseFixture(clientRequestId, stateVersion),
    result_code: "DYNAMIC_NARRATIVE_COMMITTED",
    feedback_code: "DYNAMIC_NARRATIVE_COMMITTED",
    feedback_parameters: feedbackParameters,
  };
}

const initialNoNpcSuggestionTexts = [
  "观察周围可见的环境。",
  "调查眼前的情况。",
  "谨慎尝试改变当前局面。",
] as const;

const initialGuideSuggestionTexts = [
  "观察周围可见的环境。",
  "与眼前可见的人交谈。",
  "谨慎尝试改变当前局面。",
] as const;

const laterServerSuggestionTexts = [
  "追踪刚刚显现的信号。",
  "比较已经确认的公开事实。",
  "依据变化后的局面继续行动。",
] as const;

function dynamicSuggestionSubmission(
  stateVersion: number,
  ordinal: number,
  description: string,
) {
  const identitySuffix = `${stateVersion.toString(16).padStart(2, "0")}${ordinal
    .toString(16)
    .padStart(2, "0")}${"a".repeat(56)}`;
  return {
    turn_id: `dst.${identitySuffix}`,
    client_request_id: `dsr.${identitySuffix}`,
    action_type: "CUSTOM" as const,
    description,
  };
}

function dynamicSuggestionViewFixture({
  stateVersion,
  suggestionTexts,
  visibleNpcs = [],
  customLabel = "自由行动",
}: {
  stateVersion: number;
  suggestionTexts: readonly [string, string, string];
  visibleNpcs?: PlayerSessionView["player_state"]["visible_npcs"];
  customLabel?: string;
}): PlayerSessionView {
  const view = freeActionViewFixture(stateVersion);
  return {
    ...view,
    narrative_frame: {
      ...view.narrative_frame,
      visible_entities: visibleNpcs.map((npc) => npc.npc_id),
    },
    player_state: {
      ...view.player_state,
      visible_npcs: visibleNpcs,
    },
    action_affordances: {
      mode: "FREE_ACTIONS",
      actions: [
        {
          action_type: "CUSTOM",
          label: customLabel,
          input_kind: "DESCRIPTION",
          max_input_length: 150,
          target_required: false,
          targets: [],
        },
      ],
      choices: [],
      suggested_actions: suggestionTexts.map((text, ordinal) => ({
        suggestion_id: `sug.${stateVersion
          .toString(16)
          .padStart(2, "0")}${ordinal
          .toString(16)
          .padStart(2, "0")}${"b".repeat(60)}`,
        ordinal,
        label: text,
        description: text,
        submission: dynamicSuggestionSubmission(stateVersion, ordinal, text),
      })),
    },
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

afterEach(() => {
  vi.unstubAllEnvs();
});

const canonicalChoiceSets: Record<
  number,
  Array<{ choice_id: string; label: string }>
> = {
  0: [
    {
      choice_id: "death_certificate.action.move_fingers_rhythmically",
      label: "有规律地移动仍可控制的手指",
    },
    {
      choice_id: "death_certificate.action.interfere_pulse_oximeter",
      label: "干扰指夹式血氧传感器",
    },
    {
      choice_id: "death_certificate.action.adjust_breathing_signal",
      label: "调整呼吸制造可识别生命信号",
    },
    {
      choice_id: "death_certificate.action.observe_quietly",
      label: "保持安静并获取现场信息",
    },
  ],
  4: [
    {
      choice_id: "death_certificate.action.prove_vitals",
      label: "要求复核生命指标",
    },
    {
      choice_id: "death_certificate.action.seek_records",
      label: "转向签发记录来源",
    },
  ],
  8: [
    {
      choice_id: "death_certificate.action.inspect_archive",
      label: "核对档案时间与签发链",
    },
    {
      choice_id: "death_certificate.action.trace_protocol",
      label: "追踪处置规程的触发来源",
    },
  ],
  11: [
    {
      choice_id: "death_certificate.action.open_observation",
      label: "进入地下观察层核验对象",
    },
    {
      choice_id: "death_certificate.action.secure_audit",
      label: "保存可追溯审计证据",
    },
  ],
  15: [
    {
      choice_id: "death_certificate.action.pause_protocol",
      label: "争取暂停处置规程",
    },
    {
      choice_id: "death_certificate.action.protect_patient",
      label: "优先稳定观察对象",
    },
  ],
  16: [
    {
      choice_id: "death_certificate.action.ask_coordinator",
      label: "要求协调员承担复核责任",
    },
    {
      choice_id: "death_certificate.action.ask_custodian",
      label: "要求保管员冻结记录链",
    },
  ],
  17: [
    {
      choice_id: "death_certificate.action.public_override",
      label: "公开推翻错误记录",
    },
    {
      choice_id: "death_certificate.action.controlled_audit",
      label: "以受控审计保留制度证据",
    },
  ],
  18: [
    {
      choice_id: "death_certificate.action.final_suspend",
      label: "执行最终暂停",
    },
    {
      choice_id: "death_certificate.action.final_disclose",
      label: "执行最终披露",
    },
  ],
};

const canonicalFreeActionTypes: Record<
  number,
  Array<"CONTINUE" | "CUSTOM" | "EXPLORE" | "OBSERVE" | "TALK" | "MOVE">
> = {
  1: ["CONTINUE", "CUSTOM", "EXPLORE", "OBSERVE", "TALK"],
  2: ["CONTINUE", "CUSTOM", "EXPLORE", "OBSERVE", "TALK"],
  3: ["CONTINUE", "CUSTOM", "EXPLORE", "OBSERVE", "TALK"],
  5: ["CONTINUE", "CUSTOM", "EXPLORE", "MOVE", "OBSERVE"],
  6: ["CONTINUE", "CUSTOM", "EXPLORE", "MOVE", "OBSERVE"],
  7: ["CONTINUE", "CUSTOM", "EXPLORE", "OBSERVE", "TALK"],
  9: ["CONTINUE", "CUSTOM", "EXPLORE", "OBSERVE", "TALK"],
  10: ["CONTINUE", "CUSTOM", "EXPLORE", "OBSERVE", "TALK"],
  12: ["CONTINUE", "CUSTOM", "EXPLORE", "OBSERVE", "TALK"],
  13: ["CONTINUE", "CUSTOM", "EXPLORE", "OBSERVE", "TALK"],
  14: ["CONTINUE", "CUSTOM", "EXPLORE", "OBSERVE", "TALK"],
};

const canonicalClockValues = [
  [0, 0],
  [0, 0],
  [1, 0],
  [2, 1],
  [3, 2],
  [4, 2],
  [4, 3],
  [4, 4],
  [4, 5],
  [4, 6],
  [4, 7],
  [4, 8],
  [4, 9],
  [4, 10],
  [4, 11],
  [4, 12],
  [4, 12],
  [4, 12],
  [4, 12],
  [4, 12],
] as const;

function canonicalPhase(version: number): string {
  if (version === 0) return "death_certificate.arrival_locked";
  if (version <= 4) return "death_certificate.life_disputed";
  if (version <= 6) return "death_certificate.disposal_escape";
  if (version <= 12) return "death_certificate.investigation";
  if (version <= 14) return "death_certificate.self_fulfilling_truth";
  if (version <= 18) return "death_certificate.core_conflict";
  return "death_certificate.resolution";
}

const canonicalScenePresentation: Record<
  string,
  { title: string; summary: string }
> = {
  "death_certificate.arrival_locked": {
    title: "封闭抵达",
    summary: "在封闭接收室中回应迫近的处置程序。",
  },
  "death_certificate.life_disputed": {
    title: "生命争议",
    summary: "让现场人员正视你仍然活着的事实。",
  },
  "death_certificate.disposal_escape": {
    title: "处置脱离",
    summary: "在规程推进前离开封闭处置路线。",
  },
  "death_certificate.investigation": {
    title: "交叉调查",
    summary: "调查记录、因果链与仍在运行的设施。",
  },
  "death_certificate.self_fulfilling_truth": {
    title: "自证真相",
    summary: "把已验证的线索连接成可以公开质疑的因果链。",
  },
  "death_certificate.core_conflict": {
    title: "核心冲突",
    summary: "在时间耗尽前决定如何终止记录驱动的规程。",
  },
  "death_certificate.resolution": {
    title: "结算",
    summary: "查看这次调查最终留下的公开结果。",
  },
};

function canonicalLocation(version: number): string {
  if (version <= 4) return "death_certificate.intake_room";
  if (version <= 8) return "death_certificate.service_corridor";
  if (version <= 10) return "death_certificate.records_room";
  if (version <= 14) return "death_certificate.observation_level";
  return "death_certificate.control_room";
}

function canonicalActionLabel(
  actionType: "CONTINUE" | "CUSTOM" | "EXPLORE" | "OBSERVE" | "TALK" | "MOVE",
): string {
  return {
    CONTINUE: "继续",
    CUSTOM: "自由行动",
    EXPLORE: "探索",
    OBSERVE: "观察",
    TALK: "交谈",
    MOVE: "移动",
  }[actionType];
}

function canonicalView(version: number): PlayerSessionView {
  const choices = canonicalChoiceSets[version] ?? [];
  const freeActionTypes = canonicalFreeActionTypes[version] ?? [];
  const ended = version === 19;
  const rapid = version >= 15 && version <= 18;
  const decision = choices.length > 0;
  const decisionId = `death_certificate.decision.bound.${version}`;
  const phaseId = canonicalPhase(version);
  const scene = canonicalScenePresentation[phaseId]!;
  const [disposal, deadline] = canonicalClockValues[version]!;
  const clocks = [
    {
      clock_id: "disposal_protocol",
      value: disposal,
      maximum: 12,
    },
    {
      clock_id: "predicted_death_deadline",
      value: deadline,
      maximum: 13,
    },
  ];
  const frame = {
    ...activeViewFixture.narrative_frame,
    frame_id: `death_certificate.frame.${version}`,
    scenario_id: "death_certificate",
    phase_id: phaseId,
    mode: ended
      ? ("SETTLEMENT" as const)
      : rapid
        ? ("RAPID_DECISION" as const)
        : decision
          ? ("DECISION" as const)
          : ("FLOW" as const),
    current_location_id: canonicalLocation(version),
    decision_required: decision,
    ...(decision
      ? {
          decision_id: decisionId,
          decision_reason: rapid
            ? ("TIME_CRITICAL" as const)
            : ("PLAYER_DIRECT_RESPONSE" as const),
          suggested_actions: choices.map((choice) => ({
            action_id: choice.choice_id,
            action_type: "choice" as const,
            label_hint: choice.label,
            target_ids: [],
          })),
        }
      : {
          decision_id: undefined,
          decision_reason: undefined,
          suggested_actions: [],
        }),
    stop_condition: ended
      ? ("SCENARIO_ENDED" as const)
      : decision
        ? ("AWAIT_PLAYER" as const)
        : ("CONTINUE" as const),
    player_visible_clocks: clocks,
  };
  const actionAffordances: PlayerSessionView["action_affordances"] = ended
    ? { mode: "ENDED", actions: [], choices: [] }
    : decision
      ? {
          mode: "DECISION",
          actions: [],
          decision_id: decisionId,
          choices: choices.map((choice) => ({
            action_type: "CHOOSE",
            choice_id: choice.choice_id,
            label: choice.label,
            target_ids: [],
          })),
        }
      : {
          mode: "FREE_ACTIONS",
          actions: freeActionTypes.map((actionType) => ({
            action_type: actionType,
            label: canonicalActionLabel(actionType),
            input_kind:
              actionType === "CONTINUE"
                ? ("NONE" as const)
                : actionType === "TALK"
                  ? ("DIALOGUE" as const)
                  : ("DESCRIPTION" as const),
            ...(actionType === "CONTINUE"
              ? {}
              : {
                  max_input_length: actionType === "TALK" ? 200 : 150,
                }),
            target_required: false,
            targets: [],
          })),
          choices: [],
        };
  const phase = ended ? "ENDED" : "AWAITING_ACTION";
  return {
    ...activeViewFixture,
    metadata: {
      ...activeViewFixture.metadata,
      phase,
      state_version: version,
      content_version: "death-certificate-1.1.0",
      character_definition_id: "character.death_certificate.investigator",
      character_display_name: "调查者",
      updated_at: `2026-07-23T00:00:${String(version).padStart(2, "0")}Z`,
    },
    narrative_frame: frame,
    player_state: {
      ...activeViewFixture.player_state,
      phase,
      state_version: version,
      content_version: "death-certificate-1.1.0",
      character_definition_id: "character.death_certificate.investigator",
      player_memory: activeViewFixture.player_memory,
    },
    presentation: {
      title: "死亡证明已签发",
      scene_title: scene.title,
      scene_summary: scene.summary,
      ...(ended
        ? {
            ending: {
              title: "规程已中断",
              summary:
                "处置规程被阻止，你的生命状态获得了可验证的承认。",
            },
          }
        : {}),
    },
    action_affordances: actionAffordances,
    scenario_status: ended ? "ENDED" : "ACTIVE",
    ending_status: ended ? "RESOLVED" : null,
    public_clocks: clocks,
    recent_narrative_texts: [`完整权威 View 版本 ${version}`],
    ...(ended
      ? { ending_id: "death_certificate.ending.protocol_broken" }
      : { ending_id: undefined }),
  };
}

function assertCanonicalDecisionPresentation(
  view: PlayerSessionView,
  version: number,
): void {
  const expectedChoices = canonicalChoiceSets[version];
  if (expectedChoices === undefined) {
    return;
  }
  expect(view.action_affordances).toEqual({
    mode: "DECISION",
    actions: [],
    decision_id: `death_certificate.decision.bound.${version}`,
    choices: expectedChoices.map((choice) => ({
      action_type: "CHOOSE",
      choice_id: choice.choice_id,
      label: choice.label,
      target_ids: [],
    })),
  });
  expect(view.narrative_frame.suggested_actions).toEqual(
    expectedChoices.map((choice) => ({
      action_id: choice.choice_id,
      action_type: "choice",
      label_hint: choice.label,
      target_ids: [],
    })),
  );
}

function assertExactDemoWarning(container: HTMLElement): void {
  const warnings = Array.from(container.querySelectorAll(".demo-warning"));
  if (warnings.length !== 1 || warnings[0]?.textContent !== exactDemoWarning) {
    throw new Error("the exact deterministic Demo warning was not rendered");
  }
}

function assertRenderedScenarioCatalogPresentation(
  container: HTMLElement,
): void {
  const scenarioCopy = container.querySelector(".scenario-copy");
  const scenarioSelect = container.querySelector("#scenario");
  if (
    !(scenarioCopy instanceof HTMLElement) ||
    !(scenarioSelect instanceof HTMLSelectElement)
  ) {
    throw new Error("the public scenario catalog was not rendered");
  }

  expect(
    within(scenarioCopy).getByRole("heading", { name: "死亡证明已签发" }),
  ).toBeVisible();
  expect(
    within(scenarioCopy).getByText(
      "你还活着，但系统已经签发了你的死亡证明。必须在处置规程完成前证明记录错了。",
    ),
  ).toBeVisible();
  expect(scenarioSelect.value).toBe("death_certificate");
  expect(container.querySelector("#role")).toBeNull();
}

function readRenderedCanonicalPresentation(container: HTMLElement) {
  const view = container.querySelector(".view-summary");
  if (!(view instanceof HTMLElement)) {
    throw new Error("the authoritative View presentation was not rendered");
  }
  return {
    scenarioTitle: view.querySelector("#session-view-heading")?.textContent,
    sceneTitle: view.querySelector("#scene-heading")?.textContent,
    sceneSummary: view.querySelector("#session-view-heading + p")?.textContent,
    choiceLabels: Array.from(
      container.querySelectorAll(".decision-choices button"),
      (button) => button.textContent,
    ),
    endingTitle: view.querySelector("#ending-heading")?.textContent ?? null,
    endingSummary:
      view.querySelector("#ending-heading + p")?.textContent ?? null,
  };
}

function assertRenderedCanonicalPresentation(
  container: HTMLElement,
  version: number,
): void {
  const scene = canonicalScenePresentation[canonicalPhase(version)]!;
  expect(readRenderedCanonicalPresentation(container)).toEqual({
    scenarioTitle: "死亡证明已签发",
    sceneTitle: `当前场景：${scene.title}`,
    sceneSummary: scene.summary,
    choiceLabels: (canonicalChoiceSets[version] ?? []).map(
      (choice) => choice.label,
    ),
    endingTitle: version === 19 ? "规程已中断" : null,
    endingSummary:
      version === 19
        ? "处置规程被阻止，你的生命状态获得了可验证的承认。"
        : null,
  });
}

describe("action_affordances and synchronous lifecycle", () => {
  const presentationProbe =
    import.meta.env.VITE_DEVIATION_DEMO_PRESENTATION_PROBE === "1" ? it : it.skip;

  presentationProbe(
    "renders the exact deterministic Demo warning from the effective Vite mode",
    () => {
      server.use(scenarioHandler());
      const rendered = renderActionApp();
      assertExactDemoWarning(rendered.container);
    },
  );

  it("rejects the exact-warning presentation contract when Demo mode is absent", () => {
    vi.stubEnv("VITE_APP_MODE", "production");
    server.use(scenarioHandler());
    const rendered = renderActionApp();
    expect(() => assertExactDemoWarning(rendered.container)).toThrow(
      "the exact deterministic Demo warning was not rendered",
    );
  });

  it("rejects the exact-warning presentation contract when rendering is suppressed", () => {
    vi.stubEnv("VITE_APP_MODE", "deterministic-demo");
    server.use(scenarioHandler());
    const rendered = renderActionApp();
    rendered.container.querySelector(".demo-warning")?.remove();
    expect(() => assertExactDemoWarning(rendered.container)).toThrow(
      "the exact deterministic Demo warning was not rendered",
    );
  });

  it("submits all three authoritative dynamic suggestions verbatim, then keeps free CUSTOM independent", async () => {
    let viewReads = 0;
    const submittedBodies: unknown[] = [];
    const actionIdentityFactory = vi.fn(() => ({
      turnId: "client-owned-free-turn",
      clientRequestId: "client-owned-free-request",
    }));
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(
            dynamicSuggestionViewFixture({
              stateVersion: viewReads,
              suggestionTexts:
                viewReads <= 3
                  ? initialNoNpcSuggestionTexts
                  : laterServerSuggestionTexts,
            }),
          );
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          const body = await request.json();
          submittedBodies.push(body);
          return HttpResponse.json(
            committedActionResponseFixture(
              (body as { client_request_id: string }).client_request_id,
              99,
            ),
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp({ actionIdentityFactory });
    await loadSession(user);

    for (const [ordinal, text] of initialNoNpcSuggestionTexts.entries()) {
      await user.click(screen.getByRole("button", { name: text }));
      await waitFor(() => expect(viewReads).toBe(ordinal + 2));
      expect(actionIdentityFactory).not.toHaveBeenCalled();
    }

    expect(submittedBodies).toEqual(
      initialNoNpcSuggestionTexts.map((text, ordinal) =>
        dynamicSuggestionSubmission(ordinal + 1, ordinal, text),
      ),
    );
    for (const text of laterServerSuggestionTexts) {
      expect(screen.getByRole("button", { name: text })).toBeVisible();
    }
    expect(screen.queryByText("权威 View 已推进到版本 99。")).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "提交自由行动" }),
    ).toBeVisible();

    await user.type(screen.getByLabelText("行动描述"), "检查眼前公开可见的细节。");
    expect(
      screen.getByRole("button", { name: "提交自由行动" }),
    ).toBeEnabled();
    await user.click(
      screen.getByRole("button", { name: "提交自由行动" }),
    );
    await waitFor(() => expect(viewReads).toBe(5));

    expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
    expect(submittedBodies[3]).toEqual({
      turn_id: "client-owned-free-turn",
      client_request_id: "client-owned-free-request",
      action_type: "CUSTOM",
      description: "检查眼前公开可见的细节。",
    });
    expect(screen.getByText("权威 View：当前")).toBeVisible();
  });

  it("recovers the canonical fifth Fake failure without replay and continues through item eight", async () => {
    const anchor = "A visible amber marker appears beside the sealed doorway.";
    const continuity =
      "The visible amber marker established earlier now identifies the route forward.";
    const suggestionTexts = [
      initialNoNpcSuggestionTexts,
      ["沿琥珀色痕迹继续。", "比较新出现的标记。", "检查改变后的路线。"],
      ["核对已确认的信号。", "询问发生了什么变化。", "标记可见的路线。"],
      ["复核公开标记。", "比较当前场景。", "谨慎继续行动。"],
      ["返回标记处。", "观察密封门口。", "沿恢复的路线行动。"],
      ["追踪稍后出现的信号。", "比较保留的事实。", "依据变化继续行动。"],
      ["沿琥珀色路线行动。", "复核先前的标记。", "等待新的信号。"],
      ["确认前进路线。", "检查最后的标记。", "比较可见的变化。"],
    ] as const;
    const submittedBodies: unknown[] = [];
    let actionPosts = 0;
    let viewReads = 0;
    let committedVersion = 0;
    const actionIdentityFactory = deterministicActionIdentityFactory();

    function manualFakeView(version: number): PlayerSessionView {
      const view = dynamicSuggestionViewFixture({
        stateVersion: version,
        suggestionTexts: suggestionTexts[version]!,
        customLabel: "自由行动",
      });
      return {
        ...view,
        presentation: {
          ...view.presentation,
          scene_summary: version === 7 ? continuity : `Manual Fake View ${version}`,
        },
        recent_narrative_texts: version === 0 ? [] : [anchor],
      };
    }

    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(manualFakeView(committedVersion));
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          actionPosts += 1;
          const body = await request.json();
          submittedBodies.push(body);
          if (actionPosts === 5) {
            return HttpResponse.json(
              errorFixture(
                "NARRATIVE_OUTCOME_UNKNOWN",
                "Narrative turn cannot be committed",
              ),
              { status: 409 },
            );
          }
          committedVersion += 1;
          return HttpResponse.json(
            synchronousActionResponseFixture(
              (body as { client_request_id: string }).client_request_id,
              committedVersion,
            ),
          );
        },
      ),
    );
    const user = userEvent.setup();
    const rendered = renderActionApp({ actionIdentityFactory });
    await loadSession(user);

    async function submitCustom(description: string, expectedPosts: number) {
      const form = actionForm("提交自由行动");
      const input = within(form).getByLabelText("行动描述");
      await user.clear(input);
      await user.type(input, description);
      await user.click(within(form).getByRole("button", { name: "提交自由行动" }));
      await waitFor(() => expect(actionPosts).toBe(expectedPosts));
    }

    await user.click(screen.getByRole("button", { name: "观察周围可见的环境。" }));
    await waitFor(() => expect(committedVersion).toBe(1));
    expect(screen.getAllByText(anchor)).toHaveLength(2);

    await submitCustom("检查可见的地面标记，但不要触碰任何物品。", 2);
    await user.click(screen.getByRole("button", { name: "询问发生了什么变化。" }));
    await waitFor(() => expect(committedVersion).toBe(3));
    await submitCustom(
      "安静等待，并把当前场景与上一次可见变化进行比较。",
      4,
    );
    await submitCustom("停下来倾听房间里的变化。", 5);
    expect(
      await screen.findByText(
        "HTTP 409 · NARRATIVE_OUTCOME_UNKNOWN · Narrative turn cannot be committed",
      ),
    ).toBeVisible();
    expect(committedVersion).toBe(4);
    expect(actionPosts).toBe(5);
    const readsBeforeRecovery = viewReads;

    rendered.unmount();
    renderActionApp({ actionIdentityFactory });
    await screen.findByText("当前 Session：session-public-1");
    await waitFor(() => expect(viewReads).toBe(readsBeforeRecovery + 1));
    expect(actionPosts).toBe(5);

    await user.click(screen.getByRole("button", { name: "沿恢复的路线行动。" }));
    await waitFor(() => expect(committedVersion).toBe(5));
    await submitCustom(
      "沿先前可见的变化继续检查它现在影响了什么。",
      7,
    );
    await user.click(screen.getByRole("button", { name: "沿琥珀色路线行动。" }));
    await waitFor(() => expect(committedVersion).toBe(7));
    expect(await screen.findByText(continuity)).toBeVisible();

    expect(actionPosts).toBe(8);
    expect(submittedBodies).toEqual([
      dynamicSuggestionSubmission(0, 0, "观察周围可见的环境。"),
      {
        turn_id: "opaque-turn-1",
        client_request_id: "opaque-request-1",
        action_type: "CUSTOM",
        description: "检查可见的地面标记，但不要触碰任何物品。",
      },
      dynamicSuggestionSubmission(2, 1, "询问发生了什么变化。"),
      {
        turn_id: "opaque-turn-2",
        client_request_id: "opaque-request-2",
        action_type: "CUSTOM",
        description: "安静等待，并把当前场景与上一次可见变化进行比较。",
      },
      {
        turn_id: "opaque-turn-3",
        client_request_id: "opaque-request-3",
        action_type: "CUSTOM",
        description: "停下来倾听房间里的变化。",
      },
      dynamicSuggestionSubmission(4, 2, "沿恢复的路线行动。"),
      {
        turn_id: "opaque-turn-4",
        client_request_id: "opaque-request-4",
        action_type: "CUSTOM",
        description: "沿先前可见的变化继续检查它现在影响了什么。",
      },
      dynamicSuggestionSubmission(6, 0, "沿琥珀色路线行动。"),
    ]);
  });

  it.each([
    {
      branch: "zero eligible NPCs",
      visibleNpcs: [],
      suggestionTexts: initialNoNpcSuggestionTexts,
      middleLabel: "调查眼前的情况。",
    },
    {
      branch: "one eligible NPC",
      visibleNpcs: [
        {
          npc_id: "npc.public.guide",
          npc_definition_id: "npc.definition.guide",
          display_name: "Guide",
        },
      ],
      suggestionTexts: initialGuideSuggestionTexts,
      middleLabel: "与眼前可见的人交谈。",
    },
    {
      branch: "multiple eligible NPCs with the server-selected Guide",
      visibleNpcs: [
        {
          npc_id: "npc.public.guide",
          npc_definition_id: "npc.definition.guide",
          display_name: "Guide",
        },
        {
          npc_id: "npc.public.observer",
          npc_definition_id: "npc.definition.observer",
          display_name: "Observer",
        },
      ],
      suggestionTexts: initialGuideSuggestionTexts,
      middleLabel: "与眼前可见的人交谈。",
    },
  ])(
    "renders the exact initial suggestion branch for $branch and submits its server payload",
    async ({ visibleNpcs, suggestionTexts, middleLabel }) => {
      let viewReads = 0;
      const submittedBodies: unknown[] = [];
      const actionIdentityFactory = vi.fn(() => ({
        turnId: "must-not-be-created",
        clientRequestId: "must-not-be-created",
      }));
      server.use(
        scenarioHandler(),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () => {
            viewReads += 1;
            return HttpResponse.json(
              dynamicSuggestionViewFixture({
                stateVersion: viewReads,
                suggestionTexts,
                visibleNpcs: [...visibleNpcs],
              }),
            );
          },
        ),
        http.post(
          `${apiOrigin}/v1/sessions/session-public-1/actions`,
          async ({ request }) => {
            const body = await request.json();
            submittedBodies.push(body);
            return HttpResponse.json(
              committedActionResponseFixture(
                (body as { client_request_id: string }).client_request_id,
                2,
              ),
            );
          },
        ),
      );
      const user = userEvent.setup();
      renderActionApp({ actionIdentityFactory });
      await loadSession(user);

      const suggestionGroup = screen.getByRole("group", {
        name: "动态建议行动",
      });
      expect(within(suggestionGroup).getAllByRole("button")).toHaveLength(3);
      for (const text of suggestionTexts) {
        expect(
          within(suggestionGroup).getByRole("button", { name: text }),
        ).toBeVisible();
      }
      const playerState = screen
        .getByRole("heading", { name: "公开玩家状态" })
        .closest("section");
      expect(playerState).toHaveTextContent(`可见 NPC${visibleNpcs.length}`);
      expect(
        screen.getByRole("button", { name: "提交自由行动" }),
      ).toBeVisible();

      await user.click(
        within(suggestionGroup).getByRole("button", { name: middleLabel }),
      );
      await waitFor(() => expect(viewReads).toBe(2));

      expect(submittedBodies).toEqual([
        dynamicSuggestionSubmission(1, 1, middleLabel),
      ]);
      expect(actionIdentityFactory).not.toHaveBeenCalled();
    },
  );

  it.each([
    ["absent", undefined],
    ["invalid", "Bad\u0000Name"],
    ["over-bound", "N".repeat(121)],
  ] as const)(
    "does not render a fallback or progress when the server refuses an %s selected NPC name",
    async (_caseName, selectedNpcName) => {
      let viewReads = 0;
      let actionPosts = 0;
      server.use(
        scenarioHandler(),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () => {
            viewReads += 1;
            const selectedNameIsValid =
              selectedNpcName !== undefined &&
              !/[\p{Cc}\p{Cf}]/u.test(selectedNpcName) &&
              Array.from(selectedNpcName).length <= 120;
            if (selectedNameIsValid) {
              throw new Error("the invalid selected-NPC vector was not invalid");
            }
            return HttpResponse.json(
              errorFixture("INTERNAL_SERVER_ERROR", "Internal server error"),
              { status: 500 },
            );
          },
        ),
        http.post(
          `${apiOrigin}/v1/sessions/session-public-1/actions`,
          () => {
            actionPosts += 1;
            return HttpResponse.json({}, { status: 500 });
          },
        ),
      );
      const user = userEvent.setup();
      renderActionApp();
      await user.type(await screen.findByLabelText("Session ID"), "session-public-1");
      await user.click(
        screen.getByRole("button", { name: "读取 PlayerSessionView" }),
      );

      expect(await screen.findByRole("alert")).toHaveTextContent(
        "Internal server error",
      );
      expect(viewReads).toBe(1);
      expect(actionPosts).toBe(0);
      expect(
        screen.queryByText("当前 Session：session-public-1"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("group", { name: "动态建议行动" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();
    },
  );

  it("rejects a version-4 choice divergence served and rendered by App", async () => {
    let currentVersion = 0;
    const viewVersions: number[] = [];
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json(canonicalScenarioCatalog),
      ),
      http.post(`${apiOrigin}/v1/runs`, () =>
        HttpResponse.json({
          ...runEntryResponseFixture,
          scenario_id: "death_certificate",
        }),
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          const view = canonicalView(currentVersion);
          if (
            currentVersion === 4 &&
            view.action_affordances.mode === "DECISION"
          ) {
            view.action_affordances.choices[0] = {
              ...view.action_affordances.choices[0]!,
              label: "证明生命体征",
            };
          }
          viewVersions.push(currentVersion);
          return HttpResponse.json(view);
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          const body = (await request.json()) as Record<string, unknown>;
          currentVersion += 1;
          const clientRequestId = body.client_request_id as string;
          return HttpResponse.json(
            currentVersion === 2
              ? committedActionResponseFixture(
                  clientRequestId,
                  currentVersion,
                )
              : synchronousActionResponseFixture(
                  clientRequestId,
                  currentVersion,
                ),
          );
        },
      ),
    );

    const user = userEvent.setup();
    const rendered = renderActionApp();
    await screen.findByLabelText("副本");
    await user.click(screen.getByRole("button", { name: "进入 Run" }));
    await waitFor(() => expect(viewVersions).toEqual([0]));
    await user.click(
      screen.getByRole("button", {
        name: "有规律地移动仍可控制的手指",
      }),
    );
    await waitFor(() => expect(viewVersions).toEqual([0, 1]));

    const customForm = actionForm("提交自由行动");
    await user.type(
      within(customForm).getByLabelText("行动描述"),
      "请协调员复核我的连续回应和生命体征",
    );
    await user.click(
      within(customForm).getByRole("button", { name: "提交自由行动" }),
    );
    await waitFor(() => expect(viewVersions).toEqual([0, 1, 2]));
    for (const expectedVersion of [3, 4]) {
      await user.click(screen.getByRole("button", { name: "提交继续" }));
      await waitFor(() =>
        expect(viewVersions.at(-1)).toBe(expectedVersion),
      );
    }

    expect(
      await screen.findByRole("button", { name: "证明生命体征" }),
    ).toBeVisible();
    expect(() =>
      assertRenderedCanonicalPresentation(rendered.container, 4),
    ).toThrow();
  });

  it("completes the canonical deterministic Demo path through 19 displayed actions and authoritative Views", async () => {
    vi.stubEnv("VITE_APP_MODE", "deterministic-demo");
    const expectedActions = [
      {
        action_type: "CHOOSE",
        decision_id: "death_certificate.decision.bound.0",
        choice_id: "death_certificate.action.move_fingers_rhythmically",
      },
      {
        action_type: "CUSTOM",
        description: "请协调员复核我的连续回应和生命体征",
      },
      { action_type: "CONTINUE" },
      { action_type: "CONTINUE" },
      {
        action_type: "CHOOSE",
        decision_id: "death_certificate.decision.bound.4",
        choice_id: "death_certificate.action.prove_vitals",
      },
      { action_type: "CONTINUE" },
      { action_type: "CONTINUE" },
      { action_type: "CONTINUE" },
      {
        action_type: "CHOOSE",
        decision_id: "death_certificate.decision.bound.8",
        choice_id: "death_certificate.action.inspect_archive",
      },
      {
        action_type: "EXPLORE",
        description: "沿记录与档案审计路径核对签发时间",
      },
      {
        action_type: "EXPLORE",
        description: "核对日志时间顺序以及规程反馈",
      },
      {
        action_type: "CHOOSE",
        decision_id: "death_certificate.decision.bound.11",
        choice_id: "death_certificate.action.open_observation",
      },
      {
        action_type: "OBSERVE",
        description: "复核地下患者的生命体征与连续监测历史",
      },
      { action_type: "CONTINUE" },
      { action_type: "CONTINUE" },
      {
        action_type: "CHOOSE",
        decision_id: "death_certificate.decision.bound.15",
        choice_id: "death_certificate.action.pause_protocol",
      },
      {
        action_type: "CHOOSE",
        decision_id: "death_certificate.decision.bound.16",
        choice_id: "death_certificate.action.ask_coordinator",
      },
      {
        action_type: "CHOOSE",
        decision_id: "death_certificate.decision.bound.17",
        choice_id: "death_certificate.action.public_override",
      },
      {
        action_type: "CHOOSE",
        decision_id: "death_certificate.decision.bound.18",
        choice_id: "death_certificate.action.final_suspend",
      },
    ] as const;
    const submittedBodies: Array<Record<string, unknown>> = [];
    const viewVersions: number[] = [];
    const servedViews: PlayerSessionView[] = [];
    const requestStatusCallSequence: Array<{
      requestId: string;
      status: "PENDING" | "COMMITTED";
    }> = [];
    const confirmed202Sequence: string[] = [];
    const pollWait = vi.fn(
      async (...parameters: [number, AbortSignal]) => {
        void parameters;
      },
    );
    let currentVersion = 0;
    let creationBody: unknown;
    let entryBody: unknown;
    let actionPostCount = 0;
    let requestStatusReads = 0;
    let legacySessionCreates = 0;

    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json(canonicalScenarioCatalog),
      ),
      http.post(`${apiOrigin}/v1/player-characters`, async ({ request }) => {
        creationBody = await request.json();
        return HttpResponse.json(playerCharacterFixture);
      }),
      http.post(`${apiOrigin}/v1/runs`, async ({ request }) => {
        entryBody = await request.json();
        return HttpResponse.json({
          ...runEntryResponseFixture,
          scenario_id: "death_certificate",
        });
      }),
      http.post(`${apiOrigin}/v1/sessions`, () => {
        legacySessionCreates += 1;
        return HttpResponse.json({}, { status: 500 });
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          const view = canonicalView(currentVersion);
          if (currentVersion === 2) {
            confirmed202Sequence.push("view:2");
          }
          viewVersions.push(view.metadata.state_version);
          servedViews.push(view);
          return HttpResponse.json(view);
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          actionPostCount += 1;
          const body = (await request.json()) as Record<string, unknown>;
          const expected = expectedActions[currentVersion]!;
          const displayed = canonicalView(currentVersion).action_affordances;
          const actionType = body.action_type;
          const commonKeys = ["action_type", "client_request_id", "turn_id"];

          expect(actionType).toBe(expected.action_type);
          if (actionType === "CHOOSE") {
            expect(displayed.mode).toBe("DECISION");
            expect(displayed.decision_id).toBe(body.decision_id);
            expect(
              displayed.choices.some(
                (choice) => choice.choice_id === body.choice_id,
              ),
            ).toBe(true);
            expect(Object.keys(body).sort()).toEqual(
              [...commonKeys, "choice_id", "decision_id"].sort(),
            );
          } else {
            expect(displayed.mode).toBe("FREE_ACTIONS");
            const affordance = displayed.actions.find(
              (action) => action.action_type === actionType,
            );
            expect(affordance).toBeDefined();
            expect(Object.keys(body).sort()).toEqual(
              actionType === "CONTINUE"
                ? commonKeys.sort()
                : [...commonKeys, "description"].sort(),
            );
          }

          submittedBodies.push(body);
          currentVersion += 1;
          const clientRequestId = body.client_request_id as string;
          if (currentVersion === 2) {
            confirmed202Sequence.push("action:2");
            return HttpResponse.json(
              pendingActionResponseFixture(clientRequestId),
              { status: 202 },
            );
          }
          const providerBacked = [2, 10, 11, 13].includes(currentVersion);
          return HttpResponse.json(
            providerBacked
              ? committedActionResponseFixture(
                  clientRequestId,
                  currentVersion,
                )
              : synchronousActionResponseFixture(
                  clientRequestId,
                  currentVersion,
            ),
          );
        },
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/:requestId`,
        ({ params }) => {
          requestStatusReads += 1;
          const requestId = String(params.requestId);
          expect(requestId).toBe("opaque-request-2");
          expect(storedRecoveryRecord()).toEqual({
            version: 1,
            session_id: "session-public-1",
            client_request_id: "opaque-request-2",
          });
          if (requestStatusReads === 1) {
            requestStatusCallSequence.push({ requestId, status: "PENDING" });
            confirmed202Sequence.push("status:PENDING");
            return HttpResponse.json({
              session_id: "session-public-1",
              client_request_id: requestId,
              status: "PENDING",
              client_action: "POLL_SAME_REQUEST",
              error_code: null,
              retry_after_seconds: 2,
              response: null,
            });
          }
          requestStatusCallSequence.push({ requestId, status: "COMMITTED" });
          confirmed202Sequence.push("status:COMMITTED");
          return HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: requestId,
            status: "COMMITTED",
            client_action: "RESPONSE_AVAILABLE",
            error_code: null,
            retry_after_seconds: null,
            response: committedActionResponseFixture(requestId, 2),
          });
        },
      ),
    );

    const mutationKeys = ["Create.Canonical-1", "Entry.Canonical-1"];
    const idempotencyKeyFactory = vi.fn(() => mutationKeys.shift()!);
    const user = userEvent.setup();
    const rendered = renderActionApp({
      eligiblePlayerCharacters: {
        eligible_player_characters: [],
        truncated: false,
      },
      idempotencyKeyFactory,
      pollWait,
    });
    expect(await screen.findByLabelText("副本")).toHaveValue(
      "death_certificate",
    );
    assertRenderedScenarioCatalogPresentation(rendered.container);
    expect(
      rendered.container.querySelector(".demo-warning")?.textContent,
    ).toBe(exactDemoWarning);

    await user.click(
      await screen.findByRole("button", {
        name: "创建最小 Player Character",
      }),
    );
    expect(await screen.findByText(/已选择服务器返回的创建结果/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "进入 Run" }));
    await waitFor(() => expect(viewVersions).toEqual([0]));
    await waitFor(() =>
      assertRenderedCanonicalPresentation(rendered.container, 0),
    );
    assertCanonicalDecisionPresentation(servedViews.at(-1)!, 0);
    for (const choice of canonicalChoiceSets[0]!) {
      expect(screen.getByRole("button", { name: choice.label })).toBeVisible();
    }
    expect(creationBody).toEqual(minimalPlayerCharacterCreationFixture);
    expect(entryBody).toEqual({
      player_character_id: playerCharacterFixture.player_character_id.value,
      expected_record_revision: playerCharacterFixture.record_revision.value,
      scenario_id: "death_certificate",
    });
    expect(idempotencyKeyFactory).toHaveBeenCalledTimes(2);
    expect(legacySessionCreates).toBe(0);

    async function submitAndAwaitView(
      actionNumber: number,
      submit: () => Promise<void>,
    ) {
      await submit();
      await waitFor(() =>
        expect(viewVersions).toHaveLength(actionNumber + 1),
      );
      expect(viewVersions.at(-1)).toBe(actionNumber);
      await waitFor(() =>
        assertRenderedCanonicalPresentation(rendered.container, actionNumber),
      );
      assertCanonicalDecisionPresentation(servedViews.at(-1)!, actionNumber);
      for (const choice of canonicalChoiceSets[actionNumber] ?? []) {
        expect(screen.getByRole("button", { name: choice.label })).toBeVisible();
      }
    }

    const choiceLabels = [
      "有规律地移动仍可控制的手指",
      "要求复核生命指标",
      "核对档案时间与签发链",
      "进入地下观察层核验对象",
      "争取暂停处置规程",
      "要求协调员承担复核责任",
      "公开推翻错误记录",
      "执行最终暂停",
    ];
    let choiceIndex = 0;
    await submitAndAwaitView(1, () =>
      user.click(
        screen.getByRole("button", { name: choiceLabels[choiceIndex++]! }),
      ),
    );

    const customForm = actionForm("提交自由行动");
    await user.type(
      within(customForm).getByLabelText("行动描述"),
      "请协调员复核我的连续回应和生命体征",
    );
    await submitAndAwaitView(2, () =>
      user.click(
        within(customForm).getByRole("button", { name: "提交自由行动" }),
      ),
    );
    for (const actionNumber of [3, 4]) {
      await submitAndAwaitView(actionNumber, () =>
        user.click(screen.getByRole("button", { name: "提交继续" })),
      );
    }
    await submitAndAwaitView(5, () =>
      user.click(
        screen.getByRole("button", { name: choiceLabels[choiceIndex++]! }),
      ),
    );
    for (const actionNumber of [6, 7, 8]) {
      await submitAndAwaitView(actionNumber, () =>
        user.click(screen.getByRole("button", { name: "提交继续" })),
      );
    }
    await submitAndAwaitView(9, () =>
      user.click(
        screen.getByRole("button", { name: choiceLabels[choiceIndex++]! }),
      ),
    );

    const firstExploreForm = actionForm("提交探索");
    await user.type(
      within(firstExploreForm).getByLabelText("行动描述"),
      "沿记录与档案审计路径核对签发时间",
    );
    await submitAndAwaitView(10, () =>
      user.click(
        within(firstExploreForm).getByRole("button", { name: "提交探索" }),
      ),
    );
    const secondExploreForm = actionForm("提交探索");
    await user.clear(within(secondExploreForm).getByLabelText("行动描述"));
    await user.type(
      within(secondExploreForm).getByLabelText("行动描述"),
      "核对日志时间顺序以及规程反馈",
    );
    await submitAndAwaitView(11, () =>
      user.click(
        within(secondExploreForm).getByRole("button", { name: "提交探索" }),
      ),
    );
    await submitAndAwaitView(12, () =>
      user.click(
        screen.getByRole("button", { name: choiceLabels[choiceIndex++]! }),
      ),
    );

    const observeForm = actionForm("提交观察");
    await user.type(
      within(observeForm).getByLabelText("行动描述"),
      "复核地下患者的生命体征与连续监测历史",
    );
    await submitAndAwaitView(13, () =>
      user.click(
        within(observeForm).getByRole("button", { name: "提交观察" }),
      ),
    );
    for (const actionNumber of [14, 15]) {
      await submitAndAwaitView(actionNumber, () =>
        user.click(screen.getByRole("button", { name: "提交继续" })),
      );
    }
    for (const actionNumber of [16, 17, 18, 19]) {
      await submitAndAwaitView(actionNumber, () =>
        user.click(
          screen.getByRole("button", {
            name: choiceLabels[choiceIndex++]!,
          }),
        ),
      );
    }

    expect(submittedBodies).toEqual(
      expectedActions.map((expected, index) => ({
        turn_id: `opaque-turn-${index + 1}`,
        client_request_id: `opaque-request-${index + 1}`,
        ...expected,
      })),
    );
    expect(actionPostCount).toBe(19);
    expect(
      submittedBodies.filter(
        (body) => body.client_request_id === "opaque-request-2",
      ),
    ).toHaveLength(1);
    expect(requestStatusCallSequence).toEqual([
      { requestId: "opaque-request-2", status: "PENDING" },
      { requestId: "opaque-request-2", status: "COMMITTED" },
    ]);
    expect(confirmed202Sequence).toEqual([
      "action:2",
      "status:PENDING",
      "status:COMMITTED",
      "view:2",
    ]);
    expect(pollWait).toHaveBeenCalledTimes(1);
    expect(pollWait.mock.calls[0]?.[0]).toBe(2_000);
    expect(viewVersions).toEqual(
      Array.from({ length: 20 }, (_, version) => version),
    );
    expect(screen.getByText("ENDED")).toBeVisible();
    expect(screen.getByText("RESOLVED")).toBeVisible();
    expect(
      screen.getByText(
        "Ending ID：death_certificate.ending.protocol_broken",
      ),
    ).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "规程已中断" }),
    ).toBeVisible();
    expect(
      screen.getByText(
        "处置规程被阻止，你的生命状态获得了可验证的承认。",
      ),
    ).toBeVisible();
    expect(screen.getByText("disposal_protocol：4 / 12")).toBeVisible();
    expect(
      screen.getByText("predicted_death_deadline：12 / 13"),
    ).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "执行最终暂停" }),
    ).not.toBeInTheDocument();
  });

  it("renders and submits every current FREE_ACTIONS contract with only allowed inputs and targets", async () => {
    const actionBodies: Array<Record<string, unknown>> = [];
    let viewVersion = 1;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(freeActionViewFixture(viewVersion)),
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          const body = (await request.json()) as Record<string, unknown>;
          actionBodies.push(body);
          viewVersion += 1;
          const requestId = body.client_request_id as string;
          return HttpResponse.json(
            body.action_type === "CONTINUE"
              ? synchronousActionResponseFixture(requestId, viewVersion)
              : committedActionResponseFixture(requestId, viewVersion),
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);

    expect(screen.getByRole("button", { name: "提交继续" })).toBeEnabled();
    for (const name of [
      "提交交谈",
      "提交自由行动",
      "提交探索",
      "提交观察",
      "提交移动",
    ]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
    expect(screen.getByText(/action_affordances · FREE_ACTIONS/)).toBeVisible();

    const talkForm = actionForm("提交交谈");
    await user.selectOptions(
      within(talkForm).getByLabelText("目标（可选）"),
      "npc.public.guide",
    );
    await user.type(
      within(talkForm).getByLabelText("对话内容"),
      "请复核当前公开信号",
    );
    await user.click(within(talkForm).getByRole("button", { name: "提交交谈" }));
    await waitFor(() => expect(actionBodies).toHaveLength(1));
    await waitFor(() =>
      expect(
        screen.getByText("空闲：当前 View 已确认，可以选择公开行动。"),
      ).toBeVisible(),
    );

    const descriptionActions = [
      ["自由行动", "CUSTOM", "尝试记录公开信号", false],
      ["探索", "EXPLORE", "探索公开区域", true],
      ["观察", "OBSERVE", "观察公开设备", false],
      ["移动", "MOVE", "移动到公开位置", true],
    ] as const;
    let expectedActionCount = 1;
    for (const [label, , description, withTarget] of
      descriptionActions) {
      const form = actionForm(`提交${label}`);
      if (withTarget) {
        await user.selectOptions(
          within(form).getByLabelText("目标（可选）"),
          "npc.public.guide",
        );
      }
      await user.type(within(form).getByLabelText("行动描述"), description);
      await user.click(
        within(form).getByRole("button", { name: `提交${label}` }),
      );
      expectedActionCount += 1;
      await waitFor(() =>
        expect(actionBodies).toHaveLength(expectedActionCount),
      );
      await waitFor(() =>
        expect(
          screen.getByText("空闲：当前 View 已确认，可以选择公开行动。"),
        ).toBeVisible(),
      );
    }

    await user.click(screen.getByRole("button", { name: "提交继续" }));
    await waitFor(() => expect(actionBodies).toHaveLength(6));

    expect(actionBodies).toEqual([
      {
        turn_id: "opaque-turn-1",
        client_request_id: "opaque-request-1",
        action_type: "TALK",
        dialogue: "请复核当前公开信号",
        target_ids: ["npc.public.guide"],
      },
      {
        turn_id: "opaque-turn-2",
        client_request_id: "opaque-request-2",
        action_type: "CUSTOM",
        description: "尝试记录公开信号",
      },
      {
        turn_id: "opaque-turn-3",
        client_request_id: "opaque-request-3",
        action_type: "EXPLORE",
        description: "探索公开区域",
        target_ids: ["npc.public.guide"],
      },
      {
        turn_id: "opaque-turn-4",
        client_request_id: "opaque-request-4",
        action_type: "OBSERVE",
        description: "观察公开设备",
      },
      {
        turn_id: "opaque-turn-5",
        client_request_id: "opaque-request-5",
        action_type: "MOVE",
        description: "移动到公开位置",
        target_ids: ["npc.public.guide"],
      },
      {
        turn_id: "opaque-turn-6",
        client_request_id: "opaque-request-6",
        action_type: "CONTINUE",
      },
    ]);
  });

  it("normalizes DESCRIPTION text before displaying limits, disabling, and submitting", async () => {
    let actionPosts = 0;
    let actionBody: unknown;
    let viewReads = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(freeActionViewFixture(viewReads));
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          actionPosts += 1;
          actionBody = await request.json();
          return HttpResponse.json(
            synchronousActionResponseFixture("opaque-request-1", 2),
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);
    const form = actionForm("提交观察");
    const input = within(form).getByLabelText("行动描述");
    const submit = within(form).getByRole("button", { name: "提交观察" });
    const emoji150 = "😀".repeat(150);

    fireEvent.change(input, { target: { value: ` ${emoji150}` } });
    expect(within(form).getByText("150 / 150")).toBeVisible();
    expect(submit).toBeEnabled();

    fireEvent.change(input, { target: { value: ` ${emoji150} ` } });
    expect(within(form).getByText("150 / 150")).toBeVisible();
    expect(submit).toBeEnabled();

    fireEvent.change(input, {
      target: { value: ` ${"😀".repeat(151)}` },
    });
    expect(within(form).getByText(/151 \/ 150/)).toHaveTextContent(
      "已超过公开合同上限",
    );
    expect(submit).toBeDisabled();

    fireEvent.change(input, { target: { value: "   " } });
    expect(within(form).getByText("0 / 150")).toBeVisible();
    expect(submit).toBeDisabled();

    fireEvent.change(input, { target: { value: ` ${emoji150} ` } });
    await user.click(submit);

    await waitFor(() => expect(viewReads).toBe(2));
    expect(actionPosts).toBe(1);
    expect(actionBody).toEqual({
      turn_id: "opaque-turn-1",
      client_request_id: "opaque-request-1",
      action_type: "OBSERVE",
      description: emoji150,
    });
  });

  it("uses the normalized TALK candidate at the 200/201 code-point boundary", async () => {
    let actionPosts = 0;
    let actionBody: unknown;
    let viewReads = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(freeActionViewFixture(viewReads));
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          actionPosts += 1;
          actionBody = await request.json();
          return HttpResponse.json(
            synchronousActionResponseFixture("opaque-request-1", 2),
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);
    const form = actionForm("提交交谈");
    const input = within(form).getByLabelText("对话内容");
    const submit = within(form).getByRole("button", { name: "提交交谈" });
    const emoji200 = "😀".repeat(200);

    fireEvent.change(input, { target: { value: ` ${emoji200} ` } });
    expect(within(form).getByText("200 / 200")).toBeVisible();
    expect(submit).toBeEnabled();

    fireEvent.change(input, {
      target: { value: ` ${"😀".repeat(201)} ` },
    });
    expect(within(form).getByText(/201 \/ 200/)).toHaveTextContent(
      "已超过公开合同上限",
    );
    expect(submit).toBeDisabled();

    fireEvent.change(input, { target: { value: ` ${emoji200} ` } });
    await user.click(submit);

    await waitFor(() => expect(viewReads).toBe(2));
    expect(actionPosts).toBe(1);
    expect(actionBody).toEqual({
      turn_id: "opaque-turn-1",
      client_request_id: "opaque-request-1",
      action_type: "TALK",
      dialogue: emoji200,
    });
  });

  it("accepts additive affordance/action/target fields without creating UI authority", async () => {
    let actionPosts = 0;
    let actionBody: unknown;
    let viewReads = 0;
    const baseView = freeActionViewFixture();
    const additiveView = {
      ...baseView,
      action_affordances: {
        ...baseView.action_affordances,
        future_actions: [
          {
            action_type: "SYSTEM_OVERRIDE",
            label: "扩展字段伪造行动",
          },
        ],
        actions: baseView.action_affordances.actions.map((action) =>
          action.action_type === "TALK"
            ? {
                ...action,
                future_action_type: "SYSTEM_OVERRIDE",
                future_targets: [
                  {
                    target_id: "npc.hidden.extension",
                    display_name: "隐藏扩展目标",
                  },
                ],
                targets: action.targets.map((target) => ({
                  ...target,
                  future_target_authority: "must be stripped",
                })),
              }
            : action,
        ),
      },
    };
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(
            viewReads === 1 ? additiveView : freeActionViewFixture(2),
          );
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          actionPosts += 1;
          actionBody = await request.json();
          return HttpResponse.json(
            committedActionResponseFixture("opaque-request-1", 2),
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);

    expect(
      screen.queryByRole("button", { name: "扩展字段伪造行动" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("option", { name: "隐藏扩展目标" }),
    ).not.toBeInTheDocument();
    const form = actionForm("提交交谈");
    await user.selectOptions(
      within(form).getByLabelText("目标（可选）"),
      "npc.public.guide",
    );
    await user.type(within(form).getByLabelText("对话内容"), "只提交已知字段");
    await user.click(within(form).getByRole("button", { name: "提交交谈" }));

    await waitFor(() => expect(viewReads).toBe(2));
    expect(actionPosts).toBe(1);
    expect(actionBody).toEqual({
      turn_id: "opaque-turn-1",
      client_request_id: "opaque-request-1",
      action_type: "TALK",
      dialogue: "只提交已知字段",
      target_ids: ["npc.public.guide"],
    });
  });

  it("accepts additive choice fields without creating a decision action", async () => {
    let actionPosts = 0;
    let actionBody: unknown;
    let viewReads = 0;
    const additiveDecisionView = {
      ...activeViewFixture,
      action_affordances: {
        ...activeViewFixture.action_affordances,
        future_choices: [
          {
            action_type: "CHOOSE",
            choice_id: "choice.hidden.extension",
            label: "扩展字段伪造选择",
          },
        ],
        choices: activeViewFixture.action_affordances.choices.map((choice) => ({
          ...choice,
          future_choice_id: "choice.hidden.extension",
        })),
      },
    };
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(
            viewReads === 1 ? additiveDecisionView : endedViewFixture(),
          );
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          actionPosts += 1;
          actionBody = await request.json();
          return HttpResponse.json(
            synchronousActionResponseFixture("opaque-request-1", 7),
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);

    expect(
      screen.queryByRole("button", { name: "扩展字段伪造选择" }),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "检查灯塔信号" }));

    await waitFor(() => expect(viewReads).toBe(2));
    expect(actionPosts).toBe(1);
    expect(actionBody).toEqual({
      turn_id: "opaque-turn-1",
      client_request_id: "opaque-request-1",
      action_type: "CHOOSE",
      decision_id: "decision.public.bound-token",
      choice_id: "choice.public.inspect-light",
    });
  });

  it("treats lowercase public ActionResponse codes as a valid HTTP 200 lifecycle", async () => {
    let actionPosts = 0;
    let viewReads = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(freeActionViewFixture(viewReads));
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () => {
          actionPosts += 1;
          return HttpResponse.json({
            ...synchronousActionResponseFixture("opaque-request-1", 2),
            result_code: "scenario.auto_beat_advanced",
            feedback_code: "scenario feedback available",
          });
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);

    await user.click(screen.getByRole("button", { name: "提交继续" }));

    await waitFor(() => expect(viewReads).toBe(2));
    expect(actionPosts).toBe(1);
    expect(screen.getByText("权威 View：当前")).toBeVisible();
    expect(screen.queryByText(/transport-uncertain/)).not.toBeInTheDocument();
  });

  it("submits a displayed DECISION choice and confirms ACTIVE to ENDED only through a new View", async () => {
    let viewReads = 0;
    let actionPosts = 0;
    let actionBody: unknown;
    const decisionView = {
      ...activeViewFixture,
      narrative_frame: {
        ...activeViewFixture.narrative_frame,
        suggested_actions: activeViewFixture.narrative_frame.suggested_actions.map(
          (action) => ({
            ...action,
            label_hint: "叙事提示不可执行",
          }),
        ),
      },
    };
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(
            viewReads === 1 ? decisionView : endedViewFixture("RESOLVED"),
          );
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          actionPosts += 1;
          actionBody = await request.json();
          return HttpResponse.json(
            synchronousActionResponseFixture("opaque-request-1", 7),
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);

    expect(screen.getByText("叙事提示不可执行")).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "叙事提示不可执行" }),
    ).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "检查灯塔信号" }),
    );

    expect(await screen.findByRole("heading", { name: "回声确认" })).toBeVisible();
    expect(screen.getByText("RESOLVED")).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "检查灯塔信号" })).not.toBeInTheDocument();
    expect(actionBody).toEqual({
      turn_id: "opaque-turn-1",
      client_request_id: "opaque-request-1",
      action_type: "CHOOSE",
      decision_id: "decision.public.bound-token",
      choice_id: "choice.public.inspect-light",
    });
    expect(actionPosts).toBe(1);
    expect(viewReads).toBe(2);
  });
});

describe("committed Dynamic Narrative action evidence", () => {
  function installDirectEvidenceHandlers(
    feedbackParameters: ActionResponse["feedback_parameters"],
    responseUpdate: Partial<ActionResponse> = {},
  ) {
    let viewReads = 0;
    const submission = dynamicSuggestionSubmission(
      0,
      0,
      initialNoNpcSuggestionTexts[0],
    );
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          const stateVersion = viewReads;
          viewReads += 1;
          return HttpResponse.json(
            dynamicSuggestionViewFixture({
              stateVersion,
              suggestionTexts: initialNoNpcSuggestionTexts,
            }),
          );
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () =>
          HttpResponse.json({
            ...dynamicCommittedActionResponse({
              clientRequestId: submission.client_request_id,
              stateVersion: 1,
              feedbackParameters,
            }),
            ...responseUpdate,
          }),
      ),
    );
    return { submission, viewReads: () => viewReads };
  }

  it("retains a direct committed response through refresh and renders numeric zero", async () => {
    const { viewReads } = installDirectEvidenceHandlers({
      outcome_result: "SUCCESS",
      public_fact_count: 0,
    });
    const user = userEvent.setup();
    const rendered = renderActionApp();
    await loadSession(user);

    expect(screen.queryByText(/^NEW_PUBLIC_FACTS=/)).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: initialNoNpcSuggestionTexts[0] }),
    );
    await waitFor(() => expect(viewReads()).toBe(2));

    const evidence = screen.getByRole("region", {
      name: "Dynamic Narrative action evidence",
    });
    expect(within(evidence).getByText("REVISION=1")).toBeVisible();
    expect(within(evidence).getByText("NEW_STORY_SEGMENTS=1")).toBeVisible();
    expect(within(evidence).getByText("SUGGESTIONS=3")).toBeVisible();
    expect(within(evidence).getByText("NEW_PUBLIC_FACTS=0")).toBeVisible();
    expect(rendered.container).not.toHaveTextContent("public-note-");
    expect(rendered.container).not.toHaveTextContent("allocated public fact");
  });

  it("renders the exact nonzero count from a 202-to-COMMITTED stored response", async () => {
    let viewReads = 0;
    let statusReads = 0;
    const submission = dynamicSuggestionSubmission(
      0,
      0,
      initialNoNpcSuggestionTexts[0],
    );
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          const stateVersion = viewReads;
          viewReads += 1;
          return HttpResponse.json(
            dynamicSuggestionViewFixture({
              stateVersion,
              suggestionTexts: initialNoNpcSuggestionTexts,
            }),
          );
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () =>
          HttpResponse.json(
            pendingActionResponseFixture(submission.client_request_id),
            { status: 202 },
          ),
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/${submission.client_request_id}`,
        () => {
          statusReads += 1;
          return HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: submission.client_request_id,
            status: "COMMITTED",
            client_action: "RESPONSE_AVAILABLE",
            error_code: null,
            retry_after_seconds: null,
            response: dynamicCommittedActionResponse({
              clientRequestId: submission.client_request_id,
              stateVersion: 1,
              feedbackParameters: {
                outcome_result: "SUCCESS",
                public_fact_count: 3,
              },
            }),
          });
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);

    await user.click(
      screen.getByRole("button", { name: initialNoNpcSuggestionTexts[0] }),
    );
    expect(await screen.findByText("NEW_PUBLIC_FACTS=3")).toBeVisible();
    expect(screen.getByText("REVISION=1")).toBeVisible();
    expect(screen.getByText("NEW_STORY_SEGMENTS=1")).toBeVisible();
    expect(screen.getByText("SUGGESTIONS=3")).toBeVisible();
    expect(viewReads).toBe(2);
    expect(statusReads).toBe(1);
  });

  it.each(
    [
      ["missing", { outcome_result: "SUCCESS" }],
      ["null", { outcome_result: "SUCCESS", public_fact_count: null }],
      ["string", { outcome_result: "SUCCESS", public_fact_count: "1" }],
      ["boolean", { outcome_result: "SUCCESS", public_fact_count: true }],
      ["fractional", { outcome_result: "SUCCESS", public_fact_count: 1.5 }],
      ["negative", { outcome_result: "SUCCESS", public_fact_count: -1 }],
      ["above maximum", { outcome_result: "SUCCESS", public_fact_count: 4 }],
    ] satisfies ReadonlyArray<
      readonly [string, ActionResponse["feedback_parameters"]]
    >,
  )("fails closed for %s public_fact_count feedback", async (_case, feedback) => {
    const { viewReads } = installDirectEvidenceHandlers(feedback);
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);

    await user.click(
      screen.getByRole("button", { name: initialNoNpcSuggestionTexts[0] }),
    );
    await waitFor(() => expect(viewReads()).toBe(2));

    expect(
      screen.queryByRole("region", {
        name: "Dynamic Narrative action evidence",
      }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/^NEW_PUBLIC_FACTS=/)).not.toBeInTheDocument();
    expect(screen.queryByText("NEW_PUBLIC_FACTS=0")).not.toBeInTheDocument();
  });

  it.each([
    ["wrong revision", { resulting_state_version: 2 }],
    [
      "wrong lifecycle",
      {
        result_code: "NARRATIVE_OUTCOME_COMMITTED",
        feedback_code: "NARRATIVE_COMMITTED",
      },
    ],
  ] satisfies ReadonlyArray<readonly [string, Partial<ActionResponse>]>) (
    "fails closed for a committed response with %s association",
    async (_case, responseUpdate) => {
      const { viewReads } = installDirectEvidenceHandlers(
        { outcome_result: "SUCCESS", public_fact_count: 2 },
        responseUpdate,
      );
      const user = userEvent.setup();
      renderActionApp();
      await loadSession(user);

      await user.click(
        screen.getByRole("button", { name: initialNoNpcSuggestionTexts[0] }),
      );
      await waitFor(() => expect(viewReads()).toBe(2));

      expect(screen.queryByText(/^NEW_PUBLIC_FACTS=/)).not.toBeInTheDocument();
    },
  );
});

describe("HTTP 202 request-status lifecycle", () => {
  it("polls one 202 request through PENDING to COMMITTED and then reads a full View", async () => {
    let actionPosts = 0;
    let statusReads = 0;
    let viewReads = 0;
    const observedStatusIds: string[] = [];
    const pollStarted = deferred<void>();
    const pollGate = deferred<void>();
    const pollWait = vi.fn(
      async (...parameters: [number, AbortSignal]) => {
        void parameters;
        pollStarted.resolve();
        await pollGate.promise;
      },
    );
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(freeActionViewFixture(viewReads));
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () => {
          actionPosts += 1;
          return HttpResponse.json(
            pendingActionResponseFixture("opaque-request-1"),
            { status: 202 },
          );
        },
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/:requestId`,
        ({ params }) => {
          statusReads += 1;
          observedStatusIds.push(String(params.requestId));
          expect(storedRecoveryRecord()).toEqual({
            version: 1,
            session_id: "session-public-1",
            client_request_id: "opaque-request-1",
          });
          if (statusReads === 1) {
            return HttpResponse.json({
              session_id: "session-public-1",
              client_request_id: "opaque-request-1",
              status: "PENDING",
              client_action: "POLL_SAME_REQUEST",
              error_code: null,
              retry_after_seconds: 2,
              response: null,
            });
          }
          return HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: "opaque-request-1",
            status: "COMMITTED",
            client_action: "RESPONSE_AVAILABLE",
            error_code: null,
            retry_after_seconds: null,
            response: committedActionResponseFixture("opaque-request-1", 99),
          });
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp({ pollWait });
    await loadSession(user);

    const talkForm = actionForm("提交交谈");
    await user.type(
      within(talkForm).getByLabelText("对话内容"),
      "请复核公开信号",
    );
    await user.click(within(talkForm).getByRole("button", { name: "提交交谈" }));

    await pollStarted.promise;
    expect(screen.getAllByText("权威 View 已推进到版本 1。")).toHaveLength(2);
    expect(screen.queryAllByText("权威 View 已推进到版本 2。")).toHaveLength(0);
    expect(screen.queryAllByText("权威 View 已推进到版本 99。")).toHaveLength(0);
    expect(within(talkForm).getByRole("button", { name: "提交交谈" })).toBeDisabled();
    expect(actionPosts).toBe(1);
    expect(statusReads).toBe(1);
    expect(viewReads).toBe(1);

    pollGate.resolve();
    await waitFor(() => expect(viewReads).toBe(2));
    expect(actionPosts).toBe(1);
    expect(statusReads).toBe(2);
    expect(observedStatusIds).toEqual([
      "opaque-request-1",
      "opaque-request-1",
    ]);
    expect(pollWait).toHaveBeenCalledTimes(1);
    expect(pollWait.mock.calls[0]?.[0]).toBe(2_000);
    expect(screen.getByText("权威 View：当前")).toBeVisible();
    expect(screen.getAllByText("权威 View 已推进到版本 2。")).toHaveLength(2);
    expect(screen.queryAllByText("权威 View 已推进到版本 99。")).toHaveLength(0);
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });
  });

  it.each([
    ["Session ID", "other-session", "opaque-request-1"],
    ["client request ID", "session-public-1", "other-request"],
  ] as const)(
    "abandons the same-page confirmed-202 identity after a %s mismatch",
    async (_label, responseSessionId, responseRequestId) => {
      let actionPosts = 0;
      let statusReads = 0;
      let viewReads = 0;
      const statusGate = deferred<void>();
      const statusStarted = deferred<void>();
      const idempotencyKeyFactory = vi.fn(() => "must-not-be-created");
      const actionIdentityFactory = vi.fn(() => ({
        turnId: "opaque-turn-1",
        clientRequestId: "opaque-request-1",
      }));
      server.use(
        scenarioHandler(),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () => {
            viewReads += 1;
            return HttpResponse.json(freeActionViewFixture(viewReads));
          },
        ),
        http.post(
          `${apiOrigin}/v1/sessions/session-public-1/actions`,
          () => {
            actionPosts += 1;
            return HttpResponse.json(
              pendingActionResponseFixture("opaque-request-1"),
              { status: 202 },
            );
          },
        ),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/requests/opaque-request-1`,
          async () => {
            statusReads += 1;
            expect(storedRecoveryRecord()).toEqual({
              version: 1,
              session_id: "session-public-1",
              client_request_id: "opaque-request-1",
            });
            statusStarted.resolve();
            await statusGate.promise;
            return HttpResponse.json({
              session_id: responseSessionId,
              client_request_id: responseRequestId,
              status: "PENDING",
              client_action: "POLL_SAME_REQUEST",
              error_code: null,
              retry_after_seconds: 2,
              response: null,
            });
          },
        ),
      );
      const user = userEvent.setup();
      const rendered = renderActionApp({
        actionIdentityFactory,
        idempotencyKeyFactory,
      });
      await loadSession(user);

      await user.click(screen.getByRole("button", { name: "提交继续" }));
      await statusStarted.promise;
      expect(storedRecoveryRecord()).toEqual({
        version: 1,
        session_id: "session-public-1",
        client_request_id: "opaque-request-1",
      });
      statusGate.resolve();

      expect(
        await screen.findByText(/恢复身份与已保存记录不匹配/),
      ).toBeVisible();
      expect(storedRecoveryRecord()).toBeNull();
      expect(screen.queryByText("当前 Session：session-public-1")).not.toBeInTheDocument();
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText(/pending-status-unknown|无法确认其最终 request status/),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "手动重试安全 GET" }),
      ).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "进入 Run" })).toBeEnabled();
      expect(actionPosts).toBe(1);
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(1);
      expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
      expect(idempotencyKeyFactory).not.toHaveBeenCalled();

      rendered.unmount();
      renderActionApp({ actionIdentityFactory, idempotencyKeyFactory });
      await screen.findByRole("button", { name: "进入 Run" });
      await act(async () => Promise.resolve());
      expect(actionPosts).toBe(1);
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(1);
      expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
      expect(idempotencyKeyFactory).not.toHaveBeenCalled();
    },
  );

  it("keeps a same-page identity mismatch locked until its pending record is safely removed", async () => {
    let actionPosts = 0;
    let statusReads = 0;
    let viewReads = 0;
    let failRemove = false;
    const idempotencyKeyFactory = vi.fn(() => "must-not-be-created");
    const actionIdentityFactory = vi.fn(() => ({
      turnId: "opaque-turn-1",
      clientRequestId: "opaque-request-1",
    }));
    const originalRemoveItem = Storage.prototype.removeItem;
    const removeItemSpy = vi
      .spyOn(Storage.prototype, "removeItem")
      .mockImplementation(function (this: Storage, key: string) {
        if (failRemove) {
          throw new DOMException("remove blocked", "SecurityError");
        }
        originalRemoveItem.call(this, key);
      });
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(freeActionViewFixture(viewReads));
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () => {
          actionPosts += 1;
          return HttpResponse.json(
            pendingActionResponseFixture("opaque-request-1"),
            { status: 202 },
          );
        },
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/opaque-request-1`,
        () => {
          statusReads += 1;
          expect(storedRecoveryRecord()).toEqual({
            version: 1,
            session_id: "session-public-1",
            client_request_id: "opaque-request-1",
          });
          failRemove = true;
          return HttpResponse.json({
            session_id: "other-session",
            client_request_id: "opaque-request-1",
            status: "PENDING",
            client_action: "POLL_SAME_REQUEST",
            error_code: null,
            retry_after_seconds: 2,
            response: null,
          });
        },
      ),
    );
    try {
      const user = userEvent.setup();
      renderActionApp({ actionIdentityFactory, idempotencyKeyFactory });
      await loadSession(user);

      await user.click(screen.getByRole("button", { name: "提交继续" }));

      const storageAlert = (
        await screen.findByRole("heading", { name: "sessionStorage 安全锁定" })
      ).closest("section");
      if (!(storageAlert instanceof HTMLElement)) {
        throw new Error("storage safety alert must be rendered");
      }
      expect(storedRecoveryRecord()).toEqual({
        version: 1,
        session_id: "session-public-1",
        client_request_id: "opaque-request-1",
      });
      expect(screen.getByRole("button", { name: "进入 Run" })).toBeDisabled();
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();
      expect(screen.queryByText("当前 Session：session-public-1")).not.toBeInTheDocument();
      expect(within(storageAlert).getAllByRole("button")).toHaveLength(1);
      expect(
        within(storageAlert).getByRole("button", {
          name: "重试安全清除恢复记录",
        }),
      ).toBeEnabled();
      expect(actionPosts).toBe(1);
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(1);
      expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
      expect(idempotencyKeyFactory).not.toHaveBeenCalled();

      failRemove = false;
      await user.click(
        within(storageAlert).getByRole("button", {
          name: "重试安全清除恢复记录",
        }),
      );

      expect(storedRecoveryRecord()).toBeNull();
      expect(screen.getByRole("button", { name: "进入 Run" })).toBeEnabled();
      expect(
        screen.queryByRole("heading", { name: "sessionStorage 安全锁定" }),
      ).not.toBeInTheDocument();
      expect(actionPosts).toBe(1);
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(1);
      expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
      expect(idempotencyKeyFactory).not.toHaveBeenCalled();
    } finally {
      removeItemSpy.mockRestore();
    }
  });

  it("follows STALE/REFRESH_VIEW with a View GET and no action replay", async () => {
    let actionPosts = 0;
    let statusReads = 0;
    let viewReads = 0;
    const pollWait = vi.fn(
      async (...parameters: [number, AbortSignal]) => {
        void parameters;
      },
    );
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(freeActionViewFixture(viewReads));
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () => {
          actionPosts += 1;
          return HttpResponse.json(
            pendingActionResponseFixture("opaque-request-1"),
            { status: 202 },
          );
        },
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/opaque-request-1`,
        () => {
          statusReads += 1;
          return HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: "opaque-request-1",
            status: "STALE",
            client_action: "REFRESH_VIEW",
            error_code: "NARRATIVE_REQUEST_STALE",
            retry_after_seconds: null,
            response: null,
          });
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp({ pollWait });
    await loadSession(user);

    await user.click(screen.getByRole("button", { name: "提交继续" }));

    await waitFor(() => expect(viewReads).toBe(2));
    expect(actionPosts).toBe(1);
    expect(statusReads).toBe(1);
    expect(pollWait).not.toHaveBeenCalled();
    expect(screen.getByText("权威 View：当前")).toBeVisible();
    expect(screen.getAllByText("权威 View 已推进到版本 2。")).toHaveLength(2);
    expect(screen.queryAllByText("权威 View 已推进到版本 3。")).toHaveLength(0);
  });

  it.each([
    [
      "OUTCOME_UNKNOWN",
      "NARRATIVE_OUTCOME_UNKNOWN",
      "outcome-unknown",
    ],
    ["FAILED", "NARRATIVE_REQUEST_FAILED", "request-failed"],
  ] as const)(
    "does not POST again after %s/DO_NOT_RETRY",
    async (status, errorCode, staleKind) => {
      let actionPosts = 0;
      let statusReads = 0;
      let viewReads = 0;
      server.use(
        scenarioHandler(),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () => {
            viewReads += 1;
            return HttpResponse.json(freeActionViewFixture());
          },
        ),
        http.post(
          `${apiOrigin}/v1/sessions/session-public-1/actions`,
          () => {
            actionPosts += 1;
            return HttpResponse.json(
              pendingActionResponseFixture("opaque-request-1"),
              { status: 202 },
            );
          },
        ),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/requests/opaque-request-1`,
          () => {
            statusReads += 1;
            return HttpResponse.json({
              session_id: "session-public-1",
              client_request_id: "opaque-request-1",
              status,
              client_action: "DO_NOT_RETRY",
              error_code: errorCode,
              retry_after_seconds: null,
              response: null,
            });
          },
        ),
      );
      const user = userEvent.setup();
      renderActionApp();
      await loadSession(user);

      await user.click(screen.getByRole("button", { name: "提交继续" }));

      expect(
        await screen.findByText(`权威 View：可能 stale（${staleKind}）`),
      ).toBeVisible();
      const continueButton = screen.getByRole("button", { name: "提交继续" });
      expect(continueButton).toBeDisabled();
      fireEvent.click(continueButton);
      await act(async () => Promise.resolve());
      expect(actionPosts).toBe(1);
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(1);
      expect(screen.getAllByText("权威 View 已推进到版本 1。")).toHaveLength(2);
      expect(screen.queryAllByText("权威 View 已推进到版本 2。")).toHaveLength(0);
    },
  );

  it.each(["network", "invalid-response"] as const)(
    "keeps pending recovery after a normal %s status failure and retries only safe GETs after reload",
    async (failureKind) => {
      let actionPosts = 0;
      let statusReads = 0;
      let viewReads = 0;
      const idempotencyKeyFactory = vi.fn(() => "must-not-be-created");
      const actionIdentityFactory = vi.fn(() => ({
        turnId: "opaque-turn-1",
        clientRequestId: "opaque-request-1",
      }));
      server.use(
        scenarioHandler(),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () => {
            viewReads += 1;
            return HttpResponse.json(freeActionViewFixture(viewReads));
          },
        ),
        http.post(
          `${apiOrigin}/v1/sessions/session-public-1/actions`,
          () => {
            actionPosts += 1;
            return HttpResponse.json(
              pendingActionResponseFixture("opaque-request-1"),
              { status: 202 },
            );
          },
        ),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/requests/opaque-request-1`,
          () => {
            statusReads += 1;
            if (statusReads === 1) {
              return failureKind === "network"
                ? HttpResponse.error()
                : new HttpResponse('{"session_id":', {
                    headers: { "Content-Type": "application/json" },
                  });
            }
            return HttpResponse.json({
              session_id: "session-public-1",
              client_request_id: "opaque-request-1",
              status: "COMMITTED",
              client_action: "RESPONSE_AVAILABLE",
              error_code: null,
              retry_after_seconds: null,
              response: committedActionResponseFixture("opaque-request-1", 2),
            });
          },
        ),
      );
      const user = userEvent.setup();
      const rendered = renderActionApp({
        actionIdentityFactory,
        idempotencyKeyFactory,
      });
      await loadSession(user);

      await user.click(screen.getByRole("button", { name: "提交继续" }));

      expect(
        await screen.findByText("权威 View：可能 stale（pending-status-unknown）"),
      ).toBeVisible();
      expect(screen.getByText(/无法确认其最终 request status/)).toBeVisible();
      expect(screen.getByRole("button", { name: "提交继续" })).toBeDisabled();
      expect(actionPosts).toBe(1);
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(1);
      expect(storedRecoveryRecord()).toEqual({
        version: 1,
        session_id: "session-public-1",
        client_request_id: "opaque-request-1",
      });

      rendered.unmount();
      renderActionApp({ actionIdentityFactory, idempotencyKeyFactory });
      await screen.findByText("当前 Session：session-public-1");
      expect(screen.getByText("权威 View：当前")).toBeVisible();
      expect(actionPosts).toBe(1);
      expect(statusReads).toBe(2);
      expect(viewReads).toBe(2);
      expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
      expect(idempotencyKeyFactory).not.toHaveBeenCalled();
      expect(storedRecoveryRecord()).toEqual({
        version: 1,
        session_id: "session-public-1",
      });
    },
  );
});

describe("uncertain actions, stale Views and explicit refresh", () => {
  it.each([200, 202] as const)(
    "treats HTTP %i with an invalid ActionResponse as transport-uncertain until explicit View refresh",
    async (status) => {
      let actionPosts = 0;
      let statusReads = 0;
      let viewReads = 0;
      const invalidNarrativeText = "非法 ActionResponse 正文绝不能进入 View";
      const invalidFrameId = "frame.invalid.action-response";
      const pollWait = vi.fn(
        async (...parameters: [number, AbortSignal]) => {
          void parameters;
        },
      );
      server.use(
        scenarioHandler(),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () => {
            viewReads += 1;
            return HttpResponse.json(
              viewReads === 1
                ? freeActionViewFixture(1)
                : freeActionViewFixture(3),
            );
          },
        ),
        http.post(
          `${apiOrigin}/v1/sessions/session-public-1/actions`,
          () => {
            actionPosts += 1;
            const response =
              status === 200
                ? synchronousActionResponseFixture("opaque-request-1", 99)
                : pendingActionResponseFixture("opaque-request-1");
            return HttpResponse.json(
              {
                ...response,
                narrative_text:
                  status === 200 ? invalidNarrativeText : response.narrative_text,
                narrative_frame: {
                  ...response.narrative_frame,
                  frame_id: invalidFrameId,
                  future_server_field: "must make the response invalid",
                },
              },
              { status },
            );
          },
        ),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/requests/opaque-request-1`,
          () => {
            statusReads += 1;
            return HttpResponse.json({
              session_id: "session-public-1",
              client_request_id: "opaque-request-1",
              status: "COMMITTED",
              client_action: "RESPONSE_AVAILABLE",
              error_code: null,
              retry_after_seconds: null,
              response: committedActionResponseFixture("opaque-request-1", 2),
            });
          },
        ),
      );
      const user = userEvent.setup();
      renderActionApp({ pollWait });
      await loadSession(user);

      await user.click(screen.getByRole("button", { name: "提交继续" }));

      expect(
        await screen.findByText("权威 View：可能 stale（transport-uncertain）"),
      ).toBeVisible();
      expect(screen.getByText(/该行动可能已经到达服务器/)).toBeVisible();
      expect(screen.queryByText(/行动没有发生|行动未发生/)).not.toBeInTheDocument();
      const retainedScene = screen
        .getByRole("heading", { name: "当前场景：封锁线外" })
        .closest("section");
      expect(retainedScene).toHaveTextContent(
        "Frame frame.public-alpha.free-1 · 停止条件：CONTINUE",
      );
      const retainedNarrative = screen
        .getByRole("heading", { name: "当前公开正文" })
        .closest("section");
      if (!(retainedNarrative instanceof HTMLElement)) {
        throw new Error("retained View must include its current narrative section");
      }
      expect(
        within(retainedNarrative).getByText("权威 View 已推进到版本 1。"),
      ).toBeVisible();
      expect(screen.queryByText(invalidNarrativeText)).not.toBeInTheDocument();
      expect(screen.queryByText(new RegExp(invalidFrameId))).not.toBeInTheDocument();
      const retainedView = screen
        .getByRole("heading", { name: "雾港回声", level: 2 })
        .closest("article");
      if (!(retainedView instanceof HTMLElement)) {
        throw new Error("retained PlayerSessionView must remain rendered");
      }
      expect(
        within(retainedView).getByText("状态版本").closest("div"),
      ).toHaveTextContent("状态版本1");

      const actionSection = screen
        .getByRole("heading", { name: "当前可执行行动" })
        .closest("section");
      if (!(actionSection instanceof HTMLElement)) {
        throw new Error("action panel must be present while the retained View is stale");
      }
      for (const button of within(actionSection).getAllByRole("button")) {
        expect(button).toBeDisabled();
      }
      expect(
        within(screen.getByRole("alert")).getByRole("button", {
          name: "显式刷新当前权威 View",
        }),
      ).toBeEnabled();
      expect(actionPosts).toBe(1);
      expect(statusReads).toBe(0);
      expect(viewReads).toBe(1);
      expect(pollWait).not.toHaveBeenCalled();

      fireEvent.click(screen.getByRole("button", { name: "提交继续" }));
      await act(async () => Promise.resolve());
      expect(actionPosts).toBe(1);

      await user.click(
        screen.getByRole("button", { name: "显式刷新当前权威 View" }),
      );

      await waitFor(() => expect(viewReads).toBe(2));
      expect(screen.getByText("当前 Session：session-public-1")).toBeVisible();
      expect(screen.getByText("权威 View：当前")).toBeVisible();
      const refreshedScene = screen
        .getByRole("heading", { name: "当前场景：封锁线外" })
        .closest("section");
      expect(refreshedScene).toHaveTextContent(
        "Frame frame.public-alpha.free-3 · 停止条件：CONTINUE",
      );
      const refreshedNarrative = screen
        .getByRole("heading", { name: "当前公开正文" })
        .closest("section");
      if (!(refreshedNarrative instanceof HTMLElement)) {
        throw new Error("refreshed View must include its current narrative section");
      }
      expect(
        within(refreshedNarrative).getByText("权威 View 已推进到版本 3。"),
      ).toBeVisible();
      expect(screen.getByRole("button", { name: "提交继续" })).toBeEnabled();
      expect(screen.queryByText(invalidNarrativeText)).not.toBeInTheDocument();
      expect(screen.queryByText(new RegExp(invalidFrameId))).not.toBeInTheDocument();
      expect(actionPosts).toBe(1);
      expect(statusReads).toBe(0);
    },
  );

  it("keeps the last View stale after a transport-uncertain POST and refreshes without replay", async () => {
    let actionPosts = 0;
    let viewReads = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(freeActionViewFixture(viewReads));
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () => {
          actionPosts += 1;
          return HttpResponse.error();
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);

    await user.click(screen.getByRole("button", { name: "提交继续" }));

    expect(await screen.findByText(/行动响应无法确认/)).toBeVisible();
    expect(screen.getByText(/transport-uncertain/)).toBeVisible();
    expect(screen.getByRole("button", { name: "提交继续" })).toBeDisabled();
    expect(actionPosts).toBe(1);
    expect(viewReads).toBe(1);
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });

    await user.click(
      screen.getByRole("button", { name: "显式刷新当前权威 View" }),
    );

    await waitFor(() => expect(viewReads).toBe(2));
    expect(screen.getByText("权威 View：当前")).toBeVisible();
    expect(screen.getByRole("button", { name: "提交继续" })).toBeEnabled();
    expect(actionPosts).toBe(1);
  });

  it("marks the retained View stale when a confirmed action cannot fetch its new View", async () => {
    let actionPosts = 0;
    let viewReads = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          if (viewReads === 2) {
            return HttpResponse.json(
              errorFixture("INTERNAL_SERVER_ERROR", "Internal server error"),
              { status: 500 },
            );
          }
          return HttpResponse.json(freeActionViewFixture(viewReads));
        },
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () => {
          actionPosts += 1;
          return HttpResponse.json(
            synchronousActionResponseFixture("opaque-request-1", 2),
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);

    await user.click(screen.getByRole("button", { name: "提交继续" }));

    expect(
      await screen.findByText(/行动已获服务器确认，但新的完整 PlayerSessionView 获取失败/),
    ).toBeVisible();
    expect(screen.getByText(/confirmed-view-unavailable/)).toBeVisible();
    expect(screen.getByRole("button", { name: "提交继续" })).toBeDisabled();
    expect(actionPosts).toBe(1);

    await user.click(
      screen.getByRole("button", { name: "显式刷新当前权威 View" }),
    );
    await waitFor(() => expect(viewReads).toBe(3));
    expect(screen.getByText("权威 View：当前")).toBeVisible();
    expect(actionPosts).toBe(1);
  });
});

describe("foreground lock, operation identity and cancellation", () => {
  it("explicitly clears an in-flight action POST and isolates its late response", async () => {
    const actionGate = deferred<PublicActionSubmissionResult>();
    const actionStarted = deferred<void>();
    let actionSignal: AbortSignal | undefined;
    let actionPosts = 0;
    let statusReads = 0;
    let viewReads = 0;
    const actionIdentityFactory = vi.fn(() => ({
      turnId: "opaque-turn-1",
      clientRequestId: "opaque-request-1",
    }));
    const client = {
      listScenarios: async () => scenarioCatalogFixture,
      listEligiblePlayerCharacters: async () => eligiblePlayerCharactersFixture,
      getSessionView: async () => {
        viewReads += 1;
        return freeActionViewFixture(viewReads);
      },
      submitAction: async (
        _sessionId: string,
        _request: unknown,
        signal?: AbortSignal,
      ) => {
        actionPosts += 1;
        actionSignal = signal;
        actionStarted.resolve();
        return actionGate.promise;
      },
      getNarrativeRequestStatus: async () => {
        statusReads += 1;
        throw new Error("status must not be read");
      },
    } as unknown as PublicApiClient;
    const user = userEvent.setup();
    renderActionApp({ client, actionIdentityFactory });
    await loadSession(user);

    await user.click(screen.getByRole("button", { name: "提交继续" }));
    await actionStarted.promise;
    const clear = screen.getByRole("button", {
      name: "清除本标签页 Session",
    });
    expect(clear).toBeEnabled();
    await user.click(clear);

    expect(actionSignal?.aborted).toBe(true);
    expect(storedRecoveryRecord()).toBeNull();
    expect(screen.queryByText("当前 Session：session-public-1")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();

    actionGate.resolve({
      status: 200,
      response: synchronousActionResponseFixture("opaque-request-1", 2),
    });
    await act(async () => Promise.resolve());
    expect(actionPosts).toBe(1);
    expect(statusReads).toBe(0);
    expect(viewReads).toBe(1);
    expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "进入 Run" })).toBeEnabled();
  });

  it("explicitly clears during retry wait and prevents another status poll", async () => {
    const waitGate = deferred<void>();
    const waitStarted = deferred<void>();
    let operationSignal: AbortSignal | undefined;
    let actionPosts = 0;
    let statusReads = 0;
    let viewReads = 0;
    const actionIdentityFactory = vi.fn(() => ({
      turnId: "opaque-turn-1",
      clientRequestId: "opaque-request-1",
    }));
    const pendingStatus: NarrativeRequestStatusResponse = {
      session_id: "session-public-1",
      client_request_id: "opaque-request-1",
      status: "PENDING",
      client_action: "POLL_SAME_REQUEST",
      error_code: null,
      retry_after_seconds: 2,
      response: null,
    };
    const client = {
      listScenarios: async () => scenarioCatalogFixture,
      listEligiblePlayerCharacters: async () => eligiblePlayerCharactersFixture,
      getSessionView: async () => {
        viewReads += 1;
        return freeActionViewFixture(viewReads);
      },
      submitAction: async () => {
        actionPosts += 1;
        return {
          status: 202,
          response: pendingActionResponseFixture("opaque-request-1"),
        } as const;
      },
      getNarrativeRequestStatus: async () => {
        statusReads += 1;
        return pendingStatus;
      },
    } as unknown as PublicApiClient;
    const pollWait = (_milliseconds: number, signal: AbortSignal) => {
      operationSignal = signal;
      waitStarted.resolve();
      return waitGate.promise;
    };
    const user = userEvent.setup();
    renderActionApp({ client, pollWait, actionIdentityFactory });
    await loadSession(user);

    await user.click(screen.getByRole("button", { name: "提交继续" }));
    await waitStarted.promise;
    await user.click(
      screen.getByRole("button", { name: "清除本标签页 Session" }),
    );

    expect(operationSignal?.aborted).toBe(true);
    expect(storedRecoveryRecord()).toBeNull();
    waitGate.resolve();
    await act(async () => Promise.resolve());
    expect(actionPosts).toBe(1);
    expect(statusReads).toBe(1);
    expect(viewReads).toBe(1);
    expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();
  });

  it("explicitly clears a post-action /view refresh and rejects its late View", async () => {
    const refreshGate = deferred<PlayerSessionView>();
    const refreshStarted = deferred<void>();
    let refreshSignal: AbortSignal | undefined;
    let actionPosts = 0;
    let viewReads = 0;
    const actionIdentityFactory = vi.fn(() => ({
      turnId: "opaque-turn-1",
      clientRequestId: "opaque-request-1",
    }));
    const client = {
      listScenarios: async () => scenarioCatalogFixture,
      listEligiblePlayerCharacters: async () => eligiblePlayerCharactersFixture,
      getSessionView: async (_sessionId: string, signal?: AbortSignal) => {
        viewReads += 1;
        if (viewReads === 1) {
          return freeActionViewFixture(1);
        }
        refreshSignal = signal;
        refreshStarted.resolve();
        return refreshGate.promise;
      },
      submitAction: async () => {
        actionPosts += 1;
        return {
          status: 200,
          response: synchronousActionResponseFixture("opaque-request-1", 2),
        } as const;
      },
    } as unknown as PublicApiClient;
    const user = userEvent.setup();
    renderActionApp({ client, actionIdentityFactory });
    await loadSession(user);

    await user.click(screen.getByRole("button", { name: "提交继续" }));
    await refreshStarted.promise;
    await user.click(
      screen.getByRole("button", { name: "清除本标签页 Session" }),
    );

    expect(refreshSignal?.aborted).toBe(true);
    expect(storedRecoveryRecord()).toBeNull();
    refreshGate.resolve(freeActionViewFixture(99));
    await act(async () => Promise.resolve());
    expect(actionPosts).toBe(1);
    expect(viewReads).toBe(2);
    expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("权威 View 已推进到版本 99。")).not.toBeInTheDocument();
    expect(screen.queryByText("当前 Session：session-public-1")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();
  });

  it("allows only one action POST and blocks create/manual read during submission", async () => {
    const gate = deferred<void>();
    let actionPosts = 0;
    let createPosts = 0;
    let viewReads = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(freeActionViewFixture(viewReads));
        },
      ),
      http.post(`${apiOrigin}/v1/sessions`, () => {
        createPosts += 1;
        return HttpResponse.json({}, { status: 500 });
      }),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async () => {
          actionPosts += 1;
          await gate.promise;
          return HttpResponse.json(
            synchronousActionResponseFixture("opaque-request-1", 2),
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
    await loadSession(user);
    const continueForm = actionForm("提交继续");
    const manualForm = screen
      .getByRole("button", { name: "读取 PlayerSessionView" })
      .closest("form");
    const createForm = screen
      .getByRole("button", { name: "进入 Run" })
      .closest("form");
    expect(manualForm).not.toBeNull();
    expect(createForm).not.toBeNull();

    fireEvent.submit(continueForm);
    fireEvent.submit(continueForm);
    fireEvent.submit(manualForm!);
    fireEvent.submit(createForm!);

    await waitFor(() => expect(actionPosts).toBe(1));
    expect(screen.getByText("行动已禁用：前台操作正在进行")).toBeVisible();
    expect(screen.getByRole("button", { name: "提交继续" })).toBeDisabled();
    expect(createPosts).toBe(0);
    expect(viewReads).toBe(1);

    gate.resolve();
    await waitFor(() => expect(viewReads).toBe(2));
    expect(actionPosts).toBe(1);
    expect(createPosts).toBe(0);
  });

  it.each(["resolve", "reject"] as const)(
    "ignores a stale %s and its finally cannot release a newer operation",
    async (settlement) => {
      const oldRead = deferred<PlayerSessionView>();
      const newRead = deferred<PlayerSessionView>();
      const oldClient = {
        listScenarios: async () => scenarioCatalogFixture,
        listEligiblePlayerCharacters: async () => eligiblePlayerCharactersFixture,
        getSessionView: async () => oldRead.promise,
      } as unknown as PublicApiClient;
      const newClient = {
        listScenarios: async () => scenarioCatalogFixture,
        listEligiblePlayerCharacters: async () => eligiblePlayerCharactersFixture,
        getSessionView: async () => newRead.promise,
      } as unknown as PublicApiClient;
      const user = userEvent.setup();
      const rendered = renderActionApp({ client: oldClient });
      await user.type(await screen.findByLabelText("Session ID"), "old-session");
      await user.click(
        screen.getByRole("button", { name: "读取 PlayerSessionView" }),
      );
      expect(
        await screen.findByText("正在读取完整权威 View。"),
      ).toBeVisible();

      rendered.rerender(
        <App
          client={newClient}
          idempotencyKeyFactory={() => "opaque-mutation-request"}
          actionIdentityFactory={deterministicActionIdentityFactory()}
        />,
      );
      await waitFor(() =>
        expect(
          screen.getByText(
            "空闲：可以选择 Player Character 与副本进入 Run，或手动读取已有 Session。",
          ),
        ).toBeVisible(),
      );
      const input = screen.getByLabelText("Session ID");
      await user.clear(input);
      await user.type(input, "new-session");
      await user.click(
        screen.getByRole("button", { name: "读取 PlayerSessionView" }),
      );
      expect(
        await screen.findByText("正在读取完整权威 View。"),
      ).toBeVisible();

      if (settlement === "resolve") {
        oldRead.resolve(withSessionId(freeActionViewFixture(), "old-session"));
      } else {
        oldRead.reject(new Error("stale read failed"));
      }
      await act(async () => Promise.resolve());

      expect(screen.getByText("正在读取完整权威 View。")).toBeVisible();
      expect(
        screen.getByRole("button", { name: "正在读取…" }),
      ).toBeDisabled();
      expect(screen.queryByText("当前 Session：old-session")).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();

      newRead.resolve(withSessionId(freeActionViewFixture(2), "new-session"));
      expect(
        await screen.findByText("当前 Session：new-session"),
      ).toBeVisible();
      expect(
        screen.queryByText("当前 Session：old-session"),
      ).not.toBeInTheDocument();
      expect(storedRecoveryRecord()).toEqual({
        version: 1,
        session_id: "new-session",
      });
    },
  );

  it("aborts polling on unmount and never checks or posts again", async () => {
    let actionPosts = 0;
    let statusReads = 0;
    let waitSignal: AbortSignal | undefined;
    let markWaitEntered: (() => void) | undefined;
    const waitEntered = new Promise<void>((resolve) => {
      markWaitEntered = resolve;
    });
    const pollWait = (_milliseconds: number, signal: AbortSignal) => {
      waitSignal = signal;
      markWaitEntered?.();
      return new Promise<void>((_resolve, reject) => {
        signal.addEventListener(
          "abort",
          () => reject(new DOMException("aborted", "AbortError")),
          { once: true },
        );
      });
    };
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(freeActionViewFixture()),
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () => {
          actionPosts += 1;
          return HttpResponse.json(
            pendingActionResponseFixture("opaque-request-1"),
            { status: 202 },
          );
        },
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/opaque-request-1`,
        () => {
          statusReads += 1;
          return HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: "opaque-request-1",
            status: "PENDING",
            client_action: "POLL_SAME_REQUEST",
            error_code: null,
            retry_after_seconds: 2,
            response: null,
          });
        },
      ),
    );
    const user = userEvent.setup();
    const rendered = renderActionApp({ pollWait });
    await loadSession(user);
    await user.click(screen.getByRole("button", { name: "提交继续" }));
    await waitEntered;

    rendered.unmount();

    expect(waitSignal?.aborted).toBe(true);
    await act(async () => Promise.resolve());
    expect(actionPosts).toBe(1);
    expect(statusReads).toBe(1);
  });
});

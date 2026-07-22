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
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { PublicApiClient } from "./api/client";
import type { PlayerSessionView } from "./api/schemas";
import {
  activeViewFixture,
  committedActionResponseFixture,
  endedViewFixture,
  errorFixture,
  freeActionViewFixture,
  pendingActionResponseFixture,
  scenarioCatalogFixture,
  synchronousActionResponseFixture,
} from "./test/fixtures";
import { server } from "./test/server";

const apiOrigin = "http://action-ui.test";
const testClient = new PublicApiClient({ baseUrl: `${apiOrigin}/` });

function scenarioHandler() {
  return http.get(`${apiOrigin}/v1/scenarios`, () =>
    HttpResponse.json(scenarioCatalogFixture),
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
  } = {},
) {
  return render(
    <App
      client={options.client ?? testClient}
      requestIdFactory={() => "opaque-create-request"}
      actionIdentityFactory={
        options.actionIdentityFactory ?? deterministicActionIdentityFactory()
      }
      {...(options.pollWait === undefined
        ? {}
        : { pollWait: options.pollWait })}
    />,
  );
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

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((promiseResolve, promiseReject) => {
    resolve = promiseResolve;
    reject = promiseReject;
  });
  return { promise, resolve, reject };
}

describe("action_affordances and synchronous lifecycle", () => {
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

describe("HTTP 202 request-status lifecycle", () => {
  it("polls one 202 request through PENDING to COMMITTED and then reads a full View", async () => {
    let actionPosts = 0;
    let statusReads = 0;
    let viewReads = 0;
    const observedStatusIds: string[] = [];
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
        `${apiOrigin}/v1/sessions/session-public-1/requests/:requestId`,
        ({ params }) => {
          statusReads += 1;
          observedStatusIds.push(String(params.requestId));
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
            response: committedActionResponseFixture("opaque-request-1", 2),
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
    },
  );

  it("marks the View stale when a 202 request-status read fails and never re-POSTs", async () => {
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
          return HttpResponse.error();
        },
      ),
    );
    const user = userEvent.setup();
    renderActionApp();
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
  });
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
      .getByRole("button", { name: "创建 Session" })
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
        getSessionView: async () => oldRead.promise,
      } as unknown as PublicApiClient;
      const newClient = {
        listScenarios: async () => scenarioCatalogFixture,
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
          requestIdFactory={() => "opaque-create-request"}
          actionIdentityFactory={deterministicActionIdentityFactory()}
        />,
      );
      await waitFor(() =>
        expect(
          screen.getByText("空闲：可以创建 Session 或手动读取已有 Session。"),
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

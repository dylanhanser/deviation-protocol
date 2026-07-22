import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, delay, http } from "msw";
import { describe, expect, it } from "vitest";

import App from "./App";
import { PublicApiClient } from "./api/client";
import { readSessionRecoveryRecord } from "./sessionRecovery";
import {
  activeViewFixture,
  endedViewFixture,
  errorFixture,
  scenarioCatalogFixture,
  sessionCreationFixture,
} from "./test/fixtures";
import { server } from "./test/server";

const apiOrigin = "http://ui-api.test";
const testClient = new PublicApiClient({ baseUrl: `${apiOrigin}/` });

function scenarioHandler() {
  return http.get(`${apiOrigin}/v1/scenarios`, () =>
    HttpResponse.json(scenarioCatalogFixture),
  );
}

function renderApp() {
  return render(
    <App
      client={testClient}
      requestIdFactory={() => "web-create-ui-test"}
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

describe("scenario discovery states", () => {
  it("renders loading and then the successful public catalog", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, async () => {
        await delay(25);
        return HttpResponse.json(scenarioCatalogFixture);
      }),
    );

    renderApp();
    expect(screen.getByText("正在加载公开副本…")).toHaveAttribute(
      "role",
      "status",
    );
    expect(await screen.findByLabelText("副本")).toHaveValue(
      "scenario.public-alpha",
    );
    expect(screen.getByText(scenarioCatalogFixture.scenarios[0]!.hook)).toBeVisible();
    expect(screen.getByLabelText("角色")).toHaveValue(
      "character.public.observer",
    );
  });

  it("renders an empty catalog state without a create control", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json({ scenarios: [] }),
      ),
    );

    renderApp();
    expect(
      await screen.findByText("当前没有可公开游玩的副本。"),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "创建 Session" }),
    ).not.toBeInTheDocument();
  });

  it("renders a public ErrorResponse for catalog failure", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json(errorFixture("INTERNAL_SERVER_ERROR", "Internal server error"), {
          status: 500,
        }),
      ),
    );

    renderApp();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 500 · INTERNAL_SERVER_ERROR · Internal server error",
    );
  });
});

describe("session creation", () => {
  it("creates once, reads the complete view and renders its public summary", async () => {
    let creationBody: unknown;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/sessions`, async ({ request }) => {
        creationBody = await request.json();
        return HttpResponse.json(sessionCreationFixture, { status: 201 });
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
    );
    const user = userEvent.setup();
    renderApp();

    await user.click(
      await screen.findByRole("button", { name: "创建 Session" }),
    );

    expect(
      await screen.findByText("当前 Session：session-public-1"),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "雾港回声", level: 2 })).toBeVisible();
    expect(screen.getByText(/停止条件：/)).toHaveTextContent("AWAIT_PLAYER");
    expect(
      screen.getByRole("button", { name: "检查灯塔信号" }),
    ).toBeVisible();
    expect(screen.getByText("公开玩家状态")).toBeVisible();
    expect(screen.getByText("clock.public.tide：2 / 8")).toBeVisible();
    expect(creationBody).toEqual({
      client_request_id: "web-create-ui-test",
      character_definition_id: "character.public.observer",
      scenario_id: "scenario.public-alpha",
    });
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });
  });

  it("prevents duplicate creation while the first request is in flight", async () => {
    let releaseRequest: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      releaseRequest = resolve;
    });
    let createCount = 0;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/sessions`, async () => {
        createCount += 1;
        await gate;
        return HttpResponse.json(sessionCreationFixture, { status: 201 });
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
    );
    renderApp();
    const button = await screen.findByRole("button", { name: "创建 Session" });
    const form = button.closest("form");
    expect(form).not.toBeNull();

    fireEvent.submit(form!);
    fireEvent.submit(form!);
    await waitFor(() => expect(createCount).toBe(1));
    expect(screen.getByRole("button", { name: "正在创建…" })).toBeDisabled();
    releaseRequest?.();

    expect(
      await screen.findByText("当前 Session：session-public-1"),
    ).toBeVisible();
    expect(createCount).toBe(1);
  });

  it("does not create again when React rerenders the page", async () => {
    let createCount = 0;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/sessions`, () => {
        createCount += 1;
        return HttpResponse.json(sessionCreationFixture, { status: 201 });
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
    );
    const user = userEvent.setup();
    const rendered = renderApp();
    await user.click(
      await screen.findByRole("button", { name: "创建 Session" }),
    );
    await screen.findByText("当前 Session：session-public-1");

    rendered.rerender(
      <App
        client={testClient}
        requestIdFactory={() => "web-create-ui-test"}
      />,
    );
    await waitFor(() => expect(createCount).toBe(1));
  });

  it("shows a create conflict without treating it as success", async () => {
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/sessions`, () =>
        HttpResponse.json(errorFixture("IDEMPOTENCY_CONFLICT", "Idempotency key was reused"), {
          status: 409,
        }),
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.click(
      await screen.findByRole("button", { name: "创建 Session" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 409 · IDEMPOTENCY_CONFLICT",
    );
    expect(screen.queryByText(/当前 Session：/)).not.toBeInTheDocument();
  });

  it("does not combine a created session whose view failed with an older loaded view", async () => {
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/sessions`, () =>
        HttpResponse.json(
          { ...sessionCreationFixture, session_id: "session-public-2" },
          { status: 201 },
        ),
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
      http.get(`${apiOrigin}/v1/sessions/session-public-2/view`, () =>
        HttpResponse.json(
          errorFixture("SESSION_NOT_FOUND", "Created session view was not found"),
          { status: 404 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(
      await screen.findByLabelText("Session ID"),
      "session-public-1",
    );
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );
    await screen.findByText("当前 Session：session-public-1");

    await user.click(screen.getByRole("button", { name: "创建 Session" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 404 · SESSION_NOT_FOUND · Created session view was not found",
    );
    expect(
      screen.getByText(
        "已创建 Session：session-public-2，但 PlayerSessionView 未加载。",
      ),
    ).toBeVisible();
    expect(screen.queryByText(/当前 Session：/)).not.toBeInTheDocument();
    expect(screen.queryByText("PlayerSessionView")).not.toBeInTheDocument();
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-2",
    });
  });

  it("coordinates rapid create and manual submissions as one foreground operation", async () => {
    let releaseCreate: (() => void) | undefined;
    const createGate = new Promise<void>((resolve) => {
      releaseCreate = resolve;
    });
    let createCount = 0;
    let createdViewCount = 0;
    let manualReadCount = 0;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/sessions`, async () => {
        createCount += 1;
        await createGate;
        return HttpResponse.json(sessionCreationFixture, { status: 201 });
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          createdViewCount += 1;
          return HttpResponse.json(activeViewFixture);
        },
      ),
      http.get(`${apiOrigin}/v1/sessions/manual-session/view`, () => {
        manualReadCount += 1;
        return HttpResponse.json(activeViewFixture);
      }),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(
      await screen.findByLabelText("Session ID"),
      "manual-session",
    );
    const createButton = screen.getByRole("button", { name: "创建 Session" });
    const readButton = screen.getByRole("button", {
      name: "读取 PlayerSessionView",
    });
    const createForm = createButton.closest("form");
    const readForm = readButton.closest("form");
    expect(createForm).not.toBeNull();
    expect(readForm).not.toBeNull();

    fireEvent.submit(createForm!);
    fireEvent.submit(readForm!);
    await waitFor(() => expect(createCount).toBe(1));
    expect(screen.getByRole("button", { name: "正在创建…" })).toBeDisabled();
    expect(readButton).toBeDisabled();
    releaseCreate?.();

    expect(
      await screen.findByText("当前 Session：session-public-1"),
    ).toBeVisible();
    expect(createCount).toBe(1);
    expect(createdViewCount).toBe(1);
    expect(manualReadCount).toBe(0);
  });
});

describe("manual PlayerSessionView reads", () => {
  it("reads an active session only after explicit user submission", async () => {
    let readCount = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          readCount += 1;
          return HttpResponse.json(activeViewFixture);
        },
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await screen.findByLabelText("副本");
    expect(readCount).toBe(0);

    await user.type(screen.getByLabelText("Session ID"), "session-public-1");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(await screen.findByText("长期记忆")).toBeVisible();
    expect(screen.getByText("当前公开正文")).toBeVisible();
    expect(readCount).toBe(1);
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });
  });

  it("renders an ended session with ending_status and ending presentation", async () => {
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(endedViewFixture("FAILED")),
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(
      await screen.findByLabelText("Session ID"),
      "session-public-1",
    );
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(await screen.findByText("FAILED")).toBeVisible();
    expect(screen.getByRole("heading", { name: "信号沉没" })).toBeVisible();
    expect(screen.getByText("Ending ID：ending.public.failed")).toBeVisible();
    expect(screen.getByText(/停止条件：/)).toHaveTextContent("SCENARIO_ENDED");
  });

  it("renders a 404 ErrorResponse for a missing manual session", async () => {
    server.use(
      scenarioHandler(),
      http.get(`${apiOrigin}/v1/sessions/missing/view`, () =>
        HttpResponse.json(errorFixture("SESSION_NOT_FOUND", "Session was not found"), {
          status: 404,
        }),
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(await screen.findByLabelText("Session ID"), "missing");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 404 · SESSION_NOT_FOUND · Session was not found",
    );
  });

  it("clears an older loaded view when a different manual session returns 404", async () => {
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
      http.get(`${apiOrigin}/v1/sessions/missing/view`, () =>
        HttpResponse.json(
          errorFixture("SESSION_NOT_FOUND", "Requested session was not found"),
          { status: 404 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApp();
    const input = await screen.findByLabelText("Session ID");
    await user.type(input, "session-public-1");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );
    await screen.findByText("当前 Session：session-public-1");
    expect(screen.getByText("PlayerSessionView")).toBeVisible();

    await user.clear(input);
    await user.type(input, "missing");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 404 · SESSION_NOT_FOUND · Requested session was not found",
    );
    expect(screen.queryByText(/当前 Session：/)).not.toBeInTheDocument();
    expect(screen.queryByText("PlayerSessionView")).not.toBeInTheDocument();
    expect(screen.queryByText("session-public-1")).not.toBeInTheDocument();
  });

  it("reads a pasted session ID with surrounding whitespace after trimming it", async () => {
    let readCount = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          readCount += 1;
          return HttpResponse.json(activeViewFixture);
        },
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(
      await screen.findByLabelText("Session ID"),
      "  session-public-1  ",
    );
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(
      await screen.findByText("当前 Session：session-public-1"),
    ).toBeVisible();
    expect(readCount).toBe(1);
  });

  it("reports an invalid manual Session ID accessibly without making a request", async () => {
    let readCount = 0;
    server.use(
      scenarioHandler(),
      http.get(`${apiOrigin}/v1/sessions/:sessionId/view`, () => {
        readCount += 1;
        return HttpResponse.json(activeViewFixture);
      }),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(await screen.findByLabelText("Session ID"), "invalid id");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Session ID 格式无效，请检查后重试。",
    );
    expect(readCount).toBe(0);
  });

  it("aborts an in-flight foreground session operation when unmounted", async () => {
    let requestStarted = false;
    let requestAborted = false;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        async ({ request }) => {
          requestStarted = true;
          request.signal.addEventListener("abort", () => {
            requestAborted = true;
          });
          await delay("infinite");
          return HttpResponse.json(activeViewFixture);
        },
      ),
    );
    const user = userEvent.setup();
    const rendered = renderApp();
    await user.type(
      await screen.findByLabelText("Session ID"),
      "session-public-1",
    );
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );
    await waitFor(() => expect(requestStarted).toBe(true));

    rendered.unmount();

    await waitFor(() => expect(requestAborted).toBe(true));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

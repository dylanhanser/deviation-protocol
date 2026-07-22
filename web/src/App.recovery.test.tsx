import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { StrictMode } from "react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { PublicApiClient } from "./api/client";
import type { PlayerSessionView } from "./api/schemas";
import {
  SESSION_RECOVERY_STORAGE_KEY,
  readSessionRecoveryRecord,
  writeSessionRecoveryRecord,
} from "./sessionRecovery";
import {
  activeViewFixture,
  committedActionResponseFixture,
  endedViewFixture,
  errorFixture,
  freeActionViewFixture,
  scenarioCatalogFixture,
} from "./test/fixtures";
import { server } from "./test/server";

const apiOrigin = "http://recovery-ui.test";
const testClient = new PublicApiClient({ baseUrl: `${apiOrigin}/` });

function scenarioHandler() {
  return http.get(`${apiOrigin}/v1/scenarios`, () =>
    HttpResponse.json(scenarioCatalogFixture),
  );
}

function postGuards(onPost: () => void) {
  return [
    http.post(`${apiOrigin}/v1/sessions`, () => {
      onPost();
      return HttpResponse.json({}, { status: 500 });
    }),
    http.post(`${apiOrigin}/v1/sessions/:sessionId/actions`, () => {
      onPost();
      return HttpResponse.json({}, { status: 500 });
    }),
  ];
}

function deterministicActionIdentityFactory() {
  return {
    turnId: "recovery-turn-must-be-user-triggered",
    clientRequestId: "recovery-request-must-be-user-triggered",
  };
}

function renderRecoveryApp(
  options: {
    client?: PublicApiClient;
    pollWait?: (milliseconds: number, signal: AbortSignal) => Promise<void>;
    requestIdFactory?: () => string;
    actionIdentityFactory?: () => {
      turnId: string;
      clientRequestId: string;
    };
    strictMode?: boolean;
  } = {},
) {
  const app = (
    <App
      client={options.client ?? testClient}
      requestIdFactory={options.requestIdFactory ?? (() => "unused-create-id")}
      actionIdentityFactory={
        options.actionIdentityFactory ?? deterministicActionIdentityFactory
      }
      {...(options.pollWait === undefined
        ? {}
        : { pollWait: options.pollWait })}
    />
  );
  return render(options.strictMode === true ? <StrictMode>{app}</StrictMode> : app);
}

function seedRecoveryRecord(
  sessionId: string,
  confirmedPendingClientRequestId?: string,
) {
  const result = writeSessionRecoveryRecord(
    sessionId,
    confirmedPendingClientRequestId,
  );
  if (!result.ok) {
    throw new Error(`unexpected storage failure: ${result.failure.operation}`);
  }
}

function storedRecoveryRecord() {
  const result = readSessionRecoveryRecord();
  if (!result.ok) {
    throw new Error(`unexpected storage failure: ${result.failure.operation}`);
  }
  return result.value;
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
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
}

class FaultInjectingStorage implements Storage {
  private readonly values = new Map<string, string>();
  failGet = false;
  failSet = false;
  failRemove = false;

  get length() {
    return this.values.size;
  }

  clear() {
    this.values.clear();
  }

  getItem(key: string) {
    if (this.failGet) {
      throw new DOMException("get blocked", "SecurityError");
    }
    return this.values.get(key) ?? null;
  }

  key(index: number) {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string) {
    if (this.failRemove) {
      throw new Error("remove blocked");
    }
    this.values.delete(key);
  }

  setItem(key: string, value: string) {
    if (this.failSet) {
      throw new DOMException("set blocked", "QuotaExceededError");
    }
    this.values.set(key, value);
  }
}

function installSessionStorage(storage: Storage) {
  const descriptor = Object.getOwnPropertyDescriptor(
    globalThis,
    "sessionStorage",
  );
  Object.defineProperty(globalThis, "sessionStorage", {
    configurable: true,
    value: storage,
  });
  return () => {
    if (descriptor === undefined) {
      Reflect.deleteProperty(globalThis, "sessionStorage");
    } else {
      Object.defineProperty(globalThis, "sessionStorage", descriptor);
    }
  };
}

async function expectCurrentViewVersion(sessionId: string, stateVersion: number) {
  await screen.findByText(`当前 Session：${sessionId}`);
  expect(screen.getByText("状态版本").closest("div")).toHaveTextContent(
    `状态版本${stateVersion}`,
  );
}

describe("same-tab Session reload recovery", () => {
  it("restores once under the production-consistent StrictMode wrapper", async () => {
    seedRecoveryRecord("session-public-1");
    let viewReads = 0;
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () => {
        viewReads += 1;
        return HttpResponse.json(freeActionViewFixture(2));
      }),
    );

    renderRecoveryApp({ strictMode: true });

    await expectCurrentViewVersion("session-public-1", 2);
    expect(viewReads).toBe(1);
    expect(posts).toBe(0);
  });

  it("keeps affordances absent until an ACTIVE Session is restored through authoritative /view", async () => {
    seedRecoveryRecord("session-public-1");
    const viewGate = deferred<void>();
    let viewReads = 0;
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        async () => {
          viewReads += 1;
          await viewGate.promise;
          return HttpResponse.json(freeActionViewFixture(4));
        },
      ),
    );

    renderRecoveryApp();
    await waitFor(() => expect(viewReads).toBe(1));
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("PlayerSessionView")).not.toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "创建 Session" }),
    ).toBeDisabled();
    expect(posts).toBe(0);

    viewGate.resolve();
    expect(
      await screen.findByText("当前 Session：session-public-1"),
    ).toBeVisible();
    expect(screen.getByText("权威 View：当前")).toBeVisible();
    expect(screen.getByRole("button", { name: "提交继续" })).toBeEnabled();
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });
    expect(posts).toBe(0);
  });

  it("restores an ENDED Session only from /view and never creates action controls", async () => {
    seedRecoveryRecord("session-public-1");
    let viewReads = 0;
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          viewReads += 1;
          return HttpResponse.json(endedViewFixture("RESOLVED"));
        },
      ),
    );

    renderRecoveryApp();

    expect(await screen.findByText("RESOLVED")).toBeVisible();
    expect(screen.getByRole("heading", { name: "回声确认" })).toBeVisible();
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();
    expect(viewReads).toBe(1);
    expect(posts).toBe(0);
  });

  it("clears the current View and persistence only after explicit user clearing", async () => {
    seedRecoveryRecord("session-public-1");
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(freeActionViewFixture()),
      ),
    );
    const user = userEvent.setup();
    renderRecoveryApp();
    await screen.findByText("当前 Session：session-public-1");

    await user.click(
      screen.getByRole("button", { name: "清除本标签页 Session" }),
    );

    expect(storedRecoveryRecord()).toBeNull();
    expect(screen.queryByText("PlayerSessionView")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();
  });

  it("shows clear during confirmed-pending recovery and aborts a long status read without replay", async () => {
    seedRecoveryRecord("session-public-1", "confirmed-request-1");
    const statusGate = deferred<void>();
    const statusStarted = deferred<void>();
    let statusSignal: AbortSignal | undefined;
    let statusReads = 0;
    let viewReads = 0;
    let posts = 0;
    const requestIdFactory = vi.fn(() => "must-not-be-created");
    const actionIdentityFactory = vi.fn(deterministicActionIdentityFactory);
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/confirmed-request-1`,
        async ({ request }) => {
          statusReads += 1;
          statusSignal = request.signal;
          statusStarted.resolve();
          await statusGate.promise;
          return HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: "confirmed-request-1",
            status: "PENDING",
            client_action: "POLL_SAME_REQUEST",
            error_code: null,
            retry_after_seconds: 2,
            response: null,
          });
        },
      ),
      http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () => {
        viewReads += 1;
        return HttpResponse.json(freeActionViewFixture(99));
      }),
    );
    const user = userEvent.setup();
    renderRecoveryApp({ requestIdFactory, actionIdentityFactory });
    await statusStarted.promise;

    const clear = screen.getByRole("button", {
      name: "清除本标签页 Session",
    });
    expect(clear).toBeEnabled();
    expect(await screen.findByText(/confirmed-202 request/)).toBeVisible();
    await user.click(clear);

    await waitFor(() => expect(statusSignal?.aborted).toBe(true));
    expect(storedRecoveryRecord()).toBeNull();
    expect(screen.getByRole("button", { name: "创建 Session" })).toBeEnabled();
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();

    statusGate.resolve();
    await act(async () => Promise.resolve());
    expect(statusReads).toBe(1);
    expect(viewReads).toBe(0);
    expect(posts).toBe(0);
    expect(requestIdFactory).not.toHaveBeenCalled();
    expect(actionIdentityFactory).not.toHaveBeenCalled();
  });

  it("resumes one confirmed request through PENDING/COMMITTED with the same identities and then reads /view", async () => {
    seedRecoveryRecord(
      "session-public-1",
      "confirmed-request-1",
    );
    const events: string[] = [];
    const observedRequestIds: string[] = [];
    let statusReads = 0;
    let posts = 0;
    const pollWait = vi.fn(
      async (...parameters: [number, AbortSignal]) => {
        void parameters;
      },
    );
    const requestIdFactory = vi.fn(() => "must-not-be-created");
    const actionIdentityFactory = vi.fn(deterministicActionIdentityFactory);
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/:requestId`,
        ({ params }) => {
          statusReads += 1;
          events.push("status");
          observedRequestIds.push(String(params.requestId));
          if (statusReads === 1) {
            return HttpResponse.json({
              session_id: "session-public-1",
              client_request_id: "confirmed-request-1",
              status: "PENDING",
              client_action: "POLL_SAME_REQUEST",
              error_code: null,
              retry_after_seconds: 4,
              response: null,
            });
          }
          return HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: "confirmed-request-1",
            status: "COMMITTED",
            client_action: "RESPONSE_AVAILABLE",
            error_code: null,
            retry_after_seconds: null,
            response: committedActionResponseFixture("confirmed-request-1", 2),
          });
        },
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          events.push("view");
          return HttpResponse.json(freeActionViewFixture(5));
        },
      ),
    );

    renderRecoveryApp({
      pollWait,
      requestIdFactory,
      actionIdentityFactory,
    });

    await expectCurrentViewVersion("session-public-1", 5);
    expect(events).toEqual(["status", "status", "view"]);
    expect(observedRequestIds).toEqual([
      "confirmed-request-1",
      "confirmed-request-1",
    ]);
    expect(pollWait).toHaveBeenCalledTimes(1);
    expect(pollWait.mock.calls[0]?.[0]).toBe(4_000);
    expect(requestIdFactory).not.toHaveBeenCalled();
    expect(actionIdentityFactory).not.toHaveBeenCalled();
    expect(posts).toBe(0);
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });
  });

  it("follows STALE/REFRESH_VIEW without treating request status as a View", async () => {
    seedRecoveryRecord(
      "session-public-1",
      "confirmed-request-1",
    );
    const events: string[] = [];
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/confirmed-request-1`,
        () => {
          events.push("status");
          return HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: "confirmed-request-1",
            status: "STALE",
            client_action: "REFRESH_VIEW",
            error_code: "NARRATIVE_REQUEST_STALE",
            retry_after_seconds: null,
            response: null,
          });
        },
      ),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          events.push("view");
          return HttpResponse.json(freeActionViewFixture(6));
        },
      ),
    );

    renderRecoveryApp();

    await expectCurrentViewVersion("session-public-1", 6);
    expect(events).toEqual(["status", "view"]);
    expect(posts).toBe(0);
  });

  it.each([
    ["FAILED", "NARRATIVE_REQUEST_FAILED"],
    ["OUTCOME_UNKNOWN", "NARRATIVE_OUTCOME_UNKNOWN"],
  ] as const)(
    "uses a controlled authoritative View GET after %s/DO_NOT_RETRY and never POSTs",
    async (status, errorCode) => {
      seedRecoveryRecord(
        "session-public-1",
        "confirmed-request-1",
      );
      let statusReads = 0;
      let viewReads = 0;
      let posts = 0;
      server.use(
        scenarioHandler(),
        ...postGuards(() => {
          posts += 1;
        }),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/requests/confirmed-request-1`,
          () => {
            statusReads += 1;
            return HttpResponse.json({
              session_id: "session-public-1",
              client_request_id: "confirmed-request-1",
              status,
              client_action: "DO_NOT_RETRY",
              error_code: errorCode,
              retry_after_seconds: null,
              response: null,
            });
          },
        ),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () => {
            viewReads += 1;
            return HttpResponse.json(freeActionViewFixture(7));
          },
        ),
      );

      renderRecoveryApp();

      await expectCurrentViewVersion("session-public-1", 7);
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(1);
      expect(posts).toBe(0);
    },
  );

  it.each(["network", "malformed-response"] as const)(
    "stops automatic recovery after a %s failure and resumes only after a manual safe GET",
    async (failureKind) => {
      seedRecoveryRecord(
        "session-public-1",
        "confirmed-request-1",
      );
      let statusReads = 0;
      let viewReads = 0;
      let posts = 0;
      server.use(
        scenarioHandler(),
        ...postGuards(() => {
          posts += 1;
        }),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/requests/confirmed-request-1`,
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
              client_request_id: "confirmed-request-1",
              status: "COMMITTED",
              client_action: "RESPONSE_AVAILABLE",
              error_code: null,
              retry_after_seconds: null,
              response: committedActionResponseFixture(
                "confirmed-request-1",
                2,
              ),
            });
          },
        ),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () => {
            viewReads += 1;
            return HttpResponse.json(freeActionViewFixture(8));
          },
        ),
      );

      const user = userEvent.setup();
      renderRecoveryApp();

      expect(
        await screen.findByRole("heading", { name: "自动恢复已暂停" }),
      ).toBeVisible();
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(0);
      expect(posts).toBe(0);
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "创建 Session" })).toBeDisabled();
      expect(
        screen.getByRole("button", { name: "读取 PlayerSessionView" }),
      ).toBeDisabled();
      await act(async () => Promise.resolve());
      expect(statusReads).toBe(1);

      await user.click(
        screen.getByRole("button", { name: "手动重试安全 GET" }),
      );

      await expectCurrentViewVersion("session-public-1", 8);
      expect(statusReads).toBe(2);
      expect(viewReads).toBe(1);
      expect(posts).toBe(0);
    },
  );

  it.each(["view", "request-status"] as const)(
    "invalidates the persisted record after a recovery %s returns 404",
    async (missingEndpoint) => {
      seedRecoveryRecord(
        "session-public-1",
        ...(missingEndpoint === "request-status"
          ? (["confirmed-request-1"] as const)
          : []),
      );
      let posts = 0;
      server.use(
        scenarioHandler(),
        ...postGuards(() => {
          posts += 1;
        }),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () =>
            HttpResponse.json(
              errorFixture("SESSION_NOT_FOUND", "Session was not found"),
              { status: 404 },
            ),
        ),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/requests/confirmed-request-1`,
          () =>
            HttpResponse.json(
              errorFixture("REQUEST_NOT_FOUND", "Request was not found"),
              { status: 404 },
            ),
        ),
      );

      renderRecoveryApp();

      expect(
        await screen.findByText(/恢复记录在服务器返回 404 后失效/),
      ).toBeVisible();
      expect(
        globalThis.sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY),
      ).toBeNull();
      expect(screen.getByRole("button", { name: "创建 Session" })).toBeEnabled();
      expect(screen.getByLabelText("Session ID")).toBeEnabled();
      expect(
        screen.getByRole("button", { name: "读取 PlayerSessionView" }),
      ).toBeDisabled();
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();
      expect(posts).toBe(0);
    },
  );

  it.each([
    ["malformed JSON", "{"],
    ["unsupported version", JSON.stringify({ version: 99, session_id: "session-public-1" })],
    [
      "illegal field",
      JSON.stringify({
        version: 1,
        session_id: "session-public-1",
        action_payload: { action_type: "CONTINUE" },
      }),
    ],
  ])("does not create controls or requests from %s local data", async (_label, value) => {
    globalThis.sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY, value);
    let sessionGets = 0;
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(`${apiOrigin}/v1/sessions/:sessionId/view`, () => {
        sessionGets += 1;
        return HttpResponse.json(activeViewFixture);
      }),
    );

    renderRecoveryApp();
    expect(await screen.findByRole("button", { name: "创建 Session" })).toBeEnabled();

    expect(sessionGets).toBe(0);
    expect(posts).toBe(0);
    expect(
      globalThis.sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY),
    ).toBeNull();
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();
  });

  it("renders a non-actionable safety state when the sessionStorage getter throws", async () => {
    const descriptor = Object.getOwnPropertyDescriptor(
      globalThis,
      "sessionStorage",
    );
    Object.defineProperty(globalThis, "sessionStorage", {
      configurable: true,
      get() {
        throw new DOMException("storage denied", "SecurityError");
      },
    });
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
    );
    try {
      expect(() => renderRecoveryApp()).not.toThrow();
      expect(
        await screen.findByRole("heading", { name: "sessionStorage 安全锁定" }),
      ).toBeVisible();
      expect(screen.getByText(/失败边界：access/)).toBeVisible();
      expect(screen.getByRole("button", { name: "创建 Session" })).toBeDisabled();
      expect(
        screen.getByRole("button", { name: "读取 PlayerSessionView" }),
      ).toBeDisabled();
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();
      expect(posts).toBe(0);
    } finally {
      if (descriptor !== undefined) {
        Object.defineProperty(globalThis, "sessionStorage", descriptor);
      }
    }
  });

  it("renders the same non-actionable safety state when getItem throws", async () => {
    const storage = new FaultInjectingStorage();
    storage.failGet = true;
    const restoreStorage = installSessionStorage(storage);
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
    );
    try {
      expect(() => renderRecoveryApp()).not.toThrow();
      expect(
        await screen.findByRole("heading", { name: "sessionStorage 安全锁定" }),
      ).toBeVisible();
      expect(screen.getByText(/失败边界：get/)).toBeVisible();
      expect(screen.getByRole("button", { name: "创建 Session" })).toBeDisabled();
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();
      expect(posts).toBe(0);
    } finally {
      restoreStorage();
    }
  });

  it("locks and hides a fetched View when setItem fails", async () => {
    const storage = new FaultInjectingStorage();
    storage.failSet = true;
    const restoreStorage = installSessionStorage(storage);
    let viewReads = 0;
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () => {
        viewReads += 1;
        return HttpResponse.json(freeActionViewFixture());
      }),
    );
    try {
      const user = userEvent.setup();
      renderRecoveryApp();
      await user.type(await screen.findByLabelText("Session ID"), "session-public-1");
      await user.click(
        screen.getByRole("button", { name: "读取 PlayerSessionView" }),
      );

      expect(
        await screen.findByRole("heading", { name: "sessionStorage 安全锁定" }),
      ).toBeVisible();
      expect(screen.getByText(/失败边界：set/)).toBeVisible();
      expect(viewReads).toBe(1);
      expect(posts).toBe(0);
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();
      expect(screen.queryByText("当前 Session：session-public-1")).not.toBeInTheDocument();
    } finally {
      restoreStorage();
    }
  });

  it("does not unlock when explicit removeItem fails", async () => {
    const storage = new FaultInjectingStorage();
    storage.setItem(
      SESSION_RECOVERY_STORAGE_KEY,
      JSON.stringify({ version: 1, session_id: "session-public-1" }),
    );
    const restoreStorage = installSessionStorage(storage);
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () =>
        HttpResponse.json(freeActionViewFixture()),
      ),
    );
    try {
      const user = userEvent.setup();
      renderRecoveryApp();
      await screen.findByText("当前 Session：session-public-1");
      storage.failRemove = true;

      await user.click(
        screen.getByRole("button", { name: "清除本标签页 Session" }),
      );

      expect(
        await screen.findByRole("heading", { name: "sessionStorage 安全锁定" }),
      ).toBeVisible();
      expect(screen.getByText(/失败边界：remove/)).toBeVisible();
      expect(storage.getItem(SESSION_RECOVERY_STORAGE_KEY)).not.toBeNull();
      expect(screen.getByRole("button", { name: "创建 Session" })).toBeDisabled();
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();
      expect(screen.queryByText("当前 Session：session-public-1")).not.toBeInTheDocument();
      expect(posts).toBe(0);
    } finally {
      restoreStorage();
    }
  });

  it.each([
    ["Session", "other-session", "confirmed-request-1"],
    ["request", "session-public-1", "other-request"],
  ] as const)(
    "invalidates recovery when request-status returns a mismatched %s identity",
    async (_identity, responseSessionId, responseRequestId) => {
      seedRecoveryRecord(
        "session-public-1",
        "confirmed-request-1",
      );
      let statusReads = 0;
      let viewReads = 0;
      let posts = 0;
      server.use(
        scenarioHandler(),
        ...postGuards(() => {
          posts += 1;
        }),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/requests/confirmed-request-1`,
          () => {
            statusReads += 1;
            return (
            HttpResponse.json({
              session_id: responseSessionId,
              client_request_id: responseRequestId,
              status: "PENDING",
              client_action: "POLL_SAME_REQUEST",
              error_code: null,
              retry_after_seconds: 2,
              response: null,
            })
            );
          },
        ),
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/view`,
          () => {
            viewReads += 1;
            return HttpResponse.json(freeActionViewFixture());
          },
        ),
        http.get(`${apiOrigin}/v1/sessions/new-session/view`, () => {
          viewReads += 1;
          return HttpResponse.json(
            withSessionId(freeActionViewFixture(3), "new-session"),
          );
        }),
      );

      const rendered = renderRecoveryApp();

      expect(
        await screen.findByText(/恢复身份与已保存记录不匹配/),
      ).toBeVisible();
      expect(storedRecoveryRecord()).toBeNull();
      expect(
        screen.queryByRole("button", { name: "手动重试安全 GET" }),
      ).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "创建 Session" })).toBeEnabled();
      expect(viewReads).toBe(0);
      expect(posts).toBe(0);
      expect(statusReads).toBe(1);
      expect(
        screen.queryByRole("heading", { name: "当前可执行行动" }),
      ).not.toBeInTheDocument();

      rendered.unmount();
      renderRecoveryApp();
      await screen.findByRole("button", { name: "创建 Session" });
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(0);
      expect(posts).toBe(0);

      const user = userEvent.setup();
      await user.type(screen.getByLabelText("Session ID"), "new-session");
      await user.click(
        screen.getByRole("button", { name: "读取 PlayerSessionView" }),
      );
      await screen.findByText("当前 Session：new-session");
      expect(statusReads).toBe(1);
      expect(viewReads).toBe(1);
      expect(storedRecoveryRecord()).toEqual({
        version: 1,
        session_id: "new-session",
      });
    },
  );

  it("keeps identity-mismatch invalidation locked when storage removal fails", async () => {
    const storage = new FaultInjectingStorage();
    storage.setItem(
      SESSION_RECOVERY_STORAGE_KEY,
      JSON.stringify({
        version: 1,
        session_id: "session-public-1",
        client_request_id: "confirmed-request-1",
      }),
    );
    storage.failRemove = true;
    const restoreStorage = installSessionStorage(storage);
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/confirmed-request-1`,
        () =>
          HttpResponse.json({
            session_id: "other-session",
            client_request_id: "confirmed-request-1",
            status: "PENDING",
            client_action: "POLL_SAME_REQUEST",
            error_code: null,
            retry_after_seconds: 2,
            response: null,
          }),
      ),
    );
    try {
      renderRecoveryApp();

      expect(
        await screen.findByRole("heading", { name: "sessionStorage 安全锁定" }),
      ).toBeVisible();
      expect(screen.getByText(/失败边界：remove/)).toBeVisible();
      expect(storage.getItem(SESSION_RECOVERY_STORAGE_KEY)).not.toBeNull();
      expect(screen.getByRole("button", { name: "创建 Session" })).toBeDisabled();
      expect(
        screen.queryByRole("button", { name: "手动重试安全 GET" }),
      ).not.toBeInTheDocument();
      expect(posts).toBe(0);
    } finally {
      restoreStorage();
    }
  });

  it("atomically replaces recovery state when the user switches Sessions", async () => {
    seedRecoveryRecord("old-session");
    const newViewGate = deferred<void>();
    let newViewStarted = false;
    let posts = 0;
    server.use(
      scenarioHandler(),
      ...postGuards(() => {
        posts += 1;
      }),
      http.get(`${apiOrigin}/v1/sessions/old-session/view`, () =>
        HttpResponse.json(withSessionId(freeActionViewFixture(1), "old-session")),
      ),
      http.get(`${apiOrigin}/v1/sessions/new-session/view`, async () => {
        newViewStarted = true;
        await newViewGate.promise;
        return HttpResponse.json(
          withSessionId(freeActionViewFixture(2), "new-session"),
        );
      }),
    );
    const user = userEvent.setup();
    renderRecoveryApp();
    await screen.findByText("当前 Session：old-session");

    const input = screen.getByLabelText("Session ID");
    await user.clear(input);
    await user.type(input, "new-session");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );
    await waitFor(() => expect(newViewStarted).toBe(true));

    expect(storedRecoveryRecord()).toBeNull();
    expect(screen.queryByText("当前 Session：old-session")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "当前可执行行动" }),
    ).not.toBeInTheDocument();

    newViewGate.resolve();
    expect(await screen.findByText("当前 Session：new-session")).toBeVisible();
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "new-session",
    });
    expect(posts).toBe(0);
  });

  it("does not recover a transport-uncertain POST as pending after reload", async () => {
    seedRecoveryRecord("session-public-1");
    let viewReads = 0;
    let actionPosts = 0;
    let createPosts = 0;
    let statusReads = 0;
    const actionIdentityFactory = vi.fn(deterministicActionIdentityFactory);
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/sessions`, () => {
        createPosts += 1;
        return HttpResponse.json({}, { status: 500 });
      }),
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
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/:requestId`,
        () => {
          statusReads += 1;
          return HttpResponse.json({}, { status: 500 });
        },
      ),
    );
    const user = userEvent.setup();
    const rendered = renderRecoveryApp({ actionIdentityFactory });
    await screen.findByText("当前 Session：session-public-1");

    await user.click(screen.getByRole("button", { name: "提交继续" }));
    expect(await screen.findByText(/行动响应无法确认/)).toBeVisible();
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });

    rendered.unmount();
    renderRecoveryApp({ actionIdentityFactory });
    await waitFor(() => expect(viewReads).toBe(2));
    expect(screen.getByText("当前 Session：session-public-1")).toBeVisible();
    expect(actionPosts).toBe(1);
    expect(createPosts).toBe(0);
    expect(statusReads).toBe(0);
    expect(actionIdentityFactory).toHaveBeenCalledTimes(1);
  });

  it("lets an obsolete recovery response neither commit nor overwrite a newer Session", async () => {
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
    seedRecoveryRecord("session-public-1");
    const rendered = renderRecoveryApp({ client: oldClient });
    expect(
      await screen.findByText("正在重新读取完整权威 View。"),
    ).toBeVisible();

    rendered.rerender(
      <App
        client={newClient}
        requestIdFactory={() => "unused-create-id"}
        actionIdentityFactory={deterministicActionIdentityFactory}
      />,
    );
    await act(async () => Promise.resolve());
    oldRead.resolve(withSessionId(freeActionViewFixture(1), "session-public-1"));
    await act(async () => Promise.resolve());
    expect(screen.queryByText("权威 View 已推进到版本 1。"))
      .not.toBeInTheDocument();

    newRead.resolve(withSessionId(freeActionViewFixture(9), "session-public-1"));
    await expectCurrentViewVersion("session-public-1", 9);
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });
  });
});

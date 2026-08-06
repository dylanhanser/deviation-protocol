import { HttpResponse, delay, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PublicApiClient } from "./client";
import { configuredApiBaseUrl, normalizeApiBaseUrl } from "./config";
import {
  actionRequestSchema,
  actionResponseSchema,
  eligiblePlayerCharacterCollectionSchema,
  minimalPlayerCharacterCreationRequestSchema,
  narrativeRequestStatusResponseSchema,
  playerCharacterSelfProjectionSchema,
  playerSessionViewSchema,
  runEntryRequestSchema,
  runEntryResponseSchema,
} from "./schemas";
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
  runEntryRequestFixture,
  runEntryResponseFixture,
  scenarioCatalogFixture,
  sessionCreationFixture,
  synchronousActionResponseFixture,
} from "../test/fixtures";
import { server } from "../test/server";

const apiOrigin = "http://api.test";

function client(baseUrl = `${apiOrigin}/`) {
  return new PublicApiClient({ baseUrl });
}

function actionResponseWithFactIds(
  mustFactIds: string[],
  mayFactIds: string[],
  clientRequestId = "request-fact-uniqueness",
) {
  const response = synchronousActionResponseFixture(clientRequestId);
  if (response.narrative_frame === null) {
    throw new Error("action response fixture must contain one NarrativeFrame");
  }
  return {
    ...response,
    narrative_frame: {
      ...response.narrative_frame,
      must_render_facts: mustFactIds.map((factId, index) => ({
        fact_id: factId,
        value: { source: "must", index },
      })),
      may_render_facts: mayFactIds.map((factId, index) => ({
        fact_id: factId,
        value: { source: "may", index },
      })),
    },
  };
}

function localQueryActionResponse(
  feedbackParameters: Record<string, unknown>,
  localQueryResult: Record<string, unknown>,
  clientRequestId = "request-local-query-json",
) {
  return {
    ...synchronousActionResponseFixture(clientRequestId),
    result_code: "STATUS_INSPECTED",
    feedback_code: "STATUS_INSPECTED",
    feedback_parameters: feedbackParameters,
    state_changed: false,
    narrative_text: null,
    local_query_result: localQueryResult,
  };
}

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("API base URL configuration", () => {
  it("normalizes relative paths and trailing slashes", () => {
    expect(normalizeApiBaseUrl("/gateway", "http://app.test/root").href).toBe(
      "http://app.test/gateway/",
    );
    expect(normalizeApiBaseUrl("https://api.test/base///").href).toBe(
      "https://api.test/base/",
    );
  });

  it("falls back to /api/ for an empty VITE_API_BASE_URL", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");

    expect(configuredApiBaseUrl().href).toBe(
      new URL("/api/", globalThis.location.origin).href,
    );
  });

  it("falls back to /api/ for a whitespace-only VITE_API_BASE_URL", () => {
    vi.stubEnv("VITE_API_BASE_URL", "  \t  ");

    expect(configuredApiBaseUrl().href).toBe(
      new URL("/api/", globalThis.location.origin).href,
    );
  });

  it("rejects credentials and unsupported schemes", () => {
    expect(() => normalizeApiBaseUrl("https://user:secret@api.test")).toThrow();
    expect(() => normalizeApiBaseUrl("file:///tmp/api")).toThrow();
  });

  it("preserves a configured base path for requests", async () => {
    server.use(
      http.get("http://app.test/gateway/v1/scenarios", () =>
        HttpResponse.json(scenarioCatalogFixture),
      ),
    );
    const api = new PublicApiClient({
      baseUrl: "/gateway/",
      origin: "http://app.test",
    });

    await expect(api.listScenarios()).resolves.toEqual(scenarioCatalogFixture);
  });
});

describe("public API response contracts", () => {
  it("parses a successful public scenario listing", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json(scenarioCatalogFixture),
      ),
    );

    await expect(client().listScenarios()).resolves.toEqual(
      scenarioCatalogFixture,
    );
  });

  it("accepts an empty public scenario listing", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json({ scenarios: [] }),
      ),
    );

    await expect(client().listScenarios()).resolves.toEqual({ scenarios: [] });
  });

  it("maps a sealed ErrorResponse from scenario listing", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json(errorFixture("INTERNAL_SERVER_ERROR", "Internal server error"), {
          status: 500,
        }),
      ),
    );

    await expect(client().listScenarios()).rejects.toMatchObject({
      kind: "api",
      status: 500,
      errorCode: "INTERNAL_SERVER_ERROR",
      message: "Internal server error",
    });
  });

  it("rejects a scenario response with a missing required field", async () => {
    const invalidScenario = {
      ...scenarioCatalogFixture.scenarios[0],
      playable_characters: undefined,
    };
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json({ scenarios: [invalidScenario] }),
      ),
    );

    await expect(client().listScenarios()).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
      reason: "CONTRACT_MISMATCH",
    });
  });

  it("allows harmless added response fields without exposing them", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json({
          ...scenarioCatalogFixture,
          future_public_hint: "safe additive field",
          scenarios: scenarioCatalogFixture.scenarios.map((scenario) => ({
            ...scenario,
            future_scenario_hint: "safe nested additive field",
            playable_characters: scenario.playable_characters.map((role) => ({
              ...role,
              future_role_hint: "safe nested additive field",
            })),
          })),
        }),
      ),
    );

    const result = await client().listScenarios();
    expect(result).not.toHaveProperty("future_public_hint");
    expect(result.scenarios[0]).not.toHaveProperty("future_scenario_hint");
    expect(result.scenarios[0]?.playable_characters[0]).not.toHaveProperty(
      "future_role_hint",
    );
  });

  it("allows harmless added PlayerSessionView fields without exposing them", () => {
    const result = playerSessionViewSchema.parse({
      ...activeViewFixture,
      future_public_hint: "safe additive field",
      narrative_frame: {
        ...activeViewFixture.narrative_frame,
        future_frame_hint: "safe nested additive field",
      },
    });

    expect(result).not.toHaveProperty("future_public_hint");
    expect(result.narrative_frame).not.toHaveProperty("future_frame_hint");
  });

  it.each([
    ["affordance set", "set"],
    ["action item", "action"],
    ["target item", "target"],
    ["choice item", "choice"],
  ] as const)(
    "accepts and strips a harmless additive field on the %s through getSessionView",
    async (_label, layer) => {
      const sourceView =
        layer === "choice" ? activeViewFixture : freeActionViewFixture();
      let responseBody;
      if (layer === "set") {
        responseBody = {
          ...sourceView,
          action_affordances: {
            ...sourceView.action_affordances,
            future_affordance_hint: "safe additive field",
          },
        };
      } else if (layer === "action") {
        const freeView = freeActionViewFixture();
        responseBody = {
          ...freeView,
          action_affordances: {
            ...freeView.action_affordances,
            actions: freeView.action_affordances.actions.map((action) =>
              action.action_type === "TALK"
                ? { ...action, future_action_hint: "safe additive field" }
                : action,
            ),
          },
        };
      } else if (layer === "target") {
        const freeView = freeActionViewFixture();
        responseBody = {
          ...freeView,
          action_affordances: {
            ...freeView.action_affordances,
            actions: freeView.action_affordances.actions.map((action) =>
              action.action_type === "TALK"
                ? {
                    ...action,
                    targets: action.targets.map((target) => ({
                      ...target,
                      future_target_hint: "safe additive field",
                    })),
                  }
                : action,
            ),
          },
        };
      } else {
        responseBody = {
          ...activeViewFixture,
          action_affordances: {
            ...activeViewFixture.action_affordances,
            choices: activeViewFixture.action_affordances.choices.map(
              (choice) => ({
                ...choice,
                future_choice_hint: "safe additive field",
              }),
            ),
          },
        };
      }
      server.use(
        http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () =>
          HttpResponse.json(responseBody),
        ),
      );

      const view = await client().getSessionView("session-public-1");

      expect(view.action_affordances.mode).toBe(
        layer === "choice" ? "DECISION" : "FREE_ACTIONS",
      );
      const talk = view.action_affordances.actions.find(
        (action) => action.action_type === "TALK",
      );
      if (layer === "set") {
        expect(view.action_affordances).not.toHaveProperty(
          "future_affordance_hint",
        );
      } else if (layer === "action") {
        expect(talk?.action_type).toBe("TALK");
        expect(talk).not.toHaveProperty("future_action_hint");
      } else if (layer === "target") {
        expect(talk?.targets[0]?.target_id).toBe("npc.public.guide");
        expect(talk?.targets[0]).not.toHaveProperty("future_target_hint");
      } else {
        expect(view.action_affordances.choices[0]?.choice_id).toBe(
          "choice.public.inspect-light",
        );
        expect(view.action_affordances.choices[0]).not.toHaveProperty(
          "future_choice_hint",
        );
      }
    },
  );

  it.each([
    ["must_render_facts internally", ["fact.same", "fact.same"], []],
    ["may_render_facts internally", [], ["fact.same", "fact.same"]],
    ["must_render_facts and may_render_facts", ["fact.same"], ["fact.same"]],
  ] as const)("rejects repeated fact IDs across %s", (_label, mustIds, mayIds) => {
    expect(
      actionResponseSchema.safeParse(
        actionResponseWithFactIds([...mustIds], [...mayIds]),
      ).success,
    ).toBe(false);
  });

  it("accepts distinct fact IDs across must_render_facts and may_render_facts", () => {
    expect(
      actionResponseSchema.safeParse(
        actionResponseWithFactIds(
          ["fact.must.one", "fact.must.two"],
          ["fact.may.one", "fact.may.two"],
        ),
      ).success,
    ).toBe(true);
  });

  it("rejects repeated NarrativeFrame fact IDs through getSessionView", async () => {
    const view = freeActionViewFixture();
    server.use(
      http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () =>
        HttpResponse.json({
          ...view,
          narrative_frame: {
            ...view.narrative_frame,
            must_render_facts: [
              { fact_id: "fact.repeated", value: "must" },
            ],
            may_render_facts: [
              { fact_id: "fact.repeated", value: "may" },
            ],
          },
        }),
      ),
    );

    await expect(
      client().getSessionView("session-public-1"),
    ).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
      reason: "CONTRACT_MISMATCH",
      message: "Server response does not match the public contract",
    });
  });

  it("rejects a STARTED memory record that carries an ending_id", () => {
    const invalidMemory = {
      ...activeViewFixture.player_memory,
      scenarios: [
        {
          scenario_id: "scenario.public-alpha",
          scenario_content_version: "public-alpha-1.0.0",
          status: "STARTED",
          ending_id: "ending.public.impossible",
          milestone_refs: ["STARTED"],
          known_public_fact_refs: [],
        },
      ],
      total_scenario_records: 1,
    };
    const result = playerSessionViewSchema.safeParse({
      ...activeViewFixture,
      player_memory: invalidMemory,
      player_state: {
        ...activeViewFixture.player_state,
        player_memory: invalidMemory,
      },
    });

    expect(result.success).toBe(false);
  });

  it("rejects duplicate suggested action IDs in one NarrativeFrame", () => {
    const suggestedAction =
      activeViewFixture.narrative_frame.suggested_actions[0];
    if (suggestedAction === undefined) {
      throw new Error("active view fixture must contain one suggested action");
    }
    const result = playerSessionViewSchema.safeParse({
      ...activeViewFixture,
      narrative_frame: {
        ...activeViewFixture.narrative_frame,
        suggested_actions: [
          suggestedAction,
          { ...suggestedAction, label_hint: "重复的公开建议" },
        ],
      },
    });

    expect(result.success).toBe(false);
  });

  it("rejects an action affordance target that is not visible in the authoritative View", () => {
    const view = freeActionViewFixture();
    const result = playerSessionViewSchema.safeParse({
      ...view,
      action_affordances: {
        ...view.action_affordances,
        actions: view.action_affordances.actions.map((action) =>
          action.action_type === "TALK"
            ? {
                ...action,
                targets: [
                  {
                    target_id: "npc.hidden.not-public",
                    display_name: "隐藏目标",
                  },
                ],
              }
            : action,
        ),
      },
    });

    expect(result.success).toBe(false);
  });

  it.each([
    [
      "mode payload",
      () => {
        const view = freeActionViewFixture();
        return {
          ...view,
          action_affordances: {
            ...view.action_affordances,
            decision_id: "decision.not-allowed-in-free-mode",
          },
        };
      },
    ],
    [
      "action input contract",
      () => {
        const view = freeActionViewFixture();
        return {
          ...view,
          action_affordances: {
            ...view.action_affordances,
            actions: view.action_affordances.actions.map((action) =>
              action.action_type === "TALK"
                ? { ...action, input_kind: "DESCRIPTION" }
                : action,
            ),
          },
        };
      },
    ],
    [
      "duplicate target IDs",
      () => {
        const view = freeActionViewFixture();
        const talk = view.action_affordances.actions.find(
          (action) => action.action_type === "TALK",
        );
        const target = talk?.targets[0];
        if (target === undefined) {
          throw new Error("free action fixture must contain one TALK target");
        }
        return {
          ...view,
          action_affordances: {
            ...view.action_affordances,
            actions: view.action_affordances.actions.map((action) =>
              action.action_type === "TALK"
                ? { ...action, targets: [target, target] }
                : action,
            ),
          },
        };
      },
    ],
    [
      "duplicate choice IDs",
      () => {
        const choice = activeViewFixture.action_affordances.choices[0];
        if (choice === undefined) {
          throw new Error("decision fixture must contain one public choice");
        }
        return {
          ...activeViewFixture,
          action_affordances: {
            ...activeViewFixture.action_affordances,
            choices: [choice, choice],
          },
        };
      },
    ],
  ] as const)("continues to reject an invalid affordance %s", (_label, makeView) => {
    expect(playerSessionViewSchema.safeParse(makeView()).success).toBe(false);
  });

  it("validates the bounded Player Character and Run-entry schema matrix", () => {
    expect(
      minimalPlayerCharacterCreationRequestSchema.parse(
        minimalPlayerCharacterCreationFixture,
      ),
    ).toEqual(minimalPlayerCharacterCreationFixture);
    expect(
      playerCharacterSelfProjectionSchema.parse({
        ...playerCharacterFixture,
        harmless_future_field: "discarded",
      }),
    ).toEqual(playerCharacterFixture);
    expect(
      eligiblePlayerCharacterCollectionSchema.parse(
        eligiblePlayerCharactersFixture,
      ),
    ).toEqual(eligiblePlayerCharactersFixture);
    expect(runEntryRequestSchema.parse(runEntryRequestFixture)).toEqual(
      runEntryRequestFixture,
    );
    expect(runEntryResponseSchema.parse(runEntryResponseFixture)).toEqual(
      runEntryResponseFixture,
    );

    expect(
      minimalPlayerCharacterCreationRequestSchema.safeParse({
        ...minimalPlayerCharacterCreationFixture,
        lifecycle: "active",
      }).success,
    ).toBe(false);
    expect(
      runEntryRequestSchema.safeParse({
        ...runEntryRequestFixture,
        expected_record_revision: Number.MAX_SAFE_INTEGER + 1,
      }).success,
    ).toBe(false);
    expect(
      eligiblePlayerCharacterCollectionSchema.safeParse({
        eligible_player_characters: Array.from({ length: 33 }, (_, index) => ({
          ...playerCharacterFixture,
          player_character_id: { value: `pc.${String(index).padStart(2, "0")}` },
        })),
        truncated: true,
      }).success,
    ).toBe(false);
    expect(
      eligiblePlayerCharacterCollectionSchema.safeParse({
        eligible_player_characters: [
          { ...playerCharacterFixture, player_character_id: { value: "pc.b" } },
          { ...playerCharacterFixture, player_character_id: { value: "pc.a" } },
        ],
        truncated: false,
      }).success,
    ).toBe(false);
    expect(
      eligiblePlayerCharacterCollectionSchema.safeParse({
        eligible_player_characters: [
          { ...playerCharacterFixture, lifecycle: "retired" },
        ],
        truncated: false,
      }).success,
    ).toBe(false);
    expect(
      eligiblePlayerCharacterCollectionSchema.safeParse({
        eligible_player_characters: [playerCharacterFixture],
        truncated: true,
      }).success,
    ).toBe(false);
    expect(
      playerCharacterSelfProjectionSchema.safeParse({
        ...playerCharacterFixture,
        record_revision: { value: Number.MAX_SAFE_INTEGER + 1 },
      }).success,
    ).toBe(false);
  });

  it("rejects invalid mutation construction before fetch and exposes no raw value", async () => {
    const fetchImplementation = vi.fn();
    const api = new PublicApiClient({
      baseUrl: `${apiOrigin}/`,
      fetchImplementation,
    });
    expect(() =>
      api.createPlayerCharacter(
        minimalPlayerCharacterCreationFixture,
        "invalid key with spaces",
      ),
    ).toThrow();
    await expect(
      api.enterRun(
        { ...runEntryRequestFixture, expected_record_revision: 0 },
        "Entry.Invalid-1",
      ),
    ).rejects.toThrow();
    expect(fetchImplementation).not.toHaveBeenCalled();
  });

  it.each([
    ["revision", { ...playerCharacterFixture, record_revision: { value: 2 } }],
    ["lifecycle", { ...playerCharacterFixture, lifecycle: "retired" }],
  ] as const)("rejects an incompatible creation-success %s", async (_label, body) => {
    server.use(
      http.post(`${apiOrigin}/v1/player-characters`, () =>
        HttpResponse.json(body),
      ),
    );
    await expect(
      client().createPlayerCharacter(
        minimalPlayerCharacterCreationFixture,
        "Create.Incompatible-1",
      ),
    ).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
      reason: "CONTRACT_MISMATCH",
    });
  });

  it("sends each new operation once with its exact method, URL, headers and body", async () => {
    const requests: Array<{
      method: string;
      url: string;
      accept: string | null;
      contentType: string | null;
      key: string | null;
      body: unknown;
    }> = [];
    server.use(
      http.post(`${apiOrigin}/v1/player-characters`, async ({ request }) => {
        requests.push({
          method: request.method,
          url: request.url,
          accept: request.headers.get("accept"),
          contentType: request.headers.get("content-type"),
          key: request.headers.get("idempotency-key"),
          body: await request.json(),
        });
        return HttpResponse.json(playerCharacterFixture);
      }),
      http.get(
        `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
        ({ request }) => {
          requests.push({
            method: request.method,
            url: request.url,
            accept: request.headers.get("accept"),
            contentType: request.headers.get("content-type"),
            key: request.headers.get("idempotency-key"),
            body: null,
          });
          return HttpResponse.json(eligiblePlayerCharactersFixture);
        },
      ),
      http.post(`${apiOrigin}/v1/runs`, async ({ request }) => {
        requests.push({
          method: request.method,
          url: request.url,
          accept: request.headers.get("accept"),
          contentType: request.headers.get("content-type"),
          key: request.headers.get("idempotency-key"),
          body: await request.json(),
        });
        return HttpResponse.json(runEntryResponseFixture);
      }),
    );

    const api = client();
    await expect(
      api.createPlayerCharacter(
        minimalPlayerCharacterCreationFixture,
        "Create.Web-1",
      ),
    ).resolves.toEqual(playerCharacterFixture);
    await expect(api.listEligiblePlayerCharacters()).resolves.toEqual(
      eligiblePlayerCharactersFixture,
    );
    await expect(
      api.enterRun(runEntryRequestFixture, "Entry.Web-1"),
    ).resolves.toEqual(runEntryResponseFixture);

    expect(requests).toEqual([
      {
        method: "POST",
        url: `${apiOrigin}/v1/player-characters`,
        accept: "application/json",
        contentType: "application/json",
        key: "Create.Web-1",
        body: minimalPlayerCharacterCreationFixture,
      },
      {
        method: "GET",
        url: `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
        accept: "application/json",
        contentType: null,
        key: null,
        body: null,
      },
      {
        method: "POST",
        url: `${apiOrigin}/v1/runs`,
        accept: "application/json",
        contentType: "application/json",
        key: "Entry.Web-1",
        body: runEntryRequestFixture,
      },
    ]);
  });

  it.each([
    ["scenario", { ...runEntryResponseFixture, scenario_id: "scenario.other" }],
    [
      "character",
      {
        ...runEntryResponseFixture,
        player_character: {
          ...playerCharacterFixture,
          player_character_id: { value: "pc.other" },
        },
      },
    ],
    [
      "revision",
      {
        ...runEntryResponseFixture,
        player_character: {
          ...playerCharacterFixture,
          record_revision: { value: 2 },
        },
      },
    ],
  ] as const)("rejects a Run-entry %s identity mismatch", async (_label, body) => {
    server.use(
      http.post(`${apiOrigin}/v1/runs`, () => HttpResponse.json(body)),
    );
    await expect(
      client().enterRun(runEntryRequestFixture, "Entry.Identity-1"),
    ).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
      reason: "CONTRACT_MISMATCH",
    });
  });

  it.each([
    [
      "creation",
      () =>
        client().createPlayerCharacter(
          minimalPlayerCharacterCreationFixture,
          "Create.Malformed-1",
        ),
      `${apiOrigin}/v1/player-characters`,
    ],
    [
      "eligible collection",
      () => client().listEligiblePlayerCharacters(),
      `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
    ],
    [
      "Run entry",
      () => client().enterRun(runEntryRequestFixture, "Entry.Malformed-1"),
      `${apiOrigin}/v1/runs`,
    ],
  ] as const)("rejects a malformed successful %s response without retry", async (_label, call, url) => {
    let fetchCount = 0;
    server.use(
      http.all(url, () => {
        fetchCount += 1;
        return HttpResponse.json({ unexpected: "shape" });
      }),
    );
    await expect(call()).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
      reason: "CONTRACT_MISMATCH",
    });
    expect(fetchCount).toBe(1);
  });

  it.each([
    [404, "PLAYER_CHARACTER_NOT_FOUND"],
    [409, "IDEMPOTENCY_CONFLICT"],
    [422, "REQUEST_VALIDATION_FAILED"],
    [500, "INTERNAL_SERVER_ERROR"],
  ] as const)("maps sanitized Run-entry HTTP %i errors without retry", async (status, code) => {
    let fetchCount = 0;
    server.use(
      http.post(`${apiOrigin}/v1/runs`, () => {
        fetchCount += 1;
        return HttpResponse.json(errorFixture(code, `safe ${status}`), { status });
      }),
    );
    await expect(
      client().enterRun(runEntryRequestFixture, "Entry.Error-1"),
    ).rejects.toMatchObject({ kind: "api", status, errorCode: code });
    expect(fetchCount).toBe(1);
  });

  it("maps a Run-entry response-read failure as network uncertainty without retry", async () => {
    const response = HttpResponse.json(runEntryResponseFixture);
    const responseText = vi
      .spyOn(response, "text")
      .mockRejectedValue(new TypeError("response stream lost"));
    const fetchImplementation = vi.fn(async () => response);
    const api = new PublicApiClient({
      baseUrl: `${apiOrigin}/`,
      fetchImplementation,
    });

    await expect(
      api.enterRun(runEntryRequestFixture, "Entry.Response-Lost-1"),
    ).rejects.toMatchObject({ kind: "network" });
    expect(fetchImplementation).toHaveBeenCalledTimes(1);
    expect(responseText).toHaveBeenCalledTimes(1);
  });

  it("aborts one Run-entry fetch without retrying", async () => {
    const controller = new AbortController();
    const fetchImplementation = vi.fn(
      async (_input: RequestInfo | URL, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener(
            "abort",
            () => reject(new DOMException("aborted", "AbortError")),
            { once: true },
          );
        }),
    );
    const api = new PublicApiClient({
      baseUrl: `${apiOrigin}/`,
      fetchImplementation,
    });
    const pending = api.enterRun(
      runEntryRequestFixture,
      "Entry.Abort-1",
      controller.signal,
    );
    controller.abort();

    await expect(pending).rejects.toMatchObject({ kind: "aborted" });
    expect(fetchImplementation).toHaveBeenCalledTimes(1);
  });

  it("sends the exact session creation method, URL, headers and JSON body", async () => {
    let observedMethod = "";
    let observedUrl = "";
    let observedContentType = "";
    let observedBody: unknown;
    server.use(
      http.post(`${apiOrigin}/v1/sessions`, async ({ request }) => {
        observedMethod = request.method;
        observedUrl = request.url;
        observedContentType = request.headers.get("content-type") ?? "";
        observedBody = await request.json();
        return HttpResponse.json(sessionCreationFixture, { status: 201 });
      }),
    );
    const body = {
      client_request_id: "web-create-test-1",
      character_definition_id: "character.public.observer",
      scenario_id: "scenario.public-alpha",
    };

    await expect(client().createSession(body)).resolves.toEqual(
      sessionCreationFixture,
    );
    expect(observedMethod).toBe("POST");
    expect(observedUrl).toBe(`${apiOrigin}/v1/sessions`);
    expect(observedContentType).toBe("application/json");
    expect(observedBody).toEqual(body);
  });

  it("reads an active PlayerSessionView without ending fields", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () =>
        HttpResponse.json(activeViewFixture),
      ),
    );

    const view = await client().getSessionView("session-public-1");
    expect(view.scenario_status).toBe("ACTIVE");
    expect(view.ending_status).toBeNull();
    expect(view).not.toHaveProperty("ending_id");
  });

  it("reads an ended PlayerSessionView with ending and ending_status", async () => {
    const ended = endedViewFixture("FAILED");
    server.use(
      http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () =>
        HttpResponse.json(ended),
      ),
    );

    await expect(client().getSessionView("session-public-1")).resolves.toEqual(
      ended,
    );
  });

  it("URL-encodes the opaque session ID as one path segment", async () => {
    let observedPath = "";
    server.use(
      http.get(`${apiOrigin}/v1/sessions/:sessionId/view`, ({ request }) => {
        observedPath = new URL(request.url).pathname;
        return HttpResponse.json({
          ...activeViewFixture,
          metadata: {
            ...activeViewFixture.metadata,
            session_id: "session:public.one",
          },
          player_state: {
            ...activeViewFixture.player_state,
            session_id: "session:public.one",
          },
        });
      }),
    );

    await client().getSessionView("session:public.one");
    expect(observedPath).toBe("/v1/sessions/session%3Apublic.one/view");
  });

  it.each([
    [404, "SESSION_NOT_FOUND"],
    [409, "IDEMPOTENCY_CONFLICT"],
    [422, "REQUEST_VALIDATION_FAILED"],
    [503, "NARRATIVE_PROVIDER_NOT_CONFIGURED"],
    [500, "INTERNAL_SERVER_ERROR"],
  ])("preserves HTTP %i and public error code %s", async (status, errorCode) => {
    server.use(
      http.get(`${apiOrigin}/v1/sessions/missing/view`, () =>
        HttpResponse.json(errorFixture(errorCode, "Safe public message"), {
          status,
        }),
      ),
    );

    await expect(client().getSessionView("missing")).rejects.toMatchObject({
      kind: "api",
      status,
      errorCode,
      message: "Safe public message",
    });
  });

  it("rejects a non-JSON error response without exposing its body", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.text("upstream stack and private details", { status: 500 }),
      ),
    );

    await expect(client().listScenarios()).rejects.toMatchObject({
      kind: "invalid-response",
      status: 500,
      reason: "NON_JSON_RESPONSE",
      message: "Server response does not match the public contract",
    });
  });

  it("rejects malformed JSON from a successful response", async () => {
    server.use(
      http.get(
        `${apiOrigin}/v1/scenarios`,
        () =>
          new HttpResponse('{"scenarios":', {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    );

    await expect(client().listScenarios()).rejects.toMatchObject({
      kind: "invalid-response",
      reason: "MALFORMED_JSON",
    });
  });

  it("rejects an empty successful response", async () => {
    server.use(
      http.get(
        `${apiOrigin}/v1/scenarios`,
        () =>
          new HttpResponse(null, {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
      ),
    );

    await expect(client().listScenarios()).rejects.toMatchObject({
      kind: "invalid-response",
      reason: "EMPTY_RESPONSE",
    });
  });

  it("rejects a contract-incompatible successful PlayerSessionView", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () =>
        HttpResponse.json({
          ...activeViewFixture,
          ending_status: "RESOLVED",
        }),
      ),
    );

    await expect(
      client().getSessionView("session-public-1"),
    ).rejects.toMatchObject({
      kind: "invalid-response",
      reason: "CONTRACT_MISMATCH",
    });
  });

  it("supports AbortSignal cancellation without retrying", async () => {
    let requestCount = 0;
    let markEntered: (() => void) | undefined;
    const entered = new Promise<void>((resolve) => {
      markEntered = resolve;
    });
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, async () => {
        requestCount += 1;
        markEntered?.();
        await delay("infinite");
        return HttpResponse.json(scenarioCatalogFixture);
      }),
    );
    const controller = new AbortController();
    const request = client().listScenarios(controller.signal);
    await entered;
    controller.abort();

    await expect(request).rejects.toMatchObject({ kind: "aborted" });
    expect(requestCount).toBe(1);
  });

  it("maps AbortError while reading the response body to aborted", async () => {
    const controller = new AbortController();
    const response = HttpResponse.json(scenarioCatalogFixture);
    vi.spyOn(response, "text").mockImplementation(async () => {
      controller.abort();
      throw new DOMException("Body read was aborted", "AbortError");
    });
    let requestCount = 0;
    const fetchImplementation: typeof fetch = async () => {
      requestCount += 1;
      return response;
    };
    const api = new PublicApiClient({
      baseUrl: `${apiOrigin}/`,
      fetchImplementation,
    });

    await expect(api.listScenarios(controller.signal)).rejects.toMatchObject({
      kind: "aborted",
    });
    expect(requestCount).toBe(1);
  });
});

describe("public action and request-status contracts", () => {
  it("posts an exact payload-free CONTINUE and distinguishes HTTP 200", async () => {
    let observedMethod = "";
    let observedUrl = "";
    let observedAccept = "";
    let observedContentType = "";
    let observedBody: unknown;
    server.use(
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          observedMethod = request.method;
          observedUrl = request.url;
          observedAccept = request.headers.get("accept") ?? "";
          observedContentType = request.headers.get("content-type") ?? "";
          observedBody = await request.json();
          return HttpResponse.json(
            synchronousActionResponseFixture("opaque:request.one"),
          );
        },
      ),
    );
    const request = {
      turn_id: "opaque:turn.one",
      client_request_id: "opaque:request.one",
      action_type: "CONTINUE" as const,
    };

    const result = await client().submitAction("session-public-1", request);

    expect(result.status).toBe(200);
    expect(result.response.client_request_id).toBe("opaque:request.one");
    expect(observedMethod).toBe("POST");
    expect(observedUrl).toBe(
      `${apiOrigin}/v1/sessions/session-public-1/actions`,
    );
    expect(observedAccept).toBe("application/json");
    expect(observedContentType).toBe("application/json");
    expect(observedBody).toEqual(request);
  });

  it("distinguishes HTTP 202 without changing the action body", async () => {
    let observedBody: unknown;
    server.use(
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          observedBody = await request.json();
          return HttpResponse.json(
            pendingActionResponseFixture("request-pending-1"),
            { status: 202 },
          );
        },
      ),
    );
    const request = {
      turn_id: "turn-pending-1",
      client_request_id: "request-pending-1",
      action_type: "TALK" as const,
      dialogue: "请复核公开信号",
    };

    await expect(
      client().submitAction("session-public-1", request),
    ).resolves.toEqual({
      status: 202,
      response: pendingActionResponseFixture("request-pending-1"),
    });
    expect(observedBody).toEqual(request);
  });

  it.each([
    {
      label: "TALK/DIALOGUE with an optional visible target",
      request: {
        turn_id: "turn-talk",
        client_request_id: "request-talk",
        action_type: "TALK" as const,
        dialogue: "请说明当前公开情况",
        target_ids: ["npc.public.guide"],
      },
    },
    {
      label: "DESCRIPTION without a target",
      request: {
        turn_id: "turn-observe",
        client_request_id: "request-observe",
        action_type: "OBSERVE" as const,
        description: "观察公开信号",
      },
    },
    {
      label: "CHOOSE with only decision and choice",
      request: {
        turn_id: "turn-choice",
        client_request_id: "request-choice",
        action_type: "CHOOSE" as const,
        decision_id: "decision.public.bound-token",
        choice_id: "choice.public.inspect-light",
      },
    },
  ])("sends $label fields exactly", async ({ request }) => {
    let observedBody: unknown;
    server.use(
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request: httpRequest }) => {
          observedBody = await httpRequest.json();
          return HttpResponse.json(
            synchronousActionResponseFixture(request.client_request_id),
          );
        },
      ),
    );

    await client().submitAction("session-public-1", request);

    expect(observedBody).toEqual(request);
  });

  it("reads request status with the same opaque session and request IDs", async () => {
    let observedMethod = "";
    let observedPath = "";
    server.use(
      http.get(
        `${apiOrigin}/v1/sessions/:sessionId/requests/:requestId`,
        ({ request }) => {
          observedMethod = request.method;
          observedPath = new URL(request.url).pathname;
          return HttpResponse.json({
            session_id: "session:opaque.one",
            client_request_id: "request:opaque.one",
            status: "PENDING",
            client_action: "POLL_SAME_REQUEST",
            error_code: null,
            retry_after_seconds: 2,
            response: null,
          });
        },
      ),
    );

    const status = await client().getNarrativeRequestStatus(
      "session:opaque.one",
      "request:opaque.one",
    );

    expect(status.session_id).toBe("session:opaque.one");
    expect(status.client_request_id).toBe("request:opaque.one");
    expect(observedMethod).toBe("GET");
    expect(observedPath).toBe(
      "/v1/sessions/session%3Aopaque.one/requests/request%3Aopaque.one",
    );
  });

  it.each([
    ["Session ID", "other-session", "request-status", "SESSION_ID"],
    [
      "client_request_id",
      "session-public-1",
      "other-request",
      "CLIENT_REQUEST_ID",
    ],
  ] as const)(
    "classifies a request-status %s mismatch separately from schema damage",
    async (_label, responseSessionId, responseRequestId, identityMismatch) => {
      server.use(
        http.get(
          `${apiOrigin}/v1/sessions/session-public-1/requests/request-status`,
          () =>
            HttpResponse.json({
              session_id: responseSessionId,
              client_request_id: responseRequestId,
              status: "PENDING",
              client_action: "POLL_SAME_REQUEST",
              error_code: null,
              retry_after_seconds: 2,
              response: null,
            }),
        ),
      );

      await expect(
        client().getNarrativeRequestStatus(
          "session-public-1",
          "request-status",
        ),
      ).rejects.toMatchObject({
        kind: "identity-mismatch",
        status: 200,
        identityMismatch,
      });
    },
  );

  it("validates every real request-status/client_action shape", () => {
    const committedResponse = committedActionResponseFixture("request-status");
    const identities = {
      session_id: "session-public-1",
      client_request_id: "request-status",
    };
    const validStatuses = [
      {
        ...identities,
        status: "PENDING",
        client_action: "POLL_SAME_REQUEST",
        error_code: null,
        retry_after_seconds: 2,
        response: null,
      },
      {
        ...identities,
        status: "COMMITTED",
        client_action: "RESPONSE_AVAILABLE",
        error_code: null,
        retry_after_seconds: null,
        response: committedResponse,
      },
      {
        ...identities,
        status: "STALE",
        client_action: "REFRESH_VIEW",
        error_code: "NARRATIVE_REQUEST_STALE",
        retry_after_seconds: null,
        response: null,
      },
      {
        ...identities,
        status: "OUTCOME_UNKNOWN",
        client_action: "DO_NOT_RETRY",
        error_code: "NARRATIVE_OUTCOME_UNKNOWN",
        retry_after_seconds: null,
        response: null,
      },
      {
        ...identities,
        status: "FAILED",
        client_action: "DO_NOT_RETRY",
        error_code: "NARRATIVE_REQUEST_FAILED",
        retry_after_seconds: null,
        response: null,
      },
    ];

    for (const status of validStatuses) {
      expect(narrativeRequestStatusResponseSchema.safeParse(status).success).toBe(
        true,
      );
    }
  });

  it.each([
    {
      turn_id: "turn-invalid",
      client_request_id: "request-invalid",
      action_type: "CONTINUE",
      target_ids: [],
    },
    {
      turn_id: "turn-invalid",
      client_request_id: "request-invalid",
      action_type: "TALK",
      description: "wrong field",
    },
    {
      turn_id: "turn-invalid",
      client_request_id: "request-invalid",
      action_type: "OBSERVE",
      dialogue: "wrong field",
    },
    {
      turn_id: "turn-invalid",
      client_request_id: "request-invalid",
      action_type: "TALK",
      dialogue: "包含换行\n的对话",
    },
    {
      turn_id: "turn-invalid",
      client_request_id: "request-invalid",
      action_type: "CHOOSE",
      decision_id: "decision.public.bound-token",
      choice_id: "choice.public.inspect-light",
      target_ids: ["npc.public.guide"],
    },
  ])("rejects an illegal action DTO %#", (request) => {
    expect(actionRequestSchema.safeParse(request).success).toBe(false);
  });

  it("applies action text limits by Unicode character like the public API", () => {
    const request = {
      turn_id: "turn-unicode-length",
      client_request_id: "request-unicode-length",
      action_type: "OBSERVE",
    } as const;

    expect(
      actionRequestSchema.safeParse({
        ...request,
        description: "😀".repeat(150),
      }).success,
    ).toBe(true);
    expect(
      actionRequestSchema.safeParse({
        ...request,
        description: "😀".repeat(151),
      }).success,
    ).toBe(false);
  });

  it.each([200, 202] as const)(
    "classifies HTTP %i with repeated NarrativeFrame fact IDs as a safe invalid response",
    async (status) => {
      const requestId = `request-duplicate-facts-${status}`;
      const baseResponse =
        status === 200
          ? actionResponseWithFactIds(
              ["fact.repeated"],
              ["fact.repeated"],
              requestId,
            )
          : {
              ...pendingActionResponseFixture(requestId),
              narrative_frame: actionResponseWithFactIds(
                ["fact.repeated"],
                ["fact.repeated"],
                requestId,
              ).narrative_frame,
            };
      server.use(
        http.post(
          `${apiOrigin}/v1/sessions/session-public-1/actions`,
          () => HttpResponse.json(baseResponse, { status }),
        ),
      );

      let capturedError: Error | null = null;
      try {
        await client().submitAction("session-public-1", {
          turn_id: `turn-duplicate-facts-${status}`,
          client_request_id: requestId,
          action_type: "CONTINUE",
        });
      } catch (error: unknown) {
        if (error instanceof Error) {
          capturedError = error;
        }
      }

      expect(capturedError).toMatchObject({
        kind: "invalid-response",
        status,
        reason: "CONTRACT_MISMATCH",
        message: "Server response does not match the public contract",
      });
      expect(capturedError?.message).not.toContain("fact.repeated");
      expect(capturedError?.message).not.toMatch(/zod|stack|narrative frame/i);
    },
  );

  it("rejects repeated NarrativeFrame fact IDs inside COMMITTED request status", async () => {
    const requestId = "request-status-duplicate-facts";
    server.use(
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/${requestId}`,
        () =>
          HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: requestId,
            status: "COMMITTED",
            client_action: "RESPONSE_AVAILABLE",
            error_code: null,
            retry_after_seconds: null,
            response: {
              ...committedActionResponseFixture(requestId),
              narrative_frame: actionResponseWithFactIds(
                ["fact.repeated"],
                ["fact.repeated"],
                requestId,
              ).narrative_frame,
            },
          }),
      ),
    );

    await expect(
      client().getNarrativeRequestStatus("session-public-1", requestId),
    ).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
      reason: "CONTRACT_MISMATCH",
    });
  });

  it("accepts public lowercase result and feedback code strings and still rejects non-strings", () => {
    const response = synchronousActionResponseFixture("request-lowercase-codes");

    expect(
      actionResponseSchema.safeParse({
        ...response,
        result_code: "scenario.auto_beat_advanced",
        feedback_code: "scenario feedback available",
      }).success,
    ).toBe(true);
    expect(
      actionResponseSchema.safeParse({ ...response, result_code: 7 }).success,
    ).toBe(false);
    expect(
      actionResponseSchema.safeParse({ ...response, feedback_code: false })
        .success,
    ).toBe(false);
  });

  it("accepts lowercase public code strings through an HTTP 200 action response", async () => {
    const requestId = "request-http-lowercase-codes";
    server.use(
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () =>
          HttpResponse.json({
            ...synchronousActionResponseFixture(requestId),
            result_code: "scenario.auto_beat_advanced",
            feedback_code: "scenario feedback available",
          }),
      ),
    );

    await expect(
      client().submitAction("session-public-1", {
        turn_id: "turn-http-lowercase-codes",
        client_request_id: requestId,
        action_type: "CONTINUE",
      }),
    ).resolves.toMatchObject({
      status: 200,
      response: {
        result_code: "scenario.auto_beat_advanced",
        feedback_code: "scenario feedback available",
      },
    });
  });

  it("accepts lowercase public code strings inside COMMITTED request status", async () => {
    const requestId = "request-status-lowercase-codes";
    server.use(
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/${requestId}`,
        () =>
          HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: requestId,
            status: "COMMITTED",
            client_action: "RESPONSE_AVAILABLE",
            error_code: null,
            retry_after_seconds: null,
            response: {
              ...committedActionResponseFixture(requestId),
              result_code: "narrative.outcome_committed",
              feedback_code: "narrative committed",
            },
          }),
      ),
    );

    await expect(
      client().getNarrativeRequestStatus("session-public-1", requestId),
    ).resolves.toMatchObject({
      status: "COMMITTED",
      response: {
        result_code: "narrative.outcome_committed",
        feedback_code: "narrative committed",
      },
    });
  });

  it.each([
    ["same object key order", { a: 1, b: 2 }, { a: 1, b: 2 }, true],
    ["different object key order", { a: 1, b: 2 }, { b: 2, a: 1 }, true],
    [
      "different nested object key order",
      { outer: { a: 1, b: { x: true, y: null } } },
      { outer: { b: { y: null, x: true }, a: 1 } },
      true,
    ],
    ["same array order", { values: [1, 2, 3] }, { values: [1, 2, 3] }, true],
    ["different array order", { values: [1, 2, 3] }, { values: [3, 2, 1] }, false],
    ["missing object key", { a: 1, b: 2 }, { a: 1 }, false],
    ["different value", { a: 1, b: 2 }, { a: 1, b: 3 }, false],
  ] as const)(
    "compares local query JSON by semantic value for %s",
    (_label, feedbackParameters, localQueryResult, expected) => {
      expect(
        actionResponseSchema.safeParse(
          localQueryActionResponse(
            { ...feedbackParameters },
            { ...localQueryResult },
          ),
        ).success,
      ).toBe(expected);
    },
  );

  it("accepts an HTTP 200 local-query DTO whose JSON object keys are reordered", async () => {
    const requestId = "request-http-reordered-json";
    server.use(
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () =>
          HttpResponse.json(
            localQueryActionResponse(
              { first: 1, nested: { alpha: true, beta: [1, 2] } },
              { nested: { beta: [1, 2], alpha: true }, first: 1 },
              requestId,
            ),
          ),
      ),
    );

    await expect(
      client().submitAction("session-public-1", {
        turn_id: "turn-http-reordered-json",
        client_request_id: requestId,
        action_type: "CONTINUE",
      }),
    ).resolves.toMatchObject({ status: 200 });
  });

  it("accepts reordered local-query JSON inside a COMMITTED request status", async () => {
    const requestId = "request-status-reordered-json";
    server.use(
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/${requestId}`,
        () =>
          HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: requestId,
            status: "COMMITTED",
            client_action: "RESPONSE_AVAILABLE",
            error_code: null,
            retry_after_seconds: null,
            response: localQueryActionResponse(
              { dynamic_a: 1, dynamic_b: { left: true, right: false } },
              { dynamic_b: { right: false, left: true }, dynamic_a: 1 },
              requestId,
            ),
          }),
      ),
    );

    const result = await client().getNarrativeRequestStatus(
      "session-public-1",
      requestId,
    );

    expect(result.status).toBe("COMMITTED");
    if (result.status === "COMMITTED") {
      expect(result.response.feedback_parameters).toEqual({
        dynamic_a: 1,
        dynamic_b: { left: true, right: false },
      });
      expect(result.response.local_query_result).toEqual({
        dynamic_b: { right: false, left: true },
        dynamic_a: 1,
      });
    }
  });

  it("rejects unknown fields throughout an ActionResponse NarrativeFrame instead of stripping them", async () => {
    const baseResponse = synchronousActionResponseFixture("request-strict-frame");
    const frame = baseResponse.narrative_frame;
    const suggestedAction =
      activeViewFixture.narrative_frame.suggested_actions[0];
    if (frame === null || suggestedAction === undefined) {
      throw new Error("strict response fixtures must contain nested Frame objects");
    }
    const invalidResponses = [
      {
        label: "ActionResponse top level",
        response: { ...baseResponse, future_action_field: "must reject" },
      },
      {
        label: "NarrativeFrame direct field",
        response: {
          ...baseResponse,
          narrative_frame: { ...frame, future_frame_field: "must reject" },
        },
      },
      {
        label: "RenderableFact array item",
        response: {
          ...baseResponse,
          narrative_frame: {
            ...frame,
            must_render_facts: [
              {
                fact_id: "fact.public.signal",
                value: { arbitrary_public_json: { remains_allowed: true } },
                future_fact_metadata: "must reject",
              },
            ],
          },
        },
      },
      {
        label: "SuggestedAction array item",
        response: {
          ...baseResponse,
          narrative_frame: {
            ...activeViewFixture.narrative_frame,
            suggested_actions: [
              { ...suggestedAction, future_action_hint: "must reject" },
            ],
          },
        },
      },
      {
        label: "VisibleClock array item",
        response: {
          ...baseResponse,
          narrative_frame: {
            ...frame,
            player_visible_clocks: [
              {
                clock_id: "clock.public.tide",
                value: 2,
                maximum: 8,
                future_clock_metadata: "must reject",
              },
            ],
          },
        },
      },
    ];

    for (const invalid of invalidResponses) {
      server.use(
        http.post(
          `${apiOrigin}/v1/sessions/session-public-1/actions`,
          () => HttpResponse.json(invalid.response),
        ),
      );

      await expect(
        client().submitAction("session-public-1", {
          turn_id: "turn-strict-frame",
          client_request_id: "request-strict-frame",
          action_type: "CONTINUE",
        }),
        invalid.label,
      ).rejects.toMatchObject({
        kind: "invalid-response",
        status: 200,
        reason: "CONTRACT_MISMATCH",
      });
    }
  });

  it("rejects a recursively invalid ActionResponse inside COMMITTED request status", async () => {
    const response = committedActionResponseFixture("request-strict-status");
    const frame = response.narrative_frame;
    if (frame === null) {
      throw new Error("committed response fixture must contain one Frame");
    }
    server.use(
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/requests/request-strict-status`,
        () =>
          HttpResponse.json({
            session_id: "session-public-1",
            client_request_id: "request-strict-status",
            status: "COMMITTED",
            client_action: "RESPONSE_AVAILABLE",
            error_code: null,
            retry_after_seconds: null,
            response: {
              ...response,
              narrative_frame: {
                ...frame,
                npc_knowledge: [
                  {
                    npc_id: "npc.public.guide",
                    npc_definition_id: "npc.definition.guide",
                    known_facts: [],
                    future_npc_metadata: "must reject",
                  },
                ],
              },
            },
          }),
      ),
    );

    await expect(
      client().getNarrativeRequestStatus(
        "session-public-1",
        "request-strict-status",
      ),
    ).rejects.toMatchObject({
      kind: "invalid-response",
      status: 200,
      reason: "CONTRACT_MISMATCH",
    });
  });

  it("preserves arbitrary JSON where the Python response contract explicitly allows it", async () => {
    const response = synchronousActionResponseFixture("request-json-values");
    const frame = response.narrative_frame;
    if (frame === null) {
      throw new Error("response fixture must contain one Frame");
    }
    const allowedJson = {
      extension_key: { nested_key: [true, 3, "public value"] },
    };
    server.use(
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () =>
          HttpResponse.json({
            ...response,
            feedback_parameters: allowedJson,
            narrative_frame: {
              ...frame,
              must_render_facts: [
                { fact_id: "fact.public.signal", value: allowedJson },
              ],
            },
          }),
      ),
    );

    const result = await client().submitAction("session-public-1", {
      turn_id: "turn-json-values",
      client_request_id: "request-json-values",
      action_type: "CONTINUE",
    });

    expect(result.response.feedback_parameters).toEqual(allowedJson);
    expect(result.response.narrative_frame?.must_render_facts[0]?.value).toEqual(
      allowedJson,
    );
  });

  it.each([
    ["10,000 BMP code points", "界".repeat(10_000), true],
    ["10,001 BMP code points", "界".repeat(10_001), false],
    ["6,000 astral code points", "😀".repeat(6_000), true],
    ["10,000 astral code points", "😀".repeat(10_000), true],
    ["10,001 astral code points", "😀".repeat(10_001), false],
  ] as const)(
    "validates ActionResponse narrative_text by Python Unicode code points at %s",
    (_label, narrativeText, expected) => {
      const result = actionResponseSchema.safeParse({
        ...committedActionResponseFixture("request-unicode-response"),
        narrative_text: narrativeText,
      });

      expect(result.success).toBe(expected);
    },
  );

  it("uses the same code-point boundary for COMMITTED request-status responses", () => {
    const status = (narrativeText: string) => ({
      session_id: "session-public-1",
      client_request_id: "request-unicode-status",
      status: "COMMITTED",
      client_action: "RESPONSE_AVAILABLE",
      error_code: null,
      retry_after_seconds: null,
      response: {
        ...committedActionResponseFixture("request-unicode-status"),
        narrative_text: narrativeText,
      },
    });

    expect(
      narrativeRequestStatusResponseSchema.safeParse(
        status("😀".repeat(10_000)),
      ).success,
    ).toBe(true);
    expect(
      narrativeRequestStatusResponseSchema.safeParse(
        status("😀".repeat(10_001)),
      ).success,
    ).toBe(false);
  });

  it("validates NarrativeFrame label_hint by its 160-code-point Python limit", () => {
    const suggestedAction =
      activeViewFixture.narrative_frame.suggested_actions[0];
    if (suggestedAction === undefined) {
      throw new Error("active view fixture must contain one suggested action");
    }
    const responseWithLabel = (labelHint: string) => ({
      ...synchronousActionResponseFixture("request-frame-label"),
      narrative_frame: {
        ...activeViewFixture.narrative_frame,
        suggested_actions: [
          { ...suggestedAction, label_hint: labelHint },
        ],
      },
    });

    expect(
      actionResponseSchema.safeParse(responseWithLabel("😀".repeat(160))).success,
    ).toBe(true);
    expect(
      actionResponseSchema.safeParse(responseWithLabel("😀".repeat(161))).success,
    ).toBe(false);
  });

  it("applies PlayerSessionView character and UTF-8 budgets independently", () => {
    const viewWithTexts = (recentNarrativeTexts: string[]) => ({
      ...freeActionViewFixture(),
      recent_narrative_texts: recentNarrativeTexts,
    });
    const tenThousandCodePoints = `😀${"a".repeat(9_999)}`;

    expect(
      playerSessionViewSchema.safeParse(
        viewWithTexts([tenThousandCodePoints, "b".repeat(2_000)]),
      ).success,
    ).toBe(true);
    expect(
      playerSessionViewSchema.safeParse(
        viewWithTexts([tenThousandCodePoints, "b".repeat(2_001)]),
      ).success,
    ).toBe(false);
    expect(
      playerSessionViewSchema.safeParse(
        viewWithTexts(["😀".repeat(6_000)]),
      ).success,
    ).toBe(true);
    expect(
      playerSessionViewSchema.safeParse(
        viewWithTexts(["😀".repeat(6_001)]),
      ).success,
    ).toBe(false);
  });

  it("rejects illegal action responses and status combinations", async () => {
    expect(
      actionResponseSchema.safeParse({
        ...pendingActionResponseFixture("request-invalid-response"),
        narrative_pending: false,
      }).success,
    ).toBe(false);
    expect(
      actionResponseSchema.safeParse({
        ...synchronousActionResponseFixture("request-extra"),
        action_id: "invented-action-id",
      }).success,
    ).toBe(false);
    expect(
      narrativeRequestStatusResponseSchema.safeParse({
        session_id: "session-public-1",
        client_request_id: "request-status",
        status: "PENDING",
        client_action: "REFRESH_VIEW",
        error_code: null,
        retry_after_seconds: 2,
        response: null,
      }).success,
    ).toBe(false);
    expect(
      narrativeRequestStatusResponseSchema.safeParse({
        session_id: "session-public-1",
        client_request_id: "request-status",
        status: "RETRYING",
        client_action: "POLL_SAME_REQUEST",
        error_code: null,
        retry_after_seconds: 2,
        response: null,
      }).success,
    ).toBe(false);

    server.use(
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        () =>
          HttpResponse.json(
            pendingActionResponseFixture("different-request"),
            { status: 202 },
          ),
      ),
    );
    await expect(
      client().submitAction("session-public-1", {
        turn_id: "turn-mismatch",
        client_request_id: "request-mismatch",
        action_type: "TALK",
        dialogue: "检查绑定",
      }),
    ).rejects.toMatchObject({
      kind: "invalid-response",
      reason: "CONTRACT_MISMATCH",
    });
  });

  it("rejects a committed status whose nested response has another identity", () => {
    expect(
      narrativeRequestStatusResponseSchema.safeParse({
        session_id: "session-public-1",
        client_request_id: "request-status",
        status: "COMMITTED",
        client_action: "RESPONSE_AVAILABLE",
        error_code: null,
        retry_after_seconds: null,
        response: committedActionResponseFixture("another-request"),
      }).success,
    ).toBe(false);
  });

  it("parses every server-owned dynamic identity and reuses each exact nested HTTP payload", async () => {
    const source = freeActionViewFixture();
    const freeCustom = {
      action_type: "CUSTOM" as const,
      label: "Server-owned free CUSTOM label",
      input_kind: "DESCRIPTION" as const,
      max_input_length: 150,
      target_required: false,
      targets: [],
    };
    const suggested_actions = [0, 1, 2].map((ordinal) => ({
      suggestion_id: `sug.server-owned-${ordinal}`,
      ordinal,
      label: `Server suggestion ${ordinal}`,
      description: `Server suggestion ${ordinal}`,
      submission: {
        turn_id: `dst.server-owned-${ordinal}`,
        client_request_id: `dsr.server-owned-${ordinal}`,
        action_type: "CUSTOM" as const,
        description: `Server suggestion ${ordinal}`,
      },
    }));
    const authoritativeView = {
      ...source,
      action_affordances: {
        mode: "FREE_ACTIONS",
        actions: [freeCustom],
        decision_id: null,
        choices: [],
        suggested_actions,
      },
    };
    const observedBodies: unknown[] = [];
    server.use(
      http.get(`${apiOrigin}/v1/sessions/session-public-1/view`, () =>
        HttpResponse.json(authoritativeView),
      ),
      http.post(
        `${apiOrigin}/v1/sessions/session-public-1/actions`,
        async ({ request }) => {
          const body = await request.json();
          observedBodies.push(body);
          const requestId = (body as { client_request_id: string })
            .client_request_id;
          return HttpResponse.json(
            synchronousActionResponseFixture(requestId),
          );
        },
      ),
    );

    const api = client();
    const parsed = await api.getSessionView("session-public-1");
    expect(parsed.action_affordances.actions).toEqual([freeCustom]);
    expect(parsed.action_affordances.actions[0]?.label).toBe(
      "Server-owned free CUSTOM label",
    );
    expect(parsed.action_affordances.suggested_actions).toEqual(
      suggested_actions,
    );
    expect(
      parsed.action_affordances.suggested_actions?.map(
        ({ suggestion_id, ordinal, submission }) => ({
          suggestion_id,
          ordinal,
          turn_id: submission.turn_id,
          client_request_id: submission.client_request_id,
        }),
      ),
    ).toEqual([
      {
        suggestion_id: "sug.server-owned-0",
        ordinal: 0,
        turn_id: "dst.server-owned-0",
        client_request_id: "dsr.server-owned-0",
      },
      {
        suggestion_id: "sug.server-owned-1",
        ordinal: 1,
        turn_id: "dst.server-owned-1",
        client_request_id: "dsr.server-owned-1",
      },
      {
        suggestion_id: "sug.server-owned-2",
        ordinal: 2,
        turn_id: "dst.server-owned-2",
        client_request_id: "dsr.server-owned-2",
      },
    ]);

    for (const suggestion of parsed.action_affordances.suggested_actions ?? []) {
      await api.submitAction("session-public-1", suggestion.submission);
    }

    expect(observedBodies).toEqual(
      suggested_actions.map((suggestion) => suggestion.submission),
    );
    for (const [index, body] of observedBodies.entries()) {
      expect(Object.keys(body as Record<string, unknown>)).toEqual([
        "turn_id",
        "client_request_id",
        "action_type",
        "description",
      ]);
      expect(body).not.toHaveProperty("suggestion_id");
      expect(body).not.toHaveProperty("label");
      expect(body).toEqual(suggested_actions[index]?.submission);
    }
  });
});

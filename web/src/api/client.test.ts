import { HttpResponse, delay, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PublicApiClient } from "./client";
import { configuredApiBaseUrl, normalizeApiBaseUrl } from "./config";
import { playerSessionViewSchema } from "./schemas";
import {
  activeViewFixture,
  endedViewFixture,
  errorFixture,
  scenarioCatalogFixture,
  sessionCreationFixture,
} from "../test/fixtures";
import { server } from "../test/server";

const apiOrigin = "http://api.test";

function client(baseUrl = `${apiOrigin}/`) {
  return new PublicApiClient({ baseUrl });
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
        }),
      ),
    );

    const result = await client().listScenarios();
    expect(result).not.toHaveProperty("future_public_hint");
  });

  it("allows harmless added PlayerSessionView fields without exposing them", () => {
    const result = playerSessionViewSchema.parse({
      ...activeViewFixture,
      future_public_hint: "safe additive field",
    });

    expect(result).not.toHaveProperty("future_public_hint");
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
        return HttpResponse.json(activeViewFixture);
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

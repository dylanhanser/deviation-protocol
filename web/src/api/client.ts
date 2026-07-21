import type { z } from "zod";

import { configuredApiBaseUrl, normalizeApiBaseUrl } from "./config";
import { ApiClientError } from "./errors";
import type { InvalidResponseReason } from "./errors";
import {
  createSessionRequestSchema,
  errorResponseSchema,
  playerSessionViewSchema,
  publicScenarioCatalogSchema,
  sessionPathIdSchema,
  sessionCreationResultSchema,
  type CreateSessionRequest,
  type PlayerSessionView,
  type PublicScenarioCatalog,
  type SessionCreationResult,
} from "./schemas";

type FetchImplementation = typeof fetch;

interface PublicApiClientOptions {
  baseUrl?: string | URL;
  fetchImplementation?: FetchImplementation;
  origin?: string;
}

function isJsonContentType(contentType: string | null): boolean {
  if (contentType === null) {
    return false;
  }
  const mediaType = contentType.split(";", 1)[0]?.trim().toLowerCase();
  return mediaType === "application/json" || mediaType?.endsWith("+json") === true;
}

function responseError(
  response: Response,
  reason: InvalidResponseReason,
): ApiClientError {
  return new ApiClientError("Server response does not match the public contract", {
    kind: "invalid-response",
    status: response.status,
    reason,
  });
}

async function parseJsonBody(response: Response): Promise<unknown> {
  const body = await response.text();
  if (body.trim() === "") {
    throw responseError(response, "EMPTY_RESPONSE");
  }
  if (!isJsonContentType(response.headers.get("content-type"))) {
    throw responseError(response, "NON_JSON_RESPONSE");
  }
  try {
    return JSON.parse(body) as unknown;
  } catch {
    throw responseError(response, "MALFORMED_JSON");
  }
}

export class PublicApiClient {
  private readonly baseUrl: URL;
  private readonly fetchImplementation: FetchImplementation | undefined;

  constructor(options: PublicApiClientOptions = {}) {
    if (options.baseUrl instanceof URL) {
      this.baseUrl = normalizeApiBaseUrl(options.baseUrl.toString());
    } else if (options.baseUrl !== undefined) {
      this.baseUrl = normalizeApiBaseUrl(options.baseUrl, options.origin);
    } else {
      this.baseUrl = configuredApiBaseUrl();
    }
    this.fetchImplementation = options.fetchImplementation;
  }

  listScenarios(signal?: AbortSignal): Promise<PublicScenarioCatalog> {
    return this.request(
      "v1/scenarios",
      { method: "GET", ...(signal === undefined ? {} : { signal }) },
      200,
      publicScenarioCatalogSchema,
    );
  }

  createSession(
    request: CreateSessionRequest,
    signal?: AbortSignal,
  ): Promise<SessionCreationResult> {
    const body = createSessionRequestSchema.parse(request);
    return this.request(
      "v1/sessions",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        ...(signal === undefined ? {} : { signal }),
      },
      201,
      sessionCreationResultSchema,
    );
  }

  getSessionView(
    sessionId: string,
    signal?: AbortSignal,
  ): Promise<PlayerSessionView> {
    const validatedSessionId = sessionPathIdSchema.parse(sessionId);
    return this.request(
      `v1/sessions/${encodeURIComponent(validatedSessionId)}/view`,
      { method: "GET", ...(signal === undefined ? {} : { signal }) },
      200,
      playerSessionViewSchema,
    );
  }

  private async request<T>(
    relativePath: string,
    init: RequestInit,
    expectedStatus: number,
    schema: z.ZodType<T>,
  ): Promise<T> {
    const url = new URL(relativePath, this.baseUrl);
    let response: Response;
    let payload: unknown;
    try {
      response = await (this.fetchImplementation ?? globalThis.fetch)(url, {
        ...init,
        headers: {
          Accept: "application/json",
          ...init.headers,
        },
      });
      payload = await parseJsonBody(response);
    } catch (cause) {
      if (cause instanceof ApiClientError) {
        throw cause;
      }
      if (
        init.signal?.aborted === true ||
        (cause instanceof DOMException && cause.name === "AbortError")
      ) {
        throw new ApiClientError("Request was aborted", {
          kind: "aborted",
          cause,
        });
      }
      throw new ApiClientError("Public API request failed", {
        kind: "network",
        cause,
      });
    }

    if (!response.ok) {
      const parsedError = errorResponseSchema.safeParse(payload);
      if (!parsedError.success) {
        throw responseError(response, "CONTRACT_MISMATCH");
      }
      throw new ApiClientError(parsedError.data.error.message, {
        kind: "api",
        status: response.status,
        errorCode: parsedError.data.error.error_code,
      });
    }
    if (response.status !== expectedStatus) {
      throw responseError(response, "UNEXPECTED_STATUS");
    }
    const parsed = schema.safeParse(payload);
    if (!parsed.success) {
      throw responseError(response, "CONTRACT_MISMATCH");
    }
    return parsed.data;
  }
}

export const publicApiClient = new PublicApiClient();

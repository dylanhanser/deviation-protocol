import type { z } from "zod";

import { configuredApiBaseUrl, normalizeApiBaseUrl } from "./config";
import { ApiClientError } from "./errors";
import type {
  InvalidResponseReason,
  ResponseIdentityMismatch,
} from "./errors";
import {
  actionRequestSchema,
  actionResponseSchema,
  createSessionRequestSchema,
  errorResponseSchema,
  narrativeRequestStatusResponseSchema,
  playerSessionViewSchema,
  publicScenarioCatalogSchema,
  requestPathIdSchema,
  sessionPathIdSchema,
  sessionCreationResultSchema,
  type ActionRequest,
  type ActionResponse,
  type CreateSessionRequest,
  type NarrativeRequestStatusResponse,
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

export interface PublicActionSubmissionResult {
  status: 200 | 202;
  response: ActionResponse;
}

function isJsonContentType(contentType: string | null): boolean {
  if (contentType === null) {
    return false;
  }
  const mediaType = contentType.split(";", 1)[0]?.trim().toLowerCase();
  return mediaType === "application/json" || mediaType?.endsWith("+json") === true;
}

function responseError(
  status: number,
  reason: InvalidResponseReason,
): ApiClientError {
  return new ApiClientError("Server response does not match the public contract", {
    kind: "invalid-response",
    status,
    reason,
  });
}

function responseIdentityMismatch(
  status: number,
  identityMismatch: ResponseIdentityMismatch,
): ApiClientError {
  return new ApiClientError("Server response identity does not match the request", {
    kind: "identity-mismatch",
    status,
    identityMismatch,
  });
}

async function parseJsonBody(response: Response): Promise<unknown> {
  const body = await response.text();
  if (body.trim() === "") {
    throw responseError(response.status, "EMPTY_RESPONSE");
  }
  if (!isJsonContentType(response.headers.get("content-type"))) {
    throw responseError(response.status, "NON_JSON_RESPONSE");
  }
  try {
    return JSON.parse(body) as unknown;
  } catch {
    throw responseError(response.status, "MALFORMED_JSON");
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
    ).then((view) => {
      if (view.metadata.session_id !== validatedSessionId) {
        throw responseError(200, "CONTRACT_MISMATCH");
      }
      return view;
    });
  }

  async submitAction(
    sessionId: string,
    request: ActionRequest,
    signal?: AbortSignal,
  ): Promise<PublicActionSubmissionResult> {
    const validatedSessionId = sessionPathIdSchema.parse(sessionId);
    const body = actionRequestSchema.parse(request);
    const result = await this.requestWithStatus(
      `v1/sessions/${encodeURIComponent(validatedSessionId)}/actions`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        ...(signal === undefined ? {} : { signal }),
      },
      [200, 202] as const,
      actionResponseSchema,
    );
    if (
      result.data.session_id !== validatedSessionId ||
      result.data.client_request_id !== body.client_request_id ||
      (result.status === 202) !== result.data.narrative_pending
    ) {
      throw responseError(result.status, "CONTRACT_MISMATCH");
    }
    return { status: result.status, response: result.data };
  }

  async getNarrativeRequestStatus(
    sessionId: string,
    clientRequestId: string,
    signal?: AbortSignal,
  ): Promise<NarrativeRequestStatusResponse> {
    const validatedSessionId = sessionPathIdSchema.parse(sessionId);
    const validatedRequestId = requestPathIdSchema.parse(clientRequestId);
    const status = await this.request(
      `v1/sessions/${encodeURIComponent(validatedSessionId)}/requests/${encodeURIComponent(validatedRequestId)}`,
      { method: "GET", ...(signal === undefined ? {} : { signal }) },
      200,
      narrativeRequestStatusResponseSchema,
    );
    if (status.session_id !== validatedSessionId) {
      throw responseIdentityMismatch(200, "SESSION_ID");
    }
    if (status.client_request_id !== validatedRequestId) {
      throw responseIdentityMismatch(200, "CLIENT_REQUEST_ID");
    }
    return status;
  }

  private async request<T>(
    relativePath: string,
    init: RequestInit,
    expectedStatus: number,
    schema: z.ZodType<T>,
  ): Promise<T> {
    const result = await this.requestWithStatus(
      relativePath,
      init,
      [expectedStatus],
      schema,
    );
    return result.data;
  }

  private async requestWithStatus<T, Status extends number>(
    relativePath: string,
    init: RequestInit,
    expectedStatuses: readonly Status[],
    schema: z.ZodType<T>,
  ): Promise<{ status: Status; data: T }> {
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
        throw responseError(response.status, "CONTRACT_MISMATCH");
      }
      throw new ApiClientError(parsedError.data.error.message, {
        kind: "api",
        status: response.status,
        errorCode: parsedError.data.error.error_code,
      });
    }
    if (!expectedStatuses.includes(response.status as Status)) {
      throw responseError(response.status, "UNEXPECTED_STATUS");
    }
    const parsed = schema.safeParse(payload);
    if (!parsed.success) {
      throw responseError(response.status, "CONTRACT_MISMATCH");
    }
    return { status: response.status as Status, data: parsed.data };
  }
}

export const publicApiClient = new PublicApiClient();

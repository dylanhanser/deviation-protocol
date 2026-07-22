export type ApiClientErrorKind =
  | "api"
  | "aborted"
  | "network"
  | "identity-mismatch"
  | "invalid-response"
  | "configuration";

export type ResponseIdentityMismatch = "SESSION_ID" | "CLIENT_REQUEST_ID";

export type InvalidResponseReason =
  | "EMPTY_RESPONSE"
  | "NON_JSON_RESPONSE"
  | "MALFORMED_JSON"
  | "CONTRACT_MISMATCH"
  | "UNEXPECTED_STATUS";

interface ApiClientErrorOptions {
  kind: ApiClientErrorKind;
  status?: number;
  errorCode?: string;
  reason?: InvalidResponseReason;
  identityMismatch?: ResponseIdentityMismatch;
  cause?: unknown;
}

export class ApiClientError extends Error {
  readonly kind: ApiClientErrorKind;
  readonly status: number | undefined;
  readonly errorCode: string | undefined;
  readonly reason: InvalidResponseReason | undefined;
  readonly identityMismatch: ResponseIdentityMismatch | undefined;

  constructor(message: string, options: ApiClientErrorOptions) {
    super(message, { cause: options.cause });
    this.name = "ApiClientError";
    this.kind = options.kind;
    this.status = options.status;
    this.errorCode = options.errorCode;
    this.reason = options.reason;
    this.identityMismatch = options.identityMismatch;
  }
}

export function formatApiClientError(error: unknown): string {
  if (!(error instanceof ApiClientError)) {
    return "发生未知错误，请稍后重试。";
  }
  if (error.kind === "api") {
    const status = error.status === undefined ? "" : `HTTP ${error.status} · `;
    const code = error.errorCode === undefined ? "" : `${error.errorCode} · `;
    return `${status}${code}${error.message}`;
  }
  if (error.kind === "aborted") {
    return "请求已取消。";
  }
  if (error.kind === "network") {
    return "无法连接公开 API，请检查服务地址和网络状态。";
  }
  if (error.kind === "configuration") {
    return "公开 API 地址配置无效。";
  }
  if (error.kind === "identity-mismatch") {
    return "服务器响应身份与请求不匹配。";
  }
  const status = error.status === undefined ? "" : `HTTP ${error.status} · `;
  return `${status}服务器响应不符合公开合同（${error.reason ?? "UNKNOWN"}）。`;
}

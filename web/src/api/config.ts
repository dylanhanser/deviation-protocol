import { ApiClientError } from "./errors";

function isAbsoluteUrl(value: string): boolean {
  return /^[A-Za-z][A-Za-z\d+.-]*:/.test(value);
}

export function normalizeApiBaseUrl(
  configuredValue: string | undefined,
  origin?: string,
): URL {
  const value = configuredValue?.trim() || "/api/";
  let url: URL;
  try {
    if (isAbsoluteUrl(value)) {
      url = new URL(value);
    } else {
      const baseOrigin = origin ?? globalThis.location?.origin;
      if (baseOrigin === undefined) {
        throw new TypeError("relative API base URL requires a browser origin");
      }
      url = new URL(value, baseOrigin);
    }
  } catch (cause) {
    throw new ApiClientError("Public API base URL is invalid", {
      kind: "configuration",
      cause,
    });
  }

  if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) {
    throw new ApiClientError("Public API base URL is invalid", {
      kind: "configuration",
    });
  }
  url.search = "";
  url.hash = "";
  url.pathname = `${url.pathname.replace(/\/+$/, "")}/`;
  return url;
}

export function configuredApiBaseUrl(): URL {
  return normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
}

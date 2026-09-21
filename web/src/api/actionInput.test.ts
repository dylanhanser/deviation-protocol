import { describe, expect, it, vi } from "vitest";
import { ZodError } from "zod";

import { PublicApiClient } from "./client";
import { ApiClientError, formatApiClientError } from "./errors";
import { actionRequestSchema, singleLineActionTextSchema } from "./schemas";

const message = "当前输入仅支持单行文字，请删除换行后重试。";
const unknownMessage = "发生未知错误，请稍后重试。";
const identity = { turn_id: "turn-input", client_request_id: "request-input" };

describe("single-line action validation", () => {
  it("keeps literal escape spellings as single-line text", () => {
    const request = {
      ...identity, action_type: "OBSERVE", description: "记录字面量 \\n 与 \\r",
    };
    expect(actionRequestSchema.parse(request)).toEqual(request);
  });

  it.each(["\n", "\r\n", "\r"])(
    "preserves a typed line-break error before fetch for %j",
    async (lineBreak) => {
      const fetchImplementation = vi.fn<typeof fetch>();
      const client = new PublicApiClient({ baseUrl: "http://input.test/", fetchImplementation });
      for (const text of [`前${lineBreak}后`, `${lineBreak}原文`, `原文${lineBreak}`, `${lineBreak}原文${lineBreak}`]) {
        const raw = singleLineActionTextSchema.safeParse(text);
        expect(raw.success).toBe(false);
        if (raw.success) throw new Error("unexpected accepted raw line break");
        expect(raw.error.issues).toEqual(expect.arrayContaining([
          expect.objectContaining({ code: "custom", params: { inputViolation: "action-line-break" } }),
        ]));
        for (const payload of [
          { action_type: "OBSERVE" as const, description: text },
          { action_type: "TALK" as const, dialogue: text },
        ]) {
          const request = { ...identity, ...payload };
          const parsed = actionRequestSchema.safeParse(request);
          expect(parsed.success).toBe(false);
          if (parsed.success) throw new Error("unexpected accepted line break");
          expect(parsed.error).toBeInstanceOf(ZodError);
          expect(formatApiClientError(parsed.error)).toBe(message);
          const error = await client.submitAction("session-input", request).catch((value: unknown) => value);
          expect(error).toBeInstanceOf(ZodError);
          expect(formatApiClientError(error)).toBe(message);
        }
      }
      expect(fetchImplementation).not.toHaveBeenCalled();
    },
  );

  it.each(["\u2028", "\u2029"])(
    "preserves baseline schema and request construction for %j", async (separator) => {
      const text = `前${separator}后`;
      expect(singleLineActionTextSchema.parse(text)).toBe(text);
      const fetchImplementation = vi.fn<typeof fetch>().mockImplementation(async () => new Response(
        JSON.stringify({ error: { error_code: "REQUEST_VALIDATION_FAILED", message: "Request validation failed" } }),
        { status: 422, headers: { "Content-Type": "application/json" } },
      ));
      const client = new PublicApiClient({ baseUrl: "http://input.test/", fetchImplementation });
      for (const payload of [
        { action_type: "OBSERVE" as const, description: text },
        { action_type: "TALK" as const, dialogue: text },
      ]) {
        const request = { ...identity, ...payload };
        expect(actionRequestSchema.parse(request)).toEqual(request);
        const error = await client.submitAction("session-input", request).catch((value: unknown) => value);
        expect(JSON.parse(fetchImplementation.mock.lastCall?.[1]?.body as string)).toEqual(request);
        // Schema acceptance does not promise acceptance by a later business policy.
        expect(error).toBeInstanceOf(ApiClientError);
        expect(formatApiClientError(error)).toBe("HTTP 422 · REQUEST_VALIDATION_FAILED · Request validation failed");
      }
      expect(fetchImplementation).toHaveBeenCalledTimes(2);
    },
  );

  it.each(["前\t后", "前\u0000后", "前\u200b后", "前\u000b后", "前\u000c后", "前\u0085后", "", "字".repeat(151)])(
    "does not mislabel another text validation failure: %j",
    async (description) => {
      const fetchImplementation = vi.fn<typeof fetch>();
      const client = new PublicApiClient({ baseUrl: "http://input.test/", fetchImplementation });
      const error = await client.submitAction("session-input", {
        ...identity, action_type: "OBSERVE", description,
      }).catch((value: unknown) => value);
      expect(error).toBeInstanceOf(ZodError);
      expect(formatApiClientError(error)).toBe(unknownMessage);
      expect(fetchImplementation).not.toHaveBeenCalled();
    },
  );

  it("retains unknown and unrelated schema fallbacks", () => {
    expect(formatApiClientError(new Error("private details"))).toBe(unknownMessage);
    const parsed = actionRequestSchema.safeParse({
      ...identity, turn_id: "bad\nid", action_type: "OBSERVE", description: "原文",
    });
    expect(parsed.success).toBe(false);
    if (!parsed.success) expect(formatApiClientError(parsed.error)).toBe(unknownMessage);
  });

  it("preserves the backend 422 envelope without relabeling it as multiline", async () => {
    const fetchImplementation = vi.fn<typeof fetch>().mockResolvedValue(new Response(
      JSON.stringify({ error: { error_code: "REQUEST_VALIDATION_FAILED", message: "Request validation failed" } }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    ));
    const client = new PublicApiClient({ baseUrl: "http://input.test/", fetchImplementation });
    const error = await client.submitAction("session-input", {
      ...identity, action_type: "OBSERVE", description: "单行文字",
    }).catch((value: unknown) => value);
    expect(fetchImplementation).toHaveBeenCalledTimes(1);
    expect(error).toBeInstanceOf(ApiClientError);
    expect(formatApiClientError(error)).toBe("HTTP 422 · REQUEST_VALIDATION_FAILED · Request validation failed");
  });
});

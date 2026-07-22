import { describe, expect, it } from "vitest";

import {
  SESSION_RECOVERY_RECORD_VERSION,
  SESSION_RECOVERY_STORAGE_KEY,
  clearSessionRecoveryRecord,
  readSessionRecoveryRecord,
  writeSessionRecoveryRecord,
} from "./sessionRecovery";

class MemoryStorage implements Storage {
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

function withSessionStorage<T>(storage: Storage, callback: () => T): T {
  const descriptor = Object.getOwnPropertyDescriptor(
    globalThis,
    "sessionStorage",
  );
  Object.defineProperty(globalThis, "sessionStorage", {
    configurable: true,
    value: storage,
  });
  try {
    return callback();
  } finally {
    if (descriptor === undefined) {
      Reflect.deleteProperty(globalThis, "sessionStorage");
    } else {
      Object.defineProperty(globalThis, "sessionStorage", descriptor);
    }
  }
}

function expectValue<T>(result: ReturnType<typeof readSessionRecoveryRecord>): T {
  if (!result.ok) {
    throw new Error(`unexpected storage failure: ${result.failure.operation}`);
  }
  return result.value as T;
}

describe("same-tab Session recovery storage", () => {
  it("writes one versioned allowlist record and atomically clears pending on View commit", () => {
    const storage = new MemoryStorage();

    withSessionStorage(storage, () => {
      expect(writeSessionRecoveryRecord("session-public-1").ok).toBe(true);
      expect(JSON.parse(storage.getItem(SESSION_RECOVERY_STORAGE_KEY)!)).toEqual({
        version: SESSION_RECOVERY_RECORD_VERSION,
        session_id: "session-public-1",
      });

      expect(
        writeSessionRecoveryRecord(
          "session-public-1",
          "confirmed-request-1",
        ).ok,
      ).toBe(true);
      expect(expectValue(readSessionRecoveryRecord())).toEqual({
        version: SESSION_RECOVERY_RECORD_VERSION,
        session_id: "session-public-1",
        client_request_id: "confirmed-request-1",
      });

      expect(writeSessionRecoveryRecord("session-public-1").ok).toBe(true);
      expect(expectValue(readSessionRecoveryRecord())).toEqual({
        version: SESSION_RECOVERY_RECORD_VERSION,
        session_id: "session-public-1",
      });
      expect(storage.length).toBe(1);
    });
  });

  it.each([
    ["malformed JSON", "{"],
    ["unsupported version", JSON.stringify({ version: 2, session_id: "session-1" })],
    [
      "unknown cached View field",
      JSON.stringify({
        version: 1,
        session_id: "session-1",
        view: { action_affordances: [] },
      }),
    ],
    ["invalid Session ID", JSON.stringify({ version: 1, session_id: "bad id" })],
    [
      "invalid request ID",
      JSON.stringify({
        version: 1,
        session_id: "session-1",
        client_request_id: "bad request id",
      }),
    ],
    [
      "null request ID",
      JSON.stringify({
        version: 1,
        session_id: "session-1",
        client_request_id: null,
      }),
    ],
  ])("clears %s without returning recovery authority", (_label, serialized) => {
    const storage = new MemoryStorage();
    storage.setItem(SESSION_RECOVERY_STORAGE_KEY, serialized);

    withSessionStorage(storage, () => {
      expect(expectValue(readSessionRecoveryRecord())).toBeNull();
      expect(storage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBeNull();
    });
  });

  it("distinguishes a sessionStorage property getter failure", () => {
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
    try {
      expect(readSessionRecoveryRecord()).toMatchObject({
        ok: false,
        failure: { operation: "access" },
      });
    } finally {
      if (descriptor !== undefined) {
        Object.defineProperty(globalThis, "sessionStorage", descriptor);
      }
    }
  });

  it.each(["get", "set", "remove"] as const)(
    "returns an explicit failure when %sItem throws",
    (operation) => {
      const storage = new MemoryStorage();
      storage.setItem(
        SESSION_RECOVERY_STORAGE_KEY,
        JSON.stringify({ version: 1, session_id: "session-public-1" }),
      );
      storage.failGet = operation === "get";
      storage.failSet = operation === "set";
      storage.failRemove = operation === "remove";

      withSessionStorage(storage, () => {
        const result =
          operation === "get"
            ? readSessionRecoveryRecord()
            : operation === "set"
              ? writeSessionRecoveryRecord("session-public-2")
              : clearSessionRecoveryRecord();
        expect(result).toMatchObject({
          ok: false,
          failure: { operation },
        });
      });
    },
  );

  it("reports removal failure while discarding an invalid record", () => {
    const storage = new MemoryStorage();
    storage.setItem(SESSION_RECOVERY_STORAGE_KEY, "{");
    storage.failRemove = true;

    withSessionStorage(storage, () => {
      expect(readSessionRecoveryRecord()).toMatchObject({
        ok: false,
        failure: { operation: "remove" },
      });
    });
  });
});

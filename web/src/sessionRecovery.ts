import { z } from "zod";

import { requestPathIdSchema, sessionPathIdSchema } from "./api/schemas";

export const SESSION_RECOVERY_STORAGE_KEY =
  "deviation-protocol.web-session-recovery";
export const SESSION_RECOVERY_RECORD_VERSION = 1 as const;

export const sessionRecoveryRecordSchema = z
  .object({
    version: z.literal(SESSION_RECOVERY_RECORD_VERSION),
    session_id: sessionPathIdSchema,
    client_request_id: requestPathIdSchema.optional(),
  })
  .strict();

export type SessionRecoveryRecord = z.infer<
  typeof sessionRecoveryRecordSchema
>;

export type SessionRecoveryStorageOperation =
  | "access"
  | "get"
  | "set"
  | "remove";

export interface SessionRecoveryStorageFailure {
  operation: SessionRecoveryStorageOperation;
  cause: unknown;
}

export type SessionRecoveryStorageResult<T> =
  | { ok: true; value: T }
  | { ok: false; failure: SessionRecoveryStorageFailure };

function storageFailure<T>(
  operation: SessionRecoveryStorageOperation,
  cause: unknown,
): SessionRecoveryStorageResult<T> {
  return { ok: false, failure: { operation, cause } };
}

function getSessionStorage(): SessionRecoveryStorageResult<Storage> {
  try {
    return { ok: true, value: globalThis.sessionStorage };
  } catch (cause: unknown) {
    return storageFailure("access", cause);
  }
}

function removeRecord(storage: Storage): SessionRecoveryStorageResult<void> {
  try {
    storage.removeItem(SESSION_RECOVERY_STORAGE_KEY);
    return { ok: true, value: undefined };
  } catch (cause: unknown) {
    return storageFailure("remove", cause);
  }
}

export function readSessionRecoveryRecord(): SessionRecoveryStorageResult<
  SessionRecoveryRecord | null
> {
  const storageResult = getSessionStorage();
  if (!storageResult.ok) {
    return storageResult;
  }

  let serialized: string | null;
  try {
    serialized = storageResult.value.getItem(SESSION_RECOVERY_STORAGE_KEY);
  } catch (cause: unknown) {
    return storageFailure("get", cause);
  }
  if (serialized === null) {
    return { ok: true, value: null };
  }

  let candidate: unknown;
  try {
    candidate = JSON.parse(serialized) as unknown;
  } catch {
    const removeResult = removeRecord(storageResult.value);
    return removeResult.ok ? { ok: true, value: null } : removeResult;
  }

  const parsed = sessionRecoveryRecordSchema.safeParse(candidate);
  if (!parsed.success) {
    const removeResult = removeRecord(storageResult.value);
    return removeResult.ok ? { ok: true, value: null } : removeResult;
  }
  return { ok: true, value: parsed.data };
}

export function writeSessionRecoveryRecord(
  sessionId: string,
  confirmedPendingClientRequestId?: string,
): SessionRecoveryStorageResult<SessionRecoveryRecord> {
  const record = sessionRecoveryRecordSchema.parse({
    version: SESSION_RECOVERY_RECORD_VERSION,
    session_id: sessionId,
    ...(confirmedPendingClientRequestId === undefined
      ? {}
      : { client_request_id: confirmedPendingClientRequestId }),
  });
  const storageResult = getSessionStorage();
  if (!storageResult.ok) {
    return storageResult;
  }
  try {
    storageResult.value.setItem(
      SESSION_RECOVERY_STORAGE_KEY,
      JSON.stringify(record),
    );
  } catch (cause: unknown) {
    return storageFailure("set", cause);
  }
  return { ok: true, value: record };
}

export function clearSessionRecoveryRecord(): SessionRecoveryStorageResult<void> {
  const storageResult = getSessionStorage();
  if (!storageResult.ok) {
    return storageResult;
  }
  return removeRecord(storageResult.value);
}

import { ApiClientError } from "./api/errors";
import { idempotencyKeySchema, nativeRunExitRequestSchema, nativeRunStatusSchema, sessionPathIdSchema,
  type NativeRunStatus, type PlayerSessionView } from "./api/schemas";

export interface FrozenRunExit {
  readonly url: string;
  readonly key: string;
  readonly serializedBody: string;
  readonly sessionId: string;
  readonly runId: string;
}

export function assertRunStatus(view: PlayerSessionView, status: NativeRunStatus): void {
  nativeRunStatusSchema.parse(status);
  if (!view.run_context || view.metadata.session_id !== status.session_id ||
      view.run_context.run_id !== status.run_id || view.metadata.state_version !== status.session_state_version) {
    throw new ApiClientError("Run status does not match the loaded View", {kind:"invalid-response", reason:"CONTRACT_MISMATCH"});
  }
}

export function freezeRunExit(view: PlayerSessionView, status: NativeRunStatus, key: string): FrozenRunExit {
  assertRunStatus(view, status);
  if (view.scenario_status !== "ENDED" || !status.can_exit || status.lifecycle_status !== "active") {
    throw new Error("Run exit is not available");
  }
  const sessionId = sessionPathIdSchema.parse(status.session_id);
  return Object.freeze({url:`v1/sessions/${encodeURIComponent(sessionId)}/run-exit`, sessionId,
    runId:status.run_id, key:idempotencyKeySchema.parse(key),
    serializedBody:JSON.stringify(nativeRunExitRequestSchema.parse({expected_run_state_version:status.run_state_version,
      expected_session_state_version:status.session_state_version}))});
}

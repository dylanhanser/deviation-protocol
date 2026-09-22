import { ApiClientError } from "./api/errors";
import { assertNativeView } from "./runSetup";
import { idempotencyKeySchema, nativeRunExitRequestSchema, nativeRunContinuationStatusSchema, nativeRunContinuationResultSchema,
  type NativeRunContinuationStatus, type NativeRunContinuationResult, type PlayerSessionView } from "./api/schemas";
import type { FrozenRunExit } from "./runExit";

export type FrozenRunContinuation = FrozenRunExit;
function mismatch(): never {
  throw new ApiClientError("Continuation identity does not match the loaded journey", {kind:"invalid-response", reason:"CONTRACT_MISMATCH"});
}
export function assertContinuationStatus(view: PlayerSessionView, status: NativeRunContinuationStatus): void {
  nativeRunContinuationStatusSchema.parse(status);
  if (!view.run_context || status.session_id !== view.metadata.session_id || status.run_id !== view.run_context.run_id ||
      status.session_state_version !== view.metadata.state_version) mismatch();
  if (status.successor) assertContinuationResult(view, status.successor);
  if (status.visit?.visit_ordinal === 2 && (view.narrative_frame.scenario_id !== (status.visit.world_id === "world.fog_station" ? "fog_patrol" : "undelivered_receipt") ||
      view.metadata.content_version !== (status.visit.world_id === "world.fog_station" ? "fog-patrol-1.0.0" : "undelivered-receipt-1.0.0"))) mismatch();
}
export function assertContinuationResult(source: PlayerSessionView, result: NativeRunContinuationResult): void {
  nativeRunContinuationResultSchema.parse(result);
  if (source.metadata.session_id !== result.source_session_id || source.metadata.state_version !== result.source_session_state_version ||
      source.run_context?.run_id !== result.run_id) mismatch();
  assertNativeView(source, result.run_context);
}
export interface ConfirmedContinuation {
  source: PlayerSessionView;
  result: NativeRunContinuationResult;
}
export function assertConfirmedSuccessor(confirmed: ConfirmedContinuation, view: PlayerSessionView,
  status: NativeRunContinuationStatus): void {
  const {source,result}=confirmed;
  assertContinuationResult(source,result);
  assertContinuationStatus(view,status);
  assertNativeView(view,result.run_context);
  const predecessor=status.predecessor;
  if (view.metadata.session_id !== result.session_id || status.current_session_id !== result.session_id ||
      view.narrative_frame.scenario_id !== result.scenario_id || view.metadata.content_version !== result.scenario_content_version ||
      !predecessor || predecessor.session_id !== result.source_session_id ||
      predecessor.session_state_version !== result.source_session_state_version ||
      predecessor.scenario_id !== source.narrative_frame.scenario_id || predecessor.scenario_content_version !== source.metadata.content_version ||
      !status.visit || Object.keys(result.visit).some(key => status.visit![key as keyof typeof result.visit] !== result.visit[key as keyof typeof result.visit])) mismatch();
  // Initialization versions belong to the receipt; current Session/Run versions
  // may legitimately advance through actions and continued exit.
}
export function freezeRunContinuation(view: PlayerSessionView, status: NativeRunContinuationStatus, key: string): FrozenRunContinuation {
  assertContinuationStatus(view,status);
  if (view.scenario_status !== "ENDED" || !status.can_continue || status.lifecycle_status !== "active") mismatch();
  return Object.freeze({url:`v1/sessions/${encodeURIComponent(status.session_id)}/run-continuation`, sessionId:status.session_id,
    runId:status.run_id,key:idempotencyKeySchema.parse(key),serializedBody:JSON.stringify(nativeRunExitRequestSchema.parse({
      expected_run_state_version:status.run_state_version,expected_session_state_version:status.session_state_version}))});
}
export function assertHistoricalPair(current: PlayerSessionView, status: NativeRunContinuationStatus,
  history: PlayerSessionView, historicalStatus: NativeRunContinuationStatus): void {
  assertContinuationStatus(current,status); assertContinuationStatus(history,historicalStatus);
  assertNativeView(history,current.run_context);
  const predecessor=status.predecessor, successor=historicalStatus.successor;
  if (!predecessor || !successor || predecessor.session_id !== history.metadata.session_id ||
      predecessor.session_state_version !== history.metadata.state_version || predecessor.scenario_id !== history.narrative_frame.scenario_id ||
      predecessor.scenario_content_version !== history.metadata.content_version || history.scenario_status !== "ENDED" ||
      successor.session_id !== current.metadata.session_id || historicalStatus.current_session_id !== current.metadata.session_id ||
      historicalStatus.run_state_version !== status.run_state_version || historicalStatus.lifecycle_status !== status.lifecycle_status ||
      JSON.stringify(predecessor.visit) !== JSON.stringify(historicalStatus.visit) ||
      JSON.stringify(successor.visit) !== JSON.stringify(status.visit)) mismatch();
}

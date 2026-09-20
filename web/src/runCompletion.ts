import { ApiClientError } from "./api/errors";
import { idempotencyKeySchema, nativeRunJourneySchema, nativeRunCompletionStatusSchema, nativeRunCompletionResultSchema,
  nativeRunExitRequestSchema, type NativeRunCompletionStatus, type NativeRunCompletionResult,
  type NativeRunJourney, type NativeRunStatus, type PlayerSessionView } from "./api/schemas";
import { assertJourneyRunStatus, sameAssociation, sameVisit } from "./runJourney";
import { assertNativeView } from "./runSetup";
import type { FrozenRunExit } from "./runExit";

function mismatch(): never {
  throw new ApiClientError("Completion authority does not match the loaded journey", {kind:"invalid-response",reason:"CONTRACT_MISMATCH"});
}

export type CompletionAuthorities = {journey:NativeRunJourney;status:NativeRunStatus;completion:NativeRunCompletionStatus};
export function assertCompletionAuthorities(view:PlayerSessionView, authorities:CompletionAuthorities):void {
  const {journey,status,completion}=authorities;
  assertJourneyRunStatus(view,journey,status);
  nativeRunCompletionStatusSchema.parse(completion);
  assertNativeView(view,completion.run_context);
  if (completion.session_id!==journey.session_id || completion.run_id!==journey.run_id ||
      completion.run_state_version!==journey.run_state_version || completion.lifecycle_status!==journey.lifecycle_status ||
      JSON.stringify(completion.run_context)!==JSON.stringify(journey.run_context) ||
      !sameAssociation(completion.path,journey.path) || !sameAssociation(completion.current,journey.current) ||
      (completion.can_complete && (view.scenario_status!=="ENDED" || view.ending_id!=="receipt_archive.ending.unresolved_sealed")) ||
      (journey.lifecycle_status==="completed" && JSON.stringify(journey.completion)!==JSON.stringify(completion.completion))) mismatch();
}

export type FrozenRunCompletion=FrozenRunExit & {readonly source:PlayerSessionView;readonly authority:CompletionAuthorities};
export function freezeRunCompletion(view:PlayerSessionView, authority:CompletionAuthorities, key:string):FrozenRunCompletion {
  assertCompletionAuthorities(view,authority);
  if (!authority.completion.can_complete || view.scenario_status!=="ENDED") mismatch();
  const frozen={url:`v1/sessions/${encodeURIComponent(view.metadata.session_id)}/run-complete`,
    sessionId:view.metadata.session_id,runId:authority.journey.run_id,key:idempotencyKeySchema.parse(key),
    serializedBody:JSON.stringify(nativeRunExitRequestSchema.parse({expected_run_state_version:5,
      expected_session_state_version:view.metadata.state_version})),source:structuredClone(view),authority:structuredClone(authority)};
  function freeze(value:object) {Object.freeze(value);for(const child of Object.values(value)) if(child && typeof child==="object") freeze(child);}
  freeze(frozen);
  return frozen;
}

export function assertCompletionSubmission(attempt:FrozenRunCompletion, view:PlayerSessionView, authority:CompletionAuthorities):void {
  assertCompletionAuthorities(view,authority);
  if (JSON.stringify(attempt.source)!==JSON.stringify(view) || JSON.stringify(attempt.authority)!==JSON.stringify(authority)) mismatch();
}

export function assertCompletionReconciliation(attempt:FrozenRunCompletion, view:PlayerSessionView, authority:CompletionAuthorities):void {
  assertCompletionAuthorities(view,authority);
  if (JSON.stringify(attempt.source)!==JSON.stringify(view) || authority.journey.run_id!==attempt.runId ||
      !sameAssociation(authority.journey.path,attempt.authority.journey.path) ||
      !sameAssociation(authority.journey.current,attempt.authority.journey.current) ||
      JSON.stringify(authority.journey.run_context)!==JSON.stringify(attempt.authority.journey.run_context)) mismatch();
  if (authority.journey.lifecycle_status==="active") assertCompletionSubmission(attempt,view,authority);
  else if (authority.journey.lifecycle_status!=="completed") mismatch();
}

export function assertCompletionResult(attempt:FrozenRunCompletion, result:NativeRunCompletionResult):void {
  nativeRunCompletionResultSchema.parse(result);
  assertNativeView(attempt.source,result.run_context);
  if (result.run_id!==attempt.runId || result.source_session_id!==attempt.sessionId ||
      result.source_session_state_version!==attempt.source.metadata.state_version ||
      !sameVisit(result.visit,attempt.authority.journey.current.visit)) mismatch();
}

export function assertConfirmedCompletion(confirmed:{attempt:FrozenRunCompletion;result:NativeRunCompletionResult},
    view:PlayerSessionView, authority:CompletionAuthorities):void {
  assertCompletionResult(confirmed.attempt,confirmed.result);
  assertCompletionAuthorities(view,authority);
  if (authority.journey.lifecycle_status!=="completed" || authority.journey.run_id!==confirmed.result.run_id ||
      !sameAssociation(authority.journey.current,confirmed.attempt.authority.journey.current) ||
      JSON.stringify(authority.completion.completion)!==JSON.stringify(confirmed.result.completion)) mismatch();
}

export function assertCompletionHistory(confirmed:{attempt:FrozenRunCompletion;result:NativeRunCompletionResult}, journey:NativeRunJourney):void {
  assertCompletionResult(confirmed.attempt,confirmed.result);
  nativeRunJourneySchema.parse(journey);
  if(journey.schema_version!=="native-run-journey/v2" || journey.run_id!==confirmed.result.run_id ||
      !sameAssociation(journey.current,confirmed.attempt.authority.journey.current) ||
      JSON.stringify(journey.run_context)!==JSON.stringify(confirmed.result.run_context) ||
      JSON.stringify(journey.completion)!==JSON.stringify(confirmed.result.completion)) mismatch();
}

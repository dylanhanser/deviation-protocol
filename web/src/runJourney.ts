import { ApiClientError } from "./api/errors";
import { assertNativeView } from "./runSetup";
import { idempotencyKeySchema, nativeRunExitRequestSchema, nativeRunJourneySchema,
  nativeRunContinuationResultSchema, nativeRunRevisitResultSchema,
  type NativeRunJourney, type NativeJourneyAssociation, type NativeTransitionResult,
  type PlayerSessionView } from "./api/schemas";
import { assertRunStatus, type FrozenRunExit } from "./runExit";
import type { NativeRunStatus } from "./api/schemas";

function mismatch(): never {
  throw new ApiClientError("Journey authority does not match the loaded View", {kind:"invalid-response", reason:"CONTRACT_MISMATCH"});
}
export function sameVisit(a: NativeJourneyAssociation["visit"], b: NativeJourneyAssociation["visit"]): boolean {
  return a === null || b === null ? a === b : Object.keys(a).every(k => a[k as keyof typeof a] === b[k as keyof typeof b]);
}
export function sameAssociation(a: NativeJourneyAssociation, b: NativeJourneyAssociation): boolean {
  return a.session_id === b.session_id && a.session_state_version === b.session_state_version &&
    a.scenario_id === b.scenario_id && a.scenario_content_version === b.scenario_content_version && sameVisit(a.visit,b.visit);
}
export function assertJourney(view: PlayerSessionView, journey: NativeRunJourney): void {
  nativeRunJourneySchema.parse(journey);
  assertNativeView(view,journey.run_context);
  const path=journey.path;
  if (view.metadata.session_id !== path.session_id || view.metadata.state_version !== path.session_state_version ||
      view.narrative_frame.scenario_id !== path.scenario_id || view.metadata.content_version !== path.scenario_content_version ||
      (path.session_id !== journey.current.session_id && view.scenario_status !== "ENDED") ||
      ((journey.next_transition !== null || journey.lifecycle_status !== "active") && view.scenario_status !== "ENDED")) mismatch();
}
export function assertJourneyRunStatus(view: PlayerSessionView, journey: NativeRunJourney, status: NativeRunStatus): void {
  assertJourney(view,journey);
  assertRunStatus(view,status);
  // Each schema admits multiple historical families. Compare the complete
  // shared association, not a revision number interpreted without its family.
  if (journey.session_id !== status.session_id || journey.run_id !== status.run_id ||
      journey.path.session_state_version !== status.session_state_version ||
      journey.run_state_version !== status.run_state_version || journey.lifecycle_status !== status.lifecycle_status ||
      (status.can_exit && (view.scenario_status !== "ENDED" || journey.path.session_id !== journey.current.session_id))) mismatch();
}
export function assertTransitionResult(source: PlayerSessionView, result: NativeTransitionResult): void {
  (result.schema_version === "native-run-revisit-result/v1" ? nativeRunRevisitResultSchema : nativeRunContinuationResultSchema).parse(result);
  assertNativeView(source,result.run_context);
  if (source.metadata.session_id !== result.source_session_id || source.metadata.state_version !== result.source_session_state_version ||
      source.scenario_status !== "ENDED" || source.narrative_frame.scenario_id !==
      (result.visit.visit_ordinal === 3 ? "undelivered_receipt" : "death_certificate")) mismatch();
}
export interface ConfirmedTransition {
  source: PlayerSessionView;
  sourceAssociation: NativeJourneyAssociation;
  result: NativeTransitionResult;
}
export function assertConfirmedCurrent(confirmed: ConfirmedTransition, journey: NativeRunJourney): void {
  const {source,sourceAssociation,result}=confirmed;
  assertTransitionResult(source,result);
  nativeRunJourneySchema.parse(journey);
  const target=[journey.path,journey.current,journey.predecessor,journey.successor].find(
    association=>association?.visit?.visit_ordinal===result.visit.visit_ordinal);
  if (!target) mismatch();
  const count=journey.current.visit?.visit_ordinal;
  if (count!==result.visit.visit_ordinal && !(result.visit.visit_ordinal===2 && count===3)) mismatch();
  if (journey.run_id !== result.run_id || JSON.stringify(journey.run_context) !== JSON.stringify(result.run_context) ||
      target.session_id !== result.session_id || target.scenario_id !== result.scenario_id ||
      target.scenario_content_version !== result.scenario_content_version || !sameVisit(target.visit,result.visit) ||
      target.session_state_version < result.initial_session_state_version || journey.run_state_version < result.resulting_run_state_version) mismatch();
  // The first continuation materializes the formerly unmaterialized source visit.
  if (journey.path.session_id === result.source_session_id && !sameAssociation(journey.path,
      sourceAssociation.visit === null && result.visit.visit_ordinal === 2
        ? {...sourceAssociation,visit:journey.path.visit} : sourceAssociation)) mismatch();
}
export function assertConfirmedDestination(confirmed: ConfirmedTransition, view: PlayerSessionView, journey: NativeRunJourney): void {
  const {source,sourceAssociation,result}=confirmed;
  assertTransitionResult(source,result);
  assertConfirmedCurrent(confirmed,journey);
  assertJourney(view,journey);
  assertNativeView(view,result.run_context);
  if (view.metadata.session_id !== result.session_id || journey.path.scenario_id !== result.scenario_id ||
      journey.path.scenario_content_version !== result.scenario_content_version || !sameVisit(journey.path.visit,result.visit) ||
      !journey.predecessor || !sameAssociation(journey.predecessor,
        sourceAssociation.visit === null && result.visit.visit_ordinal === 2
          ? {...sourceAssociation,visit:journey.predecessor.visit} : sourceAssociation) ||
      journey.run_state_version < result.resulting_run_state_version || view.metadata.state_version < result.initial_session_state_version) mismatch();
}
export type FrozenJourneyTransition = FrozenRunExit & {
  readonly kind: "first_continuation" | "regional_revisit";
  readonly source: PlayerSessionView;
  readonly authority: NativeRunJourney;
};
export function freezeJourneyTransition(view: PlayerSessionView, journey: NativeRunJourney, key: string): FrozenJourneyTransition {
  assertJourney(view,journey);
  if (journey.lifecycle_status !== "active" || !journey.next_transition || view.scenario_status !== "ENDED") mismatch();
  const kind=journey.next_transition.kind;
  const frozen={url:`v1/sessions/${encodeURIComponent(journey.session_id)}/${kind === "regional_revisit" ? "run-revisit" : "run-continuation"}`,
    sessionId:journey.session_id,runId:journey.run_id,key:idempotencyKeySchema.parse(key),kind,
    serializedBody:JSON.stringify(nativeRunExitRequestSchema.parse({expected_run_state_version:journey.run_state_version,
      expected_session_state_version:journey.path.session_state_version})), source:structuredClone(view),authority:structuredClone(journey)};
  function freeze(value: object) {Object.freeze(value);for (const child of Object.values(value)) if (child && typeof child === "object") freeze(child);}
  freeze(frozen);
  return frozen;
}
export function assertNeighbor(from: NativeRunJourney, to: NativeRunJourney): void {
  nativeRunJourneySchema.parse(from);nativeRunJourneySchema.parse(to);
  const expected=from.predecessor?.session_id === to.session_id ? from.predecessor : from.successor;
  const reciprocal=to.predecessor?.session_id === from.session_id ? to.predecessor : to.successor;
  if (!expected || !reciprocal || !sameAssociation(expected,to.path) || !sameAssociation(reciprocal,from.path) ||
      !sameAssociation(from.current,to.current) || from.run_state_version !== to.run_state_version ||
      from.lifecycle_status !== to.lifecycle_status ||
      (from.schema_version === "native-run-journey/v2" && (to.schema_version !== "native-run-journey/v2" ||
        JSON.stringify(from.completion) !== JSON.stringify(to.completion))) || JSON.stringify(from.run_context) !== JSON.stringify(to.run_context)) mismatch();
}

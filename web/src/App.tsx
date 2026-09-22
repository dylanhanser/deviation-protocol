import { useOpeningPreparation } from "./useOpeningPreparation";
import { useOpeningRecovery } from "./useOpeningRecovery";
import { clearOpeningRecovery, readOpeningRecovery, writeOpeningRecovery, assertOpeningReference } from "./openingRecovery";
import { OpeningTalentChoices, ConfirmedOpeningTalents } from "./OpeningTalents";
import type { OpeningPreparation } from "./api/schemas";
import { SessionReading } from "./SessionReading";
import { JourneyRecap } from "./JourneyRecap";
import { assertCompletionHistory, assertCompletionAuthorities, assertCompletionSubmission, assertCompletionReconciliation, assertConfirmedCompletion, freezeRunCompletion, type FrozenRunCompletion } from "./runCompletion";
import type { NativeRunCompletionStatus, NativeRunCompletionResult } from "./api/schemas";
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent } from "react";

import { publicApiClient, type PublicApiClient } from "./api/client";
import { assertRunStatus, freezeRunExit, type FrozenRunExit } from "./runExit";
import { assertJourney as assertContinuationStatus, assertTransitionResult as assertContinuationResult, assertConfirmedCurrent, assertConfirmedDestination as assertConfirmedSuccessor, assertNeighbor, assertJourneyRunStatus, sameAssociation, freezeJourneyTransition as freezeRunContinuation, type ConfirmedTransition as ConfirmedContinuation, type FrozenJourneyTransition as FrozenRunContinuation } from "./runJourney";
import type { NativeRunJourney as NativeRunContinuationStatus, NativeTransitionResult as NativeRunContinuationResult } from "./api/schemas";
import type { NativeRunStatus } from "./api/schemas";
import { ApiClientError, formatApiClientError } from "./api/errors";
import { assertNativeResponse, assertNativeView, nativeFailureIsUncertain, objectiveLabels, proposedPresentation, type FrozenNativeEntry } from "./runSetup";
import { objectiveNames, type RunEntryOptions, type NativeRunEntryResponse, type PublicNativeRunContext } from "./api/schemas";
import {
  actionRequestSchema,
  createSessionRequestSchema,
  type CreateSessionRequest,
  type SessionCreationResult,
  singleLineActionTextSchema,
  idempotencyKeySchema,
  minimalPlayerCharacterCreationRequestSchema,
  runEntryRequestSchema,
  sessionPathIdSchema,
  type ActionResponse,
  type ActionRequest,
  type MinimalPlayerCharacterCreationRequest,
  type PlayerSessionView,
  type PlayerCharacterSelfProjection,
  type PublicActionAffordance,
  type PublicPlayableActionType,
  type PublicSuggestedAction,
  type PublicScenarioDescription,
  type RunEntryRequest,
} from "./api/schemas";
import {
  clearSessionRecoveryRecord,
  readSessionRecoveryRecord,
  writeSessionRecoveryRecord,
  type SessionRecoveryRecord,
  type SessionRecoveryStorageFailure,
} from "./sessionRecovery";

interface ActionIdentity {
  turnId: string;
  clientRequestId: string;
}

type PollWait = (milliseconds: number, signal: AbortSignal) => Promise<void>;

interface AppProps {
  client?: PublicApiClient;
  idempotencyKeyFactory?: () => string;
  actionIdentityFactory?: () => ActionIdentity;
  pollWait?: PollWait;
}

interface DiscoveryError {
  message: string;
  retryable: boolean;
}

interface MutationAttemptBase {
  generation: number;
  idempotencyKey: string;
  uncertaintyTainted: boolean;
  inFlight: boolean;
}

interface PlayerCharacterCreateAttempt extends MutationAttemptBase {
  kind: "player-character-create";
  exactFrozenBody: Readonly<MinimalPlayerCharacterCreationRequest>;
}

interface RunEntryAttempt extends MutationAttemptBase {
  kind: "run-entry";
  exactFrozenBody: Readonly<RunEntryRequest>;
  entrySuccessAwaitingStorage: boolean;
}

interface NativeEntryAttempt extends MutationAttemptBase {
  kind: "native-entry";
  frozen: FrozenNativeEntry;
  opening?: {record:OpeningPreparation;selected:readonly string[]};
  retainedResponse?: NativeRunEntryResponse;
}
interface SessionCreateAttempt extends MutationAttemptBase {
  kind: "session-create";
  exactFrozenBody: Readonly<CreateSessionRequest>;
  contentVersion: string;
  retainedResponse?: SessionCreationResult;
}
type MutationAttempt = PlayerCharacterCreateAttempt | RunEntryAttempt | NativeEntryAttempt | SessionCreateAttempt;

type ViewStaleKind =
  | "transport-uncertain"
  | "pending-status-unknown"
  | "outcome-unknown"
  | "request-failed"
  | "confirmed-view-unavailable";

interface ViewStaleState {
  kind: ViewStaleKind;
  message: string;
}

interface LoadedSession {
  sessionId: string;
  view: PlayerSessionView;
  stale: ViewStaleState | null;
}

interface NativeViewAssociation {
  sessionId: string;
  context: PublicNativeRunContext;
  scenarioId: string;
  contentVersion: string;
}

function assertViewAssociation(
  sessionId: string,
  view: PlayerSessionView,
  expected: NativeViewAssociation | null,
): void {
  if (view.metadata.session_id !== sessionId) {
    throw new ApiClientError("View Session association changed", {kind:"invalid-response", reason:"CONTRACT_MISMATCH"});
  }
  if (expected === null) return;
  assertNativeView(view, expected.context);
  if (sessionId !== expected.sessionId || view.narrative_frame.scenario_id !== expected.scenarioId ||
      view.metadata.content_version !== expected.contentVersion) {
    throw new ApiClientError("Native View association changed", {kind:"invalid-response", reason:"CONTRACT_MISMATCH"});
  }
}

interface DynamicNarrativeActionEvidence {
  revision: number;
  newStorySegments: number;
  suggestions: number;
  publicFactCount: number;
}

interface ForegroundOperation {
  controller: AbortController;
  id: number;
}

interface RecoveryInterruption {
  message: string;
}

interface RecoveryStorageFailureState {
  failure: SessionRecoveryStorageFailure;
}

type ForegroundOperationKind =
  | "creating"
  | "entering"
  | "reading"
  | "recovering"
  | "submitting"
  | "pending"
  | "refreshing";

type DescriptionActionType = Exclude<
  PublicPlayableActionType,
  "CONTINUE" | "TALK"
>;

type ActionIntent =
  | { action_type: "CONTINUE" }
  | { action_type: "CHOOSE"; decision_id: string; choice_id: string }
  | { action_type: "TALK"; dialogue: string; target_ids?: string[] }
  | {
      action_type: DescriptionActionType;
      description: string;
      target_ids?: string[];
    };

const TRANSPORT_UNCERTAIN_MESSAGE =
  "行动响应无法确认；该行动可能已经到达服务器。请勿重新提交。当前 View 可能已过期，必须显式重新读取权威 View。刷新 View 不是行动重放，也不能保证证明未知行动的最终结果。";
const PENDING_STATUS_UNKNOWN_MESSAGE =
  "行动已被服务器受理，但客户端无法确认其最终 request status。不会重新提交行动；当前 View 可能已过期，请显式重新读取权威 View。";
const OUTCOME_UNKNOWN_MESSAGE =
  "服务器报告 OUTCOME_UNKNOWN。客户端不会重新提交行动；当前 View 已冻结为可能过期。显式刷新 View 不是行动重放，也不能保证证明该行动的最终结果。";
const REQUEST_FAILED_MESSAGE =
  "服务器报告 FAILED，并指示 DO_NOT_RETRY。客户端不会重新提交行动；请显式重新读取权威 View 后再继续。";
const CONFIRMED_VIEW_UNAVAILABLE_MESSAGE =
  "行动已获服务器确认，但新的完整 PlayerSessionView 获取失败。保留的 View 已标记为 stale，不能继续行动；显式刷新只会重新读取 View，不会重放行动。";
const RECOVERY_INTERRUPTED_MESSAGE =
  "自动恢复已停止，行动保持锁定。只能手动重试安全 GET；客户端不会 POST、重放行动或生成新的 request ID。";
const RECOVERY_NOT_FOUND_MESSAGE =
  "恢复记录在服务器返回 404 后失效；读取已暂停。请显式清除此标签页进度后重新选择。";
const RECOVERY_IDENTITY_MISMATCH_MESSAGE =
  "服务器返回的恢复身份与已保存记录不匹配，读取已暂停。可重试 GET 或显式清除此标签页进度。";
const RECOVERY_STORAGE_FAILURE_MESSAGE =
  "本标签页 sessionStorage 无法安全访问或更新。Session、View 与行动控件已锁定；客户端不会 POST、重放行动或生成新的恢复身份。";
const DETERMINISTIC_DEMO_WARNING =
  "Deterministic Demo  local only  temporary data  not a production Provider";
const MUTATION_UNCERTAIN_MESSAGE =
  "服务器是否已持久化本次操作仍不确定。客户端不会自动重试；只能用完全相同的请求内容手动重试。";
const RUN_DISCOVERY_LIMIT_MESSAGE =
  "如果 Run 已在服务器提交但 Session ID 尚未保存，此 Web 客户端无法发现或恢复该 Run。";
const DOCUMENTED_MUTATION_ERRORS: Readonly<
  Record<string, { status: number; message: string }>
> = {
  PLAYER_CHARACTER_NOT_FOUND: {
    status: 404,
    message: "Player character was not found",
  },
  IDEMPOTENCY_CONFLICT: {
    status: 409,
    message: "Idempotency key was reused",
  },
  PLAYER_CHARACTER_STALE: {
    status: 409,
    message: "Player character revision is stale",
  },
  PLAYER_CHARACTER_NOT_ELIGIBLE: {
    status: 409,
    message: "Player character is not eligible for Run entry",
  },
  RUN_ENTRY_CONFLICT: {
    status: 409,
    message: "Run entry conflicts with current state",
  },
  REQUEST_VALIDATION_FAILED: {
    status: 422,
    message: "Request validation failed",
  },
  INVALID_SCENARIO_DEFINITION: {
    status: 422,
    message: "Scenario definition is not available",
  },
};

function dynamicNarrativeActionEvidence(
  response: ActionResponse | null,
  loaded: LoadedSession,
): DynamicNarrativeActionEvidence | null {
  if (
    response === null ||
    response.session_id !== loaded.sessionId ||
    response.session_id !== loaded.view.metadata.session_id ||
    response.resulting_state_version !== loaded.view.metadata.state_version ||
    response.resolution_kind !== "NARRATIVE_COMMITTED" ||
    response.result_code !== "DYNAMIC_NARRATIVE_COMMITTED" ||
    response.feedback_code !== "DYNAMIC_NARRATIVE_COMMITTED" ||
    !response.state_changed ||
    !response.narrative_required ||
    response.narrative_pending ||
    response.narrative_status !== "COMMITTED" ||
    response.narrative_text === null
  ) {
    return null;
  }
  const publicFactCount = response.feedback_parameters["public_fact_count"];
  if (
    typeof publicFactCount !== "number" ||
    !Number.isFinite(publicFactCount) ||
    !Number.isInteger(publicFactCount) ||
    publicFactCount < 0 ||
    publicFactCount > 3
  ) {
    return null;
  }
  return {
    revision: response.resulting_state_version,
    newStorySegments: 1,
    suggestions: loaded.view.action_affordances.suggested_actions?.length ?? 0,
    publicFactCount,
  };
}

function DynamicNarrativeEvidenceSummary({
  response,
  loaded,
}: {
  response: ActionResponse | null;
  loaded: LoadedSession;
}) {
  const evidence = dynamicNarrativeActionEvidence(response, loaded);
  if (evidence === null) {
    return null;
  }
  return (
    <section className="panel" aria-labelledby="dynamic-narrative-evidence-heading">
      <h2 id="dynamic-narrative-evidence-heading">Dynamic Narrative action evidence</h2>
      <p>REVISION={evidence.revision}</p>
      <p>NEW_STORY_SEGMENTS={evidence.newStorySegments}</p>
      <p>SUGGESTIONS={evidence.suggestions}</p>
      <p>NEW_PUBLIC_FACTS={evidence.publicFactCount}</p>
    </section>
  );
}

function newOpaqueId(): string {
  return globalThis.crypto.randomUUID();
}

function newActionIdentity(): ActionIdentity {
  return {
    turnId: newOpaqueId(),
    clientRequestId: newOpaqueId(),
  };
}

function waitForPollingDelay(
  milliseconds: number,
  signal: AbortSignal,
): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Polling was aborted", "AbortError"));
      return;
    }
    const onAbort = () => {
      globalThis.clearTimeout(timeoutId);
      reject(new DOMException("Polling was aborted", "AbortError"));
    };
    const timeoutId = globalThis.setTimeout(() => {
      signal.removeEventListener("abort", onAbort);
      resolve();
    }, milliseconds);
    signal.addEventListener("abort", onAbort, { once: true });
  });
}

function isTransportUncertain(error: unknown): boolean {
  return (
    error instanceof ApiClientError &&
    ["network", "aborted", "invalid-response"].includes(error.kind)
  );
}

function discoveryErrorFor(error: unknown): DiscoveryError {
  return {
    message: formatApiClientError(error),
    retryable:
      error instanceof ApiClientError &&
      (error.kind === "network" || error.kind === "api"),
  };
}

function isDescriptionActionType(
  actionType: PublicPlayableActionType,
): actionType is DescriptionActionType {
  return ["CUSTOM", "EXPLORE", "OBSERVE", "MOVE"].includes(actionType);
}

function FreeActionForm({
  affordance,
  disabled,
  onSubmit,
}: {
  affordance: PublicActionAffordance;
  disabled: boolean;
  onSubmit: (intent: ActionIntent) => void;
}) {
  const [text, setText] = useState("");
  const [targetId, setTargetId] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const fieldPrefix = `action-${affordance.action_type.toLowerCase()}`;
  const normalizedCandidateText = text.trim();
  const inputLength = Array.from(normalizedCandidateText).length;
  const inputTooLong =
    affordance.max_input_length !== null &&
    affordance.max_input_length !== undefined &&
    inputLength > affordance.max_input_length;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled) {
      return;
    }
    if (affordance.input_kind !== "NONE") {
      const singleLine = singleLineActionTextSchema.safeParse(text);
      if (!singleLine.success) {
        setValidationError(formatApiClientError(singleLine.error));
        return;
      }
    }
    const targetIsAllowed =
      targetId === "" ||
      affordance.targets.some((target) => target.target_id === targetId);
    if (!targetIsAllowed || (affordance.target_required && targetId === "")) {
      setValidationError("请选择当前 View 为此行动提供的目标。");
      return;
    }
    const target = targetId === "" ? {} : { target_ids: [targetId] };
    if (affordance.action_type === "CONTINUE") {
      setValidationError(null);
      onSubmit({ action_type: "CONTINUE" });
      return;
    }
    if (affordance.action_type === "TALK") {
      if (normalizedCandidateText === "") {
        setValidationError("请输入要说的话。");
        return;
      }
      setValidationError(null);
      onSubmit({
        action_type: "TALK",
        dialogue: normalizedCandidateText,
        ...target,
      });
      return;
    }
    if (isDescriptionActionType(affordance.action_type)) {
      if (normalizedCandidateText === "") {
        setValidationError("请输入行动描述。");
        return;
      }
      setValidationError(null);
      onSubmit({
        action_type: affordance.action_type,
        description: normalizedCandidateText,
        ...target,
      });
    }
  }

  const inputLabel =
    affordance.input_kind === "DIALOGUE" ? "对话内容" : "行动描述";

  return (
    <form className="action-form" onSubmit={handleSubmit}>
      <fieldset disabled={disabled}>
        <legend>
          {affordance.label} <span>({affordance.action_type})</span>
        </legend>

        {affordance.action_type !== "CONTINUE" &&
        affordance.targets.length > 0 ? (
          <>
            <label htmlFor={`${fieldPrefix}-target`}>
              目标{affordance.target_required ? "（必选）" : "（可选）"}
            </label>
            <select
              id={`${fieldPrefix}-target`}
              value={targetId}
              onChange={(event) => setTargetId(event.target.value)}
              required={affordance.target_required}
            >
              <option value="">不指定目标</option>
              {affordance.targets.map((target) => (
                <option key={target.target_id} value={target.target_id}>
                  {target.display_name}
                </option>
              ))}
            </select>
          </>
        ) : null}

        {affordance.input_kind !== "NONE" ? (
          <>
            <label htmlFor={`${fieldPrefix}-text`}>{inputLabel}</label>
            <textarea
              id={`${fieldPrefix}-text`}
              value={text}
              onChange={(event) => {
                setText(event.target.value);
                setValidationError(null);
              }}
              aria-describedby={`${fieldPrefix}-limit${validationError === null ? "" : ` ${fieldPrefix}-error`}`}
              aria-invalid={inputTooLong || validationError !== null}
              required
              rows={3}
            />
            <p
              id={`${fieldPrefix}-limit`}
              className="input-limit"
              role={inputTooLong ? "alert" : undefined}
            >
              {inputLength} / {affordance.max_input_length}
              {inputTooLong ? "：已超过公开合同上限" : ""}
            </p>
          </>
        ) : (
          <p className="supporting-copy">此行动不发送额外 payload。</p>
        )}

        {validationError === null ? null : (
          <p id={`${fieldPrefix}-error`} role="alert">{validationError}</p>
        )}
        <button
          type="submit"
          disabled={
            disabled ||
            inputTooLong ||
            (affordance.input_kind !== "NONE" &&
              normalizedCandidateText === "")
          }
        >
          提交{affordance.label}
        </button>
      </fieldset>
    </form>
  );
}

function ActionPanel({
  view,
  disabled,
  disabledReason,
  onSubmit,
  onSubmitSuggestion,
}: {
  view: PlayerSessionView;
  disabled: boolean;
  disabledReason: string | null;
  onSubmit: (intent: ActionIntent) => void;
  onSubmitSuggestion: (suggestion: PublicSuggestedAction) => void;
}) {
  const affordances = view.action_affordances;
  if (affordances.mode === "ENDED") {
    return null;
  }

  return (
    <section className="panel action-panel" aria-labelledby="actions-heading">
      {view.encounter || view.relationship ? null : <p className="eyebrow">action_affordances · {affordances.mode}</p>}
      <h2 id="actions-heading">当前可执行行动</h2>
      <p className="supporting-copy">
        {view.relationship ? "选择接下来在哨站的行动。只有明确提交选择才会推进这段行程。" : view.encounter ? "选择接下来如何带同行者一起行动。" : "这里只提交当前权威 View 明确提供的行动；服务器 Gateway 与策略仍是最终权威。"}
      </p>
      {disabledReason === null ? null : (
        <p className="disabled-reason">行动已禁用：{disabledReason}</p>
      )}

      {affordances.suggested_actions === undefined ? null : (
        <div className="dynamic-suggestions" role="group" aria-label="动态建议行动">
          <h3>动态建议行动</h3>
          {affordances.suggested_actions.map((suggestion) => (
            <button
              key={suggestion.suggestion_id}
              type="button"
              disabled={disabled}
              onClick={() => onSubmitSuggestion(suggestion)}
            >
              {suggestion.label}
            </button>
          ))}
        </div>
      )}

      {affordances.mode === "DECISION" ? (
        <div
          className="decision-choices"
          role="group"
          aria-labelledby="decision-heading"
        >
          <h3 id="decision-heading">请选择一个公开决策选项</h3>
          {affordances.choices.map((choice) => (
            <button
              key={choice.choice_id}
              type="button"
              disabled={disabled}
              onClick={() => {
                if (affordances.decision_id !== null &&
                    affordances.decision_id !== undefined) {
                  onSubmit({
                    action_type: "CHOOSE",
                    decision_id: affordances.decision_id,
                    choice_id: choice.choice_id,
                  });
                }
              }}
            >
              {choice.label}
            </button>
          ))}
        </div>
      ) : affordances.actions.length === 0 ? (
        <p>当前 View 没有可提交的公开行动。</p>
      ) : (
        <div className="action-list">
          {affordances.actions.map((affordance) => (
            <FreeActionForm
              key={`${view.metadata.state_version}-${affordance.action_type}`}
              affordance={affordance}
              disabled={disabled}
              onSubmit={onSubmit}
            />
          ))}
        </div>
      )}
    </section>
  );
}

export default function App({
  client = publicApiClient,
  idempotencyKeyFactory = newOpaqueId,
  actionIdentityFactory = newActionIdentity,
  pollWait = waitForPollingDelay,
}: AppProps) {
  const [entryMode, setEntryMode] = useState<"native" | "legacy" | null>(null);
  const entryModeRef = useRef(entryMode);
  useLayoutEffect(() => {
    entryModeRef.current = entryMode;
  }, [entryMode]);
  const [runOptions, setRunOptions] = useState<RunEntryOptions | null>(null);
  const [optionsError, setOptionsError] = useState<string | null>(null);
  const [optionsRefresh, setOptionsRefresh] = useState(0);
  const [profileId, setProfileId] = useState("");
  const [worldId, setWorldId] = useState("");
  const [overrides, setOverrides] = useState<Record<string,string>>({});
  const [runPresentation, setRunPresentation] = useState({...proposedPresentation});
  const previousCatalogue = useRef<RunEntryOptions | null>(null);
  const choices = useRef({profileId,worldId,overrides});
  const nativeExpected = useRef<NativeViewAssociation | null>(null);
  const confirmedContinuation = useRef<ConfirmedContinuation | null>(null);
  const confirmedCompletion=useRef<{attempt:FrozenRunCompletion;result:NativeRunCompletionResult}|null>(null);
  const confirmedExit=useRef<NativeRunStatus|null>(null);
  const [completionProof,setCompletionProof]=useState<{attempt:FrozenRunCompletion;result:NativeRunCompletionResult}|null>(null);
  const [exitProof,setExitProof]=useState<NativeRunStatus|null>(null);
  const [completionOwner,setCompletionOwner]=useState<PublicApiClient|null>(null);
  const [exitOwner,setExitOwner]=useState<PublicApiClient|null>(null);
  const completionAttemptRef=useRef<FrozenRunCompletion|null>(null);
  const completionClientRef=useRef<PublicApiClient|null>(null);
  const completionRetryBlockedRef=useRef(false);
  const [completionRetryBlocked,setCompletionRetryBlocked]=useState(false);
  const blockCompletionRetry=useCallback((blocked:boolean)=>{
    completionRetryBlockedRef.current=blocked;setCompletionRetryBlocked(blocked);
  },[]);
  const exitConfirmationRef=useRef<{view:PlayerSessionView;authority:object;client:PublicApiClient}|null>(null);
  const continuationConfirmationRef=useRef<{view:PlayerSessionView;authority:object;client:PublicApiClient}|null>(null);
  const validateSuccessorRead = useCallback(async(view: PlayerSessionView, signal: AbortSignal) => {
    const confirmed=confirmedContinuation.current;
    if (!view.run_context) return;
    const status=await client.getNativeRunJourney(view.metadata.session_id,signal);
    assertContinuationStatus(view,status);
    if (confirmed) assertConfirmedSuccessor(confirmed,view,status);
    if (view.scenario_status==="ENDED") {
      const [runStatus,completion]=await Promise.all([client.getNativeRunStatus(view.metadata.session_id,signal),
        client.getNativeRunCompletion(view.metadata.session_id,signal)]);
      const authority={journey:status,status:runStatus,completion};
      assertCompletionAuthorities(view,authority);
      if(completionAttemptRef.current) assertCompletionReconciliation(completionAttemptRef.current,view,authority);
      if(confirmedCompletion.current) assertConfirmedCompletion(confirmedCompletion.current,view,authority);
      if(confirmedExit.current && JSON.stringify(confirmedExit.current)!==JSON.stringify(runStatus))
        throw new ApiClientError("Confirmed exit association mismatch",{kind:"invalid-response",reason:"CONTRACT_MISMATCH"});
    }
    return status;
  },[client]);
  const latestClient = useRef(client);
  useLayoutEffect(() => {
    choices.current = {profileId,worldId,overrides};
    latestClient.current = client;
  }, [client,profileId,worldId,overrides]);
  const selectedProfile = runOptions?.profiles.find((p) => p.profile_ref.profile_id === profileId);
  const selectedWorld = runOptions?.entry_worlds.find((w) => w.entry_world.entry_world_id === worldId);
  const [scenarios, setScenarios] = useState<PublicScenarioDescription[] | null>(
    null,
  );
  const [scenarioError, setScenarioError] = useState<DiscoveryError | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState("");
  const [scenarioRefreshAttempt, setScenarioRefreshAttempt] = useState(0);
  const [eligibleCharacters, setEligibleCharacters] = useState<
    PlayerCharacterSelfProjection[] | null
  >(null);
  const [eligibleTruncated, setEligibleTruncated] = useState(false);
  const [eligibleError, setEligibleError] = useState<DiscoveryError | null>(null);
  const [selectedPlayerCharacterId, setSelectedPlayerCharacterId] = useState("");
  const [createdPlayerCharacter, setCreatedPlayerCharacter] =
    useState<PlayerCharacterSelfProjection | null>(null);
  const [eligibleRefreshAttempt, setEligibleRefreshAttempt] = useState(0);
  const [mutationAttempt, setMutationAttempt] =
    useState<MutationAttempt | null>(null);
  const [requiredCatalogRefresh, setRequiredCatalogRefresh] = useState<
    "eligible" | "scenario" | null
  >(null);
  const [initialRecoveryRead] = useState(() => readSessionRecoveryRecord());
  const initialRecoveryRecord = initialRecoveryRead.ok
    ? initialRecoveryRead.value
    : null;
  const [recoveryRecord, setRecoveryRecord] =
    useState<SessionRecoveryRecord | null>(initialRecoveryRecord);
  const [foregroundOperation, setForegroundOperation] =
    useState<ForegroundOperationKind | null>(
      initialRecoveryRecord === null ? null : "recovering",
    );
  const [manualSessionId, setManualSessionId] = useState("");
  const [loadedSession, setLoadedSession] = useState<LoadedSession | null>(null);
  const [restoredReading, setRestoredReading] = useState<{
    owner: LoadedSession; client: PublicApiClient; journey: NativeRunContinuationStatus;
  } | null>(null);
  const [runAuthority, setRunAuthority] = useState<{
    owner: LoadedSession; client: PublicApiClient;
    journey: NativeRunContinuationStatus; status: NativeRunStatus | null; completion:NativeRunCompletionStatus|null;
  } | null>(null);
  const [runStatus, setRunStatus] = useState<NativeRunStatus | null>(null);
  const [completionStatus,setCompletionStatus]=useState<NativeRunCompletionStatus|null>(null);
  const [completionConfirm,setCompletionConfirm]=useState<FrozenRunCompletion|null>(null);
  const [completionAttempt,setCompletionAttempt]=useState<FrozenRunCompletion|null>(null);
  const [completionError,setCompletionError]=useState<string|null>(null);
  const [exitConfirm, setExitConfirm] = useState(false);
  const [exitAttempt, setExitAttempt] = useState<FrozenRunExit | null>(null);
  const exitAttemptRef = useRef<FrozenRunExit | null>(null);
  const [exitError, setExitError] = useState<string | null>(null);
  const [exitClearFailed, setExitClearFailed] = useState(false);
  const [continuationStatus, setContinuationStatus] = useState<NativeRunContinuationStatus | null>(null);
  const [continuationConfirm, setContinuationConfirm] = useState(false);
  const [continuationAttempt, setContinuationAttempt] = useState<FrozenRunContinuation | null>(null);
  const continuationAttemptRef = useRef<FrozenRunContinuation | null>(null);
  const [continuationError, setContinuationError] = useState<string | null>(null);
  const [historicalSession, setHistoricalSession] = useState<LoadedSession | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historicalJourney, setHistoricalJourney] = useState<NativeRunContinuationStatus | null>(null);
  const [pendingContinuationRecovery, setPendingContinuationRecovery] = useState<NativeRunContinuationResult | null>(null);
  const [committedActionResponse, setCommittedActionResponse] =
    useState<ActionResponse | null>(null);
  const [createdSessionWithoutView, setCreatedSessionWithoutView] = useState<
    string | null
  >(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [recoveryInterruption, setRecoveryInterruption] =
    useState<RecoveryInterruption | null>(null);
  const [recoveryStorageFailure, setRecoveryStorageFailure] =
    useState<RecoveryStorageFailureState | null>(
      initialRecoveryRead.ok
        ? null
        : { failure: initialRecoveryRead.failure },
    );
  const [recoveryAttempt, setRecoveryAttempt] = useState(0);
  const foregroundOperationRef = useRef<ForegroundOperation | null>(null);
  const operationGenerationRef = useRef(0);
  const mutationAttemptRef = useRef<MutationAttempt | null>(null);
  const mutationGenerationRef = useRef(0);
  const loadedSessionRef = useRef<LoadedSession | null>(null);
  const recoveryRecordRef = useRef<SessionRecoveryRecord | null>(
    initialRecoveryRecord,
  );
  const previousClientRef = useRef(client);

  const replaceMutationAttempt = useCallback(
    (next: MutationAttempt | null) => {
      mutationAttemptRef.current = next;
      setMutationAttempt(next);
    },
    [],
  );

  const updateMutationAttempt = useCallback(
    (
      generation: number,
      update: (current: MutationAttempt) => MutationAttempt,
    ): boolean => {
      const current = mutationAttemptRef.current;
      if (current === null || current.generation !== generation) {
        return false;
      }
      replaceMutationAttempt(update(current));
      return true;
    },
    [replaceMutationAttempt],
  );

  const invalidateForegroundOperation = useCallback(() => {
    setRestoredReading(null);
    operationGenerationRef.current += 1;
    const operation = foregroundOperationRef.current;
    operation?.controller.abort();
    foregroundOperationRef.current = null;
    setForegroundOperation(null);
  }, []);

  const clearSessionUiState = useCallback(() => {
    setContinuationStatus(null); setContinuationConfirm(false); setContinuationAttempt(null); continuationAttemptRef.current = null;
    setContinuationError(null); setHistoricalSession(null); setHistoricalJourney(null); setHistoryLoading(false);
    setRunStatus(null); setExitConfirm(false); setExitAttempt(null); exitAttemptRef.current = null;
    setCompletionStatus(null);setCompletionConfirm(null);setCompletionAttempt(null);completionAttemptRef.current=null;
    confirmedCompletion.current=null;confirmedExit.current=null;setCompletionProof(null);setExitProof(null);
    setCompletionOwner(null);setExitOwner(null);setCompletionError(null);completionClientRef.current=null;
    blockCompletionRetry(false);
    setExitError(null); setExitClearFailed(false);
    loadedSessionRef.current = null;
    setLoadedSession(null);
    setCommittedActionResponse(null);
    setCreatedSessionWithoutView(null);
    setManualSessionId("");
    setOperationError(null);
    setRecoveryInterruption(null);
  }, [setManualSessionId, setRunStatus, setExitConfirm, setExitAttempt, setExitError, setExitClearFailed,
    setContinuationStatus, setContinuationConfirm, setContinuationAttempt, setContinuationError, setHistoricalSession,
    setCompletionConfirm,setCompletionStatus,setCompletionAttempt,setCompletionError,setCompletionProof,setExitProof,setCompletionOwner,setExitOwner,blockCompletionRetry]);

  const enterRecoveryStorageFailure = useCallback(
    (failure: SessionRecoveryStorageFailure) => {
      invalidateForegroundOperation();
      recoveryRecordRef.current = null;
      setRecoveryRecord(null);
      clearSessionUiState();
      setRecoveryStorageFailure({ failure });
    },
    [clearSessionUiState, invalidateForegroundOperation],
  );

  const persistRecoveryRecord = useCallback(
    (sessionId: string, confirmedPendingClientRequestId?: string): boolean => {
      const result = writeSessionRecoveryRecord(
        sessionId,
        confirmedPendingClientRequestId,
      );
      if (!result.ok) {
        enterRecoveryStorageFailure(result.failure);
        return false;
      }
      recoveryRecordRef.current = result.value;
      setRecoveryRecord(result.value);
      const cleared=clearOpeningRecovery(client);
      if (!cleared.ok) {enterRecoveryStorageFailure(cleared.failure);return false;}
      return true;
    },
    [client, enterRecoveryStorageFailure],
  );

  const clearRecoveryForSessionTransition = useCallback((nextSessionId?: string): boolean => {
    const result = clearSessionRecoveryRecord();
    if (!result.ok) {
      enterRecoveryStorageFailure(result.failure);
      return false;
    }
    recoveryRecordRef.current = null;
    if (nativeExpected.current?.sessionId !== nextSessionId) {
      nativeExpected.current = null;
      confirmedContinuation.current = null;
    }
    setRecoveryRecord(null);
    loadedSessionRef.current = null;
    setLoadedSession(null);
    setCommittedActionResponse(null);
    setRecoveryStorageFailure(null);
    return true;
  }, [enterRecoveryStorageFailure]);

  const explicitlyAbandonSession = useCallback((): boolean => {
    setPendingContinuationRecovery(null);
    invalidateForegroundOperation();
    const result = clearSessionRecoveryRecord();
    recoveryRecordRef.current = null;
    setRecoveryRecord(null);
    clearSessionUiState();
    nativeExpected.current = null;
    confirmedContinuation.current = null;
    if (!result.ok) {
      setRecoveryStorageFailure({ failure: result.failure });
      return false;
    }
    setRecoveryStorageFailure(null);
    return true;
  }, [clearSessionUiState, invalidateForegroundOperation]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void client.listRunEntryOptions(controller.signal).then((options) => {
      if (!active) return;
      const old = previousCatalogue.current;
      const selected = choices.current;
      const priorProfile = old?.profiles.find((p) => p.profile_ref.profile_id === selected.profileId);
      const profile = options.profiles.find((p) => p.profile_ref.profile_id === priorProfile?.profile_ref.profile_id && p.profile_ref.profile_version === priorProfile.profile_ref.profile_version);
      const priorWorld = old?.entry_worlds.find((w) => w.entry_world.entry_world_id === selected.worldId);
      const world = options.entry_worlds.find((w) => w.entry_world.entry_world_id === priorWorld?.entry_world.entry_world_id && w.entry_world.entry_world_version === priorWorld.entry_world.entry_world_version &&
        w.eligible_profiles.some((p) => p.profile_id === profile?.profile_ref.profile_id && p.profile_version === profile.profile_ref.profile_version));
      setRunOptions(options);
      setOptionsError(null);
      setProfileId(profile?.profile_ref.profile_id ?? ""); setWorldId(world?.entry_world.entry_world_id ?? "");
      setOverrides(Object.fromEntries(Object.entries(selected.overrides).filter(([name,value]) => {
        const r=profile?.override_rules.find((r) => r.parameter === name); const number=Number(value);
        return r && value.trim() !== "" && Number.isSafeInteger(number) && number % 5 === 0 && r.minimum <= number && number <= r.maximum;
      })));
      previousCatalogue.current = options;
    }).catch((error: unknown) => {if (active) setOptionsError(formatApiClientError(error));});
    return () => {active = false; controller.abort();};
  }, [client, optionsRefresh]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void client
      .listScenarios(controller.signal)
      .then((catalog) => {
        if (!active) {
          return;
        }
        setScenarios(catalog.scenarios);
        const firstScenario = catalog.scenarios.find(item => item.entry_mode !== "SESSION");
        setSelectedScenarioId(firstScenario?.scenario_id ?? "");
      })
      .catch((error: unknown) => {
        if (
          !active ||
          (error instanceof ApiClientError && error.kind === "aborted")
        ) {
          return;
        }
        setScenarioError(discoveryErrorFor(error));
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [client, scenarioRefreshAttempt]);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    void client
      .listEligiblePlayerCharacters(controller.signal)
      .then((collection) => {
        if (!active) {
          return;
        }
        setEligibleCharacters(collection.eligible_player_characters);
        setEligibleTruncated(collection.truncated);
        setCreatedPlayerCharacter(null);
        setSelectedPlayerCharacterId((current) => {
          if (entryModeRef.current === "native") {
            return collection.eligible_player_characters.some(
              (character) => character.player_character_id.value === current,
            ) ? current : "";
          }
          return collection.eligible_player_characters[0]?.player_character_id.value ?? "";
        });
      })
      .catch((error: unknown) => {
        if (
          !active ||
          (error instanceof ApiClientError && error.kind === "aborted")
        ) {
          return;
        }
        setEligibleError(discoveryErrorFor(error));
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [client, eligibleRefreshAttempt]);

  useEffect(() => {
    if (previousClientRef.current !== client) {
      setContinuationStatus(null); setContinuationConfirm(false);
      setContinuationError(null); setHistoricalSession(null); setHistoricalJourney(null); setHistoryLoading(false);
      setRunStatus(null); setExitConfirm(false);setCompletionStatus(null);setCompletionConfirm(null);
      setExitError(null); setExitClearFailed(false);
      nativeExpected.current = null;
      previousCatalogue.current = null;
      setRunOptions(null); setProfileId(""); setWorldId(""); setOverrides({}); setEntryMode(null);
      const attempt = mutationAttemptRef.current;
      if (attempt?.inFlight === true) {
        replaceMutationAttempt({
          ...attempt,
          uncertaintyTainted: true,
          inFlight: false,
        });
      }
      invalidateForegroundOperation();
      loadedSessionRef.current = null;
      setLoadedSession(null);
      setCommittedActionResponse(null);
      setCreatedSessionWithoutView(null);
      setOperationError(null);
      setRecoveryInterruption(null);
      setScenarios(null);
      setScenarioError(null);
      setEligibleCharacters(null);
      setEligibleTruncated(false);
      setEligibleError(null);
      setCreatedPlayerCharacter(null);
      setSelectedPlayerCharacterId("");
      previousClientRef.current = client;
    }
  }, [client, invalidateForegroundOperation, replaceMutationAttempt]);

  useEffect(() => {
    return () => {
      operationGenerationRef.current += 1;
      foregroundOperationRef.current?.controller.abort();
      foregroundOperationRef.current = null;
      loadedSessionRef.current = null;
    };
  }, []);

  useEffect(() => {
    const current=loadedSession;
    const previouslyBlocked=completionRetryBlockedRef.current;
    if(completionAttemptRef.current) blockCompletionRetry(true);
    const controller=new AbortController();
    const generation=operationGenerationRef.current;
    let active=true;
    const isCurrent=()=>active && latestClient.current === client && loadedSessionRef.current === current &&
      operationGenerationRef.current === generation;
    const synchronize=async()=>{
      await Promise.resolve();
      if (!isCurrent()) return;
      setRunAuthority(null); setRunStatus(null);
      // Keep already validated arrival/history text while re-reading. The
      // separate owner-bound authority stays invalid until the reads agree.
      setContinuationStatus(previous => previous?.session_id === current?.sessionId &&
        previous?.path.session_state_version === current?.view.metadata.state_version ? previous : null);
      setContinuationConfirm(false); setExitConfirm(false);setCompletionConfirm(null);
      if (!current?.view.run_context || current.stale !== null) return;
      const [journey,status,completion]=await Promise.all([
        client.getNativeRunJourney(current.sessionId,controller.signal),
        current.view.scenario_status === "ENDED" ? client.getNativeRunStatus(current.sessionId,controller.signal) : Promise.resolve(null),
        current.view.scenario_status === "ENDED" ? client.getNativeRunCompletion(current.sessionId,controller.signal) : Promise.resolve(null),
      ]);
      if (!isCurrent()) return;
      assertContinuationStatus(current.view,journey);
      if (confirmedContinuation.current) assertConfirmedCurrent(confirmedContinuation.current,journey);
      if (confirmedContinuation.current?.result.session_id === current.sessionId)
        assertConfirmedSuccessor(confirmedContinuation.current,current.view,journey);
      if (status && completion) {
        assertCompletionAuthorities(current.view,{journey,status,completion});
        if(completionAttemptRef.current) assertCompletionReconciliation(completionAttemptRef.current,current.view,{journey,status,completion});
        if(confirmedCompletion.current) assertConfirmedCompletion(confirmedCompletion.current,current.view,{journey,status,completion});
        if(confirmedExit.current && JSON.stringify(confirmedExit.current)!==JSON.stringify(status))
          throw new ApiClientError("Confirmed exit association mismatch",{kind:"invalid-response",reason:"CONTRACT_MISMATCH"});
      }
      setContinuationStatus(journey); setRunStatus(status);
      setCompletionStatus(completion);
      setRunAuthority({owner:current,client,journey,status,completion});
      blockCompletionRetry(false);
      setContinuationError(null); setExitError(null);

    };
    void synchronize().catch((error:unknown)=>{
      if (!isCurrent()) return;
      setRestoredReading(null);
      setRunAuthority(null);
      blockCompletionRetry(previouslyBlocked || (error instanceof ApiClientError && error.reason==="CONTRACT_MISMATCH"));
      setContinuationError(formatApiClientError(error));
      if (current?.view.scenario_status === "ENDED") setExitError(formatApiClientError(error));
    });
    return ()=>{active=false;controller.abort();};
  },[client,loadedSession,blockCompletionRetry]);

  function hasRunAuthority(current: LoadedSession | null): boolean {
    if (!current || current.stale || !runAuthority || runAuthority.owner !== current || runAuthority.client !== client ||
        runAuthority.journey !== continuationStatus || runAuthority.status !== runStatus || runAuthority.completion !== completionStatus) return false;
    try {
      assertContinuationStatus(current.view,runAuthority.journey);
      if (current.view.scenario_status === "ENDED") {
        if (!runAuthority.status || !runAuthority.completion) return false;
        const authorities={journey:runAuthority.journey,status:runAuthority.status,completion:runAuthority.completion};
        assertCompletionAuthorities(current.view,authorities);
        if(completionAttempt) assertCompletionReconciliation(completionAttempt,current.view,authorities);
        if(completionProof) assertConfirmedCompletion(completionProof,current.view,authorities);
        if(exitProof && JSON.stringify(exitProof)!==JSON.stringify(runAuthority.status)) return false;
      }
      return true;
    } catch {return false;}
  }
  const runAuthorityReady=hasRunAuthority(loadedSession);

  useEffect(() => {
    if (recoveryStorageFailure !== null) {
      return;
    }
    const record = recoveryRecordRef.current;
    if (record === null) {
      return;
    }

    const operation = {
      controller: new AbortController(),
      id: operationGenerationRef.current + 1,
    };
    operationGenerationRef.current = operation.id;
    foregroundOperationRef.current = operation;

    const isCurrent = () =>
      latestClient.current === client &&
      foregroundOperationRef.current?.id === operation.id &&
      !operation.controller.signal.aborted;

    const transition = (kind: ForegroundOperationKind) => {
      if (isCurrent()) {
        setForegroundOperation(kind);
      }
    };

    const readAndCommitAuthoritativeView = async (
      response: ActionResponse | null = null,
    ) => {
      transition("refreshing");
      const restoredView = await client.getSessionView(
        record.session_id,
        operation.controller.signal,
      );
      if (!isCurrent()) {
        return;
      }
      assertViewAssociation(record.session_id, restoredView, nativeExpected.current);
      const journey = await validateSuccessorRead(restoredView,operation.controller.signal);
      if (!isCurrent()) return;
      if (restoredView.run_context) nativeExpected.current = {sessionId:record.session_id, context:restoredView.run_context,
        scenarioId:restoredView.narrative_frame.scenario_id, contentVersion:restoredView.metadata.content_version};
      if (record.client_request_id !== undefined && !persistRecoveryRecord(record.session_id)) {
        return;
      }
      if (!isCurrent()) {
        return;
      }
      const next = {
        sessionId: record.session_id,
        view: restoredView,
        stale: null,
      };
      loadedSessionRef.current = next;
      setLoadedSession(next);
      setRestoredReading(journey ? {owner:next,client,journey} : null);
      if (journey) setContinuationStatus(journey);
      if (confirmedContinuation.current?.result.session_id === record.session_id) {
        setContinuationAttempt(null);
        continuationAttemptRef.current = null;
        setContinuationError(null);
      }
      setCommittedActionResponse(
        response !== null &&
          response.session_id === record.session_id &&
          response.resulting_state_version === restoredView.metadata.state_version
          ? response
          : null,
      );
    };

    void (async () => {
      await Promise.resolve();
      if (!isCurrent()) {
        return;
      }
      loadedSessionRef.current = null;
      setLoadedSession(null);
      setCommittedActionResponse(null);
      setCreatedSessionWithoutView(null);
      setOperationError(null);
      setRecoveryInterruption(null);
      setManualSessionId(record.session_id);
      setForegroundOperation(
        record.client_request_id === undefined ? "recovering" : "pending",
      );
      try {
        if (record.client_request_id !== undefined) {
          transition("pending");
          while (isCurrent()) {
            const requestStatus = await client.getNarrativeRequestStatus(
              record.session_id,
              record.client_request_id,
              operation.controller.signal,
            );
            if (!isCurrent()) {
              return;
            }
            if (requestStatus.status === "PENDING") {
              await pollWait(
                requestStatus.retry_after_seconds * 1_000,
                operation.controller.signal,
              );
              continue;
            }
            await readAndCommitAuthoritativeView(
              requestStatus.status === "COMMITTED"
                ? requestStatus.response
                : null,
            );
            return;
          }
          return;
        }
        await readAndCommitAuthoritativeView();
      } catch (error: unknown) {
        if (!isCurrent()) {
          return;
        }
        if (
          error instanceof ApiClientError &&
          error.kind === "api" &&
          error.status === 404
        ) {
          setRecoveryInterruption({message:RECOVERY_NOT_FOUND_MESSAGE});
          return;
        }
        if (
          error instanceof ApiClientError &&
          error.kind === "identity-mismatch"
        ) {
          setRecoveryInterruption({message:RECOVERY_IDENTITY_MISMATCH_MESSAGE});
          return;
        }
        setRecoveryInterruption({
          message: `${RECOVERY_INTERRUPTED_MESSAGE} ${formatApiClientError(error)}`,
        });
      } finally {
        if (foregroundOperationRef.current?.id === operation.id) {
          foregroundOperationRef.current = null;
          setForegroundOperation(null);
        }
      }
    })();

    return () => {
      operation.controller.abort();
      if (foregroundOperationRef.current?.id === operation.id) {
        foregroundOperationRef.current = null;
      }
    };
  }, [
    client,
    explicitlyAbandonSession,
    validateSuccessorRead,
    persistRecoveryRecord,
    pollWait,
    recoveryAttempt,
    recoveryStorageFailure,
  ]);

  const selectedScenario = scenarios?.find(
    (scenario) => scenario.scenario_id === selectedScenarioId,
  );
  const selectedPlayerCharacter =
    createdPlayerCharacter?.player_character_id.value ===
    selectedPlayerCharacterId
      ? createdPlayerCharacter
      : eligibleCharacters?.find(
          (character) =>
            character.player_character_id.value === selectedPlayerCharacterId,
        );

  const openingRecovery=useOpeningRecovery(client,recoveryRecord === null && recoveryStorageFailure === null);
  const opening = useOpeningPreparation(client,selectedPlayerCharacterId,entryMode === "native" && recoveryRecord === null &&
    !openingRecovery.loading && !openingRecovery.error && !openingRecovery.record);
  const openingRecord=openingRecovery.record ?? opening.record;

  function handleScenarioChange(scenarioId: string) {
    setSelectedScenarioId(scenarioId);
  }

  function commitLoadedSession(
    sessionId: string,
    view: PlayerSessionView,
    response: ActionResponse | null = null,
  ) {
    setHistoricalSession(null); setHistoricalJourney(null);
    assertViewAssociation(sessionId, view, nativeExpected.current);
    if (view.run_context) nativeExpected.current = {sessionId, context:view.run_context,
      scenarioId:view.narrative_frame.scenario_id, contentVersion:view.metadata.content_version};
    const next = { sessionId, view, stale: null };
    loadedSessionRef.current = next;
    setLoadedSession(next);
    setCommittedActionResponse(
      response !== null &&
        response.session_id === sessionId &&
        response.resulting_state_version === view.metadata.state_version
        ? response
        : null,
    );
  }


  function persistAndCommitLoadedSession(
    sessionId: string,
    view: PlayerSessionView,
    response: ActionResponse | null = null,
  ): boolean {
    assertNativeView(view, nativeExpected.current?.sessionId === sessionId ? nativeExpected.current.context : undefined);
    if (!persistRecoveryRecord(sessionId)) {
      return false;
    }
    commitLoadedSession(sessionId, view, response);
    return true;
  }

  function beginForegroundOperation(
    kind: ForegroundOperationKind,
    options: { clearSession: boolean; nextSessionId?: string },
  ): ForegroundOperation | null {
    if (foregroundOperationRef.current !== null) {
      return null;
    }
    if (recoveryStorageFailure !== null) {
      return null;
    }
    if (options.clearSession && !clearRecoveryForSessionTransition(options.nextSessionId)) {
      return null;
    }
    const operation = {
      controller: new AbortController(),
      id: operationGenerationRef.current + 1,
    };
    setRestoredReading(null);
    operationGenerationRef.current = operation.id;
    foregroundOperationRef.current = operation;
    setForegroundOperation(kind);
    setCreatedSessionWithoutView(null);
    setOperationError(null);
    setRecoveryInterruption(null);
    return operation;
  }

  function isCurrentOperation(operation: ForegroundOperation): boolean {
    return (
      latestClient.current === client &&
      foregroundOperationRef.current?.id === operation.id &&
      !operation.controller.signal.aborted
    );
  }

  function transitionForegroundOperation(
    operation: ForegroundOperation,
    kind: ForegroundOperationKind,
  ) {
    if (isCurrentOperation(operation)) {
      setForegroundOperation(kind);
    }
  }

  function finishForegroundOperation(operation: ForegroundOperation) {
    if (foregroundOperationRef.current?.id !== operation.id) {
      return;
    }
    foregroundOperationRef.current = null;
    setForegroundOperation(null);
  }

  function markCurrentViewStale(
    operation: ForegroundOperation,
    sessionId: string,
    stale: ViewStaleState,
  ) {
    if (!isCurrentOperation(operation)) {
      return;
    }
    const current = loadedSessionRef.current;
    if (current === null || current.sessionId !== sessionId) {
      return;
    }
    const next = { ...current, stale };
    loadedSessionRef.current = next;
    setLoadedSession(next);
  }

  async function readAndCommitCurrentView(
    operation: ForegroundOperation,
    sessionId: string,
    response: ActionResponse | null = null,
  ) {
    const restoredView = await client.getSessionView(
      sessionId,
      operation.controller.signal,
    );
    if (!isCurrentOperation(operation)) {
      return;
    }
    const current = loadedSessionRef.current;
    if (current === null || current.sessionId !== sessionId) {
      return;
    }
    await validateSuccessorRead(restoredView,operation.controller.signal);
    if (!isCurrentOperation(operation) || loadedSessionRef.current !== current) return;
    persistAndCommitLoadedSession(sessionId, restoredView, response);
  }

  function clearMutationAttempt(generation: number): boolean {
    const current = mutationAttemptRef.current;
    if (current === null || current.generation !== generation) {
      return false;
    }
    replaceMutationAttempt(null);
    return true;
  }

  function isDocumentedApiResult(
    error: unknown,
    status: number,
    codes: readonly string[],
  ): error is ApiClientError {
    return (
      error instanceof ApiClientError &&
      error.kind === "api" &&
      error.status === status &&
      error.errorCode !== undefined &&
      codes.includes(error.errorCode) &&
      DOCUMENTED_MUTATION_ERRORS[error.errorCode]?.status === status &&
      DOCUMENTED_MUTATION_ERRORS[error.errorCode]?.message === error.message
    );
  }

  function retainUncertainMutation(
    generation: number,
    error: unknown,
  ) {
    updateMutationAttempt(generation, (current) => ({
      ...current,
      uncertaintyTainted: true,
      inFlight: false,
    }));
    setOperationError(
      `${formatApiClientError(error)} ${MUTATION_UNCERTAIN_MESSAGE}`,
    );
  }

  function classifyMutationFailure(
    attempt: MutationAttempt,
    error: unknown,
  ) {
    const current = mutationAttemptRef.current;
    if (current === null || current.generation !== attempt.generation) {
      return;
    }
    if (current.kind === "session-create") {
      if (!current.uncertaintyTainted && !current.retainedResponse &&
          (isDocumentedApiResult(error, 409, ["IDEMPOTENCY_CONFLICT"]) ||
           isDocumentedApiResult(error, 422, ["REQUEST_VALIDATION_FAILED", "INVALID_SCENARIO_DEFINITION"]))) {
        clearMutationAttempt(current.generation);setOperationError(formatApiClientError(error));
      } else retainUncertainMutation(current.generation, error);
      return;
    }
    if (current.kind === "native-entry") {
      if (nativeFailureIsUncertain(current.uncertaintyTainted, error)) {
        retainUncertainMutation(current.generation, error); return;
      }
      clearMutationAttempt(current.generation);
      setOperationError(formatApiClientError(error));
      if (error instanceof ApiClientError) {
        if (["PLAYER_CHARACTER_NOT_FOUND","PLAYER_CHARACTER_STALE","PLAYER_CHARACTER_NOT_ELIGIBLE","RUN_ENTRY_CONFLICT"].includes(error.errorCode ?? "")) {
          setSelectedPlayerCharacterId(""); setCreatedPlayerCharacter(null); setRequiredCatalogRefresh("eligible");
        } else if (["INVALID_RUN_PROTOCOL","INVALID_ENTRY_WORLD","INVALID_SCENARIO_DEFINITION","NATIVE_RUN_ENTRY_NOT_AVAILABLE"].includes(error.errorCode ?? "")) {
          setRunOptions(null); setProfileId(""); setWorldId(""); setOverrides({}); setOptionsError("请刷新可用选项后重新确认。");
        }
      }
      return;
    }

    const documented404 = isDocumentedApiResult(
      error,
      404,
      ["PLAYER_CHARACTER_NOT_FOUND"],
    );
    if (
      documented404 &&
      (current.uncertaintyTainted ||
        (current.kind === "run-entry" &&
          current.entrySuccessAwaitingStorage))
    ) {
      retainUncertainMutation(attempt.generation, error);
      return;
    }

    if (attempt.kind === "player-character-create") {
      if (
        documented404 ||
        isDocumentedApiResult(error, 409, ["IDEMPOTENCY_CONFLICT"]) ||
        isDocumentedApiResult(error, 422, ["REQUEST_VALIDATION_FAILED"])
      ) {
        clearMutationAttempt(attempt.generation);
        setOperationError(formatApiClientError(error));
        return;
      }
      retainUncertainMutation(attempt.generation, error);
      return;
    }

    if (documented404) {
      clearMutationAttempt(attempt.generation);
      setSelectedPlayerCharacterId("");
      setCreatedPlayerCharacter(null);
      setRequiredCatalogRefresh("eligible");
      setOperationError(formatApiClientError(error));
      return;
    }
    if (isDocumentedApiResult(error, 409, ["IDEMPOTENCY_CONFLICT"])) {
      clearMutationAttempt(attempt.generation);
      setOperationError(formatApiClientError(error));
      return;
    }
    if (
      isDocumentedApiResult(error, 409, [
        "PLAYER_CHARACTER_STALE",
        "PLAYER_CHARACTER_NOT_ELIGIBLE",
        "RUN_ENTRY_CONFLICT",
      ])
    ) {
      clearMutationAttempt(attempt.generation);
      setSelectedPlayerCharacterId("");
      setCreatedPlayerCharacter(null);
      setRequiredCatalogRefresh("eligible");
      setOperationError(formatApiClientError(error));
      return;
    }
    if (
      isDocumentedApiResult(error, 422, [
        "REQUEST_VALIDATION_FAILED",
        "INVALID_SCENARIO_DEFINITION",
      ])
    ) {
      clearMutationAttempt(attempt.generation);
      if (error.errorCode === "INVALID_SCENARIO_DEFINITION") {
        setSelectedScenarioId("");
        setRequiredCatalogRefresh("scenario");
      } else {
        setSelectedPlayerCharacterId("");
        setCreatedPlayerCharacter(null);
        setRequiredCatalogRefresh("eligible");
      }
      setOperationError(formatApiClientError(error));
      return;
    }
    retainUncertainMutation(attempt.generation, error);
  }

  async function executeMutationAttempt(
    attempt: MutationAttempt,
    operation: ForegroundOperation,
  ) {
    try {
      if (attempt.kind === "player-character-create") {
        const created = await client.createPlayerCharacter(
          attempt.exactFrozenBody,
          attempt.idempotencyKey,
          operation.controller.signal,
        );
        if (!isCurrentOperation(operation)) {
          return;
        }
        if (!clearMutationAttempt(attempt.generation)) {
          return;
        }
        setCreatedPlayerCharacter(created);
        setSelectedPlayerCharacterId(created.player_character_id.value);
        setRequiredCatalogRefresh(null);
        setOperationError(null);
        return;
      }

      if (attempt.kind === "session-create") {
        const created = attempt.retainedResponse ?? await client.createSession(attempt.exactFrozenBody, operation.controller.signal);
        if (!isCurrentOperation(operation)) return;
        if (created.scenario_id !== attempt.exactFrozenBody.scenario_id ||
            created.character_definition_id !== attempt.exactFrozenBody.character_definition_id ||
            created.content_version !== attempt.contentVersion || created.narrative_frame.scenario_id !== created.scenario_id) {
          throw new ApiClientError("Story creation association changed", {kind:"invalid-response",reason:"CONTRACT_MISMATCH"});
        }
        updateMutationAttempt(attempt.generation, current => current.kind === "session-create" ? {...current,retainedResponse:created} : current);
        if (!persistRecoveryRecord(created.session_id)) {
          updateMutationAttempt(attempt.generation, current => ({...current,inFlight:false}));return;
        }
        setManualSessionId(created.session_id);
        try {
          const restored = await client.getSessionView(created.session_id, operation.controller.signal);
          if (!isCurrentOperation(operation)) return;
          if (restored.metadata.session_id !== created.session_id || restored.run_context ||
              restored.narrative_frame.scenario_id !== created.scenario_id ||
              restored.metadata.content_version !== created.content_version ||
              restored.metadata.character_definition_id !== created.character_definition_id || !restored.encounter) {
            throw new ApiClientError("Story View association changed", {kind:"invalid-response",reason:"CONTRACT_MISMATCH"});
          }
          commitLoadedSession(created.session_id, restored);
          clearMutationAttempt(attempt.generation);
        } catch(error: unknown) {
          if (!isCurrentOperation(operation)) return;
          retainUncertainMutation(attempt.generation,error);
        }
        return;
      }
      if (attempt.kind === "native-entry" && attempt.opening && !attempt.retainedResponse) {
        // Explicit retries must retain the same recovery route too.
        const saved=writeOpeningRecovery(client,attempt.opening.record);
        if (!saved.ok) {
          updateMutationAttempt(attempt.generation,current=>({...current,inFlight:false}));
          setOperationError("无法保存开局恢复入口；确认请求未发送。请恢复此标签页的存储后重试。");
          return;
        }
      }
      const entered = attempt.kind === "native-entry"
        ? attempt.retainedResponse ?? (attempt.opening
          ? await client.confirmOpening(attempt.frozen,attempt.opening.record,attempt.opening.selected,operation.controller.signal)
          : await client.enterNativeRun(attempt.frozen, operation.controller.signal))
        : await client.enterRun(attempt.exactFrozenBody, attempt.idempotencyKey, operation.controller.signal);
      if (!isCurrentOperation(operation)) {
        return;
      }
      if (attempt.kind === "native-entry" && "run_context" in entered) {
        updateMutationAttempt(attempt.generation, (current) => current.kind === "native-entry" ? {...current, retainedResponse:entered} : current);
        nativeExpected.current = {sessionId:entered.session_id, context:entered.run_context,
          scenarioId:entered.scenario_id, contentVersion:entered.scenario_content_version};
      }
      if (!persistRecoveryRecord(entered.session_id)) {
        updateMutationAttempt(attempt.generation, (current) => ({
          ...current,
          ...(current.kind === "run-entry"
            ? { entrySuccessAwaitingStorage: true }
            : {}),
          inFlight: false,
        }));
        return;
      }
      if (!clearMutationAttempt(attempt.generation)) {
        return;
      }
      setManualSessionId(entered.session_id);
      setCreatedSessionWithoutView(null);
      try {
        const restoredView = await client.getSessionView(
          entered.session_id,
          operation.controller.signal,
        );
        if (!isCurrentOperation(operation)) {
          return;
        }
        commitLoadedSession(entered.session_id, restoredView);
      } catch (error: unknown) {
        if (!isCurrentOperation(operation)) {
          return;
        }
        setCreatedSessionWithoutView(entered.session_id);
        setOperationError(
          `Run 已进入且 Session ID 已保存；权威 View 读取失败：${formatApiClientError(error)}`,
        );
      }
    } catch (error: unknown) {
      if (!isCurrentOperation(operation)) {
        return;
      }
      classifyMutationFailure(attempt, error);
    } finally {
      finishForegroundOperation(operation);
    }
  }

  function installAndSendMutation(
    attempt: MutationAttempt,
    operationKind: "creating" | "entering",
  ) {
    replaceMutationAttempt(attempt);
    const operation = beginForegroundOperation(operationKind, {
      clearSession: false,
    });
    if (operation === null) {
      clearMutationAttempt(attempt.generation);
      return;
    }
    void executeMutationAttempt(attempt, operation);
  }

  function buildMutationIdentity(): string | null {
    try {
      const parsed = idempotencyKeySchema.safeParse(idempotencyKeyFactory());
      if (!parsed.success) {
        setOperationError("无法构造有效的操作身份；请求未发送。");
        return null;
      }
      return parsed.data;
    } catch {
      setOperationError("无法构造有效的操作身份；请求未发送。");
      return null;
    }
  }

  function handleStoryStart(story: PublicScenarioDescription) {
    if (prePlayControlsDisabled || story.entry_mode !== "SESSION" || foregroundOperationRef.current !== null || mutationAttemptRef.current !== null) return;
    const key = buildMutationIdentity();
    if (key === null) return;
    const body = createSessionRequestSchema.safeParse({client_request_id:key,
      scenario_id:story.scenario_id, character_definition_id:story.default_character_definition_id});
    if (!body.success) {setOperationError("无法创建本次故事的请求身份，请重试。");return;}
    const generation = ++mutationGenerationRef.current;
    installAndSendMutation({kind:"session-create", generation, idempotencyKey:key,
      exactFrozenBody:Object.freeze(body.data), contentVersion:story.content_version,
      uncertaintyTainted:false, inFlight:true}, "entering");
  }

  function handlePlayerCharacterCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      foregroundOperationRef.current !== null ||
      mutationAttemptRef.current !== null ||
      recoveryRecordRef.current !== null ||
      recoveryInterruption !== null ||
      recoveryStorageFailure !== null ||
      eligibleCharacters?.length !== 0 ||
      createdPlayerCharacter !== null
    ) {
      return;
    }
    const idempotencyKey = buildMutationIdentity();
    if (idempotencyKey === null) {
      return;
    }
    const parsedBody = minimalPlayerCharacterCreationRequestSchema.safeParse({
      contract_version: "structured-player-character/v1",
      character_core: {},
      narration_preferences: {},
    });
    if (!parsedBody.success) {
      setOperationError("无法构造最小 Player Character 请求；请求未发送。");
      return;
    }
    const exactFrozenBody = Object.freeze({
      ...parsedBody.data,
      character_core: Object.freeze({}),
      narration_preferences: Object.freeze({}),
    });
    const generation = mutationGenerationRef.current + 1;
    mutationGenerationRef.current = generation;
    installAndSendMutation(
      {
        kind: "player-character-create",
        generation,
        idempotencyKey,
        exactFrozenBody,
        uncertaintyTainted: false,
        inFlight: true,
      },
      "creating",
    );
  }

  function handleRunEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      foregroundOperationRef.current !== null ||
      mutationAttemptRef.current !== null ||
      recoveryRecordRef.current !== null ||
      recoveryInterruption !== null ||
      recoveryStorageFailure !== null ||
      requiredCatalogRefresh !== null ||
      entryMode !== "legacy" ||
      selectedScenario === undefined || selectedScenario.entry_mode === "SESSION" ||
      selectedPlayerCharacter === undefined
    ) {
      return;
    }
    const idempotencyKey = buildMutationIdentity();
    if (idempotencyKey === null) {
      return;
    }
    const parsedBody = runEntryRequestSchema.safeParse({
      player_character_id:
        selectedPlayerCharacter.player_character_id.value,
      expected_record_revision:
        selectedPlayerCharacter.record_revision.value,
      scenario_id: selectedScenario.scenario_id,
    });
    if (!parsedBody.success) {
      setOperationError("无法构造有效的 Run-entry 请求；请求未发送。");
      return;
    }
    const exactFrozenBody = Object.freeze(parsedBody.data);
    const generation = mutationGenerationRef.current + 1;
    mutationGenerationRef.current = generation;
    installAndSendMutation(
      {
        kind: "run-entry",
        generation,
        idempotencyKey,
        exactFrozenBody,
        uncertaintyTainted: false,
        inFlight: true,
        entrySuccessAwaitingStorage: false,
      },
      "entering",
    );
  }

  async function handleNativeEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (entryMode !== "native" || !selectedProfile || !selectedWorld || !selectedPlayerCharacter ||
        foregroundOperationRef.current || mutationAttemptRef.current || recoveryRecordRef.current || recoveryStorageFailure ||
        recoveryInterruption || requiredCatalogRefresh || opening.loading || opening.error || opening.record?.state === "PENDING" || !runOptions?.native_entry_available) return;
    const key = buildMutationIdentity();
    if (key === null) return;
    try {
      if (Object.values(overrides).some((v) => v.trim() === "")) throw new Error("empty override");
      const frozen = client.freezeNativeEntry({player_character_id:selectedPlayerCharacter.player_character_id.value,
        expected_record_revision:selectedPlayerCharacter.record_revision.value, profile_ref:selectedProfile.profile_ref,
        entry_world:selectedWorld.entry_world, overrides:objectiveNames.filter((n) => n in overrides).map((n) => ({parameter:n,value:Number(overrides[n])})),
        presentation:runPresentation}, key, selectedProfile, selectedWorld);
      const operation = beginForegroundOperation("entering", {clearSession:false});
      if (!operation) return;
      try { await opening.prepare(frozen,operation.controller.signal); }
      catch { if (isCurrentOperation(operation)) setOperationError("开局准备暂未读回。请再次读取；重试不会更换候选。"); }
      finally {finishForegroundOperation(operation);}

    } catch {setOperationError("请检查难度范围与步长；请求未发送。");}
  }

  async function handleOpeningConfirmation(selected:readonly string[]) {
    const record=openingRecord;
    if (!record || foregroundOperationRef.current || mutationAttemptRef.current || recoveryRecordRef.current ||
        recoveryStorageFailure || recoveryInterruption || openingRecovery.loading || openingRecovery.error || !runOptions ||
        (!openingRecovery.record && record.character_id !== selectedPlayerCharacterId)) return;
    const profile=runOptions.profiles.find(p => p.profile_ref.profile_id === record.admission.profile_ref.profile_id && p.profile_ref.profile_version === record.admission.profile_ref.profile_version);
    const world=runOptions.entry_worlds.find(w => w.entry_world.entry_world_id === record.admission.entry_world.entry_world_id && w.entry_world.entry_world_version === record.admission.entry_world.entry_world_version);
    if (!profile || !world) {setOperationError("原先的入场设置暂不可用，请重新读取准备。");return;}
    const key=record.state === "CONFIRMED" ? "opening.recovery" : buildMutationIdentity();
    if (!key) return;
    try {
      const frozen=client.freezeNativeEntry(record.admission,key,profile,world);
      if (record.state === "CONFIRMED") {
        const operation=beginForegroundOperation("recovering",{clearSession:false});
        if (!operation) return;
        try {
          // Refresh the owned preparation before using its result. Local IDs are only locators.
          const authoritative=await client.getOpeningPreparation(record.character_id,operation.controller.signal);
          if (!isCurrentOperation(operation)) return;
          assertOpeningReference({version:1,character_id:record.character_id,preparation_id:record.preparation_id},authoritative);
          if (!authoritative.result || JSON.stringify(authoritative)!==JSON.stringify(record)) throw new Error("Opening confirmation changed");
          const entered=authoritative.result;
          assertNativeResponse(frozen,entered);
          const view=await client.getSessionView(entered.session_id,operation.controller.signal);
          if (!isCurrentOperation(operation)) return;
          const expected={sessionId:entered.session_id,context:entered.run_context,scenarioId:entered.scenario_id,contentVersion:entered.scenario_content_version};
          assertViewAssociation(entered.session_id,view,expected);
          const journey=await client.getNativeRunJourney(entered.session_id,operation.controller.signal);
          assertContinuationStatus(view,journey);
          // A concurrent/manual recovery target always wins over this older locator.
          const storedSession=readSessionRecoveryRecord();
          const storedOpening=readOpeningRecovery(client);
          if (!isCurrentOperation(operation) || recoveryRecordRef.current || !storedSession.ok || storedSession.value ||
              !storedOpening.ok || (openingRecovery.record && !storedOpening.value) ||
              (storedOpening.value && (storedOpening.value.preparation_id!==record.preparation_id || storedOpening.value.character_id!==record.character_id))) return;
          if (!persistRecoveryRecord(entered.session_id)) return;
          nativeExpected.current=expected;
          commitLoadedSession(entered.session_id,view);
          const current=loadedSessionRef.current;
          if (current) setRestoredReading({owner:current,client,journey});
          setContinuationStatus(journey);
        } catch (error) {
          if (isCurrentOperation(operation)) setOperationError(`开局恢复尚未完成，恢复入口已保留：${formatApiClientError(error)}`);
        } finally {finishForegroundOperation(operation);}
        return;
      }
      const saved=writeOpeningRecovery(client,record);
      if (!saved.ok) {setOperationError("无法保存开局恢复入口；确认请求未发送。请恢复此标签页的存储后重试。");return;}
      const generation=++mutationGenerationRef.current;
      installAndSendMutation({kind:"native-entry",generation,idempotencyKey:key,frozen,
        opening:{record:structuredClone(record),selected:Object.freeze([...selected])},uncertaintyTainted:false,inFlight:true},"entering");
    } catch {setOperationError("天赋与入场设置不一致，请重新读取准备。");}
  }

  function handleNativeStorageRetry() {
    const attempt = mutationAttemptRef.current;
    if (attempt?.kind !== "native-entry" || !attempt.retainedResponse || foregroundOperationRef.current) return;
    const response = attempt.retainedResponse;
    if (!persistRecoveryRecord(response.session_id)) return;
    nativeExpected.current = {sessionId:response.session_id, context:response.run_context,
      scenarioId:response.scenario_id, contentVersion:response.scenario_content_version};
    setRecoveryStorageFailure(null);
    if (!clearMutationAttempt(attempt.generation)) return;
    setManualSessionId(response.session_id);
    setCreatedSessionWithoutView(response.session_id);
    setOperationError("进度已保存，请重新读取进度。");
  }

  function handleMutationRetry() {
    const current = mutationAttemptRef.current;
    if (
      current === null ||
      current.inFlight ||
      foregroundOperationRef.current !== null ||
      recoveryInterruption !== null ||
      recoveryStorageFailure !== null
    ) {
      return;
    }
    const next = { ...current, inFlight: true };
    replaceMutationAttempt(next);
    const operation = beginForegroundOperation(
      next.kind === "player-character-create" ? "creating" : "entering",
      { clearSession: false },
    );
    if (operation === null) {
      replaceMutationAttempt(current);
      return;
    }
    void executeMutationAttempt(next, operation);
  }

  async function handleManualRead(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (historicalSession || historyLoading || continuationAttemptRef.current || completionAttemptRef.current) return;
    if (
      foregroundOperationRef.current !== null ||
      mutationAttemptRef.current !== null ||
      recoveryInterruption !== null ||
      recoveryStorageFailure !== null
    ) {
      return;
    }
    const sessionId = manualSessionId.trim();
    const parsedSessionId = sessionPathIdSchema.safeParse(sessionId);
    if (!parsedSessionId.success) {
      if (!clearRecoveryForSessionTransition()) {
        return;
      }
      setCreatedSessionWithoutView(null);
      setRecoveryInterruption(null);
      setOperationError("Session ID 格式无效，请检查后重试。");
      return;
    }
    const operation = beginForegroundOperation("reading", {
      clearSession: true,
      nextSessionId: parsedSessionId.data,
    });
    if (operation === null) {
      return;
    }
    try {
      const restoredView = await client.getSessionView(
        parsedSessionId.data,
        operation.controller.signal,
      );
      if (!isCurrentOperation(operation)) {
        return;
      }
      await validateSuccessorRead(restoredView,operation.controller.signal);
      if (!isCurrentOperation(operation)) return;
      persistAndCommitLoadedSession(parsedSessionId.data, restoredView);
    } catch (error: unknown) {
      if (!isCurrentOperation(operation)) {
        return;
      }
      setOperationError(formatApiClientError(error));
    } finally {
      finishForegroundOperation(operation);
    }
  }

  async function handleEnteredSessionViewRetry() {
    const sessionId = createdSessionWithoutView;
    if (
      sessionId === null ||
      foregroundOperationRef.current !== null ||
      mutationAttemptRef.current !== null ||
      recoveryStorageFailure !== null
    ) {
      return;
    }
    const operation = beginForegroundOperation("reading", {
      clearSession: false,
    });
    if (operation === null) {
      return;
    }
    try {
      const restoredView = await client.getSessionView(
        sessionId,
        operation.controller.signal,
      );
      if (!isCurrentOperation(operation)) {
        return;
      }
      await validateSuccessorRead(restoredView,operation.controller.signal);
      if (!isCurrentOperation(operation)) return;
      commitLoadedSession(sessionId, restoredView);
      setCreatedSessionWithoutView(null);
      setOperationError(null);
    } catch (error: unknown) {
      if (!isCurrentOperation(operation)) {
        return;
      }
      setOperationError(
        `权威 View 读取失败：${formatApiClientError(error)}`,
      );
    } finally {
      finishForegroundOperation(operation);
    }
  }

  function handleScenarioRefresh() {
    if (
      foregroundOperationRef.current !== null ||
      mutationAttemptRef.current !== null
    ) {
      return;
    }
    setRequiredCatalogRefresh(null);
    setScenarios(null);
    setScenarioError(null);
    setScenarioRefreshAttempt((attempt) => attempt + 1);
  }

  function handleEligibleRefresh() {
    if (
      foregroundOperationRef.current !== null ||
      mutationAttemptRef.current !== null
    ) {
      return;
    }
    setRequiredCatalogRefresh(null);
    setEligibleCharacters(null);
    setEligibleTruncated(false);
    setEligibleError(null);
    setCreatedPlayerCharacter(null);
    setSelectedPlayerCharacterId("");
    setEligibleRefreshAttempt((attempt) => attempt + 1);
  }

  async function handleExplicitViewRefresh() {
    if (historicalSession || historyLoading || continuationAttemptRef.current || completionAttemptRef.current) return;
    const current = loadedSessionRef.current;
    if (
      current === null ||
      current.stale === null ||
      recoveryStorageFailure !== null ||
      foregroundOperationRef.current !== null
    ) {
      return;
    }
    const operation = beginForegroundOperation("refreshing", {
      clearSession: false,
    });
    if (operation === null) {
      return;
    }
    try {
      await readAndCommitCurrentView(operation, current.sessionId);
    } catch (error: unknown) {
      if (!isCurrentOperation(operation)) {
        return;
      }
      setOperationError(
        `权威 View 刷新失败：${formatApiClientError(error)}`,
      );
    } finally {
      finishForegroundOperation(operation);
    }
  }

  function handleRecoveryRetry() {
    if (
      foregroundOperationRef.current !== null ||
      recoveryInterruption === null ||
      recoveryStorageFailure !== null
    ) {
      return;
    }
    setRecoveryAttempt((attempt) => attempt + 1);
  }

  function handleExplicitSessionClear() {
    if (historicalSession || historyLoading || continuationAttemptRef.current || completionAttemptRef.current) return;
    explicitlyAbandonSession();
  }

  function handleStorageFailureClearRetry() {
    explicitlyAbandonSession();
  }

  async function handleActionRequest(requestFactory: () => ActionRequest) {
    if (historicalSession || continuationAttemptRef.current || exitAttemptRef.current || completionAttemptRef.current) return;
    const current = loadedSessionRef.current;
    if (current?.view.run_context &&
        (continuationError || continuationStatus?.session_id !== current.sessionId ||
         continuationStatus.path.session_state_version !== current.view.metadata.state_version ||
         continuationStatus.current.session_id !== current.sessionId || continuationStatus.lifecycle_status !== "active")) return;
    if (
      current === null ||
      current.stale !== null ||
      current.view.scenario_status !== "ACTIVE" ||
      current.view.action_affordances.mode === "ENDED" ||
      recoveryStorageFailure !== null ||
      foregroundOperationRef.current !== null
    ) {
      return;
    }
    const operation = beginForegroundOperation("submitting", {
      clearSession: false,
    });
    if (operation === null) {
      return;
    }
    setCommittedActionResponse(null);
    let stage: "building" | "posting" | "polling" | "refreshing" =
      "building";
    try {
      const request = requestFactory();
      stage = "posting";
      const submitted = await client.submitAction(
        current.sessionId,
        request,
        operation.controller.signal,
      );
      if (!isCurrentOperation(operation)) {
        return;
      }

      if (submitted.status === 200) {
        stage = "refreshing";
        transitionForegroundOperation(operation, "refreshing");
        await readAndCommitCurrentView(
          operation,
          current.sessionId,
          submitted.response,
        );
        return;
      }

      stage = "polling";
      transitionForegroundOperation(operation, "pending");
      if (
        !persistRecoveryRecord(
        current.sessionId,
        request.client_request_id,
        )
      ) {
        return;
      }
      while (isCurrentOperation(operation)) {
        const requestStatus = await client.getNarrativeRequestStatus(
          current.sessionId,
          request.client_request_id,
          operation.controller.signal,
        );
        if (!isCurrentOperation(operation)) {
          return;
        }
        if (requestStatus.status === "PENDING") {
          await pollWait(
            requestStatus.retry_after_seconds * 1_000,
            operation.controller.signal,
          );
          continue;
        }
        if (requestStatus.status === "COMMITTED") {
          stage = "refreshing";
          transitionForegroundOperation(operation, "refreshing");
          await readAndCommitCurrentView(
            operation,
            current.sessionId,
            requestStatus.response,
          );
          return;
        }
        if (requestStatus.status === "STALE") {
          stage = "refreshing";
          transitionForegroundOperation(operation, "refreshing");
          await readAndCommitCurrentView(operation, current.sessionId);
          return;
        }
        if (requestStatus.status === "OUTCOME_UNKNOWN") {
          markCurrentViewStale(operation, current.sessionId, {
            kind: "outcome-unknown",
            message: OUTCOME_UNKNOWN_MESSAGE,
          });
          return;
        }
        markCurrentViewStale(operation, current.sessionId, {
          kind: "request-failed",
          message: REQUEST_FAILED_MESSAGE,
        });
        return;
      }
    } catch (error: unknown) {
      if (!isCurrentOperation(operation)) {
        return;
      }
      if (
        stage === "polling" &&
        error instanceof ApiClientError &&
        error.kind === "identity-mismatch"
      ) {
        if (nativeExpected.current?.sessionId === current.sessionId) {
          markCurrentViewStale(operation, current.sessionId, {
            kind: "pending-status-unknown",
            message: RECOVERY_IDENTITY_MISMATCH_MESSAGE,
          });
        } else if (explicitlyAbandonSession()) {
          setOperationError(RECOVERY_IDENTITY_MISMATCH_MESSAGE);
        }
      } else if (stage === "posting" && isTransportUncertain(error)) {
        markCurrentViewStale(operation, current.sessionId, {
          kind: "transport-uncertain",
          message: TRANSPORT_UNCERTAIN_MESSAGE,
        });
      } else if (stage === "polling") {
        markCurrentViewStale(operation, current.sessionId, {
          kind: "pending-status-unknown",
          message: PENDING_STATUS_UNKNOWN_MESSAGE,
        });
      } else if (stage === "refreshing") {
        markCurrentViewStale(operation, current.sessionId, {
          kind: "confirmed-view-unavailable",
          message: CONFIRMED_VIEW_UNAVAILABLE_MESSAGE,
        });
      } else {
        setOperationError(formatApiClientError(error));
      }
    } finally {
      finishForegroundOperation(operation);
    }
  }

  async function handleAction(intent: ActionIntent) {
    await handleActionRequest(() => {
      const identity = actionIdentityFactory();
      return actionRequestSchema.parse({
        turn_id: identity.turnId,
        client_request_id: identity.clientRequestId,
        ...intent,
      });
    });
  }

  async function handleSuggestedAction(suggestion: PublicSuggestedAction) {
    await handleActionRequest(() =>
      actionRequestSchema.parse(suggestion.submission),
    );
  }

  async function adoptContinuation(current: LoadedSession, result: NativeRunContinuationResult, operation: ForegroundOperation) {
    assertContinuationResult(current.view,result);
    if (!isCurrentOperation(operation) || loadedSessionRef.current !== current) return;
    const prior=confirmedContinuation.current;
    if (prior?.result.source_session_id === current.sessionId) {
      if (JSON.stringify(prior.result) !== JSON.stringify(result)) throw new Error("已确认的续接关联不匹配");
      assertContinuationResult(prior.source,result);
      assertViewAssociation(current.sessionId,current.view,{sessionId:prior.source.metadata.session_id,
        context:prior.result.run_context,scenarioId:prior.source.narrative_frame.scenario_id,contentVersion:prior.source.metadata.content_version});
    } else {
      const frozen=continuationAttemptRef.current;
      if (!frozen || frozen.sessionId !== current.sessionId) throw new Error("缺少已确认的来源关联");
      confirmedContinuation.current=structuredClone({source:frozen.source,sourceAssociation:frozen.authority.path,result});
    }
    setPendingContinuationRecovery(result);
    // Persist the authoritative successor before publishing any successor View.
    if (!persistRecoveryRecord(result.session_id)) return;
    nativeExpected.current={sessionId:result.session_id,context:result.run_context,scenarioId:result.scenario_id,contentVersion:result.scenario_content_version};
    const view=await client.getSessionView(result.session_id,operation.controller.signal);
    if (!isCurrentOperation(operation) || loadedSessionRef.current !== current) return;
    assertViewAssociation(result.session_id,view,nativeExpected.current);
    const status=await client.getNativeRunJourney(result.session_id,operation.controller.signal);
    if (!isCurrentOperation(operation) || loadedSessionRef.current !== current) return;
    assertContinuationStatus(view,status);
    assertConfirmedSuccessor(confirmedContinuation.current!,view,status);
    commitLoadedSession(result.session_id,view);
    setPendingContinuationRecovery(null);
    setContinuationStatus(status); setContinuationAttempt(null); continuationAttemptRef.current=null; setContinuationError(null);
  }

  async function handleContinuation(retry=false) {
    const current=loadedSessionRef.current;
    if (!current || current.stale || historicalSession || foregroundOperationRef.current || exitAttemptRef.current || completionAttemptRef.current ||
        !hasRunAuthority(current)) return;
    let attempt=continuationAttemptRef.current;
    if (!retry) {
      if (attempt || !continuationConfirm || !continuationStatus || continuationStatus.lifecycle_status !== "active" ||
          continuationStatus.current.session_id !== current.sessionId) return;
      const opened=continuationConfirmationRef.current;
      if(!opened || opened.client!==client || JSON.stringify(opened.view)!==JSON.stringify(current.view) ||
          JSON.stringify(opened.authority)!==JSON.stringify({journey:continuationStatus,status:runStatus,completion:completionStatus}))return;
      attempt=freezeRunContinuation(current.view,continuationStatus,idempotencyKeyFactory());
      continuationAttemptRef.current=attempt;setContinuationAttempt(attempt);setContinuationConfirm(false);
    }
    if (!attempt || attempt.sessionId !== current.sessionId || attempt.runId !== current.view.run_context?.run_id) return;
    const operation=beginForegroundOperation("submitting",{clearSession:false});
    if (!operation) return;
    try {await adoptContinuation(current,await client.transitionNativeRun(attempt,operation.controller.signal),operation);}
    catch(error) {if(isCurrentOperation(operation)) setContinuationError(formatApiClientError(error));}
    finally {finishForegroundOperation(operation);}
  }

  function retryContinuationStorage() {
    const result=pendingContinuationRecovery;
    if (!result || foregroundOperationRef.current) return;
    const written=writeSessionRecoveryRecord(result.session_id);
    if (!written.ok) {setRecoveryStorageFailure({failure:written.failure});return;}
    nativeExpected.current={sessionId:result.session_id,context:result.run_context,scenarioId:result.scenario_id,contentVersion:result.scenario_content_version};
    recoveryRecordRef.current=written.value;setRecoveryRecord(written.value);
    setPendingContinuationRecovery(null);setRecoveryStorageFailure(null);setRecoveryAttempt(n=>n+1);
  }

  async function reconcileContinuation() {
    const current=loadedSessionRef.current;
    if (!current || historicalSession || foregroundOperationRef.current) return;
    const operation=beginForegroundOperation("reading",{clearSession:false});
    if (!operation) return;
    setRunAuthority(null);
    try {
      const status=await client.getNativeRunJourney(current.sessionId,operation.controller.signal);
      if (!isCurrentOperation(operation) || loadedSessionRef.current !== current) return;
      assertContinuationStatus(current.view,status);
      const confirmed=confirmedContinuation.current;
      if (confirmed) assertConfirmedCurrent(confirmed,status);
      if (confirmedContinuation.current?.result.session_id === current.sessionId)
        assertConfirmedSuccessor(confirmedContinuation.current,current.view,status);
      setContinuationStatus(status);setContinuationError(null);
      if (status.current.session_id !== current.sessionId) {
        const target=status.current;
        const saveTarget=()=>{
          if (!persistRecoveryRecord(target.session_id)) return false;
          nativeExpected.current={sessionId:target.session_id,context:confirmed?.result.run_context ?? status.run_context,
            scenarioId:target.scenario_id,contentVersion:target.scenario_content_version};
          return true;
        };
        // Without a retained receipt, keep the existing old-record recovery order.
        if (!confirmed && !saveTarget()) return;
        const view=await client.getSessionView(target.session_id,operation.controller.signal);
        const destination=await client.getNativeRunJourney(target.session_id,operation.controller.signal);
        if (!isCurrentOperation(operation) || loadedSessionRef.current !== current) return;
        assertContinuationStatus(view,destination);
        assertNativeView(view,status.run_context);
        if (!sameAssociation(target,destination.path) || destination.run_state_version!==status.run_state_version ||
            destination.lifecycle_status!==status.lifecycle_status) throw new Error("当前旅程关联发生变化，请重新读取");
        if (confirmed) assertConfirmedSuccessor(confirmed,view,destination);
        // Validate both GETs against retained POST authority before changing recovery.
        if (confirmed && !saveTarget()) return;
        commitLoadedSession(target.session_id,view);setContinuationStatus(destination);
        setPendingContinuationRecovery(null);
        setContinuationAttempt(null);continuationAttemptRef.current=null;
      } else {
        commitLoadedSession(current.sessionId,current.view);
      }
    } catch(error) {if(isCurrentOperation(operation)) setContinuationError(formatApiClientError(error));}
    finally {finishForegroundOperation(operation);}
  }

  async function navigateHistory(direction: "previous" | "next" | "current" = "previous") {
    const current=loadedSessionRef.current;
    if (direction === "current" && historyLoading) invalidateForegroundOperation();
    if (!current || foregroundOperationRef.current || continuationAttemptRef.current || exitAttemptRef.current || completionAttemptRef.current) return;
    const displayed=historicalSession ?? current;
    const operation=beginForegroundOperation("reading",{clearSession:false});
    if (!operation) return;
    setRunAuthority(null);
    setHistoryLoading(true);
    try {
      const signal=operation.controller.signal;
      const from=await client.getNativeRunJourney(displayed.sessionId,signal);
      assertContinuationStatus(displayed.view,from);
      if (confirmedCompletion.current) assertCompletionHistory(confirmedCompletion.current,from);
      if (confirmedContinuation.current) assertConfirmedCurrent(confirmedContinuation.current,from);
      const target=direction === "current" ? from.current : direction === "previous" ? from.predecessor : from.successor;
      if (!target || from.current.session_id!==current.sessionId) throw new Error("缺少完整的历史关联");
      const view=await client.getSessionView(target.session_id,signal);
      const status=await client.getNativeRunJourney(target.session_id,signal);
      assertContinuationStatus(view,status);assertNativeView(view,current.view.run_context);
      if (confirmedCompletion.current) assertCompletionHistory(confirmedCompletion.current,status);
      if (!sameAssociation(target,status.path) || !sameAssociation(from.current,status.current) ||
          from.run_state_version!==status.run_state_version || from.lifecycle_status!==status.lifecycle_status)
        throw new Error("历史关联发生变化，请重新读取");
      if (direction!=="current") assertNeighbor(from,status);
      if (confirmedContinuation.current?.result.session_id===target.session_id)
        assertConfirmedSuccessor(confirmedContinuation.current,view,status);
      if (!isCurrentOperation(operation) || loadedSessionRef.current!==current) return;
      if (target.session_id===current.sessionId) {commitLoadedSession(current.sessionId,view);setContinuationStatus(status);}
      else {setHistoricalSession({sessionId:target.session_id,view,stale:null});setHistoricalJourney(status);}
      setContinuationError(null);
    } catch(error) {if(isCurrentOperation(operation)) setContinuationError(formatApiClientError(error));}
    finally {if(isCurrentOperation(operation)) setHistoryLoading(false);finishForegroundOperation(operation);}
  }

  async function handleCompletion(retry=false) {
    const current=loadedSessionRef.current;
    if(!current || current.stale || historicalSession || foregroundOperationRef.current || exitAttemptRef.current ||
        continuationAttemptRef.current || completionClientRef.current!==client) return;
    let attempt=completionAttemptRef.current;
    if(retry && (completionRetryBlockedRef.current || (confirmedCompletion.current && !hasRunAuthority(current)))) return;
    if(!retry) {
      if(attempt || !completionConfirm || !hasRunAuthority(current) || !runAuthority?.status || !runAuthority.completion) return;
      try {assertCompletionSubmission(completionConfirm,current.view,{journey:runAuthority.journey,status:runAuthority.status,completion:runAuthority.completion});}
      catch(error) {setCompletionError(formatApiClientError(error));return;}
      attempt=completionConfirm;completionAttemptRef.current=attempt;setCompletionAttempt(attempt);setCompletionConfirm(null);
    }
    if(!attempt || attempt.sessionId!==current.sessionId || attempt.runId!==current.view.run_context?.run_id)return;
    if(JSON.stringify(attempt.source)!==JSON.stringify(current.view) || (retry && completionRetryBlockedRef.current)) return;
    const operation=beginForegroundOperation("submitting",{clearSession:false});
    if(!operation)return;
    setCompletionError(null);setRunAuthority(null);
    try {
      const result=await client.completeNativeRun(attempt,operation.controller.signal);
      if(!isCurrentOperation(operation) || loadedSessionRef.current!==current)return;
      if(confirmedCompletion.current && JSON.stringify(confirmedCompletion.current.result)!==JSON.stringify(result))
        throw new ApiClientError("Confirmed completion replay mismatch",{kind:"invalid-response",reason:"CONTRACT_MISMATCH"});
      confirmedCompletion.current ??= {attempt,result:structuredClone(result)};setCompletionProof(confirmedCompletion.current);
      const [journey,status,completion]=await Promise.all([client.getNativeRunJourney(current.sessionId,operation.controller.signal),
        client.getNativeRunStatus(current.sessionId,operation.controller.signal),client.getNativeRunCompletion(current.sessionId,operation.controller.signal)]);
      if(!isCurrentOperation(operation) || loadedSessionRef.current!==current)return;
      assertConfirmedCompletion(confirmedCompletion.current,current.view,{journey,status,completion});
      setContinuationStatus(journey);setRunStatus(status);setCompletionStatus(completion);
      setRunAuthority({owner:current,client,journey,status,completion});
      completionAttemptRef.current=null;setCompletionAttempt(null);
    } catch(error) {if(isCurrentOperation(operation)){
      if(error instanceof ApiClientError && error.reason==="CONTRACT_MISMATCH") blockCompletionRetry(true);
      setCompletionError(formatApiClientError(error));
    }}
    finally {finishForegroundOperation(operation);}
  }

  async function handleRunExit(retry = false) {
    if (historicalSession || continuationAttemptRef.current || completionAttemptRef.current) return;
    const current = loadedSessionRef.current;
    if (!current || current.stale || exitClearFailed || foregroundOperationRef.current ||
        exitConfirmationRef.current?.client!==client || !hasRunAuthority(current)) return;
    let attempt = exitAttemptRef.current;
    if (!retry) {
      if (attempt || !exitConfirm || !runStatus || !hasRunAuthority(current) || !runStatus.can_exit ||
          continuationStatus?.current.session_id!==current.sessionId || !exitConfirmationRef.current ||
          exitConfirmationRef.current.client!==client || JSON.stringify(exitConfirmationRef.current.view)!==JSON.stringify(current.view) ||
          JSON.stringify(exitConfirmationRef.current.authority)!==JSON.stringify({journey:continuationStatus,status:runStatus,completion:completionStatus})) return;
      attempt = freezeRunExit(current.view, runStatus, idempotencyKeyFactory());
      exitAttemptRef.current = attempt; setExitAttempt(attempt); setExitConfirm(false);
    }
    if (!attempt || attempt.sessionId !== current.sessionId || attempt.runId !== current.view.run_context?.run_id) return;
    const operation = beginForegroundOperation("submitting", {clearSession:false});
    if (!operation) return;
    setExitError(null);
    try {
      const status = await client.exitNativeRun(attempt, operation.controller.signal);
      if (!isCurrentOperation(operation) || loadedSessionRef.current !== current) return;
      assertRunStatus(current.view, status);
      if(confirmedExit.current && JSON.stringify(confirmedExit.current)!==JSON.stringify(status))
        throw new ApiClientError("Confirmed exit replay mismatch",{kind:"invalid-response",reason:"CONTRACT_MISMATCH"});
      confirmedExit.current ??= structuredClone(status);setExitProof(confirmedExit.current);
      // A confirmed exit advances the Run. Retain the request until a matching
      // GET confirms the pair; never synthesize a terminal Journey from status.
      setRunAuthority(null);
      const journey=await validateSuccessorRead(current.view,operation.controller.signal);
      if (!isCurrentOperation(operation) || loadedSessionRef.current !== current || !journey) return;
      const completion=await client.getNativeRunCompletion(current.sessionId,operation.controller.signal);
      if (!isCurrentOperation(operation) || loadedSessionRef.current!==current) return;
      assertCompletionAuthorities(current.view,{journey,status,completion});
      setContinuationStatus(journey); setRunStatus(status);
      setCompletionStatus(completion);
      setRunAuthority({owner:current,client,journey,status,completion});
      setExitAttempt(null); exitAttemptRef.current = null;
    } catch (error) {
      if (isCurrentOperation(operation)) {
        setExitError(formatApiClientError(error));
        // Retain the exact path/body/key even for a known rejection after an
        // earlier uncertain dispatch. Reconciliation is always GET-only.
      }
    } finally {finishForegroundOperation(operation);}
  }

  async function reconcileRunExit() {
    const current = loadedSessionRef.current;
    if (!current || foregroundOperationRef.current || exitClearFailed) return;
    const operation = beginForegroundOperation("reading", {clearSession:false});
    if (!operation) return;
    const previouslyBlocked=completionRetryBlockedRef.current;
    if(completionAttemptRef.current) blockCompletionRetry(true);
    setRunAuthority(null); setRunStatus(null);
    try {
      const view = await client.getSessionView(current.sessionId, operation.controller.signal);
      if (!isCurrentOperation(operation)) return;
      assertViewAssociation(current.sessionId, view, nativeExpected.current);
      // bind to the complete previously observed native context as well.
      assertNativeView(view, current.view.run_context);
      const status = await client.getNativeRunStatus(current.sessionId, operation.controller.signal);
      if (!isCurrentOperation(operation) || loadedSessionRef.current !== current) return;
      assertRunStatus(view, status);
      const journey=await validateSuccessorRead(view,operation.controller.signal);
      if (!isCurrentOperation(operation) || loadedSessionRef.current !== current) return;
      if (!journey) return;
      assertJourneyRunStatus(view,journey,status);
      commitLoadedSession(current.sessionId, view, null);
      setRunStatus(status); setExitError(null);

    } catch (error) {
      if (isCurrentOperation(operation)) {
        blockCompletionRetry(previouslyBlocked || (error instanceof ApiClientError && error.reason==="CONTRACT_MISMATCH"));
        setExitError(formatApiClientError(error));
      }
    } finally {finishForegroundOperation(operation);}
  }

  function returnToSetup() {
    if (historicalSession || continuationAttemptRef.current || completionAttemptRef.current) return;
    if ((runStatus?.lifecycle_status !== "terminated" && runStatus?.lifecycle_status !== "completed") || exitAttemptRef.current || foregroundOperationRef.current || !loadedSessionRef.current) return;
    if (!hasRunAuthority(loadedSessionRef.current)) return;
    const cleared = clearSessionRecoveryRecord();
    if (!cleared.ok) {setExitClearFailed(true); return;}
    invalidateForegroundOperation();
    recoveryRecordRef.current = null; setRecoveryRecord(null); nativeExpected.current = null;
    confirmedContinuation.current = null;
    clearSessionUiState();
    setEntryMode("native"); entryModeRef.current = "native";
    setSelectedPlayerCharacterId(""); setCreatedPlayerCharacter(null);
    setProfileId(""); setWorldId(""); setOverrides({}); setRunPresentation({...proposedPresentation});
    choices.current = {profileId:"", worldId:"", overrides:{}}; previousCatalogue.current = null;
    setEligibleCharacters(null); setEligibleError(null); setEligibleRefreshAttempt((n) => n + 1);
    setRunOptions(null); setOptionsError(null); setOptionsRefresh((n) => n + 1);
  }

  // Only the owner-bound, reconciled authority identifies a restored native
  // View as the current visit. Retained arrival text is not reading authority.
  // Recovery already validated the complete association before publishing its
  // View. Preserve that historical identity during the initial background sync,
  // but never carry it across an operation, client, View or failed reconciliation.
  const restoredHistory = restoredReading !== null && loadedSession?.stale === null &&
    restoredReading.owner === loadedSession && restoredReading.client === client &&
    restoredReading.journey === continuationStatus && continuationError === null && exitError === null &&
    restoredReading.journey.current.session_id !== loadedSession.sessionId;
  const readingIdentity = historicalSession !== null ? "historical"
    : loadedSession?.view.run_context
      ? foregroundOperation === null && !historyLoading
        ? runAuthorityReady
          ? runAuthority!.journey.current.session_id === loadedSession.sessionId ? "current" : "historical"
          : restoredHistory ? "historical" : "unconfirmed"
        : "unconfirmed"
      : "current";

  const operationStatus =
    recoveryStorageFailure !== null
      ? "sessionStorage 处于安全锁定状态；不能创建、读取或提交行动。"
      : foregroundOperation === "creating"
        ? "正在创建最小 Player Character；不会自动重发。"
        : foregroundOperation === "entering"
          ? "正在进入 Run；成功后先保存 Session ID，再读取权威 View。"
          : foregroundOperation === "reading"
            ? "正在读取完整权威 View。"
            : foregroundOperation === "recovering"
              ? "正在恢复本标签页已验证的 Session；行动保持锁定。"
              : foregroundOperation === "submitting"
                ? "正在提交行动；不会自动重发。"
                : foregroundOperation === "pending"
                  ? "正在按 retry 指示检查同一 confirmed-202 request。"
                  : foregroundOperation === "refreshing"
                    ? "正在重新读取完整权威 View。"
                    : recoveryInterruption !== null
                      ? "自动恢复已暂停；行动保持锁定，只能手动重试安全 GET。"
                      : mutationAttempt !== null
                        ? "一个操作结果尚未解决；只能手动重试完全相同的操作。"
                        : loadedSession?.stale !== null && loadedSession !== null
                          ? "当前 View 可能 stale；行动保持禁用，等待显式刷新。"
                          : readingIdentity === "historical"
                            ? "正在阅读历史访问；返回当前世界后才能操作当前进度。"
                          : readingIdentity === "unconfirmed"
                            ? "所显示访问与当前旅程的关联尚未确认。"
                          : loadedSession?.view.scenario_status === "ENDED"
                            ? "副本已结束；没有可执行行动。"
                            : loadedSession !== null
                              ? "空闲：当前 View 已确认，可以选择公开行动。"
                              : "空闲：可以选择 Player Character 与副本进入 Run，或手动读取已有 Session。";

  const actionDisabledReason =
    recoveryStorageFailure !== null
      ? "sessionStorage 无法安全访问或更新"
      : foregroundOperation !== null
      ? "前台操作正在进行"
      : loadedSession?.stale !== null && loadedSession !== null
        ? "当前 View 可能 stale，必须先显式刷新"
        : null;
  const isDeterministicDemo =
    import.meta.env.VITE_APP_MODE === "deterministic-demo";
  const openingControlsDisabled =
    historicalSession !== null || historyLoading || continuationAttempt !== null ||
    exitAttempt !== null || completionAttempt !== null || exitClearFailed ||
    foregroundOperation !== null ||
    mutationAttempt !== null ||
    recoveryInterruption !== null ||
    recoveryStorageFailure !== null ||
    recoveryRecord !== null ||
    requiredCatalogRefresh !== null;
  const prePlayControlsDisabled=openingControlsDisabled || openingRecovery.loading || openingRecovery.error !== null || openingRecovery.record !== null;

  const entryControls = <>
      {scenarios?.some(story => story.entry_mode === "SESSION") ?
        <section className="panel" aria-labelledby="short-story-heading">
          <h2 id="short-story-heading">独立短篇</h2>
          <p>独立保存的短篇，不进入旅程，也不消耗旅程资源。</p>
          {scenarios.filter(story => story.entry_mode === "SESSION").map(story =>
            <div key={story.scenario_id}>
              <h3>{story.title}</h3><p>{story.hook}</p>
              <button type="button" disabled={prePlayControlsDisabled} onClick={() => handleStoryStart(story)}>开始《{story.title}》</button>
            </div>)}
        </section> : null}
      <section className="panel" aria-label="进入方式">
        <p>开局天赋确认前会保存恢复入口，刷新后只读核实结果。其他尚未确认并保存的进入请求仅保存在内存中。已保存的进度仅限此标签页。</p>
        <fieldset disabled={prePlayControlsDisabled}>
          <legend>选择进入方式</legend>
          <button type="button" aria-pressed={entryMode === "native"} onClick={() => {setEntryMode("native"); if (!createdPlayerCharacter) setSelectedPlayerCharacterId("");}}>原生 Run 设置</button>
          <button type="button" aria-pressed={entryMode === "legacy"} onClick={() => setEntryMode("legacy")}>传统副本模式</button>
        </fieldset>
        {optionsError ? <p role="alert">{optionsError}</p> : runOptions === null ? <p>正在加载进入选项…</p> : null}
        {runOptions?.native_entry_available === false ? <p>当前环境不支持原生进入，可显式选择传统副本模式。</p> : null}
        <button type="button" disabled={mutationAttempt !== null || foregroundOperation !== null || recoveryRecord !== null || recoveryStorageFailure !== null}
          onClick={() => {setRunOptions(null); setOptionsError(null); setOptionsRefresh((v) => v + 1);}}>刷新可用选项</button>
        {entryMode === "native" && runOptions?.native_entry_available ? <form onSubmit={handleNativeEntry}>
          <fieldset disabled={prePlayControlsDisabled || opening.loading || opening.error !== null || opening.record?.state === "PENDING"}>
            <legend>确认原生 Run 设置</legend>
            <label>选择难度<select value={profileId} onChange={(e) => {setProfileId(e.target.value); setWorldId(""); setOverrides({});}}>
              <option value="">请选择难度</option>{runOptions.profiles.map((p) => <option key={p.profile_ref.profile_id} value={p.profile_ref.profile_id}>{p.label}</option>)}
            </select></label>
            <label>选择起始世界<select value={worldId} disabled={!selectedProfile} onChange={(e) => setWorldId(e.target.value)}>
              <option value="">请选择起始世界</option>{runOptions.entry_worlds.filter((w) => w.eligible_profiles.some((p) => p.profile_id === selectedProfile?.profile_ref.profile_id && p.profile_version === selectedProfile.profile_ref.profile_version)).map((w) => <option key={w.entry_world.entry_world_id} value={w.entry_world.entry_world_id}>{w.title}</option>)}
            </select></label>
            {selectedWorld ? <p>{selectedWorld.hook}</p> : null}
            {selectedProfile?.override_rules.map((r) => <div className="run-override" key={r.parameter}>
              <label><input type="checkbox" checked={r.parameter in overrides} onChange={(e) => setOverrides((old) => {const next = {...old}; if (e.target.checked) next[r.parameter] = String(selectedProfile.defaults[r.parameter]); else delete next[r.parameter]; return next;})}/>调整{objectiveLabels[r.parameter]}</label>
              <label>{objectiveLabels[r.parameter]}<input type="number" min={r.minimum} max={r.maximum} step={r.step} disabled={!(r.parameter in overrides)}
                value={overrides[r.parameter] ?? selectedProfile.defaults[r.parameter]} onChange={(e) => setOverrides({...overrides,[r.parameter]:e.target.value})}/></label>
              <span>允许 {r.minimum}–{r.maximum}，步长 {r.step}</span>
            </div>)}
            <label>世界基调<select value={runPresentation.world_tone} onChange={(e) => setRunPresentation({...runPresentation,world_tone:e.target.value as typeof runPresentation.world_tone})}>{runOptions.presentation_options.world_tone.map((v) => <option key={v}>{v}</option>)}</select></label>
            <label>现实边界<select value={runPresentation.reality_boundary} onChange={(e) => setRunPresentation({...runPresentation,reality_boundary:e.target.value as typeof runPresentation.reality_boundary})}>{runOptions.presentation_options.reality_boundary.map((v) => <option key={v}>{v}</option>)}</select></label>
            <label>人际氛围<select value={runPresentation.relationship_overlay} onChange={(e) => setRunPresentation({...runPresentation,relationship_overlay:e.target.value as typeof runPresentation.relationship_overlay})}>{runOptions.presentation_options.relationship_overlay.map((v) => <option key={v}>{v}</option>)}</select></label>
            <p>确认以上设置后查看五项天赋，再选择两项启程。准备生成后设置固定，表现设置仅影响叙述。</p>
            <button type="submit" disabled={!selectedProfile || !selectedWorld || !selectedPlayerCharacter || Object.entries(overrides).some(([name,value]) => {
              const r=selectedProfile?.override_rules.find((r) => r.parameter === name); const n=Number(value);
              return !r || value.trim()==="" || !Number.isSafeInteger(n) || n % 5 !== 0 || n < r.minimum || n > r.maximum;
            })}>查看开局天赋</button>
          </fieldset>
        </form> : null}
        {entryMode === "native" && opening.loading ? <p role="status">正在读取开局准备…</p> : null}
        {entryMode === "native" && opening.error ? <div role="alert"><p>{opening.error}</p><button type="button" disabled={prePlayControlsDisabled} onClick={opening.retry}>重读开局准备</button></div> : null}
        {openingRecovery.loading ? <p role="status">正在核实开局恢复入口…</p> : null}
        {openingRecovery.error ? <div role="alert"><p>{openingRecovery.error}</p><button type="button" disabled={openingControlsDisabled} onClick={openingRecovery.retry}>重读开局恢复</button></div> : null}
        {(entryMode === "native" || openingRecovery.record) && openingRecord && recoveryRecord === null ? <OpeningTalentChoices key={openingRecord.preparation_id}
          record={openingRecord} worlds={runOptions?.entry_worlds} disabled={openingControlsDisabled || openingRecovery.loading || openingRecovery.error !== null} onConfirm={handleOpeningConfirmation}/> : null}
      </section>

      <section className="panel" aria-labelledby="scenario-heading">
        <h2 id="scenario-heading">选择公开副本</h2>
        {scenarios === null && scenarioError === null ? (
          <p role="status" aria-live="polite">
            正在加载公开副本…
          </p>
        ) : null}
        {scenarioError !== null ? (
          <div role="alert">
            <p>{scenarioError.message}</p>
            {scenarioError.retryable ? (
              <button type="button" onClick={handleScenarioRefresh}>
                重试公开副本 GET
              </button>
            ) : (
              <p>公开副本响应不符合合同，选择保持锁定。</p>
            )}
          </div>
        ) : null}
        {scenarios?.length === 0 ? <p>当前没有可公开游玩的副本。</p> : null}
        {scenarios !== null && scenarios.length > 0 ? (
          <fieldset disabled={prePlayControlsDisabled}>
            <legend className="sr-only">选择公开副本</legend>
            <label htmlFor="scenario">副本</label>
            <select
              id="scenario"
              value={selectedScenarioId}
              onChange={(event) => handleScenarioChange(event.target.value)}
            >
              {scenarios.filter(scenario => scenario.entry_mode !== "SESSION").map((scenario) => (
                <option key={scenario.scenario_id} value={scenario.scenario_id}>
                  {scenario.title}
                </option>
              ))}
            </select>

            {selectedScenario === undefined ? null : (
              <div className="scenario-copy">
                <h3>{selectedScenario.title}</h3>
                <p>{selectedScenario.hook}</p>
                <p>内容版本：{selectedScenario.content_version}</p>
              </div>
            )}
          </fieldset>
        ) : null}
        {requiredCatalogRefresh === "scenario" ? (
          <button type="button" onClick={handleScenarioRefresh}>
            刷新公开副本后重新选择
          </button>
        ) : null}
      </section>

      <section className="panel" aria-labelledby="character-heading">
        <h2 id="character-heading">选择 Player Character</h2>
        {eligibleCharacters === null && eligibleError === null ? (
          <p role="status" aria-live="polite">
            正在加载可进入 Run 的 Player Character…
          </p>
        ) : null}
        {eligibleError !== null ? (
          <div role="alert">
            <p>{eligibleError.message}</p>
            {eligibleError.retryable ? (
              <button type="button" onClick={handleEligibleRefresh}>
                重试 eligible Player Character GET
              </button>
            ) : (
              <p>Player Character 响应不符合合同，选择保持锁定。</p>
            )}
          </div>
        ) : null}
        {eligibleTruncated ? (
          <p className="supporting-copy">
            仅显示服务器按顺序返回的前 32 个可选 Player Character；没有总数或分页。
          </p>
        ) : null}
        {eligibleCharacters !== null && eligibleCharacters.length > 0 ? (
          <fieldset disabled={prePlayControlsDisabled}>
            <legend className="sr-only">选择 eligible Player Character</legend>
            <label htmlFor="player-character">Player Character</label>
            <select
              id="player-character"
              value={selectedPlayerCharacterId}
              onChange={(event) =>
                setSelectedPlayerCharacterId(event.target.value)
              }
            >
              {entryMode === "native" ? <option value="">请选择角色</option> : null}
              {eligibleCharacters.map((character) => (
                <option
                  key={character.player_character_id.value}
                  value={character.player_character_id.value}
                >
                  {character.player_character_id.value} · {character.contract_version} · revision {character.record_revision.value} · {character.lifecycle}
                </option>
              ))}
            </select>
          </fieldset>
        ) : null}
        {eligibleCharacters?.length === 0 &&
        createdPlayerCharacter === null &&
        scenarios !== null &&
        scenarios.length > 0 &&
        scenarioError === null ? (
          <form onSubmit={handlePlayerCharacterCreate}>
            <fieldset disabled={prePlayControlsDisabled}>
              <legend className="sr-only">创建最小 Player Character</legend>
              <p>服务器当前没有返回可进入 Run 的 Player Character。</p>
              <button type="submit">
                {foregroundOperation === "creating"
                  ? "正在创建 Player Character…"
                  : "创建最小 Player Character"}
              </button>
            </fieldset>
          </form>
        ) : null}
        {createdPlayerCharacter === null ? null : (
          <p className="supporting-copy">
            已选择服务器返回的创建结果 {createdPlayerCharacter.player_character_id.value}（revision {createdPlayerCharacter.record_revision.value}，{createdPlayerCharacter.lifecycle}）。Run entry 将再次由服务器校验；这不是后续当前 eligibility 保证。
          </p>
        )}
        {requiredCatalogRefresh === "eligible" ? (
          <button type="button" onClick={handleEligibleRefresh}>
            刷新 eligible Player Character 后重新选择
          </button>
        ) : null}
        {selectedPlayerCharacter === undefined ||
        selectedScenario === undefined || entryMode !== "legacy" ? null : (
          <form onSubmit={handleRunEntry}>
            <fieldset disabled={prePlayControlsDisabled}>
              <legend className="sr-only">进入 Run</legend>
              <button type="submit">
                {foregroundOperation === "entering" ? "正在进入 Run…" : "进入 Run"}
              </button>
            </fieldset>
          </form>
        )}
      </section>

  </>;

  const manualRecoveryControls = (
      <section className="panel" aria-labelledby="restore-heading">
        <h2 id="restore-heading">手动读取已有 Session</h2>
        <form onSubmit={handleManualRead}>
          <fieldset
            disabled={
              historicalSession !== null || historyLoading || continuationAttempt !== null ||
              foregroundOperation !== null ||
              exitAttempt !== null || completionAttempt !== null || exitClearFailed ||
              mutationAttempt !== null ||
              recoveryInterruption !== null ||
              recoveryStorageFailure !== null
            }
          >
            <legend className="sr-only">手动读取 Session</legend>
            <label htmlFor="session-id">Session ID</label>
            <input
              id="session-id"
              value={manualSessionId}
              onChange={(event) => setManualSessionId(event.target.value)}
              autoComplete="off"
              required
            />
            <button
              type="submit"
              disabled={
                foregroundOperation !== null ||
                exitAttempt !== null || completionAttempt !== null || exitClearFailed ||
                mutationAttempt !== null ||
                recoveryInterruption !== null ||
                recoveryStorageFailure !== null ||
                manualSessionId.trim() === ""
              }
            >
              {foregroundOperation === "reading"
                ? "正在读取…"
                : "读取 PlayerSessionView"}
            </button>
          </fieldset>
        </form>
      </section>

  );

  return (
    <main>
      <header className="hero">
        <p className="eyebrow">Public Web Client</p>
        <h1>Deviation Protocol</h1>
        <p>{loadedSession?.view.encounter || loadedSession?.view.relationship ? "故事会在你做出选择后继续。" : "所有行动控件均来自最新的权威 action_affordances。"}</p>
        {isDeterministicDemo ? (
          <p className="demo-warning">{DETERMINISTIC_DEMO_WARNING}</p>
        ) : null}
      </header>

      <p className="operation-status" role="status" aria-live="polite">
        {operationStatus}
      </p>

      {loadedSession === null ? entryControls : null}

      {mutationAttempt === null ? null : (
        <section className="stale-warning" role="alert" aria-labelledby="mutation-retry-heading">
          <h2 id="mutation-retry-heading">操作结果尚未解决</h2>
          <p>
            {mutationAttempt.kind === "native-entry" && mutationAttempt.retainedResponse ? "进入已确认，进度尚待保存；重试保存不会重新进入。" : null}
            {mutationAttempt.kind === "run-entry" &&
            mutationAttempt.entrySuccessAwaitingStorage
              ? "Run entry 已成功，但 Session ID 尚未安全保存。清除存储锁定后，只能用完全相同的操作进行 replay。"
              : MUTATION_UNCERTAIN_MESSAGE}
          </p>
          {mutationAttempt.kind === "native-entry" && mutationAttempt.retainedResponse ? <button type="button" onClick={handleNativeStorageRetry}>重试保存进度</button> : null}
          {mutationAttempt.kind === "run-entry" ? (
            <p>{RUN_DISCOVERY_LIMIT_MESSAGE}</p>
          ) : null}
          <button
            type="button"
            onClick={handleMutationRetry}
            disabled={
              mutationAttempt.inFlight ||
              foregroundOperation !== null ||
              recoveryStorageFailure !== null
            }
          >
            {mutationAttempt.inFlight
              ? "相同操作正在发送…"
              : "手动重试完全相同的操作"}
          </button>
        </section>
      )}

      {loadedSession === null ? manualRecoveryControls : null}

      <div aria-live="polite">
        {loadedSession !== null ? (
          <p className="session-confirmation">
            当前 Session：{loadedSession.sessionId}
          </p>
        ) : null}
        {createdSessionWithoutView !== null ? (
          <div role="status" className="session-confirmation">
            <p>
              已进入 Run 并保存 Session：{createdSessionWithoutView}，但 PlayerSessionView 未加载。
            </p>
            <button type="button" onClick={() => void handleEnteredSessionViewRetry()}>
              重试读取权威 View
            </button>
          </div>
        ) : null}
        {operationError !== null ? <p role="alert">{operationError}</p> : null}
        {recoveryStorageFailure === null &&
        recoveryInterruption === null &&
        recoveryRecord !== null ? (
          <button type="button" disabled={historicalSession !== null || historyLoading || continuationAttempt !== null || exitAttempt !== null || completionAttempt !== null || exitClearFailed} onClick={handleExplicitSessionClear}>
            清除本标签页 Session
          </button>
        ) : null}
      </div>

      {recoveryInterruption === null ? null : (
        <section
          className="stale-warning"
          role="alert"
          aria-labelledby="recovery-interrupted-heading"
        >
          <h2 id="recovery-interrupted-heading">自动恢复已暂停</h2>
          <p>{recoveryInterruption.message}</p>
          <button type="button" onClick={handleRecoveryRetry}>
            手动重试安全 GET
          </button>
          <button type="button" onClick={handleExplicitSessionClear}>
            清除本标签页 Session
          </button>
        </section>
      )}

      {recoveryStorageFailure === null ? null : (
        <section
          className="stale-warning"
          role="alert"
          aria-labelledby="recovery-storage-failure-heading"
        >
          <h2 id="recovery-storage-failure-heading">
            sessionStorage 安全锁定
          </h2>
          <p>{RECOVERY_STORAGE_FAILURE_MESSAGE}</p>
          <p>失败边界：{recoveryStorageFailure.failure.operation}</p>
          {pendingContinuationRecovery ? <button type="button" onClick={retryContinuationStorage}>重试保存已确认的下一世界</button> : null}
          <button type="button" onClick={handleStorageFailureClearRetry}>
            重试安全清除恢复记录
          </button>
        </section>
      )}

      {recoveryStorageFailure !== null ||
      loadedSession?.stale === null ||
      loadedSession === null ? null : (
        <section className="stale-warning" role="alert" aria-labelledby="stale-heading">
          <h2 id="stale-heading">View stale / 行动状态需要确认</h2>
          <p>{loadedSession.stale.message}</p>
          <button
            type="button"
            onClick={() => void handleExplicitViewRefresh()}
            disabled={foregroundOperation !== null}
          >
            {foregroundOperation === "refreshing"
              ? "正在刷新权威 View…"
              : "显式刷新当前权威 View"}
          </button>
        </section>
      )}

      {loadedSession?.view.run_context ? <section className="panel" aria-label="世界续接与历史">
        {historyLoading && !historicalSession ? <button type="button" onClick={()=>void navigateHistory("current")}>返回当前世界</button> : null}
        {historicalSession ? <>
          <p>正在阅读旅程历史；这里只读，不会改变当前进度。</p>
          {historicalJourney?.arrival ? <div aria-label="历史抵达说明"><p>{historicalJourney.arrival.previous_ending_title}</p><p>{historicalJourney.arrival.entry_notice}</p></div> : null}
          {historicalJourney?.predecessor ? <button type="button" disabled={foregroundOperation !== null} onClick={()=>void navigateHistory()}>查看上一世界历史</button> : null}
          {historicalJourney?.successor ? <button type="button" disabled={foregroundOperation !== null} onClick={()=>void navigateHistory("next")}>查看下一段旅程</button> : null}
          <button type="button" disabled={foregroundOperation !== null && !historyLoading} onClick={()=>void navigateHistory("current")}>返回当前世界</button>
        </> : <>
          {continuationStatus?.session_id === loadedSession.sessionId && continuationStatus.arrival ?
            <div aria-label="抵达说明">
              <p>{continuationStatus.path.visit?.world_id === "world.fog_station" ? "上次访问结局：" : "上一世界结局："}{continuationStatus.arrival.previous_ending_title}（{continuationStatus.arrival.previous_ending_status}）</p>
              <p>{continuationStatus.arrival.entry_notice}</p>
            </div> : null}
          {continuationStatus?.predecessor ? <button type="button" disabled={foregroundOperation !== null || continuationAttempt !== null || exitAttempt !== null || completionAttempt !== null}
            onClick={()=>void navigateHistory()}>查看上一世界历史</button> : null}
          {runAuthorityReady && continuationStatus?.next_transition ? <button type="button" disabled={!runAuthorityReady || foregroundOperation !== null || continuationAttempt !== null || exitAttempt !== null || completionAttempt !== null}
            onClick={()=>{if(!hasRunAuthority(loadedSession))return;setExitConfirm(false);setCompletionConfirm(null);
              continuationConfirmationRef.current={view:structuredClone(loadedSession.view),authority:structuredClone({journey:continuationStatus,status:runStatus,completion:completionStatus}),client};setContinuationConfirm(true);}}>继续当前旅程</button> : null}
          {continuationConfirm ? <div role="dialog" aria-label="确认继续旅程">
            <p>将进入《{continuationStatus?.next_transition?.world_title}》的{continuationStatus?.next_transition?.region_title}。{continuationStatus?.next_transition?.notice}</p>
            <button type="button" disabled={!runAuthorityReady || foregroundOperation !== null} onClick={()=>void handleContinuation()}>{continuationStatus?.next_transition?.kind === "fog_patrol" ? "确认前往巡路风口" : continuationStatus?.next_transition?.kind === "regional_revisit" ? "确认进入核验档案室" : "确认进入下一世界"}</button>
            <button type="button" onClick={()=>setContinuationConfirm(false)}>取消继续</button>
          </div> : null}
          {continuationAttempt ? <>
            <p>续接请求尚未确认。可以读取续接状态，或重试原请求。</p>
            <button type="button" disabled={!runAuthorityReady || foregroundOperation !== null} onClick={()=>void handleContinuation(true)}>重试原续接请求</button>
          </> : null}
          {continuationAttempt || continuationStatus?.successor || continuationError ?
            <button type="button" disabled={foregroundOperation !== null} onClick={()=>void reconcileContinuation()}>读取续接状态</button> : null}
        </>}
        {continuationError ? <p role="alert">{continuationError}</p> : null}
      </section> : null}

      {!historicalSession && loadedSession?.view.run_context && loadedSession.view.scenario_status === "ENDED" ? (
        <section className="panel" aria-label="旅程状态">
          {runAuthorityReady && (runStatus?.lifecycle_status === "terminated" || runStatus?.lifecycle_status === "completed") && !completionAttempt && !exitAttempt ? <>
            {runStatus?.lifecycle_status==="completed" ? <><p>{completionStatus?.completion?.title}</p><p>{completionStatus?.completion?.notice}</p></> : <p>本次旅程已永久结束。结局与历史仍可阅读。</p>}
            {exitClearFailed ? <p role="alert">恢复记录清除失败；请重试。清除成功前不能进入新旅程。</p> : null}
            <button type="button" disabled={foregroundOperation !== null} onClick={returnToSetup}>
              {exitClearFailed ? "重试清除并返回设置" : "返回设置"}
            </button>
          </> : <>
            <button type="button" disabled={!runAuthorityReady || !runStatus?.can_exit || exitAttempt !== null || completionAttempt !== null || continuationAttempt !== null || foregroundOperation !== null || loadedSession.stale !== null}
              onClick={() => {if(!hasRunAuthority(loadedSession))return;setContinuationConfirm(false);setCompletionConfirm(null);
                setExitOwner(client);exitConfirmationRef.current={view:structuredClone(loadedSession.view),authority:structuredClone({journey:continuationStatus,status:runStatus,completion:completionStatus}),client};setExitConfirm(true);}}>结束本次旅程</button>
            {exitConfirm ? <div role="dialog" aria-label="确认结束旅程">
              <p>本次旅程将永久结束，结局与历史保留。再次进入会创建新的旅程，不是继续当前旅程。</p>
              <button type="button" disabled={!runAuthorityReady || foregroundOperation !== null} onClick={() => void handleRunExit()}>确认永久结束</button>
              <button type="button" onClick={() => setExitConfirm(false)}>取消结束</button>
            </div> : null}
            {exitAttempt ? <>
              <p>结束请求尚未确认。可读取旅程状态，或手动重试原请求。</p>
              <button type="button" disabled={!runAuthorityReady || foregroundOperation !== null || exitOwner!==client} onClick={() => void handleRunExit(true)}>重试原结束请求</button>
            </> : null}
          </>}
          {runAuthorityReady && completionStatus?.can_complete && !completionAttempt ? <>
            <p>待确认：{completionStatus.offer?.notice}</p>
            <button type="button" disabled={foregroundOperation!==null || exitAttempt!==null || continuationAttempt!==null}
              onClick={()=>{if(!runAuthority?.status || !runAuthority.completion || !hasRunAuthority(loadedSession))return;
                setExitConfirm(false);setContinuationConfirm(false);completionClientRef.current=client;setCompletionOwner(client);
                setCompletionConfirm(freezeRunCompletion(loadedSession.view,{journey:runAuthority.journey,status:runAuthority.status,completion:runAuthority.completion},idempotencyKeyFactory()));}}>完成本次旅程</button>
          </> : null}
          {completionConfirm ? <div role="dialog" aria-label="确认完成旅程">
            <p>{completionConfirm.authority.completion.offer?.notice}</p>
            <button type="button" disabled={!runAuthorityReady || foregroundOperation!==null} onClick={()=>void handleCompletion()}>确认结案并完成旅程</button>
            <button type="button" onClick={()=>setCompletionConfirm(null)}>取消完成</button>
          </div> : null}
          {completionAttempt ? <><p>完成请求尚未确认。读取状态不会重发请求。</p>
            <button type="button" disabled={foregroundOperation!==null || completionOwner!==client || completionRetryBlocked || (completionProof!==null && !runAuthorityReady)} onClick={()=>void handleCompletion(true)}>重试原完成请求</button></> : null}
          {completionError ? <p role="alert">{completionError}</p> : null}
          {exitError ? <p role="alert">{exitError}</p> : null}
          <button type="button" disabled={foregroundOperation !== null || exitClearFailed} onClick={() => void reconcileRunExit()}>读取旅程状态</button>
        </section>
      ) : null}

      {recoveryStorageFailure !== null || loadedSession === null ? null : (
        <SessionReading
          key={(historicalSession ?? loadedSession).sessionId}
          view={(historicalSession ?? loadedSession).view}
          staleKind={(historicalSession ?? loadedSession).stale?.kind ?? null}
          readingIdentity={readingIdentity}
          journeyRecap={(historicalSession ?? loadedSession).view.run_context ? <JourneyRecap
            client={client} view={(historicalSession ?? loadedSession).view}
            journey={historicalSession ? historicalJourney : continuationStatus}
            ready={readingIdentity !== "unconfirmed" && foregroundOperation === null && !historyLoading &&
              (historicalSession ?? loadedSession).stale === null && continuationError === null}
          /> : undefined}
        />
      )}

      {(historicalSession ?? loadedSession)?.view.run_context ? <ConfirmedOpeningTalents client={client} sessionId={(historicalSession ?? loadedSession)!.sessionId}/> : null}
      {historicalSession || recoveryStorageFailure !== null || loadedSession === null ? null : (
        <DynamicNarrativeEvidenceSummary
          response={committedActionResponse}
          loaded={loadedSession}
        />
      )}

      {historicalSession || recoveryStorageFailure !== null || loadedSession === null ? null : (
        <ActionPanel
          view={loadedSession.view}
          disabled={
            foregroundOperation !== null || loadedSession.stale !== null ||
            continuationAttempt !== null || exitAttempt !== null ||
            (Boolean(loadedSession.view.run_context) &&
              (continuationError !== null || continuationStatus?.session_id !== loadedSession.sessionId ||
               continuationStatus.path.session_state_version !== loadedSession.view.metadata.state_version ||
               continuationStatus.current.session_id !== loadedSession.sessionId || continuationStatus.lifecycle_status !== "active"))
          }
          disabledReason={actionDisabledReason}
          onSubmit={(intent) => void handleAction(intent)}
          onSubmitSuggestion={(suggestion) =>
            void handleSuggestedAction(suggestion)
          }
        />
      )}
      {loadedSession !== null ? <>{loadedSession.view.encounter ? null : entryControls}{manualRecoveryControls}</> : null}
    </main>
  );
}

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { publicApiClient, type PublicApiClient } from "./api/client";
import { ApiClientError, formatApiClientError } from "./api/errors";
import {
  actionRequestSchema,
  idempotencyKeySchema,
  minimalPlayerCharacterCreationRequestSchema,
  runEntryRequestSchema,
  sessionPathIdSchema,
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

type MutationAttempt = PlayerCharacterCreateAttempt | RunEntryAttempt;

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
  "已保存的同标签页恢复记录在服务器返回 404 后失效，现已清除。请创建 Session 或手动读取其他 Session。";
const RECOVERY_IDENTITY_MISMATCH_MESSAGE =
  "服务器返回的恢复身份与已保存记录不匹配，原恢复记录已失效并清除。请创建 Session 或手动读取其他 Session。";
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

function ViewSummary({ loaded }: { loaded: LoadedSession }) {
  const { view, stale } = loaded;
  const latestNarrative = view.recent_narrative_texts.at(-1);

  return (
    <article
      className={`view-summary${stale === null ? "" : " view-summary-stale"}`}
      aria-labelledby="session-view-heading"
    >
      <header>
        <p className="eyebrow">PlayerSessionView</p>
        <h2 id="session-view-heading">{view.presentation.title}</h2>
        <p>{view.presentation.scene_summary}</p>
        {stale === null ? (
          <p className="freshness-label">权威 View：当前</p>
        ) : (
          <p className="freshness-label stale-label">
            权威 View：可能 stale（{stale.kind}）
          </p>
        )}
      </header>

      <dl className="metadata-grid">
        <div>
          <dt>Session ID</dt>
          <dd>{view.metadata.session_id}</dd>
        </div>
        <div>
          <dt>角色</dt>
          <dd>{view.metadata.character_display_name}</dd>
        </div>
        <div>
          <dt>状态版本</dt>
          <dd>{view.metadata.state_version}</dd>
        </div>
        <div>
          <dt>副本状态</dt>
          <dd>{view.scenario_status}</dd>
        </div>
      </dl>

      <section aria-labelledby="scene-heading">
        <h3 id="scene-heading">当前场景：{view.presentation.scene_title}</h3>
        <p>
          Frame {view.narrative_frame.frame_id} · 停止条件：
          <strong>{view.narrative_frame.stop_condition}</strong>
        </p>
      </section>

      <section aria-labelledby="narrative-heading">
        <h3 id="narrative-heading">当前公开正文</h3>
        <p>{latestNarrative ?? "当前尚无已接受的叙事正文。"}</p>
      </section>

      <section aria-labelledby="suggestions-heading">
        <h3 id="suggestions-heading">建议行动（只读）</h3>
        <p className="supporting-copy">
          这些叙事提示不可直接提交；可执行控件只来自 action_affordances。
        </p>
        {view.narrative_frame.suggested_actions.length === 0 ? (
          <p>当前 Frame 没有建议行动。</p>
        ) : (
          <ul>
            {view.narrative_frame.suggested_actions.map((action) => (
              <li key={action.action_id}>{action.label_hint}</li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="player-state-heading">
        <h3 id="player-state-heading">公开玩家状态</h3>
        <dl className="compact-list">
          {view.player_state.attributes.map(([name, value]) => (
            <div key={name}>
              <dt>{name}</dt>
              <dd>{value}</dd>
            </div>
          ))}
          {view.player_state.resources.map((resource) => (
            <div key={resource.resource_id}>
              <dt>{resource.resource_id}</dt>
              <dd>
                {resource.current} / {resource.maximum}
              </dd>
            </div>
          ))}
        </dl>
        <p>
          背包 {view.player_state.inventory.length} · 装备
          {view.player_state.equipped_items.length} · 技能
          {view.player_state.skills.length} · 可见 NPC
          {view.player_state.visible_npcs.length}
        </p>
      </section>

      <section aria-labelledby="clock-heading">
        <h3 id="clock-heading">公开时钟</h3>
        {view.public_clocks.length === 0 ? (
          <p>当前没有公开时钟。</p>
        ) : (
          <ul>
            {view.public_clocks.map((clock) => (
              <li key={clock.clock_id}>
                {clock.clock_id}：{clock.value} / {clock.maximum}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="memory-heading">
        <h3 id="memory-heading">长期记忆</h3>
        <p>
          {view.player_memory.complete ? "索引完整" : "索引可能不完整"} · 副本
          {view.player_memory.total_scenario_records} · NPC
          {view.player_memory.total_npc_records} · 重要经历
          {view.player_memory.total_significant_experiences}
        </p>
      </section>

      <section aria-labelledby="recent-heading">
        <h3 id="recent-heading">近期已接受正文</h3>
        {view.recent_narrative_texts.length === 0 ? (
          <p>暂无。</p>
        ) : (
          <ol>
            {view.recent_narrative_texts.map((text, index) => (
              <li key={`${index}-${text.slice(0, 24)}`}>{text}</li>
            ))}
          </ol>
        )}
      </section>

      {view.ending_status !== null && view.presentation.ending != null ? (
        <section className="ending" aria-labelledby="ending-heading">
          <p className="eyebrow">{view.ending_status}</p>
          <h3 id="ending-heading">{view.presentation.ending.title}</h3>
          <p>{view.presentation.ending.summary}</p>
          <p>Ending ID：{view.ending_id}</p>
        </section>
      ) : null}
    </article>
  );
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
              onChange={(event) => setText(event.target.value)}
              aria-describedby={`${fieldPrefix}-limit`}
              aria-invalid={inputTooLong}
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
          <p role="alert">{validationError}</p>
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
      <p className="eyebrow">action_affordances · {affordances.mode}</p>
      <h2 id="actions-heading">当前可执行行动</h2>
      <p className="supporting-copy">
        这里只提交当前权威 View 明确提供的行动；服务器 Gateway 与策略仍是最终权威。
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
    operationGenerationRef.current += 1;
    const operation = foregroundOperationRef.current;
    operation?.controller.abort();
    foregroundOperationRef.current = null;
    setForegroundOperation(null);
  }, []);

  const clearSessionUiState = useCallback(() => {
    loadedSessionRef.current = null;
    setLoadedSession(null);
    setCreatedSessionWithoutView(null);
    setManualSessionId("");
    setOperationError(null);
    setRecoveryInterruption(null);
  }, []);

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
      return true;
    },
    [enterRecoveryStorageFailure],
  );

  const clearRecoveryForSessionTransition = useCallback((): boolean => {
    const result = clearSessionRecoveryRecord();
    if (!result.ok) {
      enterRecoveryStorageFailure(result.failure);
      return false;
    }
    recoveryRecordRef.current = null;
    setRecoveryRecord(null);
    loadedSessionRef.current = null;
    setLoadedSession(null);
    setRecoveryStorageFailure(null);
    return true;
  }, [enterRecoveryStorageFailure]);

  const explicitlyAbandonSession = useCallback((): boolean => {
    invalidateForegroundOperation();
    const result = clearSessionRecoveryRecord();
    recoveryRecordRef.current = null;
    setRecoveryRecord(null);
    clearSessionUiState();
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
    void client
      .listScenarios(controller.signal)
      .then((catalog) => {
        if (!active) {
          return;
        }
        setScenarios(catalog.scenarios);
        const firstScenario = catalog.scenarios[0];
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
        setSelectedPlayerCharacterId(
          collection.eligible_player_characters[0]?.player_character_id.value ??
            "",
        );
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
      foregroundOperationRef.current?.id === operation.id &&
      !operation.controller.signal.aborted;

    const transition = (kind: ForegroundOperationKind) => {
      if (isCurrent()) {
        setForegroundOperation(kind);
      }
    };

    const readAndCommitAuthoritativeView = async () => {
      transition("refreshing");
      const restoredView = await client.getSessionView(
        record.session_id,
        operation.controller.signal,
      );
      if (!isCurrent()) {
        return;
      }
      if (!persistRecoveryRecord(record.session_id)) {
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
    };

    void (async () => {
      await Promise.resolve();
      if (!isCurrent()) {
        return;
      }
      loadedSessionRef.current = null;
      setLoadedSession(null);
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
            await readAndCommitAuthoritativeView();
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
          if (explicitlyAbandonSession()) {
            setOperationError(RECOVERY_NOT_FOUND_MESSAGE);
          }
          return;
        }
        if (
          error instanceof ApiClientError &&
          error.kind === "identity-mismatch"
        ) {
          if (explicitlyAbandonSession()) {
            setOperationError(RECOVERY_IDENTITY_MISMATCH_MESSAGE);
          }
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

  function handleScenarioChange(scenarioId: string) {
    setSelectedScenarioId(scenarioId);
  }

  function commitLoadedSession(
    sessionId: string,
    view: PlayerSessionView,
  ) {
    const next = { sessionId, view, stale: null };
    loadedSessionRef.current = next;
    setLoadedSession(next);
  }

  function persistAndCommitLoadedSession(
    sessionId: string,
    view: PlayerSessionView,
  ): boolean {
    if (!persistRecoveryRecord(sessionId)) {
      return false;
    }
    commitLoadedSession(sessionId, view);
    return true;
  }

  function beginForegroundOperation(
    kind: ForegroundOperationKind,
    options: { clearSession: boolean },
  ): ForegroundOperation | null {
    if (foregroundOperationRef.current !== null) {
      return null;
    }
    if (recoveryStorageFailure !== null) {
      return null;
    }
    if (options.clearSession && !clearRecoveryForSessionTransition()) {
      return null;
    }
    const operation = {
      controller: new AbortController(),
      id: operationGenerationRef.current + 1,
    };
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
    persistAndCommitLoadedSession(sessionId, restoredView);
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

      const entered = await client.enterRun(
        attempt.exactFrozenBody,
        attempt.idempotencyKey,
        operation.controller.signal,
      );
      if (!isCurrentOperation(operation)) {
        return;
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
      selectedScenario === undefined ||
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
    explicitlyAbandonSession();
  }

  function handleStorageFailureClearRetry() {
    explicitlyAbandonSession();
  }

  async function handleActionRequest(requestFactory: () => ActionRequest) {
    const current = loadedSessionRef.current;
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
        await readAndCommitCurrentView(operation, current.sessionId);
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
        if (
          requestStatus.status === "COMMITTED" ||
          requestStatus.status === "STALE"
        ) {
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
        if (explicitlyAbandonSession()) {
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
  const prePlayControlsDisabled =
    foregroundOperation !== null ||
    mutationAttempt !== null ||
    recoveryInterruption !== null ||
    recoveryStorageFailure !== null ||
    recoveryRecord !== null ||
    requiredCatalogRefresh !== null;

  return (
    <main>
      <header className="hero">
        <p className="eyebrow">Public Web Client</p>
        <h1>Deviation Protocol</h1>
        <p>所有行动控件均来自最新的权威 action_affordances。</p>
        {isDeterministicDemo ? (
          <p className="demo-warning">{DETERMINISTIC_DEMO_WARNING}</p>
        ) : null}
      </header>

      <p className="operation-status" role="status" aria-live="polite">
        {operationStatus}
      </p>

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
              {scenarios.map((scenario) => (
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
        selectedScenario === undefined ? null : (
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

      {mutationAttempt === null ? null : (
        <section className="stale-warning" role="alert" aria-labelledby="mutation-retry-heading">
          <h2 id="mutation-retry-heading">操作结果尚未解决</h2>
          <p>
            {mutationAttempt.kind === "run-entry" &&
            mutationAttempt.entrySuccessAwaitingStorage
              ? "Run entry 已成功，但 Session ID 尚未安全保存。清除存储锁定后，只能用完全相同的操作进行 replay。"
              : MUTATION_UNCERTAIN_MESSAGE}
          </p>
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

      <section className="panel" aria-labelledby="restore-heading">
        <h2 id="restore-heading">手动读取已有 Session</h2>
        <form onSubmit={handleManualRead}>
          <fieldset
            disabled={
              foregroundOperation !== null ||
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
          <button type="button" onClick={handleExplicitSessionClear}>
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

      {recoveryStorageFailure !== null || loadedSession === null ? null : (
        <ViewSummary loaded={loadedSession} />
      )}

      {recoveryStorageFailure !== null || loadedSession === null ? null : (
        <ActionPanel
          view={loadedSession.view}
          disabled={
            foregroundOperation !== null || loadedSession.stale !== null
          }
          disabledReason={actionDisabledReason}
          onSubmit={(intent) => void handleAction(intent)}
          onSubmitSuggestion={(suggestion) =>
            void handleSuggestedAction(suggestion)
          }
        />
      )}
    </main>
  );
}

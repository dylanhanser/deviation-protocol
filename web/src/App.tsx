import { useEffect, useRef, useState, type FormEvent } from "react";

import { publicApiClient, type PublicApiClient } from "./api/client";
import { ApiClientError, formatApiClientError } from "./api/errors";
import {
  actionRequestSchema,
  sessionPathIdSchema,
  type ActionRequest,
  type PlayerSessionView,
  type PublicActionAffordance,
  type PublicPlayableActionType,
  type PublicScenarioDescription,
} from "./api/schemas";

interface ActionIdentity {
  turnId: string;
  clientRequestId: string;
}

type PollWait = (milliseconds: number, signal: AbortSignal) => Promise<void>;

interface AppProps {
  client?: PublicApiClient;
  requestIdFactory?: () => string;
  actionIdentityFactory?: () => ActionIdentity;
  pollWait?: PollWait;
}

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

type ForegroundOperationKind =
  | "creating"
  | "reading"
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
}: {
  view: PlayerSessionView;
  disabled: boolean;
  disabledReason: string | null;
  onSubmit: (intent: ActionIntent) => void;
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
  requestIdFactory = newOpaqueId,
  actionIdentityFactory = newActionIdentity,
  pollWait = waitForPollingDelay,
}: AppProps) {
  const [scenarios, setScenarios] = useState<PublicScenarioDescription[] | null>(
    null,
  );
  const [scenarioError, setScenarioError] = useState<string | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState("");
  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [foregroundOperation, setForegroundOperation] =
    useState<ForegroundOperationKind | null>(null);
  const [manualSessionId, setManualSessionId] = useState("");
  const [loadedSession, setLoadedSession] = useState<LoadedSession | null>(null);
  const [createdSessionWithoutView, setCreatedSessionWithoutView] = useState<
    string | null
  >(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const foregroundOperationRef = useRef<ForegroundOperation | null>(null);
  const operationGenerationRef = useRef(0);
  const loadedSessionRef = useRef<LoadedSession | null>(null);
  const previousClientRef = useRef(client);

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
        if (firstScenario !== undefined) {
          setSelectedScenarioId(firstScenario.scenario_id);
          setSelectedRoleId(firstScenario.default_character_definition_id);
        }
      })
      .catch((error: unknown) => {
        if (
          !active ||
          (error instanceof ApiClientError && error.kind === "aborted")
        ) {
          return;
        }
        setScenarioError(formatApiClientError(error));
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [client]);

  useEffect(() => {
    if (previousClientRef.current !== client) {
      operationGenerationRef.current += 1;
      foregroundOperationRef.current?.controller.abort();
      foregroundOperationRef.current = null;
      setForegroundOperation(null);
      loadedSessionRef.current = null;
      setLoadedSession(null);
      setCreatedSessionWithoutView(null);
      setOperationError(null);
      previousClientRef.current = client;
    }
  }, [client]);

  useEffect(() => {
    return () => {
      operationGenerationRef.current += 1;
      foregroundOperationRef.current?.controller.abort();
      foregroundOperationRef.current = null;
      loadedSessionRef.current = null;
    };
  }, []);

  const selectedScenario = scenarios?.find(
    (scenario) => scenario.scenario_id === selectedScenarioId,
  );

  function handleScenarioChange(scenarioId: string) {
    setSelectedScenarioId(scenarioId);
    const scenario = scenarios?.find((item) => item.scenario_id === scenarioId);
    setSelectedRoleId(scenario?.default_character_definition_id ?? "");
  }

  function clearLoadedSession() {
    loadedSessionRef.current = null;
    setLoadedSession(null);
  }

  function commitLoadedSession(sessionId: string, view: PlayerSessionView) {
    const next = { sessionId, view, stale: null };
    loadedSessionRef.current = next;
    setLoadedSession(next);
  }

  function beginForegroundOperation(
    kind: ForegroundOperationKind,
    options: { clearSession: boolean },
  ): ForegroundOperation | null {
    if (foregroundOperationRef.current !== null) {
      return null;
    }
    const operation = {
      controller: new AbortController(),
      id: operationGenerationRef.current + 1,
    };
    operationGenerationRef.current = operation.id;
    foregroundOperationRef.current = operation;
    setForegroundOperation(kind);
    if (options.clearSession) {
      clearLoadedSession();
    }
    setCreatedSessionWithoutView(null);
    setOperationError(null);
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
    commitLoadedSession(sessionId, restoredView);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (
      foregroundOperationRef.current !== null ||
      selectedScenario === undefined ||
      selectedRoleId === ""
    ) {
      return;
    }
    const operation = beginForegroundOperation("creating", {
      clearSession: true,
    });
    if (operation === null) {
      return;
    }
    let createdSessionId: string | null = null;
    try {
      const created = await client.createSession(
        {
          client_request_id: requestIdFactory(),
          character_definition_id: selectedRoleId,
          scenario_id: selectedScenario.scenario_id,
        },
        operation.controller.signal,
      );
      if (!isCurrentOperation(operation)) {
        return;
      }
      createdSessionId = created.session_id;
      setManualSessionId(created.session_id);
      const restoredView = await client.getSessionView(
        created.session_id,
        operation.controller.signal,
      );
      if (!isCurrentOperation(operation)) {
        return;
      }
      commitLoadedSession(created.session_id, restoredView);
    } catch (error: unknown) {
      if (!isCurrentOperation(operation)) {
        return;
      }
      if (createdSessionId !== null) {
        setCreatedSessionWithoutView(createdSessionId);
      }
      setOperationError(formatApiClientError(error));
    } finally {
      finishForegroundOperation(operation);
    }
  }

  async function handleManualRead(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (foregroundOperationRef.current !== null) {
      return;
    }
    const sessionId = manualSessionId.trim();
    const parsedSessionId = sessionPathIdSchema.safeParse(sessionId);
    if (!parsedSessionId.success) {
      clearLoadedSession();
      setCreatedSessionWithoutView(null);
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
      commitLoadedSession(parsedSessionId.data, restoredView);
    } catch (error: unknown) {
      if (!isCurrentOperation(operation)) {
        return;
      }
      setOperationError(formatApiClientError(error));
    } finally {
      finishForegroundOperation(operation);
    }
  }

  async function handleExplicitViewRefresh() {
    const current = loadedSessionRef.current;
    if (
      current === null ||
      current.stale === null ||
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

  async function handleAction(intent: ActionIntent) {
    const current = loadedSessionRef.current;
    if (
      current === null ||
      current.stale !== null ||
      current.view.scenario_status !== "ACTIVE" ||
      current.view.action_affordances.mode === "ENDED" ||
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
      const identity = actionIdentityFactory();
      const request: ActionRequest = actionRequestSchema.parse({
        turn_id: identity.turnId,
        client_request_id: identity.clientRequestId,
        ...intent,
      });
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
      if (stage === "posting" && isTransportUncertain(error)) {
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

  const operationStatus =
    foregroundOperation === "creating"
      ? "正在创建 Session 并读取完整权威 View。"
      : foregroundOperation === "reading"
        ? "正在读取完整权威 View。"
        : foregroundOperation === "submitting"
          ? "正在提交行动；不会自动重发。"
          : foregroundOperation === "pending"
            ? "行动已返回 202，正在按 retry 指示检查同一 request。"
            : foregroundOperation === "refreshing"
              ? "正在重新读取完整权威 View。"
              : loadedSession?.stale !== null && loadedSession !== null
                ? "当前 View 可能 stale；行动保持禁用，等待显式刷新。"
                : loadedSession?.view.scenario_status === "ENDED"
                  ? "副本已结束；没有可执行行动。"
                  : loadedSession !== null
                    ? "空闲：当前 View 已确认，可以选择公开行动。"
                    : "空闲：可以创建 Session 或手动读取已有 Session。";

  const actionDisabledReason =
    foregroundOperation !== null
      ? "前台操作正在进行"
      : loadedSession?.stale !== null && loadedSession !== null
        ? "当前 View 可能 stale，必须先显式刷新"
        : null;

  return (
    <main>
      <header className="hero">
        <p className="eyebrow">Phase 3.1b</p>
        <h1>Deviation Protocol</h1>
        <p>本地单标签页 minimum playable Demo；无持久化或 reload recovery。</p>
      </header>

      <p className="operation-status" role="status" aria-live="polite">
        {operationStatus}
      </p>

      <section className="panel" aria-labelledby="scenario-heading">
        <h2 id="scenario-heading">选择副本与角色</h2>
        {scenarios === null && scenarioError === null ? (
          <p role="status" aria-live="polite">
            正在加载公开副本…
          </p>
        ) : null}
        {scenarioError !== null ? <p role="alert">{scenarioError}</p> : null}
        {scenarios?.length === 0 ? <p>当前没有可公开游玩的副本。</p> : null}
        {scenarios !== null && scenarios.length > 0 ? (
          <form onSubmit={handleCreate}>
            <fieldset disabled={foregroundOperation !== null}>
              <legend className="sr-only">创建 Session</legend>
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

              <label htmlFor="role">角色</label>
              <select
                id="role"
                value={selectedRoleId}
                onChange={(event) => setSelectedRoleId(event.target.value)}
              >
                {selectedScenario?.playable_characters.map((role) => (
                  <option
                    key={role.character_definition_id}
                    value={role.character_definition_id}
                  >
                    {role.display_name} — {role.description}
                  </option>
                ))}
              </select>

              <button
                type="submit"
                disabled={
                  foregroundOperation !== null ||
                  selectedScenario === undefined ||
                  selectedRoleId === ""
                }
              >
                {foregroundOperation === "creating"
                  ? "正在创建…"
                  : "创建 Session"}
              </button>
            </fieldset>
          </form>
        ) : null}
      </section>

      <section className="panel" aria-labelledby="restore-heading">
        <h2 id="restore-heading">手动读取已有 Session</h2>
        <form onSubmit={handleManualRead}>
          <fieldset disabled={foregroundOperation !== null}>
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
                foregroundOperation !== null || manualSessionId.trim() === ""
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
          <p role="status" className="session-confirmation">
            已创建 Session：{createdSessionWithoutView}，但 PlayerSessionView 未加载。
          </p>
        ) : null}
        {operationError !== null ? <p role="alert">{operationError}</p> : null}
      </div>

      {loadedSession?.stale === null || loadedSession === null ? null : (
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

      {loadedSession === null ? null : <ViewSummary loaded={loadedSession} />}

      {loadedSession === null ? null : (
        <ActionPanel
          view={loadedSession.view}
          disabled={
            foregroundOperation !== null || loadedSession.stale !== null
          }
          disabledReason={actionDisabledReason}
          onSubmit={(intent) => void handleAction(intent)}
        />
      )}
    </main>
  );
}

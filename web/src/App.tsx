import { useEffect, useRef, useState, type FormEvent } from "react";

import { publicApiClient, type PublicApiClient } from "./api/client";
import { ApiClientError, formatApiClientError } from "./api/errors";
import type {
  PlayerSessionView,
  PublicScenarioDescription,
} from "./api/schemas";
import { sessionPathIdSchema } from "./api/schemas";

interface AppProps {
  client?: PublicApiClient;
  requestIdFactory?: () => string;
}

interface LoadedSession {
  sessionId: string;
  view: PlayerSessionView;
}

interface ForegroundOperation {
  controller: AbortController;
  id: number;
}

type ForegroundOperationKind = "creating" | "reading";

function newCreationRequestId(): string {
  return `web-create-${globalThis.crypto.randomUUID()}`;
}

function ViewSummary({ view }: { view: PlayerSessionView }) {
  const latestNarrative = view.recent_narrative_texts.at(-1);

  return (
    <article className="view-summary" aria-labelledby="session-view-heading">
      <header>
        <p className="eyebrow">PlayerSessionView</p>
        <h2 id="session-view-heading">{view.presentation.title}</h2>
        <p>{view.presentation.scene_summary}</p>
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

export default function App({
  client = publicApiClient,
  requestIdFactory = newCreationRequestId,
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

  useEffect(() => {
    const controller = new AbortController();
    void client
      .listScenarios(controller.signal)
      .then((catalog) => {
        setScenarios(catalog.scenarios);
        const firstScenario = catalog.scenarios[0];
        if (firstScenario !== undefined) {
          setSelectedScenarioId(firstScenario.scenario_id);
          setSelectedRoleId(firstScenario.default_character_definition_id);
        }
      })
      .catch((error: unknown) => {
        if (error instanceof ApiClientError && error.kind === "aborted") {
          return;
        }
        setScenarioError(formatApiClientError(error));
      });
    return () => {
      controller.abort();
    };
  }, [client]);

  useEffect(() => {
    return () => {
      operationGenerationRef.current += 1;
      foregroundOperationRef.current?.controller.abort();
      foregroundOperationRef.current = null;
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

  function beginForegroundOperation(
    kind: ForegroundOperationKind,
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
    setLoadedSession(null);
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

  function finishForegroundOperation(operation: ForegroundOperation) {
    if (foregroundOperationRef.current?.id !== operation.id) {
      return;
    }
    foregroundOperationRef.current = null;
    setForegroundOperation(null);
  }

  function operationWasAborted(
    operation: ForegroundOperation,
    error: unknown,
  ): boolean {
    return (
      operation.controller.signal.aborted ||
      (error instanceof ApiClientError && error.kind === "aborted")
    );
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
    const operation = beginForegroundOperation("creating");
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
      setLoadedSession({
        sessionId: restoredView.metadata.session_id,
        view: restoredView,
      });
    } catch (error: unknown) {
      if (!isCurrentOperation(operation) || operationWasAborted(operation, error)) {
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
      setLoadedSession(null);
      setCreatedSessionWithoutView(null);
      setOperationError("Session ID 格式无效，请检查后重试。");
      return;
    }
    const operation = beginForegroundOperation("reading");
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
      setLoadedSession({
        sessionId: restoredView.metadata.session_id,
        view: restoredView,
      });
    } catch (error: unknown) {
      if (!isCurrentOperation(operation) || operationWasAborted(operation, error)) {
        return;
      }
      setOperationError(formatApiClientError(error));
    } finally {
      finishForegroundOperation(operation);
    }
  }

  return (
    <main>
      <header className="hero">
        <p className="eyebrow">Phase 3.1a</p>
        <h1>Deviation Protocol</h1>
        <p>公开 API 适配层验证页。创建、读取，不自动推进剧情。</p>
      </header>

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
              {foregroundOperation === "creating" ? "正在创建…" : "创建 Session"}
            </button>
          </form>
        ) : null}
      </section>

      <section className="panel" aria-labelledby="restore-heading">
        <h2 id="restore-heading">手动读取已有 Session</h2>
        <form onSubmit={handleManualRead}>
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

      {loadedSession === null ? null : <ViewSummary view={loadedSession.view} />}
    </main>
  );
}

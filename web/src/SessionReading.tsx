import type { PlayerSessionView } from "./api/schemas";
import { objectiveNames } from "./api/schemas";
import { objectiveLabels } from "./runSetup";
import type { ReactNode } from "react";

/** Accepted public copy stays plain text, including apparent HTML or Markdown. */
function NarrativeText({ text }: { text: string }) {
  return <div className="narrative-prose">
    {text.split(/\r?\n[\t ]*\r?\n/u).filter((paragraph) => paragraph.length > 0).map((paragraph, index) =>
      <p key={index}>{paragraph}</p>,
    )}
  </div>;
}

export function SessionReading({ view, staleKind, readingIdentity = "current", journeyRecap }: {
  view: PlayerSessionView;
  staleKind: string | null;
  readingIdentity?: "current" | "historical" | "unconfirmed";
  journeyRecap?: ReactNode;
}) {
  const historical = readingIdentity === "historical";
  const unconfirmed = readingIdentity === "unconfirmed";
  const latestNarrative = view.recent_narrative_texts.at(-1);
  const earlierNarratives = view.recent_narrative_texts.slice(0, -1);
  const memory = view.player_memory;

  return <article
    className={`view-summary${staleKind === null ? "" : " view-summary-stale"}`}
    aria-labelledby="session-view-heading"
  >
    <header>
      <p className="eyebrow">{historical ? "历史记录 · 只读" : "故事"}</p>
      <h2 id="session-view-heading">{view.presentation.title}</h2>
      {historical ? <p className="freshness-label">历史访问（只读），不是当前进度。</p>
        : unconfirmed ? <p className="freshness-label">访问关联尚未确认；此 View 不代表已确认的当前进度。</p>
        : staleKind === null ? <p className="freshness-label">权威 View：当前</p>
        : <p className="freshness-label stale-label">权威 View：可能 stale（{staleKind}）</p>}
      {unconfirmed && staleKind !== null ? <p className="freshness-label stale-label">权威 View：可能 stale（{staleKind}）</p> : null}
    </header>

    <section aria-labelledby="scene-heading">
      <h3 id="scene-heading">{historical ? "历史场景" : unconfirmed ? "所显示访问的场景" : "当前场景"}：{view.presentation.scene_title}</h3>
      <NarrativeText text={view.presentation.scene_summary} />
    </section>

    {view.encounter ? <section aria-labelledby="escort-heading">
      <h3 id="escort-heading">同行状况</h3>
      <p>目标：{view.encounter.objective}</p>
      {view.encounter.outcome === "ACTIVE" ? <p>眼前的危险：{view.encounter.danger}</p> : null}
      <dl className="compact-list">
        <div><dt>同行者</dt><dd>{view.encounter.companion}</dd></div>
        <div><dt>你的位置</dt><dd>{view.encounter.player_position}</dd></div>
        <div><dt>同行者的位置</dt><dd>{view.encounter.companion_position}</dd></div>
        <div><dt>临时状态</dt><dd>{view.encounter.condition ?? "已结束"}</dd></div>
      </dl>
    </section> : null}

    <section aria-labelledby="narrative-heading">
      <h3 id="narrative-heading">{historical ? "历史公开正文" : unconfirmed ? "所显示访问的公开正文" : "当前公开正文"}</h3>
      <NarrativeText text={latestNarrative ?? "当前尚无已接受的叙事正文。"} />
    </section>

    {view.ending_status !== null && view.presentation.ending != null ?
      <section className="ending" aria-labelledby="ending-heading">
        <p className="eyebrow">{view.ending_status}</p>
        <h3 id="ending-heading">{view.presentation.ending.title}</h3>
        <NarrativeText text={view.presentation.ending.summary} />
      </section> : null}

    <section aria-label={historical ? "历史资源与时钟" : unconfirmed ? "所显示访问的资源与时钟" : "当前资源与时钟"}>
      <h3>{historical ? "当时的状况" : unconfirmed ? "此 View 记录的状况" : "眼下的状况"}</h3>
      <dl className="compact-list">
        {view.player_state.resources.map((resource) => <div key={resource.resource_id}>
          <dt>{resource.resource_id}</dt><dd>{resource.current} / {resource.maximum}</dd>
        </div>)}
        {view.public_clocks.map((clock) => <div key={clock.clock_id}>
          <dt>{clock.clock_id}</dt><dd>{clock.value} / {clock.maximum}</dd>
        </div>)}
      </dl>
      {view.player_state.resources.length === 0 && view.public_clocks.length === 0 ?
        <p>没有公开的资源或时钟。</p> : null}
    </section>

    {journeyRecap}

    <details className="reading-details">
      <summary>回看此前正文（{earlierNarratives.length} 段）</summary>
      <section aria-labelledby="recent-heading">
        <h3 id="recent-heading">近期已接受正文</h3>
        <p className="supporting-copy">这里只保留本次访问的近期片段，按先后排列；最新一段已在上方显示。这不是完整历史。</p>
        {earlierNarratives.length === 0 ? <p>暂无更早的近期正文。</p> :
          <ol className="narrative-history">{earlierNarratives.map((text, index) =>
            <li key={index}><NarrativeText text={text} /></li>,
          )}</ol>}
      </section>
    </details>

    <details className="reading-details">
      <summary>角色与记忆</summary>
      <section aria-labelledby="player-state-heading">
        <h3 id="player-state-heading">公开玩家状态</h3>
        <p>{view.metadata.character_display_name}</p>
        <dl className="compact-list">{view.player_state.attributes.map(([name, value]) =>
          <div key={name}><dt>{name}</dt><dd>{value}</dd></div>,
        )}</dl>
        <p>背包 {view.player_state.inventory.length} · 装备 {view.player_state.equipped_items.length} · 技能 {view.player_state.skills.length} · 可见 NPC {view.player_state.visible_npcs.length}</p>
      </section>
      <section aria-labelledby="memory-heading">
        <h3 id="memory-heading">长期记忆</h3>
        <p>此访问的记忆索引；其他世界的经历请通过旅程历史查看。</p>
        <p>{memory.complete ? "索引已同步" : "记忆索引尚未同步完整；未显示的记录不代表没有发生。"}</p>
        {memory.truncated ? <p>当前只展示部分索引，以下分别为已展示数量和索引总数。</p> : null}
        <dl className="compact-list">
          <div><dt>副本记录</dt><dd>{memory.scenarios.length} / {memory.total_scenario_records}</dd></div>
          <div><dt>NPC 记录</dt><dd>{memory.npcs.length} / {memory.total_npc_records}</dd></div>
          <div><dt>重要经历</dt><dd>{memory.significant_experiences.length} / {memory.total_significant_experiences}</dd></div>
          <div><dt>公开事实引用</dt><dd>{memory.known_public_facts.length} / {memory.total_known_public_facts}</dd></div>
        </dl>
        <p className="supporting-copy">正文回顾不等于事实或记忆更新；此 View 中的资源见上方记录。</p>
      </section>
    </details>

    {view.encounter ? null : <details className="reading-details">
      <summary>场景提示与技术信息</summary>
      <section aria-labelledby="suggestions-heading">
        <h3 id="suggestions-heading">建议行动（只读）</h3>
        <p className="supporting-copy">这些叙事提示不可直接提交；可执行控件只来自 action_affordances。</p>
        {view.narrative_frame.suggested_actions.length === 0 ? <p>当前 Frame 没有建议行动。</p> :
          <ul>{view.narrative_frame.suggested_actions.map((action) =>
            <li key={action.action_id}>{action.label_hint}</li>,
          )}</ul>}
      </section>
      <dl className="metadata-grid">
        <div><dt>Session ID</dt><dd>{view.metadata.session_id}</dd></div>
        <div><dt>状态版本</dt><dd>{view.metadata.state_version}</dd></div>
        <div><dt>副本状态</dt><dd>{view.scenario_status}</dd></div>
        <div><dt>内容版本</dt><dd>{view.metadata.content_version}</dd></div>
      </dl>
      <p>Frame {view.narrative_frame.frame_id} · 停止条件：<strong>{view.narrative_frame.stop_condition}</strong></p>
      {view.ending_id !== null ? <p>Ending ID：{view.ending_id}</p> : null}
      {view.run_context ? <section aria-label="Run 设置">
        <h3>本次 Run 设置</h3>
        <p>资源环境：{view.run_context.resource_pressure_label}</p>
        <dl className="compact-list">{objectiveNames.map((name) => <div key={name}>
          <dt>{objectiveLabels[name]}</dt><dd>{view.run_context?.objectives[name]}</dd>
        </div>)}</dl>
        <p>表现：{view.run_context.presentation.world_tone} / {view.run_context.presentation.reality_boundary} / {view.run_context.presentation.relationship_overlay}</p>
      </section> : null}
    </details>}
  </article>;
}

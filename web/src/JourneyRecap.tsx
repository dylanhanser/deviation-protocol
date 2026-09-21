import { useEffect, useState } from "react";
import type { PublicApiClient } from "./api/client";
import type { JourneyRecap as Recap, NativeRunJourney, PlayerSessionView } from "./api/schemas";
import { assertJourney } from "./runJourney";

function assertRecap(view: PlayerSessionView, journey: NativeRunJourney, recap: Recap) {
  assertJourney(view, journey);
  const c = recap.context;
  const historical = journey.path.session_id !== journey.current.session_id;
  if (recap.session_id !== view.metadata.session_id || (c !== null && (
    c.run_id !== journey.run_id || c.run_state_version !== journey.run_state_version ||
    c.session_state_version !== view.metadata.state_version || c.scenario_id !== journey.path.scenario_id ||
    c.content_version !== view.metadata.content_version || c.cutoff_visit !== (journey.path.visit?.visit_ordinal ?? 1) ||
    c.scope !== (historical ? "historical" : "current") ||
    c.lifecycle_at_cutoff !== (historical ? "active" : journey.lifecycle_status)))) {
    throw new Error("Recap association mismatch");
  }
}

export function JourneyRecap({client, view, journey, ready}: {
  client: PublicApiClient; view: PlayerSessionView; journey: NativeRunJourney | null; ready: boolean;
}) {
  const [result, setResult] = useState<{
    client: PublicApiClient; view: PlayerSessionView; journey: NativeRunJourney;
    recap: Recap | null;
  } | null>(null);
  useEffect(() => {
    if (!ready || journey === null) return;
    let active = true;
    const controller = new AbortController();
    void client.getJourneyRecap(view.metadata.session_id, controller.signal).then(recap => {
      assertRecap(view, journey, recap);
      if (active) setResult({client, view, journey, recap});
    }).catch(() => {
      if (active) setResult({client, view, journey, recap: null});
    });
    return () => { active = false; controller.abort(); };
  }, [client, view, journey, ready]);

  const bound = ready && result?.client === client && result.view === view && result.journey === journey;
  const recap = bound ? result.recap : null;
  return <details className="reading-details">
    <summary>旅程回顾</summary>
    <section aria-label="旅程回顾内容" aria-live="polite">
      <p className="supporting-copy">本次旅程的已核实经历；不是完整正文、当前资源或可编辑记忆。</p>
      {!ready || !journey ? <p>访问关联尚未确认，暂不展示回顾。</p>
        : !bound ? <p>正在读取旅程回顾…</p>
        : !recap ? <p>旅程回顾暂时无法读取；可使用现有读取控件刷新，游戏操作不受此提示影响。</p>
        : <>
          {recap.context ? <p>{recap.context.scope === "historical"
            ? `历史回顾 · 截至第 ${recap.context.cutoff_visit} 次访问，不含之后的经历。`
            : `本次旅程 · 截至当前第 ${recap.context.cutoff_visit} 次访问。`}</p> : null}
          {recap.status === "unavailable_evidence" ? <p>缺少必要证据或证据存在冲突，暂不能提供可靠回顾；未显示不代表未发生。</p>
            : recap.status === "unavailable_overflow" ? <p>必要记录超出回顾容量，暂不能提供完整回顾；请通过旅程历史阅读。</p>
            : <>
              {recap.status === "incomplete" ? <p>部分补充内容缺失或因容量限制省略；必要结果和待核事项均已保留。</p> : null}
              <div className="narrative-prose">{recap.text.split("\n\n").map((text, index) => <p key={index}>{text}</p>)}</div>
            </>}
        </>}
    </section>
  </details>;
}

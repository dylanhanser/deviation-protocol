import { useEffect, useState } from "react";
import type { PublicApiClient } from "./api/client";
import type { OpeningPreparation, TalentCard } from "./api/schemas";

const tiers = {TOP:"卓越",TRADEOFF:"取舍",ORDINARY:"普通",WEAK:"弱势"};
const parameterLabels = {resource_pressure:"资源压力",social_trust:"社会信任",consequence_severity:"后果强度",information_opacity:"信息不透明度",conflict_intensity:"冲突强度"};

export function OpeningTalentChoices({record,disabled,onConfirm}:{record:OpeningPreparation;disabled:boolean;onConfirm:(selected:readonly string[])=>void}) {
  const [chosen,setChosen]=useState<readonly string[]>(record.selected_ids);
  const confirmed=record.state === "CONFIRMED";
  const selected=confirmed ? record.selected_ids : chosen;
  return <section className="opening-talents" aria-labelledby="opening-talents-heading">
    <h3 id="opening-talents-heading">选择伴你启程的两项天赋</h3>
    <p>这五项天赋已为本次旅程保留。暂时离开或刷新后仍是同一组，入场设置也已固定。</p>
    <p>难度：{record.admission.profile_ref.profile_id === "difficulty.fragile-alliance" ? "脆弱同盟" : record.admission.profile_ref.profile_id === "difficulty.open-expedition" ? "开放探索" : "寂静猎场"}。初始世界：死亡证明。</p>
    <p>世界基调：{{grim:"冷峻",balanced:"均衡",heroic:"昂扬"}[record.admission.presentation.world_tone]}；现实边界：{{lawful:"遵循常理",deviant:"容许偏离",chaotic:"混沌"}[record.admission.presentation.reality_boundary]}；人际氛围：{{off:"不额外渲染",veiled:"含蓄",charged:"浓烈"}[record.admission.presentation.relationship_overlay]}。</p>
    {record.admission.overrides.length ? <ul aria-label="已固定的难度调整">{record.admission.overrides.map(value => <li key={value.parameter}>{parameterLabels[value.parameter]}：{value.value}</li>)}</ul> : <p>使用所选难度的默认数值。</p>}
    <fieldset disabled={disabled || confirmed}>
      <legend>天赋（恰好选择两项）</legend>
      <div className="talent-grid">{record.candidates.map(talent => <label className={`talent-card talent-${talent.tier.toLowerCase()}`} key={talent.id}>
        <span><input type="checkbox" checked={selected.includes(talent.id)} disabled={!selected.includes(talent.id) && selected.length === 2}
          onChange={() => setChosen(current => current.includes(talent.id) ? current.filter(id => id !== talent.id) : [...current,talent.id])}/>{talent.name}</span>
        <strong>{tiers[talent.tier]}</strong><span>{talent.description}</span>
      </label>)}</div>
    </fieldset>
    <p role="status">{confirmed ? "天赋已确认，本次旅程不可更换。" : `已选择 ${selected.length} / 2 项`}</p>
    <button type="button" disabled={disabled || selected.length !== 2} onClick={() => onConfirm([...selected])}>
      {confirmed ? "读取已开始的旅程" : "确认天赋并开始"}
    </button>
  </section>;
}

export function ConfirmedOpeningTalents({client,sessionId}:{client:PublicApiClient;sessionId:string}) {
  const [refresh,setRefresh]=useState(0);
  const [state,setState]=useState<{client:PublicApiClient;sessionId:string;talents:TalentCard[]|null}|null>(null);
  useEffect(() => {
    const controller=new AbortController();
    client.getOpeningTalents(sessionId,controller.signal).then(talents => {
      if (!controller.signal.aborted) setState({client,sessionId,talents});
    }).catch(() => {if (!controller.signal.aborted) setState({client,sessionId,talents:null});});
    return () => controller.abort();
  },[client,sessionId,refresh]);
  const current=state?.client === client && state.sessionId === sessionId ? state : null;
  return <section aria-label="本次旅程的天赋"><h3>本次旅程的天赋</h3>
    {!current ? <p role="status">正在读取天赋…</p> : current.talents === null ? <div><p role="status">暂时无法读取天赋。</p><button type="button" onClick={() => setRefresh(v => v+1)}>重读天赋</button></div> : current.talents.length === 0 ? <p>本次旅程没有开局天赋。</p> :
      <ul>{current.talents.map(t => <li key={t.id}><strong>{t.name} · {tiers[t.tier]}</strong><p>{t.description}</p></li>)}</ul>}
  </section>;
}

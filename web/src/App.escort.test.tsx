import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { afterEach, expect, it, vi } from "vitest";
import App from "./App";
import { PublicApiClient } from "./api/client";
import { playerSessionViewSchema, type PlayerSessionView, type PublicScenarioDescription } from "./api/schemas";
import { activeViewFixture, endedViewFixture, synchronousActionResponseFixture, eligiblePlayerCharactersFixture, scenarioCatalogFixture } from "./test/fixtures";
import { server } from "./test/server";
import { writeSessionRecoveryRecord } from "./sessionRecovery";

const origin = "http://escort-ui.test";
const client = new PublicApiClient({baseUrl:origin});
const story: PublicScenarioDescription = {scenario_id:"wind_gate",content_version:"wind-gate-1.0.0",
  title:"风闸前的同行者",hook:"护送一位成年同行者进入候船室，或一起撤回。",entry_mode:"SESSION",
  default_character_definition_id:"character.wind_gate.traveler",playable_characters:[{
    character_definition_id:"character.wind_gate.traveler",display_name:"旅人",description:"一起行动的旅人。"}]};
function scene(stage: "initial" | "unsteady" | "door" | "success" | "withdrawn", version: number): PlayerSessionView {
  const terminal = stage === "success" || stage === "withdrawn";
  const v = terminal ? endedViewFixture(stage === "success" ? "RESOLVED" : "FAILED") : structuredClone(activeViewFixture);
  v.metadata.state_version=version;v.player_state.state_version=version;
  v.metadata.content_version = story.content_version;
  v.metadata.character_definition_id = story.default_character_definition_id;
  v.narrative_frame.scenario_id = story.scenario_id;
  v.player_state.content_version = story.content_version;
  v.player_state.character_definition_id = story.default_character_definition_id;
  v.player_state.resources = [];
  v.public_clocks = [];v.narrative_frame.player_visible_clocks = [];
  v.presentation = {title:story.title,scene_title:terminal ? "同行的结果" : "渡口通道",scene_summary:"阅读和等待不会推进危险。",
    ending: terminal ? {title:stage === "success" ? "护送成功" : "安全撤回",summary:"两人都安全，没有资源损失。"} : null};
  v.ending_status = terminal ? stage === "success" ? "RESOLVED" : "FAILED" : null;
  const condition = terminal ? null : stage === "initial" ? "慌乱" : stage === "unsteady" ? "失衡" : "扶稳";
  const position = stage === "initial" ? "入口平台" : stage === "unsteady" ? "通道中段" : stage === "door" ? "内门前" : stage === "success" ? "候船室" : "避风间";
  v.encounter = {presentation_version:1,objective:"护送同行者进入候船室，或一起撤入避风间。",danger:"阵风穿过通道，外侧风闸正在关闭。",
    companion:"成年同行者",player_position:position,companion_position:position,condition,
    outcome:terminal ? stage === "success" ? "SUCCESS" : "SAFE_WITHDRAWAL" : "ACTIVE"};
  const labels = stage === "initial" ? ["先扶稳同行者","立即带向通道","一起撤入避风间"]
    : stage === "unsteady" ? ["停步抓牢扶手，扶稳对方","继续抢行","一起撤入避风间"]
    : stage === "door" ? ["结伴进入候船室","一起撤入避风间"] : [];
  if (!terminal) {
    v.action_affordances.choices = labels.map((label,index) => ({action_type:"CHOOSE" as const,choice_id:`choice.${stage}.${index}`,label,target_ids:[]}));
    v.narrative_frame.suggested_actions = v.action_affordances.choices.map(c => ({action_id:c.choice_id, action_type:"choice",label_hint:c.label,target_ids:[]}));
  }
  v.recent_narrative_texts = version ? [terminal ? "两人安全，临时状态已结束。" : `你们一起到了${position}。`] : [];
  return playerSessionViewSchema.parse(v);
}
function discovery() {
  server.use(http.get(`${origin}/v1/scenarios`,()=>HttpResponse.json({scenarios:[...scenarioCatalogFixture.scenarios,story]})),
    http.get(`${origin}/v1/player-characters/eligible-for-run-entry`,()=>HttpResponse.json(eligiblePlayerCharactersFixture)));
}
afterEach(()=>vi.restoreAllMocks());

it.each(["success","withdrawn"] as const)("restores encounter and follows authoritative choices to %s without internal state labels", async outcome=>{
  discovery();writeSessionRecoveryRecord("session-public-1");let current=scene("initial",0);let posts=0;
  server.use(http.get(`${origin}/v1/sessions/session-public-1/view`,()=>HttpResponse.json(current)),
    http.post(`${origin}/v1/sessions/session-public-1/actions`,async ({request})=>{
      const body=await request.json() as Record<string,unknown>;expect(Object.keys(body).sort()).toEqual(["action_type","choice_id","client_request_id","decision_id","turn_id"]);
      posts++;current=posts===1 ? scene("unsteady",1) : posts===2 && outcome==="success" ? scene("door",2) : scene(outcome,posts);
      const response=synchronousActionResponseFixture("response",posts);response.session_id="session-public-1";
      response.client_request_id=body.client_request_id as string;response.narrative_frame=current.narrative_frame;response.narrative_text="固定叙事结果。";
      return HttpResponse.json(response);
    }));
  const user=userEvent.setup();render(<App client={client}/>);
  expect(await screen.findByText("慌乱",{exact:true})).toBeInTheDocument();
  const encounter=screen.getByRole("region",{name:"同行状况"});
  expect(within(encounter).getByText("成年同行者",{exact:true})).toBeInTheDocument();
  expect(within(encounter).getAllByText("入口平台")).toHaveLength(2);
  expect(within(encounter).getByText(/阵风穿过通道/)).toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:"立即带向通道"}));
  expect(await screen.findByText("失衡",{exact:true})).toBeInTheDocument();
  expect(screen.queryByRole("button",{name:"先扶稳同行者"})).not.toBeInTheDocument();
  await user.click(screen.getByRole("button",{name:outcome==="success" ? "停步抓牢扶手，扶稳对方" : "继续抢行"}));
  if(outcome==="success") {
    expect(await screen.findByText("扶稳",{exact:true})).toBeInTheDocument();
    await user.click(screen.getByRole("button",{name:"结伴进入候船室"}));
  }
  expect(await screen.findByRole("heading",{name:outcome==="success" ? "护送成功" : "安全撤回"})).toBeInTheDocument();
  expect(screen.getByText("已结束",{exact:true})).toBeInTheDocument();
  expect(screen.queryByRole("button",{name:"一起撤入避风间"})).not.toBeInTheDocument();
  expect(screen.queryByText(/wind_gate\.fact|状态版本|CAS|DTO|策略仍是最终权威/)).not.toBeInTheDocument();
  expect(posts).toBe(outcome==="success" ? 3 : 2);
});

it("locks duplicate submission and ignores an old client's late action response",async()=>{
  discovery();writeSessionRecoveryRecord("session-public-1");
  const original=scene("initial",0);
  server.use(http.get(`${origin}/v1/sessions/session-public-1/view`,()=>HttpResponse.json(original)));
  let resolve!: (value: Awaited<ReturnType<PublicApiClient["submitAction"]>>) => void;
  const send=vi.spyOn(client,"submitAction").mockImplementation(()=>new Promise(r=>{resolve=r;}));
  const replacement=new PublicApiClient({baseUrl:origin});
  const mounted=render(<App client={client}/>);
  const button=await screen.findByRole("button",{name:"立即带向通道"});
  fireEvent.click(button);fireEvent.click(button);
  await waitFor(()=>expect(send).toHaveBeenCalledTimes(1));
  expect(button).toBeDisabled();
  mounted.rerender(<App client={replacement}/>);
  await act(async()=>{resolve({status:200,response:{...synchronousActionResponseFixture("response",1),narrative_frame:scene("unsteady",1).narrative_frame}});});
  await waitFor(()=>expect(screen.queryByText("失衡",{exact:true})).not.toBeInTheDocument());
  expect(send).toHaveBeenCalledTimes(1);
});

it("starts a standalone Session with its authored character and retries a failed View using GET only",async()=>{
  discovery();const initial=scene("initial",0);let posts=0,reads=0;
  server.use(http.post(`${origin}/v1/sessions`,async ({request})=>{
    posts++;const body=await request.json();expect(body).toMatchObject({scenario_id:story.scenario_id,character_definition_id:story.default_character_definition_id});
    return HttpResponse.json({...initial.metadata,scenario_id:story.scenario_id,narrative_frame:initial.narrative_frame},{status:201});
  }),http.get(`${origin}/v1/sessions/session-public-1/view`,()=>++reads===1 ? HttpResponse.error() : HttpResponse.json(initial)));
  const user=userEvent.setup();render(<App client={client}/>);
  await user.click(await screen.findByRole("button",{name:"开始《风闸前的同行者》"}));
  await user.click(await screen.findByRole("button",{name:"手动重试完全相同的操作"}));
  expect(await screen.findByText("慌乱",{exact:true})).toBeInTheDocument();expect(posts).toBe(1);expect(reads).toBe(2);
});

it("rejects a contradictory terminal condition",()=>{
  const valid=scene("success",3);
  expect(playerSessionViewSchema.safeParse({...valid,encounter:{...valid.encounter,condition:"慌乱"}}).success).toBe(false);
  expect(playerSessionViewSchema.safeParse({...valid,ending_status:"FAILED"}).success).toBe(false);
});


it("keeps a contradictory creation association locked without adopting its View",async()=>{
  discovery();const initial=scene("initial",0);let reads=0;
  server.use(http.post(`${origin}/v1/sessions`,()=>HttpResponse.json({...initial.metadata,
    scenario_id:"wrong-story",narrative_frame:{...initial.narrative_frame,scenario_id:"wrong-story"}},{status:201})),
    http.get(`${origin}/v1/sessions/session-public-1/view`,()=>{reads++;return HttpResponse.json(initial);}));
  const user=userEvent.setup();render(<App client={client}/>);
  await user.click(await screen.findByRole("button",{name:"开始《风闸前的同行者》"}));
  await screen.findByRole("heading",{name:"操作结果尚未解决"});
  expect(reads).toBe(0);expect(screen.queryByRole("button",{name:"先扶稳同行者"})).not.toBeInTheDocument();
});

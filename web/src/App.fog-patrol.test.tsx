/// <reference types="node" />
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import path from "node:path";
import { configure, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import App from "./App";
import { PublicApiClient } from "./api/client";
import { openingPreparationSchema, playerCharacterCreationResultSchema, nativeRunJourneySchema, nativeRunContinuationResultSchema } from "./api/schemas";
import { SESSION_RECOVERY_STORAGE_KEY } from "./sessionRecovery";
import { completionJourneyFixture } from "./test/fixtures";
configure({asyncUtilTimeout:10000});

it("keeps the completed old route closed to Fog Station associations",()=>{
  const {journey}=completionJourneyFixture();
  const completion={completion_id:"a".repeat(64),outcome:"unresolved_record_preserved",title:"待核事项保留，核验旅程已结案",
    notice:"本次旅程已正常完成。发运暂缓继续有效，送达仍未得到证明；旧记录与资源保持原状。",
    canon_outcome:{dispatch:"held",delivery:"unproven",record:"sealed",verification:"closed_unresolved"}};
  const completed={...journey,schema_version:"native-run-journey/v2",lifecycle_status:"completed",run_state_version:6,completion};
  expect(nativeRunJourneySchema.safeParse(completed).success).toBe(true);
  const crossed=structuredClone(completed);
  crossed.predecessor!.scenario_id="fog_patrol";
  crossed.predecessor!.scenario_content_version="fog-patrol-1.0.0";
  crossed.predecessor!.visit!.world_id="world.fog_station";
  crossed.predecessor!.visit!.region_id="region.fog_station.patrol_pass";
  expect(nativeRunJourneySchema.safeParse(crossed).success).toBe(false);
});

interface Step {action_type:string;choice_id:string|null;description:string|null}
interface Message {id?:number;ready?:boolean;actions?:Step[];status?:number;body?:unknown;sha256?:string}
interface Trace {method:string;path:string;body?:string;headers:Record<string,string>}

async function demoBridge() {
  const root=path.resolve("..");
  const env={...process.env,PYTHONIOENCODING:"utf-8",PYTHONUTF8:"1",PYTHONUNBUFFERED:"1"};
  for (const key of ["DATABASE_URL","TEST_DATABASE_URL","DEEPSEEK_API_KEY","RUN_LIVE_DEEPSEEK_TEST"]) delete env[key as keyof typeof env];
  const child=spawn(path.join(root,".venv/Scripts/python.exe"),[path.join(root,"tests/e2e/support/native_world_continuation_child.py")],
    {cwd:root,env,windowsHide:true,stdio:["pipe","pipe","pipe"]});
  let errors="",counter=0;
  const pending=new Map<number,{resolve:(m:Message)=>void;reject:(e:Error)=>void}>();
  child.stderr.on("data",chunk=>{errors+=String(chunk);});
  const lines=createInterface({input:child.stdout});
  const ready=new Promise<Step[]>((resolve,reject)=>{
    child.once("error",reject);
    child.once("exit",code=>{if(code)reject(new Error(`Demo child ${code}: ${errors}`));});
    lines.on("line",line=>{
      const message=JSON.parse(line) as Message;
      if(message.ready) resolve(message.actions!);
      else {const waiter=pending.get(message.id!);pending.delete(message.id!);waiter?.resolve(message);}
    });
  });
  child.on("exit",code=>{for(const waiter of pending.values())waiter.reject(new Error(`Demo child ${code}: ${errors}`));pending.clear();});
  const calls:Trace[]=[];
  const transport={transform:null as ((request:Trace,reply:Message)=>Message|Promise<Message>)|null};
  const send=(request:object)=>new Promise<Message>((resolve,reject)=>{
    const id=++counter;pending.set(id,{resolve,reject});child.stdin.write(JSON.stringify({...request,id})+"\n");
  });
  const fetchImplementation:typeof fetch=async(input,init)=>{
    const request={method:init?.method??"GET",path:new URL(String(input)).pathname,
      ...(typeof init?.body === "string" ? {body:init.body} : {}),headers:Object.fromEntries(new Headers(init?.headers).entries())};
    calls.push(request);
    const actual=await send(request);
    const reply=transport.transform ? await transport.transform(request,actual) : actual;
    return new Response(JSON.stringify(reply.body),{status:reply.status!,headers:{"Content-Type":"application/json"}});
  };
  const actions=await ready;
  return {actions,calls,transport,fetchImplementation,inspect:()=>send({inspect:true}),close:()=>{child.stdin.end();lines.close();child.kill();}};
}

it.each(["help", "lost-response-bypass"])("patrol %s: explicit confirmation, refresh, history and visit ending", async mode => {
  const demo = await demoBridge();
  try {
    const raw = async (method:string, route:string, body?:object, key?:string) => {
      const response = await demo.fetchImplementation(`http://demo/${route}`, {method,
        headers:{"Content-Type":"application/json",...(key ? {"Idempotency-Key":key} : {})},
        ...(body ? {body:JSON.stringify(body)} : {})});
      const value:unknown = await response.json();
      expect(response.status,JSON.stringify(value)).toBe(200);
      return value;
    };
    const character = playerCharacterCreationResultSchema.parse(await raw("POST","v1/player-characters",
      {contract_version:"structured-player-character/v1",character_core:{},narration_preferences:{}},"patrol.character"));
    const prep = openingPreparationSchema.parse(await raw("POST","v1/opening-preparations",{
      player_character_id:character.player_character_id.value,expected_record_revision:1,
      profile_ref:{profile_id:"difficulty.open-expedition",profile_version:1},entry_world:{entry_world_id:"world.fog_station",entry_world_version:1},
      overrides:[],presentation:{world_tone:"balanced",reality_boundary:"lawful",relationship_overlay:"off"}},"patrol.prepare"));
    const admitted = openingPreparationSchema.parse(await raw("POST",`v1/opening-preparations/${prep.preparation_id}/confirm`,{
      character_id:prep.character_id,catalog_version:prep.catalog_version,selected_ids:prep.candidates.slice(0,2).map(c=>c.id)},"patrol.admit"));
    const sid = admitted.result!.session_id;
    const client = new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation});
    for (const [index,label] of ["走近并与巡路员会面","配合岑舟固定挡板","现在离开哨站"].entries()) {
      const current = await client.getSessionView(sid);
      const choice = current.action_affordances.choices.find(c=>c.label===label)!;
      await client.submitAction(sid,{action_type:"CHOOSE",choice_id:choice.choice_id,decision_id:current.narrative_frame.decision_id!,
        turn_id:`source.${index}`,client_request_id:`source.${index}`});
    }
    const sourceJourney = await client.getNativeRunJourney(sid);
    expect(nativeRunJourneySchema.safeParse({...sourceJourney,next_transition:{...sourceJourney.next_transition,kind:"regional_revisit"}}).success).toBe(false);
    sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:sid}));
    let mounted = render(<App client={client} idempotencyKeyFactory={()=>"patrol.continue"}/>);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"继续当前旅程"}));
    expect(screen.getByRole("dialog",{name:"确认继续旅程"})).toHaveTextContent("雾哨站");
    await user.click(screen.getByRole("button",{name:"取消继续"}));
    expect(demo.calls.filter(c=>c.path.endsWith("/run-continuation")&&c.method==="POST")).toHaveLength(0);
    let confirmed:unknown;
    demo.transport.transform = (request,reply) => {
      if (request.method === "POST" && request.path.endsWith("/run-continuation")) {
        confirmed = reply.body;
        if (mode === "lost-response-bypass") throw new TypeError("lost confirmed response");
      }
      return reply;
    };
    await user.click(screen.getByRole("button",{name:"继续当前旅程"}));
    await user.click(screen.getByRole("button",{name:"确认前往巡路风口"}));
    if (mode === "lost-response-bypass") {
      await screen.findByRole("button",{name:"重试原续接请求"});
      await waitFor(()=>expect(screen.getByRole("button",{name:"读取续接状态"})).toBeEnabled());
      await user.click(screen.getByRole("button",{name:"读取续接状态"}));
    }
    await screen.findByRole("button",{name:"走近岑舟，打个招呼"});
    expect(demo.calls.filter(c=>c.path.endsWith("/run-continuation")&&c.method==="POST")).toHaveLength(1);
    const result = nativeRunContinuationResultSchema.parse(confirmed);
    expect(nativeRunContinuationResultSchema.safeParse({...result,scenario_content_version:"undelivered-receipt-1.0.0"}).success).toBe(false);
    expect(JSON.parse(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!).session_id).toBe(result.session_id);
    const recovered = await client.getNativeRunJourney(result.session_id);
    expect(nativeRunJourneySchema.safeParse({...recovered,next_transition:sourceJourney.next_transition}).success).toBe(false);
    expect(nativeRunJourneySchema.safeParse({...recovered,run_context:{...recovered.run_context,entry_world:{entry_world_id:"world.death_certificate",entry_world_version:1}}}).success).toBe(false);
    for (const label of ["走近岑舟，打个招呼",mode === "help" ? "在护栏内拉稳绳索，协助拆灯" : "沿背风小径安全绕行",
        mode === "help" ? "向岑舟道别，离开风口" : "向岑舟道别，继续走远"]) {
      const before = await demo.inspect();
      const posts = demo.calls.filter(c=>c.method==="POST").length;
      mounted.unmount();
      mounted = render(<App client={client}/>);
      await screen.findByRole("button",{name:label});
      expect((await demo.inspect()).sha256).toBe(before.sha256);
      expect(demo.calls.filter(c=>c.method==="POST")).toHaveLength(posts);
      await user.click(screen.getByRole("button",{name:label}));
    }
    await screen.findByRole("button",{name:"结束本次旅程"});
    expect(screen.getAllByText(/暂时没有可继续的内容/).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button",{name:"继续当前旅程"})).not.toBeInTheDocument();
    expect((await client.getNativeRunStatus(result.session_id)).lifecycle_status).toBe("active");
    const beforeHistory = await demo.inspect();
    const posts = demo.calls.filter(c=>c.method==="POST").length;
    await user.click(screen.getByRole("button",{name:"查看上一世界历史"}));
    await screen.findByText("正在阅读旅程历史；这里只读，不会改变当前进度。");
    expect(screen.queryByRole("button",{name:"继续当前旅程"})).not.toBeInTheDocument();
    await user.click(screen.getByRole("button",{name:"返回当前世界"}));
    await screen.findByRole("button",{name:"结束本次旅程"});
    expect((await demo.inspect()).sha256).toBe(beforeHistory.sha256);
    expect(demo.calls.filter(c=>c.method==="POST")).toHaveLength(posts);
    mounted.unmount();
    mounted = render(<App client={client}/>);
    await screen.findByRole("button",{name:"结束本次旅程"});
    expect((await demo.inspect()).sha256).toBe(beforeHistory.sha256);
    await waitFor(()=>expect(demo.calls.filter(c=>c.method==="POST")).toHaveLength(posts));
    mounted.unmount();
  } finally {demo.close();}
},60000);

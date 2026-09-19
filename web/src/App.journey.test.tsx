/// <reference types="node" />
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import path from "node:path";
import { act, configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import App from "./App";
import { PublicApiClient } from "./api/client";
import { ARCHIVE_NOTICE, nativeRunStatusSchema, nativeRunJourneySchema, nativeRunRevisitResultSchema, playerSessionViewSchema, nativeRunEntryResponseSchema, playerCharacterCreationResultSchema, actionRequestSchema, type NativeJourneyAssociation } from "./api/schemas";
import { SESSION_RECOVERY_STORAGE_KEY } from "./sessionRecovery";
import { endedViewFixture, nativeViewFixture } from "./test/fixtures";

configure({asyncUtilTimeout:10000});

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

it.each(["seal","defer","confirmed-visit","confirmed-predecessor","lost-response","storage-failure","progressed-valid","refresh-contradiction"])("R09 %s: actual Demo journey, storage-only remount, 3-2-1-2-3 and exit",async(mode)=>{
  const choice=mode === "defer" ? "defer" : "seal";
  const demo=await demoBridge();
  try {
    const raw=async(method:string,p:string,body?:object,key?:string)=>{
      const reply=await demo.fetchImplementation(`http://demo/${p}`,{method,headers:{"Content-Type":"application/json",...(key?{"Idempotency-Key":key}:{})},
        ...(body?{body:JSON.stringify(body)}:{})});
      const value:unknown=await reply.json();expect(reply.status,JSON.stringify(value)).toBe(200);return value;
    };
    const created=playerCharacterCreationResultSchema.parse(await raw("POST","v1/player-characters",{
      contract_version:"structured-player-character/v1",character_core:{},narration_preferences:{}},"journey.character"));
    const entered=nativeRunEntryResponseSchema.parse(await raw("POST","v1/runs/native",{
      player_character_id:created.player_character_id.value,expected_record_revision:1,
      profile_ref:{profile_id:choice==="seal"?"difficulty.open-expedition":"difficulty.silent-hunting-ground",profile_version:1},
      entry_world:{entry_world_id:"world.death_certificate",entry_world_version:1},overrides:[],
      presentation:{world_tone:"balanced",reality_boundary:"lawful",relationship_overlay:"off"}},"journey.entry"));
    let client=new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation});
    for(const [index,step]of demo.actions.entries()) {
      const view=await client.getSessionView(entered.session_id);
      if(view.scenario_status === "ENDED")break;
      await client.submitAction(entered.session_id,actionRequestSchema.parse({turn_id:`journey.turn.${index}`,client_request_id:`journey.action.${index}`,
        action_type:step.action_type,...(step.choice_id?{choice_id:step.choice_id,decision_id:view.narrative_frame.decision_id}:{}),
        ...(step.description?{description:step.description}:{})}));
    }
    const first=await client.getSessionView(entered.session_id);
    expect(first.scenario_status).toBe("ENDED");
    const secondResult=await raw("POST",`v1/sessions/${entered.session_id}/run-continuation`,{
      expected_run_state_version:3,expected_session_state_version:first.metadata.state_version},"journey.continue") as {session_id:string};
    const second=secondResult.session_id;
    await client.submitAction(second,{action_type:"OBSERVE",description:"核对收件台",turn_id:"dispatch.observe",client_request_id:"dispatch.observe"});
    await client.submitAction(second,{action_type:"TALK",target_ids:["scenario-npc-1"],dialogue:"核对排程",turn_id:"dispatch.talk",client_request_id:"dispatch.talk"});
    const decision=await client.getSessionView(second);
    await client.submitAction(second,actionRequestSchema.parse({action_type:"CHOOSE",choice_id:"undelivered_receipt.action.hold",
      decision_id:decision.narrative_frame.decision_id,turn_id:"dispatch.hold",client_request_id:"dispatch.hold"}));
    sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:second}));
    let mounted=render(<App client={client} idempotencyKeyFactory={()=>"journey.revisit"}/>);
    const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"继续当前旅程"},{timeout:10000}));
    expect(screen.getByRole("dialog",{name:"确认继续旅程"})).toHaveTextContent("核验档案室");
    await user.click(screen.getByRole("button",{name:"取消继续"}));
    expect(demo.calls.filter(c=>c.method==="POST"&&c.path.endsWith("/run-revisit"))).toHaveLength(0);
    await user.click(screen.getByRole("button",{name:"继续当前旅程"}));
    let contradicted=false,lost=false;
    demo.transport.transform=async(request,reply)=>{
      if(request.method==="POST" && request.path.endsWith("/run-revisit")) {
        if(mode==="lost-response" && !lost){lost=true;throw new TypeError("lost confirmed response");}
        if(mode==="progressed-valid") await client.submitAction((reply.body as {session_id:string}).session_id,
          {action_type:"OBSERVE",description:"查看待核记录",turn_id:"advance",client_request_id:"advance"});
      }
      if(mode.startsWith("confirmed-") && request.method==="GET" && request.path.endsWith("/run-journey") &&
          !request.path.includes(second) && !request.path.includes(entered.session_id)) {
        contradicted=true;
        const body=structuredClone(reply.body) as import("./api/schemas").NativeRunJourney;
        if(mode==="confirmed-visit") {
          body.path.visit!.visit_id="contradictory.valid.visit";body.current.visit!.visit_id="contradictory.valid.visit";
        } else body.predecessor!.visit!.visit_id="contradictory.valid.predecessor";
        return {...reply,body};
      }
      return reply;
    };
    const originalSet=Storage.prototype.setItem;
    const storageFault=mode==="storage-failure" ? vi.spyOn(Storage.prototype,"setItem").mockImplementation(function(this:Storage,key,value){
      if(key===SESSION_RECOVERY_STORAGE_KEY && !value.includes(second)) throw new DOMException("storage denied");
      originalSet.call(this,key,value);
    }) : null;
    await user.click(screen.getByRole("button",{name:"确认进入核验档案室"}));
    if(mode==="lost-response") {
      const retry=await screen.findByRole("button",{name:"重试原续接请求"});
      await waitFor(()=>expect(retry).toBeEnabled());await user.click(retry);
    }
    if(storageFault) {
      const retry=await screen.findByRole("button",{name:"重试保存已确认的下一世界"});
      storageFault.mockRestore();await user.click(retry);
    }
    if(mode.startsWith("confirmed-")) {
      await waitFor(()=>expect(contradicted).toBe(true),{timeout:10000});
      expect(screen.queryByRole("button",{name:"提交查看待核记录"})).not.toBeInTheDocument();
      const saved=sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY);
      expect(JSON.parse(saved!).session_id).not.toBe(second);
      demo.transport.transform=null;
      const retry=await screen.findByRole("button",{name:"读取续接状态"});
      await waitFor(()=>expect(retry).toBeEnabled());await user.click(retry);
      expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(saved);
    }
    if(mode!=="progressed-valid") {
      const observe=await screen.findByRole("button",{name:"提交查看待核记录"},{timeout:15000});
      expect(screen.getByLabelText("抵达说明")).toHaveTextContent("回执待核，发运暂缓");
      await user.type(within(observe.closest("form")!).getByLabelText("行动描述"),"查看待核记录");
      await user.click(observe);
    }
    const submissions=demo.calls.filter(c=>c.method==="POST"&&c.path.endsWith("/run-revisit"));
    expect(submissions).toHaveLength(mode==="lost-response" ? 2 : 1);
    if(mode==="lost-response") expect(submissions[0]).toEqual(submissions[1]);
    await screen.findByRole("button",{name:"封存待核记录"},{timeout:15000});
    demo.transport.transform=null;
    if(mode==="refresh-contradiction") {
      const saved=sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY);
      const marker=demo.calls.length;
      demo.transport.transform=(request,reply)=>{
        if(request.path.endsWith("/run-journey")) {
          const body=structuredClone(reply.body) as import("./api/schemas").NativeRunJourney;
          body.path.visit!.visit_id="contradictory.refreshed.visit";
          body.current.visit!.visit_id="contradictory.refreshed.visit";
          return {...reply,body};
        }
        return reply;
      };
      client=new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation});
      mounted.rerender(<App client={client} idempotencyKeyFactory={()=>"journey.revisit"}/>);
      await screen.findByRole("button",{name:"手动重试安全 GET"});
      expect(screen.queryByRole("button",{name:"封存待核记录"})).not.toBeInTheDocument();
      expect(demo.calls.slice(marker).every(c=>c.method==="GET")).toBe(true);
      expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(saved);
      demo.transport.transform=null;
      await user.click(screen.getByRole("button",{name:"手动重试安全 GET"}));
      await waitFor(()=>expect(screen.getByRole("button",{name:"封存待核记录"})).toBeEnabled());
    }
    const stored=sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!;
    const third=(JSON.parse(stored) as {session_id:string}).session_id;
    expect(Object.keys(JSON.parse(stored)).sort()).toEqual(["session_id","version"]);
    expect((await client.getSessionView(third)).metadata.state_version).toBe(1);
    mounted.unmount();
    client=new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation});
    const set=vi.spyOn(Storage.prototype,"setItem"),remove=vi.spyOn(Storage.prototype,"removeItem");
    const marker=demo.calls.length,before=await demo.inspect();
    mounted=render(<App client={client} idempotencyKeyFactory={()=>"journey.exit-and-fresh"}/>);
    await screen.findByRole("button",{name:"封存待核记录"},{timeout:10000});
    for(const [name,target] of [["查看上一世界历史",second],["查看上一世界历史",entered.session_id],
      ["查看下一段旅程",second],["查看下一段旅程",third]]) {
      const button=await screen.findByRole("button",{name:name!});
      await waitFor(()=>expect(button).toBeEnabled());
      await user.click(button);
      await waitFor(()=>expect(within(screen.getByRole("article")).getByText(target!,{exact:true})).toBeInTheDocument(),{timeout:10000});
    }
    await screen.findByRole("button",{name:"封存待核记录"});
    expect(screen.queryByText("正在阅读上一世界的历史。")).not.toBeInTheDocument();
    expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(stored);
    expect(set).not.toHaveBeenCalled();expect(remove).not.toHaveBeenCalled();
    expect(demo.calls.slice(marker).every(c=>c.method==="GET")).toBe(true);
    expect((await demo.inspect()).sha256).toBe(before.sha256);
    set.mockRestore();remove.mockRestore();
    await user.click(screen.getByRole("button",{name:choice==="seal"?"封存待核记录":"核验暂置"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled(),{timeout:15000});
    expect(screen.queryByRole("button",{name:"继续当前旅程"})).not.toBeInTheDocument();
    await user.click(screen.getByRole("button",{name:"结束本次旅程"}));
    await user.click(screen.getByRole("button",{name:"确认永久结束"}));
    await user.click(await screen.findByRole("button",{name:"返回设置"},{timeout:10000}));
    expect((await client.getNativeRunStatus(third)).run_state_version).toBe(6);
    await user.selectOptions(await screen.findByLabelText("选择难度"),"difficulty.open-expedition");
    await user.selectOptions(screen.getByLabelText("选择起始世界"),"world.death_certificate");
    await user.selectOptions(await screen.findByLabelText("Player Character"),created.player_character_id.value);
    await user.click(screen.getByRole("button",{name:"确认并开始"}));
    await waitFor(()=>expect(JSON.parse(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!).session_id).not.toBe(third),{timeout:10000});
    const fresh=JSON.parse(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!).session_id as string;
    await client.submitAction(fresh,{action_type:"OBSERVE",description:"查看环境",turn_id:"fresh.observe",client_request_id:"fresh.observe"});
    expect((await client.getSessionView(fresh)).metadata.state_version).toBe(1);
    mounted.unmount();
  } finally {vi.restoreAllMocks();demo.close();}
},120000);

function recoveryPair(progressed = false) {
  const association=(ordinal:1|2|3):NativeJourneyAssociation=>({session_id:["first","second","third"][ordinal-1]!,
    session_state_version:ordinal===3 ? (progressed?2:0) : 7,
    scenario_id:["death_certificate","undelivered_receipt","receipt_archive"][ordinal-1]!,
    scenario_content_version:["death-certificate-1.1.0","undelivered-receipt-1.0.0","receipt-archive-1.0.0"][ordinal-1]!,
    visit:{visit_id:`visit.${ordinal}`,visit_ordinal:ordinal,world_id:ordinal===1?"world.death_certificate":"world.undelivered_receipt",
      world_version:1,region_id:["region.death_certificate.facility","region.undelivered_receipt.dispatch_hall","region.undelivered_receipt.verification_archive"][ordinal-1]!,region_version:1}});
  const source=nativeViewFixture(endedViewFixture()),destination=nativeViewFixture();
  for(const [view,a] of [[source,association(2)],[destination,association(3)]] as const) {
    Object.assign(view.metadata,{session_id:a.session_id,state_version:a.session_state_version,content_version:a.scenario_content_version});
    Object.assign(view.player_state,{session_id:a.session_id,state_version:a.session_state_version,content_version:a.scenario_content_version});
    view.narrative_frame.scenario_id=a.scenario_id;
    playerSessionViewSchema.parse(view);
  }
  const before=nativeRunJourneySchema.parse({schema_version:"native-run-journey/v1",session_id:"second",run_id:source.run_context!.run_id,
    run_context:source.run_context,run_state_version:4,lifecycle_status:"active",path:association(2),current:association(2),predecessor:association(1),successor:null,
    next_transition:{kind:"regional_revisit",world_title:"未送达的回执",region_title:"核验档案室",notice:ARCHIVE_NOTICE},
    arrival:{previous_ending_status:"RESOLVED",previous_ending_title:"规程已中断",entry_notice:"上一世界已形成明确结果。你带着原有状态抵达发运大厅，当前队列从零开始计时。"}});
  const historical=nativeRunJourneySchema.parse({...before,run_state_version:5,current:association(3),successor:association(3),next_transition:null});
  const after=nativeRunJourneySchema.parse({...historical,session_id:"third",path:association(3),predecessor:association(2),successor:null,
    arrival:{previous_ending_status:"RESOLVED",previous_ending_title:"回执待核，发运暂缓",entry_notice:ARCHIVE_NOTICE}});
  const result=nativeRunRevisitResultSchema.parse({schema_version:"native-run-revisit-result/v1",source_session_id:"second",source_session_state_version:7,
    run_id:source.run_context!.run_id,resulting_run_state_version:5,session_id:"third",initial_session_state_version:0,
    scenario_id:"receipt_archive",scenario_content_version:"receipt-archive-1.0.0",run_context:source.run_context,visit:association(3).visit});
  return {source,destination,before,historical,after,result};
}

it.each(["target","visit","predecessor","content","matching","progressed","client-replacement"])(
  "F1 recovery %s: retained POST authority precedes storage and publication",async(mode)=>{
    const pair=recoveryPair(mode==="progressed"),events:string[]=[];
    let posted=false,failedInitial=false,valid=mode==="matching"||mode==="progressed",release:(()=>void)|undefined;
    const fetchImplementation:typeof fetch=async(input,init)=>{
      const route=new URL(String(input)).pathname,method=init?.method??"GET";
      events.push(`${method} ${route}`);
      let body:unknown;
      if(method==="POST") {expect(route).toBe("/v1/sessions/second/run-revisit");posted=true;body=pair.result;}
      else if(route.endsWith("/run-status")) body={schema_version:"native-run-status/v1",session_id:"second",run_id:pair.result.run_id,
        run_state_version:posted?5:4,session_state_version:7,lifecycle_status:"active",can_exit:!posted};
      else if(route.endsWith("/run-journey")) {
        const journey=structuredClone(route.includes("/second/") ? posted?pair.historical:pair.before : pair.after);
        if(posted && !valid) {
          if(mode==="target" || mode==="client-replacement") {
            journey.current.session_id="contradictory.third";
            if(journey.successor)journey.successor.session_id="contradictory.third";
            else {journey.session_id="contradictory.third";journey.path.session_id="contradictory.third";}
          }
          if(mode==="visit") {
            journey.current.visit!.visit_id="contradictory.visit";
            if(journey.successor)journey.successor.visit!.visit_id="contradictory.visit";
            else journey.path.visit!.visit_id="contradictory.visit";
          }
          if(mode==="predecessor" && !route.includes("/second/"))journey.predecessor!.visit!.visit_id="contradictory.source";
        }
        // Every negative reaches association validation, not schema rejection.
        body=nativeRunJourneySchema.parse(journey);
        if(mode==="client-replacement" && posted && !valid)await new Promise<void>(resolve=>{release=resolve;});
      } else if(route.endsWith("/view")) {
        if(!route.includes("/second/") && !failedInitial) {failedInitial=true;throw new TypeError("initial destination read failed");}
        const view=structuredClone(route.includes("/second/") ? pair.source : pair.destination);
        if(!valid && mode==="content" && !route.includes("/second/")) {
          view.metadata.content_version="contradictory-content-1.0.0";view.player_state.content_version=view.metadata.content_version;
        }
        body=playerSessionViewSchema.parse(view);
      } else throw new Error(`unexpected route ${route}`);
      return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
    };
    sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"second"}));
    const original=Storage.prototype.setItem;
    const set=vi.spyOn(Storage.prototype,"setItem").mockImplementation(function(this:Storage,key,value){
      events.push(`STORE ${JSON.parse(value).session_id}`);original.call(this,key,value);
    });
    const remove=vi.spyOn(Storage.prototype,"removeItem");
    const client=new PublicApiClient({baseUrl:"http://recovery/",fetchImplementation});
    const mounted=render(<App client={client} idempotencyKeyFactory={()=>"correction.revisit"}/>),user=userEvent.setup();
    try {
      await user.click(await screen.findByRole("button",{name:"继续当前旅程"}));
      await user.click(screen.getByRole("button",{name:"确认进入核验档案室"}));
      const retry=await screen.findByRole("button",{name:"读取续接状态"});
      await waitFor(()=>expect(retry).toBeEnabled());
      expect(failedInitial).toBe(true);
      const saved=sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY);
      expect(JSON.parse(saved!).session_id).toBe("third");
      expect(set).toHaveBeenCalledTimes(1);
      expect(events.indexOf("STORE third")).toBeLessThan(events.indexOf("GET /v1/sessions/third/view"));
      if(mode==="client-replacement") {
        await user.click(retry);await waitFor(()=>expect(release).toBeDefined());
        valid=true;
        mounted.rerender(<App client={new PublicApiClient({baseUrl:"http://recovery/",fetchImplementation})}/>);
        await waitFor(()=>expect(screen.getByRole("button",{name:"检查灯塔信号"})).toBeEnabled());
        await act(async()=>{release!();});
        expect(set).toHaveBeenCalledTimes(1);
      } else {
        if(!valid)for(let attempt=0;attempt<2;attempt++) {
          await user.click(retry);await waitFor(()=>expect(retry).toBeEnabled());
          expect(set).toHaveBeenCalledTimes(1);expect(remove).not.toHaveBeenCalled();
          expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(saved);
          expect(screen.queryByRole("button",{name:"检查灯塔信号"})).not.toBeInTheDocument();
          expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeDisabled();
          expect(screen.getByRole("button",{name:"重试原续接请求"})).toBeInTheDocument();
        }
        valid=true;const marker=events.length;
        await user.click(retry);
        await waitFor(()=>expect(screen.getByRole("button",{name:"检查灯塔信号"})).toBeEnabled());
        expect(set).toHaveBeenCalledTimes(2);
        const recovery=events.slice(marker);
        expect(recovery.indexOf("STORE third")).toBeGreaterThan(recovery.indexOf("GET /v1/sessions/third/run-journey"));
        expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(saved);
      }
      expect(events.filter(e=>e.startsWith("POST"))).toEqual(["POST /v1/sessions/second/run-revisit"]);
      expect(remove).not.toHaveBeenCalled();
      expect(screen.queryByRole("button",{name:"重试原续接请求"})).not.toBeInTheDocument();
    } finally {mounted.unmount();vi.restoreAllMocks();}
  });

it("F2 schema-valid terminal Journey blocks active View recovery and every write control",async()=>{
  const pair=recoveryPair(),events:string[]=[];let terminal=true;
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
  const client=new PublicApiClient({baseUrl:"http://lifecycle/",fetchImplementation:async(input,init)=>{
    const route=new URL(String(input)).pathname;events.push(`${init?.method??"GET"} ${route}`);
    const body=route.endsWith("/view") ? playerSessionViewSchema.parse(pair.destination) :
      nativeRunJourneySchema.parse({...pair.after,run_state_version:terminal?6:5,lifecycle_status:terminal?"terminated":"active"});
    return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
  }});
  const set=vi.spyOn(Storage.prototype,"setItem"),remove=vi.spyOn(Storage.prototype,"removeItem");
  const mounted=render(<App client={client}/>),user=userEvent.setup();
  try {
    await screen.findByRole("button",{name:"手动重试安全 GET"});
    for(const name of ["检查灯塔信号","继续当前旅程","确认进入核验档案室","结束本次旅程","确认永久结束"])
      expect(screen.queryByRole("button",{name})).not.toBeInTheDocument();
    expect(set).not.toHaveBeenCalled();expect(remove).not.toHaveBeenCalled();
    terminal=false;await user.click(screen.getByRole("button",{name:"手动重试安全 GET"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"检查灯塔信号"})).toBeEnabled());
    expect(events.every(e=>e.startsWith("GET"))).toBe(true);
  } finally {mounted.unmount();vi.restoreAllMocks();}
});

it("F2 exit reconciliation requires matching Journey and Run lifecycle snapshots",async()=>{
  const pair=recoveryPair(),view=nativeViewFixture(endedViewFixture());
  Object.assign(view.metadata,pair.destination.metadata,{phase:"ENDED",state_version:7});
  Object.assign(view.player_state,{session_id:"third",content_version:view.metadata.content_version,state_version:7});
  view.narrative_frame.scenario_id="receipt_archive";
  playerSessionViewSchema.parse(view);
  const journey=structuredClone(pair.after);journey.path.session_state_version=7;journey.current.session_state_version=7;
  let phase:"active"|"contradictory"|"terminated"="active";
  const events:string[]=[];
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
  const client=new PublicApiClient({baseUrl:"http://exit-recovery/",fetchImplementation:async(input,init)=>{
    const route=new URL(String(input)).pathname;events.push(`${init?.method??"GET"} ${route}`);
    const body=route.endsWith("/view") ? view : route.endsWith("/run-journey") ?
      nativeRunJourneySchema.parse({...journey,run_state_version:phase==="terminated"?6:5,lifecycle_status:phase==="terminated"?"terminated":"active"}) :
      {schema_version:"native-run-status/v1",session_id:"third",run_id:pair.result.run_id,session_state_version:7,
        run_state_version:phase==="active"?5:6,lifecycle_status:phase==="active"?"active":"terminated",can_exit:phase==="active"};
    return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
  }});
  const mounted=render(<App client={client}/>),user=userEvent.setup();
  try {
    await waitFor(()=>expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled(),{timeout:1000});
    phase="contradictory";await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
    await within(screen.getByRole("region",{name:"旅程状态"})).findByText(/CONTRACT_MISMATCH/);
    expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeDisabled();
    expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
    phase="terminated";await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"返回设置"})).toBeEnabled(),{timeout:1000});
    expect(events.every(e=>e.startsWith("GET"))).toBe(true);
  } finally {mounted.unmount();vi.restoreAllMocks();}
});

function consistencyFixture() {
  const pair=recoveryPair(),view=nativeViewFixture(endedViewFixture());
  Object.assign(view.metadata,pair.destination.metadata,{phase:"ENDED",state_version:7});
  Object.assign(view.player_state,{session_id:"third",content_version:view.metadata.content_version,state_version:7});
  view.narrative_frame.scenario_id="receipt_archive";
  const journey=structuredClone(pair.after);
  journey.path.session_state_version=7;journey.current.session_state_version=7;
  const status=nativeRunStatusSchema.parse({schema_version:"native-run-status/v1",session_id:"third",run_id:pair.result.run_id,
    session_state_version:7,run_state_version:5,lifecycle_status:"active",can_exit:true});
  return {view:playerSessionViewSchema.parse(view),journey:nativeRunJourneySchema.parse(journey),status};
}

it.each(["journey-first","status-first"])("consistency automatic sync %s: schema-valid contradictions block every POST and recover by GET",async(order)=>{
  for(const mode of ["terminal-active","active-terminal","same-revision","session","run","session-version"] as const) {
    const f=consistencyFixture(),calls:string[]=[];
    let matching=false,journeyReads=0,release:(()=>void)|undefined;
    const client=new PublicApiClient({baseUrl:"http://consistency/",fetchImplementation:async(input,init)=>{
      const route=new URL(String(input)).pathname;calls.push(`${init?.method??"GET"} ${route}`);
      let body:unknown;
      if(route.endsWith("/view"))body=f.view;
      else if(route.endsWith("/run-journey")) {
        journeyReads++;
        body=nativeRunJourneySchema.parse({...f.journey,...(!matching&&mode==="terminal-active"?{run_state_version:6,lifecycle_status:"terminated"}:{})});
        if(!matching && order==="status-first" && journeyReads===2)await new Promise<void>(r=>{release=r;});
      } else {
        body=nativeRunStatusSchema.parse({...f.status,...(!matching ?
          mode==="active-terminal"?{run_state_version:6,lifecycle_status:"terminated",can_exit:false}:
          mode==="same-revision"?{lifecycle_status:"terminated",can_exit:false}:
          mode==="session"?{session_id:"other"}:mode==="run"?{run_id:"other.run"}:
          mode==="session-version"?{session_state_version:8}:{} : {})});
        if(route.endsWith("/run-status") && !matching && order==="journey-first")await new Promise<void>(r=>{release=r;});
      }
      return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
    }});
    sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
    const mounted=render(<App client={client}/>),user=userEvent.setup();
    try {
      await waitFor(()=>expect(release).toBeDefined());
      expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeDisabled();
      await act(async()=>{release!();});
      await within(screen.getByRole("region",{name:"旅程状态"})).findByText(/CONTRACT_MISMATCH/);
      await user.click(screen.getByRole("button",{name:"结束本次旅程"}));
      expect(screen.queryByRole("button",{name:"确认永久结束"})).not.toBeInTheDocument();
      expect(screen.queryByRole("button",{name:"继续当前旅程"})).not.toBeInTheDocument();
      expect(screen.queryByRole("button",{name:"检查灯塔信号"})).not.toBeInTheDocument();
      expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
      matching=true;await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
      await waitFor(()=>expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled());
      expect(calls.every(c=>c.startsWith("GET"))).toBe(true);
      expect(JSON.parse(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!).session_id).toBe("third");
    } finally {mounted.unmount();sessionStorage.clear();}
  }
});

it.each(["active","terminated","historical"])("consistency matching %s preserves Run versus displayed Session lifecycle",async(mode)=>{
  const f=consistencyFixture(),pair=recoveryPair(),calls:string[]=[];
  const view=mode==="historical"?pair.source:f.view;
  const journey=nativeRunJourneySchema.parse(mode==="historical"?pair.historical:
    {...f.journey,...(mode==="terminated"?{run_state_version:6,lifecycle_status:"terminated"}:{})});
  const status=nativeRunStatusSchema.parse({...f.status,session_id:view.metadata.session_id,
    run_state_version:journey.run_state_version,lifecycle_status:journey.lifecycle_status,can_exit:mode==="active"});
  const client=new PublicApiClient({baseUrl:"http://consistent/",fetchImplementation:async(input,init)=>{
    const route=new URL(String(input)).pathname;calls.push(`${init?.method??"GET"} ${route}`);
    return new Response(JSON.stringify(route.endsWith("/view")?playerSessionViewSchema.parse(view):route.endsWith("/run-journey")?journey:status),
      {status:200,headers:{"Content-Type":"application/json"}});
  }});
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:view.metadata.session_id}));
  const mounted=render(<App client={client}/>);
  try {
    if(mode==="terminated")await waitFor(()=>expect(screen.getByRole("button",{name:"返回设置"})).toBeEnabled());
    else if(mode==="active")await waitFor(()=>expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled());
    else {
      await waitFor(()=>expect(screen.getByRole("button",{name:"查看上一世界历史"})).toBeEnabled());
      expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeDisabled();
      expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
      expect(screen.queryByRole("button",{name:"继续当前旅程"})).not.toBeInTheDocument();
    }
    expect(calls.every(c=>c.startsWith("GET"))).toBe(true);
  } finally {mounted.unmount();}
});

it.each(["open-confirmation","uncertain-request","history-read"])("consistency %s cannot authorize a POST after mismatching reconciliation",async(mode)=>{
  const f=consistencyFixture(),calls:string[]=[];let matching=true;
  const client=new PublicApiClient({baseUrl:"http://confirmation/",fetchImplementation:async(input,init)=>{
    const route=new URL(String(input)).pathname;calls.push(`${init?.method??"GET"} ${route}`);
    if(init?.method==="POST")throw new TypeError("lost response");
    const body=route.endsWith("/view")?f.view:route.endsWith("/run-journey")?
      nativeRunJourneySchema.parse({...f.journey,...(!matching?{run_state_version:6,lifecycle_status:"terminated"}:{})}):f.status;
    return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
  }});
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
  const mounted=render(<App client={client}/>),user=userEvent.setup();
  try {
    await waitFor(()=>expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled());
    await user.click(screen.getByRole("button",{name:"结束本次旅程"}));
    const name=mode==="uncertain-request"?"重试原结束请求":"确认永久结束";
    if(mode==="uncertain-request") {
      await user.click(screen.getByRole("button",{name:"确认永久结束"}));
      await waitFor(()=>expect(screen.getByRole("button",{name})).toBeEnabled());
    }
    matching=false;await user.click(screen.getByRole("button",{name:mode==="history-read"?"查看上一世界历史":"读取旅程状态"}));
    await within(screen.getByRole("region",{name:mode==="history-read"?"世界续接与历史":"旅程状态"})).findByText(/CONTRACT_MISMATCH/);
    expect(screen.getByRole("button",{name})).toBeDisabled();
    await user.click(screen.getByRole("button",{name}));
    expect(calls.filter(c=>c.startsWith("POST"))).toHaveLength(mode==="uncertain-request"?1:0);
    if(mode==="uncertain-request")expect(screen.getByText(/结束请求尚未确认/)).toBeInTheDocument();
    matching=true;await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:mode==="uncertain-request"?name:"结束本次旅程"})).toBeEnabled());
    expect(calls.filter(c=>c.startsWith("POST"))).toHaveLength(mode==="uncertain-request"?1:0);
  } finally {mounted.unmount();}
});

it.each(["client","target"])("consistency late matching response after %s replacement cannot reopen controls",async(mode)=>{
  const f=consistencyFixture(),calls:string[]=[];let release:(()=>void)|undefined,old=true;
  const fetchImplementation:typeof fetch=async(input,init)=>{
    const route=new URL(String(input)).pathname;calls.push(`${init?.method??"GET"} ${route}`);
    const current=structuredClone(f),replacement=route.includes("/replacement.third/");
    if(replacement) {
      current.view.metadata.session_id="replacement.third";current.view.player_state.session_id="replacement.third";
      current.journey.session_id="replacement.third";current.journey.path.session_id="replacement.third";current.journey.current.session_id="replacement.third";
      current.status.session_id="replacement.third";
    }
    let body:unknown;
    if(route.endsWith("/view"))body=playerSessionViewSchema.parse(current.view);
    else if(route.endsWith("/run-journey"))body=nativeRunJourneySchema.parse({...current.journey,...(!old?{run_state_version:6,lifecycle_status:"terminated"}:{})});
    else {
      body=nativeRunStatusSchema.parse(current.status);
      if(old && route.endsWith("/run-status"))await new Promise<void>(r=>{release=r;});
    }
    return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
  };
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
  const client=new PublicApiClient({baseUrl:"http://late/",fetchImplementation});
  const mounted=render(<App client={client}/>),user=userEvent.setup();
  try {
    await waitFor(()=>expect(release).toBeDefined());old=false;
    if(mode==="client")mounted.rerender(<App client={new PublicApiClient({baseUrl:"http://late/",fetchImplementation})}/>);
    else {
      const input=screen.getByLabelText("Session ID");await user.clear(input);await user.type(input,"replacement.third");
      await user.click(screen.getByRole("button",{name:"读取 PlayerSessionView"}));
    }
    await within(await screen.findByRole("region",{name:"旅程状态"})).findByText(/CONTRACT_MISMATCH/);
    await act(async()=>{release!();});
    expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeDisabled();
    expect(screen.queryByRole("button",{name:"确认永久结束"})).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
    expect(calls.every(c=>c.startsWith("GET"))).toBe(true);
  } finally {mounted.unmount();}
});

it("consistency revisit confirmation rechecks shared authority and preserves GET-only recovery",async()=>{
  const pair=recoveryPair(),calls:string[]=[];let matching=true;
  const client=new PublicApiClient({baseUrl:"http://revisit-consistency/",fetchImplementation:async(input,init)=>{
    const route=new URL(String(input)).pathname;calls.push(`${init?.method??"GET"} ${route}`);
    const body=route.endsWith("/view")?pair.source:route.endsWith("/run-journey")?pair.before:
      nativeRunStatusSchema.parse({schema_version:"native-run-status/v1",session_id:"second",run_id:pair.result.run_id,
        session_state_version:7,run_state_version:4,lifecycle_status:matching?"active":"terminated",can_exit:matching});
    return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
  }});
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"second"}));
  const mounted=render(<App client={client}/>),user=userEvent.setup();
  try {
    await user.click(await screen.findByRole("button",{name:"继续当前旅程"}));
    expect(screen.getByRole("button",{name:"确认进入核验档案室"})).toBeEnabled();
    matching=false;await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
    await within(screen.getByRole("region",{name:"旅程状态"})).findByText(/CONTRACT_MISMATCH/);
    expect(screen.getByRole("button",{name:"确认进入核验档案室"})).toBeDisabled();
    await user.click(screen.getByRole("button",{name:"确认进入核验档案室"}));
    expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeDisabled();
    matching=true;await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"继续当前旅程"})).toBeEnabled());
    expect(calls.every(c=>c.startsWith("GET"))).toBe(true);
  } finally {mounted.unmount();}
});

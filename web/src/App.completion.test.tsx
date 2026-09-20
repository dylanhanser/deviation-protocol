/// <reference types="node" />
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import path from "node:path";
import { act, configure, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import App from "./App";
import { PublicApiClient } from "./api/client";
import { nativeRunEntryResponseSchema, playerCharacterCreationResultSchema, actionRequestSchema, nativeRunCompletionResultSchema, playerSessionViewSchema } from "./api/schemas";
import { SESSION_RECOVERY_STORAGE_KEY } from "./sessionRecovery";
import {completionJourneyFixture} from "./test/fixtures";
import {nativeRunCompletionStatusSchema, nativeRunStatusSchema, nativeRunJourneySchema} from "./api/schemas";

configure({asyncUtilTimeout:10000});

function completedFixture() {
  const f=completionJourneyFixture();
  const completion={completion_id:"a".repeat(64),outcome:"unresolved_record_preserved",title:"待核事项保留，核验旅程已结案",
    notice:"本次旅程已正常完成。发运暂缓继续有效，送达仍未得到证明；旧记录与资源保持原状。",
    canon_outcome:{dispatch:"held",delivery:"unproven",record:"sealed",verification:"closed_unresolved"}};
  return {view:f.view,
    journey:nativeRunJourneySchema.parse({...f.journey,schema_version:"native-run-journey/v2",lifecycle_status:"completed",run_state_version:6,completion}),
    status:nativeRunStatusSchema.parse({...f.status,schema_version:"native-run-status/v2",lifecycle_status:"completed",run_state_version:6,can_exit:false}),
    completion:nativeRunCompletionStatusSchema.parse({...f.completion,lifecycle_status:"completed",run_state_version:6,can_complete:false,reason:"run_terminal",offer:null,completion}),
    result:nativeRunCompletionResultSchema.parse({schema_version:"native-run-completion-result/v1",source_session_id:"third",source_session_state_version:2,
      run_id:f.journey.run_id,resulting_run_state_version:6,lifecycle_status:"completed",run_context:f.journey.run_context,visit:f.journey.current.visit,completion})};
}

it.each(["explicit","automatic"])("R2 lost response retains exact retry across %s contradiction and matching reconciliation",async(path)=>{
  const active=completionJourneyFixture(),completed=completedFixture();
  let mode:"active"|"mismatch"|"completed"|"read-failure"="active",reads=0;
  const writes:{url:string;body:unknown;key:string|null}[]=[];
  const keys=vi.fn(()=>"r2.frozen.key");
  const client=new PublicApiClient({baseUrl:"http://r2/",fetchImplementation:async(input,init)=>{
    const route=new URL(String(input)).pathname;
    if(init?.method==="POST") {
      writes.push({url:String(input),body:init.body,key:new Headers(init.headers).get("Idempotency-Key")});
      if(writes.length===1)throw new TypeError("lost response");
      return new Response(JSON.stringify(completed.result),{status:200,headers:{"Content-Type":"application/json"}});
    }
    if(mode==="read-failure")throw new TypeError("temporary read failure");
    const f=mode==="completed"?completed:active;
    let body:unknown=route.endsWith("/view")?f.view:route.endsWith("/run-journey")?f.journey:route.endsWith("/run-status")?f.status:f.completion;
    if(route.endsWith("/run-completion") && mode==="mismatch" && (++reads>1 || path==="explicit"))
      body=nativeRunCompletionStatusSchema.parse({...active.completion,run_state_version:6,lifecycle_status:"terminated",can_complete:false,reason:"run_terminal",offer:null});
    return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
  }});
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
  render(<App client={client} idempotencyKeyFactory={keys}/>);
  const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"完成本次旅程"}));
  await user.click(screen.getByRole("button",{name:"确认结案并完成旅程"}));
  const retry=await screen.findByRole("button",{name:"重试原完成请求"});
  await waitFor(()=>expect(retry).toBeEnabled());
  mode="mismatch";
  await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
  await within(screen.getByRole("region",{name:"旅程状态"})).findByText(/CONTRACT_MISMATCH/);
  expect(retry).toBeDisabled();fireEvent.click(retry);
  expect(writes).toHaveLength(1);expect(keys).toHaveBeenCalledTimes(1);
  // A later network failure cannot erase a previously established contradiction.
  mode="read-failure";await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
  await waitFor(()=>expect(screen.getByRole("button",{name:"读取旅程状态"})).toBeEnabled());
  expect(retry).toBeDisabled();expect(writes).toHaveLength(1);
  mode="completed";await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
  await waitFor(()=>expect(retry).toBeEnabled());
  expect(writes).toHaveLength(1);expect(keys).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
  await user.click(retry);await screen.findByRole("button",{name:"返回设置"});
  expect(writes).toHaveLength(2);expect(writes[1]).toEqual(writes[0]);
  expect(writes[0]).toEqual({url:"http://r2/v1/sessions/third/run-complete",body:'{"expected_run_state_version":5,"expected_session_state_version":2}',key:"r2.frozen.key"});
  expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(JSON.stringify({version:1,session_id:"third"}));
});

it("R2 transient GET without contradiction preserves explicit exact retry; client replacement blocks stale dispatch",async()=>{
  const f=completionJourneyFixture(),writes:string[]=[];let failReads=false;
  const client=new PublicApiClient({baseUrl:"http://r2-transient/",fetchImplementation:async(input,init)=>{
    const route=new URL(String(input)).pathname;
    if(init?.method==="POST"){writes.push(JSON.stringify([String(input),init.body,new Headers(init.headers).get("Idempotency-Key")]));throw new TypeError("lost response");}
    if(failReads)throw new TypeError("temporary read failure");
    return new Response(JSON.stringify(route.endsWith("/view")?f.view:route.endsWith("/run-journey")?f.journey:route.endsWith("/run-status")?f.status:f.completion),{status:200,headers:{"Content-Type":"application/json"}});
  }});
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
  const mounted=render(<App client={client} idempotencyKeyFactory={()=>"retained"}/>),user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"完成本次旅程"}));
  await user.click(screen.getByRole("button",{name:"确认结案并完成旅程"}));
  const retry=await screen.findByRole("button",{name:"重试原完成请求"});
  await waitFor(()=>expect(retry).toBeEnabled());
  failReads=true;await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
  await waitFor(()=>expect(retry).toBeEnabled());await user.click(retry);
  await waitFor(()=>expect(retry).toBeEnabled());
  expect(writes).toHaveLength(2);expect(writes[1]).toBe(writes[0]);
  const replacementCalls:string[]=[];
  const replacement=new PublicApiClient({baseUrl:"http://r2-replaced/",fetchImplementation:async(input,init)=>{
    replacementCalls.push(init?.method??"GET");throw new TypeError(String(input));
  }});
  mounted.rerender(<App client={replacement} idempotencyKeyFactory={()=>"must-not-replace"}/>);
  expect(retry).toBeDisabled();fireEvent.click(retry);
  expect(writes).toHaveLength(2);expect(replacementCalls).not.toContain("POST");
});

it("R2 client replacement ignores a late completion result and retains the uncertain identity",async()=>{
  const f=completionJourneyFixture(),done=completedFixture();
  let release:((reply:Response)=>void)|undefined;
  const writes:{url:string;body:unknown;key:string|null}[]=[];
  const read=(input:RequestInfo|URL)=>{
    const route=new URL(String(input)).pathname;
    return new Response(JSON.stringify(route.endsWith("/view")?f.view:route.endsWith("/run-journey")?f.journey:route.endsWith("/run-status")?f.status:f.completion),
      {status:200,headers:{"Content-Type":"application/json"}});
  };
  const client=new PublicApiClient({baseUrl:"http://r2-late/",fetchImplementation:async(input,init)=>{
    if(init?.method==="POST") {
      writes.push({url:String(input),body:init.body,key:new Headers(init.headers).get("Idempotency-Key")});
      return await new Promise<Response>(resolve=>{release=resolve;});
    }
    return read(input);
  }});
  const keys=vi.fn(()=>"late.frozen");
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
  const mounted=render(<App client={client} idempotencyKeyFactory={keys}/>),user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"完成本次旅程"}));
  await user.click(screen.getByRole("button",{name:"确认结案并完成旅程"}));
  await waitFor(()=>expect(release).toBeDefined());
  const replacementCalls:string[]=[];
  const replacement=new PublicApiClient({baseUrl:"http://r2-late-replaced/",fetchImplementation:async(input,init)=>{
    replacementCalls.push(init?.method??"GET");return read(input);
  }});
  mounted.rerender(<App client={replacement} idempotencyKeyFactory={keys}/>);
  await act(async()=>release!(new Response(JSON.stringify(done.result),{status:200,headers:{"Content-Type":"application/json"}})));
  const retry=await screen.findByRole("button",{name:"重试原完成请求"});
  expect(retry).toBeDisabled();fireEvent.click(retry);
  expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
  expect(writes).toEqual([{url:"http://r2-late/v1/sessions/third/run-complete",body:'{"expected_run_state_version":5,"expected_session_state_version":2}',key:"late.frozen"}]);
  expect(keys).toHaveBeenCalledTimes(1);expect(replacementCalls).not.toContain("POST");
});

it("R2 a schema-valid GET for a replaced Session blocks uncertain retry",async()=>{
  const f=completionJourneyFixture();let wrong=false,posts=0;
  const other=playerSessionViewSchema.parse({...f.view,metadata:{...f.view.metadata,session_id:"other"},
    player_state:{...f.view.player_state,session_id:"other"}});
  const client=new PublicApiClient({baseUrl:"http://r2-target/",fetchImplementation:async(input,init)=>{
    if(init?.method==="POST"){posts++;throw new TypeError("lost response");}
    const route=new URL(String(input)).pathname;
    return new Response(JSON.stringify(route.endsWith("/view")?(wrong?other:f.view):route.endsWith("/run-journey")?f.journey:route.endsWith("/run-status")?f.status:f.completion),
      {status:200,headers:{"Content-Type":"application/json"}});
  }});
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
  render(<App client={client} idempotencyKeyFactory={()=>"same.target"}/>);const user=userEvent.setup();
  await user.click(await screen.findByRole("button",{name:"完成本次旅程"}));
  await user.click(screen.getByRole("button",{name:"确认结案并完成旅程"}));
  const retry=await screen.findByRole("button",{name:"重试原完成请求"});await waitFor(()=>expect(retry).toBeEnabled());
  wrong=true;await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
  await waitFor(()=>expect(screen.getByRole("button",{name:"读取旅程状态"})).toBeEnabled());
  expect(retry).toBeDisabled();fireEvent.click(retry);expect(posts).toBe(1);
  expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(JSON.stringify({version:1,session_id:"third"}));
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

it.each(["resolved","failed","lost-response","contradictory-result","storage-failure"])("A10 completion %s through actual Demo",async(profile)=>{
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
      profile_ref:{profile_id:profile==="resolved"?"difficulty.open-expedition":"difficulty.silent-hunting-ground",profile_version:1},
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

    const held=await client.getSessionView(second);
    const regional=await raw("POST",`v1/sessions/${second}/run-revisit`,{expected_run_state_version:4,
      expected_session_state_version:held.metadata.state_version},"completion.revisit") as {session_id:string};
    const third=regional.session_id;
    sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:third}));
    let mounted=render(<App client={client} idempotencyKeyFactory={()=>"completion.once"}/>);
    const user=userEvent.setup();
    const observe=await screen.findByRole("button",{name:"提交查看待核记录"});
    await user.type(within(observe.closest("form")!).getByLabelText("行动描述"),"查看待核记录");
    await user.click(observe);
    const seal=await screen.findByRole("button",{name:"封存待核记录"});
    await waitFor(()=>expect(seal).toBeEnabled());await user.click(seal);
    const offer=await screen.findByRole("button",{name:"完成本次旅程"});
    await waitFor(()=>expect(offer).toBeEnabled());
    const before=await demo.inspect(),stored=sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY);
    const set=vi.spyOn(Storage.prototype,"setItem"),remove=vi.spyOn(Storage.prototype,"removeItem");
    await user.click(offer);
    expect(screen.getByRole("dialog",{name:"确认完成旅程"})).toHaveTextContent("送达仍未得到证明");
    await user.click(screen.getByRole("button",{name:"取消完成"}));
    expect(demo.calls.filter(c=>c.path.endsWith("/run-complete"))).toHaveLength(0);
    expect((await demo.inspect()).sha256).toBe(before.sha256);
    let lost=false;
    demo.transport.transform=(request,reply)=>{
      if(profile==="lost-response" && request.path.endsWith("/run-complete") && !lost) {lost=true;throw new TypeError("lost completion acknowledgement");}
      if(profile==="contradictory-result" && request.method==="GET" && ["/run-journey","/run-completion"].some(p=>request.path.endsWith(p))) {
        const body=structuredClone(reply.body) as {completion?:{completion_id:string}};
        if(body.completion)body.completion.completion_id="a".repeat(64);
        return {...reply,body};
      }
      return reply;
    };
    await user.click(screen.getByRole("button",{name:"完成本次旅程"}));
    await user.click(screen.getByRole("button",{name:"确认结案并完成旅程"}));
    if(profile==="lost-response" || profile==="contradictory-result") {
      const retry=await screen.findByRole("button",{name:"重试原完成请求"});
      await waitFor(()=>expect(screen.getByRole("button",{name:"读取旅程状态"})).toBeEnabled());
      expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
      demo.transport.transform=null;
      if(profile==="contradictory-result") {
        await waitFor(()=>expect(screen.getByRole("button",{name:"读取旅程状态"})).toBeEnabled());
        await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
      }
      await waitFor(()=>expect(retry).toBeEnabled());
      if(profile==="contradictory-result") {
        demo.transport.transform=(request,reply)=>{
          if(request.path.endsWith("/run-complete")) {
            const body=structuredClone(reply.body) as {completion:{completion_id:string}};
            body.completion.completion_id="b".repeat(64);return {...reply,body};
          }
          return reply;
        };
        await user.click(retry);
        await waitFor(()=>expect(screen.getByRole("button",{name:"读取旅程状态"})).toBeEnabled());
        expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
        demo.transport.transform=null;
        await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
        await waitFor(()=>expect(retry).toBeEnabled());
      }
      await user.click(retry);
    }
    await screen.findByRole("button",{name:"返回设置"});
    expect(screen.getByText("待核事项保留，核验旅程已结案")).toBeInTheDocument();
    expect(set).not.toHaveBeenCalled();expect(remove).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(stored);
    const writes=demo.calls.filter(c=>c.path.endsWith("/run-complete"));
    expect(writes).toHaveLength(profile==="contradictory-result"?3:profile==="lost-response"?2:1);
    for(const write of writes)expect(write).toEqual(writes[0]);
    mounted.unmount();
    const marker=demo.calls.length,completed=await demo.inspect();
    client=new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation});
    mounted=render(<App client={client} idempotencyKeyFactory={()=>"completion.fresh"}/>);
    await screen.findByRole("button",{name:"返回设置"});
    for(const [name,target] of [["查看上一世界历史",second],["查看上一世界历史",entered.session_id],
      ["查看下一段旅程",second],["查看下一段旅程",third]]) {
      const button=await screen.findByRole("button",{name:name!});await waitFor(()=>expect(button).toBeEnabled());await user.click(button);
      await waitFor(()=>expect(within(screen.getByRole("article")).getByText(target!,{exact:true})).toBeInTheDocument());
    }
    await screen.findByRole("button",{name:"返回设置"});
    expect(demo.calls.slice(marker).every(c=>c.method==="GET")).toBe(true);
    expect((await demo.inspect()).sha256).toBe(completed.sha256);
    expect(set).not.toHaveBeenCalled();expect(remove).not.toHaveBeenCalled();
    if(profile==="storage-failure") {
      remove.mockImplementation(()=>{throw new DOMException("storage unavailable");});
      await user.click(screen.getByRole("button",{name:"返回设置"}));
      expect(screen.queryByRole("button",{name:"确认并开始"})).not.toBeInTheDocument();
      remove.mockRestore();
    }
    await user.click(screen.getByRole("button",{name:profile==="storage-failure"?"重试清除并返回设置":"返回设置"}));
    await user.selectOptions(await screen.findByLabelText("选择难度"),"difficulty.open-expedition");
    await user.selectOptions(screen.getByLabelText("选择起始世界"),"world.death_certificate");
    await user.selectOptions(await screen.findByLabelText("Player Character"),created.player_character_id.value);
    await user.click(screen.getByRole("button",{name:"确认并开始"}));
    await waitFor(()=>expect(JSON.parse(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!).session_id).not.toBe(third));
    const fresh=JSON.parse(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!).session_id as string;
    await client.submitAction(fresh,{action_type:"OBSERVE",description:"查看环境",turn_id:"fresh.observe",client_request_id:"fresh.observe"});
    expect((await client.getSessionView(fresh)).metadata.state_version).toBe(1);
    mounted.unmount();
  }finally{vi.restoreAllMocks();demo.close();}
},120000);

it.each(["completion-first","journey-first"])("A11 automatic four-read agreement %s",async(order)=>{
  for(const mode of ["lifecycle","visit","source","context","version"] as const) {
    const f=completionJourneyFixture(),calls:string[]=[];let valid=false,journeyReads=0,completionReads=0,release:(()=>void)|undefined;
    const client=new PublicApiClient({baseUrl:"http://completion-sync/",fetchImplementation:async(input,init)=>{
      const route=new URL(String(input)).pathname;calls.push(`${init?.method??"GET"} ${route}`);
      let body:unknown;
      if(route.endsWith("/view"))body=f.view;
      else if(route.endsWith("/run-status"))body=nativeRunStatusSchema.parse(f.status);
      else if(route.endsWith("/run-journey")) {
        journeyReads++;body=nativeRunJourneySchema.parse(f.journey);
        if(!valid && journeyReads===2 && order==="completion-first")await new Promise<void>(r=>{release=r;});
      } else if(route.endsWith("/run-completion")) {
        completionReads++;const c=structuredClone(f.completion);
        if(!valid && completionReads>1) {
          if(mode==="lifecycle")Object.assign(c,{run_state_version:6,lifecycle_status:"terminated",can_complete:false,reason:"run_terminal",offer:null});
          if(mode==="visit"){c.path.visit!.visit_id="wrong.visit";c.current.visit!.visit_id="wrong.visit";}
          if(mode==="source"){c.session_id="other";c.path.session_id="other";c.current.session_id="other";}
          if(mode==="context"){c.run_id="other.run";c.run_context.run_id="other.run";}
          if(mode==="version"){c.path.session_state_version=3;c.current.session_state_version=3;}
        }
        body=nativeRunCompletionStatusSchema.parse(c);
        if(!valid && completionReads===2 && order==="journey-first")await new Promise<void>(r=>{release=r;});
      } else throw new Error(`unexpected ${route}`);
      return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
    }});
    sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
    const mounted=render(<App client={client}/>),user=userEvent.setup();
    try {
      await waitFor(()=>expect(release).toBeDefined());
      expect(screen.queryByRole("button",{name:"完成本次旅程"})).not.toBeInTheDocument();
      expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeDisabled();
      await act(async()=>{release!();});
      await within(screen.getByRole("region",{name:"旅程状态"})).findByText(/CONTRACT_MISMATCH/);
      expect(screen.queryByRole("button",{name:"确认结案并完成旅程"})).not.toBeInTheDocument();
      valid=true;await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
      await waitFor(()=>expect(screen.getByRole("button",{name:"完成本次旅程"})).toBeEnabled());
      expect(calls.every(c=>c.startsWith("GET"))).toBe(true);
    } finally {mounted.unmount();sessionStorage.clear();}
  }
});

it("A11 opened completion cannot submit after a later contradictory GET",async()=>{
  const f=completionJourneyFixture(),calls:string[]=[];let matching=true;
  const client=new PublicApiClient({baseUrl:"http://completion-confirm/",fetchImplementation:async(input,init)=>{
    const route=new URL(String(input)).pathname;calls.push(`${init?.method??"GET"} ${route}`);
    const completion=nativeRunCompletionStatusSchema.parse({...f.completion,...(!matching?{run_state_version:6,lifecycle_status:"terminated",can_complete:false,reason:"run_terminal",offer:null}:{})});
    const body=route.endsWith("/view")?f.view:route.endsWith("/run-journey")?f.journey:route.endsWith("/run-status")?f.status:completion;
    return new Response(JSON.stringify(body),{status:200,headers:{"Content-Type":"application/json"}});
  }});
  sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:"third"}));
  const mounted=render(<App client={client}/>),user=userEvent.setup();
  try {
    await user.click(await screen.findByRole("button",{name:"完成本次旅程"}));
    expect(screen.getByRole("button",{name:"确认结案并完成旅程"})).toBeEnabled();
    matching=false;await user.click(screen.getByRole("button",{name:"读取旅程状态"}));
    await within(screen.getByRole("region",{name:"旅程状态"})).findByText(/CONTRACT_MISMATCH/);
    const confirm=screen.getByRole("button",{name:"确认结案并完成旅程"});expect(confirm).toBeDisabled();await user.click(confirm);
    expect(calls.every(c=>c.startsWith("GET"))).toBe(true);
  }finally{mounted.unmount();}
});

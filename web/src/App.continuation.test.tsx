/// <reference types="node" />
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import path from "node:path";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import App from "./App";
import { PublicApiClient } from "./api/client";
import { nativeRunEntryResponseSchema, playerCharacterCreationResultSchema, actionRequestSchema } from "./api/schemas";
import { SESSION_RECOVERY_STORAGE_KEY } from "./sessionRecovery";

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

it.each(["normal","failed-arrival","challenged-arrival","confirmed-visit","confirmed-predecessor","storage-visit","client-recovery-visit","progressed-valid","double-click","old-record","post-client","lost-response","malformed-response","exact-retry","storage-set","crossed-history","stale-return","stale-unmount","stale-client","continued-exit"])("C08 %s: public Demo play, explicit handoff, successor-only remount, history GET and return",async(mode)=>{
  const demo=await demoBridge();
  try {
    const raw=async(method:string,p:string,body?:object,key?:string)=>{
      const reply=await demo.fetchImplementation(`http://demo/${p}`,{method,headers:{"Content-Type":"application/json",...(key?{"Idempotency-Key":key}:{})},
        ...(body?{body:JSON.stringify(body)}:{})});
      const value:unknown=await reply.json();expect(reply.status,JSON.stringify(value)).toBe(200);return value;
    };
    const created=playerCharacterCreationResultSchema.parse(await raw("POST","v1/player-characters",{
      contract_version:"structured-player-character/v1",character_core:{},narration_preferences:{}},"c08.character"));
    const entered=nativeRunEntryResponseSchema.parse(await raw("POST","v1/runs/native",{
      player_character_id:created.player_character_id.value,expected_record_revision:1,
      profile_ref:{profile_id:mode==="failed-arrival"?"difficulty.silent-hunting-ground":"difficulty.open-expedition",profile_version:1},entry_world:{entry_world_id:"world.death_certificate",entry_world_version:1},
      overrides:[],presentation:{world_tone:"balanced",reality_boundary:"lawful",relationship_overlay:"off"}},"c08.entry"));
    const client=new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation});
    for(const [index,step]of demo.actions.entries()) {
      const view=await client.getSessionView(entered.session_id);
      if(view.scenario_status === "ENDED")break;
      await client.submitAction(entered.session_id,actionRequestSchema.parse({turn_id:`c08.turn.${index}`,client_request_id:`c08.action.${index}`,
        action_type:step.action_type,...(step.choice_id?{choice_id:mode==="challenged-arrival"&&step.choice_id.endsWith("final_suspend")?"death_certificate.action.final_disclose":step.choice_id,decision_id:view.narrative_frame.decision_id}:{}),
        ...(step.description?{description:step.description}:{})}));
    }
    expect((await client.getSessionView(entered.session_id)).scenario_status).toBe("ENDED");
    sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,JSON.stringify({version:1,session_id:entered.session_id}));
    let mounted=render(<App client={client} idempotencyKeyFactory={()=>"c08.continue"}/>);
    const user=userEvent.setup();
    await user.click(await screen.findByRole("button",{name:"继续当前旅程"}));
    await user.click(screen.getByRole("button",{name:"取消继续"}));
    expect(demo.calls.filter(c=>c.method==="POST"&&c.path.endsWith("/run-continuation"))).toHaveLength(0);
    await user.click(screen.getByRole("button",{name:"继续当前旅程"}));
    let failedPost=false;
    let postReply:Message|undefined;
    let releasePost:(reply:Message)=>void=()=>{};
    let contradicted=false;
    demo.transport.transform=async(request,reply)=>{
      if(request.method==="POST" && request.path.endsWith("/run-continuation")) {
        if(mode==="progressed-valid") {
          const result=reply.body as {session_id:string};
          await client.submitAction(result.session_id,{action_type:"OBSERVE",description:"核对收件台",turn_id:"advance.before.adopt",client_request_id:"advance.before.adopt"});
        }
        if(mode==="post-client" && !postReply){postReply=reply;return new Promise<Message>(resolve=>{releasePost=resolve;});}
        if(mode==="exact-retry" && !failedPost){failedPost=true;throw new TypeError("lost response");}
        if(mode==="lost-response" || mode==="old-record")throw new TypeError("lost response");
        if(mode==="malformed-response")return {...reply,body:{schema_version:"native-run-continuation-result/v1"}};
      }
      if (["confirmed-visit","confirmed-predecessor","storage-visit"].includes(mode) && request.method==="GET" &&
          request.path.endsWith("/run-continuation") && !request.path.includes(entered.session_id)) {
        contradicted=true;
        const body=reply.body as {visit:Record<string,unknown>;predecessor:Record<string,unknown>};
        return {...reply,body:{...body,...(mode==="confirmed-predecessor" ?
          {predecessor:{...body.predecessor,session_id:"unrelated.valid.session"}} : {visit:{...body.visit,visit_id:"unrelated.valid.visit"}})}};
      }
      return reply;
    };
    const originalSet=Storage.prototype.setItem;
    const fault=["storage-set","storage-visit"].includes(mode) ? vi.spyOn(Storage.prototype,"setItem").mockImplementation(function(this:Storage,key,value){
      if(key===SESSION_RECOVERY_STORAGE_KEY && !value.includes(entered.session_id))throw new DOMException("storage denied");
      originalSet.call(this,key,value);
    }) : null;
    if(mode==="double-click")await user.dblClick(screen.getByRole("button",{name:"确认进入下一世界"}));
    else await user.click(screen.getByRole("button",{name:"确认进入下一世界"}));
    if(mode==="post-client") {
      await waitFor(()=>expect(postReply).toBeDefined());
      mounted.rerender(<App client={new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation})}/>);
      await waitFor(()=>expect(screen.getByRole("button",{name:"重试原续接请求"})).toBeEnabled());
      releasePost(postReply!);
      expect(JSON.parse(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!).session_id).toBe(entered.session_id);
      await user.click(screen.getByRole("button",{name:"重试原续接请求"}));
    }
    if(mode==="old-record") {
      await screen.findByRole("button",{name:"重试原续接请求"});
      mounted.unmount();
      mounted=render(<App client={new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation})}/>);
      await waitFor(()=>expect(screen.getByRole("button",{name:"读取续接状态"})).toBeEnabled());
      await user.click(screen.getByRole("button",{name:"读取续接状态"}));
    }
    if(mode==="lost-response" || mode==="malformed-response" || mode==="exact-retry") {
      await screen.findByRole("button",{name:"重试原续接请求"});
      await waitFor(()=>expect(screen.getByRole("button",{name:"读取续接状态"})).toBeEnabled());
      expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeDisabled();
      await user.click(screen.getByRole("button",{name:mode==="exact-retry"?"重试原续接请求":"读取续接状态"}));
    }
    if(fault) {
      await screen.findByRole("button",{name:"重试保存已确认的下一世界"});
      fault.mockRestore();
      await user.click(screen.getByRole("button",{name:"重试保存已确认的下一世界"}));
    }
    if (["confirmed-visit","confirmed-predecessor","storage-visit"].includes(mode)) {
      await waitFor(()=>expect(contradicted).toBe(true));
      const retry=await screen.findByRole("button",{name:mode==="storage-visit"?"手动重试安全 GET":"读取续接状态"});
      await waitFor(()=>expect(retry).toBeEnabled());
      const confirmedStorage=sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY);
      expect(JSON.parse(confirmedStorage!).session_id).not.toBe(entered.session_id);
      expect(screen.queryByRole("button",{name:"查看上一世界历史"})).not.toBeInTheDocument();
      expect(screen.queryByLabelText("抵达说明")).not.toBeInTheDocument();
      expect(screen.queryByRole("heading",{name:"当前可执行行动"})).not.toBeInTheDocument();
      expect(demo.calls.filter(c=>c.method==="POST"&&c.path.endsWith("/run-continuation"))).toHaveLength(1);
      demo.transport.transform=null;
      await user.click(retry);
      await screen.findByRole("button",{name:"查看上一世界历史"});
      expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(confirmedStorage);
    }
    await screen.findByRole("button",{name:"查看上一世界历史"},{timeout:10000});
    const notice=mode==="failed-arrival"?"上一世界以失败结果结束。你带着原有状态抵达发运大厅，当前队列已经消耗四格期限。":
      "上一世界已形成明确结果。你带着原有状态抵达发运大厅，当前队列从零开始计时。";
    const endingTitle=mode==="failed-arrival"?"记录成为现实":mode==="challenged-arrival"?"记录已被质疑":"规程已中断";
    expect(screen.getByLabelText("抵达说明")).toHaveTextContent(endingTitle);
    expect(screen.getByLabelText("抵达说明")).toHaveTextContent(mode==="failed-arrival"?"FAILED":"RESOLVED");
    expect(screen.getByText(notice)).toBeInTheDocument();
    demo.transport.transform=null;
    const record=JSON.parse(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!) as {session_id:string;version:number};
    expect(record.session_id).not.toBe(entered.session_id);
    expect(Object.keys(record).sort()).toEqual(["session_id","version"]);
    if(mode==="client-recovery-visit") {
      const retainedStorage=sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY);
      demo.transport.transform=(request,reply)=>{
        if(request.path===`/v1/sessions/${record.session_id}/run-continuation`) {
          const body=reply.body as {visit:Record<string,unknown>};
          return {...reply,body:{...body,visit:{...body.visit,visit_id:"unrelated.valid.visit"}}};
        }
        return reply;
      };
      mounted.rerender(<App client={new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation})}/>);
      const retry=await screen.findByRole("button",{name:"手动重试安全 GET"});
      expect(screen.queryByRole("heading",{name:"当前可执行行动"})).not.toBeInTheDocument();
      expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(retainedStorage);
      expect(demo.calls.filter(c=>c.method==="POST"&&c.path.endsWith("/run-continuation"))).toHaveLength(1);
      demo.transport.transform=null;
      await user.click(retry);
      await screen.findByRole("button",{name:"查看上一世界历史"});
      expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(retainedStorage);
    }
    const renderedAction=["normal","failed-arrival","challenged-arrival"].includes(mode);
    if(renderedAction) {
      const button=screen.getByRole("button",{name:"提交核对收件台"});
      const form=button.closest("form")!;
      await user.type(within(form).getByLabelText("行动描述"),"核对收件台");
      await waitFor(()=>expect(button).toBeEnabled());
      await user.click(button);
      await waitFor(()=>expect(demo.calls.some(c=>c.method==="GET" && c.path===`/v1/sessions/${record.session_id}/run-continuation`)).toBe(true));
      await waitFor(()=>expect(screen.getByText(notice)).toBeInTheDocument(),{timeout:10000});
      await waitFor(()=>expect(screen.getByRole("button",{name:"查看上一世界历史"})).toBeEnabled(),{timeout:10000});
      expect((await client.getSessionView(record.session_id)).metadata.state_version).toBe(1);
    }
    mounted.unmount();
    if(mode!=="progressed-valid" && !renderedAction)await client.submitAction(record.session_id,{action_type:"OBSERVE",description:"核对收件台",turn_id:"c08.destination",client_request_id:"c08.destination"});
    const stored=sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY);
    const before=await demo.inspect();
    const marker=demo.calls.length;
    const set=vi.spyOn(Storage.prototype,"setItem"),remove=vi.spyOn(Storage.prototype,"removeItem");
    // New App instance and client retain only the v1 successor record.
    mounted=render(<App client={new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation})}/>);
    await screen.findByRole("button",{name:"查看上一世界历史"});
    expect(screen.getByText(notice)).toBeInTheDocument();
    expect(screen.getByLabelText("抵达说明")).toHaveTextContent(endingTitle);
    set.mockClear();remove.mockClear();
    if(mode.startsWith("stale-")) {
      let release:(reply:Message)=>void=()=>{};
      let retained:Message|undefined;
      demo.transport.transform=(request,reply)=>{
        if(request.path===`/v1/sessions/${entered.session_id}/view` && !retained) {
          retained=reply;return new Promise<Message>(resolve=>{release=resolve;});
        }
        return reply;
      };
      await user.click(screen.getByRole("button",{name:"查看上一世界历史"}));
      await waitFor(()=>expect(retained).toBeDefined());
      if(mode==="stale-return")await user.click(screen.getByRole("button",{name:"返回当前世界"}));
      else {
        const replacement=new PublicApiClient({baseUrl:"http://demo/",fetchImplementation:demo.fetchImplementation});
        if(mode==="stale-unmount"){mounted.unmount();mounted=render(<App client={replacement}/>);}
        else mounted.rerender(<App client={replacement}/>);
      }
      await waitFor(()=>expect(screen.getByRole("button",{name:"查看上一世界历史"})).toBeEnabled());
      release(retained!);
      await waitFor(()=>expect(screen.queryByText("正在阅读上一世界的历史。")).not.toBeInTheDocument());
      expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(stored);
      demo.transport.transform=null;
    }
    if(mode==="crossed-history") {
      demo.transport.transform=(request,reply)=>{
        if(request.path===`/v1/sessions/${entered.session_id}/run-continuation`) {
          const body=reply.body as {successor:Record<string,unknown>};
          return {...reply,body:{...body,successor:{...body.successor,session_id:"foreign.session"}}};
        }
        return reply;
      };
      await user.click(screen.getByRole("button",{name:"查看上一世界历史"}));
      await waitFor(()=>expect(screen.getByRole("button",{name:"查看上一世界历史"})).toBeEnabled());
      expect(screen.queryByText("正在阅读上一世界的历史。")).not.toBeInTheDocument();
      expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(stored);
      demo.transport.transform=null;
    }
    await user.click(await screen.findByRole("button",{name:"查看上一世界历史"}));
    await screen.findByText("正在阅读上一世界的历史。");
    expect(screen.queryByLabelText("抵达说明")).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"结束本次旅程"})).not.toBeInTheDocument();
    expect(screen.queryByRole("button",{name:"继续当前旅程"})).not.toBeInTheDocument();
    expect(screen.getByRole("button",{name:"清除本标签页 Session"})).toBeDisabled();
    expect(screen.getByRole("button",{name:"读取 PlayerSessionView"})).toBeDisabled();
    await user.click(screen.getByRole("button",{name:"返回当前世界"}));
    await waitFor(()=>expect(screen.queryByText("正在阅读上一世界的历史。")).not.toBeInTheDocument());
    expect(screen.getByText(notice)).toBeInTheDocument();
    expect(set).not.toHaveBeenCalled();expect(remove).not.toHaveBeenCalled();
    expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(stored);
    expect(demo.calls.slice(marker).every(c=>c.method==="GET")).toBe(true);
    expect((await demo.inspect()).sha256).toBe(before.sha256);
    const posts=demo.calls.filter(c=>c.method==="POST"&&c.path.endsWith("/run-continuation"));
    expect(posts).toHaveLength(mode==="exact-retry" || mode==="post-client"?2:1);
    if(mode==="exact-retry" || mode==="post-client")expect(posts[0]).toEqual(posts[1]);
    mounted.unmount();set.mockRestore();remove.mockRestore();
    if(mode==="continued-exit") {
      await client.submitAction(record.session_id,{action_type:"TALK",target_ids:["scenario-npc-1"],dialogue:"核对发运排程",
        turn_id:"c08.talk",client_request_id:"c08.talk"});
      const decision=await client.getSessionView(record.session_id);
      await client.submitAction(record.session_id,actionRequestSchema.parse({action_type:"CHOOSE",decision_id:decision.narrative_frame.decision_id,
        choice_id:"undelivered_receipt.action.hold",turn_id:"c08.hold",client_request_id:"c08.hold"}));
      mounted=render(<App client={client} idempotencyKeyFactory={()=>"c08.exit-and-fresh"}/>);
      await waitFor(()=>expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled());
      await user.click(screen.getByRole("button",{name:"结束本次旅程"}));
      await user.click(screen.getByRole("button",{name:"取消结束"}));
      expect(demo.calls.filter(c=>c.method==="POST"&&c.path.endsWith("/run-exit"))).toHaveLength(0);
      await user.click(screen.getByRole("button",{name:"结束本次旅程"}));
      await user.click(screen.getByRole("button",{name:"确认永久结束"}));
      await screen.findByRole("button",{name:"返回设置"});
      expect((await client.getNativeRunStatus(record.session_id)).run_state_version).toBe(5);
      const clear=vi.spyOn(Storage.prototype,"removeItem").mockImplementationOnce(()=>{throw new Error("storage clear denied");});
      await user.click(screen.getByRole("button",{name:"返回设置"}));
      await user.click(await screen.findByRole("button",{name:"重试清除并返回设置"}));
      clear.mockRestore();
      await screen.findByLabelText("选择难度");
      expect(screen.getByLabelText("选择难度")).toHaveValue("");
      expect(screen.getByLabelText("选择起始世界")).toHaveValue("");
      expect(screen.getByRole("button",{name:"确认并开始"})).toBeDisabled();
      expect(demo.calls.filter(c=>c.method==="POST"&&c.path==="/v1/runs/native")).toHaveLength(1);
      await user.selectOptions(screen.getByLabelText("选择难度"),"difficulty.open-expedition");
      await user.selectOptions(screen.getByLabelText("选择起始世界"),"world.death_certificate");
      await user.selectOptions(await screen.findByLabelText("Player Character"),created.player_character_id.value);
      await user.click(screen.getByRole("button",{name:"确认并开始"}));
      await waitFor(()=>expect(JSON.parse(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)!).session_id).not.toBe(record.session_id));
      expect(demo.calls.filter(c=>c.method==="POST"&&c.path==="/v1/runs/native")).toHaveLength(2);
      expect(demo.calls.filter(c=>c.method==="POST"&&c.path.endsWith("/run-exit"))).toHaveLength(1);
      mounted.unmount();
    }
  } finally {vi.restoreAllMocks();demo.close();}
},60000);

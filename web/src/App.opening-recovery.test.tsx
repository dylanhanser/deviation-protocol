import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import App from "./App";
import { PublicApiClient } from "./api/client";
import type { OpeningPreparation } from "./api/schemas";
import { openingRecoveryKey, readOpeningRecovery, writeOpeningRecovery } from "./openingRecovery";
import { readSessionRecoveryRecord, writeSessionRecoveryRecord } from "./sessionRecovery";
import { openingPreparedFixture, openingConfirmedFixture } from "./test/openingFixtures";
import { nativeEntryFixture, nativeViewFixture, nativeJourneyFixture, scenarioCatalogFixture, runOptionsFixture,
  eligiblePlayerCharactersFixture, playerCharacterFixture } from "./test/fixtures";

afterEach(()=>vi.restoreAllMocks());

function setup(baseUrl="http://test/") {
  const client=new PublicApiClient({baseUrl});
  vi.spyOn(client,"listScenarios").mockResolvedValue(scenarioCatalogFixture);
  vi.spyOn(client,"listRunEntryOptions").mockResolvedValue(runOptionsFixture);
  const eligible=vi.spyOn(client,"listEligiblePlayerCharacters").mockResolvedValue(eligiblePlayerCharactersFixture);
  const get=vi.spyOn(client,"getOpeningPreparation").mockResolvedValue(null);
  vi.spyOn(client,"prepareOpening").mockResolvedValue(openingPreparedFixture());
  const confirm=vi.spyOn(client,"confirmOpening");
  const native=vi.spyOn(client,"enterNativeRun");
  const legacy=vi.spyOn(client,"enterRun");
  const view=vi.spyOn(client,"getSessionView").mockResolvedValue(nativeViewFixture());
  const journey=vi.spyOn(client,"getNativeRunJourney").mockResolvedValue(nativeJourneyFixture());
  vi.spyOn(client,"getJourneyRecap").mockRejectedValue(new Error("no recap in focused fixture"));
  vi.spyOn(client,"getOpeningTalents").mockResolvedValue(openingPreparedFixture().candidates.slice(0,2));
  return {client,eligible,get,confirm,native,legacy,view,journey};
}

async function selectAndConfirm() {
  await screen.findByLabelText("Player Character");
  await waitFor(()=>expect(screen.getByRole("button",{name:"原生 Run 设置"})).toBeEnabled());
  fireEvent.click(screen.getByRole("button",{name:"原生 Run 设置"}));
  fireEvent.change(screen.getByLabelText("Player Character"),{target:{value:playerCharacterFixture.player_character_id.value}});
  fireEvent.change(screen.getByLabelText("选择难度"),{target:{value:"difficulty.open-expedition"}});
  fireEvent.change(screen.getByLabelText("选择起始世界"),{target:{value:"world.death_certificate"}});
  await waitFor(()=>expect(screen.getByRole("button",{name:"查看开局天赋"})).toBeEnabled());
  fireEvent.click(screen.getByRole("button",{name:"查看开局天赋"}));
  const group=await screen.findByRole("group",{name:"天赋（恰好选择两项）"});
  const boxes=within(group).getAllByRole("checkbox");
  fireEvent.click(boxes[0]!);fireEvent.click(boxes[1]!);
  fireEvent.click(screen.getByRole("button",{name:"确认天赋并开始"}));
}

it.each([true,false])("lost confirmation + fresh mount recovers committed=%s by GET without eligibility",async committed=>{
  const f=setup();let runs=0;
  const pending=openingPreparedFixture(),confirmed=openingConfirmedFixture(nativeEntryFixture());
  f.confirm.mockImplementation(async()=>{
    expect(readOpeningRecovery(f.client)).toEqual({ok:true,value:{version:1,character_id:pending.character_id,preparation_id:pending.preparation_id}});
    if (committed) runs++;
    f.eligible.mockResolvedValue({eligible_player_characters:[],truncated:false});
    f.get.mockResolvedValue(committed ? confirmed : pending);
    throw new Error("lost response");
  });
  const first=render(<App client={f.client}/>);
  await selectAndConfirm();
  await waitFor(()=>expect(f.confirm).toHaveBeenCalledTimes(1));
  await act(async()=>{});
  first.unmount();
  const before=f.get.mock.calls.length;
  render(<App client={f.client}/>);
  const button=await screen.findByRole("button",{name:committed ? "读取已开始的旅程" : "确认天赋并开始"});
  expect(f.get.mock.calls.length).toBeGreaterThan(before);
  expect(screen.queryByLabelText("Player Character")).not.toBeInTheDocument();
  expect(f.confirm).toHaveBeenCalledTimes(1);
  expect(f.native).not.toHaveBeenCalled();expect(f.legacy).not.toHaveBeenCalled();
  if (committed) {
    fireEvent.click(button);
    await screen.findByText("当前 Session：session-public-1");
    expect(readSessionRecoveryRecord()).toEqual({ok:true,value:{version:1,session_id:confirmed.result!.session_id}});
    expect(f.view).toHaveBeenCalledWith(confirmed.result!.session_id,expect.any(AbortSignal));
    expect(await within(screen.getByRole("region",{name:"本次旅程的天赋"})).findByText(/临机决断/)).toBeVisible();
    expect(readOpeningRecovery(f.client)).toEqual({ok:true,value:null});
  } else {
    expect(button).toBeDisabled(); // No stored choice is silently selected or submitted.
    expect(f.view).not.toHaveBeenCalled();
    expect(readOpeningRecovery(f.client).ok).toBe(true);
  }
  expect(f.confirm).toHaveBeenCalledTimes(1);expect(runs).toBe(committed?1:0);
});

it("failed storage blocks confirmation before POST and permits explicit retry",async()=>{
  const f=setup();
  const original=Storage.prototype.setItem;
  const write=vi.spyOn(Storage.prototype,"setItem").mockImplementation(function(this:Storage,key,value){
    if(key===openingRecoveryKey(f.client)) throw new Error("quota");
    return original.call(this,key,value);
  });
  render(<App client={f.client}/>);
  await selectAndConfirm();
  await screen.findByText(/无法保存开局恢复入口/);
  expect(f.confirm).not.toHaveBeenCalled();
  write.mockRestore();
  f.confirm.mockRejectedValue(new Error("no response"));
  fireEvent.click(screen.getByRole("button",{name:"确认天赋并开始"}));
  await waitFor(()=>expect(f.confirm).toHaveBeenCalledTimes(1));
});

it.each(["missing","foreign character","stale preparation","network","malformed storage"])("isolates %s recovery and keeps the reference",async kind=>{
  const f=setup();const record=openingPreparedFixture();
  expect(writeOpeningRecovery(f.client,record).ok).toBe(true);
  if(kind==="malformed storage") sessionStorage.setItem(openingRecoveryKey(f.client),'{"version":99}');
  else if(kind==="network") f.get.mockRejectedValue(new Error("offline"));
  else f.get.mockResolvedValue(kind==="missing"?null:{...record,
    ...(kind==="foreign character"?{character_id:"character.foreign"}:{preparation_id:"b".repeat(32)})});
  const raw=sessionStorage.getItem(openingRecoveryKey(f.client));
  render(<App client={f.client}/>);
  await screen.findByRole("button",{name:"重读开局恢复"});
  expect(sessionStorage.getItem(openingRecoveryKey(f.client))).toBe(raw);
  expect(f.confirm).not.toHaveBeenCalled();expect(f.view).not.toHaveBeenCalled();
  if(kind==="network") {
    f.get.mockResolvedValue(record);
    fireEvent.click(screen.getByRole("button",{name:"重读开局恢复"}));
    await screen.findByRole("button",{name:"确认天赋并开始"});
  }
});

it.each(["character","Run","Session","Journey"])("rejects contradictory %s authority before saving Session",async kind=>{
  const f=setup();const record=openingConfirmedFixture(nativeEntryFixture());
  if(kind==="character") record.result!.run_context.player_character.player_character_id.value="character.other";
  if(kind==="Run") record.result!.run_context.run_id="run.other";
  if(kind==="Session") record.result!.session_id="session.other";
  if(kind==="Journey") f.journey.mockResolvedValue({...nativeJourneyFixture(),run_id:"run.other"});
  writeOpeningRecovery(f.client,record);f.get.mockResolvedValue(record);
  render(<App client={f.client}/>);
  const button=await screen.findByRole("button",{name:"读取已开始的旅程"});
  fireEvent.click(button);
  await screen.findByText(/开局恢复尚未完成/);
  expect(readSessionRecoveryRecord()).toEqual({ok:true,value:null});
  expect(sessionStorage.getItem(openingRecoveryKey(f.client))).not.toBeNull();
  expect(f.confirm).not.toHaveBeenCalled();
});

it("existing Session recovery wins over an older opening locator",async()=>{
  const f=setup();writeOpeningRecovery(f.client,openingPreparedFixture());
  writeSessionRecoveryRecord("session-public-1");
  render(<App client={f.client}/>);
  await screen.findByText("当前 Session：session-public-1");
  expect(f.get).not.toHaveBeenCalled();expect(f.confirm).not.toHaveBeenCalled();
});

it("late recovery after client replacement cannot publish an old offer; API scopes stay isolated",async()=>{
  const a=setup(),b=setup("http://other/");
  let resolve!:(record:OpeningPreparation)=>void;
  a.get.mockReturnValue(new Promise(r=>{resolve=r;}));
  writeOpeningRecovery(a.client,openingPreparedFixture());
  const app=render(<App client={a.client}/>);
  await waitFor(()=>expect(a.get).toHaveBeenCalledTimes(1));
  app.rerender(<App client={b.client}/>);
  await act(async()=>resolve(openingConfirmedFixture(nativeEntryFixture())));
  expect(b.get).not.toHaveBeenCalled();
  expect(screen.queryByRole("button",{name:"读取已开始的旅程"})).not.toBeInTheDocument();
  expect(readSessionRecoveryRecord()).toEqual({ok:true,value:null});
});

it("a newer confirmed Session saved while GET waits cannot be overwritten",async()=>{
  const f=setup(),record=openingConfirmedFixture(nativeEntryFixture());
  writeOpeningRecovery(f.client,record);f.get.mockResolvedValue(record);
  let resolve!:(view:ReturnType<typeof nativeViewFixture>)=>void;
  f.view.mockReturnValue(new Promise(r=>{resolve=r;}));
  render(<App client={f.client}/>);
  fireEvent.click(await screen.findByRole("button",{name:"读取已开始的旅程"}));
  await waitFor(()=>expect(f.view).toHaveBeenCalledTimes(1));
  writeSessionRecoveryRecord("session.newer");
  await act(async()=>resolve(nativeViewFixture()));
  expect(readSessionRecoveryRecord()).toEqual({ok:true,value:{version:1,session_id:"session.newer"}});
  expect(screen.queryByText("当前 Session：session-public-1")).not.toBeInTheDocument();
});

it("an uncertain explicit confirmation retry checks storage again before POST",async()=>{
  const f=setup();f.confirm.mockRejectedValue(new Error("lost response"));
  render(<App client={f.client}/>);
  await selectAndConfirm();
  const retry=await screen.findByRole("button",{name:"手动重试完全相同的操作"});
  await waitFor(()=>expect(retry).toBeEnabled());
  vi.spyOn(Storage.prototype,"setItem").mockImplementation(()=>{throw new Error("quota after first send");});
  fireEvent.click(retry);
  await screen.findByText(/无法保存开局恢复入口/);
  expect(f.confirm).toHaveBeenCalledTimes(1);
});

it("same API client replacement ignores a late confirmation-recovery read",async()=>{
  const a=setup(),b=setup();const record=openingConfirmedFixture(nativeEntryFixture());
  writeOpeningRecovery(a.client,record);a.get.mockResolvedValue(record);b.get.mockRejectedValue(new Error("foreign owner"));
  let resolve!:(view:ReturnType<typeof nativeViewFixture>)=>void;
  a.view.mockReturnValue(new Promise(r=>{resolve=r;}));
  const app=render(<App client={a.client}/>);
  fireEvent.click(await screen.findByRole("button",{name:"读取已开始的旅程"}));
  await waitFor(()=>expect(a.view).toHaveBeenCalledTimes(1));
  app.rerender(<App client={b.client}/>);
  await screen.findByRole("button",{name:"重读开局恢复"});
  await act(async()=>resolve(nativeViewFixture()));
  expect(readSessionRecoveryRecord()).toEqual({ok:true,value:null});
  expect(screen.queryByText("当前 Session：session-public-1")).not.toBeInTheDocument();
  expect(a.confirm).not.toHaveBeenCalled();expect(b.confirm).not.toHaveBeenCalled();
});

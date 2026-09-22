import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import App from "./App";
import { PublicApiClient } from "./api/client";
import { openingConfirmedFixture, openingPreparedFixture } from "./test/openingFixtures";
import { eligiblePlayerCharactersFixture, nativeEntryFixture, playerCharacterFixture, runOptionsFixture, scenarioCatalogFixture } from "./test/fixtures";
import { readOpeningRecovery, writeOpeningRecovery } from "./openingRecovery";

function setup() {
  const client = new PublicApiClient({baseUrl:"http://station-test/"});
  const options = structuredClone(runOptionsFixture);
  options.entry_worlds.push({...options.entry_worlds[0]!,entry_world:{entry_world_id:"world.fog_station",entry_world_version:1},
    scenario_id:"fog_station",scenario_content_version:"fog-station-1.0.0",title:"雾哨站"});
  vi.spyOn(client,"listScenarios").mockResolvedValue(scenarioCatalogFixture);
  vi.spyOn(client,"listRunEntryOptions").mockResolvedValue(options);
  vi.spyOn(client,"listEligiblePlayerCharacters").mockResolvedValue(eligiblePlayerCharactersFixture);
  const get = vi.spyOn(client,"getOpeningPreparation").mockResolvedValue(null);
  const prepare = vi.spyOn(client,"prepareOpening").mockImplementation(async attempt => openingPreparedFixture(JSON.parse(attempt.serializedBody)));
  const confirm = vi.spyOn(client,"confirmOpening").mockRejectedValue(new Error("focused test stops after explicit confirmation"));
  const native = vi.spyOn(client,"enterNativeRun");
  const legacy = vi.spyOn(client,"enterRun");
  return {client, options, get, prepare, confirm, native, legacy};
}

async function selectCharacter() {
  await waitFor(()=>expect(screen.getByRole("button",{name:"原生 Run 设置"})).toBeEnabled());
  fireEvent.click(screen.getByRole("button",{name:"原生 Run 设置"}));
  fireEvent.change(screen.getByLabelText("Player Character"),{target:{value:playerCharacterFixture.player_character_id.value}});
}

it.each(["world.fog_station", "world.death_certificate"])("uses the issued station preparation even when the submitted selection was %s", async selectedWorld => {
  const {client,options,prepare,confirm,native,legacy}=setup();
  const issued=openingPreparedFixture();
  issued.admission.entry_world=structuredClone(options.entry_worlds[1]!.entry_world);
  // An existing pending offer can be returned even if new submitted settings differ.
  prepare.mockResolvedValue(issued);
  const before=structuredClone(issued);
  render(<App client={client}/>);
  await selectCharacter();
  fireEvent.change(screen.getByLabelText("选择难度"),{target:{value:"difficulty.open-expedition"}});
  fireEvent.change(screen.getByLabelText("选择起始世界"),{target:{value:selectedWorld}});
  expect(prepare).not.toHaveBeenCalled();
  await waitFor(()=>expect(screen.getByRole("button",{name:"查看开局天赋"})).toBeEnabled());
  fireEvent.click(screen.getByRole("button",{name:"查看开局天赋"}));
  await screen.findByRole("group",{name:"天赋（恰好选择两项）"});
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(JSON.parse(prepare.mock.calls[0]![0].serializedBody).entry_world).toEqual({entry_world_id:selectedWorld,entry_world_version:1});
  expect(screen.getByText(/初始世界：雾哨站/)).toBeVisible();
  expect(screen.getByLabelText("选择起始世界")).toHaveValue(selectedWorld);
  expect(confirm).not.toHaveBeenCalled();
  expect(native).not.toHaveBeenCalled();
  expect(legacy).not.toHaveBeenCalled();
  const boxes=within(screen.getByRole("group",{name:"天赋（恰好选择两项）"})).getAllByRole("checkbox");
  fireEvent.click(boxes[0]!);
  fireEvent.click(boxes[1]!);
  expect(confirm).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button",{name:"确认天赋并开始"}));
  await waitFor(()=>expect(confirm).toHaveBeenCalledTimes(1));
  const [frozen,record,selected]=confirm.mock.calls[0]!;
  expect(JSON.parse(frozen.serializedBody)).toEqual(before.admission);
  expect(frozen.world).toEqual(options.entry_worlds[1]);
  expect(record).toEqual(before);
  expect(selected).toEqual(["T001","T006"]);
  expect(issued).toEqual(before);
  expect(readOpeningRecovery(client)).toEqual({ok:true,value:{version:1,character_id:issued.character_id,preparation_id:issued.preparation_id}});
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(native).not.toHaveBeenCalled();
  expect(legacy).not.toHaveBeenCalled();
});

it("reloads the same pending station offer through GET with reordered discovery and no automatic POST", async () => {
  const f=setup();
  const record=openingPreparedFixture();
  record.admission.entry_world=structuredClone(f.options.entry_worlds[1]!.entry_world);
  f.prepare.mockResolvedValue(record);
  const before=structuredClone(record);
  const first=render(<App client={f.client}/>);
  await selectCharacter();
  fireEvent.change(screen.getByLabelText("选择难度"),{target:{value:"difficulty.open-expedition"}});
  fireEvent.change(screen.getByLabelText("选择起始世界"),{target:{value:"world.fog_station"}});
  await waitFor(()=>expect(screen.getByRole("button",{name:"查看开局天赋"})).toBeEnabled());
  fireEvent.click(screen.getByRole("button",{name:"查看开局天赋"}));
  await screen.findByText(/初始世界：雾哨站/);
  const cards=screen.getByRole("group",{name:"天赋（恰好选择两项）"}).textContent;
  first.unmount();
  f.get.mockResolvedValue(record);
  vi.mocked(f.client.listRunEntryOptions).mockResolvedValue({...f.options,entry_worlds:[...f.options.entry_worlds].reverse()});
  const reads=f.get.mock.calls.length;
  render(<App client={f.client}/>);
  await selectCharacter();
  await screen.findByText(/初始世界：雾哨站/);
  expect(f.get.mock.calls.length).toBeGreaterThan(reads);
  expect(f.get).toHaveBeenLastCalledWith(record.character_id,expect.any(AbortSignal));
  expect(screen.getByRole("group",{name:"天赋（恰好选择两项）"}).textContent).toBe(cards);
  expect(record).toEqual(before);
  expect(screen.getByLabelText("选择起始世界")).toHaveValue("");
  expect(f.prepare).toHaveBeenCalledTimes(1);
  expect(f.confirm).not.toHaveBeenCalled();
  expect(f.native).not.toHaveBeenCalled();
  expect(f.legacy).not.toHaveBeenCalled();
  const boxes=within(screen.getByRole("group",{name:"天赋（恰好选择两项）"})).getAllByRole("checkbox");
  fireEvent.click(boxes[0]!);
  fireEvent.click(boxes[1]!);
  fireEvent.click(screen.getByRole("button",{name:"确认天赋并开始"}));
  await waitFor(()=>expect(f.confirm).toHaveBeenCalledTimes(1));
  expect(JSON.parse(f.confirm.mock.calls[0]![0].serializedBody)).toEqual(before.admission);
  expect(f.confirm.mock.calls[0]![1]).toEqual(before);
});

it("restores the confirmed station summary from its locator without admission or preparation POST", async () => {
  const f=setup();
  const record=openingConfirmedFixture(nativeEntryFixture());
  const world=f.options.entry_worlds[1]!;
  record.admission.entry_world=structuredClone(world.entry_world);
  record.result!.run_context.entry_world=structuredClone(world.entry_world);
  record.result!.scenario_id=world.scenario_id;
  record.result!.scenario_content_version=world.scenario_content_version;
  f.get.mockResolvedValue(record);
  expect(writeOpeningRecovery(f.client,record).ok).toBe(true);
  const before=readOpeningRecovery(f.client);
  render(<App client={f.client}/>);
  await screen.findByText(/初始世界：雾哨站/);
  const group=screen.getByRole("group",{name:"天赋（恰好选择两项）"});
  expect(within(group).getAllByRole("checkbox",{checked:true})).toHaveLength(2);
  expect(within(group).getAllByRole("checkbox").every(c => c.matches(":disabled"))).toBe(true);
  expect(screen.getByRole("button",{name:"读取已开始的旅程"})).toBeEnabled();
  expect(readOpeningRecovery(f.client)).toEqual(before);
  expect(f.prepare).not.toHaveBeenCalled();
  expect(f.confirm).not.toHaveBeenCalled();
  expect(f.native).not.toHaveBeenCalled();
  expect(f.legacy).not.toHaveBeenCalled();
});

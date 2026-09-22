import { fireEvent, screen, within, waitFor } from "@testing-library/react";
import type { NativeRunEntryRequest, NativeRunEntryResponse, OpeningPreparation } from "../api/schemas";
import { nativeEntryFixture } from "./fixtures";

export function openingPreparedFixture(admission?:NativeRunEntryRequest):OpeningPreparation {
  const result=nativeEntryFixture();
  return {schema_version:"opening-preparation/v1",preparation_id:"a".repeat(32),character_id:admission?.player_character_id ?? result.run_context.player_character.player_character_id.value,
    catalog_version:"opening-talents/v1",state:"PENDING",admission:admission ?? {
      player_character_id:result.run_context.player_character.player_character_id.value,expected_record_revision:1,
      profile_ref:result.run_context.profile_ref,entry_world:result.run_context.entry_world,overrides:[],presentation:result.run_context.presentation},
    candidates:[{id:"T001",name:"临机决断",tier:"TOP",description:"探索与自由行动的额外耗时各减少 1 点。"},
      {id:"T006",name:"巧舌如簧",tier:"TRADEOFF",description:"交谈额外耗时减少 1 点，探索增加 1 点。"},
      {id:"T026",name:"能言善道",tier:"ORDINARY",description:"交谈额外耗时减少 1 点。"},
      {id:"T027",name:"明察秋毫",tier:"ORDINARY",description:"观察额外耗时减少 1 点。"},
      {id:"T061",name:"沉默寡言",tier:"WEAK",description:"交谈额外耗时增加 1 点。"}],selected_ids:[],result:null};
}

export function openingConfirmedFixture(result:NativeRunEntryResponse):OpeningPreparation {
  return {...openingPreparedFixture(),state:"CONFIRMED",selected_ids:["T001","T006"],result};
}

export async function prepareAndConfirmFirstTwo() {
  await waitFor(() => {if (screen.getByRole("button",{name:"查看开局天赋"}).matches(":disabled")) throw new Error("Opening preparation is loading");});
  fireEvent.click(screen.getByRole("button",{name:"查看开局天赋"}));
  const group=await screen.findByRole("group",{name:"天赋（恰好选择两项）"});
  const boxes=within(group).getAllByRole("checkbox");
  fireEvent.click(boxes[0]!);fireEvent.click(boxes[1]!);
  fireEvent.click(screen.getByRole("button",{name:"确认天赋并开始"}));
}

import { render, screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import { SessionReading } from "./SessionReading";
import { nativeViewFixture, nativeJourneyFixture, runOptionsFixture } from "./test/fixtures";
import { playerSessionViewSchema, runEntryOptionsSchema, nativeRunJourneyV1Schema } from "./api/schemas";

function stationView() {
  const view = nativeViewFixture();
  view.metadata.content_version = "fog-station-1.0.0";
  view.player_state.content_version = view.metadata.content_version;
  view.run_context!.entry_world = {entry_world_id:"world.fog_station", entry_world_version:1};
  view.relationship = {presentation_version:1,npc_name:"岑舟",npc_age:32,scope:"THIS_SESSION",stage:"信任",
    residence:"暂住中",activities_used:["复盘脱险"],remaining_slots:2,
    shared_experiences:["共同固定挡板。", "曾在哨站短暂停留；已共同进行：复盘脱险。"],reunited:false};
  return view;
}

it("renders bounded activity accounting and actual shared experience as plain text", () => {
  const view = stationView();
  view.relationship!.shared_experiences.push("<img src=x onerror=alert(1)>未经解释的文字");
  const {container} = render(<SessionReading view={view} staleKind={null}/>);
  const panel = screen.getByRole("region", {name:"哨站关系与暂住"});
  expect(within(panel).getByText("2 / 3")).toBeVisible();
  expect(within(panel).getByText(/每项活动只能进行一次/)).toBeVisible();
  expect(within(panel).getByText(/不决定你对岑舟的感情/)).toBeVisible();
  expect(within(panel).getByText(/<img src=x/)).toBeVisible();
  expect(container.querySelector("img, script")).toBeNull();
});

it("retains departure experience in historical reading without offering residence controls", () => {
  const view = stationView();
  view.relationship!.residence = "已离开";
  view.relationship!.remaining_slots = 0;
  render(<SessionReading view={view} staleKind={null} readingIdentity="historical"/>);
  const panel = screen.getByRole("region",{name:"这次访问的关系与暂住记录"});
  expect(within(panel).getByText("已离开")).toBeVisible();
  expect(within(panel).getByText(/复盘脱险/)).toBeVisible();
  expect(within(panel).queryByRole("button")).toBeNull();
  expect(within(panel).queryByText("剩余活动次数")).toBeNull();
});

it("validates native identity, stage, distinct activities and residence quota", () => {
  const view = stationView();
  expect(playerSessionViewSchema.safeParse(view).success).toBe(true);
  for (const patch of [{remaining_slots:3},{stage:"合作"},{activities_used:["复盘脱险","复盘脱险"]},{reunited:true}]) {
    expect(playerSessionViewSchema.safeParse({...view,relationship:{...view.relationship,...patch}}).success).toBe(false);
  }
  expect(playerSessionViewSchema.safeParse({...view,run_context:undefined}).success).toBe(false);
  expect(playerSessionViewSchema.safeParse({...view,metadata:{...view.metadata,content_version:"other"}}).success).toBe(false);
});

it("accepts the two native starting worlds and rejects duplicate world identities", () => {
  const options = structuredClone(runOptionsFixture);
  options.entry_worlds.push({...options.entry_worlds[0]!,entry_world:{entry_world_id:"world.fog_station",entry_world_version:1},
    scenario_id:"fog_station",scenario_content_version:"fog-station-1.0.0",title:"雾哨站"});
  expect(runEntryOptionsSchema.safeParse(options).success).toBe(true);
  options.entry_worlds[1] = options.entry_worlds[0]!;
  expect(runEntryOptionsSchema.safeParse(options).success).toBe(false);
});

it("binds station journey recovery to its admitted world and forbids continuation", () => {
  const view = stationView();
  const journey = nativeJourneyFixture(view);
  journey.path.scenario_id = "fog_station";
  journey.path.scenario_content_version = "fog-station-1.0.0";
  journey.current = structuredClone(journey.path);
  expect(nativeRunJourneyV1Schema.safeParse(journey).success).toBe(true);
  expect(nativeRunJourneyV1Schema.safeParse({...journey,run_context:{...journey.run_context,
    entry_world:{entry_world_id:"world.death_certificate",entry_world_version:1}}}).success).toBe(false);
  expect(nativeRunJourneyV1Schema.safeParse({...journey,next_transition:{kind:"first_continuation",world_title:"未送达的回执",
    region_title:"发运大厅",notice:"沿用当前角色和剩余资源进入发运大厅；原有资源不会恢复。"}}).success).toBe(false);
});

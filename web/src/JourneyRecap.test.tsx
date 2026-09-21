import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import App from "./App";
import { JourneyRecap } from "./JourneyRecap";
import { PublicApiClient } from "./api/client";
import { journeyRecapSchema, nativeRunJourneySchema, playerSessionViewSchema, type JourneyRecap as Recap, type NativeRunJourney } from "./api/schemas";
import { completionJourneyFixture, completionStatusFixture } from "./test/fixtures";
import { SESSION_RECOVERY_STORAGE_KEY } from "./sessionRecovery";

function recapFor(journey: NativeRunJourney, text = "已核实回顾。", status: Recap["status"] = "complete"): Recap {
  const historical = journey.path.session_id !== journey.current.session_id;
  return journeyRecapSchema.parse({schema_version: "native-run-recap/v1", session_id: journey.session_id,
    context: {run_id: journey.run_id, run_state_version: journey.run_state_version,
      session_state_version: journey.path.session_state_version, scenario_id: journey.path.scenario_id,
      content_version: journey.path.scenario_content_version, cutoff_visit: journey.path.visit?.visit_ordinal ?? 1,
      scope: historical ? "historical" : "current", lifecycle_at_cutoff: historical ? "active" : journey.lifecycle_status},
    status, text});
}
function pair() {
  const current = completionJourneyFixture();
  const second = current.journey.predecessor!;
  const view = structuredClone(current.view);
  for (const metadata of [view.metadata, view.player_state]) Object.assign(metadata, {
    session_id: second.session_id, state_version: second.session_state_version, content_version: second.scenario_content_version});
  view.narrative_frame.scenario_id = second.scenario_id;
  view.ending_id = "undelivered_receipt.ending.held_for_review";
  const journey = nativeRunJourneySchema.parse({...current.journey, session_id: "second", path: second,
    predecessor: {session_id:"first",session_state_version:10,scenario_id:"death_certificate",scenario_content_version:"death-certificate-1.1.0",
      visit:{visit_id:"visit.1",visit_ordinal:1,world_id:"world.death_certificate",world_version:1,region_id:"region.death_certificate.facility",region_version:1}},
    successor:current.journey.current,
    arrival:{previous_ending_status:"RESOLVED",previous_ending_title:"规程已中断",entry_notice:"上一世界已形成明确结果。你带着原有状态抵达发运大厅，当前队列从零开始计时。"}});
  return {current, history:{view:playerSessionViewSchema.parse(view), journey}};
}

it("parses code-point limits, closed fields and coherent unavailable states", () => {
  const f = completionJourneyFixture(), base = recapFor(f.journey);
  for (const length of [1999,2000,2001]) expect(journeyRecapSchema.safeParse({...base,text:"😀".repeat(length)}).success).toBe(length <= 2000);
  expect(journeyRecapSchema.safeParse({...base,private_binding:"no"}).success).toBe(false);
  expect(journeyRecapSchema.safeParse({...base,context:null}).success).toBe(false);
  expect(journeyRecapSchema.safeParse({...base,status:"unavailable_evidence"}).success).toBe(false);
  expect(journeyRecapSchema.safeParse({...base,status:"unavailable_overflow",text:"",context:null}).success).toBe(false);
});

it.each([
  ["complete", "已核实回顾。", "已核实回顾。"],
  ["incomplete", "已核实回顾。", "部分补充内容缺失或因容量限制省略"],
  ["unavailable_evidence", "", "缺少必要证据或证据存在冲突"],
  ["unavailable_overflow", "", "必要记录超出回顾容量"],
] as const)("renders %s through a GET-only client without storage", async(status,text,message) => {
  const f = completionJourneyFixture(); const calls: string[] = [];
  const client = new PublicApiClient({baseUrl:"http://recap/",fetchImplementation:async(input,init) => {
    calls.push(`${init?.method} ${String(input)}`);
    return Response.json(recapFor(f.journey,text,status));
  }});
  const set = vi.spyOn(Storage.prototype,"setItem"), remove = vi.spyOn(Storage.prototype,"removeItem");
  try {
    render(<JourneyRecap client={client} view={f.view} journey={f.journey} ready />);
    fireEvent.click(screen.getByText("旅程回顾"));
    await screen.findByText(new RegExp(message));
    expect(screen.getByText("本次旅程 · 截至当前第 3 次访问。")).toBeVisible();
    expect(calls).toEqual(["GET http://recap/v1/sessions/third/run-recap"]);
    expect(set).not.toHaveBeenCalled(); expect(remove).not.toHaveBeenCalled();
  } finally {vi.restoreAllMocks();}
});

it("suppresses pending/unconfirmed and replaced responses, including a replaced client", async() => {
  const {current, history} = pair(); let release: (() => void) | undefined;
  const old = new PublicApiClient({baseUrl:"http://recap/",fetchImplementation:async() => {
    await new Promise<void>(resolve => {release = resolve;});
    return Response.json(recapFor(history.journey,"旧回顾不得替换新访问。"));
  }});
  const fresh = new PublicApiClient({baseUrl:"http://recap/",fetchImplementation:async() => Response.json(recapFor(current.journey))});
  const mounted = render(<JourneyRecap client={old} view={history.view} journey={history.journey} ready={false} />);
  fireEvent.click(screen.getByText("旅程回顾"));
  expect(screen.getByText("访问关联尚未确认，暂不展示回顾。")).toBeVisible();
  expect(release).toBeUndefined();
  mounted.rerender(<JourneyRecap client={old} view={history.view} journey={history.journey} ready />);
  await waitFor(() => expect(release).toBeDefined());
  mounted.rerender(<JourneyRecap client={fresh} view={current.view} journey={current.journey} ready />);
  await screen.findByText("已核实回顾。");
  await act(async() => {release!();});
  expect(screen.queryByText("旧回顾不得替换新访问。")).not.toBeInTheDocument();
  mounted.rerender(<JourneyRecap client={fresh} view={current.view} journey={current.journey} ready={false} />);
  expect(screen.queryByText("已核实回顾。")).not.toBeInTheDocument();
});

it.each(["run", "session", "version", "content", "cutoff", "network"])("rejects %s mismatch without claiming current progress", async(kind) => {
  const f = completionJourneyFixture(), row = recapFor(f.journey, "不能显示的回顾");
  if (kind === "run") row.context!.run_id = "different";
  if (kind === "session") row.session_id = "different";
  if (kind === "version") row.context!.session_state_version++;
  if (kind === "content") row.context!.content_version = "other-version";
  if (kind === "cutoff") row.context!.cutoff_visit = 2;
  const client = new PublicApiClient({baseUrl:"http://recap/",fetchImplementation:async() => {
    if (kind === "network") throw new TypeError("offline");
    return Response.json(row);
  }});
  render(<JourneyRecap client={client} view={f.view} journey={f.journey} ready />);
  fireEvent.click(screen.getByText("旅程回顾"));
  await screen.findByText(/旅程回顾暂时无法读取/);
  expect(screen.queryByText("不能显示的回顾")).not.toBeInTheDocument();
});

it.each(["second", "third"])("App restores %s, keeps recovery and controls, and reloads using only GET", async(sid) => {
  const {current, history} = pair(), calls: string[] = [];
  const client = new PublicApiClient({baseUrl:"http://recap/",fetchImplementation:async(input,init) => {
    const route = new URL(String(input)).pathname;
    calls.push(`${init?.method ?? "GET"} ${route}`);
    const f = route.includes("/second/") ? history : current;
    const body = route.endsWith("/view") ? f.view : route.endsWith("/run-journey") ? f.journey
      : route.endsWith("/run-recap") ? recapFor(f.journey)
      : route.endsWith("/run-completion") ? completionStatusFixture(f.journey)
      : {...current.status,session_id:f.journey.session_id,session_state_version:f.view.metadata.state_version,can_exit:sid === "third"};
    return Response.json(body);
  }});
  const stored = JSON.stringify({version:1,session_id:sid}); sessionStorage.setItem(SESSION_RECOVERY_STORAGE_KEY,stored);
  const set = vi.spyOn(Storage.prototype,"setItem"), remove = vi.spyOn(Storage.prototype,"removeItem");
  let mounted = render(<App client={client} />);
  try {
    await screen.findByText("旅程回顾"); fireEvent.click(screen.getByText("旅程回顾"));
    await screen.findByText(sid === "second" ? "历史回顾 · 截至第 2 次访问，不含之后的经历。" : "本次旅程 · 截至当前第 3 次访问。");
    if (sid === "third") {
      expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled();
      fireEvent.click(screen.getByRole("button",{name:"查看上一世界历史"}));
      await screen.findByText("历史访问（只读），不是当前进度。");
      fireEvent.click(screen.getByText("旅程回顾"));
      await screen.findByText("历史回顾 · 截至第 2 次访问，不含之后的经历。");
      fireEvent.click(screen.getByRole("button",{name:"返回当前世界"}));
      await screen.findByText("权威 View：当前");
    }
    mounted.unmount(); mounted = render(<App client={client} />);
    await screen.findByText("旅程回顾"); fireEvent.click(screen.getByText("旅程回顾"));
    await screen.findByText("已核实回顾。");
    expect(sessionStorage.getItem(SESSION_RECOVERY_STORAGE_KEY)).toBe(stored);
    expect(set).not.toHaveBeenCalled(); expect(remove).not.toHaveBeenCalled();
    expect(calls.every(call => call.startsWith("GET "))).toBe(true);
  } finally {mounted.unmount();vi.restoreAllMocks();}
});

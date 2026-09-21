import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, delay, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { PublicApiClient } from "./api/client";
import { ApiClientError } from "./api/errors";
import {
  SESSION_RECOVERY_STORAGE_KEY,
  readSessionRecoveryRecord,
  writeSessionRecoveryRecord,
} from "./sessionRecovery";
import {
  activeViewFixture,
  eligiblePlayerCharactersFixture,
  endedViewFixture,
  errorFixture,
  minimalPlayerCharacterCreationFixture,
  playerCharacterFixture,
  runEntryRequestFixture,
  runEntryResponseFixture,
  scenarioCatalogFixture,
  runOptionsFixture,
  nativeEntryFixture, nativeViewFixture, nativeJourneyFixture, completionStatusFixture,
} from "./test/fixtures";
import { server } from "./test/server";

const apiOrigin = "http://ui-api.test";
const testClient = new PublicApiClient({ baseUrl: `${apiOrigin}/` });

describe("S7-1 explicit exit and return to setup", () => {
  function setup() {
    const client = new PublicApiClient({baseUrl:`${apiOrigin}/`});
    const view = nativeViewFixture(endedViewFixture("FAILED"));
    writeSessionRecoveryRecord(view.metadata.session_id);
    vi.spyOn(client,"listScenarios").mockResolvedValue(scenarioCatalogFixture);
    vi.spyOn(client,"listEligiblePlayerCharacters").mockResolvedValue(eligiblePlayerCharactersFixture);
    vi.spyOn(client,"listRunEntryOptions").mockResolvedValue(runOptionsFixture);
    vi.spyOn(client,"getSessionView").mockResolvedValue(view);
    const journey = vi.spyOn(client,"getNativeRunJourney").mockResolvedValue(nativeJourneyFixture(view));
    const active = {schema_version:"native-run-status/v1" as const, session_id:view.metadata.session_id,
      run_id:view.run_context!.run_id, session_state_version:view.metadata.state_version,
      run_state_version:3, lifecycle_status:"active" as const, can_exit:true};
    const terminal = {...active,run_state_version:4,lifecycle_status:"terminated" as const,can_exit:false};
    const status = vi.spyOn(client,"getNativeRunStatus").mockResolvedValue(active);
    vi.spyOn(client,"getNativeRunCompletion").mockImplementation(async () => completionStatusFixture(await journey.getMockImplementation()!(view.metadata.session_id)));
    const exit = vi.spyOn(client,"exitNativeRun").mockImplementation(async () => {
      status.mockResolvedValue(terminal);
      journey.mockResolvedValue({...nativeJourneyFixture(view),run_state_version:4,lifecycle_status:"terminated"});
      return terminal;
    });
    const entry = vi.spyOn(client,"enterNativeRun");
    return {client,view,active,terminal,status,journey,exit,entry};
  }

  it("confirms once, preserves history/storage, and requires explicit reselection after return", async () => {
    const c = setup(); render(<App client={c.client} idempotencyKeyFactory={() => "exit.once"}/>);
    const button = await screen.findByRole("button",{name:"结束本次旅程"});
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button); fireEvent.click(screen.getByRole("button",{name:"取消结束"}));
    expect(c.exit).not.toHaveBeenCalled();
    fireEvent.click(button); fireEvent.click(screen.getByRole("button",{name:"确认永久结束"}));
    await screen.findByRole("button",{name:"返回设置"});
    expect(c.exit).toHaveBeenCalledTimes(1); expect(c.entry).not.toHaveBeenCalled();
    expect(readSessionRecoveryRecord()).toEqual({ok:true,value:{version:1,session_id:c.view.metadata.session_id}});
    fireEvent.click(screen.getByRole("button",{name:"返回设置"}));
    await screen.findByLabelText("选择难度");
    expect(screen.getByLabelText("选择难度")).toHaveValue("");
    expect(screen.getByLabelText("选择起始世界")).toHaveValue("");
    expect(screen.getByRole("button",{name:"确认并开始"})).toBeDisabled();
    expect(c.entry).not.toHaveBeenCalled();
  });

  it("keeps a lost committed response through GET and requires exact explicit retry", async () => {
    const c = setup();
    c.exit.mockImplementation(async () => {
      c.status.mockResolvedValue(c.terminal);
      c.journey.mockResolvedValue({...nativeJourneyFixture(c.view),run_state_version:4,lifecycle_status:"terminated"});
      throw new ApiClientError("lost",{kind:"network"});
    });
    render(<App client={c.client} idempotencyKeyFactory={() => "exit.once"}/>);
    await waitFor(() => expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"结束本次旅程"}));
    fireEvent.click(screen.getByRole("button",{name:"确认永久结束"}));
    await screen.findByRole("button",{name:"重试原结束请求"});
    await waitFor(() => expect(screen.getByRole("button",{name:"读取旅程状态"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"读取旅程状态"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"重试原结束请求"})).toBeEnabled());
    expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
    expect(c.exit).toHaveBeenCalledTimes(1);
    c.exit.mockResolvedValue(c.terminal);
    fireEvent.click(screen.getByRole("button",{name:"重试原结束请求"}));
    await screen.findByRole("button",{name:"返回设置"});
    expect(c.exit).toHaveBeenCalledTimes(2); expect(c.entry).not.toHaveBeenCalled();
  });

  it("retries the exact exit and keeps storage-clear retry separate", async () => {
    const c = setup(); c.exit.mockRejectedValueOnce(new ApiClientError("lost",{kind:"network"}));
    render(<App client={c.client} idempotencyKeyFactory={() => "exit.once"}/>);
    await waitFor(() => expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"结束本次旅程"}));
    fireEvent.click(screen.getByRole("button",{name:"确认永久结束"}));
    await waitFor(() => expect(screen.getByRole("button",{name:"重试原结束请求"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"重试原结束请求"}));
    await screen.findByRole("button",{name:"返回设置"});
    expect(c.exit.mock.calls[0]?.[0]).toBe(c.exit.mock.calls[1]?.[0]);
    const remove = vi.spyOn(Storage.prototype,"removeItem").mockImplementationOnce(() => {throw new Error("blocked");});
    fireEvent.click(screen.getByRole("button",{name:"返回设置"}));
    await screen.findByRole("button",{name:"重试清除并返回设置"});
    expect(screen.getByText(`当前 Session：${c.view.metadata.session_id}`)).toBeVisible();
    expect(c.entry).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"重试清除并返回设置"}));
    await screen.findByLabelText("选择难度");
    expect(c.exit).toHaveBeenCalledTimes(2); expect(remove).toHaveBeenCalledTimes(2);
  });

  it("reloads a terminal journey using only GET without preserving exit intent in storage", async () => {
    const c = setup(); c.status.mockResolvedValue(c.terminal);
    c.journey.mockResolvedValue({...nativeJourneyFixture(c.view),run_state_version:4,lifecycle_status:"terminated"});
    render(<App client={c.client}/>);
    await screen.findByRole("button",{name:"返回设置"});
    expect(c.exit).not.toHaveBeenCalled(); expect(c.entry).not.toHaveBeenCalled();
    expect(readSessionRecoveryRecord()).toEqual({ok:true,value:{version:1,session_id:c.view.metadata.session_id}});
  });

  it.each(["session_id", "run_id", "session_state_version"] as const)("locks a mismatched status %s", async (field) => {
    const c = setup(); c.status.mockResolvedValue({...c.active,[field]:field === "session_state_version" ? c.active.session_state_version + 1 : "other"});
    render(<App client={c.client}/>);
    await waitFor(() => expect(c.status).toHaveBeenCalled());
    expect(screen.queryByRole("button",{name:"结束本次旅程"})).not.toBeInTheDocument();
    expect(c.exit).not.toHaveBeenCalled();
  });

  it("ignores an exit response after unmount and does not clear storage", async () => {
    const c = setup(); let resolve!: (value:typeof c.terminal) => void;
    c.exit.mockReturnValue(new Promise((done) => {resolve=done;}));
    const mounted = render(<App client={c.client}/>);
    await waitFor(() => expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"结束本次旅程"}));
    fireEvent.click(screen.getByRole("button",{name:"确认永久结束"}));
    await waitFor(() => expect(c.exit).toHaveBeenCalledTimes(1));
    mounted.unmount();
    await act(async () => {resolve(c.terminal);});
    expect(readSessionRecoveryRecord()).toEqual({ok:true,value:{version:1,session_id:c.view.metadata.session_id}});
    expect(c.entry).not.toHaveBeenCalled();
  });

  it("retains the exact uncertain request across client replacement and ignores the old response", async () => {
    const c = setup(); let resolve!: (value:typeof c.terminal) => void;
    c.exit.mockReturnValue(new Promise((done) => {resolve=done;}));
    const mounted = render(<App client={c.client}/>);
    await waitFor(() => expect(screen.getByRole("button",{name:"结束本次旅程"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"结束本次旅程"}));
    fireEvent.click(screen.getByRole("button",{name:"确认永久结束"}));
    await waitFor(() => expect(c.exit).toHaveBeenCalledTimes(1));
    const next = setup();
    mounted.rerender(<App client={next.client}/>);
    await act(async () => {resolve(c.terminal);});
    expect(screen.queryByRole("button",{name:"返回设置"})).not.toBeInTheDocument();
    expect(next.exit).not.toHaveBeenCalled();
    expect(screen.getByRole("button",{name:"重试原结束请求"})).toBeDisabled();
    expect(next.exit).not.toHaveBeenCalled();
    mounted.rerender(<App client={c.client}/>);
    c.exit.mockResolvedValue(c.terminal);c.status.mockResolvedValue(c.terminal);
    c.journey.mockResolvedValue({...nativeJourneyFixture(c.view),run_state_version:4,lifecycle_status:"terminated"});
    await waitFor(() => expect(screen.getByRole("button",{name:"读取旅程状态"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"读取旅程状态"}));
    await waitFor(() => expect(screen.getByRole("button",{name:"重试原结束请求"})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"重试原结束请求"}));
    await screen.findByRole("button",{name:"返回设置"});
    expect(c.exit.mock.calls[1]?.[0]).toBe(c.exit.mock.calls[0]?.[0]);
  });

  it("reassesses DF-002: separate GET retries restore return-to-setup discovery without admission", async () => {
    const c = setup(); c.status.mockResolvedValue(c.terminal);
    c.journey.mockResolvedValue({...nativeJourneyFixture(c.view),run_state_version:4,lifecycle_status:"terminated"});
    vi.mocked(c.client.listRunEntryOptions).mockResolvedValueOnce(runOptionsFixture).mockRejectedValueOnce(new ApiClientError("options unavailable",{kind:"network"})).mockResolvedValue(runOptionsFixture);
    vi.mocked(c.client.listEligiblePlayerCharacters).mockResolvedValueOnce(eligiblePlayerCharactersFixture).mockRejectedValueOnce(new ApiClientError("characters unavailable",{kind:"network"})).mockResolvedValue(eligiblePlayerCharactersFixture);
    render(<App client={c.client}/>);
    fireEvent.click(await screen.findByRole("button",{name:"返回设置"}));
    const retry = await screen.findByRole("button",{name:"重试 eligible Player Character GET"});
    fireEvent.click(screen.getByRole("button",{name:"刷新可用选项"}));
    await screen.findByLabelText("选择难度");
    expect(retry).toBeVisible();
    fireEvent.click(retry);
    await waitFor(() => expect(screen.queryByRole("button",{name:"重试 eligible Player Character GET"})).not.toBeInTheDocument());
    expect(screen.getByRole("button",{name:"确认并开始"})).toBeDisabled();
    expect(screen.getByLabelText("选择难度")).toHaveValue("");
    expect(c.entry).not.toHaveBeenCalled(); expect(c.exit).not.toHaveBeenCalled();
  });
});

describe("S6 correction: late eligible characters", () => {
  function deferredCharacters() {
    let resolve!: (value: typeof eligiblePlayerCharactersFixture) => void;
    const promise = new Promise<typeof eligiblePlayerCharactersFixture>((done) => { resolve = done; });
    return {promise, resolve};
  }

  function setupClient() {
    const client = new PublicApiClient({baseUrl: `${apiOrigin}/`});
    vi.spyOn(client, "listScenarios").mockResolvedValue(scenarioCatalogFixture);
    vi.spyOn(client, "listRunEntryOptions").mockResolvedValue(runOptionsFixture);
    vi.spyOn(client, "enterNativeRun").mockResolvedValue(nativeEntryFixture());
    vi.spyOn(client, "getNativeRunJourney").mockResolvedValue(nativeJourneyFixture());
    vi.spyOn(client, "getSessionView").mockResolvedValue(nativeViewFixture(activeViewFixture));
    return client;
  }

  async function chooseNativeWorld() {
    fireEvent.click(screen.getByRole("button", {name: "原生 Run 设置"}));
    await screen.findByLabelText("选择难度");
    fireEvent.change(screen.getByLabelText("选择难度"), {target: {value: "difficulty.open-expedition"}});
    fireEvent.change(screen.getByLabelText("选择起始世界"), {target: {value: "world.death_certificate"}});
  }

  function expectExplicitSelectionRequired(client: PublicApiClient) {
    expect(screen.getByRole("button", {name: "确认并开始"})).toBeDisabled();
    fireEvent.click(screen.getByRole("button", {name: "确认并开始"}));
    expect(client.enterNativeRun).not.toHaveBeenCalled();
  }

  it.each(["initial load", "refresh"])("does not select the first character after delayed %s in native mode", async (kind) => {
    const client = setupClient();
    const late = deferredCharacters();
    const list = vi.spyOn(client, "listEligiblePlayerCharacters");
    if (kind === "refresh") list.mockRejectedValueOnce(new ApiClientError("eligible list unavailable", {kind: "network"}));
    list.mockReturnValue(late.promise);
    render(<App client={client} />);
    await chooseNativeWorld();
    if (kind === "refresh") {
      fireEvent.click(await screen.findByRole("button", {name: "重试 eligible Player Character GET"}));
      await waitFor(() => expect(list).toHaveBeenCalledTimes(2));
    }
    expectExplicitSelectionRequired(client);
    await act(async () => { late.resolve(eligiblePlayerCharactersFixture); await late.promise; });
    expect(await screen.findByLabelText("Player Character")).toHaveValue("");
    expectExplicitSelectionRequired(client);
    expect(screen.getByLabelText("选择难度")).toHaveValue("difficulty.open-expedition");
    expect(screen.getByLabelText("选择起始世界")).toHaveValue("world.death_certificate");
    fireEvent.change(screen.getByLabelText("Player Character"), {target: {value: playerCharacterFixture.player_character_id.value}});
    expect(screen.getByRole("button", {name: "确认并开始"})).toBeEnabled();
    expect(client.enterNativeRun).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: "确认并开始"}));
    await screen.findByText("当前 Session：session-public-1");
    expect(client.enterNativeRun).toHaveBeenCalledTimes(1);
  });

  it("ignores an obsolete list after client replacement and a newer explicit native selection", async () => {
    const oldClient = setupClient();
    const oldList = deferredCharacters();
    vi.spyOn(oldClient, "listEligiblePlayerCharacters").mockReturnValue(oldList.promise);
    const page = render(<App client={oldClient} />);
    await chooseNativeWorld();
    const newClient = setupClient();
    const newList = deferredCharacters();
    vi.spyOn(newClient, "listEligiblePlayerCharacters").mockReturnValue(newList.promise);
    page.rerender(<App client={newClient} />);
    await chooseNativeWorld();
    expectExplicitSelectionRequired(newClient);
    await act(async () => { newList.resolve(eligiblePlayerCharactersFixture); await newList.promise; });
    expect(await screen.findByLabelText("Player Character")).toHaveValue("");
    expectExplicitSelectionRequired(newClient);
    fireEvent.change(screen.getByLabelText("Player Character"), {target: {value: playerCharacterFixture.player_character_id.value}});
    const obsolete = {...playerCharacterFixture, player_character_id: {value: "pc.obsolete"}};
    await act(async () => {
      oldList.resolve({eligible_player_characters: [obsolete], truncated: true});
      await oldList.promise;
    });
    expect(screen.getByLabelText("Player Character")).toHaveValue(playerCharacterFixture.player_character_id.value);
    expect(screen.queryByText(/pc.obsolete/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", {name: "确认并开始"})).toBeEnabled();
    expect(oldClient.enterNativeRun).not.toHaveBeenCalled();
    expect(newClient.enterNativeRun).not.toHaveBeenCalled();
  });

  it("retains an explicit still-valid character while refreshing native options", async () => {
    const client = setupClient();
    vi.spyOn(client, "listEligiblePlayerCharacters").mockResolvedValue(eligiblePlayerCharactersFixture);
    render(<App client={client} />);
    await screen.findByLabelText("Player Character");
    await chooseNativeWorld();
    expectExplicitSelectionRequired(client);
    fireEvent.change(screen.getByLabelText("Player Character"), {target: {value: playerCharacterFixture.player_character_id.value}});
    fireEvent.click(screen.getByRole("button", {name: "刷新可用选项"}));
    await waitFor(() => expect(client.listRunEntryOptions).toHaveBeenCalledTimes(2));
    await screen.findByLabelText("选择难度");
    expect(screen.getByLabelText("Player Character")).toHaveValue(playerCharacterFixture.player_character_id.value);
    expect(screen.getByRole("button", {name: "确认并开始"})).toBeEnabled();
    expect(client.enterNativeRun).not.toHaveBeenCalled();
  });

  it("preserves legacy first-character selection when a delayed list completes in legacy mode", async () => {
    const client = setupClient();
    const late = deferredCharacters();
    vi.spyOn(client, "listEligiblePlayerCharacters").mockReturnValue(late.promise);
    render(<App client={client} />);
    await chooseNativeWorld();
    fireEvent.click(screen.getByRole("button", {name: "传统副本模式"}));
    await act(async () => { late.resolve(eligiblePlayerCharactersFixture); await late.promise; });
    expect(await screen.findByLabelText("Player Character")).toHaveValue(playerCharacterFixture.player_character_id.value);
    expect(await screen.findByRole("button", {name: "进入 Run"})).toBeEnabled();
    expect(client.enterNativeRun).not.toHaveBeenCalled();
  });

  it("retains explicitly created character selection when entering native setup", async () => {
    const client = setupClient();
    vi.spyOn(client, "listEligiblePlayerCharacters").mockResolvedValue({eligible_player_characters: [], truncated: false});
    vi.spyOn(client, "createPlayerCharacter").mockResolvedValue(playerCharacterFixture);
    render(<App client={client} />);
    fireEvent.click(await screen.findByRole("button", {name: "创建最小 Player Character"}));
    await screen.findByText(/已选择服务器返回的创建结果/);
    await chooseNativeWorld();
    expect(screen.getByRole("button", {name: "确认并开始"})).toBeEnabled();
    expect(client.createPlayerCharacter).toHaveBeenCalledTimes(1);
    expect(client.enterNativeRun).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: "确认并开始"}));
    await screen.findByText("当前 Session：session-public-1");
    expect(client.enterNativeRun).toHaveBeenCalledTimes(1);
  });
});

it("native selections and exact override bounds require explicit confirmation",async () => {
  let posts=0;
  server.use(scenarioHandler(),http.get(`${apiOrigin}/v1/run-entry-options`,() => HttpResponse.json(runOptionsFixture)),
    http.post(`${apiOrigin}/v1/runs/native`,() => {posts++; return HttpResponse.json({},{status:500});}));
  renderApp(); await screen.findByLabelText("Player Character");
  fireEvent.click(screen.getByRole("button",{name:"原生 Run 设置"}));
  await screen.findByLabelText("选择难度");
  expect(screen.getByLabelText("选择难度")).toHaveValue("");
  expect(screen.getByLabelText("选择起始世界")).toHaveValue("");
  expect(screen.getByRole("button",{name:"确认并开始"})).toBeDisabled();
  fireEvent.change(screen.getByLabelText("Player Character"),{target:{value:playerCharacterFixture.player_character_id.value}});
  fireEvent.change(screen.getByLabelText("选择难度"),{target:{value:"difficulty.open-expedition"}});
  fireEvent.change(screen.getByLabelText("选择起始世界"),{target:{value:"world.death_certificate"}});
  fireEvent.click(screen.getByLabelText("调整资源压力"));
  fireEvent.change(screen.getByLabelText("资源压力"),{target:{value:"31"}});
  expect(screen.getByRole("button",{name:"确认并开始"})).toBeDisabled();
  fireEvent.change(screen.getByLabelText("资源压力"),{target:{value:"30"}});
  expect(screen.getByRole("button",{name:"确认并开始"})).toBeEnabled();
  fireEvent.click(screen.getByRole("button",{name:"刷新可用选项"}));
  await screen.findByLabelText("选择难度");
  expect(screen.getByLabelText("资源压力")).toHaveValue(30);
  fireEvent.change(screen.getByLabelText("选择难度"),{target:{value:"difficulty.fragile-alliance"}});
  expect(screen.getByLabelText("选择起始世界")).toHaveValue("");
  expect(screen.getByLabelText("调整资源压力")).not.toBeChecked();
  expect(posts).toBe(0);
});

function scenarioHandler() {
  return http.get(`${apiOrigin}/v1/scenarios`, () =>
    HttpResponse.json(scenarioCatalogFixture),
  );
}

function eligibleHandler() {
  return http.get(
    `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
    () => HttpResponse.json(eligiblePlayerCharactersFixture),
  );
}

function renderApp(eligible = eligibleHandler()) {
  server.use(eligible);
  const rendered = render(
    <App
      client={testClient}
      idempotencyKeyFactory={() => "web-mutation-ui-test"}
    />,
  );
  fireEvent.click(screen.getByRole("button", {name:"传统副本模式"}));
  return rendered;
}

function storedRecoveryRecord() {
  const result = readSessionRecoveryRecord();
  if (!result.ok) {
    throw new Error(`unexpected storage failure: ${result.failure.operation}`);
  }
  return result.value;
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

describe("mode presentation", () => {
  const warning =
    "Deterministic Demo  local only  temporary data  not a production Provider";

  it("shows the exact warning only in deterministic-demo mode", async () => {
    vi.stubEnv("VITE_APP_MODE", "deterministic-demo");
    server.use(scenarioHandler());

    const rendered = renderApp();

    await screen.findByLabelText("副本");
    expect(
      rendered.container.querySelector(".demo-warning")?.textContent,
    ).toBe(warning);
  });

  it.each([undefined, "development", "production", "unknown-ordinary"])(
    "does not claim deterministic Provider activation for %s mode",
    async (mode) => {
      if (mode === undefined) {
        vi.stubEnv("VITE_APP_MODE", "");
      } else {
        vi.stubEnv("VITE_APP_MODE", mode);
      }
      server.use(scenarioHandler());

      const rendered = renderApp();

      await screen.findByLabelText("副本");
      expect(rendered.container.querySelector(".demo-warning")).toBeNull();
      expect(rendered.container).not.toHaveTextContent(
        "not a production Provider",
      );
    },
  );
});

describe("scenario discovery states", () => {
  it("renders loading and then the successful public catalog", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, async () => {
        await delay(25);
        return HttpResponse.json(scenarioCatalogFixture);
      }),
    );

    renderApp();
    expect(screen.getByText("正在加载公开副本…")).toHaveAttribute(
      "role",
      "status",
    );
    expect(await screen.findByLabelText("副本")).toHaveValue(
      "scenario.public-alpha",
    );
    expect(screen.getByText(scenarioCatalogFixture.scenarios[0]!.hook)).toBeVisible();
    expect(screen.getByLabelText("Player Character")).toHaveValue(
      playerCharacterFixture.player_character_id.value,
    );
  });

  it("renders an empty catalog state without a create control", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json({ scenarios: [] }),
      ),
    );

    renderApp();
    expect(
      await screen.findByText("当前没有可公开游玩的副本。"),
    ).toBeVisible();
    expect(
      screen.queryByRole("button", { name: "进入 Run" }),
    ).not.toBeInTheDocument();
  });

  it("renders a public ErrorResponse for catalog failure", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json(errorFixture("INTERNAL_SERVER_ERROR", "Internal server error"), {
          status: 500,
        }),
      ),
    );

    renderApp();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 500 · INTERNAL_SERVER_ERROR · Internal server error",
    );
  });

  it("fails closed without a retry affordance for a contract-incompatible scenario response", async () => {
    server.use(
      http.get(`${apiOrigin}/v1/scenarios`, () =>
        HttpResponse.json({ scenarios: [{ scenario_id: "incomplete" }] }),
      ),
    );
    renderApp();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "公开副本响应不符合合同，选择保持锁定",
    );
    expect(
      screen.queryByRole("button", { name: "重试公开副本 GET" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "进入 Run" }),
    ).not.toBeInTheDocument();
  });

  it("fails closed without a POST for a contract-incompatible eligible response", async () => {
    let posts = 0;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/:operation`, () => {
        posts += 1;
        return HttpResponse.json({}, { status: 500 });
      }),
    );
    renderApp(
      http.get(
        `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
        () => HttpResponse.json({ eligible_player_characters: [] }),
      ),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Player Character 响应不符合合同，选择保持锁定",
    );
    expect(posts).toBe(0);
  });
});

describe("Player Character selection and Run entry", () => {
  it("persists Run entry exactly once before View GET, clears its attempt and renders the authoritative summary", async () => {
    const order: string[] = [];
    let entryBody: unknown;
    let entryKey: string | null = null;
    let entryCount = 0;
    let recoveryWrites = 0;
    let attemptWasPresentAtInitialStorage = false;
    let legacySessionCreates = 0;
    const setItem = Storage.prototype.setItem;
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(function (
      this: Storage,
      key,
      value,
    ) {
      if (key !== SESSION_RECOVERY_STORAGE_KEY) {
        setItem.call(this, key, value);
        return;
      }
      recoveryWrites += 1;
      order.push("storage");
      attemptWasPresentAtInitialStorage = screen
        .getByRole("button", { name: "相同操作正在发送…" })
        .hasAttribute("disabled");
      if (recoveryWrites > 1) {
        throw new DOMException("second recovery write blocked", "QuotaExceededError");
      }
      setItem.call(this, key, value);
    });
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/runs`, async ({ request }) => {
        entryCount += 1;
        order.push("entry");
        entryBody = await request.json();
        entryKey = request.headers.get("idempotency-key");
        return HttpResponse.json(runEntryResponseFixture);
      }),
      http.post(`${apiOrigin}/v1/sessions`, () => {
        legacySessionCreates += 1;
        return HttpResponse.json({}, { status: 500 });
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          order.push("view");
          expect(storedRecoveryRecord()).toEqual({
            version: 1,
            session_id: "session-public-1",
          });
          return HttpResponse.json(activeViewFixture);
        },
      ),
    );
    const user = userEvent.setup();
    renderApp();

    await user.click(
      await screen.findByRole("button", { name: "进入 Run" }),
    );

    expect(
      await screen.findByText("当前 Session：session-public-1"),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "雾港回声", level: 2 })).toBeVisible();
    expect(screen.getByText(/停止条件：/)).toHaveTextContent("AWAIT_PLAYER");
    expect(
      screen.getByRole("button", { name: "检查灯塔信号" }),
    ).toBeVisible();
    await user.click(screen.getByText("角色与记忆"));
    expect(screen.getByText("公开玩家状态")).toBeVisible();
    expect(screen.getByRole("region", {name: "当前资源与时钟"})).toHaveTextContent("clock.public.tide2 / 8");
    expect(entryBody).toEqual(runEntryRequestFixture);
    expect(entryKey).toBe("web-mutation-ui-test");
    expect(entryCount).toBe(1);
    expect(recoveryWrites).toBe(1);
    expect(attemptWasPresentAtInitialStorage).toBe(true);
    expect(order).toEqual(["entry", "storage", "view"]);
    expect(legacySessionCreates).toBe(0);
    expect(
      screen.queryByRole("heading", { name: "sessionStorage 安全锁定" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "手动重试完全相同的操作" }),
    ).not.toBeInTheDocument();
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });
  });

  it("prevents duplicate Run entry while the first request is in flight", async () => {
    let releaseRequest: (() => void) | undefined;
    const gate = new Promise<void>((resolve) => {
      releaseRequest = resolve;
    });
    let entryCount = 0;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/runs`, async () => {
        entryCount += 1;
        await gate;
        return HttpResponse.json(runEntryResponseFixture);
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
    );
    renderApp();
    const button = await screen.findByRole("button", { name: "进入 Run" });
    const form = button.closest("form");
    expect(form).not.toBeNull();

    fireEvent.submit(form!);
    fireEvent.submit(form!);
    await waitFor(() => expect(entryCount).toBe(1));
    expect(screen.getByRole("button", { name: "正在进入 Run…" })).toBeDisabled();
    releaseRequest?.();

    expect(
      await screen.findByText("当前 Session：session-public-1"),
    ).toBeVisible();
    expect(entryCount).toBe(1);
  });

  it("does not enter again when React rerenders the page", async () => {
    let entryCount = 0;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/runs`, () => {
        entryCount += 1;
        return HttpResponse.json(runEntryResponseFixture);
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
    );
    const user = userEvent.setup();
    const rendered = renderApp();
    await user.click(
      await screen.findByRole("button", { name: "进入 Run" }),
    );
    await screen.findByText("当前 Session：session-public-1");

    rendered.rerender(
      <App
        client={testClient}
        idempotencyKeyFactory={() => "web-mutation-ui-test"}
      />,
    );
    await waitFor(() => expect(entryCount).toBe(1));
  });

  it("shows a definitive Run-entry conflict without treating it as success", async () => {
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/runs`, () =>
        HttpResponse.json(errorFixture("IDEMPOTENCY_CONFLICT", "Idempotency key was reused"), {
          status: 409,
        }),
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.click(
      await screen.findByRole("button", { name: "进入 Run" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 409 · IDEMPOTENCY_CONFLICT",
    );
    expect(screen.queryByText(/当前 Session：/)).not.toBeInTheDocument();
  });

  it("retains stored Session recovery when the first View read fails and never repeats Run entry", async () => {
    let entryCount = 0;
    let viewCount = 0;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/runs`, () => {
        entryCount += 1;
        return HttpResponse.json({
          ...runEntryResponseFixture,
          session_id: "session-public-2",
        });
      }),
      http.get(`${apiOrigin}/v1/sessions/session-public-2/view`, () =>
        {
          viewCount += 1;
          return HttpResponse.json(
            errorFixture("SESSION_NOT_FOUND", "Entered session view was not found"),
            { status: 404 },
          );
        },
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.click(await screen.findByRole("button", { name: "进入 Run" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 404 · SESSION_NOT_FOUND · Entered session view was not found",
    );
    expect(
      screen.getByText(/已进入 Run 并保存 Session：session-public-2/),
    ).toBeVisible();
    expect(screen.queryByText(/当前 Session：/)).not.toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-2",
    });
    expect(screen.getByRole("button", { name: "重试读取权威 View" })).toBeVisible();
    expect(entryCount).toBe(1);
    expect(viewCount).toBe(1);
  });

  it("coordinates rapid Run entry and manual submissions as one foreground operation", async () => {
    let releaseEntry: (() => void) | undefined;
    const entryGate = new Promise<void>((resolve) => {
      releaseEntry = resolve;
    });
    let entryCount = 0;
    let enteredViewCount = 0;
    let manualReadCount = 0;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/runs`, async () => {
        entryCount += 1;
        await entryGate;
        return HttpResponse.json(runEntryResponseFixture);
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          enteredViewCount += 1;
          return HttpResponse.json(activeViewFixture);
        },
      ),
      http.get(`${apiOrigin}/v1/sessions/manual-session/view`, () => {
        manualReadCount += 1;
        return HttpResponse.json(activeViewFixture);
      }),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(
      await screen.findByLabelText("Session ID"),
      "manual-session",
    );
    const entryButton = screen.getByRole("button", { name: "进入 Run" });
    const readButton = screen.getByRole("button", {
      name: "读取 PlayerSessionView",
    });
    const entryForm = entryButton.closest("form");
    const readForm = readButton.closest("form");
    expect(entryForm).not.toBeNull();
    expect(readForm).not.toBeNull();

    fireEvent.submit(entryForm!);
    fireEvent.submit(readForm!);
    await waitFor(() => expect(entryCount).toBe(1));
    expect(screen.getByRole("button", { name: "正在进入 Run…" })).toBeDisabled();
    expect(readButton).toBeDisabled();
    releaseEntry?.();

    expect(
      await screen.findByText("当前 Session：session-public-1"),
    ).toBeVisible();
    expect(entryCount).toBe(1);
    expect(enteredViewCount).toBe(1);
    expect(manualReadCount).toBe(0);
  });

  it("creates exactly one minimal Player Character from authoritative empty eligibility and waits for explicit Run entry", async () => {
    let creationCount = 0;
    let entryCount = 0;
    let creationBody: unknown;
    let creationKey: string | null = null;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/player-characters`, async ({ request }) => {
        creationCount += 1;
        creationBody = await request.json();
        creationKey = request.headers.get("idempotency-key");
        return HttpResponse.json(playerCharacterFixture);
      }),
      http.post(`${apiOrigin}/v1/runs`, () => {
        entryCount += 1;
        return HttpResponse.json(runEntryResponseFixture);
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
    );
    const user = userEvent.setup();
    renderApp(
      http.get(
        `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
        () =>
          HttpResponse.json({
            eligible_player_characters: [],
            truncated: false,
          }),
      ),
    );

    await user.click(
      await screen.findByRole("button", {
        name: "创建最小 Player Character",
      }),
    );
    expect(await screen.findByText(/已选择服务器返回的创建结果/)).toHaveTextContent(
      playerCharacterFixture.player_character_id.value,
    );
    expect(creationBody).toEqual(minimalPlayerCharacterCreationFixture);
    expect(creationKey).toBe("web-mutation-ui-test");
    expect(creationCount).toBe(1);
    expect(entryCount).toBe(0);
    expect(
      screen.queryByRole("button", { name: "创建最小 Player Character" }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "进入 Run" }));
    await screen.findByText("当前 Session：session-public-1");
    expect(entryCount).toBe(1);
  });

  it.each([
    [404, "PLAYER_CHARACTER_NOT_FOUND", "Player character was not found"],
    [409, "IDEMPOTENCY_CONFLICT", "Idempotency key was reused"],
    [422, "REQUEST_VALIDATION_FAILED", "Request validation failed"],
  ] as const)(
    "clears a direct definitive creation HTTP %i %s result",
    async (status, code, message) => {
      server.use(
        scenarioHandler(),
        http.post(`${apiOrigin}/v1/player-characters`, () =>
          HttpResponse.json(errorFixture(code, message), {
            status,
          }),
        ),
      );
      const user = userEvent.setup();
      renderApp(
        http.get(
          `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
          () =>
            HttpResponse.json({
              eligible_player_characters: [],
              truncated: false,
            }),
        ),
      );
      await user.click(
        await screen.findByRole("button", {
          name: "创建最小 Player Character",
        }),
      );

      expect(screen.getByText(new RegExp(code))).toBeVisible();
      expect(
        screen.queryByRole("button", {
          name: "手动重试完全相同的操作",
        }),
      ).not.toBeInTheDocument();
      expect(
        screen.getByRole("button", {
          name: "创建最小 Player Character",
        }),
      ).toBeEnabled();
    },
  );

  it("preserves eligible server order, discloses truncation and submits the explicitly selected projection", async () => {
    const firstCharacter = {
      ...playerCharacterFixture,
      player_character_id: { value: "pc.00" },
    };
    const secondCharacter = {
      ...playerCharacterFixture,
      player_character_id: { value: "pc.01" },
      record_revision: { value: 7 },
    };
    const boundedCharacters = [
      firstCharacter,
      secondCharacter,
      ...Array.from({ length: 30 }, (_, index) => ({
        ...playerCharacterFixture,
        player_character_id: {
          value: `pc.${String(index + 2).padStart(2, "0")}`,
        },
      })),
    ];
    let entryBody: unknown;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/runs`, async ({ request }) => {
        entryBody = await request.json();
        return HttpResponse.json({
          ...runEntryResponseFixture,
          player_character: secondCharacter,
        });
      }),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
    );
    const user = userEvent.setup();
    renderApp(
      http.get(
        `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
        () =>
          HttpResponse.json({
            eligible_player_characters: boundedCharacters,
            truncated: true,
          }),
      ),
    );

    const selector = await screen.findByLabelText("Player Character");
    expect(
      [...(selector as HTMLSelectElement).options]
        .slice(0, 2)
        .map((option) => option.value),
    ).toEqual(["pc.00", "pc.01"]);
    expect(screen.getByText(/前 32 个可选 Player Character/)).toHaveTextContent(
      "没有总数或分页",
    );
    await user.selectOptions(selector, "pc.01");
    await user.click(screen.getByRole("button", { name: "进入 Run" }));
    await screen.findByText("当前 Session：session-public-1");
    expect(entryBody).toEqual({
      player_character_id: "pc.01",
      expected_record_revision: 7,
      scenario_id: "scenario.public-alpha",
    });
  });

  it("renders eligible loading, recoverable failure and explicit safe GET retry without a POST", async () => {
    let eligibleReads = 0;
    let posts = 0;
    server.use(
      scenarioHandler(),
      http.post(`${apiOrigin}/v1/:operation`, () => {
        posts += 1;
        return HttpResponse.json({}, { status: 500 });
      }),
    );
    const user = userEvent.setup();
    renderApp(
      http.get(
        `${apiOrigin}/v1/player-characters/eligible-for-run-entry`,
        () => {
          eligibleReads += 1;
          return eligibleReads === 1
            ? HttpResponse.json(
                errorFixture("INTERNAL_SERVER_ERROR", "Internal server error"),
                { status: 500 },
              )
            : HttpResponse.json(eligiblePlayerCharactersFixture);
        },
      ),
    );
    expect(
      screen.getByText("正在加载可进入 Run 的 Player Character…"),
    ).toHaveAttribute("role", "status");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 500 · INTERNAL_SERVER_ERROR",
    );
    await user.click(
      screen.getByRole("button", {
        name: "重试 eligible Player Character GET",
      }),
    );
    expect(await screen.findByLabelText("Player Character")).toHaveValue(
      "pc.public-alpha",
    );
    expect(eligibleReads).toBe(2);
    expect(posts).toBe(0);
  });

  it.each([
    [404, "PLAYER_CHARACTER_NOT_FOUND", "Player character was not found", "刷新 eligible Player Character 后重新选择"],
    [409, "PLAYER_CHARACTER_STALE", "Player character revision is stale", "刷新 eligible Player Character 后重新选择"],
    [409, "PLAYER_CHARACTER_NOT_ELIGIBLE", "Player character is not eligible for Run entry", "刷新 eligible Player Character 后重新选择"],
    [409, "RUN_ENTRY_CONFLICT", "Run entry conflicts with current state", "刷新 eligible Player Character 后重新选择"],
    [422, "REQUEST_VALIDATION_FAILED", "Request validation failed", "刷新 eligible Player Character 后重新选择"],
    [422, "INVALID_SCENARIO_DEFINITION", "Scenario definition is not available", "刷新公开副本后重新选择"],
  ] as const)(
    "classifies direct Run-entry HTTP %i %s as definitive",
    async (status, code, message, refreshLabel) => {
      server.use(
        scenarioHandler(),
        http.post(`${apiOrigin}/v1/runs`, () =>
          HttpResponse.json(errorFixture(code, message), { status }),
        ),
      );
      const user = userEvent.setup();
      renderApp();
      await user.click(await screen.findByRole("button", { name: "进入 Run" }));

      expect(await screen.findByRole("alert")).toHaveTextContent(code);
      expect(
        screen.getByRole("button", { name: refreshLabel }),
      ).toBeVisible();
      expect(
        screen.queryByRole("button", {
          name: "手动重试完全相同的操作",
        }),
      ).not.toBeInTheDocument();
    },
  );
});

describe("manual PlayerSessionView reads", () => {
  it("reads an active session only after explicit user submission", async () => {
    let readCount = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          readCount += 1;
          return HttpResponse.json(activeViewFixture);
        },
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await screen.findByLabelText("副本");
    expect(readCount).toBe(0);

    await user.type(screen.getByLabelText("Session ID"), "session-public-1");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    await user.click(await screen.findByText("角色与记忆"));
    expect(screen.getByText("长期记忆")).toBeVisible();
    expect(screen.getByText("当前公开正文")).toBeVisible();
    expect(readCount).toBe(1);
    expect(storedRecoveryRecord()).toEqual({
      version: 1,
      session_id: "session-public-1",
    });
  });

  it("renders an ended session with ending_status and ending presentation", async () => {
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(endedViewFixture("FAILED")),
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(
      await screen.findByLabelText("Session ID"),
      "session-public-1",
    );
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(await screen.findByText("FAILED")).toBeVisible();
    expect(screen.getByRole("heading", { name: "信号沉没" })).toBeVisible();
    await user.click(screen.getByText("场景提示与技术信息"));
    expect(screen.getByText("Ending ID：ending.public.failed")).toBeVisible();
    expect(screen.getByText(/停止条件：/)).toHaveTextContent("SCENARIO_ENDED");
  });

  it("renders a 404 ErrorResponse for a missing manual session", async () => {
    server.use(
      scenarioHandler(),
      http.get(`${apiOrigin}/v1/sessions/missing/view`, () =>
        HttpResponse.json(errorFixture("SESSION_NOT_FOUND", "Session was not found"), {
          status: 404,
        }),
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(await screen.findByLabelText("Session ID"), "missing");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 404 · SESSION_NOT_FOUND · Session was not found",
    );
  });

  it("clears an older loaded view when a different manual session returns 404", async () => {
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => HttpResponse.json(activeViewFixture),
      ),
      http.get(`${apiOrigin}/v1/sessions/missing/view`, () =>
        HttpResponse.json(
          errorFixture("SESSION_NOT_FOUND", "Requested session was not found"),
          { status: 404 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderApp();
    const input = await screen.findByLabelText("Session ID");
    await user.type(input, "session-public-1");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );
    await screen.findByText("当前 Session：session-public-1");
    expect(screen.getByRole("article")).toBeVisible();

    const currentInput = screen.getByLabelText("Session ID");
    await user.clear(currentInput);
    await user.type(currentInput, "missing");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "HTTP 404 · SESSION_NOT_FOUND · Requested session was not found",
    );
    expect(screen.queryByText(/当前 Session：/)).not.toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    expect(screen.queryByText("session-public-1")).not.toBeInTheDocument();
  });

  it("reads a pasted session ID with surrounding whitespace after trimming it", async () => {
    let readCount = 0;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        () => {
          readCount += 1;
          return HttpResponse.json(activeViewFixture);
        },
      ),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(
      await screen.findByLabelText("Session ID"),
      "  session-public-1  ",
    );
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(
      await screen.findByText("当前 Session：session-public-1"),
    ).toBeVisible();
    expect(readCount).toBe(1);
  });

  it("reports an invalid manual Session ID accessibly without making a request", async () => {
    let readCount = 0;
    server.use(
      scenarioHandler(),
      http.get(`${apiOrigin}/v1/sessions/:sessionId/view`, () => {
        readCount += 1;
        return HttpResponse.json(activeViewFixture);
      }),
    );
    const user = userEvent.setup();
    renderApp();
    await user.type(await screen.findByLabelText("Session ID"), "invalid id");
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Session ID 格式无效，请检查后重试。",
    );
    expect(readCount).toBe(0);
  });

  it("aborts an in-flight foreground session operation when unmounted", async () => {
    let requestStarted = false;
    let requestAborted = false;
    server.use(
      scenarioHandler(),
      http.get(
        `${apiOrigin}/v1/sessions/session-public-1/view`,
        async ({ request }) => {
          requestStarted = true;
          request.signal.addEventListener("abort", () => {
            requestAborted = true;
          });
          await delay("infinite");
          return HttpResponse.json(activeViewFixture);
        },
      ),
    );
    const user = userEvent.setup();
    const rendered = renderApp();
    await user.type(
      await screen.findByLabelText("Session ID"),
      "session-public-1",
    );
    await user.click(
      screen.getByRole("button", { name: "读取 PlayerSessionView" }),
    );
    await waitFor(() => expect(requestStarted).toBe(true));

    rendered.unmount();

    await waitFor(() => expect(requestAborted).toBe(true));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
